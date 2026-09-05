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

Repository policy alone never initiates paid work. The twenty-four live observations below
were separately authorized. None authorized an image pull/build, automatic
Docker startup, transport retry, or additional row.

## Current implementation: tool surface v17

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
No provider/Docker execution or twenty-fifth live row is authorized by this change.

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
