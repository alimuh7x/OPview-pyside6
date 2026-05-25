import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import numpy as np
    from PySide6.QtWidgets import QApplication, QHBoxLayout
    from multi_view.multi_view_cell import MultiViewCell
    from multi_view.multi_view_panel import MultiViewPanel
except ModuleNotFoundError as exc:
    QApplication = None
    QHBoxLayout = None
    np = None
    MultiViewCell = None
    MultiViewPanel = None
    MISSING_DEPENDENCY = exc.name
else:
    MISSING_DEPENDENCY = None


@unittest.skipIf(MISSING_DEPENDENCY is not None, f"missing dependency: {MISSING_DEPENDENCY}")
class MultiViewImprovementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if QApplication is not None:
            cls._app = QApplication.instance() or QApplication([])

    def test_phase_overlay_file_uses_matching_phasefield_timestep(self):
        with tempfile.TemporaryDirectory() as tmp:
            vtk_dir = Path(tmp)
            source = vtk_dir / "ElasticStrains_00005000.vts"
            phase = vtk_dir / "PhaseField_00005000.vts"
            source.write_text("", encoding="utf-8")
            phase.write_text("", encoding="utf-8")

            self.assertEqual(MultiViewPanel._phase_overlay_file(str(source)), phase)

    def test_phase_overlay_file_returns_current_phasefield_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            phase = Path(tmp) / "PhaseField_00005000.vts"
            phase.write_text("", encoding="utf-8")

            self.assertEqual(MultiViewPanel._phase_overlay_file(str(phase)), phase)

    def test_overlay_mask_keeps_only_interface_band(self):
        z_grid = np.array([[0.0, 1.5, 2.0], [3.5, 4.0, np.nan]])

        mask = MultiViewCell._build_overlay_mask(z_grid)

        expected = np.array([[np.nan, 1.0, 1.0], [1.0, np.nan, np.nan]])
        np.testing.assert_equal(mask, expected)

    def test_multiview_colorbar_is_wide_enough_for_title(self):
        from multi_view.colorbar_canvas import _W

        self.assertGreaterEqual(_W, 140)

    def test_export_size_includes_headers_and_colorbar(self):
        size = MultiViewPanel._export_image_size(
            cell_widths=[400, 400, 400],
            cell_height=420,
            colorbar_width=90,
            header_height=30,
            logo_width=58,
            spacing=8,
        )

        self.assertEqual(size, (1380, 450))

    def test_range_spin_boxes_have_90px_minimum_width(self):
        panel = MultiViewPanel({"label": "demo", "available_projects": []})

        self.assertEqual(panel.range_min.minimumWidth(), 90)
        self.assertEqual(panel.range_max.minimumWidth(), 90)

    def test_top_control_settings_use_two_visual_rows(self):
        panel = MultiViewPanel({"label": "demo", "available_projects": []})
        root_layout = panel.layout()
        first_control_card = root_layout.itemAt(0).widget()
        second_control_card = root_layout.itemAt(1).widget()

        self.assertIsInstance(first_control_card.layout(), QHBoxLayout)
        self.assertIsInstance(second_control_card.layout(), QHBoxLayout)

    def test_multiview_tab_and_panel_attach_to_upper_tabs(self):
        from multi_view.multi_view_tab import MultiViewTab

        tab = MultiViewTab()
        panel = MultiViewPanel({"label": "demo", "available_projects": []})

        margins = panel.layout().contentsMargins()

        self.assertEqual(tab.layout().spacing(), 0)
        self.assertEqual(margins.left(), 0)
        self.assertEqual(margins.top(), 0)
        self.assertEqual(margins.right(), 8)
        self.assertEqual(margins.bottom(), 8)

    def test_analysis_tools_use_one_visual_row(self):
        panel = MultiViewPanel({"label": "demo", "available_projects": []})

        self.assertIsInstance(panel.analysis_card.layout(), QHBoxLayout)

    def test_full_scale_is_off_by_default(self):
        panel = MultiViewPanel({"label": "demo", "available_projects": []})

        self.assertFalse(panel.full_scale.isChecked())

    def test_interfaces_overlay_is_last_in_third_control_row(self):
        panel = MultiViewPanel({"label": "demo", "available_projects": []})
        control_card = panel.layout().itemAt(1).widget()
        third_row = control_card.layout().itemAt(1).layout()

        self.assertIs(third_row.itemAt(third_row.count() - 1).widget(), panel.interfaces_on)

    def test_selected_scalar_def_falls_back_to_first_scalar(self):
        panel = MultiViewPanel.__new__(MultiViewPanel)
        panel._scalar_defs = [
            {"label": "PhaseFields", "value": "phase", "array": "PhaseFields"},
            {"label": "Interfaces", "value": "interfaces", "array": "Interfaces"},
        ]
        panel.scalar_combo = _ComboStub("missing")

        scalar_def = MultiViewPanel._selected_scalar_def(panel)

        self.assertEqual(scalar_def["value"], "phase")

    def test_display_params_use_custom_label_and_unit_scale(self):
        panel = MultiViewPanel.__new__(MultiViewPanel)
        panel.colorbar_label_edit = _LineEditStub("Stress")
        panel.unit_scale_combo = _ComboStub((1e-9, "GPa"))

        scale, label = MultiViewPanel._get_display_params(panel, "sigma_xx", "MPa")

        self.assertEqual(scale, 1e-9)
        self.assertEqual(label, "Stress (GPa)")

    def test_raw_display_params_do_not_auto_append_config_units(self):
        panel = MultiViewPanel.__new__(MultiViewPanel)
        panel.colorbar_label_edit = _LineEditStub("")
        panel.unit_scale_combo = _ComboStub((1.0, ""))

        scale, label = MultiViewPanel._get_display_params(panel, "CRSS 0", "MPa")

        self.assertEqual(scale, 1.0)
        self.assertEqual(label, "CRSS 0")

    def test_multiview_scalar_defs_are_raw_by_default(self):
        dataset_info = {
            "available_projects": [
                {
                    "dataset_config": {
                        "scale": 1e-6,
                        "units": "MPa",
                        "scalars": [
                            {"label": "CRSS 0", "array": "CRSS_0_0", "scale": 1e-6, "units": "MPa"}
                        ],
                    }
                }
            ]
        }

        scalar_defs = MultiViewPanel._build_scalar_defs(dataset_info)

        self.assertEqual(scalar_defs[0]["scale"], 1.0)
        self.assertIsNone(scalar_defs[0]["units"])

    def test_nearest_grid_value_uses_clicked_coordinates(self):
        x_grid = np.array([[0.0, 1.0], [0.0, 1.0]])
        y_grid = np.array([[0.0, 0.0], [1.0, 1.0]])
        z_grid = np.array([[10.0, 20.0], [30.0, 40.0]])

        value = MultiViewPanel._nearest_grid_value(x_grid, y_grid, z_grid, 0.9, 0.8)

        self.assertEqual(value, 40.0)

    def test_click_range_first_click_stores_value_without_changing_range(self):
        panel = MultiViewPanel.__new__(MultiViewPanel)
        panel._click_count = 0
        panel._first_click_value = None
        panel._last_selected_range = None
        panel.status_label = _LabelStub()

        MultiViewPanel._apply_click_range_value(panel, 6.0, "demo.vts")

        self.assertEqual(panel._click_count, 1)
        self.assertEqual(panel._first_click_value, 6.0)
        self.assertIsNone(panel._last_selected_range)
        self.assertIn("First click", panel.status_label.text)

    def test_click_range_second_click_sets_sorted_manual_range(self):
        panel = MultiViewPanel.__new__(MultiViewPanel)
        panel._click_count = 1
        panel._first_click_value = 8.0
        panel._last_selected_range = None
        panel.status_label = _LabelStub()
        panel.full_scale = _ToggleStub(True)
        panel.range_min = _SpinStub()
        panel.range_max = _SpinStub()
        panel._render_count = 0

        def render_all():
            panel._render_count += 1

        panel._render_all = render_all

        MultiViewPanel._apply_click_range_value(panel, 2.0, "demo.vts")

        self.assertEqual(panel._click_count, 0)
        self.assertIsNone(panel._first_click_value)
        self.assertEqual(panel._last_selected_range, (2.0, 8.0))
        self.assertTrue(panel.full_scale.isChecked())
        self.assertEqual(panel.range_min.value(), 2.0)
        self.assertEqual(panel.range_max.value(), 8.0)
        self.assertEqual(panel._render_count, 1)

    def test_full_scale_spin_edit_keeps_full_scale_enabled(self):
        panel = MultiViewPanel.__new__(MultiViewPanel)
        panel.full_scale = _ToggleStub(True)
        panel.range_min = _SpinStub(2.0)
        panel.range_max = _SpinStub(8.0)
        panel._range_initialized = False
        panel._render_count = 0

        def render_all():
            panel._render_count += 1

        panel._render_all = render_all

        MultiViewPanel._on_range_spin_changed(panel)

        self.assertTrue(panel.full_scale.isChecked())
        self.assertTrue(panel._range_initialized)
        self.assertEqual(panel._render_count, 1)

    def test_full_scale_slider_edit_keeps_full_scale_enabled(self):
        panel = MultiViewPanel.__new__(MultiViewPanel)
        panel.full_scale = _ToggleStub(True)
        panel.range_min = _SpinStub()
        panel.range_max = _SpinStub()
        panel._range_initialized = False
        panel._render_count = 0

        def render_all():
            panel._render_count += 1

        panel._render_all = render_all

        MultiViewPanel._on_slider_changed(panel, 3.0, 7.0)

        self.assertTrue(panel.full_scale.isChecked())
        self.assertTrue(panel._range_initialized)
        self.assertEqual(panel.range_min.value(), 3.0)
        self.assertEqual(panel.range_max.value(), 7.0)
        self.assertEqual(panel._render_count, 1)

    def test_range_reset_enables_full_scale_and_rerenders(self):
        panel = MultiViewPanel.__new__(MultiViewPanel)
        panel._click_count = 1
        panel._first_click_value = 8.0
        panel._last_selected_range = (2.0, 8.0)
        panel.status_label = _LabelStub()
        panel.full_scale = _ToggleStub(False)
        panel._render_count = 0

        def render_all():
            panel._render_count += 1

        panel._render_all = render_all

        MultiViewPanel._on_range_reset_clicked(panel)

        self.assertFalse(panel.full_scale.blocked)
        self.assertTrue(panel.full_scale.isChecked())
        self.assertEqual(panel._click_count, 0)
        self.assertIsNone(panel._first_click_value)
        self.assertIsNone(panel._last_selected_range)
        self.assertEqual(panel.status_label.text, "")
        self.assertEqual(panel._render_count, 1)

    def test_line_scan_horizontal_uses_nearest_y_row(self):
        x_grid = np.array([[0.0, 1.0, 2.0], [0.0, 1.0, 2.0], [0.0, 1.0, 2.0]])
        y_grid = np.array([[0.0, 0.0, 0.0], [5.0, 5.0, 5.0], [10.0, 10.0, 10.0]])
        z_grid = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]])

        x_data, z_data, title, x_label = MultiViewPanel._extract_line_scan(
            x_grid, y_grid, z_grid, "horizontal", 6.0
        )

        np.testing.assert_array_equal(x_data, np.array([0.0, 1.0, 2.0]))
        np.testing.assert_array_equal(z_data, np.array([4.0, 5.0, 6.0]))
        self.assertEqual(title, "Horizontal Scan at Y=6.00")
        self.assertEqual(x_label, "X Position")

    def test_line_scan_vertical_uses_nearest_x_column(self):
        x_grid = np.array([[0.0, 4.0, 8.0], [0.0, 4.0, 8.0]])
        y_grid = np.array([[0.0, 0.0, 0.0], [2.0, 2.0, 2.0]])
        z_grid = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])

        x_data, z_data, title, x_label = MultiViewPanel._extract_line_scan(
            x_grid, y_grid, z_grid, "vertical", 7.0
        )

        np.testing.assert_array_equal(x_data, np.array([0.0, 2.0]))
        np.testing.assert_array_equal(z_data, np.array([3.0, 6.0]))
        self.assertEqual(title, "Vertical Scan at X=7.00")
        self.assertEqual(x_label, "Y Position")

    def test_line_scan_default_uses_middle_row(self):
        x_grid = np.array([[0.0, 1.0], [0.0, 1.0], [0.0, 1.0]])
        y_grid = np.array([[0.0, 0.0], [5.0, 5.0], [10.0, 10.0]])
        z_grid = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])

        _, z_data, title, _ = MultiViewPanel._extract_line_scan(
            x_grid, y_grid, z_grid, "horizontal", None
        )

        np.testing.assert_array_equal(z_data, np.array([3.0, 4.0]))
        self.assertIn("click heatmap", title)

    def test_line_scan_click_sets_shared_position_without_changing_range(self):
        panel = MultiViewPanel.__new__(MultiViewPanel)
        panel.line_mode_check = _ToggleStub(True)
        panel.direction_combo = _ComboStub("horizontal")
        panel.status_label = _LabelStub()
        panel._line_scan_y = None
        panel._line_scan_x = None
        panel._render_count = 0

        def render_all():
            panel._render_count += 1

        panel._render_all = render_all

        MultiViewPanel._handle_cell_click(panel, "demo.vts", 2.0, 7.0)

        self.assertEqual(panel._line_scan_y, 7.0)
        self.assertIsNone(panel._line_scan_x)
        self.assertEqual(panel._render_count, 1)
        self.assertIn("Line scan", panel.status_label.text)

    def test_selected_histogram_scalar_def_falls_back_to_selected_scalar(self):
        panel = MultiViewPanel.__new__(MultiViewPanel)
        panel._scalar_defs = [
            {"label": "PhaseFields", "value": "phase", "array": "PhaseFields"},
            {"label": "Interfaces", "value": "interfaces", "array": "Interfaces"},
        ]
        panel.histogram_field_combo = _ComboStub("missing")
        panel.scalar_combo = _ComboStub("interfaces")

        scalar_def = MultiViewPanel._selected_histogram_scalar_def(panel)

        self.assertEqual(scalar_def["value"], "interfaces")

    def test_line_scan_series_uses_all_cached_grids(self):
        panel = MultiViewPanel.__new__(MultiViewPanel)
        panel._grid_cache = {
            "a.vts": (
                np.array([[0.0, 1.0], [0.0, 1.0]]),
                np.array([[0.0, 0.0], [2.0, 2.0]]),
                np.array([[1.0, 2.0], [3.0, 4.0]]),
            ),
            "b.vts": (
                np.array([[0.0, 1.0], [0.0, 1.0]]),
                np.array([[0.0, 0.0], [2.0, 2.0]]),
                np.array([[5.0, 6.0], [7.0, 8.0]]),
            ),
        }
        panel._columns = {"a.vts": None, "b.vts": None}
        panel.direction_combo = _ComboStub("horizontal")
        panel._line_scan_y = 2.0
        panel._line_scan_x = None

        series, title, x_label = MultiViewPanel._build_line_scan_series(panel)

        self.assertEqual([item["name"] for item in series], ["a.vts", "b.vts"])
        np.testing.assert_array_equal(series[0]["y"], np.array([3.0, 4.0]))
        np.testing.assert_array_equal(series[1]["y"], np.array([7.0, 8.0]))
        self.assertEqual(title, "Horizontal Scan at Y=2.00")
        self.assertEqual(x_label, "X Position")


class _ComboStub:
    def __init__(self, current_data):
        self._current_data = current_data

    def currentData(self):
        return self._current_data


class _LineEditStub:
    def __init__(self, text):
        self._text = text

    def text(self):
        return self._text


class _LabelStub:
    def __init__(self):
        self.text = ""

    def setText(self, text):
        self.text = text


class _ToggleStub:
    def __init__(self, checked):
        self._checked = checked
        self.blocked = False

    def isChecked(self):
        return self._checked

    def blockSignals(self, blocked):
        self.blocked = blocked

    def setChecked(self, checked):
        self._checked = checked


class _SpinStub:
    def __init__(self, value=0.0):
        self._value = value
        self.blocked = False

    def blockSignals(self, blocked):
        self.blocked = blocked

    def setValue(self, value):
        self._value = value

    def value(self):
        return self._value


if __name__ == "__main__":
    unittest.main()
