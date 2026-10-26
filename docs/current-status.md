# Current status

Updated: 2026-10-27. Runtime source owns behavior. Historical reports are evidence,
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

The [saved-mini verification](history/2026-10-27-mini-candidate-verification.md)
confirmed that generated Pylint cache files caused the earlier strict input-identity
failure. Separating fixture inputs from cache outputs gives matching original and
control conditions: mini removes F0010/unexpected exceptions, but still produces
C0112 and exit 16 on the public empty-file fixture. Its separate acceptance is FAIL.

The [operator namespace-doc follow-up](history/2026-10-27-namespace-doc-repair.md)
changed only `doc=""` to `doc=None` on that saved candidate. Six public probes
confirmed empty output/exit 0 for the original empty and nonempty fixtures,
unchanged standalone controls, preserved real empty-docstring diagnostics and
matching selected inputs. Focused work took 72.899 seconds; the public regression
passed 1,231 tests. Separate isolated acceptance remains FAIL, with regression,
scope and safety PASS. This is a public symptom repair by the operator, not a
new mini-model success or an accepted task solution. The private failure cause
is unknown and is not attributed to any public symptom.

Preserve these artifacts and production defaults. The inherited missing-initializer
guard's broader namespace/path coverage and directory traversal remain unverified.
Next distinguish those paths using public source and discriminating calls before
another paid repair trial. Do not equate absence of F0010, a regression PASS or
one expected output with whole-task correctness. Do not increase model/context
budgets based on this local outcome. All paid allocations are closed.

Public exception frames and cause/context chains are implemented in fresh invocation
v5, with historical observer v1-v4 preserved; see the
[frame investigation](history/2026-10-27-exception-frames.md). Live information,
[request-annotation](history/2026-10-27-request-annotation-results.md) and
[model-setting](history/2026-10-27-model-setting-results.md) comparisons are closed
without an accepted repair. They justify separating evidence delivery, action
selection and task correctness, not a general model-quality conclusion. The
[source-ready run](history/2026-10-27-source-ready-repair-live.md) retains one
unsettled response; the local action-capacity fix does not resolve that billing.

Context continuity is a separate question. The preceding fresh-solve pilot had
no size-triggered reset; raising 60K alone would preserve stage/result resets.
Historical mini-SWE-agent accumulated history without that extra cap, with observed
maximum input 77,660, not a full model window. Tools and budgets differed; no
context-only quality effect is established. See the
[context analysis](history/2026-10-26-target-failure-context-analysis.md).

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
uncertainty. Saved-patch isolated evaluations have completed with acceptance FAIL;
no live model has newly achieved an accepted solution in these follow-ups.
Public-check PASS, safety PASS and successful submission do not establish repair
correctness. Linux CI and general improvement remain unverified.
