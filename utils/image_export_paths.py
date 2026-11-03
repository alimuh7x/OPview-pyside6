"""Remember the image export folder across views and application restarts."""

from pathlib import Path

from PySide6.QtCore import QSettings

from app.debug import debug_print


def image_export_path(filename: str) -> str:
    debug_print(f"Image export suggested filename={filename}")
    folder = str(QSettings("OPview", "OPview").value("last_image_export_folder", "") or "")
    debug_print(f"Image export remembered folder={folder}")
    if folder and Path(folder).is_dir():
        result = str(Path(folder) / Path(filename).name)
        debug_print(f"Image export dialog starting path={result}")
        return result
    debug_print("Image export using default filename; no available remembered folder")
    return filename


def remember_image_export_path(path: str) -> None:
    debug_print(f"Image export completed path={path}")
    if not path:
        debug_print("Image export folder unchanged for empty path")
        return
    folder = str(Path(path).resolve().parent)
    debug_print(f"Image export saving folder={folder}")
    settings = QSettings("OPview", "OPview")
    settings.setValue("last_image_export_folder", folder)
    debug_print("Image export folder setting updated")
    settings.sync()
    debug_print(f"Image export folder settings status={settings.status()}")
