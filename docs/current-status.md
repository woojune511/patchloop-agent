# Current status

Updated: 2026-10-15. Current decisions; runtime source owns behavior.
Historical reports are evidence, not an active queue.

## Product and working baseline

Build a single coding agent that repairs public software tasks, verifies its changes
and submits within bounded resources. Recovery, sandboxing and isolated evaluation
support that product. Start improvements from observed failures, not a commitment
to memory, planning or another preselected technique.

- dev-head is the sole mutable runtime; every run is official=false and claim-ineligible.
- General baseline model: gpt-5.4-2026-03-05, xhigh, 25,000 output tokens.
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

[Uptake review](history/2026-10-15-uptake-grade.md): B1 U/P/I FAIL; B2 D/U/P/I PASS.
Complete chain and repair success: 1/2. Baseline kept; no follow-up queued.
USD 1.21861750; eight generations/eight counts; regrading made no calls.

[Revision comparison](../.agent/revision-comparison.md): preparing four exposed tasks,
two revisions and two repetitions with two workers. Proposed USD 19.20 cap awaits
exact manifest approval. No live result or quality gain is established.

[Navigation](history/2026-10-08-failure-navigation.md) found no current tool defect;
keep baseline. [Rule ownership](history/2026-10-08-rule-ownership.md) is an operator
control. [Thin disclosure](history/2026-10-07-thin-followup.md) remains live-untested.

The [corrected dev20 measurement](history/2026-10-06-corrected-dev20-results.md) closed:
11 PASS/7 FAIL/2 NOT_RUN; USD 5.08206870. A deadline with unconfirmed cleanup stopped
admission. Matching 18 tasks moved from 8 to 11 successes; no all-20 accuracy claim.

[Search fix and supplement](history/2026-10-06-search-once-supplement.md): rows 18/20
submitted and failed; searches took under 0.74s. Original NOT_RUN stays unchanged.
[Trace comparison](history/2026-10-06-agent-trace-comparison.md) and
[verification follow-up](history/2026-10-06-verification-closure-results.md) closed:
A 1/4 versus B 0/4; saved-case mechanism NOT_EXERCISED.
[Diagnosis](history/2026-10-06-verification-context-budget-diagnosis.md) found
untested submission, recency source loss and recheck reservation;
[accounting review](history/2026-10-06-resource-budget-context-review.md) fixed the
model/tool mismatch. [48k](history/2026-10-06-source-retention-results.md) tied at 2/4;
both [continuations](history/2026-10-06-cost-cap-continuation-results.md) failed.
[Public diagnosis](history/2026-10-07-public-verification-failure-diagnosis.md) found
an L003/L039 cycle and regression PASS mistaken for bug verification despite retained
notes and available probes. Keep 24k; no paid run queued.

[Counterexample A/B](history/2026-10-07-counterexample-results.md) closed: both FAIL,
unchanged after regression PASS; B retained the actual current failure in both inputs.
USD 0.04019910. No adoption or paid follow-up; preserve baseline.

See [panel contract](../.agent/current-dev20.md) and
[priority fixes](history/2026-10-06-agent-priority-fixes.md). Prior panels closed.

Portfolio v1 [remeasurement](history/2026-10-06-portfolio-dev20-results.md) closed at
9/20 versus historical 10/20, all evaluations agreeing; USD 3.46111455, 102m19s.
The 11/20 threshold failed; test300 remains unprepared and unauthorized. The
[decline review](history/2026-10-06-dev20-decline-review.md) adopted no intervention.
[Public results](../examples/portfolio-dev20/README.md) and saved demos remain local;
remote publication/release and Linux CI are NOT_RUN. [Preparation](history/2026-10-05-portfolio-preparation.md)
preserves validation and the closed immutable evidence roots.

[Mini/full](history/2026-10-04-mini-full-results.md): mini selected for the six-task
panel only; 24/24 completed at USD 5.42285815. CLI defaults unchanged.
[Direction review](history/2026-10-01-development-direction-review.md): task-by-task
diagnosis closed; no isort repair control or agent change queued.
[Selection review](history/2026-10-02-requirement-selection-decision.md): task-first
design exists; baseline kept, no duplicate planning/prompt change.

