"""One Multi View comparison panel (one tab)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from config.constants import DEFAULTS, PALETTES
from multi_view.colorbar_canvas import ColorbarCanvas, _W as _CB_W
from multi_view.multi_view_cell import MultiViewCell, MultiViewHeader, _CELL_W
from utils.vtk_utils import get_reader
from viewer.colorscale import palette_to_cmap
from viewer.heatmap_canvas import _CANVAS_HEIGHT
from viewer.range_slider_widget import RangeSliderWidget
from viewer.toggle_switch_widget import ToggleSwitchWidget

_ASSETS = Path(__file__).resolve().parent.parent / "assets"
_LOGO_W = 58


class MultiViewPanel(QWidget):
    """Side-by-side heatmap comparison with shared controls."""

    def __init__(self, dataset_info: dict, parent=None) -> None:
        super().__init__(parent)
        self._dataset_info       = dataset_info
        self._scalar_defs        = self._build_scalar_defs(dataset_info)
        self._available_projects = dataset_info.get("available_projects", [])
        self._columns: dict[str, tuple[MultiViewHeader, MultiViewCell]] = {}
        self._build_ui()
        self._connect_signals()
        self._populate_project_combo()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.setAutoFillBackground(True)
        self.setStyleSheet("MultiViewPanel { background: white; }")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Row 1: four dropdowns
        r1_card = QWidget()
        r1_card.setObjectName("controlsCard")
        r1_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        r1 = QHBoxLayout(r1_card)
        r1.setContentsMargins(14, 8, 14, 8)
        r1.setSpacing(8)

        self.project_combo = QComboBox(); self.project_combo.setObjectName("viewerCombo")
        self.file_combo    = QComboBox(); self.file_combo.setObjectName("viewerCombo")
        self.type_combo    = QComboBox(); self.type_combo.setObjectName("viewerCombo")
        self.type_combo.addItem("Heatmap",         "heatmap")
        self.type_combo.addItem("Contour Lines",   "contour_lines")
        self.type_combo.addItem("Contour Filled",  "contour_filled")
        self.type_combo.addItem("Heatmap+Contour", "heatmap_contour")
        self.palette_combo = QComboBox(); self.palette_combo.setObjectName("viewerCombo")
        for key in PALETTES:
            self.palette_combo.addItem(key.replace("-", " ").title(), key)

        r1.addWidget(self.project_combo, 2)
        r1.addWidget(self.file_combo, 3)
        r1.addWidget(self.type_combo, 2)
        r1.addWidget(self.palette_combo, 2)
        root.addWidget(r1_card)

        # Row 2: range controls
        r2_card = QWidget()
        r2_card.setObjectName("controlsCard")
        r2_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        r2 = QHBoxLayout(r2_card)
        r2.setContentsMargins(14, 6, 14, 6)
        r2.setSpacing(8)

        r2.addWidget(QLabel("Range:"))
        self.range_min = QDoubleSpinBox(); self.range_min.setObjectName("viewerSpin")
        self.range_min.setDecimals(6); self.range_min.setRange(-1e12, 1e12)
        self.range_max = QDoubleSpinBox(); self.range_max.setObjectName("viewerSpin")
        self.range_max.setDecimals(6); self.range_max.setRange(-1e12, 1e12)
        self.range_max.setValue(1.0)
        self.range_slider  = RangeSliderWidget()
        self.full_scale    = ToggleSwitchWidget("Full Scale",         checked=True)
        self.interfaces_on = ToggleSwitchWidget("Interfaces Overlay", checked=False)

        r2.addWidget(self.range_min, 1)
        r2.addWidget(self.range_max, 1)
        r2.addWidget(self.range_slider, 3)
        r2.addWidget(self.full_scale)
        r2.addWidget(self.interfaces_on)
        root.addWidget(r2_card)

        # Heatmap scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(False)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._area = QWidget()
        area_vbox = QVBoxLayout(self._area)
        area_vbox.setContentsMargins(0, 0, 0, 0)
        area_vbox.setSpacing(0)

        # Header row: [logo spacer] [...file headers...] [colorbar spacer]
        self._header_row = QWidget()
        self._hl = QHBoxLayout(self._header_row)
        self._hl.setContentsMargins(0, 2, 0, 2)
        self._hl.setSpacing(8)
        self._hl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        logo_hdr = QWidget(); logo_hdr.setFixedWidth(_LOGO_W)
        self._hl.addWidget(logo_hdr)
        self._cb_hdr = QWidget(); self._cb_hdr.setFixedWidth(_CB_W)
        self._hl.addWidget(self._cb_hdr)

        # Heatmap row: [logo] [...cells...] [colorbar]
        self._heatmap_row = QWidget()
        self._ml = QHBoxLayout(self._heatmap_row)
        self._ml.setContentsMargins(0, 0, 0, 0)
        self._ml.setSpacing(8)
        self._ml.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Logo widget
        logo_w = QWidget(); logo_w.setFixedSize(_LOGO_W, _CANVAS_HEIGHT)
        logo_lbl = QLabel(logo_w)
        lp = _ASSETS / "OP_Logo.png"
        if lp.exists():
            px = QPixmap(str(lp)).scaledToWidth(_LOGO_W - 8, Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(px)
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
        logo_lbl.setGeometry(0, 0, _LOGO_W, _CANVAS_HEIGHT)
        self._ml.addWidget(logo_w)

        # Colorbar (rightmost)
        self.colorbar = ColorbarCanvas()
        self._ml.addWidget(self.colorbar)

        area_vbox.addWidget(self._header_row)
        area_vbox.addWidget(self._heatmap_row)
        self._update_area_size()

        scroll.setWidget(self._area)
        root.addWidget(scroll, 1)

        # Export button
        bot = QWidget()
        bl = QHBoxLayout(bot)
        bl.setContentsMargins(8, 4, 8, 4)
        bl.addStretch(1)
        self.export_btn = QPushButton(QIcon(str(_ASSETS / "download.png")), "Export PNG")
        self.export_btn.setProperty("subtle", True)
        bl.addWidget(self.export_btn)
        root.addWidget(bot)

    def _connect_signals(self) -> None:
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        self.file_combo.activated.connect(self._on_file_activated)
        self.type_combo.currentIndexChanged.connect(self._render_all)
        self.palette_combo.currentIndexChanged.connect(self._render_all)
        self.range_min.valueChanged.connect(self._render_all)
        self.range_max.valueChanged.connect(self._render_all)
        self.range_slider.values_changed.connect(self._on_slider_changed)
        self.full_scale.toggled.connect(self._render_all)
        self.interfaces_on.toggled.connect(self._render_all)
        self.export_btn.clicked.connect(self._export)

    # ── Population ────────────────────────────────────────────────────────────

    def _populate_project_combo(self) -> None:
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        for proj in self._available_projects:
            name = proj.get("project_name", proj.get("vtk_folder", ""))
            self.project_combo.addItem(name, proj)
        self.project_combo.blockSignals(False)
        self._on_project_changed()

    def _on_project_changed(self) -> None:
        proj = self.project_combo.currentData()
        files = proj.get("files", []) if proj else []
        self.file_combo.blockSignals(True)
        self.file_combo.clear()
        self.file_combo.addItem("Select file to add…", "")
        for fp in files:
            label = Path(fp).name
            # mark already-added files
            if fp in self._columns:
                label = f"✓ {label}"
            self.file_combo.addItem(label, fp)
        self.file_combo.blockSignals(False)

    def _on_file_activated(self, index: int) -> None:
        fp = self.file_combo.itemData(index)
        if fp and fp not in self._columns:
            self._add_column(fp)
            self._on_project_changed()   # refresh marks

    # ── Column management ─────────────────────────────────────────────────────

    def _add_column(self, file_path: str) -> None:
        header = MultiViewHeader(file_path)
        cell   = MultiViewCell(file_path)
        header.close_requested.connect(self._remove_column)
        self._columns[file_path] = (header, cell)

        cb_h_idx = self._hl.indexOf(self._cb_hdr)
        cb_m_idx = self._ml.indexOf(self.colorbar)
        self._hl.insertWidget(cb_h_idx, header)
        self._ml.insertWidget(cb_m_idx, cell)

        self._update_area_size()
        self._render_all()

    def _remove_column(self, file_path: str) -> None:
        if file_path not in self._columns:
            return
        header, cell = self._columns.pop(file_path)
        self._hl.removeWidget(header)
        self._ml.removeWidget(cell)
        header.deleteLater()
        cell.deleteLater()
        self._update_area_size()
        self._on_project_changed()
        self._render_all()

    def _update_area_size(self) -> None:
        n = len(self._columns)
        spacing = 8
        gaps = (n + 1) * spacing if n > 0 else 0   # gaps between logo, cells, colorbar
        self._area.setFixedWidth(_LOGO_W + n * _CELL_W + _CB_W + gaps)
        self._area.setFixedHeight(_CANVAS_HEIGHT + 30)

    # ── Rendering ─────────────────────────────────────────────────────────────

    def _render_all(self, *_) -> None:
        if not self._columns or not self._scalar_defs:
            return
        sd = self._scalar_defs[0]
        cmap  = palette_to_cmap(self.palette_combo.currentData() or "aqua-fire")
        scale = sd.get("scale", 1.0) or 1.0
        label = sd.get("label", "")
        units = sd.get("units")
        cb_label = f"{label} ({units})" if units else label

        grids = []
        for fp in self._columns:
            try:
                reader = get_reader(fp)
                x, y, z, _ = reader.get_interpolated_slice(
                    axis="y", index=0,
                    scalar_name=sd["array"],
                    component=sd.get("component"),
                    resolution=DEFAULTS["interpolation_resolution"],
                )
                grids.append((fp, x, y, z * scale))
            except Exception:
                grids.append((fp, None, None, None))

        valid = [z for _, _, _, z in grids if z is not None]
        if self.full_scale.isChecked() and valid:
            vmin = float(min(np.nanmin(z) for z in valid))
            vmax = float(max(np.nanmax(z) for z in valid))
        else:
            vmin = self.range_min.value()
            vmax = self.range_max.value()

        self.range_min.blockSignals(True)
        self.range_max.blockSignals(True)
        self.range_min.setValue(vmin)
        self.range_max.setValue(vmax)
        self.range_min.blockSignals(False)
        self.range_max.blockSignals(False)

        for fp, x, y, z in grids:
            _, cell = self._columns[fp]
            if z is not None:
                cell.render(x, y, z, vmin=vmin, vmax=vmax, cmap=cmap)

        self.colorbar.update_colorbar(cmap, vmin, vmax, cb_label)

    def _on_slider_changed(self, lo: float, hi: float) -> None:
        self.range_min.blockSignals(True)
        self.range_max.blockSignals(True)
        self.range_min.setValue(lo)
        self.range_max.setValue(hi)
        self.range_min.blockSignals(False)
        self.range_max.blockSignals(False)
        self._render_all()

    # ── Export ────────────────────────────────────────────────────────────────

    def _export(self) -> None:
        from PySide6.QtGui import QImage, QPainter
        from PySide6.QtWidgets import QFileDialog

        pixmaps = [cell.grab_pixmap() for _, cell in self._columns.values()]
        cb_px   = self.colorbar._web.grab()
        if not pixmaps:
            return
        total_w = sum(p.width() for p in pixmaps) + cb_px.width()
        max_h   = max(p.height() for p in pixmaps)
        img = QImage(total_w, max_h, QImage.Format.Format_RGB32)
        img.fill(Qt.GlobalColor.white)
        p = QPainter(img)
        x = 0
        for px in pixmaps:
            p.drawPixmap(x, 0, px); x += px.width()
        p.drawPixmap(x, 0, cb_px)
        p.end()
        path, _ = QFileDialog.getSaveFileName(self, "Export", "multi_view.png", "PNG (*.png)")
        if path:
            img.save(path)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _build_scalar_defs(dataset_info: dict) -> list[dict]:
        projects = dataset_info.get("available_projects", [])
        cfg   = projects[0].get("dataset_config", {}) if projects else {}
        scale = cfg.get("scale", 1.0)
        units = cfg.get("units")
        scalars = cfg.get("scalars")
        if scalars:
            return [{"label": d["label"], "value": f"s-{i}", "array": d["array"],
                     "component": d.get("component"),
                     "scale": d.get("scale", scale), "units": d.get("units", units)}
                    for i, d in enumerate(scalars)]
        files = [f for p in projects for f in p.get("files", [])]
        if not files:
            return []
        try:
            reader = get_reader(files[0])
            return [{"label": n, "value": n, "array": n, "component": None,
                     "scale": scale or 1.0, "units": units}
                    for n in reader.scalar_fields]
        except Exception:
            return []
