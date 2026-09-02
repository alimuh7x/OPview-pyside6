"""One Multi View comparison panel (one tab)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.debug import debug_print
from app.resources import HEATMAP_LOGO_PATH
from config.constants import DEFAULTS, PALETTES
from multi_view.colorbar_canvas import ColorbarCanvas, _W as _CB_W
from multi_view.multi_view_cell import MultiViewCell, MultiViewHeader, _CELL_W
from utils.combo_box_utils import update_combo_popup_width
from utils.time_series import compact_timestep_label
from utils.vtk_utils import get_reader
from viewer.colorscale import make_dynamic_colormap, palette_to_cmap
from viewer.histogram_canvas import HistogramCanvas
from viewer.heatmap_canvas import _CANVAS_HEIGHT
from viewer.heatmap_orientation import Heatmap2DOrientation
from viewer.line_scan_canvas import LineScanCanvas
from viewer.range_slider_widget import RangeSliderWidget
from viewer.toggle_switch_widget import ToggleSwitchWidget

_ASSETS = Path(__file__).resolve().parent.parent / "assets"
_LOGO_W = 58


class MultiViewPanel(QWidget):
    """Side-by-side heatmap comparison with shared controls."""

    def __init__(self, dataset_info: dict, parent=None) -> None:
        super().__init__(parent)
        debug_print("MultiViewPanel.__init__ start")
        self._dataset_info       = dataset_info
        debug_print(f"MultiViewPanel dataset label={dataset_info.get('label')}")
        self._scalar_defs        = self._build_scalar_defs(dataset_info)
        debug_print(f"MultiViewPanel scalar_defs count={len(self._scalar_defs)}")
        self._available_projects = dataset_info.get("available_projects", [])
        debug_print(f"MultiViewPanel available_projects count={len(self._available_projects)}")
        self._columns: dict[str, tuple[MultiViewHeader, MultiViewCell]] = {}
        self._legend_names: dict[str, str] = {}
        self._grid_cache: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
        self._histogram_cache: dict[tuple[str, str], np.ndarray] = {}
        self._click_count = 0
        self._first_click_value: float | None = None
        self._last_selected_range: tuple[float, float] | None = None
        self._line_scan_y: float | None = None
        self._line_scan_x: float | None = None
        self._line_scan_direction = "horizontal"
        self._available_width: int | None = None
        self._rotation_degrees: int = 0
        self._selected_rotation_degrees: int = 0
        self._cell_widths: dict[str, int] = {}
        self._range_initialized = False
        self._pending_range_position: tuple[float, float] | None = None
        self._build_ui()
        self._connect_signals()
        self._populate_project_combo()
        debug_print("MultiViewPanel.__init__ complete")

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        debug_print("MultiViewPanel._build_ui start")
        self.setAutoFillBackground(True)
        self.setStyleSheet("MultiViewPanel { background: white; }")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 8, 8)
        root.setSpacing(8)
        debug_print("MultiViewPanel root layout created")

        # Row 1: project / file / scalar / plot / palette dropdowns
        r1_card = QWidget()
        r1_card.setObjectName("controlsCard")
        r1_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        r1 = QHBoxLayout(r1_card)
        r1.setContentsMargins(14, 8, 14, 8)
        r1.setSpacing(8)
        debug_print("MultiViewPanel row 1 uses one horizontal layout")

        self.project_combo = QComboBox(); self.project_combo.setObjectName("viewerCombo")
        self.file_combo    = QComboBox(); self.file_combo.setObjectName("viewerCombo")
        self.scalar_combo  = QComboBox(); self.scalar_combo.setObjectName("viewerCombo")
        self.type_combo    = QComboBox(); self.type_combo.setObjectName("viewerCombo")
        self.type_combo.addItem("Heatmap",         "heatmap")
        self.type_combo.addItem("Contour Lines",   "contour_lines")
        self.type_combo.addItem("Contour Filled",  "contour_filled")
        self.type_combo.addItem("Heatmap+Contour", "heatmap_contour")
        self.palette_combo = QComboBox(); self.palette_combo.setObjectName("viewerCombo")
        for key in PALETTES:
            self.palette_combo.addItem(key.replace("-", " ").title(), key)
        update_combo_popup_width(self.type_combo)
        update_combo_popup_width(self.palette_combo)

        r1.addWidget(self.project_combo, 2)
        debug_print("MultiViewPanel row 1 project combo added")
        r1.addWidget(self.file_combo, 3)
        debug_print("MultiViewPanel row 1 file combo added")
        r1.addWidget(self.scalar_combo, 2)
        debug_print("MultiViewPanel row 1 scalar combo added")
        r1.addWidget(self.type_combo, 2)
        debug_print("MultiViewPanel row 1 type combo added")
        r1.addWidget(self.palette_combo, 2)
        debug_print("MultiViewPanel row 1 palette combo added")
        root.addWidget(r1_card)

        # Row 2: range controls
        r2_card = QWidget()
        r2_card.setObjectName("controlsCard")
        r2_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        r2_vbox = QVBoxLayout(r2_card)
        r2_vbox.setContentsMargins(14, 6, 14, 6)
        r2_vbox.setSpacing(4)
        r2 = QHBoxLayout()
        r2.setSpacing(8)
        r2_bottom = QHBoxLayout()
        r2_bottom.setSpacing(8)
        r2_vbox.addLayout(r2)
        r2_vbox.addLayout(r2_bottom)
        debug_print("MultiViewPanel row 2 split into two sub-rows")

        self.range_min = QDoubleSpinBox(); self.range_min.setObjectName("viewerSpin")
        self.range_min.setDecimals(12); self.range_min.setRange(-1e12, 1e12)
        self.range_min.setKeyboardTracking(False)
        debug_print("MultiViewPanel range_min keyboard tracking disabled")
        debug_print("MultiViewPanel range_min decimals set to 12")
        self.range_min.setMinimumWidth(200)
        debug_print("MultiViewPanel range_min minimum width set to 200")
        self.range_max = QDoubleSpinBox(); self.range_max.setObjectName("viewerSpin")
        self.range_max.setDecimals(12); self.range_max.setRange(-1e12, 1e12)
        self.range_max.setKeyboardTracking(False)
        debug_print("MultiViewPanel range_max keyboard tracking disabled")
        debug_print("MultiViewPanel range_max decimals set to 12")
        self.range_max.setMinimumWidth(200)
        debug_print("MultiViewPanel range_max minimum width set to 200")
        self.range_max.setValue(1.0)
        self.colorbar_label_edit = QLineEdit()
        self.colorbar_label_edit.setPlaceholderText("Colorbar label...")
        self.colorbar_label_edit.setObjectName("viewerLineEdit")
        self.colorbar_label_edit.setMinimumWidth(72)
        debug_print("MultiViewPanel colorbar label min width set to 72")
        self.unit_scale_combo = QComboBox()
        self.unit_scale_combo.setObjectName("viewerCombo")
        self.unit_scale_combo.addItem("Raw", (1.0, ""))
        self.unit_scale_combo.addItem("% x100", (100.0, "%"))
        self.unit_scale_combo.addItem("MPa /1e6", (1e-6, "MPa"))
        self.unit_scale_combo.addItem("GPa /1e9", (1e-9, "GPa"))
        update_combo_popup_width(self.unit_scale_combo)
        self.range_slider  = RangeSliderWidget()
        debug_print("MultiViewPanel range slider created")
        self.reset_button = QPushButton()
        debug_print("MultiViewPanel reset button created")
        self.reset_button.setIcon(QIcon(str(_ASSETS / "refresh.png")))
        debug_print("MultiViewPanel reset button icon set")
        self.reset_button.setIconSize(QSize(16, 16))
        debug_print("MultiViewPanel reset button icon size set")
        self.reset_button.setProperty("subtle", True)
        debug_print("MultiViewPanel reset button subtle property set")
        self.reset_button.setFixedSize(32, 32)
        debug_print("MultiViewPanel reset button fixed size set")
        self.reset_button.setToolTip("Reset range to data min/max")
        debug_print("MultiViewPanel reset button tooltip set")
        self.full_scale    = ToggleSwitchWidget("Full Scale",         checked=False)
        self.interfaces_on = ToggleSwitchWidget("Interfaces Overlay", checked=False)
        self.vectors_on = ToggleSwitchWidget("Vectors", checked=False)
        self.vectors_on.setToolTip("Show fixed-size vector arrows colored by magnitude")
        debug_print("MultiViewPanel vector overlay toggle initialized")

        # ------------------------------------------------------------------------------------------------
        # Rotation in Multi view
        # ------------------------------------------------------------------------------------------------
        self.rotation_button_row = QWidget()
        self.rotation_button_row.setObjectName("rotationButtonRow")
        rotation_button_layout = QHBoxLayout(self.rotation_button_row)
        rotation_button_layout.setContentsMargins(0, 0, 0, 0)
        rotation_button_layout.setSpacing(2)
        debug_print("MultiViewPanel rotation button row created")
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
            debug_print(f"MultiViewPanel rotation button added degrees={degrees}")
        self._sync_rotation_buttons()
        debug_print("MultiViewPanel rotation buttons initialized")
        # ------------------------------------------------------------------------------------------------

        self.export_btn = QPushButton(QIcon(str(_ASSETS / "download.png")), "Export PNG")
        self.export_btn.setProperty("subtle", True)
        self.status_label = QLabel("")
        self.status_label.setObjectName("mutedInfo")
        self.status_label.setMinimumWidth(100)
        debug_print("MultiViewPanel status label min width set to 100")

        r2.addWidget(QLabel("Range:"))
        debug_print("MultiViewPanel row 2 range label added")
        r2.addWidget(self.range_min, 4)
        debug_print("MultiViewPanel row 2 range_min added")
        r2.addWidget(self.range_max, 4)
        debug_print("MultiViewPanel row 2 range_max added")
        r2.addWidget(self.range_slider, 12)
        debug_print("MultiViewPanel row 2 range slider added")
        r2.addWidget(self.reset_button)
        debug_print("MultiViewPanel reset button added to range row")
        r2.addWidget(self.full_scale)
        debug_print("MultiViewPanel row 2 full scale toggle added")
        r2.addWidget(self.rotation_button_row)
        debug_print("MultiViewPanel row 2 rotation buttons added")
        r2.addWidget(self.export_btn)
        debug_print("MultiViewPanel row 2 export button added")

        label_caption = QLabel("Label:")
        label_caption.setObjectName("mutedInfo")
        r2_bottom.addWidget(label_caption)
        debug_print("MultiViewPanel row 2b colorbar label caption added")
        r2_bottom.addWidget(self.colorbar_label_edit, 2)
        debug_print("MultiViewPanel row 2b colorbar label edit added")
        conversion_caption = QLabel("Conversion:")
        conversion_caption.setObjectName("mutedInfo")
        r2_bottom.addWidget(conversion_caption)
        debug_print("MultiViewPanel row 2b conversion label added")
        r2_bottom.addWidget(self.unit_scale_combo, 1)
        debug_print("MultiViewPanel row 2b unit scale combo added")
        r2_bottom.addStretch()
        r2_bottom.addWidget(self.vectors_on)
        debug_print("MultiViewPanel row 2b vectors toggle added")
        r2_bottom.addWidget(self.interfaces_on)
        debug_print("MultiViewPanel row 2b interfaces toggle added at end")
        root.addWidget(r2_card)

        # Heatmap area
        debug_print("MultiViewPanel creating non-scrollable heatmap area")
        self._area = QWidget()
        self._area.setObjectName("multiViewArea")
        area_vbox = QVBoxLayout(self._area)
        area_vbox.setContentsMargins(0, 0, 0, 0)
        area_vbox.setSpacing(0)

        # Header row: [logo spacer] [...file headers...] [colorbar spacer]
        self._header_row = QWidget()
        self._hl = QHBoxLayout(self._header_row)
        self._hl.setContentsMargins(0, 2, 0, 2)
        self._hl.setSpacing(8)
        self._hl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        logo_hdr = QWidget(); logo_hdr.setFixedWidth(_LOGO_W)
        self._hl.addWidget(logo_hdr)
        self._cb_hdr = QWidget(); self._cb_hdr.setFixedWidth(_CB_W)
        self._hl.addWidget(self._cb_hdr)

        # Heatmap row: [logo] [...cells...] [colorbar]
        self._heatmap_row = QWidget()
        self._heatmap_row.setObjectName("multiViewHeatmapRow")
        self._ml = QHBoxLayout(self._heatmap_row)
        self._ml.setContentsMargins(0, 0, 0, 0)
        self._ml.setSpacing(8)
        self._ml.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Logo widget
        logo_w = QWidget(); logo_w.setFixedSize(_LOGO_W, _CANVAS_HEIGHT)
        logo_lbl = QLabel(logo_w)
        lp = HEATMAP_LOGO_PATH
        if lp.exists():
            px = QPixmap(str(lp)).scaledToWidth(_LOGO_W - 8, Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(px)
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
        logo_lbl.setGeometry(0, 0, _LOGO_W, _CANVAS_HEIGHT)
        self._ml.addWidget(logo_w)

        # Colorbar (rightmost)
        self.colorbar = ColorbarCanvas()
        self._ml.addWidget(self.colorbar)

        area_vbox.addWidget(self._header_row)
        area_vbox.addWidget(self._heatmap_row)
        self.empty_label = QLabel("Add files to compare timesteps side by side")
        self.empty_label.setObjectName("mutedInfo")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setFixedHeight(64)
        area_vbox.addWidget(self.empty_label)
        self._update_area_size()

        root.addWidget(self._area, 1)
        debug_print("MultiViewPanel added heatmap area without inner scroll")

        self.analysis_card = self._build_analysis_area()
        root.addWidget(self.analysis_card)
        root.addStretch(1)
        debug_print("MultiViewPanel analysis area added to panel root")

        self._populate_scalar_combo()
        debug_print("MultiViewPanel._build_ui complete")

    def _build_analysis_area(self) -> QWidget:
        debug_print("MultiViewPanel._build_analysis_area called")
        card = QWidget()
        card.setObjectName("controlsCard")
        card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)
        debug_print("MultiViewPanel analysis tools use one horizontal layout")

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
        self.line_mode_check = ToggleSwitchWidget("Line Scan", checked=False)
        self.show_line_check = ToggleSwitchWidget("Show Line", checked=True)
        self.line_direction_button_row = QWidget()
        self.line_direction_button_row.setObjectName("lineDirectionButtonRow")
        line_direction_layout = QHBoxLayout(self.line_direction_button_row)
        line_direction_layout.setContentsMargins(0, 0, 0, 0)
        line_direction_layout.setSpacing(2)
        debug_print("MultiViewPanel line direction button row created")
        self.line_direction_buttons: dict[str, QPushButton] = {}
        for direction, icon_name, tooltip in (
            ("horizontal", "Horizontal.png", "Horizontal line scan"),
            ("vertical", "Vertical.png", "Vertical line scan"),
        ):
            button = self._make_line_direction_button(direction, icon_name, tooltip)
            self.line_direction_buttons[direction] = button
            line_direction_layout.addWidget(button)
            debug_print(f"MultiViewPanel line direction button added direction={direction}")
        self._sync_line_direction_buttons()
        debug_print("MultiViewPanel line direction buttons initialized")
        direction_label = QLabel("Direction:")
        direction_label.setObjectName("mutedInfo")
        self.line_grid_check = ToggleSwitchWidget("Grid", checked=True)
        line_toolbar_layout.addWidget(self.line_mode_check)
        line_toolbar_layout.addWidget(self.show_line_check)
        line_toolbar_layout.addWidget(direction_label)
        line_toolbar_layout.addWidget(self.line_direction_button_row)
        line_toolbar_layout.addWidget(self.line_grid_check)
        line_toolbar_layout.addStretch(1)
        self.line_scan_canvas = LineScanCanvas()
        debug_print(f"MultiViewPanel setting line graph height={_CANVAS_HEIGHT}")
        self.line_scan_canvas.set_canvas_height(_CANVAS_HEIGHT)
        debug_print(f"MultiViewPanel line graph height now={self.line_scan_canvas.height()}")
        line_layout.addWidget(line_toolbar)
        line_layout.addWidget(self.line_scan_canvas, 1, Qt.AlignmentFlag.AlignHCenter)

        histogram_card = QWidget()
        histogram_card.setObjectName("innerCard")
        histogram_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        histogram_layout = QVBoxLayout(histogram_card)
        histogram_layout.setContentsMargins(12, 12, 12, 12)
        histogram_layout.setSpacing(10)
        histogram_toolbar = QWidget()
        histogram_toolbar.setObjectName("toolbarStrip")
        histogram_toolbar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        histogram_toolbar_layout = QHBoxLayout(histogram_toolbar)
        histogram_toolbar_layout.setContentsMargins(0, 0, 0, 0)
        histogram_toolbar_layout.setSpacing(12)
        histogram_toolbar_layout.addWidget(QLabel("Number of Bins"))
        self.histogram_bins_slider = QSlider(Qt.Orientation.Horizontal)
        self.histogram_bins_slider.setRange(10, 200)
        self.histogram_bins_slider.setValue(30)
        histogram_toolbar_layout.addWidget(self.histogram_bins_slider, 1)
        self.histogram_grid_check = ToggleSwitchWidget("Grid", checked=True)
        histogram_toolbar_layout.addWidget(self.histogram_grid_check)
        self.histogram_canvas = HistogramCanvas()
        debug_print(f"MultiViewPanel setting histogram graph height={_CANVAS_HEIGHT}")
        self.histogram_canvas.set_canvas_height(_CANVAS_HEIGHT)
        debug_print(f"MultiViewPanel histogram graph height now={self.histogram_canvas.height()}")
        histogram_layout.addWidget(histogram_toolbar)
        histogram_layout.addWidget(self.histogram_canvas, 1, Qt.AlignmentFlag.AlignHCenter)

        layout.addWidget(line_card, 1)
        debug_print("MultiViewPanel line scan card added to analysis row")
        layout.addWidget(histogram_card, 1)
        debug_print("MultiViewPanel histogram card added to analysis row")
        debug_print("MultiViewPanel._build_analysis_area complete")
        return card

    def _make_rotation_button(self, degrees: int, icon_name: str) -> QPushButton:
        debug_print("MultiViewPanel._make_rotation_button called")
        button = QPushButton()
        button.setObjectName("rotationIconButton")
        button.setCheckable(True)
        button.setProperty("subtle", True)
        button.setFixedSize(32, 32)
        button.setIcon(QIcon(str(_ASSETS / icon_name)))
        button.setIconSize(QSize(24, 24))
        button.setToolTip(f"Rotate {degrees} degrees")
        debug_print(f"MultiViewPanel rotation button configured degrees={degrees}")
        return button

    def _sync_rotation_buttons(self) -> None:
        debug_print("MultiViewPanel._sync_rotation_buttons called")
        for degrees, button in self.rotation_buttons.items():
            button.setChecked(degrees == self._selected_rotation_degrees)
            debug_print(f"MultiViewPanel rotation button checked degrees={degrees} checked={button.isChecked()}")

    @staticmethod
    def _clockwise_to_orientation_degrees(degrees: int) -> int:
        debug_print("MultiViewPanel._clockwise_to_orientation_degrees called")
        mapped_degrees = (-int(degrees)) % 360
        debug_print(f"MultiViewPanel clockwise degrees={degrees}")
        debug_print(f"MultiViewPanel orientation degrees={mapped_degrees}")
        return mapped_degrees

    def _make_line_direction_button(self, direction: str, icon_name: str, tooltip: str) -> QPushButton:
        debug_print("MultiViewPanel._make_line_direction_button called")
        button = QPushButton()
        button.setObjectName("lineScanDirectionButton")
        button.setCheckable(True)
        button.setProperty("subtle", True)
        button.setFixedSize(32, 32)
        button.setIcon(QIcon(str(_ASSETS / icon_name)))
        button.setIconSize(QSize(22, 22))
        button.setToolTip(tooltip)
        debug_print(f"MultiViewPanel line direction button configured direction={direction}")
        return button

    def _sync_line_direction_buttons(self) -> None:
        debug_print("MultiViewPanel._sync_line_direction_buttons called")
        for direction, button in self.line_direction_buttons.items():
            button.setChecked(direction == self._line_scan_direction)
            debug_print(f"MultiViewPanel line direction checked direction={direction} checked={button.isChecked()}")

    def _set_line_scan_direction(self, direction: str) -> None:
        debug_print("MultiViewPanel._set_line_scan_direction called")
        self._line_scan_direction = direction
        debug_print(f"MultiViewPanel selected line direction={self._line_scan_direction}")
        self._sync_line_direction_buttons()
        self._on_analysis_control_changed()

    def _current_line_scan_direction(self) -> str:
        debug_print("MultiViewPanel._current_line_scan_direction called")
        if hasattr(self, "line_direction_buttons"):
            debug_print(f"MultiViewPanel current line direction={self._line_scan_direction}")
            return self._line_scan_direction
        direction_combo = getattr(self, "direction_combo", None)
        direction = direction_combo.currentData() if direction_combo is not None else "horizontal"
        debug_print(f"MultiViewPanel fallback line direction={direction}")
        return direction or "horizontal"

    def _connect_signals(self) -> None:
        debug_print("MultiViewPanel._connect_signals called")
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        self.file_combo.activated.connect(self._on_file_activated)
        self.scalar_combo.currentIndexChanged.connect(self._on_scalar_changed)
        self.type_combo.currentIndexChanged.connect(self._render_all)
        self.palette_combo.currentIndexChanged.connect(self._render_all)
        self.colorbar_label_edit.editingFinished.connect(self._render_all)
        self.unit_scale_combo.currentIndexChanged.connect(self._on_display_scale_changed)
        self.range_min.valueChanged.connect(self._on_range_spin_changed)
        self.range_max.valueChanged.connect(self._on_range_spin_changed)
        self.range_slider.values_changed.connect(self._on_slider_changed)
        self.reset_button.clicked.connect(self._on_range_reset_clicked)
        debug_print("MultiViewPanel reset button connected")
        self.full_scale.toggled.connect(self._render_all)
        self.interfaces_on.toggled.connect(self._render_all)
        self.vectors_on.toggled.connect(self._render_all)
        debug_print("MultiViewPanel vectors toggle connected")
        for degrees, button in self.rotation_buttons.items():
            button.clicked.connect(lambda _checked=False, value=degrees: self._on_rotation_changed(value))
            debug_print(f"MultiViewPanel rotation button connected degrees={degrees}")
        self.export_btn.clicked.connect(self._export)
        self.line_mode_check.toggled.connect(self._on_line_mode_toggled)
        self.show_line_check.toggled.connect(self._render_all)
        self.line_grid_check.toggled.connect(self._render_all)
        for direction, button in self.line_direction_buttons.items():
            button.clicked.connect(lambda _checked=False, value=direction: self._set_line_scan_direction(value))
            debug_print(f"MultiViewPanel line direction button connected direction={direction}")
        self.histogram_bins_slider.valueChanged.connect(self._on_analysis_control_changed)
        self.histogram_grid_check.toggled.connect(self._render_all)

    def set_available_width(self, width: int) -> None:
        """Constrain this panel to the app content viewport width."""
        debug_print(f"MultiViewPanel.set_available_width width={width}")
        self._available_width = max(0, int(width))
        self.setMinimumWidth(0)
        self.setMaximumWidth(self._available_width)
        controls = [
            self.project_combo,
            self.file_combo,
            self.scalar_combo,
            self.type_combo,
            self.palette_combo,
            self.colorbar_label_edit,
            self.unit_scale_combo,
            self.rotation_button_row,
            self.range_slider,
        ]
        for control in controls:
            control.setMaximumWidth(self._available_width)
            debug_print(
                f"MultiViewPanel capped {control.objectName() or control.__class__.__name__} "
                f"to {self._available_width}"
            )
        self._area.setMaximumWidth(self._available_width)
        self.analysis_card.setMaximumWidth(self._available_width)
        self.line_scan_canvas.set_available_width(max(240, self._available_width - 56))
        self.histogram_canvas.set_available_width(max(240, self._available_width - 56))
        self._update_area_size()
        debug_print("MultiViewPanel.set_available_width complete")

    # ── Population ────────────────────────────────────────────────────────────

    def _populate_project_combo(self) -> None:
        debug_print("MultiViewPanel._populate_project_combo start")
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        for proj in self._available_projects:
            name = proj.get("project_name", proj.get("vtk_folder", ""))
            debug_print(f"MultiViewPanel adding project option={name}")
            self.project_combo.addItem(name, proj)
        self.project_combo.blockSignals(False)
        update_combo_popup_width(self.project_combo)
        self._on_project_changed()
        debug_print("MultiViewPanel._populate_project_combo complete")

    def _populate_scalar_combo(self) -> None:
        debug_print("MultiViewPanel._populate_scalar_combo called")
        self.scalar_combo.blockSignals(True)
        self.scalar_combo.clear()
        for scalar_def in self._scalar_defs:
            debug_print(f"MultiViewPanel adding scalar option={scalar_def.get('label')}")
            self.scalar_combo.addItem(scalar_def["label"], scalar_def["value"])
        self.scalar_combo.blockSignals(False)
        update_combo_popup_width(self.scalar_combo)
        debug_print(f"MultiViewPanel scalar combo count={self.scalar_combo.count()}")

    def _on_project_changed(self) -> None:
        debug_print("MultiViewPanel._on_project_changed called")
        proj = self.project_combo.currentData()
        files = proj.get("files", []) if proj else []
        debug_print(f"MultiViewPanel project files count={len(files)}")
        self.file_combo.blockSignals(True)
        self.file_combo.clear()
        self.file_combo.addItem("Select file to add…", "")
        for fp in files:
            label = Path(fp).name
            # mark already-added files
            if fp in self._columns:
                label = f"✓ {label}"
            self.file_combo.addItem(label, fp)
        self.file_combo.blockSignals(False)
        update_combo_popup_width(self.file_combo)
        debug_print("MultiViewPanel._on_project_changed complete")

    def _on_file_activated(self, index: int) -> None:
        debug_print(f"MultiViewPanel._on_file_activated index={index}")
        fp = self.file_combo.itemData(index)
        debug_print(f"MultiViewPanel activated file={fp}")
        if fp and fp not in self._columns:
            self._add_column(fp)
            self._on_project_changed()   # refresh marks
        else:
            debug_print("MultiViewPanel file ignored because it is empty or already added")

    # ── Column management ─────────────────────────────────────────────────────

    def _add_column(self, file_path: str) -> None:
        debug_print(f"MultiViewPanel._add_column file={file_path}")
        header = MultiViewHeader(file_path)
        cell   = MultiViewCell(file_path)
        header.close_requested.connect(self._remove_column)
        header.legend_name_changed.connect(self._on_legend_name_changed)
        cell.heatmap_clicked.connect(self._handle_cell_click)
        self._columns[file_path] = (header, cell)
        self._range_initialized = False

        cb_h_idx = self._hl.indexOf(self._cb_hdr)
        cb_m_idx = self._ml.indexOf(self.colorbar)
        self._hl.insertWidget(cb_h_idx, header)
        self._ml.insertWidget(cb_m_idx, cell)

        self._update_area_size()
        self._render_all()
        debug_print("MultiViewPanel._add_column complete")

    def _remove_column(self, file_path: str) -> None:
        debug_print(f"MultiViewPanel._remove_column file={file_path}")
        if file_path not in self._columns:
            debug_print("MultiViewPanel remove skipped, file not present")
            return
        header, cell = self._columns.pop(file_path)
        self._hl.removeWidget(header)
        self._ml.removeWidget(cell)
        header.deleteLater()
        cell.deleteLater()
        self._grid_cache.pop(file_path, None)
        self._cell_widths.pop(file_path, None)
        self._legend_names.pop(file_path, None)
        self._range_initialized = False
        self._histogram_cache = {
            key: value for key, value in self._histogram_cache.items() if key[0] != file_path
        }
        debug_print("MultiViewPanel removed histogram cache entries for file")
        self._update_area_size()
        self._on_project_changed()
        self._render_all()
        debug_print("MultiViewPanel._remove_column complete")

    def _on_legend_name_changed(self, file_path: str, name: str) -> None:
        debug_print(f"MultiViewPanel._on_legend_name_changed file={file_path} name={name}")
        self._legend_names[file_path] = name
        self._render_all()

    def _update_area_size(self) -> None:
        debug_print("MultiViewPanel._update_area_size called")
        n = len(self._columns)
        spacing = 8
        gaps = (n + 1) * spacing if n > 0 else 0   # gaps between logo, cells, colorbar
        cells_width = sum(self._cell_widths.get(file_path, _CELL_W) for file_path in self._columns)
        width = _LOGO_W + cells_width + _CB_W + gaps
        available = self._available_width
        final_width = min(width, available) if available is not None and available > 0 else width
        self._area.setFixedWidth(final_width)
        self._area.setMaximumWidth(final_width)
        self._area.setFixedHeight(_CANVAS_HEIGHT + 96)
        self.empty_label.setVisible(n == 0)
        if hasattr(self, "export_btn"):
            self.export_btn.setEnabled(n > 0)
            debug_print(f"MultiViewPanel export enabled={n > 0}")
        debug_print(f"MultiViewPanel columns={n}")
        debug_print(f"MultiViewPanel area width={width}")
        debug_print(f"MultiViewPanel available width={available}")
        debug_print(f"MultiViewPanel final area width={final_width}")

    # ── Rendering ─────────────────────────────────────────────────────────────

    def _render_all(self, *_) -> None:
        debug_print("MultiViewPanel._render_all start")
        if not self._columns or not self._scalar_defs:
            debug_print("MultiViewPanel render skipped: no columns or no scalar defs")
            return
        sd = self._selected_scalar_def()
        self._grid_cache.clear()
        debug_print("MultiViewPanel grid cache cleared")
        debug_print(f"MultiViewPanel scalar array={sd.get('array')}")
        debug_print(f"MultiViewPanel scalar component={sd.get('component')}")
        palette_name = self.palette_combo.currentData() or "aqua-fire"
        cmap  = palette_to_cmap(palette_name)
        debug_print(f"MultiViewPanel palette={palette_name}")
        scale = sd.get("scale", 1.0) or 1.0
        label = sd.get("label", "")
        units = sd.get("units")
        extra_scale, cb_label = self._get_display_params(label, units)
        total_scale = scale * extra_scale
        debug_print(f"MultiViewPanel base scale={scale}")
        debug_print(f"MultiViewPanel extra scale={extra_scale}")
        debug_print(f"MultiViewPanel total scale={total_scale}")
        debug_print(f"MultiViewPanel colorbar label={cb_label}")

        grids = []
        for fp in self._columns:
            debug_print(f"MultiViewPanel loading grid file={fp}")
            try:
                reader = get_reader(fp)
                debug_print("MultiViewPanel reader loaded")
                axis = self._axis_for_reader(reader)
                x, y, z, _ = reader.get_interpolated_slice(
                    axis=axis, index=0,
                    scalar_name=sd["array"],
                    component=sd.get("component"),
                    resolution=DEFAULTS["interpolation_resolution"],
                )
                debug_print(f"MultiViewPanel grid min={float(np.nanmin(z))}")
                debug_print(f"MultiViewPanel grid max={float(np.nanmax(z))}")
                orientation = self._orientation()
                overlay = orientation.apply_overlay(self._build_overlay_grid(fp, axis))
                vector_overlay = self._build_vector_overlay_for_file(reader, sd, axis, orientation)
                z_scaled = z * total_scale
                display = orientation.apply_grid(x, y, z_scaled)
                self._grid_cache[fp] = (display.x, display.y, display.z)
                self._apply_cell_width(fp, orientation.plot_width_for_height(display.x, display.y, _CANVAS_HEIGHT))
                debug_print(f"MultiViewPanel cached grid for={fp}")
                grids.append((fp, display.x, display.y, display.z, overlay, vector_overlay, None))
            except Exception as exc:
                debug_print(f"MultiViewPanel render failed for {fp}: {exc}")
                grids.append((fp, None, None, None, None, None, str(exc)))

        valid = [z for _, _, _, z, _, _, _ in grids if z is not None]
        debug_print(f"MultiViewPanel valid grid count={len(valid)}")
        if valid:
            data_vmin = float(min(np.nanmin(z) for z in valid))
            data_vmax = float(max(np.nanmax(z) for z in valid))
        else:
            data_vmin = self.range_min.value()
            data_vmax = self.range_max.value()
        debug_print(f"MultiViewPanel data_vmin={data_vmin}")
        debug_print(f"MultiViewPanel data_vmax={data_vmax}")
        selected_min, selected_max = self._current_selected_range()
        pending_range_position = getattr(self, "_pending_range_position", None)
        if valid and pending_range_position is not None:
            debug_print("MultiViewPanel restoring range position after conversion")
            debug_print(f"MultiViewPanel pending range position={pending_range_position}")
            selected_min, selected_max = self._range_from_position(
                pending_range_position,
                (data_vmin, data_vmax),
            )
            self._pending_range_position = None
            self._range_initialized = True
            debug_print(f"MultiViewPanel restored selected_min={selected_min}")
            debug_print(f"MultiViewPanel restored selected_max={selected_max}")
        elif valid and not self._range_initialized:
            selected_min = data_vmin
            selected_max = data_vmax
            self._range_initialized = True
            debug_print("MultiViewPanel selected range initialized from data")
        debug_print(f"MultiViewPanel selected_min={selected_min}")
        debug_print(f"MultiViewPanel selected_max={selected_max}")

        full_scale_enabled = self.full_scale.isChecked() and valid
        if full_scale_enabled:
            debug_print("MultiViewPanel full scale enabled")
            vmin = data_vmin
            vmax = data_vmax
            cmap = make_dynamic_colormap(data_vmin, data_vmax, selected_min, selected_max, palette_name)
        else:
            debug_print("MultiViewPanel manual scale enabled")
            vmin = selected_min
            vmax = selected_max
        if vmax < vmin:
            debug_print("MultiViewPanel swapping inverted manual range")
            vmin, vmax = vmax, vmin
        debug_print(f"MultiViewPanel vmin={vmin}")
        debug_print(f"MultiViewPanel vmax={vmax}")

        self.range_min.blockSignals(True)
        self.range_max.blockSignals(True)
        self.range_min.setValue(selected_min)
        self.range_max.setValue(selected_max)
        self.range_min.blockSignals(False)
        self.range_max.blockSignals(False)
        self.range_slider.blockSignals(True)
        self.range_slider.set_bounds(data_vmin, data_vmax)
        self.range_slider.set_values(selected_min, selected_max, emit_signal=False)
        self.range_slider.blockSignals(False)
        self.range_min.setEnabled(True)
        self.range_max.setEnabled(True)
        self.range_slider.setEnabled(True)
        debug_print("MultiViewPanel range controls synced")

        for fp, x, y, z, overlay, vector_overlay, error in grids:
            _, cell = self._columns[fp]
            if z is not None:
                debug_print(f"MultiViewPanel rendering cell={fp}")
                line_overlay = self._current_line_overlay()
                debug_print(f"MultiViewPanel line_overlay={line_overlay}")
                debug_print(f"MultiViewPanel vector_overlay present={vector_overlay is not None}")
                cell.render(
                    x, y, z,
                    vmin=vmin,
                    vmax=vmax,
                    cmap=cmap,
                    overlay_grid=overlay,
                    line_overlay=line_overlay,
                    vector_overlay=vector_overlay,
                )
            else:
                debug_print(f"MultiViewPanel rendering error status for={fp}")
                cell.render_status(f"Could not render {Path(fp).name}<br>{error or 'Unknown error'}")

        self.colorbar.update_colorbar(cmap, vmin, vmax, cb_label)
        self._render_analysis(sd, total_scale, extra_scale, cb_label)
        debug_print("MultiViewPanel._render_all complete")

    def _on_scalar_changed(self, *_) -> None:
        debug_print("MultiViewPanel._on_scalar_changed called")
        self._range_initialized = False
        self._reset_click_range_state("scalar changed")
        self._render_all()
        debug_print("MultiViewPanel._on_scalar_changed complete")

    def _on_display_scale_changed(self, *_) -> None:
        debug_print("MultiViewPanel._on_display_scale_changed called")
        selected_range = self._current_selected_range()
        slider_bounds = self._current_slider_bounds()
        debug_print(f"MultiViewPanel conversion old selected range={selected_range}")
        debug_print(f"MultiViewPanel conversion old slider bounds={slider_bounds}")
        self._pending_range_position = self._range_position(selected_range, slider_bounds)
        debug_print(f"MultiViewPanel conversion saved range position={self._pending_range_position}")
        self._range_initialized = True
        debug_print("MultiViewPanel conversion keeps range initialized")
        self._render_all()
        debug_print("MultiViewPanel._on_display_scale_changed complete")

    def _on_range_spin_changed(self, *_):
        debug_print("MultiViewPanel._on_range_spin_changed called")
        debug_print(f"MultiViewPanel range_min now={self.range_min.value()}")
        debug_print(f"MultiViewPanel range_max now={self.range_max.value()}")
        self._range_initialized = True
        if not self.full_scale.isChecked():
            self._switch_to_manual_range("range number changed")
        self._render_all()
        debug_print("MultiViewPanel._on_range_spin_changed complete")

    def _on_slider_changed(self, lo: float, hi: float) -> None:
        debug_print("MultiViewPanel._on_slider_changed called")
        debug_print(f"MultiViewPanel slider lo={lo}")
        debug_print(f"MultiViewPanel slider hi={hi}")
        self._range_initialized = True
        if not self.full_scale.isChecked():
            self._switch_to_manual_range("range slider changed")
        self.range_min.blockSignals(True)
        self.range_max.blockSignals(True)
        self.range_min.setValue(lo)
        self.range_max.setValue(hi)
        self.range_min.blockSignals(False)
        self.range_max.blockSignals(False)
        self._render_all()
        debug_print("MultiViewPanel._on_slider_changed complete")

    def _on_range_reset_clicked(self, *_args) -> None:
        debug_print("MultiViewPanel._on_range_reset_clicked called")
        self._reset_click_range_state("range reset clicked")
        self._range_initialized = False
        debug_print("MultiViewPanel click range state cleared for reset")
        self.full_scale.blockSignals(True)
        debug_print("MultiViewPanel full scale signals blocked")
        self.full_scale.setChecked(True)
        debug_print("MultiViewPanel full scale checked for range reset")
        self.full_scale.blockSignals(False)
        debug_print("MultiViewPanel full scale signals unblocked")
        self._render_all()
        debug_print("MultiViewPanel._on_range_reset_clicked complete")

    def _switch_to_manual_range(self, reason: str) -> None:
        debug_print("MultiViewPanel._switch_to_manual_range called")
        debug_print(f"MultiViewPanel manual range reason={reason}")
        if not self.full_scale.isChecked():
            debug_print("MultiViewPanel already in manual range mode")
            return
        self.full_scale.blockSignals(True)
        self.full_scale.setChecked(False)
        self.full_scale.blockSignals(False)
        debug_print("MultiViewPanel Full Scale turned off for manual range")

    def _current_selected_range(self) -> tuple[float, float]:
        lo = float(self.range_min.value())
        hi = float(self.range_max.value())
        if hi < lo:
            lo, hi = hi, lo
        return lo, hi

    def _current_slider_bounds(self) -> tuple[float, float]:
        debug_print("MultiViewPanel._current_slider_bounds called")
        minimum = float(getattr(self.range_slider, "_minimum", self.range_min.value()))
        maximum = float(getattr(self.range_slider, "_maximum", self.range_max.value()))
        if maximum < minimum:
            minimum, maximum = maximum, minimum
        debug_print(f"MultiViewPanel slider minimum={minimum}")
        debug_print(f"MultiViewPanel slider maximum={maximum}")
        return minimum, maximum

    @staticmethod
    def _range_position(
        selected_range: tuple[float, float],
        bounds: tuple[float, float],
    ) -> tuple[float, float]:
        debug_print("MultiViewPanel._range_position called")
        lo, hi = selected_range
        minimum, maximum = bounds
        if maximum < minimum:
            minimum, maximum = maximum, minimum
        span = maximum - minimum
        debug_print(f"MultiViewPanel range position selected={selected_range}")
        debug_print(f"MultiViewPanel range position bounds={bounds}")
        if span == 0:
            debug_print("MultiViewPanel range position zero span; using full range")
            return 0.0, 1.0
        lower = (float(lo) - minimum) / span
        upper = (float(hi) - minimum) / span
        lower = max(0.0, min(1.0, lower))
        upper = max(0.0, min(1.0, upper))
        if upper < lower:
            lower, upper = upper, lower
        debug_print(f"MultiViewPanel range position lower={lower}")
        debug_print(f"MultiViewPanel range position upper={upper}")
        return lower, upper

    @staticmethod
    def _range_from_position(
        position: tuple[float, float],
        bounds: tuple[float, float],
    ) -> tuple[float, float]:
        debug_print("MultiViewPanel._range_from_position called")
        lower, upper = position
        minimum, maximum = bounds
        if maximum < minimum:
            minimum, maximum = maximum, minimum
        span = maximum - minimum
        lower = max(0.0, min(1.0, float(lower)))
        upper = max(0.0, min(1.0, float(upper)))
        if upper < lower:
            lower, upper = upper, lower
        selected = (minimum + (lower * span), minimum + (upper * span))
        debug_print(f"MultiViewPanel range from position={position}")
        debug_print(f"MultiViewPanel range from bounds={bounds}")
        debug_print(f"MultiViewPanel range from selected={selected}")
        return selected

    def _handle_cell_click(self, file_path: str, x_value: float, y_value: float) -> None:
        debug_print("MultiViewPanel._handle_cell_click called")
        debug_print(f"MultiViewPanel click file={file_path}")
        debug_print(f"MultiViewPanel click x={x_value}")
        debug_print(f"MultiViewPanel click y={y_value}")
        if self.line_mode_check.isChecked():
            debug_print("MultiViewPanel click handled as line scan")
            self._apply_line_scan_click(x_value, y_value)
            return
        debug_print("MultiViewPanel click handled as range selection")
        grid = self._grid_cache.get(file_path)
        if grid is None:
            debug_print("MultiViewPanel click ignored: no cached grid for file")
            self.status_label.setText("Click ignored: render data not ready")
            return
        x_grid, y_grid, z_grid = grid
        try:
            clicked_value = self._nearest_grid_value(x_grid, y_grid, z_grid, x_value, y_value)
        except ValueError as exc:
            debug_print(f"MultiViewPanel click ignored: {exc}")
            self.status_label.setText("Click ignored: no valid value")
            return
        debug_print(f"MultiViewPanel clicked value={clicked_value}")
        self._apply_click_range_value(clicked_value, file_path)

    def _apply_line_scan_click(self, x_value: float, y_value: float) -> None:
        debug_print("MultiViewPanel._apply_line_scan_click called")
        direction = self._current_line_scan_direction()
        debug_print(f"MultiViewPanel line scan direction={direction}")
        if direction == "horizontal":
            self._line_scan_y = float(y_value)
            debug_print(f"MultiViewPanel line scan y set={self._line_scan_y}")
            message = f"Line scan Y={self._line_scan_y:.6f}"
        else:
            self._line_scan_x = float(x_value)
            debug_print(f"MultiViewPanel line scan x set={self._line_scan_x}")
            message = f"Line scan X={self._line_scan_x:.6f}"
        self.status_label.setText(message)
        debug_print(message)
        self._render_all()

    def _apply_click_range_value(self, clicked_value: float, file_path: str) -> None:
        debug_print("MultiViewPanel._apply_click_range_value called")
        debug_print(f"MultiViewPanel click value={clicked_value}")
        debug_print(f"MultiViewPanel click range file={file_path}")
        if self._click_count == 0:
            self._first_click_value = clicked_value
            self._click_count = 1
            self._last_selected_range = None
            message = f"First click: {clicked_value:.6f} (click again to finish range)"
            self.status_label.setText(message)
            debug_print(message)
            return
        lo, hi = sorted([float(self._first_click_value), float(clicked_value)])
        self._last_selected_range = (lo, hi)
        self._click_count = 0
        self._first_click_value = None
        self._range_initialized = True
        if not self.full_scale.isChecked():
            self._switch_to_manual_range("heatmap click range selected")
        self.range_min.blockSignals(True)
        self.range_max.blockSignals(True)
        self.range_min.setValue(lo)
        self.range_max.setValue(hi)
        self.range_min.blockSignals(False)
        self.range_max.blockSignals(False)
        message = f"Range selected: [{lo:.6f}, {hi:.6f}]"
        self.status_label.setText(message)
        debug_print(message)
        self._render_all()

    def _reset_click_range_state(self, reason: str) -> None:
        debug_print("MultiViewPanel._reset_click_range_state called")
        debug_print(f"MultiViewPanel reset reason={reason}")
        self._click_count = 0
        self._first_click_value = None
        self._last_selected_range = None
        if hasattr(self, "status_label"):
            self.status_label.setText("")

    def _on_line_mode_toggled(self, checked: bool) -> None:
        debug_print("MultiViewPanel._on_line_mode_toggled called")
        debug_print(f"MultiViewPanel line mode checked={checked}")
        if checked:
            self._reset_click_range_state("line scan mode enabled")
        self._render_all()
        debug_print("MultiViewPanel._on_line_mode_toggled complete")

    def _on_analysis_control_changed(self, *_) -> None:
        debug_print("MultiViewPanel._on_analysis_control_changed called")
        debug_print(f"MultiViewPanel line direction={self._current_line_scan_direction()}")
        debug_print(f"MultiViewPanel histogram bins={self.histogram_bins_slider.value()}")
        self._render_all()
        debug_print("MultiViewPanel._on_analysis_control_changed complete")

    def _render_analysis(
        self,
        selected_scalar_def: dict,
        total_scale: float,
        extra_scale: float,
        display_label: str,
    ) -> None:
        debug_print("MultiViewPanel._render_analysis called")
        line_series, line_title, x_label = self._build_line_scan_series()
        debug_print(f"MultiViewPanel line series count={len(line_series)}")
        self.line_scan_canvas.render_lines(
            line_series,
            title=line_title,
            x_label=x_label,
            y_label=display_label,
            show_grid=self.line_grid_check.isChecked(),
        )
        hist_series, hist_label = self._build_histogram_series(
            selected_scalar_def,
            total_scale,
            extra_scale,
            display_label,
        )
        debug_print(f"MultiViewPanel histogram series count={len(hist_series)}")
        self.histogram_canvas.render_histograms(
            hist_series,
            label=hist_label,
            bins=int(self.histogram_bins_slider.value()),
            show_grid=self.histogram_grid_check.isChecked(),
        )
        debug_print("MultiViewPanel._render_analysis complete")

    def _build_line_scan_series(self) -> tuple[list[dict], str, str]:
        debug_print("MultiViewPanel._build_line_scan_series called")
        direction = self._current_line_scan_direction()
        position = self._line_scan_y if direction == "horizontal" else self._line_scan_x
        debug_print(f"MultiViewPanel line direction={direction}")
        debug_print(f"MultiViewPanel line position={position}")
        series = []
        title = "Line Scan"
        x_label = "X Position" if direction == "horizontal" else "Y Position"
        for fp in self._columns:
            debug_print(f"MultiViewPanel line series file={fp}")
            grid = self._grid_cache.get(fp)
            if grid is None:
                debug_print("MultiViewPanel line grid missing")
                continue
            x_grid, y_grid, z_grid = grid
            x_data, z_data, title, x_label = self._extract_line_scan(
                x_grid,
                y_grid,
                z_grid,
                direction,
                position,
            )
            legend = self._legend_names.get(fp) or compact_timestep_label(fp)
            series.append({"name": legend, "x": x_data, "y": z_data})
            debug_print(f"MultiViewPanel line series added={legend}")
        debug_print(f"MultiViewPanel line series final count={len(series)}")
        return series, title, x_label

    @staticmethod
    def _extract_line_scan(x_grid, y_grid, z_grid, direction: str, position):
        debug_print("MultiViewPanel._extract_line_scan called")
        debug_print(f"MultiViewPanel extract direction={direction}")
        debug_print(f"MultiViewPanel extract position={position}")
        x_data, z_data, title, x_label = Heatmap2DOrientation.extract_line_scan(
            x_grid, y_grid, z_grid, direction, position
        )
        debug_print(f"MultiViewPanel extracted points={len(np.asarray(z_data))}")
        return x_data, z_data, title, x_label

    def _build_histogram_series(
        self,
        selected_scalar_def: dict,
        total_scale: float,
        extra_scale: float,
        display_label: str,
    ) -> tuple[list[dict], str]:
        debug_print("MultiViewPanel._build_histogram_series called")
        series = []
        for fp in self._columns:
            debug_print(f"MultiViewPanel histogram file={fp}")
            if fp in self._grid_cache:
                debug_print("MultiViewPanel histogram using rendered grid cache")
                values = self._grid_cache[fp][2]
            else:
                debug_print("MultiViewPanel histogram loading scalar grid")
                values = self._histogram_grid_for_file(fp, selected_scalar_def)
                if values is None:
                    debug_print("MultiViewPanel histogram grid missing")
                    continue
                if extra_scale != 1.0:
                    debug_print("MultiViewPanel histogram applying extra scale")
                    values = values * extra_scale
            legend = self._legend_names.get(fp) or compact_timestep_label(fp)
            series.append({"name": legend, "values": values})
            debug_print(f"MultiViewPanel histogram series added={legend}")
        debug_print(f"MultiViewPanel histogram final count={len(series)}")
        return series, display_label

    def _histogram_grid_for_file(self, file_path: str, scalar_def: dict):
        debug_print("MultiViewPanel._histogram_grid_for_file called")
        scalar_key = scalar_def.get("value", "")
        cache_key = (file_path, scalar_key)
        debug_print(f"MultiViewPanel histogram cache key={cache_key}")
        if cache_key in self._histogram_cache:
            debug_print("MultiViewPanel histogram cache hit")
            return self._histogram_cache[cache_key]
        try:
            reader = get_reader(file_path)
            debug_print("MultiViewPanel histogram reader loaded")
            axis = self._axis_for_reader(reader)
            _, _, z_grid, _ = reader.get_interpolated_slice(
                axis=axis,
                index=0,
                scalar_name=scalar_def["array"],
                component=scalar_def.get("component"),
                resolution=DEFAULTS["interpolation_resolution"],
            )
            scale = scalar_def.get("scale", 1.0) or 1.0
            debug_print(f"MultiViewPanel histogram scalar scale={scale}")
            z_grid = z_grid * scale
            self._histogram_cache[cache_key] = z_grid
            debug_print("MultiViewPanel histogram cache stored")
            return z_grid
        except Exception as exc:
            debug_print(f"MultiViewPanel histogram load failed: {exc}")
            return None

    def _current_line_overlay(self):
        debug_print("MultiViewPanel._current_line_overlay called")
        if not self.line_mode_check.isChecked():
            debug_print("MultiViewPanel line overlay skipped: line mode off")
            return None
        if not self.show_line_check.isChecked():
            debug_print("MultiViewPanel line overlay skipped: show line off")
            return None
        direction = self._current_line_scan_direction()
        debug_print(f"MultiViewPanel line overlay direction={direction}")
        if direction == "horizontal":
            if self._line_scan_y is None:
                debug_print("MultiViewPanel line overlay skipped: no y yet")
                return None
        overlay = Heatmap2DOrientation.line_overlay(direction, self._line_scan_x, self._line_scan_y)
        if overlay is None:
            debug_print("MultiViewPanel line overlay skipped: no position yet")
        return overlay

    def _on_rotation_changed(self, degrees: int) -> None:
        debug_print("MultiViewPanel._on_rotation_changed called")
        self._selected_rotation_degrees = int(degrees)
        debug_print(f"MultiViewPanel selected icon rotation degrees={self._selected_rotation_degrees}")
        self._rotation_degrees = self._clockwise_to_orientation_degrees(degrees)
        debug_print(f"MultiViewPanel internal rotation degrees={self._rotation_degrees}")
        self._sync_rotation_buttons()
        self._line_scan_x = None
        debug_print("MultiViewPanel line scan x reset after rotation")
        self._line_scan_y = None
        debug_print("MultiViewPanel line scan y reset after rotation")
        self._reset_click_range_state("rotation changed")
        self._grid_cache.clear()
        debug_print("MultiViewPanel grid cache cleared after rotation")
        self._render_all()

    # ── Export ────────────────────────────────────────────────────────────────

    def _export(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        debug_print("MultiViewPanel._export called")
        if not self._columns:
            debug_print("MultiViewPanel export skipped: no columns")
            return
        px = self._heatmap_row.grab()
        path, _ = QFileDialog.getSaveFileName(self, "Export", "multi_view.png", "PNG (*.png)")
        if path:
            debug_print(f"MultiViewPanel saving export path={path}")
            px.save(path)
        else:
            debug_print("MultiViewPanel export cancelled")
        debug_print("MultiViewPanel._export complete")

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _build_scalar_defs(dataset_info: dict) -> list[dict]:
        debug_print("MultiViewPanel._build_scalar_defs called")
        projects = dataset_info.get("available_projects", [])
        debug_print(f"MultiViewPanel scalar projects count={len(projects)}")
        cfg = projects[0].get("dataset_config", {}) if projects else {}
        scalars = cfg.get("scalars")
        if scalars:
            debug_print(f"MultiViewPanel using configured scalars count={len(scalars)}")
            return [{"label": d["label"], "value": f"s-{i}", "array": d["array"],
                     "component": d.get("component"),
                     "scale": 1.0, "units": None}
                    for i, d in enumerate(scalars)]
        files = [f for p in projects for f in p.get("files", [])]
        if not files:
            debug_print("MultiViewPanel no files for auto scalar defs")
            return []
        try:
            reader = get_reader(files[0])
            debug_print(f"MultiViewPanel auto scalar source={files[0]}")
            return [{"label": n, "value": n, "array": n, "component": None,
                     "scale": 1.0, "units": None}
                    for n in reader.scalar_fields]
        except Exception as exc:
            debug_print(f"MultiViewPanel auto scalar defs failed: {exc}")
            return []

    def _selected_scalar_def(self) -> dict:
        debug_print("MultiViewPanel._selected_scalar_def called")
        scalar_key = self.scalar_combo.currentData() if hasattr(self, "scalar_combo") else None
        debug_print(f"MultiViewPanel selected scalar key={scalar_key}")
        for scalar_def in self._scalar_defs:
            if scalar_def.get("value") == scalar_key:
                debug_print("MultiViewPanel selected scalar matched")
                return scalar_def
        debug_print("MultiViewPanel selected scalar fallback to first")
        return self._scalar_defs[0]


    def _get_display_params(self, scalar_label: str, units: str | None) -> tuple[float, str]:
        debug_print("MultiViewPanel._get_display_params called")
        custom_name = self.colorbar_label_edit.text().strip() if hasattr(self, "colorbar_label_edit") else ""
        extra_scale, unit_suffix = self.unit_scale_combo.currentData() if hasattr(self, "unit_scale_combo") else (1.0, "")
        debug_print(f"MultiViewPanel custom colorbar label={custom_name}")
        debug_print(f"MultiViewPanel unit suffix={unit_suffix}")
        name = custom_name if custom_name else scalar_label
        if unit_suffix:
            label = f"{name} ({unit_suffix})"
        else:
            label = name
        debug_print(f"MultiViewPanel display label={label}")
        return extra_scale, label

    @staticmethod
    def _nearest_grid_value(x_grid, y_grid, z_grid, x_value: float, y_value: float) -> float:
        debug_print("MultiViewPanel._nearest_grid_value called")
        z_arr = np.asarray(z_grid, dtype=float)
        valid = ~np.isnan(z_arr)
        if not np.any(valid):
            raise ValueError("No valid z values in grid")
        distance = (np.asarray(x_grid) - float(x_value)) ** 2 + (np.asarray(y_grid) - float(y_value)) ** 2
        distance = np.where(valid, distance, np.inf)
        idx = np.unravel_index(np.argmin(distance), distance.shape)
        value = float(z_arr[idx])
        debug_print(f"MultiViewPanel nearest grid idx={idx}")
        debug_print(f"MultiViewPanel nearest grid value={value}")
        return value

    def _build_vector_overlay_for_file(
        self,
        reader,
        scalar_def: dict,
        axis: str,
        orientation: Heatmap2DOrientation,
    ) -> dict | None:
        debug_print("MultiViewPanel._build_vector_overlay_for_file called")
        debug_print(f"MultiViewPanel vector toggle checked={self.vectors_on.isChecked()}")
        if not self.vectors_on.isChecked():
            debug_print("MultiViewPanel vector overlay skipped: toggle off")
            return None
        vector_name = scalar_def.get("array")
        debug_print(f"MultiViewPanel vector candidate={vector_name}")
        vector_fields = getattr(reader, "vector_fields", [])
        debug_print(f"MultiViewPanel reader vector fields={vector_fields}")
        if vector_name not in vector_fields:
            debug_print("MultiViewPanel vector overlay skipped: scalar is not vector")
            return None
        type_combo = getattr(self, "type_combo", None)
        plot_type = type_combo.currentData() if type_combo is not None else "heatmap"
        debug_print(f"MultiViewPanel vector plot_type={plot_type}")
        if plot_type == "difference":
            debug_print("MultiViewPanel vector overlay skipped: difference plot")
            return None
        try:
            x_grid, y_grid, u_grid, v_grid, magnitude_grid, stats = reader.get_vector_overlay_grid(
                axis=axis,
                index=0,
                vector_name=vector_name,
                resolution=21,
            )
            debug_print(f"MultiViewPanel vector stats={stats}")
            overlay = {
                "x": x_grid,
                "y": y_grid,
                "u": u_grid,
                "v": v_grid,
                "magnitude": magnitude_grid,
                "label": scalar_def.get("label", vector_name),
                "stats": stats,
            }
            debug_print(f"MultiViewPanel vector raw shape={np.asarray(u_grid).shape}")
            overlay = self._orient_vector_overlay(overlay, orientation)
            overlay = self._downsample_vector_overlay(overlay, max_arrows_per_axis=21)
            debug_print(f"MultiViewPanel vector final shape={np.asarray(overlay['u']).shape}")
            debug_print(f"MultiViewPanel vector final count={np.asarray(overlay['u']).size}")
            return overlay
        except Exception as exc:
            debug_print(f"MultiViewPanel vector overlay build failed: {exc}")
            return None

    def _orient_vector_overlay(self, overlay: dict, orientation: Heatmap2DOrientation) -> dict:
        debug_print("MultiViewPanel._orient_vector_overlay called")
        x_values = np.asarray(overlay["x"], dtype=float)
        y_values = np.asarray(overlay["y"], dtype=float)
        u_source = np.asarray(overlay["u"], dtype=float)
        v_source = np.asarray(overlay["v"], dtype=float)
        start = orientation.apply_grid(x_values, y_values, overlay["magnitude"])
        plot_x_values, plot_y_values = Heatmap2DOrientation.plot_axes(start.x, start.y, start.z)
        display_x, display_y = np.meshgrid(plot_x_values, plot_y_values)
        turns = orientation.rotation_degrees // 90
        debug_print(f"MultiViewPanel vector rotation turns={turns}")
        u_rotated = np.rot90(u_source, k=-turns) if turns else u_source
        v_rotated = np.rot90(v_source, k=-turns) if turns else v_source
        debug_print(f"MultiViewPanel vector rotated u shape={u_rotated.shape}")
        debug_print(f"MultiViewPanel vector rotated v shape={v_rotated.shape}")
        if turns == 1:
            u_values = -v_rotated
            v_values = u_rotated
        elif turns == 2:
            u_values = -u_rotated
            v_values = -v_rotated
        elif turns == 3:
            u_values = v_rotated
            v_values = -u_rotated
        else:
            u_values = u_rotated
            v_values = v_rotated
        result = dict(overlay)
        result["x"] = display_x
        result["y"] = display_y
        result["u"] = u_values
        result["v"] = v_values
        result["magnitude"] = start.z
        debug_print(f"MultiViewPanel vector display x shape={display_x.shape}")
        debug_print(f"MultiViewPanel vector display y shape={display_y.shape}")
        debug_print("MultiViewPanel vector orientation applied")
        return result

    def _downsample_vector_overlay(self, overlay: dict, *, max_arrows_per_axis: int) -> dict:
        debug_print("MultiViewPanel._downsample_vector_overlay called")
        rows, cols = np.asarray(overlay["u"]).shape[:2]
        row_step = max(1, int(np.ceil(rows / max_arrows_per_axis)))
        col_step = max(1, int(np.ceil(cols / max_arrows_per_axis)))
        row_offset = row_step // 2
        col_offset = col_step // 2
        debug_print(f"MultiViewPanel vector downsample rows={rows}")
        debug_print(f"MultiViewPanel vector downsample cols={cols}")
        debug_print(f"MultiViewPanel vector downsample row_step={row_step}")
        debug_print(f"MultiViewPanel vector downsample col_step={col_step}")
        result = dict(overlay)
        for key in ("x", "y", "u", "v", "magnitude"):
            result[key] = np.asarray(overlay[key])[row_offset::row_step, col_offset::col_step]
            debug_print(f"MultiViewPanel vector downsampled {key} shape={result[key].shape}")
        x_values = np.asarray(result["x"], dtype=float)
        y_values = np.asarray(result["y"], dtype=float)
        x_span = float(np.nanmax(x_values) - np.nanmin(x_values)) if x_values.size else 1.0
        y_span = float(np.nanmax(y_values) - np.nanmin(y_values)) if y_values.size else 1.0
        density = max(max(result["u"].shape), 1)
        result["arrow_length"] = max(x_span, y_span, 1.0) / density * 0.55
        debug_print(f"MultiViewPanel vector fixed arrow_length={result['arrow_length']}")
        return result

    def _build_overlay_grid(self, file_path: str, axis: str):
        debug_print("MultiViewPanel._build_overlay_grid called")
        debug_print(f"MultiViewPanel overlay requested={self.interfaces_on.isChecked()}")
        if not self.interfaces_on.isChecked():
            debug_print("MultiViewPanel overlay skipped: toggle off")
            return None
        phase_file = self._phase_overlay_file(file_path)
        debug_print(f"MultiViewPanel overlay phase_file={phase_file}")
        if not phase_file:
            debug_print("MultiViewPanel overlay skipped: no matching PhaseField file")
            return None
        try:
            phase_reader = get_reader(str(phase_file))
            debug_print("MultiViewPanel overlay reader loaded")
            x_grid, y_grid, z_grid, _ = phase_reader.get_interpolated_slice(
                axis=axis,
                index=0,
                scalar_name="Interfaces",
                component=None,
                resolution=DEFAULTS["interpolation_resolution"],
            )
            debug_print(f"MultiViewPanel overlay min={float(np.nanmin(z_grid))}")
            debug_print(f"MultiViewPanel overlay max={float(np.nanmax(z_grid))}")
            return {"x": x_grid, "y": y_grid, "z": np.asarray(z_grid)}
        except Exception as exc:
            debug_print(f"MultiViewPanel overlay build failed: {exc}")
            return None

    @staticmethod
    def _axis_for_reader(reader) -> str:
        return Heatmap2DOrientation.detect_axis(reader.dimensions)

    def _orientation(self) -> Heatmap2DOrientation:
        return Heatmap2DOrientation(self._rotation_degrees)

    def _apply_cell_width(self, file_path: str, width: int) -> None:
        self._cell_widths[file_path] = width
        header, cell = self._columns[file_path]
        header.set_cell_width(width)
        cell.set_cell_width(width)
        self._update_area_size()

    @staticmethod
    def _phase_overlay_file(file_path: str):
        debug_print("MultiViewPanel._phase_overlay_file called")
        if not file_path:
            debug_print("MultiViewPanel no file_path for phase overlay")
            return None
        file_name = Path(file_path).name
        debug_print(f"MultiViewPanel overlay source filename={file_name}")
        if file_name.startswith("PhaseField_"):
            debug_print("MultiViewPanel source is already PhaseField")
            return Path(file_path)
        suffix = file_name.split("_")[-1]
        debug_print(f"MultiViewPanel overlay suffix={suffix}")
        candidate = Path(file_path).with_name(f"PhaseField_{suffix}")
        debug_print(f"MultiViewPanel overlay candidate={candidate}")
        if candidate.exists():
            debug_print("MultiViewPanel overlay candidate exists")
            return candidate
        debug_print("MultiViewPanel overlay candidate missing")
        return None
