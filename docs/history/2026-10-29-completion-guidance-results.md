# Completion guidance A/B: both observed failure, neither repaired

Status: CLOSED. Official=false, claim-ineligible; one continuation per condition
on an exposed development checkpoint. The original dev20 score remains 10/20.

## Question and execution authority

The [preparation](2026-10-29-completion-guidance-preparation.md) held the public
helper replay fixed and changed only completion guidance: A retained the existing
prompt; B distinguished submission eligibility from whether further diagnosis or
repair was warranted. The preceding comparison had delivered the observation but
both arms submitted unchanged. This experiment tested the decision after delivery,
without another gate, private hint, budget increase or ordinary-runtime change.

The user authorized the exact command and fresh USD6.795082 cap, USD3.397541 per
arm, A then B once, with no transfer or retry. Both completed under that authority.

- Command: `& 'C:/pt/completion-guidance-plan-v1/run.ps1'`.
- Manifest: `C:/pt/completion-guidance-plan-v1/manifest.json`,
  `sha256:9f30758c5de15a1a99b2e637ca96496e1be2356c151e5ce04b78259ef2b53cd4`.
- Result: `C:/pt/completion-guidance-run-v1/result.json`.
- Task: Astroid-1333, dev-train current-dev20/13; parent
  `run_dev_aecd56b8decc47ff`, prefix through sequence 213.
- Model: gpt-5.4-2026-03-05/xhigh; credentials
  `C:/Users/geonj/Documents/PatchLoop/.env`.
- Same public-checks-v1/thin/segmented-v1/completion-recovery-v1, six remaining
  responses including at most one correction, 14 actions, two edits, approximately
  1,648 solver seconds plus 390 for evaluation; input60K/output40K/correction25K.
- Implementation `a3145422`, execution HEAD `3b48a1b8`; ordinary runtime remained
  `sha256:c9fd20d950163c453aea27e0d050fcc19f40b92a76c4338ffffd900ffd8c4169`.

Both received the same sealed helper receipt and were charged its one action and
11.198 seconds. This attachment was not a new physical helper execution. No
operator diagnosis, separate CLI result, hidden test, reference patch or private
evaluation log reached the repair model. Each arm independently authored its new
caller probe during this continuation.

## Outcomes

| Outcome | A: existing guidance | B: investigation guidance |
| --- | --- | --- |
| New model responses | 2 | 4 |
| New selected actions | run_probe, finish_task | read_file twice, run_probe, stop_task |
| New accepted edits | 0 | 0 |
| Current caller observation | F0010 persists | F0010 persists |
| Public required check | inherited same-diff PASS | inherited same-diff PASS |
| Submission | unverified_delivery | not submitted |
| Original SWE-bench acceptance | FAIL | NOT_RUN |
| Evaluator safety | PASS | NOT_RUN |
| New input/output tokens | 36,509 / 7,784 | 75,879 / 6,213 |
| New cost, USD | 0.1625285 | 0.2535165 |
| Charged additional solver active time | 135.304 s | 120.826 s |

Charged solver deltas include the reused 11.198-second observation. Actual new
solver deltas were 124.106 and 109.628 seconds. A's evaluation added 20.160 seconds;
B did not invoke evaluation. No new public regression check ran because neither
arm edited. Existing base-regression PASS refers to the unchanged candidate,
not confirmation that F0010 disappeared.

The candidate remained
`sha256:1ac127d0b6c304ac53f23ba4724953b59e25e665926f2b00bae9253af9d6ad57`.
A submitted it; B abandoned it. Total new cost was **USD0.416045**, all six input
counts, responses and usage records settled. There was no incomplete response,
output exhaustion, transport/billing uncertainty, retry or extra paid run. No
running Docker container remained at the final check.

## Public behavior evidence

Sequence references use each arm's
`<result-root>/<A-or-B>/runs/run_dev_aecd56b8decc47ff.jsonl`.

A selected a new helper at 233/236. It called pylint 2.12.2 on `src/project`
without a project initializer and compared a present-initializer control. At 239,
the missing case produced status 1 and F0010; the control produced status 20 with
C0114/W0611 and no F0010. The helper completed with exit 0, full 1,875-byte capture
and confirmed cleanup in 9.360 seconds. Helper exit 0 is execution completion,
not repair success. Both cases ran sequentially in one process; changed-line
coverage is aggregate and is not a separately isolated attribution for each case.

A's finish at 249/252/253 explicitly acknowledged that F0010 remained and repair
was not established. Before that response, five calls, 13 actions, two edits,
USD3.311043 and 1,572 solver seconds remained; edit/read/search/probe were offered.
Immediate resource exhaustion or absent tools therefore does not explain A's
unchanged submission. Its public assessment does not establish its internal cause.
Solver finish was 257, evaluation 260 and terminal 261.

