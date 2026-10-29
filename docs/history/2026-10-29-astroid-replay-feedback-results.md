# Astroid checkpoint replay-feedback A/B: both submitted unchanged and failed

Status: CLOSED. Official=false, claim-ineligible; exposed dev-train checkpoint,
not fresh-task performance. The original dev20 score remains 10/20.

## Question, intervention and authority

The [preparation](2026-10-29-astroid-replay-feedback-preparation.md) tested whether
current-candidate output from the model's own helper changes its repair decision,
after the [pilot](2026-10-29-dev20-followup-pilot-results.md) offered replay but the
agent submitted without it. The public operator diagnosis was excluded from the
repair model. The user authorized the exact v2 command and USD6.795082 allocation,
one A and one B continuation, USD3.397541 each with no transfer or retry.

- Manifest: `C:/pt/astroid-replay-feedback-plan-v2/manifest.json`, hash
  `sha256:bc9b091f9952b86f7fa5a0cbda45d85257c90848b04a8e103684624faa8d06d2`.
- Command: `& 'C:/pt/astroid-replay-feedback-plan-v2/run.ps1'`.
- Results: `C:/pt/astroid-replay-feedback-run-v2/result.json`.
- Shared source: parent `run_dev_aecd56b8decc47ff`, prefix through sequence 213;
  Astroid-1333/current-dev20/13, gpt-5.4-2026-03-05/xhigh,
  `C:/Users/geonj/Documents/PatchLoop/.env`, public-checks-v1/thin/segmented-v1,
  completion-recovery-v1, probe policy none, input60K/output40K/correction25K.
- Runtime remained `sha256:c9fd20d950163c453aea27e0d050fcc19f40b92a76c4338ffffd900ffd8c4169`;
  diagnostic implementation `9ce5c991`, execution HEAD `96ab618e` (documentation only
  after implementation). No conditions changed between arms.

A retained the ordinary optional replay request. B received a current-diff replay
collected once during preparation: one tool action and 11.198 seconds charged to B.
It reused the immutable receipt, not a second target execution. No operator
root-cause text, separate CLI F0010 result, trace, hidden test, reference patch or
private evaluator log was injected. Existing automatic public changed-line
observations are part of the helper receipt and were retained unchanged.

## Results

| Outcome | A: optional replay | B: replay receipt delivered |
| --- | --- | --- |
| New model responses | 1 | 1 |
| Model-selected action | finish_task | finish_task |
| New reads/searches/edits/tests/model-selected probes | 0 | 0 |
| Public required checks | same-diff inherited PASS | same-diff inherited PASS |
| Submission | succeeded, unverified_delivery | succeeded, unverified_delivery |
| Original SWE-bench acceptance | FAIL | FAIL |
| Evaluator safety state | PASS | PASS |
| New input/output tokens | 15,907 / 721 | 17,954 / 744 |
| New billed USD | 0.0266785 | 0.039053 |
| Charged additional solver active time | 18.105 s | 28.576 s |

B's solver time includes the 11.198-second prepared replay; its live solver delta
was 17.378 seconds. Evaluation took an additional 20.409 seconds for A and 19.889
seconds for B. Both submitted the identical original candidate:
`sha256:1ac127d0b6c304ac53f23ba4724953b59e25e665926f2b00bae9253af9d6ad57`.
No new public regression check was executed: the inherited PASS was current because
neither arm changed the candidate. Two independent evaluations ran after submission.

Total new cost was **USD0.0657315**, with both provider calls/counts/usage settled,
no incomplete response and no stop uncertainty. No repeat, retry or extra paid
experiment followed. No running Docker container remained at the final check.

## Actual request and behavior evidence

All sequence references below use the arm journal
`<result-root>/<A-or-B>/runs/run_dev_aecd56b8decc47ff.jsonl`, except the collector
records explicitly named. Both restoration primitives use internal projection
label B (identity); this is separate from the experiment's external A/B labels.

A: prepared request 218, count 220, provider dispatch 224, response 225,
finish action 228–229, solver finish 233, evaluator 236, terminal 237.
Preparation independently verified the normalized first request against the parent;
live counting and dispatch used the same current request. `run_probe`, `read_file`,
`search_files`, `replace_text` and `run_tests` were offered alongside finish/stop.
A's assessment acknowledged that it had not replayed the helper after editing.

B: attachment marker 215 and probe receipts 217–220 are reuse of the prepared
execution, not another live model-selected helper run. First actual request 226,
count 227–228, provider dispatch 232, response 233, finish 236–237,
solver finish 241, evaluator 244, terminal 245. Collector count 9 and dispatch 11
reference the same request artifact
`sha256:651333d79c37734b31298f42f69960c210c4bbd2854aa2335776568bfe651281`.
The normalized input matched the sealed preparation. Action/input/candidate,
helper source/snapshot, question, exact stdout/stderr, exit/completeness fields and
public changed-line observation matched the captured execution.

The model view deliberately omits ambiguous raw sandbox `status=passed` and redundant
`replayed_from`; it supplies canonical `execution_status=completed` and
`behavior_verdict=not_assessed`. Do not claim entire raw-result byte identity or a
host semantic failure verdict. The stdout again selected `src/project/__init__.py`
with `errors=[]`. Helper execution completion is not task correctness.

B explicitly acknowledged that unchanged path in its finish assessment. It then
said the helper did not execute the changed lines and therefore did not confirm or
refute the repair, while describing the patch as plausible and regressions as passing.
This is the model's public assessment, not an independently established inference.
The supplied measurement only observed no changed-line entry in the Python launch
thread; other threads, subprocesses and copied source paths were unmeasured.

At B's first request, six responses, 14 tools, two edits, 1,647 solver seconds and
USD3.397541 remained. After submitting, arithmetic residual allowance was five
responses, 13 tools, two edits, 1,631.313 solver seconds and USD3.358488. There was
no output, context, tool or money exhaustion forcing submission. Both evaluators
recorded `agent_context_reinjected=false`; private failure details were not read
for this analysis, and encrypted reasoning was not decoded.

## Decision and remaining question

Supported: the narrow delivery mechanism worked on an actual live request, but
forcing this raw replay once did **not** cause a different next action or repair in
this selected pair. B's unchanged candidate and FAIL do not follow from lost
feedback, unavailable edit/diagnostic tools or immediate resource exhaustion.
Public observation and honest disclosure of uncertainty were insufficient to
produce further repair effort here.

The evidence does not prove a universal failure of replay, the model's internal
motivation, or that the completion prompt caused submission. The helper alone also
does not execute the original pylint CLI/F0010 reproduction. Keep the default
optional replay and existing public-check submission criterion; do not add a global
replay gate or increase context/budget based on this result.

The next focused question is how the completion-stage agent distinguishes
**permission to submit** from **whether further repair is warranted**. The current
completion prompt emphasizes truthful reporting of gaps when finish is offered;
it also says required-check PASS does not establish repair. A plausible explanation
is that the agent treats the remaining mismatch and unobserved modified branch as
a disclosure item rather than a reason to investigate the actual caller path.
Test that interpretation with a small generic completion-guidance change on this
same public evidence, preserving tools, budgets, submission eligibility and grading;
do not inject the operator's root-cause diagnosis. No such intervention or new paid
allocation has been implemented or executed by this result record.
