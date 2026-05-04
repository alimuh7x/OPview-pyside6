"""Sidebar widget for project and panel actions."""

from pathlib import Path
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

_ASSETS = Path(__file__).parent.parent / "assets"

from app.debug import debug_print
from config.tabs import TAB_CONFIGS
from config.dataset_registry import DatasetRegistry


class SidebarWidget(QWidget):
    """Sidebar with project overview and add-panel controls."""

    add_panel_requested = Signal(dict)
    projects_changed = Signal(dict)

    def __init__(self) -> None:
        debug_print("SidebarWidget.__init__ start")
        super().__init__()
        self._projects: dict[str, dict] = {}
        self._dataset_registry: DatasetRegistry | None = None
        self._build_ui()
        self._connect_signals()
        debug_print("SidebarWidget.__init__ complete")

    def _build_ui(self) -> None:
        debug_print("SidebarWidget._build_ui called")
        self.setObjectName("sidebarShell")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(260)
        self.setMaximumWidth(320)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)
        self.projects_group = QGroupBox("PROJECTS")
        self.projects_group.setObjectName("sidebarCard")
        self.projects_group.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        projects_layout = QVBoxLayout(self.projects_group)
        self.project_status_label = QLabel("No project loaded")
        self.project_status_label.setObjectName("sidebarMuted")
        self.project_status_label.setWordWrap(True)
        projects_layout.addWidget(self.project_status_label)
        self.project_combo = QComboBox()
        self.project_combo.setObjectName("sidebarCombo")
        self.project_combo.addItem("Select project", None)
        projects_layout.addWidget(self.project_combo)
        self.project_summary_label = QLabel("Waiting for project scan")
        self.project_summary_label.setObjectName("sidebarMuted")
        self.project_summary_label.setWordWrap(True)
        projects_layout.addWidget(self.project_summary_label)
        self.reload_projects_button = QPushButton("Reload Projects")
        self.reload_projects_button.setProperty("accent", True)
        projects_layout.addWidget(self.reload_projects_button)
        layout.addWidget(self.projects_group)

        self.panel_group = QGroupBox("ADD PANEL")
        self.panel_group.setObjectName("sidebarCard")
        self.panel_group.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        panel_layout = QVBoxLayout(self.panel_group)
        self.dataset_combo = QComboBox()
        self.dataset_combo.setObjectName("sidebarCombo")
        self.dataset_combo.addItem("Select a data type", None)
        panel_layout.addWidget(self.dataset_combo)
        self.add_panel_button = QPushButton(
            QIcon(str(_ASSETS / "plus.png")), "Add Panel"
        )
        self.add_panel_button.setIconSize(QSize(16, 16))
        self.add_panel_button.setProperty("accent", True)
        panel_layout.addWidget(self.add_panel_button)
        self.dataset_status_label = QLabel("No dataset detected yet")
        self.dataset_status_label.setObjectName("sidebarMuted")
        self.dataset_status_label.setWordWrap(True)
        panel_layout.addWidget(self.dataset_status_label)
        layout.addWidget(self.panel_group)
        layout.addStretch(1)
        debug_print("SidebarWidget UI ready")

    def _connect_signals(self) -> None:
        debug_print("SidebarWidget._connect_signals called")
        self.add_panel_button.clicked.connect(self._emit_add_panel_request)
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        self.reload_projects_button.clicked.connect(self.reload_from_cwd)
        debug_print("SidebarWidget add panel button connected")

    def set_projects(self, projects: dict[str, dict]) -> None:
        debug_print("SidebarWidget.set_projects called")
        debug_print(f"SidebarWidget received {len(projects)} projects")
        self._projects = projects
        self.project_status_label.setText("Projects loaded")
        self.project_summary_label.setText(", ".join(projects.keys()) or "No names")
        self._populate_project_combo()
        self.projects_changed.emit(projects)
        debug_print("SidebarWidget emitted projects_changed")

    def reload_from_cwd(self) -> None:
        """Reload project folders from the current working directory."""
        debug_print("SidebarWidget.reload_from_cwd called")
        from utils.project_scanner import scan_project_folders

        self.set_projects(scan_project_folders(Path.cwd(), quick_scan=True))
        debug_print("SidebarWidget.reload_from_cwd complete")

    def _emit_add_panel_request(self) -> None:
        debug_print("SidebarWidget._emit_add_panel_request called")
        dataset_info = self.dataset_combo.currentData()
        debug_print(f"Current dataset_info present={dataset_info is not None}")
        if not dataset_info:
            debug_print("No dataset selected, aborting add panel emit")
            return
        self.add_panel_requested.emit(dataset_info)
        debug_print(f"SidebarWidget emitted add_panel_requested for {dataset_info.get('label')}")

    def _populate_project_combo(self) -> None:
        debug_print("SidebarWidget._populate_project_combo called")
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        self.project_combo.addItem("Select project", None)
        for project_name, project_info in sorted(self._projects.items()):
            if not project_info.get("has_vtk"):
                continue
            self.project_combo.addItem(project_name, project_name)
        self.project_combo.blockSignals(False)
        if self.project_combo.count() > 1:
            self.project_combo.setCurrentIndex(1)
        debug_print(f"SidebarWidget project combo count={self.project_combo.count()}")

    def _on_project_changed(self) -> None:
        debug_print("SidebarWidget._on_project_changed called")
        project_key = self.project_combo.currentData()
        debug_print(f"SidebarWidget selected project_key={project_key}")
        self.dataset_combo.clear()
        self.dataset_combo.addItem("Select a data type", None)
        if not project_key:
            self.dataset_status_label.setText("No project selected")
            return
        project_info = self._projects.get(project_key)
        if not project_info:
            self.dataset_status_label.setText("Project info missing")
            return
        vtk_folder = project_info.get("vtk_path") or project_info.get("path")
        if not vtk_folder or not Path(vtk_folder).exists():
            self.dataset_status_label.setText("VTK folder missing")
            return
        self._dataset_registry = DatasetRegistry(Path(vtk_folder), TAB_CONFIGS)
        self._dataset_registry.detect(verbose=False)
        for option in self._dataset_registry.get_dropdown_options():
            payload = dict(option["value"])
            payload["project_name"] = project_key
            payload["project_path"] = str(project_info.get("path"))
            payload["vtk_folder"] = str(vtk_folder)
            self.dataset_combo.addItem(option["label"], payload)
        self.dataset_status_label.setText(f"{len(self._dataset_registry.all_datasets)} dataset(s) detected")
        debug_print("SidebarWidget dataset combo populated")
