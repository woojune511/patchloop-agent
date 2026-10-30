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
