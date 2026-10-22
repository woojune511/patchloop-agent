# Internal implementation guide

Companion to [AGENTS.md](../AGENTS.md). [Status](../docs/current-status.md) owns
current facts; source/tests own behavior. Read relevant sections only.

## Choosing the next improvement

Start from observed public failures; separate evidence, suspected causes and alternatives.
Use the smallest diagnostic or change. Memory, planning and gates need demonstrated
benefit. Record significant investigations once in history with problem, evidence,
hypothesis, change, result and next question. Replace stale current status with the
active decision and evidence links. Routine fixes need no comparison process.

## Source map

| Concern | Current source |
| --- | --- |
| CLI and request/default contracts | `patchloop/cli.py`, `patchloop/dev/contracts.py` |
| Loop, preflight, action horizon, terminal handling | `patchloop/dev/runner.py` |
| Pure completion/mutation resource forecasts | `patchloop/dev/completion_budget.py` |
| Public prompt and provider adapter | `patchloop/dev/model.py`, `patchloop/agent/model.py` |
| Tool grammar, observed anchors, edits, checks, finish | `patchloop/dev/tools.py` |
| Audit context and compact public view | `patchloop/dev/context.py`, `patchloop/dev/model_state.py` |
| Native delivery and context policies | `patchloop/dev/conversation.py`, `patchloop/dev/native_sources.py`, `patchloop/dev/segments.py` |
| Notes, concerns, and source currency | `patchloop/dev/working_notes.py`, `patchloop/dev/verification_concerns.py`, `patchloop/dev/source_rebinding.py` |
| Journal/recovery and evaluator completion | `patchloop/dev/state.py`, `patchloop/dev/evaluation_completion.py` |
| Prices and pre-dispatch cost admission | `patchloop/dev/cost.py` |
| Workspaces, prepared inputs, deadlines | `patchloop/repository.py`, `patchloop/prepared_source.py`, `patchloop/git_execution.py`, `patchloop/deadline.py` |
| Registered checks and public probes | `patchloop/sandbox/`, `patchloop/dev/probe_replay.py`, `patchloop/dev/probe_cases.py` |
| Patch/test comparison | `patchloop/repair_verification.py` |
| Task/manifest contracts and isolated evaluation | `patchloop/contracts.py`, `patchloop/task_loader.py`, `patchloop/verifier/` |

Use public task inputs for agent work. Private task material and evaluator internals
never enter coding-agent context, including through diagnostics or repair hints.

Completion forecasts are pure snapshot arithmetic. The runner owns tool admission;
`dev/cost.py` owns provider admission. Preserve exact-envelope runtime identity.

## Loop and mutation contract

Only mutable `dev-head` runs, always `official=false`.
Gates: `needs_mutation`, `needs_visible_checks`, `ready_to_submit`, and opt-in
`needs_original_reproduction`.
Gates and resource horizons expose registered tools, never unrestricted shell.

`replace_text` uses `TextReplacementIntent` and `CausalRevision`. Preserve explicit
public fields, required/null rules, keyword order, absent/default serialization,
unadvertised recovery annotations, and cross-field/anchor/scope validation.

Batch 1–4 `read_file`/`search_files` calls; other tools run singly.
Opt-in history search: eight candidates, execution-only ranking, whole originals
within actual input limits. Only fresh-seed overflow uses 48k units; ID pages are
48k too. Authored fields labelled, no source/PASS credit.
A question may retain search results within its existing two handoff references.
A bounded public `turn_decision` accompanies each default-policy call. Opt-in
`--agent-policy thin --planning-policy none` replaces it with root nullable
`memory_update`; see [contract](thin-policy-reference.md). Execution gates stay shared.
Notes/plans are unverified; never reasoning transcripts.
One consecutive protocol/incomplete correction; reset on valid batches.

Reads return at most 400 lines. Searches use literal queries, rooted component-aware
globs and one tracked-path enumeration per uncached call. Edits require delivered
current public source. `replace_text` requires an exact occurrence in a tracked,
allowed file, a hypothesis and expected behavior (each 1-1,500 characters in both
schemas). Bind the contiguous observed anchor, enforce canonical full-diff scope,
and restore the pre-image on rejection. No fuzzy matching, unseen source, new paths
or model-selected mutation evidence IDs. Exact reads/previews use literal Git pathspecs;
decode quoted/NUL-delimited Git paths without changing diff bytes.
Retired requirement/case annotations remain for exact legacy recovery, not fresh requests.

