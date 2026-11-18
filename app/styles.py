"""Application stylesheet helpers."""

from pathlib import Path

from app.debug import debug_print
from app.theme import FONT_FAMILY, is_dark, themed


def build_app_stylesheet() -> str:
    """Return the application stylesheet in OPStudio's corporate design for the current mode.

    The colours below are written for the light mode; themed() maps each one to the OPStudio
    colour of its role in the current mode (see app/theme.py).
    """
    debug_print("build_app_stylesheet called")
    debug_print(f"build_app_stylesheet dark={is_dark()}")
    _assets = Path(__file__).parent.parent / "assets"
    _arrow     = str(_assets / "dropdown_icon_2.png").replace("\\", "/")
    _arrow_up  = str(_assets / "dropUp_icon_2.png").replace("\\", "/")
    _arrow_dn  = str(_assets / "dropdown_icon_2.png").replace("\\", "/")
    _checkbox_tick = str(_assets / "checkbox-tick.svg").replace("\\", "/")
    return themed(f"""
QMainWindow, QWidget#appShell {{
    background: #f3f3f3;
}}
QWidget {{
    color: #1c1c1c;
    font-family: '{FONT_FAMILY}', sans-serif;
    font-size: 13px;
}}
QLabel {{
    background: transparent;
}}
QAbstractItemView {{
    background: #ffffff;
    color: #1c1c1c;
    selection-background-color: #e6edf7;
    selection-color: #1c1c1c;
    border: 1px solid #ced8e8;
}}
QLabel#brandWordmark {{
    background: transparent;
    font-size: 20px;
    font-weight: 700;
    padding: 0px 14px 0px 8px;
    margin: 4px 6px 4px 10px;
    border-right: 1px solid #c7c7c7;
}}
QWidget#headerBar {{
    background: #f3f3f3;
    border: none;
}}
QPushButton#headerDocButton {{
    background: #f3f3f3;
    color: #082b63;
    border: 2px solid #082b63;
    min-height: 28px;
    padding: 0 18px;
    border-radius: 0px;
    font-weight: 600;
}}
QPushButton#headerDocButton:hover {{
    background: #ffffff;
}}
QPushButton#headerDocButton:pressed {{
    background: #f3f3f3;
    padding-top: 1px;
}}
QPushButton#headerSidebarToggleButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 0px;
    min-width: 42px;
    max-width: 42px;
    min-height: 42px;
    max-height: 42px;
    padding: 0px;
    margin: 0px 8px 0px 0px;
}}
QPushButton#headerSidebarToggleButton:hover {{
    background: #ffffff;
    border-color: #c7c7c7;
}}
QPushButton#headerSidebarToggleButton:pressed {{
    background: #d8d8d8;
}}
QWidget#sidebarShell {{
    background: #f3f3f3;
    border: none;
    border-right: 1px solid #c7c7c7;
}}
QWidget#sidebarShell * {{
    background: transparent;
}}
QWidget#sidebarShell QLabel,
QWidget#sidebarShell QGroupBox {{
    color: #1c1c1c;
}}
QGroupBox#sidebarCard {{
    background: #ffffff;
    border: 1px solid #c7c7c7;
    border-radius: 0px;
    margin-top: 14px;
    padding-top: 12px;
    font-weight: 600;
    color: #082b63;
}}
QGroupBox#sidebarCard::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 6px;
    color: #082b63;
    background: #f3f3f3;
}}
QLabel#sidebarMuted {{
    color: #787878;
}}
QComboBox#sidebarCombo {{
    background: #ffffff;
    color: #1c1c1c;
    border: 1px solid #c7c7c7;
    border-radius: 0px;
    min-height: 30px;
    padding: 2px 10px;
}}
QComboBox#sidebarCombo::drop-down {{
    border: none;
    width: 28px;
    background: transparent;
}}
QComboBox#sidebarCombo QAbstractItemView {{
    background: #ffffff;
    color: #1c1c1c;
    border: 1px solid #c7c7c7;
    selection-background-color: #082b63;
    selection-color: #ffffff;
}}
QComboBox#sidebarCombo QAbstractItemView::item {{
    background: #ffffff;
    color: #1c1c1c;
}}
QComboBox#sidebarCombo QAbstractItemView::item:hover,
QComboBox#sidebarCombo QAbstractItemView::item:selected {{
    background: #082b63;
    color: #ffffff;
}}
QLineEdit#sidebarLineEdit {{
    background: #ffffff;
    color: #1c1c1c;
    border: 1px solid #c7c7c7;
    border-radius: 0px;
    min-height: 30px;
    padding: 2px 10px;
}}
QLineEdit#sidebarLineEdit::placeholder {{
    color: #787878;
}}
QListWidget#projectList,
QListWidget#datasetList,
QListWidget#textFileList {{
    background: #ffffff;
    color: #1c1c1c;
    border: 1px solid #c7c7c7;
    border-radius: 0px;
    padding: 2px;
    outline: none;
}}
QListWidget#projectList::item,
QListWidget#datasetList::item,
QListWidget#textFileList::item {{
    padding: 3px 6px;
    border-radius: 0px;
}}
QListWidget#projectList::item:hover,
QListWidget#datasetList::item:hover,
QListWidget#textFileList::item:hover {{
    background: #ececec;
}}
QListWidget#projectList::item:selected,
QListWidget#datasetList::item:selected,
QListWidget#textFileList::item:selected {{
    background: #082b63;
    color: #ffffff;
}}
QWidget#contentShell {{
    background: #f3f3f3;
}}
QScrollArea#appContentScroll {{
    background: #f3f3f3;
    border: none;
}}
QScrollArea#appContentScroll > QWidget > QWidget {{
    background: #f3f3f3;
}}
QTabBar#mainTabs {{
    background: transparent;
}}
QTabBar#mainTabs::tab:hover {{
    background: #ffffff;
}}
QTabBar#mainTabs::tab {{
    background: #f3f3f3;
    color: #959595;
    border: 1px solid #c7c7c7;
    padding: 6px 28px;
    margin: 0px 0px 0px 0px;
    min-width: 7em;
    border-radius: 0px;
    font-weight: 500;
    font-size: 13px;
}}
QTabBar#mainTabs::tab:selected {{
    background: #082b63;
    color: #ffffff;
    border-color: #082b63;
}}
QWidget#controlsCard,
QWidget#viewerCard,
QWidget#innerCard {{
    background: #ffffff;
    border: 1px solid #d7deea;
}}
QWidget#toolbarStrip {{
    background: #f3f6fa;
    border-radius: 0px;
}}
QFrame#phaseFractionHistorySeparator {{
    color: #d7deea;
    background: transparent;
    border: none;
    border-top: 1px solid #d7deea;
    margin-top: 8px;
    margin-bottom: 4px;
}}
QWidget#timePlotToolbar {{
    background: #f3f6fa;
    border: 1px solid #e0e7f1;
    border-radius: 0px;
}}
QWidget#timePlotActionRow,
QWidget#timePlotStatusRow,
QWidget#timePlotPointsContainer {{
    background: transparent;
}}
QPushButton#timePlotAddPointButton,
QPushButton#timePlotManualButton,
QPushButton#timePlotCancelButton,
QPushButton#timePlotClearButton {{
    background: #ffffff;
    border: 1px solid #d2dbea;
    border-radius: 0px;
    padding: 3px 10px;
    font-weight: 700;
}}
QPushButton#timePlotAddPointButton:hover,
QPushButton#timePlotManualButton:hover,
QPushButton#timePlotCancelButton:hover,
QPushButton#timePlotClearButton:hover {{
    background: #eaf0f8;
    border-color: #bfccde;
}}
QPushButton#timePlotAddPointButton:checked {{
    background: #cc0c24;
    color: #ffffff;
    border-color: #ad081d;
}}
QPushButton#timePlotCalculateButton {{
    background: #123764;
    color: #ffffff;
    border: 1px solid #123764;
    border-radius: 0px;
    padding: 3px 12px;
    font-weight: 700;
}}
QPushButton#timePlotCalculateButton:hover {{
    background: #1b4778;
    border-color: #1b4778;
}}
QPushButton#timePlotCalculateButton:disabled,
QPushButton#timePlotCancelButton:disabled {{
    background: #edf1f7;
    color: #8fa0b8;
    border-color: #d9e1ed;
}}
QWidget#timePlotPointRow {{
    background: #f8fafd;
    border: 1px solid #dfe7f2;
    border-radius: 0px;
}}
QLabel#timePlotPointLabel {{
    color: #17375e;
    font-size: 13px;
    font-weight: 700;
}}
QPushButton#timePlotRemovePointButton {{
    background: #ffffff;
    color: #6a7e9f;
    border: 1px solid #d8e0ec;
    border-radius: 0px;
    padding: 0px;
    font-weight: 700;
}}
QPushButton#timePlotRemovePointButton:hover {{
    background: #ffecef;
    color: #cc0c24;
    border-color: #f2b9c1;
}}
QPushButton#discreteBandButton {{
    background: #ffffff;
    color: #111827;
    border: 2px solid #8a96a8;
    border-radius: 0px;
    padding: 0px;
    font-size: 18px;
    font-weight: 700;
}}
QPushButton#discreteBandButton:hover {{
    background: #f3f6fa;
    border-color: #5f6b7a;
    color: #000000;
}}
QPushButton#discreteBandButton:pressed {{
    background: #d8dde6;
    border-color: #4b5563;
    color: #000000;
}}
QWidget#controlsRow {{
    background: transparent;
}}
QScrollArea#multiViewScroll {{
    background: #f7f9fc;
    border: none;
}}
QScrollArea#multiViewScroll > QWidget > QWidget {{
    background: #f7f9fc;
}}
QWidget#multiViewArea,
QWidget#multiViewHeatmapRow {{
    background: #f7f9fc;
}}
QLabel#sectionTitle {{
    color: #102a52;
    font-size: 14px;
    font-weight: 700;
}}
QLabel#mutedInfo {{
    color: #6a7e9f;
    font-size: 14px;
}}
QComboBox#viewerCombo,
QDoubleSpinBox#viewerSpin {{
    min-width: 72px;
    min-height: 28px;
    background: #ffffff;
    color: #1c1c1c;
    selection-background-color: #d8ecff;
    selection-color: #1c1c1c;
    border: 1px solid #ccd7e8;
    border-radius: 0px;
    padding: 2px 24px 2px 8px;
}}
QComboBox#viewerCombo::drop-down {{
    border: none;
    width: 22px;
    background: transparent;
    subcontrol-position: right center;
}}
QComboBox#viewerCombo::down-arrow {{
    image: url({_arrow});
    width: 10px;
    height: 7px;
}}
QComboBox#viewerCombo:disabled {{
    background: #f5f8fc;
    color: #4a648b;
}}
QComboBox#viewerCombo QAbstractItemView {{
    background: #ffffff;
    color: #1c1c1c;
    border: 1px solid rgba(255, 255, 255, 0.18);
}}
QComboBox#viewerCombo QAbstractItemView::item:hover {{
    background: #1e4a8a;
    color: #ffffff;
}}

QLineEdit#viewerLineEdit {{
    min-width: 72px;
    min-height: 28px;
    background: #ffffff;
    color: #1c1c1c;
    border: 1px solid #ccd7e8;
    border-radius: 0px;
    padding: 2px 8px;
    font-size: 13px;
}}
QLineEdit#viewerLineEdit:focus {{
    border-color: #8FAE00;
}}
QDoubleSpinBox#viewerSpin {{
    background: #ffffff;
    padding: 4px 6px 4px 8px;
}}
QDoubleSpinBox#viewerSpin[rangeSpin="true"] {{
    min-width: 120px;
}}

QDoubleSpinBox#viewerSpin::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 16px;
    height: 20px;
    border-left: 1px solid #ccd7e8;
    border-top-right-radius: 10px;
    background: #f5f8fc;
}}
QDoubleSpinBox#viewerSpin::up-button:hover {{
    background: #e6edf7;
}}
QDoubleSpinBox#viewerSpin::up-button:pressed {{
    background: #d0dff0;
}}
QDoubleSpinBox#viewerSpin::up-arrow {{
    image: url({_arrow_up});
    width: 10px;
    height: 7px;
}}
QDoubleSpinBox#viewerSpin::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 16px;
    height: 20px;
    border-left: 1px solid #ccd7e8;
    border-top: 1px solid #ccd7e8;
    border-bottom-right-radius: 10px;
    background: #f5f8fc;
}}
QDoubleSpinBox#viewerSpin::down-button:hover {{
    background: #e6edf7;
}}
QDoubleSpinBox#viewerSpin::down-button:pressed {{
    background: #d0dff0;
}}
QDoubleSpinBox#viewerSpin::down-arrow {{
    image: url({_arrow_dn});
    width: 10px;
    height: 7px;
}}
QPushButton[accent="true"] {{
    background: #082b63;
    color: #ffffff;
    border: 2px solid #082b63;
    border-radius: 0px;
    padding: 5px 14px;
    font-weight: 700;
}}
QPushButton[accent="true"]:hover {{
    background: #123978;
    border-color: #123978;
}}
QWidget#sidebarShell QPushButton[accent="true"] {{
    background: #f3f3f3;
    border: 2px solid #082b63;
    color: #082b63;
}}
QWidget#sidebarShell QPushButton[accent="true"]:hover {{
    background: #ffffff;
    border-color: #082b63;
}}
QWidget#sidebarShell QPushButton[accent="true"]:pressed {{
    background: #f3f3f3;
    border-color: #123978;
}}
QPushButton[subtle="true"] {{
    background: #ffffff;
    border: 1px solid #d2dbea;
    border-radius: 0px;
    padding: 6px 12px;
    font-weight: 700;
}}
QPushButton#rotationIconButton,
QPushButton#lineScanDirectionButton {{
    background: #ffffff;
    border: 1px solid #d2dbea;
    border-radius: 0px;
    padding: 0px;
}}
QPushButton#rotationIconButton:hover,
QPushButton#lineScanDirectionButton:hover {{
    background: #eef3f8;
    border-color: #bdcad9;
}}
QPushButton#rotationIconButton:checked,
QPushButton#rotationIconButton:pressed,
QPushButton#lineScanDirectionButton:checked,
QPushButton#lineScanDirectionButton:pressed {{
    background: #9aabbf;
    border-color: #8194aa;
}}
QPushButton#playbackTransportButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 0px;
    padding: 0px;
}}
QPushButton#playbackTransportButton:hover {{
    background: rgba(16, 42, 82, 0.08);
    border-color: rgba(16, 42, 82, 0.12);
}}
QPushButton#playbackTransportButton:pressed {{
    background: rgba(16, 42, 82, 0.14);
    border-color: rgba(16, 42, 82, 0.18);
}}
QPushButton#playbackTransportButton:disabled {{
    background: transparent;
    border-color: transparent;
}}
QSlider::groove:horizontal {{
    height: 6px;
    background: #d8dde6;
    border-radius: 0px;
}}
QSlider::handle:horizontal {{
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
    background: #ffffff;
    border: 2px solid #17375e;
}}
QSlider::sub-page:horizontal {{
    background: #17375e;
    border-radius: 0px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid #ccd7e8;
    border-radius: 0px;
    background: #ffffff;
}}
QCheckBox::indicator:checked {{
    background: #c50623;
    border-color: #c50623;
}}

QTabWidget#panelTabs,
QTabWidget#graphPanelTabs {{
    background: transparent;
}}
QTabWidget#panelTabs::pane,
QTabWidget#graphPanelTabs::pane {{
    border: none;
    background: transparent;
}}
QTabWidget#panelTabs QTabBar,
QTabWidget#graphPanelTabs QTabBar {{
    background: transparent;
}}

QTabWidget#panelTabs QTabBar::tab,
QTabWidget#graphPanelTabs QTabBar::tab {{
    background: #bccbdd;
    border: 4px solid #bccbdd;
    border-bottom: none;
    border-top: none;
    padding: 2px 0px 2px 0px;
    margin-right: 4px;
    color: #000000;
    font-weight: 700;
}}
QTabWidget#panelTabs QTabBar::tab:selected,
QTabWidget#graphPanelTabs QTabBar::tab:selected {{
    background: #0d2b55;
    border: 4px solid #0d2b55;
    border-bottom: none;
    border-top: none;
    margin-right: 4px;
    padding: 2px 0px 2px 0px;
    color: #ffffff;
    font-weight: 700;
}}
QWidget#customGraphPanel {{
    background: #ffffff;
    border: 1px solid #e5e5e5;
}}
QWidget#graphTopControls {{
    background: #f8fbff;
    border-bottom: 1px solid #e2e8f0;
}}
QGroupBox#graphDataSources {{
    background: #ffffff;
    border: 1px solid #e2e8f0;
    margin-top: 12px;
    padding-top: 12px;
    color: #102a52;
    font-weight: 600;
}}
QGroupBox#graphDataSources::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: #102a52;
    background: #f8fbff;
}}
QFrame#graphFileSection {{
    background: rgba(18, 43, 98, 0.02);
    border: 1px solid #e2e8f0;
}}
QFrame#graphFileSection QLabel {{
    color: #102a52;
    font-weight: 600;
}}
QFrame#graphFileSection QCheckBox {{
    color: #102a52;
    background: transparent;
}}
QFrame#graphFileSection QPushButton {{
    background: #ffffff;
    color: #102a52;
    border: 1px solid #ccd7e8;
    font-weight: 700;
}}
QWidget#graphMainContent {{
    background: #ffffff;
}}
QWidget#graphArea {{
    background: #ffffff;
}}
QWidget#customGraphCanvas {{
    background: #ffffff;
}}
QScrollArea#graphSettingsScroll {{
    background: #fbfdff;
    border-left: 1px solid #e2e8f0;
    border-top: none;
    border-right: none;
    border-bottom: none;
}}
QScrollArea#graphSettingsScroll > QWidget > QWidget,
QWidget#graphSettingsContent {{
    background: #fbfdff;
}}
QLabel#graphSettingsTitle {{
    color: #0d2b55;
    font-size: 14px;
    font-weight: 700;
}}
QPushButton#graphSettingsToggleButton,
QPushButton#graphSettingsCollapsedToggleButton {{
    background: transparent;
    border: none;
    padding: 0px;
}}
QPushButton#graphSettingsToggleButton:hover,
QPushButton#graphSettingsCollapsedToggleButton:hover {{
    background: transparent;
    border: none;
}}
QWidget#graphSettingsCollapsedLabel {{
    color: #0d2b55;
    font-size: 14px;
    font-weight: 700;
}}
QGroupBox#graphSettingsSection {{
    background: #ffffff;
    border: 1px solid #d5deeb;
    margin-top: 16px;
    color: #102a52;
    font-weight: 700;
    font-size: 14px;
}}
QGroupBox#graphSettingsSection::title {{
    subcontrol-origin: margin;
    left: 18px;
    padding: 0 7px;
    color: #102a52;
    background: #fbfdff;
}}
QGroupBox#graphSettingsSection QLabel,
QGroupBox#graphSettingsSection QRadioButton,
QGroupBox#graphSettingsSection QCheckBox {{
    color: #435a7c;
    background: transparent;
    font-size: 14px;
    font-weight: 400;
}}
QGroupBox#graphSettingsSection QCheckBox::indicator,
QFrame#graphFileSection QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    background: #ffffff;
    border: 2px solid #ccd7e8;
    border-radius: 0px;
}}
QGroupBox#graphSettingsSection QCheckBox::indicator:checked,
QFrame#graphFileSection QCheckBox::indicator:checked {{
    background: #ffffff;
    border: 2px solid #ccd7e8;
    image: url({_checkbox_tick});
}}
QGroupBox#graphSettingsSection QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    background: #ffffff;
    border: 2px solid #ccd7e8;
    border-radius: 0px;
}}
QGroupBox#graphSettingsSection QRadioButton::indicator:checked {{
    background: #ffffff;
    border: 2px solid #ccd7e8;
    image: url({_checkbox_tick});
}}
QComboBox#graphCombo,
QLineEdit#graphLineEdit {{
    min-height: 36px;
    background: #ffffff;
    color: #1c1c1c;
    border: 1px solid #ccd7e8;
    border-radius: 0px;
    padding: 2px 10px;
    font-size: 14px;
    font-weight: 400;
}}
QComboBox#graphCombo::drop-down {{
    border: none;
    width: 26px;
    background: transparent;
}}
QComboBox#graphCombo::down-arrow {{
    image: url({_arrow});
    width: 10px;
    height: 7px;
}}
QComboBox#graphCombo QAbstractItemView {{
    background: #ffffff;
    color: #1c1c1c;
    border: 1px solid #ccd7e8;
    selection-background-color: #1e4a8a;
    selection-color: #ffffff;
}}
QComboBox#graphCombo QAbstractItemView::item {{
    background: #ffffff;
    color: #1c1c1c;
    min-height: 28px;
    padding: 4px 8px;
}}
QComboBox#graphCombo QAbstractItemView {{
    outline: none;
}}
QComboBox#graphCombo QAbstractItemView::item:focus,
QComboBox#graphCombo QAbstractItemView::item:selected {{
    background: #e3ecf8;
    color: #1c1c1c;
    border: none;
}}
QComboBox#graphCombo QAbstractItemView::item:hover {{
    background: #1e4a8a;
    color: #ffffff;
}}
QComboBox#graphCombo QAbstractItemView QScrollBar:vertical {{
    background: #edf2f8;
    border-left: 1px solid #ccd7e8;
    margin: 0px;
    width: 13px;
}}
QComboBox#graphCombo QAbstractItemView QScrollBar::handle:vertical {{
    background: #6f89ad;
    border-radius: 0px;
    min-height: 24px;
    margin: 2px;
}}
QComboBox#graphCombo QAbstractItemView QScrollBar::handle:vertical:hover {{
    background: #526f98;
}}
QComboBox#graphCombo QAbstractItemView QScrollBar::add-line:vertical,
QComboBox#graphCombo QAbstractItemView QScrollBar::sub-line:vertical {{
    background: transparent;
    border: none;
    height: 0px;
}}
QComboBox#graphCombo QAbstractItemView QScrollBar::add-page:vertical,
QComboBox#graphCombo QAbstractItemView QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QWidget#panelTabHeader {{
    background: transparent;
}}
QLabel#panelTabLabel {{
    background: transparent;
    font-weight: 700;
}}
QLabel#panelTabLabel[selected="true"] {{
    color: #ffffff;
}}
QLabel#panelTabLabel[selected="false"] {{
    color: #102a52;
}}
QPushButton#panelTabCloseButton {{
    background: transparent;
    color: #c50623;
    border: 1px solid transparent;
    border-radius: 0px;
    padding: 0px;
    margin: 0px;
    font-size: 14px;
    font-weight: 700;
    min-width: 16px;
    min-height: 16px;
}}
QPushButton#panelTabCloseButton:hover {{
    background: rgba(197, 6, 35, 0.12);
    border-color: rgba(197, 6, 35, 0.22);
    color: #8f0016;
}}
QPushButton#panelTabCloseButton:pressed {{
    background: rgba(197, 6, 35, 0.18);
}}
QMenuBar {{
    background: #f3f3f3;
    color: #1c1c1c;
    font-size: 13px;
    font-weight: 700;
    padding: 2px 4px;
    border-bottom: 1px solid #c7c7c7;
}}
QMenuBar::item {{
    padding: 7px 10px;
    background: transparent;
}}
QMenuBar::item:selected {{
    background: #d8d8d8;
    border-radius: 0px;
}}
QMenu {{
    background: #ffffff;
    color: #1c1c1c;
    border: 1px solid #ced8e8;
    padding: 4px 0;
}}
QMenu::item {{
    padding: 6px 24px 6px 16px;
}}
QMenu::item:selected {{
    background: #e6edf7;
}}
QMenu::item:disabled {{
    color: #9aabbf;
}}
QMenu::separator {{
    height: 1px;
    background: #ced8e8;
    margin: 4px 8px;
}}
QProgressDialog {{
    background: #f7f9fc;
    color: #1c1c1c;
}}
QProgressDialog QLabel {{
    background: transparent;
    color: #1c1c1c;
}}
QProgressBar {{
    background: #e7ecf4;
    border: none;
    border-radius: 0px;
}}
QProgressBar::chunk {{
    background: #cc0c24;
    border-radius: 0px;
}}
""")
