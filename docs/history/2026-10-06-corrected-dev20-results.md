# Corrected current-capability dev20 measurement

Date: 2026-10-06. Allocation CLOSED; official=false and claim-ineligible.
This is a new observation, not a replacement for either previous panel.

## Question and frozen conditions

The user authorized a fresh measurement after the [component audit](2026-10-06-current-agent-audit.md)
and [priority fixes](2026-10-06-agent-priority-fixes.md). The question was whether
the current agent repairs more of the same development-exposed tasks once its
verification capabilities and execution corrections are available. The previous
full panel resolved 9/20; the subsequent panel stopped with 16 agreeing evaluations.
Completion, correctness, cost and time were separate decision criteria. Repeating
an uninformative full panel or tuning exposed failures was not an automatic next step.

- Frozen implementation: e3aa70804005f110c9f6ed32b0ba792958a56aa3.
- Runtime: sha256:db912ef87f74330ace6285939ecdc124a83e14b1a401022fcb5dfe0c9102ca21.
- Canonical packet hash: sha256:ce5465fa7bd236083e67c226744898db6ac20aac4acf95bbe35f5ad750409c75.
- Same 20 exact dev-train tasks, one fresh attempt each, two independent workers.
- gpt-5.4-mini-2026-03-17, xhigh, 25,000 desired output tokens, repository .env.
- USD 1.20 per row, USD 24 total, no transfer; 40 model calls, 100 actions,
  four accepted edits and 1,800 total seconds per task. Evaluation reserves 330
  seconds inside that total, leaving 1,470 solver seconds.
- Probes, selected tests, additive tests and repair recheck enabled. Automatic
  probe replay remains none. Cross-run memory and held-out tuning remain disabled.
- Stop on count, transport, billing or cleanup uncertainty, unexplained completed
  grading disagreement, or frozen identity drift. No retry, resume or replacement.

Before dispatch, a coordinator defect was corrected: the runtime's stop-repetitions
flag also accompanies settled row cost exhaustion. Such exhaustion may stay local
only with reconciled, known accounting within that row's cap. Other stop conditions
retain global effect. The correction added actual parallel continuation and invalid
accounting regressions. It changed no solver prompt or core runtime. The original
plan and its explicit amendment remain separate immutable evidence.

Fresh dependency preparation and all 20 import, ordinary-operation and selected-test
canaries passed. Marshmallow uses Python 3.9, Astroid rows 12/13 Python 3.10, and
PyVista its prepared graphics profile. Actual first admissions independently confirmed
the delivered tools, limits, test declarations and time reservation. Source remained
frozen through closure and the independent audit; only the user's existing AGENTS.md
edit was present.

## Outcome and comparison

All 20 attempts started. Eighteen completed with agreeing registered/native verdicts:
**11 PASS and 7 FAIL**. Row 18 exhausted its solver deadline during uncertain Git
termination; row 20 was interrupted by the resulting global stop. Both retain
acceptance and safety NOT_RUN. The 18 completed rows have safety PASS. This is
still an incomplete 20-task evaluation, not a 20-task success-rate estimate.

| Measurement | Started | Agreeing evaluations | Acceptance | Settled USD | Wall time |
| --- | ---: | ---: | --- | ---: | --- |
| Previous full, 59d90f6b | 20 | 20 | 9 PASS / 11 FAIL | 3.46111455 | 102m19s |
| Previous partial, 2a8bf737 | 18 | 16 | 8 PASS / 8 FAIL / 1 ERROR / 3 NOT_RUN | 5.39413050 | 67m49s |
| Corrected fresh, e3aa7080 | 20 | 18 | 11 PASS / 7 FAIL / 2 NOT_RUN | 5.08206870 | 69m38s |

The previous partial row with registered ERROR has a native FAIL; those axes are
preserved rather than treated as an agreeing behavioral failure. Its NOT_RUN rows
include one peer interruption and two tasks never started.

