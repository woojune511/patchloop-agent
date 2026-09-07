"""Reference source already delivered in the immutable native tool history.

New mutation results may reference position-bound unchanged source. Durable receipts,
source admission, canonical context and previously sent native items remain exact.
"""

from __future__ import annotations

import copy
import json
from collections import defaultdict
from typing import Any

from patchloop.util import canonical_json, sha256_bytes

MAX_CONTENT_REFERENCES = 16


def _lines(span: Any) -> list[str] | None:
    if not isinstance(span, dict):
        return None
    path, file_hash = span.get("path"), span.get("file_hash")
    start, end, content = span.get("start_line"), span.get("end_line"), span.get("content")
    if (
        not isinstance(path, str) or not path
        or not isinstance(file_hash, str) or not file_hash
        or type(start) is not int or type(end) is not int or not 1 <= start <= end
        or not isinstance(content, str)
    ):
        return None
    # The explicit span range, not whole-file EOF rules, defines a final blank line.
    lines = content.replace("\r\n", "\n").split("\n")
    return lines if len(lines) == end - start + 1 else None


class _SourceIndex:
    """Resolve backward-only deliveries in memory, including exact rebinding aliases."""

    def __init__(self, history: list[dict[str, Any]]) -> None:
        self.observed: dict[tuple[str, str], dict[int, tuple[str, str, str]]] = defaultdict(dict)
        self.conflicts: set[tuple[str, str, int]] = set()
        self.deliveries: dict[tuple[str, str, str], tuple[str, int, list[str]]] = {}
        for item in history:
            self._add(item)

    def _resolve(self, span: Any) -> list[str] | None:
        lines = _lines(span)
        if lines is not None:
            return lines
        if not isinstance(span, dict) or "content" in span:
            return None
        start, end = span.get("start_line"), span.get("end_line")
        refs = span.get("content_delivery")
        if (type(start) is not int or type(end) is not int or not 1 <= start <= end
                or not isinstance(span.get("path"), str)
                or not isinstance(span.get("file_hash"), str)
                or span.get("origin") != "revalidated_after_mutation"
                or not isinstance(refs, list) or not 1 <= len(refs) <= MAX_CONTENT_REFERENCES):
            return None
        resolved: dict[int, str] = {}
        for ref in refs:
            if not isinstance(ref, dict):
                return None
            keys = [ref.get(key) for key in ("action_id", "field", "file_hash")]
            first, last, target = (ref.get(key) for key in (
                "start_line", "end_line", "target_start_line",
            ))
            if (not all(isinstance(key, str) for key in keys)
                    or not all(type(n) is int for n in (first, last, target))):
                return None
            delivery = self.deliveries.get(tuple(keys))
            if delivery is None:
                return None
            path, base, body = delivery
            if (path != span["path"] or not base <= first <= last < base + len(body)
                    or not start <= target <= target + last - first <= end):
                return None
            for offset, line in enumerate(body[first - base:last - base + 1], target):
                if offset in resolved and resolved[offset] != line:
                    return None
                resolved[offset] = line
        if len(resolved) != end - start + 1:
            return None
        lines = [resolved[n] for n in range(start, end + 1)]
        if sha256_bytes("\n".join(lines).encode()) != span.get("content_hash"):
            return None
        return lines

    def _add(self, item: dict[str, Any]) -> None:
        if item.get("type") != "function_call_output":
            return
        try:
            result = json.loads(item["output"])
        except (KeyError, TypeError, ValueError):
            return
        if (
            not isinstance(result, dict) or result.get("status") != "succeeded"
            or result.get("tool") not in {"read_file", "search_files", "replace_text"}
            or result.get("action_id") != item.get("call_id")
            or not isinstance(result.get("output"), dict)
        ):
            return
        output = result["output"]
        candidates = [("output.mutation_evidence", output.get("mutation_evidence"))]
        for key in ("spans", "revalidated_spans"):
            spans = output.get(key, [])
            if isinstance(spans, list):
                candidates.extend((f"output.{key}[{index}]", span)
                                  for index, span in enumerate(spans))
        # Resolve before adding this action: self/forward references cannot gain authority.
        resolved = [(field, span, self._resolve(span)) for field, span in candidates]
        for field, span, lines in resolved:
            if lines is None:
                continue
            identity = (span["path"], span["file_hash"])
            self.deliveries[(item["call_id"], field, span["file_hash"])] = (
                span["path"], span["start_line"], lines,
            )
            by_line = self.observed[identity]
            for number, line in enumerate(lines, span["start_line"]):
                previous = by_line.get(number)
                if previous is None:
                    by_line[number] = (line, item["call_id"], field)
                elif previous[0] != line:
                    self.conflicts.add((*identity, number))

    def references(self, span: dict[str, Any]) -> list[dict[str, Any]]:
        lines = _lines(span)
        if lines is None:
            return []
        identity = span["path"], span["file_hash"]
        refs: list[dict[str, Any]] = []
        for number, line in enumerate(lines, span["start_line"]):
            prior = self.observed.get(identity, {}).get(number)
            if prior is None or prior[0] != line or (*identity, number) in self.conflicts:
                return []
            _, action_id, field = prior
            if (refs and refs[-1]["action_id"] == action_id and refs[-1]["field"] == field
                    and refs[-1]["end_line"] + 1 == number):
                refs[-1]["end_line"] = number
            else:
                refs.append({"action_id": action_id, "field": field,
                             "start_line": number, "end_line": number})
            if len(refs) > MAX_CONTENT_REFERENCES:
                return []
        return refs


