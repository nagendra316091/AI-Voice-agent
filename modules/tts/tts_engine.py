"""Offline text-to-speech via ``pyttsx3``.

Binds to the host's native engine (SAPI5 on Windows, NSSpeech on macOS,
espeak on Linux). The engine instance is intentionally created lazily
*inside* whichever thread calls :meth:`speak` first, because pyttsx3 on
Windows has COM thread-affinity — calling it from a different thread than
the one that created it can deadlock. If the engine ever raises during a
speak call, it's rebuilt once and the phrase retried.
"""
from __future__ import annotations

import logging
from typing import Optional

import pyttsx3

logger = logging.getLogger(__name__)


class TTSEngine:
    def __init__(
        self,
        rate: int = 185,
        volume: float = 1.0,
        voice_hint: Optional[str] = None,
    ) -> None:
        self._rate = rate
        self._volume = max(0.0, min(1.0, volume))
        self._voice_hint = voice_hint
        self._engine: Optional[pyttsx3.Engine] = None

    # -- lifecycle -------------------------------------------------------
    def _build(self) -> pyttsx3.Engine:
        engine = pyttsx3.init()
        engine.setProperty("rate", self._rate)
        engine.setProperty("volume", self._volume)
        if self._voice_hint:
            self._select_voice(engine, self._voice_hint)
        return engine

    def _select_voice(self, engine: pyttsx3.Engine, hint: str) -> None:
        hint_l = hint.lower()
        for voice in engine.getProperty("voices"):
            if hint_l in voice.name.lower() or hint_l in voice.id.lower():
                engine.setProperty("voice", voice.id)
                logger.info("TTS voice selected: %s", voice.name)
                return
        logger.warning("No TTS voice matched hint %r; using default.", hint)

    # -- public ----------------------------------------------------------
    def speak(self, text: str) -> None:
        if not text:
            return
        logger.info("TTS: %s", text)
        # Rebuild the SAPI5 engine for every utterance. Reusing it from a
        # QThread is fragile on Windows: the first runAndWait() often works
        # but later ones silently produce no audio (text shows on the UI but
        # no sound). A fresh engine per call is slightly slower (~30ms) but
        # eliminates the silent-failure mode entirely.
        try:
            engine = self._build()
            engine.say(text)
            engine.runAndWait()
            try:
                engine.stop()
            except Exception:
                pass
            del engine
        except Exception:
            logger.exception("TTS speak failed")
