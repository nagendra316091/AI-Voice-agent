"""Dispatcher that runs :class:`Task` objects against the host OS.

Each action is a small function in ``modules.executor.skills.*``. Adding a
new capability is a three-line change: write the skill function, import it,
register it in the dispatch table.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

from config import settings
from modules.executor.skills import apps, files, media, system, utility, web, window
from modules.planner.planner import Task

logger = logging.getLogger(__name__)


class Executor:
    def __init__(self, result_file: Path, screenshot_dir: Path) -> None:
        self.result_file = Path(result_file)
        self.result_file.parent.mkdir(parents=True, exist_ok=True)
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self._dispatch: dict[str, Callable[..., dict[str, Any]]] = {
            # Opening things
            "open":            self._action_open,
            # Web
            "search_web":      lambda query: web.search(query, engine="google"),
            "search_youtube":  lambda query: web.search(query, engine="youtube"),
            # Utilities
            "math":            lambda op, a, b: utility.do_math(op, a, b, self.result_file),
            "type_text":       lambda text: utility.type_text(text),
            "say":             lambda text: {"ok": True, "speak": text, "message": text},
            "screenshot":      lambda: utility.screenshot(self.screenshot_dir),
            "time":            utility.time_now,
            "date":            utility.date_today,
            # System
            "lock":             system.lock,
            "sleep":            system.sleep,
            "shutdown":         system.shutdown,
            "restart":          system.restart,
            "cancel_shutdown":  system.cancel_shutdown,
            "volume_up":        system.volume_up,
            "volume_down":      system.volume_down,
            "mute_volume":      system.mute,
            "unmute_volume":    system.unmute,
            "volume_set":       lambda level: system.set_volume(level),
            # Window
            "minimize_all":    window.minimize_all,
            "close_window":    window.close_window,
            "switch_window":   window.switch_window,
            # Media
            "media_play_pause": media.play_pause,
            "media_next":       media.next_track,
            "media_prev":       media.prev_track,
            # Control
            "help":             self._action_help,
            "greet":            lambda: {"ok": True, "speak": "Hi! How can I help?"},
            "exit":             lambda: {"ok": True, "speak": "Goodbye.", "exit": True},
            "noop":             lambda: {"ok": False, "speak": None, "message": "noop"},
        }

    # -- dispatch --------------------------------------------------------
    def execute(self, task: Task) -> dict[str, Any]:
        handler = self._dispatch.get(task.action)
        if handler is None:
            msg = f"No handler registered for action '{task.action}'."
            logger.error(msg)
            return {"ok": False, "message": msg, "speak": "I can't do that yet."}
        try:
            result = handler(**task.params) if task.params else handler()
        except TypeError:
            logger.exception("Param mismatch for %s with %s", task.action, task.params)
            return {"ok": False, "speak": "I couldn't run that command."}
        except Exception as exc:
            logger.exception("Execution failed for %s", task.action)
            return {"ok": False, "message": str(exc),
                    "speak": "Something went wrong while running that command."}
        if not isinstance(result, dict):
            result = {"ok": True, "speak": str(result)}
        if "speak" not in result and task.speak:
            result["speak"] = task.speak
        return result

    # -- smart open ------------------------------------------------------
    def _action_open(self, target: str) -> dict[str, Any]:
        t = (target or "").strip().lower()
        if not t:
            return {"ok": False, "speak": "Open what?"}
        # Folder shortcut
        if t in settings.FOLDER_PATHS:
            return files.open_path(settings.FOLDER_PATHS[t])
        # Website shortcut
        if t in settings.WEBSITE_SHORTCUTS:
            return web.open_url(settings.WEBSITE_SHORTCUTS[t])
        # Bare URL / domain (contains a dot, no spaces)
        if web.looks_like_url(t):
            return web.open_url(t)
        # App catalogue (or fall through to Windows shell)
        return apps.open_app(t)

    # -- help ------------------------------------------------------------
    def _action_help(self) -> dict[str, Any]:
        tips = (
            "Here are some things you can say: open chrome, open youtube, open documents, "
            "search Google for python tutorials, play on YouTube lofi beats, multiply 72 thousand "
            "and 32, volume up, set volume to 50, mute, play, next track, minimize all, show desktop, "
            "lock my computer, take a screenshot, type hello world, what time is it."
        )
        return {"ok": True, "speak": tips, "message": tips}
