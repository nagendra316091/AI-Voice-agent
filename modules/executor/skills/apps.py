"""Application launching skill.

Known apps are looked up in :data:`config.settings.APP_COMMANDS`. Anything
else falls back to the Windows shell's ``start`` command, which resolves
App Paths / the Start Menu index and handles most installed software.

Two layers of robustness sit in front of that lookup:

1. ``_STT_ALIASES`` — a fixed map of common Vosk mishearings (e.g. the
   small English model often hears "notepad" as "not bad" or "no pad").
2. Fuzzy matching via ``difflib.get_close_matches`` against the union of
   ``APP_COMMANDS`` keys and the alias keys, so close-but-not-exact
   transcripts still resolve to the right app.
3. ``_BROWSER_TERMS`` — generic words like "browser" or "web browser"
   open the user's default browser instead of erroring out.
"""
from __future__ import annotations

import difflib
import logging
import os
import subprocess
import sys
import webbrowser
from typing import Any

from config.settings import APP_COMMANDS

logger = logging.getLogger(__name__)


# Common Vosk small-model mishearings -> canonical app key in APP_COMMANDS.
_STT_ALIASES: dict[str, str] = {
    # notepad
    "not bad": "notepad",
    "no pad": "notepad",
    "note pad": "notepad",
    "no bad": "notepad",
    "nor pad": "notepad",
    # calculator
    "calc later": "calculator",
    "cal later": "calculator",
    "calc": "calculator",
    # chrome
    "chrom": "chrome",
    "chrome browser": "chrome",
    "google": "chrome",            # ambiguous but usually means chrome here
    # edge
    "microsoft": "edge",
    "ms edge": "edge",
    # vs code
    "vs": "vs code",
    "visual code": "vs code",
    "v s code": "vs code",
    "the s code": "vs code",
    # explorer
    "file": "explorer",
    "files": "explorer",
    # terminal
    "term": "terminal",
}

# Generic browser words -> open the system default browser.
_BROWSER_TERMS: set[str] = {
    "browser",
    "web browser",
    "default browser",
    "in browser",        # frequent Vosk mishearing of "open browser"
    "internet",
    "web",
}


def _expand(cmd: list[str]) -> list[str]:
    return [os.path.expandvars(part) for part in cmd]


def _normalize(name: str) -> str:
    """Apply STT alias map, then a fuzzy match against known app keys."""
    key = name.strip().lower()
    if not key:
        return key
    if key in APP_COMMANDS:
        return key
    if key in _STT_ALIASES:
        resolved = _STT_ALIASES[key]
        logger.info("STT alias: %r -> %r", key, resolved)
        return resolved
    # Fuzzy fallback against the union of catalogued names + alias keys.
    candidates = list(APP_COMMANDS.keys()) + list(_STT_ALIASES.keys())
    matches = difflib.get_close_matches(key, candidates, n=1, cutoff=0.78)
    if matches:
        hit = matches[0]
        resolved = _STT_ALIASES.get(hit, hit)
        logger.info("Fuzzy match: %r -> %r (via %r)", key, resolved, hit)
        return resolved
    return key


def _open_default_browser() -> dict[str, Any]:
    try:
        webbrowser.open_new("about:blank")
        return {"ok": True, "message": "Launched default browser",
                "speak": "Opening your default browser."}
    except Exception as e:
        logger.exception("Default browser launch failed")
        return {"ok": False, "message": f"Could not open browser: {e}",
                "speak": "I couldn't open the default browser."}


def open_app(name: str) -> dict[str, Any]:
    raw = (name or "").strip().lower()
    if not raw:
        return {"ok": False, "speak": "Open which app?"}

    # Generic "browser" -> system default browser.
    if raw in _BROWSER_TERMS:
        return _open_default_browser()

    key = _normalize(raw)

    cmd = APP_COMMANDS.get(key)
    if cmd:
        expanded = _expand(cmd)
        try:
            subprocess.Popen(expanded, shell=False)
            return {"ok": True, "message": f"Launched {key}",
                    "speak": f"Opening {key}."}
        except FileNotFoundError:
            logger.info("Catalogued path not found for %s (%s); trying shell start.",
                        key, expanded[0])
        except Exception as e:
            logger.warning("Catalogued launch failed for %s: %s", key, e)

    # Fallback: let the OS figure it out.
    if sys.platform.startswith("win"):
        try:
            subprocess.Popen(f'start "" "{key}"', shell=True)
            return {"ok": True, "message": f"Launched {key} via shell",
                    "speak": f"Opening {key}."}
        except Exception as e:
            return {"ok": False, "message": f"Could not open {key}: {e}",
                    "speak": f"I couldn't find {key} on this computer."}

    if sys.platform == "darwin":
        subprocess.Popen(["open", "-a", key])
        return {"ok": True, "speak": f"Opening {key}."}

    subprocess.Popen(["xdg-open", key])
    return {"ok": True, "speak": f"Opening {key}."}
