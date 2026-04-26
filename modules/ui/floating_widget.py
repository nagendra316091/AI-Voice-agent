"""Always-on-top floating bar UI.

A compact, draggable pill that sits above every other window. Shows the
current agent state (idle / listening / thinking / speaking / muted) via an
animated orb, plus the last transcript and the last agent response. Has two
buttons: mute/unmute and close.
"""
from __future__ import annotations

import math

from PyQt6.QtCore import QPoint, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


STATE_COLORS: dict[str, QColor] = {
    "idle":      QColor(110, 110, 130),
    "listening": QColor(60, 200, 130),
    "thinking":  QColor(240, 190, 40),
    "speaking":  QColor(80, 160, 255),
    "muted":     QColor(210, 80, 90),
}

STATE_LABELS: dict[str, str] = {
    "idle":      "Idle",
    "listening": "Listening...",
    "thinking":  "Thinking...",
    "speaking":  "Speaking...",
    "muted":     "Muted",
}


class StatusOrb(QWidget):
    """Animated circle that breathes when the agent is active."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(42, 42)
        self._state = "idle"
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)  # ~30 FPS

    def set_state(self, state: str) -> None:
        if state not in STATE_COLORS:
            state = "idle"
        self._state = state
        self.update()

    def _tick(self) -> None:
        self._phase = (self._phase + 0.08) % (2 * math.pi)
        if self._state in ("listening", "speaking", "thinking"):
            self.update()

    def paintEvent(self, event) -> None:  # noqa: ARG002
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        base = STATE_COLORS[self._state]
        rect = QRectF(self.rect()).adjusted(5, 5, -5, -5)

        # Pulsing halo
        if self._state in ("listening", "speaking"):
            amp = 3 + 3 * math.sin(self._phase * 2)
            halo = QColor(base)
            halo.setAlpha(90)
            p.setBrush(halo)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(rect.adjusted(-amp, -amp, amp, amp))

        # Core orb with gradient
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, base.lighter(140))
        grad.setColorAt(1.0, base.darker(130))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(rect)

        # Highlight
        hl = QColor(255, 255, 255, 90)
        p.setBrush(hl)
        p.drawEllipse(rect.adjusted(rect.width() * 0.15,
                                    rect.height() * 0.1,
                                    -rect.width() * 0.55,
                                    -rect.height() * 0.55))


class FloatingAgentBar(QWidget):
    """Frameless always-on-top pill showing agent state + transcript."""

    mute_toggled = pyqtSignal(bool)
    closed = pyqtSignal()

    def __init__(self, opacity: float = 0.95) -> None:
        super().__init__()
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # no taskbar icon
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(opacity)
        self.resize(480, 96)

        self._muted = False
        self._drag_offset: QPoint | None = None

        self._build_ui()
        self._place_top_center()

    # -- UI construction -------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 10, 16, 10)
        root.setSpacing(2)

        top = QHBoxLayout()
        top.setSpacing(10)

        self.orb = StatusOrb()
        top.addWidget(self.orb)

        self.status_label = QLabel(STATE_LABELS["listening"])
        status_font = QFont()
        status_font.setPointSize(10)
        status_font.setBold(True)
        self.status_label.setFont(status_font)
        self.status_label.setStyleSheet("color: #e8e8f0;")
        top.addWidget(self.status_label, 1)

        self.mute_btn = self._make_button("🎙", self._toggle_mute, tip="Mute")
        top.addWidget(self.mute_btn)

        self.close_btn = self._make_button("✕", self._on_close, tip="Close agent")
        top.addWidget(self.close_btn)

        root.addLayout(top)

        self.transcript_label = QLabel("")
        self.transcript_label.setStyleSheet(
            "color: #9ddcff; font-size: 11px; font-style: italic;"
        )
        self.transcript_label.setWordWrap(True)
        root.addWidget(self.transcript_label)

        self.response_label = QLabel("")
        self.response_label.setStyleSheet("color: #f0f0f0; font-size: 11px;")
        self.response_label.setWordWrap(True)
        root.addWidget(self.response_label)

    def _make_button(self, text: str, on_click, tip: str = "") -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(30, 30)
        btn.setToolTip(tip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton {"
            "  background: rgba(255,255,255,25); color: #eee;"
            "  border: 0; border-radius: 15px; font-size: 13px;"
            "} QPushButton:hover { background: rgba(255,255,255,55); }"
        )
        btn.clicked.connect(on_click)
        return btn

    def _place_top_center(self) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.x() + (screen.width() - self.width()) // 2
        y = screen.y() + 20
        self.move(x, y)

    # -- painting (rounded translucent background) -----------------------
    def paintEvent(self, event) -> None:  # noqa: ARG002
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 18, 18)

        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor(32, 32, 48, 235))
        grad.setColorAt(1.0, QColor(20, 20, 30, 235))
        p.fillPath(path, QBrush(grad))

        p.setPen(QPen(QColor(255, 255, 255, 45), 1))
        p.drawPath(path)

    # -- drag-to-move ----------------------------------------------------
    def mousePressEvent(self, ev) -> None:
        if ev.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = ev.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, ev) -> None:
        if self._drag_offset is not None and ev.buttons() & Qt.MouseButton.LeftButton:
            self.move(ev.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, ev) -> None:  # noqa: ARG002
        self._drag_offset = None

    # -- buttons ---------------------------------------------------------
    def _toggle_mute(self) -> None:
        self._muted = not self._muted
        self.mute_btn.setText("🔇" if self._muted else "🎙")
        self.mute_btn.setToolTip("Unmute" if self._muted else "Mute")
        self.mute_toggled.emit(self._muted)
        self.set_state("muted" if self._muted else "listening")

    def _on_close(self) -> None:
        self.closed.emit()
        self.close()

    # -- public slots ----------------------------------------------------
    def set_state(self, state: str) -> None:
        self.orb.set_state(state)
        self.status_label.setText(STATE_LABELS.get(state, state))

    def set_transcript(self, text: str) -> None:
        self.transcript_label.setText(f"you: {text}")

    def set_response(self, text: str) -> None:
        self.response_label.setText(f"agent: {text}")
