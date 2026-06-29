import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QSizePolicy, QWidget

from app.application_bootstrap import ApplicationBootstrap
from app.main_window import MainWindow
from app.styles import build_app_stylesheet
from single_view.tab_widget import SingleViewTab
from viewer.histogram_canvas import HistogramCanvas
from viewer.panel_widget import PanelWidget


class SingleViewOOPShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_application_bootstrap_creates_main_window(self):
        bootstrap = ApplicationBootstrap()
        window = bootstrap.build_main_window()

        self.assertIsInstance(window, MainWindow)
        self.assertIs(window.single_view_tab, window.content_tabs["single_view"])

    def test_application_bootstrap_uses_windows11_style(self):
        bootstrap = ApplicationBootstrap()
        bootstrap.get_application()

        self.assertEqual(bootstrap._style_name, "windows11")

    def test_stylesheet_contains_underlined_tab_bar_rules(self):
        stylesheet = build_app_stylesheet()

        self.assertIn("QTabBar#mainTabs::tab {", stylesheet)
        self.assertIn("background: transparent;", stylesheet)
        self.assertIn("padding: 7px 20px;", stylesheet)
        self.assertIn("border-bottom: 3px solid #cc0c24;", stylesheet)

    def test_main_window_wires_sidebar_to_single_view(self):
        window = MainWindow()

        sample_project = {
            "DemoProject": {
                "path": "/tmp/DemoProject",
                "has_vtk": True,
                "vtk_path": "/tmp/DemoProject/VTK",
                "has_textdata": False,
                "textdata_path": None,
            }
        }

        window.sidebar_widget.set_projects(sample_project)
        window.sidebar_widget.dataset_combo.setCurrentIndex(1)
        window.sidebar_widget.add_panel_requested.emit(
            {
                "id": "demo-temperature",
                "label": "Temperature",
                "files": [],
                "tab_id": "single_view",
            }
        )

        self.assertEqual(window.single_view_tab.panel_count(), 1)

    def test_main_window_exposes_styled_shell_widgets(self):
        window = MainWindow()

        self.assertEqual(window.header_bar.objectName(), "headerBar")
        self.assertEqual(window.tab_widget.objectName(), "mainTabs")
        self.assertEqual(window.sidebar_widget.objectName(), "sidebarShell")
        self.assertEqual(window.documentation_button.property("accent"), True)
        self.assertIsNone(window.header_bar.findChild(QLabel, "brandLogo"))
        self.assertFalse(window.windowIcon().isNull())

    def test_main_tabs_live_inside_header_bar(self):
        window = MainWindow()

        self.assertIs(window.tab_widget.parentWidget(), window.header_bar)

    def test_header_sidebar_toggle_button_syncs_sidebar_and_menu(self):
        window = MainWindow()
        window.show()
        QApplication.processEvents()

        toggle_button = window.sidebar_toggle_button
        header_layout = window.header_bar.layout()

        self.assertIs(toggle_button.parentWidget(), window.header_bar)
        self.assertEqual(header_layout.indexOf(toggle_button), 0)
        self.assertLess(header_layout.indexOf(toggle_button), header_layout.indexOf(window.tab_widget))
        self.assertFalse(toggle_button.icon().isNull())
        self.assertTrue(window.sidebar_widget.isVisible())
        self.assertTrue(window.app_menu_bar.toggle_sidebar_action.isChecked())

        toggle_button.click()

        self.assertFalse(window.sidebar_widget.isVisible())
        self.assertFalse(window.app_menu_bar.toggle_sidebar_action.isChecked())
        self.assertFalse(toggle_button.icon().isNull())

        toggle_button.click()

        self.assertTrue(window.sidebar_widget.isVisible())
        self.assertTrue(window.app_menu_bar.toggle_sidebar_action.isChecked())

        window.app_menu_bar.toggle_sidebar_action.setChecked(False)

        self.assertFalse(window.sidebar_widget.isVisible())
        self.assertFalse(toggle_button.icon().isNull())

    def test_single_view_tab_creates_panel_widget(self):
        tab = SingleViewTab()

        panel = tab.add_panel(
            {
                "id": "demo-temperature",
                "label": "Temperature",
                "files": [],
                "tab_id": "single_view",
            }
        )

        self.assertEqual(tab.panel_count(), 1)
        self.assertIsInstance(panel, PanelWidget)

    def test_single_view_tab_and_panel_attach_to_upper_tabs(self):
        tab = SingleViewTab()
        panel = PanelWidget({"label": "PhaseField", "files": []})

        margins = panel.layout().contentsMargins()

        self.assertEqual(tab.layout().spacing(), 0)
        self.assertEqual(margins.left(), 0)
        self.assertEqual(margins.top(), 0)
        self.assertEqual(margins.right(), 8)
        self.assertEqual(margins.bottom(), 8)

    def test_panel_analysis_card_has_separate_line_scan_and_histogram_headings(self):
        panel = PanelWidget({"label": "PhaseField", "files": []})

        section_titles = [
            label.text()
            for label in panel.findChildren(QLabel, "sectionTitle")
        ]

        self.assertIn("Analysis", section_titles)
        self.assertIn("Line Scan", section_titles)
        self.assertIn("Histogram", section_titles)
        self.assertNotIn("Line Scan & Histogram Analysis", section_titles)

    def test_panel_show_line_defaults_off(self):
        panel = PanelWidget({"label": "PhaseField", "files": []})

        self.assertFalse(panel.show_line_check.isChecked())
        self.assertFalse(panel.controller.state.line_overlay_visible)

    def test_single_view_tab_uses_custom_tab_header_with_close_button(self):
        tab = SingleViewTab()
        tab.add_panel(
            {
                "id": "demo-temperature",
                "label": "Temperature",
                "files": [],
                "tab_id": "single_view",
            }
        )

        tab_bar = tab._panel_tabs.tabBar()
        tab_header = tab_bar.tabButton(0, tab_bar.ButtonPosition.LeftSide)

        self.assertFalse(tab._panel_tabs.tabsClosable())
        self.assertIsNotNone(tab_header)
        self.assertIsInstance(tab_header, QWidget)
        label = tab_header.findChild(QLabel, "panelTabLabel")
        close_button = tab_header.findChild(QPushButton, "panelTabCloseButton")
        self.assertIsNotNone(label)
        self.assertEqual(label.text(), "Temperature")
        self.assertIsNotNone(close_button)
        self.assertFalse(close_button.icon().isNull())

    def test_panel_widget_uses_controller_to_update_canvas_message(self):
        panel = PanelWidget(
            dataset_info={
                "id": "mechanics-elastic",
                "label": "Elastic Strains",
                "files": [str(Path("Project1/VTK/ElasticStrains_00000000.vts").resolve())],
                "dataset_config": {
                    "label": "Elastic Strains",
                    "scale": 100.0,
                    "units": "%",
                    "scalars": [
                        {"label": "eps_xx", "array": "ElasticStrains", "component": 0},
                    ],
                },
                "tab_id": "single_view",
            }
        )

        panel.controls_widget.scalar_combo.setCurrentIndex(0)
        panel.controls_widget.slice_slider.setValue(7)
        panel.controller.refresh_view()

        self.assertIn("Elastic Strains", panel.heatmap_canvas.status_text())
        self.assertIn("axis=y", panel.heatmap_canvas.status_text())
        self.assertIn("slice=0", panel.heatmap_canvas.status_text())
        self.assertEqual(panel.heatmap_canvas._axes.get_aspect(), 1.0)
        self.assertGreater(panel.histogram_field_combo.count(), 0)

    def test_panel_widget_has_no_resolution_dropdown(self):
        panel = PanelWidget(
            dataset_info={
                "id": "mechanics-elastic",
                "label": "Elastic Strains",
                "files": [str(Path("Project1/VTK/ElasticStrains_00000000.vts").resolve())],
                "dataset_config": {
                    "label": "Elastic Strains",
                    "scale": 100.0,
                    "units": "%",
                    "scalars": [
                        {"label": "eps_xx", "array": "ElasticStrains", "component": 0},
                    ],
                },
                "tab_id": "single_view",
            }
        )

        self.assertFalse(hasattr(panel, "resolution_combo"))
        self.assertFalse(hasattr(panel, "resolution_label"))

    def test_heatmap_uses_lightweight_live_resolution(self):
        panel = PanelWidget(
            dataset_info={
                "id": "mechanics-elastic",
                "label": "Elastic Strains",
                "files": [str(Path("Project1/VTK/ElasticStrains_00000000.vts").resolve())],
                "dataset_config": {
                    "label": "Elastic Strains",
                    "scale": 100.0,
                    "units": "%",
                    "scalars": [
                        {"label": "eps_xx", "array": "ElasticStrains", "component": 0},
                    ],
                },
                "tab_id": "single_view",
            }
        )
        grid = panel.heatmap_canvas._last_export_payload["z_grid"]

        self.assertEqual(grid.shape, (160, 160))

    def test_live_heatmap_keeps_visible_plotly_heatmap_and_colorbar(self):
        panel = PanelWidget(
            dataset_info={
                "id": "mechanics-elastic",
                "label": "Elastic Strains",
                "files": [str(Path("Project1/VTK/ElasticStrains_00000000.vts").resolve())],
                "dataset_config": {
                    "label": "Elastic Strains",
                    "scale": 100.0,
                    "units": "%",
                    "scalars": [
                        {"label": "eps_xx", "array": "ElasticStrains", "component": 0},
                    ],
                },
                "tab_id": "single_view",
            }
        )
        payload = panel.heatmap_canvas._last_export_payload

        figure = panel.heatmap_canvas._build_figure(
            x_grid=payload["x_grid"],
            y_grid=payload["y_grid"],
            z_grid=payload["z_grid"],
            cmap=payload["cmap"],
            vmin=payload["vmin"],
            vmax=payload["vmax"],
            line_overlay=payload["line_overlay"],
            overlay_grid=payload["overlay_grid"],
            title="",
            colorbar_label=payload["colorbar_label"],
            plot_type="heatmap",
        )

        self.assertEqual(tuple(figure.layout.images or ()), ())
        self.assertEqual(figure.data[0].type, "heatmap")
        self.assertNotEqual(figure.data[0].opacity, 0)
        self.assertIsNotNone(figure.data[0].colorbar)

    def test_png_export_uses_automatic_good_resolution(self):
        from matplotlib import image as mpimg

        panel = PanelWidget(
            dataset_info={
                "id": "mechanics-elastic",
                "label": "Elastic Strains",
                "files": [str(Path("Project1/VTK/ElasticStrains_00000000.vts").resolve())],
                "dataset_config": {
                    "label": "Elastic Strains",
                    "scale": 100.0,
                    "units": "%",
                    "scalars": [
                        {"label": "eps_xx", "array": "ElasticStrains", "component": 0},
                    ],
                },
                "tab_id": "single_view",
            }
        )
        output_path = Path(tempfile.gettempdir()) / "opview_auto_good_resolution_test.png"

        self.assertTrue(panel.heatmap_canvas.save_high_resolution_png(str(output_path)))
        image = mpimg.imread(output_path)

        self.assertGreaterEqual(image.shape[0], 1000)
        self.assertGreaterEqual(image.shape[1], 1000)

    def test_phase_field_defaults_to_phasefields_scalar(self):
        panel = PanelWidget(
            dataset_info={
                "id": "phase-field-phase",
                "label": "PhaseField",
                "files": [str(Path("Project1/VTK/PhaseField_00005000.vts").resolve())],
                "dataset_config": {
                    "label": "PhaseField",
                    "scalars": [
                        {"label": "PhaseFields", "array": "PhaseFields"},
                        {"label": "Interfaces", "array": "Interfaces"},
                    ],
                },
                "tab_id": "single_view",
            }
        )

        self.assertEqual(panel.controls_widget.current_scalar_label(), "PhaseFields")
        self.assertIn("PhaseFields", panel.map_title_label.text())

    def test_histogram_canvas_handles_near_constant_data(self):
        canvas = HistogramCanvas()
        values = [100000000.0, 100000000.0, 100000000.00000001, 99999999.99999999]

        canvas.render_histogram(values, label="CRSS 0", bins=30)

        self.assertEqual(canvas._axes.get_xlabel(), "CRSS 0")

    def test_panel_widget_exposes_dual_range_slider(self):
        panel = PanelWidget(
            dataset_info={
                "id": "phase-field-phase",
                "label": "PhaseField",
                "files": [str(Path("Project1/VTK/PhaseField_00005000.vts").resolve())],
                "dataset_config": {
                    "label": "PhaseField",
                    "scalars": [
                        {"label": "PhaseFields", "array": "PhaseFields"},
                        {"label": "Interfaces", "array": "Interfaces"},
                    ],
                },
                "tab_id": "single_view",
            }
        )

        slider = panel.controls_widget.range_slider

        self.assertIsNotNone(slider)
        self.assertLessEqual(slider.lower_value(), slider.upper_value())
        self.assertEqual(slider.lower_value(), panel.controller.state.range_min)
        self.assertEqual(slider.upper_value(), panel.controller.state.range_max)

    def test_range_slider_updates_controller_state(self):
        panel = PanelWidget(
            dataset_info={
                "id": "phase-field-phase",
                "label": "PhaseField",
                "files": [str(Path("Project1/VTK/PhaseField_00005000.vts").resolve())],
                "dataset_config": {
                    "label": "PhaseField",
                    "scalars": [
                        {"label": "PhaseFields", "array": "PhaseFields"},
                        {"label": "Interfaces", "array": "Interfaces"},
                    ],
                },
                "tab_id": "single_view",
            }
        )

        slider = panel.controls_widget.range_slider
        lower = panel.controller.state.range_min + 1.0
        upper = panel.controller.state.range_max - 1.0

        slider.set_values(lower, upper)

        self.assertAlmostEqual(panel.controller.state.range_min, lower, places=4)
        self.assertAlmostEqual(panel.controller.state.range_max, upper, places=4)
        self.assertAlmostEqual(panel.controls_widget.range_min_spin.value(), lower, places=4)
        self.assertAlmostEqual(panel.controls_widget.range_max_spin.value(), upper, places=4)

    def test_range_spin_boxes_update_slider_values(self):
        panel = PanelWidget(
            dataset_info={
                "id": "phase-field-phase",
                "label": "PhaseField",
                "files": [str(Path("Project1/VTK/PhaseField_00005000.vts").resolve())],
                "dataset_config": {
                    "label": "PhaseField",
                    "scalars": [
                        {"label": "PhaseFields", "array": "PhaseFields"},
                        {"label": "Interfaces", "array": "Interfaces"},
                    ],
                },
                "tab_id": "single_view",
            }
        )

        panel.controls_widget.range_min_spin.setValue(2.0)
        panel.controls_widget.range_max_spin.setValue(7.0)

        self.assertAlmostEqual(panel.controls_widget.range_slider.lower_value(), 2.0, places=4)
        self.assertAlmostEqual(panel.controls_widget.range_slider.upper_value(), 7.0, places=4)

    def test_range_reset_restores_slider_bounds(self):
        panel = PanelWidget(
            dataset_info={
                "id": "phase-field-phase",
                "label": "PhaseField",
                "files": [str(Path("Project1/VTK/PhaseField_00005000.vts").resolve())],
                "dataset_config": {
                    "label": "PhaseField",
                    "scalars": [
                        {"label": "PhaseFields", "array": "PhaseFields"},
                        {"label": "Interfaces", "array": "Interfaces"},
                    ],
                },
                "tab_id": "single_view",
            }
        )

        initial_min = panel.controller.state.range_min
        initial_max = panel.controller.state.range_max
        panel.controls_widget.range_slider.set_values(initial_min + 1.0, initial_max - 1.0)

        panel.controls_widget.reset_button.click()

        self.assertAlmostEqual(panel.controls_widget.range_slider.lower_value(), initial_min, places=4)
        self.assertAlmostEqual(panel.controls_widget.range_slider.upper_value(), initial_max, places=4)
        self.assertAlmostEqual(panel.controller.state.range_min, initial_min, places=4)
        self.assertAlmostEqual(panel.controller.state.range_max, initial_max, places=4)

    def test_full_scale_mode_ignores_manual_slider_range(self):
        panel = PanelWidget(
            dataset_info={
                "id": "phase-field-phase",
                "label": "PhaseField",
                "files": [str(Path("Project1/VTK/PhaseField_00005000.vts").resolve())],
                "dataset_config": {
                    "label": "PhaseField",
                    "scalars": [
                        {"label": "PhaseFields", "array": "PhaseFields"},
                        {"label": "Interfaces", "array": "Interfaces"},
                    ],
                },
                "tab_id": "single_view",
            }
        )

        slider = panel.controls_widget.range_slider
        slider.set_values(2.0, 7.0)
        panel.controls_widget.full_scale_check.setChecked(True)

        image = panel.heatmap_canvas._image

        self.assertIsNotNone(image)
        self.assertAlmostEqual(image.norm.vmin, float(panel.controller._last_scaled_grid.min()), places=4)
        self.assertAlmostEqual(image.norm.vmax, float(panel.controller._last_scaled_grid.max()), places=4)

    def test_invalid_spin_box_order_is_clamped_deterministically(self):
        panel = PanelWidget(
            dataset_info={
                "id": "phase-field-phase",
                "label": "PhaseField",
                "files": [str(Path("Project1/VTK/PhaseField_00005000.vts").resolve())],
                "dataset_config": {
                    "label": "PhaseField",
                    "scalars": [
                        {"label": "PhaseFields", "array": "PhaseFields"},
                        {"label": "Interfaces", "array": "Interfaces"},
                    ],
                },
                "tab_id": "single_view",
            }
        )

        panel.controls_widget.range_min_spin.setValue(8.0)
        panel.controls_widget.range_max_spin.setValue(3.0)

        self.assertLessEqual(panel.controller.state.range_min, panel.controller.state.range_max)
        self.assertLessEqual(
            panel.controls_widget.range_slider.lower_value(),
            panel.controls_widget.range_slider.upper_value(),
        )

    def test_panel_widget_uses_left_and_right_columns(self):
        panel = PanelWidget(
            dataset_info={
                "id": "phase-field-phase",
                "label": "PhaseField",
                "files": [str(Path("Project1/VTK/PhaseField_00005000.vts").resolve())],
                "dataset_config": {
                    "label": "PhaseField",
                    "scalars": [
                        {"label": "PhaseFields", "array": "PhaseFields"},
                        {"label": "Interfaces", "array": "Interfaces"},
                    ],
                },
                "tab_id": "single_view",
            }
        )

        self.assertIs(panel.left_column_layout.itemAt(0).widget(), panel.controls_widget)
        self.assertIs(panel.left_column_layout.itemAt(1).widget(), panel.heatmap_card)
        self.assertIs(panel.right_column_layout.itemAt(0).widget(), panel.analysis_card)
        self.assertEqual(
            panel.analysis_card.sizePolicy().verticalPolicy(),
            QSizePolicy.Policy.Expanding,
        )

    def test_sidebar_buttons_and_cards_expose_visual_properties(self):
        window = MainWindow()

        self.assertEqual(window.sidebar_widget.reload_projects_button.property("accent"), True)
        self.assertEqual(window.sidebar_widget.add_panel_button.property("accent"), True)
        self.assertEqual(window.sidebar_widget.projects_group.objectName(), "sidebarCard")
        self.assertEqual(window.sidebar_widget.panel_group.objectName(), "sidebarCard")


if __name__ == "__main__":
    unittest.main()
