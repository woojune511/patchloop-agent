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

PR #9 Linux CI exposed an unlocked journal read racing with a parallel append.
Readers now share the append locks; a controlled partial-write test verifies that
readers wait for completion and still reject a torn tail after a failed write.
The focused journal/parallel-note tests and Ruff pass locally; full-suite and hosted
validation are pending. This changes persistence synchronization, not solving policy.

The [fresh Darts repair](history/2026-09-30-darts-fresh-repair.md) remains acceptance
FAIL despite public regression PASS; its USD 0.607473 allocation is closed.
The [offline correction](history/2026-09-30-darts-feature-ownership.md) replaces
name-prefix ownership with fitted feature widths and restores the original column
schema during inverse transformation. It passes 13 selected public cases and all
8 registered regressions. This is an operator patch, not a successful agent rerun;
private acceptance is NOT_RUN. Preserve the runtime/task/prompt baseline and both
failure and correction evidence. No new paid invocation or automatic adoption.

The [fresh MontePy v2 repair](history/2026-09-30-montepy-v2-fresh-repair.md) completed:
one edit, 44 public tests passed, isolated acceptance/safety PASS, 12 model calls,
251.479 seconds and USD 0.594456. Its allocation is closed; no additional live
invocation is authorized. Keep the baseline: this exposed development task supplies
one successful execution, not a general quality gain or a new runtime-fix rationale.
No optional probe ran and public changed-line coverage was unavailable; those
limits remain separate from the successful private verdict.

Keep journal validation and state construction unchanged. The bounded
[mock journal-read profile](history/2026-09-30-journal-read-profile.md) did not meet
its frozen cost threshold for reusing repeated reads. No cache or RunState is queued.
The result covers a short smoke task and mutation-receipt recovery; large-journal
and live-run performance remain unmeasured.

The compact model view selects explicit top-level runtime/public diagnostic fields,
preserving existing values/order and nested rules. The
[projection tests](../tests/test_model_view_fields.py) cover this input boundary.

Completion and mutation-attempt call-budget arithmetic lives in
[completion_budget.py](../patchloop/dev/completion_budget.py). The runner constructs
the state snapshot and admits tools; monetary admission stays in `dev/cost.py`.
Runtime identity changes normally and prior-run resume restrictions remain intact.

The [cross-task development review](history/2026-09-30-development-review.md) closes
the repeated prompt/context/prior-decision ablation series without establishing an
effective default quality fix. Keep the solving baseline; no new quality experiment,
memory extension or mandatory probe gate is queued.

The subsequent contract review identified two reproducible engineering defects:
undisclosed mutation-explanation length limits and successful append returns after
incomplete journal writes. The public schema now derives mutation field constraints
from the internal intent models, preserving public descriptions, required/null rules
and recovery-only serialization. [Boundary tests](../tests/test_replacement_schema.py)
cover length, occurrence, missing/null and legacy-field behavior. Journal append
completes short writes and propagates zero-progress/I/O failures.
Invalid journal tails remain preserved and block recovery. The [contract tests](../tests/test_dev_contracts.py)
and [journal tests](../tests/test_dev_state.py) cover the boundaries and injected failures.
[CI](../.github/workflows/ci.yml) is configured for locked dependencies and both Windows
and Linux. These changes do not establish improved patch correctness.

The [CI feedback investigation](history/2026-09-30-ci-feedback-speed.md) found Git
subprocess waiting dominated a sampled slow test. CI now runs the complete suite
with four file-grouped workers, on PRs and main pushes, with duration/JUnit reports.
Both hosted jobs passed 3,688 tests with 25 skips on the unchanged 3,713-case inventory.
In one before/after PR comparison, Linux took 519.48 -> 280.06 seconds and Windows
2,564.75 -> 1,340.70 seconds. [PR #2](https://github.com/woojune511/patchloop-agent/pull/2)
was merged at `bb265c83`; its completed receipts supersede the local investigation's
pending-hosted status. These timings are individual runs, not a stable benchmark.
No runtime logic, test assertions or test selection changed.

The approved [fresh tox repair](history/2026-09-30-tox-fresh-repair.md) completed with
the working baseline unchanged: one edit, 29 public regression tests passed,
isolated acceptance PASS and safety PASS. Five model calls cost USD 0.2702935 by
recorded usage; elapsed process time was 113.233 seconds. The one-run USD 3.00
allocation is closed. This exposed development-task success establishes one completed
repair path, not a quality gain, feature effect or held-out generalization. No new
runtime defect or follow-up experiment was established; retain the working baseline.

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
