"""Main application window."""

from pathlib import Path

from PySide6.QtCore import QEvent, QSettings, QSize, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QTabBar,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.debug import debug_print
from app.menu_bar import AppMenuBar
from app.resources import APP_LOGO_PATH, DOCUMENTATION_PATH
from graphs.tab_widget import CustomGraphTab
from multi_view.multi_view_tab import MultiViewTab
from sidebar.sidebar_widget import SidebarWidget
from single_view.tab_widget import SingleViewTab
from utils.file_watcher import FileWatcherService
from utils.project_scanner import scan_project_folders


class MainWindow(QMainWindow):
    """Top-level window that coordinates the sidebar and content tabs."""

    def __init__(self, project_path: Path | None = None) -> None:
        debug_print("MainWindow.__init__ start")
        super().__init__()
        self.sidebar_widget: SidebarWidget | None = None
        self.single_view_tab: SingleViewTab | None = None
        self.multi_view_tab: MultiViewTab | None = None
        self.custom_graph_tab: CustomGraphTab | None = None
        self.content_tabs: dict[str, QWidget] = {}
        self.app_menu_bar: AppMenuBar | None = None
        self.file_watcher: FileWatcherService | None = None
        self.sidebar_toggle_button: QPushButton | None = None
        self._settings = QSettings("OPview", "OPview")
        self._project_path = Path(project_path).expanduser() if project_path else None
        debug_print(f"MainWindow project_path={self._project_path}")
        self._build_window()
        self._connect_signals()
        self._load_initial_projects()
        debug_print("MainWindow.__init__ complete")

    def _build_window(self) -> None:
        debug_print("MainWindow._build_window called")
        self.setWindowTitle("OPview PySide6")
        self.setWindowIcon(QIcon(str(APP_LOGO_PATH)))
        self.setMinimumWidth(800)
        debug_print("MainWindow minimum width set to 800")
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
        self.custom_graph_tab = CustomGraphTab()
        debug_print("MainWindow created CustomGraphTab")
        self.content_stack = QStackedWidget()
        debug_print("MainWindow created content stack")
        self.content_stack.addWidget(self.single_view_tab)
        debug_print("MainWindow added SingleViewTab to content stack")
        self.content_stack.addWidget(self.multi_view_tab)
        debug_print("MainWindow added MultiViewTab to content stack")
        self.content_stack.addWidget(self.custom_graph_tab)
        debug_print("MainWindow added CustomGraphTab to content stack")
        self.content_stack.setCurrentIndex(0)
        debug_print("MainWindow set content stack index to 0")
        self.content_scroll = QScrollArea()
        self.content_scroll.setObjectName("appContentScroll")
        debug_print("MainWindow created app-level content scroll area")
        self.content_scroll.setWidgetResizable(True)
        debug_print("MainWindow enabled content scroll widget resizing")
        self.content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        debug_print("MainWindow enabled horizontal app content scrolling as needed")
        self.content_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        debug_print("MainWindow enabled vertical app content scrolling as needed")
        self.content_scroll.setWidget(self.content_stack)
        self.content_scroll.viewport().installEventFilter(self)
        debug_print("MainWindow installed content viewport resize filter")
        debug_print("MainWindow installed content stack inside app scroll area")
        self.content_tabs = {
            "single_view": self.single_view_tab,
            "multi_view": self.multi_view_tab,
            "custom_graph": self.custom_graph_tab,
        }
        content_layout.addWidget(self.content_scroll, 1)
        debug_print("MainWindow added app content scroll to content layout")
        body_layout.addWidget(content_area, 1)
        root_layout.addLayout(body_layout)
        self._sync_content_width()
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
        header_bar_layout.setSpacing(8)
        self.sidebar_toggle_button = QPushButton()
        debug_print("MainWindow created sidebar toggle button")
        self.sidebar_toggle_button.setObjectName("headerSidebarToggleButton")
        debug_print("MainWindow assigned object name to sidebar toggle button")
        self.sidebar_toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
        debug_print("MainWindow set sidebar toggle button cursor")
        self.sidebar_toggle_button.setIconSize(QSize(28, 28))
        debug_print("MainWindow set sidebar toggle button icon size")
        self._update_sidebar_toggle_button(True)
        debug_print("MainWindow initialised sidebar toggle button state")
        header_bar_layout.addWidget(
            self.sidebar_toggle_button,
            0,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
        )
        debug_print("MainWindow added sidebar toggle button before tabs")
        header_bar_layout.addWidget(self.tab_widget, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        header_bar_layout.addStretch(1)
        self.documentation_button = QPushButton("Documentation")
        self.documentation_button.setObjectName("headerDocButton")
        self.documentation_button.setProperty("accent", True)
        self.documentation_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.documentation_button.clicked.connect(self._open_documentation)
        header_bar_layout.addWidget(
            self.documentation_button,
            0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        header_layout.addWidget(self.header_bar)
        debug_print("MainWindow header created")
        return header_layout

    def _open_documentation(self) -> None:
        debug_print("MainWindow._open_documentation called")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(DOCUMENTATION_PATH)))

    def _connect_signals(self) -> None:
        debug_print("MainWindow._connect_signals called")
        assert self.sidebar_widget is not None
        assert self.single_view_tab is not None
        assert self.custom_graph_tab is not None
        assert self.app_menu_bar is not None
        assert self.file_watcher is not None
        # Panel creation routed through slot so we can register the file with the watcher
        self.sidebar_widget.add_panel_requested.connect(self._on_add_panel_requested)
        debug_print("Connected sidebar add_panel_requested to _on_add_panel_requested")
        self.sidebar_widget.projects_changed.connect(self.single_view_tab.set_projects)
        debug_print("Connected sidebar projects_changed to SingleViewTab.set_projects")
        self.sidebar_widget.projects_changed.connect(self.custom_graph_tab.set_projects)
        debug_print("Connected sidebar projects_changed to CustomGraphTab.set_projects")
        self.sidebar_widget.custom_graph_project_scope_changed.connect(self.custom_graph_tab.set_selected_project_names)
        debug_print("Connected sidebar custom_graph_project_scope_changed")
        self.sidebar_widget.projects_changed.connect(self._on_projects_changed)
        debug_print("Connected sidebar projects_changed to _on_projects_changed")
        self.tab_widget.currentChanged.connect(self._on_main_tab_changed)
        debug_print("Connected main tab bar currentChanged to _on_main_tab_changed")
        self.sidebar_widget.text_files_add_requested.connect(self._on_text_files_add_requested)
        debug_print("Connected sidebar text_files_add_requested")
        assert self.sidebar_toggle_button is not None
        self.sidebar_toggle_button.clicked.connect(self._on_sidebar_toggle_button_clicked)
        debug_print("Connected sidebar toggle button clicked")
        self.app_menu_bar.toggle_sidebar.connect(self._set_sidebar_visible)
        debug_print("Connected menu toggle_sidebar to _set_sidebar_visible")
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
        self.sidebar_widget.add_folder_requested.connect(self._on_add_project_folder)
        debug_print("Connected sidebar add_folder_requested to _on_add_project_folder")
        self.single_view_tab.panel_ready.connect(self._on_panel_ready)
        debug_print("Connected single_view_tab.panel_ready to _on_panel_ready")
        debug_print("Menu export_requested not yet connected (no export handler)")

    def _on_sidebar_toggle_button_clicked(self) -> None:
        debug_print("MainWindow._on_sidebar_toggle_button_clicked called")
        assert self.sidebar_widget is not None
        current_visible = not self.sidebar_widget.isHidden()
        debug_print(f"MainWindow sidebar currently visible={current_visible}")
        requested_visible = not current_visible
        debug_print(f"MainWindow sidebar requested visible={requested_visible}")
        self._set_sidebar_visible(requested_visible)
        debug_print("MainWindow._on_sidebar_toggle_button_clicked complete")

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        debug_print(f"MainWindow.resizeEvent width={event.size().width()}")
        self._sync_content_width()

    def eventFilter(self, watched, event):  # noqa: N802
        if (
            hasattr(self, "content_scroll")
            and watched is self.content_scroll.viewport()
            and event.type() == QEvent.Type.Resize
        ):
            debug_print(f"MainWindow content viewport resize width={event.size().width()}")
            self._sync_content_width()
        return super().eventFilter(watched, event)

    def _set_sidebar_visible(self, visible: bool) -> None:
        debug_print(f"MainWindow._set_sidebar_visible requested visible={visible}")
        assert self.sidebar_widget is not None
        assert self.app_menu_bar is not None
        self.sidebar_widget.setVisible(visible)
        debug_print(f"MainWindow sidebar actual visible={self.sidebar_widget.isVisible()}")
        self._sync_content_width()
        debug_print("MainWindow synced content width after sidebar visibility change")
        self._update_sidebar_toggle_button(visible)
        debug_print("MainWindow sidebar toggle button updated")
        action = self.app_menu_bar.toggle_sidebar_action
        debug_print(f"MainWindow menu sidebar action before sync={action.isChecked()}")
        if action.isChecked() != visible:
            debug_print("MainWindow syncing menu sidebar action checked state")
            was_blocked = action.blockSignals(True)
            action.setChecked(visible)
            action.blockSignals(was_blocked)
            debug_print(f"MainWindow menu sidebar action synced={action.isChecked()}")
        else:
            debug_print("MainWindow menu sidebar action already synced")
        debug_print("MainWindow._set_sidebar_visible complete")

    def _update_sidebar_toggle_button(self, sidebar_visible: bool) -> None:
        debug_print(f"MainWindow._update_sidebar_toggle_button visible={sidebar_visible}")
        assert self.sidebar_toggle_button is not None
        asset_name = "hide_sidebar.png" if sidebar_visible else "show_sidebar.png"
        debug_print(f"MainWindow sidebar toggle asset name={asset_name}")
        asset_path = Path(__file__).parent.parent / "assets" / asset_name
        debug_print(f"MainWindow sidebar toggle asset path={asset_path}")
        icon = QIcon(str(asset_path))
        debug_print(f"MainWindow sidebar toggle icon isNull={icon.isNull()}")
        self.sidebar_toggle_button.setIcon(icon)
        debug_print("MainWindow sidebar toggle icon applied")
        tooltip = "Hide sidebar" if sidebar_visible else "Show sidebar"
        self.sidebar_toggle_button.setToolTip(tooltip)
        debug_print(f"MainWindow sidebar toggle tooltip={tooltip}")

    def _sync_content_width(self) -> None:
        debug_print("MainWindow._sync_content_width called")
        if not hasattr(self, "content_scroll") or not hasattr(self, "content_stack"):
            debug_print("MainWindow._sync_content_width skipped: content not ready")
            return
        viewport_width = max(0, self.content_scroll.viewport().width())
        debug_print(f"MainWindow content viewport width={viewport_width}")
        if viewport_width <= 0:
            debug_print("MainWindow._sync_content_width skipped: viewport width unavailable")
            return
        custom_graph_active = getattr(self, "tab_widget", None) is not None and self.tab_widget.currentIndex() == 2
        debug_print(f"MainWindow custom graph active={custom_graph_active}")
        self.content_stack.setMinimumWidth(0)
        if custom_graph_active:
            self.content_stack.setMaximumWidth(16777215)
        else:
            self.content_stack.setMaximumWidth(viewport_width)
        debug_print(f"MainWindow content stack max width={self.content_stack.maximumWidth()}")
        for key, widget in self.content_tabs.items():
            widget.setMinimumWidth(0)
            if custom_graph_active and key == "custom_graph":
                widget.setMaximumWidth(16777215)
            else:
                widget.setMaximumWidth(viewport_width)
            debug_print(f"MainWindow applying available width to {key}: {viewport_width}")
            if hasattr(widget, "set_available_width"):
                widget.set_available_width(viewport_width)
                debug_print(f"MainWindow called set_available_width on {key}")

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

    def _on_main_tab_changed(self, index: int) -> None:
        debug_print(f"MainWindow._on_main_tab_changed index={index}")
        assert self.sidebar_widget is not None
        self.content_stack.setCurrentIndex(index)
        self._sync_content_width()
        debug_print("MainWindow synced content width after tab change")
        mode = "custom_graph" if index == 2 else "vtk"
        self.sidebar_widget.set_mode(mode)
        debug_print(f"MainWindow._on_main_tab_changed sidebar_mode={mode}")

    def _on_text_files_add_requested(self, files: list[str]) -> None:
        debug_print(f"MainWindow._on_text_files_add_requested files={files}")
        assert self.custom_graph_tab is not None
        self.custom_graph_tab.add_files_to_active_panel(files)
        debug_print("MainWindow._on_text_files_add_requested complete")

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
        if self.sidebar_widget.mode() == "custom_graph":
            self.sidebar_widget._emit_custom_graph_project_scope()
        else:
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
        if self.sidebar_widget.mode() != "custom_graph":
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
        if self.sidebar_widget.mode() == "custom_graph":
            last = self._settings.value("last_text_folder", "")
            folder = QFileDialog.getExistingDirectory(self, "Select Folder Containing Text Data Files", last)
            if not folder:
                return
            self._settings.setValue("last_text_folder", folder)
            text_folder = Path(folder)
            project_name = f"[Folder] {text_folder.name}"
            info = {
                "path"               : text_folder,
                "has_vtk"            : False,
                "has_textdata"       : True,
                "vtk_path"           : None,
                "textdata_path"      : text_folder,
                "vtk_file_count"     : 0,
                "textdata_file_count": -1,
                "is_subdirectory"    : False,
                "parent_folder"      : None,
            }
            self.sidebar_widget.add_manual_project(project_name, info)
            debug_print(f"MainWindow added text folder: {text_folder}")
            return
        last = self._settings.value("last_vtk_folder", "")
        folder = QFileDialog.getExistingDirectory(self, "Select Folder Containing VTK Files", last)
        if not folder:
            return
        self._settings.setValue("last_vtk_folder", folder)
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
        self.sidebar_widget.set_projects(scan_project_folders(self._project_path))
        debug_print("MainWindow initial projects loaded")
