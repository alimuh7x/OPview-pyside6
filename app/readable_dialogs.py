"""Readable app dialogs with explicit light styling."""

from PySide6.QtWidgets import QMessageBox, QWidget

from app.debug import debug_print


READABLE_MESSAGE_BOX_STYLESHEET = """
QMessageBox#readableMessageBox {
    background: #f7f9fc;
    color: #102a52;
}
QMessageBox#readableMessageBox QLabel {
    background: transparent;
    color: #102a52;
    font-size: 13px;
}
QMessageBox#readableMessageBox QPushButton {
    background: #ffffff;
    color: #102a52;
    border: 1px solid #d2dbea;
    border-radius: 6px;
    padding: 6px 14px;
    min-width: 72px;
    font-weight: 700;
}
QMessageBox#readableMessageBox QPushButton:hover {
    background: #eef4ff;
    border-color: #9fb5d6;
}
"""


def build_readable_message_box(
    parent: QWidget | None,
    icon: QMessageBox.Icon,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton,
    default_button: QMessageBox.StandardButton | None = None,
) -> QMessageBox:
    debug_print("build_readable_message_box called")
    debug_print(f"readable message title={title}")
    debug_print(f"readable message text={text}")
    debug_print(f"readable message buttons={buttons}")
    box = QMessageBox(parent)
    box.setObjectName("readableMessageBox")
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(buttons)
    if default_button is not None:
        box.setDefaultButton(default_button)
    box.setStyleSheet(READABLE_MESSAGE_BOX_STYLESHEET)
    debug_print("readable message stylesheet applied")
    return box


def readable_warning(parent: QWidget | None, title: str, text: str) -> QMessageBox.StandardButton:
    debug_print("readable_warning called")
    return build_readable_message_box(
        parent,
        QMessageBox.Icon.Warning,
        title,
        text,
        QMessageBox.StandardButton.Ok,
        QMessageBox.StandardButton.Ok,
    ).exec()


def readable_information(parent: QWidget | None, title: str, text: str) -> QMessageBox.StandardButton:
    debug_print("readable_information called")
    return build_readable_message_box(
        parent,
        QMessageBox.Icon.Information,
        title,
        text,
        QMessageBox.StandardButton.Ok,
        QMessageBox.StandardButton.Ok,
    ).exec()


def readable_question(
    parent: QWidget | None,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton,
    default_button: QMessageBox.StandardButton,
) -> QMessageBox.StandardButton:
    debug_print("readable_question called")
    return build_readable_message_box(
        parent,
        QMessageBox.Icon.Question,
        title,
        text,
        buttons,
        default_button,
    ).exec()
