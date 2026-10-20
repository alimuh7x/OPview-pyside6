"""Unit table and conversion resolver shared by the Custom Graph panel and canvas."""

import unittest

import numpy as np

from config import units


class NormalizeUnitTests(unittest.TestCase):
    def test_brackets_case_and_aliases(self):
        for raw, expected in (
            ("Pa", "Pa"), ("[Pa]", "Pa"), ("(MPa)", "MPa"), ("mpa", "MPa"), ("GPA", "GPa"), (" kPa ", "kPa"),
            ("s", "s"), ("sec", "s"), ("seconds", "s"), ("ms", "ms"), ("minutes", "min"), ("hr", "h"), ("hours", "h"),
            ("days", "day"), ("%", "%"), ("percent", "%"), ("-", "-"), ("", ""), ("[-]", "-"),
            ("K", "K"), ("degC", "°C"), ("°C", "°C"), ("celsius", "°C"),
            ("um", "µm"), ("µm", "µm"), ("nm", "nm"), ("mm", "mm"), ("m", "m"),
            ("microstrain", "µε"), ("ue", "µε"),
        ):
            self.assertEqual(units.normalize_unit(raw), expected, raw)

    def test_unknown_units_are_kept_as_typed(self):
        self.assertEqual(units.normalize_unit("W/m2"), "W/m2")
        self.assertIsNone(units.family_of("W/m2"))


class FamilyTests(unittest.TestCase):
    def test_families(self):
        self.assertEqual(units.family_of("MPa"), "pressure")
        self.assertEqual(units.family_of("min"), "time")
        self.assertEqual(units.family_of("µm"), "length")
        self.assertEqual(units.family_of("%"), "strain")
        self.assertEqual(units.family_of("°C"), "temperature")
        self.assertIsNone(units.family_of(""))

    def test_targets_are_the_family_without_the_source(self):
        self.assertEqual(units.targets_for("MPa"), ["mPa", "Pa", "kPa", "GPa"])
        self.assertEqual(units.targets_for("s"), ["ms", "min", "h", "day"])
        self.assertEqual(units.targets_for("K"), ["°C"])
        self.assertEqual(units.targets_for("unknown"), [])


class AffineTests(unittest.TestCase):
    def test_pressure_both_directions(self):
        self.assertEqual(units.affine("Pa", "MPa"), (1e-6, 0.0))
        self.assertEqual(units.affine("MPa", "GPa"), (1e-3, 0.0))
        self.assertAlmostEqual(units.affine("GPa", "Pa")[0], 1e9)

    def test_time(self):
        self.assertAlmostEqual(units.affine("s", "min")[0], 1 / 60)
        self.assertAlmostEqual(units.affine("ms", "h")[0], 1e-3 / 3600)
        self.assertAlmostEqual(units.affine("day", "s")[0], 86400.0)

    def test_strain(self):
        self.assertAlmostEqual(units.affine("-", "%")[0], 100.0)
        self.assertAlmostEqual(units.affine("%", "µε")[0], 1e4)

    def test_temperature_has_an_offset(self):
        a, b = units.affine("K", "°C")
        self.assertEqual((a, b), (1.0, -273.15))
        a, b = units.affine("°C", "K")
        self.assertEqual((a, b), (1.0, 273.15))
        self.assertAlmostEqual(a * 25.0 + b, 298.15)

    def test_round_trip_is_the_identity(self):
        for source, target in (("MPa", "Pa"), ("min", "ms"), ("°C", "K"), ("µε", "%")):
            a1, b1 = units.affine(source, target)
            a2, b2 = units.affine(target, source)
            self.assertAlmostEqual(a2 * (a1 * 7.5 + b1) + b2, 7.5, places=9, msg=(source, target))

    def test_incompatible_or_unknown_units_have_no_conversion(self):
        self.assertIsNone(units.affine("Pa", "s"))
        self.assertIsNone(units.affine("Pa", "unknown"))
        self.assertIsNone(units.affine("", "MPa"))


