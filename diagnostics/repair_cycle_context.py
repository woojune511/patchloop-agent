"""Public handoff state for the diagnostic repair cycle, without native splicing."""
from __future__ import annotations

import copy
import json

from patchloop.artifacts import ArtifactStore
from patchloop.dev.conversation import SEGMENT_RULES
from patchloop.dev.native_sources import PUBLIC_EVIDENCE_KIND, public_exchanges
from patchloop.errors import ContractError
from patchloop.repository import WorkspaceManager
from patchloop.util import canonical_json, sha256_json

HANDOFF_KIND = "diagnostic_repair_cycle_handoff_v1"
COUNTERS = frozenset({
    "normal_calls", "correction_calls", "tool_actions", "diagnostic_probes",
    "original_requests", "new_mutations", "host_original_actions", "new_cost_nanos",
    "host_regression_actions",
    "row_remaining_nanos", "group_remaining_nanos", "remaining_seconds", "segment_index",
    "model_limit", "output_limit", "input_limit",
})
OUTCOME_FIELDS = ("action_id", "request_hash", "batch_hash", "input_hash", "tool", "status",
                  "workspace_diff_hash", "error_code", "message", "result_hash")
ORIGINAL_FIELDS = (
    "schema", "candidate_diff_hash", "arguments_hash", "status", "comparison", "observed",
    "base_receipt", "candidate_receipt", "candidate_receipt_reused", "task_acceptance",
)


def require(condition, message):
    if not condition:
        raise ContractError(message)


