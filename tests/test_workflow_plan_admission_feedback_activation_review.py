from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from patchloop.agent.runner import AgentRunner
from patchloop.agent.workflow_plan_admission_feedback_activation_review import (
    ADMISSION_THRESHOLDS,
    IMMUTABLE_INPUTS,
    QUALIFICATION_PATH,
    SOURCE_FILES,
    assess_plan_feedback_request_pair,
    build_plan_admission_feedback_activation_review,
    measure_plan_feedback_request_artifact,
    review_bytes,
)
from patchloop.agent.workflow_successor_v2 import WORK_PLAN_ADMISSION_POLICY
from patchloop.contracts import EventType
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes
from tests.test_workflow_plan_admission_feedback_runner import (
    _manifest,
    _plan_requests,
)
from tests.test_workflow_successor_v2_runner import (
    TASK_PATH,
    _CrashBeforePinnedRetryAdapter,
    _PinnedPlanGateWorkflowAdapter,
)

ROOT = Path(__file__).resolve().parents[1]


def _load_result_details(failure) -> dict:
    artifact = json.loads(Path(failure.payload["artifact_path"]).read_text(encoding="utf-8"))
    return artifact["error_details"]


def _measure_pair(runner: AgentRunner, run_id: str) -> tuple[dict, dict]:
    plans = _plan_requests(runner, run_id)
    failures = [
        event
        for event in runner.state.list_events(run_id)
        if event.type == EventType.TOOL_FAILED and event.payload.get("tool") == "record_work_plan"
    ]
    assert len(plans) == len(failures) == 2
    current = measure_plan_feedback_request_artifact(plans[0][2])
    recovered = measure_plan_feedback_request_artifact(
        plans[1][2],
        durable_error_details=failures[0].payload["error_details"],
        result_error_details=_load_result_details(failures[0]),
    )
    return current, recovered


def test_review_independently_measures_bounded_retry_and_durable_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest("run_v22_activation_review_measure")
    runner = AgentRunner(tmp_path / "v22-review-measure")
    adapter = _PinnedPlanGateWorkflowAdapter(
        prefix="v22-review-measure",
        invalid_closure=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    current, recovered = _measure_pair(runner, manifest.run_id)
    assessment = assess_plan_feedback_request_pair(current, recovered)

    assert result["terminal_error"]["code"] == "WORK_PLAN_ADMISSION_REPEATED"
    assert assessment["candidate_preparation_pair_ready"] is True
    assert all(assessment["checks"].values())
    assert (
        current["canonical_request_body_bytes"]
        <= (ADMISSION_THRESHOLDS["current_plan_request_max_bytes"])
    )
    assert (
        recovered["canonical_request_body_bytes"]
        <= (ADMISSION_THRESHOLDS["recovered_retry_request_max_bytes"])
    )
    assert recovered["context_bytes_saved"] >= 30_000
    assert recovered["durable_error_details_bytes"] > 30_000
    assert recovered["projected_error_details_bytes"] <= 4_096
    assert recovered["omitted_source_value_bytes"] > 30_000
    assert recovered["workflow_projection_field_occurrences"] == {
        "eligible_plan_evidence_catalog": 1,
        "activated_exploration_plan_request": 1,
        "causal_plan_request_projection": 1,
        "semantic_progress_state": 1,
        "cross_reset_failure_trigger": 1,
        "causal_mechanism_history": 1,
    }
    assert recovered["residual_full_projection_duplicate_count"] == 0
    assert recovered["embedded_full_omitted_value_count"] == 0
    assert recovered["full_nested_feedback_fields"] == []


def test_review_restart_uses_one_recovered_retry_and_stops_before_third_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest("run_v22_activation_review_restart")
    runner = AgentRunner(tmp_path / "v22-review-restart")
    first = _CrashBeforePinnedRetryAdapter(prefix="v22-review-restart-first")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: first)

    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK_PATH, model="mock", manifest=manifest)

    second = _PinnedPlanGateWorkflowAdapter(
        prefix="v22-review-restart-second",
        invalid_closure=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: second)
    result = runner.resume(manifest.run_id)
    events = runner.state.list_events(manifest.run_id)
    current, recovered = _measure_pair(runner, manifest.run_id)
    assessment = assess_plan_feedback_request_pair(current, recovered)
    blocked = [
        event
        for event in events
        if event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("policy_version") == WORK_PLAN_ADMISSION_POLICY
    ]

    assert result["terminal_error"]["code"] == "WORK_PLAN_ADMISSION_REPEATED"
    assert assessment["candidate_preparation_pair_ready"] is True
    assert recovered["readiness_source"] == "recovered_pin"
    assert len(blocked) == 2
    assert not any(
        event.type == EventType.MODEL_CALLED and event.sequence > blocked[-1].sequence
        for event in events
    )
    assert not any(
        event.type == EventType.TOOL_SUCCEEDED and event.payload.get("tool") == "run_check"
        for event in events
    )


