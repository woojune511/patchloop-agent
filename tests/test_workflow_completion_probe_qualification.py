from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from patchloop.agent.context import BuiltContext
from patchloop.agent.runner import AgentRunner
from patchloop.contracts import (
    DatasetRole,
    EventType,
    ExperimentPurpose,
    ExperimentRunContext,
    RunManifest,
    RunOutcomeKind,
    RunResult,
    RunStatus,
    Usage,
    Verdicts,
)
from patchloop.errors import ModelGenerationBudgetError
from patchloop.evals import runner as eval_runner
from patchloop.evals.qualification import qualify_run
from patchloop.runtime import build_manifest
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_text

TASK_DIR = Path(eval_runner.WORKFLOW_COMPLETION_PROBE_TASK).parent
HASH = "sha256:" + "a" * 64


def _exact_manifest(run_id: str) -> RunManifest:
    package = load_task_package(TASK_DIR)
    assert package.environment is not None
    return build_manifest(
        package,
        run_id=run_id,
        provider="openai",
        model_id=eval_runner.GPT54_MINI_PILOT_MODEL_ID,
        sandbox_backend="docker",
        budget=eval_runner.GPT54_MINI_WORKFLOW_COMPLETION_PROBE_BUDGET,
        transport_max_retries=0,
        max_output_tokens=25_000,
        input_price_per_million_usd=0.75,
        cached_input_price_per_million_usd=0.075,
        output_price_per_million_usd=4.5,
        agent_image_digest=package.environment.image_digest,
        evaluator_image_digest=package.environment.image_digest,
        experiment_context=ExperimentRunContext(
            experiment_id=(
                eval_runner.WORKFLOW_COMPLETION_PROBE_EXPERIMENT_ID
            ),
            purpose=ExperimentPurpose.WORKFLOW_COMPLETION_PROBE,
            suite_hash=HASH,
            execution_hash="sha256:" + "b" * 64,
            dataset_manifest_hash="sha256:" + "c" * 64,
            dataset_role=DatasetRole.MEMORY_DEVELOPMENT,
            schedule_seed=20260723,
            schedule_order=1,
            schedule_row_id="sha256:" + "d" * 64,
            repetition=1,
        ),
    )


def _minimal_probe_trace(
    root: Path,
    *,
    run_id: str,
    runtime_policy: str = eval_runner.WORKFLOW_COMPLETION_CALL_GUARD_POLICY,
    wall_duration_ms: int = 0,
) -> tuple[AgentRunner, RunManifest, BuiltContext, Any, str]:
    """Create only the evidence needed by the call-guard qualification check."""

    manifest = _exact_manifest(run_id)
    runner = AgentRunner(root)
    runner.state.create_run(manifest)
    runner.state.claim_run_for_worker(
        run_id,
        owner_id="worker_workflow_qualification",
        owner_pid=1234,
        owner_hostname="workflow-qualification-host",
        allowed_statuses={RunStatus.CREATED},
        manifest=manifest,
    )

    system_prompt, tools = AgentRunner._runtime_contract(manifest)
    runtime_document = (
        AgentRunner._generic_baseline_runtime_evidence_document(
            manifest=manifest,
            system_prompt=system_prompt,
            tool_schemas=tools,
        )
    )
    assert runtime_document is not None
    runtime_document["call_guard_policy"] = runtime_policy
    runtime_artifact = runner.artifacts.put_json(runtime_document)
    runner.state.append_event(
        run_id,
        EventType.RUN_STARTED,
        actor="runner",
        payload={
            "task_id": manifest.task_id,
            "artifact_role": "runtime-contract",
            "artifact_id": runtime_artifact.artifact_id,
            "artifact_path": runtime_artifact.path,
            "runtime_contract_artifact": runtime_artifact.model_dump(
                mode="json"
            ),
        },
    )
    if wall_duration_ms:
        runner.state.append_event(
            run_id,
            EventType.TOOL_SUCCEEDED,
            actor="tool-gateway",
            payload={"duration_ms": wall_duration_ms},
        )

    rendered = json.dumps({"rejected_mutation_retry": None})
    request_body = {
        "model": manifest.model.model_id,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": rendered},
        ],
        "tools": tools,
        "store": False,
        "reasoning": {"effort": manifest.model.reasoning_effort},
        "service_tier": manifest.model.service_tier,
        "max_output_tokens": manifest.model.max_output_tokens,
        "truncation": "disabled",
    }
    request_hash = sha256_text(canonical_json(request_body))
    retry_evidence = {"included": False, "truncated": False}
    request_artifact = runner.artifacts.put_json(
        {
            "schema_version": "model-request-evidence-v1",
            "provider": "openai",
            "request_body": request_body,
            "request_body_hash": request_hash,
            "context_build": {
                "rejected_mutation_retry": retry_evidence,
            },
        }
    )
    runner.state.append_event(
        run_id,
        EventType.CONTEXT_BUILT,
        actor="context-builder",
        payload={
            "artifact_id": request_artifact.artifact_id,
            "artifact_path": request_artifact.path,
            "request_body_hash": request_hash,
            "context_hash": sha256_text(rendered),
            "investigation_tail_block_reasons": [],
        },
    )
    built_context = BuiltContext(
        rendered=rendered,
        content_hash=sha256_text(rendered),
        evidence={"rejected_mutation_retry": retry_evidence},
    )
    return runner, manifest, built_context, request_artifact, request_hash


