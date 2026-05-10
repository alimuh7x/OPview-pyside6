"""Plot type strategy classes for the heatmap canvas."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
import plotly.graph_objects as go


class PlotTypeRenderer(ABC):
    """Abstract base — each subclass knows how to build its Plotly traces."""

    key:   str  # stored as QComboBox item data
    label: str  # displayed in QComboBox

    @abstractmethod
    def build_traces(
        self,
        x,
        y,
        z,
        zmin: float,
        zmax: float,
        colorscale,
        colorbar_cfg: dict,
        hovertemplate: str,
    ) -> list[go.BaseTraceType]:
        """Return one or more Plotly traces for this plot type."""
        ...


class HeatmapRenderer(PlotTypeRenderer):
    """Plain filled heatmap."""

    key   = "heatmap"
    label = "Heatmap"

    def build_traces(self, x, y, z, zmin, zmax, colorscale, colorbar_cfg, hovertemplate):
        return [go.Heatmap(
            x             = x,
            y             = y,
            z             = np.asarray(z),
            zmin          = zmin,
            zmax          = zmax,
            colorscale    = colorscale,
            colorbar      = colorbar_cfg,
            hovertemplate = hovertemplate,
        )]


class ContourLinesRenderer(PlotTypeRenderer):
    """Isolines only — no fill, labeled contour lines."""

    key   = "contour_lines"
    label = "Contour Lines"

    def build_traces(self, x, y, z, zmin, zmax, colorscale, colorbar_cfg, hovertemplate):
        return [go.Contour(
            x             = x,
            y             = y,
            z             = np.asarray(z),
            zmin          = zmin,
            zmax          = zmax,
            colorscale    = colorscale,
            colorbar      = colorbar_cfg,
            contours      = dict(
                coloring  = "lines",
                showlabels= True,
                labelfont = dict(size=11, color="black"),
            ),
            hovertemplate = hovertemplate,
        )]


class ContourFilledRenderer(PlotTypeRenderer):
    """Discrete colour bands between isolines, with labels."""

    key   = "contour_filled"
    label = "Contour Filled"

    def build_traces(self, x, y, z, zmin, zmax, colorscale, colorbar_cfg, hovertemplate):
        return [go.Contour(
            x             = x,
            y             = y,
            z             = np.asarray(z),
            zmin          = zmin,
            zmax          = zmax,
            colorscale    = colorscale,
            colorbar      = colorbar_cfg,
            contours      = dict(
                coloring  = "fill",
                showlabels= False,
            ),
            hovertemplate = hovertemplate,
        )]


class HeatmapContourRenderer(PlotTypeRenderer):
    """Continuous heatmap fill with black contour lines overlaid."""

    key   = "heatmap_contour"
    label = "Heatmap + Contour"

    def build_traces(self, x, y, z, zmin, zmax, colorscale, colorbar_cfg, hovertemplate):
        return [
            go.Heatmap(
                x             = x,
                y             = y,
                z             = np.asarray(z),
                zmin          = zmin,
                zmax          = zmax,
                colorscale    = colorscale,
                colorbar      = colorbar_cfg,
                hovertemplate = hovertemplate,
            ),
            go.Contour(
                x          = x,
                y          = y,
                z          = np.asarray(z),
                zmin       = zmin,
                zmax       = zmax,
                showscale  = False,
                colorscale = colorscale,
                contours   = dict(coloring="lines"),
                line       = dict(color="black", width=1),
                hoverinfo  = "skip",
            ),
        ]


class ThresholdRenderer(PlotTypeRenderer):
    """Show only values within [zmin, zmax]; everything outside is transparent."""

    key   = "threshold"
    label = "Threshold"

    def build_traces(self, x, y, z, zmin, zmax, colorscale, colorbar_cfg, hovertemplate):
        z_arr    = np.asarray(z, dtype=float)
        z_masked = np.where((z_arr >= zmin) & (z_arr <= zmax), z_arr, np.nan)
        return [go.Heatmap(
            x             = x,
            y             = y,
            z             = z_masked,
            zmin          = zmin,
            zmax          = zmax,
            colorscale    = colorscale,
            colorbar      = colorbar_cfg,
            hovertemplate = hovertemplate,
        )]


class DifferencePlotRenderer(PlotTypeRenderer):
    """Display next − current on a symmetric diverging colorscale.

    The diff grid is computed by the controller before calling build_traces,
    so this renderer is stateless and receives ready-to-display data.
    """

    key   = "difference"
    label = "Difference (next − current)"

    def build_traces(self, x, y, z, zmin, zmax, colorscale, colorbar_cfg, hovertemplate):
        return [go.Heatmap(
            x             = x,
            y             = y,
            z             = np.asarray(z),
            zmin          = zmin,
            zmax          = zmax,
            colorscale    = colorscale,
            colorbar      = colorbar_cfg,
            hovertemplate = hovertemplate,
        )]


# ── Registry ──────────────────────────────────────────────────────────────────

PLOT_TYPE_REGISTRY: list[PlotTypeRenderer] = [
    HeatmapRenderer(),
    ContourLinesRenderer(),
    ContourFilledRenderer(),
    HeatmapContourRenderer(),
    ThresholdRenderer(),
    DifferencePlotRenderer(),
]

PLOT_TYPE_MAP: dict[str, PlotTypeRenderer] = {r.key: r for r in PLOT_TYPE_REGISTRY}
