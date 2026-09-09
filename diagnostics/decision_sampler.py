"""Frozen next-action pilot, separate from dev-head. Never execute sampled tools.

Run with ``uv run python -m diagnostics.decision_sampler --help`` from the checkout.
Validation/inspection do not load credentials. Collection requires a new external
root and an explicit six-cell, packet/source/price-bound approval. There is no resume.
"""

from __future__ import annotations

import argparse
import json
import secrets
import uuid
from collections.abc import Callable
from contextlib import suppress
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from time import monotonic

from patchloop.agent.model import OpenAIResponsesAdapter, create_openai_client
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact, ModelConfig
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev.conversation import reconstruct_state, validate_model_input
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.dev.runner import (
    _load_provider_continuation,
    _store_provider_continuation,
    _turn_from_openai,
    _validate_continuation_action_order,
)
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas, validate_tool_batch
from patchloop.environment import load_exact_openai_api_key
from patchloop.errors import ContractError
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text

MODEL = "gpt-5.4-mini-2026-03-17"
ORDER = (("C1", "A"), ("C1", "B"), ("C2", "B"), ("C2", "A"), ("C3", "A"), ("C3", "B"))
EFFORTS = {"A": "medium", "B": "high"}
OUTPUT_CEILING = 25_000
ACTIVE_SECONDS = 1800
SETTINGS = {
    "model": MODEL,
    "tool_choice": "required",
    "parallel_tool_calls": True,
    "store": False,
    "include": ["reasoning.encrypted_content"],
    "service_tier": "default",
    "max_output_tokens": OUTPUT_CEILING,
    "truncation": "disabled",
}
BOUNDARIES = {
    "official": False,
    "claim_eligible": False,
    "tool_executions": 0,
    "task_acceptance": "NOT_RUN",
    "safety_state": "NOT_RUN",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def sampler_hash() -> str:
    # This standalone module is the entire diagnostic implementation content set.
    return sha256_bytes(Path(__file__).read_bytes())


def price_identity() -> dict[str, str]:
    return {key: str(value) for key, value in asdict(pricing_for_model(MODEL)).items()}


def model_config(effort: str) -> ModelConfig:
    return ModelConfig(
        provider="openai",
        model_id=MODEL,
        reasoning_effort=effort,
        reasoning_continuation="encrypted-v1",
        transport_max_retries=0,
        max_output_tokens=OUTPUT_CEILING,
        service_tier="default",
    )


def read_source_artifact(root: Path, value: dict) -> bytes:
    """CAS verification without creating directories in the historical state root."""
    artifact = Artifact.model_validate(value)
    digest = artifact.content_hash.removeprefix("sha256:")
    expected = root / "artifacts" / "objects" / "sha256" / digest[:2] / digest[2:]
    path = Path(artifact.path)
    require(path.resolve() == expected.resolve() and not path.is_symlink(), "source CAS path")
    raw = path.read_bytes()
    require(len(raw) == artifact.size_bytes, "source CAS size")
    require(sha256_bytes(raw) == artifact.content_hash, "source CAS hash")
    return raw


@dataclass(frozen=True)
class Cell:
    case_id: str
    arm: str
    request_json: str = field(repr=False)
    request_hash: str
    historical_count: int | None
    source_turn_id: str
    max_parallel_reads: int
    read_paths: tuple[str, ...]
    sample_number: int | None = None


@dataclass(frozen=True)
class CollectionProtocol:
    """Validated diagnostic schedule; never an agent workflow or model input."""

    kind: str
    efforts: dict[str, str]
    sampling_order: tuple[tuple[str, str | int], ...]
    input_token_limit: int | None = None
    reserve_future_calls: bool = True


SIX_CELL_PROTOCOL = CollectionProtocol("decision-sampler-v1", EFFORTS, ORDER)


@dataclass(frozen=True)
class FrozenPlan:
    packet_path: Path
    packet_hash: str
    packet: dict = field(repr=False)
    cells: tuple[Cell, ...] = field(repr=False)
    source_root: Path
    design_hashes: dict[str, str]


def load_plan(packet_path: Path, source_root: Path, expected_hash: str) -> FrozenPlan:
    """Reconstruct only original requests. No workspace, private task or provider reads."""
    raw = packet_path.read_bytes()
    require(sha256_bytes(raw) == expected_hash, "packet hash mismatch")
    packet = json.loads(raw)
    require(packet["status"] == "PREPARED_NOT_EXECUTABLE", "not a prepared packet")
    require(packet["dispatch_enabled"] is False, "preparation is not execution authority")
    require(packet["official"] is False and packet["claim_eligible"] is False, "claim boundary")
    require(
        packet["actual_provider_calls"] == packet["actual_input_count_calls"] == 0
        and packet["actual_cost_nanos"] == 0,
        "preparation must be unexecuted",
    )
    require(packet["runtime_hash"] == runtime_content_hash(), "pinned runtime mismatch")
    require(
        packet["model"] == MODEL and packet["fixed_request_settings"] == SETTINGS,
        "fixed model/request settings mismatch",
    )
    require(
        packet["arms"] == [{"id": k, "reasoning_effort": v} for k, v in EFFORTS.items()],
        "effort arms mismatch",
    )
    require(tuple(map(tuple, packet["sampling_order"])) == ORDER, "sampling order mismatch")
    require(
        packet["maximum_generation_calls"] == packet["maximum_input_count_calls"] == 6
        and packet["samples_per_case_per_arm"] == 1,
        "six cells required",
    )
    require(
        packet["maximum_tool_executions"]
        == packet["maximum_correction_calls"]
        == packet["maximum_sdk_retries"]
        == 0,
        "no execution, correction or retry",
    )
    require(
        packet["proposed_total_active_seconds"] == ACTIVE_SECONDS
        and packet["proposed_total_cap_usd"] == "1.20",
        "pilot limits mismatch",
    )
    require(
        [(c["case_id"], c["source_turn_number"]) for c in packet["cases"]]
        == [("C1", 6), ("C2", 21), ("C3", 32)],
        "checkpoint selection mismatch",
    )
    source_root = source_root.resolve()
    journal_path = source_root / "runs" / f"{packet['source_run_id']}.jsonl"
    require(journal_path.is_file(), "source journal missing")
    require(
        sha256_bytes(journal_path.read_bytes()) == packet["source_journal_hash"],
        "source journal mismatch",
    )
    # DevJournal.events only reads; construction cannot create an absent runs directory here.
    journal = DevJournal(source_root, packet["source_run_id"])
    events = journal.events()
    envelope = json.loads(journal.envelope_path.read_bytes())
    require(
        all(envelope[k] == packet[k] for k in ("task_id", "task_version", "task_content_hash")),
        "task identity mismatch",
    )
    turns = [e for e in events if e["event_type"] == "turn_started"]
    dispatches = {
        e["payload"]["turn_id"]: e["payload"]
        for e in events
        if e["event_type"] == "provider_call_started"
    }
    cases = {}
    for case in packet["cases"]:
        event = turns[case["source_turn_number"] - 1]
        turn = event["payload"]
        cutoff = events.index(event)
        require(
            case["source_turn_id"] == turn["turn_id"]
            and case["turn_started_journal_line"] == cutoff + 1,
            "checkpoint cutoff mismatch",
        )
        require(
            case["input_artifact"] == turn["model_input_artifact"]
            and case["canonical_context_artifact"] == turn["context_artifact"],
            "checkpoint artifact mismatch",
        )
        read_source_artifact(source_root, case["canonical_context_artifact"])
        items = json.loads(read_source_artifact(source_root, case["input_artifact"]))
        validate_model_input(items, turn["native_history"])
        state = reconstruct_state(items)
        require(
            case["native_history"] == turn["native_history"]
            and sha256_json(state) == case["state_hash"]
            and state["mutation_scope_budget"] == case["scope_budget"],
            "state mismatch",
        )
        schema_inputs = {
            "finish_enabled": "finish_task" in turn["available_tool_names"],
            "check_ids": [
                c["check_id"] for c in state["visible_check_status"] if c["status"] == "NOT_RUN"
            ],
            "allowed_tools": turn["available_tool_names"],
            "read_paths": turn["targeted_read_paths"],
        }
        require(schema_inputs == case["tool_schema_inputs"], "tool policy mismatch")
        schemas = dev_tool_schemas(**schema_inputs)
        require(
            sha256_json(schemas) == case["tools_hash"]
            and [s["name"] for s in schemas] == case["schema_order"],
            "tool schema mismatch",
        )
        prior = {
            e["payload"]["result"]["action_id"]
            for e in events[:cutoff]
            if e["event_type"] == "action_finished"
        }
        outputs = [i["call_id"] for i in items if i.get("type") == "function_call_output"]
        calls = [i["call_id"] for i in items if i.get("type") == "function_call"]
        require(
            outputs == calls == turn["transcript_action_ids"]
            and len(set(outputs)) == len(outputs) == case["prior_action_count"]
            and set(outputs) <= prior,
            "native action cutoff/order mismatch",
        )
        reasoning = [i for i in items if i.get("type") == "reasoning"]
        require(
            len(reasoning) == case["continuation_items"]
            and all(
                i.get("encrypted_content")
                and i.get("summary") == []
                and not i.get("text")
                and not i.get("content")
                for i in reasoning
            ),
            "encrypted history mismatch",
        )
        historical = case["historical_input_count"]
        require(type(historical) is int and historical > 0, "invalid historical count")
        for arm, effort in EFFORTS.items():
            request = {
                **SETTINGS,
                "input": items,
                "tools": schemas,
                "reasoning": {"effort": effort},
            }
            request_hash = sha256_json(request)
            require(request_hash == case[f"{effort}_request_hash"], "frozen request mismatch")
            if arm == "A":
                require(
                    request_hash == dispatches[turn["turn_id"]]["request_hash"],
                    "original request mismatch",
                )
            cases[case["case_id"], arm] = Cell(
                case["case_id"],
                arm,
                # Canonical hashing is order-insensitive. Sending that sorted JSON
                # would change the LLM-visible schema property order, so keep the
                # original builder's ordering separately from content identity.
                json.dumps(request, ensure_ascii=False, separators=(",", ":")),
                request_hash,
                historical,
                turn["turn_id"],
                turn["max_parallel_reads"],
                tuple(turn["targeted_read_paths"]),
            )
    hashes = {
        name: sha256_bytes(packet_path.with_name(name).read_bytes())
        for name in ("protocol.md", "rubric.json")
    }
    return FrozenPlan(
        packet_path.resolve(),
        expected_hash,
        packet,
        tuple(cases[k] for k in ORDER),
        source_root,
        hashes,
    )


@dataclass(frozen=True)
class Approval:
    packet_hash: str
    sampler_hash: str
    result_root: Path
    credential_file: Path
    max_cost_usd: Decimal
    pricing_hash: str
    pricing_verified_on: str


def validate_approval(plan: FrozenPlan, approval: Approval) -> None:
    _validate_collection_approval(plan, approval, sampler_hash())


def _validate_collection_approval(
    plan: FrozenPlan,
    approval: Approval,
    expected_sampler_hash: str,
    *,
    protected_roots: tuple[Path, ...] = (),
) -> None:
    require(approval.packet_hash == plan.packet_hash, "approval packet mismatch")
    require(approval.sampler_hash == expected_sampler_hash, "approval sampler mismatch")
    require(
        approval.max_cost_usd == Decimal(plan.packet["proposed_total_cap_usd"]),
        "approval cap mismatch",
    )
    require(approval.pricing_hash == sha256_json(price_identity()), "reviewed pricing mismatch")
    require(
        approval.pricing_verified_on == datetime.now(UTC).date().isoformat(),
        "pricing must be reviewed on execution UTC date",
    )
    require(approval.credential_file.is_absolute(), "exact absolute credential path required")
    require(approval.result_root.is_absolute(), "absolute result root required")
    root = approval.result_root.resolve()
    require(not root.exists(), "result root already exists; collection never resumes or retries")
    require(
        not any(
            root.is_relative_to(p)
            for p in (
                repository_root().resolve(),
                plan.source_root,
                plan.packet_path.parent,
                *protected_roots,
            )
        ),
        "result root must be outside repository, source state and prepared design",
    )


def full_reservation(input_tokens: int) -> int:
    # Use the same reviewed integer-nanos ledger, with no ceiling reduction.
    ledger = DevCostLedger(Decimal("1000000"), pricing_for_model(MODEL))
    admission = ledger.admit(
        input_tokens, desired_output_ceiling=OUTPUT_CEILING, minimum_output_ceiling=OUTPUT_CEILING
    )
    require(admission is not None, "invalid reservation")
    return admission.reserved_cost_nanos


def inspect_result(root: Path) -> dict:
    """Read-only receipt, including a conservative outcome after a killed process."""
    raw = json.loads((root / "envelope.json").read_bytes())
    require(
        raw["kind"] in {"decision-sampler-v1", "fresh-state-sampler-v1", "failure-order-sampler-v1",
                        "completion-signal-sampler-v1"}
        and (root / "runs").is_dir(),
        "not a diagnostic result root",
    )
    journal = DevJournal(root, raw["run_id"])
    events = journal.events()
    terminal = journal.terminal()
    if terminal:
        return terminal["payload"]
    started = {
        e["payload"]["call_id"] for e in events if e["event_type"] == "provider_call_started"
    }
    finished = {
        e["payload"]["call_id"] for e in events if e["event_type"] == "provider_call_finished"
    }
    count_started = {
        e["payload"]["count_id"] for e in events if e["event_type"] == "input_count_started"
    }
    count_finished = {
        e["payload"]["count_id"] for e in events if e["event_type"] == "input_count_finished"
    }
    billing_unknown = bool(started - finished) or any(
        not e["payload"]["billing_known"]
        for e in events
        if e["event_type"] == "provider_call_finished"
    )
    code = (
        "PROVIDER_TIMEOUT_OR_UNKNOWN"
        if billing_unknown
        else "COUNT_TIMEOUT_OR_UNKNOWN"
        if count_started - count_finished
        else "INTERRUPTED"
    )
    return {
        **BOUNDARIES,
        "terminal": code,
        "read_only": True,
        "resume_allowed": False,
        "provider_calls": len(started),
        "input_count_calls": len(count_started),
        "sample_count": sum(e["event_type"] == "sample_recorded" for e in events),
        "recorded_cost_nanos": sum(
            e["payload"].get("cost_nanos") or 0
            for e in events
            if e["event_type"] == "provider_call_finished"
        ),
        "total_cost_known": not billing_unknown,
    }


def collect(
    plan: FrozenPlan,
    approval: Approval,
    *,
    adapter_factory: Callable[[ModelConfig], OpenAIResponsesAdapter] | None = None,
    clock: Callable[[], float] = monotonic,
    checkpoint: Callable[[str], None] = lambda _: None,
) -> dict:
    """One create per cell. Factory/clock/checkpoint injection is only for offline tests."""
    validate_approval(plan, approval)
    # Revalidate all disk-backed inputs before claiming a new output root or loading a key.
    refreshed = load_plan(plan.packet_path, plan.source_root, approval.packet_hash)
    require(refreshed.design_hashes == plan.design_hashes, "review design changed after validation")
    return _collect_validated(
        refreshed,
        approval,
        protocol=SIX_CELL_PROTOCOL,
        adapter_factory=adapter_factory,
        clock=clock,
        checkpoint=checkpoint,
    )


def _collect_validated(
    plan: FrozenPlan,
    approval: Approval,
    *,
    protocol: CollectionProtocol,
    adapter_factory: Callable[[ModelConfig], OpenAIResponsesAdapter] | None,
    clock: Callable[[], float],
    checkpoint: Callable[[str], None],
) -> dict:
    """Shared one-response engine. Callers must validate disk inputs and exact approval."""
    root = approval.result_root.resolve()
    root.mkdir(parents=True, exist_ok=False)  # Atomic exclusive claim, including concurrent starts.
    store = ArtifactStore(root)
    journal = DevJournal(root, f"run_dev_sample_{uuid.uuid4().hex[:16]}")
    started_at = clock()
    deadline = ExecutionDeadline.from_remaining(ACTIVE_SECONDS, clock=clock)
    ledger = DevCostLedger(approval.max_cost_usd, pricing_for_model(MODEL))
    envelope = {
        **BOUNDARIES,
        "kind": protocol.kind,
        "run_id": journal.run_id,
        "packet_hash": plan.packet_hash,
        "sampler_hash": approval.sampler_hash,
        "runtime_hash": plan.packet["runtime_hash"],
        "design_hashes": plan.design_hashes,
        "source_run_id": plan.packet["source_run_id"],
        "source_journal_hash": plan.packet["source_journal_hash"],
        "task_id": plan.packet["task_id"],
        "task_version": plan.packet["task_version"],
        "task_content_hash": plan.packet["task_content_hash"],
        "credential_path_hash": sha256_text(str(approval.credential_file.resolve())),
        "result_root": str(root),
        "cap_nanos": ledger.cap_nanos,
        "pricing": price_identity(),
        "pricing_hash": approval.pricing_hash,
        "pricing_verified_on": approval.pricing_verified_on,
        "models": [
            model_config(effort).model_dump(mode="json") for effort in protocol.efforts.values()
        ],
        "sampling_order": protocol.sampling_order,
        "collection_policy": asdict(protocol),
        "request_hashes": [c.request_hash for c in plan.cells],
        "ordered_request_hashes": [sha256_text(c.request_json) for c in plan.cells],
        "fixed_output_ceiling": OUTPUT_CEILING,
        "active_seconds": ACTIVE_SECONDS,
        "maximum_generation_calls": len(plan.cells),
        "maximum_input_count_calls": len(plan.cells),
        "correction_calls": 0,
        "sdk_retries": 0,
        "resume_allowed": False,
        "provider_free": adapter_factory is not None,
    }
    for key in ("source_packet_hash", "preparer_hash", "schema_version", "source_checkpoints"):
        if key in plan.packet:
            envelope[key] = plan.packet[key]
    envelope_ref = store.put_json(envelope)
    store.write_text_immutable(root / "envelope.json", canonical_json(envelope))
    real_client = None
    count_calls = provider_calls = 0
    samples: list[dict] = []
    billing_known = True

    def elapsed() -> int:
        return max(0, int((clock() - started_at) * 1000))

    def finish(code: str) -> dict:
        existing = journal.terminal()
        if existing is not None:
            return existing["payload"]
        # Display order is independently shuffled; arm/effort/usage are not in review artifacts.
        display = list(samples)
        secrets.SystemRandom().shuffle(display)
        review = store.put_json({**BOUNDARIES, "samples": display, "grading": "NOT_ASSESSED"})
        result = {
            **BOUNDARIES,
            "terminal": code,
            "run_id": journal.run_id,
            "provider_free": envelope["provider_free"],
            "provider_calls": provider_calls,
            "input_count_calls": count_calls,
            "sample_count": len(samples),
            "recorded_cost_nanos": ledger.spent_nanos,
            "total_cost_known": billing_known,
            "active_elapsed_ms": elapsed(),
            "resume_allowed": False,
            "review_artifact": review.model_dump(mode="json"),
        }
        journal.append("terminal", result)
        store.write_text_immutable(root / "result.json", canonical_json(result))
        return result

    with journal.execution_lock():
        journal.append(
            "sampler_started", {"envelope_artifact": envelope_ref.model_dump(mode="json")}
        )
        try:
            for index, cell in enumerate(plan.cells):
                deadline.check()
                if not protocol.reserve_future_calls:
                    future = 0
                    basis = "current counted input plus full output; no future trajectory reserve"
                elif protocol.input_token_limit is None:
                    future = sum(
                        full_reservation(c.historical_count) for c in plan.cells[index + 1 :]
                    )
                    basis = "historical counts; recount before each dispatch"
                else:
                    # No guessed token counts for repackaged input. Each future response
                    # must satisfy this admission limit, or stop before its generation.
                    future = (len(plan.cells) - index - 1) * full_reservation(
                        protocol.input_token_limit
                    )
                    basis = "per-response input admission limit; not an estimated token count"
                if (
                    protocol.reserve_future_calls and protocol.input_token_limit is None
                    and full_reservation(cell.historical_count) + future > ledger.remaining_nanos
                ):
                    return finish("COST_CAP_REACHED")
                config = model_config(protocol.efforts[cell.arm])
                if adapter_factory is None:
                    if real_client is None:
                        key = load_exact_openai_api_key(approval.credential_file)
                        real_client = create_openai_client(config, api_key=key)
                        del key
                    adapter = OpenAIResponsesAdapter(config, api_key="", client=real_client)
                else:
                    adapter = adapter_factory(config)
                require(adapter.config == config, "adapter config mismatch")
                require(adapter.client.max_retries == 0, "adapter retries must be zero")
                request = json.loads(cell.request_json)
                require(sha256_json(request) == cell.request_hash, "request identity mismatch")
                request_ref = store.put_text(cell.request_json, "application/json")
                count_id, call_id = f"count_{uuid.uuid4().hex}", f"call_{uuid.uuid4().hex}"
                sample_id = f"sample_{uuid.uuid4().hex}"
                common = {
                    "case_id": cell.case_id,
                    "arm": cell.arm,
                    "sample_id": sample_id,
                    "request_hash": cell.request_hash,
                    "ordered_request_hash": sha256_text(cell.request_json),
                    "source_turn_id": cell.source_turn_id,
                }
                if cell.sample_number is not None:
                    common["sample_number"] = cell.sample_number
                count_timeout = deadline.check()
                journal.append(
                    "input_count_started",
                    {
                        **common,
                        "count_id": count_id,
                        "request_artifact": request_ref.model_dump(mode="json"),
                        "active_elapsed_ms": elapsed(),
                    },
                )
                count_calls += 1
                try:
                    count = adapter.count_input_tokens_v2(request, timeout_seconds=count_timeout)
                    require(type(count) is int and count > 0, "invalid input count")
                except Exception:
                    return finish("COUNT_TIMEOUT_OR_UNKNOWN")
                journal.append(
                    "input_count_finished",
                    {"count_id": count_id, "input_tokens": count, "active_elapsed_ms": elapsed()},
                )
                if protocol.input_token_limit is not None and count > protocol.input_token_limit:
                    return finish("INPUT_LIMIT_EXCEEDED")
                admission = ledger.admit(
                    count,
                    desired_output_ceiling=OUTPUT_CEILING,
                    minimum_output_ceiling=OUTPUT_CEILING,
                )
                if (
                    admission is None
                    or admission.reserved_cost_nanos + future > ledger.remaining_nanos
                ):
                    return finish("COST_CAP_REACHED")
                timeout = deadline.check()
                require(sha256_json(request) == cell.request_hash, "count altered request")
                require(
                    json.dumps(request, ensure_ascii=False, separators=(",", ":"))
                    == cell.request_json,
                    "count altered request order",
                )
                journal.append(
                    "provider_call_started",
                    {
                        **common,
                        "call_id": call_id,
                        "input_tokens": count,
                        "output_ceiling": OUTPUT_CEILING,
                        "reserved_cost_nanos": admission.reserved_cost_nanos,
                        "remaining_cell_reserve_nanos": future,
                        "remaining_input_basis": basis,
                        "active_elapsed_ms": elapsed(),
                    },
                )
                provider_calls += 1
                billing_known = False
                checkpoint("dispatch_recorded")
                try:
                    raw_turn = adapter.execute_request(
                        request, requested_input_tokens=count, timeout_seconds=timeout
                    )
                except Exception:
                    return finish("PROVIDER_TIMEOUT_OR_UNKNOWN")
                checkpoint("provider_returned")
                usage_valid = (
                    raw_turn.input_tokens == count
                    and 0 <= raw_turn.cached_input_tokens <= count
                    and 0
                    <= raw_turn.reasoning_output_tokens
                    <= raw_turn.output_tokens
                    <= OUTPUT_CEILING
                    and raw_turn.response_model == MODEL
                    and bool(raw_turn.response_id)
                    and raw_turn.response_status in {"completed", "incomplete"}
                    and not (raw_turn.error and raw_turn.error.code == "input_token_count_mismatch")
                )
                cost = (
                    ledger.settle(
                        input_tokens=raw_turn.input_tokens,
                        cached_input_tokens=raw_turn.cached_input_tokens,
                        output_tokens=raw_turn.output_tokens,
                    )
                    if usage_valid
                    else None
                )
                billing_known = usage_valid and ledger.spent_nanos <= ledger.cap_nanos
                # Persist usage before parsing/public-decision/continuation storage can fail.
                journal.append(
                    "provider_call_finished",
                    {
                        **common,
                        "call_id": call_id,
                        "response_id": raw_turn.response_id,
                        "response_model": raw_turn.response_model,
                        "response_status": raw_turn.response_status,
                        "output_item_types": list(raw_turn.output_item_types),
                        "output_shape_hash": raw_turn.output_shape_hash,
                        "input_tokens": raw_turn.input_tokens,
                        "cached_input_tokens": raw_turn.cached_input_tokens,
                        "output_tokens": raw_turn.output_tokens,
                        "reasoning_output_tokens": raw_turn.reasoning_output_tokens,
                        "error_code": raw_turn.error.code if raw_turn.error else None,
                        "cost_nanos": cost,
                        "billing_known": billing_known,
                        "active_elapsed_ms": elapsed(),
                    },
                )
                checkpoint("usage_recorded")
                if not billing_known:
                    return finish("PROVIDER_TIMEOUT_OR_UNKNOWN")
                turn = _turn_from_openai(raw_turn)
                if turn.error_code == "provider_continuation_error":
                    return finish("PROVIDER_CONTINUATION_ERROR")
                continuation_ref = None
                if "reasoning" in turn.output_item_types:
                    if turn.provider_continuation is None:
                        return finish("PROVIDER_CONTINUATION_ERROR")
                    try:
                        _validate_continuation_action_order(
                            turn.provider_continuation, turn.tool_calls
                        )
                        continuation_ref = _store_provider_continuation(
                            store, turn.provider_continuation
                        )
                        checkpoint("continuation_stored")
                        _load_provider_continuation(store, continuation_ref)
                    except Exception:
                        return finish("PROVIDER_CONTINUATION_ERROR")
                batch_shape = None
                if not turn.error_code:
                    # Shape validation is not source admission, scope, or semantic grading.
                    with suppress(ContractError):
                        batch_shape = validate_tool_batch(
                            turn.tool_calls,
                            allowed_tools={s["name"] for s in request["tools"]},
                            max_parallel_reads=cell.max_parallel_reads,
                            allowed_read_paths=cell.read_paths,
                        )
                public = {
                    **BOUNDARIES,
                    "anonymous_sample_id": sample_id,
                    "case_id": cell.case_id,
                    "tool_calls": [asdict(c) for c in raw_turn.tool_calls],
                    "response_status": turn.response_status,
                    "error_code": turn.error_code,
                    "incomplete_reason": turn.incomplete_reason,
                    "batch_shape": batch_shape,
                    "tool_contract": "NOT_ASSESSABLE",
                    "grading": "NOT_ASSESSED",
                }
                public_ref = store.put_json(public)
                journal.append(
                    "sample_recorded",
                    {
                        **common,
                        "public_artifact": public_ref.model_dump(mode="json"),
                        "continuation_ref": continuation_ref.model_dump(mode="json")
                        if continuation_ref
                        else None,
                    },
                )
                samples.append(
                    {
                        "anonymous_sample_id": sample_id,
                        "case_id": cell.case_id,
                        "public_artifact": public_ref.model_dump(mode="json"),
                    }
                )
                checkpoint("sample_recorded")
            return finish("SAMPLES_COLLECTED")
        except ExecutionDeadlineExceeded:
            return finish("LIMIT_REACHED")
        except (KeyboardInterrupt, SystemExit):
            return finish("INTERRUPTED" if billing_known else "PROVIDER_TIMEOUT_OR_UNKNOWN")
        except Exception:
            return finish("SAMPLER_ERROR" if billing_known else "PROVIDER_TIMEOUT_OR_UNKNOWN")
        finally:
            if real_client is not None:
                # Closing a completed HTTP client must not replace a durable receipt.
                with suppress(Exception):
                    real_client.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="read an existing receipt; never resume")
    inspect.add_argument("--result-root", type=Path, required=True)
    for name in ("validate", "collect"):
        command = commands.add_parser(name)
        command.add_argument("--packet", type=Path, required=True)
        command.add_argument("--packet-hash", required=True)
        command.add_argument("--source-state-root", type=Path, required=True)
        if name == "collect":
            command.add_argument(
                "--approve-six-responses-zero-tools", action="store_true", required=True
            )
            command.add_argument("--sampler-hash", required=True)
            command.add_argument("--result-root", type=Path, required=True)
            command.add_argument("--credential-file", type=Path, required=True)
            command.add_argument("--max-cost-usd", type=Decimal, required=True)
            command.add_argument("--pricing-hash", required=True)
            command.add_argument("--pricing-verified-on", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            result = inspect_result(args.result_root)
        else:
            plan = load_plan(args.packet, args.source_state_root, args.packet_hash)
            if args.command == "validate":
                result = {
                    **BOUNDARIES,
                    "status": "VALIDATED_NOT_EXECUTED",
                    "packet_hash": plan.packet_hash,
                    "sampler_hash": sampler_hash(),
                    "runtime_hash": plan.packet["runtime_hash"],
                    "design_hashes": plan.design_hashes,
                    "request_hashes": [c.request_hash for c in plan.cells],
                    "pricing": price_identity(),
                    "pricing_hash": sha256_json(price_identity()),
                    "pricing_status": "REGISTERED_RATES_REQUIRE_FRESH_LIVE_REVIEW",
                    "planning_reserve_nanos": sum(
                        full_reservation(c.historical_count) for c in plan.cells
                    ),
                    "provider_calls": 0,
                    "input_count_calls": 0,
                }
            else:
                result = collect(
                    plan,
                    Approval(
                        args.packet_hash,
                        args.sampler_hash,
                        args.result_root,
                        args.credential_file,
                        args.max_cost_usd,
                        args.pricing_hash,
                        args.pricing_verified_on,
                    ),
                )
        print(canonical_json(result))
        return 0 if result.get("terminal") in {None, "SAMPLES_COLLECTED"} else 1
    except Exception as exc:
        # Never print SDK exception bodies, credential lines, or arbitrary validation inputs.
        print(
            canonical_json(
                {**BOUNDARIES, "status": "PREFLIGHT_REJECTED", "error_type": type(exc).__name__}
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
