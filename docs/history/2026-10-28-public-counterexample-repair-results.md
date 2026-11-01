# Public counterexample revision: no new edit, unresolved defects submitted

Material Passport: LIVE_EXECUTED, official=false, claim-ineligible. One approved
operator-assisted saved-checkpoint continuation; allocation CLOSED. No retries or
additional model runs. Public observation delivery, correct repair, submission,
independent acceptance and safety are separate outcomes.

## Question and scope

The [prepared trial](2026-10-28-public-counterexample-repair-plan.md) asked whether
the model would revise a saved candidate after receiving three public path-contract
counterexamples, while preserving the original caller behavior. This follows the
[public base/candidate comparison](2026-10-28-caller-path-contract-results.md), not
inspection of a private evaluator failure.

The user approved manifest
`sha256:aa4f9cc0390ed63ed98bc111af507cebbc4b26cfc281090399fd66eba001c1ba`,
one Astroid-1333 `dev-train current-dev20/13` continuation with
`gpt-5.4-2026-03-05`/`xhigh`, repository `.env`, and fresh cap **USD3.38078870**.
Preparation runtime was `f385692d`; documentation commit at dispatch was
`b7bdaecb`. The original total cap, remaining responses/actions/edits and time were
retained. One action and 35 seconds were reserved for the final public matrix.

## Result

| Outcome | Observation |
| --- | --- |
| New model calls | 6; all counted and settled |
| New ordinary actions | 5 reads, 2 helper probes, 1 finish |
| New accepted edits | **0**; result's total 1 is inherited |
| Submitted candidate | Exact same diff as the saved candidate |
| Original caller and public regression | Same-diff successful receipts reused; no new registered recheck |
| New final public matrix | **FAIL**, 8/11 mandatory cases pass, all three candidate regressions remain |
| Pre-existing empty-path discrepancy | Still FAIL; separately reported, not a new obligation |
| Normal finish/submission | Completed |
| Isolated task acceptance / safety | **FAIL / PASS**, terminal `EVALUATOR_FAIL` |
| New model cost | **USD0.599278**, billing known |
| Remaining fresh allocation | USD2.78151070 CLOSED, not available for another run |

Combined action count was 35: inherited 26, new ordinary 8, and final host check 1.
The new ordinary counted active time was 278.302s; the final public matrix added
6.350s. No protocol correction, output exhaustion or context-limit failure was
recorded. Maximum actual input was 38,577 tokens against 60K; maximum response
output was 5,505 against 40K. These limits did not end the run.

The final failed cases remained `namespace_leaf_explicit`, `split_leaf_forward`
and `split_leaf_reverse`. Submitted diff identity remained
`sha256:141dc0f8e373a23b7379661de8c08b3b0f07c6fa010f2d7bbb8b18b0ed74967f`.
The public matrix ran once after ordinary completion and was not returned to the
model. Private evaluation status was not reinjected; no private details were read.

## What reached the model, and what it did

The counterexample packet was identical in all six actual requests. After the
first response, three successful reads supplied `modutils.py` 474–712,
`unittest_modutils.py` 120–220 and `spec.py` 320–369. The next counted/dispatched
request contained all 13,255 characters exactly once, with matching action/input
hash, source spans and current diff. This live evidence supports the latest-source
delivery repair. The model then read `modutils.py` 300–473 and reread the same
test range. Repetition alone does not identify why it selected that read.

Its first helper temporarily replaced `_spec_from_modpath` to use the existing
fallback only when `context` was present. Direct leaf lookup became `ImportError`
and the parent-root case remained a namespace, but the helper's Pylint example
again produced F0010 without W0611. The wrapper also omitted other normal
postprocessing, so this is not a controlled test of only the `context` condition.
It did not edit the workspace. Its 278-character stdout reached the next request.

The second helper retained the candidate behavior and logged arguments. For the
`project` lookup, Pylint supplied the namespace directory itself twice in the search
path. The helper reported no F0010 but did not report W0611 or selected-file
processing. Its 684-character stdout was captured successfully; however, a fresh
completion segment discarded that output before the next model request. Only
status/exit/timeout/diff summaries survived. Both probes completed and cleaned up;
both were helper diagnostics, not new frozen-original verification credit.

The final public `finish_task.assessment` explicitly acknowledged the current three
counterexamples, the overly broad search-path behavior and incomplete broader
verification. It submitted the original-case-supported candidate with those gaps.
This was not a concealed failure, but it was not a successful repair.

## Response reservations changed which actions were possible

The first five requests offered `replace_text`. Before the second helper, four
responses remained and the mutation completion route was still possible. After
that helper, the final request had three responses left, including an unused
protocol-correction reservation of one. The minimum edit/check/finish route needed
three ordinary responses, leaving only two after the reservation. The host therefore
removed `replace_text`; read/search were already closed. Only `finish_task`,
`stop_task`, `run_probe` and `run_tests` remained.

Money, time, action slots and two accepted-edit slots remained. Thus it is inaccurate
to say that all resources were exhausted, or that the model could still edit when
it chose finish. Exploration consumed the response capacity needed for a revision;
the additional helper was admissible because ordinary completion was still ready.
The public counterexamples were visible information, not registered blocking checks.

## Decision and limitations

Keep the proven latest read/search delivery fix. Reject this candidate as a complete
repair. Merely placing counterexamples in the prompt was insufficient in this run.
The evidence now identifies two concrete issues before another live test: preserve
new helper observations across completion-segment changes, and make the response
cost of another diagnostic reflect the intended unresolved revision path. Separately,
known current public counterexamples need an explicit completion disposition if
they are to block a success claim; an honest assessment paragraph is not resolution.

This trial does not establish that a larger context/output budget would help,
that the protocol reservation is universally too conservative, or that mandatory
counterexample checks would make the model derive a correct repair. Lost helper
output, response-cap admission, remaining repair difficulty and optional completion
all coexist. A further comparison needs a concrete intervention and fresh approval;
no larger-budget run or additional implementation was performed after this result.

## Evidence

- Result root: `C:/pt/public-counterexample-repair-run-v1`.
- Result hash: `sha256:9e9ee3303d721b6008b275702f5e2ccdbff8c6ef40497f0346e2cba2f847fc69`.
- Branch journal: `repair/runs/run_dev_3e21775752a54cae.jsonl`, through event 309,
  hash `sha256:53fc43ab9c8eaa9c36bc7cabb59131eb64bf833359a698b08a1d91ab068cc74b`.
- Public outcome audit: `public-outcome-audit.json`,
  hash `sha256:3482b254fa6dfd893546c1eee4c2c619c4e5e0916b3e95f9d02eb0187a31b272`.
- Audit receipt: collector event 31,
  `sha256:f41228340300514af17c3c3dd39d1c496c8d12351d310829aab639aed78a6257`.
- Helper output delivery: receipt/request events 271→274 (present), 286→290
  (stdout absent), with fresh segment 289. Last input artifact:
  `sha256:bf54ff1c9d6a1f2001d2e512ea1dcd5810ab81accd862015122f9603392d0277`.
- Final public matrix receipt:
  `sha256:705435e164b3804de3688c73d7d91c9cdd7c46f36c5a65da8cdf382caaff5311`.
- Allocation closure: collector event 30, known cost USD0.599278, no automatic retry.

Local mechanism validation before dispatch passed 37 focused tests in 22.619s,
including isolated mock evaluation; Ruff and documentation checks passed. The live
result above is an additional negative diagnostic, not a causal or generalization
claim and not a new benchmark solve.
