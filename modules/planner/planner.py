"""Translate a recognised :class:`Intent` into an executable :class:`Task`.

The planner stays thin: it passes entity params through and attaches a
fallback spoken phrase. The executor still owns the final word, so it can
override ``speak`` with dynamic responses (e.g. the result of a calculation).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from modules.nlp.intent_recognizer import Intent

logger = logging.getLogger(__name__)


@dataclass
class Task:
    action: str
    params: dict[str, Any] = field(default_factory=dict)
    speak: Optional[str] = None


# Static speak-fallbacks keyed by intent name. Missing keys are fine — the
# executor will fill one in from the action handler.
_SPEAK_DEFAULTS: dict[str, str] = {
    "exit":              "Goodbye.",
    "greet":             "Hi! How can I help?",
    "help":              "I can open apps, folders, and websites, search the web, do maths, "
                         "control volume and media, lock or sleep the computer, take screenshots, "
                         "type for you, and more. Just ask.",
    "mute_volume":       "Muted.",
    "unmute_volume":     "Unmuted.",
    "volume_up":         "Volume up.",
    "volume_down":       "Volume down.",
    "minimize_all":      "Showing desktop.",
    "close_window":      "Closing window.",
    "switch_window":     "Switching window.",
    "media_play_pause":  "Toggled playback.",
    "media_next":        "Next track.",
    "media_prev":        "Previous track.",
    "lock":              "Locking the screen.",
    "cancel_shutdown":   "Shutdown cancelled.",
}


class Planner:
    def plan(self, intent: Intent) -> Task:
        logger.debug("Planning intent=%s entities=%s", intent.name, intent.entities)
        if intent.name == "unknown":
            return Task("noop")  # silent noop — don't nag the user
        speak = _SPEAK_DEFAULTS.get(intent.name)
        return Task(intent.name, params=dict(intent.entities), speak=speak)
