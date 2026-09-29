# Observation comparison: recount and receipt-lineage correction

Started 2026-09-29; validation completed 2026-09-30. Follow-up to the immutable
[comparison results](2026-09-29-observation-comparison-results.md).
This correction uses synthetic clients and local fixtures; it does not reopen the
closed invocation, change its recorded results, or establish agent improvement.

## Problem and mechanism

P1B legitimately counted an oversized input, replaced its segment, and counted the
smaller request. The collector incorrectly required cumulative counts to equal
dispatches plus one, rejecting that replacement before SDK transmission. The count
needed for admission is the latest successful unconsumed count, not the total.

N1A/B copied parent probe outcomes for agent history. Submission packaged those old
profile receipts as though they had executed under the new envelope, so the evaluator
correctly rejected them. Historical execution and current sandbox evidence need
separate provenance; relaxing the evaluator would hide the mismatch.

## Change

- In the comparison collector, a successful count supplies one dispatch binding.
  Replacement counts supersede it; failed counts invalidate it. Payload drift,
  ceiling growth and reuse remain rejected. Uncertain sends still stop the group.
- The fork marker binds parent receipt artifacts to the source and prefix hash.
  Submission packages all new executed probes and appends a lineage event linking
  historical and current receipts. Ordinary resume still packages the whole run.
  Evaluator checks, public/private isolation and submission gates are unchanged.

## Verification

Focused validation: 30 passed in 67.23 seconds. The scripted collector exercises a
real size-triggered recount, single-use count bindings, failed recount invalidation,
payload/ceiling rejection and unchanged whole-group stops on uncertainty. A fixture
with an old parent profile and a new probe reaches isolated local evaluation PASS;
changing the new receipt's profile still fails evaluator integrity. Fork-marker
drift is rejected and ordinary receipt packaging remains intact. Ruff passed.

Saved-source replay also passed without model calls: the actual P1B sequence now
reaches a fifth inert send after six counts; a fresh fork of N1 retains both old
profile receipts and packages zero current executions before any new actions.
Original source journals remain byte-identical. This packaging audit does not
reevaluate N1 acceptance. Scripts, hashes and results are saved under
`C:/pt/analyses/observation-boundary-fixes-20260929-v1`.

Mock smoke reached `EVALUATOR_PASS`, task acceptance PASS, safety NOT_RUN, under
`C:/pt/observation-boundary-fixes-smoke-20260929-v1`, run
`run_dev_e204d5e903c24096`. Synthetic receipt checks are not Docker safety evidence.
Actual provider calls: 0. Actual new provider cost: USD 0.

The full default suite passed: 3,650 passed, 16 skipped across all 194 test files,
in eight file-disjoint processes with separate external temporary roots. All eight
exit codes were zero; the longest shard took 2,505.28 seconds (41m45s). This broad
suite is substantially slower than the focused 67-second check. Per-shard logs and
exit codes are in the evidence directory above. Real-Docker opt-in tests were not
enabled. No old reports, experiments, journals or closed history records were edited.

## Remaining question

Does observation retention improve supported interpretation and discriminating
action? The incomplete comparison does not answer that question. A future live
comparison needs a newly prepared manifest and exact authorization; the prior
allocation and prior outcomes remain closed. These changes repair diagnostic
plumbing, not the agent's task-solving behavior.
