"""High-resolution PNG renderer for Multi Property View."""

from __future__ import annotations

from pathlib import Path

import matplotlib.image as mpimg
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.figure import Figure

from app.debug import debug_print
from viewer.colorbar_ticks import format_colorbar_ticks
from viewer.heatmap_orientation import Heatmap2DOrientation
from viewer.plot_style import PlotStyle

_HEATMAP_TARGET_PX = 1000
_COLORBAR_HEIGHT_PX = 220
_LOGO_BAND_WIDTH_PX = 125
_CELL_GAP_PX = 20
_ROW_GAP_PX = 20
# Colorbar text is sized in sheet pixels (converted to points per dpi), so it always fits the
# fixed-pixel colorbar zone. In points, 13-14 pt at 300 dpi is 54-58 px and overflowed the zone.
_TICK_FONT_PX = 46
_TITLE_FONT_PX = 52
_LABEL_PAD_PX = 12
_TICK_PAD_PX = 10
_BAR_THICKNESS_PX = 44
# Colorbar offset from the near edge of its zone (px): the top row's bar sits above its heatmap
# with ticks between bar and heatmap and the title above; the bottom row is the mirror image.
_BAR_OFFSET_TOP_ROW_PX = 70
_BAR_OFFSET_BOTTOM_ROW_PX = 80
# Colorbar spans this fraction of the cell, centred, so end tick labels (up to ~9 characters,
# e.g. "-1.23e-10") stay inside the cell instead of colliding with the neighbouring cell's labels.
_COLORBAR_SPAN = 0.72
# Narrowest cell: keeps a tall domain's title and colorbar labels from being squeezed.
_MIN_CELL_WIDTH_PX = 700


def _px_to_pt(pixels: float, dpi: int) -> float:
    return float(pixels) * 72.0 / float(dpi)


def save_multi_property_png(
    path: str,
    *,
    rows: list[list[dict]],
    logo_path: Path | None,
    dpi: int,
) -> bool:
    """Render export payload rows into one resolution-independent PNG sheet."""
    debug_print("MultiPropertyExport.save_multi_property_png called")
    debug_print(f"MultiPropertyExport output path={path}")
    debug_print(f"MultiPropertyExport row count={len(rows)}")
    if not rows or not any(rows):
        debug_print("MultiPropertyExport skipped empty rows")
        return False

    safe_dpi = max(72, int(dpi))
    row_layouts = [_row_layout(row) for row in rows]
    sheet_width = max(layout["width"] for layout in row_layouts)
    sheet_height = sum(layout["height"] for layout in row_layouts) + _ROW_GAP_PX * max(0, len(rows) - 1)
    debug_print(f"MultiPropertyExport dpi={safe_dpi}")
    debug_print(f"MultiPropertyExport image pixels={sheet_width}x{sheet_height}")

    figure = Figure(figsize=(sheet_width / safe_dpi, sheet_height / safe_dpi), dpi=safe_dpi)
    figure.patch.set_facecolor("white")
    FigureCanvasAgg(figure)
    row_top = sheet_height
    for row_index, (payloads, layout) in enumerate(zip(rows, row_layouts)):
        row_top -= layout["height"]
        debug_print(f"MultiPropertyExport drawing row={row_index}")
        debug_print(f"MultiPropertyExport row bottom={row_top}")
        _draw_logo(
            figure,
            logo_path,
            sheet_width,
            sheet_height,
            row_top,
            layout["height"],
            bottom_row=row_index > 0,
        )
        cell_x = _LOGO_BAND_WIDTH_PX + _CELL_GAP_PX
        for cell_index, (payload, cell_layout) in enumerate(zip(payloads, layout["cells"])):
            debug_print(f"MultiPropertyExport drawing row={row_index} cell={cell_index}")
            debug_print(f"MultiPropertyExport cell label={payload.get('label', '')}")
            _draw_cell(
                figure,
                payload,
                sheet_width=sheet_width,
                sheet_height=sheet_height,
                left=cell_x,
                bottom=row_top,
                width=cell_layout["width"],
                heatmap_width=cell_layout["heatmap_width"],
                heatmap_height=cell_layout["heatmap_height"],
                bottom_row=row_index > 0,
                dpi=safe_dpi,
            )
            cell_x += cell_layout["width"] + _CELL_GAP_PX
        if row_index < len(rows) - 1:
            row_top -= _ROW_GAP_PX

    figure.savefig(path, dpi=safe_dpi, facecolor="white")
    debug_print("MultiPropertyExport PNG saved")
    return True


