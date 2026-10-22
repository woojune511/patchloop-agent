# Original-case verification at finish

Date: 2026-10-22. Local implementation and scripted protocol comparison only.
All runs are official=false and claim-ineligible. No paid allocation was opened.

## Problem, evidence and decision

The [caller](2026-10-19-caller-evidence-results.md),
[invocation](2026-10-22-probe-invocation-results.md) and
[helper-path](2026-10-22-helper-path-results.md) investigations repeatedly found
regression/helper success without verification of the reported caller. Delivering
more evidence or a separate judgment did not establish a repair improvement.
The consequence was an apparently complete submission with the original question
still unresolved. This justified changing completion control rather than adding
another reminder or cross-run memory.

Hypothesis: once the agent has acquired a public invocation-bound case, retaining
it independently of plans and checking it before finish prevents that particular
evidence substitution. Alternatives remain initial misinterpretation, a wrong
expectation, failure to acquire a case and inadequate model repair capability.
Rejecting more submissions alone cannot distinguish these or establish improvement.

The [pre-execution plan](../../.agent/plans/finish-reproduction.md) specified the
local controls and boundaries. Starting HEAD was
`188f7267d0793c65f9158452d0e8291f28ae36a6`; the comparison froze the uncommitted
implementation by individual source hashes before execution.

## Implemented change

- `completion_reproduction.py` projects all original-requirement bindings from
  the journal, independently of the three-case context display. Healthy baseline
  controls are retained too. New inputs, expectations or plans cannot replace them.
- The runner replays stale cases through the existing registered probe gateway
  before `finish_task`. Deterministic child action IDs preserve input-hash recovery,
  current-diff identity, action counts and the shared deadline. It needs no extra
  review model call. Completed or unavailable attempts are not repeated on that diff.
- The gateway rejects pending or current comparable refuted/conflicting evidence.
  Unknown, incomplete, unavailable or absent cases remain explicitly unverified;
  `submission_verification` is separate from the model's assessment.
- Refutation returns the policy and displayed readiness to repair. The resource
  forecast includes replay actions and a bounded repair after failed verification,
  including the existing first-mutation rejection allowance.

The host checks execution identity and comparison currency, not whether a case or
expected output correctly represents the user's requirement. Semantic mapping stays
`model_authored_unverified`; case support never becomes `repair_success`.
Initial case acquisition is still the agent's responsibility.

## Frozen local comparison

Driver: [finish_reproduction_experiment.py](../../diagnostics/finish_reproduction_experiment.py).
Public task: `tasks/smoke/csv-quoted-newline/public.yaml`. Fixed trusted decisions,
one execution per condition and arm. OFF disables only the completion projection
and automatic replay in the same current runtime; it is not a historical runtime
reconstruction. Both arms use the exact same candidate patch in each pair.

Real local subprocesses run the parser and visible checks. The trusted test probe
backend supplies simulated container metadata. No Docker, network, credentials,
model/provider call, private spec or private evaluator is used by this driver.
Limits were 10 seconds per subprocess and 180 seconds for the comparison.

| Fixed condition | OFF finish | ON finish | ON automatic probes |
| --- | --- | --- | ---: |
| Comment-only wrong patch; helper and regression PASS | Accepted | Rejected: refuted | 1 |
| Correct CSV streaming repair and normal-input control | Accepted | Cases verified | 2 |
| No original case; comment-only patch | Accepted | Unverified submission | 0 |
| Incomplete current observation; normal cases PASS | Accepted | Unverified submission | 1 |

All 8 protocol controls matched their prespecified outcomes in 47.332 seconds;
provider/model calls 0, cost USD 0. This counts expected protocol behavior, not
eight successful repairs. Every repeated identical finish returned its prior
receipt, with zero additional probe execution. Independent acceptance is NOT_RUN
for all eight rows. In particular, the two unverified paths can submit wrong patches.

