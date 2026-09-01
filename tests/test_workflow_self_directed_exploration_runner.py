from __future__ import annotations

import json
from pathlib import Path

import pytest

from patchloop.agent.lean_runtime import (
    LEAN_RUNTIME_POLICY_VERSION_V23,
    LeanHarnessRequestEvidenceV23,
    build_lean_harness_calibration_manifest,
    validate_persisted_lean_harness_request,
)
from patchloop.agent.model import ModelTurn, RequestedTool
from patchloop.agent.runner import AgentRunner
from patchloop.agent.workflow_successor import PROTOCOL_RECOVERY_POLICY
from patchloop.contracts import EventType, MemoryCondition
from patchloop.task_loader import load_task_package
from tests.test_workflow_successor_v2_runner import (
    TARGET_PATH,
    TASK_PATH,
    _FailFirstTwoVisibleChecksSandbox,
    _FailFirstVisibleCheckSandbox,
    _PinnedPlanGateWorkflowAdapter,
)


def _manifest(run_id: str):
    package = load_task_package("tasks/smoke/config-falsy-override")
    return build_lean_harness_calibration_manifest(
        package,
        run_id=run_id,
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V23,
    )


def _request_evidence(runner: AgentRunner, run_id: str) -> list[LeanHarnessRequestEvidenceV23]:
    requests: list[LeanHarnessRequestEvidenceV23] = []
    for event in runner.state.list_events(run_id):
        if event.type != EventType.MODEL_CALLED:
            continue
        payload = json.loads(
            Path(event.payload["request_artifact_path"]).read_text(encoding="utf-8")
        )
        raw = payload.get("lean_harness_request")
        if isinstance(raw, dict) and raw.get("schema_version") == (
            "lean-harness-request-evidence-v23"
        ):
            evidence = validate_persisted_lean_harness_request(payload)
            assert isinstance(evidence, LeanHarnessRequestEvidenceV23)
            requests.append(evidence)
    return requests


