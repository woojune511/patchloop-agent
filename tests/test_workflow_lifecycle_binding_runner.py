from __future__ import annotations

import json
from pathlib import Path

import pytest

from patchloop.agent.lean_runtime import (
    LEAN_RUNTIME_POLICY_VERSION_V28,
    LeanHarnessRequestEvidenceV28,
    build_lean_harness_calibration_manifest,
    validate_persisted_lean_harness_request,
)
from patchloop.agent.model import ModelTurn
from patchloop.agent.runner import AgentRunner
from patchloop.agent.workflow_lifecycle_binding_successor import (
    LIFECYCLE_COMPONENT_BINDING_POLICY,
    PLAN_ADMISSION_FEEDBACK_POLICY_V3,
)
from patchloop.contracts import EventType, MemoryCondition
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json
from tests.test_workflow_self_directed_exploration_runner import (
    TASK_PATH,
    _SelfDirectedWorkflowAdapter,
)


def _manifest(run_id: str):
    package = load_task_package("tasks/smoke/config-falsy-override")
    return build_lean_harness_calibration_manifest(
        package,
        run_id=run_id,
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V28,
    )


def _requests(runner: AgentRunner, run_id: str) -> list[LeanHarnessRequestEvidenceV28]:
    values: list[LeanHarnessRequestEvidenceV28] = []
    for event in runner.state.list_events(run_id):
        if event.type != EventType.MODEL_CALLED:
            continue
        payload = json.loads(
            Path(event.payload["request_artifact_path"]).read_text(encoding="utf-8")
        )
        raw = payload.get("lean_harness_request")
        if not isinstance(raw, dict) or raw.get("schema_version") != (
            "lean-harness-request-evidence-v28"
        ):
            continue
        evidence = validate_persisted_lean_harness_request(payload)
        assert isinstance(evidence, LeanHarnessRequestEvidenceV28)
        values.append(evidence)
    return values


def _lifecycle(arguments: dict) -> dict:
    mutation_span = arguments["causal_mechanism"]["mutation_site"]["source_span_id"]
    basis = arguments["readiness_assessment"]["basis_source_span_ids"]
    second_span = next((span for span in basis if span != mutation_span), mutation_span)
    return {
        "components": [
            {
                "name": "configuration merger",
                "owner_source_span_id": mutation_span,
                "responsibility": "Own the public merge result transition.",
                "before": "falsey override is replaced",
                "after": "explicit override is retained",
            },
            {
                "name": "base value preservation",
                "owner_source_span_id": second_span,
                "responsibility": "Preserve values for keys absent from the override.",
                "before": "base values are retained",
                "after": "base values remain retained",
            },
        ],
        "transitions": [
            {
                "trigger": "An override key is iterated by the public merge loop.",
                "affected_component_indices": [0, 1],
                "evidence_source_span_ids": list(dict.fromkeys([mutation_span, second_span])),
                "atomic": True,
            }
        ],
        "atomic_postconditions": [
            {
                "condition": "Present overrides win while absent keys retain base values.",
                "evidence_source_span_ids": list(dict.fromkeys([mutation_span, second_span])),
                "falsification_observation": (
                    "A public check observes a falsey override replaced by its base value."
                ),
            }
        ],
    }


