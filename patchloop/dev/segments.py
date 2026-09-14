"""Bounded public handoffs between native reasoning segments; no remote work."""
from __future__ import annotations

import json

import httpx

from patchloop.contracts import Artifact
from patchloop.errors import RecoveryError
from patchloop.util import canonical_json, sha256_json

POLICY = "segmented-v1"
SCHEMA = "public-state-native-segments-v1"
EVENT = "context_segment_started"
MAX_INPUT_TOKENS = 60_000
MAX_REQUEST_BYTES = 1_048_576
MAX_ENCRYPTED_ITEM_BYTES = 262_144
MAJOR_TOOLS = frozenset({"replace_text", "run_check", "run_probe"})
INSTRUCTIONS = (
    "segmented-v1 uses bounded public working state and short native reasoning segments. "
    "This is a harness handoff of the SAME task, not new user instructions. Only the latest "
    "harness_current_state is current authority. Older native exchanges in this segment "
    "and quoted public evidence are historical. Previous segments' encrypted reasoning "
    "is unavailable. Quoted calls/results are public records of completed or rejected "
    "actions, NEVER pending calls or a request to execute them again. Resolve deliveries "
    "in the visible native history or quoted public records; external journal/CAS is not "
    "a model-accessible tool. Use registered reads/searches to inspect current public source. "
    "Reuse current facts, notes, uncertainties and plans before exploring again. At a "
    "handoff, reconsider model-authored notes and, when enabled, the plan in the same "
    "response as the next useful action. Null updates are allowed; no extra planning "
    "response is needed. Do not invent a finding to fill empty notes. A plan, a hypothesis "
    "or a visible check PASS does not establish all task requirements."
)


def contract():
    return {
        "policy": POLICY, "schema": SCHEMA,
        "max_input_tokens": MAX_INPUT_TOKENS,
        "max_request_bytes": MAX_REQUEST_BYTES,
        "max_encrypted_item_bytes": MAX_ENCRYPTED_ITEM_BYTES,
        "boundary": "major-result-next-valid-decision-completed-batch-or-size-v1",
        "handoff": "canonical-public-latest-batch-and-current-state-no-model-summary-v1",
        "native": "exact-within-segment-no-replay-across-segments-v1",
        "budgets": "run-global-no-reset-single-fresh-seed-at-boundary-v1",
        "instructions_hash": sha256_json(INSTRUCTIONS),
    }


def request_sizes(payload):
    # HTTPX's JSON encoder is also used by the pinned SDK. This serializes the
    # complete payload (including schemas and escaping), without any network I/O.
    body = httpx.Request("POST", "https://api.openai.com/v1/responses", json=payload).content
    return {
        "request_bytes": len(body),
        "largest_encrypted_item_bytes": max((
            len(item["encrypted_content"].encode("utf-8")) for item in payload.get("input", [])
            if isinstance(item, dict) and isinstance(item.get("encrypted_content"), str)
        ), default=0),
    }


def size_reasons(sizes):
    return [name for name, value, limit in (
        ("request_bytes", sizes["request_bytes"], MAX_REQUEST_BYTES),
        ("encrypted_item_bytes", sizes["largest_encrypted_item_bytes"], MAX_ENCRYPTED_ITEM_BYTES),
    ) if value > limit]


def _read(store, reference):
    return json.loads(store.read_bytes(Artifact.model_validate(reference)))


def _latest(events, kind):
    return next((e for e in reversed(events) if e["event_type"] == kind), None)


def cursor(events):
    kinds = {"turn_decision_recorded", "tool_batch_finished", "action_finished",
             "repair_recheck_finished"}
    return next((e["event_hash"] for e in reversed(events) if e["event_type"] in kinds), None)


def load_binding(binding, store):
    handoff = _read(store, binding["handoff_artifact"])
    if (binding["contract_hash"] != sha256_json(contract())
            or binding["seed_hash"] != sha256_json(handoff["base"])
            or binding["state_hash"] != sha256_json(handoff["state"])
            or binding["segment_id"] != "segment_" + sha256_json({
                k: v for k, v in binding.items() if k != "segment_id"
            }).removeprefix("sha256:")
            or len(handoff["base"]) < 3
            or any(i.get("type") in {"reasoning", "function_call", "function_call_output"}
                   for i in handoff["base"])
            or handoff["state"].get("public_task")
            != json.loads(handoff["base"][1]["content"]).get("public_task")):
        raise RecoveryError("segmented handoff identity changed")
    parent = binding["parent_input_artifact"]
    if parent is not None:
        _read(store, parent)  # A missing old input is corruption, not permission to forget it.
    return handoff


