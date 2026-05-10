"""Composition widget for one dataset panel."""

from pathlib import Path

from PySide6.QtGui import QIcon, QPixmap, QResizeEvent
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.debug import debug_print
from viewer.heatmap_canvas import HeatmapCanvas
from viewer.heatmap_controller import HeatmapController
from viewer.histogram_canvas import HistogramCanvas
from viewer.line_scan_canvas import LineScanCanvas
from viewer.panel_controls_widget import PanelControlsWidget
from viewer.toggle_switch_widget import ToggleSwitchWidget


class HeatmapAlignmentRow(QWidget):
    """Position logo and heatmap from the heatmap center."""

    def __init__(
        self,
        logo_widget: QWidget,
        heatmap_widget: HeatmapCanvas,
        *,
        gap: int = 8,
    ) -> None:
        debug_print("HeatmapAlignmentRow.__init__ start")
        super().__init__()
        self._logo_widget = logo_widget
        self._heatmap_widget = heatmap_widget
        self._gap = gap
        self._logo_widget.setParent(self)
        self._heatmap_widget.setParent(self)
        self._heatmap_widget.geometry_changed.connect(self._refresh_layout)
        self.setMinimumHeight(self._row_height())
        self._refresh_layout()
        debug_print("HeatmapAlignmentRow.__init__ complete")

    def _row_height(self) -> int:
        debug_print("HeatmapAlignmentRow._row_height called")
        return max(
            self._logo_widget.sizeHint().height(),
            self._heatmap_widget.height(),
        )

    def _refresh_layout(self) -> None:
        debug_print("HeatmapAlignmentRow._refresh_layout called")
        row_height = self._row_height()
        self.setMinimumHeight(row_height)
        self.setMaximumHeight(row_height)
        self.updateGeometry()
        self._position_children()
        debug_print("HeatmapAlignmentRow layout refresh complete")

    def resizeEvent(self, event) -> None:  # noqa: N802
        debug_print("HeatmapAlignmentRow.resizeEvent called")
        super().resizeEvent(event)
        self._position_children()
        debug_print("HeatmapAlignmentRow resize handled")

    def _position_children(self) -> None:
        debug_print("HeatmapAlignmentRow._position_children called")
        row_height = self._row_height()
        heatmap_width = self._heatmap_widget.width()
        heatmap_height = self._heatmap_widget.height()
        logo_width = self._logo_widget.width()
        logo_height = self._logo_widget.height()
        heatmap_x = max(0, int((self.width() - heatmap_width) / 2))
        heatmap_y = row_height - heatmap_height
        logo_x = heatmap_x - self._gap - logo_width
        logo_y = max(0, row_height - logo_height - 12)
        debug_print(f"HeatmapAlignmentRow row_height={row_height}")
        debug_print(f"HeatmapAlignmentRow heatmap_x={heatmap_x}")
        debug_print(f"HeatmapAlignmentRow logo_x={logo_x}")
        self._heatmap_widget.setGeometry(heatmap_x, heatmap_y, heatmap_width, heatmap_height)
        self._logo_widget.setGeometry(logo_x, logo_y, logo_width, logo_height)
        self.setMinimumHeight(row_height)
        self.setMaximumHeight(row_height)
        debug_print("HeatmapAlignmentRow child geometry applied")


