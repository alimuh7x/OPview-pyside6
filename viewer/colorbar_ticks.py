"""Colorbar tick label formatting shared by heatmap views."""

from __future__ import annotations

import math
from decimal import Decimal, InvalidOperation
from typing import Iterable

from app.debug import debug_print


def format_colorbar_ticks(values: Iterable[float]) -> list[str]:
    """Format colorbar ticks from neighboring tick spacing."""
    debug_print("colorbar_ticks.format_colorbar_ticks called")
    tick_values = [float(value) for value in values]
    debug_print(f"colorbar_ticks values={tick_values}")
    if not tick_values:
        debug_print("colorbar_ticks no values")
        return []
    finite_values = [value for value in tick_values if math.isfinite(value)]
    debug_print(f"colorbar_ticks finite count={len(finite_values)}")
    use_scientific = any(_uses_scientific(value) for value in finite_values)
    debug_print(f"colorbar_ticks use scientific={use_scientific}")
    if use_scientific:
        labels = [_format_scientific(value) for value in tick_values]
        debug_print(f"colorbar_ticks scientific labels={labels}")
        return labels
    if _should_force_integer_labels(finite_values):
        debug_print("colorbar_ticks forcing integer labels")
        labels = [_format_decimal(value, 0) for value in tick_values]
        debug_print(f"colorbar_ticks integer labels={labels}")
        return labels
    decimals = min(_decimal_places_from_spacing(finite_values), 2)
    debug_print(f"colorbar_ticks decimals={decimals}")
    labels = [_format_decimal(value, decimals) for value in tick_values]
    debug_print(f"colorbar_ticks decimal labels={labels}")
    return labels


def format_colorbar_tick(value: float) -> str:
    """Format a single tick using automatic scientific thresholds."""
    debug_print("colorbar_ticks.format_colorbar_tick called")
    debug_print(f"colorbar_ticks single value={value}")
    numeric_value = float(value)
    if _uses_scientific(numeric_value):
        label = _format_scientific(numeric_value)
        debug_print(f"colorbar_ticks single scientific label={label}")
        return label
    decimals = _decimal_places_from_value(numeric_value)
    debug_print(f"colorbar_ticks single decimals={decimals}")
    label = _format_decimal(numeric_value, decimals)
    debug_print(f"colorbar_ticks single label={label}")
    return label


def _uses_scientific(value: float) -> bool:
    debug_print("colorbar_ticks._uses_scientific called")
    debug_print(f"colorbar_ticks scientific value={value}")
    abs_value = abs(float(value))
    result = abs_value >= 1000.0 or (0.0 < abs_value < 0.001)
    debug_print(f"colorbar_ticks scientific result={result}")
    return result


def _format_scientific(value: float) -> str:
    debug_print("colorbar_ticks._format_scientific called")
    debug_print(f"colorbar_ticks scientific format value={value}")
    if not math.isfinite(value):
        label = str(value)
        debug_print(f"colorbar_ticks scientific nonfinite label={label}")
        return label
    if value == 0:
        debug_print("colorbar_ticks scientific zero label=0")
        return "0"
    label = f"{value:.1e}".replace("e+0", "e").replace("e+", "e").replace("e-0", "e-")
    debug_print(f"colorbar_ticks scientific label={label}")
    return label


def _format_decimal(value: float, decimals: int) -> str:
    debug_print("colorbar_ticks._format_decimal called")
    debug_print(f"colorbar_ticks decimal value={value}")
    debug_print(f"colorbar_ticks decimal places={decimals}")
    if not math.isfinite(value):
        label = str(value)
        debug_print(f"colorbar_ticks decimal nonfinite label={label}")
        return label
    label = f"{value:.{decimals}f}"
    debug_print(f"colorbar_ticks decimal label={label}")
    return label


def _decimal_places_from_spacing(values: list[float]) -> int:
    debug_print("colorbar_ticks._decimal_places_from_spacing called")
    if len(values) < 2:
        debug_print("colorbar_ticks spacing single value decimals=0")
        return 0
    sorted_values = sorted(values)
    debug_print(f"colorbar_ticks sorted values={sorted_values}")
    spacings = [
        abs(sorted_values[index + 1] - sorted_values[index])
        for index in range(len(sorted_values) - 1)
        if abs(sorted_values[index + 1] - sorted_values[index]) > 0
    ]
    debug_print(f"colorbar_ticks spacings={spacings}")
    if not spacings:
        debug_print("colorbar_ticks zero spacings decimals=0")
        return 0
    spacing = min(spacings)
    debug_print(f"colorbar_ticks selected spacing={spacing}")
    normalized_spacing = f"{spacing:.12g}"
    debug_print(f"colorbar_ticks normalized spacing={normalized_spacing}")
    try:
        decimal_spacing = Decimal(normalized_spacing).normalize()
    except InvalidOperation:
        debug_print("colorbar_ticks decimal conversion failed decimals=6")
        return 6
    exponent = decimal_spacing.as_tuple().exponent
    decimals = max(0, -int(exponent))
    debug_print(f"colorbar_ticks exponent={exponent}")
    debug_print(f"colorbar_ticks computed decimals={decimals}")
    capped_decimals = min(decimals, 2)
    debug_print(f"colorbar_ticks capped decimals={capped_decimals}")
    return capped_decimals


def _should_force_integer_labels(values: list[float]) -> bool:
    debug_print("colorbar_ticks._should_force_integer_labels called")
    if len(values) < 2:
        debug_print("colorbar_ticks force integer false: not enough values")
        return False
    sorted_values = sorted(values)
    debug_print(f"colorbar_ticks force sorted values={sorted_values}")
    min_value = sorted_values[0]
    max_value = sorted_values[-1]
    is_zero_to_small_range = (
        math.isclose(min_value, 0.0, abs_tol=1e-12)
        and 5.0 <= max_value <= 10.0
    )
    debug_print(f"colorbar_ticks force zero_to_small_range={is_zero_to_small_range}")
    spacings = [
        abs(sorted_values[index + 1] - sorted_values[index])
        for index in range(len(sorted_values) - 1)
        if abs(sorted_values[index + 1] - sorted_values[index]) > 0
    ]
    debug_print(f"colorbar_ticks force spacings={spacings}")
    spacing_greater_than_ten = bool(spacings) and min(spacings) > 10.0
    debug_print(f"colorbar_ticks force spacing_gt_10={spacing_greater_than_ten}")
    result = is_zero_to_small_range or spacing_greater_than_ten
    debug_print(f"colorbar_ticks force result={result}")
    return result


def _decimal_places_from_value(value: float) -> int:
    debug_print("colorbar_ticks._decimal_places_from_value called")
    debug_print(f"colorbar_ticks value decimals input={value}")
    if not math.isfinite(value):
        debug_print("colorbar_ticks value nonfinite decimals=0")
        return 0
    normalized_value = f"{value:.12g}"
    debug_print(f"colorbar_ticks normalized value={normalized_value}")
    try:
        decimal_value = Decimal(normalized_value).normalize()
    except InvalidOperation:
        debug_print("colorbar_ticks value decimal conversion failed decimals=6")
        return 6
    exponent = decimal_value.as_tuple().exponent
    decimals = max(0, -int(exponent))
    debug_print(f"colorbar_ticks value exponent={exponent}")
    debug_print(f"colorbar_ticks value computed decimals={decimals}")
    capped_decimals = min(decimals, 2)
    debug_print(f"colorbar_ticks value capped decimals={capped_decimals}")
    return capped_decimals
