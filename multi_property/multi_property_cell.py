"""One property heatmap cell in Multi Property View."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.debug import debug_print
from multi_property.colorbar_canvas import MultiPropertyColorbarCanvas
from multi_view.multi_view_cell import MultiViewCell, _CELL_W

_ASSETS = Path(__file__).resolve().parent.parent / "assets"
_RANGE_SPIN_W = 112
_CONTROL_BUTTON_W = 16
_MIN_CELL_W = 330
_TITLE_TOP_GAP = 12
_TITLE_BOTTOM_GAP = 8
_TITLE_ROW_GAP = 6


def _format_range_value(value: float) -> str:
    debug_print("MultiPropertyCell._format_range_value called")
    debug_print(f"MultiPropertyCell format range value={value}")
    value = float(value)
    abs_value = abs(value)
    if value == 0.0:
        debug_print("MultiPropertyCell formatted range value=0")
        return "0"
    if abs_value < 0.001 or abs_value >= 1000.0:
        formatted = f"{value:.2e}"
        debug_print(f"MultiPropertyCell formatted scientific={formatted}")
        return formatted
    formatted = f"{value:.12f}".rstrip("0").rstrip(".")
    debug_print(f"MultiPropertyCell formatted decimal={formatted}")
    return formatted


class ScientificRangeSpinBox(QDoubleSpinBox):
    """Range spin box that displays large/small values in scientific notation."""

    def textFromValue(self, value: float) -> str:  # noqa: N802
        debug_print("ScientificRangeSpinBox.textFromValue called")
        return _format_range_value(value)

    def valueFromText(self, text: str) -> float:  # noqa: N802
        debug_print("ScientificRangeSpinBox.valueFromText called")
        debug_print(f"ScientificRangeSpinBox input text={text}")
        try:
            value = float(text.strip())
        except ValueError:
            debug_print("ScientificRangeSpinBox parse failed")
            return self.value()
        debug_print(f"ScientificRangeSpinBox parsed value={value}")
        return value


class MultiPropertyCell(QWidget):
    """Selector title, colorbar, and heatmap for one property."""

    select_requested = Signal(str)
    remove_requested = Signal(str)
    renamed = Signal(str, str)

    def __init__(self, property_key: str, label: str, *, bottom_row: bool = False, parent=None) -> None:
        super().__init__(parent)
        debug_print("MultiPropertyCell.__init__ start")
        self.property_key = property_key
        self.label = label
        self._bottom_row = bottom_row
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            "MultiPropertyCell { background: #ffffff; } "
            "QWidget#multiPropertyControls { background: #ffffff; } "
            "QWidget#multiPropertyTitleRow {"
            "  background: #ffffff;"
            "  border: 1px solid #d6dee9;"
            "  border-radius: 4px;"
            "}"
            "QPushButton#multiPropertySelectBullet {"
            "  background: #ffffff;"
            "  border: 2px solid #b8c3d2;"
            "  border-radius: 9px;"
            "  padding: 0px;"
            "  margin: 0px;"
            "}"
            "QPushButton#multiPropertySelectBullet:checked {"
            "  background: #8FAE00;"
            "  border-color: #8FAE00;"
            "}"
            "QPushButton#multiPropertySelectBullet:hover {"
            "  border-color: #8FAE00;"
            "}"
            "QLabel#multiPropertyTitleLabel {"
            "  background: transparent;"
            "  color: #102a52;"
            "  font-size: 18px;"
            "  font-weight: 700;"
            "}"
            "QPushButton#multiPropertyTitleEditButton {"
            "  background: #ffffff;"
            "  border: 1px solid #c7d2e2;"
            "  border-radius: 4px;"
            "  padding: 0px;"
            "  margin: 0px;"
            "  color: #536579;"
            "  font-size: 14px;"
            "}"
            "QPushButton#multiPropertyTitleEditButton:hover {"
            "  background: #eef4ff;"
            "  border-color: #9fb5d6;"
            "  color: #c50623;"
            "}"
            "QPushButton#multiPropertyIconButton {"
            "  background: transparent;"
            "  border: 0px;"
            "  border-radius: 0px;"
            "  padding: 0px;"
            "  margin: 0px;"
            "}"
            "QPushButton#multiPropertyIconButton:hover {"
            "  background: #edf2f8;"
            "}"
        )
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        debug_print("MultiPropertyCell size policy fixed")
        self.heatmap = MultiViewCell(property_key)
        self.colorbar = MultiPropertyColorbarCanvas()
        self.select_button = QPushButton("")
        self.select_button.setObjectName("multiPropertySelectBullet")
        self.select_button.setCheckable(True)
        self.select_button.setFlat(False)
        self.select_button.setFixedSize(18, 18)
        self.select_button.setToolTip("Select this property range")
        debug_print("MultiPropertyCell round selector created")
        debug_print("MultiPropertyCell round selector size=18x18")
        self.title_label = QLabel(label)
        self.title_label.setObjectName("multiPropertyTitleLabel")
        title_font = QFont(self.title_label.font())
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        debug_print("MultiPropertyCell title label style=multiPropertyTitleLabel")
        debug_print("MultiPropertyCell title font size=16")
        self.rename_button = QPushButton("✎")
        self.rename_button.setObjectName("multiPropertyTitleEditButton")
        self.rename_button.setFlat(True)
        self.rename_button.setFixedSize(22, 22)
        self.rename_button.setToolTip("Rename this property")
        debug_print("MultiPropertyCell rename button created")
        debug_print("MultiPropertyCell rename button pencil added")
        self.remove_button = QPushButton(QIcon(str(_ASSETS / "remove.png")), "")
        self.remove_button.setObjectName("multiPropertyIconButton")
        self.remove_button.setFlat(True)
        self.remove_button.setFixedSize(_CONTROL_BUTTON_W, _CONTROL_BUTTON_W)
        self.remove_button.setIconSize(QSize(_CONTROL_BUTTON_W, _CONTROL_BUTTON_W))
        self.remove_button.setToolTip("Remove this property")
        debug_print(f"MultiPropertyCell remove icon button width={_CONTROL_BUTTON_W}")
        debug_print("MultiPropertyCell remove icon button padding=0")
        debug_print("MultiPropertyCell remove icon button border=0")
        self._build_ui()
        self._connect_signals()
        debug_print(f"MultiPropertyCell property={property_key}")
        debug_print(f"MultiPropertyCell bottom_row={bottom_row}")
        debug_print("MultiPropertyCell.__init__ complete")

    def _build_ui(self) -> None:
        debug_print("MultiPropertyCell._build_ui called")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        debug_print("MultiPropertyCell root spacing set to 0")
        debug_print("MultiPropertyCell root size constraint fixed")
        self.controls = QWidget()
        self.controls.setObjectName("multiPropertyControls")
        self.controls.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        controls_layout = QVBoxLayout(self.controls)
        controls_layout.setContentsMargins(1, _TITLE_TOP_GAP, 1, _TITLE_BOTTOM_GAP)
        controls_layout.setSpacing(1)
        debug_print("MultiPropertyCell controls margins compact")
        debug_print(f"MultiPropertyCell title top gap={_TITLE_TOP_GAP}")
        debug_print(f"MultiPropertyCell title bottom gap={_TITLE_BOTTOM_GAP}")
        debug_print("MultiPropertyCell controls spacing=1")
        title_row = QWidget()
        title_row.setObjectName("multiPropertyTitleRow")
        title_row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        title_layout = QHBoxLayout(title_row)
        title_layout.setContentsMargins(6, 3, 6, 3)
        title_layout.setSpacing(_TITLE_ROW_GAP)
        title_layout.addWidget(self.select_button)
        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.rename_button)
        title_layout.addStretch(1)
        title_layout.addWidget(self.remove_button)
        debug_print(f"MultiPropertyCell title row spacing={_TITLE_ROW_GAP}")
        debug_print("MultiPropertyCell title row border enabled")
        debug_print("MultiPropertyCell title row margins=6,3,6,3")
        debug_print("MultiPropertyCell title row select bullet added")
        debug_print("MultiPropertyCell title row label added")
        debug_print("MultiPropertyCell title row edit button added after title")
        debug_print("MultiPropertyCell title row stretch added after edit button")
        debug_print("MultiPropertyCell title row remove button added at row end")
        controls_layout.addWidget(title_row)
        widgets = [self.heatmap, self.colorbar, self.controls] if self._bottom_row else [self.controls, self.colorbar, self.heatmap]
        for widget in widgets:
            root.addWidget(widget)
        self.set_cell_width(_CELL_W)
        debug_print("MultiPropertyCell layout built")

    def set_cell_width(self, width: int) -> None:
        debug_print("MultiPropertyCell.set_cell_width called")
        debug_print(f"MultiPropertyCell width={width}")
        self.set_heatmap_size(width, self.heatmap.height())
        debug_print("MultiPropertyCell width applied")

    def set_heatmap_size(self, width: int, height: int) -> None:
        debug_print("MultiPropertyCell.set_heatmap_size called")
        safe_width = max(_MIN_CELL_W, int(width))
        safe_height = max(1, int(height))
        debug_print(f"MultiPropertyCell heatmap width={safe_width}")
        debug_print(f"MultiPropertyCell heatmap height={safe_height}")
        self.heatmap.set_cell_size(safe_width, safe_height)
        self.colorbar.set_canvas_width(safe_width)
        self.controls.setFixedWidth(safe_width)
        self.setFixedWidth(safe_width)
        self.updateGeometry()
        debug_print(f"MultiPropertyCell controls fixed width={self.controls.width()}")
        debug_print("MultiPropertyCell no per-cell range widgets to resize")
        debug_print("MultiPropertyCell heatmap size applied")

    def _connect_signals(self) -> None:
        debug_print("MultiPropertyCell._connect_signals called")
        self.select_button.clicked.connect(lambda *_: self.select_requested.emit(self.property_key))
        self.remove_button.clicked.connect(lambda *_: self.remove_requested.emit(self.property_key))
        self.rename_button.clicked.connect(self._open_rename_dialog)
        debug_print("MultiPropertyCell signals connected")

    def rename_property(self, label: str) -> None:
        debug_print("MultiPropertyCell.rename_property called")
        debug_print(f"MultiPropertyCell rename requested label={label}")
        clean_label = str(label).strip()
        if not clean_label:
            debug_print("MultiPropertyCell rename skipped empty label")
            return
        self.label = clean_label
        self.title_label.setText(clean_label)
        self.renamed.emit(self.property_key, clean_label)
        debug_print(f"MultiPropertyCell renamed label={self.label}")
        debug_print("MultiPropertyCell title label updated")
        debug_print("MultiPropertyCell renamed signal emitted")

    def _open_rename_dialog(self) -> None:
        debug_print("MultiPropertyCell._open_rename_dialog called")
        debug_print(f"MultiPropertyCell rename current label={self.label}")
        dialog = self._build_rename_dialog()
        accepted = dialog.exec()
        label = dialog.textValue()
        debug_print(f"MultiPropertyCell rename dialog accepted={accepted}")
        debug_print(f"MultiPropertyCell rename dialog label={label}")
        if accepted:
            self.rename_property(label)

    def _build_rename_dialog(self) -> QInputDialog:
        debug_print("MultiPropertyCell._build_rename_dialog called")
        debug_print(f"MultiPropertyCell build dialog current label={self.label}")
        dialog = QInputDialog(self)
        dialog.setObjectName("multiPropertyRenameDialog")
        dialog.setWindowTitle("Rename Property")
        dialog.setLabelText("Property name:")
        dialog.setTextValue(self.label)
        dialog.setInputMode(QInputDialog.InputMode.TextInput)
        dialog.setMinimumWidth(360)
        dialog.setStyleSheet(
            """
