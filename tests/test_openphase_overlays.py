"""Overlay source discovery must also support OpenPhase output files."""

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pyvista as pv

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from viewer.animation_player import _FrameFetcher
from viewer.heatmap_controller import HeatmapController
from multi_view.multi_view_panel import MultiViewPanel
from multi_property.multi_property_panel import MultiPropertyPanel


class OpenPhaseOverlaySourceTests(unittest.TestCase):
    def resolve_sources(self, source):
        controller = HeatmapController.__new__(HeatmapController)
        return (
            controller._phase_overlay_file(str(source)),
            _FrameFetcher._phase_overlay_file(str(source)),
            MultiViewPanel._phase_overlay_file(str(source)),
            MultiPropertyPanel._phase_overlay_file(str(source)),
        )

    def test_openphase_is_used_for_active_and_other_datasets(self):
        with tempfile.TemporaryDirectory() as tmp:
            phase = Path(tmp) / "OpenPhase_00005000.vts"
            phase.touch()
            for source in (phase, Path(tmp) / "Stresses_00005000.vts"):
                with self.subTest(source=source.name):
                    self.assertEqual(self.resolve_sources(source), (phase,) * 4)

    def test_existing_phase_sources_keep_priority(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "OpenPhase_00005000.vts"
            source.touch()
            for prefix in ("PhaseFieldDistorted", "PhaseField"):
                phase = Path(tmp) / f"{prefix}_00005000.vts"
                phase.touch()
                with self.subTest(prefix=prefix):
                    self.assertEqual(self.resolve_sources(source), (phase,) * 4)

    def test_openphase_from_another_timestep_is_not_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "OpenPhase_00000000.vts").touch()
            source = Path(tmp) / "Stresses_00005000.vts"
            self.assertEqual(self.resolve_sources(source), (None,) * 4)

    def test_comparison_views_load_interfaces_from_openphase_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            phase = Path(tmp) / "OpenPhase_00005000.vts"
            x, y, z = np.meshgrid(np.arange(3.0), np.arange(3.0), [0.0], indexing="ij")
            grid = pv.StructuredGrid(x, y, z)
            grid["Interfaces"] = np.full(grid.n_points, 2.0)
            grid.save(str(phase))
            for panel_type in (MultiViewPanel, MultiPropertyPanel):
                for source in (phase, Path(tmp) / "Stresses_00005000.vts"):
                    with self.subTest(view=panel_type.__name__, source=source.name):
                        panel = panel_type.__new__(panel_type)
                        panel.interfaces_on = SimpleNamespace(isChecked=lambda: True)
                        overlay = panel._build_overlay_grid(str(source), "z")
                        self.assertIsNotNone(overlay)
                        self.assertEqual(overlay["z"].shape, (160, 160))
                        np.testing.assert_allclose(overlay["z"], 2.0)
