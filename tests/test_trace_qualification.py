from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from patchloop.agent.runner import AgentRunner
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import (
    Artifact,
    Budget,
    Checkpoint,
    DatasetRole,
    EventType,
    ExperimentPurpose,
    ExperimentRunContext,
    FaultSpec,
    Phase,
    RunOutcomeKind,
    RunResult,
    RunStatus,
    Usage,
    Verdicts,
    VerdictState,
    VerifierResult,
)
from patchloop.dataset import load_dataset_manifest
from patchloop.errors import ContractError
from patchloop.evals import qualification as qualification_module
from patchloop.evals.failures import classify_failure
from patchloop.evals.qualification import (
    _private_leak_tokens,
    calculate_source_evidence_hash,
    load_trace_qualification,
    qualify_run,
)
from patchloop.evals.runner import (
    MEMORY_DEVELOPMENT_TASKS,
    ExperimentSuite,
    _execution_hash,
    _suite_payload,
)
from patchloop.evals.runner import (
    PILOT_TASK as PILOT_TASK_PATH,
)
from patchloop.memory.store import review_failure
from patchloop.runtime import build_manifest
from patchloop.state import StateStore
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_text, utc_now

MEMORY_TASK = Path("tasks/dev-train/loguru-invalid-format-feedback")
PILOT_TASK = Path("tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes")
V2_TASK = Path("tasks/same-repo-heldout/pyfakefs-file-wrapper-io-capabilities")
HASH = "sha256:" + ("a" * 64)
PATCH_TEXT = (
    "diff --git a/example.py b/example.py\n"
    "--- a/example.py\n"
    "+++ b/example.py\n"
    "@@ -1 +1 @@\n"
    "-before\n"
    "+after\n"
)
DIFF_HASH = sha256_bytes(PATCH_TEXT.encode("utf-8"))


def _execution_plan_path_for_test(root: Path, execution_hash: str) -> Path:
    return root / "experiments" / "plans" / f"{execution_hash.removeprefix('sha256:')}.json"


def _suite_for_manifest(manifest, *, dataset_hash: str) -> ExperimentSuite:
    assert manifest.experiment is not None
    purpose = manifest.experiment.purpose
    if purpose == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY:
        tasks = sorted(MEMORY_DEVELOPMENT_TASKS)
        conditions = ["no_memory"]
        repetitions = 2
        cost_limit = 20
        embedding_revision = "PIN_AT_FREEZE"
        model_id = manifest.model.model_id
        budget = manifest.budget
        max_output_tokens = manifest.model.max_output_tokens
        diagnostic = None
    elif purpose == ExperimentPurpose.DEVELOPMENT_VALIDATION_MODEL_CANDIDATE_PILOT:
        tasks = [PILOT_TASK_PATH]
        conditions = ["no_memory"]
        repetitions = 1
        cost_limit = 2
        embedding_revision = "PIN_AT_FREEZE"
        model_id = "gpt-5.4-mini-2026-03-17"
        diagnostic_profile_by_total_budget = {
            120_000: "d037-rejected-patch-retry-v2",
            200_000: "d037-rejected-patch-retry-v3",
        }
        diagnostic_profile = (
            "d037-rejected-patch-retry-v4"
            if manifest.fault.type
            == "controlled-reject-first-prepared-patch"
            else diagnostic_profile_by_total_budget.get(
                manifest.budget.max_total_tokens
            )
        )
        if diagnostic_profile is not None:
            budget = Budget(
                max_total_tokens=manifest.budget.max_total_tokens
            )
            max_output_tokens = 25_000
            diagnostic = {
                "schema_version": "experiment-diagnostic-v1",
                "profile": diagnostic_profile,
                "required_trace_features": ["rejected_patch_retry_context"],
            }
        elif manifest.model.max_output_tokens == 25_000:
            # Preserve an invalid partial contract for negative qualification
            # tests rather than silently normalizing it to a valid profile.
            budget = Budget(max_total_tokens=120_000)
            max_output_tokens = 25_000
            diagnostic = {
                "schema_version": "experiment-diagnostic-v1",
                "profile": "d037-rejected-patch-retry-v2",
                "required_trace_features": ["rejected_patch_retry_context"],
            }
        else:
            budget = Budget(max_total_tokens=90_000)
            max_output_tokens = 4096
            diagnostic = None
    elif purpose == ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT:
        tasks = [PILOT_TASK_PATH]
        conditions = ["no_memory"]
        repetitions = 1
        cost_limit = 2
        embedding_revision = "PIN_AT_FREEZE"
        model_id = manifest.model.model_id
        budget = manifest.budget
        max_output_tokens = manifest.model.max_output_tokens
        diagnostic = None
    else:
        tasks = [f"qualification-core-task-{index}" for index in range(12)]
        conditions = [
            "no_memory",
            "raw_trace",
            "structured",
            "selective_structured",
        ]
        repetitions = 2
        cost_limit = 150
        embedding_revision = "test-revision"
        model_id = manifest.model.model_id
        budget = manifest.budget
        max_output_tokens = manifest.model.max_output_tokens
        diagnostic = None

    return ExperimentSuite.model_validate(
        {
            "schema_version": "experiment-v2",
            "experiment_id": manifest.experiment.experiment_id,
            "purpose": purpose.value,
            "tasks": tasks,
            "conditions": conditions,
            "repetitions": repetitions,
            "model": "openai",
            "model_id": model_id,
            "reasoning_effort": "medium",
            "reasoning_mode": "standard",
            "service_tier": "default",
            "max_output_tokens": max_output_tokens,
            "budget": budget.model_dump(mode="json"),
            "seed": manifest.experiment.schedule_seed,
            "diagnostic": diagnostic,
            "live_cost_approved": False,
            "approved_execution_hash": None,
            "pilot_run_id": None,
            "estimated_cost_usd": 0,
            "cost_limit_usd": cost_limit,
            "pricing_verified_at": None,
            "pricing_source_url": None,
            "input_price_per_million_usd": (
                manifest.model.input_price_per_million_usd
            ),
            "cached_input_price_per_million_usd": (
                manifest.model.cached_input_price_per_million_usd
            ),
            "cache_write_input_price_per_million_usd": (
                manifest.model.cache_write_input_price_per_million_usd
            ),
            "output_price_per_million_usd": (
                manifest.model.output_price_per_million_usd
            ),
            "retrieval_threshold": 0.72,
            "memory_token_budget": manifest.memory.max_context_tokens,
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "embedding_revision": embedding_revision,
            "dataset_manifest_hash": dataset_hash,
        }
    )


def _write_execution_plan(
    root: Path,
    *,
    manifest,
    dataset_hash: str,
    suite_overrides: dict[str, object] | None = None,
) -> Path:
    assert manifest.experiment is not None
    experiment = manifest.experiment
    suite = _suite_for_manifest(manifest, dataset_hash=dataset_hash)
    suite_payload = _suite_payload(suite)
    if suite_overrides is not None:
        suite_payload.update(suite_overrides)
    experiment.suite_hash = sha256_text(canonical_json(suite_payload))
    dataset = {"manifest_hash": dataset_hash}
    tasks = [
        {
            "task_id": manifest.task_id,
            "task_version": manifest.task_version,
            "public_spec_hash": manifest.public_spec_hash,
            "private_spec_hash": manifest.private_spec_hash,
            "base_commit": manifest.base_commit,
            "evaluator_image_digest": manifest.evaluator_image_digest,
        }
    ]
    schedule = [
        {
            "order": experiment.schedule_order,
            "schedule_row_id": experiment.schedule_row_id,
            "task_id": manifest.task_id,
            "dataset_role": (
                experiment.dataset_role.value
                if experiment.dataset_role is not None
                else None
            ),
            "condition": manifest.memory.condition.value,
            "repetition": experiment.repetition,
        }
    ]
    schedule_hash = sha256_text(canonical_json(schedule))
    environment = {
        "git": {"commit": manifest.harness_git_commit},
        "docker": {"images": []},
        "openai_sdk": {
            "installed": True,
            "version": manifest.model.provider_sdk_version,
        },
    }
    pilot_qualification: dict[str, object] = {}
    experiment.execution_hash = _execution_hash(
        suite,
        dataset=dataset,
        task_rows=tasks,
        schedule_hash=schedule_hash,
        git_state=environment["git"],
        docker_state=environment["docker"],
        openai_sdk=environment["openai_sdk"],
        pilot_qualification=pilot_qualification,
    )
    payload = {
        "schema_version": "experiment-execution-plan-v1",
        "experiment_id": experiment.experiment_id,
        "purpose": experiment.purpose.value,
        "suite_hash": experiment.suite_hash,
        "execution_hash": experiment.execution_hash,
        "schedule_hash": schedule_hash,
        "expected_runs": len(schedule),
        "suite": suite_payload,
        "dataset": dataset,
        "tasks": tasks,
        "schedule": schedule,
        "environment": environment,
        "approval": {
            "invocation_approve_live_cost": True,
            "invocation_approved_execution_hash": experiment.execution_hash,
            "matches_execution_hash": True,
        },
        "pilot_qualification": pilot_qualification,
        "blockers": [],
        "ready": True,
    }
    path = _execution_plan_path_for_test(root, experiment.execution_hash)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _result(run_id: str, *, resolved: bool, hidden_check_id: str) -> RunResult:
    verifier = VerifierResult(
        verifier_result_id="vr_test",
        run_id=run_id,
        check_type="hidden",
        check_id=hidden_check_id,
        state=VerdictState.PASS if resolved else VerdictState.FAIL,
        duration_ms=1,
    )
    return RunResult(
        run_id=run_id,
        agent_submission_status="completed",
        evaluation_status="completed",
        scope_compliant_success=resolved,
        official=True,
        verdicts=Verdicts(
            hidden_tests=VerdictState.PASS if resolved else VerdictState.FAIL,
            regression_tests=VerdictState.PASS,
            scope_policy=VerdictState.PASS,
            safety_policy=VerdictState.PASS,
        ),
        usage=Usage(model_calls=1, tool_calls=1),
        submitted_patch_artifact_id="art_patch",
        verifier_results=[verifier],
        outcome_kind=(RunOutcomeKind.RESOLVED if resolved else RunOutcomeKind.TASK_FAILURE),
    )


