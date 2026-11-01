"""Small receipt/source controls; no model, target process, container or network."""

import copy
import json

import pytest
from test_observation_correction import action

from patchloop.dev import first_observation as observation
from patchloop.errors import ContractError
from patchloop.sandbox import call_path_trace
from patchloop.util import sha256_bytes, sha256_json

SOURCE = ("def first(value, *, flag=False):\n    return value\n\n"
          "def second(value):\n    return value\n")


def selection(prediction="entered"):
    return {"hypothesis": "The original caller reaches first before the failure.",
            "candidates": [{"origin": "workspace", "path": "sample.py", "function": "first",
                            "prediction": prediction}]}


def baseline():
    events = action(status="consistent")
    binding = events[-1]["payload"]["result"]["output"]["reproduction"]["binding"]
    completion = {"baseline_failure_case_ids": [binding["case_id"]], "cases": [{
        "case_id": binding["case_id"], "root_action_id": "baseline", "replayable": True,
        "evidence": {"status": "REFUTED"}}]}
    return events, completion


def preflight(workspace, request, *, deadline=None, line_changes=None):
    del deadline
    return call_path_trace.bind_request(request, workspace, line_changes=line_changes)


def admit(tmp_path, raw=None):
    (tmp_path / "sample.py").write_text(SOURCE, encoding="utf-8")
    events, completion = baseline()
    state = observation.review(events, observation.EMPTY_DIFF, completion)
    raw = raw or selection()
    admission = observation.prepare(raw, state, tmp_path, preflight)
    execution = {"action_id": "observe-1", "run_id": "run", "tool": "observe_original"}
    start = {"action_id": "observe-1", "tool": observation.TOOL_NAME,
             "arguments": copy.deepcopy(raw), "execution_identity": execution,
             "input_hash": sha256_json({"tool": observation.TOOL_NAME, "arguments": raw}),
             "first_observation_link": observation.link(state), "first_observation": admission,
             "probe_request": {"status": "accepted"}}
    events.append({"event_type": "action_started", "payload": start})
    return events, completion, start


def execute_receipt(tmp_path, raw=None, *, entered=True, raised=False):
    events, completion, start = admit(tmp_path, raw)
    request = start["first_observation"]["call_path"]
    snapshot_hash = sha256_bytes(SOURCE.encode())
    bound = call_path_trace.bind_request(
        request, tmp_path, snapshot_hash=snapshot_hash,
        execution_identity_hash=sha256_json(start["execution_identity"]))
    rows = []
    for index, target in enumerate([bound["focus"], *bound["watches"]]):
        row_events = []
        if entered:
            row_events = [{"event": kind, "line": target["def_line"], "parent_index": None,
                           "values": {}, **({"exception_type": "ValueError"}
                                            if kind == "exception" else {})}
                          for kind in (["call", "exception", "return"] if raised
                                       else ["call", "return"])]
        rows.append({"index": index, "entries": int(entered), "line_hits": [],
                     "events": row_events})
    feedback = call_path_trace.public_feedback(bound, {"request_hash": bound["request_hash"],
        "scope": "selected_call", "status": "complete", "reason": None, "rows": rows})
    feedback.update(raw_request_hash=sha256_json(request),
                    candidate_diff_hash=observation.EMPTY_DIFF)
    result = copy.deepcopy(events[1]["payload"]["result"])
    result.update(action_id=start["action_id"], tool=observation.TOOL_NAME,
                  input_hash=start["input_hash"])
    result["output"].update(call_path=feedback, snapshot_hash=snapshot_hash,
                             execution_source_hash="execution-source")
    events.extend([
        {"event_type": "probe_execution_started", "payload": {
            "action_id": start["action_id"], "call_path_request_hash": sha256_json(request),
            "execution_source_hash": "execution-source"}},
        {"event_type": "action_finished", "payload": {
            "action_id": start["action_id"], "result": result}},
    ])
    return events, completion


def test_small_selection_contract_cannot_replace_original_caller_or_add_annotations(tmp_path):
    schema = observation.schema()
    assert schema["name"] == "observe_original" and schema["strict"]
    assert len(json.dumps(schema, separators=(",", ":"))) < 2000
    raw = selection()
    events, completion, start = admit(tmp_path, raw)
    admitted = start["first_observation"]
    canonical = observation.arguments(raw, admitted)
    assert canonical == {"question": None, "python_source": None, "purpose": None,
                         "replay_action_id": "baseline", "call_path": admitted["call_path"]}
    assert admitted["call_path"]["scope"] == "selected_call"
    assert admitted["call_path"]["call_id"] == "call-1"
    assert admitted["call_path"]["watches"][0]["fields"] == ["value", "flag"]
    assert admitted["call_path"]["watches"][0]["lines"] == [2]
    assert raw == selection()
    canonical["call_path"]["watches"][0]["fields"].clear()
    assert admitted["call_path"]["watches"][0]["fields"] == ["value", "flag"]
    with pytest.raises(ContractError, match="differs"):
        observation.arguments(selection("not_entered"), admitted)
    pending = observation.review(events, observation.EMPTY_DIFF, completion)
    assert pending["execution_reserved"] and not pending["available"] and not pending["blocked"]


