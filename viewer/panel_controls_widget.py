"""Pure controls widget for a viewer panel."""

from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QSize, QRect, Signal
from PySide6.QtGui import QIcon, QPen
from PySide6.QtWidgets import (
    QDialog,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStyle,
    QSlider,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)

from app.debug import debug_print
from config.constants import PALETTES
from utils.combo_box_utils import update_combo_popup_width
from viewer.plot_types import PLOT_TYPE_REGISTRY
from viewer.range_slider_widget import RangeSliderWidget
from viewer.toggle_switch_widget import ToggleSwitchWidget

_ASSETS = Path(__file__).parent.parent / "assets"


class _PhaseFractionRenameDelegate(QStyledItemDelegate):
    """Draw the phase rename icon in a fixed right-side popup slot."""

    def __init__(self, controls: "PanelControlsWidget") -> None:
        debug_print("_PhaseFractionRenameDelegate.__init__ called")
        super().__init__(controls.scalar_combo)
        self._controls = controls

    def paint(self, painter, option, index) -> None:  # noqa: N802
        super().paint(painter, option, index)
        key = index.data(Qt.ItemDataRole.UserRole)
        if not self._controls.is_phase_fraction_key(key):
            return
        debug_print("_PhaseFractionRenameDelegate.paint phase fraction")
        debug_print(f"_PhaseFractionRenameDelegate key={key}")
        icon_rect = self._rename_icon_rect(option.rect)
        debug_print(f"_PhaseFractionRenameDelegate icon_rect={icon_rect}")
        icon_color = self._rename_icon_color(option)
        debug_print(f"_PhaseFractionRenameDelegate icon_color={icon_color.name()}")
        painter.save()
        painter.setPen(QPen(icon_color))
        painter.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, "✎")
        painter.restore()

    @staticmethod
    def _rename_icon_rect(row_rect: QRect) -> QRect:
        width = 28
        return QRect(row_rect.right() - width + 1, row_rect.top(), width, row_rect.height())

    @staticmethod
    def _rename_icon_color(option):
        debug_print("_PhaseFractionRenameDelegate._rename_icon_color called")
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        debug_print(f"_PhaseFractionRenameDelegate hovered={hovered}")
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        debug_print(f"_PhaseFractionRenameDelegate selected={selected}")
        if hovered or selected:
            debug_print("_PhaseFractionRenameDelegate using highlighted text color")
            return option.palette.highlightedText().color()
        debug_print("_PhaseFractionRenameDelegate using normal text color")
        return option.palette.text().color()