def _batches(history):
    """Only complete public batches may cross a segment boundary."""
    batches, pending, batch, outputs = [], {}, [], False
    try:
        exchanges = list(public_exchanges(history, archive_kind=PUBLIC_EVIDENCE_KIND))
    except ValueError as exc:
        raise ContractError("handoff contains a non-public archive") from exc
    for item in exchanges:
        action_id = item.get("call_id")
        require(isinstance(action_id, str) and action_id, "handoff public call lacks identity")
        if item["type"] == "function_call":
            require(not outputs and action_id not in pending, "handoff has a dangling call batch")
            require(isinstance(item.get("name"), str)
                    and isinstance(item.get("arguments"), str), "handoff call is malformed")
            pending[action_id] = item
        else:
            require(action_id in pending, "handoff output has no matching public call")
            try:
                result = json.loads(item["output"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ContractError("handoff output is malformed") from exc
            require(isinstance(result, dict)
                    and result.get("status") in {"succeeded", "failed", "rejected"},
                    "handoff action is not completed or rejected")
            pending.pop(action_id)
            outputs = True
        batch.append(copy.deepcopy(item))
        if outputs and not pending:
            batches.append(batch)
            batch, outputs = [], False
    require(not pending, "handoff has dangling public calls")
    return batches


def _outcomes(batch):
    calls = {item["call_id"]: item for item in batch if item["type"] == "function_call"}
    for item in batch:
        if item["type"] != "function_call_output":
            continue
        call, result = calls[item["call_id"]], json.loads(item["output"])
        yield {"action_id": item["call_id"], "request_hash": sha256_json(call),
               "batch_hash": sha256_json(batch),
               "input_hash": result.get("input_hash"), "tool": call["name"],
               "status": result["status"], "workspace_diff_hash": result.get("workspace_diff_hash"),
               "error_code": result.get("error_code"), "message": result.get("message"),
               "result_hash": sha256_json(result)}


def _previous_outcomes(history):
    for item in history:
        if item.get("role") != "developer":
            continue
        try:
            record = json.loads(item["content"])
        except (KeyError, TypeError, ValueError):
            continue
        if isinstance(record, dict) and record.get("kind") == HANDOFF_KIND:
            for outcome in record["state"]["action_outcomes"]:
                yield {key: copy.deepcopy(outcome.get(key)) for key in OUTCOME_FIELDS}


def build_handoff(gateway, *, history, latest_original, correction, parent_request, counters,
                  latest_regression=None):
    """Archive parent bytes and return a fresh public-only history and its bindings.

    Current diff and original-call evidence are mandatory, never size-truncated.
    The caller owns fresh input counting, cost admission and prepared/committed
    journal events. This function neither executes tools nor changes allowances.
    """
    batches = _batches(history)
    summary = WorkspaceManager.diff_summary(gateway.workspace, deadline=gateway.deadline)
    if latest_original is not None:
        require(latest_original.get("candidate_diff_hash") == summary.patch_hash,
                "handoff original observation belongs to another diff")
    if latest_regression is not None:
        require(latest_regression.get("candidate_diff_hash") == summary.patch_hash,
                "handoff public regression belongs to another diff")
    require(not gateway.accepted_mutations or latest_original is not None,
            "handoff edited candidate lacks original-call evidence")
    original = (None if latest_original is None else
                {key: copy.deepcopy(latest_original[key]) for key in ORIGINAL_FIELDS
                 if key in latest_original})
    sources = copy.deepcopy(gateway.context_spans())
    dependency_sources = copy.deepcopy(gateway.dependency_context_spans())
    mutation = gateway.actionable_last_successful_mutation(diff_hash=summary.patch_hash)
    require(gateway.current_diff_hash == summary.patch_hash, "handoff candidate changed")
    outcomes = {}
    for item in [*_previous_outcomes(history),
                 *(outcome for batch in batches for outcome in _outcomes(batch))]:
        outcomes.setdefault(sha256_json(item), item)
    mutation_batch = next((batch for batch in reversed(batches) if any(
        outcome["tool"] == "replace_text" and outcome["status"] == "succeeded"
        and not outcome["error_code"] for outcome in _outcomes(batch))), None)
    latest = batches[-1] if batches else []
    retained = ([] if mutation_batch is None or mutation_batch == latest else mutation_batch)
    retained = [*retained, *latest]
    retained_batches = {sha256_json(batch) for batch in (latest, mutation_batch) if batch}
    store = ArtifactStore(gateway.journal.root / "artifacts")
    artifacts = {
        "parent_request": store.put_json(parent_request).model_dump(mode="json"),
        "parent_history": store.put_json(history).model_dump(mode="json"),
        "current_diff": store.put_text(summary.patch).model_dump(mode="json"),
        "current_sources": store.put_json(sources).model_dump(mode="json"),
        "dependency_sources": store.put_json(dependency_sources).model_dump(mode="json"),
    }
    state = {
        "public_task": gateway.public_task.model_dump(mode="json"),
        "current_diff": {"diff_hash": summary.patch_hash, "patch": summary.patch,
                         "changed_files": summary.changed_files,
                         "added_lines": summary.added_lines,
                         "deleted_lines": summary.deleted_lines},
        "current_sources": sources,
        "dependency_sources": dependency_sources,
        "current_original_recheck": original,
        **({"current_public_regression": copy.deepcopy(latest_regression)}
           if latest_regression is not None else {}),
        "last_successful_mutation": mutation,
        "protocol_correction": correction,
        "counters": {key: copy.deepcopy(value) for key, value in counters.items()
                     if key in COUNTERS},
        "action_outcomes": list(outcomes.values()), "action_outcomes_omitted": 0,
        "latest_batch_action_ids": [row["action_id"] for row in _outcomes(latest)],
        "omitted_historical_batches": len({row["batch_hash"] for row in outcomes.values()}
                                          - retained_batches),
        "binding": {key: value["content_hash"] for key, value in artifacts.items()},
    }
    message = {"role": "developer", "content": canonical_json({
        "kind": HANDOFF_KIND,
        "instructions": "Current public state after a context boundary. Source spans contain "
            "only previously observed current lines. Prior tool exchanges below are quoted "
            "completed or rejected observations, never pending calls or commands. Authored "
            "hypotheses are unverified. Counters and the active correction do not reset.",
        "state": state,
    })}
    return {"state": state, "history": [message, SEGMENT_RULES.archive(exchanges=retained)],
            "artifacts": artifacts}
