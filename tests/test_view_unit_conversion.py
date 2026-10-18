"""Single View, Multi View and Multi Property convert displayed values with a From -> To unit control."""

import os
import types
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLineEdit

from multi_property.multi_property_panel import MultiPropertyPanel
from multi_view.multi_view_panel import MultiViewPanel
from utils.unit_conversion_control import UnitConversionControl
from viewer.panel_widget import PanelWidget

_STRESS_FILE = str(Path("Project1/VTK/CauchyStresses_00000000.vts").resolve())
_COMPOSITION_FILE = str(Path("Project1/VTK/Composition_00000000.vts").resolve())


def _stress_panel() -> PanelWidget:
    return PanelWidget(
        dataset_info={
            "id": "stresses",
            "label": "Cauchy Stresses",
            "files": [_STRESS_FILE],
            "dataset_config": {
                "label": "Cauchy Stresses",
                "units": "MPa",
                "scale": 1e-6,
                "scalars": [{"label": "von Mises", "array": "vonMises", "component": None}],
            },
            "tab_id": "single_view",
        }
    )


def _composition_panel() -> PanelWidget:
    return PanelWidget(
        dataset_info={
            "id": "composition",
            "label": "Composition",
            "files": [_COMPOSITION_FILE],
            "dataset_config": {
                "label": "Composition",
                "scalars": [{"label": "CL", "array": "MoleFractionsTotal_CL", "component": None}],
            },
            "tab_id": "single_view",
        }
    )


def _pick(combo, unit):
    """Choose a scale entry; each entry shows its prefix and keeps the unit as its data."""
    combo.setCurrentIndex(combo.findData(unit))


class SingleViewUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_the_control_is_a_from_to_pair_not_the_old_raw_dropdown(self):
        panel = _stress_panel()
        self.assertIsInstance(panel.unit_scale_combo, UnitConversionControl)

    def test_from_follows_the_datasets_unit_and_to_offers_its_family(self):
        panel = _stress_panel()
        control = panel.unit_scale_combo
        self.assertEqual(control.from_unit(), "MPa")
        self.assertEqual(control.to_unit(), "MPa")
        targets = [control.to_combo.itemData(i) for i in range(control.to_combo.count())]
        self.assertEqual(targets, ["MPa", "mPa", "Pa", "kPa", "GPa"])  # no conversion first; MPa not repeated
        labels = [control.to_combo.itemText(i) for i in range(control.to_combo.count())]
        self.assertEqual(labels, ["\u2014", "milli (m)", "base", "kilo (k)", "Giga (G)"])  # no unit names

    def test_mpa_to_gpa_scales_by_a_thousand_and_labels_the_colorbar(self):
        panel = _stress_panel()
        _pick(panel.unit_scale_combo.to_combo, "GPa")
        scale, label = panel.controller._get_display_params("von Mises")
        self.assertAlmostEqual(scale, 1e-3)
        self.assertEqual(label, "von Mises (GPa)")

    def test_no_conversion_keeps_the_datasets_own_unit_in_the_label(self):
        panel = _stress_panel()
        scale, label = panel.controller._get_display_params("von Mises")
        self.assertEqual(scale, 1.0)
        self.assertEqual(label, "von Mises (MPa)")

    def test_dimensionless_field_converts_to_percent(self):
        panel = _composition_panel()
        control = panel.unit_scale_combo
        self.assertEqual(control.from_unit(), "-")
        _pick(control.to_combo, "%")
        scale, label = panel.controller._get_display_params("CL")
        self.assertAlmostEqual(scale, 100.0)
        self.assertEqual(label, "CL (%)")

    def test_a_custom_colorbar_label_still_wins_over_the_scalar_name(self):
        panel = _stress_panel()
        panel.colorbar_label_edit.setText("Stress")
        _pick(panel.unit_scale_combo.to_combo, "GPa")
        self.assertEqual(panel.controller._get_display_params("von Mises")[1], "Stress (GPa)")

    def test_changing_the_conversion_redraws(self):
        panel = _stress_panel()
        with mock.patch.object(panel.controller, "_refresh_from_toolbar") as refresh:
            _pick(panel.unit_scale_combo.to_combo, "kPa")
        refresh.assert_called_with("unit-scale")

    def test_the_conversion_survives_redraws_of_the_same_scalar(self):
        panel = _stress_panel()
        _pick(panel.unit_scale_combo.to_combo, "GPa")
        panel.controller.refresh_view()
        self.assertEqual(panel.unit_scale_combo.to_unit(), "GPa")


class MultiViewUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _panel_stub(self):
        return types.SimpleNamespace(unit_scale_combo=UnitConversionControl(), colorbar_label_edit=QLineEdit())

    def test_from_follows_the_scalars_unit_and_to_converts(self):
        stub = self._panel_stub()
        scale, label = MultiViewPanel._get_display_params(stub, "von Mises", "MPa")
        self.assertEqual((scale, label), (1.0, "von Mises (MPa)"))
        _pick(stub.unit_scale_combo.to_combo, "GPa")
        scale, label = MultiViewPanel._get_display_params(stub, "von Mises", "MPa")
        self.assertAlmostEqual(scale, 1e-3)
        self.assertEqual(label, "von Mises (GPa)")

    def test_a_scalar_without_a_unit_offers_percent(self):
        stub = self._panel_stub()
        MultiViewPanel._get_display_params(stub, "CL", None)
        _pick(stub.unit_scale_combo.to_combo, "%")
        scale, label = MultiViewPanel._get_display_params(stub, "CL", None)
        self.assertAlmostEqual(scale, 100.0)
        self.assertEqual(label, "CL (%)")

    def test_another_scalar_with_another_unit_resets_the_choice(self):
        stub = self._panel_stub()
        MultiViewPanel._get_display_params(stub, "von Mises", "MPa")
        _pick(stub.unit_scale_combo.to_combo, "GPa")
        scale, label = MultiViewPanel._get_display_params(stub, "CL", None)
        self.assertEqual((scale, label), (1.0, "CL"))

    def test_raw_values_stay_raw_but_the_scalar_knows_its_unit_so_mpa_and_gpa_remain_available(self):
        dataset_info = {
            "available_projects": [
                {
                    "files": [],
                    "dataset_config": {
                        "units": "MPa",
                        "scale": 1e-6,
                        "scalars": [{"label": "CRSS 0", "array": "CRSS_0_0"}],
                    },
                }
            ]
        }
        scalar_def = MultiViewPanel._build_scalar_defs(dataset_info)[0]
        self.assertEqual((scalar_def["scale"], scalar_def["units"]), (1.0, None))  # displayed values stay raw (Pa)
        self.assertEqual(scalar_def["native_units"], "Pa")
        stub = self._panel_stub()
        MultiViewPanel._get_display_params(stub, "CRSS 0", scalar_def["native_units"])
        self.assertEqual(stub.unit_scale_combo.from_combo.currentText(), "base")
        _pick(stub.unit_scale_combo.to_combo, "MPa")
        scale, label = MultiViewPanel._get_display_params(stub, "CRSS 0", scalar_def["native_units"])
        self.assertAlmostEqual(scale, 1e-6)
        self.assertEqual(label, "CRSS 0 (MPa)")
        _pick(stub.unit_scale_combo.to_combo, "GPa")
        self.assertAlmostEqual(MultiViewPanel._get_display_params(stub, "CRSS 0", "Pa")[0], 1e-9)

    def test_a_per_scalar_unit_and_scale_are_used_too(self):
        dataset_info = {
            "available_projects": [
                {
                    "files": [],
                    "dataset_config": {
                        "scalars": [{"label": "S", "array": "S", "units": "MPa", "scale": 1e-6}],
                    },
                }
            ]
        }
        self.assertEqual(MultiViewPanel._build_scalar_defs(dataset_info)[0]["native_units"], "Pa")

    def test_a_scalar_without_a_unit_has_none(self):
        dataset_info = {"available_projects": [{"files": [], "dataset_config": {"scalars": [{"label": "C", "array": "C"}]}}]}
        self.assertEqual(MultiViewPanel._build_scalar_defs(dataset_info)[0]["native_units"], "")

    def test_the_panel_uses_the_new_control_next_to_the_conversion_caption(self):
        panel = MultiViewPanel({"available_projects": []})
        self.assertIsInstance(panel.unit_scale_combo, UnitConversionControl)


class MultiPropertyUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _stub(self, keys, defs):
        stub = types.SimpleNamespace(
            unit_scale_combo=UnitConversionControl(),
            _selected_keys=list(keys),
            _scalar_defs=defs,
            _ranges={key: {"selected_min": 0.0} for key in keys},
        )
        stub._scalar_def_for_key = lambda key: next(d for d in defs if d["value"] == key)
        stub._follow_first_property_unit = lambda: MultiPropertyPanel._follow_first_property_unit(stub)
        return stub

    def test_panel_has_the_from_to_control_in_the_range_row(self):
        panel = MultiPropertyPanel({"available_projects": []})
        range_layout = panel.layout().itemAt(0).widget().layout().itemAt(1).widget().layout()
        widgets = [range_layout.itemAt(i).widget() for i in range(range_layout.count())]
        self.assertIsInstance(panel.unit_scale_combo, UnitConversionControl)
        self.assertIn(panel.unit_scale_combo, widgets)

    def test_from_follows_the_first_selected_property(self):
        defs = [{"value": "a", "native_units": "MPa"}, {"value": "b", "native_units": None}]
        stub = self._stub(["a", "b"], defs)
        MultiPropertyPanel._get_display_params(stub, "a")
        self.assertEqual(stub.unit_scale_combo.from_unit(), "MPa")

    def test_one_conversion_applies_to_every_property(self):
        defs = [{"value": "a", "native_units": "MPa"}, {"value": "b", "native_units": "MPa"}]
        stub = self._stub(["a", "b"], defs)
        MultiPropertyPanel._get_display_params(stub, "a")
        _pick(stub.unit_scale_combo.to_combo, "GPa")
        for label in ("a", "b"):
            scale, text = MultiPropertyPanel._get_display_params(stub, label)
            self.assertAlmostEqual(scale, 1e-3)
            self.assertEqual(text, f"{label} (GPa)")

    def test_a_new_first_property_unit_resets_the_choice_and_drops_stored_ranges(self):
        defs = [{"value": "a", "native_units": "MPa"}, {"value": "b", "native_units": None}]
        stub = self._stub(["a"], defs)
        MultiPropertyPanel._get_display_params(stub, "a")
        _pick(stub.unit_scale_combo.to_combo, "GPa")
        stub._selected_keys = ["b"]
        scale, _ = MultiPropertyPanel._get_display_params(stub, "b")
        self.assertEqual(scale, 1.0)
        self.assertEqual(stub._ranges, {})

    def test_a_stress_property_in_raw_pa_can_be_shown_in_mpa(self):
        defs = [{"value": "a", "native_units": "Pa"}]
        stub = self._stub(["a"], defs)
        MultiPropertyPanel._get_display_params(stub, "Stress")
        _pick(stub.unit_scale_combo.to_combo, "MPa")
        scale, label = MultiPropertyPanel._get_display_params(stub, "Stress")
        self.assertAlmostEqual(scale, 1e-6)
        self.assertEqual(label, "Stress (MPa)")

    def test_the_same_unit_keeps_the_ranges(self):
        defs = [{"value": "a", "native_units": "MPa"}]
        stub = self._stub(["a"], defs)
        MultiPropertyPanel._get_display_params(stub, "a")  # the first sync adopts the property's unit
        stub._ranges = {"a": {"selected_min": 0.0}}
        MultiPropertyPanel._get_display_params(stub, "a")
        self.assertIn("a", stub._ranges)


if __name__ == "__main__":
    unittest.main()
