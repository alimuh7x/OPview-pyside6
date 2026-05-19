"""Generic text-data source for Custom Graph panels."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from app.debug import debug_print
from config.constants import ALLOWED_TEXTDATA_EXTENSIONS


class GenericTextDataSource:
    """Load arbitrary tabular text data from a local file path."""

    def __init__(self, file_path: Path | str) -> None:
        debug_print(f"GenericTextDataSource.__init__ file_path={file_path}")
        self.file_path = Path(file_path)
        self._columns: list[str] = []
        self._data: dict[str, np.ndarray] = {}
        self._loaded = False
        self._separator = "whitespace"

    def load(self) -> bool:
        """Parse the file and expose numeric columns for plotting."""
        debug_print(f"GenericTextDataSource.load start path={self.file_path}")
        self._loaded = True
        self._columns = []
        self._data = {}

        if not self.file_path.exists():
            debug_print(f"GenericTextDataSource.load missing file={self.file_path}")
            return False
        if self.file_path.suffix.lower() not in ALLOWED_TEXTDATA_EXTENSIONS:
            debug_print(f"GenericTextDataSource.load unsupported suffix={self.file_path.suffix}")
            return False

        try:
            lines = self._read_nonempty_lines()
            debug_print(f"GenericTextDataSource.load nonempty_lines={len(lines)}")
            if len(lines) < 2:
                debug_print("GenericTextDataSource.load not enough rows")
                return False

            header = self._split_line(lines[0])
            debug_print(f"GenericTextDataSource.load header={header}")
            raw_columns: dict[str, list[float]] = {name: [] for name in header}

            for row_number, line in enumerate(lines[1:], start=2):
                parts = self._split_line(line)
                debug_print(f"GenericTextDataSource.load row={row_number} parts={len(parts)}")
                if len(parts) < len(header):
                    debug_print(f"GenericTextDataSource.load pad row={row_number} missing={len(header) - len(parts)}")
                    parts = parts + ["nan"] * (len(header) - len(parts))
                if len(parts) > len(header):
                    debug_print(f"GenericTextDataSource.load trim row={row_number} extra={len(parts) - len(header)}")
                    parts = parts[:len(header)]
                for name, value in zip(header, parts):
                    try:
                        raw_columns[name].append(float(value))
                    except ValueError:
                        debug_print(f"GenericTextDataSource.load nonnumeric value column={name} row={row_number}")
                        raw_columns[name].append(np.nan)

            for name, values in raw_columns.items():
                arr = np.asarray(values, dtype=float)
                debug_print(f"GenericTextDataSource.load column={name} size={arr.size}")
                if arr.size == 0:
                    debug_print(f"GenericTextDataSource.load skip empty column={name}")
                    continue
                if np.all(np.isnan(arr)):
                    debug_print(f"GenericTextDataSource.load skip nonnumeric column={name}")
                    continue
                self._columns.append(name)
                self._data[name] = arr

            debug_print(f"GenericTextDataSource.load columns={self._columns}")
            return bool(self._columns)
        except OSError as exc:
            debug_print(f"GenericTextDataSource.load os error={exc}")
            return False

    def columns(self) -> list[str]:
        debug_print(f"GenericTextDataSource.columns loaded={self._loaded} count={len(self._columns)}")
        return list(self._columns)

    def series(self, column: str) -> np.ndarray:
        debug_print(f"GenericTextDataSource.series column={column}")
        if column not in self._data:
            debug_print(f"GenericTextDataSource.series missing column={column}")
            raise KeyError(column)
        return self._data[column]

    def dataframe_dict(self) -> dict[str, np.ndarray]:
        debug_print("GenericTextDataSource.dataframe_dict called")
        return dict(self._data)

    @property
    def separator(self) -> str:
        return self._separator

    def _read_nonempty_lines(self) -> list[str]:
        debug_print(f"GenericTextDataSource._read_nonempty_lines path={self.file_path}")
        with self.file_path.open("r", encoding="utf-8-sig") as handle:
            lines = [line.strip() for line in handle if line.strip()]
        if lines and "," in lines[0]:
            self._separator = "comma"
        else:
            self._separator = "whitespace"
        debug_print(f"GenericTextDataSource._read_nonempty_lines separator={self._separator}")
        return lines

    def _split_line(self, line: str) -> list[str]:
        debug_print(f"GenericTextDataSource._split_line separator={self._separator}")
        if self._separator == "comma":
            return [part.strip() for part in next(csv.reader([line]))]
        return line.split()
