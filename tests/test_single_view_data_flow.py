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
from viewer.time_plot_canvas import TimePlotCanvas


class SingleViewDataFlowTests(unittest.TestCase):
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
