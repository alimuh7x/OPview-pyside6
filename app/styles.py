"""Application stylesheet helpers."""

from pathlib import Path

from app.debug import debug_print


def build_app_stylesheet() -> str:
    """Return a windows11-friendly stylesheet closer to OPView."""
    debug_print("build_app_stylesheet called")
    _assets = Path(__file__).parent.parent / "assets"
    _arrow     = str(_assets / "dropdown_icon_2.png").replace("\\", "/")
    _arrow_up  = str(_assets / "dropUp_icon_2.png").replace("\\", "/")
    _arrow_dn  = str(_assets / "dropdown_icon_2.png").replace("\\", "/")
    _checkbox_tick = str(_assets / "checkbox-tick.svg").replace("\\", "/")
    return f"""
QMainWindow, QWidget#appShell {{
    background: #e7ecf4;
}}
QWidget {{
    color: #102a52;
    font-family: 'Roboto Condensed', sans-serif;
    font-size: 15px;
}}
QLabel {{
    background: transparent;
}}
QAbstractItemView {{
    background: #ffffff;
    color: #102a52;
    selection-background-color: #e6edf7;
    selection-color: #102a52;
    border: 1px solid #ced8e8;
}}
QWidget#headerBar {{
    background: #0d2b55;
    border: none;
}}
QLabel#brandBadge {{
    min-width: 44px;
    min-height: 44px;
    max-width: 44px;
    max-height: 44px;
    border-radius: 10px;
    background: #ffffff;
    color: #c50623;
    font-size: 20px;
    font-weight: 800;
    qproperty-alignment: AlignCenter;
}}
QLabel#brandTitle {{
    color: #ffffff;
    font-size: 26px;
    font-weight: 800;
}}
QLabel#brandSubtitle {{
    color: #d5dfef;
    font-size: 14px;
}}
QPushButton#headerDocButton {{
    min-height: 32px;
    padding: 0 18px;
    border-radius: 18px;
}}
QPushButton#headerSidebarToggleButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    min-width: 34px;
    max-width: 34px;
    min-height: 34px;
    max-height: 34px;
    padding: 0px;
    margin: 0px 8px 0px 0px;
}}
QPushButton#headerSidebarToggleButton:hover {{
    background: rgba(255, 255, 255, 0.12);
    border-color: rgba(255, 255, 255, 0.18);
}}
QPushButton#headerSidebarToggleButton:pressed {{
    background: rgba(255, 255, 255, 0.18);
}}
QWidget#sidebarShell {{
    background: #0d2b55;
    border: none;
}}
QWidget#sidebarShell * {{
    background: transparent;
}}
QWidget#sidebarShell QLabel,
QWidget#sidebarShell QGroupBox {{
    color: #ffffff;
}}
QGroupBox#sidebarCard {{
    background: #0d2b55;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 14px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 800;
    letter-spacing: 2px;
    color: #d8e2f2;
}}
QGroupBox#sidebarCard::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #d8e2f2;
}}
QLabel#sidebarMuted {{
    color: #c9d5e7;
}}
QComboBox#sidebarCombo {{
    background: rgba(255, 255, 255, 0.08);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 10px;
    min-height: 34px;
    padding: 2px 12px;
}}
QComboBox#sidebarCombo::drop-down {{
    border: none;
    width: 28px;
    background: transparent;
}}
QComboBox#sidebarCombo QAbstractItemView {{
    background: #173763;
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.18);
}}
QLineEdit#sidebarLineEdit {{
    background: rgba(255, 255, 255, 0.08);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 10px;
    min-height: 34px;
    padding: 2px 12px;
}}
QLineEdit#sidebarLineEdit::placeholder {{
    color: #c9d5e7;
}}
QListWidget#projectList,
QListWidget#textFileList {{
    background: rgba(255, 255, 255, 0.06);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 10px;
    padding: 4px;
    outline: none;
}}
QListWidget#projectList::item,
QListWidget#textFileList::item {{
    padding: 5px 8px;
    border-radius: 6px;
}}
QListWidget#projectList::item:hover,
QListWidget#textFileList::item:hover {{
    background: rgba(255, 255, 255, 0.08);
}}
QListWidget#projectList::item:selected,
QListWidget#textFileList::item:selected {{
    background: rgba(255, 255, 255, 0.12);
    color: #ffffff;
}}
QWidget#contentShell {{
    background: #e7ecf4;
}}
QScrollArea#appContentScroll {{
    background: #e7ecf4;
    border: none;
}}
QScrollArea#appContentScroll > QWidget > QWidget {{
    background: #e7ecf4;
}}
QTabBar#mainTabs {{
    background: transparent;
}}
QTabBar#mainTabs::tab:last {{
    border-right: none;
}}
QTabBar#mainTabs::tab:hover {{
    color: #000000;
}}
QTabBar#mainTabs::tab {{
    background: #E5E5E5;
    color: #444444;
    padding: 7px 20px;
    margin: 0px 6px 0px 0px;
    border-radius: 2px 2px 0 0;
    font-weight: 700;
    font-size: 15px;
}}
QTabBar#mainTabs::tab:selected {{
    background: #FFFFFF;
    color: #cc0c24;
    border-bottom: 3px solid #cc0c24;
}}
QWidget#controlsCard,
QWidget#viewerCard,
QWidget#innerCard {{
    background: #ffffff;
    border: 1px solid #d7deea;
    border-radius: 16px;
}}
QWidget#toolbarStrip {{
    background: #f3f6fa;
    border-radius: 10px;
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
    font-size: 20px;
    font-weight: 800;
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
    color: #102a52;
    border: 1px solid #ccd7e8;
    border-radius: 10px;
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
    color: #173763;
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
    color: #102a52;
    border: 1px solid #ccd7e8;
    border-radius: 10px;
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
    background: #123764;
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 10px;
    padding: 6px 14px;
    font-weight: 700;
}}
QWidget#sidebarShell QPushButton[accent="true"] {{
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.16);
    color: #ffffff;
}}
QPushButton[subtle="true"] {{
    background: #ffffff;
    border: 1px solid #d2dbea;
    border-radius: 10px;
    padding: 6px 12px;
    font-weight: 700;
}}QSlider::groove:horizontal {{
    height: 6px;
    background: #d8dde6;
    border-radius: 3px;
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
    border-radius: 3px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid #ccd7e8;
    border-radius: 5px;
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
    border-radius: 8px;
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
    border-radius: 6px;
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
    border-radius: 4px;
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
    font-size: 16px;
    font-weight: 800;
}}
QGroupBox#graphSettingsSection {{
    background: #ffffff;
    border: 1px solid #d5deeb;
    border-radius: 8px;
    margin-top: 16px;
    color: #102a52;
    font-weight: 800;
    font-size: 16px;
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
    font-size: 16px;
    font-weight: 400;
}}
QGroupBox#graphSettingsSection QCheckBox::indicator,
QFrame#graphFileSection QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    background: #ffffff;
    border: 2px solid #ccd7e8;
    border-radius: 5px;
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
    border-radius: 5px;
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
    color: #001f4d;
    border: 1px solid #ccd7e8;
    border-radius: 7px;
    padding: 2px 10px;
    font-size: 16px;
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
    color: #102a52;
    border: 1px solid #ccd7e8;
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
    border-radius: 8px;
    padding: 0px;
    margin: 0px;
    font-size: 14px;
    font-weight: 800;
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
    background: #0d2b55;
    color: #ffffff;
    font-size: 15px;
    padding: 2px 4px;
}}
QMenuBar::item {{
    padding: 4px 10px;
    background: transparent;
}}
QMenuBar::item:selected {{
    background: #1a3f70;
    border-radius: 4px;
}}
QMenu {{
    background: #ffffff;
    color: #102a52;
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
QProgressBar {{
    background: #e7ecf4;
    border: none;
    border-radius: 3px;
}}
QProgressBar::chunk {{
    background: #cc0c24;
    border-radius: 3px;
}}
"""
