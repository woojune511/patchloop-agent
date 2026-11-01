"""Pure preflight diagnostics and argument-based correction receipts.

Only deterministic, fresh request validation participates. Completed executions,
setup failures and action-id recovery keep their existing semantics.
"""

from __future__ import annotations

import copy

from pydantic import ValidationError

from patchloop.errors import ContractError, RecoveryError
from patchloop.util import sha256_json

POLICY = "probe-request-correction-v1"


def error(message, *paths):
    return ContractError(message, details={"invalid_fields": [
        {"path": path, "requirement": message} for path in paths
    ]})


def fields(exc, *, prefix=""):
    if exc is None:
        return []
    if isinstance(exc, ValidationError):
        return [{"path": prefix + "/" + "/".join(str(part) for part in item["loc"]),
                 "requirement": item["msg"]}
                for item in exc.errors(include_url=False, include_input=False)]
    return copy.deepcopy(getattr(exc, "details", {}).get("invalid_fields") or [
        {"path": "/", "requirement": str(exc)[:500]},
    ])


def _value(arguments, path):
    value = arguments
    if path == "/":
        return True, value
    for part in path.lstrip("/").split("/"):
        if not isinstance(value, dict) or part not in value:
            return False, None
        value = value[part]
    return True, value


def review(arguments, exc, events, *, public_task_hash, kind):
    """Compare with the latest rejected fresh request, never prose or action IDs.

    The receipt is saved at admission and reused on crash recovery. A successful
    preflight closes the correction chain, even when execution later fails.
    """
    if arguments.get("replay_action_id") is not None or isinstance(exc, RecoveryError):
        return None
    receipt = {
        "policy": POLICY, "public_task_hash": public_task_hash,
        "arguments_hash": sha256_json(arguments), "invalid_fields": fields(exc),
        "correction": {"status": "not_attempted"},
    }
    for event in reversed(events):
        row = event["payload"]
        if event["event_type"] != "action_started" or row.get("tool") != "run_probe":
            continue
        admission = row.get("probe_request", {})
        prior = admission.get("validation")
        if (admission.get("status") != "rejected" or not prior
                or prior.get("policy") != POLICY
                or prior.get("public_task_hash") != public_task_hash):
            break
        changed = [item["path"] for item in prior["invalid_fields"]
                   if _value(arguments, item["path"])
                   != _value(row["arguments"], item["path"])]
        same = receipt["arguments_hash"] == prior["arguments_hash"]
        status = ("different_purpose" if admission.get("kind") not in {kind, "unclassified"}
                  else "unchanged" if same else "invalid" if exc is not None
                  else "corrected" if changed else "not_corrected")
        receipt["correction"] = {
            "status": status, "previous_action_id": row["action_id"],
            "changed_error_fields": changed,
        }
        break
    return receipt
