from __future__ import annotations

import json
from pathlib import Path

import pytest

from patchloop.agent.runner import AgentRunner
from patchloop.agent.workflow_self_directed_exploration_activation_review import (
    IMMUTABLE_INPUTS,
    INHERITED_REQUEST_ENVELOPES,
    QUALIFICATION_PATH,
    SOURCE_FILES,
    assess_self_directed_exploration_request_series,
    audit_invalid_intent_recovery,
    build_self_directed_exploration_activation_review,
    measure_self_directed_exploration_request,
    project_bounded_context_counterfactual,
    review_bytes,
)
from patchloop.contracts import EventType
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes
from tests.test_workflow_self_directed_exploration_runner import (
    TASK_PATH,
    _CrashAfterCoverageAdapter,
    _manifest,
    _SelfDirectedWorkflowAdapter,
)

ROOT = Path(__file__).resolve().parents[1]


def _request_payloads(runner: AgentRunner, run_id: str) -> list[dict]:
    values: list[dict] = []
    for event in runner.state.list_events(run_id):
        if event.type != EventType.MODEL_CALLED:
            continue
        values.append(
            json.loads(Path(event.payload["request_artifact_path"]).read_text(encoding="utf-8"))
        )
    return values


def test_review_measures_zero_to_limit_surface_and_size_without_checks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest("run_v23_explicit_exhaustion")
    runner = AgentRunner(tmp_path / "review-limit")
    adapter = _SelfDirectedWorkflowAdapter(prefix="v23-exhaust", exhaust=True)
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    payloads = _request_payloads(runner, manifest.run_id)
    measurements = [measure_self_directed_exploration_request(item) for item in payloads]
    assessment = assess_self_directed_exploration_request_series(measurements)
    limit_payload = next(
        payload
        for payload, measurement in zip(payloads, measurements, strict=True)
        if measurement["information_actions_used"] == 10
    )
    projected = project_bounded_context_counterfactual(limit_payload)

    assert result["terminal_error"]["code"] == "SELF_DIRECTED_EXPLORATION_EXHAUSTED"
    assert not any(
        event.type == EventType.TOOL_SUCCEEDED and event.payload.get("tool") == "run_check"
        for event in events
    )
    assert not any(event.type == EventType.PATCH_APPLIED for event in events)
    assert not any(event.type == EventType.SUBMISSION_ACCEPTED for event in events)
    assert len(measurements) == 11
    assert measurements[0]["allowed_tool_names"] == (
        "search_files",
        "read_file",
        "run_check",
    )
    assert measurements[1]["allowed_tool_names"] == (
        "search_files",
        "read_file",
        "run_check",
        "record_work_plan",
    )
    assert assessment["contract_checks"]["zero_source_surface_exact"] is False
    assert assessment["contract_checks"]["source_available_surface_exact"] is False
    assert assessment["contract_checks"]["run_check_absent_before_plan"] is False
    assert assessment["max_recent_investigation_card_count"] == 3
    assert assessment["max_investigation_ledger_recent_detail_count"] == 10
    assert 62_700 <= assessment["first_choice_request_body_bytes"] <= 62_800
    assert 98_500 <= assessment["max_recovered_request_body_bytes"] <= 98_800
    assert 97_000 <= assessment["limit_request_body_bytes"] <= 97_300
    assert 1.57 <= assessment["max_recovered_growth_ratio"] <= 1.58
    assert assessment["inherited_envelope_checks"] == {
        "first_choice_within_current_ceiling": True,
        "all_recovered_choices_within_recovered_ceiling": False,
        "recovered_growth_within_predecessor_ceiling": False,
    }
    assert assessment["candidate_preparation_series_ready"] is False
    assert projected["implemented"] is False
    assert projected["valid_v23_request_claimed"] is False
    assert 85_000 <= projected["projected_request_body_bytes"] <= 85_300
    assert 11_800 <= projected["projected_saved_bytes"] <= 12_100
    assert projected["retained_raw_source_content_count"] == 1
    assert (
        projected["projected_request_body_bytes"]
        <= (INHERITED_REQUEST_ENVELOPES["recovered_request_max_bytes"])
    )


