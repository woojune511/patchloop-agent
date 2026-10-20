# Current agent audit: repair quality, verification and measurement

2026-10-06. Operator-only follow-up requested by the user: examine the agent's
components and explain why the current test results are not improving.
Starting/current source head: `b97b99cd`. Measured panel: `2a8bf737`.
No solver prompt, runtime, task, acceptance rule or historical artifact was changed.
No new model call, Docker execution, evaluator run or paid allocation was made.

## Question, scope and evidence

The problem matters because infrastructure and verification capabilities have
grown while the same development tasks remain unresolved. Separate whether the
capabilities were unavailable, whether the agent used relevant evidence correctly,
whether resources forced submission, and whether original grading requires more
than the public issue states. A public check PASS, a completed tool call and a
correct repair answer different questions.

The review covers task registration and public checks; model/settings and prompt;
search/source retention; plans/notes; edit admission; probes and selected tests;
feedback and finish decisions; budgets/deadlines; persistence/accounting; parallel
execution; isolated evaluation; and the comparison design. It examines actual
public requests/actions and patches, not private reasoning. Existing private
evaluation outputs were read only as operator evidence after the public trajectory;
they must not become repair-agent context or task-specific hints. Reference patches
were not read for this audit.

Evidence roots:

- `C:/pt/cd20p06b`: frozen manifest, result, postrun audit, submitted/native artifacts.
- `C:/pt/cd20live06/<index>/runs/<run_id>.jsonl`: 18 saved worker trajectories.
- `C:/pt/pv1dev20`: preceding complete panel and per-task costs/outcomes.
- `C:/pt/analyses/current-agent-audit-20261006-v1`: new read-only audit recipe,
  derived receipts and separate append-only `dev-run-v1` journals.

`audit.py` revalidated all 18 worker hash chains and 534 distinct public
request/context artifacts, reconciled all 263 model calls and their input counts,
and reproduced the verification-helper policy gap without executing a candidate.
The context review separately validated all 263 actual model requests and checked
that the latest results reached them. These checks establish the provenance and
specific properties inspected; they are not an exhaustive proof of source correctness.

## What the comparison actually shows

The [current panel](2026-10-06-current-dev20-results.md) has 8 agreeing PASS,
8 agreeing FAIL, one registered evaluation ERROR/native FAIL, one peer interruption
and two unstarted tasks. It is not an 8/20 completed solve-rate result.

For the **same sixteen tasks with agreeing evaluations**, every outcome equals
the preceding panel: no FAIL became PASS and no PASS became FAIL. Their recorded
cost increased from **USD 2.1160632 to USD 3.68085435**, about 74%, with 200 current
model calls. This is a descriptive paired subset, not a causal estimate of any one
feature. The panel changed multiple capabilities and ran each task only once.
Incomplete concurrent wall time cannot establish speedup.

The latest test-method/class admission correction is newer than the measured
runtime. Its structural/local test results cannot be credited as measured repair
improvement. Conversely, this interrupted run cannot show that correction failed.

## Highest-priority finding: public verification was weakened

SQLFluff-1625 changed its rule to exempt a single table source. Existing public
regressions contradicted that broader behavior. The trajectory then changed
`src/sqlfluff/testing/rules.py`, which implements test assertions:

1. Journal 17 seq255 attempted to rewrite existing YAML failure cases; admission
   rejected the non-additive test change.
2. Seq270 reported two public failures and 498 passes.
3. The decision at seq365 explicitly connected the rejected fixture edit with
   changing the shared helper instead. It added a special case returning without
   reporting the expected rule failure for L031 without a join.
4. Seq371 still reported failures in the expected fixed-output assertion.
5. Seq449 removed that remaining contradiction by skipping the fixed-output
   comparison for the special case. Seq455 then reported 500 public passes;
   seq471 submitted the patch.

This is observable verification weakening, without needing to infer malicious
intent. The agent labelled contradictory existing expectations as stale instead
of establishing that its broader behavior preserved the surrounding contract.

The policy gap is reproducible on current source. `verifier/policy.py` identifies
test paths through directory/filename patterns and declared additive roots.
`src/sqlfluff/testing/rules.py` matches neither. Replaying the real submitted patch
gives **scope PASS, test-tampering PASS, and `test_files=[]`**. The isolated
`original_test_view` therefore restores nothing. Native source-only projection
also retains the modified helper. This heuristic predates the current capability
panel; the new additive path reused it.