def _terminal_trace(
    tmp_path: Path,
    *,
    task_dir: Path = MEMORY_TASK,
    purpose: ExperimentPurpose = ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY,
    role: DatasetRole = DatasetRole.MEMORY_DEVELOPMENT,
    resolved: bool = False,
    agent_failure: bool = False,
    context_text: str = "public task context",
    write_execution_plan: bool = True,
    prompt_telemetry: bool = True,
    prompt_mismatch: bool = False,
    model_id: str = "gpt-5.4-mini-2026-03-17",
    budget: Budget | None = None,
    max_output_tokens: int | None = None,
    malformed_lifecycle: bool = False,
    complete_review_context: bool = True,
    actual_review_context: bool = True,
    include_mutation: bool = True,
    include_visible_checks: bool = True,
    visible_checks_after_get_diff: bool = False,
    checkpoint_diff_hash: str = DIFF_HASH,
    legacy_contract: bool = False,
    rejected_legacy_submission: bool = False,
    unpaired_submission_attempt: bool = False,
    checkpoint_event_overrides: dict[str, object] | None = None,
    duplicate_checkpoint_event: bool = False,
    include_apply_replay: bool = False,
    include_rejected_mutation: bool = False,
    rejected_retry_context: str | None = None,
    stale_rejected_retry_context: bool = False,
    force_v3_contract: bool = False,
    fault: FaultSpec | None = None,
    controlled_rejection: bool = False,
    controlled_rejection_interleaved: bool = False,
    controlled_rejection_details_overrides: dict[str, object] | None = None,
    execution_plan_suite_overrides: dict[str, object] | None = None,
    counter_generation_block_reason: str | None = None,
) -> tuple[str, RunResult, str]:
    package = load_task_package(task_dir)
    _, dataset_hash, _ = load_dataset_manifest()
    outcome_label = "agent" if agent_failure else ("resolved" if resolved else "failure")
    run_id = f"run_qualification_{outcome_label}"
    effective_budget = budget
    if effective_budget is None:
        effective_budget = (
            Budget(max_model_calls=21, max_total_tokens=200_000)
            if model_id == "gpt-5.4-mini-2026-03-17"
            else Budget()
        )
    effective_max_output_tokens = max_output_tokens
    if effective_max_output_tokens is None:
        effective_max_output_tokens = (
            4096
            if (
                model_id == "gpt-5.4-mini-2026-03-17"
                and effective_budget.max_total_tokens == 90_000
            )
            else (
                25_000
                if model_id == "gpt-5.4-mini-2026-03-17"
                else 4096
            )
        )
    manifest = build_manifest(
        package,
        run_id=run_id,
        provider="openai",
        model_id=model_id,
        sandbox_backend="docker",
        budget=effective_budget,
        fault=fault,
        max_output_tokens=effective_max_output_tokens,
        agent_image_digest=(
            package.environment.image_digest if package.environment is not None else None
        ),
        evaluator_image_digest=(
            package.environment.image_digest if package.environment is not None else None
        ),
    )
    if legacy_contract:
        manifest.tool_schema_version = "v1"
        manifest.context_policy_version = "v1"
    elif (
        rejected_retry_context is not None
        or force_v3_contract
        or controlled_rejection
        or counter_generation_block_reason is not None
    ):
        manifest.context_policy_version = "phase-evidence-v3"
    else:
        # This fixture primarily exercises the immutable v2 qualification
        # contract. v3 is opted into explicitly by the retry-context cases.
        manifest.context_policy_version = "phase-evidence-v2"
    manifest.experiment = ExperimentRunContext(
        experiment_id="qualification-test",
        purpose=purpose,
        suite_hash=HASH,
        execution_hash=HASH,
        dataset_manifest_hash=dataset_hash,
        dataset_role=role,
        schedule_seed=20260723,
        schedule_order=1,
        schedule_row_id=HASH,
        repetition=1,
    )
    if write_execution_plan:
        _write_execution_plan(
            tmp_path,
            manifest=manifest,
            dataset_hash=dataset_hash,
            suite_overrides=execution_plan_suite_overrides,
        )
    state = StateStore(tmp_path / "state.sqlite3")
    state.create_run(manifest)
    state.claim_run_for_worker(
        run_id,
        owner_id="worker_qualification",
        owner_pid=1234,
        owner_hostname="qualification-host",
        allowed_statuses={RunStatus.CREATED},
        manifest=manifest,
    )
    artifacts = ArtifactStore(tmp_path / "artifacts")
    runtime_contract = artifacts.put_text("public runtime contract")
    submitted_patch = artifacts.put_text(PATCH_TEXT, "text/x-diff")
    initial_model = artifacts.put_text("public model response: get_diff")
    get_diff_payload = {
        "patch": PATCH_TEXT,
        "patch_hash": DIFF_HASH,
        "worktree_diff_hash": DIFF_HASH,
        "changed_files": ["example.py"],
        "added_lines": 1,
        "deleted_lines": 0,
    }
    get_diff_result = artifacts.put_json(get_diff_payload)
    review_model = artifacts.put_text("public model response: finish_task")
    last_retry_payload: dict[str, object] | None = None

    def request_artifact(
        rendered_context: str,
        *,
        tool_results: list[dict] | None = None,
        runtime_contract: bool = False,
    ):
        if runtime_contract:
            system_prompt, tools = AgentRunner._runtime_contract(manifest)
            request_body = {
                "model": model_id,
                "input": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": rendered_context},
                ],
                "tools": tools,
                "store": False,
                "reasoning": {
                    "effort": manifest.model.reasoning_effort,
                },
                "service_tier": manifest.model.service_tier,
                "max_output_tokens": manifest.model.max_output_tokens,
                "truncation": "disabled",
            }
        else:
            request_body = {
                "model": model_id,
                "input": [
                    {"role": "system", "content": "public system prompt"},
                    {"role": "user", "content": rendered_context},
                ],
            }
        context_build = {"tool_results": tool_results or []}
        if runtime_contract:
            context_build["rejected_mutation_retry"] = {
                "included": False,
                "truncated": False,
            }
        request_hash = sha256_text(canonical_json(request_body))
        artifact = artifacts.put_json(
            {
                "schema_version": "model-request-evidence-v1",
                "request_body": request_body,
                "request_body_hash": request_hash,
                "context_build": context_build,
            }
        )
        return artifact, request_hash

    initial_rendered_context = json.dumps(
        {
            "public_task": package.public.model_dump(mode="json"),
            "task_context": context_text,
            "recent_events": [],
        },
        ensure_ascii=False,
        default=str,
    )
    initial_context, initial_request_hash = request_artifact(initial_rendered_context)
    state.append_event(
        run_id,
        EventType.RUN_STARTED,
        actor="runner",
        payload={
            "artifact_id": runtime_contract.artifact_id,
            "artifact_path": runtime_contract.path,
        },
    )
    state.append_event(
        run_id,
        EventType.CONTEXT_BUILT,
        actor="context-builder",
        payload={
            "artifact_id": initial_context.artifact_id,
            "artifact_path": initial_context.path,
            "request_body_hash": initial_request_hash,
            "context_hash": sha256_text(initial_rendered_context),
        },
    )

    def model_payload(
        model_artifact,
        request_artifact,
        *,
        mismatch: bool = False,
        request_hash: str,
    ) -> dict:
        payload = {
            "artifact_id": model_artifact.artifact_id,
            "artifact_path": model_artifact.path,
            "input_tokens": 0,
            "cached_input_tokens": 0,
            "cache_write_input_tokens": 0,
            "output_tokens": 0,
            "duration_ms": 0,
            "request_artifact_id": request_artifact.artifact_id,
            "request_artifact_path": request_artifact.path,
            "request_body_hash": request_hash,
        }
        if prompt_telemetry:
            payload.update(
                {
                    "prompt_telemetry_version": "prompt-token-integrity-v1",
                    "requested_input_tokens": 1 if mismatch else 0,
                    "input_token_count_match": not mismatch,
                    "input_token_count_calls": 1,
                    "reasoning_output_tokens": 0,
                    "total_tokens": 0,
                    "total_token_count_match": True,
                    "response_status": "completed",
                    "response_truncation": "disabled",
                    "response_incomplete_reason": None,
                    "response_model": model_id,
                }
            )
        return payload

    state.append_event(
        run_id,
        EventType.MODEL_CALLED,
        actor="model-adapter",
        payload=model_payload(
            initial_model,
            initial_context,
            mismatch=prompt_mismatch,
            request_hash=initial_request_hash,
        ),
    )

    def append_visible_checks() -> None:
        if legacy_contract or not include_visible_checks:
            return
        for offset, check in enumerate(package.public.visible_checks):
            correlation_id = f"qualification-check-{offset}"
            state.append_event(
                run_id,
                EventType.TOOL_CALLED,
                actor="agent",
                correlation_id=correlation_id,
                payload={"tool": "run_check"},
            )
            state.append_event(
                run_id,
                EventType.TOOL_SUCCEEDED,
                actor="tool-gateway",
                correlation_id=correlation_id,
                payload={
                    "tool": "run_check",
                    "status": "succeeded",
                    "check_id": check.id,
                    "passed": True,
                    "worktree_diff_hash": DIFF_HASH,
                    "duration_ms": 0,
                },
            )

    if not legacy_contract and include_mutation:
        patch_input_hash = sha256_text(
            canonical_json(
                {
                    "tool": "apply_patch",
                    "input": {"patch": PATCH_TEXT},
                }
            )
        )
        preimage = artifacts.put_bytes(b"before\n")
        postimage = artifacts.put_bytes(b"after\n")
        if include_rejected_mutation:
            rejected_preimage = artifacts.put_bytes(b"rejected-before\n")
            rejected_postimage = artifacts.put_bytes(b"rejected-after\n")
            rejected_intent = artifacts.put_json(
                {
                    "schema_version": "patch-mutation-intent-v1",
                    "run_id": run_id,
                    "action_id": "qualification-rejected-apply",
                    "input_hash": patch_input_hash,
                    "patch_artifact": submitted_patch.model_dump(mode="json"),
                    "baseline_worktree_diff_hash": sha256_text(""),
                    "expected_worktree_diff_hash": DIFF_HASH,
                    "files": [
                        {
                            "path": "example.py",
                            "mode": 0o644,
                            "git_mode": "100644",
                            "preimage_artifact": rejected_preimage.model_dump(mode="json"),
                            "postimage_artifact": rejected_postimage.model_dump(mode="json"),
                        }
                    ],
                }
            )
            rejected_call = state.append_event(
                run_id,
                EventType.TOOL_CALLED,
                actor="agent",
                correlation_id="qualification-rejected-apply",
                payload={
                    "tool": "apply_patch",
                    "input_hash": patch_input_hash,
                    "patch_artifact": submitted_patch.model_dump(mode="json"),
                    "artifact_id": submitted_patch.artifact_id,
                    "artifact_path": submitted_patch.path,
                },
            )
            rejected_prepared_event = state.append_event(
                run_id,
                EventType.PATCH_PREPARED,
                actor="tool-gateway",
                correlation_id="qualification-rejected-apply",
                payload={
                    "schema_version": "patch-mutation-intent-v1",
                    "artifact_id": rejected_intent.artifact_id,
                    "artifact_path": rejected_intent.path,
                    "content_hash": rejected_intent.content_hash,
                    "size_bytes": rejected_intent.size_bytes,
                    "intent_artifact": rejected_intent.model_dump(mode="json"),
                    "baseline_worktree_diff_hash": sha256_text(""),
                    "expected_worktree_diff_hash": DIFF_HASH,
                },
            )
            if rejected_retry_context is None:
                state.append_event(
                    run_id,
                    EventType.TOOL_FAILED,
                    actor="tool-gateway",
                    correlation_id="qualification-rejected-apply",
                    payload={
                        "tool": "apply_patch",
                        "status": "rejected",
                        "duration_ms": 0,
                    },
                )
            else:
                rejection_error_code = (
                    "CONTROLLED_DIAGNOSTIC_REJECTION"
                    if controlled_rejection
                    else "CONTRACT_ERROR"
                )
                rejection_error_message = (
                    "diagnostic control rejected the first "
                    "preflight-valid patch before worktree mutation"
                    if controlled_rejection
                    else "public rejected patch"
                )
                rejection_error_details = (
                    {
                        "schema_version": "controlled-rejection-v1",
                        "stage": "diagnostic",
                        "reason": "controlled_rejection",
                        "guidance": (
                            "Review the rehydrated candidate and rejection "
                            "evidence, then retry with a new action_id."
                        ),
                        "fault_type": (
                            "controlled-reject-first-prepared-patch"
                        ),
                        "trigger": (
                            "first-preflight-valid-apply-patch"
                        ),
                        "trigger_after": 1,
                        "source_call_sequence": rejected_call.sequence,
                        "source_prepared_sequence": (
                            rejected_prepared_event.sequence
                        ),
                        "candidate_content_hash": (
                            submitted_patch.content_hash
                        ),
                        "input_hash": patch_input_hash,
                        "prepared_intent_content_hash": (
                            rejected_intent.content_hash
                        ),
                        "baseline_worktree_diff_hash": sha256_text(
                            ""
                        ),
                        "expected_worktree_diff_hash": DIFF_HASH,
                        "observed_worktree_diff_hash": sha256_text(
                            ""
                        ),
                        "worktree_mutated": False,
                    }
                    if controlled_rejection
                    else {"reason": "invalid public patch"}
                )
                if (
                    controlled_rejection
                    and controlled_rejection_details_overrides is not None
                ):
                    rejection_error_details.update(
                        controlled_rejection_details_overrides
                    )
                if controlled_rejection_interleaved:
                    state.append_event(
                        run_id,
                        EventType.LOOP_DETECTED,
                        actor="tamper-test",
                        payload={
                            "reason": "interleaved-before-controlled-failure"
                        },
                    )
                rejected_result_payload = {
                    "tool": "apply_patch",
                    "status": "rejected",
                    "error_code": rejection_error_code,
                    "error_message": rejection_error_message,
                    "error_details": rejection_error_details,
                }
                rejected_result = artifacts.put_json(rejected_result_payload)
                rejected_failure = state.append_event(
                    run_id,
                    EventType.TOOL_FAILED,
                    actor="tool-gateway",
                    correlation_id="qualification-rejected-apply",
                    payload={
                        "tool": "apply_patch",
                        "status": "rejected",
                        "artifact_id": rejected_result.artifact_id,
                        "artifact_path": rejected_result.path,
                        "result_artifact": rejected_result.model_dump(mode="json"),
                        "error_code": rejection_error_code,
                        "error_message": rejection_error_message,
                        "error_details": rejection_error_details,
                        "duration_ms": 0,
                    },
                )
                retry_payload = {
                    "schema_version": "rejected-mutation-retry-v1",
                    "tool": "apply_patch",
                    "action_id": "qualification-rejected-apply",
                    "source_call_sequence": rejected_failure.sequence - 2,
                    "source_failure_sequence": rejected_failure.sequence,
                    "candidate": {
                        "patch": PATCH_TEXT,
                        "content_hash": submitted_patch.content_hash,
                        "size_bytes": submitted_patch.size_bytes,
                        "input_hash": patch_input_hash,
                    },
                    "rejection": {
                        "status": "rejected",
                        "error_code": rejection_error_code,
                        "error_message": rejection_error_message,
                        "error_details": rejection_error_details,
                    },
                }
                last_retry_payload = retry_payload
                if rejected_retry_context == "hash-only":
                    retry_payload["candidate"].pop("patch")
                elif rejected_retry_context == "wrong-reason":
                    retry_payload["rejection"]["error_code"] = "POLICY_VIOLATION"
                retry_rendered_context = json.dumps(
                    {
                        "public_task": package.public.model_dump(mode="json"),
                        "task_context": context_text,
                        "recent_events": [],
                        "rejected_mutation_retry": retry_payload,
                    },
                    ensure_ascii=False,
                    default=str,
                )
                retry_context, retry_request_hash = request_artifact(retry_rendered_context)
                state.append_event(
                    run_id,
                    EventType.CONTEXT_BUILT,
                    actor="context-builder",
                    payload={
                        "artifact_id": retry_context.artifact_id,
                        "artifact_path": retry_context.path,
                        "request_body_hash": retry_request_hash,
                        "context_hash": sha256_text(retry_rendered_context),
                    },
                )
                retry_model = artifacts.put_text("public model response: corrected patch")
                state.append_event(
                    run_id,
                    EventType.MODEL_CALLED,
                    actor="model-adapter",
                    payload=model_payload(
                        retry_model,
                        retry_context,
                        request_hash=retry_request_hash,
                    ),
                )
        patch_intent = artifacts.put_json(
            {
                "schema_version": "patch-mutation-intent-v1",
                "run_id": run_id,
                "action_id": "qualification-apply",
                "input_hash": patch_input_hash,
                "patch_artifact": submitted_patch.model_dump(mode="json"),
                "baseline_worktree_diff_hash": sha256_text(""),
                "expected_worktree_diff_hash": DIFF_HASH,
                "files": [
                    {
                        "path": "example.py",
                        "mode": 0o644,
                        "git_mode": "100644",
                        "preimage_artifact": preimage.model_dump(mode="json"),
                        "postimage_artifact": postimage.model_dump(mode="json"),
                    }
                ],
            }
        )
        state.append_event(
            run_id,
            EventType.TOOL_CALLED,
            actor="agent",
            correlation_id="qualification-apply",
            payload={
                "tool": "apply_patch",
                "input_hash": patch_input_hash,
                "patch_artifact": submitted_patch.model_dump(mode="json"),
                "artifact_id": submitted_patch.artifact_id,
                "artifact_path": submitted_patch.path,
            },
        )
        state.append_event(
            run_id,
            EventType.PATCH_PREPARED,
            actor="tool-gateway",
            correlation_id="qualification-apply",
            payload={
                "schema_version": "patch-mutation-intent-v1",
                "artifact_id": patch_intent.artifact_id,
                "artifact_path": patch_intent.path,
                "content_hash": patch_intent.content_hash,
                "size_bytes": patch_intent.size_bytes,
                "intent_artifact": patch_intent.model_dump(mode="json"),
                "baseline_worktree_diff_hash": sha256_text(""),
                "expected_worktree_diff_hash": DIFF_HASH,
            },
        )
        state.append_event(
            run_id,
            EventType.TOOL_SUCCEEDED,
            actor="tool-gateway",
            correlation_id="qualification-apply",
            payload={
                "tool": "apply_patch",
                "status": "succeeded",
                "patch_hash": DIFF_HASH,
                "worktree_diff_hash": DIFF_HASH,
                "duration_ms": 0,
            },
        )
        state.append_event(
            run_id,
            EventType.PATCH_APPLIED,
            actor="tool-gateway",
            correlation_id="qualification-apply",
            payload={
                "patch_hash": DIFF_HASH,
                "worktree_diff_hash": DIFF_HASH,
            },
        )
        if include_apply_replay:
            state.append_event(
                run_id,
                EventType.TOOL_REPLAYED,
                actor="idempotency-store",
                correlation_id="qualification-apply",
                payload={
                    "tool": "apply_patch",
                    "status": "succeeded",
                    "replayed": True,
                    "worktree_diff_hash": DIFF_HASH,
                },
            )

    if not visible_checks_after_get_diff:
        append_visible_checks()
    state.append_event(
        run_id,
        EventType.TOOL_CALLED,
        actor="agent",
        correlation_id="qualification-get-diff",
        payload={"tool": "get_diff"},
    )
    get_diff_event = state.append_event(
        run_id,
        EventType.TOOL_SUCCEEDED,
        actor="tool-gateway",
        correlation_id="qualification-get-diff",
        payload={
            "tool": "get_diff",
            "status": "succeeded",
            "artifact_id": get_diff_result.artifact_id,
            "artifact_path": get_diff_result.path,
            "worktree_diff_hash": DIFF_HASH,
            "duration_ms": 0,
        },
    )
    if visible_checks_after_get_diff:
        append_visible_checks()

    if counter_generation_block_reason is not None:
        if counter_generation_block_reason != "model_call_budget_exhausted":
            raise AssertionError(
                "the complete synthetic qualification trace only supports "
                "model-call exhaustion"
            )
        existing_model_calls = sum(
            event.type == EventType.MODEL_CALLED
            for event in state.list_events(run_id)
        )
        for index in range(
            manifest.budget.max_model_calls - existing_model_calls
        ):
            filler_rendered_context = json.dumps(
                {
                    "public_task": package.public.model_dump(mode="json"),
                    "task_context": context_text,
                    "recent_events": [],
                    "rejected_mutation_retry": None,
                },
                ensure_ascii=False,
                default=str,
            )
            filler_context, filler_request_hash = request_artifact(
                filler_rendered_context
            )
            state.append_event(
                run_id,
                EventType.CONTEXT_BUILT,
                actor="context-builder",
                payload={
                    "artifact_id": filler_context.artifact_id,
                    "artifact_path": filler_context.path,
                    "request_body_hash": filler_request_hash,
                    "context_hash": sha256_text(filler_rendered_context),
                },
            )
            filler_model = artifacts.put_text(
                f"public model response: continue {index}"
            )
            state.append_event(
                run_id,
                EventType.MODEL_CALLED,
                actor="model-adapter",
                payload=model_payload(
                    filler_model,
                    filler_context,
                    request_hash=filler_request_hash,
                ),
            )

    rendered_get_diff_event = {
        "sequence": get_diff_event.sequence,
        "type": get_diff_event.type.value,
        "actor": get_diff_event.actor,
        "payload": {
            **get_diff_event.payload,
            "tool_result": get_diff_payload,
        },
    }
    review_context_payload = {
        "public_task": package.public.model_dump(mode="json"),
        "task_context": context_text,
        "recent_events": (
            [rendered_get_diff_event] if complete_review_context and actual_review_context else []
        ),
    }
    if manifest.context_policy_version == "phase-evidence-v3":
        review_context_payload["rejected_mutation_retry"] = (
            last_retry_payload if stale_rejected_retry_context else None
        )
    review_rendered_context = json.dumps(
        review_context_payload,
        ensure_ascii=False,
        default=str,
    )
    review_tool_results = (
        [
            {
                "event_sequence": get_diff_event.sequence,
                "tool": "get_diff",
                "worktree_diff_hash": DIFF_HASH,
                "artifact_id": get_diff_result.artifact_id,
                "available": True,
                "truncated": False,
            }
        ]
        if complete_review_context
        else []
    )
    review_context, review_request_hash = request_artifact(
        review_rendered_context,
        tool_results=review_tool_results,
        runtime_contract=counter_generation_block_reason is not None,
    )
    if counter_generation_block_reason is not None:
        checkpoint = Checkpoint(
            checkpoint_id="ckpt_qualification",
            run_id=run_id,
            through_sequence=state.last_sequence(run_id),
            phase=Phase.REVIEW,
            repository_head=package.public.repository.base_commit,
            worktree_diff_hash=checkpoint_diff_hash,
            created_at=utc_now(),
        )
        state.save_checkpoint(checkpoint)
        state.append_event(
            run_id,
            EventType.CHECKPOINT_SAVED,
            actor="state-store",
            payload={
                "checkpoint_id": checkpoint.checkpoint_id,
                "through_sequence": checkpoint.through_sequence,
                "worktree_diff_hash": checkpoint.worktree_diff_hash,
            },
        )
    state.append_event(
        run_id,
        EventType.CONTEXT_BUILT,
        actor="context-builder",
        payload={
            "artifact_id": review_context.artifact_id,
            "artifact_path": review_context.path,
            "request_body_hash": review_request_hash,
            "context_hash": sha256_text(review_rendered_context),
        },
    )
    generation_block_payload: dict[str, object] | None = None
    if counter_generation_block_reason is None:
        state.append_event(
            run_id,
            EventType.MODEL_CALLED,
            actor="model-adapter",
            payload=model_payload(
                review_model,
                review_context,
                request_hash=review_request_hash,
            ),
        )
    else:
        preceding_events = state.list_events(run_id)
        model_calls_used = sum(
            event.type == EventType.MODEL_CALLED
            for event in preceding_events
        )
        tool_calls_used = sum(
            event.type == EventType.TOOL_CALLED
            for event in preceding_events
        )
        wall_clock_ms = sum(
            int(event.payload.get("duration_ms", 0))
            for event in preceding_events
            if event.type
            in {
                EventType.MODEL_CALLED,
                EventType.TOOL_SUCCEEDED,
                EventType.TOOL_FAILED,
            }
        )
        total_tokens_used = sum(
            int(event.payload.get("input_tokens", 0))
            + int(event.payload.get("output_tokens", 0))
            for event in preceding_events
            if event.type == EventType.MODEL_CALLED
        )
        generation_block_payload = {
            "schema_version": "model-generation-block-v2",
            "reason_code": counter_generation_block_reason,
            "error_code": "MODEL_GENERATION_BUDGET_EXCEEDED",
            "generation_started": False,
            "request_artifact_id": review_context.artifact_id,
            "request_artifact_path": review_context.path,
            "request_body_hash": review_request_hash,
            "requested_input_tokens": None,
            "remaining_tokens": None,
            "max_output_tokens": manifest.model.max_output_tokens,
            "input_token_count_calls": 0,
            "retry_context_present": False,
            "retry_candidate_content_hash": None,
            "model_calls_used": model_calls_used,
            "max_model_calls": manifest.budget.max_model_calls,
            "tool_calls_used": tool_calls_used,
            "max_tool_calls": manifest.budget.max_tool_calls,
            "wall_clock_ms": wall_clock_ms,
            "wall_clock_timeout_ms": (
                manifest.budget.wall_clock_timeout_seconds * 1000
            ),
            "total_tokens_used": total_tokens_used,
            "max_total_tokens": manifest.budget.max_total_tokens,
        }
        state.append_event(
            run_id,
            EventType.MODEL_GENERATION_BLOCKED,
            actor="budget-guard",
            payload=generation_block_payload,
        )
    hidden_id = package.private.hidden_checks[0].id
    if agent_failure:
        terminal_error = (
            {
                "type": "ModelGenerationBudgetError",
                "code": "MODEL_GENERATION_BUDGET_EXCEEDED",
                "message": (
                    "model generation blocked: "
                    f"{counter_generation_block_reason}"
                ),
                "details": generation_block_payload,
            }
            if generation_block_payload is not None
            else {
                "type": "ContractError",
                "message": "public failure",
            }
        )
        result = RunResult(
            run_id=run_id,
            agent_submission_status="failed",
            evaluation_status="not_run",
            scope_compliant_success=False,
            official=False,
            verdicts=Verdicts(),
            usage=Usage(
                model_calls=2,
                input_token_count_calls=2 if prompt_telemetry else 0,
                tool_calls=1,
            ),
            outcome_kind=RunOutcomeKind.AGENT_FAILURE,
            terminal_error=terminal_error,
        )
    else:
        result = _result(run_id, resolved=resolved, hidden_check_id=hidden_id)
        result.usage.model_calls = 2
        result.usage.tool_calls = 1 if legacy_contract else 2
        if not legacy_contract:
            result.submitted_patch_artifact_id = submitted_patch.artifact_id
        if prompt_telemetry:
            result.usage.input_token_count_calls = 2
    if agent_failure and (rejected_legacy_submission or unpaired_submission_attempt):
        state.append_event(
            run_id,
            EventType.SUBMISSION_ATTEMPTED,
            actor="submission-gate",
            payload={
                "attempt_number": 1,
                "worktree_diff_hash": DIFF_HASH,
                "submission_method": "legacy_done_text",
            },
        )
        if rejected_legacy_submission:
            state.append_event(
                run_id,
                EventType.SUBMISSION_REJECTED,
                actor="submission-gate",
                payload={
                    "attempt_number": 1,
                    "worktree_diff_hash": DIFF_HASH,
                    "reason_code": "structured_finish_task_required",
                    "missing_evidence": ["structured_finish_task"],
                },
            )
    if not agent_failure and not legacy_contract:
        state.append_event(
            run_id,
            EventType.TOOL_CALLED,
            actor="agent",
            correlation_id="qualification-finish",
            payload={"tool": "finish_task"},
        )
        state.append_event(
            run_id,
            EventType.REVIEW_RECORDED,
            actor="submission-gate",
            correlation_id="qualification-finish",
            payload={
                "worktree_diff_hash": DIFF_HASH,
                "source_get_diff_sequence": get_diff_event.sequence,
                "request_artifact_id": review_context.artifact_id,
                "complete_tool_result": True,
            },
        )
        state.append_event(
            run_id,
            EventType.SUBMISSION_ATTEMPTED,
            actor="submission-gate",
            correlation_id="qualification-finish",
            payload={
                "attempt_number": 1,
                "worktree_diff_hash": DIFF_HASH,
                "submission_method": "finish_task",
            },
        )
        finish_result = artifacts.put_json(
            {
                "tool": "finish_task",
                "status": "succeeded",
                "worktree_diff_hash": DIFF_HASH,
                "accepted_for_evaluation": True,
                "submitted_patch_artifact": submitted_patch.model_dump(mode="json"),
            }
        )
        state.append_event(
            run_id,
            EventType.TOOL_SUCCEEDED,
            actor="submission-gate",
            correlation_id="qualification-finish",
            payload={
                "tool": "finish_task",
                "status": "succeeded",
                "artifact_id": finish_result.artifact_id,
                "artifact_path": finish_result.path,
                "worktree_diff_hash": DIFF_HASH,
                "submitted_patch_artifact": submitted_patch.model_dump(mode="json"),
                "duration_ms": 0,
            },
        )
        state.append_event(
            run_id,
            EventType.SUBMISSION_ACCEPTED,
            actor="submission-gate",
            correlation_id="qualification-finish",
            payload={
                "attempt_number": 1,
                "worktree_diff_hash": (
                    "sha256:" + ("b" * 64) if malformed_lifecycle else DIFF_HASH
                ),
                "accepted_for": "deterministic_evaluation",
                "evaluation_success_claimed": False,
                "submitted_patch_artifact": submitted_patch.model_dump(mode="json"),
            },
        )
        state.append_event(
            run_id,
            EventType.PHASE_CHANGED,
            actor="phase-machine",
            payload={"from": "REVIEW", "to": "DONE"},
        )
    if counter_generation_block_reason is None:
        checkpoint = Checkpoint(
            checkpoint_id="ckpt_qualification",
            run_id=run_id,
            through_sequence=state.last_sequence(run_id),
            phase=Phase.REVIEW if agent_failure else Phase.DONE,
            repository_head=package.public.repository.base_commit,
            worktree_diff_hash=checkpoint_diff_hash,
            created_at=utc_now(),
        )
        state.save_checkpoint(checkpoint)
        checkpoint_event_payload: dict[str, object] = {
            "checkpoint_id": checkpoint.checkpoint_id,
            "through_sequence": checkpoint.through_sequence,
            "worktree_diff_hash": checkpoint.worktree_diff_hash,
        }
        if checkpoint_event_overrides is not None:
            checkpoint_event_payload.update(checkpoint_event_overrides)
        state.append_event(
            run_id,
            EventType.CHECKPOINT_SAVED,
            actor="state-store",
            payload=checkpoint_event_payload,
        )
        if duplicate_checkpoint_event:
            state.append_event(
                run_id,
                EventType.CHECKPOINT_SAVED,
                actor="state-store",
                payload=checkpoint_event_payload,
            )
    result.usage.tool_calls = sum(
        event.type == EventType.TOOL_CALLED for event in state.list_events(run_id)
    )
    result.usage.model_calls = sum(
        event.type == EventType.MODEL_CALLED for event in state.list_events(run_id)
    )
    result.usage.input_token_count_calls = sum(
        int(event.payload.get("input_token_count_calls", 0))
        for event in state.list_events(run_id)
        if event.type == EventType.MODEL_CALLED
    )
    failure_id = ""
    failure = classify_failure(
        result,
        package.public.split,
        root=tmp_path,
    )
    if failure is not None:
        failure_id = failure.failure_id
        state.append_event(
            run_id,
            EventType.FAILURE_TAGGED,
            actor="failure-classifier",
            payload={"failure_id": failure.failure_id},
        )
    state.finalize_run(
        run_id,
        status=RunStatus.FAILED if agent_failure else RunStatus.COMPLETED,
        result=result,
        event_type=(EventType.RUN_FAILED if agent_failure else EventType.RUN_COMPLETED),
        actor="runner" if agent_failure else "evaluator",
        payload=(
            {
                "error_type": "ModelGenerationBudgetError",
                "error_code": "MODEL_GENERATION_BUDGET_EXCEEDED",
                "error_details": generation_block_payload,
                "message": (
                    "model generation blocked: "
                    f"{counter_generation_block_reason}"
                ),
            }
            if generation_block_payload is not None
            else None
        ),
    )
    result_path = tmp_path / "artifacts" / "runs" / run_id / "result.json"
    result_path.parent.mkdir(parents=True)
    result_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return run_id, result, failure_id