def _heatmap_size_px(payload: dict) -> tuple[int, int]:
    """Heatmap pixel size from the physical x/y extent, longest side `_HEATMAP_TARGET_PX`.

    The sampled grid is always square (resolution x resolution), so its shape says nothing about
    the domain's aspect ratio; sizing from it letterboxed non-square domains inside a square cell.
    """
    z_grid = np.asarray(payload["z_grid"], dtype=float)
    x_values, y_values = Heatmap2DOrientation.plot_axes(payload["x_grid"], payload["y_grid"], z_grid)
    x_span = float(np.nanmax(x_values) - np.nanmin(x_values))
    y_span = float(np.nanmax(y_values) - np.nanmin(y_values))
    if not (np.isfinite(x_span) and np.isfinite(y_span)) or x_span <= 0.0 or y_span <= 0.0:
        return _HEATMAP_TARGET_PX, _HEATMAP_TARGET_PX
    aspect = x_span / y_span
    if aspect >= 1.0:
        return _HEATMAP_TARGET_PX, max(1, int(round(_HEATMAP_TARGET_PX / aspect)))
    return max(1, int(round(_HEATMAP_TARGET_PX * aspect))), _HEATMAP_TARGET_PX


def _row_layout(payloads: list[dict]) -> dict:
    debug_print("MultiPropertyExport._row_layout called")
    cells = []
    for payload in payloads:
        heatmap_width, heatmap_height = _heatmap_size_px(payload)
        cell_width = max(heatmap_width, _MIN_CELL_WIDTH_PX)
        cells.append({"width": cell_width, "heatmap_width": heatmap_width, "heatmap_height": heatmap_height})
        debug_print(f"MultiPropertyExport heatmap pixels={heatmap_width}x{heatmap_height}")
        debug_print(f"MultiPropertyExport cell pixels={cell_width}x{heatmap_height}")
    row_width = _LOGO_BAND_WIDTH_PX + _CELL_GAP_PX
    row_width += sum(cell["width"] for cell in cells)
    row_width += _CELL_GAP_PX * max(0, len(cells) - 1)
    row_height = max(cell["heatmap_height"] for cell in cells) + _COLORBAR_HEIGHT_PX
    debug_print(f"MultiPropertyExport row pixels={row_width}x{row_height}")
    return {"cells": cells, "width": row_width, "height": row_height}


