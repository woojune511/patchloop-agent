# Astroid output exhaustion and panel stop audit

Date: 2026-10-16. Offline follow-up to the [closed D/E panel](2026-10-16-purpose-stop.md).
Provider calls, evaluator runs and candidate edits in this investigation: **zero**.
The original allocation remains closed at USD 1.47315645; all original outcomes,
public classifications and artifacts remain unchanged.

Two findings have different certainty and ownership. The astroid row exhausted its
25,000-token output ceiling twice before producing a tool call, after investigation
had failed to settle on a repair and its exploration budget had closed. A context
handoff discarded the first incomplete response's encrypted reasoning before the
second attempt. These observed conditions support a decision/continuation difficulty;
they do not reveal what the model privately reasoned or prove a unique cause.

The whole-panel stop has a reproducible implementation cause: the batch worker
excludes `INCOMPLETE_RESPONSE` from its acceptable terminal list and converts it to
a shared stop, even when usage is settled and the runtime did not request one.
That is broader than the written protocol's uncertainty/identity/cleanup stop
rationale. Ending this astroid row was appropriate under its correction limit;
ending the remaining twelve independent solves was not required by the observed
failure. This is a batch-policy design mismatch, not billing uncertainty.

## Evidence question and boundaries

The problem matters because one unsubmitted baseline row prevented all E exposure,
making the intended mechanism and behavior comparison unavailable. The user asked
for actual-prompt/action diagnosis and whether the panel-wide consequence was needed,
with no further paid execution. This audit checks the exact frozen D checkout
`fcfa496dfb57f7e0d79616e5389fac034cfbc6b2`, its actual requests and the frozen launcher;
it does not infer behavior from today's prompt or from E's unexecuted instructions.

Run: `A1-13`, `run_dev_d62784f22316450d`. Original journal SHA-256:
`cd625505541e511c057586e21fb8722a6ddf6d059799286673cdfd5892d19af2`.
Its hash chain, request-artifact hashes and sealed public-extraction identity agree.
There are 37 prepared/counting requests but **35 dispatched generation requests**;
the two unsubmitted preparations are not extra model calls. All 53 actions completed
successfully at the tool level. This says nothing about whether a search answered
the right question or a probe reproduced the reported defect.

The actual model was `gpt-5.4-mini-2026-03-17`, xhigh, `tool_choice=required`,
`store=false`, desired/actual output ceiling 25,000 and segmented-v1. The relevant
limits were 40 generation calls, 100 actions, four accepted edits and USD 1.20.
Both failed calls retained the full 25,000 ceiling; cost admission did not lower it.
Only public actions, public decision annotations, request text and usage metadata
were inspected. Encrypted reasoning was measured by size, never decrypted or summarized.

## Before the two incomplete responses

| Calls / events | Observation | What it establishes |
| --- | --- | --- |
| 1-16; initial plan 16 | Searches/reads across discovery, manager, builder, namespace specs and tests; no edit. | The repair owner remained unresolved. |
| 17; probe 266/result 267 | A temporary missing-init tree is passed to six `modutils` calls. `file_info_from_modpath` returns PY_NAMESPACE; `file_from_modpath` returns None. | Discovery behavior for those supplied inputs; not the reported CLI failure. |
| 18-30; plan 292 | Investigates namespace materialization, then returns to modpath validation and callers. | The probe narrowed a hypothesis but did not reproduce the failing loading path. |
| 31/action 451, 32/action 464 | Public basis mentions patching `check_modpath_has_init`, then finding a regression slot for `modpath_from_file`. | A tentative edit direction existed, but no edit or updated committed plan followed. |
| 33; request 472, actions 482/483 | Last inspection opportunity; repeats `PY_NAMESPACE` and `__init__.py` searches. Both are cache hits with no new covered lines. Plan 481 returns to finding a later namespace materialization bug. | Still searching for the repair owner when the last available inspection ends. |
| 34; request 488/result 494 | Only `replace_text` and `stop_task` remain; 25,000 reasoning-output tokens, zero tool calls, incomplete. | First output-cap failure at the transition to execution-only choices. |
| 35; correction 496, handoff 497, request 498/result 503 | Same tool choices and output cap; another 25,000 reasoning-output tokens, zero tool calls. Terminal 505 ends the row. | The allowed correction did not produce an action. |

The public issue reproduces `pylint src/project` from the repository root. The
probe instead calls discovery helpers directly, often with `[src]` as the search
path. It does not call that CLI, manager loading or `file_build`, and does not
observe the reported F0010. Its success cannot establish the cause of that failure.
The public plan nevertheless narrows to a step that supposedly turns a valid
namespace result into a file load. This remains a hypothesis, not an observed chain.

