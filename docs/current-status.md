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

Keep the [required-public-check design](history/2026-10-28-required-public-checks.md):
known FAIL and required NOT_RUN block successful finish; accepted edits require
fresh current-diff checks and deliver their failures to the next response.
Model notes remain advisory. The [assisted continuation](history/2026-10-28-required-public-check-repair-results.md)
passed11 required public cases,1231 regression tests and isolated acceptance/safety
after two edits. That saved-candidate result is not a fresh solve or generalization
estimate. Its allocation is CLOSED.

The [clean-original follow-up](history/2026-10-28-autonomous-fresh-results.md)
reproduced F0010, inspected source31 times and made two edits, but still failed its
selected processing witness. Tool actions38/40 left two versus four needed for
completion; USD1.549624/4.50 and656.865 active seconds were below their limits.
Public regression, submission, isolated acceptance and safety are NOT_RUN.
Its allocation is CLOSED; supplemental operator counterexamples were not injected.

The [public-record analysis](history/2026-10-28-autonomous-fresh-analysis.md)
found that the complete caller file and the first patch's negative feedback reached
the model. Both edits treated the missing init file downstream without establishing
that the caller selected and processed the real fixture file. An initial callee
search fragment was lost before the second edit, but missing caller information
does not explain the first edit. Exact repeated inspection requests were absent.

After reproduction, ordinary probes were denied under protected recovery cost while
reads could use a minimum-success path. The first-observation selector also stayed
inactive for this ruleless case. Thus source-only exploration was partly a host
action-set restriction, not simply model avoidance of available observation.
An early helper configuration failure remained a separate UNKNOWN obligation;
pure policy replay showed that this alone did not cause the probe denial.

The [observation-opportunity change](history/2026-10-28-observation-opportunity.md)
now exposes bounded captured-call selection for null diagnostic rules and aligns
reading, general-probe and first-observation minimum-path admission. General probes
reserve a prospective additional case; reading/probing preserves an available first
observation. Response/action/cost/time and protocol-correction reserves remain real.
Protected later-failure recovery is preferred when feasible; its release is explicit.

Fresh v10 invocation evidence distinguishes host-confirmed settings rejection before
any captured target entry from unknown execution. Such attempts retain their costs
and counters but do not become replay obligations. Old v1-v9 programs and unknown
receipts are preserved; saved v9 and fresh v10 argument correction remain supported.
Original verification and required checks are not waived by selection or observation.
Focused79 and quick792 checks pass, including isolated mock evaluation. Pure replay
of the saved public state opens reading and both observation options under the same
limits while retaining the old UNKNOWN obligation. This is local mechanism evidence.

The next live question is whether the model uses the restored choice to inspect
file selection/processing and revise its repair hypothesis. Local mechanism checks
do not answer it. A [clean-start follow-up](history/2026-10-28-observation-opportunity-fresh-plan.md)
is prepared for one full-model run with the same USD4.50/20-response/40-action/
three-edit/2400-second limits. Offline first-request audit and read-only preflight
pass. The new command/cap confirmation is pending; no provider execution has started.
Prior allocations remain closed and benchmark candidates are unchanged.

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