def test_review_audits_shared_recovery_without_tool_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest("run_v23_activation_invalid_intent")
    runner = AgentRunner(tmp_path / "review-recovery")
    adapter = _SelfDirectedWorkflowAdapter(prefix="v23-review-invalid", invalid_intent=True)
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    audit = audit_invalid_intent_recovery(runner.state.list_events(manifest.run_id))

    assert result["terminal_error"]["code"] == "MODEL_ACTION_CONTRACT_REPEATED"
    assert audit["candidate_recovery_ready"] is True
    assert all(audit["checks"].values())
    assert audit["provider_calls"] == audit["visible_check_calls"] == 0


class _CaptureRestartAndCrashAdapter(_SelfDirectedWorkflowAdapter):
    def __init__(self, *, prefix: str) -> None:
        super().__init__(prefix=prefix)
        self.first_context: str | None = None
        self.first_tools: list[dict] | None = None

    def next_turn(self, context: str, tools: list[dict]):
        self.first_context = context
        self.first_tools = tools
        raise SystemExit(87)


def test_review_restart_reuses_identical_bounded_state_and_surface(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest("run_v23_activation_restart")
    runner = AgentRunner(tmp_path / "review-restart")
    first = _CrashAfterCoverageAdapter(prefix="v23-review-restart-first")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: first)

    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK_PATH, model="mock", manifest=manifest)
    assert first.captured_state is not None
    assert first.captured_tool_names is not None

    second = _CaptureRestartAndCrashAdapter(prefix="v23-review-restart-second")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: second)
    with pytest.raises(SystemExit, match="87"):
        runner.resume(manifest.run_id)

    assert second.first_context is not None
    restarted_workflow = json.loads(second.first_context)["workflow"]
    assert restarted_workflow["self_directed_exploration_state"] == first.captured_state
    assert tuple(item["name"] for item in second.first_tools or []) == first.captured_tool_names
    events = runner.state.list_events(manifest.run_id)
    assert not any(
        event.type == EventType.TOOL_SUCCEEDED and event.payload.get("tool") == "run_check"
        for event in events
    )
    assert not any(event.type == EventType.PATCH_APPLIED for event in events)


def test_measurement_fails_closed_on_request_tamper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest("run_v23_activation_tamper")
    runner = AgentRunner(tmp_path / "review-tamper")
    adapter = _SelfDirectedWorkflowAdapter(prefix="v23-review-tamper", exhaust=True)
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    runner.start(TASK_PATH, model="mock", manifest=manifest)
    payload = _request_payloads(runner, manifest.run_id)[0]
    tampered = json.loads(canonical_json(payload))
    tampered["request_body"]["tools"] = []

    with pytest.raises(ContractError):
        measure_self_directed_exploration_request(tampered)


def test_activation_review_is_deterministic_source_bound_and_candidate_blocking() -> None:
    first = build_self_directed_exploration_activation_review(ROOT)
    second = build_self_directed_exploration_activation_review(ROOT)

    assert review_bytes(first) == review_bytes(second)
    assert first["status"] == "candidate-preparation-blocked"
    assert first["decision"]["candidate_preparation_ready"] is False
    assert first["decision"]["rapid_candidate_created"] is False
    assert first["decision"]["blocking_failure_class"] == (
        "self-directed-pre-plan-request-contract-mismatch"
    )
    assert first["decision"]["runtime_source_change_in_this_review"] is False
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


def test_stored_self_directed_activation_review_is_a_byte_audit() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    value = json.loads(raw)

    assert raw == review_bytes(value)
    assert sha256_bytes(raw).startswith("sha256:")
