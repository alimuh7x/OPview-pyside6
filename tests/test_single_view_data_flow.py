import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from config.tabs import TAB_CONFIGS
from config.dataset_registry import DatasetRegistry
from utils.project_scanner import scan_project_folders
from utils.vtk_utils import get_reader


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


if __name__ == "__main__":
    unittest.main()
