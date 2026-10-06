"""One-file, multi-property heatmap panel."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtCore import QEvent, QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QBoxLayout,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QStyleOptionViewItem,
    QStyledItemDelegate,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.debug import debug_print
from app.resources import HEATMAP_LOGO_PATH
from config.constants import DEFAULTS, PALETTES
from multi_property.export_renderer import save_multi_property_png
from multi_property.multi_property_cell import MultiPropertyCell, ScientificRangeSpinBox, _MIN_CELL_W, _RANGE_SPIN_W
from multi_view.multi_view_cell import _CELL_W
from multi_view.multi_view_panel import MultiViewPanel, _LOGO_W
from utils.combo_box_utils import update_combo_popup_width
from utils.vtk_utils import get_reader
from viewer.colorscale import (
    DISCRETE_CUSTOM_PALETTE,
    discrete_palette_colors,
    make_discrete_colormap,
    palette_to_cmap,
)
from viewer.histogram_canvas import HistogramCanvas
from viewer.heatmap_canvas import _CANVAS_HEIGHT
from viewer.heatmap_orientation import Heatmap2DOrientation
from viewer.line_scan_canvas import LineScanCanvas
from viewer.range_slider_widget import RangeSliderWidget
from viewer.toggle_switch_widget import ToggleSwitchWidget

_ASSETS = Path(__file__).resolve().parent.parent / "assets"
_MAX_PROPERTIES = 10
_CELL_GAP = 8
_ROW_GAP = 8
_TOP_RANGE_SPIN_W = 160
_DEFAULT_ANALYSIS_AVAILABLE_W = 760
_LINE_ANALYSIS_CANVAS_W = 800
_HISTOGRAM_ANALYSIS_CANVAS_W = 800
_ANALYSIS_TOOLBAR_H = 40
_STACKED_ANALYSIS_BREAKPOINT = 680


def _freq_debug(message: str) -> None:
    text = f"MP-FREQ {message}"
    print(text)
    debug_print(text)


class _PropertyCheckDelegate(QStyledItemDelegate):
    """Draw a clear checkbox and bold tick for Multi Property selection."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("multiPropertyCheckDelegate")
        self.box_size = 14
        self.box_border_width = 2
        self.box_left_padding = 8
        self.text_gap_after_box = 12
        self.tick_weight = 900
        self.paint_checkable_rows_without_super = True
        debug_print(f"MultiPropertyPanel property check box left padding={self.box_left_padding}")
        debug_print(f"MultiPropertyPanel property check text gap={self.text_gap_after_box}")
        debug_print("MultiPropertyPanel property check delegate created")

    def text_left_offset(self) -> int:
        debug_print("MultiPropertyPanel property check delegate text_left_offset called")
        offset = self.box_left_padding + self.box_size + self.text_gap_after_box
        debug_print(f"MultiPropertyPanel property check text offset={offset}")
        return offset

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        debug_print("MultiPropertyPanel property check delegate paint called")
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        check_state = index.data(Qt.ItemDataRole.CheckStateRole)
        debug_print(f"MultiPropertyPanel property check delegate state={check_state}")
        has_checkbox = check_state is not None
        if has_checkbox:
            stripped = self._text_option_without_default_check(check_state, opt.features)
            opt.features = stripped.features
            opt.checkState = stripped.checkState
            opt.rect = opt.rect.adjusted(self.text_left_offset(), 0, 0, 0)
            debug_print("MultiPropertyPanel property check delegate text shifted")
        if not has_checkbox:
            super().paint(painter, opt, index)
            debug_print("MultiPropertyPanel property check delegate skipped placeholder")
            return
        self._paint_checkable_background(painter, option)
        debug_print("MultiPropertyPanel property check delegate manual background drawn")
        self._paint_checkable_text(painter, opt)
        debug_print("MultiPropertyPanel property check delegate manual text drawn")
        square = QRect(
            option.rect.left() + self.box_left_padding,
            option.rect.top() + max(0, (option.rect.height() - self.box_size) // 2),
            self.box_size,
            self.box_size,
        )
        debug_print(f"MultiPropertyPanel property check delegate box={square}")
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(QColor("#102a52"), self.box_border_width))
        painter.setBrush(QColor("#ffffff"))
        painter.drawRect(square)
        debug_print("MultiPropertyPanel property check delegate box drawn")
        if check_state == Qt.CheckState.Checked:
            font = painter.font()
            font.setBold(True)
            font.setWeight(QFont.Weight.Black)
            painter.setFont(font)
            painter.setPen(QColor("#102a52"))
            painter.drawText(square.adjusted(-1, -3, 2, 2), Qt.AlignmentFlag.AlignCenter, "✓")
            debug_print("MultiPropertyPanel property check delegate bold tick drawn")
        painter.restore()
        debug_print("MultiPropertyPanel property check delegate paint complete")

    def _text_option_without_default_check(self, check_state: Qt.CheckState, features=None) -> QStyleOptionViewItem:
        debug_print("MultiPropertyPanel property check delegate stripping default check")
        option = QStyleOptionViewItem()
        if features is not None:
            option.features = features
            debug_print(f"MultiPropertyPanel stripped input features={features}")
        option.features &= ~QStyleOptionViewItem.ViewItemFeature.HasCheckIndicator
        option.checkState = Qt.CheckState.Unchecked
        debug_print(f"MultiPropertyPanel stripped original state={check_state}")
        debug_print(f"MultiPropertyPanel stripped features={option.features}")
        return option

    def _paint_checkable_background(self, painter: QPainter, option: QStyleOptionViewItem) -> None:
        debug_print("MultiPropertyPanel property check delegate paint background called")
        painter.save()
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor("#eef4ff"))
            debug_print("MultiPropertyPanel property check delegate selected background")
        else:
            painter.fillRect(option.rect, QColor("#ffffff"))
            debug_print("MultiPropertyPanel property check delegate white background")
        painter.restore()

    def _paint_checkable_text(self, painter: QPainter, option: QStyleOptionViewItem) -> None:
        debug_print("MultiPropertyPanel property check delegate paint text called")
        painter.save()
        painter.setPen(QColor("#102a52"))
        painter.drawText(
            option.rect.adjusted(0, 0, -6, 0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            option.text,
        )
        painter.restore()


class MultiPropertyPanel(QWidget):
    """Display several scalar properties for one selected VTK file."""

    def __init__(self, dataset_info: dict, parent=None) -> None:
        super().__init__(parent)
        debug_print("MultiPropertyPanel.__init__ start")
        self._dataset_info = dataset_info
        self._available_projects = dataset_info.get("available_projects", [])
        self._scalar_defs = MultiViewPanel._build_scalar_defs(dataset_info)
        self._selected_keys: list[str] = []
        self._cells: dict[str, MultiPropertyCell] = {}
        self._ranges: dict[str, dict[str, float]] = {}
        self._property_labels: dict[str, str] = {}
        self._grid_cache: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
        self._click_count = 0
        self._first_click_value: float | None = None
        self._row_widgets: list[QWidget] = []
        self._row_layouts: list[QHBoxLayout] = []
        self._available_width: int | None = None
        self._active_key: str | None = None
        self._rotation_degrees: int = 0
        self._selected_rotation_degrees: int = 0
        self._line_scan_y: float | None = None
        self._line_scan_x: float | None = None
        self._line_scan_direction = "horizontal"
        self._build_ui()
        self._connect_signals()
        self._populate_project_combo()
        debug_print(f"MultiPropertyPanel scalar_defs count={len(self._scalar_defs)}")
        debug_print("MultiPropertyPanel.__init__ complete")

    def _build_ui(self) -> None:
        debug_print("MultiPropertyPanel._build_ui called")
        self.setStyleSheet(
            "QPushButton#multiPropertyTopRangeReset {"
            "  background: #ffffff;"
            "  border: 1px solid #c7d2e2;"
            "  border-radius: 4px;"
            "  color: #102a52;"
            "  padding: 0px;"
            "}"
            "QPushButton#multiPropertyTopRangeReset:hover {"
            "  background: #eef4ff;"
            "  border-color: #8FAE00;"
            "}"
            "QPushButton#multiPropertyTopRangeReset:disabled {"
            "  background: #ffffff;"
            "  border-color: #c7d2e2;"
            "  color: #102a52;"
            "}"
            "QPushButton#multiPropertyTopRangeResetAll {"
            "  background: #ffffff;"
            "  border: 1px solid #c7d2e2;"
            "  border-radius: 4px;"
            "  color: #102a52;"
            "  font-size: 12px;"
            "  font-weight: 700;"
            "  padding: 0px 8px;"
            "}"
            "QPushButton#multiPropertyTopRangeResetAll:hover {"
            "  background: #eef4ff;"
            "  border-color: #8FAE00;"
            "}"
            "QPushButton#multiPropertyTopRangeResetAll:disabled {"
            "  background: #ffffff;"
            "  border-color: #c7d2e2;"
            "  color: #102a52;"
            "}"
        )
        debug_print("MultiPropertyPanel stylesheet applied")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 8, 8)
        root.setSpacing(8)
        controls_card = QWidget()
        controls_card.setObjectName("controlsCard")
        controls_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        controls = QVBoxLayout(controls_card)
        controls.setContentsMargins(14, 8, 14, 8)
        controls.setSpacing(6)
        selection_row = QWidget()
        selection_layout = QHBoxLayout(selection_row)
        selection_layout.setContentsMargins(0, 0, 0, 0)
        selection_layout.setSpacing(8)
        range_row = QWidget()
        range_layout = QHBoxLayout(range_row)
        range_layout.setContentsMargins(0, 0, 0, 0)
        range_layout.setSpacing(8)
        self.project_combo = QComboBox()
        self.project_combo.setObjectName("viewerCombo")
        self.file_combo = QComboBox()
        self.file_combo.setObjectName("viewerCombo")
        self.property_combo = QComboBox()
        self.property_combo.setObjectName("viewerCombo")
        self.property_combo.setItemDelegate(_PropertyCheckDelegate(self.property_combo))
        debug_print("MultiPropertyPanel property combo check delegate installed")
        self.property_combo.view().viewport().installEventFilter(self)
        debug_print("MultiPropertyPanel property combo event filter installed")
        self.type_combo = QComboBox()
        self.type_combo.setObjectName("viewerCombo")
        self.type_combo.addItem("Heatmap", "heatmap")
        self.type_combo.addItem("Contour Lines", "contour_lines")
        self.type_combo.addItem("Contour Filled", "contour_filled")
        debug_print("MultiPropertyPanel plot type added=contour_filled")
        self.type_combo.addItem("Contour Filled + Values", "contour_filled_values")
        debug_print("MultiPropertyPanel plot type added=contour_filled_values")
        self.type_combo.addItem("Heatmap+Contour", "heatmap_contour")
        debug_print("MultiPropertyPanel plot type added=heatmap_contour")
        self.palette_combo = QComboBox()
        self.palette_combo.setObjectName("viewerCombo")
        for key in PALETTES:
            self.palette_combo.addItem(key.replace("-", " ").title(), key)
        update_combo_popup_width(self.type_combo)
        self.discrete_band_count = 2
        self.discrete_minus_button = QPushButton("-")
        self.discrete_minus_button.setObjectName("discreteBandButton")
        self.discrete_minus_button.setFixedSize(28, 28)
        self.discrete_minus_button.setToolTip("Remove a discrete color band")
        self.discrete_band_label = QLabel(str(self.discrete_band_count))
        self.discrete_band_label.setObjectName("mutedInfo")
        self.discrete_band_label.setFixedWidth(18)
        self.discrete_band_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.discrete_plus_button = QPushButton("+")
        self.discrete_plus_button.setObjectName("discreteBandButton")
        self.discrete_plus_button.setFixedSize(28, 28)
        self.discrete_plus_button.setToolTip("Add a discrete color band")
        debug_print(f"MultiPropertyPanel discrete bands initial={self.discrete_band_count}")
        self.interfaces_on = ToggleSwitchWidget("Interfaces Overlay", checked=False)
        debug_print("MultiPropertyPanel interfaces overlay toggle created")
        self.add_all_properties_button = QPushButton("Add All")
        self.add_all_properties_button.setProperty("subtle", True)
        self.add_all_properties_button.setToolTip("Add all properties as heatmaps")
        debug_print("MultiPropertyPanel add all properties button created")
        self.clear_button = QPushButton("Clear")
        self.clear_button.setProperty("subtle", True)
        self.export_button = QPushButton("Export PNG")
        self.export_button.setProperty("subtle", True)
        debug_print("MultiPropertyPanel export button created")
        self.status_label = QLabel("")
        self.status_label.setObjectName("mutedInfo")
        self.range_min = self._make_range_spin("min")
        self.range_max = self._make_range_spin("max")
        self.range_slider = RangeSliderWidget()
        self.range_slider.setMinimumWidth(240)
        self.unit_scale_combo = QComboBox()
        self.unit_scale_combo.setObjectName("viewerCombo")
        self.unit_scale_combo.addItem("Raw", (1.0, ""))
        self.unit_scale_combo.addItem("% x100", (100.0, "%"))
        self.unit_scale_combo.addItem("MPa /1e6", (1e-6, "MPa"))
        self.unit_scale_combo.addItem("GPa /1e9", (1e-9, "GPa"))
        update_combo_popup_width(self.unit_scale_combo)
        debug_print("MultiPropertyPanel unit scale combo created")
        debug_print(f"MultiPropertyPanel unit scale count={self.unit_scale_combo.count()}")
        self.reset_button = QPushButton()
        self.reset_button.setObjectName("multiPropertyTopRangeReset")
        self.reset_button.setFlat(False)
        self.reset_button.setFixedSize(32, 28)
        self.reset_button.setIcon(QIcon(str(_ASSETS / "refresh.png")))
        self.reset_button.setIconSize(QSize(16, 16))
        self.reset_button.setToolTip("Reset selected property range")
        debug_print(f"MultiPropertyPanel reset button icon null={self.reset_button.icon().isNull()}")
        debug_print(f"MultiPropertyPanel reset button text={self.reset_button.text()}")
        debug_print(f"MultiPropertyPanel reset button size={self.reset_button.size()}")
        self.reset_all_button = QPushButton("Reset All")
        self.reset_all_button.setObjectName("multiPropertyTopRangeResetAll")
        self.reset_all_button.setFlat(False)
        self.reset_all_button.setFixedSize(78, 28)
        self.reset_all_button.setToolTip("Reset all property ranges")
        debug_print(f"MultiPropertyPanel reset all button icon null={self.reset_all_button.icon().isNull()}")
        debug_print(f"MultiPropertyPanel reset all button text={self.reset_all_button.text()}")
        debug_print(f"MultiPropertyPanel reset all button size={self.reset_all_button.size()}")
        debug_print("MultiPropertyPanel top range controls created")
        self.rotation_button_row = QWidget()
        self.rotation_button_row.setObjectName("rotationButtonRow")
        rotation_button_layout = QHBoxLayout(self.rotation_button_row)
        rotation_button_layout.setContentsMargins(0, 0, 0, 0)
        rotation_button_layout.setSpacing(2)
        debug_print("MultiPropertyPanel rotation button row created")
        self.rotation_buttons: dict[int, QPushButton] = {}
        for degrees, icon_name in (
            (0, "coordinate_00.png"),
            (90, "coordinate_90.png"),
            (180, "coordinate_180.png"),
            (270, "coordinate_270.png"),
        ):
            button = self._make_rotation_button(degrees, icon_name)
            self.rotation_buttons[degrees] = button
            rotation_button_layout.addWidget(button)
            debug_print(f"MultiPropertyPanel rotation button added degrees={degrees}")
        self._sync_rotation_buttons()
        debug_print("MultiPropertyPanel rotation buttons initialized")
        selection_layout.addWidget(self.project_combo, 2)
        selection_layout.addWidget(self.file_combo, 3)
        selection_layout.addWidget(self.property_combo, 2)
        selection_layout.addWidget(self.type_combo, 2)
        selection_layout.addWidget(self.palette_combo, 2)
        selection_layout.addWidget(self.discrete_minus_button)
        selection_layout.addWidget(self.discrete_band_label)
        selection_layout.addWidget(self.discrete_plus_button)
        debug_print("MultiPropertyPanel discrete controls added")
        self._sync_discrete_controls()
        selection_layout.addWidget(self.interfaces_on)
        debug_print("MultiPropertyPanel interfaces overlay toggle added")
        selection_layout.addWidget(self.add_all_properties_button)
        debug_print("MultiPropertyPanel add all properties button added")
        selection_layout.addWidget(self.clear_button)
        selection_layout.addWidget(self.export_button)
        debug_print("MultiPropertyPanel export button added")
        selection_layout.addWidget(self.status_label, 2)
        range_layout.addWidget(QLabel("Range"))
        range_layout.addWidget(self.range_min)
        range_layout.addWidget(self.range_max)
        range_layout.addWidget(self.range_slider, 1)
        range_layout.addWidget(self.reset_button)
        range_layout.addWidget(self.reset_all_button)
        range_layout.addWidget(self.unit_scale_combo)
        range_layout.addWidget(self.rotation_button_row)
        debug_print("MultiPropertyPanel top range row added")
        controls.addWidget(selection_row)
        controls.addWidget(range_row)
        root.addWidget(controls_card)
        self.scroll = QScrollArea()
        self.scroll.setObjectName("appContentScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        debug_print("MultiPropertyPanel scroll alignment set left/top")
        self.scroll.setStyleSheet("QScrollArea#appContentScroll, QScrollArea#appContentScroll > QWidget { background: #ffffff; }")
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("multiPropertyScrollContent")
        self.scroll_content.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.scroll_content.setStyleSheet("QWidget#multiPropertyScrollContent { background: #ffffff; }")
        debug_print("MultiPropertyPanel shared scroll content created")
        scroll_content_layout = QVBoxLayout(self.scroll_content)
        scroll_content_layout.setContentsMargins(0, 0, 0, 0)
        scroll_content_layout.setSpacing(8)
        scroll_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        debug_print("MultiPropertyPanel shared scroll layout configured")
        self.rows_widget = QWidget()
        self.rows_widget.setObjectName("multiPropertyRows")
        self.rows_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.rows_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        debug_print("MultiPropertyPanel rows widget size policy fixed")
        self.rows_widget.setStyleSheet("QWidget#multiPropertyRows { background: #ffffff; }")
        self.rows_layout = QVBoxLayout(self.rows_widget)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(_ROW_GAP)
        self.rows_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.rows_layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        scroll_content_layout.addWidget(self.rows_widget)
        debug_print("MultiPropertyPanel rows widget added to shared scroll")
        debug_print(f"MultiPropertyPanel row spacing={_ROW_GAP}")
        debug_print(f"MultiPropertyPanel column spacing={_CELL_GAP}")
        self.analysis_card = self._build_analysis_area()
        scroll_content_layout.addWidget(self.analysis_card)
        debug_print("MultiPropertyPanel analysis area added to shared scroll")
        self._set_analysis_visible(False)
        debug_print("MultiPropertyPanel analysis area hidden initially")
        self.empty_label = QLabel("Add properties to view this file")
        self.empty_label.setObjectName("mutedInfo")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll_content_layout.addWidget(self.empty_label)
        debug_print("MultiPropertyPanel empty label added to shared scroll")
        self.scroll.setWidget(self.scroll_content)
        debug_print("MultiPropertyPanel shared scroll content installed")
        root.addWidget(self.scroll, 1)
        debug_print("MultiPropertyPanel one scroll area added to panel root")
        self._populate_property_combo()
        self._sync_top_range_controls()
        debug_print("MultiPropertyPanel UI built")

    def _build_analysis_area(self) -> QWidget:
        debug_print("MultiPropertyPanel._build_analysis_area called")
        card = QWidget()
        card.setObjectName("controlsCard")
        card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)
        debug_print("MultiPropertyPanel analysis tools use one horizontal layout")

        line_card = QWidget()
        line_card.setObjectName("innerCard")
        line_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        line_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        line_layout = QVBoxLayout(line_card)
        line_layout.setContentsMargins(12, 12, 12, 12)
        line_layout.setSpacing(10)
        line_toolbar = QWidget()
        line_toolbar.setObjectName("toolbarStrip")
        line_toolbar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        line_toolbar.setFixedHeight(_ANALYSIS_TOOLBAR_H)
        debug_print(f"MultiPropertyPanel line toolbar fixed height={_ANALYSIS_TOOLBAR_H}")
        line_toolbar_layout = QHBoxLayout(line_toolbar)
        line_toolbar_layout.setContentsMargins(0, 0, 0, 0)
        line_toolbar_layout.setSpacing(12)
        self.line_mode_check = ToggleSwitchWidget("Line Scan", checked=False)
        debug_print("MultiPropertyPanel line scan toggle created")
        self.show_line_check = ToggleSwitchWidget("Show Line", checked=True)
        debug_print("MultiPropertyPanel show line toggle created")
        self.line_direction_button_row = QWidget()
        self.line_direction_button_row.setObjectName("lineDirectionButtonRow")
        line_direction_layout = QHBoxLayout(self.line_direction_button_row)
        line_direction_layout.setContentsMargins(0, 0, 0, 0)
        line_direction_layout.setSpacing(2)
        debug_print("MultiPropertyPanel line direction button row created")
        self.line_direction_buttons: dict[str, QPushButton] = {}
        for direction, icon_name, tooltip in (
            ("horizontal", "Horizontal.png", "Horizontal line scan"),
            ("vertical", "Vertical.png", "Vertical line scan"),
        ):
            button = self._make_line_direction_button(direction, icon_name, tooltip)
            self.line_direction_buttons[direction] = button
            line_direction_layout.addWidget(button)
            debug_print(f"MultiPropertyPanel line direction button added direction={direction}")
        self._sync_line_direction_buttons()
        debug_print("MultiPropertyPanel line direction buttons initialized")
        direction_label = QLabel("Direction:")
        direction_label.setObjectName("mutedInfo")
        self.line_grid_check = ToggleSwitchWidget("Grid", checked=True)
        debug_print("MultiPropertyPanel line grid toggle created")
        value_label = QLabel("Value:")
        value_label.setObjectName("mutedInfo")
        self.analysis_value_label_edit = QLineEdit("Value")
        self.analysis_value_label_edit.setObjectName("viewerLineEdit")
        self.analysis_value_label_edit.setToolTip("Rename value label for line and frequency graphs")
        self.analysis_value_label_edit.setFixedWidth(150)
        self.analysis_value_label_edit.setFixedHeight(24)
        debug_print(f"MultiPropertyPanel analysis value label edit height={self.analysis_value_label_edit.height()}")
        debug_print("MultiPropertyPanel analysis value label edit created")
        debug_print(f"MultiPropertyPanel analysis value label default={self.analysis_value_label_edit.text()}")
        line_toolbar_layout.addWidget(self.line_mode_check)
        line_toolbar_layout.addWidget(self.show_line_check)
        line_toolbar_layout.addWidget(direction_label)
        line_toolbar_layout.addWidget(self.line_direction_button_row)
        line_toolbar_layout.addWidget(self.line_grid_check)
        line_toolbar_layout.addWidget(value_label)
        line_toolbar_layout.addWidget(self.analysis_value_label_edit)
        line_toolbar_layout.addStretch(1)
        self.line_scan_canvas = LineScanCanvas(max_width=_LINE_ANALYSIS_CANVAS_W)
        debug_print(f"MultiPropertyPanel line max width={_LINE_ANALYSIS_CANVAS_W}")
        debug_print(f"MultiPropertyPanel setting line graph height={_CANVAS_HEIGHT}")
        self.line_scan_canvas.set_canvas_height(_CANVAS_HEIGHT)
        debug_print(f"MultiPropertyPanel line graph height now={self.line_scan_canvas.height()}")
        line_layout.addWidget(line_toolbar)
        line_layout.addWidget(self.line_scan_canvas, 0, Qt.AlignmentFlag.AlignHCenter)

        histogram_card = QWidget()
        histogram_card.setObjectName("innerCard")
        histogram_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        histogram_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        histogram_layout = QVBoxLayout(histogram_card)
        histogram_layout.setContentsMargins(12, 12, 12, 12)
        histogram_layout.setSpacing(10)
        histogram_toolbar = QWidget()
        histogram_toolbar.setObjectName("toolbarStrip")
        histogram_toolbar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        histogram_toolbar.setFixedHeight(_ANALYSIS_TOOLBAR_H)
        debug_print(f"MultiPropertyPanel histogram toolbar fixed height={_ANALYSIS_TOOLBAR_H}")
        histogram_toolbar_layout = QHBoxLayout(histogram_toolbar)
        histogram_toolbar_layout.setContentsMargins(0, 0, 0, 0)
        histogram_toolbar_layout.setSpacing(12)
        histogram_toolbar_layout.addWidget(QLabel("Number of Bins"))
        self.histogram_bins_slider = QSlider(Qt.Orientation.Horizontal)
        self.histogram_bins_slider.setRange(10, 200)
        self.histogram_bins_slider.setValue(30)
        debug_print("MultiPropertyPanel histogram bins slider created")
        histogram_toolbar_layout.addWidget(self.histogram_bins_slider, 1)
        self.histogram_grid_check = ToggleSwitchWidget("Grid", checked=True)
        histogram_toolbar_layout.addWidget(self.histogram_grid_check)
        debug_print("MultiPropertyPanel histogram grid toggle created")
        self.histogram_canvas = HistogramCanvas(max_width=_HISTOGRAM_ANALYSIS_CANVAS_W)
        debug_print(f"MultiPropertyPanel setting histogram graph height={_CANVAS_HEIGHT}")
        self.histogram_canvas.set_canvas_height(_CANVAS_HEIGHT)
        debug_print(f"MultiPropertyPanel histogram graph height now={self.histogram_canvas.height()}")
        histogram_layout.addWidget(histogram_toolbar)
        histogram_layout.addWidget(self.histogram_canvas, 0, Qt.AlignmentFlag.AlignHCenter)

        default_line_width = self._analysis_canvas_width(_DEFAULT_ANALYSIS_AVAILABLE_W)
        default_histogram_width = self._histogram_canvas_width(_DEFAULT_ANALYSIS_AVAILABLE_W)
        debug_print(f"MultiPropertyPanel default line canvas width={default_line_width}")
        debug_print(f"MultiPropertyPanel default histogram canvas width={default_histogram_width}")
        _freq_debug(f"default_widths line={default_line_width} histogram={default_histogram_width}")
        self.line_scan_canvas.set_available_width(default_line_width)
        self.histogram_canvas.set_available_width(default_histogram_width)
        debug_print("MultiPropertyPanel default analysis canvas widths applied")

        layout.addWidget(line_card, 1)
        debug_print("MultiPropertyPanel line scan card added to analysis row")
        layout.addWidget(histogram_card, 1)
        debug_print("MultiPropertyPanel histogram card added to analysis row")
        debug_print("MultiPropertyPanel._build_analysis_area complete")
        return card

    def _make_range_spin(self, role: str) -> QDoubleSpinBox:
        debug_print("MultiPropertyPanel._make_range_spin called")
        spin = ScientificRangeSpinBox()
        spin.setObjectName("viewerSpin")
        spin.setDecimals(12)
        spin.setRange(-1e12, 1e12)
        spin.setKeyboardTracking(False)
        spin.setFixedWidth(max(_RANGE_SPIN_W, _TOP_RANGE_SPIN_W))
        spin.setToolTip(f"Selected property range {role}")
        debug_print(f"MultiPropertyPanel top range spin role={role}")
        debug_print(f"MultiPropertyPanel top range spin width={spin.width()}")
        debug_print("MultiPropertyPanel top range spin scientific display enabled")
        return spin

    def _make_rotation_button(self, degrees: int, icon_name: str) -> QPushButton:
        debug_print("MultiPropertyPanel._make_rotation_button called")
        button = QPushButton()
        button.setObjectName("rotationIconButton")
        button.setCheckable(True)
        button.setProperty("subtle", True)
        button.setFixedSize(32, 32)
        button.setIcon(QIcon(str(_ASSETS / icon_name)))
        button.setIconSize(QSize(24, 24))
        button.setToolTip(f"Rotate {degrees} degrees")
        debug_print(f"MultiPropertyPanel rotation button configured degrees={degrees}")
        debug_print(f"MultiPropertyPanel rotation icon null={button.icon().isNull()}")
        return button

    def _sync_rotation_buttons(self) -> None:
        debug_print("MultiPropertyPanel._sync_rotation_buttons called")
        for degrees, button in self.rotation_buttons.items():
            button.setChecked(degrees == self._selected_rotation_degrees)
            debug_print(f"MultiPropertyPanel rotation button checked degrees={degrees} checked={button.isChecked()}")

    def _make_line_direction_button(self, direction: str, icon_name: str, tooltip: str) -> QPushButton:
        debug_print("MultiPropertyPanel._make_line_direction_button called")
        button = QPushButton()
        button.setObjectName("lineScanDirectionButton")
        button.setCheckable(True)
        button.setProperty("subtle", True)
        button.setFixedSize(32, 32)
        button.setIcon(QIcon(str(_ASSETS / icon_name)))
        button.setIconSize(QSize(22, 22))
        button.setToolTip(tooltip)
        debug_print(f"MultiPropertyPanel line direction button configured direction={direction}")
        debug_print(f"MultiPropertyPanel line direction icon null={button.icon().isNull()}")
        return button

    def _sync_line_direction_buttons(self) -> None:
        debug_print("MultiPropertyPanel._sync_line_direction_buttons called")
        for direction, button in self.line_direction_buttons.items():
            button.setChecked(direction == self._line_scan_direction)
            debug_print(f"MultiPropertyPanel line direction checked direction={direction} checked={button.isChecked()}")

    def _set_line_scan_direction(self, direction: str) -> None:
        debug_print("MultiPropertyPanel._set_line_scan_direction called")
        self._line_scan_direction = direction
        debug_print(f"MultiPropertyPanel selected line direction={self._line_scan_direction}")
        self._sync_line_direction_buttons()
        self._on_analysis_control_changed()
        debug_print("MultiPropertyPanel._set_line_scan_direction complete")

    def _current_line_scan_direction(self) -> str:
        debug_print("MultiPropertyPanel._current_line_scan_direction called")
        direction = getattr(self, "_line_scan_direction", "horizontal")
        debug_print(f"MultiPropertyPanel current line direction={direction}")
        return direction or "horizontal"

    @staticmethod
    def _clockwise_to_orientation_degrees(degrees: int) -> int:
        debug_print("MultiPropertyPanel._clockwise_to_orientation_degrees called")
        mapped_degrees = (-int(degrees)) % 360
        debug_print(f"MultiPropertyPanel clockwise degrees={degrees}")
        debug_print(f"MultiPropertyPanel orientation degrees={mapped_degrees}")
        return mapped_degrees

    def _connect_signals(self) -> None:
        debug_print("MultiPropertyPanel._connect_signals called")
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        self.file_combo.currentIndexChanged.connect(self._render_all)
        self.property_combo.activated.connect(self._on_property_combo_activated)
        self.add_all_properties_button.clicked.connect(self._add_all_properties)
        debug_print("MultiPropertyPanel add all properties button connected")
        self.clear_button.clicked.connect(self._clear_properties)
        self.export_button.clicked.connect(self._export_png)
        self.type_combo.currentIndexChanged.connect(self._render_all)
        debug_print("MultiPropertyPanel plot type combo connected")
        self.palette_combo.currentIndexChanged.connect(self._on_palette_changed)
        self.discrete_minus_button.clicked.connect(lambda *_: self._change_discrete_band_count(-1))
        self.discrete_plus_button.clicked.connect(lambda *_: self._change_discrete_band_count(1))
        debug_print("MultiPropertyPanel discrete band controls connected")
        self.interfaces_on.toggled.connect(self._render_all)
        self.range_min.valueChanged.connect(self._on_active_range_spin_changed)
        self.range_max.valueChanged.connect(self._on_active_range_spin_changed)
        self.range_slider.values_changed.connect(self._on_active_slider_range_changed)
        self.reset_button.clicked.connect(self._reset_active_range)
        self.reset_all_button.clicked.connect(self._reset_all_ranges)
        debug_print("MultiPropertyPanel reset all button connected")
        self.unit_scale_combo.currentIndexChanged.connect(self._on_unit_scale_changed)
        debug_print("MultiPropertyPanel unit scale combo connected")
        self.line_mode_check.toggled.connect(self._on_line_mode_toggled)
        debug_print("MultiPropertyPanel line mode toggle connected")
        self.show_line_check.toggled.connect(self._render_all)
        debug_print("MultiPropertyPanel show line toggle connected")
        self.line_grid_check.toggled.connect(self._on_analysis_control_changed)
        self.analysis_value_label_edit.editingFinished.connect(self._on_analysis_control_changed)
        debug_print("MultiPropertyPanel analysis value label edit connected")
        debug_print("MultiPropertyPanel line grid toggle connected")
        for direction, button in self.line_direction_buttons.items():
            button.clicked.connect(lambda _checked=False, value=direction: self._set_line_scan_direction(value))
            debug_print(f"MultiPropertyPanel line direction button connected direction={direction}")
        self.histogram_bins_slider.valueChanged.connect(self._on_analysis_control_changed)
        debug_print("MultiPropertyPanel histogram bins slider connected")
        self.histogram_grid_check.toggled.connect(self._on_analysis_control_changed)
        debug_print("MultiPropertyPanel histogram grid toggle connected")
        for degrees, button in self.rotation_buttons.items():
            button.clicked.connect(lambda _checked=False, value=degrees: self._on_rotation_changed(value))
            debug_print(f"MultiPropertyPanel rotation button connected degrees={degrees}")
        debug_print("MultiPropertyPanel signals connected")

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if watched is self.property_combo.view().viewport() and event.type() == QEvent.Type.MouseButtonRelease:
            debug_print("MultiPropertyPanel property combo popup click")
            index = self.property_combo.view().indexAt(event.position().toPoint())
            debug_print(f"MultiPropertyPanel property combo popup row={index.row()}")
            if not index.isValid():
                debug_print("MultiPropertyPanel property combo popup invalid row")
                return super().eventFilter(watched, event)
            self._toggle_property_combo_index(index.row(), keep_popup=True)
            debug_print("MultiPropertyPanel property combo popup click handled")
            return True
        return super().eventFilter(watched, event)

    def set_available_width(self, width: int) -> None:
        debug_print("MultiPropertyPanel.set_available_width called")
        self._available_width = max(0, int(width))
        self.setMaximumWidth(self._available_width)
        self.scroll.setMaximumWidth(self._available_width)
        self.scroll_content.setMaximumWidth(self._available_width)
        self.analysis_card.setMaximumWidth(self._available_width)
        self._sync_analysis_layout_for_width(self._available_width)
        line_canvas_width = self._analysis_canvas_width(self._available_width)
        histogram_canvas_width = self._histogram_canvas_width(self._available_width)
        debug_print(f"MultiPropertyPanel line canvas width={line_canvas_width}")
        debug_print(f"MultiPropertyPanel histogram canvas width={histogram_canvas_width}")
        _freq_debug(f"set_available_width line={line_canvas_width} histogram={histogram_canvas_width}")
        self.line_scan_canvas.set_available_width(line_canvas_width)
        self.histogram_canvas.set_available_width(histogram_canvas_width)
        debug_print(f"MultiPropertyPanel available width={self._available_width}")
        debug_print("MultiPropertyPanel shared scroll content width capped")

    def _sync_analysis_layout_for_width(self, available_width: int) -> None:
        debug_print("MultiPropertyPanel._sync_analysis_layout_for_width called")
        safe_width = max(0, int(available_width))
        debug_print(f"MultiPropertyPanel sync analysis width={safe_width}")
        layout = self.analysis_card.layout()
        if not isinstance(layout, QBoxLayout):
            debug_print("MultiPropertyPanel analysis layout direction skipped")
            return
        if safe_width and safe_width < _STACKED_ANALYSIS_BREAKPOINT:
            layout.setDirection(QBoxLayout.Direction.TopToBottom)
            debug_print("MultiPropertyPanel analysis layout stacked vertically")
        else:
            layout.setDirection(QBoxLayout.Direction.LeftToRight)
            debug_print("MultiPropertyPanel analysis layout side-by-side")

    @staticmethod
    def _analysis_canvas_width(available_width: int) -> int:
        debug_print("MultiPropertyPanel._analysis_canvas_width called")
        safe_width = max(0, int(available_width))
        debug_print(f"MultiPropertyPanel analysis available width={safe_width}")
        if safe_width and safe_width < _STACKED_ANALYSIS_BREAKPOINT:
            stacked_width = max(240, min(_LINE_ANALYSIS_CANVAS_W, safe_width - 56))
            debug_print(f"MultiPropertyPanel stacked analysis canvas width={stacked_width}")
            _freq_debug(f"analysis_width stacked available={safe_width} width={stacked_width}")
            return stacked_width
        canvas_width = _LINE_ANALYSIS_CANVAS_W
        debug_print("MultiPropertyPanel analysis side-by-side uses full canvas width")
        debug_print(f"MultiPropertyPanel analysis canvas width result={canvas_width}")
        _freq_debug(f"analysis_width side_by_side available={safe_width} width={canvas_width}")
        return canvas_width

    @staticmethod
    def _histogram_canvas_width(available_width: int) -> int:
        debug_print("MultiPropertyPanel._histogram_canvas_width called")
        safe_width = max(0, int(available_width))
        debug_print(f"MultiPropertyPanel histogram available width={safe_width}")
        if safe_width and safe_width < _STACKED_ANALYSIS_BREAKPOINT:
            stacked_width = max(240, min(_HISTOGRAM_ANALYSIS_CANVAS_W, safe_width - 56))
            debug_print(f"MultiPropertyPanel stacked histogram canvas width={stacked_width}")
            _freq_debug(f"histogram_width stacked available={safe_width} width={stacked_width}")
            return stacked_width
        canvas_width = _HISTOGRAM_ANALYSIS_CANVAS_W
        debug_print("MultiPropertyPanel histogram side-by-side uses wide canvas")
        debug_print(f"MultiPropertyPanel histogram canvas width result={canvas_width}")
        _freq_debug(f"histogram_width side_by_side available={safe_width} width={canvas_width}")
        return canvas_width

    def _populate_project_combo(self) -> None:
        debug_print("MultiPropertyPanel._populate_project_combo called")
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        for project in self._available_projects:
            name = project.get("project_name", project.get("vtk_folder", ""))
            self.project_combo.addItem(name, project)
            debug_print(f"MultiPropertyPanel added project={name}")
        self.project_combo.blockSignals(False)
        update_combo_popup_width(self.project_combo)
        self._on_project_changed()

    def _populate_property_combo(self) -> None:
        debug_print("MultiPropertyPanel._populate_property_combo called")
        self.property_combo.blockSignals(True)
        self.property_combo.clear()
        self.property_combo.addItem("Add Property", "")
        debug_print("MultiPropertyPanel added property placeholder")
        for scalar_def in self._scalar_defs:
            key = scalar_def["value"]
            checked = key in self._selected_keys
            label = self._property_combo_text(scalar_def["label"], checked)
            self.property_combo.addItem(label, key)
            index = self.property_combo.count() - 1
            self.property_combo.setItemData(
                index,
                Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked,
                Qt.ItemDataRole.CheckStateRole,
            )
            self.property_combo.setItemData(
                index,
                Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled,
                Qt.ItemDataRole.UserRole + 1,
            )
            debug_print(f"MultiPropertyPanel added property={scalar_def['label']}")
            debug_print(f"MultiPropertyPanel property checked={checked}")
        self.property_combo.setCurrentIndex(0)
        debug_print("MultiPropertyPanel property combo reset to placeholder")
        self.property_combo.blockSignals(False)
        update_combo_popup_width(self.property_combo)

    @staticmethod
    def _property_combo_text(label: str, checked: bool) -> str:
        debug_print("MultiPropertyPanel._property_combo_text called")
        debug_print(f"MultiPropertyPanel property combo checked={checked}")
        text = str(label)
        debug_print(f"MultiPropertyPanel property combo text={text}")
        return text

    def _on_project_changed(self) -> None:
        debug_print("MultiPropertyPanel._on_project_changed called")
        project = self.project_combo.currentData()
        files = project.get("files", []) if project else []
        self.file_combo.blockSignals(True)
        self.file_combo.clear()
        self.file_combo.addItem("Select file", "")
        debug_print("MultiPropertyPanel added file placeholder")
        for file_path in files:
            self.file_combo.addItem(Path(file_path).name, file_path)
            debug_print(f"MultiPropertyPanel added file={file_path}")
        self.file_combo.setCurrentIndex(0)
        debug_print("MultiPropertyPanel file combo reset to placeholder")
        self.file_combo.blockSignals(False)
        update_combo_popup_width(self.file_combo)
        self._render_all()

    def _on_property_combo_activated(self, index: int) -> None:
        debug_print("MultiPropertyPanel._on_property_combo_activated called")
        debug_print(f"MultiPropertyPanel activated property index={index}")
        _freq_debug(f"activated property combo index={index}")
        self._toggle_property_combo_index(index, keep_popup=True)

    def _add_selected_property(self) -> None:
        debug_print("MultiPropertyPanel._add_selected_property called")
        key = self.property_combo.currentData()
        debug_print(f"MultiPropertyPanel selected property key={key}")
        _freq_debug(f"add_selected start key={key} selected_before={list(self._selected_keys)}")
        if not key:
            debug_print("MultiPropertyPanel add skipped empty key")
            _freq_debug("add_selected skipped empty_key")
            return
        if key in self._selected_keys:
            debug_print("MultiPropertyPanel add skipped duplicate")
            _freq_debug(f"add_selected skipped duplicate key={key}")
            return
        if len(self._selected_keys) >= _MAX_PROPERTIES:
            self.status_label.setText("Maximum 10 properties")
            debug_print("MultiPropertyPanel add skipped maximum reached")
            _freq_debug(f"add_selected skipped max selected_count={len(self._selected_keys)}")
            return
        self._selected_keys.append(key)
        _freq_debug(f"add_selected appended key={key} selected_after={list(self._selected_keys)}")
        if self._active_key is None:
            self._active_key = key
            debug_print(f"MultiPropertyPanel active key initialized={key}")
            _freq_debug(f"add_selected active initialized={key}")
        debug_print(f"MultiPropertyPanel selected count={len(self._selected_keys)}")
        self._sync_property_combo_checks()
        self._sync_cells()
        self._render_all()
        _freq_debug(f"add_selected complete selected_final={list(self._selected_keys)}")

    def _toggle_property_combo_index(self, index: int, *, keep_popup: bool = True) -> None:
        debug_print("MultiPropertyPanel._toggle_property_combo_index called")
        debug_print(f"MultiPropertyPanel toggle index={index}")
        debug_print(f"MultiPropertyPanel toggle keep_popup={keep_popup}")
        _freq_debug(f"toggle start index={index} selected_before={list(self._selected_keys)}")
        if index <= 0 or index >= self.property_combo.count():
            debug_print("MultiPropertyPanel toggle skipped placeholder/out of range")
            _freq_debug(f"toggle skipped out_of_range index={index} combo_count={self.property_combo.count()}")
            self.property_combo.setCurrentIndex(0)
            return
        key = self.property_combo.itemData(index)
        debug_print(f"MultiPropertyPanel toggle key={key}")
        _freq_debug(f"toggle key={key}")
        if not key:
            debug_print("MultiPropertyPanel toggle skipped empty key")
            _freq_debug("toggle skipped empty key")
            self.property_combo.setCurrentIndex(0)
            return
        if key in self._selected_keys:
            debug_print("MultiPropertyPanel toggle removing selected key")
            _freq_debug(f"toggle removing key={key}")
            self._remove_property(key)
        else:
            debug_print("MultiPropertyPanel toggle adding unchecked key")
            if len(self._selected_keys) >= _MAX_PROPERTIES:
                self.status_label.setText("Maximum 10 properties")
                debug_print("MultiPropertyPanel toggle skipped maximum reached")
                _freq_debug(f"toggle skipped max selected_count={len(self._selected_keys)}")
            else:
                self._selected_keys.append(key)
                debug_print(f"MultiPropertyPanel selected count={len(self._selected_keys)}")
                _freq_debug(f"toggle appended key={key} selected_after={list(self._selected_keys)}")
                if self._active_key is None:
                    self._active_key = key
                    debug_print(f"MultiPropertyPanel active key initialized={key}")
                    _freq_debug(f"toggle active initialized={key}")
                self._sync_property_combo_checks()
                self._sync_cells()
                self._render_all()
        self.property_combo.setCurrentIndex(0)
        debug_print("MultiPropertyPanel property combo current reset to placeholder after toggle")
        _freq_debug(f"toggle complete selected_final={list(self._selected_keys)} active={self._active_key}")
        if keep_popup:
            self.property_combo.showPopup()
            debug_print("MultiPropertyPanel property combo popup reopened")

    def _sync_property_combo_checks(self) -> None:
        debug_print("MultiPropertyPanel._sync_property_combo_checks called")
        selected = set(self._selected_keys)
        debug_print(f"MultiPropertyPanel selected combo check count={len(selected)}")
        self.property_combo.blockSignals(True)
        for index in range(1, self.property_combo.count()):
            key = self.property_combo.itemData(index)
            checked = key in selected
            debug_print(f"MultiPropertyPanel sync property key={key}")
            debug_print(f"MultiPropertyPanel sync property checked={checked}")
            scalar_def = self._scalar_def_for_key(key)
            property_labels = getattr(self, "_property_labels", {})
            label = property_labels.get(key, scalar_def.get("label", key))
            self.property_combo.setItemText(index, self._property_combo_text(label, checked))
            self.property_combo.setItemData(
                index,
                Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked,
                Qt.ItemDataRole.CheckStateRole,
            )
        self.property_combo.setCurrentIndex(0)
        self.property_combo.blockSignals(False)
        update_combo_popup_width(self.property_combo)
        debug_print("MultiPropertyPanel property combo checks synced")

    def _add_all_properties(self) -> None:
        debug_print("MultiPropertyPanel._add_all_properties called")
        added_count = 0
        debug_print(f"MultiPropertyPanel add all scalar count={len(self._scalar_defs)}")
        for scalar_def in self._scalar_defs:
            key = scalar_def.get("value")
            debug_print(f"MultiPropertyPanel add all checking key={key}")
            if not key:
                debug_print("MultiPropertyPanel add all skipped empty key")
                continue
            if key in self._selected_keys:
                debug_print(f"MultiPropertyPanel add all skipped duplicate key={key}")
                continue
            if len(self._selected_keys) >= _MAX_PROPERTIES:
                self.status_label.setText("Maximum 10 properties")
                debug_print("MultiPropertyPanel add all stopped maximum reached")
                break
            self._selected_keys.append(key)
            added_count += 1
            debug_print(f"MultiPropertyPanel add all appended key={key}")
            debug_print(f"MultiPropertyPanel selected count={len(self._selected_keys)}")
            if self._active_key is None:
                self._active_key = key
                debug_print(f"MultiPropertyPanel active key initialized={key}")
        if added_count == 0:
            debug_print("MultiPropertyPanel add all no new properties")
            return
        debug_print(f"MultiPropertyPanel add all added count={added_count}")
        self._sync_property_combo_checks()
        self._sync_cells()
        self._render_all()

    def _clear_properties(self) -> None:
        debug_print("MultiPropertyPanel._clear_properties called")
        self._selected_keys.clear()
        self._ranges.clear()
        self._property_labels.clear()
        self._grid_cache.clear()
        self._active_key = None
        self._reset_click_range_state("properties cleared")
        debug_print("MultiPropertyPanel active key cleared")
        debug_print("MultiPropertyPanel custom labels cleared")
        self._sync_property_combo_checks()
        self._sync_cells()
        self._render_all()

    def _remove_property(self, key: str) -> None:
        debug_print("MultiPropertyPanel._remove_property called")
        debug_print(f"MultiPropertyPanel remove key={key}")
        if key in self._selected_keys:
            self._selected_keys.remove(key)
        self._ranges.pop(key, None)
        self._property_labels.pop(key, None)
        self._grid_cache.pop(key, None)
        self._reset_click_range_state("property removed")
        debug_print("MultiPropertyPanel custom label removed")
        if self._active_key == key:
            self._active_key = self._selected_keys[0] if self._selected_keys else None
            debug_print(f"MultiPropertyPanel active key after remove={self._active_key}")
        self._sync_property_combo_checks()
        self._sync_cells()
        self._render_all()

    def _select_property(self, key: str) -> None:
        debug_print("MultiPropertyPanel._select_property called")
        debug_print(f"MultiPropertyPanel requested active key={key}")
        if key not in self._selected_keys:
            debug_print("MultiPropertyPanel select skipped missing key")
            return
        self._active_key = key
        debug_print(f"MultiPropertyPanel active key set={self._active_key}")
        self._sync_selected_bullets()
        self._sync_top_range_controls()

    def _on_line_mode_toggled(self, checked: bool) -> None:
        debug_print("MultiPropertyPanel._on_line_mode_toggled called")
        debug_print(f"MultiPropertyPanel line mode checked={checked}")
        if checked:
            self._reset_click_range_state("line scan mode enabled")
            debug_print("MultiPropertyPanel click range state reset for line mode")
        self._render_all()
        debug_print("MultiPropertyPanel._on_line_mode_toggled complete")

    def _on_analysis_control_changed(self, *_) -> None:
        debug_print("MultiPropertyPanel._on_analysis_control_changed called")
        bins_slider = getattr(self, "histogram_bins_slider", None)
        bins_value = bins_slider.value() if bins_slider is not None else 30
        debug_print(f"MultiPropertyPanel line direction={self._current_line_scan_direction()}")
        debug_print(f"MultiPropertyPanel histogram bins={bins_value}")
        self._refresh_analysis_only()
        debug_print("MultiPropertyPanel._on_analysis_control_changed complete")

    def _set_analysis_visible(self, visible: bool) -> None:
        debug_print("MultiPropertyPanel._set_analysis_visible called")
        debug_print(f"MultiPropertyPanel analysis visible requested={visible}")
        analysis_card = getattr(self, "analysis_card", None)
        if analysis_card is None:
            debug_print("MultiPropertyPanel analysis visibility skipped no card")
            return
        analysis_card.setVisible(bool(visible))
        debug_print(f"MultiPropertyPanel analysis hidden={analysis_card.isHidden()}")

    def _refresh_analysis_only(self) -> None:
        debug_print("MultiPropertyPanel._refresh_analysis_only called")
        file_path = self.file_combo.currentData() if hasattr(self, "file_combo") else ""
        debug_print(f"MultiPropertyPanel analysis-only file_path={file_path}")
        selected_count = len(getattr(self, "_selected_keys", []))
        debug_print(f"MultiPropertyPanel analysis-only selected count={selected_count}")
        grid_count = len(getattr(self, "_grid_cache", {}))
        debug_print(f"MultiPropertyPanel analysis-only grid count={grid_count}")
        if not file_path or selected_count == 0 or grid_count == 0:
            self._set_analysis_visible(False)
            debug_print("MultiPropertyPanel analysis-only skipped missing data")
            return
        self._set_analysis_visible(True)
        debug_print("MultiPropertyPanel analysis-only rendering cached graphs")
        self._render_analysis()
        debug_print("MultiPropertyPanel._refresh_analysis_only complete")

    def _handle_cell_click(self, property_key: str, x_value: float, y_value: float) -> None:
        debug_print("MultiPropertyPanel._handle_cell_click called")
        debug_print(f"MultiPropertyPanel click property={property_key}")
        debug_print(f"MultiPropertyPanel click x={x_value}")
        debug_print(f"MultiPropertyPanel click y={y_value}")
        if property_key not in self._selected_keys:
            debug_print("MultiPropertyPanel click ignored missing property")
            self.status_label.setText("Click ignored: property not selected")
            return
        self._active_key = property_key
        debug_print(f"MultiPropertyPanel click active key={self._active_key}")
        self._sync_selected_bullets()
        self._sync_top_range_controls()
        line_mode = getattr(self, "line_mode_check", None)
        line_mode_enabled = bool(line_mode is not None and line_mode.isChecked())
        debug_print(f"MultiPropertyPanel line mode enabled={line_mode_enabled}")
        if line_mode_enabled:
            self._apply_line_scan_click(x_value, y_value)
            debug_print("MultiPropertyPanel click handled as line scan")
            return
        grid = self._grid_cache.get(property_key)
        if grid is None:
            debug_print("MultiPropertyPanel click ignored missing cached grid")
            self.status_label.setText("Click ignored: render data not ready")
            return
        x_grid, y_grid, z_grid = grid
        try:
            clicked_value = MultiViewPanel._nearest_grid_value(x_grid, y_grid, z_grid, x_value, y_value)
        except ValueError as exc:
            debug_print(f"MultiPropertyPanel click ignored: {exc}")
            self.status_label.setText("Click ignored: no valid value")
            return
        debug_print(f"MultiPropertyPanel clicked value={clicked_value}")
        self._apply_click_range_value(property_key, clicked_value)

    def _apply_click_range_value(self, property_key: str, clicked_value: float) -> None:
        debug_print("MultiPropertyPanel._apply_click_range_value called")
        debug_print(f"MultiPropertyPanel click range property={property_key}")
        debug_print(f"MultiPropertyPanel click value={clicked_value}")
        if self._click_count == 0:
            self._first_click_value = float(clicked_value)
            self._click_count = 1
            message = f"First click: {clicked_value:.6f} (click again to finish range)"
            self.status_label.setText(message)
            debug_print(message)
            return
        lo, hi = sorted([float(self._first_click_value), float(clicked_value)])
        self._click_count = 0
        self._first_click_value = None
        state = self._ranges.setdefault(property_key, {})
        state["selected_min"] = lo
        state["selected_max"] = hi
        debug_print(f"MultiPropertyPanel click selected_min={lo}")
        debug_print(f"MultiPropertyPanel click selected_max={hi}")
        self._sync_top_range_controls()
        message = f"Range selected: [{lo:.6f}, {hi:.6f}]"
        self.status_label.setText(message)
        debug_print(message)
        self._render_all()

    def _apply_line_scan_click(self, x_value: float, y_value: float) -> None:
        debug_print("MultiPropertyPanel._apply_line_scan_click called")
        direction = self._current_line_scan_direction()
        debug_print(f"MultiPropertyPanel line scan direction={direction}")
        if direction == "horizontal":
            self._line_scan_y = float(y_value)
            debug_print(f"MultiPropertyPanel line scan y set={self._line_scan_y}")
            message = f"Line scan Y={self._line_scan_y:.6f}"
        else:
            self._line_scan_x = float(x_value)
            debug_print(f"MultiPropertyPanel line scan x set={self._line_scan_x}")
            message = f"Line scan X={self._line_scan_x:.6f}"
        self.status_label.setText(message)
        debug_print(message)
        self._render_all()
        debug_print("MultiPropertyPanel._apply_line_scan_click complete")

    def _reset_click_range_state(self, reason: str) -> None:
        debug_print("MultiPropertyPanel._reset_click_range_state called")
        debug_print(f"MultiPropertyPanel reset click reason={reason}")
        self._click_count = 0
        self._first_click_value = None

    def _on_property_range_changed(self, key: str, minimum: float, maximum: float) -> None:
        debug_print("MultiPropertyPanel._on_property_range_changed called")
        debug_print(f"MultiPropertyPanel range key={key}")
        debug_print(f"MultiPropertyPanel range minimum={minimum}")
        debug_print(f"MultiPropertyPanel range maximum={maximum}")
        lo, hi = sorted([float(minimum), float(maximum)])
        self._reset_click_range_state("manual range changed")
        state = self._ranges.setdefault(key, {})
        state["selected_min"] = lo
        state["selected_max"] = hi
        debug_print(f"MultiPropertyPanel stored selected range={lo}..{hi}")
        self._render_all()

    def _on_active_range_spin_changed(self, *_args) -> None:
        debug_print("MultiPropertyPanel._on_active_range_spin_changed called")
        if self._active_key is None:
            debug_print("MultiPropertyPanel spin change skipped no active key")
            return
        debug_print(f"MultiPropertyPanel spin active key={self._active_key}")
        self._on_property_range_changed(self._active_key, self.range_min.value(), self.range_max.value())

    def _on_active_slider_range_changed(self, minimum: float, maximum: float) -> None:
        debug_print("MultiPropertyPanel._on_active_slider_range_changed called")
        debug_print(f"MultiPropertyPanel slider minimum={minimum}")
        debug_print(f"MultiPropertyPanel slider maximum={maximum}")
        if self._active_key is None:
            debug_print("MultiPropertyPanel slider change skipped no active key")
            return
        self._set_top_range_values(minimum, maximum)
        self._on_property_range_changed(self._active_key, minimum, maximum)

    def _reset_property_range(self, key: str) -> None:
        debug_print("MultiPropertyPanel._reset_property_range called")
        debug_print(f"MultiPropertyPanel reset key={key}")
        state = self._ranges.get(key)
        if not state:
            debug_print("MultiPropertyPanel reset skipped no state")
            return
        state["selected_min"] = state.get("data_min", 0.0)
        state["selected_max"] = state.get("data_max", 1.0)
        self._sync_top_range_controls()
        self._render_all()

    def _reset_active_range(self) -> None:
        debug_print("MultiPropertyPanel._reset_active_range called")
        if self._active_key is None:
            debug_print("MultiPropertyPanel reset active skipped no active key")
            return
        self._reset_property_range(self._active_key)

    def _reset_all_ranges(self) -> None:
        debug_print("MultiPropertyPanel._reset_all_ranges called")
        reset_count = 0
        for key, state in self._ranges.items():
            debug_print(f"MultiPropertyPanel reset all key={key}")
            if "data_min" not in state or "data_max" not in state:
                debug_print("MultiPropertyPanel reset all skipped missing bounds")
                continue
            state["selected_min"] = state.get("data_min", 0.0)
            state["selected_max"] = state.get("data_max", 1.0)
            reset_count += 1
            debug_print(f"MultiPropertyPanel reset all selected_min={state['selected_min']}")
            debug_print(f"MultiPropertyPanel reset all selected_max={state['selected_max']}")
        debug_print(f"MultiPropertyPanel reset all count={reset_count}")
        self._sync_top_range_controls()
        self._render_all()

    def _on_unit_scale_changed(self, *_) -> None:
        debug_print("MultiPropertyPanel._on_unit_scale_changed called")
        debug_print(f"MultiPropertyPanel ranges before unit change={len(self._ranges)}")
        self._ranges.clear()
        debug_print("MultiPropertyPanel ranges cleared after unit change")
        self._render_all()
        debug_print("MultiPropertyPanel._on_unit_scale_changed complete")

    def _get_display_params(self, scalar_label: str, *, override_label: str | None = None) -> tuple[float, str]:
        debug_print("MultiPropertyPanel._get_display_params called")
        extra_scale, unit_suffix = self.unit_scale_combo.currentData() if hasattr(self, "unit_scale_combo") else (1.0, "")
        debug_print(f"MultiPropertyPanel unit scale multiplier={extra_scale}")
        debug_print(f"MultiPropertyPanel unit suffix={unit_suffix}")
        base_label = override_label or scalar_label
        debug_print(f"MultiPropertyPanel scalar label={scalar_label}")
        debug_print(f"MultiPropertyPanel override label={override_label}")
        label = f"{base_label} ({unit_suffix})" if unit_suffix else base_label
        debug_print(f"MultiPropertyPanel display label={label}")
        return float(extra_scale), label

    def _on_property_renamed(self, key: str, label: str) -> None:
        debug_print("MultiPropertyPanel._on_property_renamed called")
        clean_label = str(label).strip()
        debug_print(f"MultiPropertyPanel renamed key={key}")
        debug_print(f"MultiPropertyPanel renamed label={clean_label}")
        if not clean_label:
            debug_print("MultiPropertyPanel rename skipped empty label")
            return
        self._property_labels[key] = clean_label
        debug_print("MultiPropertyPanel custom label stored")
        self._render_all()
        debug_print("MultiPropertyPanel rerendered after rename")

    def _on_rotation_changed(self, degrees: int) -> None:
        debug_print("MultiPropertyPanel._on_rotation_changed called")
        self._selected_rotation_degrees = int(degrees)
        debug_print(f"MultiPropertyPanel selected icon rotation degrees={self._selected_rotation_degrees}")
        self._rotation_degrees = self._clockwise_to_orientation_degrees(degrees)
        debug_print(f"MultiPropertyPanel internal rotation degrees={self._rotation_degrees}")
        self._sync_rotation_buttons()
        self._line_scan_x = None
        debug_print("MultiPropertyPanel line scan x reset after rotation")
        self._line_scan_y = None
        debug_print("MultiPropertyPanel line scan y reset after rotation")
        self._render_all()

    def _sync_top_range_controls(self) -> None:
        debug_print("MultiPropertyPanel._sync_top_range_controls called")
        active_key = self._active_key if self._active_key in self._selected_keys else None
        debug_print(f"MultiPropertyPanel sync active key={active_key}")
        enabled = bool(active_key and active_key in self._ranges)
        self.range_min.setEnabled(enabled)
        self.range_max.setEnabled(enabled)
        self.range_slider.setEnabled(enabled)
        self.reset_button.setEnabled(enabled)
        self.reset_all_button.setEnabled(bool(self._ranges))
        debug_print(f"MultiPropertyPanel top range enabled={enabled}")
        debug_print(f"MultiPropertyPanel reset all enabled={self.reset_all_button.isEnabled()}")
        if not enabled:
            self._set_top_range_values(0.0, 1.0)
            self.range_slider.set_bounds(0.0, 1.0)
            debug_print("MultiPropertyPanel top range defaulted")
            return
        state = self._ranges[active_key]
        data_min = float(state.get("data_min", 0.0))
        data_max = float(state.get("data_max", 1.0))
        selected_min = float(state.get("selected_min", data_min))
        selected_max = float(state.get("selected_max", data_max))
        debug_print(f"MultiPropertyPanel top data min={data_min}")
        debug_print(f"MultiPropertyPanel top data max={data_max}")
        debug_print(f"MultiPropertyPanel top selected min={selected_min}")
        debug_print(f"MultiPropertyPanel top selected max={selected_max}")
        self.range_slider.blockSignals(True)
        self.range_slider.set_bounds(data_min, data_max)
        self.range_slider.blockSignals(False)
        self._set_top_range_values(selected_min, selected_max)
        debug_print("MultiPropertyPanel top range synced")

    def _set_top_range_values(self, minimum: float, maximum: float) -> None:
        debug_print("MultiPropertyPanel._set_top_range_values called")
        debug_print(f"MultiPropertyPanel top set minimum={minimum}")
        debug_print(f"MultiPropertyPanel top set maximum={maximum}")
        self.range_min.blockSignals(True)
        self.range_max.blockSignals(True)
        self.range_slider.blockSignals(True)
        self.range_min.setValue(float(minimum))
        self.range_max.setValue(float(maximum))
        self.range_slider.set_values(float(minimum), float(maximum), emit_signal=False)
        self.range_min.blockSignals(False)
        self.range_max.blockSignals(False)
        self.range_slider.blockSignals(False)
        debug_print(f"MultiPropertyPanel top min spin value={self.range_min.value()}")
        debug_print(f"MultiPropertyPanel top max spin value={self.range_max.value()}")
        debug_print(f"MultiPropertyPanel top slider lower={self.range_slider.lower_value()}")
        debug_print(f"MultiPropertyPanel top slider upper={self.range_slider.upper_value()}")

    def _export_png(self) -> None:
        debug_print("MultiPropertyPanel._export_png called")
        if not self._selected_keys:
            self.status_label.setText("Add properties before export")
            debug_print("MultiPropertyPanel export skipped no properties")
            return
        selected_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Multi Property PNG",
            "multi_property.png",
            "PNG (*.png)",
        )
        debug_print(f"MultiPropertyPanel export selected path={selected_path}")
        output_path = self._normalise_png_export_path(selected_path)
        debug_print(f"MultiPropertyPanel export output path={output_path}")
        if output_path is None:
            debug_print("MultiPropertyPanel export cancelled")
            return
        saved = self._save_high_resolution_export_png(str(output_path))
        debug_print(f"MultiPropertyPanel high-resolution export saved={saved}")
        if not saved:
            debug_print("MultiPropertyPanel falling back to live widget capture")
            pixmap = self._grab_export_pixmap()
            debug_print(f"MultiPropertyPanel export pixmap null={pixmap.isNull()}")
            saved = bool(pixmap.save(str(output_path), "PNG"))
        debug_print(f"MultiPropertyPanel export saved={saved}")
        if saved:
            self.status_label.setText(f"Exported {output_path.name}")
        else:
            self.status_label.setText("Export failed")
        debug_print("MultiPropertyPanel._export_png complete")

    def _save_high_resolution_export_png(self, path: str) -> bool:
        debug_print("MultiPropertyPanel._save_high_resolution_export_png called")
        try:
            rows = self._build_high_resolution_export_rows()
            debug_print(f"MultiPropertyPanel export payload rows ready={rows is not None}")
            if rows is None:
                return False
            dpi = int(DEFAULTS.get("export_dpi", 300))
            debug_print(f"MultiPropertyPanel export dpi={dpi}")
            return bool(save_multi_property_png(path, rows=rows, logo_path=HEATMAP_LOGO_PATH, dpi=dpi))
        except Exception as exc:
            debug_print(f"MultiPropertyPanel high-resolution export failed={exc}")
            return False

    def _build_high_resolution_export_rows(self) -> list[list[dict]] | None:
        debug_print("MultiPropertyPanel._build_high_resolution_export_rows called")
        file_path = self.file_combo.currentData()
        debug_print(f"MultiPropertyPanel export file_path={file_path}")
        if not file_path or not self._selected_keys:
            debug_print("MultiPropertyPanel export payload skipped missing input")
            return None
        export_resolution = int(DEFAULTS.get("export_resolution", 1000))
        debug_print(f"MultiPropertyPanel export interpolation resolution={export_resolution}")
        reader = get_reader(file_path)
        axis = Heatmap2DOrientation.detect_axis(reader.dimensions)
        orientation = Heatmap2DOrientation(getattr(self, "_rotation_degrees", 0))
        cmap = self._palette_cmap(self.palette_combo.currentData() or "aqua-fire")
        type_combo = getattr(self, "type_combo", None)
        plot_type = type_combo.currentData() if type_combo is not None else "heatmap"
        plot_type = plot_type or "heatmap"
        debug_print(f"MultiPropertyPanel export plot_type={plot_type}")
        raw_overlay = self._build_overlay_grid(file_path, axis, resolution=export_resolution)
        overlay_grid = orientation.apply_overlay(raw_overlay) if raw_overlay is not None else None
        line_overlay = self._current_line_overlay()
        payloads = {}
        for key in self._selected_keys:
            debug_print(f"MultiPropertyPanel building export property={key}")
            payloads[key] = self._build_export_property_payload(
                reader,
                axis=axis,
                orientation=orientation,
                key=key,
                cmap=cmap,
                plot_type=plot_type,
                overlay_grid=overlay_grid,
                line_overlay=line_overlay,
                resolution=export_resolution,
            )
        columns = self._columns_for_count(len(self._selected_keys))
        rows = [[payloads[key] for key in keys] for keys in self._row_keys(columns)]
        debug_print(f"MultiPropertyPanel export row count={len(rows)}")
        return rows

    def _build_export_property_payload(
        self,
        reader,
        *,
        axis: str,
        orientation: Heatmap2DOrientation,
        key: str,
        cmap,
        plot_type: str,
        overlay_grid,
        line_overlay,
        resolution: int,
    ) -> dict:
        debug_print("MultiPropertyPanel._build_export_property_payload called")
        debug_print(f"MultiPropertyPanel export property key={key}")
        debug_print(f"MultiPropertyPanel export property resolution={resolution}")
        scalar_def = self._scalar_def_for_key(key)
        x_grid, y_grid, z_grid, _ = reader.get_interpolated_slice(
            axis=axis,
            index=0,
            scalar_name=scalar_def["array"],
            component=scalar_def.get("component"),
            resolution=resolution,
        )
        scale = scalar_def.get("scale", 1.0) or 1.0
        base_label = getattr(self, "_property_labels", {}).get(key, scalar_def.get("label", key))
        extra_scale, display_label = self._get_display_params(scalar_def.get("label", key), override_label=base_label)
        z_grid = np.asarray(z_grid, dtype=float) * scale * extra_scale
        display = orientation.apply_grid(x_grid, y_grid, z_grid)
        state = self._ranges.get(key, {})
        vmin = float(state.get("selected_min", np.nanmin(display.z)))
        vmax = float(state.get("selected_max", np.nanmax(display.z)))
        debug_print(f"MultiPropertyPanel export property shape={np.asarray(display.z).shape}")
        debug_print(f"MultiPropertyPanel export property range={vmin}..{vmax}")
        return {
            "x_grid": display.x,
            "y_grid": display.y,
            "z_grid": display.z,
            "cmap": cmap,
            "vmin": vmin,
            "vmax": vmax,
            "label": display_label,
            "plot_type": plot_type,
            "overlay_grid": overlay_grid,
            "line_overlay": line_overlay,
        }

    def _grab_export_pixmap(self) -> QPixmap:
        debug_print("MultiPropertyPanel._grab_export_pixmap called")
        states = self._set_export_controls_hidden(True)
        debug_print(f"MultiPropertyPanel export hidden controls count={len(states)}")
        try:
            if hasattr(self.rows_widget, "updateGeometry"):
                self.rows_widget.updateGeometry()
                debug_print("MultiPropertyPanel export rows geometry updated")
            else:
                debug_print("MultiPropertyPanel export rows geometry update skipped")
            pixmap = self.rows_widget.grab()
            debug_print(f"MultiPropertyPanel export live grab width={pixmap.width()}")
            debug_print(f"MultiPropertyPanel export live grab height={pixmap.height()}")
            debug_print(f"MultiPropertyPanel export live grab null={pixmap.isNull()}")
            debug_print("MultiPropertyPanel export live rows pixmap complete")
            return pixmap
        finally:
            self._restore_export_controls_hidden(states)
            debug_print("MultiPropertyPanel export controls restored after live grab")

    def _export_rows(self) -> list[list[tuple[str, QPixmap, int, int]]]:
        debug_print("MultiPropertyPanel._export_rows called")
        rows: list[list[tuple[str, QPixmap, int, int]]] = []
        for row_index, row_widget in enumerate(self._row_widgets):
            row_layout = row_widget.layout()
            if row_layout is None:
                debug_print(f"MultiPropertyPanel export row skipped no layout index={row_index}")
                continue
            row: list[tuple[str, QPixmap, int, int]] = []
            for item_index in range(row_layout.count()):
                widget = row_layout.itemAt(item_index).widget()
                if widget is None:
                    debug_print(f"MultiPropertyPanel export skipped empty item index={item_index}")
                    continue
                if isinstance(widget, MultiPropertyCell):
                    pixmap = self._grab_export_cell(widget)
                    row.append(("multiPropertyExportCell", pixmap, pixmap.width(), pixmap.height()))
                    debug_print(f"MultiPropertyPanel export added cell key={widget.property_key}")
                elif widget.objectName() == "multiPropertyLogoBand":
                    pixmap = widget.grab()
                    row.append(("multiPropertyLogoBand", pixmap, pixmap.width(), pixmap.height()))
                    debug_print("MultiPropertyPanel export added logo band")
            if row:
                rows.append(row)
                debug_print(f"MultiPropertyPanel export row added index={row_index}")
        return rows

    def _grab_export_cell(self, cell: MultiPropertyCell) -> QPixmap:
        debug_print("MultiPropertyPanel._grab_export_cell called")
        debug_print(f"MultiPropertyPanel export cell key={cell.property_key}")
        widgets = [cell.heatmap, cell.colorbar] if cell._bottom_row else [cell.colorbar, cell.heatmap]
        pixmaps = [widget.grab() for widget in widgets]
        width = max((pixmap.width() for pixmap in pixmaps), default=1)
        height = sum(pixmap.height() for pixmap in pixmaps)
        width = max(1, width)
        height = max(1, height)
        debug_print(f"MultiPropertyPanel export cell width={width}")
        debug_print(f"MultiPropertyPanel export cell height={height}")
        cell_canvas = QPixmap(width, height)
        cell_canvas.fill(Qt.GlobalColor.white)
        painter = QPainter(cell_canvas)
        y = 0
        for pixmap in pixmaps:
            painter.drawPixmap(0, y, pixmap)
            debug_print(f"MultiPropertyPanel export cell paint y={y}")
            y += pixmap.height()
        painter.end()
        debug_print("MultiPropertyPanel export cell pixmap ready")
        return cell_canvas

    def _set_export_controls_hidden(self, hidden: bool) -> list[tuple[QWidget, bool]]:
        debug_print("MultiPropertyPanel._set_export_controls_hidden called")
        debug_print(f"MultiPropertyPanel export set controls hidden={hidden}")
        states: list[tuple[QWidget, bool]] = []
        for key, cell in getattr(self, "_cells", {}).items():
            controls = cell.controls
            was_hidden = controls.isHidden()
            states.append((controls, was_hidden))
            debug_print(f"MultiPropertyPanel export controls key={key}")
            debug_print(f"MultiPropertyPanel export controls was_hidden={was_hidden}")
            controls.setHidden(hidden)
            debug_print(f"MultiPropertyPanel export controls now_hidden={controls.isHidden()}")
        if hasattr(self.rows_widget, "updateGeometry"):
            self.rows_widget.updateGeometry()
            debug_print("MultiPropertyPanel export rows geometry updated")
        else:
            debug_print("MultiPropertyPanel export rows geometry update skipped")
        return states

    def _restore_export_controls_hidden(self, states: list[tuple[QWidget, bool]]) -> None:
        debug_print("MultiPropertyPanel._restore_export_controls_hidden called")
        for controls, was_hidden in states:
            controls.setHidden(was_hidden)
            debug_print(f"MultiPropertyPanel restored controls hidden={was_hidden}")
        if hasattr(self.rows_widget, "updateGeometry"):
            self.rows_widget.updateGeometry()
            debug_print("MultiPropertyPanel restored rows geometry updated")
        else:
            debug_print("MultiPropertyPanel restored rows geometry update skipped")

    @staticmethod
    def _normalise_png_export_path(path: str) -> Path | None:
        debug_print("MultiPropertyPanel._normalise_png_export_path called")
        debug_print(f"MultiPropertyPanel raw export path={path}")
        if not path:
            debug_print("MultiPropertyPanel normalised export path=None")
            return None
        output_path = Path(path)
        if not output_path.suffix:
            output_path = output_path.with_suffix(".png")
            debug_print(f"MultiPropertyPanel appended png suffix={output_path}")
        debug_print(f"MultiPropertyPanel normalised export path={output_path}")
        return output_path

    def _render_analysis(self) -> None:
        debug_print("MultiPropertyPanel._render_analysis called")
        _freq_debug(f"render_analysis start selected={list(getattr(self, '_selected_keys', []))}")
        _freq_debug(f"render_analysis cache_keys={list(getattr(self, '_grid_cache', {}).keys())}")
        value_label = self._analysis_value_label()
        debug_print(f"MultiPropertyPanel analysis value label={value_label}")
        _freq_debug(f"analysis_value_label={value_label}")
        line_series, line_title, x_label = self._build_line_scan_series()
        debug_print(f"MultiPropertyPanel line series count={len(line_series)}")
        _freq_debug(f"line_series_count={len(line_series)} names={[item.get('name', '') for item in line_series]}")
        line_grid_check = getattr(self, "line_grid_check", None)
        show_line_grid = True if line_grid_check is None else line_grid_check.isChecked()
        debug_print(f"MultiPropertyPanel line grid shown={show_line_grid}")
        self.line_scan_canvas.render_lines(
            line_series,
            title=line_title,
            x_label=x_label,
            y_label=value_label,
            show_grid=show_line_grid,
        )
        debug_print("MultiPropertyPanel line graph rendered")
        hist_series, hist_label = self._build_histogram_series()
        hist_label = value_label or hist_label
        debug_print(f"MultiPropertyPanel histogram value label={hist_label}")
        debug_print(f"MultiPropertyPanel histogram series count={len(hist_series)}")
        _freq_debug(f"hist_series_count={len(hist_series)} names={[item.get('name', '') for item in hist_series]}")
        histogram_bins_slider = getattr(self, "histogram_bins_slider", None)
        bins = int(histogram_bins_slider.value()) if histogram_bins_slider is not None else 30
        debug_print(f"MultiPropertyPanel histogram bins={bins}")
        _freq_debug(f"hist_bins={bins}")
        histogram_grid_check = getattr(self, "histogram_grid_check", None)
        show_histogram_grid = True if histogram_grid_check is None else histogram_grid_check.isChecked()
        debug_print(f"MultiPropertyPanel histogram grid shown={show_histogram_grid}")
        self.histogram_canvas.render_histograms(
            hist_series,
            label=hist_label,
            bins=bins,
            show_grid=show_histogram_grid,
        )
        debug_print("MultiPropertyPanel histogram graph rendered")
        _freq_debug("hist_render_called")
        self._refresh_analysis_canvases()
        debug_print("MultiPropertyPanel analysis canvases refreshed")
        debug_print("MultiPropertyPanel._render_analysis complete")

    def _analysis_value_label(self, fallback: str = "Value") -> str:
        debug_print("MultiPropertyPanel._analysis_value_label called")
        edit = getattr(self, "analysis_value_label_edit", None)
        debug_print(f"MultiPropertyPanel analysis label edit present={edit is not None}")
        text = edit.text().strip() if edit is not None else ""
        debug_print(f"MultiPropertyPanel analysis label raw={text}")
        label = text or fallback
        debug_print(f"MultiPropertyPanel analysis label result={label}")
        _freq_debug(f"analysis_label result={label}")
        return label

    def _palette_cmap(self, palette_name: str):
        debug_print("MultiPropertyPanel._palette_cmap called")
        debug_print(f"MultiPropertyPanel palette cmap name={palette_name}")
        if palette_name == DISCRETE_CUSTOM_PALETTE:
            debug_print(f"MultiPropertyPanel building discrete cmap bands={self.discrete_band_count}")
            return make_discrete_colormap(discrete_palette_colors(self.discrete_band_count))
        debug_print("MultiPropertyPanel building normal cmap")
        return palette_to_cmap(palette_name)

    def _on_palette_changed(self, *_) -> None:
        debug_print("MultiPropertyPanel._on_palette_changed called")
        self._sync_discrete_controls()
        self._render_all()

    def _sync_discrete_controls(self) -> None:
        debug_print("MultiPropertyPanel._sync_discrete_controls called")
        visible = (self.palette_combo.currentData() or "aqua-fire") == DISCRETE_CUSTOM_PALETTE
        debug_print(f"MultiPropertyPanel discrete controls visible={visible}")
        self.discrete_minus_button.setVisible(visible)
        self.discrete_band_label.setVisible(visible)
        self.discrete_plus_button.setVisible(visible)

    def _change_discrete_band_count(self, delta: int) -> None:
        debug_print("MultiPropertyPanel._change_discrete_band_count called")
        debug_print(f"MultiPropertyPanel discrete delta={delta}")
        next_count = max(2, min(10, self.discrete_band_count + int(delta)))
        debug_print(f"MultiPropertyPanel discrete next_count={next_count}")
        if next_count == self.discrete_band_count:
            debug_print("MultiPropertyPanel discrete count unchanged")
            return
        self.discrete_band_count = next_count
        self.discrete_band_label.setText(str(next_count))
        debug_print(f"MultiPropertyPanel discrete label={self.discrete_band_label.text()}")
        self._render_all()

    def _refresh_analysis_canvases(self) -> None:
        debug_print("MultiPropertyPanel._refresh_analysis_canvases called")
        for name in ("line_scan_canvas", "histogram_canvas"):
            canvas = getattr(self, name, None)
            debug_print(f"MultiPropertyPanel refresh canvas name={name}")
            if canvas is None:
                debug_print("MultiPropertyPanel refresh skipped missing canvas")
                continue
            if hasattr(canvas, "updateGeometry"):
                canvas.updateGeometry()
                debug_print("MultiPropertyPanel canvas geometry updated")
            web_view = getattr(canvas, "_web_view", None)
            debug_print(f"MultiPropertyPanel canvas web view present={web_view is not None}")
            if web_view is not None:
                web_view.show()
                debug_print("MultiPropertyPanel canvas web view shown")
                web_view.updateGeometry()
                debug_print("MultiPropertyPanel canvas web view geometry updated")
                web_view.repaint()
                debug_print("MultiPropertyPanel canvas web view repainted")
            if hasattr(canvas, "repaint"):
                canvas.repaint()
                debug_print("MultiPropertyPanel canvas repainted")
        debug_print("MultiPropertyPanel._refresh_analysis_canvases complete")

    def _build_line_scan_series(self) -> tuple[list[dict], str, str]:
        debug_print("MultiPropertyPanel._build_line_scan_series called")
        direction = self._current_line_scan_direction()
        position = self._line_scan_y if direction == "horizontal" else self._line_scan_x
        debug_print(f"MultiPropertyPanel line direction={direction}")
        debug_print(f"MultiPropertyPanel line position={position}")
        series = []
        title = "Line Scan"
        x_label = "X Position" if direction == "horizontal" else "Y Position"
        for key in self._selected_keys:
            debug_print(f"MultiPropertyPanel line series key={key}")
            grid = self._grid_cache.get(key)
            if grid is None:
                debug_print("MultiPropertyPanel line grid missing")
                continue
            x_grid, y_grid, z_grid = grid
            x_data, z_data, title, x_label = MultiViewPanel._extract_line_scan(
                x_grid,
                y_grid,
                z_grid,
                direction,
                position,
            )
            legend = self._property_legend(key)
            series.append({"name": legend, "x": x_data, "y": z_data})
            debug_print(f"MultiPropertyPanel line series added={legend}")
        debug_print(f"MultiPropertyPanel line series final count={len(series)}")
        return series, title, x_label

    def _build_histogram_series(self) -> tuple[list[dict], str]:
        debug_print("MultiPropertyPanel._build_histogram_series called")
        _freq_debug(f"build_hist selected_keys={list(getattr(self, '_selected_keys', []))}")
        _freq_debug(f"build_hist cache_keys={list(getattr(self, '_grid_cache', {}).keys())}")
        series = []
        for key in self._selected_keys:
            debug_print(f"MultiPropertyPanel histogram series key={key}")
            _freq_debug(f"build_hist checking key={key}")
            grid = self._grid_cache.get(key)
            if grid is None:
                debug_print("MultiPropertyPanel histogram grid missing")
                _freq_debug(f"build_hist missing grid key={key}")
                continue
            legend = self._property_legend(key)
            z_values = np.asarray(grid[2])
            finite_count = int(np.count_nonzero(np.isfinite(z_values)))
            _freq_debug(f"build_hist add key={key} legend={legend} shape={z_values.shape} finite={finite_count}")
            series.append({"name": legend, "values": grid[2]})
            debug_print(f"MultiPropertyPanel histogram series added={legend}")
        debug_print(f"MultiPropertyPanel histogram final count={len(series)}")
        _freq_debug(f"build_hist final_count={len(series)}")
        return series, "Value"

    def _property_legend(self, key: str) -> str:
        debug_print("MultiPropertyPanel._property_legend called")
        scalar_def = self._scalar_def_for_key(key)
        property_labels = getattr(self, "_property_labels", {})
        debug_print(f"MultiPropertyPanel property custom labels count={len(property_labels)}")
        legend = property_labels.get(key, scalar_def.get("label", key))
        debug_print(f"MultiPropertyPanel property legend key={key}")
        debug_print(f"MultiPropertyPanel property legend={legend}")
        return legend

    def _current_line_overlay(self):
        debug_print("MultiPropertyPanel._current_line_overlay called")
        line_mode_check = getattr(self, "line_mode_check", None)
        if line_mode_check is None or not line_mode_check.isChecked():
            debug_print("MultiPropertyPanel line overlay skipped: line mode off")
            return None
        show_line_check = getattr(self, "show_line_check", None)
        if show_line_check is not None and not show_line_check.isChecked():
            debug_print("MultiPropertyPanel line overlay skipped: show line off")
            return None
        direction = self._current_line_scan_direction()
        debug_print(f"MultiPropertyPanel line overlay direction={direction}")
        if direction == "horizontal" and self._line_scan_y is None:
            debug_print("MultiPropertyPanel line overlay skipped: no y yet")
            return None
        if direction == "vertical" and self._line_scan_x is None:
            debug_print("MultiPropertyPanel line overlay skipped: no x yet")
            return None
        overlay = Heatmap2DOrientation.line_overlay(direction, self._line_scan_x, self._line_scan_y)
        debug_print(f"MultiPropertyPanel line overlay={overlay}")
        return overlay

    def _sync_cells(self, *, reset_cell_widths: bool = True) -> None:
        debug_print("MultiPropertyPanel._sync_cells called")
        debug_print(f"MultiPropertyPanel reset cell widths={reset_cell_widths}")
        self._unlock_rows_widget_size()
        self._clear_row_widgets()
        for key, cell in list(self._cells.items()):
            if key not in self._selected_keys:
                debug_print(f"MultiPropertyPanel deleting cell key={key}")
                self._cells.pop(key)
                cell.deleteLater()
        columns = self._columns_for_count(len(self._selected_keys))
        debug_print(f"MultiPropertyPanel layout columns={columns}")
        for row, row_keys in enumerate(self._row_keys(columns)):
            bottom_row = row == 1
            row_widget = QWidget()
            row_widget.setObjectName("multiPropertyHeatmapRow")
            row_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            row_widget.setStyleSheet("QWidget#multiPropertyHeatmapRow { background: #ffffff; }")
            row_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(_CELL_GAP)
            row_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
            row_layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
            debug_print(f"MultiPropertyPanel creating row={row}")
            debug_print(f"MultiPropertyPanel row key count={len(row_keys)}")
            row_cells: list[MultiPropertyCell] = []
            for column, key in enumerate(row_keys):
                scalar_def = self._scalar_def_for_key(key)
                label = scalar_def.get("label", key)
                cell = self._cells.get(key)
                if cell is None:
                    debug_print(f"MultiPropertyPanel creating cell key={key}")
                    cell = MultiPropertyCell(key, label, bottom_row=bottom_row)
                    cell.select_requested.connect(self._select_property)
                    cell.remove_requested.connect(self._remove_property)
                    cell.renamed.connect(self._on_property_renamed)
                    cell.heatmap.heatmap_clicked.connect(self._handle_cell_click)
                    debug_print(f"MultiPropertyPanel heatmap click connected key={key}")
                    self._cells[key] = cell
                    debug_print(f"MultiPropertyPanel rename signal connected key={key}")
                else:
                    cell.set_bottom_row(bottom_row)
                if reset_cell_widths:
                    cell.set_cell_width(_CELL_W)
                    debug_print(f"MultiPropertyPanel reset cell width key={key}")
                else:
                    cell.updateGeometry()
                    debug_print(f"MultiPropertyPanel preserved rendered cell size key={key}")
                row_cells.append(cell)
                debug_print(f"MultiPropertyPanel placed key={key} row={row} column={column} bottom={bottom_row}")
            reference_cell = row_cells[0] if row_cells else None
            top_offset = reference_cell.heatmap_top_offset() if reference_cell else 0
            bottom_offset = reference_cell.heatmap_bottom_offset() if reference_cell else 0
            heatmap_height = reference_cell.heatmap.height() if reference_cell else _CANVAS_HEIGHT
            debug_print(f"MultiPropertyPanel logo top offset row={row} value={top_offset}")
            debug_print(f"MultiPropertyPanel logo bottom offset row={row} value={bottom_offset}")
            debug_print(f"MultiPropertyPanel logo heatmap height row={row} value={heatmap_height}")
            logo_band = self._make_logo_band(top_offset=top_offset, bottom_offset=bottom_offset, heatmap_height=heatmap_height)
            row_layout.addWidget(logo_band)
            debug_print(f"MultiPropertyPanel logo added row={row}")
            for cell in row_cells:
                row_layout.addWidget(cell)
                debug_print(f"MultiPropertyPanel row cell added key={cell.property_key}")
            self.rows_layout.addWidget(row_widget)
            self._row_widgets.append(row_widget)
            debug_print(f"MultiPropertyPanel row widget count={len(self._row_widgets)}")
            self._row_layouts.append(row_layout)
            debug_print(f"MultiPropertyPanel row layout count={len(self._row_layouts)}")
        self._lock_layout_sizes()
        self._sync_selected_bullets()
        self._sync_top_range_controls()
        self.empty_label.setVisible(not self._selected_keys)

    def _unlock_rows_widget_size(self) -> None:
        debug_print("MultiPropertyPanel._unlock_rows_widget_size called")
        self.rows_widget.setMinimumSize(0, 0)
        debug_print("MultiPropertyPanel rows minimum reset to 0x0")
        self.rows_widget.setMaximumSize(16777215, 16777215)
        debug_print("MultiPropertyPanel rows maximum reset to default limit")
        self.rows_widget.updateGeometry()
        debug_print("MultiPropertyPanel rows geometry update requested before rebuild")

    def _sync_selected_bullets(self) -> None:
        debug_print("MultiPropertyPanel._sync_selected_bullets called")
        for key, cell in self._cells.items():
            selected = key == self._active_key
            debug_print(f"MultiPropertyPanel bullet key={key}")
            debug_print(f"MultiPropertyPanel bullet selected={selected}")
            cell.set_selected(selected)

    def _clear_row_widgets(self) -> None:
        debug_print("MultiPropertyPanel._clear_row_widgets called")
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            row_widget = item.widget()
            if row_widget is None:
                continue
            row_layout = row_widget.layout()
            if row_layout is not None:
                while row_layout.count():
                    child_item = row_layout.takeAt(0)
                    child = child_item.widget()
                    if child is None:
                        continue
                    if isinstance(child, MultiPropertyCell):
                        child.setParent(self.rows_widget)
                        debug_print(f"MultiPropertyPanel preserved cell key={child.property_key}")
                    else:
                        child.deleteLater()
                        debug_print("MultiPropertyPanel deleted row helper widget")
            row_widget.deleteLater()
            debug_print("MultiPropertyPanel deleted row widget")
        self._row_widgets.clear()
        self._row_layouts.clear()
        debug_print("MultiPropertyPanel row layouts cleared")
        debug_print("MultiPropertyPanel row widgets cleared")

    def _lock_layout_sizes(self) -> None:
        debug_print("MultiPropertyPanel._lock_layout_sizes called")
        for index, row_widget in enumerate(self._row_widgets):
            row_height = row_widget.sizeHint().height()
            row_width = row_widget.sizeHint().width()
            debug_print(f"MultiPropertyPanel lock row index={index}")
            debug_print(f"MultiPropertyPanel lock row width={row_width}")
            debug_print(f"MultiPropertyPanel lock row height={row_height}")
            row_widget.setFixedSize(row_width, row_height)
            debug_print(f"MultiPropertyPanel row fixed width={row_widget.width()}")
            debug_print(f"MultiPropertyPanel row fixed height={row_widget.height()}")
        rows_size = self.rows_widget.sizeHint()
        debug_print(f"MultiPropertyPanel rows size hint width={rows_size.width()}")
        debug_print(f"MultiPropertyPanel rows size hint height={rows_size.height()}")
        self.rows_widget.setFixedSize(rows_size)
        debug_print(f"MultiPropertyPanel rows fixed width={self.rows_widget.width()}")
        debug_print(f"MultiPropertyPanel rows fixed height={self.rows_widget.height()}")

    def _row_keys(self, columns: int) -> list[list[str]]:
        debug_print("MultiPropertyPanel._row_keys called")
        safe_columns = max(1, int(columns))
        rows = [
            self._selected_keys[start:start + safe_columns]
            for start in range(0, len(self._selected_keys), safe_columns)
        ]
        debug_print(f"MultiPropertyPanel row count={len(rows)}")
        return rows

    def _make_logo_band(self, *, top_offset: int = 0, bottom_offset: int = 0, heatmap_height: int = _CANVAS_HEIGHT) -> QWidget:
        debug_print("MultiPropertyPanel._make_logo_band called")
        safe_top_offset = max(0, int(top_offset))
        safe_bottom_offset = max(0, int(bottom_offset))
        safe_heatmap_height = max(1, int(heatmap_height))
        total_height = safe_top_offset + safe_heatmap_height + safe_bottom_offset
        debug_print(f"MultiPropertyPanel logo top offset={safe_top_offset}")
        debug_print(f"MultiPropertyPanel logo bottom offset={safe_bottom_offset}")
        debug_print(f"MultiPropertyPanel logo heatmap height={safe_heatmap_height}")
        debug_print(f"MultiPropertyPanel logo wrapper height={total_height}")
        logo_w = QWidget()
        logo_w.setObjectName("multiPropertyLogoBand")
        logo_w.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        logo_w.setStyleSheet("QWidget#multiPropertyLogoBand { background: #ffffff; }")
        logo_w.setFixedSize(_LOGO_W, total_height)
        logo_w.setProperty("heatmapTopOffset", safe_top_offset)
        logo_w.setProperty("heatmapHeight", safe_heatmap_height)
        logo_w.setProperty("heatmapBottomOffset", safe_bottom_offset)
        logo_layout = QVBoxLayout(logo_w)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setSpacing(0)
        if safe_top_offset:
            logo_layout.addSpacing(safe_top_offset)
            debug_print("MultiPropertyPanel logo top spacer added")
        logo_lbl = QLabel()
        logo_lbl.setFixedSize(_LOGO_W, safe_heatmap_height)
        debug_print(f"MultiPropertyPanel logo path={HEATMAP_LOGO_PATH}")
        debug_print(f"MultiPropertyPanel logo exists={HEATMAP_LOGO_PATH.exists()}")
        if HEATMAP_LOGO_PATH.exists():
            px = QPixmap(str(HEATMAP_LOGO_PATH)).scaledToWidth(
                _LOGO_W - 8,
                Qt.TransformationMode.SmoothTransformation,
            )
            logo_lbl.setPixmap(px)
            debug_print(f"MultiPropertyPanel logo pixmap null={px.isNull()}")
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
        logo_layout.addWidget(logo_lbl)
        if safe_bottom_offset:
            logo_layout.addSpacing(safe_bottom_offset)
            debug_print("MultiPropertyPanel logo bottom spacer added")
        debug_print("MultiPropertyPanel logo band built")
        return logo_w

    def _render_all(self, *_) -> None:
        debug_print("MultiPropertyPanel._render_all called")
        file_path = self.file_combo.currentData()
        debug_print(f"MultiPropertyPanel file_path={file_path}")
        _freq_debug(f"render_all start file={file_path}")
        _freq_debug(f"render_all selected_keys={list(getattr(self, '_selected_keys', []))}")
        _freq_debug(f"render_all cell_keys={list(getattr(self, '_cells', {}).keys())}")
        if not file_path:
            self.status_label.setText("Select a file")
            self._set_analysis_visible(False)
            debug_print("MultiPropertyPanel render skipped no file")
            _freq_debug("render_all skipped no_file")
            return
        if not self._selected_keys:
            self.status_label.setText("Add properties")
            self._set_analysis_visible(False)
            debug_print("MultiPropertyPanel render skipped no properties")
            _freq_debug("render_all skipped no_properties")
            return
        try:
            reader = get_reader(file_path)
            axis = Heatmap2DOrientation.detect_axis(reader.dimensions)
            rotation_degrees = getattr(self, "_rotation_degrees", 0)
            debug_print(f"MultiPropertyPanel requested rotation={rotation_degrees}")
            orientation = Heatmap2DOrientation(rotation_degrees)
            debug_print(f"MultiPropertyPanel orientation rotation={rotation_degrees}")
            cmap = self._palette_cmap(self.palette_combo.currentData() or "aqua-fire")
            type_combo = getattr(self, "type_combo", None)
            debug_print(f"MultiPropertyPanel type combo present={type_combo is not None}")
            plot_type = type_combo.currentData() if type_combo is not None else "heatmap"
            plot_type = plot_type or "heatmap"
            debug_print(f"MultiPropertyPanel selected plot_type={plot_type}")
            raw_overlay_grid = self._build_overlay_grid(file_path, axis)
            debug_print(f"MultiPropertyPanel raw overlay present={raw_overlay_grid is not None}")
            overlay_grid = orientation.apply_overlay(raw_overlay_grid) if rotation_degrees else raw_overlay_grid
            debug_print(f"MultiPropertyPanel overlay rotation applied={bool(rotation_degrees and raw_overlay_grid is not None)}")
            debug_print(f"MultiPropertyPanel overlay present={overlay_grid is not None}")
            line_overlay = self._current_line_overlay()
            debug_print(f"MultiPropertyPanel line overlay present={line_overlay is not None}")
            debug_print(f"MultiPropertyPanel reader loaded axis={axis}")
            if not hasattr(self, "_grid_cache"):
                self._grid_cache = {}
                debug_print("MultiPropertyPanel grid cache initialized during render")
            self._grid_cache.clear()
            debug_print("MultiPropertyPanel grid cache cleared")
            _freq_debug("render_all grid_cache_cleared")
            for key in self._selected_keys:
                scalar_def = self._scalar_def_for_key(key)
                cell = self._cells.get(key)
                _freq_debug(
                    f"render_all property_start key={key} label={scalar_def.get('label')} "
                    f"array={scalar_def.get('array')} component={scalar_def.get('component')}"
                )
                if cell is None:
                    debug_print(f"MultiPropertyPanel missing cell key={key}")
                    _freq_debug(f"render_all missing_cell key={key}")
                    continue
                try:
                    x_grid, y_grid, z_grid, stats = reader.get_interpolated_slice(
                        axis=axis,
                        index=0,
                        scalar_name=scalar_def["array"],
                        component=scalar_def.get("component"),
                        resolution=DEFAULTS["interpolation_resolution"],
                    )
                    scale = scalar_def.get("scale", 1.0) or 1.0
                    property_labels = getattr(self, "_property_labels", {})
                    debug_print(f"MultiPropertyPanel custom label count={len(property_labels)}")
                    base_label = property_labels.get(key, scalar_def.get("label", key))
                    debug_print(f"MultiPropertyPanel base display label={base_label}")
                    extra_scale, display_label = self._get_display_params(scalar_def.get("label", key), override_label=base_label)
                    debug_print(f"MultiPropertyPanel scalar base scale={scale}")
                    debug_print(f"MultiPropertyPanel scalar extra scale={extra_scale}")
                    z_grid = np.asarray(z_grid, dtype=float) * scale * extra_scale
                    debug_print(f"MultiPropertyPanel display label={display_label}")
                    display = orientation.apply_grid(x_grid, y_grid, z_grid)
                    self._grid_cache[key] = (display.x, display.y, display.z)
                    debug_print(f"MultiPropertyPanel cached grid key={key}")
                    finite_count = int(np.count_nonzero(np.isfinite(display.z)))
                    _freq_debug(f"render_all cached key={key} cache_count={len(self._grid_cache)} finite={finite_count}")
                    data_min = float(np.nanmin(display.z))
                    data_max = float(np.nanmax(display.z))
                    debug_print(f"MultiPropertyPanel property={key}")
                    debug_print(f"MultiPropertyPanel data_min={data_min}")
                    debug_print(f"MultiPropertyPanel data_max={data_max}")
                    state = self._ranges.setdefault(key, {})
                    if "selected_min" not in state or "selected_max" not in state:
                        state["selected_min"] = data_min
                        state["selected_max"] = data_max
                        debug_print("MultiPropertyPanel initialized property range")
                    state["data_min"] = data_min
                    state["data_max"] = data_max
                    selected_min = float(state["selected_min"])
                    selected_max = float(state["selected_max"])
                    debug_print(f"MultiPropertyPanel selected_min={selected_min}")
                    debug_print(f"MultiPropertyPanel selected_max={selected_max}")
                    heatmap_width, heatmap_height = self._heatmap_size_for_grid(display.x, display.y)
                    debug_print(f"MultiPropertyPanel heatmap width={heatmap_width}")
                    debug_print(f"MultiPropertyPanel heatmap height={heatmap_height}")
                    cell.set_heatmap_size(heatmap_width, heatmap_height)
                    cell.render(
                        display.x,
                        display.y,
                        display.z,
                        cmap=cmap,
                        vmin=selected_min,
                        vmax=selected_max,
                        label=display_label,
                        plot_type=plot_type,
                        overlay_grid=overlay_grid,
                        line_overlay=line_overlay,
                    )
                except Exception as exc:
                    debug_print(f"MultiPropertyPanel property render failed key={key}: {exc}")
                    _freq_debug(f"render_all property_failed key={key} error={exc}")
                    cell.render_status(f"Could not render {scalar_def.get('label', key)}<br>{exc}")
            self._sync_cells(reset_cell_widths=False)
            _freq_debug(f"render_all after_sync selected={list(self._selected_keys)} cache_keys={list(self._grid_cache.keys())}")
            if hasattr(self, "line_scan_canvas") and hasattr(self, "histogram_canvas"):
                self._set_analysis_visible(True)
                debug_print("MultiPropertyPanel rendering analysis graphs")
                _freq_debug("render_all calling_render_analysis")
                self._render_analysis()
            else:
                debug_print("MultiPropertyPanel analysis render skipped no canvases")
                _freq_debug("render_all skipped no_analysis_canvases")
            self.status_label.setText(f"{len(self._selected_keys)} property/properties")
            debug_print("MultiPropertyPanel render complete")
            _freq_debug(f"render_all complete selected_count={len(self._selected_keys)} cache_count={len(self._grid_cache)}")
        except Exception as exc:
            self.status_label.setText("Could not load file")
            debug_print(f"MultiPropertyPanel render failed file={exc}")
            _freq_debug(f"render_all failed file_error={exc}")

    def _scalar_def_for_key(self, key: str) -> dict:
        debug_print("MultiPropertyPanel._scalar_def_for_key called")
        for scalar_def in self._scalar_defs:
            if scalar_def.get("value") == key:
                debug_print(f"MultiPropertyPanel scalar matched key={key}")
                return scalar_def
        debug_print(f"MultiPropertyPanel scalar fallback key={key}")
        return self._scalar_defs[0] if self._scalar_defs else {"label": key, "value": key, "array": key}

    def _build_overlay_grid(self, file_path: str, axis: str, *, resolution: int | None = None):
        debug_print("MultiPropertyPanel._build_overlay_grid called")
        requested_resolution = int(resolution or DEFAULTS["interpolation_resolution"])
        debug_print(f"MultiPropertyPanel overlay resolution={requested_resolution}")
        debug_print(f"MultiPropertyPanel overlay requested={self.interfaces_on.isChecked()}")
        if not self.interfaces_on.isChecked():
            debug_print("MultiPropertyPanel overlay skipped toggle off")
            return None
        phase_file = self._phase_overlay_file(file_path)
        debug_print(f"MultiPropertyPanel overlay phase_file={phase_file}")
        if not phase_file:
            debug_print("MultiPropertyPanel overlay skipped no PhaseField file")
            return None
        try:
            phase_reader = get_reader(str(phase_file))
            debug_print("MultiPropertyPanel overlay reader loaded")
            x_grid, y_grid, z_grid, _ = phase_reader.get_interpolated_slice(
                axis=axis,
                index=0,
                scalar_name="Interfaces",
                component=None,
                resolution=requested_resolution,
            )
            debug_print(f"MultiPropertyPanel overlay min={float(np.nanmin(z_grid))}")
            debug_print(f"MultiPropertyPanel overlay max={float(np.nanmax(z_grid))}")
            return {"x": x_grid, "y": y_grid, "z": np.asarray(z_grid)}
        except Exception as exc:
            debug_print(f"MultiPropertyPanel overlay build failed: {exc}")
            return None

    @staticmethod
    def _phase_overlay_file(file_path: str):
        debug_print("MultiPropertyPanel._phase_overlay_file called")
        if not file_path:
            debug_print("MultiPropertyPanel no file_path for phase overlay")
            return None
        path = Path(file_path)
        file_name = path.name
        debug_print(f"MultiPropertyPanel overlay source filename={file_name}")
        if file_name.startswith("PhaseField_"):
            debug_print("MultiPropertyPanel source is already PhaseField")
            return path
        suffix = file_name.split("_")[-1]
        debug_print(f"MultiPropertyPanel overlay suffix={suffix}")
        phase_candidate = path.with_name(f"PhaseField_{suffix}")
        debug_print(f"MultiPropertyPanel overlay PhaseField candidate={phase_candidate}")
        if phase_candidate.exists():
            debug_print("MultiPropertyPanel overlay using PhaseField candidate")
            return phase_candidate
        debug_print("MultiPropertyPanel overlay PhaseField candidate missing")
        if file_name.startswith("PhaseFieldDistorted_"):
            debug_print("MultiPropertyPanel source is PhaseFieldDistorted fallback")
            return path
        distorted_candidate = path.with_name(f"PhaseFieldDistorted_{suffix}")
        debug_print(f"MultiPropertyPanel overlay PhaseFieldDistorted candidate={distorted_candidate}")
        if distorted_candidate.exists():
            debug_print("MultiPropertyPanel overlay using PhaseFieldDistorted fallback")
            return distorted_candidate
        debug_print("MultiPropertyPanel overlay PhaseFieldDistorted fallback missing")
        return None

    @staticmethod
    def _columns_for_count(count: int) -> int:
        debug_print("MultiPropertyPanel._columns_for_count called")
        debug_print(f"MultiPropertyPanel property count={count}")
        if count <= 0:
            return 1
        if count <= 3:
            return count
        if count <= 4:
            return 2
        if count <= 6:
            return 3
        if count <= 8:
            return 4
        return 5

    @staticmethod
    def _heatmap_size_for_grid(x_grid, y_grid, *, max_width: int = _CELL_W, max_height: int = _CANVAS_HEIGHT) -> tuple[int, int]:
        debug_print("MultiPropertyPanel._heatmap_size_for_grid called")
        safe_max_width = max(1, int(max_width))
        safe_max_height = max(1, int(max_height))
        debug_print(f"MultiPropertyPanel max heatmap width={safe_max_width}")
        debug_print(f"MultiPropertyPanel max heatmap height={safe_max_height}")
        x_arr = np.asarray(x_grid, dtype=float)
        y_arr = np.asarray(y_grid, dtype=float)
        x_span = float(np.nanmax(x_arr) - np.nanmin(x_arr))
        y_span = float(np.nanmax(y_arr) - np.nanmin(y_arr))
        debug_print(f"MultiPropertyPanel x span={x_span}")
        debug_print(f"MultiPropertyPanel y span={y_span}")
        if not np.isfinite(x_span) or not np.isfinite(y_span) or x_span <= 0.0 or y_span <= 0.0:
            debug_print("MultiPropertyPanel invalid span, using default heatmap size")
            return safe_max_width, safe_max_height
        data_aspect = x_span / y_span
        box_aspect = safe_max_width / safe_max_height
        debug_print(f"MultiPropertyPanel data aspect={data_aspect}")
        debug_print(f"MultiPropertyPanel box aspect={box_aspect}")
        if data_aspect >= box_aspect:
            width = safe_max_width
            height = max(1, int(round(safe_max_width / data_aspect)))
            debug_print("MultiPropertyPanel width-limited heatmap")
        else:
            width = max(_MIN_CELL_W, int(round(safe_max_height * data_aspect)))
            height = safe_max_height
            debug_print("MultiPropertyPanel height-limited heatmap")
        debug_print(f"MultiPropertyPanel calculated heatmap width={width}")
        debug_print(f"MultiPropertyPanel calculated heatmap height={height}")
        return width, height
