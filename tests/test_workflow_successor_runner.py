from __future__ import annotations

import json

import pytest

from patchloop.agent.model import ModelTurn, RequestedTool
from patchloop.agent.runner import AgentRunner
from patchloop.agent.workflow_successor import PROTOCOL_RECOVERY_POLICY
from patchloop.contracts import Budget, EventType, Phase, RunManifest
from patchloop.memory.fixed_bundle import FIXED_BUNDLE_POLICY_VERSION
from patchloop.runtime import build_manifest
from patchloop.task_loader import load_task_package

TASK_PATH = "tasks/smoke/config-falsy-override/public.yaml"
TARGET_PATH = "mini_data_utils/config.py"


def _successor_manifest(*, run_id: str, version: int) -> RunManifest:
    package = load_task_package("tasks/smoke/config-falsy-override")
    manifest = build_manifest(
        package,
        run_id=run_id,
        provider="mock",
        model_id="patchloop-public-calibration-mock-v1",
        memory_policy_version=FIXED_BUNDLE_POLICY_VERSION,
        sandbox_backend="local",
        budget=Budget(
            max_model_calls=240,
            max_tool_calls=400,
            max_total_tokens=1_100_000,
            wall_clock_timeout_seconds=3_600,
            token_budget_schema_version="cumulative-split-v1",
            max_cumulative_input_tokens=1_000_000,
            max_cumulative_output_tokens=100_000,
        ),
        max_output_tokens=25_000,
    )
    payload = manifest.model_dump(mode="python")
    payload["tool_schema_version"] = "v13" if version == 9 else "v14"
    payload["context_policy_version"] = (
        "phase-evidence-v19" if version == 9 else "phase-evidence-v20"
    )
    payload["model"]["temperature"] = 0.0
    return RunManifest.model_validate(payload)


class _RepeatedUnavailableAdapter:
    def __init__(self) -> None:
        self.calls = 0

    def next_turn(self, _context, _tools):
        self.calls += 1
        return ModelTurn(
            tool_calls=[
                RequestedTool(
                    "unavailable_tool",
                    f"unavailable-{self.calls}",
                    {},
                )
            ]
        )


class _CrashAfterOneRecoveryAdapter(_RepeatedUnavailableAdapter):
    def next_turn(self, context, tools):
        if self.calls == 1:
            raise SystemExit(86)
        return super().next_turn(context, tools)


class _V10PublicPlanAdapter:
    def __init__(self, runner: AgentRunner, run_id: str, *, crash_after_plan: bool = False) -> None:
        self.runner = runner
        self.run_id = run_id
        self.crash_after_plan = crash_after_plan
        self.crashed = False

    def next_turn(self, context: str, tools: list[dict]) -> ModelTurn:
        names = tuple(item["name"] for item in tools)
        payload = json.loads(context)
        workflow = payload["workflow"]
        assert workflow["available_tool_names"] == list(names)
        if (
            self.crash_after_plan
            and not self.crashed
            and "apply_structured_edit" in names
            and any(
                event.type == EventType.PLAN_RECORDED
                for event in self.runner.state.list_events(self.run_id)
            )
        ):
            self.crashed = True
            raise SystemExit(86)
        if "record_work_plan" in names:
            read_event = next(
                event
                for event in reversed(self.runner.state.list_events(self.run_id))
                if event.type == EventType.TOOL_SUCCEEDED
                and event.payload.get("tool") == "read_file"
            )
            check_ids = workflow["public_task_spec"]["visible_check_ids"]
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        "record_work_plan",
                        "v10-record-plan",
                        {
                            "reproduction_status": "static_evidence",
                            "hypothesis": (
                                "The override path uses truthiness instead of presence."
                            ),
                            "evidence_event_sequences": [read_event.sequence],
                            "candidate_files": [TARGET_PATH],
                            "planned_check_ids": check_ids,
                            "unknowns": [],
                        },
                    )
                ]
            )
        if "finish_task" in names:
            return ModelTurn(tool_calls=[RequestedTool("finish_task", "v10-finish", {})])
        if "apply_structured_edit" in names:
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        "apply_structured_edit",
                        "v10-structured-edit",
                        {
                            "schema_version": "structured-edit-arguments-v2",
                            "files": [
                                {
                                    "path": TARGET_PATH,
                                    "replacements": [
                                        {
                                            "expected_text": (
                                                "result[key] = value or result.get(key)"
                                            ),
                                            "replacement_text": "result[key] = value",
                                        }
                                    ],
                                }
                            ],
                        },
                    )
                ]
            )
        if "read_file" in names and not any(
            event.type == EventType.TOOL_SUCCEEDED and event.payload.get("tool") == "read_file"
            for event in self.runner.state.list_events(self.run_id)
        ):
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        "read_file",
                        "v10-initial-read",
                        {"path": TARGET_PATH, "start_line": 1, "end_line": 120},
                    )
                ]
            )
        if "run_check" in names:
            run_check = next(item for item in tools if item["name"] == "run_check")
            check_id = run_check["parameters"]["properties"]["check_id"]["enum"][0]
            check_call_count = sum(
                event.type == EventType.TOOL_CALLED and event.payload.get("tool") == "run_check"
                for event in self.runner.state.list_events(self.run_id)
            )
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        "run_check",
                        f"v10-visible-check-{check_call_count + 1}",
                        {"check_id": check_id},
                    )
                ]
            )
        if names == ("get_diff",):
            diff_call_count = sum(
                event.type == EventType.TOOL_CALLED and event.payload.get("tool") == "get_diff"
                for event in self.runner.state.list_events(self.run_id)
            )
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        "get_diff",
                        f"v10-final-diff-{diff_call_count + 1}",
                        {},
                    )
                ]
            )
        raise AssertionError(f"unexpected V10 tool surface: {names}")


