"""Small advisory after an original observation; no inspection or source authority."""

from __future__ import annotations

from patchloop.dev.contracts import DEV_READ_TOOLS

POLICY = "post-observation-inspection-v1"
RECENT_ACTIONS = 3
SOURCE_REFS = 4
RANGES_PER_SOURCE = 4
QUESTION_CHARS = 320


def contract():
    return {"policy": POLICY, "trigger": "complete-current-original-observation",
            "recent_action_limit": RECENT_ACTIONS, "source_reference_limit": SOURCE_REFS,
            "ranges_per_source_limit": RANGES_PER_SOURCE, "question_chars": QUESTION_CHARS,
            "effect": "advisory-only-no-tool-source-or-completion-authority"}


def _current_observation(events, state):
    diff = state.get("current_diff", {}).get("patch_hash")
    first = (state.get("action_horizon", {}).get("first_observation")
             or state.get("repair_stage", {}).get("first_observation") or {})
    observation = first.get("observation") or {}
    if (not diff or first.get("status") != "observed" or first.get("stale") is not False
            or first.get("evidence_currency") != "current"
            or first.get("candidate_diff_hash") != diff
            or observation.get("status") != "observed" or not observation.get("action_id")):
        return None
    for index, event in enumerate(events):
        if event.get("event_type") != "action_finished":
            continue
        result = event["payload"]["result"]
        if (result.get("action_id") == observation["action_id"]
                and result.get("tool") == "observe_original"
                and result.get("status") == "succeeded"
                and result.get("workspace_diff_hash") == diff
                and result.get("output", {}).get("call_path", {}).get("status") == "complete"):
            return index, first, observation
    return None


def _question(state, latest, diff):
    """An inspection goal may already be answered; do not certify it as still open."""
    if latest:
        intent = latest.get("output", {}).get("inspection_intent") or {}
        text = intent.get("evidence_goal") if intent.get("mode") == "inspect" else None
        if not text:
            ledger = state.get("evidence_ledger") or {}
            retained = ledger.get("latest_inspection_intent") or {}
            if ledger.get("diff_hash") == diff and retained.get("action_id") == latest["action_id"]:
                text = retained.get("evidence_goal")
        if isinstance(text, str) and text.strip():
            return {"source": "inspection_intent.evidence_goal", "action_id": latest["action_id"],
                    "text": text[:QUESTION_CHARS],
                    "omitted_chars": max(0, len(text) - QUESTION_CHARS),
                    "interpretation": "model_authored_unverified", "resolution": "not_assessed"}
    for field in ("working_notes", "repair_intent"):
        text = (state.get(field) or {}).get("open_question")
        if isinstance(text, str) and text.strip():
            return {"source": field + ".open_question", "text": text[:QUESTION_CHARS],
                    "omitted_chars": max(0, len(text) - QUESTION_CHARS),
                    "interpretation": "model_authored_unverified", "resolution": "not_assessed"}
    return None


def _action_ref(result):
    output = result["output"]
    request, omitted = {}, {}
    fields = ("path", "start_line", "end_line") if result["tool"] == "read_file" else (
        "query", "path_glob")
    for key in fields:
        value = output.get(key)
        if isinstance(value, str):
            request[key] = value[:240]
            if len(value) > 240:
                omitted[key] = len(value) - 240
        elif type(value) is int:
            request[key] = value
    return {"action_id": result["action_id"], "tool": result["tool"], "request": request,
            **({"omitted_request_chars": omitted} if omitted else {}),
            "new_covered_line_count": 0, "returned_span_count": len(output.get("spans", [])),
            "truncated": bool(output.get("truncated")), "information_value": "not_assessed"}


