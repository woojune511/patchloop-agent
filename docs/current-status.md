# Current status

Updated: 2026-10-01. Replaceable authority for current decisions. Runtime source owns
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

The [next original benchmark task](../.agent/original-next-readiness.md) is
Conan #19735. Its approved image and original oracle are calibrated: baseline
F2P 0/1, P2P 21/21; reference 22/22 PASS. Package integration remains; no paid run
is authorized.

The [jsonschema follow-up](history/2026-10-01-jsonschema-hidden-evaluation.md)
is closed: saved-patch hidden evaluation passed, original FAIL preserved.
Live admission rejects missing hidden checks; coverage requires calibration.

The [Darts decision audit](history/2026-10-01-darts-decision-scope-closeout.md)
closes this investigation. Both runs expected inverse preservation; neither
records a considered/rejected zero-width input. B recognized the regression gap
but submitted after ordinary drop-mode checks. This establishes incomplete
verification, not its internal cause or an effective general intervention.
Keep the baseline; no further Darts diagnostic, prompt change or paid run is queued.

The [zero-width diagnosis](history/2026-10-01-zero-width-ownership-diagnosis.md)
locates Darts' task-level defect in inverse column reconstruction, with sufficient
metadata retained elsewhere. The [priority review](history/2026-10-01-failure-priority-review.md)
and [patch review](history/2026-09-30-submitted-patch-review.md) preserve the evidence
and separate verification gaps from environment/resource failures.

The [guidance comparison](history/2026-10-01-verification-selection-comparison.md)
closed at USD 1.125171 of USD 6. Both Darts patches retained the same frozen gaps;
B's probes corrected a test expectation, not a candidate defect. Correctness was
INCONCLUSIVE. The [baseline decision](history/2026-10-01-verification-guidance-baseline.md)
restored previous guidance: no adoption evidence, not general ineffectiveness.
Preserve original records; the [comparison note](../.agent/verification-selection-comparison.md)
is closed and grants no further execution.

The [PDM repair observation](history/2026-10-01-pdm-repair-observation.md) completed
one approved run on the exposed dev-train v2 task. One edit passed all 24 public
bug cases, all 36 upstream regressions, isolated acceptance and real sandbox
safety. Recorded usage was USD 0.3550415; the USD 3 allocation is closed.
The agent used registered checks and no optional probes. Because the public bug
contract failed unchanged source, this run did verify repaired behavior; zero
probes alone is not a verification failure. Keep the restored baseline and choose
further work from a concrete failure, rather than automatically running another
task. No prompt effect, unseen-task success rate or complete coverage is established.

The [four-row probe comparison](history/2026-09-30-probe-replay-comparison.md)
closed at USD 1.412167 of USD 12. All Darts/MontePy rows passed acceptance, safety
and public checks, but none used probes: mechanism NOT_EXERCISED, improvement
INCONCLUSIVE. This exposed panel supports no adoption or general success rate.
Its [comparison note](../.agent/probe-replay-comparison.md) is closed.

Optional [program replay](history/2026-09-30-probe-program-replay.md), its control
and panel ledger remain implemented. Earlier Darts/MontePy observations and
operator corrections are separate from this panel's fresh control rows; see the
comparison record. Mock safety NOT_RUN remains separate from live safety PASS.

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

CI runs the complete suite with four file-grouped workers on PRs and main pushes,
with duration/JUnit reports. The [completed investigation](history/2026-09-30-ci-feedback-speed.md)
and [merged PR #2](https://github.com/woojune511/patchloop-agent/pull/2) retain the
individual timing evidence; those timings are not a stable performance benchmark.

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
