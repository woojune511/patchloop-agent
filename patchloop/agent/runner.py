"""Durable single-agent loop with deterministic evaluation and recovery."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from patchloop.agent.context import build_context_with_evidence
from patchloop.agent.model import (
    SYSTEM_PROMPT_V1,
    SYSTEM_PROMPT_V2,
    MockModelAdapter,
    ModelAdapter,
    OpenAIResponsesAdapter,
    ReplayModelAdapter,
)
from patchloop.agent.phases import diff_bound_evidence, validate_transition
from patchloop.agent.tools import (
    TOOL_SCHEMAS_V1,
    TOOL_SCHEMAS_V2,
    ToolGateway,
)
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import (
    Artifact,
    Budget,
    Checkpoint,
    EventType,
    ExperimentRunContext,
    MemoryCondition,
    Phase,
    PublicTask,
    RunManifest,
    RunOutcomeKind,
    RunResult,
    RunStatus,
    TaskPackage,
    ToolResult,
    Usage,
    Verdicts,
)
from patchloop.errors import (
    ContractError,
    InjectedFault,
    RecoveryError,
    SubmissionProtocolError,
)
from patchloop.evals.failures import classify_failure
from patchloop.memory import retrieve_memory
from patchloop.repository import WorkspaceManager
from patchloop.runtime import (
    build_manifest,
    calculate_model_cost,
    repository_root,
    runtime_root,
)
from patchloop.sandbox import DockerSandbox, LocalSandbox, TimeoutOnceSandbox
from patchloop.state import StateStore
from patchloop.task_loader import load_task_package
from patchloop.util import (
    canonical_json,
    ensure_within,
    safe_relative_path,
    sha256_bytes,
    sha256_text,
    utc_now,
)
from patchloop.verifier import EvaluationEngine

_LIVE_AUTHORIZATION_GUARD = object()
_MAX_RECOVERABLE_SUBMISSION_REJECTIONS = 2


@dataclass(frozen=True)
class LiveExecutionAuthorization:
    """Ephemeral capability issued only after an approved live preflight."""

    execution_hash: str
    plan_path: str
    plan_hash: str
    _guard: object


def issue_live_execution_authorization(
    execution_hash: str,
    *,
    root: str | Path | None = None,
) -> LiveExecutionAuthorization:
    """Issue a capability only when the approved execution plan is durable."""

    if re.fullmatch(r"sha256:[0-9a-f]{64}", execution_hash) is None:
        raise ContractError("live execution hash must be a SHA-256 identity")
    plan_path = (
        Path(root) if root is not None else runtime_root()
    ) / "experiments" / "plans" / f"{execution_hash.removeprefix('sha256:')}.json"
    try:
        plan_bytes = plan_path.read_bytes()
        plan = json.loads(plan_bytes)
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(
            "live execution capability requires a persisted approved execution plan"
        ) from exc
    approval = plan.get("approval") if isinstance(plan, dict) else None
    if (
        not isinstance(plan, dict)
        or plan.get("schema_version") != "experiment-execution-plan-v1"
        or plan.get("ready") is not True
        or plan.get("blockers") != []
        or plan.get("execution_hash") != execution_hash
        or not isinstance(approval, dict)
        or approval.get("invocation_approve_live_cost") is not True
        or approval.get("invocation_approved_execution_hash") != execution_hash
        or approval.get("matches_execution_hash") is not True
    ):
        raise ContractError(
            "persisted execution plan does not authorize this live execution hash"
        )
    return LiveExecutionAuthorization(
        execution_hash=execution_hash,
        plan_path=str(plan_path),
        plan_hash=sha256_bytes(plan_bytes),
        _guard=_LIVE_AUTHORIZATION_GUARD,
    )


class AgentRunner:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root else runtime_root()
        self.state = StateStore(self.root / "state.sqlite3")
        self.artifacts = ArtifactStore(self.root / "artifacts")
        self.workspaces = WorkspaceManager(
            repository_root() / "fixtures" / "repositories", self.root / "workspaces"
        )

    def start(
        self,
        task_path: str | Path,
        *,
        model: str = "mock",
        memory_condition: MemoryCondition = MemoryCondition.NO_MEMORY,
        manifest: RunManifest | None = None,
        input_price_per_million_usd: float | None = None,
        cached_input_price_per_million_usd: float | None = None,
        cache_write_input_price_per_million_usd: float | None = None,
        output_price_per_million_usd: float | None = None,
        model_id: str | None = None,
        reasoning_effort: str = "medium",
        reasoning_mode: str = "standard",
        service_tier: str = "default",
        max_output_tokens: int = 4096,
        budget: Budget | None = None,
        experiment_context: ExperimentRunContext | None = None,
        live_authorization: LiveExecutionAuthorization | None = None,
    ) -> dict[str, Any]:
        task_dir = self._task_dir(task_path)
        package = load_task_package(task_dir)
        normalized_model = model
        replay_hash = None
        if model.startswith("replay:"):
            normalized_model, _, replay_hash = self._replay_identity(model)
            selected_provider = "replay"
        elif model in {"mock", "openai"}:
            selected_provider = model
        else:
            raise ContractError(f"unknown model adapter: {model}")

        if manifest is not None:
            package_identity = (
                package.public.task_id,
                package.public.task_version,
                package.public.repository.base_commit,
                package.public_spec_hash,
                package.private_spec_hash,
            )
            manifest_identity = (
                manifest.task_id,
                manifest.task_version,
                manifest.base_commit,
                manifest.public_spec_hash,
                manifest.private_spec_hash,
            )
            if package_identity != manifest_identity:
                raise ContractError(
                    "task package does not match the immutable run manifest"
                )
        if manifest is not None and manifest.model.provider != selected_provider:
            raise ContractError(
                "model selector does not match the immutable run manifest provider"
            )
        if selected_provider == "openai":
            self._require_live_authorization(manifest, live_authorization)

        if manifest is not None and not self.state.has_run(manifest.run_id):
            self.state.create_run(manifest)

        try:
            docker_sandbox = self._docker_sandbox(package)
            backend = (
                "docker"
                if DockerSandbox.available() and docker_sandbox.image_identity() is not None
                else "local"
            )
            if package.environment is not None:
                image_identity = docker_sandbox.image_identity()
                if backend != "docker":
                    raise ContractError(
                        "task requires its digest-pinned Docker evaluator image, "
                        "but it is unavailable"
                    )
                if image_identity != package.environment.image_digest:
                    raise ContractError(
                        "task evaluator image identity does not match environment.yaml: "
                        f"{image_identity} != {package.environment.image_digest}"
                    )
            if manifest is None:
                selected_model_id = (
                    "mock-v1" if selected_provider == "mock" else normalized_model
                )
                image_identity = (
                    docker_sandbox.image_identity() if backend == "docker" else None
                )
                manifest = build_manifest(
                    package,
                    provider=selected_provider,
                    model_id=selected_model_id,
                    memory_condition=memory_condition,
                    sandbox_backend=backend,
                    agent_image_digest=image_identity,
                    evaluator_image_digest=image_identity,
                    input_price_per_million_usd=input_price_per_million_usd,
                    cached_input_price_per_million_usd=cached_input_price_per_million_usd,
                    cache_write_input_price_per_million_usd=(
                        cache_write_input_price_per_million_usd
                    ),
                    output_price_per_million_usd=output_price_per_million_usd,
                    reasoning_effort=reasoning_effort,
                    reasoning_mode=reasoning_mode,
                    service_tier=service_tier,
                    max_output_tokens=max_output_tokens,
                    budget=budget,
                    replay_hash=replay_hash,
                    experiment_context=experiment_context,
                )
                self.state.create_run(manifest)
            workspace = self.root / "workspaces" / manifest.run_id / "repo"
            if not workspace.exists():
                workspace = self.workspaces.create(
                    manifest.run_id,
                    package.public.repository.url,
                    package.public.repository.base_commit,
                )
            elif self.state.list_events(manifest.run_id):
                self._reconcile_workspace(manifest, workspace)
            adapter = self._model_adapter(
                normalized_model, manifest, self._completed_tools(manifest.run_id)
            )
            return self._execute(package, workspace, manifest, adapter)
        except Exception as exc:
            if manifest is None or not self.state.has_run(manifest.run_id):
                raise
            events = self.state.list_events(manifest.run_id)
            if any(
                event.type in {EventType.RUN_COMPLETED, EventType.RUN_FAILED}
                for event in events
            ):
                raise
            checkpoint = self.state.latest_checkpoint(manifest.run_id)
            self._terminal_failure(
                task_dir,
                manifest,
                checkpoint.phase if checkpoint is not None else Phase.INTAKE,
                self._usage(manifest.run_id),
                exc,
                RunOutcomeKind.INFRASTRUCTURE_ERROR,
            )
            raise

    def resume(
        self,
        run_id: str,
        *,
        live_authorization: LiveExecutionAuthorization | None = None,
    ) -> dict[str, Any]:
        manifest = self.state.get_manifest(run_id)
        run_rows = [row for row in self.state.list_runs() if row["run_id"] == run_id]
        if len(run_rows) != 1 or run_rows[0]["status"] != RunStatus.SUSPENDED.value:
            raise RecoveryError("only a suspended run may be resumed")
        task_dir = self._find_task(manifest)
        if manifest.model.provider == "mock":
            model = "mock"
        elif manifest.model.provider == "replay":
            model = manifest.model.model_id
        else:
            model = "openai"
        return self.start(
            task_dir,
            model=model,
            memory_condition=manifest.memory.condition,
            manifest=manifest,
            live_authorization=live_authorization,
        )

    @staticmethod
    def _require_live_authorization(
        manifest: RunManifest | None,
        authorization: LiveExecutionAuthorization | None,
    ) -> None:
        if (
            manifest is None
            or manifest.experiment is None
            or authorization is None
            or authorization._guard is not _LIVE_AUTHORIZATION_GUARD
            or authorization.execution_hash != manifest.experiment.execution_hash
            or not AgentRunner._live_plan_unchanged(authorization)
        ):
            raise ContractError(
                "live model execution requires an approved experiment execution capability"
            )

    @staticmethod
    def _live_plan_unchanged(authorization: LiveExecutionAuthorization) -> bool:
        try:
            return sha256_bytes(Path(authorization.plan_path).read_bytes()) == (
                authorization.plan_hash
            )
        except OSError:
            return False

    def _execute(
        self,
        package: TaskPackage,
        workspace: Path,
        manifest: RunManifest,
        adapter: ModelAdapter,
    ) -> dict[str, Any]:
        task_dir = package.root
        system_prompt, tool_schemas = self._runtime_contract(manifest)
        sandbox = (
            self._docker_sandbox(package)
            if manifest.sandbox_backend == "docker"
            else LocalSandbox()
        )
        if (
            package.environment is not None
            and manifest.evaluator_image_digest != package.environment.image_digest
        ):
            raise ContractError("run manifest evaluator image does not match the task environment")
        gateway_sandbox = (
            TimeoutOnceSandbox(sandbox) if manifest.fault.type == "test-timeout" else sandbox
        )
        gateway = ToolGateway(
            run_id=manifest.run_id,
            workspace=workspace,
            task=package.public,
            state=self.state,
            artifacts=self.artifacts,
            sandbox=gateway_sandbox,
        )
        self.state.set_run_status(manifest.run_id, RunStatus.RUNNING)
        if not self.state.list_events(manifest.run_id):
            runtime_contract = self.artifacts.put_json(
                {
                    "system_prompt": system_prompt,
                    "tools": tool_schemas,
                    "tool_schema_version": manifest.tool_schema_version,
                    "context_policy_version": manifest.context_policy_version,
                }
            )
            self.state.append_event(
                manifest.run_id,
                EventType.RUN_STARTED,
                actor="runner",
                payload={
                    "task_id": manifest.task_id,
                    "artifact_id": runtime_contract.artifact_id,
                    "artifact_path": runtime_contract.path,
                    "artifact_role": "runtime-contract",
                },
            )
            if manifest.fault.type in {"context-reset", "test-timeout"}:
                self.state.append_event(
                    manifest.run_id,
                    EventType.FAULT_INJECTED,
                    actor="fault-injector",
                    payload={"fault": manifest.fault.type},
                )
        checkpoint = self.state.latest_checkpoint(manifest.run_id)
        phase = checkpoint.phase if checkpoint else Phase.INTAKE
        if phase == Phase.INTAKE:
            phase = self._transition(manifest.run_id, phase, Phase.REPRODUCE)
            checkpoint = self._checkpoint(
                manifest,
                workspace,
                phase,
                task=package.public,
            )

        usage = self._usage(manifest.run_id)
        try:
            phase, checkpoint, recovered_submission = (
                self._reconcile_submission_recovery(
                    manifest=manifest,
                    task=package.public,
                    workspace=workspace,
                    phase=phase,
                    usage=usage,
                )
            )
            usage = self._usage(manifest.run_id)
            if recovered_submission is not None:
                return self._evaluate(
                    task_dir,
                    workspace,
                    manifest,
                    sandbox,
                    usage,
                )
            while True:
                self._assert_budget(manifest, usage)
                events = self.state.list_events(manifest.run_id)
                memory_text, retrieval = retrieve_memory(
                    run_id=manifest.run_id,
                    query=(
                        package.public.issue.title
                        + "\n"
                        + package.public.issue.description
                        + "\n"
                        + " ".join(package.public.tags)
                    ),
                    phase=phase,
                    condition=manifest.memory.condition,
                    token_budget=manifest.memory.max_context_tokens,
                )
                if retrieval is not None:
                    retrieval_artifact = self.artifacts.put_json(retrieval.model_dump(mode="json"))
                    self.state.append_event(
                        manifest.run_id,
                        EventType.MEMORY_RETRIEVED,
                        actor="memory-retriever",
                        payload={
                            "index_version": retrieval.index_version,
                            "selected_memory_ids": retrieval.selected_memory_ids,
                            "no_match": retrieval.no_match,
                            "artifact_id": retrieval_artifact.artifact_id,
                            "artifact_path": retrieval_artifact.path,
                        },
                    )
                built_context = build_context_with_evidence(
                    package.public,
                    events,
                    checkpoint,
                    memory_text,
                    policy_version=manifest.context_policy_version,
                )
                context = built_context.rendered
                if isinstance(adapter, OpenAIResponsesAdapter):
                    request_body = adapter.request_payload(
                        context,
                        tool_schemas,
                        system_prompt=system_prompt,
                    )
                    request_endpoint = "/v1/responses"
                else:
                    request_body = {
                        "model": manifest.model.model_id,
                        "system_prompt": system_prompt,
                        "context": context,
                        "tools": tool_schemas,
                    }
                    request_endpoint = None
                request_body_hash = sha256_text(canonical_json(request_body))
                request_artifact = self.artifacts.put_json(
                    {
                        "schema_version": "model-request-evidence-v1",
                        "provider": manifest.model.provider,
                        "endpoint": request_endpoint,
                        "request_body": request_body,
                        "request_body_hash": request_body_hash,
                        "context_build": built_context.evidence,
                    }
                )
                self.state.append_event(
                    manifest.run_id,
                    EventType.CONTEXT_BUILT,
                    actor="context-builder",
                    payload={
                        "context_hash": built_context.content_hash,
                        "context_characters": built_context.evidence[
                            "rendered_characters"
                        ],
                        "context_bytes": built_context.evidence["rendered_bytes"],
                        "eligible_event_count": built_context.evidence["events"][
                            "eligible_count"
                        ],
                        "included_event_count": built_context.evidence["events"][
                            "included_count"
                        ],
                        "omitted_event_count": built_context.evidence["events"][
                            "omitted_count"
                        ],
                        "truncated_tool_result_count": sum(
                            bool(item["truncated"])
                            for item in built_context.evidence["tool_results"]
                        ),
                        "request_body_hash": request_body_hash,
                        "artifact_id": request_artifact.artifact_id,
                        "artifact_path": request_artifact.path,
                        "artifact_role": "model-request-evidence",
                        "provider_state_used": False,
                    },
                )
                model_started = time.monotonic()
                if isinstance(adapter, OpenAIResponsesAdapter):
                    requested_input_tokens = adapter.count_input_tokens(request_body)
                    remaining_tokens = (
                        manifest.budget.max_total_tokens
                        - usage.input_tokens
                        - usage.output_tokens
                    )
                    if (
                        requested_input_tokens + manifest.model.max_output_tokens
                        > remaining_tokens
                    ):
                        raise ContractError(
                            "remaining token budget cannot fund the exact input "
                            "plus one bounded model response"
                        )
                    turn = adapter.execute_request(
                        request_body,
                        requested_input_tokens=requested_input_tokens,
                    )
                else:
                    turn = adapter.next_turn(context, tool_schemas)
                model_duration_ms = int((time.monotonic() - model_started) * 1000)
                usage.model_calls += 1
                usage.input_tokens += turn.input_tokens
                usage.cached_input_tokens += turn.cached_input_tokens
                usage.cache_write_input_tokens += turn.cache_write_input_tokens
                usage.output_tokens += turn.output_tokens
                usage.reasoning_output_tokens += turn.reasoning_output_tokens
                usage.input_token_count_calls += turn.input_token_count_calls
                usage.wall_clock_ms += model_duration_ms
                turn_artifact = self.artifacts.put_json(
                    {
                        "text": turn.text,
                        "done": turn.done,
                        "tool_calls": [call.__dict__ for call in turn.tool_calls],
                        "response_id": turn.response_id,
                        "response_model": turn.response_model,
                        "response_service_tier": turn.response_service_tier,
                        "system_fingerprint": turn.system_fingerprint,
                        "response_status": turn.response_status,
                        "response_truncation": turn.response_truncation,
                        "response_incomplete_reason": turn.response_incomplete_reason,
                        "requested_input_tokens": turn.requested_input_tokens,
                        "input_tokens": turn.input_tokens,
                        "cached_input_tokens": turn.cached_input_tokens,
                        "cache_write_input_tokens": turn.cache_write_input_tokens,
                        "output_tokens": turn.output_tokens,
                        "reasoning_output_tokens": turn.reasoning_output_tokens,
                        "total_tokens": turn.total_tokens,
                        "input_token_count_match": turn.input_token_count_match,
                        "total_token_count_match": turn.total_token_count_match,
                        "response_error": (
                            {
                                "code": turn.error.code,
                                "message": turn.error.message,
                            }
                            if turn.error is not None
                            else None
                        ),
                    }
                )
                model_event = self.state.append_event(
                    manifest.run_id,
                    EventType.MODEL_CALLED,
                    actor="model-adapter",
                    payload={
                        "model": manifest.model.model_id,
                        "store": False,
                        "previous_response_id_used": False,
                        "input_tokens": turn.input_tokens,
                        "cached_input_tokens": turn.cached_input_tokens,
                        "cache_write_input_tokens": turn.cache_write_input_tokens,
                        "output_tokens": turn.output_tokens,
                        "reasoning_output_tokens": turn.reasoning_output_tokens,
                        "total_tokens": turn.total_tokens,
                        "requested_input_tokens": turn.requested_input_tokens,
                        "input_token_count_match": turn.input_token_count_match,
                        "total_token_count_match": turn.total_token_count_match,
                        "input_token_count_calls": turn.input_token_count_calls,
                        "prompt_telemetry_version": (
                            "prompt-token-integrity-v1"
                            if turn.requested_input_tokens is not None
                            else None
                        ),
                        "request_artifact_id": request_artifact.artifact_id,
                        "request_artifact_path": request_artifact.path,
                        "request_artifact_hash": request_artifact.content_hash,
                        "request_body_hash": request_body_hash,
                        "response_model": turn.response_model,
                        "response_service_tier": turn.response_service_tier,
                        "system_fingerprint": turn.system_fingerprint,
                        "response_status": turn.response_status,
                        "response_truncation": turn.response_truncation,
                        "response_incomplete_reason": turn.response_incomplete_reason,
                        "response_error_code": (
                            turn.error.code if turn.error is not None else None
                        ),
                        "artifact_id": turn_artifact.artifact_id,
                        "artifact_path": turn_artifact.path,
                        "duration_ms": model_duration_ms,
                    },
                )
                self._assert_consumed_budget(manifest, usage)
                if turn.error is not None:
                    raise ContractError(
                        f"model response rejected: {turn.error.code}"
                    )
                if turn.done:
                    if manifest.tool_schema_version == "v1":
                        self._validate_legacy_submission(
                            package.public,
                            manifest.run_id,
                            phase,
                        )
                        phase = self._transition(
                            manifest.run_id,
                            phase,
                            Phase.DONE,
                        )
                        checkpoint = self._checkpoint(
                            manifest,
                            workspace,
                            phase,
                            usage,
                            task=package.public,
                        )
                        return self._evaluate(
                            task_dir,
                            workspace,
                            manifest,
                            sandbox,
                            usage,
                        )
                    should_stop = self._reject_unstructured_submission(
                        manifest.run_id,
                        workspace,
                        correlation_id=model_event.event_id,
                    )
                    checkpoint = self._checkpoint(
                        manifest,
                        workspace,
                        phase,
                        usage,
                        task=package.public,
                    )
                    if should_stop:
                        raise SubmissionProtocolError(
                            "structured finish_task submission was rejected "
                            "three times"
                        )
                    continue
                if not turn.tool_calls:
                    raise ContractError(
                        "model returned neither a tool call nor a submission"
                    )
                finish_calls = [
                    call
                    for call in turn.tool_calls
                    if call.name == "finish_task"
                ]
                if finish_calls and len(turn.tool_calls) != 1:
                    if usage.tool_calls >= manifest.budget.max_tool_calls:
                        raise ContractError("tool call budget exhausted")
                    finish_call = finish_calls[0]
                    result, _, should_stop = self._finish_task(
                        run_id=manifest.run_id,
                        task=package.public,
                        workspace=workspace,
                        phase=phase,
                        action_id=finish_call.action_id,
                        arguments=finish_call.arguments,
                        context_evidence=built_context.evidence,
                        request_artifact_id=request_artifact.artifact_id,
                        additional_missing_evidence=[
                            "finish_task_must_be_only_action"
                        ],
                    )
                    if not result.output.get("replayed"):
                        usage.tool_calls += 1
                        usage.wall_clock_ms += int(
                            (
                                result.finished_at - result.started_at
                            ).total_seconds()
                            * 1000
                        )
                    checkpoint = self._checkpoint(
                        manifest,
                        workspace,
                        phase,
                        usage,
                        result,
                        task=package.public,
                    )
                    if should_stop:
                        raise SubmissionProtocolError(
                            "submission preconditions were rejected three times"
                        )
                    continue
                for call in turn.tool_calls:
                    if usage.tool_calls >= manifest.budget.max_tool_calls:
                        raise ContractError("tool call budget exhausted")
                    if call.name == "finish_task":
                        if manifest.tool_schema_version != "v2":
                            raise ContractError(
                                "finish_task is unavailable in tool schema v1"
                            )
                        result, accepted, should_stop = self._finish_task(
                            run_id=manifest.run_id,
                            task=package.public,
                            workspace=workspace,
                            phase=phase,
                            action_id=call.action_id,
                            arguments=call.arguments,
                            context_evidence=built_context.evidence,
                            request_artifact_id=request_artifact.artifact_id,
                            additional_missing_evidence=[],
                        )
                        if not result.output.get("replayed"):
                            usage.tool_calls += 1
                            usage.wall_clock_ms += int(
                                (
                                    result.finished_at - result.started_at
                                ).total_seconds()
                                * 1000
                            )
                        if isinstance(adapter, MockModelAdapter) and (
                            result.status == "succeeded"
                        ):
                            adapter.record_completed(call.name)
                        if accepted:
                            phase, checkpoint = (
                                self._complete_accepted_submission(
                                    manifest=manifest,
                                    task=package.public,
                                    workspace=workspace,
                                    phase=phase,
                                    usage=usage,
                                    result=result,
                                )
                            )
                        else:
                            checkpoint = self._checkpoint(
                                manifest,
                                workspace,
                                phase,
                                usage,
                                result,
                                task=package.public,
                            )
                        if should_stop:
                            raise SubmissionProtocolError(
                                "submission preconditions were rejected three times"
                            )
                        if accepted:
                            return self._evaluate(
                                task_dir,
                                workspace,
                                manifest,
                                sandbox,
                                usage,
                            )
                        continue
                    result = gateway.execute(call.name, call.action_id, call.arguments)
                    if not result.output.get("replayed"):
                        usage.tool_calls += 1
                        usage.wall_clock_ms += int(
                            (result.finished_at - result.started_at).total_seconds() * 1000
                        )
                    if isinstance(adapter, MockModelAdapter) and result.status == "succeeded":
                        adapter.record_completed(call.name)
                    if (
                        result.status == "failed"
                        and result.output.get("fatal") is True
                    ):
                        raise RecoveryError(
                            result.error_message
                            or "tool execution failed with a fatal state error"
                        )
                    phase = self._phase_after_tool(
                        manifest.run_id,
                        phase,
                        call.name,
                        result,
                        package.public,
                        workspace,
                    )
                    checkpoint = self._checkpoint(
                        manifest,
                        workspace,
                        phase,
                        usage,
                        result,
                        task=package.public,
                    )
                    if (
                        call.name == "run_check"
                        and result.status == "succeeded"
                        and result.output.get("timed_out") is True
                    ):
                        raise ContractError(
                            "visible check timed out; the unchanged command "
                            "will not be repeated"
                        )
                    if (
                        manifest.fault.type == "worker-kill-after-patch"
                        and call.name == "apply_patch"
                        and result.status == "succeeded"
                    ):
                        self.state.append_event(
                            manifest.run_id,
                            EventType.FAULT_INJECTED,
                            actor="fault-injector",
                            payload={
                                "fault": manifest.fault.type,
                                "after_action": call.action_id,
                            },
                        )
                        raise InjectedFault(
                            "worker terminated immediately after durable patch checkpoint"
                        )
        except InjectedFault as exc:
            self.state.set_run_status(manifest.run_id, RunStatus.SUSPENDED)
            return {
                "run_id": manifest.run_id,
                "status": "suspended",
                "fault": manifest.fault.type,
                "message": str(exc),
                "resume_command": f"patchloop resume --run-id {manifest.run_id}",
            }
        except Exception as exc:
            outcome_kind = (
                RunOutcomeKind.AGENT_FAILURE
                if isinstance(exc, ContractError)
                else RunOutcomeKind.INFRASTRUCTURE_ERROR
            )
            return self._terminal_failure(
                task_dir,
                manifest,
                phase,
                usage,
                exc,
                outcome_kind,
            )

    def _evaluate(
        self,
        task_dir: str | Path,
        workspace: Path,
        manifest: RunManifest,
        sandbox: DockerSandbox | LocalSandbox,
        usage: Usage,
    ) -> dict[str, Any]:
        usage.model_cost_usd = calculate_model_cost(usage, manifest.model)
        summary = WorkspaceManager.diff_summary(workspace)
        submitted_patch_artifact: Artifact | None = None
        if manifest.tool_schema_version == "v2":
            accepted_events = [
                event
                for event in self.state.list_events(manifest.run_id)
                if event.type == EventType.SUBMISSION_ACCEPTED
            ]
            if len(accepted_events) != 1:
                raise RecoveryError(
                    "v2 evaluation requires one accepted submission"
                )
            try:
                submitted_patch_artifact = Artifact.model_validate(
                    accepted_events[0].payload["submitted_patch_artifact"]
                )
                submitted_patch_bytes = Path(
                    submitted_patch_artifact.path
                ).read_bytes()
            except (KeyError, OSError, TypeError, ValueError) as exc:
                raise RecoveryError(
                    "accepted submission patch artifact is unavailable"
                ) from exc
            if (
                submitted_patch_artifact.content_hash
                != accepted_events[0].payload.get("worktree_diff_hash")
                or sha256_bytes(submitted_patch_bytes)
                != submitted_patch_artifact.content_hash
                or summary.patch_hash
                != submitted_patch_artifact.content_hash
            ):
                raise RecoveryError(
                    "accepted patch artifact, event, and worktree differ"
                )
        else:
            submitted_patch_bytes = summary.patch.encode("utf-8")
        run_dir = self.root / "runs" / manifest.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        patch_path = run_dir / "submitted.patch"
        patch_path.write_bytes(submitted_patch_bytes)
        evaluator = EvaluationEngine(self.workspaces, sandbox, self.artifacts)
        evaluator_started = time.monotonic()
        result = evaluator.evaluate(
            task_dir,
            patch_path,
            manifest,
            usage=usage,
            submitted_patch_artifact=submitted_patch_artifact,
        )
        evaluator_duration_ms = int((time.monotonic() - evaluator_started) * 1000)
        failure = classify_failure(
            result,
            load_task_package(task_dir).public.split,
            root=self.root,
            phase=Phase.REVIEW,
            events=self.state.list_events(manifest.run_id),
        )
        if failure is not None:
            self.state.append_event(
                manifest.run_id,
                EventType.FAILURE_TAGGED,
                actor="failure-classifier",
                payload={
                    "failure_id": failure.failure_id,
                    "primary_cause": failure.primary_cause,
                    "classification_method": failure.classification_method,
                },
            )
        self.state.append_event(
            manifest.run_id,
            EventType.RUN_COMPLETED,
            actor="evaluator",
            payload={
                "scope_compliant_success": result.scope_compliant_success,
                "official": result.official,
                "duration_ms": evaluator_duration_ms,
            },
        )
        self.state.set_run_status(
            manifest.run_id, RunStatus.COMPLETED, result.model_dump(mode="json")
        )
        return result.model_dump(mode="json")

    def _terminal_failure(
        self,
        task_dir: str | Path,
        manifest: RunManifest,
        phase: Phase,
        usage: Usage,
        error: Exception,
        outcome_kind: RunOutcomeKind,
    ) -> dict[str, Any]:
        """Persist a schema-valid terminal attempt even when evaluation is not reached."""

        usage.model_cost_usd = calculate_model_cost(usage, manifest.model)
        safe_message = self._safe_error_message(error)
        events = self.state.list_events(manifest.run_id)
        submission_accepted = any(
            event.type == EventType.SUBMISSION_ACCEPTED for event in events
        )
        result = RunResult(
            run_id=manifest.run_id,
            agent_submission_status=(
                "completed" if submission_accepted else "failed"
            ),
            evaluation_status="not_run",
            scope_compliant_success=False,
            official=False,
            verdicts=Verdicts(),
            usage=usage,
            outcome_kind=outcome_kind,
            terminal_error={
                "type": type(error).__name__,
                "message": safe_message,
            },
        )
        failure = classify_failure(
            result,
            load_task_package(task_dir).public.split,
            root=self.root,
            phase=phase,
            events=events,
        )
        if failure is not None:
            self.state.append_event(
                manifest.run_id,
                EventType.FAILURE_TAGGED,
                actor="failure-classifier",
                payload={
                    "failure_id": failure.failure_id,
                    "primary_cause": failure.primary_cause,
                    "classification_method": failure.classification_method,
                },
            )
        self.state.append_event(
            manifest.run_id,
            EventType.RUN_FAILED,
            actor="runner",
            payload={
                "outcome_kind": outcome_kind.value,
                "error_type": type(error).__name__,
                "message": safe_message,
                "model_cost_usd": usage.model_cost_usd,
            },
        )
        self.state.set_run_status(
            manifest.run_id,
            RunStatus.FAILED,
            result.model_dump(mode="json"),
        )
        run_dir = self.artifacts.root / "runs" / manifest.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "manifest.json").write_text(
            manifest.model_dump_json(indent=2),
            encoding="utf-8",
        )
        (run_dir / "result.json").write_text(
            result.model_dump_json(indent=2),
            encoding="utf-8",
        )
        (run_dir / "provenance.json").write_text(
            json.dumps(
                {
                    "evaluation_reached": False,
                    "outcome_kind": outcome_kind.value,
                    "error_type": type(error).__name__,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return result.model_dump(mode="json")

    @staticmethod
    def _safe_error_message(error: Exception) -> str:
        message = str(error)
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            message = message.replace(api_key, "[REDACTED]")
        return message[:2_000]

    def _checkpoint(
        self,
        manifest: RunManifest,
        workspace: Path,
        phase: Phase,
        usage: Usage | None = None,
        last_result: ToolResult | None = None,
        *,
        task: PublicTask | None = None,
    ) -> Checkpoint:
        if WorkspaceManager.untracked_files(workspace):
            raise RecoveryError(
                "agent workspace contains untracked files at checkpoint"
            )
        summary = WorkspaceManager.diff_summary(workspace)
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=workspace,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        completed_actions = list(
            dict.fromkeys(
                event.correlation_id
                for event in self.state.list_events(manifest.run_id)
                if event.type == EventType.TOOL_SUCCEEDED and event.correlation_id
            )
        )
        events = self.state.list_events(manifest.run_id)
        if manifest.context_policy_version == "phase-evidence-v2":
            evidence = diff_bound_evidence(
                task or load_task_package(self._find_task(manifest)).public,
                events,
                summary.patch_hash,
            )
            completed_checks = list(evidence.completed_checks)
            pending_checks = list(evidence.pending_checks)
            # The next model context recalculates presented-result evidence.
            # Avoid persisting a stale tool prescription in the checkpoint.
            current_plan = []
            patch_events = [
                event
                for event in events
                if event.type == EventType.PATCH_APPLIED
                and event.payload.get("patch_hash")
            ]
            last_patch_hash = (
                str(patch_events[-1].payload["patch_hash"])
                if patch_events
                else None
            )
            important_decisions = [
                {
                    "event_sequence": event.sequence,
                    "type": event.type.value,
                    "reason_code": event.payload.get("reason_code"),
                    "worktree_diff_hash": event.payload.get(
                        "worktree_diff_hash"
                    ),
                }
                for event in events
                if event.type
                in {
                    EventType.REVIEW_RECORDED,
                    EventType.SUBMISSION_REJECTED,
                    EventType.SUBMISSION_ACCEPTED,
                }
            ][-5:]
        else:
            completed_checks = list(
                dict.fromkeys(
                    str(event.payload["check_id"])
                    for event in events
                    if event.type == EventType.TOOL_SUCCEEDED
                    and event.payload.get("tool") == "run_check"
                    and event.payload.get("passed") is True
                    and event.payload.get("check_id")
                )
            )
            pending_checks = []
            current_plan = []
            important_decisions = []
            last_patch_hash = (
                last_result.output.get("patch_hash")
                if last_result and last_result.status == "succeeded"
                else None
            )
        usage = usage or Usage()
        checkpoint = Checkpoint(
            checkpoint_id=f"ckpt_{uuid.uuid4().hex}",
            run_id=manifest.run_id,
            through_sequence=self.state.last_sequence(manifest.run_id),
            phase=phase,
            task_summary=manifest.task_id,
            current_plan=current_plan,
            modified_files=summary.changed_files,
            completed_action_ids=completed_actions,
            completed_checks=completed_checks,
            pending_checks=pending_checks,
            important_decisions=important_decisions,
            repository_head=head,
            worktree_diff_hash=summary.patch_hash,
            last_patch_hash=last_patch_hash,
            remaining_budget={
                "model_calls": manifest.budget.max_model_calls - usage.model_calls,
                "tool_calls": manifest.budget.max_tool_calls - usage.tool_calls,
                "tokens": manifest.budget.max_total_tokens
                - usage.input_tokens
                - usage.output_tokens,
            },
            created_at=utc_now(),
        )
        self.state.save_checkpoint(checkpoint)
        self.state.append_event(
            manifest.run_id,
            EventType.CHECKPOINT_SAVED,
            actor="state-store",
            payload={
                "checkpoint_id": checkpoint.checkpoint_id,
                "through_sequence": checkpoint.through_sequence,
                "worktree_diff_hash": checkpoint.worktree_diff_hash,
            },
        )
        return checkpoint

    def _transition(self, run_id: str, current: Phase, target: Phase) -> Phase:
        validate_transition(current, target)
        self.state.append_event(
            run_id,
            EventType.PHASE_CHANGED,
            actor="phase-machine",
            payload={"from": current.value, "to": target.value},
        )
        return target

    @staticmethod
    def _runtime_contract(
        manifest: RunManifest,
    ) -> tuple[str, list[dict[str, Any]]]:
        if (
            manifest.tool_schema_version == "v1"
            and manifest.context_policy_version == "v1"
        ):
            return SYSTEM_PROMPT_V1, TOOL_SCHEMAS_V1
        if (
            manifest.tool_schema_version == "v2"
            and manifest.context_policy_version == "phase-evidence-v2"
        ):
            return SYSTEM_PROMPT_V2, TOOL_SCHEMAS_V2
        raise ContractError(
            "unsupported tool schema and context policy version combination"
        )

    def _validate_legacy_submission(
        self,
        task: PublicTask,
        run_id: str,
        phase: Phase,
    ) -> None:
        passed_checks = {
            event.payload.get("check_id")
            for event in self.state.list_events(run_id)
            if event.type == EventType.TOOL_SUCCEEDED
            and event.payload.get("tool") == "run_check"
            and event.payload.get("passed") is True
        }
        required_checks = {check.id for check in task.visible_checks}
        if not required_checks.issubset(passed_checks):
            raise ContractError(
                "DONE requires every registered visible check to have a passing result"
            )
        if phase != Phase.REVIEW:
            raise ContractError("DONE requires REVIEW phase under legacy schema v1")

    def _reject_unstructured_submission(
        self,
        run_id: str,
        workspace: Path,
        *,
        correlation_id: str,
    ) -> bool:
        summary = WorkspaceManager.diff_summary(workspace)
        attempt_number = 1 + sum(
            event.type == EventType.SUBMISSION_ATTEMPTED
            for event in self.state.list_events(run_id)
        )
        self.state.append_event(
            run_id,
            EventType.SUBMISSION_ATTEMPTED,
            actor="submission-gate",
            correlation_id=correlation_id,
            payload={
                "attempt_number": attempt_number,
                "worktree_diff_hash": summary.patch_hash,
                "submission_method": "legacy_done_text",
            },
        )
        self.state.append_event(
            run_id,
            EventType.SUBMISSION_REJECTED,
            actor="submission-gate",
            correlation_id=correlation_id,
            payload={
                "attempt_number": attempt_number,
                "worktree_diff_hash": summary.patch_hash,
                "submission_method": "legacy_done_text",
                "reason_code": "structured_finish_task_required",
                "missing_evidence": ["structured_finish_task"],
            },
        )
        return self._submission_rejection_count(run_id) > (
            _MAX_RECOVERABLE_SUBMISSION_REJECTIONS
        )

    def _finish_task(
        self,
        *,
        run_id: str,
        task: PublicTask,
        workspace: Path,
        phase: Phase,
        action_id: str,
        arguments: dict[str, Any],
        context_evidence: dict[str, Any],
        request_artifact_id: str,
        additional_missing_evidence: list[str],
    ) -> tuple[ToolResult, bool, bool]:
        input_hash = sha256_text(
            canonical_json({"tool": "finish_task", "input": arguments})
        )
        prior = self.state.get_action_result(run_id, action_id, input_hash)
        if prior is not None:
            accepted, should_stop = self._reconcile_finish_task_lifecycle(
                run_id,
                action_id,
                input_hash,
                prior,
            )
            replayed = prior.model_copy(
                update={"output": {**prior.output, "replayed": True}}
            )
            return replayed, accepted, should_stop

        started = utc_now()
        summary = WorkspaceManager.diff_summary(workspace)
        readiness = diff_bound_evidence(
            task,
            self.state.list_events(run_id),
            summary.patch_hash,
            presented_tool_results=context_evidence.get("tool_results", []),
            phase=phase,
        )
        missing_evidence = list(readiness.missing_evidence)
        missing_evidence.extend(additional_missing_evidence)
        if arguments:
            missing_evidence.append("empty_finish_arguments")
        attempt_number = 1 + sum(
            event.type == EventType.SUBMISSION_ATTEMPTED
            for event in self.state.list_events(run_id)
        )
        accepted = not missing_evidence
        if accepted:
            submitted_patch_artifact = self.artifacts.put_text(
                summary.patch,
                "text/x-diff",
            )
            submitted_patch = submitted_patch_artifact.model_dump(mode="json")
            artifact_payload = {
                "tool": "finish_task",
                "status": "succeeded",
                "worktree_diff_hash": summary.patch_hash,
                "accepted_for_evaluation": True,
                "submitted_patch_artifact": submitted_patch,
            }
            artifact = self.artifacts.put_json(artifact_payload)
            result = ToolResult(
                action_id=action_id,
                status="succeeded",
                started_at=started,
                finished_at=utc_now(),
                output={
                    "artifact_id": artifact.artifact_id,
                    "artifact_path": artifact.path,
                    "worktree_diff_hash": summary.patch_hash,
                    "accepted_for_evaluation": True,
                    "submission_attempt_number": attempt_number,
                    "submission_method": "finish_task",
                    "source_get_diff_sequence": readiness.review_event_sequence,
                    "request_artifact_id": request_artifact_id,
                    "complete_tool_result": True,
                    "submitted_patch_artifact": submitted_patch,
                },
            )
        else:
            message = (
                "submission is not ready: " + ", ".join(missing_evidence)
            )
            artifact_payload = {
                "tool": "finish_task",
                "status": "rejected",
                "error_code": "SUBMISSION_NOT_READY",
                "error_message": message,
                "error_details": {
                    "missing_evidence": missing_evidence,
                    "recoverable": True,
                },
                "worktree_diff_hash": summary.patch_hash,
            }
            artifact = self.artifacts.put_json(artifact_payload)
            result = ToolResult(
                action_id=action_id,
                status="rejected",
                started_at=started,
                finished_at=utc_now(),
                output={
                    "artifact_id": artifact.artifact_id,
                    "artifact_path": artifact.path,
                    "worktree_diff_hash": summary.patch_hash,
                    "error_details": artifact_payload["error_details"],
                    "submission_attempt_number": attempt_number,
                    "submission_method": "finish_task",
                },
                error_code="SUBMISSION_NOT_READY",
                error_message=message,
            )
        self.state.append_event(
            run_id,
            EventType.TOOL_CALLED,
            actor="agent",
            correlation_id=action_id,
            payload={
                "tool": "finish_task",
                "input_hash": input_hash,
                "recovery_result": result.model_dump(mode="json"),
            },
        )
        self.state.record_action_result(run_id, action_id, input_hash, result)
        durable_result = self.state.get_action_result(
            run_id,
            action_id,
            input_hash,
        )
        if durable_result is None:
            raise RecoveryError(
                "finish_task action result was not durable after recording"
            )
        accepted, should_stop = self._reconcile_finish_task_lifecycle(
            run_id,
            action_id,
            input_hash,
            durable_result,
        )
        return durable_result, accepted, should_stop

    def _reconcile_finish_task_lifecycle(
        self,
        run_id: str,
        action_id: str,
        input_hash: str,
        result: ToolResult,
    ) -> tuple[bool, bool]:
        """Append only a missing suffix for one durable finish_task decision."""

        attempt_number = result.output.get("submission_attempt_number")
        diff_hash = result.output.get("worktree_diff_hash")
        if not isinstance(attempt_number, int) or not isinstance(diff_hash, str):
            raise RecoveryError(
                "finish_task result lacks durable submission decision metadata"
            )
        accepted = bool(
            result.status == "succeeded"
            and result.output.get("accepted_for_evaluation") is True
        )
        expected: list[tuple[EventType, str, dict[str, Any]]] = [
            (
                EventType.TOOL_CALLED,
                "agent",
                {
                    "tool": "finish_task",
                    "input_hash": input_hash,
                },
            )
        ]
        if accepted:
            source_sequence = result.output.get("source_get_diff_sequence")
            request_artifact_id = result.output.get("request_artifact_id")
            if not isinstance(source_sequence, int) or not isinstance(
                request_artifact_id,
                str,
            ):
                raise RecoveryError(
                    "accepted finish_task result lacks final-review provenance"
                )
            expected.append(
                (
                    EventType.REVIEW_RECORDED,
                    "submission-gate",
                    {
                        "worktree_diff_hash": diff_hash,
                        "source_get_diff_sequence": source_sequence,
                        "request_artifact_id": request_artifact_id,
                        "complete_tool_result": True,
                    },
                )
            )
        expected.append(
            (
                EventType.SUBMISSION_ATTEMPTED,
                "submission-gate",
                {
                    "attempt_number": attempt_number,
                    "worktree_diff_hash": diff_hash,
                    "submission_method": "finish_task",
                },
            )
        )
        expected.append(
            (
                (
                    EventType.TOOL_SUCCEEDED
                    if accepted
                    else EventType.TOOL_FAILED
                ),
                "submission-gate",
                {
                    "tool": "finish_task",
                    "status": result.status,
                    "artifact_id": result.output.get("artifact_id"),
                    "artifact_path": result.output.get("artifact_path"),
                    "worktree_diff_hash": diff_hash,
                    "error_code": result.error_code,
                    "error_message": result.error_message,
                    "duration_ms": int(
                        (
                            result.finished_at - result.started_at
                        ).total_seconds()
                        * 1000
                    ),
                    "submitted_patch_artifact": result.output.get(
                        "submitted_patch_artifact"
                    ),
                },
            )
        )
        if accepted:
            expected.append(
                (
                    EventType.SUBMISSION_ACCEPTED,
                    "submission-gate",
                    {
                        "attempt_number": attempt_number,
                        "worktree_diff_hash": diff_hash,
                        "accepted_for": "deterministic_evaluation",
                        "evaluation_success_claimed": False,
                        "submitted_patch_artifact": result.output.get(
                            "submitted_patch_artifact"
                        ),
                    },
                )
            )
        else:
            missing_evidence = (
                result.output.get("error_details", {}).get(
                    "missing_evidence",
                    [],
                )
            )
            expected.append(
                (
                    EventType.SUBMISSION_REJECTED,
                    "submission-gate",
                    {
                        "attempt_number": attempt_number,
                        "worktree_diff_hash": diff_hash,
                        "submission_method": "finish_task",
                        "reason_code": "submission_preconditions_missing",
                        "missing_evidence": missing_evidence,
                    },
                )
            )

        relevant_types = {
            EventType.TOOL_CALLED,
            EventType.TOOL_SUCCEEDED,
            EventType.TOOL_FAILED,
            EventType.REVIEW_RECORDED,
            EventType.SUBMISSION_ATTEMPTED,
            EventType.SUBMISSION_REJECTED,
            EventType.SUBMISSION_ACCEPTED,
        }
        existing = [
            event
            for event in self.state.list_events(run_id)
            if event.correlation_id == action_id
            and event.type in relevant_types
        ]
        expected_types = [item[0] for item in expected]
        existing_types = [event.type for event in existing]
        if existing_types != expected_types[: len(existing_types)]:
            raise RecoveryError(
                "finish_task lifecycle is not a valid durable prefix"
            )
        for event, (_, actor, payload) in zip(
            existing,
            expected[: len(existing)],
            strict=True,
        ):
            if event.actor != actor or any(
                event.payload.get(key) != value
                for key, value in payload.items()
            ):
                raise RecoveryError(
                    "finish_task lifecycle conflicts with its action result"
                )
        for event_type, actor, payload in expected[len(existing) :]:
            self.state.append_event(
                run_id,
                event_type,
                actor=actor,
                correlation_id=action_id,
                payload=payload,
            )
        return (
            accepted,
            (
                not accepted
                and self._submission_rejection_count(run_id)
                > _MAX_RECOVERABLE_SUBMISSION_REJECTIONS
            ),
        )

    def _submission_rejection_count(self, run_id: str) -> int:
        return sum(
            event.type == EventType.SUBMISSION_REJECTED
            for event in self.state.list_events(run_id)
        )

    def _reconcile_submission_recovery(
        self,
        *,
        manifest: RunManifest,
        task: PublicTask,
        workspace: Path,
        phase: Phase,
        usage: Usage,
    ) -> tuple[Phase, Checkpoint | None, ToolResult | None]:
        """Repair an interrupted v2 submission before another model call."""

        checkpoint = self.state.latest_checkpoint(manifest.run_id)
        if manifest.tool_schema_version != "v2":
            return phase, checkpoint, None
        self._reconcile_unstructured_submission_lifecycle(manifest.run_id)
        calls: dict[str, Any] = {}
        for event in self.state.list_events(manifest.run_id):
            if (
                event.type == EventType.TOOL_CALLED
                and event.payload.get("tool") == "finish_task"
            ):
                if event.correlation_id is None:
                    raise RecoveryError(
                        "finish_task ToolCalled event lacks correlation identity"
                    )
                if event.correlation_id in calls:
                    raise RecoveryError(
                        "finish_task action has duplicate ToolCalled events"
                    )
                calls[event.correlation_id] = event

        accepted_results: list[ToolResult] = []
        latest_rejected: ToolResult | None = None
        for action_id, call_event in calls.items():
            input_hash = call_event.payload.get("input_hash")
            if not isinstance(input_hash, str):
                raise RecoveryError(
                    "finish_task ToolCalled event lacks its input hash"
                )
            result = self.state.get_action_result(
                manifest.run_id,
                action_id,
                input_hash,
            )
            if result is None:
                result = self._restore_finish_task_action_result(
                    manifest.run_id,
                    action_id,
                    input_hash,
                    call_event.payload.get("recovery_result"),
                )
            accepted, _ = self._reconcile_finish_task_lifecycle(
                manifest.run_id,
                action_id,
                input_hash,
                result,
            )
            if accepted:
                accepted_results.append(result)
            else:
                latest_rejected = result

        if len(accepted_results) > 1:
            raise RecoveryError(
                "run contains more than one accepted finish_task action"
            )
        rejection_count = self._submission_rejection_count(manifest.run_id)
        if (
            accepted_results
            and rejection_count
            > _MAX_RECOVERABLE_SUBMISSION_REJECTIONS
        ):
            raise RecoveryError(
                "submission was accepted after the terminal rejection limit"
            )
        if accepted_results:
            phase, checkpoint = self._complete_accepted_submission(
                manifest=manifest,
                task=task,
                workspace=workspace,
                phase=phase,
                usage=usage,
                result=accepted_results[0],
            )
            return phase, checkpoint, accepted_results[0]

        if rejection_count > _MAX_RECOVERABLE_SUBMISSION_REJECTIONS:
            raise SubmissionProtocolError(
                "submission preconditions were rejected three times"
            )
        if latest_rejected is not None:
            rejected_event = next(
                event
                for event in reversed(
                    self.state.list_events(manifest.run_id)
                )
                if event.type == EventType.SUBMISSION_REJECTED
                and event.correlation_id == latest_rejected.action_id
            )
            checkpoint = self.state.latest_checkpoint(manifest.run_id)
            if (
                checkpoint is None
                or checkpoint.through_sequence < rejected_event.sequence
            ):
                checkpoint = self._checkpoint(
                    manifest,
                    workspace,
                    phase,
                    usage,
                    latest_rejected,
                    task=task,
                )
            else:
                self._ensure_checkpoint_event(checkpoint)
        return phase, checkpoint, None

    def _restore_finish_task_action_result(
        self,
        run_id: str,
        action_id: str,
        input_hash: str,
        raw_result: Any,
    ) -> ToolResult:
        try:
            result = ToolResult.model_validate(raw_result)
        except (TypeError, ValueError) as exc:
            raise RecoveryError(
                "interrupted finish_task lacks a recoverable action result"
            ) from exc
        if result.action_id != action_id:
            raise RecoveryError(
                "finish_task recovery result has a conflicting action identity"
            )
        self.state.record_action_result(
            run_id,
            action_id,
            input_hash,
            result,
        )
        restored = self.state.get_action_result(
            run_id,
            action_id,
            input_hash,
        )
        if restored is None:
            raise RecoveryError(
                "restored finish_task action result was not durable"
            )
        return restored

    def _reconcile_unstructured_submission_lifecycle(
        self,
        run_id: str,
    ) -> None:
        attempts = [
            event
            for event in self.state.list_events(run_id)
            if event.type == EventType.SUBMISSION_ATTEMPTED
            and event.payload.get("submission_method")
            == "legacy_done_text"
        ]
        for attempt in attempts:
            if attempt.correlation_id is None:
                raise RecoveryError(
                    "v2 legacy-DONE rejection lacks correlation identity"
                )
            outcomes = [
                event
                for event in self.state.list_events(run_id)
                if event.type == EventType.SUBMISSION_REJECTED
                and event.correlation_id == attempt.correlation_id
            ]
            if len(outcomes) > 1:
                raise RecoveryError(
                    "legacy-DONE attempt has duplicate rejection outcomes"
                )
            expected_payload = {
                "attempt_number": attempt.payload.get("attempt_number"),
                "worktree_diff_hash": attempt.payload.get(
                    "worktree_diff_hash"
                ),
                "submission_method": "legacy_done_text",
                "reason_code": "structured_finish_task_required",
                "missing_evidence": ["structured_finish_task"],
            }
            if outcomes:
                outcome = outcomes[0]
                if (
                    outcome.sequence <= attempt.sequence
                    or any(
                        outcome.payload.get(key) != value
                        for key, value in expected_payload.items()
                    )
                ):
                    raise RecoveryError(
                        "legacy-DONE rejection conflicts with its attempt"
                    )
                continue
            self.state.append_event(
                run_id,
                EventType.SUBMISSION_REJECTED,
                actor="submission-gate",
                correlation_id=attempt.correlation_id,
                payload=expected_payload,
            )

    def _complete_accepted_submission(
        self,
        *,
        manifest: RunManifest,
        task: PublicTask,
        workspace: Path,
        phase: Phase,
        usage: Usage,
        result: ToolResult,
    ) -> tuple[Phase, Checkpoint]:
        diff_hash = result.output.get("worktree_diff_hash")
        summary = WorkspaceManager.diff_summary(workspace)
        if not isinstance(diff_hash, str) or summary.patch_hash != diff_hash:
            raise RecoveryError(
                "accepted submission does not match the current worktree diff"
            )
        try:
            submitted_patch_artifact = Artifact.model_validate(
                result.output["submitted_patch_artifact"]
            )
            submitted_patch_bytes = Path(
                submitted_patch_artifact.path
            ).read_bytes()
        except (KeyError, OSError, TypeError, ValueError) as exc:
            raise RecoveryError(
                "accepted finish_task lacks its immutable patch artifact"
            ) from exc
        if (
            submitted_patch_artifact.content_hash != diff_hash
            or sha256_bytes(submitted_patch_bytes) != diff_hash
        ):
            raise RecoveryError(
                "accepted finish_task patch artifact does not match its diff"
            )
        accepted_events = [
            event
            for event in self.state.list_events(manifest.run_id)
            if event.type == EventType.SUBMISSION_ACCEPTED
        ]
        if (
            len(accepted_events) != 1
            or accepted_events[0].correlation_id != result.action_id
            or accepted_events[0].payload.get("worktree_diff_hash")
            != diff_hash
            or accepted_events[0].payload.get(
                "submitted_patch_artifact"
            )
            != submitted_patch_artifact.model_dump(mode="json")
        ):
            raise RecoveryError(
                "accepted finish_task lacks one matching lifecycle event"
            )
        accepted_event = accepted_events[0]
        done_transitions = [
            event
            for event in self.state.list_events(manifest.run_id)
            if event.type == EventType.PHASE_CHANGED
            and event.sequence > accepted_event.sequence
            and event.payload.get("from") == Phase.REVIEW.value
            and event.payload.get("to") == Phase.DONE.value
        ]
        if len(done_transitions) > 1:
            raise RecoveryError(
                "accepted submission has duplicate DONE transitions"
            )
        if done_transitions:
            phase = Phase.DONE
            done_transition = done_transitions[0]
        else:
            if phase != Phase.REVIEW:
                raise RecoveryError(
                    "accepted submission cannot transition to DONE "
                    f"from {phase.value}"
                )
            phase = self._transition(
                manifest.run_id,
                phase,
                Phase.DONE,
            )
            done_transition = next(
                event
                for event in reversed(
                    self.state.list_events(manifest.run_id)
                )
                if event.type == EventType.PHASE_CHANGED
                and event.payload.get("from") == Phase.REVIEW.value
                and event.payload.get("to") == Phase.DONE.value
            )

        checkpoint = self.state.latest_checkpoint(manifest.run_id)
        if (
            checkpoint is not None
            and checkpoint.phase == Phase.DONE
            and checkpoint.worktree_diff_hash == diff_hash
            and checkpoint.through_sequence >= done_transition.sequence
        ):
            self._ensure_checkpoint_event(checkpoint)
            return phase, checkpoint
        if (
            checkpoint is not None
            and checkpoint.through_sequence >= done_transition.sequence
        ):
            raise RecoveryError(
                "checkpoint after submission acceptance is not a DONE checkpoint"
            )
        checkpoint = self._checkpoint(
            manifest,
            workspace,
            phase,
            usage,
            result,
            task=task,
        )
        return phase, checkpoint

    def _ensure_checkpoint_event(self, checkpoint: Checkpoint) -> None:
        events = [
            event
            for event in self.state.list_events(checkpoint.run_id)
            if event.type == EventType.CHECKPOINT_SAVED
            and event.payload.get("checkpoint_id")
            == checkpoint.checkpoint_id
        ]
        if len(events) > 1:
            raise RecoveryError(
                "checkpoint has duplicate CheckpointSaved events"
            )
        expected = {
            "checkpoint_id": checkpoint.checkpoint_id,
            "through_sequence": checkpoint.through_sequence,
            "worktree_diff_hash": checkpoint.worktree_diff_hash,
        }
        if events:
            if any(
                events[0].payload.get(key) != value
                for key, value in expected.items()
            ):
                raise RecoveryError(
                    "CheckpointSaved event conflicts with durable checkpoint"
                )
            return
        self.state.append_event(
            checkpoint.run_id,
            EventType.CHECKPOINT_SAVED,
            actor="state-store",
            payload=expected,
        )

    def _phase_after_tool(
        self,
        run_id: str,
        phase: Phase,
        tool: str,
        result: ToolResult,
        task: PublicTask,
        workspace: Path,
    ) -> Phase:
        if result.status != "succeeded":
            return phase
        if tool == "apply_patch":
            if phase == Phase.REPRODUCE:
                phase = self._transition(run_id, phase, Phase.PLAN)
                return self._transition(run_id, phase, Phase.IMPLEMENT)
            if phase == Phase.PLAN:
                return self._transition(run_id, phase, Phase.IMPLEMENT)
            if phase in {Phase.VERIFY, Phase.REVIEW}:
                return self._transition(run_id, phase, Phase.IMPLEMENT)
            return phase
        if tool == "run_check":
            if phase == Phase.REVIEW:
                phase = self._transition(run_id, phase, Phase.IMPLEMENT)
            if result.output.get("passed") is True:
                if phase == Phase.IMPLEMENT:
                    return self._transition(run_id, phase, Phase.VERIFY)
                return phase
            if phase == Phase.VERIFY:
                return self._transition(run_id, phase, Phase.IMPLEMENT)
            return phase
        if tool == "get_diff":
            summary = WorkspaceManager.diff_summary(workspace)
            evidence = diff_bound_evidence(
                task,
                self.state.list_events(run_id),
                summary.patch_hash,
            )
            if (
                not evidence.mutation_present
                or evidence.pending_checks
                or evidence.review_event_sequence is None
            ):
                return phase
            if phase == Phase.REPRODUCE:
                phase = self._transition(run_id, phase, Phase.PLAN)
            if phase == Phase.PLAN:
                phase = self._transition(run_id, phase, Phase.IMPLEMENT)
            if phase == Phase.IMPLEMENT:
                phase = self._transition(run_id, phase, Phase.VERIFY)
            if phase == Phase.VERIFY:
                return self._transition(run_id, phase, Phase.REVIEW)
        return phase

    @staticmethod
    def _task_dir(task_path: str | Path) -> Path:
        path = Path(task_path).resolve()
        return path.parent if path.is_file() else path

    def _find_task(self, manifest: RunManifest) -> Path:
        for public_path in (repository_root() / "tasks").rglob("public.yaml"):
            package = load_task_package(public_path.parent)
            if (
                package.public.task_id == manifest.task_id
                and package.public.task_version == manifest.task_version
                and package.public_spec_hash == manifest.public_spec_hash
            ):
                return public_path.parent
        raise RecoveryError(f"task package for run {manifest.run_id} is unavailable")

    def _model_adapter(
        self, model: str, manifest: RunManifest, completed_tools: list[str]
    ) -> ModelAdapter:
        if model == "mock":
            return MockModelAdapter(
                manifest.task_id,
                completed_tools,
                structured_finish=manifest.tool_schema_version == "v2",
            )
        if model.startswith("replay:"):
            normalized_model, replay_path, replay_hash = self._replay_identity(model)
            if (
                manifest.model.provider != "replay"
                or manifest.model.model_id != normalized_model
                or manifest.model.replay_hash != replay_hash
            ):
                raise ContractError("replay source does not match the immutable run manifest")
            return ReplayModelAdapter(
                replay_path,
                len(completed_tools),
                expected_hash=manifest.model.replay_hash,
            )
        if model == "openai":
            return OpenAIResponsesAdapter(manifest.model)
        raise ContractError(f"unknown model adapter: {model}")

    @staticmethod
    def _replay_identity(model: str) -> tuple[str, Path, str]:
        raw_path = model.split(":", 1)[1]
        relative = safe_relative_path(raw_path, field_name="replay path")
        replay_path = ensure_within(repository_root(), relative)
        if not replay_path.is_file():
            raise ContractError(f"replay file does not exist: {relative}")
        return (
            f"replay:{Path(relative).as_posix()}",
            replay_path,
            sha256_bytes(replay_path.read_bytes()),
        )

    def _reconcile_workspace(self, manifest: RunManifest, workspace: Path) -> None:
        checkpoint = self.state.latest_checkpoint(manifest.run_id)
        if checkpoint is None:
            raise RecoveryError("run has events but no durable checkpoint")
        if WorkspaceManager.untracked_files(workspace):
            raise RecoveryError(
                "agent workspace contains untracked files during recovery"
            )
        summary = WorkspaceManager.diff_summary(workspace)
        if summary.patch_hash != checkpoint.worktree_diff_hash:
            raise RecoveryError("workspace diff hash does not match the latest durable checkpoint")
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=workspace,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        if head != checkpoint.repository_head:
            raise RecoveryError("workspace HEAD does not match the latest durable checkpoint")

    def _completed_tools(self, run_id: str) -> list[str]:
        return [
            str(event.payload["tool"])
            for event in self.state.list_events(run_id)
            if event.type == EventType.TOOL_SUCCEEDED and event.payload.get("tool")
        ]

    @staticmethod
    def _docker_sandbox(package) -> DockerSandbox:
        if package.environment is not None:
            return DockerSandbox(package.environment.evaluator_image)
        return DockerSandbox()

    def _usage(self, run_id: str) -> Usage:
        usage = Usage()
        for event in self.state.list_events(run_id):
            if event.type == EventType.MODEL_CALLED:
                usage.model_calls += 1
                usage.input_tokens += int(event.payload.get("input_tokens", 0))
                usage.cached_input_tokens += int(
                    event.payload.get("cached_input_tokens", 0)
                )
                usage.cache_write_input_tokens += int(
                    event.payload.get("cache_write_input_tokens", 0)
                )
                usage.output_tokens += int(event.payload.get("output_tokens", 0))
                usage.reasoning_output_tokens += int(
                    event.payload.get("reasoning_output_tokens", 0)
                )
                usage.input_token_count_calls += int(
                    event.payload.get("input_token_count_calls", 0)
                )
                usage.wall_clock_ms += int(event.payload.get("duration_ms", 0))
            elif event.type == EventType.TOOL_CALLED:
                usage.tool_calls += 1
            elif event.type in {EventType.TOOL_SUCCEEDED, EventType.TOOL_FAILED}:
                usage.wall_clock_ms += int(event.payload.get("duration_ms", 0))
        manifest = self.state.get_manifest(run_id)
        usage.model_cost_usd = calculate_model_cost(usage, manifest.model)
        return usage

    def _assert_budget(self, manifest: RunManifest, usage: Usage) -> None:
        if usage.model_calls >= manifest.budget.max_model_calls:
            raise ContractError("model call budget exhausted")
        if usage.tool_calls >= manifest.budget.max_tool_calls:
            raise ContractError("tool call budget exhausted")
        if usage.input_tokens + usage.output_tokens >= manifest.budget.max_total_tokens:
            raise ContractError("token budget exhausted")
        if usage.wall_clock_ms >= manifest.budget.wall_clock_timeout_seconds * 1000:
            raise ContractError("wall clock budget exhausted")

    @staticmethod
    def _assert_consumed_budget(manifest: RunManifest, usage: Usage) -> None:
        if usage.model_calls > manifest.budget.max_model_calls:
            raise ContractError("model call budget exceeded")
        if usage.input_tokens + usage.output_tokens > manifest.budget.max_total_tokens:
            raise ContractError("token budget exceeded")
        if usage.wall_clock_ms > manifest.budget.wall_clock_timeout_seconds * 1000:
            raise ContractError("wall clock budget exceeded")


def run_from_cli(
    task: str | Path,
    *,
    model: str,
    memory_condition: MemoryCondition,
) -> dict[str, Any]:
    if model == "openai":
        raise ContractError(
            "direct live runs are disabled; use an approved experiment-v2 suite"
        )
    return AgentRunner().start(task, model=model, memory_condition=memory_condition)


def resume_from_cli(run_id: str) -> dict[str, Any]:
    runner = AgentRunner()
    manifest = runner.state.get_manifest(run_id)
    if manifest.model.provider == "openai":
        raise ContractError(
            "direct live resume is disabled; approved campaign resume is not implemented"
        )
    return runner.resume(run_id)
