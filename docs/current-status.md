# Current status

Updated: 2026-10-30. Runtime source owns behavior. Historical reports are evidence,
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

The [forecast-only comparison](history/2026-10-30-forecast-only-comparison-results.md)
is CLOSED: Astroid checkpoint OFF/ON, GPT-5.4/xhigh, one branch each. New cost was
USD0.5311435 of the approved USD6.636999 cap, all settled. Both chose run_probe
and made zero new edits/checks. OFF submitted the unchanged patch: independent
acceptance FAIL, safety PASS. ON observed the original F0010 and stopped without
submission; independent acceptance/safety NOT_RUN. Unused funds are closed.

Actual first-request count/prepared/dispatch bindings passed. After declared time
normalization, only the forecast field differed; both inputs contained the same
current helper source. The forecast did not preserve the edit/check/finish route
or produce a repair in this pair. ON's different diagnosis/closure cannot be
attributed to the forecast from one stochastic pair. No general effect is established.

A controlled public follow-up identifies the OFF false-success mechanism. Its
probe adds the fixture's absolute root to sys.path. Removing only that line
restores the directory F0010 on the same candidate; the direct-file control passes
in both conditions. Snapshot/profile/cwd/arguments stay fixed. This is public
operator evidence, separate from independent acceptance. No extra model call or
source repair was made. No new prompt, gate or quota change is adopted.

The next correctness question is how to preserve the public caller's reproduction
conditions when constructing diagnostics. ON shows existing tools can reproduce
the failure; a new execution capability has not been shown necessary. Do not
continue this allocation or repeat the pair merely because money remains.

The [source-delivery fix](history/2026-10-29-public-alternative-and-budget-readiness.md)
remains selected: completion retains already bounded current source while mutation
tools are offered. It repairs a delivery defect; live repair benefit is unproven.
The operator's one-line Astroid alternative remains a separate local result, not
an agent-generated repair. The [file lifecycle](history/2026-10-29-file-lifecycle-followup.md)
and [usability](history/2026-10-29-runtime-usability-followup.md) changes also remain:
new/multiple files and receipt undo, exact recovery, accurate action forecasts,
character-paged reads and the configurable 12-edit default.

The frozen runtime's quick suite passed 1,101 tests in 276.40 seconds, including
isolated mock evaluation; Ruff passed. No runtime code changed in this experiment.
Full-suite completion, broader repair benefit and end-to-end speed gain remain
unverified. The historical dev20 measurement stays [closed](history/2026-10-29-repair-dev20-results.md):
10 PASS, 9 FAIL, 1 unsubmitted/NOT_RUN; USD11.7967235. It is not a causal baseline
for the new defaults. Only one of its 20 traces exhausted three edits (one source,
two test revisions); a current cap4 diagnostic must precede any proposed 4-vs-12
comparison. No such new paid scope is authorized.

Keep current-diff required public checks, source/mutation scope, action identity,
independent evaluation and stop-on-uncertainty. public-checks-v1 remains the measured
panel policy; reproduction-gated-v1 remains the compatible request default. Future
paid work needs a new exact task/model/credential/repeat/cap scope.

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
retains unknown billing; later settled allocations do not resolve it. An older
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
