"""Offline speech-to-text backed by faster-whisper.

Drop-in replacement for :class:`VoskSTT`. Same constructor surface and
``listen_once(stop_event)`` semantics, so the rest of the agent does not
need to change.

Pipeline:
    1. Capture mono int16 PCM at 16 kHz from the default microphone.
    2. Use a simple energy-based VAD to detect the start of speech and the
       end-of-utterance silence.
    3. Hand the buffered float32 PCM to faster-whisper for transcription.
    4. Return the first non-empty utterance.

The model is downloaded automatically by faster-whisper on first use and
cached under ``%USERPROFILE%/.cache/huggingface``.
"""
from __future__ import annotations

import logging
import queue
import sys
import threading
import time
import types
from typing import Optional

import numpy as np
import sounddevice as sd

# faster-whisper eagerly imports `av` (PyAV) for its decode_audio() helper.
# We never call that helper — we feed the model numpy arrays directly — but
# the import still happens at module load. On Windows machines with
# Application Control blocking PyAV's bundled DLLs the import fails. Stub
# the module before the real import so loading succeeds.
if "av" not in sys.modules:
    _av = types.ModuleType("av")
    _av_audio = types.ModuleType("av.audio")
    _av_audio_resampler = types.ModuleType("av.audio.resampler")
    _av_audio_resampler.AudioResampler = object  # placeholder
    _av_audio.resampler = _av_audio_resampler
    _av.audio = _av_audio
    sys.modules["av"] = _av
    sys.modules["av.audio"] = _av_audio
    sys.modules["av.audio.resampler"] = _av_audio_resampler

from faster_whisper import WhisperModel  # noqa: E402

logger = logging.getLogger(__name__)


class WhisperSTT:
    def __init__(
        self,
        model_size: str = "base.en",
        sample_rate: int = 16000,
        blocksize: int = 1600,                     # 100 ms frames
        device: Optional[int] = None,
        compute_type: str = "int8",                # CPU-friendly default
        # VAD knobs — tune if you find it too aggressive / too lazy.
        # 1200 keeps quiet keyboard / fan noise out so Whisper doesn't
        # hallucinate plausible-sounding English over near-silence.
        speech_rms_threshold: float = 1200.0,      # int16 RMS for "is speech"
        min_speech_ms: int = 400,                  # ignore blips shorter than this
        end_silence_ms: int = 700,                 # silence that ends the utterance
        max_utterance_ms: int = 10_000,            # hard stop
        no_speech_threshold: float = 0.6,          # Whisper: drop low-confidence text
        # Compatibility with the VoskSTT constructor signature so main.py can
        # pass the same kwargs without branching.
        model_path: Optional[object] = None,       # accepted, ignored
    ) -> None:
        logger.info("Loading faster-whisper model: %s (compute_type=%s)",
                    model_size, compute_type)
        # device="cpu" is the safe default; CUDA users can edit this line.
        self._model = WhisperModel(model_size, device="cpu", compute_type=compute_type)
        self._sample_rate = sample_rate
        self._blocksize = blocksize
        self._device = device
        self._audio_q: queue.Queue[bytes] = queue.Queue()

        self._speech_rms_threshold = speech_rms_threshold
        self._min_speech_frames = max(1, min_speech_ms * sample_rate // 1000 // blocksize)
        self._end_silence_frames = max(1, end_silence_ms * sample_rate // 1000 // blocksize)
        self._max_utterance_frames = max_utterance_ms * sample_rate // 1000 // blocksize
        self._no_speech_threshold = no_speech_threshold

        # Common Whisper hallucinations on silence — drop these outright.
        # Whisper was trained on YouTube + podcast subtitles, so on quiet
        # audio it pattern-matches to canned closing phrases.
        self._hallucinations = {
            "thank you.", "thanks for watching.", "thank you for watching.",
            "thanks for watching!", "you", "bye.", "bye-bye.",
            "subtitles by the amara.org community",
            "we'll see you then, take care.", "we'll see you then.",
            "take care.", "take care!", "see you next time.",
            "see you in the next video.", "see you later.",
            "and then we'll have more today.",
            ".", "..", "...", "?", "!",
        }
        # Substrings that mark an utterance as conversational filler /
        # hallucination, regardless of surrounding text.
        self._hallucination_substrings = (
            "subtitles by", "amara.org",
            "thanks for watching", "thank you for watching",
            "see you next time", "see you in the next",
            "subscribe to", "like and subscribe",
        )

    # -- audio plumbing --------------------------------------------------
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

    @staticmethod
    def _rms(int16_buf: bytes) -> float:
        if not int16_buf:
            return 0.0
        arr = np.frombuffer(int16_buf, dtype=np.int16).astype(np.float32)
        if arr.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(arr * arr)))

    # -- public ----------------------------------------------------------
    def listen_once(self, stop_event: Optional[threading.Event] = None) -> str:
        """Block until one non-empty utterance is recognised, return it."""
        self._drain()
        speech_frames: list[bytes] = []
        silence_run = 0
        in_speech = False
        total_frames = 0

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

                rms = self._rms(chunk)
                is_speech = rms >= self._speech_rms_threshold

                if not in_speech:
                    if is_speech:
                        in_speech = True
                        speech_frames.append(chunk)
                        silence_run = 0
                        total_frames = 1
                    # else: idle silence, keep waiting
                    continue

                # in_speech == True: keep collecting until end-silence threshold
                speech_frames.append(chunk)
                total_frames += 1
                if is_speech:
                    silence_run = 0
                else:
                    silence_run += 1

                if (silence_run >= self._end_silence_frames
                        and total_frames >= self._min_speech_frames):
                    break
                if total_frames >= self._max_utterance_frames:
                    logger.info("Max utterance length reached, transcribing.")
                    break

        if not speech_frames:
            return ""

        pcm_int16 = np.frombuffer(b"".join(speech_frames), dtype=np.int16)
        pcm_float32 = pcm_int16.astype(np.float32) / 32768.0

        t0 = time.perf_counter()
        segments, info = self._model.transcribe(
            pcm_float32,
            language="en",
            beam_size=1,
            vad_filter=False,                          # already VAD'd above
            condition_on_previous_text=False,
            no_speech_threshold=self._no_speech_threshold,
            log_prob_threshold=-1.0,                    # drop low-confidence
            compression_ratio_threshold=2.4,            # drop repetitive babble
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info("Whisper: %.0fms no_speech=%.2f -> %r",
                    elapsed_ms, getattr(info, "no_speech_prob", -1.0), text)

        # Whisper "hallucinates" canned phrases on silence — discard them.
        lowered = text.lower().strip()
        if lowered in self._hallucinations:
            logger.info("Discarding hallucination (exact): %r", text)
            return ""
        if any(sub in lowered for sub in self._hallucination_substrings):
            logger.info("Discarding hallucination (substring): %r", text)
            return ""
        return text
