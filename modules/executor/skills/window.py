"""Window management skill — minimize all, close, switch."""
from __future__ import annotations

import logging
import sys
from typing import Any

logger = logging.getLogger(__name__)

try:
    import pyautogui
    _HAS_PAG = True
except Exception as _pag_err:  # pragma: no cover
    logger.warning("pyautogui unavailable: %s", _pag_err)
    _HAS_PAG = False


def minimize_all() -> dict[str, Any]:
    if not _HAS_PAG:
        return {"ok": False, "speak": "Hotkeys unavailable."}
    if sys.platform.startswith("win"):
        pyautogui.hotkey("win", "d")
    elif sys.platform == "darwin":
        pyautogui.hotkey("fn", "f11")
    else:
        pyautogui.hotkey("super", "d")
    return {"ok": True, "speak": "Showing desktop."}


def close_window() -> dict[str, Any]:
    if not _HAS_PAG:
        return {"ok": False, "speak": "Hotkeys unavailable."}
    if sys.platform == "darwin":
        pyautogui.hotkey("command", "w")
    else:
        pyautogui.hotkey("alt", "f4")
    return {"ok": True, "speak": "Closing window."}


def switch_window() -> dict[str, Any]:
    if not _HAS_PAG:
        return {"ok": False, "speak": "Hotkeys unavailable."}
    if sys.platform == "darwin":
        pyautogui.hotkey("command", "tab")
    else:
        pyautogui.hotkey("alt", "tab")
    return {"ok": True, "speak": "Switched window."}