class _V28Adapter(_SelfDirectedWorkflowAdapter):
    def __init__(self, *, prefix: str, invalid_first_plan: bool = False) -> None:
        super().__init__(prefix=prefix)
        self.invalid_first_plan = invalid_first_plan
        self.plan_attempts = 0
        self.feedback_mismatches: list[dict] = []

    def next_turn(self, context: str, tools: list[dict]) -> ModelTurn:
        parsed = json.loads(context)
        for event in parsed.get("recent_events", []):
            details = event.get("payload", {}).get("error_details")
            mismatch = (
                details.get("lifecycle_relation_mismatch") if isinstance(details, dict) else None
            )
            if isinstance(mismatch, dict) and (
                not self.feedback_mismatches
                or self.feedback_mismatches[-1].get("content_hash") != mismatch.get("content_hash")
            ):
                self.feedback_mismatches.append(mismatch)
        activated = parsed.get("workflow", {}).get("activated_exploration_plan_request")
        if isinstance(activated, dict) and activated.get("schema_version") == (
            "lifecycle-component-bound-self-directed-plan-request-v2"
        ):
            parsed["workflow"]["activated_exploration_plan_request"] = activated["source_request"]
        turn = super().next_turn(canonical_json(parsed), tools)
        if len(turn.tool_calls) == 1 and turn.tool_calls[0].name == "read_file":
            arguments = turn.tool_calls[0].arguments
            for key in ("path", "start_line", "end_line", "search_anchor"):
                arguments.setdefault(key, None)
        if len(turn.tool_calls) == 1 and turn.tool_calls[0].name in {
            "record_work_plan",
            "revise_work_plan",
        }:
            self.plan_attempts += 1
            lifecycle = _lifecycle(turn.tool_calls[0].arguments)
            if self.invalid_first_plan and self.plan_attempts == 1:
                lifecycle["transitions"][0]["affected_component_indices"] = [0, 2]
            turn.tool_calls[0].arguments["lifecycle_component_binding"] = lifecycle
        return turn


class _CrashOnFeedbackAdapter(_V28Adapter):
    def next_turn(self, context: str, tools: list[dict]) -> ModelTurn:
        parsed = json.loads(context)
        has_feedback = any(
            isinstance(event.get("payload", {}).get("error_details"), dict)
            and isinstance(
                event["payload"]["error_details"].get("lifecycle_relation_mismatch"),
                dict,
            )
            for event in parsed.get("recent_events", [])
        )
        if has_feedback:
            super().next_turn(context, tools)
            raise SystemExit(84)
        return super().next_turn(context, tools)


class _AlwaysInvalidV28Adapter(_V28Adapter):
    def next_turn(self, context: str, tools: list[dict]) -> ModelTurn:
        turn = super().next_turn(context, tools)
        if len(turn.tool_calls) == 1 and turn.tool_calls[0].name in {
            "record_work_plan",
            "revise_work_plan",
        }:
            turn.tool_calls[0].arguments["lifecycle_component_binding"]["transitions"][0][
                "affected_component_indices"
            ] = [0, 2]
        return turn


def test_v28_full_mocked_runner_records_component_registry(tmp_path, monkeypatch) -> None:
    manifest = _manifest("run_v28_component_success")
    runner = AgentRunner(tmp_path / "v28-success")
    adapter = _V28Adapter(prefix="v28-success")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    requests = _requests(runner, manifest.run_id)

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert requests and all(item.tool_schema_version == "v29" for item in requests)
    plan_event = next(
        event
        for event in events
        if event.type == EventType.PLAN_RECORDED
        and event.payload.get("lifecycle_component_binding") is not None
    )
    lifecycle = plan_event.payload["lifecycle_component_binding"]
    assert lifecycle["policy_version"] == LIFECYCLE_COMPONENT_BINDING_POLICY
    assert lifecycle["lifecycle"]["transitions"][0]["affected_component_indices"] == [0, 1]
    assert "owners" not in lifecycle["lifecycle"]
    assert plan_event.payload["lifecycle_component_binding_hash"] == lifecycle["content_hash"]