Submit a nonempty tracked diff only after all required checks pass on it.
`finish_task.assessment` and `plan_review` bind judgment and plan to the submitted diff.
Plan replacements need `plan_update_reason`; invalid reasons preserve the prior plan.
Latest predecessor/reason stays visible; see [planning](planning-experiment.md).
Check PASS alone certifies no requirement coverage. Label source inference.
See [evidence recovery](evidence-recovery.md) for opt-in source restoration and
fixed probe comparisons.
Finish replays stale invocation-bound cases. Current mismatch/conflict blocks;
missing/incomplete evidence stays unverified. Mapping remains model-authored.
`original_obligation.py` retains the public-task obligation separately from cases.
`--reproduction-acquisition bounded-v1` requires probes. Before edits it permits two
actual original dispatches, two rejected requests, and six total investigation actions;
completion budgets can release it earlier. Rejected requests do not count as executions.
Stage receipts distinguish accepted/rejected requests, dispatch and returned results.
Legacy unknown dispatches reserve slots without becoming execution evidence. Releases
preserve unmet verification. Journal roots and action/release identities survive recovery;
forecasts never write them.
Only an unchanged-base failure plus comparable current support permits
`cases_verified_delivery`; otherwise finish returns `unverified_delivery`.
Delivery, selected-case verification and independent acceptance stay separate.
After edits, required checks need fresh PASS; probes give no check credit.
Preserve pre-state, candidate and incremental patch identities on replay.
Visible-check IDs must be unique at task admission.
Advisory line feedback decodes those paths and binds script filenames at launch,
preserving arguments and tracking across chdir.

Reserve the minimum completion path and bounded recovery. Forecast model calls and
tool actions separately: an eligible automatic required-check recheck costs zero
model calls and one action. Share execution's current/healthy/registered eligibility
in admission, successor and cost forecasts; retain all tool slots. Disabled recheck
preserves the common counts.
A failed check does not require another read when current edit evidence exists.
Preserve the distinction between minimum and protected completion, and do not add
hard tool restrictions from advisory progress signals or task-specific failure patterns.

## Context and recovery

Project only explicit public fields; separate current evidence, history and notes.
The six retained unsuccessful executions keep identities, flags and omission count.
PASS cannot erase them; edits make them historical. Null concern ID creates; an ID
updates. Bound evidence requires an unsuccessful observation; null means hypothesis.
Operator feedback is never an observation; delivery does not imply use.
Model positions describe discussion. `reproduction_review` computes case evidence;
requirement mapping stays unverified.
Plans/concerns cannot close it or gate finish. See [scope](evidence-recovery.md).
Completion retains all cases beyond the three-case display, independently of plans.

Latest observations must reach the next request. `--retained-source-chars` selects
24,000 (default) or 48,000 previously observed characters; complete lines only, no
unseen gaps. The setting binds model/envelope identity and resume. Native history
and the separate 60,000-token segmented limit are unchanged. Result handoffs may
discard older history below that limit. Run-local notes are not cross-run memory.
Fresh native tool outputs contain only the primary action result. Note/plan update
receipts stay in their separate current-state fields, including failures and note IDs.
An annotation failure neither replaces an action error nor turns a successful action
into a failure. Preserve legacy native outputs and their exact replay bytes.

External state is append-only, hash-chained `dev-run-v1` JSONL with immutable envelopes.
Preserve `action_id + input_hash`: replay completed mutations/checks, reject conflicting
reuse, and reconcile admitted mutations after crashes without applying them twice.
Never rewrite journals, old envelopes or native outputs. Reads/appends share the
reentrant process lock; only append takes a file lock. Append completes writes and
fsync before returning; I/O errors propagate. LF alone separates records. Preserve
Unicode data; torn tails, including missing final LF, block replay/append unchanged.
Resume requires repeat=1, exact envelope-bound settings/identities, and the run lock.
Pre-envelope runs cannot resume. Preserve settled usage, counters, and active deadlines.
The offline [observation-exposure fork](observation-exposure.md) retains parent
provenance under a new current-runtime envelope; it does not relax ordinary resume.

Use `store=false` and ordered encrypted continuation. No plaintext reasoning/summaries.
Missing/corrupt continuation fails closed. Unmatched dispatch/unknown usage forbids retry.
[HTTP/SDK diagnostics](provider-usage-diagnostics.md) are operator-only.
Durable evaluator completion verifies check/safety artifact references and bytes
before finalizing without re-execution;
a crash before that receipt does not establish exactly-once evaluator execution.

One deadline covers preparation, counting, generation, tools, Git, and evaluation.
Development requests may reserve evaluation time inside that total (default zero).
A timely, bound `solver_finished` receipt permits recovery after the solver cutoff,
with no new solver actions; see [current panel](current-dev20.md).
After expiry permit only bounded metadata/reconciliation work. Unknown process or
container cleanup stops execution/repetitions; preserve the original failure and typed
cleanup evidence. Fresh probe dispatches without a durable return receipt stop on
uncertainty; never execute the same action again. Durable returns resume postprocessing
without another backend call. A dispatch receipt is not proof of completed execution.

## Live, cost, and evaluation boundary

