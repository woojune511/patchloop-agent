# Current status

Updated: 2026-10-26. Runtime source owns behavior. Historical reports are evidence,
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

The [closed live pilot](history/2026-10-26-trace-budget-live.md) delivered complete
traces but retained F0010: spec.find_spec raised before the changed branch, then
the model added an unexecuted test. It ended VERIFICATION_INCOMPLETE at $0.944915400
within $1.20. The remaining two funded minimum calls could not cover four required
calls; no output cap was exhausted. Complete observation did not establish useful
repair revision. The prepared direct-API caller still has shell/venv equivalence
limits, and changed caller conditions prevent causal historical comparisons.

The [revision follow-up](history/2026-10-26-repair-revision.md) separates complete
diagnosis collection from original-effect refutation. The next source edit supplies
a small host-bound changed-observation prediction, checked during the already-required
original replay. Prediction results never replace original verification or checks.

A test-only edit reserves a frozen comparison of the actually added/extended test
before/after the diagnosed source edit, plus remaining source repair and completion.
Strict additive-test receipt chains and unchanged captured failure/environment can
reuse the old diagnosis with explicit historical diff/snapshot provenance. They do
not produce a new current-snapshot trace or renew consumed diagnostic allowances.
PASSED_BOTH and unverified comparison results cannot retire the original failure.

Local core: 68 PASS (37.93 s); quick: 377 PASS (36.34 s, four workers), including
isolated mock evaluation; Ruff PASS. No provider generation or real container execution is part of
this change. Normal output, action, mutation and monetary limits are unchanged;
the unused protocol correction reserve remains reserved.

The [collector](history/2026-10-26-trace-budget.md) and
[first-repair path](history/2026-10-26-first-repair.md) retain their finite budgets,
complete-coverage requirements and recovery identities. The next unresolved question
is whether a real model revises its repair mechanism using the refutation and
resolves F0010 within the unchanged limits. No new paid run is authorized.

The [fresh pilot preparation](history/2026-10-26-repair-revision-live-plan.md) found
that the actual task's public pytest copy wrapper was unsupported by paired
comparison. The adapter now instruments its child pytest while preserving the
registered wrapper's setup; task bytes are unchanged. Wrapper/comparison controls
15 PASS (24.69 s), quick 378 PASS (35.30 s), Ruff PASS; no live target execution.
The proposed new scope is Astroid-1333, gpt-5.4-mini-2026-03-17 xhigh, one run,
40K/25K output ceilings and $1.20 total. Exact request approval remains pending.

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
uncertainty. The latest live run made one source edit and one test-only edit but
retained the original failure; checks, finish, frozen post-submission checks and
independent evaluation were NOT_RUN.
Linux CI and general improvement remain unverified.
