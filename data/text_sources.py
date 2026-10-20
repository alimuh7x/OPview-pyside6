"""Generic text-data source for Custom Graph panels."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from config.constants import ALLOWED_TEXTDATA_EXTENSIONS

_COMMENT_PREFIXES = ("#", "%", "//")
# Delimiters in the order they are tried; "whitespace" (any run of blanks) is the final fallback.
_DELIMITERS = ((";", "semicolon"), ("\t", "tab"), (",", "comma"), (None, "whitespace"))
_DECIMAL_COMMA = re.compile(r"^[+-]?\d+,\d+(?:[eE][+-]?\d+)?$")
_SAMPLE_ROWS = 20
_MIN_NUMERIC_SHARE = 0.8  # share of numeric tokens that makes a delimiter believable


def _is_comment(line: str) -> bool:
    return line.startswith(_COMMENT_PREFIXES)


def _strip_comment_marker(line: str) -> str:
    for prefix in _COMMENT_PREFIXES:
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    return line


class GenericTextDataSource:
    """Load arbitrary tabular text data from a local file path.

    Understands whitespace, tab, comma and semicolon delimiters, decimal commas, `#`/`%`/`//` comment
    lines (including a commented header), a units row under the header, ragged rows (padded with NaN),
    duplicate or blank column names, and headerless numeric files. When a file cannot be loaded,
    `error` says why.
    """

    def __init__(self, file_path: Path | str) -> None:
        self.file_path = Path(file_path)
        self._columns: list[str] = []
        self._data: dict[str, np.ndarray] = {}
        self._units: dict[str, str] = {}
        self._loaded = False
        self._separator = "whitespace"
        self._error = ""

    # ---- public API ---------------------------------------------------------------------------
    def load(self) -> bool:
        """Parse the file and expose numeric columns for plotting."""
        self._loaded = True
        self._columns = []
        self._data = {}
        self._units = {}
        self._error = ""

        if not self.file_path.exists():
            return self._fail("File not found.")
        suffix = self.file_path.suffix.lower()
        if suffix not in ALLOWED_TEXTDATA_EXTENSIONS:
            return self._fail(f"Unsupported file type '{suffix}' (supported: {', '.join(ALLOWED_TEXTDATA_EXTENSIONS)}).")

        try:
            lines = self._read_lines()
        except OSError as exc:
            return self._fail(f"Could not read the file: {exc.strerror or exc}.")
        if not lines:
            return self._fail("The file is empty.")

        names, units, rows = self._split_table(lines)
        if names is None:
            return self._fail(units)  # (None, message, None): the message says what is missing

        width = len(names)
        padded = [row + ["nan"] * (width - len(row)) if len(row) < width else row for row in rows]
        for name, tokens in zip(names, zip(*padded)):
            arr = self._to_array(tokens)
            if arr.size == 0 or np.all(np.isnan(arr)):
                continue
            self._columns.append(name)
            self._data[name] = arr
            if name in units:
                self._units[name] = units[name]
        if not self._columns:
            return self._fail("No numeric columns found in the file.")
        return True

    def columns(self) -> list[str]:
        return list(self._columns)

    def series(self, column: str) -> np.ndarray:
        if column not in self._data:
            raise KeyError(column)
        return self._data[column]

    def dataframe_dict(self) -> dict[str, np.ndarray]:
        return dict(self._data)

    def units(self) -> dict[str, str]:
        """Units read from a units row under the header (e.g. `[s] [Pa]`), by column name."""
        return dict(self._units)

    @property
    def separator(self) -> str:
        return self._separator

    @property
    def error(self) -> str:
        """Why the last `load()` failed ("" after a successful load)."""
        return self._error

    # ---- parsing ------------------------------------------------------------------------------
    def _fail(self, message: str) -> bool:
        self._error = message
        return False

    def _read_lines(self) -> list[str]:
        # errors="replace": a stray non-UTF-8 byte (e.g. in a comment) must not make the file unreadable.
        with self.file_path.open("r", encoding="utf-8-sig", errors="replace", newline=None) as handle:
            return [line.strip() for line in handle if line.strip()]

    def _split_table(self, lines: list[str]):
        """Return (names, units, data rows), or (None, message, None) when there is no usable table."""
        content = [line for line in lines if not _is_comment(line)]
        if not content:
            return None, "The file only contains comments.", None
        preceding_comment = ""
        for line in lines:
            if not _is_comment(line):
                break
            preceding_comment = line

        delimiter, label = self._detect_delimiter(content, preceding_comment)
        self._separator = label
        first = self._split(content[0], delimiter)
        has_header_line = self._numeric_share(first, delimiter) < 0.5
        if has_header_line:  # a text first line is the header
            names_raw, body = first, content[1:]
        else:  # numbers from the first row on: the header, if there is one, was a comment
            body = content
            names_raw = self._split(_strip_comment_marker(preceding_comment), delimiter) if preceding_comment else []

        rows = [self._split(line, delimiter) for line in body]
        units_raw: list[str] = []
        if names_raw and rows and self._numeric_share(rows[0], delimiter) == 0.0:
            units_raw = rows.pop(0)  # a row of pure text under the header ("[s] [Pa]") holds units, not data
        if not rows:
            return None, "No data rows found: the file needs a header line and at least one row of numbers.", None
        if not names_raw and len(rows) < 2:
            return None, "Only one line of numbers and no header: add a header line with the column names.", None
        width = max(len(names_raw), max(len(row) for row in rows))
        names = self._unique_names(names_raw, width)
        return names, self._units_by_name(names, units_raw), [row[:width] for row in rows]

    def _detect_delimiter(self, content: list[str], preceding_comment: str) -> tuple[str | None, str]:
        header_candidates = [content[0]] + ([_strip_comment_marker(preceding_comment)] if preceding_comment else [])
        sample = content[1 : 1 + _SAMPLE_ROWS] or content[:1]
        for delimiter, label in _DELIMITERS[:-1]:
            if not any(delimiter in line for line in header_candidates):
                continue  # the header would be a single token: not this delimiter
            sample_rows = [self._split(line, delimiter) for line in sample]
            # a text-only row (units under the header) must not make the delimiter look wrong
            data_rows = [row for row in sample_rows if self._numeric_share(row, delimiter) > 0.0] or sample_rows
            tokens = [token for row in data_rows for token in row]
            if tokens and self._numeric_share(tokens, delimiter) >= _MIN_NUMERIC_SHARE:
                return delimiter, label
        return None, "whitespace"

    @staticmethod
    def _split(line: str, delimiter: str | None) -> list[str]:
        if delimiter is None:
            return line.split()
        return [part.strip() for part in line.split(delimiter)]

    def _to_array(self, tokens) -> np.ndarray:
        """One column of tokens as floats: numpy's fast conversion first, token by token only if needed."""
        try:
            return np.array(tokens, dtype=float)
        except ValueError:
            return np.array([self._to_float(token) for token in tokens], dtype=float)

    def _to_float(self, token: str) -> float:
        try:
            return float(token)
        except ValueError:
            if self._separator != "comma" and _DECIMAL_COMMA.match(token):
                return float(token.replace(",", "."))
            return np.nan

    def _numeric_share(self, tokens: list[str], delimiter: str | None) -> float:
        """Share of the non-empty tokens that parse as numbers (decimal commas count unless `,` delimits)."""
        values = [token for token in tokens if token != ""]
        if not values:
            return 0.0
        decimal_comma = delimiter != ","
        count = 0
        for token in values:
            try:
                float(token)
                count += 1
            except ValueError:
                if decimal_comma and _DECIMAL_COMMA.match(token):
                    count += 1
        return count / len(values)

    @staticmethod
    def _unique_names(names_raw: list[str], width: int) -> list[str]:
        names: list[str] = []
        seen: dict[str, int] = {}
        for index in range(width):
            base = names_raw[index].strip() if index < len(names_raw) else ""
            if not base:
                base = f"Column {index + 1}"
            seen[base] = seen.get(base, 0) + 1
            names.append(base if seen[base] == 1 else f"{base}_{seen[base]}")
        return names

    @staticmethod
    def _units_by_name(names: list[str], units_raw: list[str]) -> dict[str, str]:
        units: dict[str, str] = {}
        for index, name in enumerate(names):
            if index < len(units_raw):
                text = units_raw[index].strip().strip("[]()").strip()
                if text:
                    units[name] = text
        return units
