# Why seven assessment runs finished after public PASS

Date: 2026-10-16. Offline follow-up to the closed
[comparison](2026-10-16-submission-assessment-results.md). No provider, probe, test
candidate or evaluator execution was added. Runtime and frozen evidence are unchanged.
All underlying runs are development-exposed, `official=false` and claim-ineligible.

## Question and method

Seven of eight B runs supplied an assessment and made no further external inspection,
verification or edit after their first healthy current-diff required PASS. The user
asked why, using the actual prompts and actions rather than another paid experiment.
This matters because a readiness explanation can satisfy the new contract without
changing a previously insufficient completion decision.

Read each run's hash-chained public journal, the saved `model_input_prepared` request
that produced finish, and its recorded public `turn_decision` and assessment. Verified
the request artifact's SHA256, canonical request hash and matching provider dispatch.
Compared public task/check definitions, pre-PASS plans and verification, retained
context, offered tools and budgets. B2-19 is a contrast case, not an extra treatment.
No private test, reference patch or grader-detail artifact was read. Public decisions
are model-authored declarations, not internal reasoning or proof of semantic coverage.

## What the model actually received

All seven final requests contained the B system instruction:

> After required checks pass, review the public requirements, current patch, evidence
> and remaining uncertainties. Call finish_task only if you judge the task complete;
> its assessment must explain why the repair is ready and any verification limits.
> If more work is needed, continue. After an edit, require fresh checks and reassess.
> This judgment needs no separate call or mandatory experiment.

The current state also said:

> Use run_probe if a concrete remaining public uncertainty could change the decision.
> No extra experiment is required.

The delivered finish description explicitly said `PASS alone is not that judgment`.
Thus the new review instruction was present; the old automatic-finish instruction
was not accidentally used. At the same time, `workflow_gate` and completion stage
were `ready_to_submit`, `submission_ready=true`, and `next_action=null`. The model
could finish on the next call if it judged the already available evidence sufficient.
This is the requested judgment contract, not an implementation requirement to obtain
new evidence. The state label is mechanical eligibility, not a correctness verdict.

The system further warned that intended mutation effects are not check coverage and
that check definitions do not certify execution of every case. Those caveats did not
prevent the stronger completion claims below. All final states included
`recent_checks[0].evidence_review.coverage_status=not_assessed`,
`selection_kind=unresolved` and `declared_targets=[]`. Public changed-line feedback
was `unknown`, which means unmeasured, not unexecuted. The finish schema required a 1-1,500
character assessment; runtime validation required nonblank text, a nonempty tracked
patch and current required PASS. It did not evaluate the explanation's sufficiency.
Relevant implementation: [system prompt](../../patchloop/dev/model.py),
[completion guidance](../../patchloop/dev/runner.py),
[finish schema and execution](../../patchloop/dev/tools.py),
[assessment contract](../../patchloop/dev/contracts.py). These paths have no changes
between frozen B `a18976699ed16533516b4347df935e0dea51d161` and analysis HEAD
`9dde12a8192117935b9e98cb3ddd25f0164681b5`.

All seven received `working_plan.review_request.requested=true`, including
`check_result` and `first_ready_to_submit`. Six finished with `plan_update=null`;
B2-10 explicitly marked its plan complete. None had an explicit verification concern
registered. This does not mean no uncertainty was mentioned in ordinary prose, or
that the model did not think. It means no additional external action was chosen.

## Seven trajectories

Sequences below are one-based journal sequences. Every row has exactly one new
model response after first PASS, selecting finish. First-PASS and final patches are
identical. No row ran a separate `run_tests` action.

