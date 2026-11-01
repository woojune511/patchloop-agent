"""Refutation-to-revision controls using public synthetic receipts and tiny local code."""

import copy
import os
import sys
from types import SimpleNamespace

import pytest
from test_dev_tools import mutation_call
from test_repair_path_diagnosis import diagnosis, setup, state
from test_repair_path_reuse import (
    SOURCE,
    TEST,
    finished,
    mutation,
    receipts,
    result_for,
    start_for,
)

from patchloop.contracts import PublicTestSuite
from patchloop.dev import completion_reproduction, repair_path
from patchloop.dev import repair_prediction as prediction
from patchloop.dev.contracts import RequestedTool
from patchloop.errors import ContractError
from patchloop.util import sha256_json


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("repair revision controls must not access the network")
    monkeypatch.setattr("socket.socket.connect", forbidden)


def diagnosed():
    events, completion = receipts(test_edit=False)
    path = prediction.decorate(repair_path.review(events, SOURCE, completion))
    state = prediction.review(events, SOURCE, path)
    task = SimpleNamespace(test_suites=[SimpleNamespace(id="public-tests")])
    return events, path, state, task


def source_prediction(path, state, task, *, event="not_raised", target=0):
    return prediction.admit(path, state, {
        "hypothesis": "Avoid the exception before the previously changed branch.",
        "expected_behavior": "The original input reaches the guarded branch.",
        "repair_prediction": {"kind": "source", "target": target, "event": event},
    }, public_task=task)


@pytest.mark.parametrize("event", ["entered", "raised"])
def test_prediction_must_change_the_failed_observation(event):
    _, path, state, task = diagnosed()
    with pytest.raises(ContractError, match="already true"):
        source_prediction(path, state, task, event=event)
    assert source_prediction(path, state, task)["refutation"]["original_failure"] == "unchanged"
    # A value repair need not change call/exception counts.
    assert source_prediction(path, state, task, event="original_failure_absent", target=-1)[
        "function"] is None


@pytest.mark.parametrize("raw", [None, {"kind": "source", "target": True, "event": "entered"},
                                {"kind": "source", "target": 4, "event": "entered"},
                                {"kind": "source", "target": 0,
                                 "event": "original_failure_absent"}])
def test_missing_or_unbound_predictions_cannot_authorize_source_repair(raw):
    _, path, state, task = diagnosed()
    with pytest.raises(ContractError):
        prediction.admit(path, state, {"repair_prediction": raw}, public_task=task)


def replay_case():
    events, path, state, task = diagnosed()
    admitted = source_prediction(path, state, task)
    start, _ = mutation(events, "revised", SOURCE, TEST)
    start["repair_prediction"] = admitted
    call = completion_reproduction.replay_call("run", path["case_id"], "baseline", TEST)
    target = {key: admitted["function"][key] for key in prediction.IDENTITY}
    target["file_hash"] = sha256_json("revised-file")

    def preflight(workspace, request, **kwargs):
        assert request["scope"] == "selected_call"
        return {"focus": target, "watches": [{**target, "lines": [], "parameters": []}]}

    admission = prediction.prepare_replay(events, call, TEST, "run", None, preflight)
    result = copy.deepcopy(result_for(events, "diagnosis")["output"])
    identity = {"run_id": "run", "action_id": call.action_id, "input_hash": "raw-input"}
    result.update(diff_hash=TEST, snapshot_hash="revised-snapshot")
    trace = result["call_path"]
    trace.update(candidate_diff_hash=TEST, snapshot_hash="revised-snapshot",
                 raw_request_hash=sha256_json(admission["call_path"]),
                 execution_identity_hash=sha256_json(identity))
    trace["focus"].update(target, event_counts={"call": 1, "exception": 0})
    return events, call, admission, result, identity, preflight


def test_observed_prediction_and_original_failure_are_independent():
    _, _, admission, result, identity, _ = replay_case()
    assessed = prediction.assess(admission, result, identity)
    assert assessed["status"] == "matched" and assessed["original_effect"] == "refuted"
    assert assessed["semantic_correctness"] == "unverified"
    assert not assessed["counts_toward_required_checks"]
    result["call_path"]["focus"]["event_counts"] = {"call": 0, "exception": 0}
    # A function never entered does not support 'entered without exceptions'.
    assert prediction.assess(admission, result, identity)["status"] == "contradicted"


@pytest.mark.parametrize("rules_present", [False, True])
def test_missing_judgment_blocks_only_rule_based_assessment(rules_present):
    _, _, admission, result, identity, _ = replay_case()
    reproduction = result["reproduction"]
    reproduction["judgment"] = None
    if not rules_present:
        reproduction["binding"]["definition"]["diagnostic_rules"] = None
        admission["invocation_fingerprint"] = prediction._invocation_fingerprint(result)
    assessed = prediction.assess(admission, result, identity)
    assert assessed["status"] == ("unverified" if rules_present else "matched")
    assert assessed["original_effect"] == ("unverified" if rules_present else "refuted")
    assert assessed["semantic_correctness"] == "unverified"
    # Ruleless comparison still requires the same invocation and a complete trace.
    reproduction["call_observation"]["incomplete"] = True
    assessed = prediction.assess(admission, result, identity)
    assert assessed["status"] == assessed["original_effect"] == "unverified"


