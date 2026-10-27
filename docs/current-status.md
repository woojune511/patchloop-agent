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

The [relative-root repair](history/2026-10-27-relative-root-repair.md) now passes
separate isolated acceptance, regression, scope and safety on Astroid-1333.
From clean task source, the operator changed one line in `astroid/modutils.py`:
normalize the search root with `abspath` before comparing it with absolute filenames.
This candidate contains none of the earlier synthetic namespace builder edits.
It is an accepted local operator repair, not a fresh benchmark-model solve.

Ten public probes confirmed the mechanism: base fails with relative root `"."` but
resolves its absolute equivalent. The candidate resolves both, recognizes the
namespace, selects and parses the actual child. Empty input exits 0; `import os`
produces real lint diagnostics; invalid child syntax produces E0001. Direct-file
and ordinary-package controls are unchanged. Focused comparison took 100.340 seconds;
with 1,231 public regression passes it took 113.341 seconds. Isolated acceptance
was run separately once, with no provider calls, credential reads or private
content in coding context. official=false and claim-ineligible.

The [preceding selection diagnostic](history/2026-10-27-namespace-selection-diagnostic.md)
explains the earlier apparent success: the old builder candidate handled a missing
initializer while leaving the child outside the selected file list. Its
[docstring improvement](history/2026-10-27-namespace-doc-repair.md) and
[mini verification](history/2026-10-27-mini-candidate-verification.md) remain narrower
public results with acceptance FAIL; do not rewrite them as this new success.

The [clean-base observation A/B](history/2026-10-27-selection-observation-results.md)
is complete: both mini candidates retained F0010 and failed isolated acceptance,
despite 1,231 public regression passes each. A changed a prefix check on a false
source premise; B appended `__init__` to directory paths and newly omitted the
invalid child in the ordinary-package control. The assigned public packets were
delivered intact. Both reached one edit; no context/output/cost cutoff was reported.
Total settled cost was $0.3003564, with one model run and evaluation per arm.
The initial zero-call preflight metadata error was corrected without changing
model requests or conditions. The [follow-up analysis](history/2026-10-27-selection-observation-failure-analysis.md)
found A edited a search excerpt without the preceding incremental path construction;
its failed helper left no diagnostic opportunity. B could probe but edited directly.
The experiment stopped at the first edit and did not return public failures to the
model. It does not measure recovery after feedback or the full production loop.
This remains operator-assisted, single-pair evidence.
The unresolved issue is testing and revising repair premises against the caller.
Production defaults stay unchanged; this and all prior paid allocations are closed.

The [follow-up design](history/2026-10-27-feedback-source-plan.md) proposes two
fresh continuations from the same saved A candidate with identical public failure
feedback, varying only partial versus complete current-file source. It is design
only, not implemented, sealed or authorized for execution. Selected-file whole
reading is proposed; search-wide automatic full-file output is not. No default
or resource-limit change is active.

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
uncertainty. Earlier saved candidates failed isolated acceptance; the clean-source operator
resolver candidate now passes. No live model has newly achieved an accepted solution
in these follow-ups.
Public-check PASS, safety PASS and successful submission do not establish repair
correctness. Linux CI and general improvement remain unverified.
