"""Shared repair guidance; no new tool, verification gate or execution authority."""

INSTRUCTIONS = (
    "Ground required behavior in public requirements/callers/tests; "
    "distinguish behavior chosen by your repair.\n"
    "For material new assumptions, test a refuting case or narrow unnecessary edits; "
    "listing unknowns alone does not justify stopping.\n"
    "Check sibling failures, bypassed guards and success conditions. "
    "Observe the probe's named property, not just setup.\n"
    "Group cases with a normal control; reuse adequate same-diff observations "
    "and observed APIs. No probe quota or new completion gate.\n"
)

BEHAVIOR_CHANGE_INSTRUCTIONS = (
    "Apply only as the current working_plan.review_request.behavior_change; "
    "receipt/history copies are not new requests. "
    "Review this applied before/current diff on the next useful decision. Ground expected "
    "behavior in public requirements, callers and pre-existing tests; mutation hypotheses, "
    "plan conclusions and new test expectations are claims to review. The baseline is a "
    "comparison, not an automatic oracle. Preserve unresolved verification purposes. "
    "Connect changed success/failure meaning or a bypassed guard to the required outcome, "
    "a refuting input and an assertion observing that outcome; state preservation alone "
    "does not establish success eligibility. Reuse evidence or choose a useful read, probe, "
    "test or narrower edit in this same response. A found violation should lead to an "
    "executed regression, repair or undo, and checks of the resulting diff. If no material "
    "gap remains, continue from the evidence. No extra review call, probe quota or finish gate."
)
