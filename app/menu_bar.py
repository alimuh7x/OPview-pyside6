"""Application menu bar."""

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import QApplication, QMenuBar, QMessageBox

from app.debug import debug_print
from app.resources import DOCUMENTATION_PATH


class AppMenuBar(QMenuBar):
    """
    Top-level menu bar for OPView.
    | File | View | Settings | Help |View | Settings | Help |
    """

    add_project_folder_requested = Signal()
    add_vtk_files_requested      = Signal()
    export_requested             = Signal()
    toggle_sidebar               = Signal(bool)
    toggle_overlay               = Signal(bool)
    reset_view_requested         = Signal()

    def __init__(self, parent=None) -> None:
        debug_print("AppMenuBar.__init__ called")
        super().__init__(parent)
        self._build_ui()
        debug_print("AppMenuBar.__init__ complete")

    def _build_ui(self) -> None:
        debug_print("AppMenuBar._build_ui called")
        self._build_file_menu()
        self._build_view_menu()
        self._build_settings_menu()
        self._build_help_menu()

    def _build_file_menu(self) -> None:
        file_menu = self.addMenu("File")

        add_folder_action = QAction("Add Project Folder", self)
        add_folder_action.setShortcut("Ctrl+O")
        add_folder_action.triggered.connect(self.add_project_folder_requested.emit)
        file_menu.addAction(add_folder_action)

        add_vtk_action = QAction("Add VTK Files", self)
        add_vtk_action.setShortcut("Ctrl+Shift+O")
        add_vtk_action.triggered.connect(self.add_vtk_files_requested.emit)
        file_menu.addAction(add_vtk_action)

        file_menu.addSeparator()

        export_action = QAction("Export Current View", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_requested.emit)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(QApplication.quit)
        file_menu.addAction(quit_action)

        debug_print("AppMenuBar File menu built")

    def _build_view_menu(self) -> None:
        view_menu = self.addMenu("View")

        self.toggle_sidebar_action = QAction("Toggle Sidebar", self)
        self.toggle_sidebar_action.setCheckable(True)
        self.toggle_sidebar_action.setChecked(True)
        self.toggle_sidebar_action.toggled.connect(self.toggle_sidebar.emit)
        view_menu.addAction(self.toggle_sidebar_action)

        self.toggle_overlay_action = QAction("Toggle Interfaces Overlay", self)
        self.toggle_overlay_action.setCheckable(True)
        self.toggle_overlay_action.setChecked(False)
        self.toggle_overlay_action.toggled.connect(self.toggle_overlay.emit)
        view_menu.addAction(self.toggle_overlay_action)

        view_menu.addSeparator()

        reset_action = QAction("Reset View", self)
        reset_action.triggered.connect(self.reset_view_requested.emit)
        view_menu.addAction(reset_action)

        debug_print("AppMenuBar View menu built")

    def _build_settings_menu(self) -> None:
        settings_menu = self.addMenu("Settings")

        preferences_action = QAction("Preferences", self)
        preferences_action.setEnabled(False)
        settings_menu.addAction(preferences_action)

        debug_print("AppMenuBar Settings menu built")

    def _build_help_menu(self) -> None:
        help_menu = self.addMenu("Help")

        docs_action = QAction("Documentation", self)
        docs_action.triggered.connect(self._open_documentation)
        help_menu.addAction(docs_action)

        help_menu.addSeparator()

        about_action = QAction("About OPView", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

        debug_print("AppMenuBar Help menu built")

    def _open_documentation(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(DOCUMENTATION_PATH)))

    def _show_about(self) -> None:
        QMessageBox.about(
            self.parent(),
            "About OPView",
            "<b>OPView</b><br>PySide6 desktop viewer<br><br>"
            "VTK-based visualization tool for phase-field simulation data.",
        )
