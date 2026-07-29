import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import plotly.graph_objects as go
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from multi_view.multi_view_panel import MultiViewPanel
from viewer.heatmap_canvas import HeatmapCanvas
from viewer.heatmap_controller import HeatmapController
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

    def test_panel_controls_marks_phase_fraction_scalars_checkable(self):
        controls = PanelControlsWidget({"label": "PhaseField"})

        controls.set_scalar_options(
            [
                {"label": "PhaseFields", "value": "PhaseFields", "array": "PhaseFields"},
                {"label": "PhaseFraction_0", "value": "PhaseFraction_0", "array": "PhaseFraction_0"},
                {"label": "PhaseFraction_1", "value": "PhaseFraction_1", "array": "PhaseFraction_1"},
            ]
        )

        phase_index = controls.scalar_combo.findData("PhaseFraction_0")

        self.assertEqual(
            controls.scalar_combo.itemData(phase_index, Qt.ItemDataRole.CheckStateRole),
            Qt.CheckState.Checked,
        )
        self.assertEqual(
            controls.selected_phase_fraction_keys(),
            ["PhaseFraction_0", "PhaseFraction_1"],
        )

    def test_panel_controls_renames_phase_fraction_display_only(self):
        controls = PanelControlsWidget({"label": "PhaseField"})
        controls.set_scalar_options(
            [
                {"label": "PhaseFraction_0", "value": "PhaseFraction_0", "array": "PhaseFraction_0"},
            ]
        )

        controls.rename_phase_fraction("PhaseFraction_0", "Austenite")
        phase_index = controls.scalar_combo.findData("PhaseFraction_0")

        self.assertEqual(controls.scalar_combo.itemText(phase_index), "Austenite")
        self.assertEqual(controls.scalar_combo.itemData(phase_index), "PhaseFraction_0")
        self.assertEqual(
            controls.phase_fraction_display_label("PhaseFraction_0"),
            "Austenite",
        )

    def test_panel_controls_current_scalar_label_excludes_phase_rename_icon(self):
        controls = PanelControlsWidget({"label": "PhaseField"})
        controls.set_scalar_options(
            [
                {"label": "PhaseFraction_0", "value": "PhaseFraction_0", "array": "PhaseFraction_0"},
            ]
        )

        controls.rename_phase_fraction("PhaseFraction_0", "Austenite")

        self.assertEqual(controls.current_scalar_label(), "Austenite")

    def test_panel_controls_rename_hit_zone_only_uses_far_right_icon_slot(self):
        controls = PanelControlsWidget({"label": "PhaseField"})
        controls.set_scalar_options(
            [
                {"label": "PhaseFraction_0", "value": "PhaseFraction_0", "array": "PhaseFraction_0"},
            ]
        )
        phase_index = controls.scalar_combo.findData("PhaseFraction_0")
        near_text_role = controls.phase_fraction_click_role(
            phase_index,
            120,
            200,
        )
        icon_role = controls.phase_fraction_click_role(
            phase_index,
            184,
            200,
        )

        self.assertEqual(near_text_role, "select")
        self.assertEqual(icon_role, "rename")

    def test_panel_controls_scalar_combo_uses_phase_fraction_rename_delegate(self):
        controls = PanelControlsWidget({"label": "PhaseField"})

        self.assertIs(controls.scalar_combo.itemDelegate()._controls, controls)

    def test_phase_fraction_rename_dialog_uses_readable_light_style(self):
        controls = PanelControlsWidget({"label": "PhaseField"})

        dialog = controls._build_phase_fraction_rename_dialog("PhaseFraction_0", "PhaseFraction_0")
        stylesheet = dialog.styleSheet()

        self.assertIn("QInputDialog#phaseRenameDialog", stylesheet)
        self.assertIn("background: #f7f9fc", stylesheet)
        self.assertIn("color: #102a52", stylesheet)

    def test_phase_fraction_traces_use_legend_without_colorbar(self):
        canvas = HeatmapCanvas.__new__(HeatmapCanvas)
        figure = go.Figure()

        canvas._add_phase_fraction_traces(
            figure,
            [
                {
                    "label": "PhaseFraction_0",
                    "x": np.array([[0.0, 1.0], [0.0, 1.0]]),
                    "y": np.array([[0.0, 0.0], [1.0, 1.0]]),
                    "z": np.array([[0.0, 0.7], [0.8, 0.0]]),
                    "range": (0.5, 1.0),
                    "color": "#d62728",
                }
            ],
        )

        trace = figure.data[0]

        self.assertEqual(trace.name, "PhaseFraction_0")
        self.assertTrue(trace.showlegend)
        self.assertFalse(trace.showscale)

    def test_phase_fraction_animation_specs_match_selected_threshold_settings(self):
        class ControlsStub:
            def current_plot_type(self):
                return "threshold"

            def is_phase_fraction_key(self, key):
                return key.startswith("PhaseFraction_")

            def selected_phase_fraction_keys(self):
                return ["PhaseFraction_0", "PhaseFraction_3"]

            def phase_fraction_display_label(self, key, fallback=None):
                return {"PhaseFraction_0": "Alpha", "PhaseFraction_3": "Delta"}.get(key, fallback or key)

        controller = HeatmapController.__new__(HeatmapController)
        controller.controls_widget = ControlsStub()
        controller.state = SimpleNamespace(scalar_key="PhaseFraction_0", range_min=0.0, range_max=1.0)
        controller.scalar_defs = [
            {"label": "PhaseFraction_0", "value": "PhaseFraction_0", "array": "PhaseFraction_0"},
            {"label": "PhaseFraction_3", "value": "PhaseFraction_3", "array": "PhaseFraction_3"},
        ]
        controller._phase_fraction_ranges = {
            "PhaseFraction_0": (0.4, 1.0),
            "PhaseFraction_3": (0.2, 0.7),
        }

        specs = controller.phase_fraction_animation_specs()

        self.assertEqual([spec["label"] for spec in specs], ["Alpha", "Delta"])
        self.assertEqual([spec["range"] for spec in specs], [(0.4, 1.0), (0.2, 0.7)])
        self.assertEqual([spec["color"] for spec in specs], ["#d62728", "#1f77b4"])

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
