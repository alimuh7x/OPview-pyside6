"""Background worker for pre-warming the VTK reader cache before panel creation."""

from PySide6.QtCore import QThread, Signal

from utils.vtk_utils import get_reader


class PanelLoadWorker(QThread):
    """Loads a VTK reader off the main thread to warm the cache."""

    finished = Signal()
    failed   = Signal(str)

    def __init__(self, file_path: str, parent=None) -> None:
        super().__init__(parent)
        self.file_path = file_path

    def run(self) -> None:
        try:
            get_reader(self.file_path)
            self.finished.emit()
        except Exception as exc:
            self.failed.emit(str(exc))
