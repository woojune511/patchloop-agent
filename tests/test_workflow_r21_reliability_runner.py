from __future__ import annotations

import json
from pathlib import Path

import pytest

from patchloop.agent.lean_runtime import (
    LEAN_RUNTIME_POLICY_VERSION_V26,
    LeanHarnessRequestEvidenceV26,
    build_lean_harness_calibration_manifest,
    validate_persisted_lean_harness_request,
)
from patchloop.agent.model import ModelTurn, ModelTurnError, RequestedTool
from patchloop.agent.runner import AgentRunner
from patchloop.agent.workflow_r21_reliability_successor import (
    GENERATION_INCOMPLETE_RECOVERY_POLICY,
    LIFECYCLE_PLAN_POLICY,
    PLAN_ADMISSION_FEEDBACK_POLICY_V2,
)
from patchloop.contracts import EventType, MemoryCondition
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json
from tests.test_workflow_self_directed_exploration_runner import (
    TASK_PATH,
    _SelfDirectedWorkflowAdapter,
)
from tests.test_workflow_successor_v2_runner import TARGET_PATH


def _manifest(run_id: str):
    package = load_task_package("tasks/smoke/config-falsy-override")
    return build_lean_harness_calibration_manifest(
        package,
        run_id=run_id,
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V26,
    )


def _requests(runner: AgentRunner, run_id: str) -> list[LeanHarnessRequestEvidenceV26]:
    values: list[LeanHarnessRequestEvidenceV26] = []
    for event in runner.state.list_events(run_id):
        if event.type != EventType.MODEL_CALLED:
            continue
        payload = json.loads(
            Path(event.payload["request_artifact_path"]).read_text(encoding="utf-8")
        )
        raw = payload.get("lean_harness_request")
        if not isinstance(raw, dict) or raw.get("schema_version") != (
            "lean-harness-request-evidence-v26"
        ):
            continue
        evidence = validate_persisted_lean_harness_request(payload)
        assert isinstance(evidence, LeanHarnessRequestEvidenceV26)
        values.append(evidence)
    return values


def _lifecycle(arguments: dict) -> dict:
    mutation_span = arguments["causal_mechanism"]["mutation_site"]["source_span_id"]
    basis = arguments["readiness_assessment"]["basis_source_span_ids"]
    second_span = next((span for span in basis if span != mutation_span), mutation_span)
    return {
        "owners": [
            {
                "component": "configuration merger",
                "owner_source_span_id": mutation_span,
                "responsibility": "Own the public merge result transition.",
            },
            {
                "component": "base value preservation",
                "owner_source_span_id": second_span,
                "responsibility": "Preserve values for keys absent from the override.",
            },
        ],
        "states": [
            {
                "component": "configuration merger",
                "before": "falsey override is replaced",
                "after": "explicit override is retained",
            },
            {
                "component": "base value preservation",
                "before": "unmentioned base values are retained",
                "after": "unmentioned base values remain retained",
            },
        ],
        "transitions": [
            {
                "trigger": "An override key is iterated by the public merge loop.",
                "affected_components": [
                    "configuration merger",
                    "base value preservation",
                ],
                "evidence_source_span_ids": list(dict.fromkeys([mutation_span, second_span])),
                "atomic": True,
            }
        ],
        "atomic_postconditions": [
            {
                "condition": "Every present override wins while absent keys retain base values.",
                "evidence_source_span_ids": list(dict.fromkeys([mutation_span, second_span])),
                "falsification_observation": (
                    "A public check observes a falsey override replaced by its base value."
                ),
            }
        ],
    }


class _V26Adapter(_SelfDirectedWorkflowAdapter):
    def next_turn(self, context: str, tools: list[dict]) -> ModelTurn:
        parsed = json.loads(context)
        activated = parsed.get("workflow", {}).get("activated_exploration_plan_request")
        if isinstance(activated, dict) and activated.get("schema_version") == (
            "lifecycle-bound-self-directed-plan-request-v1"
        ):
            parsed["workflow"]["activated_exploration_plan_request"] = activated["source_request"]
        turn = super().next_turn(canonical_json(parsed), tools)
        if len(turn.tool_calls) == 1 and turn.tool_calls[0].name in {
            "record_work_plan",
            "revise_work_plan",
        }:
            turn.tool_calls[0].arguments["lifecycle_state_transition"] = _lifecycle(
                turn.tool_calls[0].arguments
            )
        return turn


