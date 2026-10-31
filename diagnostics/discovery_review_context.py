"""Project saved public facts into a fixed-candidate diagnostic's actual capabilities.

This changes request delivery only. Source checkpoints, native exchanges, evidence
identities and execution authority remain with their existing owners.
"""

from __future__ import annotations

import copy
import json
from typing import Any

from patchloop.dev.conversation import TASK_MESSAGE
from patchloop.util import canonical_json

DIAGNOSTIC_TASK_MESSAGE = {
    "role": "user",
    "content": (
        "Review the fixed candidate against the supplied public_task using this request's "
        "offered tools. Check execution feasibility against their schemas and the supplied "
        "probe environment. Record public observations with report_discovery; candidate "
        "editing, normal submission and independent evaluation are outside this diagnostic."
    ),
}

_NORMAL_CONTROLS = (
    "remaining_visible_check_ids", "ready_to_submit", "completion_guidance", "completion_stage",
    "action_horizon", "segment_handoff", "mutation_scope_budget", "mutation_readiness",
    "commitment_signal", "protocol_correction", "diagnosis_stage", "repair_stage", "repair_intent",
    "completion_cost", "minimum_completion_tool_actions", "completion_budget_tool_actions",
)
_ACQUISITION_LIMITS = (
    "max_investigation_actions", "max_original_attempts", "max_preparation_actions",
    "max_request_errors", "preparation_actions_remaining",
)
_RECOVERY_RESOURCES = (
    "preparation_available", "preparation_allowance_available",
    "preparation_model_turns_available", "preparation_tool_actions_available",
    "preparation_limit", "preparation_completion_calls_reserved",
    "preparation_completion_tool_actions_reserved", "preparation_request_correction_reserved",
    "preparation_required_for_completion", "preparation_blocked_reason", "offered_tools",
    "blocks_submission",
)


def _reproduction(review: dict[str, Any], *, replay_offered: bool) -> None:
    review.pop("submission_gate", None)
    review["interpretation"] = (
        "Saved public verification evidence, not current workflow or execution authority. "
        "Statuses, cases and recorded counters retain their source-run meaning; only the "
        "tools and remaining budget in this request authorize new diagnostic actions."
    )
    completion = review.get("completion")
    if isinstance(completion, dict):
        completion.pop("blocks_submission", None)
        completion.pop("early_replay_reusable", None)
        completion["interpretation"] = (
            "Saved original-case evidence; missing evidence remains unverified. This "
            "diagnostic does not run the source workflow's automatic replay or recovery."
        )
        obligation = completion.get("original_obligation")
        if isinstance(obligation, dict):
            for key in _ACQUISITION_LIMITS:
                obligation.pop(key, None)
            obligation["accounting_scope"] = "source_run_history_not_current_diagnostic_budget"
        # These are saved diagnosis/recovery records, not new action grants. Keep
        # case identities, observations and attempted-action records unchanged.
        for name in ("first_observation", "helper_correction", "observation_correction",
                     "repair_path", "repair_prediction"):
            control = completion.get(name)
            if not isinstance(control, dict):
                continue
            for key in ("available", "test_available"):
                if key in control:
                    control[key] = False
            for key in _RECOVERY_RESOURCES:
                control.pop(key, None)
    followup = review.get("probe_followup")
    if not isinstance(followup, dict):
        return
    replay = followup.get("replay")
    if isinstance(replay, dict) and not replay_offered:
        replay["available"] = False
        replay["reason"] = "replay_reference_not_offered_in_this_diagnostic"
        replay.pop("arguments", None)
        replay.pop("argument_scope", None)
    followup["guidance"] = (
        "Compare these saved public observations with current evidence. Use only an "
        "offered tool and its actual schema/environment for a new observation; saved "
        "action IDs identify evidence and do not independently authorize replay."
    )


def _state(state: dict[str, Any], tools: list[dict[str, Any]]) -> None:
    for key in _NORMAL_CONTROLS:
        state.pop(key, None)
    state["workflow_gate"] = "fixed_candidate_review"
    state["diagnostic_mode"] = "fixed_candidate_public_review"
    state["available_tool_names"] = [tool["name"] for tool in tools]
    for name in ("repair_recheck", "probe_recheck"):
        control = state.get(name)
        if isinstance(control, dict):
            control["enabled"] = False
            control["policy"] = "No automatic recheck is scheduled by this fixed-candidate review."
    review = state.get("reproduction_review")
    if isinstance(review, dict):
        replay_offered = any(
            tool["name"] == "run_probe"
            and "replay_action_id" in tool.get("parameters", {}).get("properties", {})
            for tool in tools
        )
        _reproduction(review, replay_offered=replay_offered)


def _report_annotation(tool: dict[str, Any]) -> None:
    annotation = tool.get("parameters", {}).get("properties", {}).get("turn_decision")
    if not isinstance(annotation, dict):
        return
    # An external saved-state diagnostic may already offer an optional review.
    # Align that annotation; the ordinary seven-field report stays unchanged.
    branches = annotation.get("anyOf", [annotation])
    for branch in branches:
        properties = branch.get("properties", {})
        if "mode" in properties:
            properties["mode"] = {"type": "string", "enum": ["finish"]}
        if "evidence_goal" in properties:
            properties["evidence_goal"] = {
                "type": "null", "description": "Exactly null for terminal reporting.",
            }


def project_request(request: dict[str, Any]) -> dict[str, Any]:
    """Pure, idempotent projection; apply after all overlays and before freezing.

    Only recognized current-state envelopes and the normal task continuation are
    rewritten. Historical archives, native calls/results and arbitrary public
    messages are untouched. No source retrieval, tool execution or semantic gate.
    """
    projected = copy.deepcopy(request)
    tools = projected.get("tools", [])
    reports = [tool for tool in tools if tool.get("name") == "report_discovery"]
    if not reports:
        return projected
    for tool in reports:
        _report_annotation(tool)
    for item in projected.get("input", []):
        if item == TASK_MESSAGE:
            item.update(DIAGNOSTIC_TASK_MESSAGE)
            continue
        content = item.get("content")
        if item.get("role") != "developer" or not isinstance(content, str):
            continue
        try:
            envelope = json.loads(content)
        except json.JSONDecodeError:
            continue
        if (not isinstance(envelope, dict) or envelope.get("kind") != "harness_current_state"
                or not isinstance(envelope.get("state"), dict)):
            continue
        _state(envelope["state"], tools)
        item["content"] = canonical_json(envelope)
    return projected
