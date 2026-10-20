# Why the funded SQLFluff continuations still failed

Date: 2026-10-07. Public diagnosis only; official=false, claim_eligible=false.
Source commit: `32787db1a41bef1cda7c1b4ea27798661a7002d9`.
Public execution evidence: `C:/pt/sretwhy01` and `C:/pt/sretwhy02`.
Five isolated public probes, zero provider calls, no source/patch changes.

## Question and finding

The [funded continuations](2026-10-06-cost-cap-continuation-results.md) both
submitted and failed after extra budget. Repeating "verification was omitted"
did not explain why the patches produced five spaces or whether context/tool
restrictions still caused the omission. We examined the public rule execution,
actual model inputs, action decisions, public tests and completion policy.

The surplus-whitespace hypothesis was partly right, but its proposed repair
missed an interaction with another rule and the fix-loop cycle detector.
The agent then treated passing existing regressions as confirmation of behavior
those assertions had not established. The missing verification obligation was
still visible in the final context. Budget/context availability improvements
did not fix this evidence-to-decision failure on these two trajectories.

## Executed mechanism: why the patched output is five spaces

Read-only instrumentation wrapped `_coerce_indent_to` and the top-level
`BaseSegment.apply_fixes` call while running the exact public issue through
`Linter(dialect='ansi').lint_string(..., fix=True).fix_string()`.
It did not change the fixes or tree. Observed tree text matched final output.
Workspace patch identities were checked before and after every probe.

The baseline and B2 share this rule sequence:

1. L036 moves the first field to a new line: zero leading spaces.
2. L003 inserts four, then another four: eight spaces in two segments.
3. L039 reduces one four-space segment to one: five spaces total.
4. L003 sees `[4, 1]` and correctly requests eight spaces.

The baseline edits only the first segment, leaving `[8, 1]`: nine spaces.
Both submitted patches edit the first segment and delete the second. The helper
therefore proposes eight, but the linter has already visited that exact eight-space
tree at step 2. `previous_versions` rejects the repeated state, leaving five.
B1 and B2 emit the same intended edit/delete pair in opposite list order and
both produce five; full-loop tracing was performed for baseline and B2.

Source pointers in the B2 workspace:
`src/sqlfluff/rules/L039.py:33-66` tracks newline/whitespace and reduces a selected
whitespace segment to one. `src/sqlfluff/core/linter/linter.py:378,415-425` tracks
visited raw trees and declines repeats. The traces identify the rule interaction;
no benchmark fix, reference patch, or private test was used or authored here.

Thus the earlier broad description "wrong hypothesis" needs qualification:
an extra segment really did explain the baseline nine spaces. What failed was
the assumption that normalizing that helper alone would repair the complete
default-rule pipeline. An incorrect desired-indent calculation was considered
but is contradicted by the observed eight-space target.

## Why the agent submitted the wrong repair

Public pre-edit probes showed full-default output of nine versus eight with
L003/L036 alone or sequentially. These observations suggested a wider interaction
but did not inspect actual indentation buffers or trace rule-by-rule application.
B1 source events 373/374 and B2 436/437 preserve those partial-path comparisons.
They remained in actual pre-edit and pre-finish inputs.

B1 continuation event 519 relied on its earlier sequential L036-to-L003 result
to dismiss remaining uncertainty. That experiment was on the old code and a
restricted execution path; its notes were explicitly historical. B2 event 521
planned to confirm the WITH repair through `base-regression`; after PASS, event
536 declared no remaining public uncertainty. Yet the same final input retained
unresolved concern `v1`: verify eight-space WITH output and preserve plain SELECT.

B2 original events 253/254 are a valid baseline assertion failure, not an API
failure and not a direct falsification of the surplus-segment hypothesis. Its
exact stdout/program had left the recent-probe window by the final turn, but the
failure catalog and unresolved verification notes survived. Context loss is not
a sufficient explanation for these final decisions.

Final decision resources were B1 four calls/427 solver seconds and B2 five
calls/162 seconds. Both offered probes, selected tests, reads, searches and edits,
with `closure_reason=null`. B2's earlier protected path temporarily offered
edit, then regression check; after PASS, optional verification reopened.
No test edit was attempted or rejected in either B run. The historical YAML-test
edit rejection belongs to A2 and cannot explain these two submissions.

## What 506 PASS does and does not establish

The registered command runs `pytest -q test/rules`. Static public inventory
matches the observed 506 tests: 413 YAML cases (including 29 L003 and 21 L036),
one YAML configuration check, 30 autofix, ten L003 helper, 36 general rules/config,
eight roundtrip and eight other helper tests. These are substantive regressions.

Most YAML cases select one rule via `sqlfluff/testing/rules.py:61-64`.
Combination tests also exist: the L003/L036 autofix fixture
`016_no_fix_in_template_loops` tests template-loop preservation, not this WITH
first-field relocation under the complete default rule set. Passing that suite
does not verify a newly assumed behavior merely because the agent writes it in
`expected_behavior`. Coverage instrumentation reported unknown due to unsupported
Python options; that does not prove changed lines were unexecuted.

## Runtime contribution and limits

`patchloop/dev/runner.py:581-591` suggests `finish_task` once required checks pass,
while saying eligibility is not proof of untested behavior and probes remain
appropriate for uncertainty. `patchloop/dev/model.py:95-111` likewise limits
conclusions to actual inputs and results. This finish suggestion may contribute
to premature closure, but this diagnosis does not establish its causal effect.
No new violation of the current runtime contract was demonstrated.

The observed agent failure is the substitution of old partial-path evidence and
regression PASS for verification of the current patch on the public requirement.
More capacity and restored calls made actions possible but did not make the model
choose the decisive check. Model capability, completion advice and scheduling
contributions remain unseparated; two continuations on one task cannot establish
a general agent-quality cause or justify a new mandatory gate by themselves.

Keep the baseline. No paid run, prompt change, automatic replay policy, test300
execution or generalization claim follows. The next design question is how a
concrete unresolved public requirement becomes an executed current-patch check,
without treating the presence of notes or the count of passing tests as success.
