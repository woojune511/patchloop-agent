# Selected-test revalidation timing

Date: 2026-10-07. Source baseline: `ac485a4a`. Provider-free static investigation;
official=false. This follows the [thin diagnosis](2026-10-07-thin-followup.md).
The user authorized the proposed first step: locate possible selected-test reruns
in existing traces and determine whether repair capacity remained. No solver,
test, Docker, provider or evaluator execution was performed.

## Question and method

SQLFluff-1733 thin repeat 1 authored a useful full-behavior assertion, observed a
selected-file PASS, then made two source edits without repeating that selection.
The unchanged final candidate later failed the exact added node. This makes
revalidation timing a concrete question: could additional feedback have arrived
while a repair was still possible, or would it only identify an exhausted run?

The counterfactual rule is deliberately narrow: after a source edit, repeat the
latest previously executed healthy selected test with the same suite and targets,
after any existing required-check child and before the next inference. There is
no new selector registration, inferred probe, mandatory finish gate or policy
implementation. This is scheduling arithmetic, not an executed alternative trace.

Read three closed public journals, envelopes and bound public contexts. Validate
their hash chains and bind actual request artifacts without projecting their
contents. Use recorded next-turn budgets after the existing required recheck,
before that turn's provider dispatch; do not reuse the pre-edit budget. Preserve
the existing 330-second evaluation reserve and 1,470-second solver allocation.
The source journals and all 142 bound files remained unchanged.

## Coverage and timing

| Closed SQLFluff-1733 row | Selected-test executions | Candidate rerun points |
| --- | ---: | --- |
| 1, current repeat 1 | 0 | None |
| 8, thin repeat 1 | 1 | After source mutations 3 and 4 |
| 14, current repeat 2 | 0 | None |

The current-policy failures had no selected test to reuse. Their existing probes
do not become selected-test targets under this proposal. This mechanism therefore
does not address those two recorded trajectories as written.

Row 8's original selection was the whole existing file
`test/rules/std_L016_L36_combo.py`, suite `public-pytest`, not just the added node.
Its sequence-281 execution passed four tests on diff `945e1aaf...014e6`.
The complete action interval was 17.474 seconds; this includes more than pytest's
test-duration display and is only an observed duration, not a runtime prediction.

| Source mutation completed | Boundary after required recheck | Remaining edits | Remaining model calls | Remaining actions | Solver seconds | Remaining USD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 357: L003 change, edit 3 | 367 | 1 | 14 | 57 | 704 | 2.411310 |
| 373: L036 revert, edit 4 | 384 | 0 | 13 | 55 | 650 | 2.313419 |

These are recorded integer-budget snapshots before adding optional work. At the
first boundary `replace_text` and `run_tests` were offered, and the mutation
completion horizon was possible. At the second, `run_tests` remained available
but `replace_text` was absent because all four accepted edits were consumed.
One remaining edit is capacity for an attempt, not proof that a sufficient repair
fits one edit or that the agent would choose it.

An automatic child would consume one tool action and zero direct model calls.
Holding the original later actions fixed for arithmetic, two reruns would leave
56 and 53 actions at the respective boundaries; protected completion needed 6
and 1. Reusing the prior action duration leaves about 686.526 and 615.053 solver
seconds after cumulative extra work. Allowing each rerun its registered 300-second
timeout plus recorded 5-second cleanup reserve instead leaves 399 and 40 seconds.
The timeout allowance excludes other possible launch/setup overhead, so this is
not a guaranteed wall-time admission. The original operator diagnostic's separate
90-second limit is not the registered selection's 300-second limit.

The existing child would not itself incur a provider call. Its new output changes
the next request, so subsequent token counts, cost admission and model behavior
remain unknown. Neither recorded monetary headroom nor call counts certify a
counterfactual repair path. Later actions could change after the first feedback;
the cumulative figures do not predict that the original fourth edit would occur.

## Known result versus missing result

At mutation 357, diff `59679012...d2987` still contained the first L036 change as
well as the new L003 change. The selected file/node was not executed on that diff:
its result is **NOT_RUN**, not FAIL. The required check at sequence 362 failed a
different L036 fixture, already failing at sequence 294. It supplies no result
for the added task assertion. The older selected PASS was correctly labelled
historical in the next context; currency tracking was not defective.

At mutation 373, L036 was reverted and the final diff became `94b0aeeb...f25f3`.
The existing post-submission operator receipt proves the added node fails on that
diff, with five spaces where eight were expected. That receipt covers one node,
not a newly executed whole-file rerun, and was never delivered to the closed
solver. By this point no accepted edits remained.

Thus the first possible rerun had repair capacity but an unknown test outcome.
The only candidate with an observed task-test failure had no repair capacity.
The evidence establishes neither that mutation 357 already broke the assertion
nor that mutation 373 was the first mutation to break it.

## Decision and next question

Keep current and defer the optional automatic selected-test prototype. Available
execution headroom alone does not establish useful earlier failure feedback.
Moreover, the [counterexample comparison](2026-10-07-counterexample-results.md)
already showed that receiving an actual failure need not produce a repair.
No live comparison, larger cap or default-policy change follows from this result.

The smallest remaining discriminator is the same existing selected file on the
exact intermediate diff `59679012...d2987`, with assertion-level output. If its
task assertion fails, feedback could have arrived with one edit remaining, though
corrective behavior would still be untested. If it passes, this trace supports
late regression detection but not an earlier repair opportunity from this rule.
That execution and intermediate-workspace reconstruction were **NOT_RUN** here.

## Evidence and validation

- Analysis script and frozen plan: `C:/pt/strace01/analyze.py`, `plan.json`.
- Result: `C:/pt/strace01/result.json`, hash
  `sha256:eee7c16ddc575efbdd1e6d67b9bb6982a470456d5ac93bcfd2e7ab91ae4af55c`.
- Append-only record: `C:/pt/strace01/runs/run_dev_selectedtiming.jsonl`.
- Three original hash chains and 142 file bindings validated; timeline assertions
  confirmed selections 0/1/0, trigger counts 0/2/0, and remaining edits 1/0.
- Independent review recounted dispatches, actions and edits at both boundaries.
- Documentation layout/link checks passed 5/5 after trimming current-document
  byte limits; Ruff and whitespace checks passed. Both initial and final document
  test receipts remain in the external analysis root.
- Prior exact-node receipt: `C:/pt/thdiag02/selected-result.json`, bound in the plan.
- Runtime content remained
  `sha256:b3c8e80c0656fb4954eebcb5d30de411d4b0fa687a150ef3308883487bb08208`.

No runtime code changed. No new test outcome, agent repair, private acceptance or
quality improvement is claimed. Broad runtime tests and mock smoke are not needed
for this static analysis/documentation change; their previous results are not
relabelled as validation of a new implementation.
