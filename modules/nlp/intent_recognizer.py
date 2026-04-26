"""Rule-based intent recognition.

Still rule-based so the agent stays fully offline and latency-free. The Intent
schema is stable, so a future phase can swap this for an LLM/embedding
recogniser without touching the planner or executor.

Supported intents (Phase 2):
    exit, help, time, date, screenshot,
    lock, sleep, shutdown, restart, cancel_shutdown,
    volume_up, volume_down, mute_volume, unmute_volume, volume_set,
    minimize_all, close_window, switch_window,
    media_play_pause, media_next, media_prev,
    open, search_web, search_youtube, type_text, say, math
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Number parsing
# ---------------------------------------------------------------------------

_WORD_TO_NUMBER = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90,
    "hundred": 100, "thousand": 1_000,
    "million": 1_000_000, "billion": 1_000_000_000,
}


def _words_to_number(tokens: list[str]) -> Optional[int]:
    if not tokens:
        return None
    total = 0
    current = 0
    for raw in tokens:
        tok = raw.lower().strip(",")
        if tok == "and":
            continue
        if tok not in _WORD_TO_NUMBER:
            return None
        val = _WORD_TO_NUMBER[tok]
        if val == 100:
            current = max(current, 1) * 100
        elif val >= 1_000:
            current = max(current, 1) * val
            total += current
            current = 0
        else:
            current += val
    return total + current


def parse_number(token: str) -> Optional[float]:
    token = token.strip().replace(",", "")
    if not token:
        return None
    try:
        return float(token)
    except ValueError:
        pass
    val = _words_to_number(token.split())
    return float(val) if val is not None else None


# ---------------------------------------------------------------------------
# Intent schema
# ---------------------------------------------------------------------------

@dataclass
class Intent:
    name: str
    entities: dict[str, Any] = field(default_factory=dict)
    raw: str = ""


# ---------------------------------------------------------------------------
# Recogniser
# ---------------------------------------------------------------------------

class IntentRecognizer:
    _OP_ALIASES = {
        "multiply": "multiply", "times": "multiply", "multiplied by": "multiply",
        "add": "add", "plus": "add",
        "subtract": "subtract", "minus": "subtract",
        "divide": "divide", "divided by": "divide",
    }

    _SIMPLE_INTENTS = [
        (r"\b(exit|quit|goodbye|shut\s*down\s+agent|close\s+agent|turn\s+off\s+agent)\b", "exit"),
        (r"^\s*(hello|hi|hey|hi there|hello there|hey there|good\s+(morning|afternoon|evening))\b", "greet"),
        (r"\b(help|what\s+can\s+you\s+do|show\s+(?:me\s+)?commands)\b", "help"),
        (r"\b(what(?:'s|\s+is)?\s+the\s+time|what\s+time\s+is\s+it|current\s+time|tell\s+me\s+the\s+time)\b", "time"),
        (r"\b(what(?:'s|\s+is)?\s+(?:the\s+)?date|what\s+day\s+is\s+it|today'?s\s+date|current\s+date)\b", "date"),
        (r"\btake\s+(?:a\s+)?(?:screen\s*shot|screenshot)\b|\bcapture\s+(?:my\s+)?screen\b", "screenshot"),
        (r"\block\s+(?:my\s+)?(?:pc|computer|screen|laptop|system)\b", "lock"),
        (r"\b(?:put\s+(?:my\s+)?(?:pc|computer|laptop)\s+to\s+sleep|go\s+to\s+sleep|sleep\s+mode)\b", "sleep"),
        (r"\b(?:shut\s*down|power\s*off|turn\s+off)\s+(?:my\s+)?(?:pc|computer|laptop|system)\b", "shutdown"),
        (r"\brestart\s+(?:my\s+)?(?:pc|computer|laptop|system)\b|\breboot\b", "restart"),
        (r"\bcancel\s+shut\s*down\b|\babort\s+shutdown\b", "cancel_shutdown"),
        (r"\bmute(?:\s+volume)?\b", "mute_volume"),
        (r"\bunmute(?:\s+volume)?\b", "unmute_volume"),
        (r"\bvolume\s+(?:up|increase|louder|higher)\b|\bincrease\s+volume\b|\bturn\s+up\s+(?:the\s+)?volume\b", "volume_up"),
        (r"\bvolume\s+(?:down|decrease|quieter|lower)\b|\bdecrease\s+volume\b|\bturn\s+down\s+(?:the\s+)?volume\b", "volume_down"),
        (r"\b(?:minimize\s+(?:all|everything|windows?)|show\s+desktop|hide\s+all)\b", "minimize_all"),
        (r"\bclose\s+(?:this\s+)?(?:window|tab|app|application)\b", "close_window"),
        (r"\bswitch\s+(?:window|app|application|tab)\b", "switch_window"),
        (r"\b(?:play|pause)\s+(?:music|media|song|video)\b", "media_play_pause"),
        (r"\bnext\s+(?:song|track|video)\b", "media_next"),
        (r"\bprevious\s+(?:song|track|video)\b|\bprev\s+(?:song|track)\b", "media_prev"),
    ]

    def __init__(self) -> None:
        self._simple: list[tuple[re.Pattern[str], str]] = [
            (re.compile(p, re.I), n) for p, n in self._SIMPLE_INTENTS
        ]
        self._math_pattern = re.compile(
            r"(multiplied by|divided by|multiply|divide|subtract|add|times|plus|minus)"
            r"\s+(.+?)\s+(?:and|by|with|\+|-|\*|/|x)\s+(.+)",
            re.I,
        )
        self._volume_set = re.compile(r"\bset\s+(?:the\s+)?volume\s+(?:to\s+)?(\d{1,3})\b", re.I)
        self._type_text  = re.compile(r"^(?:type|write)\s+(.+)$", re.I)
        self._say_text   = re.compile(r"^(?:say|repeat)\s+(.+)$", re.I)
        self._search_yt  = re.compile(r"^(?:play\s+|search\s+)?(?:on\s+)?youtube\s+(?:for\s+)?(.+)$", re.I)
        self._search_web = re.compile(r"^(?:search|google|look\s+up|find)\s+(?:for\s+)?(.+)$", re.I)
        self._open_tgt   = re.compile(r"^(?:open|launch|start|run|go\s+to|show(?:\s+me)?)\s+(.+?)(?:\s+(?:folder|app|website|site))?$", re.I)

    def recognize(self, text: str) -> Intent:
        raw = text
        text = (text or "").strip().lower()
        if not text:
            return Intent("unknown", raw=raw)

        for pat, name in self._simple:
            if pat.search(text):
                return Intent(name, raw=raw)

        m = self._volume_set.search(text)
        if m:
            return Intent("volume_set", {"level": int(m.group(1))}, raw=raw)

        m = self._math_pattern.search(text)
        if m:
            op = self._OP_ALIASES.get(m.group(1).lower(), m.group(1).lower())
            a = parse_number(m.group(2))
            b = parse_number(m.group(3))
            if a is not None and b is not None:
                return Intent("math", {"op": op, "a": a, "b": b}, raw=raw)

        m = self._type_text.match(text)
        if m:
            return Intent("type_text", {"text": m.group(1).strip()}, raw=raw)

        m = self._say_text.match(text)
        if m:
            return Intent("say", {"text": m.group(1).strip()}, raw=raw)

        m = self._search_yt.match(text)
        if m:
            return Intent("search_youtube", {"query": m.group(1).strip()}, raw=raw)

        m = self._search_web.match(text)
        if m:
            return Intent("search_web", {"query": m.group(1).strip()}, raw=raw)

        m = self._open_tgt.match(text)
        if m:
            return Intent("open", {"target": m.group(1).strip()}, raw=raw)

        return Intent("unknown", raw=raw)
