# Current status

Updated: 2026-10-24. Runtime source owns behavior. Historical reports are evidence,
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

[Request correction](history/2026-10-23-requests.md) binds public task/issue identity
and credits correction only after actual argument changes pass full preflight.
The [size repair](history/2026-10-24-size.md) separates 8,000-character authored and
host observer allowances while preserving bounded transport and replay identities.
The current v51 guidance asks for discriminating observations and keeps unexpected
execution unverified. Frozen comparison and completion semantics are unchanged.

The [fresh repair pilot](history/2026-10-24-repair-live.md) is closed. One Astroid-1333
solve on gpt-5.4-mini-2026-03-17 cost USD 0.525472350 in 432.812 seconds, within the
USD 0.88 cap. A missing program was corrected to a valid 2,450-character request,
which executed. The old host-size rejection did not recur in that request.

Original acquisition and repair still failed. The model passed a string instead
of a command-argument list to pylint and searched the returned object for errors
emitted on stdout. Both faulty base/candidate observations matched the desired JSON;
neither established the declared base failure. Automatic replay and public
regression PASS therefore retained `unverified_delivery`. Independent acceptance
failed, safety passed, and the frozen public missing-init/control checks were
FAIL/PASS. The missing-init case analyzed the child but retained F0010.

The first unresolved stage is faithful call/observation construction, not execution
size or exhausted completion funding. The next small diagnostic should distinguish
argument-shape guidance from diagnostic-capture problems before adding another
prompt/tool/gate. No remedy or new live run is selected. One exposed-task sample
does not estimate quality or establish a causal effect of the guidance.

The [operator oracle experiment](history/2026-10-24-oracle.md) remains separate:
two operator-corrected programs acquired their declared failures on the unchanged
base; it did not establish autonomous repair. Prior mismatches are never regraded.
Its runtime validation passed 237 distinct repository cases, including isolated
mock evaluation, plus 35 operator-predicate cases. Routine verification remains
quick plus changed-owner cases; this execution closeout changes documentation only.

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
retains unknown billing; later settled allocations do not resolve it.

Fresh solves, seeded repairs, funded continuations, saved-patch evaluations,
operator replays and scripted tests are different evidence. Do not pool them as
solve rates or expose private evaluator details to the agent. Public case support,
submission, independent task acceptance and safety are separate. Mock safety is NOT_RUN.

Do not start Docker Desktop or pull/build evaluator images automatically. Preserve
exact recovery identities, zero SDK retries and stop-all on count/transport/billing
uncertainty. A live replay of an unacquired case is observed; replay/rejection after
a faithfully acquired original failure, Linux CI and general improvement remain
unverified.