class _SelfDirectedWorkflowAdapter(_PinnedPlanGateWorkflowAdapter):
    def __init__(
        self,
        *,
        prefix: str,
        invalid_intent: bool = False,
        exhaust: bool = False,
        fail_first_mutation: bool = False,
        review_correction: bool = False,
        reject_review_edit_once: bool = False,
    ) -> None:
        super().__init__(prefix=prefix, fail_first_mutation=fail_first_mutation)
        self.invalid_intent = invalid_intent
        self.exhaust = exhaust
        self.review_correction = review_correction
        self.reject_review_edit_once = reject_review_edit_once
        self.review_plan_recorded = False
        self.review_correction_done = False
        self.review_edit_rejected = False
        self.gate_targets: dict[str, int] = {}

    def _intent(self, workflow: dict, *, target_role: str = "execution_path") -> dict:
        spans = workflow["self_directed_exploration_state"]["source_spans"]
        basis = [spans[0]["source_span_id"]]
        if self.invalid_intent:
            basis = ["cspan:999999:0"]
        return {
            "status": "need_more_evidence",
            "blocking_question": "Which public source boundary completes the merge?",
            "basis_source_span_ids": basis,
            "target_role": target_role,
            "expected_information_gain": (
                "The next public result can distinguish ownership from mutation."
            ),
        }

    @staticmethod
    def _readiness(arguments: dict) -> dict:
        coverage = arguments["exploration_state"]["boundary_coverage"]
        basis = list(
            dict.fromkeys(
                coverage["ownership_boundary_span_ids"] + coverage["mutation_boundary_span_ids"]
            )
        )
        return {
            "readiness_status": "ready_to_plan",
            "sufficiency_mode": "multi_range",
            "basis_source_span_ids": basis,
            "sufficiency_rationale": (
                "The current public source ranges bind ownership and the mutation site."
            ),
            "remaining_unknowns_non_blocking": True,
        }

    def next_turn(self, context: str, tools: list[dict]) -> ModelTurn:
        workflow = json.loads(context)["workflow"]
        names = tuple(item["name"] for item in tools)
        state = workflow.get("self_directed_exploration_state")
        if (
            state is not None
            and state["trigger"] == "review_correction"
            and "finish_task" in names
            and not self.exhaust
            and not self.review_correction
        ):
            return super().next_turn(context, tools)
        if state is not None and self.exhaust and "declare_exploration_exhausted" in names:
            self.calls += 1
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        "declare_exploration_exhausted",
                        self._action_id("explicit-stop"),
                        {
                            "status": "not_ready",
                            "blocking_question": (
                                "Which public source boundary owns the final state?"
                            ),
                            "basis_source_span_ids": [state["source_spans"][0]["source_span_id"]],
                            "reason": "evidence_budget_exhausted",
                        },
                    )
                ]
            )
        if state is not None and set(names).intersection({"read_file", "search_files"}):
            gate_id = state["plan_gate_id"]
            target_index = self.gate_targets.get(gate_id, 0)
            if not state["source_spans"]:
                self.calls += 1
                self.gate_targets[gate_id] = target_index + 1
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "read_file",
                            self._action_id("initial-read"),
                            {"path": TARGET_PATH, "start_line": 1, "end_line": 8},
                        )
                    ]
                )
            if self.invalid_intent:
                self.calls += 1
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "read_file",
                            self._action_id("invalid-intent"),
                            {
                                "path": TARGET_PATH,
                                "start_line": 9,
                                "end_line": 20,
                                "investigation_intent": self._intent(workflow),
                            },
                        )
                    ]
                )
            if self.exhaust and state["information_actions_used"] < 10:
                self.calls += 1
                self.gate_targets[gate_id] = target_index + 1
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "search_files",
                            self._action_id("bounded-search"),
                            {
                                "query": f"result[{target_index}]",
                                "path_glob": TARGET_PATH,
                                "investigation_intent": self._intent(
                                    workflow, target_role="falsification"
                                ),
                            },
                        )
                    ]
                )
            if len(state["distinct_source_coverage_keys"]) < 2:
                self.calls += 1
                self.gate_targets[gate_id] = target_index + 1
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "read_file",
                            self._action_id("second-read"),
                            {
                                "path": TARGET_PATH,
                                "start_line": 9,
                                "end_line": 20,
                                "investigation_intent": self._intent(workflow),
                            },
                        )
                    ]
                )
        if "record_work_plan" in names or "revise_work_plan" in names:
            self.calls += 1
            revision = "revise_work_plan" in names
            tool_name = "revise_work_plan" if revision else "record_work_plan"
            arguments = super()._exploration_arguments(workflow)
            arguments["readiness_assessment"] = self._readiness(arguments)
            if revision:
                arguments["prior_hypothesis_disposition"] = (
                    workflow.get("required_prior_hypothesis_disposition") or "refined"
                )
                if state is not None and state["trigger"] == "review_correction":
                    self.review_plan_recorded = True
            self.plan_arguments.append(arguments)
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        tool_name,
                        self._action_id("self-directed-plan"),
                        arguments,
                    )
                ]
            )
        if (
            self.review_correction
            and self.review_plan_recorded
            and not self.review_correction_done
            and "apply_structured_edit" in names
        ):
            self.calls += 1
            rejecting = self.reject_review_edit_once and not self.review_edit_rejected
            if rejecting:
                self.review_edit_rejected = True
            else:
                self.review_correction_done = True
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        "apply_structured_edit",
                        self._action_id("review-edit"),
                        {
                            "schema_version": "structured-edit-arguments-v2",
                            "files": [
                                {
                                    "path": TARGET_PATH,
                                    "replacements": [
                                        {
                                            "expected_text": (
                                                "result[key] = missing_value"
                                                if rejecting
                                                else "result[key] = value"
                                            ),
                                            "replacement_text": ("result[key] = value  # reviewed"),
                                        }
                                    ],
                                }
                            ],
                        },
                    )
                ]
            )
        return super().next_turn(context, tools)


class _CrashAfterCoverageAdapter(_SelfDirectedWorkflowAdapter):
    def __init__(self, *, prefix: str) -> None:
        super().__init__(prefix=prefix)
        self.captured_state: dict | None = None
        self.captured_tool_names: tuple[str, ...] | None = None

    def next_turn(self, context: str, tools: list[dict]) -> ModelTurn:
        workflow = json.loads(context)["workflow"]
        state = workflow.get("self_directed_exploration_state")
        if (
            state is not None
            and len(state["distinct_source_coverage_keys"]) >= 2
            and not getattr(self, "crashed", False)
        ):
            self.crashed = True
            self.captured_state = state
            self.captured_tool_names = tuple(item["name"] for item in tools)
            raise SystemExit(86)
        return super().next_turn(context, tools)


class _CaptureFirstRequestAdapter(_SelfDirectedWorkflowAdapter):
    def __init__(self, *, prefix: str) -> None:
        super().__init__(prefix=prefix)
        self.first_state: dict | None = None
        self.first_tool_names: tuple[str, ...] | None = None

    def next_turn(self, context: str, tools: list[dict]) -> ModelTurn:
        if self.first_state is None:
            self.first_state = json.loads(context)["workflow"].get(
                "self_directed_exploration_state"
            )
            self.first_tool_names = tuple(item["name"] for item in tools)
        return super().next_turn(context, tools)


