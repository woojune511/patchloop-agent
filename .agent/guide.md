# Internal implementation guide

This is the agent-only companion to the required root `AGENTS.md`. It summarizes
active contracts for navigation; checked-in source remains the behavioral authority.

## Source map

```text
patchloop/dev/runner.py   loop composition, gates, context, terminal handling
patchloop/dev/tools.py    tool grammar, spans, mutations, checks, finish
patchloop/dev/state.py    append-only JSONL, action/provider recovery
patchloop/dev/cost.py     reviewed prices and pre-dispatch admission
patchloop/agent/model.py  journal-managed Responses adapter, zero retries
patchloop/repository.py   audited checkout, workspace, full diff
patchloop/sandbox/        registered checks and optional isolated public probes
patchloop/verifier/       separate private evaluation and static policy
patchloop/contracts.py    task, manifest, result, and evaluator models
tasks/                    public/private packages and declared checks
```

## Loop and tool contract

The only runtime is mutable `dev-head`. Its public workflow gates are
`needs_mutation`, `needs_visible_checks`, and `ready_to_submit`; there is no plan
state or plan tool.

One model response may request either, when that tool family is exposed by the
current gate and action horizon:

- 1–4 parallel `search_files` and/or `read_file` calls, or
- exactly one `replace_text`, `run_check`, enabled `run_probe`, `finish_task`, or
  `stop_task` call.

Every call requires one bounded public `turn_decision` with `mode`, `basis`, an
`evidence_goal` only for inspection, and nullable `memory_update`. Mode must match the tool family.
Parallel reads all use `inspect` mode, while each call may state the distinct rationale
and evidence goal for its concrete query or range. These are actions selected from
preceding public evidence, not promises about unseen results, a plan phase, or a
reasoning transcript.

The provider request uses required tool choice, and the application validates the
smaller batch grammar above. Mixed, empty, duplicate-action, and oversized batches
receive one short correction. A second consecutive protocol/incomplete violation
terminates the row; any valid completed tool batch resets the correction allowance.
Search globs are case-sensitive, repository-rooted, and component-aware: `*`, `?`,
and character classes stay within one component, while a whole `**` includes zero or
more directories. Default `**/*` includes root files. Queries are literal strings.
`searched_file_count` counts eligible decoded files actually searched before truncation;
zero files is distinct from searching files but finding no text. Keep search matching
separate from frozen task-scope matching and retain all public/tracked admission gates.
Optional inspection remains available only while both model-call and tool-action
budgets exceed the minimum path through mutation, all required checks, and finish plus
bounded failure-recovery allowances limited by remaining accepted mutations. A single
transition model accounts for every check invalidated by repair and any permitted check
order. After failure, retain `replace_text` when current observed evidence exists and
inspection while completion slack permits. Require a read only when current exact edit
evidence is absent; failure locations do not impose a path restriction. A rejected
optional proposal does not invalidate its rollback baseline or that baseline's checks.
`completion_possible` separately reports whether
the actual remaining budgets cover the best-case path;
`protected_completion_possible` includes the unused allowance. Neither is an alias
for mutation capacity.
An optional edit needs its minimum successful successor, not full recovery protection:
one edit, every invalidated visible check, and finish must fit both resource budgets.
`action_horizon.mutation_completion_horizon`, also stored at `turn_started`, reports
minimum/protected calls and feasibility separately. An affordable edit remains exposed
with a recovery warning when full protection does not fit. Neither semantic success nor
a protected post-edit path follows from the current baseline being ready to submit.
Probe failures do not become check failures or force repair; public evidence can motivate
an optional edit without granting special repair credit. Inspection/probe P floors remain.
With one optional turn left, expose reads with `last_opportunity`; with none, remove
them and record/project `tool_policy_transition`. `tools_closing_after_this_turn` uses
the actual policy's one-read/search successor with unchanged evidence and one model/tool
call consumed, including consumed repair-read credit. Warn about every affected tool,
including optional probes/checks, not just reads. The explicit prediction basis is
conditional: new evidence, other actions, and larger parallel batches can differ.
This preview must neither mutate live counters nor change admission or budgets.
Reopen them through the same transition when a changed gate restores slack. A first
source read required to establish a mutation anchor belongs to the minimum path. The
legacy 24/3 counters are telemetry, never an action mask. Corrections must be generated
from the actual allowed-tool set and must not name a missing tool.
`first_search_observation` is query-novelty telemetry only. Marginal gain requires at
least one newly covered line from a tracked public source and is split into editable and
supporting coverage. A zero-match, covered-only, shifted, or contained observation is
not new line coverage merely because its query or span hash is new. Coverage and
commitment are advisory: repeated source and negative searches can still answer useful
questions. Neither plateau nor mutation-failure counters remove tools. Clear the
advisory signal after successful mutation or check/completion transition.

An unexecuted `run_check` may be available on the first turn while the action horizon
has slack; on a changed diff it is direct completion work. A check that already failed
is not offered again on the same diff. A failed check with current exact mutation evidence
offers `replace_text` immediately and, if protected slack remains, public read/search.
The minimum path includes a source read only when current exact evidence must first be
acquired. `finish_task` is exposed only for a non-empty
diff with no untracked files after all visible checks pass on that exact diff.
`stop_task` is always exposed as an explicit unsuccessful terminal; it never submits
or evaluates.

`run_probe` is default-disabled and appears only for `--enable-probes` runs with at
least one model call and tool action beyond the protected completion budget. It uses
`verify` decision mode with `evidence_goal=null`. It accepts one public question (500
characters) and Python source (8,000 characters / 32,000 UTF-8 bytes), not a command,
image, mount, or environment supplied by the model. A probe result is diagnostic:
it never grants source-span coverage, visible-check PASS, or finish credit, and failure
does not force mutation or consume a check-repair allowance. See
[the probe runtime contract](../docker/README.md) for image and isolation details.

## Mutation and causal pivot

`replace_text` accepts one exact occurrence of `old_text` and its `new_text` in one
tracked, existing, allowed public file. The model never serializes patch headers or
hunk counts. The gateway verifies the current file and evidence anchor, performs the
replacement, then derives the bounded Git diff and canonical full worktree diff used
by checks and submission. It rejects stale or out-of-range occurrences, newline ambiguity,
untracked files, new paths, and scope violations, and restores the exact pre-image on
failure. The mutation also requires:

- `hypothesis`
- `expected_behavior`
- exact `path`, `old_text`, `new_text`, and occurrence

Prefer the smallest sufficient unique anchor; omit unchanged signatures/docstrings for
an executable-line edit and preserve observed line breaks exactly. Do not replace exact
admission with fuzzy matching. Anchor-failure feedback permits correcting from delivered
evidence; acquire missing exact evidence only when needed and allowed, not by a compulsory
one-read lease.

The model does not select or serialize evidence IDs for mutation. The gateway finds
all previously observed public spans whose actual returned content and file hash are
current, then validates their contiguous union covers the exact anchor. It journals
their IDs and the admitted anchor range. No covering current union is an
`evidence_invalid` failure with the required path/range; evidence validation remains
fail-closed.

Before invalidating edited-file
pre-image spans, a successful mutation revalidates any unchanged, uniquely occurring
span against the post-image hash. It also registers one bounded replacement post-image
span bound to the current file and diff hashes. Those spans can authorize a same-file
repair only when their contiguous observed union covers the exact current anchor;
an edit elsewhere still requires current read/search evidence. Read, search and post-image
spans contain only
complete returned lines; EOF has no span, and CRLF uses the same normalization for reads,
replacement and revalidation. Resulting paths, file count, line count, dependencies,
tests and public API remain constrained by the public task. `causal_revision` remains
optional explanatory metadata, including when the same failure site repeats.

