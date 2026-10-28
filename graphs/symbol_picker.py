"""Shared symbol picker: insert Greek letters, math signs or SI units into label fields."""

from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QFont, QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QButtonGroup, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from app.debug import debug_print
from utils.label_editing import edit_label_text
from utils.label_formatting import label_to_html
from utils.label_notation import label_to_notation

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
            "#symbolPicker{background:white;color:#0f172a;border:1px solid #94a3b8;border-radius:6px;}"
            "#symbolPicker QLabel{color:#475569;font-weight:600;padding-top:4px;}"
            "#symbolPicker QPushButton{min-width:34px;min-height:28px;padding:0 6px;border:1px solid #cbd5e1;"
            "border-radius:4px;background:#f8fafc;color:#0f172a;font-size:15px;}"
            "#symbolPicker QPushButton:hover{background:#e0e7ff;color:#0f172a;border-color:#6366f1;}"
            "#symbolPicker QPushButton:checked{background:#dbeafe;color:#0f172a;border-color:#6366f1;}"
            "#symbolPicker QPushButton:pressed{background:#c7d2fe;color:#0f172a;}"
            "#symbolPicker QPushButton:disabled{background:#e2e8f0;color:#64748b;}"
            "#symbolPicker QLineEdit{background:#fff;color:#0f172a;border:1px solid #94a3b8;"
            "border-radius:4px;padding:4px;selection-background-color:#bfdbfe;selection-color:#0f172a;}"
        )
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 4, 8, 8)
        outer.setSpacing(2)
        self._edit = parent if isinstance(parent, QLineEdit) else None
        self._script_kind = "normal"
        self._syncing = False
        self._commit_pending = False
        self._commit_timer = QTimer(self)
        self._commit_timer.setSingleShot(True)
        self._commit_timer.setInterval(120)
        self._commit_timer.timeout.connect(self._flush_commit)
        debug_print("SymbolPicker initialized live label synchronization")
        self.preview_label = QLabel()
        self.preview_label.setObjectName("symbolFormattingPreview")
        self.preview_label.setTextFormat(Qt.TextFormat.RichText)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(52)
        self.preview_label.setWordWrap(True)
        self.preview_label.setFixedWidth(410)
        self.preview_label.setStyleSheet("font-size:22px;font-weight:400;background:#f1f5f9;border-radius:4px;padding:8px;")
        self.preview_label.setToolTip("Live preview; edit the complete label in the text field below")
        outer.addWidget(self.preview_label)
        debug_print("SymbolPicker preview placed at top")
        self.script_input = QLineEdit()
        self.script_input.setPlaceholderText("Edit the complete label here; use _xx or ^yy for formatting")
        self.script_input.setAccessibleName("Complete label text")
        self.script_input.setToolTip("Edit, select or remove any part of the label. Both label fields update together.")
        if self._edit is not None:
            self.script_input.setMaxLength(self._edit.maxLength())
        outer.addWidget(self.script_input)
        debug_print("SymbolPicker script text entry added below preview")
        formatting_row = QHBoxLayout()
        self.sub_button = QPushButton("x₂ Subscript")
        self.sup_button = QPushButton("x² Superscript")
        self.normal_button = QPushButton("Normal")
        self._script_buttons = QButtonGroup(self)
        for kind, button in (("normal", self.normal_button), ("sub", self.sub_button), ("sup", self.sup_button)):
            button.setCheckable(True)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setToolTip("Format selected label text; Subscript or Superscript inserts a template when nothing is selected")
            self._script_buttons.addButton(button)
            button.clicked.connect(lambda _=False, k=kind: self._choose_format(k))
            formatting_row.addWidget(button)
        self.normal_button.setChecked(True)
        debug_print("SymbolPicker subscript and superscript buttons added")
        outer.addLayout(formatting_row)
        debug_print("SymbolPicker Normal, Subscript and Superscript modes added")
        editing_row = QHBoxLayout()
        self.backspace_button = QPushButton("⌫ Backspace")
        self.backspace_button.setToolTip("Delete the selected label text or the character before the dialog cursor")
        self.clear_button = QPushButton("Clear")
        self.clear_button.setToolTip("Clear the label in both fields; undo is available")
        for button, handler in ((self.backspace_button, self._backspace), (self.clear_button, self._clear)):
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.clicked.connect(handler)
            editing_row.addWidget(button)
        debug_print("SymbolPicker Backspace and Clear actions connected")
        self.done_button = QPushButton("Done")
        self.done_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.done_button.clicked.connect(self._done)
        editing_row.addWidget(self.done_button)
        outer.addLayout(editing_row)
        debug_print("SymbolPicker Done button closes the live editor")
        self.script_input.textChanged.connect(self._editor_changed)
        self.script_input.cursorPositionChanged.connect(self._editor_cursor_changed)
        self.script_input.selectionChanged.connect(self._editor_cursor_changed)
        self.script_input.returnPressed.connect(self._done)
        self.symbol_chosen.connect(self._insert_symbol)
        if self._edit is not None:
            self._edit.textChanged.connect(self._target_changed)
            self._edit.cursorPositionChanged.connect(self._target_cursor_changed)
            self._edit.selectionChanged.connect(self._target_cursor_changed)
        self._sync_from_target()
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

    @staticmethod
    def _copy_cursor(source: QLineEdit, destination: QLineEdit) -> None:
        cursor = source.cursorPosition()
        if source.hasSelectedText():
            start = source.selectionStart()
            length = len(source.selectedText().encode("utf-16-le")) // 2
            anchor = start + length if cursor == start else start
            destination.setSelection(anchor, cursor - anchor)
        else:
            destination.setCursorPosition(cursor)

    def _sync_from_target(self) -> None:
        if self._syncing:
            return
        self._syncing = True
        try:
            if self._edit is not None:
                with QSignalBlocker(self.script_input):
                    if self.script_input.text() != self._edit.text():
                        self.script_input.setText(self._edit.text())
                    self._copy_cursor(self._edit, self.script_input)
                debug_print(f"SymbolPicker source -> full editor text={self._edit.text()}")
        finally:
            self._syncing = False
        self._update_preview()

    def _target_changed(self, *_args) -> None:
        if self._syncing:
            return
        self._commit_timer.stop()
        self._commit_pending = False
        debug_print("SymbolPicker original label changed; mirroring complete text")
        self._sync_from_target()

    def _target_cursor_changed(self, *_args) -> None:
        if self._syncing or self._edit is None:
            return
        self._syncing = True
        try:
            with QSignalBlocker(self.script_input):
                self._copy_cursor(self._edit, self.script_input)
        finally:
            self._syncing = False
        debug_print(f"SymbolPicker mirrored source cursor={self.script_input.cursorPosition()}")

    def _editor_cursor_changed(self, *_args) -> None:
        if self._syncing or self._edit is None:
            return
        self._syncing = True
        try:
            self._copy_cursor(self.script_input, self._edit)
        finally:
            self._syncing = False
        debug_print(f"SymbolPicker mirrored dialog cursor={self.script_input.cursorPosition()}")

    def _editor_changed(self, *_args) -> None:
        if self._syncing:
            return
        text = self.script_input.text()
        debug_print(f"SymbolPicker full editor -> source text={text}")
        self._syncing = True
        changed = False
        try:
            if self._edit is not None:
                changed = text != self._edit.text()
                if changed:
                    self._edit.selectAll()
                    self._edit.insert(text)
                    debug_print("SymbolPicker source replaced in an undoable edit")
                self._copy_cursor(self.script_input, self._edit)
        finally:
            self._syncing = False
        self._update_preview()
        if changed:
            self._commit_pending = True
            self._commit_timer.start()
            debug_print("SymbolPicker scheduled graph label notification after typing")

    def _update_preview(self) -> None:
        self.preview_label.setText(label_to_html(self.script_input.text()))
        debug_print(f"SymbolPicker full-label preview={self.script_input.text()}")

    def _flush_commit(self, *, closing: bool = False) -> None:
        self._commit_timer.stop()
        if not self._commit_pending:
            return
        if not closing and self.isVisible() and not self.script_input.text():
            debug_print("SymbolPicker keeping empty live editor while user replaces an automatic title")
            return
        self._commit_pending = False
        if self._edit is not None:
            debug_print(f"SymbolPicker notifying label change={self._edit.text()}")
            self._edit.editingFinished.emit()

    def _replace_editor(self, text: str, cursor: int) -> None:
        debug_print(f"SymbolPicker replacing full editor text={text} cursor={cursor}")
        if self.script_input.text() != text:
            self.script_input.selectAll()
            self.script_input.insert(text)
        self.script_input.setCursorPosition(cursor)
        self._update_preview()
        self._flush_commit()

    def _choose_format(self, kind: str) -> None:
        if not self.isVisible():
            self._sync_from_target()
        self._script_kind = kind
        debug_print(f"SymbolPicker dialog selection format={kind}")
        if self.script_input.hasSelectedText():
            start = self.script_input.selectionStart()
            length = len(self.script_input.selectedText().encode("utf-16-le")) // 2
            action = "normal" if kind == "normal" else "format-selected"
            updated, cursor = edit_label_text(self.script_input.text(), start, length, action=action, kind=kind)
            self._replace_editor(updated, cursor)
        elif kind != "normal":
            cursor = self.script_input.cursorPosition()
            template = "_{}" if kind == "sub" else "^{}"
            self.script_input.insert(template)
            self.script_input.setCursorPosition(cursor + 2)
            debug_print("SymbolPicker inserted formatting template at dialog cursor")
            self._flush_commit()
        self.script_input.setFocus()

    def _insert_symbol(self, symbol: str) -> None:
        if not self.isVisible():
            self._sync_from_target()
        start = self.script_input.selectionStart() if self.script_input.hasSelectedText() else self.script_input.cursorPosition()
        length = len(self.script_input.selectedText().encode("utf-16-le")) // 2
        action = "insert-normal" if self._script_kind == "normal" else "insert-script"
        debug_print(f"SymbolPicker inserting symbol at dialog cursor={start} selection={length}")
        updated, cursor = edit_label_text(self.script_input.text(), start, length, action=action, text=symbol, kind=self._script_kind)
        self._replace_editor(updated, cursor)
        self.script_input.setFocus()

    def _backspace(self) -> None:
        if not self.isVisible():
            self._sync_from_target()
        start = self.script_input.selectionStart() if self.script_input.hasSelectedText() else self.script_input.cursorPosition()
        length = len(self.script_input.selectedText().encode("utf-16-le")) // 2
        encoded = self.script_input.text().encode("utf-16-le")
        prefixes = tuple(value.encode("utf-16-le") for value in ("_{", "^{"))
        if not length and encoded[:start * 2].endswith(prefixes) and encoded[start * 2:].startswith("}".encode("utf-16-le")):
            start -= 2
            length = 3
            debug_print("SymbolPicker Backspace removing empty template without deleting label text")
        debug_print(f"SymbolPicker deleting at dialog cursor={start} selection={length}")
        updated, cursor = edit_label_text(self.script_input.text(), start, length, action="backspace")
        self._replace_editor(updated, cursor)
        self.script_input.setFocus()

    def _clear(self) -> None:
        debug_print("SymbolPicker clearing synchronized full label")
        self._replace_editor("", 0)
        self.script_input.setFocus()

    def _choose(self, symbol: str) -> None:
        debug_print(f"SymbolPicker._choose symbol={symbol}")
        self.symbol_chosen.emit(symbol)

    def _done(self) -> None:
        self._flush_commit(closing=True)
        self.hide()

    def hideEvent(self, event) -> None:
        self._flush_commit(closing=True)
        super().hideEvent(event)

    def show_centered(self, widget) -> None:
        """Open the full synchronized label editor in the middle of its screen."""
        debug_print(f"SymbolPicker.show_centered field={widget.objectName()}")
        self._sync_from_target()
        self._script_kind = "normal"
        self.normal_button.setChecked(True)
        cursor = self.script_input.cursorPosition()
        start = self.script_input.selectionStart()
        length = len(self.script_input.selectedText().encode("utf-16-le")) // 2
        self.show()
        self.script_input.setFocus(Qt.FocusReason.PopupFocusReason)
        if length:
            anchor = start + length if cursor == start else start
            self.script_input.setSelection(anchor, cursor - anchor)
        else:
            self.script_input.setCursorPosition(cursor)
        self.adjustSize()
        screen = widget.screen() or QGuiApplication.primaryScreen()
        area = screen.availableGeometry()
        self.move(area.x() + (area.width() - self.width()) // 2, area.y() + (area.height() - self.height()) // 2)
        debug_print(f"SymbolPicker opened full label={self.script_input.text()}")


def attach_symbol_picker(edit: QLineEdit) -> SymbolPicker:
    """Add a σ button opening a full-label editor synchronized live with `edit`."""
    debug_print(f"attach_symbol_picker field={edit.objectName()}")
    readable = label_to_notation(edit.text())
    if readable != edit.text():
        edit.setText(readable)
        debug_print("SymbolPicker converted legacy label to _/^ notation")
    picker = SymbolPicker(edit)
    debug_print("attach_symbol_picker popup created")

    action = QAction(_icon("σ"), "Insert symbol", edit)
    action.setToolTip("Insert a symbol, subscript or superscript")
    action.triggered.connect(lambda: picker.show_centered(edit))
    edit.addAction(action, QLineEdit.ActionPosition.TrailingPosition)
    debug_print("attach_symbol_picker trailing action attached")
    return picker