On the **18 matching tasks evaluated in both the full baseline and this run**,
accepted repairs increased **8 to 11**: three FAIL-to-PASS, eight PASS-to-PASS,
seven FAIL-to-FAIL and no PASS-to-FAIL. Paired cost rose from USD 2.79057885 to
USD 4.23602205. Against the previous partial run's 16 agreeing rows, the same
three gains remain, with eight unchanged successes and five unchanged failures.
The unevaluated row 20 was previously a success, so no all-20 no-regression claim
follows. Incomplete wall time and changed concurrency cannot establish speedup.

| Row | Task | Previous full | Corrected fresh |
| ---: | --- | --- | --- |
| 1 | marshmallow-1343 | PASS | PASS |
| 2 | pvlib-1072 | PASS | PASS |
| 3 | pvlib-1154 | PASS | PASS |
| 4 | pvlib-1606 | PASS | PASS |
| 5 | pvlib-1707 | FAIL | PASS |
| 6 | pvlib-1854 | PASS | PASS |
| 7 | pydicom-1139 | FAIL | FAIL |
| 8 | pydicom-1413 | FAIL | PASS |
| 9 | pydicom-1694 | PASS | PASS |
| 10 | pydicom-901 | FAIL | FAIL |
| 11 | astroid-1196 | PASS | PASS |
| 12 | astroid-1268 | FAIL | FAIL |
| 13 | astroid-1333 | FAIL | FAIL |
| 14 | astroid-1866 | FAIL | PASS |
| 15 | pyvista-4315 | PASS | PASS |
| 16 | sqlfluff-1517 | FAIL | FAIL |
| 17 | sqlfluff-1625 | FAIL | FAIL |
| 18 | sqlfluff-1733 | FAIL | NOT_RUN: solver limit and Git uncertainty |
| 19 | sqlfluff-1763 | FAIL | FAIL |
| 20 | sqlfluff-2419 | PASS | NOT_RUN: peer interruption |

There were 252 model calls and 259 input-count admissions, all settled, with peak
overlap of two task workers and two model calls. Nine probes completed; selected
tests were available but never chosen. Seven accepted mutations touched tests,
including a follow-up repair to one added test; this is not seven independent tests.
No verification-helper edits were attempted or accepted. Counts alone are not
quality evidence.

## Stop mechanism and observed search cost

At 1470.216 active seconds, row 18 ended with LIMIT_REACHED and the message
"Git execution interrupted; descendant cleanup is not established". It had made
28 model calls, four probes and zero accepted edits, with no submission or evaluator
result. Two test-tree search actions admitted at 1342 seconds were still unfinished.
The runtime correctly retained stop_remaining=true for GitExecutionUncertain.
Row 20's next input count was durably prevented; its two earlier model calls were
settled. Independent audit found no later count or generation admission after the
failure terminal. This is cleanup uncertainty, not a confirmed task-local deadline.

No evaluator deadline, cost-cap exhaustion or grading disagreement caused this stop.
The evaluation reserve cannot produce a submission after a solver fails to finish.
No active Git processes or Docker containers were observed in the operator's later
read-only snapshot; that does not retroactively establish cleanup at interruption.

The public search implementation in patchloop/dev/tools.py performs one Git
tracked-file subprocess check per matching file. Each distinct query repeats that
work. This is a concrete source-supported bottleneck in the Windows run:

- Row 16's three parallel negative searches each scanned 1,481 small files. They
  took 169.792 seconds of shared wall time, not their 509.298-second duration sum.
- Row 17's three test-tree searches took 374.205 seconds, 25.46% of its solver budget.
- Row 19's searches occupied 662.823 seconds of union wall time. Nevertheless it
  submitted with 495.661 solver seconds left, so its deadline did not force submission.
- Row 18's completed search intervals occupied 568.247 seconds. Including the
  unfinished final intervals up to termination gives 695.869 seconds, about 47.3%
  of its solver budget. That last figure is a bounded action interval, not proof
  of completed search execution or CPU time.

Small file sizes and fast metadata enumeration weaken the explanation that an
unusually large or pathological file caused these delays. Per-file Git overhead
is supported by source and action timings, not an isolated profiler or replacement
benchmark. Removing that overhead has not yet been measured. The saved failure
omits the particular Git child and direct-reap details, so neither an orphan-process
claim nor an exact subprocess diagnosis is justified.

