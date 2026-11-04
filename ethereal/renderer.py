"""
Core visualization renderer for Ethereal.

Renders the stylized MIDI piano roll, real-time audio waveform,
customizable hit markers (emojis, glowing dots, stars, shockwaves),
and advanced glow effects with Satoshi typography.
"""
from __future__ import annotations

import math
import os
import random
from typing import Optional

import numpy as np
from PyQt6.QtCore import Qt, QRectF, QPointF, QTimer, QElapsedTimer
from PyQt6.QtGui import (
    QPainter, QPainterPath, QColor, QLinearGradient, QRadialGradient,
    QFont, QFontMetrics, QPen, QBrush, QImage, QPixmap
)
from PyQt6.QtWidgets import QWidget

from ethereal.midi_engine import MidiData, Note, TrackInfo, MultiMidiProject, detect_chord
from ethereal.palettes import ColorPalette, get_palette
from ethereal.audio_engine import AudioData


class Particle:
    """Spark particle emitted during note strikes."""
    __slots__ = ('x', 'y', 'vx', 'vy', 'color', 'life', 'max_life', 'size')

    def __init__(self, x: float, y: float, color: QColor, size: float = 3.0):
        self.x = x
        self.y = y
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(20.0, 90.0)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.color = color
        self.max_life = random.uniform(0.3, 0.7)
        self.life = self.max_life
        self.size = size

    def update(self, dt: float) -> bool:
        self.life -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        return self.life > 0


