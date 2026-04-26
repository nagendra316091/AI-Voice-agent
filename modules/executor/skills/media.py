"""Media transport skill — uses OS media keys."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    import pyautogui
    _HAS_PAG = True
except Exception as _pag_err:  # pragma: no cover
    logger.warning("pyautogui unavailable: %s", _pag_err)
    _HAS_PAG = False


def play_pause() -> dict[str, Any]:
    if not _HAS_PAG:
        return {"ok": False, "speak": "Media control isn't available."}
    pyautogui.press("playpause")
    return {"ok": True, "speak": "Toggled playback."}


def next_track() -> dict[str, Any]:
    if not _HAS_PAG:
        return {"ok": False, "speak": "Media control isn't available."}
    pyautogui.press("nexttrack")
    return {"ok": True, "speak": "Next track."}


def prev_track() -> dict[str, Any]:
    if not _HAS_PAG:
        return {"ok": False, "speak": "Media control isn't available."}
    pyautogui.press("prevtrack")
    return {"ok": True, "speak": "Previous track."}