| Run | Verification before first PASS | Recorded completion decision and remaining gap | PASS / decision / finish |
| --- | --- | --- | --- |
| B1-7, pydicom-1139 | Baseline probe reproduced membership TypeError (79); added `__contains__` and a Dataset.PatientName positive/negative membership test (134); 39 tests passed. | Targeted membership behavior had been tested. Assessment treated broader PN string/iteration behavior as outside that tested path. The public title asks for iterable behavior; this repair concentrated on the membership example. No broken promise to add that membership test. | 148 / 159 / 164 |
| B1-10, pydicom-901 | Initial plans promised a direct logger-state regression test (13, 31), but only config.py was edited. Plan changed to regression PASS implies ready (118); 95 passed, 1 skipped. | Source inspection plus suite PASS was deemed sufficient. Assessment expressly admits no targeted logging probe. The earlier direct-test plan was dropped. | 122 / 133 / 137 |
| B1-13, astroid-1333 | Initial targeted test was conditional (13); namespace-detection edit and typo correction, with no probe or new test. Plan says PASS implies ready (189); 1,231 passed, 69 skipped, 15 xfailed. | Assessment calls PASS an `end-to-end confirmation` that the targeted failure disappeared. No issue-specific `pylint src/project` reproduction or added targeted test supports that claim. | 193 / 204 / 208 |
| B1-19, sqlfluff-1763 | Initial Unicode/file-preservation probe was conditional (13). Later plan asks only for regression verification (45). Added `errors="backslashreplace"`; 146 passed. | Assessment says encoding failure and truncation are addressed while admitting no targeted reproduction. No direct observation established original-file preservation for the reported failure scenario. | 159 / 170 / 174 |
| B2-7, pydicom-1139 | Baseline probe reproduced iteration and membership TypeErrors (80); added `__iter__`, `__contains__` and list/membership tests (124); 39 tests passed. | The promised direct regression test was completed. Assessment treats broader downstream behavior as untested, without a concrete remaining blocker. | 138 / 149 / 153 |
| B2-10, pydicom-901 | Tried adding a fresh-import logger test; mutation rejected (120) because it changed existing top-level imports. Plan then made another test conditional on suite results (130); 95 passed, 1 skipped. | No compliant rewrite or probe substitute followed. Assessment admits no dedicated logger-state test, but says source side effects are removed; final plan explicitly marks work complete. | 135 / 146 / 150 |
| B2-13, astroid-1333 | Plan explicitly promised a namespace lint/module-loading regression test (376), and searches sought a suitable test pattern. Only modutils.py was edited. Check basis deferred follow-up-test choice until after results (480); 1,231 passed, 69 skipped, 15 xfailed. | Final basis says `no unresolved public uncertainty remains`, while assessment acknowledges untested namespace edge cases. The promised test was not added; its absence did not block submission. | 484 / 495 / 499 |

The public check scopes matter. Task 7 runs `pydicom/tests/test_valuerep.py`, including
the added tests. Task 10 runs only `test_misc.py` and `test_dataset.py`, not the whole
`pydicom/tests` tree as B1-10's assessment loosely describes. Task 13 runs `tests/`.
Task 19 runs `test/cli` and `test/core/linter_test.py`. A broad suite PASS establishes
those assertions passing; without a target-specific observation, it does not by
itself establish the reported failure is repaired. This analysis does not assert
that every unexecuted probe would have found the independent-evaluation failure.

B2-10's rejection was a real local friction point, not a global inability to verify.
The rejection explained how to preserve existing tests/imports/helpers and add a new
test function; `run_probe`, `run_tests` and further edits remained offered at finish.
It explains an abandoned route in that row, not the other six exits.

## Why B2-19 continued

Before first PASS, B2-19 had a concrete unresolved question: successful encoding
round trips do not test whether failed encoding preserves the original file. At
decision 285 (mutation action 289), it recorded that concern and planned a failure-path
probe or regression test. Automatic recheck PASS 295 did not answer the question.
The next request (297, dispatched 302) still contained concern `v1`. Decision 304
selected the probe; result 309 observed `False` and the original `SELECT 1\n` file
contents preserved. Finish followed at 323 without another edit.

This contrast supports the narrower mechanism that a concrete, still-open behavior
question can survive regression PASS and lead to another action. It does not show
that concern bookkeeping caused the action or that the new assessment instruction
created the question: both the question and plan existed before PASS. Independent
acceptance still failed, so another check alone is not evidence of a sufficient repair.

## Alternatives and interpretation

- **Instruction missing or automatic finish:** contradicted. All seven received the
  review requirement and made a new model-selected finish call after PASS.
- **Tools or resources forced finish:** contradicted. All had read/search, replace,
  probe, selected tests, finish and stop tools. `tool_choice=required` required a tool,
  not finish specifically. Exploration was open, closure reason null, no tools were
  projected to close after one unchanged inspection, and further mutation completion
  was feasible. Remaining resources were 7-32 model calls, 2-3 edits, 46-86 actions,
  USD 0.60465270-1.05986355 and conservatively 1,105-1,371 solver seconds. Current
  required checks were already satisfied; absence of `run_check` was not absence of
  optional tests/probes. These are dispatch-state observations, not hypothetical
  provider availability guarantees.