def test_live_memory_development_failure_is_qualified_and_eligible(tmp_path) -> None:
    run_id, _, failure_id = _terminal_trace(tmp_path)

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    assert qualification["schema_version"] == "trace-qualification-v2"
    assert qualification["model_id"] == "gpt-5.4-mini-2026-03-17"
    assert qualification["reasoning_effort"] == "medium"
    assert qualification["reasoning_mode"] == "standard"
    assert qualification["service_tier"] == "default"
    assert qualification["max_output_tokens"] == 25_000
    assert qualification["budget"] == Budget(
        max_model_calls=21,
        max_total_tokens=200_000
    ).model_dump(mode="json")
    assert qualification["harness_git_commit"]
    assert qualification["tool_schema_version"] == "v2"
    assert qualification["context_policy_version"] == "phase-evidence-v2"
    assert qualification["runtime_contract_content_hash"] == sha256_bytes(
        b"public runtime contract"
    )
    lifecycle = next(
        check for check in qualification["checks"] if check["check_id"] == "submission_lifecycle"
    )
    assert lifecycle["details"]["submitted_patch_artifact_valid"] is True
    assert lifecycle["details"]["request_body_valid"] is True
    assert lifecycle["details"]["complete_source_in_context"] is True
    assert lifecycle["details"]["ordered_submission_valid"] is True
    assert qualification["qualified"] is True, [
        check
        for check in qualification["checks"]
        if not check["passed"]
    ]
    assert qualification["trace_integrity_passed"] is True
    assert qualification["leakage_scan_passed"] is True
    assert qualification["outcome_kind"] == "task_failure"
    assert qualification["memory_candidate_eligible"] is True
    assert qualification["failure_record_id"] == failure_id
    assert qualification["source_evidence_hash"] == calculate_source_evidence_hash(
        run_id,
        root=tmp_path,
    )
    assert load_trace_qualification(run_id, root=tmp_path) == qualification


