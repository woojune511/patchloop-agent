# Review pilot collector and scoring readiness

Date: 2026-10-01. Implementation follow-up to the
[integrated rehearsal](2026-10-01-review-integrated-execution.md).
No provider calls or credential-content reads; no new repair-quality evidence.

## Problem and decision

The review-context hypothesis already has a frozen four-task, three-arm design,
but the earlier preparation could not safely execute its allocation or score final
submissions. Complete that execution seam before requesting paid approval. This
change preserves the baseline and the experiment design; it does not infer a
context benefit from scripted behavior.

## Change and boundaries

The collector requires the exact manifest SHA and cap, reconstructs all bound
controls, requires clean tracked implementation and readmits all four environments
before creating a client. It binds all diagnostic helpers, runtime, source and
evaluation packages, public scoring programs, model settings and configured prices.
Each of twelve rows shares USD 2 across review and repair, giving an invocation
maximum of USD 24. A fresh external root prevents restart; count, transport,
billing, cleanup or scoring failure stops remaining rows. Known settlements survive
later scoring failure. Clients close once, without a cleanup retry.

The real entry uses the existing zero-retry provider adapter and native repair
loop. Finite rehearsals remain restricted to scripted clients. Reviewer and repair
usage retain separate provenance within the shared row allowance. Private scoring
never returns to either model context.

Post-submission scoring rechecks the submitted patch, uses frozen public matrices
for OpenSandbox/isort, and separately evaluates pyinfra v2 while retaining original
v1 verdicts. Its operator-only deadline is 300 seconds per row, with no model calls.
Conan retains its original isolated verdict. No submission yields NOT_RUN.
The collector does not automatically classify a causal improvement.

## Executed evidence

All roots below are external, append-only evidence; earlier failures were retained.

- `C:/pt/analyses/review-collector-rehearsal-20261001-v1`: all twelve rows traversed
  actual preflight, reviewer/repair routing and scorer entry with an injected finite
  SDK transport. Every row intentionally stopped without submission; scoring was
  NOT_RUN. Actual provider calls were zero. The 11,000,000 cost nanos are simulated.
- `C:/pt/analyses/review-final-scoring-20261001-v2`: saved submitted candidates
  scored 5/8 frozen OpenSandbox observations and 4/8 isort observations. These are
  behavior checks on existing patches, not task-level success rates. Pyinfra v2
  actually passed but an uppercase-versus-enum-value comparison rejected completion.
- `C:/pt/analyses/review-final-scoring-20261001-v3`: after fixing that comparison,
  pyinfra v2 passed hidden/regression/scope/safety and retained source v1 acceptance
  FAIL. Conan scoring completed. Unchanged public matrices were not rerun.
- The first scoring driver (`review-final-scoring-20261001-v1`) selected the parent
  workspace directory rather than its `repo` child and stopped before scoring.
  The driver path was corrected; original evidence was not edited.

Focused tests cover fixed order, cap/approval rejection, failed preflight,
uncertain dispatch, overruns, scoring failure, close-once behavior, no restart,
unsubmitted scoring and typed verdict values, alongside existing projection,
restoration and shared-budget tests. Final validation and manifest admission are
recorded below when completed.

## Unresolved and next decision

Real provider acceptance, review quality, repair improvement, latency and actual
cost remain untested. Approve only the exact new manifest and scope in the
[protocol](../../.agent/review-context-pilot.md), then perform one bounded pilot.
Do not reuse closed allocations, tune scoring after outcomes, or infer general
performance from exposed outcome-selected cases. No paid execution is queued.