class _IncompleteThenV26Adapter(_V26Adapter):
    def __init__(self, *, prefix: str, incomplete_count: int) -> None:
        super().__init__(prefix=prefix)
        self.incomplete_count = incomplete_count
        self.incomplete_emitted = 0
        self.recovery_context_seen = False

    def next_turn(self, context: str, tools: list[dict]) -> ModelTurn:
        parsed = json.loads(context)
        recovery = parsed.get("workflow", {}).get("generation_incomplete_recovery")
        if isinstance(recovery, dict) and recovery.get("used") is True:
            self.recovery_context_seen = True
        if self.incomplete_emitted < self.incomplete_count:
            self.incomplete_emitted += 1
            return ModelTurn(
                output_tokens=4_096,
                reasoning_output_tokens=4_096,
                total_tokens=4_096,
                response_status="incomplete",
                response_incomplete_reason="max_output_tokens",
                error=ModelTurnError(
                    code="incomplete_response",
                    message="synthetic reasoning-only incomplete response",
                ),
            )
        return super().next_turn(context, tools)


class _InvalidInitialPlanOnceAdapter(_V26Adapter):
    def __init__(self, *, prefix: str) -> None:
        super().__init__(prefix=prefix)
        self.plan_attempts = 0

    def next_turn(self, context: str, tools: list[dict]) -> ModelTurn:
        turn = super().next_turn(context, tools)
        if len(turn.tool_calls) == 1 and turn.tool_calls[0].name == "record_work_plan":
            self.plan_attempts += 1
            if self.plan_attempts == 1:
                turn.tool_calls[0].arguments["prior_hypothesis_disposition"] = "refined"
        return turn


class _CrashAfterGenerationRecovery(_IncompleteThenV26Adapter):
    def __init__(self, *, prefix: str) -> None:
        super().__init__(prefix=prefix, incomplete_count=1)

    def next_turn(self, context: str, tools: list[dict]) -> ModelTurn:
        recovery = json.loads(context).get("workflow", {}).get("generation_incomplete_recovery")
        if isinstance(recovery, dict) and recovery.get("used") is True:
            raise SystemExit(86)
        return super().next_turn(context, tools)


class _CaptureGenerationRecoveryAdapter(_V26Adapter):
    def __init__(self, *, prefix: str) -> None:
        super().__init__(prefix=prefix)
        self.recovered_state: dict | None = None

    def next_turn(self, context: str, tools: list[dict]) -> ModelTurn:
        recovery = json.loads(context).get("workflow", {}).get("generation_incomplete_recovery")
        if isinstance(recovery, dict) and recovery.get("used") is True:
            self.recovered_state = recovery
        return super().next_turn(context, tools)


class _AnchoredReadAdapter(_V26Adapter):
    def __init__(self, *, prefix: str) -> None:
        super().__init__(prefix=prefix)
        self.search_done = False
        self.anchor_done = False

    def next_turn(self, context: str, tools: list[dict]) -> ModelTurn:
        parsed = json.loads(context)
        workflow = parsed["workflow"]
        state = workflow.get("self_directed_exploration_state")
        names = {item["name"] for item in tools}
        if state is not None and not state["source_spans"] and "search_files" in names:
            if not self.search_done:
                self.search_done = True
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "search_files",
                            self._action_id("anchor-search"),
                            {
                                "query": "result[key] = value or result.get(key)",
                                "path_glob": TARGET_PATH,
                            },
                        )
                    ]
                )
            if not self.anchor_done:
                search_sequence = next(
                    event["sequence"]
                    for event in reversed(parsed["recent_events"])
                    if event.get("type") == "ToolSucceeded"
                    and event.get("payload", {}).get("tool") == "search_files"
                )
                self.anchor_done = True
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "read_file",
                            self._action_id("anchored-read"),
                            {
                                "search_anchor": {
                                    "search_event_sequence": search_sequence,
                                    "match_index": 0,
                                    "before_lines": 5,
                                    "after_lines": 5,
                                }
                            },
                        )
                    ]
                )
        return super().next_turn(context, tools)


def test_v26_full_mocked_runner_records_lifecycle_plan(tmp_path, monkeypatch) -> None:
    manifest = _manifest("run_v26_lifecycle_success")
    runner = AgentRunner(tmp_path / "v26-success")
    adapter = _V26Adapter(prefix="v26-success")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    requests = _requests(runner, manifest.run_id)

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert requests and all(item.tool_schema_version == "v27" for item in requests)
    assert any(
        event.type == EventType.PLAN_RECORDED
        and event.payload.get("lifecycle_state_transition", {}).get("policy_version")
        == LIFECYCLE_PLAN_POLICY
        for event in events
    )
    assert all(item.generation_incomplete_recovery_state.remaining == 1 for item in requests)


