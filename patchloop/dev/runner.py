"""Single mutable PatchLoop development runtime."""

from __future__ import annotations

import copy
import json
import os
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from time import monotonic
from typing import Any

from pydantic import ValidationError

from patchloop.agent.count_diagnostics import (
    input_count_error_metadata,
    input_count_request_metadata,
)
from patchloop.agent.model import (
    EncryptedReasoningContinuationItem as ProviderReasoningItem,
)
from patchloop.agent.model import FunctionCallContinuationRef as ProviderFunctionCallRef
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.agent.request_transport import BoundedResponsesClient
from patchloop.agent.usage_diagnostics import usage_failure_message
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact, ModelConfig, RunManifest, VerdictState
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev import (
    completion_context,
    completion_reproduction,
    correction_drafts,
    diagnosis_context,
    evidence_focus,
    helper_recovery,
    history_search,
    inspection_focus,
    native_compaction,
    probe_recheck,
    repair_context,
    segments,
    test_comparison,
    thin_policy,
    working_plan,
)
from patchloop.dev.check_feedback import output_tail
from patchloop.dev.compaction import CompactionAdapter
from patchloop.dev.completion_budget import (
    CompletionState,
    completion_budget,
    minimum_successor_calls,
    mutation_attempt_budget,
    test_addition_budget,
)
from patchloop.dev.context import SourceProjection, build_observed_source_index
from patchloop.dev.contracts import (
    DEV_RUNTIME_ID,
    DevModelTurn,
    DevRunEnvelope,
    DevRunRequest,
    DevTerminal,
    DevToolContractFailure,
    DevToolContractViolation,
    DevToolResult,
    EncryptedReasoningContinuationItem,
    FunctionCallContinuationRef,
    ProviderContinuationArtifact,
    ProviderContinuationRef,
    RequestedTool,
    RunEnvelope,
    RunRequest,
    dev_tool_surface_hash,
)
from patchloop.dev.conversation import (
    APPEND_POLICY,
    SEGMENT_RULES,
    WINDOW_POLICY,
    WINDOW_RULES,
    assemble_model_input,
    history_metadata,
    segment_seed,
    validate_model_input,
)
from patchloop.dev.cost import (
    COMPLETION_MINIMUM_POLICY,
    COMPLETION_RECOVERY_POLICY,
    COMPLETION_RESERVE_POLICY,
    DEFAULT_COMPLETION_COST_POLICY,
    DEFAULT_OUTPUT_CEILING,
    FINALIZATION_OUTPUT_FLOOR,
    MINIMUM_OUTPUT_CEILING,
    PRICING_SOURCE,
    PRICING_VERIFIED_ON,
    DevCostLedger,
    ModelPricing,
    completion_cost_contract,
    correction_output_ceiling,
    pricing_for_model,
)
from patchloop.dev.dependency_sources import for_run as caller_sources_for_run
from patchloop.dev.evaluation_completion import (
    EvaluationCompletion,
    load_evaluation_completion,
    prepare_evaluation_completion,
)
from patchloop.dev.inspection_projection import (
    project_inspection_context,
    project_inspection_result,
)
from patchloop.dev.model import DEV_SYSTEM_PROMPT, MockDevAdapter
from patchloop.dev.model_state import compact_model_state
from patchloop.dev.native_sources import (
    PUBLIC_EVIDENCE_KIND,
    project_mutation_result,
    public_exchanges,
    reference_native_sources,
)
from patchloop.dev.probe_observation import probe_observation, project_probe_result
from patchloop.dev.public_history import NATIVE
from patchloop.dev.recovery_resources import (
    CHECK_OVERHEAD_SECONDS,
    FOLLOWUP_SECONDS,
    merge_resources,
    ordinary_route_supported,
    requested_revision_resources,
    successor_resources,
)
from patchloop.dev.repair_recheck import (
    latest_repair_check,
    repair_recheck_context,
    select_repair_recheck,
)
from patchloop.dev.state import DevJournal
from patchloop.dev.test_selection import recent_tests
from patchloop.dev.tools import (
    DevGatewayStateSnapshot,
    DevToolGateway,
    dev_tool_schemas,
    validate_tool_batch,
)
from patchloop.environment import load_exact_openai_api_key
from patchloop.errors import (
    ContractError,
    PatchLoopError,
    RecoveryError,
    ResumeContractMismatch,
)
from patchloop.git_execution import GitExecutionUncertain, run_git
from patchloop.prepared_probe_dependencies import admit, load_dependencies
from patchloop.prepared_source import admission_hash, load_source
from patchloop.repair import (
    RepairEnvelope,
    RepairRunRequest,
    RepairTask,
    load_delivery,
    prepared_sandbox,
    record_delivery,
)
from patchloop.repository import WorkspaceManager
from patchloop.runtime import (
    git_commit,
    make_run_id,
    repository_root,
    runtime_content_hash,
    runtime_content_paths,
)
from patchloop.sandbox import DockerSandbox, LocalSandbox
from patchloop.sandbox.probes import (
    PROBE_TIMEOUT_SECONDS,
    DockerProbeSandbox,
    probe_profile,
    probe_profile_hash,
)
from patchloop.sandbox.runner import SandboxCleanupError
from patchloop.task_loader import load_task_package, task_package_content_paths
from patchloop.util import canonical_json, sha256_bytes, sha256_json, utc_now
from patchloop.verifier.core import EvaluationEngine

_EVIDENCE_PLATEAU_WARNING_TURNS = 2
_FIRST_OBSERVATION_EXPLORATION = frozenset({
    "read_file", "search_files", "search_history", "run_probe", "run_tests", "run_check",
})


@dataclass
class _RunCounters:
    model_calls: int = 0
    compaction_calls: int = 0
    tool_actions: int = 0
    input_count_calls: int = 0
    protocol_recoveries: int = 0
    protocol_corrections_total: int = 0
    inspection_turns_at_diff: int = 0
    failed_mutation_repair_turns: int = 0
    failed_mutation_pending: bool = False
    failed_mutation_recovery_key: str | None = None
    mutation_recovery_used: bool = False
    check_recovery_used: bool = False
    check_recovery_used_ids: set[str] = field(default_factory=set)
    failed_check_pending: bool = False
    failed_check_repair_read_used: bool = False
    consecutive_no_evidence_gain_turns: int = 0
    current_anchor_diff_hash: str | None = None
    commitment_diff_hash: str | None = None
    commitment_trigger_no_gain_turns: int = 0


@dataclass
class _OneRunResult:
    public: dict[str, Any]
    stop_remaining: bool


@dataclass(frozen=True)
class _ToolPolicy:
    workflow_gate: str
    allowed_tools: frozenset[str]
    check_ids: tuple[str, ...]
    remaining_check_ids: tuple[str, ...]
    max_parallel_reads: int
    minimum_completion_calls: int
    completion_budget_calls: int
    mutation_recovery_reserve_calls: int
    check_recovery_reserve_calls: int
    check_recovery_reserve_ids: tuple[str, ...]
    completion_possible: bool
    protected_completion_possible: bool
    exploration_allowed: bool
    exploration_state: str
    commitment_action_state: str
    model_turns_available_for_exploration: int
    tool_actions_available_for_exploration: int
    closure_reason: str | None
    tools_closing_after_this_turn: tuple[str, ...]
    required_inspection_for_completion: bool
    targeted_check_repair_inspection: bool
    targeted_check_repair_required: bool
    targeted_mutation_repair_inspection: bool
    targeted_read_paths: tuple[str, ...]
    current_repair_read_reserve_calls: int = 0
    future_check_failure_slots: int = 0
    optional_mutation_completion_calls: int = 0
    optional_mutation_protected_calls: int = 0
    mutation_completion_possible: bool = False
    mutation_protected_completion_possible: bool = False
    inspection_uses_repair_credit: bool = False
    repair_inspection_policy: str = "protected-v1"
    inspection_reserve_calls: int = 0
    inspection_released_check_recovery_calls: int = 0
    completion_cost: dict[str, Any] | None = None
    repair_recheck: bool = False
    minimum_completion_tool_actions: int = 0
    completion_budget_tool_actions: int = 0
    optional_mutation_completion_tool_actions: int = 0
    optional_mutation_protected_tool_actions: int = 0
    inspection_reserve_tool_actions: int = 0
    original_failure_diagnostic: dict[str, Any] | None = None
    observation_correction: dict[str, Any] | None = None
    repair_path_diagnosis: dict[str, Any] | None = None
    helper_correction: dict[str, Any] | None = None
    first_observation: dict[str, Any] | None = None
    repair_prediction: dict[str, Any] | None = None
    repair_test_edit_enabled: bool = False
    repair_test_edit_minimum_calls: int = 0
    repair_test_edit_minimum_tool_actions: int = 0
    selected_test_reserve_tool_actions: int | None = None
    selected_test_comparison_required: bool = False

    @property
    def feedback_recovery_reserve_calls(self) -> int:
        return (
            self.mutation_recovery_reserve_calls
            + self.check_recovery_reserve_calls
            + self.current_repair_read_reserve_calls
        )


class _ProviderContinuationError(RecoveryError):
    pass


def default_state_root() -> Path:
    configured = os.environ.get("PATCHLOOP_STATE_ROOT")
    if configured:
        root = Path(configured).expanduser().resolve()
    elif os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        root = (Path(os.environ["LOCALAPPDATA"]) / "PatchLoop" / "dev-state").resolve()
    else:
        root = (Path.home() / ".local" / "state" / "patchloop" / "dev").resolve()
    repo = repository_root().resolve()
    if root == repo or root.is_relative_to(repo):
        raise ContractError("development run state must be outside the PatchLoop repository")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _runtime_hash() -> str:
    return runtime_content_hash()


def _model_hash(request: RunRequest, pricing: ModelPricing | None) -> str:
    from patchloop.dev import probe_cases

    return sha256_json(
        {
            "provider": request.provider,
            "model": request.model,
            "reasoning_effort": request.reasoning_effort,
            "context_policy": request.context_policy,
            **({"history_search_contract": history_search.contract()}
               if request.history_search_policy != "none" else {}),
            **({"agent_policy_contract": thin_policy.contract()}
               if request.agent_policy == "thin" else {}),
            **({"retained_source_chars": request.retained_source_chars}
               if request.retained_source_chars != 24_000 else {}),
            **({"caller_source_roots": request.caller_source_roots}
               if request.caller_source_roots else {}),
            **({"evaluation_reserve_seconds": request.evaluation_reserve_seconds}
               if isinstance(request, DevRunRequest)
               and request.evaluation_reserve_seconds else {}),
            **({"completion_cost_contract": completion_cost_contract(
                request.completion_cost_policy,
                max_correction_output_tokens=request.max_correction_output_tokens,
            )}
               if request.completion_cost_policy != DEFAULT_COMPLETION_COST_POLICY else {}),
            **({"repair_inspection_policy": request.repair_inspection_policy}
               if request.repair_inspection_policy != "protected-v1" else {}),
            **({"segment_contract": segments.contract(
                request.segment_boundary_policy, agent_policy=request.agent_policy)}
               if request.context_policy == segments.POLICY else {}),
            "compaction_contract": native_compaction.policy_contract(request),
            **({"planning_contract": working_plan.contract(request.planning_policy)}
               if request.planning_policy != "none" else {}),
            **({"probe_case_contract": probe_cases.contract(request.probe_policy)}
               if request.probe_policy != "none" else {}),
            **({"probe_recheck_contract": probe_recheck.contract()}
               if request.probe_recheck != "none" else {}),
            **({"reproduction_acquisition": request.reproduction_acquisition}
               if request.reproduction_acquisition != "none" else {}),
            "transport_max_retries": 0 if request.provider == "openai" else None,
            "service_tier": "default",
            "api_base_url": "https://api.openai.com/v1",
            "max_output_tokens": request.max_output_tokens,
            "reasoning_continuation": ("encrypted-v1" if request.provider == "openai" else "none"),
            "response_include": (
                ["reasoning.encrypted_content"] if request.provider == "openai" else []
            ),
            "pricing_source": PRICING_SOURCE if pricing else None,
            "pricing_verified_on": PRICING_VERIFIED_ON if pricing else None,
            "pricing": (
                {
                    "input": str(pricing.input_per_million_usd),
                    "cached_input": str(pricing.cached_input_per_million_usd),
                    "output": str(pricing.output_per_million_usd),
                }
                if pricing
                else None
            ),
        }
    )


def _resolve_task_file(task: Path) -> tuple[Path, Any]:
    selected = task.resolve()
    if selected.name != "public.yaml" or not selected.is_file():
        raise ContractError("--task must name an existing public.yaml file")
    package = load_task_package(selected.parent)
    return selected.parent, package


def _live_task_is_admitted(task_dir: Path, package: Any) -> None:
    if package.public.split != "dev-train":
        raise ContractError("live dev-head runs accept only the dev-train split")
    admitted_root = (repository_root() / "tasks" / "dev-train").resolve()
    if not task_dir.resolve().is_relative_to(admitted_root):
        raise ContractError("live dev-head task must be checked in under tasks/dev-train")
    if package.environment is None:
        raise ContractError("live dev-head task is missing environment.yaml")
    if not package.private.hidden_checks:
        raise ContractError("live dev-head task requires at least one hidden check")


def _require_tracked_clean_paths(
    root: Path, relative_paths: list[str], *, deadline: ExecutionDeadline | None = None,
) -> None:
    expected = sorted(set(relative_paths))
    tracked = run_git(root, "ls-files", "-z", "--", *expected, check=False, deadline=deadline)
    if tracked.returncode != 0:
        raise ContractError("cannot inspect live source tracking state")
    actual = sorted(path for path in tracked.stdout.split("\0") if path)
    if actual != expected:
        raise ContractError("live runtime and task inputs must all be tracked")
    status = run_git(
        root, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--", *expected,
        check=False, deadline=deadline,
    )
    if status.returncode != 0:
        raise ContractError("cannot inspect live source modification state")
    if status.stdout:
        raise ContractError("live runtime and task inputs must match HEAD exactly")


def _live_source_preflight(
    task_dir: Path, package: Any, *, deadline: ExecutionDeadline | None = None,
) -> None:
    root = repository_root().resolve()
    task_paths = [
        (task_dir / relative).resolve().relative_to(root).as_posix()
        for relative in task_package_content_paths(package)
    ]
    _require_tracked_clean_paths(
        root, [*runtime_content_paths(root), *task_paths], deadline=deadline,
    )


def _live_sandbox_preflight(
    package: Any, *, deadline: ExecutionDeadline | None = None,
) -> DockerSandbox:
    environment = package.environment
    if environment is None:
        raise ContractError("live evaluator environment is missing")
    sandbox = DockerSandbox(environment.evaluator_image)
    if not DockerSandbox.available(deadline=deadline):
        raise ContractError("Docker is unavailable; dev-head never starts or installs it")
    identity = sandbox.image_identity(deadline=deadline)
    if identity is None:
        raise ContractError(
            "required evaluator image is not local; dev-head never pulls or builds it"
        )
    if identity != environment.image_digest:
        raise ContractError("local evaluator image does not match environment.yaml")
    return sandbox


def _manifest(
    *,
    request: RunRequest,
    package: Any,
    run_id: str,
    sandbox_backend: str,
    pricing: ModelPricing | None,
    runtime_hash: str,
    model_hash: str,
    submitted_patch_hash: str,
    submitted_changed_files: list[str],
    created_at: Any,
    harness_git_commit: str,
    probe_evidence: list[Artifact] | None = None,
    probe_dependencies=None,
) -> RunManifest:
    return RunManifest(
        run_id=run_id,
        agent_policy=request.agent_policy,
        planning_policy=request.planning_policy,
        probe_policy=request.probe_policy,
        probe_recheck=request.probe_recheck,
        history_search_policy=request.history_search_policy,
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        base_commit=package.public.repository.base_commit,
        public_spec_hash=package.public_spec_hash,
        private_spec_hash=package.private_spec_hash,
        task_content_hash=package.task_content_hash,
        runtime_content_hash=runtime_hash,
        model_hash=model_hash,
        tool_surface_hash=dev_tool_surface_hash(
            history_search_policy=request.history_search_policy,
            agent_policy=request.agent_policy,
            planning_policy=request.planning_policy, probe_policy=request.probe_policy,
            probe_recheck=request.probe_recheck,
        ),
        sandbox_identity_hash=_sandbox_identity_hash(request, package, probe_dependencies),
        probe_image_digest=(probe_profile(probe_dependencies)["image_digest"]
                            if request.enable_probes else None),
        probe_profile_hash=(probe_profile_hash(probe_dependencies)
                            if request.enable_probes else None),
        probe_dependencies=probe_dependencies,
        probe_evidence=probe_evidence or [],
        probe_execution_count=len(probe_evidence or []),
        submitted_patch_content_hash=submitted_patch_hash,
        visible_check_diff_hash=submitted_patch_hash,
        submitted_changed_files=sorted(submitted_changed_files),
        harness_git_commit=harness_git_commit,
        model=ModelConfig(
            provider=request.provider,
            model_id=request.model,
            reasoning_effort=request.reasoning_effort,
            reasoning_continuation=("encrypted-v1" if request.provider == "openai" else "none"),
            transport_max_retries=0 if request.provider == "openai" else None,
            max_output_tokens=request.max_output_tokens,
            input_price_per_million_usd=(float(pricing.input_per_million_usd) if pricing else None),
            cached_input_price_per_million_usd=(
                float(pricing.cached_input_per_million_usd) if pricing else None
            ),
            output_price_per_million_usd=(
                float(pricing.output_per_million_usd) if pricing else None
            ),
        ),
        max_model_calls=request.limits.max_model_calls,
        max_tool_actions=request.limits.max_tool_actions,
        max_accepted_mutations=request.limits.max_accepted_mutations,
        wall_time_seconds=request.limits.wall_time_seconds,
        protocol_recovery_limit=request.limits.max_protocol_recoveries,
        sandbox_backend=sandbox_backend,
        evaluator_image_digest=(
            package.environment.image_digest
            if sandbox_backend == "docker" and package.environment
            else None
        ),
        created_at=created_at,
    )


def _pending_protocol_correction(journal: DevJournal) -> dict[str, Any] | None:
    """A started request does not consume a correction; a new decision does."""

    events = journal.events()
    decision = next(
        (event for event in reversed(events) if event["event_type"] == "turn_decision_recorded"),
        None,
    )
    if decision is None:
        return None
    turn_id = decision["payload"].get("turn_id")
    for event in reversed(events):
        payload = event["payload"]
        if payload.get("turn_id") != turn_id:
            continue
        if event["event_type"] == "tool_batch_finished":
            return None
        if event["event_type"] == "protocol_correction":
            return dict(payload)
    return None


