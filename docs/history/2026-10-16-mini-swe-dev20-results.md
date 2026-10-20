# mini-SWE-agent dev20 baseline results

Date: 2026-10-16. Allocation CLOSED; official=false and claim-ineligible.
All 20 fresh attempts ran. Mini resolved 10/20;
5 submitted patches received native FAIL and
5 attempts were unsubmitted/native NOT_RUN.
Recorded fresh-run cost was USD 3.2146974; including
the first stopped attempt, cumulative cost was USD 3.2171004
of the authorized USD 24. This establishes a bounded development-panel baseline,
not an official mini-SWE-agent score or an estimate of general model accuracy.

## Question and frozen comparison

The user requested an external-agent reference against existing PatchLoop results.
Repeated prompt/context experiments had not established better acceptance; an
independent, simpler harness could show which of the same public tasks remain
difficult under different tools and execution policies. This is a descriptive
comparison. A win would identify a task for public-trace investigation, not prove
a causal harness feature; shared failures would not prove a model ceiling.

The user explicitly approved the corrected fresh rerun, isolated-container bash
and a cumulative USD 24 ceiling including the prior USD 0.002403. The
[first stopped attempt](2026-10-16-mini-swe-count-stop.md) remains unchanged.
Its adapter defect omitted no generations from billing: one generation was
settled, with no unmatched dispatch. Its raw count-failure billing flag remains
preserved separately from that audited usage evidence.

- Agent: mini-SWE-agent v2.4.6, upstream
  `a83fcae82d2a08f0ee0c688f9d137b3566c097f8`; upstream DefaultAgent, SWE-bench
  prompts, Responses action parser and observation/error templates retained.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh, default service tier, global endpoint,
  desired maximum output 25,000; exact primary-repository `.env` credential file.
- Frozen execution checkout: `dca0f0cf4848a6c53377f1352aa356eaf3a9730e` at
  `C:/Users/geonj/.codex/worktrees/mini-swe-dev20/PatchLoop`.
- Packet: `sha256:680a2c6377a7267afc76354cce9d00df8c90234355c432aa60c77a1a14658b7a`.
  Preparation `C:/pt/mini20prep05`; fresh state `C:/pt/mini20live02`;
  audit/comparison `C:/pt/mini20rerun01`.
- One fresh attempt per original task, one worker, 40 generations and 100 bash
  actions/task. USD 23.997597 new allocation, equally divided into USD 1.19987985
  per task, with no transfers. Solver allowance 1,470 seconds; separate native
  grading process allowance 330 seconds and test timeout 300 seconds.
- Exact input counting before each dispatch, worst-case reservation, zero SDK
  retries and recorded usage settlement. No resumed or replacement attempt.
  A corrected saved-request count-only precheck passed once (3,154 input tokens,
  zero generations); previous solver history was not supplied to fresh attempts.

All 20 instance/base/source-archive/public-text/task-package/image/native-row
identities matched the original prepared roster. Core PatchLoop runtime hash
remained `sha256:8d1abdcba22c1f91beb037bd22dc9ed4d209ef173843a74e9b643d9ebd1c12ba`.
Native SWE-bench grading remained pinned to
`02e7a74ffd0b707aab73d203fe87bdc7c76afc8e`. No image was pulled or built.
The approval and source/dependency bindings were verified before execution and
again by the provider-free audit.

Each solver used an offline container with a read-only root, no host mounts or
credentials, dropped capabilities and bounded CPU/memory/PIDs. A verified public
base archive populated `/testbed` tmpfs with synthetic Git history. The solver
container was destroyed before private grading. No private tests, reference
patches, previous trajectories or historical verdicts entered solver context.

## Execution and accounting

| Axis | Result |
| --- | --- |
| Planned / started / submitted | 20 / 20 / 15 |
| Native PASS / FAIL / NOT_RUN | 10 / 5 / 5 |
| Scope checks | 15 PASS; 5 NOT_RUN |
| Registered PatchLoop evaluation / registered safety | NOT_RUN for all 20 |
| Generations / input-count requests / bash actions | 524 / 524 / 740 |
| Fresh-run recorded cost | USD 3.2146974 |
| Prior stopped generation / cumulative recorded cost | USD 0.002403 / USD 3.2171004 |
| Run wall time, first solver container request to panel close | 3452.835 seconds (57m33s) |
| Fresh billing evidence / cleanup | All dispatched generations settled; all solver/native cleanup confirmed |

Unsubmitted row numbers: 8, 13, 16, 17, 18. All five exhausted the 40-generation
limit; no task reached its cost cap. Their terminal status and exact costs remain
in `audit.json`. Native NOT_RUN is not a failing native
test verdict. The overall resolved count uses all 20 attempts; success conditional
only on submitted patches would answer a different question. No count/transport/
billing uncertainty or grading-infrastructure stop occurred during this fresh panel.

