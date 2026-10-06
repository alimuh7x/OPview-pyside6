"""Application bootstrap helpers."""

import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from app.debug import debug_print
from app.main_window import MainWindow
from app.styles import build_app_stylesheet

_FONTS_DIR = Path(__file__).parent.parent / "assets" / "fonts"
_NO_GPU_CHROMIUM_FLAGS = (
    "--disable-gpu "
    "--disable-gpu-compositing "
    "--disable-accelerated-2d-canvas "
    "--disable-accelerated-video-decode "
    "--disable-webgl "
    "--disable-3d-apis "
    "--disable-software-rasterizer=false "
    "--disable-features=VizDisplayCompositor "
    "--ignore-gpu-blocklist"
)


def _configure_no_gpu_environment() -> None:
    debug_print("ApplicationBootstrap._configure_no_gpu_environment called")
    if os.environ.get("OPVIEW_NO_GPU", "").strip().lower() not in {"1", "true", "yes", "on"}:
        debug_print("ApplicationBootstrap no-gpu disabled")
        return
    os.environ["QT_OPENGL"] = "software"
    debug_print(f"ApplicationBootstrap QT_OPENGL={os.environ['QT_OPENGL']}")
    os.environ["QT_QUICK_BACKEND"] = "software"
    debug_print(f"ApplicationBootstrap QT_QUICK_BACKEND={os.environ['QT_QUICK_BACKEND']}")
    os.environ["QTWEBENGINE_DISABLE_GPU"] = "1"
    debug_print(f"ApplicationBootstrap QTWEBENGINE_DISABLE_GPU={os.environ['QTWEBENGINE_DISABLE_GPU']}")
    existing_flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "").strip()
    flags = f"{existing_flags} {_NO_GPU_CHROMIUM_FLAGS}".strip()
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = flags
    debug_print(f"ApplicationBootstrap QTWEBENGINE_CHROMIUM_FLAGS={flags}")


def _is_supported_font_file(font_file: Path) -> bool:
    debug_print(f"Checking font file={font_file}")
    try:
        header = font_file.read_bytes()[:4]
    except OSError as exc:
        debug_print(f"Font read failed for {font_file.name}: {exc}")
        return False
    debug_print(f"Font header bytes={header!r}")
    supported = header in {b"\x00\x01\x00\x00", b"OTTO", b"ttcf"}
    debug_print(f"Font supported={supported}")
    return supported


class ApplicationBootstrap:
    """Create and launch the QApplication and main window."""

    def __init__(self, project_path: Path | None = None) -> None:
        debug_print("ApplicationBootstrap.__init__ start")
        self._application: QApplication | None = None
        self._project_path = Path(project_path).expanduser() if project_path else None
        debug_print(f"ApplicationBootstrap project_path={self._project_path}")
        self._style_name = "windows11"
        debug_print("ApplicationBootstrap.__init__ complete")

    def get_application(self) -> QApplication:
        debug_print("ApplicationBootstrap.get_application called")
        _configure_no_gpu_environment()
        application = QApplication.instance()
        debug_print(f"Existing QApplication present={application is not None}")
        if application is None:
            if os.environ.get("OPVIEW_NO_GPU", "").strip().lower() in {"1", "true", "yes", "on"}:
                QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL, True)
                debug_print("ApplicationBootstrap set AA_UseSoftwareOpenGL")
            debug_print("Creating new QApplication instance")
            application = QApplication([])
        debug_print(f"Applying {self._style_name} application style")
        application.setStyle(self._style_name)
        self._load_fonts(application)
        application.setStyleSheet(build_app_stylesheet())
        self._application = application
        debug_print("QApplication ready")
        return application

    def _load_fonts(self, application: QApplication) -> None:
        loaded_families: list[str] = []
        for font_file in _FONTS_DIR.glob("*.ttf"):
            debug_print(f"ApplicationBootstrap font candidate={font_file.name}")
            if not _is_supported_font_file(font_file):
                debug_print(f"Skipping unsupported font file={font_file.name}")
                continue
            fid = QFontDatabase.addApplicationFont(str(font_file))
            debug_print(f"ApplicationBootstrap font id={fid}")
            if fid < 0:
                debug_print(f"Qt rejected font file={font_file.name}")
                continue
            families = QFontDatabase.applicationFontFamilies(fid)
            loaded_families.extend(families)
            debug_print(f"Loaded font {font_file.name}: {families}")
        family = "Roboto Condensed" if "Roboto Condensed" in loaded_families else application.font().family()
        debug_print(f"ApplicationBootstrap selected font family={family}")
        font = QFont(family, 13)
        font.setStyleHint(QFont.StyleHint.SansSerif)
        application.setFont(font)
        debug_print(f"App font set to {family}")

    def build_main_window(self) -> MainWindow:
        debug_print("ApplicationBootstrap.build_main_window called")
        self.get_application()
        window = MainWindow(project_path=self._project_path)
        debug_print("MainWindow instance created")
        return window

    def run(self) -> int:
        debug_print("ApplicationBootstrap.run called")
        application = self.get_application()
        window = self.build_main_window()
        debug_print("Showing main window")
        window.show()
        debug_print("Entering QApplication event loop")
        return application.exec()
