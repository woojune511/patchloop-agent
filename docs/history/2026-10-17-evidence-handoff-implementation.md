# Evidence-preserving handoff implementation

Date: 2026-10-17. Design baseline: `ffe11a0`. User authorized implementation with
unchanged transition timing and budgets, using existing logs and no paid execution.
This follows the [audit](2026-10-16-segment-boundary-audit.md) and
[design](../../.agent/plans/evidence-preserving-handoff.md); neither historical
record nor original run is migrated. Local delivery validation is not repair-quality
or model-uptake evidence.

## Problem, intervention and limits

The audit found source loss at handoff and unverified interpretations surviving in
plans/notes. These matter because a reset can remove a branch needed to challenge
the retained explanation. It did not establish that transition timing caused repair
failures. Keep the completed-followup and size rules; change evidence selection and
its public authority labels. A wrong focus can still select the wrong evidence.

- `open_question` is a nullable `{text, evidence}` object: at most 500 text characters
  and two already-observed source/result references. Admission binds identities;
  invalid question updates preserve the prior question without rejecting valid
  independent annotations/actions. Null memory updates preserve it; null questions
  clear it. Unique exact source-body rebind or explicit expiry survives recovery.
- Existing mutation anchors come first, declared source ranges second, ordinary
  selection third. A range receives atomic priority only if it fits; oversized
  ranges do not suppress ordinary fallback or a smaller second reference. Old
  read/search/mutation source references use this same selector, not extra quoted code.
- Older declared verification results may carry their original bounded public
  call/result once. No summarizer, automatic read, behavioral judge, or review call
  was added. Fresh candidates can omit these optional bodies once if byte or known
  token limits require it. Identity/flags remain, delivery becomes incomplete.
- Candidate artifacts and count receipts precede segment commitment. Recovery uses
  the identical prepared request and known completed count. Unknown count/transport
  results stop; they never authorize fallback, retry or another dispatch.
- Notes expose `model_interpretation`, `evidence_currency`, and actual
  `evidence_delivery`. A current citation is not a verified statement. Concerns
  expose `closed_by_model`/`dismissed_by_model`, with `behavior_coverage=not_assessed`;
  the existing current-diff resolution eligibility is unchanged. Plans describe
  proposed remaining work; existing independent concerns retain original purposes.

The mechanical reason is now `major_result_followup_completed`; legacy journals
retain `major_result_reviewed`. Limits remain 24,000 retained source characters,
60,000 counted input tokens, 1,048,576 request bytes, 262,144 encrypted-item bytes,
40 model calls, 100 actions, four accepted edits and 1,800 seconds. No cost cap,
finish gate or provider retry policy changed. Contract hashes reject mixed-runtime
resume. Ordinary CLI defaults remain unchanged.
The question's extra schema structure grows canonical memory-schema bytes from
3,198 to 3,950; the common system prompt shrinks to 7,961 characters. This overhead
still competes inside the same final request/count limits, not a larger input budget.
To fit that prompt bound, explicit post-image and per-turn three-part-plan wording
was condensed to reconsidering claims after edits and optional updates; its effect
on model behavior was not tested.

## Saved-log method

The operator [replay](../../diagnostics/evidence_handoff_replay.py) reads all 75
saved handoffs from the 20-run `plmini20live02` audit. It reconstructs the original
selector from each pre-boundary journal prefix and checks exact equality with the
saved source selection before applying the candidate selector. It uses only public
observations, no new workspace execution or evaluator output for selection.

Historical runs did not declare the new question references. The frozen surrogate
is the first two distinct source citations from retained current notes, traversed
in reverse retained order. No future action, later read or outcome determines the
selection. This is a selector test; model focus exposure is `NOT_EXPOSED`.

Each candidate is composed through the runtime public-state/input path. The replay
checks delivered source identity, exact reference-level omissions, retained-character
bounds, mutation-protected lines, and absence of cross-segment reasoning. Repeated
lines across snapshots count as separate occurrences. It does not estimate saved
rereads or execute the saved next action. Remote token counts are `NOT_RUN`.

Evidence root: `C:/pt/analyses/evidence-handoff-20261017-v6`. It contains a
hash-chained `runs/run_dev_handoffreplay.jsonl`, frozen protocol/source hashes,
`read-manifest.json`, `results.json`, `summary.json`, and 75 composed public inputs.
All 97 input files were rehashed unchanged. Earlier failed operator attempts and
the preceding successful selector run remain separate external records.

A separate frozen tool-focus surrogate takes the first two distinct verification
result citations from retained notes in reverse order, allowing historical evidence.
It is never combined with the source-focus selection. Three eligible boundaries
(row 5 sequences 111/125 and row 9 sequence 167) deliver all three declared probe
results, with original execution flags, `historical` currency and
`behavior_coverage=not_assessed`. Source retention is unchanged in this separate
body-delivery test. Full request/token admission is not claimed for offline inputs;
the fake-provider tests cover the bounded admission/fallback path.

## Retention and displaced information