There was relevant counterevidence in the delivered source. The manager's
PY_NAMESPACE branch returns `_build_namespace_module`; the builder helper returns
`nodes.Module(name, doc="", path=path, package=True)` without an explicit file-open
operation there. Both snippets were still present in the actual requests for calls
34 and 35. This does not prove the whole loading path correct, but weakens an
unqualified claim that those observed helpers themselves synthesize the bad file load.
The model never ran a focused loading-path experiment to resolve that uncertainty.

Whole trajectory: 35 searches, 17 reads and one probe; no edit, public check or
finish. Seven search actions repeat an earlier exact query/glob, across six keys.
Repetition alone is not a failure criterion, but the final two searches reproduce
already-delivered results while the plan still asks which branch owns the error.

## Actual prompt, budgets and context handoffs

The actual D system prompt already says to limit small-experiment conclusions to
their observed inputs, avoid rereading merely to restate an answered question,
and try a supported small repair when only its outcome remains uncertain. It also
says `ready_to_attempt` establishes editable source evidence, not a correct solution,
and allows `stop_task` when no offered action supports progress. This was not an
instruction to keep searching forever or to produce a successful repair at any cost.

Call 33 explicitly received `exploration_state=last_opportunity`, one remaining
exploration turn, and the list of tools closing afterward: reads, searches, checks,
probes and selected tests. Call 34 received `closure_reason=completion_horizon`,
seven remaining model calls, 47 tool actions, four edits and approximately 973 solver
seconds. Seven model calls were reserved for the protected completion path, so an
additional optional inspection could not leave that reserve intact. Minimum
successful edit/check/finish still fit in three calls. This is the current completion
budget policy, not the older fixed inspection-lease rule.

The current completion message was:

> The current candidate needs a repair. Use replace_text for a supported edit; available anchor evidence does not establish a correct solution.

The correction delivered in call 35's `recent_attempt_result_next_question` begins:

> Provider response was incomplete (max_output_tokens). Return one valid dev-head tool-call shape.

It then explicitly names `needs_mutation`, `replace_text` and `stop_task`. The schema
and current allowed-tool list agree. No instruction to call an unavailable read tool
was found in this correction. The general advisory about investigation is not evidence
that a forbidden tool was actually attempted; neither failed response emitted any tool.

Two handoffs are relevant:

1. Before call 33, input-size management starts a new segment at event 471. The
   earlier private continuation is absent. The exact call-31 public basis about
   `check_modpath_has_init` is also absent from this request, while call 32's
   `modpath_from_file` test rationale remains in the quoted last exchange. The older
   namespace plan persists. This is partial loss of a tentative direction, not proof
   that all source or the task was lost; the next plan choice is still model-authored.
2. After call 34, the encrypted reasoning item's 345,804 bytes exceed the configured
   262,144-byte per-item limit. Event 497 records `encrypted_item_bytes`; call 35
   starts a fresh segment with **zero reasoning input items**. It keeps current source,
   the probe note, plan/predecessor/reason and correction, but does not continue the
   preceding 25,000-token reasoning item. The public note still asks which branch
   materializes `__init__.py`; no new repair hypothesis emerged from the failed call.

Thus the second attempt received the same unresolved repair choice and a format
correction with no new execution evidence. Lost private progress is a plausible
contributor, but its content is unknown. The record cannot establish that preserving
that item, raising its byte cap, increasing output tokens or lowering effort would
have produced a valid repair. Those would be separate interventions.

| Usage | Calls 1-33 | Call 34 | Call 35 |
| --- | ---: | ---: | ---: |
| Output tokens | 45,230 total; median 1,028; max 5,077 | 25,000 | 25,000 |
| Input tokens | Varied; call 32 was 59,593 | 25,971 | 23,577 |
| Reasoning-output tokens | Varied | 25,000 | 25,000 |
| Tool calls in response | 53 total | 0 | 0 |
| Provider incomplete reason | None | max_output_tokens | max_output_tokens |

The last two calls alone cost USD 0.25844580 and consumed more output tokens than
the preceding 33 combined. These are output exhaustion receipts, not an inferred
context-window overflow. Earlier success below this ceiling does not prove that a
repair response could fit, but it also does not justify declaring 25,000 generally
too low. The strongest supported diagnosis is unresolved repair selection meeting
the exploration cutoff, followed by a fresh-segment correction that still produced
no action. Causal shares between model difficulty, hypothesis persistence and context
retention remain unmeasured. E's unexecuted guidance cannot be blamed or credited.

