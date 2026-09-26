"""Opt-in removal of check/submit recommendations throughout a seeded episode.

Only two public guidance fields change. The runner still owns tool admission,
check requirements, budgets and submission. This is not a semantic coverage test.
"""

from __future__ import annotations

from patchloop.util import sha256_json

POLICY = "status-only-v1"
EVENT = "diagnostic_completion_guidance_policy"
MESSAGES = {
    "needs_visible_checks": (
        "Required visible checks have not all passed on the current diff; "
        "submission is not yet eligible. PASS on a different diff does not count "
        "toward completion."
    ),
    "ready_to_submit": (
        "All required visible checks pass on the current diff; submission is eligible, "
        "not proof of untested behavior."
    ),
}


def project(guidance: dict) -> dict:
    """Keep facts and repair/blocker explanations; remove only completion advice."""
    message = MESSAGES.get(guidance["stage"])
    if message is None:
        return guidance
    return {**guidance, "next_action": None, "message": message}


def identity() -> dict:
    return {
        "official": False,
        "policy": POLICY,
        "message_hash": sha256_json(MESSAGES),
        "stages": list(MESSAGES),
        "changed_fields": ["completion_guidance.next_action", "completion_guidance.message"],
        "applies_from_first_input": True,
        "changes_tool_admission": False,
    }