class ParseNumberTests(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual(units.parse_number("2.5", 1.0), 2.5)
        self.assertEqual(units.parse_number("1,5", 1.0), 1.5)  # decimal comma
        self.assertEqual(units.parse_number("1e-3", 1.0), 1e-3)
        self.assertEqual(units.parse_number(" -273.15 ", 0.0), -273.15)
        self.assertEqual(units.parse_number(0.25, 1.0), 0.25)

    def test_blank_or_invalid_falls_back_to_the_default(self):
        for text in ("", "  ", "abc", None, "nan", "inf"):
            self.assertEqual(units.parse_number(text, 7.0), 7.0, text)


class ResolveTransformTests(unittest.TestCase):
    def _apply(self, transform, values):
        return transform.apply(np.asarray(values, dtype=float))

    def test_as_is_is_the_identity_and_names_the_source_unit(self):
        t = units.resolve_transform("as-is", source_unit="Pa")

        self.assertEqual(self._apply(t, [1, 2]).tolist(), [1, 2])
        self.assertEqual(t.unit, "Pa")

    def test_legacy_mpa_assumes_pa_when_the_source_is_unknown(self):
        t = units.resolve_transform("mpa")

        self.assertEqual(self._apply(t, [2e6]).tolist(), [2.0])
        self.assertEqual(t.unit, "MPa")

    def test_legacy_mpa_uses_the_known_source_unit(self):
        t = units.resolve_transform("mpa", source_unit="GPa")  # data are in GPa: 3 GPa = 3000 MPa

        self.assertAlmostEqual(float(self._apply(t, [3.0])[0]), 3000.0)

    def test_a_chosen_target_unit_converts_from_the_source(self):
        t = units.resolve_transform("to:GPa", source_unit="MPa")

        self.assertAlmostEqual(float(self._apply(t, [2500.0])[0]), 2.5)
        self.assertEqual(t.unit, "GPa")

    def test_target_without_a_usable_source_is_the_identity(self):
        t = units.resolve_transform("to:GPa", source_unit="")

        self.assertEqual(self._apply(t, [5.0]).tolist(), [5.0])

    def test_legacy_percent_and_time_defaults(self):
        self.assertEqual(self._apply(units.resolve_transform("percent"), [0.5]).tolist(), [50.0])
        self.assertAlmostEqual(float(self._apply(units.resolve_transform("sec-to-min"), [120.0])[0]), 2.0)
        self.assertAlmostEqual(float(self._apply(units.resolve_transform("sec-to-hour"), [7200.0])[0]), 2.0)

    def test_legacy_conversion_with_a_source_of_another_family_keeps_the_legacy_assumption(self):
        t = units.resolve_transform("mpa", source_unit="m")  # a length cannot be turned into MPa

        self.assertAlmostEqual(float(self._apply(t, [2e6])[0]), 2.0)

    def test_custom_factor_and_offset(self):
        t = units.resolve_transform("custom", factor="2", offset="10", custom_unit="W")

        self.assertEqual(self._apply(t, [1, 2]).tolist(), [12.0, 14.0])
        self.assertEqual(t.unit, "W")

    def test_custom_defaults_are_factor_one_offset_zero(self):
        t = units.resolve_transform("custom")

        self.assertEqual(self._apply(t, [3.0]).tolist(), [3.0])

    def test_custom_accepts_decimal_commas_and_ignores_garbage(self):
        self.assertEqual(self._apply(units.resolve_transform("custom", factor="0,5"), [4.0]).tolist(), [2.0])
        self.assertEqual(self._apply(units.resolve_transform("custom", factor="oops", offset="x"), [4.0]).tolist(), [4.0])

    def test_log10_drops_non_positive_values(self):
        t = units.resolve_transform("log10")

        out = self._apply(t, [100.0, 0.0, -5.0, 10.0])

        self.assertEqual(out[0], 2.0)
        self.assertTrue(np.isnan(out[1]) and np.isnan(out[2]))
        self.assertEqual(out[3], 1.0)
        self.assertEqual(t.unit, "log10")

    def test_aliases_from_display_labels(self):
        self.assertEqual(units.normalize_conversion("GPa"), "gpa")
        self.assertEqual(units.normalize_conversion("%"), "percent")
        self.assertEqual(units.normalize_conversion("As-is"), "as-is")
        self.assertEqual(units.normalize_conversion("Log10"), "log10")
        self.assertEqual(units.normalize_conversion("sec -> min"), "sec-to-min")
        self.assertEqual(units.normalize_conversion("to:MPa"), "to:MPa")
        self.assertEqual(units.normalize_conversion("Custom"), "custom")
        self.assertEqual(units.normalize_conversion("nonsense"), "as-is")


class ScaleOnlyUnitTests(unittest.TestCase):
    """Heatmap views multiply values by one factor, so they only use units related by a pure scale."""

    def test_scale_units_exclude_offset_units(self):
        listed = units.scale_units()
        for unit in ("Pa", "GPa", "s", "min", "mm", "µm", "-", "%", "µε"):
            self.assertIn(unit, listed)
        self.assertNotIn("K", listed)
        self.assertNotIn("°C", listed)

    def test_scale_targets_follow_the_family_and_exclude_the_source(self):
        self.assertEqual(units.scale_targets_for("MPa"), ["mPa", "Pa", "kPa", "GPa"])
        self.assertEqual(units.scale_targets_for("-"), ["n-", "µε", "m-", "%", "k-", "M-", "G-"])
        self.assertEqual(units.scale_targets_for("K"), [])
        self.assertEqual(units.scale_targets_for("mol"), [])

    def test_scale_between_gives_the_factor(self):
        self.assertAlmostEqual(units.scale_between("MPa", "GPa"), 1e-3)
        self.assertAlmostEqual(units.scale_between("Pa", "MPa"), 1e-6)
        self.assertAlmostEqual(units.scale_between("-", "%"), 100.0)
        self.assertAlmostEqual(units.scale_between("s", "min"), 1 / 60)
        self.assertEqual(units.scale_between("MPa", "MPa"), 1.0)

    def test_scale_between_is_none_when_not_a_pure_scale(self):
        self.assertIsNone(units.scale_between("MPa", "s"))
        self.assertIsNone(units.scale_between("K", "°C"))
        self.assertIsNone(units.scale_between("mol", "kmol"))


class PrefixedUnitTests(unittest.TestCase):
    """Any SI prefix on a known base unit converts: N/kN/MN, J/kJ/MJ, W, g/kg, Hz, V, A, m/cm/mm."""

    def test_new_base_units_have_families(self):
        for unit, family in (
            ("N", "force"), ("kN", "force"), ("MN", "force"), ("mN", "force"),
            ("J", "energy"), ("kJ", "energy"), ("MJ", "energy"), ("GJ", "energy"),
            ("W", "power"), ("kW", "power"), ("MW", "power"),
            ("g", "mass"), ("kg", "mass"), ("mg", "mass"),
            ("Hz", "frequency"), ("kHz", "frequency"),
            ("V", "voltage"), ("mV", "voltage"), ("A", "current"), ("mA", "current"),
            ("cm", "length"), ("km", "length"),
        ):
            self.assertEqual(units.family_of(unit), family, unit)

    def test_conversion_factors(self):
        for source, target, factor in (
            ("N", "kN", 1e-3), ("kN", "MN", 1e-3), ("MN", "N", 1e6), ("mN", "N", 1e-3),
            ("J", "kJ", 1e-3), ("kJ", "MJ", 1e-3), ("MJ", "J", 1e6), ("GJ", "MJ", 1e3),
            ("kW", "W", 1e3), ("kg", "g", 1e3), ("g", "mg", 1e3), ("cm", "mm", 10.0), ("km", "m", 1e3),
            ("kHz", "Hz", 1e3), ("mA", "A", 1e-3),
        ):
            self.assertAlmostEqual(units.affine(source, target)[0] / factor, 1.0, msg=f"{source}->{target}")

    def test_any_prefix_works_even_when_not_listed(self):
        self.assertEqual(units.family_of("hPa"), None)  # hecto is not a supported prefix
        self.assertEqual(units.family_of("TPa"), "pressure")
        self.assertEqual(units.family_of("dm"), "length")
        self.assertAlmostEqual(units.affine("TPa", "GPa")[0], 1e3)
        self.assertAlmostEqual(units.affine("dm", "cm")[0], 10.0)
        self.assertAlmostEqual(units.affine("ns", "µs")[0], 1e-3)
        self.assertAlmostEqual(units.affine("pm", "nm")[0], 1e-3)

    def test_ascii_u_stands_for_micro(self):
        self.assertEqual(units.normalize_unit("uN"), "µN")
        self.assertEqual(units.normalize_unit("us"), "µs")
        self.assertAlmostEqual(units.affine("uN", "mN")[0], 1e-3)

    def test_listed_targets_of_the_new_families(self):
        self.assertEqual(units.targets_for("N"), ["mN", "kN", "MN", "GN"])
        self.assertEqual(units.targets_for("MJ"), ["mJ", "J", "kJ", "GJ"])
        self.assertIn("kg", units.targets_for("g"))
        self.assertEqual(units.targets_for("TPa"), ["mPa", "Pa", "kPa", "MPa", "GPa"])  # an unlisted prefix still gets its family

    def test_names_that_look_like_prefixed_units_keep_their_meaning(self):
        self.assertEqual(units.family_of("min"), "time")
        self.assertEqual(units.family_of("h"), "time")
        self.assertEqual(units.family_of("m"), "length")
        self.assertEqual(units.family_of("mm"), "length")
        self.assertEqual(units.family_of("ms"), "time")
        self.assertEqual(units.family_of("day"), "time")
        self.assertIsNone(units.family_of("mol"))
        self.assertIsNone(units.family_of("W/m2"))
        self.assertIsNone(units.family_of("Nm"))

    def test_case_is_kept_where_it_changes_the_meaning(self):
        self.assertEqual(units.normalize_unit("mN"), "mN")
        self.assertEqual(units.normalize_unit("MN"), "MN")
        self.assertAlmostEqual(units.affine("MN", "mN")[0], 1e9)
        self.assertEqual(units.normalize_unit("mpa"), "MPa")  # still a convenience alias: unambiguous

    def test_different_families_do_not_convert(self):
        self.assertIsNone(units.affine("N", "J"))
        self.assertIsNone(units.affine("kg", "kN"))

    def test_scale_helpers_cover_the_new_units(self):
        self.assertAlmostEqual(units.scale_between("kJ", "MJ"), 1e-3)
        self.assertIn("kN", units.scale_units())
        self.assertIn("MJ", units.scale_targets_for("J"))

    def test_family_units_are_sorted_from_milli_to_giga_with_the_base_in_place(self):
        self.assertEqual(units.family_units("Pa"), ["mPa", "Pa", "kPa", "MPa", "GPa"])
        self.assertEqual(units.family_units("MPa"), ["mPa", "Pa", "kPa", "MPa", "GPa"])  # same list for any member
        self.assertEqual(units.family_units("m"), ["nm", "µm", "mm", "cm", "m", "km"])
        self.assertEqual(units.family_units("N"), ["mN", "N", "kN", "MN", "GN"])
        self.assertEqual(units.family_units("s"), ["ms", "s", "min", "h", "day"])
        self.assertEqual(units.family_units("-"), ["n-", "µε", "m-", "%", "-", "k-", "M-", "G-"])
        self.assertEqual(units.family_units("K"), ["K", "°C"])

    def test_scale_labels_name_the_prefix_and_never_the_base_unit(self):
        for unit, label in (
            ("Pa", "base"), ("kPa", "kilo (k)"), ("MPa", "Mega (M)"), ("GPa", "Giga (G)"), ("mPa", "milli (m)"),
            ("m", "base"), ("mm", "milli (m)"), ("cm", "centi (c)"), ("µm", "micro (µ)"), ("nm", "nano (n)"),
            ("km", "kilo (k)"), ("N", "base"), ("kN", "kilo (k)"), ("MJ", "Mega (M)"), ("kg", "kilo (k)"),
            ("s", "base"), ("ms", "milli (m)"), ("min", "minute (min)"), ("h", "hour (h)"), ("day", "day"),
            ("-", "base"), ("%", "percent (%)"), ("µε", "micro (µ)"),
            ("K", "Kelvin (K)"), ("°C", "Celsius (°C)"), ("TPa", "Tera (T)"),
        ):
            self.assertEqual(units.scale_label(unit), label, unit)

    def test_data_with_no_unit_can_be_scaled_by_prefix_alone(self):
        self.assertAlmostEqual(units.scale_between("-", "k-"), 1e-3)
        self.assertAlmostEqual(units.scale_between("M-", "k-"), 1e3)
        self.assertAlmostEqual(units.scale_between("k-", "-"), 1e3)
        self.assertAlmostEqual(units.scale_between("-", "%"), 100.0)
        self.assertEqual(units.scale_label("k-"), "kilo (k)")
        self.assertEqual(units.scale_label("G-"), "Giga (G)")

    def test_display_unit_prints_nothing_for_data_without_a_unit(self):
        for unit in ("-", "n-", "m-", "k-", "M-", "G-", "", None):
            self.assertEqual(units.display_unit(unit), "", unit)
        for unit, shown in (("MPa", "MPa"), ("%", "%"), ("µε", "µε"), ("s", "s"), ("mpa", "MPa")):
            self.assertEqual(units.display_unit(unit), shown)

    def test_scale_label_of_an_unknown_unit_is_base(self):
        self.assertEqual(units.scale_label("mol"), "base")
        self.assertEqual(units.scale_label(""), "base")

    def test_family_units_include_an_unlisted_prefix_in_its_place(self):
        self.assertEqual(units.family_units("TPa"), ["mPa", "Pa", "kPa", "MPa", "GPa", "TPa"])

    def test_family_units_of_an_unknown_unit_is_just_that_unit(self):
        self.assertEqual(units.family_units("mol"), ["mol"])
        self.assertEqual(units.family_units(""), [])

    def test_family_units_for_image_views_leave_temperature_alone(self):
        self.assertEqual(units.family_units("K", scale_only=True), ["K"])
        self.assertEqual(units.family_units("kPa", scale_only=True), ["mPa", "Pa", "kPa", "MPa", "GPa"])

    def test_each_base_unit_reaches_its_prefixes_through_the_to_list(self):
        self.assertEqual(units.targets_for("Pa"), ["mPa", "kPa", "MPa", "GPa"])
        self.assertEqual(units.targets_for("m"), ["nm", "µm", "mm", "cm", "km"])
        self.assertEqual(units.targets_for("°C"), ["K"])
        self.assertEqual(units.targets_for("K"), ["°C"])

    def test_declarable_units_are_only_seconds_and_temperature(self):
        self.assertEqual(units.declarable_units(), ["s", "K", "°C"])
        self.assertEqual(units.declarable_units(scale_only=True), ["s"])
        for unit in ("Pa", "N", "J", "W", "m", "g"):
            self.assertEqual(units.family_units(unit)[0] != "", True)  # still recognised when a file gives them

    def test_raw_unit_is_the_unit_the_stored_values_are_in(self):
        """A dataset says `units: MPa, scale: 1e-6`: the stored values are in Pa, shown as MPa after scaling."""
        self.assertEqual(units.raw_unit("MPa", 1e-6), "Pa")
        self.assertEqual(units.raw_unit("GPa", 1e-9), "Pa")
        self.assertEqual(units.raw_unit("kPa", 1e-3), "Pa")
        self.assertEqual(units.raw_unit("MPa", 1.0), "MPa")
        self.assertEqual(units.raw_unit("MPa", None), "MPa")
        self.assertEqual(units.raw_unit("mm", 1e3), "m")

    def test_raw_unit_is_empty_when_there_is_no_unit_or_no_matching_one(self):
        self.assertEqual(units.raw_unit(None, 1e-6), "")
        self.assertEqual(units.raw_unit("", 1.0), "")
        self.assertEqual(units.raw_unit("MPa", 7.0), "MPa")  # no unit of that scale: keep the stated unit

    def test_the_unit_list_has_no_duplicates(self):
        listed = units.all_units()
        self.assertEqual(len(listed), len(set(listed)))


if __name__ == "__main__":
    unittest.main()
