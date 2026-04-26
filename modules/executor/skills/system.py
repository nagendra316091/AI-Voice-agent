"""System control skill — volume, power state.

Volume keys (up/down/mute) use the OS-level media keys via ``pyautogui`` so
they work reliably on Windows, macOS, and Linux without elevated rights.
Precise volume setting requires ``pycaw`` (Windows only); other platforms
fall back to repeated key presses.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from typing import Any

logger = logging.getLogger(__name__)

try:
    import pyautogui
    _HAS_PAG = True
except Exception as _pag_err:  # pragma: no cover
    logger.warning("pyautogui unavailable: %s", _pag_err)
    _HAS_PAG = False

# pycaw is Windows-only and optional.
try:
    from ctypes import POINTER, cast

    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    _HAS_PYCAW = True
except Exception:
    _HAS_PYCAW = False


# ---- volume --------------------------------------------------------------

def _press(key: str, times: int = 1) -> None:
    if not _HAS_PAG:
        return
    for _ in range(times):
        pyautogui.press(key)


def volume_up() -> dict[str, Any]:
    if not _HAS_PAG:
        return {"ok": False, "speak": "Volume control is not available."}
    _press("volumeup", 5)
    return {"ok": True, "speak": "Volume up."}


def volume_down() -> dict[str, Any]:
    if not _HAS_PAG:
        return {"ok": False, "speak": "Volume control is not available."}
    _press("volumedown", 5)
    return {"ok": True, "speak": "Volume down."}


def mute() -> dict[str, Any]:
    if not _HAS_PAG:
        return {"ok": False, "speak": "Mute is not available."}
    _press("volumemute", 1)
    return {"ok": True, "speak": "Muted."}


def unmute() -> dict[str, Any]:
    # VK_VOLUME_MUTE toggles; on most systems this re-enables audio.
    if not _HAS_PAG:
        return {"ok": False, "speak": "Unmute is not available."}
    _press("volumemute", 1)
    return {"ok": True, "speak": "Unmuted."}


def set_volume(level: int) -> dict[str, Any]:
    level = max(0, min(100, int(level)))
    if _HAS_PYCAW and sys.platform.startswith("win"):
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            endpoint = cast(interface, POINTER(IAudioEndpointVolume))
            endpoint.SetMasterVolumeLevelScalar(level / 100.0, None)
            return {"ok": True, "speak": f"Volume set to {level} percent."}
        except Exception as e:
            logger.warning("pycaw set_volume failed: %s — falling back to keypress.", e)
    # Fallback: hammer the volume keys roughly proportionally.
    if _HAS_PAG:
        _press("volumedown", 50)  # zero it
        _press("volumeup", int(level / 2))
        return {"ok": True, "speak": f"Volume roughly set to {level} percent."}
    return {"ok": False, "speak": "Precise volume control isn't available."}


# ---- power / session -----------------------------------------------------

def lock() -> dict[str, Any]:
    if sys.platform.startswith("win"):
        subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])
        return {"ok": True, "speak": "Locking the screen."}
    if sys.platform == "darwin":
        subprocess.Popen(["pmset", "displaysleepnow"])
        return {"ok": True, "speak": "Locking the screen."}
    subprocess.Popen(["xdg-screensaver", "lock"])
    return {"ok": True, "speak": "Locking the screen."}


def sleep() -> dict[str, Any]:
    if sys.platform.startswith("win"):
        # 3rd arg 0 = sleep, 1 = hibernate. Third/fourth flags disable wake timers.
        subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
        return {"ok": True, "speak": "Going to sleep."}
    if sys.platform == "darwin":
        subprocess.Popen(["pmset", "sleepnow"])
        return {"ok": True, "speak": "Going to sleep."}
    subprocess.Popen(["systemctl", "suspend"])
    return {"ok": True, "speak": "Going to sleep."}


def shutdown() -> dict[str, Any]:
    if sys.platform.startswith("win"):
        subprocess.Popen(["shutdown", "/s", "/t", "10"])
        return {"ok": True,
                "speak": "Shutting down in 10 seconds. Say 'cancel shutdown' to abort."}
    if sys.platform == "darwin":
        subprocess.Popen(["osascript", "-e", 'tell app "System Events" to shut down'])
        return {"ok": True, "speak": "Shutting down."}
    subprocess.Popen(["shutdown", "-h", "+0"])
    return {"ok": True, "speak": "Shutting down."}


def restart() -> dict[str, Any]:
    if sys.platform.startswith("win"):
        subprocess.Popen(["shutdown", "/r", "/t", "10"])
        return {"ok": True,
                "speak": "Restarting in 10 seconds. Say 'cancel shutdown' to abort."}
    if sys.platform == "darwin":
        subprocess.Popen(["osascript", "-e", 'tell app "System Events" to restart'])
        return {"ok": True, "speak": "Restarting."}
    subprocess.Popen(["shutdown", "-r", "+0"])
    return {"ok": True, "speak": "Restarting."}


def cancel_shutdown() -> dict[str, Any]:
    if sys.platform.startswith("win"):
        subprocess.Popen(["shutdown", "/a"])
        return {"ok": True, "speak": "Shutdown cancelled."}
    return {"ok": False, "speak": "Only Windows shutdowns can be cancelled here."}