class PanelWidget(QWidget):
    """Compose controls, canvas, and controller into one panel."""

    file_loaded = Signal(str)  # emitted with file_path whenever a VTK file is loaded

    _ASSETS = Path(__file__).parent.parent / "assets"

    def __init__(self, dataset_info: dict, projects: dict | None = None) -> None:
        debug_print("PanelWidget.__init__ start")
        super().__init__()
        self.dataset_info = dataset_info
        self.projects = projects or {}
        self.controls_widget = PanelControlsWidget(dataset_info)
        self.heatmap_canvas = HeatmapCanvas()
        self.line_scan_canvas = LineScanCanvas()
        self.histogram_canvas = HistogramCanvas()
        self.line_mode_check = ToggleSwitchWidget("Line Scan", checked=False)
        self.show_line_check = ToggleSwitchWidget("Show Line", checked=True)
        self.direction_combo = QComboBox()
        self.direction_combo.setObjectName("viewerCombo")
        self.direction_combo.addItem(
            QIcon(str(self._ASSETS / "Horizontal.png")), "Horizontal", "horizontal"
        )
        self.direction_combo.addItem(
            QIcon(str(self._ASSETS / "Vertical.png")), "Vertical", "vertical"
        )
        self.direction_combo.setIconSize(QSize(18, 18))
        self.histogram_field_combo = QComboBox()
        self.histogram_field_combo.setObjectName("viewerCombo")
        self.histogram_bins_slider = QSlider()
        self.histogram_bins_slider.setOrientation(self.controls_widget.slice_slider.orientation())
        self.histogram_bins_slider.setRange(10, 200)
        self.histogram_bins_slider.setValue(30)

        self.interfaces_check = ToggleSwitchWidget("Interfaces Overlay", checked=False)
        self.colorbar_label_edit = QLineEdit()
        self.colorbar_label_edit.setPlaceholderText("Colorbar label…")
        self.colorbar_label_edit.setObjectName("viewerLineEdit")
        self.colorbar_label_edit.setFixedWidth(140)
        self.unit_scale_combo = QComboBox()
        self.unit_scale_combo.setObjectName("viewerCombo")
        self.unit_scale_combo.addItem("Raw",     (1.0,   ""))
        self.unit_scale_combo.addItem("% ×100",  (100.0, ""))
        self.unit_scale_combo.addItem("M ÷1e6",  (1e-6,  ""))
        self.unit_scale_combo.addItem("G ÷1e9",  (1e-9,  ""))
        self.export_button = QPushButton(
            QIcon(str(self._ASSETS / "download.png")), "Export"
        )
        self.export_button.setIconSize(QSize(16, 16))
        self.export_button.setProperty("subtle", True)
        self.logo_label = QLabel()
        self.heatmap_status_label = QLabel("Heatmap waiting for controller")
        self.heatmap_status_label.setObjectName("mutedInfo")
        self.heatmap_status_label.setWordWrap(True)
        self._build_ui()
        self.heatmap_canvas.status_changed.connect(self.heatmap_status_label.setText)
        self.controller = HeatmapController(
            controls_widget=self.controls_widget,
            heatmap_canvas=self.heatmap_canvas,
            line_scan_canvas=self.line_scan_canvas,
            histogram_canvas=self.histogram_canvas,
            line_mode_check=self.line_mode_check,
            show_line_check=self.show_line_check,
            direction_combo=self.direction_combo,
            histogram_field_combo=self.histogram_field_combo,
            histogram_bins_slider=self.histogram_bins_slider,
            interfaces_check=self.interfaces_check,
            export_button=self.export_button,
            colorbar_label_edit=self.colorbar_label_edit,
            unit_scale_combo=self.unit_scale_combo,
            dataset_info=dataset_info,
        )
        self.controller._file_loaded_callback = self.file_loaded.emit
        self.controller.connect_signals()
        self.controller.refresh_view()
        debug_print("PanelWidget.__init__ complete")

    def _build_ui(self) -> None:
        debug_print("PanelWidget._build_ui called")
        left_col    = QWidget()
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        left_layout.addWidget(self.controls_widget)
        self.heatmap_card = self._build_heatmap_card()
        left_layout.addWidget(self.heatmap_card, 1)

        self.analysis_card = self._build_analysis_card()

        left_col.setMinimumWidth(420)
        self.analysis_card.setMinimumWidth(520)
        self.analysis_card.setMaximumWidth(720)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.addWidget(left_col)
        self._splitter.addWidget(self.analysis_card)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(0)
        main_layout.addWidget(self._splitter)
        debug_print("PanelWidget layout ready")

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        orientation = (
            Qt.Orientation.Vertical
            if event.size().width() < 980
            else Qt.Orientation.Horizontal
        )
        self._splitter.setOrientation(orientation)

    def _build_heatmap_card(self) -> QWidget:
        debug_print("PanelWidget._build_heatmap_card called")
        card = QWidget()
        card.setObjectName("viewerCard")
        card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Topbar: dataset title + actions
        toolbar = QWidget()
        toolbar.setObjectName("toolbarStrip")
        toolbar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        toolbar.setFixedHeight(44)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(12, 0, 12, 0)
        toolbar_layout.setSpacing(12)
        cb_label = QLabel("Label:")
        cb_label.setObjectName("mutedInfo")
        toolbar_layout.addWidget(cb_label)
        toolbar_layout.addWidget(self.colorbar_label_edit)
        toolbar_layout.addWidget(self.unit_scale_combo)
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(self.interfaces_check)
        toolbar_layout.addWidget(self.export_button)
        layout.addWidget(toolbar)

        # heatmap-row: [logo] [centered heatmap], bottom aligned by canvas height
        logo_card = QWidget()
        logo_path = Path(__file__).parent.parent / "assets" / "OP_Logo.png"
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path)).scaledToWidth(
                52, Qt.TransformationMode.SmoothTransformation
            )
            self.logo_label.setPixmap(pixmap)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
        self.logo_label.setParent(logo_card)
        logo_card.setFixedWidth(58)
        logo_card.setFixedHeight(self.heatmap_canvas.canvas_height())
        logo_width = logo_card.width()
        logo_height = self.logo_label.sizeHint().height()
        logo_y = max(0, logo_card.height() - logo_height - 12)
        self.logo_label.setGeometry(0, logo_y, logo_width, logo_height)
        self.logo_label.setFixedWidth(logo_width)
        self.heatmap_row = HeatmapAlignmentRow(
            logo_card,
            self.heatmap_canvas,
        )
        self.heatmap_row.setMinimumHeight(self.heatmap_canvas.canvas_height())
        self.heatmap_row.setMaximumHeight(self.heatmap_canvas.canvas_height())
        layout.addSpacing(24)
        layout.addWidget(self.heatmap_row)
        layout.addWidget(self.heatmap_status_label)
        return card

    def _build_analysis_card(self) -> QWidget:
        debug_print("PanelWidget._build_analysis_card called")
        card = QWidget()
        card.setObjectName("viewerCard")
        card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        chart_icon = QLabel()
        chart_pixmap = QPixmap(str(self._ASSETS / "bar-chart.png")).scaledToHeight(
            20, Qt.TransformationMode.SmoothTransformation
        )
        chart_icon.setPixmap(chart_pixmap)
        title_label = QLabel("Line Scan & Histogram Analysis")
        title_label.setObjectName("sectionTitle")
        title_row.addWidget(chart_icon)
        title_row.addWidget(title_label)
        title_row.addStretch(1)
        layout.addLayout(title_row)

        line_card = QWidget()
        line_card.setObjectName("innerCard")
        line_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        line_layout = QVBoxLayout(line_card)
        line_layout.setContentsMargins(12, 12, 12, 12)
        line_layout.setSpacing(10)
        line_toolbar = QWidget()
        line_toolbar.setObjectName("toolbarStrip")
        line_toolbar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        line_toolbar_layout = QHBoxLayout(line_toolbar)
        line_toolbar_layout.setContentsMargins(0, 0, 0, 0)
        line_toolbar_layout.setSpacing(12)
        line_toolbar_layout.addWidget(self.line_mode_check)
        line_toolbar_layout.addWidget(self.show_line_check)
        scan_dir_label = QLabel("Direction:")
        scan_dir_label.setObjectName("mutedInfo")
        line_toolbar_layout.addWidget(scan_dir_label)
        line_toolbar_layout.addWidget(self.direction_combo)
        line_toolbar_layout.addStretch(1)
        line_layout.addWidget(line_toolbar)
        line_layout.addWidget(self.line_scan_canvas, 1, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(line_card, 1)

        histogram_controls = QWidget()
        histogram_controls.setObjectName("innerCard")
        histogram_controls.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        histogram_controls_layout = QHBoxLayout(histogram_controls)
        histogram_controls_layout.setContentsMargins(12, 12, 12, 12)
        histogram_controls_layout.setSpacing(12)
        histogram_controls_layout.addWidget(QLabel("Histogram Field"))
        histogram_controls_layout.addWidget(self.histogram_field_combo, 1)
        histogram_controls_layout.addWidget(QLabel("Number of Bins"))
        histogram_controls_layout.addWidget(self.histogram_bins_slider, 1)
        layout.addWidget(histogram_controls)

        histogram_card = QWidget()
        histogram_card.setObjectName("innerCard")
        histogram_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        histogram_layout = QVBoxLayout(histogram_card)
        histogram_layout.setContentsMargins(12, 12, 12, 12)
        histogram_layout.addWidget(self.histogram_canvas, 1, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(histogram_card, 1)

        return card
