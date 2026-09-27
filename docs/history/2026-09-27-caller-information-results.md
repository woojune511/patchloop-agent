# Caller-information comparison: local action change without established quality gain

Date: 2026-09-27. Executed on collector `dcacb0d2f0ae1593e8a6d8524626c1ce27336b97`.
Every run is official=false; the allocation is closed.

## Question and fixed intervention

The [prepared comparison](2026-09-27-caller-information.md) asked whether measured
caller state changes a first repair that previously assumed caller cancellation.
The operator probe had measured a pending, uncancelled caller during callback
KeyboardInterrupt, with an explicit-cancel positive control. It was collected
after the original N1 checkpoint, not autonomously by these continuations.

The user authorized the exact frozen task/model/credential/repeat/cap manifest:
`C:\pt\analyses\caller-information-comparison-20260927-v1\manifest.json`, hash
`sha256:abfda949b2aa1d2de0ea64d05f3bea485744022e77da702c7b1ed68bc3d67da2`.
A1/B1/B2/A2 ran serially against fresh unchanged task workspaces. A's first input
was exact N1; B added the separately attributed public probe program and raw
measurements. Both retained original mutation advice, tools, encrypted history,
task/model/settings and remaining allowances. The observation was injected once,
with ordinary context construction afterward. No default runtime policy changed.

## Outcomes and first repairs

| Row | First patch and first lifecycle check | Accepted mutations | New dispatch/count | Final acceptance / safety | New USD |
| --- | --- | ---: | --- | --- | ---: |
| A1 | Caller-cancellation-only path; 4 passed, 3 interrupt failures | 2 | 5 / 5 | PASS / PASS | 0.7976785 |
| B1 | Added aborted-run_test path; cleanup timeout, case set incomplete | 3 | 6 / 7 | NOT_RUN / NOT_RUN | 0.9389390 |
| B2 | Tracked pending call and handled aborted run_test; 7 passed | 1 | 4 / 4 | PASS / PASS | 0.4056935 |
| A2 | Caller-cancellation-only path; 4 passed, 3 interrupt failures | 2 | 6 / 7 | NOT_RUN / NOT_RUN | 0.8836440 |

All first actions were replace_text, with no new inspection or probe beforehand.
A1/A2 cancelled the runner from _call_in_runner_task only when the current caller
was cancelling. Neither first patch handled the synchronous run_test escape from
a callback KeyboardInterrupt. Both public checks observed post_interrupt execution
in the function, module and task-group cases.

B1 tracked the pending future and cancelled it/the runner in run_test's
BaseException handler. B2 tracked the caller task, cancelled the runner and drained
the pending call from that handler. Thus both B first patches addressed the
uncancelled pending-call path. B2 still had a separate caller-cancellation guard;
its presence is not the failed premise because the callback path no longer depends
on it. B2's public plan explicitly said the bug was not just caller-task cancellation.
These patch/plan observations support a local uptake signal beyond delivery alone.

B1's first public execution recorded post_interrupt=0, but fixture cleanup never
completed before the case timeout. Remaining cases were not completed; the
summary's 0 passed/7 failed is not seven independently executed failures. B1's
second patch removed run_test handling and reproduced the three resumed-test
failures. Its third restored guarded pending-future handling and passed all seven
lifecycle cases; upstream regression and isolated evaluation remained NOT_RUN.
The suggested double-cancellation explanation is model-authored, not a measured
cause. There was no new diagnostic probe on any candidate.

A1's second patch passed both public checks and isolated acceptance/safety.
B2 passed both checks and isolated acceptance/safety on its first patch.
A2 later recognized the pending implicit-caller path and introduced a _run_in_loop
helper. Its second patch produced post_interrupt=0 but timed out before cleanup,
with incomplete case execution. It never submitted and was not evaluator-rejected.

## Resource outcomes and provenance audit

Total new billed usage is $3.025955 of $3.869852. The $0.843897 remainder is closed;
inherited $0.232537 per row is excluded from new spending. Billing is known for all
rows, with no count/transport/billing/cleanup uncertainty and no automatic retries.
The ordinary bounded protocol-correction path did execute for incomplete responses.

B1's last dispatch had a 177-token ceiling and returned reasoning only with
incomplete_response/max_output_tokens. A2 had a reasoning-only incomplete response
at 25,000 tokens, recovered to issue its second mutation, then exhausted a final
488-token ceiling without a tool call. These are observed output ceilings/response
shapes, not a claim about a universal model reasoning threshold. Both final
correction inputs were counted but not dispatched because minimum cost no longer
fit. B1 saw its lifecycle PASS in a generated turn, and A2 saw its last failed
check in a generated turn; each then ran out of output allowance. Do not confuse
that with the undelivered correction input or claim feedback was never delivered.

The read-only audit validated all 21 dispatched and 23 counted inputs against
saved public projections; count-to-dispatch bindings, exact first A/B hashes,
native continuation and the 58-event inherited prefix/envelope all matched.
The operator evidence file, journal, program and receipt bindings still verified.
B's observation field appeared only in the first counted/dispatched state;
ordinary model-authored retention remained allowed. First input counts were 36,637
for A and 38,716 for B, with identical 25,000 output ceilings. Added input, attention
and cost effects are part of this supplied-evidence treatment, not separately isolated.
All 10 owned new public-check containers were absent after completion. Zero new
probe executions occurred. Evaluator outputs were never fed into model context.

## Decision and next question

Both B first patches handled a path missing from both A first patches, but only
B2 solved it on the first attempt. Each arm ultimately had one accepted submission
and one resource-limited non-submission. This selected two-repetition checkpoint
diagnostic does not establish a success-rate improvement, autonomous diagnosis,
generalization, a pure numeric-state effect or a default prompt/memory policy.
Keep the working baseline. Original fresh-solve and advice-removal outcomes remain
separate, closed evidence rather than pooled fresh-task controls.

The next concrete uncertainty is B1's first cleanup timeout versus B2's completing
first patch. A bounded provider-free trace of caller/future/runner state and cancel
counts on the saved public patches could distinguish repeated cancellation from
undrained pending work. Neither explanation has yet been tested on those patches.
No fresh paid invocation or new candidate probe is part of this closure.

## Evidence locations and validation scope

- Live group/branches: `C:\pt\callerinfo0927a`.
- Audit and closure: `C:\pt\analyses\caller-information-results-20260927-v1`.
- `public-audit.json` contains public action arguments/decisions, checks, per-call
  identities, usage and projection results; `audit.py` is the saved read-only audit.
- Original input pair and operator probe packets remain unchanged; the live
  manifest binds their exact hashes and collector implementation.
- Runtime remains `sha256:e3b533ac585ea2b48d159a6f8449d3996cd991b3da73fa268dbda71f8d5230c3`.

Implementation validation is the previously recorded 33 focused tests, scoped
Ruff and mock isolated-evaluation smoke. This closure changes documentation only;
documentation/link checks are rerun and recorded in the external closure receipt.
No full pytest suite, new provider call, new public check or evaluator rerun is
performed during the audit/closure. Saved acceptance establishes those submissions,
not broad semantic coverage; the explicit-cancel same-task coverage gap remains.
