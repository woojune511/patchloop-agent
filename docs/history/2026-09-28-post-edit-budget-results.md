# Unhinted post-edit continuation: completed, semantic repair not discovered

Date: 2026-09-28. official=false. One selected continuation, not a fresh solve or A/B.
See [preparation](2026-09-28-post-edit-budget-preparation.md) and
[contract](../../.agent/post-edit-budget-continuation.md).

## Execution and result

The user authorized the exact prepared manifest with a fresh $3.00 cap, repeat=1,
`original-toqito-1538`, `gpt-5.4-2026-03-05` xhigh / 25,000 desired output tokens,
and the repository `.env`. Collector implementation commit: `349d42c`.
Manifest: `sha256:b91d6d1aec19ad6478766a1cae21b46eee17b3de1071c076d87a2fd330658f88`.

| Measure | Result |
| --- | --- |
| Newly dispatched model calls / input counts | 2 / 2 |
| New registered actions | `run_check(base-regression)`, then `finish_task` |
| New mutations / probes / source inspections | 0 / 0 / 0 |
| Registered public check | 14 passed, 1 already-frozen deselection |
| Submission | Same patch as checkpoint |
| Isolated original benchmark acceptance | FAIL (`EVALUATOR_FAIL`) |
| Safety | PASS |
| New settled cost | $0.2168265 / $3.00 |
| Collector elapsed time | 71.37 seconds, including preparation/evaluation |

Billing is known. No retries or subsequent paid allocation were used. The unused
$2.7831735 is closed. Restored cost bookkeeping includes $1.091299 before the
checkpoint; the branch cumulative $1.3081255 is not this invocation's new bill.
The original pilot run's non-submitted NOT_RUN result remains unchanged.

## Input and process evidence

The inherited prefix through event 139 matches the source exactly. The first actual
request equals the frozen original except the two current cost fields, `invocation_cap`
and `remaining`. Both actual inputs match their saved public state projections.
No operator observation, counterexample or new generic guidance was supplied.

At the first decision the agent had 32 model calls, 85 tool actions, three edits,
approximately 1,212 active seconds and $3 available. It chose the existing regression
check and planned to submit if that check passed. Its public plan acknowledged the
implementation had not yet verified values/semantics, but made the old suite its
remaining verification criterion.

After the check, the next actual input included the successful stdout and the
existing warning that submission eligibility is not proof of untested behavior.
Read/search/edit/probe tools remained available. It had 31 model calls, 84 tool
actions, three edits, approximately 1,178 seconds and $2.8761725 available before
that final model dispatch. The agent nevertheless cleared its open question and
submitted. It described the PASS as confirming variant validation, the new uparrow
order guard, and exercised small-state behavior, leaving only broader numerical
fallback quality untested.

Public source inspection shows a narrower scope: all selected test calls omit
`variant`, whose default remains `downarrow`. The sole explicit `uparrow` test is
the pre-existing unsupported-operation test already excluded before this pilot.
Therefore these 14 passing cases do not establish the claimed new uparrow behavior.
This scope mismatch is visible in public test source and the agent's recorded
decision; private evaluator details are unnecessary to establish it.

## Correctness evidence and limits

The submitted patch is byte-identical to the previously audited candidate:
`sha256:fdd4fa640b555cc3ef43317ec9b4b3fa2a694902f11d571f43fb48dd2a318745`.
The prior journal-bound [public counterexample](2026-09-28-toqito-public-validation.md)
therefore still applies: the patch returns 0.5849625 below a feasible 0.7715533
objective. The prior case was not rerun; exact patch identity was verified instead.
This known semantic defect and the aggregate benchmark FAIL are separate evidence.
No private failing test or evaluator internals were inspected, and no claim is made
that this public witness explains the benchmark's specific failure.

This run demonstrates that removing the immediate cost constraint was sufficient
for completion here, but did not produce autonomous correction. It does not prove
budget never matters, nor identify which prompt/plan/context mechanism caused the
decision. Existing completion guidance, inherited beliefs and selective verification
remain competing influences. It is not evidence of a general failure rate.

The next diagnostic question is whether a task-independent check of the actual scope
of passing tests changes this completion decision. If tested, hold the checkpoint,
model, tools and allowance fixed, change one generic verification-scope cue, and
measure independent discovery/correction as well as submission. Do not provide
the task formula, counterexample, or private evaluation feedback. No such follow-up
is authorized by this record, and no runtime/default guidance was changed.

## Evidence and validation

- Live collector: `C:/pt/posteditlive0928a/result.json`; hash-chained group journal
  `runs/run_dev_posteditcontinuation.jsonl` and branch `A1/runs/run_dev_33068b6e257f423a.jsonl`.
- Public process audit: `C:/pt/analyses/postedit-budget-results-20260928-v1/public-process-audit.json`;
  journal `runs/run_dev_posteditresultaudit.jsonl` binds the report and collector result.
- Audit script: `C:/pt/audit_postedit_continuation_0928.py`.

Provider-free assertions verified source preservation, exact first-input changes,
both delivered state projections, new cost accounting, unchanged patch identity,
public test call scope and the prior counterexample receipt. Documentation checks
passed. No new runtime changes, full-suite run or additional model call was needed.
