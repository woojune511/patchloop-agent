# Current status

`dev-head` is the only active coding-agent runtime. It is mutable, development-only,
and always records `official=false`. The available commands are `patchloop dev`,
`patchloop doctor`, and `patchloop task validate`; legacy Rapid and provider-backed
claim commands are absent.

## Targets and limits

- focused local validation: under 2 minutes
- default one-row live limit: 1,800 seconds
- 40 model calls, 100 tool actions, and 4 accepted mutations
- one consecutive protocol/incomplete correction and at most 4 parallel reads
- budget-only public inspection with advisory coverage/causal signals, a bounded
  two-call mutation-rejection allowance and order-independent distinct-check recovery
  reserves; legacy 24/3 counters are telemetry only
- `repeat=1` by default, 6 maximum, under one invocation-wide cost cap

## Authority

Mock execution carries no provider authority. One exact live `patchloop dev`
invocation authorizes only its declared `dev-train` task, model, credential file,
repeat count, and positive total cap. It never authorizes an image pull/build,
another task, an automatic retry after uncertainty, or a confirmatory claim run.

Repository policy alone never initiates paid work. The thirty-eight live observations below
were separately authorized. None authorized an image pull/build, automatic
Docker startup, transport retry, or additional row.

## Current implementation: explicit mutation pre-state and completed identity (v31)

A successful `replace_text` now records its completed candidate in the result's
`workspace_diff_hash`, equal to `output.worktree_diff_hash` and the mutation/post-image
diff identity. `output.baseline_diff_hash` explicitly preserves the full pre-edit diff.
The baseline comes from the original admission even when a resumed process finds the
candidate already applied. The incremental replacement's `output.patch_hash` remains
separate from both full-diff hashes. These are action-time snapshots, not a claim that
a historical result describes the workspace at later replay.

The read-only row-38 audit found the prior ambiguity in all four successful edits:
the outer workspace hash named the pre-edit diff while the inner worktree hash named
the post-edit diff. The source was actually changed and the final current-state view
was correct. This is a feedback identity inconsistency, not evidence of an unapplied
repair, and not proof of why the model ignored recheck guidance. The final candidate
remains untested. No additional stop validation, forced check, action mask, prompt,
model setting, scope or resource-limit change is introduced.

Reads, searches, probes and checks retain their existing snapshot identity. Failed
mutations retain the rolled-back workspace identity and existing typed baseline/
candidate diagnostics. Durable action IDs/inputs, source references, note lifecycle,
check invalidation and finish identity remain unchanged. Tool-surface v31 binds the
new output semantics; `dev-run-v1` and tool input shapes/order are unchanged. Older
run/envelope bytes are not migrated and saved native prefixes are never rewritten.
Implementation authorizes no Docker/provider execution, historical candidate repair/
recheck, retry/resume or row 39.

The new regression first reproduces the old pre-state-as-result mismatch, then Ruff
and all 118 focused identity/recovery/projection/completion/contract cases pass in
95.54 seconds. All 47 test files run exactly once across six fresh parallel external
roots `C:\pt\pl31-full-a{1,2,3,4,5,6}`: 717 passed, four real-Docker opt-ins skipped.
Groups pass 71/77/48/129/187/205 cases in 85.85/71.97/66.44/72.47/107.86/99.19 seconds.
The eight new cases cover LF/CRLF, sequential non-empty baselines, incremental versus
complete diff identity, admission/replacement/result crash boundaries, exact completed
replay, scope rollback/cache preservation, actual native/context delivery and unchanged
check/finish eligibility at zero edits. Runtime bytes stayed fixed across validation.
Focused validation and each full-suite group meet two minutes; the staged sequence
including smoke and audit is not claimed as a sub-two-minute workflow.

Mock `run_dev_52c7646bb0b54864` under `C:\pt\pl31-smoke-a` reaches mutation, visible
check, finish and isolated task acceptance PASS/safety NOT_RUN: four mock turns, five
tools, one accepted mutation, zero provider/count calls and zero cost. Its pre/post,
checked and submitted identities verify. Tested runtime hash is
`sha256:94cdd9067d777ba2bd2246dd8ea8fa9dbefcbba758ac886e037f1a9702950853`;
tool-surface hash is
`sha256:43e2a53673700c48b46247df8b1d91e7ce2af52b88d042f00d843128e9e5f6de`.
No model prompt or tool input changes. Row 38's journal remains hash-identical; this
local consistency correction establishes neither live rechecking nor task correctness.
Final preservation hashes match for `.env`, user-owned `AGENTS.md`, all 1,249 tracked
task/historical files and 148 prior run files; all 175 preexisting untracked entries remain.

## Previous implementation: current permissions and action-bound note feedback (v30)

The provider-free follow-up labels each observed source group with
`edit_permission=allowed|read_only`, using the same public path matcher as mutation
admission. Forbidden paths still take precedence. The label does not grant anchor
evidence, imply semantic readiness or change offered tools. No source is read to create it.

A successful mutation that expires source notes now carries `working_notes_after_batch`
even with no memory update. The notice belongs to that exact action and current diff;
later unrelated reads/checks do not repeat it. A later current view references the full
exact memory receipt already delivered in native history rather than re-emitting its
historical success/rejection body. Missing or mismatched delivery keeps inline feedback.
Canonical audit context, original receipts, prior native prefixes and durable lifecycle
remain intact. Note expiry, unknown-ID rejection and main-action independence do not change.
Tool-surface identity is v30; input shapes/order, global limits, model settings, task bytes
and action masks are unchanged. Existing envelopes are not migrated.

Row 37's read-only analysis distinguished 13 inspections that added coverage, three
zero-match searches and two covered-only inspections. One covered-only search was a cache
hit; both reread ranges were still present in the actual input. Path rejection and the
65/54-line scope failures were correct and reached the next decisions. Source groups
previously lacked adjacent permission labels, but the public constraints were delivered.
Notes first appeared at turn 23. Turn 25 changed their broadly cited source and expired
both IDs; turns 26/27 repeated those IDs despite current-state/unknown-ID guidance.
Both findings failed in each partially applied update; only other annotation fields
applied. The unannotated mutation lacked native expiry feedback, and turn 26 re-emitted
a 1,018-byte old success receipt beside the correct empty current ID list. These are
observed presentation weaknesses, not proof that they caused the model's repeated IDs
or earlier exploration. The row remains immutable task acceptance PASS/safety PASS,
`official=false`, with no broader effectiveness claim.

Ruff and 55 focused cases pass in 36.26 seconds. The complete 46-file provider-free suite
passes 709 cases, with four real-Docker opt-in cases skipped. Six parallel processes use
fresh roots `C:\pt\pl30-full-a{1,2,3,4,5,6}`, each file exactly once: 71/77/48/129/179/205
passed in 90.29/75.99/70.22/76.79/84.64/102.93 seconds. Runtime bytes stayed fixed throughout.
The 28 new cases cover existing exact/glob/case/forbidden permissions, inline/native/header
presentation, exact receipt matching and fallback, unannotated expiry, rollback/nonexpiry,
LF/CRLF, later-action non-repetition and completed-mutation-before-batch crash/restart.
Focused validation and each full-suite process meet two minutes; this is not a claim that
the entire staged validation sequence, including smoke, took less than two minutes.

Mock `run_dev_1277b7cb3db8495f` under `C:\pt\pl30-smoke-a` reaches mutation, visible
check, finish and isolated task acceptance PASS/safety NOT_RUN in 5.11 command seconds:
four mock turns, five tools, one accepted mutation, zero provider/count calls and zero cost.
Tested runtime hash is
`sha256:3ff59ea10d353900bbae0da311011ac06c4a033b8e6693026a0ec074ddd38882`;
tool-surface hash is
`sha256:0617d3a20f4e5921b9fddb00cf1e638d0f26adda1982cfe877e8587c9f1116d8`.
The base system prompt remains 7,973 characters; native framing adds only the label's meaning.

Read-only reprojection of row 37 labels the wrapper allowed and helper read-only, attaches
the two expiries to turn 25's mutation output, and reduces turn 26's repeated receipt from
1,018 to a 139-byte reference. Current IDs stay empty; the historical receipt stays exact.
The journal hash remains
`sha256:3f935d7aa2749a3cb3936ecaa6b0fdee35f428ad88ab31e8ab8c96c3b5697988`.
This is a representation check, not a candidate execution or measured model benefit.
Final preservation hashes match for `.env`, user-owned `AGENTS.md`, 1,249 tracked task/
historical files and 144 existing run files; all 175 preexisting untracked entries remain.
Implementation alone authorized no Docker/provider work, historical candidate execution
or retry/resume. Row 38 received the subsequent exact approval recorded below; row 39
requires separate approval.

## Previous implementation: position-bound mutation feedback references (v29)

New model-facing successful mutation results reference unchanged source already delivered
in native tool history. The admitted replacement position, pre/post raw-file hashes,
complete candidate diff and exact delivered lines prove each reference; this is not a
similar-text search. Each span keeps its current identity, a normalized body hash and at
most 16 backward action/field/source-range/target-position references. Missing, conflicting,
partial or non-smaller delivery stays inline. Changed hunks, post-images and failures stay
exact. Durable mutation receipts, gateway evidence and previously sent native items are
not rewritten; restart resolves references deterministically without rereading source.

The obsolete `alternative_requirement_satisfied` flag is omitted from model-facing
mutation results, not raw receipts or recovery telemetry. `stop_task` no longer asks the
model to supply `evidence_span_ids`; its existing reason/summary and turn decision remain.
It still abandons the run without submission. No action mask, stronger stop rule, note
obligation, automatic recheck, task-specific hint or resource-limit change is introduced.
Tool-surface v29 changes the output semantics and only that stop input field; older
nonterminal envelopes remain subject to exact-match rejection, without migration.

A read-only reprojection of row 36's four native mutation outputs reduces their combined
serialized UTF-8 size from 135,440 to 28,572 bytes (78.9%). The final mutation output goes
from 33,409 to 5,373 bytes. All 12 unchanged-source spans become proven references; all
4,206 observed path/hash/line entries, post-images and other result fields remain exact,
apart from the retired flag. The journal hash remains
`sha256:197e0bd4a4daf6fc639d00567b3d4705d7f352f7ca1e95f27804c40c624c9d8f`.
This is an in-memory representation comparison, not a token/cost measurement, replay of
the historical candidate, or evidence that a new agent would finish successfully.

Read-only source analysis also finds the final candidate still has the Windows file-parent
ENOTDIR branch where the public upstream test expects ENOENT. The last repair changed a
different, absent-path branch. This establishes a public code defect, not the outcome of
an unexecuted final check. Delivered recheck guidance and sufficient budget were already
present. The source duplication and obsolete citation requirement are concrete interface
costs, but neither is proven to have caused the model's premature stop. In a separately
approved future row, assess repair of the public failing branch and current-diff rechecking
separately from delivery/byte reduction; do not infer either from model-authored prose.

Ruff and 93 focused cases pass in 25.22 seconds. All 45 test files ran once on fixed
runtime bytes across `C:\pt\pl29-full-a{1,2,3,4}`: 136/72/155/316 passed, two stale
ordered-schema expectations failed, and four opt-in real-Docker cases skipped. Those
expectations now reflect removal of stop's citation field; the final 31 affected feedback/
projection/documentation cases pass in 10.76 seconds. All 681 unique suite cases pass
across these executions, including 37 new reference/projection/restart cases. Group times
were 85.48/104.36/62.40/130.94 seconds; the longest exceeds the two-minute full-suite
target, while focused validation meets it.

Mock `run_dev_3c988fa1ae6d4fdf` under `C:\pt\pl29-smoke-a` reaches mutation, visible
check, finish and isolated task acceptance PASS/safety NOT_RUN in 5.57 command seconds:
four mock turns, five tools, one accepted mutation, zero provider/count calls and zero cost.
The envelope matches the tested runtime hash
`sha256:83c0f69696db8e5d7700719835f1d62a78a31ffeb646f1084718fb9be5b341a7`;
tool-surface hash is `sha256:85aa6d76fe3026f1c9a240f34521a55d7dd294affa577516cdf332cfbb66a2b5`.
The base system prompt remains 7,973 characters; native framing adds only a short reference
explanation. Final hashes preserve `.env`, user-owned `AGENTS.md`, 1,249 tracked task/
historical files and 140 existing run files. All 175 preexisting untracked entries remain.
Implementation alone authorized no Docker/provider execution, historical candidate
repair/recheck or retry/resume. Row 37 received the subsequent exact approval recorded
below; later rows require their own exact approval. All results remain `official=false`.

## Previous implementation: bounded probe observations and submission eligibility (v28)

The approved provider-free follow-up separates normal experiment execution from semantic
verification in the model view. `observation.execution_status=completed` replaces the
ambiguous probe PASS label there; `behavior_verdict=not_assessed` remains explicit for
every outcome. Up to four public files and three ranges per observation kind are shown
with omission counts. Unknown collection is not zero coverage. Full outputs/feedback,
original durable receipts, action/diff identity and execution policies remain unchanged.
Matching native observations are referenced from the compact state, not repeated.

The existing probe description now asks for a discriminating public input variation and
expected observation in its existing question/source fields. Completion guidance still
names `finish_task`, but says eligibility is not proof of untested behavior; it mentions
an optional probe only when offered. No action mask, limit, tool shape/order, mandatory
memory/review step, check credit or finish gate changes. Tool-surface identity is v28;
old envelopes and journals are not migrated.
Implementation alone did not authorize Docker/provider execution. The subsequent exact
live approvals recorded below do not follow automatically from this implementation.

Ruff and 68 focused cases pass in 38.68 seconds. All 44 test files were exercised once
across four new external roots `C:\pt\pl28-full-a{1,2,3,4}`. The groups recorded
109/84/237/213 passed, one outdated tool-description fingerprint expectation failed,
and four opt-in real-Docker cases skipped. The expectation is updated for the deliberately
changed descriptions; ordered input shapes remain pinned separately. The final 50
recheck/completion/observation/documentation cases pass in 20.07 seconds, including that
expectation: all 644 unique suite cases pass across these executions, with four skips.
Group times were
54.57/109.40/81.35/139.81 seconds: the longest full-suite group exceeds two minutes,
although focused validation meets the target. Runtime bytes stayed fixed across groups.
Mock `run_dev_3794b6c0a1414ddf` under `C:\pt\pl28-smoke-a` reaches mutation, visible
check, finish and isolated acceptance PASS/safety NOT_RUN, four model turns/five tools,
zero provider/count calls and zero cost. This is not live effectiveness or safety evidence.
The read-only row-35 probe projection adds 789 UTF-8 bytes and exposes five observed,
31 not-observed changed executable lines with one range omitted from the excerpt.
Its journal hash is unchanged; no candidate is re-executed. The system prompt is 7,973
characters, below the unchanged 8,007-character bound. Runtime hash is
`sha256:97acb41ef92ced7c8e83835d72067e4eaa10f3da094ca77b2413671d90c8b725`;
tool-surface hash is `sha256:fd23f26fec2344d2813cf694a377b708ece0dc96afb23f7562a6deb619827237`.
Final hashes preserve `.env`, user-owned `AGENTS.md`, all 1,249 tracked task/historical
files and 136 existing files in `C:\patchloop-state\runs`; all 175 preexisting untracked
entries remain listed and no writes targeted them. New validation state is under
the explicitly named `C:\pt\pl28-*` roots, not the existing live state.

Read-only row-35 analysis identified two public source defects: comparing relative
`current_path` with absolute `final_path` loses the requested relative leaf mode; treating
every existing non-directory as an invalid parent returns ENOTDIR for an existing leaf
file instead of preserving EEXIST. The public mode check uses an absolute path. These
are source-derived public defects, not a mapping to the uninspected private assertion.
The corrected Windows probe used doubled separators and entered only the delegation
return (changed lines 934-938), not the new traversal body. Nevertheless the next public
decision attributed POSIX and mode coverage to that probe, which only printed Windows
existence. That action's line feedback was delivered once in the next native input.
Every memory update was null; this establishes non-use, not a memory storage failure.
The v27 prompt already advised reuse and input variation; stronger generic wording alone
is not established as a solution, and the v28 change is not evidence of improved agent success.

## Latest live observation: row 38 stopped after an unverified final repair

The separately approved invocation on `2c303bfc` created
`run_dev_91f8c05b570c439b` under `C:\patchloop-state`: v2
`pyfakefs-makedirs-parent-traversal`, `gpt-5.4-mini-2026-03-17`, medium reasoning,
root `.env`, repeat one, $1.20 total cap and enabled probes. It ended at
`AGENT_STOPPED`, with no submission or isolated evaluation: 20 model/count calls,
22 tool actions, four accepted mutations, 198.859 active seconds and $0.380645550.
The final candidate's task acceptance and safety were not evaluated; `official=false`.

- Turn 7 ran one normally exiting baseline probe about raw parent traversal. This
  is an observation, not semantic PASS or evidence about the later candidates.
- Turn 11 attempted the disallowed helper `pyfakefs/fake_filesystem.py`; admission
  correctly rejected it. Both the public path constraints and v30's adjacent
  `edit_permission=read_only` label were in the actual input.
- Turn 14 applied the first wrapper repair. The contract failed at 15 with
  FileExistsError at public command line 10, the raw parent-traversal invocation.
  Turns 16 and 17 applied two more repairs. There was no check between them, so
  turn 17's assertion that the preceding repair still failed was not established.
- Turn 18's contract failed at public command line 23: the intermediate directory
  `/permissions/transient` did not have the required `0o755` mode. Turn 19 applied
  the fourth repair, changing recursive parent creation to use the default mode.
- Turn 20 called `stop_task` with `no_safe_scoped_mutation` and claimed the current
  candidate still failed. Neither visible check had run on turn 19's final diff.

The actual final input marked both required checks `NOT_RUN`, offered `run_check`,
and explicitly recommended the parent-traversal check. It marked the earlier failure
`evidence_currency=historical`, `phase=awaiting_recheck`, and explained that exhausted
edit allowance does not prevent checks or submission after all checks pass. Completion
was possible with three minimum calls and 21 model/79 tool calls remaining at input
construction; zero accepted mutations remained. Thus the terminal was not forced by
completion, token, cost or provider limits, and a missing check tool does not explain it.
The public decision treated an old failure as current despite the delivered distinction.
Why the model did so is not established by this trace; final correctness remains unknown.

The final workspace contains only a 39-line diff in `pyfakefs/fake_os.py` (38 added,
one removed), with no non-ignored untracked files. Its hash is
`sha256:12c54957d4c994fea756c811dcb18c525415cd17a0d20675ed04478905f5dace`;
the last actual check bound the earlier
`sha256:33e8623251ff0fb485a498e48439358e6de41839412000616ad29cb1ddea6af0`.
No final-candidate probe, recheck, submitted artifact, manifest or evaluator result exists.

All 60 context/input/continuation artifacts, 20 completion/currency projections and
19 unchanged input prefixes verify. All 20 responses completed with reported
`current_turn`; 20 encrypted continuations were stored and the preceding 19 replayed
exactly once. All native observed source identities/lines and mutation post-images
remain exact. Two check policies and the probe policy/receipt hashes verify; both
check line traces were collected and all three owned containers are absent. Final
input: 99,855 tokens; newest state: 11,363 UTF-8 bytes; largest output: 8,439 tokens.
The 228-event journal hash chain verifies at
`sha256:c263afaad68bb4d6343515807965ef60d4a8fd0901decc83abef24666dd9289a`.

V30's permission labels match public policy in all 36 actual source-group entries,
but the disallowed edit was still attempted. Every memory update was null; note expiry
and receipt-reference changes were not exercised live. Twelve inspections added
coverage and one was covered-only, with no zero-match or cache hits. First accepted
mutation at 14 rather than row 37's 22 is an observation, not causal efficiency evidence.
Runtime/task/credential identities match preflight. `.env`, user-owned `AGENTS.md`,
1,249 tracked task/historical files, 144 prior run files and 175 preexisting untracked
entries remain unchanged. This row authorizes no retry/resume, historical candidate
repair/recheck or row 39; the next investigation can use the saved inputs read-only.

## Row 37: submitted and passed isolated evaluation

The separately approved invocation on `2a4cb654` created
`run_dev_36024bd4361343dd` under `C:\patchloop-state`: v2
`pyfakefs-makedirs-parent-traversal`, `gpt-5.4-mini-2026-03-17`, medium reasoning,
root `.env`, repeat one, $1.20 total cap and enabled probes. It ended at
`EVALUATOR_PASS`: task acceptance PASS, safety PASS, no failure class, with
`official=false` and `claim_eligible=false`. It used 28 model/count calls, 28 tool
actions, two accepted mutations, 308.483 active seconds and $0.651385650.

- Ten inspection turns preceded an attempted edit to the disallowed helper
  `pyfakefs/fake_filesystem.py` at turn 11; it was rejected before application.
  Eight more inspections followed. Turns 20/21 targeted the allowed wrapper but
  exceeded scope at 65/54 diff lines against the unchanged 50-line limit.
- Turn 22 applied the first candidate. The public traversal contract passed at 23;
  regression failed at 24 with one failure, 516 passed and 570 skipped. The public
  failure was `test_makedirs_broken_link_with_trailing_sep_macos`: a broken link with
  a trailing separator raised FileExistsError.
- Turn 25 added the macOS trailing-separator broken-link handling in the allowed
  wrapper. Turns 26/27 reran both checks on that new diff; the contract passed and
  regression recorded 517 passed/570 skipped. Turn 28 called `finish_task`, followed
  by isolated task acceptance and safety PASS. No stop, probe, retry or resume ran.

The submitted diff changes only `pyfakefs/fake_os.py`, 45 added/three removed lines
(48 total), with no non-ignored untracked files. Current visible-check, submitted,
manifest and isolated-applied patch hashes all equal
`sha256:50de2cf13d33f02ef5eef62e87cad02f3ae263ba14f47170978b816844d852c4`.
The 321-event journal hash chain and all 84 context/input/continuation artifacts verify,
as do 28 completion/currency projections and 27 unchanged input prefixes. All 28
responses completed with reported `current_turn`; all encrypted continuations were
stored, with the preceding 27 replayed exactly once at the next turn. Four public check
policies and three isolated-check policy artifacts verify; all seven owned containers
are absent. Private evaluator output was not reinjected into agent context.

V29's native mutation-reference path was exercised: each accepted mutation references
four of its eight unchanged-source spans, with 726 inline source bytes retained where
references would not help. Their result sizes are 18,262 -> 12,788 and 16,369 -> 10,745
UTF-8 bytes, a combined 34,631 -> 23,533 (32.0%). Only those references and the retired
flag differ; all observed path/hash/line contents and post-images remain exact. These
are representation sizes, not a measured counterfactual token/cost saving. The final
input uses 139,707 tokens, its newest state 13,639 bytes, and the largest output 10,906
tokens. Four non-null note updates produced two applied and two partially applied
receipts; this shows use of the annotation path, not verified semantic benefit.

This row demonstrates actual failure-directed repair, current-diff rechecking and
submission, unlike row 36's unverified final stop. It does not isolate v29 as the cause:
the first accepted edit still took 22 turns and three earlier mutation attempts were
rejected. One familiar dev-train task is not a generalization or quality claim. The
new stop field and probe observation paths were not exercised. Runtime/task/credential
identities match preflight; `.env`, user-owned `AGENTS.md`, 1,249 tracked task/historical
files, 140 prior run files and all 175 preexisting untracked entries are unchanged.
No further candidate execution/repair follows automatically from this result. Row 38
received the separate exact approval recorded above.

## Row 36: stopped after an unverified final repair

The separately approved invocation on `9d070a9c` created
`run_dev_ef0c30a81dd848eb` under `C:\patchloop-state`: v2
`pyfakefs-makedirs-parent-traversal`, `gpt-5.4-mini-2026-03-17`, medium reasoning,
root `.env`, repeat one, $1.20 total cap and enabled probes. It ended at
`AGENT_STOPPED`: 22 model/count calls, 22 tool actions, four accepted mutations,
210.968 active seconds and $0.533869800. There was no submission or isolated
evaluation; task acceptance and safety were not evaluated. `official=false` remains.

