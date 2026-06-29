import tempfile
import unittest
from pathlib import Path

from app.startup_args import parse_args
from utils.project_scanner import scan_project_folders


class ProjectPathStartupTests(unittest.TestCase):
    def test_parse_args_accepts_optional_project_path(self):
        args = parse_args(["/tmp/openphase-projects"])

        self.assertEqual(args.project_path, Path("/tmp/openphase-projects"))

    def test_parse_args_allows_no_project_path(self):
        args = parse_args([])

        self.assertIsNone(args.project_path)

    def test_scan_project_folders_accepts_project_folder_itself(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "DemoProject"
            vtk = project / "VTK"
            vtk.mkdir(parents=True)

            projects = scan_project_folders(project, quick_scan=True)

        self.assertIn("DemoProject", projects)
        self.assertIn("DemoProject/VTK", projects)
        self.assertEqual(projects["DemoProject"]["vtk_path"], vtk)


if __name__ == "__main__":
    unittest.main()
