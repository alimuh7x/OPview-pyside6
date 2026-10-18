"""Colours and stylesheet of the column formula editor (scoped to `#formulaDialog`)."""

from __future__ import annotations

WINDOW = "#FFFFFF"
EDITOR = "#FFFFFF"
PANEL = "#F5F7FA"  # light-grey grouping behind related controls
SURFACE = "#FFFFFF"
SURFACE_HOVER = "#E8EEF6"
BORDER = "#DCE3ED"
TEXT = "#172B4D"
TEXT_MUTED = "#64748B"
HEADER = "#252526"  # same charcoal as the application's top bar and sidebar
HEADER_TEXT = "#F5F5F5"
HEADER_MUTED = "#B8B8B8"
HEADER_HOVER = "#3A3A3D"
ACCENT = "#0F2D61"
ACCENT_HOVER = "#17408A"
FOCUS_RING = ACCENT
OK = "#16803C"
ERROR = "#DC3545"

MONO_FAMILY = '"Cascadia Mono", "Consolas", "DejaVu Sans Mono", "Menlo", monospace'

WINDOW_RADIUS = 14
EDITOR_RADIUS = 11
CONTROL_RADIUS = 9

# Formula syntax colours (readable on white)
SYNTAX_FUNCTION = "#1E4A8A"
SYNTAX_COLUMN = "#7A3E9D"
SYNTAX_NUMBER = "#0F766E"  # teal: numbers must never look like an error (red or orange)
SYNTAX_OPERATOR = TEXT_MUTED
SYNTAX_VARIABLE = ACCENT