@pytest.mark.parametrize("change", ["extra", "annotation", "hash", "fields", "escape", "bad_name",
                                  "empty", "three", "duplicate", "prediction", "long_hypothesis"])
def test_invalid_selections_reject_before_source_binding(change):
    raw = selection()
    if change in {"extra", "annotation"}:
        raw["python_source" if change == "extra" else "turn_decision"] = None
    elif change in {"hash", "fields"}:
        raw["candidates"][0]["file_hash" if change == "hash" else "fields"] = []
    elif change == "escape":
        raw["candidates"][0]["path"] = "../secret.py"
    elif change == "bad_name":
        raw["candidates"][0]["function"] = "call()"
    elif change in {"empty", "three", "duplicate"}:
        raw["candidates"] *= {"empty": 0, "three": 3, "duplicate": 2}[change]
    elif change == "prediction":
        raw["candidates"][0]["prediction"] = "fixed"
    else:
        raw["hypothesis"] = "h" * 1001
    with pytest.raises(ContractError) as caught:
        observation.validate_selection(raw)
    assert caught.value.details["invalid_fields"]


def test_two_functions_and_dependency_parameters_are_host_derived(tmp_path):
    raw = selection()
    raw["candidates"].append({"origin": "dependency", "path": "dep.py", "function": "Caller.run",
                               "prediction": "not_entered"})
    dependency = tmp_path / "dependency"
    dependency.mkdir()
    source = (b"class Caller:\n    def run(self, path, *args, mode=None, **kwargs):\n"
              b"        return path\n")
    (dependency / "dep.py").write_bytes(source)

    def bind(workspace, request, *, deadline=None, line_changes=None):
        del deadline
        return call_path_trace.bind_request(request, workspace, dependency_root=dependency,
            dependency_files={"dep.py": sha256_bytes(source)}, line_changes=line_changes)

    (tmp_path / "sample.py").write_text(SOURCE, encoding="utf-8")
    events, completion = baseline()
    state = observation.review(events, observation.EMPTY_DIFF, completion)
    admitted = observation.prepare(raw, state, tmp_path, bind)
    assert admitted["call_path"]["watches"][1]["fields"] == [
        "self", "path", "mode", "args", "kwargs"]
    assert admitted["call_path"]["watches"][1]["lines"] == [3]
    assert admitted["call_path"]["focus"]["function"] == "first"
    raw["candidates"][1]["function"] = "missing"
    with pytest.raises(ContractError, match="source binding"):
        observation.prepare(raw, state, tmp_path, bind)


@pytest.mark.parametrize("change", ["no_case", "not_replayable", "conflict", "judgment", "no_rules",
                                  "setup", "different_diff", "edited", "both_fail", "no_control",
                                  "same_call", "unobserved_control", "misjudged_control"])
def test_only_acquired_healthy_base_failure_offers_observation(change):
    events, completion = baseline()
    current = observation.EMPTY_DIFF
    assert observation.review(events, current, completion)["available"]
    if change == "no_case":
        completion["baseline_failure_case_ids"] = []
    elif change == "not_replayable":
        completion["cases"][0]["replayable"] = False
    elif change == "conflict":
        completion["cases"][0]["evidence"]["status"] = "CONFLICT"
    elif change == "judgment":
        events[1]["payload"]["result"]["output"]["reproduction"]["judgment"]["status"] = "unknown"
    elif change == "no_rules":
        events[1]["payload"]["result"]["output"]["reproduction"]["binding"]["definition"][
            "diagnostic_rules"] = []
    elif change == "setup":
        events[1]["payload"]["result"]["output"]["setup_checks"] = {"status": "failed"}
    elif change == "different_diff":
        current = "candidate"
    elif change == "edited":
        events.append({"event_type": "action_finished", "payload": {"result": {
            "action_id": "edit", "tool": "replace_text", "status": "succeeded"}}})
    else:
        repro = events[1]["payload"]["result"]["output"]["reproduction"]
        definition = repro["binding"]["definition"]
        if change == "both_fail":
            repro["observed_json"] = definition["reported_failure_json"] = (
                '{"bug":true,"control":true}')
            repro["call_observation"]["calls"][1]["capture"]["stdout"] = "F0010"
        elif change == "no_control":
            definition["diagnostic_rules"] = definition["diagnostic_rules"][:1]
        elif change == "same_call":
            definition["diagnostic_rules"][1]["call_id"] = "call-1"
        elif change == "unobserved_control":
            repro["call_observation"]["calls"][1]["capture"]["status"] = "truncated"
        else:
            repro["call_observation"]["calls"][1]["capture"]["stdout"] = "F0010"
    state = observation.review(events, current, completion)
    assert state["status"] == "not_needed" and not state["available"] and not state["blocked"]


