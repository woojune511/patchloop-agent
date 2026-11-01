"""Pure receipt controls: no target process, provider, container or filesystem replay."""

import copy

import pytest
from test_observation_correction import action

from patchloop.dev import repair_path
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes, sha256_json

PATH = "sample.py"
FILE_HASH = sha256_json("implementation-after")
BASE, SOURCE, TEST, TEST2 = [sha256_json(value) for value in ("base", "source", "test", "test2")]


def finished(result):
    return {"event_type": "action_finished", "payload": {
        "action_id": result["action_id"], "input_hash": result.get("input_hash"), "result": result}}


def mutation(events, action_id, before, after, *, path=PATH, preimage=None, test_only=False):
    arguments = {"path": path, "old_text": "old", "new_text": "new", "occurrence": 1,
                 "hypothesis": "Changing the selected branch resolves the original failure.",
                 "expected_behavior": "The original invocation stops reporting its error."}
    patch = f"diff --git a/{path} b/{path}\n-old\n+new\n"
    postimage = FILE_HASH if path == PATH else sha256_json(action_id + "-postimage")
    start = {"action_id": action_id, "tool": "replace_text", "arguments": arguments,
             "input_hash": sha256_json(arguments), "mutation_admitted": True,
             "mutation_target_path": path, "baseline_diff_hash": before,
             "mutation_preimage_file_hash": preimage or sha256_json(path + "-preimage"),
             "mutation_expected_postimage_file_hash": postimage,
             "mutation_expected_worktree_diff_hash": after,
             "mutation_generated_patch": patch, "mutation_test_only": test_only}
    result = {"action_id": action_id, "tool": "replace_text", "status": "succeeded",
              "input_hash": start["input_hash"], "workspace_diff_hash": after, "output": {
                  "patch_hash": sha256_bytes(patch.encode()), "worktree_diff_hash": after,
                  "changed_files": [path], "mutation": {"diff_hash": after,
                      "changed_hunk": patch, "replacement_hash": sha256_json({
                          key: arguments[key]
                          for key in ("path", "old_text", "new_text", "occurrence")})},
                  "mutation_evidence": {"path": path, "source_diff_hash": after,
                                        "file_hash": postimage}}}
    events.extend([{"event_type": "action_started", "payload": start}, finished(result)])
    return start, result


def failure(events, original, action_id, diff):
    result = copy.deepcopy(original)
    result.update(action_id=action_id, input_hash=sha256_json(action_id), workspace_diff_hash=diff)
    result["output"].update(diff_hash=diff, public_execution={"diff_hash": diff, "files": [{
        "path": PATH, "file_hash": FILE_HASH, "status": "collected",
        "not_observed_changed_ranges": [[12, 13]],
    }]})
    events.extend([{"event_type": "action_started", "payload": {
        "action_id": action_id, "tool": "run_probe", "arguments": {}}}, finished(result)])
    return result


def receipts(*, diagnosis_status="complete", test_edit=True):
    events = action(status="consistent")
    root = events[1]["payload"]["result"]
    root["workspace_diff_hash"] = BASE
    root["output"].update(image_digest="image", profile_hash="profile")
    case_id = root["output"]["reproduction"]["binding"]["case_id"]
    completion = {"baseline_failure_case_ids": [case_id], "cases": [{
        "case_id": case_id, "root_action_id": "baseline", "evidence": {"status": "REFUTED"}}]}
    mutation(events, "source-edit", BASE, SOURCE)
    first = failure(events, root, "failure-source", SOURCE)
    state = repair_path.review(events, SOURCE, completion)
    assert state["status"] == "needs_path_diagnosis"
    request = {"scope": "selected_call", "call_id": "call-1",
               "focus": {"origin": "workspace", "path": PATH, "function": "entry"},
               "watches": [{"origin": "workspace", "path": PATH, "function": "entry",
                            "file_hash": FILE_HASH, "lines": [10, 12, 13], "fields": []}]}
    start = {"action_id": "diagnosis", "tool": "run_probe",
             "arguments": {"focus": request["focus"]},
             "input_hash": sha256_json(request), "repair_path_link": repair_path.link(state),
             "diagnosis_request": {"call_path": request},
             "execution_identity": {"action_id": "diagnosis"}}
    row = {"origin": "workspace", "path": PATH, "function": "entry", "file_hash": FILE_HASH,
           "entries": 1, "observation": "observed", "observed_lines": [10],
           "not_observed_lines": [12, 13], "event_counts": {
               "call": 1, "line": 1, "exception": 1, "return": 1},
           "events": [{"event": "call", "line": 9},
                      {"event": "exception", "line": 10, "exception_type": "ImportError"},
                      {"event": "return", "line": 10, "value": None}]}
    trace = {"status": diagnosis_status, "call_id": "call-1", "candidate_diff_hash": SOURCE,
             "scope": "selected_call_launch_thread", "snapshot_hash": "source-snapshot",
             "raw_request_hash": sha256_json(request),
             "execution_identity_hash": sha256_json(start["execution_identity"]),
             "focus": row, "watches": [copy.deepcopy(row)], "collection": {
                 "coverage": {"status": diagnosis_status}, "details": {"status": "complete"}}}
    result = copy.deepcopy(first)
    result.update(action_id="diagnosis", input_hash=start["input_hash"])
    result["output"].update(call_path=trace, snapshot_hash="source-snapshot")
    events.extend([{"event_type": "action_started", "payload": start},
                   {"event_type": "probe_execution_started",
                    "payload": {"action_id": "diagnosis"}}])
    if diagnosis_status != "pending":
        events.append(finished(result))
    if test_edit:
        mutation(events, "test-edit", SOURCE, TEST, path="tests/test_sample.py", test_only=True)
        failure(events, root, "failure-test", TEST)
    return events, completion


