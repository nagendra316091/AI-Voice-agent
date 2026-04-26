"""Offline speech-to-text backed by Vosk.

Streams 16-bit mono PCM from the default microphone into a ``KaldiRecognizer``
and returns the first *final* utterance. ``listen_once`` accepts a
``threading.Event`` so the agent worker can interrupt a blocked listen call
(e.g. when the UI is closed or the mic is muted).
"""
from __future__ import annotations

import json
import logging
import queue
import threading
from pathlib import Path
from typing import Optional

import sounddevice as sd
from vosk import KaldiRecognizer, Model, SetLogLevel

SetLogLevel(-1)
logger = logging.getLogger(__name__)


class VoskSTT:
    def __init__(
        self,
        model_path: Path,
        sample_rate: int = 16000,
        blocksize: int = 8000,
        device: Optional[int] = None,
    ) -> None:
        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(
                f"Vosk model not found at: {model_path}\n"
                "Run `python scripts/download_model.py` first."
            )
        logger.info("Loading Vosk model from %s", model_path)
        self._model = Model(str(model_path))
        self._sample_rate = sample_rate
        self._blocksize = blocksize
        self._device = device
        self._audio_q: queue.Queue[bytes] = queue.Queue()

    def _audio_callback(self, indata, frames, time_info, status) -> None:  # noqa: ARG002
        if status:
            logger.debug("Audio input status: %s", status)
        self._audio_q.put(bytes(indata))

    def _drain(self) -> None:
        while not self._audio_q.empty():
            try:
                self._audio_q.get_nowait()
            except queue.Empty:
                break

    def listen_once(self, stop_event: Optional[threading.Event] = None) -> str:
        """Block until one non-empty final utterance is recognised.

        If ``stop_event`` is provided and becomes set, returns an empty string
        promptly so the caller can shut the loop down.
        """
        recognizer = KaldiRecognizer(self._model, self._sample_rate)
        recognizer.SetWords(True)
        self._drain()

        with sd.RawInputStream(
            samplerate=self._sample_rate,
            blocksize=self._blocksize,
            dtype="int16",
            channels=1,
            device=self._device,
            callback=self._audio_callback,
        ):
            while True:
                if stop_event is not None and stop_event.is_set():
                    return ""
                try:
                    chunk = self._audio_q.get(timeout=0.1)
                except queue.Empty:
                    continue
                if recognizer.AcceptWaveform(chunk):
                    payload = json.loads(recognizer.Result())
                    text = (payload.get("text") or "").strip()
                    if text:
                        return text
