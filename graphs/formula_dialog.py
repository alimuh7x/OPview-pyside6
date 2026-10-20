"""Column formula editor (Custom Graph): write a conversion formula with a live preview."""

from __future__ import annotations

from typing import Mapping

import numpy as np
from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QCursor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCompleter,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.debug import debug_print
from config import formula as formula_engine
from graphs import formula_dialog_style as style
from graphs.formula_highlighter import FormulaHighlighter

_OPERATORS = (
    ("+", "Add"), ("-", "Subtract"), ("*", "Multiply"), ("/", "Divide"),
    ("^", "Power"), ("(", "Open bracket"), (")", "Close bracket"),
)
_FUNCTIONS = (
    ("sqrt", "Square root: sqrt(x)"), ("abs", "Absolute value: abs(x)"), ("log10", "Base-10 logarithm: log10(x)"),
    ("ln", "Natural logarithm: ln(x)"), ("exp", "Exponential: exp(x)"),
)
_UNIT_EXAMPLES = ("s", "ms", "µm", "mm", "MPa", "GPa", "mm/s", "K", "°C", "%")
_PREVIEW_ROWS = 3
_PREVIEW_DEBOUNCE_MS = 150
_MIN_WIDTH = 640
_DEFAULT_SIZE = (720, 620)
_MAX_BUTTON_NAME = 18  # longer column names are shortened on the button (the full name is inserted)
_TOKEN_CHAR_WIDTH = 10  # px per character of the 14 px monospace button text
_RESIZE_MARGIN = 7  # transparent border around the rounded window that grabs the resize drag


def _repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class _DragHeader(QFrame):
    """The navy header; dragging it moves the (frameless) dialog."""

    def mousePressEvent(self, event) -> None:
        handle = self.window().windowHandle()
        if event.button() == Qt.MouseButton.LeftButton and handle is not None:
            handle.startSystemMove()
            event.accept()
            return
        super().mousePressEvent(event)


_EDGE_CURSORS = {
    Qt.Edge.LeftEdge: Qt.CursorShape.SizeHorCursor,
    Qt.Edge.RightEdge: Qt.CursorShape.SizeHorCursor,
    Qt.Edge.TopEdge: Qt.CursorShape.SizeVerCursor,
    Qt.Edge.BottomEdge: Qt.CursorShape.SizeVerCursor,
}


