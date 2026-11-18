"""Animated toggle switch — drop-in replacement for QCheckBox."""

from PySide6.QtCore import QEasingCurve, QRect, QVariantAnimation, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QMouseEvent, QPaintEvent, QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.theme import FONT_FAMILY, color


class ToggleSwitchWidget(QWidget):
    """Pill-shaped animated toggle switch with ON/OFF labels."""

    toggled = Signal(bool)

    _TRACK_W  = 36
    _TRACK_H  = 18
    _THUMB_SZ = 12
    _OFFSET   = 3
    _GAP      = 6       # gap between track and label text
    _COLOR_THUMB = QColor("#ffffff")

    def __init__(self, text: str = "", checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._checked = checked
        self._pos = 1.0 if checked else 0.0
        self._text = text

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(350)
        self._anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self._anim.valueChanged.connect(self._on_anim)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._update_size()

    def _update_size(self) -> None:
        fm = QFontMetrics(QFont(FONT_FAMILY, 10))
        text_w = (fm.horizontalAdvance(self._text) + self._GAP) if self._text else 0
        self.setFixedSize(self._TRACK_W + text_w, max(self._TRACK_H, 24))

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool) -> None:
        if checked == self._checked:
            return
        self._checked = checked
        self._anim.stop()
        self._anim.setStartValue(float(self._pos))
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()
        self.toggled.emit(checked)

    def setText(self, text: str) -> None:
        self._text = text
        self._update_size()
        self.update()

    def text(self) -> str:
        return self._text

    def _on_anim(self, value: float) -> None:
        self._pos = value
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            new_state = not self._checked
            self.setChecked(new_state)
        event.accept()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        p = QPainter(self)
        if not self.isEnabled():
            p.setOpacity(0.45)  # a disabled toggle (e.g. Auto Scale in an unsupported mode) looks dimmed
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self._pos

        # Interpolate track color OFF → ON (OPStudio colours of the current mode)
        color_off, color_on = QColor(color("element_dark")), QColor(color("accent"))
        r = int(color_off.red()   + t * (color_on.red()   - color_off.red()))
        g = int(color_off.green() + t * (color_on.green() - color_off.green()))
        b = int(color_off.blue()  + t * (color_on.blue()  - color_off.blue()))

        track_y = (self.height() - self._TRACK_H) // 2
        radius  = self._TRACK_H // 2

        # Track
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(r, g, b))
        p.drawRoundedRect(0, track_y, self._TRACK_W, self._TRACK_H, radius, radius)

        # Thumb
        thumb_x_min = float(self._OFFSET)
        thumb_x_max = float(self._TRACK_W - self._THUMB_SZ - self._OFFSET)
        thumb_x = thumb_x_min + t * (thumb_x_max - thumb_x_min)
        thumb_y = track_y + (self._TRACK_H - self._THUMB_SZ) // 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._COLOR_THUMB)
        p.drawEllipse(int(thumb_x), int(thumb_y), self._THUMB_SZ, self._THUMB_SZ)

        # Label text to the right of the track
        if self._text:
            txt_font = QFont(FONT_FAMILY, 10)
            p.setFont(txt_font)
            p.setPen(QColor(color("primary_text")))
            p.drawText(
                QRect(self._TRACK_W + self._GAP, 0, self.width() - self._TRACK_W - self._GAP, self.height()),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                self._text,
            )

        p.end()
