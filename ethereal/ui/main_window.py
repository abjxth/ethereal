"""
Main window for Ethereal — stylized MIDI and Audio Visualizer.
With bold Satoshi typography, sleek minimalist scrollbars, real-time
instrument & song title renaming, multi-MIDI tracks, and creator credits.
"""
from __future__ import annotations

import os
import sys
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QUrl
from PyQt6.QtGui import (
    QFont, QColor, QPixmap, QIcon, QDesktopServices, QDragEnterEvent, QDropEvent
)
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QFileDialog, QMessageBox, QLabel, QPushButton, QComboBox,
    QSlider, QCheckBox, QScrollArea, QFrame, QLineEdit,
    QSpinBox, QDoubleSpinBox, QProgressBar, QDialog,
    QApplication, QToolBar, QSizePolicy, QColorDialog
)

from ethereal.midi_engine import parse_midi, MidiData, MultiMidiProject, LoadedMidi
from ethereal.audio_engine import AudioData, AudioPlayer, load_audio_waveform
from ethereal.renderer import MidiRenderer
from ethereal.palettes import (
    get_palette, get_palette_names, extract_palette_from_image, ColorPalette
)
from ethereal.presets import Preset, load_presets, save_preset
from ethereal.exporter import ExportWorker, find_ffmpeg, ASPECT_RATIOS, RESOLUTIONS


# ---------------------------------------------------------------------------
# Sleek, Modern, Minimalist Dark Theme with Bold Satoshi Typography
# ---------------------------------------------------------------------------
# Sleek, Modern Antigravity IDE Dark Theme with Bold Satoshi Typography
# ---------------------------------------------------------------------------

def get_icons_dir() -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    icons_dir = os.path.join(base, "resources", "icons")
    if getattr(sys, "frozen", False):
        meipass_icons = os.path.join(getattr(sys, "_MEIPASS", ""), "ethereal", "resources", "icons")
        if os.path.exists(meipass_icons):
            icons_dir = meipass_icons
    return icons_dir.replace("\\", "/")


def get_dark_style() -> str:
    icons_dir = get_icons_dir()
    return f"""
QMainWindow, QWidget {{
    background-color: #0d0d12;
    color: #e6e6f0;
    font-family: "Satoshi", "Segoe UI", -apple-system, sans-serif;
    font-size: 12px;
    font-weight: 700;
}}

/* ToolBar — Antigravity Header */
QToolBar {{
    background-color: #121218;
    border-bottom: 1px solid #1e1e28;
    spacing: 8px;
    padding: 7px 16px;
}}
QToolBar QPushButton, QToolBar QComboBox {{
    background-color: #1a1a24;
    border: 1px solid #2a2a3a;
    border-radius: 8px;
    padding: 6px 14px;
    color: #f0f0f8;
    font-weight: 700;
    min-height: 24px;
}}
QToolBar QPushButton:hover {{
    background-color: #242434;
    border-color: #3e3e56;
    color: #ffffff;
}}
QToolBar QPushButton:pressed {{
    background-color: #00d2c8;
    border-color: #00d2c8;
    color: #081111;
}}

/* Modern Antigravity Section Cards */
QFrame.SectionCard {{
    background-color: #14141e;
    border: 1px solid #222232;
    border-radius: 10px;
    padding: 14px;
    margin-bottom: 6px;
}}
QFrame.SectionCard:hover {{
    border-color: #2e2e42;
}}

/* Section Header Labels */
QLabel.SectionHeader {{
    color: #00d2c8;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    background: transparent;
}}

/* Ultra-Sleek Minimalist 6px Scrollbars */
QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 6px;
    margin: 4px 1px 4px 1px;
}}
QScrollBar::handle:vertical {{
    background: rgba(255, 255, 255, 0.14);
    min-height: 32px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical:hover {{
    background: #00d2c8;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
    border: none;
    background: none;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    border: none;
    background: transparent;
    height: 6px;
    margin: 1px 4px 1px 4px;
}}
QScrollBar::handle:horizontal {{
    background: rgba(255, 255, 255, 0.14);
    min-width: 32px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal:hover {{
    background: #00d2c8;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
    border: none;
    background: none;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}

/* Modern Sleek Text Input */
QLineEdit {{
    background-color: #181824;
    border: 1px solid #282838;
    border-radius: 8px;
    padding: 6px 10px;
    color: #ffffff;
    font-weight: 700;
    font-size: 12px;
    selection-background-color: #00d2c8;
    selection-color: #081111;
}}
QLineEdit:hover {{
    border-color: #38384e;
    background-color: #1b1b28;
}}
QLineEdit:focus {{
    border-color: #00d2c8;
    background-color: #1d1d2b;
}}

/* Antigravity Modern SpinBox & DoubleSpinBox with Real Chevron Icons */
QSpinBox, QDoubleSpinBox {{
    background-color: #181824;
    border: 1px solid #282838;
    border-radius: 8px;
    padding: 6px 26px 6px 10px;
    color: #ffffff;
    font-weight: 700;
    font-size: 12px;
    selection-background-color: #00d2c8;
    selection-color: #081111;
}}
QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: #38384e;
    background-color: #1b1b28;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: #00d2c8;
    background-color: #1d1d2b;
}}
QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 22px;
    height: 14px;
    background: #1e1e2b;
    border-left: 1px solid #282838;
    border-bottom: 1px solid #282838;
    border-top-right-radius: 7px;
    margin: 1px 1px 0 0;
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
    background: #2b2b3d;
}}
QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed {{
    background: #00d2c8;
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: url({icons_dir}/spin_up.png);
    width: 10px;
    height: 6px;
}}
QSpinBox::up-arrow:hover, QDoubleSpinBox::up-arrow:hover {{
    image: url({icons_dir}/spin_up_hover.png);
}}
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 22px;
    height: 14px;
    background: #1e1e2b;
    border-left: 1px solid #282838;
    border-bottom-right-radius: 7px;
    margin: 0 1px 1px 0;
}}
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background: #2b2b3d;
}}
QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {{
    background: #00d2c8;
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: url({icons_dir}/spin_down.png);
    width: 10px;
    height: 6px;
}}
QSpinBox::down-arrow:hover, QDoubleSpinBox::down-arrow:hover {{
    image: url({icons_dir}/spin_down_hover.png);
}}

/* Antigravity Modern ComboBox with Real Chevron Down Arrow */
QComboBox {{
    background-color: #181824;
    border: 1px solid #282838;
    border-radius: 8px;
    padding: 6px 30px 6px 12px;
    color: #ffffff;
    font-weight: 700;
    font-size: 12px;
    min-height: 20px;
}}
QComboBox:hover {{
    border-color: #38384e;
    background-color: #1b1b28;
}}
QComboBox:focus {{
    border-color: #00d2c8;
}}
QComboBox::drop-down {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 26px;
    border-left: 1px solid #282838;
    border-top-right-radius: 7px;
    border-bottom-right-radius: 7px;
    background: #1e1e2b;
}}
QComboBox::drop-down:hover {{
    background: #2b2b3d;
}}
QComboBox::down-arrow {{
    image: url({icons_dir}/dropdown_arrow.png);
    width: 14px;
    height: 14px;
}}
QComboBox::down-arrow:hover {{
    image: url({icons_dir}/dropdown_arrow_hover.png);
}}
QComboBox QAbstractItemView {{
    background-color: #14141e;
    border: 1px solid #28283c;
    border-radius: 8px;
    padding: 4px;
    color: #f0f0f8;
    selection-background-color: #242436;
    selection-color: #00d2c8;
    font-weight: 700;
    outline: none;
}}

/* Antigravity Modern Checkbox with Real Checkmark Icon */
QCheckBox {{
    spacing: 10px;
    color: #d0d0dc;
    font-weight: 700;
    font-size: 12px;
    background: transparent;
}}
QCheckBox:hover {{
    color: #ffffff;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
}}
QCheckBox::indicator:unchecked {{
    image: url({icons_dir}/checkbox_unchecked.png);
}}
QCheckBox::indicator:unchecked:hover {{
    image: url({icons_dir}/checkbox_hover.png);
}}
QCheckBox::indicator:checked {{
    image: url({icons_dir}/checkbox_checked.png);
}}

/* Antigravity Sliders (Both sub-page and add-page for solid track display) */
QSlider::groove:horizontal {{
    border: none;
    height: 4px;
    background: #232332;
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: #00d2c8;
    border-radius: 2px;
}}
QSlider::add-page:horizontal {{
    background: #232332;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: #ffffff;
    border: 2px solid #00d2c8;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{
    background: #00d2c8;
    border: 2px solid #ffffff;
}}

/* Antigravity Modern Sleek Buttons */
QPushButton {{
    background-color: #1c1c28;
    border: 1px solid #2b2b3c;
    border-radius: 8px;
    padding: 7px 14px;
    color: #ececf4;
    font-weight: 700;
    font-size: 12px;
}}
QPushButton:hover {{
    background-color: #252536;
    border-color: #3e3e56;
    color: #ffffff;
}}
QPushButton:pressed {{
    background-color: #00d2c8;
    border-color: #00d2c8;
    color: #081111;
}}
QPushButton:disabled {{
    background-color: #13131a;
    border-color: #1f1f29;
    color: #555564;
}}

QScrollArea {{
    border: none;
    background-color: transparent;
}}
QProgressBar {{
    border: 1px solid #2a2a3c;
    border-radius: 8px;
    background-color: #181824;
    text-align: center;
    color: #ffffff;
    font-weight: 700;
    height: 22px;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00d2c8, stop:1 #00b4d8);
    border-radius: 7px;
}}
QLabel {{
    color: #b0b0c2;
    font-weight: 700;
    font-size: 11px;
    background: transparent;
}}

QSplitter::handle {{
    background-color: #181822;
    width: 1px;
}}
QSplitter::handle:hover {{
    background-color: #00d2c8;
}}

/* Antigravity Modern Transport bar */
#transport {{
    background-color: #0d0d14;
    border-top: 1px solid #1c1c28;
    min-height: 58px;
    max-height: 58px;
}}
#transport QPushButton {{
    background-color: #181824;
    border: 1px solid #28283a;
    font-size: 14px;
    color: #ffffff;
    padding: 0px;
    margin: 0px;
    min-width: 36px;
    max-width: 36px;
    min-height: 36px;
    max-height: 36px;
    border-radius: 8px;
    font-weight: 800;
}}
#transport #btn_play {{
    background-color: #00d2c8;
    border: 1px solid #00d2c8;
    color: #081111;
    font-size: 15px;
    font-weight: 900;
    padding: 0px;
    margin: 0px;
    min-width: 36px;
    max-width: 36px;
    min-height: 36px;
    max-height: 36px;
    border-radius: 8px;
}}
#transport #btn_play:hover {{
    background-color: #00f0e6;
    border-color: #00f0e6;
}}
#transport #btn_play:pressed {{
    background-color: #00b8af;
    border-color: #00b8af;
}}
#transport #btn_stop {{
    background-color: #181824;
    border: 1px solid #28283a;
    color: #e6e6f0;
    font-size: 13px;
    font-weight: 900;
    padding: 0px;
    margin: 0px;
    min-width: 36px;
    max-width: 36px;
    min-height: 36px;
    max-height: 36px;
    border-radius: 8px;
}}
#transport #btn_stop:hover {{
    background-color: #242436;
    border-color: #ff5566;
    color: #ff6677;
}}
#transport #btn_stop:pressed {{
    background-color: #ff4455;
    border-color: #ff4455;
    color: #ffffff;
}}
"""