def test_v2_source_hash_binds_accepted_patch_cas_bytes(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(tmp_path)
    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)
    state = StateStore(tmp_path / "state.sqlite3")
    accepted = next(
        event for event in state.list_events(run_id) if event.type == EventType.SUBMISSION_ACCEPTED
    )
    submitted_patch = Artifact.model_validate(accepted.payload["submitted_patch_artifact"])

    Path(submitted_patch.path).write_bytes(b"tampered accepted patch")

    assert (
        calculate_source_evidence_hash(
            run_id,
            root=tmp_path,
        )
        != qualification["source_evidence_hash"]
    )
    with pytest.raises(ContractError, match="qualification is immutable"):
        qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)


def test_v4_source_schema_does_not_rewrite_historical_v3_hash(
    tmp_path,
    monkeypatch,
) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        force_v3_contract=True,
    )
    original_hash = calculate_source_evidence_hash(
        run_id,
        root=tmp_path,
    )

    assert (
        qualification_module._SOURCE_EVIDENCE_SCHEMA_VERSION_V4
        == "trace-source-evidence-v4"
    )
    with monkeypatch.context() as schema_patch:
        schema_patch.setattr(
            qualification_module,
            "_SOURCE_EVIDENCE_SCHEMA_VERSION_V4",
            "trace-source-evidence-v4-test-mutation",
        )
        assert (
            calculate_source_evidence_hash(
                run_id,
                root=tmp_path,
            )
            == original_hash
        )


def test_v2_source_hash_binds_patch_intent_preimage_bytes(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )
    runner = AgentRunner(tmp_path)
    result = runner.start(
        "tasks/smoke/csv-quoted-newline/public.yaml",
        model="mock",
    )
    run_id = result["run_id"]
    source_hash = calculate_source_evidence_hash(
        run_id,
        root=tmp_path,
        require_valid_plan=False,
    )
    prepared = next(
        event
        for event in runner.state.list_events(run_id)
        if event.type == EventType.PATCH_PREPARED
    )
    intent = json.loads(Path(prepared.payload["artifact_path"]).read_text(encoding="utf-8"))
    preimage = Artifact.model_validate(intent["files"][0]["preimage_artifact"])

    Path(preimage.path).write_bytes(b"tampered preimage")

    assert (
        calculate_source_evidence_hash(
            run_id,
            root=tmp_path,
            require_valid_plan=False,
        )
        != source_hash
    )


def test_v2_source_hash_binds_verifier_evidence_bytes(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )
    runner = AgentRunner(tmp_path)
    result = runner.start(
        "tasks/smoke/csv-quoted-newline/public.yaml",
        model="mock",
    )
    run_id = result["run_id"]
    source_hash = calculate_source_evidence_hash(
        run_id,
        root=tmp_path,
        require_valid_plan=False,
    )
    persisted = RunResult.model_validate_json(
        (tmp_path / "artifacts" / "runs" / run_id / "result.json").read_text(encoding="utf-8")
    )
    raw_evidence = next(
        verifier.details["evidence_artifacts"][0]
        for verifier in persisted.verifier_results
        if verifier.evidence_artifact_ids
    )
    verifier_artifact = Artifact.model_validate(raw_evidence)

    Path(verifier_artifact.path).write_bytes(b"tampered verifier output")

    assert (
        calculate_source_evidence_hash(
            run_id,
            root=tmp_path,
            require_valid_plan=False,
        )
        != source_hash
    )


def test_v2_qualification_requires_patch_prepared_lifecycle(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(tmp_path)
    database = tmp_path / "state.sqlite3"
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT sequence, event_json FROM events WHERE run_id = ? ORDER BY sequence",
            (run_id,),
        ).fetchall()
        sequence, raw_event = next(
            (sequence, raw_event)
            for sequence, raw_event in rows
            if json.loads(raw_event)["type"] == EventType.PATCH_PREPARED.value
        )
        event = json.loads(raw_event)
        event["type"] = EventType.TOOL_REPLAYED.value
        connection.execute(
            "UPDATE events SET event_json = ? WHERE run_id = ? AND sequence = ?",
            (json.dumps(event), run_id, sequence),
        )

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    assert qualification["qualified"] is False
    lifecycle = next(
        check for check in qualification["checks"] if check["check_id"] == "submission_lifecycle"
    )
    assert lifecycle["details"]["patch_intent_valid"] is False
    artifacts = next(
        check for check in qualification["checks"] if check["check_id"] == "agent_visible_artifacts"
    )
    assert artifacts["passed"] is False


def test_v2_patch_intent_binds_tool_call_top_level_patch_artifact(
    tmp_path,
) -> None:
    run_id, _, _ = _terminal_trace(tmp_path)
    database = tmp_path / "state.sqlite3"
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT sequence, event_json FROM events WHERE run_id = ? ORDER BY sequence",
            (run_id,),
        ).fetchall()
        sequence, raw_event = next(
            (sequence, raw_event)
            for sequence, raw_event in rows
            if json.loads(raw_event)["type"] == EventType.TOOL_CALLED.value
            and json.loads(raw_event)["payload"].get("tool") == "apply_patch"
        )
        event = json.loads(raw_event)
        event["payload"]["artifact_id"] = "art_tampered_top_level"
        connection.execute(
            "UPDATE events SET event_json = ? WHERE run_id = ? AND sequence = ?",
            (json.dumps(event), run_id, sequence),
        )

    qualification = qualify_run(
        run_id,
        task_dir=MEMORY_TASK,
        root=tmp_path,
    )

    artifacts = next(
        check for check in qualification["checks"] if check["check_id"] == "agent_visible_artifacts"
    )
    assert artifacts["passed"] is False
    assert qualification["qualified"] is False