Project `mutation_scope_budget` before mutation with complete current-diff lines/files,
limits, and remaining headroom; headroom is not the replacement's line count. If the
complete candidate violates scope, roll back first and return typed baseline, candidate,
delta, actual, limit, and overage fields. Record the restored baseline as the failed
result's workspace hash. The agent may revise, investigate, or abandon that proposal;
its failure is not an obligation to mutate an already checked baseline. Inspection
availability follows the completion budget. Admission records the complete expected
candidate diff before atomic replacement. Reconciliation must match that identity,
including after a crash before rollback, and restores an admitted over-scope candidate.

## Context boundary

The deterministic context artifact puts current workflow gate, remaining budget,
action horizon, mutation readiness, mutation scope budget, and the bounded evidence
ledger before the larger task text. It also contains the public task, current full diff, the exact latest tool
batch, a prioritized current-source working set, recent visible-check output, the
complete current-diff check status, exact remaining check IDs, bounded
`last_successful_mutation`, bounded `last_failed_mutation`, and the latest three
batch-level attempt-result-next-question cards. The ledger merges covered line ranges
per path and records canonical search observations and the latest public inspection
intent; it stores neither raw reasoning nor semantic claims inferred by the harness.
Source projection precedes policy/readiness: exact native results plus the retained
working set define delivered evidence. Retained source is bounded to 24,000 characters.
Failed/current edit anchors are atomic pins, then editable source, source-backed helper
notes, and other recent observations fill the budget. Adjacent and overlapping observed
ranges are merged; missing gaps are never read implicitly. A pin that cannot fit is
omitted whole and reported in projection metadata rather than clipped into a false anchor.
Other omitted observations retain at most 12 path/hash/range metadata entries and a
total omitted-range count, never their source body. The compact context's latest three
inspection outcomes include both read and search actions in durable observation order.
Native latest source, mutation content, and check output are not repeated in derived cards.
`observed_source_index` provides at most 16 lexical Python header candidates within
4,000 serialized characters, with exact observed path/hash/start-line metadata. Build
it only from current delivered spans, prioritize editable paths, and never read unseen
source or infer complete function extents. It is navigation, not a parsed symbol table
or semantic authority; a partial fragment's unseen enclosing string state is unknown.
If its first multiline delimiter is a bare triple quote and the fragment does not
start at file line 1, do not guess quote polarity to suppress header candidates.
The row-25 public fragment began inside a docstring; assuming code hid its real editable
header. Explicit lexical qualification handles this ambiguity without reading more source.
`memory_update` adds at most two findings of 400 characters with one or two observed
source-range or prior tool-result references and a 500-character open question or null.
Only the first non-null update per batch is considered, before that batch executes;
extra updates are diagnosed and ignored. Stable IDs (`n1`, `n2`, ...) are independent
of citations: `note_id=null` creates; an existing ID updates that note even if its
references change. `remove_note_ids` explicitly consolidates redundant notes. Unknown
IDs, invalid metadata, or invalid source references produce bounded diagnostics without
rejecting the action. Accepted-mutation references bind the actual output diff.
Unique `working_notes_updated` events record allocations, removals, evictions, and
retained IDs, and hydrate at most six model-authored findings. Source notes
retain their actually observed bodies separately from active source spans, with a
24,000-character total body bound per note. Over-bound citations reject only that note
with a narrower-citation hint. Successful mutation `action_finished` payloads atomically
bind `working_notes_state` outside the public result; hydrate replays that snapshot,
never recomputing historical lifecycle decisions from the final filesystem. Unique
unchanged text rebinds; changed or ambiguous text expires without later resurrection.
`last_source_lifecycle` exposes only triggering action, rebound IDs, and expiry reasons.
Old tool-result references remain historical.
These are public run-local notes, not raw reasoning or cross-run memory retrieval.
The separate `working_notes.verification` projection retains up to three model-authored
public verification concerns. `memory_update.verification_updates` accepts at most three
operations: `upsert`, `resolve`, or `dismiss`, each with explicit nullable concern_id,
statement, evidence_action_id, and reason. Null ID creates a stable `vN` ID with an
immutable original statement. Existing-ID upsert stores its statement as progress_note
about that original, reopening only for changed progress. Repeating the original or
latest progress returns applied/unchanged without modifying state, decision, or update
time. A distinct concern needs a new null-ID upsert. Focus changes, source-note expiry,
and check PASS never resolve
unrelated concerns. Empty/omitted updates preserve them. Independent annotation parsing
keeps valid findings/focus and the main action usable after a bad concern update.
Resolution requires a prior completed successful current-diff public check/probe and a
short reason. The gateway binds action/input/diff identity, not semantic coverage;
dismissal is only model judgment. Both decisions become historical after a diff change
and the retained concern reopens. When full, new concerns may replace currently resolved
or dismissed entries, never silently evict unresolved ones. Journaled verification_state
retains items and the ID allocator independently of source lifecycle snapshots. The same
first-non-null batch owner receives one native verification receipt; no private evaluator
result is admissible evidence. A final-PASS card invites affordable useful verification
or submission, labels its concern IDs as a check-time snapshot, and adds no finish gate.
Each projected finding has `interpretation_status=model_authored_unverified`.
Legacy `status=current` means only that its cited evidence is current; the harness does
not revalidate the statement's meaning. Cite behavior-bearing source, retain the causal
mechanism rather than repeated wrapper locations, and close answered questions. Revisit
behavior claims against observed post-image evidence after edits even if citations survive.
Notes may retain observed mechanisms, the chosen implementation approach, and untested
behavior. The system prompt encourages reuse of existing responsibilities and asks
whether another inspection can change the edit or next check. These remain optional
concise findings, not a mandatory plan or a harness guarantee of semantic correctness.
`memory_update=null` preserves the notes and question; `open_question=null` inside an
update resolves the question. The harness does not automatically merge similar prose.
Before an observation, use an open question or null update; findings may cite only
source/results observed before the current batch. The next native output carries the
owner call's `memory_update_result`, independently of main-action status. Its bounded
per-finding outcomes identify created/updated/rejected IDs and a recovery hint; separate
batch/removal diagnostics never repeat the finding's message. Context uses a delivery
reference for that receipt and otherwise labels the last receipt by turn/action. Do not
confuse its `scope=before_tool_batch`, `diff_hash_at_update`, and historical
`note_ids_after_update` with current availability. `working_notes.available_note_ids`
is current retained-ID authority. The native owner output's `working_notes_after_batch`
labels the completed batch's diff/current IDs and only that batch's expired notes.
Replay preserves the original receipt and the current view's public values. Rebuilding
context after hydration may reorder nested JSON keys; the persisted context reconstructs
the exact native input. Do not infer note storage from read success. Call arguments remain exact,
but read results omit the redundant unvalidated annotation from `inspection_intent`.
The successful-mutation
projection separates current actionable post-image evidence from historical action
inputs. A successful check card names
the next remaining check instead of treating PASS as a failure. A failed mutation
retains its bounded exact replacement, full replacement hash, intent, anchor, evidence
IDs, error, parsed error location, failure class, and typed scope arithmetic across later
reads and process resume. A later failed mutation replaces it; a successful mutation
clears it. `mutation_readiness.state=ready_to_attempt` uses basis
`current_delivered_editable_source_evidence`: this input contains non-empty current editable source.
The complete anchor of a proposed edit still requires separate admission validation;
readiness does not prove that coverage or semantic sufficiency. From turn two onward, the
actual model input carries the immediately preceding calls and exact public results as
native `function_call` / `function_call_output` items, followed by current derived
state without duplicating those results. One content-addressed model-input artifact
binds that sequence. Each read action in the batch card carries its corresponding
decision once. Identical evidence is counted per fingerprint at the unchanged diff.
A cache hit still costs one tool action, but its observation-level gain is recalculated
against the current coverage ledger. It may be signaled but is not hard-blocked. Never
add raw reasoning, private task material, hidden tests, reference
patches, or evaluator details.

