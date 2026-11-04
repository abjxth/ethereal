"""
Settings Panel — Collapsible right-side panel with display, color, background,
and export controls.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QCheckBox, QComboBox, QPushButton, QSpinBox, QDoubleSpinBox,
    QScrollArea, QFrame, QFileDialog, QSizePolicy,
)

from ethereal.palettes import get_palette_names


# ---------------------------------------------------------------------------
# Stylesheet tokens
# ---------------------------------------------------------------------------

_ACCENT = "rgb(0, 210, 200)"
_BG = "rgb(30, 30, 35)"
_BG_SECTION = "rgb(36, 36, 42)"
_BG_INPUT = "rgb(44, 44, 52)"
_BORDER = "rgba(255, 255, 255, 18)"
_TEXT = "rgb(220, 220, 225)"
_TEXT_DIM = "rgb(140, 140, 150)"

_PANEL_STYLE = f"""
QWidget#settingsPanel {{
    background: {_BG};
    border-left: 1px solid {_BORDER};
}}
"""

_SECTION_TITLE_STYLE = f"""
QLabel {{
    color: {_ACCENT};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    padding: 0;
}}
"""

_LABEL_STYLE = f"""
QLabel {{
    color: {_TEXT};
    font-size: 12px;
}}
"""

_CHECKBOX_STYLE = f"""
QCheckBox {{
    color: {_TEXT};
    font-size: 12px;
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid rgba(255,255,255,30);
    background: {_BG_INPUT};
}}
QCheckBox::indicator:checked {{
    background: {_ACCENT};
    border-color: {_ACCENT};
}}
"""

_SLIDER_STYLE = f"""
QSlider::groove:horizontal {{
    background: {_BG_INPUT};
    height: 5px;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {_ACCENT};
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border-radius: 6px;
}}
QSlider::sub-page:horizontal {{
    background: {_ACCENT};
    border-radius: 2px;
}}
"""

_COMBO_STYLE = f"""
QComboBox {{
    background: {_BG_INPUT};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 12px;
    min-height: 24px;
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background: {_BG_INPUT};
    color: {_TEXT};
    selection-background-color: rgba(0,210,200,60);
    border: 1px solid {_BORDER};
    border-radius: 4px;
}}
"""

_BUTTON_STYLE = f"""
QPushButton {{
    background: {_BG_INPUT};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 12px;
}}
QPushButton:hover {{
    background: rgb(55, 55, 65);
    border-color: rgba(255,255,255,30);
}}
QPushButton:pressed {{
    background: rgb(65, 65, 75);
}}
"""

_EXPORT_BUTTON_STYLE = f"""
QPushButton {{
    background: {_ACCENT};
    color: rgb(15, 15, 18);
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton:hover {{
    background: rgb(0, 230, 220);
}}
QPushButton:pressed {{
    background: rgb(0, 190, 180);
}}
"""

_SPINBOX_STYLE = f"""
QSpinBox, QDoubleSpinBox {{
    background: {_BG_INPUT};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 3px 6px;
    font-size: 12px;
    min-height: 24px;
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    width: 16px;
    border: none;
    background: transparent;
}}
"""

_SEPARATOR_STYLE = f"""
QFrame {{
    background: {_BORDER};
    max-height: 1px;
    margin: 4px 0;
}}
"""


# ---------------------------------------------------------------------------
# Settings panel
# ---------------------------------------------------------------------------

class SettingsPanel(QWidget):
    """Collapsible right-side settings panel."""

    # Display signals
    zoom_changed = pyqtSignal(float)             # 0.5 – 4.0
    note_height_changed = pyqtSignal(int)         # 0=small, 1=medium, 2=large
    show_note_labels_changed = pyqtSignal(bool)
    show_chord_names_changed = pyqtSignal(bool)
    show_beat_grid_changed = pyqtSignal(bool)
    show_velocity_shading_changed = pyqtSignal(bool)
    glow_intensity_changed = pyqtSignal(int)      # 0–100

    # Color signals
    palette_changed = pyqtSignal(str)
    photo_palette_requested = pyqtSignal(str)     # image path

    # Background signals
    bg_type_changed = pyqtSignal(str)             # "Solid Color" | "Gradient" | "Image"
    bg_color_requested = pyqtSignal()
    bg_image_requested = pyqtSignal(str)          # image path
    bg_blur_changed = pyqtSignal(int)             # 0–100

    # Export signals
    aspect_ratio_changed = pyqtSignal(str)
    resolution_changed = pyqtSignal(str)
    fps_changed = pyqtSignal(int)
    start_time_changed = pyqtSignal(float)
    end_time_changed = pyqtSignal(float)
    export_requested = pyqtSignal()

    WIDTH = 260

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsPanel")
        self.setFixedWidth(self.WIDTH)
        self.setStyleSheet(_PANEL_STYLE)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        # Scroll area wrapping everything
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background: transparent; width: 6px; }"
            f"QScrollBar::handle:vertical {{ background: rgba(255,255,255,25); border-radius: 3px; }}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self._root = QVBoxLayout(container)
        self._root.setContentsMargins(14, 14, 14, 14)
        self._root.setSpacing(6)

        self._build_display_section()
        self._root.addWidget(self._separator())
        self._build_colors_section()
        self._root.addWidget(self._separator())
        self._build_background_section()
        self._root.addWidget(self._separator())
        self._build_export_section()

        self._root.addStretch()

        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ======================================================================
    # Section builders
    # ======================================================================

    def _build_display_section(self) -> None:
        self._root.addWidget(self._section_title("DISPLAY"))

        # Zoom
        self._root.addWidget(self._label("Zoom"))
        self._zoom_slider = self._make_slider(50, 400, 100)
        self._zoom_label = self._value_label("1.0×")
        row = self._slider_row(self._zoom_slider, self._zoom_label)
        self._root.addLayout(row)
        self._zoom_slider.valueChanged.connect(self._on_zoom)

        # Note height
        self._root.addWidget(self._label("Note Height"))
        self._note_height_combo = QComboBox()
        self._note_height_combo.addItems(["Small", "Medium", "Large"])
        self._note_height_combo.setCurrentIndex(1)
        self._note_height_combo.setStyleSheet(_COMBO_STYLE)
        self._note_height_combo.currentIndexChanged.connect(
            lambda i: self.note_height_changed.emit(i)
        )
        self._root.addWidget(self._note_height_combo)

        # Checkboxes
        self._cb_note_labels = self._make_checkbox("Show note labels", False)
        self._cb_chord_names = self._make_checkbox("Show chord names", False)
        self._cb_beat_grid = self._make_checkbox("Show beat grid", True)
        self._cb_velocity = self._make_checkbox("Show velocity shading", True)

        self._cb_note_labels.toggled.connect(self.show_note_labels_changed.emit)
        self._cb_chord_names.toggled.connect(self.show_chord_names_changed.emit)
        self._cb_beat_grid.toggled.connect(self.show_beat_grid_changed.emit)
        self._cb_velocity.toggled.connect(self.show_velocity_shading_changed.emit)

        self._root.addWidget(self._cb_note_labels)
        self._root.addWidget(self._cb_chord_names)
        self._root.addWidget(self._cb_beat_grid)
        self._root.addWidget(self._cb_velocity)

        # Glow intensity
        self._root.addWidget(self._label("Glow Intensity"))
        self._glow_slider = self._make_slider(0, 100, 60)
        self._glow_label = self._value_label("60%")
        row = self._slider_row(self._glow_slider, self._glow_label)
        self._root.addLayout(row)
        self._glow_slider.valueChanged.connect(self._on_glow)

    def _build_colors_section(self) -> None:
        self._root.addWidget(self._section_title("COLORS"))

        self._root.addWidget(self._label("Palette"))
        self._palette_combo = QComboBox()
        self._palette_combo.addItems(get_palette_names())
        self._palette_combo.setStyleSheet(_COMBO_STYLE)
        self._palette_combo.currentTextChanged.connect(self.palette_changed.emit)
        self._root.addWidget(self._palette_combo)

        self._btn_from_image = QPushButton("From Image…")
        self._btn_from_image.setStyleSheet(_BUTTON_STYLE)
        self._btn_from_image.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_from_image.clicked.connect(self._on_pick_palette_image)
        self._root.addWidget(self._btn_from_image)

    def _build_background_section(self) -> None:
        self._root.addWidget(self._section_title("BACKGROUND"))

        self._root.addWidget(self._label("Type"))
        self._bg_type_combo = QComboBox()
        self._bg_type_combo.addItems(["Solid Color", "Gradient", "Image"])
        self._bg_type_combo.setStyleSheet(_COMBO_STYLE)
        self._bg_type_combo.currentTextChanged.connect(self._on_bg_type)
        self._root.addWidget(self._bg_type_combo)

        # Color picker button
        self._btn_bg_color = QPushButton("Pick Color…")
        self._btn_bg_color.setStyleSheet(_BUTTON_STYLE)
        self._btn_bg_color.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_bg_color.clicked.connect(self.bg_color_requested.emit)
        self._root.addWidget(self._btn_bg_color)

        # Image file picker
        self._btn_bg_image = QPushButton("Choose Image…")
        self._btn_bg_image.setStyleSheet(_BUTTON_STYLE)
        self._btn_bg_image.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_bg_image.clicked.connect(self._on_pick_bg_image)
        self._btn_bg_image.setVisible(False)
        self._root.addWidget(self._btn_bg_image)

        # Blur
        self._root.addWidget(self._label("Background Blur"))
        self._blur_slider = self._make_slider(0, 100, 0)
        self._blur_label = self._value_label("0%")
        row = self._slider_row(self._blur_slider, self._blur_label)
        self._root.addLayout(row)
        self._blur_slider.valueChanged.connect(self._on_blur)

    def _build_export_section(self) -> None:
        self._root.addWidget(self._section_title("EXPORT"))

        # Aspect ratio
        self._root.addWidget(self._label("Aspect Ratio"))
        self._aspect_combo = QComboBox()
        self._aspect_combo.addItems(["9:16", "4:5", "1:1", "16:9"])
        self._aspect_combo.setCurrentText("16:9")
        self._aspect_combo.setStyleSheet(_COMBO_STYLE)
        self._aspect_combo.currentTextChanged.connect(self.aspect_ratio_changed.emit)
        self._root.addWidget(self._aspect_combo)

        # Resolution
        self._root.addWidget(self._label("Resolution"))
        self._res_combo = QComboBox()
        self._res_combo.addItems(["720p", "1080p", "4K"])
        self._res_combo.setCurrentText("1080p")
        self._res_combo.setStyleSheet(_COMBO_STYLE)
        self._res_combo.currentTextChanged.connect(self.resolution_changed.emit)
        self._root.addWidget(self._res_combo)

        # FPS
        self._root.addWidget(self._label("FPS"))
        self._fps_combo = QComboBox()
        self._fps_combo.addItems(["30", "60"])
        self._fps_combo.setCurrentText("30")
        self._fps_combo.setStyleSheet(_COMBO_STYLE)
        self._fps_combo.currentTextChanged.connect(
            lambda t: self.fps_changed.emit(int(t))
        )
        self._root.addWidget(self._fps_combo)

        # Start / End time
        time_row = QHBoxLayout()
        time_row.setSpacing(8)

        start_col = QVBoxLayout()
        start_col.setSpacing(2)
        start_col.addWidget(self._label("Start (s)"))
        self._spin_start = QDoubleSpinBox()
        self._spin_start.setRange(0, 99999)
        self._spin_start.setDecimals(1)
        self._spin_start.setSingleStep(0.5)
        self._spin_start.setValue(0.0)
        self._spin_start.setStyleSheet(_SPINBOX_STYLE)
        self._spin_start.valueChanged.connect(self.start_time_changed.emit)
        start_col.addWidget(self._spin_start)

        end_col = QVBoxLayout()
        end_col.setSpacing(2)
        end_col.addWidget(self._label("End (s)"))
        self._spin_end = QDoubleSpinBox()
        self._spin_end.setRange(0, 99999)
        self._spin_end.setDecimals(1)
        self._spin_end.setSingleStep(0.5)
        self._spin_end.setValue(0.0)
        self._spin_end.setStyleSheet(_SPINBOX_STYLE)
        self._spin_end.valueChanged.connect(self.end_time_changed.emit)
        end_col.addWidget(self._spin_end)

        time_row.addLayout(start_col)
        time_row.addLayout(end_col)
        self._root.addLayout(time_row)

        # Export button
        self._btn_export = QPushButton("Export Video")
        self._btn_export.setStyleSheet(_EXPORT_BUTTON_STYLE)
        self._btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_export.clicked.connect(self.export_requested.emit)
        self._root.addWidget(self._btn_export)

    # ======================================================================
    # Public helpers
    # ======================================================================

    def set_song_duration(self, seconds: float) -> None:
        """Update end-time spin box max and default."""
        self._spin_start.setMaximum(seconds)
        self._spin_end.setMaximum(seconds)
        self._spin_end.setValue(seconds)

    def current_palette_name(self) -> str:
        return self._palette_combo.currentText()

    def current_aspect_ratio(self) -> str:
        return self._aspect_combo.currentText()

    def current_resolution(self) -> str:
        return self._res_combo.currentText()

    def current_fps(self) -> int:
        return int(self._fps_combo.currentText())

    def current_zoom(self) -> float:
        return self._zoom_slider.value() / 100.0

    def current_glow_intensity(self) -> int:
        return self._glow_slider.value()

    # ======================================================================
    # Slots
    # ======================================================================

    def _on_zoom(self, value: int) -> None:
        z = value / 100.0
        self._zoom_label.setText(f"{z:.1f}×")
        self.zoom_changed.emit(z)

    def _on_glow(self, value: int) -> None:
        self._glow_label.setText(f"{value}%")
        self.glow_intensity_changed.emit(value)

    def _on_blur(self, value: int) -> None:
        self._blur_label.setText(f"{value}%")
        self.bg_blur_changed.emit(value)

    def _on_bg_type(self, text: str) -> None:
        self._btn_bg_color.setVisible(text in ("Solid Color", "Gradient"))
        self._btn_bg_image.setVisible(text == "Image")
        self.bg_type_changed.emit(text)

    def _on_pick_palette_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Image for Palette", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if path:
            self.photo_palette_requested.emit(path)

    def _on_pick_bg_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Background Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if path:
            self.bg_image_requested.emit(path)

    # ======================================================================
    # Widget factories
    # ======================================================================

    @staticmethod
    def _section_title(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(_SECTION_TITLE_STYLE)
        return lbl

    @staticmethod
    def _label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(_LABEL_STYLE)
        return lbl

    @staticmethod
    def _value_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"QLabel {{ color: {_TEXT_DIM}; font-size: 11px; min-width: 36px; }}"
        )
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return lbl

    @staticmethod
    def _make_slider(lo: int, hi: int, default: int) -> QSlider:
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(lo, hi)
        s.setValue(default)
        s.setStyleSheet(_SLIDER_STYLE)
        return s

    @staticmethod
    def _make_checkbox(text: str, checked: bool) -> QCheckBox:
        cb = QCheckBox(text)
        cb.setChecked(checked)
        cb.setStyleSheet(_CHECKBOX_STYLE)
        cb.setCursor(Qt.CursorShape.PointingHandCursor)
        return cb

    @staticmethod
    def _slider_row(slider: QSlider, label: QLabel) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(slider, stretch=1)
        row.addWidget(label)
        return row

    @staticmethod
    def _separator() -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(_SEPARATOR_STYLE)
        return sep
