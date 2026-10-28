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

The [ruleless path-diagnosis fix](history/2026-10-28-ruleless-path-diagnosis.md)
connects a valid null-rule original reproduction to the existing bounded diagnosis
and revision route. When the same captured failure persists and changed Python
lines were measured but not reached, the model selects a captured call and public
focus function. The host freezes the original and watches the changed functions.
Call selection remains unverified and cannot renew preparation, rejection or
execution allowances. Linked repair predictions use the next comparable original
replay; canonical rule-based judgments retain their existing requirements.

Pure re-projection of the saved Astroid-1333 receipts opens this route at candidate2
(seq164), while candidate1/3 remain ineligible and all original verdicts stay
refuted. A tiny local fixture verifies diagnosis, recovery without duplicate
execution, linked repair, replay and delivery to model context. This establishes
the local mechanism, not live-model uptake or Astroid repair success. The
[processing comparison](history/2026-10-28-file-processing-results.md) remains
public diagnostic evidence; its target-specific repair answer was not added to
runtime prompts or selection logic.

The [model trial](history/2026-10-28-post-reproduction-repair-results.md) stopped at
three edits despite other resources remaining. First-edit observation with null
rules, changed-failure diagnosis and final edit-cap continuation are unchanged.
Whether this newly available earlier path diagnosis improves the model's next
repair is unresolved. Previously exposed malformed-purpose and stale-example
quick failures are corrected locally. No new provider execution is funded;
USD4.13241570 and all earlier allocations remain CLOSED.

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
