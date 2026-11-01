# Affected input families in the existing post-edit review

2026-10-31. Local implementation; no live experiment or repair-gain claim.

## Problem and decision

The [fresh task 8/10 public audit](2026-10-31-verification-continuity-0810-results.md)
showed useful source repair and passing controls without establishing the complete
affected input family. For task 8, an existing public parameter table described
related types, but the agent read the setter and searched writer tests without
acquiring that table. The information was never read, rather than lost in a later
context handoff. The [operator failure attribution](2026-10-31-continuity-0810-failure-attribution.md)
keeps private specifics outside solver guidance and distinguishes a source-scope
omission from additional benchmark expectations.

This matters because a shared rule can be partially repaired while the selected
tests and normal control all pass. Existing instructions already said to check
sibling failures, map contracts to cases and preserve original inputs/assertions.
More retention, another generic reminder or a larger budget does not directly
address acquisition of the public scope definition. The user selected a small
change to the existing review, not a task-specific patch or hidden-oracle hint.

The hypothesis is that an explicit public scope comparison will help the model
notice unexamined members and choose a useful discriminating case. Alternatives
remain: the model may ignore the instruction, misread a family definition, infer
an incorrect invariant, or correctly determine that a listed member is outside
the changed rule. Source navigation may also be expensive or ambiguous. Local
delivery tests cannot establish discovery, correct scope or improved repair.

## Change

Only `BEHAVIOR_CHANGE_INSTRUCTIONS` in `patchloop/dev/repair_guidance.py` changes
production behavior. The existing post-edit request now asks the model to:

1. For type/option branches, dispatch tables or exception lists, derive the affected
   input family from public definitions, registries, callers or pre-existing
   parameterized tests. The edited list alone is not evidence of completeness.
2. Compare that scope with edited members and adequate current-diff results. Use
   existing reads/searches if missing scope evidence could change the repair.
3. Group relevant unverified members of a small finite family in a parameterized
   probe/test, or select uncovered branch representatives for a larger family.
   Preserve the publicly grounded caller, input construction and outcome assertion
   while varying the member; keep a normal control and disclose missing setup
   assumptions. Reuse adequate results.
4. Retain the existing success/guard review and connect a found violation to an
   executed regression, repair or undo, then checks of the resulting diff.

This is a replacement within the next existing useful decision. No scope extractor,
AST classifier, persistent checklist, tool, plan field, review call, probe quota,
test mandate or completion gate is added. The host does not infer semantic coverage
from a source table or a passing command. General repair instructions, tool schemas,
registered checks, task packages, private grading and budget settings stay unchanged.
The existing planning contract binds the changed guidance hash; historical identities
and journals remain intact. Planning-off identities stay unchanged.

The post-edit review text grows from 962 to 1,668 characters (+706). The 499-character
shared repair guidance is unchanged. This is additional text at the existing review
decision, not a cost or latency reduction claim. Current brief-v1 tool identity is
`sha256:a08947ccc21442a914419f9b82ddfbdc05af7ee4f8cca64b60cac84a8b270dff`;
the nested guidance hash is
`sha256:acec98456f7ca9a766bb0f17562783296685c4042b10504c18c80167a3363f26`.

The change is task-independent. It contains no benchmark task IDs, type names from
the investigated task, private expected values, API additions or reference patches.
For an underspecified public task, an agent can still improve public behavioral
evidence but cannot be expected to infer an arbitrary undisclosed API contract.

## Validation and remaining question

Existing focused tests cover exact guidance delivery through actual append/segmented
requests, normal and completion contexts, preservation of source/plan/evidence and
available tools/budgets/gates, current mutation identity, single consumption and
recovery. A contract-identity control checks that changing this nested guidance
changes enabled planning identities without changing tool schemas, contract shape
or planning-off identities. These tests do not emulate a model discovering a family.

Local command receipts, JUnit reports, source/contract hashes and final validation
are stored in [the external evidence directory](C:/pt/family-scope-review-20261031-v1/).
Focused owner/contract tests: **66 PASS in 21.10 seconds** (22.555-second command
wall), including three isolated native mock scenarios. Fast suite: **1,363 PASS /
1 host-symlink SKIP in 310.94 seconds** (312.540-second command wall), four workers,
no worker restart, including its isolated mock evaluations. Ruff passed. No prior
run artifact or closed history record is edited. There are no new provider or
benchmark calls.

The first Ruff run found one 101-character new test function signature; wrapping
that signature fixed it. The initial failed receipt is preserved. The final Ruff
receipt and CAS were durable, but the external helper then used an invalid journal
ID containing a hyphen. Its metadata was appended to a valid journal from the saved
receipt without repeating Ruff. This was local evidence postprocessing, not a
runtime, model or target failure. Final runtime hash:
`sha256:dcc04d586ddb7554c3fc2c735577f6ca91676b0dcb0b5ca172d53a0b0c6acaa7`.

The next live evidence would need to show that the agent actually obtains the
public family definition, relates it to the changed rule, executes a useful missing
case and changes or justifies the repair accordingly. More searches, more probes
or successful submission alone are not success criteria. Public behavioral repair,
independent acceptance, cost and time must remain separate outcomes. No such live
execution or causal improvement has been measured or scheduled in this change.
