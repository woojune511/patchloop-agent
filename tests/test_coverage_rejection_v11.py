from __future__ import annotations

import copy
import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from patchloop.agent.context import (
    _coverage_rejection_feedback_v11,
    build_context_with_evidence,
)
from patchloop.agent.model import (
    SYSTEM_PROMPT_V7,
    SYSTEM_PROMPT_V8,
    MockModelAdapter,
    ModelTurn,
    RequestedTool,
)
from patchloop.agent.review import (
    public_review_contract_content_hash,
    public_review_coverage_target_id,
)
from patchloop.agent.runner import AgentRunner
from patchloop.agent.tools import TOOL_SCHEMAS_V5, TOOL_SCHEMAS_V6
from patchloop.contracts import (
    Artifact,
    EventType,
    ExperimentPurpose,
    ExperimentRunContext,
    PublicReviewContract,
    RunEvent,
    RunManifest,
)
from patchloop.errors import ContractError, RecoveryError
from patchloop.evals.qualification import (
    _private_leak_tokens,
    _v11_coverage_rejection_recovery_evidence,
    _v11_latest_worker_claim,
    qualify_run,
)
from patchloop.runtime import build_manifest
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_text, utc_now
from tests.test_coverage_review_v10 import (
    TASK,
    _review_arguments,
    _smoke_v2_contract,
)


def _wrong_target_review(context, contract) -> dict:
    """Cite a globally uncitable sequence for the inspection-only target."""

    arguments = _review_arguments(context, contract, complete=False)
    review_evidence = json.loads(context)["review_evidence"]
    wrong_sequence = review_evidence["source_get_diff_sequence"] + 10_000
    inspection_target = contract.requirements[0].coverage_targets[0]
    inspection_row = next(
        row
        for row in arguments["coverage_targets"]
        if row["coverage_target_id"]
        == inspection_target.coverage_target_id
    )
    inspection_row["status"] = "verified"
    inspection_row["evidence_event_sequences"] = [wrong_sequence]
    requirement_row = arguments["requirements"][0]
    requirement_row["status"] = "verified"
    requirement_row["evidence_event_sequences"] = [
        wrong_sequence,
        *requirement_row["evidence_event_sequences"],
    ]
    return arguments


def _missing_validation_evidence_review(context, contract) -> dict:
    arguments = _review_arguments(context, contract, complete=False)
    validation_target = contract.requirements[0].coverage_targets[1]
    validation_row = next(
        row
        for row in arguments["coverage_targets"]
        if row["coverage_target_id"]
        == validation_target.coverage_target_id
    )
    validation_row["status"] = "verified"
    validation_row["evidence_event_sequences"] = []
    return arguments


def _multi_check_v2_contract(package) -> PublicReviewContract:
    payload = _smoke_v2_contract(package).model_dump(mode="json")
    requirement = payload["requirements"][0]
    target = requirement["coverage_targets"][1]
    target["check_ids"] = ["existing-unit-tests", "second-unit-tests"]
    target["coverage_target_id"] = public_review_coverage_target_id(
        requirement["requirement_id"],
        description=target["description"],
        evidence_kind=target["evidence_kind"],
        check_ids=target["check_ids"],
    )
    payload["content_hash"] = public_review_contract_content_hash(payload)
    return PublicReviewContract.model_validate(payload)


def test_v11_equal_timestamp_claim_uses_durable_row_order() -> None:
    claimed_at = utc_now()
    base = {
        "run_id": "run_v11_equal_claim_time",
        "owner_pid": 1,
        "owner_hostname": "test-host",
        "claimed_at": claimed_at.isoformat(),
        "prior_status": "RUNNING",
        "reclaimed": True,
    }
    claims = [
        {
            **base,
            "claim_id": "claim_first",
            "owner_id": "worker_first",
        },
        {
            **base,
            "claim_id": "claim_second",
            "owner_id": "worker_second",
        },
    ]
    with pytest.raises(RecoveryError, match="active durable claim"):
        _v11_latest_worker_claim(
            worker_claims=claims,
            claim_evidence={
                "schema_version": "worker-claim-evidence-v1",
                **claims[0],
            },
            context_timestamp=claimed_at,
            label="equal-time test",
        )
    selected, selected_at = _v11_latest_worker_claim(
        worker_claims=claims,
        claim_evidence={
            "schema_version": "worker-claim-evidence-v1",
            **claims[1],
        },
        context_timestamp=claimed_at,
        label="equal-time test",
    )
    assert selected == claims[1]
    assert selected_at == claimed_at


def test_v11_selector_is_offline_only_and_does_not_mutate_v10() -> None:
    package = load_task_package(TASK.parent)
    contract = _smoke_v2_contract(package)
    manifest = build_manifest(
        package,
        run_id="run_v11_selector",
        coverage_rejection_validation=True,
        public_review_contract=contract,
    )

    assert manifest.tool_schema_version == "v6"
    assert manifest.context_policy_version == "phase-evidence-v11"
    assert AgentRunner._runtime_contract(manifest) == (
        SYSTEM_PROMPT_V8,
        TOOL_SCHEMAS_V6,
    )
    assert "may be stale after recovery" in SYSTEM_PROMPT_V8
    assert "review_evidence.coverage_target_event_sequences" in (
        SYSTEM_PROMPT_V8
    )
    assert SYSTEM_PROMPT_V7 not in {SYSTEM_PROMPT_V8}
    assert TOOL_SCHEMAS_V5 != TOOL_SCHEMAS_V6

    with pytest.raises(ContractError, match="offline-only"):
        build_manifest(
            package,
            provider="openai",
            model_id="gpt-test",
            coverage_rejection_validation=True,
            public_review_contract=contract,
        )
    experiment = ExperimentRunContext(
        experiment_id="v11-forbidden-experiment",
        purpose=ExperimentPurpose.OFFLINE_SMOKE,
        suite_hash="sha256:" + ("a" * 64),
        execution_hash="sha256:" + ("b" * 64),
        schedule_seed=20260723,
        schedule_order=1,
        schedule_row_id="sha256:" + ("c" * 64),
        repetition=1,
    )
    with pytest.raises(ContractError, match="cannot declare an experiment"):
        build_manifest(
            package,
            experiment_context=experiment,
            coverage_rejection_validation=True,
            public_review_contract=contract,
        )
    with pytest.raises(ContractError, match="mutually exclusive"):
        build_manifest(
            package,
            coverage_review_validation=True,
            coverage_rejection_validation=True,
            public_review_contract=contract,
        )

    payload = manifest.model_dump(mode="json")
    payload["tool_schema_version"] = "v5"
    with pytest.raises(ValueError, match="exact .* pair"):
        RunManifest.model_validate(payload)


