"""Qt WebEngine download helpers."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QFileDialog, QWidget

from app.debug import debug_print


PNG_FILTER = "PNG (*.png);;All Files (*)"


def _suggested_png_name(suggested_name: str, fallback_name: str) -> str:
    debug_print("webengine_downloads._suggested_png_name called")
    debug_print(f"webengine_downloads suggested_name={suggested_name}")
    debug_print(f"webengine_downloads fallback_name={fallback_name}")
    raw_name = (suggested_name or fallback_name or "plot.png").strip()
    path = Path(raw_name)
    if not path.suffix:
        path = path.with_suffix(".png")
    debug_print(f"webengine_downloads resolved suggested path={path}")
    return str(path)


def _normalise_png_save_path(selected_path: str, suggested_name: str) -> str:
    debug_print("webengine_downloads._normalise_png_save_path called")
    debug_print(f"webengine_downloads selected_path={selected_path}")
    debug_print(f"webengine_downloads suggested_name={suggested_name}")
    if not selected_path:
        debug_print("webengine_downloads selected path empty")
        return ""
    path = Path(selected_path)
    if not path.suffix:
        suggested_suffix = Path(suggested_name).suffix or ".png"
        path = path.with_suffix(suggested_suffix)
        debug_print(f"webengine_downloads appended suffix path={path}")
    debug_print(f"webengine_downloads normalised path={path}")
    return str(path)


def _apply_download_path(download, selected_path: str) -> None:
    debug_print("webengine_downloads._apply_download_path called")
    path = Path(selected_path)
    debug_print(f"webengine_downloads download directory={path.parent}")
    debug_print(f"webengine_downloads download filename={path.name}")
    download.setDownloadDirectory(str(path.parent))
    download.setDownloadFileName(path.name)
    download.accept()
    debug_print("webengine_downloads download accepted")


def install_save_dialog_download_handler(
    web_view: QWebEngineView,
    parent: QWidget,
    *,
    fallback_name: str,
    dialog_title: str = "Save Plotly PNG",
) -> None:
    """Install a per-view WebEngine profile that asks before saving downloads."""
    debug_print("webengine_downloads.install_save_dialog_download_handler called")
    debug_print(f"webengine_downloads fallback_name={fallback_name}")
    profile = QWebEngineProfile(web_view)
    debug_print("webengine_downloads profile created")
    page = QWebEnginePage(profile, web_view)
    debug_print("webengine_downloads page created")
    web_view.setPage(page)
    debug_print("webengine_downloads page assigned to view")

    def _on_download_requested(download) -> None:
        debug_print("webengine_downloads download requested")
        suggested_name = download.suggestedFileName() or download.downloadFileName()
        debug_print(f"webengine_downloads raw suggested name={suggested_name}")
        default_path = _suggested_png_name(suggested_name, fallback_name)
        debug_print(f"webengine_downloads dialog default path={default_path}")
        selected_path, _ = QFileDialog.getSaveFileName(
            parent,
            dialog_title,
            default_path,
            PNG_FILTER,
        )
        debug_print(f"webengine_downloads dialog selected path={selected_path}")
        final_path = _normalise_png_save_path(selected_path, default_path)
        if not final_path:
            debug_print("webengine_downloads download cancelled by user")
            download.cancel()
            return
        _apply_download_path(download, final_path)

    profile.downloadRequested.connect(_on_download_requested)
    debug_print("webengine_downloads downloadRequested connected")
    web_view._opview_download_profile = profile
    web_view._opview_download_page = page
    web_view._opview_download_handler = _on_download_requested
    debug_print("webengine_downloads handler references stored")
