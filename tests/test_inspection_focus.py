"""Pure public-context advisory controls; no target, network or filesystem execution."""

import copy
import json

import pytest

from patchloop.dev import inspection_focus

DIFF = "sha256:current"
PATH = "pkg/resolver.py"
HASH = "sha256:source"


def finished(result):
    return {"event_type": "action_finished", "payload": {"result": result}}


def inspection(action_id, *, tool="read_file", gain=0, goal="Which branch handles the input?",
               path=PATH, spans=None, diff=DIFF, status="succeeded"):
    spans = ([{"path": path, "file_hash": HASH, "start_line": 10, "end_line": 20,
               "content": "Already delivered source body"}] if spans is None else spans)
    return finished({
        "action_id": action_id, "tool": tool, "status": status, "workspace_diff_hash": diff,
        "output": {"path": path, "start_line": 10, "end_line": 20,
                   "query": "caller(", "path_glob": "pkg/**/*.py", "spans": spans,
                   "evidence_gain": {"new_covered_line_count": gain},
                   "inspection_intent": {"mode": "inspect", "evidence_goal": goal},
                   "truncated": False},
    })


def context():
    events = [inspection("before-observation"), finished({
        "action_id": "observation", "tool": "observe_original", "status": "succeeded",
        "workspace_diff_hash": DIFF, "output": {"call_path": {"status": "complete"}},
    })]
    state = {
        "current_diff": {"patch_hash": DIFF},
        "action_horizon": {"first_observation": {
            "status": "observed", "stale": False, "evidence_currency": "current",
            "candidate_diff_hash": DIFF, "call_id": "call-1", "case_id": "case",
            "observation": {"action_id": "observation", "status": "observed",
                            "candidates": [{"path": PATH, "file_hash": HASH}]},
        }},
        "source_spans": [{"span_id": "source-1", "path": PATH, "file_hash": HASH,
                          "start_line": 1, "end_line": 30, "content": "Exact editable source"}],
        "observed_source_index": {"entries": [{"path": "pkg/header_only.py",
            "file_hash": "header-hash", "kind": "function", "name": "f", "start_line": 1}]},
        "mutation_readiness": {"current_anchor_evidence_paths": [PATH]},
        "available_tool_names": ["read_file", "search_files", "replace_text", "stop_task"],
        "remaining_budget": {"tool_actions": 50}, "working_notes": {"open_question": None},
    }
    return events, state


def test_observation_and_delivered_source_are_referenced_without_new_requirements():
    events, state = context()
    before = copy.deepcopy((events, state))
    packet = inspection_focus.packet(events, state)
    assert packet["original_observation"] == {
        "action_id": "observation", "diff_hash": DIFF, "call_id": "call-1", "case_id": "case"}
    assert packet["current_source_refs"] == [{
        "path": PATH, "file_hash": HASH, "ranges": [[1, 30]], "omitted_range_count": 0}]
    assert packet["recent_no_new_coverage_actions"] == []
    assert packet["question_to_reassess"] is None and packet["advisory_only"]
    assert "Exact editable source" not in json.dumps(packet)
    assert "header_only" not in json.dumps(packet)
    assert not {"blocked", "required_action", "allowed_tools", "inspection_limit"} & packet.keys()
    assert (events, state) == before
    assert inspection_focus.packet(events, {**state, "inspection_focus": packet}) == packet


def test_only_current_post_observation_receipts_supply_coverage_and_latest_goal():
    events, state = context()
    events.extend([inspection("repeat"), inspection("old-diff", diff="other", goal="Old goal"),
                   inspection("failed", status="failed", goal="Failed request"),
                   inspection("new-source", gain=3, goal="Find the upstream caller.")])
    packet = inspection_focus.packet(events, state)
    assert [row["action_id"] for row in packet["recent_no_new_coverage_actions"]] == ["repeat"]
    assert packet["question_to_reassess"] == {
        "source": "inspection_intent.evidence_goal", "action_id": "new-source",
        "text": "Find the upstream caller.", "omitted_chars": 0,
        "interpretation": "model_authored_unverified", "resolution": "not_assessed"}
    assert "Old goal" not in json.dumps(packet) and "Failed request" not in json.dumps(packet)


