"""Single mutable PatchLoop development runtime."""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from typing import Any

from pydantic import ValidationError

from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import ModelConfig, RunManifest, VerdictState
from patchloop.dev.contracts import (
    DEV_RUNTIME_ID,
    DevModelTurn,
    DevRunEnvelope,
    DevRunRequest,
    DevTerminal,
    DevToolResult,
    RequestedTool,
    dev_tool_surface_hash,
)
from patchloop.dev.cost import (
    PRICING_SOURCE,
    PRICING_VERIFIED_ON,
    DevCostLedger,
    ModelPricing,
    pricing_for_model,
)
from patchloop.dev.model import DEV_SYSTEM_PROMPT, MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas, validate_tool_batch
from patchloop.environment import load_exact_openai_api_key
from patchloop.errors import (
    ContractError,
    PatchLoopError,
    RecoveryError,
    ResumeContractMismatch,
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
from patchloop.task_loader import load_task_package, task_package_content_paths
from patchloop.util import canonical_json, sha256_bytes, sha256_json, utc_now
from patchloop.verifier.core import EvaluationEngine


@dataclass
class _RunCounters:
    model_calls: int = 0
    tool_actions: int = 0
    input_count_calls: int = 0
    protocol_recoveries: int = 0
    inspection_turns_at_diff: int = 0
    failed_mutation_repair_turns: int = 0
    failed_mutation_pending: bool = False


@dataclass
class _OneRunResult:
    public: dict[str, Any]
    stop_remaining: bool


@dataclass(frozen=True)
class _ToolPolicy:
    workflow_gate: str
    allowed_tools: frozenset[str]
    check_ids: tuple[str, ...]
    max_parallel_reads: int
    minimum_completion_calls: int
    completion_possible: bool
    exploration_allowed: bool
    inspection_lease_available: bool


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


def _model_hash(request: DevRunRequest, pricing: ModelPricing | None) -> str:
    return sha256_json(
        {
            "provider": request.provider,
            "model": request.model,
            "reasoning_effort": request.reasoning_effort,
            "transport_max_retries": 0 if request.provider == "openai" else None,
            "service_tier": "default",
            "api_base_url": "https://api.openai.com/v1",
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


def _require_tracked_clean_paths(root: Path, relative_paths: list[str]) -> None:
    expected = sorted(set(relative_paths))
    tracked = subprocess.run(
        ["git", "ls-files", "-z", "--", *expected],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if tracked.returncode != 0:
        raise ContractError("cannot inspect live source tracking state")
    actual = sorted(path for path in tracked.stdout.split("\0") if path)
    if actual != expected:
        raise ContractError("live runtime and task inputs must all be tracked")
    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all", "--", *expected],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if status.returncode != 0:
        raise ContractError("cannot inspect live source modification state")
    if status.stdout:
        raise ContractError("live runtime and task inputs must match HEAD exactly")


def _live_source_preflight(task_dir: Path, package: Any) -> None:
    root = repository_root().resolve()
    task_paths = [
        (task_dir / relative).resolve().relative_to(root).as_posix()
        for relative in task_package_content_paths(package)
    ]
    _require_tracked_clean_paths(root, [*runtime_content_paths(root), *task_paths])


def _live_sandbox_preflight(package: Any) -> DockerSandbox:
    environment = package.environment
    if environment is None:
        raise ContractError("live evaluator environment is missing")
    sandbox = DockerSandbox(environment.evaluator_image)
    if not DockerSandbox.available():
        raise ContractError("Docker is unavailable; dev-head never starts or installs it")
    identity = sandbox.image_identity()
    if identity is None:
        raise ContractError(
            "required evaluator image is not local; dev-head never pulls or builds it"
        )
    if identity != environment.image_digest:
        raise ContractError("local evaluator image does not match environment.yaml")
    return sandbox


def _manifest(
    *,
    request: DevRunRequest,
    package: Any,
    run_id: str,
    sandbox_backend: str,
    pricing: ModelPricing | None,
    runtime_hash: str,
    model_hash: str,
    submitted_patch_hash: str,
    submitted_changed_files: list[str],
    created_at: Any,
) -> RunManifest:
    return RunManifest(
        run_id=run_id,
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        base_commit=package.public.repository.base_commit,
        public_spec_hash=package.public_spec_hash,
        private_spec_hash=package.private_spec_hash,
        task_content_hash=package.task_content_hash,
        runtime_content_hash=runtime_hash,
        model_hash=model_hash,
        tool_surface_hash=dev_tool_surface_hash(),
        sandbox_identity_hash=_sandbox_identity_hash(request, package),
        submitted_patch_content_hash=submitted_patch_hash,
        visible_check_diff_hash=submitted_patch_hash,
        submitted_changed_files=sorted(submitted_changed_files),
        harness_git_commit=git_commit(),
        model=ModelConfig(
            provider=request.provider,
            model_id=request.model,
            reasoning_effort=request.reasoning_effort,
            transport_max_retries=0 if request.provider == "openai" else None,
            max_output_tokens=4096,
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
                "remaining_visible_check_ids": correction[
                    "remaining_visible_check_ids"
                ],
            }
        )
    return cards[-3:]


def _recent_checks(gateway: DevToolGateway) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for diff_hash, checks in gateway.checks_by_diff.items():
        for value in checks.values():
            rows.append(
                {
                    "check_id": value["check_id"],
                    "diff_hash": diff_hash,
                    "passed": value["passed"],
                    "failure_signature": value.get("failure_signature"),
                    "exit_code": value.get("exit_code"),
                    "timed_out": value.get("timed_out"),
                    "stdout": value.get("stdout", "")[-4_000:],
                    "stderr": value.get("stderr", "")[-4_000:],
                }
            )
    return rows[-3:]


def _workflow_gate(gateway: DevToolGateway, *, summary: Any | None = None) -> str:
    current = summary if summary is not None else gateway.current_diff
    if not current.patch or current.untracked_files:
        return "needs_mutation"
    if gateway.ready_to_submit():
        return "ready_to_submit"
    return "needs_visible_checks"


def _minimum_completion_calls(gateway: DevToolGateway, workflow_gate: str) -> int:
    mutation_calls = 1 + (0 if gateway.spans else 1)
    if workflow_gate == "needs_mutation":
        return mutation_calls + len(gateway.public_task.visible_checks) + 1
    if workflow_gate == "needs_visible_checks":
        if any(row["status"] == "FAIL" for row in gateway.visible_check_status()):
            return mutation_calls + len(gateway.public_task.visible_checks) + 1
        return len(gateway.remaining_visible_check_ids()) + 1
    return 1


def _tool_policy(
    gateway: DevToolGateway,
    counters: _RunCounters,
    limits: Any,
) -> _ToolPolicy:
    workflow_gate = _workflow_gate(gateway)
    minimum_completion_calls = _minimum_completion_calls(gateway, workflow_gate)
    remaining_model_calls = max(0, limits.max_model_calls - counters.model_calls)
    remaining_tool_actions = max(0, limits.max_tool_actions - counters.tool_actions)
    model_slack = remaining_model_calls - minimum_completion_calls
    tool_slack = remaining_tool_actions - minimum_completion_calls
    summary = gateway.current_diff
    current_check_failed = any(
        row["status"] == "FAIL" for row in gateway.visible_check_status()
    )
    mutation_capacity = (
        gateway.accepted_mutations < limits.max_accepted_mutations
        and not summary.untracked_files
    )
    requires_mutation_for_completion = (
        workflow_gate == "needs_mutation" or current_check_failed
    )
    completion_possible = not requires_mutation_for_completion or mutation_capacity
    exploration_allowed = model_slack > 0 and tool_slack > 0 and completion_possible
    if gateway.last_failed_mutation is not None:
        inspection_lease_available = (
            counters.failed_mutation_repair_turns
            < limits.max_failed_mutation_repair_turns
        )
    else:
        inspection_lease_available = (
            counters.inspection_turns_at_diff
            < limits.max_consecutive_inspection_turns
        )
    max_parallel_reads = (
        min(limits.max_parallel_reads, tool_slack)
        if exploration_allowed and inspection_lease_available
        else 0
    )

    allowed = {"stop_task"}
    unrun_checks = tuple(gateway.unrun_visible_check_ids())
    if workflow_gate == "ready_to_submit":
        allowed.add("finish_task")
    else:
        if max_parallel_reads > 0:
            allowed.update({"read_file", "search_files"})
        # A base check is diagnostic evidence and may use only genuine horizon slack.
        # On a non-empty diff, each not-yet-run check is direct completion work.
        if unrun_checks and (
            (bool(summary.patch) and not current_check_failed) or exploration_allowed
        ):
            allowed.add("run_check")
        if (
            mutation_capacity
            and bool(gateway.spans)
        ):
            allowed.add("apply_git_diff")
    return _ToolPolicy(
        workflow_gate=workflow_gate,
        allowed_tools=frozenset(allowed),
        check_ids=unrun_checks,
        max_parallel_reads=max_parallel_reads,
        minimum_completion_calls=minimum_completion_calls,
        completion_possible=completion_possible,
        exploration_allowed=exploration_allowed,
        inspection_lease_available=inspection_lease_available,
    )


def _protocol_correction(
    *,
    turn_id: str,
    code: str,
    issue: str,
    gateway: DevToolGateway,
) -> dict[str, Any]:
    gate = _workflow_gate(gateway)
    remaining = gateway.remaining_visible_check_ids()
    if gate == "needs_mutation":
        guidance = (
            "Current gate is needs_mutation. Read public source as needed, apply one safe "
            "scoped mutation, or call stop_task if no safe progress is possible."
        )
    elif gate == "needs_visible_checks":
        guidance = (
            "Current gate is needs_visible_checks. Remaining visible checks for the current "
            f"diff: {', '.join(remaining)}. Run one remaining check, or inspect and mutate only "
            "when public evidence requires it."
        )
    else:
        guidance = "Current gate is ready_to_submit. Call finish_task or stop_task."
    return {
        "turn_id": turn_id,
        "code": code,
        "message": f"{issue} {guidance}",
        "workflow_gate": gate,
        "remaining_visible_check_ids": remaining,
    }


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
) -> str:
    summary = gateway.current_diff
    active_policy = policy or _tool_policy(gateway, counters, limits)
    latest_span_ids = {
        span["span_id"]
        for result in latest_tool_results
        for span in result.output.get("spans", [])
        if isinstance(span, dict) and isinstance(span.get("span_id"), str)
    }
    payload = {
        "public_task": package.public.model_dump(mode="json"),
        "current_diff": {
            "patch": summary.patch,
            "patch_hash": summary.patch_hash,
            "changed_files": summary.changed_files,
            "added_lines": summary.added_lines,
            "deleted_lines": summary.deleted_lines,
            "untracked_files": summary.untracked_files,
            "truncated": False,
        },
        "latest_tool_results": [
            result.model_dump(mode="json", exclude={"replayed"})
            for result in latest_tool_results
        ],
        "source_spans": gateway.context_spans(exclude=latest_span_ids),
        "recent_checks": _recent_checks(gateway),
        "visible_check_status": gateway.visible_check_status(),
        "remaining_visible_check_ids": gateway.remaining_visible_check_ids(),
        "last_successful_mutation": gateway.last_successful_mutation,
        "last_failed_mutation": gateway.last_failed_mutation,
        "recent_attempt_result_next_question": _cards(journal, correction),
        "workflow_gate": active_policy.workflow_gate,
        "available_tool_names": sorted(active_policy.allowed_tools),
        "action_horizon": {
            "minimum_completion_calls": active_policy.minimum_completion_calls,
            "completion_possible": active_policy.completion_possible,
            "exploration_allowed": active_policy.exploration_allowed,
            "max_parallel_reads_this_turn": active_policy.max_parallel_reads,
            "inspection_turns_at_current_diff": counters.inspection_turns_at_diff,
            "inspection_turn_limit": limits.max_consecutive_inspection_turns,
            "failed_mutation_repair_turns": counters.failed_mutation_repair_turns,
            "failed_mutation_repair_turn_limit": (
                limits.max_failed_mutation_repair_turns
            ),
        },
        "remaining_budget": {
            "model_calls": max(0, limits.max_model_calls - counters.model_calls),
            "tool_actions": max(0, limits.max_tool_actions - counters.tool_actions),
            "accepted_mutations": max(
                0,
                limits.max_accepted_mutations - gateway.accepted_mutations,
            ),
            "active_wall_time_seconds": max(
                0,
                int(limits.wall_time_seconds - elapsed_seconds),
            ),
            "consecutive_protocol_corrections": max(
                0,
                limits.max_protocol_recoveries - counters.protocol_recoveries,
            ),
        },
    }
    # Construction is allowlist-based from ``package.public`` and public tool outputs;
    # private task fields are never accepted as context inputs.
    return canonical_json(payload)


def _requested_tool_from_openai(call: Any) -> RequestedTool:
    arguments = dict(call.arguments)
    turn_decision = arguments.pop("turn_decision", None)
    return RequestedTool(
        name=call.name,
        action_id=call.action_id,
        arguments=arguments,
        turn_decision=turn_decision,
    )


def _turn_from_openai(turn: Any) -> DevModelTurn:
    calls: list[RequestedTool] = []
    conversion_error: str | None = None
    for call in turn.tool_calls:
        try:
            calls.append(_requested_tool_from_openai(call))
        except (TypeError, ValueError, ValidationError):
            calls = []
            conversion_error = "invalid_dev_tool_contract"
            break
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
        incomplete_reason=turn.response_incomplete_reason,
        error_code=turn.error.code if turn.error else conversion_error,
        output_item_count=turn.output_item_count,
        non_tool_output_item_count=turn.non_tool_output_item_count,
        output_item_types=list(turn.output_item_types),
        output_shape_hash=turn.output_shape_hash,
    )


def _provider_tool_arguments(call: RequestedTool) -> dict[str, Any]:
    arguments = dict(call.arguments)
    if call.turn_decision is None:
        raise RecoveryError("public tool transcript is missing its turn decision")
    arguments["turn_decision"] = call.turn_decision.model_dump(mode="json")
    return arguments


def _build_model_input(
    *,
    journal: DevJournal,
    context: str,
    latest_tool_results: list[DevToolResult],
) -> list[dict[str, Any]]:
    """Build one bounded native tool continuation from public durable records."""

    system_item = {"role": "system", "content": DEV_SYSTEM_PROMPT}
    if not latest_tool_results:
        return [system_item, {"role": "user", "content": context}]
    events = journal.events()
    batch = next(
        (event for event in reversed(events) if event["event_type"] == "tool_batch_finished"),
        None,
    )
    if batch is None:
        raise RecoveryError("latest tool results have no completed batch")
    turn_id = batch["payload"].get("turn_id")
    action_ids = batch["payload"].get("action_ids")
    if not isinstance(turn_id, str) or not isinstance(action_ids, list):
        raise RecoveryError("latest completed batch has an invalid identity")
    decision = next(
        (
            event
            for event in reversed(events)
            if event["event_type"] == "turn_decision_recorded"
            and event["payload"].get("turn_id") == turn_id
        ),
        None,
    )
    started = next(
        (
            event
            for event in reversed(events)
            if event["event_type"] == "turn_started"
            and event["payload"].get("turn_id") == turn_id
        ),
        None,
    )
    if decision is None or started is None:
        raise RecoveryError("latest completed batch is missing its public turn records")
    calls = [
        RequestedTool.model_validate(value)
        for value in decision["payload"].get("tool_calls", [])
    ]
    if [call.action_id for call in calls] != action_ids:
        raise RecoveryError("latest public tool calls do not match the completed batch")
    results_by_id = {result.action_id: result for result in latest_tool_results}
    if set(results_by_id) != set(action_ids):
        raise RecoveryError("latest public tool results do not match the completed batch")

    current_payload = json.loads(context)
    current_payload["latest_tool_results"] = []
    current_payload["latest_tool_results_delivery"] = {
        "format": "preceding_function_call_output_items",
        "action_ids": action_ids,
    }
    marker = canonical_json(
        {
            "continuation": "immediately_preceding_public_tool_batch",
            "prior_turn_id": turn_id,
            "prior_context_hash": started["payload"].get("context_hash"),
        }
    )
    call_items = [
        {
            "type": "function_call",
            "call_id": call.action_id,
            "name": call.name,
            "arguments": canonical_json(_provider_tool_arguments(call)),
        }
        for call in calls
    ]
    output_items = [
        {
            "type": "function_call_output",
            "call_id": action_id,
            "output": canonical_json(
                results_by_id[action_id].model_dump(mode="json", exclude={"replayed"})
            ),
        }
        for action_id in action_ids
    ]
    return [
        system_item,
        {"role": "user", "content": marker},
        *call_items,
        *output_items,
        {"role": "user", "content": canonical_json(current_payload)},
    ]


def _attempt_card(result: DevToolResult, gateway: DevToolGateway) -> dict[str, Any]:
    if result.status == "failed":
        next_question = (
            "Repair or explicitly replace last_failed_mutation; use read/search only "
            "when needed for that repair."
            if result.tool == "apply_git_diff"
            else "What available public action resolves this failure?"
        )
        return {
            "action_id": result.action_id,
            "attempt": result.tool,
            "result": result.error_code or "failed",
            "next_question": next_question,
        }
    if result.tool in {"read_file", "search_files"}:
        spans = result.output.get("spans", [])
        if result.output.get("stagnation_signal"):
            next_question = (
                "This exact evidence is already visible; choose a materially different query, "
                "range, check, or mutation."
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
                "findings": findings,
                "evidence_fingerprint": result.output.get("evidence_fingerprint"),
                "evidence_cache_hit": result.evidence_cache_hit,
                "stagnation_signal": result.output.get("stagnation_signal", False),
            },
            "next_question": next_question,
        }
    if result.tool == "apply_git_diff":
        return {
            "action_id": result.action_id,
            "attempt": "mutation",
            "result": result.output["worktree_diff_hash"],
            "next_question": (
                "Which registered visible check most directly tests the expected behavior?"
            ),
        }
    if result.tool == "run_check":
        if result.output["passed"] is not True:
            next_question = (
                "What does this public failure falsify, and what mechanism should change next?"
            )
        elif gateway.ready_to_submit():
            next_question = "Submit the projected diff."
        else:
            remaining = gateway.remaining_visible_check_ids()
            next_question = (
                "Run one remaining visible check for the current diff: " + ", ".join(remaining)
                if remaining
                else "Resolve the current workflow gate before submission."
            )
        return {
            "action_id": result.action_id,
            "attempt": f"check:{result.output['check_id']}",
            "result": "PASS" if result.output["passed"] else result.output["failure_signature"],
            "next_question": next_question,
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
        "next_question": "Run the isolated private evaluator.",
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
    decision = calls[0].turn_decision
    if decision is None:
        raise RecoveryError("completed tool batch is missing its public turn decision")
    if all(call.name in {"read_file", "search_files"} for call in calls):
        actions: list[dict[str, Any]] = []
        for call, result in zip(calls, results, strict=True):
            spans = result.output.get("spans", [])
            actions.append(
                {
                    "action_id": result.action_id,
                    "tool": result.tool,
                    "input": call.arguments,
                    "status": result.status,
                    "error_code": result.error_code,
                    "span_count": len(spans),
                    "new_span_count": result.output.get("new_span_count", 0),
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
        elif any(action["stagnation_signal"] for action in actions):
            next_question = "Choose a materially different available action from this evidence."
        else:
            next_question = "Choose the next available action from this completed batch evidence."
        return {
            "action_id": f"batch:{turn_id}",
            "attempt": "inspect",
            "turn_decision": decision.model_dump(mode="json"),
            "result": {"actions": actions},
            "next_question": next_question,
        }
    card = _attempt_card(results[0], gateway)
    card["turn_decision"] = decision.model_dump(mode="json")
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
        if result["tool"] == "apply_git_diff":
            mutation = output["mutation"]
            plans.append(
                {
                    "hypothesis_hash": sha256_json(mutation["hypothesis"]),
                    "expected_behavior_hash": sha256_json(mutation["expected_behavior"]),
                    "evidence_span_ids": mutation["evidence_span_ids"],
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
                "evidence_span_ids": output["evidence_span_ids"],
                "diff_hash": output["diff_hash"],
            }
    return {
        "plan": plans,
        "edit": edits,
        "check": checks,
        "submission": submission,
        "agent_stop": agent_stop,
    }


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
                    int(
                        (
                            utc_now() - journal.load_envelope().created_at
                        ).total_seconds()
                    ),
                )
                if run_age_seconds is None
                else run_age_seconds
            ),
        }
        existing = journal.append("terminal", payload)
    return existing["payload"]


def _public_result(run_id: str, terminal_payload: dict[str, Any]) -> dict[str, Any]:
    return {
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


def _credential_file_path_hash(request: DevRunRequest) -> str | None:
    if request.env_file is None:
        return None
    return sha256_bytes(str(request.env_file.resolve()).encode("utf-8"))


def _sandbox_identity_hash(request: DevRunRequest, package: Any) -> str:
    environment = package.environment if request.provider == "openai" else None
    return sha256_json(
        {
            "backend": "docker" if request.provider == "openai" else "local",
            "evaluator_image": environment.evaluator_image if environment else None,
            "image_digest": environment.image_digest if environment else None,
        }
    )


def _run_envelope(
    *,
    request: DevRunRequest,
    task_dir: Path,
    package: Any,
    run_id: str,
    runtime_hash: str,
    model_hash: str,
    cost_ledger: DevCostLedger | None,
    cost_start_nanos: int,
    created_at: Any | None = None,
) -> DevRunEnvelope:
    return DevRunEnvelope(
        run_id=run_id,
        provider=request.provider,
        task_path=str((task_dir / "public.yaml").resolve()),
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        split=package.public.split,
        base_commit=package.public.repository.base_commit,
        public_spec_hash=package.public_spec_hash,
        private_spec_hash=package.private_spec_hash,
        task_content_hash=package.task_content_hash,
        runtime_hash=runtime_hash,
        model_hash=model_hash,
        sandbox_identity_hash=_sandbox_identity_hash(request, package),
        model=request.model,
        reasoning_effort=request.reasoning_effort,
        credential_file_path_hash=_credential_file_path_hash(request),
        max_cost_nanos=cost_ledger.cap_nanos if cost_ledger else 0,
        cost_start_nanos=cost_start_nanos,
        limits=request.limits,
        sandbox_backend="docker" if request.provider == "openai" else "local",
        evaluator_image_digest=(package.environment.image_digest if package.environment else None),
        created_at=created_at or utc_now(),
    )


def _validate_resume_envelope(actual: DevRunEnvelope, expected: DevRunEnvelope) -> None:
    if actual.model_dump(mode="json") != expected.model_dump(mode="json"):
        raise ResumeContractMismatch("run configuration or runtime changed")


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
            event["event_type"] in {"provider_call_started", "model_call_finished"}
            for event in events
        ),
        tool_actions=sum(
            len(event["payload"].get("tool_calls", []))
            for event in events
            if event["event_type"] == "tool_batch_started"
        ),
        input_count_calls=sum(
            event["event_type"] == "input_count_started" for event in events
        ),
        protocol_recoveries=consecutive_protocol_recoveries,
    )
    action_results: dict[str, DevToolResult] = {}
    for event in events:
        if event["event_type"] == "action_finished":
            result = DevToolResult.model_validate(event["payload"]["result"])
            action_results[result.action_id] = result
        elif event["event_type"] == "tool_batch_finished":
            action_ids = event["payload"].get("action_ids", [])
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
) -> None:
    if results and all(result.tool in {"read_file", "search_files"} for result in results):
        counters.inspection_turns_at_diff += 1
        if counters.failed_mutation_pending:
            counters.failed_mutation_repair_turns += 1
        return
    if len(results) != 1 or results[0].tool != "apply_git_diff":
        return
    if results[0].status == "succeeded":
        counters.inspection_turns_at_diff = 0
        counters.failed_mutation_repair_turns = 0
        counters.failed_mutation_pending = False
    else:
        counters.failed_mutation_repair_turns = 0
        counters.failed_mutation_pending = True