## Repair behavior: gains and remaining gaps

The three gains contain concrete repair differences on matching task bases, public
issues, model and effort. Pvlib-1707 changed to an output mask for incidence angles
at or beyond 90 degrees, added a scalar/array/Series test and corrected its dtype
expectation through repair recheck. Pydicom-1413 moved the repair upstream to stop
binary-value splitting rather than compensating during writing. Astroid-1866 added
ValueError handling alongside TypeError and passed despite a rejected pytest.param
test addition. None of these three used probes or selected tests. One observation
per task with multiple configuration changes does not isolate any feature's effect.

The available-tool explanation is also insufficient for the remaining failures:

- Pydicom-1139 now accepted the new test method in an existing class, yet still failed
  acceptance after 39 public tests passed. That old restriction cannot explain this
  current result.
- Pydicom-901 and Astroid-1268 submitted after existing regressions passed without
  directly exercising the task-specific behavior.
- Astroid-1333 used two useful probes before editing, but did not recheck the changed
  entry point afterward. SQLFluff-1517 reproduced the public crash and planned a
  focused regression, then submitted after 166 existing tests passed without it.
- SQLFluff-1763 planned an unencodable-buffer/original-file-preservation regression,
  but submitted after 146 existing tests passed, with no added test or probe and
  considerable remaining time and edits.
- SQLFluff-1625 made no helper-edit attempt and completed evaluation with an agreeing
  FAIL. Its public repair recheck passed on the submitted diff. Helper protection
  and the 330-second reserve were delivered, but neither a forbidden-edit rejection
  nor reserve cutoff/recovery was exercised in this row.

These are observed verification gaps, not proof of each native FAIL's exact cause.
Public evidence alone leaves those causes unresolved. No hidden test or reference
patch was projected into solver context or used to author a new candidate.

## Decision and next question

Preserve the execution corrections and these raw outcomes. Three matching repairs
improved, but the complete-panel question remains unanswered and no individual
feature or general performance gain is established. Keep acceptance, execution,
safety and unassessed rows separate. The previous allocations remain closed.

The next focused engineering question is whether one tracked-file enumeration per
search can replace thousands of repeated Git processes while preserving public-path,
matching, freshness and deadline behavior. Characterize it provider-free, including
deadline/cancellation tests, before considering another paid measurement. Preserve
the uncertainty stop rather than weakening it to finish a panel. Verification-choice
quality remains a separate unresolved problem; generic mandatory probes or another
similar prompt experiment do not follow from this run.

No retry, replacement, paid follow-up, held-out/test300 run or publication is queued.
The unused allocation cannot be reused automatically.

## Evidence and validation

Preparation: C:/pt/cd20p06c. Live state: C:/pt/cd20live06c.
Analysis: C:/pt/analyses/current-dev20-corrected-20261006.
Each evidence recipe writes immutable artifacts and append-only, hash-chained
dev-run-v1 journals. Original panels are read-only inputs.

- plan.json, plan-amendment.json, manifest.json, preflight.json and authorization.json
  bind the exact approved scope. result.json binds the closed outcome.
- comparison.json validates saved journals and compares matching task identities.
  independent-final-audit.json checks source, model, cost, tool caps, projections,
  concurrency and stop conformance; it explicitly retains unresolved Git cleanup.
- first-admission-audit.json checks actual delivery. gain-samples.json and
  failure-samples-v1/v2/v3.json retain public repair evidence. search-latency-v2.json,
  row17-protection-limit-audit.json, row19-public-audit.json and row18-stop-audit.json
  separate behavior, search latency and the stop mechanism.
- Before dispatch, 66 focused tests passed in 75.346 seconds and the new coordinator
  group passed 23 tests in 8.997 seconds. Ruff and documentation checks passed.
  validation.json explicitly reuses the prior unchanged-core 4,264-pass/18-skip suite
  and 330-second-reserve isolated mock PASS. That full suite predates the small
  coordinator correction; the new focused regressions cover its delta.
- No further model or evaluator calls were made for comparison or these audits.
  Documentation closeout validation, file hashes and final documentation commit
  are recorded separately in analysis closeout.json.