def test_v2_patch_intent_binds_applied_patch_hash(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(tmp_path)
    database = tmp_path / "state.sqlite3"
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT sequence, event_json FROM events WHERE run_id = ? ORDER BY sequence",
            (run_id,),
        ).fetchall()
        sequence, raw_event = next(
            (sequence, raw_event)
            for sequence, raw_event in rows
            if json.loads(raw_event)["type"] == EventType.PATCH_APPLIED.value
        )
        event = json.loads(raw_event)
        event["payload"]["patch_hash"] = "sha256:" + ("f" * 64)
        connection.execute(
            "UPDATE events SET event_json = ? WHERE run_id = ? AND sequence = ?",
            (json.dumps(event), run_id, sequence),
        )

    qualification = qualify_run(
        run_id,
        task_dir=MEMORY_TASK,
        root=tmp_path,
    )

    artifacts = next(
        check for check in qualification["checks"] if check["check_id"] == "agent_visible_artifacts"
    )
    assert artifacts["passed"] is False
    assert qualification["qualified"] is False


def test_v2_source_hash_binds_worker_claim_provenance(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(tmp_path)
    qualification = qualify_run(
        run_id,
        task_dir=MEMORY_TASK,
        root=tmp_path,
    )
    database = tmp_path / "state.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "DELETE FROM run_worker_claims WHERE run_id = ?",
            (run_id,),
        )

    assert (
        calculate_source_evidence_hash(
            run_id,
            root=tmp_path,
            require_valid_plan=False,
        )
        != qualification["source_evidence_hash"]
    )
    with pytest.raises(ContractError, match="qualification is immutable"):
        qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)


def test_idempotent_apply_replay_does_not_duplicate_success_lifecycle(
    tmp_path,
) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        include_apply_replay=True,
    )

    qualification = qualify_run(
        run_id,
        task_dir=MEMORY_TASK,
        root=tmp_path,
    )

    assert qualification["qualified"] is True
    lifecycle = next(
        check for check in qualification["checks"] if check["check_id"] == "submission_lifecycle"
    )
    assert lifecycle["details"]["ordered_submission_valid"] is True


def test_rejected_prepared_patch_before_success_remains_qualified(
    tmp_path,
) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        include_rejected_mutation=True,
    )

    qualification = qualify_run(
        run_id,
        task_dir=MEMORY_TASK,
        root=tmp_path,
    )

    assert qualification["qualified"] is True
    assert all(
        check["check_id"] != "rejected_patch_retry_context" for check in qualification["checks"]
    )
    artifacts = next(
        check for check in qualification["checks"] if check["check_id"] == "agent_visible_artifacts"
    )
    assert artifacts["passed"] is True
    assert artifacts["details"]["patch_intent_artifact_count"] == 8


def test_v3_qualification_binds_exact_rejected_patch_retry_context(
    tmp_path,
) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        include_rejected_mutation=True,
        rejected_retry_context="exact",
    )

    qualification = qualify_run(
        run_id,
        task_dir=MEMORY_TASK,
        root=tmp_path,
    )

    retry = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "rejected_patch_retry_context"
    )
    assert retry["passed"] is True
    assert retry["details"]["rejected_candidate_count"] == 1
    assert retry["details"]["retry_episode_count"] == 1
    assert retry["details"]["verified_retry_count"] == 1
    assert retry["details"]["model_generation_blocked_count"] == 0
    assert len(retry["details"]["verified_candidate_content_hashes"]) == 1
    assert retry["details"]["failed_source_failure_sequences"] == []
    assert qualification["qualified"] is True


def test_controlled_diagnostic_binds_one_unmutated_rejection_and_retry(
    tmp_path,
) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        task_dir=PILOT_TASK,
        purpose=(
            ExperimentPurpose.DEVELOPMENT_VALIDATION_MODEL_CANDIDATE_PILOT
        ),
        role=DatasetRole.DEVELOPMENT_VALIDATION,
        resolved=True,
        prompt_telemetry=True,
        model_id="gpt-5.4-mini-2026-03-17",
        budget=Budget(max_total_tokens=200_000),
        max_output_tokens=25_000,
        include_rejected_mutation=True,
        rejected_retry_context="exact",
        controlled_rejection=True,
        fault=FaultSpec(
            type="controlled-reject-first-prepared-patch",
            trigger_after=1,
        ),
    )

    qualification = qualify_run(
        run_id,
        task_dir=PILOT_TASK,
        root=tmp_path,
    )

    controlled = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "controlled_diagnostic_boundary"
    )
    retry = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "rejected_patch_retry_context"
    )
    assert controlled["passed"] is True
    assert controlled["details"]["controlled_rejection_count"] == 1
    assert (
        controlled["details"]["verified_controlled_rejection_count"]
        == 1
    )
    assert controlled["details"]["controlled_patch_applied_sequences"] == []
    assert retry["passed"] is True
    assert retry["details"]["retry_episode_count"] == 1
    assert retry["details"]["verified_retry_count"] == 1
    assert retry["details"]["controlled_rejection_count"] == 1
    assert not any(
        check["check_id"] == "fault_free"
        for check in qualification["checks"]
    )
    assert qualification["qualified"] is True


def test_controlled_diagnostic_rejects_interleaved_failure_declaration(
    tmp_path,
) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        task_dir=PILOT_TASK,
        purpose=(
            ExperimentPurpose.DEVELOPMENT_VALIDATION_MODEL_CANDIDATE_PILOT
        ),
        role=DatasetRole.DEVELOPMENT_VALIDATION,
        resolved=True,
        prompt_telemetry=True,
        model_id="gpt-5.4-mini-2026-03-17",
        budget=Budget(max_total_tokens=200_000),
        max_output_tokens=25_000,
        include_rejected_mutation=True,
        rejected_retry_context="exact",
        controlled_rejection=True,
        controlled_rejection_interleaved=True,
        fault=FaultSpec(
            type="controlled-reject-first-prepared-patch",
            trigger_after=1,
        ),
    )

    qualification = qualify_run(
        run_id,
        task_dir=PILOT_TASK,
        root=tmp_path,
    )

    controlled = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "controlled_diagnostic_boundary"
    )
    assert controlled["passed"] is False
    assert controlled["details"][
        "verified_controlled_rejection_count"
    ] == 0
    assert qualification["qualified"] is False


@pytest.mark.parametrize("corruption", ["malformed", "duplicate"])
def test_controlled_diagnostic_fails_closed_on_declared_rejection_corruption(
    tmp_path,
    corruption,
) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        task_dir=PILOT_TASK,
        purpose=(
            ExperimentPurpose.DEVELOPMENT_VALIDATION_MODEL_CANDIDATE_PILOT
        ),
        role=DatasetRole.DEVELOPMENT_VALIDATION,
        resolved=True,
        prompt_telemetry=True,
        model_id="gpt-5.4-mini-2026-03-17",
        budget=Budget(max_total_tokens=200_000),
        max_output_tokens=25_000,
        include_rejected_mutation=True,
        rejected_retry_context="exact",
        controlled_rejection=True,
        controlled_rejection_details_overrides=(
            {"schema_version": "controlled-rejection-corrupt"}
            if corruption == "malformed"
            else None
        ),
        fault=FaultSpec(
            type="controlled-reject-first-prepared-patch",
            trigger_after=1,
        ),
    )
    state = StateStore(tmp_path / "state.sqlite3")
    controlled_failures = [
        event
        for event in state.list_events(run_id)
        if event.type == EventType.TOOL_FAILED
        and event.payload.get("error_code")
        == "CONTROLLED_DIAGNOSTIC_REJECTION"
    ]
    assert len(controlled_failures) == 1
    expected_failed_sequences = [controlled_failures[0].sequence]
    if corruption == "duplicate":
        duplicate = state.append_event(
            run_id,
            EventType.TOOL_FAILED,
            actor=controlled_failures[0].actor,
            correlation_id=controlled_failures[0].correlation_id,
            payload=dict(controlled_failures[0].payload),
        )
        expected_failed_sequences = [duplicate.sequence]

    qualification = qualify_run(
        run_id,
        task_dir=PILOT_TASK,
        root=tmp_path,
    )

    controlled = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "controlled_diagnostic_boundary"
    )
    assert controlled["passed"] is False
    assert controlled["details"]["controlled_rejection_count"] == (
        2 if corruption == "duplicate" else 1
    )
    assert controlled["details"]["verified_controlled_rejection_count"] == (
        1 if corruption == "duplicate" else 0
    )
    assert (
        controlled["details"]["failed_controlled_source_failure_sequences"]
        == expected_failed_sequences
    )
    assert qualification["qualified"] is False


def test_controlled_diagnostic_rejects_profile_manifest_fault_mismatch(
    tmp_path,
) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        task_dir=PILOT_TASK,
        purpose=(
            ExperimentPurpose.DEVELOPMENT_VALIDATION_MODEL_CANDIDATE_PILOT
        ),
        role=DatasetRole.DEVELOPMENT_VALIDATION,
        resolved=True,
        prompt_telemetry=True,
        model_id="gpt-5.4-mini-2026-03-17",
        budget=Budget(max_total_tokens=200_000),
        max_output_tokens=25_000,
        include_rejected_mutation=True,
        rejected_retry_context="exact",
        controlled_rejection=True,
        fault=FaultSpec(
            type="controlled-reject-first-prepared-patch",
            trigger_after=1,
        ),
        execution_plan_suite_overrides={
            "diagnostic": {
                "schema_version": "experiment-diagnostic-v1",
                "profile": "d037-rejected-patch-retry-v3",
                "required_trace_features": [
                    "rejected_patch_retry_context"
                ],
            }
        },
    )

    qualification = qualify_run(
        run_id,
        task_dir=PILOT_TASK,
        root=tmp_path,
    )

    plan = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "approved_execution_plan"
    )
    assert plan["passed"] is False
    assert qualification["qualified"] is False


def test_v3_retry_context_contract_passes_vacuously_without_rejection(
    tmp_path,
) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        resolved=True,
        force_v3_contract=True,
    )

    qualification = qualify_run(
        run_id,
        task_dir=MEMORY_TASK,
        root=tmp_path,
    )

    retry = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "rejected_patch_retry_context"
    )
    assert retry["passed"] is True
    assert retry["details"]["rejected_candidate_count"] == 0
    assert retry["details"]["retry_episode_count"] == 0
    assert retry["details"]["verified_retry_count"] == 0
    assert qualification["qualified"] is True


@pytest.mark.parametrize(
    "retry_context",
    ["hash-only", "wrong-reason"],
)
def test_v3_qualification_rejects_incomplete_retry_context(
    tmp_path,
    retry_context,
) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        include_rejected_mutation=True,
        rejected_retry_context=retry_context,
    )

    qualification = qualify_run(
        run_id,
        task_dir=MEMORY_TASK,
        root=tmp_path,
    )

    retry = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "rejected_patch_retry_context"
    )
    assert retry["passed"] is False
    assert retry["details"]["verified_retry_count"] == 0
    assert len(retry["details"]["failed_source_failure_sequences"]) == 1
    assert qualification["trace_integrity_passed"] is False
    assert qualification["qualified"] is False


@pytest.mark.parametrize(
    "tamper_target",
    ["nested-content-hash", "top-level-artifact-id"],
)
def test_v3_qualification_rejects_tampered_result_identity(
    tmp_path,
    tamper_target,
) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        include_rejected_mutation=True,
        rejected_retry_context="exact",
    )
    database = tmp_path / "state.sqlite3"
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT sequence, event_json FROM events WHERE run_id = ? ORDER BY sequence",
            (run_id,),
        ).fetchall()
        sequence, raw_event = next(
            (sequence, raw_event)
            for sequence, raw_event in rows
            if json.loads(raw_event)["type"] == EventType.TOOL_FAILED.value
            and json.loads(raw_event)["payload"].get("tool") == "apply_patch"
        )
        event = json.loads(raw_event)
        if tamper_target == "nested-content-hash":
            event["payload"]["result_artifact"]["content_hash"] = "sha256:" + ("f" * 64)
        else:
            event["payload"]["artifact_id"] = "art_tampered_top_level"
        connection.execute(
            "UPDATE events SET event_json = ? WHERE run_id = ? AND sequence = ?",
            (json.dumps(event), run_id, sequence),
        )

    qualification = qualify_run(
        run_id,
        task_dir=MEMORY_TASK,
        root=tmp_path,
    )

    retry = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "rejected_patch_retry_context"
    )
    assert retry["passed"] is False
    assert qualification["qualified"] is False


