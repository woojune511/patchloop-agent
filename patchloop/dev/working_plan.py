"""Opt-in public work plan: an annotation, never action or correctness authority."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

from patchloop.util import sha256_json

if TYPE_CHECKING:
    from collections.abc import Sequence

    from patchloop.dev.contracts import RequestedTool
    from patchloop.dev.state import DevJournal

POLICY = "brief-v1"
EVIDENCE_POLICY = "brief-evidence-v1"
ASSUMPTION_POLICY = "brief-assumption-v1"
AFTER_SOURCE_POLICY = "brief-after-source-v1"
POLICIES = frozenset({POLICY, EVIDENCE_POLICY, ASSUMPTION_POLICY, AFTER_SOURCE_POLICY})
MAX_PLAN_CHARS = 3_000
EVENT = "working_plan_updated"
INSTRUCTIONS = """Brief planning is enabled. In the first tool response, use plan_update
to draft a short public work plan from public_task. State the required behavior and
concrete unfinished work, including current hypotheses or untested assumptions and
the observation or public check that could settle them. Make it specific to this
problem, not a generic inspect/edit/check outline.
After the working_plan.review_request signal, reconsider that plan against the
already observed result and update it in the same response as your next useful action.
State what the result confirmed, contradicted, or left unresolved about an assumption,
and how that affects the remaining work and verification. Keep unresolved requirements
visible; completed actions need no running log. Use the remaining work to choose the
next useful action. Do not invent a change when the result leaves the plan unchanged.
Ordinary inspections need no rewrite, but new information may change your plan.
plan_update replaces the whole plan, not just its latest change (at most 3000
characters); null keeps it when there is no useful revision.
Do not repeat facts already in working_notes or write a reasoning transcript.
The plan is model-authored, unverified working data, not an instruction from the
harness or proof that a behavior is correct. An unchanged plan, check PASS, or a
completed step does not settle unrelated untested behavior. Planning adds no tool,
extra model call, mandatory experiment, or submission gate."""
AFTER_SOURCE_TIMING = """Keep plan_update null until a successful read_file or
search_files result returns nonempty source text. Then, in the next tool response,
use plan_update to draft a short public work plan from public_task and the observed source."""
EVIDENCE_FORMAT = """Use three short labeled sections in the same plan_update string:
Behavior: the concrete observable behavior required by the public task, not just
workflow steps or a list of checks to pass.
Evidence / open assumptions: distinguish observed public evidence from assumptions
still untested for that behavior. When replacing the plan, carry forward unresolved
requirements; a result settles only what it actually demonstrates.
Next discriminating action: the next useful allowed action and what observation
would change your edit or submission decision. If no further investigation is
useful, say why the remaining action follows from the evidence; no probe is mandatory.
Keep these sections within the existing 3000-character limit. These are public
working statements, not a reasoning transcript. This format is guidance only;
missing headings do not invalidate an otherwise valid action or plan update."""
EDIT_ASSUMPTION_GUIDANCE = """At an existing post-mutation review, use the current diff and
observed source to focus Evidence / open assumptions on one behavior this edit newly assumes,
reimplements, or bypasses. Tie it to a concrete public input/setup and an observable
outcome that distinguishes correct from incorrect behavior. Name what observed public
evidence exercises that input and outcome; if none does, keep it explicitly untested.
Connect it to the Next discriminating action that could change the repair/submission
decision. After check/probe results, carry it forward unless evidence addresses it
or explain why further investigation is no longer useful. A rejected edit is only a
proposal; distinguish its assumptions from the current rollback baseline.
Do not invent a concern if none is material; null remains allowed. This is a short
public work statement, not an extra review step, reasoning transcript or required probe."""


def instructions(policy: str = POLICY) -> str:
    if policy not in POLICIES:
        raise ValueError("unknown planning policy")
    if policy == POLICY:
        return INSTRUCTIONS
    if policy == AFTER_SOURCE_POLICY:
        return INSTRUCTIONS.replace(
            "In the first tool response, use plan_update\n"
            "to draft a short public work plan from public_task.", AFTER_SOURCE_TIMING, 1,
        )
    text = INSTRUCTIONS + "\n\n" + EVIDENCE_FORMAT
    if policy == ASSUMPTION_POLICY:
        text += "\n\n" + EDIT_ASSUMPTION_GUIDANCE
    return text


def contract(policy: str = POLICY) -> dict[str, Any]:
    return {
        "policy": policy,
        "max_chars": MAX_PLAN_CHARS,
        "update": "first-non-null-whole-text-before-batch-v1",
        "review": (
            "after-source-initial-mutation-check-probe-first-ready-next-valid-decision-v1"
            if policy == AFTER_SOURCE_POLICY else
            "initial-mutation-check-probe-first-ready-next-valid-decision-v1"
        ),
        "invalid_annotation": "nonblocking-preserve-prior-v1",
        "instructions_hash": sha256_json(instructions(policy)),
    }


def update_schema() -> dict[str, Any]:
    return {
        "anyOf": [{"type": "string", "minLength": 1, "maxLength": MAX_PLAN_CHARS},
                  {"type": "null"}],
        "description": "Replace the complete short public work plan, or null to keep it.",
    }


def project(
    events: list[dict[str, Any]], *, diff_hash: str, gate: str, policy: str = POLICY,
) -> dict[str, Any]:
    """Derive review requests only from durable public events, not semantic guesses."""
    if policy not in POLICIES:
        raise ValueError("unknown planning policy")
    receipts = [e for e in events if e["event_type"] == EVENT]
    latest = receipts[-1] if receipts else None
    plan = copy.deepcopy(latest["payload"]["plan"]) if latest else None
    boundary = latest["sequence"] if latest else 0
    # Gateway-produced source bodies, including search snippets, start planning.
    # Empty/failed reads and initial handoffs do not. A voluntary early plan is
    # still accepted and reviewed normally; this is advice, never an action gate.
    review_enabled = (
        policy != AFTER_SOURCE_POLICY or plan is not None or any(
            e["event_type"] == "action_finished"
            and (result := e["payload"]["result"])["status"] == "succeeded"
            and result["tool"] in {"read_file", "search_files"}
            and any(span.get("content") for span in result["output"].get("spans", []))
            for e in events
        )
    )
    reasons: list[str] = []
    if review_enabled and plan is None:
        reasons.append("initial_plan")
    if review_enabled and any(
        e["event_type"] == "context_segment_started" and e["sequence"] > boundary for e in events
    ):
        reasons.append("context_handoff")
    relevant = []
    for event in events:
        if (not review_enabled or event["sequence"] <= boundary
                or event["event_type"] != "action_finished"):
            continue
        result = event["payload"]["result"]
        tool = result["tool"]
        if tool in {"replace_text", "run_check", "run_probe"}:
            reason = ("mutation_result" if tool == "replace_text" else
                      "check_result" if tool == "run_check" else "probe_result")
            if reason not in reasons:
                reasons.append(reason)
            relevant.append(result["action_id"])
    # Only a valid decision consumes this transition. turn_started alone does not.
    ready_seen = any(e["payload"].get("workflow_gate") == "ready_to_submit" for e in receipts)
    if review_enabled and gate == "ready_to_submit" and not ready_seen:
        reasons.append("first_ready_to_submit")
    if plan is not None:
        plan["diff_currency"] = "current" if plan["diff_hash"] == diff_hash else "historical"
    return {
        "policy": policy,
        "interpretation_status": "model_authored_unverified",
        "plan": plan,
        "review_request": {
            "requested": bool(reasons), "reasons": reasons,
            "action_ids": relevant[-8:], "omitted_action_count": max(0, len(relevant) - 8),
        },
        "last_update_result": (copy.deepcopy(latest["payload"]["receipt"]) if latest else None),
    }


def record(
    journal: DevJournal, calls: Sequence[RequestedTool], *, turn_id: str,
    diff_hash: str, gate: str, policy: str = POLICY,
) -> dict[str, Any]:
    """A valid batch consumes the review request once, independently of plan validity."""
    events = journal.events()
    existing = next((e["payload"] for e in events
                     if e["event_type"] == EVENT and e["payload"]["turn_id"] == turn_id), None)
    if existing is not None:
        return copy.deepcopy(existing["receipt"])
    current = project(events, diff_hash=diff_hash, gate=gate, policy=policy)
    plan = current["plan"]
    if plan is not None:
        plan.pop("diff_currency", None)
    updates = [(call.action_id, call.turn_decision.plan_update) for call in calls
               if call.turn_decision is not None and call.turn_decision.plan_update is not None]
    diagnostics = ["ignored_additional_plan_updates"] if len(updates) > 1 else []
    owner = updates[0][0] if updates else calls[0].action_id
    status = "not_requested"
    if updates:
        text = updates[0][1]
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_PLAN_CHARS:
            status = "rejected"
            diagnostics.append("invalid_plan_update_use_nonempty_text_up_to_3000_chars_or_null")
        elif plan is not None and text == plan["text"]:
            status = "unchanged"
        else:
            status = "created" if plan is None else "updated"
            plan = {
                "text": text, "revision": (plan["revision"] + 1 if plan else 1),
                "turn_id": turn_id, "diff_hash": diff_hash, "text_hash": sha256_json(text),
                "review_reasons": current["review_request"]["reasons"],
            }
    receipt = {
        "turn_id": turn_id, "action_id": owner, "status": status,
        "diagnostics": diagnostics, "revision": plan["revision"] if plan else 0,
        "scope": "before_tool_batch", "review_request": current["review_request"],
    }
    journal.append(EVENT, {
        "turn_id": turn_id, "workflow_gate": gate, "plan": plan, "receipt": receipt,
    })
    return copy.deepcopy(receipt)