Before each new model turn, recompute best-path completion feasibility after replaying
any pending durable batch. If mutation, all required checks, and finish cannot fit the
remaining model/tool/mutation resources, expose only `stop_task` for introspection but
do not dispatch it to the model. Record existing `LIMIT_REACHED` with
`completion horizon exhausted before provider dispatch` and bounded horizon arithmetic.
Terminal resume returns that same public result. Current semantics are tool-surface `v18`;
do not migrate old envelopes or journal bytes.

## State and recovery

Each run owns an external `dev-run-v1` JSONL stream with sequence, prior hash, and
event hash. Mutations and checks use `action_id + input_hash`; identical input
replays the durable result, conflicting reuse fails closed, and an admitted
mutation is reconciled after a crash instead of applied twice. A provider start
without durable usage is uncertain and must not be retried automatically.

New runs also own one immutable `dev-run-envelope-v1`. `--resume-run-id` requires
`repeat=1` and an exact match for provider, task, runtime, model, reasoning,
credential path hash, cost cap, limits, and sandbox identity, including the opt-in probe
image/profile identities. Repeat `--enable-probes` only if it was enabled originally.
Pre-envelope runs
cannot resume. A run-lifetime OS lock rejects concurrent execution. Generic turn
and tool-batch events recover a durable model decision without another provider
call; exact per-turn tool availability and native call/output linkage are stored at
the turn boundary. OpenAI turns additionally store provider-encrypted reasoning and
its output ordering in the external content-addressed artifact store; journal rows
contain only its reference, counts, and order hash. The next stateless request replays
that reasoning with matching calls and public results. Plaintext reasoning and
summaries are never retained. Missing, damaged, reordered, or action-mismatched
continuation evidence ends at `PROVIDER_CONTINUATION_ERROR` before another tool or
provider call. Counters, legacy inspection telemetry, settled cost, latest batch, and
active execution time are rebuilt from unique journal events. Process downtime
contributes only to run age.
One active monotonic deadline reaches provider counting/generation and tool execution,
including pending replay and checks. Each blocking operation receives remaining time.
Docker checks bind run/action execution identity so crash recovery does not duplicate
the same check container; a check timeout is not model protocol failure.

Completed probes also replay `action_id + input_hash`. If a probe was interrupted
before its durable result, confirm cleanup of its exact labeled container and permit
rerunning the isolated snapshot experiment on the bound baseline. This is not an
exactly-once process guarantee. Container ownership mismatch or uncertain cleanup stops
execution. The probe timeout is at most 30 seconds, reduced by the shared deadline,
with a five-second cleanup reserve inside the row budget. Combined stdout/stderr is
bounded to 12,000 bytes during collection, and excess output ends execution.

## Live and evaluation boundary

Live mode accepts only checked-in `dev-train` tasks and requires an explicit model,
credential file, positive total cap, and repeat count. The credential is injected
directly into the SDK and is never placed in the process environment inherited by
repository or evaluator subprocesses. Active runtime/lock files and the selected
task package must be tracked and HEAD-clean; unrelated pathspecs do not block live
preflight. The local evaluator image and digest are checked before provider
dispatch; no pull/build/start occurs.
Enabled probes additionally require the fixed clean official Python image already
present locally; they never reuse the evaluator or historical custom sandbox image.
The trusted wrapper is separately copied and mounted read-only, with bytes bound in
the probe profile. Runtime content also hashes `docker/probe_runner.py` and
`docker/Dockerfile.sandbox`, so those active paths must be tracked and HEAD-clean.
Probe snapshots contain only current tracked regular public files and exclude `.git`,
`.env*`, `.patchloop-hidden`, symlinks, and reparse points. Numeric non-root execution,
no network, read-only root/source, bounded tmpfs and resource limits are host-controlled.

Actual request input is counted immediately before generation. The ledger reserves
uncached input plus a conservative output ceiling, lowers that ceiling when needed,
and emits `COST_CAP_REACHED` without generation when the minimum request cannot fit.
Transport retry is zero. Count, provider, or billing uncertainty stops remaining
repetitions. Provider completion records structural output evidence only: item
count, non-tool count, item types, a shape hash, and an encrypted-continuation artifact
reference. Request `reasoning.encrypted_content` with `store=false`; never persist
response text, plaintext reasoning, or a reasoning summary for protocol diagnosis.

After finish, the canonical submitted diff is content-addressed and an immutable
manifest is recorded before evaluator execution. It binds task bytes, full runtime
bytes, model/tool/sandbox identities, the visible-check diff, changed files, and
the submitted artifact. The evaluator validates those inputs before workspace or
check execution, then a clean workspace receives the exact artifact and private
files. Agent context is never resumed with evaluator output.
If probes executed, the manifest includes their count and content-addressed public
receipts, binding action/input, source, diff, snapshot, image/profile, and execution-policy
hashes. Validate receipts before evaluator workspace creation: absent or invalid evidence
is safety ERROR; a valid policy receipt showing a violation is safety FAIL. Probe test
outcomes never affect task acceptance. Preserve receipt and policy hashes on later
evaluator failure. Merely enabling the capability requires no execution receipt.

Task acceptance contains hidden, regression, and scope results only. Safety is a
separate typed result for runtime contract, constrained tool surface, managed
workspace, and requested sandbox policy. Docker evidence maps match/violation/
missing-or-invalid to PASS/FAIL/ERROR; local/mock Docker policy is NOT_RUN.
`EVALUATOR_PASS` means only task acceptance. Public summaries always expose both
axes and `claim_eligible=false`; every result remains `official=false`. Never use
`AuditSpec.prohibited_behaviors` as an automatic safety oracle.

## Default limits

- 40 model calls
- 100 tool actions
- 4 accepted mutations
- 1,800 seconds per row
- one consecutive protocol/incomplete recovery
- four parallel reads
- completion-slack inspection with one warned final opportunity and independent
  two-call mutation-failure and check-failure recovery reserves
- an advisory commitment signal after consecutive zero-coverage inspections;
  it never changes the tool surface
- legacy 24-turn and three-repair-read fields retained as telemetry only
- 25,000 desired output tokens per provider call, reduced by cost admission
- one repetition by default, six maximum

## Development decisions and next seam

- Edit `dev-head` directly in small commits; do not version ordinary fixes.
- Keep cross-run memory disabled; bounded public run-local working notes are enabled.
- Keep mutation intent embedded in the mutation turn.
- Treat the exact live invocation as bounded development authority.
- Recover historical executables only from checkpoint `b71ddeee`; do not restore
  their active import graph.
- Keep confirmatory work in a future, separately frozen lane.

