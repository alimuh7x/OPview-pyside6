"""Unit table and conversion resolver for Custom Graph (Qt-free).

A conversion turns a column from its *source unit* into a *target unit*: `y = a * x + b`. Units live in
families (pressure, time, length, strain, temperature); each unit is stored as a scale and an offset to a
family base, so converting between any two units of a family is one affine map. That covers offsets
(K to degC) as well as plain factors, and a custom formula in `x` (see config/formula.py) covers everything else.

The older conversion keys (`mpa`, `gpa`, `percent`, `sec-to-min`, `sec-to-hour`) still work. Without a known
source unit they keep their original assumption (Pa, a fraction, seconds); with one, they convert from it.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

import numpy as np

from config.formula import compile_formula

# SI prefixes. `h` (hecto) and `da` are left out on purpose: `h` is the hour and `min` the minute.
SI_PREFIXES: dict[str, float] = {
    "p": 1e-12, "n": 1e-9, "µ": 1e-6, "m": 1e-3, "c": 1e-2, "d": 1e-1,
    "k": 1e3, "M": 1e6, "G": 1e9, "T": 1e12,
}

# Base unit -> (family, prefixes listed in the dropdowns, small to large). Any prefix above also works when
# typed or read from a file ("TPa", "dm"); the listed ones are just the ones the dropdowns offer.
BASE_UNITS: dict[str, tuple[str, tuple[str, ...]]] = {
    "Pa": ("pressure", ("m", "", "k", "M", "G")),
    "s": ("time", ("m", "")),
    "m": ("length", ("n", "µ", "m", "c", "", "k")),
    "N": ("force", ("m", "", "k", "M", "G")),
    "J": ("energy", ("m", "", "k", "M", "G")),
    "W": ("power", ("m", "", "k", "M", "G")),
    "g": ("mass", ("µ", "m", "", "k")),
    "Hz": ("frequency", ("", "k", "M", "G")),
    "V": ("voltage", ("µ", "m", "", "k")),
    "A": ("current", ("µ", "m", "", "k")),
}

# Units with no SI prefix: (scale, offset) to the family's base unit. `-` is the dimensionless unit.
_EXTRA_UNITS: dict[str, dict[str, tuple[float, float]]] = {
    "time": {"min": (60.0, 0.0), "h": (3600.0, 0.0), "day": (86400.0, 0.0)},
    # `-` is "no unit". Its prefixed forms (n-, m-, k-, M-, G-) let data of unknown unit be scaled by prefix alone.
    "strain": {
        "n-": (1e-9, 0.0), "µε": (1e-6, 0.0), "m-": (1e-3, 0.0), "%": (1e-2, 0.0), "-": (1.0, 0.0),
        "k-": (1e3, 0.0), "M-": (1e6, 0.0), "G-": (1e9, 0.0),
    },
    "temperature": {"K": (1.0, 0.0), "°C": (1.0, 273.15)},
}


def _build_families() -> dict[str, dict[str, tuple[float, float]]]:
    """family -> {unit: (scale, offset)}, meaning  base = value * scale + offset  (in the family's base unit)."""
    families: dict[str, dict[str, tuple[float, float]]] = {}
    for base, (family, prefixes) in BASE_UNITS.items():
        members = families.setdefault(family, {})
        for prefix in prefixes:
            members[f"{prefix}{base}"] = (SI_PREFIXES.get(prefix, 1.0), 0.0)
    for family, extras in _EXTRA_UNITS.items():
        families.setdefault(family, {}).update(extras)
    order = ("pressure", "time", "length", "strain", "temperature")
    return {name: families[name] for name in (*order, *(f for f in families if f not in order))}


UNIT_FAMILIES: dict[str, dict[str, tuple[float, float]]] = _build_families()

_UNIT_FAMILY = {unit: family for family, members in UNIT_FAMILIES.items() for unit in members}
# Case-insensitive spellings ("mpa" -> "MPa") only where they are unambiguous: "mN" and "MN" stay distinct.
_LOWER_COUNTS: dict[str, int] = {}
for _unit in _UNIT_FAMILY:
    _LOWER_COUNTS[_unit.lower()] = _LOWER_COUNTS.get(_unit.lower(), 0) + 1
_UNIT_ALIASES = {unit.lower(): unit for unit in _UNIT_FAMILY if _LOWER_COUNTS[unit.lower()] == 1}
# Spelled-out names and other spellings, matched without regard to case ("degC", "Celsius").
_WORD_ALIASES = {
    "mpa": "MPa",  # all-lowercase is meant as megapascal; milli-pascal needs its exact "mPa"
        "sec": "s", "second": "s", "seconds": "s", "secs": "s",
        "minute": "min", "minutes": "min", "mins": "min",
        "hr": "h", "hour": "h", "hours": "h", "hrs": "h",
        "days": "day",
        "percent": "%", "pct": "%", "1": "-",
        "degc": "°C", "celsius": "°C", "deg c": "°C",
        "kelvin": "K",
        "um": "µm", "micron": "µm", "microns": "µm", "micrometer": "µm",
        "ue": "µε", "microstrain": "µε", "με": "µε", "µe": "µε", "ustrain": "µε", "ppm": "µε",
}

# Legacy conversion key -> (target unit, unit assumed for the data when none is known).
_LEGACY_TARGETS = {
    "percent": ("%", "-"),
    "mpa": ("MPa", "Pa"),
    "gpa": ("GPa", "Pa"),
    "sec-to-min": ("min", "s"),
    "sec-to-hour": ("h", "s"),
}
_CONVERSION_ALIASES = {
    "": "as-is", "as is": "as-is", "as-is": "as-is", "raw": "as-is",
    "%": "percent", "percent": "percent", "percentage": "percent",
    "mpa": "mpa", "gpa": "gpa",
    "log": "log10", "log10": "log10", "base 10 log": "log10", "base-10 log": "log10",
    "sec -> min": "sec-to-min", "sec-to-min": "sec-to-min", "seconds to minutes": "sec-to-min",
    "min": "sec-to-min", "minutes": "sec-to-min",
    "sec -> hour": "sec-to-hour", "sec-to-hour": "sec-to-hour", "seconds to hours": "sec-to-hour",
    "hour": "sec-to-hour", "hours": "sec-to-hour",
    "custom": "custom",
}
_DECIMAL_COMMA = re.compile(r"^[+-]?\d+,\d+(?:[eE][+-]?\d+)?$")


def _lookup(unit: str) -> tuple[str, float, float] | None:
    """`(family, scale, offset)` of a unit spelled exactly, or None. Listed units, then prefix + base unit."""
    family = _UNIT_FAMILY.get(unit)
    if family is not None:
        scale, offset = UNIT_FAMILIES[family][unit]
        return family, scale, offset
    for prefix in sorted(SI_PREFIXES, key=len, reverse=True):
        if unit.startswith(prefix) and unit[len(prefix):] in BASE_UNITS:
            return BASE_UNITS[unit[len(prefix):]][0], SI_PREFIXES[prefix], 0.0
    return None


def normalize_unit(text) -> str:
    """Canonical spelling of a unit ("[mpa]" -> "MPa", "uN" -> "µN"); unknown units are returned as typed."""
    if text is None:
        return ""
    value = str(text).strip()
    value = value.strip("[]()").strip()
    if not value:
        return ""
    if _lookup(value) is not None:
        return value
    alias = _WORD_ALIASES.get(value.lower())
    if alias is not None:
        return alias
    # Unit names match without regard to case only for all-lower or all-upper spellings ("mpa", "GPA"):
    # "Nm" is not a nanometre.
    alias = _UNIT_ALIASES.get(value.lower()) if value in (value.lower(), value.upper()) else None
    if alias is not None:
        return alias
    if value.startswith("u") and _lookup("µ" + value[1:]) is not None:
        return "µ" + value[1:]
    return value


def family_of(unit) -> str | None:
    found = _lookup(normalize_unit(unit))
    return found[0] if found else None


def family_units(unit, *, scale_only: bool = False) -> list[str]:
    """Every listed unit of `unit`'s family, sorted small to large (milli ... base ... kilo ... Mega).

    The same list for any member, so "from" and "to" show one scale and the base unit sits in its place.
    A unit with an unlisted prefix ("TPa") is added where it belongs; an unknown unit is just itself.
    `scale_only` leaves temperature alone (it needs an offset), for views that only multiply values.
    """
    source = normalize_unit(unit)
    found = _lookup(source)
    if not source:
        return []
    if found is None:
        return [source]
    family = found[0]
    members = list(UNIT_FAMILIES[family])
    if scale_only and any(offset != 0.0 for _scale, offset in UNIT_FAMILIES[family].values()):
        return [source]
    if source not in members:
        members.append(source)
    return sorted(members, key=lambda name: (_lookup(name)[1], _lookup(name)[2]))


def targets_for(unit) -> list[str]:
    """The other listed units of the same family, small to large (empty for unknown units)."""
    source = normalize_unit(unit)
    if family_of(source) is None:
        return []
    return [name for name in family_units(source) if name != source]


def all_units() -> list[str]:
    return list(_UNIT_FAMILY)


def affine(source, target) -> tuple[float, float] | None:
    """`(a, b)` with `target_value = a * source_value + b`, or None when the units are unknown or unrelated."""
    src, tgt = _lookup(normalize_unit(source)), _lookup(normalize_unit(target))
    if src is None or tgt is None or src[0] != tgt[0]:
        return None
    _, s_scale, s_offset = src
    _, t_scale, t_offset = tgt
    return s_scale / t_scale, (s_offset - t_offset) / t_scale


_PREFIX_NAMES = {
    "p": "pico", "n": "nano", "µ": "micro", "m": "milli", "c": "centi", "d": "deci",
    "k": "kilo", "M": "Mega", "G": "Giga", "T": "Tera",
}
_SCALE_LABELS = {
    "min": "minute (min)", "h": "hour (h)", "day": "day", "%": "percent (%)", "µε": "micro (µ)",
    "K": "Kelvin (K)", "°C": "Celsius (°C)",
    "n-": "nano (n)", "m-": "milli (m)", "k-": "kilo (k)", "M-": "Mega (M)", "G-": "Giga (G)",
}
_NO_UNIT_SCALES = ("-", "n-", "m-", "k-", "M-", "G-")  # a scale of data that has no unit: nothing to print


# What data of unknown unit can be declared as ("this column is in Pa"). Prefixes are chosen separately.
DECLARABLE_UNITS = ("s", "K", "°C")  # time and temperature; Pa, N, J, W, m and g come with the data


def declarable_units(*, scale_only: bool = False) -> list[str]:
    """Base units a user may declare for data that has none. `scale_only` drops temperature (needs an offset)."""
    allowed = set(scale_units()) if scale_only else None
    return [unit for unit in DECLARABLE_UNITS if allowed is None or unit in allowed]


def raw_unit(unit, scale) -> str:
    """The unit stored values are in, when they are multiplied by `scale` to be shown in `unit`.

    A dataset that says `units: MPa, scale: 1e-6` stores Pa. Without a (matching) scale the stated unit is
    returned, and "" when there is no unit at all.
    """
    shown = normalize_unit(unit)
    if not shown:
        return ""
    factor = float(scale) if scale else 1.0
    for candidate in family_units(shown):
        ratio = scale_between(candidate, shown)  # shown = candidate * ratio
        if ratio is not None and math.isclose(ratio, factor, rel_tol=1e-9):
            return candidate
    return shown


def display_unit(unit) -> str:
    """The unit to print in a title or label: "" for data with no unit (including its prefixed scales)."""
    name = normalize_unit(unit)
    return "" if name in _NO_UNIT_SCALES else name


def scale_label(unit) -> str:
    """How a unit is named in a From/To dropdown: its prefix ("kilo (k)"), or "base" for the base unit itself.

    The base unit's name (Pa, m, N, ...) is not shown: the data already says which it is.
    """
    name = normalize_unit(unit)
    if name in _SCALE_LABELS:
        return _SCALE_LABELS[name]
    if _lookup(name) is None or name in BASE_UNITS or name == "-":
        return "base"
    for prefix in sorted(SI_PREFIXES, key=len, reverse=True):
        if name.startswith(prefix) and name[len(prefix):] in BASE_UNITS:
            return f"{_PREFIX_NAMES[prefix]} ({prefix})"
    return "base"


def scale_between(source, target) -> float | None:
    """The factor from `source` to `target` when they differ by a pure scale (no offset), else None.

    Heatmap views only multiply values, so they use this instead of `affine` (which also covers K to degC).
    """
    pair = affine(source, target)
    if pair is None or pair[1] != 0.0:
        return None
    return pair[0]


def scale_units() -> list[str]:
    """Every unit that converts by scale alone, in table order (temperature needs an offset and is left out)."""
    return [
        unit
        for members in UNIT_FAMILIES.values()
        if all(offset == 0.0 for _scale, offset in members.values())
        for unit in members
    ]


def scale_targets_for(unit) -> list[str]:
    """The other units `unit` converts to by scale alone (empty for unknown units and for temperature)."""
    source = normalize_unit(unit)
    return [name for name in family_units(source, scale_only=True) if name != source]


def parse_number(value, default: float) -> float:
    """A finite float from a number or text (decimal comma accepted); `default` for blank or invalid input."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = str(value).strip()
        if not text:
            return default
        if _DECIMAL_COMMA.match(text):
            text = text.replace(",", ".")
        try:
            number = float(text)
        except ValueError:
            return default
    return number if math.isfinite(number) else default


def normalize_conversion(value) -> str:
    """Canonical conversion key: "as-is", "log10", "custom", "to:<unit>" or a legacy key (see module doc)."""
    text = str(value or "").strip()
    if text.lower().startswith("to:"):
        return "to:" + normalize_unit(text[3:])
    return _CONVERSION_ALIASES.get(text.lower(), "as-is")


@dataclass(frozen=True)
class Transform:
    """What to do to a column before plotting: `a * x + b`, or log10; `unit` names the result."""

    kind: str  # "affine" | "log10" | "formula"
    a: float = 1.0
    b: float = 0.0
    unit: str = ""
    expr: str = ""
    columns: tuple = ()  # names of the columns a formula may refer to

    def apply(self, values, columns=None) -> np.ndarray:
        """Convert `values`; `columns` maps column names to data for formulas that use other columns."""
        data = np.asarray(values, dtype=float)
        if self.kind == "formula":
            try:
                result = compile_formula(self.expr, self.columns)(data, columns)
            except ValueError:
                return data  # data a formula needs is not available: leave the column as it is
            return result if result.shape == data.shape else data
        if self.kind == "log10":
            out = np.full(data.shape, np.nan, dtype=float)
            positive = data > 0
            out[positive] = np.log10(data[positive])
            return out
        out = data * self.a
        return out + self.b if self.b else out


def resolve_transform(
    conversion,
    *,
    source_unit="",
    factor=None,
    offset=None,
    custom_unit="",
    formula="",
    column_names=(),
) -> Transform:
    """Resolve one column's (or the X axis') conversion settings into a Transform."""
    key = normalize_conversion(conversion)
    source = normalize_unit(source_unit)
    if key == "as-is":
        return Transform("affine", 1.0, 0.0, source)
    if key == "log10":
        return Transform("log10", unit="log10")
    if key == "custom":
        expression = str(formula or "").strip()
        if expression:
            names = tuple(column_names)
            try:
                compile_formula(expression, names)
            except ValueError:
                return Transform("affine", 1.0, 0.0, normalize_unit(custom_unit))  # invalid: leave data as-is
            return Transform("formula", unit=normalize_unit(custom_unit), expr=expression, columns=names)
        return Transform(
            "affine", parse_number(factor, 1.0), parse_number(offset, 0.0), normalize_unit(custom_unit)
        )
    if key.startswith("to:"):
        target = key[3:]
        pair = affine(source, target)
        if pair is None:
            return Transform("affine", 1.0, 0.0, source)  # no usable source unit: nothing to convert from
        return Transform("affine", pair[0], pair[1], target)
    target, assumed = _LEGACY_TARGETS[key]
    # A known source of the target's own family wins; otherwise the legacy assumption (Pa / fraction / s).
    effective = source if family_of(source) == family_of(target) and source else assumed
    a, b = affine(effective, target) or (1.0, 0.0)
    return Transform("affine", a, b, target)
