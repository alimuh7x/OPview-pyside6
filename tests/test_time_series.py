import tempfile
import unittest
from pathlib import Path

from utils.time_series import collect_same_series_files


class TimeSeriesTests(unittest.TestCase):
    def test_collect_same_series_files_can_skip_missing_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            current = root / "PhaseField_00000000.vts"
            existing = root / "PhaseField_00000001.vts"
            missing = root / "PhaseField_00000002.vts"
            current.touch()
            existing.touch()

            series = collect_same_series_files(
                str(current),
                [str(current), str(existing), str(missing)],
                existing_only=True,
            )

        self.assertEqual([item.path for item in series], [str(current), str(existing)])
