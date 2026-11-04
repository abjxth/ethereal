"""
Track Pills — Rounded pill buttons for toggling track visibility.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QFontMetrics
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QSizePolicy,
)

from ethereal.midi_engine import TrackInfo
from ethereal.palettes import ColorPalette


# ---------------------------------------------------------------------------
# Single track pill
# ---------------------------------------------------------------------------

class TrackPill(QWidget):
    """A single rounded pill representing one MIDI track."""

    toggled = pyqtSignal(int, bool)  # (track_index, is_visible)

    _BG_NORMAL = QColor(40, 40, 48, 180)
    _BG_HOVER = QColor(55, 55, 65, 200)
    _BG_INACTIVE = QColor(30, 30, 35, 140)
    _TEXT_ACTIVE = QColor(255, 255, 255)
    _TEXT_INACTIVE = QColor(120, 120, 130)

    def __init__(
        self,
        track_info: TrackInfo,
        color: tuple[int, int, int],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._track = track_info
        self._color = QColor(*color)
        self._active = track_info.visible
        self._hovered = False

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setMouseTracking(True)

        self._font = QFont("Satoshi", 9)
        self._font.setWeight(QFont.Weight.Bold)

        self._dot_radius = 4
        self._h_pad = 14
        self._v_pad = 7
        self._dot_text_gap = 6

    # -- size ---------------------------------------------------------------

    def sizeHint(self) -> QSize:
        fm = QFontMetrics(self._font)
        text_w = fm.horizontalAdvance(self._track.name)
        w = self._h_pad * 2 + self._dot_radius * 2 + self._dot_text_gap + text_w
        h = self._v_pad * 2 + fm.height()
        return QSize(w, h)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    # -- properties ---------------------------------------------------------

    @property
    def track_index(self) -> int:
        return self._track.index

    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, value: bool) -> None:
        if self._active != value:
            self._active = value
            self._track.visible = value
            self.update()

    # -- painting -----------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        radius = rect.height() / 2

        # Background fill
        if self._active:
            bg = self._BG_HOVER if self._hovered else self._BG_NORMAL
        else:
            bg = self._BG_INACTIVE

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg))
        painter.drawRoundedRect(rect, radius, radius)

        # Active border
        if self._active:
            border_color = QColor(self._color)
            border_color.setAlpha(200 if self._hovered else 160)
            painter.setPen(QPen(border_color, 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect, radius, radius)

        # Colored dot
        dot_x = rect.left() + self._h_pad + self._dot_radius
        dot_y = rect.center().y()
        dot_color = QColor(self._color)
        if not self._active:
            dot_color.setAlpha(80)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(dot_color))
        painter.drawEllipse(dot_x - self._dot_radius, dot_y - self._dot_radius,
                            self._dot_radius * 2, self._dot_radius * 2)

        # Subtle glow behind dot (active only)
        if self._active:
            glow = QColor(self._color)
            glow.setAlpha(40)
            painter.setBrush(QBrush(glow))
            glow_r = self._dot_radius + 4
            painter.drawEllipse(dot_x - glow_r, dot_y - glow_r, glow_r * 2, glow_r * 2)

        # Track name
        text_color = self._TEXT_ACTIVE if self._active else self._TEXT_INACTIVE
        painter.setPen(QPen(text_color))
        painter.setFont(self._font)

        text_x = dot_x + self._dot_radius + self._dot_text_gap
        text_rect = rect.adjusted(0, 0, 0, 0)
        text_rect.setLeft(text_x)
        text_rect.setRight(rect.right() - self._h_pad)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter, self._track.name)

        painter.end()

    # -- interaction --------------------------------------------------------

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.active = not self._active
            self.toggled.emit(self._track.index, self._active)

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hovered = True
        self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hovered = False
        self.update()


# ---------------------------------------------------------------------------
# Container widget
# ---------------------------------------------------------------------------

class TrackPillBar(QWidget):
    """Horizontal bar of track pills."""

    track_visibility_changed = pyqtSignal(int, bool)  # (track_index, visible)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pills: dict[int, TrackPill] = {}

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 8, 12, 8)
        self._layout.setSpacing(6)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.setStyleSheet("background: transparent;")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    # -- public API ---------------------------------------------------------

    def set_tracks(self, tracks: list[TrackInfo], palette: ColorPalette) -> None:
        """Populate pills from track list and palette."""
        self.clear()
        for track in tracks:
            color = palette.colors[track.color_idx % len(palette.colors)]
            pill = TrackPill(track, color, parent=self)
            pill.toggled.connect(self._on_pill_toggled)
            self._layout.addWidget(pill)
            self._pills[track.index] = pill

    def clear(self) -> None:
        """Remove all pills."""
        for pill in self._pills.values():
            pill.toggled.disconnect(self._on_pill_toggled)
            self._layout.removeWidget(pill)
            pill.deleteLater()
        self._pills.clear()

    def set_track_active(self, track_index: int, active: bool) -> None:
        """Programmatically set a track's visibility."""
        pill = self._pills.get(track_index)
        if pill is not None:
            pill.active = active

    def solo_track(self, track_index: int) -> None:
        """Make only one track visible."""
        for idx, pill in self._pills.items():
            pill.active = (idx == track_index)

    def show_all(self) -> None:
        """Make all tracks visible."""
        for pill in self._pills.values():
            pill.active = True

    # -- private ------------------------------------------------------------

    def _on_pill_toggled(self, track_index: int, visible: bool) -> None:
        self.track_visibility_changed.emit(track_index, visible)
