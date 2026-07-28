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

from patchloop.agent.context import build_context
from patchloop.agent.model import (
    SYSTEM_PROMPT,
    MockModelAdapter,
    ModelAdapter,
    OpenAIResponsesAdapter,
    ReplayModelAdapter,
)
from patchloop.agent.phases import validate_transition
from patchloop.agent.tools import TOOL_SCHEMAS, ToolGateway
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import (
    Budget,
    Checkpoint,
    EventType,
    ExperimentRunContext,
    MemoryCondition,
    Phase,
    RunManifest,
    RunOutcomeKind,
    RunResult,
    RunStatus,
    TaskPackage,
    ToolResult,
    Usage,
    Verdicts,
)
from patchloop.errors import ContractError, InjectedFault, RecoveryError
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
from patchloop.util import ensure_within, safe_relative_path, sha256_bytes, utc_now
from patchloop.verifier import EvaluationEngine

_LIVE_AUTHORIZATION_GUARD = object()


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
                {"system_prompt": SYSTEM_PROMPT, "tools": TOOL_SCHEMAS}
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
            checkpoint = self._checkpoint(manifest, workspace, phase)

        usage = self._usage(manifest.run_id)
        try:
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
                context, context_hash = build_context(
                    package.public, events, checkpoint, memory_text
                )
                context_artifact = self.artifacts.put_text(context, "application/json")
                self.state.append_event(
                    manifest.run_id,
                    EventType.CONTEXT_BUILT,
                    actor="context-builder",
                    payload={
                        "context_hash": context_hash,
                        "artifact_id": context_artifact.artifact_id,
                        "artifact_path": context_artifact.path,
                        "provider_state_used": False,
                    },
                )
                model_started = time.monotonic()
                turn = adapter.next_turn(context, TOOL_SCHEMAS)
                model_duration_ms = int((time.monotonic() - model_started) * 1000)
                usage.model_calls += 1
                usage.input_tokens += turn.input_tokens
                usage.cached_input_tokens += turn.cached_input_tokens
                usage.cache_write_input_tokens += turn.cache_write_input_tokens
                usage.output_tokens += turn.output_tokens
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
                self.state.append_event(
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
                        "response_model": turn.response_model,
                        "response_service_tier": turn.response_service_tier,
                        "system_fingerprint": turn.system_fingerprint,
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
                    passed_checks = {
                        event.payload.get("check_id")
                        for event in self.state.list_events(manifest.run_id)
                        if event.type == EventType.TOOL_SUCCEEDED
                        and event.payload.get("tool") == "run_check"
                        and event.payload.get("passed") is True
                    }
                    required_checks = {check.id for check in package.public.visible_checks}
                    if not required_checks.issubset(passed_checks):
                        raise ContractError(
                            "DONE requires every registered visible check to have a passing result"
                        )
                    phase = self._transition(manifest.run_id, phase, Phase.DONE)
                    checkpoint = self._checkpoint(manifest, workspace, phase, usage)
                    return self._evaluate(task_dir, workspace, manifest, sandbox, usage)
                if not turn.tool_calls:
                    raise ContractError("model returned neither a tool call nor DONE")
                for call in turn.tool_calls:
                    if usage.tool_calls >= manifest.budget.max_tool_calls:
                        raise ContractError("tool call budget exhausted")
                    phase = self._phase_for_tool(manifest.run_id, phase, call.name)
                    result = gateway.execute(call.name, call.action_id, call.arguments)
                    if not result.output.get("replayed"):
                        usage.tool_calls += 1
                        usage.wall_clock_ms += int(
                            (result.finished_at - result.started_at).total_seconds() * 1000
                        )
                    if isinstance(adapter, MockModelAdapter) and result.status == "succeeded":
                        adapter.record_completed(call.name)
                    checkpoint = self._checkpoint(manifest, workspace, phase, usage, result)
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
        run_dir = self.root / "runs" / manifest.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        patch_path = run_dir / "submitted.patch"
        patch_path.write_text(summary.patch, encoding="utf-8", newline="\n")
        evaluator = EvaluationEngine(self.workspaces, sandbox, self.artifacts)
        evaluator_started = time.monotonic()
        result = evaluator.evaluate(task_dir, patch_path, manifest, usage=usage)
        evaluator_duration_ms = int((time.monotonic() - evaluator_started) * 1000)
        failure = classify_failure(
            result,
            load_task_package(task_dir).public.split,
            root=self.root,
            phase=Phase.REVIEW,
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
        result = RunResult(
            run_id=manifest.run_id,
            agent_submission_status="failed",
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
        completed_checks = list(
            dict.fromkeys(
                str(event.payload["check_id"])
                for event in self.state.list_events(manifest.run_id)
                if event.type == EventType.TOOL_SUCCEEDED
                and event.payload.get("tool") == "run_check"
                and event.payload.get("passed") is True
                and event.payload.get("check_id")
            )
        )
        usage = usage or Usage()
        checkpoint = Checkpoint(
            checkpoint_id=f"ckpt_{uuid.uuid4().hex}",
            run_id=manifest.run_id,
            through_sequence=self.state.last_sequence(manifest.run_id),
            phase=phase,
            task_summary=manifest.task_id,
            modified_files=summary.changed_files,
            completed_action_ids=completed_actions,
            completed_checks=completed_checks,
            repository_head=head,
            worktree_diff_hash=summary.patch_hash,
            last_patch_hash=(
                last_result.output.get("patch_hash")
                if last_result and last_result.status == "succeeded"
                else None
            ),
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

    def _phase_for_tool(self, run_id: str, phase: Phase, tool: str) -> Phase:
        if tool == "apply_patch" and phase == Phase.REPRODUCE:
            phase = self._transition(run_id, phase, Phase.PLAN)
            return self._transition(run_id, phase, Phase.IMPLEMENT)
        if tool == "apply_patch" and phase == Phase.PLAN:
            return self._transition(run_id, phase, Phase.IMPLEMENT)
        if tool == "apply_patch" and phase in {Phase.VERIFY, Phase.REVIEW}:
            return self._transition(run_id, phase, Phase.IMPLEMENT)
        if tool == "run_check" and phase == Phase.IMPLEMENT:
            return self._transition(run_id, phase, Phase.VERIFY)
        if tool == "get_diff" and phase == Phase.VERIFY:
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
            return MockModelAdapter(manifest.task_id, completed_tools)
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
                usage.wall_clock_ms += int(event.payload.get("duration_ms", 0))
            elif event.type == EventType.TOOL_CALLED:
                usage.tool_calls += 1
            elif event.type in {EventType.TOOL_SUCCEEDED, EventType.TOOL_FAILED}:
                if event.actor == "tool-gateway":
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
