"""One Custom Graph panel tab."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtCore import Qt, QRect, QSize
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
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
from config import units
from config.constants import ALLOWED_TEXTDATA_EXTENSIONS, SKIP_FOLDERS
from data.text_sources import GenericTextDataSource
from graphs.graph_animation_player import GraphAnimationPlayer
from graphs.formula_dialog import FormulaDialog
from graphs.graph_canvas import GraphCanvas
from graphs.symbol_picker import attach_symbol_picker
from utils.combo_box_utils import hide_popup_focus_outline, update_combo_popup_width
from viewer.plot_style import PlotStyle

_ASSETS = Path(__file__).resolve().parent.parent / "assets"
_FILE_COMBO_MAX_VISIBLE_ITEMS = 12


_TIME_LIKE_COLUMNS = ("time", "t")  # preferred X column, case-insensitive
_DEFAULT_TITLES = {"x": "Time", "y1": "Y1", "y2": "Y2"}
_SETTINGS_SCROLLBAR_ALLOWANCE = 20  # room for the vertical scrollbar beside the settings
_CUSTOM = "Custom"  # last entry of a From dropdown: opens the formula dialog
_NO_UNIT = "-"  # shown when a column has no unit; also the dimensionless unit
_UNIT_COMBO_WIDTH = 128  # the from and to dropdowns are the same width; room for "percent (%)"
_MAX_LISTED_COLUMNS = 2  # more columns on one axis are abbreviated: "a, b, …"


def conversion_options(source_unit: str) -> list[tuple[str, str]]:
    """Entries of a "To" combo: an em dash (no conversion), then the scale of the source unit without the source.

    The scale runs small to large (milli ... base ... Mega) and is named by prefix; the unit chosen in From is
    not listed again. An unknown unit has nothing to convert to.
    """
    family = units.family_units(source_unit)
    options = [("\u2014", "as-is")]
    return options + [(units.scale_label(unit), f"to:{unit}") for unit in family if unit != source_unit]


class _RotatedSettingsLabel(QWidget):
    """Paints a single word rotated for the collapsed settings rail."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._text = text
        self.setObjectName("graphSettingsCollapsedLabel")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def text(self) -> str:
        return self._text

    def rotation_degrees(self) -> int:
        return 90

    def sizeHint(self) -> QSize:
        metrics = self.fontMetrics()
        return QSize(metrics.height() + 8, metrics.horizontalAdvance(self._text) + 8)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setPen(QColor("#0d2b55"))
        painter.setFont(self.font())
        painter.translate(self.width(), 0)
        painter.rotate(self.rotation_degrees())
        painter.drawText(QRect(0, 0, self.height(), self.width()), Qt.AlignmentFlag.AlignCenter, self._text)


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
        self._unit_combos: dict[tuple[str, str], QComboBox] = {}
        self._x_formula = ""
        self._x_custom_unit = ""
        self._file_column_names: dict[str, tuple[str, ...]] = {}  # columns of each file, by file path
        self._color_combos: dict[tuple[str, str], QComboBox] = {}
        self._sources_layout: QVBoxLayout | None = None
        self._settings_layout: QGridLayout | None = None
        self._title_user_set = {"x": False, "y1": False, "y2": False}  # a typed title is never overwritten
        self._auto_titles = dict(_DEFAULT_TITLES)  # what the panel itself last wrote into each title
        self._file_units: dict[str, dict[str, str]] = {}  # units row of each file, by file path
        self._animation_player_class = GraphAnimationPlayer
        self._animation_player = None
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
            "x_axis_source_unit": self._unit_of(self.x_axis_unit_combo),
            "x_axis_formula": self._x_formula,
            "x_axis_custom_unit": self._x_custom_unit,
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
        self.file_combo.setMaxVisibleItems(_FILE_COMBO_MAX_VISIBLE_ITEMS)
        self.file_combo.currentIndexChanged.connect(self._add_selected_graph_file)
        toolbar.addWidget(self.file_combo)

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
        self.download_animation_button = QPushButton(QIcon(str(_ASSETS / "play.png")), "Animate")
        self.download_animation_button.setIconSize(QSize(16, 16))
        self.download_animation_button.setProperty("accent", True)
        self.download_animation_button.setToolTip("Open reveal animation")
        self.download_animation_button.clicked.connect(self._open_animation_player)
        toolbar.addWidget(self.download_animation_button)
        toolbar.addStretch(1)
        top_layout.addLayout(toolbar)

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
        self._refresh_project_selector()
        self._hide_combo_outlines()
        debug_print("GraphPanelWidget._build_ui complete")

    def _build_settings_panel(self) -> QWidget:
        debug_print("GraphPanelWidget._build_settings_panel called")
        container = QWidget()
        container.setObjectName("graphSettingsContainer")
        container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("graphSettingsScroll")
        scroll.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # never scroll sideways
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

        header = QWidget()
        header.setObjectName("graphSettingsHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        title = QLabel("SETTINGS")
        title.setObjectName("graphSettingsTitle")
        header_layout.addWidget(title)
        header_layout.addStretch(1)
        self.settings_toggle_button = QPushButton(header)
        self.settings_toggle_button.setObjectName("graphSettingsToggleButton")
        self.settings_toggle_button.setCheckable(True)
        self.settings_toggle_button.setChecked(True)
        self.settings_toggle_button.setFlat(True)
        self.settings_toggle_button.setIconSize(QSize(28, 28))
        self.settings_toggle_button.toggled.connect(self._set_settings_visible)
        header_layout.addWidget(self.settings_toggle_button)
        self._settings_layout.addWidget(header, 0, 0, 1, 2)

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
        container_layout.addWidget(scroll)

        self.settings_collapsed_rail = QWidget()
        self.settings_collapsed_rail.setObjectName("graphSettingsCollapsedRail")
        self.settings_collapsed_rail.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.settings_collapsed_rail.setFixedWidth(56)
        rail_layout = QVBoxLayout(self.settings_collapsed_rail)
        rail_layout.setContentsMargins(8, 18, 8, 8)
        rail_layout.setSpacing(8)
        self.settings_collapsed_toggle_button = QPushButton(self.settings_collapsed_rail)
        self.settings_collapsed_toggle_button.setObjectName("graphSettingsCollapsedToggleButton")
        self.settings_collapsed_toggle_button.setCheckable(True)
        self.settings_collapsed_toggle_button.setChecked(False)
        self.settings_collapsed_toggle_button.setFlat(True)
        self.settings_collapsed_toggle_button.setIconSize(QSize(28, 28))
        self.settings_collapsed_toggle_button.toggled.connect(self._set_settings_visible)
        self.settings_collapsed_label = _RotatedSettingsLabel("Settings", self.settings_collapsed_rail)
        rail_layout.addWidget(self.settings_collapsed_toggle_button, 0, Qt.AlignmentFlag.AlignHCenter)
        rail_layout.addWidget(self.settings_collapsed_label, 0, Qt.AlignmentFlag.AlignHCenter)
        rail_layout.addStretch(1)
        self.settings_collapsed_rail.hide()
        container_layout.addWidget(self.settings_collapsed_rail)
        self._update_settings_toggle_button(True)
        return container

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
        # Wide enough for the settings content, so nothing is cut off and no horizontal scrollbar is needed.
        content_width = self.settings_scroll.widget().minimumSizeHint().width() + _SETTINGS_SCROLLBAR_ALLOWANCE
        settings_width = min(max(720, content_width), bounded_width)
        self.settings_scroll.setMinimumWidth(min(max(280, content_width), settings_width))
        self.settings_scroll.setMaximumWidth(settings_width)
        debug_print(f"GraphPanelWidget settings max width={settings_width}")

    def _set_settings_visible(self, visible: bool) -> None:
        debug_print(f"GraphPanelWidget._set_settings_visible visible={visible}")
        settings_visible = bool(visible)
        self.settings_scroll.setVisible(settings_visible)
        self.settings_collapsed_rail.setVisible(not settings_visible)
        for button in (self.settings_toggle_button, self.settings_collapsed_toggle_button):
            was_blocked = button.blockSignals(True)
            button.setChecked(settings_visible)
            button.blockSignals(was_blocked)
        self._update_settings_toggle_button(settings_visible)

    def _update_settings_toggle_button(self, settings_visible: bool) -> None:
        asset_name = "show_sidebar.png" if settings_visible else "hide_sidebar.png"
        icon = QIcon(str(_ASSETS / asset_name))
        self.settings_toggle_button.setIcon(icon)
        self.settings_collapsed_toggle_button.setIcon(icon)
        self.settings_toggle_button.setProperty("icon_asset", asset_name)
        self.settings_collapsed_toggle_button.setProperty("icon_asset", asset_name)
        tooltip = "Hide settings" if settings_visible else "Show settings"
        self.settings_toggle_button.setToolTip(tooltip)
        self.settings_collapsed_toggle_button.setToolTip(tooltip)

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
        self.x_axis_combo.currentIndexChanged.connect(self._on_x_column_changed)
        layout.addWidget(self.x_axis_combo, 0, 1)
        layout.addWidget(QLabel("X Convert:"), 1, 0)
        self.x_axis_conversion_combo = QComboBox()
        self.x_axis_conversion_combo.setObjectName("graphCombo")
        self.x_axis_conversion_combo.setFixedWidth(_UNIT_COMBO_WIDTH)
        self.x_axis_unit_combo = self._build_unit_combo()
        self._fill_conversion_combo(self.x_axis_conversion_combo, _NO_UNIT, "as-is")
        self.x_axis_conversion_combo.currentIndexChanged.connect(self._refresh_graph)
        self.x_axis_unit_combo.currentIndexChanged.connect(self._on_x_unit_changed)
        self.x_axis_unit_combo.activated.connect(self._on_x_unit_activated)
        x_conversion_row = QWidget()
        x_conversion_layout = QHBoxLayout(x_conversion_row)
        x_conversion_layout.setContentsMargins(0, 0, 0, 0)
        x_conversion_layout.setSpacing(6)
        x_conversion_layout.addWidget(self.x_axis_unit_combo)
        x_conversion_layout.addWidget(QLabel("to"))
        x_conversion_layout.addWidget(self.x_axis_conversion_combo)
        x_conversion_layout.addStretch(1)
        layout.addWidget(x_conversion_row, 1, 1)
        layout.addWidget(QLabel("X Title:"), 2, 0)
        self.x_title_edit = QLineEdit("Time")
        self.x_title_edit.setObjectName("graphLineEdit")
        self.x_title_edit.setMinimumWidth(120)  # grows to fill the column
        self.x_title_edit.editingFinished.connect(self._refresh_graph)
        attach_symbol_picker(self.x_title_edit)
        layout.addWidget(self.x_title_edit, 2, 1)
        layout.addWidget(QLabel("Y-Axis 1 Title:"), 3, 0)
        self.y1_title_edit = QLineEdit("Y1")
        self.y1_title_edit.setObjectName("graphLineEdit")
        self.y1_title_edit.setMinimumWidth(120)  # grows to fill the column
        self.y1_title_edit.editingFinished.connect(self._refresh_graph)
        attach_symbol_picker(self.y1_title_edit)
        layout.addWidget(self.y1_title_edit, 3, 1)
        layout.addWidget(QLabel("Y-Axis 2 Title:"), 4, 0)
        self.y2_title_edit = QLineEdit("Y2")
        self.y2_title_edit.setObjectName("graphLineEdit")
        self.y2_title_edit.setMinimumWidth(120)  # grows to fill the column
        self.y2_title_edit.editingFinished.connect(self._refresh_graph)
        attach_symbol_picker(self.y2_title_edit)
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
        self.legend_position_combo.setMinimumWidth(130)
        for label, value in [
            ("Top Left", "top-left"),
            ("Middle Top", "middle-top"),
            ("Top Right", "top-right"),
            ("Middle Left", "middle-left"),
            ("Middle Right", "middle-right"),
            ("Bottom Left", "bottom-left"),
            ("Middle Bottom", "middle-bottom"),
            ("Bottom Right", "bottom-right"),
            ("Right Outside", "right-outside"),
        ]:
            debug_print(f"GraphPanelWidget adding legend position label={label} value={value}")
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
        self.trace_mode_combo.setMinimumWidth(130)
        for label, value in [("Lines", "lines"), ("Markers", "markers"), ("Lines + Markers", "lines+markers")]:
            self.trace_mode_combo.addItem(label, value)
        update_combo_popup_width(self.trace_mode_combo)
        self.trace_mode_combo.currentIndexChanged.connect(self._refresh_graph)
        layout.addWidget(self.trace_mode_combo, 2, 1)

        layout.addWidget(QLabel("Style:"), 3, 0)
        self.line_style_combo = QComboBox()
        self.line_style_combo.setObjectName("graphCombo")
        self.line_style_combo.setMinimumWidth(130)
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
        index = self.project_combo.findData(current) if current else -1
        if index < 0 and self.project_combo.count() > 1:
            index = 1
            debug_print("GraphPanelWidget selecting first available project")
        self.project_combo.setCurrentIndex(index if index >= 0 else 0)
        debug_print(f"GraphPanelWidget project selector index={self.project_combo.currentIndex()}")
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
        index = self.folder_combo.findData(current) if current else -1
        if index < 0 and self.folder_combo.count() > 1:
            index = 1
            debug_print("GraphPanelWidget selecting first available folder")
        self.folder_combo.setCurrentIndex(index if index >= 0 else 0)
        debug_print(f"GraphPanelWidget folder selector index={self.folder_combo.currentIndex()}")
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
        index = self.file_combo.findData(current) if current else -1
        if index < 0:
            debug_print("GraphPanelWidget no previous file selection; waiting for user click")
        self.file_combo.setCurrentIndex(index if index >= 0 else 0)
        debug_print(f"GraphPanelWidget file selector index={self.file_combo.currentIndex()}")
        self.file_combo.blockSignals(False)
        self._update_file_combo_scrollbar()
        update_combo_popup_width(self.file_combo)
        debug_print("GraphPanelWidget file selector refreshed without auto-add")

    def _update_file_combo_scrollbar(self) -> None:
        item_count = self.file_combo.count()
        debug_print(f"GraphPanelWidget._update_file_combo_scrollbar count={item_count}")
        debug_print(f"GraphPanelWidget._update_file_combo_scrollbar max_visible={_FILE_COMBO_MAX_VISIBLE_ITEMS}")
        scrollbar_policy = (
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
            if item_count > _FILE_COMBO_MAX_VISIBLE_ITEMS
            else Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        debug_print(f"GraphPanelWidget._update_file_combo_scrollbar policy={scrollbar_policy}")
        self.file_combo.view().setVerticalScrollBarPolicy(scrollbar_policy)
        debug_print("GraphPanelWidget._update_file_combo_scrollbar applied")

    def _add_selected_graph_file(self) -> None:
        debug_print("GraphPanelWidget._add_selected_graph_file called")
        file_path = self.file_combo.currentData()
        if not file_path:
            debug_print("GraphPanelWidget._add_selected_graph_file no file")
            return
        debug_print(f"GraphPanelWidget._add_selected_graph_file file={file_path}")
        self.add_files([file_path])

    def _download_png(self) -> None:
        debug_print("GraphPanelWidget._download_png called")
        self.canvas.download_png(f"custom_graph_{self.panel_number}")

    def _open_animation_player(self) -> None:
        debug_print("GraphPanelWidget._open_animation_player called")
        if self._animation_player is not None and self._animation_player.isVisible():
            debug_print("GraphPanelWidget animation player already visible")
            self._animation_player.raise_()
            debug_print("GraphPanelWidget animation player raised")
            self._animation_player.activateWindow()
            debug_print("GraphPanelWidget animation player activated")
            return
        state = self.state()
        debug_print(f"GraphPanelWidget animation file count={len(state.get('files', []))}")
        debug_print(f"GraphPanelWidget animation panel_number={self.panel_number}")
        self._animation_player = self._animation_player_class(
            state,
            self.panel_number,
            parent=self,
        )
        debug_print("GraphPanelWidget animation player created")
        self._animation_player.show()
        debug_print("GraphPanelWidget animation player shown")

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
            reason = QLabel(source.error or "Could not load file")
            reason.setWordWrap(True)
            layout.addWidget(reason)
            return frame
        self._file_units[file_path] = source.units()
        self._file_column_names[file_path] = tuple(source.columns())
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
        if idx < 0:
            idx = self._default_x_index()
        self.x_axis_combo.setCurrentIndex(idx)
        self.x_axis_combo.blockSignals(False)
        update_combo_popup_width(self.x_axis_combo)
        if self.x_axis_combo.currentData() != current:
            self._sync_x_unit_from_file()
        debug_print(f"GraphPanelWidget._refresh_x_axis_options count={self.x_axis_combo.count()}")

    def _hide_combo_outlines(self) -> None:
        for combo in self.findChildren(QComboBox):
            hide_popup_focus_outline(combo)

    def _refresh_column_settings(self) -> None:
        debug_print("GraphPanelWidget._refresh_column_settings called")
        self._clear_layout(self.column_settings_layout)
        self._axis_radios.clear()
        self._legend_edits.clear()
        self._conversion_combos.clear()
        self._unit_combos.clear()
        self._color_combos.clear()
        for file_path, columns in self._columns_by_file.items():
            for column in columns:
                self.column_settings_layout.addWidget(self._build_column_setting(file_path, column))
        if not any(self._columns_by_file.values()):
            self.column_settings_layout.addWidget(QLabel("Select columns to configure traces."))
        self._hide_combo_outlines()
        debug_print("GraphPanelWidget._refresh_column_settings complete")

    @staticmethod
    def _build_unit_combo() -> QComboBox:
        combo = QComboBox()
        combo.setObjectName("graphCombo")
        combo.setFixedWidth(_UNIT_COMBO_WIDTH)
        GraphPanelWidget._rebuild_unit_combo(combo, _NO_UNIT, _NO_UNIT)
        combo.setToolTip(
            "Unit of the data in the file, pre-filled from its units row. Custom: write a formula instead."
        )
        return combo

    @staticmethod
    def _rebuild_unit_combo(combo: QComboBox, selected: str, native: str = "") -> None:
        """From lists the scale of the data's own unit by prefix, then Custom.

        Each entry keeps its unit as data, so the base unit's name never has to be shown. When the file gives
        no unit (`native`), `s`, `K` and `°C` follow so the user can say what the data is. The list belongs to
        the data, not to the selection: it does not change while the user picks from it.
        """
        no_unit = not units.display_unit(native)
        combo.blockSignals(True)
        combo.clear()
        for unit in units.family_units(_NO_UNIT if no_unit else native):  # the data's own scale, whatever is selected
            combo.addItem(units.scale_label(unit), unit)
        if no_unit:
            for base in units.declarable_units():
                combo.addItem(base, base)
        combo.addItem(_CUSTOM, _CUSTOM)
        index = combo.findData(selected)
        combo.setCurrentIndex(index if index >= 0 else 0)
        update_combo_popup_width(combo)
        combo.blockSignals(False)

    @staticmethod
    def _show_unit(combo: QComboBox, unit: str, native: str = "") -> None:
        """Show a unit in a From dropdown, with its whole scale listed (also for a unit like "TPa" or "mol")."""
        GraphPanelWidget._rebuild_unit_combo(combo, unit or _NO_UNIT, native)

    @staticmethod
    def _unit_of(combo: QComboBox) -> str:
        """The unit (or "Custom") behind the selected entry of a From dropdown."""
        return combo.currentData() or _NO_UNIT

    @staticmethod
    def _fill_conversion_combo(combo: QComboBox, source_unit: str, current: str) -> str:
        """Rebuild the "To" entries for a source unit; returns the conversion now selected."""
        combo.blockSignals(True)
        combo.clear()
        for label, value in conversion_options(source_unit):
            combo.addItem(label, value)
        index = combo.findData(units.normalize_conversion(current))
        if index < 0:
            index = max(0, combo.findData("as-is"))  # no change: the source unit itself
        combo.setCurrentIndex(index)
        update_combo_popup_width(combo)
        combo.blockSignals(False)
        return combo.currentData() or "as-is"

    def _on_x_column_changed(self, _index: int = 0) -> None:
        self._sync_x_unit_from_file()

    def _on_x_unit_changed(self, _index: int = 0) -> None:
        if self._unit_of(self.x_axis_unit_combo) == _CUSTOM:
            return  # handled when activated: the formula dialog decides
        unit = units.normalize_unit(self._unit_of(self.x_axis_unit_combo)) or _NO_UNIT
        self._fill_conversion_combo(
            self.x_axis_conversion_combo, unit, self.x_axis_conversion_combo.currentData() or "as-is"
        )
        self._refresh_graph()

    def _on_x_unit_activated(self, _index: int = 0) -> None:
        if self._unit_of(self.x_axis_unit_combo) != _CUSTOM:
            return
        column = self.x_axis_combo.currentData()
        answer = self._ask_formula(self._files[0], column, self._x_formula, self._x_custom_unit) if (
            column and self._files
        ) else None
        if answer is None:
            if self.x_axis_conversion_combo.currentData() != "custom":
                self._show_unit(self.x_axis_unit_combo, self._x_previous_unit(), self._x_native_unit())
            return
        self._x_formula, self._x_custom_unit = answer
        self._show_custom(self.x_axis_unit_combo, self.x_axis_conversion_combo, self._x_custom_unit)
        self._refresh_graph()

    def _x_native_unit(self) -> str:
        """The unit the file gives for the X column ("" when it gives none)."""
        column = self.x_axis_combo.currentData()
        return units.normalize_unit(self._file_unit(self._files[0], column)) if (column and self._files) else ""

    def _x_previous_unit(self) -> str:
        column = self.x_axis_combo.currentData()
        file_unit = self._file_unit(self._files[0], column) if (column and self._files) else ""
        return units.normalize_unit(file_unit)

    def _sync_x_unit_from_file(self) -> None:
        """Default the X unit to the file's units row for the chosen X column."""
        column = self.x_axis_combo.currentData()
        file_unit = self._file_unit(self._files[0], column) if (column and self._files) else ""
        self.x_axis_unit_combo.blockSignals(True)
        self._show_unit(self.x_axis_unit_combo, units.normalize_unit(file_unit), units.normalize_unit(file_unit))
        self.x_axis_unit_combo.blockSignals(False)
        self._on_x_unit_changed()

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
        layout.addWidget(QLabel("Convert from / to:"), 1, 2)
        layout.addWidget(QLabel("Y-axis:"), 1, 3)

        legend = QLineEdit(settings.get("legend", column))
        legend.setObjectName("graphLineEdit")
        legend.setFixedWidth(145)
        legend.setFixedHeight(30)
        legend.editingFinished.connect(lambda f=file_path, c=column, edit=legend: self._set_legend(f, c, edit.text()))
        self._legend_edits[(file_path, column)] = legend
        attach_symbol_picker(legend)
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

        conversion_widget = QWidget()
        conversion_layout = QHBoxLayout(conversion_widget)
        conversion_layout.setContentsMargins(0, 0, 0, 0)
        conversion_layout.setSpacing(6)
        unit_combo = self._build_unit_combo()
        unit_combo.setFixedHeight(30)
        self._show_unit(unit_combo, settings.get("source_unit", ""), self._file_unit(file_path, column))
        conversion_combo = QComboBox()
        conversion_combo.setObjectName("graphCombo")
        conversion_combo.setFixedWidth(_UNIT_COMBO_WIDTH)
        conversion_combo.setFixedHeight(30)
        settings["conversion"] = self._fill_conversion_combo(
            conversion_combo, settings.get("source_unit", ""), settings.get("conversion", "as-is")
        ) if settings.get("conversion") != "custom" else "custom"
        conversion_combo.currentIndexChanged.connect(
            lambda _index, f=file_path, c=column, combo=conversion_combo: self._set_conversion(f, c, combo.currentData())
        )
        unit_combo.currentIndexChanged.connect(
            lambda _index, f=file_path, c=column, combo=unit_combo: self._set_source_unit(f, c, self._unit_of(combo))
        )
        unit_combo.activated.connect(lambda _index, f=file_path, c=column: self._on_unit_activated(f, c))
        if settings.get("conversion") == "custom":
            self._show_custom(unit_combo, conversion_combo, settings.get("custom_unit", ""))
        self._conversion_combos[(file_path, column)] = conversion_combo
        self._unit_combos[(file_path, column)] = unit_combo
        conversion_layout.addWidget(unit_combo)
        conversion_layout.addWidget(QLabel("to"))
        conversion_layout.addWidget(conversion_combo)
        layout.addWidget(conversion_widget, 2, 2)

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

    def _set_source_unit(self, file_path: str, column: str, text: str) -> None:
        debug_print(f"GraphPanelWidget._set_source_unit file={file_path} column={column} unit={text}")
        if text == _CUSTOM:
            return  # handled when activated: the formula dialog decides
        settings = self._ensure_column_setting(file_path, column)
        settings["source_unit"] = units.normalize_unit(text) or _NO_UNIT
        combo = self._conversion_combos.get((file_path, column))
        if combo is not None:
            settings["conversion"] = self._fill_conversion_combo(
                combo, settings["source_unit"], settings.get("conversion", "as-is")
            )
        self._refresh_graph()

    def _on_unit_activated(self, file_path: str, column: str) -> None:
        combo = self._unit_combos.get((file_path, column))
        if combo is None or self._unit_of(combo) != _CUSTOM:
            return
        settings = self._ensure_column_setting(file_path, column)
        answer = self._ask_formula(file_path, column, settings.get("formula", ""), settings.get("custom_unit", ""))
        if answer is None:
            if settings.get("conversion") != "custom":
                self._show_unit(combo, settings.get("source_unit", ""), self._file_unit(file_path, column))
            return
        settings["formula"], settings["custom_unit"] = answer
        settings["conversion"] = "custom"
        self._show_custom(combo, self._conversion_combos[(file_path, column)], answer[1])
        self._refresh_graph()

    def _show_custom(self, unit_combo: QComboBox, conversion_combo: QComboBox, label: str) -> None:
        """Show a formula conversion: the From dropdown reads Custom, the To dropdown the result's unit label."""
        unit_combo.blockSignals(True)
        unit_combo.setCurrentIndex(max(0, unit_combo.findData(_CUSTOM)))
        unit_combo.blockSignals(False)
        conversion_combo.blockSignals(True)
        conversion_combo.clear()
        conversion_combo.addItem(label or _NO_UNIT, "custom")
        conversion_combo.setCurrentIndex(0)
        conversion_combo.blockSignals(False)

    def _ask_formula(self, file_path: str, column: str, formula: str, unit: str) -> tuple[str, str] | None:
        """Open the formula dialog for one column; returns (formula, unit label), or None when cancelled."""
        source = GenericTextDataSource(file_path)
        data = source.dataframe_dict() if source.load() else {}
        if column not in data:
            return None
        dialog = FormulaDialog(
            self,
            current_column=column,
            column_data=data,
            formula=formula,
            unit=unit,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.formula(), dialog.unit()
        return None

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
        settings.setdefault("source_unit", units.normalize_unit(self._file_unit(file_path, column)) or _NO_UNIT)
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

    def _default_x_index(self) -> int:
        """A time-like column when the file has one (TimeStep, the first column, is rarely what you plot against)."""
        for index in range(self.x_axis_combo.count()):
            if str(self.x_axis_combo.itemData(index)).strip().lower() in _TIME_LIKE_COLUMNS:
                return index
        return 0

    def _file_unit(self, file_path: str, column: str) -> str:
        return self._file_units.get(file_path, {}).get(column, "")

    @staticmethod
    def _axis_title(base: str, unit_list: list[str]) -> str:
        shared = unit_list[0] if unit_list and all(unit == unit_list[0] for unit in unit_list) else ""
        shared = units.display_unit(shared)  # data with no unit shows none, whatever its prefix
        return f"{base} ({shared})" if shared else base

    def _auto_x_title(self) -> str:
        column = self.x_axis_combo.currentData()
        if not column:
            return _DEFAULT_TITLES["x"]
        names = self._file_column_names.get(self._files[0], ()) if self._files else ()
        transform = self.canvas.x_transform(self.state(), names)
        fallback = self._file_unit(self._files[0], column) if (self._files and transform.kind != "formula") else ""
        return self._axis_title(str(column), [transform.unit or fallback])

    def _auto_y_title(self, axis: str) -> str:
        names: list[str] = []
        shown_units: list[str] = []
        for file_path, columns in self._columns_by_file.items():
            for column in columns:
                settings = self._column_settings.get(file_path, {}).get(column, {})
                if settings.get("yaxis", "y1") != axis:
                    continue
                transform = self.canvas.column_transform(settings, self._file_column_names.get(file_path, ()))
                custom = settings.get("conversion") == "custom"
                unit = transform.unit or ("" if custom else self._file_unit(file_path, column))
                shown_units.append(unit)
                if column not in names:
                    names.append(column)
        if not names:
            return _DEFAULT_TITLES[axis]
        base = ", ".join(names[:_MAX_LISTED_COLUMNS]) + (", …" if len(names) > _MAX_LISTED_COLUMNS else "")
        return self._axis_title(base, shown_units)

    def _refresh_auto_titles(self) -> None:
        """Axis titles follow the X column, the plotted columns and their units, unless you typed a title.

        A title that differs from what this method last wrote was typed by the user and is left alone;
        clearing it hands it back to automatic.
        """
        edits = {"x": self.x_title_edit, "y1": self.y1_title_edit, "y2": self.y2_title_edit}
        for key, edit in edits.items():
            text = edit.text()
            if not text.strip():
                self._title_user_set[key] = False
            elif text != self._auto_titles[key]:
                self._title_user_set[key] = True
            if self._title_user_set[key]:
                continue
            title = self._auto_x_title() if key == "x" else self._auto_y_title(key)
            self._auto_titles[key] = title
            if text != title:
                edit.setText(title)

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
        self._refresh_auto_titles()
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
