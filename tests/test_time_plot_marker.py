import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from viewer.time_plot_canvas import TimePlotCanvas

_SERIES = [{"label": "P1", "steps": [0.0, 10.0, 20.0], "values": [1.0, 2.0, 3.0]}]


class TimePlotCurrentStepMarkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_current_step_adds_dashed_vline(self):
        figure = TimePlotCanvas()._build_time_plot_figure(_SERIES, y_label="v", current_step=10.0)

        self.assertEqual(len(figure.layout.shapes), 1)
        shape = figure.layout.shapes[0]
        self.assertEqual(shape.x0, 10.0)
        self.assertEqual(shape.line.dash, "dash")

    def test_no_marker_without_current_step(self):
        figure = TimePlotCanvas()._build_time_plot_figure(_SERIES, y_label="v")

        self.assertEqual(len(figure.layout.shapes), 0)

    def test_no_marker_when_no_finite_data(self):
        empty = [{"label": "P1", "steps": [0.0], "values": [float("nan")]}]
        figure = TimePlotCanvas()._build_time_plot_figure(empty, y_label="v", current_step=0.0)

        self.assertEqual(len(figure.layout.shapes), 0)


if __name__ == "__main__":
    unittest.main()
