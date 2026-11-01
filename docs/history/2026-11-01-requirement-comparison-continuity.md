# Keep the public requirement attached to helper review

Date: 2026-11-01. Implemented and locally tested; no live model experiment.
Parent: `37c6b5e1a80eb108030c5c509c38ababc4c8c1a4`. All evidence is official=false,
claim-ineligible. No paid allocation was opened or reused.

## Problem and selected question

The [fresh task8 run](2026-11-01-causal-link-task8-results.md) delivered causal-link
guidance but again repaired an adjacent helper. The public report described
serialized bytes and OL failure with successful OB/OF controls. The model broadened
this to bytes-like input, then adopted array/bytearray failures for both OL and OB.
Those helpers passed after editing, while the original distinguishing conditions
remained unexplained. Independent evaluation failed. Resources were still available.

This recurring target substitution matters more than another increase in probe
capacity. The public issue was already delivered, so adding another copy of the
issue does not address the observed mechanism. Current source revealed two gaps:

- Every valid decision records `working_plan_updated`, consuming the existing
  event-based review even when its scope annotation is null. A plan rewrite could
  therefore carry the helper forward without recording its relation to the report.
- `public_conditions` accepted a model paraphrase without binding it to the issue.
  The plan and its helper could effectively supply both sides of the comparison.

These are observed contract/projection properties, not proof that they caused the
model's failure. An alternative remains inadequate semantic judgment despite all
relevant evidence. Another is poor selection of a distinguishing input or source
path. Retaining an explicit comparison tests the structural explanation without
assuming a new memory system, stronger model or mandatory reproduction is necessary.
If a future model receives and accurately records the mismatch but still stops,
this intervention alone would be insufficient. A quotation alone cannot prove fit.

## Small change within existing contracts

The plan now orders an approach to `public_task.issue`; it does not restate the
requirement as an independently editable finish criterion. Existing
`scope_review.input.public_conditions` quotes a literal substring of the public
issue title/description, with CRLF/LF normalization only. The host stores source,
issue hash and quote hash. A paraphrase rejects only this annotation, preserving
the prior review and allowing the action/plan update to proceed. Null controls and
legacy string annotations remain readable; neither establishes an original binding.

`review_request.requirement_comparison` is derived from existing public action
receipts. It selects the latest helper with matching action/input/source/diff
identity, references the immutable issue and the existing `recent_probes` bodies,
and remains `review_needed` across null reviews, plan replacement and recovery.
A stored case linking both the public quote and that execution changes it to
`review_recorded`. The interpretation is still model-authored and requirement fit
is `not_certified`; failed/partial execution never becomes successful coverage.

An exact replay on another diff also references its prior observation. Both use
the existing three-probe retention limit; the remaining slot takes the newest
result. Compact completion preserves their bounded program/output and historical
flags. This prevents the base discrepancy disappearing when the candidate passes.
There is no duplicated program in the plan, exhaustive obligation ledger or
automatic semantic mismatch detector. A newer helper becomes the comparison target.

Guidance asks whether the actual conditions/outcomes support, contradict or leave
the proposed cause untested, and connects a material gap to a useful offered action
or blocker. Source evidence may justify proceeding without another execution.
Redundant wording was removed to keep the combined brief prompt at 11,123 characters
within the prior 11,164 bound. The four-case/500-character scope bounds, model/action/
edit/probe limits, action_id+input_hash recovery and finish eligibility are unchanged.
No new tool, required annotation, review call, semantic gate or task-specific input
was added. The shared completion retention contract and enabled planning identities
change; planning OFF receives no new annotation/comparison.

## Validation and preserved failures

External evidence: `C:/pt/requirement-fit-20261101-v1/`.

| Check | Result |
| --- | --- |
| Final focused controls | 96 PASS, 48.441s |
| Full quick run before corrections | 1,515 PASS, 4 FAIL, 1 host skip; 399.028s |
| Corrected quick cases plus added integration case | All four failures pass in final focused run; resulting manifest coverage 1,520 PASS / 1 skip |
| Ruff | PASS |
| Segmented brief mock smoke | EVALUATOR_PASS, safety NOT_RUN; zero provider cost |
| Frozen public-prefix projection | PASS over 11 decision points; zero model/probe/evaluator executions |

Initial focused failures exposed an incorrect fixture path, a missing public-issue
argument in the actual-input audit, and a changed contract pin; all were corrected.
The quick run then exposed two mock annotations using paraphrases, the prompt length
bound and an enabled-contract pin. The fixture now selects a real issue quote; the
prompt was shortened and the pin updated. Failure logs/XML remain beside final
receipts. The full quick suite was not rerun after these focused corrections.

Controls cover null/rewritten plans, restart/idempotency, invalid or legacy quote
bindings, changed issues, wrong execution references, partial results, source-hash
mismatch and replay on another diff. A real runner-input fixture executes four
helpers, edits and replays the evicted first helper: the final counted/dispatched
input contains base + newest intermediate + replay, exactly three observations.
Separate append/segmented mock controls reach isolated evaluation with the stored
scope review. The synthetic provider-wire fixture deliberately retains its existing
evaluator-identity ERROR; it is delivery evidence, not acceptance evidence. The
standalone mock smoke supplies the separate isolated PASS above.

The saved task8 comparison holds old public events/decisions fixed. The old probe
review reason disappears after the next valid decision (other handoff/mutation/check
reasons can remain). The new comparison stays pending in calls 7-11, including after
the call7 plan replacement. Call11 references both the base helper and candidate
replay under the same public issue hash. See `projection-plan-final.json` and
`saved-public-projection-final.json`. This is a mechanical projection control,
not a new autonomous diagnosis or counterexample execution.

`validation.json` binds final source/runtime hashes, test results, public projection,
mock evidence and documentation checks to an external hash-chained journal/CAS.
`commit.json` records the resulting commit. Historical runs, private evaluators,
reference patches and task data were not changed; no private assertion was inspected
or supplied to runtime guidance or tests. Generic CSV fixtures exercise the contract.

## Decision and remaining question

Keep the locally verified continuity change. It preserves the comparison at the
decision where the adjacent repair was selected, without forcing another execution
or treating missing reproduction as automatic task failure. It does not establish
better reasoning, task8 acceptance, efficiency or generalization.

The next unresolved observation is whether a model uses this retained difference
to inspect another producing step, construct a discriminating public case and repair
the original behavior. A model may quote an irrelevant clause or misinterpret a
valid result; the host deliberately does not certify those judgments. No new paid
run is scheduled by this implementation record.