Current seam: tool surface `v18` preserves original verification questions separately
from progress, treats identical updates as no-ops, separates pre-batch note receipts
from current IDs, indexes already delivered header locations, and forecasts affected
tools using a conditional actual-policy successor. Preserve source-note expiry,
first-owner receipts, exact replay, budgets/action masks, and finish availability.
No task case, hidden oracle, new model step, or mandatory experiment is added. Tests
validate feedback contracts, not improved choices. Row 25 retained the relevant source;
the identified feedback defects do not establish what caused all repeated exploration.
Old nonterminal runtime mismatch still rejects resume; no migration is approved. The
separately approved row 26 below passed task acceptance and safety, but annotation
limitations remain and no twenty-seventh row is approved. V17 below is historical evidence.
The preceding tool surface `v16` fixes recursive search-glob semantics and uses the
minimum successful edit successor for mutation admission, with separate protected-recovery
warnings. It keeps inspection/probe protection, exact evidence, check invalidation, and
existing limits. Mechanism-oriented notes, evidence-only currency labels, small exact
anchors, and non-compulsory anchor-repair feedback add no planning call or semantic oracle.
The preceding tool surface `v15` fixes independent source-body retention, atomic note
lifecycle replay, and action-associated note receipts. Source validation and nonblocking
annotation failure remain; new planning calls, read caps, or cross-run memory are absent.
The real two-unrelated-edit reproduction must retain the same note in uninterrupted and
resumed execution. Genuine expiry must not resurrect when source text later returns.
Provider-free tests fix these cases, mutation-completion crash boundaries, and the
initial invalid-reference -> unknown-ID -> null-create feedback path.

The preceding tool surface `v14` added stable run-local note IDs and explicit
create/update/removal, guidance connecting mechanisms to small implementation choices,
and an opt-in public Python experiment tool. Existing source admission, budget-only
exploration, exact mutation recovery, provider diagnostics, and execution deadlines
remain. The twenty-first v13 row reached evaluation, but task acceptance failed after
26 inspection turns and a broad manual path-walking edit with public semantic
counterexamples. Its prompts contained the core mechanism; duplicated or weakened
notes are observed limitations, not proof that memory alone caused the failure.
The initial v14 implementation passed Ruff, 215 provider-free tests, and mock isolated
evaluation. Separately approved real Docker probes now verify basic source/process
isolation, completed replay, bounded output, and deadline cleanup using synthetic data.
They exposed tag/digest lookup mismatch and unread-pipe cleanup backpressure; canonical
repository@digest execution and discard-after-cap draining fix those specific defects.
Keep the output retention limit distinct from total drained-byte telemetry. The failed
flood receipt remains preserved beside the successful bounded recheck; cleanup uncertainty
still stops execution. Future exact live authorization must explicitly include the probe
capability if used. Local or mocked execution does not establish that the model chooses
better experiments or reaches submission faster.

The separately approved twenty-second row, `run_dev_309a71c0c16544ed`, ran v14 commit
`f7849c664f43cd84d3c5badfb5b9c2b8a3beb012` with probes enabled and reached isolated
`EVALUATOR_PASS`, task acceptance PASS, safety PASS, and `claim_eligible=false`.
It used 33 model calls, 36 actions, two mutations, one probe, and $0.385299450. The
recursive edit reused existing path/mkdir operations; the public parent-mode failure
was correctly repaired, both visible checks passed, and the submitted diff had 15 lines.
The Linux real-os probe observed string/bytes traversal side effects, not Windows or
candidate equivalence. Do not turn its successful execution into a broader claim.

The read-only review then examined early memory admission and repeated inspection.
The first edit still arrived at call 27; 17 of 29 inspections added no source coverage.
The first note cited nonexistent result `pending`; five subsequent updates targeted
unallocated `n1`. Diagnostics were projected, but no findings survived before mutation.
Valid note creation began on call 30, with source-change expiry and later updates working.
These observations do not prove memory caused either the delay or the final success.
It separately reproduced the unchanged-note deletion/resume resurrection now fixed in v15.
Do not attribute that separate bug to row 22's initial rejection, auto-accept unobserved
sources, or add a hard read cap.

The separately approved twenty-third row, `run_dev_ac4248e1b75e4ad2`, ran v15 commit
`61dea7880eb11fa588f0b17a0b516215972bb089`: 32 model calls, 34 actions, one accepted
mutation, $0.361692000, and `EVALUATOR_FAIL` (task acceptance FAIL, safety PASS,
`claim_eligible=false`). Probes were enabled but unused. Notes were created from call 4;
call 5's unobserved-source annotation received a concrete nonblocking receipt, and call 7
updated the existing note. All 22 receipts matched their next native delivery. The accepted
mutation rebound unchanged `n1` and expired changed-source `n2`, as the next context showed.
There was no resume or second accepted mutation; those lifecycle guarantees still rely
on the focused provider-free tests, not this live observation.

Early working notes did not establish more efficient exploration: 17 of 29 inspections
again added no source coverage. The first edit attempt at call 27 miscopied a docstring
line break and was rejected; after a read, call 29's exact replacement was accepted.
Both visible checks passed and call 32 submitted the same four-line diff evaluated in
isolation. Acceptance failed on a trailing-separator boundary: the new `head and tail`
guard skips traversal when the final split component is empty. Private diagnostics were
not returned to the coding agent. There was no token-ceiling or protocol terminal.

The subsequent read-only diagnosis found intact source projection, a false-negative
recursive glob, and a latent probe-to-edit budget disconnect. V16 fixes the latter two
and clarifies note/anchor guidance. The subsequent live observation below tests these
paths, not another speculative action mask or budget increase. The row comparison is descriptive,
not proof of memory causality. Do not inject private test cases into future model contexts.

The separately approved twenty-fourth row, `run_dev_89757e404d894362`, used v16 commit
`fcc8e79b11c1f3a478f07dcd894ab995ac3c1988` with the same task/model/medium/.env/repeat-1/
$1.20/probe conditions: 33 model calls, 38 actions, two accepted mutations, $0.365351250,
and `EVALUATOR_FAIL` (acceptance FAIL, safety PASS, `claim_eligible=false`). Recursive
search correctly found direct-child definitions; 26 note receipts with a following turn
matched their single native delivery. The call-22 probe compared baseline behavior only.
The first edit at call 27 and permission repair at call 30 were accepted without anchor
errors, but their 20- and 15-line anchors were still broad. Both public checks passed and
call 33 submitted; isolated acceptance reported incorrect file-parent error semantics.
Sixteen of 31 inspections added no coverage, so faster evidence reuse is not established.
Minimum-path edit admission remained visible with separate protection warnings, but a
late-probe-to-repair sequence was not exercised. The subsequent read-only diagnosis found
an invalid-parent concern replaced by mode/check questions, and an unconditional submit
card. V17 addresses these workflow seams without treating their causal impact as proved.
Do not copy private cases
into future prompts or infer an action-mask/budget remedy from the final FAIL alone.
That observation did not authorize the subsequent twenty-fifth row. All existing
external evidence remains immutable.

The separately approved twenty-fifth row, `run_dev_553ec14ad0d4441c`, used v17 commit
`8e6eedcee705bab1fea5cad5d850e764ed14dae2` with the same task/model/medium/.env/repeat-1/
$1.20/probe conditions. It ended `LIMIT_REACHED`: 37 model/input-count calls, 38 actions,
three accepted mutations, $0.486200250, and 312.967 active seconds. Thirty inspections
(18 zero-coverage, five cache hits) preceded the first edit on call 31. Subsequent edits
fixed public bytes assembly and intermediate-mode failures; the public contract passed,
but the required upstream regression failed on macOS broken-link/trailing-separator
semantics. Three remaining model calls could not cover the four-call edit/check/check/
finish path. There was no next provider dispatch, submission, or private evaluation.

