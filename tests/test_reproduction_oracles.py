"""Separate declared failure and desired outcome using trusted offline public probes."""

from __future__ import annotations

import copy
import json

import pytest
from test_dev_probe_cases import ExecutingProbe
from test_dev_runner import _crash_journal_once, _SimulatedCrash
from test_evidence_recovery import intent as legacy_intent
from test_evidence_recovery import probe as legacy_probe
from test_finish_reproduction import checks, finish, mutate, results_for
from test_original_obligation import restore, view
from test_probe_purpose import SOURCE, original_intent, probe

from patchloop.dev import completion_reproduction as completion
from patchloop.dev import original_obligation, probe_invocation, reproduction
from patchloop.util import canonical_json, sha256_bytes, sha256_json


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr("socket.socket.connect", lambda *a, **k: pytest.fail("offline only"))


@pytest.fixture
def gateway(gateway_factory):
    initial, _, _ = gateway_factory()
    return restore(initial, backend=ExecutingProbe())


def projected(gateway):
    return completion.review(gateway.journal.events(), gateway.current_diff_hash,
                             public_task=gateway.public_task, run_id=gateway.journal.run_id)


def test_only_fresh_purpose_schema_requires_both_oracles(smoke_package):
    old = reproduction.schema()["anyOf"][0]
    fresh = reproduction.purpose_schema()["anyOf"][1]
    assert "reported_failure_json" not in old["properties"]
    assert "reported_failure_json" not in reproduction.Intent.model_fields
    assert {"reported_failure_json", "expected_json"} <= set(fresh["required"])
    raw = original_intent(smoke_package.public)
    binding = reproduction.bind(raw, smoke_package.public, SOURCE, "a",
                                observation_channel=probe_invocation.CHANNEL)
    formatted = copy.deepcopy(raw)
    formatted["reported_failure_json"] = json.dumps(json.loads(raw["reported_failure_json"]),
                                                   indent=2)
    same = reproduction.bind(formatted, smoke_package.public, SOURCE, "a",
                             observation_channel=probe_invocation.CHANNEL)
    assert binding == same
    formatted["reported_failure_json"] = "null"
    changed = reproduction.bind(formatted, smoke_package.public, SOURCE, "a",
                                observation_channel=probe_invocation.CHANNEL)
    assert changed["case_id"] != binding["case_id"]


@pytest.mark.parametrize("fault", ["missing", "malformed", "nonfinite", "duplicate", "equal"])
def test_bad_or_equal_failure_declarations_never_dispatch_or_seed_completion(gateway, fault):
    call = probe(gateway.public_task)
    purpose = call.arguments["purpose"]
    if fault == "missing":
        purpose.pop("reported_failure_json")
    else:
        purpose["reported_failure_json"] = {
            "malformed": "not json", "nonfinite": "NaN", "duplicate": '{"x":1,"x":2}',
            "equal": json.dumps(json.loads(purpose["expected_json"]), indent=3),
        }[fault]
    result = gateway.execute(call)
    assert result.status == "failed" and result.output["probe_stage"] == "preflight_rejected"
    assert gateway.probe_sandbox.calls == 0
    assert view(gateway)["request_errors"] == 1 and view(gateway)["original_attempts"] == 0
    assert projected(gateway)["case_count"] == projected(gateway)["pending_count"] == 0
    before = gateway.journal.path.read_bytes()
    assert restore(gateway).execute(call).replayed
    assert gateway.journal.path.read_bytes() == before


def test_rejected_bound_request_does_not_poison_corrected_completion(gateway):
    bad = probe(gateway.public_task, "bad-question")
    bad.arguments["question"] = ""
    assert gateway.execute(bad).status == "failed"
    start = next(e["payload"] for e in gateway.journal.events()
                 if e["event_type"] == "action_started")
    assert start["reproduction_binding"] is not None  # Binding preceded the question rejection.
    assert start["probe_request"]["status"] == "rejected"
    assert projected(gateway)["case_count"] == 0
    corrected = gateway.execute(probe(gateway.public_task, "corrected"))
    state = projected(gateway)
    assert corrected.output["reproduction"]["declared_failure_comparison"] == "matched"
    assert state["case_count"] == 1 and len(state["baseline_failure_case_ids"]) == 1
    assert state["cases"][0]["root_action_id"] == "corrected"