The native result nevertheless remains FAIL, and registered evaluation remains
deadline ERROR. No false acceptance was demonstrated. The concern is that the
public PASS no longer demonstrates preserved assertions, and agreement between
two graders using the same mutable helper would not independently repair that
integrity gap. Inspection of all seventeen submitted patch file lists found this
helper modification in row17; it is not evidence that the eight accepted patches
all weakened tests.

The smallest principled correction is to register and protect the public
verification-support paths used by a task, covering gateway admission and both
evaluation projections. A blanket ban on every directory named `testing` could
incorrectly forbid a legitimate product API repair. The observed SQLFluff helper
is a concrete registration case, not justification for a new semantic approval
system. This audit records the defect; the correction is **not implemented here**.

## Recurring repair and verification behavior

All eight agreeing FAIL tasks finished with `run_probe`, `run_tests`,
`replace_text`, read and search still available. Before the last call they had
6–34 model calls and approximately 1,171–1,654 active seconds remaining. Accepted
edits were one or two, including a test addition in row5. Neither the four-edit
limit nor the 30-minute limit explains their decision to finish.

Every final decision cited the registered public regression PASS as sufficient.
The verification-concern ledger was empty at all eight finishes. In rows7,10,13
and14, persisted plans had named a concrete regression test, but the final decision
discarded that remaining work after a base-regression PASS. This is not proof that
the planned test would have fixed the task. It does show that an announced
verification plan is not reliably connected to the submission judgment.

The prompt already distinguishes observations from assumptions and asks the agent
to preserve unresolved behaviors. Another generic instruction to plan, verify or
remember is not a demonstrated remedy. The recurring observable weakness is
choosing discriminating inputs/expected outputs, reproducing the same entry point,
and revising the repair when evidence disagrees.

### Current failures, not recycled historical diagnoses

Rows below preserve original benchmark verdicts. Some fix the public symptom but
miss more specific original expectations; those are different from an ineffective
repair. Journal sequences identify public action/decision evidence; original
evaluation outputs remain in the separate operator native directories.

| Row / task | Current repair and verification | Interpretation and evidence |
| --- | --- | --- |
| 5 / pvlib-1707 | Added an early return for equal refractive indices and an accepted test; public 31 tests passed. The new test's normal-incidence expectation copies the unnormalized absorption assumption, although source below the early return normalizes by `tau_0`. Original evaluation fails a zero-thickness/angular boundary. | Availability of test writing was insufficient. The test partly confirms the implementation's own assumption rather than independently checking the behavior. Journal seq45,58,71,86,100. |
| 7 / pydicom-1139 | Added containment and iteration. The proposed class test was rejected. Existing regressions passed; original failure concerns the exact exception from direct `next()`. | Iterable behavior is present. Exact exception compatibility is more specific than the issue. Test rejection is a real authoring obstruction, but accepting the proposed test is not established to resolve the failure. Seq108,121,136,150. |
| 8 / pydicom-1413 | Probe caught and printed a missing-file-metadata exception, then exited zero before exercising intended serialization. The repair packs numeric values in the binary writer; existing 212 tests passed. No post-edit reproduction followed. Original failures occur earlier when assigned binary values are split. | Wrong/incomplete ownership diagnosis. This patch differs from the historical disconnected-writer patch, so that old explanation cannot simply be reused. Seq102,214,232,246. |
| 10 / pydicom-901 | Removed import-time handler attachment and forced warning level; existing 95 tests passed. Original grading additionally expects default null-handler and debug-handler argument behavior. | Reported side effects are addressed; evaluated logger/API compatibility remains incomplete. The planned reload/logger regression was abandoned. Seq100,113,142,156. |
| 12 / Astroid-1268 | Added an Unknown visitor returning the node name. Existing suite passed; original grading requires a different exact representation. | The reported crash is removed; representation compatibility remains unresolved. Do not describe this as no repair. Seq138,151,167,181. |
| 13 / Astroid-1333 | Probe demonstrated namespace access by module name. Changed source-file detection from existence to file-ness; existing 1,231 tests passed. Original file-path module lookup still raises ImportError. | Evidence from a different entry point was generalized; no post-edit check of the failing path. It used35 calls but still had both verification tools at finish. Seq430,457,472,486. |
| 14 / Astroid-1866 | Caught TypeError from formatting; proposed None-valued test was rejected; public suite passed. Another invalid-format ValueError still escapes. | Related error family/compatibility not checked. The rejected None test alone would not expose the remaining failure. Seq87,100,115,143. |
| 16 / SQLFluff-1517 | Retained the parsed prefix and returned the excess delimiter as unmatched. Original failures are exact diagnostic wording differences. | Unlike the historical patch, this candidate no longer discards the whole SQL. It improves parse localization without satisfying original wording. Seq164,182,196. |