def _draw_logo(
    figure,
    logo_path,
    sheet_width: int,
    sheet_height: int,
    row_bottom: int,
    row_height: int,
    *,
    bottom_row: bool,
) -> None:
    debug_print("MultiPropertyExport._draw_logo called")
    if logo_path is None or not logo_path.exists():
        debug_print("MultiPropertyExport logo skipped")
        return
    logo_size = min(110, _LOGO_BAND_WIDTH_PX - 12)
    logo_left = max(0, (_LOGO_BAND_WIDTH_PX - logo_size) // 2)
    heatmap_bottom = row_bottom + (_COLORBAR_HEIGHT_PX if bottom_row else 0)
    logo_bottom = heatmap_bottom + 12
    debug_print(f"MultiPropertyExport logo heatmap bottom={heatmap_bottom}")
    debug_print(f"MultiPropertyExport logo pixels={logo_size}x{logo_size}")
    logo_ax = figure.add_axes([
        logo_left / sheet_width,
        logo_bottom / sheet_height,
        logo_size / sheet_width,
        logo_size / sheet_height,
    ])
    logo_ax.set_axis_off()
    try:
        logo_ax.imshow(mpimg.imread(str(logo_path)))
        debug_print("MultiPropertyExport logo loaded")
    except Exception as exc:
        debug_print(f"MultiPropertyExport logo load failed={exc}")


def _draw_cell(
    figure,
    payload: dict,
    *,
    sheet_width: int,
    sheet_height: int,
    left: int,
    bottom: int,
    width: int,
    heatmap_width: int,
    heatmap_height: int,
    bottom_row: bool,
    dpi: int,
) -> None:
    debug_print("MultiPropertyExport._draw_cell called")
    colorbar_bottom = bottom if bottom_row else bottom + heatmap_height
    heatmap_bottom = bottom + _COLORBAR_HEIGHT_PX if bottom_row else bottom
    debug_print(f"MultiPropertyExport heatmap bottom={heatmap_bottom}")
    debug_print(f"MultiPropertyExport colorbar bottom={colorbar_bottom}")
    heatmap_ax = figure.add_axes([
        (left + (width - heatmap_width) / 2.0) / sheet_width,  # centred in the cell, like the colorbar
        heatmap_bottom / sheet_height,
        heatmap_width / sheet_width,
        heatmap_height / sheet_height,
    ])
    colorbar_offset = _BAR_OFFSET_BOTTOM_ROW_PX if bottom_row else _BAR_OFFSET_TOP_ROW_PX
    debug_print(f"MultiPropertyExport colorbar offset={colorbar_offset}")
    colorbar_ax = figure.add_axes([
        (left + int(width * (1.0 - _COLORBAR_SPAN) / 2.0)) / sheet_width,
        (colorbar_bottom + colorbar_offset) / sheet_height,
        int(width * _COLORBAR_SPAN) / sheet_width,
        _BAR_THICKNESS_PX / sheet_height,
    ])
    mappable = _draw_property(heatmap_ax, payload, dpi)
    colorbar = figure.colorbar(mappable, cax=colorbar_ax, orientation="horizontal")
    ticks = [payload["vmin"], payload["vmin"] + (payload["vmax"] - payload["vmin"]) * 0.5, payload["vmax"]]
    colorbar.set_ticks(ticks)
    colorbar.set_ticklabels(format_colorbar_ticks(ticks))
    colorbar.outline.set_visible(False)
    colorbar.ax.tick_params(labelsize=_px_to_pt(_TICK_FONT_PX, dpi), pad=_px_to_pt(_TICK_PAD_PX, dpi))
    colorbar.set_label(
        str(payload.get("label", "")),
        fontsize=_px_to_pt(_TITLE_FONT_PX, dpi),
        labelpad=_px_to_pt(_LABEL_PAD_PX, dpi),
        weight="bold",
    )
    if bottom_row:
        colorbar.ax.xaxis.set_ticks_position("top")
        colorbar.ax.xaxis.set_label_position("bottom")
    else:
        colorbar.ax.xaxis.set_ticks_position("bottom")
        colorbar.ax.xaxis.set_label_position("top")
    debug_print("MultiPropertyExport colorbar drawn")


def _draw_property(ax, payload: dict, dpi: int):
    debug_print("MultiPropertyExport._draw_property called")
    z_grid = np.asarray(payload["z_grid"], dtype=float)
    x_values, y_values = Heatmap2DOrientation.plot_axes(payload["x_grid"], payload["y_grid"], z_grid)
    extent = [float(np.nanmin(x_values)), float(np.nanmax(x_values)), float(np.nanmin(y_values)), float(np.nanmax(y_values))]
    vmin = float(payload["vmin"])
    vmax = float(payload["vmax"])
    cmap = payload["cmap"]
    plot_type = payload.get("plot_type", "heatmap")
    debug_print(f"MultiPropertyExport plot_type={plot_type}")
    norm = Normalize(vmin=vmin, vmax=vmax)
    mappable = ScalarMappable(norm=norm, cmap=cmap)
    if plot_type == "threshold":
        z_grid = np.where((z_grid >= vmin) & (z_grid <= vmax), z_grid, np.nan)
        ax.imshow(z_grid, origin="lower", extent=extent, cmap=cmap, norm=norm, aspect="equal", interpolation="bilinear")
    elif plot_type == "contour_lines":
        contours = ax.contour(x_values, y_values, z_grid, levels=10, cmap=cmap, norm=norm, linewidths=1.8)
        ax.clabel(contours, inline=True, fontsize=10)
    elif plot_type in {"contour_filled", "contour_filled_values"}:
        ax.contourf(x_values, y_values, z_grid, levels=10, cmap=cmap, norm=norm)
        if plot_type == "contour_filled_values":
            contours = ax.contour(x_values, y_values, z_grid, levels=10, colors="black", linewidths=1.5)
            ax.clabel(contours, inline=True, fontsize=10)
    else:
        ax.imshow(z_grid, origin="lower", extent=extent, cmap=cmap, norm=norm, aspect="equal", interpolation="bilinear")
        if plot_type == "heatmap_contour":
            ax.contour(x_values, y_values, z_grid, levels=10, colors="black", linewidths=1.5)
    overlay_grid = payload.get("overlay_grid")
    if overlay_grid is not None:
        overlay_z = np.asarray(overlay_grid["z"], dtype=float)
        overlay_x, overlay_y = Heatmap2DOrientation.plot_axes(overlay_grid["x"], overlay_grid["y"], overlay_z)
        ax.contourf(
            overlay_x,
            overlay_y,
            overlay_z,
            levels=[1.5, 3.5],
            colors=[PlotStyle.INTERFACE_OVERLAY_COLOR],
            alpha=PlotStyle.INTERFACE_OVERLAY_ALPHA,
        )
        debug_print("MultiPropertyExport interface overlay drawn")
    line_overlay = payload.get("line_overlay")
    if line_overlay:
        direction, value = line_overlay
        guide_points = _px_to_pt(PlotStyle.GUIDE_LINE_WIDTH, dpi)
        if direction == "horizontal":
            ax.axhline(value, color="#c50623", linewidth=guide_points, linestyle="--")
        else:
            ax.axvline(value, color="#c50623", linewidth=guide_points, linestyle="--")
        debug_print(f"MultiPropertyExport line overlay direction={direction}")
    ax.set_axis_off()
    return mappable
