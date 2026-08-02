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

from patchloop.agent.context import BuiltContext, build_context_with_evidence
from patchloop.agent.model import (
    SYSTEM_PROMPT_V1,
    SYSTEM_PROMPT_V2,
    SYSTEM_PROMPT_V3,
    SYSTEM_PROMPT_V4,
    SYSTEM_PROMPT_V5,
    SYSTEM_PROMPT_V6,
    SYSTEM_PROMPT_V7,
    SYSTEM_PROMPT_V8,
    MockModelAdapter,
    ModelAdapter,
    OpenAIResponsesAdapter,
    ReplayModelAdapter,
)
from patchloop.agent.phases import diff_bound_evidence, validate_transition
from patchloop.agent.review import (
    build_public_review_base_provenance,
    validate_public_review_base_provenance_document,
)
from patchloop.agent.tools import (
    TOOL_SCHEMAS_V1,
    TOOL_SCHEMAS_V2,
    TOOL_SCHEMAS_V3,
    TOOL_SCHEMAS_V4,
    TOOL_SCHEMAS_V5,
    TOOL_SCHEMAS_V6,
    ToolGateway,
)
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import (
    Artifact,
    Budget,
    Checkpoint,
    EventType,
    ExperimentPurpose,
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
    ModelGenerationBudgetError,
    RecoveryError,
    RunOwnershipConflict,
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
from patchloop.state import RunOwnershipCoordinator, StateStore
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
_MAX_RECOVERABLE_REVIEW_REJECTIONS = 2
_EVALUATION_RECEIPT_SCHEMA = "evaluation-receipt-v1"
_EXACT_REQUEST_GENERATION_BLOCK_SCHEMA = "model-generation-block-v1"
_COUNTER_GENERATION_BLOCK_SCHEMA = "model-generation-block-v2"
_OPTIONAL_COUNTER_GENERATION_BLOCK_SCHEMA = "model-generation-block-v3"
_COUNTER_GENERATION_BLOCK_REASONS = frozenset(
    {
        "model_call_budget_exhausted",
        "tool_call_budget_exhausted",
        "wall_clock_budget_exhausted",
    }
)


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
        self.ownership = RunOwnershipCoordinator(self.root / "worker-locks")
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
        self_validation: bool = False,
        live_authorization: LiveExecutionAuthorization | None = None,
        _allowed_worker_statuses: set[RunStatus] | None = None,
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
        if selected_provider == "openai" and (
            self_validation
            or (
                manifest is not None
                and (
                    manifest.tool_schema_version == "v3"
                    or manifest.context_policy_version
                    == "phase-evidence-v6"
                )
            )
        ):
            raise ContractError(
                "self-validation v3/v6 is offline-only and unavailable "
                "for the OpenAI provider"
            )
        if selected_provider == "openai":
            self._require_live_authorization(manifest, live_authorization)

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
            probe_image_identity = (
                docker_sandbox.probe_image_identity()
                if (
                    self_validation
                    and package.public.probe_profiles
                    and backend == "docker"
                )
                else None
            )
            manifest = build_manifest(
                package,
                provider=selected_provider,
                model_id=selected_model_id,
                memory_condition=memory_condition,
                sandbox_backend=backend,
                agent_image_digest=image_identity,
                evaluator_image_digest=image_identity,
                probe_image_digest=probe_image_identity,
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
                self_validation=self_validation,
            )
        if (
            manifest.tool_schema_version in {"v3", "v4", "v5", "v6"}
            and package.public.probe_profiles
            and manifest.probe_image_digest is None
        ):
            raise ContractError(
                "registered probe profiles require the dedicated Docker "
                "probe image and a manifest-bound image identity"
            )
        allowed_statuses = _allowed_worker_statuses or {RunStatus.CREATED}
        with self.ownership.acquire(manifest.run_id) as worker:
            worker_claim = self.state.claim_run_for_worker(
                manifest.run_id,
                owner_id=worker.owner_id,
                owner_pid=worker.pid,
                owner_hostname=worker.hostname,
                allowed_statuses=allowed_statuses,
                manifest=manifest,
            )
            try:
                workspace = self.root / "workspaces" / manifest.run_id / "repo"
                if not workspace.exists():
                    workspace = self.workspaces.create(
                        manifest.run_id,
                        package.public.repository.url,
                        package.public.repository.base_commit,
                    )
                workspace = self.workspaces.validate_managed_workspace(
                    workspace
                )
                if self.state.latest_checkpoint(manifest.run_id) is None:
                    self.workspaces.validate_pristine(
                        workspace,
                        package.public.repository.url,
                        package.public.repository.base_commit,
                    )
                public_review_base_provenance = (
                    self._prepare_public_review_base_provenance(
                        manifest=manifest,
                        task=package.public,
                        workspace=workspace,
                    )
                )
                return self._execute(
                    package,
                    workspace,
                    manifest,
                    normalized_model,
                    public_review_base_provenance=(
                        public_review_base_provenance
                    ),
                    worker_claim=worker_claim,
                )
            except RunOwnershipConflict:
                raise
            except Exception as exc:
                events = self.state.list_events(manifest.run_id)
                if any(
                    event.type in {EventType.RUN_COMPLETED, EventType.RUN_FAILED}
                    for event in events
                ):
                    raise
                if self._evaluation_receipt_path(
                    manifest.run_id
                ).exists():
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
            _allowed_worker_statuses={
                RunStatus.CREATED,
                RunStatus.SUSPENDED,
                RunStatus.RUNNING,
            },
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
            or not AgentRunner._live_plan_matches_manifest(
                manifest,
                authorization,
            )
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

    @staticmethod
    def _live_plan_matches_manifest(
        manifest: RunManifest,
        authorization: LiveExecutionAuthorization,
    ) -> bool:
        """Bind the complete hash-approved plan at the paid-call boundary."""

        try:
            plan = json.loads(
                Path(authorization.plan_path).read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return False
        if not isinstance(plan, dict):
            return False
        runtime_contract = plan.get("runtime_contract")
        corrective = bool(
            manifest.experiment is not None
            and manifest.experiment.purpose
            == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_CORRECTIVE_PILOT
        )
        saturation = bool(
            manifest.experiment is not None
            and manifest.experiment.purpose
            == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_SATURATION_PILOT
        )
        review_evidence = bool(
            manifest.experiment is not None
            and manifest.experiment.purpose
            == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_REVIEW_EVIDENCE_PILOT
        )
        coverage_review = bool(
            manifest.experiment is not None
            and manifest.experiment.purpose
            == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REVIEW_PILOT
        )
        coverage_rejection = bool(
            manifest.experiment is not None
            and manifest.experiment.purpose
            == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REJECTION_PILOT
        )
        generic_baseline_readiness = bool(
            manifest.experiment is not None
            and manifest.experiment.purpose
            == ExperimentPurpose.GENERIC_BASELINE_READINESS
        )
        workflow_completion_probe = bool(
            manifest.experiment is not None
            and manifest.experiment.purpose
            == ExperimentPurpose.WORKFLOW_COMPLETION_PROBE
        )
        if not any(
            (
                generic_baseline_readiness,
                workflow_completion_probe,
                corrective,
                saturation,
                review_evidence,
                coverage_review,
                coverage_rejection,
            )
        ):
            return runtime_contract is None
        try:
            # Keep start/resume on the same complete suite, task, schedule,
            # model, budget, pricing, review and runtime comparison used by
            # post-run qualification. This import is local to avoid making
            # the agent runner depend on evaluation modules at import time.
            from patchloop.evals.qualification import (
                _execution_plan_matches,
            )

            return _execution_plan_matches(
                plan=plan,
                manifest=manifest,
            )
        except Exception:
            return False

    def _prepare_public_review_base_provenance(
        self,
        *,
        manifest: RunManifest,
        task: PublicTask,
        workspace: Path,
    ) -> Artifact | None:
        """Build once, then validate and reuse V10/V11 base-anchor provenance."""

        if manifest.context_policy_version not in {
            "phase-evidence-v10",
            "phase-evidence-v11",
        }:
            return None
        contract = manifest.public_review_contract
        if contract is None:
            raise ContractError(
                "V10/V11 requires a public review contract for base provenance"
            )
        expected = build_public_review_base_provenance(
            contract,
            repository_url=task.repository.url,
            base_commit=task.repository.base_commit,
            read_base_file=lambda path: self.workspaces.read_base_file(
                workspace,
                path,
            ),
        )
        events = self.state.list_events(manifest.run_id)
        if not events:
            return self.artifacts.put_json(expected)
        started = [
            event
            for event in events
            if event.type == EventType.RUN_STARTED
        ]
        if (
            len(started) != 1
            or started[0].actor != "runner"
            or started[0].payload.get("task_id") != manifest.task_id
        ):
            raise RecoveryError(
                "V10/V11 run lacks one authoritative base provenance source"
            )
        try:
            artifact = Artifact.model_validate(
                started[0].payload.get(
                    "public_review_base_provenance_artifact"
                )
            )
            document = json.loads(
                self.artifacts.read_bytes(artifact).decode("utf-8")
            )
            validate_public_review_base_provenance_document(
                document,
                contract=contract,
                repository_url=task.repository.url,
                base_commit=task.repository.base_commit,
            )
        except (UnicodeDecodeError, ValueError, RecoveryError, ContractError) as exc:
            raise RecoveryError(
                "V10/V11 public review base provenance is invalid"
            ) from exc
        if document != expected:
            raise RecoveryError(
                "V10/V11 public review base provenance does not match Git HEAD"
            )
        return artifact

    def _execute(
        self,
        package: TaskPackage,
        workspace: Path,
        manifest: RunManifest,
        model: str,
        *,
        public_review_base_provenance: Artifact | None = None,
        worker_claim: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        task_dir = package.root
        system_prompt, tool_schemas = self._runtime_contract(manifest)
        if (
            manifest.context_policy_version == "phase-evidence-v11"
            and worker_claim is None
        ):
            raise RecoveryError(
                "phase-evidence-v11 requires an active worker claim"
            )
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
        if (
            manifest.tool_schema_version in {"v3", "v4", "v5", "v6"}
            and manifest.probe_image_digest is not None
            and (
                not isinstance(sandbox, DockerSandbox)
                or sandbox.probe_image_identity()
                != manifest.probe_image_digest
            )
        ):
            raise ContractError(
                "run manifest probe image does not match the dedicated "
                "self-validation sandbox image"
            )
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
            tool_schema_version=manifest.tool_schema_version,
            context_policy_version=manifest.context_policy_version,
            fault=manifest.fault,
        )
        existing_events = self.state.list_events(manifest.run_id)
        if existing_events:
            self._validate_generic_baseline_runtime_resume_contract(
                manifest=manifest,
                events=existing_events,
                system_prompt=system_prompt,
                tool_schemas=tool_schemas,
            )
        if (
            manifest.context_policy_version
            in {"phase-evidence-v10", "phase-evidence-v11"}
            and public_review_base_provenance is None
        ):
            raise ContractError(
                "V10/V11 execution requires public review base provenance"
            )
        checkpoint = self.state.latest_checkpoint(manifest.run_id)
        recovered_initial_phase: Phase | None = None
        if existing_events:
            if checkpoint is None:
                recovered_initial_phase = self._recover_initial_prefix(
                    manifest,
                    workspace,
                    existing_events,
                )
            else:
                self._reconcile_workspace_head(checkpoint, workspace)
                recovered_patch = gateway.reconcile_interrupted_patch(
                    checkpoint
                )
                recovered_tool: tuple[str, ToolResult] | None = None
                if recovered_patch is not None:
                    recovered_tool = ("apply_patch", recovered_patch)
                else:
                    # Only a prepared patch may legitimately move the
                    # worktree away from the last checkpoint. Validate the
                    # old durable boundary before replaying a read/check
                    # action or promoting any event suffix into a checkpoint.
                    self._reconcile_checkpoint_workspace(
                        checkpoint,
                        workspace,
                    )
                    recovered_tool = (
                        gateway.reconcile_interrupted_action(checkpoint)
                    )
                if recovered_tool is not None:
                    tool_name, recovered_result = recovered_tool
                    if (
                        recovered_result.status == "failed"
                        and recovered_result.output.get("fatal") is True
                    ):
                        raise RecoveryError(
                            recovered_result.error_message
                            or "interrupted tool recovery failed"
                        )
                    phase = self._phase_after_checkpoint(checkpoint)
                    phase = self._phase_after_tool(
                        manifest.run_id,
                        phase,
                        tool_name,
                        recovered_result,
                        package.public,
                        workspace,
                    )
                    checkpoint = self._checkpoint(
                        manifest,
                        workspace,
                        phase,
                        self._usage(manifest.run_id),
                        recovered_result,
                        task=package.public,
                    )
                else:
                    phase = self._phase_after_checkpoint(checkpoint)
                    suffix_events = [
                        event
                        for event in self.state.list_events(
                            manifest.run_id
                        )
                        if event.sequence > checkpoint.through_sequence
                        and event.type != EventType.CHECKPOINT_SAVED
                    ]
                    if suffix_events:
                        checkpoint = self._checkpoint(
                            manifest,
                            workspace,
                            phase,
                            self._usage(manifest.run_id),
                            task=package.public,
                        )
                    else:
                        self._ensure_checkpoint_event(checkpoint)
                recovered_barriers = (
                    gateway.reconcile_same_turn_barriers()
                )
                if recovered_barriers:
                    checkpoint = self.state.latest_checkpoint(
                        manifest.run_id
                    )
                    if checkpoint is None:
                        raise RecoveryError(
                            "same-turn barrier recovery lacks a durable checkpoint"
                        )
                    checkpoint = self._checkpoint(
                        manifest,
                        workspace,
                        self._phase_after_checkpoint(checkpoint),
                        self._usage(manifest.run_id),
                        task=package.public,
                    )
                self._reconcile_workspace(manifest, workspace)
        else:
            generic_runtime_document = (
                self._generic_baseline_runtime_evidence_document(
                    manifest=manifest,
                    system_prompt=system_prompt,
                    tool_schemas=tool_schemas,
                )
            )
            runtime_contract_metadata: dict[str, Any] = {}
            if (
                generic_runtime_document is None
                and manifest.context_policy_version in {
                    "phase-evidence-v8",
                    "phase-evidence-v9",
                    "phase-evidence-v10",
                    "phase-evidence-v11",
                }
            ):
                runtime_contract_metadata = {
                    "schema_version": (
                        "corrective-runtime-contract-v5"
                        if manifest.context_policy_version
                        == "phase-evidence-v11"
                        else (
                            "corrective-runtime-contract-v4"
                            if manifest.context_policy_version
                            == "phase-evidence-v10"
                            else (
                                "corrective-runtime-contract-v3"
                                if manifest.context_policy_version
                                == "phase-evidence-v9"
                                else "corrective-runtime-contract-v2"
                            )
                        )
                    )
                }
            runtime_contract = self.artifacts.put_json(
                generic_runtime_document
                or {
                    **runtime_contract_metadata,
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
                    **(
                        {
                            "runtime_contract_artifact": (
                                runtime_contract.model_dump(mode="json")
                            )
                        }
                        if generic_runtime_document is not None
                        or manifest.tool_schema_version in {"v4", "v5", "v6"}
                        else {}
                    ),
                    **(
                        {
                            "public_review_base_provenance_artifact": (
                                public_review_base_provenance.model_dump(
                                    mode="json"
                                )
                            )
                        }
                        if public_review_base_provenance is not None
                        else {}
                    ),
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
        phase = (
            checkpoint.phase
            if checkpoint
            else recovered_initial_phase or Phase.INTAKE
        )
        if phase == Phase.INTAKE:
            phase = self._transition(manifest.run_id, phase, Phase.REPRODUCE)
        if checkpoint is None:
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
            adapter = self._model_adapter(
                model,
                manifest,
                self._completed_tools(manifest.run_id),
                bool(package.public.probe_profiles),
            )
            while True:
                if (
                    manifest.context_policy_version
                    in {
                        "phase-evidence-v9",
                        "phase-evidence-v10",
                        "phase-evidence-v11",
                    }
                    and self._review_rejection_count(manifest.run_id)
                    > _MAX_RECOVERABLE_REVIEW_REJECTIONS
                ):
                    raise SubmissionProtocolError(
                        "structured review evidence was rejected three times"
                    )
                if manifest.context_policy_version not in {
                    "phase-evidence-v3",
                    "phase-evidence-v4",
                    "phase-evidence-v5",
                    "phase-evidence-v6",
                    "phase-evidence-v7",
                    "phase-evidence-v8",
                    "phase-evidence-v9",
                    "phase-evidence-v10",
                    "phase-evidence-v11",
                }:
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
                if manifest.context_policy_version in {
                    "phase-evidence-v5",
                    "phase-evidence-v6",
                    "phase-evidence-v7",
                    "phase-evidence-v8",
                    "phase-evidence-v9",
                    "phase-evidence-v10",
                    "phase-evidence-v11",
                }:
                    # V5 binds the ledger to the exact durable prefix. A
                    # MemoryRetrieved event appended above must therefore be
                    # included before ContextBuilt is emitted.
                    events = self.state.list_events(manifest.run_id)
                built_context = build_context_with_evidence(
                    package.public,
                    events,
                    checkpoint,
                    memory_text,
                    policy_version=manifest.context_policy_version,
                    artifact_store=self.artifacts,
                    budget=manifest.budget,
                    max_output_tokens=manifest.model.max_output_tokens,
                    public_review_contract=(
                        manifest.public_review_contract
                    ),
                    model_provider=manifest.model.provider,
                )
                context = built_context.rendered
                coverage_rejection_feedback = (
                    json.loads(context).get(
                        "coverage_rejection_feedback"
                    )
                    if manifest.context_policy_version
                    == "phase-evidence-v11"
                    else None
                )
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
                worker_claim_evidence = (
                    {
                        "schema_version": "worker-claim-evidence-v1",
                        **worker_claim,
                    }
                    if manifest.context_policy_version
                    == "phase-evidence-v11"
                    and worker_claim is not None
                    else None
                )
                request_artifact = self.artifacts.put_json(
                    {
                        "schema_version": "model-request-evidence-v1",
                        "provider": manifest.model.provider,
                        "endpoint": request_endpoint,
                        "request_body": request_body,
                        "request_body_hash": request_body_hash,
                        "context_build": built_context.evidence,
                        **(
                            {"worker_claim": worker_claim_evidence}
                            if worker_claim_evidence is not None
                            else {}
                        ),
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
                        **(
                            {"worker_claim": worker_claim_evidence}
                            if worker_claim_evidence is not None
                            else {}
                        ),
                        **(
                            {
                                "investigation_ledger_hash": (
                                    built_context.evidence[
                                        "investigation_ledger"
                                    ]["content_hash"]
                                ),
                                "investigation_source_through_sequence": (
                                    built_context.evidence[
                                        "investigation_ledger"
                                    ]["source_through_sequence"]
                                ),
                                "investigation_no_progress_streak": (
                                    built_context.evidence[
                                        "investigation_ledger"
                                    ]["no_progress_streak"]
                                ),
                                "investigation_exploration_admitted": (
                                    built_context.evidence[
                                        "investigation_ledger"
                                    ]["exploration_admitted"]
                                ),
                                **(
                                    {
                                        "investigation_tail_block_reasons": (
                                            built_context.evidence[
                                                "investigation_ledger"
                                            ]["tail_block_reasons"]
                                        ),
                                        "investigation_tail_remaining_tokens": (
                                            built_context.evidence[
                                                "investigation_ledger"
                                            ]["tail_remaining_tokens"]
                                        ),
                                        "investigation_tail_observation_count": (
                                            built_context.evidence[
                                                "investigation_ledger"
                                            ]["tail_observation_count"]
                                        ),
                                        "investigation_tail_max_observed_input_tokens": (
                                            built_context.evidence[
                                                "investigation_ledger"
                                            ][
                                                "tail_max_observed_input_tokens"
                                            ]
                                        ),
                                        "investigation_tail_max_positive_growth": (
                                            built_context.evidence[
                                                "investigation_ledger"
                                            ]["tail_max_positive_growth"]
                                        ),
                                        "investigation_tail_projected_next_input_tokens": (
                                            built_context.evidence[
                                                "investigation_ledger"
                                            ][
                                                "tail_projected_next_input_tokens"
                                            ]
                                        ),
                                        "investigation_tail_projected_model_turns": (
                                            built_context.evidence[
                                                "investigation_ledger"
                                            ][
                                                "tail_projected_model_turns"
                                            ]
                                        ),
                                        "investigation_tail_reserved_tokens": (
                                            built_context.evidence[
                                                "investigation_ledger"
                                            ]["tail_reserved_tokens"]
                                        ),
                                        "investigation_tail_max_output_tokens": (
                                            built_context.evidence[
                                                "investigation_ledger"
                                            ]["tail_max_output_tokens"]
                                        ),
                                    }
                                    if manifest.context_policy_version
                                    in {
                                        "phase-evidence-v5",
                                        "phase-evidence-v6",
                                        "phase-evidence-v7",
                                        "phase-evidence-v8",
                                        "phase-evidence-v9",
                                        "phase-evidence-v10",
                                        "phase-evidence-v11",
                                    }
                                    else {}
                                ),
                                **(
                                    {
                                        "probe_ledger_hash": (
                                            built_context.evidence[
                                                "probe_ledger"
                                            ]["content_hash"]
                                        ),
                                        "probe_ledger_source_through_sequence": (
                                            built_context.evidence[
                                                "probe_ledger"
                                            ][
                                                "source_through_sequence"
                                            ]
                                        ),
                                        "probe_ledger_entry_count": (
                                            built_context.evidence[
                                                "probe_ledger"
                                            ]["entry_count"]
                                        ),
                                    }
                                    if manifest.context_policy_version
                                    in {
                                        "phase-evidence-v6",
                                        "phase-evidence-v7",
                                        "phase-evidence-v8",
                                        "phase-evidence-v9",
                                        "phase-evidence-v10",
                                        "phase-evidence-v11",
                                    }
                                    else {}
                                ),
                            }
                            if manifest.context_policy_version
                            in {
                                "phase-evidence-v4",
                                "phase-evidence-v5",
                                "phase-evidence-v6",
                                "phase-evidence-v7",
                                "phase-evidence-v8",
                                "phase-evidence-v9",
                                "phase-evidence-v10",
                                "phase-evidence-v11",
                            }
                            else {}
                        ),
                        **(
                            {
                                "investigation_read_search_admitted": (
                                    built_context.evidence[
                                        "read_search_policy"
                                    ]["admitted"]
                                ),
                                "investigation_read_search_reason_codes": (
                                    built_context.evidence[
                                        "read_search_policy"
                                    ]["reason_codes"]
                                ),
                                "investigation_semantic_replay_count": (
                                    built_context.evidence[
                                        "read_search_policy"
                                    ]["semantic_replay_count"]
                                ),
                                "investigation_semantic_replay_threshold": (
                                    built_context.evidence[
                                        "read_search_policy"
                                    ]["semantic_replay_threshold"]
                                ),
                                "investigation_saturation_mutation_epoch_sequence": (
                                    built_context.evidence[
                                        "read_search_policy"
                                    ]["mutation_epoch_sequence"]
                                ),
                            }
                            if manifest.context_policy_version
                            in {
                                "phase-evidence-v8",
                                "phase-evidence-v9",
                                "phase-evidence-v10",
                                "phase-evidence-v11",
                            }
                            else {}
                        ),
                        **(
                            {
                                "review_evidence_pinning_active": (
                                    built_context.evidence[
                                        "review_evidence"
                                    ]["pinning_active"]
                                ),
                                "review_evidence_worktree_diff_hash": (
                                    built_context.evidence[
                                        "review_evidence"
                                    ]["worktree_diff_hash"]
                                ),
                                "review_evidence_mutation_event_sequence": (
                                    built_context.evidence[
                                        "review_evidence"
                                    ]["mutation_event_sequence"]
                                ),
                                "review_evidence_passing_check_event_sequences": (
                                    built_context.evidence[
                                        "review_evidence"
                                    ]["passing_check_event_sequences"]
                                ),
                                "review_evidence_source_get_diff_sequence": (
                                    built_context.evidence[
                                        "review_evidence"
                                    ]["source_get_diff_sequence"]
                                ),
                                "review_evidence_citable_event_sequences": (
                                    built_context.evidence[
                                        "review_evidence"
                                    ]["citable_event_sequences"]
                                ),
                                "review_evidence_incomplete_event_sequences": (
                                    built_context.evidence[
                                        "review_evidence"
                                    ]["incomplete_event_sequences"]
                                ),
                            }
                            if manifest.context_policy_version
                            in {
                                "phase-evidence-v9",
                                "phase-evidence-v10",
                                "phase-evidence-v11",
                            }
                            else {}
                        ),
                        **(
                            {
                                "review_evidence_coverage_target_event_sequences": (
                                    built_context.evidence[
                                        "review_evidence"
                                    ][
                                        "coverage_target_event_sequences"
                                    ]
                                )
                            }
                            if manifest.context_policy_version
                            in {"phase-evidence-v10", "phase-evidence-v11"}
                            else {}
                        ),
                        **(
                            {
                                "coverage_rejection_feedback": (
                                    built_context.evidence.get(
                                        "coverage_rejection_feedback"
                                    )
                                )
                            }
                            if manifest.context_policy_version
                            == "phase-evidence-v11"
                            else {}
                        ),
                    },
                )
                if manifest.context_policy_version in {
                    "phase-evidence-v3",
                    "phase-evidence-v4",
                    "phase-evidence-v5",
                    "phase-evidence-v6",
                    "phase-evidence-v7",
                    "phase-evidence-v8",
                    "phase-evidence-v9",
                    "phase-evidence-v10",
                    "phase-evidence-v11",
                }:
                    pre_generation_reason = self._pre_generation_budget_reason(
                        manifest,
                        usage,
                    )
                    if pre_generation_reason is not None:
                        self._block_model_generation(
                            manifest=manifest,
                            built_context=built_context,
                            request_artifact=request_artifact,
                            request_body_hash=request_body_hash,
                            reason_code=pre_generation_reason,
                            usage=usage,
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
                        if manifest.context_policy_version in {
                            "phase-evidence-v3",
                            "phase-evidence-v4",
                            "phase-evidence-v5",
                            "phase-evidence-v6",
                            "phase-evidence-v7",
                            "phase-evidence-v8",
                            "phase-evidence-v9",
                            "phase-evidence-v10",
                            "phase-evidence-v11",
                        }:
                            usage.input_token_count_calls += 1
                            self._block_model_generation(
                                manifest=manifest,
                                built_context=built_context,
                                request_artifact=request_artifact,
                                request_body_hash=request_body_hash,
                                reason_code="exact_request_budget_exceeded",
                                usage=usage,
                                requested_input_tokens=requested_input_tokens,
                                remaining_tokens=remaining_tokens,
                                input_token_count_calls=1,
                            )
                        raise ContractError(
                            "remaining token budget cannot fund the exact input "
                            "plus one bounded model response"
                        )
                    turn = adapter.execute_request(
                        request_body,
                        requested_input_tokens=requested_input_tokens,
                    )
                else:
                    if (
                        manifest.context_policy_version
                        in {
                            "phase-evidence-v3",
                            "phase-evidence-v4",
                            "phase-evidence-v5",
                            "phase-evidence-v6",
                            "phase-evidence-v7",
                            "phase-evidence-v8",
                            "phase-evidence-v9",
                            "phase-evidence-v10",
                            "phase-evidence-v11",
                        }
                        and usage.input_tokens + usage.output_tokens
                        >= manifest.budget.max_total_tokens
                    ):
                        self._block_model_generation(
                            manifest=manifest,
                            built_context=built_context,
                            request_artifact=request_artifact,
                            request_body_hash=request_body_hash,
                            reason_code="token_budget_exhausted",
                            usage=usage,
                        )
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
                v4_apply_precedes_finish = (
                    manifest.tool_schema_version in {"v4", "v5", "v6"}
                    and bool(finish_calls)
                    and any(
                        call.name == "apply_patch"
                        for call in turn.tool_calls[
                            : turn.tool_calls.index(finish_calls[0])
                        ]
                    )
                )
                if (
                    finish_calls
                    and len(turn.tool_calls) != 1
                    and not v4_apply_precedes_finish
                ):
                    if (
                        manifest.budget.max_tool_calls is not None
                        and usage.tool_calls >= manifest.budget.max_tool_calls
                    ):
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
                        tool_schema_version=manifest.tool_schema_version,
                        additional_missing_evidence=[
                            "finish_task_must_be_only_action"
                        ],
                    )
                    if (
                        not result.output.get("replayed")
                        and not result.output.get("admission_blocked")
                    ):
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
                for call_index, call in enumerate(turn.tool_calls, 1):
                    if (
                        manifest.budget.max_tool_calls is not None
                        and usage.tool_calls >= manifest.budget.max_tool_calls
                    ):
                        raise ContractError("tool call budget exhausted")
                    if call.name == "finish_task":
                        if manifest.tool_schema_version not in {
                            "v2",
                            "v3",
                            "v4",
                            "v5",
                            "v6",
                        }:
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
                            tool_schema_version=(
                                manifest.tool_schema_version
                            ),
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
                    execution_context = (
                        {
                            "request_artifact_id": (
                                request_artifact.artifact_id
                            ),
                            "phase": phase.value,
                            "presented_tool_results": (
                                built_context.evidence.get(
                                    "tool_results",
                                    [],
                                )
                            ),
                            **(
                                {
                                    "review_evidence": (
                                        built_context.evidence.get(
                                            "review_evidence"
                                        )
                                    )
                                }
                                if manifest.context_policy_version
                                in {
                                    "phase-evidence-v9",
                                    "phase-evidence-v10",
                                    "phase-evidence-v11",
                                }
                                else {}
                            ),
                            **(
                                {
                                    "coverage_rejection_feedback": (
                                        coverage_rejection_feedback
                                    )
                                }
                                if manifest.context_policy_version
                                == "phase-evidence-v11"
                                else {}
                            ),
                        }
                        if call.name == "review_task"
                        else None
                    )
                    result = gateway.execute(
                        call.name,
                        call.action_id,
                        call.arguments,
                        execution_context=execution_context,
                    )
                    if (
                        manifest.tool_schema_version in {"v4", "v5", "v6"}
                        and call.name == "apply_patch"
                    ):
                        for blocked_index, blocked_call in enumerate(
                            turn.tool_calls[call_index:],
                            call_index + 1,
                        ):
                            gateway.block_same_turn_action(
                                blocked_call.name,
                                blocked_call.action_id,
                                blocked_call.arguments,
                                source_action_id=call.action_id,
                                source_result_status=result.status,
                                source_model_event_id=model_event.event_id,
                                source_call_index=call_index,
                                blocked_call_index=blocked_index,
                            )
                    if (
                        not result.output.get("replayed")
                        and not result.output.get("admission_blocked")
                    ):
                        usage.tool_calls += 1
                        if not result.output.get("semantic_replay"):
                            usage.wall_clock_ms += int(
                                (
                                    result.finished_at
                                    - result.started_at
                                ).total_seconds()
                                * 1000
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
                        manifest.context_policy_version
                        in {
                            "phase-evidence-v9",
                            "phase-evidence-v10",
                            "phase-evidence-v11",
                        }
                        and call.name == "review_task"
                        and result.status != "succeeded"
                        and self._review_rejection_count(manifest.run_id)
                        > _MAX_RECOVERABLE_REVIEW_REJECTIONS
                    ):
                        raise SubmissionProtocolError(
                            "structured review evidence was rejected three times"
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
                    if (
                        manifest.tool_schema_version in {"v4", "v5", "v6"}
                        and call.name == "apply_patch"
                    ):
                        break
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
            if self._evaluation_receipt_path(manifest.run_id).exists():
                raise
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
        if manifest.tool_schema_version in {"v2", "v3", "v4", "v5", "v6"}:
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
                submitted_patch_bytes = self.artifacts.read_bytes(
                    submitted_patch_artifact
                )
            except (
                KeyError,
                OSError,
                RecoveryError,
                TypeError,
                ValueError,
            ) as exc:
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
        self._write_runtime_bytes_atomic(
            patch_path,
            submitted_patch_bytes,
        )
        completed_evaluation = self._load_completed_evaluation(
            manifest,
            expected_patch_hash=summary.patch_hash,
            submitted_patch_artifact=submitted_patch_artifact,
            expected_official=sandbox.official,
        )
        if completed_evaluation is None:
            evaluator = EvaluationEngine(
                self.workspaces,
                sandbox,
                self.artifacts,
            )
            evaluator_started = time.monotonic()
            result = evaluator.evaluate(
                task_dir,
                patch_path,
                manifest,
                usage=usage,
                submitted_patch_artifact=submitted_patch_artifact,
            )
            evaluator_duration_ms = int(
                (time.monotonic() - evaluator_started) * 1000
            )
            self._persist_evaluation_receipt(
                manifest,
                result,
                evaluator_duration_ms=evaluator_duration_ms,
                expected_patch_hash=summary.patch_hash,
                submitted_patch_artifact=submitted_patch_artifact,
                expected_official=sandbox.official,
            )
        else:
            result, evaluator_duration_ms = completed_evaluation
        classification_error: dict[str, str] | None = None
        try:
            failure = classify_failure(
                result,
                load_task_package(task_dir).public.split,
                root=self.root,
                phase=Phase.REVIEW,
                events=self.state.list_events(manifest.run_id),
            )
        except (ContractError, OSError, ValueError) as exc:
            failure = None
            classification_error = {
                "type": type(exc).__name__,
                "message": self._safe_error_message(exc),
            }
        failure_payload = None
        if failure is not None:
            failure_payload = {
                "failure_id": failure.failure_id,
                "primary_cause": failure.primary_cause,
                "classification_method": failure.classification_method,
            }
        self.state.finalize_run(
            manifest.run_id,
            status=RunStatus.COMPLETED,
            result=result,
            event_type=EventType.RUN_COMPLETED,
            actor="evaluator",
            payload={
                "scope_compliant_success": result.scope_compliant_success,
                "official": result.official,
                "duration_ms": evaluator_duration_ms,
                "failure_classification_error": classification_error,
            },
            failure_payload=failure_payload,
        )
        return result.model_dump(mode="json")

    def _load_completed_evaluation(
        self,
        manifest: RunManifest,
        *,
        expected_patch_hash: str,
        submitted_patch_artifact: Artifact | None,
        expected_official: bool,
    ) -> tuple[RunResult, int] | None:
        receipt_path = self._evaluation_receipt_path(manifest.run_id)
        if not receipt_path.exists():
            return None
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RecoveryError(
                "completed evaluation receipt is unreadable"
            ) from exc
        if not isinstance(receipt, dict):
            raise RecoveryError("completed evaluation receipt is malformed")
        file_hashes = receipt.get("file_hashes")
        duration_ms = receipt.get("evaluator_duration_ms")
        result_artifact_id = receipt.get(
            "submitted_patch_artifact_id"
        )
        if (
            receipt.get("schema_version") != _EVALUATION_RECEIPT_SCHEMA
            or receipt.get("run_id") != manifest.run_id
            or receipt.get("worktree_diff_hash") != expected_patch_hash
            or not isinstance(result_artifact_id, str)
            or not result_artifact_id
            or (
                submitted_patch_artifact is not None
                and result_artifact_id
                != submitted_patch_artifact.artifact_id
            )
            or not isinstance(duration_ms, int)
            or duration_ms < 0
            or not isinstance(file_hashes, dict)
            or set(file_hashes)
            != {"manifest.json", "result.json", "provenance.json"}
        ):
            raise RecoveryError(
                "completed evaluation receipt conflicts with the run"
            )
        result = self._validate_completed_evaluation_files(
            manifest,
            file_hashes=file_hashes,
            expected_patch_hash=expected_patch_hash,
            expected_result_artifact_id=result_artifact_id,
            submitted_patch_artifact=submitted_patch_artifact,
            expected_official=expected_official,
        )
        return result, duration_ms

    def _persist_evaluation_receipt(
        self,
        manifest: RunManifest,
        result: RunResult,
        *,
        evaluator_duration_ms: int,
        expected_patch_hash: str,
        submitted_patch_artifact: Artifact | None,
        expected_official: bool,
    ) -> None:
        run_dir = self.artifacts.root / "runs" / manifest.run_id
        result_artifact_id = result.submitted_patch_artifact_id
        if not isinstance(result_artifact_id, str) or not result_artifact_id:
            raise RecoveryError(
                "completed evaluation lacks its submitted patch artifact"
            )
        if (
            submitted_patch_artifact is not None
            and result_artifact_id
            != submitted_patch_artifact.artifact_id
        ):
            raise RecoveryError(
                "completed evaluation patch artifact conflicts with "
                "the accepted submission"
            )
        file_hashes: dict[str, str] = {}
        for name in ("manifest.json", "result.json", "provenance.json"):
            try:
                file_hashes[name] = sha256_bytes(
                    (run_dir / name).read_bytes()
                )
            except OSError as exc:
                raise RecoveryError(
                    "evaluator did not persist a complete result bundle"
                ) from exc
        persisted = self._validate_completed_evaluation_files(
            manifest,
            file_hashes=file_hashes,
            expected_patch_hash=expected_patch_hash,
            expected_result_artifact_id=result_artifact_id,
            submitted_patch_artifact=submitted_patch_artifact,
            expected_official=expected_official,
        )
        if persisted != result:
            raise RecoveryError(
                "evaluator return value differs from its persisted result"
            )
        receipt = {
            "schema_version": _EVALUATION_RECEIPT_SCHEMA,
            "run_id": manifest.run_id,
            "worktree_diff_hash": expected_patch_hash,
            "submitted_patch_artifact_id": result_artifact_id,
            "evaluator_duration_ms": evaluator_duration_ms,
            "file_hashes": file_hashes,
        }
        self.artifacts.write_text_atomic(
            run_dir / "evaluation-receipt.json",
            json.dumps(receipt, indent=2, sort_keys=True),
        )

    def _validate_completed_evaluation_files(
        self,
        manifest: RunManifest,
        *,
        file_hashes: dict[str, Any],
        expected_patch_hash: str,
        expected_result_artifact_id: str,
        submitted_patch_artifact: Artifact | None,
        expected_official: bool,
    ) -> RunResult:
        run_dir = self.artifacts.root / "runs" / manifest.run_id
        contents: dict[str, bytes] = {}
        try:
            for name in (
                "manifest.json",
                "result.json",
                "provenance.json",
            ):
                declared_hash = file_hashes.get(name)
                content = (run_dir / name).read_bytes()
                if (
                    not isinstance(declared_hash, str)
                    or sha256_bytes(content) != declared_hash
                ):
                    raise RecoveryError(
                        "completed evaluation file hash does not match "
                        f"its receipt: {name}"
                    )
                contents[name] = content
            persisted_manifest = RunManifest.model_validate_json(
                contents["manifest.json"]
            )
            result = RunResult.model_validate_json(
                contents["result.json"]
            )
            provenance = json.loads(contents["provenance.json"])
        except RecoveryError:
            raise
        except (
            OSError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            raise RecoveryError(
                "completed evaluation bundle is invalid"
            ) from exc
        if not isinstance(provenance, dict):
            raise RecoveryError(
                "completed evaluation provenance is malformed"
            )
        verifier_evidence = self._validated_verifier_evidence(result)
        if (
            persisted_manifest != manifest
            or result.run_id != manifest.run_id
            or result.evaluation_status != "completed"
            or result.official is not expected_official
            or provenance.get("patch_hash") != expected_patch_hash
            or provenance.get("diff_hash") != expected_patch_hash
            or provenance.get("submitted_patch_content_hash")
            != expected_patch_hash
            or provenance.get("submitted_patch_artifact_id")
            != expected_result_artifact_id
            or result.submitted_patch_artifact_id
            != expected_result_artifact_id
            or provenance.get("verifier_evidence_schema_version")
            != "verifier-evidence-v1"
            or provenance.get("verifier_evidence_artifacts")
            != verifier_evidence
        ):
            raise RecoveryError(
                "completed evaluation bundle conflicts with immutable run "
                "evidence"
            )
        if (
            submitted_patch_artifact is not None
            and (
                submitted_patch_artifact.artifact_id
                != expected_result_artifact_id
                or submitted_patch_artifact.content_hash
                != expected_patch_hash
            )
        ):
            raise RecoveryError(
                "accepted patch artifact conflicts with completed evaluation"
            )
        return result

    def _validated_verifier_evidence(
        self,
        result: RunResult,
    ) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        for verifier_result in result.verifier_results:
            raw_artifacts = verifier_result.details.get(
                "evidence_artifacts"
            )
            if not verifier_result.evidence_artifact_ids:
                if raw_artifacts not in (None, []):
                    raise RecoveryError(
                        "verifier result has unreferenced evidence artifacts"
                    )
                continue
            if (
                not isinstance(raw_artifacts, list)
                or len(raw_artifacts)
                != len(verifier_result.evidence_artifact_ids)
            ):
                raise RecoveryError(
                    "verifier result lacks complete evidence descriptors"
                )
            descriptors: list[dict[str, Any]] = []
            for expected_id, raw_artifact in zip(
                verifier_result.evidence_artifact_ids,
                raw_artifacts,
                strict=True,
            ):
                try:
                    artifact = Artifact.model_validate(raw_artifact)
                    self.artifacts.read_bytes(artifact)
                except (RecoveryError, TypeError, ValueError) as exc:
                    raise RecoveryError(
                        "verifier evidence artifact failed integrity "
                        "validation"
                    ) from exc
                if artifact.artifact_id != expected_id:
                    raise RecoveryError(
                        "verifier evidence identity conflicts with its result"
                    )
                descriptors.append(
                    artifact.model_dump(mode="json")
                )
            evidence.extend(descriptors)
        return evidence

    def _evaluation_receipt_path(self, run_id: str) -> Path:
        return (
            self.artifacts.root
            / "runs"
            / run_id
            / "evaluation-receipt.json"
        )

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
        terminal_error: dict[str, Any] = {
            "type": type(error).__name__,
            "message": safe_message,
        }
        error_code = getattr(error, "code", None)
        if isinstance(error_code, str):
            terminal_error["code"] = error_code
        error_details = self._safe_error_details(error)
        if error_details:
            terminal_error["details"] = error_details
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
            terminal_error=terminal_error,
        )
        failure = classify_failure(
            result,
            load_task_package(task_dir).public.split,
            root=self.root,
            phase=phase,
            events=events,
        )
        failure_payload = None
        if failure is not None:
            failure_payload = {
                "failure_id": failure.failure_id,
                "primary_cause": failure.primary_cause,
                "classification_method": failure.classification_method,
        }
        run_dir = self.artifacts.root / "runs" / manifest.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "evaluation-receipt.json").unlink(missing_ok=True)
        self.artifacts.write_text_atomic(
            run_dir / "manifest.json",
            manifest.model_dump_json(indent=2),
        )
        self.artifacts.write_text_atomic(
            run_dir / "result.json",
            result.model_dump_json(indent=2),
        )
        self.artifacts.write_text_atomic(
            run_dir / "provenance.json",
            json.dumps(
                {
                    "evaluation_reached": False,
                    "outcome_kind": outcome_kind.value,
                    "error_type": type(error).__name__,
                    "error_code": error_code,
                },
                indent=2,
            ),
        )
        self.state.finalize_run(
            manifest.run_id,
            status=RunStatus.FAILED,
            result=result,
            event_type=EventType.RUN_FAILED,
            actor="runner",
            payload={
                "outcome_kind": outcome_kind.value,
                "error_type": type(error).__name__,
                "error_code": error_code,
                "error_details": error_details or None,
                "message": safe_message,
                "model_cost_usd": usage.model_cost_usd,
            },
            failure_payload=failure_payload,
        )
        return result.model_dump(mode="json")

    @staticmethod
    def _safe_error_message(error: Exception) -> str:
        message = str(error)
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            message = message.replace(api_key, "[REDACTED]")
        return message[:2_000]

    @staticmethod
    def _safe_error_details(error: Exception) -> dict[str, Any]:
        raw = getattr(error, "details", None)
        if not isinstance(raw, dict) or not raw:
            return {}
        api_key = os.environ.get("OPENAI_API_KEY")

        def redact(value: Any) -> Any:
            if isinstance(value, str):
                return value.replace(api_key, "[REDACTED]") if api_key else value
            if isinstance(value, list):
                return [redact(item) for item in value]
            if isinstance(value, dict):
                return {
                    str(key): redact(item)
                    for key, item in value.items()
                }
            if value is None or isinstance(value, (bool, int, float)):
                return value
            return str(value)

        return redact(raw)

    def _write_runtime_bytes_atomic(
        self,
        path: Path,
        content: bytes,
    ) -> None:
        try:
            root = self.root.resolve()
            resolved = path.resolve()
        except OSError as exc:
            raise RecoveryError(
                "runtime artifact path cannot be resolved"
            ) from exc
        if not resolved.is_relative_to(root) or path.is_symlink():
            raise RecoveryError("runtime artifact path escapes the run root")
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(
            f".{path.name}.{uuid.uuid4().hex}.tmp"
        )
        try:
            with temporary.open("xb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

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
        if manifest.context_policy_version in {
            "phase-evidence-v2",
            "phase-evidence-v3",
            "phase-evidence-v4",
            "phase-evidence-v5",
            "phase-evidence-v6",
            "phase-evidence-v7",
            "phase-evidence-v8",
            "phase-evidence-v9",
            "phase-evidence-v10",
            "phase-evidence-v11",
        }:
            evidence_task = (
                task
                or load_task_package(
                    self._find_task(manifest)
                ).public
            )
            evidence = diff_bound_evidence(
                evidence_task,
                events,
                summary.patch_hash,
                structured_review_required=(
                    manifest.context_policy_version
                    in {
                        "phase-evidence-v6",
                        "phase-evidence-v7",
                        "phase-evidence-v8",
                        "phase-evidence-v9",
                        "phase-evidence-v10",
                        "phase-evidence-v11",
                    }
                ),
                coverage_review_required=(
                    manifest.context_policy_version
                    in {"phase-evidence-v10", "phase-evidence-v11"}
                ),
                probe_available=bool(evidence_task.probe_profiles),
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
                **(
                    {
                        "model_calls": (
                            manifest.budget.max_model_calls
                            - usage.model_calls
                        )
                    }
                    if manifest.budget.max_model_calls is not None
                    else {}
                ),
                **(
                    {
                        "tool_calls": (
                            manifest.budget.max_tool_calls
                            - usage.tool_calls
                        )
                    }
                    if manifest.budget.max_tool_calls is not None
                    else {}
                ),
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
    def _generic_baseline_runtime_evidence_document(
        *,
        manifest: RunManifest,
        system_prompt: str,
        tool_schemas: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        if manifest.experiment is None or manifest.experiment.purpose not in {
            ExperimentPurpose.GENERIC_BASELINE_READINESS,
            ExperimentPurpose.WORKFLOW_COMPLETION_PROBE,
        }:
            return None
        workflow_completion_probe = bool(
            manifest.experiment.purpose
            == ExperimentPurpose.WORKFLOW_COMPLETION_PROBE
        )
        document = {
            "schema_version": (
                "workflow-completion-runtime-evidence-v1"
                if workflow_completion_probe
                else "generic-baseline-runtime-evidence-v1"
            ),
            "transport_max_retries": manifest.model.transport_max_retries,
            "system_prompt": system_prompt,
            "tools": tool_schemas,
            "tool_schema_version": manifest.tool_schema_version,
            "context_policy_version": manifest.context_policy_version,
        }
        if workflow_completion_probe:
            document["call_guard_policy"] = (
                "model-tool-observability-only-v1"
            )
        return document

    def _validate_generic_baseline_runtime_resume_contract(
        self,
        *,
        manifest: RunManifest,
        events: list[Any],
        system_prompt: str,
        tool_schemas: list[dict[str, Any]],
    ) -> None:
        expected = self._generic_baseline_runtime_evidence_document(
            manifest=manifest,
            system_prompt=system_prompt,
            tool_schemas=tool_schemas,
        )
        if expected is None:
            return
        started = [
            event for event in events if event.type == EventType.RUN_STARTED
        ]
        try:
            if len(started) != 1:
                raise ValueError("expected one RunStarted event")
            event = started[0]
            artifact = Artifact.model_validate(
                event.payload.get("runtime_contract_artifact")
            )
            if (
                event.actor != "runner"
                or event.run_id != manifest.run_id
                or event.payload.get("task_id") != manifest.task_id
                or event.payload.get("artifact_role") != "runtime-contract"
                or event.payload.get("artifact_id") != artifact.artifact_id
                or event.payload.get("artifact_path") != artifact.path
                or artifact.media_type
                != "application/json; charset=utf-8"
            ):
                raise ValueError("runtime descriptor does not match RunStarted")
            observed = json.loads(
                self.artifacts.read_bytes(artifact).decode("utf-8")
            )
            if observed != expected:
                raise ValueError("runtime evidence bytes do not match the manifest")
        except (
            UnicodeDecodeError,
            ValueError,
            RecoveryError,
        ) as exc:
            raise RecoveryError(
                "generic baseline runtime contract artifact is invalid during recovery"
            ) from exc

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
            and manifest.context_policy_version
            in {"phase-evidence-v2", "phase-evidence-v3"}
        ):
            return SYSTEM_PROMPT_V2, TOOL_SCHEMAS_V2
        if (
            manifest.tool_schema_version == "v2"
            and manifest.context_policy_version
            in {"phase-evidence-v4", "phase-evidence-v5"}
        ):
            return SYSTEM_PROMPT_V3, TOOL_SCHEMAS_V2
        if (
            manifest.tool_schema_version == "v3"
            and manifest.context_policy_version == "phase-evidence-v6"
        ):
            return SYSTEM_PROMPT_V4, TOOL_SCHEMAS_V3
        if (
            manifest.tool_schema_version == "v4"
            and manifest.context_policy_version
            in {"phase-evidence-v7", "phase-evidence-v8"}
        ):
            return SYSTEM_PROMPT_V5, TOOL_SCHEMAS_V4
        if (
            manifest.tool_schema_version == "v4"
            and manifest.context_policy_version == "phase-evidence-v9"
        ):
            return SYSTEM_PROMPT_V6, TOOL_SCHEMAS_V4
        if (
            manifest.tool_schema_version == "v5"
            and manifest.context_policy_version == "phase-evidence-v10"
        ):
            return SYSTEM_PROMPT_V7, TOOL_SCHEMAS_V5
        if (
            manifest.tool_schema_version == "v6"
            and manifest.context_policy_version == "phase-evidence-v11"
        ):
            return SYSTEM_PROMPT_V8, TOOL_SCHEMAS_V6
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
        tool_schema_version: str,
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
            structured_review_required=(
                tool_schema_version in {"v3", "v4", "v5", "v6"}
            ),
            coverage_review_required=(tool_schema_version in {"v5", "v6"}),
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
            task_review_event = None
            task_review_artifact = None
            if tool_schema_version in {"v3", "v4", "v5", "v6"}:
                task_review_event = next(
                    (
                        event
                        for event in self.state.list_events(run_id)
                        if event.sequence
                        == readiness.task_review_event_sequence
                    ),
                    None,
                )
                try:
                    task_review_artifact = Artifact.model_validate(
                        task_review_event.payload.get(
                            "review_artifact"
                        )
                        if task_review_event is not None
                        else None
                    )
                    review_document = json.loads(
                        self.artifacts.read_bytes(
                            task_review_artifact
                        ).decode("utf-8", errors="strict")
                    )
                except (
                    OSError,
                    TypeError,
                    ValueError,
                    UnicodeDecodeError,
                    json.JSONDecodeError,
                ) as exc:
                    raise RecoveryError(
                        "accepted structured review artifact is unavailable"
                    ) from exc
                if (
                    review_document.get("schema_version")
                    != (
                        "task-review-v3"
                        if tool_schema_version in {"v5", "v6"}
                        else (
                            "task-review-v2"
                            if tool_schema_version == "v4"
                            else "task-review-v1"
                        )
                    )
                    or review_document.get("run_id") != run_id
                    or review_document.get("worktree_diff_hash")
                    != summary.patch_hash
                    or review_document.get("source_get_diff_sequence")
                    != readiness.review_event_sequence
                    or review_document.get("request_artifact_id")
                    != task_review_event.payload.get(
                        "request_artifact_id"
                    )
                    or task_review_artifact.content_hash
                    != task_review_event.payload.get(
                        "review_content_hash"
                    )
                ):
                    raise RecoveryError(
                        "structured review artifact conflicts with current "
                        "trace evidence"
                    )
                if tool_schema_version in {"v4", "v5", "v6"}:
                    review_contract = self.state.get_manifest(
                        run_id
                    ).public_review_contract
                    requirement_rows = review_document.get("requirements")
                    if (
                        review_contract is None
                        or review_document.get(
                            "public_review_contract_hash"
                        )
                        != review_contract.content_hash
                        or not isinstance(requirement_rows, list)
                        or {
                            item.get("requirement_id")
                            for item in requirement_rows
                            if isinstance(item, dict)
                        }
                        != {
                            item.requirement_id
                            for item in review_contract.requirements
                        }
                        or len(requirement_rows)
                        != len(review_contract.requirements)
                    ):
                        raise RecoveryError(
                            "task review does not cover its public contract"
                        )
                    if tool_schema_version in {"v5", "v6"}:
                        coverage_rows = review_document.get(
                            "coverage_targets"
                        )
                        coverage = review_document.get(
                            "public_review_coverage"
                        )
                        authoritative_target_ids = [
                            target.coverage_target_id
                            for requirement in review_contract.requirements
                            for target in requirement.coverage_targets
                        ]
                        if (
                            not isinstance(coverage_rows, list)
                            or [
                                item.get("coverage_target_id")
                                for item in coverage_rows
                                if isinstance(item, dict)
                            ]
                            != authoritative_target_ids
                            or not isinstance(coverage, dict)
                            or coverage.get("schema_version")
                            != "public-review-coverage-v1"
                            or coverage.get("coverage_complete") is not True
                            or coverage.get("ready_for_submission") is not True
                            or coverage.get(
                                "authoritative_coverage_target_ids"
                            )
                            != authoritative_target_ids
                            or coverage.get("verified_coverage_target_ids")
                            != authoritative_target_ids
                            or coverage.get(
                                "unresolved_coverage_target_ids"
                            )
                            != []
                            or task_review_event.payload.get(
                                "coverage_complete"
                            )
                            is not True
                        ):
                            raise RecoveryError(
                                "task-review-v3 coverage decision is not submission-ready"
                            )
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
                **(
                    {
                        "source_task_review_sequence": (
                            readiness.task_review_event_sequence
                        ),
                        "task_review_artifact": (
                            task_review_artifact.model_dump(mode="json")
                        ),
                        "task_review_content_hash": (
                            task_review_artifact.content_hash
                        ),
                    }
                    if task_review_artifact is not None
                    else {}
                ),
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
                    **(
                        {
                            "source_task_review_sequence": (
                                readiness.task_review_event_sequence
                            ),
                            "task_review_artifact": (
                                task_review_artifact.model_dump(
                                    mode="json"
                                )
                            ),
                            "task_review_content_hash": (
                                task_review_artifact.content_hash
                            ),
                        }
                        if task_review_artifact is not None
                        else {}
                    ),
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
        manifest = self.state.get_manifest(run_id)
        source_tool_schema = manifest.tool_schema_version
        structured_review_required = source_tool_schema in {
            "v3",
            "v4",
            "v5",
            "v6",
        }
        source_task_review_sequence = None
        task_review_artifact = None
        task_review_content_hash = None
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
            review_payload = {
                "worktree_diff_hash": diff_hash,
                "source_get_diff_sequence": source_sequence,
                "request_artifact_id": request_artifact_id,
                "complete_tool_result": True,
            }
            source_task_review_sequence = result.output.get(
                "source_task_review_sequence"
            )
            task_review_artifact = result.output.get(
                "task_review_artifact"
            )
            task_review_content_hash = result.output.get(
                "task_review_content_hash"
            )
            review_provenance_present = any(
                value is not None
                for value in (
                    source_task_review_sequence,
                    task_review_artifact,
                    task_review_content_hash,
                )
            )
            if structured_review_required or review_provenance_present:
                if (
                    not isinstance(source_task_review_sequence, int)
                    or not isinstance(task_review_artifact, dict)
                    or not isinstance(task_review_content_hash, str)
                ):
                    raise RecoveryError(
                        "accepted structured finish result has incomplete review provenance"
                    )
                try:
                    review_descriptor = Artifact.model_validate(
                        task_review_artifact
                    )
                    review_document = json.loads(
                        self.artifacts.read_bytes(
                            review_descriptor
                        ).decode("utf-8", errors="strict")
                    )
                except (
                    OSError,
                    TypeError,
                    ValueError,
                    UnicodeDecodeError,
                    json.JSONDecodeError,
                ) as exc:
                    raise RecoveryError(
                        "accepted v3 finish result has an invalid review artifact"
                    ) from exc
                source_review = next(
                    (
                        event
                        for event in self.state.list_events(run_id)
                        if event.sequence
                        == source_task_review_sequence
                    ),
                    None,
                )
                expected_review_schema = (
                    "task-review-v3"
                    if source_tool_schema in {"v5", "v6"}
                    else (
                        "task-review-v2"
                        if source_tool_schema == "v4"
                        else "task-review-v1"
                    )
                )
                coverage_consistent = True
                if source_tool_schema in {"v5", "v6"}:
                    review_contract = manifest.public_review_contract
                    coverage_rows = review_document.get(
                        "coverage_targets"
                    )
                    coverage = review_document.get(
                        "public_review_coverage"
                    )
                    authoritative_target_ids = (
                        [
                            target.coverage_target_id
                            for requirement in review_contract.requirements
                            for target in requirement.coverage_targets
                        ]
                        if review_contract is not None
                        else []
                    )
                    coverage_consistent = bool(
                        review_contract is not None
                        and review_document.get(
                            "public_review_contract_hash"
                        )
                        == review_contract.content_hash
                        and isinstance(coverage_rows, list)
                        and all(
                            isinstance(item, dict)
                            for item in coverage_rows
                        )
                        and [
                            item.get("coverage_target_id")
                            for item in coverage_rows
                        ]
                        == authoritative_target_ids
                        and isinstance(coverage, dict)
                        and coverage.get("schema_version")
                        == "public-review-coverage-v1"
                        and coverage.get(
                            "authoritative_coverage_target_ids"
                        )
                        == authoritative_target_ids
                        and coverage.get(
                            "verified_coverage_target_ids"
                        )
                        == authoritative_target_ids
                        and coverage.get(
                            "unresolved_coverage_target_ids"
                        )
                        == []
                        and coverage.get("coverage_complete") is True
                        and coverage.get("ready_for_submission") is True
                        and source_review is not None
                        and source_review.payload.get(
                            "coverage_target_count"
                        )
                        == len(authoritative_target_ids)
                        and source_review.payload.get(
                            "coverage_complete"
                        )
                        is True
                        and source_review.payload.get(
                            "verified_coverage_target_ids"
                        )
                        == authoritative_target_ids
                        and source_review.payload.get(
                            "unresolved_coverage_target_ids"
                        )
                        == []
                    )
                if (
                    review_descriptor.content_hash
                    != task_review_content_hash
                    or review_document.get("schema_version")
                    != expected_review_schema
                    or review_document.get("run_id") != run_id
                    or review_document.get("worktree_diff_hash")
                    != diff_hash
                    or source_review is None
                    or source_review.type
                    != EventType.TOOL_SUCCEEDED
                    or source_review.payload.get("tool")
                    != "review_task"
                    or source_review.payload.get("review_artifact")
                    != task_review_artifact
                    or source_review.payload.get(
                        "review_content_hash"
                    )
                    != task_review_content_hash
                    or source_review.payload.get(
                        "source_get_diff_sequence"
                    )
                    != source_sequence
                    or not coverage_consistent
                ):
                    raise RecoveryError(
                        "accepted structured finish review provenance is inconsistent"
                    )
                review_payload.update(
                    {
                        "source_task_review_sequence": (
                            source_task_review_sequence
                        ),
                        "task_review_artifact": task_review_artifact,
                        "task_review_content_hash": (
                            task_review_content_hash
                        ),
                        "self_attestation": True,
                        "deterministic_correctness_claimed": False,
                    }
                )
            expected.append(
                (
                    EventType.REVIEW_RECORDED,
                    "submission-gate",
                    review_payload,
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
                    **(
                        {
                            "source_task_review_sequence": (
                                source_task_review_sequence
                            ),
                            "task_review_artifact": task_review_artifact,
                            "task_review_content_hash": (
                                task_review_content_hash
                            ),
                        }
                        if source_task_review_sequence is not None
                        else {}
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
                        **(
                            {
                                "source_task_review_sequence": (
                                    source_task_review_sequence
                                ),
                                "task_review_artifact": (
                                    task_review_artifact
                                ),
                                "task_review_content_hash": (
                                    task_review_content_hash
                                ),
                            }
                            if source_task_review_sequence is not None
                            else {}
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

    def _review_rejection_count(self, run_id: str) -> int:
        """Count failed structured reviews in the active mutation epoch."""

        events = self.state.list_events(run_id)
        mutation_sequence = max(
            (
                event.sequence
                for event in events
                if event.type == EventType.PATCH_APPLIED
            ),
            default=0,
        )
        return sum(
            event.sequence > mutation_sequence
            and event.type == EventType.TOOL_FAILED
            and event.payload.get("tool") == "review_task"
            for event in events
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
        """Repair an interrupted structured submission before another call."""

        checkpoint = self.state.latest_checkpoint(manifest.run_id)
        if manifest.tool_schema_version not in {
            "v2",
            "v3",
            "v4",
            "v5",
            "v6",
        }:
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
        if (
            tool == "review_task"
            and result.output.get("review_schema_version")
            == "task-review-v3"
            and result.output.get("coverage_complete") is False
            and phase == Phase.REVIEW
        ):
            return self._transition(run_id, phase, Phase.IMPLEMENT)
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
        roots = (
            repository_root() / "tasks",
            repository_root() / "fixtures" / "task-packages",
        )
        for root in roots:
            if not root.is_dir():
                continue
            for public_path in root.rglob("public.yaml"):
                package = load_task_package(public_path.parent)
                if (
                    package.public.task_id == manifest.task_id
                    and package.public.task_version == manifest.task_version
                    and package.public_spec_hash == manifest.public_spec_hash
                ):
                    return public_path.parent
        raise RecoveryError(f"task package for run {manifest.run_id} is unavailable")

    def _model_adapter(
        self,
        model: str,
        manifest: RunManifest,
        completed_tools: list[str],
        probe_available: bool = False,
    ) -> ModelAdapter:
        if model == "mock":
            return MockModelAdapter(
                manifest.task_id,
                completed_tools,
                structured_finish=manifest.tool_schema_version
                in {"v2", "v3", "v4", "v5", "v6"},
                structured_review=manifest.tool_schema_version
                in {"v3", "v4", "v5", "v6"},
                structured_probe=(
                    manifest.tool_schema_version in {"v3", "v4", "v5", "v6"}
                    and manifest.probe_image_digest is not None
                    and probe_available
                ),
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
        self._reconcile_checkpoint_workspace(checkpoint, workspace)

    def _reconcile_checkpoint_workspace(
        self,
        checkpoint: Checkpoint,
        workspace: Path,
    ) -> None:
        if WorkspaceManager.untracked_files(workspace):
            raise RecoveryError(
                "agent workspace contains untracked files during recovery"
            )
        summary = WorkspaceManager.diff_summary(workspace)
        if summary.patch_hash != checkpoint.worktree_diff_hash:
            raise RecoveryError("workspace diff hash does not match the latest durable checkpoint")
        self._reconcile_workspace_head(checkpoint, workspace)

    def _recover_initial_prefix(
        self,
        manifest: RunManifest,
        workspace: Path,
        events,
    ) -> Phase:
        """Recover the narrow startup prefix before the first checkpoint."""

        expected_fault = (
            manifest.fault.type
            if manifest.fault.type in {"context-reset", "test-timeout"}
            else None
        )
        types = [event.type for event in events]
        allowed_prefix = [EventType.RUN_STARTED]
        if types[:1] != allowed_prefix:
            raise RecoveryError(
                "run without a checkpoint has an invalid startup prefix"
            )
        run_started = events[0]
        try:
            runtime_artifact = Path(
                str(run_started.payload["artifact_path"])
            )
        except KeyError as exc:
            raise RecoveryError(
                "startup prefix lacks its runtime contract artifact"
            ) from exc
        if (
            run_started.actor != "runner"
            or run_started.payload.get("task_id") != manifest.task_id
            or not runtime_artifact.is_file()
        ):
            raise RecoveryError(
                "startup prefix conflicts with the immutable run contract"
            )

        index = 1
        if expected_fault is not None and len(events) > index:
            fault_event = events[index]
            if (
                fault_event.type != EventType.FAULT_INJECTED
                or fault_event.actor != "fault-injector"
                or fault_event.payload != {"fault": expected_fault}
            ):
                raise RecoveryError(
                    "run without a checkpoint has an invalid fault prefix"
                )
            index += 1
        if expected_fault is not None and len(events) == 1:
            self.state.append_event(
                manifest.run_id,
                EventType.FAULT_INJECTED,
                actor="fault-injector",
                payload={"fault": expected_fault},
            )

        phase = Phase.INTAKE
        if len(events) > index:
            transition = events[index]
            if (
                transition.type != EventType.PHASE_CHANGED
                or transition.actor != "phase-machine"
                or transition.payload
                != {
                    "from": Phase.INTAKE.value,
                    "to": Phase.REPRODUCE.value,
                }
            ):
                raise RecoveryError(
                    "run without a checkpoint has an invalid phase prefix"
                )
            phase = Phase.REPRODUCE
            index += 1
        if len(events) != index:
            raise RecoveryError(
                "run without a checkpoint contains non-startup events"
            )
        if WorkspaceManager.untracked_files(workspace):
            raise RecoveryError(
                "startup workspace contains untracked files"
            )
        summary = WorkspaceManager.diff_summary(workspace)
        if summary.patch_hash != sha256_text(""):
            raise RecoveryError(
                "startup workspace changed before its first checkpoint"
            )
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=workspace,
            capture_output=True,
            text=True,
            check=False,
        )
        if head.returncode != 0 or not head.stdout.strip():
            raise RecoveryError("startup workspace has no valid Git HEAD")
        return phase

    @staticmethod
    def _reconcile_workspace_head(
        checkpoint: Checkpoint,
        workspace: Path,
    ) -> None:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=workspace,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        if head != checkpoint.repository_head:
            raise RecoveryError("workspace HEAD does not match the latest durable checkpoint")

    def _phase_after_checkpoint(self, checkpoint: Checkpoint) -> Phase:
        phase = checkpoint.phase
        for event in self.state.list_events(checkpoint.run_id):
            if (
                event.sequence <= checkpoint.through_sequence
                or event.type != EventType.PHASE_CHANGED
            ):
                continue
            try:
                source = Phase(str(event.payload["from"]))
                target = Phase(str(event.payload["to"]))
            except (KeyError, ValueError) as exc:
                raise RecoveryError(
                    "phase transition after checkpoint is malformed"
                ) from exc
            if source != phase:
                raise RecoveryError(
                    "phase transition after checkpoint is not contiguous"
                )
            validate_transition(source, target)
            phase = target
        return phase

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
            elif event.type == EventType.MODEL_GENERATION_BLOCKED:
                usage.input_token_count_calls += int(
                    event.payload.get("input_token_count_calls", 0)
                )
        manifest = self.state.get_manifest(run_id)
        usage.model_cost_usd = calculate_model_cost(usage, manifest.model)
        return usage

    @staticmethod
    def _pre_generation_budget_reason(
        manifest: RunManifest,
        usage: Usage,
    ) -> str | None:
        if (
            manifest.budget.max_model_calls is not None
            and usage.model_calls >= manifest.budget.max_model_calls
        ):
            return "model_call_budget_exhausted"
        if (
            manifest.budget.max_tool_calls is not None
            and usage.tool_calls >= manifest.budget.max_tool_calls
        ):
            return "tool_call_budget_exhausted"
        if (
            usage.wall_clock_ms
            >= manifest.budget.wall_clock_timeout_seconds * 1000
        ):
            return "wall_clock_budget_exhausted"
        return None

    def _block_model_generation(
        self,
        *,
        manifest: RunManifest,
        built_context: BuiltContext,
        request_artifact: Artifact,
        request_body_hash: str,
        reason_code: str,
        usage: Usage,
        requested_input_tokens: int | None = None,
        remaining_tokens: int | None = None,
        input_token_count_calls: int = 0,
    ) -> None:
        retry_evidence = built_context.evidence.get(
            "rejected_mutation_retry"
        )
        retry_present = bool(
            isinstance(retry_evidence, dict)
            and retry_evidence.get("included") is True
        )
        retry_candidate = (
            retry_evidence.get("candidate", {})
            if isinstance(retry_evidence, dict)
            else {}
        )
        payload = {
            "reason_code": reason_code,
            "error_code": ModelGenerationBudgetError.code,
            "generation_started": False,
            "request_artifact_id": request_artifact.artifact_id,
            "request_artifact_path": request_artifact.path,
            "request_body_hash": request_body_hash,
            "requested_input_tokens": requested_input_tokens,
            "remaining_tokens": remaining_tokens,
            "max_output_tokens": manifest.model.max_output_tokens,
            "input_token_count_calls": input_token_count_calls,
            "retry_context_present": retry_present,
            "retry_candidate_content_hash": (
                retry_candidate.get("content_hash")
                if isinstance(retry_candidate, dict)
                else None
            ),
        }
        if reason_code == "exact_request_budget_exceeded":
            payload["schema_version"] = _EXACT_REQUEST_GENERATION_BLOCK_SCHEMA
        elif reason_code in _COUNTER_GENERATION_BLOCK_REASONS:
            optional_call_limits = bool(
                manifest.budget.max_model_calls is None
                or manifest.budget.max_tool_calls is None
            )
            payload.update(
                {
                    "schema_version": (
                        _OPTIONAL_COUNTER_GENERATION_BLOCK_SCHEMA
                        if optional_call_limits
                        else _COUNTER_GENERATION_BLOCK_SCHEMA
                    ),
                    "model_calls_used": usage.model_calls,
                    "max_model_calls": manifest.budget.max_model_calls,
                    "tool_calls_used": usage.tool_calls,
                    "max_tool_calls": manifest.budget.max_tool_calls,
                    "wall_clock_ms": usage.wall_clock_ms,
                    "wall_clock_timeout_ms": (
                        manifest.budget.wall_clock_timeout_seconds * 1000
                    ),
                    "total_tokens_used": (
                        usage.input_tokens + usage.output_tokens
                    ),
                    "max_total_tokens": manifest.budget.max_total_tokens,
                }
            )
            if optional_call_limits:
                payload["disabled_budget_dimensions"] = [
                    dimension
                    for dimension, limit in (
                        ("model_calls", manifest.budget.max_model_calls),
                        ("tool_calls", manifest.budget.max_tool_calls),
                    )
                    if limit is None
                ]
        self.state.append_event(
            manifest.run_id,
            EventType.MODEL_GENERATION_BLOCKED,
            actor="budget-guard",
            payload=payload,
        )
        if reason_code == "exact_request_budget_exceeded":
            message = (
                "remaining token budget cannot fund the exact input plus one "
                "bounded model response"
            )
        else:
            message = f"model generation blocked: {reason_code}"
        raise ModelGenerationBudgetError(message, details=payload)

    def _assert_budget(self, manifest: RunManifest, usage: Usage) -> None:
        if (
            manifest.budget.max_model_calls is not None
            and usage.model_calls >= manifest.budget.max_model_calls
        ):
            raise ContractError("model call budget exhausted")
        if (
            manifest.budget.max_tool_calls is not None
            and usage.tool_calls >= manifest.budget.max_tool_calls
        ):
            raise ContractError("tool call budget exhausted")
        if usage.input_tokens + usage.output_tokens >= manifest.budget.max_total_tokens:
            raise ContractError("token budget exhausted")
        if usage.wall_clock_ms >= manifest.budget.wall_clock_timeout_seconds * 1000:
            raise ContractError("wall clock budget exhausted")

    @staticmethod
    def _assert_consumed_budget(manifest: RunManifest, usage: Usage) -> None:
        if (
            manifest.budget.max_model_calls is not None
            and usage.model_calls > manifest.budget.max_model_calls
        ):
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
    self_validation: bool = False,
) -> dict[str, Any]:
    if model == "openai":
        raise ContractError(
            "direct live runs are disabled; use an approved experiment-v2 suite"
        )
    return AgentRunner().start(
        task,
        model=model,
        memory_condition=memory_condition,
        self_validation=self_validation,
    )


def resume_from_cli(run_id: str) -> dict[str, Any]:
    runner = AgentRunner()
    manifest = runner.state.get_manifest(run_id)
    if manifest.model.provider == "openai":
        raise ContractError(
            "direct live resume is disabled; approved campaign resume is not implemented"
        )
    return runner.resume(run_id)
