"""Optional runner compaction boundaries; no credentials or implicit remote retries."""

from __future__ import annotations

import json

from patchloop.agent.count_diagnostics import (
    input_count_error_metadata,
    input_count_request_metadata,
)
from patchloop.contracts import Artifact
from patchloop.dev import compaction_cost
from patchloop.dev.compacted_window import CompactedWindow
from patchloop.dev.conversation import WINDOW_POLICY, WINDOW_RULES, validate_model_input
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, sha256_json


def policy_contract(request):
    if request.compact_at_input_tokens is None:
        return None
    return {
        "kind": "native-window-compaction-policy-v1",
        "context_policy": WINDOW_POLICY,
        "compact_at_input_tokens": request.compact_at_input_tokens,
        "maximum_compaction_requests": 1,
        "accept_model_limit_reservation": request.accept_compaction_model_limit_reservation,
        "cost_contract": compaction_cost.CONTRACT,
        "cost_contract_hash": sha256_json(compaction_cost.CONTRACT),
        "prepared_input": "exact-request-count-then-optional-compact-recount-v1",
    }


def read_json(store, ref):
    return json.loads(store.read_bytes(Artifact.model_validate(ref)))


def put_json(store, value):
    return store.put_text(canonical_json(value), "application/json").model_dump(mode="json")


def cursor(journal):
    kinds = {
        "turn_decision_recorded",
        "tool_batch_finished",
        "action_finished",
        "repair_recheck_finished",
        "context_window_activated",
        "context_segment_started",
    }
    return next(
        (e["event_hash"] for e in reversed(journal.events()) if e["event_type"] in kinds), None
    )


def prepared_input(journal, store, turn, request_payload, transition):
    """Freeze input BEFORE counting, without inventing a model decision/turn start."""
    journal.require_execution_lock()
    current = cursor(journal)
    saved = next(
        (
            e["payload"]
            for e in reversed(journal.events())
            if e["event_type"] == "model_input_prepared"
        ),
        None,
    )
    if saved and saved["cursor"] == current:
        bundle = read_json(store, saved["artifact"])
    else:
        bundle = {"turn": turn, "request": request_payload, "transition": transition}
        saved = {
            "boundary_id": turn["turn_id"],
            "cursor": current,
            "artifact": put_json(store, bundle),
            "request_hash": sha256_json(request_payload),
        }
        journal.append("model_input_prepared", saved)
    if (
        sha256_json(bundle["request"]) != saved["request_hash"]
        or bundle["turn"]["turn_id"] != saved["boundary_id"]
        or read_json(store, bundle["turn"]["model_input_artifact"]) != bundle["request"]["input"]
    ):
        raise RecoveryError("prepared input request identity mismatch")
    return saved, bundle


class CountFailure(RecoveryError):
    pass


def count_prepared(journal, boundary, bundle, adapter, deadline, active_elapsed_ms):
    journal.require_execution_lock()
    boundary_id = boundary["boundary_id"]
    count_id = "count_" + boundary_id
    events = journal.events()
    started = next(
        (
            e["payload"]
            for e in events
            if e["event_type"] == "input_count_started" and e["payload"].get("count_id") == count_id
        ),
        None,
    )
    finished = next(
        (
            e["payload"]
            for e in events
            if e["event_type"] == "input_count_finished"
            and e["payload"].get("count_id") == count_id
        ),
        None,
    )
    if started:
        if (
            not finished
            or started["request_hash"] != boundary["request_hash"]
            or finished.get("request_hash") != boundary["request_hash"]
            or finished.get("boundary_id") != boundary_id
        ):
            raise CountFailure("prepared input count outcome is unavailable or mismatched")
        return count_id, finished["input_tokens"]
    timeout = deadline.bounded_timeout(deadline.remaining_seconds())
    common = {
        "count_id": count_id,
        "turn_id": boundary_id,
        "boundary_id": boundary_id,
        "request_hash": boundary["request_hash"],
    }
    journal.append(
        "input_count_started",
        {
            **common,
            "request_metadata": input_count_request_metadata(bundle["request"]),
            "active_elapsed_ms": active_elapsed_ms(),
        },
    )
    try:
        tokens = adapter.count_input_tokens_v2(bundle["request"], timeout_seconds=timeout)
        if type(tokens) is not int or tokens < 0:
            raise ValueError("invalid input count")
    except Exception as exc:
        error = input_count_error_metadata(exc)
        journal.append(
            "input_count_failed",
            {**common, "error": error, "active_elapsed_ms": active_elapsed_ms()},
        )
        raise CountFailure(f"input count failed: {error['exception_type']}") from exc
    journal.append(
        "input_count_finished",
        {**common, "input_tokens": tokens, "active_elapsed_ms": active_elapsed_ms()},
    )
    return count_id, tokens


