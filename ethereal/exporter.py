"""
Video exporter — renders the MIDI visualization to MP4 using FFmpeg.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import threading
from typing import Optional, Callable

from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QImage

from ethereal.midi_engine import MidiData
from ethereal.palettes import ColorPalette


# ---------------------------------------------------------------------------
# Aspect ratio presets
# ---------------------------------------------------------------------------

ASPECT_RATIOS = {
    "9:16": (1080, 1920),
    "4:5":  (1080, 1350),
    "1:1":  (1080, 1080),
    "16:9": (1920, 1080),
}

RESOLUTIONS = {
    "720p":  0.667,   # scale factor from 1080p
    "1080p": 1.0,
    "4K":    2.0,
}


def find_ffmpeg() -> Optional[str]:
    """Find ffmpeg executable."""
    import sys
    candidates = [
        "ffmpeg",
        "ffmpeg.exe",
        # Next to the running executable (.exe)
        os.path.join(os.path.dirname(sys.executable), "ffmpeg.exe"),
        # Current working directory
        os.path.join(os.getcwd(), "ffmpeg.exe"),
        # Bundled temp folder (PyInstaller _MEIPASS)
        os.path.join(getattr(sys, "_MEIPASS", ""), "ffmpeg.exe"),
        # Source project root
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ffmpeg.exe"),
    ]

    # Also check PATH
    for candidate in candidates:
        if not candidate:
            continue
        try:
            result = subprocess.run(
                [candidate, "-version"],
                capture_output=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            )
            if result.returncode == 0:
                return candidate
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            continue

    return None


def find_working_encoder(ffmpeg_path: str) -> tuple[str, list[str]]:
    """Test and return the best available video encoder and its options."""
    candidates = [
        ("h264_nvenc", ["-c:v", "h264_nvenc", "-preset", "p4", "-b:v", "12M"]),
        ("h264_mf", ["-c:v", "h264_mf", "-b:v", "12M"]),
        ("libopenh264", ["-c:v", "libopenh264", "-b:v", "12M"]),
        ("libx264", ["-c:v", "libx264", "-preset", "medium", "-crf", "18"]),
    ]
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    for name, args in candidates:
        test_cmd = [
            ffmpeg_path, "-y",
            "-loglevel", "quiet",
            "-nostats",
            "-f", "rawvideo", "-vcodec", "rawvideo",
            "-s", "64x64", "-pix_fmt", "bgra", "-r", "30",
            "-i", "-",
            *args,
            "-pix_fmt", "yuv420p",
            "-f", "null", "-"
        ]
        try:
            p = subprocess.Popen(
                test_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
            p.stdin.write(bytes(64 * 64 * 4 * 2))
            p.stdin.close()
            p.wait(timeout=3)
            if p.returncode == 0:
                return name, args
        except Exception:
            continue
    return "h264_mf", ["-c:v", "h264_mf", "-b:v", "12M"]


class ExportWorker(QThread):
    """Background thread that renders frames and pipes to FFmpeg."""

    progress = pyqtSignal(int, int)         # current_frame, total_frames
    frame_rendered = pyqtSignal(QImage)     # preview of current frame
    finished_ok = pyqtSignal(str)           # output file path
    error = pyqtSignal(str)                 # error message

    def __init__(
        self,
        renderer,  # MidiRenderer instance (used for render_frame)
        palette: ColorPalette,
        output_path: str,
        midi_data=None,
        total_duration: Optional[float] = None,
        aspect_ratio: str = "9:16",
        resolution: str = "1080p",
        fps: int = 60,
        start_time: float = 0.0,
        end_time: Optional[float] = None,
        ffmpeg_path: Optional[str] = None,
        audio_path: Optional[str] = None,
    ):
        super().__init__()
        self._renderer = renderer
        self._midi = midi_data
        self._palette = palette
        self._output_path = output_path
        self._aspect_ratio = aspect_ratio
        self._resolution = resolution
        self._fps = fps
        self._start_time = start_time
        calc_end = end_time or total_duration or (midi_data.total_time if hasattr(midi_data, "total_time") else 30.0)
        self._end_time = max(calc_end, self._start_time + 1.0)
        self._ffmpeg_path = ffmpeg_path or find_ffmpeg()
        self._audio_path = audio_path
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        if not self._ffmpeg_path:
            self.error.emit("FFmpeg not found. Please install FFmpeg or place ffmpeg.exe next to Ethereal.")
            return

        try:
            self._do_export()
        except Exception as e:
            self.error.emit(str(e))

    def _do_export(self):
        # Calculate dimensions
        base_w, base_h = ASPECT_RATIOS.get(self._aspect_ratio, (1080, 1920))
        scale = RESOLUTIONS.get(self._resolution, 1.0)
        out_w = int(base_w * scale)
        out_h = int(base_h * scale)
        # Ensure even dimensions for h264
        out_w = out_w + (out_w % 2)
        out_h = out_h + (out_h % 2)

        duration = self._end_time - self._start_time
        total_frames = int(duration * self._fps)

        if total_frames <= 0:
            self.error.emit("Export duration is zero or negative.")
            return

        # Build FFmpeg command
        cmd = [
            self._ffmpeg_path,
            "-y",
            "-loglevel", "warning",
            "-nostats",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{out_w}x{out_h}",
            "-pix_fmt", "bgra",
            "-r", str(self._fps),
            "-i", "-",
        ]

        if self._audio_path and os.path.exists(self._audio_path):
            cmd.extend([
                "-ss", str(self._start_time),
                "-t", str(duration),
                "-i", self._audio_path,
            ])

        _enc_name, enc_opts = find_working_encoder(self._ffmpeg_path)
        cmd.extend(enc_opts)
        cmd.extend(["-pix_fmt", "yuv420p"])

        if self._audio_path and os.path.exists(self._audio_path):
            cmd.extend(["-c:a", "aac", "-b:a", "192k", "-shortest"])

        cmd.append(self._output_path)

        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            creationflags=creationflags,
        )

        # Background thread to continuously drain stderr and prevent OS pipe buffer deadlocks
        stderr_chunks: list[bytes] = []
        def _drain_stderr():
            try:
                while True:
                    chunk = proc.stderr.read(4096)
                    if not chunk:
                        break
                    stderr_chunks.append(chunk)
            except Exception:
                pass

        err_thread = threading.Thread(target=_drain_stderr, daemon=True)
        err_thread.start()

        try:
            for frame_num in range(total_frames):
                if self._cancelled:
                    proc.kill()
                    return

                time_s = self._start_time + frame_num / self._fps

                # Render frame
                image = self._renderer.render_frame(time_s, out_w, out_h)

                # Convert QImage to raw bytes
                image = image.convertToFormat(QImage.Format.Format_ARGB32)
                ptr = image.bits()
                ptr.setsize(out_w * out_h * 4)
                raw = bytes(ptr)

                proc.stdin.write(raw)

                # Emit progress
                self.progress.emit(frame_num + 1, total_frames)

                # Send preview every 30 frames
                if frame_num % 30 == 0:
                    preview = image.scaled(
                        270, int(270 * out_h / out_w),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.frame_rendered.emit(preview)

            proc.stdin.close()
            proc.wait(timeout=120)
            err_thread.join(timeout=5)

            if proc.returncode == 0:
                self.finished_ok.emit(self._output_path)
            else:
                err_text = b"".join(stderr_chunks).decode('utf-8', errors='replace')
                self.error.emit(f"FFmpeg error (code {proc.returncode}):\n{err_text[-600:]}")

        except Exception as e:
            try:
                proc.kill()
            except Exception:
                pass
            raise