## Why one row stopped the panel

The failure propagates through three layers:

1. Frozen `patchloop/dev/runner.py` stops the row after one consecutive correction
   has already been consumed (`4990` onward). It records `INCOMPLETE_RESPONSE`
   without setting the invocation-wide `stop_remaining` flag. The returned result
   has no such flag. Ending this unsuccessful row is consistent with its contract.
2. `diagnostics/parallel_dev_batch.py:175` checks an allowlist containing evaluator
   PASS/FAIL, AGENT_STOPPED, LIMIT_REACHED and COST_CAP_REACHED. INCOMPLETE_RESPONSE
   is absent. Consequently `ok=false` calls `stop_workers()` despite settled usage;
   the batch loop also sets its shared stop on any non-ok worker result.
3. Frozen `C:/pt/purpose16prep01/run_comparison.py:407` rejects a non-ok row unless
   its assessment disposition is `task_limit`. The row never reached assessment;
   the parent also observes the stopped wave and declines E1, E2 and D2.

All four D1 rows were already admitted before astroid ended. The batch classification
therefore prevented twelve later rows, including all E exposure. The worker's `ok`
and the parent's local variable `known` mix a usable per-row outcome with uncertainty;
neither variable is a synonym for billing completeness.

The evidence has none of the written [protocol](../../.agent/verification-purpose-comparison.md)'s
shared stop triggers: all 35 provider starts have settled finishes, all 37 input
counts complete, costs reconcile within the cap, the probe reports `cleanup_failed=false`,
and all admitted tools finish. There is no evaluator running for this unsubmitted
row, completed-grader disagreement, identity drift or transport exception. The
runtime's shared-stop flag is absent. The final accounting explicitly reports both
`billing_known=true` and `counting_known=true`.

The written protocol permits a known row limit to close that row only and separates
NOT_RUN from quality judgments. It does not explicitly enumerate this protocol-failure
case; that omission does not turn a settled local failure into a shared hazard.
The implementation's blanket allowlist is broader than the stated stop rationale.
A quality criterion becoming unavailable also does not implicitly cancel the
separate mechanism/behavior questions; no such futility rule was prespecified.

Provider-free tests execute the exact frozen worker with an intercepted `run_dev`
return and the actual settled accounting. With identical accounting and no runtime
stop flag, INCOMPLETE_RESPONSE stops the batch, while LIMIT_REACHED and AGENT_STOPPED
do not. The actual wave is rejected by the parent. A clearly labeled hypothetical
row-local classification is accepted with the same cost; making billing unknown
still rejects it. Five tests passed in 2.11 seconds, with network access blocked in
the worker cases. These tests reproduce existing behavior; they do not implement a fix.
The batch source bytes also match current HEAD, so this is not only a retired-path issue.

## Decision and follow-up boundary

The previous result accurately reported what the frozen code did. This follow-up
clarifies that following those bytes did not make whole-panel stopping necessary.
The operator preparation missed the mismatch: its tests covered limits, uncertain
billing, grader disagreement and missing results, but not a fully accounted
INCOMPLETE_RESPONSE with no runtime stop. Frozen results are preserved rather than
retroactively relabeled or resumed.

A minimal future correction belongs at the batch outcome classification: retain
this row as an unsubmitted local generation failure while admitting other already
authorized independent rows only when accounting, cleanup and runtime stop evidence
permit it. This must not become blanket acceptance of unknown transport, continuation
corruption, unconfirmed cleanup or unrecognized terminal states. Row failure, batch
continuation and independent evaluation need separate meanings.

No runtime/helper fix, token-cap change, new prompt, paid retry or resumed allocation
was performed. The stronger model-side explanation still requires separating repair
selection from handoff loss; adding another generic review instruction is not justified
by this trace alone.

Evidence root: `C:/pt/purpose16diagnosis01/`. `trace-summary.json` binds all dispatched
requests and actions; `request-{33,34,35}.public.json` preserves public request text
with encrypted content replaced by byte counts; `delivery-checks.json` records exact
phrase/source presence. `test_stop_scope.py` and `stop-scope-tests.xml` reproduce the
batch issue; `runs/run_dev_purposediagnosis.jsonl` binds offline outputs and closure.
The closing receipt verifies the original 9,155 protected evidence/source files and
records documentation validation. Current status and the mutable history index link
this follow-up; the earlier closed report, protocol, judgments and logs are unchanged.
