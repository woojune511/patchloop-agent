"""Separate recorded inspection intent from observations delivered to the model."""

from __future__ import annotations

import copy
from collections.abc import Collection
from typing import Any

from patchloop.dev.contracts import DEV_READ_TOOLS


def _decision_ref(action_id: str | None, delivery: str) -> dict[str, Any]:
    return {
        "action_id": action_id,
        "delivery": delivery,
        "kind": "model_authored_pre_observation_intent",
    }


def project_inspection_result(
    result: dict[str, Any], *, native_action_ids: Collection[str] = (),
) -> dict[str, Any]:
    """Keep observed output exact; refer to intent already in the native call."""

    projected = copy.deepcopy(result)
    if projected.get("tool") in DEV_READ_TOOLS:
        output = projected.get("output", {})
        if projected["action_id"] in native_action_ids and "inspection_intent" in output:
            output.pop("inspection_intent")
            output["inspection_intent_ref"] = _decision_ref(
                projected["action_id"], "preceding_function_call_arguments",
            )
    return projected


def project_inspection_context(
    payload: dict[str, Any], *, native_action_ids: Collection[str] = (),
) -> dict[str, Any]:
    """Project known intent fields only; never deduplicate source or note prose.

    Context-only adapters retain the latest intent once in its tool result. Native
    adapters receive it in the original call arguments instead. Older intentions
    stay in the journal, not repeatedly asserted by derived observation cards.
    """

    projected = copy.deepcopy(payload)
    latest = projected.get("latest_tool_results", [])
    result_ids = {
        result["action_id"] for result in latest
        if result.get("tool") in DEV_READ_TOOLS
        and "inspection_intent" in result.get("output", {})
    }

    def reference(action_id):
        delivery = (
            "preceding_function_call_arguments" if action_id in native_action_ids
            else "latest_tool_result.inspection_intent" if action_id in result_ids
            else "journal_only"
        )
        return _decision_ref(action_id, delivery)

    if "latest_tool_results" in projected:
        projected["latest_tool_results"] = [
            project_inspection_result(result, native_action_ids=native_action_ids)
            for result in latest
        ]
    ledger = projected.get("evidence_ledger", {})
    intent = ledger.get("latest_inspection_intent")
    if isinstance(intent, dict):
        action_id = intent.get("action_id", intent.get("decision_ref", {}).get("action_id"))
        intent.pop("basis", None)
        intent.pop("evidence_goal", None)
        intent["decision_ref"] = reference(action_id)
    for outcome in ledger.get("recent_inspection_outcomes", []):
        outcome.pop("evidence_goal", None)
        outcome["decision_ref"] = reference(outcome.get("action_id"))
    for card in projected.get("recent_attempt_result_next_question", []):
        if card.get("attempt") == "inspect":
            actions = card.get("result", {}).get("actions", [])
        elif card.get("attempt") in DEV_READ_TOOLS:
            actions = [card]
        else:
            continue
        for action in actions:
            if "turn_decision" in action or "turn_decision_ref" in action:
                action.pop("turn_decision", None)
                action["turn_decision_ref"] = reference(action.get("action_id"))
    return projected