def _validate_resumed_workspace(workspace: Path, journal: DevJournal) -> None:
    summary = WorkspaceManager.diff_summary(workspace)
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
            if result.status == "succeeded" and result.tool == "apply_git_diff":
                expected_diff_hash = str(result.output["worktree_diff_hash"])
    if pending is not None and pending.get("tool") == "apply_git_diff":
        if pending.get("baseline_diff_hash") != expected_diff_hash:
            raise ResumeContractMismatch("pending mutation baseline does not match the journal")
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
                "output_item_count": payload.get("output_item_count", 0),
                "non_tool_output_item_count": payload.get(
                    "non_tool_output_item_count", 0
                ),
                "output_item_types": payload.get("output_item_types", []),
                "output_shape_hash": payload.get("output_shape_hash"),
            },
        )
        return


def _unresolved_decision(
    journal: DevJournal,
) -> tuple[str, list[RequestedTool], str | None, bool, frozenset[str], int] | None:
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
        turn_start = next(
            (
                row
                for row in reversed(events)
                if row["event_type"] == "turn_started"
                and row["payload"].get("turn_id") == turn_id
            ),
            None,
        )
        if turn_start is None:
            raise RecoveryError("recorded model decision has no turn boundary")
        available = turn_start["payload"].get("available_tool_names")
        max_parallel_reads = turn_start["payload"].get("max_parallel_reads")
        if (
            not isinstance(available, list)
            or not all(isinstance(name, str) for name in available)
            or type(max_parallel_reads) is not int
            or max_parallel_reads < 0
        ):
            raise RecoveryError("recorded model decision has no exact tool policy")
        return (
            turn_id,
            calls,
            error_code,
            turn_id in started,
            frozenset(available),
            max_parallel_reads,
        )
    return None


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