@pytest.mark.parametrize(
    ("validation_mode", "expected_error_code"),
    [
        ("v11", "COVERAGE_CITATION_REJECTED"),
        ("v10", "CONTRACT_ERROR"),
    ],
)
def test_validation_target_mismatch_feedback_is_v11_only(
    tmp_path,
    monkeypatch,
    validation_mode: str,
    expected_error_code: str,
) -> None:
    package = load_task_package(TASK.parent)
    contract = _smoke_v2_contract(package)
    manifest = build_manifest(
        package,
        run_id=f"run_{validation_mode}_validation_target_mismatch",
        sandbox_backend="local",
        coverage_rejection_validation=(validation_mode == "v11"),
        coverage_review_validation=(validation_mode == "v10"),
        public_review_contract=contract,
    )
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )

    class ValidationMismatchAdapter(MockModelAdapter):
        def __init__(self) -> None:
            super().__init__(package.public.task_id)

        def next_turn(self, context, tools):
            counts = {
                name: self.completed_tools.count(name)
                for name in set(self.completed_tools)
            }
            if counts.get("get_diff", 0) == 0:
                return super().next_turn(context, tools)
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        "review_task",
                        f"{validation_mode}-validation-target-mismatch",
                        _missing_validation_evidence_review(
                            context,
                            contract,
                        ),
                    )
                ]
            )

    runner = AgentRunner(tmp_path / validation_mode)
    adapter = ValidationMismatchAdapter()
    monkeypatch.setattr(
        runner,
        "_model_adapter",
        lambda *_args, **_kwargs: adapter,
    )
    original_phase_after_tool = runner._phase_after_tool

    def stop_after_rejection(
        run_id,
        phase,
        tool,
        result,
        task,
        workspace,
    ):
        if tool == "review_task" and result.status == "rejected":
            raise SystemExit(87)
        return original_phase_after_tool(
            run_id,
            phase,
            tool,
            result,
            task,
            workspace,
        )

    monkeypatch.setattr(
        runner,
        "_phase_after_tool",
        stop_after_rejection,
    )
    with pytest.raises(SystemExit, match="87"):
        runner.start(TASK, model="mock", manifest=manifest)

    events = runner.state.list_events(manifest.run_id)
    failure = next(
        event
        for event in events
        if event.type == EventType.TOOL_FAILED
        and event.payload.get("tool") == "review_task"
    )
    assert failure.payload["error_code"] == expected_error_code
    result_artifact = Artifact.model_validate(
        failure.payload["result_artifact"]
    )
    result_document = json.loads(
        runner.artifacts.read_bytes(result_artifact).decode("utf-8")
    )
    assert result_document["error_code"] == expected_error_code

    if validation_mode == "v10":
        assert failure.payload["error_details"] == {}
        assert result_document["error_details"] == {}
        assert failure.payload["error_message"] == (
            "verified coverage target requires all advertised evidence"
        )
        return

    validation_target = contract.requirements[0].coverage_targets[1]
    details = failure.payload["error_details"]
    assert details["schema_version"] == "coverage-citation-error-v1"
    assert details["reason"] == "verified_target_evidence_mismatch"
    assert details["coverage_target_id"] == (
        validation_target.coverage_target_id
    )
    assert details["requirement_id"] == (
        contract.requirements[0].requirement_id
    )
    assert details["evidence_kind"] == "passing_validation"
    assert details["required_evidence"] == {
        "tool": "run_check",
        "check_ids": list(validation_target.check_ids),
    }
    assert details["submitted_event_sequences"] == []
    assert details["invalid_event_sequences"] == []
    assert len(details["allowed_event_sequences"]) == 1
    allowed_sequence = details["allowed_event_sequences"][0]
    allowed_event = next(
        event for event in events if event.sequence == allowed_sequence
    )
    assert allowed_event.type == EventType.TOOL_SUCCEEDED
    assert allowed_event.payload["tool"] == "run_check"
    assert allowed_event.payload["check_id"] in validation_target.check_ids
    assert allowed_event.payload["passed"] is True
    assert result_document["error_details"] == details

    class StaleThenRecoverAdapter(MockModelAdapter):
        def __init__(self) -> None:
            super().__init__(package.public.task_id)
            self.stage = 0
            self.latest_feedback: dict | None = None

        def next_turn(self, context, tools):
            del tools
            context_payload = json.loads(context)
            if self.stage == 0:
                arguments = _review_arguments(
                    context,
                    contract,
                    complete=False,
                )
                stale_sequences = context_payload["review_evidence"][
                    "coverage_target_event_sequences"
                ][validation_target.coverage_target_id]
                assert stale_sequences
                validation_row = next(
                    row
                    for row in arguments["coverage_targets"]
                    if row["coverage_target_id"]
                    == validation_target.coverage_target_id
                )
                validation_row["status"] = "verified"
                validation_row["evidence_event_sequences"] = list(
                    stale_sequences
                )
                requirement_sequences = []
                statuses = []
                for row in arguments["coverage_targets"]:
                    statuses.append(row["status"])
                    for sequence in row["evidence_event_sequences"]:
                        if sequence not in requirement_sequences:
                            requirement_sequences.append(sequence)
                requirement_row = arguments["requirements"][0]
                requirement_row["status"] = (
                    "verified"
                    if all(status == "verified" for status in statuses)
                    else "partially_verified"
                )
                requirement_row["evidence_event_sequences"] = (
                    requirement_sequences
                )
                arguments["residual_risks"] = (
                    []
                    if requirement_row["status"] == "verified"
                    else arguments["residual_risks"]
                )
                self.stage = 1
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "review_task",
                            "v11-stale-validation-retry",
                            arguments,
                        )
                    ]
                )
            if self.stage == 5:
                assert context_payload["coverage_rejection_feedback"] is None
                self.stage = 6
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "finish_task",
                            "v11-validation-recovered-finish",
                            {},
                        )
                    ]
                )
            feedback = context_payload["coverage_rejection_feedback"]
            if self.latest_feedback is None:
                self.latest_feedback = feedback
            assert feedback == self.latest_feedback
            if self.stage == 1:
                self.stage = 2
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "run_check",
                            "v11-fresh-validation-recovery",
                            {"check_id": validation_target.check_ids[0]},
                        )
                    ]
                )
            if self.stage == 2:
                self.stage = 3
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "read_file",
                            "v11-validation-recovery-anchor",
                            {
                                "path": "mini_data_utils/csvlite.py",
                                "start_line": 1,
                                "end_line": 50,
                            },
                        )
                    ]
                )
            if self.stage == 3:
                self.stage = 4
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "get_diff",
                            "v11-validation-recovery-diff",
                            {},
                        )
                    ]
                )
            if self.stage == 4:
                self.stage = 5
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "review_task",
                            "v11-validation-recovered-review",
                            _review_arguments(
                                context,
                                contract,
                                complete=True,
                            ),
                        )
                    ]
                )
            raise AssertionError(f"unexpected recovery stage: {self.stage}")

    resumed_runner = AgentRunner(runner.root)
    stale_adapter = StaleThenRecoverAdapter()
    monkeypatch.setattr(
        resumed_runner,
        "_model_adapter",
        lambda *_args, **_kwargs: stale_adapter,
    )
    result = resumed_runner.resume(manifest.run_id)

    resumed_events = resumed_runner.state.list_events(manifest.run_id)
    assert result["scope_compliant_success"] is True
    assert stale_adapter.stage == 6
    stale_failure = next(
        event
        for event in reversed(resumed_events)
        if event.type == EventType.TOOL_FAILED
        and event.payload.get("tool") == "review_task"
    )
    assert stale_failure.correlation_id == "v11-stale-validation-retry"
    assert stale_failure.payload["error_code"] == (
        "COVERAGE_CITATION_REJECTED"
    )
    stale_details = stale_failure.payload["error_details"]
    assert stale_details["submitted_event_sequences"] == (
        stale_details["allowed_event_sequences"]
    ), stale_details
    assert stale_details["reason"] == (
        "fresh_target_evidence_required"
    ), stale_details
    assert not any(
        failure.sequence < event.sequence < stale_failure.sequence
        and event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "run_check"
        for event in resumed_events
    )
    fresh_check = next(
        event
        for event in resumed_events
        if event.type == EventType.TOOL_SUCCEEDED
        and event.correlation_id == "v11-fresh-validation-recovery"
    )
    assert fresh_check.sequence > stale_failure.sequence
    passed, recovery_details = _v11_coverage_rejection_recovery_evidence(
        root=resumed_runner.root,
        manifest=manifest,
        package=package,
        events=resumed_events,
        context_events=[
            event
            for event in resumed_events
            if event.type == EventType.CONTEXT_BUILT
        ],
        worker_claims=resumed_runner.state.list_worker_claims(
            manifest.run_id
        ),
    )
    assert passed is True, recovery_details
    assert recovery_details["verified_rejection_sequences"] == [
        failure.sequence,
        stale_failure.sequence,
    ]
    assert recovery_details["restart_rejection_sequences"] == [
        failure.sequence
    ]
    assert fresh_check.sequence in recovery_details[
        "recovery_evidence_sequences"
    ]


def test_v11_multi_check_recovery_binds_every_fresh_citation(
    tmp_path,
    monkeypatch,
) -> None:
    task_dir = tmp_path / "multi-check-task"
    shutil.copytree(TASK.parent, task_dir)
    public_path = task_dir / "public.yaml"
    public_document = yaml.safe_load(public_path.read_text(encoding="utf-8"))
    second_check = copy.deepcopy(public_document["visible_checks"][0])
    second_check["id"] = "second-unit-tests"
    public_document["visible_checks"].append(second_check)
    public_path.write_text(
        yaml.safe_dump(public_document, sort_keys=False),
        encoding="utf-8",
    )
    package = load_task_package(task_dir)
    contract = _multi_check_v2_contract(package)
    validation_target = contract.requirements[0].coverage_targets[1]
    manifest = build_manifest(
        package,
        run_id="run_v11_multi_check_recovery",
        sandbox_backend="local",
        coverage_rejection_validation=True,
        public_review_contract=contract,
    )
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )

    class MultiCheckRejectingAdapter(MockModelAdapter):
        def __init__(self) -> None:
            super().__init__(package.public.task_id)

        def next_turn(self, context, tools):
            counts = {
                name: self.completed_tools.count(name)
                for name in set(self.completed_tools)
            }
            if counts.get("read_file", 0) == 0:
                return super().next_turn(context, tools)
            if counts.get("apply_patch", 0) == 0:
                return super().next_turn(context, tools)
            if counts.get("run_check", 0) == 0:
                return super().next_turn(context, tools)
            if counts.get("run_check", 0) == 1:
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "run_check",
                            "v11-initial-second-check",
                            {"check_id": "second-unit-tests"},
                        )
                    ]
                )
            if counts.get("get_diff", 0) == 0:
                return super().next_turn(context, tools)
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        "review_task",
                        "v11-multi-check-source-rejection",
                        _missing_validation_evidence_review(
                            context,
                            contract,
                        ),
                    )
                ]
            )

    runner = AgentRunner(tmp_path / "multi-check-runtime")
    rejecting_adapter = MultiCheckRejectingAdapter()
    monkeypatch.setattr(
        runner,
        "_model_adapter",
        lambda *_args, **_kwargs: rejecting_adapter,
    )
    original_phase_after_tool = runner._phase_after_tool

    def crash_after_rejection(
        run_id,
        phase,
        tool,
        result,
        task,
        workspace,
    ):
        if tool == "review_task" and result.status == "rejected":
            raise SystemExit(93)
        return original_phase_after_tool(
            run_id,
            phase,
            tool,
            result,
            task,
            workspace,
        )

    monkeypatch.setattr(runner, "_phase_after_tool", crash_after_rejection)
    with pytest.raises(SystemExit, match="93"):
        runner.start(public_path, model="mock", manifest=manifest)
    source_events = runner.state.list_events(manifest.run_id)
    failure = next(
        event
        for event in source_events
        if event.type == EventType.TOOL_FAILED
        and event.payload.get("error_code") == "COVERAGE_CITATION_REJECTED"
    )
    assert len(failure.payload["error_details"]["allowed_event_sequences"]) == 2

    class MultiCheckRecoveryAdapter:
        def __init__(self) -> None:
            self.stage = 0
            self.feedback: dict | None = None
            self.fresh_sequences: list[int] = []

        def next_turn(self, context, tools):
            del tools
            payload = json.loads(context)
            if self.stage == 5:
                assert payload["coverage_rejection_feedback"] is None
                self.stage = 6
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "finish_task",
                            "v11-multi-check-finish",
                            {},
                        )
                    ]
                )
            active_feedback = payload["coverage_rejection_feedback"]
            if self.feedback is None:
                self.feedback = active_feedback
            assert active_feedback == self.feedback
            if self.stage == 0:
                self.stage = 2
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "run_check",
                            f"v11-fresh-{check_id}",
                            {"check_id": check_id},
                        )
                        for check_id in validation_target.check_ids
                    ]
                )
            if self.stage == 2:
                self.stage = 3
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "read_file",
                            "v11-multi-check-anchor",
                            {
                                "path": "mini_data_utils/csvlite.py",
                                "start_line": 1,
                                "end_line": 50,
                            },
                        )
                    ]
                )
            if self.stage == 3:
                self.stage = 4
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "get_diff",
                            "v11-multi-check-diff",
                            {},
                        )
                    ]
                )
            if self.stage == 4:
                self.fresh_sequences = payload["review_evidence"][
                    "coverage_target_event_sequences"
                ][validation_target.coverage_target_id]
                assert len(self.fresh_sequences) == 2
                assert all(
                    sequence > failure.sequence
                    for sequence in self.fresh_sequences
                )
                self.stage = 5
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "review_task",
                            "v11-multi-check-review",
                            _review_arguments(
                                context,
                                contract,
                                complete=True,
                            ),
                        )
                    ]
                )
            raise AssertionError(f"unexpected recovery stage: {self.stage}")

    resumed = AgentRunner(runner.root)
    recovery_adapter = MultiCheckRecoveryAdapter()
    monkeypatch.setattr(
        resumed,
        "_model_adapter",
        lambda *_args, **_kwargs: recovery_adapter,
    )
    monkeypatch.setattr(resumed, "_find_task", lambda _manifest: task_dir)
    result = resumed.resume(manifest.run_id)
    events = resumed.state.list_events(manifest.run_id)
    assert result["scope_compliant_success"] is True
    assert recovery_adapter.stage == 6

    passed, details = _v11_coverage_rejection_recovery_evidence(
        root=resumed.root,
        manifest=manifest,
        package=package,
        events=events,
        context_events=[
            event for event in events if event.type == EventType.CONTEXT_BUILT
        ],
        worker_claims=resumed.state.list_worker_claims(manifest.run_id),
    )
    assert passed is True, details
    assert details["restart_rejection_sequences"] == [failure.sequence]
    assert details["recovery_evidence_sequences"] == (
        recovery_adapter.fresh_sequences
    )
    qualification = qualify_run(
        manifest.run_id,
        task_dir=task_dir,
        root=resumed.root,
    )
    recovery_check = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "coverage_rejection_recovery_contract"
    )
    assert recovery_check["passed"] is True, recovery_check