def eligible(
    journal,
    *,
    threshold,
    input_tokens,
    remaining_model_calls,
    minimum_completion_calls,
    ledger,
    deadline,
    correction,
):
    """Optional compaction cannot take away a viable minimum completion path."""
    events = journal.events()
    if (
        threshold is None
        or input_tokens < threshold
        or input_tokens > 272_000
        or remaining_model_calls - 1 < minimum_completion_calls
        or correction is not None
        or deadline.remaining_seconds() <= 5
        or any(e["event_type"] == "compaction_started" for e in events)
    ):
        return False
    decision = next(
        (e["payload"] for e in reversed(events) if e["event_type"] == "turn_decision_recorded"),
        None,
    )
    batch = next(
        (e["payload"] for e in reversed(events) if e["event_type"] == "tool_batch_finished"), None
    )
    if (
        not decision
        or not batch
        or decision.get("error_code")
        or decision.get("incomplete_reason")
        or batch["turn_id"] != decision["turn_id"]
        or not decision.get("tool_calls")
        or any(c["name"] in {"finish_task", "stop_task"} for c in decision["tool_calls"])
    ):
        return False
    try:
        compaction_cost.reserve_from_ledger(ledger)
    except ContractError:
        return False
    return True


def load_window(binding, store):
    source = read_json(store, binding["source_input"])
    bundle = read_json(store, binding["prepared_artifact"])
    turn = bundle["turn"]
    validate_model_input(source, turn["native_history"], context_policy=WINDOW_POLICY)
    receipt = read_json(store, binding["receipt_artifact"])
    if (
        source != bundle["request"]["input"]
        or receipt["source_input_hash"] != sha256_json(source)
        or receipt["window_artifact"] != binding["seed_artifact"]
        or receipt["ready_for_activation"] is not True
        or receipt["terminal"] is not None
        or binding["last_exchange_turn_id"] != turn["context_window"]["last_exchange_turn_id"]
    ):
        raise RecoveryError("compaction activation provenance mismatch")
    window = CompactedWindow(source, read_json(store, binding["seed_artifact"]), WINDOW_RULES)
    if (
        read_json(store, binding["base_artifact"]) != window.base
        or binding["window_binding"] != window.binding
    ):
        raise RecoveryError("compaction activation base changed")
    return window


def active_window(journal, store):
    activations = [
        e["payload"] for e in journal.events() if e["event_type"] == "context_window_activated"
    ]
    if len(activations) > 1:
        raise RecoveryError("multiple compacted windows in one run")
    return (activations[0], load_window(activations[0], store)) if activations else (None, None)


def ready_source(journal, store, receipt):
    """Read-only activation preflight, also before resume credentials/workspace."""
    preparation = next(
        e["payload"] for e in journal.events() if e["event_type"] == "compaction_prepared"
    )
    boundary = next(
        e["payload"]
        for e in journal.events()
        if e["event_type"] == "model_input_prepared"
        and e["payload"]["boundary_id"] == preparation["boundary_id"]
    )
    bundle = read_json(store, boundary["artifact"])
    source = read_json(store, preparation["source_input"])
    if (
        bundle["request"]["input"] != source
        or sha256_json(bundle["request"]) != boundary["request_hash"]
        or bundle["turn"]["model_input_artifact"] != preparation["source_input"]
        or receipt["source_input_hash"] != sha256_json(source)
        or not receipt["ready_for_activation"]
        or receipt["terminal"] is not None
    ):
        raise RecoveryError("compaction prepared source mismatch")
    validate_model_input(source, bundle["turn"]["native_history"], context_policy=WINDOW_POLICY)
    window = CompactedWindow(source, read_json(store, receipt["window_artifact"]), WINDOW_RULES)
    return preparation, boundary, bundle, window


def activate(journal, store, receipt):
    journal.require_execution_lock()
    existing, window = active_window(journal, store)
    if existing:
        if read_json(store, existing["receipt_artifact"]) != receipt:
            raise RecoveryError("compaction activation receipt changed")
        return existing, window
    preparation, boundary, bundle, window = ready_source(journal, store, receipt)
    if boundary["cursor"] != cursor(journal):
        raise RecoveryError("compaction public exchange cursor changed before activation")
    binding = {
        "seed_artifact": receipt["window_artifact"],
        "base_artifact": put_json(store, window.base),
        "source_input": preparation["source_input"],
        "prepared_artifact": boundary["artifact"],
        "receipt_artifact": put_json(store, receipt),
        "window_binding": window.binding,
        "last_exchange_turn_id": bundle["turn"]["context_window"]["last_exchange_turn_id"],
    }
    load_window(binding, store)
    journal.append("context_window_activated", binding)
    return binding, window
