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

The [post-reproduction repair continuation](history/2026-10-28-post-reproduction-repair-plan.md)
is prepared, locally validated and NOT live-executed. It restores the public
Astroid-1333 checkpoint immediately after the completed original probe, preserves
its program/caller/fixture and failure/desired comparisons, and uses the ordinary
repair/recheck/public-check/finish/isolated-evaluation loop. No new runtime gate,
repair hint or diagnostic-rules override was added.

The actual saved failure and both complete call captures are present in the next
model request, with stage needs_mutation. Two independent offline restores agree
at the first count/dispatch boundary after clock/derived-segment normalization.
Historical opaque reasoning is excluded. Core local validation is 26 PASS in about
71 seconds, including mock isolated completion; documentation 5 PASS and Ruff PASS.
Read-only environment preflight is READY. Provider calls and new benchmark calls: 0.

Proposed run: same gpt-5.4-2026-03-05 xhigh, one dev-train current-dev20/13
continuation, NEW cap USD 4.13241570 (not approved). Preserve remaining 15 responses,
33 tools, 3 edits, output40K/correction25K/context60K, solver1727.678 seconds plus
390 evaluation reserve. Historical settled USD0.3675843 is excluded from new cost;
all old allocations remain closed. See the linked plan for sealed controls and files.

The preceding [signature-guided trial](history/2026-10-28-argument-first-reproduction-results.md)
entered the original call and reproduced F0010; its normal package control emitted
W0611. No repair was attempted. Signature inspection was executed but its returned
value was discarded, so adaptive use is not established. Argument correction is
NOT_EXERCISED in that live trial; local correction controls do not prove uptake.

Next evidence must separate same-call error absence and processing, public
regressions, normal submission and isolated acceptance. The case has null
diagnostic_rules and model-authored boolean judgment; independently audit candidate
captures against it. W0611 is an added processing check beyond the public issue.
Checkpoint repair is not a clean-start solve or a general improvement claim.

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
