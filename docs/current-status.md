# Current status

Updated: 2026-10-28. Runtime source owns behavior. Historical reports are evidence,
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

The [canonical diagnostic live pilot](history/2026-10-28-canonical-diagnostic-fresh-results.md)
completed ordinary acquisition, one edit, public regression and normal finish,
then failed isolated task acceptance. Safety PASS is separate. It cost USD
0.59931540 / 4.50 in about 13m38s: 12 responses/counts, 16 actions and one edit.
All usage settled; no retry, operator patch or synthetic submission occurred.
The allocation is closed. This is not resource exhaustion or successful task repair.

The model selected fresh F0010 code rules, corrected an invalid helper argument,
and reproduced the baseline. Host v2 computed true/false, then false/false after
the edit. Actual subsequent requests received that observation, current patch
and public regression PASS (1,231 passed, 69 skipped, 15 xfailed).
The patch synthesizes an empty package module when its initializer is missing.
Code absence does not establish correct file selection or analysis.

The [public operator diagnosis](history/2026-10-28-canonical-diagnostic-analysis.md)
now confirms the candidate processes an empty initializer AST and omits the child
file; direct-file and healthy-directory controls still emit W0611. Two isolated
public probes (28.373 seconds total, no model) matched the saved first-two-call
captures, source snapshots and input fingerprints exactly.

The candidate's first call creates cache/pylint and project1.stats. Including the
whole work/cache root in both input snapshots causes the observed 14-to-16 entry
drift before call-2; no fixture file changed. Delivery stayed unverified. Actual
requests received UNKNOWN and had remaining tools/time, but no positive child-analysis
observation rejected the empty-module candidate. The initial target-not-entered
argument error also remains an unverified case in the aggregate. These are separate
behavior-coverage, identity-scope and obligation-accounting issues.
Changed-wording failure feedback and revision remain NOT_EXERCISED in the live run.

Keep the [canonical host change](history/2026-10-27-canonical-diagnostic-feedback.md):
it removed duplicate helper judgment for fresh calls and kept incomplete execution
unknown. Local normal-runner tests cover changed-text feedback and a second edit;
25 new core cases PASS, quick covered 526 cases/82.779s including isolated mock,
all failed schema/document nodes passed targeted reruns, Ruff PASS. These local
mechanisms and live task acceptance remain separate claims.

Next improve discriminating public observations, distinguish fixture inputs from
generated outputs, and separate pre-target request errors from established baseline
obligations. These recommendations are not implemented. The diagnostic does not
identify private-test details or replace independent acceptance. Do not increase
limits or rerun from unused funds. General settings remain unchanged; no further
paid execution is authorized.

The preceding [saved-evidence trial](history/2026-10-27-public-regression-cycle-results.md)
did receive regression failure, revise and pass isolated acceptance. It used a
diagnostic loop, prepared evidence and synthetic submission, so it does not establish
clean-start normal completion. Keep these evidence scopes separate.

## Supporting evidence

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
uncertainty. Earlier saved candidates failed isolated acceptance; the clean-source operator
resolver candidate passes. The saved-evidence A model trial now passes acceptance;
fresh-solve and held-out improvement remain unverified.
Public-check PASS, safety PASS and successful submission do not establish repair
correctness. Linux CI and general improvement remain unverified.
