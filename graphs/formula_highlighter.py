"""Syntax colouring for the column formula editor."""

from __future__ import annotations

import re
from typing import Iterable

from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat, QTextDocument

from config import formula as formula_engine
from graphs import formula_dialog_style as style


def _format(color: str, *, bold: bool = False) -> QTextCharFormat:
    text_format = QTextCharFormat()
    text_format.setForeground(QColor(color))
    if bold:
        text_format.setFontWeight(QFont.Weight.Bold)
    return text_format


class FormulaHighlighter(QSyntaxHighlighter):
    """Colours numbers, operators, `x`, functions and column references (`Time`, `[Epsilon xx]`)."""

    def __init__(self, document: QTextDocument, column_names: Iterable[str] = (), current_column: str = "") -> None:
        super().__init__(document)
        names = sorted({name for name in column_names if name and name.isidentifier()}, key=len, reverse=True)
        functions = "|".join(formula_engine.FUNCTION_NAMES)
        rules: list[tuple[re.Pattern, QTextCharFormat]] = [
            (re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"), _format(style.SYNTAX_NUMBER)),
            (re.compile(r"[-+*/^%]"), _format(style.SYNTAX_OPERATOR, bold=True)),
            (re.compile(rf"\b(?:{functions})(?=\s*\()"), _format(style.SYNTAX_FUNCTION, bold=True)),
            (re.compile(r"\b(?:pi|e)\b"), _format(style.SYNTAX_NUMBER)),
            (re.compile(r"\bx\b"), _format(style.SYNTAX_VARIABLE, bold=True)),
            (re.compile(r"\[[^\]\n]*\]"), _format(style.SYNTAX_COLUMN)),
        ]
        if names:
            pattern = r"\b(?:" + "|".join(re.escape(name) for name in names) + r")\b"
            rules.append((re.compile(pattern), _format(style.SYNTAX_COLUMN)))
        if current_column:
            # The column being converted stands out from the other columns.
            own = re.escape(current_column)
            pattern = rf"\[{own}\]" if not current_column.isidentifier() else rf"\b{own}\b|\[{own}\]"
            rules.append((re.compile(pattern), _format(style.SYNTAX_VARIABLE, bold=True)))
        self._rules = rules

    def highlightBlock(self, text: str) -> None:
        for pattern, text_format in self._rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), text_format)
