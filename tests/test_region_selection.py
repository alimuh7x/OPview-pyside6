"""Select Rectangle (no zoom), Show Rectangle, colours from the region, Reset and time-step persistence."""

import json
import os
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtCore import QEventLoop, QPoint, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from viewer import visible_range as vr
from viewer.heatmap_orientation import Heatmap2DOrientation
from viewer.panel_widget import PanelWidget

_FILES = [
    str(Path("Project1/VTK/Composition_00000000.vts").resolve()),
    str(Path("Project1/VTK/Composition_00050000.vts").resolve()),
]


def _make_panel(files=_FILES) -> PanelWidget:
    return PanelWidget(
        dataset_info={
            "id": "composition",
            "label": "Composition",
            "files": list(files),
            "dataset_config": {
                "label": "Composition",
                "scalars": [{"label": "CL", "array": "MoleFractionsTotal_CL", "component": None}],
            },
            "tab_id": "single_view",
        }
    )


def _axes(controller):
    return Heatmap2DOrientation.plot_axes(*controller._last_display_grids)


def _window(controller, fx0, fx1, fy0, fy1):
    x_axis, y_axis = _axes(controller)
    xs, ys = x_axis[-1] - x_axis[0], y_axis[-1] - y_axis[0]
    return (x_axis[0] + fx0 * xs, x_axis[0] + fx1 * xs, y_axis[0] + fy0 * ys, y_axis[0] + fy1 * ys)


def _expected_range(controller, window):
    """Colour range the automatic scaling must give for `window` (None = the whole heatmap)."""
    x_axis, y_axis = Heatmap2DOrientation.plot_axes(*controller._last_display_grids)
    z = controller._last_display_grids[2]
    if window is None:
        return float(np.nanmin(z)), float(np.nanmax(z))
    return vr.padded_range(*vr.visible_min_max(x_axis, y_axis, z, window))


class RegionSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.panel = _make_panel()
        self.controller = self.panel.controller
        self.controls = self.panel.controls_widget
        self.canvas = self.panel.heatmap_canvas

    def _select(self, window):
        """Deliver a box selection as the canvas would, spying on in-place recolouring and reloads."""
        with mock.patch.object(self.canvas, "restyle_color_range", return_value=True) as restyle, mock.patch.object(
            self.controller, "refresh_view"
        ) as refresh:
            self.controller._on_region_selected(*window)
        return restyle, refresh

    def _zoom(self, window):
        with mock.patch.object(self.canvas, "restyle_color_range", return_value=True), mock.patch.object(
            self.controller, "refresh_view"
        ):
            self.controller._on_zoom_changed(*window)

    # ---- defaults: nothing changes when the new features are off ------------------------------
    def test_defaults_colors_follow_the_region_and_existing_modes_unchanged(self):
        self.assertFalse(hasattr(self.controls, "auto_scale_check"))  # always on: there is no switch
        self.assertTrue(self.controller.auto_scale_enabled())
        self.assertFalse(self.controls.select_region_check.isChecked())
        self.assertFalse(self.controls.show_selection_check.isChecked())
        self.assertTrue(self.controls.click_mode_range_check.isChecked())  # two-point selection is still the default
        self.assertEqual(self.canvas._drag_mode, "pan")
        self.assertIsNone(self.controller._selection_window)

    def _toggle_widgets(self):
        box_layout = self.controls.region_toggles.layout()
        return [box_layout.itemAt(i).widget() for i in range(box_layout.count())]

    def test_toggles_are_ordered_select_points_then_rectangle_then_show(self):
        self.controls.set_available_width(1400)

        self.assertEqual(
            self._toggle_widgets(),
            [self.controls.click_mode_range_check, self.controls.select_region_check, self.controls.show_selection_check],
        )
        self.assertEqual([w.text() for w in self._toggle_widgets()], ["Select Points", "Select Rectangle", "Show Rectangle"])

    def test_toggles_sit_on_the_same_row_as_the_range_inputs_when_there_is_room(self):
        for width, row_name in ((1100, "range_row"), (900, "range_row"), (700, "range_values_row"), (640, "range_values_row")):
            self.controls.set_available_width(width)

            self.assertIs(self.controls.region_toggles.parentWidget(), getattr(self.controls, row_name), width)
            self.assertTrue(self.controls.region_row.isHidden(), width)
            # ... and that row is the one holding the Range min / max inputs
            self.assertIs(self.controls.range_min_spin.parentWidget(), getattr(self.controls, row_name), width)

    def test_the_row_never_needs_more_width_than_the_panel_has(self):
        for width in (374, 450, 520, 570, 610, 640, 700, 900, 1100, 1400):
            self.controls.set_available_width(width)

            holder = self.controls.region_toggles.parentWidget()
            row_layout = holder.layout()
            self.assertLessEqual(row_layout.minimumSize().width(), width, width)

    def test_only_a_very_narrow_panel_puts_the_toggles_on_a_line_below_range(self):
        self.controls.set_available_width(374)

        self.assertIs(self.controls.region_toggles.parentWidget(), self.controls.region_row)
        self.assertFalse(self.controls.region_row.isHidden())
        self.assertLessEqual(self.controls.region_row.layout().minimumSize().width(), 374)
        main = self.controls.layout()
        self.assertEqual(main.indexOf(self.controls.region_row), main.indexOf(self.controls.range_values_row) + 1)

    def test_labels_shorten_only_as_needed_and_return_when_there_is_room(self):
        full = ["Select Points", "Select Rectangle", "Show Rectangle"]
        self.controls.set_available_width(640)
        self.assertNotEqual([w.text() for w in self._toggle_widgets()], full)  # shortened to fit the Range row
        self.assertTrue(all(len(w.text()) <= len(f) for w, f in zip(self._toggle_widgets(), full)))

        self.controls.set_available_width(1400)
        self.assertEqual([w.text() for w in self._toggle_widgets()], ["Select Points", "Select Rectangle", "Show Rectangle"])

    def test_the_toggles_are_not_duplicated_in_the_range_rows(self):
        for width in (374, 640, 900):
            self.controls.set_available_width(width)
            holders = [
                row for row in (self.controls.range_row, self.controls.range_values_row, self.controls.region_row)
                if self.controls.click_mode_range_check in row.findChildren(type(self.controls.click_mode_range_check))
            ]
            self.assertEqual(len(holders), 1, width)

    # ---- select without zoom -------------------------------------------------------------------
    def test_selecting_a_region_does_not_zoom(self):
        window = _window(self.controller, 0.0, 0.5, 0.5, 1.0)

        self._select(window)

        self.assertIsNone(self.controller._zoom_window)  # the sample stays fully visible
        self.assertEqual(self.controller._selection_window, window)


    def test_selected_region_limits_are_applied_to_the_whole_heatmap(self):
        window = _window(self.controller, 0.0, 0.5, 0.5, 1.0)
        x_axis, y_axis = Heatmap2DOrientation.plot_axes(*self.controller._last_display_grids)
        lo, hi = vr.padded_range(*vr.visible_min_max(x_axis, y_axis, self.controller._last_display_grids[2], window))
        full = (self.controller.state.range_min, self.controller.state.range_max)
        self.assertNotEqual((lo, hi), full)

        restyle, refresh = self._select(window)

        self.assertAlmostEqual(self.controller.state.range_min, lo)
        self.assertAlmostEqual(self.controller.state.range_max, hi)
        restyle.assert_called_once()  # in-place colour update ...
        self.assertAlmostEqual(restyle.call_args.args[0], lo)
        self.assertAlmostEqual(restyle.call_args.args[1], hi)
        refresh.assert_not_called()  # ... without a page reload
        self.assertIsNone(self.controller._zoom_window)
        self.assertAlmostEqual(self.controls.range_min_spin.value(), lo, places=6)

    def test_selection_takes_over_from_a_held_manual_range(self):
        self.controls.range_min_spin.setValue(0.04)  # a typed range is held ...
        self.assertFalse(self.controller.auto_scale_enabled())
        window = _window(self.controller, 0.0, 0.5, 0.5, 1.0)

        restyle, _ = self._select(window)  # ... until a region is selected

        self.assertTrue(self.controller.auto_scale_enabled())
        restyle.assert_called_once()
        x_axis, y_axis = Heatmap2DOrientation.plot_axes(*self.controller._last_display_grids)
        lo, hi = vr.padded_range(*vr.visible_min_max(x_axis, y_axis, self.controller._last_display_grids[2], window))
        self.assertAlmostEqual(self.controller.state.range_min, lo)

    def test_selection_does_not_recolour_in_modes_without_an_automatic_range(self):
        self.controls.plot_type_combo.setCurrentIndex(self.controls.plot_type_combo.findData("threshold"))
        before = (self.controller.state.range_min, self.controller.state.range_max)

        restyle, _ = self._select(_window(self.controller, 0.0, 0.5, 0.5, 1.0))

        restyle.assert_not_called()
        self.assertEqual((self.controller.state.range_min, self.controller.state.range_max), before)

    # ---- rectangle visibility -----------------------------------------------------------------
    def test_rectangle_is_hidden_by_default_and_toggling_it_changes_no_values(self):
        window = _window(self.controller, 0.0, 0.5, 0.5, 1.0)
        self._select(window)
        before = (
            self.controller._selection_window,
            self.controller.state.range_min,
            self.controller.state.range_max,
        )
        self.assertFalse(self.canvas._show_selection)

        self.controls.show_selection_check.setChecked(True)
        self.assertTrue(self.canvas._show_selection)
        self.controls.show_selection_check.setChecked(False)

        after = (
            self.controller._selection_window,
            self.controller.state.range_min,
            self.controller.state.range_max,
        )
        self.assertEqual(before, after)

    def test_figure_contains_the_outline_only_when_shown(self):
        window = _window(self.controller, 0.1, 0.4, 0.2, 0.6)
        self._select(window)

        def names():
            self.canvas._selection_window = window
            figure = self.canvas._build_figure(**self._figure_args())
            return [shape.name for shape in figure.layout.shapes or ()]

        self.canvas._show_selection = False
        self.assertEqual(names(), [])
        self.canvas._show_selection = True
        self.assertEqual(sorted(names()), ["opview-selection", "opview-selection-halo"])

    def _figure_args(self):
        x, y, z = self.controller._last_display_grids
        return dict(
            x_grid=x, y_grid=y, z_grid=z, cmap=self.controller._current_palette_cmap(),
            vmin=float(np.nanmin(z)), vmax=float(np.nanmax(z)), line_overlay=None, overlay_grid=None,
        )

    def test_export_payload_carries_the_rectangle_only_when_shown(self):
        window = _window(self.controller, 0.1, 0.4, 0.2, 0.6)
        self._select(window)

        hidden = self.controller._build_high_resolution_export_payload()
        self.controls.show_selection_check.setChecked(True)
        shown = self.controller._build_high_resolution_export_payload()

        self.assertIsNone(hidden["selection_rect"])
        self.assertEqual(shown["selection_rect"], window)

    # ---- zoom and the selection together ------------------------------------------------------
    def test_zoom_still_drives_the_colors_of_the_visible_region(self):
        window = _window(self.controller, 0.0, 0.5, 0.5, 1.0)

        self._zoom(window)

        lo, hi = _expected_range(self.controller, window)
        self.assertAlmostEqual(self.controller.state.range_min, lo)
        self.assertAlmostEqual(self.controller.state.range_max, hi)


    def test_last_action_decides_between_selection_and_visible_region(self):
        selection = _window(self.controller, 0.0, 0.3, 0.0, 0.3)
        zoom = _window(self.controller, 0.5, 1.0, 0.5, 1.0)

        self._select(selection)
        self._zoom(zoom)
        self.assertAlmostEqual(self.controller.state.range_min, _expected_range(self.controller, zoom)[0])
        self.assertAlmostEqual(self.controller.state.range_max, _expected_range(self.controller, zoom)[1])

        self._select(selection)  # selecting again hands control back to the selection
        self.assertAlmostEqual(self.controller.state.range_min, _expected_range(self.controller, selection)[0])
        self.assertAlmostEqual(self.controller.state.range_max, _expected_range(self.controller, selection)[1])


    def test_zooming_out_to_the_full_view_returns_to_the_selection(self):
        selection = _window(self.controller, 0.0, 0.3, 0.0, 0.3)
        self._select(selection)
        self._zoom(_window(self.controller, 0.5, 1.0, 0.5, 1.0))

        self._zoom(_window(self.controller, -0.01, 1.01, -0.01, 1.01))  # Plotly's full-extent report

        self.assertIsNone(self.controller._zoom_window)
        self.assertEqual(self.controller._selection_window, selection)  # a zoom reset does not clear it
        self.assertAlmostEqual(self.controller.state.range_min, _expected_range(self.controller, selection)[0])


    def test_unzoomed_view_without_selection_uses_the_heatmaps_own_min_max(self):
        self._zoom(_window(self.controller, 0.5, 1.0, 0.5, 1.0))
        self._zoom(_window(self.controller, -0.01, 1.01, -0.01, 1.01))

        z = self.controller._last_display_grids[2]
        self.assertAlmostEqual(self.controller.state.range_min, float(np.nanmin(z)))
        self.assertAlmostEqual(self.controller.state.range_max, float(np.nanmax(z)))


    # ---- time steps ---------------------------------------------------------------------------
    def test_selection_is_kept_and_everything_recalculated_for_a_new_time_step(self):
        window = _window(self.controller, 0.0, 0.5, 0.5, 1.0)
        self._select(window)
        first_range = (self.controller.state.range_min, self.controller.state.range_max)

        self.controls.file_combo.setCurrentIndex(1)

        self.assertEqual(self.controller.state.file_path, _FILES[1])
        self.assertEqual(self.controller._selection_window, window)  # preserved
        x_axis, y_axis = Heatmap2DOrientation.plot_axes(*self.controller._last_display_grids)
        lo, hi = vr.padded_range(*vr.visible_min_max(x_axis, y_axis, self.controller._last_display_grids[2], window))
        self.assertAlmostEqual(self.controller.state.range_min, lo)  # colours from the NEW step's region
        self.assertAlmostEqual(self.controller.state.range_max, hi)
        self.assertNotEqual((lo, hi), first_range)

    def test_zoom_is_kept_across_time_steps_while_a_manual_range_is_held(self):
        self.controls.range_min_spin.setValue(0.04)
        window = _window(self.controller, 0.0, 0.5, 0.5, 1.0)
        self._zoom(window)

        self.controls.file_combo.setCurrentIndex(1)

        self.assertEqual(self.controller._zoom_window, window)
        self.assertEqual(self.canvas.zoom_window(), window)  # re-applied to the new page

    def test_rectangle_visibility_survives_a_time_step(self):
        self.controls.show_selection_check.setChecked(True)
        window = _window(self.controller, 0.0, 0.5, 0.5, 1.0)
        self._select(window)

        self.controls.file_combo.setCurrentIndex(1)

        self.assertTrue(self.canvas._show_selection)
        self.assertEqual(self.canvas._selection_window, window)

    def test_selection_outside_a_new_domain_falls_back_safely(self):
        self.controller._selection_window = (500.0, 600.0, 500.0, 600.0)  # far outside the data

        window = self.controller._active_region(*Heatmap2DOrientation.plot_axes(*self.controller._last_display_grids))

        self.assertIsNone(window)  # ignored for the colours ...
        self.assertIsNotNone(self.controller._selection_window)  # ... but kept, in case the domain returns


    def test_rotation_clears_the_selection_like_the_zoom(self):
        self._select(_window(self.controller, 0.0, 0.5, 0.5, 1.0))

        self.controls._set_rotation_degrees(90)

        self.assertIsNone(self.controller._selection_window)

    # ---- exclusivity with the click modes ------------------------------------------------------
    def test_select_region_switches_the_click_modes_off_and_uses_the_select_drag(self):
        self.controls.select_region_check.setChecked(True)

        self.assertFalse(self.controls.click_mode_range_check.isChecked())
        self.assertFalse(self.controller.line_mode_check.isChecked())
        self.assertEqual(self.canvas._drag_mode, "select")
        self.assertEqual(self.controller.state.click_mode, "none")

    def test_switching_select_region_off_restores_pan_and_two_point_selection(self):
        self.controls.select_region_check.setChecked(True)

        self.controls.select_region_check.setChecked(False)

        self.assertEqual(self.canvas._drag_mode, "pan")
        self.assertTrue(self.controls.click_mode_range_check.isChecked())

    def test_turning_on_range_selection_or_line_scan_leaves_select_region(self):
        self.controls.select_region_check.setChecked(True)
        self.controls.click_mode_range_check.setChecked(True)
        self.assertFalse(self.controls.select_region_check.isChecked())
        self.assertEqual(self.canvas._drag_mode, "pan")

        self.controls.select_region_check.setChecked(True)
        self.controller.line_mode_check.setChecked(True)
        self.assertFalse(self.controls.select_region_check.isChecked())
        self.assertEqual(self.canvas._drag_mode, "pan")

    def test_two_point_selection_still_sets_the_range_when_select_region_is_off(self):
        x_axis, y_axis = Heatmap2DOrientation.plot_axes(*self.controller._last_display_grids)
        grid_z = self.controller._last_display_grids[2]
        lo, hi = sorted([float(grid_z[5, 5]), float(grid_z[-5, -5])])

        self.controller._handle_heatmap_click(float(x_axis[5]), float(y_axis[5]))
        self.controller._handle_heatmap_click(float(x_axis[-5]), float(y_axis[-5]))

        self.assertAlmostEqual(self.controller.state.range_min, lo, places=5)
        self.assertAlmostEqual(self.controller.state.range_max, hi, places=5)

    def test_reset_restores_the_full_domain_range_and_clears_the_rectangle(self):
        z = self.controller._last_display_grids[2]
        self._select(_window(self.controller, 0.0, 0.4, 0.5, 1.0))
        self.assertNotAlmostEqual(self.controller.state.range_min, float(np.nanmin(z)), places=9)

        self.controls.reset_button.click()

        self.assertAlmostEqual(self.controller.state.range_min, float(np.nanmin(z)))
        self.assertAlmostEqual(self.controller.state.range_max, float(np.nanmax(z)))
        self.assertAlmostEqual(self.controls.range_min_spin.value(), float(np.nanmin(z)), places=6)
        self.assertIsNone(self.controller._selection_window)  # Reset drops the rectangle too
        self.assertIsNone(self.canvas._selection_window)


    def test_reset_works_after_every_way_of_setting_a_range(self):
        full_stats = self.controller._last_grids[3]
        x_axis, y_axis = Heatmap2DOrientation.plot_axes(*self.controller._last_display_grids)
        actions = {
            "typed": lambda: self.controls.range_min_spin.setValue(0.03),
            "two points": lambda: (
                self.controller._handle_heatmap_click(float(x_axis[5]), float(y_axis[5])),
                self.controller._handle_heatmap_click(float(x_axis[-5]), float(y_axis[-5])),
            ),
            "slider": lambda: self.controls.range_slider.set_values(
                self.controls.range_slider.lower_value(),
                (self.controls.range_slider.lower_value() + self.controls.range_slider.upper_value()) / 2,
                emit_signal=True,
            ),
            "rectangle": lambda: self._select(_window(self.controller, 0.0, 0.4, 0.5, 1.0)),
            "zoom": lambda: self._zoom(_window(self.controller, 0.0, 0.4, 0.5, 1.0)),
        }
        for name, action in actions.items():
            action()

            self.controls.reset_button.click()

            self.assertAlmostEqual(self.controller.state.range_min, full_stats["min"], msg=name)
            self.assertAlmostEqual(self.controller.state.range_max, full_stats["max"], msg=name)

    def test_a_typed_range_is_held_after_a_selection(self):
        self._select(_window(self.controller, 0.0, 0.5, 0.5, 1.0))

        self.controls.range_min_spin.setValue(0.01)

        self.assertFalse(self.controller.auto_scale_enabled())
        self.assertAlmostEqual(self.controller.state.range_min, 0.01, places=6)

    # ---- transformed fields -------------------------------------------------------------------
    # ---- the panel itself ---------------------------------------------------------------------

