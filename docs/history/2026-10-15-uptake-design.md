# Pre-edit diagnostic uptake: minimum continuation design

Date: 2026-10-15. Design only; no paid or task execution authorized or performed.
Follows the [grading correction](2026-10-15-pre-edit-grade.md), which qualified
both saved B proposals under the original selection rubric. It does not reopen
the closed A/B allocation or change the runtime baseline.

## Limits fixed before execution

| Resource | Frozen proposed limit |
| --- | --- |
| Task | `swebench-lite-dev-sqlfluff-sqlfluff-1733`, `dev-train` |
| Rows | Saved B1 once, then saved B2 once; two continuations total |
| Model | `gpt-5.4-2026-03-05`, xhigh, default/standard service tier |
| New generations | Six per row, twelve total, including any auxiliary model work |
| Token-count requests | Six per row, twelve total, including discarded counts |
| Tokens per generation | At most 60,000 input; fixed 25,000 output ceiling, including reasoning |
| New provider allowance | USD 3.50 per row, USD 7.00 invocation-wide; no transfers |
| Other provider work | At most one exact-model metadata read; zero retries, correction calls, paid compaction or judges |
| Solver actions | Eighteen per row, including its saved probe, batched reads and automatic checks |
| Accepted edits | One remaining per row; no reset or extra edit after a failed final repair |
| Solver time | At most 600 seconds per row, also bounded by inherited remaining time |
| Terminal assessment | At most one 30-second public oracle and one 330-second isolated evaluation per submitted row |
| Whole invocation | 2,100 seconds including preparation, counting, tools and assessment |
| Credentials | `C:/Users/geonj/Documents/PatchLoop/.env`; contents not read in this preparation |

Six responses leave room for two source-investigation batches, one follow-up
diagnostic, an edit, verification and finish. This is a ceiling, not a required
action sequence; automatic rechecks consume actions without a model call. A
smaller response cap could stop the repair before testing the intended chain.

