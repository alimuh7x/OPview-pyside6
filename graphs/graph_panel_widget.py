"""One Custom Graph panel tab."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
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
from config.constants import ALLOWED_TEXTDATA_EXTENSIONS
from data.text_sources import GenericTextDataSource
from graphs.graph_canvas import GraphCanvas
from utils.combo_box_utils import update_combo_popup_width


class GraphPanelWidget(QWidget):
    """Controls and chart canvas for one graph panel."""

    def __init__(self, panel_number: int, suggested_files: list[str] | None = None) -> None:
        debug_print(f"GraphPanelWidget.__init__ start panel_number={panel_number}")
        super().__init__()
        self.setObjectName("customGraphPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.panel_number = panel_number
        self._suggested_files = suggested_files or []
        self._files: list[str] = []
        self._columns_by_file: dict[str, list[str]] = {}
        self._column_settings: dict[str, dict[str, dict[str, str]]] = {}
        self._column_checkboxes: dict[tuple[str, str], QCheckBox] = {}
        self._axis_radios: dict[tuple[str, str, str], QRadioButton] = {}
        self._legend_edits: dict[tuple[str, str], QLineEdit] = {}
        self._conversion_combos: dict[tuple[str, str], QComboBox] = {}
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

    def set_suggested_files(self, files: list[str]) -> None:
        debug_print(f"GraphPanelWidget.set_suggested_files count={len(files)}")
        self._suggested_files = files
        self.suggested_file_combo.clear()
        self.suggested_file_combo.addItem("Select discovered file", None)
        for file_path in files:
            self.suggested_file_combo.addItem(self._file_label(file_path), file_path)
        update_combo_popup_width(self.suggested_file_combo)

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
        self.add_file_button = QPushButton("+ Add Text File")
        self.add_file_button.setProperty("accent", True)
        self.add_file_button.clicked.connect(self._open_file_dialog)
        toolbar.addWidget(self.add_file_button)

        self.suggested_file_combo = QComboBox()
        self.suggested_file_combo.setObjectName("graphCombo")
        self.suggested_file_combo.setMinimumWidth(260)
        self.suggested_file_combo.currentIndexChanged.connect(self._add_selected_suggestion)
        toolbar.addWidget(self.suggested_file_combo)
        toolbar.addStretch(1)
        top_layout.addLayout(toolbar)

        self.set_suggested_files(self._suggested_files)

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
        self.column_settings_layout.setContentsMargins(18, 22, 18, 18)
        self.column_settings_layout.setSpacing(14)
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

    def _add_selected_suggestion(self, index: int) -> None:
        debug_print(f"GraphPanelWidget._add_selected_suggestion index={index}")
        file_path = self.suggested_file_combo.itemData(index)
        if not file_path:
            debug_print("GraphPanelWidget._add_selected_suggestion no file")
            return
        self.add_files([file_path])
        self.suggested_file_combo.setCurrentIndex(0)

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
        header.addWidget(QLabel(Path(file_path).name))
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
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(8)
        layout.setColumnStretch(1, 1)
        settings = self._ensure_column_setting(file_path, column)
        title = QLabel(f"{Path(file_path).name} -> {column}")
        layout.addWidget(title, 0, 0, 1, 7)
        layout.addWidget(QLabel("Legend:"), 1, 0)
        legend = QLineEdit(settings.get("legend", column))
        legend.setObjectName("graphLineEdit")
        legend.textChanged.connect(lambda text, f=file_path, c=column: self._set_legend(f, c, text))
        self._legend_edits[(file_path, column)] = legend
        layout.addWidget(legend, 1, 1)
        layout.addWidget(QLabel("Conversion:"), 1, 2)
        conversion_combo = QComboBox()
        conversion_combo.setObjectName("graphCombo")
        conversion_combo.setFixedWidth(100)
        for label, value in [("As-is", "as-is"), ("%", "percent"), ("MPa", "mpa"), ("GPa", "gpa")]:
            conversion_combo.addItem(label, value)
        update_combo_popup_width(conversion_combo)
        conversion_index = conversion_combo.findData(settings.get("conversion", "as-is"))
        conversion_combo.setCurrentIndex(conversion_index if conversion_index >= 0 else 0)
        conversion_combo.currentIndexChanged.connect(
            lambda _index, f=file_path, c=column, combo=conversion_combo: self._set_conversion(f, c, combo.currentData())
        )
        self._conversion_combos[(file_path, column)] = conversion_combo
        layout.addWidget(conversion_combo, 1, 3)
        layout.addWidget(QLabel("Y-Axis:"), 1, 4)
        y1 = QRadioButton("Y1")
        y2 = QRadioButton("Y2")
        yaxis = settings.get("yaxis", "y1")
        y1.setChecked(yaxis != "y2")
        y2.setChecked(yaxis == "y2")
        y1.toggled.connect(lambda checked, f=file_path, c=column: self._set_yaxis(f, c, "y1") if checked else None)
        y2.toggled.connect(lambda checked, f=file_path, c=column: self._set_yaxis(f, c, "y2") if checked else None)
        self._axis_radios[(file_path, column, "y1")] = y1
        self._axis_radios[(file_path, column, "y2")] = y2
        layout.addWidget(y1, 1, 5)
        layout.addWidget(y2, 1, 6)
        return widget

    def _set_legend(self, file_path: str, column: str, text: str) -> None:
        debug_print(f"GraphPanelWidget._set_legend file={file_path} column={column} text={text}")
        self._ensure_column_setting(file_path, column)["legend"] = text
        self._refresh_graph()

    def _set_conversion(self, file_path: str, column: str, conversion: str) -> None:
        debug_print(f"GraphPanelWidget._set_conversion file={file_path} column={column} conversion={conversion}")
        self._ensure_column_setting(file_path, column)["conversion"] = conversion or "as-is"
        self._refresh_graph()

    def _set_yaxis(self, file_path: str, column: str, yaxis: str) -> None:
        debug_print(f"GraphPanelWidget._set_yaxis file={file_path} column={column} yaxis={yaxis}")
        self._ensure_column_setting(file_path, column)["yaxis"] = yaxis
        self._refresh_graph()

    def _ensure_column_setting(self, file_path: str, column: str) -> dict[str, str]:
        debug_print(f"GraphPanelWidget._ensure_column_setting file={file_path} column={column}")
        settings = self._column_settings.setdefault(file_path, {}).setdefault(column, {})
        settings.setdefault("legend", column)
        settings.setdefault("yaxis", "y1")
        settings.setdefault("conversion", "as-is")
        debug_print(f"GraphPanelWidget._ensure_column_setting settings={settings}")
        return settings

    def _refresh_graph(self, *args) -> None:
        debug_print("GraphPanelWidget._refresh_graph called")
        self.canvas.render(self.state())
        debug_print("GraphPanelWidget._refresh_graph complete")

    def _file_label(self, file_path: str) -> str:
        path = Path(file_path)
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
