"""Auto Scale on Zoom in Single View: zoom, pan, reset, manual override, time steps, export."""

import os
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from viewer import visible_range as vr
from viewer.heatmap_orientation import Heatmap2DOrientation
from viewer.panel_widget import PanelWidget

_FILES = [
    str(Path("Project1/VTK/Composition_00000000.vts").resolve()),
    str(Path("Project1/VTK/Composition_00050000.vts").resolve()),
]


def _make_panel() -> PanelWidget:
    return PanelWidget(
        dataset_info={
            "id": "composition",
            "label": "Composition",
            "files": list(_FILES),
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
    """A zoom window given as fractions of the full domain."""
    x_axis, y_axis = _axes(controller)
    x_span, y_span = x_axis[-1] - x_axis[0], y_axis[-1] - y_axis[0]
    return (
        x_axis[0] + fx0 * x_span,
        x_axis[0] + fx1 * x_span,
        y_axis[0] + fy0 * y_span,
        y_axis[0] + fy1 * y_span,
    )


class AutoScaleZoomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.panel = _make_panel()
        self.controller = self.panel.controller
        self.controls = self.panel.controls_widget
        self.canvas = self.panel.heatmap_canvas

    def _enable(self):
        self.controls.auto_scale_check.setChecked(True)  # real toggle -> full render
        self.assertTrue(self.controller.auto_scale_enabled())

    def _expected_visible_range(self, window):
        x_axis, y_axis = _axes(self.controller)
        z = self.controller._last_display_grids[2]
        return vr.padded_range(*vr.visible_min_max(x_axis, y_axis, z, window))

    def _zoom(self, window):
        """Deliver a settled zoom event, recording what the controller does with it."""
        with mock.patch.object(self.canvas, "restyle_color_range", return_value=True) as restyle, mock.patch.object(
            self.controller, "refresh_view"
        ) as refresh:
            self.controller._on_zoom_changed(*window)
        return restyle, refresh

    # ---- defaults ------------------------------------------------------------------------------
    def test_auto_scale_is_off_by_default_and_changes_nothing(self):
        self.assertFalse(self.controls.auto_scale_check.isChecked())
        self.assertFalse(self.controller.auto_scale_enabled())
        before = (self.controller.state.range_min, self.controller.state.range_max)

        restyle, _ = self._zoom(_window(self.controller, 0.2, 0.5, 0.2, 0.5))

        restyle.assert_not_called()
        self.assertEqual((self.controller.state.range_min, self.controller.state.range_max), before)

    # ---- zoom, pan, reset ---------------------------------------------------------------------
    def test_zoom_recolors_in_place_to_the_visible_min_max(self):
        self._enable()
        window = _window(self.controller, 0.0, 0.5, 0.5, 1.0)
        full_range = (self.controller.state.range_min, self.controller.state.range_max)

        restyle, refresh = self._zoom(window)

        lo, hi = self._expected_visible_range(window)
        self.assertNotEqual((lo, hi), full_range)
        self.assertAlmostEqual(self.controller.state.range_min, lo)
        self.assertAlmostEqual(self.controller.state.range_max, hi)
        restyle.assert_called_once()
        self.assertAlmostEqual(restyle.call_args.args[0], lo)
        self.assertAlmostEqual(restyle.call_args.args[1], hi)
        refresh.assert_not_called()  # no page reload for a colour-only update

    def test_zoom_updates_spin_boxes_and_slider(self):
        self._enable()
        window = _window(self.controller, 0.0, 0.5, 0.5, 1.0)

        self._zoom(window)

        lo, hi = self._expected_visible_range(window)
        self.assertAlmostEqual(self.controls.range_min_spin.value(), lo, places=6)
        self.assertAlmostEqual(self.controls.range_max_spin.value(), hi, places=6)
        self.assertAlmostEqual(self.controls.range_slider.lower_value(), lo, places=6)
        self.assertAlmostEqual(self.controls.range_slider.upper_value(), hi, places=6)

    def test_pan_recolors_for_the_new_window(self):
        self._enable()
        self._zoom(_window(self.controller, 0.0, 0.4, 0.6, 1.0))
        zoomed = (self.controller.state.range_min, self.controller.state.range_max)

        restyle, _ = self._zoom(_window(self.controller, 0.0, 0.4, 0.0, 0.4))  # same size, moved down

        panned = (self.controller.state.range_min, self.controller.state.range_max)
        self.assertNotEqual(panned, zoomed)
        restyle.assert_called_once()
        self.assertAlmostEqual(panned[0], self._expected_visible_range(_window(self.controller, 0.0, 0.4, 0.0, 0.4))[0])

    def test_reset_restores_the_full_domain_range(self):
        self._enable()
        full_stats = self.controller._last_grids[3]
        self._zoom(_window(self.controller, 0.0, 0.5, 0.5, 1.0))

        restyle, _ = self._zoom(_window(self.controller, -0.01, 1.01, -0.01, 1.01))  # what Plotly reports on reset

        self.assertIsNone(self.controller._zoom_window)
        self.assertAlmostEqual(self.controller.state.range_min, full_stats["min"])
        self.assertAlmostEqual(self.controller.state.range_max, full_stats["max"])
        restyle.assert_called_once()

    def test_repeated_identical_window_is_ignored(self):
        self._enable()
        window = _window(self.controller, 0.0, 0.5, 0.5, 1.0)
        self._zoom(window)

        restyle, refresh = self._zoom(window)

        restyle.assert_not_called()  # guards against echoes of a view we already applied
        refresh.assert_not_called()

    def test_restyle_failure_falls_back_to_a_full_render(self):
        self._enable()
        window = _window(self.controller, 0.0, 0.5, 0.5, 1.0)

        with mock.patch.object(self.canvas, "restyle_color_range", return_value=False), mock.patch.object(
            self.controller, "refresh_view"
        ) as refresh:
            self.controller._on_zoom_changed(*window)

        refresh.assert_called_once()

    # ---- manual override and exclusivity -----------------------------------------------------
    def test_typing_a_range_switches_auto_scale_off(self):
        self._enable()
        self._zoom(_window(self.controller, 0.0, 0.5, 0.5, 1.0))

        self.controls.range_min_spin.setValue(0.01)

        self.assertFalse(self.controls.auto_scale_check.isChecked())
        self.assertFalse(self.controller.auto_scale_enabled())
        self.assertAlmostEqual(self.controller.state.range_min, 0.01, places=6)  # the typed value wins

    def test_dragging_the_range_slider_switches_auto_scale_off(self):
        self._enable()
        low, high = self.controls.range_slider.lower_value(), self.controls.range_slider.upper_value()

        self.controls.range_slider.set_values(low, (low + high) / 2.0, emit_signal=True)

        self.assertFalse(self.controls.auto_scale_check.isChecked())

    def test_two_point_map_selection_switches_auto_scale_off_and_sets_the_range(self):
        self._enable()
        x_axis, y_axis = _axes(self.controller)
        grid_z = self.controller._last_display_grids[2]
        p1 = (float(x_axis[5]), float(y_axis[5]))
        p2 = (float(x_axis[-5]), float(y_axis[-5]))
        lo, hi = sorted([float(grid_z[5, 5]), float(grid_z[-5, -5])])

        self.controller._handle_heatmap_click(*p1)
        self.assertTrue(self.controller.auto_scale_enabled())  # one click is not a selection yet
        self.controller._handle_heatmap_click(*p2)

        self.assertFalse(self.controls.auto_scale_check.isChecked())
        self.assertAlmostEqual(self.controller.state.range_min, lo, places=5)
        self.assertAlmostEqual(self.controller.state.range_max, hi, places=5)

    def test_reset_button_switches_auto_scale_off(self):
        self._enable()

        self.controls.reset_button.click()

        self.assertFalse(self.controls.auto_scale_check.isChecked())

    def test_full_scale_and_auto_scale_are_mutually_exclusive(self):
        self._enable()
        self.controls.full_scale_check.setChecked(True)
        self.assertFalse(self.controls.auto_scale_check.isChecked())
        self.assertTrue(self.controls.full_scale_check.isChecked())

        self.controls.auto_scale_check.setChecked(True)
        self.assertFalse(self.controls.full_scale_check.isChecked())
        self.assertTrue(self.controller.auto_scale_enabled())
        self.assertEqual(self.controller.state.colorscale_mode, "normal")

    def test_switching_auto_scale_off_restores_the_full_domain_range(self):
        self._enable()
        full_stats = self.controller._last_grids[3]
        self._zoom(_window(self.controller, 0.0, 0.5, 0.5, 1.0))

        self.controls.auto_scale_check.setChecked(False)

        self.assertAlmostEqual(self.controller.state.range_min, full_stats["min"])
        self.assertAlmostEqual(self.controller.state.range_max, full_stats["max"])

    # ---- incompatible modes ------------------------------------------------------------------
    def test_disabled_in_threshold_mode(self):
        self._enable()
        index = self.controls.plot_type_combo.findData("threshold")

        self.controls.plot_type_combo.setCurrentIndex(index)

        self.assertFalse(self.controls.auto_scale_check.isEnabled())
        self.assertFalse(self.controls.auto_scale_check.isChecked())
        self.assertFalse(self.controller.auto_scale_enabled())

    def test_disabled_for_contour_and_difference_plot_types(self):
        for key in ("contour_filled", "contour_lines", "difference", "heatmap_contour"):
            index = self.controls.plot_type_combo.findData(key)
            if index < 0:
                continue
            self.controls.plot_type_combo.setCurrentIndex(index)
            self.assertFalse(self.controls.auto_scale_check.isEnabled(), key)

    def test_stays_enabled_for_heatmap_and_gradient_magnitude(self):
        for key in ("heatmap", "gradient_magnitude"):
            self.controls.plot_type_combo.setCurrentIndex(self.controls.plot_type_combo.findData(key))
            self.assertTrue(self.controls.auto_scale_check.isEnabled(), key)

    def test_disabled_with_the_discrete_palette(self):
        from viewer.colorscale import DISCRETE_CUSTOM_PALETTE

        self._enable()
        index = self.controls.palette_combo.findData(DISCRETE_CUSTOM_PALETTE)
        self.assertGreaterEqual(index, 0)

        self.controls.palette_combo.setCurrentIndex(index)

        self.assertFalse(self.controls.auto_scale_check.isEnabled())
        self.assertFalse(self.controller.auto_scale_enabled())

    # ---- time steps --------------------------------------------------------------------------
    def test_zoom_is_kept_and_range_recomputed_when_the_time_step_changes(self):
        self._enable()
        window = _window(self.controller, 0.0, 0.5, 0.5, 1.0)
        self._zoom(window)
        first_range = (self.controller.state.range_min, self.controller.state.range_max)

        self.controls.file_combo.setCurrentIndex(1)

        self.assertEqual(self.controller.state.file_path, _FILES[1])
        self.assertTrue(self.controller.auto_scale_enabled())
        self.assertEqual(self.controller._zoom_window, window)  # zoom preserved
        self.assertEqual(self.canvas.zoom_window(), window)  # and re-applied to the new page
        lo, hi = self._expected_visible_range(window)  # visible region of the NEW step
        self.assertAlmostEqual(self.controller.state.range_min, lo)
        self.assertAlmostEqual(self.controller.state.range_max, hi)
        self.assertNotEqual((lo, hi), first_range)

    def test_time_step_change_without_zoom_uses_the_full_domain_range(self):
        self._enable()

        self.controls.file_combo.setCurrentIndex(1)

        full_stats = self.controller._last_grids[3]
        self.assertAlmostEqual(self.controller.state.range_min, full_stats["min"])
        self.assertAlmostEqual(self.controller.state.range_max, full_stats["max"])

    def test_zoom_is_dropped_when_the_view_orientation_changes(self):
        self._enable()
        self._zoom(_window(self.controller, 0.0, 0.5, 0.5, 1.0))

        self.controls._set_rotation_degrees(90)

        self.assertIsNone(self.controller._zoom_window)

    def test_auto_scale_off_keeps_no_stale_zoom_after_a_render(self):
        self._zoom(_window(self.controller, 0.0, 0.5, 0.5, 1.0))
        self.assertIsNotNone(self.controller._zoom_window)

        self.controls.file_combo.setCurrentIndex(1)

        self.assertIsNone(self.controller._zoom_window)  # the page reload reset Plotly's view

    # ---- data and animation untouched ---------------------------------------------------------
    def test_underlying_data_is_not_modified_by_zooming(self):
        self._enable()
        before = np.array(self.controller._last_display_grids[2], copy=True)

        self._zoom(_window(self.controller, 0.0, 0.5, 0.5, 1.0))

        np.testing.assert_array_equal(self.controller._last_display_grids[2], before)

    def test_animation_receives_the_current_fixed_range(self):
        self._enable()
        self._zoom(_window(self.controller, 0.0, 0.5, 0.5, 1.0))

        # the animation starts from state.range_*: one fixed range, the same one the controls show
        self.assertAlmostEqual(self.controller.state.range_min, self.controls.range_min_spin.value(), places=6)
        self.assertAlmostEqual(self.controller.state.range_max, self.controls.range_max_spin.value(), places=6)
        self.assertLess(self.controller.state.range_min, self.controller.state.range_max)

    # ---- PNG export --------------------------------------------------------------------------
    def test_png_export_covers_the_visible_region_with_the_current_colorbar(self):
        self._enable()
        window = _window(self.controller, 0.0, 0.5, 0.5, 1.0)
        self._zoom(window)

        payload = self.controller._build_high_resolution_export_payload()

        x, y = payload["x_grid"], payload["y_grid"]
        cell = (x.max() - x.min()) / max(x.shape[1] - 1, 1)
        self.assertGreaterEqual(float(x.min()), window[0] - cell)
        self.assertLessEqual(float(x.max()), window[1] + cell)
        self.assertGreaterEqual(float(y.min()), window[2] - cell)
        self.assertLessEqual(float(y.max()), window[3] + cell)
        self.assertGreaterEqual(min(payload["z_grid"].shape), 900)  # resolution raised for the zoomed region
        self.assertAlmostEqual(payload["vmin"], self.controller.state.range_min)
        self.assertAlmostEqual(payload["vmax"], self.controller.state.range_max)

    def test_crop_rebuilds_ascending_axes_so_a_mirrored_grid_is_cropped_correctly(self):
        from viewer.heatmap_controller import HeatmapController

        axis = np.arange(11, dtype=float)
        x, y = np.meshgrid(axis[::-1], axis)  # x runs descending along the columns (a rotated grid)
        z = np.arange(121, dtype=float).reshape(11, 11)

        x_crop, y_crop, z_crop = HeatmapController._crop_grid_to_window(x, y, z, (2.0, 4.0, 3.0, 5.0))

        self.assertEqual(float(x_crop.min()), 2.0)
        self.assertEqual(float(x_crop.max()), 4.0)  # still the requested window, not its mirror
        self.assertEqual((float(y_crop.min()), float(y_crop.max())), (3.0, 5.0))
        self.assertEqual(z_crop.shape, x_crop.shape)

    def test_zoomed_export_resolution_is_raised_but_capped(self):
        self._enable()
        controller = self.controller
        half = _window(controller, 0.0, 0.5, 0.0, 0.5)
        tiny = _window(controller, 0.0, 0.001, 0.0, 0.001)

        self.assertEqual(controller._export_resolution_for_zoom(1000, half), 2000)
        self.assertEqual(controller._export_resolution_for_zoom(1000, tiny), controller._EXPORT_MAX_RESOLUTION)

    def test_png_export_of_an_unzoomed_view_is_the_full_domain(self):
        payload = self.controller._build_high_resolution_export_payload()

        x_axis, _ = _axes(self.controller)
        self.assertAlmostEqual(float(payload["x_grid"].min()), float(x_axis[0]), places=6)
        self.assertAlmostEqual(float(payload["x_grid"].max()), float(x_axis[-1]), places=6)


class CanvasZoomPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.panel = _make_panel()
        self.canvas = self.panel.heatmap_canvas

    def test_saved_zoom_is_embedded_and_reapplied_flagged_as_programmatic(self):
        self.canvas.set_zoom_window((10.0, 40.0, 20.0, 50.0))

        page_html = self.canvas._build_html(self._figure())

        self.assertIn('"x": [10.0, 40.0]', page_html)
        self.assertIn('"y": [20.0, 50.0]', page_html)
        self.assertIn("__opviewApplying = true", page_html)

    def _figure(self):
        import plotly.graph_objects as go

        return go.Figure()

    def test_no_saved_zoom_by_default(self):
        self.canvas.set_zoom_window(None)

        page_html = self.canvas._build_html(self._figure())

        self.assertIn("const savedZoom = null;", page_html)

    def test_restyle_is_refused_when_the_new_labels_need_a_wider_colorbar(self):
        self.canvas._colorbar_width = 90  # reserved width for short labels
        self.assertFalse(self.canvas.restyle_color_range(0.0, 1.0e-30))  # "1.0e-30": far wider
        self.assertFalse(self.canvas.restyle_color_range(1.0, 1.0))  # no valid range

    def test_restyle_is_accepted_when_the_new_labels_fit_the_reserved_width(self):
        self.canvas._colorbar_width = 400

        self.assertTrue(self.canvas.restyle_color_range(0.0, 1.0e-30))

    def test_zoom_event_payload_is_turned_into_a_signal(self):
        received = []
        self.canvas.zoom_changed.connect(lambda *args: received.append(args))

        self.canvas.handle_plotly_event("zoom", '{"x": [1.5, 9.5], "y": [2.0, 8.0]}')
        self.canvas.handle_plotly_event("zoom", '{"x": [1.5], "y": [2.0, 8.0]}')  # incomplete: ignored

        self.assertEqual(received, [(1.5, 9.5, 2.0, 8.0)])


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


class PlotlyEventIntegrationTests(unittest.TestCase):
    """Drives the real Plotly page in QtWebEngine: events, in-place restyle and recursion guards."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.panel = _make_panel()
        self.panel.resize(1100, 900)
        self.panel.show()
        self.canvas = self.panel.heatmap_canvas
        self.page = self.canvas._web_view.page()
        self.events = []
        self.loads = 0
        self.canvas.zoom_changed.connect(lambda *args: self.events.append(args))
        self.canvas._web_view.loadFinished.connect(lambda *_: setattr(self, "loads", self.loads + 1))
        self.assertTrue(self._wait_page_ready(), "Plotly page did not become ready")

    def tearDown(self):
        self.panel.close()

    def _js(self, script):
        box = {}
        self.page.runJavaScript(script, lambda value: box.setdefault("value", value))
        _wait_for(lambda: "value" in box, 4000)
        return box.get("value")

    def _wait_page_ready(self, loads_before=None):
        """Wait until the page has (re)loaded and Plotly is drawn; `loads_before` demands a NEW load."""
        if loads_before is not None and not _wait_for(lambda: self.loads > loads_before, 15000):
            return False
        return _wait_for(lambda: bool(self._js("!!window.opviewReportZoom && !!document.querySelector('.modebar')")))

    def _reload(self, action):
        """Run `action` (which re-renders the heatmap) and wait for the new page."""
        before = self.loads
        action()
        return self._wait_page_ready(before)

    def _settle(self, ms=500):
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()

    def test_zoom_pan_and_reset_are_reported_once_after_the_debounce(self):
        # a burst of relayouts (as wheel zooming produces) ...
        for lo in (10, 12, 14, 16):
            self._js(
                "Plotly.relayout(document.getElementById('heatmapDiv'),"
                f"{{'xaxis.range[0]':{lo},'xaxis.range[1]':{lo + 40},'yaxis.range[0]':{lo},'yaxis.range[1]':{lo + 40}}});1"
            )
        self._settle(600)
        self.assertEqual(len(self.events), 1)  # ... is reported once, with the settled window
        self.assertEqual([round(v) for v in self.events[0]], [16, 56, 16, 56])

        self.events.clear()  # pan: same size, moved
        self._js(
            "Plotly.relayout(document.getElementById('heatmapDiv'),"
            "{'xaxis.range[0]':30,'xaxis.range[1]':70,'yaxis.range[0]':16,'yaxis.range[1]':56});1"
        )
        self._settle(500)
        self.assertEqual([round(v) for v in self.events[-1]], [30, 70, 16, 56])

        self.events.clear()  # reset through the modebar button reports the full extent
        self._js("document.querySelector('.modebar-btn[data-attr=\"zoom\"][data-val=\"reset\"]').click();1")
        self._settle(500)
        self.assertEqual(len(self.events), 1)
        x_axis, y_axis = _axes(self.panel.controller)
        self.assertAlmostEqual(self.events[0][0], float(x_axis[0]), delta=1.0)
        self.assertAlmostEqual(self.events[0][1], float(x_axis[-1]), delta=1.0)

    def test_in_place_restyle_recolors_without_reloading_or_new_zoom_events(self):
        self._js(
            "Plotly.relayout(document.getElementById('heatmapDiv'),"
            "{'xaxis.range[0]':20,'xaxis.range[1]':60,'yaxis.range[0]':30,'yaxis.range[1]':70});1"
        )
        self._settle(500)
        self.events.clear()
        self._js("window.__sentinel = 'same page'; 1")

        self.assertTrue(self.canvas.restyle_color_range(0.01, 0.08))
        self._settle(600)

        state = self._js(
            "var g=document.getElementById('heatmapDiv');"
            "JSON.stringify({sentinel:window.__sentinel,zmin:g._fullData[0].zmin,zmax:g._fullData[0].zmax,"
            "x:g._fullLayout.xaxis.range,y:g._fullLayout.yaxis.range,ticks:g._fullData[0].colorbar.tickvals})"
        )
        import json

        data = json.loads(state)
        self.assertEqual(data["sentinel"], "same page")  # the page was not reloaded
        self.assertAlmostEqual(data["zmin"], 0.01)
        self.assertAlmostEqual(data["zmax"], 0.08)
        self.assertEqual(data["x"], [20, 60])  # zoom untouched
        self.assertEqual(data["y"], [30, 70])
        self.assertEqual(len(data["ticks"]), 5)
        self.assertEqual(self.events, [])  # restyle must not feed back as a zoom event

    def test_reapplied_zoom_after_a_reload_is_not_reported_back(self):
        window = (20.0, 60.0, 30.0, 70.0)
        self.assertTrue(self._reload(lambda: self.panel.controls_widget.auto_scale_check.setChecked(True)))
        self.panel.controller._zoom_window = window
        self.events.clear()

        # full render -> the saved zoom is re-applied by the new page
        self.assertTrue(self._reload(self.panel.controller.refresh_view))
        self._settle(800)

        view = self._js(
            "var g=document.getElementById('heatmapDiv');JSON.stringify({x:g._fullLayout.xaxis.range,y:g._fullLayout.yaxis.range})"
        )
        import json

        view = json.loads(view)
        self.assertEqual(view["x"], [20, 60])
        self.assertEqual(view["y"], [30, 70])
        self.assertEqual(self.events, [])  # programmatic relayout is flagged and never echoed

    def _page_state(self):
        import json

        return json.loads(
            self._js(
                "var g=document.getElementById('heatmapDiv');"
                "JSON.stringify({zmin:g._fullData[0].zmin,zmax:g._fullData[0].zmax,"
                "x:g._fullLayout.xaxis.range,y:g._fullLayout.yaxis.range})"
            )
        )

    def test_complete_workflow_zoom_reset_and_time_step_through_the_real_page(self):
        controller = self.panel.controller
        controls = self.panel.controls_widget
        self.assertTrue(self._reload(lambda: controls.auto_scale_check.setChecked(True)))  # full render
        full_stats = controller._last_grids[3]
        full = self._page_state()
        self.assertAlmostEqual(full["zmin"], full_stats["min"], places=6)

        # 1. user zooms: Plotly event -> debounce -> bridge -> controller -> in-place restyle
        x_axis, y_axis = _axes(controller)
        zx = (float(x_axis[10]), float(x_axis[60]))
        zy = (float(y_axis[100]), float(y_axis[150]))
        self._js(
            "Plotly.relayout(document.getElementById('heatmapDiv'),"
            f"{{'xaxis.range[0]':{zx[0]},'xaxis.range[1]':{zx[1]},'yaxis.range[0]':{zy[0]},'yaxis.range[1]':{zy[1]}}});1"
        )
        self.assertTrue(_wait_for(lambda: controller._zoom_window is not None, 5000))
        self._settle(400)
        expected = vr.padded_range(*vr.visible_min_max(x_axis, y_axis, controller._last_display_grids[2],
                                                       controller._zoom_window))
        zoomed = self._page_state()
        self.assertAlmostEqual(zoomed["zmin"], expected[0], places=9)  # colours follow the visible region
        self.assertAlmostEqual(zoomed["zmax"], expected[1], places=9)
        self.assertAlmostEqual(controls.range_min_spin.value(), expected[0], places=5)
        self.assertEqual([round(v, 3) for v in zoomed["x"]], [round(v, 3) for v in zx])  # view untouched
        self.assertNotEqual((zoomed["zmin"], zoomed["zmax"]), (full["zmin"], full["zmax"]))

        # 2. time step changes: zoom kept, range recomputed from the NEW step's visible region
        saved_window = controller._zoom_window
        self.assertTrue(self._reload(lambda: controls.file_combo.setCurrentIndex(1)))
        self._settle(900)
        step2 = self._page_state()
        new_x, new_y = _axes(controller)
        expected2 = vr.padded_range(*vr.visible_min_max(new_x, new_y, controller._last_display_grids[2], saved_window))
        self.assertEqual(controller._zoom_window, saved_window)
        self.assertEqual([round(v, 3) for v in step2["x"]], [round(v, 3) for v in zx])
        self.assertAlmostEqual(step2["zmin"], expected2[0], places=9)
        self.assertAlmostEqual(step2["zmax"], expected2[1], places=9)

        # 3. reset zoom (modebar button): the full-domain range of the current step comes back
        self._js("document.querySelector('.modebar-btn[data-attr=\"zoom\"][data-val=\"reset\"]').click();1")
        self.assertTrue(_wait_for(lambda: controller._zoom_window is None, 5000))
        self._settle(400)
        step2_stats = controller._last_grids[3]
        reset = self._page_state()
        self.assertAlmostEqual(reset["zmin"], step2_stats["min"], places=9)
        self.assertAlmostEqual(reset["zmax"], step2_stats["max"], places=9)


if __name__ == "__main__":
    unittest.main()