Evidence root: `C:/pt/finish-reproduction22-local/final/`.
`protocol.json` and `result.json` are content-addressed in the external append-only,
hash-chained `dev-run-v1` journal `runs/run_dev_finishreproductioncontrols.jsonl`.
Each row also preserves its action journal, source program, exact candidate diff,
observations and receipts. Protocol hash:
`sha256:e4473cd4b0ff7e5fa2242bb9c43f640643aae13ab145df7d54ca00a49251494e`.
Driver development errors remain in separate `development-tests-*` directories;
the valid frozen comparison was not rerun.

After this comparison, a focused budget test exposed a missing two-action/model
reservation for the first rejected mutation following an automatic replay failure.
`completion_budget.py` restored that allowance, and the runner's cost forecast
reserved the advertised recovery funds before a finish that could be rejected.
Crash tests also found that a durable child completion marker could hide its
cleanup/deadline abort on recovery. The runner now rechecks current-candidate child
receipts without re-executing them; both injected failures remain terminal.
These two runtime files changed after the frozen comparison. The result is preserved;
it is not represented as an execution of those later forecast bytes. The comparison
exercises fixed gateway submissions, not provider admission or those recovery branches.
The frozen inventory's `tests/test_dev_probe_cases.py` also changed afterward:
only its current prompt/tool hash expectations changed; the trusted probe backend
used by the comparison did not. Historical comparison guards remain unchanged.

## Local validation and remaining question

Focused tests cover exact-case retention, helper substitution, changed setup,
incomplete execution, conflicts, display overflow, current-diff invalidation,
action limits and crash recovery at child admission, child completion and finish.
Budget tests cover both a successful finish and bounded recovery after rejection.
The correct repair/control integration test reaches isolated mock evaluation.

Final-source CLI mock smoke: `run_dev_3a9f50d9c67b47e0` at
`C:/pt/finish22-cli-smoke-final`,
EVALUATOR_PASS, task acceptance PASS, safety NOT_RUN, USD 0. This is separate from
the eight-row comparison and from any live model performance measurement.

- Focused projection/finish/budget/driver suite: 42 PASS in 79.50 seconds.
- After the final child-abort recovery fix, finish/recovery suite: 12 PASS in
  73.65 seconds. Both focused runs were under two minutes.
- Completion resource/cost suite: 48 PASS in 56.70 seconds.
- Quick selection: 270 PASS in 220.16 seconds, before the final child-abort fix.
- Final Ruff and `git diff --check` passed.
- Full regression coverage: 5,626 PASS and 20 SKIP across all 5,646 collected
  tests, with no unresolved failure or unexecuted test. This combines three
  executions on unchanged runtime/diagnostic source, not one passing full run.
  Phase 1 stopped after 4,475 PASS, 7 SKIP and 15 failures in old test doubles or
  prompt expectations. Phase 2 ran every incomplete/changed file: 1,199 PASS,
  13 SKIP and three more stale-test failures. Updating those two test files and
  rerunning both gave 10 PASS in 4.27 seconds. Historical expectation branches
  stayed frozen; no runtime change was needed during these three phases.

`C:/pt/finish-reproduction22-local/full-coverage.json` maps every current test to
its latest result on matching test-file bytes. All three XML reports, the complete
collection and per-phase source inventories are retained alongside it. The final
validation record uses a separate external `validation/` journal; the frozen
comparison journal was not extended or rewritten.

These overlapping test counts are assertion coverage, not independent repairs.
An earlier focused recovery check correctly rejected runtime drift while source
was still being edited; the stable rerun above passed. Closed diagnostic tests now
use their frozen public inputs, while current guidance hashes were updated. The
diagnostic drift guards and historical experiment artifacts were not relaxed.

Decision: keep the implemented completion mechanism for development. The fixed
negative control supports preventing observed same-case failure from being closed
by unrelated PASS. It does not establish autonomous reproduction, better repairs,
false-rejection rate, Docker behavior or performance on other tasks. A live
comparison needs an exact new task/model/credential/repetition/cap authorization
and a separate question about acquisition and recovery; prior allocations remain
closed. More reminders or a larger panel are not justified by this local result alone.
