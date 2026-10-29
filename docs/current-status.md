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

Prioritize integrated development, as requested on 2026-10-30. Apply coherent known
fixes together, run relevant local checks, then exercise the current configuration
on a small set of public development tasks from start to finish. Review task
acceptance, regressions, cost and elapsed time; use observed failures to choose the
next fix. This is the default development loop, not a sequence of one-factor studies.

The [latest integrated run of tasks 3, 9 and 16](history/2026-10-30-integrated-3916-results.md)
is CLOSED. pvlib1154 and pydicom1694 passed independent acceptance; SQLFluff1517
failed. Safety passed for all three. USD1.899919 settled against USD12; all 33 model
calls and 33 input counts settled and linked, with no retry. Two-worker wall time:
10 min 32 s. The roster differs from earlier panels, so batch totals are not a
matched comparison or a general success rate.

pvlib used 10 calls / 245.563 s, with no mutation rejection or undo, and explicitly
ran its new file. It created that file immediately, so exact-restoration use was
not exercised. Pydicom repaired its implementation once and corrected its new test
twice before acceptance PASS; this does not establish an edit-cap effect.

Next investigation: SQLFluff1517's public-evidence/correctness gap. Its 167-PASS
public check and candidate API probe preceded acceptance FAIL. The probe supports
crash avoidance for the double-semicolon example; broader delimiter handling and
token/tree preservation remain unverified. The public issue leaves the desired
duplicate-semicolon handling open, so a parse error alone is not a proven defect.
Inspect public contracts and examples; no private evaluator content or new funded
run is needed to frame that diagnosis. Its new test has directory-discovery evidence
only, not a separate file selection. Do not turn this into another blanket gate.

Keep [advisory test-selection feedback and batched source tracking](history/2026-10-30-test-execution-visibility-and-latency.md).
The [earlier 3/13/18 run](history/2026-10-30-integrated-selection-results.md) observed
explicit selection of previously omitted file types but also exposed the two
validation conflicts below. Provider dispatch still occupied 68-74% of task time
in the latest run; lower Git latency alone is not an end-to-end speed claim.

The [two test-validation conflicts](history/2026-10-30-test-validation-fixes.md)
are fixed locally. Exact original-byte restoration now uses one shared rule for
both mutation tools. pvlib's wrapper pins the projection target and local anchor,
allowing admitted test additions while the shared policy preserves original tests.
Replaying the previously rejected first candidate reached pytest: 99 PASS; original
source with the identical added test gave 1 FAIL / 98 PASS. This used no model or
private evaluation. The live follow-up had no validation conflict, but used a
different test-edit path; causal benefit remains unproven. Another paid ablation
is not a prerequisite for development.

No forecast OFF/ON repeat, cap4 diagnostic or 4-vs-12 comparison is a prerequisite
for continuing with the selected 12-edit configuration. Isolate a condition only
when an important design decision remains unresolved after inspecting a real
failure. A combined result measures the configuration; it does not identify the
contribution of each change. Use the existing result records and concise failure
notes rather than adding a planning/reporting layer for every fix.

The [forecast-only comparison](history/2026-10-30-forecast-only-comparison-results.md)
is CLOSED: zero new edits in both arms; OFF acceptance FAIL, ON unsubmitted/NOT_RUN;
USD0.5311435 settled. Public controls showed that OFF's added sys.path entry masked
the original failure. Preserve the public caller's reproduction conditions in
future diagnostics and investigate repair-route closure if it recurs in full runs.
Neither finding requires another isolated study before integrated development.
Unused allowance is closed; this direction change launches no new paid work.

The [source-delivery fix](history/2026-10-29-public-alternative-and-budget-readiness.md)
remains selected: completion retains already bounded current source while mutation
tools are offered. It repairs a delivery defect; live repair benefit is unproven.
The operator's one-line Astroid alternative remains a separate local result, not
an agent-generated repair. The [file lifecycle](history/2026-10-29-file-lifecycle-followup.md)
and [usability](history/2026-10-29-runtime-usability-followup.md) changes also remain:
new/multiple files and receipt undo, exact recovery, accurate action forecasts,
character-paged reads and the configurable 12-edit default.

The current runtime's quick regression passed 1,208 tests, including isolated mock
evaluation, and skipped one unavailable symlink check: 332.31 seconds with four
file-grouped workers and no failures. Both validation fixes are included. Ruff
passed. Full-suite completion, Linux validation and causal quality/speed benefit
remain unverified; changing task rosters cannot establish a batch speed gain.
The historical dev20 measurement stays [closed](history/2026-10-29-repair-dev20-results.md):
10 PASS, 9 FAIL, 1 unsubmitted/NOT_RUN; USD11.7967235. It is development context,
not a causal baseline for the combined current configuration.

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
