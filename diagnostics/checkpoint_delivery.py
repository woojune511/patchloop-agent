"""Reference exact source already visible in a checkpoint's public evidence.

Only presentation copies change. Durable tool receipts, source admission and
current-file identities remain intact; missing source keeps the inline content.
"""
from __future__ import annotations

import copy
import json

from diagnostics.public_context_dedup import _source_bank
from patchloop.util import canonical_json, sha256_bytes

REFERENCE_RULES = (
    "A revalidated source span's content_reference names exact text already in "
    "saved_public_evidence, by source scope, path, file hash and inclusive line range. "
    "Read those lines as the span's content; its own file hash and range describe the "
    "current file. The reference changes text delivery only. Changed source and current "
    "verification results remain explicit."
)


def _results(exchanges):
    for item in exchanges:
        if item.get("type") != "function_call_output":
            continue
        try:
            result = json.loads(item["output"])
        except (KeyError, TypeError, ValueError):
            continue
        if (isinstance(result, dict) and result.get("tool") == "replace_text"
                and result.get("status") == "succeeded"
                and isinstance(result.get("output"), dict)):
            yield item, result


def _reference(span, sources):
    content = span.get("content")
    if (span.get("origin") != "revalidated_after_mutation" or not isinstance(content, str)
            or type(span.get("start_line")) is not int or type(span.get("end_line")) is not int
            or len(content.split("\n")) != span["end_line"] - span["start_line"] + 1):
        return None
    wanted = content.split("\n")
    for source in sources:
        if (source["path"] != span.get("path")
                or source["source_scope"] != span.get("source_scope", "repository")):
            continue
        for bounds in source["ranges"]:
            lines = bounds["content"].split("\n")
            for offset in range(len(lines) - len(wanted) + 1):
                if lines[offset:offset + len(wanted)] != wanted:
                    continue
                start = bounds["start_line"] + offset
                return {"document": "saved_public_evidence", "path": source["path"],
                    "source_scope": source["source_scope"], "file_hash": source["file_hash"],
                    "start_line": start, "end_line": start + len(wanted) - 1,
                    "content_hash": sha256_bytes(content.encode("utf-8"))}
    return None


def project_exchanges(evidence, exchanges):
    """Replace only fully matching revalidated text, never a changed hunk or receipt."""
    projected = copy.deepcopy(exchanges)
    sources, _ = _source_bank(evidence)
    for item, result in _results(projected):
        changed = False
        for span in result["output"].get("revalidated_spans", []):
            reference = _reference(span, sources)
            if reference is None:
                continue
            candidate = {key: value for key, value in span.items() if key != "content"}
            candidate["content_reference"] = reference
            if len(canonical_json(candidate)) < len(canonical_json(span)):
                span.clear()
                span.update(candidate)
                changed = True
        if changed:
            item["output"] = canonical_json(result)
    return projected


def expand_exchanges(evidence, exchanges):
    """Audit the exact source references without reading files or executing actions."""
    expanded = copy.deepcopy(exchanges)
    sources, _ = _source_bank(evidence)
    for item, result in _results(expanded):
        changed = False
        for span in result["output"].get("revalidated_spans", []):
            ref = span.get("content_reference")
            if ref is None:
                continue
            content = None
            for source in sources:
                if any(source[key] != ref[key] for key in ("source_scope", "path", "file_hash")):
                    continue
                for bounds in source["ranges"]:
                    if bounds["start_line"] <= ref["start_line"] <= ref["end_line"] <= bounds[
                        "end_line"
                    ]:
                        lines = bounds["content"].split("\n")
                        content = "\n".join(lines[ref["start_line"] - bounds["start_line"]:
                                                 ref["end_line"] - bounds["start_line"] + 1])
            if (ref.get("document") != "saved_public_evidence" or content is None
                    or sha256_bytes(content.encode("utf-8")) != ref["content_hash"]
                    or span["end_line"] - span["start_line"]
                    != ref["end_line"] - ref["start_line"]):
                raise ValueError("checkpoint source reference is not covered by visible evidence")
            span.pop("content_reference")
            span["content"] = content
            changed = True
        if changed:
            item["output"] = canonical_json(result)
    return expanded