def test_v26_reasoning_incomplete_uses_dedicated_slot_then_completes(tmp_path, monkeypatch) -> None:
    manifest = _manifest("run_v26_generation_recovery")
    runner = AgentRunner(tmp_path / "v26-generation-recovery")
    adapter = _IncompleteThenV26Adapter(prefix="v26-recovery", incomplete_count=1)
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    dedicated = [
        event
        for event in events
        if event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("policy_version") == GENERATION_INCOMPLETE_RECOVERY_POLICY
    ]

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert len(dedicated) == 1
    assert dedicated[0].payload["shared_protocol_recovery_slot_consumed"] is False
    assert adapter.recovery_context_seen is True
    assert not any(
        event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("policy_version") == "shared-model-action-contract-recovery-v1"
        for event in events
    )


def test_v26_second_reasoning_incomplete_stops_without_third_dispatch(
    tmp_path, monkeypatch
) -> None:
    manifest = _manifest("run_v26_generation_repeated")
    runner = AgentRunner(tmp_path / "v26-generation-repeated")
    adapter = _IncompleteThenV26Adapter(prefix="v26-repeated", incomplete_count=2)
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)

    assert result["terminal_error"]["code"] == "MODEL_GENERATION_INCOMPLETE_REPEATED"
    assert sum(event.type == EventType.MODEL_CALLED for event in events) == 2
    assert (
        sum(
            event.type == EventType.TOOL_ADMISSION_BLOCKED
            and event.payload.get("policy_version") == GENERATION_INCOMPLETE_RECOVERY_POLICY
            for event in events
        )
        == 1
    )


def test_v26_generation_recovery_survives_restart_without_shared_slot(
    tmp_path, monkeypatch
) -> None:
    manifest = _manifest("run_v26_generation_restart")
    runner = AgentRunner(tmp_path / "v26-generation-restart")
    first = _CrashAfterGenerationRecovery(prefix="v26-restart-first")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: first)

    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK_PATH, model="mock", manifest=manifest)

    second = _CaptureGenerationRecoveryAdapter(prefix="v26-restart-second")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: second)
    result = runner.resume(manifest.run_id)
    events = runner.state.list_events(manifest.run_id)

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert second.recovered_state is not None
    assert second.recovered_state["remaining"] == 0
    assert (
        sum(
            event.type == EventType.TOOL_ADMISSION_BLOCKED
            and event.payload.get("policy_version") == GENERATION_INCOMPLETE_RECOVERY_POLICY
            for event in events
        )
        == 1
    )
    assert not any(
        event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("policy_version") == "shared-model-action-contract-recovery-v1"
        for event in events
    )


def test_v26_plan_rejection_feedback_is_compact_and_retry_completes(tmp_path, monkeypatch) -> None:
    manifest = _manifest("run_v26_compact_feedback")
    runner = AgentRunner(tmp_path / "v26-compact-feedback")
    adapter = _InvalidInitialPlanOnceAdapter(prefix="v26-feedback")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    requests = _requests(runner, manifest.run_id)
    projected = [
        item.plan_admission_feedback_projection
        for item in requests
        if item.plan_admission_feedback_projection.rejection_count
    ]

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert adapter.plan_attempts == 2
    assert projected
    assert projected[-1].policy_version == PLAN_ADMISSION_FEEDBACK_POLICY_V2
    assert projected[-1].latest_feedback_bytes <= 12_000
    retry_requests = [
        item for item in requests if item.plan_admission_feedback_projection.rejection_count
    ]
    assert (
        max(
            item.bounded_investigation_request_context.projected_context_bytes
            for item in retry_requests
        )
        < 90_000
    )


def test_v26_anchored_read_dispatches_exact_resolved_range(tmp_path, monkeypatch) -> None:
    manifest = _manifest("run_v26_anchored_read")
    runner = AgentRunner(tmp_path / "v26-anchored-read")
    adapter = _AnchoredReadAdapter(prefix="v26-anchor")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    anchored = next(
        event
        for event in events
        if event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "read_file"
        and event.payload.get("anchored_read_resolution") is not None
    )
    resolution = anchored.payload["anchored_read_resolution"]

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert adapter.search_done and adapter.anchor_done
    assert resolution["path"] == TARGET_PATH
    assert resolution["start_line"] <= resolution["match_line"] <= resolution["end_line"]
