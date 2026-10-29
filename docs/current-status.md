# Current status

Updated: 2026-10-29. Runtime source owns behavior. Historical reports are evidence,
not an active queue.

## Product and working baseline

Build a single coding agent that repairs public software tasks, verifies changes
and submits within bounded resources. Start improvements from observed failures.
Recovery, sandboxing and isolated evaluation support that product.

- dev-head is the sole mutable runtime; official=false and claim-ineligible.
- General baseline: gpt-5.4-2026-03-05, xhigh, 25,000 output tokens.
- Selected policies: segmented-v1, result-or-size-v1, brief-v1, probes enabled with
  policy none, repair-recheck, protected-v1 inspection, per-call-v1 cost admission.
- Limits: 40 model calls, 100 actions, 12 accepted edits, 1,800 seconds.
  Paid work also requires the exact task/model/credential/repeat scope and cap.
- Cross-run memory, held-out tuning and claim execution are disabled. Bounded
  run-local notes remain available. Historical Rapid executables are absent.
- These are selected settings, not CLI defaults or evidence of general accuracy.

See [guide](../.agent/guide.md), [operations](operations.md), [product](product.md)
and [evidence boundaries](evidence.md).

## Active decision

The [runtime usability follow-up](history/2026-10-29-runtime-usability-followup.md)
normalizes fresh versus legacy contract tests, explains action-specific budget
consequences, and gives new dev/repair requests a 12-edit default. Exact all-match
replacement handles repeated changes in one observed file; fresh read ranges use
character pagination without a separate 400-line cap. Explicit historical run limits
are unchanged. These are local engineering changes, not demonstrated repair gains.

Phase projection precedes native-result deduplication instead of replacing its
output. Journal reads reuse only byte-identical validated prefixes, retaining full
byte checks, detached returned objects, fsync and uncertainty boundaries. The local
unchanged-journal benchmark improved; end-to-end speed remains unmeasured.

The quick manifest plus isolated-evaluator mock passed 1,022 tests. Current contract
and audit fixes have focused local coverage; the full suite is not verified green.
The old boundary-panel B driver loses its planning treatment in compact phase prompts;
its failing delivery assertion is retained as an incompatibility detector. See the
follow-up for baseline reproduction, executed checks and remaining limitations.

The [last dev20 measurement](history/2026-10-29-repair-dev20-results.md) stays CLOSED:
10 PASS, 9 FAIL, 1 unsubmitted/NOT_RUN; USD11.7967235. Its 20 responses/40 actions/
3 edits, 2,400 seconds, public-checks-v1, thin and completion-recovery-v1 settings
are historical measurement conditions, not the new default or fresh authorization.
All 19 submitted candidates passed required public checks; acceptance remained
independent. No held-out generalization or causal comparison is established.

The [failure analysis](history/2026-10-29-repair-dev20-failure-analysis.md) and
[two-task pilot](history/2026-10-29-dev20-followup-pilot-results.md) motivate separating
caller/expectation mistakes from resource loss. The
[completion-guidance A/B](history/2026-10-29-completion-guidance-results.md) established
that one optional probe can spend the last edit/check/finish response route while
money, time and edits remain. The new forecast makes that consequence explicit;
its effect on actual model choices is untested. The other arm still had repair
tools but submitted unchanged, so budget explanations alone are not a repair solution.

Keep current-diff required public checks, source/mutation scope, action identity,
independent evaluation and stop-on-uncertainty. public-checks-v1 remains the measured
panel policy; reproduction-gated-v1 remains the compatible request default. No new
mandatory diagnostic gate, paid run or global verification-policy switch is adopted.

Next questions: effect of larger edit allowance on quota-limited tasks; new-file,
atomic multi-file and undo lifecycle; why observed failure does not lead to another
repair; which diagnostic layers can be removed; redundant model turns and stage
latency. See the follow-up's ordered work list and validation boundaries. Every
live comparison needs new exact task/model/credential/repeat/cap authorization.

## Supporting evidence

- [Astroid clean-start result](history/2026-10-29-helper-contract-fresh-results.md):
  original F0010 repaired, 1231 public tests PASS, isolated acceptance/safety PASS;
  USD2.0153455. Call tracing was incomplete; one exposed development task only.
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
uncertainty. Saved-candidate and operator successes remain distinct from clean-start
development outcomes above. Repeated fresh-solve performance and held-out
improvement remain unverified.
Public-check PASS, safety PASS and successful submission do not establish repair
correctness. Linux CI and general improvement remain unverified.
