"""Manual point entry dialog for Plot Over Time."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QDoubleSpinBox, QGridLayout, QLabel, QVBoxLayout

from app.debug import debug_print


class ManualPointDialog(QDialog):
    """Clear two-field dialog for entering Plot Over Time coordinates."""

    def __init__(self, *, x_value: float = 0.0, y_value: float = 0.0, parent=None) -> None:
        debug_print("ManualPointDialog.__init__ start")
        super().__init__(parent)
        self.setObjectName("manualPointDialog")
        debug_print("ManualPointDialog object name set")
        self.setWindowTitle("Manual Point")
        debug_print("ManualPointDialog title set")
        self.setMinimumWidth(360)
        debug_print("ManualPointDialog minimum width set")
        self.setModal(True)
        debug_print("ManualPointDialog modal enabled")
        self._apply_readable_styles()
        debug_print("ManualPointDialog readable styles applied")

        layout = QVBoxLayout(self)
        debug_print("ManualPointDialog root layout created")
        layout.setContentsMargins(18, 16, 18, 16)
        debug_print("ManualPointDialog layout margins set")
        layout.setSpacing(12)
        debug_print("ManualPointDialog layout spacing set")

        title = QLabel("Add point at coordinates")
        title.setObjectName("sectionTitle")
        debug_print("ManualPointDialog title label created")
        layout.addWidget(title)
        debug_print("ManualPointDialog title label added")

        form_layout = QGridLayout()
        debug_print("ManualPointDialog form layout created")
        form_layout.setContentsMargins(0, 0, 0, 0)
        debug_print("ManualPointDialog form margins set")
        form_layout.setHorizontalSpacing(12)
        debug_print("ManualPointDialog form horizontal spacing set")
        form_layout.setVerticalSpacing(10)
        debug_print("ManualPointDialog form vertical spacing set")

        self.x_input = self._make_coordinate_input(float(x_value), "manualPointXInput")
        self.y_input = self._make_coordinate_input(float(y_value), "manualPointYInput")

        x_label = QLabel("X coordinate")
        x_label.setObjectName("manualPointLabel")
        debug_print("ManualPointDialog X label created")
        y_label = QLabel("Y coordinate")
        y_label.setObjectName("manualPointLabel")
        debug_print("ManualPointDialog Y label created")

        form_layout.addWidget(x_label, 0, 0)
        debug_print("ManualPointDialog X label added")
        form_layout.addWidget(self.x_input, 0, 1)
        debug_print("ManualPointDialog X input added")
        form_layout.addWidget(y_label, 1, 0)
        debug_print("ManualPointDialog Y label added")
        form_layout.addWidget(self.y_input, 1, 1)
        debug_print("ManualPointDialog Y input added")
        layout.addLayout(form_layout)
        debug_print("ManualPointDialog form layout added")

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        debug_print("ManualPointDialog button box created")
        self.button_box.accepted.connect(self.accept)
        debug_print("ManualPointDialog accept connected")
        self.button_box.rejected.connect(self.reject)
        debug_print("ManualPointDialog reject connected")
        layout.addWidget(self.button_box, 0, Qt.AlignmentFlag.AlignRight)
        debug_print("ManualPointDialog button box added")
        debug_print("ManualPointDialog.__init__ complete")

    def point_values(self) -> tuple[float, float]:
        """Return the entered x/y coordinates."""
        debug_print("ManualPointDialog.point_values called")
        x_value = float(self.x_input.value())
        y_value = float(self.y_input.value())
        debug_print(f"ManualPointDialog x={x_value}")
        debug_print(f"ManualPointDialog y={y_value}")
        return x_value, y_value

    def _make_coordinate_input(self, value: float, object_name: str) -> QDoubleSpinBox:
        debug_print("ManualPointDialog._make_coordinate_input called")
        debug_print(f"ManualPointDialog input object_name={object_name}")
        input_widget = QDoubleSpinBox()
        input_widget.setObjectName(object_name)
        input_widget.setRange(-1.0e12, 1.0e12)
        input_widget.setDecimals(6)
        input_widget.setSingleStep(1.0)
        input_widget.setValue(value)
        input_widget.setMinimumHeight(34)
        input_widget.setMinimumWidth(180)
        input_widget.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        debug_print(f"ManualPointDialog input value={value}")
        return input_widget

    def _apply_readable_styles(self) -> None:
        """Use explicit dialog colors so native dark themes stay readable."""
        debug_print("ManualPointDialog._apply_readable_styles called")
        self.setStyleSheet(
            """
QDialog#manualPointDialog {
    background: #f7f9fc;
}
QDialog#manualPointDialog QLabel {
    color: #102a52;
    background: transparent;
}
QDialog#manualPointDialog QLabel#sectionTitle {
    color: #102a52;
    font-size: 15px;
    font-weight: 700;
}
QDialog#manualPointDialog QLabel#manualPointLabel {
    color: #102a52;
    font-size: 14px;
}
QDialog#manualPointDialog QDoubleSpinBox#manualPointXInput,
QDialog#manualPointDialog QDoubleSpinBox#manualPointYInput {
    background: #ffffff;
    color: #102a52;
    border: 1px solid #ccd7e8;
    border-radius: 8px;
    padding: 4px 8px;
    selection-background-color: #d9e7ff;
    selection-color: #102a52;
}
QDialog#manualPointDialog QDoubleSpinBox#manualPointXInput:focus,
QDialog#manualPointDialog QDoubleSpinBox#manualPointYInput:focus {
    border-color: #a652b8;
}
QDialog#manualPointDialog QPushButton {
    background: #ffffff;
    color: #102a52;
    border: 1px solid #ccd7e8;
    border-radius: 8px;
    min-width: 82px;
    min-height: 28px;
    padding: 2px 12px;
}
QDialog#manualPointDialog QPushButton:hover {
    background: #eef4ff;
    border-color: #9fb5d6;
}
QDialog#manualPointDialog QPushButton:pressed {
    background: #dbe8fb;
}
"""
        )
        debug_print("ManualPointDialog stylesheet set")
