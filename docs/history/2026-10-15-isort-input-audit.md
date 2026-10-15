# isort I1: input and response audit

Date: 2026-10-15. Saved-evidence review only; no new model, diagnostic or evaluator
execution. The [I1 outcome and pre-evaluation U grade](2026-10-15-isort-uptake-result.md)
remain unchanged. Runtime, prompts, frozen inputs and historical records are unchanged.

The question is why the complete position counterexamples did not change the
submitted patch, and whether a minimal intervention is justified. The observed
decision completed the old keyword-based repair plan using one confirming
diagnostic case and the registered regression PASS. Missing delivery and forced
tool closure do not explain it. The independent effects of the plan, completion
advice, presentation and interpretation of the task cannot be identified from
this single response.

## Evidence boundary

The authoritative input is I1 journal event **344**, prepared artifact
`sha256:2460f77bf2d7a9afde727eb21da9b1c1c6118957ee21536039c7f6fb83ce40dc`.
Its request hash matches counted/dispatched events **346/349**:
`sha256:8be6295e69d4294b7275881b5e86cc42e03babc248e990e1cf0f0f4895f0984f`.
The public response is **352**; plan update, finish and submission are **354–360**.

Read the exact system/user/public-task text, preceding public native calls and
the latest `harness_current_state`. Decode only the existing public diagnostic
stdout. Opaque reasoning was not interpreted; private evaluator contents were
not used to explain the decision. A decoded audit table is not an input the
model actually received. No synthetic counterfactual response is claimed.

## The inherited hypothesis and its closure

The preceding native search rationale says that opening-line and per-item cases
reach `wrap.line` with the same shape, and asks whether existing `type: ignore`
handling supports a text-specific extension of the `noqa` exception. The native
mutation then states that the safe distinction available there is comment text.
It expects type-ignore comments on the opening line and ordinary item comments
on the imported name. This is a semantic substitution: comment kind is being
used as a proxy for original attachment.

`working_plan.plan.text` repeats that plan: narrow `wrap.line` to
"statement-level linter comments (`type: ignore`, with existing `noqa` behavior
left intact)" and use the regression recheck. The mutation cleared the open
question; verification concerns were empty. However, the plan was correctly
labelled `model_authored_unverified` and `diff_currency=historical`, and
`working_plan.review_request.requested=true` asked for review after the mutation,
check and first submission-ready transition. The harness did not certify the plan.

I1's actual response says the current diagnostic preserves the reported
opening-line type-ignore case, calls the requested behavior addressed, and
selects `finish_task`. Its replacement plan begins "The latest results confirmed
the intended repair" and declares the remaining work complete. Thus plan review
occurred; it confirmed the old hypothesis without addressing the two contrary
position observations. Adding another generic plan-review instruction would
duplicate an instruction that was already delivered.

The existing memory was not simply lost: note n1 still points to
`parse.file_contents` returning `categorized_comments` and `as_map` as evidence
of comment association. The new receipts also contain different `straight` and
`nested` categories for opening and item inputs. That is evidence of an available
alternative distinction, not proof of the exact repair or its feasibility within
the remaining edit allowance.

## Competing influences in the actual input

| Candidate influence | Observed support | What limits the explanation |
| --- | --- | --- |
| Commitment to the old plan | The same comment-kind hypothesis appears in prior native arguments, the current plan and the final confirmation. The open question was cleared. | The plan was explicitly unverified/historical; review was requested. Textual continuity does not establish the plan's causal effect. |
| Completion advice | `completion_guidance.next_action.tool=finish_task`, `submission_ready=true`, no remaining required check IDs, and advice to submit if no useful experiment remains. The response cites that completion condition. | The same message says eligibility is not proof of untested behavior. Read/search/replace/probe remained available and protected mutation completion was possible. This was advice, not a forced finish. |
| Diagnostic presentation | Both receipts have top-level `status=passed`, exit 0 and setup PASS. The contradictory `position_preserved=false` values are JSON records inside a stdout string, not case-level fields beside the completion state. | The packet explicitly warns that execution status is not a repair verdict. The response cites a positive behavior from the current diagnostic, so complete non-exposure is excluded and complete non-reading is not established. There is no explicit claim that exit 0 proves all cases passed. |
| Narrow interpretation of the task | The exact issue example is `type_opening`, which now succeeds; the crossed cases are explicitly labelled inferred public controls. The response refers to the reported case. | The issue describes moving comments generally, with mypy as an example. `type_item` demonstrates newly changed behavior on an otherwise identical public input, and the prompt explicitly requires preserving behavior outside the requested change. No response dismisses the controls as out of scope. |

