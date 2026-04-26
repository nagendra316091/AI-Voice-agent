"""Append-only interaction log.

Each turn is one JSON line: ``{ts, transcript, intent, result}``. JSONL keeps
reads cheap and is trivially tailable. A future memory phase can replace this
with a vector store without changing the call site.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class History:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add(self, transcript: str, intent: str, result: dict[str, Any]) -> None:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "transcript": transcript,
            "intent": intent,
            "result": {
                k: v for k, v in result.items()
                if isinstance(v, (str, int, float, bool)) or v is None
            },
        }
        try:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            logger.exception("Failed to write history entry to %s", self.path)