- **Loss of all relevant context:** not supported as a common explanation. All had
  the public issue/check definitions, full untruncated current patch and current PASS.
  Five omitted zero observed source lines; B1-13 omitted 21 and B2-13 omitted 677.
  Source loss could affect individual judgments, but does not explain the common
  seven-run pattern. B2-13's unfulfilled test plan was still in its final input.
  All seven crossed a `major_result_reviewed` segment handoff with
  `previous_reasoning_available=false`; retaining source is not retaining all prior
  context. B2-19 also had this handoff when it chose the probe, so handoff alone is
  not a demonstrated explanation for immediate finish.
- **Existing verification judged sufficient, with gaps treated as tolerable limits:**
  directly supported by the recorded plans, bases and assessments. Two rows completed
  their direct-test plans; other rows dropped, conditioned or abandoned direct checks.
  Several converted regression success and source plausibility into stronger repair
  claims. Merely naming an unverified limit did not make it a reason to continue.

The observed behavior is therefore consistent with assessment becoming a declaration
of the existing completion judgment. The contract added an explicit judgment but did
not establish a stronger standard for deciding which public requirement/evidence gaps
must remain open. The prompt's `No extra experiment is required` and mechanical
`ready_to_submit` state permit this path; their individual causal effects cannot be
isolated from these logs. Nor can these logs establish absence or quality of internal
deliberation.

The decision from this investigation is to retain the measured result and identify
requirement-to-evidence sufficiency, including abandoned direct-test plans, as the
concrete unresolved mechanism. No forced probe count, new gate, prompt change or paid
comparison is adopted here. A future proposal needs to address that mechanism and
state what observation would disconfirm it. The seven exits are not all invalid
processes, and the known independent FAIL outcomes do not disclose their exact causes.

## Evidence index

Original row roots are `C:/pt/assesscmp16live01/<row>/`. Journals are under
`runs/<run_id>.jsonl`. Each input below is the saved request that selected finish.
CAS path is `artifacts/objects/sha256/<first two hash characters>/<remaining characters>`.

| Row | Run ID suffix after `run_dev_` | Input / provider dispatch | Input SHA256 |
| --- | --- | --- | --- |
| B1-7 | 316f81274e164c65 | 152 / 157 | ebed3eb913f433b63baf9642ec90808d2fd21aeac0128baf7acee42061047a83 |
| B1-10 | 583eebf00d2f4942 | 126 / 131 | e48d549c6f8c99a323f7bf506767fb072a78ae3741e8a9fd5c27e3b43bcf10da |
| B1-13 | c396736ce1574d15 | 197 / 202 | 59967604723e725f837663fb507d6babff6247bd7a84f56468473f94ddb9b4b9 |
| B1-19 | d95c98fc828d4deb | 163 / 168 | 9b23b238646fb8d360ff9d4ef43bb32630230eb46d1dbf18c124ac363f55eed3 |
| B2-7 | b35b7283350c41f1 | 142 / 147 | 651d27d75d131d5c661e82a00559b08c3c20ec5a51278c26faecec9584f12499 |
| B2-10 | 54bd1fc5163f4134 | 139 / 144 | 8bdabbba35b4d0f75a9fa23f605e29c411d26df9df0ebae2605f81087b94b31e |
| B2-13 | bfc3ad55366d4c96 | 488 / 493 | 363eb17a3c4a9147c97de997afe333744b3ad0349179059f57e3b25b1096d413 |

Contrast B2-19 is `run_dev_481902d63bc647af`; its post-PASS probe-selecting request
at 297 is `sha256:119a7def8135984130d7e84c2500b8a89137ca08d264901dbcca4e9decf1f00b`.
New offline extraction is `C:/pt/assesscmp16analysis01/public-evidence-v2.json`,
`sha256:57055263ac5f40c4380e541642eda556df7f9b5e7f53ef820a27867ab5bf989f`, bound with
extractor/source hashes in `runs/run_dev_assessmentexitanalysis.jsonl`. JSON locations:
`rows[].post_pass_requests[].system_prompts`, `tools`, `state`, `tool_calls`,
`rows[].actions`, and `public_check_results`. Only public messages/tool calls were
extracted; no provider reasoning/continuation content was read.

The first extraction's dispatch lookup used the wrong event name and returned empty
indexes. It is preserved separately; v2 uses `provider_call_started` and asserts one
matching dispatch per request. This report correction made no solver/evaluator call
and changed none of the source artifacts or original comparison conclusions.

Validation: documentation-layout checks 5 PASS and `git diff --check` passed.
An independent public-payload review found no material evidence mismatch. No runtime
code changed; runtime suite, mock smoke and live checks were not rerun for this
documentation-only analysis.
