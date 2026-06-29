"""VTK reader and slice interpolation helpers."""

from time import perf_counter

import numpy as np

from app.debug import debug_print
from config.constants import DEFAULTS


class VTKReader:
    """Read VTK files through PyVista and provide interpolated slices."""

    def __init__(self, file_path: str):
        debug_print("VTKReader.__init__ start")
        self.file_path = file_path
        self.mesh = None
        self.scalar_name = None
        self.dimensions = None
        self.is_3d = False
        self._interpolation_cache = {}
        self.load_file()
        debug_print("VTKReader.__init__ complete")

    def load_file(self) -> None:
        debug_print("VTKReader.load_file called")
        start = perf_counter()
        import pyvista as pv

        self.mesh = pv.read(self.file_path)
        debug_print(f"VTKReader loaded file={self.file_path} seconds={perf_counter() - start:.3f}")
        if self.mesh.n_arrays <= 0:
            raise ValueError(f"No scalar arrays found in {self.file_path}")
        self.scalar_name = self.mesh.array_names[0]
        self.dimensions = getattr(self.mesh, "dimensions", None)
        if not self.dimensions:
            bounds = self.mesh.bounds
            self.dimensions = (
                int(bounds[1] - bounds[0] + 1),
                int(bounds[3] - bounds[2] + 1),
                int(bounds[5] - bounds[4] + 1),
            )
        self.is_3d = all(value > 1 for value in self.dimensions)
        debug_print(f"VTKReader dimensions={self.dimensions}")
        debug_print(f"VTKReader is_3d={self.is_3d}")

    def get_slice(self, axis: str = "y", index: int | None = None, scalar_name: str | None = None, component: int | None = None):
        debug_print("VTKReader.get_slice called")
        scalar_name = scalar_name or self.scalar_name
        if not self.is_3d:
            debug_print("VTKReader using _extract_2d_data")
            return self._extract_2d_data(scalar_name, component)
        axis_map = {"x": 0, "y": 1, "z": 2}
        axis_index = axis_map[axis.lower()]
        if index is None:
            index = self.dimensions[axis_index] // 2
        index = max(0, min(index, self.dimensions[axis_index] - 1))
        bounds = self.mesh.bounds
        x_mid = (bounds[0] + bounds[1]) * 0.5
        y_mid = (bounds[2] + bounds[3]) * 0.5
        z_mid = (bounds[4] + bounds[5]) * 0.5
        if axis.lower() == "x":
            x_val = bounds[0] + (bounds[1] - bounds[0]) * index / max(1, self.dimensions[0] - 1)
            slice_mesh = self.mesh.slice(normal="x", origin=(x_val, y_mid, z_mid))
        elif axis.lower() == "y":
            y_val = bounds[2] + (bounds[3] - bounds[2]) * index / max(1, self.dimensions[1] - 1)
            slice_mesh = self.mesh.slice(normal="y", origin=(x_mid, y_val, z_mid))
        else:
            z_val = bounds[4] + (bounds[5] - bounds[4]) * index / max(1, self.dimensions[2] - 1)
            slice_mesh = self.mesh.slice(normal="z", origin=(x_mid, y_mid, z_val))
        debug_print(f"VTKReader created slice axis={axis} index={index}")
        return self._process_slice(slice_mesh, axis, scalar_name, component)

    def get_interpolated_slice(self, axis: str = "y", index: int | None = None, scalar_name: str | None = None, component: int | None = None, resolution: int | None = 160):
        debug_print("VTKReader.get_interpolated_slice called")
        scalar_name = scalar_name or self.scalar_name
        resolution_key = "native" if resolution is None else int(resolution)
        cache_key = (scalar_name, component, axis.lower(), -1 if index is None else index, resolution_key)
        if cache_key in self._interpolation_cache:
            debug_print("VTKReader cache hit")
            return self._interpolation_cache[cache_key]
        if not self.is_3d and self._can_use_structured_2d_grid():
            debug_print("VTKReader using structured 2D grid fast path")
            result = self._structured_2d_grid(scalar_name, component, resolution)
        else:
            if resolution is None:
                resolution = DEFAULTS["native_fallback_resolution"]
                debug_print(f"VTKReader native requested for unstructured path; fallback resolution={resolution}")
            x_coords, y_coords, scalars, stats = self.get_slice(axis=axis, index=index, scalar_name=scalar_name, component=component)
            x_grid, y_grid, z_grid = self.interpolate_to_grid(x_coords, y_coords, scalars, resolution)
            result = (x_grid, y_grid, z_grid, stats)
        self._interpolation_cache[cache_key] = result
        debug_print("VTKReader cached interpolated slice")
        return result

    def interpolate_to_grid(self, x_coords, y_coords, scalars, resolution: int = 160):
        debug_print("VTKReader.interpolate_to_grid called")
        start = perf_counter()
        from scipy.interpolate import griddata

        xi = np.linspace(np.min(x_coords), np.max(x_coords), resolution)
        yi = np.linspace(np.min(y_coords), np.max(y_coords), resolution)
        x_grid, y_grid = np.meshgrid(xi, yi)
        z_grid = griddata((x_coords, y_coords), scalars, (x_grid, y_grid), method="linear", fill_value=np.nan)
        debug_print(f"VTKReader grid shape={z_grid.shape} seconds={perf_counter() - start:.3f}")
        return x_grid, y_grid, z_grid

    def _can_use_structured_2d_grid(self) -> bool:
        debug_print("VTKReader._can_use_structured_2d_grid called")
        if not self.dimensions or len(self.dimensions) != 3:
            return False
        if sum(1 for value in self.dimensions if value > 1) != 2:
            return False
        return int(np.prod(self.dimensions)) == len(self.mesh.points)

    def _structured_2d_grid(self, scalar_name: str, component: int | None, resolution: int | None):
        debug_print("VTKReader._structured_2d_grid called")
        start = perf_counter()
        scalars = self._select_component(self.mesh[scalar_name], component)
        nx, ny, nz = (int(value) for value in self.dimensions)
        if scalars.size != nx * ny * nz:
            debug_print("VTKReader structured fast path size mismatch; falling back to interpolation")
            if resolution is None:
                resolution = DEFAULTS["native_fallback_resolution"]
                debug_print(f"VTKReader structured mismatch native fallback resolution={resolution}")
            x_coords, y_coords, scalars, stats = self._extract_2d_data(scalar_name, component)
            x_grid, y_grid, z_grid = self.interpolate_to_grid(x_coords, y_coords, scalars, resolution)
            return x_grid, y_grid, z_grid, stats

        data3 = np.asarray(scalars).reshape((nz, ny, nx))
        active_axes = [axis for axis, dim in enumerate((nx, ny, nz)) if dim > 1]
        inactive_axis = next(axis for axis, dim in enumerate((nx, ny, nz)) if dim <= 1)
        if inactive_axis == 0:
            z_grid = data3[:, :, 0]
        elif inactive_axis == 1:
            z_grid = data3[:, 0, :]
        else:
            z_grid = data3[0, :, :]

        bounds = self.mesh.bounds
        axis_values = {
            0: np.linspace(bounds[0], bounds[1], nx),
            1: np.linspace(bounds[2], bounds[3], ny),
            2: np.linspace(bounds[4], bounds[5], nz),
        }
        x_values = axis_values[active_axes[0]]
        y_values = axis_values[active_axes[1]]
        z_grid, x_values, y_values = self._resample_grid(z_grid, x_values, y_values, resolution)
        x_grid, y_grid = np.meshgrid(x_values, y_values)
        stats = {
            "min": float(np.nanmin(scalars)),
            "max": float(np.nanmax(scalars)),
            "mean": float(np.nanmean(scalars)),
            "std": float(np.nanstd(scalars)),
        }
        debug_print(f"VTKReader structured grid shape={z_grid.shape} seconds={perf_counter() - start:.3f}")
        return x_grid, y_grid, z_grid, stats

    def _resample_grid(self, z_grid, x_values, y_values, resolution: int | None):
        debug_print("VTKReader._resample_grid called")
        if resolution is None or resolution <= 0:
            debug_print("VTKReader native resolution selected")
            return z_grid, x_values, y_values
        row_count, col_count = z_grid.shape
        target_rows = int(resolution)
        target_cols = int(resolution)
        if target_rows == row_count and target_cols == col_count:
            debug_print("VTKReader resample skipped")
            return z_grid, x_values, y_values
        source_cols = np.arange(col_count)
        source_rows = np.arange(row_count)
        target_col_positions = np.linspace(0, col_count - 1, target_cols)
        target_row_positions = np.linspace(0, row_count - 1, target_rows)
        resampled_cols = np.empty((row_count, target_cols), dtype=float)
        for row_index in range(row_count):
            resampled_cols[row_index] = np.interp(
                target_col_positions,
                source_cols,
                z_grid[row_index],
            )
        resampled = np.empty((target_rows, target_cols), dtype=float)
        for col_index in range(target_cols):
            resampled[:, col_index] = np.interp(
                target_row_positions,
                source_rows,
                resampled_cols[:, col_index],
            )
        x_resampled = np.interp(target_col_positions, source_cols, x_values)
        y_resampled = np.interp(target_row_positions, source_rows, y_values)
        debug_print(f"VTKReader resample rows={row_count}->{target_rows} cols={col_count}->{target_cols}")
        return resampled, x_resampled, y_resampled

    def _extract_2d_data(self, scalar_name: str, component: int | None):
        debug_print("VTKReader._extract_2d_data called")
        points = self.mesh.points
        scalars = self._select_component(self.mesh[scalar_name], component)
        std_devs = np.std(points, axis=0)
        active_axes = np.where(std_devs > 1e-10)[0]
        if len(active_axes) < 2:
            active_axes = [0, 1]
        x_coords = points[:, active_axes[0]]
        y_coords = points[:, active_axes[1]]
        stats = {
            "min": float(np.nanmin(scalars)),
            "max": float(np.nanmax(scalars)),
            "mean": float(np.nanmean(scalars)),
            "std": float(np.nanstd(scalars)),
        }
        return x_coords, y_coords, scalars, stats

    def _process_slice(self, slice_mesh, axis: str, scalar_name: str, component: int | None):
        debug_print("VTKReader._process_slice called")
        points = slice_mesh.points
        scalars = self._select_component(slice_mesh[scalar_name], component)
        if axis.lower() == "x":
            x_coords = points[:, 1]
            y_coords = points[:, 2]
        elif axis.lower() == "y":
            x_coords = points[:, 0]
            y_coords = points[:, 2]
        else:
            x_coords = points[:, 0]
            y_coords = points[:, 1]
        stats = {
            "min": float(np.nanmin(scalars)),
            "max": float(np.nanmax(scalars)),
            "mean": float(np.nanmean(scalars)),
            "std": float(np.nanstd(scalars)),
        }
        return x_coords, y_coords, scalars, stats

    def get_max_slice_index(self, axis: str = "y") -> int:
        debug_print("VTKReader.get_max_slice_index called")
        axis_map = {"x": 0, "y": 1, "z": 2}
        return max(0, self.dimensions[axis_map[axis.lower()]] - 1)

    @property
    def scalar_fields(self):
        debug_print("VTKReader.scalar_fields called")
        return list(self.mesh.array_names)

    def _select_component(self, scalars, component: int | None):
        debug_print("VTKReader._select_component called")
        if getattr(scalars, "ndim", 1) == 1:
            return scalars
        if getattr(scalars, "ndim", 1) == 2:
            if component is not None and 0 <= component < scalars.shape[1]:
                return scalars[:, component]
            return np.linalg.norm(scalars, axis=1)
        return scalars