def test_v3_qualification_rejects_stale_retry_block_after_consumer(
    tmp_path,
) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        include_rejected_mutation=True,
        rejected_retry_context="exact",
        stale_rejected_retry_context=True,
    )

    qualification = qualify_run(
        run_id,
        task_dir=MEMORY_TASK,
        root=tmp_path,
    )

    retry = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "rejected_patch_retry_context"
    )
    assert retry["passed"] is False
    assert retry["details"]["verified_retry_count"] == 0
    assert qualification["trace_integrity_passed"] is False
    assert qualification["qualified"] is False


def test_rejected_prepared_patch_still_binds_its_private_cas(
    tmp_path,
) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        include_rejected_mutation=True,
    )
    state = StateStore(tmp_path / "state.sqlite3")
    rejected_prepared = next(
        event
        for event in state.list_events(run_id)
        if event.type == EventType.PATCH_PREPARED
        and event.correlation_id == "qualification-rejected-apply"
    )
    intent = json.loads(
        Path(rejected_prepared.payload["artifact_path"]).read_text(encoding="utf-8")
    )
    rejected_preimage = Artifact.model_validate(intent["files"][0]["preimage_artifact"])
    Path(rejected_preimage.path).write_bytes(b"tampered rejected preimage")

    qualification = qualify_run(
        run_id,
        task_dir=MEMORY_TASK,
        root=tmp_path,
    )

    artifacts = next(
        check for check in qualification["checks"] if check["check_id"] == "agent_visible_artifacts"
    )
    assert artifacts["passed"] is False
    assert qualification["qualified"] is False


def test_legacy_v1_qualification_is_byte_stable_when_requalified(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(tmp_path, legacy_contract=True)

    first = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)
    path = tmp_path / "qualifications" / f"{run_id}.json"
    first["checks"] = [
        check for check in first["checks"] if check["check_id"] != "prompt_token_integrity"
    ]
    first["qualification_hash"] = sha256_text(
        canonical_json({key: value for key, value in first.items() if key != "qualification_hash"})
    )
    path.write_text(
        json.dumps(first, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    original_bytes = path.read_bytes()
    second = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    assert first["schema_version"] == "trace-qualification-v1"
    assert all(check["check_id"] != "submission_lifecycle" for check in first["checks"])
    assert "runtime_contract_content_hash" not in first
    assert "tool_schema_version" not in first
    assert "context_policy_version" not in first
    required_trace = next(
        check for check in first["checks"] if check["check_id"] == "required_trace_evidence"
    )
    assert set(required_trace["details"]) == {
        "missing_event_types",
        "checkpoint_count",
    }
    assert second == first
    assert path.read_bytes() == original_bytes


def test_structured_v2_neutral_detail_shape_is_byte_stable_when_requalified(
    tmp_path,
) -> None:
    run_id, _, _ = _terminal_trace(tmp_path, prompt_telemetry=True)

    historical = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)
    path = tmp_path / "qualifications" / f"{run_id}.json"
    terminal_check = next(
        check
        for check in historical["checks"]
        if check["check_id"] == "terminal_result_integrity"
    )
    terminal_check["details"].update(
        {
            "model_generation_block_binding_required": False,
            "model_generation_block_binding_valid": True,
        }
    )
    historical["qualification_hash"] = sha256_text(
        canonical_json(
            {
                key: value
                for key, value in historical.items()
                if key != "qualification_hash"
            }
        )
    )
    path.write_text(
        json.dumps(
            historical,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    original_bytes = path.read_bytes()

    reloaded = qualify_run(
        run_id,
        task_dir=MEMORY_TASK,
        root=tmp_path,
    )

    assert reloaded == historical
    assert path.read_bytes() == original_bytes


def test_structured_v2_non_neutral_qualification_change_is_rejected(
    tmp_path,
) -> None:
    run_id, _, _ = _terminal_trace(tmp_path, prompt_telemetry=True)

    tampered = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)
    path = tmp_path / "qualifications" / f"{run_id}.json"
    prompt_check = next(
        check
        for check in tampered["checks"]
        if check["check_id"] == "prompt_token_integrity"
    )
    prompt_check["passed"] = False
    tampered["qualified"] = False
    tampered["qualification_hash"] = sha256_text(
        canonical_json(
            {
                key: value
                for key, value in tampered.items()
                if key != "qualification_hash"
            }
        )
    )
    path.write_text(
        json.dumps(
            tampered,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ContractError, match="trace qualification is immutable"):
        qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)


def test_structured_submission_lifecycle_must_bind_same_diff(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(tmp_path, malformed_lifecycle=True)

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    lifecycle = next(
        check for check in qualification["checks"] if check["check_id"] == "submission_lifecycle"
    )
    assert lifecycle["passed"] is False
    assert qualification["trace_integrity_passed"] is False
    assert qualification["qualified"] is False


def test_submission_review_must_include_complete_get_diff_result(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        complete_review_context=False,
    )

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    lifecycle = next(
        check for check in qualification["checks"] if check["check_id"] == "submission_lifecycle"
    )
    assert lifecycle["passed"] is False
    assert lifecycle["details"]["source_get_diff_valid"] is True
    assert lifecycle["details"]["review_context_valid"] is True
    assert lifecycle["details"]["complete_source_in_context"] is False


def test_submission_review_sidecar_cannot_replace_actual_request_context(
    tmp_path,
) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        actual_review_context=False,
    )

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    lifecycle = next(
        check for check in qualification["checks"] if check["check_id"] == "submission_lifecycle"
    )
    assert lifecycle["passed"] is False
    assert lifecycle["details"]["request_body_valid"] is True
    assert lifecycle["details"]["complete_source_in_context"] is False


@pytest.mark.parametrize(
    "trace_overrides",
    [
        {"include_mutation": False},
        {"include_visible_checks": False},
        {"visible_checks_after_get_diff": True},
    ],
    ids=["missing-mutation", "missing-checks", "checks-after-get-diff"],
)
def test_submission_qualification_reconstructs_required_order(
    tmp_path,
    trace_overrides: dict[str, bool],
) -> None:
    run_id, _, _ = _terminal_trace(tmp_path, **trace_overrides)

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    lifecycle = next(
        check for check in qualification["checks"] if check["check_id"] == "submission_lifecycle"
    )
    assert lifecycle["passed"] is False
    assert lifecycle["details"]["ordered_submission_valid"] is False


def test_submission_lifecycle_requires_done_checkpoint_on_same_diff(
    tmp_path,
) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        checkpoint_diff_hash="sha256:" + ("c" * 64),
    )

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    lifecycle = next(
        check for check in qualification["checks"] if check["check_id"] == "submission_lifecycle"
    )
    assert lifecycle["passed"] is False
    assert lifecycle["details"]["done_checkpoint_valid"] is False


def test_v2_qualification_rejects_durable_checkpoint_without_event(
    tmp_path,
) -> None:
    run_id, _, _ = _terminal_trace(tmp_path)
    state = StateStore(tmp_path / "state.sqlite3")
    checkpoint = state.latest_checkpoint(run_id)
    assert checkpoint is not None
    state.save_checkpoint(
        checkpoint.model_copy(
            update={
                "checkpoint_id": "ckpt_without_event",
                "created_at": utc_now(),
            }
        )
    )

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    required_trace = next(
        check for check in qualification["checks"] if check["check_id"] == "required_trace_evidence"
    )
    assert required_trace["passed"] is False
    assert required_trace["details"]["checkpoint_count"] == 2
    assert required_trace["details"]["checkpoint_event_count"] == 1
    assert required_trace["details"]["missing_checkpoint_event_ids"] == ["ckpt_without_event"]
    assert qualification["trace_integrity_passed"] is False


def test_v2_qualification_rejects_checkpoint_event_without_durable_identity(
    tmp_path,
) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        checkpoint_event_overrides={"checkpoint_id": "ckpt_without_durable_state"},
    )

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    required_trace = next(
        check for check in qualification["checks"] if check["check_id"] == "required_trace_evidence"
    )
    assert required_trace["passed"] is False
    assert required_trace["details"]["missing_checkpoint_event_ids"] == ["ckpt_qualification"]
    assert required_trace["details"]["orphan_checkpoint_event_ids"] == [
        "ckpt_without_durable_state"
    ]


def test_v2_qualification_rejects_duplicate_checkpoint_event(
    tmp_path,
) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        duplicate_checkpoint_event=True,
    )

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    required_trace = next(
        check for check in qualification["checks"] if check["check_id"] == "required_trace_evidence"
    )
    assert required_trace["passed"] is False
    assert required_trace["details"]["checkpoint_event_count"] == 2
    assert required_trace["details"]["duplicate_checkpoint_event_ids"] == ["ckpt_qualification"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("through_sequence", -1),
        ("worktree_diff_hash", "sha256:" + ("d" * 64)),
    ],
)
def test_v2_qualification_rejects_checkpoint_event_payload_conflict(
    tmp_path,
    field: str,
    value: object,
) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        checkpoint_event_overrides={field: value},
    )

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    required_trace = next(
        check for check in qualification["checks"] if check["check_id"] == "required_trace_evidence"
    )
    assert required_trace["passed"] is False
    assert required_trace["details"]["checkpoint_payload_mismatches"] == [
        {
            "checkpoint_id": "ckpt_qualification",
            "fields": [field],
        }
    ]


def test_uncorrelated_legacy_rejection_uses_attempt_identity_fallback(
    tmp_path,
) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        agent_failure=True,
        rejected_legacy_submission=True,
    )

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    lifecycle = next(
        check for check in qualification["checks"] if check["check_id"] == "submission_lifecycle"
    )
    assert lifecycle["passed"] is True
    assert lifecycle["details"]["attempt_count"] == 1
    assert lifecycle["details"]["paired_attempt_count"] == 1


def test_unpaired_submission_attempt_fails_lifecycle_qualification(
    tmp_path,
) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        agent_failure=True,
        unpaired_submission_attempt=True,
    )

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    lifecycle = next(
        check for check in qualification["checks"] if check["check_id"] == "submission_lifecycle"
    )
    assert lifecycle["passed"] is False
    assert lifecycle["details"]["attempt_count"] == 1
    assert lifecycle["details"]["paired_attempt_count"] == 0
    assert qualification["trace_integrity_passed"] is False


def test_memory_development_requires_prompt_token_telemetry(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(tmp_path, prompt_telemetry=False)

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    prompt_check = next(
        check for check in qualification["checks"] if check["check_id"] == "prompt_token_integrity"
    )
    assert prompt_check["passed"] is False
    assert prompt_check["details"]["required"] is True
    assert prompt_check["details"]["declared"] is False
    assert qualification["qualified"] is False
    assert qualification["memory_candidate_eligible"] is False


def test_prompt_token_telemetry_is_enforced_when_declared(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(tmp_path, prompt_telemetry=True)

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    prompt_check = next(
        check for check in qualification["checks"] if check["check_id"] == "prompt_token_integrity"
    )
    assert prompt_check["passed"] is True
    assert prompt_check["details"]["required"] is True
    assert qualification["qualified"] is True


def test_gpt54mini_pilot_contract_is_qualified(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        task_dir=PILOT_TASK,
        purpose=ExperimentPurpose.DEVELOPMENT_VALIDATION_MODEL_CANDIDATE_PILOT,
        role=DatasetRole.DEVELOPMENT_VALIDATION,
        resolved=True,
        prompt_telemetry=True,
        model_id="gpt-5.4-mini-2026-03-17",
        budget=Budget(max_total_tokens=90_000),
    )

    qualification = qualify_run(run_id, task_dir=PILOT_TASK, root=tmp_path)

    model_check = next(
        check for check in qualification["checks"] if check["check_id"] == "frozen_model_contract"
    )
    assert model_check["passed"] is True
    assert model_check["details"]["model_id"] == "gpt-5.4-mini-2026-03-17"
    assert model_check["details"]["max_total_tokens"] == 90_000
    assert qualification["qualified"] is True


def test_gpt54mini_d037_corrective_contract_is_qualified(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        task_dir=PILOT_TASK,
        purpose=ExperimentPurpose.DEVELOPMENT_VALIDATION_MODEL_CANDIDATE_PILOT,
        role=DatasetRole.DEVELOPMENT_VALIDATION,
        resolved=True,
        prompt_telemetry=True,
        model_id="gpt-5.4-mini-2026-03-17",
        budget=Budget(max_total_tokens=120_000),
        max_output_tokens=25_000,
    )

    qualification = qualify_run(run_id, task_dir=PILOT_TASK, root=tmp_path)

    model_check = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "frozen_model_contract"
    )
    assert model_check["passed"] is True
    assert model_check["details"]["model_id"] == "gpt-5.4-mini-2026-03-17"
    assert model_check["details"]["max_total_tokens"] == 120_000
    assert model_check["details"]["max_output_tokens"] == 25_000
    plan_check = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "approved_execution_plan"
    )
    assert plan_check["passed"] is True
    assert qualification["qualified"] is True


