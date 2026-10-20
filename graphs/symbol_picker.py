"""Shared symbol picker: insert Greek letters, math signs or SI units into label fields."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QColor, QFont, QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from app.debug import debug_print

SYMBOL_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Greek", tuple("αβγδεζηθικλμνξοπρστυφχψω")),
    ("Greek variants", ("ϕ", "ϑ", "ϵ", "ϰ", "ϖ", "ϱ", "ς")),
    ("Greek capitals", tuple("ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ")),
    ("Math", ("±", "·", "°", "∂", "∇", "∞", "∫", "∑", "→")),
    ("Powers", ("⁻⁴", "⁻³", "⁻²", "⁻¹", "¹", "²", "³", "⁴", "¹⁺", "²⁺", "³⁺", "⁴⁺")),
    ("SI units", ("N/m²", "N/m", "N", "Pa", "kPa", "MPa", "GPa", "J/m³", "J/m²", "J/mol", "m²/s", "m/s",
                  "s⁻¹", "µm", "mm", "µs", "K", "°C", "W/m²", "kg/m³")),
)
_COLUMNS = 8
_ITALIC_GROUPS = {"Greek", "Greek variants", "Greek capitals"}
_SERIF_ITALIC_FAMILY = "STIX Two Text"
_ICON_SIZE = 18


def _icon(glyph: str) -> QIcon:
    pixmap = QPixmap(_ICON_SIZE, _ICON_SIZE)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setPen(QColor("#475569"))
    font = QFont()
    font.setPixelSize(15)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, glyph)
    painter.end()
    return QIcon(pixmap)


def _greek_font() -> QFont:
    font = QFont(_SERIF_ITALIC_FAMILY)
    font.setItalic(True)
    font.setPixelSize(19)
    return font


class SymbolPicker(QFrame):
    """Popup grid of symbol buttons; stays open while you click, closes on an outside click or Esc."""

    symbol_chosen = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent, Qt.WindowType.Popup)
        self.setObjectName("symbolPicker")
        self.setStyleSheet(
            "#symbolPicker{background:white;border:1px solid #94a3b8;border-radius:6px;}"
            "#symbolPicker QLabel{color:#475569;font-weight:600;padding-top:4px;}"
            "#symbolPicker QPushButton{min-width:34px;min-height:28px;padding:0 6px;border:1px solid #cbd5e1;"
            "border-radius:4px;background:#f8fafc;font-size:15px;}"
            "#symbolPicker QPushButton:hover{background:#e0e7ff;border-color:#6366f1;}"
        )
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 4, 8, 8)
        outer.setSpacing(2)
        for title, symbols in SYMBOL_GROUPS:
            outer.addWidget(QLabel(title))
            grid = QGridLayout()
            grid.setSpacing(3)
            for index, symbol in enumerate(symbols):
                button = QPushButton(symbol)
                button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                if title in _ITALIC_GROUPS:
                    button.setFont(_greek_font())
                    button.setStyleSheet("font-size:19px;")
                button.setToolTip(f"Insert {symbol}")
                button.clicked.connect(lambda _=False, s=symbol: self._choose(s))
                grid.addWidget(button, index // _COLUMNS, index % _COLUMNS)
            outer.addLayout(grid)

    def _choose(self, symbol: str) -> None:
        debug_print(f"SymbolPicker._choose symbol={symbol}")
        self.symbol_chosen.emit(symbol)

    def show_centered(self, widget) -> None:
        """Open in the middle of the screen the field is on."""
        debug_print(f"SymbolPicker.show_centered field={widget.objectName()}")
        self.show()  # size settles after the stylesheet is applied, so centre only afterwards
        self.adjustSize()
        debug_print(f"SymbolPicker popup size={self.size()}")
        screen = widget.screen() or QGuiApplication.primaryScreen()
        area = screen.availableGeometry()
        self.move(area.x() + (area.width() - self.width()) // 2, area.y() + (area.height() - self.height()) // 2)
        debug_print(f"SymbolPicker popup position={self.pos()}")


def attach_symbol_picker(edit: QLineEdit) -> SymbolPicker:
    """Add a small σ button inside `edit`; symbols are inserted at the cursor and the edit is committed."""
    debug_print(f"attach_symbol_picker field={edit.objectName()}")
    picker = SymbolPicker(edit)
    debug_print("attach_symbol_picker popup created")

    def insert(symbol: str) -> None:
        debug_print(f"SymbolPicker insert symbol={symbol} cursor={edit.cursorPosition()}")
        edit.insert(symbol)
        debug_print(f"SymbolPicker updated label={edit.text()}")
        edit.editingFinished.emit()
        debug_print("SymbolPicker label editingFinished emitted")

    picker.symbol_chosen.connect(insert)
    action = QAction(_icon("σ"), "Insert symbol", edit)
    action.setToolTip("Insert Greek letter, math sign or unit")
    action.triggered.connect(lambda: picker.show_centered(edit))
    edit.addAction(action, QLineEdit.ActionPosition.TrailingPosition)
    debug_print("attach_symbol_picker trailing action attached")
    return picker