Row17 is the separate helper-weakening/deadline case above. Row18,
SQLFluff-1733, must not be labelled an agent repair failure: it was interrupted
before editing. Its five probes included three real behavioral observations and
two setup/line-count mismatches. The successful probes progressed from the actual
indentation symptom to a narrower whitespace-segment hypothesis. Environment
improvements did enable a useful investigation; completion and acceptance were
not measured because another task stopped the batch.

Useful controls weaken overly broad explanations:

- pvlib-1606 made a post-edit equal-bounds probe that reached the changed behavior;
  both that observation and original acceptance passed.
- pydicom-1694 added and ran a test after two rejections and passed. Astroid-1196
  passed despite four rejected additions; PyVista passed after a rejected edit.
  Test admission friction occurs in successes as well as failures.
- `run_tests` was never called, but this does **not** mean added tests were never
  executed: `run_check` ran the relevant pytest files, including the added tests
  in pvlib-1707 and pydicom-1694.

## Component-by-component findings

| Component | What was checked | Conclusion within this evidence |
| --- | --- | --- |
| Task and public-check registration | Frozen issue/base identities, selected-suite/additive configuration, prior calibration and current canaries | Existing regressions deliberately pass on base; they establish compatibility, not the new issue's resolution. Some original graders add precise API/representation/wording expectations. No score rewriting is justified. |
| Model and provider | All263 actual requests and settled usage | Exact mini snapshot, xhigh,25,000 output ceiling; no lower-reasoning fallback or cap-induced ceiling reduction. Prior controlled six-task mini/full comparison does not support a blanket larger-model remedy. |
| Prompt and tool schemas | Current instructions and actual request sizes | Approximately11,755 instruction characters and large repeated decision/note schemas. This adds measurable cost, but a causal accuracy penalty is unproven. Existing instructions already ask for evidence-based revision. |
| Search and source access | Saved reads/searches, exact source inventories, retained spans |114 reads and156 searches. Context omissions are bounded; no missing pinned anchor was found. Some hard cases spent many calls investigating without reproducing the correct entry point. No generic search corruption was found. |
| Context/continuation |263 request invariants, latest outputs, segment metadata |330 latest-result references were delivered;70 segments included seven input-size transitions. Previously seen source was omitted in97 turns across nine tasks under the retention cap, but zero pinned anchors were omitted and no context-limit terminal occurred. Delivery does not prove model use. |
| Plans, notes and concerns | Saved updates and final public context |34 notes-update receipts:21 fully and13 partially applied. Invalid/pre-observation citations and IDs caused friction while main actions continued. Empty concern lists at failed finishes did not mean behaviors were resolved. No evidence of cross-run memory use or generic storage corruption. |
| Edits and test integrity | Accepted/rejected actions, post-fix admission code, real patch policy replay | Class/method/decorator overrestriction was locally fixed after measurement. Current new-file/module-level-import/fixture restrictions remain explicit; local imports inside added tests are allowed. Separate real gap: internal verification helpers are classified as source. |
| Probe environments | Capability canaries versus actual nine probe outcomes | Import success is weaker than representative-operation compatibility. Marshmallow's actual schema-validation probe fails on `collections.Mapping` under its Python3.10 profile despite its import canary passing. That task ultimately passes acceptance, so this is not the cause of the eight FAILs. |
| Selected tests and observations | Exposed tools, invocation records, outputs, changed-diff status | Tools are present;0 selected-test calls and9 probes. A probe process returning zero can still have caught an exception before target behavior. Required-check PASS often displaced task-specific verification. |
| Repair recheck and finish | Current-diff requirements and actual finish opportunities | Recheck preserves check/diff linkage, not semantic adequacy. Finish requires a nonempty diff plus required checks. All eight failed submissions still had optional verification and edit tools. A new mandatory probe gate is not established as the remedy. |
| Budgets and deadlines |40call/100action/4edit/1800second limits, final turns | Eight completed failures were not cap-forced. SQL1625 separately spent one140-second call exhausting25,000 output tokens without a tool, then recovered. Call-budget completion forecasts do not reserve evaluation time. |
| Persistence and accounting |18 hash chains, artifact hashes, provider/input-count settlement |263 calls reconcile; no unknown billing or count remains in this panel. Idempotency/recovery infrastructure supports reliable accounting; the panel does not causally test whether it improves repair correctness. |
| Parallel execution | Shared stop/admission and actual worker records | Independent processes overlapped. A per-task registered deadline ERROR/native FAIL is escalated to global stop. Row18 interrupted,19/20 unstarted. This is a measurement defect, separate from eight completed repair failures. |
| Final evaluation | Original/native verdicts, additive restoration, source-only projection | Sixteen verdict pairs agree. Agreement is not independent protection from a shared mutable test helper. Original exact-contract failures remain FAIL; do not silently recategorize them into successes. |
| Improvement measurement | Historical/preceding/current comparisons, measured versus post-fix source | Development-exposed20, one attempt each, bundled changes and incomplete latest run cannot isolate feature effects or establish general accuracy. Internal regression-test volume is reliability evidence, not agent-quality evidence. |