class PanelControlsWidget(QWidget):
    """UI-only controls for selecting scalar and slice values."""

    refresh_requested = Signal()
    export_requested = Signal()
    range_slider_changed = Signal(float, float)
    phase_fraction_selection_changed = Signal()

    def __init__(self, dataset_info: dict) -> None:
        debug_print("PanelControlsWidget.__init__ start")
        super().__init__()
        self.dataset_info = dataset_info
        self._last_trigger = "init"
        self._layout_mode = ""
        self._phase_fraction_keys: list[str] = []
        self._phase_fraction_aliases: dict[str, str] = {}
        self._build_ui()
        self._connect_signals()
        self.scalar_combo.view().viewport().installEventFilter(self)
        debug_print("PanelControlsWidget.__init__ complete")

    def _build_ui(self) -> None:
        debug_print("PanelControlsWidget._build_ui called")
        self.setObjectName("controlsCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(self)
        self._root_layout = layout
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
        self._configure_compact_combo(self.project_combo, 8)
        self.file_combo = QComboBox()
        self.file_combo.setObjectName("viewerCombo")
        self._configure_compact_combo(self.file_combo, 12)
        self.scalar_combo = QComboBox()
        self.scalar_combo.setObjectName("viewerCombo")
        self._configure_compact_combo(self.scalar_combo, 10)
        self.scalar_combo.setItemDelegate(_PhaseFractionRenameDelegate(self))
        debug_print("PanelControlsWidget scalar phase rename delegate installed")
        self.scalar_combo.addItem("Select scalar", "")
        update_combo_popup_width(self.scalar_combo)
        row1_layout.addWidget(self.project_combo, 2)
        row1_layout.addWidget(self.file_combo, 3)
        row1_layout.addWidget(self.scalar_combo, 2)
        layout.addWidget(row1)

        # ------------------------------------------------------------------------------------------------
        # Row 2: range controls
        # ------------------------------------------------------------------------------------------------
        self.range_row = QWidget()
        self.range_row.setObjectName("controlsRow")
        self.range_row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        range_row_layout = QHBoxLayout(self.range_row)
        self.range_row_layout = range_row_layout
        range_row_layout.setContentsMargins(0, 0, 0, 0)
        range_row_layout.setSpacing(8)
        self.plot_type_combo  = QComboBox()
        self.plot_type_combo.setObjectName("viewerCombo")
        self._configure_compact_combo(self.plot_type_combo, 8)
        for renderer in PLOT_TYPE_REGISTRY:
            self.plot_type_combo.addItem(renderer.label, renderer.key)
        update_combo_popup_width(self.plot_type_combo)
        self.range_label = QLabel("Range")
        self.range_label.setObjectName("mutedInfo")

        self.range_min_spin = QDoubleSpinBox()
        self.range_min_spin.setObjectName("viewerSpin")
        self.range_min_spin.setProperty("rangeSpin", True)
        self.range_min_spin.setDecimals(6)
        self.range_min_spin.setRange(-1e12, 1e12)
        self.range_min_spin.setKeyboardTracking(False)
        debug_print("PanelControlsWidget range_min_spin keyboard tracking disabled")
        self.range_min_spin.setMinimumWidth(120)
        self.range_min_spin.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        debug_print("PanelControlsWidget range_min_spin min width set to 120")
        self.range_max_spin = QDoubleSpinBox()
        self.range_max_spin.setObjectName("viewerSpin")
        self.range_max_spin.setProperty("rangeSpin", True)
        self.range_max_spin.setDecimals(6)
        self.range_max_spin.setRange(-1e12, 1e12)
        self.range_max_spin.setKeyboardTracking(False)
        debug_print("PanelControlsWidget range_max_spin keyboard tracking disabled")
        self.range_max_spin.setMinimumWidth(120)
        self.range_max_spin.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        debug_print("PanelControlsWidget range_max_spin min width set to 120")

        self.reset_button = QPushButton()
        self.reset_button.setIcon(QIcon(str(_ASSETS / "refresh.png")))
        self.reset_button.setIconSize(QSize(16, 16))
        self.reset_button.setProperty("subtle", True)
        self.reset_button.setFixedSize(32, 32)
        self.reset_button.setToolTip("Reset range to data min/max")

        self.click_mode_range_check = ToggleSwitchWidget("Range Selection on Map", checked=True)
        layout.addWidget(self.range_row)
        self.range_values_row = QWidget()
        self.range_values_row.setObjectName("controlsRow")
        self.range_values_row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.range_values_row_layout = QHBoxLayout(self.range_values_row)
        self.range_values_row_layout.setContentsMargins(0, 0, 0, 0)
        self.range_values_row_layout.setSpacing(8)
        layout.addWidget(self.range_values_row)

        # ------------------------------------------------------------------------------------------------
        # Row 3: palette / dual range slider / full scale
        # ------------------------------------------------------------------------------------------------
        self.palette_row = QWidget()
        self.palette_row.setObjectName("controlsRow")
        self.palette_row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        palette_row_layout = QHBoxLayout(self.palette_row)
        palette_row_layout.setContentsMargins(0, 0, 0, 0)
        palette_row_layout.setSpacing(8)
        self.palette_combo = QComboBox()
        self.palette_combo.setObjectName("viewerCombo")
        self._configure_compact_combo(self.palette_combo, 8)
        for key in PALETTES:
            label = key.replace("-", " ").title()
            self.palette_combo.addItem(label, key)
        update_combo_popup_width(self.palette_combo)
        self.range_slider = RangeSliderWidget()
        self.full_scale_check = ToggleSwitchWidget("Full Scale", checked=False)

        # ------------------------------------------------------------------------------------------------
        # Rotation in single view
        # ------------------------------------------------------------------------------------------------
        self.rotation_combo = QComboBox()
        self.rotation_combo.setObjectName("viewerCombo")
        self._configure_compact_combo(self.rotation_combo, 8)
        self.rotation_combo.addItem("0 deg", 0)
        self.rotation_combo.addItem("90 deg", 90)
        self.rotation_combo.addItem("180 deg", 180)
        self.rotation_combo.addItem("270 deg", 270)
        update_combo_popup_width(self.rotation_combo)

        palette_row_layout.addWidget(self.palette_combo, 1)
        palette_row_layout.addWidget(self.range_slider, 4)
        palette_row_layout.addWidget(self.full_scale_check)
        palette_row_layout.addWidget(self.rotation_combo)
        layout.addWidget(self.palette_row)
        self._apply_layout_mode("wide", force=True)
        # ------------------------------------------------------------------------------------------------

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
        self._configure_compact_combo(self.axis_combo, 1)
        self.axis_combo.addItem("X", "x")
        self.axis_combo.addItem("Y", "y")
        self.axis_combo.addItem("Z", "z")
        self.axis_combo.setFixedWidth(60)
        update_combo_popup_width(self.axis_combo)
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

    def _configure_compact_combo(self, combo: QComboBox, minimum_contents_length: int) -> None:
        debug_print("PanelControlsWidget._configure_compact_combo called")
        combo.setMinimumContentsLength(minimum_contents_length)
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        debug_print(
            f"PanelControlsWidget compact combo configured length={minimum_contents_length}"
        )

    def _clear_layout(self, target_layout: QHBoxLayout) -> None:
        debug_print("PanelControlsWidget._clear_layout called")
        while target_layout.count():
            item = target_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(self)
                debug_print(
                    "PanelControlsWidget temporarily removed "
                    f"{widget.objectName() or widget.__class__.__name__}"
                )

    def _apply_layout_mode(self, mode: str, *, force: bool = False) -> None:
        debug_print("PanelControlsWidget._apply_layout_mode called")
        if mode == self._layout_mode and not force:
            debug_print(f"PanelControlsWidget layout mode unchanged={mode}")
            self._debug_range_layout("unchanged")
            return
        debug_print(f"PanelControlsWidget changing layout mode from={self._layout_mode} to={mode}")
        self._clear_layout(self.range_row_layout)
        self._clear_layout(self.range_values_row_layout)
        if mode == "compact":
            debug_print("PanelControlsWidget applying compact range rows")
            self.click_mode_range_check.setText("Range")
            self.click_mode_range_check.setToolTip("Range Selection on Map")
            self.range_row_layout.setSpacing(8)
            self.range_values_row_layout.setSpacing(2)
            self.range_row_layout.addWidget(self.plot_type_combo, 1)
            self.range_row_layout.addWidget(self.click_mode_range_check)
            self.range_values_row_layout.addWidget(self.range_label)
            self.range_values_row_layout.addWidget(self.range_min_spin, 1)
            self.range_values_row_layout.addWidget(self.range_max_spin, 1)
            self.range_values_row_layout.addWidget(self.reset_button)
            self.range_values_row.show()
        else:
            debug_print("PanelControlsWidget applying wide range row")
            self.click_mode_range_check.setText("Range Selection on Map")
            self.click_mode_range_check.setToolTip("")
            self.range_row_layout.setSpacing(8)
            self.range_values_row_layout.setSpacing(8)
            self.range_row_layout.addWidget(self.plot_type_combo)
            self.range_row_layout.addWidget(self.range_label)
            self.range_row_layout.addWidget(self.range_min_spin, 1)
            self.range_row_layout.addWidget(self.range_max_spin, 1)
            self.range_row_layout.addWidget(self.reset_button)
            self.range_row_layout.addWidget(self.click_mode_range_check)
            self.range_values_row.hide()
        self._layout_mode = mode
        self.range_row.updateGeometry()
        self.range_values_row.updateGeometry()
        self.updateGeometry()
        self._debug_range_layout("applied")

    def _update_layout_mode_for_width(self, width: int) -> None:
        debug_print("PanelControlsWidget._update_layout_mode_for_width called")
        bounded_width = max(0, int(width))
        mode = "compact" if bounded_width and bounded_width < 680 else "wide"
        debug_print(f"PanelControlsWidget current width={bounded_width}")
        debug_print(f"PanelControlsWidget selected layout mode={mode}")
        self._apply_layout_mode(mode)

    def _debug_range_layout(self, reason: str) -> None:
        debug_print(f"PanelControlsWidget._debug_range_layout reason={reason}")
        debug_print(f"PanelControlsWidget layout mode={self._layout_mode}")
        debug_print(f"PanelControlsWidget widget width={self.width()}")
        debug_print(f"PanelControlsWidget max width={self.maximumWidth()}")
        debug_print(f"PanelControlsWidget range row min={self.range_row_layout.minimumSize().width()}")
        debug_print(f"PanelControlsWidget range row actual={self.range_row.width()}")
        debug_print(f"PanelControlsWidget values row min={self.range_values_row_layout.minimumSize().width()}")
        debug_print(f"PanelControlsWidget values row actual={self.range_values_row.width()}")
        debug_print(f"PanelControlsWidget range_min min={self.range_min_spin.minimumWidth()}")
        debug_print(f"PanelControlsWidget range_min hint={self.range_min_spin.sizeHint().width()}")
        debug_print(f"PanelControlsWidget range_min actual={self.range_min_spin.width()}")
        debug_print(f"PanelControlsWidget range_max min={self.range_max_spin.minimumWidth()}")
        debug_print(f"PanelControlsWidget range_max hint={self.range_max_spin.sizeHint().width()}")
        debug_print(f"PanelControlsWidget range_max actual={self.range_max_spin.width()}")

    def layout_mode(self) -> str:
        debug_print("PanelControlsWidget.layout_mode called")
        return self._layout_mode

    def _connect_signals(self) -> None:
        debug_print("PanelControlsWidget._connect_signals called")
        self.project_combo.currentIndexChanged.connect(lambda *_: self._emit_refresh_requested("project"))
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
        self.rotation_combo.currentIndexChanged.connect(lambda *_: self._emit_refresh_requested("rotation"))
        self.plot_type_combo.currentIndexChanged.connect(lambda *_: self._emit_refresh_requested("plot-type"))
        debug_print("PanelControlsWidget signals connected")

    def set_available_width(self, width: int) -> None:
        """Constrain controls to the current app content width."""
        debug_print(f"PanelControlsWidget.set_available_width width={width}")
        bounded_width = max(0, int(width))
        self.setMinimumWidth(0)
        self.setMaximumWidth(bounded_width)
        self._update_layout_mode_for_width(bounded_width)
        controls = [
            self.project_combo,
            self.file_combo,
            self.scalar_combo,
            self.plot_type_combo,
            self.range_min_spin,
            self.range_max_spin,
            self.palette_combo,
            self.rotation_combo,
            self.range_slider,
            self.axis_combo,
            self.slice_slider,
        ]
        for control in controls:
            minimum = control.minimumWidth()
            control.setMaximumWidth(max(bounded_width, minimum))
            debug_print(
                f"PanelControlsWidget capped {control.objectName() or control.__class__.__name__} "
                f"to {control.maximumWidth()}"
            )
        self._debug_range_layout("set-available-width")

    def resizeEvent(self, event) -> None:  # noqa: N802
        debug_print("PanelControlsWidget.resizeEvent called")
        super().resizeEvent(event)
        self._update_layout_mode_for_width(event.size().width())

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
        update_combo_popup_width(self.file_combo)
        debug_print(f"PanelControlsWidget file count={self.file_combo.count()}")

    def set_scalar_options(self, scalar_defs: list[dict]) -> None:
        debug_print("PanelControlsWidget.set_scalar_options called")
        previous_checked = set(self.selected_phase_fraction_keys())
        debug_print(f"PanelControlsWidget previous checked phase fractions={sorted(previous_checked)}")
        self.scalar_combo.blockSignals(True)
        self.scalar_combo.clear()
        self._phase_fraction_keys = []
        for scalar_def in scalar_defs:
            key = scalar_def["value"]
            is_phase_fraction = self._is_phase_fraction_scalar(scalar_def)
            label = self._phase_fraction_combo_text(key, scalar_def["label"]) if is_phase_fraction else scalar_def["label"]
            self.scalar_combo.addItem(label, key)
            debug_print(f"PanelControlsWidget scalar option label={scalar_def['label']}")
            debug_print(f"PanelControlsWidget scalar option value={key}")
            debug_print(f"PanelControlsWidget scalar option is_phase_fraction={is_phase_fraction}")
            if is_phase_fraction:
                self._phase_fraction_keys.append(key)
                index = self.scalar_combo.count() - 1
                checked = key in previous_checked or not previous_checked
                self.scalar_combo.setItemData(
                    index,
                    Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked,
                    Qt.ItemDataRole.CheckStateRole,
                )
                self.scalar_combo.setItemData(
                    index,
                    Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled,
                    Qt.ItemDataRole.UserRole + 1,
                )
                debug_print(f"PanelControlsWidget phase fraction check initialized key={key}")
                debug_print(f"PanelControlsWidget phase fraction checked={checked}")
        self.scalar_combo.blockSignals(False)
        update_combo_popup_width(self.scalar_combo)
        debug_print(f"PanelControlsWidget scalar count={self.scalar_combo.count()}")
        debug_print(f"PanelControlsWidget phase fraction count={len(self._phase_fraction_keys)}")

    def _phase_fraction_combo_text(self, key: str, fallback: str | None = None) -> str:
        debug_print("PanelControlsWidget._phase_fraction_combo_text called")
        display = self.phase_fraction_display_label(key, fallback)
        debug_print(f"PanelControlsWidget phase fraction combo text={display}")
        return display

    def phase_fraction_click_role(self, row: int, click_x: float, viewport_width: int) -> str:
        """Return checkbox, rename, or select for a phase-fraction popup click."""
        debug_print("PanelControlsWidget.phase_fraction_click_role called")
        debug_print(f"PanelControlsWidget click role row={row}")
        debug_print(f"PanelControlsWidget click role x={click_x}")
        debug_print(f"PanelControlsWidget click role viewport_width={viewport_width}")
        if click_x <= 34:
            debug_print("PanelControlsWidget click role=checkbox")
            return "checkbox"
        rename_width = 28
        debug_print(f"PanelControlsWidget click role rename_width={rename_width}")
        rename_start = max(35, viewport_width - rename_width)
        debug_print(f"PanelControlsWidget click role rename_start={rename_start}")
        debug_print(f"PanelControlsWidget click role rename_end={viewport_width}")
        if click_x >= rename_start:
            debug_print("PanelControlsWidget click role=rename")
            return "rename"
        debug_print("PanelControlsWidget click role=select")
        return "select"

    def _is_phase_fraction_scalar(self, scalar_def: dict) -> bool:
        debug_print("PanelControlsWidget._is_phase_fraction_scalar called")
        label = str(scalar_def.get("label", ""))
        array = str(scalar_def.get("array", ""))
        component = scalar_def.get("component")
        result = component is None and (label.startswith("PhaseFraction_") or array.startswith("PhaseFraction_"))
        debug_print(f"PanelControlsWidget phase fraction result={result}")
        return result

    def is_phase_fraction_key(self, key: str) -> bool:
        debug_print("PanelControlsWidget.is_phase_fraction_key called")
        debug_print(f"PanelControlsWidget phase fraction key query={key}")
        return key in self._phase_fraction_keys

    def phase_fraction_display_label(self, key: str, fallback: str | None = None) -> str:
        debug_print("PanelControlsWidget.phase_fraction_display_label called")
        debug_print(f"PanelControlsWidget display label key={key}")
        label = self._phase_fraction_aliases.get(key) or fallback or key
        debug_print(f"PanelControlsWidget display label={label}")
        return label

    def rename_phase_fraction(self, key: str, alias: str) -> None:
        debug_print("PanelControlsWidget.rename_phase_fraction called")
        debug_print(f"PanelControlsWidget rename key={key}")
        old_label = self.phase_fraction_display_label(key)
        alias = alias.strip()
        debug_print(f"PanelControlsWidget rename old label={old_label}")
        debug_print(f"PanelControlsWidget rename new label={alias}")
        if key not in self._phase_fraction_keys:
            debug_print("PanelControlsWidget rename skipped non phase fraction")
            return
        if alias:
            self._phase_fraction_aliases[key] = alias
        else:
            self._phase_fraction_aliases.pop(key, None)
        index = self.scalar_combo.findData(key)
        if index >= 0:
            self.scalar_combo.setItemText(index, self._phase_fraction_combo_text(key))
            update_combo_popup_width(self.scalar_combo)
        debug_print(f"PanelControlsWidget rename aliases={self._phase_fraction_aliases}")
        self.phase_fraction_selection_changed.emit()
        debug_print("PanelControlsWidget emitted phase_fraction_selection_changed after rename")

    def _open_phase_fraction_rename_dialog(self, key: str) -> None:
        debug_print("PanelControlsWidget._open_phase_fraction_rename_dialog called")
        debug_print(f"PanelControlsWidget rename dialog key={key}")
        current_label = self.phase_fraction_display_label(key)
        dialog = self._build_phase_fraction_rename_dialog(key, current_label)
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        new_label = dialog.textValue()
        debug_print(f"PanelControlsWidget rename dialog accepted={accepted}")
        debug_print(f"PanelControlsWidget rename dialog value={new_label}")
        if accepted:
            self.rename_phase_fraction(key, new_label)

    def _build_phase_fraction_rename_dialog(self, key: str, current_label: str) -> QInputDialog:
        debug_print("PanelControlsWidget._build_phase_fraction_rename_dialog called")
        debug_print(f"PanelControlsWidget build rename dialog key={key}")
        debug_print(f"PanelControlsWidget build rename dialog current_label={current_label}")
        dialog = QInputDialog(self)
        dialog.setObjectName("phaseRenameDialog")
        dialog.setWindowTitle("Rename Phase")
        dialog.setLabelText(f"{key}\nName:")
        dialog.setTextValue(current_label)
        dialog.setInputMode(QInputDialog.InputMode.TextInput)
        dialog.setMinimumWidth(360)
        dialog.setStyleSheet(
            """
QInputDialog#phaseRenameDialog {
    background: #f7f9fc;
    color: #102a52;
}
QInputDialog#phaseRenameDialog QLabel {
    color: #102a52;
    background: transparent;
}
QInputDialog#phaseRenameDialog QLineEdit {
    background: #ffffff;
    color: #102a52;
    border: 1px solid #ccd7e8;
    border-radius: 8px;
    padding: 6px 8px;
    selection-background-color: #d9e7ff;
    selection-color: #102a52;
}
QInputDialog#phaseRenameDialog QPushButton {
    background: #ffffff;
    color: #102a52;
    border: 1px solid #d2dbea;
    border-radius: 8px;
    padding: 6px 12px;
    font-weight: 700;
}
QInputDialog#phaseRenameDialog QPushButton:hover {
    background: #eef4ff;
    border-color: #9fb5d6;
}
"""
        )
        debug_print("PanelControlsWidget phase rename dialog styled")
        return dialog

    def selected_phase_fraction_keys(self) -> list[str]:
        debug_print("PanelControlsWidget.selected_phase_fraction_keys called")
        selected: list[str] = []
        for index in range(self.scalar_combo.count()):
            key = self.scalar_combo.itemData(index)
            if key not in self._phase_fraction_keys:
                continue
            check_state = self.scalar_combo.itemData(index, Qt.ItemDataRole.CheckStateRole)
            debug_print(f"PanelControlsWidget phase fraction key={key}")
            debug_print(f"PanelControlsWidget phase fraction check_state={check_state}")
            if check_state == Qt.CheckState.Checked:
                selected.append(key)
        debug_print(f"PanelControlsWidget selected phase fractions={selected}")
        return selected

    def set_phase_fraction_checked(self, key: str, checked: bool) -> None:
        debug_print("PanelControlsWidget.set_phase_fraction_checked called")
        debug_print(f"PanelControlsWidget set phase fraction key={key}")
        debug_print(f"PanelControlsWidget set phase fraction checked={checked}")
        index = self.scalar_combo.findData(key)
        if index < 0 or key not in self._phase_fraction_keys:
            debug_print("PanelControlsWidget phase fraction check skipped")
            return
        self.scalar_combo.setItemData(
            index,
            Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked,
            Qt.ItemDataRole.CheckStateRole,
        )
        debug_print("PanelControlsWidget phase fraction check state updated")
        self.phase_fraction_selection_changed.emit()
        debug_print("PanelControlsWidget phase_fraction_selection_changed emitted")

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if watched is self.scalar_combo.view().viewport() and event.type() == QEvent.Type.MouseButtonRelease:
            index = self.scalar_combo.view().indexAt(event.position().toPoint())
            if not index.isValid():
                return super().eventFilter(watched, event)
            key = self.scalar_combo.itemData(index.row())
            if key not in self._phase_fraction_keys:
                return super().eventFilter(watched, event)
            click_x = event.position().x()
            debug_print("PanelControlsWidget scalar popup phase fraction click")
            debug_print(f"PanelControlsWidget clicked phase fraction key={key}")
            debug_print(f"PanelControlsWidget click x={click_x}")
            role = self.phase_fraction_click_role(
                index.row(),
                click_x,
                self.scalar_combo.view().viewport().width(),
            )
            if role == "checkbox":
                current = self.scalar_combo.itemData(index.row(), Qt.ItemDataRole.CheckStateRole)
                next_checked = current != Qt.CheckState.Checked
                debug_print(f"PanelControlsWidget checkbox click next_checked={next_checked}")
                self.set_phase_fraction_checked(key, next_checked)
                self.scalar_combo.showPopup()
                return True
            if role == "rename":
                debug_print("PanelControlsWidget pencil click opening rename")
                self.scalar_combo.hidePopup()
                self._open_phase_fraction_rename_dialog(key)
                return True
            debug_print("PanelControlsWidget row text click selecting active phase fraction")
            self.scalar_combo.blockSignals(True)
            self.scalar_combo.setCurrentIndex(index.row())
            self.scalar_combo.blockSignals(False)
            self.scalar_combo.hidePopup()
            self._emit_refresh_requested("scalar")
            return True
        return super().eventFilter(watched, event)

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

    def set_project_options(self, projects: list[dict]) -> None:
        debug_print("PanelControlsWidget.set_project_options called")
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        for p in projects:
            folder = Path(p["vtk_folder"])
            label = f"{folder.parent.name}/{folder.name}"
            self.project_combo.addItem(label, p)
        self.project_combo.blockSignals(False)
        update_combo_popup_width(self.project_combo)
        debug_print(f"PanelControlsWidget project options count={self.project_combo.count()}")

    def current_project_info(self) -> dict:
        debug_print("PanelControlsWidget.current_project_info called")
        return self.project_combo.currentData() or {}

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
        key = self.current_scalar_key()
        debug_print(f"PanelControlsWidget current scalar label key={key}")
        if key in self._phase_fraction_keys:
            label = self.phase_fraction_display_label(key)
            debug_print(f"PanelControlsWidget current scalar phase label={label}")
            return label
        label = self.scalar_combo.currentText()
        debug_print(f"PanelControlsWidget current scalar label={label}")
        return label

    def current_axis(self) -> str:
        debug_print("PanelControlsWidget.current_axis called")
        return self.axis_combo.currentData() or "y"

    def current_slice_index(self) -> int:
        debug_print("PanelControlsWidget.current_slice_index called")
        return self.slice_slider.value()

    def current_palette(self) -> str:
        debug_print("PanelControlsWidget.current_palette called")
        return self.palette_combo.currentData() or "aqua-fire"

    def current_rotation_degrees(self) -> int:
        debug_print("PanelControlsWidget.current_rotation_degrees called")
        return int(self.rotation_combo.currentData() or 0)

    def current_range(self) -> tuple[float, float]:
        debug_print("PanelControlsWidget.current_range called")
        return (self.range_min_spin.value(), self.range_max_spin.value())

    def full_scale_enabled(self) -> bool:
        debug_print("PanelControlsWidget.full_scale_enabled called")
        return self.full_scale_check.isChecked()

    def current_plot_type(self) -> str:
        return self.plot_type_combo.currentData() or "heatmap"

    def click_mode(self) -> str:
        debug_print("PanelControlsWidget.click_mode called")
        return "range" if self.click_mode_range_check.isChecked() else "linescan"

    def _update_slice_label(self) -> None:
        debug_print("PanelControlsWidget._update_slice_label called")
        self.slice_value_label.setText(str(self.slice_slider.value()))

    def last_trigger(self) -> str:
        debug_print("PanelControlsWidget.last_trigger called")
        return self._last_trigger

    def set_last_trigger(self, trigger: str) -> None:
        """Record a refresh trigger from controls that live outside this widget."""
        debug_print("PanelControlsWidget.set_last_trigger called")
        self._last_trigger = trigger
        debug_print(f"PanelControlsWidget external trigger={trigger}")

    def _handle_range_slider_changed(self, minimum: float, maximum: float) -> None:
        debug_print("PanelControlsWidget._handle_range_slider_changed called")
        debug_print(f"PanelControlsWidget slider changed={minimum}..{maximum}")
        if self.full_scale_check.isChecked():
            debug_print("PanelControlsWidget disabling full scale after slider range edit")
            self.full_scale_check.blockSignals(True)
            self.full_scale_check.setChecked(False)
            self.full_scale_check.blockSignals(False)
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
        if self.full_scale_check.isChecked():
            debug_print("PanelControlsWidget disabling full scale after spin range edit")
            self.full_scale_check.blockSignals(True)
            self.full_scale_check.setChecked(False)
            self.full_scale_check.blockSignals(False)
        self.set_slider_values(minimum, maximum)
        self._emit_refresh_requested("range")
