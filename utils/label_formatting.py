"""Render stored subscript/superscript label markup in Qt and Matplotlib."""

from html import escape, unescape
import re

from app.debug import debug_print
from utils.label_notation import label_to_markup

_PREVIEW_TAG = re.compile(r"(</?(?:sub|sup)>)", re.IGNORECASE)
_MATH_ESCAPES = {
    "\\": r"\\", "{": r"\{", "}": r"\}", "$": r"\$",
}


def label_to_html(label: str) -> str:
    """Allow only script tags in a rich-text preview; display other text literally."""
    parts = _PREVIEW_TAG.split(label_to_markup(str(label)))
    debug_print(f"Label preview parts={len(parts)}")
    result = "".join(part.lower() if _PREVIEW_TAG.fullmatch(part) else escape(unescape(part)) for part in parts)
    debug_print(f"Label preview markup={result}")
    return result


def label_to_matplotlib(label: str) -> str:
    """Convert balanced script markup, including nested scripts, to mathtext."""
    label = label_to_markup(str(label))
    if not _PREVIEW_TAG.search(label):
        return unescape(label)
    debug_print(f"Label converting scripts for Matplotlib={label}")
    root = []
    stack = [(None, root)]
    for part in _PREVIEW_TAG.split(label):
        tag = part.lower()
        if tag in ("<sub>", "<sup>"):
            kind, children = tag[1:-1], []
            stack[-1][1].append((kind, children))
            stack.append((kind, children))
            debug_print(f"Label parsing {kind} script depth={len(stack) - 1}")
        elif tag in ("</sub>", "</sup>"):
            if len(stack) == 1 or stack[-1][0] != tag[2:-1]:
                debug_print("Label unbalanced scripts; keeping literal label")
                return label
            stack.pop()
        elif part:
            stack[-1][1].append(unescape(part))
    if len(stack) != 1:
        debug_print("Label unclosed script; keeping literal label")
        return label

    def math_nodes(nodes) -> str:
        result = []
        seen = set()
        for node in nodes:
            if isinstance(node, str):
                escaped = "".join(_MATH_ESCAPES.get(char, char) for char in node)
                result.append(r"\text{" + escaped + "}")
                seen.clear()
            else:
                kind, children = node
                if not result or kind in seen:
                    result.append("{}")
                result.append(("_" if kind == "sub" else "^") + "{" + math_nodes(children) + "}")
                seen.add(kind)
        return "".join(result)

    result = []
    pending_scripts = []
    for node in root:
        if isinstance(node, str):
            if pending_scripts:
                result.append("$" + math_nodes(pending_scripts) + "$")
                pending_scripts.clear()
            result.append(node.replace("$", r"\$"))
        else:
            pending_scripts.append(node)
    if pending_scripts:
        result.append("$" + math_nodes(pending_scripts) + "$")
    converted = "".join(result)
    debug_print(f"Label Matplotlib text={converted}")
    return converted


def label_to_plotly(label: str) -> str:
    """Render notation while preserving Plotly's existing rich-text wrappers."""
    if _PREVIEW_TAG.search(label):
        return label
    wrapper = re.compile(r"(<(?:/?(?:b|i|em|strong|span|a)|br\s*/?)(?:\s[^>]*)?>)", re.IGNORECASE)
    parts = wrapper.split(label)
    return "".join(part if wrapper.fullmatch(part) else label_to_markup(part) for part in parts)


def format_plotly_figure(figure) -> None:
    """Translate display labels at chart serialization, keeping editor notation readable."""
    def title(owner):
        value = getattr(owner, "title", None)
        if value is not None and getattr(value, "text", None):
            value.text = label_to_plotly(value.text)

    title(figure.layout)
    for key in figure.layout:
        if key.startswith(("xaxis", "yaxis", "coloraxis")):
            owner = figure.layout[key]
            title(owner)
            if getattr(owner, "colorbar", None) is not None:
                title(owner.colorbar)
    for annotation in figure.layout.annotations or ():
        if annotation.text:
            annotation.text = label_to_plotly(annotation.text)
    for trace in figure.data:
        if trace.name:
            trace.name = label_to_plotly(trace.name)
        for owner in (trace, getattr(trace, "marker", None)):
            colorbar = getattr(owner, "colorbar", None)
            if colorbar is not None:
                title(colorbar)
        text = getattr(trace, "text", None)
        if isinstance(text, str):
            trace.text = label_to_plotly(text)
        elif text is not None:
            trace.text = [label_to_plotly(value) if isinstance(value, str) else value for value in text]
    debug_print("Plotly display labels converted from _/^ notation")