@pytest.mark.parametrize("field,value", [
    ("status", "unknown"), ("scope", "selected_call_focus_launch_thread"),
    ("snapshot_hash", None), ("raw_request_hash", "different"),
    ("candidate_diff_hash", "different"), ("execution_identity_hash", "different"),
])
def test_partial_or_misbound_trace_cannot_confirm_prediction(field, value):
    _, _, admission, result, identity, _ = replay_case()
    result["call_path"][field] = value
    assert prediction.assess(admission, result, identity)["status"] == "unverified"


@pytest.mark.parametrize("change", ["environment", "image", "binding"])
def test_changed_original_conditions_invalidate_both_prediction_and_original_effect(change):
    _, _, admission, result, identity, _ = replay_case()
    if change == "environment":
        result["reproduction"]["call_observation"]["execution_environment"] = {"drift": True}
    elif change == "image":
        result["image_digest"] = "another-image"
    else:
        result["reproduction"]["binding"]["root_action_id"] = "another-root"
    assessed = prediction.assess(admission, result, identity)
    assert assessed["status"] == assessed["original_effect"] == "unverified"


def test_only_exact_automatic_replay_gets_host_observation_and_bad_binding_does_not_block_it():
    events, call, _, _, _, preflight = replay_case()
    other = call.model_copy(deep=True)
    other.arguments["purpose"] = {"changed": True}
    assert prediction.prepare_replay(events, other, TEST, "run", None, preflight) is None
    original = copy.deepcopy(call.arguments)

    def missing(*args, **kwargs):
        raise ContractError("function removed by the repair")

    unavailable = prediction.prepare_replay(events, call, TEST, "run", None, missing)
    assert unavailable["status"] == "unavailable" and unavailable["call_path"] is None
    assert call.arguments == original


@pytest.mark.parametrize("completed", ["PASSED_BOTH", "INCONCLUSIVE", "request_failed"])
def test_test_comparison_is_one_frozen_attempt_and_never_original_repair_credit(completed):
    events, path, state, task = diagnosed()
    intent = prediction.admit(path, state, {"path": "tests/test_sample.py",
        "repair_prediction": {"kind": "test", "suite_id": "public-tests",
                              "targets": ["tests/test_sample.py::test_original"]}},
                              public_task=task)
    start, _ = mutation(events, "test-edit", SOURCE, TEST,
                         path="tests/test_sample.py", test_only=True)
    start["repair_prediction"] = intent
    pending = prediction.review(events, TEST, path)
    assert pending["status"] == "needs_test_comparison" and not pending["test_available"]
    expected = pending["pending_test"]
    assert expected["comparison"] == {"baseline": "before_mutation",
                                       "mutation_action_id": "source-edit"}
    with pytest.raises(ContractError, match="frozen"):
        prediction.validate_test(pending, path, {**expected, "comparison": None})
    link = prediction.validate_test(pending, path, expected)
    events.append({"event_type": "action_started", "payload": {
        "action_id": "compare", "repair_test_link": link}})
    # Starting the pair does not refill it; pending recovery retains its exact selection.
    assert not prediction.review(events, TEST, path)["test_available"]
    events.append(finished({"action_id": "compare", "status": "failed"
        if completed == "request_failed" else "succeeded", "output": {
            "comparison": {"status": completed, "original_requirement_credit": False}}}))
    final = prediction.review(events, TEST, path)
    assert final["status"] == ("observed" if completed == "PASSED_BOTH" else "unverified")
    assert not final["test_available"] and not final["original_requirement_credit"]
    assert final["pending_test"] is None


def test_comparison_must_select_the_added_test_not_an_existing_helper_case():
    before = b"def test_control():\n    assert True\n"
    after = before + b"\ndef test_new():\n    assert False\n"
    selection = {"targets": ["tests/test_sample.py::test_control"]}
    with pytest.raises(ContractError, match="new or extended test"):
        prediction.validate_addition("tests/test_sample.py", before, after, selection)
    selection["targets"] = ["tests/test_sample.py::test_new"]
    prediction.validate_addition("tests/test_sample.py", before, after, selection)


