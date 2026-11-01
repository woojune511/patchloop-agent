"""Recover an already delivered read around an explicit source-search hit."""

from __future__ import annotations

import copy

from patchloop.dev.history_search import PublicHistory
from patchloop.util import sha256_json


def enclosing_span(snippet, observed):
    """Union same-version overlapping ranges without dropping the original hit's edges."""
    lines = {}
    for span in (snippet, observed):
        for number, text in enumerate(span["content"].split("\n"), span["start_line"]):
            if number <= span["end_line"]:
                lines[number] = text
    first, last = min(lines), max(lines)
    identity = {"path": snippet["path"], "file_hash": snippet["file_hash"],
                "start_line": first, "end_line": last,
                "content": "\n".join(lines[n] for n in range(first, last + 1))}
    return {"span_id": "span_" + sha256_json(identity).split(":", 1)[1][:16], **identity}


def expand(output: dict, history: PublicHistory, visible: set[tuple], *, limit=24_000) -> dict:
    """Replace snippets with exact observed ranges; never reinterpret old source as current.

    The current search owns file/hash/location identity. No semantic query matching,
    new filesystem reads, function clipping, or additional history reference is used.
    """
    result = copy.deepcopy(output)
    snippets = result.get("spans", [])
    candidates = []
    for record in history.records.values():
        call = record["body"].get("call", {})
        if call.get("tool") != "read_file":
            continue
        for span in (record["body"].get("result", {}).get("output") or {}).get("spans", []):
            candidates.append((record, span))
    recovered, hints = [], []
    size = sum(len(s["content"]) for s in snippets)
    for index, snippet in enumerate(snippets):
        matches = [
            (r, s)
            for r, s in candidates
            if s["path"] == snippet["path"]
            and s["start_line"] <= snippet["end_line"]
            and s["end_line"] >= snippet["start_line"]
            and s["end_line"] - s["start_line"] > snippet["end_line"] - snippet["start_line"]
        ]
        # Prefer the smallest complete prior read containing the matched query,
        # not an arbitrarily selected function or a large unrelated file window.
        matches = [(r, s) for r, s in matches if result["query"] in s["content"]]
        matches.sort(
            key=lambda pair: (
                pair[1]["file_hash"] != snippet["file_hash"],
                len(pair[1]["content"]),
                -pair[0]["origin"]["first_delivered_sequence"],
            )
        )
        if not matches:
            continue
        record, span = matches[0]
        hint = {
            "record_id": record["record_id"],
            "action_id": record["body"]["call"]["action_id"],
            "path": span["path"],
            "start_line": span["start_line"],
            "end_line": span["end_line"],
            "file_hash": span["file_hash"],
        }
        if span["file_hash"] != snippet["file_hash"]:
            hints.append({**hint, "delivery": "old_file_version_read_current_source"})
            continue
        keys = {
            (span["path"], span["file_hash"], n)
            for n in range(span["start_line"], span["end_line"] + 1)
        }
        if keys <= visible:
            continue
        expanded = enclosing_span(snippet, span)
        proposed = size - len(snippet["content"]) + len(expanded["content"])
        if proposed > limit:
            hints.append({**hint, "delivery": "omitted_size_limit"})
            continue
        # Avoid duplicating the same whole read for nearby literal matches.
        if any(s["path"] == span["path"] and s["file_hash"] == span["file_hash"]
               and s["start_line"] <= span["start_line"] and s["end_line"] >= span["end_line"]
               for s in snippets[:index]):
            continue
        snippets[index] = expanded
        size = proposed
        recovered.append({**hint, "delivery": "complete_observed_read"})
    if recovered or hints:
        result["source_recovery"] = {
            "recovered": recovered,
            "omitted": hints,
            "interpretation": "Exact prior reads at current search locations. Old file versions "
            "are hints only; use read_file for current source or search_history(record_id) "
            "for the old record. A restored range is not necessarily a whole function.",
        }
    return result
