"""Opt-in public work plan: an annotation, never action or correctness authority."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

from patchloop.dev import scope_review
from patchloop.dev.mutation_tools import MUTATION_TOOLS
from patchloop.dev.repair_guidance import BEHAVIOR_CHANGE_INSTRUCTIONS
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
MAX_REASON_CHARS = 800
EVENT = "working_plan_updated"
INSTRUCTIONS = """The plan orders remaining work. Keep unresolved verification purposes in concerns;
plan changes do not resolve them. Record observations/interpretations in working notes,
not as verified plan facts.
Use annotations only where the current tool schema offers them. When a result changes
the next decision, retain its scoped finding and remaining question through memory_update,
citing prior completed actions or observed source. A basis statement is not a stored note.
Use the next useful action; no separate planning response or mandatory note is needed.
Brief planning is enabled. In the first tool response, use plan_update
to draft a short public work plan from public_task. State the required behavior and
concrete unfinished work, including current hypotheses or untested assumptions and
the observation or public check that could settle them. Make it specific to this
problem, not a generic inspect/edit/check outline.
After the working_plan.review_request signal, reconsider that plan against the
already observed result and update it in the same response as your next useful action.
When review_request.behavior_change is present, apply its attached guidance
review to that mutation before carrying forward a check-then-submit plan.
Listing unknowns alone does not justify stopping. Choose observations that could change
the patch/submission decision over repeating supported examples.
Use scope_review to compare known public conditions with actual/planned case conditions
and the required observation; do not narrow the public objective to an inherited plan's
finish criterion. Explain substitutions/gaps in interpretation. Cite source_receipts
IDs and current-diff execution IDs, or mark source inference/untested. Failure/partial
output records execution, not coverage. Null preserves the review; a new diff makes
it historical. Observe the named property, retain material gaps, group related cases
with a normal control and reuse adequate current-diff evidence. Unchanged evidence
or inspections need no plan rewrite; null remains allowed.
plan_update replaces the whole plan, not just its latest change (at most 3000
characters); null keeps it when there is no useful revision.
When replacing an existing plan, supply plan_update_reason (at most 800 characters).
For removed/closed verification, preserve its original input/path/outcome and cite
current-diff executed input/assertion/result, or explain why it no longer matters.
Suite PASS or another path's success cannot substitute; do not make verification
conditional on suite failure. Tie source inference to current source and that purpose;
keep unexecuted behavior unverified. Invalid/missing reasons preserve the prior plan
without blocking actions. Latest predecessor/reason stays visible; all revisions are
journaled. At finish, assessment covers unfinished purposes even with null plan_update.
No additional check is mandatory.
Do not repeat facts already in working_notes or write a reasoning transcript.
The plan is model-authored unverified working data, not authority or proof. Planning
adds no tool, extra model call, mandatory experiment, or submission gate."""
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
        "max_reason_chars": MAX_REASON_CHARS,
        "update": "first-non-null-whole-text-with-revision-reason-v2",
        "revision_review": "latest-predecessor-and-reason-durable-unverified-v1",
        "repair_delivery": "current-plan-notes-and-review-preserved-v1",
        "behavior_change": {
            "policy": "admitted-current-mutation-next-valid-decision-v1",
            "instructions_hash": sha256_json(BEHAVIOR_CHANGE_INSTRUCTIONS),
        },
        "scope_review": scope_review.contract(),
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


def reason_schema() -> dict[str, Any]:
    return {
        "anyOf": [{"type": "string", "minLength": 1, "maxLength": MAX_REASON_CHARS},
                  {"type": "null"}],
        "description": (
            "Required when replacing an existing plan: explain any removed/closed verification "
            "purpose, the observed evidence satisfying it or why it no longer matters. "
            "Distinguish executed behavior from source inference; otherwise retain open checks. "
            "Null for an initial or unchanged plan. An invalid reason preserves the old plan."
        ),
    }


def submission_review(events: list[dict[str, Any]], diff_hash: str) -> dict[str, Any] | None:
    """Bind the submitted assessment to the plan without marking its checks verified."""
    latest = next((e for e in reversed(events) if e["event_type"] == EVENT), None)
    if latest is None or latest["payload"]["plan"] is None:
        return None
    plan = copy.deepcopy(latest["payload"]["plan"])
    plan["diff_currency"] = "current" if plan["diff_hash"] == diff_hash else "historical"
    if isinstance(plan.get("scope_review"), dict):
        plan["scope_review"] = scope_review.project(plan["scope_review"], diff_hash)
    return {"plan": plan, "assessment_ref": "assessment",
            "interpretation_status": "model_authored_unverified",
            "verification_status": "not_inferred_from_submission"}


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
        e["event_type"] in {"context_segment_started", "context_segment_prepared"}
        and e["sequence"] > boundary for e in events
    ):
        reasons.append("context_handoff")
    relevant = []
    for event in events:
        if (not review_enabled or event["sequence"] <= boundary
                or event["event_type"] != "action_finished"):
            continue
        result = event["payload"]["result"]
        tool = result["tool"]
        if tool in {"replace_text", "edit_files", "run_check", "run_tests", "run_probe"}:
            reason = ("mutation_result" if tool in MUTATION_TOOLS else
                      "check_result" if tool == "run_check" else
                      "test_result" if tool == "run_tests" else "probe_result")
            if reason not in reasons:
                reasons.append(reason)
            relevant.append(result["action_id"])
    # Only a valid decision consumes this transition. turn_started alone does not.
    ready_seen = any(e["payload"].get("workflow_gate") == "ready_to_submit" for e in receipts)
    if review_enabled and gate == "ready_to_submit" and not ready_seen:
        reasons.append("first_ready_to_submit")
    if plan is not None:
        plan["diff_currency"] = "current" if plan["diff_hash"] == diff_hash else "historical"
        if isinstance(plan.get("scope_review"), dict):
            plan["scope_review"] = scope_review.project(plan["scope_review"], diff_hash)
    review_request = {
        "requested": bool(reasons), "reasons": reasons,
        "action_ids": relevant[-8:], "omitted_action_count": max(0, len(relevant) - 8),
    }
    if review_enabled and (change := _behavior_change(events, boundary, diff_hash)):
        review_request["behavior_change"] = change
    return {
        "policy": policy,
        "interpretation_status": "model_authored_unverified",
        "plan": plan,
        "review_request": review_request,
        "last_update_result": (copy.deepcopy(latest["payload"]["receipt"]) if latest else None),
    }


def _behavior_change(
    events: list[dict[str, Any]], boundary: int, diff_hash: str,
) -> dict[str, str] | None:
    """Identify an applied change, without inferring its semantics or another gate."""
    started = {}
    change = None
    for event in events:
        payload = event["payload"]
        if event["event_type"] == "action_started" and payload.get("tool") in MUTATION_TOOLS:
            started[(payload["action_id"], payload["input_hash"])] = payload
        elif event["event_type"] == "action_finished" and event["sequence"] > boundary:
            result = payload["result"]
            if (result["tool"] not in MUTATION_TOOLS or result["status"] != "succeeded"
                    or result.get("replayed")
                    or result.get("workspace_diff_hash") != diff_hash
                    or result.get("output", {}).get("worktree_diff_hash") != diff_hash):
                continue
            admission = started.get((result["action_id"], result["input_hash"]), {})
            baseline = admission.get("baseline_diff_hash")
            if (admission.get("tool") != result["tool"]
                    or admission.get("mutation_admitted") is not True
                    or not baseline or baseline == diff_hash
                    or admission.get("mutation_expected_worktree_diff_hash") != diff_hash):
                continue
            change = {
                "action_id": result["action_id"], "input_hash": result["input_hash"],
                "baseline_diff_hash": baseline, "candidate_diff_hash": diff_hash,
                "guidance": BEHAVIOR_CHANGE_INSTRUCTIONS,
            }
    return change


def record(
    journal: DevJournal, calls: Sequence[RequestedTool], *, turn_id: str,
    diff_hash: str, gate: str, policy: str = POLICY,
    evidence_events: list[dict[str, Any]] | None = None,
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
        # Projection currency is derived, never stored as a new observation.
        if isinstance(plan.get("scope_review"), dict):
            plan["scope_review"].pop("diff_currency", None)
            for source in plan["scope_review"].get("source_evidence", []):
                source.pop("currency", None)
            for case in plan["scope_review"].get("cases", []):
                if isinstance(case.get("execution"), dict):
                    case["execution"].pop("currency", None)
    updates = [(call.action_id, call.turn_decision.plan_update,
                call.turn_decision.plan_update_reason) for call in calls
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
        elif plan is not None and (
            not isinstance(updates[0][2], str) or not updates[0][2].strip()
            or len(updates[0][2]) > MAX_REASON_CHARS
        ):
            status = "rejected"
            diagnostics.append("plan_revision_requires_reason_previous_plan_preserved")
        else:
            status = "created" if plan is None else "updated"
            prior_scope_review = plan.get("scope_review") if plan is not None else None
            previous = ({key: plan[key] for key in
                         ("text", "revision", "diff_hash", "text_hash", "turn_id")}
                        if plan else None)
            plan = {
                "text": text, "revision": (plan["revision"] + 1 if plan else 1),
                "turn_id": turn_id, "diff_hash": diff_hash, "text_hash": sha256_json(text),
                "review_reasons": current["review_request"]["reasons"],
            }
            if prior_scope_review is not None:
                plan["scope_review"] = prior_scope_review
            if previous is not None:
                plan["last_change"] = {
                    "previous_plan": previous, "reason": updates[0][2],
                    "interpretation_status": "model_authored_unverified",
                }
    receipt = {
        "turn_id": turn_id, "action_id": owner, "status": status,
        "diagnostics": diagnostics, "revision": plan["revision"] if plan else 0,
        "scope": "before_tool_batch", "review_request": current["review_request"],
    }
    reviews = [(call.action_id, getattr(call.turn_decision, "scope_review", None))
               for call in calls if call.turn_decision is not None
               and getattr(call.turn_decision, "scope_review", None) is not None]
    if reviews:
        review_owner, raw = reviews[0]
        # Trusted diagnostics may bind an externally validated public prefix.
        # It supplies reference evidence only, never planning lifecycle authority.
        observations = events if evidence_events is None else evidence_events
        review, issue = (scope_review.parse(
            raw, events=observations, diff_hash=diff_hash, turn_id=turn_id,
        ) if plan is not None else (None, "scope_review_requires_plan"))
        review_diagnostics = ([issue] if issue else [])
        if len(reviews) > 1:
            review_diagnostics.append("ignored_additional_scope_reviews")
        receipt["scope_review"] = {
            "action_id": review_owner, "status": "rejected" if issue else "applied",
            "diagnostics": review_diagnostics,
        }
        if review is not None:
            change = _behavior_change(observations, 0, diff_hash)
            if change is not None:
                review["mutation"] = {key: value for key, value in change.items()
                                      if key != "guidance"}
            plan["scope_review"] = review
    journal.append(EVENT, {
        "turn_id": turn_id, "workflow_gate": gate, "plan": plan, "receipt": receipt,
    })
    return copy.deepcopy(receipt)