The [official pricing table](https://developers.openai.com/api/docs/pricing),
checked on 2026-10-15, lists standard GPT-5.4 input/cached-input/output at
USD 2.50/0.25/15.00 per million tokens. With no cache discount, one maximum request
reserves `60,000 * 2.50 / 1e6 + 25,000 * 15.00 / 1e6 = USD 0.525`.
Six requests reserve USD 3.15; twelve reserve USD 6.30. USD 7 is the hard ceiling,
not expected spend. No long-context, regional or priority surcharge is assumed.
Prices, account access and the exact snapshot must be rechecked before dispatch.

Every generation needs a fresh successful count of that exact final request and
full-output reservation against both caps. Do not lower the output ceiling to
squeeze in another response. A count is single-use and a failed/uncertain count
cannot be retried. Call caps prevent further dispatch, not settlement of an
already dispatched response; its tool action still needs action/time admission.
Terminal assessment has its own stated allowance and never permits another edit.

## Success and stop rules

| Dimension | Predeclared rule |
| --- | --- |
| D: diagnostic exposure | The unchanged saved probe reaches the public CTE under a faithful hypothetical L036 substitution, returns an interpretable contradiction to preservation, and its actual receipt is delivered |
| U: observable uptake | Before or in the accepted edit, existing public hypothesis, causal-revision, notes or tool arguments connect the observation to rejection or material qualification of the simple-revert premise; the next action is consistent |
| P: public repair | An actual submitted source change passes the unchanged registered `base-regression` check on its final diff and the frozen original-issue CTE oracle; tests/constraints are not weakened |
| I: isolated acceptance | One existing registered isolated evaluation of that submitted artifact returns `EVALUATOR_PASS`; no private feedback reaches the solver |
| Integrity and safety | Candidate, input, action and receipt identities remain bound; safety is reported separately from task acceptance |

A row demonstrates the complete chain only with D, U, P and I supported and
boundaries intact. A new hypothesis sentence, a relevant read, successful
submission or public PASS alone does not suffice. No specific replacement rule,
file name, operator patch or explanation format is required. Existing public
fields supply evidence; no additional instruction asks the model to announce a
hypothesis change. Correct repair without explicit public linkage is repair
evidence with U `NOT_OBSERVABLE`, not proof of forgetting or complete-chain success.

Two complete chains out of the two fixed rows support a local feasibility finding.
One is mixed evidence; zero provides no complete chain. Keep exposure failure,
executed task failure, infrastructure error, resource cutoff and unobservable
uptake separate. Do not remove an unassessable row from the planned denominator.
No outcome adopts the instruction or automatically starts another experiment.

- Stop all remaining work on count, transport, billing, continuation, identity,
  private-boundary or cleanup uncertainty, or an invocation resource limit.
  Preserve settled usage and the original uncertainty; do not report unknown cost
  as zero. No automatic Docker start, image pull/build or model substitution.
- Stop a row before any new model call if its saved probe yields no usable
  disconfirming observation. Record whether setup failed, required evidence was
  missing/truncated, or the result did not contradict the premise. Do not fix the
  probe, substitute the operator reference, or choose a replacement sample.
- Stop a row at finish/stop, its resource limit, or a known malformed/incomplete
  response. No protocol-repair call, resume, retry, extra edit or budget extension.
  Other rows still run after an ordinary settled failure; uncertainty stops all.
- A normal assertion/test failure is evidence. B1's valid CTE assertion failure
  can satisfy D. An unrelated later assertion error is not a blanket veto unless
  it prevents or invalidates the required observation. Preserve all raw output.
- Freeze wording, rows, oracles and scoring before execution. No threshold change,
  prompt tuning, replacement, resampling or spending unused funds afterward.

## Why this is the minimum useful next experiment

The previous four responses established selection behavior at one familiar
checkpoint: A requested the unsupported final reversion twice; B proposed the
counterfactual twice. They did not execute a model-selected probe, expose its
result to that model, or observe a subsequent repair.

Continue both B responses instead of selecting the cleaner B2 or regenerating
them. This tests the missing observation-to-action-to-repair chain with two
continuations. Repeating A or adding a result-withheld arm is unnecessary for
that feasibility question and would increase cost. Consequently this design
cannot identify the diagnostic's causal effect or estimate improvement over A.
The existing A edits and historical failure are reference evidence, not fresh
controlled outcome rows. These are seeded continuations, not fresh task solves.

Plausible outcomes remain separate: no valid diagnostic exposure; valid exposure
but unsupported interpretation; supported revision but an incorrect patch; or
public success with failed isolated acceptance. A resource cutoff cannot identify
which later outcome would have occurred. A correct repair is not known to be
reachable from this particular candidate with one accepted edit; that restriction
is retained and must limit interpretation of a negative result.

## Exact continuation and execution sequence

The parent is `run_dev_c6cdf266d5a34ded`, prepared cut **364**, reviewed model input
**367**. Restore only the prefix before the original next decision and the third
edit candidate, whose diff hash is
`sha256:59679012118d519810c25430eb177c6fe0fb5480b986b452b6c2e8bd676d2987`.
The parent had 14 calls and 57 actions remaining. Importing a saved B response
consumes one historical model decision; executing its probe consumes one action.
New limits tighten the remaining allowance. Import recorded sample time without
rebilling the historical call or reopening any historical funds.

| Row | Saved sample | Saved probe action |
| --- | --- | --- |
| B1 | `sample_6cd00cf2d1fb4bb2a1c6cf35b73b34f6` | `call_g4i3Wut9q7aNbraYP2EEV25B` |
| B2 | `sample_5d84f5fdf7334e20af31d553f1c40354` | `call_KwfCpguw0Pm6G7Jc1RNgNEtv` |

For each row, restore a fresh external branch, execute its saved `run_probe`
exactly once, and apply the D gate. If exposed, deliver its actual full public
receipt with the same call ID and continue the ordinary registered-tool loop.
Keep the original B paragraph verbatim; add no interpretation, repair hint,
operator probe, future original edit or private material. The ordinary source,
current state and reduced budgets must be accurately rebuilt in the next input.
Keep segmented-v1/result-or-size-v1 handling, source retention, working notes,
tool grammar, source admission and repair recheck fixed. No new pruning or memory
mechanism is part of this experiment.

Saved B outputs contain a separate opaque `output_order` artifact even though
their ordinary `continuation_ref` is null. Static review verified the encrypted
item shape and exact action ordering; encrypted content was not interpreted.
Preserve those items with the tool call/result, following
[Responses continuation guidance](https://developers.openai.com/api/docs/guides/reasoning#keeping-reasoning-items-in-context).
Dropping them or resampling a response is not an allowed fallback.

At the terminal boundary, freeze the candidate and public trace. Actual finish
uses the existing nonempty-diff and exact-diff required-check gate. Only submitted
artifacts receive the frozen public CTE oracle and one existing isolated
evaluation. No post-terminal result returns to the model. Record U/P evidence
before examining private verdicts. There is no new paid judge or independent
blinded-review claim. Native benchmark reevaluation is not included; registered
acceptance, public correctness, safety and generalization remain distinct.

The final public oracle derives its input and full expected output directly from
the original public issue, calls default `sqlfluff.fix` on the final candidate,
and checks exact equality. It does not monkeypatch L036 or trust a model-edited
test. Required regression credit must be fresh on the final diff; historical
PASS and the hypothetical probe supply no credit. Non-submission leaves terminal
acceptance NOT_RUN; do not manufacture a submission to obtain a verdict.

## Preparation status and required readiness work

The design is frozen at `C:/pt/hypfollow01/plan.json`, hash
`sha256:ebf523c24e626e4c8b184eda4f3ab9a9b764958c8e37eab8c4821298ae0e3b5a`.
`grading.json` fixes the separate D/U/P/I criteria and edge cases. `bindings.json`
binds 74 prior inputs; `proposals/B1.py` and `B2.py` are exact public-response
extractions. `operator-only/final_cte_oracle.py` is frozen but unexecuted.
`runs/run_dev_uptakedesign.jsonl` is a new append-only, hash-chained journal.

**This is not yet an executable collector or paid-run approval packet.** The
existing [observation fork](../../.agent/observation-exposure.md) restores settled
runner checkpoints; it does not automatically import these response-only samples
and attach their pending actions. The next provider-free preparation must:

1. Implement the narrow import/continuation adapter using existing restoration,
   admission, gateway and evaluator paths; do not bypass normal resume guards.
2. Rehearse receipt delivery, encrypted ordering, current source/read ownership,
   reduced budgets, exact count/dispatch binding, failed-probe output preservation,
   final-diff checks and private-feedback exclusion with an inert provider.
3. Bind that implementation, committed runtime, first-input reconstruction,
   both samples, existing probe/dependency/evaluator identities and this protocol
   in a reviewable execution manifest. Read-only readiness must pass; no new images.
4. Obtain exact paid authorization only after that provider-free preparation.

No collector was implemented, credential loaded, model/count/metadata API called,
Docker started, task/probe executed or private evaluation run during this design.
Static artifact/AST/cost checks and documentation layout/link, Ruff and whitespace
checks are relevant here; broad runtime tests and mock smoke are NOT_RUN.