def build_dialog_stylesheet() -> str:
    return f"""
QDialog#formulaDialog {{
    background: transparent;
}}
#formulaDialog QFrame#fdWindow {{
    background: {WINDOW};
    border: 1px solid {BORDER};
    border-radius: {WINDOW_RADIUS}px;
}}
#formulaDialog QFrame#fdFooter, #formulaDialog QWidget#fdBody {{
    background: transparent;
    border: none;
}}
#formulaDialog QFrame#fdHeader {{
    background: {HEADER};
    border: none;
    border-top-left-radius: {WINDOW_RADIUS - 1}px;
    border-top-right-radius: {WINDOW_RADIUS - 1}px;
}}
#formulaDialog QFrame#fdHeader QLabel#fdTitle {{
    color: {HEADER_TEXT};
}}

#formulaDialog QLabel {{
    color: {TEXT};
    font-size: 13px;
    background: transparent;
    border: none;
}}
#formulaDialog QLabel#fdTitle {{
    font-size: 17px;
    font-weight: 600;
}}
#formulaDialog QLabel#fdHint {{
    color: {TEXT_MUTED};
    font-size: 12px;
}}
#formulaDialog QLabel#fdSectionTitle {{
    color: {TEXT_MUTED};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}}
#formulaDialog QLabel#fdContext {{
    color: {TEXT_MUTED};
    font-size: 12px;
}}
#formulaDialog QPushButton#fdClose {{
    background: transparent;
    color: {HEADER_MUTED};
    border: none;
    border-radius: {CONTROL_RADIUS}px;
    font-size: 15px;
    min-width: 30px;
    max-width: 30px;
    min-height: 30px;
    max-height: 30px;
}}
#formulaDialog QPushButton#fdClose:hover {{
    background: {HEADER_HOVER};
    color: #FFFFFF;
}}
#formulaDialog QPushButton#fdClose:focus {{
    border: 2px solid {HEADER_MUTED};
}}
#formulaDialog QPlainTextEdit#fdFormula {{
    background: {EDITOR};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: {EDITOR_RADIUS}px;
    padding: 10px 12px;
    font-family: {MONO_FAMILY};
    font-size: 15px;
    selection-background-color: {ACCENT};
    selection-color: #FFFFFF;
}}
#formulaDialog QPlainTextEdit#fdFormula:focus {{
    border: 2px solid {FOCUS_RING};
    padding: 9px 11px;
}}
#formulaDialog QPlainTextEdit#fdFormula[invalid="true"] {{
    border: 1px solid {ERROR};
}}
#formulaDialog QPlainTextEdit#fdFormula[invalid="true"]:focus {{
    border: 2px solid {ERROR};
}}
#formulaDialog QLineEdit, #formulaDialog QComboBox {{
    background: {SURFACE};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: {CONTROL_RADIUS}px;
    padding: 4px 10px;
    min-height: 26px;
    font-size: 13px;
    selection-background-color: {ACCENT};
    selection-color: #FFFFFF;
}}
#formulaDialog QLineEdit:focus, #formulaDialog QComboBox:focus {{
    border: 2px solid {FOCUS_RING};
    padding: 3px 9px;
}}
#formulaDialog QComboBox QLineEdit {{
    border: none;
    padding: 0;
    background: transparent;
    min-height: 0;
}}
#formulaDialog QComboBox::drop-down {{
    border: none;
    width: 26px;
}}
#formulaDialog QComboBox::down-arrow {{
    width: 10px;
    height: 10px;
}}
#formulaDialog QAbstractItemView {{
    background: {SURFACE};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: {CONTROL_RADIUS}px;
    outline: none;
    padding: 4px;
    selection-background-color: {SURFACE_HOVER};
    selection-color: {TEXT};
}}
#formulaDialog QAbstractItemView::item {{
    min-height: 24px;
    padding: 2px 8px;
    border-radius: 6px;
}}
#formulaDialog QPushButton#fdToken {{
    background: {SURFACE};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: {CONTROL_RADIUS}px;
    min-height: 28px;
    padding: 0 8px;
    font-family: {MONO_FAMILY};
    font-size: 14px;
}}
#formulaDialog QPushButton#fdToken:hover {{
    background: {SURFACE_HOVER};
    border-color: {FOCUS_RING};
}}
#formulaDialog QPushButton#fdToken:pressed {{
    background: {ACCENT};
    color: #FFFFFF;
}}
#formulaDialog QPushButton#fdToken:focus {{
    border: 2px solid {FOCUS_RING};
}}
#formulaDialog QPushButton#fdToken[kind="variable"] {{
    color: {ACCENT};
    font-weight: 700;
}}
#formulaDialog QFrame#fdDivider {{
    background: {BORDER};
    border: none;
    min-width: 1px;
    max-width: 1px;
}}
#formulaDialog QFrame#fdPanel, #formulaDialog QFrame#fdPreviewBox {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: {EDITOR_RADIUS}px;
}}
#formulaDialog QLabel#fdPreview {{
    font-size: 12px;
    color: {TEXT_MUTED};
}}
#formulaDialog QLabel#fdPreview[state="ok"] {{
    color: {OK};
    font-family: {MONO_FAMILY};
}}
#formulaDialog QLabel#fdPreview[state="error"] {{
    color: {ERROR};
}}
#formulaDialog QPushButton#fdSecondary {{
    background: {SURFACE};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: {CONTROL_RADIUS}px;
    min-height: 32px;
    min-width: 84px;
    padding: 0 16px;
    font-size: 13px;
}}
#formulaDialog QPushButton#fdSecondary:hover {{
    background: {SURFACE_HOVER};
}}
#formulaDialog QPushButton#fdSecondary:focus {{
    border: 2px solid {FOCUS_RING};
}}
#formulaDialog QPushButton#fdPrimary {{
    background: {ACCENT};
    color: #FFFFFF;
    border: 1px solid {ACCENT};
    border-radius: {CONTROL_RADIUS}px;
    min-height: 32px;
    min-width: 96px;
    padding: 0 18px;
    font-size: 13px;
    font-weight: 600;
}}
#formulaDialog QPushButton#fdPrimary:hover {{
    background: {ACCENT_HOVER};
}}
#formulaDialog QPushButton#fdPrimary:focus {{
    border: 2px solid {FOCUS_RING};
}}
#formulaDialog QPushButton#fdPrimary:disabled {{
    background: {SURFACE};
    color: {TEXT_MUTED};
    border-color: {BORDER};
}}
#formulaDialog QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 4px 2px;
}}
#formulaDialog QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 3px;
    min-height: 24px;
}}
#formulaDialog QScrollBar::add-line:vertical, #formulaDialog QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""