def test_v23_runner_allows_optional_second_read_then_completes(tmp_path, monkeypatch) -> None:
    manifest = _manifest("run_v23_self_directed_success")
    runner = AgentRunner(tmp_path / "v23-success")
    adapter = _SelfDirectedWorkflowAdapter(prefix="v23-success")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    requests = _request_evidence(runner, manifest.run_id)
    inspections = [
        event
        for event in events
        if event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") in {"read_file", "search_files"}
    ]

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert len(inspections) == 2
    assert inspections[0].payload.get("investigation_intent") is None
    assert inspections[1].payload["investigation_intent"]["status"] == "need_more_evidence"
    assert inspections[1].payload["investigation_target_hash"].startswith("sha256:")
    assert any(
        {"search_files", "read_file", "record_work_plan"}.issubset(
            item.workflow_decision.allowed_tool_names
        )
        for item in requests
    )
    plan = next(event for event in events if event.type == EventType.PLAN_RECORDED)
    patch = next(event for event in events if event.type == EventType.PATCH_APPLIED)
    assert patch.payload["plan_hash"] == plan.payload["plan_hash"]
    assert plan.payload["self_directed_closure_receipt_hash"].startswith("sha256:")


def test_v23_invalid_intent_uses_shared_slot_then_stops_without_dispatch(
    tmp_path, monkeypatch
) -> None:
    manifest = _manifest("run_v23_invalid_intent")
    runner = AgentRunner(tmp_path / "v23-invalid-intent")
    adapter = _SelfDirectedWorkflowAdapter(prefix="v23-invalid", invalid_intent=True)
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    blocked = [
        event
        for event in events
        if event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("policy_version") == PROTOCOL_RECOVERY_POLICY
    ]

    assert result["terminal_error"]["code"] == "MODEL_ACTION_CONTRACT_REPEATED"
    assert len(blocked) == 1
    assert blocked[0].payload["reason_code"] == ("self_directed_investigation_basis_ineligible")
    assert (
        sum(
            event.type == EventType.TOOL_CALLED and event.payload.get("tool") == "read_file"
            for event in events
        )
        == 1
    )
    assert not any(event.type == EventType.PATCH_APPLIED for event in events)


