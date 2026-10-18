"""Safe element-wise formulas for Custom Graph conversions (Qt-free).

`x` is the column being converted. Other columns of the same file can be used by name (`Time`) or, when the
name has spaces or symbols, in square brackets (`[Epsilon xx]`). Examples: `x*9/5+32`, `x^2`, `log10(x)`,
`[Sigma_xx] / [Epsilon_xx]`, `x * Time + Pressure`.

Only numbers, `x`, `pi`, `e`, column names, arithmetic and a short list of functions are allowed;
everything else is rejected, so a formula typed into the UI cannot run code.
"""

from __future__ import annotations

import ast
import operator
import re
from functools import lru_cache
from typing import Callable, Mapping

import numpy as np

_FUNCTIONS = {
    "abs": np.abs, "sqrt": np.sqrt, "exp": np.exp, "ln": np.log, "log": np.log, "log10": np.log10,
    "log2": np.log2, "sin": np.sin, "cos": np.cos, "tan": np.tan,
}
FUNCTION_NAMES = tuple(_FUNCTIONS)
_CONSTANTS = {"pi": float(np.pi), "e": float(np.e)}
RESERVED_NAMES = frozenset({"x", *_CONSTANTS})
_BINARY = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Pow: operator.pow, ast.Mod: operator.mod,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_MAX_LENGTH = 300
_BRACKETED = re.compile(r"\[([^\]]+)\]")
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

Evaluator = Callable[[np.ndarray, Mapping[str, np.ndarray]], np.ndarray]


def column_reference(name: str) -> str:
    """How a column is written in a formula: its bare name, or `[name]` when that is not a plain identifier."""
    usable = _IDENTIFIER.match(name) and name not in RESERVED_NAMES and name not in _FUNCTIONS
    return name if usable else f"[{name}]"


def _build(node: ast.AST, columns: dict[str, str]) -> Evaluator:
    """`columns` maps an identifier as it appears in the parsed text to the real column name."""
    if isinstance(node, ast.Expression):
        return _build(node.body, columns)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        value = float(node.value)
        return lambda x, cols: np.full(x.shape, value)
    if isinstance(node, ast.Name):
        if node.id == "x":
            return lambda x, cols: x
        if node.id in _CONSTANTS and node.id not in columns:
            value = _CONSTANTS[node.id]
            return lambda x, cols: np.full(x.shape, value)
        if node.id in columns:
            name = columns[node.id]

            def column(x, cols, name=name):
                if name not in cols:
                    raise ValueError(f"column '{name}' is not available")
                return np.asarray(cols[name], dtype=float)

            return column
        raise ValueError(f"unknown name '{node.id}': use x, or a column name")
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        op, left, right = _BINARY[type(node.op)], _build(node.left, columns), _build(node.right, columns)
        return lambda x, cols: op(left(x, cols), right(x, cols))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        op, operand = _UNARY[type(node.op)], _build(node.operand, columns)
        return lambda x, cols: op(operand(x, cols))
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in _FUNCTIONS
        and len(node.args) == 1
        and not node.keywords
    ):
        func, arg = _FUNCTIONS[node.func.id], _build(node.args[0], columns)
        return lambda x, cols: func(arg(x, cols))
    raise ValueError("unsupported expression")


@lru_cache(maxsize=256)
def compile_formula(text: str, columns: tuple[str, ...] = ()) -> Callable[..., np.ndarray]:
    """Compile a formula into `run(x, other_columns=None)`; raises ValueError when it is invalid.

    `columns` are the names of the columns the formula may refer to. `other_columns` maps those names to
    their data when the formula is run.
    """
    source = str(text or "").strip()
    if not source:
        raise ValueError("empty formula")
    if len(source) > _MAX_LENGTH:
        raise ValueError("formula too long")
    known = {name for name in columns if name}
    mapping: dict[str, str] = {name: name for name in known if _IDENTIFIER.match(name)}

    def replace(match: re.Match) -> str:
        name = match.group(1).strip()
        if name not in known:
            raise ValueError(f"unknown column '{name}'")
        alias = f"__col{len(mapping)}__"
        mapping[alias] = name
        return alias

    source = _BRACKETED.sub(replace, source).replace("^", "**")
    try:
        tree = ast.parse(source, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"invalid formula: {exc.msg}") from exc
    func = _build(tree, mapping)

    def run(values, other_columns: Mapping[str, np.ndarray] | None = None) -> np.ndarray:
        data = np.asarray(values, dtype=float)
        with np.errstate(all="ignore"):
            return np.asarray(func(data, other_columns or {}), dtype=float)

    return run