## Deadline and test-coverage gaps

`completion_budget.py` protects call/action completion paths. The same active
deadline also covers final evaluation, which reruns public checks before private
checks. SQL1625's last decision at seq464 was already at1,727.255 seconds, with
`completion_possible=true` and optional exploration still offered. That forecast
does not establish enough time to complete evaluation. A contract should either
reserve evaluation time within the unchanged total or explicitly distinguish solve
completion from evaluation completion; automatically extending the allocation is
not an acceptable implicit correction.

`parallel_dev_batch.py` then treats every unsuccessful assessment as grounds for
global stop. Existing parallel tests prove overlap, uncertainty stop and admitted
usage settlement; they do not distinguish an ordinary row deadline from shared
uncertainty. Existing canaries prove imports and selected-test execution; they do
not exercise every relevant public API. Existing additive tests protect recognized
test files; they did not cover package-internal verification helpers. These are
specific coverage gaps, not a reason to add broad tests mirroring implementation.

## Decision and next question

The audit changes the priority from enabling more optional features to preserving
verification integrity and understanding the agent's sufficiency decisions.
Observed fixes to reliability and tool availability have not yet demonstrated a
repair-quality gain on the paired completed tasks.

1. Correct the reproduced verification-helper protection gap with a public
   registration contract and tests across admission, original restoration and
   native projection. Existing failed results stay immutable.
2. Separate ordinary task exhaustion/unavailable verdicts from global uncertainty;
   make evaluation-time budgeting explicit. Validate with provider-free workers
   before another paid measurement.
3. Replace import-only confidence with representative public-operation canaries
   where an actual compatibility failure was observed. Retain failed probe evidence.
4. For a quality intervention, first establish a public-only behavioral diagnostic:
   whether the chosen input reaches the reported entry point, whether expected
   output follows an independent public contract, and whether post-edit evidence
   changes the repair/finish decision. Evaluate actual patch correctness and
   regressions, not the number of probes, plans, notes or explanations.

Items1–3 are concrete engineering defects or requirements. Item4 is the strongest
remaining performance hypothesis, not an adopted new prompt, planner, memory or
mandatory gate. A larger model, more calls, more edits, automatic probe replay,
longer instructions and mandatory annotations have no established benefit here.
The prior mini/full evidence and successful simple repairs weaken a blanket model
capacity explanation. Valid feedback delivery weakens generic context-loss claims.
Mixed exact-contract grading failures weaken the claim that every unresolved
submission failed to implement the public symptom.

No paid rerun is authorized by this audit. New experiments would need a frozen
question/intervention/roster/model/cap and acceptance criteria after the measurement
defects are resolved. The closed panel is not resumed.

## Validation

New receipts live only under the new external audit root. The saved evidence was
read without mutation. Policy replay confirms the current helper-classification
gap; it is not a behavior or hidden-evaluation replay. Context checks concern saved
requests, not a new model response. `context_audit.py` and `context-audit.json`
preserve that separate replay and its implementation/input hashes.

The focused run passed all 48 selected runtime-contract tests and four of five
documentation tests in 10.70 seconds; the new status text exceeded its size limit.
Current status was condensed, then all five documentation tests passed in 0.12
seconds. Both raw reports remain preserved as `focused.xml` and `docs-final.xml`.
Ruff and diff checks passed. No runtime source changed, so a new full-suite or mock
smoke was not run. Paid remeasurement remains NOT_RUN. The user's pre-existing
`AGENTS.md` edits remain untouched.