Live work requires the authorized exact checked-in `dev-train` task, model,
credential file, repeat count, and positive invocation-wide cap.
Admission rejects missing hidden checks before execution; calibrate coverage separately.
Runtime/lock inputs and the selected task package must be tracked and HEAD-clean. Keep credentials out
of repository/evaluator subprocess environments. Inspect existing local images;
never start Docker Desktop or pull/build images automatically.

Count actual input immediately before dispatch and reserve conservative input/output
cost using reviewed prices. Cost admission may reduce the desired output ceiling.
Opt-in `completion-minimum-v1` requires segmented-v1. First retain existing model/tool
slot rules, then remove actions whose successful minimum successors cannot be funded.
Reserve the largest offered successor at 60K uncached input plus 128 output per call;
ready finish uses exact counting without a successor reserve. Rechecks/replays keep
their real tool slots. This funds minimum admission, not useful output, failure recovery
or correct repairs. `per-call-v1` and `completion-reserve-v1` retain their contracts.
Use zero SDK retries; count, transport, billing, or cleanup uncertainty stops all
remaining repetitions. Reservations are not billed usage; unknown usage is not zero.
Panel usage restoration includes compaction and adds only the row's delta to shared cost.

Probes use isolated public snapshots and the approved clean image/profile: no network,
read-only source/root, bounded resources, and no private files, credentials, Git data,
symlinks, or reparse points. Their sandbox receipts are separate from task correctness.
The probe profile binds OPENBLAS_NUM_THREADS=1 at launch to fit its single CPU and
eight-task PID limit. This is a library default; the existing thread limit still applies.
Finish stores the exact submitted diff and content-bound manifest before isolated
evaluation. Do not feed evaluator output back into the coding agent. Report acceptance
and safety separately; `EVALUATOR_PASS` means task acceptance, mock Docker safety is
`NOT_RUN`, and `claim_eligible=false`. Development results are not general quality claims.
Registered checks may declare `infrastructure_exit_codes`, disjoint from success
codes. Isolated evaluation classifies these exits as ERROR; opted-in check timeouts
are also ERROR. Omitted/empty declarations preserve existing serialization and behavior.
Original-input pilot packages use exit 2 for setup, collection or incomplete-oracle
execution, distinct from exit 1 for a completed wrong-answer result.

## Defaults and optional diagnostics

CLI defaults differ from the selected working baseline in current status. Defaults:
medium reasoning, 25,000 desired output tokens, append-v1 context, planning none,
probes OFF, probe-policy none, repair-recheck OFF, protected-v1 inspection,
result-or-size-v1 segment boundaries, and per-call-v1 cost admission.
Limits are 40 model calls, 100 tool actions, 4 accepted mutations, and 1,800 seconds;
repeat defaults to 1 (maximum 6). Verify exact options in `DevRunRequest` and CLI.
The reviewed full GPT-5.4 snapshot requires segmented-v1 and its counted input bound.
Choosing a baseline or reading a diagnostic never authorizes a live run or changes defaults.

Read optional implementation notes only when changing that feature. They contain
experimental context and historical plans; current source/status take precedence:

- Context: [handoffs](plans/evidence-preserving-handoff.md), [native window](plans/native-context-window.md).
- Planning and probes: [planning](planning-experiment.md), [probe replay/cases](probe-cases.md),
  [saved-program recheck](probe-recheck.md),
  [setup](probe-setup.md), [dependencies](prepared-probe-dependencies.md), [threads](probe-threads.md).
- Public test selection: [registered pytest suites](selected-tests.md).
- Current dev20 capability and task parallelism: [bounded panel](current-dev20.md).
- Closed discovery, completion and candidate experiments remain indexed in
  [history](../docs/history/README.md); their detailed contracts remain under `.agent/`.

Public [repair and repair-verify](../examples/repair/README.md) return public evidence,
acceptance `NOT_RUN`. Verification compares unchanged submitted tests without a model.
Live repair requires exact public-request/cost approval; live dev requires dev-train.

## Validation checklist

Use the quick selection plus changed-owner tests for routine validation; run the full
suite for broad integration changes. Docs-only changes need `test_documentation_layout.py`.
Keep focused validation under two minutes and freeze runtime during provenance checks.
Use short unique external basetemps; never sweep durable evidence or a parent directory.

```powershell
uv run ruff check patchloop tests
uv run --locked pytest @tests/quick.txt --basetemp C:\pt\tmp\<short-id>
# Full regression when warranted:
uv run --locked pytest tests -n 4 --dist loadfile --max-worker-restart 0 --basetemp C:\pt\tmp\<short-id>
```

Quick tests include mock smoke. Worker crashes fail validation. Docker tests require
opt-in and existing images. Before handoff verify boundaries, links, recovery identities,
unrelated edits and historical bytes. Separate local evidence from live and `NOT_RUN`.