def test_review_rejects_durable_or_result_binding_tamper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest("run_v22_activation_review_binding_tamper")
    runner = AgentRunner(tmp_path / "v22-review-tamper")
    adapter = _PinnedPlanGateWorkflowAdapter(
        prefix="v22-review-tamper",
        invalid_closure=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    runner.start(TASK_PATH, model="mock", manifest=manifest)
    plans = _plan_requests(runner, manifest.run_id)
    failure = next(
        event
        for event in runner.state.list_events(manifest.run_id)
        if event.type == EventType.TOOL_FAILED and event.payload.get("tool") == "record_work_plan"
    )
    durable = failure.payload["error_details"]
    result_details = _load_result_details(failure)

    tampered_durable = copy.deepcopy(durable)
    tampered_durable["reason_codes"] = ["tampered"]
    with pytest.raises(ContractError, match="durable detail binding differs"):
        measure_plan_feedback_request_artifact(
            plans[1][2],
            durable_error_details=tampered_durable,
            result_error_details=tampered_durable,
        )

    tampered_result = copy.deepcopy(result_details)
    tampered_result["attempt"] = 2
    with pytest.raises(ContractError, match="durable result artifact differs"):
        measure_plan_feedback_request_artifact(
            plans[1][2],
            durable_error_details=durable,
            result_error_details=tampered_result,
        )


def test_activation_review_is_deterministic_source_bound_and_candidate_ready() -> None:
    first = build_plan_admission_feedback_activation_review(ROOT)
    second = build_plan_admission_feedback_activation_review(ROOT)

    assert review_bytes(first) == review_bytes(second)
    assert first["status"] == "candidate-preparation-ready"
    assert first["decision"]["candidate_preparation_ready"] is True
    assert first["decision"]["authority"] == "exact-no-call-candidate-preparation-only"
    assert first["decision"]["rapid_candidate_created"] is False
    assert first["decision"]["rehearsal_executed"] is False
    assert all(first["activation_criteria"].values())
    assert [item["path"] for item in first["source_files"]] == list(SOURCE_FILES)
    assert [item["path"] for item in first["immutable_inputs"]] == list(IMMUTABLE_INPUTS)
    assert all(
        first["evidence_boundary"][key] == 0
        for key in (
            "provider_calls",
            "docker_calls",
            "evaluator_calls",
            "visible_check_calls",
            "network_calls",
        )
    )
    assert first["provider_efficiency_established"] is False
    assert first["quality_improvement_established"] is False


def test_stored_plan_feedback_activation_review_is_a_byte_audit() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    value = json.loads(raw)

    assert raw == review_bytes(value)
    assert len(raw) == 6_574
    assert sha256_bytes(raw) == (
        "sha256:897204b88e598db7ecb156922f1a98659e49e60d93a273139e977d189e9270d2"
    )
    assert value["content_hash"] == (
        "sha256:d1194a9cbdc55cbe9b07c813ea032b0ecae6cf28fe5b55fea03c6e5b9871a18d"
    )
    assert value["decision"]["candidate_preparation_ready"] is True
