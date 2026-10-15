# isort I2: why revision did not reach an edit

Date: 2026-10-15. Saved-input/source analysis only, official=false.
No new model, input-count, metadata, diagnostic or evaluator execution.
The [closed I2 result](2026-10-15-isort-table-result.md), frozen design and raw
grades remain unchanged. Runtime and default policies are unchanged.

The public sequence narrows the failure to action selection after recognition:
the model recognized a current counterexample, reopened its behavior as an
untested question, then returned to the same implementation investigation.
Long model-response waits exhausted the fixed solver time before any edit.
Loss of the original diagnostic at a handoff is a plausible contributor, but
the revised conclusion and relevant source survived. This does not establish
a general memory failure, a tool defect, or a causal benefit from retaining more
context. The unreturned fourth response cannot reveal what action was intended.

## Evidence and comparison scope

The source is `C:/pt/isorttablelive01/I2/runs/run_dev_49397fa9568d4b80.jsonl`,
hash `sha256:d401b250d1953c4212af82e29b4cd39e4ba5d76fdb2b079c2d9580d48d026a57`.
The four actual prepared requests are at events **344, 363, 377 and 394**;
their completed public decisions are **352, 369 and 383**. The fourth request
has no recorded response. Public tool arguments, returned observations, working
plans and notes are evidence; encrypted reasoning is not interpreted.

The audit validates request/artifact hashes and the journal chain, reconstructs
the public state from each actual input, resolves source references only from
delivered public exchanges, and compares timestamps. Runtime files match the
execution commit `2c594f0eeef10b8a9fea3a005730aea1bbc9d987`. No target code is
imported or executed to infer behavior. Existing receipt outputs are compared.

## The question changed back from implementation to behavior

At **352**, the model says the diagnostic contradicts a `type: ignore` text
special case: it fixes the opening-line example but hoists an item-line comment.
Its remaining question is structural: can output preserve parser-distinguished
opening and item comments before flattening them into `wrap.line` input?
The plan at **355** and open question at **354** record that revision.

The following searches locate no `def with_comments` in `isort/output.py`, and
locate only the declaration of `add_to_line` in `isort/comments.py`. They do not
answer the helper-body question. The useful unresolved fact remains how that
helper and its caller handle comment ownership.

At **369**, the model instead calls the item case an assumption that remains
untested and selects a two-input probe. Its plan says both unchanged outputs
would justify submission; a moved item comment would lead back to a narrower
repair. At **374**, the probe observes that moved item comment. At **383**, the
model again rejects the text rule and returns to inspecting output/comment
helpers. This is a visible return to the implementation question it had already
posed at 352, after another verification turn.

The repeated verification is **not an identical execution**:

| Dimension | Delivered operator diagnostic | Model-authored probe |
| --- | --- | --- |
| Candidate | Seed diff `6edb32a6...` | Same seed, no intervening edit |
| Type-comment inputs | `type_opening` and `type_item`, plus two plain-comment controls | Exactly the same two type-comment strings, byte for byte |
| Configuration | `Config(profile="black")`, line length 88, trailing-comma splitting true | Explicit line length 79, parentheses, trailing comma and `VERTICAL_HANGING_INDENT`; no black profile |
| Checked setup | Recorded original config and public source import | Four supplied config values match; no claim of checking every config field |
| Observed type-case outputs | Opening case unchanged; item comment hoisted | Exactly the same two output strings |
| Other evidence | Parser categories, text/count, position and import AST for four cases | Exact-output assertions for two cases; no parser observation |

The new configuration adds coverage, so calling the entire probe pointless
would be too strong. However, the public basis does not cite the 79-versus-88
configuration difference or distrust of the supplied diagnostic as its reason.
It describes the already observed ownership problem as untested. It supplies
no new observation about the helper responsibility that the previous plan
identified as the implementation uncertainty.

## What the handoffs removed and retained

| Actual input | Operator packet | Native items | Plan revision | Displayed seconds left |
| --- | --- | --- | --- | --- |
| 344 | Complete program, receipts and four-case table | 8 | 15, original plan | 269 |
| 363 | Absent from the entire input | 0 | 16, explicit counterexample and structural repair question | 197 |
| 377 | Absent | 3 | 17, item behavior reopened as untested | 109 |
| 394 | Absent | 0 | 18, counterexample and structural question again | 56 |

The transitions at **362** and **393** are `major_result_reviewed`, not token
overflow. The first follows review of the inherited edit/check at **332/337**;
the second follows review of the new probe at **374**. The ordinary segmented
policy quotes the latest completed public batch and rebuilds current state,
dropping older native reasoning and exchanges. The I2 connector injects its
operator packet only before the first generation, as frozen in the design.
It does not register those operator observations as ordinary tool results.

Consequently, input 363 has the latest two search records but no original
table, configuration, case inputs, actual outputs, parser observations or
operator receipts. It still has the revised plan explicitly saying that the
item-line result contradicts the text rule, the new open question, and the
existing parser note. `findings` and `verification_updates` in the new memory
updates are empty; there is no new durable observation note. The existing
verification catalog then contains only the historical failed regression.
After the agent probe, its current failure is retained in that catalog.

This is a reduction from a concrete executed observation to an unverified
model-authored plan, not complete loss of the conclusion. Both facts matter:
raw-evidence loss could weaken continuity, while the retained contradiction
rules out the claim that the next model had no information about the failure.
The record cannot identify which fact determined the second response.

