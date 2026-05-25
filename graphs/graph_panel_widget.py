"""One Custom Graph panel tab."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.debug import debug_print
from config.constants import ALLOWED_TEXTDATA_EXTENSIONS, SKIP_FOLDERS
from data.text_sources import GenericTextDataSource
from graphs.graph_canvas import GraphCanvas
from utils.combo_box_utils import update_combo_popup_width
from viewer.plot_style import PlotStyle

_ASSETS = Path(__file__).resolve().parent.parent / "assets"


class GraphPanelWidget(QWidget):
    """Controls and chart canvas for one graph panel."""

    def __init__(
        self,
        panel_number: int,
        projects: dict[str, dict] | None = None,
        selected_project_names: list[str] | None = None,
        suggested_files: list[str] | None = None,
    ) -> None:
        debug_print(f"GraphPanelWidget.__init__ start panel_number={panel_number}")
        super().__init__()
        self.setObjectName("customGraphPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.panel_number = panel_number
        self._projects = projects or {}
        self._selected_project_names = selected_project_names or []
        self._folder_files: dict[str, list[str]] = {}
        self._files: list[str] = []
        self._columns_by_file: dict[str, list[str]] = {}
        self._column_settings: dict[str, dict[str, dict[str, str]]] = {}
        self._column_checkboxes: dict[tuple[str, str], QCheckBox] = {}
        self._axis_radios: dict[tuple[str, str, str], QRadioButton] = {}
        self._legend_edits: dict[tuple[str, str], QLineEdit] = {}
        self._conversion_combos: dict[tuple[str, str], QComboBox] = {}
        self._color_combos: dict[tuple[str, str], QComboBox] = {}
        self._sources_layout: QVBoxLayout | None = None
        self._settings_layout: QGridLayout | None = None
        self._build_ui()
        self._refresh_file_sections()
        self._refresh_graph()
        debug_print("GraphPanelWidget.__init__ complete")

    def add_files(self, files: list[str]) -> None:
        debug_print(f"GraphPanelWidget.add_files files={files}")
        for file_path in files:
            resolved = str(Path(file_path).resolve())
            debug_print(f"GraphPanelWidget.add_files resolved={resolved}")
            if resolved in self._files:
                debug_print(f"GraphPanelWidget.add_files duplicate skip={resolved}")
                continue
            if len(self._files) >= 3:
                debug_print("GraphPanelWidget.add_files max files reached")
                break
            self._files.append(resolved)
            self._columns_by_file.setdefault(resolved, [])
            self._column_settings.setdefault(resolved, {})
        self._refresh_file_sections()
        self._refresh_x_axis_options()
        self._refresh_auto_legends()
        self._refresh_graph()

    def state(self) -> dict:
        debug_print("GraphPanelWidget.state called")
        return {
            "files": list(self._files),
            "columns_by_file": {k: list(v) for k, v in self._columns_by_file.items()},
            "column_settings": self._column_settings,
            "x_axis_column": self.x_axis_combo.currentData(),
            "x_axis_conversion": self.x_axis_conversion_combo.currentData() or "as-is",
            "x_axis_title": self.x_title_edit.text().strip() or "Time",
            "yaxis1_title": self.y1_title_edit.text().strip() or "Y1",
            "yaxis2_title": self.y2_title_edit.text().strip() or "Y2",
            "legend_position": self.legend_position_combo.currentData() or "top-left",
            "show_legend": self.legend_check.isChecked(),
            "show_grid": self.grid_check.isChecked(),
            "trace_mode": self.trace_mode_combo.currentData() or "lines",
            "line_style": self.line_style_combo.currentData() or "solid",
        }

    def set_project_scope(self, projects: dict[str, dict], selected_project_names: list[str]) -> None:
        debug_print(f"GraphPanelWidget.set_project_scope selected={len(selected_project_names)}")
        self._projects = projects
        self._selected_project_names = [name for name in selected_project_names if name in projects]
        self._refresh_project_selector()

    def _build_ui(self) -> None:
        debug_print("GraphPanelWidget._build_ui called")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.top_controls = QWidget()
        self.top_controls.setObjectName("graphTopControls")
        self.top_controls.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        top_layout = QVBoxLayout(self.top_controls)
        top_layout.setContentsMargins(18, 18, 18, 14)
        top_layout.setSpacing(12)
        toolbar = QHBoxLayout()
        self.project_combo = QComboBox()
        self.project_combo.setObjectName("graphCombo")
        self.project_combo.setMinimumWidth(210)
        self.project_combo.currentIndexChanged.connect(self._refresh_folder_selector)
        toolbar.addWidget(self.project_combo)

        self.folder_combo = QComboBox()
        self.folder_combo.setObjectName("graphCombo")
        self.folder_combo.setMinimumWidth(210)
        self.folder_combo.currentIndexChanged.connect(self._refresh_file_selector)
        toolbar.addWidget(self.folder_combo)

        self.file_combo = QComboBox()
        self.file_combo.setObjectName("graphCombo")
        self.file_combo.setMinimumWidth(260)
        self.file_combo.currentIndexChanged.connect(self._sync_add_button_state)
        toolbar.addWidget(self.file_combo)

        self.add_file_button = QPushButton("+ Add To Graph")
        self.add_file_button.setProperty("accent", True)
        self.add_file_button.clicked.connect(self._add_selected_graph_file)
        toolbar.addWidget(self.add_file_button)

        self.external_file_button = QPushButton("Add External Text File")
        self.external_file_button.setProperty("accent", True)
        self.external_file_button.clicked.connect(self._open_file_dialog)
        toolbar.addWidget(self.external_file_button)
        self.download_png_button = QPushButton(QIcon(str(_ASSETS / "grey_download.png")), "PNG")
        self.download_png_button.setIconSize(QSize(16, 16))
        self.download_png_button.setProperty("accent", True)
        self.download_png_button.setToolTip("Download graph as PNG")
        self.download_png_button.clicked.connect(self._download_png)
        toolbar.addWidget(self.download_png_button)
        toolbar.addStretch(1)
        top_layout.addLayout(toolbar)

        self._refresh_project_selector()

        self.sources_group = QGroupBox("Data Sources")
        self.sources_group.setObjectName("graphDataSources")
        self.sources_group.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._sources_layout = QVBoxLayout(self.sources_group)
        self._sources_layout.setContentsMargins(12, 12, 12, 12)
        self._sources_layout.setSpacing(12)
        top_layout.addWidget(self.sources_group)
        root.addWidget(self.top_controls)

        self.main_content = QWidget()
        self.main_content.setObjectName("graphMainContent")
        self.main_content.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        main_split = QHBoxLayout()
        main_split.setContentsMargins(0, 0, 0, 0)
        main_split.setSpacing(0)
        debug_print("GraphPanelWidget._build_ui main split spacing=0")
        self.main_content.setLayout(main_split)
        self.graph_area = QWidget()
        self.graph_area.setObjectName("graphArea")
        self.graph_area.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        graph_layout = QVBoxLayout(self.graph_area)
        graph_layout.setContentsMargins(18, 18, 0, 18)
        debug_print("GraphPanelWidget._build_ui graph area right margin=0")
        self.canvas = GraphCanvas()
        graph_layout.addWidget(self.canvas)
        main_split.addWidget(self.graph_area, 1)
        settings = self._build_settings_panel()
        main_split.addWidget(settings, 0)
        root.addWidget(self.main_content, 1)
        debug_print("GraphPanelWidget._build_ui complete")

    def _build_settings_panel(self) -> QWidget:
        debug_print("GraphPanelWidget._build_settings_panel called")
        scroll = QScrollArea()
        scroll.setObjectName("graphSettingsScroll")
        scroll.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(280)
        debug_print("GraphPanelWidget._build_settings_panel width min=280")
        scroll.setMaximumWidth(720)
        debug_print("GraphPanelWidget._build_settings_panel width max=720")
        self.settings_scroll = scroll
        content = QWidget()
        content.setObjectName("graphSettingsContent")
        content.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._settings_layout = QGridLayout(content)
        self._settings_layout.setContentsMargins(18, 18, 18, 18)
        self._settings_layout.setSpacing(14)
        self._settings_layout.setColumnStretch(0, 1)
        self._settings_layout.setColumnStretch(1, 1)

        title = QLabel("SETTINGS")
        title.setObjectName("graphSettingsTitle")
        self._settings_layout.addWidget(title, 0, 0, 1, 2)

        self._settings_layout.addWidget(self._build_axis_group(), 1, 0)
        self._settings_layout.addWidget(self._build_display_group(), 1, 1)
        self.column_settings_group = QGroupBox("COLUMN SETTINGS")
        self.column_settings_group.setObjectName("graphSettingsSection")
        self.column_settings_group.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.column_settings_layout = QVBoxLayout(self.column_settings_group)
        self.column_settings_layout.setContentsMargins(12, 14, 12, 12)
        self.column_settings_layout.setSpacing(6)
        self._settings_layout.addWidget(self.column_settings_group, 2, 0, 1, 2)
        self._settings_layout.setRowStretch(3, 1)
        scroll.setWidget(content)
        return scroll

    def set_available_width(self, width: int) -> None:
        debug_print(f"GraphPanelWidget.set_available_width width={width}")
        bounded_width = max(0, int(width))
        self.setMinimumWidth(0)
        self.setMaximumWidth(16777215)
        self.top_controls.setMaximumWidth(bounded_width)
        self.main_content.setMaximumWidth(16777215)
        self.graph_area.setMinimumWidth(800)
        self.graph_area.setMaximumWidth(16777215)
        self.canvas.set_available_width(bounded_width)
        settings_width = min(720, bounded_width)
        self.settings_scroll.setMinimumWidth(min(280, settings_width))
        self.settings_scroll.setMaximumWidth(settings_width)
        debug_print(f"GraphPanelWidget settings max width={settings_width}")

    def _build_axis_group(self) -> QWidget:
        debug_print("GraphPanelWidget._build_axis_group called")
        group = QGroupBox("X / Y AXIS")
        group.setObjectName("graphSettingsSection")
        group.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QGridLayout(group)
        layout.setContentsMargins(18, 22, 18, 18)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(10)
        layout.setColumnStretch(1, 1)
        layout.addWidget(QLabel("X Column:"), 0, 0)
        self.x_axis_combo = QComboBox()
        self.x_axis_combo.setObjectName("graphCombo")
        self.x_axis_combo.setFixedWidth(120)
        self.x_axis_combo.currentIndexChanged.connect(self._refresh_graph)
        layout.addWidget(self.x_axis_combo, 0, 1)
        layout.addWidget(QLabel("X Conversion:"), 1, 0)
        self.x_axis_conversion_combo = QComboBox()
        self.x_axis_conversion_combo.setObjectName("graphCombo")
        self.x_axis_conversion_combo.setFixedWidth(120)
        for label, value in [("As-is", "as-is"), ("sec -> min", "sec-to-min"), ("sec -> hour", "sec-to-hour")]:
            self.x_axis_conversion_combo.addItem(label, value)
        update_combo_popup_width(self.x_axis_conversion_combo)
        self.x_axis_conversion_combo.currentIndexChanged.connect(self._refresh_graph)
        layout.addWidget(self.x_axis_conversion_combo, 1, 1)
        layout.addWidget(QLabel("X Title:"), 2, 0)
        self.x_title_edit = QLineEdit("Time")
        self.x_title_edit.setObjectName("graphLineEdit")
        self.x_title_edit.setFixedWidth(120)
        self.x_title_edit.textChanged.connect(self._refresh_graph)
        layout.addWidget(self.x_title_edit, 2, 1)
        layout.addWidget(QLabel("Y-Axis 1 Title:"), 3, 0)
        self.y1_title_edit = QLineEdit("Y1")
        self.y1_title_edit.setObjectName("graphLineEdit")
        self.y1_title_edit.setFixedWidth(120)
        self.y1_title_edit.textChanged.connect(self._refresh_graph)
        layout.addWidget(self.y1_title_edit, 3, 1)
        layout.addWidget(QLabel("Y-Axis 2 Title:"), 4, 0)
        self.y2_title_edit = QLineEdit("Y2")
        self.y2_title_edit.setObjectName("graphLineEdit")
        self.y2_title_edit.setFixedWidth(120)
        self.y2_title_edit.textChanged.connect(self._refresh_graph)
        layout.addWidget(self.y2_title_edit, 4, 1)
        return group

    def _build_display_group(self) -> QWidget:
        debug_print("GraphPanelWidget._build_display_group called")
        group = QGroupBox("DISPLAY")
        group.setObjectName("graphSettingsSection")
        group.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QGridLayout(group)
        layout.setContentsMargins(18, 22, 18, 18)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(10)
        layout.setColumnStretch(1, 1)
        layout.addWidget(QLabel("Legend Pos:"), 0, 0)
        self.legend_position_combo = QComboBox()
        self.legend_position_combo.setObjectName("graphCombo")
        self.legend_position_combo.setMinimumWidth(170)
        for label, value in [
            ("Top Left", "top-left"),
            ("Top Right", "top-right"),
            ("Bottom Left", "bottom-left"),
            ("Bottom Right", "bottom-right"),
            ("Right Outside", "right-outside"),
        ]:
            self.legend_position_combo.addItem(label, value)
        update_combo_popup_width(self.legend_position_combo)
        self.legend_position_combo.currentIndexChanged.connect(self._refresh_graph)
        layout.addWidget(self.legend_position_combo, 0, 1)

        self.legend_check = QCheckBox("Legend")
        self.legend_check.setChecked(True)
        self.legend_check.toggled.connect(self._refresh_graph)
        layout.addWidget(self.legend_check, 1, 0)
        self.grid_check = QCheckBox("Grid")
        self.grid_check.toggled.connect(self._refresh_graph)
        layout.addWidget(self.grid_check, 1, 1)

        layout.addWidget(QLabel("Trace:"), 2, 0)
        self.trace_mode_combo = QComboBox()
        self.trace_mode_combo.setObjectName("graphCombo")
        self.trace_mode_combo.setMinimumWidth(170)
        for label, value in [("Lines", "lines"), ("Markers", "markers"), ("Lines + Markers", "lines+markers")]:
            self.trace_mode_combo.addItem(label, value)
        update_combo_popup_width(self.trace_mode_combo)
        self.trace_mode_combo.currentIndexChanged.connect(self._refresh_graph)
        layout.addWidget(self.trace_mode_combo, 2, 1)

        layout.addWidget(QLabel("Style:"), 3, 0)
        self.line_style_combo = QComboBox()
        self.line_style_combo.setObjectName("graphCombo")
        self.line_style_combo.setMinimumWidth(170)
        for label, value in [("Solid", "solid"), ("Dash", "dash"), ("Dot", "dot"), ("Dash Dot", "dashdot")]:
            self.line_style_combo.addItem(label, value)
        update_combo_popup_width(self.line_style_combo)
        self.line_style_combo.currentIndexChanged.connect(self._refresh_graph)
        layout.addWidget(self.line_style_combo, 3, 1)
        return group

    def _open_file_dialog(self) -> None:
        debug_print("GraphPanelWidget._open_file_dialog called")
        patterns = " ".join(f"*{ext}" for ext in ALLOWED_TEXTDATA_EXTENSIONS)
        files, _ = QFileDialog.getOpenFileNames(self, "Select Text Data Files", "", f"Text Data ({patterns})")
        debug_print(f"GraphPanelWidget._open_file_dialog selected={files}")
        self.add_files(files)

    def _refresh_project_selector(self) -> None:
        debug_print("GraphPanelWidget._refresh_project_selector called")
        current = self.project_combo.currentData()
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        self.project_combo.addItem("Select project", None)
        for project_name in self._selected_project_names:
            info = self._projects.get(project_name)
            if not info:
                continue
            self.project_combo.addItem(project_name, project_name)
            self.project_combo.setItemData(self.project_combo.count() - 1, self._project_tooltip(info), Qt.ItemDataRole.ToolTipRole)
        index = self.project_combo.findData(current)
        if index < 0 and self.project_combo.count() > 1:
            index = 1
        self.project_combo.setCurrentIndex(index if index >= 0 else 0)
        self.project_combo.blockSignals(False)
        update_combo_popup_width(self.project_combo)
        self._refresh_folder_selector()

    def _refresh_folder_selector(self, *args) -> None:
        debug_print("GraphPanelWidget._refresh_folder_selector called")
        project_name = self.project_combo.currentData()
        current = self.folder_combo.currentData()
        self.folder_combo.blockSignals(True)
        self.folder_combo.clear()
        self._folder_files = {}
        self.folder_combo.addItem("Select folder", None)
        if project_name:
            for label, folder_path, files in self._folder_options(project_name):
                self._folder_files[folder_path] = files
                self.folder_combo.addItem(label, folder_path)
                self.folder_combo.setItemData(self.folder_combo.count() - 1, folder_path, Qt.ItemDataRole.ToolTipRole)
        index = self.folder_combo.findData(current)
        if index < 0 and self.folder_combo.count() > 1:
            index = 1
        self.folder_combo.setCurrentIndex(index if index >= 0 else 0)
        self.folder_combo.blockSignals(False)
        update_combo_popup_width(self.folder_combo)
        self._refresh_file_selector()

    def _refresh_file_selector(self, *args) -> None:
        debug_print("GraphPanelWidget._refresh_file_selector called")
        folder_path = self.folder_combo.currentData()
        current = self.file_combo.currentData()
        self.file_combo.blockSignals(True)
        self.file_combo.clear()
        self.file_combo.addItem("Select text file", None)
        for file_path in self._folder_files.get(folder_path, []):
            path = Path(file_path)
            self.file_combo.addItem(path.name, file_path)
            self.file_combo.setItemData(self.file_combo.count() - 1, str(path), Qt.ItemDataRole.ToolTipRole)
        index = self.file_combo.findData(current)
        if index < 0 and self.file_combo.count() > 1:
            index = 1
        self.file_combo.setCurrentIndex(index if index >= 0 else 0)
        self.file_combo.blockSignals(False)
        update_combo_popup_width(self.file_combo)
        self._sync_add_button_state()

    def _sync_add_button_state(self, *args) -> None:
        self.add_file_button.setEnabled(bool(self.file_combo.currentData()))

    def _add_selected_graph_file(self) -> None:
        debug_print("GraphPanelWidget._add_selected_graph_file called")
        file_path = self.file_combo.currentData()
        if not file_path:
            debug_print("GraphPanelWidget._add_selected_graph_file no file")
            return
        self.add_files([file_path])

    def _download_png(self) -> None:
        debug_print("GraphPanelWidget._download_png called")
        self.canvas.download_png(f"custom_graph_{self.panel_number}")

    def _folder_options(self, project_name: str) -> list[tuple[str, str, list[str]]]:
        info = self._projects.get(project_name) or {}
        project_root = Path(info.get("path") or "").resolve()
        roots: list[Path] = []
        if info.get("textdata_path"):
            roots.append(Path(info["textdata_path"]))
        if info.get("path"):
            roots.append(Path(info["path"]))
        folder_files: dict[str, set[str]] = {}
        seen_files: set[str] = set()
        skip_names = set(SKIP_FOLDERS) | {"VTK", "vtk", ".git", "__pycache__"}
        for root in roots:
            root = Path(root)
            if not root.exists() or not root.is_dir():
                continue
            try:
                for path in root.rglob("*"):
                    if not path.is_file():
                        continue
                    if any(part in skip_names for part in path.parts):
                        continue
                    if path.suffix.lower() not in ALLOWED_TEXTDATA_EXTENSIONS:
                        continue
                    resolved = str(path.resolve())
                    if resolved in seen_files:
                        continue
                    seen_files.add(resolved)
                    folder = str(path.parent.resolve())
                    folder_files.setdefault(folder, set()).add(resolved)
            except (OSError, PermissionError) as exc:
                debug_print(f"GraphPanelWidget._folder_options scan error root={root} error={exc}")
        options: list[tuple[str, str, list[str]]] = []
        for folder_path, files in sorted(folder_files.items()):
            label = self._folder_label(project_root, Path(folder_path))
            options.append((label, folder_path, sorted(files)))
        return options

    def _folder_label(self, project_root: Path, folder: Path) -> str:
        try:
            relative = folder.resolve().relative_to(project_root)
        except ValueError:
            return folder.name
        if str(relative) == ".":
            return "Project root"
        return relative.as_posix()

    def _project_tooltip(self, info: dict) -> str:
        path = info.get("path") or info.get("textdata_path")
        return str(path) if path else ""

    def _refresh_file_sections(self) -> None:
        debug_print("GraphPanelWidget._refresh_file_sections called")
        assert self._sources_layout is not None
        self._clear_layout(self._sources_layout)
        self._column_checkboxes.clear()
        for file_path in self._files:
            self._sources_layout.addWidget(self._build_file_section(file_path))
        if not self._files:
            label = QLabel("No files selected. Add any supported text-data file.")
            label.setObjectName("mutedInfo")
            self._sources_layout.addWidget(label)
        self._refresh_column_settings()
        debug_print("GraphPanelWidget._refresh_file_sections complete")

    def _build_file_section(self, file_path: str) -> QWidget:
        debug_print(f"GraphPanelWidget._build_file_section file_path={file_path}")
        frame = QFrame()
        frame.setObjectName("graphFileSection")
        frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(frame)
        header = QHBoxLayout()
        title = QLabel(self._file_label(file_path))
        title.setToolTip(str(Path(file_path)))
        header.addWidget(title)
        remove_button = QPushButton("x")
        remove_button.setFixedWidth(26)
        remove_button.clicked.connect(lambda *_: self._remove_file(file_path))
        header.addStretch(1)
        header.addWidget(remove_button)
        layout.addLayout(header)

        source = GenericTextDataSource(file_path)
        if not source.load():
            layout.addWidget(QLabel("Could not load file"))
            return frame
        row = QHBoxLayout()
        for column in source.columns():
            check = QCheckBox(column)
            check.setChecked(column in self._columns_by_file.get(file_path, []))
            check.toggled.connect(lambda checked, f=file_path, c=column: self._on_column_toggled(f, c, checked))
            self._column_checkboxes[(file_path, column)] = check
            row.addWidget(check)
        row.addStretch(1)
        layout.addLayout(row)
        return frame

    def _remove_file(self, file_path: str) -> None:
        debug_print(f"GraphPanelWidget._remove_file file_path={file_path}")
        if file_path in self._files:
            self._files.remove(file_path)
        self._columns_by_file.pop(file_path, None)
        self._column_settings.pop(file_path, None)
        self._refresh_auto_legends()
        self._refresh_file_sections()
        self._refresh_x_axis_options()
        self._refresh_graph()

    def _on_column_toggled(self, file_path: str, column: str, checked: bool) -> None:
        debug_print(f"GraphPanelWidget._on_column_toggled file={file_path} column={column} checked={checked}")
        selected = self._columns_by_file.setdefault(file_path, [])
        if checked and column not in selected:
            selected.append(column)
        if not checked and column in selected:
            selected.remove(column)
        self._ensure_column_setting(file_path, column)
        self._refresh_auto_legends()
        self._refresh_column_settings()
        self._refresh_graph()

    def _refresh_x_axis_options(self) -> None:
        debug_print("GraphPanelWidget._refresh_x_axis_options called")
        current = self.x_axis_combo.currentData()
        self.x_axis_combo.blockSignals(True)
        self.x_axis_combo.clear()
        if self._files:
            source = GenericTextDataSource(self._files[0])
            if source.load():
                for column in source.columns():
                    self.x_axis_combo.addItem(column, column)
        idx = self.x_axis_combo.findData(current)
        self.x_axis_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.x_axis_combo.blockSignals(False)
        update_combo_popup_width(self.x_axis_combo)
        debug_print(f"GraphPanelWidget._refresh_x_axis_options count={self.x_axis_combo.count()}")

    def _refresh_column_settings(self) -> None:
        debug_print("GraphPanelWidget._refresh_column_settings called")
        self._clear_layout(self.column_settings_layout)
        self._axis_radios.clear()
        self._legend_edits.clear()
        self._conversion_combos.clear()
        self._color_combos.clear()
        for file_path, columns in self._columns_by_file.items():
            for column in columns:
                self.column_settings_layout.addWidget(self._build_column_setting(file_path, column))
        if not any(self._columns_by_file.values()):
            self.column_settings_layout.addWidget(QLabel("Select columns to configure traces."))
        debug_print("GraphPanelWidget._refresh_column_settings complete")

    def _build_column_setting(self, file_path: str, column: str) -> QWidget:
        debug_print(f"GraphPanelWidget._build_column_setting file={file_path} column={column}")
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(2)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)
        layout.setColumnStretch(3, 1)
        settings = self._ensure_column_setting(file_path, column)
        title = QLabel(f"{self._file_label(file_path)} -> {column}")
        title.setToolTip(str(Path(file_path)))
        title.setMaximumHeight(20)
        layout.addWidget(title, 0, 0, 1, 4)
        layout.addWidget(QLabel("Legend:"), 1, 0)
        layout.addWidget(QLabel("Color:"), 1, 1)
        layout.addWidget(QLabel("Conversions:"), 1, 2)
        layout.addWidget(QLabel("Y-axis:"), 1, 3)

        legend = QLineEdit(settings.get("legend", column))
        legend.setObjectName("graphLineEdit")
        legend.setFixedWidth(145)
        legend.setFixedHeight(30)
        legend.textChanged.connect(lambda text, f=file_path, c=column: self._set_legend(f, c, text))
        self._legend_edits[(file_path, column)] = legend
        layout.addWidget(legend, 2, 0)

        color_combo = QComboBox()
        color_combo.setObjectName("graphCombo")
        color_combo.setFixedWidth(125)
        color_combo.setFixedHeight(30)
        for index, color in enumerate(PlotStyle.SERIES_COLORS):
            color_combo.addItem(
                self._color_icon(color),
                f"Color {index + 1}",
                color,
            )
        color_index = color_combo.findData(settings.get("color"))
        if color_index >= 0:
            color_combo.setCurrentIndex(color_index)
        color_combo.currentIndexChanged.connect(
            lambda _index, f=file_path, c=column, combo=color_combo: self._set_color(f, c, combo.currentData())
        )
        update_combo_popup_width(color_combo)
        self._color_combos[(file_path, column)] = color_combo
        layout.addWidget(color_combo, 2, 1)

        conversion_combo = QComboBox()
        conversion_combo.setObjectName("graphCombo")
        conversion_combo.setFixedWidth(125)
        conversion_combo.setFixedHeight(30)
        for label, value in [("As-is", "as-is"), ("%", "percent"), ("MPa", "mpa"), ("GPa", "gpa")]:
            conversion_combo.addItem(label, value)
        update_combo_popup_width(conversion_combo)
        conversion_index = conversion_combo.findData(settings.get("conversion", "as-is"))
        conversion_combo.setCurrentIndex(conversion_index if conversion_index >= 0 else 0)
        conversion_combo.currentIndexChanged.connect(
            lambda _index, f=file_path, c=column, combo=conversion_combo: self._set_conversion(f, c, combo.currentData())
        )
        self._conversion_combos[(file_path, column)] = conversion_combo
        layout.addWidget(conversion_combo, 2, 2)

        y_axis_widget = QWidget()
        y_axis_layout = QHBoxLayout(y_axis_widget)
        y_axis_layout.setContentsMargins(0, 0, 0, 0)
        y_axis_layout.setSpacing(8)
        y1 = QRadioButton("Y1")
        y2 = QRadioButton("Y2")
        yaxis = settings.get("yaxis", "y1")
        y1.setChecked(yaxis != "y2")
        y2.setChecked(yaxis == "y2")
        y1.toggled.connect(lambda checked, f=file_path, c=column: self._set_yaxis(f, c, "y1") if checked else None)
        y2.toggled.connect(lambda checked, f=file_path, c=column: self._set_yaxis(f, c, "y2") if checked else None)
        self._axis_radios[(file_path, column, "y1")] = y1
        self._axis_radios[(file_path, column, "y2")] = y2
        y_axis_layout.addWidget(y1)
        y_axis_layout.addWidget(y2)
        y_axis_layout.addStretch(1)
        layout.addWidget(y_axis_widget, 2, 3)
        return widget

    def _color_icon(self, color: str) -> QIcon:
        pixmap = QPixmap(18, 18)
        pixmap.fill(QColor(color))
        return QIcon(pixmap)

    def _set_legend(self, file_path: str, column: str, text: str) -> None:
        debug_print(f"GraphPanelWidget._set_legend file={file_path} column={column} text={text}")
        settings = self._ensure_column_setting(file_path, column)
        settings["legend"] = text
        settings["legend_auto"] = "false"
        self._refresh_graph()

    def _set_conversion(self, file_path: str, column: str, conversion: str) -> None:
        debug_print(f"GraphPanelWidget._set_conversion file={file_path} column={column} conversion={conversion}")
        self._ensure_column_setting(file_path, column)["conversion"] = conversion or "as-is"
        self._refresh_graph()

    def _set_color(self, file_path: str, column: str, color: str) -> None:
        debug_print(f"GraphPanelWidget._set_color file={file_path} column={column} color={color}")
        self._ensure_column_setting(file_path, column)["color"] = color or PlotStyle.series_color(0)
        self._refresh_graph()

    def _set_yaxis(self, file_path: str, column: str, yaxis: str) -> None:
        debug_print(f"GraphPanelWidget._set_yaxis file={file_path} column={column} yaxis={yaxis}")
        self._ensure_column_setting(file_path, column)["yaxis"] = yaxis
        self._refresh_graph()

    def _ensure_column_setting(self, file_path: str, column: str) -> dict[str, str]:
        debug_print(f"GraphPanelWidget._ensure_column_setting file={file_path} column={column}")
        settings = self._column_settings.setdefault(file_path, {}).setdefault(column, {})
        settings.setdefault("legend_auto", "true")
        settings.setdefault("legend", self._default_legend(file_path, column))
        settings.setdefault("yaxis", "y1")
        settings.setdefault("conversion", "as-is")
        settings.setdefault("color", PlotStyle.series_color(self._series_index(file_path, column)))
        debug_print(f"GraphPanelWidget._ensure_column_setting settings={settings}")
        return settings

    def _series_index(self, file_path: str, column: str) -> int:
        index = 0
        for current_file, columns in self._columns_by_file.items():
            for current_column in columns:
                if current_file == file_path and current_column == column:
                    return index
                index += 1
        return index

    def _refresh_auto_legends(self) -> None:
        selected: list[tuple[str, str]] = [
            (file_path, column)
            for file_path, columns in self._columns_by_file.items()
            for column in columns
        ]
        duplicate_columns = {
            column
            for _, column in selected
            if sum(1 for _file, current_column in selected if current_column == column) > 1
        }
        for file_path, column in selected:
            settings = self._column_settings.setdefault(file_path, {}).setdefault(column, {})
            if settings.get("legend_auto", "true") == "false":
                continue
            settings["legend_auto"] = "true"
            settings["legend"] = self._default_legend(file_path, column, duplicate_columns)

    def _default_legend(
        self,
        file_path: str,
        column: str,
        duplicate_columns: set[str] | None = None,
    ) -> str:
        duplicate_columns = duplicate_columns or set()
        if column not in duplicate_columns:
            return column
        return f"{self._short_file_label(file_path)}: {column}"

    def _short_file_label(self, file_path: str) -> str:
        label = self._file_label(file_path)
        parts = label.split("/")
        if len(parts) >= 2:
            return " / ".join(part.strip() for part in parts[:-1] if part.strip())
        return Path(file_path).parent.name

    def _refresh_graph(self, *args) -> None:
        debug_print("GraphPanelWidget._refresh_graph called")
        self._refresh_auto_legends()
        self.canvas.render(self.state())
        debug_print("GraphPanelWidget._refresh_graph complete")

    def _file_label(self, file_path: str) -> str:
        path = Path(file_path)
        resolved = path.resolve()
        for project_name, info in self._projects.items():
            project_root = info.get("path")
            if not project_root:
                continue
            try:
                relative = resolved.relative_to(Path(project_root).resolve())
            except ValueError:
                continue
            return f"{project_name} / {relative.as_posix()}"
        return f"{path.parent.name} / {path.name}"

    def _clear_layout(self, layout) -> None:
        debug_print("GraphPanelWidget._clear_layout called")
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            if child_layout is not None:
                self._clear_layout(child_layout)
