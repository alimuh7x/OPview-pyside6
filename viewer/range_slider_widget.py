"""Reusable dual-handle range slider widget."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPaintEvent, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.debug import debug_print


class RangeSliderWidget(QWidget):
    """Simple horizontal dual-handle slider for float ranges."""

    values_changed = Signal(float, float)

    def __init__(self, parent: QWidget | None = None) -> None:
        debug_print("RangeSliderWidget.__init__ start")
        super().__init__(parent)
        self._minimum = 0.0
        self._maximum = 1.0
        self._lower_value = 0.0
        self._upper_value = 1.0
        self._active_handle: str | None = None
        self._track_margin = 12
        self._handle_radius = 9
        self.setMinimumHeight(36)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMouseTracking(True)
        debug_print("RangeSliderWidget.__init__ complete")

    def set_bounds(self, minimum: float, maximum: float) -> None:
        debug_print("RangeSliderWidget.set_bounds called")
        minimum = float(minimum)
        maximum = float(maximum)
        if maximum < minimum:
            minimum, maximum = maximum, minimum
        if maximum == minimum:
            maximum = minimum + 1e-9
        self._minimum = minimum
        self._maximum = maximum
        debug_print(f"RangeSliderWidget bounds={self._minimum}..{self._maximum}")
        self.set_values(self._lower_value, self._upper_value, emit_signal=False)

    def set_values(self, lower: float, upper: float, *, emit_signal: bool = True) -> None:
        debug_print("RangeSliderWidget.set_values called")
        lower = self._clamp(float(lower))
        upper = self._clamp(float(upper))
        if upper < lower:
            lower, upper = upper, lower
        changed = lower != self._lower_value or upper != self._upper_value
        self._lower_value = lower
        self._upper_value = upper
        debug_print(f"RangeSliderWidget values={self._lower_value}..{self._upper_value}")
        self.update()
        if changed and emit_signal:
            debug_print("RangeSliderWidget emitting values_changed")
            self.values_changed.emit(self._lower_value, self._upper_value)

    def lower_value(self) -> float:
        debug_print("RangeSliderWidget.lower_value called")
        return self._lower_value

    def upper_value(self) -> float:
        debug_print("RangeSliderWidget.upper_value called")
        return self._upper_value

    def paintEvent(self, event: QPaintEvent) -> None:
        debug_print("RangeSliderWidget.paintEvent called")
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center_y = self.height() / 2
        left = self._track_margin
        right = max(left + 1, self.width() - self._track_margin)
        track_rect = QRectF(left, center_y - 3, right - left, 6)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#d8dde6"))
        painter.drawRoundedRect(track_rect, 3, 3)

        lower_x = self._value_to_pos(self._lower_value)
        upper_x = self._value_to_pos(self._upper_value)
        selection_rect = QRectF(lower_x, center_y - 4, max(2.0, upper_x - lower_x), 8)
        painter.setBrush(QColor("#8FAE00"))
        painter.drawRoundedRect(selection_rect, 4, 4)

        painter.setPen(QPen(QColor("#8FAE00"), 2))
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(QPoint(int(lower_x), int(center_y)), self._handle_radius, self._handle_radius)
        painter.drawEllipse(QPoint(int(upper_x), int(center_y)), self._handle_radius, self._handle_radius)
        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        debug_print("RangeSliderWidget.mousePressEvent called")
        handle = self._closest_handle(event.position().x())
        self._active_handle = handle
        debug_print(f"RangeSliderWidget active_handle={handle}")
        self._update_from_mouse(event.position().x())
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        debug_print("RangeSliderWidget.mouseMoveEvent called")
        if self._active_handle is None:
            event.ignore()
            return
        self._update_from_mouse(event.position().x())
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        debug_print("RangeSliderWidget.mouseReleaseEvent called")
        self._active_handle = None
        event.accept()

    def _update_from_mouse(self, mouse_x: float) -> None:
        debug_print("RangeSliderWidget._update_from_mouse called")
        value = self._pos_to_value(mouse_x)
        debug_print(f"RangeSliderWidget mouse value={value}")
        if self._active_handle == "lower":
            self.set_values(value, self._upper_value)
        else:
            self.set_values(self._lower_value, value)

    def _closest_handle(self, mouse_x: float) -> str:
        debug_print("RangeSliderWidget._closest_handle called")
        lower_distance = abs(mouse_x - self._value_to_pos(self._lower_value))
        upper_distance = abs(mouse_x - self._value_to_pos(self._upper_value))
        return "lower" if lower_distance <= upper_distance else "upper"

    def _clamp(self, value: float) -> float:
        debug_print("RangeSliderWidget._clamp called")
        return max(self._minimum, min(self._maximum, value))

    def _value_to_pos(self, value: float) -> float:
        debug_print("RangeSliderWidget._value_to_pos called")
        if self._maximum == self._minimum:
            return float(self._track_margin)
        usable_width = max(1.0, float(self.width() - (2 * self._track_margin)))
        ratio = (value - self._minimum) / (self._maximum - self._minimum)
        return float(self._track_margin) + (ratio * usable_width)

    def _pos_to_value(self, position_x: float) -> float:
        debug_print("RangeSliderWidget._pos_to_value called")
        usable_width = max(1.0, float(self.width() - (2 * self._track_margin)))
        clamped_x = max(float(self._track_margin), min(float(self.width() - self._track_margin), float(position_x)))
        ratio = (clamped_x - float(self._track_margin)) / usable_width
        return self._minimum + (ratio * (self._maximum - self._minimum))