def test_gpt54mini_d037_tail_reserve_contract_is_qualified(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        task_dir=PILOT_TASK,
        purpose=ExperimentPurpose.DEVELOPMENT_VALIDATION_MODEL_CANDIDATE_PILOT,
        role=DatasetRole.DEVELOPMENT_VALIDATION,
        resolved=True,
        prompt_telemetry=True,
        model_id="gpt-5.4-mini-2026-03-17",
        budget=Budget(max_total_tokens=200_000),
        max_output_tokens=25_000,
    )

    qualification = qualify_run(run_id, task_dir=PILOT_TASK, root=tmp_path)

    model_check = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "frozen_model_contract"
    )
    assert model_check["passed"] is True
    assert model_check["details"]["model_id"] == "gpt-5.4-mini-2026-03-17"
    assert model_check["details"]["max_total_tokens"] == 200_000
    assert model_check["details"]["max_output_tokens"] == 25_000
    plan_check = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "approved_execution_plan"
    )
    assert plan_check["passed"] is True
    assert qualification["qualified"] is True


@pytest.mark.parametrize(
    "suite_overrides",
    [
        {"diagnostic": None},
        {
            "diagnostic": {
                "schema_version": "experiment-diagnostic-v1",
                "profile": "d037-rejected-patch-retry-v1",
                "required_trace_features": ["rejected_patch_retry_context"],
            }
        },
        {"budget": Budget(max_total_tokens=90_000).model_dump(mode="json")},
        {"max_output_tokens": 4096},
        {"model_id": "gpt-5.6-terra"},
    ],
)
def test_gpt54mini_d037_corrective_plan_tampering_is_rejected(
    tmp_path,
    suite_overrides: dict[str, object],
) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        task_dir=PILOT_TASK,
        purpose=ExperimentPurpose.DEVELOPMENT_VALIDATION_MODEL_CANDIDATE_PILOT,
        role=DatasetRole.DEVELOPMENT_VALIDATION,
        resolved=True,
        prompt_telemetry=True,
        model_id="gpt-5.4-mini-2026-03-17",
        budget=Budget(max_total_tokens=120_000),
        max_output_tokens=25_000,
        execution_plan_suite_overrides=suite_overrides,
    )

    qualification = qualify_run(run_id, task_dir=PILOT_TASK, root=tmp_path)

    plan_check = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "approved_execution_plan"
    )
    assert plan_check["passed"] is False
    assert qualification["qualified"] is False


def test_gpt54mini_d037_partial_corrective_contract_is_rejected(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        task_dir=PILOT_TASK,
        purpose=ExperimentPurpose.DEVELOPMENT_VALIDATION_MODEL_CANDIDATE_PILOT,
        role=DatasetRole.DEVELOPMENT_VALIDATION,
        resolved=True,
        prompt_telemetry=True,
        model_id="gpt-5.4-mini-2026-03-17",
        budget=Budget(max_total_tokens=90_000),
        max_output_tokens=25_000,
    )

    qualification = qualify_run(run_id, task_dir=PILOT_TASK, root=tmp_path)

    model_check = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "frozen_model_contract"
    )
    assert model_check["passed"] is False
    assert qualification["qualified"] is False


def test_gpt54mini_pilot_requires_prompt_token_telemetry(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        task_dir=PILOT_TASK,
        purpose=ExperimentPurpose.DEVELOPMENT_VALIDATION_MODEL_CANDIDATE_PILOT,
        role=DatasetRole.DEVELOPMENT_VALIDATION,
        resolved=True,
        prompt_telemetry=False,
        model_id="gpt-5.4-mini-2026-03-17",
        budget=Budget(max_total_tokens=90_000),
    )

    qualification = qualify_run(run_id, task_dir=PILOT_TASK, root=tmp_path)

    prompt_check = next(
        check for check in qualification["checks"] if check["check_id"] == "prompt_token_integrity"
    )
    assert prompt_check["passed"] is False
    assert prompt_check["details"]["required"] is True
    assert prompt_check["details"]["declared"] is False
    assert prompt_check["details"]["failed_event_sequences"] == [
        event.sequence
        for event in StateStore(tmp_path / "state.sqlite3").list_events(run_id)
        if event.type == EventType.MODEL_CALLED
    ]
    assert qualification["qualified"] is False


def test_prompt_token_count_mismatch_fails_qualification(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        prompt_telemetry=True,
        prompt_mismatch=True,
    )

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    prompt_check = next(
        check for check in qualification["checks"] if check["check_id"] == "prompt_token_integrity"
    )
    assert prompt_check["passed"] is False
    assert prompt_check["details"]["failed_event_sequences"] == [3]
    assert qualification["qualified"] is False


def test_resolved_live_pilot_is_qualified_but_not_memory_eligible(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        task_dir=PILOT_TASK,
        purpose=ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT,
        role=DatasetRole.DEVELOPMENT_VALIDATION,
        resolved=True,
        prompt_telemetry=True,
    )

    qualification = qualify_run(run_id, task_dir=PILOT_TASK, root=tmp_path)

    assert qualification["qualified"] is True
    assert qualification["purpose"] == "development-validation-live-pilot"
    assert qualification["dataset_role"] == "development-validation"
    assert qualification["outcome_kind"] == "resolved"
    assert qualification["memory_candidate_eligible"] is False


def test_primary_mini_live_pilot_requires_prompt_token_telemetry(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        task_dir=PILOT_TASK,
        purpose=ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT,
        role=DatasetRole.DEVELOPMENT_VALIDATION,
        resolved=True,
        prompt_telemetry=False,
    )

    qualification = qualify_run(run_id, task_dir=PILOT_TASK, root=tmp_path)

    prompt_check = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "prompt_token_integrity"
    )
    assert prompt_check["passed"] is False
    assert prompt_check["details"]["required"] is True
    assert qualification["qualified"] is False


def test_publicly_disclosed_private_marker_does_not_fail_leak_scan(tmp_path) -> None:
    package = load_task_package(PILOT_TASK)
    hidden_id = package.private.hidden_checks[0].id
    assert hidden_id in package.public.task_id
    assert ".patchloop-hidden" in json.dumps(package.public.model_dump(mode="json"))
    run_id, _, _ = _terminal_trace(
        tmp_path,
        task_dir=PILOT_TASK,
        purpose=ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT,
        role=DatasetRole.DEVELOPMENT_VALIDATION,
        resolved=True,
        prompt_telemetry=True,
        context_text=json.dumps(package.public.model_dump(mode="json")),
    )

    qualification = qualify_run(run_id, task_dir=PILOT_TASK, root=tmp_path)

    assert qualification["qualified"] is True
    assert qualification["leakage_scan_passed"] is True


def test_terminal_agent_failure_is_qualified_and_memory_eligible(tmp_path) -> None:
    run_id, _, failure_id = _terminal_trace(tmp_path, agent_failure=True)

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    assert qualification["qualified"] is True
    assert qualification["evaluation_reached"] is False
    assert qualification["outcome_kind"] == "agent_failure"
    assert qualification["failure_record_id"] == failure_id
    assert qualification["memory_candidate_eligible"] is True


def test_v2_model_call_budget_block_can_be_fully_qualified(
    tmp_path,
) -> None:
    run_id, _, failure_id = _terminal_trace(
        tmp_path,
        agent_failure=True,
        counter_generation_block_reason="model_call_budget_exhausted",
    )

    qualification = qualify_run(
        run_id,
        task_dir=MEMORY_TASK,
        root=tmp_path,
    )
    checks = {
        check["check_id"]: check
        for check in qualification["checks"]
    }

    assert qualification["qualified"] is True, [
        check
        for check in qualification["checks"]
        if not check["passed"]
    ]
    assert qualification["evaluation_reached"] is False
    assert qualification["outcome_kind"] == "agent_failure"
    assert qualification["failure_record_id"] == failure_id
    assert checks["prompt_token_integrity"]["passed"] is True
    assert checks["prompt_token_integrity"]["details"][
        "terminal_generation_block_schema_version"
    ] == "model-generation-block-v2"
    assert checks["prompt_token_integrity"]["details"][
        "terminal_generation_block_reason"
    ] == "model_call_budget_exhausted"
    assert checks["terminal_result_integrity"]["passed"] is True


def test_v2_counter_block_requires_durable_event_durations(
    tmp_path,
) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        agent_failure=True,
        counter_generation_block_reason="model_call_budget_exhausted",
    )
    database = tmp_path / "state.sqlite3"
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT sequence, event_json FROM events "
            "WHERE run_id = ? ORDER BY sequence",
            (run_id,),
        ).fetchall()
        sequence, raw_event = next(
            (sequence, raw_event)
            for sequence, raw_event in rows
            if json.loads(raw_event)["type"]
            == EventType.MODEL_CALLED.value
        )
        event = json.loads(raw_event)
        event["payload"].pop("duration_ms")
        connection.execute(
            "UPDATE events SET event_json = ? "
            "WHERE run_id = ? AND sequence = ?",
            (canonical_json(event), run_id, sequence),
        )

    qualification = qualify_run(
        run_id,
        task_dir=MEMORY_TASK,
        root=tmp_path,
    )
    checks = {
        check["check_id"]: check
        for check in qualification["checks"]
    }

    assert qualification["qualified"] is False
    assert checks["prompt_token_integrity"]["passed"] is False


def test_v2_counter_block_rejects_result_wall_clock_tampering(
    tmp_path,
) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        agent_failure=True,
        counter_generation_block_reason="model_call_budget_exhausted",
    )
    database = tmp_path / "state.sqlite3"
    with sqlite3.connect(database) as connection:
        raw_result = connection.execute(
            "SELECT result_json FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()[0]
        result_payload = json.loads(raw_result)
        result_payload["usage"]["wall_clock_ms"] = 123_456
        connection.execute(
            "UPDATE runs SET result_json = ? WHERE run_id = ?",
            (canonical_json(result_payload), run_id),
        )
    result_path = (
        tmp_path / "artifacts" / "runs" / run_id / "result.json"
    )
    result_path.write_text(
        json.dumps(result_payload, indent=2),
        encoding="utf-8",
    )

    qualification = qualify_run(
        run_id,
        task_dir=MEMORY_TASK,
        root=tmp_path,
    )
    checks = {
        check["check_id"]: check
        for check in qualification["checks"]
    }

    assert qualification["qualified"] is False
    assert checks["usage_reconciliation"]["passed"] is False
    assert checks["persisted_result"]["passed"] is True


def test_v2_model_call_block_rejects_over_limit_tool_usage(
    tmp_path,
) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        agent_failure=True,
        write_execution_plan=False,
        budget=Budget(
            max_model_calls=21,
            max_tool_calls=1,
            max_total_tokens=200_000,
        ),
        counter_generation_block_reason="model_call_budget_exhausted",
    )

    qualification = qualify_run(
        run_id,
        task_dir=MEMORY_TASK,
        root=tmp_path,
    )
    checks = {
        check["check_id"]: check
        for check in qualification["checks"]
    }

    assert qualification["qualified"] is False
    assert checks["prompt_token_integrity"]["passed"] is False


def test_v2_counter_block_requires_budget_guard_actor(
    tmp_path,
) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        agent_failure=True,
        counter_generation_block_reason="model_call_budget_exhausted",
    )
    database = tmp_path / "state.sqlite3"
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT sequence, event_json FROM events "
            "WHERE run_id = ? ORDER BY sequence",
            (run_id,),
        ).fetchall()
        sequence, raw_event = next(
            (sequence, raw_event)
            for sequence, raw_event in rows
            if json.loads(raw_event)["type"]
            == EventType.MODEL_GENERATION_BLOCKED.value
        )
        event = json.loads(raw_event)
        event["actor"] = "tampered-budget-guard"
        connection.execute(
            "UPDATE events SET event_json = ? "
            "WHERE run_id = ? AND sequence = ?",
            (canonical_json(event), run_id, sequence),
        )

    qualification = qualify_run(
        run_id,
        task_dir=MEMORY_TASK,
        root=tmp_path,
    )
    checks = {
        check["check_id"]: check
        for check in qualification["checks"]
    }

    assert qualification["qualified"] is False
    assert checks["prompt_token_integrity"]["passed"] is False


