"""Single View tab implementation."""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTabBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from utils.panel_load_worker import PanelLoadWorker
from viewer.panel_widget import PanelWidget

_REMOVE_ICON_PATH = Path(__file__).resolve().parent.parent / "assets" / "remove.png"


class SingleViewTab(QWidget):
    """Owns panel tabs for the Single View workflow."""

    panel_ready = Signal(object)  # emits PanelWidget after background load completes

    def __init__(self) -> None:
        super().__init__()
        self._projects: dict[str, dict] = {}
        self._panel_tabs = QTabWidget()
        self._panel_tabs.setObjectName("panelTabs")
        self._panel_tabs.setTabsClosable(False)
        self._panel_tabs.currentChanged.connect(self._refresh_tab_header_states)

        layout = QVBoxLayout(self)
        layout.addWidget(self._panel_tabs)

    def set_projects(self, projects: dict[str, dict]) -> None:
        self._projects = projects

    def add_panel(self, dataset_info: dict) -> None:
        """Start an async panel load — shows spinner immediately, creates panel when ready."""
        label = dataset_info.get("label", "Untitled Panel")

        loading = self._build_loading_widget(label)
        load_index = self._panel_tabs.addTab(loading, "Loading…")
        self._panel_tabs.setCurrentIndex(load_index)
        QApplication.processEvents()

        available = dataset_info.get("available_projects", [])
        files = available[0].get("files", []) if available else dataset_info.get("files", [])
        file_path = files[0] if files else ""

        if file_path:
            worker = PanelLoadWorker(file_path, parent=self)
            worker.finished.connect(
                lambda: self._finish_panel(load_index, label, dataset_info, worker)
            )
            worker.failed.connect(
                lambda msg: self._fail_panel(load_index, label, msg, worker)
            )
            worker.start()
        else:
            self._finish_panel(load_index, label, dataset_info, worker=None)

    def _finish_panel(self, load_index: int, label: str, dataset_info: dict, worker) -> None:
        """Called on main thread after worker warms the cache. Creates and installs the panel."""
        panel = PanelWidget(dataset_info=dataset_info, projects=self._projects)

        self._panel_tabs.removeTab(load_index)
        index = self._panel_tabs.insertTab(load_index, panel, label)
        self._panel_tabs.setTabText(index, "")
        tab_header = self._build_tab_header(label=label, panel=panel)
        self._panel_tabs.tabBar().setTabButton(index, QTabBar.ButtonPosition.LeftSide, tab_header)
        self._panel_tabs.setCurrentWidget(panel)
        self._refresh_tab_header_states()

        self.panel_ready.emit(panel)
        if worker is not None:
            worker.deleteLater()

    def _fail_panel(self, load_index: int, label: str, error_msg: str, worker) -> None:
        """Replace spinner with an error label if the worker fails."""
        err_widget = QLabel(f"Failed to load {label}:\n{error_msg}")
        err_widget.setObjectName("mutedInfo")
        err_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._panel_tabs.removeTab(load_index)
        index = self._panel_tabs.insertTab(load_index, err_widget, f"⚠ {label}")
        self._panel_tabs.setCurrentIndex(index)
        if worker is not None:
            worker.deleteLater()

    def _build_loading_widget(self, label: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel(f"Loading {label}…")
        lbl.setObjectName("mutedInfo")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bar = QProgressBar()
        bar.setRange(0, 0)
        bar.setFixedWidth(220)
        bar.setFixedHeight(6)
        layout.addWidget(lbl)
        layout.addSpacing(12)
        layout.addWidget(bar, 0, Qt.AlignmentFlag.AlignCenter)
        return widget

    def panel_count(self) -> int:
        return self._panel_tabs.count()

    def _build_tab_header(self, label: str, panel: PanelWidget) -> QWidget:
        header = QWidget()
        header.setObjectName("panelTabHeader")
        header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(12, 1, 0, 1)
        layout.setSpacing(4)
        text_label = QLabel(label)
        text_label.setObjectName("panelTabLabel")
        text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(text_label, 4)

        close_column = QWidget()
        close_column.setObjectName("panelTabCloseColumn")
        close_column.setFixedWidth(18)
        close_column.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        close_layout = QHBoxLayout(close_column)
        close_layout.setContentsMargins(2, 0, 0, 4)
        close_layout.setSpacing(0)

        close_button = QPushButton()
        close_button.setObjectName("panelTabCloseButton")
        close_button.setFlat(True)
        close_button.setFixedSize(12, 12)
        close_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        close_button.setIcon(QIcon(str(_REMOVE_ICON_PATH)))
        close_button.setIconSize(close_button.size())
        close_button.clicked.connect(
            lambda checked=False, target_panel=panel: self._remove_panel_for_widget(target_panel)
        )

        close_layout.addWidget(close_button)
        layout.addWidget(close_column, 1)
        layout.setStretch(0, 4)
        layout.setStretch(1, 1)
        return header

    def _refresh_tab_header_states(self, current_index: int | None = None) -> None:
        if current_index is None:
            current_index = self._panel_tabs.currentIndex()
        tab_bar = self._panel_tabs.tabBar()
        for index in range(self._panel_tabs.count()):
            is_selected = index == current_index
            header = tab_bar.tabButton(index, QTabBar.ButtonPosition.LeftSide)
            if header is None:
                continue
            self._set_tab_header_selected_state(header=header, is_selected=is_selected)

    def _set_tab_header_selected_state(self, header: QWidget, is_selected: bool) -> None:
        selected_value = "true" if is_selected else "false"
        header.setProperty("selected", selected_value)
        label = header.findChild(QLabel, "panelTabLabel")
        if label is not None:
            label.setProperty("selected", selected_value)
            label.style().unpolish(label)
            label.style().polish(label)
        header.style().unpolish(header)
        header.style().polish(header)

    def _remove_panel_for_widget(self, panel: PanelWidget) -> None:
        index = self._panel_tabs.indexOf(panel)
        if index < 0:
            return
        self._remove_panel(index)

    def _remove_panel(self, index: int) -> None:
        widget = self._panel_tabs.widget(index)
        self._panel_tabs.removeTab(index)
        self._refresh_tab_header_states()
        if widget is not None:
            widget.deleteLater()