def _qualification_check(root: Path, run_id: str, check_id: str) -> dict:
    qualification = qualify_run(
        run_id,
        task_dir=TASK_DIR,
        root=root,
        persist=False,
    )
    return next(
        check
        for check in qualification["checks"]
        if check["check_id"] == check_id
    )


def test_disabled_call_guard_contract_accepts_exact_minimal_evidence(
    tmp_path: Path,
) -> None:
    _minimal_probe_trace(tmp_path, run_id="run_workflow_guard_valid")

    check = _qualification_check(
        tmp_path,
        "run_workflow_guard_valid",
        "disabled_call_guard_contract",
    )

    assert check["passed"] is True
    assert check["details"]["runtime_contract_valid"] is True
    assert check["details"]["context_tail_failure_sequences"] == []
    assert check["details"]["admission_tail_failure_sequences"] == []


@pytest.mark.parametrize(
    "reason_code",
    ["model_call_budget_exhausted", "tool_call_budget_exhausted"],
)
def test_disabled_call_guard_contract_rejects_forged_call_budget_block(
    tmp_path: Path,
    reason_code: str,
) -> None:
    runner, manifest, _, _, _ = _minimal_probe_trace(
        tmp_path,
        run_id=f"run_workflow_forged_{reason_code}",
    )
    blocked = runner.state.append_event(
        manifest.run_id,
        EventType.MODEL_GENERATION_BLOCKED,
        actor="budget-guard",
        payload={"reason_code": reason_code},
    )

    check = _qualification_check(
        tmp_path,
        manifest.run_id,
        "disabled_call_guard_contract",
    )

    assert check["passed"] is False
    assert check["details"]["forbidden_generation_block_sequences"] == [
        blocked.sequence
    ]


def test_disabled_call_guard_contract_rejects_call_tail_reason(
    tmp_path: Path,
) -> None:
    runner, manifest, _, _, _ = _minimal_probe_trace(
        tmp_path,
        run_id="run_workflow_forged_call_tail",
    )
    blocked = runner.state.append_event(
        manifest.run_id,
        EventType.TOOL_ADMISSION_BLOCKED,
        actor="tool-gateway",
        payload={
            "reason_codes": ["model_tail_reserved"],
            "max_model_calls": None,
            "max_tool_calls": None,
            "error_details": {
                "remaining_model_calls": None,
                "remaining_tool_calls": None,
            },
        },
    )

    check = _qualification_check(
        tmp_path,
        manifest.run_id,
        "disabled_call_guard_contract",
    )

    assert check["passed"] is False
    assert check["details"]["forbidden_tail_block_sequences"] == [
        blocked.sequence
    ]


def test_disabled_call_guard_contract_rejects_non_null_admission_remaining(
    tmp_path: Path,
) -> None:
    runner, manifest, _, _, _ = _minimal_probe_trace(
        tmp_path,
        run_id="run_workflow_non_null_admission_remaining",
    )
    blocked = runner.state.append_event(
        manifest.run_id,
        EventType.TOOL_ADMISSION_BLOCKED,
        actor="tool-gateway",
        payload={
            "reason_codes": ["token_tail_reserved"],
            "max_model_calls": None,
            "max_tool_calls": None,
            "error_details": {
                "remaining_model_calls": 1,
                "remaining_tool_calls": None,
                "tail_policy": {
                    "remaining_budget": {
                        "model_calls": 1,
                        "model_calls_after_next_generation": 0,
                        "tool_calls": None,
                    }
                },
            },
        },
    )

    check = _qualification_check(
        tmp_path,
        manifest.run_id,
        "disabled_call_guard_contract",
    )

    assert check["passed"] is False
    assert check["details"]["admission_tail_failure_sequences"] == [
        blocked.sequence
    ]


