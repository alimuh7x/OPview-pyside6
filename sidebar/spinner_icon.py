"""Rotating arc shown as a button icon while a blocking action runs."""

from PySide6.QtCore import QObject, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QAbstractButton

from app.debug import debug_print

_ICON_SIZE = 18
_STEP_DEGREES = 30
_FRAME_INTERVAL_MS = 60
_ARC_SPAN_DEGREES = 270


def _arc_icon(angle: int, color: QColor, size: int = _ICON_SIZE) -> QIcon:
    ratio = 2  # render at 2x so the arc stays crisp on high-dpi screens
    pixmap = QPixmap(size * ratio, size * ratio)
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(color, 2.2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    margin = 2.0
    painter.drawArc(
        QRectF(margin, margin, size - 2 * margin, size - 2 * margin),
        -angle * 16,
        -_ARC_SPAN_DEGREES * 16,
    )
    painter.end()
    return QIcon(pixmap)


class ButtonSpinner(QObject):
    """Spins an arc in front of a button's text; restores the original icon when stopped."""

    def __init__(self, button: QAbstractButton, color: str = "#ffffff") -> None:
        super().__init__(button)
        self._button = button
        self._color = QColor(color)
        self._angle = 0
        self._saved_icon = QIcon()
        self._saved_icon_size = QSize()
        self._timer = QTimer(self)
        self._timer.setInterval(_FRAME_INTERVAL_MS)
        self._timer.timeout.connect(self._tick)

    def is_spinning(self) -> bool:
        return self._timer.isActive()

    def start(self) -> None:
        debug_print("ButtonSpinner.start called")
        if self._timer.isActive():
            return
        self._saved_icon = self._button.icon()
        self._saved_icon_size = self._button.iconSize()
        self._button.setIconSize(QSize(_ICON_SIZE, _ICON_SIZE))
        self._angle = 0
        self._apply_frame()
        self._timer.start()

    def stop(self) -> None:
        debug_print("ButtonSpinner.stop called")
        if not self._timer.isActive():
            return
        self._timer.stop()
        self._button.setIcon(self._saved_icon)
        self._button.setIconSize(self._saved_icon_size)

    def _tick(self) -> None:
        self._angle = (self._angle + _STEP_DEGREES) % 360
        self._apply_frame()

    def _apply_frame(self) -> None:
        self._button.setIcon(_arc_icon(self._angle, self._color))
