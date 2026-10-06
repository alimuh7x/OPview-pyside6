import os
import shutil
import tempfile
import unittest
from pathlib import Path

import plotly.graph_objects as go

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QPushButton, QScrollArea, QTabWidget, QWidget

from data.text_sources import GenericTextDataSource
from app.styles import build_app_stylesheet
from graphs.graph_canvas import GraphCanvas
from graphs.graph_animation_player import GraphAnimationPlayer
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
        self.assertEqual(
            sidebar.project_list.item(0).data(Qt.ItemDataRole.UserRole),
            "TextOnlyProject",
        )
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
        self.assertEqual(
            sidebar.project_list.item(0).data(Qt.ItemDataRole.UserRole),
            "VtkProject",
        )
        self.assertFalse(sidebar.panel_group.isHidden())
        self.assertTrue(sidebar.text_files_group.isHidden())

    def test_sidebar_dataset_display_label_omits_empty_module_label(self):
        sidebar = SidebarWidget()

        self.assertEqual(
            sidebar._dataset_display_label({"module_label": "", "label": "OtherThing"}),
            "OtherThing",
        )
        self.assertEqual(
            sidebar._dataset_display_label({"module_label": "Mechanics", "label": "Elastic"}),
            "Mechanics: Elastic",
        )

    def test_sidebar_vtk_status_counts_visible_projects_only(self):
        root = Path(tempfile.mkdtemp())
        sidebar = SidebarWidget()
        projects = {
            "DemoProject": {
                "path": root / "DemoProject",
                "has_vtk": True,
                "vtk_path": root / "DemoProject" / "VTK",
                "has_textdata": False,
                "textdata_path": None,
                "is_subdirectory": False,
            },
            "DemoProject/VTK": {
                "path": root / "DemoProject" / "VTK",
                "has_vtk": True,
                "vtk_path": root / "DemoProject" / "VTK",
                "has_textdata": False,
                "textdata_path": None,
                "is_subdirectory": True,
                "parent_folder": "DemoProject",
            },
            "OtherProject": {
                "path": root / "OtherProject",
                "has_vtk": True,
                "vtk_path": root / "OtherProject" / "VTK",
                "has_textdata": False,
                "textdata_path": None,
                "is_subdirectory": False,
            },
        }

        sidebar.set_mode("vtk")
        sidebar.set_projects(projects)

        self.assertEqual(sidebar.project_list.count(), 2)
        self.assertEqual(sidebar.project_status_label.text(), "2 project(s) found")

    def test_sidebar_project_rows_keep_native_checkbox_with_remove_delegate(self):
        root = Path(tempfile.mkdtemp())
        sidebar = SidebarWidget()
        sidebar.set_projects({
            "DemoProject": {
                "path": root / "DemoProject",
                "has_vtk": True,
                "vtk_path": root / "DemoProject" / "VTK",
                "has_textdata": False,
                "textdata_path": None,
            },
        })

        item = sidebar.project_list.item(0)
        delegate = sidebar.project_list.itemDelegate()

        self.assertEqual(item.text(), "DemoProject")
        self.assertIsNone(sidebar.project_list.itemWidget(item))
        self.assertTrue(item.flags() & Qt.ItemFlag.ItemIsUserCheckable)
        self.assertEqual(delegate.remove_button_width, 24)

    def test_sidebar_project_item_uses_native_text_and_check_state(self):
        root = Path(tempfile.mkdtemp())
        sidebar = SidebarWidget()
        sidebar.set_projects({
            "DemoProject": {
                "path": root / "DemoProject",
                "has_vtk": True,
                "vtk_path": root / "DemoProject" / "VTK",
                "has_textdata": False,
                "textdata_path": None,
            },
        })

        item = sidebar.project_list.item(0)

        self.assertEqual(item.text(), "DemoProject")
        self.assertEqual(item.data(Qt.ItemDataRole.UserRole), "DemoProject")
        self.assertEqual(item.checkState(), Qt.CheckState.Unchecked)

    def test_sidebar_project_row_reserves_space_for_remove_column(self):
        root = Path(tempfile.mkdtemp())
        sidebar = SidebarWidget()
        sidebar.set_projects({
            "DemoProject": {
                "path": root / "DemoProject",
                "has_vtk": True,
                "vtk_path": root / "DemoProject" / "VTK",
                "has_textdata": False,
                "textdata_path": None,
            },
        })

        item = sidebar.project_list.item(0)
        delegate = sidebar.project_list.itemDelegate()

        self.assertGreaterEqual(item.sizeHint().height(), delegate.remove_button_width)
        self.assertEqual(delegate.remove_button_width, 24)

    def test_sidebar_project_row_uses_native_item_and_fixed_remove_column(self):
        root = Path(tempfile.mkdtemp())
        sidebar = SidebarWidget()
        sidebar.set_projects({
            "DemoProject": {
                "path": root / "DemoProject",
                "has_vtk": True,
                "vtk_path": root / "DemoProject" / "VTK",
                "has_textdata": False,
                "textdata_path": None,
            },
        })

        item = sidebar.project_list.item(0)
        delegate = sidebar.project_list.itemDelegate()

        self.assertEqual(item.text(), "DemoProject")
        self.assertIsNone(sidebar.project_list.itemWidget(item))
        self.assertEqual(delegate.remove_button_width, 24)

    def test_sidebar_remove_button_hides_scanned_project(self):
        root = Path(tempfile.mkdtemp())
        sidebar = SidebarWidget()
        projects = {
            "DemoProject": {
                "path": root / "DemoProject",
                "has_vtk": True,
                "vtk_path": root / "DemoProject" / "VTK",
                "has_textdata": False,
                "textdata_path": None,
            },
        }
        sidebar.set_projects(projects)

        sidebar.remove_project("DemoProject")
        self.assertIn("DemoProject", projects)
        sidebar.set_projects(projects)

        self.assertEqual(sidebar.project_list.count(), 0)
        self.assertEqual(sidebar.project_status_label.text(), "0 project(s) found")

    def test_sidebar_remove_button_hides_vtk_subentry_and_parent(self):
        root = Path(tempfile.mkdtemp())
        sidebar = SidebarWidget()
        projects = {
            "DemoProject": {
                "path": root / "DemoProject",
                "has_vtk": True,
                "vtk_path": root / "DemoProject" / "VTK",
                "has_textdata": False,
                "textdata_path": None,
                "is_subdirectory": False,
            },
            "DemoProject/VTK": {
                "path": root / "DemoProject" / "VTK",
                "has_vtk": True,
                "vtk_path": root / "DemoProject" / "VTK",
                "has_textdata": False,
                "textdata_path": None,
                "is_subdirectory": True,
                "parent_folder": "DemoProject",
            },
        }
        sidebar.set_projects(projects)

        sidebar.remove_project("DemoProject/VTK")
        self.assertEqual(sidebar.project_list.count(), 0)
        sidebar.set_projects(projects)

        self.assertEqual(sidebar.project_list.count(), 0)
        self.assertEqual(sidebar.project_status_label.text(), "0 project(s) found")

    def test_sidebar_remove_button_removes_manual_project_from_reload_state(self):
        root = Path(tempfile.mkdtemp())
        sidebar = SidebarWidget()
        sidebar.add_manual_project("ManualProject", {
            "path": root / "ManualProject",
            "has_vtk": True,
            "vtk_path": root / "ManualProject",
            "has_textdata": False,
            "textdata_path": None,
        })

        sidebar.remove_project("ManualProject")

        self.assertNotIn("ManualProject", sidebar._manual_projects)
        self.assertNotIn("ManualProject", sidebar._projects)
        self.assertEqual(sidebar.project_list.count(), 0)

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

        self.assertEqual(
            sidebar.project_list.item(0).data(Qt.ItemDataRole.UserRole),
            "TextProject",
        )
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

    def test_sidebar_text_file_check_emits_add_request_without_add_button(self):
        root = Path(tempfile.mkdtemp()) / "TextOnlyProject"
        textdata = root / "TextData"
        textdata.mkdir(parents=True)
        path = textdata / "curves.txt"
        path.write_text("Time A\n0 1\n1 2\n", encoding="utf-8")
        sidebar = SidebarWidget()
        emitted: list[list[str]] = []
        sidebar.text_files_add_requested.connect(lambda files: emitted.append(files))
        sidebar.set_projects(
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

        sidebar.set_mode("custom_graph")
        sidebar.project_list.item(0).setCheckState(Qt.CheckState.Checked)
        item = sidebar.text_file_list.item(0)
        item.setCheckState(Qt.CheckState.Checked)

        self.assertFalse(hasattr(sidebar, "add_text_files_button"))
        self.assertEqual(emitted, [[str(path.resolve())]])

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

        window.tab_widget.setCurrentIndex(3)
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
        self.assertIsNone(file_combo.currentData())

    def test_main_window_adds_checked_sidebar_text_file_to_custom_graph(self):
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

        window.tab_widget.setCurrentIndex(3)
        window.sidebar_widget.project_list.item(0).setCheckState(Qt.CheckState.Checked)
        window.sidebar_widget.text_file_list.item(0).setCheckState(Qt.CheckState.Checked)

        tabs = window.custom_graph_tab.findChild(QTabWidget, "graphPanelTabs")
        panel = tabs.widget(0)
        self.assertEqual(panel.state()["files"], [str(path.resolve())])

    def test_graph_tab_selectors_wait_for_file_click_before_adding_to_graph(self):
        root = Path(tempfile.mkdtemp()) / "RunA"
        textdata = root / "TextData"
        textdata.mkdir(parents=True)
        path = textdata / "curves.txt"
        path.write_text("Time A\n0 1\n1 2\n", encoding="utf-8")
        panel = GraphPanelWidget(panel_number=1, projects={
            "RunA": {
                "path": root,
                "has_vtk": False,
                "vtk_path": None,
                "has_textdata": True,
                "textdata_path": textdata,
            }
        }, selected_project_names=["RunA"])

        self.assertEqual(panel.project_combo.currentData(), "RunA")
        self.assertEqual(panel.folder_combo.currentText(), "TextData")
        self.assertIsNone(panel.file_combo.currentData())
        self.assertEqual(panel.state()["files"], [])

        panel.file_combo.setCurrentIndex(1)

        self.assertEqual(panel.file_combo.currentData(), str(path.resolve()))
        self.assertEqual(panel.state()["files"], [str(path.resolve())])
        self.assertFalse(hasattr(panel, "add_file_button"))

    def test_graph_file_combo_shows_scrollbar_for_many_text_files(self):
        root = Path(tempfile.mkdtemp()) / "RunA"
        textdata = root / "TextData"
        textdata.mkdir(parents=True)
        for index in range(30):
            (textdata / f"curve_{index:02d}.txt").write_text("Time A\n0 1\n", encoding="utf-8")
        panel = GraphPanelWidget(panel_number=1, projects={
            "RunA": {
                "path": root,
                "has_vtk": False,
                "vtk_path": None,
                "has_textdata": True,
                "textdata_path": textdata,
            }
        }, selected_project_names=["RunA"])

        self.assertEqual(panel.file_combo.maxVisibleItems(), 12)
        self.assertEqual(panel.file_combo.view().verticalScrollBarPolicy(), Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

    def test_graph_panel_exposes_png_download_button(self):
        panel = GraphPanelWidget(panel_number=1)

        self.assertEqual(panel.download_png_button.text(), "PNG")
        self.assertEqual(panel.download_png_button.toolTip(), "Download graph as PNG")
        self.assertFalse(panel.download_png_button.icon().isNull())

    def test_graph_panel_exposes_animate_button(self):
        panel = GraphPanelWidget(panel_number=1)

        self.assertEqual(panel.download_animation_button.text(), "Animate")
        self.assertEqual(panel.download_animation_button.toolTip(), "Open reveal animation")
        self.assertFalse(panel.download_animation_button.icon().isNull())

    def test_graph_panel_exposes_settings_collapse_button(self):
        panel = GraphPanelWidget(panel_number=1)

        self.assertEqual(panel.settings_toggle_button.text(), "")
        self.assertEqual(panel.settings_toggle_button.parent().objectName(), "graphSettingsHeader")
        self.assertTrue(panel.settings_toggle_button.isCheckable())
        self.assertTrue(panel.settings_toggle_button.isChecked())
        self.assertTrue(panel.settings_toggle_button.isFlat())
        self.assertEqual(panel.settings_toggle_button.iconSize(), QSize(28, 28))
        self.assertEqual(panel.settings_toggle_button.toolTip(), "Hide settings")
        self.assertEqual(panel.settings_toggle_button.property("icon_asset"), "show_sidebar.png")
        self.assertFalse(panel.settings_toggle_button.icon().isNull())
        self.assertFalse(panel.settings_scroll.isHidden())
        self.assertTrue(panel.settings_collapsed_rail.isHidden())
        self.assertEqual(panel.settings_collapsed_label.text(), "Settings")
        self.assertNotIn("\n", panel.settings_collapsed_label.text())
        self.assertEqual(panel.settings_collapsed_label.rotation_degrees(), 90)
        self.assertGreater(panel.settings_collapsed_label.sizeHint().height(), panel.settings_collapsed_label.sizeHint().width())

    def test_graph_panel_settings_icon_collapses_to_right_rail_and_restores_settings(self):
        panel = GraphPanelWidget(panel_number=1)

        panel.settings_toggle_button.setChecked(False)

        self.assertTrue(panel.settings_scroll.isHidden())
        self.assertFalse(panel.settings_collapsed_rail.isHidden())
        self.assertTrue(panel.settings_collapsed_toggle_button.isFlat())
        self.assertEqual(panel.settings_collapsed_toggle_button.toolTip(), "Show settings")
        self.assertEqual(panel.settings_collapsed_toggle_button.property("icon_asset"), "hide_sidebar.png")
        self.assertEqual(panel.settings_collapsed_label.text(), "Settings")
        self.assertNotIn("\n", panel.settings_collapsed_label.text())

        panel.settings_collapsed_toggle_button.setChecked(True)

        self.assertFalse(panel.settings_scroll.isHidden())
        self.assertTrue(panel.settings_collapsed_rail.isHidden())
        self.assertEqual(panel.settings_toggle_button.toolTip(), "Hide settings")
        self.assertEqual(panel.settings_toggle_button.property("icon_asset"), "show_sidebar.png")

    def test_graph_panel_opens_animation_player_with_copied_state(self):
        temp_dir = Path(tempfile.mkdtemp())
        path = temp_dir / "curves.txt"
        path.write_text("Time A\n0 1\n1 2\n", encoding="utf-8")
        panel = GraphPanelWidget(panel_number=3)
        panel.add_files([str(path)])
        panel._column_checkboxes[(str(path.resolve()), "A")].setChecked(True)
        opened = []

        class FakeAnimationPlayer:
            def __init__(self, state, panel_number, parent=None):
                opened.append((state, panel_number, parent))

            def show(self):
                opened.append("show")

        panel._animation_player_class = FakeAnimationPlayer

        panel._open_animation_player()

        self.assertEqual(opened[0][1], 3)
        self.assertIs(opened[0][2], panel)
        self.assertEqual(opened[0][0]["files"], [str(path.resolve())])
        self.assertEqual(opened[0][0]["columns_by_file"][str(path.resolve())], ["A"])
        self.assertIsNot(opened[0][0], panel.state())
        self.assertEqual(opened[1], "show")

    def test_graph_panel_reuses_visible_animation_player(self):
        panel = GraphPanelWidget(panel_number=3)
        calls = []

        class FakeAnimationPlayer:
            def __init__(self, state, panel_number, parent=None):
                calls.append(("init", panel_number, parent))

            def isVisible(self):
                return True

            def raise_(self):
                calls.append("raise")

            def activateWindow(self):
                calls.append("activate")

            def show(self):
                calls.append("show")

        panel._animation_player_class = FakeAnimationPlayer

        panel._open_animation_player()
        panel._open_animation_player()

        self.assertEqual(calls.count("show"), 1)
        self.assertEqual(calls.count("raise"), 1)
        self.assertEqual(calls.count("activate"), 1)
        self.assertEqual(len([call for call in calls if isinstance(call, tuple) and call[0] == "init"]), 1)

    def test_graph_animation_player_builds_reveal_frames_from_graph_settings(self):
        temp_dir = Path(tempfile.mkdtemp())
        path = temp_dir / "curves.txt"
        path.write_text("Time A B\n0 1 10\n1 2 20\n2 3 30\n", encoding="utf-8")
        state = {
            "files": [str(path)],
            "columns_by_file": {str(path): ["A", "B"]},
            "column_settings": {
                str(path): {
                    "A": {"legend": "Alpha", "yaxis": "y1", "conversion": "percent", "color": "#111111"},
                    "B": {"legend": "Beta", "yaxis": "y2", "conversion": "as-is", "color": "#d62728"},
                }
            },
            "x_axis_column": "Time",
            "x_axis_conversion": "as-is",
            "x_axis_title": "Time",
            "yaxis1_title": "Y1",
            "yaxis2_title": "Y2",
            "trace_mode": "lines",
            "line_style": "dash",
            "show_grid": True,
            "show_legend": True,
            "legend_position": "top-left",
        }

        figure = GraphAnimationPlayer.build_reveal_figure(state)

        self.assertEqual(len(figure.frames), 3)
        self.assertEqual(list(figure.frames[0].data[0].x), [0, 1])
        self.assertEqual(list(figure.frames[0].data[0].y), [100, 200])
        self.assertEqual(list(figure.frames[1].data[0].x), [0, 1])
        self.assertEqual(list(figure.frames[-1].data[1].y), [10, 20, 30])
        self.assertEqual(figure.data[0].name, "Alpha")
        self.assertEqual(figure.data[1].yaxis, "y2")
        self.assertEqual(figure.layout.xaxis.title.text, "Time")

    def test_graph_animation_player_locks_ranges_to_final_graph(self):
        temp_dir = Path(tempfile.mkdtemp())
        path = temp_dir / "curves.txt"
        path.write_text("Time A B\n0 10 100\n1 20 200\n2 30 300\n", encoding="utf-8")
        state = {
            "files": [str(path)],
            "columns_by_file": {str(path): ["A", "B"]},
            "column_settings": {
                str(path): {
                    "A": {"legend": "Alpha", "yaxis": "y1", "conversion": "as-is", "color": "#111111"},
                    "B": {"legend": "Beta", "yaxis": "y2", "conversion": "as-is", "color": "#d62728"},
                }
            },
            "x_axis_column": "Time",
            "x_axis_conversion": "as-is",
            "x_axis_title": "Time",
            "yaxis1_title": "Y1",
            "yaxis2_title": "Y2",
            "trace_mode": "lines",
            "line_style": "solid",
            "show_grid": True,
            "show_legend": True,
            "legend_position": "top-left",
        }

        figure = GraphAnimationPlayer.build_reveal_figure(state)
        preview = GraphAnimationPlayer.preview_figure_for_frame(figure, 0)

        self.assertEqual(list(preview.layout.xaxis.range), [-0.1, 2.1])
        self.assertEqual(list(preview.layout.yaxis.range), [10, 30])
        self.assertEqual(list(preview.layout.yaxis2.range), [100, 300])

    def test_graph_animation_player_caps_large_reveal_frame_count(self):
        temp_dir = Path(tempfile.mkdtemp())
        path = temp_dir / "curves.txt"
        rows = ["Time A"]
        rows.extend(f"{index} {index * 2}" for index in range(1000))
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        state = {
            "files": [str(path)],
            "columns_by_file": {str(path): ["A"]},
            "column_settings": {
                str(path): {
                    "A": {"legend": "Alpha", "yaxis": "y1", "conversion": "as-is", "color": "#111111"},
                }
            },
            "x_axis_column": "Time",
            "x_axis_conversion": "as-is",
            "x_axis_title": "Time",
            "yaxis1_title": "Y1",
            "yaxis2_title": "Y2",
            "trace_mode": "lines",
            "line_style": "solid",
            "show_grid": True,
            "show_legend": True,
            "legend_position": "top-left",
        }

        figure = GraphAnimationPlayer.build_reveal_figure(state)

        self.assertLessEqual(len(figure.frames), 120)
        self.assertEqual(list(figure.frames[-1].data[0].x)[-1], 999)
        self.assertEqual(list(figure.frames[-1].data[0].y)[-1], 1998)

    def test_graph_animation_player_downsamples_large_traces_to_1000_points(self):
        temp_dir = Path(tempfile.mkdtemp())
        path = temp_dir / "curves.txt"
        rows = ["Time A"]
        rows.extend(f"{index} {index * 2}" for index in range(1000))
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        state = {
            "files": [str(path)],
            "columns_by_file": {str(path): ["A"]},
            "column_settings": {
                str(path): {
                    "A": {"legend": "Alpha", "yaxis": "y1", "conversion": "as-is", "color": "#111111"},
                }
            },
            "x_axis_column": "Time",
            "x_axis_conversion": "as-is",
            "x_axis_title": "Time",
            "yaxis1_title": "Y1",
            "yaxis2_title": "Y2",
            "trace_mode": "lines",
            "line_style": "solid",
            "show_grid": True,
            "show_legend": True,
            "legend_position": "top-left",
        }

        figure = GraphAnimationPlayer.build_reveal_figure(state)
        final_trace = figure.frames[-1].data[0]

        self.assertEqual(len(final_trace.x), 1000)
        self.assertEqual(list(final_trace.x)[0], 0)
        self.assertEqual(list(final_trace.y)[0], 0)
        self.assertEqual(list(final_trace.x)[-1], 999)
        self.assertEqual(list(final_trace.y)[-1], 1998)

    def test_graph_animation_player_interpolates_large_reveal_frames_for_smooth_motion(self):
        temp_dir = Path(tempfile.mkdtemp())
        path = temp_dir / "curves.txt"
        rows = ["Time A"]
        rows.extend(f"{index} {index * 2}" for index in range(1000))
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        state = {
            "files": [str(path)],
            "columns_by_file": {str(path): ["A"]},
            "column_settings": {
                str(path): {
                    "A": {"legend": "Alpha", "yaxis": "y1", "conversion": "as-is", "color": "#111111"},
                }
            },
            "x_axis_column": "Time",
            "x_axis_conversion": "as-is",
            "x_axis_title": "Time",
            "yaxis1_title": "Y1",
            "yaxis2_title": "Y2",
            "trace_mode": "lines",
            "line_style": "solid",
            "show_grid": True,
            "show_legend": True,
            "legend_position": "top-left",
        }

        figure = GraphAnimationPlayer.build_reveal_figure(state)
        first_frame_x = list(figure.frames[1].data[0].x)
        first_frame_y = list(figure.frames[1].data[0].y)

        self.assertNotEqual(first_frame_x[-1], int(first_frame_x[-1]))
        self.assertAlmostEqual(first_frame_y[-1], first_frame_x[-1] * 2)

    def test_graph_animation_player_reveals_by_visual_arc_length_for_stress_strain(self):
        temp_dir = Path(tempfile.mkdtemp())
        path = temp_dir / "stress_strain.txt"
        path.write_text("Strain Stress\n0.0 0\n0.01 1000\n1.0 1100\n", encoding="utf-8")
        state = {
            "files": [str(path)],
            "columns_by_file": {str(path): ["Stress"]},
            "column_settings": {
                str(path): {
                    "Stress": {"legend": "Stress", "yaxis": "y1", "conversion": "as-is", "color": "#111111"},
                }
            },
            "x_axis_column": "Strain",
            "x_axis_conversion": "as-is",
            "x_axis_title": "Strain",
            "yaxis1_title": "Stress",
            "yaxis2_title": "Y2",
            "trace_mode": "lines",
            "line_style": "solid",
            "show_grid": True,
            "show_legend": True,
            "legend_position": "top-left",
        }

        figure = GraphAnimationPlayer.build_reveal_figure(state)
        middle_trace = figure.frames[1].data[0]

        self.assertGreater(list(middle_trace.x)[-1], 0.01)
        self.assertLess(list(middle_trace.x)[-1], 0.1)
        self.assertGreater(list(middle_trace.y)[-1], 1000)

    def test_graph_animation_player_reveals_markers_progressively(self):
        trace = go.Scatter(
            x=[0, 1, 2, 3],
            y=[0, 1, 2, 3],
            mode="markers",
            name="Markers",
        )

        prefix = GraphAnimationPlayer._trace_prefix(trace, 0.5)

        self.assertEqual(prefix.mode, "markers")
        self.assertEqual(list(prefix.x), [0, 1])
        self.assertEqual(list(prefix.y), [0, 1])

    def test_graph_animation_player_hides_line_markers_until_final_frame(self):
        trace = go.Scatter(
            x=[0, 1, 2, 3],
            y=[0, 1, 2, 3],
            mode="lines+markers",
            name="Line Markers",
        )

        middle_prefix = GraphAnimationPlayer._trace_prefix(trace, 0.5)
        final_prefix = GraphAnimationPlayer._trace_prefix(trace, 1.0)

        self.assertEqual(middle_prefix.mode, "lines")
        self.assertEqual(final_prefix.mode, "lines+markers")
        self.assertEqual(list(final_prefix.x), [0, 1, 2, 3])

    def test_graph_animation_player_animates_sampled_marker_trace_for_lines_plus_markers(self):
        temp_dir = Path(tempfile.mkdtemp())
        path = temp_dir / "curves.txt"
        path.write_text("Time A\n0 0\n1 1\n2 2\n3 3\n", encoding="utf-8")
        state = {
            "files": [str(path)],
            "columns_by_file": {str(path): ["A"]},
            "column_settings": {
                str(path): {
                    "A": {"legend": "Alpha", "yaxis": "y1", "conversion": "as-is", "color": "#111111"},
                }
            },
            "x_axis_column": "Time",
            "x_axis_conversion": "as-is",
            "x_axis_title": "Time",
            "yaxis1_title": "Y1",
            "yaxis2_title": "Y2",
            "trace_mode": "lines+markers",
            "line_style": "solid",
            "show_grid": True,
            "show_legend": True,
            "legend_position": "top-left",
        }

        figure = GraphAnimationPlayer.build_reveal_figure(state)

        self.assertEqual(len(figure.frames[1].data), 2)
        self.assertEqual(figure.frames[1].data[0].mode, "lines")
        self.assertEqual(figure.frames[1].data[1].mode, "markers")
        self.assertEqual(figure.frames[-1].data[1].showlegend, False)

    def test_graph_animation_player_defers_frame_build_until_prepare(self):
        original_build = GraphAnimationPlayer.build_reveal_figure
        calls = []
        player = None

        def fake_build(state):
            calls.append(state)
            return go.Figure(frames=[go.Frame(data=[go.Scatter(x=[0, 1], y=[0, 1])])])

        GraphAnimationPlayer.build_reveal_figure = staticmethod(fake_build)
        try:
            player = GraphAnimationPlayer({"files": ["slow.txt"]}, panel_number=1)
            self.assertEqual(calls, [])
            self.assertEqual(player._frame_count, 0)

            player._prepare_animation_preview()

            self.assertEqual(len(calls), 1)
            self.assertEqual(player._frame_count, 1)
        finally:
            GraphAnimationPlayer.build_reveal_figure = original_build
            if player is not None:
                player.deleteLater()

    def test_graph_animation_player_opens_with_stable_dialog_size(self):
        player = None
        try:
            player = GraphAnimationPlayer({}, panel_number=1)

            self.assertGreaterEqual(player.minimumWidth(), 940)
            self.assertGreaterEqual(player.minimumHeight(), 760)
            self.assertFalse(player._preview_html_loaded)
        finally:
            if player is not None:
                player.deleteLater()

    def test_graph_animation_player_has_no_stop_button(self):
        player = None
        try:
            player = GraphAnimationPlayer({}, panel_number=1)

            self.assertFalse(hasattr(player, "_stop_btn"))
        finally:
            if player is not None:
                player.deleteLater()

    def test_graph_animation_player_play_restarts_from_final_frame(self):
        player = None
        try:
            player = GraphAnimationPlayer({}, panel_number=1)
            player._frame_count = 3
            player._current = 2
            calls = []
            player._show_frame = lambda index: calls.append(index)

            player._start_play()

            self.assertEqual(calls, [0])
            self.assertTrue(player._playing)
        finally:
            if player is not None:
                player.deleteLater()

    def test_graph_animation_player_defaults_to_fast_smooth_fps(self):
        player = None
        try:
            player = GraphAnimationPlayer({}, panel_number=1)

            self.assertEqual(player._fps, 30)
            self.assertEqual(player._fps_combo.currentData(), 30)
        finally:
            if player is not None:
                player.deleteLater()

    def test_graph_animation_player_defers_initial_preview_until_show_event(self):
        original_show_frame = GraphAnimationPlayer._show_frame
        calls = []
        player = None

        def fake_show_frame(self, index):
            calls.append(index)

        GraphAnimationPlayer._show_frame = fake_show_frame
        try:
            player = GraphAnimationPlayer({}, panel_number=1)
            self.assertEqual(calls, [])

            player.showEvent(None)

            self.assertEqual(calls, [])
        finally:
            GraphAnimationPlayer._show_frame = original_show_frame
            if player is not None:
                player.deleteLater()

    def test_graph_animation_player_creates_standalone_preview_frame(self):
        temp_dir = Path(tempfile.mkdtemp())
        path = temp_dir / "curves.txt"
        path.write_text("Time A\n0 1\n1 2\n2 3\n", encoding="utf-8")
        state = {
            "files": [str(path)],
            "columns_by_file": {str(path): ["A"]},
            "column_settings": {
                str(path): {
                    "A": {"legend": "Alpha", "yaxis": "y1", "conversion": "as-is", "color": "#111111"},
                }
            },
            "x_axis_column": "Time",
            "x_axis_conversion": "as-is",
            "x_axis_title": "Time",
            "yaxis1_title": "Y1",
            "yaxis2_title": "Y2",
            "trace_mode": "lines",
            "line_style": "solid",
            "show_grid": True,
            "show_legend": True,
            "legend_position": "top-left",
        }
        figure = GraphAnimationPlayer.build_reveal_figure(state)

        preview = GraphAnimationPlayer.preview_figure_for_frame(figure, 1)

        self.assertIsNot(preview, figure)
        self.assertEqual(list(preview.data[0].x), [0, 1])
        self.assertEqual(list(preview.data[0].y), [1, 2])
        self.assertEqual(len(figure.frames), 3)

    def test_graph_animation_player_preview_html_uses_static_graph_render_path(self):
        figure = GraphAnimationPlayer.build_reveal_figure({})
        player = GraphAnimationPlayer.__new__(GraphAnimationPlayer)

        html = player._build_html(figure)

        self.assertIn("Plotly.newPlot('graph'", html)
        self.assertNotIn("Plotly.addFrames", html)
        self.assertIn("OPVIEW_SHOW_FRAME", html)
        self.assertIn("displayModeBar:false", html)
        self.assertNotIn("displayModeBar:true", html)

    def test_graph_animation_player_updates_existing_preview_without_reloading_html(self):
        class FakeWebView:
            def __init__(self):
                self.html_calls = []
                self.js_calls = []

            def setHtml(self, html, base_url):
                self.html_calls.append((html, base_url))

            def page(self):
                return self

            def runJavaScript(self, script):
                self.js_calls.append(script)

        class FakeSlider:
            def blockSignals(self, blocked):
                pass

            def setValue(self, value):
                self.value = value

        class FakeLabel:
            def setText(self, text):
                self.text = text

        temp_dir = Path(tempfile.mkdtemp())
        path = temp_dir / "curves.txt"
        path.write_text("Time A\n0 1\n1 2\n2 3\n", encoding="utf-8")
        state = {
            "files": [str(path)],
            "columns_by_file": {str(path): ["A"]},
            "column_settings": {
                str(path): {
                    "A": {"legend": "Alpha", "yaxis": "y1", "conversion": "as-is", "color": "#111111"},
                }
            },
            "x_axis_column": "Time",
            "x_axis_conversion": "as-is",
            "x_axis_title": "Time",
            "yaxis1_title": "Y1",
            "yaxis2_title": "Y2",
            "trace_mode": "lines",
            "line_style": "solid",
            "show_grid": True,
            "show_legend": True,
            "legend_position": "top-left",
        }
        player = GraphAnimationPlayer.__new__(GraphAnimationPlayer)
        player._figure = GraphAnimationPlayer.build_reveal_figure(state)
        player._frame_count = len(player._figure.frames)
        player._current = 0
        player._base_url = None
        player._preview_html_loaded = False
        player._web_view = FakeWebView()
        player._slider = FakeSlider()
        player._frame_label = FakeLabel()
        player._status_label = FakeLabel()

        player._show_frame(0)
        player._show_frame(1)

        self.assertEqual(len(player._web_view.html_calls), 1)
        self.assertEqual(len(player._web_view.js_calls), 1)
        self.assertIn("OPVIEW_SHOW_FRAME(1)", player._web_view.js_calls[0])

    def test_graph_animation_player_does_not_add_duplicate_plotly_controls(self):
        temp_dir = Path(tempfile.mkdtemp())
        path = temp_dir / "curves.txt"
        path.write_text("Time A\n0 1\n1 2\n2 3\n", encoding="utf-8")
        state = {
            "files": [str(path)],
            "columns_by_file": {str(path): ["A"]},
            "column_settings": {
                str(path): {
                    "A": {"legend": "Alpha", "yaxis": "y1", "conversion": "as-is", "color": "#111111"},
                }
            },
            "x_axis_column": "Time",
            "x_axis_conversion": "as-is",
            "x_axis_title": "Time",
            "yaxis1_title": "Y1",
            "yaxis2_title": "Y2",
            "trace_mode": "lines",
            "line_style": "solid",
            "show_grid": True,
            "show_legend": True,
            "legend_position": "top-left",
        }

        figure = GraphAnimationPlayer.build_reveal_figure(state)

        self.assertFalse(figure.layout.updatemenus)
        self.assertFalse(figure.layout.sliders)

    def test_graph_animation_player_mp4_export_uses_web_view_capture(self):
        player = GraphAnimationPlayer.__new__(GraphAnimationPlayer)
        calls = []

        def fake_capture(path):
            calls.append(path)

        player._write_mp4_from_web_view = fake_capture

        player._write_mp4(Path("graph.mp4"))

        self.assertEqual(calls, [Path("graph.mp4")])

    def test_graph_animation_player_encoder_check_uses_ffmpeg_command(self):
        original_which = shutil.which
        try:
            shutil.which = lambda command: "/usr/bin/ffmpeg" if command == "ffmpeg" else None
            player = GraphAnimationPlayer.__new__(GraphAnimationPlayer)

            self.assertEqual(player._mp4_encoder_error(), "")
        finally:
            shutil.which = original_which

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

    def test_graph_panel_legend_edit_renders_only_after_editing_finished(self):
        temp_dir = Path(tempfile.mkdtemp())
        path = temp_dir / "curves.txt"
        path.write_text("Time A\n0 1\n1 2\n", encoding="utf-8")
        tab = CustomGraphTab()
        panel = tab.add_graph_panel()

        panel.add_files([str(path)])
        resolved = str(path.resolve())
        panel._column_checkboxes[(resolved, "A")].setChecked(True)
        render_calls = []
        panel.canvas.render = lambda state: render_calls.append(state)

        legend = panel._legend_edits[(resolved, "A")]
        legend.setText("Alpha")

        self.assertEqual(render_calls, [])

        legend.editingFinished.emit()

        self.assertEqual(len(render_calls), 1)
        self.assertEqual(panel.state()["column_settings"][resolved]["A"]["legend"], "Alpha")

    def test_graph_panel_axis_title_edits_render_only_after_editing_finished(self):
        tab = CustomGraphTab()
        panel = tab.add_graph_panel()
        render_calls = []
        panel.canvas.render = lambda state: render_calls.append(state)

        panel.x_title_edit.setText("Simulation Time")
        panel.y1_title_edit.setText("Stress")
        panel.y2_title_edit.setText("Strain")

        self.assertEqual(render_calls, [])

        panel.x_title_edit.editingFinished.emit()
        panel.y1_title_edit.editingFinished.emit()
        panel.y2_title_edit.editingFinished.emit()

        self.assertEqual(len(render_calls), 3)
        self.assertEqual(panel.state()["x_axis_title"], "Simulation Time")
        self.assertEqual(panel.state()["yaxis1_title"], "Stress")
        self.assertEqual(panel.state()["yaxis2_title"], "Strain")

    def test_graph_panel_updates_x_axis_conversion_state(self):
        tab = CustomGraphTab()
        panel = tab.add_graph_panel()

        panel.x_axis_conversion_combo.setCurrentIndex(panel.x_axis_conversion_combo.findData("sec-to-min"))
        state = panel.state()

        self.assertEqual(state["x_axis_conversion"], "sec-to-min")

    def test_graph_panel_x_axis_conversion_combo_includes_percent(self):
        panel = GraphPanelWidget(panel_number=1)

        panel.x_axis_conversion_combo.setCurrentIndex(panel.x_axis_conversion_combo.findData("percent"))
        state = panel.state()

        self.assertEqual(state["x_axis_conversion"], "percent")

    def test_graph_panel_conversion_dropdown_includes_log10(self):
        temp_dir = Path(tempfile.mkdtemp())
        path = temp_dir / "curves.txt"
        path.write_text("Time A\n0 1\n1 10\n", encoding="utf-8")
        panel = GraphPanelWidget(panel_number=1)

        panel.add_files([str(path)])
        resolved = str(path.resolve())
        panel._column_checkboxes[(resolved, "A")].setChecked(True)
        combo = panel._conversion_combos[(resolved, "A")]

        self.assertGreaterEqual(combo.findData("log10"), 0)

    def test_graph_panel_x_axis_conversion_combo_includes_log10(self):
        panel = GraphPanelWidget(panel_number=1)

        panel.x_axis_conversion_combo.setCurrentIndex(panel.x_axis_conversion_combo.findData("log10"))
        state = panel.state()

        self.assertEqual(state["x_axis_conversion"], "log10")

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

    def test_graph_canvas_applies_x_axis_percent_conversion(self):
        temp_dir = Path(tempfile.mkdtemp())
        path = temp_dir / "curves.txt"
        path.write_text("Strain A\n0.0 10\n0.25 20\n0.5 30\n", encoding="utf-8")
        canvas = GraphCanvas()
        state = {
            "files": [str(path)],
            "columns_by_file": {str(path): ["A"]},
            "column_settings": {
                str(path): {
                    "A": {"legend": "A", "yaxis": "y1", "conversion": "as-is"},
                }
            },
            "x_axis_column": "Strain",
            "x_axis_conversion": "percent",
            "trace_mode": "lines",
            "line_style": "solid",
            "show_grid": True,
            "show_legend": True,
        }

        figure = canvas._build_figure(state)

        self.assertEqual(list(figure.data[0].x), [0, 25, 50])

    def test_graph_canvas_applies_x_axis_log10_conversion(self):
        temp_dir = Path(tempfile.mkdtemp())
        path = temp_dir / "curves.txt"
        path.write_text("Time A\n1 10\n10 20\n100 30\n", encoding="utf-8")
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
            "x_axis_conversion": "log10",
            "trace_mode": "lines",
            "line_style": "solid",
            "show_grid": True,
            "show_legend": True,
        }

        figure = canvas._build_figure(state)

        self.assertEqual(list(figure.data[0].x), [0, 1, 2])

    def test_graph_canvas_applies_column_log10_conversion(self):
        temp_dir = Path(tempfile.mkdtemp())
        path = temp_dir / "curves.txt"
        path.write_text("Time A\n0 1\n1 10\n2 100\n", encoding="utf-8")
        canvas = GraphCanvas()
        state = {
            "files": [str(path)],
            "columns_by_file": {str(path): ["A"]},
            "column_settings": {
                str(path): {
                    "A": {"legend": "A", "yaxis": "y1", "conversion": "log10"},
                }
            },
            "x_axis_column": "Time",
            "trace_mode": "lines",
            "line_style": "solid",
            "show_grid": True,
            "show_legend": True,
        }

        figure = canvas._build_figure(state)

        self.assertEqual(list(figure.data[0].y), [0, 1, 2])

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

    def test_graph_panel_legend_position_combo_includes_middle_positions(self):
        panel = GraphPanelWidget(panel_number=1)
        combo = panel.legend_position_combo

        self.assertGreaterEqual(combo.findData("middle-right"), 0)
        self.assertGreaterEqual(combo.findData("middle-top"), 0)
        self.assertGreaterEqual(combo.findData("middle-left"), 0)
        self.assertGreaterEqual(combo.findData("middle-bottom"), 0)

    def test_graph_canvas_maps_middle_legend_positions_to_plotly_anchors(self):
        canvas = GraphCanvas()

        middle_right = canvas._legend_config("middle-right")
        middle_top = canvas._legend_config("middle-top")

        self.assertEqual(middle_right["x"], 0.98)
        self.assertEqual(middle_right["y"], 0.5)
        self.assertEqual(middle_right["xanchor"], "right")
        self.assertEqual(middle_right["yanchor"], "middle")
        self.assertEqual(middle_top["x"], 0.5)
        self.assertEqual(middle_top["y"], 0.98)
        self.assertEqual(middle_top["xanchor"], "center")
        self.assertEqual(middle_top["yanchor"], "top")

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

    def test_graph_canvas_lines_plus_markers_uses_full_line_and_20_sampled_markers(self):
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

        self.assertEqual(len(figure.data), 2)
        self.assertEqual(figure.data[0].mode, "lines")
        self.assertEqual(len(figure.data[0].x), 40)
        self.assertEqual(figure.data[0].name, "A")
        self.assertEqual(figure.data[1].mode, "markers")
        self.assertEqual(len(figure.data[1].x), 20)
        self.assertEqual(figure.data[1].showlegend, False)
        self.assertEqual(figure.data[1].marker.size, PlotStyle.MARKER_SIZE)
        self.assertEqual(figure.data[1].marker.line.width, 1.5)

    def test_graph_canvas_lines_mode_pads_x_axis_range(self):
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
            "trace_mode": "lines",
            "line_style": "solid",
            "show_grid": True,
            "show_legend": True,
        }

        figure = canvas._build_figure(state)

        self.assertEqual(list(figure.layout.xaxis.range), [-1.9500000000000002, 40.95])
        self.assertFalse(figure.layout.xaxis.autorange)

    def test_graph_canvas_lines_plus_markers_keeps_x_axis_autorange(self):
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

        self.assertIsNone(figure.layout.xaxis.range)
        self.assertIsNone(figure.layout.xaxis.autorange)

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

    def test_custom_graph_combo_dropdown_items_have_hover_style(self):
        stylesheet = build_app_stylesheet()

        self.assertIn("QComboBox#graphCombo QAbstractItemView::item:hover", stylesheet)
        self.assertIn("QComboBox#graphCombo QAbstractItemView::item:selected", stylesheet)
        self.assertIn("background: #1e4a8a;\n    color: #ffffff;", stylesheet)

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
        self.assertIn("QPushButton#graphSettingsToggleButton,\nQPushButton#graphSettingsCollapsedToggleButton", stylesheet)
        self.assertIn("background: transparent;\n    border: none;\n    padding: 0px;", stylesheet)
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
        window.tab_widget.setCurrentIndex(3)
        QApplication.processEvents()

        viewport_width = window.content_scroll.viewport().width()

        self.assertEqual(window.content_scroll.horizontalScrollBarPolicy(), Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.assertGreater(window.content_stack.maximumWidth(), viewport_width)
        self.assertGreater(window.custom_graph_tab.maximumWidth(), viewport_width)


if __name__ == "__main__":
    unittest.main()