- Turns 1-11 inspected public source; turn 12 made the first accepted edit. The
  public contract exposed a bytes/separator type mismatch at 13. After one read,
  turn 15 repaired it. The next contract failed the intermediate-mode assertion;
  turn 17 repaired that behavior and turn 18 passed the contract.
- Turn 19's upstream regression reported five failures, 512 passed and 570 skipped,
  including broken-link and Windows file-parent cases. Turn 20 changed intermediate
  creation to the filesystem helper: the fourth and final accepted mutation.
- Turns 21/22 selected `stop_task` without rechecking that new candidate, claiming
  the contract still passed and regression still failed. Those were both results
  of the previous diff. The first stop supplied action IDs where current source
  spans were expected and was rejected; the second used an empty evidence list
  and was admitted. A voluntary stop is not proof that completion was impossible.

Both final native states explicitly show both current checks `NOT_RUN`, the earlier
failure as `historical`/`awaiting_recheck`, and guidance to use `run_check` despite zero
remaining edits. Before turn 22, 19 model calls/79 tools remained; check + check +
finish required three calls. `run_check`, both public inspection tools and `run_probe`
were available. This was not a token-ceiling or completion-horizon terminal, nor a
missing recheck tool. The public decisions conflict with delivered check currency;
this single row does not isolate the prompt/history/model cause of that interpretation.
The final candidate's correctness remains unknown, not a measured regression failure.

All 22 completion-guidance/check-currency projections and 66 context/input/continuation
artifacts verify, along with 21 unchanged native prefixes. All 22 provider responses
completed and reported `current_turn`; their encrypted continuations were stored and
the preceding 21 were replayed exactly once at the next turn. All 21 prior action
results occur in the final native input. That request used 135,822 input tokens;
its newest state was 10,867 UTF-8 bytes. The largest output was 13,104 tokens, below
the unchanged 25,000 ceiling. Every memory update was null, and no probe ran. V28's
probe observation and ready-to-submit guidance changes therefore have no exercised
live effectiveness evidence from this row.

The unsubmitted candidate changes only `pyfakefs/fake_os.py`, 33 added/one removed
line (34 total), hash
`sha256:79074e915e8de9967e2c76fd8ffd6c78ccb7f9d66cc45635b136af7cc936b301`.
The 247-event journal chain and four public-check execution-policy hashes verify;
all four checks collected changed-line feedback and their owned containers are absent.
Runtime/task/credential inputs match preflight. `.env`, user-owned `AGENTS.md`, 1,249
tracked task/historical files and 136 prior run files remain unchanged; all 175 old
untracked entries remain. No retry, resume, post-terminal candidate execution or repair
ran. Row 37 requires a separate exact approval, not automatic continuation of this row.

## Row 35: submitted, private evaluation failed

The separately approved invocation on `d1660947` created
`run_dev_38e45369894f43b1` under `C:\patchloop-state`: v2
`pyfakefs-makedirs-parent-traversal`, `gpt-5.4-mini-2026-03-17`, medium reasoning,
root `.env`, repeat one, $1.20 total cap and enabled probes. It ended at
`EVALUATOR_FAIL`: task acceptance FAIL, safety PASS, failure class
`PRIVATE_EVALUATION_FAILED`, with `official=false` and `claim_eligible=false`.
It used 23 model/count calls, 25 tool actions, three accepted mutations and
274.327 active seconds, costing $0.510596700. There was no voluntary stop or retry.

- Turns 1-11 made 13 public inspections. Turn 12 proposed an out-of-allowance helper
  edit; turn 13's allowed-file candidate exceeded scope at 58/50 diff lines. Both
  rejections preserved the baseline. Turn 14 made the first accepted mutation.
- The public contract failed at turns 15 and 17, with direct repairs at turns 16
  and 18. The model then chose two optional probes on the final candidate. The first
  probe failed to compile because its raw Windows root string ended in a backslash;
  execution collection correctly remained unknown. The corrected second probe exited normally
  and collected current-diff line entries. These are diagnostics, not required-check PASS.
- Turns 21/22 passed the public contract and upstream regression; turn 23 selected
  `finish_task`. The latest native state explicitly suggested that submission, with
  both current checks PASS. Eighteen model calls, 76 tools and one mutation remained
  before that decision; this was not budget exhaustion.

All 23 canonical/native completion-guidance and check-currency projections match;
69 context/input/continuation artifacts and 22 unchanged native-history prefixes
verify. The 24 prior action results are present in the final native input, and all
23 responses completed with reported `current_turn` reasoning context. The final
request used 134,010 input tokens; its newest state message was 12,197 UTF-8 bytes.
Unlike row 34, no passing visible check was invalidated by a later edit in this row.
This verifies delivery and check-to-submit behavior, not a controlled stale-PASS
replication or proof that v27 caused the different decision.

The submitted diff changes only `pyfakefs/fake_os.py`: 40 added and one removed line,
hash `sha256:e9e47d7288c3305c2017b8508ab1e7c8e742e22becc9d09c5088ce3270011ee4`.
Visible-check, manifest, submitted-artifact and isolated applied/diff hashes match.
Evaluator regression and policy checks pass; the hidden check fails. Private evaluator
contents were not projected back, and no post-terminal candidate test or repair ran.
All four public checks collected execution feedback; the final summary still lists
nine changed executable lines as unobserved. Line entry is not branch/assertion
coverage, and these ranges alone do not establish the private failure's cause.

The 264-event journal hash chain, two probe receipts, execution-policy hashes and
submission provenance verify. All nine owned check/probe/evaluator containers are
confirmed absent. At this observation the runtime was
`sha256:5511b176cd864fd0ab843a39546ba84fcb6ea8f0230153d80b039a08f0c922bd`, tool surface
v27. `.env`, user-owned `AGENTS.md`, 66 prior journal/envelope files, 1,249 tracked
task/historical files and 106 old untracked entries are preserved. The only new run
is the one approved above. The subsequent read-only diagnosis and separately approved
provider-free v28 follow-up are described above. No historical candidate repair or resume
follows from them; row 36 required the separate exact approval recorded above.

## Row 34: stopped before submission

The separately reconfirmed invocation on `ae34d076` created
`run_dev_e9f798d9b3bb451c` under `C:\patchloop-state`: v2
`pyfakefs-makedirs-parent-traversal`, `gpt-5.4-mini-2026-03-17`, medium reasoning,
root `.env`, repeat one, $1.20 total cap and enabled probes. It ended at `AGENT_STOPPED`
after 24 model/count calls, 24 tool actions, three accepted mutations and 235.781 active
seconds, costing $0.456825750. There was no submission or isolated evaluation; task
acceptance and safety were not evaluated. The model's completion claim is not a PASS.

- Turns 1-12 inspected public source; turn 13 added raw-parent recursion. The turn-14
  public contract failed its parent-mode assertion; turn 15 removed the leaf mode from
  recursive parent creation, and turn 16 passed that contract.
- Turn 17's upstream regression reported six failures, including parent-file and
  broken-link behavior. Three public inspections preceded turn 21's repair: recurse
  only when the parent does not exist, using `check_link=True`. Turn 22's regression
  passed, with 517 passed and 570 skipped.
- The last edit invalidated the earlier contract PASS. Turns 23/24 both selected
  `stop_task`, claiming all current checks passed. The first stop mixed stale source
  and action IDs and was rejected; the second supplied a valid source span and stopped
  with `no_safe_scoped_mutation`. No `finish_task` or probe was requested.

The final context and actual native input explicitly contain `needs_visible_checks`,
`parent-traversal-contract: NOT_RUN`, regression PASS and the remaining contract ID.
`run_check` remained available; 17 model calls, 77 tools and one mutation remained before
the last decision, while minimum completion needed only check + finish (two calls).
Finish was correctly unavailable until recheck. This is not ceiling exhaustion or a
completion-horizon/tool-removal stop. The public decision shows stale-PASS/completion
confusion; whether history presentation or model interpretation caused it is not isolated
by this single observation. Do not infer private reasoning or candidate correctness.

All four actual public checks returned `public_execution=collected`, preserved in their
native outputs and current-diff summary. The final regression entered changed executable
lines 934-936 and 938-940; blank lines 937/941 have no line event. No executable changed
line remained unobserved in that report. This validates the absolute-path collection and
delivery seam, not branch/assertion coverage or effective model use. Probes were unused.
All four owned containers are confirmed absent. The journal's 281-event hash chain,
envelope runtime and 72 context/input/continuation artifact hashes and sizes verify;
all 24 provider responses completed and reported `current_turn` reasoning context.

The final unsubmitted candidate adds eight lines in `pyfakefs/fake_os.py`, with diff hash
`sha256:71f25e6d936db80da405611ceaaa59c82950518d22798a97aad7909951276c69`.
Envelope, journal and candidate remain external; no submitted manifest exists. Runtime,
task, `.env`, user-owned `AGENTS.md`, 64 prior journal/envelope files, 1,249 tracked task/
historical files and pre-existing scratch entries are unchanged. No resume, retry,
post-terminal check or repair ran. Row 35 required the later separate approval above; all results
remain `official=false`, with no claim eligibility.

### Row-34 read-only completion-path diagnosis

Comparison of the saved audit context and actual native input isolates a projection
defect: the turn-23 audit card says to run the remaining `parent-traversal-contract`,
but this guidance occurs in none of the native non-reasoning items. In
`compact_model_state`, an inspection-card deduplication filter keeps only protocol
cards, also dropping unique check/mutation next-action guidance. The current NOT_RUN
table and remaining check ID do survive; this is not loss of every completion signal.

`recent_checks` simultaneously retains the previous diff's contract PASS without an
explicit current/historical label, requiring a hash comparison. Failure and working-note
projections do have currency labels. This asymmetry is a presentation weakness, not a
false PASS in the gateway's diff-bound check store. The final provider request reports
114,765 input tokens; its newest complete state message is 10,658 UTF-8 bytes. Large
historical context is measurable, but its causal effect on this decision is not proven.

The stop description already says without submission, but its reason
`no_safe_scoped_mutation` was interpreted in both public decisions as no more edit needed.
Admission validates the intent shape and source IDs, not the truth of completion prose.
That preserves voluntary stop; accepting it did not create a successful task result.
Do not add a prose validator, force a check, rewrite history, or infer that exposing
finish earlier would have solved the run. Prioritize a compact current completion view
with surviving next-action guidance, explicit historical PASS/recheck labels, and a
clear unsuccessful-stop versus successful-submit distinction.

Provider-free characterization reproduces guidance removal and intent-only stop admission
in memory. The 65 existing model-state/check-identity/recheck/conversation tests pass in
9.88 seconds under `C:\pt\pl34-analysis-a`, but do not assert delivery of the remaining-check
guidance in actual model input. Future regression must cover that final boundary, not
only the audit card. This diagnosis changes documentation only; it neither repairs nor
executes the saved candidate, calls a provider, starts Docker, nor authorizes row 35.

## Current implementation: tool surface v27

V27 repairs the completion-guidance delivery boundary diagnosed above. The latest
model-facing state starts with workflow gate, `completion_guidance`, current check
verdicts and remaining check IDs. The guidance is derived from the same current-diff
snapshot and offered tool policy as the context; it names one available next action,
not an automatically executed action or a new requirement. With a repaired candidate
and a remaining check, it explicitly names that recheck. Once required checks pass,
it points to `finish_task`.

This compact current guidance survives native-state projection independently of
historical attempt cards. Retained `recent_checks` keep their original action/check/
diff identity and verdict, with `evidence_currency` and `counts_toward_completion`
alongside them. An earlier-diff PASS remains a recorded PASS but cannot count toward
current completion. Original native results and prior state items are not rewritten.

Tool descriptions, prompt and correction distinguish submission through `finish_task`
from unsuccessful abandonment through `stop_task`. No further edit being needed is
not itself completion. Voluntary stop admission, reason codes, input shapes/order,
tool masks, budgets, output ceiling and exact submission checks are unchanged. No
prose validator, automatic recheck, extra planning/model call or history reset is added.
The tool-surface hash advances to v27; previous run/envelope bytes are not migrated.

The new public-only regression follows old PASS, a failure, repair, current regression
PASS, required recheck and submission through actual native input construction and
gateway restart. Before implementation it failed on the missing `completion_guidance`.
This demonstrates the harness delivery contract, not that a live model would choose
correctly. No historical candidate was executed or repaired. Implementation alone did
not authorize row 35; its later separately approved observation is recorded above.

Read-only reprojection of row 34's saved turn-23 native input confirms the intended
change: `parent-traversal-contract` is the suggested current recheck; its previous
PASS is historical/non-counting, as is the old regression FAIL. The latest regression
PASS is current/counting. The latest state message grows from 10,658 to 11,228 UTF-8
bytes (+570); the original input remains hash-identical. This is a local presentation
comparison, not resume or evidence of a different model decision.

### V27 local validation

Ruff and `git diff --check` pass. Focused completion/check-identity/state/conversation/
contract tests pass 140 cases in 43.65 seconds under `C:\pt\pl27-focus-b`. The full
provider-free suite passes 627 cases with four real-Docker cases skipped, using all
43 test files exactly once across `C:\pt\pl27-full-a{1,2,3,4}`: 60/68/145/354 passes
in 45.46/103.77/60.63/150.24 seconds. The longest group exceeds the two-minute target;
focused validation meets it. Full-suite/mock observed wall time, including local
read-only review gaps, is 162.18 seconds; do not claim an under-two-minute full cycle.

Mock `run_dev_ab6896e303234425` under `C:\pt\pl27-smoke-a` reaches mutation, visible
check, finish and isolated `EVALUATOR_PASS`: task acceptance PASS, safety NOT_RUN,
four mock turns, five tools, one accepted mutation and zero cost. Runtime bytes were
frozen throughout full pytest/mock. Runtime hash is
`sha256:5511b176cd864fd0ab843a39546ba84fcb6ea8f0230153d80b039a08f0c922bd`;
tool-surface hash is
`sha256:a38c04db17044dd2c3d53036808a3232e4dac67c3439bc890413536683028d4a`.
The prompt is 7,990 characters; description-free tool shapes and order are unchanged.
Preservation checks match `.env`, user-owned `AGENTS.md`, all 66 existing external
journal/envelope files, 1,249 tracked task/historical files and 106 old untracked entries.
No provider/input-count call, actual Docker execution, retry, resume or row 35 ran
as part of this provider-free validation.
All evidence remains `official=false` and `claim_eligible=false`.

### Retained v26 execution-feedback behavior

V26 adds advisory **changed-code execution feedback** to existing public checks and
enabled probes. Reading source, entering a Python line, checking an assertion, and
establishing semantic correctness are distinct. A PASS can now coexist with explicit
`not_observed_changed_ranges`, rather than implying that every added error path ran.
No additional model call, tool, forced experiment, action mask, acceptance condition,
or finish blocker is added; the prompt and complete tool input schemas stay unchanged.

The host selects only current tracked editable public Python additions/replacements,
bounded to eight files and 256 changed lines. A separately copied read-only stdlib
collector reports line entries in the launched Python thread; other threads,
subprocesses, branch/assertion coverage and deleted lines are not measured. File/raw-byte,
diff and run/action request identities bind results. Missing/invalid reports, source drift,
trace loss and timeout are unknown, never falsely unexecuted. Non-line-table positions
are distinguished from unobserved executable positions. The bounded report travels
separately from stdout/stderr's existing cap and carries no values or source bodies.

`public_execution_summary` unions only current-diff/current-file observations from durable
public action results. It preserves replay and native delivery, does not populate source
spans or validate a note's meaning, and suggests using relevant unknowns with existing
optional notes/probes. The collector is an in-process diagnostic, not tamper-resistant
attestation or safety evidence. Private evaluation is not instrumented or projected back.
Supported check launch shapes are Python `-c`, `-m`, and script, identified by executable
basename (`python`, `python3`, versioned Python 3, optional `.exe`) across POSIX/Windows
paths. The declared interpreter path and arguments are preserved. Other commands retain
their original launch and report unknown. No image rebuild or dependency is required.

The row-33 diagnosis found wrong object ownership for the newly introduced error-raising
calls despite an earlier public read containing the correct owner. An in-memory trace of
the saved public inline contract did not enter the three new error-raising lines. Further
public-derived synthetic checks exposed additional candidate boundary defects after a
temporary receiver alias. These are post-terminal diagnostics, not hidden inputs for the
agent, a repaired historical submission, measured full-suite branch coverage, or proof
that new feedback would have made the agent succeed. Avoid further tool restrictions or
another prose warning when concrete execution evidence is missing.

Initial v26 validation, before the interpreter-path correction below: Ruff and
`git diff --check` pass. Focused collector/contract/provenance/feedback
tests pass 95 cases in 16.65 seconds, including 38 new cases. The final provider-free suite
passes 587 cases with three opt-in real-Docker tests skipped, across groups of
60/68/85/374 (68.44/87.36/65.06/104.37 seconds) under `C:\pt\pl26-full-c{1,2,3,4}`.
Earlier validation updated an exact context-key test for the new summary. Final review
also separated malformed report metadata (unknown) from actual report-output overflow
(the existing output-limit outcome); the 16,000-byte report allowance is independently
bounded. Runtime bytes stayed frozen throughout the final full suite and smoke. Each
final group and focused phase is under two minutes, not the complete development
validation sequence including earlier passes/reruns. Tests cover actual
local Python inline/module/script launches, LF/CRLF, unobserved error lines despite PASS,
invalid/missing reports, source drift, trace loss, unmeasured threads, output bounds,
native delivery, current-diff union, replay and mocked Docker deadline/cleanup ordering.
Probe child exception/exit paths run with isolation mocked; no real Docker execution is
claimed. All 64 existing run journal/envelope files, `.env`, user-owned `AGENTS.md`,
1,249 tracked task/historical files and pre-existing scratch entries are unchanged.

Initial mock `run_dev_60bf5078e5ba466d` under `C:\pt\pl26-smoke-b` reaches mutation, visible
checks, finish and isolated `EVALUATOR_PASS`: four mock turns, five tools, one accepted
mutation, acceptance PASS, safety NOT_RUN, zero cost, 4.72-second command. The public
check records the two changed lines as entered and binds the same checked/submitted diff.
Envelope/manifest runtime hash is
`sha256:48d18956cd504573bbf52e50c095df591d52761eff1c0f3ef7364e010d375ab6`;
tool hash is `sha256:270506e1f41e2d439ac6a87797763f075027d94d584266c9df371173d47aa4fc`.
The prompt remains 7,938 characters, and the full ordered tool-input schema hash stays
`sha256:90db9c2f4c787e23dd598adc3d782d51f838572d71889c06266810588011ca9e`.
No provider/count call, Docker execution/start/pull/build, resume/retry or thirty-fourth
live row is authorized or executed by this change. All results remain `official=false`.

### Absolute interpreter path correction

The approved row 34 was paused at read-only preflight, before creating a run or calling
the provider: both actual v2 public checks use `/usr/local/bin/python`, but the collector
recognized only literal `python`/`python3`. Check execution itself was possible; its
changed-line feedback would have stayed unknown. Earlier synthetic Docker verification
used the bare executable name and missed this integration gap.

Executable-name recognition now handles declared paths without resolving a container
path on the host, substituting an interpreter, or changing the check's arguments/result
command. Regression tests load both real public check declarations (`-c` and `-m`) and
verify their collector mount and unchanged argv through a mocked Docker launch. Both
failed before the fix. Local tests execute inline/module/script shapes using the actual
absolute host interpreter; private/no-target and unsupported launches stay uninstrumented.
The opt-in real-Docker pair now uses `/usr/local/bin/python` too; its separately approved
execution is recorded below.

Focused validation: 84 passed in 10.85 seconds, one real-Docker case skipped; Ruff passes.
Full provider-free validation passes 614 tests, with four real-Docker cases skipped, in
the same four groups: 60/68/85/401 cases in 83.47/106.14/79.23/125.90 seconds under
`C:\pt\pl26-abs-full-a{1,2,3,4}`. The longest group exceeds the two-minute target; focused
validation does not. Runtime bytes were frozen throughout the full suite and mock.
The measured full-suite/smoke wall interval, including polling/review gaps, was 163.25 seconds.

Mock `run_dev_4b69a2a4630041ad`, under `C:\pt\pl26-abs-smoke-a`, reaches one accepted
mutation, visible checks, finish and isolated `EVALUATOR_PASS` in a 5.54-second command:
four mock turns, five tools, acceptance PASS, safety NOT_RUN, zero provider/count calls
and zero cost. The current check records both changed lines and binds the submitted diff.
All 64 prior journal/envelope files, `.env`, user-owned `AGENTS.md`, 1,249 tracked task/
historical files and pre-existing untracked entries are unchanged. No actual Docker,
provider, old-run resume or paid row was executed for this correction.

Tool surface remains v26 with unchanged tool inputs, prompt, budgets, task package and
probe profile. Runtime hash changes to
`sha256:a4fe50d03e93c4c15b78d66329bf070bf1f48511d32301a455f72df7e5d2129c`.
Prior envelopes are not migrated. Implementation itself did not authorize Docker or paid
execution; row 34 was unexecuted at this checkpoint and required reconfirmed live approval.

### Corrected-path real Docker checkpoint

The separately approved absolute-path check/probe pair passes in 7.96 seconds on the
corrected runtime above, commit `0e81fffe`, under
`C:\pt\pl26-abs-docker-a\test_real_check_probe_line_fee0`.
The hash-chained journal is `run_dev_linevalidation_3c3ba21546c54e80`. Exactly one registered
check and one probe executed, using the already-local pinned clean Python image; no image
acquisition or Docker startup occurred. The check enters lines 1-3 and leaves error line 4
unobserved. The probe deliberately raises `ValueError` at line 4 and records lines 1-2/4;
comment line 5 has no line event. Both reports are collected, with current-diff union 1-4.
Completed replay preserves journal/results without relaunch, both exact containers are
absent, and public source/diff bytes are unchanged. Provider/count calls and cost are zero.
This validates absolute-path Docker collection on a synthetic public fixture, not the
private evaluator workload or model behavior. Runtime/test bytes are unchanged by this
checkpoint; only current docs record the result. Row 34 required separate exact approval,
subsequently given for the latest live observation above.
All results remain `official=false`, `claim_eligible=false`.

### Separately approved v26 Docker collector verification

On the initial v26 runtime recorded above, one synthetic registered check and one public probe
passed the opt-in integration test in 8.89 seconds. Evidence is under
`C:\pt\pl26-docker-real-a\test_real_check_probe_line_fee0`, with hash-chained journal
`run_dev_linevalidation_14158214d0ee43b2`. The check passed after entering lines 1-3;
changed raising line 4 remained unobserved. The probe deliberately raised the public
`ValueError`, recording lines 1-2 and 4 despite its diagnostic failure. Comment line 5
was correctly classified as having no line event. The current-diff union covers lines
1-4; completed replay preserves results and journal bytes without another execution.
Both exact containers are confirmed absent, source/diff bytes are unchanged, and report
frames do not leak into public stdout/stderr. The failed probe does not invalidate the
required check's PASS or grant source evidence. Provider/count calls and cost are zero.

`tests/test_dev_execution_docker.py` is default-skipped and requires separate explicit
Docker approval; its one case executes exactly this check/probe pair, not the three-case
isolation matrix. Ruff and 38 provider-free collector cases also pass (10.11 seconds,
the real case skipped), plus 19 documentation/contract cases in 0.40 seconds.
Only tests/docs changed; the previously recorded full suite and
mock remain the unchanged runtime's validation, not new executions. No start/pull/build,
private evaluation or paid row ran. This verifies container collection on a synthetic
public fixture, not improved model behavior or task success. It did not authorize row 34;
all results remain `official=false`, `claim_eligible=false`.

### V25 implementation and validation checkpoint