def test_v11_partial_review_keeps_rejection_feedback(
    tmp_path,
    monkeypatch,
) -> None:
    package = load_task_package(TASK.parent)
    contract = _smoke_v2_contract(package)
    manifest = build_manifest(
        package,
        run_id="run_v11_partial_review_feedback",
        sandbox_backend="local",
        coverage_rejection_validation=True,
        public_review_contract=contract,
    )
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )

    class RejectingAdapter(MockModelAdapter):
        def __init__(self) -> None:
            super().__init__(package.public.task_id)

        def next_turn(self, context, tools):
            counts = {
                name: self.completed_tools.count(name)
                for name in set(self.completed_tools)
            }
            if counts.get("get_diff", 0) == 0:
                return super().next_turn(context, tools)
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        "review_task",
                        "v11-partial-source-rejection",
                        _wrong_target_review(context, contract),
                    )
                ]
            )

    runner = AgentRunner(tmp_path / "partial-runtime")
    rejecting_adapter = RejectingAdapter()
    monkeypatch.setattr(
        runner,
        "_model_adapter",
        lambda *_args, **_kwargs: rejecting_adapter,
    )
    original_phase_after_tool = runner._phase_after_tool

    def crash_after_rejection(
        run_id,
        phase,
        tool,
        result,
        task,
        workspace,
    ):
        if tool == "review_task" and result.status == "rejected":
            raise SystemExit(91)
        return original_phase_after_tool(
            run_id,
            phase,
            tool,
            result,
            task,
            workspace,
        )

    monkeypatch.setattr(runner, "_phase_after_tool", crash_after_rejection)
    with pytest.raises(SystemExit, match="91"):
        runner.start(TASK, model="mock", manifest=manifest)

    class PartialReviewAdapter(MockModelAdapter):
        def __init__(self) -> None:
            super().__init__(package.public.task_id)
            self.stage = 0

        def next_turn(self, context, tools):
            del tools
            payload = json.loads(context)
            if self.stage < 3:
                assert payload["coverage_rejection_feedback"] is not None
            if self.stage == 0:
                self.stage = 1
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "read_file",
                            "v11-partial-fresh-anchor",
                            {
                                "path": "mini_data_utils/csvlite.py",
                                "start_line": 1,
                                "end_line": 200,
                            },
                        )
                    ]
                )
            if self.stage == 1:
                self.stage = 2
                arguments = _review_arguments(
                    context,
                    contract,
                    complete=True,
                )
                validation_target = contract.requirements[
                    0
                ].coverage_targets[1]
                validation_row = next(
                    row
                    for row in arguments["coverage_targets"]
                    if row["coverage_target_id"]
                    == validation_target.coverage_target_id
                )
                validation_row["status"] = "unverified"
                validation_row["evidence_event_sequences"] = []
                inspection_row = arguments["coverage_targets"][0]
                arguments["requirements"][0]["status"] = (
                    "partially_verified"
                )
                arguments["requirements"][0][
                    "evidence_event_sequences"
                ] = list(inspection_row["evidence_event_sequences"])
                arguments["residual_risks"] = [
                    {
                        "requirement_ids": [
                            contract.requirements[0].requirement_id
                        ],
                        "risk": "One validation target remains unverified.",
                        "mitigation": "Refresh the registered check.",
                    }
                ]
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "review_task",
                            "v11-valid-partial-review",
                            arguments,
                        )
                    ]
                )
            if self.stage == 2:
                self.stage = 3
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "apply_patch",
                            "v11-feedback-clearing-mutation",
                            {
                                "patch": (
                                    "diff --git a/mini_data_utils/csvlite.py "
                                    "b/mini_data_utils/csvlite.py\n"
                                    "--- a/mini_data_utils/csvlite.py\n"
                                    "+++ b/mini_data_utils/csvlite.py\n"
                                    "@@ -6,4 +6,5 @@ import io\n"
                                    " def parse_rows(text: str) -> "
                                    "list[list[str]]:\n"
                                    "     \"\"\"Parse CSV text into rows while "
                                    "preserving quoted values.\"\"\"\n"
                                    "+    # Preserve logical records across "
                                    "physical newlines.\n"
                                    " \n"
                                    "     return list(csv.reader(io.StringIO("
                                    "text, newline=\"\")))\n"
                                )
                            },
                        )
                    ]
                )
            if self.stage == 3:
                assert payload["coverage_rejection_feedback"] is None
                self.stage = 4
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "apply_patch",
                            "v11-post-clear-mutation",
                            {
                                "patch": (
                                    "diff --git a/mini_data_utils/csvlite.py "
                                    "b/mini_data_utils/csvlite.py\n"
                                    "--- a/mini_data_utils/csvlite.py\n"
                                    "+++ b/mini_data_utils/csvlite.py\n"
                                    "@@ -8,3 +8,4 @@\n"
                                    "     # Preserve logical records across "
                                    "physical newlines.\n"
                                    "+    # Keep parsing delegated to the CSV "
                                    "state machine.\n"
                                    " \n"
                                    "     return list(csv.reader(io.StringIO("
                                    "text, newline=\"\")))\n"
                                )
                            },
                        )
                    ]
                )
            assert payload["coverage_rejection_feedback"] is None
            raise SystemExit(92)

    resumed = AgentRunner(runner.root)
    partial_adapter = PartialReviewAdapter()
    monkeypatch.setattr(
        resumed,
        "_model_adapter",
        lambda *_args, **_kwargs: partial_adapter,
    )
    with pytest.raises(SystemExit, match="92"):
        resumed.resume(manifest.run_id)
    partial_outcome = next(
        event
        for event in resumed.state.list_events(manifest.run_id)
        if event.type == EventType.TOOL_SUCCEEDED
        and event.correlation_id == "v11-valid-partial-review"
    )
    assert partial_outcome.payload["coverage_complete"] is False
    assert partial_outcome.payload["unresolved_coverage_target_ids"]
    assert partial_adapter.stage == 4
    assert any(
        event.type == EventType.PATCH_APPLIED
        and event.correlation_id == "v11-feedback-clearing-mutation"
        for event in resumed.state.list_events(manifest.run_id)
    )
    assert any(
        event.type == EventType.PATCH_APPLIED
        and event.correlation_id == "v11-post-clear-mutation"
        for event in resumed.state.list_events(manifest.run_id)
    )
    partial_events = resumed.state.list_events(manifest.run_id)
    clearing_mutation = next(
        event
        for event in partial_events
        if event.type == EventType.PATCH_APPLIED
        and event.correlation_id == "v11-feedback-clearing-mutation"
    )
    clearing_prepared = next(
        event
        for event in partial_events
        if event.type == EventType.PATCH_PREPARED
        and event.correlation_id == clearing_mutation.correlation_id
    )
    final_checkpoint = resumed.state.latest_checkpoint(manifest.run_id)
    assert final_checkpoint is not None
    with pytest.raises(RecoveryError):
        _coverage_rejection_feedback_v11(
            [
                event
                for event in partial_events
                if event.event_id != clearing_prepared.event_id
            ],
            worktree_diff_hash=final_checkpoint.worktree_diff_hash,
            artifact_store=resumed.artifacts,
            public_review_contract=contract,
        )

    clearing_call = next(
        event
        for event in partial_events
        if event.type == EventType.TOOL_CALLED
        and event.correlation_id == clearing_mutation.correlation_id
    )
    clearing_model = [
        event
        for event in partial_events
        if event.type == EventType.MODEL_CALLED
        and event.sequence < clearing_call.sequence
    ][-1]
    clearing_response_document = json.loads(
        Path(clearing_model.payload["artifact_path"]).read_text(
            encoding="utf-8"
        )
    )
    clearing_response_document["tool_calls"] = [
        item
        for item in clearing_response_document["tool_calls"]
        if item["action_id"] != clearing_call.correlation_id
    ]
    forged_clearing_response = resumed.artifacts.put_json(
        clearing_response_document
    )
    forged_clearing_events = [
        event.model_copy(
            update={
                "payload": {
                    **event.payload,
                    "artifact_id": forged_clearing_response.artifact_id,
                    "artifact_path": forged_clearing_response.path,
                }
            }
        )
        if event.event_id == clearing_model.event_id
        else event
        for event in partial_events
    ]
    with pytest.raises(RecoveryError, match="model-response-bound"):
        _coverage_rejection_feedback_v11(
            forged_clearing_events,
            worktree_diff_hash=final_checkpoint.worktree_diff_hash,
            artifact_store=resumed.artifacts,
            public_review_contract=contract,
        )


def _tampered_events(
    events: list[RunEvent],
    failure_sequence: int,
    *,
    field: str,
) -> list[RunEvent]:
    tampered = []
    for event in events:
        if event.sequence != failure_sequence:
            tampered.append(event)
            continue
        payload = dict(event.payload)
        if field == "error_details":
            details = dict(payload["error_details"])
            details["allowed_event_sequences"] = [
                details["submitted_event_sequences"][0]
            ]
            payload["error_details"] = details
        elif field == "result_artifact":
            descriptor = dict(payload["result_artifact"])
            descriptor["content_hash"] = "sha256:" + ("0" * 64)
            payload["result_artifact"] = descriptor
        else:  # pragma: no cover - test helper guard
            raise AssertionError(field)
        tampered.append(event.model_copy(update={"payload": payload}))
    return tampered


