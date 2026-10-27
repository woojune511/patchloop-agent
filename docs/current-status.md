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

The [caller-source trial](history/2026-10-27-dependency-source-results.md) acquired
caller source, rechecked F0010 and executed a useful helper, but made zero edits.
The next response exhausted 40K without a tool call. A correction then had about
six usable seconds and ended PROVIDER_UNCERTAIN; its exception class was not
recorded. Confirmed cost is $0.49747575 for 15 settled calls, with one unsettled
correction. The allocation is closed; final public/isolated checks were NOT_RUN.

The [first-edit checkpoint intervention](history/2026-10-27-first-edit-checkpoint.md)
now rejects cycle corrections below 30 usable seconds after original-check reserves,
logs safe exception classes and actual request timeouts, and provides lossless
public-context deduplication. Thirty seconds is an admission floor, not guaranteed
response-completion time. Production defaults and legacy time admission are unchanged.

The next controlled question is whether the model reaches a justified first edit
from the same saved post-helper evidence with duplicates retained (A) or encoded
once with references (B). Both conditions receive fresh equal budgets and preserve
all unique public facts/source lines. There is no new exploration or forced probe.
The complete prepared request differs only in the evidence representation. This
changes reading work as well as length, so it is not a pure token-length effect.
No solution hints or private evaluation details enter the packet.

Local validation: 112 focused PASS/71.16s; 472 quick PASS/116.57s including isolated
mock evaluation; Ruff PASS. All 14 saved source anchors matched a fresh workspace.
The proposed paid scope is A/B once each,
$1.20 per condition and $2.40 total, mini/xhigh, two ordinary responses, one
correction and one new edit. New exact approval follows preparation and preflight.
No provider or target execution has run for this change; live repair is unverified.
After an edit, original-call feedback precedes the final response; public regression,
isolated acceptance, cost and completion remain separate outcomes.

Prior repair-cycle/source-access evidence is indexed in
[October 27 history](history/2026-10-27/README.md). The
[relative-root operator repair](history/2026-10-27-relative-root-repair.md) passed
local isolated acceptance but is excluded from model inputs and is not a model
solve. Historical mini-SWE-agent context settings are documented in the
[context analysis](history/2026-10-26-target-failure-context-analysis.md); no
context-only quality effect is established.

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
resolver candidate now passes. No live model has newly achieved an accepted solution
in these follow-ups.
Public-check PASS, safety PASS and successful submission do not establish repair
correctness. Linux CI and general improvement remain unverified.
