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

The [latest fresh SQLFluff run](history/2026-10-30-retained-source-sqlfluff-results.md)
is CLOSED: independent acceptance FAIL / safety PASS, required public check PASS,
12 calls, 24 actions, 1 edit, USD 0.7579325 and 457.526 seconds; unverified_delivery.
All current billing/counting is settled. No retry or extra evaluation is pending.

The [source-retention and finish-description fixes](history/2026-10-30-plan-action-delivery-audit.md)
worked in actual requests: current Delimited lines 1-255 / 12,439 characters remain
after public PASS and before finish, and public-checks-v1 correctly says original
replay is not automatic. Keep both fixes. Existing source limits and submission
rules remain; no new gate or state store was added. Their focused 16/7 tests and
quick 1,265 PASS / 1 SKIP, Ruff and isolated mock evaluation remain the local baseline.

The new patch changes one failure return to a partial success instead of the
previous two. Its added grammar test directly asserts matched prefix and full token
reconstruction for `bar..`. It was authored before post-mutation retention, so this
difference cannot be attributed to that retention. However, it tests only
allow_trailing=True with no minimum. The agent read the existing trailing/minimum
option table but did not connect the changed success meaning to a refuting case
for those options. The single Linter probe checks normal and doubled semicolons.
No observed violation triggered another edit or narrowing. Source delivery is now
demonstrated; semantic verification selection remains unresolved. Do not attribute
independent FAIL to a particular unexecuted case or infer a model capability ceiling.

Keep the [scope-choice instructions](history/2026-10-30-verification-scope-choice.md).
No generic warning, check quota or repeat is justified solely by this result. Any
next intervention should address the observed gap between preserving data and
changing success eligibility; retaining source alone did not close it in this attempt.
The [preceding normal run](history/2026-10-30-verification-scope-choice-results.md)
and [operator counterexamples](history/2026-10-30-sqlfluff-contract-diagnostic.md)
remain separate evidence about earlier patches. This one exposed attempt with two
combined host fixes establishes neither causal repair gain nor stable speed gain.

Two focused reviews are CLOSED and separate from the normal loop's 40-call cap. The first
identified minimum-delimiter risk but hit a300-second wait: USD0.1377155 known, last
call billing unknown. The [remaining-deadline review](history/2026-10-30-sqlfluff-deadline-review.md)
used4 calls/1 probe,217.406 seconds,USD0.189707 settled; four semicolon cases met its
expectations, with no counterexample or final report. It did not test the changed
success conditions. No response exceeded300 seconds, so wait adjustment is not a
proven cause of progress. Keep that diagnostic setting; no automatic repeat is pending.

The [preceding 3/9/16 run](history/2026-10-30-contract-observation-3916-results.md)
had PASS/PASS/FAIL and all safety PASS. SQLFluff then used 13 calls, USD1.0609665
and 566.561 seconds. Current cost/time are lower descriptively, but one exposed
attempt and different batch concurrency establish no stable or causal improvement.
That record retains pydicom's real-data test follow-through gap and pvlib's duplicate
verification; neither was retested here. The [selection audit](history/2026-10-30-verification-selection-diagnosis.md)
remains the public basis for the intervention.

Keep the [bounded observation-retention fix](history/2026-10-30-verification-evidence-reuse.md),
which has earlier live evidence of preserving concrete current-diff outputs across
handoffs. That repairs a delivery defect, not semantic completeness. Size bounds,
historical exclusion and deduplication remain; no new persistent store was added.

Keep [advisory test-selection feedback and batched source tracking](history/2026-10-30-test-execution-visibility-and-latency.md).
The [earlier 3/13/18 run](history/2026-10-30-integrated-selection-results.md) observed
explicit selection of previously omitted file types but also exposed the two
validation conflicts below. Provider dispatch still occupied 68-74% of task time
in the preceding 3/9/16 run and 66-79% in the shared-guidance run; lower Git latency alone
is not an end-to-end speed claim.

The [two test-validation conflicts](history/2026-10-30-test-validation-fixes.md)
are fixed locally. Exact original-byte restoration now uses one shared rule for
both mutation tools. pvlib's wrapper pins the projection target and local anchor,
allowing admitted test additions while the shared policy preserves original tests.
Replaying the previously rejected first candidate reached pytest: 99 PASS; original
source with the identical added test gave 1 FAIL / 98 PASS. This used no model or
private evaluation. The latest pvlib run exercised additions in the existing
projection-target file without conflict; exact original-byte restoration was not
requested. Causal quality benefit remains unproven; another paid ablation is not
a prerequisite for development.

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

Full-suite completion, Linux validation and causal quality/speed benefit remain
unverified; changing task rosters cannot establish a batch speed gain.
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
source-ready diagnostic and the current focused review each retain an unsettled response.

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
