"""Tabbed Custom Graph workspace."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize
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

_ASSETS = Path(__file__).resolve().parent.parent / "assets"
_REMOVE = str(_ASSETS / "remove.png")


class _GraphTabBar(QTabBar):
    """Tab bar with a wider final add tab."""

    def tabSizeHint(self, index: int) -> QSize:  # noqa: N802
        size = super().tabSizeHint(index)
        if index == self.count() - 1:
            size.setWidth(size.width() * 2)
        return size


class CustomGraphTab(QWidget):
    """Owns graph-panel tabs and the add button."""

    def __init__(self, parent=None) -> None:
        debug_print("CustomGraphTab.__init__ start")
        super().__init__(parent)
        self._projects: dict[str, dict] = {}
        self._selected_project_names: list[str] = []
        self._next_panel_number = 1
        self._plus_tab = QWidget()
        self._creating_tab = False
        self._activating_plus_tab = False
        self._build_ui()
        self.add_graph_panel()
        debug_print("CustomGraphTab.__init__ complete")

    def set_projects(self, projects: dict[str, dict]) -> None:
        debug_print(f"CustomGraphTab.set_projects count={len(projects)}")
        self._projects = projects
        self._selected_project_names = [
            name for name in self._selected_project_names if name in self._projects
        ]
        for index in range(self._tabs.count()):
            panel = self._tabs.widget(index)
            if isinstance(panel, GraphPanelWidget):
                panel.set_project_scope(self._projects, self._selected_project_names)

    def set_selected_project_names(self, project_names: list[str]) -> None:
        debug_print(f"CustomGraphTab.set_selected_project_names count={len(project_names)}")
        self._selected_project_names = [name for name in project_names if name in self._projects]
        for index in range(self._tabs.count()):
            panel = self._tabs.widget(index)
            if isinstance(panel, GraphPanelWidget):
                panel.set_project_scope(self._projects, self._selected_project_names)

    def add_graph_panel(self) -> GraphPanelWidget:
        debug_print("CustomGraphTab.add_graph_panel called")
        panel_number = self._next_panel_number
        self._next_panel_number += 1
        label = f"Graph Tab {panel_number}"
        panel = GraphPanelWidget(
            panel_number=panel_number,
            projects=self._projects,
            selected_project_names=self._selected_project_names,
        )
        insert_index = self._plus_index()
        if insert_index < 0:
            insert_index = self._tabs.count()
        self._creating_tab = True
        index = self._tabs.insertTab(insert_index, panel, label)
        self._creating_tab = False
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
        self._tabs.setTabBar(_GraphTabBar())
        self._tabs.setProperty("class", "panelTabs")
        self._tabs.setTabsClosable(False)
        self._tabs.setTabPosition(QTabWidget.TabPosition.North)
        self._tabs.currentChanged.connect(self._refresh_header_states)
        self._tabs.tabBarClicked.connect(self._on_tab_bar_clicked)
        self._creating_tab = True
        self._tabs.addTab(self._plus_tab, "+")
        self._creating_tab = False
        self._tabs.setTabToolTip(0, "Add graph tab")
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
        panel.deleteLater()
        if self._graph_tab_count() == 0:
            self.add_graph_panel()
        else:
            self._refresh_header_states()
        debug_print("CustomGraphTab._remove_panel complete")

    def _plus_index(self) -> int:
        return self._tabs.indexOf(self._plus_tab)

    def _graph_tab_count(self) -> int:
        return max(0, self._tabs.count() - 1)

    def _on_tab_bar_clicked(self, index: int) -> None:
        debug_print(f"CustomGraphTab._on_tab_bar_clicked index={index}")
        if index == self._plus_index():
            self._activating_plus_tab = True
            self.add_graph_panel()
            self._activating_plus_tab = False

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