Cost is reconstructed from provider-reported usage at USD 0.75 uncached input,
USD 0.075 cached input and USD 4.50 output per million tokens, checked against
[official pricing](https://developers.openai.com/api/docs/pricing) on 2026-10-16.
It is a usage-ledger total, not invoice reconciliation. The count-only precheck
and earlier settled generation are reported separately from fresh generation
counts. Wall time excludes preparation, the first stopped attempt and closeout.

## Historical results and per-task comparison

These historical panels used the same selected mini snapshot/xhigh. No new
PatchLoop solve or saved-patch reevaluation was performed for this comparison.

| Panel | Native result | Recorded USD | Recorded wall time |
| --- | --- | ---: | --- |
| Original registered dev20 | 10 PASS / 10 FAIL | 5.01124395 | Not restated |
| Portfolio full remeasurement | 9 PASS / 11 FAIL | 3.46111455 | 102m19s |
| Previous partial current panel | 8 PASS / 9 FAIL / 3 NOT_RUN | 5.39413050 | 67m49s |
| Corrected current panel | 11 PASS / 7 FAIL / 2 NOT_RUN | 5.08206870 | 69m38s; two workers |
| Separate rows 18/20 supplement | 0 PASS / 2 FAIL | 1.07327790 | 15m40s |
| This fresh mini panel | 10 PASS / 5 FAIL / 5 NOT_RUN | 3.2146974 | 57m33s; one worker |

The [original/full record](2026-10-06-portfolio-dev20-results.md) binds original
`3077f81afe3d85e301e3af99b09bf4c117425f52` and portfolio
`59d90f6b5fbf1ff61f8b756a030b580e621e7c76`. The
[corrected record](2026-10-06-corrected-dev20-results.md) binds
`e3aa70804005f110c9f6ed32b0ba792958a56aa3`; its
[separate supplement](2026-10-06-search-once-supplement.md) binds
`a28aa364f44901bc06162281ed7e773d26c92667`.

The partial panel's registered result was 8 PASS / 8 FAIL / 1 ERROR / 3 NOT_RUN;
its native FAIL paired with registered ERROR remains disagreement. The corrected
panel's original two NOT_RUN rows remain unchanged; its later supplement is not
pooled into a new all-20 score. A dash below means not included in that supplement.
Full instance IDs, base commits and source hashes are in `comparison.json`.

| # | Task | Mini | Original | Portfolio | Corrected | Supplement | Mini calls | Mini USD |
| ---: | --- | --- | --- | --- | --- | --- | ---: | ---: |
| 1 | marshmallow-1343 | PASS | PASS | PASS | PASS | - | 23 | 0.1052628 |
| 2 | pvlib-1072 | PASS | PASS | PASS | PASS | - | 14 | 0.04789995 |
| 3 | pvlib-1154 | PASS | PASS | PASS | PASS | - | 15 | 0.1117119 |
| 4 | pvlib-1606 | PASS | PASS | PASS | PASS | - | 18 | 0.21845205 |
| 5 | pvlib-1707 | FAIL | PASS | FAIL | PASS | - | 22 | 0.1412241 |
| 6 | pvlib-1854 | PASS | PASS | PASS | PASS | - | 11 | 0.0585618 |
| 7 | pydicom-1139 | FAIL | FAIL | FAIL | FAIL | - | 22 | 0.15040095 |
| 8 | pydicom-1413 | NOT_RUN | FAIL | FAIL | PASS | - | 40 | 0.25109775 |
| 9 | pydicom-1694 | PASS | PASS | PASS | PASS | - | 27 | 0.07609545 |
| 10 | pydicom-901 | FAIL | FAIL | FAIL | FAIL | - | 25 | 0.12920625 |
| 11 | astroid-1196 | PASS | PASS | PASS | PASS | - | 25 | 0.1589499 |
| 12 | astroid-1268 | FAIL | FAIL | FAIL | FAIL | - | 28 | 0.10528005 |
| 13 | astroid-1333 | NOT_RUN | FAIL | FAIL | FAIL | - | 40 | 0.3499104 |
| 14 | astroid-1866 | PASS | FAIL | FAIL | PASS | - | 20 | 0.0861471 |
| 15 | pyvista-4315 | PASS | PASS | PASS | PASS | - | 28 | 0.16591845 |
| 16 | sqlfluff-1517 | NOT_RUN | FAIL | FAIL | FAIL | - | 40 | 0.2663844 |
| 17 | sqlfluff-1625 | NOT_RUN | FAIL | FAIL | FAIL | - | 40 | 0.244407 |
| 18 | sqlfluff-1733 | NOT_RUN | FAIL | FAIL | NOT_RUN | FAIL | 40 | 0.27188625 |
| 19 | sqlfluff-1763 | FAIL | FAIL | FAIL | FAIL | - | 25 | 0.21739515 |
| 20 | sqlfluff-2419 | PASS | PASS | PASS | NOT_RUN | FAIL | 21 | 0.0585057 |

- Original: on its 20 historically graded tasks, mini resolved 10, historical PatchLoop 10; mini has 5 ungraded attempts in this subset. Historical FAIL to mini PASS: astroid-1866. Historical PASS to mini non-success: pvlib-1707.
- Portfolio: on its 20 historically graded tasks, mini resolved 10, historical PatchLoop 9; mini has 5 ungraded attempts in this subset. Historical FAIL to mini PASS: astroid-1866. Historical PASS to mini non-success: none.
- Corrected: on its 18 historically graded tasks, mini resolved 9, historical PatchLoop 11; mini has 4 ungraded attempts in this subset. Historical FAIL to mini PASS: none. Historical PASS to mini non-success: pvlib-1707, pydicom-1413.

`comparison.json` also retains pairs where both panels actually obtained native
grades, together with full-roster transitions. Neither view relabels missing
grades. Comparisons with the corrected panel use its original 18 graded tasks;
mini's outcomes on original rows 18/20 remain separately visible above.

## Public trace findings and limits

- `astroid-1866`: mini PASS versus portfolio FAIL and corrected PatchLoop PASS.
  Mini expanded formatting-error handling to return Uninferable, then obtained
  14 focused passes and 1,378 full-suite passes (80 skipped, 14 xfailed).
  This is a concrete successful repair, not a newly isolated feature effect.
- `pvlib-1707`: mini FAIL versus portfolio FAIL and corrected PatchLoop PASS.
  Mini repaired the shown `n=1` angle example and obtained 30 public test passes,
  yet native grading failed. Those public checks did not establish full task
  correctness. The exact private-test failure cause was not inferred from them.
- `pydicom-1413`: 212 public tests passed after a source change, followed by more
  inspection and a final diff. At 40 generations mini stopped without submitting.
  Native correctness of that unsubmitted candidate is unknown; corrected
  PatchLoop had submitted a passing patch on this task.
- `astroid-1333`: the last action at the 40-call boundary invoked an unavailable
  `apply_patch` shell command and returned 127. No final patch was submitted.
  This is a recorded tool/closure failure, not proof that its candidate repair
  would pass or fail grading.

The unavailable `apply_patch` command appeared once each on eight tasks. Three
of those tasks ultimately passed, two failed native grading, and three were
unsubmitted. Other attempts recovered using available commands, so this error
alone does not explain the panel's outcome. Public output hashes and action IDs
are retained in `public-trace.json`.

Task/model/grader identity is controlled, but agent loop, tool availability,
edit policy, context management, budget feedback and submission procedures differ.
Mini retained linear history, unrestricted in-container bash and unlimited edits
within the final source-only patch constraints. The corrected PatchLoop panel used registered tools,
four accepted edits, additive-test support, segmented context and automatic
rechecks/completion budgeting; earlier panels retain their recorded configurations.
Mini's upstream 250-step/USD 3 defaults were
replaced by this explicitly bounded 40-generation/USD 1.19987985 setup. Staged
solver/grader deadlines, concurrency and the number of actually graded patches
also limit wall-time comparisons. Registered tool-admission safety equivalence
was not assessed; container receipts do not replace that evaluation.

## Validation, evidence and decision

The new focused cap/adapter/documentation group passed 26 tests in 1.53 seconds;
Ruff and diff checks passed. Earlier realistic SDK/upstream replay regressions
passed 89 tests in 38.36 seconds, and the two-turn provider-free upstream mock
reached isolated native grading with the expected negative-control FAIL and
confirmed cleanup. The preparation full suite (5,116 passed, 19 skipped) was
reused and predates the adapter fix; it was not rerun or represented as new evidence.
Final documentation checks passed all five tests; their receipt, Ruff/diff checks
and the report commit are bound in `closeout.json`.

`audit.json` validates packet/source identities, human approval timing, journal
hash chains, request/response artifacts, exact counted/generated inputs, pricing,
reservations, settled usage, unique actions, submitted patch hashes, native
outcomes and cleanup. `comparison.json` revalidates saved historical input hashes;
`public-trace.json` records public command evidence and token totals. These
post-run analyses made zero provider and zero evaluator calls. `input-comparison.json`
binds the unchanged 20-task inputs; the preparation has separate authorization,
preflight, count-precheck and validation receipts. All earlier live/stop records
remain immutable; this document is a separate follow-up.

The external baseline is now measured under the frozen bounds. This result does
not justify replacing PatchLoop's runtime or adopting a particular mechanism.
Recorded task differences and the repeated submission-limit exits provide
concrete subjects for any future investigation; longer budgets or a forced finish
could change outcomes, but that counterfactual was not tested. Preserve the
existing runtime baseline and the first outcomes. The allocation is closed, with
no automatic rerun, budget transfer, test300 evaluation or publication queued.