def test_unrelated_healthy_mismatch_does_not_acquire_reported_failure(gateway):
    call = probe(gateway.public_task)
    call.arguments["purpose"]["reported_failure_json"] = "null"
    result = gateway.execute(call)
    evidence = result.output["reproduction"]
    assert evidence["comparison"] == evidence["declared_failure_comparison"] == "mismatched"
    assert evidence["reported_failure_match"] == "not_assessed"
    state = projected(gateway)
    assert state["baseline_failure_case_ids"] == [] and state["baseline_observed_count"] == 1
    assert state["cases"][0]["baseline_acquisition"]["status"] == "unverified"
    assert state["status"] == "refuted"  # Current desired mismatch still blocks finish.
    obligation = view(gateway)
    assert obligation["status"] == "refuted"
    assert obligation["acquisition_status"] == "not_reproduced"
    assert obligation["original_setup_failures"] == 0


@pytest.mark.parametrize("correct", [True, False])
def test_declared_failure_acquisition_still_requires_current_desired_replay(gateway, correct):
    baseline = gateway.execute(probe(gateway.public_task))
    evidence = baseline.output["reproduction"]
    assert evidence["comparison"] == "mismatched"
    assert evidence["declared_failure_comparison"] == "matched"
    assert evidence["requirement_mapping"] == "model_authored_unverified"
    assert evidence["reported_failure_match"] == evidence["repair_success"] == "not_assessed"
    assert view(gateway)["stage"] == "acquired"
    assert projected(gateway)["cases"][0]["baseline_acquisition"]["status"] == "qualified"
    mutate(gateway, correct=correct)
    checks(gateway)
    result, _ = finish(gateway)
    if correct:
        assert result.status == "succeeded"
        assert result.output["delivery_state"] == "cases_verified_delivery"
        assert result.output["original_verification"]["status"] == "verified"
    else:
        assert result.status == "failed" and projected(gateway)["status"] == "refuted"
    assert gateway.probe_sandbox.calls == 2
    assert gateway.probe_sandbox.sources[0] == gateway.probe_sandbox.sources[1]
    replay = results_for(gateway.journal, "run_probe")[-1]["output"]["reproduction"]
    assert replay["comparison"] == ("matched" if correct else "mismatched")
    assert replay["declared_failure_comparison"] == ("mismatched" if correct else "matched")
    oracle = "expected_json" if correct else "reported_failure_json"
    assert replay["observed_json"] == evidence["binding"]["definition"][oracle]


def test_incomplete_observation_gets_neither_oracle_comparison(gateway):
    result = gateway.execute(probe(gateway.public_task, source="raise ImportError('local setup')"))
    evidence = result.output["reproduction"]
    assert evidence["comparison"] == evidence["declared_failure_comparison"] == "not_compared"
    assert projected(gateway)["baseline_failure_case_ids"] == []
    assert view(gateway)["acquisition_status"] == "setup_blocked"


def test_missing_field_rejected_admission_crash_stays_rejected(gateway, monkeypatch):
    call = probe(gateway.public_task)
    call.arguments["purpose"].pop("reported_failure_json")
    _crash_journal_once(monkeypatch, event_type="action_started", when="after")
    with pytest.raises(_SimulatedCrash):
        gateway.execute(call)
    assert projected(gateway)["case_count"] == 0
    result = restore(gateway).execute(call)
    assert result.error_code == "CONTRACT_ERROR"
    assert result.output["probe_stage"] == "preflight_rejected"
    assert gateway.probe_sandbox.calls == 0 and projected(gateway)["case_count"] == 0


