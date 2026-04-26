"""Background worker that runs the STT -> NLP -> Executor -> TTS loop.

Lives on a :class:`QThread` so the Qt UI stays responsive. The TTS engine is
constructed inside :meth:`run` — pyttsx3 / SAPI5 has COM thread affinity and
must be used on the same thread that built it.
"""
from __future__ import annotations

import logging
import threading
from typing import Iterable

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from config import settings
from modules.executor import Executor
from modules.memory import History
from modules.nlp import IntentRecognizer, LLMIntentRecognizer
from modules.planner import Planner
from modules.stt import VoskSTT
from modules.tts import TTSEngine

logger = logging.getLogger(__name__)


def _strip_wake_word(text: str, wake_words: Iterable[str]) -> str | None:
    """Return text with wake-word removed, or ``None`` if none matched."""
    t = text.strip().lower()
    for w in sorted(wake_words, key=len, reverse=True):
        wl = w.lower()
        if t.startswith(wl):
            stripped = text.strip()[len(w):].strip(" ,.?!")
            return stripped if stripped else text.strip()
    return None


class AgentWorker(QObject):
    transcript = pyqtSignal(str)
    response   = pyqtSignal(str)
    state      = pyqtSignal(str)   # idle / listening / thinking / speaking / muted
    error      = pyqtSignal(str)
    finished   = pyqtSignal()

    def __init__(
        self,
        stt: VoskSTT,
        nlp: IntentRecognizer,
        planner: Planner,
        executor: Executor,
        history: History,
    ) -> None:
        super().__init__()
        self._stt = stt
        self._nlp = nlp
        self._planner = planner
        self._executor = executor
        self._history = history
        self._stop_event = threading.Event()
        self._muted = False
        # Optional LLM fallback for utterances the regex doesn't catch.
        self._llm_nlp: LLMIntentRecognizer | None = None
        if getattr(settings, "LLM_INTENT_ENABLED", False):
            llm = LLMIntentRecognizer(model=getattr(settings, "LLM_MODEL",
                                                    "llama-3.1-8b-instant"))
            if llm.enabled:
                self._llm_nlp = llm

    # -- thread-safe setters called from UI thread -----------------------
    @pyqtSlot(bool)
    def set_muted(self, muted: bool) -> None:
        self._muted = muted
        logger.info("Agent mic %s", "muted" if muted else "unmuted")

    @pyqtSlot()
    def stop(self) -> None:
        logger.info("Agent stop requested")
        self._stop_event.set()

    # -- the loop --------------------------------------------------------
    @pyqtSlot()
    def run(self) -> None:
        # TTS built in-thread (pyttsx3 / SAPI5 thread affinity).
        tts = TTSEngine(
            rate=settings.TTS_RATE,
            volume=settings.TTS_VOLUME,
            voice_hint=settings.TTS_VOICE_HINT,
        )
        try:
            tts.speak("Voice agent ready. How can I help?")
        except Exception:  # pragma: no cover
            logger.exception("Initial TTS greeting failed")

        while not self._stop_event.is_set():
            if self._muted:
                self.state.emit("muted")
                self._stop_event.wait(0.2)
                continue

            self.state.emit("listening")
            try:
                transcript = self._stt.listen_once(self._stop_event)
            except Exception as e:
                logger.exception("STT failure")
                self.error.emit(f"STT error: {e}")
                self._stop_event.wait(0.5)
                continue
            if self._stop_event.is_set():
                break
            if not transcript:
                continue

            # Wake-word gate
            if settings.REQUIRE_WAKE_WORD:
                stripped = _strip_wake_word(transcript, settings.WAKE_WORDS)
                if stripped is None:
                    logger.debug("No wake word in %r — ignoring.", transcript)
                    continue
                transcript = stripped

            self.transcript.emit(transcript)
            self.state.emit("thinking")

            intent = self._nlp.recognize(transcript)
            if intent.name == "unknown" and self._llm_nlp is not None:
                llm_intent = self._llm_nlp.recognize(transcript)
                if llm_intent is not None:
                    intent = llm_intent
                    logger.info("LLM resolved intent=%s entities=%s",
                                intent.name, intent.entities)
            logger.info("Intent=%s entities=%s", intent.name, intent.entities)

            task = self._planner.plan(intent)
            result = self._executor.execute(task)

            speak_text = result.get("speak") or task.speak or result.get("message", "")
            if speak_text:
                self.response.emit(speak_text)
                self.state.emit("speaking")
                try:
                    tts.speak(speak_text)
                except Exception as e:
                    logger.exception("TTS failed")
                    self.error.emit(f"TTS error: {e}")

            try:
                self._history.add(transcript, intent.name, result)
            except Exception:
                logger.exception("History write failed")

            if result.get("exit"):
                break

        self.state.emit("idle")
        self.finished.emit()
        logger.info("Agent worker stopped.")
