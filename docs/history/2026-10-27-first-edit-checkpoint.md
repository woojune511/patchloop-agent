# First-edit checkpoint and correction-time admission

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: implementation, local validation and controlled-trial preparation
- Origin Date: 2026-10-27
- Verification Status: IMPLEMENTED / LOCALLY TESTED; live NOT_RUN
- Baseline: `2f0518ba`, following the [caller-source trial](2026-10-27-dependency-source-results.md)

## Problem and decision

Caller acquisition is no longer the observed bottleneck in the last trial: the
model obtained the full public caller, reproduced F0010 and executed an untruncated
helper. The next response exhausted 40K output without an edit. A correction was
then dispatched with about six usable seconds after reserving original-call check
time. That call has unknown usage; the old allocation stays closed. Its exception
class was not logged, so timeout remains a supported explanation, not an established
exception diagnosis.

Two distinct questions follow. A known operational defect is admission of a
correction with plainly insufficient time and missing transport diagnostics.
The unresolved model question is whether repeated public context burdens the first
edit. The failed request already offered only replace/stop and contained five public
messages, without opaque reasoning. Another tool or smaller edit schema would not
address those observations. Context duplication is a hypothesis; diagnosis quality,
decision difficulty or model response variability remain plausible alternatives.

## Implemented contracts

`exception_frame_repair.run_model` now checks a configurable positive correction
time floor (30 seconds by default for the opt-in repair cycle) before counting and
again immediately before generation. It holds the originally offered original-call
time reserve through cost narrowing. Below the floor, it returns
`CORRECTION_TIME_UNAVAILABLE` without dispatch or correction-quota consumption.
This is an admission floor, not a guarantee that 25K output can finish, and it does
not shorten the ordinary generation timeout to promise later correction time.

Input-count and provider events record phase, request/call identity, actual timeout
and elapsed time. Exceptions record an allowlisted class, with unknown classes
mapped to `OtherException`; messages and response bodies are not logged. Count,
transport or billing uncertainty still stops every remaining condition. Legacy
non-cycle profiles keep their earlier time-admission behavior. Production defaults
are unchanged.

`first_edit_checkpoint_source` seals the completed public helper at sequence 113
and the following pre-generation request at sequence 120 in the prior journal.
It checks the journal chain, request/artifact bytes, seed diff and helper exchange.
It reads user, public handoff and public exchange bodies only, never opaque parent
history or subsequent failed generations. Public workspace spans are registered
again against the restored candidate, including all 14 unique observed spans;
dependency source remains read-only. Historical action IDs remain evidence, not
pending actions or reusable execution authorization.

`public_context_dedup` retains every unique public fact and source line. Repeated
JSON values are stored once in a definition table; overlapping source spans refer
to ranges in a bank keyed by scope, path and file hash. Conflicting same-pin lines
are rejected. Expanding the encoded object reproduces the original JSON exactly.
This is deterministic serialization, without summarization or source selection.

## Controlled question and scope

`first_edit_checkpoint` prepares A=full duplicate public evidence and B=lossless
reference representation. Both start from the same saved post-helper candidate,
not from the beginning of exploration. Both remove only obsolete budget/correction
metadata, receive the same new prompt and fresh allowances, and retain completed
public exchanges rather than redispatching opaque state. After expanding B, the
entire first requests must equal A, including tools and generation settings.

- Astroid-1333, `dev-train/current-dev20/13`, official=false; same seed diff.
- `gpt-5.4-mini-2026-03-17`, xhigh; repository `.env`.
- A then B, once each; $1.20 per condition and $2.40 invocation cap.
- Two ordinary responses, one protocol correction, two model-tool actions and
  one accepted new edit. No new helper or original-call selection requests.
- Input 60K, output 40K/25K; fresh model/intermediate-check deadline 600 seconds.
  After an edit, host original checks allow fresh baseline plus candidate (two
  actions, 60 seconds each). Return the result before the final model response.
  Final public controls/regression and isolated evaluation each have 390 seconds.
- SDK retries zero; exact input count immediately before dispatch. Stop all
  conditions on count/transport/billing/execution uncertainty. Never repeat a
  started condition or spend the old allocation's remaining balance.

The prepared evidence body is 179,749 canonical JSON characters in A and 114,684
in B (36.2% fewer). The source bank contains 12 files and 961 unique lines, with
57 repeated-value definitions. Full requests are 198,061 and 128,246 characters.
These are offline character counts, not model token measurements. No unique source,
negative observation or original failure was dropped and no known operator fix or
private evaluation material was added.

## Interpretation and decision criteria

Record actual counted input, first valid edit, invalid requests, output exhaustion,
correction admission, time and settled/unknown cost. For any edit, separately record
whether F0010 disappears with original-call identity preserved, whether public
controls/regression pass, and isolated task acceptance and safety. A tool call or
submission alone does not establish repair.

If B produces a valid first edit while A exhausts output under the controlled
conditions, that supports further investigation of context representation. The
reference format also changes reading work, so this is not a pure token-length
effect. If both fail despite usable time, duplication is insufficient to explain
the first-edit bottleneck; do not respond by adding another prompt gate. If an edit
fails the original caller, use the public changed-path evidence to assess the
repair hypothesis. Both succeeding would weaken the claim that duplicate context
alone caused the preceding failure and leave fresh time/response variability as
alternatives. One pair cannot establish statistical or general repair gains.

This is a fresh saved-evidence trial with new budgets, not a literal resumption or
fresh benchmark solve. The historical helper output is supplied as evidence; new
verification receipts are obtained after editing. The known operator repair is
excluded. No cross-run memory or held-out tuning is enabled.

## Validation and execution boundary

Focused validation: 112 PASS in 71.16 seconds, including first-edit feedback,
correction admission at/below the floor, time consumed by counting, retained
verification reserve, safe exception logging, lossless expansion, checkpoint
tampering/cutoff, source registration and whole-pair uncertainty stops. Receipt:
`C:/pt/tmp/firstedit-focus27.xml`. No provider or target execution.

Quick suite: 472 PASS in 116.57 seconds, including isolated mock evaluation.
Receipt: `C:/pt/tmp/firstedit-quick27.xml`. Ruff and whitespace checks PASS.
Both validation selections finish under two minutes; the quick suite already
contains mock smoke, so it was not repeated separately.

A real saved-workspace restoration verified all 14 observed source anchors and
the unchanged seed, with a fresh two-action model allowance. Existing pinned
images passed identity inspection. Only public source reads ran; provider,
input-count, credential-read and target-execution counts were zero. Receipt:
`C:/pt/first-edit-checkpoint-restore-preflight-v1/summary.json`.

New paid execution requires a sealed manifest, read-only preflight and exact scope
approval. Local scripted model/check receipts do not establish live model repair.
