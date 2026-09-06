# Run and validate

All generated state must live outside the repository. The examples use short
Windows paths to avoid temporary-directory permission and path-length failures.

## Fast local verification

```powershell
$testRoot = 'C:\patchloop-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
uv sync --extra dev --locked
uv run ruff check patchloop tests
uv run pytest tests -p no:cacheprovider --basetemp $testRoot
```

This path uses no provider or Docker call.

Keep runtime files unchanged while tests run, because provenance tests bind their actual
bytes. For a faster complete suite, run the runner/resume tests in one process and all
remaining test files in another, each with a different new external temporary root.
The exact split and latest measured result are in [the internal guide](../.agent/guide.md#validation-checklist).

## Mock end-to-end

```powershell
$env:PATCHLOOP_STATE_ROOT = 'C:\patchloop-state'
uv run patchloop dev `
  --provider mock `
  --task tasks/smoke/csv-quoted-newline/public.yaml `
  --model mock-dev `
  --repeat 1
```

Mock mode forbids credential and cost options. A successful smoke run performs
parallel public inspection, one admitted mutation, a visible check, automatic
full-diff projection, finish, and a separate private evaluation. Its result is
still unofficial.

## Explicitly approved live development

First inspect local prerequisites and the task package:

```powershell
$env:PATCHLOOP_STATE_ROOT = 'C:\patchloop-state'
uv run patchloop doctor
uv run patchloop task validate tasks/dev-train/<task>
```

Then issue one fully specified invocation:

```powershell
uv run patchloop dev `
  --provider openai `
  --task tasks/dev-train/<task>/public.yaml `
  --model gpt-5.4-mini-2026-03-17 `
  --reasoning-effort medium `
  --env-file <credential-file> `
  --max-cost-usd <positive-decimal> `
  --repeat 1
```

That exact command is the development approval for its provider, task, model,
credential file, repeat count, and invocation-wide cap. Live mode accepts only
checked-in `dev-train` tasks. Every active `patchloop/**/*.py`, `pyproject.toml`,
`uv.lock`, trusted `docker/probe_runner.py`, `docker/Dockerfile.sandbox`, and selected
task-package input must be tracked and match HEAD;
unrelated scratch or untracked paths outside those pathspecs are ignored. The
credential file may contain only one `OPENAI_API_KEY=...` assignment. It may be the
ignored repository-root `.env` or an exact external path, but it must never be tracked
or committed.

The required evaluator image must already exist locally at the declared digest.
PatchLoop never starts Docker Desktop or pulls/builds an image. Unknown model
pricing fails before dispatch. The adapter counts the actual request immediately
before generation. The desired response ceiling is 25,000 tokens. The Responses API
counts both reasoning and visible output against it; pre-dispatch admission lowers that
ceiling when necessary to stay inside the invocation-wide cap. Every admitted ceiling
is journaled. The adapter uses zero SDK transport retries and stops all remaining
repetitions when count, transport, or billing state is uncertain. Generation and input
counting use the same
`tool_choice=required` contract, so the provider request and the runner's non-empty
tool-batch requirement agree. V22 keeps one active native episode: system instructions,
replaceable harness-state JSON, one stable user task, then all encrypted reasoning,
canonical calls and matching outputs in chronological order. Updating the prefix never
adds a user turn or retains another old state snapshot. History is restored from the
last decision's hash-verified input artifact and extended once, including correction
responses. Existing current-state/source/check validity remains authoritative; historical
native results do not become current PASS. PatchLoop requests
`reasoning.encrypted_content` while retaining `store=false`. Plaintext reasoning,
reasoning summaries, and non-tool response content are not retained or replayed.
`turn_started.native_history` binds item/call/output/reasoning counts and the history hash.
Provider/decision events record `response_reasoning_context` only as `current_turn`,
`all_turns`, or null; no mode is inferred from a ciphertext. GPT-5.4 mini receives no new
reasoning-context setting. The existing token count and invocation cap apply to the whole
input, which can grow despite a bounded retained-source snapshot. No history dropping,
automatic compaction, extra provider call, or larger cap is introduced.
The application still enforces its smaller grammar: up to four reads/searches, or
exactly one mutation, check, enabled probe, finish, or stop.

`run_probe` is off by default. An exact future live authorization must include
`--enable-probes` to add this capability; enabling it also requires the separate clean
Python image in [the probe runtime contract](../docker/README.md) to be present locally.
Preflight verifies that image and the hash-bound trusted wrapper before provider dispatch.
It does not pull/build an image, start Docker Desktop, or fall back to the evaluator image.
The separately approved twenty-second through twenty-fourth rows enabled this opt-in;
rows 22 and 24 used one baseline probe each, while row 23 did not. These observations
do not establish candidate validation by probing; exact results are in `docs/current-status.md`.
The separately approved twenty-fifth row also enabled probes but did not invoke one.
It terminated at the completion horizon after a public regression failure, without
submission or private evaluation. The separately approved twenty-sixth v18 row,
`run_dev_306785d397d640f3`, reached `EVALUATOR_PASS` (task acceptance and safety PASS)
in 28 model calls and 32 actions for $0.432518400. It also did not invoke a probe.
The initial Docker-unavailable read-only preflight made no run/provider call; the user
started Docker before the one invocation. The separately approved twenty-seventh v19 row,
`run_dev_e68682d51d2a4dfa`, used two successful baseline probes but no candidate probe.
It ended at `LIMIT_REACHED` after four accepted mutations and four failed traversal checks:
29 model calls, 30 actions, $0.349973100, no submission or private evaluation. Eleven model
calls remained, but no mutation could repair the current failure. Source/check identity and
native feedback passed the read-only audit; this is not evidence of task success.
The separately approved twenty-eighth v20 row, `run_dev_a01ff61f95be4a57`, reached
`EVALUATOR_PASS` (task acceptance and safety PASS): 20 model/input-count calls, 21 actions,
two accepted mutations, $0.193324200, and 133.016 active seconds. A public intermediate-mode
failure was repaired immediately, both visible checks passed, and finish submitted the
same patch later applied by isolated evaluation. Probes were enabled but unused; no
working note cited a check, so this row did not exercise the v20 check-result label.
Exact replay, native results, note receipts, execution-policy and patch provenance passed
read-only audit. That result and local validation did not authorize a later invocation.
The separately approved twenty-ninth v21 row, `run_dev_7005744ccb5d4cc1`, reached
`EVALUATOR_FAIL`: public traversal and regression checks passed, isolated task acceptance
failed, and safety passed (`PRIVATE_EVALUATION_FAILED`). It used 32 model/input-count calls,
35 actions, one accepted mutation, $0.482969550, and 290.593 active seconds. The first
candidate at turn 27 exceeded scope (60/50 lines); turn 29 accepted a 48-line replacement,
and turn 32 submitted it. Checked, submitted, and isolated-applied patch hashes match.
V21 intent references and exact saved-input/continuation replay passed read-only audit,
but 15 of 30 inspections added no coverage and no probe ran. This does not establish
efficiency improvement or a cause for the different outcome. All 54 prior journal/envelope
files remain unchanged. No automatic repair, retry, resume, or thirtieth live row is
authorized by this result, the implementation, or local validation. All results remain
unofficial; no hidden evaluator output is reinjected into the coding agent.

Tool surface v22 retains bounded run-local verification concerns inside the existing
memory annotation. Inspect `working_notes.verification` for current unresolved IDs and
`memory_update_result.verification` for update outcomes. A source/focus update does not
clear these items, a successful check does not automatically resolve unrelated items,
and a baseline probe cannot resolve a later candidate's concern. Resolution/dismissal
decisions are diff-bound model judgments, not added acceptance checks. Concern state and
ID allocation replay from `working_notes_updated`; malformed annotations do not reject
the main tool action. Null concern ID creates an immutable original `statement`; an
existing `vN` upsert stores its incoming statement as the latest `progress_note` about
that original. A distinct question needs a null ID. Exact repetition of the original
or retained progress yields applied code `unchanged`, preserving state, update time,
and any resolution/dismissal. Changed progress reopens the concern. Old envelopes remain
immutable; v22 does not migrate them and rejects mismatched nonterminal resume under the
existing exact-match contract. No new experiment is automatically executed after a check PASS.

Model-facing inspection feedback uses action-bound decision references instead of repeating
the original basis/goal across tool results, evidence ledger, and recent attempt cards.
The native call arguments retain the exact decision. `delivery` distinguishes
`preceding_function_call_arguments`, `latest_tool_result.inspection_intent` for context-only
delivery, and `journal_only` when an older intention is no longer projected. These are
model-authored pre-observation intentions, not observations or accessible extra tools.
Raw results and original cards remain in the immutable journal; stored context/model-input
artifacts bind the projected delivery. Rebuilding/replaying a current run uses the same
action identities. Source, visible-check output, note receipts, and encrypted continuation
are unchanged. There is no historical run migration or automatic re-execution.

Current GPT-5.4 mini pricing and supported reasoning effort are reviewed against
the official [API pricing](https://developers.openai.com/api/docs/pricing) and
[model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini). Input
counting follows the official
[token-counting guide](https://developers.openai.com/api/docs/guides/token-counting).
Required tool choice follows the official
[Responses create contract](https://developers.openai.com/api/reference/resources/responses/methods/create).

## Submission and evaluation

Public search uses literal queries and case-sensitive, repository-rooted path globs.
Within a path component, `*`, `?`, and character classes match names; a whole `**`
matches zero or more directory components. `**/*` includes root-level files and
`pkg/**/*.py` includes `pkg/module.py` as well as nested Python files. Results retain
the same public/tracked and output bounds. `searched_file_count` counts eligible files
actually decoded and searched, not the total matching files when results are truncated.

The mutation tool is `replace_text`. It names one tracked, existing, allowed path, one
exact current `old_text` occurrence, and the desired `new_text`; it does not accept Git
diff syntax. Prefer a small sufficient unique executable-code anchor instead of copying
unchanged signatures/docstrings; preserve its exact observed line breaks. The gateway
checks that current public evidence covers that anchor,
constructs a bounded Git diff, writes the replacement, and then derives the canonical
full worktree diff used by visible checks and submission. Stale or out-of-range occurrences,
mixed newline styles, non-tracked paths, untracked files, and scope violations fail
closed. A failure after the write restores the exact pre-image, while a crash after an
admitted write is reconciled from its expected post-image hash and admitted path set.
If a valid mutation call fails, its bounded exact replacement, replacement hash, intent,
error location, and typed recovery lineage remain in `last_failed_mutation` across later reads and
resume. Scope failure additionally returns the baseline and complete candidate diff
hashes, line/file counts, their delta, typed actual/limit/overage violations, and
`rolled_back=true`; the failed result's workspace hash is the restored baseline.
A failed proposal is diagnostic state: it does not invalidate that baseline's checks
or require another accepted mutation when the baseline is already ready to submit.
Read/search availability after failure follows the remaining completion budget.
After success, unchanged uniquely occurring
edited-file spans are rebound to the post-image hash, changed pre-image spans are
invalidated, and one bounded replacement post-image span is registered in the evidence
store. Reads and post-images return complete bounded lines, EOF yields no source span,
and CRLF is normalized consistently while raw bytes remain hash-bound. `replace_text`
has no model-supplied evidence-ID field: the gateway verifies a contiguous union of
actually observed current ranges and journals that binding. Unobserved gaps and stale
file hashes still fail closed. `causal_revision` is optional, including after repeated
failure sites. Before writing, admission records the complete expected candidate diff
hash. A crash after the atomic file replacement must reconcile against that exact hash;
an over-scope candidate is restored to the admitted baseline with typed failure evidence.
Tool execution failures are not counted or presented as model protocol violations.
Every tool call must include one bounded public `turn_decision` containing `mode`,
`basis`, an `evidence_goal` only for inspection, and nullable `memory_update`. Its mode must match the actual
tool family. Parallel reads all use `inspect` mode, while their `basis` and
`evidence_goal` may describe different concrete queries or ranges. Each decision
records its action after the preceding public result; it is not a promise about an
unseen result or stored raw reasoning. Action identity binds each decision, while the
operational read cache remains keyed only by the executable request and current diff.
`memory_update` contains up to two findings, each with a statement of at most 400
characters and one or two source-range/prior-tool-result references, plus an open
question of at most 500 characters or null. Only the first non-null update per batch is
validated before tool execution; additional non-null updates produce a bounded diagnostic
and are ignored. Findings have stable run-local IDs independent of their source ranges:
`note_id=null` allocates a new ID such as `n3`; an existing ID updates that note.
`remove_note_ids` explicitly removes redundant IDs when consolidating notes. At most
six findings are retained; unknown IDs or invalid citations produce bounded diagnostics.
For `unobserved_source_range`, inspect `reason` and `range_details`: `never_observed`
means some requested coordinates have no prior public source observation;
`stale_current_range` means prior observations lack a current binding. Historical ranges
are not current text proof. Requested/current/missing range metadata is bounded; no source
body or unknown path is echoed, and no partial finding or compulsory reread is introduced.
Successful exact replacements rebind unchanged complete-line fragments by verified edit
position, not substring guessing, and journal them for identical recovery. Check summaries
retain action ID/check ID/diff together, and concern decisions preserve the actual cited
check ID even though semantic relevance remains model-authored.
Tool-result notes use the result's actual output diff, including the post-mutation diff.
For an executed public check, `evidence[].check_result` stores `check_id`, `passed`, and
bounded `exception_type` from the recorded result. Projection adds `currency` relative
to the current diff (current/historical; unknown if the cited diff is missing). A stored
PASS on an earlier diff never becomes a current PASS. Failed actions/non-checks get no
invented check verdict. Prose is still unverified and may contradict that label; no semantic
rejection or new gate is added. Keep reusable behavior facts separate from status already
shown in `current_public_failure`; refining an ID should refine the same fact.
Invalid notes do not reject that action. A separate `memory_update_result` on the owner
call's native output reports each note's outcome and an actionable error. Its
`scope=before_tool_batch`, `diff_hash_at_update`, and `note_ids_after_update` identify
the update-time state, not IDs still usable after a mutation. The native owner output's
sibling `working_notes_after_batch` reports `scope=after_completed_tool_batch`,
`diff_hash`, `available_note_ids`, and batch-local `expired_notes`. The current context's
`working_notes.available_note_ids` is authoritative for the next update. A successful
annotation can therefore coexist with a subsequent same-batch source-note expiry
without falsely advertising the expired ID as currently available.
The derived context uses a delivery reference instead of duplicating that receipt.
Read output does not echo the unvalidated annotation; original function-call arguments
remain intact for continuation. Before an observation, use an open question or null;
afterward, cite the already returned source/result on a subsequent useful call.
Durable `working_notes_updated` events restore at most six run-local findings and retain
up to 24,000 observed source characters per note outside public projection. Successful
mutations atomically record rebound/expired note state in `action_finished`, outside
the public tool result. Resume replays that recorded state. Uniquely unchanged source
rebinds; changed/ambiguous source expires without resurrection; old tool-result references
are historical. Public `last_source_lifecycle` identifies the action and affected IDs.
Finding `status=current` describes citation currency only; every projected finding has
`interpretation_status=model_authored_unverified`. Prefer behavior-bearing citations and
mechanism explanations, resolve answered questions, and revisit behavior claims after
mutation even if unchanged citations let them survive. No semantic truth check is added.
Allocation, update, removal, and eviction are journaled for deterministic resume.
`memory_update=null` retains the notes and open question; `open_question=null` inside
an update resolves the question. Notes can retain the mechanism, chosen approach, and
unverified behavior without a mandatory plan. This does not enable cross-run memory or
store raw reasoning, and the harness verifies citations rather than interpretation truth.

The public context presents the workflow gate, budget, action horizon, mutation
readiness, mutation scope budget, evidence ledger, and any active mapped public-check
failure before the larger task payload. Its latest three inspection outcomes include
both reads and searches, with bounded queries/ranges, public evidence goals and coverage
results; detailed fingerprints remain journal evidence rather than context repetition.
Immediately before a new model turn, the scheduler captures one coherent public state
snapshot containing the complete diff, actually delivered evidence paths, and visible-check state.
Source projection is selected first: prioritize the failed/current edit, source-backed
findings, then recency; merge overlapping or adjacent observed ranges without filling
gaps. Retained source totals at most 24,000 characters, separately from the exact native
latest tool batch. Omitted observed source is summarized without body text in at most
12 path/hash/range entries plus the full omitted-range count. Readiness uses both deliveries.
Native source ranges, latest mutation
content, and latest check output are not duplicated in derived context cards.
The `observed_source_index` adds at most 16 lexical function/class-header locations
within a 4,000-character bound, derived only from delivered observed current code.
It does not read unseen source, add evidence coverage, or establish a function's extent.
Use it to locate already delivered code; source bodies remain the evidence authority.
Policy derivation and context projection share that snapshot rather than independently
rerunning Git inspection. Evidence validation groups spans by path and hashes each
observed file once. The snapshot is not retained across a tool batch, mutation, check,
or resume reconciliation; the next decision captures fresh workspace state.
`ready_to_attempt` has basis `current_delivered_editable_source_evidence`: non-empty current editable
source is present in this input. Exact replacement coverage is checked at admission;
readiness neither proves that coverage for an as-yet unspecified edit nor claims that
the semantic solution is sufficient. Scope headroom describes the current complete diff; it is not
the replacement line count. The ledger is bounded and deterministic: it merges covered
line ranges by path, retains the latest 12 search observations, adds an aggregate over
the complete search history, and is rebuilt from durable tool results on resume. The
aggregate separates total, zero-match, covered-only, new-coverage, and unique result-
fingerprint counts. It contains neither private evaluator data nor inferred chain-of-
thought.

Tool availability is derived from the workflow gate, current evidence, unexecuted
visible checks, and remaining model/tool budget. Optional inspection stays open while
both budgets have calls beyond the minimum mutation, check, and finish path plus bounded
recovery allowances. One transition model accounts for all checks invalidated by a
repair and for distinct visible-check failures, limited by remaining accepted mutations.
It handles any permitted check order instead of assuming declared order. At
one remaining optional turn, the context marks
`last_opportunity`; at zero inspection slack the inspection tools are removed.
`tools_closing_after_this_turn` previews the actual policy after one read/search with
unchanged evidence, so affected `run_probe` and `run_check` entries are included as well
as reads/searches. It is a conditional notice, not a prediction of newly observed evidence
or a new restriction; action masks and budget rules are unchanged.
Each allowance is consumed only by its corresponding failure, and
both states are reconstructed from durable batches on resume. A source read that is strictly required to
establish a mutation anchor is included in the minimum path rather than treated as
optional exploration. The scheduler recognizes mutation evidence only when a non-empty
current observed source range is actually delivered, not merely present in gateway memory.
Optional edits use the minimum successful post-edit path rather than the protected
failure path: one edit, all invalidated visible checks, and finish must fit both budgets.
`action_horizon.mutation_completion_horizon` separately reports `minimum_calls`,
`protected_calls`, their feasibility with current evidence/capacity, and a warning when
the edit is executable without full recovery protection. These values are also journaled
at `turn_started`. A checked baseline may be fully protected while an optional edit is
not; the two states are not interchangeable. A diagnostic probe's failure does not mark
a required check failed or consume its repair allowance. The agent can choose an
affordable edit based on public evidence without waiting for a registered check to fail.
`completion_possible` requires both remaining budgets
to cover the best-case minimum path and required mutation capacity;
`protected_completion_possible` includes the unused recovery allowances. The legacy
24-turn and three-repair-read fields remain envelope-compatible telemetry and do not
remove tools. Cached or repeated evidence remains diagnostic-only. `new_span_count` is
syntactic telemetry, and `first_search_observation` records query novelty only.
`marginal_evidence_gain` is true only when the result adds a previously uncovered line
from any tracked public source; editable and supporting lines are reported separately,
with the old task-relevant count retained as an editable-line alias. A zero-match or
covered-only result is a negative observation, not new line coverage. Commitment and
coverage plateau signals remain advisory and never remove tools. Repeated source or
zero-match searches can still answer a decision-relevant public question. Successful
mutation or a check/completion transition clears the signal; `stop_task` is always available.
Every inspection close or reopen is journaled as `tool_policy_transition` and projected
once in the public context.
If the best-case minimum path no longer fits the remaining model calls, tool actions,
or mutation capacity, introspection exposes only `stop_task` and the scheduler does not
create another model turn. It records existing `LIMIT_REACHED` with message
`completion horizon exhausted before provider dispatch` and bounded gate, remaining-
resource, minimum-call, and blocker fields. Resume first reconciles any already durable
provider decision or pending batch, then applies this test before a new dispatch.
These output and scheduler semantics are bound by tool-surface identity `v22`; prior
envelopes and journals are not migrated.
One consecutive invalid or incomplete model response receives a correction that
names the current workflow gate, remaining public checks, and only the tools actually
available on that correction turn. If rejected function calls carried encrypted
reasoning, bounded public rejection outputs preserve their call-ID linkage for the
next request. A valid tool batch resets that correction allowance. Provider journals
retain output item counts, types, a shape hash, typed incomplete-reason metadata, and a
continuation artifact reference for diagnosis. A local tool conversion failure additionally
retains only the public tool name, canonical arguments hash, at most four validation field
paths and codes, and a truncation flag. The correction repeats this bounded diagnostic;
raw rejected arguments and validation inputs are not stored. Ciphertext is stored only in
the external content-addressed
artifact store. Missing, malformed, reordered, or action-mismatched continuation
evidence produces `PROVIDER_CONTINUATION_ERROR` before another provider or tool call.
This includes older episode references and the pending decision's saved input artifact;
integrity failure never falls back to a fresh stateless request. Billing uncertainty
retains priority, and already terminal runs retain their existing exact-resume contract.
The same incomplete reason survives decision recovery and is named in correction and
terminal provenance. If no public read, check, or safe scoped mutation can make
progress, the agent may call `stop_task` with a bounded reason. This produces
`AGENT_STOPPED` without submission or evaluation.

`finish_task` becomes available only after every visible check passes on the
current non-empty diff and no non-ignored untracked file remains. The context lists
every current-diff check as PASS, FAIL, or NOT_RUN and separately names remaining
IDs; the `run_check` schema exposes only public checks not yet executed on that exact
diff. A failed check therefore requires a mutation or stop rather than a same-diff
rerun. Current observed evidence allows an immediate exact repair. Source inspection
remains available while budget permits and is required only if the exact edit evidence
is missing. Failure locations do not restrict inspection to that path. The completion
model includes the repair and every visible check invalidated by the new diff; recovery
IDs and total call cost are projected and journaled. A rejected optional proposal can
be abandoned and a still-checked baseline submitted directly.

For a failed registered `python -c` check, `run_check` parses only the already-public
command and bounded public output. A valid `<string>` frame is mapped to its exact
statement and hashed as a semantic failure site; the original stdout/stderr signature
remains unchanged for provenance. A module frame does not prove which other lines ran
through loops or branches, so later-line execution remains unknown. Across distinct
diffs, the context labels the same site, a later/earlier traceback line number, or an
incomparable change without claiming semantic progress from source order. The resulting
`current_public_failure` survives a targeted read and journal hydration, includes the
remaining accepted-mutation count, and clears when the relevant recheck passes. No
private task bytes, hidden path, evaluator output, local-variable capture, or inferred
reasoning enters this card.

One monotonic active-execution deadline covers provider counting/generation and tool
work, including pending replay and visible checks. Remaining time is passed into each
blocking operation. Docker checks carry run/action identity so recovery can reconcile
their execution without launching duplicate check containers. Process downtime remains
excluded from active execution and recorded separately as run age.

When enabled, `run_probe(question, python_source)` uses one model turn and one tool
action only when both budgets retain the protected completion path afterward. Source
is limited to 8,000 characters and 32,000 UTF-8 bytes; execution is limited to 30 seconds
and combined stdout/stderr to 12,000 bytes while collecting output. The shared deadline
can reduce execution time and reserves up to five seconds within the remaining row
budget for cleanup. The host exports current tracked public files, excluding `.git`,
`.env*`, and `.patchloop-hidden`, and rejects symlinks or reparse points. Only this
read-only snapshot and the trusted wrapper are mounted into the clean Python container;
the agent worktree, Git data, credentials, and private evaluator material are absent.
The stable tool description explicitly names `/workspace` as the importable current
public snapshot, including accepted edits, and `/tmp` as writable scratch. It supplies
only base Python and public project code, with no network or dependency installation.
An agent can therefore test a candidate's concrete uncertainty, not just baseline OS
behavior; this remains optional and does not replace registered checks.
The container runs as numeric non-root user with no network, a read-only root, dropped
capabilities, and bounded CPU, memory, processes, and temporary storage.

A probe cannot change the worktree or the required-check status. Its public receipt binds
source, current diff, snapshot, image, profile, action/input, and execution-policy hashes.
Its result can be cited as diagnostic evidence but does not grant source-anchor coverage.
Failure does not require a mutation or invalidate a previously checked baseline.
If a probe lacks a durable result after interruption, recovery confirms cleanup of only
its owned container and may rerun the isolated experiment on the same bound baseline.
This is safe recovery of an isolated experiment, not an exactly-once process guarantee.
Cleanup uncertainty stops further execution. Durable completed results use normal
`action_id + input_hash` replay.

The full submitted patch is stored by content hash. A separate
manifest is atomically recorded before evaluator execution and binds the exact
task bytes, full runtime bytes, model/tool/sandbox identities, visible-check diff,
submitted patch, and changed files. A separate workspace receives that artifact
and private evaluator files; those details are never returned to the agent.

Before creating its workspace, the evaluator compares task ID/version, base,
public/private/content hashes, runtime and tool surface, sandbox backend/image,
and submitted artifact against the manifest. Public summaries expose
`task_acceptance`, `safety_state`, a safe `failure_class`, and
`claim_eligible=false`. `EVALUATOR_PASS` means task acceptance only; it does not
mean an official run or safety PASS.

Enabled-probe manifests also bind image/profile identities, execution count, and
content-addressed public receipts. Before creating a workspace, the evaluator validates
receipt integrity and policy bindings. Missing or invalid receipts produce safety
`ERROR`; a valid receipt showing a requested-policy violation produces `FAIL`. Probe
outcomes never count as required tests. Receipt and execution-policy hashes remain in
provenance even if subsequent evaluation fails. Enabled but unused probes require no
execution receipt, and disabled runs retain their existing sandbox identity.

Task acceptance combines hidden checks, public regression, and scope policies.
Safety is a separate typed axis covering runtime contract, constrained tool
surface, managed workspace, and requested Docker execution policy. Complete
matching Docker evidence is `PASS`, an observed policy violation is `FAIL`,
missing or invalid required evidence is `ERROR`, and an unexecuted local/mock
Docker policy is `NOT_RUN`. Free-form audit prose is not an automatic safety rule.

Each run writes append-only `dev-run-v1` JSONL plus content-addressed artifacts to
the external state root. Operational acceptance requires a durable terminal and
evaluator summary within 30 minutes. Preserve the run directory and do not edit it.

## Resume an interrupted run

Only runs created with a `dev-run-envelope-v1` envelope can resume. Reissue the
original command against the same external state root, add the exact run ID, and
set one repetition:

```powershell
uv run patchloop dev `
  --provider openai `
  --task tasks/dev-train/<task>/public.yaml `
  --model gpt-5.4-mini-2026-03-17 `
  --reasoning-effort medium `
  --env-file <same-credential-file> `
  --max-cost-usd <same-positive-decimal> `
  --repeat 1 `
  --resume-run-id run_dev_<id>
```

Provider, task, model, reasoning effort, resolved credential-file path, invocation
cap, limits, runtime content, sandbox identity, and full task-content identity must
match the stored envelope exactly. Include `--enable-probes` again only when it was in
the original invocation; the probe profile and image are part of that exact identity.
A mismatch returns `RESUME_CONTRACT_MISMATCH`
before a provider call and leaves the journal unchanged. Pre-envelope runs,
including `run_dev_e89e940c0715474e`, are immutable evidence and cannot resume.

Resume takes a run-lifetime execution lock, restores durable cost and counters,
and excludes process downtime from active wall-time while retaining run age. A
recorded model decision continues with the exact stored tool policy and same tool
calls; its encrypted continuation artifact is verified before any tool execution.
Completed actions use `action_id + input_hash` replay, and pending mutations use
reconciliation. A missing or damaged continuation becomes
`PROVIDER_CONTINUATION_ERROR`; an unmatched provider dispatch is never retried and
becomes one `PROVIDER_TIMEOUT_OR_UNKNOWN` terminal. Resuming a terminal run is a
read-only,
idempotent return of its existing public result. The restored protocol counter is
the consecutive corrections since the latest completed valid tool batch, not a
lifetime total.
