"""Main application window."""

from PySide6.QtWidgets import (
    QPushButton,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QTabBar,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from app.debug import debug_print
from sidebar.sidebar_widget import SidebarWidget
from single_view.tab_widget import SingleViewTab
from utils.project_scanner import scan_project_folders


class MainWindow(QMainWindow):
    """Top-level window that coordinates the sidebar and content tabs."""

    def __init__(self) -> None:
        debug_print("MainWindow.__init__ start")
        super().__init__()
        self.sidebar_widget: SidebarWidget | None = None
        self.single_view_tab: SingleViewTab | None = None
        self.content_tabs: dict[str, QWidget] = {}
        self._build_window()
        self._connect_signals()
        self._load_initial_projects()
        debug_print("MainWindow.__init__ complete")

    def _build_window(self) -> None:
        debug_print("MainWindow._build_window called")
        self.setWindowTitle("OPview PySide6")
        self.resize(1400, 900)
        tabs = QTabBar()
        self.tab_widget = tabs
        debug_print("MainWindow created top-level tab bar")
        tabs.setObjectName("mainTabs")
        debug_print("MainWindow assigned object name to main tab bar")
        tabs.setDrawBase(False)
        debug_print("MainWindow disabled tab bar base drawing")
        tabs.setExpanding(False)
        debug_print("MainWindow disabled tab expansion")
        tabs.setDocumentMode(True)
        debug_print("MainWindow enabled document mode for main tab bar")
        tabs.addTab("Single View")
        debug_print("MainWindow added Single View tab")
        tabs.addTab("Multi View")
        debug_print("MainWindow added Multi View tab")
        tabs.addTab("Custom Graph")
        debug_print("MainWindow added Custom Graph tab")
        tabs.setCurrentIndex(0)
        debug_print("MainWindow set main tab bar index to 0")
        central_widget = QWidget()
        central_widget.setObjectName("appShell")
        central_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCentralWidget(central_widget)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addLayout(self._build_header())
        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        self.sidebar_widget = SidebarWidget()
        body_layout.addWidget(self.sidebar_widget, 0)
        content_area = QWidget()
        content_area.setObjectName("contentShell")
        content_area.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(14, 0, 14, 14)
        content_layout.setSpacing(10)
        self.single_view_tab = SingleViewTab()
        debug_print("MainWindow created SingleViewTab")
        placeholder_multi = QLabel("Multi View will be added later")
        debug_print("MainWindow created Multi View placeholder")
        placeholder_graph = QLabel("Custom Graph will be added later")
        debug_print("MainWindow created Custom Graph placeholder")
        self.content_stack = QStackedWidget()
        debug_print("MainWindow created content stack")
        self.content_stack.addWidget(self.single_view_tab)
        debug_print("MainWindow added SingleViewTab to content stack")
        self.content_stack.addWidget(placeholder_multi)
        debug_print("MainWindow added Multi View placeholder to content stack")
        self.content_stack.addWidget(placeholder_graph)
        debug_print("MainWindow added Custom Graph placeholder to content stack")
        self.content_stack.setCurrentIndex(0)
        debug_print("MainWindow set content stack index to 0")
        self.content_tabs = {
            "single_view": self.single_view_tab,
            "multi_view": placeholder_multi,
            "custom_graph": placeholder_graph,
        }
        content_layout.addWidget(self.content_stack, 1)
        body_layout.addWidget(content_area, 1)
        root_layout.addLayout(body_layout)
        debug_print("MainWindow widgets assembled")

    def _build_header(self) -> QHBoxLayout:
        debug_print("MainWindow._build_header called")
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_bar = QWidget()
        self.header_bar.setObjectName("headerBar")
        self.header_bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        header_bar_layout = QVBoxLayout(self.header_bar)
        header_bar_layout.setContentsMargins(18, 8, 18, 0)
        debug_print("MainWindow created header bar layout")
        header_bar_layout.setSpacing(0)
        debug_print("MainWindow set header bar layout spacing")
        brand_row = QWidget()
        brand_row_layout = QHBoxLayout(brand_row)
        brand_row_layout.setContentsMargins(0, 0, 0, 0)
        brand_row_layout.setSpacing(14)
        debug_print("MainWindow created brand row layout")
        logo_badge = QLabel("OP")
        logo_badge.setObjectName("brandBadge")
        title_label = QLabel("OPView")
        title_label.setObjectName("brandTitle")
        subtitle_label = QLabel("PySide6 desktop viewer")
        subtitle_label.setObjectName("brandSubtitle")
        brand_cluster = QWidget()
        brand_cluster_layout = QHBoxLayout(brand_cluster)
        brand_cluster_layout.setContentsMargins(0, 6, 0, 0)
        debug_print("MainWindow set brand cluster top offset")
        brand_cluster_layout.setSpacing(14)
        debug_print("MainWindow set brand cluster spacing")
        left_column = QVBoxLayout()
        left_column.setContentsMargins(0, 0, 0, 0)
        left_column.setSpacing(0)
        left_column.addWidget(title_label)
        left_column.addWidget(subtitle_label)
        debug_print("MainWindow built brand text column")
        brand_cluster_layout.addWidget(logo_badge)
        debug_print("MainWindow added logo badge to brand cluster")
        brand_cluster_layout.addLayout(left_column)
        debug_print("MainWindow added text column to brand cluster")
        brand_row_layout.addWidget(brand_cluster, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        debug_print("MainWindow added brand cluster to brand row")
        brand_row_layout.addStretch(1)
        debug_print("MainWindow added stretch after brand cluster")
        self.documentation_button = QPushButton("DOCUMENTATION")
        self.documentation_button.setProperty("accent", True)
        self.documentation_button.setObjectName("headerDocButton")
        brand_row_layout.addWidget(self.documentation_button)
        debug_print("MainWindow added documentation button to header")
        tabs_row_layout = QHBoxLayout()
        tabs_row_layout.setContentsMargins(280, 0, 0, 0)
        debug_print("MainWindow set main tab row margins")
        tabs_row_layout.setSpacing(0)
        debug_print("MainWindow set main tab row spacing")
        tabs_row_layout.addWidget(self.tab_widget, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        debug_print("MainWindow added main tab bar to header row")
        tabs_row_layout.addStretch(1)
        debug_print("MainWindow added trailing stretch to header tab row")
        header_bar_layout.setStretch(0, 0)
        debug_print("MainWindow set brand row stretch factor")
        header_bar_layout.setStretch(1, 0)
        debug_print("MainWindow set tab row stretch factor")
        header_bar_layout.addWidget(brand_row)
        debug_print("MainWindow added brand row to header bar")
        header_bar_layout.addLayout(tabs_row_layout)
        debug_print("MainWindow added tab row layout to header bar")
        header_layout.addWidget(self.header_bar)
        debug_print("MainWindow header created")
        return header_layout

    def _connect_signals(self) -> None:
        debug_print("MainWindow._connect_signals called")
        assert self.sidebar_widget is not None
        assert self.single_view_tab is not None
        self.sidebar_widget.add_panel_requested.connect(self.single_view_tab.add_panel)
        debug_print("Connected sidebar add_panel_requested to SingleViewTab.add_panel")
        self.sidebar_widget.projects_changed.connect(self.single_view_tab.set_projects)
        debug_print("Connected sidebar projects_changed to SingleViewTab.set_projects")
        self.tab_widget.currentChanged.connect(self.content_stack.setCurrentIndex)
        debug_print("Connected main tab bar currentChanged to content stack")

    def _load_initial_projects(self) -> None:
        debug_print("MainWindow._load_initial_projects called")
        assert self.sidebar_widget is not None
        self.sidebar_widget.set_projects(scan_project_folders())
        debug_print("MainWindow initial projects loaded")