class FormulaDialog(QDialog):
    """Build a formula with buttons for operators, functions and the other columns of the file.

    `x` is the value of the column being converted. Other columns are used by name (`Time`) or in brackets
    (`[Epsilon xx]`). The preview evaluates the formula on a copy of the first rows, so the data is never
    modified; Apply is enabled only for a formula that evaluates.
    """

    def __init__(
        self,
        parent: QWidget | None,
        *,
        current_column: str,
        column_data: Mapping[str, np.ndarray],
        formula: str = "",
        unit: str = "",
    ) -> None:
        super().__init__(parent)
        debug_print(f"FormulaDialog.__init__ column={current_column}")
        self.setObjectName("formulaDialog")
        # Frameless with a transparent surround: the rounded `fdWindow` frame is the visible window and the
        # transparent margin around it is the resize border.
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setWindowTitle("Formula Editor")
        self.setStyleSheet(style.build_dialog_stylesheet())
        self._current_column = current_column
        self._column_data = dict(column_data)
        self._column_names = tuple(self._column_data)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(_RESIZE_MARGIN, _RESIZE_MARGIN, _RESIZE_MARGIN, _RESIZE_MARGIN)
        window = QFrame()
        window.setObjectName("fdWindow")
        outer.addWidget(window)
        root = QVBoxLayout(window)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())
        root.addWidget(self._build_body(formula, unit), 1)
        root.addWidget(self._build_footer())
        # Never smaller than the layout needs, so nothing overlaps or is clipped.
        self.setMinimumSize(outer.minimumSize().expandedTo(QSize(_MIN_WIDTH, 0)))
        self.resize(QSize(*_DEFAULT_SIZE).expandedTo(self.minimumSize()))

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(_PREVIEW_DEBOUNCE_MS)
        self._timer.timeout.connect(self.refresh_preview)
        self.formula_edit.textChanged.connect(self._on_formula_changed)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._apply)
        QShortcut(QKeySequence("Ctrl+Enter"), self, activated=self._apply)
        self._setup_tab_order()
        self.refresh_preview()

    # ------------------------------------------------------------------ #
    # Public                                                              #
    # ------------------------------------------------------------------ #

    def formula(self) -> str:
        """The formula on one line; line breaks typed for readability count as spaces."""
        return " ".join(self.formula_edit.toPlainText().split())

    def unit(self) -> str:
        return self.unit_edit.text().strip()

    def insert_text(self, text: str) -> None:
        """Insert at the caret, replacing any selection, and leave a space after it.

        Focus and caret stay in the editor, so the next entry can follow at once.
        """
        self._insert(text, caret_back=0)

    def insert_function(self, name: str) -> None:
        """`name(selection)` around selected text, else `name()` with the caret between the brackets."""
        selected = self.formula_edit.textCursor().selectedText().replace("\u2029", " ")
        self._insert(f"{name}({selected})", caret_back=0 if selected else 1)

    def insert_column(self) -> None:
        """Insert the current column, by name."""
        self.insert_text(formula_engine.column_reference(self._current_column))

    def _insert(self, text: str, *, caret_back: int) -> None:
        """Insert `text` plus a trailing space (unless one follows already); caret goes back `caret_back`."""
        cursor = self.formula_edit.textCursor()
        cursor.insertText(text)
        # At the very end of the text Qt reports a paragraph separator, which is not a real character.
        following = "" if cursor.atEnd() else self.formula_edit.document().characterAt(cursor.position())
        space = "" if (following.isspace() or following == ")") else " "
        if space:
            cursor.insertText(space)
        # Land after the space for a plain entry, or just before the closing bracket of `name()`.
        back = caret_back + len(space) if caret_back else 0
        if back:
            cursor.movePosition(cursor.MoveOperation.Left, cursor.MoveMode.MoveAnchor, back)
        self.formula_edit.setTextCursor(cursor)
        self.formula_edit.setFocus()

    def refresh_preview(self) -> None:
        """Validate the formula and show example values; enables Apply only when it evaluates."""
        self._timer.stop()
        text = self.formula()
        if not text:
            self._show_state("idle", "Write a formula or use the buttons. Nothing changes until you apply it.")
            return
        try:
            run = formula_engine.compile_formula(text, self._column_names)
            current = np.array(self._column_data[self._current_column], dtype=float, copy=True)
            result = run(current, self._column_data)
            if result.shape != current.shape:
                raise ValueError("the formula must give one value per row")
        except (ValueError, KeyError) as exc:
            if self._looks_unfinished(text):
                # Still typing (`Sigma /`, `sqrt(`): not a mistake, so nothing turns red.
                self._show_state("idle", "Keep typing to finish the formula.")
            else:
                self._show_state("error", f"{exc}")
            return
        self._show_state("ok", self._preview_text(current, result))

    # ------------------------------------------------------------------ #
    # Building                                                            #
    # ------------------------------------------------------------------ #

    def _build_header(self) -> QWidget:
        header = _DragHeader()
        header.setObjectName("fdHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 14, 12, 14)
        titles = QVBoxLayout()
        titles.setSpacing(1)
        title = QLabel("Formula Editor")
        title.setObjectName("fdTitle")
        titles.addWidget(title)
        layout.addLayout(titles)
        layout.addStretch(1)
        close = QPushButton("\u2715")
        close.setObjectName("fdClose")
        close.setToolTip("Close without applying (Esc)")
        close.setAccessibleName("Close")
        close.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.clicked.connect(self.reject)
        layout.addWidget(close, 0, Qt.AlignmentFlag.AlignTop)
        return header

    @staticmethod
    def _section_title(text: str) -> QLabel:
        label = QLabel(text.upper())
        label.setObjectName("fdSectionTitle")
        return label

    def _build_body(self, formula: str, unit: str) -> QWidget:
        body = QWidget()
        body.setObjectName("fdBody")
        layout = QVBoxLayout(body)
        layout.setContentsMargins(20, 8, 20, 12)
        layout.setSpacing(12)
        layout.addLayout(self._build_formula_section(formula), 1)
        layout.addWidget(self._build_token_panel())
        layout.addWidget(self._build_unit_panel(unit))
        layout.addWidget(self._build_preview_box())
        return body

    def _build_formula_section(self, formula: str) -> QVBoxLayout:
        section = QVBoxLayout()
        section.setSpacing(6)
        head = QHBoxLayout()
        head.addWidget(self._section_title("Formula"))
        head.addStretch(1)
        section.addLayout(head)
        self.formula_edit = QPlainTextEdit()
        self.formula_edit.setObjectName("fdFormula")
        self.formula_edit.setPlaceholderText(f"{formula_engine.column_reference(self._current_column)} / 1000")
        self.formula_edit.setPlainText(formula)
        self.formula_edit.setMinimumHeight(120)
        self.formula_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.formula_edit.setTabChangesFocus(True)
        self.formula_edit.setCursorWidth(2)
        self.formula_edit.setAccessibleName("Formula")
        self.formula_edit.moveCursor(self.formula_edit.textCursor().MoveOperation.End)
        self._highlighter = FormulaHighlighter(
            self.formula_edit.document(), self._column_names, current_column=self._current_column
        )
        self._highlighter.rehighlight()
        section.addWidget(self.formula_edit, 1)
        return section

    def _token_button(self, text: str, tooltip: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("fdToken")
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        button.setAutoDefault(False)
        # Reachable with Tab, but a mouse click does not steal focus from the editor.
        button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        # Wide enough for its own text (log10), whatever the platform font.
        button.setMinimumWidth(max(30, len(text) * _TOKEN_CHAR_WIDTH + 30))
        return button

    @staticmethod
    def _panel() -> tuple[QFrame, QVBoxLayout]:
        panel = QFrame()
        panel.setObjectName("fdPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        return panel, layout

    def _token_row(self, caption: str, tokens, handler) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(6)
        label = QLabel(caption)
        label.setObjectName("fdHint")
        label.setMinimumWidth(66)
        row.addWidget(label)
        for text, tooltip in tokens:
            button = self._token_button(text, tooltip)
            button.clicked.connect(lambda _checked=False, t=text: handler(t))
            row.addWidget(button)
        return row

    def _build_token_panel(self) -> QFrame:
        panel, layout = self._panel()
        operators = self._token_row("Operators", _OPERATORS, self.insert_text)
        self.x_button = self._token_button(
            self._short_name(self._current_column), f"Insert the column {self._current_column}"
        )
        self.x_button.setProperty("kind", "variable")
        self.x_button.clicked.connect(lambda _checked=False: self.insert_column())
        operators.insertWidget(1, self.x_button)
        operators.insertWidget(2, self._divider())
        operators.addStretch(1)
        functions = self._token_row("Functions", _FUNCTIONS, self.insert_function)
        pi = self._token_button("pi", "The constant pi")
        pi.clicked.connect(lambda _checked=False: self.insert_text("pi"))
        functions.addWidget(pi)
        functions.addStretch(1)
        layout.addLayout(operators)
        layout.addLayout(functions)
        return panel

    def _build_unit_panel(self, unit: str) -> QFrame:
        panel, layout = self._panel()
        layout.addWidget(self._section_title("Unit Label"))
        self.unit_edit = QLineEdit(unit)
        self.unit_edit.setPlaceholderText("e.g. s, ms, MPa")
        self.unit_edit.setAccessibleName("Unit label")
        completer = QCompleter(list(_UNIT_EXAMPLES), self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.unit_edit.setCompleter(completer)
        layout.addWidget(self.unit_edit)
        return panel

    @staticmethod
    def _short_name(name: str) -> str:
        return name if len(name) <= _MAX_BUTTON_NAME else name[: _MAX_BUTTON_NAME - 1] + "\u2026"

    @staticmethod
    def _divider() -> QFrame:
        line = QFrame()
        line.setObjectName("fdDivider")
        line.setFixedHeight(20)
        return line

    def _build_preview_box(self) -> QFrame:
        box = QFrame()
        box.setObjectName("fdPreviewBox")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)
        layout.addWidget(self._section_title("Preview"))
        self.preview_label = QLabel()
        self.preview_label.setObjectName("fdPreview")
        self.preview_label.setWordWrap(True)
        self.preview_label.setMinimumHeight(58)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.preview_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.preview_label)
        return box

    def _build_footer(self) -> QWidget:
        footer = QFrame()
        footer.setObjectName("fdFooter")
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(20, 6, 20, 16)
        layout.setSpacing(10)
        layout.addStretch(1)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("fdSecondary")
        self.cancel_button.setAutoDefault(False)
        self.cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button)
        self.apply_button = QPushButton("Apply Formula")
        self.apply_button.setObjectName("fdPrimary")
        self.apply_button.setAutoDefault(False)
        self.apply_button.setToolTip("Apply the formula (Ctrl+Enter)")
        self.apply_button.clicked.connect(self._apply)
        layout.addWidget(self.apply_button)
        return footer

    @property
    def ok_button(self) -> QPushButton:
        return self.apply_button

    def _setup_tab_order(self) -> None:
        order = [self.formula_edit, self.x_button]
        order += [w for w in self.findChildren(QPushButton, "fdToken") if w is not self.x_button]
        order += [self.unit_edit, self.cancel_button, self.apply_button]
        for first, second in zip(order, order[1:]):
            self.setTabOrder(first, second)

    # ------------------------------------------------------------------ #
    # Behaviour                                                           #
    # ------------------------------------------------------------------ #

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.formula_edit.setFocus()  # typing can start at once

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.formula_edit.setFocus()  # typing can start at once

    # ------------------------------------------------------------------ #
    # Frameless window: resize from the transparent border                #
    # ------------------------------------------------------------------ #

    def _edges_at(self, pos) -> Qt.Edge:
        edges = Qt.Edge(0)
        if pos.x() <= _RESIZE_MARGIN:
            edges |= Qt.Edge.LeftEdge
        elif pos.x() >= self.width() - _RESIZE_MARGIN:
            edges |= Qt.Edge.RightEdge
        if pos.y() <= _RESIZE_MARGIN:
            edges |= Qt.Edge.TopEdge
        elif pos.y() >= self.height() - _RESIZE_MARGIN:
            edges |= Qt.Edge.BottomEdge
        return edges

    @staticmethod
    def _cursor_for(edges: Qt.Edge) -> Qt.CursorShape:
        horizontal = bool(edges & (Qt.Edge.LeftEdge | Qt.Edge.RightEdge))
        vertical = bool(edges & (Qt.Edge.TopEdge | Qt.Edge.BottomEdge))
        if horizontal and vertical:
            same = bool(edges & Qt.Edge.LeftEdge) == bool(edges & Qt.Edge.TopEdge)
            return Qt.CursorShape.SizeFDiagCursor if same else Qt.CursorShape.SizeBDiagCursor
        if horizontal:
            return Qt.CursorShape.SizeHorCursor
        return Qt.CursorShape.SizeVerCursor if vertical else Qt.CursorShape.ArrowCursor

    def mouseMoveEvent(self, event) -> None:
        edges = self._edges_at(event.position().toPoint())
        if edges:
            self.setCursor(QCursor(self._cursor_for(edges)))
        else:
            self.unsetCursor()  # the controls keep their own cursors
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event) -> None:
        edges = self._edges_at(event.position().toPoint())
        handle = self.windowHandle()
        if event.button() == Qt.MouseButton.LeftButton and edges and handle is not None:
            handle.startSystemResize(edges)
            event.accept()
            return
        super().mousePressEvent(event)

    def _on_formula_changed(self) -> None:
        self._set_apply_enabled(False)  # re-enabled once the new text has been checked
        self._timer.start()

    def _set_apply_enabled(self, enabled: bool) -> None:
        self.apply_button.setEnabled(enabled)
        self.apply_button.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)

    def _apply(self) -> None:
        self.refresh_preview()
        if self.apply_button.isEnabled():
            self.accept()

    def _show_state(self, state: str, message: str) -> None:
        self.preview_label.setProperty("state", state)
        self.preview_label.setText(message)
        _repolish(self.preview_label)
        self.formula_edit.setProperty("invalid", state == "error")
        _repolish(self.formula_edit)
        self._set_apply_enabled(state == "ok")

    @staticmethod
    def _looks_unfinished(text: str) -> bool:
        """True for a formula that stops mid-way: a trailing operator or an unclosed bracket."""
        return text.endswith(("+", "-", "*", "/", "^", "(", "%")) or text.count("(") > text.count(")")

    def _preview_text(self, current: np.ndarray, result: np.ndarray) -> str:
        rows = min(_PREVIEW_ROWS, len(current))
        label = self._short_name(self._current_column)
        lines = [f"{label} = {current[i]:<12g} \u2192   {result[i]:g}" for i in range(rows)]
        lines.append(f"First {rows} of {len(current)} rows. The data is not changed.")
        return "\n".join(lines)