def test_v11_rejection_survives_restart_and_recovers_exact_anchor(
    tmp_path,
    monkeypatch,
) -> None:
    package = load_task_package(TASK.parent)
    contract = _smoke_v2_contract(package)
    manifest = build_manifest(
        package,
        run_id="run_v11_exact_anchor_resume",
        sandbox_backend="local",
        coverage_rejection_validation=True,
        public_review_contract=contract,
    )
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )

    class RejectingAdapter(MockModelAdapter):
        def __init__(self) -> None:
            super().__init__(package.public.task_id)
            self.script = replace(
                self.script,
                patch=(
                    "diff --git a/mini_data_utils/csvlite.py "
                    "b/mini_data_utils/csvlite.py\n"
                    "--- a/mini_data_utils/csvlite.py\n"
                    "+++ b/mini_data_utils/csvlite.py\n"
                    "@@ -1,13 +1,11 @@\n"
                    ' \"\"\"A deliberately small CSV reader with one audited defect.\"\"\"\n'
                    " \n"
                    " import csv\n"
                    "+from io import StringIO\n"
                    " \n"
                    " \n"
                    " def parse_rows(text: str) -> list[list[str]]:\n"
                    '     \"\"\"Parse CSV text into rows while preserving quoted values.\"\"\"\n'
                    " \n"
                    "-    rows: list[list[str]] = []\n"
                    "-    for physical_line in text.splitlines():\n"
                    "-        rows.extend(csv.reader([physical_line]))\n"
                    "-    return rows\n"
                    "+    return list(csv.reader(StringIO(text, newline=\"\")))\n"
                    " \n"
                ),
            )

        def next_turn(self, context, tools):
            counts = {
                name: self.completed_tools.count(name)
                for name in set(self.completed_tools)
            }
            if counts.get("get_diff", 0) == 0:
                return super().next_turn(context, tools)
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        "review_task",
                        "v11-wrong-target-review",
                        _wrong_target_review(context, contract),
                    )
                ]
            )

    runner = AgentRunner(tmp_path / "runtime")
    rejecting_adapter = RejectingAdapter()
    monkeypatch.setattr(
        runner,
        "_model_adapter",
        lambda *_args, **_kwargs: rejecting_adapter,
    )
    original_phase_after_tool = runner._phase_after_tool

    def crash_after_durable_rejection(
        run_id,
        phase,
        tool,
        result,
        task,
        workspace,
    ):
        if (
            tool == "review_task"
            and result.status == "rejected"
            and result.error_code == "COVERAGE_CITATION_REJECTED"
        ):
            raise SystemExit(86)
        return original_phase_after_tool(
            run_id,
            phase,
            tool,
            result,
            task,
            workspace,
        )

    monkeypatch.setattr(
        runner,
        "_phase_after_tool",
        crash_after_durable_rejection,
    )
    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK, model="mock", manifest=manifest)

    events_before_resume = runner.state.list_events(manifest.run_id)
    failure = next(
        event
        for event in events_before_resume
        if event.type == EventType.TOOL_FAILED
        and event.payload.get("tool") == "review_task"
    )
    assert failure.payload["error_code"] == "COVERAGE_CITATION_REJECTED"
    assert failure.payload["error_details"]["reason"] == (
        "target_evidence_not_allowed"
    )
    submitted_sequences = failure.payload["error_details"][
        "submitted_event_sequences"
    ]
    assert len(submitted_sequences) == 1
    assert all(
        event.sequence != submitted_sequences[0]
        for event in events_before_resume
    )
    result_artifact = Artifact.model_validate(
        failure.payload["result_artifact"]
    )
    result_document = json.loads(
        runner.artifacts.read_bytes(result_artifact).decode("utf-8")
    )
    assert result_document["error_details"] == failure.payload[
        "error_details"
    ]
    assert sum(
        event.type == EventType.PATCH_APPLIED
        for event in events_before_resume
    ) == 1

    checkpoint = runner.state.latest_checkpoint(manifest.run_id)
    assert checkpoint is not None
    built = build_context_with_evidence(
        package.public,
        events_before_resume,
        checkpoint,
        policy_version="phase-evidence-v11",
        artifact_store=runner.artifacts,
        budget=manifest.budget,
        max_output_tokens=manifest.model.max_output_tokens,
        public_review_contract=contract,
    )
    rendered = json.loads(built.rendered)
    feedback = rendered["coverage_rejection_feedback"]
    assert feedback["schema_version"] == (
        "coverage-rejection-feedback-v1"
    )
    assert feedback["source_failure_sequence"] == failure.sequence
    assert feedback["coverage_target_id"] == contract.requirements[
        0
    ].coverage_targets[0].coverage_target_id
    assert feedback["submitted_event_sequences"] == failure.payload[
        "error_details"
    ]["submitted_event_sequences"]
    assert feedback["allowed_event_sequences"] == []
    assert feedback["required_evidence"] == {
        "tool": "read_file",
        "path": "mini_data_utils/csvlite.py",
        "anchor": "def parse_rows",
    }
    assert all(
        event["sequence"] != failure.sequence
        for event in rendered["recent_events"]
    )
    assert built.evidence["schema_version"] == (
        "context-build-evidence-v11"
    )
    assert built.evidence["coverage_rejection_feedback"][
        "included"
    ] is True

    for field in ("error_details", "result_artifact"):
        with pytest.raises(RecoveryError):
            build_context_with_evidence(
                package.public,
                _tampered_events(
                    events_before_resume,
                    failure.sequence,
                    field=field,
                ),
                checkpoint,
                policy_version="phase-evidence-v11",
                artifact_store=runner.artifacts,
                budget=manifest.budget,
                max_output_tokens=manifest.model.max_output_tokens,
                public_review_contract=contract,
            )

    for semantic_tamper in ("reason", "guidance", "anchor"):
        tampered_document = copy.deepcopy(result_document)
        tampered_details = tampered_document["error_details"]
        if semantic_tamper == "reason":
            tampered_details["reason"] = (
                "verified_target_evidence_mismatch"
            )
        elif semantic_tamper == "guidance":
            tampered_details["guidance"] = "WRONG BUT PUBLIC"
        else:
            tampered_details["required_evidence"]["anchor"] = (
                "def unrelated_anchor"
            )
        tampered_artifact = runner.artifacts.put_json(tampered_document)
        self_consistent_events = [
            event.model_copy(
                update={
                    "payload": {
                        **event.payload,
                        "artifact_id": tampered_artifact.artifact_id,
                        "artifact_path": tampered_artifact.path,
                        "result_artifact": tampered_artifact.model_dump(
                            mode="json"
                        ),
                        "error_details": tampered_details,
                    }
                }
            )
            if event.sequence == failure.sequence
            else event
            for event in events_before_resume
        ]
        with pytest.raises(RecoveryError):
            build_context_with_evidence(
                package.public,
                self_consistent_events,
                checkpoint,
                policy_version="phase-evidence-v11",
                artifact_store=runner.artifacts,
                budget=manifest.budget,
                max_output_tokens=manifest.model.max_output_tokens,
                public_review_contract=contract,
            )

    source_call = next(
        event
        for event in events_before_resume
        if event.type == EventType.TOOL_CALLED
        and event.correlation_id == failure.correlation_id
    )
    input_tampered_events = [
        event.model_copy(
            update={
                "payload": {
                    **event.payload,
                    "input_artifact": {
                        **event.payload["input_artifact"],
                        "content_hash": "sha256:" + ("0" * 64),
                    },
                }
            }
        )
        if event.sequence == source_call.sequence
        else event
        for event in events_before_resume
    ]
    with pytest.raises(RecoveryError):
        build_context_with_evidence(
            package.public,
            input_tampered_events,
            checkpoint,
            policy_version="phase-evidence-v11",
            artifact_store=runner.artifacts,
            budget=manifest.budget,
            max_output_tokens=manifest.model.max_output_tokens,
            public_review_contract=contract,
        )

    source_input_artifact = Artifact.model_validate(
        source_call.payload["input_artifact"]
    )
    source_input_document = json.loads(
        runner.artifacts.read_bytes(source_input_artifact).decode(
            "utf-8"
        )
    )
    missing_context_id = "art_v11_missing_request_context"
    source_input_document["execution_context"][
        "request_artifact_id"
    ] = missing_context_id
    missing_context_input = runner.artifacts.put_json(
        source_input_document
    )
    missing_context_events = [
        event.model_copy(
            update={
                "payload": {
                    **event.payload,
                    "artifact_id": missing_context_input.artifact_id,
                    "artifact_path": missing_context_input.path,
                    "input_artifact": missing_context_input.model_dump(
                        mode="json"
                    ),
                    "request_artifact_id": missing_context_id,
                }
            }
        )
        if event.sequence == source_call.sequence
        else event
        for event in events_before_resume
    ]
    with pytest.raises(RecoveryError):
        build_context_with_evidence(
            package.public,
            missing_context_events,
            checkpoint,
            policy_version="phase-evidence-v11",
            artifact_store=runner.artifacts,
            budget=manifest.budget,
            max_output_tokens=manifest.model.max_output_tokens,
            public_review_contract=contract,
        )

    source_get_diff = next(
        event
        for event in events_before_resume
        if event.sequence
        == failure.payload["error_details"]["source_get_diff_sequence"]
    )
    source_get_diff_call = next(
        event
        for event in events_before_resume
        if event.type == EventType.TOOL_CALLED
        and event.correlation_id == source_get_diff.correlation_id
        and event.payload.get("tool") == "get_diff"
    )
    with pytest.raises(RecoveryError, match="correlated call"):
        build_context_with_evidence(
            package.public,
            [
                event
                for event in events_before_resume
                if event.event_id != source_get_diff_call.event_id
            ],
            checkpoint,
            policy_version="phase-evidence-v11",
            artifact_store=runner.artifacts,
            budget=manifest.budget,
            max_output_tokens=manifest.model.max_output_tokens,
            public_review_contract=contract,
        )

    source_diff_artifact = Artifact.model_validate(
        source_get_diff.payload["result_artifact"]
    )
    forged_source_diff_document = json.loads(
        runner.artifacts.read_bytes(source_diff_artifact).decode("utf-8")
    )
    forged_source_diff_document["patch"] += "\n# forged source diff\n"
    forged_source_diff_artifact = runner.artifacts.put_json(
        forged_source_diff_document
    )
    forged_source_diff_events = [
        event.model_copy(
            update={
                "payload": {
                    **event.payload,
                    "artifact_id": forged_source_diff_artifact.artifact_id,
                    "artifact_path": forged_source_diff_artifact.path,
                    "result_artifact": forged_source_diff_artifact.model_dump(
                        mode="json"
                    ),
                }
            }
        )
        if event.sequence == source_get_diff.sequence
        else event
        for event in events_before_resume
    ]
    with pytest.raises(RecoveryError, match="get_diff result binding"):
        build_context_with_evidence(
            package.public,
            forged_source_diff_events,
            checkpoint,
            policy_version="phase-evidence-v11",
            artifact_store=runner.artifacts,
            budget=manifest.budget,
            max_output_tokens=manifest.model.max_output_tokens,
            public_review_contract=contract,
        )

    duplicate_failure = failure.model_copy(
        update={
            "event_id": "evt_v11_duplicate_rejection_outcome",
            "sequence": events_before_resume[-1].sequence + 1,
            "timestamp": utc_now(),
        }
    )
    with pytest.raises(RecoveryError, match="exact call/outcome pair"):
        build_context_with_evidence(
            package.public,
            [*events_before_resume, duplicate_failure],
            checkpoint,
            policy_version="phase-evidence-v11",
            artifact_store=runner.artifacts,
            budget=manifest.budget,
            max_output_tokens=manifest.model.max_output_tokens,
            public_review_contract=contract,
        )

    orphan_review_success = RunEvent(
        event_id="evt_v11_orphan_review_success",
        run_id=manifest.run_id,
        sequence=events_before_resume[-1].sequence + 1,
        type=EventType.TOOL_SUCCEEDED,
        timestamp=utc_now(),
        actor="tool-gateway",
        correlation_id="v11-orphan-review-success",
        payload={
            "tool": "review_task",
            "status": "succeeded",
            "worktree_diff_hash": checkpoint.worktree_diff_hash,
        },
    )
    with pytest.raises(RecoveryError, match="correlated call"):
        _coverage_rejection_feedback_v11(
            [*events_before_resume, orphan_review_success],
            worktree_diff_hash=checkpoint.worktree_diff_hash,
            artifact_store=runner.artifacts,
            public_review_contract=contract,
        )

    replacement_diff_hash = sha256_text("replacement mutation")
    replacement_mutation = RunEvent(
        event_id="evt_v11_replacement_mutation",
        run_id=manifest.run_id,
        sequence=events_before_resume[-1].sequence + 1,
        type=EventType.PATCH_APPLIED,
        timestamp=utc_now(),
        actor="tool-gateway",
        correlation_id="v11-replacement-mutation",
        payload={"worktree_diff_hash": replacement_diff_hash},
    )
    with pytest.raises(
        RecoveryError,
        match="feedback-clearing mutation lifecycle is ambiguous",
    ):
        _coverage_rejection_feedback_v11(
            [*events_before_resume, replacement_mutation],
            worktree_diff_hash=replacement_diff_hash,
            artifact_store=runner.artifacts,
            public_review_contract=contract,
        )

    class RecoveryAdapter:
        def __init__(self) -> None:
            self.stage = 0
            self.contexts: list[dict] = []
            self.active_feedback: dict | None = None

        def next_turn(self, context, tools):
            del tools
            payload = json.loads(context)
            self.contexts.append(payload)
            if self.stage == 0:
                self.active_feedback = payload[
                    "coverage_rejection_feedback"
                ]
                assert self.active_feedback == feedback
                assert all(
                    event["sequence"] != failure.sequence
                    for event in payload["recent_events"]
                )
                self.stage = 1
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "read_file",
                            "v11-exact-anchor-read",
                            {
                                "path": "mini_data_utils/csvlite.py",
                                "start_line": 6,
                                "end_line": 8,
                            },
                        )
                    ]
                )
            if self.stage == 1:
                assert payload["coverage_rejection_feedback"] == (
                    self.active_feedback
                )
                self.stage = 2
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "read_file",
                            "v11-exact-anchor-read-latest",
                            {
                                "path": "mini_data_utils/csvlite.py",
                                "start_line": 1,
                                "end_line": 50,
                            },
                        )
                    ]
                )
            if self.stage == 2:
                assert payload["coverage_rejection_feedback"] == (
                    self.active_feedback
                )
                self.stage = 3
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "get_diff",
                            "v11-recovery-diff",
                            {},
                        )
                    ]
                )
            if self.stage == 3:
                assert payload["coverage_rejection_feedback"] == (
                    self.active_feedback
                )
                target_id = contract.requirements[0].coverage_targets[
                    0
                ].coverage_target_id
                assert payload["review_evidence"][
                    "coverage_target_event_sequences"
                ][target_id]
                self.stage = 4
                arguments = _review_arguments(
                    context,
                    contract,
                    complete=True,
                )
                arguments["coverage_targets"].reverse()
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "review_task",
                            "v11-recovered-review",
                            arguments,
                        )
                    ]
                )
            if self.stage == 4:
                assert payload["coverage_rejection_feedback"] is None
                self.stage = 5
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "finish_task",
                            "v11-recovered-finish",
                            {},
                        )
                    ]
                )
            raise AssertionError(f"unexpected recovery stage: {self.stage}")

    resumed_runner = AgentRunner(runner.root)
    recovery_adapter = RecoveryAdapter()
    monkeypatch.setattr(
        resumed_runner,
        "_model_adapter",
        lambda *_args, **_kwargs: recovery_adapter,
    )

    result = resumed_runner.resume(manifest.run_id)
    events = resumed_runner.state.list_events(manifest.run_id)

    assert result["scope_compliant_success"] is True
    assert recovery_adapter.stage == 5
    exact_read = next(
        event
        for event in events
        if event.type == EventType.TOOL_SUCCEEDED
        and event.correlation_id == "v11-exact-anchor-read"
    )
    assert exact_read.sequence > failure.sequence
    exact_read_artifact = Artifact.model_validate(
        exact_read.payload["result_artifact"]
    )
    exact_read_document = json.loads(
        resumed_runner.artifacts.read_bytes(exact_read_artifact).decode(
            "utf-8"
        )
    )
    assert exact_read_document["path"] == "mini_data_utils/csvlite.py"
    assert "def parse_rows" in exact_read_document["content"]
    latest_exact_read = next(
        event
        for event in events
        if event.type == EventType.TOOL_SUCCEEDED
        and event.correlation_id == "v11-exact-anchor-read-latest"
    )
    latest_exact_read_artifact = Artifact.model_validate(
        latest_exact_read.payload["result_artifact"]
    )
    latest_exact_read_document = json.loads(
        resumed_runner.artifacts.read_bytes(
            latest_exact_read_artifact
        ).decode("utf-8")
    )
    assert latest_exact_read_document["path"] == (
        "mini_data_utils/csvlite.py"
    )
    assert "def parse_rows" in latest_exact_read_document["content"]
    refreshed_diff = next(
        event
        for event in events
        if event.type == EventType.TOOL_SUCCEEDED
        and event.correlation_id == "v11-recovery-diff"
    )
    recovered_review = next(
        event
        for event in events
        if event.type == EventType.TOOL_SUCCEEDED
        and event.correlation_id == "v11-recovered-review"
    )
    assert (
        exact_read.sequence
        < latest_exact_read.sequence
        < refreshed_diff.sequence
        < recovered_review.sequence
    )
    recovered_review_artifact = Artifact.model_validate(
        recovered_review.payload["review_artifact"]
    )
    recovered_review_document = json.loads(
        resumed_runner.artifacts.read_bytes(
            recovered_review_artifact
        ).decode("utf-8")
    )
    inspection_target_id = contract.requirements[0].coverage_targets[
        0
    ].coverage_target_id
    inspection_review_row = next(
        row
        for row in recovered_review_document["coverage_targets"]
        if row["coverage_target_id"] == inspection_target_id
    )
    assert inspection_review_row["evidence_event_sequences"] == [
        latest_exact_read.sequence
    ]
    assert sum(
        event.type == EventType.TOOL_CALLED
        and event.payload.get("tool") == "apply_patch"
        for event in events
    ) == 1
    assert sum(event.type == EventType.PATCH_PREPARED for event in events) == 1
    assert sum(event.type == EventType.PATCH_APPLIED for event in events) == 1
    assert sum(
        event.type == EventType.TOOL_FAILED
        and event.payload.get("tool") == "review_task"
        for event in events
    ) == 1
    assert sum(
        event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "review_task"
        and event.payload.get("coverage_complete") is True
        for event in events
    ) == 1
    assert sum(
        event.type == EventType.SUBMISSION_ACCEPTED for event in events
    ) == 1

    final_feedback, final_feedback_evidence, final_feedback_sequence = (
        _coverage_rejection_feedback_v11(
            events,
            worktree_diff_hash=(
                resumed_runner.state.latest_checkpoint(
                    manifest.run_id
                ).worktree_diff_hash
            ),
            artifact_store=resumed_runner.artifacts,
            public_review_contract=contract,
        )
    )
    assert final_feedback is None
    assert final_feedback_evidence["included"] is False
    assert final_feedback_sequence is None

    qualification = qualify_run(
        manifest.run_id,
        task_dir=TASK.parent,
        root=resumed_runner.root,
    )
    checks = {
        check["check_id"]: check for check in qualification["checks"]
    }
    assert qualification["qualified"] is False
    assert qualification["evaluation_reached"] is True
    for check_id in (
        "agent_visible_artifacts",
        "public_private_boundary",
        "public_coverage_contract",
        "coverage_decision_integrity",
        "coverage_submission_lifecycle",
        "coverage_recovery_contract",
        "coverage_terminal_contract",
        "coverage_rejection_recovery_contract",
    ):
        assert checks[check_id]["passed"] is True, checks[check_id]
    agent_visible_text = canonical_json(
        recovery_adapter.contexts
    ).lower()
    private_tokens = _private_leak_tokens(package, api_key=None)
    assert sorted(
        token
        for token in private_tokens
        if token.lower() in agent_visible_text
    ) == []

    context_events = [
        event for event in events if event.type == EventType.CONTEXT_BUILT
    ]
    worker_claims = resumed_runner.state.list_worker_claims(manifest.run_id)
    qualifier_arguments = {
        "root": resumed_runner.root,
        "manifest": manifest,
        "package": package,
        "context_events": context_events,
        "worker_claims": worker_claims,
    }
    final_checkpoint = resumed_runner.state.latest_checkpoint(manifest.run_id)
    assert final_checkpoint is not None

    def assert_runtime_rejects(tampered_events: list[RunEvent]) -> None:
        with pytest.raises(RecoveryError):
            _coverage_rejection_feedback_v11(
                tampered_events,
                worktree_diff_hash=final_checkpoint.worktree_diff_hash,
                artifact_store=resumed_runner.artifacts,
                public_review_contract=contract,
            )

    def assert_qualifier_rejects(
        tampered_events: list[RunEvent],
    ) -> None:
        passed, tamper_details = (
            _v11_coverage_rejection_recovery_evidence(
                events=tampered_events,
                **{
                    **qualifier_arguments,
                    "context_events": [
                        event
                        for event in tampered_events
                        if event.type == EventType.CONTEXT_BUILT
                    ],
                },
            )
        )
        assert passed is False, tamper_details
        assert tamper_details["failed_rejection_sequences"] == [
            failure.sequence
        ]

    first_rehydrated_context = next(
        event
        for event in context_events
        if event.sequence > failure.sequence
    )
    restart_checkpoint = next(
        event
        for event in events
        if failure.sequence
        < event.sequence
        < first_rehydrated_context.sequence
    )
    assert restart_checkpoint.type == EventType.CHECKPOINT_SAVED
    old_worker_activity = restart_checkpoint.model_copy(
        update={
            "type": EventType.TOOL_CALLED,
            "actor": "agent",
            "correlation_id": "v11-forged-old-worker-call",
            "payload": {"tool": "read_file"},
        }
    )
    assert_qualifier_rejects(
        [
            old_worker_activity
            if event.event_id == restart_checkpoint.event_id
            else event
            for event in events
        ]
    )

    source_context = next(
        event
        for event in context_events
        if event.payload.get("artifact_id")
        == source_call.payload["request_artifact_id"]
    )
    source_model = next(
        event
        for event in events
        if event.type == EventType.MODEL_CALLED
        and source_context.sequence < event.sequence < source_call.sequence
    )
    source_request_document = json.loads(
        Path(source_context.payload["artifact_path"]).read_text(
            encoding="utf-8"
        )
    )
    forged_source_feedback = copy.deepcopy(feedback)
    forged_source_feedback_build = copy.deepcopy(
        built.evidence["coverage_rejection_feedback"]
    )
    forged_source_feedback_build["source_through_sequence"] = (
        source_context.sequence - 1
    )
    forged_source_rendered = json.loads(
        source_request_document["request_body"]["context"]
    )
    forged_source_rendered["coverage_rejection_feedback"] = (
        forged_source_feedback
    )
    forged_source_rendered_text = json.dumps(
        forged_source_rendered,
        indent=2,
        ensure_ascii=False,
        default=str,
    )
    source_request_document["request_body"]["context"] = (
        forged_source_rendered_text
    )
    source_request_document["context_build"][
        "coverage_rejection_feedback"
    ] = forged_source_feedback_build
    source_request_document["request_body_hash"] = sha256_text(
        canonical_json(source_request_document["request_body"])
    )
    forged_source_request = resumed_runner.artifacts.put_json(
        source_request_document
    )
    forged_source_input_document = json.loads(
        resumed_runner.artifacts.read_bytes(
            Artifact.model_validate(source_call.payload["input_artifact"])
        ).decode("utf-8")
    )
    forged_source_input_document["execution_context"][
        "request_artifact_id"
    ] = forged_source_request.artifact_id
    forged_source_input_document["execution_context"][
        "coverage_rejection_feedback"
    ] = forged_source_feedback
    forged_source_input = resumed_runner.artifacts.put_json(
        forged_source_input_document
    )
    forged_active_source_events = [
        event.model_copy(
            update={
                "payload": {
                    **event.payload,
                    "artifact_id": forged_source_request.artifact_id,
                    "artifact_path": forged_source_request.path,
                    "request_body_hash": source_request_document[
                        "request_body_hash"
                    ],
                    "context_hash": sha256_text(
                        forged_source_rendered_text
                    ),
                    "coverage_rejection_feedback": (
                        forged_source_feedback_build
                    ),
                }
            }
        )
        if event.event_id == source_context.event_id
        else event.model_copy(
            update={
                "payload": {
                    **event.payload,
                    "request_artifact_id": (
                        forged_source_request.artifact_id
                    ),
                    "request_artifact_path": forged_source_request.path,
                    "request_artifact_hash": (
                        forged_source_request.content_hash
                    ),
                    "request_body_hash": source_request_document[
                        "request_body_hash"
                    ],
                }
            }
        )
        if event.event_id == source_model.event_id
        else event.model_copy(
            update={
                "payload": {
                    **event.payload,
                    "artifact_id": forged_source_input.artifact_id,
                    "artifact_path": forged_source_input.path,
                    "input_artifact": forged_source_input.model_dump(
                        mode="json"
                    ),
                    "request_artifact_id": (
                        forged_source_request.artifact_id
                    ),
                }
            }
        )
        if event.event_id == source_call.event_id
        else event
        for event in events
    ]
    assert_runtime_rejects(forged_active_source_events)
    assert_qualifier_rejects(forged_active_source_events)

    source_response_document = json.loads(
        Path(source_model.payload["artifact_path"]).read_text(
            encoding="utf-8"
        )
    )
    source_response_document["tool_calls"] = []
    forged_source_response = resumed_runner.artifacts.put_json(
        source_response_document
    )
    missing_model_call_events = [
        event.model_copy(
            update={
                "payload": {
                    **event.payload,
                    "artifact_id": forged_source_response.artifact_id,
                    "artifact_path": forged_source_response.path,
                }
            }
        )
        if event.event_id == source_model.event_id
        else event
        for event in events
    ]
    assert_runtime_rejects(missing_model_call_events)
    assert_qualifier_rejects(missing_model_call_events)

    for field, forged_value in (
        ("execution", "recovered-without-dispatch"),
        ("normalized_call_hash", "sha256:" + ("0" * 64)),
    ):
        source_call_tamper = [
            event.model_copy(
                update={
                    "payload": {
                        **event.payload,
                        field: forged_value,
                    }
                }
            )
            if event.event_id == source_call.event_id
            else event
            for event in events
        ]
        assert_runtime_rejects(source_call_tamper)
        assert_qualifier_rejects(source_call_tamper)

    original_source_input = json.loads(
        resumed_runner.artifacts.read_bytes(
            Artifact.model_validate(source_call.payload["input_artifact"])
        ).decode("utf-8")
    )

    def rewritten_source_call(
        rewritten_input: dict,
    ) -> RunEvent:
        rewritten_artifact = resumed_runner.artifacts.put_json(
            rewritten_input
        )
        rewritten_arguments = rewritten_input["input"]
        rewritten_input_hash = sha256_text(
            canonical_json(
                {
                    "tool": "review_task",
                    "input": rewritten_arguments,
                }
            )
        )
        rewritten_normalized_hash = sha256_text(
            canonical_json(
                {
                    "tool": "review_task",
                    "input": rewritten_arguments,
                    "worktree_diff_hash": source_call.payload[
                        "worktree_diff_hash"
                    ],
                    "state_marker": None,
                }
            )
        )
        return source_call.model_copy(
            update={
                "payload": {
                    **source_call.payload,
                    "artifact_id": rewritten_artifact.artifact_id,
                    "artifact_path": rewritten_artifact.path,
                    "input_artifact": rewritten_artifact.model_dump(
                        mode="json"
                    ),
                    "input_hash": rewritten_input_hash,
                    "normalized_call_hash": rewritten_normalized_hash,
                }
            }
        )

    def rewritten_source_model(
        rewritten_arguments: dict,
    ) -> RunEvent:
        response_document = json.loads(
            Path(source_model.payload["artifact_path"]).read_text(
                encoding="utf-8"
            )
        )
        response_call = next(
            item
            for item in response_document["tool_calls"]
            if item["action_id"] == source_call.correlation_id
        )
        response_call["arguments"] = rewritten_arguments
        response_artifact = resumed_runner.artifacts.put_json(
            response_document
        )
        return source_model.model_copy(
            update={
                "payload": {
                    **source_model.payload,
                    "artifact_id": response_artifact.artifact_id,
                    "artifact_path": response_artifact.path,
                }
            }
        )

    post_rejection_unchecked_input = copy.deepcopy(
        original_source_input
    )
    post_rejection_target = post_rejection_unchecked_input["input"][
        "coverage_targets"
    ][1]
    assert post_rejection_target["evidence_event_sequences"]
    post_rejection_target["status"] = "unverified"
    post_rejection_unchecked_input["input"]["targeted_validation"] = []
    post_rejection_unchecked_input["input"]["residual_risks"] = [
        {"not": "validated after the earlier structured rejection"}
    ]
    post_rejection_call = rewritten_source_call(
        post_rejection_unchecked_input
    )
    post_rejection_model = rewritten_source_model(
        post_rejection_unchecked_input["input"]
    )
    post_rejection_events = [
        post_rejection_call
        if event.event_id == source_call.event_id
        else post_rejection_model
        if event.event_id == source_model.event_id
        else event
        for event in events_before_resume
    ]
    post_feedback, _, _ = _coverage_rejection_feedback_v11(
        post_rejection_events,
        worktree_diff_hash=checkpoint.worktree_diff_hash,
        artifact_store=resumed_runner.artifacts,
        public_review_contract=contract,
    )
    assert post_feedback is not None
    post_rejection_passed, post_rejection_details = (
        _v11_coverage_rejection_recovery_evidence(
            events=post_rejection_events,
            **{
                **qualifier_arguments,
                "context_events": [
                    event
                    for event in post_rejection_events
                    if event.type == EventType.CONTEXT_BUILT
                ],
            },
        )
    )
    assert post_rejection_passed is False
    assert post_rejection_details["failure_reasons"] == [
            {
                "sequence": failure.sequence,
                "reason": "v11 rejection has no post-failure model request",
            }
    ]

    malformed_source_inputs: list[dict] = []
    missing_requirement_input = copy.deepcopy(original_source_input)
    missing_requirement_input["input"]["requirements"] = []
    malformed_source_inputs.append(missing_requirement_input)
    missing_target_input = copy.deepcopy(original_source_input)
    missing_target_input["input"]["coverage_targets"] = [
        row
        for row in missing_target_input["input"]["coverage_targets"]
        if row["coverage_target_id"]
        == failure.payload["error_details"]["coverage_target_id"]
    ]
    malformed_source_inputs.append(missing_target_input)
    for malformed_input in malformed_source_inputs:
        forged_source_call = rewritten_source_call(malformed_input)
        forged_source_model = rewritten_source_model(
            malformed_input["input"]
        )
        malformed_source_events = [
            forged_source_call
            if event.event_id == source_call.event_id
            else forged_source_model
            if event.event_id == source_model.event_id
            else event
            for event in events
        ]
        assert_runtime_rejects(malformed_source_events)
        assert_qualifier_rejects(malformed_source_events)

    recovered_review_call = next(
        event
        for event in events
        if event.type == EventType.TOOL_CALLED
        and event.correlation_id == recovered_review.correlation_id
    )
    recovered_review_input_artifact = Artifact.model_validate(
        recovered_review_call.payload["input_artifact"]
    )
    forged_review_input_document = json.loads(
        resumed_runner.artifacts.read_bytes(
            recovered_review_input_artifact
        ).decode("utf-8")
    )
    validation_target_id = contract.requirements[0].coverage_targets[
        1
    ].coverage_target_id
    forged_validation_input_row = next(
        row
        for row in forged_review_input_document["input"][
            "coverage_targets"
        ]
        if row["coverage_target_id"] == validation_target_id
    )
    assert forged_validation_input_row["evidence_event_sequences"]
    forged_validation_input_row["evidence_event_sequences"] = []
    forged_requirement_input_row = forged_review_input_document["input"][
        "requirements"
    ][0]
    forged_requirement_input_row["evidence_event_sequences"] = list(
        next(
            row
            for row in forged_review_input_document["input"][
                "coverage_targets"
            ]
            if row["coverage_target_id"] == inspection_target_id
        )["evidence_event_sequences"]
    )
    forged_review_input_artifact = resumed_runner.artifacts.put_json(
        forged_review_input_document
    )
    forged_review_arguments = forged_review_input_document["input"]
    forged_review_call = recovered_review_call.model_copy(
        update={
            "payload": {
                **recovered_review_call.payload,
                "artifact_id": forged_review_input_artifact.artifact_id,
                "artifact_path": forged_review_input_artifact.path,
                "input_artifact": forged_review_input_artifact.model_dump(
                    mode="json"
                ),
                "input_hash": sha256_text(
                    canonical_json(
                        {
                            "tool": "review_task",
                            "input": forged_review_arguments,
                        }
                    )
                ),
                "normalized_call_hash": sha256_text(
                    canonical_json(
                        {
                            "tool": "review_task",
                            "input": forged_review_arguments,
                            "worktree_diff_hash": (
                                recovered_review_call.payload[
                                    "worktree_diff_hash"
                                ]
                            ),
                            "state_marker": None,
                        }
                    )
                ),
            }
        }
    )
    forged_review_document = copy.deepcopy(recovered_review_document)
    next(
        row
        for row in forged_review_document["coverage_targets"]
        if row["coverage_target_id"] == validation_target_id
    )["evidence_event_sequences"] = []
    forged_review_document["requirements"][0][
        "evidence_event_sequences"
    ] = list(forged_requirement_input_row["evidence_event_sequences"])
    forged_review_artifact = resumed_runner.artifacts.put_json(
        forged_review_document
    )
    recovered_review_result_artifact = Artifact.model_validate(
        recovered_review.payload["result_artifact"]
    )
    forged_review_result_document = json.loads(
        resumed_runner.artifacts.read_bytes(
            recovered_review_result_artifact
        ).decode("utf-8")
    )
    forged_review_result_document["review"] = forged_review_document
    forged_review_result_document["review_artifact"] = (
        forged_review_artifact.model_dump(mode="json")
    )
    forged_review_result_document["review_content_hash"] = (
        forged_review_artifact.content_hash
    )
    forged_review_result_artifact = resumed_runner.artifacts.put_json(
        forged_review_result_document
    )
    forged_review_outcome = recovered_review.model_copy(
        update={
            "payload": {
                **recovered_review.payload,
                "artifact_id": forged_review_result_artifact.artifact_id,
                "artifact_path": forged_review_result_artifact.path,
                "result_artifact": forged_review_result_artifact.model_dump(
                    mode="json"
                ),
                "review_artifact": forged_review_artifact.model_dump(
                    mode="json"
                ),
                "review_content_hash": forged_review_artifact.content_hash,
            }
        }
    )
    forged_clearing_review_events = [
        forged_review_call
        if event.event_id == recovered_review_call.event_id
        else forged_review_outcome
        if event.event_id == recovered_review.event_id
        else event
        for event in events
    ]
    assert_runtime_rejects(forged_clearing_review_events)
    assert_qualifier_rejects(forged_clearing_review_events)

    clear_context = next(
        event
        for event in context_events
        if event.sequence > recovered_review.sequence
    )
    clear_request_document = json.loads(
        Path(clear_context.payload["artifact_path"]).read_text(
            encoding="utf-8"
        )
    )
    clear_model = next(
        event
        for event in events
        if event.type == EventType.MODEL_CALLED
        and event.payload.get("request_artifact_id")
        == clear_context.payload.get("artifact_id")
    )
    forged_clear_feedback_document = copy.deepcopy(
        clear_request_document
    )
    forged_clear_feedback_document["context_build"][
        "coverage_rejection_feedback"
    ]["unexpected"] = "forged"
    forged_clear_feedback = forged_clear_feedback_document[
        "context_build"
    ]["coverage_rejection_feedback"]
    forged_clear_feedback_artifact = resumed_runner.artifacts.put_json(
        forged_clear_feedback_document
    )
    forged_clear_feedback_events = [
        event.model_copy(
            update={
                "payload": {
                    **event.payload,
                    "artifact_id": forged_clear_feedback_artifact.artifact_id,
                    "artifact_path": forged_clear_feedback_artifact.path,
                    "coverage_rejection_feedback": forged_clear_feedback,
                }
            }
        )
        if event.event_id == clear_context.event_id
        else event.model_copy(
            update={
                "payload": {
                    **event.payload,
                    "request_artifact_id": (
                        forged_clear_feedback_artifact.artifact_id
                    ),
                    "request_artifact_path": (
                        forged_clear_feedback_artifact.path
                    ),
                    "request_artifact_hash": (
                        forged_clear_feedback_artifact.content_hash
                    ),
                }
            }
        )
        if event.event_id == clear_model.event_id
        else event
        for event in events
    ]
    assert_qualifier_rejects(forged_clear_feedback_events)
    forged_clear_claim = {
        **clear_request_document["worker_claim"],
        "owner_id": "worker_forged_clear_context",
    }
    clear_request_document["worker_claim"] = forged_clear_claim
    forged_clear_request_artifact = resumed_runner.artifacts.put_json(
        clear_request_document
    )
    forged_clear_context = clear_context.model_copy(
        update={
            "payload": {
                **clear_context.payload,
                "artifact_id": forged_clear_request_artifact.artifact_id,
                "artifact_path": forged_clear_request_artifact.path,
                "worker_claim": forged_clear_claim,
            }
        }
    )
    clear_claim_tampered_events = [
        forged_clear_context
        if event.event_id == clear_context.event_id
        else event
        for event in events
    ]
    assert_qualifier_rejects(clear_claim_tampered_events)

    exact_read_call = next(
        event
        for event in events
        if event.type == EventType.TOOL_CALLED
        and event.correlation_id == exact_read.correlation_id
    )
    passed, details = _v11_coverage_rejection_recovery_evidence(
        events=[
            event
            for event in events
            if event.event_id != exact_read_call.event_id
        ],
        **qualifier_arguments,
    )
    assert passed is False, details
    assert details["failed_rejection_sequences"] == [failure.sequence]

    for recovery_outcome in (latest_exact_read, refreshed_diff):
        recovery_source_call = next(
            event
            for event in events
            if event.type == EventType.TOOL_CALLED
            and event.correlation_id == recovery_outcome.correlation_id
        )
        recovery_source_model = [
            event
            for event in events
            if event.type == EventType.MODEL_CALLED
            and event.sequence < recovery_source_call.sequence
        ][-1]
        recovery_response_document = json.loads(
            Path(
                recovery_source_model.payload["artifact_path"]
            ).read_text(encoding="utf-8")
        )
        recovery_response_document["tool_calls"] = [
            item
            for item in recovery_response_document["tool_calls"]
            if item["action_id"] != recovery_source_call.correlation_id
        ]
        forged_recovery_response = resumed_runner.artifacts.put_json(
            recovery_response_document
        )
        missing_recovery_model_call_events = [
            event.model_copy(
                update={
                    "payload": {
                        **event.payload,
                        "artifact_id": (
                            forged_recovery_response.artifact_id
                        ),
                        "artifact_path": forged_recovery_response.path,
                    }
                }
            )
            if event.event_id == recovery_source_model.event_id
            else event
            for event in events
        ]
        assert_runtime_rejects(missing_recovery_model_call_events)
        assert_qualifier_rejects(
            missing_recovery_model_call_events
        )

    refreshed_diff_call = next(
        event
        for event in events
        if event.type == EventType.TOOL_CALLED
        and event.correlation_id == refreshed_diff.correlation_id
    )
    retagged_diff_call_events = [
        event.model_copy(update={"correlation_id": "v11-retagged-diff-call"})
        if event.event_id == refreshed_diff_call.event_id
        else event
        for event in events
    ]
    passed, details = _v11_coverage_rejection_recovery_evidence(
        events=retagged_diff_call_events,
        **qualifier_arguments,
    )
    assert passed is False, details
    assert details["failed_rejection_sequences"] == [failure.sequence]

    passed, details = _v11_coverage_rejection_recovery_evidence(
        events=[
            event
            for event in events
            if event.event_id != source_get_diff_call.event_id
        ],
        **qualifier_arguments,
    )
    assert passed is False, details
    assert details["failed_rejection_sequences"] == [failure.sequence]

    passed, details = _v11_coverage_rejection_recovery_evidence(
        events=[
            event.model_copy(
                update={
                    "payload": {
                        **event.payload,
                        "artifact_id": (
                            forged_source_diff_artifact.artifact_id
                        ),
                        "artifact_path": forged_source_diff_artifact.path,
                        "result_artifact": (
                            forged_source_diff_artifact.model_dump(
                                mode="json"
                            )
                        ),
                    }
                }
            )
            if event.sequence == source_get_diff.sequence
            else event
            for event in events
        ],
        **qualifier_arguments,
    )
    assert passed is False, details
    assert details["failed_rejection_sequences"] == [failure.sequence]

    recovered_review_call = next(
        event
        for event in events
        if event.type == EventType.TOOL_CALLED
        and event.correlation_id == recovered_review.correlation_id
    )
    recovered_review_context = next(
        event
        for event in events
        if event.type == EventType.CONTEXT_BUILT
        and event.payload.get("artifact_id")
        == recovered_review_call.payload["request_artifact_id"]
    )
    recovered_review_model = next(
        event
        for event in events
        if event.type == EventType.MODEL_CALLED
        and recovered_review_context.sequence
        < event.sequence
        < recovered_review_call.sequence
    )
    clearing_response_document = json.loads(
        Path(recovered_review_model.payload["artifact_path"]).read_text(
            encoding="utf-8"
        )
    )
    clearing_response_document["tool_calls"] = []
    forged_clearing_response = resumed_runner.artifacts.put_json(
        clearing_response_document
    )
    missing_clearing_model_call_events = [
        event.model_copy(
            update={
                "payload": {
                    **event.payload,
                    "artifact_id": forged_clearing_response.artifact_id,
                    "artifact_path": forged_clearing_response.path,
                }
            }
        )
        if event.event_id == recovered_review_model.event_id
        else event
        for event in events
    ]
    assert_runtime_rejects(missing_clearing_model_call_events)
    assert_qualifier_rejects(missing_clearing_model_call_events)
    with pytest.raises(RecoveryError, match="correlated call"):
        _coverage_rejection_feedback_v11(
            [
                event
                for event in events
                if event.event_id != recovered_review_call.event_id
            ],
            worktree_diff_hash=(
                resumed_runner.state.latest_checkpoint(
                    manifest.run_id
                ).worktree_diff_hash
            ),
            artifact_store=resumed_runner.artifacts,
            public_review_contract=contract,
        )

    with pytest.raises(
        RecoveryError,
        match="review request context is ambiguous",
    ):
        _coverage_rejection_feedback_v11(
            [
                event
                for event in events
                if event.event_id != recovered_review_context.event_id
            ],
            worktree_diff_hash=(
                resumed_runner.state.latest_checkpoint(
                    manifest.run_id
                ).worktree_diff_hash
            ),
            artifact_store=resumed_runner.artifacts,
            public_review_contract=contract,
        )

    forged_feedback = {
        **feedback,
        "guidance": "self-consistent but forged recovery guidance",
    }
    forged_request_document = json.loads(
        Path(recovered_review_context.payload["artifact_path"]).read_text(
            encoding="utf-8"
        )
    )
    forged_rendered_payload = json.loads(
        forged_request_document["request_body"]["context"]
    )
    forged_rendered_payload["coverage_rejection_feedback"] = (
        forged_feedback
    )
    forged_rendered_context = json.dumps(
        forged_rendered_payload,
        indent=2,
        ensure_ascii=False,
        default=str,
    )
    forged_request_document["request_body"]["context"] = (
        forged_rendered_context
    )
    forged_request_document["context_build"][
        "coverage_rejection_feedback"
    ]["content_hash"] = sha256_text(
        json.dumps(
            forged_feedback,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    )
    forged_request_document["request_body_hash"] = sha256_text(
        json.dumps(
            forged_request_document["request_body"],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    )
    forged_request = resumed_runner.artifacts.put_json(
        forged_request_document
    )
    recovered_review_input = Artifact.model_validate(
        recovered_review_call.payload["input_artifact"]
    )
    forged_review_input_document = json.loads(
        resumed_runner.artifacts.read_bytes(
            recovered_review_input
        ).decode("utf-8")
    )
    forged_review_input_document["execution_context"][
        "request_artifact_id"
    ] = forged_request.artifact_id
    forged_review_input_document["execution_context"][
        "coverage_rejection_feedback"
    ] = forged_feedback
    forged_review_input = resumed_runner.artifacts.put_json(
        forged_review_input_document
    )
    forged_feedback_events = [
        event.model_copy(
            update={
                "payload": {
                    **event.payload,
                    "artifact_id": forged_request.artifact_id,
                    "artifact_path": forged_request.path,
                    "request_body_hash": forged_request_document[
                        "request_body_hash"
                    ],
                    "context_hash": sha256_text(
                        forged_rendered_context
                    ),
                    "coverage_rejection_feedback": (
                        forged_request_document["context_build"][
                            "coverage_rejection_feedback"
                        ]
                    ),
                }
            }
        )
        if event.event_id == recovered_review_context.event_id
        else event.model_copy(
            update={
                "payload": {
                    **event.payload,
                    "artifact_id": forged_review_input.artifact_id,
                    "artifact_path": forged_review_input.path,
                    "input_artifact": forged_review_input.model_dump(
                        mode="json"
                    ),
                    "request_artifact_id": forged_request.artifact_id,
                }
            }
        )
        if event.event_id == recovered_review_call.event_id
        else event
        for event in events
    ]
    with pytest.raises(
        RecoveryError,
        match="feedback-clearing review request binding is invalid",
    ):
        _coverage_rejection_feedback_v11(
            forged_feedback_events,
            worktree_diff_hash=(
                resumed_runner.state.latest_checkpoint(
                    manifest.run_id
                ).worktree_diff_hash
            ),
            artifact_store=resumed_runner.artifacts,
            public_review_contract=contract,
        )
    assert_qualifier_rejects(forged_feedback_events)

    partial_review_events = [
        event.model_copy(
            update={
                "payload": {
                    **event.payload,
                    "coverage_complete": False,
                    "unresolved_coverage_target_ids": [
                        contract.requirements[0].coverage_targets[
                            0
                        ].coverage_target_id
                    ],
                }
            }
        )
        if event.event_id == recovered_review.event_id
        else event
        for event in events
    ]
    with pytest.raises(
        RecoveryError,
        match="feedback-clearing review binding is invalid",
    ):
        _coverage_rejection_feedback_v11(
            partial_review_events,
            worktree_diff_hash=(
                resumed_runner.state.latest_checkpoint(
                    manifest.run_id
                ).worktree_diff_hash
            ),
            artifact_store=resumed_runner.artifacts,
            public_review_contract=contract,
        )

    for field in ("error_details", "result_artifact"):
        passed, details = _v11_coverage_rejection_recovery_evidence(
            events=_tampered_events(
                events,
                failure.sequence,
                field=field,
            ),
            **qualifier_arguments,
        )
        assert passed is False, details
        assert details["failed_rejection_sequences"] == [failure.sequence]

    passed, details = _v11_coverage_rejection_recovery_evidence(
        events=events,
        **{
            **qualifier_arguments,
            "worker_claims": worker_claims[:1],
        },
    )
    assert passed is False, details
    assert details["failed_rejection_sequences"] == [failure.sequence]

    owner_tampered_claims = copy.deepcopy(worker_claims)
    owner_tampered_claims[1]["owner_id"] = "worker_tampered_owner"
    passed, details = _v11_coverage_rejection_recovery_evidence(
        events=events,
        **{
            **qualifier_arguments,
            "worker_claims": owner_tampered_claims,
        },
    )
    assert passed is False, details
    assert details["failed_rejection_sequences"] == [failure.sequence]

    future_claims = [
        *worker_claims[:1],
        {
            **worker_claims[1],
            "claimed_at": "2099-01-01T00:00:00+00:00",
        },
    ]
    passed, details = _v11_coverage_rejection_recovery_evidence(
        events=events,
        **{
            **qualifier_arguments,
            "worker_claims": future_claims,
        },
    )
    assert passed is False, details
    assert details["failed_rejection_sequences"] == [failure.sequence]

    tampered_recovery_events = [
        event.model_copy(
            update={
                "payload": {
                    **event.payload,
                    "result_artifact": {
                        **event.payload["result_artifact"],
                        "content_hash": "sha256:" + ("0" * 64),
                    },
                }
            }
        )
        if event.sequence == exact_read.sequence
        else event
        for event in events
    ]
    passed, details = _v11_coverage_rejection_recovery_evidence(
        events=tampered_recovery_events,
        **qualifier_arguments,
    )
    assert passed is False, details
    assert details["failed_rejection_sequences"] == [failure.sequence]

    stale_diff_recovery_events = [
        event.model_copy(
            update={
                "payload": {
                    **event.payload,
                    "tool": "read_file",
                }
            }
        )
        if event.sequence == refreshed_diff.sequence
        else event
        for event in events
    ]
    passed, details = _v11_coverage_rejection_recovery_evidence(
        events=stale_diff_recovery_events,
        **qualifier_arguments,
    )
    assert passed is False, details
    assert details["failed_rejection_sequences"] == [failure.sequence]

    refreshed_diff_artifact = Artifact.model_validate(
        refreshed_diff.payload["result_artifact"]
    )
    refreshed_diff_document = json.loads(
        resumed_runner.artifacts.read_bytes(
            refreshed_diff_artifact
        ).decode("utf-8")
    )
    refreshed_diff_document["patch"] += "\n# forged diff bytes\n"
    forged_diff_artifact = resumed_runner.artifacts.put_json(
        refreshed_diff_document
    )
    forged_diff_events = [
        event.model_copy(
            update={
                "payload": {
                    **event.payload,
                    "artifact_id": forged_diff_artifact.artifact_id,
                    "artifact_path": forged_diff_artifact.path,
                    "result_artifact": forged_diff_artifact.model_dump(
                        mode="json"
                    ),
                }
            }
        )
        if event.sequence == refreshed_diff.sequence
        else event
        for event in events
    ]
    passed, details = _v11_coverage_rejection_recovery_evidence(
        events=forged_diff_events,
        **qualifier_arguments,
    )
    assert passed is False, details
    assert details["failed_rejection_sequences"] == [failure.sequence]

    active_context = next(
        event
        for event in context_events
        if event.payload.get("coverage_rejection_feedback", {}).get(
            "included"
        )
        is True
    )
    active_model = next(
        event
        for event in events
        if event.type == EventType.MODEL_CALLED
        and event.payload.get("request_artifact_id")
        == active_context.payload.get("artifact_id")
    )
    wrong_rehydrated_request_events = [
        event.model_copy(
            update={
                "payload": {
                    **event.payload,
                    "request_artifact_id": "art_v11_decoy_request",
                }
            }
        )
        if event.event_id == active_model.event_id
        else event
        for event in events
    ]
    assert_qualifier_rejects(wrong_rehydrated_request_events)
    claim_mirror_tampered_events = [
        event.model_copy(
            update={
                "payload": {
                    **event.payload,
                    "worker_claim": {
                        **event.payload["worker_claim"],
                        "owner_id": "worker_tampered_mirror",
                    },
                }
            }
        )
        if event.sequence == active_context.sequence
        else event
        for event in events
    ]
    passed, details = _v11_coverage_rejection_recovery_evidence(
        events=claim_mirror_tampered_events,
        **{
            **qualifier_arguments,
            "context_events": [
                event
                for event in claim_mirror_tampered_events
                if event.type == EventType.CONTEXT_BUILT
            ],
        },
    )
    assert passed is False, details
    assert details["failed_rejection_sequences"] == [failure.sequence]

    active_request_document = json.loads(
        Path(active_context.payload["artifact_path"]).read_text(
            encoding="utf-8"
        )
    )
    forged_active_build_document = copy.deepcopy(active_request_document)
    forged_active_build_document["context_build"][
        "coverage_rejection_feedback"
    ]["source_through_sequence"] -= 1
    forged_active_build = forged_active_build_document[
        "context_build"
    ]["coverage_rejection_feedback"]
    forged_active_build_artifact = resumed_runner.artifacts.put_json(
        forged_active_build_document
    )
    forged_active_build_events = [
        event.model_copy(
            update={
                "payload": {
                    **event.payload,
                    "artifact_id": forged_active_build_artifact.artifact_id,
                    "artifact_path": forged_active_build_artifact.path,
                    "coverage_rejection_feedback": forged_active_build,
                }
            }
        )
        if event.event_id == active_context.event_id
        else event.model_copy(
            update={
                "payload": {
                    **event.payload,
                    "request_artifact_id": (
                        forged_active_build_artifact.artifact_id
                    ),
                    "request_artifact_path": (
                        forged_active_build_artifact.path
                    ),
                    "request_artifact_hash": (
                        forged_active_build_artifact.content_hash
                    ),
                }
            }
        )
        if event.event_id == active_model.event_id
        else event
        for event in events
    ]
    assert_qualifier_rejects(forged_active_build_events)
    active_request_document["worker_claim"]["owner_id"] = (
        "worker_tampered_request"
    )
    tampered_request_artifact = resumed_runner.artifacts.put_json(
        active_request_document
    )
    request_claim_tampered_events = [
        event.model_copy(
            update={
                "payload": {
                    **event.payload,
                    "artifact_id": tampered_request_artifact.artifact_id,
                    "artifact_path": tampered_request_artifact.path,
                }
            }
        )
        if event.sequence == active_context.sequence
        else event
        for event in events
    ]
    passed, details = _v11_coverage_rejection_recovery_evidence(
        events=request_claim_tampered_events,
        **{
            **qualifier_arguments,
            "context_events": [
                event
                for event in request_claim_tampered_events
                if event.type == EventType.CONTEXT_BUILT
            ],
        },
    )
    assert passed is False, details
    assert details["failed_rejection_sequences"] == [failure.sequence]

    feedback_tampered_events = [
        event.model_copy(
            update={
                "payload": {
                    **event.payload,
                    "coverage_rejection_feedback": {
                        **event.payload["coverage_rejection_feedback"],
                        "content_hash": "sha256:" + ("0" * 64),
                    },
                }
            }
        )
        if event.sequence == active_context.sequence
        else event
        for event in events
    ]
    passed, details = _v11_coverage_rejection_recovery_evidence(
        events=feedback_tampered_events,
        **{
            **qualifier_arguments,
            "context_events": [
                event
                for event in feedback_tampered_events
                if event.type == EventType.CONTEXT_BUILT
            ],
        },
    )
    assert passed is False, details
    assert details["failed_rejection_sequences"] == [failure.sequence]

    duplicate_mutation = next(
        event for event in events if event.type == EventType.PATCH_APPLIED
    ).model_copy(
        update={
            "event_id": "evt_v11_duplicate_mutation",
            "sequence": events[-1].sequence + 1,
            "timestamp": utc_now(),
            "correlation_id": "v11-duplicate-mutation",
        }
    )
    passed, details = _v11_coverage_rejection_recovery_evidence(
        events=[*events, duplicate_mutation],
        **qualifier_arguments,
    )
    assert passed is False, details
    assert details["patch_applied_sequences"] == [
        next(
            event.sequence
            for event in events
            if event.type == EventType.PATCH_APPLIED
        ),
        duplicate_mutation.sequence,
    ]
