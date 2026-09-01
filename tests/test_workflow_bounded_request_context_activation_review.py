from __future__ import annotations

import json
from pathlib import Path

import pytest

from patchloop.agent.runner import AgentRunner
from patchloop.agent.workflow_bounded_request_context_activation_review import (
    IMMUTABLE_INPUTS,
    QUALIFICATION_PATH,
    SOURCE_FILES,
    assess_bounded_request_series,
    build_bounded_request_context_activation_review,
    measure_bounded_request,
    review_bytes,
)
from patchloop.agent.workflow_self_directed_exploration_activation_review import (
    audit_invalid_intent_recovery,
)
from patchloop.contracts import EventType
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes
from tests.test_workflow_bounded_request_context_runner import (
    _manifest,
    _request_payloads,
)
from tests.test_workflow_self_directed_exploration_runner import (
    TASK_PATH,
    _SelfDirectedWorkflowAdapter,
)

ROOT = Path(__file__).resolve().parents[1]


def _inside(value: int | float, bounds: dict[str, int | float]) -> bool:
    return bounds["min"] <= value <= bounds["max"]


def test_v24_activation_measures_exact_zero_to_limit_series(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest("run_v24_activation_zero_to_limit")
    runner = AgentRunner(tmp_path / "v24-activation-limit")
    adapter = _SelfDirectedWorkflowAdapter(prefix="v24-activation", exhaust=True)
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    measurements = [
        measure_bounded_request(payload) for payload in _request_payloads(runner, manifest.run_id)
    ]
    assessment = assess_bounded_request_series(measurements)
    declared = build_bounded_request_context_activation_review(ROOT)[
        "observed_offline_public_mock_sample"
    ]

    assert result["terminal_error"]["code"] == "SELF_DIRECTED_EXPLORATION_EXHAUSTED"
    assert assessment["candidate_preparation_series_ready"] is True
    assert all(assessment["contract_checks"].values())
    assert all(assessment["inherited_envelope_checks"].values())
    assert _inside(
        assessment["zero_source_request_body_bytes"],
        declared["zero_source_request_body_bytes"],
    )
    assert _inside(
        assessment["first_choice_request_body_bytes"],
        declared["first_source_choice_request_body_bytes"],
    )
    assert _inside(
        assessment["max_recovered_request_body_bytes"],
        declared["max_recovered_request_body_bytes"],
    )
    assert _inside(
        assessment["limit_request_body_bytes"],
        declared["limit_request_body_bytes"],
    )
    assert _inside(
        assessment["max_recovered_growth_ratio"],
        declared["max_recovered_growth_ratio"],
    )
    assert not any(
        event.type == EventType.TOOL_SUCCEEDED and event.payload.get("tool") == "run_check"
        for event in events
    )
    assert not any(event.type == EventType.PATCH_APPLIED for event in events)
    assert not any(event.type == EventType.SUBMISSION_ACCEPTED for event in events)


def test_v24_activation_inherits_bounded_invalid_intent_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest("run_v24_activation_invalid_intent")
    runner = AgentRunner(tmp_path / "v24-activation-invalid")
    adapter = _SelfDirectedWorkflowAdapter(
        prefix="v24-activation-invalid",
        invalid_intent=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    audit = audit_invalid_intent_recovery(runner.state.list_events(manifest.run_id))

    assert result["terminal_error"]["code"] == "MODEL_ACTION_CONTRACT_REPEATED"
    assert audit["candidate_recovery_ready"] is True
    assert audit["provider_calls"] == audit["visible_check_calls"] == 0


def test_v24_activation_measurement_fails_closed_on_request_tamper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest("run_v24_activation_tamper")
    runner = AgentRunner(tmp_path / "v24-activation-tamper")
    adapter = _SelfDirectedWorkflowAdapter(prefix="v24-activation-tamper", exhaust=True)
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    runner.start(TASK_PATH, model="mock", manifest=manifest)
    payload = _request_payloads(runner, manifest.run_id)[1]
    tampered = json.loads(canonical_json(payload))
    tampered["lean_harness_request"]["request_body"]["tools"] = []

    with pytest.raises(ContractError):
        measure_bounded_request(tampered)


def test_v24_activation_review_is_deterministic_and_candidate_noncreating() -> None:
    first = build_bounded_request_context_activation_review(ROOT)
    second = build_bounded_request_context_activation_review(ROOT)

    assert review_bytes(first) == review_bytes(second)
    assert first["status"] == "activation-reviewed-candidate-decision-ready"
    assert first["decision"]["candidate_preparation_ready"] is True
    assert first["decision"]["candidate_created"] is False
    assert first["candidate_created"] is False
    assert [item["path"] for item in first["source_files"]] == list(SOURCE_FILES)
    assert [item["path"] for item in first["immutable_inputs"]] == list(IMMUTABLE_INPUTS)
    assert first["external_calls"] == 0
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


def test_stored_v24_activation_review_is_a_byte_audit() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    value = json.loads(raw)

    assert raw == review_bytes(value)
    assert sha256_bytes(raw).startswith("sha256:")
