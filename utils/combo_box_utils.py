"""Helpers for making opened combo-box popups wide enough for their text."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QComboBox

from app.debug import debug_print

_POPUP_PADDING = 40
_ICON_PADDING = 8
_MIN_EMPTY_WIDTH = 72


def compute_combo_popup_width(combo: QComboBox, *, max_width: int | None = None) -> int:
    """Return a popup width that can fit the combo's longest visible item."""
    debug_print("compute_combo_popup_width called")
    debug_print(f"combo objectName={combo.objectName()}")
    item_count = combo.count()
    debug_print(f"combo item_count={item_count}")
    visible_width = combo.width() if combo.isVisible() else 0
    closed_width = max(visible_width, combo.minimumWidth(), _MIN_EMPTY_WIDTH)
    debug_print(f"combo visible_width={visible_width}")
    debug_print(f"combo closed_width={closed_width}")
    metrics = combo.view().fontMetrics() if combo.view() else combo.fontMetrics()
    longest = 0
    icon_extent = 0
    for index in range(item_count):
        text = combo.itemText(index)
        text_width = metrics.horizontalAdvance(text)
        debug_print(f"combo item index={index}")
        debug_print(f"combo item text_width={text_width}")
        longest = max(longest, text_width)
        icon = combo.itemIcon(index)
        if not icon.isNull():
            icon_size = combo.iconSize()
            icon_extent = max(icon_extent, icon_size.width() + _ICON_PADDING)
            debug_print(f"combo icon_extent={icon_extent}")
    scrollbar_width = combo.view().verticalScrollBar().sizeHint().width() if combo.view() else 0
    debug_print(f"combo scrollbar_width={scrollbar_width}")
    frame_width = combo.view().frameWidth() * 2 if combo.view() else 0
    debug_print(f"combo frame_width={frame_width}")
    computed = max(closed_width, longest + icon_extent + scrollbar_width + frame_width + _POPUP_PADDING)
    debug_print(f"combo computed before cap={computed}")
    cap = max_width if max_width is not None else _screen_popup_cap(combo)
    debug_print(f"combo popup cap={cap}")
    if cap is not None and cap > 0:
        computed = min(computed, cap)
    debug_print(f"combo computed popup width={computed}")
    return int(computed)


def update_combo_popup_width(combo: QComboBox, *, max_width: int | None = None) -> int:
    """Set the combo popup view minimum width without changing the closed combo."""
    debug_print("update_combo_popup_width called")
    width = compute_combo_popup_width(combo, max_width=max_width)
    debug_print(f"combo applying popup width={width}")
    combo.view().setMinimumWidth(width)
    debug_print("combo popup width applied")
    return width


def update_combo_popups(combos) -> None:
    """Update popup widths for a sequence of combo boxes."""
    debug_print("update_combo_popups called")
    for combo in combos:
        if combo is None:
            debug_print("update_combo_popups skipping None")
            continue
        update_combo_popup_width(combo)
    debug_print("update_combo_popups complete")


def _screen_popup_cap(combo: QComboBox) -> int | None:
    debug_print("_screen_popup_cap called")
    screen = combo.screen() or QApplication.primaryScreen()
    if screen is None:
        debug_print("no screen available for popup cap")
        return None
    available_width = screen.availableGeometry().width()
    cap = max(160, available_width - 32)
    debug_print(f"screen popup cap={cap}")
    return cap
