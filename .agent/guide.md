# Internal implementation guide

This is the agent-only companion to the required root `AGENTS.md`. It summarizes
active contracts for navigation; checked-in source remains the behavioral authority.

## Source map

```text
patchloop/dev/runner.py   loop composition, gates, context, terminal handling
patchloop/dev/conversation.py  default append / opt-in snapshot window, current view and recovery
patchloop/dev/model_state.py   compact public model view, separate from audit accounting
patchloop/dev/native_sources.py  exact current-source delivery references into native history
patchloop/dev/tools.py    tool grammar, spans, mutations, checks, finish
patchloop/dev/check_feedback.py  complete-line public output and terminal diagnostics
patchloop/dev/state.py    append-only JSONL, action/provider recovery
patchloop/dev/evaluation_completion.py  durable evaluator receipt and read-only recovery validation
patchloop/dev/cost.py     reviewed prices and pre-dispatch admission
patchloop/agent/model.py  journal-managed Responses adapter, zero retries
patchloop/repository.py   audited checkout, workspace, full diff
patchloop/git_execution.py  exact Git output, deadline and uncertain-execution boundary
patchloop/sandbox/        registered checks and optional isolated public probes
patchloop/sandbox/capture.py  bounded check-output drain and process/pipe teardown
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
Compute that forecast with the same B/P function as an immediate mutation attempt,
not the already-successful successor. Include the first rejected attempt's unused
two-call reserve even on the last mutation or when no check recovery allowance remains.
Do not double reserve that allowance or include an optional read before the selected edit.
The minimum path and actual offered tools remain unchanged by this forecast correction.
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
or evaluates. Its tool arguments are the existing reason code/summary and turn decision;
do not ask the model for source-span IDs. The gateway attaches the current diff identity.
Retired citation fields are strict input errors, not new semantic reasons to reject a stop.

Derive `completion_guidance` from the already prepared gateway snapshot and actual
offered policy, without re-executing checks or modifying admission. Project workflow
gate, this guidance, current check table and remaining IDs first. A current FAIL or
empty diff points to an offered repair/evidence action; an unchecked candidate names
an offered remaining check; a ready candidate names `finish_task`. This is advisory,
not proof that a supported semantic repair exists or that all public behavior was tested.
At submission eligibility, mention an optional discriminating public experiment only
when `run_probe` is actually offered; otherwise name finish without inventing an action.
No review call, annotation, experiment quota or new gate is required. Keep guidance in the
latest native
view even when historical attempt cards are omitted. Label retained check summaries
with `evidence_currency` and `counts_toward_completion`; preserve original verdicts
and action/check/diff identity. Missing currency is unknown, never current credit.
Only current-diff PASS counts; do not rewrite historical native results. Clarify
unsuccessful `stop_task` versus submission, but never reject a stop based on its prose
or automatically run the suggested action. Test the actual native boundary and restart,
not only the canonical audit context.

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

V28 projects an `observation` ahead of native probe `output`: `execution_status=completed`
means the recorded process exited normally, while `behavior_verdict=not_assessed` never
certifies the question. Preserve nonzero, timeout, output-limit and cleanup outcomes.
Summarize already public line-entry evidence for at most four files, three observed and
three not-observed ranges each, with full line counts and explicit omission counts.
Unknown collection remains null, not zero hits. Do not infer branches, assertions, values
or untried inputs. The full feedback/stdout/stderr and action/diff/file identities remain
available. Only the model view drops the ambiguous output `status`; the original sandbox
receipt, journal, probe provenance and concern-resolution admission are unchanged.
Context-only and native results share this projection. Retained model-state probe cards
reference identical native observation details instead of repeating ranges. Hydration is
deterministic; already sent native history is never rewritten. Tool descriptions recommend
one discriminating public input variation and an expected observation using the existing
question/source fields, not a new schema, mandatory note or extra model call.

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

For a successful mutation, `DevToolResult.workspace_diff_hash` names the completed
full candidate, equal to `output.worktree_diff_hash`, `output.mutation.diff_hash` and
post-image source diff identity. `output.baseline_diff_hash` names the full pre-state
from admission, not the candidate found on disk during reconciliation. The incremental
replacement's `output.patch_hash` remains distinct. Results are action-time snapshots;
replaying an earlier action must not replace its hashes with the latest workspace.
Failed mutation workspace identity remains the post-rollback baseline, with the existing
typed failure diagnostics. Reads/searches/checks/probes keep their existing identities.
Do not migrate old results or rewrite previously sent native history. Admission and
reconciliation continue to use `action_started.baseline_diff_hash` and the admitted
complete candidate; no extra filesystem read or semantic check is added for these labels.

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
For a newly delivered mutation result, replace an unchanged `revalidated_spans` body with
backward `content_delivery` only when its admitted action/input/candidate identity and
pre/post raw hashes match. Map complete lines using the admitted replacement position and
line delta, never a text search. Each reference names the earlier action/field/file hash,
inclusive source range and `target_start_line`; keep the new span's current file/diff
identity and normalized `content_hash`. Use at most 16 references and only when their
final serialized UTF-8 form is smaller. An unproven, partial, conflicting or touched span
stays inline. Resolve alias chains chronologically with complete range/body-hash checks;
self/forward references cannot gain authority. No filesystem read or new evidence admission
is performed. The gateway and canonical audit retain exact bodies; saved native prefixes
and original mutation receipts never change. Context/native mutation projections omit
`alternative_requirement_satisfied`, while raw receipts and internal recovery telemetry
retain it. Keep current post-image, bounded changed hunk and typed failure feedback exact.
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
Observation and note retention share CRLF-to-LF normalization. Mixed LF/CRLF is
readable and can back notes, including read-only helpers; raw-byte hashes still
identify files. Mutation-only mixed/legacy-newline refusal must not expire an
unchanged readable note. Exact replacement retains that separate format restriction.
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
status already has `current_public_failure` for the current diff or `pending_recheck`
for an edited-but-unchecked candidate in the model view. Historical failure is not a
current-candidate verdict. Do not overwrite reusable knowledge with a copy of
that status. The system prompt encourages reuse of existing responsibilities and asks
whether another inspection can change the edit or next check. These remain optional
concise findings, not a mandatory plan or a harness guarantee of semantic correctness.
V34 compresses the dedicated system memory block and memory/concern schema descriptions
only. Field-local descriptions carry API construction details; the system block keeps
purpose, timing and interpretation/lifecycle boundaries. Preserve nullable/required
shape, property/tool order, bounds, source validation, state/receipt projection and
replay. No note quota, semantic judge, cross-run retrieval or new call is introduced.
The shorter guidance does not establish better note use or task performance.
`memory_update=null` preserves the notes and question; `open_question=null` inside an
update resolves the question. The harness does not automatically merge similar prose.
Before an observation, use an open question or null update; findings may cite only
source/results observed before the current batch. The next native output carries the
owner call's `memory_update_result`, independently of main-action status. Its bounded
per-finding outcomes identify created/updated/rejected IDs and a recovery hint; separate
batch/removal diagnostics never repeat the finding's message. The model view references
the full exact receipt already delivered by its action/turn in any earlier native output,
not only the latest batch. Never substitute a different receipt or drop an undelivered one;
missing/mismatched delivery keeps bounded inline feedback. The canonical audit and native
receipt remain exact. Do not
confuse its `scope=before_tool_batch`, `diff_hash_at_update`, and historical
`note_ids_after_update` with current availability. `working_notes.available_note_ids`
is current retained-ID authority. The native owner output's `working_notes_after_batch`
labels the completed batch's diff/current IDs and only that action's expired notes.
A successful mutation that expires notes also carries this post-batch notice when
`memory_update=null`; it does not fabricate an update receipt. Match the durable lifecycle's
trigger action, never attach an older expiry to an unrelated read/check, and never alter
expiry/rebinding, ID allocation, annotation rejection or main-action admission.
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
The following complete-prefix contract describes default `append-v1`.
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

Opt-in `native-window-v1` uses `single-user-managed-window-v1`, not that complete-prefix
validator. Its immutable seed is the first three items; only recognized post-seed
`harness_current_state` snapshots expire. Keep at most one current view after the seed.
`public_history.SnapshotRules` shares the pure diagnostic evidence projector without
importing diagnostics into runtime. A removed view's unique complete source lines,
public exchange versions and harness observations are rescued as
`harness_historical_public_evidence_v1`, at the replaced historical position. Native
encrypted reasoning/calls/outputs remain exact and ordered; never fabricate native
results from harness receipts. Known mutable controls, expired notes and consumed
corrections are not revived. Unknown public observation fields are retained exactly.
Sources use path/raw hash/inclusive line/LF body; no unseen gap or filesystem read.
Resolve current references against visible native or quoted public exchange deliveries;
plain archived source facts without an action ID retain inline fallback rather than
inventing one. Validate groups chronologically, never using a future delivery.
Gateway evidence admission and current PASS/notes stay independent of the archive.
The 24,000-character current-source budget and latest complete batch are unchanged;
there is no lossy archive cap or compaction call. Preserve default wire equivalence.
Turn metadata binds policy, seed CAS/hash/window ID, parent input, consumed decision,
current-state hash and exact public-evidence inventory. Seed CAS uses canonical JSON
bytes, not pretty JSON with a different byte hash. Resume checks seed, parent native
prefix and public-evidence inclusion before pending tools/count; broken saved inputs
end at `PROVIDER_CONTINUATION_ERROR`. A started-only turn is not a consumed decision.

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
Each group has `edit_permission=allowed|read_only`, derived from the immutable public
constraints using the same case-sensitive matcher as gateway mutation admission, with
forbidden paths taking precedence. This labels path permission only, not complete anchor
coverage, semantic readiness, remaining edit budget or actual tool availability. Preserve
the existing glob semantics; search's separate rooted-component matcher is not this policy.
Context-only fixtures lacking public constraints omit the label rather than infer permission.
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
The canonical audit preserves that full qualified focus. In the derived model view,
keep actual current failures unchanged; move historical/unbound focus to `pending_recheck`
and clear `current_public_failure`. Reference the earlier native result only when its
action/check/diff and entire failure payload match. Otherwise retain bounded original
details explicitly as historical/unbound. Do not duplicate the old recurrence/repair
claims as a current error. Current check status remains authoritative; recheck PASS
clears pending and recheck FAIL supplies the new current failure. Preserve original
native outputs, prior input prefixes and all replay identities. Optional inspection
and independently evidenced edits remain available under the same budgets.
The default prompt distinguishes completion of this candidate from the separate further-edit
horizon. Do not change tool masks or reject a voluntary stop on this basis. Only the
explicit repair-recheck experiment below schedules a check without a model choice.
Recheck a repair before assuming the old failure persists. A proposed explanation is
not a verified defect; a helper header does not establish its unread return behavior.
These are concise task instructions, not required planning or raw-reasoning output.

Public check bodies retain complete LF/CRLF lines: sandbox byte-prefix allocation,
12,000-character gateway tails and 4,000-character recent-check tails. Preserve fitting
EOF lines without a newline; omit a cut line rather than publishing its fragment.
Keep existing caps/stdout-first allocation and propagate every clipping stage through
`truncated`. Parse already captured public output before gateway reduction; never read
another file or private evaluator input to enrich feedback. Final pytest failure rows
take precedence over intermediate chained exceptions. Otherwise accept recognizable
pytest exception lines or a Python terminal frame. Unframed words and mixed/unknown
terminal types stay null. `failure_summary` is literal observed public diagnostics,
at most eight complete lines / 4,000 characters, with observed_count and truncation;
do not label comparison operands as expected/actual or infer a causal explanation.
Durable focus/native/check evidence and restart preserve that summary. Old completed
action results are restored verbatim, not reclassified by the current parser. Verdicts,
deadlines, policy hashes, raw-tail failure-signature formula and all workflow gates
remain unchanged; only captured/retained output and diagnostic semantics change.

Terminal resume returns that same public result. Current semantics are tool-surface `v37`;
do not migrate old envelopes or journal bytes.

### Opt-in repair-recheck feedback

`DevRunRequest.repair_recheck` / `--repair-recheck` defaults false and is bound in
the exact run envelope. No tool name, input schema/order, prompt, memory requirement,
provider continuation or action mask changes. The v36 surface hash records this
scheduler/output contract; old runtime envelopes remain immutable and mismatched.

After the native mutation batch is durably complete, select the latest still-failing
registered check on that mutation's baseline, using only action results preceding
admission. A newer PASS supersedes its earlier FAIL. Trigger only for a successful,
diff-changing replacement; not rejected/initial edits without current failure,
historical failures on other diffs, probes or speculative hypotheses. If multiple
checks fail, choose the latest one by journal sequence, independent of declaration
order. Rerun exactly that check through the existing gateway before a new inference.

`repair_recheck_started/finished` bind origin=harness, parent mutation, previous
check action, check ID and baseline/candidate hashes. A deterministic child action
uses normal action_id+input_hash and sandbox execution identity. Count its reservation
once as a tool action, not a model/count call. Resume drains pending native actions
first, then this child, then recomputes the completion horizon. Existing minimum
completion already includes all invalidated checks; this consumes one reserved check
without reserving another model turn or changing the conservative B/P calculation.

Do not add the child to a native tool batch or encrypted function-call history. Its
bounded stdout/stderr use existing recent-check tails in public current state; an
explicit repair_recheck receipt identifies the harness action and checked diff. Keep
its available recent-check row pinned; do not falsely reference a native function
output. No additional source/private information or model-authored interpretation
is produced. Other checks must still pass on this diff before submission.

Replay completed child results without execution or another charge, including after
expiry. A check interrupted before a durable result follows existing exact-container
cleanup/re-execution semantics: this is not a promise of exactly-once physical
execution across that uncertainty window. Workspace mismatch, cleanup uncertainty,
deadline and tool-limit boundaries stop before another inference. A semantic FAIL
instead supplies the new current error and ordinary remaining-budget workflow.

This tests feedback timing, not whether the next repair is correct. Default behavior
stays off. No live grant, Docker start/pull/build or prior-run migration follows.

## Local storage hygiene

New disposable pytest basetemps belong only under `C:\pt\tmp\<unique-name>`, not
directly under `C:\`, beside durable experiment records, or inside the repository.
Each parallel test process owns its own exact child directory. Keep JUnit reports
under `C:\pt\validation`, or in the current durable diagnostic record, before cleanup.
After the process and its children have exited, recycle the owned temporary root;
retain a failed-test workspace only while it is needed for diagnosis. Never sweep
the parent, empty the Recycle Bin automatically, or infer disposability from a name.

Durable runs, CAS objects, experiment packets, analysis, submitted patches and their
workspaces are not pytest scratch. Preserve existing paths and bytes; state roots and
recorded absolute paths must not be relocated as a side effect of housekeeping.
Credentials, user-owned `AGENTS.md`, task packages, historical reports and existing
repository-local scratch remain outside this cleanup scope. For an approved legacy
cleanup, freeze exact targets, exclude active processes/locks and reparse points,
confirm actual Recycle Bin delivery and retain a restoration list separately.
The approved 2026-09-10 legacy cleanup recycled 598 pytest roots; its exact mappings
and hash checks are at `C:\pt\maintenance\cleanup-20260910`. Old pytest basetemp
references may therefore point to recycled scratch, not missing durable run evidence.

## State and recovery

Each run owns an external `dev-run-v1` JSONL stream with sequence, prior hash, and
event hash. Mutations and checks use `action_id + input_hash`; identical input
replays the durable result, conflicting reuse fails closed, and an admitted
mutation is reconciled after a crash instead of applied twice. A provider start
without durable usage is uncertain and must not be retried automatically.

New runs also own one immutable `dev-run-envelope-v1`. `--resume-run-id` requires
`repeat=1` and an exact match for provider, task, runtime, model, reasoning,
credential path hash, cost cap, limits, repair_recheck/context_policy options, and sandbox identity,
including the opt-in probe
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
One active monotonic deadline starts before workspace creation and live preflight,
then reaches provider counting/generation, Git, tool execution and isolated evaluation.
Git waits use a shared wrapper with exact file-backed byte capture, remaining-time
timeouts and a finite standalone default. An interrupted Git process has unknown
descendant cleanup even if the direct process is reaped: stop the row/repetitions,
never retry or claim process-tree termination. Allow only bounded read-only metadata
and exact mutation reconciliation after expiry; no new task execution. Record the
harness Git identity at row admission and reuse it for post-deadline provenance.
Docker checks bind run/action execution identity so crash recovery does not duplicate
the same check container; a check timeout is not model protocol failure.
If launcher execution raises, preserve the original exception only after confirmed
owned-container cleanup. Otherwise raise typed `SANDBOX_CLEANUP_FAILED` with the
failed execution-policy hash and `cleanup_failed=true`, including on interruption.
The gateway journals that result and stops further tools/repetitions; it must not
flatten uncertain cleanup into a retryable generic tool error or semantic check failure.
Registered checks drain both output pipes concurrently while retaining only bounded
prefixes; exceeding their public output cap does not stop a check or change its exit
verdict. Allocate stdout-first using total observed bytes, align clipped output to
complete lines, and keep the separately bounded trace-report channel. Pipe/read/close
or join uncertainty is an execution error, not a semantic failure. Docker cleanup and
reader teardown share the remaining cleanup budget. Probes retain their separate
stop-on-output-limit contract below.

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
Before `evaluator_finished`, store the evaluation summary and terminal provenance
in CAS. That single completion event binds the original artifacts, terminal/message,
active elapsed time and repetition-stop flag. Both normal completion and resume use
the same metadata-only finalizer. After exact envelope and provider-uncertainty guards,
a completed evaluation resumes without workspace, credential, sandbox or evaluator
execution; validate the stored submission/manifest/provenance before writing a terminal,
including the explicit typed completed-check artifact references and their CAS bytes.
Preserve result/provenance bytes and partial-error evidence. A crash before durable
`evaluator_finished` does not prove completion; this is not an exactly-once evaluator
process guarantee. Old envelopes/events are not migrated.
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

Current seam: failure-given repair input/criteria preparation only; no paid authority.
`diagnostics/failure_given_repair.py` has only prepare/validate entry points. Packet:
`C:\pt\analyses\failure-given-repair-20260914\ready`, SHA-256
`8a1ea07a28fa7035419445cd7634fa23fddc586a08bdac1d9604ec42e946e7b3`.
Restore the identical A2 pre-turn22 native request using the existing public-prefix
restorer. Verify the sealed operator panel completion, packet, source, A2 receipt
and hash-chained journal, public spec, diff and target raw file identity. Project only
the selected multi_parent case: str a/../b/../c, initially empty cwd, Linux/umask022,
mode0777/exist_ok=false; real a, b, c versus fake a, c, no exceptions, mode0755.
Other cases, candidate diagnoses, source locations and repair hints are not input.

The sole overlay is state.operator_public_feedback in the latest unsent snapshot.
Do not append another user message: native v38 requires one immutable task message.
Keep historical items, 21 opaque reasoning items/native action pairs, prompt, tools,
notes, budgets and actual check status unchanged. No review suffix, forged native
action, failed-check credit, enforced probe or finish gate. Mark origin as
operator_executed_public_diagnostic; the observed diff is the report's only authority.
After native construction a future adapter must overlay the same report once in the
latest view and matching context artifact, relabel it historical_candidate after a
diff change, and preserve all already-sent items. Read-only restoration is tested; NOT a
tested execution/recovery adapter yet. Initial wire delta: 1,601 bytes, not tokens.

Rubric: observed acknowledgment != semantic repair; admission != correctness;
same-case agent probe != operator audit; inherited visible PASS != new execution;
finish != bug resolution. Freeze an independent one-case reproduction from the
existing public panel, for post-episode operator checks only. Never give the agent
credit for that audit or feed its result back into a finished diagnostic branch.
Current public checks remain the registered two, not this additional diagnostic.
One selected case/checkpoint cannot distinguish all model/context causes or prove
autonomous discovery/generalization. Old no-feedback responses are not fresh controls.

Plan two independent F1/F2 continuations, <=8 calls each, $0.50 each/$1 total,
no transfer/retry/resume/extra sample, full25k admission and unchanged mini/medium.
Prices must be reviewed and the exact request counted before later live admission.
No credentials/provider/Docker/patch execution in preparation; task/private/safety
NOT_RUN, official=false. New model calls need an executable packet and fresh grant.
55 focused tests and Ruff pass; actual prefix replays twice with forbidden network/process/
secret access; 6,391 protected hashes match. Validation root:
`C:\pt\validation\failure-given-repair-20260914`. Runtime/default/task unchanged;
full runtime suite and isolated evaluator smoke not rerun for this no-call design.
Next scoped implementation reuses the bounded collector, with real native feedback,
currency/correction/recovery tests before paid authorization, not more agent gates.

Prior seam: voluntary counterexample-review packet completed; approval consumed.
Evidence: `C:\pt\analyses\counterexample-review-live-20260913`.
Exact packet `6502091980b8b38dc6c47e730c6418c51e95a953cec4c793e3b6e16b6434e367`
ran once, A1/B1/B2/A2, mini-2026-03-17/medium/.env, $0.50 each/$2 total, v38 intact.
A1/A2/B2 immediately finished; B1 probed Windows-mode bytes parent traversal, saw
two existence assertions pass, then finished. All submitted unchanged `43fb9b2b...`.
Five provider/counts and tools, no new mutation/registered check; 57.693s,
$0.194283150 known model cost. Current public PASS was inherited, not re-executed.
Hidden/task_acceptance/safety NOT_RUN and official=false; not four task successes.
Initial requests, encrypted/native prefixes, suffix counts and usage costs verify.
One real probe/cleanup confirmed and exact container absent. No truncation, cap,
deadline or action-mask closure caused submission; no new failure exercised repair.
The selected probe is public-grounded and falsifiable but narrow (Windows emulation
plus bytes, one parent traversal), not an OS-wide differential test or a defect found.
Do not infer repeatable quality improvement, memory/planning causality or adopt B.
Code content was label-masked before key opening, but prior operator status exposed
arm/count metadata; document this limited masking, not independent blinded scoring.
Terminal note updates in A1/A2/B1 tried unknown v1/v2 concern IDs. Gateway rejected
those resolutions non-blockingly. A2/B1 notes reference a historical failed check
while describing current PASS; typed historical evidence remains FAIL. These notes
accompanied finish and did not feed an earlier choice here; no causal attribution.
5,571 protected hashes verify. `approval.json` records the user's new authority:
the immutable execution envelope copied the prepared paid_execution_authorized=false
flag, so do not rewrite it or confuse that stale plan flag with absent user approval.
Model-rate cost != invoice/count-endpoint billing. First A/B had zero cache and
second samples reused 102,784 tokens each; cost/behavior effects remain separate.
No further paid run/resume/retry, operator cases, hidden evaluator or default change
is authorized. Keep these workspaces as actual execution evidence, not pytest scratch.
Next scoped decision concerns discriminating test selection and completion confidence;
do not infer a need for more hard gates from one post-hoc checkpoint/two samples.

Prior seam: counterexample-review collector implementation and frozen preparation.
`diagnostics/counterexample_review.py` restores A2 `run_dev_8d592587618448b7` turn22
from its public prefix. Artifacts: `C:\pt\analyses\counterexample-review-20260913`.
Both current checks PASS, 19 model/78 tool/2 accepted mutations remain, 1619 seconds.
A unchanged; B appends one generic falsification/verification system suffix once.
Do not inject the operator's 14 cases or findings. Preserve task/source/notes/native
results, all 21 encrypted reasoning items and 21 action pairs, and exact tool order.
No forced tool_choice or finish gate; the original prompt already mentions probes.
The first system-message suffix changes cache-prefix identity; report that cost effect.
Four new branches A1/B1/B2/A2, round-robin, <=8 calls each, $0.50 each/$2 shared
planning cap, no transfer, no paid approval. Exact counting/full25k admission required
later; do not lower output to fund a tail or treat censored samples as semantic failures.
The immutable design module remains `prepare`/`validate` only. The separate
`diagnostics/counterexample_review_rollout.py` adds `prepare`/`validate`/`run` without
altering the frozen design or any default runtime/task/prompt/tool-policy bytes.
Executable packet: `C:\pt\analyses\counterexample-review-executable-20260913`;
`plan.json` SHA-256 `6502091980b8b38dc6c47e730c6418c51e95a953cec4c793e3b6e16b6434e367`.
Approval must identify that exact packet, task/model/medium/root .env, four branches,
<=8 new calls each, $0.50 each/$2 total, probes/recheck ON and a fresh external result
root. `run` requires `--approval-packet-hash`, `--credential-file`, `--max-cost-usd 2`
and `--pricing-verified-on` equal to the current UTC date. The date is an operator
price-review assertion, not an automatic price lookup. No paid authorization yet.
SDK retries zero, count wait 30s, response wait 300s, client cleanup 5s; effective
limits are clipped by branch-active/global 1800s deadlines. No Docker start/pull/build.
Count/transport/billing/continuation or unconfirmed cleanup aborts the experiment;
branch cost/8-response bounds censor only that branch. No lowering the 25k ceiling,
transferring budget, automatic replacement samples, experiment resume or root reuse.
The source context contains larger storage representations than the sent view: prove
the full native request by `_build_model_input` replay, then compare stable identity
fields. Do not mistake intentional native-reference projection for evidence loss.
The adapter uses the existing dispatcher/reconciliation plus active native context
and repair-recheck paths. Import both repair_recheck events; otherwise the inherited
tool count and feedback are wrong. Derive the two accepted mutations from the restored
gateway, not an older collector's hard-coded three. Count new harness rechecks as
tool actions, preserve their real origin, and never fabricate native function calls.
Resolve durable work before budget admission. Terminal finalization uses the last
recorded diff/check identity without running Git after deadline; pending worktree
state is not claimed current. A/B initial request bytes and all source/notes/native
items are restored exactly. No forced probe or finish gate is inherited from the
older probe-first collector. B retains its sole system suffix through native history.
Tests cover optional probe/repair/check/finish, correction/continuation, fault replay,
automatic recheck, actual-prefix no-call restoration, per-branch caps, all-branch
uncertainty stops and deadline receipts. External validation/preservation/cleanup
receipts accompany the packet. Real provider/count, Docker, pyfakefs candidate checks
and hidden evaluation remain NOT_RUN. Full runtime suite/isolated-evaluator smoke
not rerun: runtime/default/task unchanged. Next is exact paid approval, not more
default agent scaffolding or an assumed benefit from the review instruction.
85 focused tests PASS/93.071s; 5,556 protected hashes verified. `final-validation.json`
records the final Ruff/docs checks after wrapping an external audit-helper long line;
the original validation receipt is retained, including that corrected lint failure.
Score useful model-authored cases, actual execution, evidence-responsive repair,
same-case recheck, current visible checks/finish, cost and censoring separately.
No hidden evaluator or paid judge. Single post-hoc seed/two samples per arm are not
general capability or default-adoption evidence. Runtime v38/task/default unchanged.

Prior seam: provider-free public counterexample diagnostic completed.
Evidence: `C:\pt\analyses\public-counterexamples-20260913`, packet `06cd6fb9...`.
Four saved candidates plus local BASE clone, 14 fixed public-spec cases each,
existing public probe sandbox, Linux/Python 3.12.13/umask 0o022. Setup snapshots
match before each operation; real os.makedirs outputs match across all five subjects.
Compare errors and full filesystem side effects, including modes after an error.
Agreement BASE/A1/B1/B2/A2 = 1/11/11/8/7 of 14, not a hidden score or global ranking.
A2 omits b from a/../b/../c; bytes variant agrees while the str early-break path fails.
B1 still accepts file/../leaf and resolves two directory-link/.. destinations wrongly.
B2 has existing-target/error-path mode/link failures. Preserve original EVALUATOR_PASS
and FAIL records; the new public counterexamples supplement their finite coverage.
Do not infer exact hidden failures or invalidate old results by rewriting them.
All candidates differ on the two valid-link traversal cases. This proves candidate
semantic defects, not missing planning/memory/context as their isolated cause.
No agent in the prior four runs called run_probe; these are operator-authored checks.
Do not give the agent credit, add the cases to immutable tasks, force probe use, or
inject task-specific solutions into default prompts under this diagnostic approval.
5 sandbox calls/70 comparisons in 21.313102s, zero provider/count/generation cost;
hidden evaluator, Windows/macOS and task_acceptance NOT_RUN, official/claim flags false.
5,514 protected file hashes match; 5 own container cleanups confirmed/absent.
Six diagnostic tests PASS/0.08s; docs/Ruff/read-only final receipt completion.json.
Only owned C:\pt\tmp\ce0913a was recycled after process completion: 128 files with
before/after hashes and exact restoration path in cleanup.json. Original candidate
workspaces remain in place. No Docker start/pull/build,
runtime/task/default edits, full-suite/mock rerun or new paid authorization.
Next decision: one generic public-requirement combination-check behavior experiment,
with independent evaluation before adoption; do not generalize this post-hoc panel.

Prior seam: native context A/B completed; exact four-row approval consumed.
Immutable design: `C:\pt\analyses\native-window-comparison-20260913\packet.json`, hash
`sha256:8f0160790dc5916f5b6f28b98a4170ee2683604d69ebcf422fda291b018dd808`.
Live evidence: `C:\pt\analyses\native-window-comparison-live-20260913`.
A1/B1/B2/A2 used append/window/window/append, fresh repeat1 rows, pyfakefs v2,
mini-2026-03-17/medium, root `.env`, probes/repair-recheck ON; $1.20 each/$4.80 total.
Both compact thresholds null, acknowledgement false; encrypted-v1 intact.
Unchanged v38 runtime/tool/default/task, 40/100/4/1800; all output ceilings 25k.

- A1 `run_dev_c2ec79e5f30648d4`: AGENT_STOPPED, acceptance/safety NOT_RUN;
  26 model/28 tools, 3 accepted/3 rejected mutations, 329.021s, $0.556358850.
- B1 `run_dev_e54abd76ccf54c4a`: EVALUATOR_PASS, acceptance/safety PASS;
  21/28, 4 accepted/0 rejected, 228.900s, $0.380706000, patch `4f56e7c2...`.
- B2 `run_dev_55e85c0941ed4081`: EVALUATOR_FAIL, acceptance FAIL/safety PASS;
  27/38, 4 accepted/3 rejected, 249.998s, $0.541517400, patch `9970b739...`.
- A2 `run_dev_8d592587618448b7`: EVALUATOR_FAIL, acceptance FAIL/safety PASS;
  22/23, 2 accepted/1 rejected, 193.030s, $0.369103950, patch `43fb9b2b...`.

96 generation/counts, 117 tools, nine repair-rechecks; probes NOT_EXERCISED,
compact DISABLED. Known model-rate total $1.847686200; count billing/invoice total
remain unverified. No retry/resume/extra sample/budget transfer/operator repair,
Docker start/pull/build or old-run mutation. Approval is closed, not reusable.
B has more submissions/acceptance, but only two rows per arm. The context policy
includes its WINDOW_INSTRUCTIONS and archive representation, with different
subsequent trajectories: no pure deletion-only effect or generalization claim.
Both arms used 48 model calls. B input tokens are 25.90% lower but known cost only
0.35% lower (A cached share 73.60%, B 59.10%); inspections A33/B41. Runtime
model_hash differs only because it binds policy; the actual model snapshot is equal.

Public-code observations: B1 processes all raw prefixes through existing mkdir;
A2 pre-creates only until the first `..`; B2 retains manual entry handling for `..`
paths while falling back for other paths. A1 stopped with public regression FAIL
and repeated 52/50 scope rejection. Do not map these observations to exact hidden
failures: private details were not read and no new candidate checks were run.
No submission means acceptance NOT_RUN, not hidden FAIL. All official/claim flags false.
A1/B1/B2 memory_update all null; A2 six updates, one created/updated finding
delivered on 17 turns. Invalid current_state citation was rejected nonblockingly.
Successful storage/delivery is not evidence of semantic correctness or memory benefit.

All 96 current-input/count/dispatch requests reconstruct from available prefixes;
native encrypted/call-output ordering and current task/diff match. Final submitted
patches match workspace and both current visible PASS records. Two read-only audits
agree (3.716853s/3.717737s), 5,483 protected hashes verify; 19 public check container
cleanups are confirmed/absent. Only aggregate private evaluator verdicts were read.
The auditor's initial compact-preparation-field assumption was corrected to the
disabled-compact turn_started/count path; this did not alter runtime/live evidence.
Operator stop-policy tests: 10 PASS/0.81s. Final docs/Ruff receipt: completion.json.
No full-suite/mock rerun for this unchanged runtime. Preserve the original design,
including its 31-case/12.474s receipt and frozen 101-column E501 warning.
Next decision: provider-free public-spec edge-case validation before one loop change;
no automatic window adoption, mandatory notes, new task or paid comparison.

Prior seam: v38 native-window pilot completed; exact approval consumed once.
Evidence: `C:\pt\analyses\native-compaction-pilot-live-20260913`.
Fresh `run_dev_ebfe33596eed4353`: EVALUATOR_PASS, acceptance/safety PASS, official=false;
19 model/19 count/20 tools/two accepted mutations, 121.047 active seconds, $0.19483845
known model-rate cost. Invoice/count billing are unverified, not promised free.
All generation ceilings stayed 25k. Peak input 45507 < 60000 means compact NOT_EXERCISED;
no native compact activation/recount or long-window prevention claim. No extra sample.
Fourteen inspections precede mutation15; check16 maps the intermediate-mode assertion;
mutation17 fixes parent-vs-leaf mode, harness recheck passes, regression18 passes
(517/570 skipped), finish19 binds the +23/-1 submission to both current visible PASSes.
All 19 model inputs replay exactly from public journal prefixes, with native pairs,
current task/diff and prior source facts intact. Nineteen memory updates are null.
Two read-only audits match (1.120s/1.019s); 81 artifacts, 5,061 prior protected files,
worktree/submission hash and three public container cleanup receipts verify.
Private artifacts are hash-checked, not parsed; only aggregate acceptance/safety is read.
The generic `.patchloop-hidden/**` forbidden-path glob is explicitly in public.yaml;
do not mistake that public restriction for leaked private test filenames/content.
Runtime/default/task unchanged. This single trajectory is not a causal A/B comparison.
Do not lower T, force compact, retry/resume or run another sample under this closed grant.

Consumed design (immutable):
`C:\pt\analyses\native-compaction-pilot-design-20260913\packet.json` byte hash:
`sha256:30bec892489cc9bd379f8dd6ec1e4101f7171b0c47d5ae264de44e3b408aedfc`.
One fresh pyfakefs v2/mini-2026-03-17/medium/root `.env`/repeat1 run under
`C:\patchloop-state`, probes and repair-recheck ON, native-window-v1, T=60000,
one compact maximum and conditional model-limit reservation acknowledgement.
The shared cap $2.00 (not $1.20) and conditional invoice boundary were approved for
this one run only. No default T/adoption or reusable paid authority follows.
Reuse existing run_dev; do not create a second runner. Prepare/verify scripts cannot
load credentials or invoke providers/count/Docker/task execution. Verify the frozen
packet hash twice, runtime/tool/model/task hashes, source cleanliness and credential
integrity, then perform read-only Docker/image/pricing checks only at approved admission.
One external admission record; no retry/resume/extra sample/answer seed/hidden feedback.
Native private evaluation after finish is aggregate-only and always official=false.

65 saved inputs replay with exact evidence/native order; 15 threshold/budget/guard
cases pass. Historical APPEND first 60k crossings are A1 turn15 64852, B1 turn17 61805,
B2 turn16 62141. At design time, new-window token counts/trigger timing were UNKNOWN;
do not scale tokens by serialized bytes or treat these as matched behavioral controls. T is a
round early pilot value, not a fitted optimum or encrypted-field safety boundary.
Below-threshold/ineligible paths remain NOT_EXERCISED without forcing a second run.
Report snapshot integrity, compaction/activation/recount, actual token/byte/field
growth, agent actions/submission and acceptance/safety as separate axes.
Two exact no-call verifications match (0.578s/0.559s); wrong packet hash rejects.
All 5,050 protected files remain unchanged, three docs tests/Ruff pass. No new full
runtime/mock claim: the phase-3 receipt below still binds the unchanged runtime.

Implemented runtime: v38 opt-in runner compaction (phase 3).
The default append wire remains unchanged. `native-window-v1` alone only expires
snapshots. Compact additionally requires positive `compact_at_input_tokens < 272000`,
the exact mini snapshot and `accept_compaction_model_limit_reservation=true`.
Bind T, maximum one request, acknowledgement and the reviewed cost/limit contract
into request/model/envelope identity. Do not choose a default T from prior counts.

`native_compaction.py` owns prepared-input/count and activation bindings, not a new
agent framework. A `model_input_prepared` boundary is NOT a model decision. Persist
exact input/state/schemas/request, current public cursor and request hash before
counting. Resume completed counts with that exact bundle; the final `turn_started`
selects its count ID. A healthy completed batch, no pending correction, input within
the reviewed limit, remaining model calls >= B+1, full remaining cost reserve and
active time are necessary for compact. Repair-recheck/pending action recovery run
first. Optional compaction unavailability alone never closes generation.

Compose the adapter's `*_locked` methods with the RUN-LIFETIME execution lock;
never reacquire it. Use an explicitly created owned bounded client only at admission.
Compact dispatch consumes one model call, no tool/mutation. Its separately durable
usage joins `provider_usage()` and the invocation ledger exactly once, including
usage-only failures. Active elapsed seconds include request/cleanup, not downtime.
Unknown count/provider/billing/cleanup stops without retry or a replacement request.

`CompactedWindow` keeps every returned item in exact order. Its semantic source index
is local lookup data, NOT another model message: each indexed fact is actually in
the seed or its missing-evidence archive. Rescue only absent public exchanges,
source bodies and observations; never manufacture native calls or observations.
Latest state explicitly contains the unchanged public_task; seed-era notes/PASS/
correction/tool lists are historical. The activation binds source input, preparation,
receipt, whole seed, base and consumed exchange. Skip that already-consumed exchange
once, then append future native reasoning/calls/results normally. Rebuild policy and
recount the full new request after activation; do not reuse its precursor count.

After compact, a fresh SYSTEM notice explicitly supersedes the old system's
no-compaction and initial-task inheritance descriptions. A developer-only reentry
would not resolve that priority conflict. Retain the old seed unchanged; supersede
its obsolete control description at the same instruction level, not by pruning it.
The authority regression is in `tests/test_dev_native_compaction.py`.

Started-without-response and usage-only compact crashes terminate. A complete receipt
before activation validates read-only before resume credentials/workspace; activation
and later generation boundaries are idempotent. Terminal resume stays read-only.
No encrypted-state reset, schema reordering, new terminal or journal migration.
Current verification: `C:\pt\validation\native-compact-runner-final-20260913` (provider-free).
44 new cases PASS/52.149s, 109 compatibility cases PASS/18.694s, Ruff PASS; all
91 files yield 1,803 PASS/four real-Docker skips, longest worker 384.729s. Full suite
exceeds two minutes; focused validation meets the target. Mock `run_dev_05c974e7447c4506`
reaches mutation/check/finish/isolated acceptance PASS in 4.468s, safety NOT_RUN/cost 0.
The ordinary mock does not call compact; injected-provider tests cover that branch.
Runtime `sha256:a6595319b770bc91e733e138273ee22de698a9fd707ce5543cfe06d0dd67d765`;
v38 surface `sha256:5393d4fb6eab34c4db114fcfa18187e332cd1daac6cb07967d31da9e93003979`.
The pilot above consumed its grant without exercising compact; no default adoption.

Prior layer: durable compact handoff, before native runner integration.
`patchloop/dev/compaction.py` implements prepare/execute/recover under the existing
run execution lock, at most one admitted request. Preparation has no client, and
execute requires an explicitly supplied owned zero-retry bounded client factory.
There is no default client, credential loader, CLI entry point, count/create call,
tool executor, scheduling threshold or window activation in this module.

`patchloop/agent/compaction.py` and `request_transport.py` hold shared validation
and bounded whole-body async transport; diagnostics retain compatibility exports.
`patchloop/dev/compaction_cost.py` preserves the reviewed 2026-09-12 mini contract
and $0.876 full-model-limit reservation; no new rates/model/endpoint cap are inferred.
Quote against remaining invocation budget, recheck before dispatch, and do not lower
the reserve or manufacture max_output_tokens/reasoning parameters. The handoff exports
known usage/cost but does not mutate the caller's ledger: the runner layer must settle
unique durable attempts once and count compact against the existing model budget.

Preparation binds source input/seed CAS, boundary, policy/runtime hashes, the full
cost contract and reservation. Output retains every validated provider item in order;
retained message role/text/multiplicity and exact actions must correspond to source.
Reject unsupported output as a whole, including unobserved plaintext messages and
reasoning summaries. Never log SDK serialization warnings or raw exception bodies.
Usage is separately durable before output serialization/validation/CAS writes.
Journal records hashes, numeric accounting and bounded failure labels, not ciphertext.

Use the caller's monotonic deadline, min(300s, remaining minus 5s cleanup reserve),
and only the owned client's bounded close. Store active elapsed independently of
process downtime. Late valid output/usage is preserved, not permission for more work;
cleanup uncertainty stops even with a valid window. Do not claim remote cancellation.
The atomic receipt binds source/policy, complete output/order, usage/cost, cleanup and
elapsed time. Receipt verification precedes any recovery write. A receipt before its
marker is finalized once; a durable validated-output event plus confirmed cleanup can
finish a missing receipt. Orphan CAS, started-only and usage-only states cannot supply
a window. Unknown outcomes never retry. Completed recovery is byte-idempotent, with
no client, count, task, clock reset or cost re-settlement. Source/receipt/CAS corruption
and runtime/policy mismatch reject without changing the journal.

Evidence: 60 adapter tests PASS/9.586s and 100 existing compact/transport tests
PASS/30.395s; `C:\pt\validation\native-compact-adapter-20260913`. All 90 files yield
1,759 PASS/four real-Docker opt-in skips, longest worker 362.932s; Ruff PASS. Mock
`run_dev_702e01bb86114453` reaches mutation/check/finish/isolated acceptance PASS in
4.628s, four mock turns/five tools, safety NOT_RUN and cost zero. A read-only check
of the saved actual compact response preserves all 23 items and 22 public messages.
v37 schema/tool policy and default append behavior stay exact.
That layer's next seam was phase 3 of [the plan](plans/native-context-window.md),
now covered above. Its saved evidence is unchanged; no paid grant follows.

Prior layer: first native-window layer in the
[implementation plan](plans/native-context-window.md) is implemented under v37.
Default append wire remains unchanged; policy is opt-in and envelope/model-bound.
65 saved native inputs replay with exact source facts, public observations, latest
state and native sequence. Last normal A1/B1/B2 input-array JSON bytes fall
33.67% / 36.77% / 31.69% after evidence rescue, not token or model-performance gains.
The giant B2 encrypted item remains exact. Replay takes 14.258s, with 4,571 prior
protected files unchanged; receipt is `C:\pt\validation\native-window-20260913`.
138 focused tests PASS/61.77s; all 89 full-suite files yield 1,699 PASS/four real-Docker
skips, longest worker 382.43s. Ruff passes. Opt-in CLI mock `run_dev_91de969f3e434039`
reaches isolated acceptance PASS/safety NOT_RUN, four turns/five tools/one edit in
4.73s; its saved window inputs revalidate. No real API/count/compact or Docker.
Only later work adds the durable compact adapter, healthy-boundary activation,
full-output seed, shared cost/deadline and recount. Model-limit reservation is not an
enforced invoice cap. No fitted cutoff, opaque reset, pending-call retry or old-run
migration. Trigger/reservation fields and paid/default adoption are not implemented
or authorized by the snapshot option.

Prior audit: native-input audit completed; no runtime change or execution grant.
`C:\pt\analyses\native-input-audit-20260913` reconstructs all A1/B1/B2 65 input/count
hashes and 64 generation admissions. Native source references differ from diagnostic
reentry expansion: superseded state removal upper bounds are A1 33.70%, B1 37.53%,
B2 pre-failure 31.47% of full compact-JSON bytes. Initial three items, latest full state,
source facts and native reasoning/call/output are exact. Omitted old state observation
versions are flagged, not proven lost facts: equivalent native output values were not
reconciled. Do not turn the sizing probe into a provider-ready prune implementation.

B2 turn20 -> turn21 adds 1,716,122 bytes, including one 1,701,293-byte reasoning item
(99.14%); its encrypted value is 1,701,176 characters and occurs once. Hash/order match
the durable continuation and previous count-only per-field rejection. Removing old
state leaves that value unchanged, so the direct rejection mechanism is not repaired.
Exact server threshold, modified-request admission and generation endpoint remain
untested. Native B1 continued at 101,831 input tokens, so do not infer a 97,810-token
failure threshold or a model-effect explanation from B2. No raw reasoning/ciphertext
or runnable rewritten request is published; private evaluator artifacts are not parsed.

Two guarded analyses agree/3.855761s; ten external fixtures and three docs checks
PASS/0.784s, Ruff PASS, 4,649 protected files unchanged. Native reconstruction files
match source 22798e34..., but full old runtime envelopes are not migrated. API/count/
credential/task/Docker/hidden calls zero; no native full suite or evaluator smoke.
Next design candidate: explicit native context-window lifecycle using the tested
healthy-checkpoint compact/full-window/public-reentry path. Preserve canonical compact
output, source references, harness receipts, correction consumption, budgets and exact
resume identity. No simple active-episode pruning, ciphertext reset, arbitrary length
cutoff, new paid sample or claim that preemptive compaction guarantees prevention.
Model/planning/memory/tool-mask changes are not supported by this byte audit.

Prior live: exact latest-state grant consumed; public submission, default unchanged.
Packet `429d4173349ac1306ef1bdcfc4889b75ae5ef4cfd03b4f933518416cb31d7a64`, plan
`0d45099f800d447291a8cd627e1be22907339ae92afa82670f29c50c632a787a` executed once
on 2026-09-13 KST. Collector `run_dev_compactcollectloop_ef29a44a32a64717`, child
`run_dev_compactepisode_999605443f744e56`: PUBLIC_CHECKS_SUBMITTED, not censored.
Eight counts/generations, eleven tools including saved seed and automatic rechecks,
two accepted repairs, 101.420s, generation $0.53881155 under $1.20. Separate count
billing/invoice remain unknown. Existing images only; six owned public container
cleanups confirmed, client CLOSED. No native row/resume/recompaction/retry/extra sample.

Two probes exposed bytes/str traversal mismatch. First repair used make_string_path
on string literals (which preserves str), then the automatic check failed at the same
site. Helper read -> matching_string(path, token) repair -> contract PASS -> requested
upstream regression PASS (517 passed/570 skipped) -> finish. Both PASS records and
submission share a54bfbd1..., one file/+33/-0/no untracked. Source checkpoint/final
artifact stay isolated; never apply this task-specific candidate to the task package.

Actual input counts 107319/111303/115395/120527/123219/129082/135028/138566.
Last complete request 566920 bytes, same-trajectory append reconstruction 1381335
(-58.959% bytes; the shadow was not dispatched/counted). Full seed, each native
continuation/call/output and latest complete state preserved; cumulative inventories
match at every turn (final 1279 source facts/28 exchange versions/33 observation
versions). Nineteen historical observation versions rescued; new memory_update all null.
Two readonly result inspections 0.167361s, two projection replays/inventory checks
0.492546s; protected 4218 and completed collection 234 files unchanged.

Collection: `C:\pt\analyses\compaction-snapshot-collection-20260913`; approval/audit:
`C:\pt\analyses\compaction-snapshot-live-20260913`. Native runtime/v36/default,
limits and task untouched; acceptance/safety NOT_RUN, official=false. Compare the
historical five-call/one-repair/$0.50483145 success only descriptively: actions/cache
hits differ and this is not a fresh control, cheaper run or quality/generalization
proof. Next interpret the bounded evidence, not automatic adoption or another paid
sample. Pending/terminal collection has no retry/resume grant; readonly result only.

Implemented: opt-in diagnostic snapshot lifecycle; native runtime unchanged.
`compaction_episode prepare --context-policy latest-state-v1` binds the mode and
`compaction_snapshot.py` bytes into the new packet/collector identity. Default is
`append-v1`; neither native state assembly nor tool-surface v36 changes. A new mode
is not permission to reuse an old execution packet or reset encrypted continuation.

Keep the whole seed window byte-equivalent and every subsequent native item in order.
Only our post-seed `diagnostic_compaction_reentry` snapshots expire. Before replacement,
retain missing public exchange versions, complete source lines (LF comparison, raw
file hash, no filled gaps), and public receipt values in historical evidence messages
at the old snapshot position. Existing archives remain immutable, exact versions are
deduplicated, and unknown public fields are retained conservatively. No filesystem
source lookup, summary model, new planning hints or lossy evidence cap is introduced.
The already bounded episode/global limits still bound this diagnostic.

The current reentry is unchanged and overrides historical evidence, including old
PASS/currency/failure fields. Do not inherit missing current fields, revive expired
notes or reissue consumed protocol correction. Gateway admission/current-source/notes
policy is untouched. Projection happens before the actual ordered input CAS, counting
and dispatch; turn_started binds lifecycle hashes/counts as well as exact wire input.
Recovery is deterministic reconstruction from that input, not a new paid resume path.
Interrupted/pending/terminal collection still stops without retry; old completed result
inspection continues to validate its saved contract, not the new implementation.

Provider-free historical replay agrees twice (0.653178s). Final complete request
948,877 -> 517,178 UTF-8 bytes (-45.5%); 942 source facts/22 public exchange versions,
latest complete state and seven rescued past observation versions preserved. This is
not a token, API-admission, behavioral or compaction-causality measurement. Receipts:
`C:\pt\validation\compactstate-20260913`; final 4,182 protected files match excluding
two diagnostic modules and the later-edited collector regression test (the initial
replay receipt verified 4,183 before that test edit). Native runtime unchanged. No API/count,
credentials, Docker, hidden evaluator or new execution grant in implementation validation.
The packet's later approved result is above; do not change the default loop from
structural tests or this one diagnostic trajectory.

Validation: 17 focused PASS/21.589s; 89 related regression PASS/123.997s (slightly
over the two-minute target); 4 final collector/docs PASS/6.424s, Ruff PASS. Total
110 test executions/107 distinct, process-time sum 152.010s, not elapsed wall time.
Injected collector proves packet-mode admission and counted/dispatched/CAS input
identity; mock/local repair reaches recheck and public finish. Native full suite and
isolated evaluator were not rerun for this diagnostic-only change. Dispose only the
four owned compactstate test roots after processes exit; preserve receipts separately.

Prior seam: provider-free reentry audit completed; native runtime unchanged.
Five requests grew 519,521 wire bytes, including 439,219 superseded post-seed state
bytes (84.5%), 47,564 encrypted-reasoning bytes and 26,755 native call/output bytes.
Each new reentry quoted 12/14/14/12/14 exact items already present earlier in input.
The diagnostic's one-shot public restoration (inline selected source plus transitive
quoted call/output archive) is appended every turn. This is snapshot/history lifetime
coupling, not measured proof of the same growth in the default reference-based loop.

In-memory removal of only post-seed superseded reentries yielded 948,877 -> 509,654
bytes at the final request (-46.3%), preserving full seed/native items, latest state,
942 observed source facts and 22 public action versions in this trace. No request
was published/dispatched/counted; API admissibility/token/model effects remain untested.
The opt-in implementation above follows that candidate, not a default adoption.
Never turn a sizing probe into blanket permission to discard old observations,
reset reasoning or run paid work.
Two guarded audits agree (0.662391s), seven synthetic checks PASS, 4,169 protected files
unchanged; `C:\pt\analyses\compaction-reentry-audit-20260913`. API/count/tools/Docker 0.

Prior live evidence: the exact `1f4b1ff0...` compacted short-episode grant is consumed.
`run_dev_compactcollectloop_770d791800604acd` / child
`run_dev_compactepisode_a24b09c546ff4deb` reached PUBLIC_CHECKS_SUBMITTED on
2026-09-13 KST. Five new responses/counts, seven tools including saved seed and
harness recheck, one accepted mutation, 91.483s, known generation cost $0.50483145
under $1.20. Separate count billing/invoice remain unknown. No native live row,
native resume, new compaction, Docker start/pull/build, retry or hidden evaluation.

Seed bytes-path failure -> search/read helper -> exclude final component from
precreation -> automatic opt-in contract recheck PASS -> requested upstream check
PASS (517/570 skipped) -> finish. Two PASS checks and submitted patch share
`43894e2c...`, one file/+33/-0/no untracked. Five input continuations retain the
full compacted prefix and append prior encrypted reasoning/call/output once;
reported reasoning context is current_turn, not evidence of effective model use.
All new memory_update values are null. Acceptance/safety NOT_RUN, official=false.

The completed audit above inspects repeated public reentry bodies. Actual
input grew 107,343 -> 137,253 -> 168,054 -> 202,832 -> 231,983 tokens; every turn
appended 93,518-106,658 characters while retaining older snapshots. The fifth
request kept five previous reentries/497,060 characters. Separate source/tool
evidence from repeated state descriptions before proposing one change. Do not
infer compaction causality from a single branch without a new control, remove
observations, reset encrypted state or turn this consumed grant into another run.
Native runtime/v36 and old packet/source bytes remain unchanged.

Collection: `C:\pt\analyses\compaction-episode-collection-20260913`; authorization,
result analysis and preservation receipts:
`C:\pt\analyses\compaction-episode-live-20260913`. Two read-only result inspections
agree (0.183008s); all 221 collection files and 3,937 protected predecessor files
remain unchanged. Client CLOSED/public containers cleanup confirmed. Collector
inspect/collect/result contracts are in operations; partial result inspection is
read-only and never a retry. Prior implementation tests remain 104/119.415s + Ruff
at `C:\pt\validation\compactcollect-20260913`, not new full-suite/hidden-evaluator evidence.

Prior implementation: provider-free compacted short-episode mechanics, not a live collector.
`diagnostics.compaction_episode` verifies the completed one-turn collection and
healthy pre-turn20 source, freezes an immutable packet, and exposes injected
initialize/execute_seed/step mechanics. CLI supports only prepare/verify. Do not
construct provider/Docker backends or infer a grant from the packet. Native runtime,
v36 tools, limits and default loop remain unchanged; old runs cannot be migrated.

Keep the complete compacted input prefix in its original order. Native history
restoration rejects compacted windows; use original observed public history only as
a local reconstruction index, never as a second native reasoning prefix on the wire.
Append the newest encrypted reasoning/calls/matching outputs and exact public reentry
through the existing public-source projection. No new source read or hidden evidence
is introduced by reconstruction. Store ordered input bytes and hash those same bytes.

Clone base+cutoff patch into new isolated state, hydrate unique event counters/notes
and checks, and execute the saved check at most once. Its previously billed response
consumes one inherited model step and 7.517505s active time, but no new cost. Reuse
the original repair_recheck option, native tool policy, corrections, gateway and
JIT full-25k reservation. Terminal/interrupted work is not retryable here; no native
resume contract is weakened. Deadline/cleanup failures retain native terminal classes
and bounded metadata survives expiry. No private evaluator is invoked at finish.

Packet `65e1ce83...` at `C:\pt\analyses\compaction-episode-design-20260912` is
PREPARED_NOT_EXECUTABLE, generation cap unset, max eight new responses. This is an
external observation bound, not a changed completion budget or action mask. Two
no-call verifications agree in 0.448505s; exact real-source hydration takes 3.989775s
and retains counters 19/20/2 plus existing PASS/NOT_RUN checks. Seed execution and
all actual API/Docker/evaluator work remain zero. 29 mock/local cases pass in 54.005s;
3,897 protected files and native runtime are unchanged. Receipts live under
`C:\pt\validation\compactloop-20260912`; local fixture success is not task success.
Related regression adds 188 PASS/51.188s: final tests total 217/105.193s, excluding
debugging runs. Ruff passes; native full suite/isolated evaluation were not rerun.

Next add a bounded collector with exact grant/cap, current prices/count-billing
disclosure, lifetime execution lock, client cleanup, partial receipts and preflight
of already-running Docker/exact images. No start/pull/build or paid work is authorized
by this implementation. Acceptance/safety remain NOT_RUN, official=false.

Prior diagnostic: one post-compaction response collected; the exact grant is consumed.
`run_dev_compactnext_822a9ab18f5f4ce3` used one count and one generation with frozen
`aa469bad...` inputs. Count/usage agree at 78,485 input tokens; output 117/reasoning 44,
completed, new encrypted reasoning 1,484 chars. It proposes the remaining registered
`parent-traversal-contract` check. The cutoff is needs_visible_checks, upstream
regression PASS and that contract NOT_RUN; the public decision matches this state.
No tool, Docker, hidden evaluation, correction, recompaction or retry occurred.
Generation tariff estimate $0.05939025, actual full-output reservation $0.17136375,
generation cap $1.20. Count billing remains separately UNCONFIRMED; invoice unknown.
Cleanup CLOSED, journal 7.517505s. Evidence and later separate authorization:
`C:\pt\analyses\compaction-followup-live-20260912`; immutable collection:
`C:\pt\analyses\compaction-followup-collection-20260912`.

Original turn20 exhausted 25k reasoning with no tool at 97,810 input; this sample uses
19.76% fewer input tokens and proposes a relevant action. Do not equate this with
check execution, full argument admission, task success or native-loop adoption.
Historical control is not a fresh replicate; compression, exact reentry and sampling
effects are not separated, and all 22 original messages remain. The oversized later
item was not the compaction input. Two preflight inspections match (0.142799s), two
result reads are byte-idempotent, and 3,879 protected files/runtime remain unchanged.
Next seam: review bounded actual-loop validation. No paid permission remains; no
automatic follow-up or migration of old receipts. Acceptance/safety NOT_RUN, official=false.

Prior implementation: post-compaction one-turn collector, provider-free preparation.
`diagnostics.compaction_followup` independently verifies the terminal, child receipt,
source reconstruction and CAS artifacts without source locks/writes. The exact
next count/generation artifacts, JSON member order, complete returned window and
public reentry remain unchanged. It reuses native parsing/continuation storage and
decision/batch validation, not the multi-cell sampler's scheduling or task executor.

Frozen proposal `aa469bad...` in `C:\pt\analyses\compaction-followup-design-20260912`
permits, only after exact separate approval, one count then at most one generation.
Same mini/medium/.env/repeat1/25k settings; proposed generation cap $1.20. Reserve
272k input +25k output at no-cache rates ($0.3165) before client setup, then recount
and reserve the actual request immediately before dispatch. Never lower 25k output
or reuse native/compact usage as the next request count. Count billing is explicitly
UNCONFIRMED outside the generation cap; separate acknowledgement is not a price or
an invoice-wide hard cap. Check official rates on execution day; no old grant reused.

30s count, 300s generation, 335s total including 5s cleanup. Store numeric usage before
parsing, metadata without raw provider error text, encrypted continuation and bounded
public tool proposals. Do not save plaintext reasoning/summary or assistant prose.
No tools, correction, recompaction, retries, Docker, hidden evaluator or paid resume.
`RESPONSE_COLLECTED` is not agent success. `PASS_SHAPE_ONLY` checks public decision,
allowed tool and batch form; full argument/schema and mutation/source/semantic
admission remain untested. Incomplete reasoning-only responses retain their error
and encrypted state without a correction call. Read-only result inspection verifies
terminal/CAS/continuation or returns conservative interrupted evidence.

188 focused cases PASS/40.79s; Ruff PASS; two real-packet no-call inspections equal
in 0.148343s. `C:\pt\validation\compactnext-20260912` preserves verification and 3,862
unchanged-file hashes. Native runtime/tool schema, source collection and prior frozen
packets are unchanged. No actual API/credential/tool/Docker work, native full suite
or task mock rerun at that preparation stage. Existing 22 retained messages are not
pruned; this diagnostic does not resolve historical-state interference, task correctness
or opaque semantic preservation. At preparation, follow-up admission and tool behavior
were untested; the later one-response result and narrower boundaries are recorded above.

Prior diagnostic: one standalone compaction completed; follow-up request artifacts only.
The separately approved `03b157e1...` plan completed in
`run_dev_compactcollect_5d1017bb7cf54445` with exactly one compact call, no count/create,
tool/Docker/hidden-evaluation work or retry. The grant is consumed. Read
`C:\pt\analyses\compaction-live-20260912\result.md` and `analysis.json`; preserve the
collection `C:\pt\analyses\compaction-collection-20260912` and old proposal bytes.

Usage: input 93,107/output 1,069, model-rate estimate $0.07464075, invoice unknown;
9.927731s journal duration, cleanup CLOSED. Reported use is within the conditional
reservation, not proof of an endpoint hard cap. Two read-only recoveries preserve all
collection bytes; source/runtime and 3,838 protected files are unchanged.

The original 19 reasoning items/133,464 encrypted characters become one 7,308-character
compaction item. All 22 original messages remain text-equivalent (20 developer, one
system, one user); this is not a current-state-only treatment. The returned window is
181,806 bytes, next generation request 315,757 versus 448,333 canonical bytes; reentry
keeps 319 selected public source lines and six referenced action pairs exact. Never
call these byte/character reductions a measured next-input-token reduction. All output
items, their order and the exact reentry are retained; generation settings unchanged.

The oversized 1,701,176-character turn20 response was not compacted. Next endpoint
admission, new reasoning size, useful tool behavior and hidden acceptance remain
unmeasured. Frozen next-generation hash `c1e2825b...`, count hash `d5716b19...` identify
artifacts, not authorization. Prepare separately bounded follow-up admission before
requesting a new grant. Do not silently prune returned messages, reset reasoning or
adopt compaction in the native loop. Every result remains official=false.

Prior implementation: one-compaction collector with explicit model-limit reservation.
`diagnostics/compaction_collector.py` consumes the unchanged `504756b2...` packet.
Inspect binds packet, source task/model/tier, credential path hash, new destination,
repeat=1, budget, cost contract and implementation hashes. Equal decimal cap notation
is normalized. Collect requires that exact inspection hash plus acknowledgement of
the conditional reservation, separate from user approval. No previous grant is reused.

`diagnostics/compaction_cost.py` uses official Responses model rates: 0.75/0.075/4.50
USD per million input/cached/output tokens. Reserve 400k input plus 128k output, $0.876,
without cache expectations. This deliberately reserves the full context window above
272k published max input. Applying model limits to compact is a planning assumption,
not an endpoint-specific output guarantee or server-enforced dollar cap. Retain that
qualification in plan, receipt and approval; never silently replace a strict hard cap.
The old native count and 25k generation ceiling are not compact input/output limits.
No count endpoint is called, so no free-counting assertion enters this contract.

One fresh directory and a run-lifetime lock own each collection. Before dispatch,
recompute the full reservation and bound request time by min(300s, remaining 305s minus
5s cleanup). Zero retries; only compact is reachable. Persist usage before validating
or storing the output window; a later output/receipt/publication failure must retain
valid observed usage. Save full valid window/next-input artifacts using the existing
handoff primitives. Numeric tariff accounting is not verified invoice billing.
Reasoning tokens are a subset of output, not an extra charge. Nonzero unpriced cache
writes, missing usage, violated reserved bounds, network uncertainty or cleanup failure
stop. Never automatically call count/create/tools, reset state or start Docker.

The parent collection journal and child handoff journal are distinct, preserving the
existing handoff contract. Receipt and terminal recovery executes no provider call.
A durable dispatch intent is not proof of HTTP execution after a crash: known call
attempts and admitted intents have separate fields; unknown request count is null.
Recover missing derived result.json from its terminal CAS artifact; reject changed
source/code for unfinished recovery and verify completed child receipts. Do not claim
remote cancellation or retry an interrupted collection under a new directory silently.

Provider-free evidence: 163 focused cases PASS/30.05s, Ruff PASS. Two exact real-packet
inspections agree in 0.094s. Proposed execution `03b157e1...` at
`C:\pt\analyses\compaction-execution-design-20260912` uses a $1.20 budget for one compact
request; the $0.876 reservation is conditional on published model limits, not an
endpoint guarantee. User has not accepted this assumption or granted execution yet.
`C:\pt\validation\compactcollector-20260912` preserves tests/inspection and 3,821
unchanged-file hashes. No credential/client/API/Docker/task work, default runtime
changes, full native suite or task mock rerun. Source packet bytes remain unchanged.

Prior implementation: standalone diagnostic compaction handoff; no live execution grant.
`diagnostics/compaction_replay.py` freezes B2's healthy pre-turn20 request, preserving
its original encrypted history and exact model/tool settings. It reuses the unchanged
count-replay reader and selected-source materializer. Do not feed back the original
oversized response, reset the reasoning state, add new observations, or modify default
runtime schemas to make this diagnostic run. Packet identity binds source journal,
envelope, cutoff, request/reentry artifacts and relevant implementation raw hashes.
Preparation/verification has no credential, client, task-workspace or execution path.

Use the standalone compact endpoint's entire returned window as canonical input,
including retained messages/reasoning/calls/results, without pruning or reordering.
Append the original coding instructions and a self-contained public reentry record:
exact public_task, latest state/diff/budgets/tools, inline *selected* observed source
ranges with raw-file hashes, and exact referenced public exchanges as quoted data.
Keep gaps, historical-check currency and native call/output identities. Resolve
backward references from public history only; missing promised deliveries fail.
No native history migration, new user boundary, planning requirement or evidence gain.

`diagnostics/compaction_state.py` provides reserve/record/recover primitives, not a
live collector. New external roots are exclusively claimed. A reservation is not cost
admission. Validate output before persisting; reject plaintext reasoning, unknown
items, missing ciphertext, changed/invented actions and incomplete retained pairs.
Do not salvage a window by stripping rejected items. SDK serialization warnings may
contain response text, so do not emit them; explicit validation remains authoritative.
Record numeric usage separately even when output fails; unknown price is null, not zero.

CAS stores the output and prepared next count/generation bodies; the journal stores
hashes, never ciphertext. The atomic receipt is the durable completion boundary.
Recover a receipt written before its journal event without another compact request.
An orphan CAS object or unfinished attempt is UNKNOWN, never retry permission. A
missing committed receipt or corrupt artifact is an integrity error. Run-lifetime
locking prevents concurrent record/recover. Completed recovery is byte-idempotent.
No tool executor is present, so retained functions and newly prepared requests do not
execute. Native resume and v36 remain unchanged. The diagnostic transport only adds
compact to its existing zero-retry, bounded whole-body wait/cleanup mechanism.

The official compact schema exposes usage but no reasoning-effort/max_output_tokens
parameters; do not invent them or call a next-generation 25k limit a compaction cap.
Standalone compaction is stateless; next generation stays store=false/medium/25k.
Before a future live collector, settle cost admission and obtain exact packet approval.
Compaction reduction and a valid next tool call remain untested live outcomes. Field
character counts, serialized bytes and rendered tokens are distinct; no numeric server
field limit is inferred. All results official=false, acceptance/safety NOT_RUN.

Evidence: `C:\pt\analyses\compaction-design-20260912`, packet `504756b2...`;
133 focused tests PASS in 23.69s and Ruff PASS. Two real-input no-call verifications
agree (0.264s including preparation), restoring 319 selected source lines and six
referenced action pairs. The 106,578-byte reentry is exact-state overhead, not actual
compaction output or token count. `C:\pt\validation\compaction-20260912` retains
reports and preservation hashes for 3,797 unchanged files. The old count packet still
verifies; native runtime is unchanged. No credentials/API/Docker/task execution or
full native/mock-task rerun. An initial new fixture omitted succeeded status and used
the wrong span-field notation; it was corrected without weakening source validation.

Prior diagnostic: approved count-only collection finished; its grant is consumed.
`C:\pt\analyses\count-replay-live-20260912` retains preflight, preservation and analysis;
collection `C:\pt\analyses\count-replay-collection-20260912`, diagnostic run
`run_dev_countcollect_82df89236b5c4404`. Control turn20 counts 97,810, matching history.
Turn21 returns HTTP 400 `string_above_max_length`, param `input[79].encrypted_content`.
The actual failed HTTP body hash equals the frozen canonical hash; 2,164,348 bytes.
Exactly two count requests in 2.811447s, zero generation/tools/Docker/hidden evaluation,
no retries/resume and cleanup CLOSED. Billing is still UNCONFIRMED/null, not proven free.

The rejected encrypted item is 1,701,176 characters, identical to the single-item
continuation recorded after original turn20, and occurs once in the request. Original
turn20 input remains an exact prefix. Its response was incomplete/max_output_tokens,
25k output/reasoning tokens, no tools. This narrows the observed failure to a per-field
string limit; it is not a recovered historical error body, known numeric server cap,
proof about responses.create, or explanation of why the provider inflated the opaque
state. Do not truncate, splice, reset or decrypt it as an unapproved workaround.

3,784 protected file hashes and native runtime are unchanged. All results official=false,
task acceptance/safety NOT_RUN. Next seam: offline continuation size/admission and
documented compaction review. A guard can diagnose an oversized item but cannot by
itself restore a valid continuation; do not claim a task-solving fix from this replay.

Prior implementation: standalone count-only collector; no live execution at that stage.
`diagnostics/count_collector.py` consumes the unchanged frozen packet below. Exact
packet/source/reconstruction and credential path validation precede key/client setup.
An explicit acknowledgement of unconfirmed count billing is required in addition to
fresh exact approval; the old packet's disabled-live flag is not a transferable grant.
The acknowledgement is not an official pricing statement or enforceable dollar cap.
Native admission/billing rules are unchanged. Never infer zero cost from missing usage.

An atomic new-directory claim prevents concurrent reuse and retry of the same
invocation. Durable `input_count_started` precedes dispatch; outcomes retain safe
allowlisted error fields, never exception messages, raw bodies, headers or ciphertext.
Pending after a crash means UNKNOWN; no resume/retry path exists. The pure reducer
allows case 2 only after the 97,810-token control. Client/setup, count, persistence or
cleanup failure never unlocks another request. Preserve received counts even when the
post-response deadline check stops further work. A terminal result artifact survives
failure to publish the derived result.json; recorded source state is never modified.

Reuse `episode_requests.DiagnosticClient`: official endpoint, trust_env=false, zero
SDK retries, outer whole-request cancellation plus per-I/O timeouts. Count limits are
30s/request, 65s total active execution including 5s cleanup reserve. Recheck remaining
time after admission fsync. Cleanup timeout/uncertainty is explicit; never claim remote
or OS-thread termination. A future invocation records collector and transport hashes
in its own dev-run-v1 journal. Only count calls are reachable, never generation,
tools, task workspaces, Docker or evaluators. Default runtime and v36 are unchanged.

Collector validation: 32 focused new cases; 159 combined count/transport/sampler/docs
cases PASS in 65.77s, Ruff PASS. Two read-only admissions of the real frozen packet
agree in 0.547s and 3,776 protected file hashes are unchanged. Receipts under
`C:\pt\validation\countcollector-20260912` and `countcollector-focus-0912a.xml`.
No real credential/count/generation/task/Docker action; full runtime suite and mock
task smoke were not rerun for this diagnostic-only seam. Original rejection remains
UNRESOLVED. Initial new-test socket guard incorrectly blocked Windows asyncio's
internal socketpair; restricting that guard to real HTTP transports fixed the tests
without weakening the production transport. Do not misclassify that fixture failure
as a reproduced provider rejection.

Prior preparation: standalone frozen count-only design, no live entry point at that stage.
`diagnostics/count_replay.py` reconstructs frozen B2 turns 20/21 using the saved
public input/context, native call/output order and registered schemas. Original
generation-request and count-body hashes must match before preparation. A harness
check is not a synthetic native call. Preserve empty reasoning summary arrays as
wire structure; reject nonempty summaries/plaintext rather than stripping and
silently changing the request. Context identity hashes artifact bytes, while model
input identity uses canonical JSON. Do not read unobserved source or private files.

The new external packet at `C:\pt\analyses\count-replay-design-20260912` binds
source journal/envelope, cutoff hashes, request artifacts and reconstruction
implementation identity. Prepare requires a new root outside repo/source state.
Verify is read-only; two repetitions must agree exactly. The pure protocol reducer
permits a second count only after the control returns its historical 97,810 tokens;
an error, unfinished attempt or changed count ends the sequence. Maximum two counts,
one attempt per case, no generation/tools/Docker/private evaluation or source resume.
Both succeeding means NOT_REPRODUCED, not proven transient cause or safe-size evidence.

At that stage only preparation and mock scheduling existed, not an executable live client.
Count-only billing remains UNCONFIRMED after reviewing the official counting guide
and pricing page; do not assume free, infer it from generation rates or reuse the old
comparison grant. Resolve the billing/cap contract and obtain exact packet approval
before a separately scoped collector. Runtime, task, v36, model/output settings,
continuation and default repair-recheck behavior remain unchanged.
Packet `f8342755...`: two identical no-call verifications, 0.443s preparation/rehearsal,
3,759 protected files unchanged. Count/diagnostic/sampler/docs focused regression:
112 PASS/50.68s; Ruff PASS. No new full runtime suite or smoke for this diagnostic-only
seam. Receipts: `C:\pt\validation\countreplay-20260912` and
`C:\pt\validation\countreplay-focus-0912a.xml`. Keep prior runtime test results dated.

Prior implementation: operator-only input-count diagnostics and failure recovery.
`agent/count_diagnostics.py` measures the actual count-payload fields in canonical
UTF-8; its hash/size is not claimed to be the wire representation. On SDK errors,
already-buffered HTTP request body size/hash is recorded separately, without reading
streams. Retain only status, finite allowlisted error code/type, structural parameter
paths and validated request IDs; redact other field values. Never stringify/store
exception messages, response bodies, authorization headers, prompts or ciphertext.

`input_count_started` binds request metadata to count ID/turn ID/request hash.
`input_count_failed` fsyncs the bounded outcome before terminal; duplicate identical
failure receipts replay, conflicts reject. COUNT_TIMEOUT_OR_UNKNOWN terminal and
operator public result expose `input_count_failure`, not agent context. An admitted
count with no durable outcome is interrupted/unknown, not a proven HTTP error.
Exact-envelope resume handles either case before credential/workspace/client setup,
with no recount or next provider request. Durable provider/billing uncertainty still
has priority; terminal resume returns the recorded result unchanged. Do not migrate
old envelopes or old terminal evidence. No model/tool/schema/action-mask changes:
v36 stays unchanged while runtime content identity changes.

Local SDK MockTransport plus fault injection verifies the privacy and stop boundaries;
42 focused tests PASS in 37.78s, Ruff PASS. All 80 test files, partitioned exactly once,
pass 1,448 cases with four real-Docker skips in 325.65/320.84/316.56/317.31s. One existing
JUnit record-property warning remains; do not claim a two-minute full cycle. Mock
`run_dev_0bd40e245b0742ee` at `C:\pt\validation\countdiag-smoke-0912a` completes
edit/check/finish/isolated evaluation in 3.889s, four model turns/five tools, zero count
calls/cost, acceptance PASS, safety NOT_RUN, official=false. Read-only frozen B2 count bodies
reproduce the original request hashes and measure 448,226 / 2,164,348 canonical UTF-8
bytes. This is not actual wire capture, token counting, a server size limit, or a
recovered rejection reason. Receipts: `C:\pt\validation\countdiag-20260912` and
`C:\pt\validation\countdiag-focus-0912a.xml`. 3,704 previously protected files (the two
edited runtime files excluded) and all 30 sealed comparison files verify unchanged.
No live paid/count call, Docker operation or pyfakefs execution. Comparison grant remains
closed; choose an exact separately authorized next experiment, not retry or reset.

Prior comparison: the approved comparison stopped on B2 COUNT_TIMEOUT_OR_UNKNOWN.
Evidence: `C:\pt\analyses\repair-recheck-comparison-live-20260912b`
(`result.md`, `analysis.json`, `failure-analysis.json`, observer). A1 OFF
`run_dev_2d9ac37041ae4c28`: public PASS/private aggregate FAIL, $0.334105050.
B1 ON `run_dev_1cd3d953c69240e7`: task acceptance/safety PASS, $0.333564450.
B2 ON `run_dev_03b4fcac720b4760`: unsubmitted, $0.484494900; A2 OFF NOT_RUN.
Total $1.152164400, 64 model/65 count/72 tool calls, no retry/resume/replacement.
All 3,706 protected files, prior Docker preflight-stop record and old native runs
remain unchanged. Current native runtime/task unchanged, official=false.

B2 repaired seven public regression failures and its harness child returned PASS
before turn20. The other contract check remained NOT_RUN on the new diff. Read,
search, check and mutation remained available, with 21 model/80 tool/two mutation
budget remaining. Turn20 used 25k reasoning tokens without a call; turn21 preserved
the 1,701,176-character encrypted item and all native pairs, but count failed with
BadRequestError. No paid model request21. Exact server error body/code/parameter
was not retained: do not assert timeout, a specific size limit or a proven cause.
This motivated safe typed count-error evidence and offline shape/size validation,
not ciphertext truncation/reset or extra live sampling. New paid work needs authority.

The immutable four-run native comparison design remains at
`C:\pt\analyses\repair-recheck-comparison-20260912`; packet hash `af29b90f...`.
Its exact $4.80 scope was approved and is now closed. OFF/ON/ON/OFF, same runtime v36/
`28f08d7c...`, task v2, mini snapshot/medium/.env/probes, each repeat1/$1.20, total
$4.80 with no budget transfer. Keep 40/100/4/1,800 and native output admission.
Previous rows are context only, never substitute controls or answer seeds. The option
also adds its initial context notice, so this is not a timing-only intervention.
Initial-context equality excluding that notice and packet/model/cap binding pass;
21 existing focused/docs tests plus two design cases complete in about 70s.

Use the unchanged native run entry per cell only after exact packet approval; bind
each admission once in a separate observer. Verify terminal/cost/cleanup before the
next row. Infrastructure/transport/billing/continuation or safety uncertainty ends
the comparison; preserve partial results, no resume/retry/replacement. Native private
evaluation follows ordinary finish; read aggregate verdicts only. Include no-child
and non-submission rows with NOT_EXERCISED/NOT_RUN labels, not selected-success bias.
No implementation/default adoption or generalization claim follows from this design.

Prior single-row result: separately approved fresh mini `run_dev_d484ea8a2a8e4ba4` completes
with EVALUATOR_PASS, task acceptance/safety PASS, official=false. Its exact v2/mini
snapshot/medium/.env/repeat1/$1.20/probes/repair-recheck invocation is consumed.
Evidence: `C:\pt\analyses\repair-recheck-live-20260912` (`result.md`, `analysis.json`).
Runtime `28f08d7c...`, v36, default-off option and native limits remain unchanged.
15 model/count calls, 16 tools, two edits, $0.208261650/163.312s; final +18/-1 patch
passes both public checks and isolated task acceptance. Regression 517 passed/570
skipped; private details remain uninspected and never enter the agent context.

Turns1-10 contain nine source inspections and one real-OS probe. Turn11 chooses a
recursive raw-path repair; turn12 exposes the public intermediate-mode assertion.
Turn13 correctly replaces recursive `mode` with `PERM_DEF`; the harness child reruns
that failure and supplies current PASS before turn14. The agent runs the remaining
regression then finishes at turn15. One child, no additional provider/count call,
no fabricated native function call, exact checked/worktree/submission hash. Fifteen
canonical requests/continuations, 14 replay deliveries, 51 artifacts and 3,645 protected
files verify. All optional notes are null; native evidence and continuation are not.

This is one live success and a feedback-delivery observation, not feature causality:
the improved initial algorithm and correct repair both occur before the child. No
default adoption, memory mandate, success-rate or generalization claim follows.
This single-row result motivated the subsequently admitted comparison above, which
did not complete. No further paid invocation, Docker start/pull/build, task alteration
or historical update is authorized; prioritize the current evidence-visibility seam.

Prior implementation: v36 focused tests cover current-failure selection, fresh verdict
before inference, exact option/envelope matching, counters and six crash boundaries.
Keep these local reliability tests distinct from the subsequent live observations.

Prior result: the separately approved frozen-third-candidate public check is complete
at `C:\pt\evaluations\mini-third-candidate-20260912` (`result.md`). Restore the exact
30-line `7c97d024...` candidate from native turn23 context/turn22 admission, never
the source final worktree. Both declared checks ran once on a no-hardlink base clone:
contract FAIL at line23/mode (same as saved fourth-candidate result); upstream
regression 6 failed/511 passed/570 skipped. Verified public control flow establishes
the earlier bytes example already works before edit4; not all bytes paths or whole
candidate correctness. Additional public failures concern parent-file errno and
broken symlinks/trailing separators. No fourth-candidate or baseline rerun occurred.

13.189s total, 1.176s/10.604s check durations, zero provider/count/model cost. Exact
diff/postimage/scope/policy and 3,388 protected files verify; owned containers absent.
No candidate repair, source resume, private evaluator/details, Docker start/pull/build,
runtime/task change or retry. Task acceptance/safety NOT_RUN, official=false. Preserve
the original source NOT_RUN/terminal; these are later operator-only observations.
This motivated an opt-in successful-repair plus prior-failed-check
feedback transaction, preserving native action/time/replay boundaries. Do not assume
it makes semantic repairs correct or add mandatory notes/extra action masks. This
completed two-check grant did not authorize implementation or another paid run;
the implementation above is a separately requested follow-up.

Prior run: the exact fresh-start native mini grant is consumed by
`run_dev_91384f8a97354835` at `C:\patchloop-state`; approval and public analysis are
at `C:\pt\analyses\mini-fresh-start-20260912` (`result.md`, `analysis.json`). No
checkpoint, answer patch or private feedback was seeded. Runtime a3d7f3c0/v35,
v2 task, mini snapshot/medium/25k, .env, repeat1, probes, $1.20 and 40/100/4/1,800
remain unchanged. 27 responses/counts/tools, four accepted edits, three failed public
checks, $0.441195300/220.438s end in LIMIT_REACHED: accepted_mutations is the only
blocker, despite 13 model/73 tool calls left. Final diff +31/-1 fits scope; public
mode assertion fails because prefix creation still uses the leaf mode. No submission,
regression/hidden evaluation, probe, retry/resume or Docker start/pull/build occurred.

Third edit's new post-image, historical TypeError, current NOT_RUN and explicit
pending-recheck guidance reach turns23-26. The model nonetheless claims the bytes
repair was insufficient and spends its final edit before any check/probe. The later
public-only check above resolves that bytes question, not overall candidate PASS.
Do not call this lost feedback. Check/probe/read/search
remain available all 27 turns. Four proposed note updates produce one retained note
(first invalid tool-result citation rejected without blocking); delivery/rebinding
verify, but notes are not updated after failures. No forced-note/plan conclusion.

27 canonical request hashes/continuations, 26 replay deliveries, 81 artifacts and
3,231 protected files verify; exact check containers are absent. Peak input/output
122,330/6,939 are below limits. No incomplete/protocol/transport uncertainty. The
subsequent third-candidate check and separately approved repair/recheck-loop observation
are above. Do not repair/rerun frozen patches or launch a paid row automatically.
No runtime/task changes; task acceptance/safety NOT_RUN, official=false, no claim.

Prior result: the separately approved independent evaluation of the two frozen mini
submissions is complete at `C:\pt\evaluations\pl43-mini-recovery-v1` (`result.md`).
C1/A/1's unchanged 49-line patch passes task acceptance; C1/A/2's unchanged 28-line
patch fails it. Both public regression, scope and typed evaluation safety PASS.
The two evaluator invocations take 8.518s/8.356s; no execution error, provider/count/
new-probe call, patch repair, agent resume, Docker start/pull/build or retry occurred.
Both exact artifact/manifest/policy chains and 2,845 protected files verify; owned
containers are absent. Preserve original diagnostic NOT_RUN/terminal bytes.

Only aggregate private verdicts are returned to the operator. Do not inspect private
failure details or claim the earlier public receiver-risk finding caused this failure.
The schema-required model field is unused operator metadata, not a mock task result;
real Docker evaluation ran. Safety covers these evaluations, not the full source loop.
One checkpoint-produced mini patch is independently accepted. The separately approved
fresh-start reproduction is recorded above; reliability, model success rates and
generalization remain unestablished. No answer-patch/private-feedback seeds were used.
No new paid work or loop change is authorized; official=false/claim_eligible=false.

Prior diagnostic: the exact `mini-recovery-budget-v1` grant is consumed. Collection
`run_dev_episode_collection_a78ccd1085a8478b` at
`C:\pt\analyses\pl43-mini-recovery-live-v1` completed eight episodes, 76 responses
and count calls, 83 tools, $2.55174405 / $5 in 994.987s, fully known cost. No unknown
dispatch, incomplete response, protocol error or diagnostic censoring occurred.
Read `C:\pt\analyses\pl43-mini-recovery-assessment-v1\analysis.md` and its sealed
blind observations/quantitative/mechanism audits before proposing a next change.
Default runtime, tool surface v35, model/context/notes and task packages are unchanged.

C1 historical A submitted 2/2; initial-current B 0/2. C2 both 0/2, starting with
only one accepted mutation remaining. Both submissions followed real repair/recheck
at responses 13 and 11. All six failures exhausted accepted mutations, not tokens
or request time. Do not infer that removing history helps, mini cannot recover,
an eight-response cutoff proves failure, or absent new notes proves absent planning.
In one failed branch the exact request already delivers the corrected receiver and
marks old failures historical with pending-recheck guidance. Its subsequent public
decision misuses that evidence. Preserve this counterexample to a missing-feedback
diagnosis. A residual unexecuted receiver risk in one passing candidate is a code
observation, not a new check failure or hidden result. Hidden/task acceptance and
safety remain NOT_RUN; official=false. Further implementation/evaluation requires
a separate decision; no automatic paid sample, retry, resume or default-loop change.

This fixed profile selects A/B mini cells only, two checkpoints x two repetitions,
in pair order C1/1 AB, C2/1 BA, C1/2 BA, C2/2 AB. It has no independent eight-response
cutoff, but inherits native budgets/gates, including C1's 27 model/87 tool/4 mutation
and C2's 20 model/80 tool/1 mutation remainder. Do not reset counters, enlarge native
limits or read new initial source. `factorial-eight-v1` remains the default four-arm,
eight-response diagnostic. Preparation binds the profile, exact selected requests,
balanced groups and response maximum; collector recomputes these before credential
access. `max_responses=null` means native-budget-bounded, not unlimited execution.

The new mini packet hash is
`sha256:ce3e9de64c93c324fa78ef2132b7f569be924c6fcb9db0511faa712f9016a976`;
implementation-set hash is
`sha256:00c10b9b1d209bc93a23f31b33983d5abb9812af75d8397fc7bb30f5f090cf93`.
Consumed contract: mini snapshot `gpt-5.4-mini-2026-03-17`, medium, 25k, root `.env`, shared
$5/1,800s, count30s/response300s, no retry/resume. Maximum responses/counts188 is a
native resource ceiling, not a promised sample size. Full A/B depth reservation
is $0.633, with no cache discount, before per-request JIT counting. Execution used
already-running Docker and pinned check/probe images, with no start/pull/build,
hidden evaluator, paid judge or automatic candidate checking by the assessor.

Only inherited pre-checkpoint state differs; all new native state/result/reasoning
history accumulates in both arms. The eight first requests exactly match the earlier
instruction-repaired preparation. Two identical no-call rehearsals restore all four
distinct case/arm checkpoints in 10.377s; 1,366 protected files are unchanged. The
response8-failure/response9-repair/recheck/finish mock and native horizon stop pass.
188 related tests pass in groups under two minutes (30/105.92s, 27/106.79s, 131/89.04s),
plus Ruff; not a full suite or a two-minute aggregate. Separate default smoke
`run_dev_21fe1d793876457e` reaches isolated evaluator PASS, safety NOT_RUN, zero cost.
No provider/count API, real task check or Docker execution ran for this preparation.

Anonymous public code observations were sealed before joining conditions/tokens/costs.
Report recovery and final-diff checks separately from inspection and diagnostic
censoring; missing cells are not failures. This does not isolate instruction repair,
test native continuation reset, establish a model effect or prove missing planning.
Any default-loop implementation or additional paid work needs a separate decision.

The mini public decision trace is complete at
`C:\pt\analyses\pl43-mini-decision-trace-v1`. Sixteen exact requests and continuations,
14 follow-up histories and seven executable observation groups verify: the public
task/source were delivered, new notes/concerns remained empty without rejected
updates, six tools stayed open, and both eight-response windows ended during real
recovery. Historical mini repaired ancestor mode immediately; its final diff was
not retested. Current mini searched for the helper owner after calling a backend
method on the wrapper's `self`. An unanswered Windows `isabs` implementation query
is a public tracking-gap example, not the cause established for that exception.
Do not infer absent internal planning, broken feedback or inability to recover.

The **diagnostic instruction repair is implemented**, not a default-loop change.
`model_state_episode.episode_request` replaces only the unsent snapshot notice with
the native conversation instructions plus archive lookup guidance. First-request
top-level state applies until a later `harness_current_state.state`; only the public
task is inherited as current authority. Initial archive/source_bodies remain quoted
checkpoint evidence. New native outputs and latest current_sources determine source
currency, including verified backward references into the archive. Never rewrite
sent messages, the one-response sampler, tool/property order or encrypted replay.

Preparation schema v2 binds `input_contract_hash`, original `source_request_hash`,
new `request_hash` and ordered wire hash. The collector recomputes the exact transformed
request and rejects old/mismatched preparations before task/credential access. Do not
migrate or resume old diagnostic packets; read-only saved-input hydration tests are
not a new resume entrypoint. No plan/note requirement or solution hint is introduced.

At `C:\pt\analyses\pl43-episode-instructions-v1`, all 16 starting cells and 16 saved
mini inputs preserve exact public information under the instruction-only change;
14 saved follow-ups still resolve current sources. 1,367 protected files outside the
two changed diagnostic modules retain their hashes. Related validation passes:
19 focused/63.384s, 25 collector/117.263s, 76 reused cases/17.757s and Ruff. Do not
claim a full-runtime rerun or a two-minute aggregate. Diagnostic mock reaches checks
and finish; separate default mock `run_dev_e680c529bc3849cb` reaches isolated evaluator
PASS, safety NOT_RUN, official=false, under `C:\pt\smoke\pl43-episode-instructions-v1`.
No provider/count call, real Docker or pyfakefs evaluator was executed.

The separate **diagnostic request-wait repair is implemented** in
`diagnostics/episode_requests.py` and the short-episode collector. Count waits are
30s, response waits 300s, both clipped to the current execution deadline. The async
SDK facade uses a whole-request timer in addition to per-I/O timeout, zero retries
and `trust_env=false`. Cancellation finishes before returning to the scheduler;
there is no provider worker or new resume path. Parsing is local and a late
response cannot execute tools. Client cleanup has a separate bounded 5s per owned
client, before the existing 10s read-only metadata tail; no further task runs there.
Close the owned loop without a default-executor join that could delay failure
receipts. An OS DNS lookup can outlive cancellation but cannot re-enter that loop;
do not claim hard process/OS-thread termination or remote request cancellation.

New exact packets/envelopes bind `episode-request-waits-v1` and implementation bytes.
Old packets/runs are never migrated. Existing sampler/default-agent wire inputs,
model settings, tool order, public evidence, notes and encrypted replay are unchanged.
`diagnostic_response_received` precedes parsing; `diagnostic_request_failed` records
fixed phase/error labels, elapsed/effective wait and request identities, not exception
messages, headers, response bodies or reasoning summaries. Read-only inspect returns
durable failures and the last recorded phase of pending attempts; that phase is not
a diagnosis of the remote cause. Verified usage survives action parsing failure.
Late parsed decision/continuation artifacts survive without a tool batch. Unknown
count/provider state retains its terminal priority; local timeout/cancellation never
proves that a remote charge did not occur. No automatic retry, paid judge or hidden
evaluator. Cleanup outcomes are recorded before terminal finalization.

Receipts: `C:\pt\analyses\pl43-request-waits-v1`. No provider/count or Docker execution
is part of this fix. The next packet is specified above but remains unapproved;
it is not another default-agent feature or a claim of improved mini performance.
Validation covers 192 distinct related cases plus Ruff: focused 32/73.97s, final
collector 27/112.58s, shared regression 131/108.72s and boundary/docs 18/11.35s
(overlapping counts). The first collector group took 127.36s; redundant repetition
in its lock test was removed, retaining the independent 16-window schedule test.
Do not claim a two-minute aggregate or full-runtime rerun. Default mock
`run_dev_ce016b90431140df` reaches isolated evaluation at zero cost, safety NOT_RUN,
official=false. Saved first inputs (16) and protected files (1,366) are unchanged.

The trace bound 1,369 unchanged files and executed no provider/count call, task,
Docker or hidden evaluator. Input-size growth is measured, not attention-loss
proof. Retain public-only analysis artifacts and original runs as immutable evidence.
Any future experiment needs a new packet and exact approval; both grants are consumed.

The preceding result is the completed **partial** short-episode invocation. Run
`run_dev_episode_collection_dd2a43b37b8d406c` at
`C:\pt\analyses\pl43-short-episode-live-v1` ended `PROVIDER_TIMEOUT_OR_UNKNOWN` on
2026-09-11: 29 dispatches, 28 completed responses, 31 actions, 1,801.237s including
read-only finalization. Known completed cost is $1.420476; one additional charge
is unknown. No retry/resume or replacement root is authorized. The grant is consumed.

After blind observation sealing, C1/repeat1 maps to mini historical/current: two
eight-response censored recovery windows; GPT-5.4 historical/current: same-hash
public checks and finish in four/six responses. Mini historical made a real mode
repair at response eight; its final candidate was not tested. Mini current hit a
wrong-receiver missing helper and searched to recover. Do not convert censoring
to incapability. C2 has one D and one B inspection response, a C dispatch without
response/usage, and no A dispatch; all C2 check statuses are inherited. Repetition
two never started. No hidden acceptance, replicated model/context effect or
default model/prompt/policy/memory change follows from this partial evidence.

Audit at `C:\pt\analyses\pl43-short-episode-assessment-v1` verified 29 wire/canonical
requests, 28 encrypted artifacts, 22 follow-up replay orders, six new public
check-policy/diff bindings and two submissions. Optional new note proposals: zero;
inherited notes/native history remain. Last dispatch occupied about 22m26s; no
response means no token-exhaustion diagnosis. The collector used for that run did
not retain a safe error type/phase. Bounded request waits and sanitized failure-phase
receipts have since been implemented as described above; they do not recover the
missing old response or resolve its billing. Preserve all source/new journals and
candidate bytes.

The exact-grant short-episode collector is in
`diagnostics/model_state_episode_collector.py`. Only `collect` may access credentials
or preflight already-running Docker/images; `prepare`, `validate` and `inspect` are
strictly provider-free. Default runtime/tool surface v35 and task packages stay frozen.
The executed packet is `C:\pt\analyses\pl43-short-episode-execution-v2\packet.json`,
`sha256:422ea586587c7a059fd48c65f6fcc9530c41874eb776f4594c5c944cce2a6776`, binding
implementation-set `sha256:df64112be339bb3c00c699446c1a4cb6c0c8e4b8e86899986168bb809fbe9939`.
It bound one $5 invocation at `C:\pt\analyses\pl43-short-episode-live-v1` using root
`.env`, not a reusable grant. Both previous and current paid grants are consumed.
Any further approval must match a new packet, implementation, prices, cap,
credential and fresh output path; never reuse this occupied result root.
Recheck official prices on the execution UTC date. No automatic retry/resume,
replacement root/model, Docker start/pull/build, hidden evaluator or paid judge.

Before any credential access, revalidate packet/source/task/runtime/code hashes and
atomically claim the fresh result root. Record the envelope, then hold invocation
and branch locks throughout execution. Register each branch before cloning so even
partial initialization remains inspectable. One shared 1,800-second deadline also
bounds cloning; each branch retains its inherited active budget. Reserve every
active arm at each depth with 272k input/full 25k output, then count each exact
request immediately before dispatch. The four-arm reservation is $2.743; $5 cannot
guarantee all 16 windows or 128 maximum responses. Do not lower outputs, skip to
cheaper groups, retry uncertainty or interpret censoring as agent failure.

Collect exact native public action/result and candidate receipts before blind review;
condition mapping remains separately journaled. Read-only inspection derives counts
and known usage from non-inherited events, with provider/count uncertainty taking
precedence over interruption/deadline. Finalization permits only ten seconds of
read-only Git metadata after execution stops, without resetting the gateway deadline.
Missing/drifted candidates mark partial review evidence, never an invented PASS binding.
Checks/probes/finish are model-requested; no automatic evaluation is added. Test errors
are not serialized verbatim. Preparation/validation must not read credential values.

Twenty-two new collector tests pass in 110.02s, including public local mock
mutation/check/finish, uncertainty, concurrent entry, deadline and crash inspection.
Both real source checkpoints and all 16 first requests validate without network,
tools, credentials or Docker. New receipts are at
`C:\pt\validation\pl43-episode-collector`. Related totals are 166 passing cases:
22 collector, 45 episode/factorial/review (126.96s), 96 reused engine/sampler
(116.24s), three docs (0.05s), plus Ruff. The 45-case group exceeded two minutes;
do not claim a full runtime suite or a two-minute whole cycle. Anonymous receipts
pair exact public decision arguments and action results. The earlier unapproved
execution-v1 packet is preserved, superseded and incompatible with the final code.
Eight owned scratch roots were recycled with full content identity and restoration
records. All 1,298 protected files and source/user file hashes are unchanged.
Those tests are implementation evidence, distinct from the partial paid result
above and not a quality claim.

The preceding provider-free audit/preparation remains in
`diagnostics/model_state_inspection_audit.py` and `diagnostics/model_state_episode.py`.
The audit at `C:\pt\analyses\pl43-inspection-audit-v1` binds saved inspection results to
the exact frozen requests by path/raw hash/range/body. It finds 16 new-coverage,
six covered-only and three zero-match actions in the 14 response batches. Five
pre-turn21 reads revisit the already delivered editable body for exact anchors.
Public explanations can already identify the repair direction; neither explanations
nor source novelty establish repair quality or semantic necessity. Cause unresolved.

Episode preparation uses all 16 independent frozen starting public inputs, never
selected old responses. Current v2 changes only the unsent format instructions and
binds new first-request identities; historical v1 packets below are evidence only.
No old encrypted reasoning crosses the checkpoint. New native
reasoning/calls/results, state views, optional notes and corrections use the existing
engine in every arm. Only inherited historical state differs: this is not perpetual
current-only projection. Do not rewrite default agent prompts, model, memory, tool
policy or runtime identity. The external eight-response window must be labeled
censored, never charged as an agent LIMIT_REACHED or used to reduce its 40/100/4
limits. Restore checkpoint counters/mutations and verify the prepared first request
(separately bound to its source request) and allowed tools before new actions.
Public checks/finish remain model-selected;
no hidden evaluator, automatic checker or new planning action is added.

The injected scheduler reserves a complete active four-arm depth at the 272k input
bound/full 25k output with per-model prices and a shared cap. It stops every arm on
count/transport/billing/continuation uncertainty, never retries or resumes. The episode
module's CLI remains preparation-only; use the separate exact-grant collector above
for any later authorized invocation. The existing $5 grant is consumed; no cap/approval
transfers.
No-call checkpoint rehearsal forbids network, checks and probes while restoring both
actual source cutoffs into owned external disposable copies. Keep new validation
receipts at `C:\pt\validation\pl43-episodes`, separate from disposable scratch.
The prepared successor is `C:\pt\analyses\pl43-short-episode-design-v1\packet.json`
(`sha256:dc8f431ea408ce311270f2e42cd2ccbfc16d3ed6f7b8efa888c87e3ba1b5ac02`).
Both real cutoffs restore exact requests/tools/counters without actions. The 13 new
tests pass in 69.80s; 63 reused-engine/sampler cases pass in 104.12s; 35 factorial/
review/doc cases pass in 79.21s. Ruff passes. These are 111 related provider-free
cases, not the full runtime suite or a single under-two-minute end-to-end run.
Eight owned scratch roots were recycled with content identity and recovery mapping.
All 1,298 protected runtime/task/history files, source run and user files are unchanged.

The completed standalone model/state-history factorial diagnostic is in
`diagnostics/model_state_sampler.py` and `diagnostics/model_state_review.py`.
Its exact grant is consumed by `run_dev_sample_4bf128b8d21744d5` at
`C:\pt\analyses\pl43-model-state-live`: 16 responses/counts, four complete blocks,
$0.9615305 / $5, 159.184s, no retries/corrections/chaining. The earlier host rejection
started no process; explicit transmission/spend approval preceded the first dispatch.
Assessment at `C:\pt\analyses\pl43-model-state-assessment` freezes anonymous code
and public execution before mapping. Fourteen inspection batches remain unassessed
repair quality; two admitted mutations are both GPT-5.4/history, at C1/1 and C2/2.
C1's 29-line patch fails the first contract call (FileExistsError followed by an
unavailable `FakeOsModule.raise_os_error`); its upstream check passes. C2's 39-line
patch adds non-parent-path delegation, passing both checks. Both upstream executions
are 517 passed / 570 skipped. There are 25 inspection actions, two mutations, four
Docker checks, no check cache reuse and confirmed cleanup. Hidden acceptance/safety
evaluation remain NOT_RUN. Sixteen ordered requests/continuations, 27 function refs,
costs and candidate/check bindings validate. Input reduction is 43.3%/46.4%, but no
repeatable repair-quality benefit is established. Conclude CAUSE_UNRESOLVED: a
one-response design censors repairs after inspection. Do not adopt a default change,
force planning/memory, reset continuation or automatically extend paid collection.
The 1,298 protected files and user/source evidence hashes remain unchanged. The
16 exact owned checkpoint copies were recycled with identical content; restoration
and the separate Windows cleanup-helper correction are recorded in
`scratch-recycled.json` at the assessment root. Do not rewrite absolute historical
scratch references or sweep other roots. Three result-documentation tests pass in
0.066s with Ruff/diff checks; no new full runtime-suite claim accompanies this update.
Keep production runtime/tool surface v35, task packages, optional memory, schemas,
native history and encrypted continuation unchanged. No planning/memory requirement,
default model upgrade, default context rewrite or reasoning reset is adopted.

Preparation verifies immutable row43 journal/envelope/CAS at pre-turn14 and pre-turn21.
Reuse `fresh_state_design` to materialize only previously observed current source and
quote every prior public call/result. Both input variants start fresh, with no old
encrypted reasoning. A/C additionally quote older developer records in
`past_state_views`; B/D leave only that field empty. Model pairs differ only in model
ID. Preparation checks exact wire equality after removing the designated factor.
Both arms retain original public task, source hashes/ranges, current diff/errors,
notes/budgets/tool order and complete public archive. Do not inspect future outcomes
to select a proposal or add solution hints. This tests history length/repetition too;
it does not identify the native continuation effect.

Fix mini `gpt-5.4-mini-2026-03-17` versus `gpt-5.4-2026-03-05`, medium/25k, with reviewed
Standard short-context prices bound outside production pricing. Four blocks:
C1/1 ACBD, C2/1 DBCA, C1/2 BDAC, C2/2 CADB. One shared proposed $5 cap; maximum 16
responses/counts. The collector's optional per-arm prices and balanced-block policy
leave old protocols' defaults unchanged. Reserve all four responses at the 272k
input admission bound/full output before a block; count actual inputs JIT and stop
above that bound. No assumed cache discount or ceiling reduction. Conservative
reservation may leave unused money. All uncertainty stops the invocation without
retry/resume or replacements; partial blocks remain explicitly censored.

Public assessment is separate from collection and the original agent. Clone the
base commit and apply the public checkpoint diff, never copy final worktree state.
Restore host newline differences only when the *whole* historical file hash matches;
then recheck the canonical full diff. Hydrate prior source/check/mutation evidence
from the verified prefix into new journals. Use gateway admission and registered
public checks, not a second heuristic admission framework. Preserve candidate and
execution-policy evidence on failure; uncertain cleanup stops further execution.
Cache checks by checkpoint/candidate hash only within the same frozen assessment.
Keep inspection validity separate from relevance and unobserved mutation quality.
Only previously PASS declared checks can establish a newly observed regression.
Freeze anonymous public-code/action observations before `report` exposes model,
condition and tokens/cost. No paid judge, hidden evaluator, automatic causal verdict
or task-acceptance credit. `official=false`, `task_acceptance=NOT_RUN` throughout.

The packet and validation receipts require a separate exact execution grant; $5 is
not approval. Before any later collection revalidate source, runtime, diagnostic
implementation and pricing on the execution date. Old packets/journals are immutable,
not migrated after diagnostic hash changes. After data exists, select at most one
evidence-supported next implementation; insufficient/reversed differences mean
cause unresolved, not a forced planning/memory experiment or automatic extra run.

Prepared packet: `C:\pt\analyses\pl43-model-state-design\packet.json`,
`sha256:8e5c7710ea7162f6f91bd31fcdc9b05b5098afc61330108243aa9572d04d72b7`.
Sampler: `sha256:c3429a2dcef5b24deab165de0908c28a5efdd237799b79f27660d4248ec796ce`.
No-call receipts at `C:\pt\validation\pl43-model-state`: identical validation twice,
actual checkpoint clones/hydration, 237 passing tests (35 in 73.68s; 202 in 97.58s;
parallel XML span 99.382s), and Ruff. The synthetic public-assessment smoke reaches
mutation/checks/blind freeze/report, not hidden evaluation or measured agent quality.
All 1,298 protected runtime/task/history files and source run bytes remain identical;
user `.env`/`AGENTS.md` remain unchanged. No paid invocation or full runtime-suite
rerun is claimed. The nine exact owned temporary roots were recycled; their
restoration mappings are in `scratch-recycled.json` beside these receipts. There is
no authorization for a wider sweep of similarly named roots.

The preceding seam is the completed draft-review pilot at
`C:\pt\analyses\pl43-draft-review-live`, run `run_dev_sample_28ab0479aac64fe9`.
The original pre-process denial remains recorded. Subsequent explicit transmission
approval preceded the first actual invocation: four independent responses/counts,
$0.0700872 / $1.20, 38.615s, zero sampled tools, retries, corrections or evaluation.
This grant is consumed; no automatic repeat, feedback rollout or new live row follows.

The anonymous review at `C:\pt\analyses\pl43-draft-review-audit` was frozen before
mapping. All four ASTs equal the draft; A1/A2/B1 code bytes match, B2 only wraps a
line. Both public contradictions remain; all source anchors match and all new
memory updates are null. Actual A/B inputs are 50,675/50,702 tokens. Reasoning tokens
34/93 (A) versus 215/316 (B) do not establish what was internally reviewed; no output
is near 25k. Four ordered requests and continuations validate, with 13 original
reasoning items/native pairs per request. All 1,069 protected files and 17 live files
are unchanged during review. Keep runtime/task/prompt v35 unchanged and do not adopt
this extra review call: it shows no code improvement at this checkpoint, not that all
review or memory interventions fail. Static code evidence is not executed acceptance.
Documentation validation passes (3 tests, 0.10s) with Ruff; no full runtime suite,
runtime mock smoke or new scratch directory is claimed for this result-only update.

The preceding seam is the provider-free draft-review packet at
`C:\pt\analyses\pl43-draft-review`, implemented in `diagnostics/draft_review_sampler.py`.
It reuses historical checkpoint reconstruction and the existing independent-response
collector. The first collected requirements-focus A1 draft is pinned by source
journal/envelope/public artifact and original request identity; never rank/select a
different proposal based on later quality analysis. Both arms receive identical
unexecuted proposal data. Only `draft_reconsideration.harness_instruction` changes.
Original native history, 54 earlier items/13 opaque reasoning items, public task,
tools/order, notes, budget and model/medium/25k stay fixed. The draft-generating
response's own reasoning is not read; no native call or fake completion is inserted.
At preparation, request sizes 258,422/258,605 were bytes, with no fresh input counts.

This tests review framing beyond a neutral extra opportunity, not extra inference
versus none, native draft continuation, or general agent quality. Four independent
A1/B1/B2/A2 responses and a shared $1.20 cap were proposed, not run by preparation.
Keep actual replacement behavior separate from requirement mentions and static
contradictions separate from gateway/check acceptance. Freeze anonymous action reviews
before mapping; no judge, sampled tool, retry, correction or feedback chain is included.
The collector hash binds all three diagnostic source files. Its read-only inspector
recognizes one additional kind; old exact packet validation must use the recorded
implementation, not rewrite old packet hashes. Runtime/task/tool surface are unchanged.
All 82 focused draft/source/collector/docs tests pass in 37.59s and Ruff passes.
No full runtime suite or runtime mock smoke is newly claimed for this diagnostic-only change.

The preceding seam is the provider-free proposal-review/repair-boundary audit at
`C:\pt\analyses\pl43-proposal-review-boundary`. Mutation admission checks source,
scope and identity, not the truth of hypothesis/expected_behavior. B1's public prose
mentions preserving mode while its code violates that condition. Optional notes and
concerns are retention/attention aids, not a separate semantic reviewer.
`tests/test_dev_proposal_review_boundary.py` uses real local CSV checks, no model:
one read, wrong edit, first failure, journal reconstruction, partial repair, second
failure, final repair/check/finish. Three accepted mutations expose the cost of
sequential discovery; ample-budget inspection and direct repair remain available.
Same-hypothesis repairs and empty optional notes are valid. Existing native-note,
concern and mapped-feedback regressions complement this scripted gateway test.

Do not infer internal reasoning failure, new context loss or a required review gate.
Next isolate draft review versus a neutral extra inference on the same frozen public
input/draft; score actual replacements, not mentions of requirements. Preparing the
comparison is not paid execution authority. No runtime/task/prompt change, proposal
execution, full-suite result or new live quality claim follows from this audit.
An independent known limitation remains: `_inline_python_source` does not recognize
intervening interpreter flags such as `python -B -c`; raw failure feedback survives.
The row43 task uses the mapped plain form, so this is not its causal explanation.
All 56 focused workflow/concern/feedback/docs tests pass in 32.20s and Ruff passes;
the existing verification-flow mock reaches isolated CSV evaluation. No full-suite
rerun or separate mock CLI invocation is claimed for this test/documentation change.

The preceding seam is the completed requirements-proximity pilot on `d5a411a`:
`run_dev_sample_e54f9963571a4f1d`, `C:\pt\analyses\pl43-requirements-focus-live`.
Explicit payload/destination approval followed a host rejection that had started
no process or count. The one actual invocation completed four responses/counts,
$0.081974700 / $1.20 and 48.434s, zero sampled tools/retries/corrections/evaluation.
No additional collection or feedback rollout is authorized by this consumed grant.

Review at `C:\pt\analyses\pl43-requirements-focus-review` freezes anonymous static
findings before mapping: A1/A2/B1/B2 all create a missing leaf then falsely raise
EEXIST, and all pass leaf mode into intermediate create_dir calls. A2 additionally
has an old_text anchor omitting the actual docstring. Four null memory updates are
model choices, not lost gateway notes. No proposal is applied and no gateway/check
verdict is claimed. All four exact ordered requests and opaque continuations verify;
each request retains 13 reasoning items. A/B input counts are 49,648/50,210 and
all responses finish at 838–2,489 output tokens, below 25k. Protected 991 files and
17 live-result files remain unchanged during review; cache warmth confounds costs.

Do not promote this repetition field into the default runtime: this small pilot
shows no proposal improvement. The behavioral gap is public-constraint integration
and proposal validation; it does not establish internal reasoning, memory attention
or general ability. Source docstrings apply mode to parents while public checks
require a leaf/intermediate distinction, a possible conflicting cue, not causal proof.
The next investigation should target requirement/proposal checking rather than more
source repetition, mandatory notes or action restrictions. Runtime/task/tool hashes
are unchanged; official=false and acceptance/safety remain NOT_RUN.

The preceding provider-free requirements-proximity packet is at
`C:\pt\analyses\pl43-requirements-focus`, implemented outside the runtime in
`diagnostics/requirements_focus_sampler.py`. A pins row43 turn 14's historical
canonical request hash 511b1fc7; B adds only public_requirements_at_decision to the
latest state, copying the original issue and every public check ID/command verbatim.
Do not add an operator solution, new examples, selected helper details, mandatory
notes/probes, action masks or a continuation reset. Earlier 54 items/13 encrypted
reasoning items and tools/order/settings are unchanged. Full requests are
253,546/256,004 bytes, not fresh token counts. Runtime remains a3d7f3c0/v35.

Prepare/validate neither load credentials nor dispatch/count or execute task code.
The proposed collect scope is four independent A1/B1/B2/A2 next responses, mini
medium, fixed 25k, a shared $1.20 cap and zero tools. It reuses the bounded collector:
JIT count, full output/future-sample reserve, zero SDK retries, global uncertainty
stop, sanitized public output and encrypted-only artifacts. A frozen exact packet,
sampler and source/runtime identity are revalidated before credentials or output
root claim. No retry/resume/chaining/judge/evaluator is authorized. Static anonymous
action review precedes unblinding; non-mutation is not a correct-edit score. This
small proximity-plus-repetition pilot cannot establish attention use or task success.
Collection is not executed or authorized by preparing the packet; use the exact
operations approval contract. First accepted edit, repair and submission require
a separately scoped feedback rollout, not claims from these single responses.
All 95 focused sampler/shared-collector/docs cases pass in 45.108s and Ruff passes;
four-response fake collection never executes tools. Two real-source provider-free
validations agree exactly. No full runtime-suite/mock-smoke rerun is claimed for
this diagnostics-only change. Owned pytest scratch is recycled and hash-verified;
the mapping and validation receipt stay with the packet.

The previous seam is the public-only first-mutation trace audit at
`C:\pt\analyses\pl43-first-mutation`. Original row43
run_dev_9b91e06c13ff4bd3 introduces the traversal rewrite at turn 14 / decision seq151;
B2 inherits the first 20 decisions and diff bindings. Source/B2 chains, all 22
input/context/continuation artifacts, 21 append-only request extensions and native
call/output ordering verify. Seventy read source files are unchanged. Use stored
historical input: source runtime 1cd81f90 differs from current a3d7f3c0/v35, even
though the system prompt itself is identical.

The first edit had the public mode assertions and 350 exact source lines, including
helper behavior, with 27 model/87 tool actions/four mutations remaining and read,
search and probe available. Its response completed at 1,860/25,000 output tokens.
All 22 memory_update values are null; no note was authored or lost. Broad replacement
of delegation discarded existing behavior. EEXIST and intermediate-mode feedback
were then interpreted and repaired correctly; do not generalize this into inability
to interpret every failure. Untested combinations of traversal, target validation,
mode and platform behavior remained the public verification gap.

No new reproducible harness defect is established, so do not make a speculative
runtime/prompt/tool change or force notes/probes based on this trace. The 226,142-byte,
49,648-input-token request motivates an input-usability hypothesis, not proof of
attention failure. Presence of encrypted history proves retention, not semantic use.
Next isolate an evidence-to-decision change at the same pre-first-mutation public
checkpoint, with no operator solution/private hints, and measure first-edit public
violations, mutation consumption, counterexample repair and submission separately.
No new comparison or candidate execution is part of this audit. Provider/count,
Docker, task/check/probe/evaluator executions and private evaluator reads are zero.
Analysis CAS and a hash-chained dev-run-v1 completion event are under the new root;
official=false/claim_eligible=false. Runtime/task/history/user-owned files are unchanged.
Three documentation tests and Ruff pass. No full runtime-suite/mock-smoke claim;
the documentation tests did not create their reserved disposable basetemp.

The preceding seam is the completed isolated evaluation of the frozen operator repair
at `C:\pt\evaluations\pl43-b2-repaired`. Exact 49-line patch
`sha256:c69bf63cc3a7fc7c91054888501b538c9d7a4314849baabb2c2525c80e120610`
passes task acceptance, public regression, scope and typed evaluation safety;
failure_class=null. One unchanged evaluator invocation/fresh no-hardlink workspace
takes 7.559s. Manifest/task/runtime/image, submitted/applied/checked hash and policy
receipts verify; 2,025 protected files are unchanged and owned containers are absent.
No provider/count/new-probe call, repair, retry, model cost or live row occurs.
Only aggregate private results return to the operator conversation. No private case,
failure detail or reference solution is used for diagnosis or agent context.

Evaluation ID is run_dev_operator_b2_repair_eval_20260911, separate from original B2
and the operator repair. Prior probes are source history, not inherited native calls.
Manifest model is an explicitly unused schema placeholder; task execution is real
Docker, not a mock acceptance result. All results remain official=false/claim_eligible=false.
Runtime/tool surface stays v35 and task v2/50-line scope are unchanged.

Read-only review of B2's last five public actions confirms probe -> non-parent
delegation repair -> two passing checks -> finish, with completed responses and
memory_update=null. The probe and repair address no-parent regressions; changed
parent-traversal combinations are not independently exercised in that tail.
This is a behavioral-verification gap, not evidence that finish used stale checks.
It does not establish missing context, tool removal or token saturation. One last
accepted mutation remained in B2; the operator used three candidates and extra public
observations. Do not claim an equal-budget comparison or global budget sufficiency.
The next loop question is how an agent selects public checks for changed behavior
and remaining assumptions, not whether to inject this patch or force more tools.
Twelve existing evaluator/documentation tests and Ruff pass. The new owned pytest
scratch is recycled with content verification and a recorded restoration mapping;
durable evaluator workspace and all prior roots are preserved. No new full-suite or
mock-smoke claim. Result and public-only trace comparison remain in the evaluation root.

The preceding seam is the completed separate B2 operator repair at
`C:\pt\repairs\pl43-b2`. Original run/task/runtime bytes are not modified, and no
private evaluator input, hidden failure detail or reference patch is loaded or used.
The independent no-hardlink workspace contains a 49-line, one-file final patch
`sha256:c69bf63cc3a7fc7c91054888501b538c9d7a4314849baabb2c2525c80e120610`.
The original 50-line scope and both public registered checks remain unchanged.

The frozen 30-case POSIX differential matrix matches 30/30, versus original B2's
18/30. Resolved intermediate traversal and final-target validation must be separate.
Windows has different parent-existence/normalization semantics; three operator
candidates match a separate unchanged native Windows matrix in 6/24, 23/24 and
24/24 cases. Preserve drive-relative behavior as well as absolute/relative paths.
Both original checks pass on the final hash, with upstream 517 passed / 570 skipped.
Final sandbox execution time totals 11.267s. Across development there are five public
probes, four public checks and one stdlib-only native Windows batch, all provider-free.

Native Windows Python is 3.14.5 and container Python is 3.12.13: this selected matrix
is not cross-version equivalence or generalization evidence. macOS native, Windows
ACL/mode and symlink/junction/network-share behavior are not verified. Private task
acceptance is NOT_RUN. Do not equate operator patch success with agent improvement,
resume/back-credit original B2, supply operator solutions as agent memory, or add
tool-policy restrictions on this evidence. Any private acceptance evaluation is
separate work. Final patch, public comparison and provenance live beside result.md;
official=false/claim_eligible=false throughout. Runtime/tool surface remains v35.
Audit verifies 234 protected files, runtime, candidate/receipt bindings, CAS/journal
and owned-container cleanup. The new native Windows scratch is recycled with an
exact verified restoration mapping; the docs-only pytest basetemp is not created.
Three documentation tests and Ruff pass; no new full runtime-suite/mock claim.

The preceding seam is the completed independent public B2 diagnostic at
`C:\pt\analyses\pl43-b2-public`. No private evaluator file/detail/reference patch is
read; cases derive from public requirements and B2 source. One fixed public probe
on Python 3.12.13/POSIX compares 30 cases: 18 match and 12 differ, not a sampled
failure-rate estimate. Existing-file acceptance, terminal-parent validation,
trailing-separator mode/error and repeated-separator/symlink parent resolution
expose incomplete semantics in the hand-written traversal branch. Four tested invalid
parent cases and two terminal-dot cases agree; preserve these negative findings.
The comparison takes 6.328s; exit zero means execution completed, not behavioral PASS.
Journal/CAS, source/diff and policy receipts verify; 219 protected files and runtime
bytes are unchanged, the owned container is absent, and provider/private-evaluator
calls and model cost are zero. Windows/macOS native cases remain unverified.

Do not equate these public defects with a specific hidden failure or infer a memory,
prompt or action-mask cause. No patch/task/runtime change or policy adoption occurs.
Next work should preserve intermediate side effects and final-target/type/mode
checks together, validate existing primitives before reuse, and keep the frozen
public cases as independent operator evidence. Task v2 is immutable; registered
check changes require a separately decided versioned successor. Do not inject
operator hints into the old comparison or add compulsory probes/notes on this result.
Details and limits are in result.md; all results remain official=false/claim_eligible=false.
Three documentation tests pass in 0.058s, plus Ruff. Runtime is unchanged and no new
full-suite/mock execution or disposable pytest directory is claimed.

The preceding seam is the completed post-hoc B2 submission evaluation at
`C:\pt\evaluations\pl43-b2` (aggregate report `result.md`, integrity `audit.json`).
Its unchanged 39-line public submission passes public regression and scope, but
fails private task acceptance with `PRIVATE_EVALUATION_FAILED`; typed safety PASS.
No evaluator exception occurred. One isolated workspace and the standard evaluator
complete in 7.206s with zero provider/count/new-probe calls and $0 model cost.
Base acquisition alone uses a local no-hardlink clone at the exact audited commit.
Manifest, task/runtime/image, submitted/applied/checked diff, public probe receipt
derivation and policy evidence verify; 1,835 protected files are unchanged and owned
containers are absent. Runtime/tool surface remains v35.
Twelve existing evaluator/documentation tests pass in 6.577s, plus Ruff; no new full
runtime-suite or mock-smoke execution is claimed for this operator/docs-only change.

The new operator evaluation ID and external state root distinguish this evidence
from the original B2 subject ID, which is retained for receipt identity. The original
run's PUBLIC_CHECKS_SUBMITTED / private NOT_RUN bytes are not migrated or back-credited.
This candidate is not task-complete. Do not feed private evaluator contents/failures
back into agent context or derive public repair hints from them. The aggregate failure
does not establish its semantic cause, an incorrect private oracle, a harness defect
or general probe benefit. Any further diagnosis starts from public requirements and
independent public examples. No repair, paid comparison, resume, mandatory-probe
adoption or normal live row is included. Results remain official=false/claim_eligible=false.

The preceding seam is the post-hoc A1 stop-validity check, not another model comparison.
`C:\pt\pl43-stop-validity-a` restores the exact stopped 48-line candidate once in a
new external workspace. Traversal PASS; upstream has one macOS trailing-link failure,
516 passed/570 skipped. Review/audit: `C:\pt\pl43-stop-validity-review-a`.
The candidate really failed with no edits left, so an unchecked stop alone does not
prove budget confusion, stale memory or irrational action selection. The earlier
interpretation was too strong. `completion_possible` is a conditional budget bound,
not a prediction that the code will pass. Predicted failure and an executed current-diff
verdict must remain separate. The model's internal basis is unknown; do not back-credit
operator checks or count every untested stop as a harness defect.
One unchanged operator restoration/two registered checks take 19.899s, $0, zero
provider/count/probe calls. No paid A/B, resume, new repair, Docker startup/pull/build,
private evaluation or normal runtime modification. All result axes remain NOT_RUN
except the separately recorded public check verdicts; `official=false`.
Audit verifies 62 CAS objects, exact candidate/check/task/image bindings and cleanup
of two owned containers; 7,033 prior files and 199 execution files are unchanged.
40 existing recheck/projection/docs tests pass in 43.403s, plus Ruff. Do not repeat
the already completed one-field horizon omission comparison or add mandatory checks,
stop prohibitions or forced notes on this evidence. Separate observed, predicted and
unknown candidate outcomes in analysis before considering further action-selection
comparisons. The remaining observed task defect is regression preservation in the
last repair, not established inability to understand zero-edit budgets.

The preceding seam is a collected probe-first repair comparison, with no default policy
adoption. Results: `C:\pt\pl43-probe-live-a`; review/audit:
`C:\pt\pl43-probe-review-a`. A1/B1/B2/A2 complete 4/6/5/2 new responses and actions,
17 total, $0.584686950 and 233.059s. A submits 0/2 and B 1/2 at one frozen checkpoint;
do not generalize this small observation into a mandatory-probe policy.
B2 probes both platform errors, restricts the new traversal logic to paths containing
`..`, delegates the rest to the original implementation, and submits a 39-line diff
after upstream (517 passed/570 skipped) and traversal PASS. Checked/workspace/submitted
hashes match. Private evaluation, task acceptance and aggregate safety remain NOT_RUN.
B1 probes Windows and restores platform-specific handling but leaves the macOS raw
trailing-separator operand defect; B1/A2 each record one macOS failure, then correctly
reach LIMIT_REACHED with no accepted mutation left. A1's 48-line candidate was untested
within its model trajectory:
its actual last input offers run_check, two NOT_RUN checks, null current failure,
recheck guidance and a viable three-call completion path, yet it claims current
failure and stops. Do not merge that voluntary stop with the valid horizon stops.
All 17 memory updates are null; exact native/continuation delivery is verified, not
working-note benefit or internal attention. Next evidence should distinguish useful
execution questions, behavior-preserving repair scope and actual recheck/submission,
preferably on independent public checkpoints. No extra paid run or runtime change
is part of this completed comparison.

`diagnostics.probe_first_view` freezes exact A/B inputs from the original row-43
pre-turn-21 public failure. A remains ordinary; B changes only `tool_choice` to
`{"type":"function","name":"run_probe"}` using the official Responses contract.
Keep the full tool list/order, native input and ciphertext, sources, optional notes,
model/medium/25k and inherited budgets identical. Do not insert the operator's
successful patch, probe, expected observation or diagnosis as model guidance.
The public counterfactual at `C:\pt\pl43-repair-check-review-a\result.md` proves a
50-line repair passes the two public checks, not that a model-authored probe helps.

Packet `C:\pt\pl43-probe-first-design-a` preserves 83 items/20 reasoning items;
only request bytes grow 424,331 -> 424,359. The preparation audit at
`C:\pt\pl43-probe-first-prep-a\audit.json` verifies 5,955 protected files unchanged.
Keep source request, preparer, runtime and protocol hashes exact. The prepare/validate
CLI has no credential, provider/count, sandbox or collector path. Do not mistake
`PREPARED_NOT_EXECUTABLE` for a completed agent comparison or silently use an older
collector: existing source-rollout B inlines source and would confound this contrast.

The collector contract has four A1/B1/B2/A2 branches, eight new responses each
and one shared $1.20 cap. Every probe/correction consumes the inherited budgets.
Force B's probe phase only until its first attempt's native feedback is delivered;
release on execution failure too, with no forced probe retry. Bounded protocol
correction retains the phase; subsequent requests use the ordinary loop and policy.
Reconcile pending batches before dispatch, preserve encrypted continuation and action
idempotency, and stop all branches on count/provider/billing/continuation/cleanup
uncertainty. Count just in time against the exact request and full output ceiling;
cap/response limits censor the branch. No paid retry/resume, private evaluation,
Docker startup/pull/build, normal row or runtime policy adoption is included here.
Review public question usefulness, observation interpretation, code correctness and
actual recheck/submission separately; no reasoning plaintext, model judge or semantic
success inferred from merely choosing the forced probe. One checkpoint/two samples
per arm cannot establish general effectiveness. Runtime/tool surface remains v35.

`diagnostics.probe_first_rollout` now implements this separate collector. Its plan
binds the unchanged original design and all diagnostic dependencies; never migrate
the preparer's `collector_implemented=false` record. Reuse the ordinary request
builder and shared JIT driver through explicit hooks, not the old B inlining hook.
Journal the exact forced choice separately from the unchanged full tool list, and
validate corrections/actions against that choice. Restore unconsumed corrections
and reconcile recorded decisions/batches before new dispatch or horizon admission.
Validate native input/ciphertext before replay. Completed probe/check results are
replayed; an execution lacking its durable result stops `TOOL_EXECUTION_UNKNOWN`.
Exact admitted mutation candidates reconcile once; unrelated drift fails before
execution. Unknown provider completion stops; known usage with no recoverable
decision stops continuation rather than retrying. Terminal reconciliation performs
no provider/tool work or journal writes. No paid restart/resume CLI is provided.
The implementation-only request was followed by a separate proceed request consuming
the four-branch comparison once; preserve both stages' distinct evidence.
Executable plan: `C:\pt\pl43-probe-collector-plan-a`; handoff/audit:
`C:\pt\pl43-probe-collector-review-a`. Its initial A/B hashes still match the frozen
design, and 6,065 protected files were unchanged at handoff. The later execution-day
preflight is `C:\pt\pl43-probe-preflight-a`: running backend, existing pinned images,
clean tracked inputs and official pricing pass. Final review verifies four journals,
313 CAS objects, native prefixes/ciphertext, tool-choice phase release and exact
usage/shared-cap admission. Six owned containers are cleaned up and absent; 6,174
prior protected files and 849 live files are unchanged. No cap/response censoring,
25k saturation, incomplete correction, paid retry/resume, Docker startup/pull/build
or private evaluation occurred. Runtime/tool surface remains v35.
The results-only documentation update passes three layout/link tests, Ruff on
`patchloop tests` and `git diff --check`; no new full-suite/mock claim is made.

Provider-free validation passes 178 cases in overlapping groups (74 in 55.73s,
104 in 69.90s) and Ruff. They cover the new collector's synthetic probe/repair/
check/finish and uncertainty/replay paths, not model benefit. Normal-runtime mock
`run_dev_e2ee0c2be6ec45ea` reaches isolated evaluation in 4.54 command seconds, with
four turns/five actions, zero cost and safety NOT_RUN. Keep it separate from the
diagnostic's NOT_RUN task acceptance. The unchanged full runtime suite is not rerun.

The sequential review fixes first address deterministic execution, recovery, budget
and note defects; do not attribute those synthetic edge cases to row 43 without a
matching trace. State ownership is consolidated at the existing B/P function,
shared observational normalization and durable evaluation-completion receipt, not
a new planning layer or broad framework rewrite.

`diagnostics.current_source_view` is a prepare/validate-only presentation prototype.
It changes only the latest complete view's selected current-source references into
their exact inline bodies. Earlier native items/ciphertext, task, schema order, all
other state and selected path/hash/ranges remain unchanged. Never expand selection
to all previously observed lines of that file. On frozen row-43 pre-turn-21 control A,
385 selected lines and 82 prior items/20 reasoning items are preserved; 15 current
reference ranges become inline. Full UTF-8 request bytes grow 424,331 -> 440,593.
Evidence at `C:\pt\pl-fix-source-view-a` establishes delivery equivalence and cost in
bytes only, not token counts, note use or better model decisions. This is not wired
into normal runtime and has no count/provider/tool execution path. Keep the official
[reasoning continuation contract](https://developers.openai.com/api/docs/guides/reasoning#keeping-reasoning-items-in-context).

The subsequent user request authorized this now completed A/B follow-up without
routine reapproval under the referenced task/model and shared $1.20 cap, not row 44.
`C:\pt\pl43-source-preflight-a\result.md` records the initial engine-unavailable stop.
The user later explicitly requested startup; the bounded recovery succeeds without
data reset (`C:\pt\pl-docker-start-20260910-a.md`). Do not infer future startup or
image acquisition permission. A real check/probe smoke now passes with cleanup.
`diagnostics.current_source_rollout` supplies the separate tested collector: exact
row-43 pre-turn-21 native prefix, four fresh branches in A1/B1/B2/A2 round-robin order,
eight new responses each, one shared $1.20 cap, 25k desired/admitted ceiling, 1,800
experiment seconds and inherited 20-model/80-tool/one-mutation/1,601-active-second
budgets. Only each new B view's selected current source bodies become inline. Keep
full native history/ciphertext, public/private separation and registered gateways.
Source v34 and current executing v35 are separately hash-bound; normal exact-match
resume is unchanged. Stop all branches on cost, billing, continuation or cleanup
uncertainty; no retry/resume or private evaluation. Treat cap/response-bound branches
as censored, not evidence that the model could not solve the task. The inline
prototype itself remains provider-free and immutable.

Collector `29eb5fb` completed all four branches at `C:\pt\pl43-source-live-a`:
12 counts/completed responses/selected tool actions, $0.387835350 and 204.030s.
No submission, private evaluation, retry, cap/response censoring or 25k saturation
occurs. A1 gains 79 new helper lines in two searches, mutates and stops; A2/B2
recover a scope rejection, mutate and stop. Their final actual inputs expose
`run_check`, two current NOT_RUN checks, null current failure and a viable three-call
completion path. Old failure claims in their stop decisions are not current-check
evidence. B1 uses the wrong helper receiver, runs regression (21 failures), then
correctly reaches LIMIT_REACHED because no accepted mutation remains for repair.
All 12 memory updates are null; neither note effectiveness nor source-inlining
benefit is established. Keep the voluntary untested stops separate from B1's gate.

Six provider-free post-hoc operator checks at `C:\pt\pl43-source-operator-a` find
A1/A2/B2 traversal PASS and upstream 3/1/1 failures. A2/B2 repair Windows but not
macOS; A2's explicit stale Windows claim is false, while B2 only asserts overall
current regression failure. Never back-credit these operator checks to the agent.
Analysis `C:\pt\pl43-source-review-a\result.md` and final `audit-v2.json` verify
292 branch CAS objects, exact native prefixes/encrypted continuation, billing,
owned cleanup and historical preservation. The initial audit's empty CAS glob was
corrected in a separate v2 receipt without changing live bytes. Runtime stays v35.

The next candidate was prepared as a one-field ablation in
`diagnostics.completion_signal_view`. Read-only inspection of the actual stop inputs
confirms `completion_guidance` already recommends `run_check` at the front, while
`pending_recheck.guidance` explicitly separates historical failure and zero edits from
still-available checks/submission. No missing-instruction defect is established.
Do not duplicate these instructions or claim new wording fixes the observed behavior.

The prototype selects only nonempty candidates with zero remaining accepted mutations,
current nonfailed check status, no current failure, matching declared/wire tools and
a feasible offered check/submission path. It deletes only the latest state's
`action_horizon.mutation_completion_horizon`; original zero-edit counters, completion
guidance/forecasts, historical focus, sources/notes and every earlier native item stay
exact. There is no new message, source read, reasoning reset, schema/order change,
tool execution or runtime action gate. Reject malformed/ineligible diagnostic inputs
before creating a packet. Normal state projection remains unchanged on v35.

Prepare uses an exact source hash and a fresh external root; A.json is byte-identical
control, B.json the one-field omission. Validation recomputes both plus manifest and
implementation hash without credentials/count/provider/task execution. Four pairs
in `C:\pt\pl43-completion-view-a` remove exactly 158 UTF-8 bytes each; 72 focused tests
pass in 8.95s and 5,254 protected files are unchanged. This is not token or behavior
evidence. A further 47 existing collector/native-rollout tests pass in 68.32s; mock
`run_dev_06e51698c0d640a6` reaches isolated EVALUATOR_PASS in 4.16 command seconds,
four mock turns/five actions, zero cost and safety NOT_RUN. The unchanged runtime's
full suite is not rerun. Earlier warnings and original system prompt remain, so the proposed contrast
isolates latest-field presence only, not all mutation-pressure information.
Competition between nested mutation-horizon and overall completion signals remains a
hypothesis. Do not add a hard stop prohibition, force memory, adopt inlining, execute
these historical branches or silently extend paid collection. Next work would need a
bounded matched-input collector; this prepare/validate module cannot perform it.

That collector is now `diagnostics.completion_signal_sampler`, under the subsequent
proceed request for exactly four pairs/eight responses and zero selected tools. It
reconstructs the pinned public requests from each branch's native/count event and CAS,
validates the prepare-only transformation, then freezes all eight request bodies and
source identities in a separate packet. C1-C4 map to A1/B1/B2/A2 checkpoints; sample
C1 A/B, C2 B/A, C3 A/B, C4 B/A once, without chaining sampled output or corrections.
Review anonymous public decisions before unblinding. Preserve full native prefixes,
encrypted reasoning, tools/order, snapshot model/medium/25k and root `.env` identity.

Use one fresh external result root and shared $1.20 invocation cap. Count immediately
before each dispatch and reserve that input plus the full 25k maximum output, with
zero retries. This protocol does not reserve hypothetical later samples; cap-excluded
cells remain censored. Other samplers keep future reservation enabled by default.
Keep durable usage and encrypted CAS; stop all remaining cells on uncertainty. Inspect
interrupted results read-only, never resume/recollect. Source receipt, sampler and
runtime hashes must match before claiming the result root or loading credentials.
This changes only diagnostics: no task/worktree access by selected tools, Docker,
normal row 44, private evaluation, prompt default, memory mandate or runtime policy.
Old envelopes/results are not migrated; completion-signal collection is now complete.
Validation: 29 new cases pass in 12.07s, 139 existing collector/projection/docs cases
in 62.88s, Ruff PASS; production mock `run_dev_ca8ad90fdf494637` reaches isolated
EVALUATOR_PASS in 3.97 command seconds at `C:\pt\pl43-completion-dev-smoke-b`.
All mock cost is zero and safety is NOT_RUN; the unchanged full runtime suite is not
rerun for this diagnostic-only addition.

Completed collector `5df509a`, run `run_dev_sample_a746407355254569`, at
`C:\pt\pl43-completion-live-a`: eight counts/completed responses, $0.203554800,
47.671 active seconds, zero tools. Both A and B select stop/stop/stop/run_check on
C1-C4. All six stops present a current upstream failure unsupported by current-diff
checks; zero accepted edits does not remove the offered three-call completion path.
The two C4 responses select upstream verification without executing it; one correctly
distinguishes historical failures, the other incorrectly describes upstream as the
remaining gate even though both current checks are NOT_RUN. All eight note updates
are null; native/encrypted continuation is intact. Outputs are only 296-613 tokens.
The single-field omission removes 158 bytes/31 input tokens but demonstrates no
next-action difference in these four matched pairs. Do not promote it to a default.

Read-only historical comparison finds the identical C2 original previously selected
a check but now stops, while C4 previously stopped but now checks. This variability
and one draw per condition prevent a general no-effect or root-cause conclusion.
Earlier forecasts/system prompt remain; this does not test all mutation pressure.
Current-versus-historical verdict use remains the behavioral problem, not a proven
implementation cause. An unchecked stop can be rational if the model predicts an
unrepairable failure; the public explanation does not distinguish that from stale
verdict reuse. Do not infer a memory defect from stopping alone. Keep the next
information-layout hypothesis separate from any
runtime adoption, stronger gate, forced note or reasoning reset. No further collection
or normal row is part of this completed experiment. Report and anonymous review:
`C:\pt\pl43-completion-review-a\result.md`; audit verifies 34 CAS objects, exact inputs,
continuation/billing and 5,268 unchanged protected files. Acceptance/safety NOT_RUN.

The current single-occurrence edit unit remains explicit. A synthetic text-only
comparison at `C:\pt\pl-fix-edit-unit-a` confirms two distant one-line replacements
cost two accepted mutations, while a combined exact anchor must include the gap.
With 20 unchanged lines, argument-only bytes are 167 separate vs 825 combined and
observed anchor coverage is 2 vs 22 lines. A 1,500-line gap exceeds the current 20k
old/new text bound. These are expression constraints, not model failure causation.
An atomic multi-replacement candidate would change wire and mutation-count semantics;
it is not silently enabled by the reliability fixes. No note quota, automatic semantic
memory, context reset, cap increase or new hard action gate is justified by these probes.

- Edit `dev-head` directly in small commits; do not version ordinary fixes.
- Keep cross-run memory disabled; bounded public run-local working notes are enabled.
- Keep mutation intent embedded in the mutation turn.
- Treat the exact live invocation as bounded development authority.
- Recover historical executables only from checkpoint `b71ddeee`; do not restore
  their active import graph.
- Keep confirmatory work in a future, separately frozen lane.

The prepared failure-order pilot is now collected after the user's explicit instruction
to execute it without another approval request. `08ec618f` produces
`run_dev_sample_36bef4eebfaa4954` in `C:\pt\pl43-order-live-a`: four counts/completed
responses, $0.119271000, 37.890s, zero tools/retries/corrections, acceptance/safety
NOT_RUN. Do not count this as normal row 44. Execution-day OpenAI Docs pricing agrees
with the pinned registry; all inputs count 91,222 tokens. Anonymous review precedes
unblinding in `C:\pt\pl43-order-review-a`.

A1 proposes both macOS and Windows repairs; its old text matches current delivered
source, but the complete text diff is 53 additions + one deletion = 54/50 lines.
This is a static scope finding, not an executed rejection or check. A2 and B1 search
the same macOS test name while their public goals mention both failure classes. B2
searches wrapper helper usage for macOS only. Searches are not executed or chained:
do not grade their unobserved follow-ups as failures or call independent draws a loop.
All four notes are null. Both arms retain native history and encrypted reasoning;
no note-use or history treatment occurred. No clear benefit from latest-summary order
is observed, but two samples per arm cannot identify a general causal effect. Two
earlier copies of the failure list were deliberately not reordered.

The finding narrows the observed issue to consistent integration of multiple failures
and complete patch-size constraints; it does not justify a sorting policy, forced
memory, larger cap or new gate. Existing typed scope recovery is unexercised here.
No tool-feedback continuation, further paid draw, runtime change or row 44 is implied.
Review verifies 22 events/12 CAS objects, all four requests/continuations, cost arithmetic
and immutable source/run/credential/history bytes. Result docs, three doc tests, Ruff
and whitespace are updated; unchanged runtime suite/mock is not rerun.

Latest implementation seam: `diagnostics/failure_order_sampler.py` connects the
immutable row-43 pre-turn-21 audit (`C:\pt\pl43-decision-a`) to the shared standalone
collector. This is not a runtime/prompt/memory-policy fix. A keeps the exact original
request; B permutes only `state.current_public_failure.failure_summary.lines` in
the latest developer view by `[1,2,0]`. Historical views, encrypted reasoning/native
calls and outputs, tool-schema order, source, budgets and medium/25k settings remain
unchanged. Reconstruction must match the original request hash and prospective B
input hash. Never add reviewer labels, later decisions or private feedback to inputs.

New prepare/validate commands are provider-free. The prepared external packet is
`C:\pt\pl43-order-design-a\packet.json`, hash
`sha256:95ac3ffe75d4cd4587dd1a5db0ec35e9b6a3a28aa6698c3a13c6f58f300e2664`;
collector hash is `sha256:8d7cc26d63c85a25306f64ac335eaedf0738a12d231036c7ab1b307627279bbc`.
Revalidate before any future separately approved A1/B1/B2/A2 collection. The identity
binds this module and the shared engine; normal runtime/task identity remains separately
bound. Earlier packets, collectors' receipts and audit bytes are not migrated.
The shared change is read-only inspect recognition of `failure-order-sampler-v1`.

Collection requires its own `--approve-four-order-responses-zero-tools` authority,
exact packet/sampler/credential/cap/price inputs and a fresh external root. It uses
the shared immediate-count, zero-retry, fixed-output, durable-usage and uncertainty
stop path, with the enforced 272,000 input-token limit reserving each future sample's
worst permitted cost. No guessed alternate count, chaining, correction, sampled-tool
execution, judge call or resume. Inspect interrupted results read-only. Only anonymous
public decisions enter review; plaintext reasoning is discarded and encrypted items
stay in hash-bound CAS. Keep static review separate from gateway admission/correctness.

Validation: 33 new cases plus collector/design/rollout/docs/mock regressions pass
161 tests in 71.99s and 37.58s; Ruff passes. Frozen-request fake collection in
`C:\pt\pl43-order-smoke-a` preserves all 83 input items and both arms' exact native
prefixes; all counts/responses/cost there are simulated. Production mock
`run_dev_ccc20ba4bacc4efa` reaches isolated EVALUATOR_PASS in
`C:\pt\pl43-order-dev-smoke-a` (task acceptance PASS, safety NOT_RUN, zero cost).
Receipts are in `C:\pt\pl43-order-wire-a`; unchanged runtime tests are not all rerun.
That implementation's next seam was the separately approved pilot now recorded above,
not a normal live row. It did not authorize a paid call, Docker operation, row 44 or
automatic fix. Two draws per arm on one failure-selected checkpoint do not prove
a general ordering effect, memory effectiveness or whole-run success.

Normal row 43 is complete on v34: `run_dev_9b91e06c13ff4bd3`, AGENT_STOPPED,
22 model/count/tool calls, four edits, $0.464054850, 224.094 active seconds. First
edit is turn 14. False EEXIST and intermediate-mode failures are repaired at turns
16/18, followed by public PASS at 19. Turn 20 reports one macOS and two Windows
regression failures; all three rows reach the next input. Last edit at 21 restores
only the macOS branch; 22 stops without rechecking. Final diff is 46 lines and both
checks are NOT_RUN. Pending historical failure and explicit run_check advice are
present; 19 calls/79 tools remain before stop, but zero mutations. Do not call this
a removed check tool, horizon terminal or verified final-candidate failure. A forced
recheck alone does not supply the missing Windows repair. Investigate multi-failure
repair selection and preservation of already observed helper responsibilities.
All 22 memory updates are null; no annotation rejection or projection loss occurs.
This is not proof that note non-use caused the failure or that shorter guidance cannot
help generally. Source/failure delivery, 66 artifacts, 22 continuations/21 prefixes,
four mutation identities/policies and exact container cleanup verify at
`C:\pt\pl43-review-a`. No probe, submission or private evaluator runs. Runtime remains
frozen; no auto-fix, historical candidate execution, retry/resume, paid comparison
or row 44 is authorized. The exact row-43 approval is consumed.

V34 is the local-only memory-guidance compression seam. The read-only audit at
`C:\pt\pl41-42-memory-a` found correct storage/projection: row 41 updates the same two
note IDs, often shifting into current status; row 42 never requests a non-null update.
The row-41 rejected resolution cites an observed mutation, not an eligible completed
check/probe; do not describe it as an invented future action. No new memory mechanism
or task-specific prompt repair follows. The schema's structural values/order and the
prompt outside its memory block stay exact. Measurements and validation are in
`C:\pt\pl34-memory-a`; do not rewrite the earlier audit or run bytes.
Any future comparison needs exact separate approval. Observe reusable facts before
the first edit, later topic retention, actual citation support and downstream repair/
submission. Same-response annotations are not prior-memory reuse, and annotation counts
are not effectiveness. That implementation authorized no provider/Docker execution;
row 43's later separate approval above is consumed. No row 44 or paid A/B is authorized.

Normal row 42 is complete on the same frozen v33: `run_dev_2dc51a86320d43d1`,
EVALUATOR_FAIL / acceptance FAIL / safety PASS, 18 model/count calls, 19 tools,
one accepted edit, no rejection, $0.287173950 and 197.140 active seconds. Fifteen
inspections precede turn 15's first edit; both visible checks pass (517 upstream
cases, 570 skips) and turn 18 submits the same 45-line candidate. Isolated acceptance
fails. The submitted public code duplicates the final creation for a trailing empty
component and rethrows EEXIST for a file parent. Relevant helper bodies are exact
native receipts before mutation, not missing evidence. Do not export private cases
or feedback to future agent inputs or use them to tune the frozen task.

All 54 public artifacts, eight outcome artifacts, 18 continuations, 17 input prefixes,
patch identities and execution policy hashes verify in `C:\pt\pl42-review-a`.
The row-41/42 first model inputs are byte-identical; runtime/task/model/cap/limits/
sandbox and credential-path identities match. This time notes and probes are unused.
At finish, optional source/probe/edit actions and ample budget remain available;
the model elects to submit. No public failure means the pending-recheck flow is not
exercised, rather than observed broken. Keep candidate semantic errors separate from
transport, source delivery, action-mask or budget defects. The two observations do
not isolate a memory effect, establish a success rate or justify a stronger gate.
Runtime stayed frozen for that result-only receipt. Row 43 later received its own
exact approval above; this older approval authorized only row 42. Prior bytes remain
unchanged, and the operator's saved-result analysis executes no candidate or new check.

Normal row 41 is complete on v33: `run_dev_872af7b3c9524a04`, EVALUATOR_PASS with
task acceptance and safety PASS, 22 model/count calls, 23 tools, two accepted edits,
$0.431456850 and 265.983 active seconds. First accepted edit remains turn 17 after
14 inspection actions and three rejected proposals (wrong file, 72/50 and 59/50).
Turn 18 fails the public intermediate-mode assertion; turn 19 changes the intermediate
creation mode to PERM_DEF while preserving leaf mode. Turn 20's actual native view
separates current failure from pending recheck, and the model immediately runs that
check successfully. Turn 21 passes all 517 upstream cases (570 skipped), then turn 22
submits the same 30-line candidate; isolated evaluation passes. Probes are unused.
Notes are used: 13 updates, 12 applied and one partial due to an unobserved verification
reference, corrected after the real check. Eight repeated concern updates are unchanged.
The repair/recheck path is now live-observed; attribution to v33 or broad quality is
not established by one run. Preserve early scope mistakes as efficiency evidence,
not a new reason to tighten action masks. Exact patch/manifest/policy/native-prefix
identity checks and prior-byte preservation pass in `C:\pt\pl41-review-a`.
That receipt did not authorize row 42; the separate approval above is now consumed.
Row 43's later separate approval is also consumed; no row 44, retry/resume,
earlier candidate execution or paid comparison is authorized.

Normal row 40 is now complete on v32: `run_dev_766c5a6ab2f04d82`, 25 model/count/tool
calls, four accepted edits, $0.461354550, 197.000 active seconds, LIMIT_REACHED solely
on accepted-mutation exhaustion. First edit is turn 17 after 16 inspections; turns
19/21 repair bytes separators/root prefix. Turn 23 consumes the final edit with a
false premise that `splitdrive` loses bytes type: its returns slice the input and the
added drive coercion is a str/bytes no-op. The turn-22 read stops before the return
paths. Actual turns 22/23 label the prior error historical/awaiting_recheck and guide
run_check, but the model edits again without rechecking. Preserve this difference
between delivered state and effective use; do not claim a model-only cause or turn
the trace into a mandatory check/mask without a separate scoped change.
Turn 24's public contract passes; turn 25's regression has seven failures from the
direct walk's EEXIST behavior and lost macOS handling. Both original helper bodies
were already observed. Final diff is 50 lines, current contract PASS/regression FAIL,
no submission/evaluation. V32 early error summaries reach the next decisions; the
final mixed-error summary preserves all seven rows and accurate truncation, but has
no later inference. All 75 artifacts, 24 prefixes, four mutation identities and four
check policy hashes verify; four owned containers are absent. Notes/probes are unused.
V33 now separates that historical error into pending recheck in the derived model view;
the canonical audit and original native results are unchanged. A read-only comparison
of all 25 saved row-40 views changes only the failure/pending card at turns 20/22/23/24,
not source evidence, tools or budgets. This resolves current-looking repeated failure
presentation, not the model's demonstrated misreading or the candidate's semantics.
Keep rows 40/41 and preceding experiments read-only. Row 41 observes rechecking and
an evidence-supported repair, but does not isolate why this behavior changed. Any
next experiment needs a separate defined question and exact approval; no row 44,
new paid comparison, retry/resume or candidate execution follows automatically.
Older row-40 prohibitions below describe earlier approval boundaries, not a new run.

V31 resolved successful mutation feedback's pre/post identity ambiguity.
Use the completed candidate in the result workspace hash and name the original baseline
explicitly. Preserve pending/completed replay, typed rollback, source/check/note identities,
input shapes, action masks, voluntary stop and all historical bytes. Row 38 shows the
ambiguity in all four mutation outputs, but does not establish it caused the unchecked
final stop. Current-diff NOT_RUN and run_check guidance were already correctly delivered.
Local validation establishes identity consistency, not improved model decisions. The
separately approved row 39 verifies actual pre/post identity delivery and final rechecking,
but introduces a new control-flow bug and exhausts accepted edits. Preserve that distinction;
do not infer a causal improvement from one row. Row 40 later received its own exact approval.
No historical candidate execution is authorized.

The row-39 provider-free follow-up finds no new delivery or scope-arithmetic defect.
External Git/AST comparisons show the assignment can sit outside the guard within 50
diff lines, including a multiline form after removing one added blank line. This is
layout/scope evidence, not a passing candidate. All 572 observed lines, bytes/mode checks,
permissions and reuse guidance reached the first edit. Turn 6's claimed `create_dir`
inspection actually starts in `makedir`; the called `create_dir` implementation was not
read. Conversely the full higher-level `makedirs`, including Windows errno translation,
was delivered but bypassed by the new loop. Distinguish unrequested evidence from lost
projection and observed requirements from preserved behavior. Keep the harness fixed;
do not infer that forced notes, generic extra prompt text or a semicolon ban solves this.
Any model/prompt comparison or row 40 still needs its own exact scope and approval.

The row-39 next-action pilot was prepared in
`C:\pt\pl39-decision-design-a`: before turns 6/21/32, same model, medium versus high,
one fresh response per cell (six total), unchanged native histories/tools/output cap.
Only next-response effort differs; earlier reasoning remains medium in both arms.
The user's subsequent go-ahead by reference authorized exactly that six-cell pilot,
collected as `run_dev_sample_789ffee05f9d4473` in `C:\pt\pl39-decision-live-a`:
six counts/responses, $0.392849400, 51.657s, SAMPLES_COLLECTED, zero tool executions.
All responses completed; 32 journal events, 20 CAS objects, six exact ordered request
identities and six encrypted continuation/action links verify. Assistant static facts
were fixed before unblinding under `C:\pt\pl39-decision-review-a`; no judge call ran.
Both C1 reads target the stated `_path_components` helper. C2 high proposes 44 diff
lines versus medium's 49, but both use the leaf mode in every component-creation call;
unobserved helper behavior is uncertainty, not automatic semantic FAIL. Both C3 samples
produce the identical 49-line candidate with `next_dir` assigned inside the one-line
error guard, skipping normal paths. Separate Git blobs/AST establish counts and block
structure, not task acceptance. Rubric grading stays NOT_ASSESSED; acceptance/safety
are NOT_RUN. Do not infer an effort win rate, agent improvement or a default change.
Next work must be separately scoped; no additional paid pilot, tool execution or row 40
is authorized. Keep this receipt distinct from preparation and provider-free tests.
The subsequent go-ahead authorized fresh-state input/rubric preparation only, under
`C:\pt\pl39-fresh-state-design-a`. `diagnostics/fresh_state_design.py` is an offline
prepare/validate helper, not a collector or production compactor. At pre-turn-32,
A retains the exact original medium wire request. B preserves every latest public
state field and all 32 public calls/results as quoted data, materializes 665 current
observed source lines through existing backward-reference validation, and replaces
native history with three messages. Keep core coding instructions/task/settings/tool
order unchanged; only the context-format suffix describes the different data layout.
Do not read task files, summarize source with a model, use future outcomes or insert
repair hints. Public hypotheses remain in the archive. Current bodies deliberately
also remain there; no claim of minimal serialization or memory-free reasoning follows.
B has no encrypted/native continuation; A remains intact per the normal API contract.
The intervention bundles reasoning reset, repeated-state removal, source access and
message representation, so do not attribute a future difference to any single factor.
Packet hash is `sha256:1839a26def6adea31a288ccf2c084d8a77b80b166039e3491dffd141cbb1d8d7`;
preparer hash is `sha256:3632c6fc93743b8865025cd89f0c785bd1149bb9b03badb76454c08beba2aaa2`.
Serialized request sizes are 684,213/265,083 bytes, not newly counted tokens. Preparation
uses zero key/provider/count/tool calls. 28 new regressions plus sampler/docs/mock E2E
pass 71 cases in 37.68s; Ruff passes. Mock acceptance is not comparison-arm acceptance.
The subsequent implementation go-ahead adds `diagnostics/fresh_state_sampler.py` and
provider-free tests, not paid execution. It uses the shared one-response engine with
the separate A1/B1/B2/A2 protocol (both medium); six-cell and dev/resume entry points
still reject the new packet. No runtime change or live row 40 is authorized.
The new exact approval binds the prepared packet, source design and collector content
hash over all three diagnostic modules. Keep the preparer and both frozen request
artifacts byte-identical; reconstruct/validate before claiming a fresh external result
root or loading credentials. Existing receipts retain their old sampler hashes.
Require `--approve-four-responses-zero-tools` rather than interpreting the old six-cell
flag. The subsequent approval authorized one now-completed collection, recorded below;
it is not authority for another. Validate is credential/provider/count-free.
Fresh B has no historical count. For this protocol only, reserve each future response
at the enforced 272,000-input-token admission limit plus the full 25k output ceiling.
Count the current request immediately before create; reject above-limit input or
insufficient $1.20 cap before generation, without truncation or capacity reduction.
The bound is not a token estimate or a measured price; review official rates on the
execution UTC date. All four requests retain their exact frozen object/property order.
Persist replicate numbers with arm/anonymous ID only in the journal; public review
omits those labels. Never chain samples, execute tools, correct, judge, retry or resume.
Reuse durable usage-before-continuation and whole-pilot uncertainty/deadline stops.
`inspect` reads either diagnostic kind without changing bytes or invoking a provider.
The collector content hash is
`sha256:6e373bf4028426e39c2f4a6b27f0803e6311991c4d4029cd5252355ab2c58d0a`.
33 new tests plus the old sampler/preparer, docs and mock E2E pass 104 focused cases
in 61.24s. The remaining 46 files pass 714 cases / four real-Docker opt-in skips in
six fresh `C:\pt\pl39-fresh-collector-full-a{1,2,3,4,5,6}` roots, longest 107.53s.
Combined coverage is all 50 files: 817 unique passed, four skipped; one mock test is
repeated across stages. Ruff passes. The staged sequence is longer than two minutes.
Actual frozen-request fake collection at `C:\pt\pl39-fresh-collector-smoke-a` preserves
ordered bytes; the nested counts/cost are synthetic. A report-writer error was fixed
through read-only inspection, not recollection. Separate dev mock smoke at
`C:\pt\pl39-fresh-collector-dev-smoke-a` reaches isolated task acceptance PASS / safety
NOT_RUN, four mock turns/five tools and no provider calls. No live/arm success follows.
The later exact approval by reference completed the four-response comparison on
`35f940d5`: `run_dev_sample_1272d5c8122c47cf` in `C:\pt\pl39-fresh-state-live-a`, four
counts/completed responses, zero tools, $0.195174300 and 36.344s. Official Standard
prices were reviewed on 2026-09-07 UTC. The frozen packet and source hashes still match.
Before unblinding, public static observations were fixed under
`C:\pt\pl39-fresh-state-review-a`; 22 journal events, 12 CAS objects, four exact ordered
requests and encrypted continuation/action links verify. A1 proposes a 49-line
candidate with next_dir assigned inside the error guard; A2's 48-line proposal moves
assignment outside it but checks the current parent too late to prevent the observed
broken-link child creation failure. Both observations are static, not test results.
B1 rereads 53 current wrapper lines and asks for 56 unobserved helper lines covering
both public traceback sites; B2 rereads 55 current wrapper lines. Do not label a
deferred read as a failed repair or infer source loss from a request to reread it.
Actual input counts are A 153,464 and B 66,054 (56.96% lower); cache state also varies.
The two draws per arm and bundled context intervention do not identify a single cause
or prove improved agent behavior. No output ceiling exhaustion occurred. Full tool
admission, task acceptance and safety stay unassessed/NOT_RUN. No default/context
change, further sampling, candidate execution, retry/resume or row 40 is authorized.
The packet remains PREPARED_NOT_EXECUTABLE; preparation does not grant paid authority.
The latest follow-up request targets all four stored C3 responses through their public
tool-feedback loop, not another next-action draw. `diagnostics/fresh_state_rollout.py`
is a separate, non-resumable diagnostic driver. Preserve the exact frozen seed inputs,
continuation/action identity, and checkpoint bytes in four independent external Git
clones. Label imported journal events as inherited; their provider usage is not new
billing. Restore 31 prior calls / 32 actions / 3 accepted mutations; each reused seed
consumes the next model step, then permits at most eight new responses. Keep v31 policy,
gateway, source projection, checks/probes and full 25k ceiling unchanged. Both arms
receive the same short current-state-format notice; all new native reasoning and
call/result items continue normally. B's old public archive remains quoted historical
data; do not regenerate it from future outcomes or reset reasoning every turn.
Round-robin A1/B1/B2/A2 shares one $1.20 cap with JIT full-ceiling admission.
This does not reserve a complete successful trajectory; record cap-truncated outcomes
as censored. Stop all on count/provider/billing/continuation or cleanup uncertainty.
Branch clocks exclude waiting on other branches, with an additional 1,800-second
experiment deadline. Stop at public finish or normal policy terminal; no hidden
evaluation, new row 40, restart, seed regeneration or automatic retry. The user
subsequently confirmed this exact new shared paid cap; its authority was separate
from the closed four-response zero-tool approval and is now consumed.
Wiring audit `C:\pt\pl39-rollout-wiring-a` verifies seed prefix/raw-byte/diff identity,
actual admission of A1/A2 edits and B1's 56-line helper evidence gain, with no task-code,
Docker or provider execution. 24 synthetic tests pass in 49.80s at
`C:\pt\pl39-rollout-focus-c`; mock lifecycle results are not semantic arm outcomes.
Final staged coverage is 841 passes / four real-Docker opt-in skips across 51 files:
24 new cases, 103 existing sampler/design/docs cases, and 714 runtime cases. Longest
runtime group is 108.41s; the staged total exceeds two minutes. Ruff passes. Separate
mock `run_dev_9f4f4d7ca0da4dd4` at `C:\pt\pl39-rollout-dev-smoke-a` reaches isolated
acceptance PASS / safety NOT_RUN, four turns/five tools/one mutation, zero cost. Preserve
the distinction between this mock and the subsequently executed paid follow-up.
Owned files, frozen task/history, 152 run files and 175 preexisting
untracked entries retain their before-validation identities.
The four-branch follow-up is complete at `C:\pt\pl39-rollout-live-a`, reviewed read-only
at `C:\pt\pl39-rollout-review-a`: ten new counts/responses, fifteen tools, six public
checks, zero probes/finish/private evaluation, $0.542493150, 177.172s. All branches
stop at LIMIT_REACHED solely on accepted-mutation exhaustion; do not restart them.
A1 introduces an uninitialized `next_dir`; A2 retains two original broken-parent
failures. Both B branches receive 57/50 or 56/50 scope rejection, then converge on
the same 49-line helper-delegation patch. Original four failures disappear, but the
unconditional `exist_ok=True` loses leaf-link EEXIST semantics and adds two regressions.
B's parent check passes; private acceptance/safety remain NOT_RUN. This is not a
validated default fresh-state win: two samples/arm, one checkpoint, bundled reset
and repackaging, and scope feedback before the pivot. B2 needs no new helper source
to reach B1's patch. Memory updates remain null and final failed checks have no later
inference. Do not attribute non-repair to ignoring an error the model never received.
The subsequent v32 implementation fixes public check output truncation/exception parsing.
Captured B stdout starts `turn:` after cutting a `NoReturn:` signature to 12,000 chars;
the broad exception regex invents `exception_type="turn"` while the gateway reports
the sandbox's `truncated=false`. Read-only parser reproduction confirms this separate
metadata defect; it did not cause either B patch. The repair is a separate provider-free
change, not part of the completed comparison. Keep old evidence immutable,
preserve caller/leaf semantics in agent-behavior diagnostics, and do not add masks or
increase limits on the strength of this small comparison.
The earlier six-cell implementation is `diagnostics/decision_sampler.py`, outside
the unchanged v31 runtime content set. Run it as a module from the checkout. `validate`
reconstructs hash-bound requests without a key/client; `collect` requires explicit
six-cell/zero-tool authority plus packet/sampler/price hashes, exact credential path,
new external result root and the shared cap. Same-UTC-day price review is an operator
attestation, not a fetched quote. The supplied adapter factory is an offline test seam,
not a provider CLI mode. Never invoke the real path for provider-free validation.
Keep full 25k output capacity for every remaining cell: reserve historical inputs,
recount each current request just before generation and stop if it no longer fits.
The driver reuses the adapter, ledger, native continuation helpers and DevJournal;
persist usage before continuation/public artifact processing. Return only selected
public actions and encrypted reasoning artifacts, never plaintext reasoning/summary
or a raw SDK exception body. No selected tool, correction, evaluator or judge runs.
Exclusive root creation forbids same-root concurrency/retry. There is no sampler resume:
`inspect` only reads terminal or interrupted/unknown receipts and never changes bytes.
Review artifacts omit arm/effort/cost/latency; journal keeps the unblinding map and
independent display order. Batch-shape validation is not full gateway/rubric acceptance.
Keep schema/property order in count/dispatch/capture: canonical content hashing sorts
object keys and is not evidence of order preservation. The diagnostic request artifact
and a separate ordered-request hash preserve it without changing the original content hash.
The new 39 fake-client regressions cover uncertainty, identity, privacy, fixed reservations,
deadline and crash paths. Do not infer model-quality evidence from fake decisions.
Final full validation: 756 passed / four actual-Docker opt-ins skipped across 48 files
in six new `C:\pt\pl39-sampler-final-b{1,2,3,4,5,6}` roots (longest group 116.62s).
Fake collection of the six actual frozen requests finishes under `C:\pt\pl39-sampler-smoke-b`;
its counted usage is simulated, not billed. Existing dev-head smoke at
`C:\pt\pl39-dev-smoke-a` still reaches isolated task acceptance PASS / safety NOT_RUN.
Never use terminal resume or normal repeat=1 as a six-branch shortcut. Reviewer rubrics
and future outcomes stay out of model input. Grade deferred actions as unassessed where
appropriate, not FAIL, and do not call three correlated single-sample comparisons an
agent success rate.

V30 makes current path permission and source-note expiry explicit at the
existing evidence/action boundary. Reuse the gateway's permission matcher in the source
catalog; attach expiry to its mutation even without a memory update; reference an already
delivered exact receipt instead of re-emitting historical success in the current view.
No tool schema/order, action mask, source admission, note lifecycle, limit or task changes.
Row 37's read-only analysis found 13 inspections with new coverage, three zero-match
searches and two covered-only inspections, not 18 proven wasted actions. Notes were first
requested at turn 23, so their later rejection cannot explain earlier exploration. Turns
26/27 update IDs expired by turn 25; all four findings reject as unknown IDs while other
annotation fields apply. Current IDs and rejection guidance were delivered. Re-emitted
historical receipts and conditional native expiry feedback are concrete presentation
costs, not proof of why the model repeated those IDs. Do not mandate notes or tighten
inspection limits on this evidence. Preserve prior native prefixes and all historical
run bytes. Separately approved rows 38 and 39 are recorded below; later rows require fresh
exact approval. Compare the model's current-failure assertion after an unchecked repair with
the actual historical-failure and recheck guidance before proposing another mask or obligation.

Row 39 `run_dev_eaad5c70be16434f` on `dfb3f8e9` ends at `LIMIT_REACHED`: 33 model/count
calls, 34 tools, four accepted mutations, $0.712855950, 360.375 active seconds. Rejected
proposals at 16/19/25 are path/anchor/scope failures; scope rollback correctly reports
47 baseline lines, 51 candidate, 50 limit. Accepted edits occur at 21/23/26/32. The first
two public failures concern bytes paths and intermediate mode. Turn 27's contract passes;
turn 28's regression fails four exception cases (513 passed/570 skipped). The final edit
compresses a parent guard and `next_dir` assignment onto one line. Saved source and AST
confirm that the assignment is accidentally conditional. Turn 33 rechecks this diff and
fails 21 cases with UnboundLocalError (496 passed/570 skipped). After that failure, zero
accepted edits block minimum completion; seven model/66 tool calls remain. No additional
dispatch occurs. This differs from row 38's unchecked voluntary stop, and does not justify
a mandatory check, stronger mask or scope increase. The final 49-line diff has regression
FAIL/contract NOT_RUN and no submission or isolated evaluation. All four v31 mutation
receipts/native deliveries match baseline and completed identity. All 99 saved artifacts,
33 completion projections, 32 prefixes, 33 stored/32 replayed continuations, 83 permission
entries and five execution policies verify; five owned containers are absent. Eighteen
inspections add coverage, three are covered-only and one is zero-match; all memory updates
are null and no probe ran. Runtime and protected prior bytes are unchanged. The final hash is
`sha256:26e28fec2ef8e063037a97f78a3dbd2fb32999a34a94b5016eb88c5b5c6f6341`.
Keep this run read-only; do not repair/recheck its candidate, retry/resume or start row 40.

Row 38 `run_dev_91f8c05b570c439b` on `2c303bfc` ends at `AGENT_STOPPED`: 20 model/count
calls, 22 tools, four accepted mutations, $0.380645550, 198.859 active seconds. Turn 11
attempts the read-only helper despite delivered public constraints and v30's permission
label. Accepted edits occur at 14/16/17/19; contract failures at 15/18 concern raw parent
traversal and intermediate mode. The last edit addresses parent mode, then turn 20 stops
without checking it. Both current checks were NOT_RUN, run_check was offered and explicitly
recommended, and the old failure was historical/awaiting_recheck. Minimum completion was
three calls with 21 model/79 tool calls left at input construction; only mutation allowance
was exhausted. Do not report the final candidate as a measured check failure or infer why
the model disregarded the delivered distinction. Turn 17 also claimed continued failure
without a check after turn 16. No submission, isolated acceptance or safety evaluation ran.
All 60 context/input/continuation artifacts, 20 completion projections, 19 prior prefixes
and 20 stored/19 replayed encrypted continuations verify. All 36 source permission entries
match policy; every memory update was null, so the changed note paths were not exercised.
Twelve inspections add coverage, one is covered-only; no zero-match or cache hits occur.
Final input: 99,855 tokens; newest state: 11,363 bytes; largest output: 8,439 tokens.
The unverified final 39-line diff hash is
`sha256:12c54957d4c994fea756c811dcb18c525415cd17a0d20675ed04478905f5dace`.
All three owned probe/check containers are absent and protected prior bytes are unchanged.
No historical candidate execution/repair, retry/resume or next live row follows automatically.

Row 37 `run_dev_36024bd4361343dd` on `2a4cb654` ends at `EVALUATOR_PASS`, task acceptance
PASS/safety PASS, still `official=false` and `claim_eligible=false`: 28 model/count calls
and tools, two accepted mutations, $0.651385650, 308.483 active seconds. Turn 11 targets a
disallowed helper; 20/21 exceed the 50-line scope at 65/54 lines. First accepted edit at
22 passes the contract at 23 but fails one public macOS broken-link/trailing-separator
regression at 24 (516 passed/570 skipped). Turn 25 repairs that branch; 26/27 recheck both
current-diff obligations (regression 517 passed/570 skipped), and 28 submits. No stop or
probe ran. Four annotation attempts yield two applied and two partially applied receipts.
Native mutation outputs reference four of eight unchanged spans per edit, retaining
726 inline source bytes each: 34,631 -> 23,533 result bytes overall. Exact source bodies,
post-images and prior native prefixes verify; smaller output is not causal success proof.
All 84 context/input/continuation artifacts, 28 completion projections, 27 unchanged
prefixes, 28 stored/27 next-turn encrypted continuations and the 321-event journal verify.
Last input: 139,707 tokens; newest state: 13,639 bytes; largest output: 10,906 tokens.
The checked/submitted/isolated-applied 48-line patch hash is
`sha256:50de2cf13d33f02ef5eef62e87cad02f3ae263ba14f47170978b816844d852c4`.
All seven owned public/evaluator containers are absent. Protected prior bytes are unchanged;
no private evaluator output enters the episode. Do not treat this single familiar task as
generalization or infer that the unexercised stop/probe changes were validated live.

V28 separates probe execution from unassessed behavior in model-facing
results and distinguishes submission eligibility from semantic confidence. It adds a
bounded, source-linked observation excerpt without changing tool shapes/order, masks,
budgets, note obligations, execution policy or submission admission. No task-specific
counterexample or hidden information enters prompts. Row 35's read-only analysis found
relative/absolute leaf-mode comparison and existing-leaf-file error defects in the
submitted implementation. Its corrected Windows probe doubled separators and exercised
the delegation return, not the new traversal body, then its decision extrapolated to
POSIX/modes. The line feedback reached the next native input. All 23 memory updates were
null: non-use, not lost storage. This identifies public defects and overbroad interpretation,
not the exact private failing assertion or a proven cause of model behavior. No historical
candidate rerun/repair is authorized; row 36 received the subsequent exact approval below.

Separately approved row 36 on `9d070a9c`, `run_dev_ef0c30a81dd848eb`, ends at
`AGENT_STOPPED`: 22 model/count calls and tools, four accepted mutations, $0.533869800,
210.968 active seconds. The first edit follows 11 inspection turns. Public bytes and
parent-mode failures prompt repairs; the contract passes at 18, then regression fails
five cases at 19. Turn 20 applies the final repair, but 21/22 stop without rechecking.
The first stop incorrectly cites action IDs as source spans; the second uses no spans.
Both actual native states show two current NOT_RUN checks, historical/awaiting-recheck
failure and an explicit run_check instruction despite zero edits. Before turn 22,
19 model calls/79 tools remain and minimum completion needs three calls; run_check is
available. The stop's current PASS/FAIL claims reuse the previous diff's results.
Do not report the untested final candidate as still failing, infer private reasoning,
ban voluntary stops, or attribute this solely to memory/prompt design from one row.

All 22 completion/currency projections, 66 context/input/continuation artifacts,
21 unchanged prefixes and the 247-event journal chain verify. All responses complete
with reported current_turn; 22 encrypted continuations are stored and 21 are replayed
once. The last input is 135,822 tokens; its newest state is 10,867 UTF-8 bytes.
All four checks collect public execution feedback; policy hashes verify and all four
owned containers are absent. The final unsubmitted 34-line diff hash is
`sha256:79074e915e8de9967e2c76fd8ffd6c78ccb7f9d66cc45635b136af7cc936b301`.
No notes, probe, finish or isolated evaluator run. The new v28 probe observation and
ready-submission guidance paths are unexercised, not validated as effective. Existing
protected bytes remain unchanged. Subsequent read-only diagnosis confirmed repeated
mutation source and a remaining public Windows file-parent error branch untouched by the
last repair; it did not re-execute the candidate or establish the model's private cause.
V29 addresses concrete interface costs, not a proven fix for premature stop. No candidate
recheck/repair, retry/resume or row 37 is authorized by this observation or local change.
A new live row requires separate exact approval.

V27 preserves a snapshot-derived completion view through final native
projection and labels historical check credit explicitly. Descriptions clarify
`finish_task` submission versus `stop_task` abandonment; tool shapes/order, voluntary
stop, masks and budgets stay unchanged. Separately approved row 35 on `d1660947`,
`run_dev_38e45369894f43b1`, reaches submission but ends at `EVALUATOR_FAIL`, acceptance
FAIL/safety PASS: 23 model/count calls, 25 tools, three accepted mutations, $0.510596700,
274.327 active seconds. Eleven inspection turns precede two rejected proposals
(wrong helper path, then 58/50 lines) and the first accepted edit at turn 14. Public
contract failures at 15/17 prompt direct repairs at 16/18. Two final-candidate probes
follow: an invalid raw Windows-root string fails compilation with unknown execution
feedback; the corrected probe exits normally with collected feedback. Public checks pass at
21/22 and finish follows at 23. No stop or extra model call is forced by guidance.

All 23 native completion/currency projections, 69 context/input/continuation artifacts,
22 unchanged input prefixes and the 264-event journal chain verify. The 41-line final
diff in `pyfakefs/fake_os.py` is identical through checks, submission and isolated
application. All nine owned containers are absent. Hidden acceptance fails while
regression/policy and safety pass; do not reinject private evaluator material. Final
public execution feedback leaves nine changed executable lines unobserved, which alone
does not locate the hidden failure. No prior PASS was invalidated by a later edit in
this row: it is not a controlled replication of row 34 or proof of the guidance's
causal effect. Its subsequent read-only analysis motivated the approved v28 follow-up
above, not an automatic historical repair/recheck. Row 36 required the separate exact
task/model/reasoning/credential/repeat/cap/probe/state-root approval recorded above.
All terminal rows stay immutable.

The earlier v26 seam exposes current changed-line execution evidence from public checks/probes,
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
The next diagnostic seam was to distinguish historical PASS from current completion and
understand completion-versus-stop selection without inferring reasoning or adding a stop ban.
This observation alone does not isolate prompt/history causality. Do not resume, repair,
run a post-terminal check or execute another row without new exact authority.
The subsequent read-only diagnosis finds that `compact_model_state`'s protocol-only
rolling-card filter also removes the check card's unique remaining-check instruction:
present in the turn-23 audit context, absent from all native non-reasoning items.
Current NOT_RUN/remaining IDs survive. The v26 `recent_checks` has diff hashes but no explicit
historical PASS label; this is separate from correct diff-bound submission admission.
Preserve voluntary stop while clarifying that no further edit is not task completion.
All 65 existing focused tests pass but miss that final guidance-delivery boundary.
See current status for the diagnosis and its causal limits. V27 repairs this delivery
boundary; it does not establish which presentation detail caused the live decision.

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

Latest adapter-only v37 receipt: `C:\pt\validation\native-compact-adapter-20260913`.
Runtime `sha256:15b7fb6ce5168931cd82865deb1bc8adce519c441963408522754437abd3ad9b`;
surface remains `sha256:cb6763e5b863adbd7517dc3da2e44ada6b918feea38de3676578d359092a760c`.
60 new adapter cases PASS/9.586s; 100 compact/transport compatibility cases
PASS/30.395s. Four sorted-stride groups cover all 90 files exactly once:
431/506/398/424 PASS, four real-Docker opt-in skips, in
297.067/362.932/290.525/280.210s. Focused verification meets two minutes, full does
not. Ruff PASS. Mock `run_dev_702e01bb86114453` uses the opt-in snapshot window and
reaches isolated acceptance PASS/safety NOT_RUN in 4.628s, zero provider/count/cost.
The saved actual compact window (23 items/22 public messages) validates unchanged;
this is compatibility, not a new provider experiment or native resume. No actual
compact, provider, count or Docker operation. Preserve the reports and smoke state;
recycle only the six owned adapter pytest roots after checking completed processes.

Latest v37 receipt: `C:\pt\validation\native-window-20260913`. Focused 138 cases
PASS/61.77s (`native-window-focused-green-20260913.xml`); Ruff and three docs checks
pass. Four sorted-stride groups select all 89 test files exactly once: 491/360/451/397
PASS, four real-Docker opt-in skips, in 382.43/216.70/324.59/276.08s. Full validation
does not meet two minutes; focused validation does. Preserve the initial red reports:
seed CAS pretty-vs-canonical serialization caused eight managed recovery failures;
one test omitted the pricing argument and three CLI tests mocked a lazy import at
the wrong module. The canonical seed writer and test doubles were fixed; no gate
was relaxed. The final runtime stays
`sha256:0fa12e23139f893cff734664c7b56760d853916cc251475a1521e16b9ca2e5a1`;
v37 surface is `sha256:cb6763e5b863adbd7517dc3da2e44ada6b918feea38de3676578d359092a760c`.
65 old inputs preserve source/native/current-state/public-observation inventories;
the second replay and all 4,571 selected historical/user/task/external file hashes
match after testing. Mock `run_dev_91de969f3e434039` under
`C:\pt\validation\native-window-smoke-20260913` uses the new CLI option and reaches
isolated acceptance PASS/safety NOT_RUN, four mock turns/five tools/one edit, zero
provider/count/cost. No compaction, real Docker, live-model quality or hidden pyfakefs
claim follows. Keep reports and this smoke; recycle only the owned pytest roots.

Latest v36 receipt: `C:\pt\validation\repair-recheck-20260912.md`. Eighteen focused
repair-recheck cases pass in 62.96s; 68 compatibility/docs cases pass in 86.25s;
Ruff passes. The full four-way sorted-stride selection covers all 79 test files:
1,425 passed / four real-Docker opt-in skips after replacing three affected files'
outdated expectations with the green compatibility receipt. Preserve initial red
receipts; four failures were the old surface hash and frozen-runtime admission
expectations, not authority to loosen runtime gates or rewrite frozen packets.
Longest full worker 298.86s; the overall cycle exceeds two minutes.
Runtime is `sha256:28f08d7c8d20f0f77b900cffe2e1a46101f9f0ba4c7ddb7fd666e63d89079640`;
v36 surface is `sha256:e02c52b592502dfe3796773c72f0b13482840575fdee16cf0aecfdc21e90f50c`.
CLI opt-in smoke `run_dev_bb4e471f35954f76` at
`C:\pt\validation\repair-recheck-smoke-20260912a` reaches isolated acceptance PASS /
safety NOT_RUN, four mock turns, five tools, one edit, zero count/provider/cost.
An initial edit without current failure correctly creates no child check. Synthetic
repair tests separately verify PASS/FAIL child feedback, six crash points, no extra
model call, last-mutation recheck before horizon, exact envelope and uncertainty stops.
No new live-quality, hidden pyfakefs or safety claim follows.

Prior v35 reliability receipt: `C:\pt\pl-fixes-final-b` on code/test commit
`b0da0e7`, all 63 test files, 1,108 passed and four opt-in real-Docker skips; Ruff
passes. Three-worker full pytest plus preservation is 225.594s; each focused group
is at most 115.51s. Do not call the whole cycle under two minutes. Initial test-double
deadline/signature/identity mismatches are fixed in tests, not runtime fallbacks.
The final runtime hash is
`sha256:a3d7f3c00ffc7d534b434eb197366da241228d4906d997084b9d8094c39526f1`;
tool surface v35 is
`sha256:7873a505e3ef4ecb1c32e268209b46e5e3dc3cf9538c9ce58342d8fbabbc84cd`.
Mock `run_dev_5efcad90f9ca4cdc` at `C:\pt\pl-fixes-smoke-a` reaches isolated
acceptance PASS/safety NOT_RUN with four mock turns, five tools, one accepted edit,
zero cost and matching checked/submitted/applied patch hash. No provider/real Docker
execution or agent-quality claim follows. Historical state and user-owned files are
unchanged. Detailed red/green and design-boundary notes are external at
`C:\pt\pl-fixes-review-a\implementation.md`.

V34 passes Ruff, 80 focused memory/feedback cases in 28.99s, nine final wire/compression
cases in 0.14s and both corrected legacy expectation cases in 0.74s. Every one of 54
files is represented once in the final selected nine groups: 915 passed / four real-
Docker opt-ins explicitly disabled. Use `C:\pt\pl34-memory-a\test-groups.json` (v33
partition plus the new test in group 7). Final evidence selects `final-1.xml` and
`final-8.xml` from fresh `C:\pt\pl34-full-b{1,8}`, and `full-{2,3,4,5,6,7,9}.xml`
from `C:\pt\pl34-full-a{2,3,4,5,6,7,9}`. The initial failures were an old prose string
and a full-schema hash including descriptions, not changed runtime behavior. Runtime
stays fixed; only those two expectation assertions change before their groups rerun.
Longest group command is 119.83s; do not claim the full staged cycle fits two minutes.
Mock `run_dev_f378a3d7f2724dde` at `C:\pt\pl34-smoke-a` reaches mutation/check/finish/
isolated acceptance PASS / safety NOT_RUN in 5.26s, four mock turns, five tools,
one accepted edit, zero count/provider/cost. Runtime is
`sha256:1cd81f909921c3c8ef34c0452b35db32a67421e3b45d42e525dfac057f7c53ea`.
The ordered structure, non-memory descriptions and surrounding prompt match v33;
the memory block is 3,368 -> 2,346 chars and schema 4,047 -> 3,149 canonical bytes.
Those reductions are not token/cost savings or a live memory-quality result.

V33 passes Ruff and 69 focused repair/recheck/identity/tool/prompt cases in 103.49s.
All 53 files run once on the final runtime in nine balanced fresh external roots
`C:\pt\pl33-final-b{1..9}`: 906 passed / four explicitly disabled real-Docker opt-ins.
Use `C:\pt\pl33-feedback-a\test-groups-final.json`; the longest group is 117.99s.
Each group meets two minutes, not the entire staged sequence. The 19 new cases
cover exact current diagnostics, pending historical/unbound focus, complete receipt
identity and fallback, recheck PASS/FAIL, optional edits/parallel reads, rejection,
native-prefix preservation, restart/action replay and privacy. Mock
`run_dev_47b590d48d744c5e` in `C:\pt\pl33-smoke-a` reaches mutation/check/finish/
isolated acceptance PASS / safety NOT_RUN in 5.70 command seconds, four mock turns,
five tools, one accepted mutation, zero provider/count/cost. Runtime is
`sha256:0a5a7386b3c2c2251e374815fc62c83663dbbe9650a42722c9ed571fcdd2542d` and remains
fixed during final tests and mock. Saved row-40 input comparison verifies only the
intended field changes, not hypothetical model success; old state is unchanged.

V32 passes Ruff and 46 focused public-check boundary/parser/summary/native/restart
cases in 4.63s. All 52 files run exactly once on the final runtime across eight fresh
roots `C:\pt\pl32-full-final-a{1..8}`: 887 passed / four real-Docker opt-ins skipped.
Use the measured, file-balanced partition `C:\pt\pl32-feedback-a\test-groups-final.json`.
Group 6 takes 120.53s, just above the target; do not claim all groups or the staged
workflow finish within two minutes. Runtime bytes remain fixed during final tests and
mock. Mock `run_dev_54fbfa663cfc46b9` at `C:\pt\pl32-smoke-a` reaches mutation, the
visible check, finish and isolated acceptance PASS / safety NOT_RUN, four mock turns,
five tools, one accepted mutation and zero provider/count/cost. Captured B1/B2 output
reclassification returns AssertionError plus both original public comparison rows;
old artifacts remain unchanged. This verifies feedback, not agent task success.

V31 passes Ruff and 118 focused identity/resume/projection/current-feedback/completion/
contract cases in 95.54 seconds. The first new regression fails on the old workspace
hash before the fix. All 47 files run exactly once across six parallel fresh roots
`C:\pt\pl31-full-a{1,2,3,4,5,6}`: 717 passed, four real-Docker opt-ins skipped. Use the
v30 groups below with `test_dev_mutation_identity_v31.py` added to group 5. The groups
pass 71/77/48/129/187/205 in 85.85/71.97/66.44/72.47/107.86/99.19 seconds. Runtime
bytes stay fixed. The eight new cases cover exact LF/CRLF pre/post identity across
multiple edits, incremental/full diff distinction, crash after admission/replacement/
durable result, replay without duplicate writes, rollback/read-cache preservation and
native/context/restart identity through current-diff rechecking and finish at zero edits.
Mock `run_dev_52c7646bb0b54864` under `C:\pt\pl31-smoke-a` reaches isolated acceptance
PASS/safety NOT_RUN with verified mutation/check/finish identity, four mock turns/five
tools, no provider/count calls and zero cost. Each group and focused validation meet
two minutes; the staged verification/audit sequence is not a sub-two-minute claim.
No old run is rewritten or executed; consistency is not measured model effectiveness.

V30 passes Ruff and 55 focused source/receipt/lifecycle cases in 36.26 seconds. All 46
test files run exactly once across six parallel fresh roots `C:\pt\pl30-full-a{1,2,3,4,5,6}`:
709 passed and four real-Docker opt-ins skipped. Groups pass 71/77/48/129/179/205 cases
in 90.29/75.99/70.22/76.79/84.64/102.93 seconds. The groups are:

- 1: tools, context-v12, recovery-v12, source-rebind-v19.
- 2: runner, state, search-v16.
- 3: resume-v12, input-v12, budget-v16, workflow-v12, parallel-v12.
- 4: verification concerns/flow/identity, check identity, policy feedback, notes feedback,
  note temporal and completion-v27.
- 5: execution feedback, current-feedback-v30, mutation-projection-v29, note lifecycle,
  note ranges and source navigation.
- 6: every remaining test file, including explicitly disabled real-Docker opt-ins.

Runtime bytes stay fixed across all groups. The 28 new cases cover permission equality
with admission, forbidden precedence/case/globs, native/inline/header-only catalog labels,
full exact receipt identity with inline fallback, unannotated mutation expiry, unchanged
and rolled-back sources, LF/CRLF, immutable prefix, later-action non-repetition and
completed-action-before-batch crash/restart without duplicate mutation/provider work.
Mock `run_dev_1277b7cb3db8495f` under `C:\pt\pl30-smoke-a` reaches mutation/check/finish/
isolated acceptance PASS, safety NOT_RUN, in 5.11 command seconds, zero cost and zero
provider/count calls. Each test group and focused validation meet two minutes; the full
staged sequence including smoke is not measured as a sub-two-minute workflow.
Read-only row-37 projection labels wrapper/helper permissions, links both source expiries
to the actual unannotated mutation and references its older 1,018-byte receipt in 139 bytes.
Original source/receipt/journal bytes stay unchanged; this does not establish model benefit.

V29 passes Ruff and 93 focused mutation-projection/completion/recheck/conversation/stop
cases in 25.22 seconds. All 45 test files ran once across `C:\pt\pl29-full-a{1,2,3,4}`:
136/72/155/316 passed, two stale stop-input schema hashes failed, four real-Docker cases
skipped. After updating only those expectations, all 31 affected feedback/projection/docs
cases pass in 10.76 seconds: all 681 unique cases pass across these executions. Runtime
bytes stayed fixed throughout. Groups take 85.48/104.36/62.40/130.94 seconds; do not claim
the full sequence meets the two-minute target. Group 1: tools/context/recovery/source-rebind/
execution-feedback; group 2: runner/resume/input/state; group 3: verification concerns/flow/
identity, check identity, policy feedback, source navigation, notes feedback, note temporal,
completion; group 4: every remaining file. Explicitly disable real-Docker opt-ins.
The 37 new cases cover LF/CRLF, shifted/deleted lines, exact union/gap/conflict/position
proof, bounded byte-beneficial references, backward hash-verified alias chains, inline
fallback, non-projection of unused private admission data, unchanged post-image/receipt,
real multi-edit prefix/restart/idempotency and a completed-action-before-batch crash.
Existing continuation, provider-uncertainty, mutation/check/deadline tests also pass.
Mock `run_dev_3c988fa1ae6d4fdf` in `C:\pt\pl29-smoke-a` reaches mutation/check/finish/
isolated acceptance PASS, safety NOT_RUN, four mock turns/five tools and zero cost in
5.57 command seconds. It shares the tested runtime hash recorded in current status.
The read-only row-36 four-result reprojection reduces 135,440 to 28,572 UTF-8 bytes,
preserving all 4,206 observed path/hash/line entries and the original journal hash.
This is not billed-token savings, semantic success, or authority for a new live row.

V28 passes 68 focused probe-observation/completion/probe/state/contract cases in 38.68
seconds and Ruff. All 44 files were exercised across `C:\pt\pl28-full-a{1,2,3,4}`:
109/84/237/213 passed, one deliberately changed description hash needed an expectation
update, and four real-Docker cases skipped. The runtime was frozen across groups;
the final 50-case recheck/completion/observation/documentation run passes in 20.07 seconds,
including the updated expectation. All 644 unique cases pass across these executions.
Group durations were 54.57/109.40/81.35/139.81 seconds, so the longest exceeds the
two-minute full-suite target. Mock `run_dev_3794b6c0a1414ddf` in `C:\pt\pl28-smoke-a`
reaches mutation/check/finish/isolated acceptance PASS, safety NOT_RUN, four mock turns,
five tools and zero cost. The 17 new cases cover exit-zero false/error output, failed/
unknown/full/zero line observations, bounds/privacy, native delivery, exact replay,
historical currency, no new admission/annotation requirements and generic input guidance.
Row 35's read-only single-result projection adds 789 UTF-8 bytes; native details remain
referenced rather than duplicated in the compact current view. No candidate/Docker/provider
execution is part of that comparison. Prompt length is 7,973 with the 8,007 bound unchanged.

V27 passes 140 focused completion/check-identity/state/conversation/contract tests in
43.65 seconds and Ruff. All 43 test files run once across four fresh external roots
`C:\pt\pl27-full-a{1,2,3,4}`: 627 passed, four opt-in real-Docker cases skipped.
Groups pass 60/68/145/354 in 45.46/103.77/60.63/150.24 seconds. Group 1 contains
tools/context/recovery; group 2 runner/resume/input; group 3 verification concerns/flow/
identity, policy feedback, source navigation, note feedback/temporal and completion;
group 4 contains every remaining test file. Keep runtime bytes frozen across groups.
The slowest group exceeds two minutes; focused tests meet the target. Observed full
suite/mock wall time with read-only review gaps is 162.18 seconds. Mock
`run_dev_ab6896e303234425` under `C:\pt\pl27-smoke-a` reaches mutation/check/finish/
isolated acceptance PASS, safety NOT_RUN, four model turns/five tools and zero cost.
The 13 added cases cover actual native guidance, historical/current/unknown check credit,
restart, unchanged prefix, submission, voluntary stop and stable input shapes/order.
Read-only row-34 reprojection adds 570 UTF-8 bytes to the latest view, preserves the
saved input hash and identifies the missing contract recheck. It does not run the
candidate or prove effective model use. No actual Docker/provider work or row 35 ran
as part of that local validation; the later separate live observation is recorded above.

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