def result_for(events, action_id):
    return next(e["payload"]["result"] for e in events if e["event_type"] == "action_finished"
                and e["payload"]["result"]["action_id"] == action_id)


def start_for(events, action_id):
    return next(e["payload"] for e in events if e["event_type"] == "action_started"
                and e["payload"]["action_id"] == action_id)


def test_collection_completion_keeps_original_refutation_and_exception_site_visible():
    events, completion = receipts(test_edit=False)
    before = copy.deepcopy(events)
    state = repair_path.review(events, SOURCE, completion)
    assert state["status"] == "diagnosed" and not state["blocked"]
    assert state["diagnosis_collection_status"] == "complete"
    assert state["original_effect_status"] == "original_effect_refuted"
    fact = state["factual_refutation"]
    assert fact["original_failure"] == "unchanged"
    assert fact["unobserved_changes"][0]["ranges"] == [[12, 13]]
    assert fact["exception_sites"] == [{"origin": "workspace", "path": PATH, "function": "entry",
        "file_hash": FILE_HASH, "line": 10, "exception_type": "ImportError"}]
    assert state["diagnosis_observation"]["focus"]["omitted_event_count"] == 1
    assert state["diagnosis_evidence"]["relation"] == "current_candidate"
    assert events == before


def test_certified_test_addition_carries_historical_diagnosis_without_fresh_trace_credit():
    events, completion = receipts()
    state = repair_path.review(events, TEST, completion)
    assert state["status"] == "diagnosed" and not state["blocked"]
    assert state["candidate_diff_hash"] == TEST and state["failure_action_id"] == "failure-test"
    assert state["diagnosis_action_id"] == "diagnosis"
    assert state["diagnosis_evidence"] == {
        "relation": "historical_test_only", "source_action_id": "diagnosis",
        "observed_diff_hash": SOURCE, "attempted_diff_hash": SOURCE, "current_diff_hash": TEST,
        "snapshot_hash": "source-snapshot", "test_only_mutation_action_ids": ["test-edit"],
        "current_snapshot_trace": False}
    assert state["factual_refutation"]["exception_evidence_diff_hash"] == SOURCE
    assert state["execution_attempted"]
    assert repair_path.validate(state, "replace_text", {"hypothesis": "A different mechanism"}) == {
        **repair_path.link(state), "diagnosis_action_id": "diagnosis"}
    with pytest.raises(ContractError, match="hypothesis"):
        repair_path.validate(state, "replace_text", {})


@pytest.mark.parametrize("status", ["unknown", "pending"])
def test_test_additions_cannot_refill_an_uncertain_diagnostic_execution(status):
    events, completion = receipts(diagnosis_status=status)
    state = repair_path.review(events, TEST, completion)
    assert state["status"] == "verification_incomplete" and state["blocked"]
    assert state["diagnosis_collection_status"] == "unknown"
    assert state["execution_attempted"] and state["diagnosis_action_id"] is None
    assert state["diagnosis_evidence"]["relation"] == "historical_test_only"
    assert state["diagnosis_evidence"]["observed_diff_hash"] is None
    assert not state["diagnosis_evidence"]["current_snapshot_trace"]
    assert state["factual_refutation"]["exception_sites"] == []
    with pytest.raises(ContractError):
        repair_path.validate(state, "run_probe", {"replay_action_id": "baseline", "call_path": {}})


def test_test_addition_preserves_rejected_request_and_preparation_allowances():
    events, completion = receipts()
    start = start_for(events, "diagnosis")
    start["probe_request"] = {"status": "rejected"}
    events[:] = [e for e in events if e["event_type"] != "probe_execution_started"
                 and not (e["event_type"] == "action_finished"
                          and e["payload"]["result"]["action_id"] == "diagnosis")]
    for action_id, tool in (("second-rejection", "run_probe"), ("preparation", "read_file")):
        duplicate = copy.deepcopy(start)
        duplicate.update(action_id=action_id, tool=tool)
        events.append({"event_type": "action_started", "payload": duplicate})
    state = repair_path.review(events, TEST, completion)
    assert state["status"] == "verification_incomplete"
    assert state["rejected_requests"] == 2 and not state["execution_attempted"]
    assert state["preparation_action_ids"] == ["preparation"]
    assert not state["preparation_available"] and state["diagnosis_action_id"] is None


