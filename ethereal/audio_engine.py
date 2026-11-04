"""
Audio Engine for Ethereal.
Handles audio file loading, waveform data extraction via FFmpeg,
and audio playback via QtMultimedia.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from PyQt6.QtCore import QUrl, QObject, pyqtSignal
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer

from ethereal.exporter import find_ffmpeg


@dataclass
class AudioData:
    """Waveform and amplitude data extracted from an audio file."""
    filepath: str
    filename: str
    duration: float  # seconds
    sample_rate: int = 1000  # downsampled envelope sample rate
    peaks: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.float32))
    bass_peaks: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.float32))

    def get_amplitude_at(self, time_s: float) -> float:
        """Get RMS/peak amplitude at a given timestamp (0.0 to 1.0)."""
        if len(self.peaks) == 0 or self.duration <= 0:
            return 0.0
        idx = int((time_s / self.duration) * len(self.peaks))
        idx = max(0, min(len(self.peaks) - 1, idx))
        return float(self.peaks[idx])

    def get_window(self, start_time: float, end_time: float, num_points: int = 100) -> np.ndarray:
        """Get an interpolated slice of waveform amplitudes between start and end time."""
        if len(self.peaks) == 0 or self.duration <= 0:
            return np.zeros(num_points, dtype=np.float32)

        start_idx = int((start_time / self.duration) * len(self.peaks))
        end_idx = int((end_time / self.duration) * len(self.peaks))

        # Handle out of bounds with zero padding
        left_pad = max(0, -start_idx)
        right_pad = max(0, end_idx - len(self.peaks))

        valid_start = max(0, start_idx)
        valid_end = min(len(self.peaks), end_idx)

        if valid_end <= valid_start:
            return np.zeros(num_points, dtype=np.float32)

        slice_data = self.peaks[valid_start:valid_end]
        if left_pad > 0 or right_pad > 0:
            slice_data = np.pad(slice_data, (left_pad, right_pad), mode='constant')

        if len(slice_data) == 0:
            return np.zeros(num_points, dtype=np.float32)

        # Resample to num_points
        orig_indices = np.linspace(0, 1, len(slice_data))
        new_indices = np.linspace(0, 1, num_points)
        return np.interp(new_indices, orig_indices, slice_data).astype(np.float32)


def load_audio_waveform(filepath: str, ffmpeg_path: Optional[str] = None) -> AudioData:
    """Extract downsampled audio waveform envelope from any audio format using FFmpeg."""
    ffmpeg = ffmpeg_path or find_ffmpeg() or "ffmpeg"
    filename = os.path.basename(filepath)

    # 1. Query duration using ffprobe or ffmpeg
    duration = 0.0
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    try:
        probe = subprocess.run(
            [ffmpeg, "-i", filepath],
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            creationflags=creationflags,
            timeout=5
        )
        stderr_text = probe.stderr.decode('utf-8', errors='replace')
        for line in stderr_text.splitlines():
            if "Duration:" in line:
                part = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = part.split(":")
                duration = float(h) * 3600 + float(m) * 60 + float(s)
                break
    except Exception:
        pass

    if duration <= 0:
        duration = 30.0  # fallback duration

    # 2. Extract downsampled mono audio at 4000 Hz for waveform envelope
    downsample_rate = 4000
    cmd = [
        ffmpeg, "-y",
        "-i", filepath,
        "-ac", "1",
        "-ar", str(downsample_rate),
        "-f", "f32le",
        "-"
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags
        )
        raw_bytes, _ = proc.communicate(timeout=20)
        samples = np.frombuffer(raw_bytes, dtype=np.float32)
    except Exception:
        samples = np.zeros(0, dtype=np.float32)

    if len(samples) == 0:
        return AudioData(filepath=filepath, filename=filename, duration=duration)

    # Calculate actual duration from sample count if probe failed
    if duration <= 0 or duration == 30.0:
        duration = len(samples) / downsample_rate

    # Compute RMS envelope downsampled to ~400 points per second
    chunk_size = max(1, downsample_rate // 400)
    num_chunks = len(samples) // chunk_size

    if num_chunks > 0:
        reshaped = samples[:num_chunks * chunk_size].reshape(num_chunks, chunk_size)
        peaks = np.sqrt(np.mean(reshaped ** 2, axis=1))  # RMS
        # Normalize with safety headroom
        max_val = np.max(peaks) if len(peaks) > 0 else 1.0
        if max_val > 0.001:
            peaks = np.clip(peaks / (max_val * 0.95), 0.0, 1.0)
    else:
        peaks = np.abs(samples)

    return AudioData(
        filepath=filepath,
        filename=filename,
        duration=duration,
        sample_rate=400,
        peaks=peaks.astype(np.float32)
    )


class AudioPlayer(QObject):
    """Audio playback controller synchronized with visualizer."""

    position_changed = pyqtSignal(float)  # seconds
    state_changed = pyqtSignal(bool)      # is_playing

    def __init__(self, parent=None):
        super().__init__(parent)
        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._player.setAudioOutput(self._audio_output)
        self._audio_output.setVolume(1.0)
        self._loaded_path: Optional[str] = None
        self._is_playing = False

    def load_file(self, filepath: str):
        """Load audio file into media player."""
        self._loaded_path = filepath
        url = QUrl.fromLocalFile(os.path.abspath(filepath))
        self._player.setSource(url)

    def play(self, start_time_s: float = 0.0):
        if not self._loaded_path:
            return
        self._player.setPosition(int(start_time_s * 1000))
        self._player.play()
        self._is_playing = True
        self.state_changed.emit(True)

    def pause(self):
        self._player.pause()
        self._is_playing = False
        self.state_changed.emit(False)

    def stop(self):
        self._player.stop()
        self._player.setPosition(0)
        self._is_playing = False
        self.state_changed.emit(False)

    def seek(self, time_s: float):
        if self._loaded_path:
            self._player.setPosition(int(time_s * 1000))

    def set_volume(self, volume: float):
        """Volume between 0.0 and 1.0."""
        self._audio_output.setVolume(max(0.0, min(1.0, volume)))

    def is_playing(self) -> bool:
        return self._is_playing

    def has_audio(self) -> bool:
        return self._loaded_path is not None and os.path.exists(self._loaded_path)