def _source_refs(state, preferred_paths):
    """Reference delivered ranges only; navigation headers are not source anchors."""
    groups = {}

    def add(path, file_hash, start, end):
        if (not isinstance(path, str) or not path or len(path) > 500
                or not isinstance(file_hash, str) or not file_hash or len(file_hash) > 100
                or type(start) is not int or type(end) is not int or not 1 <= start <= end):
            return
        groups.setdefault((path, file_hash), []).append([start, end])

    for span in state.get("source_spans", []):
        if "content" in span or span.get("content_delivery"):
            add(span.get("path"), span.get("file_hash"),
                span.get("start_line"), span.get("end_line"))
    # Latest native bodies can be intentionally absent from retained source_spans.
    for result in state.get("latest_tool_results", []):
        if (result.get("tool") in DEV_READ_TOOLS and result.get("status") == "succeeded"
                and result.get("workspace_diff_hash") == state["current_diff"]["patch_hash"]):
            for span in result.get("output", {}).get("spans", []):
                if "content" in span:
                    add(span.get("path"), span.get("file_hash"),
                        span.get("start_line"), span.get("end_line"))
    # Also permit audit reconstruction from the compact view. Do not fetch bodies.
    for source in state.get("current_sources", []):
        for span in source.get("inline_spans", []):
            if "content" in span:
                add(source.get("path"), source.get("file_hash"),
                    span.get("start_line"), span.get("end_line"))
        for fields in source.get("content_delivery", {}).values():
            for ranges in fields.values():
                for start, end in ranges:
                    add(source.get("path"), source.get("file_hash"), start, end)
    priority = {path: index for index, path in enumerate(dict.fromkeys(preferred_paths))}
    ordered = sorted(groups, key=lambda identity: priority.get(identity[0], len(priority)))
    refs = []
    for path, file_hash in ordered[:SOURCE_REFS]:
        merged = []
        for start, end in sorted(groups[path, file_hash]):
            if merged and start <= merged[-1][1] + 1:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        refs.append({"path": path, "file_hash": file_hash, "ranges": merged[:RANGES_PER_SOURCE],
                     "omitted_range_count": max(0, len(merged) - RANGES_PER_SOURCE)})
    return refs, max(0, len(groups) - SOURCE_REFS)


def packet(events, state):
    """Project public receipts before inspection/repair/model-state compaction.

    The caller's validated sources, current observation and optional intent remain
    authoritative. This packet neither removes deliveries nor changes tools,
    edit eligibility, completion credit or any inspection allowance.
    """
    selected = _current_observation(events, state)
    if selected is None:
        return None
    index, first, observation = selected
    diff = first["candidate_diff_hash"]
    inspections = []
    for event in events[index + 1:]:
        if event.get("event_type") != "action_finished":
            continue
        result = event["payload"]["result"]
        if (result.get("tool") in DEV_READ_TOOLS and result.get("status") == "succeeded"
                and result.get("workspace_diff_hash") == diff):
            inspections.append(result)
    recent = [result for result in inspections[-RECENT_ACTIONS:]
              if type(result.get("output", {}).get("evidence_gain", {}).get(
                  "new_covered_line_count")) is int
              and result["output"]["evidence_gain"]["new_covered_line_count"] == 0]
    preferred = [span["path"] for result in reversed(recent)
                 for span in result.get("output", {}).get("spans", []) if "path" in span]
    preferred.extend(candidate["path"] for candidate in observation.get("candidates", [])
                     if "path" in candidate)
    sources, omitted = _source_refs(state, preferred)
    return {
        "policy": POLICY, "advisory_only": True,
        "original_observation": {"action_id": observation["action_id"], "diff_hash": diff,
                                 "call_id": first.get("call_id"), "case_id": first.get("case_id")},
        "recent_no_new_coverage_actions": [_action_ref(result) for result in recent],
        "question_to_reassess": _question(state, inspections[-1] if inspections else None, diff),
        "current_source_refs": sources, "omitted_source_ref_count": omitted,
        "guidance": "Use the completed observation and current candidate source before rereading. "
            "Further inspection should target a concrete remaining question or missing exact "
            "anchor. Zero new covered lines does not determine semantic information value. "
            "This advisory changes no offered action or source/edit eligibility.",
    }
