# isort I2/I3: different first decisions under shared guidance

Date: 2026-10-15. Saved-input/response/source audit only, official=false.
No model, input-count, metadata, credential, diagnostic or evaluator execution.
The [I2 result](2026-10-15-isort-table-result.md),
[I3 result and pre-assessment grades](2026-10-15-isort-retention-result.md),
frozen designs, manifests and runtime remain unchanged.

The observable failure is that I3 completed the inherited comment-kind repair
plan using its two confirming cases and the registered regression PASS, without
addressing the crossed item-type counterexample. I2 instead treated that same
counterexample as a reason to reject the hypothesis. The common plan and finish
advice plausibly shape these decisions, but their causal contributions and the
source of response variation are not separable from this pair. No mandatory
current-contract correction or adoption of another prompt is established.

## What was actually held fixed

Both first requests are prepared at row event **344**. I2's request hash is
`sha256:1234c958e6aabee2fb48ac61eb5a7b64cbfedb03f16db8232e8f1e9fcce984b1`;
I3's is
`sha256:a83ac3c1f97343c1a83dd9938d279a544a523c784acb67e00bf0dcbd394ac855`.
Each matches its actual successful input count and provider dispatch.
Recursive comparison of the decoded requests finds exactly one differing value:

`/input/13/content/state/remaining_budget/active_wall_time_seconds`: **269 / 267**.

The system and user task, developer records, native public calls and outputs,
opaque continuation items, complete operator packet/table, plan, notes, source,
diff, tool definitions and all other request settings match. Both counted 53,279
input tokens, requested the same exact model/xhigh/default tier and 25,000 output
tokens, and returned completed responses without a protocol error. Encrypted
continuation equality was checked without interpreting or displaying its content.

I3's retention addition could first distinguish a later input. I3 generated no
later input or context boundary. The different first action cannot be an observed
effect of preserving the diagnostic across such a boundary. The common first
packet was neither pruned nor truncated in either request.

## The inherited hypothesis and the two responses

The public native mutation at input item **11** says that `wrap.line` receives
opening and item comments in the same flattened form and calls comment text the
safe distinction available there. Its expected behavior is type-ignore comments
on the opening line and ordinary item comments on the imported name. The latest
plan, revision **15**, repeats the proposal to narrow the exception to
"statement-level linter comments" and then use the required regression recheck.
This substitutes comment kind for original attachment.

The diagnostic crosses those two dimensions:

| Case | Original association | Seed output | Relationship to the old expectation |
| --- | --- | --- | --- |
| `type_opening` | opening | opening | Confirms the reported example and type-comment expectation |
| `plain_item` | item | item | Confirms ordinary item-comment preservation |
| `type_item` | item | opening | New movement relative to base; contradicts safe kind-based placement |
| `plain_opening` | opening | item | Existing position failure remains |

These observations are in the shared input, before either response or final
assessment. The exact issue example and the derived controls retain their
different declared expectation provenance; no hidden test is used to explain
the first action. `type_item` is the strongest counterexample because the patch
introduces movement that the base did not have on that input.

| Public decision | I2, event 352 | I3, event 354 |
| --- | --- | --- |
| Evidence selected | Regression PASS plus the item-type counterexample | Regression PASS, type-opening success and ordinary-item success |
| Hypothesis statement | The diagnostic "contradicted the assumption" that the text special case is safe | The narrowed gating "behaved as intended" in the replacement plan |
| Remaining work | Separate opening and nested comments before flattening; inspect helpers | No further public work before submission |
| Next action | Two searches in output/comment helpers | `finish_task` with unchanged seed |

I3's plan update at **357** and finish arguments at **358** repeat that sufficiency
judgment; **359/363** confirm finish and unchanged submission. I2's public basis
explicitly distinguishes an original-example fix from a new item-comment regression.
I3's public basis never explains away that regression or calls its setup invalid.

This establishes selective use of confirming evidence in the public decision.
It does not reveal whether I3 overlooked the negative rows, gave them too little
weight, or silently interpreted them as outside the task. It does not prove
deliberate test gaming, refusal to revise, or a particular internal reasoning path.

## Plan and completion guidance: influence versus authority

The latest plan is explicitly `model_authored_unverified`, with
`diff_currency=historical`. Its review request is true for mutation, check and
first-ready results. Delivered system lines **114-119** require reconsidering
what was confirmed, contradicted or left unresolved in the same next response.
Lines **124-127** deny that the plan or check PASS certifies correctness. I3 does
perform the requested plan update; it confirms the old interpretation. Thus the
failure is not absence of a plan review, and another generic review rule would
repeat an existing instruction.

