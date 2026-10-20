"""Declared public evidence: identity and delivery, never semantic certification."""
from __future__ import annotations

import copy
import json
import re

from pydantic import ValidationError

from patchloop.dev.context import spans_cover_range
from patchloop.dev.native_sources import PUBLIC_EVIDENCE_KIND
from patchloop.dev.public_history import SnapshotRules
from patchloop.dev.working_notes import OpenQuestion, SourceNoteEvidence
from patchloop.util import canonical_json, sha256_bytes, sha256_json


def execution_flags(result):
    return {k: result["output"][k] for k in (
        "passed", "exit_code", "status", "truncated", "timed_out", "cleanup_failed",
        "deadline_exhausted",
    ) if k in result.get("output", {})}


def bind_question(raw, spans, results, *, diff_hash=None):
    """Return an independently validated question; no current-batch evidence."""
    if raw is None:
        return None, None
    # Read old durable/synthetic annotations without advertising the old shape.
    if isinstance(raw, str) and 0 < len(raw) <= 500:
        return raw, None
    try:
        question = OpenQuestion.model_validate(raw)
    except ValidationError:
        return None, "invalid_question_shape"
    bound = []
    for ref in question.evidence:
        if isinstance(ref, SourceNoteEvidence):
            matches = [s for s in spans if s["path"] == ref.path]
            if ref.end_line < ref.start_line or not spans_cover_range(
                matches, ref.start_line, ref.end_line,
            ):
                return None, "question_source_not_observed"
            rows = {s["start_line"] + i: line for s in matches
                    for i, line in enumerate(s["content"].split("\n"))}
            body = "\n".join(rows[n] for n in range(ref.start_line, ref.end_line + 1))
            bound.append({**ref.model_dump(exclude_none=True), "file_hash": matches[0]["file_hash"],
                          "content_hash": sha256_bytes(body.encode())})
        else:
            result = results.get(ref.action_id)
            if result is None:
                return None, "question_result_not_observed"
            if ref.role and result["tool"] not in {
                "run_check", "run_tests", "run_probe", "search_history",
            }:
                return None, "question_source_requires_range"
            bound.append({**ref.model_dump(exclude_none=True), "tool": result["tool"],
                          "input_hash": result["input_hash"],
                          "execution": execution_flags(result),
                          "diff_hash": (result.get("output", {}).get("worktree_diff_hash")
                                        or result.get("output", {}).get("diff_hash")
                                        or result.get("workspace_diff_hash"))})
    declaration = {"text": question.text, "evidence": bound}
    if diff_hash is not None and all(ref.role for ref in question.evidence):
        declaration["declared_diff_hash"] = diff_hash
    return {**declaration, "revision_hash": sha256_json(declaration)}, None


def priority_status(question, diff_hash):
    """Diff scope only; eligibility never certifies relevance or minimality."""
    if not isinstance(question, dict) or question.get("declared_diff_hash") is None:
        return "unscoped"
    if diff_hash is None or question["declared_diff_hash"] != diff_hash:
        return "needs_refresh"
    return "eligible"


def refresh_question(question, bodies, read_source):
    """Exact unique-body rebind, or persistent expiry, without changing the question."""
    if not isinstance(question, dict):
        return question
    question = copy.deepcopy(question)
    for index, ref in enumerate(question["evidence"]):
        if ref["kind"] != "source" or ref.get("unavailable_reason"):
            continue
        source = read_source(ref["path"])
        if source is None:
            ref["unavailable_reason"] = "source_unavailable"
            continue
        text, file_hash = source
        if file_hash == ref["file_hash"]:
            continue
        body = bodies[index] if index < len(bodies) else None
        positions = [] if not body else [m.start() for m in re.finditer(
            f"(?={re.escape(body)})", text,
        ) if (m.start() == 0 or text[m.start() - 1] == "\n") and (
            m.start() + len(body) == len(text) or text[m.start() + len(body)] == "\n")]
        if len(positions) != 1:
            ref["unavailable_reason"] = "source_changed_or_ambiguous"
            continue
        ref.update(file_hash=file_hash, start_line=text[:positions[0]].count("\n") + 1)
        ref["end_line"] = ref["start_line"] + body.count("\n")
    return question


def source_references(question, *, diff_hash=None):
    """Only current declarations with explicit source ranges receive extra priority."""
    if priority_status(question, diff_hash) != "eligible":
        return []
    return [ref for ref in question["evidence"] if ref["kind"] == "source"]