def test_prediction_replay_recovers_without_duplicate_and_keeps_original_result(gateway_factory):
    gateway, journal, _, backend = setup(gateway_factory)
    assert gateway.execute(diagnosis(gateway)).status == "succeeded"
    path = state(gateway)
    fixed = mutation_call(gateway, action_id="revised", alternative=True)
    fixed.arguments["old_text"] = start_for(journal.events(), "wrong-repair")["arguments"][
        "new_text"]
    fixed.arguments["repair_prediction"] = {"kind": "source", "target": 0,
                                             "event": "not_entered"}
    assert gateway.execute(fixed).status == "succeeded"
    call = completion_reproduction.replay_call(
        journal.run_id, path["case_id"], "original", gateway.current_diff_hash)
    append = journal.append

    def crash(kind, payload):
        if kind == "action_finished" and payload["action_id"] == call.action_id:
            raise KeyboardInterrupt("lost parent receipt after durable child result")
        return append(kind, payload)

    journal.append = crash
    with pytest.raises(KeyboardInterrupt):
        gateway.execute(call)
    journal.append = append
    assert backend.calls == 4
    result = gateway.execute(call)
    assert result.status == "succeeded", result.message
    assert backend.calls == 4
    assert result.output["call_path"]["status"] == "complete"
    assessment = result.output["repair_prediction"]
    assert assessment["status"] == "contradicted" and assessment["original_effect"] == "supported"
    assert gateway.completion_verification(diff_hash=gateway.current_diff_hash)["status"] == (
        "cases_verified")
    assert gateway.execute(call).replayed and backend.calls == 4


@pytest.mark.parametrize("new_module", [False, True])
def test_added_test_reuses_diagnosis_then_compares_same_test_before_source_edit(
    gateway_factory, new_module,
):
    def configured():
        gateway, journal, workspace = gateway_factory()
        gateway.public_task.constraints.allowed_paths = ["**"]
        gateway.public_task.constraints.forbidden_paths = []
        gateway.public_task.constraints.additive_test_roots = ["tests"]
        gateway.public_task.constraints.max_changed_files = 2
        gateway.public_task.test_suites = [PublicTestSuite(
            id="public-tests", test_roots=["tests"],
            command=[sys.executable, "-m", "pytest", "-q"],
            environment={"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
                         **({"SYSTEMROOT": os.environ["SYSTEMROOT"]} if os.name == "nt" else {})})]
        return gateway, journal, workspace

    gateway, journal, workspace, _ = setup(configured)
    assert gateway.execute(diagnosis(gateway)).status == "succeeded"
    path = "tests/test_added.py" if new_module else "tests/test_csvlite.py"
    original = ""
    if not new_module:
        assert gateway.execute(RequestedTool(name="read_file", action_id="read-tests", arguments={
            "path": path, "start_line": 1, "end_line": 200})).status == "succeeded"
        original = (workspace / path).read_text()
    added = original + ("\n\ndef test_control_revision():\n"
                        "    from mini_data_utils.csvlite import parse_rows\n"
                        "    assert parse_rows('h,v\\na,b\\n') == [['h', 'v'], ['a', 'b']]\n")
    call = RequestedTool(name="replace_text", action_id="add-test", arguments={
        "path": path, "old_text": original, "new_text": added, "occurrence": 1,
        "hypothesis": "Check whether the selected input distinguishes the failed source edit.",
        "expected_behavior": "Compare the same assertion on both source versions.",
        "repair_prediction": {"kind": "test", "suite_id": "public-tests",
                              "targets": [path + "::test_control_revision"]}})
    if new_module:
        call = RequestedTool(name="edit_files", action_id="add-test", arguments={
            "edits": [{"path": path, "old_text": None,
                       "new_text": '"""New public test module."""\nimport math\n' + added,
                       "occurrence": 1}], "undo_action_id": None,
            **{key: call.arguments[key] for key in (
                "hypothesis", "expected_behavior", "repair_prediction")},
        })
    mislabeled = call.model_copy(deep=True, update={"action_id": "test-as-source"})
    mislabeled.arguments["repair_prediction"] = {
        "kind": "source", "target": -1, "event": "original_failure_absent"}
    assert gateway.execute(mislabeled).status == "failed"
    assert gateway.accepted_mutations == 1
    result = gateway.execute(call)
    assert result.status == "succeeded", result.message
    prior = start_for(journal.events(), "add-test")["repair_prediction"]
    replay = completion_reproduction.replay_call(
        journal.run_id, prior["case_id"], "original", gateway.current_diff_hash)
    assert gateway.execute(replay).status == "succeeded"
    review = gateway.completion_verification(diff_hash=gateway.current_diff_hash)
    assert review["repair_path"]["diagnosis_evidence"]["relation"] == "historical_test_only"
    assert review["repair_prediction"]["status"] == "needs_test_comparison"
    selection = review["repair_prediction"]["pending_test"]
    compared = gateway.execute(RequestedTool(name="run_tests", action_id="compare-added",
                                            arguments=selection))
    assert compared.status == "succeeded", compared.message
    assert compared.output["comparison"]["status"] == "PASSED_BOTH"
    review = gateway.completion_verification(diff_hash=gateway.current_diff_hash)
    assert review["status"] == "refuted" and review["repair_path"]["status"] == "diagnosed"
    assert review["repair_prediction"]["status"] == "observed"
    assert not review["repair_prediction"]["test_available"]