class MidiRenderer(QWidget):
    """
    The main visualization canvas. Renders multi-track MIDI piano roll,
    dynamic audio waveforms, custom hit markers (emojis/shapes), and glows.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 600)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        # ---- Data ----
        self._midi: Optional[MidiData] = None
        self._multi_midi: Optional[MultiMidiProject] = None
        self._audio: Optional[AudioData] = None
        self._palette: ColorPalette = get_palette("Ethereal")

        # ---- Playback state ----
        self._playing = False
        self._current_time: float = 0.0
        self._playback_timer = QTimer(self)
        self._playback_timer.setInterval(16)  # ~60fps
        self._playback_timer.timeout.connect(self._tick)
        self._elapsed = QElapsedTimer()
        self._play_start_time: float = 0.0

        # ---- Display settings ----
        self._zoom: float = 1.0
        self._note_height_mode: int = 1     # 0=small, 1=medium, 2=large
        self._show_note_labels: bool = True
        self._show_chord_names: bool = True
        self._show_beat_grid: bool = True
        self._show_velocity: bool = True
        self._show_credits_watermark: bool = True
        self._bg_image: Optional[QPixmap] = None
        self._bg_blur: float = 0.0

        # ---- Hit Markers & Glow Settings ----
        self._hit_marker_type: str = "glow_dot"  # glow_dot, emoji, ring_pulse, sparkle_star, diamond, none
        self._hit_marker_emoji: str = "🔥"
        self._hit_marker_size: float = 1.0
        self._glow_style: str = "bloom"         # bloom, neon_laser, electric_flare, particles
        self._glow_intensity: float = 0.8
        self._glow_color_mode: str = "match_note" # match_note, white_hot, accent, custom
        self._glow_custom_color: QColor = QColor(0, 230, 210)
        self._particles: list[Particle] = []
        self._last_tick_time: float = 0.0

        # ---- Waveform Settings ----
        self._waveform_style: str = "neon_bars" # neon_bars, smooth_wave, dual_mountain, circular_halo, led_matrix, minimal_line
        self._waveform_height_scale: float = 1.0
        self._waveform_opacity: float = 0.75
        self._waveform_position: str = "bottom" # bottom, center, background
        self._waveform_color_mode: str = "match_palette" # match_palette, accent, white, custom
        self._waveform_custom_color: QColor = QColor(0, 210, 200)

        # ---- Export mode ----
        self._export_mode: bool = False
        self._export_size: tuple[int, int] = (1080, 1920)

        # ---- Layout constants ----
        self._header_height = 120
        self._spectrum_height = 140
        self._playhead_x_ratio = 0.38

        # ---- Instagram Reels & YouTube Shorts Safe Framing ----
        self._reels_safe_framing: bool = True
        self._show_safe_guides: bool = False

        # ---- Cached values ----
        self._note_height: float = 8.0
        self._time_window: float = 6.0
        self._track_colors: dict[int, QColor] = {}

        # ---- Satoshi Bold Fonts ----
        self._font_family = "Satoshi"
        self._title_font = QFont("Satoshi", 22, QFont.Weight.Bold)
        self._info_font = QFont("Satoshi", 11, QFont.Weight.Bold)
        self._label_font = QFont("Satoshi", 9, QFont.Weight.Bold)
        self._pill_font = QFont("Satoshi", 10, QFont.Weight.Bold)
        self._chord_font = QFont("Satoshi", 13, QFont.Weight.Bold)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_midi_data(self, midi: Optional[MidiData]):
        """Load single MIDI data."""
        self._midi = midi
        if midi and not self._multi_midi:
            self._multi_midi = MultiMidiProject()
            self._multi_midi.add_midi(midi.filename)
        self._current_time = 0.0
        self._build_track_colors()
        self.update()

    def set_multi_midi(self, multi: MultiMidiProject):
        """Set multi-MIDI project instance."""
        self._multi_midi = multi
        self._midi = multi.midis[0].data if multi.midis else None
        self._build_track_colors()
        self.update()

    def set_audio_data(self, audio: Optional[AudioData]):
        """Attach audio data for waveform visualization."""
        self._audio = audio
        self.update()

    def set_palette(self, palette: ColorPalette):
        self._palette = palette
        self._build_track_colors()
        self.update()

    # ---- Style & Settings Setters ----

    def set_hit_marker_type(self, m_type: str):
        self._hit_marker_type = m_type
        self.update()

    def set_hit_marker_emoji(self, emoji: str):
        self._hit_marker_emoji = emoji or "🔥"
        self.update()

    def set_hit_marker_size(self, size: float):
        self._hit_marker_size = max(0.5, min(3.0, size))
        self.update()

    def set_glow_style(self, style: str):
        self._glow_style = style
        self.update()

    def set_glow_intensity(self, intensity: float):
        self._glow_intensity = max(0.0, min(2.0, intensity))
        self.update()

    def set_glow_color_mode(self, mode: str, custom_color: Optional[QColor] = None):
        self._glow_color_mode = mode
        if custom_color:
            self._glow_custom_color = custom_color
        self.update()

    def set_waveform_style(self, style: str):
        self._waveform_style = style
        self.update()

    def set_waveform_height(self, scale: float):
        self._waveform_height_scale = max(0.2, min(3.0, scale))
        self.update()

    def set_waveform_opacity(self, opacity: float):
        self._waveform_opacity = max(0.0, min(1.0, opacity))
        self.update()

    def set_waveform_position(self, pos: str):
        self._waveform_position = pos
        self.update()

    def set_reels_safe_framing(self, enable: bool):
        self._reels_safe_framing = enable
        self.update()

    def set_show_safe_guides(self, enable: bool):
        self._show_safe_guides = enable
        self.update()

    def set_zoom(self, zoom: float):
        self._zoom = max(0.3, min(5.0, zoom))
        self.update()

    def set_note_height_mode(self, mode: int):
        self._note_height_mode = mode
        self.update()

    def set_show_note_labels(self, show: bool):
        self._show_note_labels = show
        self.update()

    def set_show_chord_names(self, show: bool):
        self._show_chord_names = show
        self.update()

    def set_show_beat_grid(self, show: bool):
        self._show_beat_grid = show
        self.update()

    def set_show_velocity(self, show: bool):
        self._show_velocity = show
        self.update()

    def set_show_credits_watermark(self, show: bool):
        self._show_credits_watermark = show
        self.update()

    def set_background_image(self, pixmap: Optional[QPixmap]):
        self._bg_image = pixmap
        self.update()

    def set_time(self, time_s: float):
        self._current_time = max(0.0, time_s)
        self.update()

    def get_time(self) -> float:
        return self._current_time

    def play(self):
        if not self._has_content():
            return
        self._playing = True
        self._play_start_time = self._current_time
        self._last_tick_time = self._current_time
        self._elapsed.start()
        self._playback_timer.start()

    def pause(self):
        self._playing = False
        self._playback_timer.stop()

    def stop(self):
        self._playing = False
        self._playback_timer.stop()
        self._current_time = 0.0
        self._particles.clear()
        self.update()

    def is_playing(self) -> bool:
        return self._playing

    def get_total_time(self) -> float:
        t_midi = self._multi_midi.total_time if self._multi_midi else (self._midi.total_time if self._midi else 0.0)
        t_audio = self._audio.duration if self._audio else 0.0
        return max(t_midi, t_audio, 1.0)

    # ------------------------------------------------------------------
    # Export rendering
    # ------------------------------------------------------------------

    def render_frame(self, time_s: float, width: int, height: int) -> QImage:
        self._export_mode = True
        self._export_size = (width, height)
        self._current_time = time_s

        image = QImage(width, height, QImage.Format.Format_ARGB32)
        image.fill(QColor(*self._palette.background))

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self._paint(painter, width, height)
        painter.end()

        self._export_mode = False
        return image

    # ------------------------------------------------------------------
    # Internal & Animation
    # ------------------------------------------------------------------

    def _has_content(self) -> bool:
        return bool(self._multi_midi and self._multi_midi.midis) or bool(self._midi) or bool(self._audio)

    def _build_track_colors(self):
        self._track_colors.clear()
        if not self._multi_midi and not self._midi:
            return
        colors = self._palette.colors
        if self._multi_midi:
            for m in self._multi_midi.midis:
                for track in m.data.tracks:
                    color = m.track_colors.get(track.index, m.color)
                    self._track_colors[track.index] = QColor(*color)
        elif self._midi:
            for track in self._midi.tracks:
                idx = track.color_idx % len(colors)
                r, g, b = colors[idx]
                self._track_colors[track.index] = QColor(r, g, b)

    def _tick(self):
        if not self._has_content():
            return
        elapsed_s = self._elapsed.elapsed() / 1000.0
        prev_time = self._current_time
        self._current_time = self._play_start_time + elapsed_s
        dt = max(0.001, self._current_time - prev_time)

        # Update spark particles
        if self._glow_style == "particles" and self._particles:
            self._particles = [p for p in self._particles if p.update(dt)]

        total = self.get_total_time()
        if self._current_time >= total + 2.0:
            self.stop()
            return
        self.update()

    def paintEvent(self, event):
        w, h = self.width(), self.height()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self._paint(painter, w, h)
        painter.end()

    def _paint(self, p: QPainter, w: int, h: int):
        bg = self._palette.background

        # 1. Background
        if self._bg_image and not self._bg_image.isNull():
            scaled = self._bg_image.scaled(
                w, h, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            x = (w - scaled.width()) // 2
            y = (h - scaled.height()) // 2
            p.drawPixmap(x, y, scaled)
            p.fillRect(0, 0, w, h, QColor(bg[0], bg[1], bg[2], 180))
        else:
            p.fillRect(0, 0, w, h, QColor(*bg))

        # Vignette
        vignette = QRadialGradient(w / 2, h / 2, max(w, h) * 0.72)
        vignette.setColorAt(0, QColor(0, 0, 0, 0))
        vignette.setColorAt(1, QColor(0, 0, 0, 110))
        p.fillRect(0, 0, w, h, QBrush(vignette))

        if not self._has_content():
            self._draw_empty_state(p, w, h)
            return

        # Layout metrics
        is_vertical = (h > w * 1.1)
        scale = (h / 1920.0) if is_vertical else (h / 1080.0)

        if is_vertical and self._reels_safe_framing:
            # Instagram Reels & YouTube Shorts Safe Zone Bounds (optimized for 1080x1920)
            # Top UI: Phone camera punch-hole/notch, status bar, search & Reels audio tag (~220px)
            # Bottom UI: Instagram/Shorts account name, follow button, caption, audio bar & bottom navigation (~430px)
            # Right UI: Like, comment, share action column (~115px)
            safe_top = int(220 * scale)
            safe_bottom = int(h - 430 * scale)
            safe_right = int(w - 115 * scale)

            header_top = safe_top + int(24 * scale)
            header_content_h = int(165 * scale)
            header_h = header_top + header_content_h

            spec_h = int(110 * scale * self._waveform_height_scale)
            if self._waveform_position == "center":
                waveform_center_y = (safe_top + safe_bottom) / 2.0
                roll_bottom = safe_bottom
            elif self._waveform_position == "background":
                waveform_center_y = safe_top + (safe_bottom - safe_top) * 0.55
                roll_bottom = safe_bottom
            else:  # bottom docked safely above caption
                waveform_center_y = safe_bottom - spec_h / 2.0 - int(48 * scale)
                roll_bottom = safe_bottom - spec_h - int(60 * scale)

            roll_top = header_h + int(28 * scale)
            roll_height = max(120, roll_bottom - roll_top)
            playhead_x = int(w * 0.33)

        else:
            safe_top = 0
            safe_bottom = h
            safe_right = w
            header_top = 0
            header_h = int(self._header_height * scale)
            spec_h = int(self._spectrum_height * scale * self._waveform_height_scale)
            roll_top = header_h
            roll_bottom = h - spec_h if self._waveform_position != "background" else h
            roll_height = max(100, roll_bottom - roll_top)
            playhead_x = int(w * self._playhead_x_ratio)
            waveform_center_y = h - spec_h / 2.0 if self._waveform_position == "bottom" else (h / 2.0 if self._waveform_position == "center" else h * 0.6)

        self._time_window = 6.0 / self._zoom
        time_left = self._current_time - self._time_window * (playhead_x / max(w, 1))
        time_right = time_left + self._time_window

        # Pitch range
        min_p = self._multi_midi.min_pitch if self._multi_midi else (self._midi.min_pitch if self._midi else 36)
        max_p = self._multi_midi.max_pitch if self._multi_midi else (self._midi.max_pitch if self._midi else 84)
        pitch_range = max(max_p - min_p + 1, 12)

        base_note_h = roll_height / pitch_range
        mode_factors = [0.8, 1.25, 1.8]
        if is_vertical and self._reels_safe_framing:
            min_note_h = max(18.0, 24.0 * scale)
            max_note_h = max(26.0, 38.0 * scale)
            self._note_height = max(min_note_h, min(max_note_h, base_note_h * mode_factors[self._note_height_mode]))
        else:
            self._note_height = base_note_h * mode_factors[self._note_height_mode]

        # 2. Draw layers
        self._draw_beat_grid(p, w, roll_top, roll_bottom, playhead_x, time_left, time_right)
        self._draw_octave_lines(p, w, roll_top, roll_bottom, min_p, max_p, pitch_range)

        # Background position for waveform if selected
        if self._waveform_position == "background":
            self._draw_waveform_visualizer(p, w, h, spec_h, scale, is_vertical, waveform_center_y)

        self._draw_notes(p, w, roll_top, roll_bottom, playhead_x, time_left, time_right, min_p, pitch_range, scale, is_vertical, safe_right)
        self._draw_playhead(p, playhead_x, roll_top, roll_bottom, scale)
        self._draw_hit_markers_and_strikes(p, w, roll_top, roll_bottom, playhead_x, min_p, pitch_range, scale)
        self._draw_note_labels_at_playhead(p, w, roll_top, roll_bottom, playhead_x, min_p, pitch_range, scale)
        self._draw_chord_display(p, w, roll_top, playhead_x, scale, is_vertical)
        self._draw_header(p, w, header_h, scale, is_vertical, header_top)

        # Bottom / Center position for waveform
        if self._waveform_position != "background":
            self._draw_waveform_visualizer(p, w, h, spec_h, scale, is_vertical, waveform_center_y)

        # Creator credits watermark if enabled
        if self._show_credits_watermark:
            self._draw_credits_watermark(p, w, h, scale, is_vertical, safe_bottom)

        # Preview guides for Instagram Reels & YouTube Shorts
        if self._show_safe_guides and not self._export_mode and is_vertical:
            self._draw_social_guides(p, w, h, scale, safe_top, safe_bottom, safe_right)

    # ------------------------------------------------------------------
    # Subroutines
    # ------------------------------------------------------------------

    def _draw_empty_state(self, p: QPainter, w: int, h: int):
        p.setPen(QColor(255, 255, 255, 140))
        p.setFont(QFont(self._font_family, 18, QFont.Weight.Bold))
        p.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter,
                   "Drop MIDI or Audio files here\nor click Open MIDI / Load Audio")

        p.setPen(QColor(*self._palette.colors[0], 70))
        p.setFont(QFont(self._font_family, 48, QFont.Weight.Black))
        p.drawText(QRectF(0, h * 0.3, w, 80), Qt.AlignmentFlag.AlignCenter, "Ethereal")

    def _draw_credits_watermark(self, p: QPainter, w: int, h: int, scale: float,
                                is_vertical: bool = False, safe_bottom: int = 0):
        credit_text = "Visuals by Abijith Adithya  ·  github.com/abjxth"
        font_size = max(9, int((12 if is_vertical else 10) * scale))
        p.setFont(QFont(self._font_family, font_size, QFont.Weight.Bold))
        fm = QFontMetrics(p.font())
        tw = fm.horizontalAdvance(credit_text)
        th = fm.height()

        if is_vertical and safe_bottom > 0:
            # Placed comfortably centered right above the Instagram Reels / YouTube Shorts caption zone
            x = (w - tw) / 2
            y = safe_bottom - int(14 * scale)
        else:
            x = w - tw - int(18 * scale)
            y = h - int(14 * scale)

        badge_rect = QRectF(x - 10 * scale, y - th + 2 * scale, tw + 20 * scale, th + 6 * scale)
        p.setPen(QPen(QColor(255, 255, 255, 35), 1.0))
        p.setBrush(QColor(14, 14, 20, 210))
        p.drawRoundedRect(badge_rect, 6.0 * scale, 6.0 * scale)

        p.setPen(QColor(235, 235, 245, 230))
        p.drawText(QRectF(x, y - th + 4 * scale, tw + 10, th), Qt.AlignmentFlag.AlignLeft, credit_text)

    def _draw_header(self, p: QPainter, w: int, header_h: int, scale: float,
                     is_vertical: bool = False, header_top: int = 0):
        # Header subtle background gradient
        grad = QLinearGradient(0, header_top, 0, header_h + int(40 * scale))
        bg = self._palette.background
        grad.setColorAt(0, QColor(bg[0], bg[1], bg[2], 230 if not is_vertical else 185))
        grad.setColorAt(1, QColor(bg[0], bg[1], bg[2], 0))
        p.fillRect(0, 0, w, header_h + int(40 * scale), QBrush(grad))

        tc = self._palette.text_color
        y = header_top + int(4 * scale)

        song_name = "Ethereal"
        bpm = 120.0
        key_sig = "C"

        if self._multi_midi and self._multi_midi.midis:
            song_name = self._multi_midi.song_name
            bpm = self._multi_midi.initial_bpm
            key_sig = self._multi_midi.key_signature
        elif self._midi:
            song_name = self._midi.song_name
            bpm = self._midi.initial_bpm
            key_sig = self._midi.key_signature
        elif self._audio:
            song_name = os.path.splitext(self._audio.filename)[0]

        # Song title (Satoshi Bold) — prominent & cinematic on mobile screens
        title_size = max(18, int((38 if is_vertical else 22) * scale))
        p.setFont(QFont(self._font_family, title_size, QFont.Weight.Bold))
        # Subtle drop shadow for crisp legibility
        p.setPen(QColor(0, 0, 0, 160))
        p.drawText(QRectF(0, y + int(2 * scale), w, title_size * 2), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, song_name)
        p.setPen(QColor(*tc))
        p.drawText(QRectF(0, y, w, title_size * 2), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, song_name)

        # BPM · Key
        y += int(title_size + (24 if is_vertical else 12) * scale)
        info_size = max(11, int((16 if is_vertical else 11) * scale))
        p.setFont(QFont(self._font_family, info_size, QFont.Weight.Bold))
        p.setPen(QColor(tc[0], tc[1], tc[2], 215))
        info_text = f"{bpm:.0f} BPM  ·  {key_sig}"
        p.drawText(QRectF(0, y, w, info_size * 2), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, info_text)

        # Track pills
        tracks_to_show: list[tuple[str, QColor, bool]] = []
        if self._multi_midi:
            for m in self._multi_midi.midis:
                for t in m.data.tracks:
                    color = QColor(*m.track_colors.get(t.index, m.color))
                    t_name = m.get_track_name(t.index)
                    tracks_to_show.append((t_name, color, m.visible and t.visible))
        elif self._midi:
            for t in self._midi.tracks:
                color = self._track_colors.get(t.index, QColor(0, 210, 200))
                tracks_to_show.append((t.name, color, t.visible))

        if not tracks_to_show:
            return

        y += int(info_size + (22 if is_vertical else 14) * scale)
        pill_h = max(24, int((36 if is_vertical else 24) * scale))
        pill_font_size = max(9, int((13 if is_vertical else 10) * scale))
        p.setFont(QFont(self._font_family, pill_font_size, QFont.Weight.Bold))
        fm = QFontMetrics(p.font())

        pill_widths = [fm.horizontalAdvance(name) + int((38 if is_vertical else 32) * scale) for name, _, _ in tracks_to_show]
        gap = int((10 if is_vertical else 6) * scale)
        total_w = sum(pill_widths) + gap * (len(pill_widths) - 1)
        x = (w - total_w) / 2

        for i, (name, color, visible) in enumerate(tracks_to_show):
            pw = pill_widths[i]
            path = QPainterPath()
            path.addRoundedRect(QRectF(x, y, pw, pill_h), pill_h / 2, pill_h / 2)

            if visible:
                pill_bg = QColor(color.red(), color.green(), color.blue(), 55)
                border = QColor(color.red(), color.green(), color.blue(), 210)
            else:
                pill_bg = QColor(50, 50, 56, 120)
                border = QColor(70, 70, 78, 90)

            p.fillPath(path, pill_bg)
            p.setPen(QPen(border, max(1.2, 1.6 * scale)))
            p.drawPath(path)

            # Dot
            dot_r = max(4, int((5 if is_vertical else 4) * scale))
            dot_x = x + int((14 if is_vertical else 11) * scale)
            dot_y = y + pill_h / 2
            p.setBrush(color if visible else QColor(75, 75, 80))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(dot_x, dot_y), dot_r, dot_r)

            # Name
            p.setPen(QColor(*tc) if visible else QColor(130, 130, 135))
            text_x = dot_x + dot_r + int(7 * scale)
            p.drawText(QRectF(text_x, y, pw - (text_x - x) - 6, pill_h),
                       Qt.AlignmentFlag.AlignVCenter, name)

            x += pw + gap

    def _draw_beat_grid(self, p: QPainter, w: int, top: int, bottom: int,
                        playhead_x: int, time_left: float, time_right: float):
        if not self._show_beat_grid:
            return
        bpm = self._multi_midi.initial_bpm if self._multi_midi else (self._midi.initial_bpm if self._midi else 120.0)
        beat_duration = 60.0 / bpm
        beats_per_bar = 4

        first_beat = max(0, int(time_left / beat_duration))
        last_beat = int(time_right / beat_duration) + 1
        gc = self._palette.grid_color
        pixels_per_sec = w / self._time_window

        for beat_num in range(first_beat, last_beat + 1):
            beat_time = beat_num * beat_duration
            x = playhead_x + (beat_time - self._current_time) * pixels_per_sec
            if 0 <= x <= w:
                is_bar = (beat_num % beats_per_bar) == 0
                alpha = 35 if is_bar else 14
                p.setPen(QPen(QColor(gc[0], gc[1], gc[2], alpha), 1.0 if is_bar else 0.5))
                p.drawLine(int(x), top, int(x), bottom)

    def _draw_octave_lines(self, p: QPainter, w: int, top: int, bottom: int,
                           min_p: int, max_p: int, pitch_range: int):
        roll_h = bottom - top
        gc = self._palette.grid_color
        for pitch in range(0, 128, 12):
            if pitch < min_p or pitch > max_p:
                continue
            norm = (pitch - min_p) / pitch_range
            y = bottom - norm * roll_h
            p.setPen(QPen(QColor(gc[0], gc[1], gc[2], 18), 0.5))
            p.drawLine(0, int(y), w, int(y))

    def _draw_notes(self, p: QPainter, w: int, top: int, bottom: int,
                    playhead_x: int, time_left: float, time_right: float,
                    min_p: int, pitch_range: int, scale: float,
                    is_vertical: bool = False, safe_right: int = 1080):
        notes = self._multi_midi.get_all_notes() if self._multi_midi else (self._midi.notes if self._midi else [])
        if not notes:
            return

        roll_h = bottom - top
        pixels_per_sec = w / self._time_window
        note_h = self._note_height
        half_h = note_h / 2
        radius = min(note_h / 2.0, 7.5 * scale)

        vis_left = time_left - 1.5
        vis_right = time_right + 1.5

        for note in notes:
            if note.end_time < vis_left or note.start_time > vis_right:
                continue

            color = QColor(*note.color_override) if note.color_override else self._track_colors.get(note.track_idx, QColor(0, 210, 200))
            x1 = playhead_x + (note.start_time - self._current_time) * pixels_per_sec
            x2 = playhead_x + (note.end_time - self._current_time) * pixels_per_sec
            note_w = max(4, x2 - x1)

            norm_pitch = (note.pitch - min_p) / pitch_range
            y = bottom - norm_pitch * roll_h - half_h

            dist_from_now = abs(((note.start_time + note.end_time) / 2) - self._current_time)
            fade = max(0.2, 1.0 - (dist_from_now / (self._time_window / 2)) * 0.62)
            if note.end_time < self._current_time:
                fade *= 0.55

            # Smooth right-edge alpha fade near action buttons column in vertical mode
            if is_vertical and x2 > safe_right:
                right_fade = max(0.15, 1.0 - (x2 - safe_right) / max(1.0, w - safe_right))
                fade *= right_fade

            vel_factor = (0.45 + 0.55 * (note.velocity / 127.0)) if self._show_velocity else 1.0
            alpha = int(255 * fade * vel_factor)
            note_color = QColor(color.red(), color.green(), color.blue(), alpha)

            is_active = (note.start_time <= self._current_time <= note.end_time)

            # Draw note body
            note_rect = QRectF(x1, y, note_w, note_h)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(note_color)
            p.drawRoundedRect(note_rect, radius, radius)

            # Active note stroke & bloom
            if is_active:
                p.setPen(QPen(QColor(255, 255, 255, int(220 * vel_factor)), max(1.5, 2.0 * scale)))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRoundedRect(note_rect, radius, radius)

    def _draw_playhead(self, p: QPainter, x: int, top: int, bottom: int, scale: float):
        pc = self._palette.playhead_color
        p.setPen(QPen(QColor(*pc), max(2.0, 3.0 * scale)))
        p.drawLine(x, top, x, bottom)

        # Ambient glow behind playhead
        if self._glow_intensity > 0:
            for i in range(1, 4):
                alpha = int(35 * self._glow_intensity / i)
                p.setPen(QPen(QColor(pc[0], pc[1], pc[2], alpha), i * 3.5 * scale))
                p.drawLine(x, top, x, bottom)

    def _draw_hit_markers_and_strikes(self, p: QPainter, w: int, top: int, bottom: int,
                                      playhead_x: int, min_p: int, pitch_range: int, scale: float):
        """Render customizable hit markers (emojis, glowing dots, shockwaves) and glow styles on active notes."""
        notes = self._multi_midi.get_all_notes() if self._multi_midi else (self._midi.notes if self._midi else [])
        if not notes:
            return

        roll_h = bottom - top
        note_h = self._note_height
        half_h = note_h / 2
        now = self._current_time

        for note in notes:
            # Check if active
            if not (note.start_time <= now <= note.end_time):
                continue

            color = QColor(*note.color_override) if note.color_override else self._track_colors.get(note.track_idx, QColor(0, 210, 200))
            norm_pitch = (note.pitch - min_p) / pitch_range
            center_y = bottom - norm_pitch * roll_h

            time_since_hit = now - note.start_time
            hit_progress = min(1.0, max(0.0, time_since_hit / 0.25))  # 0.0 at strike to 1.0 after 250ms
            strike_pop = math.sin(hit_progress * math.pi) if hit_progress < 1.0 else 0.0

            # 1. Customizable Glow Effect on Note
            self._render_note_glow(p, playhead_x, center_y, color, note_h, strike_pop, scale)

            # 2. Customizable Hit Marker
            self._render_hit_marker(p, playhead_x, center_y, color, note_h, strike_pop, time_since_hit, scale)

    def _render_note_glow(self, p: QPainter, x: float, y: float, color: QColor,
                          note_h: float, strike_pop: float, scale: float):
        if self._glow_intensity <= 0:
            return

        # Determine glow color
        if self._glow_color_mode == "match_note":
            g_col = color
        elif self._glow_color_mode == "white_hot":
            g_col = QColor(255, 255, 255)
        elif self._glow_color_mode == "accent":
            ac = self._palette.playhead_color
            g_col = QColor(*ac)
        else:
            g_col = self._glow_custom_color

        intensity = self._glow_intensity * (1.0 + strike_pop * 0.8)

        if self._glow_style == "bloom":
            # Radial Gaussian-like Bloom
            glow_r = note_h * (2.8 + strike_pop * 1.5) * scale
            grad = QRadialGradient(x, y, glow_r)
            grad.setColorAt(0, QColor(255, 255, 255, int(min(255, 140 * intensity))))
            grad.setColorAt(0.35, QColor(g_col.red(), g_col.green(), g_col.blue(), int(min(255, 90 * intensity))))
            grad.setColorAt(1.0, QColor(g_col.red(), g_col.green(), g_col.blue(), 0))
            p.setBrush(QBrush(grad))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(x, y), glow_r, glow_r)

        elif self._glow_style == "neon_laser":
            # Piercing intense neon beam with white hot core
            glow_w = (40.0 + strike_pop * 30.0) * scale
            glow_h = note_h * (2.0 + strike_pop * 0.8) * scale
            grad = QRadialGradient(x, y, glow_w)
            grad.setColorAt(0, QColor(255, 255, 255, int(min(255, 220 * intensity))))
            grad.setColorAt(0.5, QColor(g_col.red(), g_col.green(), g_col.blue(), int(min(255, 120 * intensity))))
            grad.setColorAt(1.0, QColor(g_col.red(), g_col.green(), g_col.blue(), 0))
            p.setBrush(QBrush(grad))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(x, y), glow_w, glow_h)

        elif self._glow_style == "electric_flare":
            # Horizontal flare streak
            flare_len = (80.0 + strike_pop * 60.0) * scale
            p.setPen(QPen(QColor(255, 255, 255, int(min(255, 180 * intensity))), 2.0 * scale))
            p.drawLine(int(x - flare_len), int(y), int(x + flare_len), int(y))
            p.setPen(QPen(QColor(g_col.red(), g_col.green(), g_col.blue(), int(min(255, 90 * intensity))), 5.0 * scale))
            p.drawLine(int(x - flare_len * 0.7), int(y), int(x + flare_len * 0.7), int(y))

        elif self._glow_style == "particles":
            # Spawn spark particles on new strike
            if strike_pop > 0.6 and len(self._particles) < 120:
                for _ in range(2):
                    self._particles.append(Particle(x, y, g_col, size=3.0 * scale))
            # Render existing particles
            for part in self._particles:
                alpha = int(255 * (part.life / part.max_life))
                p.setBrush(QColor(part.color.red(), part.color.green(), part.color.blue(), alpha))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPointF(part.x, part.y), part.size, part.size)

    def _render_hit_marker(self, p: QPainter, x: float, y: float, color: QColor,
                           note_h: float, strike_pop: float, time_since_hit: float, scale: float):
        m_type = self._hit_marker_type
        if m_type == "none":
            return

        size = (note_h * 1.6 * self._hit_marker_size) * (1.0 + strike_pop * 0.4) * scale

        if m_type == "emoji":
            # Emoji Marker (Customizable Emoji / Symbol)
            font_size = max(10, int(size * 1.3))
            p.setFont(QFont("Segoe UI Emoji", font_size))
            emoji = self._hit_marker_emoji or "🔥"
            fm = QFontMetrics(p.font())
            tw = fm.horizontalAdvance(emoji)
            th = fm.height()
            rect = QRectF(x - tw / 2, y - th / 2, tw, th)
            p.setPen(QColor(255, 255, 255))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, emoji)

        elif m_type == "glow_dot":
            # Stylized Glowing Orb / Dot with halo bloom
            p.setPen(Qt.PenStyle.NoPen)
            # Core
            p.setBrush(QColor(255, 255, 255, 240))
            p.drawEllipse(QPointF(x, y), size * 0.4, size * 0.4)
            # Halo
            halo_r = size * 0.85
            grad = QRadialGradient(x, y, halo_r)
            grad.setColorAt(0, QColor(color.red(), color.green(), color.blue(), 180))
            grad.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))
            p.setBrush(QBrush(grad))
            p.drawEllipse(QPointF(x, y), halo_r, halo_r)

        elif m_type == "ring_pulse":
            # Shockwave ring expanding outward from the strike point
            ring_r = size * (0.6 + strike_pop * 1.5)
            alpha = int(max(0, 240 * (1.0 - strike_pop * 0.8)))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(color.red(), color.green(), color.blue(), alpha), 2.0 * scale))
            p.drawEllipse(QPointF(x, y), ring_r, ring_r)
            # Center bright pip
            p.setBrush(QColor(255, 255, 255, 220))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(x, y), size * 0.3, size * 0.3)

        elif m_type == "sparkle_star":
            # 4-point Star (✦) with luminous radial halo
            star_size = max(14, int(size * 1.5))
            # Glowing core
            grad = QRadialGradient(x, y, star_size * 0.9)
            grad.setColorAt(0, QColor(255, 255, 255, 245))
            grad.setColorAt(0.4, QColor(color.red(), color.green(), color.blue(), int(180 * (1.0 + strike_pop * 0.5))))
            grad.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))
            p.setBrush(QBrush(grad))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(x, y), star_size * 0.9, star_size * 0.9)

            # Crisp star glyph
            p.setFont(QFont(self._font_family, star_size, QFont.Weight.Bold))
            star_char = "✦"
            fm = QFontMetrics(p.font())
            tw = fm.horizontalAdvance(star_char)
            th = fm.height()
            p.setPen(QColor(255, 255, 255, 255))
            p.drawText(QRectF(x - tw / 2, y - th / 2, tw, th), Qt.AlignmentFlag.AlignCenter, star_char)

        elif m_type == "diamond":
            # Rotated Diamond (◆)
            path = QPainterPath()
            d = size * 0.7
            path.moveTo(x, y - d)
            path.lineTo(x + d, y)
            path.lineTo(x, y + d)
            path.lineTo(x - d, y)
            path.closeSubpath()
            p.fillPath(path, QColor(255, 255, 255, 220))
            p.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 200), 1.5 * scale))
            p.drawPath(path)

    def _draw_note_labels_at_playhead(self, p: QPainter, w: int, top: int, bottom: int,
                                      playhead_x: int, min_p: int, pitch_range: int, scale: float):
        if not self._show_note_labels:
            return
        notes = self._multi_midi.get_all_notes() if self._multi_midi else (self._midi.notes if self._midi else [])
        if not notes:
            return

        roll_h = bottom - top
        note_h = self._note_height
        font_size = max(7, int(9 * scale))
        p.setFont(QFont(self._font_family, font_size, QFont.Weight.Bold))
        fm = QFontMetrics(p.font())

        for note in notes:
            if not (note.start_time <= self._current_time <= note.end_time):
                continue

            color = QColor(*note.color_override) if note.color_override else self._track_colors.get(note.track_idx, QColor(0, 210, 200))
            norm = (note.pitch - min_p) / pitch_range
            y = bottom - norm * roll_h - note_h / 2

            name = note.note_name
            tw = fm.horizontalAdvance(name) + int(12 * scale)
            th = fm.height() + int(3 * scale)
            lx = playhead_x + int(8 * scale)
            ly = y + (note_h - th) / 2

            path = QPainterPath()
            path.addRoundedRect(QRectF(lx, ly, tw, th), th / 2, th / 2)
            p.fillPath(path, QColor(color.red(), color.green(), color.blue(), 220))
            p.setPen(QPen(QColor(255, 255, 255, 120), 1.0))
            p.drawPath(path)

            p.setPen(QColor(255, 255, 255))
            p.drawText(QRectF(lx, ly, tw, th), Qt.AlignmentFlag.AlignCenter, name)

    def _draw_chord_display(self, p: QPainter, w: int, top: int, playhead_x: int, scale: float, is_vertical: bool = False):
        if not self._show_chord_names:
            return
        notes = self._multi_midi.get_all_notes() if self._multi_midi else (self._midi.notes if self._midi else [])
        if not notes:
            return

        active_pitches = [n.pitch for n in notes if n.start_time <= self._current_time <= n.end_time]
        chord_name = detect_chord(active_pitches)
        if not chord_name:
            return

        font_size = max(11, int((16 if is_vertical else 13) * scale))
        p.setFont(QFont(self._font_family, font_size, QFont.Weight.Bold))
        fm = QFontMetrics(p.font())
        tw = fm.horizontalAdvance(chord_name) + int((24 if is_vertical else 18) * scale)
        th = fm.height() + int((10 if is_vertical else 8) * scale)

        x = playhead_x - tw / 2
        y = top - th - int((10 if is_vertical else 6) * scale)

        path = QPainterPath()
        path.addRoundedRect(QRectF(x, y, tw, th), th / 2, th / 2)
        p.fillPath(path, QColor(16, 16, 24, 230))
        p.setPen(QPen(QColor(0, 210, 200, 230), max(1.2, 1.6 * scale)))
        p.drawPath(path)
        p.setPen(QColor(255, 255, 255, 250))
        p.drawText(QRectF(x, y, tw, th), Qt.AlignmentFlag.AlignCenter, chord_name)

    # ------------------------------------------------------------------
    # Dynamic Waveform Visualizer (6 Styles)
    # ------------------------------------------------------------------

    def _draw_waveform_visualizer(self, p: QPainter, w: int, h: int, spec_h: int, scale: float,
                                  is_vertical: bool = False, custom_center_y: Optional[float] = None):
        """Draw gorgeous audio-reactive waveform in one of 6 distinct styles."""
        if spec_h <= 0:
            return

        # Determine base color
        if self._waveform_color_mode == "match_palette":
            c = self._palette.colors[0]
            base_col = QColor(*c)
        elif self._waveform_color_mode == "accent":
            c = self._palette.playhead_color
            base_col = QColor(*c)
        elif self._waveform_color_mode == "white":
            base_col = QColor(240, 240, 245)
        else:
            base_col = self._waveform_custom_color

        opacity = self._waveform_opacity

        # Y center position
        if custom_center_y is not None:
            center_y = custom_center_y
        elif self._waveform_position == "center":
            center_y = h / 2.0
        elif self._waveform_position == "background":
            center_y = h * 0.6
        else:  # bottom
            center_y = h - spec_h / 2.0

        # Retrieve waveform data from real AudioData or generate from MIDI notes
        num_points = 54 if is_vertical else 64
        if self._audio and len(self._audio.peaks) > 0:
            # Sliced audio window around current time (±1.5 seconds)
            amps = self._audio.get_window(self._current_time - 1.5, self._current_time + 1.5, num_points)
        else:
            # Smart pseudo-waveform from active MIDI notes
            amps = self._generate_pseudo_waveform(num_points)

        max_amp = spec_h * 0.48 * scale
        style = self._waveform_style

        # Horizontal safe margin
        margin_x = int((70 if is_vertical else 20) * scale)
        usable_w = w - margin_x * 2

        # Separator line if at bottom in landscape mode
        if self._waveform_position == "bottom" and not is_vertical:
            p.setPen(QPen(QColor(255, 255, 255, 15), 0.5))
            p.drawLine(0, int(h - spec_h), w, int(h - spec_h))

        # ---------------------------------------------------------------
        # Style 1: Neon Pulse Bars (Mirrored rounded bars with gradient)
        # ---------------------------------------------------------------
        if style == "neon_bars":
            bar_w = usable_w / num_points
            gap = max(1.5 * scale, bar_w * 0.25)
            for i, amp in enumerate(amps):
                bar_h = max(4.0 * scale, amp * max_amp * 2.2)
                bx = margin_x + i * bar_w
                by = center_y - bar_h / 2.0
                rect = QRectF(bx, by, bar_w - gap, bar_h)

                grad = QLinearGradient(bx, by, bx, by + bar_h)
                grad.setColorAt(0, QColor(base_col.red(), base_col.green(), base_col.blue(), int(245 * opacity)))
                grad.setColorAt(0.5, QColor(255, 255, 255, int(255 * opacity)))
                grad.setColorAt(1, QColor(base_col.red(), base_col.green(), base_col.blue(), int(190 * opacity)))

                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(grad))
                p.drawRoundedRect(rect, 2.5 * scale, 2.5 * scale)

                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(grad))
                p.drawRoundedRect(rect, 2.0 * scale, 2.0 * scale)

        # ---------------------------------------------------------------
        # Style 2: Smooth Glowing Wave (Oscilloscope fluid curve)
        # ---------------------------------------------------------------
        elif style == "smooth_wave":
            path = QPainterPath()
            step = w / (num_points - 1)
            points = []
            for i, amp in enumerate(amps):
                px = i * step
                py = center_y - (amp - 0.5) * max_amp * 2.2
                points.append(QPointF(px, py))

            path.moveTo(points[0])
            for i in range(1, len(points)):
                # Smooth curve
                p_prev = points[i - 1]
                p_curr = points[i]
                c_x = (p_prev.x() + p_curr.x()) / 2
                path.cubicTo(c_x, p_prev.y(), c_x, p_curr.y(), p_curr.x(), p_curr.y())

            # Glow aura
            p.setBrush(Qt.BrushStyle.NoBrush)
            for g in range(3, 0, -1):
                p.setPen(QPen(QColor(base_col.red(), base_col.green(), base_col.blue(), int(60 * opacity / g)), g * 3.5 * scale))
                p.drawPath(path)

            # Bright main line
            p.setPen(QPen(QColor(255, 255, 255, int(230 * opacity)), 2.0 * scale))
            p.drawPath(path)

        # ---------------------------------------------------------------
        # Style 3: Dual Area Mountain (Mirrored gradient peaks)
        # ---------------------------------------------------------------
        elif style == "dual_mountain":
            top_path = QPainterPath()
            bot_path = QPainterPath()
            step = w / (num_points - 1)

            top_path.moveTo(0, center_y)
            bot_path.moveTo(0, center_y)

            for i, amp in enumerate(amps):
                px = i * step
                top_y = center_y - amp * max_amp * 1.8
                bot_y = center_y + amp * max_amp * 1.8
                top_path.lineTo(px, top_y)
                bot_path.lineTo(px, bot_y)

            top_path.lineTo(w, center_y)
            top_path.closeSubpath()
            bot_path.lineTo(w, center_y)
            bot_path.closeSubpath()

            grad_top = QLinearGradient(0, center_y - max_amp, 0, center_y)
            grad_top.setColorAt(0, QColor(base_col.red(), base_col.green(), base_col.blue(), int(200 * opacity)))
            grad_top.setColorAt(1, QColor(base_col.red(), base_col.green(), base_col.blue(), 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.fillPath(top_path, QBrush(grad_top))

            grad_bot = QLinearGradient(0, center_y, 0, center_y + max_amp)
            grad_bot.setColorAt(0, QColor(base_col.red(), base_col.green(), base_col.blue(), int(200 * opacity)))
            grad_bot.setColorAt(1, QColor(base_col.red(), base_col.green(), base_col.blue(), 0))
            p.fillPath(bot_path, QBrush(grad_bot))

        # ---------------------------------------------------------------
        # Style 4: Circular Radial Halo
        # ---------------------------------------------------------------
        elif style == "circular_halo":
            radius = max_amp * 1.4
            cx = w * self._playhead_x_ratio
            cy = center_y
            angle_step = (2 * math.pi) / num_points

            for i, amp in enumerate(amps):
                angle = i * angle_step
                r1 = radius
                r2 = radius + amp * max_amp * 1.2
                x1 = cx + math.cos(angle) * r1
                y1 = cy + math.sin(angle) * r1
                x2 = cx + math.cos(angle) * r2
                y2 = cy + math.sin(angle) * r2

                p.setPen(QPen(QColor(base_col.red(), base_col.green(), base_col.blue(), int(200 * opacity)), 2.0 * scale))
                p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # ---------------------------------------------------------------
        # Style 5: Segmented LED Matrix Bars
        # ---------------------------------------------------------------
        elif style == "led_matrix":
            bar_w = (w - 40) / num_points
            segments = 8
            seg_gap = 2.0 * scale
            seg_h = (max_amp * 1.8) / segments - seg_gap

            for i, amp in enumerate(amps):
                active_segs = int(amp * segments)
                bx = 20 + i * bar_w
                for s in range(segments):
                    sy = center_y + max_amp * 0.9 - (s + 1) * (seg_h + seg_gap)
                    is_lit = s <= active_segs
                    if is_lit:
                        if s >= segments - 2:
                            col = QColor(255, 120, 50, int(240 * opacity))
                        else:
                            col = QColor(base_col.red(), base_col.green(), base_col.blue(), int(220 * opacity))
                    else:
                        col = QColor(40, 40, 45, int(60 * opacity))

                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(col)
                    p.drawRoundedRect(QRectF(bx, sy, bar_w - 2.0, seg_h), 1.0, 1.0)

        # ---------------------------------------------------------------
        # Style 6: Minimalist Line
        # ---------------------------------------------------------------
        else:  # minimal_line
            step = w / (num_points - 1)
            for i in range(len(amps) - 1):
                x1 = i * step
                y1 = center_y - (amps[i] - 0.5) * max_amp * 1.5
                x2 = (i + 1) * step
                y2 = center_y - (amps[i + 1] - 0.5) * max_amp * 1.5
                p.setPen(QPen(QColor(255, 255, 255, int(220 * opacity)), 1.5 * scale))
                p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def _generate_pseudo_waveform(self, num_points: int) -> np.ndarray:
        """Create responsive pseudo-waveform from active MIDI note pitches and velocities."""
        notes = self._multi_midi.get_all_notes() if self._multi_midi else (self._midi.notes if self._midi else [])
        amps = np.full(num_points, 0.08, dtype=np.float32)
        if not notes:
            return amps

        now = self._current_time
        active_notes = [n for n in notes if n.start_time <= now <= n.end_time]

        for note in active_notes:
            center_idx = int((note.pitch / 127.0) * (num_points - 1))
            vel_amp = (note.velocity / 127.0) * 0.9
            for offset in range(-4, 5):
                idx = center_idx + offset
                if 0 <= idx < num_points:
                    dist = abs(offset) / 4.0
                    amps[idx] = max(amps[idx], vel_amp * (1.0 - dist * 0.6))

        return amps

    def _draw_social_guides(self, p: QPainter, w: int, h: int, scale: float,
                            safe_top: int, safe_bottom: int, safe_right: int):
        p.save()
        # Top overlay guide (Camera notch, status bar, search)
        p.fillRect(0, 0, w, safe_top, QColor(0, 0, 0, 75))
        p.setPen(QPen(QColor(255, 100, 100, 160), 1.0, Qt.PenStyle.DashLine))
        p.drawLine(0, safe_top, w, safe_top)
        p.setFont(QFont(self._font_family, max(8, int(10 * scale)), QFont.Weight.Bold))
        p.setPen(QColor(255, 130, 130, 210))
        p.drawText(QRectF(16, safe_top - 24 * scale, w - 32, 20 * scale),
                   Qt.AlignmentFlag.AlignLeft, "▲ Reels & Shorts Top UI Zone (Notch, Status & App Controls)")

        # Bottom overlay guide (Caption, Profile, Audio, Nav)
        p.fillRect(0, safe_bottom, w, h - safe_bottom, QColor(0, 0, 0, 85))
        p.setPen(QPen(QColor(255, 100, 100, 160), 1.0, Qt.PenStyle.DashLine))
        p.drawLine(0, safe_bottom, w, safe_bottom)
        p.drawText(QRectF(16, safe_bottom + 8 * scale, w - 32, 20 * scale),
                   Qt.AlignmentFlag.AlignLeft, "▼ Reels & Shorts Bottom UI Zone (Caption, Account & Navigation)")

        # Right Action Column Guide (Like, Comment, Share)
        p.setPen(QPen(QColor(0, 210, 200, 120), 1.0, Qt.PenStyle.DotLine))
        p.drawLine(safe_right, safe_top + int(300 * scale), safe_right, safe_bottom)
        p.drawText(QRectF(safe_right - 140 * scale, safe_top + int(320 * scale), 130 * scale, 35 * scale),
                   Qt.AlignmentFlag.AlignRight, "▶ Right Action Stack\n(Like, Comment, Share)")
        p.restore()