def project_mutation_result(
    result: dict[str, Any], *, history: list[dict[str, Any]] | None = None,
    admission: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Reference unchanged complete lines only at the admitted pre-image coordinates.

    Missing admission/history or incomplete/conflicting delivery keeps the exact body.
    This is presentation, never new source admission or a migration of prior outputs.
    """
    if result.get("tool") != "replace_text":
        return result
    projected = copy.deepcopy(result)
    output = projected.get("output", {})
    output.pop("alternative_requirement_satisfied", None)
    admission = admission or {}
    if (result.get("status") != "succeeded" or not history
            or admission.get("tool") != "replace_text"
            or admission.get("mutation_admitted") is not True
            or admission.get("action_id") != result.get("action_id")
            or admission.get("input_hash") != result.get("input_hash")
            or admission.get("mutation_expected_worktree_diff_hash")
            != output.get("worktree_diff_hash")):
        return projected
    args = admission.get("arguments", {})
    old, new = args.get("old_text"), args.get("new_text")
    anchor = admission.get("mutation_anchor_start_line")
    before_hash = admission.get("mutation_preimage_file_hash")
    after_hash = admission.get("mutation_expected_postimage_file_hash")
    if (not isinstance(old, str) or not isinstance(new, str)
            or not isinstance(before_hash, str) or not isinstance(after_hash, str)
            or type(anchor) is not int or anchor < 1):
        return projected
    delta = new.count("\n") - old.count("\n")
    index = _SourceIndex(history)
    for span in output.get("revalidated_spans", []):
        lines = _lines(span)
        if (lines is None or span.get("path") != args.get("path")
                or span.get("file_hash") != after_hash
                or span.get("source_diff_hash") != output["worktree_diff_hash"]
                or span.get("origin") != "revalidated_after_mutation"):
            continue
        refs: list[dict[str, Any]] = []
        for number, line in enumerate(lines, span["start_line"]):
            source = number if number < anchor else number - delta
            if anchor <= number < anchor + new.count("\n"):
                break  # An inserted/touched line needs its post-image, not old source.
            found = index.references({"path": span["path"], "file_hash": before_hash,
                                      "start_line": source, "end_line": source, "content": line})
            if not found:
                break
            ref = {**found[0], "file_hash": before_hash, "target_start_line": number}
            if (refs and all(refs[-1][key] == ref[key] for key in (
                    "action_id", "field", "file_hash"))
                    and refs[-1]["end_line"] + 1 == source
                    and refs[-1]["target_start_line"]
                    + refs[-1]["end_line"] - refs[-1]["start_line"] + 1 == number):
                refs[-1]["end_line"] = source
            else:
                refs.append(ref)
            if len(refs) > MAX_CONTENT_REFERENCES:
                break
        else:
            alias = {**{key: value for key, value in span.items() if key != "content"},
                     "content_delivery": refs,
                     "content_hash": sha256_bytes("\n".join(lines).encode())}
            if len(canonical_json(alias).encode()) < len(canonical_json(span).encode()):
                span.clear()
                span.update(alias)
    return projected


def reference_native_sources(
    state: dict[str, Any], history: list[dict[str, Any]],
) -> dict[str, Any]:
    """Reference exact current lines, with original inline fallback on missing evidence."""
    index = _SourceIndex(history)

    projected = []
    for span in state.get("source_spans", []):
        references = index.references(span)
        if references:
            projected.append({
                **{key: value for key, value in span.items() if key != "content"},
                "content_delivery": references,
            })
        else:
            projected.append(span)
    return {**state, "source_spans": projected} if "source_spans" in state else state
