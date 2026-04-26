"""Folder / file opening skill."""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Union

from config.settings import FOLDER_PATHS

logger = logging.getLogger(__name__)


def open_path(path: Union[Path, str]) -> dict[str, Any]:
    p = Path(path) if not str(path).startswith("shell:") else str(path)
    # Shell virtual folders (e.g. Recycle Bin)
    if isinstance(p, str) and p.startswith("shell:"):
        subprocess.Popen(["explorer.exe", p])
        return {"ok": True, "speak": f"Opening {p.split(':', 1)[1]}."}
    if not p.exists():
        return {"ok": False, "speak": f"The path {p} does not exist."}
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(p))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(p)])
        else:
            subprocess.Popen(["xdg-open", str(p)])
        return {"ok": True, "speak": f"Opening {p.name or str(p)}."}
    except Exception as e:
        logger.exception("Failed to open %s", p)
        return {"ok": False, "speak": f"I couldn't open {p}."}


def open_folder(name: str) -> dict[str, Any]:
    key = name.strip().lower()
    target = FOLDER_PATHS.get(key)
    if target is None:
        return {"ok": False, "speak": f"I don't know a folder called {name}."}
    return open_path(target)
