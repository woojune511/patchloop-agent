"""Task-neutral, once-per-change review request for fresh seeded diagnostics.

The journal determines the subject and timing. The model chooses the question and
action through the unchanged public tool schema. Delivery is not completed review.
"""

from __future__ import annotations

FIELD = "change_review_request"
POLICY = "change-review-v1"
INSTRUCTION = (
    "Before choosing your next action, examine the changed code in current_diff and, "
    "when present, last_successful_mutation. What distinct inputs or execution states "
    "does this change treat alike? Does the public task justify treating them alike? "
    "Do not assume a defect. If an important distinction is unresolved, state the "
    "specific question, public requirement and smallest distinguishing observation "
    "in your existing turn_decision.basis, then choose an available action to obtain "
    "the missing evidence. Use existing verification_updates for a concern that must "
    "remain open. After observing a result, explain how its answer changes the next "
    "action. A successful check does not by itself answer that particular question. "
    "Keep this concise; all existing actions and submission rules remain available."
)
VALUE_ORIGIN_POLICY = "value-origin-review-v1"
VALUE_ORIGIN_INSTRUCTION = (
    "Before choosing your next action, examine the changed code in current_diff and, "
    "when present, last_successful_mutation. Select one changed condition or newly "
    "forwarded value whose origin could affect the public task's required behavior. "
    "Trace that value through its assignments, default substitution and normalization "
    "using current registered source evidence. Distinguish its effective value from "
    "how it was produced: which input or state distinctions survive, and which are "
    "lost before the changed code uses it? If that path is unknown, state the specific "
    "missing relation and choose an available read or search to resolve it. If the "
    "public requirement distinguishes cases that this path merges, choose the smallest "
    "available observation comparing those cases even when their effective values match. "
    "Derive expected behavior from the public requirement. Do not assume a defect or "
    "require different behavior merely "
    "because the origins differ. State the question and supporting evidence concisely "
    "in your existing turn_decision.basis; use existing verification_updates for a "
    "concern that remains open. After an observation, explain how its answer changes "
    "the next action. If no relevant origin distinction remains unresolved, continue "
    "normally. All existing actions and submission rules remain available."
)
INSTRUCTIONS = {POLICY: INSTRUCTION, VALUE_ORIGIN_POLICY: VALUE_ORIGIN_INSTRUCTION}


def review_request(state, events, *, policy=POLICY):
    """Reconstruct eligibility without new receipts, mutable counters or source reads.

    A response after the subject consumes this request, irrespective of whether the
    model follows it. Failed/no-op mutations and segment boundaries cannot re-arm it.
    An imported seed is explicitly distinguished from a new agent tool mutation.
    """
    subject, fresh, last_diff = None, False, None
    for event in events:
        kind, payload = event["event_type"], event["payload"]
        if kind == "diagnostic_candidate_seeded":
            last_diff = payload["seed_hash"]
            subject = {"origin": "imported_model_candidate", "action_id": None,
                       "diff_hash": last_diff}
            fresh = True
        elif kind == "action_finished":
            result = payload["result"]
            if result["tool"] != "replace_text" or result["status"] != "succeeded":
                continue
            diff_hash = (result.get("output") or {}).get("worktree_diff_hash")
            if diff_hash and diff_hash != last_diff:
                last_diff = diff_hash
                subject = {"origin": "successful_agent_mutation",
                           "action_id": result["action_id"], "diff_hash": diff_hash}
                fresh = True
        elif kind == "turn_decision_recorded":
            fresh = False
    if not fresh or subject is None or subject["diff_hash"] != state["current_diff"]["patch_hash"]:
        return None
    return {"policy": policy, "subject": subject, "instruction": INSTRUCTIONS[policy]}
