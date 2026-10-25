# Current status

Updated: 2026-10-25. Runtime source owns behavior. Historical reports are evidence,
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

The [40K pilot](history/2026-10-25-output40-live.md) acquired the original failure,
made three edits and received comparable early replay after each. All retained
F0010; regression checks, submission and independent evaluation were not reached.
The [diagnosis](history/2026-10-25-output40-diagnosis.md) found that the protected
physical-call horizon closed fresh diagnosis before the monetary stop, and the
40K correction reserve left only two funded minimum calls where three were needed.
Feedback delivery alone did not produce a discriminating observation or repair.

The [resource follow-up](history/2026-10-25-completion-resources.md) implements:

- Reuse-aware forecasts: healthy acquired cases already settled on the current
  diff omit the unreachable failed-finish call/action. Actual replay/check/edit
  work remains; pending, mixed and unknown cases retain final fallback.
- Independent correction output: optional `--max-correction-output-tokens` binds
  a separate allowance under `completion-recovery-v1`. Omission preserves the old
  coupled ceiling; explicit values are checked on resume.
- One bounded diagnostic after comparable original failure on a candidate. It may
  spend speculative recovery while retaining the minimum repair, checks, replay
  and finish. Rejected/cached requests consume it; restart and same-diff replay
  cannot renew it. A diagnostic probe budgets for a possible additional case.

The original invocation v4 identity and early feedback/reuse machinery remain in
place. Current comparable failure still blocks finish; missing/incomparable
observations remain unverified. See the [resource contract](../.agent/completion-resources.md).
Local validation passed: 56 focused checks (45s), 12 final diagnostic checks (15s),
305 quick checks (31s), Ruff and isolated mock evaluation. These establish local
mechanics. Live repair gain, useful diagnosis and output sufficiency remain
unverified. General output and
cost-policy defaults are unchanged. All paid allocations are closed; no new paid
run, continuation, cap increase or target evaluation is authorized by local tests.

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
uncertainty. The latest live run observed comparable failure after an acquired
original case; it did not reach finish or independent evaluation. Linux CI and
general improvement remain unverified.
