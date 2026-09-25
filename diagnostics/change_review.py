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


def review_request(state, events):
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
    return {"policy": POLICY, "subject": subject, "instruction": INSTRUCTION}
