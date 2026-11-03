"""Edit visible label text while preserving readable _/^ formatting notation."""

from app.debug import debug_print
from utils.label_notation import LabelChar, parse_label, render_notation


def edit_label_text(label: str, position: int, length: int, *, action: str, text: str = "", kind: str = "sub") -> tuple[str, int]:
    """Use Qt UTF-16 positions; return updated notation and the new cursor position."""
    debug_print(f"Label editing action={action} position={position} length={length}")
    encoded = label.encode("utf-16-le")
    start = len(encoded[:position * 2].decode("utf-16-le"))
    end = len(encoded[:(position + length) * 2].decode("utf-16-le"))
    items = parse_label(label)
    debug_print(f"Label editing visible token count={len(items)}")
    first = next((index for index, item in enumerate(items) if item.end > start), len(items))
    last = next((index for index, item in enumerate(items) if item.start >= end), len(items)) if length else first
    if action == "backspace":
        if not length:
            if first == 0:
                debug_print("Label backspace at beginning; no change")
                return label, position
            first -= 1
        del items[first:last]
        boundary = first
    elif action in ("normal", "format-selected"):
        styles = (kind,) if action == "format-selected" else ()
        items[first:last] = [LabelChar(item.text, styles) for item in items[first:last]]
        boundary = last
    elif action in ("insert-normal", "insert-script", "insert-notation"):
        styles = (kind,) if action == "insert-script" else ()
        replacement = parse_label(text) if action == "insert-notation" else [LabelChar(char, styles) for char in text]
        items[first:last] = replacement
        boundary = first + len(replacement)
    else:
        raise ValueError(f"Unknown label edit action: {action}")
    updated, ends = render_notation(items)
    cursor = len(updated[:ends[boundary - 1]].encode("utf-16-le")) // 2 if boundary else 0
    debug_print(f"Label editing result={updated} cursor={cursor}")
    return updated, cursor