QInputDialog#multiPropertyRenameDialog {
    background: #f7f9fc;
    color: #102a52;
}
QInputDialog#multiPropertyRenameDialog QLabel {
    color: #102a52;
    background: transparent;
}
QInputDialog#multiPropertyRenameDialog QLineEdit {
    background: #ffffff;
    color: #102a52;
    border: 1px solid #ccd7e8;
    border-radius: 8px;
    padding: 6px 8px;
    selection-background-color: #d9e7ff;
    selection-color: #102a52;
}
QInputDialog#multiPropertyRenameDialog QPushButton {
    background: #ffffff;
    color: #102a52;
    border: 1px solid #d2dbea;
    border-radius: 8px;
    padding: 6px 12px;
    font-weight: 700;
}
QInputDialog#multiPropertyRenameDialog QPushButton:hover {
    background: #eef4ff;
    border-color: #9fb5d6;
}
"""
        )
        debug_print("MultiPropertyCell rename dialog styled")
        return dialog

    def set_bottom_row(self, bottom_row: bool) -> None:
        debug_print("MultiPropertyCell.set_bottom_row called")
        debug_print(f"MultiPropertyCell requested bottom_row={bottom_row}")
        if self._bottom_row == bottom_row:
            debug_print("MultiPropertyCell bottom row unchanged")
            return
        self._bottom_row = bottom_row
        self._rebuild_order()

    def _rebuild_order(self) -> None:
        debug_print("MultiPropertyCell._rebuild_order called")
        layout = self.layout()
        widgets = []
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widgets.append(widget)
                widget.setParent(self)
        ordered = [self.heatmap, self.colorbar, self.controls] if self._bottom_row else [self.controls, self.colorbar, self.heatmap]
        for widget in ordered:
            layout.addWidget(widget)
        debug_print("MultiPropertyCell order rebuilt")

    def heatmap_top_offset(self) -> int:
        debug_print("MultiPropertyCell.heatmap_top_offset called")
        offset = 0
        layout = self.layout()
        for index in range(layout.count()):
            widget = layout.itemAt(index).widget()
            if widget is self.heatmap:
                debug_print(f"MultiPropertyCell heatmap top offset={offset}")
                return offset
            if widget is not None:
                widget_height = self._stable_layout_height(widget)
                offset += max(0, int(widget_height))
                debug_print(f"MultiPropertyCell offset add height={widget_height}")
        debug_print(f"MultiPropertyCell heatmap top offset fallback={offset}")
        return offset

    def heatmap_bottom_offset(self) -> int:
        debug_print("MultiPropertyCell.heatmap_bottom_offset called")
        after_heatmap = False
        offset = 0
        layout = self.layout()
        for index in range(layout.count()):
            widget = layout.itemAt(index).widget()
            if widget is self.heatmap:
                after_heatmap = True
                debug_print("MultiPropertyCell bottom offset after heatmap")
                continue
            if after_heatmap and widget is not None:
                widget_height = self._stable_layout_height(widget)
                offset += max(0, int(widget_height))
                debug_print(f"MultiPropertyCell bottom offset add height={widget_height}")
        debug_print(f"MultiPropertyCell heatmap bottom offset={offset}")
        return offset

    @staticmethod
    def _stable_layout_height(widget: QWidget) -> int:
        debug_print("MultiPropertyCell._stable_layout_height called")
        hint_height = widget.sizeHint().height()
        debug_print(f"MultiPropertyCell stable hint height={hint_height}")
        if hint_height > 0:
            return int(hint_height)
        widget_height = widget.height()
        debug_print(f"MultiPropertyCell stable fallback height={widget_height}")
        return int(widget_height)

    def set_selected(self, selected: bool) -> None:
        debug_print("MultiPropertyCell.set_selected called")
        debug_print(f"MultiPropertyCell selected={selected}")
        self.select_button.blockSignals(True)
        self.select_button.setChecked(bool(selected))
        self.select_button.setText("")
        self.select_button.blockSignals(False)
        debug_print(f"MultiPropertyCell round selector checked={self.select_button.isChecked()}")

    def render(
        self,
        x_grid,
        y_grid,
        z_grid,
        *,
        cmap,
        vmin: float,
        vmax: float,
        label: str,
        plot_type: str = "heatmap",
        overlay_grid=None,
        line_overlay=None,
    ) -> None:
        debug_print("MultiPropertyCell.render called")
        debug_print(f"MultiPropertyCell render property={self.property_key}")
        debug_print(f"MultiPropertyCell render vmin={vmin}")
        debug_print(f"MultiPropertyCell render vmax={vmax}")
        debug_print(f"MultiPropertyCell render label={label}")
        debug_print(f"MultiPropertyCell render plot_type={plot_type}")
        debug_print(f"MultiPropertyCell overlay present={overlay_grid is not None}")
        debug_print(f"MultiPropertyCell line overlay present={line_overlay is not None}")
        self.heatmap.render(
            x_grid,
            y_grid,
            z_grid,
            vmin=vmin,
            vmax=vmax,
            cmap=cmap,
            plot_type=plot_type,
            overlay_grid=overlay_grid,
            line_overlay=line_overlay,
            fill_canvas=False,
        )
        debug_print("MultiPropertyCell rendered heatmap fill_canvas=False")
        debug_print("MultiPropertyCell heatmap aspect preserved")
        placement = "bottom" if self._bottom_row else "top"
        debug_print(f"MultiPropertyCell colorbar placement={placement}")
        colorbar_label = label if str(label).startswith(self.label) else self.label
        debug_print(f"MultiPropertyCell colorbar label={colorbar_label}")
        self.colorbar.update_colorbar(cmap, vmin, vmax, colorbar_label, placement=placement)
        debug_print("MultiPropertyCell.render complete")

    def render_status(self, message: str) -> None:
        debug_print("MultiPropertyCell.render_status called")
        self.heatmap.render_status(message)