def test_v28_exact_relation_feedback_recovers_once_without_loop(tmp_path, monkeypatch) -> None:
    manifest = _manifest("run_v28_relation_feedback")
    runner = AgentRunner(tmp_path / "v28-feedback")
    adapter = _V28Adapter(prefix="v28-feedback", invalid_first_plan=True)
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    requests = _requests(runner, manifest.run_id)
    blocked = [
        event
        for event in runner.state.list_events(manifest.run_id)
        if event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("policy_version") == "bounded-self-directed-exploration-v1"
    ]
    rejected = [
        event
        for event in runner.state.list_events(manifest.run_id)
        if event.type == EventType.TOOL_FAILED
        and event.payload.get("error_code") == "WORK_PLAN_ADMISSION_REJECTED"
    ]
    projected = [
        item.plan_admission_feedback_projection
        for item in requests
        if item.plan_admission_feedback_projection.rejection_count
    ]

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert adapter.plan_attempts == 2
    assert len(blocked) == 1
    assert len(rejected) == 1
    mismatch = rejected[0].payload["error_details"]["lifecycle_relation_mismatch"]
    assert mismatch["component_count"] == 2
    assert mismatch["transition_reference_violations"][0]["out_of_range_component_indices"] == [2]
    assert adapter.feedback_mismatches[-1] == mismatch
    assert projected[-1].policy_version == PLAN_ADMISSION_FEEDBACK_POLICY_V3
    assert projected[-1].latest_relation_mismatch_hash == mismatch["content_hash"]


def test_v28_feedback_and_recovery_slot_survive_restart(tmp_path, monkeypatch) -> None:
    manifest = _manifest("run_v28_relation_restart")
    runner = AgentRunner(tmp_path / "v28-restart")
    first = _CrashOnFeedbackAdapter(
        prefix="v28-restart-first",
        invalid_first_plan=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: first)

    with pytest.raises(SystemExit, match="84"):
        runner.start(TASK_PATH, model="mock", manifest=manifest)
    before_rejection = next(
        event
        for event in runner.state.list_events(manifest.run_id)
        if event.type == EventType.TOOL_FAILED
        and event.payload.get("error_code") == "WORK_PLAN_ADMISSION_REJECTED"
    )
    before_hash = before_rejection.payload["error_details"]["lifecycle_relation_mismatch"][
        "content_hash"
    ]

    second = _V28Adapter(prefix="v28-restart-second")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: second)
    result = runner.resume(manifest.run_id)
    after = [
        item
        for item in _requests(runner, manifest.run_id)
        if item.plan_admission_feedback_projection.latest_relation_mismatch_hash
    ]
    blocked = [
        event
        for event in runner.state.list_events(manifest.run_id)
        if event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("policy_version") == "bounded-self-directed-exploration-v1"
    ]

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert len(blocked) == 1
    assert all(
        item.plan_admission_feedback_projection.latest_relation_mismatch_hash == before_hash
        for item in after
    )
    assert second.feedback_mismatches[-1]["content_hash"] == before_hash


def test_v28_second_relation_rejection_stops_without_third_plan_dispatch(
    tmp_path, monkeypatch
) -> None:
    manifest = _manifest("run_v28_relation_repeated")
    runner = AgentRunner(tmp_path / "v28-repeated")
    adapter = _AlwaysInvalidV28Adapter(prefix="v28-repeated")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    rejected = [
        event
        for event in events
        if event.type == EventType.TOOL_FAILED
        and event.payload.get("error_code") == "WORK_PLAN_ADMISSION_REJECTED"
    ]
    blocked = [
        event
        for event in events
        if event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("policy_version") == "bounded-self-directed-exploration-v1"
    ]
    plan_calls = [
        event
        for event in events
        if event.type == EventType.TOOL_CALLED
        and event.payload.get("tool") in {"record_work_plan", "revise_work_plan"}
    ]

    assert result["scope_compliant_success"] is False
    assert result["terminal_error"]["code"] == "WORK_PLAN_ADMISSION_REPEATED"
    assert adapter.plan_attempts == 2
    assert len(plan_calls) == 2
    assert len(rejected) == 2
    assert len(blocked) == 2
    assert rejected[-1].payload["error_details"]["lifecycle_relation_mismatch"][
        "transition_reference_violations"
    ][0]["out_of_range_component_indices"] == [2]
