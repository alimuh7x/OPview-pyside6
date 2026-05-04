"""Pure controls widget for a viewer panel."""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.debug import debug_print
from config.constants import PALETTES
from viewer.range_slider_widget import RangeSliderWidget


class PanelControlsWidget(QWidget):
    """UI-only controls for selecting scalar and slice values."""

    refresh_requested = Signal()
    export_requested = Signal()
    range_slider_changed = Signal(float, float)

    def __init__(self, dataset_info: dict) -> None:
        debug_print("PanelControlsWidget.__init__ start")
        super().__init__()
        self.dataset_info = dataset_info
        self._last_trigger = "init"
        self._build_ui()
        self._connect_signals()
        debug_print("PanelControlsWidget.__init__ complete")

    def _build_ui(self) -> None:
        debug_print("PanelControlsWidget._build_ui called")
        self.setObjectName("controlsCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        # Row 1: project / file / scalar combos
        row1 = QWidget()
        row1.setObjectName("controlsRow")
        row1.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        row1_layout = QHBoxLayout(row1)
        row1_layout.setContentsMargins(0, 0, 0, 0)
        row1_layout.setSpacing(8)
        self.project_combo = QComboBox()
        self.project_combo.setObjectName("viewerCombo")
        self.project_combo.setEnabled(False)
        self.project_combo.addItem(self._initial_project_text())
        self.file_combo = QComboBox()
        self.file_combo.setObjectName("viewerCombo")
        self.scalar_combo = QComboBox()
        self.scalar_combo.setObjectName("viewerCombo")
        self.scalar_combo.addItem("Select scalar", "")
        row1_layout.addWidget(self.project_combo, 2)
        row1_layout.addWidget(self.file_combo, 3)
        row1_layout.addWidget(self.scalar_combo, 2)
        layout.addWidget(row1)

        # Row 2: range controls
        self.range_row = QWidget()
        self.range_row.setObjectName("controlsRow")
        self.range_row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        range_row_layout = QHBoxLayout(self.range_row)
        range_row_layout.setContentsMargins(0, 0, 0, 0)
        range_row_layout.setSpacing(8)
        self.range_label = QLabel("Range")
        self.range_label.setObjectName("mutedInfo")
        range_row_layout.addWidget(self.range_label)
        self.range_min_spin = QDoubleSpinBox()
        self.range_min_spin.setObjectName("viewerSpin")
        self.range_min_spin.setDecimals(6)
        self.range_min_spin.setRange(-1e12, 1e12)
        self.range_max_spin = QDoubleSpinBox()
        self.range_max_spin.setObjectName("viewerSpin")
        self.range_max_spin.setDecimals(6)
        self.range_max_spin.setRange(-1e12, 1e12)
        self.reset_button = QPushButton("↺")
        self.reset_button.setProperty("subtle", True)
        self.reset_button.setFixedWidth(32)
        self.click_mode_range_check = QCheckBox("Range Selection on Map")
        self.click_mode_range_check.setChecked(True)
        range_row_layout.addWidget(self.range_min_spin, 1)
        range_row_layout.addWidget(self.range_max_spin, 1)
        range_row_layout.addWidget(self.reset_button)
        range_row_layout.addWidget(self.click_mode_range_check)
        layout.addWidget(self.range_row)

        # Row 3: palette / dual range slider / full scale
        self.palette_row = QWidget()
        self.palette_row.setObjectName("controlsRow")
        self.palette_row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        palette_row_layout = QHBoxLayout(self.palette_row)
        palette_row_layout.setContentsMargins(0, 0, 0, 0)
        palette_row_layout.setSpacing(8)
        self.palette_combo = QComboBox()
        self.palette_combo.setObjectName("viewerCombo")
        for key in PALETTES:
            label = key.replace("-", " ").title()
            self.palette_combo.addItem(label, key)
        self.range_slider = RangeSliderWidget()
        self.full_scale_check = QCheckBox("Full Scale")
        palette_row_layout.addWidget(self.palette_combo, 1)
        palette_row_layout.addWidget(self.range_slider, 2)
        palette_row_layout.addWidget(self.full_scale_check)
        layout.addWidget(self.palette_row)

        # Row 4: slice (hidden until a sliceable dataset is loaded)
        self.slice_controls_container = QWidget()
        self.slice_controls_container.setObjectName("controlsRow")
        self.slice_controls_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        slice_layout = QHBoxLayout(self.slice_controls_container)
        slice_layout.setContentsMargins(0, 0, 0, 0)
        slice_layout.setSpacing(8)
        slice_label = QLabel("Slice")
        slice_label.setObjectName("mutedInfo")
        self.axis_combo = QComboBox()
        self.axis_combo.setObjectName("viewerCombo")
        self.axis_combo.addItem("X", "x")
        self.axis_combo.addItem("Y", "y")
        self.axis_combo.addItem("Z", "z")
        self.axis_combo.setFixedWidth(60)
        self.slice_slider = QSlider(Qt.Horizontal)
        self.slice_slider.setRange(0, 100)
        self.slice_slider.setValue(0)
        self.slice_value_label = QLabel("0")
        self.slice_value_label.setFixedWidth(32)
        slice_layout.addWidget(slice_label)
        slice_layout.addWidget(self.axis_combo)
        slice_layout.addWidget(self.slice_slider, 1)
        slice_layout.addWidget(self.slice_value_label)
        layout.addWidget(self.slice_controls_container)
        self.slice_controls_container.hide()

        self.status_label = QLabel("Waiting for file load")
        self.status_label.setWordWrap(True)
        self.status_label.setObjectName("mutedInfo")
        self.status_label.hide()
        debug_print("PanelControlsWidget UI ready")

    def _initial_project_text(self) -> str:
        debug_print("PanelControlsWidget._initial_project_text called")
        vtk_folder = self.dataset_info.get("vtk_folder")
        if vtk_folder:
            folder = Path(vtk_folder)
            project = folder.parent.name
            return f"{project}/{folder.name}"
        if self.dataset_info.get("project_name"):
            return self.dataset_info["project_name"]
        return "Project/VTK"

    def _connect_signals(self) -> None:
        debug_print("PanelControlsWidget._connect_signals called")
        self.file_combo.currentIndexChanged.connect(lambda *_: self._emit_refresh_requested("file"))
        self.scalar_combo.currentIndexChanged.connect(lambda *_: self._emit_refresh_requested("scalar"))
        self.axis_combo.currentIndexChanged.connect(lambda *_: self._emit_refresh_requested("axis"))
        self.slice_slider.valueChanged.connect(lambda *_: self._emit_refresh_requested("slice"))
        self.slice_slider.valueChanged.connect(self._update_slice_label)
        self.range_min_spin.valueChanged.connect(self._handle_spin_range_changed)
        self.range_max_spin.valueChanged.connect(self._handle_spin_range_changed)
        self.range_slider.values_changed.connect(self._handle_range_slider_changed)
        self.reset_button.clicked.connect(lambda *_: self._emit_refresh_requested("reset"))
        self.click_mode_range_check.toggled.connect(lambda *_: self._emit_refresh_requested("click-mode"))
        self.palette_combo.currentIndexChanged.connect(lambda *_: self._emit_refresh_requested("palette"))
        self.full_scale_check.toggled.connect(lambda *_: self._emit_refresh_requested("full-scale"))
        debug_print("PanelControlsWidget signals connected")

    def _emit_refresh_requested(self, trigger: str) -> None:
        debug_print("PanelControlsWidget._emit_refresh_requested called")
        self._last_trigger = trigger
        debug_print(f"PanelControlsWidget trigger={trigger}")
        debug_print(f"Current scalar key={self.current_scalar_key()}")
        debug_print(f"Current slice index={self.current_slice_index()}")
        self.refresh_requested.emit()
        debug_print("PanelControlsWidget emitted refresh_requested")

    def set_file_options(self, file_paths: list[str]) -> None:
        debug_print("PanelControlsWidget.set_file_options called")
        self.file_combo.blockSignals(True)
        self.file_combo.clear()
        for file_path in file_paths:
            label = Path(file_path).name
            self.file_combo.addItem(label, file_path)
        self.file_combo.blockSignals(False)
        debug_print(f"PanelControlsWidget file count={self.file_combo.count()}")

    def set_scalar_options(self, scalar_defs: list[dict]) -> None:
        debug_print("PanelControlsWidget.set_scalar_options called")
        self.scalar_combo.blockSignals(True)
        self.scalar_combo.clear()
        for scalar_def in scalar_defs:
            self.scalar_combo.addItem(scalar_def["label"], scalar_def["value"])
        self.scalar_combo.blockSignals(False)
        debug_print(f"PanelControlsWidget scalar count={self.scalar_combo.count()}")

    def set_axis(self, axis: str) -> None:
        debug_print("PanelControlsWidget.set_axis called")
        index = self.axis_combo.findData(axis)
        if index >= 0:
            self.axis_combo.setCurrentIndex(index)

    def set_slice_range(self, minimum: int, maximum: int) -> None:
        debug_print("PanelControlsWidget.set_slice_range called")
        self.slice_slider.blockSignals(True)
        self.slice_slider.setRange(minimum, maximum)
        if self.slice_slider.value() < minimum:
            self.slice_slider.setValue(minimum)
        if self.slice_slider.value() > maximum:
            self.slice_slider.setValue(maximum)
        self.slice_slider.blockSignals(False)
        self._update_slice_label()
        debug_print(f"PanelControlsWidget slice range={minimum}..{maximum}")

    def set_slice_controls_visible(self, visible: bool) -> None:
        debug_print("PanelControlsWidget.set_slice_controls_visible called")
        debug_print(f"PanelControlsWidget slice controls visible={visible}")
        self.slice_controls_container.setVisible(visible)

    def set_status_text(self, message: str) -> None:
        debug_print("PanelControlsWidget.set_status_text called")
        self.status_label.setText(message)

    def set_project_text(self, text: str) -> None:
        debug_print("PanelControlsWidget.set_project_text called")
        self.project_combo.clear()
        self.project_combo.addItem(text)

    def set_range_values(self, minimum: float, maximum: float) -> None:
        debug_print("PanelControlsWidget.set_range_values called")
        self.range_min_spin.blockSignals(True)
        self.range_max_spin.blockSignals(True)
        self.range_min_spin.setValue(minimum)
        self.range_max_spin.setValue(maximum)
        self.range_min_spin.blockSignals(False)
        self.range_max_spin.blockSignals(False)
        self.set_slider_values(minimum, maximum)

    def set_slider_bounds(self, minimum: float, maximum: float) -> None:
        debug_print("PanelControlsWidget.set_slider_bounds called")
        self.range_slider.set_bounds(minimum, maximum)

    def set_slider_values(self, minimum: float, maximum: float) -> None:
        debug_print("PanelControlsWidget.set_slider_values called")
        self.range_slider.blockSignals(True)
        self.range_slider.set_values(minimum, maximum, emit_signal=False)
        self.range_slider.blockSignals(False)

    def current_file_path(self) -> str:
        debug_print("PanelControlsWidget.current_file_path called")
        return self.file_combo.currentData() or ""

    def current_scalar_key(self) -> str:
        debug_print("PanelControlsWidget.current_scalar_key called")
        return self.scalar_combo.currentData() or ""

    def current_scalar_label(self) -> str:
        debug_print("PanelControlsWidget.current_scalar_label called")
        return self.scalar_combo.currentText()

    def current_axis(self) -> str:
        debug_print("PanelControlsWidget.current_axis called")
        return self.axis_combo.currentData() or "y"

    def current_slice_index(self) -> int:
        debug_print("PanelControlsWidget.current_slice_index called")
        return self.slice_slider.value()

    def current_palette(self) -> str:
        debug_print("PanelControlsWidget.current_palette called")
        return self.palette_combo.currentData() or "aqua-fire"

    def current_range(self) -> tuple[float, float]:
        debug_print("PanelControlsWidget.current_range called")
        return (self.range_min_spin.value(), self.range_max_spin.value())

    def full_scale_enabled(self) -> bool:
        debug_print("PanelControlsWidget.full_scale_enabled called")
        return self.full_scale_check.isChecked()

    def click_mode(self) -> str:
        debug_print("PanelControlsWidget.click_mode called")
        return "range" if self.click_mode_range_check.isChecked() else "linescan"

    def _update_slice_label(self) -> None:
        debug_print("PanelControlsWidget._update_slice_label called")
        self.slice_value_label.setText(str(self.slice_slider.value()))

    def last_trigger(self) -> str:
        debug_print("PanelControlsWidget.last_trigger called")
        return self._last_trigger

    def _handle_range_slider_changed(self, minimum: float, maximum: float) -> None:
        debug_print("PanelControlsWidget._handle_range_slider_changed called")
        debug_print(f"PanelControlsWidget slider changed={minimum}..{maximum}")
        self.range_min_spin.blockSignals(True)
        self.range_max_spin.blockSignals(True)
        self.range_min_spin.setValue(minimum)
        self.range_max_spin.setValue(maximum)
        self.range_min_spin.blockSignals(False)
        self.range_max_spin.blockSignals(False)
        self.range_slider_changed.emit(minimum, maximum)
        self._emit_refresh_requested("range-slider")

    def _handle_spin_range_changed(self, *_args) -> None:
        debug_print("PanelControlsWidget._handle_spin_range_changed called")
        minimum = self.range_min_spin.value()
        maximum = self.range_max_spin.value()
        debug_print(f"PanelControlsWidget spin range raw={minimum}..{maximum}")
        self.set_slider_values(minimum, maximum)
        self._emit_refresh_requested("range")