B read two different regions of `astroid/modutils.py`: lines 600-650 at 239/240,
then 160-260 at 254/255. These were not identical read requests: the first added no
new tracked coverage, while the second added 35 editable/public lines. It then selected a
caller probe at 264/268, asking whether the actual pylint caller still emitted
F0010 or whether the mismatch was limited to lower-level expansion. The completed
probe at 271 captured 853 bytes in 7.719 seconds with confirmed cleanup, including
F0010 for `src/project/__init__.py` and no W0611. W0611 absence alone does not prove
that `file.py` was never processed; the stop assessment's stronger statement was
not separately traced. At 280/283/284, B stopped with
`no_safe_scoped_mutation`, citing the remaining failure and absent edit action.

The missing edit action was real: transition 278 removed `replace_text`, leaving
finish, probe, tests and stop. At the preceding request, an edit was still offered.
At 261, four total responses minus one unused protocol-correction reservation left
three ordinary responses, enough for edit/check/finish. After the probe, 277 had
three total responses minus that reservation, leaving two against a three-response
minimum. Two edit slots, 11 actions, USD3.2118395 and 1,551 solver seconds still
remained. `runner.py` computes ordinary capacity by reserving the correction call
and then compares that capacity with the mutation minimum. This was the actual
tool-removal condition, not an exhausted mutation count or missing editable source.

Source loss is contradicted by the actual dispatched requests: the second request
(collector 19, arm turn 248) preserved the first read's complete output in
`latest_tool_results`. The final request (collector 27, arm turn 277) retained the
second read's 2,681-character source body in a native `function_call_output`.
`source_retrieval.source_bodies_delivered=false` describes a narrower summary field;
it is not proof that source is absent from the whole request.

Before the probe, the request did expose total calls 4, correction reserve 1 and
mutation minimum 3. However, it did not forecast that choosing a probe would remove
edit eligibility next turn. `tools_closing_after_this_turn` was empty; its prediction
basis covers a read/search. The probe route used `legacy_forecast` with
`model_calls=null`, without successor edit feasibility. Afterward the exclusion
message was `current_state_or_budget`, and transition reason `evidence_changed`,
rather than the specific response-reservation constraint. The budget arithmetic
was inferable, but the action-specific consequence and subsequent explanation were
not explicit. This is a bounded guidance/forecast gap, not proof that removing the
correction reserve would produce a correct repair.

## Delivery, accounting and evidence limits

The actual first counted/dispatched requests matched the sealed normalized hashes:

- A: `sha256:fcd890c96a348249ddeb7371744d974b4a802481ffcd0bc597b65ee2988cfaf7`.
- B: `sha256:9cfb20fe7c8557ac9e5910c79eeac3fd2aea177b8c82a9be6890d117c40c6f45`.

After reverting only B's selected prompt and normalizing existing elapsed-time
and segment-identity fields, whole-request equality passed. All six real
count/dispatch artifact hashes matched. Both branch journal chains validated,
pending count/provider calls were absent, and provider-usage failure checks were
clear. The operator audit is preserved in
`C:/pt/completion-guidance-run-v1/runs/run_dev_completionguidanceaudit.jsonl`.
A's evaluator receipt records `agent_context_reinjected=false`; private logs were
not used for this behavioral diagnosis.

Preparation's focused 30 tests, Ruff, quick suite and isolated mock evaluation
passed before dispatch. These establish mechanism readiness, not model repair
quality. Post-run validation covers result accounting, identities and documentation.

## Decision and next question

Both arms went beyond the delivered lower-level helper and independently observed
the remaining public failure, yet neither repaired it. B's truthful abandonment
does not establish better task performance; A's successful submission does not
establish correctness. No default prompt adoption is supported.

The previous baseline with the same replay ended immediately, whereas this new A
ran a relevant probe. That variation under the same guidance, together with one
trajectory per arm, prevents attributing the different actions or stop decision
confidently to the added paragraph. This result does not support a general replay,
guidance or model-quality claim.

Keep the existing public-check submission criterion and ordinary runtime. The
next local question is whether the same completion-path calculation can describe
probe/read/edit successor feasibility and the exact reason an edit is unavailable.
Use the saved pre-probe state to verify ordinary response capacity and next-edit
availability without a provider call. Probe remains permissible under the current
probe/finish path; no rule promised a repair after every probe. Probe prohibition,
correction-reserve release and budget expansion are separate policy choices, not
automatic fixes justified by this pair. A live repair benefit remains unproven.
This allocation is closed; unused funds authorize no further experiment.
