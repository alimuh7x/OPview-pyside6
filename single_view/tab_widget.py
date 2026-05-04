"""Single View tab implementation."""

from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from app.debug import debug_print
from viewer.panel_widget import PanelWidget


class SingleViewTab(QWidget):
    """Owns panel tabs for the Single View workflow."""

    def __init__(self) -> None:
        debug_print("SingleViewTab.__init__ start")
        super().__init__()
        self._projects: dict[str, dict] = {}
        self._panel_tabs = QTabWidget()
        self._panel_tabs.setObjectName("panelTabs")
        self._panel_tabs.setTabsClosable(True)
        self._panel_tabs.tabCloseRequested.connect(self._remove_panel)
        layout = QVBoxLayout(self)
        layout.addWidget(self._panel_tabs)
        debug_print("SingleViewTab.__init__ complete")

    def set_projects(self, projects: dict[str, dict]) -> None:
        debug_print("SingleViewTab.set_projects called")
        debug_print(f"SingleViewTab storing {len(projects)} projects")
        self._projects = projects

    def add_panel(self, dataset_info: dict) -> PanelWidget:
        debug_print("SingleViewTab.add_panel called")
        debug_print(f"SingleViewTab creating panel for {dataset_info.get('label')}")
        panel = PanelWidget(dataset_info=dataset_info, projects=self._projects)
        label = dataset_info.get("label", "Untitled Panel")
        self._panel_tabs.addTab(panel, label)
        self._panel_tabs.setCurrentWidget(panel)
        debug_print(f"SingleViewTab panel count now {self.panel_count()}")
        return panel

    def panel_count(self) -> int:
        debug_print("SingleViewTab.panel_count called")
        return self._panel_tabs.count()

    def _remove_panel(self, index: int) -> None:
        debug_print(f"SingleViewTab._remove_panel called with index={index}")
        widget = self._panel_tabs.widget(index)
        self._panel_tabs.removeTab(index)
        if widget is not None:
            widget.deleteLater()
        debug_print(f"SingleViewTab panel removed, remaining={self.panel_count()}")
