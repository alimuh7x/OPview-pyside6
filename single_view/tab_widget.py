"""Single View tab implementation."""

from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QTabBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from viewer.panel_widget import PanelWidget

_REMOVE_ICON_PATH = Path(__file__).resolve().parent.parent / "assets" / "remove.png"


class SingleViewTab(QWidget):
    """Owns panel tabs for the Single View workflow."""

    def __init__(self) -> None:
        super().__init__()
        self._projects: dict[str, dict] = {}                                      # stores project metadata keyed by project name
        self._panel_tabs = QTabWidget()                                           # main tab container holding all panels
        self._panel_tabs.setObjectName("panelTabs")                               # names widget for QSS targeting
        self._panel_tabs.setTabsClosable(False)                                   # disables built-in close buttons (custom ones used)
        self._panel_tabs.currentChanged.connect(self._refresh_tab_header_states)  # updates header styles on tab switch

        layout = QVBoxLayout(self)                                                # vertical layout fills the widget
        layout.addWidget(self._panel_tabs)                                        # panel tabs occupy the full area

    def set_projects(self, projects: dict[str, dict]) -> None:
        self._projects = projects                                                 # caches project dict for use when creating panels

    def add_panel(self, dataset_info: dict) -> PanelWidget:
        panel = PanelWidget(dataset_info=dataset_info, projects=self._projects)                     # creates panel for the dataset
        label = dataset_info.get("label", "Untitled Panel")                                         # reads display name from dataset info
        index = self._panel_tabs.addTab(panel, label)                                               # adds panel as a new tab, returns its index
        self._panel_tabs.setTabText(index, "")                                                      # clears default text so custom header widget shows cleanly
        tab_header = self._build_tab_header(label=label, panel=panel)                               # builds custom header with label + close button
        self._panel_tabs.tabBar().setTabButton(index, QTabBar.ButtonPosition.LeftSide, tab_header)  # installs custom header into the tab bar
        self._panel_tabs.setCurrentWidget(panel)                                                    # switches focus to the newly added panel
        self._refresh_tab_header_states()                                                           # updates selected/unselected visual state for all headers
        return panel

    def panel_count(self) -> int:
        return self._panel_tabs.count()  # returns number of open panel tabs

    def _build_tab_header(self, label: str, panel: PanelWidget) -> QWidget:

        header = QWidget()                                                                    # container widget for the entire tab header
        header.setObjectName("panelTabHeader")                                                # names widget for [QSS] targeting
        header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)      # allows header to grow horizontally
        layout = QHBoxLayout(header)                                                          # horizontal layout: label on left, close button on right
        layout.setContentsMargins(12, 1, 0, 1)                                                 # tight vertical padding, minimal right inset
        layout.setSpacing(4)                                                                  # no gap between label and close column
        text_label = QLabel(label)                                                            # displays the panel/dataset name
        text_label.setObjectName("panelTabLabel")                                             # names label for [QSS] targeting
        text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)  # label takes all available width
        layout.addWidget(text_label, 4)                                                       # adds label with stretch factor 4

        close_column = QWidget()                                                            # fixed-width container that holds the close button
        close_column.setObjectName("panelTabCloseColumn")                                   # names widget for [QSS] targeting
        close_column.setFixedWidth(18)                                                      # reserves only the width needed by the close button
        close_column.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)  # prevents close column from expanding

        close_layout = QHBoxLayout(close_column)                                            # horizontal layout hosts the close button
        close_layout.setContentsMargins(2, 0, 0, 4)                                         # no padding inside close column | left , top, right, bottom |
        close_layout.setSpacing(0)                                                          # no gap around close button

        close_button = QPushButton()                                                               # the close tab button
        close_button.setObjectName("panelTabCloseButton")                                          # names button for [QSS] targeting
        close_button.setFlat(True)                                                                 # removes button border/background for a minimal look
        close_button.setFixedSize(12, 12)                                                          # small square hit area
        close_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)             # prevents button from resizing
        close_button.setIcon(QIcon(str(_REMOVE_ICON_PATH)))                                        # uses remove icon from assets instead of plain text
        close_button.setIconSize(close_button.size())                                              # scales icon to the button bounds
        close_button.clicked.connect(
            lambda checked=False, target_panel=panel: self._remove_panel_for_widget(target_panel)  # closes this specific panel on click
        )

        close_layout.addWidget(close_button)                                                               # places close button directly in the close column
        layout.addWidget(close_column, 1)                                                                  # adds close column with stretch factor 1
        layout.setStretch(0, 4)                                                                            # enforces 4:1 ratio — label gets most space
        layout.setStretch(1, 1)                                                                            # close column gets remaining space

        return header

    def _refresh_tab_header_states(self, current_index: int | None = None) -> None:
        if current_index is None:
            current_index = self._panel_tabs.currentIndex()  # reads active tab index when not provided by signal
        tab_bar = self._panel_tabs.tabBar()  # accesses the underlying tab bar widget
        for index in range(self._panel_tabs.count()):  # iterates every tab
            is_selected = index == current_index  # true only for the active tab
            header = tab_bar.tabButton(index, QTabBar.ButtonPosition.LeftSide)  # retrieves custom header widget
            if header is None:
                continue  # skips tabs whose headers haven't been installed yet
            self._set_tab_header_selected_state(header=header, is_selected=is_selected)  # applies selected/unselected style

    def _set_tab_header_selected_state(self, header: QWidget, is_selected: bool) -> None:
        selected_value = "true" if is_selected else "false"  # converts bool to QSS-compatible string property
        header.setProperty("selected", selected_value)  # sets property on header for QSS dynamic styling
        label = header.findChild(QLabel, "panelTabLabel")  # finds the text label inside the header
        if label is not None:
            label.setProperty("selected", selected_value)  # sets same property on label for independent QSS rules
            label.style().unpolish(label)  # forces Qt to discard cached style for label
            label.style().polish(label)  # reapplies QSS so dynamic property change takes effect
        header.style().unpolish(header)  # forces Qt to discard cached style for header
        header.style().polish(header)  # reapplies QSS so dynamic property change takes effect

    def _remove_panel_for_widget(self, panel: PanelWidget) -> None:
        index = self._panel_tabs.indexOf(panel)  # looks up tab index by widget reference
        if index < 0:
            return  # panel not found — nothing to remove
        self._remove_panel(index)  # delegates to index-based removal

    def _remove_panel(self, index: int) -> None:
        widget = self._panel_tabs.widget(index)  # saves widget reference before removing the tab
        self._panel_tabs.removeTab(index)  # removes the tab from the tab bar
        self._refresh_tab_header_states()  # updates selected state after tab count changes
        if widget is not None:
            widget.deleteLater()  # schedules widget destruction after current event loop iteration
