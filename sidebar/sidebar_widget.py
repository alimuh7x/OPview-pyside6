"""Sidebar widget for project and panel actions."""

from pathlib import Path
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFileDialog,
    QComboBox,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

_ASSETS = Path(__file__).parent.parent / "assets"

from app.debug import debug_print
from config.constants import ALLOWED_TEXTDATA_EXTENSIONS
from config.tabs import TAB_CONFIGS
from config.dataset_registry import DatasetRegistry
from utils.combo_box_utils import update_combo_popup_width
from utils.project_scanner import get_textdata_files


class SidebarWidget(QWidget):
    """Sidebar with project overview and add-panel controls."""

    add_panel_requested = Signal(dict)
    projects_changed = Signal(dict)
    reload_requested = Signal()
    text_files_add_requested = Signal(list)

    def __init__(self) -> None:
        debug_print("SidebarWidget.__init__ start")
        super().__init__()
        self._projects: dict[str, dict] = {}
        self._manual_projects: dict[str, dict] = {}
        self._dataset_registry: DatasetRegistry | None = None
        self._mode = "vtk"
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

        self.project_list = QListWidget()
        self.project_list.setObjectName("projectList")
        self.project_list.setMaximumHeight(160)
        projects_layout.addWidget(self.project_list)

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
        update_combo_popup_width(self.dataset_combo)
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

        self.text_files_group = QGroupBox("TEXT DATA")
        self.text_files_group.setObjectName("sidebarCard")
        self.text_files_group.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        text_layout = QVBoxLayout(self.text_files_group)
        self.text_file_filter = QLineEdit()
        self.text_file_filter.setObjectName("sidebarLineEdit")
        self.text_file_filter.setPlaceholderText("Filter text files")
        text_layout.addWidget(self.text_file_filter)
        self.text_file_list = QListWidget()
        self.text_file_list.setObjectName("textFileList")
        self.text_file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        text_layout.addWidget(self.text_file_list)
        self.add_text_files_button = QPushButton(
            QIcon(str(_ASSETS / "plus.png")), "Add To Graph"
        )
        self.add_text_files_button.setIconSize(QSize(16, 16))
        self.add_text_files_button.setProperty("accent", True)
        text_layout.addWidget(self.add_text_files_button)
        self.add_external_text_file_button = QPushButton("Add External Text File")
        self.add_external_text_file_button.setProperty("accent", True)
        text_layout.addWidget(self.add_external_text_file_button)
        self.text_file_status_label = QLabel("Check a project to browse text files")
        self.text_file_status_label.setObjectName("sidebarMuted")
        self.text_file_status_label.setWordWrap(True)
        text_layout.addWidget(self.text_file_status_label)
        layout.addWidget(self.text_files_group)
        self.text_files_group.hide()
        layout.addStretch(1)
        debug_print("SidebarWidget UI ready")

    def _connect_signals(self) -> None:
        debug_print("SidebarWidget._connect_signals called")
        self.add_panel_button.clicked.connect(self._emit_add_panel_request)
        self.project_list.itemChanged.connect(self._on_project_check_changed)
        self.reload_projects_button.clicked.connect(self.reload_from_cwd)
        self.text_file_filter.textChanged.connect(self._refresh_text_file_list)
        self.add_text_files_button.clicked.connect(self._emit_text_files_add_request)
        self.add_external_text_file_button.clicked.connect(self._open_external_text_files)
        debug_print("SidebarWidget signals connected")

    def mode(self) -> str:
        debug_print(f"SidebarWidget.mode mode={self._mode}")
        return self._mode

    def set_mode(self, mode: str) -> None:
        debug_print(f"SidebarWidget.set_mode mode={mode}")
        self._mode = "custom_graph" if mode == "custom_graph" else "vtk"
        self.panel_group.setVisible(self._mode != "custom_graph")
        self.text_files_group.setVisible(self._mode == "custom_graph")
        self._populate_project_list()
        debug_print(f"SidebarWidget.set_mode complete mode={self._mode}")

    def set_projects(self, projects: dict[str, dict]) -> None:
        debug_print("SidebarWidget.set_projects called")
        debug_print(f"SidebarWidget received {len(projects)} projects")
        self._projects = projects
        if self._mode == "custom_graph":
            count = sum(1 for p in projects.values() if self._is_text_project(p))
        else:
            count = sum(1 for p in projects.values() if p.get("has_vtk"))
        self.project_status_label.setText(f"{count} project(s) found")
        self._populate_project_list()
        self.projects_changed.emit(projects)
        debug_print("SidebarWidget emitted projects_changed")

    def reload_from_cwd(self) -> None:
        """Reload project folders from the current working directory, preserving manual projects."""
        debug_print("SidebarWidget.reload_from_cwd called")
        from utils.project_scanner import scan_project_folders
        scanned = scan_project_folders(Path.cwd(), quick_scan=True)
        self.set_projects({**scanned, **self._manual_projects})
        self.reload_requested.emit()
        debug_print("SidebarWidget.reload_from_cwd complete")

    def add_manual_project(self, name: str, info: dict) -> None:
        """Register a manually added project (survives reload)."""
        debug_print(f"SidebarWidget.add_manual_project: {name}")
        self._manual_projects[name] = info
        self.set_projects({**self._projects, **self._manual_projects})

    def _emit_add_panel_request(self) -> None:
        debug_print("SidebarWidget._emit_add_panel_request called")
        dataset_info = self.dataset_combo.currentData()
        debug_print(f"Current dataset_info present={dataset_info is not None}")
        if not dataset_info:
            debug_print("No dataset selected, aborting add panel emit")
            return
        self.add_panel_requested.emit(dataset_info)
        debug_print(f"SidebarWidget emitted add_panel_requested for {dataset_info.get('label')}")

    def _populate_project_list(self) -> None:
        debug_print("SidebarWidget._populate_project_list called")
        self.project_list.blockSignals(True)
        self.project_list.clear()
        for project_name, project_info in sorted(self._projects.items()):
            if self._mode == "custom_graph":
                if not self._is_text_project(project_info):
                    continue
            else:
                if not project_info.get("has_vtk"):
                    continue
                if not project_info.get("is_subdirectory") and f"{project_name}/VTK" in self._projects:
                    continue
            item = QListWidgetItem(project_name)
            item.setData(Qt.ItemDataRole.UserRole, project_name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.project_list.addItem(item)
        self.project_list.blockSignals(False)
        debug_print(f"SidebarWidget project list count={self.project_list.count()}")
        if self._mode == "custom_graph":
            self._refresh_text_file_list()
        else:
            self._refresh_dataset_combo()

    def _on_project_check_changed(self, item: QListWidgetItem) -> None:
        debug_print(f"SidebarWidget project check changed: {item.text()} -> {item.checkState()}")
        if self._mode == "custom_graph":
            self._refresh_text_file_list()
        else:
            self._refresh_dataset_combo()

    def _refresh_dataset_combo(self) -> None:
        """Rebuild dataset combo — one entry per unique dataset type across all checked projects."""
        debug_print("SidebarWidget._refresh_dataset_combo called")
        self.dataset_combo.blockSignals(True)
        self.dataset_combo.clear()
        self.dataset_combo.addItem("Select a data type", None)

        # Group by dataset_id so same dataset type from multiple folders merges into one entry
        dataset_groups: dict[str, dict] = {}

        for i in range(self.project_list.count()):
            item = self.project_list.item(i)
            if item.checkState() != Qt.CheckState.Checked:
                continue
            project_key = item.data(Qt.ItemDataRole.UserRole)
            project_info = self._projects.get(project_key)
            if not project_info:
                continue
            vtk_folder = project_info.get("vtk_path") or project_info.get("path")
            if not vtk_folder or not Path(vtk_folder).exists():
                continue
            registry = DatasetRegistry(Path(vtk_folder), TAB_CONFIGS)
            registry.detect(verbose=False)
            for option in registry.get_dropdown_options():
                ds_id = option["value"]["id"]
                if ds_id not in dataset_groups:
                    dataset_groups[ds_id] = {
                        "id": ds_id,
                        "label": option["value"]["label"],
                        "module_label": option["value"]["module_label"],
                        "available_projects": [],
                    }
                dataset_groups[ds_id]["available_projects"].append({
                    "project_name": project_key,
                    "project_path": str(project_info.get("path")),
                    "vtk_folder": str(vtk_folder),
                    "files": option["value"]["files"],
                    "dataset_config": option["value"]["dataset_config"],
                    "module_id": option["value"]["module_id"],
                })

        for group in dataset_groups.values():
            label = f"{group['module_label']}: {group['label']}"
            self.dataset_combo.addItem(label, group)

        total_datasets = len(dataset_groups)
        self.dataset_combo.blockSignals(False)
        update_combo_popup_width(self.dataset_combo)

        if total_datasets > 0:
            self.dataset_status_label.setText(f"{total_datasets} dataset(s) detected")
        else:
            self.dataset_status_label.setText("Check a project to load datasets")
        debug_print(f"SidebarWidget dataset combo rebuilt with {total_datasets} options")

    def _is_text_project(self, project_info: dict) -> bool:
        debug_print("SidebarWidget._is_text_project called")
        is_text = bool(
            project_info.get("has_textdata")
            or project_info.get("textdata_path")
            or (project_info.get("path") and not project_info.get("has_vtk"))
        )
        debug_print(f"SidebarWidget._is_text_project result={is_text}")
        return is_text

    def _checked_project_names(self) -> list[str]:
        debug_print("SidebarWidget._checked_project_names called")
        names = [
            self.project_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.project_list.count())
            if self.project_list.item(i).checkState() == Qt.CheckState.Checked
        ]
        debug_print(f"SidebarWidget._checked_project_names names={names}")
        return names

    def _refresh_text_file_list(self) -> None:
        debug_print("SidebarWidget._refresh_text_file_list called")
        if self._mode != "custom_graph":
            debug_print("SidebarWidget._refresh_text_file_list skipped non-custom mode")
            return
        selected_project_names = self._checked_project_names()
        files = get_textdata_files(self._projects, selected_project_names) if selected_project_names else []
        filter_text = self.text_file_filter.text().strip().lower()
        debug_print(f"SidebarWidget._refresh_text_file_list filter={filter_text}")
        self.text_file_list.clear()
        for file_path in files:
            path = Path(file_path)
            label = path.name
            if filter_text and filter_text not in label.lower() and filter_text not in str(path).lower():
                continue
            item = QListWidgetItem(label)
            item.setToolTip(str(path))
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            self.text_file_list.addItem(item)
        count = self.text_file_list.count()
        if selected_project_names:
            self.text_file_status_label.setText(f"{count} text file(s) found")
        else:
            self.text_file_status_label.setText("Check a project to browse text files")
        debug_print(f"SidebarWidget._refresh_text_file_list count={count}")

    def _selected_text_files(self) -> list[str]:
        debug_print("SidebarWidget._selected_text_files called")
        selected = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self.text_file_list.selectedItems()
            if item.data(Qt.ItemDataRole.UserRole)
        ]
        debug_print(f"SidebarWidget._selected_text_files selected={selected}")
        return selected

    def _emit_text_files_add_request(self) -> None:
        debug_print("SidebarWidget._emit_text_files_add_request called")
        files = self._selected_text_files()
        if not files:
            debug_print("SidebarWidget._emit_text_files_add_request no selection")
            return
        self.text_files_add_requested.emit(files)
        debug_print(f"SidebarWidget emitted text_files_add_requested count={len(files)}")

    def _open_external_text_files(self) -> None:
        debug_print("SidebarWidget._open_external_text_files called")
        patterns = " ".join(f"*{ext}" for ext in sorted(ALLOWED_TEXTDATA_EXTENSIONS))
        files, _ = QFileDialog.getOpenFileNames(self, "Select Text Data Files", "", f"Text Data ({patterns})")
        if not files:
            debug_print("SidebarWidget._open_external_text_files no files")
            return
        self.text_files_add_requested.emit(files)
        debug_print(f"SidebarWidget._open_external_text_files emitted count={len(files)}")

    def _checked_count(self) -> int:
        return sum(
            1 for i in range(self.project_list.count())
            if self.project_list.item(i).checkState() == Qt.CheckState.Checked
        )
