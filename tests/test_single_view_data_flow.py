import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from config.tabs import TAB_CONFIGS
from config.dataset_registry import DatasetRegistry
import utils.dataset_detector as dataset_detector
from utils.time_series import collect_same_series_files
from utils.project_scanner import scan_project_folders
from utils.vtk_utils import get_reader
from viewer.heatmap_canvas import HeatmapCanvas
from viewer.heatmap_controller import HeatmapController
from viewer.heatmap_orientation import Heatmap2DOrientation
from viewer.time_plot_canvas import TimePlotCanvas


class SingleViewDataFlowTests(unittest.TestCase):
    def test_heatmap_hover_formats_tiny_values_scientifically(self):
        canvas = HeatmapCanvas.__new__(HeatmapCanvas)

        hover_text = canvas._build_hover_text(1.0, 2.0, 1e-7)

        self.assertIn("value=1.00e-07", hover_text)
        self.assertNotIn("value=0.0000", hover_text)

    def test_scan_project_folders_finds_project1(self):
        projects = scan_project_folders(Path.cwd(), quick_scan=True)

        self.assertIn("Project1", projects)
        self.assertIn("Project1/VTK", projects)
        self.assertTrue(projects["Project1"]["has_vtk"])

    def test_dataset_registry_detects_vtk_datasets(self):
        registry = DatasetRegistry(Path("Project1/VTK"), TAB_CONFIGS)

        registry.detect(verbose=False)
        detected_ids = {dataset.dataset_id for dataset in registry.all_datasets}

        self.assertIn("mechanics-elastic", detected_ids)
        self.assertIn("plasticity-crss", detected_ids)

    def test_dataset_registry_limits_eager_file_lists_for_large_vtk_folders(self):
        with tempfile.TemporaryDirectory() as tmp:
            vtk_dir = Path(tmp) / "VTK"
            vtk_dir.mkdir()
            for index in range(750):
                (vtk_dir / f"PhaseField_{index:08d}.vts").touch()

            registry = DatasetRegistry(vtk_dir, TAB_CONFIGS)
            registry.detect(verbose=False)
            phase = next(dataset for dataset in registry.all_datasets if dataset.dataset_id == "phase-field-phase")

        self.assertEqual(phase.matched_count, 750)
        self.assertLess(len(phase.matched_files), phase.matched_count)
        self.assertGreater(len(phase.matched_files), 0)

    def test_dataset_registry_limits_unconfigured_files_per_detected_series(self):
        original_limit = dataset_detector._MAX_EAGER_FILES_PER_DATASET
        dataset_detector._MAX_EAGER_FILES_PER_DATASET = 2
        try:
            with tempfile.TemporaryDirectory() as tmp:
                vtk_dir = Path(tmp) / "VTK"
                vtk_dir.mkdir()
                for prefix in ["Alpha", "Beta", "Gamma"]:
                    for index in range(4):
                        (vtk_dir / f"{prefix}_{index:08d}.vts").touch()

                registry = DatasetRegistry(vtk_dir, TAB_CONFIGS)
                registry.detect(verbose=False)
                auto_datasets = {
                    dataset.label: dataset
                    for dataset in registry.all_datasets
                    if dataset.module_id == "unconfigured"
                }
        finally:
            dataset_detector._MAX_EAGER_FILES_PER_DATASET = original_limit

        self.assertEqual(set(auto_datasets), {"Alpha", "Beta", "Gamma"})
        for dataset in auto_datasets.values():
            self.assertEqual(dataset.matched_count, 4)
            self.assertEqual(len(dataset.matched_files), 2)
            self.assertTrue(dataset.files_limited)

    def test_vtk_reader_extracts_interpolated_slice(self):
        sample_file = Path("Project1/VTK/ElasticStrains_00000000.vts").resolve()
        reader = get_reader(str(sample_file))

        x_grid, y_grid, z_grid, stats = reader.get_interpolated_slice(
            axis="z",
            index=0,
            scalar_name="ElasticStrains",
            component=0,
            resolution=40,
        )

        self.assertEqual(x_grid.shape, (40, 40))
        self.assertEqual(y_grid.shape, (40, 40))
        self.assertEqual(z_grid.shape, (40, 40))
        self.assertLessEqual(stats["min"], stats["max"])

    def test_collect_same_series_files_filters_and_sorts_timesteps(self):
        root = Path("Project1/VTK").resolve()
        current = str(root / "PhaseField_00001000.vts")
        files = [
            str(root / "Stresses_00000000.vts"),
            str(root / "PhaseField_00005000.vts"),
            str(root / "PhaseField_00000000.vts"),
            str(root / "Composition_00000000.vts"),
            str(root / "PhaseField_00001000.vts"),
        ]

        series = collect_same_series_files(current, files)

        self.assertEqual([item.step for item in series], [0, 1000, 5000])
        self.assertTrue(all(Path(item.path).name.startswith("PhaseField_") for item in series))

    def test_vtk_reader_samples_nearest_point_value(self):
        sample_file = Path("Project1/VTK/ElasticStrains_00000000.vts").resolve()
        reader = get_reader(str(sample_file))
        x_grid, y_grid, z_grid, _ = reader.get_interpolated_slice(
            axis="z",
            index=0,
            scalar_name="ElasticStrains",
            component=0,
            resolution=None,
        )

        x_value = float(x_grid[0, 0])
        y_value = float(y_grid[0, 0])
        expected = float(z_grid[0, 0])

        sampled = reader.sample_point_value(
            axis="z",
            index=0,
            scalar_name="ElasticStrains",
            component=0,
            x_value=x_value,
            y_value=y_value,
        )

        self.assertAlmostEqual(sampled, expected, places=8)

    def test_vtk_reader_calculates_gradient_magnitude_from_slice_grid(self):
        sample_file = Path("Project1/VTK/ElasticStrains_00000000.vts").resolve()
        reader = get_reader(str(sample_file))
        x_grid, y_grid, z_grid, _ = reader.get_interpolated_slice(
            axis="z",
            index=0,
            scalar_name="ElasticStrains",
            component=0,
            resolution=40,
        )

        grad_grid, grad_stats = reader.gradient_magnitude_from_grid(x_grid, y_grid, z_grid)

        self.assertEqual(grad_grid.shape, z_grid.shape)
        self.assertTrue((grad_grid >= 0).all())
        self.assertLessEqual(grad_stats["min"], grad_stats["max"])
        self.assertGreater(float(grad_grid.max()), 0.0)

    def test_vtk_reader_extracts_projected_vector_slice(self):
        import numpy as np
        import pyvista as pv

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "vectors.vti"
            mesh = pv.ImageData(dimensions=(3, 3, 1), spacing=(1.0, 1.0, 1.0))
            vectors = np.tile(np.array([[3.0, 4.0, 12.0]]), (mesh.n_points, 1))
            mesh.point_data["Velocity"] = vectors
            mesh.point_data["StressTensor"] = np.ones((mesh.n_points, 6))
            mesh.save(path)

            reader = get_reader(str(path))
            x_grid, y_grid, u_grid, v_grid, magnitude_grid, stats = reader.get_vector_overlay_grid(
                axis="z",
                index=0,
                vector_name="Velocity",
                resolution=5,
            )
            _, _, u_grid_cached, _, _, _ = reader.get_vector_overlay_grid(
                axis="z",
                index=0,
                vector_name="Velocity",
                resolution=5,
            )

        self.assertIn("Velocity", reader.vector_fields)
        self.assertNotIn("StressTensor", reader.vector_fields)
        self.assertEqual(x_grid.shape, (5, 5))
        self.assertEqual(y_grid.shape, (5, 5))
        self.assertIs(u_grid_cached, u_grid)
        self.assertTrue(np.allclose(u_grid[np.isfinite(u_grid)], 3.0))
        self.assertTrue(np.allclose(v_grid[np.isfinite(v_grid)], 4.0))
        self.assertTrue(np.allclose(magnitude_grid[np.isfinite(magnitude_grid)], 13.0))
        self.assertEqual(stats["min"], 13.0)
        self.assertEqual(stats["max"], 13.0)

    def test_heatmap_canvas_builds_magnitude_scaled_vector_arrow_traces(self):
        import numpy as np

        overlay = {
            "x": np.array([[0.0, 1.0]]),
            "y": np.array([[0.0, 0.0]]),
            "u": np.array([[10.0, 0.0]]),
            "v": np.array([[0.0, 20.0]]),
            "magnitude": np.array([[10.0, 20.0]]),
            "label": "Velocity",
        }

        traces = HeatmapCanvas._build_vector_arrow_traces(overlay, arrow_length=0.25, color_bins=2)

        self.assertEqual(len(traces), 4)
        shaft_x_values = []
        shaft_y_values = []
        for trace in traces:
            if trace.name != "Velocity arrows":
                continue
            shaft_x_values.extend([value for value in trace.x if value is not None])
            shaft_y_values.extend([value for value in trace.y if value is not None])
        self.assertIn(0.125, shaft_x_values)
        self.assertIn(1.0, shaft_x_values)
        self.assertIn(0.375, shaft_y_values)
        head_traces = [trace for trace in traces if trace.name == "Velocity arrow heads"]
        self.assertEqual(len(head_traces), 2)

    def test_heatmap_canvas_scales_arrow_length_slightly_by_magnitude(self):
        import numpy as np

        overlay = {
            "x": np.array([[0.0, 1.0]]),
            "y": np.array([[0.0, 0.0]]),
            "u": np.array([[1.0, 1.0]]),
            "v": np.array([[0.0, 0.0]]),
            "magnitude": np.array([[10.0, 20.0]]),
            "label": "Velocity",
        }

        traces = HeatmapCanvas._build_vector_arrow_traces(overlay, arrow_length=1.0, color_bins=1)
        shaft_trace = next(trace for trace in traces if trace.name == "Velocity arrows")
        shaft_x_values = [round(float(value), 3) for value in shaft_trace.x if value is not None]

        self.assertIn(0.50, shaft_x_values)
        self.assertIn(2.50, shaft_x_values)

    def test_heatmap_controller_skips_vector_overlay_when_toggle_is_off(self):
        class ToggleOff:
            def isChecked(self):
                return False

        class ReaderThatShouldNotBeAsked:
            @property
            def vector_fields(self):
                raise AssertionError("vector fields should not be read when toggle is off")

        controller = HeatmapController.__new__(HeatmapController)
        controller.reader = ReaderThatShouldNotBeAsked()
        controller.vector_overlay_check = ToggleOff()
        controller.state = type("State", (), {"scalar_key": "Velocity", "axis": "z", "slice_index": 0})()
        controller._get_scalar_def = lambda _key: {"array": "Velocity", "label": "Velocity"}

        overlay = controller._build_vector_overlay(Heatmap2DOrientation())

        self.assertIsNone(overlay)

    def test_heatmap_controller_uses_low_resolution_vector_grid(self):
        import numpy as np

        class ToggleOn:
            def isChecked(self):
                return True

        class Controls:
            def current_plot_type(self):
                return "heatmap"

        class Reader:
            def __init__(self):
                self.requested_resolution = None

            @property
            def vector_fields(self):
                return ["Velocity"]

            def get_vector_overlay_grid(self, *, axis, index, vector_name, resolution):
                self.requested_resolution = resolution
                grid = np.ones((resolution, resolution), dtype=float)
                return grid, grid, grid, grid, grid, {"min": 1.0, "max": 1.0, "mean": 1.0, "std": 0.0}

        reader = Reader()
        controller = HeatmapController.__new__(HeatmapController)
        controller.reader = reader
        controller.controls_widget = Controls()
        controller.vector_overlay_check = ToggleOn()
        controller.state = type("State", (), {"scalar_key": "Velocity", "axis": "z", "slice_index": 0})()
        controller._get_scalar_def = lambda _key: {"array": "Velocity", "label": "Velocity"}

        overlay = controller._build_vector_overlay(Heatmap2DOrientation())

        self.assertIsNotNone(overlay)
        self.assertEqual(reader.requested_resolution, 21)
        self.assertLessEqual(max(overlay["u"].shape), 21)

    def test_heatmap_controller_rotates_vector_directions_with_display_coordinates(self):
        import numpy as np

        controller = HeatmapController.__new__(HeatmapController)
        overlay = {
            "x": np.array([[0.0, 1.0], [0.0, 1.0]]),
            "y": np.array([[0.0, 0.0], [1.0, 1.0]]),
            "u": np.ones((2, 2)),
            "v": np.zeros((2, 2)),
            "magnitude": np.ones((2, 2)),
        }

        oriented = controller._orient_vector_overlay(overlay, Heatmap2DOrientation(90))

        self.assertTrue(np.allclose(oriented["u"], 0.0))
        self.assertTrue(np.allclose(oriented["v"], 1.0))

    def test_heatmap_controller_rotates_vector_basis_for_quarter_turns(self):
        import numpy as np

        controller = HeatmapController.__new__(HeatmapController)
        base_overlay = {
            "x": np.array([[0.0, 1.0], [0.0, 1.0]]),
            "y": np.array([[0.0, 0.0], [1.0, 1.0]]),
            "magnitude": np.ones((2, 2)),
        }
        x_vector = {**base_overlay, "u": np.ones((2, 2)), "v": np.zeros((2, 2))}
        y_vector = {**base_overlay, "u": np.zeros((2, 2)), "v": np.ones((2, 2))}

        rotated_90_x = controller._orient_vector_overlay(x_vector, Heatmap2DOrientation(90))
        rotated_90_y = controller._orient_vector_overlay(y_vector, Heatmap2DOrientation(90))
        rotated_270_x = controller._orient_vector_overlay(x_vector, Heatmap2DOrientation(270))
        rotated_270_y = controller._orient_vector_overlay(y_vector, Heatmap2DOrientation(270))

        self.assertTrue(np.allclose(rotated_90_x["u"], 0.0))
        self.assertTrue(np.allclose(rotated_90_x["v"], 1.0))
        self.assertTrue(np.allclose(rotated_90_y["u"], -1.0))
        self.assertTrue(np.allclose(rotated_90_y["v"], 0.0))
        self.assertTrue(np.allclose(rotated_270_x["u"], 0.0))
        self.assertTrue(np.allclose(rotated_270_x["v"], -1.0))
        self.assertTrue(np.allclose(rotated_270_y["u"], 1.0))
        self.assertTrue(np.allclose(rotated_270_y["v"], 0.0))

    def test_heatmap_controller_places_rotated_vectors_on_display_grid(self):
        import numpy as np

        controller = HeatmapController.__new__(HeatmapController)
        overlay = {
            "x": np.array([[0.0, 1.0], [0.0, 1.0]]),
            "y": np.array([[0.0, 0.0], [1.0, 1.0]]),
            "u": np.ones((2, 2)),
            "v": np.zeros((2, 2)),
            "magnitude": np.array([[1.0, 2.0], [3.0, 4.0]]),
        }

        oriented = controller._orient_vector_overlay(overlay, Heatmap2DOrientation(90))

        self.assertTrue(np.allclose(oriented["x"], [[0.0, 1.0], [0.0, 1.0]]))
        self.assertTrue(np.allclose(oriented["y"], [[0.0, 0.0], [1.0, 1.0]]))

    def test_heatmap_canvas_draws_vector_arrow_heads_as_lines(self):
        import numpy as np

        overlay = {
            "x": np.array([[0.0]]),
            "y": np.array([[0.0]]),
            "u": np.array([[1.0]]),
            "v": np.array([[0.0]]),
            "magnitude": np.array([[1.0]]),
            "label": "Velocity",
        }

        traces = HeatmapCanvas._build_vector_arrow_traces(overlay, arrow_length=0.25, color_bins=1)

        self.assertTrue(all(trace.mode == "lines" for trace in traces))
        self.assertGreaterEqual(len([value for value in traces[-1].x if value is None]), 1)
        self.assertIn(0.165, [round(float(value), 3) for value in traces[-1].x if value is not None])
        self.assertIn(0.05, [round(abs(float(value)), 3) for value in traces[-1].y if value is not None])

    def test_time_plot_canvas_builds_multiple_point_series(self):
        QApplication.instance() or QApplication([])
        canvas = TimePlotCanvas()
        figure = canvas._build_time_plot_figure(
            [
                {"label": "P1", "steps": [0, 1], "values": [1.0, 2.0]},
                {"label": "P2", "steps": [0, 1], "values": [3.0, 4.0]},
            ],
            y_label="Value",
        )

        self.assertEqual(len(figure.data), 2)
        self.assertEqual(figure.data[0].name, "P1")
        self.assertEqual(figure.data[1].name, "P2")


if __name__ == "__main__":
    unittest.main()
