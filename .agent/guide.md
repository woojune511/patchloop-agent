# Internal implementation guide

This is the agent-only companion to the required root `AGENTS.md`. It summarizes
active contracts for navigation; checked-in source remains the behavioral authority.

## Source map

```text
patchloop/dev/runner.py   loop composition, gates, context, terminal handling
patchloop/dev/conversation.py  append-only episode, complete current view and reconstruction
patchloop/dev/model_state.py   compact public model view, separate from audit accounting
patchloop/dev/native_sources.py  exact current-source delivery references into native history
patchloop/dev/tools.py    tool grammar, spans, mutations, checks, finish
patchloop/dev/state.py    append-only JSONL, action/provider recovery
patchloop/dev/cost.py     reviewed prices and pre-dispatch admission
patchloop/agent/model.py  journal-managed Responses adapter, zero retries
patchloop/repository.py   audited checkout, workspace, full diff
patchloop/sandbox/        registered checks and optional isolated public probes
patchloop/sandbox/execution_feedback.py  bounded current-diff execution observations
patchloop/sandbox/line_trace.py  standalone stdlib launch-thread line collector
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
`read_file` advertises its existing inclusive range bound explicitly: one to 400 lines,
with `end_line - start_line + 1 <= 400`. Output may contain fewer complete lines under
the existing character cap. EOF/truncation and mutation-admission rules are unchanged.
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
image, mount, or environment supplied by the model. Its description must state that
current tracked public files, including accepted edits, are importable read-only from
`/workspace`, with writable `/tmp` scratch and only base Python/public project code:
no network or dependency installation. This describes the existing snapshot capability,
not a new mount or required experiment. A probe result is diagnostic:
it never grants source-span coverage, visible-check PASS, or finish credit, and failure
does not force mutation or consume a check-repair allowance. See
[the probe runtime contract](../docker/README.md) for image and isolation details.

Public checks and enabled probes return `public_execution`: advisory Python line-entry
feedback for current tracked editable additions/replacements only. The host binds diff,
raw file and run/action request hashes; no model-selected paths or new tool inputs are
introduced. Bound requests to eight files, 256 changed lines, and 12,000 serialized
feedback bytes. Whole over-bound/unsupported files are omitted with a count; deleted
lines have no post-image coordinate. Compile current public bytes without execution to
identify changed positions present in Python's line table; distinguish `no_line_event_ranges`
from `not_observed_changed_ranges`. Collect only the launch thread, not other threads,
subprocesses, branches, values, variable locals, source bodies or assertions. A line event
means entry, not successful completion or semantic correctness.

The same stdlib collector is copied outside the workspace, read-only: a separate mount
for registered checks, the existing trusted mount for probes. Preserve the declared check
command in results. Instrument Python `-c`, `-m`, and script launches by executable basename:
`python`, `python3`, versioned Python 3, and optional `.exe`, across POSIX/Windows paths.
Do not resolve a container path on the host or substitute the declared interpreter/argv.
Preserve unsupported commands and mark their feedback unknown. A bounded separate report
frame does not spend the stdout/stderr cap. Its separate cumulative body allowance is
16,000 bytes; malformed metadata alone must not change the probe's exit outcome.
Reject duplicate, malformed,
oversized or mismatched reports; missing
or interrupted collection, trace loss, timeout and file drift yield unknown rather than
negative line evidence. This in-process report can be interfered with by tested code and
is not a security attestation. Keep deadline/cleanup authority unchanged and remove mounted
temporary files only after exact-container cleanup. Probe profile and runtime hashes bind
the collector. Isolated private evaluation receives no collection targets and remains
outside the model loop. Follow the documented thread limits of
[Python tracing](https://docs.python.org/3.12/library/sys.html#sys.settrace).

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

Before invalidating edited-file pre-image spans, a successful exact replacement maps
their unchanged complete-line fragments using the admitted character offset and verified
raw pre/post bytes. Verify original span bodies at their original coordinates, map only
untouched lines to current coordinates, and verify full current line bodies. Do not use
fuzzy matching, infer untouched substrings as whole lines, or fill unobserved gaps.
Merge overlaps before the existing eight-span/per-span output bounds; never enlarge the
24,000-character retained projection. This preserves known prefix/suffix evidence when
one interior line changes, including positional shifts and duplicate text. Reconciliation
reconstructs and hash-verifies the exact pre-image before the identical mapping; persist
rebound fragments in the normal mutation result for deterministic hydration.
It also registers one bounded replacement post-image
span bound to the current file and diff hashes. Those spans can authorize a same-file
repair only when their contiguous observed union covers the exact current anchor;
an edit elsewhere still requires current read/search evidence. Read, search and post-image
spans contain only
complete returned lines; EOF has no span, and CRLF uses the same normalization for reads,
replacement and revalidation. Resulting paths, file count, line count, dependencies,
tests and public API remain constrained by the public task. `causal_revision` remains
optional explanatory metadata, including when the same failure site repeats.

Project `mutation_scope_budget` before mutation with complete current-diff lines/files,
limits, and remaining headroom; headroom is not the replacement's line count. A target
outside the public path rules produces `path_not_allowed` with `rejected_path`, exact
public `allowed_paths` and `forbidden_paths`, and the baseline identity before application.
Inspectable source is not necessarily editable. Persist this feedback through failed
mutation context and replay; add no action restriction. If the complete candidate
violates scope, roll back first and return typed baseline, candidate,
delta, actual, limit, and overage fields. Record the restored baseline as the failed
result's workspace hash. The agent may revise, investigate, or abandon that proposal;
its failure is not an obligation to mutate an already checked baseline. Inspection
availability follows the completion budget. Admission records the complete expected
candidate diff before atomic replacement. Reconciliation must match that identity,
including after a crash before rollback, and restores an admitted over-scope candidate.

## Context boundary

The complete deterministic audit context artifact puts current workflow gate, remaining budget,
action horizon, mutation readiness, mutation scope budget, and the bounded evidence
ledger before the larger task text. It also contains the public task, current full diff, latest tool
batch, a prioritized current-source working set, recent visible-check output, the
complete current-diff check status, exact remaining check IDs, bounded
`last_successful_mutation`, bounded `last_failed_mutation`, and the latest three
batch-level attempt-result-next-question cards. The ledger merges covered line ranges
per path and records canonical search observations and the latest public inspection
intent references; it stores neither raw reasoning nor semantic claims inferred by the harness.
Source projection precedes policy/readiness: exact native observations plus the retained
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
rejecting the action. Source-range rejection keeps `unobserved_source_range` and adds
`reason=never_observed|stale_current_range`. Report requested/current/missing ranges
bounded to eight entries each with counts/truncation; unknown paths are not echoed.
Historical coordinates describe past observations, not current text proof. Never partly
admit a finding, auto-read missing ranges, or force another action for an annotation.
Accepted-mutation references bind the actual output diff.
Unique `working_notes_updated` events record allocations, removals, evictions, and
retained IDs, and hydrate at most six model-authored findings. Source notes
retain their actually observed bodies separately from active source spans, with a
24,000-character total body bound per note. Over-bound citations reject only that note
with a narrower-citation hint. Successful mutation `action_finished` payloads atomically
bind `working_notes_state` outside the public result; hydrate replays that snapshot,
never recomputing historical lifecycle decisions from the final filesystem. Unique
unchanged text rebinds; changed or ambiguous text expires without later resurrection.
`last_source_lifecycle` exposes only triggering action, rebound IDs, and expiry reasons.
Old tool-result references remain historical. For an executed `run_check`, persist a
compact `check_result` beside the citation: actual `check_id`, `passed`, and the existing
bounded public `exception_type`, null when absent or passed. Do not infer a verdict for
an unexecuted/failed action or attach check labels to a probe. Projection adds per-reference
`currency=current|historical|unknown` from the cited/current diff hashes without rewriting
the durable result. Missing diff identity means unknown, not current-check proof. Preserve
this label through note/mutation snapshots and restart; copy no traceback, error message,
private content, or reasoning. Even contradictory note prose remains model-authored and
nonblocking. The recorded verdict is not a semantic endorsement of that prose.
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
short reason. The gateway binds action/input/diff identity, not semantic coverage.
Retained check summaries always include action/check/diff identity together, and resolved
check evidence names the actual cited `check_id`. Preserve existing check-summary
selection/order and native body deduplication. Do not infer semantic relevance from
free-form resolution prose or add a submission blocker.
Dismissal is only model judgment. Both decisions become historical after a diff change
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
Notes retain reusable behavior rules, implementation assumptions, and untested behavior.
Refine an existing ID for the same fact; use a new ID for a distinct fact. Current error
status already has `current_public_failure`, qualified by diff currency; historical failure
is not a current-candidate verdict. Do not overwrite reusable knowledge with a copy of
that status. The system prompt encourages reuse of existing responsibilities and asks
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
but native read/search results replace the redundant `inspection_intent` with a reference
to the exact call arguments. The canonical/context-only result retains that intent once.
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
actual model input retains the whole native episode, not only the previous batch.
Its order is fixed system instructions, an immutable initial developer-role state JSON,
one stable user task, then chronological encrypted reasoning/canonical calls/public outputs
and appended complete developer-role current views. Every previously sent item remains unchanged.
Each `harness_current_state` has a complete mutable `state` object. Read the latest one
directly; only `public_task` is inherited from the initial message. Missing mutable fields
are absent, not inherited. Reject within-episode task changes. Normalize nested JSON keys
while preserving top-level control-field priority. `reconstruct_state` validates all view
records and selects the latest plus the immutable task, including correction clearing,
note expiry and historical check currency. No model-facing nested JSON edit operations remain.
The JSON and source/tool/model prose remain data, not additional instructions. Never
append a fresh user context or assume the last ciphertext contains the whole episode.
Only the latest complete view is current hash/note/check/correction authority.
Old native results and superseded state remain historical, not current PASS or source proof.
The 24,000-character bound still applies to retained current source, not total history.
Existing whole-input counting, cap, output bounds and run limits constrain this episode;
do not silently drop old exchanges, reset reasoning, or introduce paid compaction.

Each new input loads the last decision's hash-verified input artifact, retains every item,
and appends only that response/executed or rejected batch and its current view. Reasoning-only
responses also append without losing earlier results; current result duplication is removed
even on a correction turn. `turn_started.native_history` stores only schema/counts/hash,
including `state_update_count` and the reconstructed model-view `current_state_hash`,
never ciphertext or plaintext reasoning. A started-but-undispatched boundary is not a new
decision or an extra exchange. All durable continuation refs and the saved active input
must validate before pending tools on resume. Billing uncertainty keeps terminal priority.
One content-addressed model-input artifact binds each sequence. V21 projects the inspection
result's echoed intent and derived
ledger/outcome/attempt decisions as action-bound references, labeled
`model_authored_pre_observation_intent`. Delivery is `preceding_function_call_arguments`,
`latest_tool_result.inspection_intent` for context-only adapters, or `journal_only` for
intentions absent from that adapter's input. V22 native history includes older call IDs too;
the compatibility `preceding_function_call_*` labels identify prior decisions/results,
not their position relative to state messages. Keep source, query/range, gain, status,
check feedback, explicit notes/questions, and original journal calls/results/cards exact.
Do not use text matching, invent a finding, reinterpret a decision as an observation, or
claim that a journal-only reference is an available tool. Original ledger action IDs
hydrate deterministically; cache and parallel action identities remain distinct.
Identical evidence is counted per fingerprint at the unchanged diff.
A cache hit still costs one tool action, but its observation-level gain is recalculated
against the current coverage ledger. It may be signaled but is not hard-blocked. Never
add raw reasoning, private task material, hidden tests, reference
patches, or evaluator details.

Before each new model turn, recompute best-path completion feasibility after replaying
any pending durable batch. If mutation, all required checks, and finish cannot fit the
remaining model/tool/mutation resources, expose only `stop_task` for introspection but
do not dispatch it to the model. Record existing `LIMIT_REACHED` with
`completion horizon exhausted before provider dispatch` and bounded horizon arithmetic.
For native delivery, retained `source_spans` use `content_delivery` references when all
their exact LF-normalized lines exist in successful native source outputs with the same
path/raw file hash. References identify action ID, output field and inclusive line range;
adjacent/overlapping spans may supply the union, with no unobserved gap. Earliest matching
deliveries keep references stable across rereads. A conflict, old hash, missing line or
more than 16 references keeps the original inline span. Original native output bytes,
canonical full context artifacts, the 24k retained selection and gateway admission do not
change. No filesystem access occurs during reference projection. Do not compare strings
without their exact source identity or reinterpret historical evidence as current.

The model view is a separate deterministic projection of that full public audit context.
Keep current gate/tools/budgets, completion feasibility and closure warnings, scope headroom,
full diff, current failure, required-check status/currency, notes and corrections. Drop
rolling inspection cards (not protocol correction cards), detailed ledger arrays, redundant
constant instructions and observation/span counters only from the model view. Native calls
and outputs, canonical artifacts and journal accounting remain exact. Keep search aggregates.
`current_sources` groups retained path/raw-hash identities with `content_delivery` maps:
action ID -> output field -> inclusive [start,end] ranges. Merge only touching/overlapping
ranges within the same exact delivery. Gaps and full `inline_spans` fallback stay intact;
lexical headers join the same file group. Do not change retained-source selection/admission.
Older mutation/check/probe bodies may use native references when matching results exist;
otherwise keep bounded inline evidence. Failure messages and typed mutation diagnostics
remain explicit, and current failure/check currency never derives from historical PASS.
Working note content, citation currency, concern status and receipts remain model-authored,
not harness-validated interpretations. No model summary, mandatory annotation/probe or new
action restriction is introduced.

`public_execution_summary` unions line observations from completed current-diff public
check/probe results with matching current raw file hashes. It contains bounded ranges and
recent action references, not another copy of the report body or an inferred semantic
summary. Mutation invalidates old-diff observations; hydration derives the identical view
from durable action results without rerunning checks. Keep per-action feedback in the
native result, following the existing [tool-output linkage](https://developers.openai.com/api/docs/guides/function-calling).
Unknown/unobserved positions can inform existing optional model-authored questions/concerns;
never auto-create a semantic finding, grant source-read coverage or mutation evidence,
resolve a concern, withhold finish, or require a probe on that basis.

Failure feedback receives the actual allowed-tool set at context construction. Preserve
the original check/diff identity and compatibility phase, adding `evidence_currency` as
current/historical/unknown. Do not give repair advice for `awaiting_recheck`: name an
offered `run_check`, and explain that zero mutations prevents further edits, not available
checks or submission after current-diff PASS. For a current failure, name only offered
repair/inspection tools. Missing diff binding never becomes a current verdict. Keep
projection read-only and deterministic after restart, including native latest-state views.
The prompt distinguishes completion of this candidate from the separate further-edit
horizon. Do not change tool masks, force a check or reject a voluntary stop on this basis.

Terminal resume returns that same public result. Current semantics are tool-surface `v26`;
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
all active-episode reasoning with matching calls and public results. Plaintext reasoning and
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
Persist bounded `response_reasoning_context` on provider/decision events and decision
recovery: reported `current_turn`/`all_turns`, null when absent/unrecognized. Do not request
GPT-5.6-only `all_turns` on GPT-5.4 mini. Wire integrity and reported mode establish
availability only, not effective model use. No output ceiling or model configuration changes.

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

Current seam: v26 exposes current changed-line execution evidence from public checks/probes,
without changing action availability, prompt, tool inputs or submission conditions. Row 33
demonstrates that correct source delivery and public PASS did not establish correct use of
the error-handling owner or execution of new error paths. The saved public inline check's
three new error-raising lines were not entered in the post-terminal local trace. This is
not a measured full-regression coverage result or proof of a counterfactual model success.
Keep observations separate from note interpretation; prefer evidence to another warning
or forced experiment. Provider-free tests cover collector bounds, unknown states,
current-diff union, native delivery, replay and mocked sandbox cleanup. A separately
approved real-Docker check/probe pair now passes under `C:\pt\pl26-docker-real-a`: the
check leaves one changed error line unobserved and the deliberately failing probe enters
it. Both owned containers are absent; completed replay launches neither again. The opt-in
`tests/test_dev_execution_docker.py` requires `PATCHLOOP_TEST_REAL_EXECUTION=1`, separate
approval and a new external basetemp; do not automatically repeat it or the older
three-probe matrix. That pair used bare `python` and did not validate the task's absolute
interpreter path. The subsequent row-34 approval was paused before run creation/provider
dispatch: both v2 public checks were excluded from collection by literal argv[0] matching.
The path correction keeps the declared interpreter/argv, adds actual public-declaration
launch tests with Docker mocked, and exercises the absolute local interpreter. The opt-in
pair now uses `/usr/local/bin/python`; a separately approved run under
`C:\pt\pl26-abs-docker-a` passes in 7.96 seconds with one check and one probe. Both collect
the expected changed lines, clean their owned containers and replay without execution.
This is a synthetic public fixture, not task-evaluator or model-success evidence.
Runtime hash changes for the path correction; tool surface v26, prompt, inputs and probe
profile do not. Reconfirmed exact approval subsequently executed row 34 below. Its
collection/delivery succeeded, but this does not establish effective model use of an
unobserved range. Do not repair historical candidates, alter task packages or project
private evaluation material.

Row 34 on `ae34d076`, `run_dev_e9f798d9b3bb451c`, ended at `AGENT_STOPPED` after 24 model/
count calls and tools, three accepted mutations, $0.456825750 and 235.781 active seconds.
The model repaired a parent-mode failure and six upstream regressions; the final eight-line
candidate passed regression (517 passed, 570 skipped), but the earlier contract PASS was
on the previous diff. Both final native inputs explicitly list that contract as NOT_RUN,
with `needs_visible_checks` and `run_check` available. Before the last decision, 17 model
calls/77 tools/one mutation remained and check + finish needed two calls. The model instead
claimed completion via `stop_task` twice; stale/mixed evidence rejected the first request,
valid source evidence admitted the second. No finish, probe or isolated evaluator ran.
All four actual public checks collected changed-line feedback, delivered through native
outputs and current-diff summary. The final regression entered all selected executable
changed lines; line entry is not branch/assertion coverage or task acceptance. Journal,
envelope, 72 context/input/continuation artifacts and owned-container cleanup verify.
Next diagnostic seam: distinguish historical PASS from current completion and understand
completion-versus-stop selection without inferring private reasoning or adding a stop ban.
This observation alone does not isolate prompt/history causality. Do not resume, repair,
run a post-terminal check or execute row 35 without new exact authority.
The subsequent read-only diagnosis finds that `compact_model_state`'s protocol-only
rolling-card filter also removes the check card's unique remaining-check instruction:
present in the turn-23 audit context, absent from all native non-reasoning items.
Current NOT_RUN/remaining IDs survive. `recent_checks` has diff hashes but no explicit
historical PASS label; this is separate from correct diff-bound submission admission.
Preserve voluntary stop while clarifying that no further edit is not task completion.
All 65 existing focused tests pass but miss that final guidance-delivery boundary.
See current status for the diagnosis and its causal limits; no runtime fix was made.

V25 qualifies historical failures and aligns their guidance with offered
actions. Row 32 rechecked earlier edits with two/one mutations left, then stopped with
zero despite an unchecked candidate and available checks. This raises a budget/currency
interpretation hypothesis, not proof of the model's private reasoning. Pure-policy
checks cover both check orders and the real-failure/no-capacity boundary. Runtime and
projection tests do not establish changed model selection or final-candidate correctness;
a paid contrast experiment still requires separate exact approval. Keep schema order,
native continuation, budgets, task bytes and voluntary stop unchanged. Do not migrate
old state or execute row 34, resume, retry or Docker work automatically.

The subsequent, separately approved row 33 on `bac7c70f` produced
`run_dev_6159179ed34542f9`: `EVALUATOR_FAIL`, task acceptance FAIL, safety PASS,
20 model/count calls and actions, two accepted mutations, $0.366307650 and 196.811 active
seconds. Turn 15 made the first edit after 14 inspections. The public intermediate-mode
failure at turn 16 prompted a direct repair at turn 17; turns 18/19 passed both checks
and turn 20 submitted the same 37-line diff later applied by isolated evaluation.
Hidden tests failed while regression/scope passed; evaluator output stayed outside agent
context. Probes were enabled but unused, with no mutation rejection or protocol correction.

Turn 18's exact input contains historical-failure/recheck guidance, and the model's public
decision distinguishes the edited candidate. It still had two mutations left, so this
does not exercise the zero-mutations boundary or prove v25 caused the behavior. All 20
input histories, 19 unchanged prefixes, count/dispatch/cost identities and submission
provenance reconcile. The next diagnostic seam is remaining submitted-code semantics,
not an inferred need for more tool masks or mandatory checks. Do not repair the saved
candidate, reinject private evaluator material or execute another paid invocation without
new authority. Runtime/task/old run bytes remain unchanged; current docs record the result.

V24 separates audit accounting from a compact, complete model-facing view
and makes out-of-allowance mutation feedback explicit. Row 31's 1,824 assignments and
24 removals were faithfully delivered but required the model to reconstruct state; rolling
inspection arrays amplified repeated metadata. Both disallowed edits had the correct
allowance available. This is a presentation/feedback repair, not proof of a semantic root
cause for every agent mistake. Keep native history, current evidence identity, optional
notes/probes, tool masks, exact limits and pending resume unchanged. A full-view prototype
still grew final input until repeated file/action identities were grouped. The final
read-only row-31 comparison reduces final bytes 727,250 -> 651,085 and aggregate bytes
10,011,657 -> 8,853,286, preserving all 31 native episodes, 30 prefix edges and exact source
delivery coverage. These are UTF-8 serialized input bytes excluding tools, not tokens,
cache savings or counterfactual task success. Dynamic schemas remain a separate seam.
The implementation did not authorize a live row. The user subsequently approved the
single row-32 invocation below; that approval authorized no further row, retry or resume.
Old run/envelope bytes are immutable.

Row 32 `run_dev_8f19af52fb0948ca` on `c62e5299` records `AGENT_STOPPED`: 34 model/count
calls and actions, four accepted mutations, $0.778038600 and 324.014 active seconds.
One disallowed helper edit received the exact path allowance; turn 25 made the first
accepted wrapper rewrite. Bytes and intermediate-mode failures prompted direct repairs,
then traversal passed and upstream regression failed five cases. Turn 33 attempted a
final compatibility repair, but turn 34 stopped without checking that 50-line diff.
The exact final request offered `run_check`, marked both current checks `NOT_RUN` and
the old failure `awaiting_recheck`, and retained seven model calls/67 actions for a
three-call minimum completion path. Zero mutation budget did not prevent checking.
Do not present the stop prose's old PASS/FAIL as verdicts on the final candidate.

All 34 saved inputs, 33 unchanged prefixes, 12,168 source-line occurrences and count/
dispatch/cost identities reconcile. Cached input is 75.93%; eight tool-schema changes
remain. Twenty-four inspections (ten without new coverage), a later first edit than
row 31, and an untested final stop do not demonstrate improved agent efficiency.
Five note updates create/update six findings and all receipts arrive; later source
changes expire the notes. Final empty notes are not missing-delivery evidence. No probe,
submission or isolated evaluation ran. Keep the next diagnosis focused on preserving
existing behavior during repair, note lifecycle/use and interpreting old versus current
check status, without inferring private reasoning or adding mandatory action gates.
The post-run change is documentation only; runtime, task and old external bytes stay fixed.

Row 31 `run_dev_7754107f07f442e4` on `bcd85f71` records `EVALUATOR_FAIL`: public checks
PASS, isolated task acceptance FAIL, safety PASS, 31 model/count calls and actions,
three accepted mutations, $0.775517100 and 267.171 active seconds. Out-of-allowance
helper edits at turns 13/14 were rejected; turn 23 made the first accepted wrapper edit.
After six regression failures, turns 26/28 repaired public behavior and turn 31 submitted
seven added lines. The remaining trailing-separator defect recursively creates the leaf
before the final `exist_ok=False` call and raises `FileExistsError`. No probe ran.
All 31 inputs reconstruct exactly with 30 unchanged full prefixes; all request, patch,
execution-policy and cost identities reconcile. Cached input is 1,837,568/2,508,902
(73.24%) versus row 30's 8.73%, but total input rises 85.82%, final input reaches 178,154
tokens and six tool-schema transitions remain. Total cost falls 26.83% in this uncontrolled
comparison; do not infer task success or general efficiency. Native source references
remove retained-body duplication without removing native history. Ten finding submissions
create two notes and update them eight times; 16/17 receipts reach a next turn, with the
finish receipt durable only. Public concern resolution is not unseen-behavior validation.
Future live analysis must separate semantic generalization, use of the simpler current
view and schema cache boundaries. Do not add hard action gates or leak evaluator cases
into agent context. No runtime or task change accompanied the original row-31 audit;
the current v24 implementation is a later provider-free change.

V22 implemented the complete active native episode and replaceable state prefix.
This followed the row-29 diagnosis, not evidence that the live
model will reason efficiently. The former wire put one previous batch before a fresh
user context; effective reasoning mode was not recorded. Historical ciphertext audits
prove delivery integrity, not model reuse. Preserve exact provider input/history through
parallel, correction and crash/resume paths. No new notes, experiment obligation, action
mask, task-specific repair hint, output ceiling or global limit is introduced. Existing
notes remain optional and bounded. A later exact-approved row must assess history/mode,
repeated answered questions, first edit, public repair and submission separately.
Implementation did not authorize row 30; the user subsequently approved the exact
single invocation recorded below. No later row, retry or resume is authorized.

Row 30 `run_dev_f5f058fc5761480b` records the first live v22 observation: acceptance and
safety PASS, 29 model/input-count calls, 28 actions, two accepted mutations, $1.059868350,
and 277.578 active seconds. Scope rejected 67/52-line candidates at turns 19/21;
turn 22 accepted 38 lines. Turn 23's parallel checks were rejected before execution.
After separate traversal PASS and regression FAIL at turns 24/25, turn 26 immediately
restored delegation for paths without `..`. Both checks and isolated evaluation then
passed; turn 29 submitted 41 diff lines. All 29 native inputs and request hashes replay
exactly, including two synthetic rejection results. Mode is reported `current_turn`
throughout, not inferred from ciphertext. Existing 56 journal/envelope files are unchanged.

Inspection zero-coverage is 1/16 with no cache hits, compared with row 29's 15/30;
that one read requested 500 lines and failed the unadvertised 400-line bound. All 15
successful inspections added coverage; this was not one repeated successful read.
this is an uncontrolled observation, not a causal claim. Input grows to 90,851 tokens
and total cost more than doubles versus row 29 despite fewer calls. Three probes all
use the baseline, one with a syntax error; source findings stay empty and the initial
question/two advisory concerns are never updated. Do not claim memory/probe effectiveness
or general efficiency from acceptance PASS. The subsequent read-only audit found the
input-prefix/source-duplication defects addressed by v23, not a source-note storage failure.

Row 29 `run_dev_7005744ccb5d4cc1` reached `EVALUATOR_FAIL`, task acceptance FAIL and safety
PASS (`PRIVATE_EVALUATION_FAILED`): 32 model/input-count calls, 35 actions, one accepted
mutation, $0.482969550, and 290.593 active seconds. Turn 27's 60-line candidate exceeded
the 50-line scope and rolled back with exact typed feedback; after a cached read at turn
28, turn 29 accepted a 48-line candidate. Both public checks passed and turn 32 submitted
the exact artifact later applied by isolated evaluation, which failed task acceptance.
All 32 saved inputs reconstruct exactly; 32 continuation artifacts, 34 native results,
30 inspection-intent references, two note receipts, patch/policy provenance, and 54 prior
journal/envelope hashes passed the read-only audit. No probe ran, retry or resume occurred.

Do not equate the v21 projection fix with efficient use of evidence: 15 of 30 inspections
added no coverage, five were cache hits, and notes first appeared at turn 27. The delegation
body remained delivered through repeated requests to read it. Later 24k retention omitted
up to 151 helper-source lines, beginning at turn 25, without dropping that editable body.
Inspect repeated-question selection and the submitted semantic miss separately; this row
does not establish why the model chose its trajectory or that deduplication made it worse.
The subsequent developer-only in-memory diagnosis reproduces a missing existing-target
directory guard and a trailing-separator split termination bug in both the rejected and
accepted proposals. The 50-line reduction did not introduce either bug. These are
candidate-algorithm defects, not grounds to inject private cases into model instructions.
Do not feed private failures back into the coding agent or add compulsory planning/notes/
probes, weaker evidence binding, tighter masks, or larger limits based only on this result.
No automatic repair, retry, resume, or thirtieth live invocation is authorized.

The preceding tool surface `v20` puts the actual public check verdict/exception beside a
note's citation and dynamically marks its diff currency. Store facts at the note-update
boundary; derive currency without mutating the durable label. Test false prose remaining
nonblocking, different check/diff identities, unknown failures, source/probe exclusions,
parallel native delivery, crash/restart, and privacy. The probe schema explicitly describes
existing current-candidate importability and clean-Python limits. Shorter system guidance
preserves reusable facts separately from current failure status, without new quotas,
planning calls, mandatory probes, tighter masks, or higher budgets. The separately approved
v20 row 28 below passed, but did not exercise check-citing notes or candidate probes.
This checkpoint did not authorize the separately approved twenty-ninth row above.

Row 28 `run_dev_a01ff61f95be4a57` reached `EVALUATOR_PASS`, task acceptance and safety PASS,
with 20 model/input-count calls, 21 actions, two mutations, $0.193324200, and 133.016 active
seconds. Turn 15 reused the existing mkdir wrapper with parent recursion; after turn 16's
intermediate-mode failure, turn 17 removed the inherited leaf mode. Both visible checks
then passed and turn 20 submitted a one-file, 14-line diff for isolated evaluation.
The audit verified 20 continuation artifacts/19 exact replay edges, 20 native results,
eight note receipts, matching checked/submitted/applied patch identity, and prior run bytes.
All inspection stayed open; four reads/searches added no coverage, with no omitted source.
No probe ran. Turn 14's pending-source finding was correctly rejected; turn 15's two notes
were created and immediately expired by their source-changing edit, leaving no retained
findings in a later context. No note cited a check, so v20 label behavior was not exercised.
The original concern remained unresolved without blocking finish. Record the successful
causal repair separately from unproven memory efficiency or feature-level causality;
do not tighten masks, mandate probes/notes, or weaken source binding based on this result.

The preceding tool surface `v19` preserves observed unchanged complete-line fragments
across exact replacements and puts citation identity beside every retained check result.
Range diagnostics distinguish unobserved from stale-current evidence without weakening
admission. Keep v18 row26 immutable: its late source-note failures exposed lost current
bindings, not omitted source from the 24k projection. Local mapping, gaps, CRLF, drift,
crash/restart, annotation/native receipts, and identity passed provider-free validation.
Separately approved v19 row27 `run_dev_e68682d51d2a4dfa` used four accepted mutations,
29 model calls, 30 actions, and $0.349973100 before `LIMIT_REACHED`. It never submitted or
evaluated privately. Four public checks exposed two wrong helper owners, premature path
normalization, and finally a newly created leaf being treated as pre-existing. Two passing
baseline probes did not validate the candidate. Actual pre/post bytes verified all four
post-images and 11 retained fragments; 20 check-summary rows and 19 native note receipts
matched durable evidence. No source-range note failed; one nonexistent tool-result citation
was correctly rejected without blocking execution. Mutation capacity, not token/cost/model
capacity or forced inspection closure, ended the run. Diagnose evidence-to-code choices
before selecting another fix; do not infer that rebinding caused the task outcome or that
larger limits would solve it. This result did not authorize the separately approved row 28.
No automatic retry, resume, or later row was authorized by that result.

Tool surface `v18` preserved original verification questions separately
from progress, treats identical updates as no-ops, separates pre-batch note receipts
from current IDs, indexes already delivered header locations, and forecasts affected
tools using a conditional actual-policy successor. Preserve source-note expiry,
first-owner receipts, exact replay, budgets/action masks, and finish availability.
No task case, hidden oracle, new model step, or mandatory experiment is added. Tests
validate feedback contracts, not improved choices. Row 25 retained the relevant source;
the identified feedback defects do not establish what caused all repeated exploration.
Old nonterminal runtime mismatch still rejects resume; no migration is approved. The
separately approved row 26 below passed task acceptance and safety, but annotation
limitations remained; that result did not authorize row 27. V17 below is historical evidence.
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

The v26 interpreter-path correction passes 84 focused cases in 10.85 seconds and Ruff.
The full provider-free suite passes 614 cases, four real-Docker cases skipped, under
`C:\pt\pl26-abs-full-a{1,2,3,4}` using the established four-group partition:
60/68/85/401 in 83.47/106.14/79.23/125.90 seconds. The longest group exceeds two minutes;
do not describe the complete validation as under that target. Full-suite/mock wall time
including polling/review gaps is 163.25 seconds. The mock on those same runtime bytes,
`run_dev_4b69a2a4630041ad` under `C:\pt\pl26-abs-smoke-a` reaches mutation, checks, finish
and isolated acceptance PASS, safety NOT_RUN: four mock turns, five tools, zero cost and
`official=false`. The opt-in Docker test was skipped in that suite. A subsequent explicit
approval ran its absolute-path check/probe pair once in 7.96 seconds under
`C:\pt\pl26-abs-docker-a`, journal `run_dev_linevalidation_3c3ba21546c54e80`.
No provider call, task-private evaluation or row 34 follows from this Docker diagnostic.

V25 passes Ruff and 549 provider-free tests, three opt-in Docker cases skipped, across
the same four groups: 60/68/85/336 cases in 74.82/92.97/70.50/86.98 seconds under
`C:\pt\pl25-full-a{1,2,3}` and `C:\pt\pl25-full-b4`. The fourth group was rerun after
an exact v24 prompt-size assertion was replaced by the existing 8,007-character bound;
runtime bytes stayed fixed. Focused tests: 89 in 51.33 seconds. Eighteen new cases cover
current/historical/unknown failure currency, allowed-tool guidance, zero-edit completion
in either check order, genuine infeasibility, voluntary stop, exact native delivery and
restart/replay. Prompt size is 7,938 characters; full tool input schemas are unchanged.

Mock `run_dev_4b8f728934de4e53` in `C:\pt\pl25-smoke-a` reaches one mutation, visible
checks, finish and isolated evaluation: acceptance PASS, safety NOT_RUN, four turns/five
actions, zero cost, `official=false`, 4.87-second command. Envelope/manifest runtime
identity matches full-suite bytes. Each final partition/focused phase is under two
minutes, not the entire validation sequence with reruns. Read-only row-32 reprojection
changes guidance, not the saved evidence or model output. It is not a counterfactual
agent success; no paid contrast, Docker execution or thirty-third live row ran.

V24 passes Ruff and 531 provider-free tests, three opt-in Docker tests skipped, in four
concurrent groups of 60/68/81/322 (106.93/132.22/87.18/155.04 seconds), under
`C:\pt\pl24-verified-a{1,2,3,4}`. Partition: tools/context/source-rebind; runner/resume/state;
recovery/notes-v14/lifecycle/feedback/probes/policy-feedback-v18/note-temporal-v18; all
remaining files. Focused conversation/input: 78 cases in 40.49 seconds; final
feedback/catalog refinement: 32 in 30.98 seconds. Thirteen added cases cover rolling
state, current-view isolation, source delivery gaps/hash/fallback, exact check identity
and explicit path allowance with admission-crash/replay. The synthetic note-feedback
fixture now supplies its same public task at every input boundary instead of introducing
one after its initial turn; exact task identity remains enforced. Existing correction,
parallel, privacy, mutation and provider-uncertainty regressions pass with v24 framing.

Mock `run_dev_8e267bd533ae42dc` in `C:\pt\pl24-smoke-a` reaches mutation, visible checks,
finish and isolated evaluation: acceptance PASS, safety NOT_RUN, four turns/five actions,
zero cost, `official=false`, `claim_eligible=false`, 6.69-second command. Runtime stayed
fixed through full tests/mock. The full pytest phase exceeds two minutes (155.04 seconds);
focused tests do not. Record this limit; do not claim an under-two-minute full cycle.
The row-31 read-only comparison preserves 13,062 exact delivered line occurrences and
all native history, not a counterfactual success. No new live call or Docker execution ran.

Run only what the change needs, then broaden to:

```powershell
uv run ruff check patchloop tests
uv run pytest tests -p no:cacheprovider --basetemp <short-external-path>
uv run patchloop dev --provider mock --task tasks/smoke/csv-quoted-newline/public.yaml --model mock-dev --repeat 1
```

V23 passes Ruff and 518 provider-free tests in four concurrent groups of 60/68/60/330
(70.68/88.89/66.98/92.84 seconds), three real-Docker tests skipped, under
`C:\pt\pl23-verified-a{1,2,3,4}`. The partition is unchanged: tools/context/source-rebind;
runner/resume/state; recovery/notes-v14/note-lifecycle/note-feedback/probes/feedback-v18/
note-temporal-v18; all remaining test files. Twenty-five new cases include 256 nested
JSON state pairs, typed null/bool/number identity, array trim/append, exact prefix and
hydration, correction clearing, source union/gap/hash/conflict/blank-line boundaries,
bounded inline fallback and read-range description/runtime consistency. Existing four
crash-boundary, provider uncertainty and pending-replay tests run with v23 framing.
Focused conversation/contracts: 59 passed in 12.70 seconds. Feedback refinement:
54 passed in 19.52 seconds. The initial stale test fixture compared an unsent marker
with a different saved turn; corrected to compare actual sent inputs. Nested key-order
differences after hydration are normalized instead of weakening exact-replay assertions.

Mock `run_dev_f84797eb6e034ce5` under `C:\pt\pl23-smoke-a` reaches one mutation, visible
checks, finish and isolated `EVALUATOR_PASS`: four turns, five actions, acceptance PASS,
safety NOT_RUN, zero cost, `official=false`, `claim_eligible=false`, 4.87-second command.
Runtime files were frozen throughout full pytest/mock. Focused and full pytest are below
two minutes; the manual complete sequence including polling/review gaps took 166 seconds,
so do not describe it as an under-two-minute full cycle.

The row-30 comparison is read-only and in memory, not an old-envelope resume. All 29
reconstructed inputs preserve original native items and 28 append-only prefix edges.
Retained-source duplication goes from 542,268 characters to zero, but cumulative canonical
input bytes rise from 5,960,829 to 7,783,355 because prior state deltas remain in history;
final input is 608,946 versus 435,299 bytes, excluding tools. Do not turn these bytes into
billed tokens or assume cache hits. No source finding was submitted in row 30, so unused
notes are not evidence of storage loss. Future separately approved live evaluation must
measure actual cache/cost and the model's use of updated state, not only hash integrity.
No provider call, Docker execution, old-run migration or thirty-first live row ran.

V22 passes Ruff and 493 provider-free tests in four concurrent groups of 60/68/60/305
(72.78/90.91/68.34/94.61 seconds), with three opt-in Docker tests skipped. Roots are
`C:\pt\pl22-verified-b{1,2,3,4}` using the same file partition as v21 below. Eighteen new
cases cover the single-user episode, ordered replaceable state, old history integrity,
reported-mode privacy, parallel/correction carry, four crash boundaries and exact input
counting; 54 focused refinement cases pass in 46.29 seconds. Mock
`run_dev_719b638249c246aa` in `C:\pt\pl22-smoke-b` reaches mutation, visible checks, finish
and isolated `EVALUATOR_PASS`: four model turns, five actions, one mutation, task acceptance
PASS, safety NOT_RUN, zero cost, `official=false`, `claim_eligible=false`. Frozen
Ruff/full-suite/mock wall time is 102.488 seconds. Ordered tool schemas, task/limits and
note policy are unchanged; native framing adds a short instruction outside the unchanged
base system prompt. The test-local helper-shadowing failure in the first full-suite
attempt was fixed, and the new state prefix preserves existing context field priority.
No live provider or Docker execution ran; historical run/envelope bytes are not migrated.

V21 passed Ruff and 475 provider-free tests in four concurrent groups of 60/68/60/287
(94.86/117.10/87.92/103.01 seconds), with three opt-in Docker cases skipped. Short roots
are `C:\pt\pl21-verified-b{1,2,3,4}`: tools/context/source-rebind; runner/resume/state;
recovery/notes-v14/note-lifecycle/note-feedback/probes/feedback-v18/note-temporal-v18;
and every remaining test file, respectively. Thirteen new cases take 2.60 seconds.
Mock `run_dev_9ec8c92cf7e34e9a` under `C:\pt\pl21-smoke-b` reaches isolated `EVALUATOR_PASS`
through one mutation, four model turns, and five actions: acceptance PASS, safety NOT_RUN,
zero cost, `official=false`, and `claim_eligible=false`. Frozen full-suite/mock wall time
was 128.0 seconds, slightly over the two-minute target; focused tests remained below it.
Runtime files were unchanged during validation. The actual prompt and ordered tool input
schemas are unchanged. Keep historical run bytes immutable; no live row is authorized.

V20 passed Ruff and 462 provider-free tests in four concurrent groups of 60/68/60/274
(71.99/88.86/66.64/76.73 seconds), with three opt-in Docker cases skipped. Short external
roots are `C:\pt\pl20-verified-a{1,2,3,4}`. The 15 new cases cover recorded verdict/exception
labels, false interpretations, historical/unknown currency, note crash/replay, parallel
delivery, privacy, and unchanged ordered model input schema. System prompt length is
7,880 characters, down from 8,007. Mock `run_dev_fe269097df164a83` under
`C:\pt\pl20-smoke-a` reaches isolated `EVALUATOR_PASS` via four model turns, five actions,
and one mutation: acceptance PASS, safety NOT_RUN, cost zero, `official=false`, and
`claim_eligible=false`. The final frozen Ruff/full-suite/mock sequence took 103.5 seconds,
excluding earlier debugging. No paid provider or Docker execution occurred; no additional
live authorization follows from these local tests.

V19 passed Ruff and 447 provider-free tests in four concurrent groups of 60/68/60/259
(69.70/86.16/64.59/67.54 seconds); three real-Docker cases remain opt-in/skipped.
Roots: `C:\pt\pl19-verified-c{1,2,3,4}`. The frozen Ruff/full-suite/mock sequence took
93 seconds, excluding earlier focused debugging. Mock `run_dev_41da713dc2504dea` under
`C:\pt\pl19-smoke-c5` reaches mutation, visible checks, finish, and isolated evaluation:
four model turns/five actions/one mutation, task acceptance PASS, safety NOT_RUN, zero
cost, `official=false`, `claim_eligible=false`. New tests cover exact-position evidence
reuse, no inferred gaps, error-range privacy/bounds, same native/restart identity, and
CRLF/no-final-newline/second-anchor crash recovery. Source-note semantic expiry remains
independent of retained line evidence. This checkpoint did not authorize the separately
approved rows 27-29 recorded above; no subsequent live invocation is authorized.

V18 passed 414 provider-free tests in three concurrent groups of 75 (90.71 seconds),
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
no new model-quality claim or additional live authorization followed from that checkpoint.

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