[Fixed batch](history/2026-10-01-fixed-batch-live-results.md): 0/3 accepted;
public/scope/safety passed, original hidden verdicts FAIL. USD 4.0651735; allocation
closed. Keep baseline.
[OpenSandbox](history/2026-10-01-opensandbox-public-diagnosis.md): backend gap confirmed.
[Pyinfra v2](history/2026-10-01-pyinfra-v2-behavior-evaluation.md): calibrated replay
PASS; original FAIL retained. No agent change or paid run queued.
[Isort](history/2026-10-01-isort-public-diagnosis.md): comment-text workaround loses
ownership; task-level repair remains unimplemented.

[Pydantic audit](history/2026-10-01-pydantic-evaluator-contract-audit.md) closed;
no contract change.

[HF v6 calibration](history/2026-10-01-hf-v6-behavior-evaluation.md) accepts HB2
and rejects baseline/four wrong controls. Historical v5 FAIL preserved; no run queued.

[Conan](history/2026-10-01-conan-live-result.md) and
[probe replay](history/2026-10-01-conan-final-probe-replay.md) passed.
Allocation closed; no causal probe-benefit claim.

[Jsonschema](history/2026-10-01-jsonschema-hidden-evaluation.md) follow-up passed;
original FAIL preserved. Hidden-check admission and coverage calibration are separate.

The [Darts audit](history/2026-10-01-darts-decision-scope-closeout.md) is closed:
boundary verification was incomplete; cause and intervention remain unresolved.
No run is queued.

The [zero-width diagnosis](history/2026-10-01-zero-width-ownership-diagnosis.md)
locates Darts' defect in inverse column reconstruction. The
[priority review](history/2026-10-01-failure-priority-review.md) separates
verification gaps from environment/resource failures.

The [guidance comparison](history/2026-10-01-verification-selection-comparison.md)
closed at USD 1.125171 of USD 6. Both Darts patches retained the same frozen gaps;
B's probes corrected a test expectation, not a candidate defect. Correctness was
INCONCLUSIVE. The [baseline decision](history/2026-10-01-verification-guidance-baseline.md)
restored previous guidance: no adoption evidence, not general ineffectiveness.
Preserve original records; the [comparison note](../.agent/verification-selection-comparison.md)
is closed and grants no further execution.

The [PDM observation](history/2026-10-01-pdm-repair-observation.md) passed 24 public
bug cases, 36 regressions, acceptance and safety in one edit. USD 0.3550415;
allocation closed. No causal prompt/probe benefit or general accuracy claim.

The [four-row probe comparison](history/2026-09-30-probe-replay-comparison.md)
closed at USD 1.412167 of USD 12. All Darts/MontePy rows passed acceptance, safety
and public checks, but none used probes: mechanism NOT_EXERCISED, improvement
INCONCLUSIVE. This exposed panel supports no adoption or general success rate.
Its [comparison note](../.agent/probe-replay-comparison.md) is closed.

Optional [program replay](history/2026-09-30-probe-program-replay.md), its control
and panel ledger remain implemented. Earlier Darts/MontePy observations and
operator corrections are separate from this panel's fresh control rows; see the
comparison record. Mock safety NOT_RUN remains separate from live safety PASS.

[Mock profiling](history/2026-09-30-journal-read-profile.md) did not justify a journal
cache. [Projection tests](../tests/test_model_view_fields.py) cover the compact public
view; [completion arithmetic](../patchloop/dev/completion_budget.py) preserves resume
identity. These local results do not establish live performance.

The [development review](history/2026-09-30-development-review.md) closes repeated
ablations: no quality experiment, memory extension or mandatory probe gate queued.

[Journal](../tests/test_dev_state.py) and [admission](../tests/test_visible_check_ids.py)
tests cover record integrity and unique check IDs. [Paths](../tests/test_repository_paths.py),
[repair verification](../tests/test_repair_verification.py) and
[line feedback](../tests/test_execution_feedback_paths.py) preserve unusual filenames.
[Panel costs](../tests/test_dev_probe_panel.py) count compaction once;
[evaluation recovery](../tests/test_dev_evaluation_resume.py) verifies evidence files.
[Schema tests](../tests/test_replacement_schema.py) cover intent bounds and legacy fields.
[CI](../.github/workflows/ci.yml) uses locked dependencies on Windows/Linux.
[Impact review](history/2026-10-07-fix-impact.md): latest runtime fix triggers were absent
from 24 reviewed runs. No patch-quality gain established or paid rerun queued.

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

Paid allocations, including the Lite pilot, are closed. No further run is authorized.
An [older interrupted call](history/2026-09-28-expectation-review-results.md)
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
