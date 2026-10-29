# Current agent measurement on the historical dev20 roster

Date: 2026-10-29. Preparation only; new live authorization is pending.
official=false, claim-ineligible. No provider calls or new repair outcomes.

## Question and decision

The user requested the same historical 20 tasks to measure current performance,
rather than another five-task diagnostic selection. That is the appropriate
denominator for a current whole-panel score. The latest
[five-task result](2026-10-29-repair-five-results.md) remains a separate 4 PASS /
1 FAIL diagnostic panel; those outcomes will not be pooled into the new score.

Use all current-dev20 indices 1 through 20 in order, one fresh solve each, with
the current complete configuration frozen. Public issue text, task IDs, original
repository commits and evaluation images match the historical panel. The old
execution worktree is gone; its public task bytes are recovered read-only from
recorded Git commit 22d8217fba31b2d85dec086e6f634d8d02c94774. Current package
hashes can differ because runtime contracts/evaluation adapters have changed.

The question is current configuration performance and per-task changes, not the
causal effect of an individual feature. The latest
[whole-roster PatchLoop result](2026-10-16-patchloop-mini-dev20-results.md) is
8 PASS, 10 FAIL and 2 NOT_RUN; the original
[mini-SWE-agent result](2026-10-16-mini-swe-dev20-results.md) is 10 PASS,
5 FAIL and 5 NOT_RUN. Model, resource, prompt, tool and environment differences
preclude attributing a new score difference solely to architecture. Separately
extended historical rows remain separate. The panel is development-exposed;
one run per task establishes neither repeatability nor held-out generalization.

## Frozen proposed scope

- All 20 exact `tasks/dev-train/current-dev20/<index>` tasks, once each;
  original source with no old patch, checkpoint, observation or diagnosis.
- gpt-5.4-2026-03-05, xhigh; primary repository `.env` credential path.
- USD4.50/task, USD90 invocation cap; sequential execution, no cap transfer.
- Same settings as the recent five-task panel: 20 responses including at most
  one correction, 40 actions, 3 edits; input60K, output40K/correction25K;
  2,400 active seconds/task including 390 reserved for isolated evaluation.
- public-checks-v1, thin, segmented-v1, completion-recovery-v1,
  protected-v1, repair-recheck, ordinary probes without automatic replay.
- No solver rule change, evaluator image pull/build, SDK retry, resumed or
  replacement attempt, cross-run memory or private evaluation feedback.

Primary outcome: original SWE-bench acceptance through the registered isolated
oracle, using the original test patch and upstream grading. Report PASS/20 plus
all FAIL, ERROR and NOT_RUN rows. Public checks, submission, safety, original
observations, cost and elapsed time stay separate. Missing diagnostics do not
erase acceptance PASS. An operationally interrupted row is not relabelled a
completed test failure. No duplicate native grading is planned.

Count before dispatch and stop the remaining batch on count, transport, billing,
execution/cleanup uncertainty or frozen-input drift. Known task-local failure or
settled resource exhaustion permits the next independently capped row. Freeze
the runtime between tasks; inspect failure causes only after the panel closes.
No new default or automatic next experiment follows from unused budget.

## Preparation and evidence

External plan: [design](C:/pt/repair-dev20-plan-v2/plan.md),
[task selection](C:/pt/repair-dev20-plan-v2/selection.json),
[historical comparison](C:/pt/repair-dev20-plan-v2/historical-comparison.json),
[manifest](C:/pt/repair-dev20-plan-v2/manifest.json),
[validation](C:/pt/repair-dev20-plan-v2/local-validation.json).
Planned fresh state: `C:/pt/repair-dev20-run-v2`.

The initial v1 preparation stopped on an absent historical worktree path, before
any provider/count call, credential read or target execution. Partial artifacts
are preserved; v2 uses immutable Git objects and fresh output paths. This is a
preparation correction, not a retry of an experimental model attempt.

Local preparation verifies all source/image/dependency identities, public
ordinary operations, selected test canaries, and actual first-request
construction with provider/network/target execution forbidden. The external
batch stop/accounting and outcome collector are tested separately. Runtime
validation is reused only while its hash remains unchanged; documentation and
explicit top-level scripts are checked anew. Local preparation is not task
acceptance or model performance evidence.

Exact command after new approval:
`& 'C:/pt/repair-dev20-plan-v2/run.ps1'`.
The sealed manifest and matching approval receipt bind the scope. All previous
allocations are closed; none authorizes this new USD90 panel.
