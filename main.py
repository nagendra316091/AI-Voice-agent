"""Voice AI Agent — entry point.

Launches the Qt application with a frameless always-on-top floating bar
and wires it to a background :class:`AgentWorker` that runs the full
STT -> NLP -> Planner -> Executor -> TTS loop.

    python main.py
"""
from __future__ import annotations

import logging
import sys

from PyQt6.QtCore import QThread, Qt
from PyQt6.QtWidgets import QApplication

from config import settings
from modules.executor import Executor
from modules.memory import History
from modules.nlp import IntentRecognizer
from modules.planner import Planner
from modules.stt import VoskSTT, WhisperSTT
from modules.ui import AgentWorker, FloatingAgentBar


def setup_logging() -> logging.Logger:
    settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-5s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(settings.LOGS_DIR / "agent.log", encoding="utf-8"),
            logging.StreamHandler(stream=sys.stdout),
        ],
    )
    return logging.getLogger("voice_agent")


def main() -> int:
    log = setup_logging()
    log.info("Starting Voice AI Agent")

    # High-DPI: Qt6 handles this automatically, but be explicit about fractional
    # scaling so the pill looks sharp on 125% / 150% DPI laptop screens.
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    # Build pipeline components on the main thread. Only TTS is deferred to
    # the worker thread (it lives inside AgentWorker.run()).
    try:
        backend = (settings.STT_BACKEND or "whisper").lower()
        if backend == "whisper":
            log.info("STT backend: Whisper (%s)", settings.WHISPER_MODEL_SIZE)
            stt = WhisperSTT(
                model_size=settings.WHISPER_MODEL_SIZE,
                compute_type=settings.WHISPER_COMPUTE_TYPE,
                sample_rate=settings.SAMPLE_RATE,
            )
        else:
            log.info("STT backend: Vosk (%s)", settings.VOSK_MODEL_NAME)
            stt = VoskSTT(
                model_path=settings.VOSK_MODEL_PATH,
                sample_rate=settings.SAMPLE_RATE,
                blocksize=settings.AUDIO_BLOCKSIZE,
            )
    except FileNotFoundError as exc:
        log.error(str(exc))
        print(str(exc))
        return 2

    nlp = IntentRecognizer()
    planner = Planner()
    executor = Executor(settings.RESULT_FILE, settings.SCREENSHOT_DIR)
    history = History(settings.HISTORY_FILE)

    # UI
    bar = FloatingAgentBar(opacity=settings.UI_OPACITY)
    bar.show()

    # Background worker
    worker = AgentWorker(stt, nlp, planner, executor, history)
    thread = QThread()
    worker.moveToThread(thread)

    # Wire signals
    worker.transcript.connect(bar.set_transcript)
    worker.response.connect(bar.set_response)
    worker.state.connect(bar.set_state)
    worker.error.connect(lambda msg: log.warning("Agent: %s", msg))
    worker.finished.connect(thread.quit)
    worker.finished.connect(app.quit)

    bar.mute_toggled.connect(worker.set_muted)
    bar.closed.connect(worker.stop)
    app.aboutToQuit.connect(worker.stop)

    thread.started.connect(worker.run)
    thread.start()

    rc = app.exec()
    worker.stop()
    thread.quit()
    thread.wait(3000)
    log.info("Voice AI Agent exited (rc=%s)", rc)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