def test_v23_failed_check_requires_fresh_exploration_revision_and_recheck(
    tmp_path, monkeypatch
) -> None:
    manifest = _manifest("run_v23_correction")
    runner = AgentRunner(tmp_path / "v23-correction")
    adapter = _SelfDirectedWorkflowAdapter(
        prefix="v23-correction",
        fail_first_mutation=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    monkeypatch.setattr(
        "patchloop.agent.runner.LocalSandbox",
        lambda: _FailFirstVisibleCheckSandbox(),
    )

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    plans = [event for event in events if event.type == EventType.PLAN_RECORDED]
    patches = [event for event in events if event.type == EventType.PATCH_APPLIED]
    checks = [
        event
        for event in events
        if event.type == EventType.TOOL_SUCCEEDED and event.payload.get("tool") == "run_check"
    ]

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert [event.payload["trigger"] for event in plans] == ["initial", "check_failure"]
    assert plans[1].payload["parent_plan_hash"] == plans[0].payload["plan_hash"]
    assert [event.payload["plan_hash"] for event in patches] == [
        plans[0].payload["plan_hash"],
        plans[1].payload["plan_hash"],
    ]
    assert [event.payload["passed"] for event in checks] == [False, True]
    failed_sequence = checks[0].sequence
    correction_reads = [
        event
        for event in events
        if event.sequence > failed_sequence
        and event.sequence < plans[1].sequence
        and event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "read_file"
    ]
    assert len(correction_reads) == 2


def test_v23_repeated_public_failure_requires_a_different_causal_boundary(
    tmp_path, monkeypatch
) -> None:
    manifest = _manifest("run_v23_repeated_failure")
    runner = AgentRunner(tmp_path / "v23-repeated-failure")
    adapter = _SelfDirectedWorkflowAdapter(
        prefix="v23-repeated-failure",
        fail_first_mutation=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    monkeypatch.setattr(
        "patchloop.agent.runner.LocalSandbox",
        lambda: _FailFirstTwoVisibleChecksSandbox(),
    )

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    plans = [event for event in events if event.type == EventType.PLAN_RECORDED]
    closures = [event for event in events if event.type == EventType.EXPLORATION_CLOSURE_RECORDED]
    restored = [event for event in events if event.type == EventType.MUTATION_BASELINE_RESTORED]

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert [event.payload["revision_index"] for event in plans] == [0, 1, 2]
    assert len(closures) == len(plans) == 3
    assert len(restored) == 1
    first_coverage = closures[0].payload["binding"]["receipt"]["selected_source_coverage_keys"]
    alternative_coverage = closures[-1].payload["binding"]["receipt"][
        "selected_source_coverage_keys"
    ]
    assert alternative_coverage != first_coverage
    assert adapter.plan_arguments[-1]["prior_hypothesis_disposition"] == "rejected"


def test_v23_explicit_exhaustion_records_one_terminal_without_patch(tmp_path, monkeypatch) -> None:
    manifest = _manifest("run_v23_explicit_exhaustion")
    runner = AgentRunner(tmp_path / "v23-exhaustion")
    adapter = _SelfDirectedWorkflowAdapter(prefix="v23-exhaust", exhaust=True)
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    stops = [event for event in events if event.type == EventType.EXPLORATION_STOP_RECORDED]

    assert result["terminal_error"]["code"] == "SELF_DIRECTED_EXPLORATION_EXHAUSTED"
    assert len(stops) == 1
    assert stops[0].payload["information_actions_used"] == 10
    assert stops[0].payload["execution"] == "not_dispatched"
    assert not any(event.type == EventType.PATCH_APPLIED for event in events)
    assert not any(event.type == EventType.SUBMISSION_ACCEPTED for event in events)


def test_v23_review_revision_survives_context_window_and_forces_full_recheck(
    tmp_path, monkeypatch
) -> None:
    manifest = _manifest("run_v23_review_correction")
    runner = AgentRunner(tmp_path / "v23-review")
    adapter = _SelfDirectedWorkflowAdapter(
        prefix="v23-review",
        review_correction=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    plans = [event for event in events if event.type == EventType.PLAN_RECORDED]
    patches = [event for event in events if event.type == EventType.PATCH_APPLIED]
    checks = [
        event
        for event in events
        if event.type == EventType.TOOL_SUCCEEDED and event.payload.get("tool") == "run_check"
    ]
    diffs = [
        event
        for event in events
        if event.type == EventType.TOOL_SUCCEEDED and event.payload.get("tool") == "get_diff"
    ]

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert [event.payload["trigger"] for event in plans] == [
        "initial",
        "review_correction",
    ]
    assert len(patches) == len(checks) == len(diffs) == 2
    assert patches[1].payload["plan_hash"] == plans[1].payload["plan_hash"]
    submission = next(event for event in events if event.type == EventType.SUBMISSION_ACCEPTED)
    assert submission.sequence > diffs[-1].sequence


def test_v23_restart_recovers_identical_exploration_state_and_surface(
    tmp_path, monkeypatch
) -> None:
    manifest = _manifest("run_v23_restart")
    runner = AgentRunner(tmp_path / "v23-restart")
    first = _CrashAfterCoverageAdapter(prefix="v23-restart-first")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: first)

    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK_PATH, model="mock", manifest=manifest)
    assert first.captured_state is not None

    second = _CaptureFirstRequestAdapter(prefix="v23-restart-second")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: second)
    result = runner.resume(manifest.run_id)

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert second.first_state == first.captured_state
    assert second.first_tool_names == first.captured_tool_names


def test_v23_review_edit_rejection_requires_reread_without_new_revision(
    tmp_path, monkeypatch
) -> None:
    manifest = _manifest("run_v23_review_rejection")
    runner = AgentRunner(tmp_path / "v23-review-rejection")
    adapter = _SelfDirectedWorkflowAdapter(
        prefix="v23-review-rejection",
        review_correction=True,
        reject_review_edit_once=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    plans = [event for event in events if event.type == EventType.PLAN_RECORDED]
    rejected = next(
        event
        for event in events
        if event.type == EventType.TOOL_FAILED
        and event.payload.get("tool") == "apply_structured_edit"
    )
    rereads = [
        event
        for event in events
        if event.sequence > rejected.sequence
        and event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "read_file"
    ]

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert [event.payload["trigger"] for event in plans] == [
        "initial",
        "review_correction",
    ]
    assert rereads
    review_plan_hash = plans[-1].payload["plan_hash"]
    assert [
        event.payload["plan_hash"] for event in events if event.type == EventType.PATCH_APPLIED
    ][-1] == review_plan_hash