Concern v1 survived all 36 following contexts and edits, with 35 once-only annotation
receipts verified. However, 30 upserts repeatedly rewrote one broad concern, and the one
resolve attempt used a read, receiving a nonblocking rejection. No probe, successful
current-diff resolution, or all-checks-PASS review occurred. Trace verification covered
453 journal events, 111 artifact hashes, 36 continuation edges, and five check policies
with cleanup confirmed. No output-ceiling or provider error occurred. Keep storage/
feedback success separate from model decision quality; no final safety verdict exists.
This observation authorizes neither a speculative runtime fix nor a twenty-sixth row.
See `docs/current-status.md` for exact results and artifact identities.

The separately approved twenty-sixth row, `run_dev_306785d397d640f3`, used v18 commit
`1d361e06ceeb2d4d85a68840ebe354eda7fc52f5` with the same v2 task/model/medium/.env/
repeat-1/$1.20/probe conditions. After the user started Docker, the one invocation ended
`EVALUATOR_PASS`: task acceptance PASS, safety PASS, 28 model/input-count calls, 32 actions,
three accepted mutations, $0.432518400, and 243.125 active seconds. First edit was call 16;
mode repair at 20 and broken-link-parent errno repair at 25 both succeeded. Final regression
and traversal checks passed at 26/27, followed by finish at 28 and isolated acceptance.
Final diff is 18 additions/one deletion in fake_os.py, hash
`sha256:49f389e710954eeda0572a20547f3b3bef74603614f4bb616f8c6a6ff9e1b69a`.

Two original concerns survived unchanged with eight repeat no-ops. All 22 next-turn
receipts and post-batch ID/diff views matched. Four unobserved source-range annotations
and one unknown concern ID were rejected nonblockingly. Both concerns were resolved
on finish, but v2's reason claimed regression evidence while citing the traversal action:
do not treat identity admission as semantic validation. Probe was available throughout
but unused; inspection closure warnings were not reached. The header index contained the
editable makedirs on turns 2–28. Of 23 inspections, five added no coverage and none were
cache hits. Maximum retained body was 23,979 characters with at most 38 omitted lines.
Read-only audit verified 348 chained events, 84 context/input/continuation artifacts,
27 replay edges, five final artifact hashes, and five public-check policy hashes with
confirmed cleanup. Journal hash is
`sha256:3b9f61aeb31a52cac79b77132ff2f6916f00a87453356a417c4413b94f9369aa`.
No new code fix, retry, or row 27 follows from this success. Runtime/task/history/credential
bytes remain unchanged, and results remain `official=false`, `claim_eligible=false`.

## Historical checkpoints

The following records describe the contracts at their respective checkpoints; earlier
mandatory reads, plateau masks, memory restrictions, and causal gates are not current guidance.

The context, resume, provenance, and typed-safety seams are locally implemented.
The second live row confirmed exact latest-batch projection and cache reuse but
exposed an ambiguous mutation encoding contract. The third live row confirmed that
the provider can call `apply_git_diff` with the raw-diff prefix, then exposed the next
boundary: one invalid hunk count was reported exactly on the next turn, after which
the agent returned to read/search for the remaining 37 turns instead of repairing
the mutation. The fourth live row confirmed that failed-mutation continuation fixed
that visibility problem: all 13 failures appeared exactly in the next context and
the repair card remained present in all 23 later turns. All 13 replacement diffs
still contained incorrect hunk totals, while a read-only `git apply --check --recount`
accepted each one against the retained isolated workspace.

A provider-free retrospective then replayed the first exact diff through the current
gateway. Recount accepted it, version-1 visible checks passed, and the exact submitted
artifact failed task acceptance while Docker safety passed. This moves the active
development boundary beyond mutation transport: the version-1 checks did not execute
the central missing-key behavior. Preserve that package as version 1. Version 2 adds
one public black-box check for actionable missing-key diagnostics, available keys,
the canonical `logger.bind()` / `{extra[key]}` pairing, and both catch modes. Do not
project evaluator details or derive further assertions from hidden output. The fifth
live row used version 2, accepted one mutation, and passed three visible checks. It
then produced two completed responses with no function call before invoking the
remaining `upstream-format-regression`, ending at `PROTOCOL_VIOLATION` with no
submission or evaluator. The old journal cannot reveal whether those responses were
reasoning, messages, or another non-tool item because their output shape was not
recorded.

The sixth separately authorized live row used the aligned tool contract and the same
version-2 task identity. Every one of 38 completed provider responses contained a
function call. The agent recovered from four rejected mutation actions, accepted one
mutation, passed all four visible checks on one canonical diff, and submitted that
same diff to the isolated evaluator. Task acceptance failed while typed Docker safety
passed. The private oracle enforced a literal example spelling that the public
contract explicitly did not require, so this is public/private contract-mismatch
evidence rather than a sound negative coding-agent verdict. Keep the hidden wording
out of agent context and preserve version 2 unchanged.

Keep repeated-evidence detection diagnostic-only. The bounded continuation evidence
does not support a hard workflow gate or a replacement mutation DSL. The smaller
current correction uses Git's deterministic recount for hunk totals while preserving
all existing mutation and submission checks. Version 3 now preserves version 2 while
replacing its literal private phrasing assertion with a semantic call-and-reference
pairing. Provider-free Docker validation makes the clean base fail, the reference and
the sixth-row exact candidate pass, and every declared known-bad patch fail acceptance.
Both passing patches also pass the full manifest-bound evaluator with all task and
safety axes PASS. This does not rewrite the immutable version-2 live result.

The separate local API defect is fixed as a small import-contract change. The
`patchloop.dev` and `patchloop.verifier` package roots retain their public exports but
resolve them lazily, and the runner depends directly on the evaluator core. A
fresh-process regression verifies lightweight package imports and both formerly
order-dependent submodule import orders. This changes no task or evaluator semantics.

The preserved `pyfakefs-makedirs-parent-traversal` version 1 had only an upstream
regression visible check. Version 2 adds a public black-box contract for POSIX,
Windows, bytes-path, and leaf-mode parent traversal while preserving every hidden,
reference, known-bad, environment, and audit byte. Its clean/reference/nine-known-bad
Docker matrix and manifest-bound reference evaluation pass provider-free.

The seventh separately authorized live row used that exact version-2 identity. It
ended at the 40-model-call limit after 44 reads and 42 searches, with no failed tool,
mutation, check, submission, or evaluator. The relevant `makedirs` source was present
in every context from turn 2 onward, and the final context still said
`needs_mutation` with one model call remaining. Treat this as a mutation-commitment
failure after sufficient public evidence, not another projection, task-contract, or
tool-transport failure. The soft repeated-evidence detector emitted no signal because
interleaved newly observed spans clear all fingerprint counts.

The post-seventh provider-free correction preserved the model's bounded public
`working_hypothesis`, `evidence_gap`, and `decision_after_result` on every read/search
result and attempt card. Action identity binds the state, while the operational read
hash remains the cache key; a cache hit therefore returns current decision state, not
the text from the call that populated the cache. Failed reads and process hydration
retain the same contract. The recorded decision takes precedence over diagnostic
stagnation wording, but no read is blocked and no new terminal exists. Local and mock
tests establish wire, cache, context, and recovery behavior only; they do not establish
live model compliance.

