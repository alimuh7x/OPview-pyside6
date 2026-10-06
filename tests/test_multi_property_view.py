import os
import tempfile
import unittest
from pathlib import Path

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QBoxLayout, QHBoxLayout, QSizePolicy
    from multi_property.colorbar_canvas import _format_tick
    from multi_property.colorbar_canvas import _build_colorbar_figure
    from multi_property.export_renderer import save_multi_property_png
    import multi_property.multi_property_panel as multi_property_panel_module
    from multi_property.multi_property_cell import MultiPropertyCell
    from multi_property.multi_property_panel import MultiPropertyPanel
    from multi_property.multi_property_tab import MultiPropertyTab
    from multi_view.multi_view_cell import _CELL_W
    from viewer.colorscale import palette_to_cmap
    from viewer.histogram_canvas import HistogramCanvas
except ModuleNotFoundError as exc:
    QApplication = None
    Qt = None
    QBoxLayout = None
    QHBoxLayout = None
    QSizePolicy = None
    _format_tick = None
    _build_colorbar_figure = None
    save_multi_property_png = None
    MultiPropertyCell = None
    MultiPropertyPanel = None
    MultiPropertyTab = None
    multi_property_panel_module = None
    _CELL_W = None
    palette_to_cmap = None
    HistogramCanvas = None
    MISSING_DEPENDENCY = exc.name
else:
    MISSING_DEPENDENCY = None


class _ToggleStub:
    def __init__(self, checked):
        self._checked = checked

    def isChecked(self):
        return self._checked


class _ComboStub:
    def __init__(self, current_data):
        self._current_data = current_data

    def currentData(self):
        return self._current_data


class _LabelStub:
    def __init__(self):
        self.text = ""

    def setText(self, text):
        self.text = text


class _LineEditStub:
    def __init__(self, text):
        self._text = text

    def text(self):
        return self._text


class _CellStub:
    def __init__(self):
        self.overlay_grid = None
        self.line_overlay = None
        self.rendered_z = None
        self.rendered_label = None
        self.plot_type = None

    def set_heatmap_size(self, width, height):
        self.heatmap_size = (width, height)

    def set_range_bounds(self, minimum, maximum):
        self.range_bounds = (minimum, maximum)

    def set_range_values(self, minimum, maximum):
        self.range_values = (minimum, maximum)

    def render(self, *args, **kwargs):
        self.rendered_z = args[2]
        self.rendered_label = kwargs.get("label")
        self.overlay_grid = kwargs.get("overlay_grid")
        self.line_overlay = kwargs.get("line_overlay")
        self.plot_type = kwargs.get("plot_type")

    def render_status(self, message):
        self.status_message = message


class _SliderStub:
    def __init__(self, value):
        self._value = value

    def value(self):
        return self._value


class _AnalysisCanvasStub:
    def __init__(self):
        self.calls = []
        self.geometry_updated = False
        self.repainted = False

    def render_lines(self, *args, **kwargs):
        self.calls.append(("lines", args, kwargs))

    def render_histograms(self, *args, **kwargs):
        self.calls.append(("histograms", args, kwargs))

    def updateGeometry(self):
        self.geometry_updated = True

    def repaint(self):
        self.repainted = True


class _ControlsStub:
    def __init__(self):
        self.hidden_values = []
        self._hidden = False

    def isHidden(self):
        return self._hidden

    def setHidden(self, hidden):
        self._hidden = hidden
        self.hidden_values.append(hidden)


class _PixmapStub:
    def __init__(self):
        self.saved_path = None

    def width(self):
        return 120

    def height(self):
        return 80

    def isNull(self):
        return False

    def save(self, path, format_name=None):
        self.saved_path = (path, format_name)
        return True


class _RowsWidgetStub:
    def __init__(self):
        self.pixmap = _PixmapStub()
        self.grabbed = False

    def grab(self):
        self.grabbed = True
        return self.pixmap


class _LiveRowsWidgetStub(_RowsWidgetStub):
    def __init__(self):
        super().__init__()
        self.geometry_updated = False

    def updateGeometry(self):
        self.geometry_updated = True


