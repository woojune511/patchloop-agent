from __future__ import annotations

import json
from pathlib import Path

import pytest

from patchloop.agent.lean_runtime import (
    LEAN_RUNTIME_POLICY_VERSION_V25,
    LeanHarnessRequestEvidenceV25,
    build_lean_harness_calibration_manifest,
    validate_persisted_lean_harness_request,
)
from patchloop.agent.model import ModelTurn, RequestedTool
from patchloop.agent.runner import AgentRunner
from patchloop.agent.workflow_self_directed_exploration_successor import (
    SELF_DIRECTED_EXPLORATION_POLICY,
)
from patchloop.contracts import EventType, MemoryCondition
from patchloop.errors import ContractError
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
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V25,
    )


def _requests(runner: AgentRunner, run_id: str) -> list[tuple[object, dict]]:
    values: list[tuple[object, dict]] = []
    for event in runner.state.list_events(run_id):
        if event.type != EventType.MODEL_CALLED:
            continue
        payload = json.loads(
            Path(event.payload["request_artifact_path"]).read_text(encoding="utf-8")
        )
        raw = payload.get("lean_harness_request")
        if not isinstance(raw, dict) or raw.get("schema_version") != (
            "lean-harness-request-evidence-v25"
        ):
            continue
        evidence = validate_persisted_lean_harness_request(payload)
        assert isinstance(evidence, LeanHarnessRequestEvidenceV25)
        values.append((event, payload))
    return values


def _plan_requests(runner: AgentRunner, run_id: str) -> list[tuple[object, dict]]:
    return [
        item
        for item in _requests(runner, run_id)
        if set(
            item[1]["lean_harness_request"]["workflow_decision"]["allowed_tool_names"]
        ).intersection({"record_work_plan", "revise_work_plan"})
    ]


class _InitialDispositionAdapter(_SelfDirectedWorkflowAdapter):
    def __init__(
        self,
        *,
        prefix: str,
        invalid_attempts: int,
        minimum_information_actions: int | None = None,
    ) -> None:
        super().__init__(prefix=prefix)
        self.invalid_attempts = invalid_attempts
        self.minimum_information_actions = minimum_information_actions
        self.plan_attempts = 0

    def next_turn(self, context: str, tools: list[dict]):
        workflow = json.loads(context)["workflow"]
        state = workflow.get("self_directed_exploration_state")
        names = {item["name"] for item in tools}
        if (
            self.minimum_information_actions is not None
            and state is not None
            and state["source_spans"]
            and state["information_actions_used"] < self.minimum_information_actions - 1
            and "search_files" in names
        ):
            used = state["information_actions_used"]
            self.calls += 1
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        "search_files",
                        self._action_id(f"r20-shaped-search-{used}"),
                        {
                            "query": f"r20-shape-{used}",
                            "path_glob": TARGET_PATH,
                            "investigation_intent": self._intent(
                                workflow,
                                target_role="falsification",
                            ),
                        },
                    )
                ]
            )
        turn = super().next_turn(context, tools)
        if len(turn.tool_calls) == 1 and turn.tool_calls[0].name == "record_work_plan":
            self.plan_attempts += 1
            if self.plan_attempts <= self.invalid_attempts:
                turn.tool_calls[0].arguments["prior_hypothesis_disposition"] = "refined"
        return turn


class _CrashBeforeCompatibleRetry(_InitialDispositionAdapter):
    def __init__(self, *, prefix: str) -> None:
        super().__init__(prefix=prefix, invalid_attempts=1)

    def next_turn(self, context: str, tools: list[dict]):
        if self.plan_attempts and "record_work_plan" in {item["name"] for item in tools}:
            raise SystemExit(86)
        return super().next_turn(context, tools)


def test_v25_initial_surface_is_null_only_and_success_path_completes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest("run_v25_trigger_bound_success")
    runner = AgentRunner(tmp_path / "v25-success")
    adapter = _SelfDirectedWorkflowAdapter(prefix="v25-success")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    plans = _plan_requests(runner, manifest.run_id)
    events = runner.state.list_events(manifest.run_id)

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert plans
    for _, payload in plans:
        request = payload["lean_harness_request"]["activated_exploration_plan_request"]
        assert request["parameters"]["properties"]["prior_hypothesis_disposition"] == {
            "type": "null",
            "enum": [None],
        }
    assert not any(
        event.type == EventType.TOOL_FAILED and event.payload.get("tool") == "record_work_plan"
        for event in events
    )


