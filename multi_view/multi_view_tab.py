"""Multi View tab container — QTabWidget that holds MultiViewPanel instances."""

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

from multi_view.multi_view_panel import MultiViewPanel

_ASSETS = Path(__file__).resolve().parent.parent / "assets"
_REMOVE = str(_ASSETS / "remove.png")


class MultiViewTab(QWidget):
    """Owns comparison-group tabs for the Multi View workflow."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._tabs = QTabWidget()
        self._tabs.setObjectName("panelTabs")
        self._tabs.setTabsClosable(False)
        self._tabs.setTabPosition(QTabWidget.TabPosition.North)
        self._tabs.currentChanged.connect(self._refresh_header_states)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._tabs)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_dataset(self, dataset_info: dict) -> None:
        """Add a new comparison tab for the given dataset."""
        label  = dataset_info.get("label", "Comparison")
        panel  = MultiViewPanel(dataset_info)
        index  = self._tabs.addTab(panel, label)
        self._tabs.setTabText(index, "")
        header = self._build_tab_header(label, panel)
        self._tabs.tabBar().setTabButton(index, QTabBar.ButtonPosition.LeftSide, header)
        self._tabs.setCurrentWidget(panel)
        self._refresh_header_states()

    # ── Tab header (same pattern as SingleViewTab) ────────────────────────────

    def _build_tab_header(self, label: str, panel: MultiViewPanel) -> QWidget:
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
        cl = QHBoxLayout(close_col)
        cl.setContentsMargins(2, 0, 0, 4)
        cl.setSpacing(0)

        btn = QPushButton()
        btn.setObjectName("panelTabCloseButton")
        btn.setFlat(True)
        btn.setFixedSize(12, 12)
        btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn.setIcon(QIcon(_REMOVE))
        btn.setIconSize(btn.size())
        btn.clicked.connect(lambda _, p=panel: self._remove_panel(p))
        cl.addWidget(btn)

        layout.addWidget(close_col, 1)
        layout.setStretch(0, 4)
        layout.setStretch(1, 1)
        return header

    def _remove_panel(self, panel: MultiViewPanel) -> None:
        idx = self._tabs.indexOf(panel)
        if idx < 0:
            return
        self._tabs.removeTab(idx)
        self._refresh_header_states()
        panel.deleteLater()

    def _refresh_header_states(self, current_index: int | None = None) -> None:
        if current_index is None:
            current_index = self._tabs.currentIndex()
        bar = self._tabs.tabBar()
        for i in range(self._tabs.count()):
            hdr = bar.tabButton(i, QTabBar.ButtonPosition.LeftSide)
            if hdr is None:
                continue
            sel = "true" if i == current_index else "false"
            hdr.setProperty("selected", sel)
            lbl = hdr.findChild(QLabel, "panelTabLabel")
            if lbl:
                lbl.setProperty("selected", sel)
                lbl.style().unpolish(lbl); lbl.style().polish(lbl)
            hdr.style().unpolish(hdr); hdr.style().polish(hdr)