def test_many_rereads_bound_the_advisory_without_removing_tools_or_editable_anchors():
    events, state = context()
    events.extend(inspection(f"read-{i}") for i in range(27))
    before = copy.deepcopy(state)
    packet = inspection_focus.packet(events, state)
    assert [row["action_id"] for row in packet["recent_no_new_coverage_actions"]] == [
        "read-24", "read-25", "read-26"]
    assert all(row["information_value"] == "not_assessed"
               for row in packet["recent_no_new_coverage_actions"])
    assert state == before
    assert "missing exact anchor" in packet["guidance"]


def test_negative_search_retains_scope_and_question_without_claiming_no_useful_information():
    events, state = context()
    events.append(inspection("negative", tool="search_files", spans=[],
                             goal="Does the upstream caller live in this search scope?"))
    packet = inspection_focus.packet(events, state)
    action = packet["recent_no_new_coverage_actions"][0]
    assert action["returned_span_count"] == 0 and action["new_covered_line_count"] == 0
    assert action["request"] == {"query": "caller(", "path_glob": "pkg/**/*.py"}
    assert action["information_value"] == "not_assessed"
    assert "does not determine semantic information value" in packet["guidance"]
    assert packet["question_to_reassess"]["resolution"] == "not_assessed"


@pytest.mark.parametrize("gain", [None, False, "0"])
def test_missing_or_noninteger_coverage_is_not_inferred_from_stagnation_flags(gain):
    events, state = context()
    row = inspection("unmeasured", gain=gain)
    row["payload"]["result"]["output"]["evidence_gain"]["marginal_evidence_gain"] = False
    events.append(row)
    assert inspection_focus.packet(events, state)["recent_no_new_coverage_actions"] == []


@pytest.mark.parametrize("change", ["status", "stale", "currency", "candidate", "current_diff",
    "observation_status", "missing_action", "receipt_diff", "receipt_status", "trace_unknown"])
def test_unobserved_or_stale_observation_never_creates_the_packet(change):
    events, state = context()
    first = state["action_horizon"]["first_observation"]
    result = events[1]["payload"]["result"]
    if change == "status":
        first["status"] = "incomplete"
    elif change == "stale":
        first["stale"] = True
    elif change == "currency":
        first["evidence_currency"] = "historical"
    elif change == "candidate":
        first["candidate_diff_hash"] = "other"
    elif change == "current_diff":
        state["current_diff"]["patch_hash"] = "other"
    elif change == "observation_status":
        first["observation"]["status"] = "insufficient"
    elif change == "missing_action":
        first["observation"]["action_id"] = "absent"
    elif change == "receipt_diff":
        result["workspace_diff_hash"] = "other"
    elif change == "receipt_status":
        result["status"] = "failed"
    else:
        result["output"]["call_path"]["status"] = "unknown"
    assert inspection_focus.packet(events, state) is None


def test_current_source_refs_never_revive_a_dropped_body_or_a_navigation_header():
    events, state = context()
    events.append(inspection("repeat"))
    state["source_spans"] = []
    packet = inspection_focus.packet(events, state)
    assert len(packet["recent_no_new_coverage_actions"]) == 1
    assert packet["current_source_refs"] == []
    assert "Already delivered source body" not in json.dumps(packet)
    assert "missing exact anchor" in packet["guidance"]


def test_latest_current_native_read_body_is_a_reference_without_refetching_or_anchor_loss():
    events, state = context()
    latest = inspection("latest")
    events.append(latest)
    state["source_spans"] = []
    state["latest_tool_results"] = [latest["payload"]["result"]]
    before = copy.deepcopy(state)
    packet = inspection_focus.packet(events, state)
    assert packet["current_source_refs"] == [{
        "path": PATH, "file_hash": HASH, "ranges": [[10, 20]], "omitted_range_count": 0}]
    assert state == before
    state["latest_tool_results"][0]["workspace_diff_hash"] = "old"
    assert inspection_focus.packet(events, state)["current_source_refs"] == []