The separately authorized eighth row used the same version-2 task, model, medium
reasoning, one repetition, and $1.20 cap. Run `run_dev_07ad1af07d22489c` reached the
40-call limit after 60 successful reads/searches, no mutation, and $0.34786650. Every
context after the first projected all latest working states. Thirty-five per-call
decisions explicitly contemplated mutation/edit/patch/apply, but subsequent tool
selection remained read/search, including the final turn. Treat this as a live
decision-to-action coupling failure, not a context projection failure.

The post-eighth provider-free correction retired that future-decision contract. It
reconstructed one bounded native public tool continuation, validated typed decisions
against the actual tool family, and derived exposed tools from workflow evidence and a
completion horizon. At unchanged diff, general inspection leases 24 turns; a failed
mutation replaces that with three repair reads. It initially also required every
parallel read to repeat the complete free-text decision exactly.

The separately authorized ninth row used the same pyfakefs version-2 tuple. Run
`run_dev_b79d22f70ae44854` ended at `PROTOCOL_VIOLATION` after three model calls, one
successful search, no mutation, and $0.0077223. The next two responses each contained
valid read/search calls in `inspect` mode but gave those distinct actions different
rationales and evidence goals. The first rejection was present in the following public
context, yet the same application-only equality constraint failed again. Native call
and result linkage worked; the inspection lease was not exercised.

The post-ninth provider-free correction removed only that cross-call free-text equality.
Parallel reads still share enforced `inspect` mode, and each call-specific decision is
retained in its batch card. At that checkpoint the completion horizon, 24/3 leases, and
diagnostic-only stagnation behavior remained unchanged.

The separately authorized tenth row used the same pyfakefs version-2 tuple. Run
`run_dev_8efe75f7c8c14cbd` ended at `INCOMPLETE_RESPONSE` after 28 provider calls,
58 tool actions, no accepted mutation, and $0.27773415. The general inspection lease
removed reads after 24 turns, establishing that native continuation, completion horizon,
and lease all operated live. A valid public check on the unchanged empty diff failed as
expected. Three other responses used their complete 4,096-token output allocation only
for reasoning and emitted no tool call; the last two were consecutive and closed the
row. The old journal omitted `incomplete_details.reason`, so ceiling exhaustion is a
strong usage-based inference rather than a stored exact provider reason.

The first post-tenth provider-free correction raised the desired output ceiling to
25,000, retained and replayed provider-encrypted reasoning, and replaced the fixed 24/3
action gates with completion slack. The separately authorized eleventh row,
`run_dev_36d200ed199d4377`, confirmed those mechanisms live: all 39 continuation edges
linked, the last inspection opportunity was announced, and execution-only policy
elicited mutation calls whose 12,128- and 7,469-token responses completed. The first
diff failed on a bare `@@`; the next turn repaired it, and the accepted one-file diff
passed both visible checks. The row nevertheless reached 40 model calls before finish,
with 94 tool actions, $0.449133 cost, no submission, and no evaluator.

That row exposed one narrower scheduler defect. The horizon reserved only the four-call
best-case mutation/check/check/finish path, and `completion_possible` tested mutation
capacity without remaining budgets. The current provider-free successor holds one
additional first-mutation repair call, consumes it after failure, and reports actual
best-case budget feasibility. A scheduler regression reproduces the eleventh-row shape
through finish at call 40 while retaining the 40/100 global limits. Ruff and all 87
tests pass in 88.79 seconds; provider-free mock run `run_dev_22a91101f0224925` reaches
isolated `EVALUATOR_PASS` through one accepted mutation with zero provider cost.

The separately authorized twelfth row, `run_dev_2e95d3d85fd84e2d`, confirmed encrypted
continuation on all 38 edges and closed inspection at turn 36 with five calls left. Its
first mutation applied, and the central visible check then failed on the public
intermediate-directory permission assertion. The next turn proposed a one-line repair,
but mutation validation rejected it because the successful mutation had invalidated
the only current span for `pyfakefs/fake_os.py`; read/search were already closed even
though `last_successful_mutation` retained the exact current hunk. Three calls also
could not cover the repair, two checks, and finish. The row deliberately stopped at
turn 39 after 76 tool actions and $0.3471675, with no submission or evaluator.

The next provider-free successor accepted a current-diff-bound successful-mutation
post-image as anchor evidence only for an overlapping repair in that same file, while
retaining current-span validation everywhere else. The separately authorized
thirteenth row, `run_dev_8ce8603c45e646a9`, reached one accepted mutation and one
failed public check, then rejected the final targeted repair because its evidence list
mixed the valid current post-image with IDs retained from the prior mutation input.
Its earlier mutation-format failure had also consumed the single shared recovery
allowance. The row ended at `LIMIT_REACHED` after 40 calls and 76 actions, with no
submission or evaluator.

The then-current provider-free seam projected only validated
`actionable_evidence_span_ids`, retained exact mutation inputs as journal provenance,
and tolerated known historical IDs only when independent current evidence covered the
exact anchor. Mutation-failure and check-failure reserves were independent. Repeated
zero-gain inspection produced only a soft commitment signal. The later fourteenth row
required and received separate authorization.
Ruff and all 92 tests pass under the two-minute provider-free target; mock run
`run_dev_7fc6bc7e982343e4` reaches isolated `EVALUATOR_PASS` with zero provider cost.
A provider-free exact replay then admitted the thirteenth row's final repair under the
new evidence classification. The central public check passed, but the digest-pinned
Docker upstream check reported 8 failures, 509 passes, and 570 skips; `finish_task`
failed closed. Treat the original rejection as a fixed harness false negative and the
replayed patch as non-submittable agent output. Do not weaken checks or add recovery
solely to make that historical patch pass.

The separately authorized fourteenth row, `run_dev_86ccd39d36ab4379`, confirms the
encrypted-continuation and action-space contracts: all 40 calls completed with
continuation references, turn 32 warned that inspection would close, turn 33 closed
it, and a failed mutation reopened one final inspection turn. It nevertheless ended
at `LIMIT_REACHED` after 70 actions and two accepted mutations. One typed-contract
failure and three structurally corrupt raw diffs consumed the protected tail before
the first patch applied. A public check failed, and the final repair used undefined
`helpers.PERM_DEF` instead of the directly imported `PERM_DEF`; no turn remained to
recheck. An external copy with only that identifier corrected passes both public
checks, including 517 upstream passes and 570 skips. No submission or hidden evaluator
ran.

The pre-fifteenth provider-free successor implemented that seam. New-span count was
syntactic telemetry; soft inspection gain came from non-overlapping coverage in
editable task paths plus the first canonical observation of a search. `replace_text` moves diff
serialization into the gateway while preserving current hash, tracked-path, scope,
rollback, recovery, and post-image contracts. A failed visible check consumes its
separate minimum three-call reserve and exposes exactly one targeted `read_file` turn over the
changed/current-evidence paths before replacement, full recheck, and finish. Unchanged,
uniquely occurring spans are revalidated across mutation so nearby import or symbol
evidence is not discarded solely because another line changed. Do not merely raise the
40-call limit, silently repair arbitrary model intent, weaken a check, or run a paid
retry/fifteenth row without separate authorization.
Focused contract tests pass 76 cases in 82.29 seconds. Ruff and all 95 tests pass in
87.75 seconds with an external short temp root. Provider-free mock run
`run_dev_c185114854c54ad6` reaches isolated `EVALUATOR_PASS` in four model calls and
five tool actions through one accepted `replace_text` mutation; task acceptance is
PASS, safety is NOT_RUN, `claim_eligible=false`, and provider cost is zero. This proves
local wiring and recovery only, not provider behavior or a fifteenth live row.