def _cards(
    journal: DevJournal,
    correction: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    cards = [
        event["payload"] for event in journal.events() if event["event_type"] == "attempt_card"
    ]
    if correction is not None:
        cards.append(
            {
                "attempt": "protocol",
                "result": correction["code"],
                "next_question": correction["message"],
                "workflow_gate": correction["workflow_gate"],
                "remaining_visible_check_ids": correction["remaining_visible_check_ids"],
            }
        )
    def compact(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: compact(item) for key, item in value.items()
                if key not in {"memory_update", "evidence_fingerprint"}
            }
        if isinstance(value, list):
            return [compact(item) for item in value]
        return value

    # Validated notes have their own projection. Keep submitted annotations and
    # detailed inspection fingerprints in the journal, not a second working set.
    return [compact(card) for card in cards[-3:]]


def _recent_checks(
    gateway: DevToolGateway, *, diff_hash: str | None = None, pinned_action_id: str | None = None,
) -> list[dict[str, Any]]:
    # Keep the result's citation identity with its label even after the native
    # output ages out. Preserve the existing diff/check selection and order;
    # repeated actions for one check only update that row's latest identity.
    current_hash = diff_hash if diff_hash is not None else gateway.current_diff_hash
    action_ids: dict[tuple[str, str], str] = {}
    for event in gateway.journal.events():
        if event["event_type"] != "action_finished":
            continue
        result = event["payload"]["result"]
        if result["tool"] != "run_check" or result["status"] != "succeeded":
            continue
        value = result["output"]
        action_ids[(value["diff_hash"], value["check_id"])] = result["action_id"]
    rows: list[dict[str, Any]] = []
    for diff_hash, checks in gateway.checks_by_diff.items():
        currency = (
            "current" if diff_hash == current_hash else "historical"
        ) if diff_hash and current_hash else "unknown"
        for value in checks.values():
            failure = value.get("public_check_failure")
            location = failure.get("public_location") if isinstance(failure, dict) else None
            stdout, stdout_clipped = output_tail(value.get("stdout", ""), 4_000)
            stderr, stderr_clipped = output_tail(value.get("stderr", ""), 4_000)
            rows.append(
                {
                    "action_id": action_ids[(diff_hash, value["check_id"])],
                    "check_id": value["check_id"],
                    "diff_hash": diff_hash,
                    "passed": value["passed"],
                    "evidence_currency": currency,
                    "counts_toward_completion": currency == "current" and value["passed"] is True,
                    "failure_signature": value.get("failure_signature"),
                    "exit_code": value.get("exit_code"),
                    "timed_out": value.get("timed_out"),
                    "failure_site_fingerprint": (
                        failure.get("failure_site_fingerprint")
                        if isinstance(failure, dict)
                        else None
                    ),
                    "public_failure_line": (
                        location.get("line") if isinstance(location, dict) else None
                    ),
                    "stdout": stdout,
                    "stderr": stderr,
                    "truncated": bool(value.get("truncated")) or stdout_clipped or stderr_clipped,
                }
            )
    selected = rows[-3:]
    if pinned_action_id is not None:
        pinned = next((row for row in rows if row["action_id"] == pinned_action_id), None)
        if pinned is not None and pinned not in selected:
            selected = [*selected[-2:], pinned]
    return selected


def _workflow_gate(summary: Any, *, ready_to_submit: bool) -> str:
    if not summary.patch or summary.untracked_files:
        return "needs_mutation"
    if ready_to_submit:
        return "ready_to_submit"
    return "needs_visible_checks"


def _completion_guidance(
    snapshot: DevGatewayStateSnapshot, policy: _ToolPolicy,
) -> dict[str, Any]:
    """Describe an offered next action, without executing it or changing admission."""
    allowed = policy.allowed_tools
    stage = "blocked"
    next_action: dict[str, Any] | None = None
    message = (
        "No completion action is currently offered under the current state and budgets. "
        "stop_task abandons without submission or evaluation."
    )
    needs_mutation = policy.workflow_gate == "needs_mutation" or any(
        row["status"] == "FAIL" for row in snapshot.visible_check_status
    ) or (snapshot.completion_verification or {}).get("status") == "refuted"
    if policy.helper_correction and policy.helper_correction.get("blocked"):
        correction = policy.helper_correction
        stage = policy.workflow_gate
        next_action = ({"tool": "run_probe", "question": correction["question"],
                        "purpose": correction.get("purpose", {"kind": "helper"}),
                        "replay_action_id": None}
                       if "run_probe" in allowed else None)
        message = (
            "The helper source was rejected before execution. Fix its named source error, "
            "keep the exact question, and submit changed python_source with a new action_id, "
            "or stop. Use only helper APIs and an ordinary scratch directory. This one "
            "correction uses existing completion resources; unrelated searches, reads and "
            "project edits cannot consume it. A returned execution is diagnostic evidence, "
            "not original-call verification. Rejection or an unavailable execution does not "
            "renew the allowance; an unresolved or unaffordable correction returns "
            "verification incomplete."
        )
        if correction.get("policy") == helper_recovery.ARGUMENT_POLICY:
            message = (
                "The original call failed argument binding before target entry. Read its actual "
                "signature and supplied arguments in helper_correction.error. Inspect "
                "target.signature() before calling; sys.argv is separate from Python arguments. "
                "Correct python_source with a new action_id, keeping the exact question, purpose "
                "and call_path, or stop. One correction request uses existing acquisition and "
                "completion budgets; unrelated exploration cannot spend it. Rejection, another "
                "pre-target error or insufficient resources leaves verification incomplete. "
                "A corrected invocation alone does not verify the original failure."
            )
    elif (policy.repair_path_diagnosis and policy.repair_path_diagnosis.get("blocked")
          and (policy.repair_prediction or {}).get("status") != "needs_test_comparison"):
        diagnosis = policy.repair_path_diagnosis
        stage = policy.workflow_gate
        next_action = ({"tool": "run_probe", "selection": (
            "focus_and_call_id" if diagnosis.get("call_selection_required") else "focus_only")}
                       if "run_probe" in allowed else None)
        message = (
            "The same original failure persists and the modified branch was not observed. "
            "Supply only focus selecting a public function on the suspected failure path. "
            "The host observes the selected call even outside focus and selects "
            "changed-function watches, parameter fields and executable lines, and binds "
            "the original replay. Omit general plan/memory annotations. "
            "Explore public callers or tests with the offered reads/searches, or run the "
            "trace when ready. Exploration uses the remaining shared budget and preserves "
            "completion plus one unused rejected-request correction. Diagnostic execution "
            "and request correction remain separately bounded. Capacity is a reservation forecast; "
            "each action rechecks cost and time. "
            "Function entry, branch execution and behavior are "
            "different observations. A complete diagnosis must inform the next hypothesis before "
            "another repair; incomplete observation returns verification incomplete."
        )
        if diagnosis.get("call_selection_required"):
            message = message.replace("Supply only focus", "Supply focus and call_id")
            message += (
                " Select call_id from the captured call_choices. Its relation to the failure "
                "is model-selected and unverified; selecting another call does not renew "
                "the shared budget, execution or correction allowance.")
        if diagnosis.get("preparation_available"):
            message += (
                " A current-source repair anchor is still required and remains reserved; "
                "reading a caller or test does not establish it."
                if diagnosis.get("preparation_required_for_completion") else
                " Reads may continue while each next action fits the remaining budget."
            )
        else:
            message += (
                " No preparation read is offered this turn; the remaining resources "
                "are reserved for diagnosis, repair and verification."
            )
    elif (policy.repair_prediction or {}).get("status") == "needs_test_comparison":
        stage = policy.workflow_gate
        next_action = ({"tool": "run_tests", **policy.repair_prediction["pending_test"]}
                       if "run_tests" in allowed else None)
        message = (
            "Run the frozen selected tests before and after the named implementation edit. "
            "This comparison uses one model call and two isolated executions; omit plan and "
            "memory annotations. The test addition did not repair the original failure. "
            "A source repair, original replay and required checks still need their own evidence. "
            "If this remaining path cannot fit, stop without claiming verification."
        )
    elif policy.workflow_gate in {"needs_observation_correction", "verification_incomplete"}:
        stage = policy.workflow_gate
        next_action = {"tool": "run_probe"} if "run_probe" in allowed else None
        message = (
            "Captured target diagnostics contradict the authored observation. Correct only the "
            "extractor in a fresh original probe and supply purpose.corrects_action_id from "
            "observation_correction. Preserve rules, expected/failure values, caller, fixtures "
            "and environment. Re-execute on the unchanged base; source repair waits for a "
            "consistent same-condition original failure. One correction is allowed in this run; "
            "a rejected or unsuccessful correction does not renew it. Unresolved or unaffordable "
            "correction returns verification incomplete."
        )
    elif policy.workflow_gate == "needs_original_reproduction":
        stage = "needs_original_reproduction"
        next_action = {"tool": "run_probe"} if "run_probe" in allowed else None
        message = (
            "Investigate the original public caller before editing. Use an original_requirement "
            "probe on the unchanged base, preserving its actual arguments, cwd, fixtures and "
            "environment; a helper or normal-only PASS does not reproduce the reported failure. "
            "Request rejection is not an execution: correct the primary probe request error. "
            "This stage permits two actual original dispatches, at most two rejected requests "
            "and six preparation actions, within the shared completion budget. When reads "
            "close, request the original probe or stop; reading does not use execution slots. "
            "Release without a failure keeps verification unmet."
        )
    elif snapshot.ready_to_submit and "finish_task" in allowed:
        stage = "ready_to_submit"
        message = (
            "Current required checks pass; this establishes eligibility, not correctness. "
            "Before deciding whether the task is complete, revisit unfinished verification "
            "plans and unsupported public requirements. Continue if an available action "
            "could resolve a material gap. Call finish_task to return the candidate with an "
            "assessment of evidence and remaining gaps. Missing original evidence returns "
            "unverified_delivery, not verified completion. Edits require fresh checks. "
        )
        if "run_probe" in allowed:
            message += (
                "Use run_probe when it could change this judgment."
            )
        if (snapshot.completion_verification or {}).get("pending_count", 0):
            message += (
                " Submitting automatically replays stale original-requirement cases. "
                "A current comparable mismatch returns to repair; unknown remains unverified."
            )
    elif needs_mutation:
        if "replace_text" in allowed:
            stage = "needs_mutation"
            next_action = {"tool": "replace_text"}
            message = (
                "The current candidate needs a repair. Use replace_text for a supported edit; "
                "available anchor evidence does not establish a correct solution. "
                "Submission waits for a scoped patch and its required visible checks."
            )
            if "observe_original" in allowed:
                next_action = {"tool": "observe_original"}
                message += (
                    " If the first repair premise is unresolved, select candidate functions "
                    "and event predictions with observe_original. The host replays the frozen "
                    "original; no helper program or invocation reconstruction is needed. "
                    "A supported direct edit remains available."
                )
        else:
            inspection = next(
                (tool for tool in ("read_file", "search_files") if tool in allowed), None,
            )
            if inspection:
                stage = "needs_source_evidence"
                next_action = {"tool": inspection}
                message = (
                    "replace_text is temporarily unavailable: current editable source evidence "
                    f"is missing. Use {inspection} on an allowed source file. After evidence is "
                    "delivered, edit availability is reevaluated with remaining budgets. "
                    "Submission waits for a scoped patch and its required visible checks."
                )
    elif "run_check" in allowed and policy.check_ids:
        stage = "needs_visible_checks"
        check_id = policy.check_ids[0]
        next_action = {"tool": "run_check", "check_id": check_id}
        message = (
            f"Run one remaining visible check for the current diff: {check_id}. "
            "Use run_check; PASS on a different diff does not count toward completion. "
            "Submission becomes available when all required checks pass on this scoped patch."
        )
    return {
        "diff_hash": snapshot.diff.patch_hash,
        "stage": stage,
        "submission_ready": (snapshot.ready_to_submit and "finish_task" in allowed
                             and (snapshot.completion_verification or {}).get("status")
                             != "refuted" and not (snapshot.completion_verification or {}).get(
                                 "target_failure_count")),
        "next_action": next_action,
        "message": message,
    }


def _minimum_completion_calls(
    gateway: DevToolGateway,
    workflow_gate: str,
    *,
    visible_check_status: tuple[dict[str, Any], ...],
    remaining_visible_check_ids: tuple[str, ...],
    has_current_mutation_evidence: bool,
    targeted_check_repair_required: bool = False,
    targeted_mutation_repair_inspection: bool = False,
    failed_mutation_pending: bool = False,
) -> int:
    # Legacy arguments remain callable, but a rejected optional mutation does not
    # invalidate the rollback baseline or require another accepted mutation.
    del (
        targeted_check_repair_required,
        targeted_mutation_repair_inspection,
        failed_mutation_pending,
    )
    requires_mutation = workflow_gate == "needs_mutation" or any(
        row["status"] == "FAIL" for row in visible_check_status
    )
    return completion_budget(
        CompletionState(
            check_count=len(gateway.public_task.visible_checks),
            remaining_check_count=len(remaining_visible_check_ids),
            unused_check_count=0,
            unrun_recoverable_check=False,
            requires_mutation=requires_mutation,
            anchor_available=has_current_mutation_evidence,
            remaining_mutations=0,
            mutation_retry_available=False,
        )
    ).minimum


def _tool_policy(
    gateway: DevToolGateway,
    counters: _RunCounters,
    limits: Any,
    *,
    snapshot: DevGatewayStateSnapshot | None = None,
    repair_inspection_policy: str = "protected-v1",
    repair_recheck: bool = False,
    cost_ledger: DevCostLedger | None = None,
    completion_cost_policy: str = DEFAULT_COMPLETION_COST_POLICY,
    desired_output_ceiling: int = DEFAULT_OUTPUT_CEILING,
    max_correction_output_tokens: int | None = None,
    remaining_seconds: float | None = None,
    requested_revision_diff_hash: str | None = None,
    _preview_inspection: bool = True,
    _cost_call_limit: int | None = None,
    _diagnostic_spent: bool = False,
) -> _ToolPolicy:
    if snapshot is None and isinstance(gateway, DevToolGateway):
        snapshot = gateway.state_snapshot()
    if snapshot is None:
        summary = gateway.current_diff
        visible_status = tuple(gateway.visible_check_status())
        remaining_check_ids = tuple(gateway.remaining_visible_check_ids())
        unrun_checks = tuple(gateway.unrun_visible_check_ids())
        ready_to_submit = gateway.ready_to_submit()
        has_current_mutation_evidence = gateway.has_current_mutation_evidence()
    else:
        summary = snapshot.diff
        visible_status = snapshot.visible_check_status
        remaining_check_ids = snapshot.remaining_visible_check_ids
        unrun_checks = snapshot.unrun_visible_check_ids
        ready_to_submit = snapshot.ready_to_submit
        has_current_mutation_evidence = bool(snapshot.mutation_evidence_paths)
    workflow_gate = _workflow_gate(summary, ready_to_submit=ready_to_submit)
    verification = (snapshot.completion_verification or {}) if snapshot is not None else {}
    observation_fix = verification.get("observation_correction", {})
    observation_blocked = bool(observation_fix.get("blocked"))
    observation_available = bool(
        observation_blocked and observation_fix.get("status") == "pending"
        and not observation_fix.get("pending_started")
    )
    path_diagnosis = verification.get("repair_path", {})
    path_blocked = bool(path_diagnosis.get("blocked") and not observation_blocked)
    path_available = bool(path_blocked and path_diagnosis.get("status") == "needs_path_diagnosis")
    path_preparation = bool(path_available and path_diagnosis.get("preparation_available"))
    repair_prediction = verification.get("repair_prediction", {})
    test_comparison_pending = repair_prediction.get("status") == "needs_test_comparison"
    diagnosed_test_available = bool(
        path_diagnosis.get("status") == "diagnosed" and repair_prediction.get("test_available")
        and not test_comparison_pending
    )
    diagnosed_test_bound = bool(path_diagnosis.get("status") == "diagnosed" and repair_prediction)
    first_observation = verification.get("first_observation", {})
    first_available = bool(first_observation.get("available")
                           and getattr(gateway, "probe_sandbox", None) is not None)
    helper_fix = verification.get("helper_correction", {})
    helper_blocked = bool(
        helper_fix.get("blocked") and not observation_blocked and not path_blocked
    )
    helper_available = bool(helper_blocked and helper_recovery.correction_available(
        helper_fix, verification.get("original_obligation", {})))
    argument_correction = bool(
        helper_available and helper_fix.get("policy") == helper_recovery.ARGUMENT_POLICY
    )
    first_available &= not (observation_blocked or path_blocked or helper_blocked)
    original_case_failed = (verification.get("status") == "refuted"
                            or bool(verification.get("target_failure_count")))
    diagnostic = verification.get("original_failure_diagnostic")
    diagnostic_available = bool(
        original_case_failed and diagnostic and diagnostic["status"] == "available"
        and diagnostic["candidate_diff_hash"] == summary.patch_hash
    )
    if original_case_failed:
        workflow_gate = "needs_mutation"
        ready_to_submit = False
    current_check_failed = any(row["status"] == "FAIL" for row in visible_status)
    declared_check_ids = tuple(
        row["check_id"]
        for row in visible_status
        if isinstance(row.get("check_id"), str)
    )
    failed_check_ids = {
        row["check_id"]
        for row in visible_status
        if row["status"] == "FAIL" and isinstance(row.get("check_id"), str)
    }
    unused_check_ids = tuple(
        check_id
        for check_id in declared_check_ids
        if check_id not in counters.check_recovery_used_ids
        and check_id not in failed_check_ids
    )
    if counters.check_recovery_used and not counters.check_recovery_used_ids:
        unused_check_ids = ()
    remaining_model_calls = max(0, limits.max_model_calls - counters.model_calls)
    cost_unit = 0
    funded_calls = None
    correction_cost = correction_reserve = correction_current_premium = 0
    finalization_premium = finalization_current_premium = 0
    finalization_floor = min(desired_output_ceiling, FINALIZATION_OUTPUT_FLOOR)
    correction_available = correction_pending = False
    correction_model_reserve = 0
    correction_ceiling = correction_output_ceiling(
        desired_output_ceiling, max_correction_output_tokens,
    )
    if (completion_cost_policy in {
            COMPLETION_RESERVE_POLICY, COMPLETION_MINIMUM_POLICY, COMPLETION_RECOVERY_POLICY,
        }
            and cost_ledger is not None):
        cost_unit = cost_ledger.future_call_reservation_nanos()
        if completion_cost_policy == COMPLETION_RECOVERY_POLICY:
            finalization_premium = cost_ledger.future_call_reservation_nanos(
                output_ceiling=finalization_floor,
            ) - cost_unit
            finalization_current_premium = finalization_premium if ready_to_submit else 0
            correction_cost = cost_ledger.future_call_reservation_nanos(
                output_ceiling=correction_ceiling,
            )
            correction_available = (
                limits.max_protocol_recoveries > 0 and counters.protocol_corrections_total == 0
            )
            correction_pending = (
                counters.protocol_corrections_total == 1 and counters.protocol_recoveries > 0
            )
            correction_reserve = correction_cost if correction_available else 0
            correction_current_premium = correction_cost - cost_unit if correction_pending else 0
            correction_model_reserve = int(correction_available)
            remaining_model_calls = max(0, remaining_model_calls - correction_model_reserve)
        funded_calls = (
            max(0, cost_ledger.remaining_nanos - correction_reserve - finalization_premium
                - (correction_current_premium if correction_pending
                   else finalization_current_premium))
            // cost_unit
            if _cost_call_limit is None else _cost_call_limit
        )
        # No future input must be funded once only the final decision remains.
        # Let exact counting admit a cheaper ready request below the input bound.
        if completion_cost_policy == COMPLETION_RESERVE_POLICY:
            remaining_model_calls = min(
                remaining_model_calls, max(int(ready_to_submit), funded_calls),
            )
    remaining_tool_actions = max(0, limits.max_tool_actions - counters.tool_actions)
    remaining_mutations = max(
        0, limits.max_accepted_mutations - gateway.accepted_mutations
    )
    mutation_capacity = remaining_mutations > 0 and not summary.untracked_files
    requires_mutation = (
        workflow_gate == "needs_mutation" or current_check_failed or original_case_failed
        or (test_comparison_pending and verification.get("status") != "cases_verified")
    )
    repair_read_credit = (
        current_check_failed
        and counters.failed_check_pending
        and not counters.failed_check_repair_read_used
    )
    current_recheck_eligible = bool(
        repair_recheck and current_check_failed and getattr(gateway, "journal", None) is not None
        and latest_repair_check(
            gateway.journal.events(), baseline=summary.patch_hash,
            registered_checks={check.id for check in gateway.public_task.visible_checks},
        ) is not None
    )
    completion_state = CompletionState(
        check_count=len(gateway.public_task.visible_checks),
        remaining_check_count=len(remaining_check_ids),
        unused_check_count=len(unused_check_ids),
        unrun_recoverable_check=bool(set(unrun_checks) & set(unused_check_ids)),
        requires_mutation=requires_mutation,
        anchor_available=has_current_mutation_evidence,
        remaining_mutations=remaining_mutations,
        mutation_retry_available=not counters.mutation_recovery_used,
        repair_read_credit=repair_read_credit,
        automatic_recheck=repair_recheck,
        current_recheck_eligible=current_recheck_eligible,
        reproduction_case_count=(verification.get("replayable_case_count", 0)
                                 + int(observation_available) + int(argument_correction)),
        pending_reproduction_count=verification.get("pending_count", 0),
        early_reproduction_count=len(verification.get("baseline_failure_case_ids", [])),
        early_replay_reusable=bool(
            verification.get("early_replay_reusable")
            and getattr(gateway, "probe_sandbox", None) is not None
        ),
        observation_correction_pending=observation_available,
        path_diagnosis_pending=path_available,
        path_preparation_available=path_preparation,
        path_request_correction_available=(path_available
                                           and not path_diagnosis.get("rejected_requests")),
        helper_correction_pending=helper_available,
        test_comparison_pending=test_comparison_pending,
        test_comparison_replay_count=sum(
            case["case_id"] in verification.get("baseline_failure_case_ids", [])
            for case in verification.get("pending_cases", [])
        ) if test_comparison_pending else 0,
    )
    budget = completion_budget(completion_state)
    completion_possible = (
        remaining_model_calls >= budget.minimum
        and remaining_tool_actions >= budget.minimum_tool_actions
        and (not requires_mutation or mutation_capacity)
    )
    protected_completion_possible = (
        completion_possible
        and remaining_model_calls >= budget.protected
        and remaining_tool_actions >= budget.protected_tool_actions
    )

    # An inspection can spend its reserved repair credit, or acquire a missing
    # anchor, without having to reserve that same read again in its successor.
    required_inspection = requires_mutation and not has_current_mutation_evidence
    inspection_uses_credit = repair_read_credit and not required_inspection
    inspection_state = replace(
        completion_state,
        anchor_available=has_current_mutation_evidence or required_inspection,
        repair_read_credit=False if repair_read_credit else completion_state.repair_read_credit,
    )
    inspection_budget = completion_budget(inspection_state)
    acquisition_pending = verification.get("original_obligation", {}).get("stage") == "pending"
    acquisition_inspection_budget = completion_budget(replace(
        inspection_state, reproduction_case_count=inspection_state.reproduction_case_count + 1,
    )) if acquisition_pending and not argument_correction else None
    inspection_floor = (
        inspection_budget.minimum
        if required_inspection and not protected_completion_possible
        else inspection_budget.protected
    )
    inspection_tool_floor = (
        inspection_budget.minimum_tool_actions
        if required_inspection and not protected_completion_possible
        else inspection_budget.protected_tool_actions
    )
    # On an observed current failure, the opt-in policy can spend speculative
    # future-check recovery on inspection. Keep the full forecast for all other
    # actions; a later failed check is no longer guaranteed a recovery path.
    # The existing minimum-only required-anchor exception remains unchanged.
    released_check_recovery = 0
    if (
        repair_inspection_policy == "current-failure-v1"
        and current_check_failed
        and not (required_inspection and not protected_completion_possible)
    ):
        released_check_recovery = inspection_budget.check_recovery_reserve
        inspection_floor -= released_check_recovery
        inspection_tool_floor -= inspection_budget.check_recovery_tool_actions
    # A comparable original failure on this candidate earns one diagnostic turn.
    # Spend speculative recovery only, retaining the real minimum repair/check/
    # replay/finish path. The journal-derived credit is independent of restarts.
    diagnostic_relaxes_inspection = (diagnostic_available and not path_blocked
                                    and not _diagnostic_spent
                                    and diagnostic.get("preparation_available", True)) and (
        remaining_model_calls - 1 < inspection_floor
        or remaining_tool_actions - 1 < inspection_tool_floor
    )
    if diagnostic_relaxes_inspection:
        inspection_floor = inspection_budget.minimum
        inspection_tool_floor = inspection_budget.minimum_tool_actions
    shared_failure_exploration = bool(
        completion_cost_policy == COMPLETION_RECOVERY_POLICY and cost_ledger is not None
        and original_case_failed and not (first_available or observation_blocked or helper_blocked
                                     or test_comparison_pending or acquisition_pending)
    )
    if shared_failure_exploration:
        # Admit this evidence-gathering choice against an actual completion route
        # below. The old protected envelope also covered multiple hypothetical
        # failures; it must not veto a selected one-cycle/required-only route first.
        request_fix = int(completion_state.path_request_correction_available)
        inspection_floor = budget.minimum + request_fix
        inspection_tool_floor = budget.minimum_tool_actions + request_fix
    # Preserve one optional original observation before exploration closes. This
    # shares the existing protected slack, rather than adding a second reserve.
    if first_available:
        inspection_floor = max(inspection_floor, inspection_budget.minimum + 1)
        inspection_tool_floor = max(
            inspection_tool_floor, inspection_budget.minimum_tool_actions + 1)
    if acquisition_inspection_budget is not None:
        # A preparatory read must leave one original dispatch and its acquired-case
        # completion route. Reading cannot consume the last funded probe opportunity.
        inspection_floor = max(inspection_floor, 1 + acquisition_inspection_budget.protected)
        inspection_tool_floor = max(
            inspection_tool_floor, 1 + acquisition_inspection_budget.protected_tool_actions)
    inspection_tool_slack = remaining_tool_actions - inspection_tool_floor
    inspection_model_slack = remaining_model_calls - inspection_floor
    inspection_allowed = (
        completion_possible
        and inspection_model_slack >= 1
        and inspection_tool_slack >= 1
    )
    max_parallel_reads = (
        min(limits.max_parallel_reads, inspection_tool_slack)
        if inspection_allowed
        else 0
    )
    # If only the best path is affordable, the one required anchor read is still
    # completion work. Extra parallel requests cannot spend unreserved headroom.
    if (required_inspection and not protected_completion_possible) or diagnostic_relaxes_inspection:
        max_parallel_reads = min(max_parallel_reads, 1)

    # A discretionary edit can invalidate every current PASS. Its successful
    # minimum successor must fit; a recovery guarantee is reported separately,
    # not required to make a viable edit executable. Optional inspection/probes
    # still preserve the complete protected baseline path above/below.
    mutation_budget = mutation_attempt_budget(completion_state)
    optional_mutation_completion_calls = mutation_budget.minimum
    optional_mutation_protected_calls = mutation_budget.protected
    mutation_allowed = (
        completion_possible
        and mutation_capacity
        and has_current_mutation_evidence
        and (
            requires_mutation
            or (
                remaining_model_calls >= optional_mutation_completion_calls
                and remaining_tool_actions >= mutation_budget.minimum_tool_actions
            )
        )
    )
    mutation_protected_completion_possible = (
        mutation_allowed
        and remaining_model_calls >= optional_mutation_protected_calls
        and remaining_tool_actions >= mutation_budget.protected_tool_actions
    )
    test_edit_budget = test_addition_budget(completion_state)
    repair_test_edit_enabled = bool(
        diagnosed_test_available and mutation_allowed and remaining_mutations >= 2
        and getattr(gateway.public_task, "test_suites", [])
        and getattr(getattr(gateway.public_task, "constraints", None), "additive_test_roots", [])
        and remaining_model_calls >= test_edit_budget.minimum
        and remaining_tool_actions >= test_edit_budget.minimum_tool_actions
        and (funded_calls is None or funded_calls >= test_edit_budget.minimum)
    )
    selected_test_floor = budget.minimum if diagnosed_test_available else budget.protected
    selected_test_tool_floor = (
        budget.minimum_tool_actions if diagnosed_test_available else budget.protected_tool_actions
    )
    allowed = {"stop_task"}
    obligation = verification.get("original_obligation", {})
    probe_budget = (completion_budget(replace(
        completion_state, reproduction_case_count=completion_state.reproduction_case_count + 1,
    )) if (obligation.get("stage") == "pending" and not argument_correction)
        or diagnostic_available else budget)
    probe_floor = probe_budget.minimum if diagnostic_available else probe_budget.protected
    probe_tool_floor = (probe_budget.minimum_tool_actions if diagnostic_available
                        else probe_budget.protected_tool_actions)
    available_check_ids = unrun_checks
    check_successor_reserve = max(0, (
        budget.protected if protected_completion_possible else budget.minimum
    ) - 1)
    if completion_possible:
        if ready_to_submit and not original_case_failed:
            allowed.add("finish_task")
        if inspection_allowed:
            allowed.update({"read_file", "search_files"})
            # Historical evidence cannot satisfy the reserved current-anchor read
            # or consume a failed-check repair-read credit. Fund it as optional work.
            if (getattr(gateway, "history_search_policy", "none") == history_search.POLICY
                    and remaining_model_calls - 1 >= budget.protected
                    and remaining_tool_actions - 1 >= budget.protected_tool_actions):
                allowed.add(history_search.TOOL)
        if mutation_allowed:
            allowed.add("replace_text")
        if (first_available and remaining_model_calls - 1 >= budget.minimum
                and remaining_tool_actions - 1 >= budget.minimum_tool_actions):
            allowed.add("observe_original")
        # On a baseline that already requires repair, a diagnostic check is
        # optional work and must leave the whole protected repair path intact.
        if requires_mutation:
            check_successor_budgets = {
                check_id: completion_budget(replace(
                        completion_state,
                        unused_check_count=(completion_state.unused_check_count
                                            - int(check_id in unused_check_ids)),
                        repair_read_credit=True,
                        current_recheck_eligible=repair_recheck,
                    ))
                for check_id in unrun_checks
            }
            available_check_ids = tuple(
                check_id
                for check_id in unrun_checks
                if remaining_model_calls - 1 >= max(
                    budget.protected, check_successor_budgets[check_id].protected,
                ) and remaining_tool_actions - 1 >= max(
                    budget.protected_tool_actions,
                    check_successor_budgets[check_id].protected_tool_actions,
                )
            )
            check_successor_reserve = max(
                (max(budget.protected, check_successor_budgets[c].protected)
                 for c in available_check_ids), default=0,
            )
        if available_check_ids:
            allowed.add("run_check")
        if (
            getattr(gateway, "probe_sandbox", None) is not None
            and remaining_model_calls - 1 >= probe_floor
            and remaining_tool_actions - 1 >= probe_tool_floor
        ):
            allowed.add("run_probe")
        if (
            getattr(gateway.public_task, "test_suites", [])
            and (not diagnosed_test_bound or diagnosed_test_available)
            and remaining_model_calls - 1 >= selected_test_floor
            and remaining_tool_actions - (2 if diagnosed_test_bound else 1)
            >= selected_test_tool_floor
        ):
            allowed.add("run_tests")

    if first_available:
        # A rejected first edit can consume mutation retry protection until the
        # protected path equals the minimum. Every optional diagnostic must still
        # leave the observation slot; reads already account for acquired anchors.
        for tool in (_FIRST_OBSERVATION_EXPLORATION - {"read_file", "search_files"}) & allowed:
            if (remaining_model_calls - 1 < budget.minimum + 1
                    or remaining_tool_actions - 1 < budget.minimum_tool_actions + 1):
                allowed.remove(tool)
        if "run_check" not in allowed:
            available_check_ids = ()

    exploration_capacity = (
        max(0, min(inspection_model_slack, inspection_tool_slack))
        if inspection_allowed
        else 0
    )
    if diagnostic_relaxes_inspection:
        exploration_capacity = min(exploration_capacity, 1)
    if obligation.get("stage") == "pending":
        workflow_gate = "needs_original_reproduction"
        allowed.intersection_update({"stop_task", "read_file", "search_files", "run_probe",
                                     history_search.TOOL})
        mutation_allowed = mutation_protected_completion_possible = False
        preparation_remaining = obligation.get("preparation_actions_remaining", max(
            0, obligation["max_investigation_actions"] - obligation["investigation_actions"]))
        max_parallel_reads = min(max_parallel_reads, preparation_remaining)
        exploration_capacity = min(exploration_capacity, preparation_remaining)
        if not preparation_remaining:
            allowed.difference_update({"read_file", "search_files", history_search.TOOL})
            inspection_allowed = False
        elif (remaining_model_calls - 1 < 1 + probe_floor
              or remaining_tool_actions - 1 < 1 + probe_tool_floor):
            allowed.discard(history_search.TOOL)
        available_check_ids = ()
    if observation_blocked:
        workflow_gate = "needs_observation_correction"
        allowed = {"stop_task"}
        completion_possible &= (
            observation_available and getattr(gateway, "probe_sandbox", None) is not None
        )
        if completion_possible:
            allowed.add("run_probe")
        mutation_allowed = mutation_protected_completion_possible = inspection_allowed = False
        max_parallel_reads = exploration_capacity = 0
        available_check_ids = ()
    elif path_blocked:
        workflow_gate = "needs_path_diagnosis"
        allowed = {"stop_task"}
        completion_possible &= (
            path_available and getattr(gateway, "probe_sandbox", None) is not None
        )
        mutation_allowed = mutation_protected_completion_possible = inspection_allowed = False
        max_parallel_reads = exploration_capacity = 0
        available_check_ids = ()
        if completion_possible:
            # The diagnostic is already in the minimum. Do not reserve it twice.
            allowed.add("run_probe")
            probe_floor = budget.minimum - 1
            probe_tool_floor = budget.minimum_tool_actions - 1
            # Caller/test exploration need not acquire a repair anchor. Preserve
            # that missing read and the existing request-correction opportunity.
            correction = int(completion_state.path_request_correction_available)
            inspection_floor = budget.minimum + correction
            inspection_tool_floor = budget.minimum_tool_actions + correction
            inspection_model_slack = max(0, remaining_model_calls - inspection_floor)
            inspection_tool_slack = max(0, remaining_tool_actions - inspection_tool_floor)
            if path_preparation and inspection_model_slack and inspection_tool_slack:
                allowed.update({"read_file", "search_files"})
                inspection_allowed = True
                max_parallel_reads = 1
                exploration_capacity = min(inspection_model_slack, inspection_tool_slack)
    if helper_blocked:
        workflow_gate = ("needs_original_argument_correction"
                         if helper_fix.get("policy") == helper_recovery.ARGUMENT_POLICY
                         else "needs_helper_correction")
        allowed = {"stop_task"}
        completion_possible &= (
            helper_available and getattr(gateway, "probe_sandbox", None) is not None
        )
        mutation_allowed = mutation_protected_completion_possible = inspection_allowed = False
        max_parallel_reads = exploration_capacity = 0
        available_check_ids = ()
        if completion_possible:
            allowed.add("run_probe")
            probe_floor = budget.minimum - 1
            probe_tool_floor = budget.minimum_tool_actions - 1
    if test_comparison_pending and not (observation_blocked or helper_blocked):
        workflow_gate = "needs_test_comparison"
        allowed = {"stop_task"}
        completion_possible &= bool(getattr(gateway.public_task, "test_suites", []))
        mutation_allowed = mutation_protected_completion_possible = inspection_allowed = False
        repair_test_edit_enabled = False
        max_parallel_reads = exploration_capacity = 0
        available_check_ids = ()
        selected_test_floor = budget.minimum - 1
        selected_test_tool_floor = budget.minimum_tool_actions - 2
        if completion_possible:
            allowed.add("run_tests")
    minimum_cost_successors = None
    recovery_routes = {}
    resource_rejections = {}
    released_failure_recovery = {}
    # This host-bound request reserves an opportunity, not verification credit.
    # Its measured diff must still be current; finish and original gates stay ordinary.
    requested_revision = bool(
        completion_cost_policy == COMPLETION_RECOVERY_POLICY and cost_ledger is not None
        and workflow_gate == "ready_to_submit" and mutation_capacity
        and requested_revision_diff_hash is not None
        and requested_revision_diff_hash == summary.patch_hash
    )
    revision_exploration = {"read_file", "search_files", history_search.TOOL,
                            "run_probe", "run_tests"}
    if (completion_cost_policy in {COMPLETION_MINIMUM_POLICY, COMPLETION_RECOVERY_POLICY}
            and funded_calls is not None):
        # Keep physical model/action recovery slots independent of money. Offer
        # only actions whose successful minimum successor can be funded, then
        # reserve the largest successor before the unknown action is generated.
        minimum_cost_successors = {
            tool: minimum_successor_calls(completion_state, tool) for tool in allowed
        }
        if path_available or shared_failure_exploration:
            for tool in {"read_file", "search_files"} & allowed:
                minimum_cost_successors[tool] = inspection_floor
        if repair_test_edit_enabled and "replace_text" in allowed:
            minimum_cost_successors["replace_text"] = max(
                minimum_cost_successors["replace_text"], test_edit_budget.minimum - 1,
            )
        if first_available:
            for tool in _FIRST_OBSERVATION_EXPLORATION & allowed:
                minimum_cost_successors[tool] += 1
        if acquisition_inspection_budget is not None:
            for tool in {"read_file", "search_files"} & allowed:
                minimum_cost_successors[tool] = max(
                    minimum_cost_successors[tool], 1 + acquisition_inspection_budget.minimum)
            if history_search.TOOL in allowed:
                minimum_cost_successors[history_search.TOOL] = 1 + probe_budget.minimum
            if "run_probe" in allowed:
                minimum_cost_successors["run_probe"] = probe_budget.minimum
        if completion_cost_policy == COMPLETION_RECOVERY_POLICY:
            checks = gateway.public_task.visible_checks
            durations = {check.id: float(getattr(check, "timeout_seconds", 0))
                         + CHECK_OVERHEAD_SECONDS
                         for check in checks}
            suites = getattr(gateway.public_task, "test_suites", ())
            for tool in allowed:
                reserve_revision = requested_revision and tool in revision_exploration
                calls = minimum_cost_successors[tool]
                extra = 2 + completion_state.check_count - int(repair_recheck
                    and completion_state.check_count > 0
                    and not completion_state.reproduction_case_count and not acquisition_pending)
                spare_edits = remaining_mutations - int(requires_mutation
                    or tool == "replace_text") - int(repair_test_edit_enabled)
                ordinary = not first_available and ordinary_route_supported(
                    completion_state, tool, acquisition_pending=acquisition_pending,
                    test_edit=repair_test_edit_enabled and tool == "replace_text",
                    test_comparison=test_comparison_pending)
                legacy_tool_minimum = (mutation_budget.minimum_tool_actions
                                       if tool == "replace_text"
                                       else budget.minimum_tool_actions)
                recover = bool(not reserve_revision and tool not in {"finish_task", "stop_task"}
                    and spare_edits > 0
                    and (completion_state.unused_check_count
                         or completion_state.reproduction_case_count)
                    and (ordinary or (
                        remaining_model_calls >= 1 + calls + extra
                        and remaining_tool_actions >= legacy_tool_minimum + 3
                        + completion_state.check_count + completion_state.reproduction_case_count)))
                options = dict(calls=calls, max_output_tokens=desired_output_ceiling,
                    check_seconds=tuple(durations.values()),
                    remaining_check_seconds=tuple(durations[c] for c in remaining_check_ids),
                    probe_seconds=PROBE_TIMEOUT_SECONDS + CHECK_OVERHEAD_SECONDS,
                    acquisition_pending=acquisition_pending and not argument_correction,
                    test_comparison=(test_comparison_pending or remaining_tool_actions - 2
                                     >= selected_test_tool_floor),
                    optional_check_seconds=max((float(getattr(s, "timeout_seconds", 0)) + 5
                                                for s in suites), default=0),
                    test_edit=repair_test_edit_enabled and tool == "replace_text",
                    preserve_pending_diagnosis=(
                        path_available and tool in {"read_file", "search_files"}),
                    ordinary_routes=ordinary,
                    preserve_read_anchor=shared_failure_exploration)
                route = successor_resources(completion_state, tool,
                                            protect_failure=recover, **options)
                if reserve_revision:
                    revision = requested_revision_resources(
                        completion_state, tool, max_output_tokens=desired_output_ceiling,
                        check_seconds=tuple(durations.values()),
                        probe_seconds=PROBE_TIMEOUT_SECONDS + CHECK_OVERHEAD_SECONDS,
                        optional_check_seconds=options["optional_check_seconds"],
                        test_comparison=options["test_comparison"])
                    floors = {
                        "read_file": (inspection_floor, inspection_tool_floor),
                        "search_files": (inspection_floor, inspection_tool_floor),
                        history_search.TOOL: (budget.protected, budget.protected_tool_actions),
                        "run_probe": (probe_floor, probe_tool_floor),
                        "run_tests": (selected_test_floor, selected_test_tool_floor),
                    }
                    model_floor, tool_floor = floors[tool]
                    current_actions = 2 if tool == "run_tests" and options["test_comparison"] else 1
                    route = merge_resources(route, revision, model_floor=1+model_floor,
                                            tool_floor=current_actions+tool_floor)

                def fits(candidate):
                    outputs = candidate.output_options
                    money = max(sum(cost_ledger.future_call_reservation_nanos(output_ceiling=n)
                                    for n in ceilings) for ceilings in outputs) + correction_reserve
                    output = (correction_ceiling if correction_pending else desired_output_ceiling
                              if requires_mutation and "replace_text" in allowed
                              else finalization_floor)
                    current = cost_ledger.future_call_reservation_nanos(output_ceiling=output)
                    physical = (not candidate.routes or (
                        candidate.model_calls <= remaining_model_calls
                        and candidate.tool_actions <= remaining_tool_actions))
                    seconds = candidate.seconds + (FOLLOWUP_SECONDS * correction_model_reserve
                                                   if candidate.routes else 0)
                    return (physical and money + current <= cost_ledger.remaining_nanos
                            and (remaining_seconds is None
                                 or remaining_seconds - seconds >= FOLLOWUP_SECONDS))

                # A useful immediate repair/check may spend speculative recovery.
                # Known original-failure exploration may also choose the required
                # route explicitly; it does not retain a later failure's revision.
                if recover and not fits(route) and (tool in {"replace_text", "run_check"}
                        or required_inspection and not path_available
                        and tool in {"read_file", "search_files"}
                        or shared_failure_exploration and tool in {"read_file", "search_files"}
                        or path_available and tool == "run_probe"):
                    route = successor_resources(completion_state, tool,
                                                protect_failure=False, **options)
                    released_failure_recovery[tool] = "speculative_future_failure_does_not_fit"
                if tool in {"finish_task", "stop_task"} or fits(route):
                    recovery_routes[tool] = route
                else:
                    resource_rejections[tool] = (
                        "model_calls" if route.routes and route.model_calls > remaining_model_calls
                        else "tool_actions" if route.routes
                        and route.tool_actions > remaining_tool_actions
                        else "time" if remaining_seconds is not None
                        and remaining_seconds - route.seconds
                            - (FOLLOWUP_SECONDS * correction_model_reserve if route.routes else 0)
                            < FOLLOWUP_SECONDS else "cost")
        allowed = {
            tool for tool in allowed
            if tool in {"finish_task", "stop_task"}
            or (tool in recovery_routes if completion_cost_policy == COMPLETION_RECOVERY_POLICY
                else funded_calls >= 1 + minimum_cost_successors[tool])
        }
        completion_possible = completion_possible and (
            funded_calls >= budget.minimum or "finish_task" in allowed
        )
        if completion_cost_policy == COMPLETION_RECOVERY_POLICY:
            completion_possible &= bool(allowed - {"stop_task"})
        protected_completion_possible &= completion_possible
        if not completion_possible:
            allowed = {"stop_task"}
        inspection_allowed = "read_file" in allowed
        mutation_allowed = "replace_text" in allowed
        repair_test_edit_enabled &= mutation_allowed
        mutation_protected_completion_possible &= mutation_allowed
        if "run_check" not in allowed:
            available_check_ids = ()
        if not inspection_allowed:
            max_parallel_reads = exploration_capacity = 0
        else:
            route = recovery_routes.get("read_file")
            if route is not None and route.routes:
                # Current read is one response/action; all other steps, including
                # host replays and retained request correction, remain ahead.
                inspection_floor = route.model_calls - 1
                inspection_tool_floor = route.tool_actions - 1
                inspection_model_slack = max(0, remaining_model_calls - inspection_floor)
                inspection_tool_slack = max(0, remaining_tool_actions - inspection_tool_floor)
                max_parallel_reads = min(max_parallel_reads, inspection_tool_slack)
            inspection_model_slack = min(
                inspection_model_slack,
                funded_calls - minimum_cost_successors["read_file"],
            )
            exploration_capacity = min(exploration_capacity, inspection_model_slack)
            if ((path_available or shared_failure_exploration or requested_revision)
                    and completion_cost_policy == COMPLETION_RECOVERY_POLICY):
                route = recovery_routes["read_file"]
                outputs = route.output_options
                reserved = max(sum(cost_ledger.future_call_reservation_nanos(output_ceiling=n)
                                   for n in ceilings) for ceilings in outputs) + correction_reserve
                read_cost = cost_ledger.future_call_reservation_nanos(
                    output_ceiling=correction_ceiling if correction_pending else finalization_floor)
                # Count-only capacity is an upper bound; qualify it by the same
                # conservative role reservation used to admit this actual read.
                cost_reads = max(0, (cost_ledger.remaining_nanos - reserved) // read_cost)
                inspection_model_slack = min(inspection_model_slack, cost_reads)
                if remaining_seconds is not None:
                    seconds = route.seconds + (FOLLOWUP_SECONDS * correction_model_reserve
                                               if route.routes else 0)
                    time_reads = max(0, int((remaining_seconds - seconds)
                                           // FOLLOWUP_SECONDS))
                    inspection_model_slack = min(inspection_model_slack, time_reads)
                exploration_capacity = min(exploration_capacity, inspection_model_slack)
    if diagnostic_relaxes_inspection and inspection_allowed:
        inspection_model_slack = min(inspection_model_slack, 1)
        inspection_tool_slack = min(inspection_tool_slack, 1)
    if (path_available or shared_failure_exploration) and inspection_allowed:
        # This stage offers one read/search per response, so its visible model
        # and action capacities share the tightest currently admitted resource.
        exploration_capacity = min(inspection_model_slack, inspection_tool_slack)
        inspection_model_slack = inspection_tool_slack = exploration_capacity
    if ((observation_blocked or path_blocked or helper_blocked) and not test_comparison_pending
            and "run_probe" not in allowed):
        workflow_gate = "verification_incomplete"
        completion_possible = protected_completion_possible = False
    if test_comparison_pending and "run_tests" not in allowed:
        workflow_gate = "verification_incomplete"
        completion_possible = protected_completion_possible = False
    repair_test_edit_enabled &= mutation_allowed
    exploration_state = (
        "last_opportunity"
        if inspection_allowed and exploration_capacity == 1
        else "open"
        if inspection_allowed
        else "closed"
    )
    closure_reason = (
        None
        if inspection_allowed
        else "completion_impossible"
        if not completion_possible
        else "workflow_ready_to_submit"
        if ready_to_submit
        else "completion_horizon"
    )
    current_diff_hash = getattr(summary, "patch_hash", None)
    commitment_active = (
        isinstance(current_diff_hash, str)
        and counters.commitment_diff_hash == current_diff_hash
        and has_current_mutation_evidence
    )
    policy = _ToolPolicy(
        workflow_gate=workflow_gate,
        allowed_tools=frozenset(allowed),
        check_ids=available_check_ids,
        remaining_check_ids=remaining_check_ids,
        max_parallel_reads=max_parallel_reads,
        minimum_completion_calls=budget.minimum,
        completion_budget_calls=budget.protected,
        mutation_recovery_reserve_calls=budget.mutation_retry_reserve,
        check_recovery_reserve_calls=budget.check_recovery_reserve,
        check_recovery_reserve_ids=unused_check_ids if budget.future_check_failures else (),
        completion_possible=completion_possible,
        protected_completion_possible=protected_completion_possible,
        exploration_allowed=inspection_allowed,
        exploration_state=exploration_state,
        commitment_action_state="advisory" if commitment_active else "inactive",
        model_turns_available_for_exploration=(
            max(0, inspection_model_slack) if inspection_allowed else 0
        ),
        tool_actions_available_for_exploration=(
            max_parallel_reads
            if exploration_state == "last_opportunity"
            else max(0, inspection_tool_slack) if inspection_allowed else 0
        ),
        closure_reason=closure_reason,
        tools_closing_after_this_turn=(),
        required_inspection_for_completion=required_inspection and inspection_allowed,
        targeted_check_repair_inspection=False,
        targeted_check_repair_required=False,
        targeted_mutation_repair_inspection=False,
        targeted_read_paths=(),
        current_repair_read_reserve_calls=budget.current_read_reserve,
        future_check_failure_slots=budget.future_check_failures,
        optional_mutation_completion_calls=optional_mutation_completion_calls,
        optional_mutation_protected_calls=optional_mutation_protected_calls,
        mutation_completion_possible=mutation_allowed,
        mutation_protected_completion_possible=mutation_protected_completion_possible,
        inspection_uses_repair_credit=inspection_uses_credit and inspection_allowed,
        repair_inspection_policy=repair_inspection_policy,
        inspection_reserve_calls=inspection_floor,
        inspection_released_check_recovery_calls=released_check_recovery,
        repair_recheck=repair_recheck,
        minimum_completion_tool_actions=budget.minimum_tool_actions,
        completion_budget_tool_actions=budget.protected_tool_actions,
        optional_mutation_completion_tool_actions=mutation_budget.minimum_tool_actions,
        optional_mutation_protected_tool_actions=mutation_budget.protected_tool_actions,
        inspection_reserve_tool_actions=inspection_tool_floor,
        repair_prediction=repair_prediction or None,
        repair_test_edit_enabled=repair_test_edit_enabled,
        repair_test_edit_minimum_calls=test_edit_budget.minimum,
        repair_test_edit_minimum_tool_actions=test_edit_budget.minimum_tool_actions,
        selected_test_reserve_tool_actions=selected_test_tool_floor,
        selected_test_comparison_required=diagnosed_test_bound or test_comparison_pending,
        original_failure_diagnostic=({
            **diagnostic,
            "offered_tools": sorted(allowed & {"read_file", "search_files", "run_probe"})
            if diagnostic_available else [],
            "uses_minimum_completion_reserve": bool(diagnostic_available and (
                (diagnostic_relaxes_inspection and inspection_allowed)
                or ("run_probe" in allowed and (
                    remaining_model_calls - 1 < probe_budget.protected
                    or remaining_tool_actions - 1 < probe_budget.protected_tool_actions
                ))
            )),
            "limit": ("Pending path diagnosis permits repeated reads within its projected "
                      "shared completion budget; its diagnostic execution and request "
                      "correction remain bounded separately." if path_blocked else
                     "One preparation read and one model diagnostic per refuted candidate "
                     "may spend speculative recovery. The minimum repair, checks, replay and "
                     "finish must still fit; request correction for path diagnosis is separate."),
        } if diagnostic is not None else None),
        observation_correction=({
            **observation_fix, "offered_tools": sorted(allowed),
            "uses_minimum_completion_reserve": "run_probe" in allowed,
        } if observation_blocked else None),
        repair_path_diagnosis=(
            _repair_path_resources(
                path_diagnosis, allowed, required_inspection=required_inspection,
                closure_reason=closure_reason,
                model_turns_available=(inspection_model_slack if inspection_allowed else 0),
                tool_actions_available=(inspection_tool_slack if inspection_allowed else 0),
                minimum_calls=budget.minimum, minimum_tool_actions=budget.minimum_tool_actions,
                request_correction_reserved=completion_state.path_request_correction_available,
            ) if path_diagnosis.get("status") not in {None, "not_needed"}
            and not observation_blocked else None
        ),
        helper_correction=({**helper_fix, "offered_tools": sorted(allowed),
                            "uses_minimum_completion_reserve": "run_probe" in allowed}
                           if helper_blocked else None),
        first_observation=({**first_observation,
                            "offered": "observe_original" in allowed,
                            "minimum_route_calls": budget.minimum + 1,
                            "minimum_route_tool_actions": budget.minimum_tool_actions + 1,
                            "reservation": "shared_protected_slack_one_observation"}
                           if first_observation.get("status") not in {None, "not_needed"}
                           else None),
    )
    if funded_calls is not None and minimum_cost_successors is not None:
        future_calls = max(minimum_cost_successors[tool] for tool in allowed)
        policy = replace(policy, completion_cost={
            "policy": completion_cost_policy,
            "future_input_tokens": segments.MAX_INPUT_TOKENS,
            "future_output_tokens": completion_cost_contract(
                COMPLETION_MINIMUM_POLICY,
            )["future_output_tokens"],
            "per_call_reservation_nanos": cost_unit,
            "funded_calls": funded_calls,
            "admitted_call_slots": max(int("finish_task" in allowed), funded_calls),
            "future_calls_reserved": future_calls,
            "future_cost_reserve_nanos": (future_calls * cost_unit + correction_reserve
                                          + (finalization_premium if future_calls else 0)),
            "basis": "largest_offered_action_minimum_successor",
            "recovery_scope": "Protected forecasts retain model/tool slots; money reserves only "
                              "successful minimum successors, not failure recovery.",
            "limit": "Successful actions only. Minimum output admission; useful output and task "
                     "success are not guaranteed.",
        })
        if completion_cost_policy == COMPLETION_RECOVERY_POLICY:
            policy.completion_cost.update({
                "basis": "minimum_successor_plus_correction_and_finalization",
                "finalization_output_floor": finalization_floor,
                "finalization_cost_reserved_nanos": finalization_premium if future_calls else 0,
                "correction_credits_remaining": int(correction_available),
                "correction_pending": correction_pending,
                "correction_output_ceiling": correction_ceiling,
                "correction_call_cost_nanos": correction_cost,
                "correction_cost_reserved_nanos": correction_reserve,
                "correction_model_calls_reserved": correction_model_reserve,
                "current_minimum_output_ceiling": (
                    correction_ceiling if correction_pending else finalization_floor
                    if ready_to_submit else MINIMUM_OUTPUT_CEILING
                ),
                "recovery_scope": "One protocol correction per run at the correction output "
                                  "ceiling, never renewed by valid actions. No tool-failure or "
                                  "unknown-billing retry funding.",
                "limit": "Correction and finalization have bounded output allowances, not "
                         "guarantees of useful output or repair. Other successors retain "
                         "minimum output admission only. The invocation cap is unchanged.",
            })
            routes = {tool: recovery_routes[tool] for tool in allowed}
            role_costs = {tool: max(
                sum(cost_ledger.future_call_reservation_nanos(output_ceiling=n) for n in ceilings)
                for ceilings in route.output_options)
                          for tool, route in routes.items()}
            policy.completion_cost.update({
                "basis": "largest_offered_action_role_successor",
                "future_output_tokens": finalization_floor,
                "funded_calls_basis": "minimum-unit-upper-bound-before-role-admission",
                "future_calls_reserved": max(len(o) for r in routes.values()
                                              for o in r.output_options),
                "future_cost_reserve_nanos": max(role_costs.values()) + correction_reserve,
                "successor_output_ceilings": {t: list(r.output_ceilings)
                                             for t, r in routes.items()},
                "failure_recovery_reserved": {t: r.failure_recovery for t, r in routes.items()},
                "future_time_reserve_seconds": max(
                    r.seconds + (FOLLOWUP_SECONDS * correction_model_reserve if r.routes else 0)
                    for r in routes.values()),
                "remaining_seconds": remaining_seconds,
                "resource_rejections": resource_rejections,
                "completion_routes": {tool: {
                    "kind": ("requested_revision" if requested_revision
                             and tool in revision_exploration else
                             "one_failure_revision" if route.failure_recovery
                             else "required_completion"),
                    "model_calls": route.model_calls,
                    "tool_actions": route.tool_actions,
                    "required_model_calls": (route.model_calls if requested_revision
                        and tool in revision_exploration else
                        route.routes[0].model_calls if route.routes else None),
                    "required_tool_actions": (route.tool_actions if requested_revision
                        and tool in revision_exploration else
                        route.routes[0].tool_actions if route.routes else None),
                    "released_reason": released_failure_recovery.get(tool),
                    "adapter": route.adapter_reason,
                } for tool, route in routes.items()},
                "route_policy": "shared-completion-paths-v1",
                "current_minimum_output_ceiling": (correction_ceiling if correction_pending
                    else desired_output_ceiling if requires_mutation and "replace_text" in allowed
                    else finalization_floor if allowed - {"stop_task"}
                    else MINIMUM_OUTPUT_CEILING),
                "recovery_scope": "Selected routes share response, tool, output and execution "
                                  "reservations. One future failure can retain revision, including "
                                  "a possible original-path diagnosis. Known-original exploration "
                                  "may release future revision while keeping current completion "
                                  "and correction; older multiple-failure protection is separate.",
                "limit": "Nominal check timeouts, follow-up floors and output allowances are "
                         "reserved within existing caps; useful output and repair are unproven.",
            })
            if requested_revision:
                policy.completion_cost["requested_revision"] = {
                    "diff_hash": requested_revision_diff_hash,
                    "scope": "preserve_one_successful_revision_after_exploration",
                    "verification_credit": False,
                    "finish_gate_changed": False,
                    "successor_output_options": {
                        tool: [list(o) for o in route.output_options]
                        for tool, route in routes.items() if tool in revision_exploration},
                }
    elif funded_calls is not None:
        successors = [0]  # Stop and a successful finish need no subsequent call.
        if ("finish_task" in allowed and verification.get("pending_count", 0)
                and protected_completion_possible):
            # The final public replay may reject this finish. Preserve the same
            # funded recovery reported by the model/action forecast.
            successors.append(budget.protected - 1)
        if inspection_allowed:
            successors.append(inspection_floor)
        if mutation_allowed:
            successors.append((
                optional_mutation_protected_calls
                if mutation_protected_completion_possible else optional_mutation_completion_calls
            ) - 1)
            if repair_test_edit_enabled:
                successors.append(test_edit_budget.minimum - 1)
        if history_search.TOOL in allowed:
            successors.append(budget.protected)
        if "run_tests" in allowed:
            successors.append(selected_test_floor)
        if "run_probe" in allowed:
            successors.append(probe_floor)
        if "observe_original" in allowed:
            successors.append(budget.minimum)
        if "run_check" in allowed:
            successors.append(check_successor_reserve)
        future_calls = max(successors)
        policy = replace(policy, completion_cost={
            "policy": completion_cost_policy,
            "future_input_tokens": segments.MAX_INPUT_TOKENS,
            "future_output_tokens": completion_cost_contract()["future_output_tokens"],
            "per_call_reservation_nanos": cost_unit,
            "funded_calls": funded_calls,
            "admitted_call_slots": max(int(ready_to_submit), funded_calls),
            "future_calls_reserved": future_calls,
            "future_cost_reserve_nanos": future_calls * cost_unit,
            "basis": "largest_offered_action_successor",
            "limit": "Minimum output admission, not a guarantee of useful output or task success.",
        })
    if inspection_allowed and _preview_inspection:
        if path_available or shared_failure_exploration:
            # One action per response; the forecast already incorporates the
            # unchanged anchor, correction, monetary and nominal-time reserves.
            # Do not assume a useful read or mutate the live cost ledger to preview it.
            return replace(policy, tools_closing_after_this_turn=(
                ("read_file", "search_files") if exploration_capacity == 1 else ()))
        # Advisory single-inspection forecast, not another admission rule. Reuse
        # the actual policy so optional probes/checks cannot disappear unannounced.
        # Evidence/gate stay unchanged; a useful read or a different action may
        # produce a different successor. Never mutate live counters or read files.
        after_inspection = _tool_policy(
            gateway,
            replace(
                counters,
                model_calls=counters.model_calls + 1,
                tool_actions=counters.tool_actions + 1,
                protocol_recoveries=(
                    0 if completion_cost_policy == COMPLETION_RECOVERY_POLICY
                    else counters.protocol_recoveries
                ),
                failed_check_repair_read_used=(
                    counters.failed_check_repair_read_used or counters.failed_check_pending
                ),
            ),
            limits,
            snapshot=snapshot,
            repair_inspection_policy=repair_inspection_policy,
            repair_recheck=repair_recheck,
            cost_ledger=cost_ledger,
            completion_cost_policy=completion_cost_policy,
            desired_output_ceiling=desired_output_ceiling,
            max_correction_output_tokens=max_correction_output_tokens,
            remaining_seconds=remaining_seconds,
            _preview_inspection=False,
            requested_revision_diff_hash=requested_revision_diff_hash,
            _cost_call_limit=(max(0, funded_calls - 1) if funded_calls is not None else None),
            _diagnostic_spent=True,
        )
        policy = replace(
            policy,
            tools_closing_after_this_turn=tuple(
                sorted(policy.allowed_tools - after_inspection.allowed_tools)
            ),
        )
    return policy


def _repair_path_resources(
    state: dict[str, Any], allowed_tools: set[str] | frozenset[str], *,
    required_inspection: bool, closure_reason: str | None,
    model_turns_available: int = 0, tool_actions_available: int = 0,
    minimum_calls: int = 0, minimum_tool_actions: int = 0,
    request_correction_reserved: bool = False,
) -> dict[str, Any]:
    """Qualify pending exploration against this turn's actual resource admission."""
    allowance = bool(state.get("preparation_available"))
    pending = state.get("status") == "needs_path_diagnosis" and bool(state.get("blocked"))
    offered = bool(allowance and pending and {"read_file", "search_files"} & allowed_tools)
    return {
        **state,
        "preparation_allowance_available": allowance,
        "preparation_available": offered,
        "preparation_model_turns_available": model_turns_available if offered else 0,
        "preparation_tool_actions_available": tool_actions_available if offered else 0,
        "preparation_limit": "shared_completion_budget",
        "preparation_completion_calls_reserved": minimum_calls if pending else 0,
        "preparation_completion_tool_actions_reserved": minimum_tool_actions if pending else 0,
        "preparation_request_correction_reserved": bool(pending and request_correction_reserved),
        "preparation_required_for_completion": bool(pending and required_inspection),
        "preparation_blocked_reason": (
            None if offered else "diagnosis_unavailable" if not pending
            else "allowance_spent" if not allowance else closure_reason or "workflow_gate"
        ),
        "offered_tools": sorted(allowed_tools),
    }


def _reproduction_review_resources(
    review: dict[str, Any], policy: _ToolPolicy,
) -> dict[str, Any]:
    """Keep the duplicate model-facing path state consistent without changing its ledger."""
    completion = review.get("completion", {})
    path_state = completion.get("repair_path")
    if not isinstance(path_state, dict) or "preparation_available" not in path_state:
        return review
    projected = policy.repair_path_diagnosis or _repair_path_resources(
        path_state, policy.allowed_tools, required_inspection=False,
        closure_reason=policy.workflow_gate,
    )
    return {**review, "completion": {**completion, "repair_path": projected}}


def _repair_inspection_payload(policy: _ToolPolicy) -> dict[str, Any]:
    diagnostic = ({"original_failure_diagnostic": policy.original_failure_diagnostic}
                  if policy.original_failure_diagnostic is not None else {})
    if policy.observation_correction is not None:
        diagnostic["observation_correction"] = policy.observation_correction
    if policy.repair_path_diagnosis is not None:
        diagnostic["repair_path_diagnosis"] = policy.repair_path_diagnosis
    if policy.helper_correction is not None:
        diagnostic["helper_correction"] = policy.helper_correction
    if policy.first_observation is not None:
        diagnostic["first_observation"] = policy.first_observation
    if policy.repair_prediction is not None:
        diagnostic["repair_prediction"] = {
            **policy.repair_prediction,
            "test_edit_enabled": policy.repair_test_edit_enabled,
            "test_edit_minimum_calls": policy.repair_test_edit_minimum_calls,
            "test_edit_minimum_tool_actions": policy.repair_test_edit_minimum_tool_actions,
        }
    if policy.repair_inspection_policy == "protected-v1":
        return diagnostic
    return {**diagnostic, "repair_inspection": {
        "policy": policy.repair_inspection_policy,
        "reserve_calls_after_inspection": policy.inspection_reserve_calls,
        "released_future_check_recovery_calls": policy.inspection_released_check_recovery_calls,
        **({"reserve_tool_actions_after_inspection": policy.inspection_reserve_tool_actions}
           if policy.repair_recheck else {}),
    }}


def _completion_cost_payload(policy: _ToolPolicy) -> dict[str, Any]:
    return {"completion_cost": policy.completion_cost} if policy.completion_cost is not None else {}


def _completion_resources_payload(policy: _ToolPolicy) -> dict[str, Any]:
    if not policy.repair_recheck:
        return {}
    return {
        "minimum_completion_tool_actions": policy.minimum_completion_tool_actions,
        "completion_budget_tool_actions": policy.completion_budget_tool_actions,
    }


def _mutation_completion_horizon(policy: _ToolPolicy) -> dict[str, Any]:
    """Describe starting an edit now, before any further source evidence is acquired."""

    return {
        "minimum_calls": policy.optional_mutation_completion_calls,
        "protected_calls": policy.optional_mutation_protected_calls,
        **({
            "minimum_tool_actions": policy.optional_mutation_completion_tool_actions,
            "protected_tool_actions": policy.optional_mutation_protected_tool_actions,
        } if policy.repair_recheck else {}),
        "minimum_possible": policy.mutation_completion_possible,
        "protected_possible": policy.mutation_protected_completion_possible,
        "recovery_warning": (
            "An edit, all checks, and finish fit if the edit succeeds; "
            "full failure-recovery reserves do not fit."
            if policy.mutation_completion_possible
            and not policy.mutation_protected_completion_possible
            else None
        ),
    }


def _commitment_signal(
    gateway: DevToolGateway,
    counters: _RunCounters,
    policy: _ToolPolicy,
    *,
    snapshot: DevGatewayStateSnapshot | None = None,
) -> dict[str, Any] | None:
    no_gain_turns = counters.consecutive_no_evidence_gain_turns
    current_diff_hash = (
        snapshot.diff.patch_hash if snapshot is not None else gateway.current_diff_hash
    )
    has_current_mutation_evidence = (
        bool(snapshot.mutation_evidence_paths)
        if snapshot is not None
        else gateway.has_current_mutation_evidence()
    )
    if (
        counters.commitment_diff_hash != current_diff_hash
        or not has_current_mutation_evidence
    ):
        return None
    state = "review_information_value"
    hard_gate = False
    message = (
        "Recent inspection has not added uncovered public source lines. This is "
        "a diagnostic signal, not proof that the solution is known. A negative search "
        "or reread may still answer a concrete question; choose inspection, mutation "
        "or checks according to which result could change the next decision."
    )
    return {
        "state": state,
        "reason": "consecutive_inspection_without_new_public_coverage",
        "consecutive_no_evidence_gain_turns": no_gain_turns,
        "activated_after_consecutive_no_gain_turns": (
            counters.commitment_trigger_no_gain_turns
        ),
        "hard_gate": hard_gate,
        "message": message,
    }


def _completion_horizon_payload(
    gateway: DevToolGateway,
    counters: _RunCounters,
    limits: Any,
    policy: _ToolPolicy,
    *,
    snapshot: DevGatewayStateSnapshot | None = None,
) -> dict[str, Any]:
    remaining_model_calls = max(0, limits.max_model_calls - counters.model_calls)
    remaining_tool_actions = max(0, limits.max_tool_actions - counters.tool_actions)
    blocking_resources: list[str] = []
    if not policy.completion_possible and policy.completion_cost:
        blocking_resources.extend(sorted(set(
            policy.completion_cost.get("resource_rejections", {}).values())))
    if (policy.completion_cost is not None
            and policy.completion_cost["admitted_call_slots"] < policy.minimum_completion_calls):
            blocking_resources.append("cost")
    correction_model_reserve = (
        policy.completion_cost.get("correction_model_calls_reserved", 0)
        if policy.completion_cost is not None else 0
    )
    if remaining_model_calls < policy.minimum_completion_calls + correction_model_reserve:
        blocking_resources.append("model_calls")
    if remaining_tool_actions < policy.minimum_completion_tool_actions:
        blocking_resources.append("tool_actions")
    current_diff = snapshot.diff if snapshot is not None else gateway.current_diff
    visible_status = (
        snapshot.visible_check_status
        if snapshot is not None
        else tuple(gateway.visible_check_status())
    )
    current_check_failed = any(row["status"] == "FAIL" for row in visible_status)
    if (
        (policy.workflow_gate in {"needs_mutation", "needs_path_diagnosis"} or current_check_failed)
        and gateway.accepted_mutations >= limits.max_accepted_mutations
    ):
        blocking_resources.append("accepted_mutations")
    if current_diff.untracked_files:
        blocking_resources.append("workspace_scope")
    return {
        "workflow_gate": policy.workflow_gate,
        "remaining_model_calls": remaining_model_calls,
        "remaining_tool_actions": remaining_tool_actions,
        "minimum_completion_calls": policy.minimum_completion_calls,
        **_completion_resources_payload(policy),
        "blocking_resources": blocking_resources,
        **_completion_cost_payload(policy),
    }


def _tool_policy_transition(
    journal: DevJournal,
    policy: _ToolPolicy,
) -> dict[str, Any] | None:
    events = journal.events()
    latest_decision = next(
        (event for event in reversed(events) if event["event_type"] == "turn_decision_recorded"),
        None,
    )
    if latest_decision is None:
        return None
    prior_turn_id = latest_decision["payload"].get("turn_id")
    prior_start = next(
        (
            event
            for event in reversed(events)
            if event["event_type"] == "turn_started"
            and event["payload"].get("turn_id") == prior_turn_id
        ),
        None,
    )
    if prior_start is None:
        raise RecoveryError("latest model decision has no recorded tool policy")
    previous_raw = prior_start["payload"].get("available_tool_names")
    if not isinstance(previous_raw, list) or not all(
        isinstance(name, str) for name in previous_raw
    ):
        raise RecoveryError("latest model decision has an invalid tool policy")
    previous = frozenset(previous_raw)
    current = policy.allowed_tools
    if previous == current:
        return None
    read_tools = {"read_file", "search_files"}
    previous_inspection = bool(previous & read_tools)
    current_inspection = bool(current & read_tools)
    if current_inspection:
        reason = (
            "inspection_reopened"
            if not previous_inspection
            else (
                "workflow_gate"
                if prior_start["payload"].get("workflow_gate") != policy.workflow_gate
                else "evidence_changed"
            )
        )
        from_state = "execution_only" if not previous_inspection else "inspection_open"
        to_state = "inspection_open"
    elif previous_inspection:
        reason = policy.closure_reason or "workflow_gate"
        from_state = "inspection_open"
        to_state = "execution_only"
    else:
        reason = (
            "workflow_gate"
            if prior_start["payload"].get("workflow_gate") != policy.workflow_gate
            else "evidence_changed"
        )
        from_state = "execution_only"
        to_state = "execution_only"
    return {
        "from": from_state,
        "to": to_state,
        "reason": reason,
        "removed_tools": sorted(previous - current),
        "added_tools": sorted(current - previous),
        "remaining_tools": sorted(current),
    }


def _parallel_tool_calls(policy: _ToolPolicy) -> bool:
    """Parallel generation is useful only when the gate can accept a read batch."""
    return policy.max_parallel_reads > 1 and bool(
        {"read_file", "search_files"} & policy.allowed_tools)


def _protocol_correction(
    *,
    turn_id: str,
    code: str,
    issue: str,
    gateway: DevToolGateway,
    policy: _ToolPolicy,
    tool_contract_failure: DevToolContractFailure | None = None,
    rejected_calls: Sequence[RequestedTool] = (),
) -> dict[str, Any]:
    allowed = policy.allowed_tools
    actions: list[str] = []
    inspection_names = sorted({"read_file", "search_files"} & allowed)
    if inspection_names:
        inspection = " or ".join(inspection_names)
        if policy.required_inspection_for_completion:
            actions.append(
                f"Use {inspection} to obtain current source evidence for the intended edit."
            )
        else:
            actions.append(
                f"Use {inspection} when its result can resolve a concrete public question."
            )
        if policy.exploration_state == "last_opportunity":
            actions.append("The remaining completion budget allows one inspection turn.")
    if "replace_text" in allowed:
        actions.append(
            "Use replace_text for an evidence-backed edit; a failed proposal may be "
            "revised or abandoned because its rollback baseline remains current."
        )
    if "run_check" in allowed:
        actions.append(
            "Use run_check for an unrun visible check. Only checks on the submitted "
            "diff satisfy completion; a check on an empty diff is diagnostic."
        )
    if "finish_task" in allowed:
        actions.append(
            "Before finish_task, judge the current evidence against public requirements "
            "and unfinished verification plans; justify remaining gaps in the assessment. "
            "Missing original evidence returns unverified_delivery."
        )
    if "run_probe" in allowed:
        actions.append(
            "Use run_probe for a small public behavior experiment when useful; it is "
            "diagnostic only and never replaces required visible checks."
        )
    if "run_tests" in allowed:
        actions.append(
            "Use run_tests to select public test files or node IDs from a registered suite; "
            "comparison runs the same tests before and after the implementation change and "
            "costs two tool executions. PASS/PASS does not distinguish the repair; selected "
            "tests do not replace the original invocation or required visible checks."
        )
    if "stop_task" in allowed:
        actions.append(
            "Use stop_task to abandon without submission or evaluation when no available "
            "action supports progress; it is not successful completion."
        )
    result = {
        "turn_id": turn_id,
        "code": code,
        "issue": issue,
        "message": f"{issue} Current gate is {policy.workflow_gate}. {' '.join(actions)}",
        "workflow_gate": policy.workflow_gate,
        "remaining_visible_check_ids": list(policy.remaining_check_ids),
        "available_tool_names": sorted(allowed),
        "exploration_state": policy.exploration_state,
        "tool_contract_failure": (
            tool_contract_failure.model_dump(mode="json")
            if tool_contract_failure is not None
            else None
        ),
    }
    if policy.workflow_gate == "needs_path_diagnosis":
        result["diagnosis_correction"] = diagnosis_context.correction(
            code, issue, result["tool_contract_failure"])
        result["message"] = result["diagnosis_correction"]["message"]
    elif policy.workflow_gate == "needs_mutation" and (
            {"replace_text", "observe_original"} & allowed):
        result["repair_correction"] = repair_context.correction(
            code, issue, result["tool_contract_failure"])
        result["message"] = result["repair_correction"]["message"]
    elif policy.workflow_gate == "ready_to_submit":
        result["completion_correction"] = completion_context.correction(
            code, issue, result["tool_contract_failure"])
        result["message"] = result["completion_correction"]["message"]
    drafts = correction_drafts.build(
        rejected_calls, turn_id=turn_id, diff_hash=gateway.current_diff.patch_hash
    ) if rejected_calls else None
    if drafts is not None:
        result["rejected_drafts"] = drafts
        result["message"] += " Reuse current rejected_drafts as appropriate; return one action."
    return result


def _build_context(
    *,
    package: Any,
    gateway: DevToolGateway,
    journal: DevJournal,
    correction: dict[str, Any] | None,
    latest_tool_results: list[DevToolResult],
    counters: _RunCounters,
    elapsed_seconds: float,
    limits: Any,
    policy: _ToolPolicy | None = None,
    snapshot: DevGatewayStateSnapshot | None = None,
    tool_policy_transition: dict[str, Any] | None = None,
    projection: SourceProjection | None = None,
    repair_recheck: bool = False,
    probe_recheck_policy: str = "none",
    repair_inspection_policy: str = "protected-v1",
    planning_policy: str = "none",
    evaluation_reserve_seconds: int = 0,
) -> str:
    projection = projection or gateway.prepare_context_projection(
        latest_results=latest_tool_results,
    )
    active_snapshot = snapshot or gateway.state_snapshot(projection=projection)
    summary = active_snapshot.diff
    if correction and "rejected_drafts" in correction:
        correction = {**correction, "rejected_drafts": correction_drafts.project(
            correction["rejected_drafts"], diff_hash=summary.patch_hash)}
    recheck_context = (
        repair_recheck_context(journal, summary.patch_hash) if repair_recheck else None
    )
    active_policy = policy or _tool_policy(
        gateway,
        counters,
        limits,
        snapshot=active_snapshot,
        repair_inspection_policy=repair_inspection_policy,
        repair_recheck=repair_recheck,
    )
    commitment_signal = _commitment_signal(
        gateway,
        counters,
        active_policy,
        snapshot=active_snapshot,
    )
    ledger = gateway.evidence_ledger(diff_hash=summary.patch_hash)
    ledger.pop("canonical_searches", None)
    recent_inspections = ledger.pop("recent_inspections", [])[:3]
    ledger["recent_inspection_outcomes"] = [
        {key: row[key] for key in (
            "tool", "action_id", "path", "start_line", "end_line", "query", "path_glob", "outcome",
            "evidence_goal", "coverage_breakdown", "returned_span_count",
            "new_covered_line_count", "new_editable_line_count", "new_supporting_line_count",
        ) if key in row}
        for row in recent_inspections
    ]
    mutation = gateway.actionable_last_successful_mutation(diff_hash=summary.patch_hash)
    payload = {
        "workflow_gate": active_policy.workflow_gate,
        "completion_guidance": _completion_guidance(active_snapshot, active_policy),
        "visible_check_status": list(active_snapshot.visible_check_status),
        "remaining_visible_check_ids": list(active_snapshot.remaining_visible_check_ids),
        "remaining_budget": {
            "model_calls": max(0, limits.max_model_calls - counters.model_calls),
            "tool_actions": max(0, limits.max_tool_actions - counters.tool_actions),
            "accepted_mutations": max(
                0,
                limits.max_accepted_mutations - gateway.accepted_mutations,
            ),
            "active_wall_time_seconds": max(
                0,
                int(limits.wall_time_seconds - evaluation_reserve_seconds - elapsed_seconds),
            ),
            **({
                "active_wall_time_scope": "solver",
                "total_active_wall_time_seconds": max(
                    0, int(limits.wall_time_seconds - elapsed_seconds),
                ),
                "evaluation_reserve_seconds": evaluation_reserve_seconds,
            } if evaluation_reserve_seconds else {}),
            "consecutive_protocol_corrections": max(
                0,
                limits.max_protocol_recoveries - counters.protocol_recoveries,
            ),
        },
        "action_horizon": {
            **_repair_inspection_payload(active_policy),
            **_completion_resources_payload(active_policy),
            "minimum_completion_calls": active_policy.minimum_completion_calls,
            "completion_budget_calls": active_policy.completion_budget_calls,
            "feedback_recovery_reserve_calls": (active_policy.feedback_recovery_reserve_calls),
            "mutation_recovery_reserve_calls": (active_policy.mutation_recovery_reserve_calls),
            "check_recovery_reserve_calls": (active_policy.check_recovery_reserve_calls),
            "check_recovery_reserve_ids": list(active_policy.check_recovery_reserve_ids),
            "current_repair_read_reserve_calls": active_policy.current_repair_read_reserve_calls,
            "future_check_failure_slots": active_policy.future_check_failure_slots,
            "inspection_uses_repair_credit": active_policy.inspection_uses_repair_credit,
            "completion_possible": active_policy.completion_possible,
            "protected_completion_possible": (active_policy.protected_completion_possible),
            "mutation_completion_horizon": _mutation_completion_horizon(active_policy),
            "exploration_allowed": active_policy.exploration_allowed,
            "exploration_state": active_policy.exploration_state,
            "commitment_action_state": active_policy.commitment_action_state,
            "model_turns_available_for_exploration": (
                active_policy.model_turns_available_for_exploration
            ),
            "tool_actions_available_for_exploration": (
                active_policy.tool_actions_available_for_exploration
            ),
            "closure_reason": active_policy.closure_reason,
            "tools_closing_after_this_turn": list(active_policy.tools_closing_after_this_turn),
            "tool_closure_prediction_basis": (
                "after_one_read_or_search_with_unchanged_evidence; "
                "larger_parallel_batches_or_other_actions_may_differ"
            ),
            "required_inspection_for_completion": (
                active_policy.required_inspection_for_completion
            ),
            "targeted_check_repair_inspection": (active_policy.targeted_check_repair_inspection),
            "targeted_check_repair_required": (active_policy.targeted_check_repair_required),
            "targeted_mutation_repair_inspection": (
                active_policy.targeted_mutation_repair_inspection
            ),
            "targeted_read_paths": list(active_policy.targeted_read_paths),
            "tool_policy_transition": tool_policy_transition,
            "max_parallel_reads_this_turn": active_policy.max_parallel_reads,
            "inspection_turns_at_current_diff": counters.inspection_turns_at_diff,
            "consecutive_no_marginal_evidence_gain_inspection_turns": (
                counters.consecutive_no_evidence_gain_turns
            ),
            "failed_mutation_repair_turns": counters.failed_mutation_repair_turns,
            "commitment_active_for_current_diff": (
                counters.commitment_diff_hash == summary.patch_hash
            ),
        },
        "current_public_failure": gateway.current_public_failure(
            diff_hash=summary.patch_hash,
            allowed_tools=active_policy.allowed_tools,
        ),
        "mutation_readiness": gateway.mutation_readiness(
            current_paths=active_snapshot.mutation_evidence_paths
        ),
        "mutation_scope_budget": gateway.mutation_scope_budget(summary=summary),
        "observed_source_index": build_observed_source_index(
            projection.delivered_spans,
            editable_paths=active_snapshot.mutation_evidence_paths,
        ),
        "evidence_ledger": ledger,
        "working_notes": gateway.working_notes(diff_hash=summary.patch_hash),
        "context_projection": {
            "retained_content_chars": projection.retained_content_chars,
            "retained_content_limit": gateway.retained_source_chars,
            "omitted_observed_line_count": projection.omitted_observed_line_count,
            "omitted_pinned_ranges": list(projection.omitted_pinned_ranges),
            "omitted_observed_ranges": list(projection.omitted_observed_ranges),
            "omitted_observed_range_count": projection.omitted_observed_range_count,
            "delivered_source_hash": sha256_json(projection.delivered_spans),
            "mutation_readiness_basis": "delivered_editable_source_not_semantic_sufficiency",
        },
        "commitment_signal": commitment_signal,
        "available_tool_names": sorted(active_policy.allowed_tools),
        "last_failed_mutation": gateway.last_failed_mutation,
        "last_successful_mutation": mutation,
        "current_diff": {
            "patch": summary.patch,
            "patch_hash": summary.patch_hash,
            "changed_files": summary.changed_files,
            "added_lines": summary.added_lines,
            "deleted_lines": summary.deleted_lines,
            "untracked_files": summary.untracked_files,
            "truncated": False,
        },
        "recent_checks": _recent_checks(
            gateway, diff_hash=summary.patch_hash,
            pinned_action_id=(
                recheck_context["last_result"]["action_id"]
                if recheck_context and recheck_context["last_result"] else None
            ),
        ),
        "public_execution_summary": gateway.public_execution_summary(diff_hash=summary.patch_hash),
        "latest_tool_results": [
            project_mutation_result(
                project_probe_result(result.model_dump(mode="json", exclude={"replayed"}))
            )
            for result in latest_tool_results
        ],
        "source_spans": list(projection.source_spans),
        "recent_attempt_result_next_question": _cards(journal, correction),
        "public_task": package.public.model_dump(mode="json"),
    }
    if getattr(gateway, "dependency_sources", None) is not None:
        # Preserve the existing registered, independently bounded read-only pool.
        # Never merge it into repository spans or acquire another source scope here.
        payload["dependency_sources"] = gateway.dependency_context_spans()
    if gateway.public_task.test_suites:
        payload["recent_tests"] = recent_tests(journal.events(), summary.patch_hash)
    if planning_policy != "none":
        payload["working_plan"] = working_plan.project(
            journal.events(), diff_hash=summary.patch_hash, gate=active_policy.workflow_gate,
            policy=planning_policy,
        )
    if gateway.probe_policy != "none":
        from patchloop.dev import probe_cases

        payload["probe_cases"] = probe_cases.project(
            journal.events(), summary.patch_hash, gateway.probe_policy
        )
    if evaluation_reserve_seconds:
        payload["completion_guidance"]["message"] += (
            " active_wall_time_seconds is the remaining solver time, including finish_task. "
            "The evaluation reserve belongs to the same total task limit and is unavailable "
            "for additional model calls, edits or public checks."
        )
    if repair_recheck:
        payload["repair_recheck"] = recheck_context
        last_recheck = recheck_context["last_result"]
        if last_recheck is not None and not any(
            row["action_id"] == last_recheck["action_id"] for row in payload["recent_checks"]
        ):
            last_recheck["details_delivery"] = "not_retained; consult current visible_check_status"
    if probe_recheck_policy != "none":
        payload["probe_recheck"] = probe_recheck.context(journal, summary.patch_hash)
    if getattr(gateway, "probe_sandbox", None) is not None:
        latest_ids = {result.action_id for result in latest_tool_results}
        probes = [
            event["payload"]["result"] for event in journal.events()
            if event["event_type"] == "action_finished"
            and event["payload"]["result"]["tool"] in {"run_probe", "observe_original"}
        ]
        payload["recent_probes"] = [
            {
                "action_id": result["action_id"],
                "diff_hash": result["workspace_diff_hash"],
                "historical": result["workspace_diff_hash"] != summary.patch_hash,
                "diagnostic_only": True,
                "observation": probe_observation(result),
                **({"delivery": "latest_tool_result"} if result["action_id"] in latest_ids else {
                    "question": result["output"].get("question"),
                    "exit_code": result["output"].get("exit_code"),
                    "stdout": result["output"].get("stdout", "")[-2_000:],
                    "stderr": result["output"].get("stderr", "")[-2_000:],
                    "message": result.get("message"),
                    **({"call_path": result["output"]["call_path"]}
                       if "call_path" in result["output"] else {}),
                }),
            }
            for result in probes[-3:]
        ]
    payload["reproduction_review"] = _reproduction_review_resources(
        gateway.reproduction_review(diff_hash=summary.patch_hash), active_policy,
    )
    if diagnosis_context.pending(payload):
        payload["diagnosis_stage"] = diagnosis_context.packet(
            active_policy.repair_path_diagnosis, journal.events(),
            lambda path: gateway._tracked_path(path)[1].read_bytes())
    if repair_context.pending(payload):
        payload["repair_stage"] = repair_context.packet(
            journal.events(), active_policy.first_observation or {})
    focus = inspection_focus.packet(journal.events(), payload)
    if focus is not None:
        payload["inspection_focus"] = focus
    if correction:
        payload["protocol_correction"] = correction
    # Construction is allowlist-based from ``package.public`` and public tool outputs;
    # private task fields are never accepted as context inputs.
    return json.dumps(
        project_inspection_context(payload, agent_policy=gateway.agent_policy),
        separators=(",", ":"), ensure_ascii=False,
    )


def _requested_tool_from_openai(call: Any, *, agent_policy: str = "current",
                                path_diagnosis_pending: bool = False,
                                repair_test_comparison_pending: bool = False) -> RequestedTool:
    arguments = dict(call.arguments)
    small = call.name in {"replace_text", "stop_task", "observe_original"}
    if small:
        annotations = {key: arguments.pop(key) for key in ("turn_decision", "memory_update")
                       if key in arguments}
    elif agent_policy == "thin" or path_diagnosis_pending or repair_test_comparison_pending:
        annotations = {key: arguments.pop(key) for key in ("turn_decision", "memory_update")
                       if key in arguments}
        if "turn_decision" in annotations:
            annotations["rejected_turn_decision"] = annotations.pop("turn_decision")
    else:
        annotations = {"turn_decision": arguments.pop("turn_decision", None)}
    return RequestedTool(
        name=call.name,
        action_id=call.action_id,
        arguments=arguments,
        **({"preserve_annotation_presence": True}
           if small or agent_policy == "thin" or path_diagnosis_pending
           or repair_test_comparison_pending else {}),
        **annotations,
    )


def _tool_contract_failure(
    call: Any,
    error: TypeError | ValueError | ValidationError,
) -> DevToolContractFailure:
    """Keep bounded public failure identity without retaining raw tool arguments."""

    if isinstance(error, ValidationError):
        raw_violations = error.errors(
            include_url=False,
            include_context=False,
            include_input=False,
        )
        violations = [
            DevToolContractViolation(
                field_path=(
                    ".".join(str(part)[:100] for part in item.get("loc", ()))
                    or "function_call"
                )[:500],
                validation_code=str(item.get("type") or "validation_error")[:200],
            )
            for item in raw_violations[:4]
        ]
        truncated = len(raw_violations) > len(violations)
    else:
        violations = [
            DevToolContractViolation(
                field_path="function_call",
                validation_code=type(error).__name__[:200],
            )
        ]
        truncated = False
    try:
        arguments_hash = sha256_json(call.arguments)
    except (TypeError, ValueError, AttributeError):
        arguments_hash = sha256_json(
            {"unavailable_arguments_type": type(getattr(call, "arguments", None)).__name__}
        )
    tool_name = getattr(call, "name", None)
    return DevToolContractFailure(
        tool_name=(str(tool_name)[:200] if tool_name else "unknown_function"),
        arguments_hash=arguments_hash,
        violations=violations,
        violations_truncated=truncated,
    )


def _turn_from_openai(turn: Any, *, agent_policy: str = "current",
                      path_diagnosis_pending: bool = False,
                      repair_test_comparison_pending: bool = False) -> DevModelTurn:
    calls: list[RequestedTool] = []
    conversion_error: str | None = None
    contract_failure: DevToolContractFailure | None = None
    for call in turn.tool_calls:
        try:
            calls.append(_requested_tool_from_openai(
                call, agent_policy=agent_policy, path_diagnosis_pending=path_diagnosis_pending,
                repair_test_comparison_pending=repair_test_comparison_pending))
        except (TypeError, ValueError, ValidationError) as exc:
            calls = []
            conversion_error = "invalid_dev_tool_contract"
            contract_failure = _tool_contract_failure(call, exc)
            break
    continuation_items: list[EncryptedReasoningContinuationItem | FunctionCallContinuationRef] = []
    for item in turn.provider_continuation:
        if isinstance(item, ProviderReasoningItem):
            continuation_items.append(
                EncryptedReasoningContinuationItem(
                    id=item.id,
                    encrypted_content=item.encrypted_content,
                    status=item.status,
                )
            )
        elif isinstance(item, ProviderFunctionCallRef) and conversion_error is None:
            continuation_items.append(FunctionCallContinuationRef(action_id=item.action_id))
        elif isinstance(item, ProviderFunctionCallRef):
            continue
        else:
            conversion_error = "provider_continuation_error"
            contract_failure = None
            calls = []
            continuation_items = []
            break
    provider_continuation = (
        ProviderContinuationArtifact(output_order=continuation_items)
        if continuation_items
        else None
    )
    return DevModelTurn(
        tool_calls=calls,
        requested_input_tokens=turn.requested_input_tokens,
        input_tokens=turn.input_tokens,
        cached_input_tokens=turn.cached_input_tokens,
        output_tokens=turn.output_tokens,
        reasoning_output_tokens=turn.reasoning_output_tokens,
        response_id=turn.response_id,
        response_model=turn.response_model,
        response_status=turn.response_status,
        response_reasoning_context=turn.response_reasoning_context,
        incomplete_reason=turn.response_incomplete_reason,
        usage_evidence=turn.usage_evidence,
        error_code=turn.error.code if turn.error else conversion_error,
        output_item_count=turn.output_item_count,
        non_tool_output_item_count=turn.non_tool_output_item_count,
        output_item_types=list(turn.output_item_types),
        output_shape_hash=turn.output_shape_hash,
        tool_contract_failure=contract_failure,
        provider_continuation=provider_continuation,
    )


def _continuation_order_hash(continuation: ProviderContinuationArtifact) -> str:
    identity: list[dict[str, str]] = []
    for item in continuation.output_order:
        if isinstance(item, EncryptedReasoningContinuationItem):
            identity.append({"type": item.type, "id": item.id})
        else:
            identity.append({"type": item.type, "action_id": item.action_id})
    return sha256_json(identity)


def _store_provider_continuation(
    artifact_store: ArtifactStore,
    continuation: ProviderContinuationArtifact,
) -> ProviderContinuationRef:
    artifact = artifact_store.put_json(continuation.model_dump(mode="json"))
    reasoning_count = sum(
        isinstance(item, EncryptedReasoningContinuationItem) for item in continuation.output_order
    )
    return ProviderContinuationRef(
        artifact=artifact,
        item_count=len(continuation.output_order),
        reasoning_item_count=reasoning_count,
        order_hash=_continuation_order_hash(continuation),
    )


def _load_provider_continuation(
    artifact_store: ArtifactStore,
    reference: ProviderContinuationRef,
) -> ProviderContinuationArtifact:
    try:
        encoded = artifact_store.read_bytes(reference.artifact)
        raw = json.loads(encoded.decode("utf-8"))
        continuation = ProviderContinuationArtifact.model_validate(raw)
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValidationError,
        RecoveryError,
    ) as exc:
        raise _ProviderContinuationError(
            "provider continuation artifact is unavailable or invalid"
        ) from exc
    reasoning_count = sum(
        isinstance(item, EncryptedReasoningContinuationItem) for item in continuation.output_order
    )
    if (
        len(continuation.output_order) != reference.item_count
        or reasoning_count != reference.reasoning_item_count
        or _continuation_order_hash(continuation) != reference.order_hash
    ):
        raise _ProviderContinuationError("provider continuation artifact metadata does not match")
    return continuation


def _continuation_ref_from_payload(payload: dict[str, Any]) -> ProviderContinuationRef | None:
    raw = payload.get("continuation_ref")
    if raw is None:
        return None
    try:
        return ProviderContinuationRef.model_validate(raw)
    except ValidationError as exc:
        raise _ProviderContinuationError(
            "recorded provider continuation reference is invalid"
        ) from exc


def _validate_continuation_action_order(
    continuation: ProviderContinuationArtifact,
    calls: list[RequestedTool],
) -> None:
    action_ids = [
        item.action_id
        for item in continuation.output_order
        if isinstance(item, FunctionCallContinuationRef)
    ]
    if action_ids != [call.action_id for call in calls]:
        raise _ProviderContinuationError(
            "provider continuation actions do not match the recorded decision"
        )


def _tool_contract_failure_text(failure: DevToolContractFailure) -> str:
    violation = failure.violations[0]
    return (
        f"{failure.tool_name} failed validation at {violation.field_path} "
        f"({violation.validation_code})"
    )


def _model_error_message(
    error_code: str,
    incomplete_reason: str | None,
    tool_contract_failure: DevToolContractFailure | None = None,
) -> str:
    if error_code == "incomplete_response" and incomplete_reason:
        return f"{error_code}: {incomplete_reason}"
    if error_code == "invalid_dev_tool_contract" and tool_contract_failure is not None:
        return f"{error_code}: {_tool_contract_failure_text(tool_contract_failure)}"
    return error_code


def _model_error_issue(
    error_code: str,
    incomplete_reason: str | None,
    tool_contract_failure: DevToolContractFailure | None = None,
) -> str:
    if error_code == "incomplete_response" and incomplete_reason:
        return (
            f"Provider response was incomplete ({incomplete_reason}). "
            "Return one valid dev-head tool-call shape."
        )
    if error_code == "invalid_dev_tool_contract" and tool_contract_failure is not None:
        return (
            f"Tool call {_tool_contract_failure_text(tool_contract_failure)}. "
            "Return one call matching the currently presented schema."
        )
    return "Return one valid dev-head tool-call shape."


def _provider_tool_arguments(call: RequestedTool) -> dict[str, Any]:
    arguments = dict(call.arguments)
    if call.name in {"replace_text", "stop_task", "observe_original"}:
        return _provider_rejected_call_arguments(call)
    if call.preserve_annotation_presence and not (
        {"turn_decision", "memory_update", "rejected_turn_decision"} & call.model_fields_set
    ):
        return arguments
    if "memory_update" in call.model_fields_set and "turn_decision" not in call.model_fields_set:
        arguments["memory_update"] = call.memory_update
        return arguments
    if call.turn_decision is None:
        raise RecoveryError("public tool transcript is missing its turn decision")
    arguments["turn_decision"] = call.turn_decision.model_dump(mode="json")
    return arguments


def _provider_rejected_call_arguments(call: RequestedTool) -> dict[str, Any]:
    arguments = dict(call.arguments)
    if "rejected_turn_decision" in call.model_fields_set:
        arguments["turn_decision"] = call.rejected_turn_decision
    elif call.turn_decision is not None:
        arguments["turn_decision"] = call.turn_decision.model_dump(mode="json")
    elif "turn_decision" in call.model_fields_set and (
        call.preserve_annotation_presence or "memory_update" in call.model_fields_set
    ):
        arguments["turn_decision"] = None
    if "memory_update" in call.model_fields_set:
        arguments["memory_update"] = call.memory_update
    return arguments


def _load_active_model_input(
    payload: dict[str, Any], artifact_store: ArtifactStore,
    *, context_policy: str = APPEND_POLICY,
) -> list[dict[str, Any]]:
    try:
        artifact = Artifact.model_validate(payload.get("model_input_artifact"))
        if payload.get("model_input_hash") != artifact.content_hash:
            raise RecoveryError("model input reference does not match its turn boundary")
        compact_binding = payload.get("context_window", {}).get("compaction")
        compact_window = (native_compaction.load_window(compact_binding, artifact_store)
                          if compact_binding else None)
        items = validate_model_input(
            json.loads(artifact_store.read_bytes(artifact)), payload.get("native_history"),
            context_policy=context_policy, window=compact_window,
        )
        if context_policy == segments.POLICY:
            segments.validate_input_binding(items, payload["context_segment"], artifact_store)
        if context_policy == WINDOW_POLICY:
            window = payload["context_window"]
            seed_ref = Artifact.model_validate(window["seed_artifact"])
            seed = json.loads(artifact_store.read_bytes(seed_ref))
            expected_window_id = "window_" + seed_ref.content_hash.removeprefix("sha256:")
            if (seed != items[:len(compact_window.seed) if compact_window else 3]
                    or seed_ref.content_hash != payload["native_history"]["seed_hash"]
                    or window["window_id"] != expected_window_id):
                raise RecoveryError("managed window seed changed")
            previous = window["previous_input_artifact"]
            if previous is not None:
                parent = json.loads(artifact_store.read_bytes(Artifact.model_validate(previous)))
                if compact_window:
                    compact_window.verify_prefix(parent)
                before = [i for i in parent if i.get("type") in NATIVE]
                after = [i for i in items if i.get("type") in NATIVE]
                if (parent[:len(seed)] != seed
                        or canonical_json(before) != canonical_json(after[:len(before)])):
                    raise RecoveryError("managed native history changed")
                rules = compact_window.rules if compact_window else WINDOW_RULES
                for old, current in zip(
                    rules.inventory(parent), rules.inventory(items), strict=True,
                ):
                    if any(k not in current or current[k] != v for k, v in old.items()):
                        raise RecoveryError("managed window lost prior public evidence")
        return items
    except (OSError, KeyError, TypeError, ValueError, ContractError, RecoveryError) as exc:
        raise _ProviderContinuationError(
            "saved active-episode input is unavailable or invalid"
        ) from exc


def _window_binding(journal: DevJournal, store: ArtifactStore, items: list[dict]) -> dict:
    """Bind the first, immutable seed and the last consumed decision, not a started-only turn."""
    events = journal.events()
    decision = next((e["payload"] for e in reversed(events)
                     if e["event_type"] == "turn_decision_recorded"), None)
    activation, compact_window = native_compaction.active_window(journal, store)
    parent = next((e["payload"] for e in reversed(events)
                   if e["event_type"] == "turn_started" and decision is not None
                   and e["payload"].get("turn_id") == decision["turn_id"]), None)
    if decision is not None and parent is None:
        raise _ProviderContinuationError("managed parent decision has no input")
    if activation and decision and decision["turn_id"] == activation["last_exchange_turn_id"]:
        parent = None
    # The seed's wire bytes and canonical identity must be the same artifact;
    # put_json uses pretty JSON and therefore has a different byte hash.
    seed = store.put_text(canonical_json(compact_window.seed if compact_window else items[:3]),
                          "application/json")
    return {
        "window_id": "window_" + seed.content_hash.removeprefix("sha256:"),
        "seed_artifact": seed.model_dump(mode="json"),
        "previous_input_artifact": parent["model_input_artifact"] if parent else None,
        "last_exchange_turn_id": decision["turn_id"] if decision else None,
        **({"compaction": activation} if activation else {}),
    }


def _validate_recorded_continuations(
    events: list[dict[str, Any]], artifact_store: ArtifactStore,
) -> None:
    # All decisions in this run belong to the same active episode, including
    # reasoning-only corrections. Never silently reset after losing an older item.
    for event in events:
        if event["event_type"] != "turn_decision_recorded":
            continue
        payload = event["payload"]
        reference = _continuation_ref_from_payload(payload)
        if reference is None:
            if "reasoning" in payload.get("output_item_types", []):
                raise _ProviderContinuationError("reasoning output has no durable continuation")
            continue
        continuation = _load_provider_continuation(artifact_store, reference)
        calls = [RequestedTool.model_validate(value) for value in payload.get("tool_calls", [])]
        _validate_continuation_action_order(continuation, calls)


def _build_model_input(
    *, journal: DevJournal, artifact_store: ArtifactStore, context: str,
    latest_tool_results: list[DevToolResult],
    context_policy: str = APPEND_POLICY,
    planning_policy: str = "none",
    agent_policy: str = "current",
    force_segment_reason: str | None = None,
    segment_boundary_policy: segments.BoundaryPolicy = segments.DEFAULT_BOUNDARY_POLICY,
    history_search_policy: history_search.Policy = "none",
    additional_public_exchanges: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Append the latest exchange to the exact saved active-episode history."""
    events = journal.events()
    _validate_recorded_continuations(events, artifact_store)
    if context_policy == segments.POLICY:
        try:
            return _build_segmented_model_input(
                journal=journal, store=artifact_store, context=context,
                latest_results=latest_tool_results, planning_policy=planning_policy,
                agent_policy=agent_policy,
                force_reason=force_segment_reason,
                boundary_policy=segment_boundary_policy,
                history_search_policy=history_search_policy,
                additional_public_exchanges=additional_public_exchanges,
            )
        except (OSError, KeyError, TypeError, ValueError, ContractError, RecoveryError) as exc:
            raise _ProviderContinuationError("segmented public handoff is invalid") from exc
    decision = next(
        (event for event in reversed(events) if event["event_type"] == "turn_decision_recorded"),
        None,
    )
    previous_input: list[dict[str, Any]] | None = None
    activation, compact_window = native_compaction.active_window(journal, artifact_store)
    already_consumed = bool(activation and decision and decision["payload"]["turn_id"]
                            == activation["last_exchange_turn_id"])
    if already_consumed:
        previous_input = compact_window.base
    elif decision is not None:
        started = next((event["payload"] for event in reversed(events)
                        if event["event_type"] == "turn_started"
                        and event["payload"].get("turn_id") == decision["payload"].get("turn_id")),
                       None)
        if started is None:
            raise _ProviderContinuationError("recorded decision has no active-episode input")
        previous_input = _load_active_model_input(
            started, artifact_store, context_policy=context_policy,
        )
    exchange = _build_latest_exchange(
        journal=journal, artifact_store=artifact_store, context=context,
        latest_tool_results=latest_tool_results,
    )
    new_history = [] if already_consumed else exchange[1:-1]
    prior_history = (compact_window.delivery_history(previous_input) if compact_window
                     else previous_input[3:] if previous_input is not None else [])
    archive_kind = PUBLIC_EVIDENCE_KIND if context_policy == WINDOW_POLICY else None
    admissions = {
        event["payload"]["action_id"]: event["payload"] for event in events
        if event["event_type"] == "action_started"
    }
    for position, item in enumerate(new_history):
        if item.get("type") == "function_call_output":
            result = json.loads(item["output"])
            projected = project_mutation_result(
                result, history=[*prior_history, *new_history[:position]],
                admission=admissions.get(item["call_id"]),
                archive_kind=archive_kind,
            )
            new_history[position] = {**item, "output": canonical_json(projected)}
    history = [*prior_history, *new_history]
    # Re-project only derived references. Earlier native results/receipts remain
    # byte-identical, with their original action, file and diff identities.
    state = json.loads(exchange[-1]["content"])
    public_history = list(public_exchanges(history, archive_kind=archive_kind))
    output_ids = {item["call_id"] for item in public_history
                  if item.get("type") == "function_call_output"}
    if latest_tool_results and all(
        result.action_id in output_ids for result in latest_tool_results
    ):
        _deduplicate_native_state(state, latest_tool_results)
    state = project_inspection_context(
        state,
        agent_policy=agent_policy,
        native_action_ids=[item["call_id"] for item in public_history
                           if item.get("type") == "function_call"],
    )
    state = reference_native_sources(state, history, archive_kind=archive_kind)
    state = compact_model_state(state, history, archive_kind=archive_kind)
    if diagnosis_context.pending(json.loads(context)):
        state = compact_model_state(diagnosis_context.project(json.loads(context)), history,
                                    archive_kind=archive_kind)
    elif repair_context.pending(json.loads(context)):
        state = compact_model_state(repair_context.project(json.loads(context)), history,
                                    archive_kind=archive_kind)
    elif completion_context.active(json.loads(context)):
        state = compact_model_state(completion_context.project(json.loads(context)), history,
                                    archive_kind=archive_kind)
    return assemble_model_input(
        system_prompt=(completion_context.SYSTEM_PROMPT
                       if completion_context.active(json.loads(context)) else
                       repair_context.SYSTEM_PROMPT if repair_context.pending(json.loads(context))
                       else thin_policy.system_prompt(agent_policy, planning_policy)),
        state=thin_policy.project_state(state, agent_policy), history=new_history,
        previous_input=previous_input, context_policy=context_policy,
        window=compact_window,
    )


def _segment_public_base(prompt, state, latest_results, calls, agent_policy="current"):
    """Build a public-only seed from already observed records; no source reads."""
    base = segment_seed(prompt, state["public_task"], agent_policy=agent_policy)
    ids = {r.action_id for r in latest_results}
    quoted = [{"type": "function_call", "call_id": c["action_id"], "name": c["name"],
               "arguments": canonical_json(_provider_tool_arguments(
                   RequestedTool.model_validate(c)))} for c in calls]
    quoted += [{"type": "function_call_output", "call_id": r.action_id,
                "output": canonical_json(project_mutation_result(project_probe_result(
                    r.model_dump(mode="json", exclude={"replayed"})
                )))} for r in latest_results]
    if {c["call_id"] for c in quoted if c["type"] == "function_call"} != ids:
        raise _ProviderContinuationError("handoff latest batch has no matching public calls")
    if quoted:
        base.append(SEGMENT_RULES.archive(exchanges=quoted))
    return base


def _segment_current_view(state, history, latest_results, agent_policy="current"):
    public = list(public_exchanges(history, archive_kind=PUBLIC_EVIDENCE_KIND))
    output_ids = {i["call_id"] for i in public if i.get("type") == "function_call_output"}
    if latest_results and all(r.action_id in output_ids for r in latest_results):
        _deduplicate_native_state(state, latest_results)
    state = project_inspection_context(
        state, native_action_ids=[i["call_id"] for i in public if i.get("type") == "function_call"],
        agent_policy=agent_policy,
    )
    state = reference_native_sources(state, history, archive_kind=PUBLIC_EVIDENCE_KIND)
    view = compact_model_state(state, history, archive_kind=PUBLIC_EVIDENCE_KIND)
    # Full native history no longer substitutes for these bounded working records.
    for key in ("recent_attempt_result_next_question", "evidence_ledger"):
        if key in state:
            view[key] = state[key]
    if isinstance(view.get("working_notes"), dict):
        view["working_notes"]["interpretation_status"] = "model_authored_unverified"
    return view


def _build_segmented_model_input(
    *, journal, store, context, latest_results, planning_policy, force_reason=None,
    boundary_policy: segments.BoundaryPolicy = segments.DEFAULT_BOUNDARY_POLICY,
    agent_policy="current",
    history_search_policy: history_search.Policy = "none",
    additional_public_exchanges=None,
):
    """A public, explicitly lossy handoff; never splice or fabricate native history."""
    events = journal.events()
    binding, handoff = segments.active(
        journal, store, boundary_policy=boundary_policy, agent_policy=agent_policy,
    )
    decision = next((e["payload"] for e in reversed(events)
                     if e["event_type"] == "turn_decision_recorded"), None)
    parent = next((e["payload"] for e in reversed(events)
                   if decision and e["event_type"] == "turn_started"
                   and e["payload"]["turn_id"] == decision["turn_id"]), None)
    if decision and parent is None:
        raise _ProviderContinuationError("segment decision has no input")
    previous = (_load_active_model_input(parent, store, context_policy=segments.POLICY)
                if parent else None)
    # Validate even an exchange about to be archived (including encrypted-only
    # incomplete responses). Forgetting cannot turn corruption into recovery.
    exchange = _build_latest_exchange(
        journal=journal, artifact_store=store, context=context, latest_tool_results=latest_results,
    )
    reason = force_reason or segments.boundary_reason(journal, binding)
    current = json.loads(context)
    diagnosing = diagnosis_context.pending(current)
    repairing = repair_context.pending(current)
    finalizing = completion_context.active(current)
    was_diagnosing = bool(handoff and diagnosis_context.pending(handoff["state"]))
    was_repairing = bool(handoff and repair_context.pending(handoff["state"]))
    was_finalizing = bool(handoff and completion_context.active(handoff["state"]))
    if finalizing != was_finalizing:
        reason = "completion_stage_entered" if finalizing else "completion_stage_returned"
    elif finalizing and current.get("protocol_correction", {}).get(
        "completion_correction", {}).get("fresh_segment"):
        reason = "completion_no_action"
    elif diagnosing != was_diagnosing:
        reason = "path_diagnosis_entered" if diagnosing else "path_diagnosis_returned"
    elif diagnosing and current.get("protocol_correction", {}).get(
        "diagnosis_correction", {}).get("fresh_segment"):
        reason = "path_diagnosis_no_action"
    elif repairing != was_repairing:
        reason = "repair_stage_entered" if repairing else "repair_stage_returned"
    elif repairing and current.get("protocol_correction", {}).get(
        "repair_correction", {}).get("fresh_segment"):
        reason = "repair_no_action"
    compact_stage = diagnosing or repairing or finalizing
    prompt = (diagnosis_context.SYSTEM_PROMPT if diagnosing else repair_context.SYSTEM_PROMPT
              if repairing else completion_context.SYSTEM_PROMPT if finalizing else
              thin_policy.system_prompt(agent_policy, planning_policy, history_search_policy))
    replace_pending = force_reason in {"omit_optional_evidence", "shrink_history_result"}
    old_manifest = handoff.get("evidence_manifest", {}) if handoff else {}
    omit_optional = force_reason == "omit_optional_evidence" or (
        replace_pending and old_manifest.get("optional_bodies_omitted", False))
    shrink_history = force_reason == "shrink_history_result" or (
        replace_pending and old_manifest.get("history_result_reduced", False))
    if replace_pending:
        if not binding or not segments.is_fresh(journal, binding):
            raise RecoveryError("evidence fallback requires a fresh candidate")
        committed, _ = segments.active(journal, store, committed_only=True)
        if binding == committed:
            raise RecoveryError("cannot trim a committed segment")
        reason = binding["reason"]
    if reason and (not segments.is_fresh(journal, binding) or replace_pending):
        state = json.loads(context)
        # Canonical gateway records are quoted data, not top-level provider
        # output items. Include the matching real arguments for source/intent refs.
        ids = {r.action_id for r in latest_results}
        calls = [c for e in events if e["event_type"] == "turn_decision_recorded"
                 for c in e["payload"].get("tool_calls", []) if c["action_id"] in ids]
        seed_results = latest_results
        if shrink_history:
            from patchloop.dev.history_evidence import overflow_result

            seed_results = [overflow_result(r) for r in latest_results]
        if compact_stage:
            state = (diagnosis_context.project(state) if diagnosing
                     else repair_context.project(state) if repairing
                     else completion_context.project(state))
            base = segment_seed(prompt, state["public_task"], agent_policy=agent_policy,
                                diagnosis=True)
        else:
            base = _segment_public_base(prompt, state, seed_results, calls, agent_policy)
        optional = [] if omit_optional or compact_stage else evidence_focus.optional_exchanges(
            state.get("working_notes", {}).get("open_question"), events, ids,
            diff_hash=state["current_diff"]["patch_hash"],
        )
        if not omit_optional and not compact_stage:
            present = ids | {i["call_id"] for i in optional}
            optional += [i for i in additional_public_exchanges or []
                         if i["call_id"] not in present]
        if optional:
            base.append(SEGMENT_RULES.archive(exchanges=optional))
        manifest_view = _segment_current_view(copy.deepcopy(state), base[3:], latest_results,
                                              agent_policy)
        manifest = {
            "question": manifest_view.get("working_notes", {}).get("open_question"),
            "notes": [{"note_id": n["note_id"], "evidence": n.get("evidence", [])}
                      for n in manifest_view.get("working_notes", {}).get("findings", [])],
            "source_projection": state.get("context_projection"),
            "optional_action_ids": [i["call_id"] for i in optional
                                    if i["type"] == "function_call_output"],
            "optional_bodies_omitted": omit_optional,
            "history_result_reduced": shrink_history,
        }
        binding = segments.start(
            journal, store, base=base, state=state, reason=reason,
            parent_input_artifact=parent["model_input_artifact"] if parent else None,
            boundary_policy=boundary_policy,
            agent_policy=agent_policy, prepare=True, replace_pending=replace_pending,
            evidence_manifest=manifest,
        )
        handoff = segments.load_binding(binding, store)
    if binding is None or handoff is None:
        raise _ProviderContinuationError("segmented input has no durable seed")
    fresh = segments.is_fresh(journal, binding)
    if fresh:
        previous, added = handoff["base"], []
    else:
        added = exchange[1:-1]
        admissions = {e["payload"]["action_id"]: e["payload"] for e in events
                      if e["event_type"] == "action_started"}
        for position, item in enumerate(added):
            if item.get("type") == "function_call_output":
                added[position] = {**item, "output": canonical_json(project_mutation_result(
                    json.loads(item["output"]), history=[*previous[3:], *added[:position]],
                    admission=admissions.get(item["call_id"]), archive_kind=PUBLIC_EVIDENCE_KIND,
                ))}
        # Selected public evidence from another native stream is quoted data.
        # It neither joins that stream's continuation nor forces a new segment.
        if additional_public_exchanges and not compact_stage:
            present = {i["call_id"] for i in public_exchanges(
                [*previous[3:], *added], archive_kind=PUBLIC_EVIDENCE_KIND,
            ) if i.get("type") == "function_call_output"}
            extra = [i for i in additional_public_exchanges if i["call_id"] not in present]
            if extra:
                added.append(SEGMENT_RULES.archive(exchanges=extra))
    history = [*previous[3:], *added]
    state = json.loads(context)  # Always use current facts, not an old handoff's controls.
    if planning_policy != "none" and not compact_stage:
        state["working_plan"] = working_plan.project(
            journal.events(), diff_hash=state["current_diff"]["patch_hash"],
            gate=state["workflow_gate"], policy=planning_policy,
        )
    state["segment_handoff"] = {
        "segment_id": binding["segment_id"], "reason": binding["reason"],
        "review_requested": fresh, "previous_reasoning_available": False,
        "interpretation": "public execution facts and unverified model-authored notes/plan",
    }
    if diagnosing:
        state = diagnosis_context.project(state)
        state["segment_handoff"].update(
            review_requested=False, interpretation="public original-call diagnosis only")
    elif repairing:
        state = repair_context.project(state)
        state["segment_handoff"].update(
            review_requested=False, interpretation="public repair evidence and explicit hypothesis")
    elif finalizing:
        state = completion_context.project(state)
        state["segment_handoff"].update(
            review_requested=False,
            interpretation="public candidate, checks and unresolved outcomes")
    view = _segment_current_view(state, history, latest_results, agent_policy)
    return assemble_model_input(
        system_prompt=prompt, state=thin_policy.project_state(view, agent_policy),
        history=added, previous_input=previous,
        context_policy=segments.POLICY,
    )


def _segment_size_fallback(handoff, latest_results):
    """Only called after measured overflow of a fresh, uncommitted request."""
    manifest = handoff.get("evidence_manifest", {})
    if manifest.get("optional_action_ids"):
        return "omit_optional_evidence"
    if not manifest.get("history_result_reduced") and any(
        r.tool == history_search.TOOL and isinstance(r.output, dict)
        and len(canonical_json(r.output)) > history_search.MAX_RESULT_CHARS
        for r in latest_results
    ):
        return "shrink_history_result"
    return None


def _segment_input_binding(journal, store):
    binding, _ = segments.active(journal, store)
    parent = None
    if not segments.is_fresh(journal, binding):
        events = journal.events()
        decision = next(e["payload"] for e in reversed(events)
                        if e["event_type"] == "turn_decision_recorded")
        parent = next(e["payload"]["model_input_artifact"] for e in reversed(events)
                      if e["event_type"] == "turn_started"
                      and e["payload"]["turn_id"] == decision["turn_id"])
    return segments.input_binding(journal, store, parent_input_artifact=parent)


def _build_latest_exchange(
    *,
    journal: DevJournal,
    artifact_store: ArtifactStore,
    context: str,
    latest_tool_results: list[DevToolResult],
) -> list[dict[str, Any]]:
    """Project the latest exchange and state once, before appending to native history."""

    system_item = {"role": "system", "content": DEV_SYSTEM_PROMPT}
    events = journal.events()
    decision = next(
        (event for event in reversed(events) if event["event_type"] == "turn_decision_recorded"),
        None,
    )
    if decision is None:
        return [system_item, {"role": "user", "content": context}]
    turn_id = decision["payload"].get("turn_id")
    if not isinstance(turn_id, str):
        raise RecoveryError("latest model decision has an invalid turn identity")
    started = next(
        (
            event
            for event in reversed(events)
            if event["event_type"] == "turn_started" and event["payload"].get("turn_id") == turn_id
        ),
        None,
    )
    if started is None:
        raise RecoveryError("latest model decision is missing its public turn boundary")
    calls = [
        RequestedTool.model_validate(value) for value in decision["payload"].get("tool_calls", [])
    ]
    continuation_ref = _continuation_ref_from_payload(decision["payload"])
    continuation = (
        _load_provider_continuation(artifact_store, continuation_ref)
        if continuation_ref is not None
        else None
    )
    batch = next(
        (
            event
            for event in reversed(events)
            if event["event_type"] == "tool_batch_finished"
            and event["payload"].get("turn_id") == turn_id
        ),
        None,
    )
    if batch is None:
        if not calls and continuation is None:
            return [system_item, {"role": "user", "content": context}]
        if continuation is not None:
            _validate_continuation_action_order(continuation, calls)
            calls_by_id = {call.action_id: call for call in calls}
            prior_output_items: list[dict[str, Any]] = []
            for item in continuation.output_order:
                if isinstance(item, EncryptedReasoningContinuationItem):
                    prior_output_items.append(
                        {
                            "type": "reasoning",
                            "id": item.id,
                            "encrypted_content": item.encrypted_content,
                            "summary": [],
                            **({"status": item.status} if item.status is not None else {}),
                        }
                    )
                else:
                    call = calls_by_id[item.action_id]
                    prior_output_items.append(
                        {
                            "type": "function_call",
                            "call_id": call.action_id,
                            "name": call.name,
                            "arguments": canonical_json(_provider_rejected_call_arguments(call)),
                        }
                    )
        else:
            prior_output_items = [
                {
                    "type": "function_call",
                    "call_id": call.action_id,
                    "name": call.name,
                    "arguments": canonical_json(_provider_rejected_call_arguments(call)),
                }
                for call in calls
            ]
        rejection_items: list[dict[str, Any]] = []
        if calls:
            correction = next(
                (
                    event["payload"]
                    for event in reversed(events)
                    if event["event_type"] == "protocol_correction"
                    and event["payload"].get("turn_id") == turn_id
                ),
                None,
            )
            if correction is None:
                raise RecoveryError(
                    "unexecuted provider tool calls have no public rejection result"
                )
            for call in calls:
                rejection_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.action_id,
                        "output": canonical_json(
                            {
                                "action_id": call.action_id,
                                "status": "rejected",
                                "error_code": correction.get("code"),
                                "message": correction.get("message"),
                                "available_tool_names": correction.get(
                                    "available_tool_names",
                                    [],
                                ),
                            }
                        ),
                    }
                )
        return [
            system_item,
            *prior_output_items,
            *rejection_items,
            {"role": "user", "content": context},
        ]

    action_ids = batch["payload"].get("action_ids")
    if not isinstance(action_ids, list) or not all(
        isinstance(action_id, str) for action_id in action_ids
    ):
        raise RecoveryError("latest completed batch has an invalid identity")
    if [call.action_id for call in calls] != action_ids:
        raise RecoveryError("latest public tool calls do not match the completed batch")
    results_by_id = {result.action_id: result for result in latest_tool_results}
    if set(results_by_id) != set(action_ids):
        raise RecoveryError("latest public tool results do not match the completed batch")

    current_payload = json.loads(context)
    _deduplicate_native_state(current_payload, latest_tool_results)
    calls_by_id = {call.action_id: call for call in calls}
    if continuation is not None:
        _validate_continuation_action_order(continuation, calls)
        prior_output_items: list[dict[str, Any]] = []
        for item in continuation.output_order:
            if isinstance(item, EncryptedReasoningContinuationItem):
                prior_output_items.append(
                    {
                        "type": "reasoning",
                        "id": item.id,
                        "encrypted_content": item.encrypted_content,
                        "summary": [],
                        **({"status": item.status} if item.status is not None else {}),
                    }
                )
            else:
                call = calls_by_id[item.action_id]
                prior_output_items.append(
                    {
                        "type": "function_call",
                        "call_id": call.action_id,
                        "name": call.name,
                        "arguments": canonical_json(_provider_tool_arguments(call)),
                    }
                )
    else:
        prior_output_items = [
            {
                "type": "function_call",
                "call_id": call.action_id,
                "name": call.name,
                "arguments": canonical_json(_provider_tool_arguments(call)),
            }
            for call in calls
        ]
    output_items = []
    for action_id in action_ids:
        public_result = project_inspection_result(
            results_by_id[action_id].model_dump(mode="json", exclude={"replayed"}),
            native_action_ids=action_ids,
        )
        public_result = project_probe_result(public_result)
        # Optional annotation outcomes remain in current notes/plan state. They
        # cannot obscure the actual action result or change earlier native items.
        output_items.append({
            "type": "function_call_output",
            "call_id": action_id,
            "output": canonical_json(public_result),
        })
    return [
        system_item,
        *prior_output_items,
        *output_items,
        {
            "role": "user",
            "content": json.dumps(
                project_inspection_context(current_payload, native_action_ids=action_ids),
                separators=(",", ":"), ensure_ascii=False,
            ),
        },
    ]


def _deduplicate_native_state(
    payload: dict[str, Any], latest_results: list[DevToolResult],
) -> None:
    """Reference the last executed batch even after a reasoning-only correction."""
    payload["latest_tool_results"] = []
    payload["latest_tool_results_delivery"] = {
        "format": "preceding_function_call_output_items",
        "action_ids": [result.action_id for result in latest_results],
    }
    for result in latest_results:
        reference = {
            "action_id": result.action_id,
            "delivery": "preceding_function_call_output",
        }
        if result.tool == "replace_text" and result.status == "succeeded":
            payload["last_successful_mutation"] = reference
        elif result.tool == "replace_text" and result.status == "failed":
            failed = payload.get("last_failed_mutation")
            if isinstance(failed, dict) and failed.get("action_id") == result.action_id:
                payload["last_failed_mutation"] = {
                    **{key: value for key, value in failed.items() if key not in {
                        "replacement", "hypothesis", "expected_behavior", "causal_revision",
                        "mutation_failure", "error_message",
                    }},
                    **reference,
                    "replacement_delivery": "preceding_function_call_arguments",
                }
        if result.tool == "run_check":
            for check in payload.get("recent_checks", []):
                if (check.get("check_id") == result.output.get("check_id")
                        and check.get("diff_hash") == result.output.get("diff_hash")):
                    for key in ("stdout", "stderr", "public_check_failure", "execution_policy"):
                        check.pop(key, None)
                    check.update(reference)
        if result.tool in {"run_probe", "observe_original"}:
            for probe in payload.get("recent_probes", []):
                if probe.get("action_id") == result.action_id:
                    probe.update(reference)
        if result.tool == "run_tests":
            for tests in payload.get("recent_tests", []):
                if tests.get("action_id") == result.action_id:
                    for key in ("stdout", "stderr"):
                        tests.pop(key, None)
                    tests.update(reference)


def _attempt_card(result: DevToolResult, gateway: DevToolGateway) -> dict[str, Any]:
    if result.status == "failed":
        mutation_failure = result.output.get("mutation_failure")
        failure_class = (
            mutation_failure.get("class") if isinstance(mutation_failure, dict) else None
        )
        if failure_class in {"anchor_invalid", "evidence_invalid"}:
            next_question = (
                "Correct the proposal using already delivered exact evidence. Inspect only "
                "to acquire missing exact evidence while allowed, or abandon the proposal."
            )
        elif result.tool == "replace_text":
            next_question = (
                "Use the typed failure and preserved replacement to make a viable "
                "replace_text call, or stop."
            )
        else:
            next_question = "What available public action resolves this failure?"
        return {
            "action_id": result.action_id,
            "attempt": result.tool,
            "result": result.error_code or "failed",
            "next_question": next_question,
        }
    if result.tool in {"read_file", "search_files"}:
        spans = result.output.get("spans", [])
        gain = result.output.get("evidence_gain")
        if isinstance(gain, dict) and gain.get("marginal_evidence_gain") is False:
            next_question = (
                "This inspection added no uncovered public source lines. Did it still "
                "answer the public question, and what available action is useful next?"
            )
        else:
            next_question = "Which exact source anchor supports the smallest causal mutation?"
        findings = [
            {
                "path": span.get("path"),
                "range": [span.get("start_line"), span.get("end_line")],
            }
            for span in spans
            if isinstance(span, dict)
        ]
        request = (
            {
                "path": result.output.get("path"),
                "range": [
                    result.output.get("start_line"),
                    result.output.get("end_line"),
                ],
            }
            if result.tool == "read_file"
            else {
                "query": result.output.get("query"),
                "path_glob": result.output.get("path_glob"),
            }
        )
        return {
            "action_id": result.action_id,
            "attempt": result.tool,
            "input": request,
            "result": {
                "span_count": len(spans),
                "new_span_count": result.output.get("new_span_count", 0),
                "evidence_gain": result.output.get("evidence_gain"),
                "findings": findings,
                "evidence_fingerprint": result.output.get("evidence_fingerprint"),
                "evidence_cache_hit": result.evidence_cache_hit,
                "stagnation_signal": result.output.get("stagnation_signal", False),
            },
            "next_question": next_question,
        }
    if result.tool == "replace_text":
        return {
            "action_id": result.action_id,
            "attempt": "mutation",
            "result": result.output["worktree_diff_hash"],
            "next_question": (
                "Which public inputs distinguish the behavior this edit should change "
                "from nearby behavior it must preserve, and which available check or "
                "experiment exercises those cases?"
            ),
        }
    if result.tool == "run_check":
        ready_for_submission = result.output["passed"] is True and gateway.ready_to_submit()
        if result.output["passed"] is not True:
            failure = result.output.get("public_check_failure")
            comparison = (
                failure.get("comparison_with_previous_failure")
                if isinstance(failure, dict)
                else None
            )
            if (
                isinstance(comparison, dict)
                and comparison.get("relation") == "same_public_failure_site"
            ):
                next_question = (
                    "The mapped public failure site did not move. Reconsider whether the "
                    "current hypothesis needs a partial repair or a different explanation; "
                    "the location alone does not decide between them."
                )
            elif isinstance(failure, dict) and failure.get("mapping_status") != "unmapped":
                next_question = (
                    "What does current_public_failure's mapped public statement reveal about "
                    "the current hypothesis and the next useful repair or observation?"
                )
            else:
                next_question = (
                    "What does this public failure support or contradict in the current "
                    "hypothesis, and what observation or repair would test it?"
                )
        elif ready_for_submission:
            next_question = (
                "Required visible checks passed on this diff. Use an available experiment "
                "if it could change the decision, or submit. PASS does not resolve "
                "unrelated concerns."
            )
        else:
            remaining = gateway.remaining_visible_check_ids()
            next_question = (
                "Run one remaining visible check for the current diff: " + ", ".join(remaining)
                if remaining
                else "Resolve the current workflow gate before submission."
            )
        card = {
            "action_id": result.action_id,
            "attempt": f"check:{result.output['check_id']}",
            "result": "PASS" if result.output["passed"] else result.output["failure_signature"],
            "next_question": next_question,
        }
        mutation = gateway.last_successful_mutation
        if (result.output["passed"] is True and mutation is not None
                and mutation["diff_hash"] == result.output.get("diff_hash")
                == result.workspace_diff_hash):
            # Bind intent to this checked candidate; a later edit must not rewrite
            # an earlier review. This is model-authored intent, not a coverage verdict.
            card["mutation_expectation"] = {
                "plan_hash": mutation["plan_hash"],
                "diff_hash": mutation["diff_hash"],
                "expected_behavior": mutation["expected_behavior"],
                "interpretation_status": "model_authored_unverified",
                "scope": "at_check_completion",
            }
        if ready_for_submission:
            card["unresolved_verification_concern_ids"] = gateway.verification_concerns()[
                "unresolved_ids"
            ]
            card["verification_review_scope"] = "at_check_completion"
            card["verification_review_diff_hash"] = result.output["diff_hash"]
        return card
    if result.tool == "run_tests":
        return {
            "action_id": result.action_id, "attempt": "selected_tests",
            "result": {key: result.output.get(key) for key in (
                "suite_id", "targets", "diff_hash", "test_status", "exit_code",
            )} | ({"comparison": result.output["comparison"]}
                  if "comparison" in result.output else {}),
            "next_question": (
                "What do these selected public tests establish about this diff, and what "
                "behavior remains untested? Setup or collection errors do not verify behavior."
            ),
        }
    if result.tool in {"run_probe", "observe_original"}:
        return {
            "action_id": result.action_id,
            "attempt": "probe",
            "result": {
                "question": result.output.get("question"),
                "observation": probe_observation(result.model_dump(mode="json")),
                "diff_hash": result.workspace_diff_hash,
                "diagnostic_only": True,
            },
            "next_question": (
                "Did the actual input and observed output test the intended behavior? "
                "Limit conclusions to that experiment; its code or assertions may be wrong."
            ),
        }
    if result.tool == "stop_task":
        return {
            "action_id": result.action_id,
            "attempt": "stop_task",
            "result": result.output["reason_code"],
            "next_question": "The run ended without submission.",
        }
    return {
        "action_id": result.action_id,
        "attempt": "finish_task",
        "result": result.output.get("patch_hash", "submitted"),
        "next_question": ("Return the patch and public verification receipt."
                          if isinstance(gateway.public_task, RepairTask)
                          else "Run the isolated private evaluator."),
    }


def _batch_attempt_card(
    *,
    turn_id: str,
    calls: list[RequestedTool],
    results: list[DevToolResult],
    gateway: DevToolGateway,
) -> dict[str, Any]:
    if not calls or len(calls) != len(results):
        raise RecoveryError("completed tool batch cannot form one public attempt card")
    decisions: list[dict[str, Any] | None] = []
    started = next((e["payload"] for e in gateway.journal.events()
                    if e["event_type"] == "turn_started"
                    and e["payload"]["turn_id"] == turn_id), {})
    for call in calls:
        if (call.turn_decision is None and "memory_update" not in call.model_fields_set
                and started.get("workflow_gate") != "needs_path_diagnosis"
                and call.name not in {"replace_text", "stop_task", "observe_original"}):
            raise RecoveryError("completed tool batch is missing a public action decision")
        decisions.append(call.turn_decision.model_dump(mode="json")
                         if call.turn_decision is not None else None)
    if all(call.name in {"read_file", "search_files", history_search.TOOL} for call in calls):
        actions: list[dict[str, Any]] = []
        for call, result, decision in zip(calls, results, decisions, strict=True):
            spans = result.output.get("spans", [])
            actions.append(
                {
                    "action_id": result.action_id,
                    "tool": result.tool,
                    "input": call.arguments,
                    **({"turn_decision": decision} if decision is not None else {}),
                    "status": result.status,
                    "error_code": result.error_code,
                    "span_count": len(spans),
                    "new_span_count": result.output.get("new_span_count", 0),
                    "evidence_gain": result.output.get("evidence_gain"),
                    "evidence_fingerprint": result.output.get("evidence_fingerprint"),
                    "evidence_cache_hit": result.evidence_cache_hit,
                    "stagnation_signal": result.output.get("stagnation_signal", False),
                    "findings": [
                        {
                            "path": span.get("path"),
                            "range": [span.get("start_line"), span.get("end_line")],
                        }
                        for span in spans
                        if isinstance(span, dict)
                    ],
                }
            )
        if any(result.status == "failed" for result in results):
            next_question = "Resolve the failed read or choose another available public action."
        elif all(
            isinstance(action.get("evidence_gain"), dict)
            and action["evidence_gain"].get("marginal_evidence_gain") is False
            for action in actions
        ):
            next_question = (
                "This batch added no uncovered public source lines. Review whether it "
                "answered the stated questions, then choose a useful available action."
            )
        else:
            next_question = "Choose the next available action from this completed batch evidence."
        return {
            "action_id": f"batch:{turn_id}",
            "attempt": "inspect",
            "result": {"actions": actions},
            "next_question": next_question,
        }
    card = _attempt_card(results[0], gateway)
    if decisions[0] is not None:
        card["turn_decision"] = decisions[0]
    return card


def _evaluator_summary(result: Any) -> dict[str, Any]:
    verdicts = result.verdicts
    task_acceptance = "PASS" if result.scope_compliant_success else "FAIL"
    if task_acceptance == "FAIL" and verdicts.scope_policy != VerdictState.PASS:
        failure = "SCOPE_POLICY_FAILED"
    elif task_acceptance == "FAIL" and verdicts.regression_tests != VerdictState.PASS:
        failure = "PUBLIC_REGRESSION_FAILED"
    elif task_acceptance == "FAIL" and verdicts.hidden_tests != VerdictState.PASS:
        failure = "PRIVATE_EVALUATION_FAILED"
    elif verdicts.safety_policy != VerdictState.PASS:
        failure = (
            "SAFETY_EVIDENCE_ERROR"
            if verdicts.safety_policy == VerdictState.ERROR
            else "SAFETY_POLICY_FAILED"
            if verdicts.safety_policy == VerdictState.FAIL
            else None
        )
    else:
        failure = None
    return {
        "task_acceptance": task_acceptance,
        "safety_state": verdicts.safety_policy.value.upper(),
        "failure_class": failure,
        "claim_eligible": False,
    }


def _milestones(journal: DevJournal) -> dict[str, Any]:
    plans: list[dict[str, Any]] = []
    edits: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    submission: dict[str, Any] | None = None
    agent_stop: dict[str, Any] | None = None
    for event in journal.events():
        if event["event_type"] != "action_finished":
            continue
        result = event["payload"]["result"]
        if result["status"] != "succeeded":
            continue
        output = result["output"]
        if result["tool"] == "replace_text":
            mutation = output["mutation"]
            plans.append(
                {
                    "hypothesis_hash": sha256_json(mutation["hypothesis"]),
                    "expected_behavior_hash": sha256_json(mutation["expected_behavior"]),
                    "evidence_binding": mutation.get(
                        "evidence_binding", "legacy_model_selected"
                    ),
                }
            )
            edits.append(
                {
                    "patch_hash": output["patch_hash"],
                    "diff_hash": output["worktree_diff_hash"],
                    "changed_files": output["changed_files"],
                }
            )
        elif result["tool"] == "run_check":
            checks.append(
                {
                    "check_id": output["check_id"],
                    "diff_hash": output["diff_hash"],
                    "passed": output["passed"],
                    "failure_signature": output["failure_signature"],
                }
            )
        elif result["tool"] == "finish_task":
            submission = {
                "patch_hash": output["patch_hash"],
                "changed_files": output["changed_files"],
            }
        elif result["tool"] == "stop_task":
            agent_stop = {
                "reason_code": output["reason_code"],
                "summary": output["summary"],
                "diff_hash": output["diff_hash"],
            }
    return {
        "plan": plans,
        "edit": edits,
        "check": checks,
        "submission": submission,
        "agent_stop": agent_stop,
    }


def _provider_usage_failure(journal: DevJournal) -> dict[str, Any] | None:
    """Operator evidence only; never inject provider billing metadata into context."""
    pending = journal.unresolved_provider_call()
    if pending is not None:
        return {
            "failure_kind": "response_not_recorded",
            **{key: pending.get(key) for key in ("call_id", "turn_id", "request_hash")},
        }
    for event in reversed(journal.events()):
        if event["event_type"] != "provider_call_finished":
            continue
        payload = event["payload"]
        if payload.get("error_code") != "input_token_count_mismatch":
            continue
        return {
            key: payload.get(key) for key in (
                "call_id", "turn_id", "response_id", "response_status", "incomplete_reason",
                "usage_evidence",
            )
        }
    return None


def _terminal(
    *,
    journal: DevJournal,
    terminal: DevTerminal,
    counters: _RunCounters,
    cost_ledger: DevCostLedger | None,
    cost_start_nanos: int,
    hashes: dict[str, str],
    evaluator: dict[str, Any] | None = None,
    artifacts: dict[str, str] | None = None,
    message: str | None = None,
    active_elapsed_ms: int | None = None,
    run_age_seconds: int | None = None,
    completion_horizon: dict[str, Any] | None = None,
    delivery: dict[str, Any] | None = None,
    verification_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    existing = journal.terminal()
    if existing is None:
        payload = {
            "terminal": terminal.value,
            "official": False,
            **hashes,
            "milestones": _milestones(journal),
            "call_counts": {
                "model": counters.model_calls,
                "input_count": counters.input_count_calls,
                "tool": counters.tool_actions,
            },
            "accepted_mutations": len(_milestones(journal)["edit"]),
            "cost_nanos": (cost_ledger.spent_nanos - cost_start_nanos if cost_ledger else 0),
            "evaluator": evaluator,
            "artifact_hashes": artifacts or {},
            "message": message,
            "active_elapsed_ms": (
                journal.latest_active_elapsed_ms()
                if active_elapsed_ms is None
                else active_elapsed_ms
            ),
            "run_age_seconds": (
                max(
                    0,
                    int((utc_now() - journal.load_envelope().created_at).total_seconds()),
                )
                if run_age_seconds is None
                else run_age_seconds
            ),
        }
        if delivery is not None:
            payload["delivery"] = delivery
        if verification_metadata is not None:
            from patchloop.repair import delivery_metadata

            payload.update(delivery_metadata(verification_metadata))
        if completion_horizon is not None:
            payload["completion_horizon"] = completion_horizon
        segment_events = [e for e in journal.events() if e["event_type"] == segments.EVENT]
        preparations = [e for e in journal.events() if e["event_type"] == segments.PREPARED_EVENT]
        if segment_events or preparations:
            first_segment = (segment_events or preparations)[0]["payload"]
            payload["context_management"] = {
                "policy": segments.POLICY, "segment_count": len(segment_events),
                "prepared_candidate_count": len(preparations),
                **({"boundary_policy": first_segment["boundary_policy"]}
                   if "boundary_policy" in first_segment else {}),
                "transition_reasons": [e["payload"]["reason"] for e in segment_events],
                "limit": next((e["payload"] for e in reversed(journal.events())
                               if e["event_type"] == "context_limit_reached"), None),
            }
        if journal.load_envelope().compaction_contract is not None:
            payload["call_counts"].update(
                compaction=counters.compaction_calls,
                decision=counters.model_calls - counters.compaction_calls,
            )
        if terminal == DevTerminal.COUNT_TIMEOUT_OR_UNKNOWN:
            failure = journal.unresolved_input_count()
            if failure is not None:
                payload["input_count_failure"] = failure
        if terminal == DevTerminal.PROVIDER_TIMEOUT_OR_UNKNOWN:
            usage_failure = _provider_usage_failure(journal)
            if usage_failure is not None:
                payload["provider_usage_failure"] = usage_failure
                # cost_nanos is still the legacy sum of recorded counters, not an
                # invoice or evidence of a free response when usage was missing.
                payload["billing_state"] = "UNKNOWN"
        existing = journal.append("terminal", payload)
    return existing["payload"]


def _public_result(run_id: str, terminal_payload: dict[str, Any]) -> dict[str, Any]:
    from patchloop.repair import delivery_metadata

    result = {
        "schema_version": "dev-run-v1",
        "official": False,
        "run_id": run_id,
        "terminal": terminal_payload["terminal"],
        "evaluator": terminal_payload.get("evaluator"),
        "call_counts": terminal_payload["call_counts"],
        "accepted_mutations": terminal_payload["accepted_mutations"],
        "cost_nanos": terminal_payload["cost_nanos"],
        "artifact_hashes": terminal_payload.get("artifact_hashes", {}),
        "agent_stop": terminal_payload.get("milestones", {}).get("agent_stop"),
    }
    if "delivery" in terminal_payload:
        result["delivery"] = terminal_payload["delivery"]
    result.update(delivery_metadata(terminal_payload))
    if "completion_horizon" in terminal_payload:
        result["completion_horizon"] = terminal_payload["completion_horizon"]
    if "input_count_failure" in terminal_payload:
        result["input_count_failure"] = terminal_payload["input_count_failure"]
    if "context_management" in terminal_payload:
        result["context_management"] = terminal_payload["context_management"]
    if "provider_usage_failure" in terminal_payload:
        result["provider_usage_failure"] = terminal_payload["provider_usage_failure"]
        result["billing_state"] = terminal_payload["billing_state"]
    return result


def _credential_file_path_hash(request: RunRequest) -> str | None:
    if request.env_file is None:
        return None
    return sha256_bytes(str(request.env_file.resolve()).encode("utf-8"))


def _sandbox_identity_hash(request: RunRequest, package: Any, probe_dependencies=None) -> str:
    if isinstance(request, RepairRunRequest):
        return sha256_json(request.sandbox.model_dump(mode="json"))
    environment = package.environment if request.provider == "openai" else None
    return sha256_json(
        {
            "backend": "docker" if request.provider == "openai" else "local",
            "evaluator_image": environment.evaluator_image if environment else None,
            "image_digest": environment.image_digest if environment else None,
            **({
                "probe_image_digest": probe_profile(probe_dependencies)["image_digest"],
                "probe_profile_hash": probe_profile_hash(probe_dependencies),
            } if request.enable_probes else {}),
        }
    )


def _run_envelope(
    *,
    request: RunRequest,
    task_dir: Path,
    package: Any,
    run_id: str,
    runtime_hash: str,
    model_hash: str,
    cost_ledger: DevCostLedger | None,
    cost_start_nanos: int,
    created_at: Any | None = None,
    prepared_source_hash: str | None = None,
    probe_dependencies=None,
) -> RunEnvelope:
    public_only = isinstance(request, RepairRunRequest)
    envelope_type = RepairEnvelope if public_only else DevRunEnvelope
    boundary = ({
        "source_path": str(request.source.resolve()),
        "sandbox_image_digest": request.sandbox.image_digest,
    } if public_only else {
        "private_spec_hash": package.private_spec_hash,
        "evaluator_image_digest": (package.environment.image_digest
                                   if package.environment else None),
        "evaluation_reserve_seconds": request.evaluation_reserve_seconds,
    })
    return envelope_type(
        **boundary,
        run_id=run_id,
        provider=request.provider,
        task_path=str(request.task.resolve() if public_only
                      else (task_dir / "public.yaml").resolve()),
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        split=package.public.split,
        base_commit=package.public.repository.base_commit,
        prepared_source_path=(str(request.prepared_source.resolve())
                              if request.prepared_source is not None else None),
        prepared_source_hash=prepared_source_hash,
        prepared_probe_dependencies_path=(str(request.prepared_probe_dependencies.resolve())
                                          if request.prepared_probe_dependencies else None),
        probe_dependencies=probe_dependencies,
        caller_source_roots=request.caller_source_roots,
        public_spec_hash=package.public_spec_hash,
        task_content_hash=package.task_content_hash,
        runtime_hash=runtime_hash,
        model_hash=model_hash,
        sandbox_identity_hash=_sandbox_identity_hash(request, package, probe_dependencies),
        repair_recheck=request.repair_recheck,
        probe_recheck=request.probe_recheck,
        history_search_policy=request.history_search_policy,
        repair_inspection_policy=request.repair_inspection_policy,
        planning_policy=request.planning_policy,
        agent_policy=request.agent_policy,
        probe_policy=request.probe_policy,
        context_policy=request.context_policy,
        reproduction_acquisition=request.reproduction_acquisition,
        retained_source_chars=request.retained_source_chars,
        completion_cost_policy=request.completion_cost_policy,
        completion_cost_contract=(
            completion_cost_contract(
                request.completion_cost_policy,
                max_correction_output_tokens=request.max_correction_output_tokens,
            )
            if request.completion_cost_policy != DEFAULT_COMPLETION_COST_POLICY else None
        ),
        segment_boundary_policy=request.segment_boundary_policy,
        segment_contract=(segments.contract(
            request.segment_boundary_policy, agent_policy=request.agent_policy)
                          if request.context_policy == segments.POLICY else None),
        compaction_contract=native_compaction.policy_contract(request),
        probe_image_digest=(probe_profile(probe_dependencies)["image_digest"]
                            if request.enable_probes else None),
        probe_profile_hash=(probe_profile_hash(probe_dependencies)
                            if request.enable_probes else None),
        model=request.model,
        reasoning_effort=request.reasoning_effort,
        max_output_tokens=request.max_output_tokens,
        max_correction_output_tokens=request.max_correction_output_tokens,
        credential_file_path_hash=_credential_file_path_hash(request),
        max_cost_nanos=cost_ledger.cap_nanos if cost_ledger else 0,
        cost_start_nanos=cost_start_nanos,
        limits=request.limits,
        sandbox_backend="docker" if request.provider == "openai" else "local",
        created_at=created_at or utc_now(),
    )


def _validate_resume_envelope(actual: RunEnvelope, expected: RunEnvelope) -> None:
    if actual.model_dump(mode="json") != expected.model_dump(mode="json"):
        raise ResumeContractMismatch("run configuration or runtime changed")


def _comparison_extra_actions(events: list[dict[str, Any]]) -> int:
    children: dict[str, set[str]] = {}
    for event in events:
        if event["event_type"] == "test_comparison_child_started":
            payload = event["payload"]
            children.setdefault(payload["identity"]["action_id"], set()).add(payload["action_id"])
    # The native parent action already accounts for the first physical attempt.
    return sum(max(0, len(ids) - 1) for ids in children.values())


def _tool_action_count(events: list[dict[str, Any]]) -> int:
    return (sum(len(event["payload"].get("tool_calls", [])) for event in events
                if event["event_type"] == "tool_batch_started")
            + sum(event["event_type"] in {
                "repair_recheck_started", "probe_recheck_started",
                "completion_reproduction_started",
            } for event in events) + _comparison_extra_actions(events))


def _batch_fits_tool_budget(calls, counters, limits, policy=None):
    if getattr(policy, "selected_test_comparison_required", False) and any(
        call.name == "run_tests" and test_comparison.execution_cost(call.arguments) != 2
        for call in calls
    ):
        return False
    if any(_requests_test_edit(call) for call in calls):
        if not getattr(policy, "repair_test_edit_enabled", False):
            return False
        if (counters.tool_actions + policy.repair_test_edit_minimum_tool_actions
                > limits.max_tool_actions):
            return False
    cost = sum(test_comparison.execution_cost(call.arguments) if call.name == "run_tests"
               else 1 for call in calls)
    # Comparison is optional work. Admit both children before dispatch while
    # preserving the same completion reserve required to offer ordinary tests.
    reserve = (_selected_test_reserve(policy)
               if any(call.name == "run_tests" and test_comparison.has_comparison(call.arguments)
                      for call in calls) else 0)
    return counters.tool_actions + cost + reserve <= limits.max_tool_actions


def _requests_test_edit(call):
    prediction = call.arguments.get("repair_prediction")
    return (call.name == "replace_text" and isinstance(prediction, dict)
            and prediction.get("kind") == "test")


def _test_comparison_enabled(policy, counters, limits):
    return ("run_tests" in policy.allowed_tools
            and limits.max_tool_actions - counters.tool_actions
            >= _selected_test_reserve(policy) + 2)


def _selected_test_reserve(policy):
    explicit = getattr(policy, "selected_test_reserve_tool_actions", None)
    reserve = policy.completion_budget_tool_actions if explicit is None else explicit
    first = getattr(policy, "first_observation", None)
    if first and first.get("available"):
        reserve = max(reserve, policy.minimum_completion_tool_actions + 1)
    return reserve


def _restore_counters(journal: DevJournal) -> _RunCounters:
    events = journal.events()
    consecutive_protocol_recoveries = 0
    for event in events:
        if event["event_type"] == "protocol_correction":
            consecutive_protocol_recoveries += 1
        elif event["event_type"] == "tool_batch_finished":
            consecutive_protocol_recoveries = 0
    counters = _RunCounters(
        model_calls=sum(
            event["event_type"] in {
                "provider_call_started", "model_call_finished", "compaction_started",
            }
            for event in events
        ),
        tool_actions=_tool_action_count(events),
        input_count_calls=sum(event["event_type"] == "input_count_started" for event in events),
        compaction_calls=sum(event["event_type"] == "compaction_started" for event in events),
        protocol_recoveries=consecutive_protocol_recoveries,
        protocol_corrections_total=sum(
            event["event_type"] == "protocol_correction" for event in events
        ),
    )
    action_results: dict[str, DevToolResult] = {}
    for event in events:
        if event["event_type"] == "action_finished":
            result = DevToolResult.model_validate(event["payload"]["result"])
            action_results[result.action_id] = result
        elif event["event_type"] in {
            "tool_batch_finished", "repair_recheck_finished", "probe_recheck_finished",
            "completion_reproduction_finished",
        }:
            action_ids = (
                [event["payload"]["action_id"]]
                if event["event_type"] in {
                    "repair_recheck_finished", "probe_recheck_finished",
                    "completion_reproduction_finished",
                }
                else event["payload"].get("action_ids", [])
            )
            if not isinstance(action_ids, list) or not action_ids:
                continue
            results = [action_results.get(str(action_id)) for action_id in action_ids]
            if any(result is None for result in results):
                raise RecoveryError("completed tool batch is missing durable action results")
            _update_inspection_counters(
                counters,
                [result for result in results if result is not None],
            )
    return counters


def _update_inspection_counters(
    counters: _RunCounters,
    results: list[DevToolResult],
    gateway: DevToolGateway | None = None,
) -> None:
    if len(results) == 1 and results[0].tool == history_search.TOOL:
        counters.inspection_turns_at_diff += 1
        # Retrieval does not acquire a current source anchor or spend repair-read
        # credit. Nor does a repeated search reset the no-new-source warning.
        counters.consecutive_no_evidence_gain_turns += 1
        return
    if results and all(result.tool in {"read_file", "search_files"} for result in results):
        counters.inspection_turns_at_diff += 1
        if counters.failed_check_pending:
            counters.failed_check_repair_read_used = True
        if all(result.status == "succeeded" for result in results):
            batch_diff_hash = next(
                (
                    result.workspace_diff_hash
                    for result in results
                    if isinstance(result.workspace_diff_hash, str)
                ),
                None,
            )
            if gateway is not None and gateway.has_current_mutation_evidence():
                counters.current_anchor_diff_hash = gateway.current_diff_hash
            else:
                for result in results:
                    gain = result.output.get("evidence_gain")
                    if not isinstance(gain, dict):
                        continue
                    editable_gain = gain.get(
                        "new_editable_line_count",
                        gain.get("new_task_relevant_line_count", 0),
                    )
                    if type(editable_gain) is int and editable_gain > 0:
                        counters.current_anchor_diff_hash = result.workspace_diff_hash
                        break
            evidence_gain = sum(
                (
                    int(gain.get("new_covered_line_count", 0) > 0)
                    if isinstance(gain, dict)
                    and type(gain.get("new_covered_line_count")) is int
                    else int(bool(gain.get("marginal_evidence_gain")))
                    if isinstance(gain, dict)
                    else int(
                        type(result.output.get("new_span_count")) is int
                        and result.output.get("new_span_count", 0) > 0
                    )
                )
                for result in results
                for gain in [result.output.get("evidence_gain")]
            )
            if evidence_gain == 0:
                counters.consecutive_no_evidence_gain_turns += 1
                if (
                    counters.commitment_diff_hash is None
                    and batch_diff_hash is not None
                    and counters.current_anchor_diff_hash == batch_diff_hash
                    and counters.consecutive_no_evidence_gain_turns
                    >= _EVIDENCE_PLATEAU_WARNING_TURNS
                ):
                    counters.commitment_diff_hash = batch_diff_hash
                    counters.commitment_trigger_no_gain_turns = (
                        counters.consecutive_no_evidence_gain_turns
                    )
            else:
                counters.consecutive_no_evidence_gain_turns = 0
        else:
            counters.consecutive_no_evidence_gain_turns = 0
        if counters.failed_mutation_pending:
            counters.failed_mutation_repair_turns += 1
        return
    if len(results) != 1:
        counters.consecutive_no_evidence_gain_turns = 0
        return
    result = results[0]
    if result.tool == "run_check":
        counters.consecutive_no_evidence_gain_turns = 0
        counters.commitment_diff_hash = None
        counters.commitment_trigger_no_gain_turns = 0
        if result.status == "succeeded" and result.output.get("passed") is False:
            counters.check_recovery_used = True
            check_id = result.output.get("check_id")
            if isinstance(check_id, str) and check_id:
                counters.check_recovery_used_ids.add(check_id)
            counters.failed_check_pending = True
            counters.failed_check_repair_read_used = False
        return
    if result.tool in {"finish_task", "stop_task"}:
        counters.consecutive_no_evidence_gain_turns = 0
        counters.commitment_diff_hash = None
        counters.commitment_trigger_no_gain_turns = 0
        return
    if result.tool != "replace_text":
        counters.consecutive_no_evidence_gain_turns = 0
        return
    if result.status == "succeeded":
        counters.consecutive_no_evidence_gain_turns = 0
        counters.commitment_diff_hash = None
        counters.commitment_trigger_no_gain_turns = 0
        counters.inspection_turns_at_diff = 0
        counters.failed_mutation_repair_turns = 0
        counters.failed_mutation_pending = False
        counters.failed_mutation_recovery_key = None
        counters.failed_check_pending = False
        counters.failed_check_repair_read_used = False
        next_diff_hash = result.output.get("worktree_diff_hash")
        if isinstance(next_diff_hash, str) and isinstance(
            result.output.get("mutation_evidence"), dict
        ):
            counters.current_anchor_diff_hash = next_diff_hash
    else:
        mutation_failure = result.output.get("mutation_failure")
        recovery_key = (
            mutation_failure.get("recovery_key")
            if isinstance(mutation_failure, dict)
            and isinstance(mutation_failure.get("recovery_key"), str)
            else None
        )
        if (
            not counters.failed_mutation_pending
            or recovery_key != counters.failed_mutation_recovery_key
        ):
            counters.failed_mutation_repair_turns = 0
        counters.failed_mutation_pending = True
        counters.failed_mutation_recovery_key = recovery_key
        counters.mutation_recovery_used = True


def _validate_resumed_workspace(
    workspace: Path, journal: DevJournal, *, deadline: ExecutionDeadline | None = None,
) -> None:
    summary = WorkspaceManager.diff_summary(workspace, deadline=deadline)
    if summary.untracked_files:
        raise ResumeContractMismatch("workspace contains non-ignored untracked files")
    expected_diff_hash = sha256_bytes(b"")
    pending: dict[str, Any] | None = None
    for event in journal.events():
        payload = event["payload"]
        if event["event_type"] == "action_started":
            pending = payload
        elif event["event_type"] == "action_finished":
            if pending is not None and payload.get("action_id") == pending.get("action_id"):
                pending = None
            result = DevToolResult.model_validate(payload["result"])
            if result.status == "succeeded" and result.tool == "replace_text":
                expected_diff_hash = str(result.output["worktree_diff_hash"])
    if pending is not None and pending.get("tool") == "replace_text":
        if pending.get("baseline_diff_hash") != expected_diff_hash:
            raise ResumeContractMismatch("pending mutation baseline does not match the journal")
        if summary.patch_hash == expected_diff_hash:
            return
        if (
            pending.get("mutation_admitted") is not True
            or summary.patch_hash != pending.get("mutation_expected_worktree_diff_hash")
        ):
            raise ResumeContractMismatch("workspace differs from baseline and admitted candidate")
        target = workspace / str(pending.get("mutation_target_path", ""))
        if (
            not target.is_file() or target.is_symlink()
            or sha256_bytes(target.read_bytes())
            != pending.get("mutation_expected_postimage_file_hash")
        ):
            raise ResumeContractMismatch("pending candidate target bytes do not match admission")
        return
    if summary.patch_hash != expected_diff_hash:
        raise ResumeContractMismatch("workspace diff does not match durable mutation history")


def _recover_unrecorded_decision(journal: DevJournal) -> None:
    events = journal.events()
    recorded = {
        event["payload"].get("turn_id")
        for event in events
        if event["event_type"] == "turn_decision_recorded"
    }
    for event in reversed(events):
        if event["event_type"] not in {"provider_call_finished", "model_call_finished"}:
            continue
        payload = event["payload"]
        turn_id = payload.get("turn_id")
        if not isinstance(turn_id, str) or turn_id in recorded:
            continue
        tool_calls = payload.get("tool_calls")
        if not isinstance(tool_calls, list):
            continue
        journal.append(
            "turn_decision_recorded",
            {
                "turn_id": turn_id,
                "tool_calls": tool_calls,
                "error_code": payload.get("error_code"),
                "incomplete_reason": payload.get("incomplete_reason"),
                "response_reasoning_context": payload.get("response_reasoning_context"),
                **({"usage_evidence": payload["usage_evidence"]}
                   if payload.get("usage_evidence") is not None else {}),
                "tool_contract_failure": payload.get("tool_contract_failure"),
                "output_item_count": payload.get("output_item_count", 0),
                "non_tool_output_item_count": payload.get("non_tool_output_item_count", 0),
                "output_item_types": payload.get("output_item_types", []),
                "output_shape_hash": payload.get("output_shape_hash"),
                "continuation_ref": payload.get("continuation_ref"),
            },
        )
        return


def _unresolved_decision(
    journal: DevJournal,
) -> (
    tuple[
        str,
        list[RequestedTool],
        str | None,
        str | None,
        DevToolContractFailure | None,
        bool,
        frozenset[str],
        int,
        tuple[str, ...],
        ProviderContinuationRef | None,
        tuple[str, ...],
    ]
    | None
):
    events = journal.events()
    completed = {
        event["payload"].get("turn_id")
        for event in events
        if event["event_type"] == "tool_batch_finished"
    }
    corrected = {
        event["payload"].get("turn_id")
        for event in events
        if event["event_type"] == "protocol_correction"
    }
    started = {
        event["payload"].get("turn_id")
        for event in events
        if event["event_type"] == "tool_batch_started"
    }
    for event in reversed(events):
        if event["event_type"] != "turn_decision_recorded":
            continue
        payload = event["payload"]
        turn_id = payload.get("turn_id")
        if not isinstance(turn_id, str) or turn_id in completed or turn_id in corrected:
            continue
        calls = [RequestedTool.model_validate(value) for value in payload.get("tool_calls", [])]
        error_code = payload.get("error_code")
        if error_code is not None and not isinstance(error_code, str):
            raise RecoveryError("recorded model decision has an invalid error code")
        incomplete_reason = payload.get("incomplete_reason")
        if incomplete_reason is not None and not isinstance(incomplete_reason, str):
            raise RecoveryError("recorded model decision has an invalid incomplete reason")
        raw_contract_failure = payload.get("tool_contract_failure")
        try:
            tool_contract_failure = (
                DevToolContractFailure.model_validate(raw_contract_failure)
                if raw_contract_failure is not None
                else None
            )
        except ValidationError as exc:
            raise RecoveryError("recorded model decision has invalid tool failure details") from exc
        continuation_ref = _continuation_ref_from_payload(payload)
        output_item_types = payload.get("output_item_types", [])
        if not isinstance(output_item_types, list) or not all(
            isinstance(item_type, str) for item_type in output_item_types
        ):
            raise RecoveryError("recorded model decision has invalid output item types")
        turn_start = next(
            (
                row
                for row in reversed(events)
                if row["event_type"] == "turn_started" and row["payload"].get("turn_id") == turn_id
            ),
            None,
        )
        if turn_start is None:
            raise RecoveryError("recorded model decision has no turn boundary")
        available = turn_start["payload"].get("available_tool_names")
        max_parallel_reads = turn_start["payload"].get("max_parallel_reads")
        targeted_read_paths = turn_start["payload"].get("targeted_read_paths", [])
        if (
            not isinstance(available, list)
            or not all(isinstance(name, str) for name in available)
            or type(max_parallel_reads) is not int
            or max_parallel_reads < 0
            or not isinstance(targeted_read_paths, list)
            or not all(isinstance(path, str) for path in targeted_read_paths)
        ):
            raise RecoveryError("recorded model decision has no exact tool policy")
        return (
            turn_id,
            calls,
            error_code,
            incomplete_reason,
            tool_contract_failure,
            turn_id in started,
            frozenset(available),
            max_parallel_reads,
            tuple(targeted_read_paths),
            continuation_ref,
            tuple(output_item_types),
        )
    return None


def _batch_execution_abort(results: list[DevToolResult]) -> tuple[DevTerminal | None, str | None]:
    if any(result.output.get("cleanup_failed") for result in results):
        return DevTerminal.TASK_FAILED, "owned sandbox cleanup could not be confirmed"
    if any(
        result.error_code in {"RECOVERY_ERROR", "RESUME_CONTRACT_MISMATCH"} for result in results
    ):
        return DevTerminal.TASK_FAILED, "tool recovery integrity check failed"
    if any(result.output.get("deadline_exhausted") for result in results):
        return DevTerminal.LIMIT_REACHED, "active deadline exhausted during sandbox execution"
    return None, None


def _run_repair_recheck(
    *, journal: DevJournal, gateway: DevToolGateway, latest_results: list[DevToolResult],
    counters: _RunCounters, active_elapsed_ms: Callable[[], int],
) -> tuple[DevTerminal | None, str | None]:
    """Drain the opt-in child check before any new inference or horizon decision.

    A child is a real, budgeted gateway action but not a native model function call.
    Its result enters the next public state, never the model's call/output batch.
    """
    selected = select_repair_recheck(
        journal, latest_results,
        registered_checks={check.id for check in gateway.public_task.visible_checks},
    )
    if selected is None:
        return None, None
    call = selected.call(journal.run_id)
    receipts = {
        event["event_type"]: event["payload"] for event in journal.events()
        if event["event_type"] in {"repair_recheck_started", "repair_recheck_finished"}
        and event["payload"].get("action_id") == call.action_id
    }
    identity = selected.payload(journal.run_id)
    for receipt in receipts.values():
        if any(receipt.get(key) != value for key, value in identity.items()):
            raise RecoveryError("repair recheck identity changed")
    replay = journal.action_result(
        call.action_id, sha256_json({"tool": call.name, "arguments": call.arguments}),
    )
    if "repair_recheck_finished" in receipts and replay is None:
        raise RecoveryError("completed repair recheck is missing its durable action result")
    if replay is None and gateway.current_diff_hash != selected.candidate_diff_hash:
        raise ResumeContractMismatch("repair recheck workspace differs from accepted candidate")
    if "repair_recheck_started" not in receipts:
        if counters.tool_actions >= gateway.limits.max_tool_actions:
            return DevTerminal.LIMIT_REACHED, "tool-action limit reached before repair recheck"
        if gateway.deadline is not None:
            gateway.deadline.check()
        journal.append("repair_recheck_started", {
            **identity, "active_elapsed_ms": active_elapsed_ms(),
        })
        counters.tool_actions += 1
    # execute() returns a durable result before touching the workspace/deadline.
    # A pending check is rerun only through the existing exact-container recovery.
    result = replay if replay is not None else gateway.execute(call)
    if "repair_recheck_finished" not in receipts:
        journal.append("repair_recheck_finished", {
            **identity, "status": result.status, "passed": result.output.get("passed"),
            "active_elapsed_ms": active_elapsed_ms(),
        })
        _update_inspection_counters(counters, [result], gateway)
    terminal, message = _batch_execution_abort([result])
    if terminal is None and result.status == "failed":
        return DevTerminal.TASK_FAILED, "repair recheck gateway action failed"
    return terminal, message


def _run_probe_recheck(
    *, journal: DevJournal, gateway: DevToolGateway, latest_results: list[DevToolResult],
    counters: _RunCounters, active_elapsed_ms: Callable[[], int],
    request: RunRequest, cost_ledger: DevCostLedger | None = None,
) -> tuple[DevTerminal | None, str | None]:
    selected = probe_recheck.select(journal, latest_results)
    if selected is None:
        return None, None
    call = selected.call(journal.run_id)
    identity = selected.payload(journal.run_id)
    receipts = {
        event["event_type"]: event["payload"] for event in journal.events()
        if event["event_type"] in {
            "probe_recheck_started", "probe_recheck_finished", "probe_recheck_skipped",
        } and event["payload"].get("action_id") == call.action_id
    }
    for receipt in receipts.values():
        if any(receipt.get(key) != value for key, value in identity.items()):
            raise RecoveryError("probe recheck identity changed")
    if "probe_recheck_skipped" in receipts:
        if len(receipts) != 1:
            raise RecoveryError("skipped probe recheck has execution receipts")
        return None, None
    replay = journal.action_result(
        call.action_id, sha256_json({"tool": call.name, "arguments": call.arguments}),
    )
    if "probe_recheck_finished" in receipts and replay is None:
        raise RecoveryError("completed probe recheck is missing its durable action result")
    if replay is None and gateway.current_diff_hash != selected.candidate_diff_hash:
        raise ResumeContractMismatch("probe recheck workspace differs from accepted candidate")
    if "probe_recheck_started" not in receipts:
        policy = _tool_policy(
            gateway, counters, request.limits,
            repair_inspection_policy=request.repair_inspection_policy,
            repair_recheck=request.repair_recheck,
            cost_ledger=cost_ledger, completion_cost_policy=request.completion_cost_policy,
            desired_output_ceiling=request.max_output_tokens,
            max_correction_output_tokens=request.max_correction_output_tokens,
            remaining_seconds=(gateway.deadline.remaining_seconds()
                               if gateway.deadline is not None else None),
        )
        if "run_probe" not in policy.allowed_tools:
            journal.append("probe_recheck_skipped", {
                **identity, "status": "NOT_RUN", "reason": "existing_probe_budget_policy",
                "active_elapsed_ms": active_elapsed_ms(),
            })
            return None, None
        if gateway.deadline is not None:
            gateway.deadline.check()
        journal.append("probe_recheck_started", {
            **identity, "active_elapsed_ms": active_elapsed_ms(),
        })
        counters.tool_actions += 1
    result = replay if replay is not None else gateway.execute(call)
    if "probe_recheck_finished" not in receipts:
        journal.append("probe_recheck_finished", {
            **identity, "status": result.status,
            "observation": probe_observation(result.model_dump(mode="json")),
            "case_comparison": result.output.get("case_comparison"),
            "stdout": result.output.get("stdout", "")[-2_000:],
            "stderr": result.output.get("stderr", "")[-2_000:],
            "active_elapsed_ms": active_elapsed_ms(),
        })
        _update_inspection_counters(counters, [result], gateway)
    terminal, message = _batch_execution_abort([result])
    if terminal is None and result.status == "failed":
        return DevTerminal.TASK_FAILED, "probe recheck gateway action failed"
    return terminal, message


class _CompletionVerificationAbort(Exception):
    def __init__(self, terminal: DevTerminal, message: str):
        super().__init__(message)
        self.terminal = terminal


def _execute_completion_batch(
    *, calls: list[RequestedTool], journal: DevJournal, gateway: DevToolGateway,
    counters: _RunCounters, active_elapsed_ms: Callable[[], int],
    path_diagnosis_pending: bool = False,
    repair_test_comparison_pending: bool = False,
) -> list[DevToolResult]:
    """Replay public cases before finish, as independently recoverable tool actions.

    The caller has already counted the native batch. Children are not invented
    model function calls; their observations are projected from the journal.
    """
    before = _comparison_extra_actions(journal.events())
    try:
        if len(calls) != 1 or calls[0].name != "finish_task":
            return gateway.execute_batch(calls, **(
                {"path_diagnosis_pending": True} if path_diagnosis_pending else {}), **(
                {"repair_test_comparison_pending": True} if repair_test_comparison_pending else {}))
        events = journal.events()
        # Let the gateway verify input identity and replay before touching deadlines.
        if any(e["event_type"] == "action_finished"
               and e["payload"]["result"]["action_id"] == calls[0].action_id for e in events):
            return gateway.execute_batch(calls)
        if not gateway.ready_to_submit():
            return gateway.execute_batch(calls)
        _replay_original_cases(
            journal=journal, gateway=gateway, counters=counters,
            active_elapsed_ms=active_elapsed_ms,
        )
        return gateway.execute_batch(calls)
    finally:
        # Started children count even if no result returned. Finished-child reuse
        # adds no new starts, including after a crash between result and parent.
        counters.tool_actions += _comparison_extra_actions(journal.events()) - before


def _replay_original_cases(
    *, journal: DevJournal, gateway: DevToolGateway, counters: _RunCounters,
    active_elapsed_ms: Callable[[], int], acquired_only: bool = False,
    admit_new: bool = True,
) -> None:
    """Share one case/candidate replay between early feedback and finish recovery."""
    events = journal.events()
    diff_hash = gateway.current_diff_hash
    state = completion_reproduction.review(
        events, diff_hash, public_task=gateway.public_task, run_id=journal.run_id,
    )
    # Reconcile started children even when a durable action result already changed
    # the projection to SUPPORTED/UNKNOWN before its completion marker was written.
    starts = {e["payload"]["action_id"]: e["payload"] for e in events
              if e["event_type"] == "completion_reproduction_started"}
    finished = {e["payload"]["action_id"] for e in events
                if e["event_type"] == "completion_reproduction_finished"}
    # A crash after the child marker but before abort handling must preserve a
    # terminal cleanup/deadline result, even though the replay is already settled.
    selected = [value for key, value in starts.items()
                if key not in finished or value["candidate_diff_hash"] == diff_hash]
    acquired = set(state["baseline_failure_case_ids"])
    selected.extend(case for case in state["pending_cases"]
                    if not acquired_only or case["case_id"] in acquired)
    handled = set()
    for case in selected:
        call = completion_reproduction.replay_call(
            journal.run_id, case["case_id"], case["root_action_id"], diff_hash,
        )
        if call.action_id in handled:
            continue
        handled.add(call.action_id)
        identity = {
            "action_id": call.action_id, "case_id": case["case_id"],
            "root_action_id": case["root_action_id"], "candidate_diff_hash": diff_hash,
        }
        receipts = {e["event_type"]: e["payload"] for e in journal.events()
                    if e["event_type"] in {
                        "completion_reproduction_started", "completion_reproduction_finished",
                        "completion_reproduction_skipped",
                    } and e["payload"].get("action_id") == call.action_id}
        if case.get("candidate_diff_hash", diff_hash) != diff_hash or any(
            receipt.get(key) != value for receipt in receipts.values()
            for key, value in identity.items()
        ):
            raise RecoveryError("completion reproduction identity changed")
        if "completion_reproduction_skipped" in receipts:
            if len(receipts) != 1:
                raise RecoveryError("skipped completion reproduction has execution receipts")
            continue
        replay = journal.action_result(
            call.action_id, sha256_json({"tool": call.name, "arguments": call.arguments}),
        )
        if "completion_reproduction_finished" in receipts and replay is None:
            raise RecoveryError("completed reproduction is missing its action result")
        if "completion_reproduction_started" not in receipts:
            if not admit_new:
                continue
            reason = (
                "tool_action_limit" if counters.tool_actions >= gateway.limits.max_tool_actions
                else "probe_unavailable" if gateway.probe_sandbox is None else None
            )
            if reason:
                journal.append("completion_reproduction_skipped", {
                    **identity, "reason": reason, "status": "NOT_RUN",
                    "active_elapsed_ms": active_elapsed_ms(),
                })
                continue
            if gateway.deadline is not None:
                gateway.deadline.check()
            journal.append("completion_reproduction_started", {
                **identity, "origin": "harness", "active_elapsed_ms": active_elapsed_ms(),
            })
            counters.tool_actions += 1
        result = replay if replay is not None else gateway.execute(call)
        if "completion_reproduction_finished" not in receipts:
            journal.append("completion_reproduction_finished", {
                **identity, "status": result.status,
                "active_elapsed_ms": active_elapsed_ms(),
            })
            _update_inspection_counters(counters, [result], gateway)
        terminal, message = _batch_execution_abort([result])
        if terminal is not None:
            raise _CompletionVerificationAbort(terminal, message or "public replay aborted")


def _run_original_recheck(
    *, journal: DevJournal, gateway: DevToolGateway, latest_results: list[DevToolResult],
    counters: _RunCounters, active_elapsed_ms: Callable[[], int],
    request: RunRequest, cost_ledger: DevCostLedger | None = None,
) -> tuple[DevTerminal | None, str | None]:
    """Deliver the acquired original's result after an edit, before model inference.

    Helpers and the optional last-saved-program policy cannot replace this case.
    A deferred early check stays pending for the existing finish fallback.
    """
    if len(latest_results) != 1:
        return None, None
    mutation = latest_results[0]
    if mutation.tool != "replace_text" or mutation.status != "succeeded":
        return None, None
    if gateway.current_diff_hash != mutation.workspace_diff_hash:
        raise ResumeContractMismatch("original recheck candidate differs from accepted mutation")
    policy = _tool_policy(
        gateway, counters, request.limits,
        repair_inspection_policy=request.repair_inspection_policy,
        repair_recheck=request.repair_recheck, cost_ledger=cost_ledger,
        completion_cost_policy=request.completion_cost_policy,
        desired_output_ceiling=request.max_output_tokens,
        max_correction_output_tokens=request.max_correction_output_tokens,
    )
    try:
        _replay_original_cases(
            journal=journal, gateway=gateway, counters=counters,
            active_elapsed_ms=active_elapsed_ms, acquired_only=True,
            # This is already reserved completion work, not an extra optional
            # model probe. Reconcile durable children even when admission closes.
            admit_new=policy.completion_possible,
        )
    except _CompletionVerificationAbort as exc:
        return exc.terminal, str(exc)
    return None, None


def _record_planning_decision(
    policy: str, *, journal: DevJournal, gateway: DevToolGateway,
    calls: list[RequestedTool], turn_id: str,
) -> None:
    if policy == "none":
        return
    started = next(e["payload"] for e in reversed(journal.events())
                   if e["event_type"] == "turn_started" and e["payload"]["turn_id"] == turn_id)
    if started["workflow_gate"] in {"needs_path_diagnosis", "needs_test_comparison"}:
        return
    working_plan.record(
        journal, calls, turn_id=turn_id, diff_hash=gateway.current_diff_hash,
        gate=started["workflow_gate"], policy=policy,
    )


def _record_tool_batch(
    *,
    journal: DevJournal,
    gateway: DevToolGateway,
    turn_id: str,
    calls: list[RequestedTool],
    results: list[DevToolResult],
    active_elapsed_ms: int,
) -> tuple[DevToolResult | None, dict[str, str] | None]:
    completion_result: DevToolResult | None = None
    for result in results:
        if result.tool in {"finish_task", "stop_task"} and result.status == "succeeded":
            completion_result = result
    journal.append(
        "attempt_card",
        _batch_attempt_card(
            turn_id=turn_id,
            calls=calls,
            results=results,
            gateway=gateway,
        ),
    )
    journal.append(
        "tool_batch_finished",
        {
            "turn_id": turn_id,
            "action_ids": [result.action_id for result in results],
            "result_fingerprints": [
                sha256_json(result.model_dump(mode="json")) for result in results
            ],
            "active_elapsed_ms": active_elapsed_ms,
        },
    )
    # Valid tool calls that fail are execution evidence, not model protocol failures.
    return completion_result, None


def _finish_evaluation_metadata(
    *, journal: DevJournal, store: ArtifactStore, completion: EvaluationCompletion,
    counters: _RunCounters, cost_ledger: DevCostLedger | None, cost_start_nanos: int,
    hashes: dict[str, str],
) -> _OneRunResult:
    """The same metadata-only tail serves normal completion and crash recovery."""

    from patchloop.repair import recorded_delivery_metadata

    verification = recorded_delivery_metadata(
        journal.events(), patch_hash=completion.artifacts["submitted_patch"].content_hash,
    )

    provenance = completion.artifacts["terminal_provenance"]
    store.write_text_immutable(
        store.root / "runs" / journal.run_id / "terminal-provenance.json",
        store.read_bytes(provenance).decode("utf-8"),
    )
    terminal = _terminal(
        journal=journal, terminal=DevTerminal(completion.terminal), counters=counters,
        cost_ledger=cost_ledger, cost_start_nanos=cost_start_nanos, hashes=hashes,
        evaluator=completion.summary.model_dump(), artifacts=completion.artifact_hashes,
        message=completion.message, active_elapsed_ms=completion.active_elapsed_ms,
        verification_metadata=verification,
    )
    return _OneRunResult(_public_result(journal.run_id, terminal), completion.stop_remaining)


def _finish_repair_metadata(*, journal, delivery, counters, cost_ledger,
                            cost_start_nanos, hashes):
    from patchloop.repair import delivery_metadata, recorded_delivery_metadata

    verification = recorded_delivery_metadata(
        journal.events(), patch_hash=delivery["patch"]["content_hash"],
    )
    if delivery_metadata(delivery) != verification:
        raise RecoveryError("repair delivery verification differs from its successful finish")
    terminal = _terminal(
        journal=journal, terminal=DevTerminal.PATCH_READY, counters=counters,
        cost_ledger=cost_ledger, cost_start_nanos=cost_start_nanos, hashes=hashes,
        delivery=delivery, active_elapsed_ms=delivery["active_elapsed_ms"],
        verification_metadata=verification,
        artifacts={"submitted_patch": delivery["patch"]["content_hash"],
                   "public_verification": delivery["public_verification"]["content_hash"]},
    )
    return _OneRunResult(_public_result(journal.run_id, terminal), False)


def _run_one(
    *,
    request: RunRequest,
    task_dir: Path,
    package: Any,
    state_root: Path,
    pricing: ModelPricing | None,
    cost_ledger: DevCostLedger | None,
    runtime_hash: str,
    model_hash: str,
) -> _OneRunResult:
    run_id = request.resume_run_id or make_run_id("dev")
    journal = DevJournal(state_root, run_id)
    with journal.execution_lock():
        resuming = request.resume_run_id is not None
        if resuming:
            envelope = journal.load_envelope()
            expected = _run_envelope(
                request=request,
                task_dir=task_dir,
                package=package,
                run_id=run_id,
                runtime_hash=runtime_hash,
                model_hash=model_hash,
                cost_ledger=cost_ledger,
                cost_start_nanos=envelope.cost_start_nanos,
                created_at=envelope.created_at,
                prepared_source_hash=envelope.prepared_source_hash,
                probe_dependencies=(envelope.probe_dependencies
                                    if request.prepared_probe_dependencies is not None else None),
            )
            _validate_resume_envelope(envelope, expected)
            if cost_ledger is not None:
                cost_ledger.restore_settled_usage(
                    journal.provider_usage(),
                    base_spent_nanos=envelope.cost_start_nanos,
                )
            existing_terminal = journal.terminal()
            if existing_terminal is not None:
                if (isinstance(request, RepairRunRequest)
                        and existing_terminal["payload"]["terminal"] == "PATCH_READY"):
                    delivery = load_delivery(journal, ArtifactStore(state_root / "artifacts"),
                                             envelope)
                    if delivery != existing_terminal["payload"].get("delivery"):
                        raise RecoveryError("terminal repair delivery differs from its receipt")
                return _OneRunResult(
                    _public_result(run_id, existing_terminal["payload"]),
                    False,
                )
        else:
            cost_start_nanos = cost_ledger.spent_nanos if cost_ledger else 0
            envelope = _run_envelope(
                request=request,
                task_dir=task_dir,
                package=package,
                run_id=run_id,
                runtime_hash=runtime_hash,
                model_hash=model_hash,
                cost_ledger=cost_ledger,
                cost_start_nanos=cost_start_nanos,
                prepared_source_hash=admission_hash(request.prepared_source),
                probe_dependencies=admit(request.prepared_probe_dependencies),
            )
            journal.write_envelope(envelope)
            journal.append(
                "run_started",
                {
                    "runtime": DEV_RUNTIME_ID,
                    "provider": request.provider,
                    "task_id": package.public.task_id,
                    "task_version": package.public.task_version,
                    "split": package.public.split,
                    "runtime_hash": runtime_hash,
                    "task_hash": package.task_content_hash,
                    "model_hash": model_hash,
                    "repair_recheck": request.repair_recheck,
                    **({"probe_recheck": request.probe_recheck}
                       if request.probe_recheck != "none" else {}),
                    **({"repair_inspection_policy": request.repair_inspection_policy}
                       if request.repair_inspection_policy != "protected-v1" else {}),
                    "context_policy": request.context_policy,
                    **({"history_search_policy": request.history_search_policy}
                       if request.history_search_policy != "none" else {}),
                    **({"retained_source_chars": request.retained_source_chars}
                       if request.retained_source_chars != 24_000 else {}),
                    **({"evaluation_reserve_seconds": request.evaluation_reserve_seconds}
                       if isinstance(request, DevRunRequest)
                       and request.evaluation_reserve_seconds else {}),
                    **({"segment_boundary_policy": request.segment_boundary_policy}
                       if request.segment_boundary_policy != segments.DEFAULT_BOUNDARY_POLICY
                       else {}),
                    **({"max_output_tokens": request.max_output_tokens}
                       if request.max_output_tokens != DEFAULT_OUTPUT_CEILING else {}),
                    **({"max_correction_output_tokens": request.max_correction_output_tokens}
                       if request.max_correction_output_tokens is not None else {}),
                },
            )

        hashes = {
            "runtime_hash": runtime_hash,
            "task_hash": package.task_content_hash,
            "model_hash": model_hash,
        }
        counters = _restore_counters(journal) if resuming else _RunCounters()
        if journal.unresolved_provider_call() is not None:
            terminal = _terminal(
                journal=journal,
                terminal=DevTerminal.PROVIDER_TIMEOUT_OR_UNKNOWN,
                counters=counters,
                cost_ledger=cost_ledger,
                cost_start_nanos=envelope.cost_start_nanos,
                hashes=hashes,
                message="an earlier provider dispatch has no durable usage record",
            )
            return _OneRunResult(_public_result(run_id, terminal), True)
        usage_failure = _provider_usage_failure(journal)
        if usage_failure is not None:
            # A completed response with uncertain usage is not a retryable
            # protocol failure. Finalize it before workspace/continuation work,
            # including segmented-context integrity checks on resume.
            _recover_unrecorded_decision(journal)
            terminal = _terminal(
                journal=journal, terminal=DevTerminal.PROVIDER_TIMEOUT_OR_UNKNOWN,
                counters=counters, cost_ledger=cost_ledger,
                cost_start_nanos=envelope.cost_start_nanos, hashes=hashes,
                message=usage_failure_message(usage_failure.get("usage_evidence")),
            )
            return _OneRunResult(_public_result(run_id, terminal), True)
        if cost_ledger is not None and cost_ledger.spent_nanos > cost_ledger.cap_nanos:
            terminal = _terminal(
                journal=journal,
                terminal=DevTerminal.PROVIDER_TIMEOUT_OR_UNKNOWN,
                counters=counters,
                cost_ledger=cost_ledger,
                cost_start_nanos=envelope.cost_start_nanos,
                hashes=hashes,
                message="durable provider usage exceeded the invocation cap",
            )
            return _OneRunResult(_public_result(run_id, terminal), True)

        count_failure = journal.unresolved_input_count()
        if count_failure is not None:
            error_type = count_failure["error"].get("exception_type")
            terminal = _terminal(
                journal=journal, terminal=DevTerminal.COUNT_TIMEOUT_OR_UNKNOWN,
                counters=counters, cost_ledger=cost_ledger,
                cost_start_nanos=envelope.cost_start_nanos, hashes=hashes,
                message=(f"input count failed: {error_type}" if error_type
                         else "an earlier input count has no durable outcome record"),
            )
            return _OneRunResult(_public_result(run_id, terminal), True)

        if envelope.compaction_contract is not None:
            try:
                receipt = CompactionAdapter(
                    journal, policy_hash=sha256_json(envelope.compaction_contract),
                ).recover_locked()
                compact_store = ArtifactStore(state_root / "artifacts")
                native_compaction.active_window(journal, compact_store)
                if receipt and receipt.get("ready_for_activation"):
                    native_compaction.ready_source(journal, compact_store, receipt)
                recovery_terminal = receipt.get("terminal") if receipt else None
                recovery_message = receipt.get("message") if receipt else None
            except (OSError, KeyError, TypeError, ValueError, ContractError, RecoveryError):
                recovery_terminal = DevTerminal.PROVIDER_CONTINUATION_ERROR.value
                recovery_message = "compaction recovery evidence is unavailable or invalid"
            if recovery_terminal is not None:
                terminal = _terminal(
                    journal=journal, terminal=DevTerminal(recovery_terminal), counters=counters,
                    cost_ledger=cost_ledger, cost_start_nanos=envelope.cost_start_nanos,
                    hashes=hashes, message=recovery_message,
                )
                return _OneRunResult(_public_result(run_id, terminal), True)

        if request.context_policy == segments.POLICY:
            try:
                segment_store = ArtifactStore(state_root / "artifacts")
                segments.active(journal, segment_store,
                                boundary_policy=request.segment_boundary_policy,
                                agent_policy=request.agent_policy)
                _validate_recorded_continuations(journal.events(), segment_store)
                for event in journal.events():
                    if event["event_type"] == "turn_started":
                        _load_active_model_input(
                            event["payload"], segment_store, context_policy=segments.POLICY,
                        )
                    elif event["event_type"] == "model_input_prepared":
                        prepared = native_compaction.read_json(
                            segment_store, event["payload"]["artifact"],
                        )
                        _load_active_model_input(
                            prepared["turn"], segment_store, context_policy=segments.POLICY,
                        )
            except (OSError, KeyError, TypeError, ValueError, ContractError, RecoveryError):
                terminal = _terminal(
                    journal=journal, terminal=DevTerminal.PROVIDER_CONTINUATION_ERROR,
                    counters=counters, cost_ledger=cost_ledger,
                    cost_start_nanos=envelope.cost_start_nanos, hashes=hashes,
                    message="segment recovery evidence is unavailable or invalid",
                )
                return _OneRunResult(_public_result(run_id, terminal), True)

        if resuming:
            store = ArtifactStore(state_root / "artifacts")
            if isinstance(request, RepairRunRequest):
                delivery = load_delivery(journal, store, envelope)
                if delivery is not None:
                    return _finish_repair_metadata(
                        journal=journal, delivery=delivery, counters=counters,
                        cost_ledger=cost_ledger, cost_start_nanos=envelope.cost_start_nanos,
                        hashes=hashes,
                    )
                completion = None
            else:
                completion = load_evaluation_completion(journal, store, envelope)
            if completion is not None:
                return _finish_evaluation_metadata(
                    journal=journal, store=store, completion=completion, counters=counters,
                    cost_ledger=cost_ledger, cost_start_nanos=envelope.cost_start_nanos,
                    hashes=hashes,
                )

        return _run_one_locked(
            request=request,
            task_dir=task_dir,
            package=package,
            state_root=state_root,
            pricing=pricing,
            cost_ledger=cost_ledger,
            runtime_hash=runtime_hash,
            model_hash=model_hash,
            run_id=run_id,
            journal=journal,
            envelope=envelope,
            resuming=resuming,
        )


def _solver_finish_receipt(journal: DevJournal, request: DevRunRequest) -> dict | None:
    """A durable, timely finish permits evaluation recovery after solver time expires."""
    events = journal.events()
    receipts = [event["payload"] for event in events if event["event_type"] == "solver_finished"]
    if not receipts:
        return None
    if len(receipts) != 1:
        raise RecoveryError("multiple solver finish receipts")
    receipt = receipts[0]
    result = next((event["payload"]["result"] for event in events
                   if event["event_type"] == "action_finished"
                   and event["payload"]["result"]["action_id"] == receipt.get("action_id")), None)
    solve_ms = (request.limits.wall_time_seconds - request.evaluation_reserve_seconds) * 1_000
    if (result is None or result["tool"] != "finish_task" or result["status"] != "succeeded"
            or receipt.get("input_hash") != result["input_hash"]
            or receipt.get("patch_hash") != result["output"].get("patch_hash")
            or type(receipt.get("active_elapsed_ms")) is not int
            or not 0 <= receipt["active_elapsed_ms"] < solve_ms):
        raise RecoveryError("solver finish receipt does not bind a timely submitted candidate")
    return receipt


def _run_one_locked(
    *,
    request: RunRequest,
    task_dir: Path,
    package: Any,
    state_root: Path,
    pricing: ModelPricing | None,
    cost_ledger: DevCostLedger | None,
    runtime_hash: str,
    model_hash: str,
    run_id: str,
    journal: DevJournal,
    envelope: RunEnvelope,
    resuming: bool,
) -> _OneRunResult:
    # Terminal and completed-evaluation recovery already returned before this
    # boundary. Workspace/Git/preflight now spend the row's active execution time.
    active_base_ms = journal.latest_active_elapsed_ms() if resuming else 0
    started = monotonic()
    deadline = ExecutionDeadline(
        started + max(0.0, request.limits.wall_time_seconds - active_base_ms / 1_000),
        clock=monotonic,
    )
    reserve_seconds = (
        request.evaluation_reserve_seconds if isinstance(request, DevRunRequest) else 0
    )
    # The absolute task deadline never moves. A previously completed finish is
    # recovered using the total remainder; new solver work cannot spend its reserve.
    solver_finished = reserve_seconds and _solver_finish_receipt(journal, request) is not None
    execution_deadline = (
        ExecutionDeadline(deadline.expires_at - reserve_seconds, clock=deadline.clock)
        if reserve_seconds and not solver_finished else deadline
    )
    try:
        identity = next((
            event["payload"] for event in journal.events()
            if event["event_type"] == "runtime_git_identity"
        ), None)
        if identity is None:
            identity = {"harness_git_commit": git_commit(deadline=execution_deadline)}
            journal.append("runtime_git_identity", {
                **identity,
                "active_elapsed_ms": active_base_ms + int((monotonic() - started) * 1_000),
            })
        return _run_one_active(
            request=request, task_dir=task_dir, package=package, state_root=state_root,
            pricing=pricing, cost_ledger=cost_ledger, runtime_hash=runtime_hash,
            model_hash=model_hash, run_id=run_id, journal=journal, envelope=envelope,
            resuming=resuming, deadline=execution_deadline, active_base_ms=active_base_ms,
            started=started, harness_git_commit=identity["harness_git_commit"],
            evaluation_deadline=deadline,
        )
    except (ExecutionDeadlineExceeded, GitExecutionUncertain) as exc:
        exhausted = isinstance(exc, ExecutionDeadlineExceeded) or exc.details.get(
            "deadline_exhausted", False,
        )
        terminal = _terminal(
            journal=journal,
            terminal=DevTerminal.LIMIT_REACHED if exhausted else DevTerminal.TASK_FAILED,
            counters=_restore_counters(journal), cost_ledger=cost_ledger,
            cost_start_nanos=envelope.cost_start_nanos,
            hashes={"runtime_hash": runtime_hash, "task_hash": package.task_content_hash,
                    "model_hash": model_hash},
            message=str(exc),
            active_elapsed_ms=active_base_ms + int((monotonic() - started) * 1_000),
        )
        return _OneRunResult(
            _public_result(run_id, terminal), isinstance(exc, GitExecutionUncertain),
        )


def _probe_evidence(journal, artifact_store, run_id):
    """Package executed probes; ordinary resume includes the complete same-profile run."""
    return [
        artifact_store.put_json({
            **event["payload"]["result"]["output"],
            "schema_version": "dev-probe-receipt-v1",
            "run_id": run_id,
            "action_id": event["payload"]["result"]["action_id"],
            "input_hash": event["payload"]["result"]["input_hash"],
            "workspace_diff_hash": event["payload"]["result"]["workspace_diff_hash"],
        })
        for event in journal.events()
        if event["event_type"] == "action_finished"
        and event["payload"]["result"]["tool"] in {"run_probe", "observe_original"}
        and event["payload"]["result"]["output"].get("execution_policy") is not None
    ]


def _run_one_active(
    *, request: RunRequest, task_dir: Path, package: Any, state_root: Path,
    pricing: ModelPricing | None, cost_ledger: DevCostLedger | None,
    runtime_hash: str, model_hash: str, run_id: str, journal: DevJournal,
    envelope: RunEnvelope, resuming: bool, deadline: ExecutionDeadline,
    active_base_ms: int, started: float, harness_git_commit: str,
    evaluation_deadline: ExecutionDeadline | None = None,
) -> _OneRunResult:
    artifact_store = ArtifactStore(state_root / "artifacts")
    counters = _restore_counters(journal) if resuming else _RunCounters()
    cost_start_nanos = envelope.cost_start_nanos
    evaluation_deadline = evaluation_deadline or deadline
    evaluation_reserve_seconds = (
        request.evaluation_reserve_seconds if isinstance(request, DevRunRequest) else 0
    )
    hashes = {
        "runtime_hash": runtime_hash,
        "task_hash": package.task_content_hash,
        "model_hash": model_hash,
    }

    def active_elapsed_ms() -> int:
        return active_base_ms + int((monotonic() - started) * 1_000)

    def remaining_active_seconds() -> float:
        return deadline.remaining_seconds()

    workspace_manager = WorkspaceManager(
        repository_root() / "fixtures" / "repositories",
        state_root / "workspaces",
        **({"local_source": request.source} if isinstance(request, RepairRunRequest) else {}),
        **({"prepared_source": request.prepared_source,
            "prepared_source_hash": envelope.prepared_source_hash}
           if request.prepared_source is not None else {}),
    )
    workspace_path = state_root / "workspaces" / run_id / "repo"
    try:
        if request.provider == "openai" and remaining_active_seconds() > 0:
            if isinstance(request, RepairRunRequest):
                root = repository_root().resolve()
                _require_tracked_clean_paths(root, runtime_content_paths(root), deadline=deadline)
            else:
                _live_source_preflight(task_dir, package, deadline=deadline)
        if resuming and not workspace_path.exists():
            raise RecoveryError("resumable development workspace is missing")
        if request.prepared_source is not None and workspace_path.exists():
            load_source(
                request.prepared_source, package.public.repository.url,
                package.public.repository.base_commit,
                expected_hash=envelope.prepared_source_hash, deadline=deadline,
            )
        workspace = (
            workspace_manager.validate_managed_workspace(workspace_path)
            if workspace_path.exists()
            else workspace_manager.create(
                run_id,
                package.public.repository.url,
                package.public.repository.base_commit,
                deadline=deadline,
            )
        )
        if isinstance(request, RepairRunRequest):
            head = run_git(workspace, "rev-parse", "HEAD", deadline=deadline).stdout.strip()
            if head != package.public.repository.base_commit:
                raise RecoveryError("repair workspace HEAD differs from the admitted base")
        if request.prepared_source is not None and not any(
            event["event_type"] == "prepared_source_bound" for event in journal.events()
        ):
            journal.append("prepared_source_bound", {
                "manifest_hash": envelope.prepared_source_hash,
                "repository_url": package.public.repository.url,
                "base_commit": package.public.repository.base_commit,
            })
    except (ExecutionDeadlineExceeded, GitExecutionUncertain):
        raise
    except PatchLoopError as exc:
        if resuming:
            raise
        terminal = _terminal(
            journal=journal,
            terminal=DevTerminal.PREFLIGHT_FAILED,
            counters=counters,
            cost_ledger=cost_ledger,
            cost_start_nanos=cost_start_nanos,
            hashes=hashes,
            message=str(exc)[:1_000],
            active_elapsed_ms=active_elapsed_ms(),
        )
        return _OneRunResult(_public_result(run_id, terminal), False)

    if resuming:
        _validate_resumed_workspace(
            workspace, journal, deadline=DevToolGateway._recovery_read_deadline(),
        )
        journal.append(
            "run_resumed",
            {
                "active_elapsed_ms": active_elapsed_ms(),
                "run_age_seconds": max(
                    0,
                    int((utc_now() - envelope.created_at).total_seconds()),
                ),
            },
        )

    api_key: str | None = None
    probe_sandbox = None
    caller_sources = None
    try:
        if isinstance(request, RepairRunRequest):
            sandbox = prepared_sandbox(request, deadline=deadline)
            if request.provider == "openai" and remaining_active_seconds() > 0:
                api_key = load_exact_openai_api_key(request.env_file)
        elif request.provider == "openai":
            assert request.env_file is not None
            if remaining_active_seconds() > 0:
                api_key = load_exact_openai_api_key(request.env_file)
                sandbox = _live_sandbox_preflight(package, deadline=deadline)
            else:
                sandbox = DockerSandbox(package.environment.evaluator_image)
        else:
            sandbox = LocalSandbox()
        if request.enable_probes:
            dependencies = (
                load_dependencies(request.prepared_probe_dependencies, package.public,
                                  envelope.probe_dependencies)
                if request.prepared_probe_dependencies is not None else None
            )
            caller_sources = caller_sources_for_run(dependencies, request.caller_source_roots)
            probe_sandbox = (DockerProbeSandbox(dependencies=dependencies)
                             if dependencies is not None else DockerProbeSandbox())
            if remaining_active_seconds() > 0:
                identity = probe_sandbox.preflight(deadline=deadline)
                if identity != {
                    "image_digest": envelope.probe_image_digest,
                    "profile_hash": envelope.probe_profile_hash,
                }:
                    raise ContractError(
                        "probe preflight identity differs from the admitted envelope"
                    )
                if dependencies is not None and not any(
                    event["event_type"] == "probe_dependencies_bound" for event in journal.events()
                ):
                    journal.append("probe_dependencies_bound", {
                        "identity": envelope.probe_dependencies.model_dump(mode="json"),
                        "repository_url": package.public.repository.url,
                        "base_commit": package.public.repository.base_commit,
                    })
    except (ExecutionDeadlineExceeded, GitExecutionUncertain):
        raise
    except PatchLoopError as exc:
        terminal = _terminal(
            journal=journal,
            terminal=DevTerminal.PREFLIGHT_FAILED,
            counters=counters,
            cost_ledger=cost_ledger,
            cost_start_nanos=cost_start_nanos,
            hashes=hashes,
            message=str(exc)[:1_000],
            active_elapsed_ms=active_elapsed_ms(),
        )
        return _OneRunResult(_public_result(run_id, terminal), False)

    journal.append("execution_prepared", {"active_elapsed_ms": active_elapsed_ms()})
    gateway = DevToolGateway(
        workspace=workspace,
        public_task=package.public,
        sandbox=sandbox,
        journal=journal,
        limits=request.limits,
        deadline=deadline,
        probe_sandbox=probe_sandbox,
        probe_policy=request.probe_policy,
        retained_source_chars=request.retained_source_chars,
        reproduction_acquisition=request.reproduction_acquisition,
        agent_policy=request.agent_policy,
        history_search_policy=request.history_search_policy,
        dependency_sources=caller_sources,
    )
    # Diagnostic gateways may schedule bounded phases while sharing this loop's
    # ledger, counters, workspace, deadline and real action receipts. Default runs
    # have no extension and retain their existing context and tool behavior.
    extension = getattr(gateway, "run_extension", None)
    if extension is not None:
        extension.bind(request=request, counters=counters, ledger=cost_ledger,
                       store=artifact_store, resuming=resuming)
    correction: dict[str, Any] | None = _pending_protocol_correction(journal)
    latest_tool_results = journal.latest_tool_batch_results() if resuming else []

    mock_adapter = MockDevAdapter(package.public.task_id) if request.provider == "mock" else None
    openai_adapter: OpenAIResponsesAdapter | None = None
    if request.provider == "openai" and remaining_active_seconds() > 0:
        assert pricing is not None
        config = ModelConfig(
            provider="openai",
            model_id=request.model,
            reasoning_effort=request.reasoning_effort,
            reasoning_continuation="encrypted-v1",
            transport_max_retries=0,
            max_output_tokens=request.max_output_tokens,
            input_price_per_million_usd=float(pricing.input_per_million_usd),
            cached_input_price_per_million_usd=float(pricing.cached_input_per_million_usd),
            output_price_per_million_usd=float(pricing.output_per_million_usd),
        )
        assert api_key is not None
        try:
            openai_adapter = OpenAIResponsesAdapter(config, api_key=api_key)
        except Exception as exc:
            terminal = _terminal(
                journal=journal,
                terminal=DevTerminal.PREFLIGHT_FAILED,
                counters=counters,
                cost_ledger=cost_ledger,
                cost_start_nanos=cost_start_nanos,
                hashes=hashes,
                message=f"provider adapter initialization failed: {type(exc).__name__}",
                active_elapsed_ms=active_elapsed_ms(),
            )
            return _OneRunResult(_public_result(run_id, terminal), False)

    terminal_code: DevTerminal | None = None
    terminal_message: str | None = None
    terminal_completion_horizon: dict[str, Any] | None = None
    stop_remaining = False
    finish_result = next(
        (
            result
            for result in latest_tool_results
            if result.tool == "finish_task" and result.status == "succeeded"
        ),
        None,
    )
    stop_result = next(
        (
            result
            for result in latest_tool_results
            if result.tool == "stop_task" and result.status == "succeeded"
        ),
        None,
    )
    if resuming:
        _recover_unrecorded_decision(journal)
        pending_decision = _unresolved_decision(journal)
        if pending_decision is not None:
            (
                pending_turn_id,
                pending_calls,
                pending_error,
                pending_incomplete_reason,
                pending_tool_contract_failure,
                batch_started,
                pending_allowed_tools,
                pending_max_parallel_reads,
                pending_targeted_read_paths,
                pending_continuation_ref,
                pending_output_item_types,
            ) = pending_decision
            try:
                # Billing uncertainty takes precedence over missing continuation;
                # neither a replayed tool nor another provider call is safe then.
                if pending_error != "input_token_count_mismatch":
                    _validate_recorded_continuations(journal.events(), artifact_store)
                    pending_started = next(
                        event["payload"] for event in reversed(journal.events())
                        if event["event_type"] == "turn_started"
                        and event["payload"].get("turn_id") == pending_turn_id
                    )
                    _load_active_model_input(
                        pending_started, artifact_store, context_policy=request.context_policy,
                    )
                if (pending_error != "input_token_count_mismatch"
                        and request.provider == "openai"
                        and "reasoning" in pending_output_item_types):
                    if pending_continuation_ref is None:
                        raise _ProviderContinuationError(
                            "reasoning output has no durable provider continuation"
                        )
                    pending_continuation = _load_provider_continuation(
                        artifact_store,
                        pending_continuation_ref,
                    )
                    _validate_continuation_action_order(
                        pending_continuation,
                        pending_calls if pending_error is None else [],
                    )
            except _ProviderContinuationError as exc:
                terminal_code = DevTerminal.PROVIDER_CONTINUATION_ERROR
                terminal_message = str(exc)
            if terminal_code is not None:
                pass
            elif pending_error == "provider_continuation_error":
                terminal_code = DevTerminal.PROVIDER_CONTINUATION_ERROR
                terminal_message = "provider reasoning continuation is unavailable"
            elif pending_error == "input_token_count_mismatch":
                terminal_code = DevTerminal.PROVIDER_TIMEOUT_OR_UNKNOWN
                terminal_message = "provider usage disagreed with the pre-dispatch input count"
                stop_remaining = True
            elif pending_error is not None:
                if counters.protocol_recoveries >= request.limits.max_protocol_recoveries:
                    terminal_code = DevTerminal.INCOMPLETE_RESPONSE
                    terminal_message = _model_error_message(
                        pending_error,
                        pending_incomplete_reason,
                        pending_tool_contract_failure,
                    )
                else:
                    counters.protocol_recoveries += 1
                    counters.protocol_corrections_total += 1
                    next_policy = _tool_policy(
                        gateway, counters, request.limits,
                        repair_inspection_policy=request.repair_inspection_policy,
                        repair_recheck=request.repair_recheck,
                        cost_ledger=cost_ledger,
                        completion_cost_policy=request.completion_cost_policy,
                        desired_output_ceiling=request.max_output_tokens,
                        max_correction_output_tokens=request.max_correction_output_tokens,
                    )
                    correction = _protocol_correction(
                        turn_id=pending_turn_id,
                        code=pending_error,
                        issue=_model_error_issue(
                            pending_error,
                            pending_incomplete_reason,
                            pending_tool_contract_failure,
                        ),
                        gateway=gateway,
                        policy=next_policy,
                        tool_contract_failure=pending_tool_contract_failure,
                    )
                    journal.append("protocol_correction", correction)
            else:
                try:
                    validate_tool_batch(
                        pending_calls,
                        agent_policy=request.agent_policy,
                        max_parallel_reads=pending_max_parallel_reads,
                        allowed_tools=pending_allowed_tools,
                        allowed_read_paths=pending_targeted_read_paths,
                        path_diagnosis_pending=(
                            pending_started["workflow_gate"] == "needs_path_diagnosis"),
                        original_acquisition_pending=(
                            pending_started.get("original_acquisition_pending", False)),
                        repair_test_comparison_pending=(
                            pending_started["workflow_gate"] == "needs_test_comparison"),
                    )
                except ContractError as exc:
                    if counters.protocol_recoveries >= request.limits.max_protocol_recoveries:
                        terminal_code = DevTerminal.PROTOCOL_VIOLATION
                        terminal_message = str(exc)
                    else:
                        counters.protocol_recoveries += 1
                        counters.protocol_corrections_total += 1
                        next_policy = _tool_policy(
                            gateway, counters, request.limits,
                            repair_inspection_policy=request.repair_inspection_policy,
                            repair_recheck=request.repair_recheck,
                            cost_ledger=cost_ledger,
                            completion_cost_policy=request.completion_cost_policy,
                            desired_output_ceiling=request.max_output_tokens,
                            max_correction_output_tokens=request.max_correction_output_tokens,
                        )
                        correction = _protocol_correction(
                            turn_id=pending_turn_id,
                            code=(
                                "MISSING_REQUIRED_TOOL"
                                if not pending_calls
                                else "INVALID_TOOL_BATCH"
                            ),
                            issue=str(exc),
                            gateway=gateway,
                            policy=next_policy,
                            rejected_calls=pending_calls,
                        )
                        journal.append("protocol_correction", correction)
                else:
                    if not batch_started:
                        recovery_policy = (_tool_policy(
                            gateway, counters, request.limits,
                            repair_inspection_policy=request.repair_inspection_policy,
                            repair_recheck=request.repair_recheck, cost_ledger=cost_ledger,
                            completion_cost_policy=request.completion_cost_policy,
                            desired_output_ceiling=request.max_output_tokens,
                            max_correction_output_tokens=request.max_correction_output_tokens,
                            _preview_inspection=False,
                        ) if any((call.name == "run_tests"
                                  and test_comparison.has_comparison(call.arguments))
                                 or _requests_test_edit(call)
                                 for call in pending_calls) else None)
                        if recovery_policy is not None and any(
                            _requests_test_edit(call) for call in pending_calls
                        ):
                            offered = pending_started.get("repair_prediction", {})
                            recovery_policy = replace(
                                recovery_policy,
                                repair_test_edit_enabled=offered.get("test_edit_enabled", False),
                                repair_test_edit_minimum_tool_actions=offered.get(
                                    "test_edit_minimum_tool_actions", 0),
                            )
                        if not _batch_fits_tool_budget(
                            pending_calls, counters, request.limits, recovery_policy,
                        ):
                            terminal_code = DevTerminal.LIMIT_REACHED
                            terminal_message = (
                                "recovered batch cannot fit tool actions and completion reserve"
                            )
                        else:
                            journal.append(
                                "tool_batch_started",
                                {
                                    "turn_id": pending_turn_id,
                                    "tool_calls": [
                                        call.model_dump(mode="json") for call in pending_calls
                                    ],
                                    "active_elapsed_ms": active_elapsed_ms(),
                                },
                            )
                            counters.tool_actions += len(pending_calls)
                    if terminal_code is None:
                        try:
                            gateway.record_working_notes_update(
                                pending_calls, turn_id=pending_turn_id,
                            )
                            _record_planning_decision(
                                request.planning_policy, journal=journal, gateway=gateway,
                                calls=pending_calls, turn_id=pending_turn_id,
                            )
                            recovered_results = _execute_completion_batch(
                                calls=pending_calls, journal=journal, gateway=gateway,
                                path_diagnosis_pending=(
                                    pending_started["workflow_gate"] == "needs_path_diagnosis"),
                                repair_test_comparison_pending=(
                                    pending_started["workflow_gate"] == "needs_test_comparison"),
                                counters=counters, active_elapsed_ms=active_elapsed_ms,
                            )
                        except _CompletionVerificationAbort as exc:
                            terminal_code, terminal_message = exc.terminal, str(exc)
                            stop_remaining = exc.terminal == DevTerminal.TASK_FAILED
                        except ExecutionDeadlineExceeded:
                            terminal_code = DevTerminal.LIMIT_REACHED
                            terminal_message = "active deadline exhausted before recovered action"
                        except GitExecutionUncertain:
                            raise
                        except Exception as exc:
                            terminal_code = DevTerminal.TASK_FAILED
                            terminal_message = (
                                f"tool gateway failed during resume: {type(exc).__name__}"
                            )
                        else:
                            recovered_completion, correction = _record_tool_batch(
                                journal=journal,
                                gateway=gateway,
                                turn_id=pending_turn_id,
                                calls=pending_calls,
                                results=recovered_results,
                                active_elapsed_ms=active_elapsed_ms(),
                            )
                            _update_inspection_counters(counters, recovered_results, gateway)
                            counters.protocol_recoveries = 0
                            latest_tool_results = recovered_results
                            terminal_code, terminal_message = _batch_execution_abort(
                                recovered_results,
                            )
                            if terminal_code == DevTerminal.TASK_FAILED:
                                stop_remaining = True
                            if recovered_completion is not None:
                                if recovered_completion.tool == "finish_task":
                                    finish_result = recovered_completion
                                else:
                                    stop_result = recovered_completion
    compact_adapter = (CompactionAdapter(
        journal, policy_hash=sha256_json(envelope.compaction_contract),
    ) if envelope.compaction_contract is not None else None)
    if compact_adapter is not None and terminal_code is None:
        recovered_receipt = compact_adapter.recover_locked()
        if recovered_receipt and recovered_receipt.get("ready_for_activation"):
            native_compaction.activate(journal, artifact_store, recovered_receipt)
    while terminal_code is None and finish_result is None and stop_result is None:
        if extension is not None:
            try:
                extension.before_turn()
            except RecoveryError as exc:
                terminal_code, terminal_message = DevTerminal.TASK_FAILED, str(exc)
                stop_remaining = True
                break
        if request.enable_probes:
            try:
                terminal_code, terminal_message = _run_original_recheck(
                    journal=journal, gateway=gateway, latest_results=latest_tool_results,
                    counters=counters, active_elapsed_ms=active_elapsed_ms,
                    request=request, cost_ledger=cost_ledger,
                )
            except ExecutionDeadlineExceeded:
                terminal_code = DevTerminal.LIMIT_REACHED
                terminal_message = "active deadline exhausted during original recheck"
            except GitExecutionUncertain:
                raise
            except Exception as exc:
                terminal_code = DevTerminal.TASK_FAILED
                terminal_message = f"original recheck failed: {type(exc).__name__}"
            if terminal_code is not None:
                stop_remaining = terminal_code == DevTerminal.TASK_FAILED
                break
        if request.repair_recheck:
            try:
                terminal_code, terminal_message = _run_repair_recheck(
                    journal=journal, gateway=gateway, latest_results=latest_tool_results,
                    counters=counters, active_elapsed_ms=active_elapsed_ms,
                )
            except ExecutionDeadlineExceeded:
                terminal_code = DevTerminal.LIMIT_REACHED
                terminal_message = "active deadline exhausted before repair recheck"
            except GitExecutionUncertain:
                raise
            except Exception as exc:
                terminal_code = DevTerminal.TASK_FAILED
                terminal_message = f"repair recheck failed: {type(exc).__name__}"
            if terminal_code is not None:
                stop_remaining = terminal_code == DevTerminal.TASK_FAILED
                break
        if request.probe_recheck != "none":
            try:
                terminal_code, terminal_message = _run_probe_recheck(
                    journal=journal, gateway=gateway, latest_results=latest_tool_results,
                    counters=counters, active_elapsed_ms=active_elapsed_ms,
                    request=request, cost_ledger=cost_ledger,
                )
            except ExecutionDeadlineExceeded:
                terminal_code = DevTerminal.LIMIT_REACHED
                terminal_message = "active deadline exhausted during probe recheck"
            except GitExecutionUncertain:
                raise
            except Exception as exc:
                terminal_code = DevTerminal.TASK_FAILED
                terminal_message = f"probe recheck failed: {type(exc).__name__}"
            if terminal_code is not None:
                stop_remaining = terminal_code == DevTerminal.TASK_FAILED
                break
        if remaining_active_seconds() <= 0:
            terminal_code = DevTerminal.LIMIT_REACHED
            terminal_message = "row wall-time limit reached"
            break
        elapsed_seconds = active_elapsed_ms() / 1_000
        if extension is not None:
            try:
                extension.before_turn()
            except RecoveryError as exc:
                terminal_code, terminal_message = DevTerminal.TASK_FAILED, str(exc)
                stop_remaining = True
                break
        input_journal = extension.input_journal if extension is not None else journal
        input_results = (input_journal.latest_tool_batch_results()
                         if extension is not None else latest_tool_results)
        projection = gateway.prepare_context_projection(latest_results=latest_tool_results)
        snapshot = gateway.state_snapshot(projection=projection)
        policy = _tool_policy(
            gateway,
            counters,
            request.limits,
            snapshot=snapshot,
            repair_inspection_policy=request.repair_inspection_policy,
            repair_recheck=request.repair_recheck,
            cost_ledger=cost_ledger,
            completion_cost_policy=request.completion_cost_policy,
            desired_output_ceiling=request.max_output_tokens,
            max_correction_output_tokens=request.max_correction_output_tokens,
            remaining_seconds=remaining_active_seconds(),
        )
        if ((snapshot.completion_verification or {}).get("original_obligation", {}).get("stage")
                == "pending" and "run_probe" not in policy.allowed_tools):
            # The phase cannot consume the protected repair/check/return path.
            # Persist this release only on the real loop, never a forecast preview.
            gateway.release_original_acquisition("completion_budget")
            snapshot = gateway.state_snapshot(projection=projection)
            policy = _tool_policy(
                gateway, counters, request.limits, snapshot=snapshot,
                repair_inspection_policy=request.repair_inspection_policy,
                repair_recheck=request.repair_recheck, cost_ledger=cost_ledger,
                completion_cost_policy=request.completion_cost_policy,
                desired_output_ceiling=request.max_output_tokens,
                max_correction_output_tokens=request.max_correction_output_tokens,
                remaining_seconds=remaining_active_seconds(),
            )
        if not policy.completion_possible:
            terminal_completion_horizon = _completion_horizon_payload(
                gateway,
                counters,
                request.limits,
                policy,
                snapshot=snapshot,
            )
            if policy.workflow_gate == "verification_incomplete":
                terminal_code = DevTerminal.VERIFICATION_INCOMPLETE
                if (policy.repair_prediction or {}).get("status") == "needs_test_comparison":
                    terminal_message = (
                        "selected-test comparison and remaining source repair cannot fit resources"
                    )
                    terminal_completion_horizon["repair_prediction"] = policy.repair_prediction
                elif policy.helper_correction and policy.helper_correction.get("blocked"):
                    terminal_message = (
                        "helper program correction is incomplete or cannot fit completion resources"
                    )
                    terminal_completion_horizon["helper_correction"] = policy.helper_correction
                elif policy.repair_path_diagnosis and policy.repair_path_diagnosis.get("blocked"):
                    terminal_message = (
                        "call-path diagnosis is incomplete or cannot fit completion resources"
                    )
                    terminal_completion_horizon["repair_path_diagnosis"] = (
                        policy.repair_path_diagnosis
                    )
                else:
                    terminal_message = (
                        "observation correction is unresolved or cannot fit completion resources"
                    )
                    terminal_completion_horizon["observation_correction"] = (
                        policy.observation_correction
                    )
            elif "cost" in terminal_completion_horizon["blocking_resources"]:
                terminal_code = DevTerminal.COST_CAP_REACHED
                terminal_message = "completion cost reservation cannot fit the remaining cap"
                stop_remaining = True
            else:
                terminal_code = DevTerminal.LIMIT_REACHED
                terminal_message = "completion horizon exhausted before provider dispatch"
            break
        time_reserve = (policy.completion_cost or {}).get("future_time_reserve_seconds", 0)
        provider_deadline = ExecutionDeadline(deadline.expires_at - time_reserve, deadline.clock)
        if (provider_deadline.remaining_seconds() <= 0
                or (policy.completion_cost or {}).get("correction_pending")
                and provider_deadline.remaining_seconds() < 30):
            terminal_code = DevTerminal.LIMIT_REACHED
            terminal_message = "verification and follow-up time reserve leaves no provider time"
            break
        turn_id = f"turn_{uuid.uuid4().hex}"
        try:
            policy_transition = _tool_policy_transition(journal, policy)
            pending_correction = _pending_protocol_correction(journal)
            if pending_correction is not None:
                correction = _protocol_correction(
                    turn_id=str(pending_correction["turn_id"]),
                    code=str(pending_correction["code"]),
                    issue=str(pending_correction.get("issue", pending_correction["message"])),
                    gateway=gateway,
                    policy=policy,
                    tool_contract_failure=(DevToolContractFailure.model_validate(
                        pending_correction["tool_contract_failure"])
                        if pending_correction.get("tool_contract_failure") else None),
                )
                if "rejected_drafts" in pending_correction:
                    # Refresh gate guidance without dropping the original rejected
                    # proposal. Context projection checks its diff before delivery.
                    correction["rejected_drafts"] = pending_correction["rejected_drafts"]
            context = _build_context(
                package=package,
                gateway=gateway,
                journal=journal,
                correction=correction,
                latest_tool_results=latest_tool_results,
                counters=counters,
                elapsed_seconds=elapsed_seconds,
                limits=request.limits,
                policy=policy,
                snapshot=snapshot,
                tool_policy_transition=policy_transition,
                projection=projection,
                repair_recheck=request.repair_recheck,
                probe_recheck_policy=request.probe_recheck,
                repair_inspection_policy=request.repair_inspection_policy,
                planning_policy=request.planning_policy,
                evaluation_reserve_seconds=evaluation_reserve_seconds,
            )
            if extension is not None:
                context = extension.context(context)
            context_payload = json.loads(context)
            if request.context_policy == segments.POLICY:
                context_payload["remaining_budget"]["cost"] = {
                    "currency": "USD", "unit": "nanodollar",
                    "invocation_cap": cost_ledger.cap_nanos if cost_ledger else None,
                    "settled_usage": cost_ledger.spent_nanos if cost_ledger else 0,
                    "remaining": cost_ledger.remaining_nanos if cost_ledger else None,
                    "provider": request.provider,
                    **_completion_cost_payload(policy),
                }
                context = canonical_json(context_payload)
            projected_spans = list(context_payload["source_spans"])
            for projected_result in context_payload["latest_tool_results"]:
                output = projected_result.get("output", {})
                projected_spans.extend(output.get("spans", []))
                mutation_evidence = output.get("mutation_evidence")
                if isinstance(mutation_evidence, dict):
                    projected_spans.append(mutation_evidence)
            context_artifact = artifact_store.put_text(context, "application/json")
            additional_public_exchanges = (extension.public_evidence(context_payload)
                                           if extension is not None else None)
            model_input = _build_model_input(
                journal=input_journal,
                artifact_store=artifact_store,
                context=context,
                latest_tool_results=input_results,
                context_policy=request.context_policy,
                planning_policy=request.planning_policy,
                agent_policy=request.agent_policy,
                segment_boundary_policy=request.segment_boundary_policy,
                history_search_policy=request.history_search_policy,
                additional_public_exchanges=additional_public_exchanges,
            )
            model_input_text = canonical_json(model_input)
            model_input_artifact = artifact_store.put_text(
                model_input_text,
                "application/json",
            )
            window_binding = (_window_binding(journal, artifact_store, model_input)
                              if request.context_policy == WINDOW_POLICY else None)
        except _ProviderContinuationError as exc:
            terminal_code = DevTerminal.PROVIDER_CONTINUATION_ERROR
            terminal_message = str(exc)
            break
        except GitExecutionUncertain:
            raise
        except RecoveryError as exc:
            terminal_code = DevTerminal.TASK_FAILED
            terminal_message = str(exc)
            break
        schemas = dev_tool_schemas(
            finish_enabled="finish_task" in policy.allowed_tools,
            check_ids=policy.check_ids,
            test_suite_ids=[suite.id for suite in gateway.public_task.test_suites],
            test_comparison_enabled=_test_comparison_enabled(policy, counters, request.limits),
            allowed_tools=policy.allowed_tools,
            read_paths=policy.targeted_read_paths,
            planning_policy=request.planning_policy,
            agent_policy=request.agent_policy,
            probe_policy=request.probe_policy,
            probe_recheck_policy=request.probe_recheck,
            probe_environment=getattr(gateway.probe_sandbox, "environment", None),
            dependency_sources=(gateway._dependency_catalog()
                                if getattr(gateway, "dependency_sources", None) is not None
                                else None),
            path_diagnosis_pending=policy.workflow_gate == "needs_path_diagnosis",
            original_acquisition_pending=policy.workflow_gate in {
                "needs_original_reproduction", "needs_original_argument_correction"},
            repair_test_comparison_pending=policy.workflow_gate == "needs_test_comparison",
            repair_revision=policy.repair_path_diagnosis,
            repair_test_edit_enabled=policy.repair_test_edit_enabled,
            history_search_policy=request.history_search_policy,
        )
        if policy.selected_test_comparison_required:
            pending_test = (policy.repair_prediction or {}).get("pending_test")
            mutation_id = (pending_test["comparison"]["mutation_action_id"] if pending_test
                           else policy.repair_path_diagnosis["mutation_action_id"])
            for schema in schemas:
                if schema["name"] == "run_tests":
                    comparison = test_comparison.schema()["anyOf"][1]
                    comparison["properties"]["baseline"]["enum"] = ["before_mutation"]
                    comparison["properties"]["mutation_action_id"] = {
                        "type": "string", "enum": [mutation_id],
                    }
                    schema["parameters"]["properties"]["comparison"] = comparison
        if extension is not None:
            schemas = extension.schemas(schemas)
        if isinstance(request, RepairRunRequest):
            for schema in schemas:
                if schema["name"] == "finish_task":
                    schema["description"] = (
                        "Return the current patch and public verification records after all "
                        "required visible checks pass on this diff and you review the public "
                        "requirements against observed evidence, including unfinished "
                        "verification plans. Describe remaining gaps; missing original evidence "
                        "returns unverified_delivery. Independent acceptance is NOT_RUN; "
                        "regression PASS alone does not prove the reported problem is fixed."
                    )
        turn_payload = {
            "turn_id": turn_id,
            "context_artifact": context_artifact.model_dump(mode="json"),
            "context_hash": context_artifact.content_hash,
            "source_projection_hash": sha256_json(projection.delivered_spans),
            "model_input_artifact": model_input_artifact.model_dump(mode="json"),
            "model_input_hash": model_input_artifact.content_hash,
            "native_history": history_metadata(
                model_input, context_policy=request.context_policy,
                window=native_compaction.active_window(journal, artifact_store)[1],
            ),
            **({"context_window": window_binding} if window_binding is not None else {}),
            **({"context_segment": _segment_input_binding(input_journal, artifact_store)}
               if request.context_policy == segments.POLICY else {}),
            "transcript_action_ids": [
                item["call_id"]
                for item in model_input
                if item.get("type") == "function_call_output"
            ],
            "available_tool_names": sorted(policy.allowed_tools),
            "workflow_gate": policy.workflow_gate,
            "max_parallel_reads": policy.max_parallel_reads,
            "original_acquisition_pending": policy.workflow_gate in {
                "needs_original_reproduction", "needs_original_argument_correction"},
            "targeted_read_paths": list(policy.targeted_read_paths),
            "minimum_completion_calls": policy.minimum_completion_calls,
            **_completion_cost_payload(policy),
            **_repair_inspection_payload(policy),
            **_completion_resources_payload(policy),
            "completion_budget_calls": policy.completion_budget_calls,
            "feedback_recovery_reserve_calls": (policy.feedback_recovery_reserve_calls),
            "mutation_recovery_reserve_calls": (policy.mutation_recovery_reserve_calls),
            "check_recovery_reserve_calls": (policy.check_recovery_reserve_calls),
            "check_recovery_reserve_ids": list(policy.check_recovery_reserve_ids),
            "completion_possible": policy.completion_possible,
            "protected_completion_possible": (policy.protected_completion_possible),
            "mutation_completion_horizon": _mutation_completion_horizon(policy),
            "exploration_state": policy.exploration_state,
            "commitment_action_state": policy.commitment_action_state,
            "closure_reason": policy.closure_reason,
            "targeted_check_repair_inspection": (policy.targeted_check_repair_inspection),
            "targeted_check_repair_required": (policy.targeted_check_repair_required),
            "targeted_mutation_repair_inspection": (
                policy.targeted_mutation_repair_inspection
            ),
            "commitment_signal": _commitment_signal(
                gateway,
                counters,
                policy,
                snapshot=snapshot,
            ),
            "consecutive_no_marginal_evidence_gain_inspection_turns": (
                counters.consecutive_no_evidence_gain_turns
            ),
            "projected_span_ids": [
                span["span_id"]
                for span in projected_spans
                if isinstance(span, dict) and isinstance(span.get("span_id"), str)
            ],
            "active_elapsed_ms": int(elapsed_seconds * 1_000),
        }
        current_output_ceiling = (
            correction_output_ceiling(
                request.max_output_tokens, request.max_correction_output_tokens,
            )
            if policy.completion_cost and policy.completion_cost.get("correction_pending")
            else request.max_output_tokens
        )
        prepared_count = None
        if request.context_policy == segments.POLICY:
            try:
                request_payload = (openai_adapter.request_payload(
                    model_input, schemas, system_prompt=thin_policy.system_prompt(
                        request.agent_policy, request.planning_policy,
                        request.history_search_policy),
                ) if openai_adapter is not None else {
                    "model": request.model, "input": model_input, "tools": schemas,
                    "max_output_tokens": request.max_output_tokens,
                })
                request_payload.update(parallel_tool_calls=_parallel_tool_calls(policy),
                                       tool_choice="required",
                                       max_output_tokens=current_output_ceiling)
                sizes = segments.request_sizes(request_payload)
                reasons = segments.size_reasons(sizes)
                turn_payload["context_request_sizes"] = sizes
                if reasons:
                    binding, _ = segments.active(input_journal, artifact_store)
                    if segments.is_fresh(input_journal, binding):
                        handoff = segments.load_binding(binding, artifact_store)
                        fallback = _segment_size_fallback(handoff, input_results)
                        if fallback:
                            _build_model_input(
                                journal=input_journal, artifact_store=artifact_store,
                                context=context,
                                latest_tool_results=input_results,
                                context_policy=segments.POLICY,
                                planning_policy=request.planning_policy,
                                agent_policy=request.agent_policy,
                                segment_boundary_policy=request.segment_boundary_policy,
                                history_search_policy=request.history_search_policy,
                                force_segment_reason=fallback,
                                additional_public_exchanges=additional_public_exchanges,
                            )
                            continue
                        segments.record_limit(input_journal, sizes=sizes)
                        terminal_code = DevTerminal.LIMIT_REACHED
                        terminal_message = "fresh public state exceeds segment request size limit"
                        break
                    _build_model_input(
                        journal=input_journal, artifact_store=artifact_store, context=context,
                        latest_tool_results=input_results, context_policy=segments.POLICY,
                        planning_policy=request.planning_policy,
                        agent_policy=request.agent_policy,
                        segment_boundary_policy=request.segment_boundary_policy,
                        history_search_policy=request.history_search_policy,
                        force_segment_reason="+".join(reasons),
                        additional_public_exchanges=additional_public_exchanges,
                    )
                    continue
            except (OSError, KeyError, TypeError, ValueError, ContractError, RecoveryError) as exc:
                terminal_code = DevTerminal.PROVIDER_CONTINUATION_ERROR
                terminal_message = (
                    f"segment request is unavailable or invalid: {type(exc).__name__}"
                )
                break
        if compact_adapter is not None or (
            request.context_policy == segments.POLICY and openai_adapter is not None
        ):
            try:
                request_payload = openai_adapter.request_payload(
                    model_input, schemas, system_prompt=thin_policy.system_prompt(
                        request.agent_policy, request.planning_policy,
                        request.history_search_policy),
                )
                request_payload["parallel_tool_calls"] = _parallel_tool_calls(policy)
                request_payload["tool_choice"] = "required"
                request_payload["max_output_tokens"] = current_output_ceiling
                boundary, bundle = native_compaction.prepared_input(
                    input_journal, artifact_store, turn_payload, request_payload, policy_transition,
                )
                turn_payload = bundle["turn"]
                model_input = _load_active_model_input(
                    turn_payload, artifact_store, context_policy=request.context_policy,
                )
                if bundle["request"]["tools"] != schemas:
                    raise RecoveryError("prepared input tool policy changed")
                turn_id = turn_payload["turn_id"]
                schemas = bundle["request"]["tools"]
                policy_transition = bundle["transition"]
                prepared_count = native_compaction.count_prepared(
                    input_journal, boundary, bundle, openai_adapter,
                    provider_deadline, active_elapsed_ms,
                )
                counters.input_count_calls = _restore_counters(journal).input_count_calls
                if (request.context_policy == segments.POLICY
                        and prepared_count[1] > segments.MAX_INPUT_TOKENS):
                    binding, _ = segments.active(input_journal, artifact_store)
                    if segments.is_fresh(input_journal, binding):
                        handoff = segments.load_binding(binding, artifact_store)
                        fallback = _segment_size_fallback(handoff, input_results)
                        if fallback:
                            _build_model_input(
                                journal=input_journal, artifact_store=artifact_store,
                                context=context,
                                latest_tool_results=input_results,
                                context_policy=segments.POLICY,
                                planning_policy=request.planning_policy,
                                agent_policy=request.agent_policy,
                                segment_boundary_policy=request.segment_boundary_policy,
                                history_search_policy=request.history_search_policy,
                                force_segment_reason=fallback,
                                additional_public_exchanges=additional_public_exchanges,
                            )
                            continue
                        segments.record_limit(input_journal, input_tokens=prepared_count[1])
                        terminal_code = DevTerminal.LIMIT_REACHED
                        terminal_message = "fresh public state exceeds segment input token limit"
                        break
                    _build_model_input(
                        journal=input_journal, artifact_store=artifact_store, context=context,
                        latest_tool_results=input_results, context_policy=segments.POLICY,
                        planning_policy=request.planning_policy,
                        agent_policy=request.agent_policy,
                        segment_boundary_policy=request.segment_boundary_policy,
                        history_search_policy=request.history_search_policy,
                        force_segment_reason="input_tokens",
                        additional_public_exchanges=additional_public_exchanges,
                    )
                    continue
                prior_preparation = next((e["payload"] for e in journal.events()
                                          if e["event_type"] == "compaction_prepared"), None)
                if (compact_adapter is not None and (prior_preparation is None
                     or prior_preparation["boundary_id"] == boundary["boundary_id"])
                        and native_compaction.eligible(
                            journal, threshold=request.compact_at_input_tokens,
                            input_tokens=prepared_count[1],
                            remaining_model_calls=(
                                request.limits.max_model_calls - counters.model_calls
                            ),
                            minimum_completion_calls=policy.minimum_completion_calls,
                            ledger=cost_ledger, deadline=provider_deadline, correction=correction,
                        )):
                    if prior_preparation is None:
                        compact_adapter.prepare_locked(
                            source_input=Artifact.model_validate(turn_payload["model_input_artifact"]),
                            source_seed=Artifact.model_validate(turn_payload["context_window"]["seed_artifact"]),
                            boundary_id=boundary["boundary_id"], ledger=cost_ledger,
                            accept_model_limit_reservation=request.accept_compaction_model_limit_reservation,
                            active_elapsed_seconds=active_elapsed_ms() / 1_000,
                        )
                    receipt = compact_adapter.execute_locked(
                        client_factory=lambda: BoundedResponsesClient(api_key=api_key),
                        ledger=cost_ledger, deadline=provider_deadline,
                        active_elapsed_seconds=active_elapsed_ms() / 1_000,
                    )
                    cost_ledger.restore_settled_usage(
                        journal.provider_usage(), base_spent_nanos=cost_start_nanos,
                    )
                    counters = _restore_counters(journal)
                    if receipt["terminal"]:
                        terminal_code = DevTerminal(receipt["terminal"])
                        terminal_message = receipt["message"]
                        stop_remaining = True
                        break
                    native_compaction.activate(journal, artifact_store, receipt)
                    # Not a decision: refresh budgets, current state and schemas;
                    # then count the full post-compaction request from scratch.
                    continue
                turn_payload = {**turn_payload, "prepared_input": boundary,
                                "selected_count_id": prepared_count[0],
                                "counted_request_hash": boundary["request_hash"]}
            except ExecutionDeadlineExceeded:
                terminal_code = DevTerminal.LIMIT_REACHED
                terminal_message = "verification reserve leaves no time for input counting"
                break
            except native_compaction.CountFailure as exc:
                counters = _restore_counters(journal)
                terminal_code = DevTerminal.COUNT_TIMEOUT_OR_UNKNOWN
                terminal_message, stop_remaining = str(exc), True
                break
            except (OSError, KeyError, TypeError, ValueError, ContractError, RecoveryError):
                counters = _restore_counters(journal)
                terminal_code = DevTerminal.PROVIDER_CONTINUATION_ERROR
                terminal_message = "prepared input or compacted window is unavailable or invalid"
                stop_remaining = True
                break
        if request.context_policy == segments.POLICY:
            segments.commit(input_journal, artifact_store)
        journal.append("turn_started", turn_payload)
        if policy_transition is not None:
            journal.append(
                "tool_policy_transition",
                {"turn_id": turn_id, **policy_transition},
            )
        correction = None
        if request.provider == "mock":
            assert mock_adapter is not None
            counters.model_calls += 1
            if extension is not None:
                extension.dispatched(turn_payload)
            try:
                mock_context = (canonical_json(thin_policy.project_state(
                    json.loads(context), "thin")) if request.agent_policy == "thin" else context)
                turn = mock_adapter.next_turn(mock_context, schemas)
            except Exception as exc:
                terminal_code = DevTerminal.TASK_FAILED
                terminal_message = f"mock model failed: {type(exc).__name__}"
                break
            journal.append(
                "model_call_finished",
                {
                    "provider": "mock",
                    "turn_id": turn_id,
                    "tool_call_count": len(turn.tool_calls),
                    "tool_calls": [call.model_dump(mode="json") for call in turn.tool_calls],
                    "error_code": turn.error_code,
                    "incomplete_reason": turn.incomplete_reason,
                    "tool_contract_failure": (
                        turn.tool_contract_failure.model_dump(mode="json")
                        if turn.tool_contract_failure is not None
                        else None
                    ),
                    "output_item_count": turn.output_item_count,
                    "non_tool_output_item_count": turn.non_tool_output_item_count,
                    "output_item_types": turn.output_item_types,
                    "output_shape_hash": turn.output_shape_hash,
                    "active_elapsed_ms": active_elapsed_ms(),
                },
            )
        else:
            assert openai_adapter is not None and cost_ledger is not None
            try:
                request_payload = (bundle["request"] if prepared_count
                                   else openai_adapter.request_payload(
                                       model_input, schemas,
                                       system_prompt=thin_policy.system_prompt(
                                           request.agent_policy, request.planning_policy,
                                           request.history_search_policy),
                                   ))
            except Exception as exc:
                terminal_code = DevTerminal.TASK_FAILED
                terminal_message = f"provider request construction failed: {type(exc).__name__}"
                break
            request_payload["parallel_tool_calls"] = _parallel_tool_calls(policy)
            request_payload["tool_choice"] = "required"
            if prepared_count:
                count_id, input_tokens = prepared_count
                count_request_hash = boundary["request_hash"]
            else:
                count_timeout = provider_deadline.remaining_seconds()
                if count_timeout <= 0:
                    terminal_code = DevTerminal.LIMIT_REACHED
                    terminal_message = "row wall-time limit reached before input counting"
                    break
                count_id = f"count_{uuid.uuid4().hex}"
                count_request_hash = sha256_json(request_payload)
                journal.append(
                    "input_count_started",
                    {
                        "count_id": count_id,
                        "turn_id": turn_id,
                        "request_hash": count_request_hash,
                        "request_metadata": input_count_request_metadata(request_payload),
                        "active_elapsed_ms": active_elapsed_ms(),
                    },
                )
                counters.input_count_calls += 1
                try:
                    input_tokens = openai_adapter.count_input_tokens_v2(
                        request_payload,
                        timeout_seconds=count_timeout,
                    )
                except Exception as exc:
                    error_metadata = input_count_error_metadata(exc)
                    journal.append("input_count_failed", {
                        "count_id": count_id, "turn_id": turn_id,
                        "request_hash": count_request_hash, "error": error_metadata,
                        "active_elapsed_ms": active_elapsed_ms(),
                    })
                    terminal_code = DevTerminal.COUNT_TIMEOUT_OR_UNKNOWN
                    terminal_message = f"input count failed: {error_metadata['exception_type']}"
                    stop_remaining = True
                    break
                journal.append(
                    "input_count_finished",
                    {
                        "count_id": count_id,
                        "turn_id": turn_id,
                        "input_tokens": input_tokens,
                        "active_elapsed_ms": active_elapsed_ms(),
                    },
                )
            admission = cost_ledger.admit(
                input_tokens,
                desired_output_ceiling=current_output_ceiling,
                minimum_output_ceiling=(
                    policy.completion_cost.get("current_minimum_output_ceiling",
                                               MINIMUM_OUTPUT_CEILING)
                    if policy.completion_cost is not None else MINIMUM_OUTPUT_CEILING
                ),
                future_cost_reserve_nanos=max(
                    policy.completion_cost["future_cost_reserve_nanos"]
                    if policy.completion_cost is not None else 0,
                    extension.cost_reserve() if extension is not None else 0,
                ),
            )
            if admission is None:
                if extension is not None and extension.cost_limited(input_tokens):
                    continue
                terminal_code = DevTerminal.COST_CAP_REACHED
                terminal_message = (
                    "provider request plus future completion reserve cannot fit the remaining cap"
                    if policy.completion_cost is not None
                    else "minimum provider request cannot fit the remaining cap"
                )
                stop_remaining = True
                break
            request_payload["max_output_tokens"] = admission.output_ceiling
            if request.context_policy == segments.POLICY:
                final_sizes = segments.request_sizes(request_payload)
                if segments.size_reasons(final_sizes):
                    segments.record_limit(journal, sizes=final_sizes)
                    terminal_code = DevTerminal.LIMIT_REACHED
                    terminal_message = "admitted request exceeds segment byte limit"
                    break
            dispatch_timeout = provider_deadline.remaining_seconds()
            if dispatch_timeout <= 0:
                terminal_code = DevTerminal.LIMIT_REACHED
                terminal_message = "row wall-time limit reached before provider dispatch"
                break
            call_id = f"call_{uuid.uuid4().hex}"
            journal.append(
                "provider_call_started",
                {
                    "call_id": call_id,
                    "turn_id": turn_id,
                    "request_hash": sha256_json(request_payload),
                    **({"prepared_boundary_id": boundary["boundary_id"],
                        "selected_count_id": count_id, "counted_request_hash": count_request_hash}
                       if prepared_count else {}),
                    "input_tokens": input_tokens,
                    "output_ceiling": admission.output_ceiling,
                    "reserved_cost_nanos": admission.reserved_cost_nanos,
                    "timeout_seconds": dispatch_timeout,
                    "future_time_reserve_seconds": time_reserve,
                    **_completion_cost_payload(policy),
                    "active_elapsed_ms": active_elapsed_ms(),
                },
            )
            counters.model_calls += 1
            if extension is not None:
                extension.dispatched(turn_payload)
            try:
                raw_turn = openai_adapter.execute_request(
                    request_payload,
                    requested_input_tokens=input_tokens,
                    timeout_seconds=dispatch_timeout,
                )
            except Exception as exc:  # a started create call has uncertain billing
                terminal_code = DevTerminal.PROVIDER_TIMEOUT_OR_UNKNOWN
                terminal_message = f"provider dispatch failed: {type(exc).__name__}"
                stop_remaining = True
                break
            turn = _turn_from_openai(
                raw_turn, agent_policy=request.agent_policy,
                path_diagnosis_pending=policy.workflow_gate == "needs_path_diagnosis",
                repair_test_comparison_pending=policy.workflow_gate == "needs_test_comparison")
            try:
                cost_nanos = cost_ledger.settle(
                    input_tokens=turn.input_tokens,
                    cached_input_tokens=turn.cached_input_tokens,
                    output_tokens=turn.output_tokens,
                )
            except PatchLoopError as exc:
                terminal_code = DevTerminal.PROVIDER_TIMEOUT_OR_UNKNOWN
                terminal_message = str(exc)
                stop_remaining = True
                break
            continuation_failure: str | None = None
            continuation_ref: ProviderContinuationRef | None = None
            if (
                "reasoning" in turn.output_item_types
                and turn.provider_continuation is None
                and turn.error_code != "input_token_count_mismatch"
            ):
                continuation_failure = "provider reasoning output has no encrypted continuation"
                turn = turn.model_copy(update={"error_code": "provider_continuation_error"})
            elif turn.provider_continuation is not None:
                try:
                    continuation_ref = _store_provider_continuation(
                        artifact_store,
                        turn.provider_continuation,
                    )
                except (OSError, RecoveryError):
                    continuation_failure = (
                        "provider reasoning continuation could not be stored durably"
                    )
                    if turn.error_code != "input_token_count_mismatch":
                        turn = turn.model_copy(update={"error_code": "provider_continuation_error"})
            if continuation_ref is not None:
                turn = turn.model_copy(update={"continuation_ref": continuation_ref})
            journal.append(
                "provider_call_finished",
                {
                    "call_id": call_id,
                    "turn_id": turn_id,
                    "response_id": turn.response_id,
                    "response_model": turn.response_model,
                    "response_status": turn.response_status,
                    "response_reasoning_context": turn.response_reasoning_context,
                    "input_tokens": turn.input_tokens,
                    "cached_input_tokens": turn.cached_input_tokens,
                    "output_tokens": turn.output_tokens,
                    "reasoning_output_tokens": turn.reasoning_output_tokens,
                    **({"usage_evidence": turn.usage_evidence}
                       if turn.usage_evidence is not None else {}),
                    "cost_nanos": cost_nanos,
                    "tool_calls": [call.model_dump(mode="json") for call in turn.tool_calls],
                    "error_code": turn.error_code,
                    "incomplete_reason": turn.incomplete_reason,
                    "tool_contract_failure": (
                        turn.tool_contract_failure.model_dump(mode="json")
                        if turn.tool_contract_failure is not None
                        else None
                    ),
                    "output_item_count": turn.output_item_count,
                    "non_tool_output_item_count": turn.non_tool_output_item_count,
                    "output_item_types": turn.output_item_types,
                    "output_shape_hash": turn.output_shape_hash,
                    "continuation_ref": (
                        continuation_ref.model_dump(mode="json")
                        if continuation_ref is not None
                        else None
                    ),
                    "active_elapsed_ms": active_elapsed_ms(),
                },
            )
        journal.append(
            "turn_decision_recorded",
            {
                "turn_id": turn_id,
                "tool_calls": [call.model_dump(mode="json") for call in turn.tool_calls],
                "error_code": turn.error_code,
                "incomplete_reason": turn.incomplete_reason,
                "response_reasoning_context": turn.response_reasoning_context,
                **({"usage_evidence": turn.usage_evidence}
                   if turn.usage_evidence is not None else {}),
                "tool_contract_failure": (
                    turn.tool_contract_failure.model_dump(mode="json")
                    if turn.tool_contract_failure is not None
                    else None
                ),
                "output_item_count": turn.output_item_count,
                "non_tool_output_item_count": turn.non_tool_output_item_count,
                "output_item_types": turn.output_item_types,
                "output_shape_hash": turn.output_shape_hash,
                "continuation_ref": (
                    turn.continuation_ref.model_dump(mode="json")
                    if turn.continuation_ref is not None
                    else None
                ),
            },
        )
        if request.provider == "openai":
            assert cost_ledger is not None
            if cost_ledger.spent_nanos > cost_ledger.cap_nanos:
                terminal_code = DevTerminal.PROVIDER_TIMEOUT_OR_UNKNOWN
                terminal_message = "observed provider usage exceeded the reserved invocation cap"
                stop_remaining = True
                break
            if turn.error_code == "input_token_count_mismatch":
                terminal_code = DevTerminal.PROVIDER_TIMEOUT_OR_UNKNOWN
                terminal_message = usage_failure_message(turn.usage_evidence)
                stop_remaining = True
                break
            if turn.error_code == "provider_continuation_error":
                terminal_code = DevTerminal.PROVIDER_CONTINUATION_ERROR
                terminal_message = (
                    continuation_failure or "provider reasoning continuation is unavailable"
                )
                break
        if turn.error_code is not None:
            if counters.protocol_recoveries >= request.limits.max_protocol_recoveries:
                terminal_code = DevTerminal.INCOMPLETE_RESPONSE
                terminal_message = _model_error_message(
                    turn.error_code,
                    turn.incomplete_reason,
                    turn.tool_contract_failure,
                )
                break
            counters.protocol_recoveries += 1
            counters.protocol_corrections_total += 1
            next_policy = _tool_policy(
                gateway, counters, request.limits,
                repair_inspection_policy=request.repair_inspection_policy,
                repair_recheck=request.repair_recheck,
                cost_ledger=cost_ledger,
                completion_cost_policy=request.completion_cost_policy,
                desired_output_ceiling=request.max_output_tokens,
                max_correction_output_tokens=request.max_correction_output_tokens,
            )
            correction = _protocol_correction(
                turn_id=turn_id,
                code=turn.error_code,
                issue=_model_error_issue(
                    turn.error_code,
                    turn.incomplete_reason,
                    turn.tool_contract_failure,
                ),
                gateway=gateway,
                policy=next_policy,
                tool_contract_failure=turn.tool_contract_failure,
            )
            journal.append("protocol_correction", correction)
            continue
        try:
            validate_tool_batch(
                turn.tool_calls,
                agent_policy=request.agent_policy,
                max_parallel_reads=policy.max_parallel_reads,
                allowed_tools=policy.allowed_tools,
                allowed_read_paths=policy.targeted_read_paths,
                path_diagnosis_pending=policy.workflow_gate == "needs_path_diagnosis",
                original_acquisition_pending=(
                    policy.workflow_gate in {
                        "needs_original_reproduction", "needs_original_argument_correction"}),
                repair_test_comparison_pending=policy.workflow_gate == "needs_test_comparison",
            )
        except ContractError as exc:
            if counters.protocol_recoveries >= request.limits.max_protocol_recoveries:
                terminal_code = DevTerminal.PROTOCOL_VIOLATION
                terminal_message = str(exc)
                break
            counters.protocol_recoveries += 1
            counters.protocol_corrections_total += 1
            next_policy = _tool_policy(
                gateway, counters, request.limits,
                repair_inspection_policy=request.repair_inspection_policy,
                repair_recheck=request.repair_recheck,
                cost_ledger=cost_ledger,
                completion_cost_policy=request.completion_cost_policy,
                desired_output_ceiling=request.max_output_tokens,
                max_correction_output_tokens=request.max_correction_output_tokens,
            )
            correction = _protocol_correction(
                turn_id=turn_id,
                code="MISSING_REQUIRED_TOOL" if not turn.tool_calls else "INVALID_TOOL_BATCH",
                issue=str(exc),
                gateway=gateway,
                policy=next_policy,
                rejected_calls=turn.tool_calls,
            )
            journal.append("protocol_correction", correction)
            continue
        if not _batch_fits_tool_budget(turn.tool_calls, counters, request.limits, policy):
            terminal_code = DevTerminal.LIMIT_REACHED
            terminal_message = "requested batch cannot fit tool actions and completion reserve"
            break
        journal.append(
            "tool_batch_started",
            {
                "turn_id": turn_id,
                "tool_calls": [call.model_dump(mode="json") for call in turn.tool_calls],
                "active_elapsed_ms": active_elapsed_ms(),
            },
        )
        counters.tool_actions += len(turn.tool_calls)
        try:
            deadline.check()
            gateway.record_working_notes_update(turn.tool_calls, turn_id=turn_id)
            _record_planning_decision(
                request.planning_policy,
                journal=extension.plan_journal if extension is not None else journal,
                gateway=gateway,
                calls=turn.tool_calls, turn_id=turn_id,
            )
            results = _execute_completion_batch(
                calls=turn.tool_calls, journal=journal, gateway=gateway, counters=counters,
                active_elapsed_ms=active_elapsed_ms,
                path_diagnosis_pending=policy.workflow_gate == "needs_path_diagnosis",
                repair_test_comparison_pending=policy.workflow_gate == "needs_test_comparison",
            )
        except _CompletionVerificationAbort as exc:
            terminal_code, terminal_message = exc.terminal, str(exc)
            stop_remaining = exc.terminal == DevTerminal.TASK_FAILED
            break
        except ExecutionDeadlineExceeded:
            terminal_code = DevTerminal.LIMIT_REACHED
            terminal_message = "active deadline exhausted before tool execution"
            break
        except GitExecutionUncertain:
            raise
        except Exception as exc:
            terminal_code = DevTerminal.TASK_FAILED
            terminal_message = f"tool gateway failed: {type(exc).__name__}"
            break
        batch_completion, correction = _record_tool_batch(
            journal=journal,
            gateway=gateway,
            turn_id=turn_id,
            calls=turn.tool_calls,
            results=results,
            active_elapsed_ms=active_elapsed_ms(),
        )
        _update_inspection_counters(counters, results, gateway)
        counters.protocol_recoveries = 0
        if batch_completion is not None:
            if batch_completion.tool == "finish_task":
                finish_result = batch_completion
            else:
                stop_result = batch_completion
        latest_tool_results = results
        terminal_code, terminal_message = _batch_execution_abort(results)
        if terminal_code == DevTerminal.TASK_FAILED:
            stop_remaining = True

    probe_evidence = _probe_evidence(journal, artifact_store, run_id)
    probe_artifact_hashes = {
        f"probe_receipt_{index + 1}": artifact.content_hash
        for index, artifact in enumerate(probe_evidence)
    }
    if stop_result is not None:
        terminal = _terminal(
            journal=journal,
            terminal=DevTerminal.AGENT_STOPPED,
            counters=counters,
            cost_ledger=cost_ledger,
            cost_start_nanos=cost_start_nanos,
            hashes=hashes,
            message=(f"{stop_result.output['reason_code']}: {stop_result.output['summary']}"),
            artifacts=probe_artifact_hashes,
            active_elapsed_ms=active_elapsed_ms(),
        )
        return _OneRunResult(_public_result(run_id, terminal), False)

    if finish_result is None:
        # A physical/output limit can stop the loop before the next policy
        # projection. Retain that stop cause while reporting the unresolved
        # observation; transport/count/billing uncertainty keeps its own terminal.
        if terminal_code in {
            DevTerminal.LIMIT_REACHED, DevTerminal.COST_CAP_REACHED,
            DevTerminal.INCOMPLETE_RESPONSE, DevTerminal.PROTOCOL_VIOLATION,
        }:
            from patchloop.dev import observation_correction

            events = journal.events()
            last_diff = next((e["payload"]["result"]["workspace_diff_hash"]
                              for e in reversed(events) if e["event_type"] == "action_finished"),
                             sha256_bytes(b""))
            unresolved = observation_correction.review(events, last_diff)
            if unresolved["blocked"]:
                terminal_completion_horizon = {
                    **(terminal_completion_horizon or {}), "stop_cause": terminal_code.value,
                    "observation_correction": unresolved,
                }
                terminal_code = DevTerminal.VERIFICATION_INCOMPLETE
            else:
                verification = gateway.completion_verification(diff_hash=last_diff)
                diagnosis = verification.get("repair_path", {})
                if (verification.get("repair_prediction", {}).get("status")
                        == "needs_test_comparison"):
                    terminal_completion_horizon = {
                        **(terminal_completion_horizon or {}), "stop_cause": terminal_code.value,
                        "repair_prediction": verification["repair_prediction"],
                    }
                    terminal_code = DevTerminal.VERIFICATION_INCOMPLETE
                elif diagnosis.get("blocked"):
                    terminal_completion_horizon = {
                        **(terminal_completion_horizon or {}), "stop_cause": terminal_code.value,
                        "repair_path_diagnosis": diagnosis,
                    }
                    terminal_code = DevTerminal.VERIFICATION_INCOMPLETE
                elif verification.get("helper_correction", {}).get("blocked"):
                    terminal_completion_horizon = {
                        **(terminal_completion_horizon or {}), "stop_cause": terminal_code.value,
                        "helper_correction": verification["helper_correction"],
                    }
                    terminal_code = DevTerminal.VERIFICATION_INCOMPLETE
        terminal = _terminal(
            journal=journal,
            terminal=terminal_code or DevTerminal.TASK_FAILED,
            counters=counters,
            cost_ledger=cost_ledger,
            cost_start_nanos=cost_start_nanos,
            hashes=hashes,
            message=terminal_message,
            active_elapsed_ms=active_elapsed_ms(),
            completion_horizon=terminal_completion_horizon,
            artifacts=probe_artifact_hashes,
        )
        return _OneRunResult(_public_result(run_id, terminal), stop_remaining)

    patch = finish_result.output["patch"]
    if evaluation_reserve_seconds:
        receipt = _solver_finish_receipt(journal, request)
        if receipt is None:
            deadline.check()
            journal.append("solver_finished", {
                "action_id": finish_result.action_id, "input_hash": finish_result.input_hash,
                "patch_hash": finish_result.output["patch_hash"],
                "active_elapsed_ms": active_elapsed_ms(),
            })
        elif receipt["action_id"] != finish_result.action_id:
            raise RecoveryError("recovered finish differs from the reserved evaluation candidate")
    submitted = artifact_store.put_text(patch, "text/x-diff")
    if submitted.content_hash != finish_result.output["patch_hash"]:
        raise RecoveryError("submitted artifact differs from the visibly checked diff")
    journal.append(
        "submission_recorded",
        {
            "patch_hash": submitted.content_hash,
            "visible_check_diff_hash": finish_result.output["patch_hash"],
            "changed_files": finish_result.output["changed_files"],
        },
    )
    if isinstance(request, RepairRunRequest):
        delivery = load_delivery(journal, artifact_store, envelope)
        if delivery is None:
            delivery = record_delivery(
                journal, artifact_store, envelope, submitted, finish_result.output,
                active_elapsed_ms(),
            )
        return _finish_repair_metadata(
            journal=journal, delivery=delivery, counters=counters, cost_ledger=cost_ledger,
            cost_start_nanos=cost_start_nanos, hashes=hashes,
        )
    manifest = _manifest(
        request=request,
        package=package,
        run_id=run_id,
        sandbox_backend="docker" if request.provider == "openai" else "local",
        pricing=pricing,
        runtime_hash=runtime_hash,
        model_hash=model_hash,
        submitted_patch_hash=submitted.content_hash,
        submitted_changed_files=finish_result.output["changed_files"],
        created_at=envelope.created_at,
        harness_git_commit=harness_git_commit,
        probe_evidence=probe_evidence,
        probe_dependencies=envelope.probe_dependencies,
    )
    manifest_text = canonical_json(manifest.model_dump(mode="json")) + "\n"
    manifest_artifact = artifact_store.put_text(manifest_text, "application/json")
    run_artifact_dir = Path(artifact_store.root) / "runs" / run_id
    artifact_store.write_text_immutable(run_artifact_dir / "manifest.json", manifest_text)
    journal.append(
        "manifest_recorded",
        {
            "manifest_content_hash": manifest_artifact.content_hash,
            "submitted_patch_content_hash": submitted.content_hash,
        },
    )
    evaluator = EvaluationEngine(workspace_manager, sandbox, artifact_store)
    try:
        evaluation = evaluator.evaluate(
            task_dir,
            submitted.path,
            manifest,
            submitted_patch_artifact=submitted,
            deadline=evaluation_deadline,
        )
        evaluator_summary = _evaluator_summary(evaluation)
        terminal_code = (
            DevTerminal.EVALUATOR_PASS
            if evaluator_summary["task_acceptance"] == "PASS"
            else DevTerminal.EVALUATOR_FAIL
        )
    except ExecutionDeadlineExceeded:
        evaluator_summary = {
            "task_acceptance": "ERROR",
            "safety_state": "ERROR",
            "failure_class": "ACTIVE_DEADLINE_EXHAUSTED",
            "claim_eligible": False,
        }
        terminal_code = DevTerminal.LIMIT_REACHED
        terminal_message = "active deadline exhausted during isolated evaluation"
    except GitExecutionUncertain as exc:
        evaluator_summary = {
            "task_acceptance": "ERROR", "safety_state": "ERROR",
            "failure_class": (
                "ACTIVE_DEADLINE_EXHAUSTED" if exc.details.get("deadline_exhausted")
                else "EVALUATOR_INFRA_FAILURE"
            ),
            "claim_eligible": False,
        }
        terminal_code = (
            DevTerminal.LIMIT_REACHED if exc.details.get("deadline_exhausted")
            else DevTerminal.EVALUATOR_ERROR
        )
        terminal_message = str(exc)
        stop_remaining = True
    except Exception as exc:
        evaluator_summary = {
            "task_acceptance": "ERROR",
            "safety_state": "ERROR",
            "failure_class": (
                "SANDBOX_CLEANUP_UNCONFIRMED"
                if isinstance(exc, SandboxCleanupError) else "EVALUATOR_INFRA_FAILURE"
            ),
            "claim_eligible": False,
        }
        if isinstance(exc, SandboxCleanupError):
            stop_remaining = True
        terminal_code = DevTerminal.EVALUATOR_ERROR
        terminal_message = f"isolated evaluator failed: {type(exc).__name__}"
    evaluator_provenance_path = run_artifact_dir / "provenance.json"
    completion_artifacts = {
        "submitted_patch": submitted,
        "manifest": manifest_artifact,
        **{f"probe_receipt_{index + 1}": artifact for index, artifact in enumerate(probe_evidence)},
    }
    if evaluator_provenance_path.is_file() and not evaluator_provenance_path.is_symlink():
        completion_artifacts["evaluator_provenance"] = artifact_store.put_bytes(
            evaluator_provenance_path.read_bytes(),
            "application/json",
        )
    completion = prepare_evaluation_completion(
        store=artifact_store, run_id=run_id, terminal=terminal_code, summary=evaluator_summary,
        message=terminal_message, stop_remaining=stop_remaining,
        active_elapsed_ms=active_elapsed_ms(), artifacts=completion_artifacts, hashes=hashes,
    )
    journal.append(
        "evaluator_finished",
        completion.model_dump(mode="json"),
    )
    return _finish_evaluation_metadata(
        journal=journal, store=artifact_store, completion=completion, counters=counters,
        cost_ledger=cost_ledger, cost_start_nanos=cost_start_nanos, hashes=hashes,
    )


def run_dev(request: DevRunRequest) -> dict[str, Any]:
    """Run 1-6 unofficial repetitions under one explicit invocation cap."""

    if not isinstance(request, DevRunRequest):
        try:
            request = DevRunRequest.model_validate(request)
        except ValidationError as exc:
            raise ContractError(str(exc)) from exc
    task_dir, package = _resolve_task_file(request.task)
    if request.provider == "openai":
        _live_task_is_admitted(task_dir, package)
    return _run_invocation(request, task_dir, package)


def _run_invocation(request: RunRequest, task_dir: Path, package: Any) -> dict[str, Any]:
    """One shared admission, budget, journal and solver loop for both entry points."""
    state_root = request.state_root.resolve() if request.state_root else default_state_root()
    repo = repository_root().resolve()
    if state_root == repo or state_root.is_relative_to(repo):
        raise ContractError("development run state must be outside the PatchLoop repository")
    state_root.mkdir(parents=True, exist_ok=True)

    pricing: ModelPricing | None = None
    cost_ledger: DevCostLedger | None = None
    if request.provider == "openai":
        assert request.max_cost_usd is not None
        pricing = pricing_for_model(request.model)
        cost_ledger = DevCostLedger(request.max_cost_usd, pricing)

    runtime_hash = _runtime_hash()
    model_hash = _model_hash(request, pricing)
    results: list[dict[str, Any]] = []
    for _ in range(request.repeat):
        one = _run_one(
            request=request,
            task_dir=task_dir,
            package=package,
            state_root=state_root,
            pricing=pricing,
            cost_ledger=cost_ledger,
            runtime_hash=runtime_hash,
            model_hash=model_hash,
        )
        results.append(one.public)
        if one.stop_remaining:
            break
    return {
        "schema_version": "dev-invocation-v1",
        "official": False,
        "runtime": DEV_RUNTIME_ID,
        "requested_repetitions": request.repeat,
        "completed_repetitions": len(results),
        "cost_cap_nanos": cost_ledger.cap_nanos if cost_ledger else 0,
        "cost_nanos": cost_ledger.spent_nanos if cost_ledger else 0,
        "runs": results,
        **({"stop_remaining": True} if one.stop_remaining else {}),
    }
