"""Readable scientific labels: _xx, ^p, and grouped expressions such as _{x y}."""

from dataclasses import dataclass
from html import escape, unescape
import re

from app.debug import debug_print

_TAG = re.compile(r"</?(sub|sup)>", re.IGNORECASE)
_ENTITY = re.compile(r"&(?:[a-z][a-z0-9]+|#[0-9]+|#x[0-9a-f]+);", re.IGNORECASE)
_SIMPLE = re.compile(r"[+-]?[^\W_]+", re.UNICODE)


@dataclass(frozen=True)
class LabelChar:
    text: str
    styles: tuple[str, ...]
    start: int = 0
    end: int = 0


def parse_label(label: str) -> list[LabelChar]:
    """Retain source character spans for selection/cursor edits; accept legacy tags."""
    if _TAG.search(label):
        result, styles, index = [], [], 0
        while index < len(label):
            tag = _TAG.match(label, index)
            if tag:
                kind = tag.group(1).lower()
                if tag.group().startswith("</"):
                    if styles and styles[-1] == kind:
                        styles.pop()
                else:
                    styles.append(kind)
                index = tag.end()
                continue
            entity = _ENTITY.match(label, index)
            end = entity.end() if entity else index + 1
            result.append(LabelChar(unescape(label[index:end]), tuple(styles), index, end))
            index = end
        return result

    def read(index, styles=(), grouped=False):
        result = []
        while index < len(label):
            char = label[index]
            if grouped and char == "}":
                return result, index + 1, True
            if char == "\\" and index + 1 < len(label) and label[index + 1] in "_^{}\\":
                result.append(LabelChar(label[index + 1], styles, index, index + 2))
                index += 2
                continue
            if char in "_^" and index + 1 < len(label):
                kind = "sub" if char == "_" else "sup"
                body = index + 1
                if label[body] == "{":
                    nested, end, closed = read(body + 1, styles + (kind,), True)
                    if closed:
                        result.extend(nested)
                        index = end
                        continue
                else:
                    end = body + (label[body] in "+-")
                    first_letter = end
                    while end < len(label) and label[end].isalnum():
                        end += 1
                    if end > first_letter:
                        result.extend(LabelChar(label[pos], styles + (kind,), pos, pos + 1) for pos in range(body, end))
                        index = end
                        continue
            entity = _ENTITY.match(label, index)
            end = entity.end() if entity else index + 1
            result.append(LabelChar(unescape(label[index:end]), styles, index, end))
            index = end
        return result, index, not grouped

    return read(0)[0]


def render_notation(items: list[LabelChar]) -> tuple[str, list[int]]:
    """Return canonical editor notation and source offsets after each visible token."""
    def render(group, depth):
        chunks, ends, offset, index = [], [], 0, 0
        while index < len(group):
            item = group[index]
            if len(item.styles) <= depth:
                fragment = "".join("\\" + char if char in "_^{}\\" else char for char in item.text)
                chunks.append(fragment)
                offset += len(fragment)
                ends.append(offset)
                index += 1
                continue
            prefix_styles = item.styles[:depth + 1]
            end = index + 1
            while end < len(group) and group[end].styles[:depth + 1] == prefix_styles:
                end += 1
            inner, inner_ends = render(group[index:end], depth + 1)
            following_letter = end < len(group) and len(group[end].styles) <= depth and group[end].text[:1].isalnum()
            braces = not _SIMPLE.fullmatch(inner) or following_letter
            prefix = ("_" if prefix_styles[-1] == "sub" else "^") + ("{" if braces else "")
            fragment = prefix + inner + ("}" if braces else "")
            ends.extend(offset + len(prefix) + value for value in inner_ends)
            chunks.append(fragment)
            offset += len(fragment)
            index = end
        return "".join(chunks), ends

    return render(items, 0)


def label_to_notation(label: str) -> str:
    result = render_notation(parse_label(str(label)))[0]
    debug_print(f"Label editor notation={result}")
    return result


def label_to_markup(label: str) -> str:
    result, active = [], ()
    for item in parse_label(str(label)):
        common = 0
        while common < min(len(active), len(item.styles)) and active[common] == item.styles[common]:
            common += 1
        result.extend(f"</{kind}>" for kind in reversed(active[common:]))
        result.extend(f"<{kind}>" for kind in item.styles[common:])
        result.append(escape(item.text).replace("_", "&#95;").replace("^", "&#94;"))
        active = item.styles
    result.extend(f"</{kind}>" for kind in reversed(active))
    return "".join(result)
