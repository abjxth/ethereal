"""
Export Dialog — Modal progress dialog for video export.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPixmap, QImage, QColor
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QSizePolicy, QFrame, QWidget,
)


# ---------------------------------------------------------------------------
# Stylesheet tokens
# ---------------------------------------------------------------------------

_ACCENT = "#00d2c8"
_BG = "#12121a"
_BG_LIGHTER = "#1a1a26"
_BORDER = "#28283a"
_TEXT = "#f0f0f8"
_TEXT_DIM = "#8e8ea0"

_DIALOG_STYLE = f"""
QDialog {{
    background: {_BG};
    border: 1px solid {_BORDER};
    border-radius: 12px;
}}
"""

_PROGRESS_STYLE = f"""
QProgressBar {{
    background: {_BG_LIGHTER};
    border: 1px solid #28283a;
    border-radius: 6px;
    height: 12px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {_ACCENT}, stop:1 #00b4d8
    );
    border-radius: 5px;
}}
"""

_CANCEL_STYLE = f"""
QPushButton {{
    background: {_BG_LIGHTER};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: 8px;
    padding: 7px 22px;
    font-size: 12px;
    font-weight: 700;
}}
QPushButton:hover {{
    background: #262638;
    border-color: #3e3e56;
    color: #ffffff;
}}
QPushButton:pressed {{
    background: #00d2c8;
    color: #081111;
}}
"""

_TITLE_STYLE = f"""
QLabel {{
    color: {_TEXT};
    font-size: 15px;
    font-weight: 800;
    letter-spacing: 0.5px;
}}
"""

_STATUS_STYLE = f"""
QLabel {{
    color: {_TEXT_DIM};
    font-size: 12px;
}}
"""

_ETA_STYLE = f"""
QLabel {{
    color: {_TEXT_DIM};
    font-size: 11px;
    font-style: italic;
}}
"""

_PREVIEW_STYLE = f"""
QLabel {{
    background: rgb(20, 20, 24);
    border: 1px solid {_BORDER};
    border-radius: 6px;
}}
"""


# ---------------------------------------------------------------------------
# Export dialog
# ---------------------------------------------------------------------------

class ExportDialog(QDialog):
    """Modal dialog showing export/render progress."""

    cancel_requested = pyqtSignal()

    _PREVIEW_W = 256
    _PREVIEW_H = 144  # 16:9

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Exporting Video")
        self.setFixedSize(QSize(380, 340))
        self.setModal(True)
        self.setStyleSheet(_DIALOG_STYLE)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        self._cancelled = False

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # Title
        self._lbl_title = QLabel("Exporting Video")
        self._lbl_title.setStyleSheet(_TITLE_STYLE)
        self._lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._lbl_title)

        # Preview thumbnail
        self._lbl_preview = QLabel()
        self._lbl_preview.setFixedSize(QSize(self._PREVIEW_W, self._PREVIEW_H))
        self._lbl_preview.setStyleSheet(_PREVIEW_STYLE)
        self._lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_preview.setText("Preview")
        self._lbl_preview.setFont(QFont("Segoe UI", 10))
        self._set_default_preview()

        preview_row = QHBoxLayout()
        preview_row.addStretch()
        preview_row.addWidget(self._lbl_preview)
        preview_row.addStretch()
        root.addLayout(preview_row)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setStyleSheet(_PROGRESS_STYLE)
        self._progress.setFixedHeight(10)
        root.addWidget(self._progress)

        # Status text
        self._lbl_status = QLabel("Preparing…")
        self._lbl_status.setStyleSheet(_STATUS_STYLE)
        self._lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._lbl_status)

        # ETA
        self._lbl_eta = QLabel("")
        self._lbl_eta.setStyleSheet(_ETA_STYLE)
        self._lbl_eta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._lbl_eta)

        root.addStretch()

        # Cancel button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_cancel = QPushButton("Cancel")
        self._btn_cancel.setStyleSheet(_CANCEL_STYLE)
        self._btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_cancel.setFixedWidth(100)
        self._btn_cancel.clicked.connect(self._on_cancel)
        btn_row.addWidget(self._btn_cancel)
        btn_row.addStretch()
        root.addLayout(btn_row)

    # -- public API ---------------------------------------------------------

    def set_progress(
        self,
        current_frame: int,
        total_frames: int,
        eta_seconds: float | None = None,
    ) -> None:
        """Update progress bar and status text."""
        if total_frames <= 0:
            return
        pct = int((current_frame / total_frames) * 100)
        self._progress.setValue(min(pct, 100))
        self._lbl_status.setText(
            f"Rendering frame {current_frame:,} / {total_frames:,}…"
        )
        if eta_seconds is not None and eta_seconds > 0:
            self._lbl_eta.setText(f"≈ {self._fmt_eta(eta_seconds)} remaining")
        else:
            self._lbl_eta.setText("")

    def set_preview_image(self, image: QImage) -> None:
        """Update the preview thumbnail from a QImage."""
        scaled = image.scaled(
            self._PREVIEW_W, self._PREVIEW_H,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._lbl_preview.setPixmap(QPixmap.fromImage(scaled))

    def set_preview_pixmap(self, pixmap: QPixmap) -> None:
        """Update the preview thumbnail from a QPixmap."""
        scaled = pixmap.scaled(
            self._PREVIEW_W, self._PREVIEW_H,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._lbl_preview.setPixmap(scaled)

    def mark_complete(self, output_path: str | None = None) -> None:
        """Show completion state."""
        self._progress.setValue(100)
        self._lbl_title.setText("Export Complete")
        msg = "Done!"
        if output_path:
            msg = f"Saved to {output_path}"
        self._lbl_status.setText(msg)
        self._lbl_eta.setText("")
        self._btn_cancel.setText("Close")

    def mark_error(self, message: str) -> None:
        """Show an error state."""
        self._lbl_title.setText("Export Failed")
        self._lbl_status.setText(message)
        self._lbl_status.setStyleSheet(
            "QLabel { color: rgb(255, 100, 80); font-size: 12px; }"
        )
        self._lbl_eta.setText("")
        self._btn_cancel.setText("Close")

    @property
    def was_cancelled(self) -> bool:
        return self._cancelled

    # -- private ------------------------------------------------------------

    def _on_cancel(self) -> None:
        if self._btn_cancel.text() == "Close":
            self.accept()
            return
        self._cancelled = True
        self._lbl_status.setText("Cancelling…")
        self._btn_cancel.setEnabled(False)
        self.cancel_requested.emit()

    def _set_default_preview(self) -> None:
        """Fill preview with a dark placeholder."""
        img = QImage(self._PREVIEW_W, self._PREVIEW_H, QImage.Format.Format_RGB32)
        img.fill(QColor(20, 20, 24))
        self._lbl_preview.setPixmap(QPixmap.fromImage(img))

    @staticmethod
    def _fmt_eta(seconds: float) -> str:
        """Format ETA as 'Xm Ys' or 'Ys'."""
        s = int(seconds)
        if s >= 60:
            return f"{s // 60}m {s % 60}s"
        return f"{s}s"

    # -- drag support (frameless window) ------------------------------------

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if (
            event.buttons() & Qt.MouseButton.LeftButton
            and hasattr(self, "_drag_pos")
        ):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