def optional_exchanges(question, events, excluded_ids=(), *, diff_hash=None):
    """Retain the question's verification/search results, within its two references."""
    from patchloop.dev.probe_observation import project_probe_result

    if priority_status(question, diff_hash) != "eligible":
        return []
    wanted = {r["action_id"] for r in question.get("evidence", [])
              if r["kind"] == "tool_result"} if isinstance(question, dict) else set()
    wanted -= set(excluded_ids)
    results = {e["payload"]["result"]["action_id"]: e["payload"]["result"]
               for e in events if e["event_type"] == "action_finished"}
    calls = {c["action_id"]: c for e in events if e["event_type"] == "turn_decision_recorded"
             for c in e["payload"].get("tool_calls", [])}
    quoted = []
    for action_id in sorted(wanted):
        result, call = results.get(action_id), calls.get(action_id)
        if not result or not call or result["tool"] not in {
            "run_check", "run_tests", "run_probe", "search_history",
        }:
            continue
        quoted.extend([
            {"type": "function_call", "call_id": action_id, "name": call["name"],
             "arguments": canonical_json(call["arguments"])},
            {"type": "function_call_output", "call_id": action_id,
             "output": canonical_json(project_probe_result(result))},
        ])
    return quoted


def project_interpretations(view, history, *, archive_kind=None):
    """Resolve actual input bodies before calling evidence delivered; never certify claims."""
    if isinstance(view.get("working_plan"), dict):
        view["working_plan"]["role"] = "proposed_remaining_work"
    notes = view.get("working_notes")
    if not isinstance(notes, dict):
        return
    question = notes.get("open_question")
    owners = [*notes.get("findings", []),
              question if isinstance(question, dict) else {},
              *(c.get("decision") or {} for c in notes.get("verification", {}).get("items", []))]
    facts, exchanges = {}, {}
    if any(owner.get("evidence") for owner in owners):
        rules = SnapshotRules("harness_current_state", archive_kind or PUBLIC_EVIDENCE_KIND, "")
        facts, exchanges, _ = rules.inventory([
            *history, {"role": "developer", "content": canonical_json({
                "kind": "harness_current_state", "state": view})},
        ])
    results = {i["call_id"]: json.loads(i["output"]) for i in exchanges.values()
               if i.get("type") == "function_call_output"}
    diff = view.get("current_diff", {}).get("patch_hash")

    def evidence(ref):
        item = copy.deepcopy(ref)
        if ref.get("kind") == "source":
            present = {n for n in range(ref["start_line"], ref["end_line"] + 1)
                       if (ref["path"], ref["file_hash"], n) in facts}
            missing = []
            for n in range(ref["start_line"], ref["end_line"] + 1):
                if n in present:
                    continue
                if missing and missing[-1][1] + 1 == n:
                    missing[-1][1] = n
                else:
                    missing.append([n, n])
            item.update(evidence_delivery="incomplete" if missing else "complete",
                        missing_ranges=missing,
                        evidence_currency="unavailable" if ref.get("unavailable_reason")
                        else ref.get("evidence_currency", "current"))
        else:
            result = results.get(ref.get("action_id"))
            matches = result and result.get("input_hash") == ref.get("input_hash")
            item.pop("result_delivery", None)
            item.update(evidence_delivery="complete" if matches else "incomplete",
                        evidence_currency="historical" if ref.get("tool") == "search_history"
                        else "unknown" if ref.get("diff_hash") is None
                        else "current" if ref["diff_hash"] == diff else "historical")
            if matches:
                item["result_delivery"] = {"action_id": ref["action_id"],
                                           "field": "function_call_output"}
                item["execution"] = execution_flags(result)
            item["behavior_coverage"] = "not_assessed"
        return item

    def delivery(refs):
        return ("complete" if refs and all(r["evidence_delivery"] == "complete" for r in refs)
                else "incomplete" if refs else "not_requested")

    if isinstance(notes.get("interpretation"), str):
        notes["interpretation"] = notes["interpretation"].replace(
            "status=current", "evidence_currency=current")
    for note in notes.get("findings", []):
        note["evidence"] = [evidence(r) for r in note.get("evidence", [])]
        note["evidence_delivery"] = delivery(note["evidence"])
        note["evidence_currency"] = note.pop("status", note.get("evidence_currency", "unknown"))
        note["model_interpretation"] = note.pop("statement", note.get("model_interpretation", ""))
    if isinstance(question, dict):
        question["priority_status"] = priority_status(question, diff)
        question["evidence"] = [evidence(r) for r in question["evidence"]]
        question["evidence_delivery"] = delivery(question["evidence"])
    for concern in notes.get("verification", {}).get("items", []):
        concern["status"] = {"resolved": "closed_by_model", "dismissed": "dismissed_by_model"}.get(
            concern.get("status"), concern.get("status"))
        concern["behavior_coverage"] = "not_assessed"
        decision = concern.get("decision")
        if isinstance(decision, dict):
            decision["outcome"] = {"resolved": "closed_by_model",
                                   "dismissed": "dismissed_by_model"}.get(
                decision.get("outcome"), decision.get("outcome"))
            if decision.get("evidence"):
                decision["evidence"] = evidence({"kind": "tool_result", **decision["evidence"]})