The completion guidance is identical in all four inputs. It states that
regression PASS makes submission eligible, not that it proves untested behavior;
it offers a probe only for a concrete remaining uncertainty and requires no
extra experiment. The system already says to reuse current facts and avoid
restating answered questions. Another generic reminder would duplicate this
guidance. The brief planning policy is unchanged; the model itself updates the
plan rather than being forced to preserve the original keyword hypothesis.

One small prompt difference is preserved in the audit: the first normal handoff
regenerates the current generic system text, adding `run_tests` to its tool-family
sentence relative to the historical seed. All later system messages match.
No `run_tests` tool is supplied or called, and this change contains no retest
instruction. First-input I1/I2 parity remains intact. Do not claim every later
system byte was identical to the historical first input.

## Source inspection and time spent

The failed definition search has a concrete explanation: `with_comments` is
an import alias, `from .comments import add_to_line as with_comments`, at
`isort/output.py:10`. That line was absent from the first three actual inputs.
Literal search for `def with_comments` therefore correctly returned no match.
The model selected an overly specific definition query; no broken search
behavior or missing tool was observed.

The later read reveals that alias and the full 35-line comments module. It
adds 110 source lines not visible in the preceding request, so it is useful
inspection. The body shows `add_to_line` returns a single string. Meanwhile,
`output.py:392-452`, including the straight/nested comment collection and
`with_comments`/`wrap.line` calls, and all 153 lines of current `wrap.py` remain
visible in every request. Pruning some other lines did not remove this repair
site. Source availability alone still does not prove the model could construct
and validate a correct replacement.

| Activity | Observed wall time |
| --- | --- |
| First model response, selecting two searches | 67.340 s |
| Second response, selecting the new probe | 80.764 s |
| Third response, selecting two reads | 48.822 s |
| Fourth request, no response before timeout | About 53.2 s; dispatch-to-terminal upper interval 53.379 s |
| Two parallel search actions | 0.104 s from first start to last finish |
| Probe action | 3.212 s action window; 2.870 s in its execution receipt |
| Two parallel read actions | 0.175 s from first start to last finish |
| Two handoff-adjacent preparation windows | 1.999 s and 2.354 s; 4.353 s total |
| Four input-count windows | 4.020 s total |

Completed provider waits total **196.925 s**. Including the timed-out request,
approximately **250 s of the 281.104 s invocation** is provider-response wait.
These intervals include service and transport, not separately measured internal
reasoning time. The handoff windows run from prior batch completion to the next
prepared request and include all intervening local preparation; they are not
isolated segment-function profiles. Direct handoff overhead is not the dominant
wall-time cost. Its possible effect on later action choice is a separate issue.

From the first search batch ending to the probe batch ending, **87.995 s**
elapse. The model then still needs the helper read and another response to
attempt a repair. This explains the lost time opportunity; it does not prove
that omitting the probe would have yielded a correct edit or submission.

All actual inputs have `mutation_readiness=ready_to_attempt`; edits are offered,
two edit slots remain, and no edit is attempted or rejected. The last input has
three model calls and thirteen tool actions left but only 56 displayed seconds.
Its horizon warns that another unchanged read could close editing, while editing
is still available on that turn. The fourth request times out. Call/action
arithmetic does not guarantee enough wall time for three more responses.

## Decision and smallest possible change

Preserve the current baseline. This audit establishes no violated read, search,
mutation or handoff contract. The loss follows the explicit first-input-only
operator-feedback design and the existing lossy segment policy. No general
pruning failure, mandatory-plan trap or insufficient tool allowance is shown.
The final missing response also prevents attributing a particular fourth action.

The most specific change worth considering, if separately chosen later, is
**observation continuity across the handoff**: retain the bounded public input,
configuration, observed result and candidate identity as separately labelled
operator evidence while the candidate remains current. Distinguish that observed
behavior from the still-open implementation question; after an edit, mark old
observations historical. Preserve provenance and do not turn derived controls
into hidden verdicts, registered check failures or mandatory submission gates.
This is a data-delivery candidate, not a new instruction to announce revision.
It is not implemented here and has no demonstrated repair benefit.

Do not adopt a blanket ban on rechecking: the new config shows why exceptions
matter. Do not add a forced-edit gate, a new plan template, cross-run memory,
larger context, more tool allowance or an automatic time extension on this
evidence. Better identifier lookup could avoid the unsuccessful definition
search, but does not justify changing literal search semantics. Lower reasoning
effort or a larger time allowance would be a different experiment, not a repair
of this closed invocation. No further experiment is queued by this audit.

## Audit artifact and preservation

`C:/pt/isorti2analysis01/analysis.json`, with append-only journal
`runs/run_dev_isorti2analysis.jsonl`, records exact inputs, public responses,
source coverage, config/input/output comparisons and timing calculations.
The artifact is
`sha256:c34c4089441e4fd40d64c4f93f9484d547c3a275a923a59531d0d08643c74b21`.
The read-only audit corrected two initial assumptions against saved evidence:
the system-message enumeration difference above, and 112 newly visible lines
versus 110 from actual new reads (two old lines returned through retention).
Original scripts and their refinement records remain separate.

I2's raw D UNKNOWN and U/P/I NOT_RUN, its unsubmitted seed, and unknown fourth-call
usage are unchanged. No retrospective U grade, corrected probe, extra model
response or final evaluation was produced. Only this follow-up, the history
index and the active status summary change; prior history and generated
execution artifacts remain immutable.
Five documentation-layout/link checks passed in 0.13 s; `git diff --check`
passed. Runtime tests and mock smoke were not repeated for this documentation-only
audit. The user's existing AGENTS.md change is preserved.