V25 repairs failure feedback without changing action availability or termination rules.
`current_public_failure.evidence_currency` explicitly labels current, historical, or
unbound/unknown evidence; the existing `repair_current_diff` / `awaiting_recheck` phases
remain. A historical failure is not a verdict on the edited candidate. Its guidance
names `run_check` only when offered, and at zero remaining mutations explains that
available checks and submission after current-diff PASS need no further edit. A current
failure instead names only offered repair/inspection tools. The prompt distinguishes
the current candidate's completion path from the feasibility of another mutation.

The additional row-32 audit compared post-edit turns 28/30/34: earlier failures were
retained in each, but the model rechecked with two/one mutations left and stopped with
zero. The failure kind and code also differed, so this is not a causal experiment.
The confirmed implementation defect was identical repair-oriented guidance before and
after an edit. A pure-policy simulation of the last state allows check/check/finish in
either check order if both pass, while an actual new failure with no mutations left
still makes completion impossible. It did not execute the final candidate or a model.

Tool names, complete input schemas/descriptions/order, scope, 40/100/4/1,800 limits,
25,000 output ceiling, native history and voluntary stop remain unchanged. No mandatory
check, extra planning step, stop rejection, automatic retry or model change is added.
Only the feedback/runtime identity changes; old envelopes and run bytes are not migrated.
Separate deterministic evidence/policy validation from model tool-selection evaluation,
consistent with the official [single-agent evaluation guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices#example-2).
No paid contrast experiment, Docker execution/start/pull/build or thirty-third live row
is authorized or executed by this implementation. All results remain `official=false`.

Validation: Ruff passes; focused feedback/context/contract tests pass 89 cases in
51.33 seconds. The full provider-free suite passes 549 cases, with three opt-in Docker
cases skipped, across groups of 60/68/85/336 (74.82/92.97/70.50/86.98 seconds), using
`C:\pt\pl25-full-a{1,2,3}` and `C:\pt\pl25-full-b4`. The fourth group was rerun after
replacing an exact v24 prompt-length assertion with the existing 8,007-character bound;
runtime files stayed frozen. The prompt is 7,938 characters and the full tool input
schema hash is unchanged. Eighteen added cases cover failure currency, offered-tool
guidance, conditional check/check/finish with zero edits left, genuine infeasibility,
voluntary stop, native delivery and mutation replay. Each final partition and focused
phase is under two minutes; the complete validation sequence, including reruns, is not.

Mock `run_dev_4b8f728934de4e53` under `C:\pt\pl25-smoke-a` reaches mutation, visible
checks, finish and isolated `EVALUATOR_PASS`: four model turns, five actions, one accepted
mutation, acceptance PASS, safety NOT_RUN, zero cost, 4.87-second command. Envelope and
manifest match runtime hash
`sha256:e1ae0f01fc181572eea43c92e4cd6edda93d280a993bebf35b9a3c3648bff9c5`;
tool hash is `sha256:2d44849e5e5f5039e8590f08324db75723d8c56eff7f5ecb365758da7071173d`.
In-memory row-32 reprojection preserves the saved failure evidence while qualifying
turns 28/30/34 as historical; it neither reruns the candidate nor predicts model choices.
All 62 existing run journal/envelope files, `.env`, user-owned `AGENTS.md`, 1,249 tracked
task/historical files and pre-existing untracked entries are unchanged.

### Thirty-third live row: public repair and submission completed, private acceptance failed

The user separately approved one new `pyfakefs-makedirs-parent-traversal` v2 invocation:
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository `.env`, repeat 1, $1.20 total cap,
and `--enable-probes` under `C:\patchloop-state`. Read-only preflight confirmed clean
tracked runtime/task inputs, credential format, both pinned local Docker images and
registered rates matching the official [API pricing table](https://developers.openai.com/api/docs/pricing).
V25 commit `bac7c70f4063224127c2b32bb429e3712056cfb2` produced
`run_dev_6159179ed34542f9`: `EVALUATOR_FAIL`, task acceptance FAIL, safety PASS,
`PRIVATE_EVALUATION_FAILED`, 20 model/input-count calls, 20 actions, two accepted mutations,
$0.366307650, 196.811 active seconds and 198 seconds run age. All ceilings stayed at
25,000. No retry, resume, second invocation, Docker startup or image pull/build ran.
The isolated evaluator recorded hidden-tests FAIL, regression PASS and scope PASS;
its output was not reinjected into the coding agent. Every result remains `official=false`,
`claim_eligible=false`.

Fourteen inspections (eight searches, six reads) preceded the first mutation at turn 15.
The model introduced a raw-component traversal only for parent-directory paths, retaining
delegation for ordinary paths. The public contract failed at turn 16 on the intermediate
directory's mode. Turn 17 directly distinguished default parent permissions from requested
leaf mode. Turn 18 rechecked and passed; turn 19 passed upstream regression (517 passes,
570 skips); turn 20 submitted 36 additions and one deletion in `pyfakefs/fake_os.py`.
No mutation was rejected, no protocol correction occurred and no enabled probe was used.

The saved turn-17 input labels the failure current; turn 18 labels it historical and
explicitly offers `run_check` for the edited candidate. The model's public decision also
distinguishes the new candidate from the earlier diff. This observes successful delivery,
repair, recheck and submission, not causation by v25. Two mutation opportunities remained
at recheck and finish: the zero-mutations boundary responsible for row 32's untested stop
was not exercised. That targeted live behavior remains unverified. Fewer turns than row 32
is an uncontrolled trajectory difference, not an efficiency or task-success claim.

Read-only audit verifies all 20 saved inputs and 19 unchanged full-input prefixes,
matching current failure/check views, encrypted continuation order, count/dispatch hashes
and exact cost settlement. All responses report `current_turn`, not proof of effective
reasoning reuse. Input totals 895,551 tokens, including 611,712 cached (68.31%); output
totals 23,900 tokens, including 18,962 reasoning. Final input is 94,438 tokens and 425,204
serialized UTF-8 bytes; aggregate input artifacts total 3,789,254 bytes, excluding tools.
Eighteen journaled note updates contain five findings without note diagnostics.

Checked, submitted, current-worktree and isolated-applied patch identities all match
`sha256:dd779e12ae729a41e32b1c74bc994ff46b0eb96a1601dee1944e65aad90ad3cc`.
No untracked candidate files remain. Envelope, manifest and terminal/evaluator provenance
bind the preflight runtime; all three visible-check policy hashes and confirmed cleanup
records match. Journal SHA-256 is
`f7b9a178a92f21bf2ec64aa3ddf03b49c0e98b8fb4f801181c3112afdc805f8d`.
All 62 prior journal/envelope files, `.env`, user-owned `AGENTS.md`, 1,249 tracked
task/historical files and old untracked entries are unchanged. This post-run change is
documentation only. The next diagnosis should examine remaining submitted-code semantics,
without treating public PASS as complete acceptance or adding a stop/tool gate. No repair,
paid contrast, retry, resume or thirty-fourth live row is authorized by this result.

Post-run documentation validation passes three tests under `C:\pt\pl33-docs-b`, Ruff
and `git diff --check`. The full suite/mock are not repeated for this documentation-only
record; runtime and task bytes remain the preflight-verified v25 inputs.

### V24 implementation and validation checkpoint

V24 separates the model's current working view from the complete public audit context.
Each appended `harness_current_state` record contains the complete mutable view; the
model does not apply nested set/remove operations or shifting array indices. Only the
unchanged public task is inherited from the initial message. Native encrypted reasoning,
calls and results remain byte-identical, in order, with no new user boundary or history
reset. Saved inputs bind the current view; canonical contexts and journal accounting
remain complete and separate. Old envelopes are not migrated.

The view keeps current tools/budgets, completion feasibility and closure warnings,
scope headroom, full diff, current failure/check currency, notes and corrections.
`current_sources` groups exact observed deliveries and lexical headers by path/raw
file hash; action ID, output field and inclusive line ranges identify native bodies.
Gaps stay gaps and unverifiable deliveries keep complete inline fallback. No source
is read by projection. Rolling inspection cards, coverage-detail arrays, span IDs and
observation counters stay in audit evidence, not repeated model state. Search aggregates
remain visible. Older mutation/check/probe bodies use native references only when the
matching result exists; current failure and typed mutation diagnostics remain explicit.

Out-of-allowance `replace_text` reports `path_not_allowed`, `rejected_path`, the actual
public `allowed_paths`/`forbidden_paths`, and unchanged baseline identity. It explains
that inspectable helper source is not necessarily editable. The pre-apply rejection,
replay key, rollback contract, action availability and mutation input schema are unchanged.

The row-31 audit found 1,824 assignments and 24 removals in accumulated state messages.
State bookkeeping explains 267,071 of the 291,951-byte final-input growth over row 30,
not lost native results or missing notes. Both rejected helper edits had the actual
allowance in input; the old generic error omitted those path names. These findings
justify clearer presentation and feedback, not a claim that they caused every semantic
error. Optional notes/probes, tool masks, task bytes, limits, model and output cap do not change.

An initial complete-view prototype still repeated file identities and made the final
input larger. Grouping exact source deliveries/headers removed that duplication.
Read-only in-memory reprojection of all 31 saved row-31 inputs now measures 651,085
versus 727,250 final canonical UTF-8 bytes (10.5% less), and 8,853,286 versus 10,011,657
aggregate bytes (11.6% less), excluding tool schemas. All native items, 30 unchanged-prefix
edges and source path/hash/action/field/line coverage match. This is not an old-run resume,
token estimate, cache/cost claim, or proof the model would solve the task. Dynamic tool
schema changes remain a separate cache limitation.

Ruff and all 531 provider-free tests pass in four concurrent groups of 60/68/81/322
(106.93/132.22/87.18/155.04 seconds), with three opt-in Docker cases skipped, under
`C:\pt\pl24-verified-a{1,2,3,4}`. Focused conversation/input coverage passes 78 cases in
40.49 seconds; final feedback/catalog refinements pass 32 in 30.98 seconds. New cases
cover 30 rolling states, unchanged audit-only metadata, exact source gaps/hash/fallback,
direct latest-state reading, stale check identity, immutable task and path-rejection
admission-crash/replay. An older synthetic fixture omitted the task at turn start but
introduced it later; it now consistently supplies the same public task. The runtime
contract was not relaxed. The full pytest phase exceeds the two-minute target; focused
tests remain under it. No full-cycle under-two-minute claim is made.

Mock `run_dev_8e267bd533ae42dc` under `C:\pt\pl24-smoke-a` reaches one mutation, visible
checks, finish and isolated `EVALUATOR_PASS`: four model turns, five actions, acceptance
PASS, safety NOT_RUN, zero cost, 6.69-second command. Runtime hash is
`sha256:964c628f70842b392f2d404d86eb7cc4f71e489aad3da856a0428174dc8a94e2`;
tool hash is `sha256:3a114a877f58c774aca0f555b106d7361df7b3087b4c04aa2903cbb9a49853cc`.
Independent audit also verifies 13,062 projected line occurrences against original
native bodies and canonical public source. Runtime files stayed fixed through full tests/mock.

No provider/count call, Docker execution/start/pull/build, old-run resume/retry or
thirty-second live row is authorized by this implementation. `.env`, user-owned
`AGENTS.md`, task/historical files, old external state and untracked work remain protected.
Hash checks confirm all 60 existing journal/envelope files, `.env`, user-owned `AGENTS.md`
and 1,249 tracked task/historical files are unchanged; all old untracked entries remain.
All results remain `official=false`, `claim_eligible=false`.

### Thirty-second live row: stopped after the final repair without rechecking

The user separately approved one new `pyfakefs-makedirs-parent-traversal` v2 invocation:
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository `.env`, repeat 1, $1.20 total cap,
and `--enable-probes` under `C:\patchloop-state`. Read-only preflight confirmed tracked,
HEAD-clean runtime/task inputs, credential format, both pinned local Docker images and
registered prices matching the official [API pricing table](https://developers.openai.com/api/docs/pricing).
V24 commit `c62e52999b2b27ed2a015305ba344c9805986a46` produced
`run_dev_8f19af52fb0948ca`: `AGENT_STOPPED`, 34 model/input-count calls, 34 actions,
four accepted mutations, $0.778038600, 324.014 active seconds and 325 seconds run age.
All output ceilings remained 25,000. No retry, resume, second invocation, Docker startup
or image pull/build ran. There was no submission or isolated evaluation; task acceptance
and safety were not evaluated. All results remain `official=false`, `claim_eligible=false`.

Turn 13 attempted the uneditable `pyfakefs/fake_filesystem.py`. Pre-apply rejection
returned `path_not_allowed` with the actual `fake_os.py` allowance; no second disallowed
edit followed. Turn 25 made the first accepted edit, replacing delegation in the allowed
wrapper with a low-level path walk. Public traversal failures at turns 26/28 exposed a
bytes/string mismatch and incorrect intermediate-directory mode. The model repaired
those causes directly at turns 27/29. Traversal passed at turn 30, but upstream regression
at turn 31 reported five failures, 512 passes and 570 skips: `exist_ok`, empty-path and
Windows file-parent compatibility. After one read, turn 33 applied the fourth mutation
to those behaviors, leaving 49 added lines and one deletion in one tracked file.

Turn 34 selected `stop_task` with `no_safe_scoped_mutation` and cited the previous
regression failure. This was not a closed-check-tool or completion-horizon terminal:
the exact request offered `run_check`, both current checks were `NOT_RUN`, and the
previous failure was marked `awaiting_recheck` with distinct old/current diff hashes.
Before dispatch, seven model calls and 67 actions remained, versus a conditional
three-call path for two checks and finish. Accepted mutation budget was zero, so further
repair was unavailable, but checking the last repair was still possible. Its success
is unknown. The stop prose's traversal-PASS/regression-FAIL claim belongs to the older
diff, not this final candidate. Do not classify the final code from those stale verdicts.

There were 24 inspections: 14 added coverage, ten did not, with no cache hits. The first
accepted mutation was later than row 31 (turn 25 versus 23). Broad exploration and a
compatibility-sensitive rewrite still followed the explicit path feedback. One rejected
path attempt rather than two is an observation, not a controlled causal result. No probe
ran and no protocol correction occurred. Five note updates submitted six findings:
three created and three updated, all accepted, with all five receipts delivered once
in the next turn. Source changes expired the retained notes; no new findings followed
turn 26. Empty final notes are not evidence that note storage or delivery failed.

All 34 saved inputs reconstruct exactly, with 33 unchanged full-input prefixes and
matching native calls/results, encrypted reasoning and current operational state.
All responses report `current_turn`; this is delivery metadata, not proof of effective
reasoning reuse. The source catalog independently preserves 12,168 delivered line
occurrences. Canonical retained-source snapshots total 486,253 characters, with zero
duplicated inline retained-source characters in model state. Serialized input totals
11,359,517 UTF-8 bytes, final input 761,362 bytes, excluding tool schemas. These are not
token estimates or a controlled comparison with the different row-31 trajectory.

Provider usage totals 2,696,452 input tokens, including 2,047,488 cached (75.93%), and
30,612 output tokens (23,575 reasoning); final input is 177,062 tokens. Eight tool-schema
changes remain. All 34 count/dispatch hashes and cost settlements reconcile, and all
four public-check policy hashes/cleanup records pass audit; no isolated safety verdict
is inferred. Final untested diff hash is
`sha256:a6690fcbebaf70fec387f0617d53229309b20ef71ac1019f8afd5f6412843f0b`;
journal SHA-256 is `b41a434076bc51fa630e6147de81020098b5456c02908e941e3746aa863c50a4`.
No untracked candidate files remain. All 60 prior journal/envelope files, `.env`,
user-owned `AGENTS.md`, 1,249 tracked task/historical files and old untracked entries
are unchanged. Only current documentation records this result. A later diagnosis should
separate compatibility-preserving repair design, note expiry/use and stale-verdict stop
selection; the delivered data alone does not establish why the model made that choice.
No automatic repair, retry, resume or thirty-third live row is authorized.

Post-run validation passes all three documentation tests under `C:\pt\pl32-docs-a`,
Ruff and `git diff --check`. The full suite and mock are not rerun for this documentation-
only change; runtime and task bytes remain the preflight-verified v24 inputs.

### V23 implementation and validation checkpoint

V23 keeps the single user task and every encrypted reasoning/call/result item, but
replaces v22's mutable front-of-request state with an immutable initial state followed
by append-only developer-role state deltas. Each delta sets or removes exact nested
paths; unchanged fields are inherited, null/empty values are explicit, and an exact
container replacement is used when smaller than individual operations. No model
summarization, new user boundary, synthetic tool call, or paid compaction is introduced.
Already sent input items remain a byte-identical prefix of the next input. Equivalent
hydrated values generate identical delta bytes; the saved input and journal metadata
bind both the history and reconstructed current-state hash. Pending replay and uncertain
provider-dispatch handling remain unchanged. Old envelopes are not migrated.

The model-facing current source projection now references complete bodies already in
native results by action ID, output field, path, raw file hash and exact line range.
Adjacent/overlapping observations can jointly supply a range; missing lines, stale hashes,
conflicting text or more than 16 delivery references retain the complete inline fallback.
No unseen source is read. Canonical context artifacts, original results and mutation
admission retain their existing full-body and current-hash contracts. The `read_file`
description now states the existing inclusive 1–400-line rule; inputs and limits are unchanged.

The row-30 read-only audit explains this seam. Input cost rose from $0.317590050 to
$0.933049350 versus row 29 while output cost fell from $0.165379500 to $0.126819000.
Cached-input share fell from 26.18% to 8.73%. Every adjacent saved input changed its
front state before the native history, preventing that history from extending an exact
cache prefix. Six tool-schema changes remain a separate cache limitation; v23 does not
change action masks, tool ordering, model, reasoning settings, output ceiling or cap.
Source body duplication was 542,268 retained characters across 29 inputs, including
23,993 in the last input. These are character measurements, not billed-token estimates.
No source finding was submitted by the model; the initial question/concerns persisted,
so the absence of findings was not a memory-storage failure. Memory simplification is deferred.

The choice follows official [prefix-caching guidance](https://developers.openai.com/api/docs/guides/prompt-caching#preserve-conversation-history)
while preserving the active reasoning/tool sequence. Read-only, in-memory reconstruction
of all 29 row-30 saved inputs preserves every original native item and all 28 successive
input prefixes. Repeated retained-source body characters fall from 542,268 to zero.
This is not a smaller total wire claim: accumulated exact state deltas increase aggregate
canonical input bytes from 5,960,829 to 7,783,355, and the final input from 435,299 to
608,946 bytes. Tool schemas are excluded from these byte counts. A first prototype
replaced entire changed top-level fields and accumulated still more metadata; exact
nested changes reduce that overhead. No tokens, cache hit rate or dollar savings are
inferred from serialized size or ciphertext length. Historical run bytes are unchanged.

Ruff and all 518 provider-free tests pass in four concurrent groups of 60/68/60/330
(70.68/88.89/66.98/92.84 seconds), with three opt-in Docker cases skipped. New short
roots are `C:\pt\pl23-verified-a{1,2,3,4}`. The 25 new cases include exact prefix/state
reconstruction, a 256-pair nested JSON oracle, correction clearing, same-state hydration,
source identity/union/fallback and the advertised read boundary. Existing parallel,
mutation, privacy, cost-admission and crash/resume regressions pass under the new framing.
The focused conversation/contract run passes 59 cases in 12.70 seconds; the earlier
feedback refinement passes 54 in 19.52 seconds. Runtime files remained frozen during
the full suite and mock. Mock `run_dev_f84797eb6e034ce5` under `C:\pt\pl23-smoke-a`
reaches mutation, visible checks, finish and isolated `EVALUATOR_PASS`: four turns,
five actions, one accepted mutation, acceptance PASS, safety NOT_RUN, zero cost.
Mock command wall time is 4.87 seconds. Focused tests and the pytest phase stay below
two minutes; the manually orchestrated Ruff/full-suite/mock sequence took 166 seconds
including review/polling gaps and is not claimed as an under-two-minute full cycle.

These checks establish neither live cache hits nor improved model behavior/generalization.
All 58 existing journal/envelope files, `.env`, user-owned `AGENTS.md`, 1,249 tracked
task/historical files, and pre-existing untracked directory entries are preserved.
All results remain `official=false`, `claim_eligible=false`. This implementation checkpoint
authorized no provider call, Docker start/pull/build, resume, retry or thirty-first row;
the live observation below required separate exact approval.

### Thirty-first live row: cache reuse observed, public checks PASS, isolated acceptance FAIL

The user separately approved one new `pyfakefs-makedirs-parent-traversal` v2 run with
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository `.env`, repeat 1, a $1.20 cap,
and `--enable-probes` under `C:\patchloop-state`. Read-only preflight confirmed tracked,
HEAD-clean runtime/task inputs, credential format and both pinned local Docker images.
The registered standard prices matched the official [API pricing table](https://developers.openai.com/api/docs/pricing).
V23 commit `bcd85f714b3994eb6aa3ea7b6ecb690b0858a063` produced
`run_dev_7754107f07f442e4`: `EVALUATOR_FAIL`, task acceptance FAIL, safety PASS,
`PRIVATE_EVALUATION_FAILED`, 31 model/input-count calls, 31 actions, three accepted
mutations, $0.775517100, 267.171 active seconds and 268 seconds run age. All 31
output ceilings were 25,000. No retry, resume, additional invocation, Docker startup
or image pull/build ran; `official=false` and `claim_eligible=false` remain unchanged.

Turns 13 and 14 attempted to edit `pyfakefs/fake_filesystem.py`, outside the public
allowance, and were rejected before applying any candidate. The first accepted edit
at turn 23 instead added recursive parent creation in the allowed `fake_os.py` wrapper.
Traversal passed at turn 24, but upstream regression failed six file-parent/broken-link
cases at turn 25. Turn 26 guarded recursion with `lexists`; after one search, turn 28
replaced that guard with a condition limiting recursion to paths containing `..`.
Both public checks passed at turns 29/30 (regression: 517 passed, 570 skipped in 3.22
seconds). Turn 31 submitted seven added lines in one tracked file, with no untracked files.
There were 21 inspections: 17 added coverage, four did not, and none was a cache hit.
Probes were enabled but never invoked; there was no protocol correction.

The isolated task check reported one error in 12 cases: a trailing-separator traversal
path raised `FileExistsError`. In the submitted code, `dirname(name)` for a trailing
separator denotes the leaf itself without that separator. Recursive `makedirs(...,
exist_ok=True)` creates that leaf, then the final delegated call tries to create it again
with the original `exist_ok=False`. This is a semantic patch defect, not an old-workspace,
submission-hash or cost-limit failure. Public checks did not cover this combination.
No private evaluator output was reinjected, and no task/harness repair was made after the run.

All 31 canonical contexts and saved inputs reconstruct exactly; all 30 successive full
input prefixes remain unchanged. Native calls/results, encrypted continuation ordering
and state hashes reconcile. All provider responses report `current_turn`, which does
not establish effective reuse of earlier reasoning. Retained current-source bodies total
501,390 characters across canonical snapshots and zero duplicated inline characters in
the model-facing retained source projection; 374 span occurrences use native references.
Aggregate canonical input is 10,011,657 bytes and the final input 727,250 bytes, excluding
tool schemas. These are serialized-byte measurements, not token or billing estimates.

Provider usage is 2,508,902 input tokens, including 1,837,568 cached (73.24%), and 29,822
output tokens (21,060 reasoning). Input costs $0.641318100 and output $0.134199000.
Compared with row 30, cached-input share rises from 8.73% and total cost falls 26.83%,
but aggregate input grows 85.82% and final input grows from 90,851 to 178,154 tokens.
Six tool-schema transitions remain; turns 25 and 31 report zero cached tokens despite
preserved input prefixes. This is observed cache use, not a controlled estimate of the
change's savings or proof of agent efficiency. Task acceptance regressed in this row.

The model submitted 17 note updates and ten source findings across five updates: two
notes were created and then updated eight times, with no finding rejected. Sixteen
receipts appear once in the next native exchange; the finish-turn receipt remains durable
without another model turn. Two verification-resolution attempts were rejected without
blocking their checks; the final question is cleared and the advisory concern resolved
against public evidence. That resolution is not a guarantee of unseen task behavior.

All 31 count/dispatch hashes and cost settlements reconcile. Four public check policies,
three isolated check evidence records, five safety controls and five terminal artifacts
pass integrity/cleanup audit. Checked, submitted, managed-workspace and isolated-applied
patch hash is `sha256:476e1d9665c0212ba417e10f57b738d00165bd1c4cd2370c11a7a0e50fccf388`.
Journal SHA-256 is `77857a7b967ce95f1107873db795793a0b58963518b70cebe02b784f1c91729a`.
All 58 prior journal/envelope files, `.env`, user-owned `AGENTS.md`, 1,249 tracked
task/historical files and existing untracked entries remain unchanged. Only current
documentation records this result. No automatic repair, retry, resume or thirty-second
live row is authorized.

Post-run validation passes all three documentation tests, Ruff and `git diff --check`.
The full suite and mock are not rerun: only current documentation changed, while runtime
and task bytes remain identical to the provider-free validated v23 checkpoint above.

### V22 implementation and validation checkpoint

V22 corrects the native conversation boundary, not the task or action policy. A request
now contains system instructions, one replaceable harness-state JSON prefix, one stable
user task, and the complete ordered native tool episode. Every encrypted reasoning item,
canonical call, and matching public result from that episode is retained exactly once.
The state prefix stays before the user boundary: updating budgets, current evidence,
notes or a correction neither invents a new user request nor accumulates old 24k snapshots.
Historical source/check results keep their original identities and are not current evidence
merely because they remain in history. Current-source admission stays fail-closed.

The saved input artifact supplies the immutable history prefix. Each `turn_started` records
content-free history counts and a history hash; resume checks this contract and all durable
reasoning references before pending tools or a new dispatch. Reasoning-only and rejected
batches append without losing the earlier episode; pending batch replay still finishes
first. Billing uncertainty keeps terminal priority. Whole-history input is counted by the
existing cost admission, with no silent truncation or paid compaction. Tool output/run
limits remain unchanged; the 24,000-character limit bounds retained current source, not
the complete native history. Full history can increase input cost and reach the cap sooner.

Provider completion/decision events now retain `response_reasoning_context` as the reported
`current_turn`/`all_turns`, or null when unreported/unrecognized. The selected GPT-5.4 mini
request still uses medium effort, `store=false`, encrypted continuation and the existing
25k desired ceiling; no GPT-5.6-only option is added. This telemetry establishes reported
availability, not that the model used evidence effectively. All plaintext reasoning,
summaries, private task material and evaluator feedback remain outside agent inputs.

The row-29 read-only diagnosis found two distinct issues. Every saved input replaced the
actual tool episode with only its previous batch and a fresh trailing user context.
[Official reasoning guidance](https://developers.openai.com/api/docs/guides/reasoning#keeping-reasoning-items-in-context)
recommends preserving the active sequence since the last user message. Earlier integrity
audits proved ciphertext delivery, not provider-side reasoning reuse; effective mode was
not recorded. This is a structural risk, not a proven explanation of repeated inspection:
row 28 succeeded with the same framing. Row 29's executable body was present at turns
3-29, mutation was available from turn 2, and the first 26 decisions had null memory updates.

Separately, the submitted manual walker skipped the directory-type check at an existing
file target with `exist_ok=True`, and treated a trailing-separator split's empty tail as
termination, hiding parent traversal. Both defects existed in the rejected 60-line proposal
as well as the accepted 48-line edit: reducing to the unchanged 50-line cap did not introduce
them. Developer-only, provider-free in-memory public-input comparisons reproduced both,
plus premature ancestor-target rejection. They were not an isolated evaluator rerun and
were not injected into the coding agent. No task, old submission or historical run was edited.

Ruff and all 493 provider-free tests pass in four concurrent groups of 60/68/60/305
(72.78/90.91/68.34/94.61 seconds), with three opt-in Docker cases skipped. The 18 new
cases cover full-episode ordering, state field priority, correction carry, reported-mode
privacy, old-history damage, four crash boundaries, once-only mutation/provider execution,
whole-input counting and billing-uncertainty priority. The focused 54-case refinement
passes in 46.29 seconds. Final roots are `C:\pt\pl22-verified-b{1,2,3,4}`.
Mock `run_dev_719b638249c246aa` under `C:\pt\pl22-smoke-b` reaches mutation, visible checks,
finish and isolated `EVALUATOR_PASS`: four model turns, five actions, one mutation,
acceptance PASS, safety NOT_RUN and zero cost. The frozen Ruff/full-suite/mock sequence
takes 102.488 seconds, below the two-minute target. No runtime file changed during it.
An earlier full-suite pass attempt exposed a renamed test-local variable shadowing its
mock helper; that test was corrected. Review also preserved existing context field order
instead of alphabetically sorting the new state prefix. Neither change alters task behavior.
All 56 pre-existing journal/envelope files, `.env`, user-owned `AGENTS.md`, task packages,
historical directories and pre-existing untracked work are preserved.
No paid provider call, Docker start/pull/build, retry, resume, or thirtieth live row is
authorized by this change. All results remain `official=false`, `claim_eligible=false`.

### Thirtieth live row: full native history, public repair, isolated acceptance PASS

The user separately approved one new `pyfakefs-makedirs-parent-traversal` v2 run with
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository `.env`, repeat 1, a $1.20 cap,
and `--enable-probes` under `C:\patchloop-state`. Read-only preflight confirmed tracked,
HEAD-clean runtime/task inputs, credential format, and both pinned local images in the
already running Docker service. V22 commit `1caa2859d6a99c8c211c9abf6e45ef4086b140c4`
produced `run_dev_f5f058fc5761480b`: `EVALUATOR_PASS`, task acceptance PASS, safety PASS,
no failure class, 29 model/input-count calls, 28 actions, two accepted mutations,
$1.059868350, 277.578 active seconds and 279 seconds run age. Results remain
`official=false`, `claim_eligible=false`. No retry, resume, extra invocation, Docker
startup, or image pull/build ran.

The first 18 turns made 16 inspections and two baseline probes. The one inspection
without coverage was turn 1's rejected 500-line read against the unadvertised 400-line
limit, not a repeated successful observation. All 15 successful inspections added new
coverage; none was a cache hit. Turn 19 proposed a 67-line mutation,
which scope rejected and rolled back. A third baseline probe at turn 20 failed with a
Python raw-string `SyntaxError`; this was diagnostic failure, not a sandbox-policy
violation. Turn 21's 52-line candidate was also rejected, and turn 22 accepted 38 diff
lines. Turn 23 requested both checks in one response, triggering the existing
single-action batch correction without executing either check. Turns 24 and 25 ran
them separately: traversal passed, upstream regression failed five cases involving
broken links and Windows file-parent error behavior. Turn 26 immediately added a
three-line delegation guard for paths without `..`, without another read. Traversal
and upstream regression then passed at turns 27 and 28 (517 passed, 570 skipped in
3.51 seconds). Turn 29 submitted the final 41-line diff: 38 additions and three deletions
in `pyfakefs/fake_os.py`, with no untracked files. Isolated evaluation passed.

All 29 saved inputs reconstruct exactly, including the rejected parallel-check batch.
The audit verifies 58 context/input artifacts, 29 continuation artifacts, unchanged
history prefixes, 27 executed native results plus two rejection results, and one note
receipt. Every request has one stable user boundary. All 29 provider responses report
`response_reasoning_context=current_turn`; ciphertext integrity and reported mode do
not prove how effectively the model used earlier reasoning. The only memory annotation,
at turn 1, creates an open question and two advisory concerns; no source finding is
written, and both concerns remain unresolved at finish. All three probes use the empty
baseline, so this row provides no candidate-probe or source-note effectiveness evidence.

This observation has fewer zero-coverage inspections than row 29 (1/16 versus 15/30)
and an earlier first accepted edit (turn 22 versus 29), but is not a controlled causal
comparison. Full request input grows from 8,317 to 90,851 tokens; aggregate input is
1,350,165 tokens, including 117,888 cached, with 28,182 output tokens (22,079 reasoning).
All admitted output ceilings remain 25,000. Cost rises from row 29's $0.482969550 to
$1.059868350 despite fewer model calls. Do not equate this single task success with
proven efficiency, generalization, or provider-side reasoning reuse.

The checked, submitted, managed-workspace and isolated-applied patch identities match
`sha256:d364976d54ce7f5c936ffc9884b6d215488b02fee152c44248380aa313b58ebe`.
All 29 count/dispatch request hashes and usage settlements reconcile. Seven public
check/probe policies, three isolated check evidence records, three probe receipts,
five safety controls and eight terminal artifacts pass identity/cleanup audit.
Journal SHA-256 is `414bf776dc136e558e546cb997bb4b32ada3f3d3a760fbb54acf3f5a8e8572a6`.
All 56 prior journal/envelope files, `.env`, user-owned `AGENTS.md`, existing untracked
work, task packages and historical directories remain unchanged. No evaluator feedback
is reinjected into the coding agent.

The immediate post-run change only recorded this evidence in current documentation. Three documentation
tests, Ruff and `git diff --check` pass; the full suite and mock are not rerun because
runtime/task bytes remain identical to the validated v22 checkpoint. No automatic repair,
retry, resume, or thirty-first live row is authorized.

### V21 implementation and validation checkpoint

V21 removes repeated pre-observation inspection prose from the model-facing projection.
The original `turn_decision`, raw tool results, attempt cards, and encrypted continuation
remain durable and unchanged. Native input keeps the exact original call arguments;
the read/search result replaces only its echoed `inspection_intent` with an action-bound
reference. Derived ledger/outcome/attempt cards also refer to the decision instead of
copying its basis, goal, or memory annotation. Source text, actual outcomes, check errors,
coverage, cache flags, explicit notes/questions, current diff, and budgets are not redacted.
This is structural projection, not string matching or semantic judgment of the model.

References distinguish `preceding_function_call_arguments`, context-only
`latest_tool_result.inspection_intent`, and `journal_only` for historical intentions that
are not delivered now. They are marked `model_authored_pre_observation_intent`, not tool
findings. Context-only/mock delivery retains the original latest result intent once where
present. Ledger observations carry their actual action IDs, including after hydration;
identical cached reads or parallel calls never borrow another action's decision.
No tool input, system prompt, note lifecycle, policy, limit, or run schema changed.
Tool-surface identity changes to v21; old envelopes and run artifacts are not migrated.

The read-only row-28 analysis ruled out missing source as the initial repeated-read cause:
the three-line delegation body was already delivered before the model said it had not
seen the body. That pre-observation statement appeared four times in the next input.
The first source finding was only attempted at turn 14; its useful executable lines were
already observed, but its overly broad citation also included unobserved lines 893-904.
Both turn-15 findings cited the source then replaced by the same mutation and correctly
expired. The mutation hypothesis and expected behavior still reached subsequent turns;
expiry did not erase the plan. Seven existing lifecycle/feedback tests passed in 15.82
seconds during diagnosis. These observations do not establish why the model chose its
trajectory or justify mandatory notes, weaker source binding, or tighter inspection masks.

In-memory comparison of all 20 saved row-28 inputs reduces the turn-4 statement from four
copies to one. Original calls/encrypted items and all source/check/note/policy/budget
values remain exact. Total derived context length falls by 5,745 characters across those
20 inputs (turn 4: 18,426 to 18,014); this is not a measured token/cost or agent-success
improvement. Observation IDs missing from the old projection were joined from its durable
public results solely for this comparison. All 54 existing journal/envelope files remain
byte-identical. That implementation checkpoint authorized no provider or Docker execution,
retry, resume, or row 29; the live observation below required separate exact approval.

Ruff and all 475 provider-free tests pass in four concurrent groups of 60/68/60/287
(94.86/117.10/87.92/103.01 seconds), with three opt-in Docker cases skipped. External
roots are `C:\pt\pl21-verified-b{1,2,3,4}`. The 13 new projection cases pass in 2.60 seconds;
related context tests pass after updating two old expectations that required duplicate
decision prose. New tests preserve same-text source/notes, parallel ownership, cache
identity, current-envelope replay, encrypted item order, and unchanged ordered tool inputs.
Mock `run_dev_9ec8c92cf7e34e9a` under `C:\pt\pl21-smoke-b` reaches mutation, visible checks,
finish, and isolated `EVALUATOR_PASS`: four model turns, five actions, one mutation,
acceptance PASS, safety NOT_RUN, zero cost, `official=false`, and `claim_eligible=false`.
The frozen full-suite/mock sequence took 128.0 seconds, slightly over the two-minute
target; focused validation remained below it. No runtime file changed during that sequence.
System prompt length remains 7,880 characters. `.env`, user-owned `AGENTS.md`, task
packages, historical directories, and prior external run bytes were not changed.

### Twenty-ninth live row: public checks PASS, isolated task acceptance FAIL

The user separately approved one new `pyfakefs-makedirs-parent-traversal` v2 run with
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository `.env`, repeat 1, a $1.20 cap,
and `--enable-probes` under `C:\patchloop-state`. Read-only preflight confirmed HEAD-clean
tracked runtime/task inputs, credential format, and both pinned local images in the
already running Docker service. V21 commit `cb235c25d903e07948bcef31a7885140b4e13aa4`
produced `run_dev_7005744ccb5d4cc1`: `EVALUATOR_FAIL`, task acceptance FAIL, safety PASS,
failure class `PRIVATE_EVALUATION_FAILED`, 32 model/input-count calls, 35 actions, one
accepted mutation, $0.482969550, 290.593 active seconds and 292 seconds run age.
Results remain `official=false` and `claim_eligible=false`. No retry, resume, additional
invocation, Docker startup, or image pull/build ran.

The first 26 turns performed 29 reads/searches. Turn 27 attempted a 60-line candidate;
scope rejected it against the unchanged 50-line limit, returned `over_by=10`, and restored
the empty baseline. Turn 28 reread an already observed range (cache hit). Turn 29 accepted
a 48-line candidate: 47 additions and one deletion in `pyfakefs/fake_os.py`, no untracked
files. Traversal passed at turn 30, upstream regression at turn 31 (517 passed, 570 skipped
in 3.34 seconds), and finish submitted at turn 32. Isolated task acceptance then failed.
This is a semantic acceptance failure, not a provider, token-ceiling, cost, or deadline
terminal. The execution checkpoint preceded the separate diagnosis recorded above.

The final visible-check diff, submitted artifact, managed workspace, and isolated
evaluator's applied diff all match
`sha256:76b50ccc326b99a286ab1b6540d8ba0b7664922f3498c21b5093c0d8b0b2a7ad`.
Read-only audit verified the journal chain, 64 context/input artifacts, all 32 encrypted
continuation artifacts, exact reconstruction of all 32 saved inputs (31 continuation
edges), 34 next-turn native results, 30 v21 inspection-intent references, two note receipts,
two public and three evaluator policy hashes with confirmed cleanup, and five terminal
artifacts. The typed 60/50 failure and restored baseline reached the next input unchanged.
Provider usage reconciles exactly with the terminal cost; no provider errors occurred.
All 54 prior journal/envelope files, `.env`, user-owned `AGENTS.md`, existing untracked
directories, runtime, task packages, and historical directories remain unchanged.
Journal SHA-256 is `8be79cd609dcc3b276d48a8cd792918c781e48d3668878a1a48af79da856668d`.

V21 removed the redundant intent fields as designed, but did not establish better agent
efficiency: 15 of 30 inspections added no source coverage, including five cache hits.
The original delegation body was delivered by turn 2 and remained in every actual input
from turns 3-29, while the model repeatedly asked to inspect it. Two findings were first
created at turn 27 and remained after the accepted edit; earlier decisions supplied no
memory update. Probes were available on 28 turns but never invoked. Retained source peaked
at 23,997 characters; bounded omission began at turn 25 and reached 151 helper-source
lines, not loss of the repeatedly requested editable body. The first accepted mutation
moved from turn 15 in row 28 to turn 29 here. These uncontrolled observations do not prove
that deduplication worsened behavior, nor support mandatory notes/probes or tighter masks.

Post-run changes only record this evidence in current documentation. All three
documentation tests, Ruff, and `git diff --check` pass. The full suite and mock were not
rerun because runtime/task code did not change after the v21 validation checkpoint above.
No automatic repair, retry, resume, or thirtieth live row is authorized.

### V20 implementation and validation checkpoint

V20 addresses two feedback affordances identified by the public row-27 audit. A working
note citing an executed public check now retains `check_result` beside its existing
action/input/diff identity: the actual `check_id`, boolean `passed`, and bounded
`exception_type` (null when absent). These facts are copied from the durable public
result, not the model's statement. Projection adds per-citation `currency` as current,
historical, or unknown when no diff identity exists. A later mutation changes currency,
not the earlier verdict. Failed actions and non-check results get no invented check
verdict. The label includes no traceback, source body, private path, or reasoning text.
Note application/recovery, nonblocking interpretation errors, and native receipt ownership
remain unchanged; this is not semantic validation of free-form prose.

The probe description now states its existing capability: current tracked public files,
including accepted edits, are importable read-only from `/workspace`; `/tmp` is writable
scratch. Only base Python and public project code are supplied, without network or
dependency installation. The optional experiment remains diagnostic, never required-check
credit. No sandbox/profile/image, tool input shape/order, action mask, or limit changes.
The system prompt replaces overlapping memory guidance with reusable behavior rules and
explicit assumptions: refine the same fact, retain distinct facts separately, and use
the existing current-failure card instead of overwriting reusable knowledge with status.
It is shorter than v19 and adds no model call, planning step, compulsory probe, or gate.

The diagnosis distinguishes observed defects from inferred model behavior. Row 27's actual
mutation inputs contained both separator helper examples and the existing mkdir wrapper;
its code still contradicted its stated normalization/delegation intent. One later note
cited the current AttributeError check but described an earlier diff's assertion failure.
Correct original feedback was present, and zero observed lines were omitted by projection.
Both real-OS probes were baseline observations; the candidate-import capability already
existed but was not explicit in the stable tool description. These changes test delivery
and discoverability, not whether another model trajectory will solve the task.
All old run/envelope bytes remain immutable. Runtime-mismatched nonterminal resume still
rejects. This implementation checkpoint did not authorize the separately approved row 28
below; it authorized no migration, retry, or subsequent live invocation.

Final provider-free verification passes Ruff and all 462 tests in four concurrent groups
of 60/68/60/274 (71.99/88.86/66.64/76.73 seconds), with three opt-in Docker tests skipped.
The 15 new cases cover actual PASS/FAIL/unknown exception labels, cross-diff false prose,
historical verdicts after mutation, parallel native receipts, durable-note crash/replay,
privacy, missing identity, and unchanged ordered tool input structure. Rebuilt contexts
agree by public values; replay from the same saved context is exact. A synthetic fixture
was corrected to restore both check history and in-memory state before testing this.
Roots are `C:\pt\pl20-verified-a{1,2,3,4}`. Mock `run_dev_fe269097df164a83` under
`C:\pt\pl20-smoke-a` reaches mutation, visible checks, finish, and isolated `EVALUATOR_PASS`:
four model turns, five actions, one mutation, acceptance PASS, safety NOT_RUN, zero cost,
`official=false`, and `claim_eligible=false`. The final frozen Ruff/full-suite/mock sequence
took 103.5 seconds, excluding earlier focused debugging. System prompt length fell from
8,007 to 7,880 characters. No paid call or Docker execution occurred; `.env`, user-owned
`AGENTS.md`, task packages, historical directories, and existing run bytes were not changed.

### Twenty-eighth live row: submitted task acceptance and safety PASS

The user separately approved one new `pyfakefs-makedirs-parent-traversal` v2 run with
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository `.env`, repeat 1, a $1.20 cap,
and `--enable-probes` under `C:\patchloop-state`. Read-only preflight confirmed tracked
HEAD-clean runtime/task inputs, credential format, and both pinned images in the already
running Docker service. V20 commit `5dc3c2a3809bc63f27e655cda03e5b13dd231d66` produced
`run_dev_a01ff61f95be4a57`: `EVALUATOR_PASS`, task acceptance PASS, safety PASS, 20 model
and input-count calls, 21 actions, two accepted mutations, $0.193324200, 133.016 active
seconds and 134 seconds run age. No retry, resume, second invocation, Docker startup,
or image pull/build ran. Results remain `official=false` and `claim_eligible=false`.

The first edit arrived at turn 15 after eight reads and seven searches across 14 turns.
It replaced the direct backend call with parent recursion and reused the existing `mkdir`
wrapper. Turn 16's public traversal check failed its intermediate-directory permission
assertion: recursive calls incorrectly inherited the leaf's explicit mode. Turn 17
identified that cause and removed `mode=mode` from the recursive call, without an
intervening read. Traversal passed at turn 18, upstream regression at turn 19 (517 passed,
570 skipped), and finish at turn 20. Isolated evaluation then passed. The submitted
`pyfakefs/fake_os.py` diff adds 13 lines and removes one, with no untracked files.

The final visible-check diff, submitted artifact, and isolated evaluator's applied diff
all match `sha256:83653e8d441d6b8ad5fb0e917b337e4e6b72a455f6100f66ef4d6f3ad164e432`.
Read-only audit verified the journal chain, 40 context/input artifacts, all 20 encrypted
continuation artifacts and 19 exact replay edges, 20 next-turn native results, eight
note receipts, three public execution-policy hashes with confirmed cleanup, and five
terminal artifacts. Prior 52 journal/envelope files and the active runtime hash remain
unchanged. Journal SHA-256 is
`297d50ef9aa517e4d768675fae81d7edf9450cd3eb8e9caa74a99d86c50dd527`.
Post-run edits only record this result in current documentation. All three documentation
tests, Ruff, and `git diff --check` pass; the full suite and mock were not rerun because
no runtime or task code changed after the v20 checkpoint above.

This is evidence of one successful repair trajectory, not that the v20 changes caused it.
Inspection remained open and probes were exposed on all 20 turns, but no probe ran and
no note cited a check, so the new check-result labels and candidate-probe description were
not behaviorally exercised. Four inspections added no source coverage, including one
cache hit. No observed lines were omitted; retained source peaked at 9,825 characters.
Turn 3 repeated a search despite the preceding native read containing the original
delegation body. Turn 14's finding cited still-pending lines 893-904 and was correctly
rejected without blocking the read. Turn 15 created two source findings, then the same
mutation changed their cited source and expired both; no later context retained a finding.
The original verification concern survived seven unchanged updates and remained advisory
and unresolved at finish. Memory-assisted efficiency and candidate probing remain
unestablished; success on this repeatedly used development task is not generalization.
This result did not authorize the separately approved twenty-ninth row above.

### V19 implementation and validation checkpoint

V19 fixes two evidence-continuity issues found by the read-only row-26 audit, without
changing action masks, model tool inputs, budgets, task packages, or acceptance gates.
An admitted exact replacement now maps previously observed complete unchanged lines
to their post-image positions. A one-line edit no longer discards an entire larger
observation. Raw pre/post hashes and exact body comparisons bind the mapping; touched
lines still require the explicit bounded mutation post-image. Unobserved gaps remain
gaps. Merged fragments retain the existing eight-span/per-span output bounds and the
24,000-character context projection bound. Durable mutation results restore the same
evidence after a crash, using the admitted offset and verified original bytes.

Source-note rejection keeps its existing code but distinguishes `never_observed` from
`stale_current_range`, with bounded requested/current/missing range metadata. Historical
coordinates are not current text proof. Errors remain nonblocking; no partial finding,
compulsory reread, new planning action, or automatic semantic validation is introduced.
Every retained check summary carries `action_id`, `check_id`, and `diff_hash` together;
concern resolution also records the actual cited check's name. The previous check-row
selection, native body deduplication, and model-authored interpretation boundary remain.

The row-26 diagnosis is more specific than the initial annotation summary below:
T2/T14 cited pending read ranges and were correctly rejected. T26/T28 cited unchanged
lines 943-948 that had been observed before T25's one-line edit and were still visible
in the current diff, but whole-span invalidation had removed them from admitted current
source. This was not a 24k projection omission. T28's wrong check citation was a model
error with a harness inconsistency: the correct ID was present in another card, but
missing from the retained regression summary itself. These deterministic fixes do not
establish why the model chose its successful solution or guarantee another live result.
Old run/envelope bytes stay immutable; current-runtime mismatches still reject nonterminal
resume. This implementation checkpoint did not authorize the separately approved row 27
below, nor the separately approved row 28. All results remain `official=false`.

Final provider-free validation passes Ruff and all 447 tests in four concurrent groups
of 60, 68, 60, and 259 (69.70, 86.16, 64.59, and 67.54 seconds), with three opt-in
Docker tests skipped. External roots are `C:\pt\pl19-verified-c{1,2,3,4}`. The new
33 cases cover positional source reuse, missing/stale range feedback, and check citation
identity. Earlier tests that assumed evidence loss now explicitly exercise truly unseen
source or deliberate span eviction; synthetic check fixtures include durable action IDs.
Normal/crash execution agrees for insertion/deletion, LF/CRLF, duplicate anchors,
no-final-newline text, and partial-line boundaries. Drift and unseen gaps still reject.
Final mock `run_dev_41da713dc2504dea` under `C:\pt\pl19-smoke-c5` reaches isolated
`EVALUATOR_PASS`: one mutation, four mock model turns, five tool actions, task acceptance
PASS, safety NOT_RUN, zero cost, `official=false`, and `claim_eligible=false`.
The frozen Ruff/full-suite/mock sequence took 93 seconds, excluding earlier focused
debugging. No provider or Docker execution occurred during that checkpoint; `.env`,
user-owned `AGENTS.md`, task packages, historical directories, and existing external run
bytes were untouched.

### Twenty-seventh live row: mutation capacity exhausted, no submission

The user separately approved one new `pyfakefs-makedirs-parent-traversal` v2 run with
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository `.env`, repeat 1, a $1.20 cap,
and `--enable-probes` under `C:\patchloop-state`. Read-only preflight passed tracked
HEAD-clean runtime/task inputs, credential format, and both pinned images in the already
running Docker service. V19 commit `6e4efbb634fc38f6c167758b567e45ba467fea11` produced
`run_dev_e68682d51d2a4dfa`: `LIMIT_REACHED`, 29 model/input-count calls, 30 actions,
four accepted mutations, $0.349973100, 195.406 active seconds and 196 seconds run age.
There was no submission, manifest, or private evaluation. All results remain
`official=false`; no retry, resume, second invocation, Docker startup, or image pull/build ran.

The first edit came on turn 18 after ten reads, six searches, and two baseline probes
across 17 model turns. Both probes passed and observed real-OS parent traversal; neither
executed a candidate patch. The entire run used 12 reads, eight searches, two probes,
four mutations, and four public `parent-traversal-contract` checks. Five inspections
added no source coverage. The upstream regression check was never reached.

| Edit / check turns | Observed change and public result |
| --- | --- |
| 18 / 19 | A manual component walker called `get_path_separator` on `self.path`; `AttributeError` stopped execution. |
| 22 / 23 | Moving that call to `self.filesystem` exposed `AssertionError: /visible/build`: whole-path `abspath` had removed the traversal components before walking. |
| 24 / 25 | Rewriting the walker to preserve the raw path introduced another wrong helper owner, `self.path._alternative_path_separator`; another `AttributeError` stopped execution. |
| 28 / 29 | Correcting that owner exposed `FileExistsError` for `/visible/release`: the code tested existence after creating the directory and treated the newly created leaf as pre-existing. |

The final candidate changes only `pyfakefs/fake_os.py`, adding 34 lines with no deleted
lines or untracked files. Its diff hash is
`sha256:a17c99b7e53425f034a991c65a49b8c7854963c775235fe4f76f5526b81970c9`.
It failed its public check and was not submitted. The scheduler then recorded
`completion horizon exhausted before provider dispatch`, with
`blocking_resources=[accepted_mutations]`: 11 model calls and 70 tool actions remained,
but zero accepted mutations could repair the failure. The conditional minimum completion
cost was four calls. There was no turn-30 provider dispatch. Cost and output-token limits
were not exhausted; all provider responses completed normally, with at most 3,359 output tokens.

Read-only audit verified 345 hash-chained events, 87 context/input/continuation artifacts,
28 exact encrypted-reasoning replay edges, and all 19 note receipts with a following
native delivery. All 20 retained check-summary rows matched the durable action/check/diff
identities. The four mutation post-images and 11 rebound source fragments matched the
actual admitted pre/post bytes. In particular, turn 24 reused the larger function anchor
after turn 22's one-line edit without an intervening read. There were no source-range note
rejections. One finding cited a nonexistent tool result ID and was correctly excluded
without blocking its probe; it also asserted the pending probe's result prematurely.
This is a model-authored annotation error, not missing tool-result delivery.

Both probe receipts and all six execution-policy hashes verified, with cleanup confirmed.
These checks do not establish an evaluator safety result: evaluation did not run.
Inspection stayed open, so closure-warning behavior was not exercised. No successful
check/concern resolution exercised the new resolution-label path. Runtime bytes and all
50 prior journal/envelope files remained unchanged. The new journal hashes to
`sha256:dab04b152155810eee272dea18159c41e943bdb85a64d15e2cfd09dc4707d071`.
Evidence continuity worked on the exercised paths, while the generated implementation
still failed public behavior. This does not prove either v19 quality regression or model
improvement relative to row 26. This result did not authorize the separately approved row 28.

### V18 implementation and validation checkpoint

V18 improves working-memory feedback without tightening the action mask. A concern's
original `statement` is immutable; an existing-ID upsert stores its latest `progress_note`.
An exact repeat of the original or current progress returns `unchanged`, preserving the
decision and update time. A distinct question needs a new concern ID. All concerns remain
model-authored, bounded to three, advisory, and resolved only with the existing evidence rules.

Source-note receipts explicitly describe `before_tool_batch`, including the update's diff
and historical `note_ids_after_update`. Current IDs live in `working_notes.available_note_ids`.
The next native owner output also labels `working_notes_after_batch`, including only that
batch's source-note expirations. Thus a pre-mutation successful note update no longer claims
that the expired ID is still available. The durable receipt, first-owner rule, and replay stay exact.

`observed_source_index` adds at most 16 lexical Python header locations within 4,000
serialized characters, using only already delivered current source. It adds no source read,
function-extent claim, or semantic proof. A conditional one-read/search policy preview now
lists all affected tools, including optional probes/checks, instead of warning about reads
alone. Other actions, new evidence, and larger parallel batches can have different successors.
No budget, tool admission, task case, mandatory experiment, or extra model turn is added.

The row-25 read-only audit found intact core-source delivery: no omitted observed lines,
at most 19,799 of 24,000 retained source characters, and the backend special-case source
already visible. It also found pre-mutation/current-note ID ambiguity, repeated rewriting of
one concern, and incomplete closure warnings. These are feedback defects, not proof that
context size or v17 caused the model's late edit or regression. V18 tests these contracts;
they cannot show that a different prompt would have solved row 25. Existing run/envelope
bytes are not migrated. That checkpoint did not authorize the separately approved row below.

The read-only comparison also caught a navigation implementation defect before release:
the observed editable fragment started inside a docstring, so assuming an initial code
state reversed quote boundaries and hid the real `makedirs` header. Ambiguous initial
bare triple quotes now disable literal masking for that fragment; entries remain explicitly
lexical candidates, not certified symbols. Known literal openings still suppress examples.
This uses no unseen source and does not change mutation evidence admission.
Reapplying the index read-only to row 25's pre-mutation context now retains the
`pyfakefs/fake_os.py:915` header: 16 entries, five omitted candidates, and 3,213 serialized
characters. This is a projection comparison, not a replay of the model's decisions.

Final provider-free verification passes Ruff and 414 tests in three concurrent groups
of 75, 144, and 195 (90.71, 83.92, and 86.28 seconds); three opt-in Docker tests were
skipped. Separate short external roots are `C:\pt\pl18-verified-6401-{a,b,c}`.
Mock `run_dev_0fde34f908a74d5e` under `C:\pt\pl18-smoke-6401` reaches isolated
`EVALUATOR_PASS` in 5.03 seconds through one mutation, four model turns and five actions:
task acceptance PASS, safety NOT_RUN, cost zero, `official=false`, and `claim_eligible=false`.
The final frozen Ruff/full-suite/mock sequence took 98 seconds, excluding earlier debugging
and focused checks. Native feedback is exact across restart; rebuilt context values are
equivalent even if JSON key order changes, and the same persisted context reproduces the
exact model input. No provider call, Docker operation, task change, or live row ran.

### Twenty-sixth live row: submitted task acceptance and safety PASS

The user separately approved one new `pyfakefs-makedirs-parent-traversal` v2 run with
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository `.env`, repeat 1, a $1.20 cap,
and `--enable-probes` under `C:\patchloop-state`. Initial read-only preflight found Docker
unavailable and made no run/provider call. After the user started Docker, preflight passed
tracked HEAD-clean runtime/task inputs, credential format, and both pinned local images.
V18 commit `1d361e06ceeb2d4d85a68840ebe354eda7fc52f5` produced
`run_dev_306785d397d640f3`: `EVALUATOR_PASS`, task acceptance PASS, safety PASS,
28 model/input-count calls, 32 actions, three accepted mutations, $0.432518400,
243.125 active seconds and 244 seconds run age. No second invocation, resume, automatic
retry, Docker startup by PatchLoop, or image pull/build ran. `official=false` and
`claim_eligible=false` remain explicit; this is development evidence, not a quality claim.

The first edit came on call 16, compared with call 31 in row 25. It replaced whole-path
delegation with recursive traversal using the existing path/mkdir helpers. Call 17 exposed
intermediate-mode handling; call 20 changed the recursive parent call to `PERM_DEF`, and
the public traversal contract passed at call 21. Call 22's upstream regression exposed
incorrect broken-link-parent errno (17 instead of 2). Call 25 changed parent existence
testing to `lexists`, allowing the existing leaf mkdir path to produce the proper error.
The regression passed at call 26 (517 passed, 570 skipped), traversal passed again at
call 27 on that same final diff, and call 28 submitted. The final patch changes only
`pyfakefs/fake_os.py`: 18 added/one deleted line, below the unchanged 50-line bound.
Submission and both final current-diff checks bind to
`sha256:49f389e710954eeda0572a20547f3b3bef74603614f4bb616f8c6a6ff9e1b69a`.
Isolated evaluation accepted that artifact; its summary was not reinjected into the agent.

The run used 23 inspections (13 reads, 10 searches), five with no new coverage and no
cache hits. The editable `makedirs` header appeared in every source index from call 2
through 28. Retained source reached 23,979 characters and at most 38 observed lines were
omitted; the working-set bound was not increased. Two concern originals remained stable,
with separate progress and eight exact-repeat no-ops. All 22 annotation receipts with a
following turn arrived exactly once with matching post-batch IDs/diff. Four source-note
range citations and one unknown concern ID were rejected without blocking actions.
Both concerns were marked resolved on the existing finish turn. One resolution reason
claimed regression-suite evidence while its action ID actually named the traversal check:
the gateway verifies current successful evidence identity, not semantic relevance. The
regression did independently pass, but this mismatch remains a model annotation limitation.

Probes were offered on all 28 turns but never used. No inspection-closure warning was
needed, so probe use and the new closure-warning boundary were not live-exercised.
No provider/protocol error or output-ceiling exhaustion occurred (maximum 7,471 output
tokens). Read-only audit verified all 348 journal events, 84 context/input/continuation
artifact hashes, 27 reasoning replay edges, five final artifact hashes, and all five
public-check policy hashes with cleanup confirmed. Journal bytes hash to
`sha256:3b9f61aeb31a52cac79b77132ff2f6916f00a87453356a417c4413b94f9369aa`.
Row-25 bytes remain unchanged. Faster editing and successful repair are observations,
not causal evidence that one v18 feature improved the model. This result did not authorize
the separately approved twenty-seventh row recorded above.

### V17 implementation and validation checkpoint

V17 separates the currently focused question from up to three run-local public
verification concerns. Optional `memory_update.verification_updates` creates/revises a
concern by stable `vN` ID, resolves it using already completed successful current-diff
check/probe evidence and a short explanation, or explicitly dismisses it with a reason.
Source-note expiry, focus changes, and unrelated check PASS do not erase these concerns.
Decisions apply to their exact diff; an edit makes old resolutions/dismissals unresolved
again, with their prior evidence marked historical. A baseline probe cannot resolve a
concern on a later candidate. Provenance validation does not prove semantic relevance;
all interpretations remain model-authored and unverified by the harness.

Concern updates share the existing first-non-null batch owner and native annotation
receipt. They are validated independently of ordinary findings/focus and never reject
the main action. An unresolved concern is never silently evicted when the three-item
working set is full. The journal stores the complete concern state and ID allocator;
resume restores them without recomputing prior decisions from final source bytes.
The current list is in `working_notes.verification`. Older check cards label their
concern IDs as snapshots at that check's completion, not current resolution authority.

After the last required visible check, feedback now invites reviewing remaining public
concerns and choosing a useful available experiment or submission, instead of commanding
immediate submission. Mutation feedback likewise allows a relevant check or experiment.
No new tool, model step, mandatory experiment, finish blocker, budget reserve, or
task-specific correctness oracle is introduced. The current gate and all tool/cost/time
limits remain unchanged. Provider schemas explicitly include the new five-field operation
objects; legacy local synthetic updates may omit the new array. Old run/envelope bytes
are not migrated, and nonterminal runtime mismatch still rejects resume.

The motivating read-only row-24 analysis found that source delivery was intact, but
the model's explicit invalid-parent uncertainty was overwritten while fixing mode,
and its only probe tested the baseline. The final context still offered inspection,
probe, and mutation with eight model calls left, yet its latest check card said to
submit. The cue's causal effect on the model was not experimentally established.
V17 targets uncertainty tracking and feedback consistency, not a larger context or
harder action mask. Existing task packages and the failed submission remain untouched.
Provider-free verification passes 59 focused concern/note/guidance cases and Ruff.
The frozen complete suite passes 336 tests in concurrent groups of 156 and 180, using
separate short external temporary roots; three opt-in Docker tests were skipped.
This full-suite invocation exceeded the two-minute target; it is not an under-two-minute
full-cycle result. The integration mock exercises non-null concern updates, rejects
same-batch resolution without rejecting the check, and resolves from its completed
result on the existing finish turn, with no additional model calls. Separate mock
`run_dev_36964c96d4834891`, under `C:\pt\pl-v17-smoke-4829`, reaches isolated
`EVALUATOR_PASS` in 4.97 seconds through one mutation, four model turns and five actions:
task acceptance PASS, safety NOT_RUN, cost zero, and `claim_eligible=false`.
These tests verify memory/feedback contracts, not improved live model decisions.
That local checkpoint did not authorize the separately approved twenty-fifth live row below.

### Twenty-fifth live row: public regression failure, completion horizon exhausted

The user separately approved one new `pyfakefs-makedirs-parent-traversal` v2 run with
`gpt-5.4-mini-2026-03-17`, medium reasoning, `.env`, repeat 1, a $1.20 invocation cap,
and `--enable-probes` under `C:\patchloop-state`. Read-only preflight verified HEAD-clean
tracked runtime/task inputs, credential format, the running Docker server, and both
local pinned images. V17 commit `8e6eedcee705bab1fea5cad5d850e764ed14dae2` produced
`run_dev_553ec14ad0d4441c`: `LIMIT_REACHED`, 37 model/input-count calls, 38 actions,
three accepted mutations, $0.486200250, and 312.967 active seconds (314 seconds run age).
No second invocation, resume, image pull/build, Docker startup, or automatic retry ran.

Thirty inspections (18 reads, 12 searches) preceded the first mutation on call 31;
18 added no source coverage and five were cache hits. Call 14 had reproduced the
baseline failure of the public parent-traversal check. The first candidate then failed
that check on bytes/str path assembly at call 32. Call 33 repaired the type-mixing error;
call 34 exposed intermediate-directory permissions, which call 35 repaired. The same
public contract passed at call 36. These are two successful local causal repairs after
late initial exploration, not a more efficient episode.

Call 37's required upstream regression reported 1 failed, 516 passed, and 570 skipped.
Its public macOS broken-symlink-with-trailing-separator case now raised `FileExistsError`
instead of completing. The new normalized whole-path existence check rejects the link
before the original backend's trailing-separator/macOS handling can run. The remaining
candidate is a 40-line diff (39 additions, one deletion) in `pyfakefs/fake_os.py`, hash
`sha256:8274b62bfc5f492526b31564b713ddc8ec58107ed49f3163a55acd747a3c4e35`.
It was not submitted. With three model calls and 62 tool actions left, recovery required
at least four calls: edit, both invalidated checks, and finish. The runner recorded
`completion horizon exhausted before provider dispatch`; the final failure was retained
but there was no subsequent model turn. No private evaluation or final safety verdict ran.
Do not label this result `EVALUATOR_FAIL`, task-acceptance FAIL, or safety PASS.

Concern `v1` was created on call 1 and appeared unresolved in all 36 following contexts.
The model repeatedly revised this single item (30 upserts) rather than maintaining
separate concrete concerns. Its statement narrowed from broad preservation requirements
to bytes assembly. Call 22's sole resolve attempt cited a read, not successful check/probe
evidence; the annotation was rejected without rejecting the read, and its receipt arrived
in the next model input. The concern remained unresolved through the three mutations.
An unknown source-note ID was rejected on call 3; a first source finding was stored on
call 11. Later note-ID/source-range errors also received nonblocking receipts. There
were 35 note-update events and all 35 matched their once-only next native delivery.

Probes were enabled but unused. The run never reached all-required-checks-PASS, so the
new final-review cue and successful current-diff concern resolution were not exercised.
Persistence and failure feedback worked, but meaningful uncertainty decomposition,
candidate experiments, and earlier editing are not demonstrated by this observation.
It does not establish that v17 caused the longer exploration or the task regression.
No provider/protocol error or output-ceiling exhaustion occurred (maximum 10,974 output
tokens versus the 25,000 desired ceiling). Read-only audit verified 453 journal events,
111 context/input/continuation artifact hashes, all 36 continuation replay edges, and
five public-check execution-policy hashes with cleanup confirmed. Journal bytes hash to
`sha256:6ae215fdd26f709347c30eb0e578d5882255b231d227edec2ab9c5357859e5e0`.
Prior row-24 bytes remain unchanged. All results remain `official=false`; no claim or
twenty-sixth live row is authorized.

### V16 implementation and validation checkpoint

V16 fixes public search path matching and separates executable edit admission from
full recovery protection. Search globs are case-sensitive and repository-rooted:
`*`, `?`, and character classes stay in one component; a whole `**` matches zero or
more directories. Thus `**/*` includes root files and `pkg/**/*.py` includes both
direct and nested files. Queries remain literal. `searched_file_count` reports eligible,
successfully decoded files actually searched before any output truncation, distinguishing
an empty file selection from a missing string. Tracked/public admission, hidden-file
exclusion, output limits, cache/replay, and task scope matching remain unchanged.

An optional edit now requires its successful minimum successor: the edit, every
invalidated visible check, and finish. Full failure-recovery reserves are reported
separately in `action_horizon.mutation_completion_horizon` and the durable turn boundary.
When that minimum fits but full protection does not, `replace_text` remains available
with a bounded warning. Current-baseline completion and conditional post-edit completion
are distinct. Inspection/probes still preserve their existing protected budget; a probe
does not grant check credit, imply a semantic failure, or force mutation.

Working-note `status=current` explicitly means cited evidence is current, not that the
statement has been semantically revalidated. Each projected finding is labelled
`interpretation_status=model_authored_unverified`; durable source bodies and lifecycle
replay are unchanged. Guidance favors causal mechanisms, closing answered questions,
behavior-bearing citations, reconsidering claims after an edit, and public experiments
for new assumptions. Exact replacement guidance favors the smallest sufficient anchor
without unchanged signatures/docstrings. An obsolete mandatory targeted-read sentence
is removed from anchor-failure feedback. These are guidance changes, not a new planning
tool, semantic oracle, blanket note expiry, fuzzy mutation admission, or read cap.

The preceding diagnosis verified that row 23 retained the editable function throughout
turns 3-29 and the normalization call from turn 8; repetition was not evidence eviction.
It also found a real false-negative search at turn 3 and a latent policy disconnect:
after a hypothetical final probe, eight calls remained for a four-call edit/check/finish
path, but the old policy required twelve protected calls. No probe was attempted then,
so that disconnect is not established as the cause of the recorded task failure.
V16 addresses these defects without changing task bytes, global limits, output ceiling,
tool names/input field shapes or order, or old envelopes. The separately approved
twenty-fourth row below executes this runtime; no further row is authorized.

Verification passes 75 focused search/guidance/tool/note cases, 16 focused budget cases,
and Ruff. The frozen complete suite passed 287 provider-free tests: 107 in 90.79 seconds
and 180 in 104.29 seconds, concurrently with separate short external temporary roots.
Three opt-in Docker tests were skipped. Both groups emitted only a pre-existing repository
pytest-cache permission warning; no test failed. Mock `run_dev_ae0880944bfd4697`, under
`C:\pt\pl16-smoke-355ec8`, reaches isolated `EVALUATOR_PASS` through one accepted mutation,
four mock model turns and five actions in approximately five seconds. Task acceptance is
PASS, safety NOT_RUN, cost zero, and `claim_eligible=false`. The regressions cover the
eight-call diagnostic-to-edit path, exact minimum/tool/capacity boundaries, complete check
invalidation, warning hydration, root/nested search and cache/restart, and the distinction
between current citations and unverified interpretation. These are local contract tests,
not evidence that the live model will explore less or produce a correct patch.

### Twenty-fourth live row: public repair succeeds, task acceptance FAIL

The user separately approved one new `pyfakefs-makedirs-parent-traversal` v2 run with
`gpt-5.4-mini-2026-03-17`, medium reasoning, `.env`, repeat 1, a $1.20 invocation cap,
and `--enable-probes` under `C:\patchloop-state`. Read-only preflight passed the exact
tracked runtime/task, credential format, running Docker, and both local pinned images.
V16 commit `fcc8e79b11c1f3a478f07dcd894ab995ac3c1988` produced
`run_dev_89757e404d894362`: `EVALUATOR_FAIL`, task acceptance FAIL, safety PASS,
`claim_eligible=false`, and `official=false`. It used 33 model/input-count calls,
38 actions, two accepted mutations, $0.365351250, and 290.735 active seconds
(292 seconds of run age). No retry, additional run, image pull/build, or Docker startup ran.

Call 3's recursive `pyfakefs/**/*` search examined 62 eligible files and returned both
direct-child `makedirs` definitions, exercising the corrected zero-depth glob semantics.
The first finding was created on call 8, with subsequent updates and the explicit
`model_authored_unverified` interpretation label. Call 5's extra parallel memory update
received a nonblocking diagnostic. All 26 receipts with a following model turn appeared
once in the native output, without duplication in that request's user context; the final
finish-associated note update had no following turn. There were 27 note-update events.

Call 22 ran one public Python probe against the unchanged baseline, comparing real-OS
and fake-filesystem parent-traversal side effects. Its 50-byte output showed the baseline
difference; it completed in 2.844 seconds with cleanup confirmed. This was not a check of
the later candidate or a broad semantic matrix. The first mutation was accepted on call 27,
after 25 inspection turns / 29 read-search actions and that probe. Its exact anchor still
covered 20 lines; the later repair used 15. Neither was rejected, but this does not show
that the smallest-anchor guidance was fully adopted.

Call 28's public contract check failed on intermediate-directory mode. After two reads
on call 29, call 30 correctly changed recursive parent creation to `PERM_DEF`, retaining
the requested leaf mode. Both visible checks passed on calls 31-32; call 33 submitted
the same 14-line diff (13 added, one deleted) applied by isolated evaluation:
`sha256:543cd29ddfad4c629ae22fc6d1be6a3b98ef6d14e1222ce1f5560a610d57a8b3`.
Regression and scope passed. Private acceptance passed 11 of 12 cases, but a file-as-parent
case returned `ENOENT` instead of `ENOTDIR`. That is an exception-semantics failure,
not a stale submission or token/protocol terminal; private diagnostics were not reinjected.

Across the run, 16 of 31 inspections added no source coverage, including six cache hits.
The first edit still arrived late, so efficient evidence reuse is not established.
V16's minimum-path mutation admission and separate recovery warning were visible on
turns 28, 32, and 33, but no late-probe-to-repair sequence was exercised. All provider
responses completed; the largest output was 4,503 tokens, below the unchanged ceiling.

Read-only verification passed the 410-event hash chain, 99 context/input/continuation
references, six terminal artifacts, three evaluator policy artifacts, all 32 continuation
edges, 38 unique completed actions, and the exact durable cost sum. No provider or action
remains pending. Existing run bytes, `.env`, task packages, and user-owned work were
unchanged. Further diagnosis should use public evidence to examine repeated investigation
and incomplete exception handling, without copying private cases into agent context.
This observation is not a controlled comparison or generalization claim. No twenty-fifth
live row is authorized.

### V15 implementation and validation checkpoint

V15 repairs working-note lifecycle and makes annotation outcomes actionable. Notes retain
up to 24,000 characters of actually observed source per note, independently of active
read/mutation spans. Successful mutation `action_finished` events atomically bind the
rebound/expired note state outside the public tool result. Resume restores that recorded
decision rather than comparing historical mutations with the final workspace. Public
context exposes only bounded lifecycle IDs/reasons, not the retained source bodies.

An action-associated `memory_update_result` now separates note creation/update/rejection
from the main action's status. It identifies the finding, allocated or rejected note ID,
and a concrete correction without echoing rejected prose or unknown source references.
It is delivered on the first non-null update's native tool output; the same context uses
a delivery reference. Read outputs no longer duplicate unvalidated `memory_update`, while
original function-call arguments and encrypted continuation remain unchanged. Guidance
explicitly puts unanswered questions before observation and findings after observation;
new notes use null and later revisions use the ID actually allocated. No extra model
call, planning tool, hard exploration mask, or mutation/check budget is introduced.

The preceding read-only review distinguished two problems. Row 22's initial rejection
was legitimate (`pending` was not observed); subsequent updates targeted unallocated `n1`.
Bare codes reached context but did not give a clear repair receipt. Independently, a real
Git reproduction showed an unchanged note surviving one unrelated edit, disappearing
after a second, and resurrecting on resume. V15 fixes that storage/replay defect; it does
not claim that the defect caused row 22's early errors or that better memory guarantees
faster exploration. Changed or ambiguous cited text still expires, and unobserved sources
are never accepted. V14 runs/envelopes remain immutable. The separately approved v15 row
below did not authorize another row; later runs required separate approval.

Validation passes Ruff, 54 focused note/context/input cases in 35.35 seconds, and all
244 provider-free tests. The frozen full-suite groups ran concurrently: 64 passed in
90.67 seconds and 180 passed in 115.15 seconds; three opt-in real Docker cases were
skipped. New regressions cover actual sequential Git edits, LF/CRLF, changed/overlapping
ambiguous source, no resurrection, and crash before/after durable mutation completion.
Feedback regressions preserve parallel ownership, exact original calls, nonblocking
rejections, bounded private-free receipts, and normal call counts through mock evaluation.
Final mock `run_dev_b4a45c26a2e84022`, under `C:\pt\pl-v15-smoke-0d2aaa`, reaches
isolated `EVALUATOR_PASS` through one mutation, four mock model turns and five actions:
task acceptance PASS, safety NOT_RUN, cost zero, and `claim_eligible=false`. This
implementation validation made no Docker or provider call. The later approved live
observation is recorded separately below.

### Twenty-third live row: memory feedback observed, task acceptance FAIL

The user separately approved one new `pyfakefs-makedirs-parent-traversal` v2 run with
`gpt-5.4-mini-2026-03-17`, medium reasoning, `.env`, repeat 1, a $1.20 invocation cap,
and `--enable-probes` under `C:\patchloop-state`. Preflight verified tracked, HEAD-clean
runtime/task inputs, the credential format, Docker availability, and both fixed local
image identities without starting, pulling, or building anything. On committed v15
runtime `61dea7880eb11fa588f0b17a0b516215972bb089`, run `run_dev_ac4248e1b75e4ad2`
ended at `EVALUATOR_FAIL`: task acceptance FAIL, safety PASS, `claim_eligible=false`,
and `official=false`. It used 32 model/input-count calls, 34 actions, one accepted
mutation, $0.361692000, and 340.828 active seconds (342 seconds of run age).
Probes were enabled but the model did not invoke one. No retry or additional row ran.

Call 4 created `n1`, before any mutation. Call 5 tried to revise it using an incompletely
observed source range; the main read succeeded while the annotation was rejected with
`unobserved_source_range` and a concrete repair instruction. Call 7 successfully updated
the existing note. `n2` was created on call 16. There was no unknown-note-ID rejection.
Call 22's parallel batch also produced the intended nonblocking additional-update
diagnostic. All 22 note-update receipts were hash-verified against their exact next
native tool output, with delivery references rather than duplicate receipts in that
request's public context. At the accepted mutation, unchanged `n1` rebound and `n2`
expired as `source_changed`; the next context agreed. This row had only one accepted
mutation and no resume, so the multi-mutation/restart repair remains provider-free evidence.

The first edit attempt still arrived on call 27 after 26 inspection turns (28 read/search
actions). Its whole-method anchor accidentally joined two original docstring lines and
was correctly rejected before a write. Call 28 read source and call 29 supplied a matching
anchor with a revised recursive-parent implementation. The accepted diff added four lines
in `pyfakefs/fake_os.py`. Calls 30 and 31 passed both visible checks, and call 32 submitted
`sha256:938e6fdbe6ce41c12f30382fa620caf7622750ab5892fb6e63deb039d527451d`.
Visible checks and isolated evaluation used that identical artifact. Regression and scope
passed, but private acceptance reported one trailing-separator failure. The submitted
`head and tail` guard skips parent creation when splitting a slash-terminated path yields
an empty tail; the remaining delegate still loses the walked-directory side effect.
This is a semantic boundary-case failure, not a stale submitted patch, token ceiling,
or provider/protocol terminal. Private evaluation was not reinjected into agent context.

Across the run, 17 of 29 inspections added no source coverage, including three cache hits.
That zero-coverage count is unchanged from row 22 despite much earlier valid note creation;
the first accepted edit moved from call 27 to call 29. Coverage alone does not establish
that a read was useless, and these two rows are not a controlled memory-effect comparison.
The result confirms live note admission/feedback delivery but not better exploration,
semantic completeness, or agent success. Both long mutation responses completed below
the unchanged 25,000-token ceiling, and no protocol correction was needed.

Read-only verification passed the 389-event hash chain, all 96 context/input/continuation
references, five terminal artifacts, three evaluator execution-policy evidence artifacts,
34 unique completed actions, and the exact durable cost sum. There is no pending provider
or action; owned check cleanup was confirmed. The journal and prior external run bytes
were not changed by analysis. The later twenty-fourth row required separate approval.

### V14 implementation and validation checkpoint

V14 adds stable run-local note IDs and optional public Python experiments. Findings
are explicitly created, revised, consolidated, or removed by short `note_id`, rather
than silently replacing every statement citing the same source. At most six remain;
source validation, stale-note expiry, nonblocking diagnostics, and durable resume remain.
The prompt encourages preserving useful mechanism observations, reusing existing
behavior owners, and testing unverified assumptions without requiring a separate plan.

`--enable-probes` explicitly enables `run_probe(question, python_source)`; it is off by
default and bound into the run envelope, sandbox identity, and manifest. A probe costs
one model turn and one tool action and is offered only when the protected completion
and recovery budget remains afterward. It never grants visible-check credit or forces
an edit. Only a locally present pinned public Python image is accepted, with an exported
tracked public source snapshot and separately hash-bound trusted wrapper. No evaluator
image, Git metadata, credential file, or hidden overlay is mounted. Experiments have
8,000-character input, 30-second execution, and 12,000-byte combined output limits,
plus the shared deadline and exact-owned-container cleanup. Missing image fails
preflight; there is no automatic startup, pull, build, or host execution fallback.
Receipts bind source/snapshot/diff/image/policy identities into failure and evaluator
provenance. Completed results replay without execution; interrupted experiments may be
repeated only after owned cleanup in a fresh snapshot, not claimed as exactly-once code.

The twenty-first-row diagnosis is narrower than "the root mechanism disappeared from
memory": recorded contexts retained it, while four or five of six findings often
repeated wrapper details and a later same-source update weakened the mechanism note.
V14 supplies explicit memory maintenance and optional counterexample experiments;
it does not establish that either change makes the agent solve the task.

V14 provider-free validation passes Ruff and all 215 tests. The frozen full-suite groups
passed 64 cases in 84.63 seconds and 151 in 82.70 seconds, running concurrently with
separate short external temporary roots. Forty new cases cover note maintenance,
probe isolation and budgets, crash/resume, receipt integrity, and failure provenance.
A final receipt-validator alignment to the gateway's 500-character action-ID limit
was rechecked with all ten probe-provenance cases (6.52 seconds). Mock
`run_dev_0e6b57566f77420b`, under `C:\pt\pl-v14-smoke-final`, reaches isolated
`EVALUATOR_PASS` through one accepted mutation, four model turns, and five actions.
Task acceptance is PASS, safety NOT_RUN, `claim_eligible=false`, and cost zero. At that
implementation checkpoint, probe launches and Docker policies were mocked. Implementation
alone authorized neither Docker execution nor a twenty-second live row.

### Separately approved real Docker probe validation

The user subsequently approved downloading the fixed Python image and bounded synthetic
Docker verification, without provider calls, evaluator-image changes, or another live row.
The digest remains `sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de`.
Actual preflight exposed a naming defect: Docker stores `python@digest`, whereas the
runtime used `python:3.12-slim@digest`. Matching and lookup now normalize only the optional
tag, preserving repository, registry port, and digest; probe execution uses the canonical
reference too. Eight offline identity cases cover accepted aliases and rejected mismatches.

Real isolation and completed-action replay passed in
`C:\pt\pl-probe-real-b\real-probe-evidence0` (`run_dev_probevalidation_138c96e2b7644a30`).
The probe imported current modified tracked bytes, excluded synthetic secret/hidden/Git
and untracked files, enforced non-root/read-only/process restrictions, allowed ephemeral
scratch writes, and received no mandatory-check credit. Restart replay returned the same
result without another backend call or journal mutation. The 1.33-second execution left
no container. Only synthetic fixtures were used; the repository `.env` was not read/copied.

The first output-flood case (`run_dev_probevalidation_fa022e287979467c`) preserved the
12,000-byte output bound but reported cleanup uncertainty and halted the remaining tests.
An independent exact-container inspection confirmed absence. A real subprocess-pipe
regression demonstrated that stopping readers at the retention cap strands a pipe writer.
Readers now keep draining and discarding excess bytes while the existing main-thread
cleanup runs; ownership checks, failure handling, and the five-second reserve are unchanged.

The two remaining cases passed in 10.80 seconds under
`C:\pt\pl-probe-real-c\real-probe-evidence0`. The repaired flood
(`run_dev_probevalidation_872424ac8fe54e9d`) retained exactly 12,000 bytes, returned
`output_limit`, and confirmed cleanup in 1.69 seconds. The deadline case
(`run_dev_probevalidation_48e0ec7ff40b4969`) used a 6.563-second effective timeout within
a 12-second row budget, returned `timeout`/`deadline_exhausted`, and confirmed cleanup
in 7.48 seconds. Exact-container absence was independently checked in both cases.
All four actual container attempts and the completed replay remain diagnostic evidence,
not an agent-success or full sandbox-security claim. That approval did not authorize a live row.

Final regression passes Ruff and 224 provider-free tests, with three explicit Docker
tests skipped by default. The two frozen suite groups passed 64 cases in 89.66 seconds
and 160 cases in 88.00 seconds concurrently. Mock `run_dev_f5951bf0dd474039` under
`C:\pt\pl-probe-smoke-final` reaches isolated `EVALUATOR_PASS` through one mutation,
four mock model turns, and five actions; acceptance PASS, safety NOT_RUN, cost zero,
and `claim_eligible=false`. The separately enabled Docker cases passed as described
above; these were not invoked by the default suite.

### Twenty-second live row: task acceptance PASS

The user separately approved one new run of `pyfakefs-makedirs-parent-traversal` v2,
`gpt-5.4-mini-2026-03-17`, medium reasoning, `.env`, repeat 1, a $1.20 invocation cap,
and `--enable-probes` under `C:\patchloop-state`. On committed runtime
`f7849c664f43cd84d3c5badfb5b9c2b8a3beb012`, run `run_dev_309a71c0c16544ed` completed
at `EVALUATOR_PASS`: task acceptance PASS, safety PASS, `claim_eligible=false`, and
`official=false`. It used 33 model/input-count calls, 36 actions, two accepted mutations,
$0.385299450, and 315.937 seconds of active execution. No provider retry, image operation,
or additional live invocation ran.

At call 13, one optional probe observed real Linux `os.makedirs` side effects for three
string paths containing `..`/`.` and one bytes path. It returned 149 output bytes in
2.937 seconds with confirmed cleanup. Its question mentioned Windows, but its code did
not exercise Windows or compare the candidate fake implementation. This is a successful
public experiment, not evidence that the probe exhaustively validated the proposed fix.
Receipt `sha256:26819db65839c3b7f7d81013ddebe43652140ae7a2bdab97a3d673bfa42bee76`
is bound into the manifest and evaluator provenance; it grants no visible-check credit.

The first accepted edit arrived at call 27, after 25 inspection turns and the probe
(27 read/search actions plus one probe). It used recursive parent creation with existing
`self.path.split`, `exists`, `isdir`, and `self.mkdir` operations instead of manually
walking normalized components. Call 28's public check correctly localized the parent-mode
assertion. After a two-action inspection batch, call 30 changed the recursive parent mode
from the caller's mode to `PERM_DEF`, retaining the caller's mode for the leaf. Both
visible checks then passed and call 33 submitted a one-file, 14-added/1-deleted-line patch:
`sha256:6e5ba56bdbfc2022e2aef341a930b8c595b2427365a27657da5eea7d29f02ef9`.
The visible checks, submission, and isolated evaluation are bound to that same artifact.

Success does not establish efficient exploration or successful early memory maintenance.
Across the run, 17 of 29 read/search actions added no source coverage, including six cache
hits. The first note cited nonexistent tool result `pending` and was excluded; the next
five tried to update unallocated `n1` and were excluded as `unknown_note_id`. Recorded
contexts exposed these diagnostics but retained no findings before the first mutation.
A valid note was first allocated at call 30, expired after its cited source changed, and
was followed by a new current-source note and later successful updates. The trace therefore
does not support attributing this pass to improved working-memory reuse. Read-only review
of note creation/feedback motivated the v15 fixes above, not a new read cap.

The journal's 390-event hash chain, all 99 context/input/continuation artifacts, six
terminal artifacts, 36 unique completed actions, and durable cost sum passed read-only
integrity checks. All 33 responses carried continuation references; no provider or action
remained pending. This is one development success on one task, not a generalization or
official-quality claim. It authorized no subsequent row; row 23 required separate approval.

The September 5 review found remaining harness defects, not evidence that model
judgment alone explained unsuccessful runs. V12 corrects truncated/empty read evidence,
CRLF revalidation, contiguous multi-span mutation admission, and unsupported traceback
execution claims. Source projection merges observed ranges, prioritizes editable and
repair evidence within 24,000 retained characters, and deduplicates the latest native
results. Bounded run-local `memory_update` notes retain source-linked model observations
and one open question; they are not verified facts, raw reasoning, or cross-run memory.

Coverage plateau and repeated causal sites are advisory. Remaining completion and
recovery budgets determine public read/search availability, including after failures.
One order-independent calculation replaces declaration-index reserves. A rejected
optional edit does not invalidate an already checked rollback baseline. Correction
resume is journal-derived. Mutation admission binds the complete candidate diff before
atomic source replacement; recovery rejects other-file drift. A shared active deadline
reaches visible checks and isolated evaluation, with label-verified owned Docker cleanup
and partial provenance retained on timeout. Cleanup uncertainty stops all repetitions.

V13 makes the provider function schema and internal decision validator identical for
non-inspection actions: `evidence_goal` is now schema-constrained to exactly `null`.
If a provider call still fails local conversion, the journal records its public tool
name, canonical argument hash, at most four validation field paths and codes, and a
truncation flag. It never stores rejected raw arguments or validation input. The same
bounded diagnostic survives decision recovery and is included in the correction; a
second violation's terminal message names the concrete tool, field, and code.

V13 validation passes seven focused schema/diagnostic/resume cases, Ruff, and all 175
provider-free tests. The independent full-suite groups pass 64 tests in 80.06 seconds
and 111 tests in 58.33 seconds, completing concurrently in about 85 seconds. Mock run
`run_dev_d22310790c4a4696` under `C:\pt\pl-v13-smoke-a` reaches isolated
`EVALUATOR_PASS` through one accepted mutation, four mock model turns, and five actions;
task acceptance is PASS, safety NOT_RUN, `claim_eligible=false`, and provider cost zero.

A provider-free reconstruction of the nineteenth row's 39 public context boundaries
compared recorded source observations with the new projector. Editable source coverage
increased in 24 turns and decreased in none. Repeated line entries fell from 1,899 to 2;
the remaining two are inside preserved parallel native outputs, not duplicated retained
source. Maximum retained source was 18,272 characters. At turn 12, visible editable
coverage rose from 74 to 139 lines. This is an observation-selection comparison only:
no model was asked to act on the reconstructed context and no success is implied.

The v12 baseline validation passed Ruff and all 175 provider-free tests. Two independent pytest
groups pass 64 tests in 77.86 seconds and 111 tests in 57.10 seconds; the final Ruff,
parallel full suite, and mock cycle takes approximately 110 seconds including orchestration.
Mock `run_dev_935f54a2c3b84b8c`, under `C:\pt\pl-v12-smoke-final-f`, reaches isolated
`EVALUATOR_PASS` through one accepted mutation, four mock model turns, and five actions.
Task acceptance is PASS, safety NOT_RUN, `claim_eligible=false`, and provider cost zero.
Fault regressions include reordered parallel-result hydration, same-action read replay,
source-linked note upsert, unconsumed correction replay, complete-candidate crash recovery,
deadline expiry before dispatch/evaluator work, and owned-container cleanup uncertainty.
Earlier checkpoint counts and policies below describe history, not the current v17
contract. No twenty-fifth live row is authorized.

The separately authorized twentieth row used the same pyfakefs version-2 task,
`gpt-5.4-mini-2026-03-17`, medium reasoning, `.env`, one repetition, a $1.20 cap,
and a new run under `C:\patchloop-state`. Provider-free preflight passed without an
image operation. Immutable run `run_dev_7b604196d0924a0f` ended at
`INCOMPLETE_RESPONSE` after 29 model/input-count calls, 35 actions, one accepted
mutation, and $0.293222400. It performed 23 searches and 11 reads before mutating on
call 27; seven searches were zero-match and six returned only covered lines. The model
then returned completed `reasoning + function_call` responses twice, but local conversion
discarded both calls as `invalid_dev_tool_contract`. No check, submission, or evaluator ran.

Because v12 stored neither rejected arguments nor validation locations, the exact field
in those two historical calls is unknowable. A provider-free reproduction found one
concrete schema/validator mismatch consistent with the timing: `run_check` permitted a
string `evidence_goal` in the provider schema while the internal model required `null`.
V13 fixes that mismatch and makes any future conversion failure diagnosable; it does not
reinterpret the twentieth row as proof of that field value or as an agent-quality result.
The accepted edit also passed no visible check and recursively propagated the requested
leaf mode to parents, so its semantic correctness is not claimed.

The separately authorized twenty-first row used the same exact task, model, reasoning,
credential-file, repetition, cap, and external state root on committed v13 runtime
`619d684f13ee9e06abd948cb7f3f1ee286d747b1`. Immutable run
`run_dev_8ca863c580e54a18` reached submission and isolated evaluation without a provider
or local tool-contract error. It ended at `EVALUATOR_FAIL` with task acceptance FAIL,
safety PASS, `claim_eligible=false`, 34 model/input-count calls, 41 actions, two accepted
mutations, and $0.532119000 cost. Both visible checks passed on submitted patch
`sha256:7929e83dddafaf6089f06fef823c776f7257f29663864f5c75d111fd6d09cc25`.

The row spent its first 26 model turns and 33 actions on inspection. Its first replacement
was rejected for a stale anchor, then one read allowed the same proposal to apply. The
public permission assertion failed, the model correctly changed non-final traversal
directories from the requested mode to `PERM_DEF`, reran both checks, and submitted.
This confirms the v13 schema repair and failed-check action path, but not task success.
Provider-free probes derived only from the public real-`os.makedirs` contract demonstrate
that the submitted manual component walker is incomplete: `/link/../leaf` follows the
lexical parent instead of the symlink target's parent, and a trailing `/.` applies the
requested mode to the preceding directory instead of the recursive default. These are
public counterexamples to the patch; without inspecting hidden evaluator content, neither
is claimed as the exact private failing case. The remaining concerns are semantic strategy
selection and working-memory convergence, not another justification for a fixed read cap.

## Evidence state (historical checkpoints)

Ruff, the fast suite, and mock smoke pass. The current context-projection checkpoint
passed 29 tests in 16.45 seconds. The resume checkpoint passes 39 tests in 35.15
seconds. The provenance/safety checkpoint passes 54 tests in 50.43 seconds and
reaches mock `EVALUATOR_PASS` with task acceptance PASS and safety NOT_RUN. The
post-live mutation-encoding checkpoint passes Ruff and 56 tests in 50.92 seconds;
mock smoke reaches the same evaluator boundary through one accepted
`apply_git_diff` mutation. The failed-mutation continuation checkpoint passes Ruff
and 59 tests in 50.51 seconds; mock smoke still reaches that boundary. The hunk-recount
checkpoint passes Ruff and 62 tests in 55.10 seconds. Mock run
`run_dev_8ba03a7965a048c5` reaches `EVALUATOR_PASS` through one accepted mutation with
task acceptance PASS, safety NOT_RUN, `claim_eligible=false`, and zero model cost.
Provider-free retrospective run `run_dev_replay_d1d2519dbd9644f9` replayed the
fourth live row's first exact raw diff through the current gateway. Recount accepted
the mutation, all three version-1 visible checks passed on canonical diff
`sha256:317ac609a2a9e555d0c38a5bf489c1dc68edd9c81457f598dbbf81fe3570d8c7`,
and the isolated evaluator applied that same diff. Task acceptance failed with
`PRIVATE_EVALUATION_FAILED` while safety passed. This separates mutation transport
from semantic task acceptance; it is not a fifth live row or a provider result.
A preserved version-1 task and new `loguru-invalid-format-feedback` version 2 now
make the central public behavior executable. In provider-free Docker validation,
the clean base and the retrospectively replayed patch both failed the new public
contract check, while a temporary public-contract correction passed all four
visible checks and reached `finish_task`. No hidden evaluator ran for that
validation. Ruff and all 63 tests pass in 54.28 seconds. Mock run
`run_dev_99bbb59c944d4c37` reaches `EVALUATOR_PASS` with task acceptance PASS,
safety NOT_RUN, `claim_eligible=false`, and zero model cost.
The post-fifth-row tool-alignment checkpoint passes Ruff and all 69 tests in
69.15 seconds. Mock run `run_dev_6374b31034c44427` reaches the same isolated
`EVALUATOR_PASS` boundary through one accepted mutation; this is provider-free
contract evidence only.
The sixth live row reached submission and isolated Docker evaluation. All four
visible checks, the submitted artifact, and the evaluator-applied patch shared diff
`sha256:e55b934c407a36807344f2f9e378c54c10283e407b063033972183ea0f43254f`.
Task acceptance reported FAIL while safety reported PASS, but the failure came from
a private literal-phrase assertion stricter than the public version-2 contract. This
is evaluator-contract evidence, not a valid negative coding-agent verdict.
Version 3 preserves every version-2 public behavior and unchanged fixture while
replacing only the private literal oracle with a semantic call-and-reference check.
Its task content hash is
`sha256:21f5f668c4f6ef85a2c1a45f4371cbd050de0e73dfcf8605a3c398413374c15b`.
Provider-free evaluator run `run_dev_v3candidate_f1bb` applied the sixth row's exact
submitted diff and reported hidden, regression, scope, and safety PASS. A separate
evaluator run `run_dev_v3reference` reports the same four-axis PASS for the reference.
A Docker matrix made the clean base fail and all six declared known-bad patches fail
acceptance. Ruff and all 70 tests pass; mock run
`run_dev_db9548d402084112` reaches `EVALUATOR_PASS` with zero model cost.
The subsequent import-contract checkpoint makes the `patchloop.dev` and
`patchloop.verifier` package re-exports lazy and gives the runner a direct evaluator
module dependency. Fresh-process regressions verify that package imports load neither
heavy module and that both `dev.contracts`-first and `verifier.policy`-first orders
work while preserving the public exports. Ruff and all 73 tests pass in 70.71 seconds;
mock run `run_dev_d309590128764086` reaches `EVALUATOR_PASS` with task acceptance
PASS, safety NOT_RUN, `claim_eligible=false`, and zero recorded cost.
A preserved `pyfakefs-makedirs-parent-traversal` version 1 and new version 2 now
make the issue's POSIX, Windows, bytes-path, and leaf-mode traversal behavior visible
through a black-box repository API check. All environment, hidden, reference,
known-bad, and audit bytes are unchanged. Version 2 has task content hash
`sha256:276b791c4c0cb1c18fa8659f6518a172f0d05b239526c0f21a7d0d2c378def87`.
A provider-free 11-case Docker matrix made the clean base fail, accepted only the
reference, and rejected all nine declared known-bad cases. Manifest-bound evaluator
run `run_dev_pyfakefsv2reference` reported hidden, regression, scope, and safety PASS
for the same reference artifact. Ruff and all 74 tests pass in 73.40 seconds; mock
run `run_dev_55d5e74e1bd743d1` reaches `EVALUATOR_PASS` with zero recorded cost.
The seventh separately approved row used that exact pyfakefs version-2 identity,
`gpt-5.4-mini-2026-03-17`, medium reasoning, one repetition, and a $1.20 cap. Run
`run_dev_42d9c3c06c6a4be9` reached durable `LIMIT_REACHED` after 198.531 active
seconds, 40 model calls, and 86 successful read/search actions, recording
$0.27031725. Public `makedirs` source evidence was present in every context after the
first turn, including the final context with gate `needs_mutation` and one model call
remaining. The agent attempted no mutation or visible check, submitted nothing, and
ran no evaluator.
The post-seventh-row working-state checkpoint introduced a requirement for every read/search decision
to carry a bounded public hypothesis, one evidence gap, and its decision after the
result. The state is bound to action identity but excluded from the operational read
cache key, then reattached after cache lookup so revised decisions cannot receive stale
text. It survives failed reads and resume, and its decision takes precedence over the
diagnostic stagnation wording without becoming a gate. Invalid provider state becomes
a bounded protocol error without discarding completed usage. Ruff and all 78 tests
pass in 83.55 seconds. Mock run `run_dev_6c167fa301ac40c3` reaches
`EVALUATOR_PASS` with one accepted mutation, zero cost, task acceptance PASS, safety
NOT_RUN, and `claim_eligible=false`.
A subsequent no-call preflight validates the ignored, untracked repository-root `.env`
without exposing its value, confirms the version-2 task content hash
`sha256:276b791c4c0cb1c18fa8659f6518a172f0d05b239526c0f21a7d0d2c378def87`,
and matches the local evaluator image to digest
`sha256:6de3b39018eec22728567f44dfbdc3cbd31322c384f6ee3d7f328ef38165d57c`.
Runtime and selected task paths match HEAD, Docker is available, and model pricing is
registered. This preflight grants no provider or eighth-row authority.
One subsequent, separately approved eighth row used those exact inputs. Run
`run_dev_07ad1af07d22489c` reached durable `LIMIT_REACHED` after 299.562 active
seconds, 40 model calls, and 60 successful read/search actions, recording
$0.34786650. It accepted no mutation and ran no check, submission, or evaluator.
Every context after the first carried working state on every latest result. Thirty-five
of the 60 per-call decisions explicitly proposed a mutation, edit, patch, or apply
action if their evidence condition was met, yet the next model turns continued to
select only reads and searches. The final context still had gate `needs_mutation`, two
current working states, and one model call remaining.
The post-eighth action-coupling checkpoint replaces that non-binding per-call future
state with typed decisions for the actual calls. Its initial parallel-read contract
required complete decisions to match, and each mode had to match its tool family.
At that checkpoint, OpenAI input reconstructed the immediately preceding public
function calls and exact outputs with call-ID linkage while retaining `store=false`
and excluding raw reasoning and private material. Tool schemas were derived from the
current gate, unexecuted checks, a completion horizon, and bounded inspection leases.
Repeated evidence remains diagnostic-only; no
stagnation terminal was added. Per-fingerprint counts now survive unrelated new spans
and checks at the same diff. This was provider-free implementation evidence and did
not itself grant ninth-row authority.
Ruff and all 78 tests pass; the full suite completed in 114.69 seconds with an external
short temp root. Mock run `run_dev_198843ed55274f09` reached `EVALUATOR_PASS` in four
model turns and five tool actions through one accepted mutation, with task acceptance
PASS, safety NOT_RUN, `claim_eligible=false`, and zero model cost. Read-only historical
trace inspection found 23 inspection batches before the first mutation in both the
fifth and sixth rows, and a maximum of three repair reads between failed mutations on
the sixth row. The 24/3 leases preserve those observed successful paths.
The separately approved ninth row used the same pyfakefs version-2 task, model,
reasoning, `.env`, repetition, and $1.20 cap. Run `run_dev_b79d22f70ae44854`
ended at durable `PROTOCOL_VIOLATION` after three model calls, one successful search,
no mutation, and $0.0077223. Native function-call/result linkage worked on the second
request. Both the second and third responses then returned valid parallel inspect calls
whose call-specific rationales differed, violating the application's exact free-text
equality rule. The first correction was present in the third public context. This is a
contract terminal before the completion horizon or inspection lease was exercised.
The post-ninth provider-free correction retains enforced `inspect` mode across parallel
reads but permits each call's bounded rationale and evidence goal to differ, preserving
all of them on the batch card. No tenth-row authority follows from this correction.
Ruff and all 79 tests pass; the final full suite completed in 113.24 seconds with a
short external temp root. Mock run `run_dev_a7724af70efb4984` reached
`EVALUATOR_PASS` in four model turns and five tool actions through one accepted
mutation, with task acceptance PASS, safety NOT_RUN, `claim_eligible=false`, and zero
model cost.
The separately approved tenth row used the same pyfakefs version-2 tuple. Run
`run_dev_8efe75f7c8c14cbd` ended at durable `INCOMPLETE_RESPONSE` after 271.046
active seconds, 28 completed provider calls and input counts, 58 tool actions, no
accepted mutation, and $0.27773415. The first 24 inspection turns completed 23 reads
and 34 searches; the lease then removed both tools exactly as configured. Turn 25
used all 4,096 output tokens as reasoning without a tool call. The correction was
followed by a valid but expected-to-fail public check on the empty diff, which reset
the consecutive correction count. Turns 27 and 28 again used all 4,096 output tokens
as reasoning, and the latter closed the row. There was no submission or evaluator.
The immutable journal records each incomplete status, ceiling, usage, output shape,
and generic error code, but not the provider's `incomplete_details.reason`; therefore
output-ceiling exhaustion is a strong trace-based inference, not a directly preserved
historical field.
The first post-tenth provider-free correction raised the desired per-call output ceiling to
25,000, while retaining pre-dispatch reduction against the invocation-wide cost cap.
That ceiling is now part of model identity and the manifest. Future incomplete reasons
are preserved in provider, decision-recovery, correction, and terminal provenance.
Ruff and all 83 tests pass; the full suite completed in about 85.5 seconds with a
short external temp root. Mock run `run_dev_5e032eaf91ec4177` reached
`EVALUATOR_PASS` in four model turns and five tool actions through one accepted
mutation, with task acceptance PASS, safety NOT_RUN, `claim_eligible=false`, and zero
model cost. No eleventh-row authority follows from this correction.
The post-tenth provider-free successor kept that 25,000-token ceiling while fixing the
two structural boundaries exposed by the same trace. With `store=false`, OpenAI
responses request, durably store, and replay provider-encrypted reasoning in original
output order with matching calls and public results. The journal contains hashes and
counts, not ciphertext or plaintext reasoning. Missing, corrupt, reordered, or
action-mismatched continuation ends at `PROVIDER_CONTINUATION_ERROR` before another
provider or tool call. Fixed 24/3 inspection leases ceased to be action gates: actual
model/tool completion slack drives `open`, warned `last_opportunity`, and `closed`
states. Before live execution, Ruff and all 86 tests passed; the full suite completed
in 111.40 seconds (112.09 seconds wall time), and provider-free mock run
`run_dev_e961ed4d987e43b1` reached isolated `EVALUATOR_PASS`.
The separately authorized eleventh row used the same pyfakefs version-2 task,
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository-root `.env`, one repetition,
and a $1.20 cap. Run `run_dev_36d200ed199d4377` ended at durable `LIMIT_REACHED`
after 412.811 active seconds, 40 provider calls, 94 tool actions, one accepted mutation,
and $0.449133. All 40 responses stored one encrypted reasoning item; all 39 next-turn
replays preserved reasoning, function-call, and result linkage, while the journal and
public contexts contained no ciphertext. Turns 37 and 38 completed with 12,128 and
7,469 output tokens respectively, including 11,235 and 6,402 reasoning tokens, and
both emitted mutation calls rather than repeating the tenth row's 4,096-token boundary.
After 90 read/search actions, turn 36 advertised `last_opportunity` and turn 37
recorded the `inspection_open` to `execution_only` transition. Its first diff
contained an invalid bare `@@` separator and failed closed; the exact failure was
projected next, and turn 38 emitted a complete diff changing only
`pyfakefs/fake_os.py`. Both `parent-traversal-contract` and
`upstream-fake-os-regression` passed on that diff in turns 39 and 40. No model call
remained for `finish_task`, so there was no submission or evaluator execution.
The current provider-free correction leaves the 40/100 limits unchanged. Before a
required mutation it reserves one additional call for repairing a rejected first diff,
consumes that reserve after failure, and computes `completion_possible` from actual
remaining model/tool budgets as well as mutation capacity. The exact eleventh-row shape
now reaches repair, two checks, and finish at call 40 in the scheduler regression. Ruff
and all 87 tests pass; the final full suite completed in 88.79 seconds with a short
external temp root. Provider-free mock run `run_dev_22a91101f0224925` reached isolated
`EVALUATOR_PASS` in four model turns and five tool actions through one accepted
mutation, with task acceptance PASS, safety NOT_RUN, `claim_eligible=false`, and zero
provider cost.
The separately authorized twelfth row used the same pyfakefs version-2 task,
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository-root `.env`, one repetition,
and a $1.20 cap. Run `run_dev_2e95d3d85fd84e2d` ended at durable `AGENT_STOPPED`
after 281.422 active seconds, 39 provider calls, 76 tool actions, one accepted
mutation, and $0.3471675. All 39 responses stored encrypted reasoning and all 38
next-turn requests carried the linked continuation; no response was incomplete.
Turn 35 advertised the final inspection opportunity and turn 36 closed inspection
with five calls reserved. The turn-36 mutation applied, then
`parent-traversal-contract` failed on its public permissions assertion in turn 37.
Turn 38 proposed a one-line repair in `pyfakefs/fake_os.py`, but the mutation contract
rejected it because no current source span covered that file: accepting the preceding
mutation had invalidated its source span, while the exact current hunk remained only
in `last_successful_mutation` and inspection was closed. The agent explicitly stopped
in turn 39. There was no submission or evaluator execution.
This is a new harness boundary, not task-acceptance evidence. A post-check repair must
be allowed to use the current-diff-bound `last_successful_mutation` hunk as exact
anchor evidence, and the horizon must reserve one bounded failed-check repair and
recheck path rather than only a rejected-patch repair. Keep current-span validation
fail-closed for edits outside that hunk. At that checkpoint no paid retry or thirteenth
row was authorized; the later thirteenth row required separate authority.
The provider-free successor now emits a bounded `mutation_evidence` post-image with
the accepted mutation's current file hash and diff hash, restores it after resume, and
references its span ID from `last_successful_mutation`. A follow-up mutation may bind
that evidence automatically only when its exact current anchor overlaps the same-file
post-image; stale hashes and anchors outside the hunk still fail closed. Scheduler and
validator now share the same test for an allowed, tracked, current-hash mutation span,
so an unrelated span cannot expose an unusable mutation action. Completion slack holds
two calls for one recoverable mutation/check feedback event: repair plus recheck. The
reserve survives the first accepted mutation, is consumed by a rejected mutation or
failed check, and is reconstructed from durable batch results on resume.
A regression reconstructs calls 34–40 as final inspection, mutation, failed check,
repair, two passing checks, and finish. Ruff and all 90 tests pass; the complete suite
finished in 110.58 seconds with an external short temp root. Provider-free mock run
`run_dev_6979578141064297` reached isolated `EVALUATOR_PASS` in four model calls and
five tool actions through one accepted mutation, with task acceptance PASS, safety
NOT_RUN, `claim_eligible=false`, and zero provider cost. No hidden evaluator was run
against the twelfth-row repair, and no live authority follows from this correction.
The separately authorized thirteenth row used the same pyfakefs version-2 task,
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository-root `.env`, one repetition,
and a $1.20 cap. Run `run_dev_8ce8603c45e646a9` ended at durable `LIMIT_REACHED`
after 358.811 active seconds and 360 seconds of run age, with 40 provider calls,
76 tool actions, one accepted mutation, and $0.39132225 of provider cost. All 40
responses stored continuation references, no response was incomplete, and the largest
response used 8,503 output tokens. The trace contains 35 inspection batches and 71
read/search actions; nine batches yielded no new span and the longest such sequence was
three.
Four mutation calls followed. The first patch did not apply, the second violated the
paired causal-alternative fields, and the third applied. The first public check then
failed. The final repair cited the accepted mutation's current post-image together with
two IDs copied from its historical input. The old validator treated every ID as current
and stopped at an `unknown evidence span` before using the valid post-image.
There was no submission or evaluator execution.
The then-current provider-free successor separated those roles. Exact mutation inputs
remained in append-only `action_started` provenance, while the agent-facing
successful-mutation projection contained only validated `actionable_evidence_span_ids`.
Known historical IDs on a retry could be ignored only when separate current evidence
authorized the exact anchor; arbitrary unknown IDs and uncovered anchors still failed
closed. The scheduler held independent two-call reserves for rejected-mutation and
failed-check recovery, and reconstructed both from durable batches. Two consecutive
successful zero-new-span inspection batches added a soft mutation-or-stop recommendation
without changing the tool
surface. At that checkpoint, no paid retry or fourteenth live row was authorized.
Ruff and all 92 tests pass with the full provider-free suite under two minutes using an
external short temp root. Provider-free mock run `run_dev_7fc6bc7e982343e4` reached
isolated `EVALUATOR_PASS` in four model calls and five tool actions through one
accepted mutation, with task acceptance PASS, safety NOT_RUN, `claim_eligible=false`,
and zero provider cost. This is local contract evidence, not another live row.
A later provider-free retrospective copied the thirteenth run's journal and retained
workspace to `C:\patchloop-test\r13-exact-replay-f81d3f60`; the original journal and
diff hashes remained unchanged. The new gateway accepted the exact final mutation
arguments (`sha256:e028b39659724aba8633b76928ea6e50c9e77eda95697d7b92944a0512ce2fff`),
classified two input IDs as currently valid and one known historical ID as stale, and
produced one-file diff
`sha256:9ea4efc3b82e7456ce7c4956e8b291ac6b1ba4b28b522a1aa267637cf765fa40`
with no untracked files. This confirms the evidence-role false negative is fixed.
Against the locally present digest-pinned Docker image, `parent-traversal-contract`
passed, but `upstream-fake-os-regression` reported 8 failed, 509 passed, and 570
skipped. The failures cover existing error behavior for broken links, file parents,
empty paths, and trailing separators. `finish_task` therefore failed closed. The old
gateway had blocked a semantically relevant repair, but not a submission-ready one;
this result warrants no further harness relaxation. No hidden evaluator or provider
call ran, and no fourteenth-row authority follows.

The later separately authorized fourteenth row used the same version-2 task,
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository-root `.env`, one repetition,
and a $1.20 cap. Run `run_dev_86ccd39d36ab4379` ended at durable `LIMIT_REACHED`
after 352.610 active seconds and 353 seconds of run age, with 40 provider calls,
70 tool actions, two accepted mutations, and $0.42157950 of provider cost. All 40
responses completed with encrypted-continuation references; none was incomplete or
reported a provider error. It used 331,742 input tokens and 38,394 output tokens,
including 28,758 reasoning tokens; the largest response used 13,921 output tokens.
The row spent its first 32 turns inspecting. Turn 32 advertised the last inspection
opportunity and turn 33 closed inspection as promised. A mutation-contract failure
reopened one warned inspection turn, after which three raw Git diffs failed structural
application before turn 38 accepted the first patch. The central public check failed
on intermediate-directory mode. Turn 40 accepted a one-line repair but no model call
remained to recheck or finish, so there was no submission or evaluator execution.
The final repair used undefined `helpers.PERM_DEF` even though `fake_os.py` imports
`PERM_DEF` directly. A provider-free copy at
`C:\patchloop-test\r14-final-repair-e84b5ab9` changed only that identifier. Both
registered public checks then passed, including 517 upstream passes and 570 skips.
No hidden evaluator ran, so this is public repair evidence rather than task acceptance.
The trace confirms encrypted continuation and announced tool-policy transitions, while
exposing three product boundaries at that checkpoint: syntactically novel overlapping
spans rarely triggered the soft commitment cue, raw unified-diff serialization wasted
recovery turns, and failed-check repair could lose same-file symbol/import context while
inspection was closed. The active provider-free successor now addresses those three
boundaries with a coverage ledger, exact replacement mutation, unchanged-span
revalidation, and one reserved targeted read. No paid retry or fifteenth row is authorized.
Focused contract tests pass 76 cases in 82.29 seconds. Ruff and all 95 tests pass in
87.75 seconds using external temp root `C:\patchloop-test\r14-seam-full-c`. Provider-free
mock run `run_dev_c185114854c54ad6` reaches isolated `EVALUATOR_PASS` in four model
calls and five tool actions through one accepted `replace_text` mutation, with task
acceptance PASS, safety NOT_RUN, `claim_eligible=false`, and zero provider cost. This
validates local contracts only; it does not establish that a provider will use the new
evidence or mutation interface effectively.

The later separately authorized fifteenth row used the same version-2 task,
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository-root `.env`, one repetition,
and a $1.20 cap at external state root `C:\patchloop-state`. Run
`run_dev_6013912c916d4781` ended at durable `LIMIT_REACHED` after 449.030 active
seconds and 450 seconds of run age, with 40 provider calls, 46 tool actions, two
accepted mutations, and $0.4705068 of provider cost. The actions were 22 reads, 17
searches, one visible check, and six mutation attempts. The first accepted mutation at
turn 32 produced a 49-line diff; its public check failed at the first byte assertion on
line 15. Four repair attempts then proposed the same complete 56-line candidate from
that 49-line baseline, but the gateway returned only a generic scope error rather than
the observed 49 to 56 delta and 50-line limit. Turn 40 accepted a different 48-line
candidate, but no call remained to check or submit it. No evaluator ran.

All 40 responses carried durable encrypted continuation and none was incomplete or a
provider error; the largest output was 11,133 tokens under the 25,000 ceiling. The
failure was therefore not reasoning-state loss or a response ceiling. Seventeen
searches comprised seven zero-new-coverage observations, four supporting-only gains,
and six editable gains, but query novelty was still counted as progress. In addition,
turns 38 through 40 reported `completion_possible=false` while still exposing
`replace_text`. The active provider-free successor separates query novelty from actual
public-source coverage, keeps commitment active for the current diff once triggered,
returns typed baseline/candidate scope arithmetic, and writes a pre-dispatch
`LIMIT_REACHED` terminal when the minimum path no longer fits. No sixteenth live row is
authorized by this implementation.

Initial provider-free validation passed all 103 tests but took 195.256 seconds. A
profile of the slowest context test found 495 subprocesses: policy and context getters
recomputed the same Git diff 76 times and validated the same evidence file once per
span. The successor now groups evidence by path and captures one fresh public state
snapshot per scheduler decision, shared by policy and context but never cached across
tool or recovery boundaries. The focused 68-test tool/runner suite passes in 90.497
seconds, and the full 103-test suite passes in 96.713 seconds with external temp root
`C:\pt\snapshot-full-final`, restoring the two-minute target. Ruff passes. Current-code
mock run `run_dev_030e46d9a4d84395` reaches isolated `EVALUATOR_PASS` in four model calls
and five tool actions through one accepted mutation, with task acceptance PASS, safety
NOT_RUN, `claim_eligible=false`, and zero provider cost. This is local harness evidence,
not provider behavior or authority for a sixteenth live row.

The later separately authorized sixteenth row used the same version-2 task,
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository-root `.env`, one repetition,
and a $1.20 cap at `C:\patchloop-state`. Run `run_dev_6c36a082c3264559` ended at
durable `LIMIT_REACHED` after 389.391 active seconds and 390 seconds of run age, with
37 provider calls, 44 tool actions, one accepted mutation, and $0.43578705 of provider
cost. It performed 27 reads, 13 searches, three mutation attempts, and one public check.
All 37 responses stored encrypted continuation references; none was incomplete or a
provider error.

Before the first mutation, the projected context already contained a current span that
covered the complete proposed source anchor. The model nevertheless supplied a shorter
overlapping `evidence_span_ids` entry twice, and the old gateway considered only those
IDs. Both attempts failed mechanically and each failure re-armed another targeted read.
Turn 36 applied a mutation; the public check then failed at line 948 because the patch
called recursive creation with an empty parent path. Three model calls remained while
the measured repair/check/finish path required five, so the pre-dispatch completion
horizon correctly terminated the run. There was no submission or evaluator execution.

The active provider-free successor removes `evidence_span_ids` from the model-facing
`replace_text` schema. The gateway now selects the most recently observed span whose
path, current file hash, and line range cover the complete exact anchor, and journals
that binding. A recovery key also limits targeted-read repair to once per baseline and
failed anchor instead of once per repeated rejection. Tool-surface identity is `v8`;
old envelopes and journals remain immutable. This addresses the two deterministic
harness losses seen before the accepted patch while leaving its semantic check failure
as agent output. That change itself authorized no paid retry; the later seventeenth row
was separately authorized.
Ruff and all 105 provider-free tests pass; the final full suite completed in 80.787
seconds with external temp root `C:\pt\pl-v8-full-0905-c`. Mock run
`run_dev_32428b48e6b341d8` reaches isolated `EVALUATOR_PASS` in four model calls and
five tool actions through one accepted mutation. Task acceptance is PASS, safety is
NOT_RUN, `claim_eligible=false`, and provider cost is zero.

The separately authorized seventeenth row used the same pyfakefs version-2 task,
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository-root `.env`, one repetition,
and a $1.20 cap at `C:\patchloop-state`. Run `run_dev_4b32848a5621473e` ended at
durable `LIMIT_REACHED` after 320.531 active seconds and 321 seconds of run age, with
34 model/input-count calls, 42 tool actions, four accepted mutations, and $0.393104700
of provider cost. It performed 18 reads, 16 searches, four mutations, and four failed
public checks. All four mutations used the new gateway-selected current observation;
there was no evidence-ID, mutation-format, scope, provider, or continuation failure.

The first patch failed the public inline check at line 12 on `/visible/build`. The
second patch moved the first failure to line 23, the public assertion that intermediate
`/permissions/transient` has mode `0o755`. The final implementation instead passed the
requested leaf mode `0o700` to every created path component. The third and fourth
mutations changed path joining and Windows-separator handling even though line 23
continued to fail and the later Windows section had not run. Four accepted mutations
were then exhausted; the pre-dispatch horizon correctly stopped with six model calls
and 58 tool actions remaining against a five-call path blocked by mutation capacity.
There was no submission or evaluator.

This row isolates a public failure-localization and causal-pivot boundary. Raw stderr
was durable, but `<string>:23`, its exact public assertion, recurrence across diffs,
unobserved later source, and remaining mutation pressure were not joined into one
prominent state. Tool surface `v9` adds that bounded `current_public_failure` focus for
safely mapped inline Python checks, retains raw signatures separately, compares semantic
sites across diffs, survives reads and resume, and grounds causal guidance in the
current public statement. It makes no task-specific mode inference and adds no semantic
hard gate. No Docker operation, provider call, eighteenth live row, submission, or
hidden evaluation is authorized by this provider-free change.
Ruff and the focused 74-test tool/runner suite pass. All 109 provider-free tests pass
in approximately 70.5 seconds with external temp root `C:\pt\pl-v9-full-a`. Mock run
`run_dev_dd14cc24d3fa46ef` reaches isolated `EVALUATOR_PASS` in four model calls and
five tool actions through one accepted mutation; task acceptance is PASS, safety is
NOT_RUN, `claim_eligible=false`, and provider cost is zero. This verifies local wiring,
not a provider causal pivot or task-quality improvement.

The separately authorized eighteenth row used the same pyfakefs version-2 task, model,
reasoning, credential path, repetition, cap, and external state root. Immutable run
`run_dev_092cb8494e254124` ended at `AGENT_STOPPED` after 62.563 active seconds and
63 seconds of run age, with nine model/input-count calls, 16 tool actions, one accepted
mutation, one failed public check, and $0.078825000 of provider cost. It performed six
reads, seven searches, one mutation, one check, and one stop. There was no provider or
continuation error, submission, or evaluator execution.

Tool surface `v9` correctly mapped the failure to public inline line 10 and preserved
the current mutation post-image. The model then explicitly identified the redundant
final `FakeFilesystem.makedirs(normalized_path)` call as the cause of `FileExistsError`
and proposed removing or conditioning it. The scheduler nevertheless exposed only
`read_file` and `stop_task`: one old boolean treated a targeted read opportunity as a
mandatory predecessor and hid `replace_text`. Because no unresolved public evidence gap
remained, the system prompt made the ceremonial read unjustified and stop was a coherent
choice. This is a deterministic action-policy contradiction, not a failure of v9 failure
localization or missing model insight.

Tool surface `v10` separates targeted-read availability from required inspection. With
current exact mutation evidence, `replace_text` is immediately available and one
path-restricted `read_file` is merely optional when protected completion slack remains.
Without current anchor evidence, the restricted read remains required and is counted in
the minimum completion path. The gateway still validates exact current evidence, scope,
rollback, checks, and submission fail-closed; no task-specific repair is encoded.
Ruff and the focused 74-test tool/runner suite pass. All 109 provider-free tests pass in
71.998 seconds with external temp root `C:\pt\pl-v10-full-a`. Mock run
`run_dev_b5d5b2473d6a414f` reaches isolated `EVALUATOR_PASS` in four model calls and
five tool actions through one accepted mutation; task acceptance is PASS, safety is
NOT_RUN, `claim_eligible=false`, and provider cost is zero. This validates local action-
space wiring, not live use of the newly exposed repair.

The separately authorized nineteenth row used the same pyfakefs version-2 task, model,
reasoning, credential path, repetition, cap, and external state root. Immutable run
`run_dev_87185b3ce20a4333` ended at `LIMIT_REACHED` after 341.375 active seconds and
342 seconds of run age, with 39 model/input-count calls, 44 tool actions, two accepted
mutations, and $0.472921050 of provider cost. It performed 25 reads, 13 searches, three
replacement attempts (one rejected and two accepted), and three public checks. All 39
responses carried encrypted reasoning continuation. There was no submission or
evaluator execution.

The first replacement used stale docstring text in its exact anchor and was rejected.
After a targeted read, the next mutation implemented recursive parent creation. The
`parent-traversal-contract` check failed at its public intermediate-directory `0o755`
assertion. Tool surface v10 correctly exposed both immediate `replace_text` and one
optional targeted read. The model used that read to find `PERM_DEF`, repaired the parent
recursion, and the contract passed. The later `upstream-fake-os-regression` check then
failed two public broken-parent-link cases: expected `ENOENT`, observed `EEXIST`. At that
point one model call remained against a four-call repair, two-check rerun, and finish
path, so the pre-dispatch horizon correctly stopped the row.

This row confirms the v10 action-mask repair and isolates two later scheduling defects.
The sticky commitment was advisory only, so 33 inspection turns could consume nearly
all completion slack. The single shared failed-check allowance was then consumed by the
first check and did not protect a repair path for the distinct second check. Tool surface
`v11` makes the next batch after two consecutive zero-coverage batches a warned final
parallel inspection. New coverage resets the current plateau and reopens exploration;
another zero-coverage batch closes broad read/search for the current diff without a new
terminal or any restriction on targeted recovery reads. It also reserves one recovery
path per distinct visible-check ID, bounded by remaining accepted mutations and sized to
rerun earlier declared checks invalidated by a repair. No pyfakefs-specific solution is
encoded.
Focused scheduler tests and Ruff pass. All 109 provider-free tests pass in 77.62 seconds
with external temp root `C:\pt\pl-v11-full-0905-c`. Mock run
`run_dev_54650ea291e24cd0` reaches isolated `EVALUATOR_PASS` in four model calls and
five tool actions through one accepted mutation; task acceptance is PASS, safety is
NOT_RUN, `claim_eligible=false`, and provider cost is zero. This is local scheduler and
wiring evidence, not live task-quality evidence.

Read-only hydration of the third live journal recovers its full failed-diff hash,
hypothesis, `loguru/_handler.py` anchor, and patch line 27. The first live row ran on
2026-09-02:
`loguru-invalid-format-feedback`, `gpt-5.4-mini-2026-03-17`, medium reasoning,
one repetition, and a $1.20 invocation cap. Run `run_dev_e89e940c0715474e`
reached a durable `LIMIT_REACHED` terminal in 141.147 seconds after 39 model
calls and 99 successful read/search actions. It accepted no mutation, submitted
nothing, ran no evaluator, and recorded $0.07907685 of provider cost.

After the local reliability plan, a second separately approved row repeated the
same task, model, reasoning, repetition, and $1.20 cap. Run
`run_dev_9939bd27c5d04819` reached durable `LIMIT_REACHED` after 209.250 active
seconds, 40 model calls, and 92 tool actions, recording $0.25888155. All 39 prior
tool batches were present in the next context and 39 exact requests used the
evidence cache. Unlike the first row, the agent attempted mutation twice, on turns
36 and 39. Both attempts used `*** Begin Patch` wrappers and were rejected because
the runtime required a raw Git diff. It accepted no mutation, submitted nothing,
and ran no evaluator.

After the mutation wire contract was made explicit, a third separately approved
row again used the same task, model, reasoning, repetition, and $1.20 cap. Run
`run_dev_ef58e14b40834f0b` reached durable `LIMIT_REACHED` after 172.780 active
seconds, 40 model calls, and 94 tool actions, recording $0.24390525. On turn 3 the
agent called `apply_git_diff` with the required raw Git-diff prefix, so the renamed
provider tool contract was accepted. The first hunk declared 20 post-image lines
but contained 21, and fail-closed `git apply --check` rejected it at the following
hunk header with `corrupt patch at <stdin>:27`. That exact failure appeared in the
next canonical context. The remaining 37 turns returned to read/search only. No
mutation was accepted, nothing was submitted, and no evaluator ran.

After failed-mutation continuation was implemented, a fourth separately approved row
used the same task, model, reasoning, repetition, and cap. Run
`run_dev_dd7c981c6d024bcf` reached durable `LIMIT_REACHED` after 293.264 active
seconds, 40 model calls, and 72 tool actions, recording $0.343095. It attempted 13
raw-diff mutations. Every failure appeared exactly in the next context, and the
repair card remained present in all 23 turns after the first failure. All 13 diffs
still had incorrect hunk totals and none applied. A read-only
`git apply --check --recount` accepted all 13 exact diffs against the retained
isolated workspace; that establishes structural applicability after recount, not
semantic correctness. No visible check, submission, or evaluator ran.

After hunk recount and the version-2 public contract were implemented, a fifth
separately approved row used the same model, reasoning, repetition, and $1.20 cap
on task version 2. Run `run_dev_329131da9a4940c3` reached durable
`PROTOCOL_VIOLATION` after 140.703 active seconds, 29 model calls, 55 tool actions,
one accepted mutation, and $0.1743726 of recorded cost. The contract, basic-format,
and patcher-field checks passed on that diff. The remaining
`upstream-format-regression` was not called before two completed provider responses
contained no function call, so no submission or evaluator followed. A later
provider-free run of that exact remaining public check against the retained diff
passed 20 tests. This is public check evidence only; it is not part of the immutable
live run and is not task acceptance.

After the tool contract was aligned, a sixth separately approved row used the same
version-2 task, model, reasoning, repetition, $1.20 cap, and external state root.
Run `run_dev_f1bb02f3e3154bb8` reached durable `EVALUATOR_FAIL` after 227.735 active
seconds and 229 seconds of run age. It made 38 model calls and 68 tool actions,
accepted one mutation, submitted one changed file, and recorded $0.26552445. All
provider responses contained at least one function call. All four visible checks
passed on the submitted diff, and the evaluator applied that identical artifact.
Regression and scope passed and typed Docker safety was PASS. Task acceptance failed
only because the private oracle required a particular example spelling even though
the public contract explicitly allowed equivalent wording. Version 2 therefore has
an acceptance-oracle mismatch and remains frozen as evidence.

The end-to-end live path reached an evaluator summary within the 30-minute row limit;
it did not produce a contract-valid task-acceptance result. See
[Evidence and limitations](evidence.md) for the exact observation and limits.

Historical executables are recoverable at checkpoint `b71ddeee`; immutable
historical artifacts and `docs/archive/` remain preserved. Current checkout
compatibility with those runners is intentionally unsupported.

## Next decision

Preserve rows 26-29 as immutable evidence. V22's local tests establish the native episode
and replay contract, not improved agent efficiency or semantic success. Evaluate a future
separately approved row along distinct axes: full-history delivery and reported reasoning
mode; first useful edit and repeated answered questions; optional note/experiment use;
correct public repair and final acceptance. Do not equate delivered ciphertext with actual
reasoning reuse, or infer feature causality from uncontrolled row comparisons. Keep private
feedback out of coding-agent inputs. Do not add mandatory notes/probes, weaken source
validity, tighten action masks, or raise limits merely from the row-29 outcome.
Neither uncontrolled row comparisons nor this reused development task establish
generalization. No automatic repair, retry, resume, or thirtieth live row is authorized.

The preceding decision after row 25 was:

The twenty-fifth row confirms bounded concern persistence and nonblocking annotation
feedback, but not effective use of those concerns: the single item was repeatedly
rewritten, no probe ran, and the first edit was delayed until call 31. Public bytes and
mode failures were repaired; a later public compatibility regression could not be
recovered within the remaining completion horizon. Review source-note reuse, concrete
uncertainty tracking, and preservation of existing backend responsibilities before
proposing another change. Do not infer that a larger budget or harder inspection mask
is the remedy, and do not convert this one uncontrolled observation into a causal claim.
No automatic repair, retry, or twenty-sixth live row is authorized by this result.

The preceding decision after row 24 was:

The twenty-fourth row exercises the corrected recursive search, explicit note-interpretation
labels, and minimum-versus-protected mutation admission. It also recovers from a public
permission failure and submits an identical checked artifact. Those working paths did not
establish efficient exploration or complete semantics: 16 of 31 inspections added no source
coverage, the first edit came on call 27, and the submitted code returned the wrong error
for a file-as-parent case. The only probe examined the baseline, not the edited behavior.
The subsequent read-only diagnosis identified lost unresolved concerns and unconditional
submission feedback alongside the model's incomplete exception handling. V17 now implements
independent concerns and current-diff evidence-backed decisions without adding hard gates.
Local regressions can verify these contracts, not prove that the live model will use them
well or solve the task. A future separately approved run can observe that behavior.
Do not promote private cases into model prompts, infer causality from uncontrolled row
comparisons, or default to a harder read cap or larger token budget. No twenty-fifth row
is authorized by implementation or local validation.
Earlier decisions below are historical context.

The first live failure exposed a context-projection defect: successful reads were
selected by lexicographic span hash, so requested source could disappear from the
next stateless request and trigger repeated inspection. The second live row provides
bounded evidence that complete latest-batch projection and exact-request caching now
operate in a live loop. The third row confirmed raw-diff tool selection but exposed
failed-mutation displacement. The fourth row shows that displacement is fixed: the
agent kept seeing the exact failed diff and attempted 13 replacements. The fifth row
then confirmed live mutation and three public-check passes, but stopped before the
fourth public check and submission. The sixth row confirms required tool selection,
complete visible-check traversal, submission identity, evaluator execution, and typed
safety in one live path. Its task-acceptance failure instead exposes a version-2
public/private oracle mismatch. The seventh row then exposed a distinct
action-selection/commitment failure after sufficient public evidence; it did not
exercise mutation, checks, submission, evaluation, or safety.
The eighth row confirms that failure persists even when the model's own bounded
decision is projected exactly into the next turn. The ninth row did not retest that
behavior because a cross-call free-text equality rule terminated first. The tenth row
confirms that the then-current public call/result continuation, completion horizon,
and 24-turn inspection lease operated live. Its failure moved to the response boundary:
once reads were removed, three reasoning-only responses each consumed the complete
4,096-token ceiling before a tool call, with one valid public-check batch between them.
The new encrypted continuation and completion-slack policy directly replace those two
structural mechanisms; increasing the ceiling remains only auxiliary headroom.
The eleventh row confirms both replacements live: every continuation edge linked, reads
remained available beyond turn 24, the last opportunity was announced, and the closed
tool surface elicited a mutation rather than another incomplete response. Its first
malformed diff was repaired on the next turn and both visible checks passed. The new
failure boundary is narrower: the horizon retained only the best-case four-call path,
so that one repair consumed the call needed for finish.
The twelfth row confirms the added rejected-patch reserve itself live: inspection
closed at turn 36, the first mutation applied, and the next turn ran the central
visible check. That check exposed a semantic permission defect. The model then formed
a bounded one-line repair, but the gateway required a current source span that its own
successful mutation had invalidated and could no longer be reread. Even if admitted,
three remaining calls could not cover repair, both checks, and finish. The next seam
was therefore current-hunk repair evidence plus one bounded failed-check recovery path,
not a larger global token or turn limit. The provider-free successor now implements
that seam while leaving the global limits unchanged.
The thirteenth row exercised that post-image path and produced a semantically targeted
repair, but exposed two residual harness couplings. Historical pre-image IDs were still
projected beside the current post-image and were validated as if all remained actionable;
the first stale ID rejected the whole call. Separately, a mutation-format failure had
already consumed the one shared recovery allowance before the visible check failed.
The current change removes historical IDs from the actionable projection, retains them
only as provenance, and splits mutation-failure and check-failure reserves. Its soft
zero-gain signal addresses repeated inspection as guidance rather than a new terminal or
tool mask. The evidence therefore points to evidence-role classification and recovery-
budget accounting, not a need to raise the global 40-call limit.

Deterministic hunk recount was the correct narrow fix for the malformed line totals in
the earlier Loguru rows: the retrospective replay confirms that it accepts one exact
provider-emitted diff while preserving canonical submission identity. The fourteenth
row supplies different evidence. Even with recount and exact failure feedback, the
model spent three tail turns reserializing corrupt hunks. The active interface therefore
moves mechanical diff construction into the gateway as `replace_text`; this is not a
stronger repeated-read terminal and does not repair arbitrary model intent. The replayed
Loguru patch passed all version-1 visible checks but failed task acceptance, exposing a
separate public-feedback boundary: those checks covered valid-format regressions but did
not execute the issue's missing-key and catch behavior.

Task version 2 preserves version 1 and adds one black-box visible check derived only
from the public issue and repository API. It exercises actionable missing-key
feedback, available record-key reporting, the canonical `logger.bind()` /
`{extra[key]}` guidance, and both catch modes without requiring an implementation
shape or exact full sentence. Its task content hash is
`sha256:61704553b8ba733bad7350561eec397a7a6c04365a56ef61854a9e12cefe259d`.
The fifth and sixth rows used this exact identity. Version 3 preserves version 2 and
accepts the semantics promised publicly rather than one literal phrasing. The sixth
row's submitted patch passes the version-3 evaluator provider-free, but that does not
retroactively change the version-2 terminal. The eighth through fourteenth live
observations used the separate pyfakefs task described below. The fourteenth row is
terminal and no retry or fifteenth live row is authorized.

The fifth row's terminal label described the application's tool-batch boundary, but
the stored evidence did not establish that the provider response itself was
malformed. Both
zero-tool responses completed and consumed output tokens, while the old adapter
discarded non-function output without recording its shape. More importantly, the
request allowed a zero-tool response even though the runner rejected one; the
context exposed only three recent checks rather than a complete current-diff status,
and every successful-check card incorrectly asked what the public “failure” had
falsified. The correction therefore aligns the request and runner with required
tool choice, projects all current check states and the exact remaining IDs, fixes
PASS guidance, records content-free response-shape metadata, and provides a
structured unsuccessful `stop_task`. Protocol recovery now counts consecutive
violations and resets after a valid tool batch. None of these changes reinterpret
the fifth row as a submission or evaluator result.

Operational resume uses an immutable envelope, exact contract comparison,
run-lifetime locking, journal-derived counters and cost, durable tool-decision replay,
and mutation reconciliation. Pre-envelope runs remain immutable and non-resumable.
Runtime and task content are byte-bound; the manifest precedes evaluation; task
acceptance and safety remain separate typed axes. That checkpoint authorized no retry;
the later thirteenth through twenty-fourth rows were separately authorized and are now
terminal. No twenty-fifth row is authorized.

The unrelated local import edge is now fixed. Package initialization no longer
eagerly imports the development runner or evaluator core, while the existing
`patchloop.dev.run_dev` and `patchloop.verifier.EvaluationEngine` exports resolve on
first access. The runner imports the concrete evaluator module directly. Fresh-process
tests cover both formerly order-dependent imports; no task, evaluator rule, or live
evidence changed.

The first distinct post-Loguru task is provider-free validated:
`pyfakefs-makedirs-parent-traversal` version 2 preserves version 1, exposes its core
public behavior as a visible check, and passes the reference/known-bad contract
matrix. Its seventh live row nevertheless spent all 40 model calls on successful
read/search actions and ended before mutation. The exact source remained visible, so
the next seam was turn-to-turn decision continuity, not another task revision. That
post-seventh provider-free seam carried `working_hypothesis`, `evidence_gap`, and
`decision_after_result` through successful, failed, cached, and resumed reads. The
eighth row proved the projection works live but did not change tool selection: all 60
actions were reads/searches even though 35 recorded decisions explicitly contemplated
mutation. Nine cache hits and 21 zero-new-span results produced no stagnation signal;
that remains a secondary observability defect, not the cause or grounds for a hard
terminal. The provider-free correction couples each typed decision to its actual tool
family, replays the preceding public tool exchange as native Responses items, and at
that checkpoint removed exploration tools at either the completion horizon or the
inspection lease. The ninth row confirms public call/result continuation but exposes
the separate mistake of requiring distinct parallel actions to duplicate the same
free text exactly. That
relational check is now removed while common `inspect` mode and all action-level
decisions are retained. Local trace/policy verification still preserves the observed
successful 24/3 paths as history, not as a sufficient-information rule. The tenth row
exercises the old general lease and exposes the separate 4,096-token response ceiling.
The active provider-free successor keeps the 25,000-token desired ceiling under the
existing cost admission, records exact future incomplete reasons, replays encrypted
reasoning across stateless turns, and derives inspection availability from completion
slack with bounded recovery reserves. `completion_possible` reports the best path,
while `protected_completion_possible` reports whether that path plus unused recovery
allowances still fits. The twelfth row exposed the post-check repair evidence and
horizon boundary. The thirteenth then exposed stale provenance in the actionable list
and the single shared allowance. The subsequent provider-free successor separated both
evidence roles and failure reserves, and added only a soft zero-gain commitment signal.
The fourteenth row confirms those two corrections but exposes the narrower mutation-
wire, evidence-saturation, and failed-check repair-context boundaries described above.
The fifteenth row confirms exact replacement and the targeted-check path, then exposes
three deterministic harness defects: query novelty masquerading as coverage, generic
scope-failure feedback, and mutation availability after the completion path was already
impossible. The current provider-free successor measures only new public-source lines,
separates editable from supporting coverage, keeps a same-diff commitment signal sticky,
returns complete candidate scope arithmetic after rollback, and terminates before a new
dispatch when minimum completion resources are unavailable. The sixteenth row exercised
these progress, scope-feedback, and pre-dispatch horizon contracts: the horizon stopped
correctly, while model-selected evidence IDs still wasted four calls before mutation.
Tool surface `v8` removes that join key and prevents the same failure lineage from
replenishing targeted reads. The separately authorized seventeenth row confirmed that
binding on all four mutations, then exposed the public failure-localization and causal-
pivot boundary now addressed by tool surface `v9`. The separately authorized eighteenth
row confirmed that focus and the model's correct repair diagnosis, then exposed the
mandatory-read action mask. Tool surface `v10` makes that read optional when current
post-image evidence already supports `replace_text`. The separately authorized
nineteenth row confirmed that repair path, then exposed repeated investigation and the
single shared failed-check reserve. The initial `v11` response closed broad inspection
after a warned zero-coverage batch and reserved recovery by check declaration order.
The subsequent review did not establish that stronger action masking was the right
remedy: it found projection, evidence, reservation, and recovery defects. `v12` replaced
those policies with the working-memory and budget-only contracts above. The twentieth
row exercised that context but exposed the provider-schema mismatch now fixed in `v13`.
The twenty-first row crossed that repaired boundary, recovered from a public check failure,
and submitted, but still spent 26 turns inspecting before its first edit and chose a broad
manual path walker with publicly reproducible semantic gaps. This is evidence for better
decision memory and edit-strategy guidance, not grounds for another hard action mask.
The twenty-second row then passed with a recursive edit and correct mode repair, while
still exposing repeated exploration and unsuccessful early note creation. The twenty-third
row exercised v15 note feedback successfully but retained repeated exploration and failed
one semantic acceptance case after submission. The twenty-fourth row then exercised the
v16 search/admission fixes and public permission repair, but still explored late and failed
exception semantics after submission. No paid retry or twenty-fifth row is authorized.

A confirmatory lane is not considered until three distinct tasks submit without a
harness/contract terminal and at least two privately pass. That threshold opens a
design review only; it does not support a quality or generalization claim.