| Measure | Original | Candidate |
| --- | ---: | ---: |
| Exactly reconstructed boundaries | 75/75 | 75/75 |
| Declared source-line occurrences delivered | 816/877 | 877/877 |
| Additional delivered lines | — | 61 |
| Previously delivered lines displaced | — | 68 |
| Boundaries with a changed source selection | — | 2/75 |
| Maximum retained source characters | 24,000 | 24,000 |

Both changed selections are astroid row 13:

| Saved boundary | Preserved declaration | Displaced source | Retained characters |
| --- | --- | --- | --- |
| 303, input-token limit | `builder.py:122-126`, 0/5 → 5/5 | `builder.py:9-11` | 23,948 → 23,945 |
| 476, completed followup | `builder.py:110-170`, 5/61 → 61/61 | `manager.py:162-208,215-229`; `astroid_manager.py:1`; `interpreter/_import/spec.py:35,60` | 23,997 → 24,000 |

The later 110–170 reference already existed in a note at boundary 476. It was not
inferred from a future read. At boundary 303 only five cited lines are preserved:
this does not preserve the whole branch or establish that a reread was avoidable.

At boundary 476 the displaced `manager.py:199-202` includes the `PY_NAMESPACE`
branch and `_build_namespace_module` return. That is potentially relevant comparison
evidence for the package-loading hypothesis, not harmless boilerplate. Fourteen
mutation-protected lines remain, but protected mutation state is not all evidence
needed for reasoning. This cost prevents claiming an overall context-quality gain.

SQLFluff-2419 row 20 remains unchanged at all three saved boundaries. It has no
eligible surrogate source references, so it is a no-change control, not proof
that the new focus mechanism was used effectively.

## Interpretations and remaining omissions

All 47 retained note occurrences preserve their prose as model interpretations;
36 have complete cited deliveries and 11 are explicitly incomplete. For example,
row 5 still carries a pre-edit `iam.physical` explanation, with historical and
undelivered probe evidence. The runtime does not rewrite it as a current observation
or decide whether the explanation is true. These 11 omissions are not newly displaced
source lines; the frozen surrogate does not pin every old tool-result citation.

The replay contains no concern closure occurrences, so its coverage of
`closed_by_model` is `NOT_EXPOSED`; dedicated tests cover that projection. Printed
false probe values, healthy execution, generic suite PASS, original truncation,
historical results, and missing result bodies remain distinct. A weak model closure
can still cause a closed concern to be evicted later. Unregistered purposes in free
plan prose and good focus selection remain outside the mechanical guarantee.

## Validation and decision

Final focused validation passed: 63 reference/model-view/wire/check-review tests in
31.48s and 10 fake-provider delivery/fallback/recovery tests in 78.71s. Earlier
focused groups passed 38 tests in 3.92s and 56 owning projection tests in 43.46s.
The fake-provider tests block network dispatch. Ruff and five documentation checks passed.

The first full suite finished with 5,096 passed, 54 failed, 12 errors and 19 skipped
in 3,992.57s. That run overlapped implementation changes and is not a clean result
for one frozen tree. Remaining failures included obsolete wire/projection assertions
and a reproducible diagnostic-fork defect: a prefix ending at segment commit now
also inherited the source request's count receipt. A changed diagnostic request
correctly rejected that mismatched receipt. Both checkpoint readers now retain the
prepared segment only before the source turn's count; a regression assertion checks
that no corresponding count is inherited. The runtime's uncertainty stop remains.
Rerunning all initially failing functions and their parameter cases produced
133 passed and three failed in 350.98s. Two remaining assertions needed current
schema/prompt values. The third found that delivery inventory was being resolved
even when no note/question/concern cited evidence, imposing unrelated source
validation on a navigation-only projection. Inventory is now requested only for
actual evidence owners; the existing navigation regression and a new no-owner
test pass. Those remaining cases are included in the final 63-test group above.
There are no unresolved observed failures. The full suite was not rerun after
these corrections, so this record does not claim a clean full-suite result for the
final tree. Rerun logs retain both failed attempts and successful corrections.

Final ordinary mock smoke `run_dev_f1af116420f54e52` reached `EVALUATOR_PASS`: four
mock model turns, five tools, one edit and zero cost. Its state root is
`C:/pt/analyses/evidence-handoff-20261017-final-mock`; safety remains `NOT_RUN`.
Final segmented smoke `run_dev_4b1f842c39304afc` also reached `EVALUATOR_PASS` with
two prepared/committed segments and the same counts. Its root is
`C:/pt/analyses/evidence-handoff-20261017-final-segmented-mock`.
No real provider/count call, Docker call, new live solve or paid evaluation ran.

Implemented selection and honest omission labels are supported by offline evidence.
The result preserves the decision to keep timing and budgets fixed. It does not
establish better repairs, fewer rereads, or stronger behavioral coverage. The
remaining question is whether model-selected references preserve the right competing
evidence in actual work; this record neither schedules nor authorizes a paid run.
