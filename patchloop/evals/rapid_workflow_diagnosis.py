"""Deterministic, public-only workflow diagnosis for consumed Rapid batches.

The projector reads an immutable Rapid result bundle plus the corresponding
agent-visible event rows from the read-only trace store.  It deliberately does
not read model response text, reasoning text, evaluator artifacts, private task
specifications, or reference patches.  The output contains no timestamps so
the same inputs produce byte-identical evidence.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from decimal import Decimal
from pathlib import Path
from typing import Any

from patchloop.contracts import EventType, PublicTask, RunEvent, RunManifest
from patchloop.errors import ContractError
from patchloop.evals.rapid_batch_driver import (
    RAPID_BATCH_DRIVER_EVENT_SCHEMA,
    RAPID_BATCH_DRIVER_TERMINAL_PARITY_POLICY_VERSION,
)
from patchloop.trace_view import ReadOnlyTraceStore
from patchloop.util import canonical_json, load_unique_yaml, sha256_json

SCHEMA_VERSION = "rapid-workflow-diagnosis-v1"
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_MUTATION_TOOLS = frozenset({"apply_patch", "apply_structured_edit"})
_TERMINAL_TYPES = frozenset({EventType.RUN_COMPLETED, EventType.RUN_FAILED})
_DRIVER_ROW_BINDINGS = (
    ("schedule_order", "order"),
    ("schedule_row_id", "schedule_row_id"),
    ("run_id", "run_id"),
    ("outcome_kind", "outcome_kind"),
    ("model_cost_nanos", "model_cost_nanos"),
)


def _bundle_row_projection(event: dict[str, Any]) -> dict[str, Any]:
    """Return one public row shape from a legacy or terminal-parity bundle event."""

    if event.get("event") != "row-terminal":
        raise ContractError("Rapid diagnosis projection requires one row terminal")
    if event.get("schema_version") != RAPID_BATCH_DRIVER_EVENT_SCHEMA:
        if "projected_row" in event or "projected_row_hash" in event:
            raise ContractError("Rapid diagnosis legacy row has an ambiguous projection")
        return event

    projected = event.get("projected_row")
    if type(projected) is not dict:
        raise ContractError("Rapid diagnosis driver row projection is unavailable")
    if event.get("projected_row_hash") != sha256_json(projected):
        raise ContractError("Rapid diagnosis driver row projection hash differs")
    if any(event.get(source) != projected.get(target) for source, target in _DRIVER_ROW_BINDINGS):
        raise ContractError("Rapid diagnosis driver row projection binding differs")
    if not (
        event.get("official") is False
        and event.get("public_projection_only") is True
        and event.get("projection_matches_result") is True
        and event.get("row_capability_consumed_and_dispatched") is True
        and event.get("terminal_state_atomic") is True
        and event.get("cost_settlement_complete") is True
        and projected.get("bundle_official") is False
        and type(projected.get("runtime_result_official")) is bool
        and type(projected.get("usage")) is dict
        and type(projected.get("order")) is int
        and projected.get("order") > 0
    ):
        raise ContractError("Rapid diagnosis driver row projection is not settled public evidence")
    return dict(projected)


def _file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _load_bundle(path: Path) -> list[dict[str, Any]]:
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("Rapid diagnosis bundle is unavailable or invalid") from exc
    if any(type(item) is not dict for item in rows):
        raise ContractError("Rapid diagnosis bundle event must be an object")
    if len(rows) < 3 or rows[0].get("event") != "batch-started":
        raise ContractError("Rapid diagnosis bundle lacks one batch start")
    if rows[-1].get("event") != "batch-completed":
        raise ContractError("Rapid diagnosis bundle lacks one batch completion")
    previous: str | None = None
    for index, item in enumerate(rows, 1):
        content_hash = item.get("content_hash")
        if not isinstance(content_hash, str) or not _SHA256.fullmatch(content_hash):
            raise ContractError(f"Rapid diagnosis bundle event {index} lacks a content hash")
        body = {key: value for key, value in item.items() if key != "content_hash"}
        if sha256_json(body) != content_hash:
            raise ContractError(f"Rapid diagnosis bundle event {index} content hash differs")
        if item.get("previous_event_hash") != previous:
            raise ContractError(f"Rapid diagnosis bundle event {index} hash chain differs")
        previous = content_hash
    driver_bundle = rows[0].get("schema_version") == RAPID_BATCH_DRIVER_EVENT_SCHEMA
    if driver_bundle:
        if any(
            item.get("schema_version") != RAPID_BATCH_DRIVER_EVENT_SCHEMA
            or item.get("driver_policy_version")
            != RAPID_BATCH_DRIVER_TERMINAL_PARITY_POLICY_VERSION
            for item in rows
        ):
            raise ContractError("Rapid diagnosis driver bundle contract differs")
    elif any(item.get("schema_version") == RAPID_BATCH_DRIVER_EVENT_SCHEMA for item in rows):
        raise ContractError("Rapid diagnosis bundle mixes legacy and driver events")

    terminal_events = [item for item in rows if item.get("event") == "row-terminal"]
    terminal_rows = [_bundle_row_projection(item) for item in terminal_events]
    orders = [item.get("order") for item in terminal_rows]
    if orders != list(range(1, len(terminal_rows) + 1)):
        raise ContractError("Rapid diagnosis row order is not contiguous")
    if len({item.get("run_id") for item in terminal_rows}) != len(terminal_rows):
        raise ContractError("Rapid diagnosis bundle repeats a run ID")
    completed = rows[-1]
    if completed.get("rows_completed") not in {None, len(terminal_rows)}:
        raise ContractError("Rapid diagnosis bundle completion row count differs")
    if driver_bundle and not (
        completed.get("terminal_row_count") == len(terminal_rows)
        and completed.get("not_started_row_count") == 0
        and completed.get("schedule_fully_observed") is True
        and completed.get("cost_fully_settled") is True
        and completed.get("official") is False
    ):
        raise ContractError("Rapid diagnosis driver bundle completion differs")
    return rows


def _load_public_task(path: Path) -> PublicTask:
    try:
        raw = load_unique_yaml(path.read_text(encoding="utf-8"))
        return PublicTask.model_validate(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("Rapid diagnosis public task is unavailable or invalid") from exc


def _validate_events(run_id: str, events: list[RunEvent], task: PublicTask) -> None:
    if not events or [event.sequence for event in events] != list(range(1, len(events) + 1)):
        raise ContractError(f"Rapid diagnosis event sequence differs for {run_id}")
    if any(event.run_id != run_id for event in events):
        raise ContractError(f"Rapid diagnosis event run binding differs for {run_id}")
    if len({event.event_id for event in events}) != len(events):
        raise ContractError(f"Rapid diagnosis event identity repeats for {run_id}")
    if sum(event.type == EventType.RUN_STARTED for event in events) != 1:
        raise ContractError(f"Rapid diagnosis run start count differs for {run_id}")
    terminals = [event for event in events if event.type in _TERMINAL_TYPES]
    if len(terminals) != 1 or terminals[0] is not events[-1]:
        raise ContractError(f"Rapid diagnosis terminal sequence differs for {run_id}")
    check_ids = {check.id for check in task.visible_checks}
    for event in events:
        diff_hash = event.payload.get("worktree_diff_hash")
        if diff_hash is not None and (
            not isinstance(diff_hash, str) or not _SHA256.fullmatch(diff_hash)
        ):
            raise ContractError(f"Rapid diagnosis diff hash differs at {run_id}:{event.sequence}")
        if event.payload.get("tool") == "run_check":
            check_id = event.payload.get("check_id")
            if check_id is not None and check_id not in check_ids:
                raise ContractError(
                    f"Rapid diagnosis check ID differs at {run_id}:{event.sequence}"
                )


def _artifact_json(
    event: RunEvent,
    *,
    state_path: Path,
    field: str,
) -> dict[str, Any] | None:
    ref = event.payload.get(field)
    if not isinstance(ref, dict):
        return None
    raw_path = ref.get("path")
    digest = ref.get("content_hash")
    if not isinstance(raw_path, str) or not isinstance(digest, str):
        raise ContractError(f"Rapid diagnosis artifact reference differs at {event.sequence}")
    if not _SHA256.fullmatch(digest):
        raise ContractError(f"Rapid diagnosis artifact hash differs at {event.sequence}")
    artifact_root = (state_path.parent / "artifacts" / "objects" / "sha256").resolve()
    selected = Path(raw_path).resolve()
    if not selected.is_relative_to(artifact_root) or not selected.is_file():
        raise ContractError(f"Rapid diagnosis artifact escapes CAS at {event.sequence}")
    raw = selected.read_bytes()
    if "sha256:" + hashlib.sha256(raw).hexdigest() != digest:
        raise ContractError(f"Rapid diagnosis artifact bytes differ at {event.sequence}")
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ContractError(f"Rapid diagnosis artifact JSON differs at {event.sequence}") from exc
    if type(value) is not dict:
        raise ContractError(f"Rapid diagnosis artifact shape differs at {event.sequence}")
    return value


def _tool_input(event: RunEvent, *, state_path: Path) -> dict[str, Any]:
    value = _artifact_json(event, state_path=state_path, field="input_artifact")
    if value is None:
        return {}
    if value.get("tool") != event.payload.get("tool") or type(value.get("input")) is not dict:
        raise ContractError(f"Rapid diagnosis tool input binding differs at {event.sequence}")
    return value["input"]


def _request_target(event: RunEvent, *, state_path: Path) -> str | None:
    raw_path = event.payload.get("request_artifact_path")
    digest = event.payload.get("request_artifact_hash")
    if not isinstance(raw_path, str) or not isinstance(digest, str):
        return None
    ref_event = event.model_copy(
        update={
            "payload": {
                **event.payload,
                "request_ref": {"path": raw_path, "content_hash": digest},
            }
        }
    )
    value = _artifact_json(ref_event, state_path=state_path, field="request_ref")
    if value is None:
        return None
    evidence = value.get("lean_harness_request")
    if not isinstance(evidence, dict):
        return None
    decision = evidence.get("completion_loop_decision") or evidence.get("workflow_decision")
    if isinstance(decision, dict) and isinstance(decision.get("target"), str):
        return str(decision["target"])
    return None


def _model_cost_nanos(payload: dict[str, Any], manifest: RunManifest) -> int:
    prices = (
        manifest.model.input_price_per_million_usd,
        manifest.model.cached_input_price_per_million_usd,
        manifest.model.cache_write_input_price_per_million_usd,
        manifest.model.output_price_per_million_usd,
    )
    if any(value is None for value in prices):
        return 0
    input_tokens = int(payload.get("input_tokens", 0) or 0)
    cached = min(input_tokens, int(payload.get("cached_input_tokens", 0) or 0))
    cache_write = min(
        input_tokens - cached,
        int(payload.get("cache_write_input_tokens", 0) or 0),
    )
    uncached = input_tokens - cached - cache_write
    output = int(payload.get("output_tokens", 0) or 0)
    usd = (
        Decimal(uncached) * Decimal(str(prices[0]))
        + Decimal(cached) * Decimal(str(prices[1]))
        + Decimal(cache_write) * Decimal(str(prices[2]))
        + Decimal(output) * Decimal(str(prices[3]))
    ) / Decimal(1_000_000)
    nanos = usd * Decimal(1_000_000_000)
    if nanos != nanos.to_integral_value():
        raise ContractError("Rapid diagnosis model cost is not exactly representable")
    return int(nanos)


def _phase_by_sequence(events: Iterable[RunEvent]) -> dict[int, str]:
    phase = "INTAKE"
    output: dict[int, str] = {}
    for event in events:
        if event.type == EventType.PHASE_CHANGED:
            target = event.payload.get("to")
            if not isinstance(target, str):
                raise ContractError("Rapid diagnosis phase transition lacks a target")
            phase = target
        output[event.sequence] = phase
    return output


def _terminal_attribution(events: list[RunEvent]) -> dict[str, Any]:
    terminal = events[-1]
    last_model = next(
        (event for event in reversed(events) if event.type == EventType.MODEL_CALLED),
        None,
    )
    model_error = last_model.payload.get("response_error_code") if last_model else None
    message = terminal.payload.get("message")
    if model_error == "input_token_count_mismatch":
        classification = "harness_runtime_contract_failure"
    elif terminal.payload.get("error_code") == "MODEL_GENERATION_BUDGET_EXCEEDED":
        classification = "token_budget_terminal"
    elif model_error == "incomplete_response":
        classification = "provider_incomplete_terminal"
    elif terminal.payload.get("outcome_kind") == "infrastructure_error":
        classification = "infrastructure_error"
    elif terminal.type == EventType.RUN_COMPLETED:
        classification = "completed"
    else:
        classification = "agent_execution_terminal"
    return {
        "classification": classification,
        "event_sequence": terminal.sequence,
        "event_type": terminal.type.value,
        "error_code": terminal.payload.get("error_code"),
        "model_error_code": model_error,
        "message": message if isinstance(message, str) else None,
    }


def _diagnose_row(
    row: dict[str, Any],
    *,
    store: ReadOnlyTraceStore,
    state_path: Path,
    task: PublicTask,
) -> dict[str, Any]:
    run_id = row.get("run_id")
    if not isinstance(run_id, str):
        raise ContractError("Rapid diagnosis row lacks a run ID")
    events = store.list_events(run_id)
    _validate_events(run_id, events, task)
    manifest = store.get_manifest(run_id)
    if (
        manifest.task_id != task.task_id
        or manifest.task_version != task.task_version
        or manifest.tool_schema_version != row.get("tool_schema_version")
        or manifest.context_policy_version != row.get("context_policy_version")
    ):
        raise ContractError(f"Rapid diagnosis manifest differs for {run_id}")

    phases = _phase_by_sequence(events)
    model_events = [event for event in events if event.type == EventType.MODEL_CALLED]
    tool_calls = [event for event in events if event.type == EventType.TOOL_CALLED]
    mutations = [event for event in events if event.type == EventType.PATCH_APPLIED]
    first_mutation = mutations[0] if mutations else None
    first_mutation_sequence = first_mutation.sequence if first_mutation else None

    phase_targets: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: {
            "model_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "reasoning_output_tokens": 0,
            "cost_nanos": 0,
        }
    )
    for event in model_events:
        target = _request_target(event, state_path=state_path) or "phase-policy"
        key = (phases[event.sequence], target)
        aggregate = phase_targets[key]
        aggregate["model_calls"] += 1
        for field in ("input_tokens", "output_tokens", "reasoning_output_tokens"):
            aggregate[field] += int(event.payload.get(field, 0) or 0)
        aggregate["cost_nanos"] += _model_cost_nanos(event.payload, manifest)

    pre_mutation_calls = [
        event
        for event in tool_calls
        if first_mutation_sequence is None or event.sequence < first_mutation_sequence
    ]
    read_files: list[str] = []
    for event in pre_mutation_calls:
        if event.payload.get("tool") == "read_file":
            path = _tool_input(event, state_path=state_path).get("path")
            if isinstance(path, str) and path not in read_files:
                read_files.append(path)

    edit_calls = [event for event in tool_calls if event.payload.get("tool") in _MUTATION_TOOLS]
    edit_terminals = [
        event
        for event in events
        if event.type in {EventType.TOOL_SUCCEEDED, EventType.TOOL_FAILED}
        and event.payload.get("tool") in _MUTATION_TOOLS
        and not event.payload.get("replayed")
        and not event.payload.get("admission_blocked")
    ]
    failure_signatures = Counter()
    for event in edit_terminals:
        if event.type != EventType.TOOL_FAILED:
            continue
        details = event.payload.get("error_details")
        reason = details.get("reason") if isinstance(details, dict) else None
        failure_signatures[
            ":".join(
                str(value or "unknown")
                for value in (
                    event.payload.get("tool"),
                    event.payload.get("error_code"),
                    reason,
                )
            )
        ] += 1

    check_events = [
        event
        for event in events
        if event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "run_check"
        and event.payload.get("passed") in {True, False}
    ]
    check_order = tuple(check.id for check in task.visible_checks)
    first_check_id = check_order[0]
    upstream_ids = set(check_order[1:])
    by_diff: dict[str, list[RunEvent]] = defaultdict(list)
    for event in check_events:
        diff_hash = event.payload.get("worktree_diff_hash")
        if not isinstance(diff_hash, str):
            raise ContractError(
                f"Rapid diagnosis check lacks a diff hash at {run_id}:{event.sequence}"
            )
        by_diff[diff_hash].append(event)
    upstream_before_target_pass = 0
    for diff_events in by_diff.values():
        target_failed = False
        target_passed = False
        for event in diff_events:
            check_id = event.payload.get("check_id")
            if check_id == first_check_id:
                target_failed = event.payload.get("passed") is False
                target_passed = event.payload.get("passed") is True
            elif check_id in upstream_ids and target_failed and not target_passed:
                upstream_before_target_pass += 1

    correction_episodes: list[dict[str, Any]] = []
    for failed in (event for event in check_events if event.payload.get("passed") is False):
        actions: list[dict[str, Any]] = []
        for later in events:
            if later.sequence <= failed.sequence:
                continue
            if later.type == EventType.TOOL_CALLED:
                actions.append(
                    {
                        "sequence": later.sequence,
                        "tool": later.payload.get("tool"),
                    }
                )
            if later.type == EventType.PATCH_APPLIED:
                break
            if later.type == EventType.TOOL_SUCCEEDED and later.payload.get("tool") == "run_check":
                break
        correction_episodes.append(
            {
                "failed_check_sequence": failed.sequence,
                "check_id": failed.payload.get("check_id"),
                "worktree_diff_hash": failed.payload.get("worktree_diff_hash"),
                "actions": actions,
            }
        )

    diff_events = [
        event
        for event in events
        if event.type == EventType.TOOL_SUCCEEDED and event.payload.get("tool") == "get_diff"
    ]
    finish_attempts = [event for event in events if event.type == EventType.SUBMISSION_ATTEMPTED]
    finish_accepted = [event for event in events if event.type == EventType.SUBMISSION_ACCEPTED]
    terminal = _terminal_attribution(events)
    usage = row.get("usage")
    if not isinstance(usage, dict):
        raise ContractError(f"Rapid diagnosis row usage differs for {run_id}")
    observed_usage = {
        "model_calls": len(model_events),
        "tool_calls": int(usage.get("tool_calls", 0) or 0),
        "input_tokens": sum(
            int(event.payload.get("input_tokens", 0) or 0) for event in model_events
        ),
        "output_tokens": sum(
            int(event.payload.get("output_tokens", 0) or 0) for event in model_events
        ),
        "reasoning_output_tokens": sum(
            int(event.payload.get("reasoning_output_tokens", 0) or 0) for event in model_events
        ),
        "cost_nanos": sum(_model_cost_nanos(event.payload, manifest) for event in model_events),
    }
    for bundle_key, observed_key in (
        ("model_calls", "model_calls"),
        ("input_tokens", "input_tokens"),
        ("output_tokens", "output_tokens"),
        ("reasoning_output_tokens", "reasoning_output_tokens"),
    ):
        if int(usage.get(bundle_key, 0) or 0) != observed_usage[observed_key]:
            raise ContractError(f"Rapid diagnosis usage differs for {run_id}:{bundle_key}")
    if int(row.get("model_cost_nanos", 0) or 0) != observed_usage["cost_nanos"]:
        raise ContractError(f"Rapid diagnosis settled cost differs for {run_id}")

    before_model = [
        event
        for event in model_events
        if first_mutation_sequence is None or event.sequence < first_mutation_sequence
    ]
    result = {
        "order": row["order"],
        "run_id": run_id,
        "variant": row.get("variant"),
        "repetition": row.get("repetition"),
        "outcome_kind": row.get("outcome_kind"),
        "evaluator_reached": row.get("evaluator_reached") is True,
        "submission_completed": row.get("submission_completed") is True,
        "success_at_budget": row.get("success_at_budget") is True,
        "token_terminal": row.get("token_terminal") is True,
        "usage": observed_usage,
        "phase_targets": [
            {"phase": key[0], "target": key[1], **value}
            for key, value in sorted(phase_targets.items())
        ],
        "first_mutation_evidence": {
            "event_sequence": first_mutation_sequence,
            "model_calls": len(before_model),
            "tool_calls": len(pre_mutation_calls),
            "input_tokens": sum(
                int(event.payload.get("input_tokens", 0) or 0) for event in before_model
            ),
            "output_tokens": sum(
                int(event.payload.get("output_tokens", 0) or 0) for event in before_model
            ),
            "cost_nanos": sum(_model_cost_nanos(event.payload, manifest) for event in before_model),
            "search_calls": sum(
                event.payload.get("tool") == "search_files" for event in pre_mutation_calls
            ),
            "read_calls": sum(
                event.payload.get("tool") == "read_file" for event in pre_mutation_calls
            ),
            "check_calls": sum(
                event.payload.get("tool") == "run_check" for event in pre_mutation_calls
            ),
            "read_files": read_files,
        },
        "correction_episodes": correction_episodes,
        "edit_path": {
            "attempts": len(edit_calls),
            "accepted": sum(event.type == EventType.TOOL_SUCCEEDED for event in edit_terminals),
            "rejected": sum(event.type == EventType.TOOL_FAILED for event in edit_terminals),
            "patch_applied": len(mutations),
            "acceptance_rate": (
                (
                    f"{sum(event.type == EventType.TOOL_SUCCEEDED for event in edit_terminals)}"
                    f"/{len(edit_terminals)}"
                )
                if edit_terminals
                else "0/0"
            ),
            "failure_signatures": [
                {"signature": signature, "count": count}
                for signature, count in sorted(failure_signatures.items())
            ],
        },
        "visible_checks": {
            "order": list(check_order),
            "invocations": [
                {
                    "sequence": event.sequence,
                    "check_id": event.payload.get("check_id"),
                    "passed": event.payload.get("passed"),
                    "worktree_diff_hash": event.payload.get("worktree_diff_hash"),
                }
                for event in check_events
            ],
            "passes": sum(event.payload.get("passed") is True for event in check_events),
            "failures": sum(event.payload.get("passed") is False for event in check_events),
            "upstream_before_target_pass": upstream_before_target_pass,
        },
        "review_submission": {
            "get_diff_sequences": [event.sequence for event in diff_events],
            "finish_attempt_sequences": [event.sequence for event in finish_attempts],
            "finish_accepted_sequences": [event.sequence for event in finish_accepted],
            "completed_get_diff_to_finish": bool(
                diff_events
                and finish_accepted
                and finish_accepted[-1].sequence > diff_events[-1].sequence
            ),
        },
        "terminal_attribution": terminal,
        "state_evidence": {
            "event_count": len(events),
            "terminal_sequence": events[-1].sequence,
            "terminal_event_hash": sha256_json(events[-1].model_dump(mode="json")),
        },
    }
    return result


def _observed_batch(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "attempted_rows": len(rows),
        "agent_rows_started": sum(row.get("agent_started") is True for row in rows),
        "harness_admission_failures": sum(
            row.get("harness_admission_failure") is True for row in rows
        ),
        "agent_failures": sum(row.get("outcome_kind") == "agent_failure" for row in rows),
        "evaluator_reached": sum(row.get("evaluator_reached") is True for row in rows),
        "submissions_completed": sum(row.get("submission_completed") is True for row in rows),
        "successes_at_budget": sum(row.get("success_at_budget") is True for row in rows),
        "token_terminals": sum(row.get("token_terminal") is True for row in rows),
        "model_calls": sum(int(row.get("usage", {}).get("model_calls", 0) or 0) for row in rows),
        "tool_calls": sum(int(row.get("usage", {}).get("tool_calls", 0) or 0) for row in rows),
        "model_cost_nanos": sum(int(row.get("model_cost_nanos", 0) or 0) for row in rows),
    }


def build_rapid_workflow_diagnosis(
    *,
    bundle_path: str | Path,
    state_path: str | Path,
    public_task_path: str | Path,
    repository_root: str | Path = ".",
) -> dict[str, Any]:
    """Build one deterministic diagnosis without invoking external systems."""

    root = Path(repository_root).resolve()
    bundle = Path(bundle_path).resolve()
    state = Path(state_path).resolve()
    task_path = Path(public_task_path).resolve()
    if not bundle.is_relative_to(root) or not task_path.is_relative_to(root):
        raise ContractError("Rapid diagnosis inputs must remain inside the repository")
    bundle_events = _load_bundle(bundle)
    task = _load_public_task(task_path)
    bundle_rows = [
        _bundle_row_projection(item)
        for item in bundle_events
        if item.get("event") == "row-terminal"
    ]
    if any(
        row.get("task_id") != task.task_id or row.get("task_version") != task.task_version
        for row in bundle_rows
    ):
        raise ContractError("Rapid diagnosis bundle task binding differs")
    store = ReadOnlyTraceStore(state)
    rows = [
        _diagnose_row(
            row,
            store=store,
            state_path=state,
            task=task,
        )
        for row in bundle_rows
    ]
    observed = _observed_batch(bundle_rows)
    derived = {
        "model_calls": sum(row["usage"]["model_calls"] for row in rows),
        "tool_calls": sum(row["usage"]["tool_calls"] for row in rows),
        "model_cost_nanos": sum(row["usage"]["cost_nanos"] for row in rows),
    }
    if any(observed[key] != value for key, value in derived.items()):
        raise ContractError("Rapid diagnosis bundle and trace totals differ")

    variants: list[dict[str, Any]] = []
    for variant in dict.fromkeys(str(row["variant"]) for row in rows):
        selected = [row for row in rows if row["variant"] == variant]
        edits = sum(row["edit_path"]["attempts"] for row in selected)
        rejected = sum(row["edit_path"]["rejected"] for row in selected)
        variants.append(
            {
                "variant": variant,
                "rows": len(selected),
                "evaluator_reached": sum(row["evaluator_reached"] for row in selected),
                "submissions_completed": sum(row["submission_completed"] for row in selected),
                "successes_at_budget": sum(row["success_at_budget"] for row in selected),
                "model_calls": sum(row["usage"]["model_calls"] for row in selected),
                "tool_calls": sum(row["usage"]["tool_calls"] for row in selected),
                "model_cost_nanos": sum(row["usage"]["cost_nanos"] for row in selected),
                "edit_attempts": edits,
                "edit_rejections": rejected,
                "edit_acceptance_rate": f"{edits - rejected}/{edits}" if edits else "0/0",
                "upstream_before_target_pass": sum(
                    row["visible_checks"]["upstream_before_target_pass"] for row in selected
                ),
                "terminal_attribution": dict(
                    sorted(
                        Counter(
                            row["terminal_attribution"]["classification"] for row in selected
                        ).items()
                    )
                ),
            }
        )

    body = {
        "schema_version": SCHEMA_VERSION,
        "official": False,
        "source_bundle": {
            "path": bundle.relative_to(root).as_posix(),
            "bytes": bundle.stat().st_size,
            "file_sha256": _file_sha256(bundle),
            "execution_hash": bundle_events[0].get("execution_hash"),
            "terminal_content_hash": bundle_events[-1].get("content_hash"),
        },
        "source_trace": {
            "path": state.relative_to(root).as_posix()
            if state.is_relative_to(root)
            else str(state),
            "read_only_immutable_sqlite": True,
            "raw_events_mutated": False,
        },
        "public_task": {
            "path": task_path.relative_to(root).as_posix(),
            "task_id": task.task_id,
            "task_version": task.task_version,
            "public_task_hash": sha256_json(task.model_dump(mode="json")),
            "visible_check_order": [check.id for check in task.visible_checks],
        },
        "evidence_boundary": {
            "private_task_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
            "reasoning_text_read": False,
            "llm_response_text_read": False,
            "provider_calls": 0,
            "docker_calls": 0,
            "evaluator_calls": 0,
            "visible_check_calls": 0,
            "state_mutations": 0,
            "added_cost_nanos": 0,
        },
        "observed_batch": observed,
        "rows": rows,
        "variants": variants,
        "order_preserving_tuple": [
            [
                row["order"],
                row["variant"],
                row["repetition"],
                row["outcome_kind"],
                row["evaluator_reached"],
                row["submission_completed"],
                row["success_at_budget"],
                row["terminal_attribution"]["classification"],
                row["first_mutation_evidence"]["event_sequence"],
                row["edit_path"]["attempts"],
                row["edit_path"]["rejected"],
                row["visible_checks"]["upstream_before_target_pass"],
                row["review_submission"]["completed_get_diff_to_finish"],
            ]
            for row in rows
        ],
    }
    return {**body, "content_hash": sha256_json(body)}


def diagnosis_bytes(value: dict[str, Any]) -> bytes:
    """Return the canonical append-only artifact bytes."""

    if value.get("content_hash") != sha256_json(
        {key: item for key, item in value.items() if key != "content_hash"}
    ):
        raise ContractError("Rapid workflow diagnosis content hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")