The separately authorized fifteenth row, `run_dev_6013912c916d4781`, ended at
`LIMIT_REACHED` after 40 calls, 46 actions, two accepted mutations, and $0.4705068. Its
first 49-line diff failed the public byte assertion. Four repairs each formed the same
56-line candidate against the 50-line limit, but generic feedback hid the 49 to 56
delta. Turn 40 accepted a different 48-line candidate without enough calls to check it.
The trace had complete encrypted continuation, no provider/incomplete error, and a
largest 11,133-token response. Seven of 17 searches added no coverage and four added
supporting-only coverage, while first-seen queries still counted as gain. Turns 38 to 40
reported `completion_possible=false` yet still offered mutation. Treat these as three
harness defects: progress semantics, mutation-feedback loss, and unenforced completion
horizon, not a reason to raise global limits.

The current provider-free successor separates novelty from public line coverage, keeps
a triggered commitment sticky for its diff, reports complete typed scope arithmetic,
routes mutation failures by class, and terminates an impossible tail before dispatch.
No Docker operation, provider call, or sixteenth live row is authorized by this seam.

The initial full run passed all 103 tests but took 195.256 seconds. Profiling showed the
same turn state was being derived through 495 subprocesses in the slowest context test:
76 repeated diff summaries plus span-by-span tracked-file validation. Do not address
this with a long-lived workspace cache. Group current observations by path, capture one
fresh `DevGatewayStateSnapshot` immediately before each scheduler decision, and share it
between policy and context. Re-observe after every tool/recovery boundary.

Ruff passes. The focused 68-test tool/runner suite now passes in 90.497 seconds and the
full 103-test suite in 96.713 seconds with external temp root
`C:\pt\snapshot-full-final`. Mock run `run_dev_030e46d9a4d84395` reaches isolated
`EVALUATOR_PASS` in four model
calls and five tool actions through one accepted mutation, with task acceptance PASS,
safety NOT_RUN, `claim_eligible=false`, and zero provider cost. This restores the
two-minute target without deleting or parallelizing tests and does not authorize a paid
row.

The separately authorized sixteenth row, `run_dev_6c36a082c3264559`, ended at
`LIMIT_REACHED` after 37 calls, 44 actions, one accepted mutation, and $0.43578705.
All 37 responses carried encrypted continuation. Before the first mutation, a current
span covering the complete proposed anchor was already projected, but the model twice
serialized a shorter overlapping span ID and the old validator rejected both attempts.
Each rejection re-armed another targeted read. Turn 36 finally applied a mutation;
the public check then exposed an empty-parent-path `FileNotFoundError`. With three calls
remaining versus a five-call repair/check/finish path, the pre-dispatch horizon correctly
stopped the run. There was no submission or evaluator.

Tool surface `v8` removes `evidence_span_ids` from `replace_text`. The gateway now binds
the most recent current covering observation itself, keeps the selected ID only as
journal provenance, and applies one targeted-read allowance per failed-anchor lineage.
This removes the mechanical join-key failure without weakening current-file, range,
scope, rollback, or submission checks. No Docker operation, provider call, or
seventeenth live row was authorized by that change; the later row required separate
authority.
Ruff and all 105 provider-free tests pass; the final full suite completed in 80.787
seconds with external temp root `C:\pt\pl-v8-full-0905-c`. Mock run
`run_dev_32428b48e6b341d8` reaches isolated `EVALUATOR_PASS` in four model calls and
five tool actions through one accepted mutation, with task acceptance PASS, safety
NOT_RUN, `claim_eligible=false`, and zero provider cost.

The separately authorized seventeenth row, `run_dev_4b32848a5621473e`, confirmed the
v8 evidence binding on all four accepted mutations, then ended at `LIMIT_REACHED`
after 34 model calls, 42 tool actions, and $0.393104700. The first public inline failure
was line 12. The second moved to line 23, the public intermediate-directory `0o755`
assertion, and the last two remained there. The final code used the requested leaf
`mode=0o700` for all path components, but the later mutations instead targeted path
joining and Windows separators; that later Windows block had not executed. Mutation
capacity, not model/tool call capacity, then blocked completion. There was no
submission or evaluator.

Tool surface `v9` keeps raw check-output signatures for provenance and adds a separate
semantic site fingerprint for safely mapped registered `python -c` failures. Its
bounded `current_public_failure` joins the exact public statement, conservative
cross-diff location comparison, unobserved-later-source status, and remaining mutation
pressure. It survives intervening reads and restart until a relevant pass clears it.
Nested and unmapped traces remain uncertain, and no local variables, hidden paths,
private bytes, reasoning, task-specific semantic rule, new terminal, or semantic hard
gate are added. Ground the existing mutation hypothesis and `causal_revision` in this
card. Provider-free regression must preserve the row-17 public `12 -> 23 -> 23`
sequence. No Docker operation, provider call, or eighteenth row is authorized by this
change.
Ruff and the focused 74-test tool/runner suite pass. All 109 provider-free tests pass
in approximately 70.5 seconds using external temp root `C:\pt\pl-v9-full-a`. Mock run
`run_dev_dd14cc24d3fa46ef` reaches isolated `EVALUATOR_PASS` in four model calls and
five tool actions through one accepted mutation, with task acceptance PASS, safety
NOT_RUN, `claim_eligible=false`, and zero provider cost. This is local wiring evidence,
not live evidence that the model makes the intended causal pivot.

The separately authorized eighteenth row, `run_dev_092cb8494e254124`, ended at
`AGENT_STOPPED` after nine model calls, 16 tool actions, one accepted mutation, one
failed public check, and $0.078825000. Tool surface v9 mapped the `FileExistsError` to
public inline line 10 and retained the current mutation post-image. The model explicitly
diagnosed the redundant final `FakeFilesystem.makedirs(normalized_path)` call and named
the appropriate repair, but the scheduler exposed only `read_file` and `stop_task`.
The old `targeted_check_repair_inspection` state conflated a restricted read opportunity
with a required predecessor, while the prompt correctly discouraged a read without an
unresolved public gap. The resulting stop is a harness action-mask contradiction, not
missing failure evidence or a failed causal pivot.

Tool surface `v10` adds `targeted_check_repair_required` as the distinct prerequisite.
When a failed check still has current exact mutation evidence, expose `replace_text`
immediately and expose one path-restricted read beside it only when protected completion
slack remains. At the exact best-path horizon, omit that optional read. When the anchor
is absent, keep the targeted read mandatory and count it in the minimum path. Corrections
must describe those two states distinctly. Preserve gateway evidence validation, scope,
rollback, resume reconstruction, and same-diff check suppression. This change authorizes
no Docker operation, provider call, or nineteenth live row.
Ruff and the focused 74-test tool/runner suite pass. All 109 provider-free tests pass in
71.998 seconds with external temp root `C:\pt\pl-v10-full-a`. Mock run
`run_dev_b5d5b2473d6a414f` reaches isolated `EVALUATOR_PASS` in four model calls and
five tool actions through one accepted mutation, with task acceptance PASS, safety
NOT_RUN, `claim_eligible=false`, and zero provider cost.

