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

The [latest evidence-reuse run of tasks 3, 9 and 16](history/2026-10-30-evidence-reuse-3916-results.md)
is CLOSED: pvlib1154 and pydicom1694 acceptance PASS, SQLFluff1517 FAIL; safety all
PASS. USD2.221501 settled against USD12, with all 33 calls/counts and 53 actions
linked, no retry or pending action. Two-worker elapsed time: 15 min 9 s. The
[preceding same-roster run](history/2026-10-30-contract-guidance-3916-results.md)
had the same verdicts, USD2.66038, 40 calls and 14 min 43 s. This attempt cost
16.5% less but took 3.0% longer. One exposed attempt per condition cannot establish
causal benefit, stable efficiency or general accuracy. All three submissions were
unverified_delivery; no comparable unchanged-base reproduction was supplied.

The [bounded observation-retention fix](history/2026-10-30-verification-evidence-reuse.md)
now has live delivery evidence: pvlib and SQLFluff completion handoffs retained
concrete earlier probe output after intervening actions, and final assessments
used it. Pydicom's failed probe output also survived. Keep this repair of a
reproduced context-loss defect; do not equate it with broader verification or
correct repair. Existing size bounds, historical exclusion and native deduplication
remain; no tool, persistent store or finish gate was added.

Pvlib ran the same full test file twice on the same diff (99 PASS each), then
checked distinct array/scalar conditions. Duplicate test execution remains a
specific latency opportunity. Pydicom again began with a misconfigured WARN-mode
probe, then used RAISE plus a valid control and replaced its mock regression with
actual RawDataElement input. Its final public file ran 27 PASS. These file-level
receipts do not establish line-entry coverage; tracking remained unknown.

SQLFluff public checks ran 167 PASS, but its sole live probe still used only adjacent
`;;` and a normal `;`. The [latest-patch public replay](history/2026-10-30-latest-sqlfluff-public-counterexamples.md)
now confirms the residual defects on this exact submission: whitespace/newline/comment
between semicolons still causes token-loss RuntimeError. The added allow_trailing=False
guard correctly rejects adjacent delimiters while preserving input, but the new early
success return accepts bar.. with min_delimiters=3, a success-condition regression.
Other failed-match/minimum paths still lose the consumed prefix. Normal lists,
sufficient minimum counts and allowed trailing delimiters remain valid controls.

This paired public-only diagnosis took 48.496 s, with no model calls or private
re-evaluation. All 1,699 copied files match except delimited.py. Both conditions
collected the identical added test: original 1 FAIL / 166 PASS, candidate 167 PASS.
The test covers adjacent delimiters, not the separated cases or generic options.
Thus test omission and stale imports do not explain the reproduced gap. The exact
independent evaluation failure remains unknown; no operator repair was applied.

Full implementation and probe output were delivered; the public plan instead narrowed
to suite PASS and the original example, and its probe did not directly observe the
preservation property named in its question. The [contract-to-observation change](history/2026-10-30-contract-observation-guidance.md)
now connects current diff/public source -> contract -> refuting setup -> expected
observable -> actual evidence or untested status in existing post-mutation planning.
Shared guidance carries the same distinction through general, repair and completion
contexts: required state preservation and success eligibility are separate. No new
tool, schema, quota, model round or finish gate is added. Local delivery/authority
validation is recorded in the linked follow-up; actual selection and repair benefit
remain untested with a live model. No automatic paid repeat is pending.

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

The current runtime's quick regression passed 1,252 tests, including isolated mock
evaluation, and skipped one check: 326.05 seconds with four file-grouped workers
and no failures. Validation fixes, shared repair guidance and recent-probe evidence
reuse are included. Focused validation: 124 PASS / 84.91 s; Ruff passed. Full-suite completion, Linux
validation and causal quality/speed benefit
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
