import unittest
from pathlib import Path

import matplotlib
import numpy as np
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from config.tabs import TAB_CONFIGS
from viewer.heatmap_canvas import HeatmapCanvas
from viewer.panel_widget import PanelWidget
from viewer.phase_overlay_button import PhaseOverlayButton


class PhaseOverlayButtonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_nothing_ticked_by_default(self):
        button = PhaseOverlayButton()
        button.set_phases([("p0", "Austenite"), ("p1", "Ferrite")])

        self.assertEqual(button.checked_keys(), [])
        self.assertEqual(button.phase_keys(), ["p0", "p1"])

    def test_selection_survives_rebuild_for_existing_phases_only(self):
        button = PhaseOverlayButton()
        button.set_phases([("p0", "A"), ("p1", "B")])
        button.set_phase_checked("p1", True)

        button.set_phases([("p1", "B"), ("p2", "C")])

        self.assertEqual(button.checked_keys(), ["p1"])

    def test_toggle_emits_selection_changed(self):
        button = PhaseOverlayButton()
        button.set_phases([("p0", "A")])
        hits = []
        button.selection_changed.connect(lambda: hits.append(1))

        button.set_phase_checked("p0", True)

        self.assertEqual(len(hits), 1)


class OverlayMenuBehaviourTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_menu_stays_open_when_an_entry_is_ticked(self):
        button = PhaseOverlayButton()
        button.set_phases([("p0", "A"), ("p1", "B")])
        button.show()
        button.showPopup()
        self.app.processEvents()
        view = button.view()
        rect = view.visualRect(button.model().index(2, 0))  # row 0 hidden caption, 1 Interfaces, 2 = p0

        QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=rect.center())
        self.app.processEvents()

        self.assertEqual(button.checked_keys(), ["p0"])
        self.assertTrue(view.isVisible())
        button.hidePopup()

    def test_popup_is_wide_enough_for_long_phase_names(self):
        button = PhaseOverlayButton()
        button.set_phases([("p0", "Austenite (face-centred cubic matrix)")])

        self.assertGreaterEqual(button.view().minimumWidth(), 260)

    def test_interfaces_entry_is_in_the_same_menu_and_counts(self):
        button = PhaseOverlayButton()
        button.set_phases([("p0", "A")])
        seen = []
        button.interfaces_toggled.connect(seen.append)

        button.set_interfaces_checked(True)

        self.assertEqual(seen, [True])
        self.assertEqual(button.currentText(), "Overlays (1)")


class OverlayRowControlsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _open(self, button):
        button.show()
        button.showPopup()
        self.app.processEvents()
        return button.view()

    def _click_slot(self, view, row, slot_from_right):
        rect = view.visualRect(view.model().index(row, 0))
        x = rect.right() - slot_from_right * 26 + 13
        QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(x, rect.center().y()))
        self.app.processEvents()

    def _click_slot_minus(self, view, row):
        rect = view.visualRect(view.model().index(row, 0))
        x = rect.right() - 26 - 36 - 26 + 13
        QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(x, rect.center().y()))
        self.app.processEvents()

    def test_interface_row_plus_minus_change_width_and_keep_popup_open(self):
        button = PhaseOverlayButton()
        button.set_phases([("p0", "A")])
        seen = []
        button.interface_width_changed.connect(seen.append)
        view = self._open(button)

        self._click_slot(view, 1, 1)  # plus
        self._click_slot(view, 1, 1)
        self._click_slot_minus(view, 1)

        self.assertEqual(button.interface_width(), 1)
        self.assertEqual(seen, [1, 2, 1])
        self.assertFalse(button.interfaces_checked())  # stepper clicks do not tick the row
        self.assertTrue(view.isVisible())
        button.hidePopup()

    def test_interface_width_defaults_to_zero(self):
        self.assertEqual(PhaseOverlayButton().interface_width(), 0)

    def test_phase_row_pencil_requests_rename_without_ticking(self):
        button = PhaseOverlayButton()
        button.set_phases([("p0", "Austenite")])
        seen = []
        button.rename_requested.connect(lambda key, label: seen.append((key, label)))
        view = self._open(button)

        self._click_slot(view, 2, 1)

        self.assertEqual(seen, [("p0", "Austenite")])
        self.assertEqual(button.checked_keys(), [])

    def test_clicking_the_row_text_still_ticks(self):
        button = PhaseOverlayButton()
        button.set_phases([("p0", "A")])
        view = self._open(button)
        rect = view.visualRect(view.model().index(2, 0))

        QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(rect.left() + 20, rect.center().y()))

        self.assertEqual(button.checked_keys(), ["p0"])
        button.hidePopup()


class InterfaceNarrowingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _band(self, size=40, half=6):
        z = np.zeros((size, size))
        z[:, size // 2 - half: size // 2 + half] = 2.0  # a vertical interface band
        return z

    @staticmethod
    def _band_width(field, row=20):
        """Sub-cell band width along a row: distance between the two 1.5 crossings."""
        values = field[row]
        crossings = []
        for idx in range(1, len(values)):
            lo, hi = values[idx - 1], values[idx]
            if (lo - 1.5) * (hi - 1.5) < 0:
                crossings.append(idx - 1 + (1.5 - lo) / (hi - lo))
        return crossings[-1] - crossings[0] if len(crossings) >= 2 else 0.0

    def test_each_negative_step_narrows_the_band_by_a_visible_amount(self):
        from viewer.heatmap_controller import narrowed_interface_field

        z = self._band()
        widths = [self._band_width(narrowed_interface_field(z, steps)) for steps in (0, 1, 2, 3, 5)]

        self.assertEqual(widths, sorted(widths, reverse=True))
        self.assertAlmostEqual(widths[0] - widths[1], 2 * 0.35, delta=0.2)  # both edges move in
        self.assertGreater(widths[0] - widths[4], 3.0)

    def test_zero_steps_keep_the_original_band_width(self):
        from viewer.heatmap_controller import narrowed_interface_field

        z = self._band()  # 12 cells wide

        self.assertAlmostEqual(self._band_width(narrowed_interface_field(z, 0)), 12.0, delta=1.0)

    def test_narrowed_edge_is_smooth_not_a_pixel_staircase(self):
        from viewer.heatmap_controller import narrowed_interface_field

        # Diagonal band: a raw-mask distance transform would zig-zag along it.
        size = 60
        yy, xx = np.mgrid[0:size, 0:size]
        z = np.where(np.abs(xx - yy) <= 5, 2.0, 0.0)
        field = narrowed_interface_field(z, 1)
        # Edge position per row = where the field crosses 1.5 (sub-cell, by interpolation).
        edge = []
        for row in range(10, 50):
            values = field[row]
            idx = np.argmax(values >= 1.5)
            lo, hi = values[idx - 1], values[idx]
            edge.append(idx - 1 + (1.5 - lo) / (hi - lo))
        steps = np.diff(edge)

        self.assertLess(float(np.std(steps)), 0.15)  # near-constant slope = straight, smooth edge

    def test_outside_the_band_stays_empty(self):
        from viewer.heatmap_controller import narrowed_interface_field

        z = self._band()

        self.assertTrue(np.all(narrowed_interface_field(z, 4)[:, :5] < 1.5))

    def test_dropdown_width_goes_negative_and_clamps(self):
        button = PhaseOverlayButton()
        button.set_interface_width(-4)
        self.assertEqual(button.interface_width(), -4)
        button.set_interface_width(-99)
        self.assertEqual(button.interface_width(), -10)

    def test_minus_click_from_zero_narrows(self):
        button = PhaseOverlayButton()
        button.set_phases([("p0", "A")])
        button.show()
        button.showPopup()
        self.app.processEvents()
        view = button.view()
        rect = view.visualRect(view.model().index(1, 0))
        minus_x = rect.right() - 26 - 36 - 26 + 13  # plus slot, value slot, minus slot
        QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(minus_x, rect.center().y()))
        self.app.processEvents()

        self.assertEqual(button.interface_width(), -1)
        button.hidePopup()


class OverlayLegendOnImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _figure(self, overlays):
        canvas = HeatmapCanvas()
        canvas._last_extent = (0.0, 3.0, 0.0, 3.0)
        grid = np.linspace(0.0, 1.0, 16).reshape(4, 4)
        x, y = np.meshgrid(np.arange(4.0), np.arange(4.0))
        return canvas._build_figure(
            x_grid=x, y_grid=y, z_grid=grid, cmap=matplotlib.colormaps["viridis"], vmin=0.0, vmax=1.0,
            line_overlay=None, overlay_grid=None, phase_fraction_overlays=overlays,
        ), x, y, grid

    def test_legend_swatches_are_real_coloured_squares_stacked_above_the_image(self):
        x = np.array([[0.0, 1.0], [0.0, 1.0]])
        y = np.array([[0.0, 0.0], [1.0, 1.0]])
        z = np.array([[0.0, 0.7], [0.8, 0.0]])
        layers = [
            {"label": name, "x": x, "y": y, "z": z, "range": (0.5, float("inf")), "color": c, "on_top": True}
            for name, c in (("Austenite", "#5f7f4f"), ("Ferrite", "#8a5a83"))
        ]

        figure, *_ = self._figure(layers)

        squares = [sh for sh in figure.layout.shapes if sh.type == "rect"]
        self.assertEqual([sh.fillcolor for sh in squares], ["#5f7f4f", "#8a5a83"])
        for sh in squares:
            self.assertGreater(sh.y0, 1.0)  # above the plot area, not over the data
            self.assertGreater(sh.x1 - sh.x0, 0)
            self.assertLessEqual(sh.x1, 1.0)
        self.assertGreater(squares[0].y0, squares[1].y0)  # first entry on top
        labels = [a for a in figure.layout.annotations if a.text in ("Austenite", "Ferrite")]
        self.assertEqual(len(labels), 2)
        for label, square in zip(labels, squares):
            self.assertGreaterEqual(label.x, square.x1)  # text to the right of its swatch
            self.assertAlmostEqual(label.y, (square.y0 + square.y1) / 2)
        self.assertFalse(figure.layout.showlegend)

    def test_many_phases_grow_the_top_margin_instead_of_covering_the_image(self):
        x = np.array([[0.0, 1.0], [0.0, 1.0]])
        z = np.array([[0.0, 0.7], [0.8, 0.0]])
        layers = [
            {"label": f"P{i}", "x": x, "y": x.T, "z": z, "range": (0.5, float("inf")), "color": "#5f7f4f", "on_top": True}
            for i in range(6)
        ]

        figure, *_ = self._figure(layers)

        self.assertGreater(figure.layout.margin.t, 60)

    def test_no_legend_without_overlays(self):
        figure, *_ = self._figure([])

        self.assertEqual(len(figure.layout.shapes), 0)
        self.assertEqual(figure.layout.margin.t, 60)

    def test_png_export_adds_a_legend_band_above_the_image(self):
        canvas = HeatmapCanvas()
        rows, cols = 40, 60
        x, y = np.meshgrid(np.arange(cols, dtype=float), np.arange(rows, dtype=float))
        z = np.random.default_rng(0).random((rows, cols))
        base = {
            "x_grid": x, "y_grid": y, "z_grid": z, "cmap": matplotlib.colormaps["viridis"],
            "vmin": 0.0, "vmax": 1.0, "colorbar_label": "v", "plot_type": "heatmap",
            "line_overlay": None, "overlay_grid": None, "time_plot_points": [],
        }
        layer = {"label": "Austenite", "x": x, "y": y, "z": z, "range": (0.5, float("inf")),
                 "color": "#5f7f4f", "on_top": True}
        import tempfile
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            plain, with_legend = f"{tmp}/a.png", f"{tmp}/b.png"
            self.assertTrue(canvas.save_high_resolution_png(plain, payload=dict(base), dpi=100))
            self.assertTrue(canvas.save_high_resolution_png(
                with_legend, payload={**base, "phase_fraction_overlays": [layer]}, dpi=100))
            height_plain = Image.open(plain).height
            height_legend = Image.open(with_legend).height

        self.assertGreater(height_legend, height_plain)  # band added; data not covered

    def test_phase_colors_avoid_every_colorbar_palette_color(self):
        from config.constants import PALETTES
        from viewer.heatmap_controller import _PHASE_FRACTION_COLORS

        def rgb(hex_color):
            h = hex_color.lstrip("#")
            return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=float)

        palette_colors = {c for colors in PALETTES.values() for c in colors}
        for phase in _PHASE_FRACTION_COLORS:
            nearest = min(np.linalg.norm(rgb(phase) - rgb(c)) for c in palette_colors)
            self.assertGreater(nearest, 50, f"{phase} is too close to a colorbar colour")


class CompositionPhaseListTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_phases_are_offered_over_a_non_phase_dataset(self):
        composition = {
            "label": "Composition",
            "scalars": [{"label": "w(FE)", "array": "WeightFractionsTotal_FE"}],
        }
        panel = PanelWidget(dataset_info={
            "id": "composition",
            "label": "Composition",
            "files": [str(Path("Project1/VTK/Composition_00000000.vts").resolve())],
            "dataset_config": composition,
            "tab_id": "single_view",
        })

        self.assertTrue(panel.phase_overlay_button.phase_keys())


class PhaseOverlayRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_on_top_layer_keeps_base_field_and_is_fully_opaque(self):
        canvas = HeatmapCanvas()
        canvas._last_extent = (0.0, 3.0, 0.0, 3.0)
        grid = np.linspace(0.0, 1.0, 16).reshape(4, 4)
        x, y = np.meshgrid(np.arange(4.0), np.arange(4.0))
        layer = {
            "label": "Phase", "x": x, "y": y, "z": grid,
            "range": (0.5, float("inf")), "color": "#d62728",
            "on_top": True,
        }

        figure = canvas._build_figure(
            x_grid=x, y_grid=y, z_grid=grid, cmap=matplotlib.colormaps["viridis"], vmin=0.0, vmax=1.0,
            line_overlay=None, overlay_grid=None, phase_fraction_overlays=[layer],
        )

        self.assertEqual(len(figure.data), 2)
        self.assertIsNone(figure.data[0].name)
        self.assertEqual(figure.data[1].name, "Phase")
        self.assertAlmostEqual(figure.data[1].opacity, 1.0)
        self.assertFalse(figure.data[1].showlegend)
        shown = np.asarray(figure.data[1].z, dtype=float)
        self.assertTrue(np.all(shown[~np.isnan(shown)] >= 0.5))

    def test_single_view_overlay_draws_ticked_phase_over_non_phase_field(self):
        panel = PanelWidget(dataset_info={
            "id": "phase",
            "label": "PhaseField",
            "files": [str(Path("Project1/VTK/PhaseField_00000000.vts").resolve())],
            "dataset_config": TAB_CONFIGS[0]["datasets"][0],
            "tab_id": "single_view",
        })
        button = panel.phase_overlay_button
        captured = {}
        original = panel.heatmap_canvas._build_figure

        def spy(**kwargs):
            captured["figure"] = original(**kwargs)
            return captured["figure"]

        panel.heatmap_canvas._build_figure = spy
        self.assertEqual(button.checked_keys(), [])

        button.set_phase_checked(button.phase_keys()[0], True)

        self.assertEqual(len(captured["figure"].data), 2)
        button.set_interfaces_checked(True)
        self.assertTrue(panel.controller.interfaces_check.isChecked())
        self.assertFalse(panel.controller.state.scalar_key in button.phase_keys())


if __name__ == "__main__":
    unittest.main()
