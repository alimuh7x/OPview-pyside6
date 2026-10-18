import unittest

import numpy as np

from config import formula, units


class FormulaTests(unittest.TestCase):
    def run_f(self, text, values):
        return formula.compile_formula(text)(np.asarray(values, dtype=float))

    def test_basic_arithmetic(self):
        self.assertTrue(np.allclose(self.run_f("x*9/5+32", [0, 100]), [32, 212]))

    def test_caret_is_power(self):
        self.assertTrue(np.allclose(self.run_f("x^2", [2, 3]), [4, 9]))

    def test_functions_and_constants(self):
        self.assertTrue(np.allclose(self.run_f("log10(x)", [10, 100]), [1, 2]))
        self.assertTrue(np.allclose(self.run_f("sqrt(x)*pi", [4]), [2 * np.pi]))

    def test_constant_formula_broadcasts(self):
        self.assertEqual(list(self.run_f("5", [1, 2, 3])), [5, 5, 5])

    def test_rejects_unsafe_or_unknown(self):
        for bad in ("__import__('os')", "x.real", "y+1", "open(x)", "x[0]", "lambda: 1", "", "x+"):
            with self.assertRaises(ValueError, msg=bad):
                formula.compile_formula(bad)

    def test_transform_uses_formula_and_unit(self):
        t = units.resolve_transform("custom", formula="x/1000", custom_unit="kN")
        self.assertTrue(np.allclose(t.apply([1000, 2000]), [1, 2]))
        self.assertEqual(t.unit, "kN")

    def test_invalid_formula_falls_back_to_identity(self):
        t = units.resolve_transform("custom", formula="x+")
        self.assertEqual(list(t.apply([1, 2])), [1, 2])

    def test_legacy_factor_offset_still_work(self):
        t = units.resolve_transform("custom", factor="2", offset="1")
        self.assertEqual(list(t.apply([1, 2])), [3, 5])


if __name__ == "__main__":
    unittest.main()


class ColumnReferenceTests(unittest.TestCase):
    COLS = {"Sigma_xx": np.array([10.0, 20.0]), "Epsilon xx": np.array([2.0, 4.0]), "Time": np.array([1.0, 2.0])}

    def run_f(self, text, x):
        fn = formula.compile_formula(text, tuple(self.COLS))
        return fn(np.asarray(x, dtype=float), self.COLS)

    def test_other_column_by_name(self):
        self.assertTrue(np.allclose(self.run_f("x * Time", [3, 4]), [3, 8]))

    def test_column_with_space_needs_brackets(self):
        self.assertTrue(np.allclose(self.run_f("[Sigma_xx] / [Epsilon xx]", [0, 0]), [5, 5]))

    def test_three_columns(self):
        self.assertTrue(np.allclose(self.run_f("x * Time + [Sigma_xx]", [1, 1]), [11, 22]))

    def test_unknown_column_rejected_at_compile(self):
        with self.assertRaises(ValueError):
            formula.compile_formula("x * Nope", tuple(self.COLS))
        with self.assertRaises(ValueError):
            formula.compile_formula("[Nope] + 1", tuple(self.COLS))

    def test_column_names_do_not_shadow_x_or_constants(self):
        fn = formula.compile_formula("x + 1", ("x", "pi"))
        self.assertTrue(np.allclose(fn(np.array([1.0]), {"x": np.array([9.0]), "pi": np.array([9.0])}), [2]))

    def test_missing_data_raises_value_error_at_run(self):
        fn = formula.compile_formula("x * Time", ("Time",))
        with self.assertRaises(ValueError):
            fn(np.array([1.0]), {})

    def test_transform_applies_with_columns_and_falls_back_without(self):
        t = units.resolve_transform("custom", formula="x * Time", column_names=tuple(self.COLS))
        self.assertTrue(np.allclose(t.apply([3, 4], self.COLS), [3, 8]))
        self.assertEqual(list(t.apply([3, 4]), ), [3, 4])  # columns unavailable: data left as it is
