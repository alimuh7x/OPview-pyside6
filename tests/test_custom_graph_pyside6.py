import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QPushButton, QScrollArea, QTabWidget, QWidget

from data.text_sources import GenericTextDataSource
from app.styles import build_app_stylesheet
from graphs.graph_canvas import GraphCanvas
from graphs.graph_panel_widget import GraphPanelWidget
from graphs.tab_widget import CustomGraphTab
from sidebar.sidebar_widget import SidebarWidget
from utils.project_scanner import get_textdata_files
from viewer.plot_style import PlotStyle


class CustomGraphPySide6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_generic_text_source_loads_file_outside_textdata_folder(self):
        temp_dir = Path(tempfile.mkdtemp())
        path = temp_dir / "custom_graph_anywhere.dat"
        path.write_text("Time Stress Strain\n0 100 0.0\n1 120 0.1\n", encoding="utf-8")

        source = GenericTextDataSource(path)

        self.assertTrue(source.load())
        self.assertEqual(source.columns(), ["Time", "Stress", "Strain"])
        self.assertEqual(source.series("Stress").tolist(), [100, 120])

    def test_generic_text_source_pads_ragged_comma_rows_like_crss_file(self):
        temp_dir = Path(tempfile.mkdtemp())
        path = temp_dir / "ragged_crss.txt"
        path.write_text(
            "Time, ss_1, ss_2, Average\n"
            "0, 100, 200\n"
            "1, 110, 210\n",
            encoding="utf-8",
        )

        source = GenericTextDataSource(path)

        self.assertTrue(source.load())
        self.assertEqual(source.columns(), ["Time", "ss_1", "ss_2"])
        self.assertEqual(source.series("ss_1").tolist(), [100, 110])

    def test_generic_text_source_loads_project_crss_file(self):
        source = GenericTextDataSource(Path("Project1/TextData/CRSSFile.txt"))

        self.assertTrue(source.load())
        self.assertIn("Time", source.columns())
        self.assertIn("ss_1", source.columns())
        self.assertGreater(len(source.series("ss_1")), 100)

    def test_project_scanner_discovers_text_files_outside_textdata_folder(self):
        root = Path(tempfile.mkdtemp()) / "custom_graph_project"
        nested = root / "Results" / "Curves"
        nested.mkdir(parents=True, exist_ok=True)
        sample = nested / "curve.opd"
        sample.write_text("Time Value\n0 1\n1 2\n", encoding="utf-8")

        projects = {
            "ManualProject": {
                "path": root,
                "has_textdata": False,
                "textdata_path": None,
            }
        }

        files = get_textdata_files(projects, ["ManualProject"])

        self.assertIn(str(sample.resolve()), files)

    def test_custom_graph_tab_creates_closeable_graph_panel_tabs(self):
        tab = CustomGraphTab()

        tabs = tab.findChild(QTabWidget, "graphPanelTabs")
        self.assertIsNotNone(tabs)
        self.assertEqual(tabs.count(), 2)
        panel = tabs.widget(0)
        self.assertIs(panel, tabs.widget(0))
        self.assertEqual(tabs.tabText(1), "+")
        header = tabs.tabBar().tabButton(0, tabs.tabBar().ButtonPosition.LeftSide)
        self.assertIsNotNone(header)
        label = header.findChild(QLabel, "panelTabLabel")
        close_button = header.findChild(QPushButton, "panelTabCloseButton")
        self.assertIsNotNone(label)
        self.assertEqual(label.text(), "Graph Tab 1")
        self.assertIsNotNone(close_button)
        self.assertEqual(panel.state()["files"], [])

    def test_custom_graph_plus_tab_creates_tabs_after_all_tabs_closed(self):
        tab = CustomGraphTab()
        tabs = tab.findChild(QTabWidget, "graphPanelTabs")
        first_panel = tabs.widget(0)

        tab._on_tab_bar_clicked(tab._plus_index())
        tab._on_tab_bar_clicked(tab._plus_index())
        self.assertEqual(tabs.count(), 4)

        tab._remove_panel(first_panel)
        tab._remove_panel(tabs.widget(0))
        tab._remove_panel(tabs.widget(0))
        self.assertEqual(tabs.count(), 2)
        self.assertEqual(tabs.tabText(1), "+")

        tab._on_tab_bar_clicked(tab._plus_index())
        self.assertEqual(tabs.count(), 3)

    def test_custom_graph_tab_adds_files_to_active_panel_and_creates_panel_if_needed(self):
        temp_dir = Path(tempfile.mkdtemp())
        path = temp_dir / "curves.txt"
        path.write_text("Time A\n0 1\n1 2\n", encoding="utf-8")
        tab = CustomGraphTab()

        panel = tab.add_files_to_active_panel([str(path)])

        tabs = tab.findChild(QTabWidget, "graphPanelTabs")
        self.assertEqual(tabs.count(), 2)
        self.assertIs(panel, tabs.widget(0))
        self.assertEqual(panel.state()["files"], [str(path.resolve())])

    def test_sidebar_custom_graph_mode_only_filters_projects_for_graph_tabs(self):
        root = Path(tempfile.mkdtemp()) / "TextOnlyProject"
        textdata = root / "TextData"
        textdata.mkdir(parents=True)
        keep = textdata / "curve_keep.txt"
        hide = textdata / "other.dat"
        keep.write_text("Time A\n0 1\n", encoding="utf-8")
        hide.write_text("Time B\n0 2\n", encoding="utf-8")
        sidebar = SidebarWidget()
        projects = {
            "TextOnlyProject": {
                "path": root,
                "has_vtk": False,
                "vtk_path": None,
                "has_textdata": True,
                "textdata_path": textdata,
            },
            "VtkOnlyProject": {
                "path": root.parent / "VtkOnlyProject",
                "has_vtk": True,
                "vtk_path": root.parent / "VtkOnlyProject" / "VTK",
                "has_textdata": False,
                "textdata_path": None,
            },
        }

        sidebar.set_mode("custom_graph")
        sidebar.set_projects(projects)
        sidebar.project_list.item(0).setCheckState(Qt.CheckState.Checked)

        self.assertEqual(sidebar.project_list.count(), 1)
        self.assertEqual(sidebar.project_list.item(0).text(), "TextOnlyProject")
        self.assertTrue(sidebar.panel_group.isHidden())
        self.assertTrue(sidebar.text_files_group.isHidden())

    def test_sidebar_normal_mode_keeps_vtk_project_list(self):
        root = Path(tempfile.mkdtemp())
        sidebar = SidebarWidget()
        projects = {
            "TextOnlyProject": {
                "path": root / "TextOnlyProject",
                "has_vtk": False,
                "vtk_path": None,
                "has_textdata": True,
                "textdata_path": root / "TextOnlyProject" / "TextData",
            },
            "VtkProject": {
                "path": root / "VtkProject",
                "has_vtk": True,
                "vtk_path": root / "VtkProject" / "VTK",
                "has_textdata": False,
                "textdata_path": None,
            },
        }

        sidebar.set_mode("vtk")
        sidebar.set_projects(projects)

        self.assertEqual(sidebar.project_list.count(), 1)
        self.assertEqual(sidebar.project_list.item(0).text(), "VtkProject")
        self.assertFalse(sidebar.panel_group.isHidden())
        self.assertTrue(sidebar.text_files_group.isHidden())

    def test_sidebar_remembers_project_check_state_when_switching_modes(self):
        root = Path(tempfile.mkdtemp())
        text_project = root / "TextProject"
        textdata = text_project / "TextData"
        textdata.mkdir(parents=True)
        textdata.joinpath("curves.txt").write_text("Time A\n0 1\n", encoding="utf-8")
        vtk_project = root / "VtkProject"
        vtk_path = vtk_project / "VTK"
        vtk_path.mkdir(parents=True)
        sidebar = SidebarWidget()
        sidebar.set_projects({
            "TextProject": {
                "path": text_project,
                "has_vtk": False,
                "vtk_path": None,
                "has_textdata": True,
                "textdata_path": textdata,
            },
            "VtkProject": {
                "path": vtk_project,
                "has_vtk": True,
                "vtk_path": vtk_path,
                "has_textdata": False,
                "textdata_path": None,
            },
        })

        sidebar.set_mode("custom_graph")
        sidebar.project_list.item(0).setCheckState(Qt.CheckState.Checked)
        sidebar.set_mode("vtk")
        sidebar.project_list.item(0).setCheckState(Qt.CheckState.Checked)
        sidebar.set_mode("custom_graph")

        self.assertEqual(sidebar.project_list.item(0).text(), "TextProject")
        self.assertEqual(sidebar.project_list.item(0).checkState(), Qt.CheckState.Checked)

        sidebar.project_list.item(0).setCheckState(Qt.CheckState.Unchecked)
        sidebar.set_mode("vtk")
        sidebar.set_mode("custom_graph")

        self.assertEqual(sidebar.project_list.item(0).checkState(), Qt.CheckState.Unchecked)

    def test_sidebar_project_list_grows_with_projects_and_dataset_list_shows_eight_rows(self):
        root = Path(tempfile.mkdtemp())
        sidebar = SidebarWidget()
        projects = {}
        for index in range(3):
            project_root = root / f"Project{index}"
            vtk_path = project_root / "VTK"
            vtk_path.mkdir(parents=True)
            projects[f"Project{index}"] = {
                "path": project_root,
                "has_vtk": True,
                "vtk_path": vtk_path,
                "has_textdata": False,
                "textdata_path": None,
            }

        sidebar.set_mode("vtk")
        sidebar.set_projects({"Project0": projects["Project0"]})
        one_project_height = sidebar.project_list.maximumHeight()
        sidebar.set_projects(projects)
        three_project_height = sidebar.project_list.maximumHeight()

        self.assertGreater(three_project_height, one_project_height)
        self.assertEqual(
            sidebar.dataset_list.minimumHeight(),
            sidebar._list_height_for_rows(8),
        )

    def test_sidebar_project_row_click_toggles_checkbox_state(self):
        root = Path(tempfile.mkdtemp())
        vtk_project = root / "VtkProject"
        vtk_path = vtk_project / "VTK"
        vtk_path.mkdir(parents=True)
        sidebar = SidebarWidget()
        sidebar.set_projects({
            "VtkProject": {
                "path": vtk_project,
                "has_vtk": True,
                "vtk_path": vtk_path,
                "has_textdata": False,
                "textdata_path": None,
            }
        })
        item = sidebar.project_list.item(0)

        sidebar._toggle_project_item_from_row_click(item)
        self.assertEqual(item.checkState(), Qt.CheckState.Checked)
        sidebar._toggle_project_item_from_row_click(item)
        self.assertEqual(item.checkState(), Qt.CheckState.Unchecked)

    def test_main_window_routes_checked_text_projects_to_custom_graph_tab_selectors(self):
        from app.main_window import MainWindow

        root = Path(tempfile.mkdtemp()) / "TextOnlyProject"
        textdata = root / "TextData"
        textdata.mkdir(parents=True)
        path = textdata / "curves.txt"
        path.write_text("Time A\n0 1\n1 2\n", encoding="utf-8")
        window = MainWindow()
        window.sidebar_widget.set_projects(
            {
                "TextOnlyProject": {
                    "path": root,
                    "has_vtk": False,
                    "vtk_path": None,
                    "has_textdata": True,
                    "textdata_path": textdata,
                }
            }
        )

        window.tab_widget.setCurrentIndex(2)
        window.sidebar_widget.project_list.item(0).setCheckState(Qt.CheckState.Checked)

        tabs = window.custom_graph_tab.findChild(QTabWidget, "graphPanelTabs")
        panel = tabs.widget(0)
        project_combo = panel.findChild(QComboBox, "graphProjectCombo") or panel.project_combo
        folder_combo = panel.findChild(QComboBox, "graphFolderCombo") or panel.folder_combo
        file_combo = panel.findChild(QComboBox, "graphFileCombo") or panel.file_combo
        self.assertEqual(window.sidebar_widget.mode(), "custom_graph")
        self.assertEqual(tabs.count(), 2)
        self.assertEqual(project_combo.currentData(), "TextOnlyProject")
        self.assertEqual(folder_combo.currentText(), "TextData")
        self.assertEqual(file_combo.currentData(), str(path.resolve()))

    def test_graph_tab_selectors_add_checked_project_file_to_graph(self):
        root = Path(tempfile.mkdtemp()) / "RunA"
        textdata = root / "TextData"
        textdata.mkdir(parents=True)
        path = textdata / "curves.txt"
        path.write_text("Time A\n0 1\n1 2\n", encoding="utf-8")
        tab = CustomGraphTab()
        tab.set_projects({
            "RunA": {
                "path": root,
                "has_vtk": False,
                "vtk_path": None,
                "has_textdata": True,
                "textdata_path": textdata,
            }
        })
        tab.set_selected_project_names(["RunA"])
        panel = tab.findChild(QTabWidget, "graphPanelTabs").widget(0)

        self.assertEqual(panel.project_combo.currentData(), "RunA")
        self.assertEqual(panel.folder_combo.currentText(), "TextData")
        self.assertEqual(panel.file_combo.currentData(), str(path.resolve()))
        panel.add_file_button.click()

        self.assertEqual(panel.state()["files"], [str(path.resolve())])

    def test_graph_panel_exposes_png_download_button(self):
        panel = GraphPanelWidget(panel_number=1)

        self.assertEqual(panel.download_png_button.text(), "PNG")
        self.assertEqual(panel.download_png_button.toolTip(), "Download graph as PNG")
        self.assertFalse(panel.download_png_button.icon().isNull())

    def test_graph_panel_disambiguates_same_named_files_and_duplicate_legends(self):
        root = Path(tempfile.mkdtemp())
        paths = []
        projects = {}
        for project_name, value in [("RunA", 1), ("RunB", 2)]:
            textdata = root / project_name / "TextData"
            textdata.mkdir(parents=True)
            path = textdata / "curves.txt"
            path.write_text(f"Time A\n0 {value}\n1 {value + 1}\n", encoding="utf-8")
            paths.append(str(path.resolve()))
            projects[project_name] = {
                "path": root / project_name,
                "has_vtk": False,
                "vtk_path": None,
                "has_textdata": True,
                "textdata_path": textdata,
            }
        panel = GraphPanelWidget(panel_number=1, projects=projects, selected_project_names=["RunA", "RunB"])

        panel.add_files(paths)
        panel._column_checkboxes[(paths[0], "A")].setChecked(True)
        panel._column_checkboxes[(paths[1], "A")].setChecked(True)
        state = panel.state()

        self.assertEqual(panel._file_label(paths[0]), "RunA / TextData/curves.txt")
        self.assertEqual(panel._file_label(paths[1]), "RunB / TextData/curves.txt")
        self.assertEqual(state["column_settings"][paths[0]]["A"]["legend"], "RunA / TextData: A")
        self.assertEqual(state["column_settings"][paths[1]]["A"]["legend"], "RunB / TextData: A")

    def test_graph_panel_loads_file_columns_and_updates_state(self):
        temp_dir = Path(tempfile.mkdtemp())
        path = temp_dir / "curves.txt"
        path.write_text("Time A B\n0 1 2\n1 3 4\n", encoding="utf-8")
        tab = CustomGraphTab()
        panel = tab.add_graph_panel()

        panel.add_files([str(path)])
        check = panel._column_checkboxes[(str(path.resolve()), "A")]
        check.setChecked(True)
        state = panel.state()

        self.assertEqual(state["files"], [str(path.resolve())])
        self.assertEqual(state["x_axis_column"], "Time")
        self.assertEqual(state["columns_by_file"][str(path.resolve())], ["A"])
        self.assertEqual(panel.canvas._last_trace_count, 1)
        self.assertEqual(state["column_settings"][str(path.resolve())]["A"]["conversion"], "as-is")

    def test_graph_panel_updates_column_conversion_state(self):
        temp_dir = Path(tempfile.mkdtemp())
        path = temp_dir / "curves.txt"
        path.write_text("Time A\n0 0.1\n1 0.2\n", encoding="utf-8")
        tab = CustomGraphTab()
        panel = tab.add_graph_panel()

        panel.add_files([str(path)])
        check = panel._column_checkboxes[(str(path.resolve()), "A")]
        check.setChecked(True)
        combo = panel._conversion_combos[(str(path.resolve()), "A")]
        combo.setCurrentIndex(combo.findData("percent"))

        state = panel.state()

        self.assertEqual(state["column_settings"][str(path.resolve())]["A"]["conversion"], "percent")

    def test_graph_panel_updates_x_axis_conversion_state(self):
        tab = CustomGraphTab()
        panel = tab.add_graph_panel()

        panel.x_axis_conversion_combo.setCurrentIndex(panel.x_axis_conversion_combo.findData("sec-to-min"))
        state = panel.state()

        self.assertEqual(state["x_axis_conversion"], "sec-to-min")

    def test_graph_panel_conversion_dropdown_updates_rendered_trace_values(self):
        temp_dir = Path(tempfile.mkdtemp())
        path = temp_dir / "curves.txt"
        path.write_text("Time A\n0 0.1\n1 0.2\n", encoding="utf-8")
        tab = CustomGraphTab()
        panel = tab.add_graph_panel()

        panel.add_files([str(path)])
        check = panel._column_checkboxes[(str(path.resolve()), "A")]
        check.setChecked(True)
        combo = panel._conversion_combos[(str(path.resolve()), "A")]
        combo.setCurrentIndex(combo.findData("percent"))

        figure = panel.canvas._build_figure(panel.state())

        self.assertEqual(list(figure.data[0].y), [10, 20])

    def test_graph_panel_x_axis_conversion_updates_rendered_trace_values(self):
        temp_dir = Path(tempfile.mkdtemp())
        path = temp_dir / "curves.txt"
        path.write_text("Time A\n0 10\n60 20\n3600 30\n", encoding="utf-8")
        tab = CustomGraphTab()
        panel = tab.add_graph_panel()

        panel.add_files([str(path)])
        check = panel._column_checkboxes[(str(path.resolve()), "A")]
        check.setChecked(True)
        panel.x_axis_conversion_combo.setCurrentIndex(panel.x_axis_conversion_combo.findData("sec-to-min"))

        figure = panel.canvas._build_figure(panel.state())

        self.assertEqual(list(figure.data[0].x), [0, 1, 60])

    def test_graph_canvas_html_contains_converted_trace_values(self):
        temp_dir = Path(tempfile.mkdtemp())
        path = temp_dir / "curves.txt"
        path.write_text("Time A\n0 0.1\n1 0.2\n", encoding="utf-8")
        canvas = GraphCanvas()
        state = {
            "files": [str(path)],
            "columns_by_file": {str(path): ["A"]},
            "column_settings": {
                str(path): {
                    "A": {"legend": "A", "yaxis": "y1", "conversion": "percent"},
                }
            },
            "x_axis_column": "Time",
            "trace_mode": "lines",
            "line_style": "solid",
            "show_grid": True,
            "show_legend": True,
        }

        figure = canvas._build_figure(state)
        html = canvas._build_html(figure)

        self.assertIn('"y":[10.0,20.0]', html)

    def test_graph_canvas_applies_x_axis_time_conversion_factors(self):
        temp_dir = Path(tempfile.mkdtemp())
        path = temp_dir / "curves.txt"
        path.write_text("Time A\n0 10\n60 20\n3600 30\n", encoding="utf-8")
        canvas = GraphCanvas()
        state = {
            "files": [str(path)],
            "columns_by_file": {str(path): ["A"]},
            "column_settings": {
                str(path): {
                    "A": {"legend": "A", "yaxis": "y1", "conversion": "as-is"},
                }
            },
            "x_axis_column": "Time",
            "x_axis_conversion": "sec-to-hour",
            "trace_mode": "lines",
            "line_style": "solid",
            "show_grid": True,
            "show_legend": True,
        }

        figure = canvas._build_figure(state)

        self.assertEqual(list(figure.data[0].x), [0, 1 / 60, 1])

    def test_graph_canvas_applies_per_column_conversion_factors(self):
        temp_dir = Path(tempfile.mkdtemp())
        path = temp_dir / "curves.txt"
        path.write_text("Time AsIs Percent MPa GPa\n0 2 0.25 3000 3000\n1 4 0.5 6000 6000\n", encoding="utf-8")
        canvas = GraphCanvas()
        state = {
            "files": [str(path)],
            "columns_by_file": {str(path): ["AsIs", "Percent", "MPa", "GPa"]},
            "column_settings": {
                str(path): {
                    "AsIs": {"legend": "AsIs", "yaxis": "y1", "conversion": "as-is"},
                    "Percent": {"legend": "Percent", "yaxis": "y1", "conversion": "percent"},
                    "MPa": {"legend": "MPa", "yaxis": "y1", "conversion": "mpa"},
                    "GPa": {"legend": "GPa", "yaxis": "y1", "conversion": "gpa"},
                }
            },
            "x_axis_column": "Time",
            "trace_mode": "lines",
            "line_style": "solid",
            "show_grid": True,
            "show_legend": True,
        }

        figure = canvas._build_figure(state)

        self.assertEqual(list(figure.data[0].y), [2, 4])
        self.assertEqual(list(figure.data[1].y), [25, 50])
        self.assertEqual(list(figure.data[2].y), [3000, 6000])
        self.assertEqual(list(figure.data[3].y), [3, 6])

    def test_graph_canvas_limits_lines_plus_markers_to_15_marker_points(self):
        temp_dir = Path(tempfile.mkdtemp())
        path = temp_dir / "many_points.txt"
        rows = ["Time A"] + [f"{index} {index * 2}" for index in range(40)]
        path.write_text("\n".join(rows), encoding="utf-8")
        canvas = GraphCanvas()
        state = {
            "files": [str(path)],
            "columns_by_file": {str(path): ["A"]},
            "column_settings": {
                str(path): {
                    "A": {"legend": "A", "yaxis": "y1", "conversion": "as-is"},
                }
            },
            "x_axis_column": "Time",
            "trace_mode": "lines+markers",
            "line_style": "solid",
            "show_grid": True,
            "show_legend": True,
        }

        figure = canvas._build_figure(state)

        self.assertEqual(len(figure.data), 1)
        self.assertEqual(figure.data[0].mode, "lines+markers")
        self.assertEqual(len(figure.data[0].x), 40)
        self.assertEqual(figure.data[0].marker.size, PlotStyle.MARKER_SIZE)
        self.assertEqual(figure.data[0].marker.maxdisplayed, PlotStyle.MAX_MARKER_POINTS)
        self.assertEqual(figure.data[0].marker.line.width, 1.5)

    def test_graph_canvas_accepts_display_conversion_labels(self):
        canvas = GraphCanvas()

        self.assertEqual(canvas._conversion_multiplier("%"), 100.0)
        self.assertEqual(canvas._conversion_multiplier("GPa"), 0.001)
        self.assertEqual(canvas._conversion_multiplier("MPa"), 1.0)
        self.assertEqual(canvas._conversion_multiplier("As-is"), 1.0)

    def test_graph_panel_uses_opview_like_dimensions_and_light_scoped_widgets(self):
        tab = CustomGraphTab()
        panel = tab.add_graph_panel()

        settings = panel.findChild(QScrollArea, "graphSettingsScroll")
        top_controls = panel.findChild(QWidget, "graphTopControls")
        graph_area = panel.findChild(QWidget, "graphArea")

        self.assertIsNotNone(settings)
        self.assertEqual(settings.minimumWidth(), 280)
        self.assertEqual(settings.maximumWidth(), 720)
        panel.set_available_width(500)
        self.assertLessEqual(settings.maximumWidth(), 500)
        self.assertEqual(panel.canvas._graph_width, 800)
        self.assertEqual(panel.canvas._web_view.minimumWidth(), 800)
        self.assertEqual(panel.canvas._web_view.minimumHeight(), 0)
        self.assertIsNotNone(top_controls)
        self.assertIsNotNone(graph_area)
        self.assertEqual(panel._settings_layout.columnCount(), 2)

    def test_graph_canvas_html_reserves_exact_opview_plot_area(self):
        tab = CustomGraphTab()
        panel = tab.add_graph_panel()

        html = panel.canvas._build_html(panel.canvas._empty_figure("Preview"))

        self.assertIn("#graph{width:800px;height:620px;", html)
        self.assertIn("display:flex;align-items:flex-start;justify-content:center;", html)

    def test_graph_canvas_uses_publication_quality_axis_styling(self):
        canvas = GraphCanvas()
        figure = canvas._empty_figure("Preview")
        state = {
            "files": [],
            "show_grid": True,
            "x_axis_title": "Time",
            "yaxis1_title": "CRSS [MPa]",
            "yaxis2_title": "Stress xx [MPa]",
        }

        figure = canvas._apply_publication_axis_styling(figure, state)

        for axis in (figure.layout.xaxis, figure.layout.yaxis, figure.layout.yaxis2):
            self.assertEqual(axis.title.font.size, PlotStyle.GRAPH_AXIS_TITLE_SIZE)
            self.assertEqual(axis.title.font.family, "Arial")
            self.assertEqual(axis.tickfont.size, PlotStyle.GRAPH_TICK_FONT_SIZE)
            self.assertEqual(axis.tickfont.family, "Arial")
            self.assertEqual(axis.exponentformat, "e")
            self.assertEqual(axis.showexponent, "all")
            self.assertEqual(axis.minexponent, 4)
            self.assertEqual(axis.mirror, "allticks")
            self.assertEqual(axis.ticks, "inside")
            self.assertEqual(axis.ticklen, 10)
            self.assertEqual(axis.tickwidth, 2.5)
            self.assertEqual(axis.tickcolor, "black")
            self.assertEqual(axis.minor.ticks, "inside")
            self.assertEqual(axis.minor.ticklen, 6)
            self.assertEqual(axis.minor.tickwidth, 1.5)
            self.assertEqual(axis.minor.tickcolor, "black")
            self.assertFalse(axis.minor.showgrid)
            self.assertEqual(axis.linecolor, "black")
            self.assertEqual(axis.linewidth, 2.5)
            self.assertTrue(axis.showline)

    def test_custom_graph_selection_indicators_use_tick_mark_not_filled_block(self):
        stylesheet = build_app_stylesheet()

        self.assertIn("QGroupBox#graphSettingsSection QCheckBox::indicator:checked", stylesheet)
        self.assertIn("QFrame#graphFileSection QCheckBox::indicator:checked", stylesheet)
        self.assertIn("QGroupBox#graphSettingsSection QRadioButton::indicator", stylesheet)
        self.assertIn("QGroupBox#graphSettingsSection QRadioButton::indicator:checked", stylesheet)
        self.assertIn("checkbox-tick.svg", stylesheet)
        self.assertNotIn("QGroupBox#graphSettingsSection QCheckBox::indicator:checked {\n    background: #c50623", stylesheet)
        self.assertNotIn("QGroupBox#graphSettingsSection QCheckBox::indicator,\nQFrame#graphFileSection QCheckBox::indicator {\n    width: 18px;\n    height: 18px;\n    background: #ffffff;\n    border: 2px solid #c50623", stylesheet)
        self.assertIn("border: 2px solid #ccd7e8", stylesheet)

    def test_main_window_uses_real_custom_graph_tab(self):
        from app.main_window import MainWindow

        window = MainWindow()

        self.assertIsInstance(window.content_tabs["custom_graph"], CustomGraphTab)

    def test_main_window_allows_custom_graph_horizontal_overflow(self):
        from app.main_window import MainWindow

        window = MainWindow()
        window.resize(760, 620)
        window.tab_widget.setCurrentIndex(2)
        QApplication.processEvents()

        viewport_width = window.content_scroll.viewport().width()

        self.assertEqual(window.content_scroll.horizontalScrollBarPolicy(), Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.assertGreater(window.content_stack.maximumWidth(), viewport_width)
        self.assertGreater(window.custom_graph_tab.maximumWidth(), viewport_width)


if __name__ == "__main__":
    unittest.main()
