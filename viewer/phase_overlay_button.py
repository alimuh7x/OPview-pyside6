"""Toolbar 'Overlays' drop-down: Interfaces plus one entry per phase."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QRect, Qt, Signal
from PySide6.QtGui import QColor, QPen, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QComboBox, QSizePolicy, QStyle, QStyledItemDelegate

from app.debug import debug_print
from utils.combo_box_utils import fit_combo_to_longest_item, update_combo_popup_width

_INTERFACES_KEY = "__interfaces__"
_POPUP_MIN_WIDTH = 280
_CLOSED_TEXT_SAMPLE = "Overlays (99)"
_CONTROL_COLOR = QColor("#102a52")
_HOVER_CONTROL_COLOR = QColor("#ffffff")
_VALUE_W = 36  # wide enough for '+10' / '-10'
_SLOT_W = 26  # width of each clickable icon slot at the right edge of a row
MIN_INTERFACE_WIDTH = -10  # negative narrows the interface band, positive thickens it
MAX_INTERFACE_WIDTH = 10


def _rename_rect(row: QRect) -> QRect:
    return QRect(row.right() - _SLOT_W + 1, row.top(), _SLOT_W, row.height())


def _stepper_rects(row: QRect) -> tuple[QRect, QRect, QRect]:
    """(minus, value, plus) slots, right-aligned in the row."""
    plus = QRect(row.right() - _SLOT_W + 1, row.top(), _SLOT_W, row.height())
    value = QRect(plus.left() - _VALUE_W, row.top(), _VALUE_W, row.height())
    minus = QRect(value.left() - _SLOT_W, row.top(), _SLOT_W, row.height())
    return minus, value, plus


class _OverlayRowDelegate(QStyledItemDelegate):
    """Draws the rename pencil on phase rows and '− n +' on the Interfaces row."""

    def __init__(self, owner: "PhaseOverlayButton") -> None:
        super().__init__(owner)
        self._owner = owner

    def paint(self, painter, option, index) -> None:  # noqa: N802
        super().paint(painter, option, index)
        key = index.data(Qt.ItemDataRole.UserRole)
        if key is None:
            return
        painter.save()
        # The popup's hover row is dark blue (#1e4a8a) with white text; otherwise the row is light.
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        painter.setPen(QPen(_HOVER_CONTROL_COLOR if hovered else _CONTROL_COLOR))
        if key == _INTERFACES_KEY:
            minus, value, plus = _stepper_rects(option.rect)
            width = self._owner.interface_width()
            bold = painter.font()
            bold.setBold(True)
            painter.setFont(bold)
            painter.drawText(minus, Qt.AlignmentFlag.AlignCenter, "−")
            painter.drawText(value, Qt.AlignmentFlag.AlignCenter, f"{width:+d}" if width else "0")
            painter.drawText(plus, Qt.AlignmentFlag.AlignCenter, "+")
        else:
            painter.drawText(_rename_rect(option.rect), Qt.AlignmentFlag.AlignCenter, "✎")
        painter.restore()


class PhaseOverlayButton(QComboBox):
    """Same look as the other toolbar combos; its checkable popup stays open.

    Row 0 is the closed-state caption ("Overlays (n)") and is hidden in the popup.
    Rows below are checkable: "Interfaces" (with a '− n +' interface-width
    stepper at its right edge) then one row per phase (with a rename pencil).
    Nothing is ticked by default, and phase ticks survive `set_phases`.
    """

    selection_changed = Signal()
    interfaces_toggled = Signal(bool)
    interface_width_changed = Signal(int)
    rename_requested = Signal(str, str)  # (phase key, current label)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("viewerCombo")
        self.setToolTip(
            "Interfaces, and phases drawn where phase fraction ≥ 0.5, on top of the current field"
        )
        self._interface_width = 0  # as drawn; negative narrows, positive thickens
        self._model = QStandardItemModel(self)
        self.setModel(self._model)
        self.setItemDelegate(_OverlayRowDelegate(self))
        self._caption = QStandardItem("Overlays")
        self._caption.setFlags(Qt.ItemFlag.ItemIsEnabled)
        self._model.appendRow(self._caption)
        self._interfaces_item = self._add_item("Interfaces", _INTERFACES_KEY)
        self._phase_items: dict[str, QStandardItem] = {}
        self.view().viewport().installEventFilter(self)
        self.view().setRowHidden(0, True)  # caption row is only for the closed state
        self.setCurrentIndex(0)
        self._refresh_caption()
        self._fit_width()
        # Never let a tight toolbar squeeze the caption ("Overlays (2)" must stay readable).
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def _add_item(self, label: str, key: str) -> QStandardItem:
        item = QStandardItem(label)
        item.setData(key, Qt.ItemDataRole.UserRole)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
        item.setData(Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
        self._model.appendRow(item)
        return item

    def _fit_width(self) -> None:
        self.addItem(_CLOSED_TEXT_SAMPLE)  # measured, then removed
        fit_combo_to_longest_item(self)
        self.removeItem(self.count() - 1)
        update_combo_popup_width(self, max_width=None)
        self.view().setMinimumWidth(max(self.view().minimumWidth(), _POPUP_MIN_WIDTH))

    def set_phases(self, phases: list[tuple[str, str]]) -> None:
        """Rebuild phase rows from (key, label) pairs, keeping still-valid ticks."""
        debug_print("PhaseOverlayButton.set_phases called")
        keep = set(self.checked_keys())
        for item in self._phase_items.values():
            self._model.removeRow(item.row())
        self._phase_items = {}
        for key, label in phases:
            item = self._add_item(label, key)
            if key in keep:
                item.setData(Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)
            self._phase_items[key] = item
        self.setCurrentIndex(0)
        self._refresh_caption()
        self.view().setMinimumWidth(max(self.view().minimumWidth(), _POPUP_MIN_WIDTH))
        if keep != set(self.checked_keys()):
            self.selection_changed.emit()

    def phase_keys(self) -> list[str]:
        return list(self._phase_items)

    def checked_keys(self) -> list[str]:
        return [key for key, item in self._phase_items.items() if self._is_checked(item)]

    def interfaces_checked(self) -> bool:
        return self._is_checked(self._interfaces_item)

    def set_interfaces_checked(self, checked: bool) -> None:
        self._set_checked(self._interfaces_item, checked)

    def set_phase_checked(self, key: str, checked: bool) -> None:
        self._set_checked(self._phase_items[key], checked)

    def interface_width(self) -> int:
        return self._interface_width

    def set_interface_width(self, width: int) -> None:
        width = max(MIN_INTERFACE_WIDTH, min(MAX_INTERFACE_WIDTH, int(width)))
        if width == self._interface_width:
            return
        self._interface_width = width
        self.view().viewport().update()
        self.interface_width_changed.emit(width)

    def set_label(self, key: str, label: str) -> None:
        item = self._phase_items.get(key)
        if item is not None and item.text() != label:
            item.setText(label)

    @staticmethod
    def _is_checked(item: QStandardItem) -> bool:
        return item.data(Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked

    def _set_checked(self, item: QStandardItem, checked: bool) -> None:
        if self._is_checked(item) == bool(checked):
            return
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        item.setData(state, Qt.ItemDataRole.CheckStateRole)
        self._refresh_caption()
        if item is self._interfaces_item:
            self.interfaces_toggled.emit(bool(checked))
        else:
            self.selection_changed.emit()

    def _refresh_caption(self) -> None:
        count = len(self.checked_keys()) + (1 if self.interfaces_checked() else 0)
        self._caption.setText(f"Overlays ({count})" if count else "Overlays")
        self.setCurrentIndex(0)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if watched is self.view().viewport() and event.type() == QEvent.Type.MouseButtonRelease:
            self._handle_popup_click(event.position().toPoint())
            return True  # swallow: the popup must stay open
        return super().eventFilter(watched, event)

    def _handle_popup_click(self, pos) -> None:
        index = self.view().indexAt(pos)
        if not index.isValid() or index.row() < 1:
            return
        item = self._model.itemFromIndex(index)
        row = self.view().visualRect(index)
        key = index.data(Qt.ItemDataRole.UserRole)
        if key == _INTERFACES_KEY:
            minus, _value, plus = _stepper_rects(row)
            if minus.contains(pos):
                self.set_interface_width(self._interface_width - 1)
                return
            if plus.contains(pos):
                self.set_interface_width(self._interface_width + 1)
                return
        elif _rename_rect(row).contains(pos):
            self.hidePopup()
            self.rename_requested.emit(key, item.text())
            return
        self._set_checked(item, not self._is_checked(item))
