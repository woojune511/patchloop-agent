"""Lossless, readable deduplication of a saved public diagnostic context.

This changes representation, never evidence selection. Source text is printed
once per pinned file line; repeated large JSON values use explicit references.
The expander is an offline audit aid, not an extra model tool.
"""
from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy
from typing import Any

FORMAT = "public-context-dedup-v1"
MIN_REFERENCE_CHARS = 256
_MARKERS = frozenset({"$ref", "$source", "$literal"})


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False)


def _span(value: Any) -> tuple[tuple[str, str, str], int, int, list[str]] | None:
    if (not isinstance(value, dict)
            or not {"path", "file_hash", "start_line", "end_line", "content"} <= value.keys()
            or not isinstance(value["content"], str)):
        return None
    start, end = value["start_line"], value["end_line"]
    if type(start) is not int or type(end) is not int or not 1 <= start <= end:
        raise ValueError("public source span has an invalid line range")
    lines = value["content"].split("\n")
    if len(lines) != end - start + 1:
        raise ValueError("public source span content differs from its line range")
    provenance = value.get("provenance")
    scope = value.get("source_scope", (
        provenance.get("scope", "repository") if isinstance(provenance, dict) else "repository"))
    key = (scope, value["path"], value["file_hash"])
    if not all(isinstance(item, str) and item for item in key):
        raise ValueError("public source span lacks a pinned identity")
    return key, start, end, lines


def _source_bank(value: Any) -> tuple[list[dict], dict[tuple[str, str, str], str]]:
    files: dict[tuple[str, str, str], dict[int, str]] = {}

    def visit(node):
        span = _span(node)
        if span is not None:
            key, start, _, lines = span
            known = files.setdefault(key, {})
            for number, line in enumerate(lines, start):
                if number in known and known[number] != line:
                    raise ValueError("conflicting public source lines for the same pinned file")
                known[number] = line
        if isinstance(node, dict):
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(value)
    sources, identities = [], {}
    for index, (key, lines) in enumerate(sorted(files.items()), 1):
        identity = f"source_{index}"
        identities[key] = identity
        ranges = []
        for number, line in sorted(lines.items()):
            if ranges and ranges[-1]["end_line"] + 1 == number:
                ranges[-1]["end_line"] = number
                ranges[-1]["content"] += "\n" + line
            else:
                ranges.append({"start_line": number, "end_line": number, "content": line})
        sources.append({"id": identity, "source_scope": key[0], "path": key[1],
                        "file_hash": key[2], "ranges": ranges})
    return sources, identities


def deduplicate(value: Any) -> dict:
    """Return all supplied public facts in a lossless reference representation.

    Only source spans carrying path, hash and exact line bounds enter the source
    bank. All original metadata and unique negative observations remain present.
    Literal reference-like dictionaries are escaped rather than interpreted.
    """
    _canonical(value)  # Require finite JSON values before building any derived state.
    sources, identities = _source_bank(value)

    def source_refs(node):
        if isinstance(node, dict):
            span = _span(node)
            result = {key: source_refs(child) for key, child in node.items()}
            if span is not None:
                key, start, end, _ = span
                result["content"] = {"$source": identities[key],
                                     "start_line": start, "end_line": end}
            return {"$literal": result} if _MARKERS & node.keys() else result
        if isinstance(node, list):
            return [source_refs(child) for child in node]
        return node

    transformed = source_refs(value)
    counts: Counter[str] = Counter()

    def count(node):
        if isinstance(node, (dict, list, str)):
            encoded = _canonical(node)
            if len(encoded) >= MIN_REFERENCE_CHARS:
                counts[encoded] += 1
        if isinstance(node, dict):
            for child in node.values():
                count(child)
        elif isinstance(node, list):
            for child in node:
                count(child)

    count(transformed)
    names, definitions = {}, {}

    def intern(node, *, define=False):
        encoded = _canonical(node)
        if not define and counts[encoded] > 1:
            if encoded not in names:
                identity = f"value_{len(names) + 1}"
                names[encoded] = identity
                definitions[identity] = intern(node, define=True)
            return {"$ref": names[encoded]}
        if isinstance(node, dict):
            return {key: intern(child, define=key == "$literal")
                    for key, child in node.items()}
        if isinstance(node, list):
            return [intern(child) for child in node]
        return node

    document = intern(transformed)
    return {"format": FORMAT, "document": document, "sources": sources,
            "definitions": definitions}


def expand(value: dict) -> Any:
    """Restore the original decoded JSON, rejecting malformed references."""
    if (not isinstance(value, dict) or value.get("format") != FORMAT
            or set(value) != {"format", "document", "sources", "definitions"}):
        raise ValueError("unknown public context representation")
    sources = {}
    for source in value["sources"]:
        if source["id"] in sources:
            raise ValueError("duplicate source bank identity")
        lines = {}
        for span in source["ranges"]:
            content = span["content"].split("\n")
            if len(content) != span["end_line"] - span["start_line"] + 1:
                raise ValueError("invalid source bank range")
            for number, line in enumerate(content, span["start_line"]):
                if number in lines:
                    raise ValueError("source bank ranges overlap")
                lines[number] = line
        sources[source["id"]] = lines

    def visit(node, active=()):
        if isinstance(node, list):
            return [visit(child, active) for child in node]
        if not isinstance(node, dict):
            return node
        if set(node) == {"$ref"}:
            name = node["$ref"]
            if name in active or name not in value["definitions"]:
                raise ValueError("unknown or cyclic public context reference")
            return visit(value["definitions"][name], (*active, name))
        if set(node) == {"$source", "start_line", "end_line"}:
            if (type(node["start_line"]) is not int or type(node["end_line"]) is not int
                    or not 1 <= node["start_line"] <= node["end_line"]):
                raise ValueError("public source reference has an invalid range")
            try:
                lines = sources[node["$source"]]
                return "\n".join(lines[index] for index in
                                 range(node["start_line"], node["end_line"] + 1))
            except (KeyError, TypeError) as exc:
                raise ValueError("public source reference is not covered") from exc
        if set(node) == {"$literal"}:
            return {key: visit(child, active) for key, child in node["$literal"].items()}
        return {key: visit(child, active) for key, child in node.items()}

    return deepcopy(visit(value["document"]))


def statistics(value: dict) -> dict:
    """Character/structure counts only; these are not model-token counts."""
    original = expand(value)
    return {"original_json_chars": len(_canonical(original)),
            "deduplicated_json_chars": len(_canonical(value)),
            "source_files": len(value["sources"]),
            "source_lines": sum(span["end_line"] - span["start_line"] + 1
                                for source in value["sources"] for span in source["ranges"]),
            "definitions": len(value["definitions"])}
