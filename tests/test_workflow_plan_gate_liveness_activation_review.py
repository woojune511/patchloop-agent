from __future__ import annotations

import json
from pathlib import Path

import pytest

from patchloop.agent.lean_runtime import recover_plan_gate_readiness_pins
from patchloop.agent.runner import AgentRunner
from patchloop.agent.workflow_plan_gate_liveness_activation_review import (
    IMMUTABLE_INPUTS,
    QUALIFICATION_PATH,
    SOURCE_FILES,
    build_plan_gate_liveness_activation_review,
    measure_plan_request_artifact,
    project_compact_feedback_counterfactual,
    review_bytes,
)
from patchloop.contracts import EventType
from patchloop.errors import RecoveryError
from patchloop.util import sha256_bytes
from tests.test_workflow_successor_v2_runner import (
    TASK_PATH,
    _CrashBeforePinnedRetryAdapter,
    _PinnedPlanGateWorkflowAdapter,
    _v21_manifest,
    _v21_model_requests,
)

ROOT = Path(__file__).resolve().parents[1]


def _load_request(event) -> dict:
    return json.loads(Path(event.payload["request_artifact_path"]).read_text(encoding="utf-8"))


def test_review_measures_retry_feedback_without_calling_external_systems(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _v21_manifest("run_v21_activation_review_size")
    runner = AgentRunner(tmp_path / "review-size")
    adapter = _PinnedPlanGateWorkflowAdapter(prefix="v21-review", invalid_closure=True)
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    plan_requests = [
        (event, evidence)
        for event, evidence in _v21_model_requests(runner, manifest.run_id)
        if evidence["workflow_decision"]["allowed_tool_names"] == ["record_work_plan"]
    ]

    assert result["terminal_error"]["code"] == "WORK_PLAN_ADMISSION_REPEATED"
    assert len(plan_requests) == 2
    current = measure_plan_request_artifact(_load_request(plan_requests[0][0]))
    recovered_payload = _load_request(plan_requests[1][0])
    recovered = measure_plan_request_artifact(recovered_payload)
    projected = project_compact_feedback_counterfactual(recovered_payload)

    assert current["readiness_source"] == "current_request"
    assert recovered["readiness_source"] == "recovered_pin"
    assert recovered["canonical_request_body_bytes"] > (
        current["canonical_request_body_bytes"] + 40_000
    )
    assert recovered["plan_feedback_error_details_bytes"] > 30_000
    assert recovered["plan_feedback_nested_projection_bytes"] > 30_000
    assert projected["projected_saved_bytes"] > 30_000
    assert projected["durable_event_changed"] is False
    assert projected["implemented"] is False


def test_review_fails_closed_on_body_chain_and_missing_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _v21_manifest("run_v21_activation_review_faults")
    runner = AgentRunner(tmp_path / "review-faults")
    first = _CrashBeforePinnedRetryAdapter(prefix="v21-review-faults")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: first)

    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    plan_event = next(
        event
        for event, evidence in _v21_model_requests(runner, manifest.run_id)
        if evidence["workflow_decision"]["allowed_tool_names"] == ["record_work_plan"]
    )

    def loader(path: str, _artifact_hash: str) -> dict:
        return json.loads(Path(path).read_text(encoding="utf-8"))

    tampered_body = plan_event.model_copy(
        update={
            "payload": {
                **plan_event.payload,
                "request_body_hash": "sha256:" + "f" * 64,
            }
        }
    )
    tampered_events = tuple(
        tampered_body if event.sequence == plan_event.sequence else event for event in events
    )
    with pytest.raises(RecoveryError, match="request body binding differs"):
        recover_plan_gate_readiness_pins(
            run_id=manifest.run_id,
            events=tampered_events,
            request_artifact_loader=loader,
        )

    repeated_current_request = plan_event.model_copy(
        update={
            "event_id": "evt_v21_activation_review_chain_tamper",
            "sequence": max(event.sequence for event in events) + 1,
        }
    )
    with pytest.raises(RecoveryError, match="pin chain differs"):
        recover_plan_gate_readiness_pins(
            run_id=manifest.run_id,
            events=(*events, repeated_current_request),
            request_artifact_loader=loader,
        )

    artifact_path = Path(plan_event.payload["request_artifact_path"])
    artifact_path.unlink()
    prior_max_sequence = max(event.sequence for event in events)
    resumed = runner.resume(manifest.run_id)
    assert resumed["terminal_error"] == {
        "code": "RECOVERY_ERROR",
        "message": "plan-gate request artifact is unavailable",
        "type": "RecoveryError",
    }
    assert not any(
        event.type == EventType.MODEL_CALLED and event.sequence > prior_max_sequence
        for event in runner.state.list_events(manifest.run_id)
    )


def test_activation_review_is_deterministic_source_bound_and_candidate_blocking() -> None:
    first = build_plan_gate_liveness_activation_review(ROOT)
    second = build_plan_gate_liveness_activation_review(ROOT)

    assert review_bytes(first) == review_bytes(second)
    assert first["status"] == "candidate-preparation-blocked"
    assert first["decision"]["candidate_preparation_ready"] is False
    assert first["decision"]["rapid_candidate_created"] is False
    assert first["decision"]["blocking_failure_class"] == (
        "model-visible-plan-admission-feedback-bloat"
    )
    assert first["counterfactual_compact_projection"]["implemented"] is False
    assert [item["path"] for item in first["source_files"]] == list(SOURCE_FILES)
    assert [item["path"] for item in first["immutable_inputs"]] == list(IMMUTABLE_INPUTS)
    assert all(
        first["evidence_boundary"][key] == 0
        for key in ("provider_calls", "docker_calls", "evaluator_calls", "network_calls")
    )


def test_stored_activation_review_is_a_byte_audit() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    value = json.loads(raw)

    assert raw == review_bytes(value)
    assert sha256_bytes(raw).startswith("sha256:")
