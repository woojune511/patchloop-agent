"""Single mutable PatchLoop development runtime."""

from __future__ import annotations

import os
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
    DevRunRequest,
    DevState,
    DevTerminal,
    DevToolResult,
    RequestedTool,
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
from patchloop.errors import ContractError, PatchLoopError
from patchloop.repository import WorkspaceManager
from patchloop.runtime import git_commit, make_run_id, repository_root
from patchloop.sandbox import DockerSandbox, LocalSandbox
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_json, utc_now
from patchloop.verifier import EvaluationEngine


@dataclass
class _RunCounters:
    model_calls: int = 0
    tool_actions: int = 0
    input_count_calls: int = 0
    protocol_recoveries: int = 0


@dataclass
class _OneRunResult:
    public: dict[str, Any]
    stop_remaining: bool


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
    root = Path(__file__).resolve().parent
    rows = []
    for path in sorted(root.glob("*.py")):
        rows.append({"path": path.name, "sha256": sha256_bytes(path.read_bytes())})
    return sha256_json({"runtime": DEV_RUNTIME_ID, "sources": rows})


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
) -> RunManifest:
    return RunManifest(
        run_id=run_id,
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        base_commit=package.public.repository.base_commit,
        public_spec_hash=package.public_spec_hash,
        private_spec_hash=package.private_spec_hash,
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
        evaluator_image_digest=(package.environment.image_digest if package.environment else None),
        created_at=utc_now(),
    )


def _cards(
    journal: DevJournal,
    correction: dict[str, str] | None,
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


def _build_context(
    *,
    package: Any,
    gateway: DevToolGateway,
    journal: DevJournal,
    correction: dict[str, str] | None,
) -> str:
    summary = gateway.current_diff
    spans = sorted(gateway.spans.values(), key=lambda item: item["span_id"])[-8:]
    payload = {
        "public_task": package.public.model_dump(mode="json"),
        "current_diff": {
            "patch": summary.patch,
            "patch_hash": summary.patch_hash,
            "changed_files": summary.changed_files,
            "added_lines": summary.added_lines,
            "deleted_lines": summary.deleted_lines,
            "truncated": False,
        },
        "source_spans": spans,
        "recent_checks": _recent_checks(gateway),
        "last_successful_mutation": gateway.last_successful_mutation,
        "recent_attempt_result_next_question": _cards(journal, correction),
    }
    # Construction is allowlist-based from ``package.public`` and public tool outputs;
    # private task fields are never accepted as context inputs.
    return canonical_json(payload)


def _turn_from_openai(turn: Any) -> DevModelTurn:
    return DevModelTurn(
        tool_calls=[
            RequestedTool(name=call.name, action_id=call.action_id, arguments=call.arguments)
            for call in turn.tool_calls
        ],
        requested_input_tokens=turn.requested_input_tokens,
        input_tokens=turn.input_tokens,
        cached_input_tokens=turn.cached_input_tokens,
        output_tokens=turn.output_tokens,
        reasoning_output_tokens=turn.reasoning_output_tokens,
        response_id=turn.response_id,
        response_model=turn.response_model,
        response_status=turn.response_status,
        incomplete_reason=turn.response_incomplete_reason,
        error_code=turn.error.code if turn.error else None,
    )


def _attempt_card(result: DevToolResult, gateway: DevToolGateway) -> dict[str, Any]:
    if result.status == "failed":
        return {
            "attempt": result.tool,
            "result": result.error_code or "failed",
            "next_question": (
                "What current public evidence or corrected contract resolves this failure?"
            ),
        }
    if result.tool in {"read_file", "search_files"}:
        return {
            "attempt": result.tool,
            "result": f"recorded {len(result.output.get('spans', []))} source spans",
            "next_question": "Which exact source anchor supports the smallest causal mutation?",
        }
    if result.tool == "apply_patch":
        return {
            "attempt": "mutation",
            "result": result.output["worktree_diff_hash"],
            "next_question": (
                "Which registered visible check most directly tests the expected behavior?"
            ),
        }
    if result.tool == "run_check":
        return {
            "attempt": f"check:{result.output['check_id']}",
            "result": "PASS" if result.output["passed"] else result.output["failure_signature"],
            "next_question": (
                "Submit the projected diff."
                if gateway.visible_checks_pass()
                else "What does this public failure falsify, and what mechanism should change next?"
            ),
        }
    return {
        "attempt": "finish_task",
        "result": result.output.get("patch_hash", "submitted"),
        "next_question": "Run the isolated private evaluator.",
    }


def _transition(journal: DevJournal, current: DevState, target: DevState) -> DevState:
    if target != current:
        journal.append("state_changed", {"from": current.value, "to": target.value})
    return target


def _evaluator_summary(result: Any) -> dict[str, Any]:
    verdicts = result.verdicts
    if result.scope_compliant_success:
        return {"status": "PASS", "failure_class": None}
    if verdicts.scope_policy != VerdictState.PASS:
        failure = "SCOPE_POLICY_FAILED"
    elif verdicts.regression_tests != VerdictState.PASS:
        failure = "PUBLIC_REGRESSION_FAILED"
    elif verdicts.hidden_tests != VerdictState.PASS:
        failure = "PRIVATE_EVALUATION_FAILED"
    elif verdicts.safety_policy != VerdictState.PASS:
        failure = "SAFETY_POLICY_FAILED"
    else:
        failure = "EVALUATION_FAILED"
    return {"status": "FAIL", "failure_class": failure}


def _milestones(journal: DevJournal) -> dict[str, Any]:
    plans: list[dict[str, Any]] = []
    edits: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    submission: dict[str, Any] | None = None
    for event in journal.events():
        if event["event_type"] != "action_finished":
            continue
        result = event["payload"]["result"]
        if result["status"] != "succeeded":
            continue
        output = result["output"]
        if result["tool"] == "apply_patch":
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
    return {"plan": plans, "edit": edits, "check": checks, "submission": submission}


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
            "cost_nanos": (
                cost_ledger.spent_nanos - cost_start_nanos if cost_ledger else 0
            ),
            "evaluator": evaluator,
            "artifact_hashes": artifacts or {},
            "message": message,
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
    }


