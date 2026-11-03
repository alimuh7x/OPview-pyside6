"""Sidebar hover help must remain opaque and readable under native theme changes."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent, QPoint
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QToolTip

from app.styles import build_app_stylesheet
from sidebar.sidebar_widget import SidebarWidget


class TooltipReadabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_add_panel_dataset_hover_is_opaque_and_readable_in_light_and_dark_palettes(self):
        previous_palette, previous_stylesheet = self.app.palette(), self.app.styleSheet()
        self.addCleanup(lambda: self.app.setPalette(previous_palette))
        self.addCleanup(lambda: self.app.setStyleSheet(previous_stylesheet))
        for dark in (False, True):
            with self.subTest(dark=dark):
                palette = QPalette(previous_palette)
                palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#111827" if dark else "#ffffff"))
                palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#f8fafc" if dark else "#102a52"))
                self.app.setPalette(palette)
                self.app.setStyleSheet(build_app_stylesheet())
                sidebar = SidebarWidget()
                sidebar.show()
                self.app.processEvents()
                text = sidebar._dataset_tooltip({
                    "label": "OpenPhase", "available_projects": [{"project_name": "Project1", "file_count": 42, "files": []}],
                })
                QToolTip.showText(QPoint(20, 20), text, sidebar.dataset_list.viewport())
                self.app.processEvents()
                tooltip = next(widget for widget in self.app.topLevelWidgets()
                               if widget.objectName() == "qtooltip_label")
                try:
                    background = tooltip.palette().color(tooltip.backgroundRole())
                    foreground = tooltip.palette().color(tooltip.foregroundRole())
                    self.assertEqual(background.alpha(), 255, "Hover help must not inherit the transparent sidebar background")
                    self.assertGreater(background.lightness(), 240)
                    self.assertLess(foreground.lightness(), 100)
                    self.assertIn("OpenPhase", tooltip.text())
                    self.assertIn("42 files", tooltip.text())
                finally:
                    tooltip.hide()
                    QToolTip.hideText()
                    sidebar.close()
                    sidebar.deleteLater()
                    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


if __name__ == "__main__":
    unittest.main()
