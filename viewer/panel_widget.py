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
    QSizePolicy,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from viewer.animation_player import AnimationPlayer

from app.debug import debug_print
from app.resources import HEATMAP_LOGO_PATH
from utils.combo_box_utils import update_combo_popup_width
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
        heatmap_widget: QWidget,
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
        self.heatmap_canvas  = HeatmapCanvas()
        self.line_scan_canvas = LineScanCanvas()
        self.histogram_canvas = HistogramCanvas()
        self.line_mode_check = ToggleSwitchWidget("Line Scan", checked=False)
        self.show_line_check = ToggleSwitchWidget("Show Line", checked=False)
        self.direction_combo = QComboBox()
        self.direction_combo.setObjectName("viewerCombo")
        self.direction_combo.addItem(
            QIcon(str(self._ASSETS / "Horizontal.png")), "Horizontal", "horizontal"
        )
        self.direction_combo.addItem(
            QIcon(str(self._ASSETS / "Vertical.png")), "Vertical", "vertical"
        )
        self.direction_combo.setIconSize(QSize(18, 18))
        update_combo_popup_width(self.direction_combo)
        self.histogram_bins_slider = QSlider()
        self.histogram_bins_slider.setOrientation(self.controls_widget.slice_slider.orientation())
        self.histogram_bins_slider.setRange(10, 200)
        self.histogram_bins_slider.setValue(30)

        self.interfaces_check = ToggleSwitchWidget("Interfaces Overlay", checked=False)
        self.colorbar_label_edit = QLineEdit()
        self.colorbar_label_edit.setPlaceholderText("Colorbar label…")
        self.colorbar_label_edit.setObjectName("viewerLineEdit")
        self.colorbar_label_edit.setMinimumWidth(72)
        debug_print("PanelWidget colorbar label min width set to 72")

        # Timeline row widgets
        self.first_frame_btn = self._make_playback_button("black_first.png", "First frame")
        self.previous_frame_btn = self._make_playback_button("black_previous.png", "Previous frame")
        self.next_frame_btn = self._make_playback_button("black_fast-forward.png", "Next frame")
        self.last_frame_btn = self._make_playback_button("black_last.png", "Last frame")
        self.playback_slider = QSlider(Qt.Orientation.Horizontal)
        self.playback_slider.setRange(0, 0)
        self.frame_label = QLabel("– / –")
        self.frame_label.setObjectName("mutedInfo")
        self.frame_label.setMinimumWidth(52)
        self.animate_btn = QPushButton("▶  Animate")
        self.animate_btn.setFixedHeight(28)
        self.animate_btn.setObjectName("playbackBtn")
        self.unit_scale_combo = QComboBox()
        self.unit_scale_combo.setObjectName("viewerCombo")
        self.unit_scale_combo.addItem("Raw",     (1.0,   ""))
        self.unit_scale_combo.addItem("% ×100",  (100.0, ""))
        self.unit_scale_combo.addItem("M ÷1e6",  (1e-6,  ""))
        self.unit_scale_combo.addItem("G ÷1e9",  (1e-9,  ""))
        update_combo_popup_width(self.unit_scale_combo)
        self.export_button = QPushButton(
            QIcon(str(self._ASSETS / "download.png")), "Export"
        )
        self.export_button.setIconSize(QSize(16, 16))
        self.export_button.setProperty("subtle", True)
        self.logo_label = QLabel()
        self.heatmap_status_label = QLabel("Heatmap waiting for controller")
        self.heatmap_status_label.setObjectName("mutedInfo")
        self.heatmap_status_label.setWordWrap(True)
        self._heatmap_toolbar_mode = ""
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

        # Timeline slider wiring
        self._sync_playback_frame_count()
        self.playback_slider.valueChanged.connect(self._on_slider_value_changed)
        self.first_frame_btn.clicked.connect(lambda: self._jump_to_frame(0))
        self.previous_frame_btn.clicked.connect(lambda: self._jump_to_frame(self.playback_slider.value() - 1))
        self.next_frame_btn.clicked.connect(lambda: self._jump_to_frame(self.playback_slider.value() + 1))
        self.last_frame_btn.clicked.connect(lambda: self._jump_to_frame(self.playback_slider.maximum()))
        self.animate_btn.clicked.connect(self._open_animation_player)

        # Keep slider in sync when user manually picks a file
        self.controls_widget.file_combo.currentIndexChanged.connect(
            self._on_file_combo_changed
        )
        debug_print("PanelWidget.__init__ complete")

    # ------------------------------------------------------------------
    # Playback handlers
    # ------------------------------------------------------------------

    def _make_playback_button(self, icon_name: str, tooltip: str) -> QPushButton:
        button = QPushButton()
        button.setObjectName("playbackTransportButton")
        button.setToolTip(tooltip)
        button.setFixedSize(34, 30)
        button.setIcon(QIcon(str(self._ASSETS / icon_name)))
        button.setIconSize(QSize(20, 20))
        return button

    def _sync_playback_frame_count(self) -> None:
        n = self.controller.get_file_count()
        self.playback_slider.setRange(0, max(0, n - 1))
        self.frame_label.setText(f"1 / {n}" if n > 0 else "– / –")
        self._update_playback_buttons()

    def _on_slider_value_changed(self, index: int) -> None:
        n = self.playback_slider.maximum() + 1
        self.frame_label.setText(f"{index + 1} / {n}")
        if self.controls_widget.file_combo.currentIndex() != index:
            self.controls_widget.file_combo.setCurrentIndex(index)
        self._update_playback_buttons()

    def _on_file_combo_changed(self, index: int) -> None:
        self.playback_slider.blockSignals(True)
        self.playback_slider.setValue(index)
        self.playback_slider.blockSignals(False)
        n = self.playback_slider.maximum() + 1
        self.frame_label.setText(f"{index + 1} / {n}" if n > 0 else "– / –")
        self._update_playback_buttons()

    def _jump_to_frame(self, index: int) -> None:
        maximum = self.playback_slider.maximum()
        if maximum < 0:
            return
        target = max(0, min(index, maximum))
        self.controls_widget.file_combo.setCurrentIndex(target)

    def _update_playback_buttons(self) -> None:
        maximum = self.playback_slider.maximum()
        current = self.playback_slider.value()
        has_frames = maximum >= 0 and self.controller.get_file_count() > 0
        for button in (
            self.first_frame_btn,
            self.previous_frame_btn,
            self.next_frame_btn,
            self.last_frame_btn,
        ):
            button.setEnabled(has_frames)
        self.first_frame_btn.setEnabled(has_frames and current > 0)
        self.previous_frame_btn.setEnabled(has_frames and current > 0)
        self.next_frame_btn.setEnabled(has_frames and current < maximum)
        self.last_frame_btn.setEnabled(has_frames and current < maximum)

    def _open_animation_player(self) -> None:
        combo = self.controls_widget.file_combo
        file_paths = [combo.itemData(i) for i in range(combo.count())]
        file_paths = [p for p in file_paths if p]
        if not file_paths:
            return
        scalar_def = self.controller._get_scalar_def(
            self.controls_widget.current_scalar_key()
        )
        if scalar_def is None:
            return
        state = self.controller.state
        _, colorbar_label = self.controller._get_display_params(
            self.controls_widget.current_scalar_label()
        )
        dlg = AnimationPlayer(
            file_paths=file_paths,
            scalar_def=scalar_def,
            axis=state.axis,
            slice_index=state.slice_index,
            palette=state.palette,
            vmin=state.range_min,
            vmax=state.range_max,
            colorbar_label=colorbar_label,
            interfaces_overlay=self.interfaces_check.isChecked(),
            parent=self,
        )
        dlg.show()

    def _build_ui(self) -> None:
        debug_print("PanelWidget._build_ui called")
        left_col    = QWidget()
        left_layout = QVBoxLayout(left_col)
        self.left_column_layout = left_layout
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        left_layout.addWidget(self.controls_widget)
        self.heatmap_card = self._build_heatmap_card()
        left_layout.addWidget(self.heatmap_card, 1)

        self.analysis_card = self._build_analysis_card()
        right_col = QWidget()
        right_layout = QVBoxLayout(right_col)
        self.right_column_layout = right_layout
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self.analysis_card, 1)

        left_col.setMinimumWidth(300)
        debug_print("PanelWidget left column min width set to 300")
        right_col.setMinimumWidth(420)
        self.analysis_card.setMinimumWidth(420)
        debug_print("PanelWidget analysis card min width set to 420")
        self.analysis_card.setMaximumWidth(720)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.addWidget(left_col)
        self._splitter.addWidget(right_col)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 8, 8)
        main_layout.setSpacing(0)
        main_layout.addWidget(self._splitter)
        debug_print("PanelWidget layout ready")

    def set_available_width(self, width: int) -> None:
        """Constrain panel content to the current app content width."""
        debug_print(f"PanelWidget.set_available_width width={width}")
        bounded_width = max(0, int(width))
        self.setMinimumWidth(0)
        self.setMaximumWidth(bounded_width)
        self.controls_widget.set_available_width(max(0, bounded_width - 16))
        self.heatmap_card.setMaximumWidth(bounded_width)
        self.analysis_card.setMaximumWidth(bounded_width)
        self._update_heatmap_toolbar_mode(max(0, bounded_width - 56))
        self.line_scan_canvas.set_available_width(max(240, bounded_width - 72))
        self.histogram_canvas.set_available_width(max(240, bounded_width - 72))
        self._splitter.setMaximumWidth(bounded_width)
        debug_print(f"PanelWidget max width applied={bounded_width}")

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        orientation = (
            Qt.Orientation.Vertical
            if event.size().width() < 980
            else Qt.Orientation.Horizontal
        )
        self._splitter.setOrientation(orientation)
        self._update_heatmap_toolbar_mode(event.size().width())

    def _build_heatmap_card(self) -> QWidget:
        debug_print("PanelWidget._build_heatmap_card called")
        card = QWidget()
        card.setObjectName("viewerCard")
        card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Topbar: dataset title + actions
        self.heatmap_toolbar = QWidget()
        self.heatmap_toolbar.setObjectName("toolbarStrip")
        self.heatmap_toolbar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.heatmap_toolbar_layout = QVBoxLayout(self.heatmap_toolbar)
        self.heatmap_toolbar_layout.setContentsMargins(12, 5, 12, 5)
        self.heatmap_toolbar_layout.setSpacing(6)
        self.heatmap_toolbar_primary_row = QWidget()
        self.heatmap_toolbar_primary_layout = QHBoxLayout(self.heatmap_toolbar_primary_row)
        self.heatmap_toolbar_primary_layout.setContentsMargins(0, 0, 0, 0)
        self.heatmap_toolbar_primary_layout.setSpacing(12)
        self.heatmap_toolbar_secondary_row = QWidget()
        self.heatmap_toolbar_secondary_layout = QHBoxLayout(self.heatmap_toolbar_secondary_row)
        self.heatmap_toolbar_secondary_layout.setContentsMargins(0, 0, 0, 0)
        self.heatmap_toolbar_secondary_layout.setSpacing(12)
        self.heatmap_toolbar_layout.addWidget(self.heatmap_toolbar_primary_row)
        self.heatmap_toolbar_layout.addWidget(self.heatmap_toolbar_secondary_row)
        self.colorbar_label_caption = QLabel("Label:")
        self.colorbar_label_caption.setObjectName("mutedInfo")
        self._apply_heatmap_toolbar_mode("wide", force=True)
        layout.addWidget(self.heatmap_toolbar)

        # Timeline row: transport buttons, slider, frame label, Animate
        playback_row = QHBoxLayout()
        playback_row.setContentsMargins(0, 2, 0, 2)
        playback_row.setSpacing(6)
        for button in (
            self.first_frame_btn,
            self.previous_frame_btn,
            self.next_frame_btn,
            self.last_frame_btn,
        ):
            playback_row.addWidget(button)
        playback_row.addSpacing(4)
        playback_row.addWidget(self.playback_slider, 1)
        playback_row.addWidget(self.frame_label)
        playback_row.addWidget(self.animate_btn)
        layout.addLayout(playback_row)

        # heatmap-row: [logo] [centered heatmap], bottom aligned by canvas height
        logo_card = QWidget()
        logo_path = HEATMAP_LOGO_PATH
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

    def _clear_toolbar_layout(self, target_layout: QHBoxLayout) -> None:
        debug_print("PanelWidget._clear_toolbar_layout called")
        while target_layout.count():
            item = target_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(self.heatmap_toolbar)
                debug_print(
                    "PanelWidget temporarily removed toolbar widget "
                    f"{widget.objectName() or widget.__class__.__name__}"
                )

    def _apply_heatmap_toolbar_mode(self, mode: str, *, force: bool = False) -> None:
        debug_print("PanelWidget._apply_heatmap_toolbar_mode called")
        if mode == self._heatmap_toolbar_mode and not force:
            debug_print(f"PanelWidget heatmap toolbar mode unchanged={mode}")
            self._debug_heatmap_toolbar("unchanged")
            return
        debug_print(
            f"PanelWidget changing heatmap toolbar mode from={self._heatmap_toolbar_mode} to={mode}"
        )
        self._clear_toolbar_layout(self.heatmap_toolbar_primary_layout)
        self._clear_toolbar_layout(self.heatmap_toolbar_secondary_layout)
        self.heatmap_toolbar_primary_layout.addWidget(self.colorbar_label_caption)
        self.heatmap_toolbar_primary_layout.addWidget(self.colorbar_label_edit, 1)
        self.heatmap_toolbar_primary_layout.addWidget(self.unit_scale_combo)
        if mode == "compact":
            debug_print("PanelWidget applying compact heatmap toolbar")
            self.heatmap_toolbar_secondary_layout.addStretch(1)
            self.heatmap_toolbar_secondary_layout.addWidget(self.interfaces_check)
            self.heatmap_toolbar_secondary_layout.addWidget(self.export_button)
            self.heatmap_toolbar.setFixedHeight(82)
            self.heatmap_toolbar_secondary_row.show()
        else:
            debug_print("PanelWidget applying wide heatmap toolbar")
            self.heatmap_toolbar_primary_layout.addStretch(1)
            self.heatmap_toolbar_primary_layout.addWidget(self.interfaces_check)
            self.heatmap_toolbar_primary_layout.addWidget(self.export_button)
            self.heatmap_toolbar.setFixedHeight(44)
            self.heatmap_toolbar_secondary_row.hide()
        self._heatmap_toolbar_mode = mode
        self.heatmap_toolbar.updateGeometry()
        self._debug_heatmap_toolbar("applied")

    def _update_heatmap_toolbar_mode(self, width: int) -> None:
        debug_print("PanelWidget._update_heatmap_toolbar_mode called")
        bounded_width = max(0, int(width))
        mode = "compact" if bounded_width and bounded_width < 620 else "wide"
        debug_print(f"PanelWidget heatmap toolbar width={bounded_width}")
        debug_print(f"PanelWidget heatmap toolbar selected mode={mode}")
        self._apply_heatmap_toolbar_mode(mode)

    def _debug_heatmap_toolbar(self, reason: str) -> None:
        debug_print(f"PanelWidget._debug_heatmap_toolbar reason={reason}")
        debug_print(f"PanelWidget heatmap toolbar mode={self._heatmap_toolbar_mode}")
        debug_print(f"PanelWidget heatmap toolbar width={self.heatmap_toolbar.width()}")
        debug_print(f"PanelWidget heatmap toolbar height={self.heatmap_toolbar.height()}")
        debug_print(
            "PanelWidget heatmap primary min="
            f"{self.heatmap_toolbar_primary_layout.minimumSize().width()}"
        )
        debug_print(
            "PanelWidget heatmap secondary min="
            f"{self.heatmap_toolbar_secondary_layout.minimumSize().width()}"
        )

    def _build_analysis_card(self) -> QWidget:
        debug_print("PanelWidget._build_analysis_card called")
        card = QWidget()
        card.setObjectName("viewerCard")
        card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        chart_icon = QLabel()
        chart_pixmap = QPixmap(str(self._ASSETS / "bar-chart.png")).scaledToHeight(
            20, Qt.TransformationMode.SmoothTransformation
        )
        chart_icon.setPixmap(chart_pixmap)
        title_label = QLabel("Analysis")
        title_label.setObjectName("sectionTitle")
        title_row.addWidget(chart_icon)
        title_row.addWidget(title_label)
        title_row.addStretch(1)
        layout.addLayout(title_row)

        self.line_card = QWidget()
        self.line_card.setObjectName("innerCard")
        self.line_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        line_layout = QVBoxLayout(self.line_card)
        line_layout.setContentsMargins(10, 8, 10, 8)
        line_layout.setSpacing(6)
        line_title = QLabel("Line Scan")
        line_title.setObjectName("sectionTitle")
        line_layout.addWidget(line_title)
        self.line_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.line_toolbar = QWidget()
        self.line_toolbar.setObjectName("toolbarStrip")
        self.line_toolbar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.line_toolbar.setFixedHeight(44)
        line_toolbar_layout = QHBoxLayout(self.line_toolbar)
        line_toolbar_layout.setContentsMargins(0, 0, 0, 0)
        line_toolbar_layout.setSpacing(12)
        line_toolbar_layout.addWidget(self.line_mode_check)
        line_toolbar_layout.addWidget(self.show_line_check)
        scan_dir_label = QLabel("Direction:")
        scan_dir_label.setObjectName("mutedInfo")
        line_toolbar_layout.addWidget(scan_dir_label)
        line_toolbar_layout.addWidget(self.direction_combo)
        line_toolbar_layout.addStretch(1)
        line_layout.addWidget(self.line_toolbar)
        line_layout.addWidget(self.line_scan_canvas, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.line_card)

        self.histogram_card = QWidget()
        self.histogram_card.setObjectName("innerCard")
        self.histogram_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.histogram_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        histogram_layout = QVBoxLayout(self.histogram_card)
        histogram_layout.setContentsMargins(10, 8, 10, 8)
        histogram_layout.setSpacing(6)
        histogram_title = QLabel("Histogram")
        histogram_title.setObjectName("sectionTitle")
        histogram_layout.addWidget(histogram_title)
        bins_row = QHBoxLayout()
        bins_row.setSpacing(8)
        bins_label = QLabel("Bins:")
        bins_label.setObjectName("mutedInfo")
        bins_row.addStretch(1)
        bins_row.addWidget(bins_label)
        bins_row.addWidget(self.histogram_bins_slider, 2)
        histogram_layout.addLayout(bins_row)
        histogram_layout.addWidget(self.histogram_canvas, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.histogram_card)
        layout.addStretch(1)

        return card
