"""Shared repair guidance; no new tool, verification gate or execution authority."""

INSTRUCTIONS = (
    "Ground behavior in public contracts, not repair assumptions. Test material "
    "assumptions or narrow edits; check sibling failures and success guards. Use observed "
    "APIs; probes must observe their named outcome with a normal control. Before verifying, "
    "compare inputs/setup/assertions with current-diff results. Reuse equivalent success; "
    "renaming adds no case. Explain new cases, incomplete observations or post-edit rechecks "
    "in basis if offered. not_assessed is no host judgment, not an unfinished case.\n"
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
