"""Shared helpers for numbered discrete color legends."""

from __future__ import annotations

from html import escape

import plotly.graph_objects as go

from app.debug import debug_print
from viewer.plot_style import PlotStyle

_LIVE_COLORBAR_GAP = 0.012
_LIVE_TITLE_LABEL_GAP = 0.09


def build_discrete_legend_html(colors: list[str], label: str = "", *, width: int = 220, height: int = 420) -> str:
    """Build standalone HTML for a vertical color-box legend."""
    debug_print("discrete_legend.build_discrete_legend_html called")
    safe_colors = [str(color) for color in colors]
    debug_print(f"discrete_legend html color count={len(safe_colors)}")
    debug_print(f"discrete_legend html label={label}")
    title = escape(label.strip())
    title_html = f"<div class=\"title\">{title}</div>" if title else ""
    rows: list[str] = []
    for index, color in enumerate(safe_colors, start=1):
        debug_print(f"discrete_legend html row index={index} color={color}")
        safe_color = escape(color, quote=True)
        rows.append(
            f"<div class=\"row\"><span class=\"swatch\" style=\"background:{safe_color}\"></span>"
            f"<span class=\"label\">{index}</span></div>"
        )
    body = f"<div class=\"rows\">{''.join(rows)}</div>"
    debug_print(f"discrete_legend html row count={len(rows)}")
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>
html,body{{margin:0;padding:0;overflow:hidden;background:white;width:100%;height:100%;}}
body{{font-family:{PlotStyle.FONT_FAMILY};color:{PlotStyle.TEXT_COLOR};}}
.wrap{{box-sizing:border-box;width:{width}px;height:{height}px;display:flex;align-items:center;justify-content:center;padding:24px 8px;}}
.legend{{display:grid;grid-template-columns:auto auto;gap:8px 28px;align-items:center;justify-content:start;}}
.title{{font-size:22px;font-weight:700;writing-mode:vertical-rl;text-orientation:mixed;transform:rotate(180deg);white-space:nowrap;grid-column:2;align-self:center;justify-self:center;}}
.rows{{grid-column:1;display:grid;gap:8px;}}
.row{{display:grid;grid-template-columns:36px auto;gap:10px;align-items:center;font-size:22px;line-height:1;}}
.swatch{{display:block;width:30px;height:26px;border:1px solid #4a4a4a;box-sizing:border-box;}}
.label{{font-variant-numeric:tabular-nums;}}
</style></head>
<body><div class="wrap"><div class="legend">{body}{title_html}</div></div></body></html>"""
    debug_print("discrete_legend html built")
    return html


def add_discrete_legend_to_figure(figure: go.Figure, colors: list[str], label: str = "") -> None:
    """Draw a vertical numbered legend in Plotly paper coordinates."""
    debug_print("discrete_legend.add_discrete_legend_to_figure called")
    safe_colors = [str(color) for color in colors]
    debug_print(f"discrete_legend figure color count={len(safe_colors)}")
    debug_print(f"discrete_legend figure label={label}")
    if not safe_colors:
        debug_print("discrete_legend skipped empty colors")
        return
    count = len(safe_colors)
    total_height = min(0.72, max(0.16, count * 0.075))
    row_height = total_height / count
    y_top = 0.78
    swatch_x0 = 1.0 + _LIVE_COLORBAR_GAP
    swatch_x1 = swatch_x0 + 0.045
    label_x = swatch_x1 + 0.018
    title_x = label_x + _LIVE_TITLE_LABEL_GAP
    debug_print(f"discrete_legend figure label_x={label_x}")
    debug_print(f"discrete_legend figure title_label_gap={_LIVE_TITLE_LABEL_GAP}")
    title_y = y_top - (((count - 1) / 2) + 0.36) * row_height
    debug_print(f"discrete_legend figure title_x={title_x}")
    debug_print(f"discrete_legend figure title_y={title_y}")
    title = label.strip()
    if title:
        figure.add_annotation(
            name="Discrete Colorbar Title",
            xref="paper",
            yref="paper",
            x=title_x,
            y=title_y,
            xanchor="center",
            yanchor="middle",
            text=title,
            showarrow=False,
            textangle=90,
            font=PlotStyle.colorbar_title_font(),
        )
        debug_print("discrete_legend figure title added")
    for index, color in enumerate(safe_colors, start=1):
        y1 = y_top - ((index - 1) * row_height)
        y0 = y1 - (row_height * 0.72)
        debug_print(f"discrete_legend figure row index={index} y0={y0} y1={y1} color={color}")
        figure.add_shape(
            type="rect",
            xref="paper",
            yref="paper",
            x0=swatch_x0,
            x1=swatch_x1,
            y0=y0,
            y1=y1,
            fillcolor=color,
            line=dict(color="#4a4a4a", width=1),
        )
        figure.add_annotation(
            name="Discrete Colorbar Label",
            xref="paper",
            yref="paper",
            x=label_x,
            y=(y0 + y1) / 2,
            xanchor="left",
            yanchor="middle",
            text=str(index),
            showarrow=False,
            font=PlotStyle.colorbar_tick_font(),
        )
    debug_print("discrete_legend figure legend added")
