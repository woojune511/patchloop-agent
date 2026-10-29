# Current status

Updated: 2026-10-29. Runtime source owns behavior. Historical reports are evidence,
not an active queue.

## Product and working baseline

Build a single coding agent that repairs public software tasks, verifies changes
and submits within bounded resources. Start improvements from observed failures.
Recovery, sandboxing and isolated evaluation support that product.

- dev-head is the sole mutable runtime; official=false and claim-ineligible.
- General baseline: gpt-5.4-2026-03-05, xhigh, 25,000 output tokens.
- Selected policies: segmented-v1, result-or-size-v1, brief-v1, probes enabled with
  policy none, repair-recheck, protected-v1 inspection, per-call-v1 cost admission.
- Limits: 40 model calls, 100 actions, four accepted edits, 1,800 seconds.
  Paid work also requires the exact task/model/credential/repeat scope and cap.
- Cross-run memory, held-out tuning and claim execution are disabled. Bounded
  run-local notes remain available. Historical Rapid executables are absent.
- These are selected settings, not CLI defaults or evidence of general accuracy.

See [guide](../.agent/guide.md), [operations](operations.md), [product](product.md)
and [evidence boundaries](evidence.md).

## Active decision

Measure the complete current configuration on the historical 20-task development
roster. The [dev20 plan](history/2026-10-29-repair-dev20-plan.md) prepares all
current-dev20 indices 1-20, once each from original source, with the recent
five-task settings frozen: gpt-5.4-2026-03-05/xhigh, public-checks-v1, thin,
segmented-v1, completion-recovery-v1, input60K, output40K/correction25K,
20 responses/40 actions/3 edits, and 2,400 seconds including 390 for evaluation.
Proposed caps are USD4.50/task and USD90 total with no transfer. No live work is
authorized yet. Earlier five-task outcomes will not be pooled into this score.

The latest [full-roster PatchLoop run](history/2026-10-16-patchloop-mini-dev20-results.md)
had 8 PASS, 10 FAIL and 2 NOT_RUN; original
[mini-SWE-agent](history/2026-10-16-mini-swe-dev20-results.md) had 10 PASS,
5 FAIL and 5 NOT_RUN. Models, budgets, policies and environments differ from the
proposed current configuration. Per-task comparisons are descriptive, not causal
architecture gains or held-out generalization. Report PASS/20 and retain all
FAIL/ERROR/NOT_RUN outcomes, costs and completion states.

Benchmark acceptance is the primary repair outcome; diagnostic completeness is
separate. [public-checks-v1](history/2026-10-29-public-check-submission.md) uses
current required public checks and scoped diff for submission. Reproduction,
path diagnosis and observation correction remain advisory evidence, with honest
delivery labels. The compatible CLI default is still reproduction-gated-v1.
No global default switch or quality improvement is claimed.

Keep the [required public check contract](history/2026-10-28-required-public-checks.md):
known FAIL and required NOT_RUN block finish, edits invalidate old PASS, and fresh
public failures reach the next response. Keep source/mutation boundaries,
recovery identities, uncertain-execution stops and total budgets.
The [helper API contract](history/2026-10-29-helper-api-contract.md),
[bounded observation correction](history/2026-10-29-observation-shape-correction.md),
[edit prerequisite delivery](history/2026-10-29-edit-prerequisite-guidance.md) and
[optional observation/replay guidance](history/2026-10-29-probe-followup-guidance.md)
remain implemented. Guidance adds no automatic replay, reserve or submission gate.
Availability and delivery do not prove model use or repair correctness.

The [SQLFluff follow-up](history/2026-10-29-probe-followup-single-results.md)
repaired the task and passed acceptance after public regression feedback prompted
a second edit. The model did not replay its pre-edit helper; the later
[saved-patch comparison](history/2026-10-29-sqlfluff-success-mechanism.md) is an
operator diagnostic. Card causality and repeatability remain unresolved.
The [pvlib native reassessment](history/2026-10-29-private-evaluation-logs-pvlib-native.md)
reproduced A PASS/B FAIL and retained exact operator-only diagnostics. Detailed
private receipts/logs stay outside solver feedback; acceptance is unchanged.

The [five-task result](history/2026-10-29-repair-five-results.md) is CLOSED:
4 acceptance PASS/1 FAIL, all public checks and submissions PASS, USD2.5451965.
All 54 provider calls/costs reconcile. The
[pydicom public comparison](history/2026-10-29-pydicom-public-logging.md) confirms
preserved user configuration and duplicate output reduced from two to one, while
default debug output changed from one to zero. This task-specific behavior does
not justify a new general solver rule. The benchmark FAIL remains, and private
acceptance expectations are not repair hints. Formal original obligations remain
unverified without erasing public observations or acceptance PASS.

Keep runtime rules and budgets unchanged during this measurement. Helper return
types, incomplete capture, repeated-run reliability and held-out improvement
remain unresolved. Unused previous funds authorize no further paid run.

## Supporting evidence

- [Astroid clean-start result](history/2026-10-29-helper-contract-fresh-results.md):
  original F0010 repaired, 1231 public tests PASS, isolated acceptance/safety PASS;
  USD2.0153455. Call tracing was incomplete; one exposed development task only.
- [Security maintenance](history/2026-10-23-security.md): refreshed host dependencies
  and public Python 3.12 images after the emSign incident. Old task/legacy images
  remain offline-only. New runs need newly prepared identities; prior manifests
  do not authorize execution against the updated runtime.
- [Helper-path results](history/2026-10-22-helper-path-results.md): useful information,
  no repair in A1/B1/B2; partial comparison stopped on drift. Allocation closed.
- [Invocation linkage](history/2026-10-22-probe-invocation-results.md): submitted
  repairs 0/3; ON mechanism use 0/2. Partial run; no adoption or quality claim.
- [Caller evidence](history/2026-10-19-caller-evidence-results.md): A/B 0/6;
  original-caller verification remained missing.
- [Portfolio remeasurement](history/2026-10-06-portfolio-dev20-results.md): 9/20,
  below the 11/20 threshold; test300 remains unprepared and unauthorized.
- [History](history/README.md) indexes the closed investigations and allocations.
  Their past next steps, settings and approvals do not carry forward.

## Execution and claim boundaries

All prior paid allocations are closed. The [older interrupted call](history/2026-09-28-expectation-review-results.md)
retains unknown billing; later settled allocations do not resolve it. The latest
source-ready diagnostic also retains one unsettled response.

Fresh solves, seeded repairs, funded continuations, saved-patch evaluations,
operator replays and scripted tests are different evidence. Do not pool them as
solve rates or expose private evaluator details to the agent. Public case support,
submission, independent task acceptance and safety are separate. Mock safety is NOT_RUN.

Do not start Docker Desktop or pull/build evaluator images automatically. Preserve
exact recovery identities, zero SDK retries and stop-all on count/transport/billing
uncertainty. Saved-candidate and operator successes remain distinct from clean-start
development outcomes above. Repeated fresh-solve performance and held-out
improvement remain unverified.
Public-check PASS, safety PASS and successful submission do not establish repair
correctness. Linux CI and general improvement remain unverified.