def test_v25_invalid_initial_plan_gets_one_bounded_retry_then_completes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest("run_v25_compatible_retry")
    runner = AgentRunner(tmp_path / "v25-retry")
    adapter = _InitialDispositionAdapter(prefix="v25-retry", invalid_attempts=1)
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    plans = _plan_requests(runner, manifest.run_id)
    events = runner.state.list_events(manifest.run_id)
    failures = [
        event
        for event in events
        if event.type == EventType.TOOL_FAILED and event.payload.get("tool") == "record_work_plan"
    ]

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert len(failures) == 1
    assert adapter.plan_attempts == 2
    assert failures[0].payload["error_details"]["policy_version"] == (
        SELF_DIRECTED_EXPLORATION_POLICY
    )
    retry_requests = [
        payload["lean_harness_request"]
        for _, payload in plans
        if payload["lean_harness_request"]["plan_admission_feedback_projection"][
            "projected_event_count"
        ]
        == 1
    ]
    assert retry_requests
    retry = retry_requests[-1]
    assert retry["plan_admission_feedback_projection"]["projected_event_count"] == 1
    feedback = next(
        event["payload"]["error_details"]
        for event in json.loads(retry["request_body"]["context"])["recent_events"]
        if event.get("type") == "ToolFailed"
        and isinstance(event.get("payload"), dict)
        and event["payload"].get("error_code") == "WORK_PLAN_ADMISSION_REJECTED"
    )
    assert feedback["policy_version"] == SELF_DIRECTED_EXPLORATION_POLICY
    assert sum(event.type == EventType.PLAN_RECORDED for event in events) == 1


@pytest.mark.parametrize(
    ("historical_run_id", "minimum_information_actions"),
    [
        ("run_rapid_v28_d7710f25ffd2_02", 8),
        ("run_rapid_v28_d7710f25ffd2_03", 9),
    ],
)
def test_v25_recovers_both_r20_invalid_initial_plan_shapes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    historical_run_id: str,
    minimum_information_actions: int,
) -> None:
    row_suffix = historical_run_id.rsplit("_", 1)[-1]
    manifest = _manifest(f"run_v25_r20_shape_{row_suffix}")
    runner = AgentRunner(tmp_path / historical_run_id)
    adapter = _InitialDispositionAdapter(
        prefix=f"r20-shape-{row_suffix}",
        invalid_attempts=1,
        minimum_information_actions=minimum_information_actions,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    first_failure = next(
        event
        for event in events
        if event.type == EventType.TOOL_FAILED and event.payload.get("tool") == "record_work_plan"
    )
    information_actions = [
        event
        for event in events
        if event.sequence < first_failure.sequence
        and event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") in {"read_file", "search_files"}
    ]

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert len(information_actions) == minimum_information_actions
    assert adapter.plan_attempts == 2


def test_v25_second_invalid_plan_stops_without_third_provider_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest("run_v25_compatible_repeated")
    runner = AgentRunner(tmp_path / "v25-repeated")
    adapter = _InitialDispositionAdapter(prefix="v25-repeated", invalid_attempts=99)
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    failures = [
        event
        for event in events
        if event.type == EventType.TOOL_FAILED and event.payload.get("tool") == "record_work_plan"
    ]

    assert result["terminal_error"]["code"] == "WORK_PLAN_ADMISSION_REPEATED"
    assert len(failures) == 2
    assert adapter.plan_attempts == 2
    assert not any(
        event.type == EventType.MODEL_CALLED and event.sequence > failures[-1].sequence
        for event in events
    )


def test_v25_retry_state_survives_restart_and_request_hash_tamper_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest("run_v25_compatible_restart")
    runner = AgentRunner(tmp_path / "v25-restart")
    first = _CrashBeforeCompatibleRetry(prefix="v25-restart-first")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: first)

    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK_PATH, model="mock", manifest=manifest)

    second = _SelfDirectedWorkflowAdapter(prefix="v25-restart-second")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: second)
    result = runner.resume(manifest.run_id)
    plans = _plan_requests(runner, manifest.run_id)

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert len(plans) >= 2
    assert (
        plans[-1][1]["lean_harness_request"]["plan_admission_feedback_projection"][
            "projected_event_count"
        ]
        == 1
    )

    tampered = json.loads(canonical_json(plans[-1][1]))
    request = tampered["lean_harness_request"]["activated_exploration_plan_request"]
    request["parameter_schema_hash"] = "sha256:" + "0" * 64
    with pytest.raises(ContractError):
        validate_persisted_lean_harness_request(tampered)
