"""Multi Property tab container."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QTabBar, QTabWidget, QVBoxLayout, QWidget

from app.debug import debug_print
from multi_property.multi_property_panel import MultiPropertyPanel

_ASSETS = Path(__file__).resolve().parent.parent / "assets"
_REMOVE = str(_ASSETS / "remove.png")


class MultiPropertyTab(QWidget):
    """Owns one-file multi-property tabs."""

    def __init__(self, parent=None) -> None:
        debug_print("MultiPropertyTab.__init__ start")
        super().__init__(parent)
        self._available_width: int | None = None
        debug_print("MultiPropertyTab available width initialized")
        self._tabs = QTabWidget()
        self._tabs.setObjectName("panelTabs")
        self._tabs.setTabsClosable(False)
        self._tabs.setTabPosition(QTabWidget.TabPosition.North)
        self._tabs.currentChanged.connect(self._refresh_header_states)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(9, 9, 9, 9)
        layout.setSpacing(0)
        layout.addWidget(self._tabs)
        debug_print("MultiPropertyTab.__init__ complete")

    def set_dataset(self, dataset_info: dict) -> None:
        debug_print("MultiPropertyTab.set_dataset called")
        label = dataset_info.get("label", "Multi Property")
        debug_print(f"MultiPropertyTab dataset label={label}")
        panel = MultiPropertyPanel(dataset_info)
        if self._available_width is not None:
            panel.set_available_width(self._available_width)
            debug_print(f"MultiPropertyTab applied stored width to new panel={self._available_width}")
        else:
            debug_print("MultiPropertyTab no stored width for new panel")
        index = self._tabs.addTab(panel, label)
        debug_print(f"MultiPropertyTab added tab index={index}")
        self._tabs.setTabText(index, "")
        header = self._build_tab_header(label, panel)
        self._tabs.tabBar().setTabButton(index, QTabBar.ButtonPosition.LeftSide, header)
        self._tabs.setCurrentWidget(panel)
        self._refresh_header_states()
        debug_print("MultiPropertyTab.set_dataset complete")

    def set_available_width(self, width: int) -> None:
        debug_print("MultiPropertyTab.set_available_width called")
        debug_print(f"MultiPropertyTab available width={width}")
        self._available_width = int(width)
        debug_print(f"MultiPropertyTab stored available width={self._available_width}")
        self.setMinimumWidth(0)
        self.setMaximumWidth(width)
        self._tabs.setMinimumWidth(0)
        self._tabs.setMaximumWidth(width)
        for index in range(self._tabs.count()):
            widget = self._tabs.widget(index)
            widget.setMinimumWidth(0)
            widget.setMaximumWidth(width)
            if hasattr(widget, "set_available_width"):
                widget.set_available_width(width)
                debug_print(f"MultiPropertyTab applied width to child index={index}")

    def _build_tab_header(self, label: str, panel: MultiPropertyPanel) -> QWidget:
        debug_print("MultiPropertyTab._build_tab_header called")
        debug_print(f"MultiPropertyTab header label={label}")
        header = QWidget()
        header.setObjectName("panelTabHeader")
        header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(12, 1, 0, 1)
        layout.setSpacing(4)
        text = QLabel(label)
        text.setObjectName("panelTabLabel")
        text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(text, 4)
        close_col = QWidget()
        close_col.setObjectName("panelTabCloseColumn")
        close_col.setFixedWidth(18)
        close_col.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        close_layout = QHBoxLayout(close_col)
        close_layout.setContentsMargins(2, 0, 0, 4)
        close_layout.setSpacing(0)
        button = QPushButton()
        button.setObjectName("panelTabCloseButton")
        button.setFlat(True)
        button.setFixedSize(12, 12)
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        button.setIcon(QIcon(_REMOVE))
        button.setIconSize(button.size())
        button.clicked.connect(lambda _, p=panel: self._remove_panel(p))
        close_layout.addWidget(button)
        layout.addWidget(close_col, 1)
        debug_print("MultiPropertyTab header built")
        return header

    def _remove_panel(self, panel: MultiPropertyPanel) -> None:
        debug_print("MultiPropertyTab._remove_panel called")
        index = self._tabs.indexOf(panel)
        debug_print(f"MultiPropertyTab remove index={index}")
        if index < 0:
            debug_print("MultiPropertyTab remove skipped missing panel")
            return
        self._tabs.removeTab(index)
        self._refresh_header_states()
        panel.deleteLater()
        debug_print("MultiPropertyTab panel removed")

    def _refresh_header_states(self, current_index: int | None = None) -> None:
        debug_print("MultiPropertyTab._refresh_header_states called")
        if current_index is None:
            current_index = self._tabs.currentIndex()
        debug_print(f"MultiPropertyTab current index={current_index}")
        bar = self._tabs.tabBar()
        for index in range(self._tabs.count()):
            header = bar.tabButton(index, QTabBar.ButtonPosition.LeftSide)
            if header is None:
                continue
            selected = "true" if index == current_index else "false"
            header.setProperty("selected", selected)
            label = header.findChild(QLabel, "panelTabLabel")
            if label:
                label.setProperty("selected", selected)
                label.style().unpolish(label)
                label.style().polish(label)
            header.style().unpolish(header)
            header.style().polish(header)
        debug_print("MultiPropertyTab header states refreshed")
