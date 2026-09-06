"""Reference source already delivered in the immutable native tool history.

Only the derived current-state projection changes. Source admission, the canonical
context, and original native results retain their complete observed bodies.
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

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


def reference_native_sources(
    state: dict[str, Any], history: list[dict[str, Any]],
) -> dict[str, Any]:
    """Replace a retained body only when every exact current line has a delivery.

    A missing line, old hash, conflicting body or overlarge reference list falls
    back to the original inline span. Never infer a gap or fetch additional source.
    """
    observed: dict[tuple[str, str], dict[int, tuple[str, str, str]]] = defaultdict(dict)
    conflicts: set[tuple[str, str, int]] = set()
    for item in history:
        if item.get("type") != "function_call_output":
            continue
        try:
            result = json.loads(item["output"])
        except (KeyError, TypeError, ValueError):
            continue
        if (
            not isinstance(result, dict) or result.get("status") != "succeeded"
            or result.get("tool") not in {"read_file", "search_files", "replace_text"}
            or result.get("action_id") != item.get("call_id")
            or not isinstance(result.get("output"), dict)
        ):
            continue
        output = result["output"]
        candidates = [("output.mutation_evidence", output.get("mutation_evidence"))]
        for key in ("spans", "revalidated_spans"):
            spans = output.get(key, [])
            if isinstance(spans, list):
                candidates.extend((f"output.{key}[{index}]", span)
                                  for index, span in enumerate(spans))
        for field, span in candidates:
            lines = _lines(span)
            if lines is None:
                continue
            identity = (span["path"], span["file_hash"])
            by_line = observed[identity]
            for number, line in enumerate(lines, span["start_line"]):
                previous = by_line.get(number)
                if previous is None:
                    by_line[number] = (line, item["call_id"], field)
                elif previous[0] != line:
                    conflicts.add((*identity, number))

    projected = []
    for span in state.get("source_spans", []):
        lines = _lines(span)
        references: list[dict[str, Any]] = []
        if lines is not None:
            identity = (span["path"], span["file_hash"])
            by_line = observed.get(identity, {})
            for number, line in enumerate(lines, span["start_line"]):
                prior = by_line.get(number)
                if prior is None or prior[0] != line or (*identity, number) in conflicts:
                    references = []
                    break
                _, action_id, field = prior
                if (references and references[-1]["action_id"] == action_id
                        and references[-1]["field"] == field
                        and references[-1]["end_line"] + 1 == number):
                    references[-1]["end_line"] = number
                else:
                    references.append({
                        "action_id": action_id, "field": field,
                        "start_line": number, "end_line": number,
                    })
                if len(references) > MAX_CONTENT_REFERENCES:
                    references = []
                    break
        if references:
            projected.append({
                **{key: value for key, value in span.items() if key != "content"},
                "content_delivery": references,
            })
        else:
            projected.append(span)
    return {**state, "source_spans": projected} if "source_spans" in state else state
