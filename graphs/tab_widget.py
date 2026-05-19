"""Tabbed Custom Graph workspace."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTabBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.debug import debug_print
from graphs.graph_panel_widget import GraphPanelWidget
from utils.project_scanner import get_textdata_files

_ASSETS = Path(__file__).resolve().parent.parent / "assets"
_REMOVE = str(_ASSETS / "remove.png")


class CustomGraphTab(QWidget):
    """Owns graph-panel tabs and the add button."""

    def __init__(self, parent=None) -> None:
        debug_print("CustomGraphTab.__init__ start")
        super().__init__(parent)
        self._projects: dict[str, dict] = {}
        self._suggested_files: list[str] = []
        self._next_panel_number = 1
        self._build_ui()
        debug_print("CustomGraphTab.__init__ complete")

    def set_projects(self, projects: dict[str, dict]) -> None:
        debug_print(f"CustomGraphTab.set_projects count={len(projects)}")
        self._projects = projects
        self._suggested_files = get_textdata_files(projects)
        debug_print(f"CustomGraphTab.set_projects suggested_files={len(self._suggested_files)}")
        for index in range(self._tabs.count()):
            panel = self._tabs.widget(index)
            if isinstance(panel, GraphPanelWidget):
                panel.set_suggested_files(self._suggested_files)

    def add_graph_panel(self) -> GraphPanelWidget:
        debug_print("CustomGraphTab.add_graph_panel called")
        panel_number = self._next_panel_number
        self._next_panel_number += 1
        label = f"Graph Panel {panel_number}"
        panel = GraphPanelWidget(panel_number=panel_number, suggested_files=self._suggested_files)
        index = self._tabs.addTab(panel, label)
        self._tabs.setTabText(index, "")
        header = self._build_tab_header(label, panel)
        self._tabs.tabBar().setTabButton(index, QTabBar.ButtonPosition.LeftSide, header)
        self._tabs.setCurrentWidget(panel)
        self._refresh_header_states()
        debug_print(f"CustomGraphTab.add_graph_panel complete label={label}")
        return panel

    def add_files_to_active_panel(self, files: list[str]) -> GraphPanelWidget:
        debug_print(f"CustomGraphTab.add_files_to_active_panel files={files}")
        panel = self._tabs.currentWidget()
        if not isinstance(panel, GraphPanelWidget):
            debug_print("CustomGraphTab.add_files_to_active_panel creating panel")
            panel = self.add_graph_panel()
        panel.add_files(files)
        debug_print("CustomGraphTab.add_files_to_active_panel complete")
        return panel

    def set_available_width(self, width: int) -> None:
        debug_print(f"CustomGraphTab.set_available_width width={width}")
        self.setMinimumWidth(0)
        self.setMaximumWidth(16777215)
        self._tabs.setMinimumWidth(0)
        self._tabs.setMaximumWidth(16777215)
        for index in range(self._tabs.count()):
            panel = self._tabs.widget(index)
            panel.setMinimumWidth(0)
            panel.setMaximumWidth(16777215)
            if hasattr(panel, "set_available_width"):
                panel.set_available_width(width)

    def _build_ui(self) -> None:
        debug_print("CustomGraphTab._build_ui called")
        root = QVBoxLayout(self)
        root.setContentsMargins(9, 9, 9, 9)
        root.setSpacing(0)

        self._tabs = QTabWidget()
        self._tabs.setObjectName("graphPanelTabs")
        self._tabs.setProperty("class", "panelTabs")
        self._tabs.setTabsClosable(False)
        self._tabs.setTabPosition(QTabWidget.TabPosition.North)
        self._tabs.currentChanged.connect(self._refresh_header_states)

        self.add_graph_button = QPushButton("+ Add Graph Panel")
        self.add_graph_button.setObjectName("addGraphPanelButton")
        self.add_graph_button.setProperty("accent", True)
        self.add_graph_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.add_graph_button.clicked.connect(self.add_graph_panel)
        self._tabs.setCornerWidget(self.add_graph_button, Qt.Corner.TopRightCorner)
        debug_print("CustomGraphTab._build_ui add graph button moved to tab corner")
        root.addWidget(self._tabs, 1)
        debug_print("CustomGraphTab._build_ui complete")

    def _build_tab_header(self, label: str, panel: GraphPanelWidget) -> QWidget:
        debug_print(f"CustomGraphTab._build_tab_header label={label}")
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
        button.clicked.connect(lambda *_: self._remove_panel(panel))
        close_layout.addWidget(button)
        layout.addWidget(close_col, 1)
        return header

    def _remove_panel(self, panel: GraphPanelWidget) -> None:
        debug_print("CustomGraphTab._remove_panel called")
        index = self._tabs.indexOf(panel)
        if index < 0:
            debug_print("CustomGraphTab._remove_panel panel missing")
            return
        self._tabs.removeTab(index)
        self._refresh_header_states()
        panel.deleteLater()
        debug_print("CustomGraphTab._remove_panel complete")

    def _refresh_header_states(self, current_index: int | None = None) -> None:
        debug_print("CustomGraphTab._refresh_header_states called")
        if current_index is None:
            current_index = self._tabs.currentIndex()
        bar = self._tabs.tabBar()
        for index in range(self._tabs.count()):
            header = bar.tabButton(index, QTabBar.ButtonPosition.LeftSide)
            if header is None:
                continue
            selected = "true" if index == current_index else "false"
            header.setProperty("selected", selected)
            label = header.findChild(QLabel, "panelTabLabel")
            if label is not None:
                label.setProperty("selected", selected)
                label.style().unpolish(label)
                label.style().polish(label)
            header.style().unpolish(header)
            header.style().polish(header)
