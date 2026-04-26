"""LLM-backed intent recognition fallback (Groq, free tier).

The rule-based :class:`IntentRecognizer` is fast and offline, but it only
matches phrasings it knows. When the regex returns ``unknown`` (e.g.
"could you fire up notepad for me", "show my downloads folder"), this
fallback asks a small Llama model to map the utterance onto our existing
intent schema.

If ``GROQ_API_KEY`` is not set, or the call fails, the fallback returns
``None`` and the agent silently falls back to its existing behavior.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # pragma: no cover
    pass

try:
    from groq import Groq
    _HAS_GROQ = True
except ImportError:  # pragma: no cover
    _HAS_GROQ = False

from .intent_recognizer import Intent

logger = logging.getLogger(__name__)


# Compact schema description shown to the model. Keep this in sync with the
# intents the executor actually handles (modules/executor/executor.py).
_SYSTEM_PROMPT = """You are an intent classifier for a Windows voice agent.
Map the user's utterance to ONE intent and return a single line of JSON.

Intents and their entities:
- open                 {"target": "<app | website | folder name>"}
- search_web           {"query": "<text>"}
- search_youtube       {"query": "<text>"}
- type_text            {"text": "<text>"}
- say                  {"text": "<text>"}
- math                 {"op": "add|subtract|multiply|divide", "a": <number>, "b": <number>}
- time                 {}
- date                 {}
- screenshot           {}
- lock                 {}
- sleep                {}
- shutdown             {}
- restart              {}
- cancel_shutdown      {}
- volume_up            {}
- volume_down          {}
- volume_set           {"level": <0-100>}
- mute_volume          {}
- unmute_volume        {}
- minimize_all         {}
- close_window         {}
- switch_window        {}
- media_play_pause     {}
- media_next           {}
- media_prev           {}
- help                 {}
- exit                 {}
- unknown              {}

Rules:
- "browser", "web browser", "default browser" -> open with target "browser".
- App names you should normalise: "notepad", "calculator", "chrome", "edge",
  "firefox", "vs code", "explorer", "spotify", "word", "excel".
- The transcript may contain speech-to-text mistakes. Pick the closest
  reasonable intent. If genuinely nothing fits, return {"name": "unknown"}.
- Output JSON ONLY. No prose, no markdown, no code fences.

Format: {"name": "<intent>", "entities": { ... }}"""


class LLMIntentRecognizer:
    """Calls Groq once per ambiguous utterance, returns an Intent or None."""

    def __init__(self, model: str = "llama-3.1-8b-instant") -> None:
        self._model = model
        self._client: Optional[Groq] = None
        if not _HAS_GROQ:
            logger.info("groq SDK not installed; LLM intent disabled.")
            return
        api_key = os.environ.get("GROQ_API_KEY", "").strip()
        if not api_key:
            logger.info("GROQ_API_KEY not set; LLM intent disabled.")
            return
        try:
            self._client = Groq(api_key=api_key)
            logger.info("LLM intent fallback: Groq %s", self._model)
        except Exception:
            logger.exception("Groq client init failed; LLM intent disabled.")
            self._client = None

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def recognize(self, text: str) -> Optional[Intent]:
        if self._client is None or not text:
            return None
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                temperature=0.0,
                max_tokens=120,
                response_format={"type": "json_object"},
            )
            content = (resp.choices[0].message.content or "").strip()
            logger.info("LLM intent raw: %s", content)
        except Exception as e:
            logger.warning("LLM intent call failed: %s", e)
            return None

        try:
            data = json.loads(content)
            name = str(data.get("name") or "unknown").strip().lower()
            entities = data.get("entities") or {}
            if not isinstance(entities, dict):
                entities = {}
            if name == "unknown":
                return None
            return Intent(name=name, entities=entities, raw=text)
        except (ValueError, TypeError) as e:
            logger.warning("LLM intent JSON parse failed: %s | %r", e, content)
            return None
