# Internal implementation guide

Implementation companion to [AGENTS.md](../AGENTS.md).
Read [current status](../docs/current-status.md) for current facts and priorities.
Source and tests own runtime behavior; read only sections relevant to the change.

Use [history](../docs/history/README.md) for specific evidence questions only, never instructions.

## Choosing the next improvement

Start with an observed task-solving problem and public evidence. Separate the
behavior from its suspected cause and alternatives. Choose the smallest diagnostic,
correction, or simplification that resolves a useful uncertainty. Memory, planning,
review, and new gates need a reason grounded in the problem; usage alone is not progress.
Record significant completed investigations once in history: problem, evidence,
hypothesis, change, result, and next question. Current status keeps only the active
implication, unresolved question, and evidence pointers; replace stale statements.
Comparisons answer causal questions when needed; routine fixes need no new process.

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
| Registered checks and public probes | `patchloop/sandbox/`, `patchloop/dev/probe_cases.py` |
| Patch/test comparison | `patchloop/repair_verification.py` |
| Task/manifest contracts and isolated evaluation | `patchloop/contracts.py`, `patchloop/task_loader.py`, `patchloop/verifier/` |

Use public task inputs for agent work. Private task material and evaluator internals
never enter coding-agent context, including through diagnostics or repair hints.

Completion-budget forecasts take an immutable state snapshot and perform no I/O.
The runner assembles that snapshot and owns tool admission; `dev/cost.py` owns
provider cost admission. Keep arithmetic independent of journals, gateways and model
calls. Source extraction changes runtime identity, so existing exact-envelope resume
checks still reject a different runtime; do not relax them for refactors.

## Loop and mutation contract

The only runtime is mutable `dev-head`; every run is `official=false`.
Public gates are `needs_mutation`, `needs_visible_checks`, and `ready_to_submit`.
The current gate and resource horizon expose registered tools, never unrestricted shell.

`replace_text` scalar constraints come from `TextReplacementIntent` and
`CausalRevision`; the provider projection in `dev/tools.py` selects public fields
explicitly. Keep provider-required presence and nullable revision shape separate from
internal recovery defaults, and retain the existing provider keyword order.
Recovery-only annotations stay unadvertised, and their
absent-versus-explicit serialization remains unchanged. Schema field constraints do
not replace cross-field validators, observed-anchor checks or mutation scope admission.

A response contains 1–4 parallel `read_file`/`search_files` calls, or exactly one
`replace_text`, `run_check`, enabled `run_tests`/`run_probe`, `finish_task`, or `stop_task`.
A bounded public `turn_decision` accompanies each call. Optional notes/plans are
unverified working data, not reasoning transcripts or an extra workflow phase.
One consecutive protocol/incomplete correction is allowed; a valid tool batch resets it.

Reads return up to 400 lines. Searches use literal queries,
rooted component-aware globs and one tracked-path enumeration per uncached call.
Only delivered current public source authorizes edits.
`replace_text` requires an exact occurrence in an
existing tracked allowed file, a hypothesis, and expected behavior (each 1-1,500
characters in both the public schema and internal contract). The gateway binds
the contiguous observed anchor, creates the canonical full diff, enforces complete-diff
scope, and restores the pre-image on rejection. Do not substitute fuzzy matching,
unobserved source, new paths, or model-selected mutation evidence IDs.
Retired requirement/case annotations remain for exact legacy recovery, not fresh requests.

A repair invalidates checks for the prior diff. Submission requires a nonempty tracked
diff and every registered required check passing on that exact diff. Optional tests/probes
do not supply required-check credit. Passing checks establish their observed results,
not complete semantic coverage. Preserve pre-state, submitted-candidate, and incremental
patch identities separately; replayed results retain action-time identities.

The scheduler reserves the minimum completion path and bounded recovery opportunities.
Forecast model calls and tool actions separately: an eligible automatic required-check
recheck costs zero model calls and one tool action. Share execution's current/healthy/
registered eligibility, retain all tool slots, and apply the split to admission,
successor and cost forecasts. Disabled recheck preserves the common counts.
A failed check does not require another read when current edit evidence exists.
Preserve the distinction between minimum and protected completion, and do not add
hard tool restrictions from advisory progress signals or task-specific failure patterns.

## Context and recovery

The compact view copies only explicit top-level fields, preserving order and nested rules.

Project only public task/source/diff/action/check information. Keep current evidence
distinct from historical or unverified notes; do not equate delivery with model use.
Completed public checks/tests/probes reconstruct working_notes.verification.observations
(latest six, with omission count), preserving action/input/diff identity and execution
flags, not bug verdicts. Unrelated PASS does not erase them; edits make them historical.
Concern upsert uses concern_id=null to create, or a returned ID to update progress.
Its evidence_action_id links an unsuccessful observation immutably; missing/healthy
IDs are rejected and null keeps a hypothesis-only concern. Operator feedback stays
separately labelled, never a registered observation. Links change no resolution or finish gate.

Latest tool observations must reach the next request. Retained source is bounded,
uses only observed complete lines, and never fills unseen gaps. Optional run-local
working notes do not enable cross-run memory.
The retained pool's 24,000 characters do not bound native results/history. The separate
segmented input limit is 60,000 tokens. Result-driven handoffs can discard old history
below it; judge source availability across the complete request.

