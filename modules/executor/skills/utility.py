"""Small utility skills: time, date, screenshot, typing, math."""
from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    import pyautogui
    _HAS_PAG = True
except Exception as _pag_err:  # pragma: no cover
    logger.warning("pyautogui unavailable: %s", _pag_err)
    _HAS_PAG = False


def time_now() -> dict[str, Any]:
    now = datetime.now().strftime("%I:%M %p").lstrip("0")
    return {"ok": True, "speak": f"It's {now}.", "message": now}


def date_today() -> dict[str, Any]:
    today = datetime.now().strftime("%A, %B %d, %Y")
    return {"ok": True, "speak": f"Today is {today}.", "message": today}


def screenshot(directory: Path) -> dict[str, Any]:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / datetime.now().strftime("screenshot_%Y%m%d_%H%M%S.png")
    try:
        if _HAS_PAG:
            pyautogui.screenshot(str(path))
        else:
            from PIL import ImageGrab  # type: ignore
            ImageGrab.grab().save(str(path))
        return {"ok": True,
                "speak": "Screenshot saved to pictures.",
                "message": f"Saved to {path}"}
    except Exception:
        logger.exception("Screenshot failed")
        return {"ok": False, "speak": "I couldn't take a screenshot."}


def type_text(text: str) -> dict[str, Any]:
    if not _HAS_PAG:
        return {"ok": False, "speak": "Typing isn't available."}
    if not text:
        return {"ok": False, "speak": "Type what?"}
    # Give the user a half-second to focus the target window.
    time.sleep(0.6)
    try:
        pyautogui.typewrite(text, interval=0.01)
    except Exception:
        # typewrite only handles ASCII; fall back to clipboard paste for Unicode.
        try:
            import pyperclip  # type: ignore
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
        except Exception:
            logger.exception("typewrite failed")
            return {"ok": False, "speak": "I couldn't type that."}
    return {"ok": True, "speak": "Typed."}


def _fmt(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def do_math(op: str, a: float, b: float, result_file: Path) -> dict[str, Any]:
    ops = {
        "multiply": (lambda x, y: x * y, "*"),
        "add":      (lambda x, y: x + y, "+"),
        "subtract": (lambda x, y: x - y, "-"),
        "divide":   (lambda x, y: x / y, "/"),
    }
    if op not in ops:
        return {"ok": False, "speak": f"I don't know how to {op}."}
    if op == "divide" and b == 0:
        return {"ok": False, "speak": "I cannot divide by zero."}
    fn, symbol = ops[op]
    result = fn(a, b)
    line = f"{_fmt(a)} {symbol} {_fmt(b)} = {_fmt(result)}"
    with Path(result_file).open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    return {"ok": True, "message": line,
            "speak": f"The result is {_fmt(result)}.",
            "result": result, "file": str(result_file)}