def test_disabled_call_guard_contract_rejects_runtime_policy_drift(
    tmp_path: Path,
) -> None:
    _minimal_probe_trace(
        tmp_path,
        run_id="run_workflow_runtime_policy_drift",
        runtime_policy="finite-call-guard-v1",
    )

    check = _qualification_check(
        tmp_path,
        "run_workflow_runtime_policy_drift",
        "disabled_call_guard_contract",
    )

    assert check["passed"] is False
    assert check["details"]["runtime_contract_valid"] is False


@pytest.mark.parametrize(
    ("reason_code", "schema_version"),
    [
        ("wall_clock_budget_exhausted", "model-generation-block-v3"),
        ("exact_request_budget_exceeded", "model-generation-block-v1"),
    ],
)
def test_retained_terminal_budget_blocks_preserve_schema_and_result_binding(
    tmp_path: Path,
    reason_code: str,
    schema_version: str,
) -> None:
    wall_duration_ms = 7_200_000 if reason_code.startswith("wall") else 0
    runner, manifest, built_context, request_artifact, request_hash = (
        _minimal_probe_trace(
            tmp_path,
            run_id=f"run_workflow_retained_{schema_version}",
            wall_duration_ms=wall_duration_ms,
        )
    )
    usage = Usage(wall_clock_ms=wall_duration_ms)
    block_arguments: dict[str, Any] = {}
    if reason_code == "exact_request_budget_exceeded":
        block_arguments = {
            "requested_input_tokens": 2_975_001,
            "remaining_tokens": 3_000_000,
            "input_token_count_calls": 1,
        }

    with pytest.raises(ModelGenerationBudgetError) as raised:
        runner._block_model_generation(
            manifest=manifest,
            built_context=built_context,
            request_artifact=request_artifact,
            request_body_hash=request_hash,
            reason_code=reason_code,
            usage=usage,
            **block_arguments,
        )
    error = raised.value
    assert error.details["schema_version"] == schema_version

    result_usage = usage.model_copy(
        update={
            "input_token_count_calls": block_arguments.get(
                "input_token_count_calls",
                0,
            )
        }
    )
    terminal_error = {
        "type": "ModelGenerationBudgetError",
        "code": error.code,
        "message": str(error),
        "details": error.details,
    }
    result = RunResult(
        run_id=manifest.run_id,
        agent_submission_status="failed",
        evaluation_status="not_run",
        scope_compliant_success=False,
        official=False,
        verdicts=Verdicts(),
        usage=result_usage,
        outcome_kind=RunOutcomeKind.AGENT_FAILURE,
        terminal_error=terminal_error,
    )
    runner.state.finalize_run(
        manifest.run_id,
        status=RunStatus.FAILED,
        result=result,
        event_type=EventType.RUN_FAILED,
        actor="runner",
        payload={
            "error_type": "ModelGenerationBudgetError",
            "error_code": error.code,
            "error_details": error.details,
            "message": str(error),
        },
    )
    result_path = (
        tmp_path
        / "artifacts"
        / "runs"
        / manifest.run_id
        / "result.json"
    )
    result_path.parent.mkdir(parents=True)
    result_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

    prompt_check = _qualification_check(
        tmp_path,
        manifest.run_id,
        "prompt_token_integrity",
    )
    terminal_check = _qualification_check(
        tmp_path,
        manifest.run_id,
        "terminal_result_integrity",
    )
    call_guard_check = _qualification_check(
        tmp_path,
        manifest.run_id,
        "disabled_call_guard_contract",
    )

    assert prompt_check["details"]["terminal_generation_block_valid"] is True
    assert prompt_check["details"][
        "terminal_generation_block_schema_version"
    ] == schema_version
    assert terminal_check["passed"] is True
    assert terminal_check["details"][
        "model_generation_block_binding_valid"
    ] is True
    assert call_guard_check["passed"] is True