DARK_STYLE = get_dark_style()


def _create_card(title: str) -> tuple[QFrame, QVBoxLayout]:
    """Helper to create a sleek Antigravity-style card container with clean header."""
    card = QFrame()
    card.setProperty("class", "SectionCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(8)

    header_row = QHBoxLayout()
    header_row.setContentsMargins(0, 0, 0, 4)
    header_row.setSpacing(7)

    dot = QLabel("●")
    dot.setStyleSheet("color: #00d2c8; font-size: 8px; background: transparent;")
    header_row.addWidget(dot)

    lbl_title = QLabel(title)
    lbl_title.setProperty("class", "SectionHeader")
    header_row.addWidget(lbl_title, 1)

    layout.addLayout(header_row)
    return card, layout


class MainWindow(QMainWindow):
    """Ethereal main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ethereal — Stylized MIDI and Audio Visualizer")
        self.setMinimumSize(1180, 780)
        self.resize(1400, 880)
        self.setAcceptDrops(True)

        # Core State
        self._multi_midi = MultiMidiProject()
        self._audio_data: Optional[AudioData] = None
        self._audio_player = AudioPlayer(self)
        self._current_palette = get_palette("Ethereal")
        self._export_worker: Optional[ExportWorker] = None

        self._init_ui()
        self._apply_style()

        # Playhead update timer
        self._ui_timer = QTimer(self)
        self._ui_timer.setInterval(35)
        self._ui_timer.timeout.connect(self._update_time_display)
        self._ui_timer.start()

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ---- Top Toolbar ----
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)

        logo_label = QLabel("●  ETHEREAL")
        logo_label.setFont(QFont("Satoshi", 13, QFont.Weight.Black))
        logo_label.setStyleSheet("color: #00d2c8; background: transparent; letter-spacing: 2px; padding-right: 6px;")
        toolbar.addWidget(logo_label)
        toolbar.addSeparator()

        btn_add_midi = QPushButton("➕ Add MIDI...")
        btn_add_midi.clicked.connect(self._open_midi_dialog)
        toolbar.addWidget(btn_add_midi)

        btn_load_audio = QPushButton("🎵 Load Audio...")
        btn_load_audio.clicked.connect(self._open_audio_dialog)
        toolbar.addWidget(btn_load_audio)

        # Audio status badge
        self._audio_badge = QFrame()
        self._audio_badge.setStyleSheet("QFrame { background: #181824; border: 1px solid #28283a; border-radius: 8px; }")
        ab_layout = QHBoxLayout(self._audio_badge)
        ab_layout.setContentsMargins(8, 3, 8, 3)
        ab_layout.setSpacing(6)
        self._lbl_audio_name = QLabel("No Audio")
        self._lbl_audio_name.setStyleSheet("color: #88889a; font-size: 11px; font-weight: 700; background: transparent; border: none;")
        ab_layout.addWidget(self._lbl_audio_name)
        self._btn_remove_audio = QPushButton("✕")
        self._btn_remove_audio.setFixedSize(16, 16)
        self._btn_remove_audio.setStyleSheet("background: transparent; color: #ff6666; font-size: 11px; border: none; font-weight: 800; padding: 0;")
        self._btn_remove_audio.clicked.connect(self._remove_audio)
        self._btn_remove_audio.hide()
        ab_layout.addWidget(self._btn_remove_audio)
        toolbar.addWidget(self._audio_badge)

        toolbar.addSeparator()

        lbl_preset = QLabel(" Preset: ")
        lbl_preset.setStyleSheet("color: #88889a; font-size: 11px; background: transparent;")
        toolbar.addWidget(lbl_preset)
        self._preset_combo = QComboBox()
        self._preset_combo.setMinimumWidth(150)
        self._refresh_presets()
        self._preset_combo.currentTextChanged.connect(self._on_preset_changed)
        toolbar.addWidget(self._preset_combo)

        btn_save_preset = QPushButton("Save Preset")
        btn_save_preset.clicked.connect(self._save_current_preset)
        toolbar.addWidget(btn_save_preset)

        # Credits button in Toolbar
        toolbar.addSeparator()
        btn_credits = QPushButton("✨ Credits")
        btn_credits.setStyleSheet("""
            QPushButton {
                background-color: #1a1a26;
                border: 1px solid #2e2e42;
                border-radius: 8px;
                color: #e4e4f0;
            }
            QPushButton:hover {
                background-color: #242436;
                border-color: #00d2c8;
                color: #00d2c8;
            }
        """)
        btn_credits.clicked.connect(self._show_credits_dialog)
        toolbar.addWidget(btn_credits)

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        # Export button
        btn_export = QPushButton("⬇  Export Video (MP4)")
        btn_export.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00d2c8, stop:1 #00b4d8);
                color: #081212;
                font-weight: 800;
                border: none;
                border-radius: 8px;
                padding: 7px 22px;
                font-size: 12px;
            }
            QPushButton:hover { background: #19ece2; }
            QPushButton:pressed { background: #00aba2; }
        """)
        btn_export.clicked.connect(self._export_video)
        toolbar.addWidget(btn_export)

        self.addToolBar(toolbar)

        # ---- Center Area (Splitter: Canvas + Sleek Settings Panel) ----
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Canvas
        self._renderer = MidiRenderer()
        self._renderer.set_multi_midi(self._multi_midi)
        splitter.addWidget(self._renderer)

        # Right Settings Panel in a scroll area with custom sleek scrollbar
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setMinimumWidth(340)
        settings_scroll.setMaximumWidth(400)
        settings_widget = self._build_settings_panel()
        settings_scroll.setWidget(settings_widget)
        splitter.addWidget(settings_scroll)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([1020, 380])

        main_layout.addWidget(splitter, 1)

        # ---- Bottom Transport Bar ----
        transport = self._build_transport()
        main_layout.addWidget(transport)

    def _build_settings_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # ---------------------------------------------------------------
        # 1. Project Info & Metadata (Renaming Song Title)
        # ---------------------------------------------------------------
        proj_card, pl = _create_card("PROJECT INFO")

        pl.addWidget(QLabel("Song Title"))
        self._song_title_edit = QLineEdit("Ethereal")
        self._song_title_edit.setPlaceholderText("Enter custom song title...")
        self._song_title_edit.textChanged.connect(self._on_song_title_edited)
        pl.addWidget(self._song_title_edit)

        bpm_key_row = QHBoxLayout()
        bpm_col = QVBoxLayout()
        bpm_col.addWidget(QLabel("BPM"))
        self._bpm_spin = QDoubleSpinBox()
        self._bpm_spin.setRange(20, 999)
        self._bpm_spin.setValue(120.0)
        self._bpm_spin.setDecimals(1)
        self._bpm_spin.valueChanged.connect(self._on_bpm_edited)
        bpm_col.addWidget(self._bpm_spin)
        bpm_key_row.addLayout(bpm_col)

        key_col = QVBoxLayout()
        key_col.addWidget(QLabel("Key"))
        self._key_edit = QLineEdit("C")
        self._key_edit.setPlaceholderText("Key (e.g. C, Am)")
        self._key_edit.textChanged.connect(self._on_key_edited)
        key_col.addWidget(self._key_edit)
        bpm_key_row.addLayout(key_col)
        pl.addLayout(bpm_key_row)

        layout.addWidget(proj_card)

        # ---------------------------------------------------------------
        # 2. Instruments & Tracks (Renaming Instrument / Track Names)
        # ---------------------------------------------------------------
        tracks_card, tl = _create_card("INSTRUMENTS & TRACKS")

        self._midi_list_container = QWidget()
        self._midi_list_layout = QVBoxLayout(self._midi_list_container)
        self._midi_list_layout.setContentsMargins(0, 0, 0, 0)
        self._midi_list_layout.setSpacing(6)
        tl.addWidget(self._midi_list_container)

        btn_add_more = QPushButton("➕ Add Another MIDI...")
        btn_add_more.clicked.connect(self._open_midi_dialog)
        tl.addWidget(btn_add_more)

        layout.addWidget(tracks_card)

        # ---------------------------------------------------------------
        # 3. Audio & Waveform Design
        # ---------------------------------------------------------------
        wave_card, wl = _create_card("AUDIO & WAVEFORM")

        wl.addWidget(QLabel("Waveform Style"))
        self._wave_style_combo = QComboBox()
        self._wave_style_combo.addItems([
            "Neon Pulse Bars",
            "Smooth Glowing Wave",
            "Dual Area Mountain",
            "Circular Radial Halo",
            "Segmented LED Matrix",
            "Minimalist Line",
        ])
        self._wave_style_combo.currentIndexChanged.connect(self._on_wave_style_changed)
        wl.addWidget(self._wave_style_combo)

        wl.addWidget(QLabel("Height Scale"))
        self._wave_h_slider = QSlider(Qt.Orientation.Horizontal)
        self._wave_h_slider.setRange(20, 250)
        self._wave_h_slider.setValue(100)
        self._wave_h_slider.valueChanged.connect(lambda v: self._renderer.set_waveform_height(v / 100.0))
        wl.addWidget(self._wave_h_slider)

        wl.addWidget(QLabel("Waveform Opacity"))
        self._wave_op_slider = QSlider(Qt.Orientation.Horizontal)
        self._wave_op_slider.setRange(10, 100)
        self._wave_op_slider.setValue(75)
        self._wave_op_slider.valueChanged.connect(lambda v: self._renderer.set_waveform_opacity(v / 100.0))
        wl.addWidget(self._wave_op_slider)

        wl.addWidget(QLabel("Position"))
        self._wave_pos_combo = QComboBox()
        self._wave_pos_combo.addItems(["Bottom", "Center", "Background"])
        self._wave_pos_combo.currentTextChanged.connect(lambda t: self._renderer.set_waveform_position(t.lower()))
        wl.addWidget(self._wave_pos_combo)

        layout.addWidget(wave_card)

        # ---------------------------------------------------------------
        # 4. Strike & Hit Effects
        # ---------------------------------------------------------------
        hit_card, hl = _create_card("STRIKE & HIT EFFECTS")

        hl.addWidget(QLabel("Hit Marker on Playhead Strike"))
        self._hit_type_combo = QComboBox()
        self._hit_type_combo.addItems([
            "Glowing Orb / Dot",
            "Emoji / Symbol",
            "Shockwave Ring",
            "Sparkle Star (✦)",
            "Diamond (◆)",
            "None",
        ])
        self._hit_type_combo.currentIndexChanged.connect(self._on_hit_type_changed)
        hl.addWidget(self._hit_type_combo)

        hl.addWidget(QLabel("Custom Emoji or Character"))
        emoji_row = QHBoxLayout()
        emoji_row.setSpacing(6)
        self._emoji_edit = QLineEdit("🔥")
        self._emoji_edit.setMaxLength(6)
        self._emoji_edit.setFixedWidth(46)
        self._emoji_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._emoji_edit.setStyleSheet("font-size: 14px; font-weight: 700;")
        self._emoji_edit.textChanged.connect(self._renderer.set_hit_marker_emoji)
        emoji_row.addWidget(self._emoji_edit)

        for em in ["🔥", "✨", "⚡", "💫", "💎", "🌸", "🎹", "✦"]:
            btn_em = QPushButton(em)
            btn_em.setFixedSize(26, 26)
            btn_em.setStyleSheet("font-size: 12px; padding: 0; border-radius: 6px;")
            btn_em.clicked.connect(lambda _, e=em: self._emoji_edit.setText(e))
            emoji_row.addWidget(btn_em)
        emoji_row.addStretch()
        hl.addLayout(emoji_row)

        hl.addWidget(QLabel("Marker Scale"))
        self._marker_size_slider = QSlider(Qt.Orientation.Horizontal)
        self._marker_size_slider.setRange(50, 250)
        self._marker_size_slider.setValue(100)
        self._marker_size_slider.valueChanged.connect(lambda v: self._renderer.set_hit_marker_size(v / 100.0))
        hl.addWidget(self._marker_size_slider)

        hl.addWidget(QLabel("Note Aura & Glow Style"))
        self._glow_style_combo = QComboBox()
        self._glow_style_combo.addItems([
            "Radial Bloom",
            "Neon Laser",
            "Electric Flare",
            "Particle Sparks",
        ])
        self._glow_style_combo.currentIndexChanged.connect(self._on_glow_style_changed)
        hl.addWidget(self._glow_style_combo)

        hl.addWidget(QLabel("Glow Intensity"))
        self._glow_slider = QSlider(Qt.Orientation.Horizontal)
        self._glow_slider.setRange(0, 200)
        self._glow_slider.setValue(80)
        self._glow_slider.valueChanged.connect(lambda v: self._renderer.set_glow_intensity(v / 100.0))
        hl.addWidget(self._glow_slider)

        hl.addWidget(QLabel("Glow Color Mode"))
        glow_color_row = QHBoxLayout()
        glow_color_row.setSpacing(8)
        self._glow_col_combo = QComboBox()
        self._glow_col_combo.addItems(["Match Note", "White-Hot Core", "Playhead Accent", "Custom"])
        self._glow_col_combo.currentTextChanged.connect(self._on_glow_color_mode_changed)
        glow_color_row.addWidget(self._glow_col_combo, 2)

        self._btn_glow_custom_col = QPushButton("● Color")
        self._btn_glow_custom_col.setMinimumWidth(80)
        self._btn_glow_custom_col.clicked.connect(self._pick_glow_custom_color)
        glow_color_row.addWidget(self._btn_glow_custom_col, 1)
        hl.addLayout(glow_color_row)

        layout.addWidget(hit_card)

        # ---------------------------------------------------------------
        # 5. Piano Roll Display
        # ---------------------------------------------------------------
        disp_card, dl = _create_card("PIANO ROLL DISPLAY")

        dl.addWidget(QLabel("Zoom (Time Window)"))
        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setRange(30, 400)
        self._zoom_slider.setValue(100)
        self._zoom_slider.valueChanged.connect(lambda v: self._renderer.set_zoom(v / 100.0))
        dl.addWidget(self._zoom_slider)

        dl.addWidget(QLabel("Note Bar Height"))
        self._note_h_combo = QComboBox()
        self._note_h_combo.addItems(["Small", "Medium", "Large"])
        self._note_h_combo.setCurrentIndex(1)
        self._note_h_combo.currentIndexChanged.connect(self._renderer.set_note_height_mode)
        dl.addWidget(self._note_h_combo)

        self._cb_labels = QCheckBox("Note Labels (Pitch Names)")
        self._cb_labels.setChecked(True)
        self._cb_labels.toggled.connect(self._renderer.set_show_note_labels)
        dl.addWidget(self._cb_labels)

        self._cb_chords = QCheckBox("Auto-Detect Chords")
        self._cb_chords.setChecked(True)
        self._cb_chords.toggled.connect(self._renderer.set_show_chord_names)
        dl.addWidget(self._cb_chords)

        self._cb_grid = QCheckBox("Beat & Bar Grid")
        self._cb_grid.setChecked(True)
        self._cb_grid.toggled.connect(self._renderer.set_show_beat_grid)
        dl.addWidget(self._cb_grid)

        self._cb_vel = QCheckBox("Velocity Shading")
        self._cb_vel.setChecked(True)
        self._cb_vel.toggled.connect(self._renderer.set_show_velocity)
        dl.addWidget(self._cb_vel)

        self._cb_reels_safe = QCheckBox("Reels & Shorts Safe Framing")
        self._cb_reels_safe.setToolTip("Auto-adjust layout for Instagram Reels & YouTube Shorts safe zones (prevents UI overlap)")
        self._cb_reels_safe.setChecked(True)
        self._cb_reels_safe.toggled.connect(self._renderer.set_reels_safe_framing)
        dl.addWidget(self._cb_reels_safe)

        self._cb_safe_guides = QCheckBox("Preview Reels / Shorts Guides")
        self._cb_safe_guides.setToolTip("Display overlay guides for mobile notch, caption, and action buttons")
        self._cb_safe_guides.setChecked(False)
        self._cb_safe_guides.toggled.connect(self._renderer.set_show_safe_guides)
        dl.addWidget(self._cb_safe_guides)

        layout.addWidget(disp_card)

        # ---------------------------------------------------------------
        # 6. Theme & Background
        # ---------------------------------------------------------------
        theme_card, tl_theme = _create_card("THEME & BACKGROUND")

        tl_theme.addWidget(QLabel("Theme Palette"))
        self._palette_combo = QComboBox()
        self._palette_combo.addItems(get_palette_names())
        self._palette_combo.currentTextChanged.connect(self._on_palette_changed)
        tl_theme.addWidget(self._palette_combo)

        btn_from_image = QPushButton("🖼 Extract Palette From Photo...")
        btn_from_image.clicked.connect(self._palette_from_image)
        tl_theme.addWidget(btn_from_image)

        btn_bg_image = QPushButton("Load Background Photo...")
        btn_bg_image.clicked.connect(self._load_bg_image)
        tl_theme.addWidget(btn_bg_image)

        btn_bg_clear = QPushButton("Clear Background Photo")
        btn_bg_clear.clicked.connect(lambda: self._renderer.set_background_image(None))
        tl_theme.addWidget(btn_bg_clear)

        layout.addWidget(theme_card)

        # ---------------------------------------------------------------
        # 7. Creator & Credits
        # ---------------------------------------------------------------
        cred_card, cl_cred = _create_card("CREATOR & CREDITS")

        self._cb_watermark = QCheckBox("Show Creator Credit on Video")
        self._cb_watermark.setChecked(True)
        self._cb_watermark.toggled.connect(self._renderer.set_show_credits_watermark)
        cl_cred.addWidget(self._cb_watermark)

        btn_open_github = QPushButton("💻 Creator: Abijith Adithya (@abjxth)")
        btn_open_github.setStyleSheet("""
            QPushButton {
                background-color: #1a1a26;
                border: 1px solid #2e2e42;
                border-radius: 8px;
                color: #e4e4f2;
                padding: 8px 12px;
                font-weight: 800;
            }
            QPushButton:hover {
                background-color: #242436;
                border-color: #00d2c8;
                color: #00d2c8;
            }
        """)
        btn_open_github.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/abjxth")))
        cl_cred.addWidget(btn_open_github)

        layout.addWidget(cred_card)

        # ---------------------------------------------------------------
        # 8. Export Video
        # ---------------------------------------------------------------
        exp_card, el = _create_card("EXPORT VIDEO")

        el.addWidget(QLabel("Aspect Ratio"))
        self._aspect_combo = QComboBox()
        self._aspect_combo.addItems(list(ASPECT_RATIOS.keys()))
        el.addWidget(self._aspect_combo)

        el.addWidget(QLabel("Resolution"))
        self._res_combo = QComboBox()
        self._res_combo.addItems(list(RESOLUTIONS.keys()))
        self._res_combo.setCurrentText("1080p")
        el.addWidget(self._res_combo)

        el.addWidget(QLabel("Frame Rate (FPS)"))
        self._fps_combo = QComboBox()
        self._fps_combo.addItems(["30", "60"])
        self._fps_combo.setCurrentText("60")
        el.addWidget(self._fps_combo)

        time_row = QHBoxLayout()
        time_row.setSpacing(12)

        start_col = QVBoxLayout()
        start_col.setSpacing(4)
        start_col.addWidget(QLabel("Start Time (s)"))
        self._start_spin = QDoubleSpinBox()
        self._start_spin.setRange(0, 9999)
        self._start_spin.setDecimals(1)
        self._start_spin.setValue(0.0)
        start_col.addWidget(self._start_spin)
        time_row.addLayout(start_col)

        end_col = QVBoxLayout()
        end_col.setSpacing(4)
        end_col.addWidget(QLabel("End Time (s)"))
        self._end_spin = QDoubleSpinBox()
        self._end_spin.setRange(0, 9999)
        self._end_spin.setDecimals(1)
        self._end_spin.setValue(0.0)
        end_col.addWidget(self._end_spin)
        time_row.addLayout(end_col)
        el.addLayout(time_row)

        btn_export_card = QPushButton("⬇  Render & Export Video")
        btn_export_card.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00d2c8, stop:1 #00b4d8);
                color: #081212;
                font-weight: 800;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 13px;
                margin-top: 6px;
            }
            QPushButton:hover { background: #19ece2; }
            QPushButton:pressed { background: #00aba2; }
        """)
        btn_export_card.clicked.connect(self._export_video)
        el.addWidget(btn_export_card)

        layout.addWidget(exp_card)

        layout.addStretch()
        return panel

    def _build_transport(self) -> QWidget:
        transport = QWidget()
        transport.setObjectName("transport")
        transport.setFixedHeight(58)
        layout = QHBoxLayout(transport)
        layout.setContentsMargins(18, 0, 18, 0)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._btn_play = QPushButton("▶")
        self._btn_play.setObjectName("btn_play")
        self._btn_play.setToolTip("Play / Pause (Space)")
        self._btn_play.setFixedSize(36, 36)
        self._btn_play.clicked.connect(self._toggle_play)
        layout.addWidget(self._btn_play)

        btn_stop = QPushButton("■")
        btn_stop.setObjectName("btn_stop")
        btn_stop.setToolTip("Stop (Esc)")
        btn_stop.setFixedSize(36, 36)
        btn_stop.clicked.connect(self._stop)
        layout.addWidget(btn_stop)

        self._seek_slider = QSlider(Qt.Orientation.Horizontal)
        self._seek_slider.setRange(0, 10000)
        self._seek_slider.setValue(0)
        self._seek_slider.sliderMoved.connect(self._on_seek)
        layout.addWidget(self._seek_slider, 1)

        self._time_label = QLabel("0:00 / 0:00")
        self._time_label.setMinimumWidth(95)
        self._time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._time_label.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        self._time_label.setStyleSheet("color: #e0e0ea; background: transparent;")
        layout.addWidget(self._time_label)

        self._bpm_label = QLabel("120 BPM")
        self._bpm_label.setFont(QFont("Satoshi", 10, QFont.Weight.Bold))
        self._bpm_label.setStyleSheet("color: #00d2c8; background: #181824; border: 1px solid #28283a; border-radius: 6px; padding: 4px 10px;")
        layout.addWidget(self._bpm_label)

        self._key_label = QLabel("C")
        self._key_label.setFont(QFont("Satoshi", 10, QFont.Weight.Bold))
        self._key_label.setStyleSheet("color: #e0e0ea; background: #181824; border: 1px solid #28283a; border-radius: 6px; padding: 4px 10px;")
        layout.addWidget(self._key_label)

        return transport

    def _apply_style(self):
        self.setStyleSheet(DARK_STYLE)

    # ------------------------------------------------------------------
    # Song Title, BPM, Key Renaming
    # ------------------------------------------------------------------

    def _on_song_title_edited(self, text: str):
        self._multi_midi.custom_song_name = text
        self.setWindowTitle(f"Ethereal — {self._multi_midi.song_name}")
        self._renderer.update()

    def _on_bpm_edited(self, val: float):
        self._multi_midi.custom_bpm = val
        self._bpm_label.setText(f"{val:.0f} BPM")
        self._renderer.update()

    def _on_key_edited(self, text: str):
        self._multi_midi.custom_key = text
        self._key_label.setText(text)
        self._renderer.update()

    # ------------------------------------------------------------------
    # Multi-MIDI & Instrument Renaming
    # ------------------------------------------------------------------

    def _open_midi_dialog(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Open MIDI Files (Select One or Multiple)", "",
            "MIDI Files (*.mid *.midi);;All Files (*)"
        )
        if paths:
            for p in paths:
                self._load_midi_file(p)

    def _load_midi_file(self, filepath: str):
        try:
            loaded = self._multi_midi.add_midi(filepath)
            self._renderer.set_multi_midi(self._multi_midi)
            self._rebuild_midi_list_ui()
            self._update_song_metadata()
        except Exception as e:
            QMessageBox.critical(self, "MIDI Parse Error", f"Failed to load {os.path.basename(filepath)}:\n{e}")

    def _rebuild_midi_list_ui(self):
        while self._midi_list_layout.count():
            item = self._midi_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for m in self._multi_midi.midis:
            # Card for this MIDI
            card = QWidget()
            card.setStyleSheet("background-color: #171724; border: 1px solid #28283a; border-radius: 8px; padding: 2px;")
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(8, 8, 8, 8)
            c_layout.setSpacing(6)

            # Main MIDI File Row
            m_row = QHBoxLayout()
            m_row.setSpacing(8)

            col = QColor(*m.color)
            btn_col = QPushButton()
            btn_col.setFixedSize(22, 22)
            btn_col.setStyleSheet(f"background-color: {col.name()}; border: 2px solid rgba(255, 255, 255, 0.85); border-radius: 11px;")
            btn_col.setToolTip("Click to change note color for this instrument")
            btn_col.clicked.connect(lambda _, midi_id=m.id: self._pick_midi_color(midi_id))
            m_row.addWidget(btn_col)

            # Editable instrument/file name
            name_edit = QLineEdit(m.display_name)
            name_edit.setToolTip("Rename this instrument / MIDI file")
            name_edit.setStyleSheet("background: #1c1c28; border: 1px solid #2d2d40; border-radius: 6px; font-size: 11px; font-weight: 700; padding: 4px 8px; color: #ffffff;")
            name_edit.textChanged.connect(lambda txt, midi_id=m.id: self._on_midi_renamed(midi_id, txt))
            m_row.addWidget(name_edit, 1)

            cb_vis = QCheckBox()
            cb_vis.setChecked(m.visible)
            cb_vis.setToolTip("Toggle visibility")
            cb_vis.toggled.connect(lambda v, midi_id=m.id: self._toggle_midi_vis(midi_id, v))
            m_row.addWidget(cb_vis)

            btn_del = QPushButton("✕")
            btn_del.setFixedSize(22, 22)
            btn_del.setStyleSheet("color: #ff6666; background: transparent; font-size: 12px; font-weight: 800; border: none; border-radius: 4px;")
            btn_del.setToolTip("Remove this instrument")
            btn_del.clicked.connect(lambda _, midi_id=m.id: self._remove_midi(midi_id))
            m_row.addWidget(btn_del)

            c_layout.addLayout(m_row)

            # Individual tracks inside this MIDI if multiple
            if len(m.data.tracks) > 1:
                t_container = QWidget()
                tc_layout = QVBoxLayout(t_container)
                tc_layout.setContentsMargins(12, 0, 0, 0)
                tc_layout.setSpacing(4)

                for t in m.data.tracks:
                    t_row = QHBoxLayout()
                    t_row.setSpacing(6)

                    # Track dot
                    dot_color = QColor(*m.track_colors.get(t.index, m.color))
                    btn_t_col = QPushButton()
                    btn_t_col.setFixedSize(16, 16)
                    btn_t_col.setStyleSheet(f"background-color: {dot_color.name()}; border: 1px solid rgba(255, 255, 255, 0.7); border-radius: 8px;")
                    btn_t_col.clicked.connect(lambda _, midi_id=m.id, tidx=t.index: self._pick_track_color(midi_id, tidx))
                    t_row.addWidget(btn_t_col)

                    # Editable Track Name
                    t_name_edit = QLineEdit(m.get_track_name(t.index))
                    t_name_edit.setStyleSheet("background: #1c1c28; border: 1px solid #2a2a3c; border-radius: 6px; font-size: 10px; font-weight: 700; padding: 3px 6px; color: #e4e4f0;")
                    t_name_edit.textChanged.connect(lambda txt, midi_id=m.id, tidx=t.index: self._on_track_renamed(midi_id, tidx, txt))
                    t_row.addWidget(t_name_edit, 1)

                    tc_layout.addLayout(t_row)

                c_layout.addWidget(t_container)

            self._midi_list_layout.addWidget(card)

    def _on_midi_renamed(self, midi_id: str, new_name: str):
        self._multi_midi.set_midi_name(midi_id, new_name)
        self._renderer.update()

    def _on_track_renamed(self, midi_id: str, track_idx: int, new_name: str):
        self._multi_midi.set_track_name(midi_id, track_idx, new_name)
        self._renderer.update()

    def _pick_midi_color(self, midi_id: str):
        m = self._multi_midi.get_midi(midi_id)
        if not m:
            return
        chosen = QColorDialog.getColor(QColor(*m.color), self, f"Pick Color for {m.display_name}")
        if chosen.isValid():
            new_col = (chosen.red(), chosen.green(), chosen.blue())
            self._multi_midi.set_midi_color(midi_id, new_col)
            self._renderer.update()
            self._rebuild_midi_list_ui()

    def _pick_track_color(self, midi_id: str, track_idx: int):
        m = self._multi_midi.get_midi(midi_id)
        if not m:
            return
        initial = QColor(*m.track_colors.get(track_idx, m.color))
        chosen = QColorDialog.getColor(initial, self, "Pick Track Color")
        if chosen.isValid():
            new_col = (chosen.red(), chosen.green(), chosen.blue())
            self._multi_midi.set_track_color(midi_id, track_idx, new_col)
            self._renderer.update()
            self._rebuild_midi_list_ui()

    def _toggle_midi_vis(self, midi_id: str, visible: bool):
        m = self._multi_midi.get_midi(midi_id)
        if m:
            m.visible = visible
            self._renderer.update()

    def _remove_midi(self, midi_id: str):
        self._multi_midi.remove_midi(midi_id)
        self._renderer.set_multi_midi(self._multi_midi)
        self._rebuild_midi_list_ui()
        self._update_song_metadata()

    # ------------------------------------------------------------------
    # Audio Upload & Controls
    # ------------------------------------------------------------------

    def _open_audio_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Audio Track", "",
            "Audio Files (*.mp3 *.wav *.flac *.ogg *.m4a *.aac);;All Files (*)"
        )
        if path:
            self._load_audio_file(path)

    def _load_audio_file(self, filepath: str):
        try:
            self._audio_data = load_audio_waveform(filepath)
            self._renderer.set_audio_data(self._audio_data)
            self._audio_player.load_file(filepath)

            fn = os.path.basename(filepath)
            mins = int(self._audio_data.duration) // 60
            secs = int(self._audio_data.duration) % 60
            self._lbl_audio_name.setText(f"🎵 {fn} ({mins}:{secs:02d})")
            self._lbl_audio_name.setStyleSheet("color: #00d2c8; font-weight: 700;")
            self._btn_remove_audio.show()

            self._update_song_metadata()
        except Exception as e:
            QMessageBox.critical(self, "Audio Load Error", f"Failed to load audio:\n{e}")

    def _remove_audio(self):
        self._audio_player.stop()
        self._audio_data = None
        self._renderer.set_audio_data(None)
        self._lbl_audio_name.setText("No Audio")
        self._lbl_audio_name.setStyleSheet("color: #888; font-size: 11px;")
        self._btn_remove_audio.hide()
        self._update_song_metadata()

    # ------------------------------------------------------------------
    # Style & Waveform Changes
    # ------------------------------------------------------------------

    def _on_wave_style_changed(self, idx: int):
        styles = ["neon_bars", "smooth_wave", "dual_mountain", "circular_halo", "led_matrix", "minimal_line"]
        self._renderer.set_waveform_style(styles[idx])

    def _on_hit_type_changed(self, idx: int):
        types = ["glow_dot", "emoji", "ring_pulse", "sparkle_star", "diamond", "none"]
        self._renderer.set_hit_marker_type(types[idx])

    def _on_glow_style_changed(self, idx: int):
        styles = ["bloom", "neon_laser", "electric_flare", "particles"]
        self._renderer.set_glow_style(styles[idx])

    def _on_glow_color_mode_changed(self, text: str):
        mode_map = {
            "Match Note": "match_note",
            "White-Hot Core": "white_hot",
            "Playhead Accent": "accent",
            "Custom": "custom",
        }
        self._renderer.set_glow_color_mode(mode_map.get(text, "match_note"))

    def _pick_glow_custom_color(self):
        chosen = QColorDialog.getColor(QColor(0, 230, 210), self, "Select Custom Glow Color")
        if chosen.isValid():
            self._renderer.set_glow_color_mode("custom", chosen)
            self._glow_col_combo.setCurrentText("Custom")

    def _update_song_metadata(self):
        total_time = self._renderer.get_total_time()
        self._end_spin.setValue(total_time)
        song_name = self._multi_midi.song_name
        self._song_title_edit.blockSignals(True)
        self._song_title_edit.setText(song_name)
        self._song_title_edit.blockSignals(False)

        bpm = self._multi_midi.initial_bpm
        self._bpm_spin.blockSignals(True)
        self._bpm_spin.setValue(bpm)
        self._bpm_spin.blockSignals(False)
        self._bpm_label.setText(f"{bpm:.0f} BPM")

        key = self._multi_midi.key_signature
        self._key_edit.blockSignals(True)
        self._key_edit.setText(key)
        self._key_edit.blockSignals(False)
        self._key_label.setText(key)

        self.setWindowTitle(f"Ethereal — {song_name}")

    # ------------------------------------------------------------------
    # Credits Modal
    # ------------------------------------------------------------------

    def _show_credits_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Credits")
        dlg.setFixedSize(390, 270)
        dlg.setStyleSheet(DARK_STYLE)

        l = QVBoxLayout(dlg)
        l.setContentsMargins(26, 26, 26, 26)
        l.setSpacing(14)
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)

        t1 = QLabel("●  ETHEREAL")
        t1.setFont(QFont("Satoshi", 18, QFont.Weight.Black))
        t1.setStyleSheet("color: #00d2c8; letter-spacing: 2px; background: transparent;")
        t1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(t1)

        t2 = QLabel("Stylized MIDI and Audio Visualizer")
        t2.setFont(QFont("Satoshi", 11, QFont.Weight.Bold))
        t2.setStyleSheet("color: #88889a; background: transparent;")
        t2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(t2)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("border: none; background: rgba(255,255,255,0.08); max-height: 1px;")
        l.addWidget(line)

        t3 = QLabel("Created by Abijith Adithya")
        t3.setFont(QFont("Satoshi", 13, QFont.Weight.Black))
        t3.setStyleSheet("color: #ffffff; background: transparent;")
        t3.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(t3)

        btn_github = QPushButton("💻 GitHub Profile: github.com/abjxth")
        btn_github.setStyleSheet("""
            QPushButton {
                background-color: #1a1a26;
                border: 1px solid #2e2e42;
                color: #ffffff;
                padding: 9px 18px;
                font-weight: 800;
                font-size: 12px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #242436;
                border-color: #00d2c8;
                color: #00d2c8;
            }
        """)
        btn_github.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/abjxth")))
        l.addWidget(btn_github)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(dlg.accept)
        l.addWidget(btn_close)

        dlg.exec()

    # ------------------------------------------------------------------
    # Playback & Transport
    # ------------------------------------------------------------------

    def _toggle_play(self):
        if self._renderer.is_playing():
            self._renderer.pause()
            self._audio_player.pause()
            self._btn_play.setText("▶")
        else:
            self._renderer.play()
            if self._audio_player.has_audio():
                self._audio_player.play(self._renderer.get_time())
            self._btn_play.setText("⏸")

    def _stop(self):
        self._renderer.stop()
        self._audio_player.stop()
        self._btn_play.setText("▶")

    def _on_seek(self, value: int):
        total = self._renderer.get_total_time()
        time_s = (value / 10000.0) * total
        self._renderer.set_time(time_s)
        if self._audio_player.has_audio():
            self._audio_player.seek(time_s)

    def _update_time_display(self):
        cur = self._renderer.get_time()
        total = self._renderer.get_total_time()

        if not self._seek_slider.isSliderDown():
            pos = int((cur / max(total, 0.001)) * 10000)
            self._seek_slider.blockSignals(True)
            self._seek_slider.setValue(min(pos, 10000))
            self._seek_slider.blockSignals(False)

        def fmt(t):
            m = int(t) // 60
            s = int(t) % 60
            return f"{m}:{s:02d}"

        self._time_label.setText(f"{fmt(cur)} / {fmt(total)}")

        if self._renderer.is_playing() and cur >= total + 1.5:
            self._stop()

    # ------------------------------------------------------------------
    # Palette & Background
    # ------------------------------------------------------------------

    def _on_palette_changed(self, name: str):
        self._current_palette = get_palette(name)
        self._renderer.set_palette(self._current_palette)

    def _palette_from_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Image for Palette", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp);;All Files (*)"
        )
        if path:
            try:
                palette = extract_palette_from_image(path)
                self._current_palette = palette
                self._renderer.set_palette(palette)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to extract palette:\n{e}")

    def _load_bg_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp);;All Files (*)"
        )
        if path:
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                self._renderer.set_background_image(pixmap)

    # ------------------------------------------------------------------
    # Presets
    # ------------------------------------------------------------------

    def _on_preset_changed(self, name: str):
        presets = load_presets()
        for p in presets:
            if p.name == name:
                self._apply_preset(p)
                break

    def _apply_preset(self, preset: Preset):
        self._palette_combo.blockSignals(True)
        self._current_palette = get_palette(preset.palette_name)
        idx = self._palette_combo.findText(preset.palette_name)
        if idx >= 0:
            self._palette_combo.setCurrentIndex(idx)
        self._palette_combo.blockSignals(False)

        self._renderer.set_palette(self._current_palette)
        self._zoom_slider.setValue(int(preset.zoom * 100))
        self._note_h_combo.setCurrentIndex(preset.note_height_mode)
        self._cb_labels.setChecked(preset.show_note_labels)
        self._cb_chords.setChecked(preset.show_chord_names)
        self._cb_grid.setChecked(preset.show_beat_grid)
        self._cb_vel.setChecked(preset.show_velocity)
        self._glow_slider.setValue(int(preset.glow_intensity * 100))

        if hasattr(preset, "waveform_style"):
            idx_w = self._wave_style_combo.findText(preset.waveform_style.replace("_", " ").title())
            if idx_w >= 0:
                self._wave_style_combo.setCurrentIndex(idx_w)
        if hasattr(preset, "hit_marker_type"):
            self._renderer.set_hit_marker_type(preset.hit_marker_type)
        if hasattr(preset, "hit_marker_emoji"):
            self._emoji_edit.setText(preset.hit_marker_emoji)

    def _save_current_preset(self):
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Save Preset", "Preset name:")
        if ok and name.strip():
            wave_styles = ["neon_bars", "smooth_wave", "dual_mountain", "circular_halo", "led_matrix", "minimal_line"]
            hit_types = ["glow_dot", "emoji", "ring_pulse", "sparkle_star", "diamond", "none"]
            preset = Preset(
                name=name.strip(),
                palette_name=self._current_palette.name,
                zoom=self._zoom_slider.value() / 100.0,
                note_height_mode=self._note_h_combo.currentIndex(),
                show_note_labels=self._cb_labels.isChecked(),
                show_chord_names=self._cb_chords.isChecked(),
                show_beat_grid=self._cb_grid.isChecked(),
                show_velocity=self._cb_vel.isChecked(),
                glow_intensity=self._glow_slider.value() / 100.0,
                waveform_style=wave_styles[self._wave_style_combo.currentIndex()],
                waveform_height_scale=self._wave_h_slider.value() / 100.0,
                waveform_opacity=self._wave_op_slider.value() / 100.0,
                waveform_position=self._wave_pos_combo.currentText().lower(),
                hit_marker_type=hit_types[self._hit_type_combo.currentIndex()],
                hit_marker_emoji=self._emoji_edit.text(),
                hit_marker_size=self._marker_size_slider.value() / 100.0,
                aspect_ratio=self._aspect_combo.currentText(),
                resolution=self._res_combo.currentText(),
                fps=int(self._fps_combo.currentText()),
            )
            save_preset(preset)
            self._refresh_presets()

    def _refresh_presets(self):
        self._preset_combo.blockSignals(True)
        self._preset_combo.clear()
        for p in load_presets():
            self._preset_combo.addItem(p.name)
        self._preset_combo.blockSignals(False)

    # ------------------------------------------------------------------
    # Video Export
    # ------------------------------------------------------------------

    def _export_video(self):
        if not self._multi_midi.midis and not self._audio_data:
            QMessageBox.warning(self, "No Content", "Please load at least one MIDI or Audio file first.")
            return

        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            QMessageBox.critical(
                self, "FFmpeg Missing",
                "FFmpeg is required for video export.\nPlease ensure ffmpeg.exe is in the Ethereal folder."
            )
            return

        default_name = f"{self._multi_midi.song_name}.mp4"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Video", default_name,
            "MP4 Video (*.mp4);;All Files (*)"
        )
        if not path:
            return

        dialog = _ExportProgressDialog(self)
        audio_file = self._audio_data.filepath if self._audio_data else None

        worker = ExportWorker(
            renderer=self._renderer,
            palette=self._current_palette,
            output_path=path,
            total_duration=self._renderer.get_total_time(),
            aspect_ratio=self._aspect_combo.currentText(),
            resolution=self._res_combo.currentText(),
            fps=int(self._fps_combo.currentText()),
            start_time=self._start_spin.value(),
            end_time=self._end_spin.value(),
            ffmpeg_path=ffmpeg,
            audio_path=audio_file,
        )

        worker.progress.connect(dialog.update_progress)
        worker.frame_rendered.connect(dialog.update_preview)
        worker.finished_ok.connect(lambda p: self._on_export_done(dialog, p))
        worker.error.connect(lambda e: self._on_export_error(dialog, e))
        dialog.cancelled.connect(worker.cancel)

        self._export_worker = worker
        worker.start()
        dialog.exec()

    def _on_export_done(self, dialog: QDialog, path: str):
        dialog.accept()
        QMessageBox.information(self, "Export Complete", f"Video exported successfully:\n{path}")

    def _on_export_error(self, dialog: QDialog, error: str):
        dialog.reject()
        QMessageBox.critical(self, "Export Error", error)

    # ------------------------------------------------------------------
    # Drag & Drop Support
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                ext = url.toLocalFile().lower()
                if ext.endswith(('.mid', '.midi', '.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac')):
                    event.acceptProposedAction()
                    return

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            ext = path.lower()
            if ext.endswith(('.mid', '.midi')):
                self._load_midi_file(path)
            elif ext.endswith(('.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac')):
                self._load_audio_file(path)

    # ------------------------------------------------------------------
    # Keyboard Shortcuts
    # ------------------------------------------------------------------

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self._toggle_play()
        elif event.key() == Qt.Key.Key_Escape:
            self._stop()
        elif event.key() == Qt.Key.Key_O and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._open_midi_dialog()
        elif event.key() == Qt.Key.Key_E and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._export_video()
        else:
            super().keyPressEvent(event)


# ---------------------------------------------------------------------------
# Export Progress Dialog
# ---------------------------------------------------------------------------

class _ExportProgressDialog(QDialog):
    cancelled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Exporting Video (60fps)...")
        self.setFixedSize(440, 280)
        self.setModal(True)
        self.setStyleSheet(DARK_STYLE)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self._status = QLabel("Initializing encoder...")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setFont(QFont("Satoshi", 11, QFont.Weight.Bold))
        layout.addWidget(self._status)

        self._preview = QLabel()
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setFixedHeight(120)
        self._preview.setStyleSheet("background: #0e0e12; border-radius: 8px; border: 1px solid #282836;")
        layout.addWidget(self._preview)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        layout.addWidget(self._progress)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self._on_cancel)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #282834;
                border: 1px solid #404052;
                border-radius: 6px;
                padding: 7px 26px;
                color: #e2e2e8;
                font-weight: 800;
            }
            QPushButton:hover { background-color: #ff4444; border-color: #ff4444; color: #fff; }
        """)
        layout.addWidget(btn_cancel, alignment=Qt.AlignmentFlag.AlignCenter)

    def update_progress(self, current: int, total: int):
        pct = int(current / max(total, 1) * 100)
        self._progress.setValue(pct)
        self._status.setText(f"Rendering frame {current} / {total}  ({pct}%)")

    def update_preview(self, image):
        pixmap = QPixmap.fromImage(image)
        self._preview.setPixmap(pixmap)

    def _on_cancel(self):
        self.cancelled.emit()
        self.reject()
