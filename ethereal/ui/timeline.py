"""
Timeline — Transport bar with play controls, seek slider, and song info.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QSlider, QLabel,
    QSizePolicy, QFrame,
)


# ---------------------------------------------------------------------------
# Stylesheet constants
# ---------------------------------------------------------------------------

_ACCENT = "#00d2c8"
_BG = "#0d0d13"
_BG_LIGHTER = "#181824"
_BORDER = "#29293a"
_TEXT = "#e6e6f0"
_TEXT_DIM = "#8e8ea0"

_BUTTON_STYLE = f"""
QPushButton {{
    background: {_BG_LIGHTER};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 15px;
    font-weight: 700;
}}
QPushButton:hover {{
    background: #232334;
    border-color: {_ACCENT};
    color: {_ACCENT};
}}
QPushButton:pressed {{
    background: {_ACCENT};
    color: #081111;
}}
"""

_SLIDER_STYLE = f"""
QSlider::groove:horizontal {{
    background: {_BG_LIGHTER};
    height: 6px;
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {_ACCENT};
    width: 14px;
    height: 14px;
    margin: -4px 0;
    border-radius: 7px;
}}
QSlider::sub-page:horizontal {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {_ACCENT}, stop:1 rgba(0, 210, 200, 140)
    );
    border-radius: 3px;
}}
"""

_INFO_LABEL_STYLE = f"""
QLabel {{
    color: {_TEXT_DIM};
    font-size: 11px;
    padding: 0 4px;
}}
"""

_TIME_LABEL_STYLE = f"""
QLabel {{
    color: {_TEXT};
    font-size: 11px;
    font-family: 'Consolas', 'Cascadia Mono', monospace;
    padding: 0 6px;
}}
"""

_SEPARATOR_STYLE = f"""
QFrame {{
    background: rgba(255, 255, 255, 25);
    max-width: 1px;
    margin: 8px 4px;
}}
"""


# ---------------------------------------------------------------------------
# Timeline widget
# ---------------------------------------------------------------------------

class TimelineBar(QWidget):
    """Transport / timeline bar shown at the bottom of the editor."""

    play_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    seek_changed = pyqtSignal(float)  # position in seconds

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._total_time: float = 0.0
        self._is_playing: bool = False

        self.setFixedHeight(50)
        self.setStyleSheet(f"background: {_BG}; border-top: 1px solid rgba(255,255,255,12);")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(6)

        # -- Transport buttons --
        self._btn_play = self._make_button("▶")
        self._btn_pause = self._make_button("⏸")
        self._btn_stop = self._make_button("■")

        self._btn_play.setToolTip("Play")
        self._btn_pause.setToolTip("Pause")
        self._btn_stop.setToolTip("Stop")

        self._btn_play.clicked.connect(self._on_play)
        self._btn_pause.clicked.connect(self._on_pause)
        self._btn_stop.clicked.connect(self._on_stop)

        layout.addWidget(self._btn_play)
        layout.addWidget(self._btn_pause)
        layout.addWidget(self._btn_stop)

        layout.addWidget(self._separator())

        # -- Time label (current) --
        self._lbl_time = QLabel("0:00")
        self._lbl_time.setStyleSheet(_TIME_LABEL_STYLE)
        self._lbl_time.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._lbl_time.setMinimumWidth(42)
        layout.addWidget(self._lbl_time)

        # -- Seek slider --
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 10000)
        self._slider.setValue(0)
        self._slider.setStyleSheet(_SLIDER_STYLE)
        self._slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._slider.valueChanged.connect(self._on_slider_changed)
        self._slider.sliderPressed.connect(self._on_slider_pressed)
        self._slider.sliderReleased.connect(self._on_slider_released)
        layout.addWidget(self._slider)
        self._slider_dragging = False

        # -- Total time label --
        self._lbl_total = QLabel("0:00")
        self._lbl_total.setStyleSheet(_TIME_LABEL_STYLE)
        self._lbl_total.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._lbl_total.setMinimumWidth(42)
        layout.addWidget(self._lbl_total)

        layout.addWidget(self._separator())

        # -- BPM --
        self._lbl_bpm = QLabel("120 BPM")
        self._lbl_bpm.setStyleSheet(_INFO_LABEL_STYLE)
        layout.addWidget(self._lbl_bpm)

        layout.addWidget(self._separator())

        # -- Key signature --
        self._lbl_key = QLabel("C")
        self._lbl_key.setStyleSheet(_INFO_LABEL_STYLE)
        layout.addWidget(self._lbl_key)

    # -- public API ---------------------------------------------------------

    def set_song_info(
        self,
        total_time: float,
        bpm: float = 120.0,
        key_signature: str = "C",
    ) -> None:
        """Configure the bar for a loaded song."""
        self._total_time = max(total_time, 0.001)
        self._lbl_total.setText(self._fmt(total_time))
        self._lbl_bpm.setText(f"{bpm:.0f} BPM")
        self._lbl_key.setText(key_signature)
        self._slider.setValue(0)
        self._lbl_time.setText("0:00")

    def set_position(self, seconds: float) -> None:
        """Update the playhead position (called by the playback timer)."""
        if self._slider_dragging:
            return
        seconds = max(0.0, min(seconds, self._total_time))
        self._lbl_time.setText(self._fmt(seconds))
        ratio = seconds / self._total_time if self._total_time else 0
        self._slider.blockSignals(True)
        self._slider.setValue(int(ratio * 10000))
        self._slider.blockSignals(False)

    def set_playing(self, playing: bool) -> None:
        """Reflect playback state (visual feedback)."""
        self._is_playing = playing
        self._btn_play.setEnabled(not playing)
        self._btn_pause.setEnabled(playing)

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _fmt(seconds: float) -> str:
        """Format seconds as 'm:ss'."""
        m = int(seconds) // 60
        s = int(seconds) % 60
        return f"{m}:{s:02d}"

    def _make_button(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setStyleSheet(_BUTTON_STYLE)
        btn.setFixedSize(QSize(36, 32))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    def _separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(_SEPARATOR_STYLE)
        return sep

    # -- slots --------------------------------------------------------------

    def _on_play(self) -> None:
        self.set_playing(True)
        self.play_clicked.emit()

    def _on_pause(self) -> None:
        self.set_playing(False)
        self.pause_clicked.emit()

    def _on_stop(self) -> None:
        self.set_playing(False)
        self.set_position(0.0)
        self.stop_clicked.emit()

    def _on_slider_changed(self, value: int) -> None:
        if self._slider_dragging:
            seconds = (value / 10000) * self._total_time
            self._lbl_time.setText(self._fmt(seconds))
            self.seek_changed.emit(seconds)

    def _on_slider_pressed(self) -> None:
        self._slider_dragging = True

    def _on_slider_released(self) -> None:
        self._slider_dragging = False
        value = self._slider.value()
        seconds = (value / 10000) * self._total_time
        self._lbl_time.setText(self._fmt(seconds))
        self.seek_changed.emit(seconds)