def test_historical_result_with_different_input_hash_remains_unknown_and_spent():
    events, completion = receipts()
    result_for(events, "diagnosis")["input_hash"] = "different"
    state = repair_path.review(events, TEST, completion)
    assert state["status"] == "verification_incomplete"
    assert state["diagnosis_collection_status"] == "unknown"
    assert state["execution_attempted"] and state["diagnosis_action_id"] is None


@pytest.mark.parametrize("change", [
    "missing_attestation", "not_test_only", "conftest", "configuration",
    "input_hash", "result_diff", "chain_gap", "patch", "source_receipt", "postimage",
    "missing_image", "image", "profile", "failure_capture", "binding"])
def test_unproven_chain_or_different_failure_retains_strict_candidate_rule(change):
    events, completion = receipts()
    start, result = start_for(events, "test-edit"), result_for(events, "test-edit")
    output = result_for(events, "failure-test")["output"]
    if change == "missing_attestation":
        start.pop("mutation_test_only")
    elif change == "not_test_only":
        start["mutation_test_only"] = False
    elif change in {"conftest", "configuration"}:
        path = "tests/conftest.py" if change == "conftest" else "tests/pytest.ini"
        index = next(i for i, e in enumerate(events) if e["event_type"] == "action_started"
                     and e["payload"]["action_id"] == "test-edit")
        replacement = []
        mutation(replacement, "test-edit", SOURCE, TEST, path=path, test_only=True)
        events[index:index + 2] = replacement
    elif change == "input_hash":
        result["input_hash"] = "different"
    elif change == "result_diff":
        result["output"]["worktree_diff_hash"] = "different"
    elif change == "chain_gap":
        start["baseline_diff_hash"] = "different"
    elif change == "patch":
        result["output"]["mutation"]["changed_hunk"] = "different"
    elif change == "source_receipt":
        result_for(events, "source-edit")["input_hash"] = "different"
    elif change == "postimage":
        result["output"]["mutation_evidence"]["file_hash"] = "different"
    elif change == "missing_image":
        output.pop("image_digest")
    elif change in {"image", "profile"}:
        output["image_digest" if change == "image" else "profile_hash"] = "different"
    elif change == "failure_capture":
        output["reproduction"]["call_observation"]["calls"][0]["capture"]["stdout"] += "different"
    elif change == "binding":
        output["reproduction"]["binding"]["program_hash"] = "different"
    state = repair_path.review(events, TEST, completion)
    assert state["status"] == "needs_path_diagnosis" and state["blocked"]
    assert "diagnosis_evidence" not in state


def test_multiple_test_edits_require_contiguous_file_and_full_diff_identities():
    events, completion = receipts()
    first = start_for(events, "test-edit")
    second, _ = mutation(events, "test-edit-2", TEST, TEST2, path="tests/test_sample.py",
                         preimage=first["mutation_expected_postimage_file_hash"], test_only=True)
    failure(events, result_for(events, "baseline"), "failure-test-2", TEST2)
    state = repair_path.review(events, TEST2, completion)
    assert state["diagnosis_evidence"]["test_only_mutation_action_ids"] == [
        "test-edit", "test-edit-2"]
    second["mutation_preimage_file_hash"] = "different"
    assert repair_path.review(events, TEST2, completion)["status"] == "needs_path_diagnosis"


def test_a_new_implementation_invalidates_historical_diagnosis_even_on_same_file():
    events, completion = receipts()
    mutation(events, "new-source-edit", TEST, TEST2)
    failure(events, result_for(events, "baseline"), "new-source-failure", TEST2)
    state = repair_path.review(events, TEST2, completion)
    assert state["status"] == "needs_path_diagnosis"
    assert state["mutation_action_id"] == "new-source-edit"
    assert "diagnosis_evidence" not in state


def test_legacy_same_candidate_remains_supported_but_cannot_create_historical_credit():
    events, completion = receipts(test_edit=False)
    start_for(events, "source-edit").pop("mutation_preimage_file_hash")
    assert repair_path.review(events, SOURCE, completion)["status"] == "diagnosed"
    mutation(events, "test-edit", SOURCE, TEST, path="tests/test_sample.py", test_only=True)
    failure(events, result_for(events, "baseline"), "failure-test", TEST)
    assert repair_path.review(events, TEST, completion)["status"] == "needs_path_diagnosis"


def test_changed_inputs_or_incomplete_original_do_not_establish_reusable_failure():
    events, completion = receipts()
    trace = result_for(events, "failure-test")["output"]["reproduction"]["call_observation"]
    trace["calls"][0]["arguments"]["args"] = ["different"]
    assert repair_path.review(events, TEST, completion)["status"] == "not_needed"
    trace["incomplete"] = True
    assert repair_path.review(events, TEST, completion)["status"] == "not_needed"
