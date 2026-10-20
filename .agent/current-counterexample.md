# Current-candidate counterexample delivery comparison

Question: can the same model revise and repair the saved SQLFluff-1733 candidate
after observing that the original public example still fails on that candidate?
The [previous replay pair](../docs/history/2026-10-07-probe-action-results.md)
never exercised replay. This comparison separates receiving the execution result
from choosing to obtain it. It is a seeded repair diagnostic, not a fresh solve.

## Frozen design

- Source candidate: B2 at prepared boundary 526 in `C:/pt/sretcl01/2`, run
  `run_dev_984d4340fa4e43d3`; patch
  `sha256:339ced45df8758edfb39c66f63731a9b70537642ab8e7ef219e4efb1ee00cce8`.
- Task: `tasks/dev-train/current-dev20/18/public.yaml`, dev-train SQLFluff-1733.
- Program: the exact earlier public agent action
  `call_YcnJuf5oV8ffOwrmGNBweCbB`, source
  `sha256:f7cab304a8f2f5b5b3f7af30d76845dd5e5d5ff79859ce0ebf6552ca7643c9a7`.
  A new provider-free execution must bind that program to this exact candidate.
  Instrumented operator programs and their root-cause findings are excluded.
- A receives the public requirement and original reproduction program; its
  execution observations are withheld. B receives the same fields plus the actual
  stdout/stderr, exit code and setup result. A must choose whether to execute it.
  A is therefore a supplied-program control, not unassisted case discovery.
- Both begin with the identical saved patch and fresh ordinary runner state.
  Neither inherits earlier plans, checks, model history or remaining counters.
  The external observation is labelled with its candidate hash; after edits it
  becomes historical and never grants required-check credit.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh, 25,000 desired output tokens;
  repository `.env`; segmented-v1, result-or-size-v1, brief-v1, 24k retained source,
  ordinary probes, repair-recheck, protected-v1 and per-call-v1 cost admission.
- Per arm: 40 model calls, 100 actions, four mutation slots (one consumed by the
  seed, leaving three new edits), 1,800 total seconds including 330 for evaluation.
  This restores the standard repair allowance equally; it does not assert that
  the old checkpoint's five calls were sufficient.
- Proposed paid scope: A then B, once each; USD 1.20 per arm, USD 2.40 total,
  no transfer of unused row allowance. The old allocation remains closed.
  Preparation has zero provider/count calls and is not paid authorization.

## Outcomes and limits

Track selection, recognition of current failure, hypothesis revision, edit,
same-program verification, registered regressions and isolated acceptance separately.
A submitted candidate is additionally checked once by the frozen public program
outside the solver, with no feedback or continuation. Do not count an unexecuted
assertion as PASS: this program prints both outputs before its first assertion,
and a failing WITH assertion prevents execution of the plain-SELECT assertion.

The positive result of interest is an actual new repair that passes the frozen
public reproduction, current required regressions and isolated acceptance. A probe
call, changed explanation or closed concern is not a repair success. B-only success
would motivate investigation of verification selection; a failed B trajectory must
be separated into ignored evidence, faulty diagnosis/repair and resource-limited
incompletion. One pair cannot establish effect size or model inability.

No policy adoption or larger task panel follows automatically. Another task scope,
model comparison or implementation change requires a result-based decision.

## Execution boundaries

`diagnostics/current_counterexample.py` reuses the ordinary seeded runner.
Its external preparation freezes calibration, task, candidate, first requests,
runtime/implementation, model, credential path and caps before live execution.
Live collection requires that exact manifest and cap. Count immediately before
dispatch, use zero SDK retries, and stop the group on count/transport/billing or
cleanup uncertainty, source drift, invalid calibration or infrastructure failure.
Known row cost exhaustion is recorded separately from wrong-answer evaluation.
Never start Docker Desktop or pull/build an image. Never import private evaluator
details, reference patches or operator repair hints into solver context.

Use fresh external roots and append-only hash-chained `dev-run-v1` journals. No
retry, resume, replacement row, automatic probe policy or historical rewrite.
All outcomes remain `official=false` and `claim_eligible=false`.
