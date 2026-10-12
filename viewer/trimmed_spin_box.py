"""Double spin box with compact, range-aware display precision."""

from __future__ import annotations

from decimal import ROUND_DOWN, Decimal

from PySide6.QtWidgets import QDoubleSpinBox

from app.debug import debug_print

_BASE_DECIMALS = 2
_MAX_DISPLAY_DECIMALS = 6


def format_trimmed(value: float, decimals: int) -> str:
    """Truncate value to `decimals` places, drop trailing zeros, keep one (5 -> '5.0')."""
    quantum = Decimal(1).scaleb(-decimals)
    text = format(Decimal(repr(float(value))).quantize(quantum, rounding=ROUND_DOWN), "f")
    if "." not in text:
        text += ".0"
    text = text.rstrip("0")
    if text.endswith("."):
        text += "0"
    return "0.0" if text in ("-0.0", "") else text


def format_fixed(value: float, decimals: int) -> str:
    """Truncate value to exactly `decimals` places, zeros kept (0.52 -> '0.520')."""
    quantum = Decimal(1).scaleb(-decimals)
    text = format(Decimal(repr(float(value))).quantize(quantum, rounding=ROUND_DOWN), "f")
    return text.replace("-0.", "0.", 1) if text.startswith("-0.") and not text.strip("-0.") else text


def display_decimals(first: float, second: float) -> int:
    """Fewest decimals (>= 2) at which both values still read differently."""
    for decimals in range(_BASE_DECIMALS, _MAX_DISPLAY_DECIMALS + 1):
        if format_trimmed(first, decimals) != format_trimmed(second, decimals):
            return decimals
    return _MAX_DISPLAY_DECIMALS if first != second else _BASE_DECIMALS


class TrimmedDoubleSpinBox(QDoubleSpinBox):
    """Shows 0.0 / 5.0 / 0.52 instead of 0.000000000000 / 5.000000000000 / 0.525641560555.

    Link two boxes with `link_peer` and both show enough decimals to tell the
    min/max apart (0.52 / 0.525). The stored value keeps full precision.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._peer: TrimmedDoubleSpinBox | None = None

    def link_peer(self, peer: "TrimmedDoubleSpinBox") -> None:
        debug_print("TrimmedDoubleSpinBox.link_peer called")
        self._peer = peer
        peer._peer = self
        for box in (self, peer):
            box.valueChanged.connect(self._refresh_pair)

    def _refresh_pair(self, *_args) -> None:
        for box in (self, self._peer):
            if box is not None and not box.hasFocus():
                box.lineEdit().setText(box.textFromValue(box.value()))

    def _decimals_for_display(self) -> int:
        if self._peer is None:
            return self.decimals()
        return display_decimals(self.value(), self._peer.value())

    def textFromValue(self, value: float) -> str:  # noqa: N802
        debug_print("TrimmedDoubleSpinBox.textFromValue called")
        decimals = min(self._decimals_for_display(), self.decimals())
        if self._peer is not None and decimals > _BASE_DECIMALS:
            return format_fixed(value, decimals)
        return format_trimmed(value, decimals)

    def valueFromText(self, text: str) -> float:  # noqa: N802
        # Untouched display text must not overwrite the full-precision value.
        if text.strip() == self.textFromValue(self.value()):
            return self.value()
        return super().valueFromText(text)