def test_rejected_requests_and_pending_or_unknown_execution_cannot_refill_allowance(tmp_path):
    events, completion = baseline()
    identity = observation.link(observation.review(events, observation.EMPTY_DIFF, completion))
    for index in range(2):
        events.append({"event_type": "action_started", "payload": {
            "action_id": f"reject-{index}", "tool": observation.TOOL_NAME,
            "first_observation_link": identity, "probe_request": {"status": "rejected"}}})
        view = observation.review(events, observation.EMPTY_DIFF, completion)
        assert view["rejected_requests"] == index + 1
        assert view["available"] is (index == 0)
        assert not view["execution_attempted"] and not view["execution_reserved"]
    assert view["status"] == "incomplete" and not view["blocked"]
    events, completion, start = admit(tmp_path)
    unchanged = copy.deepcopy(events)
    pending = observation.review(events, observation.EMPTY_DIFF, completion)
    assert pending["status"] == "incomplete" and pending["execution_reserved"]
    assert not pending["execution_attempted"] and not pending["available"]
    assert events == unchanged
    events.append({"event_type": "probe_execution_started", "payload": {
        "action_id": start["action_id"]}})
    unknown = observation.review(copy.deepcopy(events), observation.EMPTY_DIFF, completion)
    assert unknown["execution_attempted"] and unknown["observation"]["status"] == "insufficient"
    assert all(row["status"] == "insufficient" for row in unknown["observation"]["candidates"])
    with pytest.raises(ContractError, match="not available"):
        observation.prepare(selection(), unknown, tmp_path, preflight)


@pytest.mark.parametrize("prediction,entered,raised,expected", [
    ("entered", True, False, "prediction_matched"),
    ("entered", False, False, "prediction_contradicted"),
    ("not_entered", False, False, "prediction_matched"),
    ("not_entered", True, False, "prediction_contradicted"),
    ("returned", True, False, "prediction_matched"),
    ("returned", False, False, "prediction_contradicted"),
    ("raised", True, True, "prediction_matched"),
    ("raised", True, False, "prediction_contradicted"),
])
def test_prediction_uses_only_complete_same_original_trace(
    tmp_path, prediction, entered, raised, expected,
):
    events, completion = execute_receipt(
        tmp_path, selection(prediction), entered=entered, raised=raised)
    unchanged = copy.deepcopy(events)
    state = observation.review(events, observation.EMPTY_DIFF, completion)
    assert state["status"] == "observed" and not state["available"] and not state["blocked"]
    assert state["observation"]["candidates"][0]["status"] == expected
    assert state["observation"]["hypothesis"] == selection()["hypothesis"]
    assert state["repair_correctness"] == "unverified" and events == unchanged
    assert observation.review(copy.deepcopy(events), observation.EMPTY_DIFF, completion) == state


@pytest.mark.parametrize("prediction,event", [("returned", "return"), ("raised", "exception")])
@pytest.mark.parametrize("occurred", [False, True])
def test_sampled_details_use_complete_event_counts_for_predictions(
    tmp_path, prediction, event, occurred,
):
    events, completion = execute_receipt(tmp_path, selection(prediction))
    trace = events[-1]["payload"]["result"]["output"]["call_path"]
    for row in [trace["focus"], *trace["watches"]]:
        row["event_counts"] = {"call": 1, "line": 0, "return": 0, "exception": 0}
        row["event_counts"][event] = int(occurred)
        row["events"] = []  # No detailed sample is retained for this target.
    trace["collection"] = {
        "policy": "entry-and-detail-v2",
        "coverage": {"status": "complete", "call_events": 1, "call_limit": 200_000,
                     "selected_events": 2, "selected_limit": 200_000},
        "details": {"status": "sampled", "record_limit": 48, "value_byte_limit": 12_000,
                    "retained_records": 0, "retained_value_bytes": 0,
                    "coalesced_events": 0, "omitted_events": 2},
        "limits": [],
    }
    before = copy.deepcopy(events)
    state = observation.review(events, observation.EMPTY_DIFF, completion)
    candidate = state["observation"]["candidates"][0]
    assert state["status"] == "observed" and not state["available"]
    assert candidate["status"] == ("prediction_matched" if occurred else "prediction_contradicted")
    assert candidate["entry_exit_events"] == []
    assert candidate["event_counts"] == trace["watches"][0]["event_counts"]
    assert state["observation"]["collection"] == trace["collection"]
    assert events == before
    trace.update(status="unknown", reason="collector_truncated")
    incomplete = observation.review(events, observation.EMPTY_DIFF, completion)
    assert incomplete["status"] == "incomplete" and not incomplete["available"]
    assert incomplete["observation"]["candidates"][0]["status"] == "insufficient"