@pytest.mark.parametrize("stage", ["action_started", "probe_execution_started"])
def test_accepted_uncertain_binding_remains_unverified(gateway, monkeypatch, stage):
    _crash_journal_once(monkeypatch, event_type=stage, when="after")
    with pytest.raises(_SimulatedCrash):
        gateway.execute(probe(gateway.public_task))
    state = projected(gateway)
    assert state["case_count"] == state["unverified_count"] == 1
    assert state["baseline_failure_case_ids"] == []
    assert state["cases"][0]["baseline_acquisition"]["status"] == "unverified"


def test_legacy_reproduction_serialization_and_replay_remain_unchanged(gateway):
    call = legacy_probe(gateway.public_task)
    result = gateway.execute(call)
    value = result.output["reproduction"]
    raw = legacy_intent(gateway.public_task)
    definition = {**raw, "expected_json": canonical_json(json.loads(raw["expected_json"])),
                  "public_task_hash": sha256_json(gateway.public_task.model_dump(mode="json"))}
    program_hash = sha256_bytes(call.arguments["python_source"].encode())
    binding = {"case_id": sha256_json({"definition": definition, "program_hash": program_hash}),
               "definition": definition, "program_hash": program_hash, "root_action_id": "original"}
    assert value["binding"] == binding and "declared_failure_comparison" not in value
    assert gateway.probe_sandbox.sources[0] == reproduction.program(
        call.arguments["python_source"], binding)
    replay = gateway.execute(legacy_probe(gateway.public_task, "recheck", replay="original"))
    assert replay.output["reproduction"]["binding"] == binding
    assert "declared_failure_comparison" not in replay.output["reproduction"]


def test_old_accepted_pending_purpose_recovers_exact_binding_and_program(gateway):
    call = probe(gateway.public_task)
    call.arguments["purpose"].pop("reported_failure_json")
    raw = {key: value for key, value in call.arguments["purpose"].items() if key != "kind"}
    binding = reproduction.bind(raw, gateway.public_task, SOURCE, call.action_id,
                                observation_channel=probe_invocation.CHANNEL)
    old_bytes = canonical_json(binding)
    program = reproduction.program(SOURCE, binding)
    input_hash = sha256_json({"tool": call.name, "arguments": call.arguments,
                              "turn_decision": call.turn_decision.model_dump(mode="json")})
    gateway.journal.append("action_started", {
        "action_id": call.action_id, "input_hash": input_hash, "tool": call.name,
        "arguments": call.arguments, "baseline_diff_hash": original_obligation.EMPTY_DIFF,
        "turn_decision": call.turn_decision.model_dump(mode="json"),
        "reproduction_binding": binding,
        "probe_request": {"policy": original_obligation.PROBE_STAGES,
                          "status": "accepted", "kind": "original_requirement"},
    })
    assert projected(gateway)["case_count"] == projected(gateway)["unverified_count"] == 1
    # Old journals without an admission receipt retain their unresolved case.
    unknown_events = copy.deepcopy(gateway.journal.events())
    unknown_events[-1]["payload"].pop("probe_request")
    unknown = completion.review(unknown_events, gateway.current_diff_hash,
                                public_task=gateway.public_task, run_id=gateway.journal.run_id)
    assert unknown["case_count"] == unknown["unverified_count"] == 1
    assert unknown["baseline_failure_case_ids"] == []
    result = restore(gateway).execute(call)
    assert result.status == "succeeded", result
    assert canonical_json(result.output["reproduction"]["binding"]) == old_bytes
    assert "declared_failure_comparison" not in result.output["reproduction"]
    assert gateway.probe_sandbox.sources == [program]
    assert view(gateway)["stage"] == "acquired"  # Preserve the old mismatch semantics.
    assert restore(gateway).execute(call).replayed and gateway.probe_sandbox.calls == 1
