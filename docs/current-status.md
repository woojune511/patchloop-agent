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

The [first-reproduction model pair](history/2026-10-28-first-reproduction-model-results.md)
ran mini/full once at the same public checkpoint and xhigh/60K/40K/25K limits.
Mini exhausted 40K then 25K without a tool call. Full produced an admitted request
but failed before both target calls because expected_exceptions=(SystemExit,)
violated an undisclosed helper restriction. Total new cost USD 0.6721752;
all usage settled, metadata audit PASS, allocation CLOSED. No repair, submission
or isolated evaluation occurred. This single pair does not justify model adoption.

The [helper compatibility fix](history/2026-10-28-helper-system-exit-fix.md) now
accepts explicit SystemExit subclasses in fresh v8 calls, matching the automatic
capture already provided. Ordinary exceptions still require exact listed classes;
BaseException/KeyboardInterrupt/GeneratorExit are not silently treated as expected.
The first-original and general descriptions share the explicit API contract.
V1-v7 observer bytes/replay behavior remain frozen; v7/v8 retain canonical judgment,
fixture/output separation and target-entry accounting. Surface v67 binds the change.
No tool, retry opportunity, resource ceiling or completion criterion was added.

Focused local validation: 89 PASS in 28.176s, including frozen legacy bytes,
actual automatic/explicit exit capture, invalid settings, processing observations
and pre-target obligations. Quick covered 594 cases in 190.914s: 587 passed,
including isolated mock evaluation; seven current contract/description pins were
refreshed after proving the intended-only difference and all passed focused reruns.
Four additional surface-identity owner checks and Ruff also passed. No runtime
behavior changed after the quick run; its final edit was line wrapping for lint.
The maximum-entrypoint observer with call-path hooks is 7,998 characters, within 8K.
No paid model call or Astroid benchmark execution is part of this implementation.

Positive processing coverage remains a separate unresolved issue. The full arm
selected W0611 on the direct-file control only, so its desired observation would
not prove the original directory processed its file. Fixing the helper does not
repair that observation design or establish F0010 reproduction. Actual-model use
of execution feedback after the first settled probe was not tested by the closed
comparison. The [single full-model helper follow-up](history/2026-10-28-helper-first-reproduction-plan.md)
is sealed at the same public checkpoint: retain the long description except
its helper exception paragraph, fixed v8 host, same model and resource limits.
Stop at the first settled probe and audit target entry, F0010 and same-call processing
separately. Offline 60K admission preserves full 40K/25K outputs, exact first-request
diff review passes, and read-only source/image/dependency preflight is READY.
The diagnostic owner checks pass after one test-fixture correction; quick passes
594 cases including isolated mock evaluation. No new runtime behavior was added.
New collection and its USD 4.41415320 cap await exact authorization.

The preceding [saved-evidence repair](history/2026-10-27-public-regression-cycle-results.md)
passed isolated acceptance after public failure feedback; it does not establish
clean-start normal completion. The [canonical diagnosis](history/2026-10-28-canonical-diagnostic-analysis.md)
and [processing-evidence contract](history/2026-10-28-processing-evidence-implementation.md)
remain the basis for same-call processing evidence, fixture identity and request accounting.

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
