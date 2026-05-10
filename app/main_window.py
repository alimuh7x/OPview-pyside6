"""Main application window."""

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QTabBar,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from app.debug import debug_print
from app.menu_bar import AppMenuBar
from multi_view.multi_view_tab import MultiViewTab
from sidebar.sidebar_widget import SidebarWidget
from single_view.tab_widget import SingleViewTab
from utils.file_watcher import FileWatcherService
from utils.project_scanner import scan_project_folders


class MainWindow(QMainWindow):
    """Top-level window that coordinates the sidebar and content tabs."""

    def __init__(self) -> None:
        debug_print("MainWindow.__init__ start")
        super().__init__()
        self.sidebar_widget: SidebarWidget | None = None
        self.single_view_tab: SingleViewTab | None = None
        self.multi_view_tab: MultiViewTab | None = None
        self.content_tabs: dict[str, QWidget] = {}
        self.app_menu_bar: AppMenuBar | None = None
        self.file_watcher: FileWatcherService | None = None
        self._build_window()
        self._connect_signals()
        self._load_initial_projects()
        debug_print("MainWindow.__init__ complete")

    def _build_window(self) -> None:
        debug_print("MainWindow._build_window called")
        self.setWindowTitle("OPview PySide6")
        self.resize(1400, 900)
        self.app_menu_bar = AppMenuBar(self)
        self.setMenuBar(self.app_menu_bar)
        debug_print("MainWindow menu bar set")
        self.file_watcher = FileWatcherService(self)
        self.file_watcher.set_cwd(Path.cwd())
        debug_print("MainWindow file watcher initialised")
        tabs = QTabBar()
        self.tab_widget = tabs
        debug_print("MainWindow created top-level tab bar")
        tabs.setObjectName("mainTabs")
        debug_print("MainWindow assigned object name to main tab bar")
        tabs.setDrawBase(False)
        debug_print("MainWindow disabled tab bar base drawing")
        tabs.setExpanding(False)
        debug_print("MainWindow disabled tab expansion")
        tabs.setDocumentMode(True)
        debug_print("MainWindow enabled document mode for main tab bar")
        tabs.addTab("Single View")
        debug_print("MainWindow added Single View tab")
        tabs.addTab("Multi View")
        debug_print("MainWindow added Multi View tab")
        tabs.addTab("Custom Graph")
        debug_print("MainWindow added Custom Graph tab")
        tabs.setCurrentIndex(0)
        debug_print("MainWindow set main tab bar index to 0")
        central_widget = QWidget()
        central_widget.setObjectName("appShell")
        central_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCentralWidget(central_widget)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addLayout(self._build_header())
        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        self.sidebar_widget = SidebarWidget()
        body_layout.addWidget(self.sidebar_widget, 0)
        content_area = QWidget()
        content_area.setObjectName("contentShell")
        content_area.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(14, 0, 14, 14)
        content_layout.setSpacing(10)
        self.single_view_tab = SingleViewTab()
        debug_print("MainWindow created SingleViewTab")
        self.multi_view_tab = MultiViewTab()
        debug_print("MainWindow created MultiViewTab")
        placeholder_graph = QLabel("Custom Graph will be added later")
        debug_print("MainWindow created Custom Graph placeholder")
        self.content_stack = QStackedWidget()
        debug_print("MainWindow created content stack")
        self.content_stack.addWidget(self.single_view_tab)
        debug_print("MainWindow added SingleViewTab to content stack")
        self.content_stack.addWidget(self.multi_view_tab)
        debug_print("MainWindow added MultiViewTab to content stack")
        self.content_stack.addWidget(placeholder_graph)
        debug_print("MainWindow added Custom Graph placeholder to content stack")
        self.content_stack.setCurrentIndex(0)
        debug_print("MainWindow set content stack index to 0")
        self.content_tabs = {
            "single_view": self.single_view_tab,
            "multi_view": self.multi_view_tab,
            "custom_graph": placeholder_graph,
        }
        content_layout.addWidget(self.content_stack, 1)
        body_layout.addWidget(content_area, 1)
        root_layout.addLayout(body_layout)
        debug_print("MainWindow widgets assembled")

    def _build_header(self) -> QHBoxLayout:
        debug_print("MainWindow._build_header called")
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_bar = QWidget()
        self.header_bar.setObjectName("headerBar")
        self.header_bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        header_bar_layout = QHBoxLayout(self.header_bar)
        header_bar_layout.setContentsMargins(8, 0, 8, 0)
        header_bar_layout.setSpacing(0)
        header_bar_layout.addWidget(self.tab_widget, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        header_bar_layout.addStretch(1)
        header_layout.addWidget(self.header_bar)
        debug_print("MainWindow header created")
        return header_layout

    def _connect_signals(self) -> None:
        debug_print("MainWindow._connect_signals called")
        assert self.sidebar_widget is not None
        assert self.single_view_tab is not None
        assert self.app_menu_bar is not None
        assert self.file_watcher is not None
        # Panel creation routed through slot so we can register the file with the watcher
        self.sidebar_widget.add_panel_requested.connect(self._on_add_panel_requested)
        debug_print("Connected sidebar add_panel_requested to _on_add_panel_requested")
        self.sidebar_widget.projects_changed.connect(self.single_view_tab.set_projects)
        debug_print("Connected sidebar projects_changed to SingleViewTab.set_projects")
        self.sidebar_widget.projects_changed.connect(self._on_projects_changed)
        debug_print("Connected sidebar projects_changed to _on_projects_changed")
        self.tab_widget.currentChanged.connect(self.content_stack.setCurrentIndex)
        debug_print("Connected main tab bar currentChanged to content stack")
        self.app_menu_bar.toggle_sidebar.connect(self.sidebar_widget.setVisible)
        debug_print("Connected menu toggle_sidebar to sidebar setVisible")
        self.app_menu_bar.add_project_folder_requested.connect(self._on_add_project_folder)
        debug_print("Connected menu add_project_folder_requested")
        self.app_menu_bar.add_vtk_files_requested.connect(self._on_add_vtk_files)
        debug_print("Connected menu add_vtk_files_requested")
        self.file_watcher.cwd_changed.connect(self._on_cwd_changed)
        debug_print("Connected file_watcher.cwd_changed")
        self.file_watcher.vtk_folder_changed.connect(self._on_vtk_folder_changed)
        debug_print("Connected file_watcher.vtk_folder_changed")
        self.file_watcher.loaded_file_changed.connect(self._on_loaded_file_changed)
        debug_print("Connected file_watcher.loaded_file_changed")
        self.sidebar_widget.reload_requested.connect(self._force_full_rescan)
        debug_print("Connected sidebar reload_requested to _force_full_rescan")
        self.single_view_tab.panel_ready.connect(self._on_panel_ready)
        debug_print("Connected single_view_tab.panel_ready to _on_panel_ready")
        debug_print("Menu export_requested not yet connected (no export handler)")

    # ------------------------------------------------------------------ #
    # Panel creation                                                       #
    # ------------------------------------------------------------------ #

    def _on_add_panel_requested(self, dataset_info: dict) -> None:
        assert self.single_view_tab is not None
        assert self.multi_view_tab is not None
        active_index = self.tab_widget.currentIndex()
        if active_index == 1:
            # Multi View tab is active — load dataset into multi view
            self.multi_view_tab.set_dataset(dataset_info)
        else:
            # Single View (default)
            self.single_view_tab.add_panel(dataset_info)

    def _on_panel_ready(self, panel) -> None:
        assert self.file_watcher is not None
        panel.file_loaded.connect(self.file_watcher.add_watched_file)
        debug_print("MainWindow registered panel file_loaded with watcher")

    # ------------------------------------------------------------------ #
    # File watcher handlers                                              #
    # ------------------------------------------------------------------ #

    def _force_full_rescan(self) -> None:
        """Manually trigger everything the watcher does automatically."""
        debug_print("MainWindow._force_full_rescan called")
        assert self.sidebar_widget is not None
        self.sidebar_widget._refresh_dataset_combo()
        for panel in self._iter_panels():
            panel.controller.refresh_view()
        debug_print("MainWindow._force_full_rescan complete")

    def _on_cwd_changed(self) -> None:
        debug_print("MainWindow._on_cwd_changed: rescanning projects")
        assert self.sidebar_widget is not None
        self.sidebar_widget.reload_from_cwd()

    def _on_vtk_folder_changed(self, folder_path: str) -> None:
        debug_print(f"MainWindow._on_vtk_folder_changed: {folder_path}")
        assert self.sidebar_widget is not None
        self.sidebar_widget._refresh_dataset_combo()
        for panel in self._iter_panels():
            if panel.controller.state.file_path.startswith(folder_path):
                debug_print(f"MainWindow refreshing panel for changed folder: {folder_path}")
                panel.controller.refresh_view()

    def _on_loaded_file_changed(self, file_path: str) -> None:
        debug_print(f"MainWindow._on_loaded_file_changed: {file_path}")
        for panel in self._iter_panels():
            if panel.controller.state.file_path == file_path:
                debug_print(f"MainWindow reloading panel for modified file: {file_path}")
                panel.controller.refresh_view()

    def _on_projects_changed(self, projects: dict) -> None:
        assert self.file_watcher is not None
        vtk_paths = [
            Path(str(info["vtk_path"]))
            for info in projects.values()
            if info.get("vtk_path") and Path(str(info["vtk_path"])).exists()
        ]
        self.file_watcher.set_vtk_paths(vtk_paths)
        debug_print(f"MainWindow updated watcher with {len(vtk_paths)} vtk paths")

    def _iter_panels(self):
        from viewer.panel_widget import PanelWidget
        assert self.single_view_tab is not None
        tabs = self.single_view_tab._panel_tabs
        for i in range(tabs.count()):
            w = tabs.widget(i)
            if isinstance(w, PanelWidget):
                yield w

    # ------------------------------------------------------------------ #
    # Menu handlers                                                      #
    # ------------------------------------------------------------------ #

    def _on_add_project_folder(self) -> None:
        """Open a folder dialog and load all VTK files directly from it."""
        debug_print("MainWindow._on_add_project_folder called")
        assert self.sidebar_widget is not None
        folder = QFileDialog.getExistingDirectory(self, "Select Folder Containing VTK Files")
        if not folder:
            return
        vtk_folder = Path(folder)
        project_name = f"[Folder] {vtk_folder.name}"
        info = {
            "path"               : vtk_folder,
            "has_vtk"            : True,
            "has_textdata"       : False,
            "vtk_path"           : vtk_folder,
            "textdata_path"      : None,
            "vtk_file_count"     : -1,
            "textdata_file_count": 0,
            "is_subdirectory"    : False,
            "parent_folder"      : None,
        }
        self.sidebar_widget.add_manual_project(project_name, info)
        debug_print(f"MainWindow added folder: {vtk_folder}")

    def _on_add_vtk_files(self) -> None:
        """Open a file dialog and register selected VTK files as a custom project."""
        debug_print("MainWindow._on_add_vtk_files called")
        assert self.sidebar_widget is not None
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select VTK Files",
            "",
            "VTK Files (*.vti *.vts *.vtu *.vtk *.vtp);;All Files (*)",
        )
        if not files:
            return
        vtk_folder = Path(files[0]).parent
        project_name = f"[Custom] {vtk_folder.name}"
        info = {
            "path"               : vtk_folder,
            "has_vtk"            : True,
            "has_textdata"       : False,
            "vtk_path"           : vtk_folder,
            "textdata_path"      : None,
            "vtk_file_count"     : len(files),
            "textdata_file_count": 0,
            "is_subdirectory"    : False,
            "parent_folder"      : None,
        }
        self.sidebar_widget.add_manual_project(project_name, info)
        debug_print(f"MainWindow added {len(files)} VTK files from {vtk_folder}")

    def _load_initial_projects(self) -> None:
        debug_print("MainWindow._load_initial_projects called")
        assert self.sidebar_widget is not None
        self.sidebar_widget.set_projects(scan_project_folders())
        debug_print("MainWindow initial projects loaded")



