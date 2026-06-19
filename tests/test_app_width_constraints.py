import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from multi_view.multi_view_panel import MultiViewPanel
from viewer.panel_controls_widget import PanelControlsWidget
from viewer.panel_widget import PanelWidget


class AppWidthConstraintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_main_window_caps_active_view_to_scroll_viewport_width(self):
        window = MainWindow()
        window.resize(760, 620)
        window.show()
        QApplication.processEvents()

        viewport_width = window.content_scroll.viewport().width()

        self.assertLessEqual(window.content_stack.maximumWidth(), viewport_width)
        self.assertLessEqual(window.single_view_tab.maximumWidth(), viewport_width)

    def test_main_window_has_800_px_minimum_width(self):
        window = MainWindow()

        self.assertEqual(window.minimumWidth(), 800)

    def test_panel_controls_accept_app_width_cap(self):
        controls = PanelControlsWidget({"label": "PhaseField"})

        controls.set_available_width(520)

        self.assertLessEqual(controls.maximumWidth(), 520)
        self.assertLessEqual(controls.project_combo.maximumWidth(), 520)
        self.assertLessEqual(controls.file_combo.maximumWidth(), 520)
        self.assertLessEqual(controls.scalar_combo.maximumWidth(), 520)

    def test_panel_controls_wrap_range_row_at_narrow_width(self):
        controls = PanelControlsWidget({"label": "PhaseField"})

        controls.set_available_width(374)

        self.assertEqual(controls.layout_mode(), "compact")
        self.assertFalse(controls.range_values_row.isHidden())
        self.assertGreaterEqual(controls.range_min_spin.minimumWidth(), 120)
        self.assertGreaterEqual(controls.range_max_spin.minimumWidth(), 120)
        self.assertLessEqual(controls.range_row_layout.minimumSize().width(), 374)
        self.assertLessEqual(controls.range_values_row_layout.minimumSize().width(), 346)

    def test_panel_controls_use_single_range_row_at_wide_width(self):
        controls = PanelControlsWidget({"label": "PhaseField"})

        controls.set_available_width(900)

        self.assertEqual(controls.layout_mode(), "wide")
        self.assertTrue(controls.range_values_row.isHidden())

    def test_panel_widget_keeps_analysis_toolbar_compact(self):
        panel = PanelWidget({"label": "PhaseField", "files": []})

        panel.resize(900, 1000)
        panel.show()
        QApplication.processEvents()

        self.assertLessEqual(panel.line_toolbar.height(), 44)
        self.assertEqual(panel.line_card.layout().stretch(1), 0)

    def test_panel_widget_keeps_heatmap_logo_visible_when_narrow(self):
        panel = PanelWidget({"label": "PhaseField", "files": []})

        panel.set_available_width(374)
        panel.resize(374, 1000)
        panel.show()
        QApplication.processEvents()

        logo_widget = panel.heatmap_row._logo_widget
        self.assertGreaterEqual(logo_widget.x(), 0)
        self.assertIsNotNone(panel.logo_label.pixmap())
        self.assertFalse(panel.logo_label.pixmap().isNull())

    def test_panel_widget_exports_full_heatmap_row_with_logo(self):
        panel = PanelWidget({"label": "PhaseField", "files": []})

        self.assertIs(panel.controller.export_widget, panel.heatmap_row)

    def test_multiview_panel_area_does_not_force_more_than_available_width(self):
        panel = MultiViewPanel({"label": "PhaseField", "available_projects": []})

        panel.set_available_width(560)

        self.assertLessEqual(panel.maximumWidth(), 560)
        self.assertLessEqual(panel._area.maximumWidth(), 560)
        self.assertLessEqual(panel._area.sizeHint().width(), 560)


if __name__ == "__main__":
    unittest.main()