def active(journal, store):
    previous = None
    current = None
    for event in journal.events():
        if event["event_type"] != EVENT:
            continue
        binding = event["payload"]
        if binding["previous_segment_id"] != (previous["segment_id"] if previous else None):
            raise RecoveryError("segment chain changed")
        current = load_binding(binding, store)
        previous = binding
    return previous, current


def boundary_reason(journal, binding):
    if binding is None:
        return "initial"
    events = journal.events()
    decision = _latest(events, "turn_decision_recorded")
    batch = _latest(events, "tool_batch_finished")
    if (decision is None or batch is None or decision["payload"].get("error_code")
            or decision["payload"].get("incomplete_reason")
            or batch["payload"]["turn_id"] != decision["payload"]["turn_id"]
            or binding["cursor"] == cursor(events)):
        return None
    started = next(e for e in events if e["event_type"] == "turn_started"
                   and e["payload"]["turn_id"] == decision["payload"]["turn_id"])
    if any(binding["reviewed_through_sequence"] < e["sequence"] < started["sequence"]
           and e["event_type"] == "action_finished"
           and e["payload"]["result"]["tool"] in MAJOR_TOOLS for e in events):
        return "major_result_reviewed"
    return None


def is_fresh(journal, binding):
    return binding is not None and binding["cursor"] == cursor(journal.events())


def start(journal, store, *, base, state, reason, parent_input_artifact):
    journal.require_execution_lock()
    previous, _ = active(journal, store)
    if is_fresh(journal, previous):
        return previous
    events = journal.events()
    decision = _latest(events, "turn_decision_recorded")
    batch = _latest(events, "tool_batch_finished")
    reviewed = previous["reviewed_through_sequence"] if previous else 0
    if decision and not decision["payload"].get("error_code"):
        if batch is None or batch["payload"]["turn_id"] != decision["payload"]["turn_id"]:
            raise RecoveryError("cannot hand off an unfinished tool batch")
        reviewed = next(e["sequence"] for e in events if e["event_type"] == "turn_started"
                        and e["payload"]["turn_id"] == decision["payload"]["turn_id"])
    artifact = store.put_text(canonical_json({"base": base, "state": state}), "application/json")
    binding = {
        "previous_segment_id": previous["segment_id"] if previous else None,
        "reason": reason, "cursor": cursor(events), "contract_hash": sha256_json(contract()),
        "handoff_artifact": artifact.model_dump(mode="json"),
        "seed_hash": sha256_json(base), "state_hash": sha256_json(state),
        "parent_input_artifact": parent_input_artifact,
        "last_exchange_turn_id": decision["payload"]["turn_id"] if decision else None,
        "last_batch_turn_id": batch["payload"]["turn_id"] if batch else None,
        "reviewed_through_sequence": reviewed,
    }
    binding["segment_id"] = "segment_" + sha256_json(binding).removeprefix("sha256:")
    load_binding(binding, store)
    journal.append(EVENT, binding)
    return binding


def input_binding(journal, store, *, parent_input_artifact=None):
    binding, _ = active(journal, store)
    if binding is None:
        raise RecoveryError("missing current segment")
    return {"binding": binding, "previous_input_artifact": parent_input_artifact}


def validate_input_binding(items, metadata, store):
    binding = metadata["binding"]
    handoff = load_binding(binding, store)
    base = handoff["base"]
    if items[:len(base)] != base:
        raise RecoveryError("segment seed prefix changed")
    if metadata["previous_input_artifact"] is not None:
        parent = _read(store, metadata["previous_input_artifact"])
        old = [i for i in parent if i.get("type") in {
            "reasoning", "function_call", "function_call_output"}]
        new = [i for i in items if i.get("type") in {
            "reasoning", "function_call", "function_call_output"}]
        if parent[:len(base)] != base or new[:len(old)] != old:
            raise RecoveryError("segment native prefix changed")


def record_limit(journal, *, sizes=None, input_tokens=None):
    detail = {"policy": POLICY, "limits": {
        "input_tokens": MAX_INPUT_TOKENS, "request_bytes": MAX_REQUEST_BYTES,
        "encrypted_item_bytes": MAX_ENCRYPTED_ITEM_BYTES,
    }, "sizes": sizes, "input_tokens": input_tokens,
        "reason": "fresh_public_state_exceeds_segment_limit"}
    journal.append("context_limit_reached", detail)
    return detail