def _wait_for(predicate, timeout_ms=15000):
    loop = QEventLoop()
    timer = QTimer()
    timer.setInterval(50)
    deadline = QTimer()
    deadline.setSingleShot(True)
    deadline.timeout.connect(loop.quit)
    timer.timeout.connect(lambda: loop.quit() if predicate() else None)
    timer.start()
    deadline.start(timeout_ms)
    loop.exec()
    timer.stop()
    deadline.stop()
    return predicate()


class RealPageSelectionTests(unittest.TestCase):
    """Real drags through QtWebEngine: no zoom, Plotly's own outline removed, optional outline, clicks."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.panel = _make_panel()
        self.panel.resize(1100, 900)
        self.panel.show()
        self.canvas = self.panel.heatmap_canvas
        self.controller = self.panel.controller
        self.controls = self.panel.controls_widget
        self.page = self.canvas._web_view.page()
        self.selected, self.zooms, self.cleared = [], [], []
        self.canvas.region_selected.connect(lambda *a: self.selected.append(a))
        self.canvas.zoom_changed.connect(lambda *a: self.zooms.append(a))
        self.canvas.region_cleared.connect(lambda: self.cleared.append(True))
        self.loads = 0
        self.canvas._web_view.loadFinished.connect(lambda *_: setattr(self, "loads", self.loads + 1))
        self.assertTrue(self._ready())

    def tearDown(self):
        self.panel.close()

    def _js(self, script):
        box = {}
        self.page.runJavaScript(script, lambda value: box.setdefault("value", value))
        _wait_for(lambda: "value" in box, 4000)
        return box.get("value")

    def _ready(self, loads_before=None):
        if loads_before is not None and not _wait_for(lambda: self.loads > loads_before, 15000):
            return False
        return _wait_for(lambda: bool(self._js("!!window.opviewSetSelection && !!document.querySelector('.modebar')")))

    def _settle(self, ms=500):
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()

    def _drag(self, x0, y0, x1, y1):
        target = self.canvas._web_view.focusProxy() or self.canvas._web_view
        QTest.mouseMove(target, QPoint(x0, y0))
        QTest.mousePress(target, Qt.LeftButton, Qt.NoModifier, QPoint(x0, y0))
        for step in range(1, 9):
            QTest.mouseMove(target, QPoint(x0 + (x1 - x0) * step // 8, y0 + (y1 - y0) * step // 8))
            self.app.processEvents()
        QTest.mouseRelease(target, Qt.LeftButton, Qt.NoModifier, QPoint(x1, y1))

    def _click(self, x, y):
        target = self.canvas._web_view.focusProxy() or self.canvas._web_view
        QTest.mouseMove(target, QPoint(x, y))
        QTest.mouseClick(target, Qt.LeftButton, Qt.NoModifier, QPoint(x, y))

    def _layout_state(self):
        return json.loads(
            self._js(
                "var g=document.getElementById('heatmapDiv');"
                "JSON.stringify({selections:(g.layout.selections||[]).length,"
                "shapes:(g.layout.shapes||[]).map(function(s){return s.name||'unnamed'}),"
                "x:g._fullLayout.xaxis.range,y:g._fullLayout.yaxis.range,dragmode:g._fullLayout.dragmode})"
            )
        )

    def _select_mode(self):
        self.controls.select_region_check.setChecked(True)  # in-place: no reload
        self.assertTrue(_wait_for(lambda: self._layout_state()["dragmode"] == "select", 5000))

    def test_drag_in_select_mode_selects_without_zooming_and_leaves_no_outline(self):
        self._select_mode()
        before = self._layout_state()

        self._drag(120, 150, 260, 270)
        self.assertTrue(_wait_for(lambda: len(self.selected) >= 1, 6000))
        self._settle(400)

        after = self._layout_state()
        self.assertEqual(after["x"], before["x"])  # the whole sample stays visible
        self.assertEqual(after["y"], before["y"])
        self.assertEqual(after["selections"], 0)  # Plotly's persistent rectangle was removed
        self.assertEqual([n for n in after["shapes"] if n.startswith("opview-selection")], [])  # hidden by default
        self.assertEqual(self.zooms, [])  # not reported as a zoom
        window = self.controller._selection_window
        self.assertIsNotNone(window)
        x_axis, y_axis = _axes(self.controller)
        self.assertGreater(window[0], float(x_axis[0]))
        self.assertLess(window[1], float(x_axis[-1]))

    def test_drag_recolors_in_place_from_the_selected_rectangle(self):
        self.assertTrue(self.controller.auto_scale_enabled())  # always on
        self._select_mode()
        self._js("window.__sentinel='same page';1")

        self._drag(120, 150, 260, 270)
        self.assertTrue(_wait_for(lambda: self.controller._selection_window is not None, 6000))
        self._settle(600)

        window = self.controller._selection_window
        expected = _expected_range(self.controller, window)
        self.assertAlmostEqual(self.controller.state.range_min, expected[0])
        self.assertAlmostEqual(self.controller.state.range_max, expected[1])
        page = json.loads(self._js(
            "var g=document.getElementById('heatmapDiv');"
            "JSON.stringify({s:window.__sentinel,zmin:g._fullData[0].zmin,zmax:g._fullData[0].zmax})"
        ))
        self.assertEqual(page["s"], "same page")  # no reload
        self.assertAlmostEqual(page["zmin"], self.controller.state.range_min, places=9)
        self.assertAlmostEqual(page["zmax"], self.controller.state.range_max, places=9)
        self.assertEqual(self.zooms, [])  # recolouring never feeds back as a zoom event

    def _ready_after(self, action):
        before = self.loads
        action()
        return self._ready(before)

    def test_outline_appears_when_shown_and_hides_again_without_changing_the_region(self):
        self._select_mode()
        self._drag(120, 150, 260, 270)
        self.assertTrue(_wait_for(lambda: self.controller._selection_window is not None, 6000))
        window = self.controller._selection_window

        self.controls.show_selection_check.setChecked(True)
        self.assertTrue(_wait_for(lambda: len(self._layout_state()["shapes"]) == 2, 5000))
        self.assertEqual(sorted(self._layout_state()["shapes"]), ["opview-selection", "opview-selection-halo"])

        self.controls.show_selection_check.setChecked(False)
        self.assertTrue(_wait_for(lambda: self._layout_state()["shapes"] == [], 5000))
        self.assertEqual(self.controller._selection_window, window)

    def test_outline_and_select_mode_survive_a_reload_for_a_new_time_step(self):
        self.controls.show_selection_check.setChecked(True)
        self._select_mode()
        self._drag(120, 150, 260, 270)
        self.assertTrue(_wait_for(lambda: self.controller._selection_window is not None, 6000))
        window = self.controller._selection_window

        self.assertTrue(self._ready_after(lambda: self.controls.file_combo.setCurrentIndex(1)))
        self._settle(600)

        state = self._layout_state()
        self.assertEqual(state["dragmode"], "select")
        self.assertEqual(sorted(state["shapes"]), ["opview-selection", "opview-selection-halo"])
        self.assertEqual(self.controller._selection_window, window)

    def test_reset_removes_the_rectangle_and_its_outline_on_the_real_page(self):
        self.controls.show_selection_check.setChecked(True)
        self._select_mode()
        self._drag(120, 150, 260, 270)
        self.assertTrue(_wait_for(lambda: len(self._layout_state()["shapes"]) == 2, 6000))

        self.controls.reset_button.click()

        self.assertTrue(_wait_for(lambda: self._layout_state()["shapes"] == [], 6000))
        self.assertIsNone(self.controller._selection_window)
        z = self.controller._last_display_grids[2]
        self.assertAlmostEqual(self.controller.state.range_min, float(np.nanmin(z)))

    def test_zoom_mode_still_zooms_and_reports_the_visible_region(self):
        self._js("Plotly.relayout(document.getElementById('heatmapDiv'),{dragmode:'zoom'});1")
        self._settle(300)

        self._drag(150, 150, 280, 260)

        self.assertTrue(_wait_for(lambda: len(self.zooms) >= 1, 6000))
        self._settle(300)
        self.assertIsNotNone(self.controller._zoom_window)
        self.assertEqual(self.selected, [])

    def test_two_point_click_still_works_through_the_real_page_when_select_region_is_off(self):
        before = (self.controller.state.range_min, self.controller.state.range_max)
        self.assertEqual(self.canvas._drag_mode, "pan")
        self.assertTrue(self.controls.click_mode_range_check.isChecked())

        self._click(150, 150)
        self._click(300, 300)

        self.assertTrue(_wait_for(
            lambda: (self.controller.state.range_min, self.controller.state.range_max) != before, 8000))


if __name__ == "__main__":
    unittest.main()
