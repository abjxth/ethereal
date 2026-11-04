"""
Ethereal — MIDI Visualizer for Music Producers
Entry point.
"""
import sys
import os

# Ensure the package is importable when running from the project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QFontDatabase, QIcon
from PyQt6.QtCore import Qt

from ethereal.ui.main_window import MainWindow


def main():
    # High-DPI support
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

    app = QApplication(sys.argv)
    app.setApplicationName("Ethereal")
    app.setOrganizationName("Ethereal")

    # Load Satoshi fonts
    fonts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ethereal", "resources", "fonts")
    if getattr(sys, "frozen", False):
        meipass_fonts = os.path.join(getattr(sys, "_MEIPASS", ""), "ethereal", "resources", "fonts")
        if os.path.exists(meipass_fonts):
            fonts_dir = meipass_fonts

    satoshi_loaded = False
    if os.path.isdir(fonts_dir):
        for f in os.listdir(fonts_dir):
            if f.lower().endswith((".ttf", ".otf")):
                fp = os.path.join(fonts_dir, f)
                fid = QFontDatabase.addApplicationFont(fp)
                if fid != -1:
                    satoshi_loaded = True

    # Set default font to Satoshi Bold
    font_name = "Satoshi" if satoshi_loaded else "Segoe UI"
    font = QFont(font_name, 10, QFont.Weight.Bold)
    font.setBold(True)
    app.setFont(font)

    # Dark title bar on Windows 10/11
    app.setStyle("Fusion")

    # Force dark palette globally for Fusion
    from PyQt6.QtGui import QPalette, QColor
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 35))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(224, 224, 229))
    palette.setColor(QPalette.ColorRole.Base, QColor(42, 42, 50))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(50, 50, 58))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(42, 42, 50))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(224, 224, 229))
    palette.setColor(QPalette.ColorRole.Text, QColor(224, 224, 229))
    palette.setColor(QPalette.ColorRole.Button, QColor(42, 42, 50))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(224, 224, 229))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(0, 210, 200))
    palette.setColor(QPalette.ColorRole.Link, QColor(0, 210, 200))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 210, 200))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(17, 17, 17))
    app.setPalette(palette)

    # Set application icon
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ethereal", "resources", "icon.ico")
    if getattr(sys, "frozen", False):
        meipass_icon = os.path.join(getattr(sys, "_MEIPASS", ""), "ethereal", "resources", "icon.ico")
        if os.path.exists(meipass_icon):
            icon_path = meipass_icon
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)

    window = MainWindow()
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))
    window.show()

    # Apply Windows 10/11 Immersive Dark Title Bar (matching Antigravity chrome)
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import c_int, byref, sizeof
            val = c_int(1)
            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (Win 11 / Win 10 20H1+), 19 (Win 10 1809-1909)
            res = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                int(window.winId()), 20, byref(val), sizeof(val)
            )
            if res != 0:
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    int(window.winId()), 19, byref(val), sizeof(val)
                )
        except Exception:
            pass

    # If a MIDI file was passed as argument, load it
    if len(sys.argv) > 1:
        midi_path = sys.argv[1]
        if os.path.isfile(midi_path) and midi_path.lower().endswith(('.mid', '.midi')):
            window._load_midi_file(midi_path)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
