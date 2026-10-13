"""Visible-region maths for Auto Scale on Zoom (Qt-free, so it can be unit tested without a GUI).

A zoom window is `(x0, x1, y0, y1)` in the heatmap's plot-axis coordinates (what Plotly reports
for its axis ranges). Grids are `z[row, col]` over ascending axes, as drawn by the heatmap.
"""

from __future__ import annotations

import math

import numpy as np

ZoomWindow = tuple[float, float, float, float]

# A window within this fraction of a cell of the full extent counts as "not zoomed".
_FULL_DOMAIN_CELL_TOLERANCE = 0.75
# Relative size below which a range counts as constant and is padded so colour scales stay valid.
_CONSTANT_RANGE_RELATIVE = 1e-12


def normalize_window(x0, x1, y0, y1) -> ZoomWindow | None:
    """Return an ordered, finite window, or None when any bound is missing or not finite."""
    try:
        values = [float(v) for v in (x0, x1, y0, y1)]
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(v) for v in values):
        return None
    ax0, ax1 = sorted(values[:2])
    ay0, ay1 = sorted(values[2:])
    return ax0, ax1, ay0, ay1


def windows_equal(a: ZoomWindow | None, b: ZoomWindow | None, *, rel_tol: float = 1e-9) -> bool:
    """True when both windows are None or all four bounds agree (scale-aware tolerance)."""
    if a is None or b is None:
        return a is b
    scale = max(1.0, *(abs(v) for v in (*a, *b)))
    return all(abs(p - q) <= rel_tol * scale for p, q in zip(a, b))


def _ascending(axis, values=None, *, along: int):
    """Return the axis ascending, flipping `values` (a 2D grid) along `along` when it was descending."""
    axis = np.asarray(axis, dtype=float)
    if axis.size > 1 and axis[0] > axis[-1]:
        axis = axis[::-1]
        if values is not None:
            values = np.flip(values, axis=along)
    return axis, values


def _cell_edges(centres: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Lower and upper cell edges from cell centres; works for non-uniform spacing."""
    if centres.size == 1:
        return centres - 0.5, centres + 0.5
    midpoints = (centres[:-1] + centres[1:]) / 2.0
    lower = np.concatenate(([centres[0] - (centres[1] - centres[0]) / 2.0], midpoints))
    upper = np.concatenate((midpoints, [centres[-1] + (centres[-1] - centres[-2]) / 2.0]))
    return lower, upper


def _overlapping_slice(centres: np.ndarray, lo: float, hi: float) -> slice:
    """Index range of the cells overlapping [lo, hi]; the nearest cell when the window misses all."""
    lower, upper = _cell_edges(centres)
    hits = np.flatnonzero((upper >= lo) & (lower <= hi))
    if hits.size == 0:
        nearest = int(np.argmin(np.abs(centres - (lo + hi) / 2.0)))
        return slice(nearest, nearest + 1)
    return slice(int(hits[0]), int(hits[-1]) + 1)


def window_indices(x_axis, y_axis, window: ZoomWindow) -> tuple[slice, slice]:
    """(row slice, column slice) of the cells overlapping `window` on ascending axes."""
    x_axis = np.asarray(x_axis, dtype=float)
    y_axis = np.asarray(y_axis, dtype=float)
    return _overlapping_slice(y_axis, window[2], window[3]), _overlapping_slice(x_axis, window[0], window[1])


def is_full_domain(window: ZoomWindow, x_axis, y_axis) -> bool:
    """True when `window` shows (almost) the whole domain, i.e. the view is not zoomed."""
    x_axis, _ = _ascending(x_axis, along=1)
    y_axis, _ = _ascending(y_axis, along=0)
    for axis, lo, hi in ((x_axis, window[0], window[1]), (y_axis, window[2], window[3])):
        if axis.size < 2:
            continue
        tolerance = _FULL_DOMAIN_CELL_TOLERANCE * float(np.max(np.diff(axis)))
        if lo > axis[0] + tolerance or hi < axis[-1] - tolerance:
            return False
    return True


def overlaps_domain(window: ZoomWindow, x_axis, y_axis) -> bool:
    """True when `window` intersects the data domain at all."""
    x_axis, _ = _ascending(x_axis, along=1)
    y_axis, _ = _ascending(y_axis, along=0)
    if x_axis.size == 0 or y_axis.size == 0:
        return False
    return not (
        window[1] < x_axis[0] or window[0] > x_axis[-1] or window[3] < y_axis[0] or window[2] > y_axis[-1]
    )


def visible_min_max(x_axis, y_axis, z_grid, window: ZoomWindow) -> tuple[float, float] | None:
    """Finite min and max of the cells overlapping `window`; None when none of them is finite.

    A window smaller than one cell still selects that cell, so a very deep zoom keeps a valid range.
    """
    z = np.asarray(z_grid, dtype=float)
    if z.ndim != 2 or z.size == 0:
        return None
    x_axis, z = _ascending(x_axis, z, along=1)
    y_axis, z = _ascending(y_axis, z, along=0)
    if x_axis.size != z.shape[1] or y_axis.size != z.shape[0]:
        return None
    rows, cols = window_indices(x_axis, y_axis, window)
    finite = z[rows, cols][np.isfinite(z[rows, cols])]
    if finite.size == 0:
        return None
    return float(finite.min()), float(finite.max())


def padded_range(lo: float, hi: float) -> tuple[float, float] | None:
    """A strictly increasing (lo, hi); a constant field is widened symmetrically. None if not finite."""
    if not (math.isfinite(lo) and math.isfinite(hi)):
        return None
    lo, hi = (lo, hi) if lo <= hi else (hi, lo)
    if hi - lo > _CONSTANT_RANGE_RELATIVE * max(1.0, abs(lo), abs(hi)):
        return lo, hi
    pad = abs(lo) * 1e-3 or 1e-6
    return lo - pad, hi + pad
