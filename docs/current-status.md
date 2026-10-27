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
finished normally with public regression PASS but isolated acceptance FAIL.
The [public diagnosis](history/2026-10-28-canonical-diagnostic-analysis.md) found
three distinct causes: error absence hid skipped child analysis, generated cache
entered fixture identity, and a target-not-entered request polluted case accounting.
The allocation is closed; this was not resource exhaustion.

The [processing-evidence implementation](history/2026-10-28-processing-evidence-implementation.md)
addresses these mechanisms in fresh v7 invocations (wire v65). Diagnostic rules
pair failure absence with a same-call positive processing code; complete empty
output is a mismatch delivered before another response. Silent APIs retain actual
return/effect observations. Stable fixture/output sibling roots prevent generated
output scope from being declared as fixture input. Explicit settled pre-target
errors stay audited and budgeted as attempts, without becoming established-case
obligations. Unknown execution and actual target failures retain their obligations.
Saved v1-v6 programs keep their bytes and semantics. Limits are unchanged.

Local core 35 cases passed in 24.954s. Quick covered 568 cases in 159.286s;
11 legacy/current fixture compatibility failures were corrected and all passed
targeted reruns, with runtime unchanged. Ruff and isolated mock evaluation PASS.
The linked record preserves the split validation. No paid model execution or new
Astroid acceptance result is part of this change.
Positive code selection still does not prove intended-file coverage or semantic
correctness. The next live question is whether a model chooses discriminating
processing evidence and rejects a no-op repair under the existing bounded loop.
The [fresh pilot](history/2026-10-28-processing-evidence-fresh-results.md) has now
run once under the approved same mini/xhigh / USD 4.50 allocation. It stopped at
INCOMPLETE_RESPONSE before original execution or edits: the first request attempt
used 40K output (39,753 reasoning), then correction used 25K, with no valid tool
call from either. Inputs were 29,270 and 15,948, below the 60K ceiling. Six initial
read/search actions completed. Actual cost USD 0.40966830, active time 552.214s;
all six model/count calls settled. No submission or evaluation occurred.

The new processing/identity/phase mechanisms remain live NOT_EXERCISED. First
request construction is the observed bottleneck; request burden versus model
configuration remains unresolved. There is no evidence here for raising the global
cost/context limit or claiming a repair gain. Allocation CLOSED, no retry. General
settings and runtime stay unchanged; no further paid execution is authorized.

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
