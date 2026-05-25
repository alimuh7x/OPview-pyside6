"""Shared 2D heatmap orientation helpers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


_COLLAPSED_AXIS_THRESHOLD = 5
_VALID_ROTATIONS = {0, 90, 180, 270}


@dataclass(frozen=True)
class OrientedHeatmapGrid:
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray


class Heatmap2DOrientation:
    """Apply consistent plane detection and display rotation for 2D heatmaps."""

    def __init__(self, rotation_degrees: int = 0) -> None:
        rotation = int(rotation_degrees) % 360
        if rotation not in _VALID_ROTATIONS:
            raise ValueError(f"Unsupported heatmap rotation: {rotation_degrees}")
        self.rotation_degrees = rotation

    @staticmethod
    def detect_axis(dimensions, threshold: int = _COLLAPSED_AXIS_THRESHOLD) -> str:
        dx, dy, dz = dimensions
        if dz <= threshold:
            return "z"
        if dy <= threshold:
            return "y"
        if dx <= threshold:
            return "x"
        return "y"

    @staticmethod
    def is_2d(dimensions, threshold: int = _COLLAPSED_AXIS_THRESHOLD) -> bool:
        return any(value <= threshold for value in dimensions)

    def apply_grid(self, x_grid, y_grid, z_grid) -> OrientedHeatmapGrid:
        x_arr = np.asarray(x_grid)
        y_arr = np.asarray(y_grid)
        z_arr = np.asarray(z_grid)
        if self.rotation_degrees in {90, 270}:
            x_arr, y_arr = y_arr, x_arr
        return OrientedHeatmapGrid(
            x=self._rotate_array(x_arr),
            y=self._rotate_array(y_arr),
            z=self._rotate_array(z_arr),
        )

    def apply_overlay(self, overlay_grid):
        if overlay_grid is None:
            return None
        oriented = self.apply_grid(
            overlay_grid["x"],
            overlay_grid["y"],
            overlay_grid["z"],
        )
        return {"x": oriented.x, "y": oriented.y, "z": oriented.z}

    def plot_width_for_height(self, x_grid, y_grid, height: int, *, minimum: int = 100, maximum: int = 1200) -> int:
        x_arr = np.asarray(x_grid, dtype=float)
        y_arr = np.asarray(y_grid, dtype=float)
        x_span = float(np.nanmax(x_arr) - np.nanmin(x_arr))
        y_span = float(np.nanmax(y_arr) - np.nanmin(y_arr))
        if y_span <= 0:
            return minimum
        return max(minimum, min(maximum, int(height * x_span / y_span)))

    @staticmethod
    def plot_axes(x_grid, y_grid, z_grid) -> tuple[np.ndarray, np.ndarray]:
        z_arr = np.asarray(z_grid)
        rows, cols = z_arr.shape[:2]
        x_arr = np.asarray(x_grid, dtype=float)
        y_arr = np.asarray(y_grid, dtype=float)
        x_values = np.linspace(float(np.nanmin(x_arr)), float(np.nanmax(x_arr)), cols)
        y_values = np.linspace(float(np.nanmin(y_arr)), float(np.nanmax(y_arr)), rows)
        return x_values, y_values

    @staticmethod
    def nearest_value(x_grid, y_grid, z_grid, x_value: float, y_value: float) -> float:
        z_arr = np.asarray(z_grid, dtype=float)
        valid = ~np.isnan(z_arr)
        if not np.any(valid):
            raise ValueError("No valid z values in grid")
        distance = (np.asarray(x_grid) - float(x_value)) ** 2 + (np.asarray(y_grid) - float(y_value)) ** 2
        distance = np.where(valid, distance, np.inf)
        idx = np.unravel_index(np.argmin(distance), distance.shape)
        return float(z_arr[idx])

    @staticmethod
    def line_overlay(direction: str, x_position: float | None, y_position: float | None):
        if direction == "horizontal":
            if y_position is None:
                return None
            return ("horizontal", y_position)
        if x_position is None:
            return None
        return ("vertical", x_position)

    @staticmethod
    def extract_line_scan(x_grid, y_grid, z_grid, direction: str, position):
        x_arr = np.asarray(x_grid)
        y_arr = np.asarray(y_grid)
        z_arr = np.asarray(z_grid)
        x_values, y_values = Heatmap2DOrientation.plot_axes(x_arr, y_arr, z_arr)
        if direction == "horizontal":
            if position is not None:
                y_idx = int(np.argmin(np.abs(y_values - float(position))))
                title = f"Horizontal Scan at Y={float(position):.2f}"
            else:
                y_idx = z_arr.shape[0] // 2
                title = "Horizontal Scan (click heatmap to set position)"
            return x_values, z_arr[y_idx, :], title, "X Position"

        if position is not None:
            x_idx = int(np.argmin(np.abs(x_values - float(position))))
            title = f"Vertical Scan at X={float(position):.2f}"
        else:
            x_idx = z_arr.shape[1] // 2
            title = "Vertical Scan (click heatmap to set position)"
        return y_values, z_arr[:, x_idx], title, "Y Position"

    def _rotate_array(self, values: np.ndarray) -> np.ndarray:
        turns = self.rotation_degrees // 90
        if turns == 0:
            return values
        return np.rot90(values, k=-turns)
