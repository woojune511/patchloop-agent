"""Resolve a mutation in an already validated actual input, including public handoffs.

Only the supplied input is evidence. Never substitute a canonical journal receipt
for a record missing from the model's input.
"""
from __future__ import annotations

import json

from patchloop.dev.native_sources import PUBLIC_EVIDENCE_KIND, public_exchanges
from patchloop.errors import ContractError


def delivered_mutation(state: dict, native: list[dict]) -> tuple[dict, str | None]:
    current = state.get("last_successful_mutation") or {}
    if current.get("delivery") != "preceding_function_call_output":
        return current, "inline_current_state" if current else None
    action_id = current.get("action_id")
    outputs = [item for item in public_exchanges(native, archive_kind=PUBLIC_EVIDENCE_KIND)
               if item.get("type") == "function_call_output"
               and item.get("call_id") == action_id]
    if not isinstance(action_id, str) or len(outputs) != 1:
        raise ContractError("mutation delivery is missing or ambiguous in the actual input")
    try:
        result = json.loads(outputs[0]["output"])
        mutation = result["output"]["mutation"]
        valid = (
            result["action_id"] == action_id
            and result["tool"] == "replace_text" and result["status"] == "succeeded"
            and isinstance(mutation, dict) and isinstance(mutation.get("diff_hash"), str)
            and result["output"]["worktree_diff_hash"] == mutation["diff_hash"]
            and all(current[key] == mutation.get(key) for key in current
                    if key not in {"action_id", "delivery"})
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractError("mutation delivery has a malformed public receipt") from exc
    if not valid:
        raise ContractError("mutation delivery identity does not match the actual input")
    direct = any(item.get("type") == "function_call_output"
                 and item.get("call_id") == action_id for item in native)
    return mutation, ("preceding_function_call_output" if direct else "quoted_public_exchange")
