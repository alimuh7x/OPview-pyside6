import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QSizePolicy, QWidget

from app.application_bootstrap import ApplicationBootstrap
from app.main_window import MainWindow
from app.styles import build_app_stylesheet
from single_view.tab_widget import SingleViewTab
from viewer.histogram_canvas import HistogramCanvas
from viewer.panel_widget import PanelWidget
from viewer.time_plot_canvas import TimePlotCanvas


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

    def test_viewer_spin_box_selection_uses_light_blue(self):
        stylesheet = build_app_stylesheet()

        self.assertIn("selection-background-color: #d8ecff;", stylesheet)
        self.assertIn("selection-color: #102a52;", stylesheet)

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

    def test_main_window_does_not_start_filesystem_autoscan(self):
        window = MainWindow()

        self.assertFalse(hasattr(window, "file_watcher"))

    def test_main_window_manual_folder_project_name_uses_parent_and_folder(self):
        window = MainWindow()
        folder = Path("/tmp/VTK_final/VTK_final")

        self.assertEqual(window._manual_folder_project_name(folder), "VTK_final/VTK_final")

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


    def test_panel_analysis_card_has_plot_over_time_section(self):
        panel = PanelWidget({"label": "PhaseField", "files": []})

        section_titles = [
            label.text()
            for label in panel.findChildren(QLabel, "sectionTitle")
        ]

        self.assertIn("Plot Over Time", section_titles)
        self.assertIsInstance(panel.time_plot_canvas, TimePlotCanvas)
        self.assertEqual(panel.time_plot_selected_label.text(), "No point selected")
        self.assertIsNotNone(panel.findChild(QWidget, "timePlotToolbar"))
        self.assertIsNotNone(panel.findChild(QWidget, "timePlotActionRow"))
        self.assertIsNotNone(panel.findChild(QWidget, "timePlotStatusRow"))
        self.assertEqual(panel.time_plot_add_point_btn.objectName(), "timePlotAddPointButton")
        self.assertEqual(panel.time_plot_calculate_btn.objectName(), "timePlotCalculateButton")
        self.assertEqual(panel.time_plot_use_same_points_check.objectName(), "timePlotUseSamePointsToggle")
        self.assertFalse(panel.time_plot_use_same_points_check.isChecked())

    def test_plot_over_time_click_mode_selects_point_without_range_change(self):
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
        before_range = (panel.controller.state.range_min, panel.controller.state.range_max)
        x_grid, y_grid, _ = panel.controller._last_display_grids
        x_value = float(x_grid[0, 0])
        y_value = float(y_grid[0, 0])

        panel.time_plot_add_point_btn.click()
        panel.controller._handle_heatmap_click(x_value, y_value)

        self.assertTrue(panel.time_plot_add_point_btn.isChecked())
        self.assertTrue(panel.controller.state.time_plot_pick_mode)
        self.assertEqual(panel.controller.state.click_count, 0)
        self.assertEqual((panel.controller.state.range_min, panel.controller.state.range_max), before_range)
        self.assertAlmostEqual(panel.controller.state.time_plot_x, x_value)
        self.assertAlmostEqual(panel.controller.state.time_plot_y, y_value)
        self.assertIn("x=", panel.time_plot_selected_label.text())

    def test_single_view_tab_use_same_points_toggle_follows_shared_points(self):
        tab = SingleViewTab()
        source = PanelWidget({"label": "PhaseField", "files": []})
        target = PanelWidget({"label": "CRSS", "files": []})
        tab._attach_time_plot_point_sharing(source)
        tab._attach_time_plot_point_sharing(target)

        source.controller.set_time_plot_points(
            [{"label": "P1", "x": 12.0, "y": 18.0}],
            source="test-source",
            notify=True,
        )
        target.time_plot_use_same_points_check.setChecked(True)

        self.assertTrue(target.time_plot_use_same_points_check.isChecked())
        self.assertEqual(len(target.controller.state.time_plot_points), 1)
        self.assertAlmostEqual(float(target.controller.state.time_plot_points[0]["x"]), 12.0)
        self.assertAlmostEqual(float(target.controller.state.time_plot_points[0]["y"]), 18.0)

        source.controller.set_time_plot_points(
            [
                {"label": "P1", "x": 12.0, "y": 18.0},
                {"label": "P2", "x": 20.0, "y": 25.0},
            ],
            source="test-source",
            notify=True,
        )

        self.assertEqual(len(target.controller.state.time_plot_points), 2)
        self.assertEqual(target.controller.state.time_plot_points[1]["label"], "P2")
        self.assertAlmostEqual(float(target.controller.state.time_plot_points[1]["x"]), 20.0)
        self.assertAlmostEqual(float(target.controller.state.time_plot_points[1]["y"]), 25.0)

    def test_plot_over_time_add_point_toggle_disables_range_and_line_modes(self):
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

        panel.line_mode_check.setChecked(True)
        self.assertTrue(panel.line_mode_check.isChecked())

        panel.time_plot_add_point_btn.click()

        self.assertTrue(panel.time_plot_add_point_btn.isChecked())
        self.assertEqual(panel.time_plot_add_point_btn.text(), "Add Point: ON")
        self.assertTrue(panel.controller.state.time_plot_pick_mode)
        self.assertFalse(panel.line_mode_check.isChecked())
        self.assertFalse(panel.controls_widget.click_mode_range_check.isChecked())
        self.assertEqual(panel.controller.state.click_count, 0)
        self.assertIsNone(panel.controller.state.first_click)

    def test_project_change_loads_first_new_file_and_resyncs_playback_slider(self):
        first_project_files = [
            str(Path("Project1/VTK/ElasticStrains_00000000.vts").resolve()),
            str(Path("Project1/VTK/ElasticStrains_00000500.vts").resolve()),
        ]
        second_project_files = [
            str(Path("Project1/VTK/ElasticStrains_00001000.vts").resolve()),
            str(Path("Project1/VTK/ElasticStrains_00001500.vts").resolve()),
            str(Path("Project1/VTK/ElasticStrains_00002000.vts").resolve()),
        ]
        panel = PanelWidget(
            dataset_info={
                "id": "mechanics-elastic",
                "label": "Elastic Strains",
                "available_projects": [
                    {
                        "vtk_folder": str(Path("Project1/VTK").resolve()),
                        "project_name": "First",
                        "files": first_project_files,
                    },
                    {
                        "vtk_folder": str(Path("Project1/VTK").resolve()),
                        "project_name": "Second",
                        "files": second_project_files,
                    },
                ],
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

        panel.playback_slider.setValue(1)
        self.assertEqual(panel.controller.state.file_path, first_project_files[1])

        panel.controls_widget.project_combo.setCurrentIndex(1)

        self.assertEqual(panel.controls_widget.file_combo.count(), 3)
        self.assertEqual(panel.controls_widget.current_file_path(), second_project_files[0])
        self.assertEqual(panel.controller.state.file_path, second_project_files[0])
        self.assertEqual(panel.playback_slider.maximum(), 2)
        self.assertEqual(panel.playback_slider.value(), 0)
        self.assertEqual(panel.frame_label.text(), "1 / 3")

    def test_range_or_line_mode_turns_off_add_point_toggle(self):
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

        panel.time_plot_add_point_btn.click()
        panel.controls_widget.click_mode_range_check.setChecked(True)

        self.assertFalse(panel.time_plot_add_point_btn.isChecked())
        self.assertEqual(panel.time_plot_add_point_btn.text(), "Add Point")
        self.assertFalse(panel.controller.state.time_plot_pick_mode)
        self.assertTrue(panel.controls_widget.click_mode_range_check.isChecked())

        panel.time_plot_add_point_btn.click()
        panel.line_mode_check.setChecked(True)

        self.assertFalse(panel.time_plot_add_point_btn.isChecked())
        self.assertEqual(panel.time_plot_add_point_btn.text(), "Add Point")
        self.assertFalse(panel.controller.state.time_plot_pick_mode)
        self.assertTrue(panel.line_mode_check.isChecked())

    def test_plot_over_time_can_store_multiple_clicked_points(self):
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
        x_grid, y_grid, _ = panel.controller._last_display_grids

        panel.time_plot_add_point_btn.click()
        panel.controller._handle_heatmap_click(float(x_grid[0, 0]), float(y_grid[0, 0]))
        panel.controller._handle_heatmap_click(float(x_grid[-1, -1]), float(y_grid[-1, -1]))

        self.assertEqual(len(panel.controller.state.time_plot_points), 2)
        self.assertIn("2 points selected", panel.time_plot_selected_label.text())

    def test_plot_over_time_shows_selected_point_rows_and_can_remove_one(self):
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
        x_grid, y_grid, _ = panel.controller._last_display_grids

        panel.time_plot_add_point_btn.click()
        panel.controller._handle_heatmap_click(float(x_grid[0, 0]), float(y_grid[0, 0]))
        panel.controller._handle_heatmap_click(float(x_grid[-1, -1]), float(y_grid[-1, -1]))

        point_labels = panel.time_plot_points_container.findChildren(QLabel, "timePlotPointLabel")
        remove_buttons = panel.time_plot_points_container.findChildren(QPushButton, "timePlotRemovePointButton")
        self.assertEqual([label.text().split()[0] for label in point_labels], ["P1", "P2"])
        self.assertEqual(len(remove_buttons), 2)

        remove_buttons[0].click()

        remaining_labels = panel.time_plot_points_container.findChildren(QLabel, "timePlotPointLabel")
        self.assertEqual(len(panel.controller.state.time_plot_points), 1)
        self.assertEqual(remaining_labels[0].text().split()[0], "P1")
        self.assertIn("1 point selected", panel.time_plot_selected_label.text())

    def test_plot_over_time_show_points_draws_heatmap_markers(self):
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
        x_grid, y_grid, _ = panel.controller._last_display_grids

        panel.time_plot_add_point_btn.click()
        panel.controller._handle_heatmap_click(float(x_grid[0, 0]), float(y_grid[0, 0]))
        panel.controller._handle_heatmap_click(float(x_grid[-1, -1]), float(y_grid[-1, -1]))
        panel.time_plot_show_points_check.setChecked(True)

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
            time_plot_points=payload["time_plot_points"],
            title="",
            colorbar_label=payload["colorbar_label"],
            plot_type="heatmap",
        )

        marker_traces = [trace for trace in figure.data if trace.name == "Plot Over Time Points"]
        self.assertEqual(len(marker_traces), 1)
        self.assertEqual(tuple(marker_traces[0].text), ("P1", "P2"))

    def test_file_change_keeps_time_plot_points_and_line_scan_position(self):
        first_file = str(Path("Project1/VTK/ElasticStrains_00000000.vts").resolve())
        second_file = str(Path("Project1/VTK/ElasticStrains_00000500.vts").resolve())
        panel = PanelWidget(
            dataset_info={
                "id": "mechanics-elastic",
                "label": "Elastic Strains",
                "files": [first_file, second_file],
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
        x_grid, y_grid, _ = panel.controller._last_display_grids
        point_x = float(x_grid[0, 0])
        point_y = float(y_grid[0, 0])
        line_y = float(y_grid[20, 0])

        panel.time_plot_add_point_btn.click()
        panel.controller._handle_heatmap_click(point_x, point_y)
        panel.time_plot_show_points_check.setChecked(True)
        panel.line_mode_check.setChecked(True)
        panel.show_line_check.setChecked(True)
        panel.controller._handle_heatmap_click(point_x, line_y)

        panel.controls_widget.file_combo.setCurrentIndex(1)

        self.assertEqual(panel.controller.state.file_path, second_file)
        self.assertTrue(panel.controller.state.time_plot_points_visible)
        self.assertEqual(len(panel.controller.state.time_plot_points), 1)
        self.assertAlmostEqual(float(panel.controller.state.time_plot_points[0]["x"]), point_x)
        self.assertAlmostEqual(float(panel.controller.state.time_plot_points[0]["y"]), point_y)
        self.assertAlmostEqual(panel.controller.state.line_scan_y, line_y)
        payload = panel.heatmap_canvas._last_export_payload
        self.assertEqual(payload["time_plot_points"][0]["label"], "P1")
        self.assertEqual(payload["line_overlay"], ("horizontal", line_y))

    def test_manual_point_dialog_has_clear_coordinate_inputs(self):
        from viewer.manual_point_dialog import ManualPointDialog

        dialog = ManualPointDialog(x_value=1.25, y_value=2.5)

        self.assertEqual(dialog.objectName(), "manualPointDialog")
        self.assertEqual(dialog.windowTitle(), "Manual Point")
        self.assertEqual(dialog.x_input.objectName(), "manualPointXInput")
        self.assertEqual(dialog.y_input.objectName(), "manualPointYInput")
        self.assertAlmostEqual(dialog.point_values()[0], 1.25)
        self.assertAlmostEqual(dialog.point_values()[1], 2.5)
        stylesheet = dialog.styleSheet()
        self.assertIn("QDialog#manualPointDialog", stylesheet)
        self.assertIn("QLabel#manualPointLabel", stylesheet)
        self.assertIn("QDoubleSpinBox#manualPointXInput", stylesheet)
        self.assertIn("color: #102a52", stylesheet)
        self.assertIn("background: #ffffff", stylesheet)

    def test_plot_over_time_clicked_point_snaps_to_grid_point(self):
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
        x_grid, y_grid, _ = panel.controller._last_display_grids
        expected_x = float(x_grid[0, 0])
        expected_y = float(y_grid[0, 0])

        panel.time_plot_add_point_btn.click()
        panel.controller._handle_heatmap_click(expected_x + 0.19, expected_y + 0.21)

        point = panel.controller.state.time_plot_points[0]
        self.assertAlmostEqual(point["x"], expected_x)
        self.assertAlmostEqual(point["y"], expected_y)

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

    def test_heatmap_mode_dropdown_includes_gradient_magnitude(self):
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

        labels = [
            panel.controls_widget.scalar_combo.itemText(index)
            for index in range(panel.controls_widget.scalar_combo.count())
        ]
        plot_modes = [
            panel.controls_widget.plot_type_combo.itemText(index)
            for index in range(panel.controls_widget.plot_type_combo.count())
        ]

        self.assertEqual(labels, ["eps_xx"])
        self.assertIn("|grad|", plot_modes)

    def test_selecting_gradient_magnitude_mode_updates_heatmap_grid(self):
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

        grad_index = panel.controls_widget.plot_type_combo.findText("|grad|")
        self.assertGreaterEqual(grad_index, 0)
        panel.controls_widget.plot_type_combo.setCurrentIndex(grad_index)
        panel.controller.refresh_view()

        payload = panel.heatmap_canvas._last_export_payload
        z_grid = payload["z_grid"]

        self.assertEqual(panel.controls_widget.current_scalar_label(), "eps_xx")
        self.assertEqual(panel.controls_widget.current_plot_type(), "gradient_magnitude")
        self.assertIn("|grad|", payload["colorbar_label"])
        self.assertGreater(float(z_grid.max()), 0.0)
        self.assertGreaterEqual(float(z_grid.min()), 0.0)

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

    def test_threshold_png_export_masks_values_outside_selected_range(self):
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
        panel.heatmap_canvas._last_export_payload = {
            "z_grid": np.array([[0.1, 0.6], [0.8, 1.2]], dtype=float),
            "x_grid": np.array([[0.0, 1.0], [0.0, 1.0]], dtype=float),
            "y_grid": np.array([[0.0, 0.0], [1.0, 1.0]], dtype=float),
            "cmap": "viridis",
            "vmin": 0.5,
            "vmax": 1.0,
            "plot_type": "threshold",
            "line_overlay": None,
            "overlay_grid": None,
            "time_plot_points": [],
            "colorbar_label": "",
            "phase_fraction_overlays": [],
        }

        z_grid = panel.heatmap_canvas._export_z_grid_for_payload(
            panel.heatmap_canvas._last_export_payload
        )

        self.assertTrue(np.isnan(z_grid[0, 0]))
        self.assertFalse(np.isnan(z_grid[0, 1]))
        self.assertFalse(np.isnan(z_grid[1, 0]))
        self.assertTrue(np.isnan(z_grid[1, 1]))

    def test_threshold_export_uses_exact_current_row_png_with_logo(self):
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
        threshold_index = panel.controls_widget.plot_type_combo.findData("threshold")
        panel.controls_widget.plot_type_combo.blockSignals(True)
        panel.controls_widget.plot_type_combo.setCurrentIndex(threshold_index)
        panel.controls_widget.plot_type_combo.blockSignals(False)
        calls = []

        class FakePixmap:
            def isNull(self):
                return False

            def save(self, path, fmt):
                calls.append(("current-row", path, fmt))
                return True

        class FakeExportWidget:
            def grab(self):
                calls.append(("grab-export-widget",))
                return FakePixmap()

        def fake_save_png(path):
            calls.append(("heatmap-only", path))
            return True

        def fake_save_high_resolution_png(path):
            calls.append(("high-resolution", path))
            return True

        panel.controller.export_widget = FakeExportWidget()
        panel.heatmap_canvas.save_png = fake_save_png
        panel.heatmap_canvas.save_high_resolution_png = fake_save_high_resolution_png
        output_path = str(Path(tempfile.gettempdir()) / "opview_threshold_exact_view_test.png")

        with patch("viewer.heatmap_controller.QFileDialog.getSaveFileName", return_value=(output_path, "PNG (*.png)")):
            panel.controller._export_png()

        self.assertEqual(calls, [("grab-export-widget",), ("current-row", output_path, "PNG")])

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

    def test_phase_field_panel_shows_phase_fraction_history_graph(self):
        first_file = str(Path("Project1/VTK/PhaseField_00000000.vts").resolve())
        second_file = str(Path("Project1/VTK/PhaseField_00005000.vts").resolve())
        panel = PanelWidget(
            dataset_info={
                "id": "phase-field-phase",
                "label": "PhaseField",
                "files": [first_file, second_file],
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

        payload = panel.phase_fraction_history_canvas._last_payload

        self.assertFalse(panel.phase_fraction_history_canvas.isHidden())
        self.assertFalse(panel.phase_fraction_history_separator.isHidden())
        self.assertEqual(payload["y_label"], "Phase fraction (%)")
        self.assertEqual(payload["current_step"], 0)
        self.assertIn("PhaseFraction_0", [item["label"] for item in payload["series"]])
        for item in payload["series"]:
            for value in item["values"]:
                self.assertGreaterEqual(value, 0.0)
                self.assertLessEqual(value, 100.0)

        panel.controls_widget.file_combo.setCurrentIndex(1)

        self.assertEqual(panel.phase_fraction_history_canvas._last_payload["current_step"], 5000)

        panel.phase_history_dt_spin.setValue(0.5)
        panel.phase_history_time_unit_combo.setCurrentText("min")

        converted_payload = panel.phase_fraction_history_canvas._last_payload
        self.assertEqual(converted_payload["x_label"], "Time [min]")
        self.assertAlmostEqual(converted_payload["current_step"], 2500 / 60)
        self.assertAlmostEqual(converted_payload["series"][0]["steps"][1], 2500 / 60)

    def test_plot_over_time_uses_phase_history_dt_time_axis(self):
        panel = PanelWidget({"label": "PhaseField", "files": []})
        panel.controller._time_plot_series_data = [
            {"label": "P1", "x": 1.0, "y": 2.0, "steps": [0, 5000], "values": [3.0, 4.0]}
        ]
        panel.controller._time_plot_display_label = "PhaseFields"

        self.assertEqual(panel.phase_history_time_unit_combo.itemText(0), "timestep")
        default_series, default_x_label, default_hover_x_label = panel.controller._converted_time_plot_series()
        self.assertEqual(default_x_label, "Timestep")
        self.assertEqual(default_hover_x_label, "timestep")
        self.assertEqual(default_series[0]["steps"], [0.0, 5000.0])

        panel.phase_history_dt_spin.setValue(0.5)
        panel.phase_history_time_unit_combo.setCurrentText("min")
        converted_series, x_label, hover_x_label = panel.controller._converted_time_plot_series()

        self.assertEqual(x_label, "Time [min]")
        self.assertEqual(hover_x_label, "time")
        self.assertAlmostEqual(converted_series[0]["steps"][1], 2500 / 60)

    def test_non_phase_field_panel_hides_phase_fraction_history_graph(self):
        panel = PanelWidget(
            dataset_info={
                "id": "mechanics-elastic",
                "label": "Elastic Strains",
                "files": [str(Path("Project1/VTK/ElasticStrains_00000000.vts").resolve())],
                "dataset_config": {
                    "label": "Elastic Strains",
                    "scalars": [
                        {"label": "eps_xx", "array": "ElasticStrains", "component": 0},
                    ],
                },
                "tab_id": "single_view",
            }
        )

        self.assertTrue(panel.phase_fraction_history_canvas.isHidden())
        self.assertTrue(panel.phase_fraction_history_separator.isHidden())

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

    def test_range_spin_box_text_edit_commits_only_when_finished(self):
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
        panel.show()
        QApplication.processEvents()
        panel.controls_widget.range_min_spin.setValue(2.0)
        panel.controls_widget.range_max_spin.setValue(7.0)
        QApplication.processEvents()

        line_edit = panel.controls_widget.range_min_spin.lineEdit()
        panel.controls_widget.range_min_spin.setFocus()
        line_edit.selectAll()
        QTest.keyClicks(line_edit, "1")
        QApplication.processEvents()

        self.assertAlmostEqual(panel.controls_widget.range_slider.lower_value(), 2.0, places=4)
        self.assertAlmostEqual(panel.controls_widget.range_slider.upper_value(), 7.0, places=4)
        self.assertAlmostEqual(panel.controller.state.range_min, 2.0, places=4)
        self.assertAlmostEqual(panel.controller.state.range_max, 7.0, places=4)

        QTest.keyClick(line_edit, Qt.Key.Key_Return)
        QApplication.processEvents()

        self.assertAlmostEqual(panel.controls_widget.range_slider.lower_value(), 1.0, places=4)
        self.assertAlmostEqual(panel.controls_widget.range_slider.upper_value(), 7.0, places=4)
        self.assertAlmostEqual(panel.controller.state.range_min, 1.0, places=4)
        self.assertAlmostEqual(panel.controller.state.range_max, 7.0, places=4)

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

    def test_manual_range_is_preserved_when_changing_file_frame(self):
        first_file = str(Path("Project1/VTK/PhaseField_00000000.vts").resolve())
        second_file = str(Path("Project1/VTK/PhaseField_00005000.vts").resolve())
        panel = PanelWidget(
            dataset_info={
                "id": "phase-field-phase",
                "label": "PhaseField",
                "files": [first_file, second_file],
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

        panel.controls_widget.range_min_spin.setValue(0.2)
        panel.controls_widget.range_max_spin.setValue(0.8)

        panel.controls_widget.file_combo.setCurrentIndex(1)

        self.assertEqual(panel.controller.state.file_path, second_file)
        self.assertAlmostEqual(panel.controller.state.range_min, 0.2, places=4)
        self.assertAlmostEqual(panel.controller.state.range_max, 0.8, places=4)
        self.assertAlmostEqual(panel.controls_widget.range_min_spin.value(), 0.2, places=4)
        self.assertAlmostEqual(panel.controls_widget.range_max_spin.value(), 0.8, places=4)
        self.assertAlmostEqual(panel.heatmap_canvas._last_export_payload["vmin"], 0.2, places=4)
        self.assertAlmostEqual(panel.heatmap_canvas._last_export_payload["vmax"], 0.8, places=4)

    def test_manual_range_is_preserved_when_changing_file_on_non_first_scalar(self):
        first_file = str(Path("Project1/VTK/PhaseField_00000000.vts").resolve())
        second_file = str(Path("Project1/VTK/PhaseField_00005000.vts").resolve())
        panel = PanelWidget(
            dataset_info={
                "id": "phase-field-phase",
                "label": "PhaseField",
                "files": [first_file, second_file],
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

        panel.controls_widget.scalar_combo.setCurrentIndex(1)
        panel.controls_widget.range_min_spin.setValue(0.2)
        panel.controls_widget.range_max_spin.setValue(0.8)

        panel.controls_widget.file_combo.setCurrentIndex(1)

        self.assertEqual(panel.controller.state.file_path, second_file)
        self.assertEqual(panel.controller.state.scalar_label, "Interfaces")
        self.assertAlmostEqual(panel.controller.state.range_min, 0.2, places=4)
        self.assertAlmostEqual(panel.controller.state.range_max, 0.8, places=4)
        self.assertAlmostEqual(panel.controls_widget.range_min_spin.value(), 0.2, places=4)
        self.assertAlmostEqual(panel.controls_widget.range_max_spin.value(), 0.8, places=4)
        self.assertAlmostEqual(panel.heatmap_canvas._last_export_payload["vmin"], 0.2, places=4)
        self.assertAlmostEqual(panel.heatmap_canvas._last_export_payload["vmax"], 0.8, places=4)

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

    def test_manual_range_edit_turns_off_full_scale_mode(self):
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

        panel.controls_widget.full_scale_check.setChecked(True)
        panel.controls_widget.range_min_spin.setValue(2.0)
        panel.controls_widget.range_max_spin.setValue(7.0)

        image = panel.heatmap_canvas._image

        self.assertFalse(panel.controls_widget.full_scale_check.isChecked())
        self.assertEqual(panel.controller.state.colorscale_mode, "normal")
        self.assertAlmostEqual(image.norm.vmin, 2.0, places=4)
        self.assertAlmostEqual(image.norm.vmax, 7.0, places=4)

    def test_heatmap_click_does_not_change_range_when_range_selection_is_off(self):
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
        before_range = (panel.controller.state.range_min, panel.controller.state.range_max)
        x_grid, y_grid, _ = panel.controller._last_display_grids

        panel.controls_widget.click_mode_range_check.setChecked(False)
        panel.controller._handle_heatmap_click(float(x_grid[0, 0]), float(y_grid[0, 0]))
        panel.controller._handle_heatmap_click(float(x_grid[-1, -1]), float(y_grid[-1, -1]))

        self.assertFalse(panel.controls_widget.click_mode_range_check.isChecked())
        self.assertFalse(panel.line_mode_check.isChecked())
        self.assertEqual(panel.controller.state.click_mode, "none")
        self.assertEqual((panel.controller.state.range_min, panel.controller.state.range_max), before_range)

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