@pytest.mark.parametrize("invalid", [None, {}, {"call": 1, "line": 0, "return": True,
                                               "exception": 0},
                                   {"call": 1, "line": 0, "return": -1, "exception": 0},
                                   {"call": 2, "line": 0, "return": 1, "exception": 0}])
def test_invalid_aggregate_events_cannot_fall_back_to_sampled_details(tmp_path, invalid):
    events, completion = execute_receipt(tmp_path, selection("returned"))
    trace = events[-1]["payload"]["result"]["output"]["call_path"]
    assert any(event["event"] == "return" for event in trace["watches"][0]["events"])
    trace["watches"][0]["event_counts"] = invalid
    state = observation.review(events, observation.EMPTY_DIFF, completion)
    assert state["status"] == "incomplete" and not state["available"]
    assert state["observation"]["candidates"][0]["status"] == "insufficient"


@pytest.mark.parametrize("change", ["unknown_no_hit", "setup", "new_outcome", "control", "rules",
                                  "program", "arguments", "environment", "source", "snapshot",
                                  "execution", "request", "dispatch", "execution_source", "scope",
                                  "diff", "selection", "lines"])
def test_changed_or_incomplete_evidence_cannot_support_or_refute_prediction(tmp_path, change):
    events, completion = execute_receipt(tmp_path, selection("not_entered"), entered=False)
    output = events[-1]["payload"]["result"]["output"]
    trace, repro = output["call_path"], output["reproduction"]
    if change == "unknown_no_hit":
        trace.update(status="unknown", reason="collector_truncated")
    elif change == "setup":
        output["setup_checks"] = {"status": "failed"}
    elif change == "new_outcome":
        repro.update(comparison="matched", declared_failure_comparison="mismatched")
    elif change == "control":
        repro["observed_json"] = '{"bug":true,"control":true}'
    elif change == "rules":
        repro["binding"]["definition"]["diagnostic_rules"][0]["contains"] = "other-error"
    elif change == "program":
        repro["binding"]["program_hash"] = "other-program"
    elif change == "arguments":
        repro["call_observation"]["calls"][0]["arguments"]["args"] = ["other"]
    elif change == "environment":
        repro["call_observation"]["calls"][1]["sys_path"] = ["other-root"]
    elif change == "source":
        trace["watches"][0]["file_hash"] = "other-source"
    elif change in {"snapshot", "execution", "request"}:
        trace[{"snapshot": "snapshot_hash", "execution": "execution_identity_hash",
               "request": "raw_request_hash"}[change]] = "other"
    elif change == "dispatch":
        events[-2]["payload"]["call_path_request_hash"] = "other"
    elif change == "execution_source":
        output["execution_source_hash"] = "other"
    elif change == "scope":
        trace["scope"] = "selected_call_focus_launch_thread"
    elif change == "diff":
        trace["candidate_diff_hash"] = "other-diff"
    elif change == "selection":
        events[2]["payload"]["arguments"]["hypothesis"] = "changed after admission"
    else:
        trace["watches"][0]["not_observed_lines"] = []
    state = observation.review(events, observation.EMPTY_DIFF, completion)
    assert state["status"] == "incomplete" and not state["available"] and not state["blocked"]
    assert state["observation"]["candidates"][0]["status"] == "insufficient"


def test_observed_result_survives_edit_as_historical_without_refilling(tmp_path):
    events, completion = execute_receipt(tmp_path)
    before = observation.review(events, observation.EMPTY_DIFF, completion)
    events.append({"event_type": "action_finished", "payload": {"result": {
        "action_id": "edit", "tool": "replace_text", "status": "succeeded"}}})
    for current in ("candidate", observation.EMPTY_DIFF):
        state = observation.review(events, current, completion)
        assert state["status"] == "observed" and state["stale"]
        assert state["evidence_currency"] == "historical" and not state["available"]
        assert state["observation"] == before["observation"]
        assert observation.link(state) == observation.link(before)
