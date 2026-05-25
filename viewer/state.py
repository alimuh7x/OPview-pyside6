"""Viewer state models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass
class ViewerState:
    """Serialisable state for one Single View panel."""

    dataset_id: str
    dataset_label: str
    scalar_key: str
    scalar_label: str
    axis: str
    slice_index: int
    file_path: str
    palette: str = "aqua-fire"
    units: Optional[str] = None
    scale: float = 1.0
    threshold: float = 0.0
    range_min: float = 0.0
    range_max: float = 1.0
    click_count: int = 0
    first_click: Optional[float] = None
    clicked_message: Optional[str] = None
    colorscale_mode: str = "normal"
    line_scan_y: Optional[float] = None
    line_scan_x: Optional[float] = None
    line_scan_direction: str = "horizontal"
    click_mode: str = "range"
    line_overlay_visible: bool = False
    interfaces_overlay_visible: bool = False
    status_message: str = "Waiting for data"
    rotation_degrees: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]], fallback: "ViewerState") -> "ViewerState":
        """Restore state from dict or return fallback."""
        if not data:
            return fallback
        return cls(**{**fallback.to_dict(), **data})


def initial_state(
    dataset_id: str,
    dataset_label: str,
    scalar_key: str,
    scalar_label: str,
    axis: str,
    slice_index: int,
    stats: Dict[str, float],
    file_path: str,
    *,
    scale: float = 1.0,
    units: Optional[str] = None,
    palette: str = "aqua-fire",
) -> ViewerState:
    """Create a ViewerState with defaults derived from dataset statistics."""
    threshold = (stats["min"] + stats["max"]) / 2
    return ViewerState(
        dataset_id=dataset_id,
        dataset_label=dataset_label,
        scalar_key=scalar_key,
        scalar_label=scalar_label,
        axis=axis,
        slice_index=slice_index,
        file_path=file_path,
        palette=palette,
        units=units,
        scale=scale,
        threshold=threshold,
        range_min=stats["min"],
        range_max=stats["max"],
    )
