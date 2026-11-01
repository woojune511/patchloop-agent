# SQLFluff edit guidance follow-up: submission reached, repair not accepted

Status: LIVE_EXECUTED, AUDITED, allocation CLOSED. One approved attempt; no retry.
All evidence remains official=false and claim-ineligible.

## Question, scope and outcome

The [prepared follow-up](2026-10-29-edit-prerequisite-single-plan.md) tested the
[edit-prerequisite fix](2026-10-29-edit-prerequisite-guidance.md) on the prior
SQLFluff B immediate-stop condition. Its exact command and new USD4.50 cap were
approved in this conversation. Same public original, task/model/settings and
nominal resources; request state_root was the only request-field change. Runtime
implementation was `7d97cbb5`, preparation record commit `32ba7ca0`, runtime hash
`sha256:8eb3e389ce20f0b9143c330a3dae3dbd9fcca65f8f0b1ad5d1f5c6dc6a621cfb`.

| Outcome | Observed |
| --- | --- |
| Independent task acceptance | FAIL; PRIVATE_EVALUATION_FAILED |
| Safety | PASS |
| Public regression | 506 PASS, `pytest -q test/rules`, 16.88 seconds |
| Submission | Normal `finish_task`; unverified_delivery |
| Model / input-count calls | 11 / 11 |
| Tools / accepted edits | 19 / 1; first edit on response 9 |
| Tools by type | 12 searches, 3 reads, 1 helper probe, 1 edit, 1 check, 1 finish |
| Protocol corrections | 0; fresh-correction behavior NOT_EXERCISED |
| Settled cost / cap | USD0.587558 / USD4.50 |
| Active elapsed time | 350.549 seconds |
| Registered original attempts | 0; distinct from the executed helper |

The run did not terminate on a resource limit. Its final request still offered
read/search, replace_text, run_probe and run_tests beside finish/stop. Nominal
unused response/edit/cost capacity is not authorization for another invocation.

## Mechanism evidence

The first actual request retained `needs_current_source` with the offered
read_file/search_files prerequisite. Its saved input, actual schema, input-count
start/finish and provider dispatch identities matched. The first response selected
four searches. The next request delivered current editable evidence from
`src/sqlfluff/rules/L036.py`, reported ready_to_attempt and actually offered
replace_text. This remained available through the later requests.

All 11 actual requests passed the card/schema/state-tools/count-dispatch audit.
The previous immediate-stop behavior did not recur in this one run: source
acquisition, edit availability, edit execution, public check and normal submission
were observed. This is a historical single-draw follow-up, not a controlled causal
effect or solve-rate estimate. It cannot establish that the card caused the choices.
The independent acceptance FAIL means it is not evidence of successful repair.

## Public trajectory and remaining question

The baseline helper did execute `sqlfluff.fix()` on the public WITH SQL example.
It observed nine spaces before `my_id` and the L003 message that a fix would
re-cause the same error. The helper exited zero without truncation. Its later
segment listing parsed the original `sql`, not the transformed `fixed` output.
It therefore did not establish the segment structure of the faulty fixed result.

The model's hypothesis was that L036's whitespace deletion plus separate newline
creation left an extra space. It changed the first target's first whitespace into
a newline and deleted only additional whitespace. This is a model hypothesis,
not a verified explanation. After applying the candidate, it ran the registered
regression and submitted; no helper replay of the reported example or new
discriminating test followed. The finish assessment acknowledged the missing
bound reproduction/replay. Changed-line execution remained UNKNOWN due to
unsupported_python_options; it does not establish that the changed branch was absent.

The next smallest diagnostic is to run the same public WITH input and
`sqlfluff.fix()` settings on the saved candidate and compare the observed output
with the baseline: is the indentation eight spaces, still nine, or otherwise
incorrect? If needed, parse the transformed output rather than only the original.
A remaining public failure would refute the patch hypothesis; a passing example
would leave other coverage/correctness questions open. No additional target replay
was executed here. Operator review used public artifacts and acceptance/safety
verdicts without opening private test contents or a reference patch; evaluator
output was not fed back to the solver. The specific private failure cause remains
unestablished.

## Decision and evidence integrity

Keep the capability card: this run confirms actual transport and an available
source-to-edit path. Do not change default submission policy, expose every schema,
increase budgets or add another mandatory diagnostic gate from this one result.
The next issue is candidate behavior and verification coverage, not a demonstrated
inability to discover the edit tool. Helper return-type/capture issues from other
tasks remain separate and are not resolved by this run.

The approved manifest hash is
`sha256:4723c5e442ddc326c1d349cbf4102662a851be6962e7d01fdffcb0ef9e82200f`.
Its 29 sealed bindings remained unchanged after execution; the 58 prior-plan
bindings were unchanged during preparation. Count/provider/action/probe receipts
paired, usage settled, cost sums matched, cleanup had no recorded hazards, and the
allocation closed. No retries, new model calls or target executions were added by
collection or audit. Existing image identities were reused without pull/build.

Evidence root: `C:/pt/edit-prerequisite-single-run-v1`:
`batch-collection.json`, `summary.json`, `post-run-audit.json`, and the row's
`18-B/collection.json` plus hash-chained run `run_dev_d5806f63861b47e6`.
The submitted patch hash is
`sha256:d3022a59756dfb1c7ad44b9b2c063306a384e147f78c9f0a0194d3fc560bfe62`.
Plan, approval, preflight and first-request artifacts remain under
`C:/pt/edit-prerequisite-single-plan-v1`.