The separately authorized nineteenth row, `run_dev_87185b3ce20a4333`, ended at
`LIMIT_REACHED` after 39 model/input-count calls, 44 tool actions, two accepted
mutations, and $0.472921050. All 39 provider turns carried encrypted continuation. The
first replacement was rejected for a stale exact anchor, and the second implemented the
recursive behavior. The first public check then failed its intermediate-directory mode
assertion. Tool surface v10 correctly offered both optional targeted read and immediate
replacement; the repair switched recursive parents to `PERM_DEF`, and that check passed.
The later upstream regression check failed two broken-parent-link cases with `EEXIST`
instead of `ENOENT`. Only one model call remained against a four-call repair/recheck/
finish path, so the pre-dispatch horizon stopped the row. There was no submission or
evaluator.

Tool surface `v11` addresses the two remaining scheduler causes without encoding that
task's semantic repair. Two zero-coverage batches now announce one final parallel
inspection; new public coverage reopens exploration, while a further zero-coverage
batch closes broad reads for the current diff and leaves mutation or stop. Separately,
the horizon reserves one recovery path per distinct visible-check ID, ordered by the
declared check sequence and bounded by remaining mutation capacity. Consuming the first
check's reserve no longer erases the second's. Legacy check failures without an ID keep
their conservative consumed state. This change authorizes no Docker operation, provider
call, or twentieth live row.
Focused scheduler tests and Ruff pass. All 109 provider-free tests pass in 77.62 seconds
with external temp root `C:\pt\pl-v11-full-0905-c`. Mock run
`run_dev_54650ea291e24cd0` reaches isolated `EVALUATOR_PASS` in four model calls and
five tool actions through one accepted mutation, with task acceptance PASS, safety
NOT_RUN, `claim_eligible=false`, and zero provider cost.

Confirmatory design review still waits for three distinct harness/contract-clean
submissions with at least two private passes; that threshold itself proves no quality
or generalization benefit.

## Validation checklist

Run only what the change needs, then broaden to:

```powershell
uv run ruff check patchloop tests
uv run pytest tests -p no:cacheprovider --basetemp <short-external-path>
uv run patchloop dev --provider mock --task tasks/smoke/csv-quoted-newline/public.yaml --model mock-dev --repeat 1
```

V18 passes 414 provider-free tests in three concurrent groups of 75 (90.71 seconds),
144 (83.92 seconds), and 195 (86.28 seconds), using `C:\pt\pl18-verified-6401-{a,b,c}`;
three opt-in Docker tests remain skipped. Ruff and mock pass. The frozen final
Ruff/full-suite/mock sequence took 98 seconds, excluding earlier debugging/focused checks.
Mock `run_dev_0fde34f908a74d5e` under `C:\pt\pl18-smoke-6401` reaches isolated
`EVALUATOR_PASS` in 5.03 seconds: one mutation, four model turns, five actions, acceptance
PASS, safety NOT_RUN, zero cost, `official=false`, and `claim_eligible=false`.
The native feedback/restart tests preserve exact receipts and exact reconstruction
from the same saved context; independently rebuilt context is compared by public values,
not incidental nested JSON key order. The read-only row-25 index comparison includes
the actual editable makedirs header at line 915, within 16 entries/3,213 characters.
That local checkpoint did not authorize the separately approved row 26 recorded above;
no new model-quality claim or twenty-seventh row follows.

V17 passes 59 focused concern/note/guidance cases, Ruff, and all 336 provider-free tests
in two concurrent groups of 156 and 180 with separate short external roots. Three real
Docker cases remain skipped. This full-suite invocation exceeded the two-minute target;
do not report it as an under-two-minute full cycle. The annotation-aware integration mock
checks pending-result rejection, current-result resolution on the existing finish turn,
and once-only native receipt delivery without extra model calls. Separate mock
`run_dev_36964c96d4834891` in `C:\pt\pl-v17-smoke-4829` reaches isolated `EVALUATOR_PASS`
in 4.97 seconds: one mutation, four model turns, five actions, task acceptance PASS,
safety NOT_RUN, cost zero, and `claim_eligible=false`. No live/provider/Docker execution
ran for this implementation checkpoint; the later twenty-fifth row was separately
approved and is recorded above.

V16 passes 75 focused search/guidance/tool/note cases, 16 focused budget cases, and Ruff.
All 287 provider-free tests pass in concurrent groups of 107 (90.79 seconds) and 180
(104.29 seconds), with three real-Docker tests skipped. The only warnings were repository
pytest-cache permissions; use `-p no:cacheprovider` or an external cache directory to avoid
that unrelated cache write. Mock `run_dev_ae0880944bfd4697`, under
`C:\pt\pl16-smoke-355ec8`, reaches isolated `EVALUATOR_PASS` through one mutation,
four model turns and five actions in about five seconds: acceptance PASS, safety NOT_RUN,
cost zero, and `claim_eligible=false`. No Docker or provider call ran for this change.

V15 passes 54 focused note/context/input cases in 35.35 seconds and Ruff. Full-suite
groups pass 64 in 90.67 seconds and 180 in 115.15 seconds concurrently: 244 provider-free
cases, with three real-Docker cases disabled. Final mock `run_dev_b4a45c26a2e84022` under
`C:\pt\pl-v15-smoke-0d2aaa` reaches isolated `EVALUATOR_PASS`, task acceptance PASS,
safety NOT_RUN, through one mutation, four mock model turns and five actions, at zero cost.
This verifies note lifecycle/receipt contracts locally, not better live model decisions.

Freeze runtime files while running the suite: content-hash provenance tests intentionally
reject concurrent source edits. To stay near the two-minute full-cycle target, run
`test_dev_runner.py`, `test_dev_resume_v12.py`, the three `test_dev_*_v16.py` files,
and both `test_dev_verification_*_v17.py` files in one pytest process and every other
`test*.py` file in another, using distinct new short external basetemps. Do not omit tests
or share temporary roots. Then run mock smoke. V14 passed Ruff and 215 tests: 64 in
84.63 seconds and 151 in 82.70 seconds, running concurrently. A final 500-character
action-ID receipt-boundary correction passed all ten probe-provenance tests in 6.52
seconds. Mock `run_dev_0e6b57566f77420b`, under `C:\pt\pl-v14-smoke-final`, reached
`EVALUATOR_PASS` with task acceptance PASS, safety NOT_RUN, one accepted mutation,
four model turns, five actions, and zero cost. Docker/probe launches were mocked at
that checkpoint. Later approved real-probe evidence is under `C:\pt\pl-probe-real-b`
(isolation/replay and failed flood) and `C:\pt\pl-probe-real-c` (repaired flood/deadline).
The opt-in `tests/test_dev_probe_docker.py` requires `PATCHLOOP_TEST_REAL_PROBES=1`
and an external basetemp; default regression skips all three real-Docker cases. It
must never pull/build/start automatically, and cleanup uncertainty aborts the session.
After the real-Docker fixes, Ruff and 224 provider-free tests pass (64 in 89.66 seconds,
160 in 88.00 seconds, parallel), with three real-Docker cases skipped by default.
Mock `run_dev_f5951bf0dd474039` in `C:\pt\pl-probe-smoke-final` reaches isolated
`EVALUATOR_PASS`, acceptance PASS, safety NOT_RUN, and zero cost. See
`docs/current-status.md` for the separate Docker results and claim boundaries. The preceding
v13 checkpoint passed seven focused schema/diagnostic/resume cases, Ruff, all 175 tests
(64 in 80.06 seconds and 111 in 58.33
seconds in parallel), and mock isolated evaluation in run
`run_dev_d22310790c4a4696`. It is local/provider-free evidence, not a live agent-success
result.

Before handoff, confirm no private projection, repository-local run state, live
call, Docker mutation, historical artifact edit, stale active-doc link, or invented
result was introduced.