def test_compact_native_and_inline_source_ranges_preserve_gaps_and_current_hashes():
    events, state = context()
    state["repair_stage"] = {"first_observation": state.pop("action_horizon")["first_observation"]}
    state.pop("source_spans")
    state["current_sources"] = [{"path": PATH, "file_hash": HASH,
        "content_delivery": {"read-1": {"output.spans[0]": [[1, 5], [12, 20]]}},
        "inline_spans": [{"start_line": 6, "end_line": 8, "content": "Exact body"}],
        "headers": [{"kind": "function", "name": "unseen", "start_line": 9}]},
        {"path": "header_only.py", "file_hash": "h", "headers": [{"start_line": 1}]}]
    packet = inspection_focus.packet(events, state)
    assert packet["current_source_refs"] == [{
        "path": PATH, "file_hash": HASH, "ranges": [[1, 8], [12, 20]], "omitted_range_count": 0}]


def test_question_fallback_requires_a_real_current_inspection_or_existing_open_question():
    events, state = context()
    state["evidence_ledger"] = {"diff_hash": DIFF, "latest_inspection_intent": {
        "action_id": "invented", "evidence_goal": "Never revive this question"}}
    assert inspection_focus.packet(events, state)["question_to_reassess"] is None
    state["working_notes"]["open_question"] = "Which caller supplies the path?"
    packet = inspection_focus.packet(events, state)
    assert packet["question_to_reassess"]["source"] == "working_notes.open_question"
    assert packet["question_to_reassess"]["resolution"] == "not_assessed"
    events.append(inspection("latest", goal=None))
    state["evidence_ledger"]["latest_inspection_intent"]["action_id"] = "latest"
    state["evidence_ledger"]["latest_inspection_intent"]["evidence_goal"] = "Retained actual goal"
    assert inspection_focus.packet(events, state)["question_to_reassess"]["text"] == (
        "Retained actual goal")
    state["evidence_ledger"]["diff_hash"] = "old"
    assert inspection_focus.packet(events, state)["question_to_reassess"]["source"] == (
        "working_notes.open_question")


def test_newer_inspection_does_not_revive_an_older_question_and_recent_window_can_move_on():
    events, state = context()
    events.append(inspection("old", goal="Earlier question"))
    events.extend(inspection(f"useful-{i}", gain=5, goal=None) for i in range(3))
    packet = inspection_focus.packet(events, state)
    assert packet["recent_no_new_coverage_actions"] == []
    assert packet["question_to_reassess"] is None


def test_packet_is_bounded_and_never_reads_provider_payloads_or_copies_source_bodies():
    class ForbiddenPayload(dict):
        def __getitem__(self, key):
            raise AssertionError("provider payload is outside the projection")

    events, state = context()
    events.append({"event_type": "provider_call_finished", "payload": ForbiddenPayload()})
    state["source_spans"] *= 10
    for i in range(8):
        state["source_spans"].extend({"path": f"pkg/file{i}.py", "file_hash": f"hash-{i}",
            "start_line": line, "end_line": line, "content": "large source body" * 1000}
            for line in range(1, 14, 2))
    for i in range(3):
        row = inspection(f"search-{i}", tool="search_files", goal="question" * 1000)
        row["payload"]["result"]["output"]["query"] = "query" * 1000
        events.append(row)
    packet = inspection_focus.packet(events, state)
    assert len(packet["current_source_refs"]) == inspection_focus.SOURCE_REFS
    assert packet["omitted_source_ref_count"] == 5
    assert packet["current_source_refs"][1]["omitted_range_count"] == 3
    assert len(packet["question_to_reassess"]["text"]) == inspection_focus.QUESTION_CHARS
    assert packet["question_to_reassess"]["omitted_chars"] > 0
    assert len(json.dumps(packet)) < 4500
    assert "large source body" not in json.dumps(packet)
    assert inspection_focus.packet([], {}) is None
    assert inspection_focus.contract()["policy"] == packet["policy"]
