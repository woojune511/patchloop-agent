"""Read-only budget-pressure diagnostics derived from durable run evidence."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from patchloop.contracts import EventType, RunEvent, RunManifest, RunResult
from patchloop.state import StateStore

BudgetInput = RunManifest | Mapping[str, Any]
EventInput = RunEvent | Mapping[str, Any]
ResultInput = RunResult | Mapping[str, Any] | None


def _mapping(value: Any, *, label: str) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(mode="json")
        if isinstance(dumped, Mapping):
            return dumped
    raise TypeError(f"{label} must be a mapping or Pydantic model")


def _optional_nonnegative_int(value: Any, *, label: str) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a nonnegative integer or null")
    return value


def _required_nonnegative_int(value: Any, *, label: str) -> int:
    parsed = _optional_nonnegative_int(value, label=label)
    if parsed is None:
        raise ValueError(f"{label} must be a nonnegative integer")
    return parsed


def _event_type(event: Mapping[str, Any]) -> str:
    event_type = event.get("type")
    if isinstance(event_type, EventType):
        return event_type.value
    return str(event_type)


def _event_sequence(event: Mapping[str, Any]) -> int:
    return _required_nonnegative_int(
        event.get("sequence"),
        label="event.sequence",
    )


def _payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = event.get("payload", {})
    if not isinstance(payload, Mapping):
        raise ValueError("event.payload must be a mapping")
    return payload


def _usage_from_events(events: Sequence[Mapping[str, Any]]) -> dict[str, int | None]:
    input_tokens = 0
    output_tokens = 0
    model_calls = 0
    tool_calls = 0
    for event in events:
        event_type = _event_type(event)
        payload = _payload(event)
        if event_type == EventType.MODEL_CALLED.value:
            input_tokens += _required_nonnegative_int(
                payload.get("input_tokens"),
                label="ModelCalled.input_tokens",
            )
            output_tokens += _required_nonnegative_int(
                payload.get("output_tokens"),
                label="ModelCalled.output_tokens",
            )
            model_calls += 1
        elif event_type == EventType.TOOL_CALLED.value:
            tool_calls += 1
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "model_calls": model_calls,
        "tool_calls": tool_calls,
        "wall_clock_ms": None,
    }


def _observed_usage(
    events: Sequence[Mapping[str, Any]],
    result: ResultInput,
) -> dict[str, int | None]:
    fallback = _usage_from_events(events)
    if result is None:
        return fallback
    result_payload = _mapping(result, label="result")
    usage = result_payload.get("usage")
    if not isinstance(usage, Mapping):
        return fallback
    parsed: dict[str, int | None] = {}
    for field in (
        "input_tokens",
        "output_tokens",
        "model_calls",
        "tool_calls",
        "wall_clock_ms",
    ):
        parsed[field] = _required_nonnegative_int(
            usage.get(field),
            label=f"result.usage.{field}",
        )
    parsed["total_tokens"] = int(parsed["input_tokens"] or 0) + int(parsed["output_tokens"] or 0)
    return parsed


def _context_tail_snapshot(
    event: Mapping[str, Any],
    *,
    max_total_tokens: int,
) -> dict[str, Any] | None:
    payload = _payload(event)
    reasons = payload.get("investigation_tail_block_reasons")
    if not isinstance(reasons, list) or "token_tail_reserved" not in reasons:
        return None
    remaining = _required_nonnegative_int(
        payload.get("investigation_tail_remaining_tokens"),
        label="ContextBuilt.investigation_tail_remaining_tokens",
    )
    reserved = _required_nonnegative_int(
        payload.get("investigation_tail_reserved_tokens"),
        label="ContextBuilt.investigation_tail_reserved_tokens",
    )
    return _tail_snapshot(
        event,
        source_event_type=EventType.CONTEXT_BUILT.value,
        projection_stage="pre_generation",
        tokens_used=max_total_tokens - remaining,
        remaining_tokens=remaining,
        reserved_tokens=reserved,
        projected_next_input_tokens=_optional_nonnegative_int(
            payload.get("investigation_tail_projected_next_input_tokens"),
            label="ContextBuilt.investigation_tail_projected_next_input_tokens",
        ),
        projected_model_turns=_optional_nonnegative_int(
            payload.get("investigation_tail_projected_model_turns"),
            label="ContextBuilt.investigation_tail_projected_model_turns",
        ),
    )


def _blocked_tool_tail_snapshot(
    event: Mapping[str, Any],
) -> dict[str, Any] | None:
    payload = _payload(event)
    reasons = payload.get("reason_codes")
    if not isinstance(reasons, list) or "token_tail_reserved" not in reasons:
        return None
    tail_policy = payload.get("tail_policy")
    if not isinstance(tail_policy, Mapping):
        raise ValueError("ToolAdmissionBlocked.tail_policy must be a mapping")
    projection = tail_policy.get("token_projection")
    if not isinstance(projection, Mapping):
        raise ValueError("ToolAdmissionBlocked.tail_policy.token_projection must be a mapping")
    return _tail_snapshot(
        event,
        source_event_type=EventType.TOOL_ADMISSION_BLOCKED.value,
        projection_stage=str(tail_policy.get("projection_stage", "post_generation")),
        tokens_used=_required_nonnegative_int(
            projection.get("total_tokens_used"),
            label="ToolAdmissionBlocked.total_tokens_used",
        ),
        remaining_tokens=_required_nonnegative_int(
            projection.get("remaining_tokens"),
            label="ToolAdmissionBlocked.remaining_tokens",
        ),
        reserved_tokens=_required_nonnegative_int(
            projection.get("reserved_tokens"),
            label="ToolAdmissionBlocked.reserved_tokens",
        ),
        projected_next_input_tokens=_optional_nonnegative_int(
            projection.get("projected_next_input_tokens"),
            label="ToolAdmissionBlocked.projected_next_input_tokens",
        ),
        projected_model_turns=_optional_nonnegative_int(
            projection.get("projected_model_turns"),
            label="ToolAdmissionBlocked.projected_model_turns",
        ),
    )


def _tail_snapshot(
    event: Mapping[str, Any],
    *,
    source_event_type: str,
    projection_stage: str,
    tokens_used: int,
    remaining_tokens: int,
    reserved_tokens: int,
    projected_next_input_tokens: int | None,
    projected_model_turns: int | None,
) -> dict[str, Any]:
    additional = max(0, reserved_tokens - remaining_tokens + 1)
    return {
        "sequence": _event_sequence(event),
        "source_event_type": source_event_type,
        "projection_stage": projection_stage,
        "tokens_used": tokens_used,
        "remaining_tokens": remaining_tokens,
        "reserved_tokens": reserved_tokens,
        "projected_next_input_tokens": projected_next_input_tokens,
        "projected_model_turns": projected_model_turns,
        "additional_tokens_to_reopen": additional,
        "minimum_total_budget_to_keep_exploration_open_same_prefix": (
            tokens_used + reserved_tokens + 1
        ),
    }


def _exact_request_diagnostic(
    payload: Mapping[str, Any],
    *,
    sequence: int | None,
    max_total_tokens: int,
) -> dict[str, Any]:
    requested = _required_nonnegative_int(
        payload.get("requested_input_tokens"),
        label="ModelGenerationBlocked.requested_input_tokens",
    )
    allowance = _required_nonnegative_int(
        payload.get("max_output_tokens"),
        label="ModelGenerationBlocked.max_output_tokens",
    )
    remaining = _required_nonnegative_int(
        payload.get("remaining_tokens"),
        label="ModelGenerationBlocked.remaining_tokens",
    )
    required = requested + allowance
    tokens_used = max_total_tokens - remaining
    return {
        "blocked": True,
        "sequence": sequence,
        "requested_input_tokens": requested,
        "max_output_tokens": allowance,
        "required_tokens": required,
        "remaining_tokens": remaining,
        "deficit_tokens": max(0, required - remaining),
        "minimum_total_budget_same_prefix": tokens_used + required,
    }


def _observed_prefix_minimum(
    events: Sequence[Mapping[str, Any]],
    *,
    max_output_tokens: int,
) -> int:
    cumulative = 0
    required_budget = 0
    for event in events:
        payload = _payload(event)
        event_type = _event_type(event)
        if event_type == EventType.MODEL_CALLED.value:
            requested = payload.get("requested_input_tokens")
            if requested is None:
                requested = payload.get("input_tokens")
            requested_tokens = _required_nonnegative_int(
                requested,
                label="ModelCalled.requested_input_tokens",
            )
            required_budget = max(
                required_budget,
                cumulative + requested_tokens + max_output_tokens,
            )
            cumulative += _required_nonnegative_int(
                payload.get("input_tokens"),
                label="ModelCalled.input_tokens",
            ) + _required_nonnegative_int(
                payload.get("output_tokens"),
                label="ModelCalled.output_tokens",
            )
        elif (
            event_type == EventType.MODEL_GENERATION_BLOCKED.value
            and payload.get("reason_code") == "exact_request_budget_exceeded"
        ):
            requested_tokens = _required_nonnegative_int(
                payload.get("requested_input_tokens"),
                label="ModelGenerationBlocked.requested_input_tokens",
            )
            allowance = _required_nonnegative_int(
                payload.get("max_output_tokens"),
                label="ModelGenerationBlocked.max_output_tokens",
            )
            required_budget = max(
                required_budget,
                cumulative + requested_tokens + allowance,
            )
    return required_budget


def _binding_dimension(reason_code: str | None) -> str:
    return {
        "exact_request_budget_exceeded": "total_tokens",
        "token_budget_exhausted": "total_tokens",
        "model_call_budget_exhausted": "model_calls",
        "tool_call_budget_exhausted": "tool_calls",
        "wall_clock_budget_exhausted": "wall_clock",
    }.get(reason_code, "none" if reason_code is None else "unknown")


def _result_terminal_details(result: ResultInput) -> Mapping[str, Any] | None:
    if result is None:
        return None
    terminal_error = _mapping(result, label="result").get("terminal_error")
    if not isinstance(terminal_error, Mapping):
        return None
    details = terminal_error.get("details")
    return details if isinstance(details, Mapping) else None


def calculate_budget_pressure(
    manifest: BudgetInput,
    events: Sequence[EventInput],
    result: ResultInput = None,
) -> dict[str, Any]:
    """Derive a deterministic budget diagnostic without mutating run state."""

    manifest_payload = _mapping(manifest, label="manifest")
    run_id = manifest_payload.get("run_id")
    if not isinstance(run_id, str):
        raise ValueError("manifest.run_id must be a string")
    budget = manifest_payload.get("budget")
    model = manifest_payload.get("model")
    if not isinstance(budget, Mapping) or not isinstance(model, Mapping):
        raise ValueError("manifest budget and model must be mappings")
    limits = {
        "model_calls": _optional_nonnegative_int(
            budget.get("max_model_calls"), label="budget.max_model_calls"
        ),
        "tool_calls": _optional_nonnegative_int(
            budget.get("max_tool_calls"), label="budget.max_tool_calls"
        ),
        "total_tokens": _required_nonnegative_int(
            budget.get("max_total_tokens"), label="budget.max_total_tokens"
        ),
        "wall_clock_ms": _required_nonnegative_int(
            budget.get("wall_clock_timeout_seconds"),
            label="budget.wall_clock_timeout_seconds",
        )
        * 1000,
    }
    call_limits_disabled = bool(
        limits["model_calls"] is None or limits["tool_calls"] is None
    )
    if call_limits_disabled:
        try:
            exact_manifest = RunManifest.model_validate(manifest_payload)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "disabled model/tool call limits require the exact workflow "
                "completion probe or D-081 generic readiness observability contract"
            ) from exc
        workflow_completion_probe = bool(
            exact_manifest.experiment is not None
            and exact_manifest.experiment.purpose.value
            == "workflow-completion-probe"
            and exact_manifest.experiment.experiment_id
            == "pyfakefs-workflow-completion-probe-v2v5-20260803-r1"
            and limits["model_calls"] is None
            and limits["tool_calls"] is None
            and limits["total_tokens"] == 3_000_000
            and limits["wall_clock_ms"] == 7_200_000
        )
        generic_count_observability = bool(
            exact_manifest.experiment is not None
            and exact_manifest.experiment.purpose.value
            == "generic-baseline-readiness"
            and exact_manifest.experiment.experiment_id
            == "generic-baseline-readiness-v2v5-20260803-r3"
            and limits["model_calls"] is None
            and limits["tool_calls"] is None
            and limits["total_tokens"] == 2_400_000
            and limits["wall_clock_ms"] == 1_800_000
        )
        if not (workflow_completion_probe or generic_count_observability):
            raise ValueError(
                "disabled model/tool call limits require the exact workflow "
                "completion probe or D-081 generic readiness observability contract"
            )
    max_output_tokens = _required_nonnegative_int(
        model.get("max_output_tokens"),
        label="model.max_output_tokens",
    )
    if call_limits_disabled and not (
        model.get("model_id") == "gpt-5.4-mini-2026-03-17"
        and max_output_tokens == 25_000
    ):
        raise ValueError(
            "observability diagnostics require the exact model and output allowance"
        )
    event_payloads = [_mapping(event, label="event") for event in events]
    for event in event_payloads:
        event_run_id = event.get("run_id")
        if event_run_id is not None and event_run_id != run_id:
            raise ValueError("event run_id does not match manifest.run_id")
    if result is not None:
        result_payload = _mapping(result, label="result")
        if result_payload.get("run_id") != run_id:
            raise ValueError("result run_id does not match manifest.run_id")

    usage = _observed_usage(event_payloads, result)
    headroom = {
        dimension: (
            limit - int(usage[dimension])
            if limit is not None and usage.get(dimension) is not None
            else None
        )
        for dimension, limit in limits.items()
    }

    blocked_tools = [
        event
        for event in event_payloads
        if _event_type(event) == EventType.TOOL_ADMISSION_BLOCKED.value
    ]
    reasons: Counter[str] = Counter()
    tools: Counter[str] = Counter()
    for event in blocked_tools:
        payload = _payload(event)
        reason_codes = payload.get("reason_codes", [])
        if isinstance(reason_codes, list):
            reasons.update(str(reason) for reason in reason_codes)
        tool = payload.get("tool")
        if isinstance(tool, str):
            tools[tool] += 1

    tail_snapshots: list[dict[str, Any]] = []
    for event in event_payloads:
        event_type = _event_type(event)
        snapshot = None
        if event_type == EventType.CONTEXT_BUILT.value:
            snapshot = _context_tail_snapshot(
                event,
                max_total_tokens=limits["total_tokens"],
            )
        elif event_type == EventType.TOOL_ADMISSION_BLOCKED.value:
            snapshot = _blocked_tool_tail_snapshot(event)
        if snapshot is not None:
            tail_snapshots.append(snapshot)
    tail_snapshots.sort(key=lambda item: item["sequence"])
    maximum_tail = max(
        tail_snapshots,
        key=lambda item: (
            item["additional_tokens_to_reopen"],
            item["sequence"],
        ),
        default=None,
    )

    generation_blocks = [
        event
        for event in event_payloads
        if _event_type(event) == EventType.MODEL_GENERATION_BLOCKED.value
    ]
    terminal_block = generation_blocks[-1] if generation_blocks else None
    result_terminal_details = _result_terminal_details(result)
    terminal_reason_value = (
        _payload(terminal_block).get("reason_code")
        if terminal_block is not None
        else (
            result_terminal_details.get("reason_code")
            if result_terminal_details is not None
            else None
        )
    )
    terminal_reason = str(terminal_reason_value) if terminal_reason_value is not None else None
    exact_blocks = [
        event
        for event in generation_blocks
        if _payload(event).get("reason_code") == "exact_request_budget_exceeded"
    ]
    exact_event = exact_blocks[-1] if exact_blocks else None
    exact_payload = (
        _payload(exact_event)
        if exact_event is not None
        else (
            result_terminal_details
            if result_terminal_details is not None
            and result_terminal_details.get("reason_code") == "exact_request_budget_exceeded"
            else None
        )
    )
    exact_request = (
        _exact_request_diagnostic(
            exact_payload,
            sequence=(_event_sequence(exact_event) if exact_event is not None else None),
            max_total_tokens=limits["total_tokens"],
        )
        if exact_payload is not None
        else {
            "blocked": False,
            "sequence": None,
            "requested_input_tokens": None,
            "max_output_tokens": max_output_tokens,
            "required_tokens": None,
            "remaining_tokens": None,
            "deficit_tokens": 0,
            "minimum_total_budget_same_prefix": None,
        }
    )
    observed_minimum = _observed_prefix_minimum(
        event_payloads,
        max_output_tokens=max_output_tokens,
    )
    exact_request["observed_prefix_minimum_total_budget"] = max(
        observed_minimum,
        int(exact_request["minimum_total_budget_same_prefix"] or 0),
    )

    return {
        "schema_version": "budget-pressure-v1",
        "run_id": run_id,
        "configured_limits": limits,
        "observed_usage": usage,
        "headroom": headroom,
        "binding_dimension": _binding_dimension(terminal_reason),
        "binding_reason": terminal_reason,
        "blocked_tool_count": len(blocked_tools),
        "blocked_tool_counts_by_reason": dict(sorted(reasons.items())),
        "blocked_tool_counts_by_tool": dict(sorted(tools.items())),
        "token_tail": {
            "triggered": bool(tail_snapshots),
            "snapshot_count": len(tail_snapshots),
            "first": tail_snapshots[0] if tail_snapshots else None,
            "maximum": maximum_tail,
        },
        "exact_request": exact_request,
        "counterfactual_same_prefix_only": True,
    }


def derive_experiment_budget_pressure(
    experiment_result: Mapping[str, Any] | str | Path,
    state: StateStore,
) -> dict[str, Any]:
    """Read an experiment result and derive diagnostics from its StateStore."""

    if isinstance(experiment_result, (str, Path)):
        source = Path(experiment_result)
        payload = json.loads(source.read_text(encoding="utf-8"))
    else:
        payload = dict(experiment_result)
    runs = payload.get("runs")
    if not isinstance(runs, list):
        raise ValueError("experiment result must contain a runs list")

    diagnostics = []
    for row in runs:
        if not isinstance(row, Mapping):
            raise ValueError("experiment run row must be a mapping")
        run_id = row.get("run_id")
        if not isinstance(run_id, str):
            continue
        diagnostic = calculate_budget_pressure(
            state.get_manifest(run_id),
            state.list_events(run_id),
            row.get("result"),
        )
        diagnostics.append(
            {
                "order": row.get("order"),
                "task_id": row.get("task_id"),
                "run_id": run_id,
                "diagnostic": diagnostic,
            }
        )

    return {
        "schema_version": "experiment-budget-pressure-v1",
        "experiment_id": payload.get("experiment_id"),
        "execution_hash": payload.get("execution_hash"),
        "run_count": len(diagnostics),
        "runs": diagnostics,
    }
