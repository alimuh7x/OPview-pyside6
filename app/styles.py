"""Application stylesheet helpers."""

from pathlib import Path

from app.debug import debug_print


def build_app_stylesheet() -> str:
    """Return a windows11-friendly stylesheet closer to OPView."""
    debug_print("build_app_stylesheet called")
    _assets = Path(__file__).parent.parent / "assets"
    _arrow = str(_assets / "arrow-down.svg").replace("\\", "/")
    _remove = str(_assets / "remove.png").replace("\\", "/")
    _remove_hover = str(_assets / "remove_hover.png").replace("\\", "/")
    return f"""
QMainWindow, QWidget#appShell {{
    background: #e7ecf4;
}}
QWidget {{
    color: #102a52;
    font-size: 13px;
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
    font-size: 18px;
    font-weight: 800;
    qproperty-alignment: AlignCenter;
}}
QLabel#brandTitle {{
    color: #ffffff;
    font-size: 24px;
    font-weight: 800;
}}
QLabel#brandSubtitle {{
    color: #d5dfef;
    font-size: 12px;
}}
QPushButton#headerDocButton {{
    min-height: 32px;
    padding: 0 18px;
    border-radius: 18px;
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
QWidget#contentShell {{
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
    font-size: 13px;
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
QLabel#sectionTitle {{
    color: #102a52;
    font-size: 16px;
    font-weight: 800;
}}
QLabel#mutedInfo {{
    color: #6a7e9f;
    font-size: 12px;
}}
QComboBox#viewerCombo,
QDoubleSpinBox#viewerSpin {{
    min-height: 34px;
    background: #ffffff;
    color: #102a52;
    border: 1px solid #ccd7e8;
    border-radius: 10px;
    padding: 2px 36px 2px 12px;
}}
QComboBox#viewerCombo::drop-down {{
    border: none;
    width: 28px;
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
QDoubleSpinBox#viewerSpin {{
    background: #ffffff;
    padding: 4px 12px;
}}
QDoubleSpinBox#viewerSpin:up-button,
QDoubleSpinBox#viewerSpin:down-button {{
    width: 18px;
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
}}
QSlider::groove:horizontal {{
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
    background: #83d8dd;
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
QTabWidget#panelTabs::pane {{
    border: none;
    background: transparent;
}}
QTabWidget#panelTabs QTabBar::tab {{
    background: #e3ebf6;
    border: 1px solid #cdd8e9;
    border-radius: 8px;
    padding: 6px 34px 6px 16px;
    margin-right: 8px;
    font-weight: 600;
    color: #34547d;
}}
QTabWidget#panelTabs QTabBar::tab:selected {{
    background: #123764;
    border-color: #123764;
    color: #ffffff;
}}
QTabWidget#panelTabs QTabBar::tab:hover {{
    background: #d9e4f1;
    color: #163961;
}}
QTabWidget#panelTabs QTabBar::close-button {{
    subcontrol-origin: padding;
    subcontrol-position: right;
    right: 12px;
    width: 10px;
    height: 10px;
}}
QTabWidget#panelTabs QTabBar::close-button:hover {{
    right: 12px;
}}
QTabBar::close-button {{
    image: url({_remove});
    subcontrol-position: right;
}}
QTabBar::close-button:hover {{
    image: url({_remove_hover});
}}
"""
