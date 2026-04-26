"""One-shot downloader for the small English Vosk model (~50 MB).

Run once:  python scripts/download_model.py
"""
from __future__ import annotations

import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

MODEL_NAME = "vosk-model-small-en-us-0.15"
MODEL_URL = f"https://alphacephei.com/vosk/models/{MODEL_NAME}.zip"
TARGET_DIR = Path(__file__).resolve().parent.parent / "models"


def main() -> int:
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    model_dir = TARGET_DIR / MODEL_NAME
    if model_dir.exists():
        print(f"[ok] Model already present: {model_dir}")
        return 0

    zip_path = TARGET_DIR / f"{MODEL_NAME}.zip"
    print(f"[..] Downloading {MODEL_URL}")
    try:
        with urllib.request.urlopen(MODEL_URL) as resp, zip_path.open("wb") as out:
            shutil.copyfileobj(resp, out)
    except Exception as exc:
        print(f"[err] Download failed: {exc}", file=sys.stderr)
        return 1

    print(f"[..] Extracting to {TARGET_DIR}")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(TARGET_DIR)
    zip_path.unlink(missing_ok=True)
    print(f"[ok] Model ready: {model_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