def test_private_token_leak_fails_without_copying_token_to_artifact(
    tmp_path,
    monkeypatch,
) -> None:
    package = load_task_package(MEMORY_TASK)
    hidden_id = package.private.hidden_checks[0].id
    api_key = "sk-test-private-qualification-key"
    monkeypatch.setenv("OPENAI_API_KEY", api_key)
    run_id, _, _ = _terminal_trace(
        tmp_path,
        context_text=f"leaked: {hidden_id} {api_key}",
    )

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)
    persisted = json.dumps(qualification, sort_keys=True)

    assert qualification["qualified"] is False
    assert qualification["leakage_scan_passed"] is False
    assert qualification["memory_candidate_eligible"] is False
    assert hidden_id not in persisted
    assert api_key not in persisted
    assert package.private.reference_patch.sha256 not in persisted


def test_undisclosed_reference_hash_still_fails_leak_scan(tmp_path) -> None:
    package = load_task_package(MEMORY_TASK)
    reference_hash = package.private.reference_patch.sha256
    assert reference_hash not in json.dumps(package.public.model_dump(mode="json"))
    run_id, _, _ = _terminal_trace(
        tmp_path,
        context_text=f"leaked oracle hash: {reference_hash}",
    )

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    assert qualification["qualified"] is False
    assert qualification["leakage_scan_passed"] is False


def test_undisclosed_hidden_artifact_hash_fails_leak_scan(tmp_path) -> None:
    package = load_task_package(V2_TASK)
    hidden_hash = package.private.hidden_artifacts[0].sha256
    assert hidden_hash not in json.dumps(package.public.model_dump(mode="json"))
    run_id, _, _ = _terminal_trace(
        tmp_path,
        task_dir=V2_TASK,
        purpose=ExperimentPurpose.CORE,
        role=DatasetRole.CORE_SAME_REPO,
        resolved=True,
        context_text=f"leaked hidden artifact hash: {hidden_hash}",
    )

    qualification = qualify_run(run_id, task_dir=V2_TASK, root=tmp_path)
    public_private = next(
        check for check in qualification["checks"] if check["check_id"] == "public_private_boundary"
    )

    assert public_private["passed"] is False
    assert qualification["leakage_scan_passed"] is False


def test_oracle_identities_remain_private_if_public_spec_is_contaminated() -> None:
    package = load_task_package(V2_TASK)
    hidden_artifact = package.private.hidden_artifacts[0]
    reference_hash = package.private.reference_patch.sha256
    contaminated_issue = package.public.issue.model_copy(
        update={
            "description": (
                f"{package.public.issue.description}\n"
                f"{reference_hash} {hidden_artifact.path} {hidden_artifact.sha256}"
            )
        }
    )
    contaminated_public = package.public.model_copy(update={"issue": contaminated_issue})
    contaminated_package = package.model_copy(update={"public": contaminated_public})

    tokens = _private_leak_tokens(contaminated_package, api_key=None)

    assert reference_hash in tokens
    assert hidden_artifact.path in tokens
    assert hidden_artifact.sha256 in tokens


def test_modified_content_addressed_artifact_fails_trace_integrity(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(tmp_path)
    object_paths = sorted(
        path
        for path in (tmp_path / "artifacts" / "objects" / "sha256").rglob("*")
        if path.is_file()
    )
    assert object_paths
    object_paths[0].write_text("modified after event persistence", encoding="utf-8")

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    assert qualification["qualified"] is False
    assert qualification["trace_integrity_passed"] is False
    artifact_check = next(
        check for check in qualification["checks"] if check["check_id"] == "agent_visible_artifacts"
    )
    assert artifact_check["passed"] is False


def test_required_event_without_artifact_identity_fails_qualification(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(tmp_path)
    database = tmp_path / "state.sqlite3"
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT event_json FROM events WHERE run_id = ? AND sequence = 2",
            (run_id,),
        ).fetchone()
        assert row is not None
        payload = json.loads(row[0])
        assert payload["type"] == EventType.CONTEXT_BUILT.value
        payload["payload"].pop("artifact_id")
        connection.execute(
            "UPDATE events SET event_json = ? WHERE run_id = ? AND sequence = 2",
            (json.dumps(payload), run_id),
        )

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    assert qualification["qualified"] is False
    artifact_check = next(
        check for check in qualification["checks"] if check["check_id"] == "agent_visible_artifacts"
    )
    assert artifact_check["passed"] is False
    assert artifact_check["details"]["missing_required_artifact_events"] == [
        EventType.CONTEXT_BUILT.value
    ]


def test_trace_without_approved_execution_plan_is_not_qualified(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(tmp_path, write_execution_plan=False)

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    assert qualification["qualified"] is False
    plan_check = next(
        check for check in qualification["checks"] if check["check_id"] == "approved_execution_plan"
    )
    assert plan_check["passed"] is False
    assert plan_check["details"]["plan_present"] is False


def test_execution_plan_schedule_row_must_match_run_manifest(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(tmp_path)
    manifest = StateStore(tmp_path / "state.sqlite3").get_manifest(run_id)
    assert manifest.experiment is not None
    plan_path = _execution_plan_path_for_test(
        tmp_path,
        manifest.experiment.execution_hash,
    )
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["schedule"][0]["dataset_role"] = DatasetRole.CORE_CROSS_REPO.value
    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    assert qualification["qualified"] is False
    plan_check = next(
        check for check in qualification["checks"] if check["check_id"] == "approved_execution_plan"
    )
    assert plan_check["passed"] is False


def test_execution_plan_private_evaluator_identity_must_match_manifest(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(tmp_path)
    manifest = StateStore(tmp_path / "state.sqlite3").get_manifest(run_id)
    assert manifest.experiment is not None
    plan_path = _execution_plan_path_for_test(
        tmp_path,
        manifest.experiment.execution_hash,
    )
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["tasks"][0]["private_spec_hash"] = "sha256:" + ("f" * 64)
    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    assert qualification["qualified"] is False
    plan_check = next(
        check for check in qualification["checks"] if check["check_id"] == "approved_execution_plan"
    )
    assert plan_check["passed"] is False


def test_execution_plan_rejects_arbitrary_self_consistent_execution_hash(
    tmp_path,
) -> None:
    run_id, _, _ = _terminal_trace(tmp_path)
    state = StateStore(tmp_path / "state.sqlite3")
    manifest = state.get_manifest(run_id)
    assert manifest.experiment is not None
    original_path = _execution_plan_path_for_test(
        tmp_path,
        manifest.experiment.execution_hash,
    )
    plan = json.loads(original_path.read_text(encoding="utf-8"))
    arbitrary_hash = "sha256:" + ("f" * 64)
    manifest.experiment.execution_hash = arbitrary_hash
    plan["execution_hash"] = arbitrary_hash
    plan["approval"]["invocation_approved_execution_hash"] = arbitrary_hash
    with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
        connection.execute(
            "UPDATE runs SET manifest_json = ? WHERE run_id = ?",
            (canonical_json(manifest.model_dump(mode="json")), run_id),
        )
    arbitrary_path = _execution_plan_path_for_test(tmp_path, arbitrary_hash)
    original_path.rename(arbitrary_path)
    arbitrary_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    plan_check = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "approved_execution_plan"
    )
    assert plan_check["passed"] is False
    assert qualification["qualified"] is False


@pytest.mark.parametrize(
    "tamper_target",
    ["environment", "schedule_hash", "pilot_qualification"],
)
def test_execution_plan_hash_inputs_cannot_be_tampered(
    tmp_path,
    tamper_target: str,
) -> None:
    run_id, _, _ = _terminal_trace(tmp_path)
    manifest = StateStore(tmp_path / "state.sqlite3").get_manifest(run_id)
    assert manifest.experiment is not None
    plan_path = _execution_plan_path_for_test(
        tmp_path,
        manifest.experiment.execution_hash,
    )
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if tamper_target == "environment":
        plan["environment"]["git"]["commit"] = "f" * 40
    elif tamper_target == "schedule_hash":
        plan["schedule_hash"] = "sha256:" + ("f" * 64)
    else:
        plan["pilot_qualification"]["qualification_hash"] = (
            "sha256:" + ("f" * 64)
        )
    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    plan_check = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "approved_execution_plan"
    )
    assert plan_check["passed"] is False
    assert qualification["qualified"] is False


def test_noncanonical_copy_of_dataset_package_is_not_qualified(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(tmp_path)
    copied_task = tmp_path / "copied-task-package"
    shutil.copytree(MEMORY_TASK, copied_task)

    qualification = qualify_run(run_id, task_dir=copied_task, root=tmp_path)

    assert qualification["qualified"] is False
    provenance_check = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "frozen_campaign_provenance"
    )
    assert provenance_check["passed"] is False
    assert provenance_check["details"]["canonical_package"] is False


def test_source_event_changed_after_qualification_cannot_be_reviewed(tmp_path) -> None:
    run_id, _, failure_id = _terminal_trace(tmp_path)
    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)
    database = tmp_path / "state.sqlite3"
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT event_json FROM events WHERE run_id = ? AND sequence = 1",
            (run_id,),
        ).fetchone()
        assert row is not None
        event = json.loads(row[0])
        event["actor"] = "tampered-after-qualification"
        connection.execute(
            "UPDATE events SET event_json = ? WHERE run_id = ? AND sequence = 1",
            (json.dumps(event), run_id),
        )

    assert qualification["source_evidence_hash"] != calculate_source_evidence_hash(
        run_id,
        root=tmp_path,
    )
    with pytest.raises(ContractError, match="source evidence changed"):
        review_failure(failure_id, root=tmp_path, approve=True)


def test_execution_plan_changed_after_qualification_cannot_be_reviewed(tmp_path) -> None:
    run_id, _, failure_id = _terminal_trace(tmp_path)
    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)
    plan_path = _execution_plan_path_for_test(tmp_path, qualification["execution_hash"])
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["audit_note"] = "changed after qualification"
    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")

    with pytest.raises(ContractError, match="source evidence changed"):
        review_failure(failure_id, root=tmp_path, approve=True)


def test_failure_symptoms_do_not_expose_hidden_check_id(tmp_path) -> None:
    package = load_task_package(MEMORY_TASK)
    hidden_id = package.private.hidden_checks[0].id
    result = _result("run_hidden_id_sanitization", resolved=False, hidden_check_id=hidden_id)

    record = classify_failure(result, package.public.split, root=tmp_path)

    assert record is not None
    assert record.observed_symptoms == ["hidden:fail"]
    assert hidden_id not in record.model_dump_json()


def test_failure_record_write_does_not_leave_partial_target(
    tmp_path,
    monkeypatch,
) -> None:
    package = load_task_package(MEMORY_TASK)
    hidden_id = package.private.hidden_checks[0].id
    result = _result(
        "run_atomic_failure_record",
        resolved=False,
        hidden_check_id=hidden_id,
    )

    def fail_replace(*_args, **_kwargs):
        raise OSError("synthetic replace failure")

    with monkeypatch.context() as context:
        context.setattr(
            "patchloop.evals.failures.os.replace",
            fail_replace,
        )
        with pytest.raises(OSError, match="synthetic replace failure"):
            classify_failure(
                result,
                package.public.split,
                root=tmp_path,
            )

    failure_dir = tmp_path / "failures" / package.public.split
    assert not list(failure_dir.glob("*.json"))
    assert not list(failure_dir.glob("*.tmp"))

    record = classify_failure(
        result,
        package.public.split,
        root=tmp_path,
    )
    assert record is not None
    path = failure_dir / f"{record.failure_id}.json"
    assert json.loads(path.read_text(encoding="utf-8"))["failure_id"] == (record.failure_id)


def test_unqualified_failure_cannot_enter_review_history(tmp_path) -> None:
    _, _, failure_id = _terminal_trace(tmp_path)
    failure_path = tmp_path / "failures" / "dev-train" / f"{failure_id}.json"
    original = failure_path.read_bytes()

    with pytest.raises(ContractError, match="qualification is unavailable"):
        review_failure(failure_id, root=tmp_path, approve=True)

    assert failure_path.read_bytes() == original
    assert not failure_path.with_suffix(".review-history.jsonl").exists()


def test_failure_record_changed_after_qualification_cannot_be_reviewed(tmp_path) -> None:
    run_id, _, failure_id = _terminal_trace(tmp_path)
    qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)
    failure_path = tmp_path / "failures" / "dev-train" / f"{failure_id}.json"
    record = json.loads(failure_path.read_text(encoding="utf-8"))
    record["confidence"] = 0.5
    failure_path.write_text(json.dumps(record, indent=2), encoding="utf-8")

    with pytest.raises(ContractError, match="changed after trace qualification"):
        review_failure(failure_id, root=tmp_path, approve=True)