def _run_one(
    *,
    request: DevRunRequest,
    task_dir: Path,
    package: Any,
    state_root: Path,
    sandbox: Any,
    pricing: ModelPricing | None,
    cost_ledger: DevCostLedger | None,
    api_key: str | None,
    runtime_hash: str,
    model_hash: str,
) -> _OneRunResult:
    run_id = make_run_id("dev")
    journal = DevJournal(state_root, run_id)
    counters = _RunCounters()
    cost_start_nanos = cost_ledger.spent_nanos if cost_ledger else 0
    hashes = {
        "runtime_hash": runtime_hash,
        "task_hash": sha256_json(
            {
                "public": package.public_spec_hash,
                "private": package.private_spec_hash,
            }
        ),
        "model_hash": model_hash,
    }
    journal.append(
        "run_started",
        {
            "runtime": DEV_RUNTIME_ID,
            "provider": request.provider,
            "task_id": package.public.task_id,
            "task_version": package.public.task_version,
            "split": package.public.split,
            **hashes,
        },
    )
    if journal.unresolved_provider_call() is not None:
        terminal = _terminal(
            journal=journal,
            terminal=DevTerminal.PROVIDER_TIMEOUT_OR_UNKNOWN,
            counters=counters,
            cost_ledger=cost_ledger,
            cost_start_nanos=cost_start_nanos,
            hashes=hashes,
            message="an earlier provider dispatch has no durable usage record",
        )
        return _OneRunResult(_public_result(run_id, terminal), True)

    workspace_manager = WorkspaceManager(
        repository_root() / "fixtures" / "repositories",
        state_root / "workspaces",
    )
    workspace_path = state_root / "workspaces" / run_id / "repo"
    try:
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
    state = DevState.WORK
    correction: dict[str, str] | None = None
    started = monotonic()
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
            )
            return _OneRunResult(_public_result(run_id, terminal), False)

    terminal_code: DevTerminal | None = None
    terminal_message: str | None = None
    stop_remaining = False
    finish_result: DevToolResult | None = None
    while terminal_code is None and finish_result is None:
        if monotonic() - started >= request.limits.wall_time_seconds:
            terminal_code = DevTerminal.LIMIT_REACHED
            terminal_message = "row wall-time limit reached"
            break
        if counters.model_calls >= request.limits.max_model_calls:
            terminal_code = DevTerminal.LIMIT_REACHED
            terminal_message = "model-call limit reached"
            break
        context = _build_context(
            package=package,
            gateway=gateway,
            journal=journal,
            correction=correction,
        )
        schemas = dev_tool_schemas(finish_enabled=gateway.visible_checks_pass())
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
                {"provider": "mock", "tool_call_count": len(turn.tool_calls)},
            )
        else:
            assert openai_adapter is not None and cost_ledger is not None
            try:
                request_payload = openai_adapter.request_payload(
                    context,
                    schemas,
                    system_prompt=DEV_SYSTEM_PROMPT,
                )
            except Exception as exc:
                terminal_code = DevTerminal.TASK_FAILED
                terminal_message = f"provider request construction failed: {type(exc).__name__}"
                break
            request_payload["parallel_tool_calls"] = True
            count_id = f"count_{uuid.uuid4().hex}"
            journal.append(
                "input_count_started",
                {"count_id": count_id, "request_hash": sha256_json(request_payload)},
            )
            counters.input_count_calls += 1
            try:
                count_timeout = request.limits.wall_time_seconds - (monotonic() - started)
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
                {"count_id": count_id, "input_tokens": input_tokens},
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
                    "request_hash": sha256_json(request_payload),
                    "input_tokens": input_tokens,
                    "output_ceiling": admission.output_ceiling,
                    "reserved_cost_nanos": admission.reserved_cost_nanos,
                },
            )
            counters.model_calls += 1
            try:
                dispatch_timeout = request.limits.wall_time_seconds - (monotonic() - started)
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
                },
            )
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
                correction = {
                    "code": turn.error_code,
                    "message": "Return one valid dev-head tool-call shape.",
                }
                continue

        try:
            validate_tool_batch(
                turn.tool_calls,
                max_parallel_reads=request.limits.max_parallel_reads,
            )
        except ContractError as exc:
            if counters.protocol_recoveries >= request.limits.max_protocol_recoveries:
                terminal_code = DevTerminal.PROTOCOL_VIOLATION
                terminal_message = str(exc)
                break
            counters.protocol_recoveries += 1
            correction = {
                "code": "INVALID_TOOL_BATCH",
                "message": (
                    "Use up to four reads/searches only, or exactly one check, mutation, or finish."
                ),
            }
            journal.append("protocol_correction", correction)
            continue
        if counters.tool_actions + len(turn.tool_calls) > request.limits.max_tool_actions:
            terminal_code = DevTerminal.LIMIT_REACHED
            terminal_message = "tool-action limit reached"
            break
        counters.tool_actions += len(turn.tool_calls)
        try:
            results = gateway.execute_batch(turn.tool_calls)
        except Exception as exc:
            terminal_code = DevTerminal.TASK_FAILED
            terminal_message = f"tool gateway failed: {type(exc).__name__}"
            break
        for result in results:
            journal.append("attempt_card", _attempt_card(result, gateway))
            if result.tool == "run_check":
                state = _transition(journal, state, DevState.VERIFY)
                state = _transition(
                    journal,
                    state,
                    DevState.REVIEW if gateway.visible_checks_pass() else DevState.WORK,
                )
            elif result.tool == "apply_patch" and result.status == "succeeded":
                state = _transition(journal, state, DevState.WORK)
            elif result.tool == "finish_task" and result.status == "succeeded":
                state = _transition(journal, state, DevState.SUBMITTED)
                finish_result = result
        if all(result.status == "failed" for result in results):
            # Tool-contract failures are recoverable through the normal next model turn.
            correction = {
                "code": results[0].error_code or "TOOL_FAILED",
                "message": results[0].message or "Use current public evidence and retry safely.",
            }

    if finish_result is None:
        terminal = _terminal(
            journal=journal,
            terminal=terminal_code or DevTerminal.TASK_FAILED,
            counters=counters,
            cost_ledger=cost_ledger,
            cost_start_nanos=cost_start_nanos,
            hashes=hashes,
            message=terminal_message,
        )
        return _OneRunResult(_public_result(run_id, terminal), stop_remaining)

    artifact_store = ArtifactStore(state_root / "artifacts")
    patch = finish_result.output["patch"]
    submitted = artifact_store.put_text(patch, "text/x-diff")
    manifest = _manifest(
        request=request,
        package=package,
        run_id=run_id,
        sandbox_backend="docker" if request.provider == "openai" else "local",
        pricing=pricing,
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
        evaluator_hash = sha256_json(evaluator_summary)
        terminal_code = (
            DevTerminal.EVALUATOR_PASS
            if evaluator_summary["status"] == "PASS"
            else DevTerminal.EVALUATOR_FAIL
        )
    except Exception as exc:
        evaluator_summary = {
            "status": "ERROR",
            "failure_class": "EVALUATOR_INFRA_FAILURE",
        }
        evaluator_hash = sha256_json(evaluator_summary)
        terminal_code = DevTerminal.EVALUATOR_ERROR
        terminal_message = f"isolated evaluator failed: {type(exc).__name__}"
    journal.append(
        "evaluator_finished",
        {
            "summary": evaluator_summary,
            "summary_hash": evaluator_hash,
            "agent_context_reinjected": False,
        },
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
            "evaluator_summary": evaluator_hash,
        },
        message=terminal_message,
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
    api_key: str | None = None
    if request.provider == "openai":
        _live_task_is_admitted(task_dir, package)
        assert request.env_file is not None and request.max_cost_usd is not None
        api_key = load_exact_openai_api_key(request.env_file)
        pricing = pricing_for_model(request.model)
        cost_ledger = DevCostLedger(request.max_cost_usd, pricing)
        sandbox = _live_sandbox_preflight(package)
    else:
        sandbox = LocalSandbox()

    runtime_hash = _runtime_hash()
    model_hash = _model_hash(request, pricing)
    results: list[dict[str, Any]] = []
    for _ in range(request.repeat):
        one = _run_one(
            request=request,
            task_dir=task_dir,
            package=package,
            state_root=state_root,
            sandbox=sandbox,
            pricing=pricing,
            cost_ledger=cost_ledger,
            api_key=api_key,
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