External state uses append-only, hash-chained `dev-run-v1` JSONL and immutable run
envelopes. Mutations/checks preserve `action_id + input_hash`: replay completed results,
reject conflicting reuse, reconcile admitted mutations after crashes instead of
applying them twice. Do not rewrite journals, old envelopes, or prior native outputs.
Reads and appends share the reentrant process lock; only append takes a file lock.
Append returns only after complete writes and fsync. Write/sync errors propagate;
torn tails remain untouched and block replay/append. Failed sync is not durability.
Resume requires repeat=1, exact envelope-bound settings/identities, and the run lock.
Pre-envelope runs cannot resume. Preserve settled usage, counters, and active deadlines.
The offline [observation-exposure fork](observation-exposure.md) retains parent
provenance under a new current-runtime envelope; it does not relax ordinary resume.

OpenAI uses `store=false` and encrypted continuation with exact call/output ordering;
never log plaintext reasoning or reasoning summaries. Missing/corrupt continuation
fails closed. An unmatched provider dispatch or uncertain usage must not trigger retry.
Durable evaluator completion can finalize from verified artifacts without re-execution;
a crash before that receipt does not establish exactly-once evaluator execution.

One deadline covers preparation, counting, generation, tools, Git, and evaluation.
Development requests may reserve evaluation time inside that total (default zero).
A timely, bound `solver_finished` receipt permits recovery after the solver cutoff,
with no new solver actions; see [current panel](current-dev20.md).
After expiry permit only bounded metadata/reconciliation work. Unknown process or
container cleanup stops execution/repetitions; preserve the original failure and typed
cleanup evidence. Interrupted probes may rerun only on their bound snapshot after
confirmed owned-container cleanup; this is not an exactly-once process guarantee.

## Live, cost, and evaluation boundary

Live work requires the authorized exact checked-in `dev-train` task, model,
credential file, repeat count, and positive invocation-wide cap.
Admission rejects missing hidden checks before execution; calibrate coverage separately.
Runtime/lock inputs and the selected task package must be tracked and HEAD-clean. Keep credentials out
of repository/evaluator subprocess environments. Inspect existing local images;
never start Docker Desktop or pull/build images automatically.

Count actual input immediately before dispatch and reserve conservative input/output
cost using reviewed prices. Cost admission may reduce the desired output ceiling.
Use zero SDK retries; count, transport, billing, or cleanup uncertainty stops all
remaining repetitions. Reservations are not billed usage; unknown usage is not zero.

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

- Context: [segmented context](plans/segmented-context.md), [native window](plans/native-context-window.md).
- Planning and probes: [planning](planning-experiment.md), [probe cases](probe-cases.md),
  [saved-program recheck](probe-recheck.md),
  [setup](probe-setup.md), [dependencies](prepared-probe-dependencies.md), [threads](probe-threads.md).
- Public test selection: [registered pytest suites](selected-tests.md).
- Current dev20 capability and task parallelism: [bounded panel](current-dev20.md).
- Discovery diagnostics: [counterexamples](counterexample-discovery.md),
  [task-first discovery](task-first-discovery.md), [construction links](construction-links.md),
  [frozen expectations](frozen-probe-expectation.md), [profile scope](profile-scope-diagnostic.md).
- Completion diagnostics: [status-only](completion-status-diagnostic.md),
  [mutation checkpoint](mutation-advice-checkpoint.md),
  [offline continuation](checkpoint-continuation.md), [live collector](checkpoint-comparison.md),
  [caller state](caller-state-probe.md), [caller information](caller-information.md),
  [cleanup](cleanup-probe.md), [closure sampler](closure-policy-sampler.md),
  [selected probe replay](selected-probe-continuation.md).
- Candidate comparison: [independent candidate](independent-candidate.md), an
  opt-in public alternative in the ordinary seeded repair loop.
- Search context: [declaration context](declaration-context.md), opt-in bounded
  declaration/documentation expansion in the first tool batch; the separate
  [checkpoint sampler](declaration-checkpoint.md) retains a saved first decision prefix.

Public [repair and repair-verify](../examples/repair/README.md) return public evidence,
acceptance `NOT_RUN`. Verification compares unchanged submitted tests without a model.
Live repair requires exact public-request/cost approval; live dev requires dev-train.

## Validation checklist

Run focused tests appropriate to the changed contract, Ruff, the fast suite, and mock
smoke as relevant. Documentation-only changes need the documentation layout/link tests.
Keep focused validation under two minutes; report longer or unrun groups honestly.
Freeze runtime source during provenance checks. Use unique external basetemps under
`C:\pt\tmp\<unique-name>`; parallel processes need separate roots. Durable run/evidence
stores are not scratch. Never sweep a parent directory or relocate recorded state.
Keep Windows basetemp names short; nested CAS temporary paths can exceed MAX_PATH.

```powershell
uv run pytest tests/test_documentation_layout.py -p no:cacheprovider
uv run ruff check patchloop tests
uv run --locked pytest tests -n 4 --dist loadfile --max-worker-restart 0 --durations=20 --basetemp C:\pt\tmp\<unique-name>
uv run patchloop dev --provider mock --task tasks/smoke/csv-quoted-newline/public.yaml --model mock-dev --repeat 1
```

Set `PATCHLOOP_STATE_ROOT` to an external directory for mock smoke. Omit `-n 4` for
small focused checks; full-suite workers keep each test file together and use separate temporary
directories. Automatic worker restart is disabled so worker crashes fail validation.
Real-Docker tests remain opt-in and require existing images; mock/local evidence
does not prove live behavior.
Before handoff check public/private boundaries, current links, external state, exact
recovery identities, unrelated edits, and unchanged historical artifacts. Report what
was implemented, locally tested, live-executed, and left `NOT_RUN` separately.
