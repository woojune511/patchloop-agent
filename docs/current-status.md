# Current status

Updated: 2026-10-23. Runtime source owns behavior. Historical reports are evidence,
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

[Reproduction recovery and funding](history/2026-10-23-repro-recovery.md) separates
primary action results from optional note/plan receipts and separates rejected
requests from actual dispatch starts. Opt-in `--reproduction-acquisition bounded-v1`
requires probes; its acquisition phase permits two dispatches, at most two original
or unclassified request errors and six total investigation actions. Completion
budgets can release it earlier. A durable backend
return resumes without another execution; unknown dispatch outcomes stop.

Opt-in `--completion-cost-policy completion-minimum-v1` requires segmented-v1.
It keeps physical model/tool recovery slots, closes unaffordable actions and reserves
their successful minimum check/finish successors before counting/dispatching the call.
The 128-output-token future floor does not guarantee useful responses or failure recovery.
Existing selected settings and defaults remain unchanged; all paid allocations are closed.

The public-task obligation survives plans and helper cases. Only an unchanged-base
failure plus current comparable support permits `cases_verified_delivery`. Missing
evidence returns `unverified_delivery`; current mismatch/conflict blocks finish.
Independent acceptance cannot upgrade original verification. Invocation receipts bind
sys.argv and preserve legacy replay bytes.

Local controls exercise request correction, separate caps, interruption/replay,
annotation isolation and virtual cost admission. Scripted virtual USD 0.30 controls
reach check/finish with minimum-successor reservation; per-call admission stops early.
Standard mock smoke reaches isolated evaluation PASS, safety NOT_RUN, unverified delivery.
Focused controls: 65 PASS; quick suite: 312 PASS. Full coverage plus an unmodified
short-path recheck: 5,742 PASS, 20 SKIP, no unresolved failures. One Windows temporary
path failure remains in the initial full-run record. These controls do not show
improved LLM repair.

The [prior live diagnosis](history/2026-10-23-repro-budget.md) remains the observed
failure: retained obligation, no acquired original case, unchecked edit and cost stop.
Whether the model corrects the quote and faithfully binds the caller/arguments/oracle
is unresolved. Live delivery/replay and repair benefit remain unverified. No follow-up
paid run is queued or authorized.

## Supporting evidence

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
uncertainty. Linux CI, live replay/rejection of an acquired original case, and
general improvement are unverified.