@unittest.skipIf(MISSING_DEPENDENCY is not None, f"missing dependency: {MISSING_DEPENDENCY}")
class MultiPropertyViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if QApplication is not None:
            cls._app = QApplication.instance() or QApplication([])

    def test_columns_follow_requested_layout_rules(self):
        expected = {
            1: 1,
            2: 2,
            3: 3,
            4: 2,
            5: 3,
            6: 3,
            7: 4,
            8: 4,
            9: 5,
            10: 5,
        }

        for count, columns in expected.items():
            self.assertEqual(MultiPropertyPanel._columns_for_count(count), columns)

    def test_colorbar_shows_only_min_middle_and_max_ticks_with_readable_font(self):
        figure = _build_colorbar_figure("Viridis", 2.0, 10.0, "Temperature", 360)

        colorbar = figure.data[0].colorbar

        self.assertEqual(list(colorbar.tickvals), [2.0, 6.0, 10.0])
        self.assertEqual(colorbar.tickfont.size, 20)
        self.assertEqual(colorbar.title.font.size, 22)
        self.assertEqual(colorbar.title.font.weight, 700)
        self.assertEqual(colorbar.thickness, 14)
        self.assertEqual(colorbar.len, 0.88)
        self.assertEqual(figure.layout.margin.l, 36)
        self.assertEqual(figure.layout.margin.r, 36)
        self.assertEqual(figure.layout.height, 78)
        self.assertEqual(figure.layout.margin.t, 22)
        self.assertEqual(figure.layout.margin.b, 16)
        self.assertEqual(colorbar.title.side, "top")
        self.assertEqual(colorbar.ticklabelposition, "outside bottom")

    def test_colorbar_tick_text_uses_spacing_based_decimals(self):
        figure = _build_colorbar_figure("Viridis", 0.0, 1.0, "Temperature", 360)

        colorbar = figure.data[0].colorbar

        self.assertEqual(list(colorbar.tickvals), [0.0, 0.5, 1.0])
        self.assertEqual(list(colorbar.ticktext), ["0.0", "0.5", "1.0"])

    def test_bottom_colorbar_places_values_above_and_name_below(self):
        figure = _build_colorbar_figure("Viridis", 2.0, 10.0, "Temperature", 360, placement="bottom")

        colorbar = figure.data[0].colorbar

        self.assertEqual(colorbar.title.side, "bottom")
        self.assertEqual(colorbar.ticklabelposition, "outside top")
        self.assertEqual(figure.layout.margin.t, 16)
        self.assertEqual(figure.layout.margin.b, 22)

    def test_colorbar_tick_format_uses_scientific_outside_three_digit_range(self):
        self.assertEqual(_format_tick(999.0), "999")
        self.assertEqual(_format_tick(1000.0), "1.0e3")
        self.assertEqual(_format_tick(0.001), "0.001")
        self.assertEqual(_format_tick(0.0001), "1.0e-4")

    def test_property_ranges_are_stored_independently(self):
        panel = MultiPropertyPanel.__new__(MultiPropertyPanel)
        panel._ranges = {}
        panel._render_count = 0

        def render_all():
            panel._render_count += 1

        panel._render_all = render_all

        MultiPropertyPanel._on_property_range_changed(panel, "temperature", 100.0, 500.0)
        MultiPropertyPanel._on_property_range_changed(panel, "phase", 0.2, 0.8)

        self.assertEqual(panel._ranges["temperature"]["selected_min"], 100.0)
        self.assertEqual(panel._ranges["temperature"]["selected_max"], 500.0)
        self.assertEqual(panel._ranges["phase"]["selected_min"], 0.2)
        self.assertEqual(panel._ranges["phase"]["selected_max"], 0.8)
        self.assertEqual(panel._render_count, 2)

    def test_bottom_row_cell_places_heatmap_before_colorbar(self):
        cell = MultiPropertyCell("phase", "Phase", bottom_row=True)

        layout = cell.layout()

        self.assertIs(layout.itemAt(0).widget(), cell.heatmap)
        self.assertIs(layout.itemAt(1).widget(), cell.colorbar)

    def test_top_row_cell_places_colorbar_before_heatmap(self):
        cell = MultiPropertyCell("phase", "Phase", bottom_row=False)

        layout = cell.layout()

        self.assertEqual(layout.spacing(), 0)
        self.assertIs(layout.itemAt(1).widget(), cell.colorbar)
        self.assertIs(layout.itemAt(2).widget(), cell.heatmap)

    def test_property_cell_title_has_gap_and_pencil_rename_button(self):
        cell = MultiPropertyCell("phase", "Phase", bottom_row=False)
        controls_layout = cell.controls.layout()
        margins = controls_layout.contentsMargins()
        title_row = controls_layout.itemAt(0).widget()
        title_layout = title_row.layout()

        self.assertGreaterEqual(margins.top(), 12)
        self.assertGreaterEqual(margins.bottom(), 8)
        self.assertEqual(controls_layout.count(), 1)
        self.assertEqual(title_row.objectName(), "multiPropertyTitleRow")
        self.assertIs(title_layout.itemAt(0).widget(), cell.select_button)
        self.assertIs(title_layout.itemAt(1).widget(), cell.title_label)
        self.assertIs(title_layout.itemAt(2).widget(), cell.rename_button)
        self.assertIsNotNone(title_layout.itemAt(3).spacerItem())
        self.assertIs(title_layout.itemAt(4).widget(), cell.remove_button)
        self.assertEqual(cell.select_button.objectName(), "multiPropertySelectBullet")
        self.assertEqual(cell.select_button.text(), "")
        self.assertEqual(cell.select_button.width(), 18)
        self.assertEqual(cell.select_button.height(), 18)
        self.assertEqual(cell.rename_button.text(), "✎")
        self.assertEqual(cell.rename_button.toolTip(), "Rename this property")
        self.assertEqual(cell.title_label.objectName(), "multiPropertyTitleLabel")
        self.assertNotEqual(cell.title_label.sizePolicy().horizontalPolicy(), QSizePolicy.Policy.Expanding)
        self.assertGreaterEqual(cell.title_label.font().pointSize(), 16)
        self.assertIn("QWidget#multiPropertyTitleRow", cell.styleSheet())
        self.assertIn("border: 1px solid #d6dee9", cell.styleSheet())

    def test_property_cell_selection_bullet_is_visible_when_selected(self):
        cell = MultiPropertyCell("phase", "Phase", bottom_row=False)

        cell.set_selected(True)

        self.assertEqual(cell.select_button.text(), "")
        self.assertTrue(cell.select_button.isChecked())
        self.assertIn("QPushButton#multiPropertySelectBullet:checked", cell.styleSheet())
        self.assertIn("background: #8FAE00", cell.styleSheet())
        self.assertIn("border-radius: 9px", cell.styleSheet())

    def test_property_cell_rename_updates_title_and_colorbar_label(self):
        cell = MultiPropertyCell("phase", "Phase", bottom_row=False)
        x_grid = np.array([[0.0, 1.0], [0.0, 1.0]])
        y_grid = np.array([[0.0, 0.0], [1.0, 1.0]])
        z_grid = np.array([[1.0, 2.0], [3.0, 4.0]])
        captured = {}

        def update_colorbar(_cmap, _vmin, _vmax, label, *, placement="top"):
            captured["label"] = label
            captured["placement"] = placement

        cell.colorbar.update_colorbar = update_colorbar

        cell.rename_property("Stress XX")
        cell.render(
            x_grid,
            y_grid,
            z_grid,
            cmap=palette_to_cmap("aqua-fire"),
            vmin=1.0,
            vmax=4.0,
            label="Phase",
        )

        self.assertEqual(cell.label, "Stress XX")
        self.assertEqual(cell.title_label.text(), "Stress XX")
        self.assertEqual(captured["label"], "Stress XX")

    def test_multi_property_panel_stores_renamed_title_for_colorbar_label(self):
        panel = MultiPropertyPanel.__new__(MultiPropertyPanel)
        panel._property_labels = {}
        panel._render_count = 0

        def render_all():
            panel._render_count += 1

        panel._render_all = render_all

        MultiPropertyPanel._on_property_renamed(panel, "p1", "Stress XX")

        self.assertEqual(panel._property_labels["p1"], "Stress XX")
        self.assertEqual(panel._render_count, 1)

    def test_multi_property_cell_click_selects_range_for_clicked_property(self):
        panel = MultiPropertyPanel.__new__(MultiPropertyPanel)
        panel._grid_cache = {
            "p1": (
                np.array([[0.0, 1.0], [0.0, 1.0]]),
                np.array([[0.0, 0.0], [1.0, 1.0]]),
                np.array([[1.0, 2.0], [3.0, 4.0]]),
            )
        }
        panel._ranges = {"p1": {"data_min": 1.0, "data_max": 4.0}}
        panel._selected_keys = ["p1"]
        panel._active_key = None
        panel._click_count = 0
        panel._first_click_value = None
        panel.status_label = _LabelStub()
        panel._sync_count = 0
        panel._render_count = 0
        panel._sync_selected_bullets = lambda: setattr(panel, "_sync_count", panel._sync_count + 1)
        panel._sync_top_range_controls = lambda: None
        panel._render_all = lambda: setattr(panel, "_render_count", panel._render_count + 1)

        MultiPropertyPanel._handle_cell_click(panel, "p1", 0.0, 0.0)

        self.assertEqual(panel._active_key, "p1")
        self.assertEqual(panel._click_count, 1)
        self.assertEqual(panel._first_click_value, 1.0)
        self.assertIn("First click", panel.status_label.text)

        MultiPropertyPanel._handle_cell_click(panel, "p1", 1.0, 1.0)

        self.assertEqual(panel._click_count, 0)
        self.assertIsNone(panel._first_click_value)
        self.assertEqual(panel._ranges["p1"]["selected_min"], 1.0)
        self.assertEqual(panel._ranges["p1"]["selected_max"], 4.0)
        self.assertEqual(panel._render_count, 1)
        self.assertIn("Range selected", panel.status_label.text)

    def test_multi_property_display_label_uses_renamed_title_and_units(self):
        panel = MultiPropertyPanel.__new__(MultiPropertyPanel)
        panel.unit_scale_combo = _ComboStub((1e-6, "MPa"))

        scale, label = MultiPropertyPanel._get_display_params(panel, "Phase", override_label="Stress XX")

        self.assertEqual(scale, 1e-6)
        self.assertEqual(label, "Stress XX (MPa)")

    def test_property_cell_colorbar_uses_render_label_with_unit_suffix(self):
        cell = MultiPropertyCell("phase", "Phase", bottom_row=False)
        x_grid = np.array([[0.0, 1.0], [0.0, 1.0]])
        y_grid = np.array([[0.0, 0.0], [1.0, 1.0]])
        z_grid = np.array([[1.0, 2.0], [3.0, 4.0]])
        captured = {}

        def update_colorbar(_cmap, _vmin, _vmax, label, *, placement="top"):
            captured["label"] = label

        cell.colorbar.update_colorbar = update_colorbar

        cell.rename_property("Stress XX")
        cell.render(
            x_grid,
            y_grid,
            z_grid,
            cmap=palette_to_cmap("aqua-fire"),
            vmin=1.0,
            vmax=4.0,
            label="Stress XX (MPa)",
        )

        self.assertEqual(captured["label"], "Stress XX (MPa)")

    def test_property_rename_dialog_uses_readable_light_style(self):
        cell = MultiPropertyCell("phase", "Phase", bottom_row=False)

        dialog = cell._build_rename_dialog()
        stylesheet = dialog.styleSheet()

        self.assertEqual(dialog.objectName(), "multiPropertyRenameDialog")
        self.assertIn("QInputDialog#multiPropertyRenameDialog", stylesheet)
        self.assertIn("background: #f7f9fc", stylesheet)
        self.assertIn("color: #102a52", stylesheet)
        self.assertIn("QLineEdit", stylesheet)

    def test_property_cell_uses_multiview_cell_width(self):
        cell = MultiPropertyCell("phase", "Phase", bottom_row=False)

        self.assertEqual(cell.width(), _CELL_W)
        self.assertEqual(cell.heatmap.width(), _CELL_W)
        self.assertEqual(cell.colorbar.width(), _CELL_W)
        self.assertEqual(cell.sizePolicy().verticalPolicy(), QSizePolicy.Policy.Fixed)

    def test_property_cell_can_apply_heatmap_size_without_stretching(self):
        cell = MultiPropertyCell("phase", "Phase", bottom_row=False)

        cell.set_heatmap_size(240, 320)

        self.assertEqual(cell.width(), 330)
        self.assertEqual(cell.heatmap.width(), 330)
        self.assertEqual(cell.heatmap.height(), 320)
        self.assertEqual(cell.colorbar.width(), 330)
        self.assertEqual(cell.controls.width(), 330)

    def test_property_cell_controls_fit_narrow_heatmap_width(self):
        cell = MultiPropertyCell("phase", "Phase", bottom_row=False)

        cell.set_heatmap_size(210, 420)

        self.assertEqual(cell.width(), 330)
        self.assertEqual(cell.heatmap.width(), 330)
        self.assertEqual(cell.colorbar.width(), 330)
        self.assertEqual(cell.controls.width(), 330)
        self.assertEqual(cell.remove_button.objectName(), "multiPropertyIconButton")

    def test_property_cell_heatmap_offsets_use_stable_size_hints_not_stale_heights(self):
        cell = MultiPropertyCell("phase", "Phase", bottom_row=False)
        cell.set_heatmap_size(360, 180)

        expected_offset = cell.controls.sizeHint().height() + cell.colorbar.sizeHint().height()

        self.assertNotEqual(cell.controls.height(), cell.controls.sizeHint().height())
        self.assertEqual(cell.heatmap_top_offset(), expected_offset)

        cell.set_bottom_row(True)

        expected_bottom_offset = cell.controls.sizeHint().height() + cell.colorbar.sizeHint().height()
        self.assertEqual(cell.heatmap_bottom_offset(), expected_bottom_offset)
        self.assertEqual(cell.remove_button.width(), 16)
        self.assertTrue(cell.remove_button.isFlat())
        self.assertFalse(hasattr(cell, "range_min"))
        self.assertFalse(hasattr(cell, "range_max"))
        self.assertFalse(hasattr(cell, "range_slider"))
        self.assertFalse(hasattr(cell, "reset_button"))

    def test_heatmap_size_matches_square_grid_aspect(self):
        x_grid = np.array([[0.0, 1.0], [0.0, 1.0]])
        y_grid = np.array([[0.0, 0.0], [1.0, 1.0]])

        width, height = MultiPropertyPanel._heatmap_size_for_grid(x_grid, y_grid)

        self.assertEqual((width, height), (360, 360))

    def test_heatmap_size_matches_tall_grid_aspect(self):
        x_grid = np.array([[0.0, 1.0], [0.0, 1.0]])
        y_grid = np.array([[0.0, 0.0], [2.0, 2.0]])

        width, height = MultiPropertyPanel._heatmap_size_for_grid(x_grid, y_grid)

        self.assertEqual((width, height), (330, 420))

    def test_heatmap_size_matches_wide_grid_aspect(self):
        x_grid = np.array([[0.0, 2.0], [0.0, 2.0]])
        y_grid = np.array([[0.0, 0.0], [1.0, 1.0]])

        width, height = MultiPropertyPanel._heatmap_size_for_grid(x_grid, y_grid)

        self.assertEqual((width, height), (360, 180))

    def test_top_range_slider_tracks_active_property_values(self):
        panel = MultiPropertyPanel({"available_projects": []})
        panel._selected_keys = ["phase"]
        panel._active_key = "phase"
        panel._ranges = {
            "phase": {
                "data_min": -2.0,
                "data_max": 8.0,
                "selected_min": 1.0,
                "selected_max": 5.0,
            }
        }

        panel._sync_top_range_controls()

        self.assertEqual(panel.range_slider.lower_value(), 1.0)
        self.assertEqual(panel.range_slider.upper_value(), 5.0)
        self.assertEqual(panel.range_min.value(), 1.0)
        self.assertEqual(panel.range_max.value(), 5.0)

    def test_top_range_spin_boxes_use_scientific_display_for_large_values(self):
        panel = MultiPropertyPanel({"available_projects": []})
        panel._selected_keys = ["phase"]
        panel._active_key = "phase"
        panel._ranges = {
            "phase": {
                "data_min": -228399948.474190115929,
                "data_max": 0.0000001,
                "selected_min": -228399948.474190115929,
                "selected_max": 0.0000001,
            }
        }

        panel._sync_top_range_controls()

        self.assertEqual(panel.range_min.text(), "-2.28e+08")
        self.assertEqual(panel.range_max.text(), "1.00e-07")

    def test_property_cell_accepts_interfaces_overlay_grid(self):
        cell = MultiPropertyCell("phase", "Phase", bottom_row=False)
        x_grid = np.array([[0.0, 1.0], [0.0, 1.0]])
        y_grid = np.array([[0.0, 0.0], [1.0, 1.0]])
        z_grid = np.array([[1.0, 2.0], [3.0, 4.0]])
        overlay = {
            "x": x_grid,
            "y": y_grid,
            "z": np.array([[0.0, 2.0], [3.0, 4.0]]),
        }

        cell.render(
            x_grid,
            y_grid,
            z_grid,
            cmap=palette_to_cmap("aqua-fire"),
            vmin=1.0,
            vmax=4.0,
            label="Phase",
            overlay_grid=overlay,
        )

        self.assertEqual(cell.colorbar.width(), cell.width())

    def test_property_cell_forwards_selected_plot_type_to_heatmap(self):
        cell = MultiPropertyCell("phase", "Phase", bottom_row=False)
        captured = {}
        x_grid = np.array([[0.0, 1.0], [0.0, 1.0]])
        y_grid = np.array([[0.0, 0.0], [1.0, 1.0]])
        z_grid = np.array([[1.0, 2.0], [3.0, 4.0]])

        def render_heatmap(*args, **kwargs):
            captured["plot_type"] = kwargs.get("plot_type")

        cell.heatmap.render = render_heatmap

        cell.render(
            x_grid,
            y_grid,
            z_grid,
            cmap=palette_to_cmap("aqua-fire"),
            vmin=1.0,
            vmax=4.0,
            label="Phase",
            plot_type="contour_filled",
        )

        self.assertEqual(captured["plot_type"], "contour_filled")

    def test_property_rows_keep_multiview_spacing_and_left_logo(self):
        panel = MultiPropertyPanel({"available_projects": []})
        panel._scalar_defs = [
            {"label": "Property 1", "value": "p1", "array": "p1"},
            {"label": "Property 2", "value": "p2", "array": "p2"},
            {"label": "Property 3", "value": "p3", "array": "p3"},
            {"label": "Property 4", "value": "p4", "array": "p4"},
        ]
        panel._selected_keys = ["p1", "p2", "p3", "p4"]

        panel._sync_cells()

        self.assertEqual(panel.rows_layout.count(), 2)
        self.assertEqual(panel.rows_layout.spacing(), 8)
        self.assertEqual(panel.rows_widget.minimumHeight(), panel.rows_widget.maximumHeight())
        first_row = panel.rows_layout.itemAt(0).widget()
        self.assertEqual(first_row.minimumHeight(), first_row.maximumHeight())
        self.assertEqual(first_row.sizePolicy().verticalPolicy(), QSizePolicy.Policy.Fixed)
        first_layout = first_row.layout()
        self.assertEqual(first_layout.spacing(), 8)
        self.assertEqual(first_layout.count(), 3)
        self.assertEqual(first_layout.itemAt(0).widget().objectName(), "multiPropertyLogoBand")
        second_row = panel.rows_layout.itemAt(1).widget()
        second_layout = second_row.layout()
        self.assertEqual(second_layout.itemAt(0).widget().objectName(), "multiPropertyLogoBand")

    def test_lock_layout_sizes_releases_stale_large_row_width_after_heatmaps_shrink(self):
        panel = MultiPropertyPanel({"available_projects": []})
        panel._scalar_defs = [
            {"label": f"Property {index}", "value": f"p{index}", "array": f"p{index}"}
            for index in range(1, 6)
        ]
        panel._selected_keys = [f"p{index}" for index in range(1, 6)]
        panel._sync_cells()
        row = panel._row_widgets[0]
        row.setFixedWidth(5000)

        for cell in panel._cells.values():
            cell.set_heatmap_size(330, 240)

        panel._lock_layout_sizes()

        self.assertLess(row.width(), 5000)

    def test_lock_layout_sizes_releases_stale_large_rows_widget_width_after_heatmaps_shrink(self):
        panel = MultiPropertyPanel({"available_projects": []})
        panel._scalar_defs = [
            {"label": f"Property {index}", "value": f"p{index}", "array": f"p{index}"}
            for index in range(1, 6)
        ]
        panel._selected_keys = [f"p{index}" for index in range(1, 6)]
        panel._sync_cells()
        panel.rows_widget.setFixedWidth(6000)

        for cell in panel._cells.values():
            cell.set_heatmap_size(330, 240)

        panel._lock_layout_sizes()

        self.assertLess(panel.rows_widget.width(), 6000)

    def test_render_rebuilds_logo_band_after_heatmap_height_shrinks(self):
        class FakeReader:
            dimensions = (2, 2, 1)

            def get_interpolated_slice(self, *, axis, index, scalar_name, component, resolution):
                x_grid = np.array([[0.0, 2.0], [0.0, 2.0]])
                y_grid = np.array([[0.0, 0.0], [1.0, 1.0]])
                z_grid = np.array([[1.0, 2.0], [3.0, 4.0]])
                return x_grid, y_grid, z_grid, {}

        original_get_reader = multi_property_panel_module.get_reader
        multi_property_panel_module.get_reader = lambda _path: FakeReader()
        self.addCleanup(lambda: setattr(multi_property_panel_module, "get_reader", original_get_reader))
        panel = MultiPropertyPanel({"available_projects": []})
        panel.file_combo.addItem("demo.vts", "demo.vts")
        panel.file_combo.setCurrentIndex(panel.file_combo.count() - 1)
        panel._scalar_defs = [
            {"label": f"Property {index}", "value": f"p{index}", "array": f"p{index}"}
            for index in range(1, 6)
        ]
        panel._selected_keys = [f"p{index}" for index in range(1, 6)]
        panel._sync_cells()
        for cell in panel._cells.values():
            cell.render = lambda *args, **kwargs: None
        panel._build_overlay_grid = lambda file_path, axis: None

        panel._render_all()

        top_row = panel.rows_layout.itemAt(0).widget()
        logo = top_row.layout().itemAt(0).widget()
        first_cell = top_row.layout().itemAt(1).widget()
        self.assertEqual(first_cell.heatmap.height(), 180)
        self.assertEqual(logo.property("heatmapHeight"), first_cell.heatmap.height())

    def test_first_multi_property_row_is_left_aligned_after_empty_state(self):
        panel = MultiPropertyPanel({"available_projects": []})
        panel._scalar_defs = [
            {"label": "Property 1", "value": "p1", "array": "p1"},
        ]

        panel._sync_cells()
        panel._selected_keys = ["p1"]
        panel._sync_cells()

        alignment = panel.scroll.alignment()
        self.assertTrue(alignment & Qt.AlignmentFlag.AlignLeft)
        self.assertTrue(alignment & Qt.AlignmentFlag.AlignTop)
        self.assertEqual(panel.rows_widget.sizePolicy().horizontalPolicy(), QSizePolicy.Policy.Fixed)
        self.assertEqual(panel.rows_widget.sizePolicy().verticalPolicy(), QSizePolicy.Policy.Fixed)
        self.assertEqual(panel.rows_layout.alignment() & Qt.AlignmentFlag.AlignLeft, Qt.AlignmentFlag.AlignLeft)
        self.assertEqual(panel.rows_layout.count(), 1)
        first_row = panel.rows_layout.itemAt(0).widget()
        first_layout = first_row.layout()
        self.assertEqual(first_layout.alignment() & Qt.AlignmentFlag.AlignLeft, Qt.AlignmentFlag.AlignLeft)
        self.assertEqual(first_layout.itemAt(0).widget().objectName(), "multiPropertyLogoBand")

    def test_logo_band_aligns_with_heatmap_area_for_top_and_bottom_rows(self):
        panel = MultiPropertyPanel({"available_projects": []})
        panel._scalar_defs = [
            {"label": "Property 1", "value": "p1", "array": "p1"},
            {"label": "Property 2", "value": "p2", "array": "p2"},
            {"label": "Property 3", "value": "p3", "array": "p3"},
            {"label": "Property 4", "value": "p4", "array": "p4"},
        ]
        panel._selected_keys = ["p1", "p2", "p3", "p4"]

        panel._sync_cells()

        top_row = panel.rows_layout.itemAt(0).widget()
        top_logo = top_row.layout().itemAt(0).widget()
        top_cell = top_row.layout().itemAt(1).widget()
        bottom_row = panel.rows_layout.itemAt(1).widget()
        bottom_logo = bottom_row.layout().itemAt(0).widget()
        bottom_cell = bottom_row.layout().itemAt(1).widget()

        self.assertEqual(top_logo.property("heatmapTopOffset"), top_cell.heatmap_top_offset())
        self.assertEqual(top_logo.property("heatmapHeight"), top_cell.heatmap.height())
        self.assertEqual(bottom_logo.property("heatmapTopOffset"), 0)
        self.assertEqual(bottom_logo.property("heatmapHeight"), bottom_cell.heatmap.height())

    def test_multi_property_has_top_interfaces_overlay_toggle(self):
        panel = MultiPropertyPanel({"available_projects": []})
        controls_card = panel.layout().itemAt(0).widget()
        controls_layout = controls_card.layout()
        selection_layout = controls_layout.itemAt(0).widget().layout()
        range_layout = controls_layout.itemAt(1).widget().layout()

        self.assertFalse(panel.interfaces_on.isChecked())
        self.assertEqual(panel.interfaces_on.text(), "Interfaces Overlay")
        self.assertIs(selection_layout.itemAt(5).widget(), panel.interfaces_on)
        self.assertIs(range_layout.itemAt(1).widget(), panel.range_min)
        self.assertIs(range_layout.itemAt(2).widget(), panel.range_max)
        self.assertIs(range_layout.itemAt(3).widget(), panel.range_slider)
        self.assertIs(range_layout.itemAt(4).widget(), panel.reset_button)
        self.assertIs(range_layout.itemAt(5).widget(), panel.reset_all_button)

    def test_multi_property_has_add_all_properties_button(self):
        panel = MultiPropertyPanel({"available_projects": []})
        controls_card = panel.layout().itemAt(0).widget()
        controls_layout = controls_card.layout()
        selection_layout = controls_layout.itemAt(0).widget().layout()

        self.assertFalse(hasattr(panel, "add_property_button"))
        self.assertEqual(panel.add_all_properties_button.text(), "Add All")
        self.assertEqual(panel.add_all_properties_button.toolTip(), "Add all properties as heatmaps")
        self.assertIs(selection_layout.itemAt(6).widget(), panel.add_all_properties_button)

    def test_multi_property_has_same_plot_type_options_as_multi_view(self):
        panel = MultiPropertyPanel({"available_projects": []})
        controls_card = panel.layout().itemAt(0).widget()
        controls_layout = controls_card.layout()
        selection_layout = controls_layout.itemAt(0).widget().layout()

        options = [panel.type_combo.itemData(index) for index in range(panel.type_combo.count())]

        self.assertEqual(
            options,
            ["heatmap", "contour_lines", "contour_filled", "contour_filled_values", "heatmap_contour"],
        )
        self.assertIs(selection_layout.itemAt(3).widget(), panel.type_combo)

    def test_multi_property_file_combo_starts_with_select_file_placeholder(self):
        panel = MultiPropertyPanel({"available_projects": []})
        panel.project_combo.addItem(
            "Project",
            {"files": ["/tmp/PhaseField_00000001.vts", "/tmp/PhaseField_00000002.vts"]},
        )
        panel.project_combo.setCurrentIndex(0)

        panel._on_project_changed()

        self.assertEqual(panel.file_combo.itemText(0), "Select file")
        self.assertEqual(panel.file_combo.itemData(0), "")
        self.assertEqual(panel.file_combo.itemText(1), "PhaseField_00000001.vts")

    def test_multi_property_property_combo_has_checkable_placeholder_and_items(self):
        panel = MultiPropertyPanel({"available_projects": []})
        panel._scalar_defs = [
            {"label": "Property 1", "value": "p1", "array": "p1"},
            {"label": "Property 2", "value": "p2", "array": "p2"},
        ]
        panel._selected_keys = ["p2"]

        panel._populate_property_combo()

        self.assertEqual(panel.property_combo.itemText(0), "Add Property")
        self.assertEqual(panel.property_combo.itemData(0), "")
        self.assertIsNone(panel.property_combo.itemData(0, Qt.ItemDataRole.CheckStateRole))
        self.assertEqual(panel.property_combo.itemText(1), "Property 1")
        self.assertEqual(panel.property_combo.itemData(1, Qt.ItemDataRole.CheckStateRole), Qt.CheckState.Unchecked)
        self.assertEqual(panel.property_combo.itemText(2), "Property 2")
        self.assertEqual(panel.property_combo.itemData(2, Qt.ItemDataRole.CheckStateRole), Qt.CheckState.Checked)
        self.assertEqual(panel.property_combo.currentIndex(), 0)

    def test_multi_property_property_combo_uses_bold_check_delegate(self):
        panel = MultiPropertyPanel({"available_projects": []})

        delegate = panel.property_combo.itemDelegate()

        self.assertEqual(delegate.objectName(), "multiPropertyCheckDelegate")
        self.assertEqual(delegate.box_size, 14)
        self.assertEqual(delegate.box_border_width, 2)
        self.assertEqual(delegate.box_left_padding, 8)
        self.assertEqual(delegate.text_gap_after_box, 12)
        self.assertEqual(delegate.text_left_offset(), 34)
        self.assertEqual(delegate.tick_weight, 900)
        option = delegate._text_option_without_default_check(Qt.CheckState.Checked)
        self.assertFalse(option.features & option.ViewItemFeature.HasCheckIndicator)
        self.assertEqual(option.checkState, Qt.CheckState.Unchecked)
        self.assertTrue(delegate.paint_checkable_rows_without_super)

    def test_multi_property_toggles_property_combo_selection_and_keeps_placeholder(self):
        panel = MultiPropertyPanel({"available_projects": []})
        panel._scalar_defs = [
            {"label": "Property 1", "value": "p1", "array": "p1"},
            {"label": "Property 2", "value": "p2", "array": "p2"},
        ]
        panel._selected_keys = []
        panel._active_key = None
        panel._sync_count = 0
        panel._render_count = 0
        panel._sync_cells = lambda: setattr(panel, "_sync_count", panel._sync_count + 1)
        panel._render_all = lambda: setattr(panel, "_render_count", panel._render_count + 1)
        panel._populate_property_combo()

        panel._toggle_property_combo_index(1, keep_popup=False)

        self.assertEqual(panel._selected_keys, ["p1"])
        self.assertEqual(panel._active_key, "p1")
        self.assertEqual(panel.property_combo.currentIndex(), 0)
        self.assertEqual(panel.property_combo.itemData(1, Qt.ItemDataRole.CheckStateRole), Qt.CheckState.Checked)
        self.assertEqual(panel.property_combo.itemText(1), "Property 1")
        self.assertEqual(panel._sync_count, 1)
        self.assertEqual(panel._render_count, 1)

        panel._toggle_property_combo_index(1, keep_popup=False)

        self.assertEqual(panel._selected_keys, [])
        self.assertIsNone(panel._active_key)
        self.assertEqual(panel.property_combo.itemData(1, Qt.ItemDataRole.CheckStateRole), Qt.CheckState.Unchecked)
        self.assertEqual(panel.property_combo.itemText(1), "Property 1")

    def test_multi_property_top_reset_button_is_visible(self):
        panel = MultiPropertyPanel({"available_projects": []})

        self.assertEqual(panel.reset_button.objectName(), "multiPropertyTopRangeReset")
        self.assertFalse(panel.reset_button.icon().isNull())
        self.assertEqual(panel.reset_button.text(), "")
        self.assertGreaterEqual(panel.reset_button.width(), 30)
        self.assertEqual(panel.reset_button.toolTip(), "Reset selected property range")
        self.assertIn("QPushButton#multiPropertyTopRangeReset", panel.styleSheet())
        self.assertIn("QPushButton#multiPropertyTopRangeReset:disabled", panel.styleSheet())

    def test_multi_property_top_reset_all_button_is_visible(self):
        panel = MultiPropertyPanel({"available_projects": []})

        self.assertEqual(panel.reset_all_button.objectName(), "multiPropertyTopRangeResetAll")
        self.assertTrue(panel.reset_all_button.icon().isNull())
        self.assertEqual(panel.reset_all_button.text(), "Reset All")
        self.assertEqual(panel.reset_all_button.toolTip(), "Reset all property ranges")
        self.assertGreaterEqual(panel.reset_all_button.width(), 74)
        self.assertIn("QPushButton#multiPropertyTopRangeResetAll", panel.styleSheet())

    def test_add_all_properties_selects_available_properties_up_to_limit(self):
        panel = MultiPropertyPanel({"available_projects": []})
        panel._scalar_defs = [
            {"label": f"Property {index}", "value": f"p{index}", "array": f"p{index}"}
            for index in range(1, 13)
        ]
        panel._selected_keys = ["p2"]
        panel._active_key = "p2"
        panel._sync_count = 0
        panel._render_count = 0

        def sync_cells():
            panel._sync_count += 1

        def render_all():
            panel._render_count += 1

        panel._sync_cells = sync_cells
        panel._render_all = render_all

        panel._add_all_properties()

        self.assertEqual(panel._selected_keys, ["p2", "p1", "p3", "p4", "p5", "p6", "p7", "p8", "p9", "p10"])
        self.assertEqual(panel._active_key, "p2")
        self.assertEqual(panel.status_label.text(), "Maximum 10 properties")
        self.assertEqual(panel._sync_count, 1)
        self.assertEqual(panel._render_count, 1)

    def test_ten_multi_property_maps_use_two_rows_of_five(self):
        panel = MultiPropertyPanel({"available_projects": []})
        panel._selected_keys = [f"p{index}" for index in range(1, 11)]

        rows = panel._row_keys(panel._columns_for_count(len(panel._selected_keys)))

        self.assertEqual(len(rows), 2)
        self.assertEqual([len(row) for row in rows], [5, 5])

    def test_nine_multi_property_maps_use_five_by_two_layout(self):
        panel = MultiPropertyPanel({"available_projects": []})
        panel._selected_keys = [f"p{index}" for index in range(1, 10)]

        rows = panel._row_keys(panel._columns_for_count(len(panel._selected_keys)))

        self.assertEqual(len(rows), 2)
        self.assertEqual([len(row) for row in rows], [5, 4])

    def test_multi_property_reset_all_ranges_resets_every_property(self):
        panel = MultiPropertyPanel.__new__(MultiPropertyPanel)
        panel._ranges = {
            "p1": {"data_min": 1.0, "data_max": 9.0, "selected_min": 2.0, "selected_max": 4.0},
            "p2": {"data_min": -5.0, "data_max": 5.0, "selected_min": -1.0, "selected_max": 1.0},
        }
        panel._render_count = 0
        panel._sync_count = 0

        def render_all():
            panel._render_count += 1

        def sync_top_range_controls():
            panel._sync_count += 1

        panel._render_all = render_all
        panel._sync_top_range_controls = sync_top_range_controls

        MultiPropertyPanel._reset_all_ranges(panel)

        self.assertEqual(panel._ranges["p1"]["selected_min"], 1.0)
        self.assertEqual(panel._ranges["p1"]["selected_max"], 9.0)
        self.assertEqual(panel._ranges["p2"]["selected_min"], -5.0)
        self.assertEqual(panel._ranges["p2"]["selected_max"], 5.0)
        self.assertEqual(panel._sync_count, 1)
        self.assertEqual(panel._render_count, 1)

    def test_multi_property_uses_rotation_icon_buttons_like_multiview(self):
        panel = MultiPropertyPanel({"available_projects": []})
        controls_card = panel.layout().itemAt(0).widget()
        controls_layout = controls_card.layout()
        range_layout = controls_layout.itemAt(1).widget().layout()

        self.assertFalse(hasattr(panel, "rotation_combo"))
        self.assertEqual(sorted(panel.rotation_buttons), [0, 90, 180, 270])
        self.assertIs(range_layout.itemAt(7).widget(), panel.rotation_button_row)

        panel.rotation_buttons[90].click()

        self.assertEqual(panel._rotation_degrees, 270)
        self.assertTrue(panel.rotation_buttons[90].isChecked())

    def test_multi_property_has_unit_conversion_combo_like_multiview(self):
        panel = MultiPropertyPanel({"available_projects": []})
        controls_card = panel.layout().itemAt(0).widget()
        controls_layout = controls_card.layout()
        range_layout = controls_layout.itemAt(1).widget().layout()

        self.assertIs(range_layout.itemAt(6).widget(), panel.unit_scale_combo)
        self.assertEqual(panel.unit_scale_combo.itemText(0), "Raw")
        self.assertEqual(panel.unit_scale_combo.itemData(0), (1.0, ""))
        self.assertEqual(panel.unit_scale_combo.itemData(1), (100.0, "%"))
        self.assertEqual(panel.unit_scale_combo.itemData(2), (1e-6, "MPa"))
        self.assertEqual(panel.unit_scale_combo.itemData(3), (1e-9, "GPa"))

    def test_multi_property_has_analysis_graphs_like_multiview(self):
        panel = MultiPropertyPanel({"available_projects": []})

        self.assertIsInstance(panel.analysis_card.layout(), QHBoxLayout)
        self.assertEqual(panel.line_mode_check.text(), "Line Scan")
        self.assertEqual(panel.show_line_check.text(), "Show Line")
        self.assertEqual(sorted(panel.line_direction_buttons), ["horizontal", "vertical"])
        self.assertEqual(panel.line_grid_check.text(), "Grid")
        self.assertEqual(panel.analysis_value_label_edit.text(), "Value")
        self.assertEqual(panel.analysis_value_label_edit.toolTip(), "Rename value label for line and frequency graphs")
        self.assertEqual(panel.analysis_value_label_edit.minimumHeight(), 24)
        self.assertEqual(panel.analysis_value_label_edit.maximumHeight(), 24)
        self.assertEqual(panel.histogram_bins_slider.minimum(), 10)
        self.assertEqual(panel.histogram_bins_slider.maximum(), 200)
        self.assertEqual(panel.histogram_bins_slider.value(), 30)
        self.assertEqual(panel.histogram_grid_check.text(), "Grid")
        self.assertIs(panel.scroll.widget().layout().itemAt(1).widget(), panel.analysis_card)

    def test_multi_property_analysis_value_label_is_after_line_grid_toggle(self):
        panel = MultiPropertyPanel({"available_projects": []})
        line_card = panel.analysis_card.layout().itemAt(0).widget()
        line_toolbar = line_card.layout().itemAt(0).widget()
        line_toolbar_layout = line_toolbar.layout()

        self.assertIs(line_toolbar_layout.itemAt(4).widget(), panel.line_grid_check)
        self.assertIs(line_toolbar_layout.itemAt(6).widget(), panel.analysis_value_label_edit)

    def test_multi_property_discrete_palette_controls_show_only_for_discrete_custom(self):
        panel = MultiPropertyPanel({"available_projects": []})

        self.assertTrue(panel.discrete_minus_button.isHidden())
        self.assertTrue(panel.discrete_band_label.isHidden())
        self.assertTrue(panel.discrete_plus_button.isHidden())

        panel.palette_combo.setCurrentIndex(panel.palette_combo.findData("discrete-custom"))
        QApplication.processEvents()

        self.assertFalse(panel.discrete_minus_button.isHidden())
        self.assertFalse(panel.discrete_band_label.isHidden())
        self.assertFalse(panel.discrete_plus_button.isHidden())
        self.assertEqual(panel.discrete_minus_button.objectName(), "discreteBandButton")
        self.assertEqual(panel.discrete_plus_button.objectName(), "discreteBandButton")

    def test_multi_property_discrete_band_buttons_clamp_between_two_and_ten(self):
        panel = MultiPropertyPanel({"available_projects": []})

        panel._change_discrete_band_count(-1)
        self.assertEqual(panel.discrete_band_count, 2)
        panel._change_discrete_band_count(20)
        self.assertEqual(panel.discrete_band_count, 10)
        self.assertEqual(panel.discrete_band_label.text(), "10")

    def test_multi_property_heatmaps_and_graphs_share_one_scroll_area(self):
        panel = MultiPropertyPanel({"available_projects": []})

        self.assertEqual(panel.layout().count(), 2)
        self.assertIs(panel.layout().itemAt(1).widget(), panel.scroll)
        scroll_content = panel.scroll.widget()
        scroll_layout = scroll_content.layout()

        self.assertEqual(scroll_content.objectName(), "multiPropertyScrollContent")
        self.assertIs(scroll_layout.itemAt(0).widget(), panel.rows_widget)
        self.assertIs(scroll_layout.itemAt(1).widget(), panel.analysis_card)
        self.assertIs(scroll_layout.itemAt(2).widget(), panel.empty_label)
        self.assertEqual(scroll_layout.spacing(), 8)

    def test_multi_property_hides_analysis_graphs_until_file_and_property_selected(self):
        panel = MultiPropertyPanel({"available_projects": []})

        self.assertTrue(panel.analysis_card.isHidden())

        panel.file_combo.addItem("demo.vts", "demo.vts")
        panel.file_combo.setCurrentIndex(panel.file_combo.count() - 1)
        panel._selected_keys = []
        panel._render_all()

        self.assertTrue(panel.analysis_card.isHidden())

    def test_multi_property_analysis_canvases_fit_side_by_side_in_available_width(self):
        panel = MultiPropertyPanel({"available_projects": []})

        panel.set_available_width(900)

        self.assertEqual(panel.analysis_card.layout().direction(), QBoxLayout.Direction.LeftToRight)
        self.assertEqual(panel.line_scan_canvas.width(), 800)
        self.assertEqual(panel.histogram_canvas.width(), 800)
        self.assertGreater(
            panel.line_scan_canvas.width() + panel.histogram_canvas.width() + 88,
            900,
        )
        self.assertEqual(panel.histogram_canvas.width(), panel.line_scan_canvas.width())

    def test_multi_property_analysis_stacks_when_width_is_too_narrow(self):
        panel = MultiPropertyPanel({"available_projects": []})

        panel.set_available_width(520)

        self.assertEqual(panel.analysis_card.layout().direction(), QBoxLayout.Direction.TopToBottom)
        self.assertLessEqual(panel.histogram_canvas.width() + 56, 520)
        self.assertEqual(panel.line_scan_canvas.width(), panel.histogram_canvas.width())

    def test_multi_property_analysis_default_width_keeps_frequency_visible(self):
        panel = MultiPropertyPanel({"available_projects": []})

        self.assertEqual(panel.line_scan_canvas.width(), 800)
        self.assertEqual(panel.histogram_canvas.width(), 800)
        self.assertEqual(panel.histogram_canvas.width(), panel.line_scan_canvas.width())

    def test_multi_property_analysis_toolbars_keep_fixed_height(self):
        panel = MultiPropertyPanel({"available_projects": []})
        panel._set_analysis_visible(True)
        panel.resize(900, 900)
        QApplication.processEvents()

        line_card = panel.analysis_card.layout().itemAt(0).widget()
        histogram_card = panel.analysis_card.layout().itemAt(1).widget()
        line_toolbar = line_card.layout().itemAt(0).widget()
        histogram_toolbar = histogram_card.layout().itemAt(0).widget()

        self.assertEqual(line_card.sizePolicy().verticalPolicy(), QSizePolicy.Policy.Fixed)
        self.assertEqual(histogram_card.sizePolicy().verticalPolicy(), QSizePolicy.Policy.Fixed)
        self.assertEqual(line_card.layout().stretch(1), 0)
        self.assertEqual(histogram_card.layout().stretch(1), 0)
        self.assertEqual(line_toolbar.height(), 40)
        self.assertEqual(line_toolbar.minimumHeight(), 40)
        self.assertEqual(line_toolbar.maximumHeight(), 40)
        self.assertEqual(histogram_toolbar.height(), 40)
        self.assertEqual(histogram_toolbar.minimumHeight(), 40)
        self.assertEqual(histogram_toolbar.maximumHeight(), 40)

    def test_multi_property_tab_applies_existing_width_to_new_panel_graphs(self):
        tab = MultiPropertyTab()

        tab.set_available_width(900)
        tab.set_dataset({"label": "Demo", "available_projects": []})

        panel = tab._tabs.widget(0)
        self.assertEqual(panel.line_scan_canvas.width(), 800)
        self.assertEqual(panel.histogram_canvas.width(), 800)
        self.assertEqual(panel.histogram_canvas.width(), panel.line_scan_canvas.width())

    def test_default_histogram_canvas_matches_line_plot_width(self):
        from viewer.line_scan_canvas import _W as line_width
        from viewer.histogram_canvas import _W as histogram_width

        self.assertEqual(histogram_width, line_width)

    def test_default_line_scan_canvas_stays_single_view_width(self):
        from viewer.line_scan_canvas import _W as line_width

        self.assertEqual(line_width, 600)

    def test_multi_property_line_scan_series_uses_selected_property_labels(self):
        panel = MultiPropertyPanel.__new__(MultiPropertyPanel)
        panel._selected_keys = ["p1", "p2"]
        panel._property_labels = {"p2": "Renamed Stress"}
        panel._scalar_defs = [
            {"label": "Property 1", "value": "p1", "array": "p1"},
            {"label": "Property 2", "value": "p2", "array": "p2"},
        ]
        panel._grid_cache = {
            "p1": (
                np.array([[0.0, 1.0], [0.0, 1.0]]),
                np.array([[0.0, 0.0], [2.0, 2.0]]),
                np.array([[1.0, 2.0], [3.0, 4.0]]),
            ),
            "p2": (
                np.array([[0.0, 1.0], [0.0, 1.0]]),
                np.array([[0.0, 0.0], [2.0, 2.0]]),
                np.array([[5.0, 6.0], [7.0, 8.0]]),
            ),
        }
        panel._line_scan_direction = "horizontal"
        panel._line_scan_y = 2.0
        panel._line_scan_x = None

        series, title, x_label = MultiPropertyPanel._build_line_scan_series(panel)

        self.assertEqual([item["name"] for item in series], ["Property 1", "Renamed Stress"])
        np.testing.assert_array_equal(series[0]["y"], np.array([3.0, 4.0]))
        np.testing.assert_array_equal(series[1]["y"], np.array([7.0, 8.0]))
        self.assertEqual(title, "Horizontal Scan at Y=2.00")
        self.assertEqual(x_label, "X Position")

    def test_multi_property_histogram_series_uses_selected_property_labels(self):
        panel = MultiPropertyPanel.__new__(MultiPropertyPanel)
        panel._selected_keys = ["p1", "p2"]
        panel._property_labels = {"p2": "Renamed Stress"}
        panel._scalar_defs = [
            {"label": "Property 1", "value": "p1", "array": "p1"},
            {"label": "Property 2", "value": "p2", "array": "p2"},
        ]
        panel._grid_cache = {
            "p1": (None, None, np.array([[1.0, 2.0]])),
            "p2": (None, None, np.array([[3.0, 4.0]])),
        }

        series, label = MultiPropertyPanel._build_histogram_series(panel)

        self.assertEqual([item["name"] for item in series], ["Property 1", "Renamed Stress"])
        self.assertEqual([item["values"].tolist() for item in series], [[[1.0, 2.0]], [[3.0, 4.0]]])
        self.assertEqual(label, "Value")

    def test_multi_property_line_scan_click_sets_shared_position_without_changing_range(self):
        panel = MultiPropertyPanel.__new__(MultiPropertyPanel)
        panel._selected_keys = ["p1"]
        panel._active_key = None
        panel._ranges = {"p1": {"data_min": 1.0, "data_max": 4.0}}
        panel._grid_cache = {
            "p1": (
                np.array([[0.0, 1.0], [0.0, 1.0]]),
                np.array([[0.0, 0.0], [2.0, 2.0]]),
                np.array([[1.0, 2.0], [3.0, 4.0]]),
            )
        }
        panel.line_mode_check = _ToggleStub(True)
        panel._line_scan_direction = "horizontal"
        panel._line_scan_y = None
        panel._line_scan_x = None
        panel._click_count = 0
        panel._first_click_value = None
        panel.status_label = _LabelStub()
        panel._sync_selected_bullets = lambda: None
        panel._sync_top_range_controls = lambda: None
        panel._render_count = 0
        panel._render_all = lambda: setattr(panel, "_render_count", panel._render_count + 1)

        MultiPropertyPanel._handle_cell_click(panel, "p1", 1.0, 2.0)

        self.assertEqual(panel._active_key, "p1")
        self.assertEqual(panel._line_scan_y, 2.0)
        self.assertIsNone(panel._line_scan_x)
        self.assertEqual(panel._click_count, 0)
        self.assertNotIn("selected_min", panel._ranges["p1"])
        self.assertEqual(panel._render_count, 1)
        self.assertIn("Line scan", panel.status_label.text)

    def test_multi_property_passes_line_overlay_to_all_maps(self):
        class FakeReader:
            dimensions = (2, 2, 1)

            def get_interpolated_slice(self, *, axis, index, scalar_name, component, resolution):
                x_grid = np.array([[0.0, 1.0], [0.0, 1.0]])
                y_grid = np.array([[0.0, 0.0], [1.0, 1.0]])
                z_grid = np.array([[1.0, 2.0], [3.0, 4.0]])
                return x_grid, y_grid, z_grid, {}

        original_get_reader = multi_property_panel_module.get_reader
        multi_property_panel_module.get_reader = lambda _path: FakeReader()
        self.addCleanup(lambda: setattr(multi_property_panel_module, "get_reader", original_get_reader))
        cells = {"p1": _CellStub(), "p2": _CellStub()}
        panel = MultiPropertyPanel.__new__(MultiPropertyPanel)
        panel.file_combo = _ComboStub("demo.vts")
        panel.palette_combo = _ComboStub("aqua-fire")
        panel.type_combo = _ComboStub("heatmap")
        panel.interfaces_on = _ToggleStub(False)
        panel.line_mode_check = _ToggleStub(True)
        panel.show_line_check = _ToggleStub(True)
        panel.line_grid_check = _ToggleStub(True)
        panel.histogram_grid_check = _ToggleStub(True)
        panel.histogram_bins_slider = _SliderStub(30)
        panel.line_scan_canvas = type("LineCanvasStub", (), {"render_lines": lambda *args, **kwargs: None})()
        panel.histogram_canvas = type("HistogramCanvasStub", (), {"render_histograms": lambda *args, **kwargs: None})()
        panel._line_scan_direction = "vertical"
        panel._line_scan_x = 1.0
        panel._line_scan_y = None
        panel._selected_keys = ["p1", "p2"]
        panel._cells = cells
        panel._ranges = {}
        panel._property_labels = {}
        panel._grid_cache = {}
        panel._scalar_defs = [
            {"label": "Property 1", "value": "p1", "array": "p1"},
            {"label": "Property 2", "value": "p2", "array": "p2"},
        ]
        panel.status_label = _LabelStub()
        panel._sync_cells = lambda reset_cell_widths=True: None
        panel._build_overlay_grid = lambda file_path, axis: None

        MultiPropertyPanel._render_all(panel)

        self.assertEqual(cells["p1"].line_overlay, ("vertical", 1.0))
        self.assertEqual(cells["p2"].line_overlay, ("vertical", 1.0))

    def test_multi_property_successful_render_calls_frequency_graph(self):
        class FakeReader:
            dimensions = (2, 2, 1)

            def get_interpolated_slice(self, *, axis, index, scalar_name, component, resolution):
                x_grid = np.array([[0.0, 1.0], [0.0, 1.0]])
                y_grid = np.array([[0.0, 0.0], [1.0, 1.0]])
                z_grid = np.array([[1.0, 2.0], [3.0, 4.0]])
                return x_grid, y_grid, z_grid, {}

        original_get_reader = multi_property_panel_module.get_reader
        multi_property_panel_module.get_reader = lambda _path: FakeReader()
        self.addCleanup(lambda: setattr(multi_property_panel_module, "get_reader", original_get_reader))
        panel = MultiPropertyPanel.__new__(MultiPropertyPanel)
        panel.file_combo = _ComboStub("demo.vts")
        panel.palette_combo = _ComboStub("aqua-fire")
        panel.type_combo = _ComboStub("heatmap")
        panel.interfaces_on = _ToggleStub(False)
        panel.line_mode_check = _ToggleStub(False)
        panel.show_line_check = _ToggleStub(True)
        panel.line_grid_check = _ToggleStub(True)
        panel.histogram_grid_check = _ToggleStub(True)
        panel.histogram_bins_slider = _SliderStub(30)
        panel.analysis_value_label_edit = _LineEditStub("Stress (MPa)")
        panel.line_scan_canvas = _AnalysisCanvasStub()
        panel.histogram_canvas = _AnalysisCanvasStub()
        panel.analysis_card = type("AnalysisCardStub", (), {"setVisible": lambda self, visible: setattr(self, "visible", visible), "isHidden": lambda self: not getattr(self, "visible", False)})()
        panel._line_scan_direction = "horizontal"
        panel._line_scan_x = None
        panel._line_scan_y = None
        panel._selected_keys = ["p1"]
        panel._cells = {"p1": _CellStub()}
        panel._ranges = {}
        panel._property_labels = {}
        panel._grid_cache = {}
        panel._scalar_defs = [{"label": "Property 1", "value": "p1", "array": "p1"}]
        panel.status_label = _LabelStub()
        panel._sync_cells = lambda reset_cell_widths=True: None
        panel._build_overlay_grid = lambda file_path, axis: None

        MultiPropertyPanel._render_all(panel)

        self.assertEqual(len(panel.histogram_canvas.calls), 1)
        call_name, args, kwargs = panel.histogram_canvas.calls[0]
        self.assertEqual(call_name, "histograms")
        self.assertEqual(args[0][0]["name"], "Property 1")
        np.testing.assert_array_equal(args[0][0]["values"], np.array([[1.0, 2.0], [3.0, 4.0]]))
        self.assertEqual(panel.line_scan_canvas.calls[0][2]["y_label"], "Stress (MPa)")
        self.assertEqual(kwargs["label"], "Stress (MPa)")
        self.assertEqual(kwargs["bins"], 30)
        self.assertFalse(panel.analysis_card.isHidden())
        self.assertTrue(panel.histogram_canvas.geometry_updated)
        self.assertTrue(panel.histogram_canvas.repainted)

    def test_multi_property_analysis_value_label_falls_back_to_value(self):
        panel = MultiPropertyPanel.__new__(MultiPropertyPanel)
        panel.analysis_value_label_edit = _LineEditStub("   ")

        self.assertEqual(MultiPropertyPanel._analysis_value_label(panel), "Value")

    def test_multi_property_graph_control_change_does_not_rerender_heatmaps(self):
        panel = MultiPropertyPanel.__new__(MultiPropertyPanel)
        panel.file_combo = _ComboStub("demo.vts")
        panel._selected_keys = ["p1"]
        panel._grid_cache = {
            "p1": (
                np.array([[0.0, 1.0], [0.0, 1.0]]),
                np.array([[0.0, 0.0], [1.0, 1.0]]),
                np.array([[1.0, 2.0], [3.0, 4.0]]),
            )
        }
        panel._scalar_defs = [{"label": "Property 1", "value": "p1", "array": "p1"}]
        panel._property_labels = {}
        panel._line_scan_direction = "horizontal"
        panel._line_scan_y = None
        panel._line_scan_x = None
        panel.line_grid_check = _ToggleStub(False)
        panel.histogram_grid_check = _ToggleStub(False)
        panel.histogram_bins_slider = _SliderStub(40)
        panel.line_scan_canvas = _AnalysisCanvasStub()
        panel.histogram_canvas = _AnalysisCanvasStub()
        panel.analysis_card = type(
            "AnalysisCardStub",
            (),
            {
                "setVisible": lambda self, visible: setattr(self, "visible", visible),
                "isHidden": lambda self: not getattr(self, "visible", False),
            },
        )()
        panel._render_count = 0
        panel._render_all = lambda: setattr(panel, "_render_count", panel._render_count + 1)

        MultiPropertyPanel._on_analysis_control_changed(panel)

        self.assertEqual(panel._render_count, 0)
        self.assertEqual(len(panel.line_scan_canvas.calls), 1)
        self.assertEqual(len(panel.histogram_canvas.calls), 1)
        self.assertFalse(panel.analysis_card.isHidden())

    def test_multi_property_graph_grid_toggles_do_not_rerender_heatmaps(self):
        panel = MultiPropertyPanel({"available_projects": []})
        panel.file_combo.addItem("demo.vts", "demo.vts")
        panel.file_combo.setCurrentIndex(panel.file_combo.count() - 1)
        panel._selected_keys = ["p1"]
        panel._grid_cache = {
            "p1": (
                np.array([[0.0, 1.0], [0.0, 1.0]]),
                np.array([[0.0, 0.0], [1.0, 1.0]]),
                np.array([[1.0, 2.0], [3.0, 4.0]]),
            )
        }
        panel._scalar_defs = [{"label": "Property 1", "value": "p1", "array": "p1"}]
        panel.line_scan_canvas = _AnalysisCanvasStub()
        panel.histogram_canvas = _AnalysisCanvasStub()
        panel._render_count = 0
        panel._render_all = lambda: setattr(panel, "_render_count", panel._render_count + 1)

        panel.line_grid_check.setChecked(False)
        panel.histogram_grid_check.setChecked(False)

        self.assertEqual(panel._render_count, 0)
        self.assertEqual(len(panel.line_scan_canvas.calls), 2)
        self.assertEqual(len(panel.histogram_canvas.calls), 2)

    def test_frequency_graph_ignores_infinite_values_from_add_all_properties(self):
        canvas = HistogramCanvas.__new__(HistogramCanvas)
        canvas._canvas_width = 480
        canvas._canvas_height = 300
        canvas._web_view = None

        figure = canvas._figure_for_histograms(
            [
                {"name": "Good", "values": np.array([1.0, 2.0, 3.0])},
                {"name": "Bad Inf", "values": np.array([np.inf, -np.inf, np.nan])},
            ],
            label="Value",
            bins=30,
        )

        self.assertEqual(len(figure.data), 1)
        self.assertEqual(figure.data[0].name, "Good")
        self.assertTrue(np.all(np.isfinite(figure.data[0].x)))

    def test_frequency_graph_reserves_legend_space_for_ten_properties(self):
        canvas = HistogramCanvas.__new__(HistogramCanvas)
        canvas._canvas_width = 600
        canvas._canvas_height = 300
        canvas._web_view = None
        series = [
            {"name": f"Property {index}", "values": np.array([index, index + 1], dtype=float)}
            for index in range(10)
        ]

        figure = canvas._figure_for_histograms(series, label="Value", bins=30)

        self.assertEqual(len(figure.data), 10)
        self.assertEqual(figure.layout.legend.orientation, "v")
        self.assertGreater(figure.layout.legend.x, 1.0)
        self.assertEqual(figure.layout.legend.y, 1.0)
        self.assertEqual(figure.layout.legend.yanchor, "top")
        self.assertGreaterEqual(figure.layout.margin.r, 180)
        self.assertLessEqual(len(figure.data[0].x), 30)
        self.assertTrue(np.all(np.isfinite(figure.data[0].x)))
        self.assertTrue(np.all(np.isfinite(figure.data[0].y)))

    def test_frequency_graph_sends_compact_binned_data_to_plotly(self):
        canvas = HistogramCanvas.__new__(HistogramCanvas)
        canvas._canvas_width = 600
        canvas._canvas_height = 300
        canvas._web_view = None
        series = [
            {"name": f"Stresses[{index}]", "values": np.arange(25600, dtype=float) + index}
            for index in range(5)
        ]

        figure = canvas._figure_for_histograms(series, label="Value", bins=30)

        self.assertEqual(len(figure.data), 5)
        self.assertTrue(all(trace.type == "bar" for trace in figure.data))
        self.assertTrue(all(len(trace.x) <= 30 for trace in figure.data))

    def test_multi_property_unit_conversion_resets_ranges_and_rerenders(self):
        panel = MultiPropertyPanel.__new__(MultiPropertyPanel)
        panel._ranges = {"p1": {"selected_min": 2.0, "selected_max": 4.0}}
        panel._render_count = 0

        def render_all():
            panel._render_count += 1

        panel._render_all = render_all

        MultiPropertyPanel._on_unit_scale_changed(panel)

        self.assertEqual(panel._ranges, {})
        self.assertEqual(panel._render_count, 1)

    def test_multi_property_has_export_png_button_in_top_controls(self):
        panel = MultiPropertyPanel({"available_projects": []})
        controls_card = panel.layout().itemAt(0).widget()
        controls_layout = controls_card.layout()
        selection_layout = controls_layout.itemAt(0).widget().layout()

        self.assertEqual(panel.export_button.text(), "Export PNG")
        self.assertIs(selection_layout.itemAt(8).widget(), panel.export_button)

    def test_multi_property_export_prefers_high_resolution_renderer(self):
        original_dialog = multi_property_panel_module.QFileDialog.getSaveFileName
        multi_property_panel_module.QFileDialog.getSaveFileName = lambda *args, **kwargs: ("multi_property_export", "PNG (*.png)")
        self.addCleanup(lambda: setattr(multi_property_panel_module.QFileDialog, "getSaveFileName", original_dialog))
        panel = MultiPropertyPanel.__new__(MultiPropertyPanel)
        panel._selected_keys = ["p1"]
        panel.rows_widget = _RowsWidgetStub()
        panel._save_high_resolution_export_png = lambda path: path == "multi_property_export.png"
        panel._grab_export_pixmap = lambda: self.fail("live capture must not run after high-resolution export succeeds")
        panel.status_label = _LabelStub()

        MultiPropertyPanel._export_png(panel)

        self.assertFalse(panel.rows_widget.grabbed)
        self.assertEqual(panel.status_label.text, "Exported multi_property_export.png")

    def test_multi_property_export_falls_back_to_live_capture(self):
        original_dialog = multi_property_panel_module.QFileDialog.getSaveFileName
        multi_property_panel_module.QFileDialog.getSaveFileName = lambda *args, **kwargs: ("multi_property_export", "PNG (*.png)")
        self.addCleanup(lambda: setattr(multi_property_panel_module.QFileDialog, "getSaveFileName", original_dialog))
        export_pixmap = _PixmapStub()
        panel = MultiPropertyPanel.__new__(MultiPropertyPanel)
        panel._selected_keys = ["p1"]
        panel.rows_widget = _RowsWidgetStub()
        panel._save_high_resolution_export_png = lambda path: False
        panel._grab_export_pixmap = lambda: export_pixmap
        panel.status_label = _LabelStub()

        MultiPropertyPanel._export_png(panel)

        self.assertEqual(export_pixmap.saved_path, ("multi_property_export.png", "PNG"))
        self.assertEqual(panel.status_label.text, "Exported multi_property_export.png")

    def test_multi_property_export_payload_uses_export_resolution(self):
        class ReaderStub:
            def __init__(self):
                self.resolution = None

            def get_interpolated_slice(self, *, axis, index, scalar_name, component, resolution):
                self.resolution = resolution
                values = np.arange(16, dtype=float).reshape(4, 4)
                x_grid, y_grid = np.meshgrid(np.arange(4, dtype=float), np.arange(4, dtype=float))
                return x_grid, y_grid, values, {}

        panel = MultiPropertyPanel.__new__(MultiPropertyPanel)
        panel._property_labels = {}
        panel._ranges = {"p1": {"selected_min": 2.0, "selected_max": 12.0}}
        panel._scalar_defs = [{"label": "Property 1", "value": "p1", "array": "p1", "scale": 1.0}]
        panel._get_display_params = lambda label, override_label=None: (1.0, override_label or label)
        reader = ReaderStub()

        payload = panel._build_export_property_payload(
            reader,
            axis="z",
            orientation=multi_property_panel_module.Heatmap2DOrientation(0),
            key="p1",
            cmap=palette_to_cmap("aqua-fire"),
            plot_type="heatmap",
            overlay_grid=None,
            line_overlay=None,
            resolution=multi_property_panel_module.DEFAULTS["export_resolution"],
        )

        self.assertEqual(reader.resolution, multi_property_panel_module.DEFAULTS["export_resolution"])
        self.assertEqual(payload["z_grid"].shape, (4, 4))
        self.assertEqual(payload["vmin"], 2.0)
        self.assertEqual(payload["vmax"], 12.0)

    def test_multi_property_high_resolution_renderer_outputs_1000_pixel_heatmap(self):
        values = np.arange(48, dtype=float).reshape(6, 8)
        x_grid, y_grid = np.meshgrid(np.arange(8, dtype=float), np.arange(6, dtype=float))
        payload = {
            "x_grid": x_grid,
            "y_grid": y_grid,
            "z_grid": values,
            "cmap": palette_to_cmap("aqua-fire"),
            "vmin": float(values.min()),
            "vmax": float(values.max()),
            "label": "Property 1",
            "plot_type": "heatmap",
            "overlay_grid": None,
            "line_overlay": None,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "multi_property.png"

            saved = save_multi_property_png(
                str(output_path),
                rows=[[payload]],
                logo_path=None,
                dpi=300,
            )
            image = multi_property_panel_module.QPixmap(str(output_path))

        self.assertTrue(saved)
        self.assertFalse(image.isNull())
        self.assertGreaterEqual(image.width(), 1000)
        self.assertGreaterEqual(image.height(), 750)

    def test_multi_property_export_grabs_live_rows_widget_geometry(self):
        panel = MultiPropertyPanel.__new__(MultiPropertyPanel)
        panel.rows_widget = _LiveRowsWidgetStub()
        panel._row_widgets = [object()]
        panel._cells = {"p1": type("CellStub", (), {"controls": _ControlsStub()})()}

        pixmap = MultiPropertyPanel._grab_export_pixmap(panel)

        self.assertIs(pixmap, panel.rows_widget.pixmap)
        self.assertTrue(panel.rows_widget.grabbed)
        self.assertTrue(panel.rows_widget.geometry_updated)
        self.assertEqual(panel._cells["p1"].controls.hidden_values, [True, False])
        self.assertFalse(panel._cells["p1"].controls.isHidden())

    def test_multi_property_export_restores_controls_after_capture(self):
        original_dialog = multi_property_panel_module.QFileDialog.getSaveFileName
        multi_property_panel_module.QFileDialog.getSaveFileName = lambda *args, **kwargs: ("multi_property_export.png", "PNG (*.png)")
        self.addCleanup(lambda: setattr(multi_property_panel_module.QFileDialog, "getSaveFileName", original_dialog))
        export_pixmap = _PixmapStub()
        cell = type("CellStub", (), {"controls": _ControlsStub()})()
        panel = MultiPropertyPanel.__new__(MultiPropertyPanel)
        panel._selected_keys = ["p1"]
        panel._cells = {"p1": cell}
        panel.rows_widget = _RowsWidgetStub()
        panel._grab_export_pixmap = lambda: export_pixmap
        panel.status_label = _LabelStub()

        MultiPropertyPanel._export_png(panel)

        self.assertEqual(cell.controls.hidden_values, [])
        self.assertFalse(cell.controls.isHidden())

    def test_multi_property_export_cell_pixmap_excludes_controls_height(self):
        cell = MultiPropertyCell("phase", "Phase", bottom_row=False)
        cell.colorbar.setFixedSize(120, 30)
        cell.heatmap.setFixedSize(120, 80)
        cell.controls.setFixedSize(120, 50)

        pixmap = MultiPropertyPanel._grab_export_cell(MultiPropertyPanel.__new__(MultiPropertyPanel), cell)

        self.assertEqual(pixmap.width(), 120)
        self.assertEqual(pixmap.height(), 110)

    def test_multi_property_export_skips_without_properties(self):
        panel = MultiPropertyPanel.__new__(MultiPropertyPanel)
        panel._selected_keys = []
        panel.rows_widget = _RowsWidgetStub()
        panel.status_label = _LabelStub()

        MultiPropertyPanel._export_png(panel)

        self.assertFalse(panel.rows_widget.grabbed)
        self.assertEqual(panel.status_label.text, "Add properties before export")

    def test_multi_property_builds_interfaces_overlay_when_enabled(self):
        class FakeReader:
            def get_interpolated_slice(self, *, axis, index, scalar_name, component, resolution):
                self.axis = axis
                self.index = index
                self.scalar_name = scalar_name
                self.component = component
                self.resolution = resolution
                x_grid = np.array([[0.0, 1.0], [0.0, 1.0]])
                y_grid = np.array([[0.0, 0.0], [1.0, 1.0]])
                z_grid = np.array([[0.0, 2.0], [3.0, 4.0]])
                return x_grid, y_grid, z_grid, {}

        original_get_reader = multi_property_panel_module.get_reader
        fake_reader = FakeReader()
        multi_property_panel_module.get_reader = lambda _path: fake_reader
        self.addCleanup(lambda: setattr(multi_property_panel_module, "get_reader", original_get_reader))
        panel = MultiPropertyPanel.__new__(MultiPropertyPanel)
        panel.interfaces_on = _ToggleStub(True)

        with tempfile.TemporaryDirectory() as tmp:
            vtk_dir = Path(tmp)
            source = vtk_dir / "ElasticStrains_00005000.vts"
            phase = vtk_dir / "PhaseField_00005000.vts"
            source.write_text("", encoding="utf-8")
            phase.write_text("", encoding="utf-8")

            overlay = MultiPropertyPanel._build_overlay_grid(panel, str(source), "z")

        self.assertEqual(fake_reader.scalar_name, "Interfaces")
        self.assertIsNone(fake_reader.component)
        self.assertEqual(fake_reader.resolution, 160)
        np.testing.assert_equal(overlay["z"], np.array([[0.0, 2.0], [3.0, 4.0]]))

    def test_multi_property_phase_overlay_file_prefers_phasefield_over_distorted(self):
        with tempfile.TemporaryDirectory() as tmp:
            vtk_dir = Path(tmp)
            source = vtk_dir / "ElasticStrains_00005000.vts"
            phase = vtk_dir / "PhaseField_00005000.vts"
            distorted = vtk_dir / "PhaseFieldDistorted_00005000.vts"
            source.write_text("", encoding="utf-8")
            phase.write_text("", encoding="utf-8")
            distorted.write_text("", encoding="utf-8")

            self.assertEqual(MultiPropertyPanel._phase_overlay_file(str(source)), phase)

    def test_multi_property_phase_overlay_file_falls_back_to_distorted_phasefield(self):
        with tempfile.TemporaryDirectory() as tmp:
            vtk_dir = Path(tmp)
            source = vtk_dir / "ElasticStrains_00005000.vts"
            distorted = vtk_dir / "PhaseFieldDistorted_00005000.vts"
            source.write_text("", encoding="utf-8")
            distorted.write_text("", encoding="utf-8")

            self.assertEqual(MultiPropertyPanel._phase_overlay_file(str(source)), distorted)

    def test_multi_property_phase_overlay_file_prefers_phasefield_when_source_is_distorted(self):
        with tempfile.TemporaryDirectory() as tmp:
            vtk_dir = Path(tmp)
            phase = vtk_dir / "PhaseField_00005000.vts"
            distorted = vtk_dir / "PhaseFieldDistorted_00005000.vts"
            phase.write_text("", encoding="utf-8")
            distorted.write_text("", encoding="utf-8")

            self.assertEqual(MultiPropertyPanel._phase_overlay_file(str(distorted)), phase)

    def test_multi_property_passes_interfaces_overlay_to_all_maps(self):
        class FakeReader:
            dimensions = (2, 2, 1)

            def get_interpolated_slice(self, *, axis, index, scalar_name, component, resolution):
                x_grid = np.array([[0.0, 1.0], [0.0, 1.0]])
                y_grid = np.array([[0.0, 0.0], [1.0, 1.0]])
                z_grid = np.array([[1.0, 2.0], [3.0, 4.0]])
                return x_grid, y_grid, z_grid, {}

        overlay = {
            "x": np.array([[0.0, 1.0], [0.0, 1.0]]),
            "y": np.array([[0.0, 0.0], [1.0, 1.0]]),
            "z": np.array([[0.0, 2.0], [3.0, 4.0]]),
        }
        cells = {"p1": _CellStub(), "p2": _CellStub()}
        original_get_reader = multi_property_panel_module.get_reader
        multi_property_panel_module.get_reader = lambda _path: FakeReader()
        self.addCleanup(lambda: setattr(multi_property_panel_module, "get_reader", original_get_reader))
        panel = MultiPropertyPanel.__new__(MultiPropertyPanel)
        panel.file_combo = _ComboStub("demo.vts")
        panel.palette_combo = _ComboStub("aqua-fire")
        panel._selected_keys = ["p1", "p2"]
        panel._cells = cells
        panel._ranges = {}
        panel._grid_cache = {}
        panel._scalar_defs = [
            {"label": "Property 1", "value": "p1", "array": "p1"},
            {"label": "Property 2", "value": "p2", "array": "p2"},
        ]
        panel.status_label = _LabelStub()
        panel._lock_layout_sizes = lambda: None
        panel._build_overlay_grid = lambda file_path, axis: overlay

        MultiPropertyPanel._render_all(panel)

        self.assertIs(cells["p1"].overlay_grid, overlay)
        self.assertIs(cells["p2"].overlay_grid, overlay)
        self.assertEqual(set(panel._grid_cache), {"p1", "p2"})

    def test_multi_property_passes_selected_plot_type_to_all_maps(self):
        class FakeReader:
            dimensions = (2, 2, 1)

            def get_interpolated_slice(self, *, axis, index, scalar_name, component, resolution):
                x_grid = np.array([[0.0, 1.0], [0.0, 1.0]])
                y_grid = np.array([[0.0, 0.0], [1.0, 1.0]])
                z_grid = np.array([[1.0, 2.0], [3.0, 4.0]])
                return x_grid, y_grid, z_grid, {}

        cells = {"p1": _CellStub(), "p2": _CellStub()}
        original_get_reader = multi_property_panel_module.get_reader
        multi_property_panel_module.get_reader = lambda _path: FakeReader()
        self.addCleanup(lambda: setattr(multi_property_panel_module, "get_reader", original_get_reader))
        panel = MultiPropertyPanel.__new__(MultiPropertyPanel)
        panel.file_combo = _ComboStub("demo.vts")
        panel.palette_combo = _ComboStub("aqua-fire")
        panel.type_combo = _ComboStub("contour_filled_values")
        panel._selected_keys = ["p1", "p2"]
        panel._cells = cells
        panel._ranges = {}
        panel._scalar_defs = [
            {"label": "Property 1", "value": "p1", "array": "p1"},
            {"label": "Property 2", "value": "p2", "array": "p2"},
        ]
        panel.status_label = _LabelStub()
        panel._lock_layout_sizes = lambda: None
        panel._sync_top_range_controls = lambda: None
        panel._build_overlay_grid = lambda file_path, axis: None

        MultiPropertyPanel._render_all(panel)

        self.assertEqual(cells["p1"].plot_type, "contour_filled_values")
        self.assertEqual(cells["p2"].plot_type, "contour_filled_values")

    def test_multi_property_rotation_is_applied_to_all_maps(self):
        class FakeReader:
            dimensions = (2, 3, 1)

            def get_interpolated_slice(self, *, axis, index, scalar_name, component, resolution):
                x_grid = np.array([[0.0, 1.0, 2.0], [0.0, 1.0, 2.0]])
                y_grid = np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]])
                z_grid = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
                return x_grid, y_grid, z_grid, {}

        cells = {"p1": _CellStub()}
        original_get_reader = multi_property_panel_module.get_reader
        multi_property_panel_module.get_reader = lambda _path: FakeReader()
        self.addCleanup(lambda: setattr(multi_property_panel_module, "get_reader", original_get_reader))
        panel = MultiPropertyPanel.__new__(MultiPropertyPanel)
        panel.file_combo = _ComboStub("demo.vts")
        panel.palette_combo = _ComboStub("aqua-fire")
        panel._selected_keys = ["p1"]
        panel._cells = cells
        panel._ranges = {}
        panel._scalar_defs = [{"label": "Property 1", "value": "p1", "array": "p1"}]
        panel._rotation_degrees = 90
        panel.status_label = _LabelStub()
        panel._lock_layout_sizes = lambda: None
        panel._sync_top_range_controls = lambda: None
        panel._build_overlay_grid = lambda file_path, axis: None

        MultiPropertyPanel._render_all(panel)

        np.testing.assert_equal(cells["p1"].rendered_z, np.rot90(np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]), -1))

    def test_multi_property_unit_conversion_is_applied_to_all_maps(self):
        class FakeReader:
            dimensions = (2, 2, 1)

            def get_interpolated_slice(self, *, axis, index, scalar_name, component, resolution):
                x_grid = np.array([[0.0, 1.0], [0.0, 1.0]])
                y_grid = np.array([[0.0, 0.0], [1.0, 1.0]])
                z_grid = np.array([[1000.0, 2000.0], [3000.0, 4000.0]])
                return x_grid, y_grid, z_grid, {}

        cells = {"p1": _CellStub()}
        original_get_reader = multi_property_panel_module.get_reader
        multi_property_panel_module.get_reader = lambda _path: FakeReader()
        self.addCleanup(lambda: setattr(multi_property_panel_module, "get_reader", original_get_reader))
        panel = MultiPropertyPanel.__new__(MultiPropertyPanel)
        panel.file_combo = _ComboStub("demo.vts")
        panel.palette_combo = _ComboStub("aqua-fire")
        panel.unit_scale_combo = _ComboStub((1e-6, "MPa"))
        panel._selected_keys = ["p1"]
        panel._cells = cells
        panel._ranges = {}
        panel._scalar_defs = [{"label": "Stress", "value": "p1", "array": "p1", "scale": 1.0, "units": "Pa"}]
        panel._rotation_degrees = 0
        panel.status_label = _LabelStub()
        panel._lock_layout_sizes = lambda: None
        panel._sync_top_range_controls = lambda: None
        panel._build_overlay_grid = lambda file_path, axis: None

        MultiPropertyPanel._render_all(panel)

        np.testing.assert_equal(cells["p1"].rendered_z, np.array([[0.001, 0.002], [0.003, 0.004]]))
        self.assertEqual(cells["p1"].rendered_label, "Stress (MPa)")
        self.assertEqual(panel._ranges["p1"]["data_min"], 0.001)
        self.assertEqual(panel._ranges["p1"]["data_max"], 0.004)


if __name__ == "__main__":
    unittest.main()
