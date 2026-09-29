# Current status

Updated: 2026-09-30. Replaceable authority for current decisions. Runtime source owns
behavior; historical reports are evidence, not an active work queue.

## Product and working baseline

Build a single coding agent that repairs public software tasks, verifies its changes
and submits within bounded resources. Recovery, sandboxing and isolated evaluation
support that product. Start improvements from observed failures, not a commitment
to memory, planning or another preselected technique.

- dev-head is the sole mutable runtime; every run is official=false and claim-ineligible.
- Selected working model: gpt-5.4-2026-03-05, xhigh, 25,000 output tokens.
- Selected policies: segmented-v1, result-or-size-v1, brief-v1, probes enabled with
  policy none, repair-recheck, protected-v1 inspection, per-call-v1 cost admission.
- Working limits: 40 model calls, 100 actions, four accepted edits, 1,800 seconds.
  Paid work additionally requires its exact task/model/credential/repeat scope and cap.
- Cross-run memory, held-out tuning and claim execution are disabled. Bounded
  run-local notes remain available. Historical Rapid executables are absent.
- These settings are the selected baseline, not a statement of CLI defaults.

See [implementation guide](../.agent/guide.md), [operations](operations.md),
[product](product.md) and [evidence boundaries](evidence.md) as needed.

## Active decision

The [cross-task development review](history/2026-09-30-development-review.md) closes
the repeated prompt/context/prior-decision ablation series without establishing an
effective default quality fix. Keep the solving baseline; no new quality experiment,
memory extension or mandatory probe gate is queued.

The subsequent contract review identified two reproducible engineering defects:
undisclosed mutation-explanation length limits and successful append returns after
incomplete journal writes. The public schema now exposes the existing 1,500-character
limits; journal append completes short writes and propagates zero-progress/I/O failures.
Invalid journal tails remain preserved and block recovery. The [contract tests](../tests/test_dev_contracts.py)
and [journal tests](../tests/test_dev_state.py) cover the boundaries and injected failures.
[CI](../.github/workflows/ci.yml) is configured for locked dependencies and both Windows
and Linux. These changes do not establish improved patch correctness.

The [CI feedback investigation](history/2026-09-30-ci-feedback-speed.md) found Git
subprocess waiting dominated a sampled slow test. CI now runs the complete suite
with four file-grouped workers, on PRs and main pushes, with duration/JUnit reports.
The unchanged four-test local comparison passed in 138 seconds serially versus 62
seconds with four workers; hosted full-suite verification remains pending. No runtime
logic, test assertions or test selection changed.

The clearest repeated weakness is selecting verification that exposes an incorrect
repair condition. The 24-run six-task panel had nine acceptance failures despite all
final public checks passing; public replay confirms omitted distinctions on Pydantic
and HF. This does not establish one general harness fix or explain every failure.

Conversely, 11 registered failure events across three tasks reached later same-check
PASS; tox and one HF seeded episode repaired their identified public mismatch. Only
one reviewed seeded HF episode meets the strict unresolved-delivered-counterexample
criterion. Do not generalize that episode into universal evidence loss or incapacity.

Known environment/recount/receipt-lineage problems were separately reproduced and
corrected. Historical probe failures include invalid setup, API use and expectations;
they are not all current environment defects or product bugs. Resources censored the
original toqito attempt but not the completed panel. Full distinctions and exclusions
are in the review, including 95 source-journal hash/chain rechecks.

Further development should address a concrete current-contract defect or an implementation
with a specific predicted repair benefit. Use focused fixes/tests for reproducible
bugs. For quality interventions, executed patch correctness, regressions and cost/time
are decision evidence; explanation scores and tool/plan counts are auxiliary. Do not
start another adjacent diagnostic merely because the previous one is complete.

## Evidence map

- [Development review and task dispositions](history/2026-09-30-development-review.md):
  consolidated coverage of twelve task identities; no new twelve-task evaluation.
- [Fresh six-task panel](history/2026-09-29-boundary-pair-panel-results.md): 24 runs,
  A 7/12 versus B 8/12; no procedure adoption.
- [Basic/current comparison](history/2026-09-28-basic-current-baseline-comparison.md):
  12 fresh runs, 4/6 versus 5/6; bundled single-pair difference, not a general gain.
- [Original-input pilot](history/2026-09-28-original-pilot-results.md): MontePy/darts
  pass; toqito cost-limited before submission. Environment preparation passed for all.
- [Strict delivered-counterexample audit](history/2026-09-30-retained-counterexample-audit.md):
  distinguishes actual unresolved behavior, repaired cases, setup failures and post-run discoveries.
- [Last prior-decision comparison](history/2026-09-30-prior-decision-results.md):
  16 responses, no target-HF improvement, USD 0.738169 settled; allocation closed.
- [Recount/receipt-lineage fixes](history/2026-09-29-observation-boundary-fixes.md):
  locally tested engineering corrections; not agent-accuracy evidence.
- [Observation linking](history/2026-09-29-verification-observation-linking.md):
  implemented provenance retention; no semantic verdict or new submission gate.
- [History index](history/README.md): targeted lookup only. Closed reports and
  generated evidence remain immutable; changed interpretations get new follow-ups.

## Execution and claim boundaries

All previous paid allocations are closed. No live invocation is authorized by this
snapshot. An [older interrupted call](history/2026-09-28-expectation-review-results.md)
retains unknown billing separately from later settled allocations; closed allocation
does not mean that earlier uncertainty was resolved.

Fresh solves, seeded repairs, funded continuations, saved-patch evaluations, operator
replays and response-only judgments are different evidence. Do not pool them as solve
rates or feed private evaluator details to the agent. Public PASS certifies its checked
cases; submission eligibility is not semantic correctness. Mock safety is NOT_RUN.

Do not start Docker Desktop or pull/build evaluator images automatically. Preserve
exact recovery identities, zero SDK retries and stop-all on count/transport/billing
uncertainty. Runtime/default adoption and general improvement remain unestablished.

Replace this page's active decision when real work changes it. Keep completed
investigations in linked history, not in a growing sequence of suggested experiments.