The latest completion state says `ready_to_submit`, `submission_ready=true`,
`next_action.tool=finish_task`, and has no remaining required check IDs. Its
message says submission is eligible, **not proof of untested behavior**, and
conditionally recommends a useful probe or otherwise finishing. System lines
**96-101** similarly limit conclusions to observed coverage and make experiments
optional. These are salient finish cues with semantic caveats, not an unconditional
order to submit or an automated choice of the tool.

Read, search, replace, probe and finish were all offered. The action horizon had
no closing tools, five exploratory turns, seventeen exploratory tool slots and
a feasible protected mutation path. Remaining overall allowances were six model
calls, eighteen tools and two accepted edits. `tool_choice=required` requires a
tool call, not `finish_task`. The 2-second display difference changed none of
these admissions. I3 did not cite urgency, and it submitted well before its
solver deadline. A forced finish or exhausted repair budget does not fit the record.

Other common state can reinforce closure: the open question and current public
failure are null and verification concerns are empty. However, the operator
diagnostic intentionally remains separate from registered checks. Those fields
do not assert that its two contrary cases passed. The parser association note
also remains available. No lost first-context observation or false promotion of
the old plan to verified status was found.

The current-state text is 87,498 characters. Completion guidance starts at 1,166,
the operator packet at 35,052, and the plan at 86,214 (zero-based). This describes
shared presentation and repetition, not attention measurement. The table is
already explicit; the raw execution/setup PASS is explicitly labelled as distinct
from a repair verdict. I3 cites positive case behavior, not an assertion that all
cases passed merely because execution exited zero.

Source ownership matches the delivered behavior:
[`_completion_guidance`](../../patchloop/dev/runner.py) supplies an offered
recommendation without executing it; the plan contract in
[`working_plan.py`](../../patchloop/dev/working_plan.py) treats plans as annotations;
the diagnostic adapter retains separate operator data. The observed behavior
does not reproduce a current implementation-contract defect.

## What response variation does and does not explain

Nearly matched requests produced materially different first decisions. That is
an observation; the underlying source of variation is not identified. The input
still differs by two seconds, and the logs do not identify internal sampling or
backend state. Neither request specifies seed, temperature or top_p. Identical
model ID/settings and input counts do not establish a deterministic execution.
No failure probability or relative causal contribution can be estimated from
these two responses.

Plan/advice influence and response variation are compatible explanations: common
cues can affect which outcome is favored without forcing every response. I2
revising under the same cues weakens the claim that they necessarily force finish;
it does not prove their influence is zero. Conversely, I3 echoing the old plan
does not prove that removing the plan would have changed its action. Nothing in
this pair independently varies plan, completion advice or the 2-second display.

The strongest bounded interpretation is that I3 treated the old repair's expected
successes as sufficient, while I2 used the new regression to reopen that repair.
The table made that revision possible in I2 but did not reliably elicit it in
this observed pair. This is not a measured retention effect, a model-temperature
diagnosis or evidence that a longer context or more calls would solve the problem.

## Minimal-change decision

**Keep the runtime and baseline; do not install another rule from this audit.**
The current evidence identifies a decision-quality failure but does not establish
a required contract fix or an intervention that improves accepted repairs.

Subtraction was considered before adding more instructions or state. Removing
the `ready_to_submit` finish recommendation would be the smallest distinct
candidate if a later investigation were separately justified. It would leave
the plan, system-level completion language and eligibility signals present, so
even that comparison would measure only the removed recommendation's marginal
effect. Its benefit is untested; no variant, experiment or paid follow-up is queued.
Deleting the plan is broader, loses useful history and leaves the same hypothesis
in native mutation arguments. Adding generic counterexample-review prose would
duplicate the delivered instructions.

Do not promote derived operator cases to registered failures, add a mandatory
probe/finish gate, force a new edit, increase memory or lengthen the budget to
make this case pass. Those change authority or workflow without a demonstrated
benefit. Preserve I3's C NOT_EXERCISED, R NOT_OBSERVABLE and U FAIL, and I2's
uncertainty-censored U NOT_RUN. Neither recognition alone nor fewer probes without
an edit becomes repair success.

## Evidence and validation

`C:/pt/isortfirstpairaudit01/public-excerpts.json` preserves exact selected public
input fields, inherited arguments, system lines and first responses.
`analysis.json` records request equality/differences, response metadata, source
bindings and interpretation limits, hash
`sha256:9bdc9ebb0bc5e15fc72ef4049a29c570ca89223192701f2c4f4b3112c6163aa5`.
The append-only hash-chained journal is `runs/run_dev_isortfirstpairaudit.jsonl`.
Saved-data checks validated both row chains, count/dispatch identities and eighteen
immutable file bindings. No original record, grade, manifest or runtime changed.
Five documentation layout/link tests passed in 0.10 s; `git diff --check` passed.
No runtime test, mock continuation or experiment was run for this document-only
follow-up. The user's existing AGENTS.md change remains untouched.