class _V10DoubleReviewCorrectionAdapter(_V10PublicPlanAdapter):
    def next_turn(self, context: str, tools: list[dict]) -> ModelTurn:
        names = tuple(item["name"] for item in tools)
        if "finish_task" in names:
            patch_count = sum(
                event.type == EventType.PATCH_APPLIED
                for event in self.runner.state.list_events(self.run_id)
            )
            expected_text = (
                "result[key] = value"
                if patch_count == 1
                else "result[key] = value  # preserve falsy overrides"
            )
            replacement_text = (
                "result[key] = value  # preserve falsy overrides"
                if patch_count == 1
                else "result[key] = value  # keep explicit falsy overrides"
            )
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        "apply_structured_edit",
                        f"v10-review-correction-{patch_count}",
                        {
                            "schema_version": "structured-edit-arguments-v2",
                            "files": [
                                {
                                    "path": TARGET_PATH,
                                    "replacements": [
                                        {
                                            "expected_text": expected_text,
                                            "replacement_text": replacement_text,
                                        }
                                    ],
                                }
                            ],
                        },
                    )
                ]
            )
        return super().next_turn(context, tools)


def test_v9_shared_protocol_recovery_is_one_use_and_never_dispatches(tmp_path, monkeypatch) -> None:
    manifest = _successor_manifest(run_id="run_v9_shared_recovery", version=9)
    runner = AgentRunner(tmp_path / "runtime")
    adapter = _RepeatedUnavailableAdapter()
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)

    assert result["agent_submission_status"] == "failed"
    assert result["terminal_error"]["code"] == "MODEL_ACTION_CONTRACT_REPEATED"
    recoveries = [
        event
        for event in events
        if event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("policy_version") == PROTOCOL_RECOVERY_POLICY
    ]
    assert len(recoveries) == 1
    assert recoveries[0].payload["execution"] == "not_dispatched"
    assert not any(event.type == EventType.TOOL_CALLED for event in events)


def test_v9_shared_protocol_recovery_survives_restart(tmp_path, monkeypatch) -> None:
    manifest = _successor_manifest(run_id="run_v9_recovery_restart", version=9)
    runner = AgentRunner(tmp_path / "runtime")
    first = _CrashAfterOneRecoveryAdapter()
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: first)

    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK_PATH, model="mock", manifest=manifest)
    checkpoint = runner.state.latest_checkpoint(manifest.run_id)
    assert checkpoint is not None
    assert checkpoint.phase == Phase.REPRODUCE

    second = _RepeatedUnavailableAdapter()
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: second)
    result = runner.resume(manifest.run_id)
    events = runner.state.list_events(manifest.run_id)

    assert result["terminal_error"]["code"] == "MODEL_ACTION_CONTRACT_REPEATED"
    assert (
        sum(
            event.type == EventType.TOOL_ADMISSION_BLOCKED
            and event.payload.get("policy_version") == PROTOCOL_RECOVERY_POLICY
            for event in events
        )
        == 1
    )
    assert not any(event.type == EventType.TOOL_CALLED for event in events)


def test_v10_plan_phase_and_hash_survive_restart_then_complete(tmp_path, monkeypatch) -> None:
    manifest = _successor_manifest(run_id="run_v10_plan_restart", version=10)
    runner = AgentRunner(tmp_path / "runtime")
    first = _V10PublicPlanAdapter(runner, manifest.run_id, crash_after_plan=True)
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: first)

    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK_PATH, model="mock", manifest=manifest)
    checkpoint = runner.state.latest_checkpoint(manifest.run_id)
    assert checkpoint is not None
    assert checkpoint.phase == Phase.PLAN
    assert checkpoint.reproduction_status == "static_evidence"
    assert len(checkpoint.current_plan) == 1
    recorded_plan_hash = checkpoint.current_plan[0]

    second = _V10PublicPlanAdapter(runner, manifest.run_id)
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: second)
    result = runner.resume(manifest.run_id)
    events = runner.state.list_events(manifest.run_id)

    assert result["scope_compliant_success"] is True
    plan_events = [event for event in events if event.type == EventType.PLAN_RECORDED]
    patch_events = [event for event in events if event.type == EventType.PATCH_APPLIED]
    assert len(plan_events) == 1
    assert plan_events[0].payload["plan_hash"] == recorded_plan_hash
    assert patch_events[0].payload["plan_hash"] == recorded_plan_hash
    assert sum(event.type == EventType.TOOL_CALLED for event in events) == 6
    assert not any(
        event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("policy_version") == PROTOCOL_RECOVERY_POLICY
        for event in events
    )


def test_v10_second_review_correction_is_terminal_without_submission(tmp_path, monkeypatch) -> None:
    manifest = _successor_manifest(run_id="run_v10_review_limit", version=10)
    runner = AgentRunner(tmp_path / "runtime")
    adapter = _V10DoubleReviewCorrectionAdapter(runner, manifest.run_id)
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)

    assert result["terminal_error"]["code"] == "REVIEW_CORRECTION_LIMIT"
    assert sum(event.type == EventType.PATCH_APPLIED for event in events) == 2
    assert not any(event.type == EventType.SUBMISSION_ACCEPTED for event in events)
    correction_calls = [
        event
        for event in events
        if event.type == EventType.TOOL_CALLED
        and event.payload.get("tool") == "apply_structured_edit"
    ]
    assert len(correction_calls) == 2