The latest state contains 86,841 characters, with a 24,553-character operator
packet. In that serialized state, completion guidance begins at character 1,166,
the operator packet at 35,052, recent checks at 67,905 and the plan at 85,557
(zero-based). The whole request counted 53,144 tokens. This documents presentation
and repetition of the old interpretation; character position is not attention
evidence or a causal measurement. The required complete packet was present and
not truncated. There was no additional first-turn pruning or handoff that removed it.

The current state also has `current_public_failure=null` and no unresolved
verification concerns. These do **not** mean the candidate has no contradictory
behavior. That failure field describes registered-check failures, while this
operator packet intentionally remains separate. The connector only adds
`operator_public_observation`; it does not synthesize a model check, rewrite the
plan or change the completion gate. This matches the frozen design and current
contract, rather than exposing a newly discovered missing-field bug.

The relevant source is `_completion_guidance` in
[runner.py](../../patchloop/dev/runner.py), the existing evidence/plan warnings in
[model.py](../../patchloop/dev/model.py) and
[working_plan.py](../../patchloop/dev/working_plan.py), and `add_feedback` in
[isort_uptake_execution.py](../../diagnostics/isort_uptake_execution.py).

## What the crossed observations establish

This table is derived from the already-delivered base and submitted receipts,
not from the later terminal oracle or an additional execution:

| Case | Declared original association | Base output | Submitted output | Observed change |
| --- | --- | --- | --- | --- |
| `type_opening` | Opening | Item | Opening | Reported example repaired |
| `type_item` | Item | Item | Opening | New movement introduced |
| `plain_opening` | Opening | Item | Item | Existing movement persists |
| `plain_item` | Item | Item | Item | Original association preserved |

`type_item` is the strongest challenge to the sufficiency claim: the same text
and imported name remain on the item in base but move after the patch. It is not
merely a second pre-existing failure outside the exact issue example. The
public control's expected-position provenance still matters; this table does not
promote inferred expectations into private ground truth. It does show why the
single confirming `type_opening` result cannot establish general ownership
preservation or absence of a new movement regression.

## Minimal-change decision

**Keep the current runtime and baseline. No mandatory implementation correction
is established by this audit.** It narrows the public failure to selective use
of evidence at completion, but cannot assign separate effects to the three
presentation/context choices. It does not prove deliberate test gaming or reveal
the model's internal reason for leaving the controls unaddressed.

For a later, separately chosen intervention, the narrowest useful candidate is a
presentation change in the operator diagnostic adapter: expose all four cases
as a compact comparison of declared expectation, base observation and current
observation alongside the full raw receipts. Preserve case order, provenance,
diff hashes, comment/AST results and execution status separately. This requires
no new test, repair hint, aggregate correctness label or automatic finish gate.
The table above makes that candidate concrete; no revised packet was dispatched
or installed, and its effect on repair is unmeasured.

Deleting finish advice is a smaller text edit, and was considered before adding
information. However, it would change policy advice globally without establishing
that advice caused this response, and would leave the case comparison implicit.
Deleting the plan would also discard useful hypothesis history without showing
that the plan caused failure. Do not adopt either from I1. Do not add a generic
"reconsider counterexamples" paragraph: existing instructions already require
evidence-based revision, scope-limited conclusions and reconsideration of plans.
More memory, context, edit slots, paid calls or mandatory diagnostics are likewise
unsupported by this trace.

The earlier [SQLFluff counterexample review](2026-10-07-counterexample-results.md)
also found current operator feedback separate from the native failure catalog
and completion advice. That is supporting recurrence of an unresolved mechanism,
not a controlled comparison with I1. Existing
[thin presentation](../../patchloop/dev/thin_policy.py) already removes plans and
completion advice together; switching to it would not isolate their influence.

## Audit artifacts and validation

New external root: `C:/pt/isortinputaudit01`.
`public-input-excerpts.json` contains exact selected public inputs, response and
decoded saved receipts with source pointers. `bindings.json` binds the prepared
artifact, response event, parent journal and inspected source/history bytes.
`runs/run_dev_isortinputaudit.jsonl` is append-only and hash-chained.
The extractor checked the counted/dispatched request identity, full feedback
equality and unchanged source journal; all frozen input bindings still verify.

Only this follow-up and current documentation change. The original I1 response,
grade, result, experiment packet, source code and user AGENTS.md changes remain
unchanged. No provider, model, target diagnostic or evaluation execution occurred;
the only checks are saved-file integrity and documentation validation.