def _run_one(
    *,
    request: DevRunRequest,
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
            )
            _validate_resume_envelope(envelope, expected)
            if cost_ledger is not None:
                cost_ledger.restore_settled_usage(
                    journal.provider_usage(),
                    base_spent_nanos=envelope.cost_start_nanos,
                )
            existing_terminal = journal.terminal()
            if existing_terminal is not None:
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


def _run_one_locked(
    *,
    request: DevRunRequest,
    task_dir: Path,
    package: Any,
    state_root: Path,
    pricing: ModelPricing | None,
    cost_ledger: DevCostLedger | None,
    runtime_hash: str,
    model_hash: str,
    run_id: str,
    journal: DevJournal,
    envelope: DevRunEnvelope,
    resuming: bool,
) -> _OneRunResult:
    artifact_store = ArtifactStore(state_root / "artifacts")
    counters = _restore_counters(journal) if resuming else _RunCounters()
    cost_start_nanos = envelope.cost_start_nanos
    hashes = {
        "runtime_hash": runtime_hash,
        "task_hash": package.task_content_hash,
        "model_hash": model_hash,
    }
    workspace_manager = WorkspaceManager(
        repository_root() / "fixtures" / "repositories",
        state_root / "workspaces",
    )
    workspace_path = state_root / "workspaces" / run_id / "repo"
    try:
        if resuming and not workspace_path.exists():
            raise RecoveryError("resumable development workspace is missing")
        workspace = (
            workspace_manager.validate_managed_workspace(workspace_path)
            if workspace_path.exists()
            else workspace_manager.create(
                run_id,
                package.public.repository.url,
                package.public.repository.base_commit,
            )
        )
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
        )
        return _OneRunResult(_public_result(run_id, terminal), False)

    if resuming:
        _validate_resumed_workspace(workspace, journal)
        journal.append(
            "run_resumed",
            {
                "active_elapsed_ms": journal.latest_active_elapsed_ms(),
                "run_age_seconds": max(
                    0,
                    int((utc_now() - envelope.created_at).total_seconds()),
                ),
            },
        )

    api_key: str | None = None
    try:
        if request.provider == "openai":
            assert request.env_file is not None
            api_key = load_exact_openai_api_key(request.env_file)
            sandbox = _live_sandbox_preflight(package)
        else:
            sandbox = LocalSandbox()
    except PatchLoopError as exc:
        terminal = _terminal(
            journal=journal,
            terminal=DevTerminal.PREFLIGHT_FAILED,
            counters=counters,
            cost_ledger=cost_ledger,
            cost_start_nanos=cost_start_nanos,
            hashes=hashes,
            message=str(exc)[:1_000],
        )
        return _OneRunResult(_public_result(run_id, terminal), False)

    gateway = DevToolGateway(
        workspace=workspace,
        public_task=package.public,
        sandbox=sandbox,
        journal=journal,
        limits=request.limits,
    )
    correction: dict[str, str] | None = None
    latest_tool_results = journal.latest_tool_batch_results() if resuming else []
    active_base_ms = journal.latest_active_elapsed_ms() if resuming else 0
    started = monotonic()

    def active_elapsed_ms() -> int:
        return active_base_ms + int((monotonic() - started) * 1_000)

    def remaining_active_seconds() -> float:
        return request.limits.wall_time_seconds - (active_elapsed_ms() / 1_000)

    mock_adapter = MockDevAdapter(package.public.task_id) if request.provider == "mock" else None
    openai_adapter: OpenAIResponsesAdapter | None = None
    if request.provider == "openai":
        assert pricing is not None
        config = ModelConfig(
            provider="openai",
            model_id=request.model,
            reasoning_effort=request.reasoning_effort,
            transport_max_retries=0,
            max_output_tokens=4096,
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
                batch_started,
                pending_allowed_tools,
                pending_max_parallel_reads,
            ) = pending_decision
            if pending_error == "input_token_count_mismatch":
                terminal_code = DevTerminal.PROVIDER_TIMEOUT_OR_UNKNOWN
                terminal_message = "provider usage disagreed with the pre-dispatch input count"
                stop_remaining = True
            elif pending_error is not None:
                if counters.protocol_recoveries >= request.limits.max_protocol_recoveries:
                    terminal_code = DevTerminal.INCOMPLETE_RESPONSE
                    terminal_message = pending_error
                else:
                    counters.protocol_recoveries += 1
                    correction = _protocol_correction(
                        turn_id=pending_turn_id,
                        code=pending_error,
                        issue="Return one valid dev-head tool-call shape.",
                        gateway=gateway,
                    )
                    journal.append("protocol_correction", correction)
            else:
                try:
                    validate_tool_batch(
                        pending_calls,
                        max_parallel_reads=pending_max_parallel_reads,
                        allowed_tools=pending_allowed_tools,
                    )
                except ContractError as exc:
                    if counters.protocol_recoveries >= request.limits.max_protocol_recoveries:
                        terminal_code = DevTerminal.PROTOCOL_VIOLATION
                        terminal_message = str(exc)
                    else:
                        counters.protocol_recoveries += 1
                        correction = _protocol_correction(
                            turn_id=pending_turn_id,
                            code=(
                                "MISSING_REQUIRED_TOOL"
                                if not pending_calls
                                else "INVALID_TOOL_BATCH"
                            ),
                            issue=str(exc),
                            gateway=gateway,
                        )
                        journal.append("protocol_correction", correction)
                else:
                    if not batch_started:
                        if (
                            counters.tool_actions + len(pending_calls)
                            > request.limits.max_tool_actions
                        ):
                            terminal_code = DevTerminal.LIMIT_REACHED
                            terminal_message = "tool-action limit reached before recovered batch"
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
                            recovered_results = gateway.execute_batch(pending_calls)
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
                            _update_inspection_counters(counters, recovered_results)
                            counters.protocol_recoveries = 0
                            latest_tool_results = recovered_results
                            if recovered_completion is not None:
                                if recovered_completion.tool == "finish_task":
                                    finish_result = recovered_completion
                                else:
                                    stop_result = recovered_completion
    while terminal_code is None and finish_result is None and stop_result is None:
        if remaining_active_seconds() <= 0:
            terminal_code = DevTerminal.LIMIT_REACHED
            terminal_message = "row wall-time limit reached"
            break
        if counters.model_calls >= request.limits.max_model_calls:
            terminal_code = DevTerminal.LIMIT_REACHED
            terminal_message = "model-call limit reached"
            break
        if counters.tool_actions >= request.limits.max_tool_actions:
            terminal_code = DevTerminal.LIMIT_REACHED
            terminal_message = "tool-action limit reached"
            break
        elapsed_seconds = active_elapsed_ms() / 1_000
        policy = _tool_policy(gateway, counters, request.limits)
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
        )
        context_payload = json.loads(context)
        context_artifact = artifact_store.put_text(context, "application/json")
        model_input = _build_model_input(
            journal=journal,
            context=context,
            latest_tool_results=latest_tool_results,
        )
        model_input_text = canonical_json(model_input)
        model_input_artifact = artifact_store.put_text(model_input_text, "application/json")
        schemas = dev_tool_schemas(
            finish_enabled="finish_task" in policy.allowed_tools,
            check_ids=policy.check_ids,
            allowed_tools=policy.allowed_tools,
        )
        turn_id = f"turn_{uuid.uuid4().hex}"
        journal.append(
            "turn_started",
            {
                "turn_id": turn_id,
                "context_artifact": context_artifact.model_dump(mode="json"),
                "context_hash": context_artifact.content_hash,
                "model_input_artifact": model_input_artifact.model_dump(mode="json"),
                "model_input_hash": model_input_artifact.content_hash,
                "transcript_action_ids": [
                    item["call_id"]
                    for item in model_input
                    if item.get("type") == "function_call_output"
                ],
                "available_tool_names": sorted(policy.allowed_tools),
                "max_parallel_reads": policy.max_parallel_reads,
                "minimum_completion_calls": policy.minimum_completion_calls,
                "projected_span_ids": [
                    span["span_id"]
                    for span in [
                        *context_payload["source_spans"],
                        *[
                            span
                            for result in context_payload["latest_tool_results"]
                            for span in result.get("output", {}).get("spans", [])
                        ],
                    ]
                    if isinstance(span, dict) and isinstance(span.get("span_id"), str)
                ],
                "active_elapsed_ms": int(elapsed_seconds * 1_000),
            },
        )
        correction = None
        if request.provider == "mock":
            assert mock_adapter is not None
            counters.model_calls += 1
            try:
                turn = mock_adapter.next_turn(context, schemas)
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
                request_payload = openai_adapter.request_payload(
                    model_input,
                    schemas,
                    system_prompt=DEV_SYSTEM_PROMPT,
                )
            except Exception as exc:
                terminal_code = DevTerminal.TASK_FAILED
                terminal_message = f"provider request construction failed: {type(exc).__name__}"
                break
            request_payload["parallel_tool_calls"] = True
            request_payload["tool_choice"] = "required"
            count_id = f"count_{uuid.uuid4().hex}"
            journal.append(
                "input_count_started",
                {
                    "count_id": count_id,
                    "turn_id": turn_id,
                    "request_hash": sha256_json(request_payload),
                    "active_elapsed_ms": active_elapsed_ms(),
                },
            )
            counters.input_count_calls += 1
            try:
                count_timeout = remaining_active_seconds()
                if count_timeout <= 0:
                    terminal_code = DevTerminal.LIMIT_REACHED
                    terminal_message = "row wall-time limit reached before input counting"
                    break
                input_tokens = openai_adapter.count_input_tokens_v2(
                    request_payload,
                    timeout_seconds=count_timeout,
                )
            except Exception as exc:  # provider timeout/transport state is intentionally opaque
                terminal_code = DevTerminal.COUNT_TIMEOUT_OR_UNKNOWN
                terminal_message = f"input count failed: {type(exc).__name__}"
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
            admission = cost_ledger.admit(input_tokens)
            if admission is None:
                terminal_code = DevTerminal.COST_CAP_REACHED
                terminal_message = "minimum provider request cannot fit the remaining cap"
                stop_remaining = True
                break
            request_payload["max_output_tokens"] = admission.output_ceiling
            call_id = f"call_{uuid.uuid4().hex}"
            journal.append(
                "provider_call_started",
                {
                    "call_id": call_id,
                    "turn_id": turn_id,
                    "request_hash": sha256_json(request_payload),
                    "input_tokens": input_tokens,
                    "output_ceiling": admission.output_ceiling,
                    "reserved_cost_nanos": admission.reserved_cost_nanos,
                    "active_elapsed_ms": active_elapsed_ms(),
                },
            )
            counters.model_calls += 1
            try:
                dispatch_timeout = remaining_active_seconds()
                if dispatch_timeout <= 0:
                    terminal_code = DevTerminal.LIMIT_REACHED
                    terminal_message = "row wall-time limit reached before provider dispatch"
                    break
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
            turn = _turn_from_openai(raw_turn)
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
            journal.append(
                "provider_call_finished",
                {
                    "call_id": call_id,
                    "turn_id": turn_id,
                    "response_id": turn.response_id,
                    "response_model": turn.response_model,
                    "response_status": turn.response_status,
                    "input_tokens": turn.input_tokens,
                    "cached_input_tokens": turn.cached_input_tokens,
                    "output_tokens": turn.output_tokens,
                    "reasoning_output_tokens": turn.reasoning_output_tokens,
                    "cost_nanos": cost_nanos,
                    "tool_calls": [call.model_dump(mode="json") for call in turn.tool_calls],
                    "error_code": turn.error_code,
                    "output_item_count": turn.output_item_count,
                    "non_tool_output_item_count": turn.non_tool_output_item_count,
                    "output_item_types": turn.output_item_types,
                    "output_shape_hash": turn.output_shape_hash,
                    "active_elapsed_ms": active_elapsed_ms(),
                },
            )
        journal.append(
            "turn_decision_recorded",
            {
                "turn_id": turn_id,
                "tool_calls": [call.model_dump(mode="json") for call in turn.tool_calls],
                "error_code": turn.error_code,
                "output_item_count": turn.output_item_count,
                "non_tool_output_item_count": turn.non_tool_output_item_count,
                "output_item_types": turn.output_item_types,
                "output_shape_hash": turn.output_shape_hash,
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
                terminal_message = "provider usage disagreed with the pre-dispatch input count"
                stop_remaining = True
                break
        if turn.error_code is not None:
            if counters.protocol_recoveries >= request.limits.max_protocol_recoveries:
                terminal_code = DevTerminal.INCOMPLETE_RESPONSE
                terminal_message = turn.error_code
                break
            counters.protocol_recoveries += 1
            correction = _protocol_correction(
                turn_id=turn_id,
                code=turn.error_code,
                issue="Return one valid dev-head tool-call shape.",
                gateway=gateway,
            )
            journal.append("protocol_correction", correction)
            continue
        try:
            validate_tool_batch(
                turn.tool_calls,
                max_parallel_reads=policy.max_parallel_reads,
                allowed_tools=policy.allowed_tools,
            )
        except ContractError as exc:
            if counters.protocol_recoveries >= request.limits.max_protocol_recoveries:
                terminal_code = DevTerminal.PROTOCOL_VIOLATION
                terminal_message = str(exc)
                break
            counters.protocol_recoveries += 1
            correction = _protocol_correction(
                turn_id=turn_id,
                code="MISSING_REQUIRED_TOOL" if not turn.tool_calls else "INVALID_TOOL_BATCH",
                issue=str(exc),
                gateway=gateway,
            )
            journal.append("protocol_correction", correction)
            continue
        if counters.tool_actions + len(turn.tool_calls) > request.limits.max_tool_actions:
            terminal_code = DevTerminal.LIMIT_REACHED
            terminal_message = "tool-action limit reached"
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
            results = gateway.execute_batch(turn.tool_calls)
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
        _update_inspection_counters(counters, results)
        counters.protocol_recoveries = 0
        if batch_completion is not None:
            if batch_completion.tool == "finish_task":
                finish_result = batch_completion
            else:
                stop_result = batch_completion
        latest_tool_results = results

    if stop_result is not None:
        terminal = _terminal(
            journal=journal,
            terminal=DevTerminal.AGENT_STOPPED,
            counters=counters,
            cost_ledger=cost_ledger,
            cost_start_nanos=cost_start_nanos,
            hashes=hashes,
            message=(
                f"{stop_result.output['reason_code']}: {stop_result.output['summary']}"
            ),
            active_elapsed_ms=active_elapsed_ms(),
        )
        return _OneRunResult(_public_result(run_id, terminal), False)

    if finish_result is None:
        terminal = _terminal(
            journal=journal,
            terminal=terminal_code or DevTerminal.TASK_FAILED,
            counters=counters,
            cost_ledger=cost_ledger,
            cost_start_nanos=cost_start_nanos,
            hashes=hashes,
            message=terminal_message,
            active_elapsed_ms=active_elapsed_ms(),
        )
        return _OneRunResult(_public_result(run_id, terminal), stop_remaining)

    patch = finish_result.output["patch"]
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
        )
        evaluator_summary = _evaluator_summary(evaluation)
        terminal_code = (
            DevTerminal.EVALUATOR_PASS
            if evaluator_summary["task_acceptance"] == "PASS"
            else DevTerminal.EVALUATOR_FAIL
        )
    except Exception as exc:
        evaluator_summary = {
            "task_acceptance": "ERROR",
            "safety_state": "ERROR",
            "failure_class": "EVALUATOR_INFRA_FAILURE",
            "claim_eligible": False,
        }
        terminal_code = DevTerminal.EVALUATOR_ERROR
        terminal_message = f"isolated evaluator failed: {type(exc).__name__}"
    evaluator_hash = sha256_json(evaluator_summary)
    evaluator_summary_artifact = artifact_store.put_json(evaluator_summary)
    evaluator_provenance_path = run_artifact_dir / "provenance.json"
    evaluator_provenance_hash = None
    if evaluator_provenance_path.is_file() and not evaluator_provenance_path.is_symlink():
        evaluator_provenance = artifact_store.put_bytes(
            evaluator_provenance_path.read_bytes(),
            "application/json",
        )
        evaluator_provenance_hash = evaluator_provenance.content_hash
    journal.append(
        "evaluator_finished",
        {
            "summary": evaluator_summary,
            "summary_hash": evaluator_hash,
            "agent_context_reinjected": False,
        },
    )
    terminal_provenance = artifact_store.put_json(
        {
            "schema_version": "dev-terminal-provenance-v1",
            "official": False,
            "terminal": terminal_code.value,
            "manifest_content_hash": manifest_artifact.content_hash,
            "submitted_patch_content_hash": submitted.content_hash,
            "evaluator_summary_hash": evaluator_hash,
            "evaluator_provenance_content_hash": evaluator_provenance_hash,
            "runtime_content_hash": runtime_hash,
            "task_content_hash": package.task_content_hash,
            "model_hash": model_hash,
        }
    )
    artifact_store.write_bytes_atomic(
        run_artifact_dir / "terminal-provenance.json",
        artifact_store.read_bytes(terminal_provenance),
    )
    terminal = _terminal(
        journal=journal,
        terminal=terminal_code,
        counters=counters,
        cost_ledger=cost_ledger,
        cost_start_nanos=cost_start_nanos,
        hashes=hashes,
        evaluator=evaluator_summary,
        artifacts={
            "submitted_patch": submitted.content_hash,
            "manifest": manifest_artifact.content_hash,
            "evaluator_summary": evaluator_summary_artifact.content_hash,
            "terminal_provenance": terminal_provenance.content_hash,
            **(
                {"evaluator_provenance": evaluator_provenance_hash}
                if evaluator_provenance_hash is not None
                else {}
            ),
        },
        message=terminal_message,
        active_elapsed_ms=active_elapsed_ms(),
    )
    return _OneRunResult(_public_result(run_id, terminal), False)


def run_dev(request: DevRunRequest) -> dict[str, Any]:
    """Run 1-6 unofficial repetitions under one explicit invocation cap."""

    if not isinstance(request, DevRunRequest):
        try:
            request = DevRunRequest.model_validate(request)
        except ValidationError as exc:
            raise ContractError(str(exc)) from exc
    task_dir, package = _resolve_task_file(request.task)
    state_root = request.state_root.resolve() if request.state_root else default_state_root()
    repo = repository_root().resolve()
    if state_root == repo or state_root.is_relative_to(repo):
        raise ContractError("development run state must be outside the PatchLoop repository")
    state_root.mkdir(parents=True, exist_ok=True)

    pricing: ModelPricing | None = None
    cost_ledger: DevCostLedger | None = None
    if request.provider == "openai":
        _live_task_is_admitted(task_dir, package)
        _live_source_preflight(task_dir, package)
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
    }
