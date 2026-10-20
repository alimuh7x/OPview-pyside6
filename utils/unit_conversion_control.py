"""From -> to unit control shared by Single View, Multi View and Multi Property.

The dropdowns name scales, not units: `milli (m)`, `base`, `kilo (k)`, `Mega (M)` ... The data already says
which unit it is in (Pa, m, N, ...), so that is not repeated; the unit stays behind each entry as its data and
reaches the colorbar title (`MPa`).

The views multiply every displayed value by one factor, so only units related by a pure scale are offered
(`config.units.scale_between`); temperature, which needs an offset, is Custom Graph only.

The control follows the old single "conversion" dropdown closely so the views barely change: `currentData()`
still returns `(scale, unit_suffix)` and `currentIndexChanged` still fires when the user changes a choice.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget

from app.debug import debug_print
from config import units
from utils.combo_box_utils import update_combo_popup_width

NO_UNIT = "-"  # the dimensionless unit of the strain family (data with no unit)
NO_CONVERSION = "\u2014"  # first entry of To: leave the values as they are
_COMBO_WIDTH = 126  # fits "percent (%)" and "minute (min)" in the viewer combo style


class UnitConversionControl(QWidget):
    """`[from unit] -> [to unit]`; the displayed value is multiplied by the factor between the two."""

    currentIndexChanged = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        debug_print("UnitConversionControl.__init__ called")
        self.setObjectName("unitConversionControl")
        self._native = NO_UNIT
        self.from_combo = self._build_combo("Unit of the values shown, filled in from the data")
        self.to_combo = self._build_combo("Convert the display to this unit")
        self._family: list[str] = []
        self._fill_from(NO_UNIT)
        self._fill_to(NO_UNIT, NO_UNIT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.from_combo)
        arrow = QLabel("→")
        arrow.setObjectName("mutedInfo")
        layout.addWidget(arrow)
        layout.addWidget(self.to_combo)

        self.from_combo.currentIndexChanged.connect(self._on_from_changed)
        self.to_combo.currentIndexChanged.connect(self._on_changed)

    # ------------------------------------------------------------------ #
    # Public                                                              #
    # ------------------------------------------------------------------ #

    def from_unit(self) -> str:
        return self.from_combo.currentData() or NO_UNIT

    def to_unit(self) -> str:
        return self.to_combo.currentData() or NO_UNIT

    def currentData(self) -> tuple[float, str]:
        """`(scale, suffix)`: the factor to multiply values by and the unit to show in labels ("" for none)."""
        factor = units.scale_between(self.from_unit(), self.to_unit())
        return (1.0 if factor is None else float(factor)), units.display_unit(self.to_unit())

    def set_native_unit(self, unit) -> bool:
        """Follow the unit of the data now shown. The user's choices stay while it is the same unit.

        Never emits: callers change the shown data themselves and read `currentData()` as they redraw.
        Returns True when the unit changed (and so the From/To choices were reset).
        """
        native = units.normalize_unit(unit) or NO_UNIT
        if native == self._native:
            return False
        debug_print(f"UnitConversionControl.set_native_unit {self._native} -> {native}")
        self._native = native
        self._fill_from(native)
        self._fill_to(native, native)
        return True

    # ------------------------------------------------------------------ #
    # Internals                                                           #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_combo(tooltip: str) -> QComboBox:
        combo = QComboBox()
        combo.setObjectName("viewerCombo")
        combo.setFixedWidth(_COMBO_WIDTH)
        combo.setToolTip(tooltip)
        return combo

    def _fill_from(self, selected: str) -> None:
        """From lists the scale of the data's own unit by prefix; for data of unknown unit also the units to declare.

        The list belongs to the data, not to the selection, so it stays put while the user picks from it.
        """
        no_unit = not units.display_unit(self._native)
        self._family = units.family_units(NO_UNIT if no_unit else self._native, scale_only=True)
        combo = self.from_combo
        combo.blockSignals(True)
        combo.clear()
        for unit in self._family:
            combo.addItem(units.scale_label(unit), unit)
        if no_unit:
            for base in units.declarable_units(scale_only=True):
                combo.addItem(base, base)
        combo.setCurrentIndex(max(0, combo.findData(selected)))
        update_combo_popup_width(combo)
        combo.blockSignals(False)

    def _fill_to(self, source: str, selected: str) -> None:
        """To lists the scale without the unit chosen in From, led by an em dash for no conversion.

        `selected` stays chosen when it is still on the list; otherwise there is no conversion.
        """
        combo = self.to_combo
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(NO_CONVERSION, source)  # data is the source itself: converting to it changes nothing
        for unit in units.family_units(source, scale_only=True):
            if unit != source:
                combo.addItem(units.scale_label(unit), unit)
        index = combo.findData(selected)
        combo.setCurrentIndex(index if index >= 0 else 0)
        update_combo_popup_width(combo)
        combo.blockSignals(False)

    def _on_from_changed(self, index: int) -> None:
        self._fill_to(self.from_unit(), self.to_unit())  # To follows the choice; From stays as it is
        self.currentIndexChanged.emit(index)

    def _on_changed(self, index: int) -> None:
        self.currentIndexChanged.emit(index)
