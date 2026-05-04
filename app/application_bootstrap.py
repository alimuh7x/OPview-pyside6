"""Application bootstrap helpers."""

from PySide6.QtWidgets import QApplication

from app.debug import debug_print
from app.main_window import MainWindow
from app.styles import build_app_stylesheet


class ApplicationBootstrap:
    """Create and launch the QApplication and main window."""

    def __init__(self) -> None:
        debug_print("ApplicationBootstrap.__init__ start")
        self._application: QApplication | None = None
        self._style_name = "windows11"
        debug_print("ApplicationBootstrap.__init__ complete")

    def get_application(self) -> QApplication:
        debug_print("ApplicationBootstrap.get_application called")
        application = QApplication.instance()
        debug_print(f"Existing QApplication present={application is not None}")
        if application is None:
            debug_print("Creating new QApplication instance")
            application = QApplication([])
        debug_print(f"Applying {self._style_name} application style")
        application.setStyle(self._style_name)
        application.setStyleSheet(build_app_stylesheet())
        self._application = application
        debug_print("QApplication ready")
        return application

    def build_main_window(self) -> MainWindow:
        debug_print("ApplicationBootstrap.build_main_window called")
        self.get_application()
        window = MainWindow()
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
