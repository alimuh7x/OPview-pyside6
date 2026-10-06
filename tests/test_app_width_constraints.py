import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import plotly.graph_objects as go
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QApplication, QStyle, QStyleOptionViewItem

from app.main_window import MainWindow
from multi_view.multi_view_panel import MultiViewPanel
from viewer.heatmap_canvas import HeatmapCanvas
from viewer.heatmap_controller import HeatmapController
from viewer.panel_controls_widget import PanelControlsWidget
from viewer.panel_widget import PanelWidget
from viewer.phase_fraction_history_canvas import PhaseFractionHistoryCanvas
from viewer.time_plot_canvas import TimePlotCanvas


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

    def test_panel_controls_range_spins_preserve_tiny_values(self):
        controls = PanelControlsWidget({"label": "PhaseField"})

        controls.set_range_values(1e-7, 2e-7)

        minimum, maximum = controls.current_range()
        self.assertEqual(minimum, 1e-7)
        self.assertEqual(maximum, 2e-7)

    def test_panel_controls_use_rotation_icon_buttons(self):
        controls = PanelControlsWidget({"label": "PhaseField"})

        self.assertFalse(hasattr(controls, "rotation_combo"))
        self.assertEqual(sorted(controls.rotation_buttons), [0, 90, 180, 270])

        controls.rotation_buttons[90].click()

        self.assertEqual(controls.current_rotation_degrees(), 270)
        self.assertTrue(controls.rotation_buttons[90].isChecked())

    def test_multi_view_uses_rotation_icon_buttons(self):
        panel = MultiViewPanel({"label": "PhaseField", "available_projects": []})

        self.assertFalse(hasattr(panel, "rotation_combo"))
        self.assertEqual(sorted(panel.rotation_buttons), [0, 90, 180, 270])

        panel.rotation_buttons[90].click()

        self.assertEqual(panel._rotation_degrees, 270)
        self.assertTrue(panel.rotation_buttons[90].isChecked())

    def test_panel_widget_uses_line_direction_icon_buttons(self):
        panel = PanelWidget({"label": "PhaseField", "files": []})

        self.assertFalse(hasattr(panel, "direction_combo"))
        self.assertEqual(sorted(panel.line_direction_buttons), ["horizontal", "vertical"])

        panel.line_direction_buttons["vertical"].click()

        self.assertEqual(panel.current_line_scan_direction(), "vertical")
        self.assertTrue(panel.line_direction_buttons["vertical"].isChecked())

    def test_multi_view_uses_line_direction_icon_buttons(self):
        panel = MultiViewPanel({"label": "PhaseField", "available_projects": []})

        self.assertFalse(hasattr(panel, "direction_combo"))
        self.assertEqual(sorted(panel.line_direction_buttons), ["horizontal", "vertical"])

        panel.line_direction_buttons["vertical"].click()

        self.assertEqual(panel._current_line_scan_direction(), "vertical")
        self.assertTrue(panel.line_direction_buttons["vertical"].isChecked())

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

    def test_phase_fraction_rename_icon_uses_hover_text_color(self):
        controls = PanelControlsWidget({"label": "PhaseField"})
        delegate = controls.scalar_combo.itemDelegate()
        option = QStyleOptionViewItem()
        option.state = QStyle.StateFlag.State_MouseOver

        self.assertEqual(
            delegate._rename_icon_color(option),
            option.palette.highlightedText().color(),
        )

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

    def test_phase_fraction_history_legend_is_on_top_with_taller_graph(self):
        canvas = PhaseFractionHistoryCanvas.__new__(PhaseFractionHistoryCanvas)
        canvas._canvas_width = 800

        figure = canvas._build_figure(
            [
                {
                    "label": "PhaseFraction_0",
                    "steps": [0, 1],
                    "values": [20.0, 30.0],
                    "color": "#d62728",
                }
            ],
            current_step=1,
        )

        self.assertEqual(figure.layout.height, 400)
        self.assertEqual(figure.layout.legend.orientation, "h")
        self.assertEqual(figure.layout.legend.yanchor, "bottom")
        self.assertEqual(figure.layout.legend.xanchor, "right")
        self.assertEqual(figure.layout.legend.x, 1.0)
        self.assertEqual(figure.layout.legend.entrywidthmode, "fraction")
        self.assertAlmostEqual(figure.layout.legend.entrywidth, 0.33)
        self.assertGreaterEqual(figure.layout.legend.y, 1.02)
        self.assertGreaterEqual(figure.layout.margin.t, 108)

    def test_phase_fraction_history_modebar_stays_visible_at_top(self):
        canvas = PhaseFractionHistoryCanvas.__new__(PhaseFractionHistoryCanvas)
        html = canvas._build_html(go.Figure())

        self.assertIn(".modebar", html)
        self.assertIn("top: 0px !important", html)

    def test_line_scan_and_histogram_modebars_stay_visible_at_top(self):
        from viewer.histogram_canvas import HistogramCanvas
        from viewer.line_scan_canvas import LineScanCanvas

        line_canvas = LineScanCanvas.__new__(LineScanCanvas)
        histogram_canvas = HistogramCanvas.__new__(HistogramCanvas)

        self.assertIn("top: 0px !important", line_canvas._build_html(go.Figure()))
        self.assertIn("top: 0px !important", histogram_canvas._build_html(go.Figure()))

    def test_line_scan_and_histogram_reserve_top_space_for_modebar(self):
        from viewer.histogram_canvas import HistogramCanvas
        from viewer.line_scan_canvas import LineScanCanvas

        line_canvas = LineScanCanvas.__new__(LineScanCanvas)
        line_canvas._canvas_width = 800
        line_canvas._canvas_height = 360
        line_canvas._web_view = None
        histogram_canvas = HistogramCanvas.__new__(HistogramCanvas)
        histogram_canvas._canvas_width = 800
        histogram_canvas._canvas_height = 360
        histogram_canvas._web_view = None

        line_figure = line_canvas._figure_for_lines(
            [{"name": "5000", "x": [0.0, 1.0], "y": [2.0, 3.0]}],
            title="Line Scan",
            x_label="X Position",
            y_label="PhaseFields",
        )
        histogram_figure = histogram_canvas._figure_for_histograms(
            [{"name": "5000", "values": [1.0, 2.0, 3.0]}],
            label="PhaseFields",
            bins=10,
        )

        self.assertGreaterEqual(line_figure.layout.margin.t, 70)
        self.assertGreaterEqual(histogram_figure.layout.margin.t, 70)

    def test_line_scan_legend_is_outside_right_side(self):
        from viewer.line_scan_canvas import LineScanCanvas

        canvas = LineScanCanvas.__new__(LineScanCanvas)
        canvas._canvas_width = 800
        canvas._canvas_height = 360
        canvas._web_view = None

        figure = canvas._figure_for_lines(
            [
                {"name": "Stresses[0]", "x": [0.0, 1.0], "y": [2.0, 3.0]},
                {"name": "Stresses[1]", "x": [0.0, 1.0], "y": [4.0, 5.0]},
            ],
            title="Line Scan",
            x_label="X Position",
            y_label="Value",
        )

        self.assertEqual(figure.layout.legend.orientation, "v")
        self.assertGreater(figure.layout.legend.x, 1.0)
        self.assertEqual(figure.layout.legend.y, 1.0)
        self.assertEqual(figure.layout.legend.yanchor, "top")
        self.assertGreaterEqual(figure.layout.margin.r, 180)

    def test_time_plot_modebar_stays_visible_at_top(self):
        canvas = TimePlotCanvas.__new__(TimePlotCanvas)

        self.assertIn("top: 0px !important", canvas._build_html(go.Figure()))

    def test_time_plot_reserves_top_space_for_modebar(self):
        canvas = TimePlotCanvas.__new__(TimePlotCanvas)
        canvas._canvas_width = 800

        figure = canvas._build_time_plot_figure(
            [{"label": "P1", "steps": [0.0, 1.0], "values": [2.0, 3.0]}],
            y_label="PhaseFields",
        )

        self.assertGreaterEqual(figure.layout.margin.t, 70)

    def test_phase_fraction_history_canvas_can_use_wider_panel_space(self):
        canvas = PhaseFractionHistoryCanvas()

        canvas.set_available_width(900)

        self.assertEqual(canvas._canvas_width, 680)

    def test_phase_fraction_history_uses_supplied_time_axis_label(self):
        canvas = PhaseFractionHistoryCanvas.__new__(PhaseFractionHistoryCanvas)
        canvas._canvas_width = 800

        figure = canvas._build_figure(
            [
                {
                    "label": "PhaseFraction_0",
                    "steps": [0.0, 2.5],
                    "values": [20.0, 30.0],
                    "color": "#d62728",
                }
            ],
            current_step=2.5,
            x_label="Time [min]",
            hover_x_label="time",
        )

        self.assertEqual(figure.layout.xaxis.title.text, "Time [min]")
        self.assertEqual(list(figure.data[0].x), [0.0, 2.5])

    def test_phase_fraction_history_defaults_to_timestep_axis(self):
        canvas = PhaseFractionHistoryCanvas.__new__(PhaseFractionHistoryCanvas)
        canvas._canvas_width = 800

        figure = canvas._build_figure(
            [
                {
                    "label": "PhaseFraction_0",
                    "steps": [0.0, 1.0],
                    "values": [20.0, 30.0],
                    "color": "#d62728",
                }
            ],
            current_step=1.0,
        )

        self.assertEqual(figure.layout.xaxis.title.text, "Timestep")
        self.assertIn("timestep=", figure.data[0].hovertemplate)
        self.assertEqual(tuple(figure.layout.yaxis.range), (0, 100))

    def test_scalar_average_history_uses_auto_y_axis_range(self):
        canvas = PhaseFractionHistoryCanvas.__new__(PhaseFractionHistoryCanvas)
        canvas._canvas_width = 800

        figure = canvas._build_figure(
            [
                {
                    "label": "CRSS 0",
                    "steps": [0.0, 1.0],
                    "values": [125.0, 175.0],
                    "color": "#c50623",
                }
            ],
            current_step=1.0,
            y_label="Average CRSS 0 (MPa)",
            hover_value_label="average",
        )

        self.assertEqual(figure.layout.yaxis.title.text, "Average CRSS 0 (MPa)")
        self.assertIsNone(figure.layout.yaxis.range)

    def test_plot_over_time_uses_supplied_time_axis_label(self):
        canvas = TimePlotCanvas.__new__(TimePlotCanvas)
        canvas._canvas_width = 600

        figure = canvas._build_time_plot_figure(
            [{"label": "P1", "steps": [0.0, 2.5], "values": [1.0, 3.0]}],
            y_label="Temperature",
            x_label="Time [min]",
            hover_x_label="time",
        )

        self.assertEqual(figure.layout.xaxis.title.text, "Time [min]")
        self.assertEqual(list(figure.data[0].x), [0.0, 2.5])
        self.assertNotIn("step=", figure.data[0].hovertemplate)

    def test_single_view_toolbar_balances_label_and_dropdown_widths(self):
        panel = PanelWidget({"label": "PhaseField", "files": []})

        self.assertGreaterEqual(panel.phase_history_dt_spin.width(), 120)
        self.assertGreaterEqual(panel.colorbar_label_edit.minimumWidth(), 300)
        self.assertGreaterEqual(panel.phase_history_time_unit_combo.width(), 120)
        self.assertLessEqual(panel.unit_scale_combo.width(), 86)

    def test_panel_widget_keeps_analysis_toolbar_compact(self):
        panel = PanelWidget({"label": "PhaseField", "files": []})

        panel.resize(900, 1000)
        panel.show()
        QApplication.processEvents()

        self.assertLessEqual(panel.line_toolbar.height(), 32)
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
