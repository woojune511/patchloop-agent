# Internal implementation guide

This is the current contract and navigation companion to [AGENTS.md](../AGENTS.md).
Read [current status](../docs/current-status.md) for current facts and priorities.
Checked-in source and tests own runtime behavior; this guide identifies the relevant
contracts. Read only the sections and source needed for the change.

Historical observations are indexed in [history](../docs/history/README.md).
Search that index for a specific question, then read a bounded matching excerpt.
Do not concatenate histories into normal context or treat old next steps as work orders.
Keep run narratives and validation history out of this guide.

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
| Public prompt and provider adapter | `patchloop/dev/model.py`, `patchloop/agent/model.py` |
| Tool grammar, observed anchors, edits, checks, finish | `patchloop/dev/tools.py` |
| Audit context and compact public view | `patchloop/dev/context.py`, `patchloop/dev/model_state.py` |
| Native delivery and context policies | `patchloop/dev/conversation.py`, `patchloop/dev/native_sources.py`, `patchloop/dev/segments.py` |
| Notes, concerns, and source currency | `patchloop/dev/working_notes.py`, `patchloop/dev/verification_concerns.py`, `patchloop/dev/source_rebinding.py` |
| Journal/recovery and evaluator completion | `patchloop/dev/state.py`, `patchloop/dev/evaluation_completion.py` |
| Prices and pre-dispatch cost admission | `patchloop/dev/cost.py` |
| Workspaces, prepared inputs, deadlines | `patchloop/repository.py`, `patchloop/prepared_source.py`, `patchloop/git_execution.py`, `patchloop/deadline.py` |
| Registered checks and public probes | `patchloop/sandbox/`, `patchloop/dev/probe_cases.py` |
| Task/manifest contracts and isolated evaluation | `patchloop/contracts.py`, `patchloop/task_loader.py`, `patchloop/verifier/` |

Use public task inputs for agent work. Private task material and evaluator internals
never enter coding-agent context, including through diagnostics or repair hints.

## Loop and mutation contract

The only runtime is mutable `dev-head`; every run is `official=false`.
Public gates are `needs_mutation`, `needs_visible_checks`, and `ready_to_submit`.
The current gate and resource horizon expose registered tools, never unrestricted shell.
A response contains 1–4 parallel `read_file`/`search_files` calls, or exactly one
`replace_text`, `run_check`, enabled `run_probe`, `finish_task`, or `stop_task`.
A bounded public `turn_decision` accompanies each call. Optional notes/plans are
unverified working data, not reasoning transcripts or an extra workflow phase.
One consecutive protocol/incomplete correction is allowed; a valid tool batch resets it.

Reads return at most 400 inclusive lines within output bounds. Searches use literal
queries and repository-rooted component-aware globs. Only delivered, current public
source can authorize an edit. `replace_text` requires an exact occurrence in an
existing tracked allowed file, a hypothesis, and expected behavior. The gateway binds
the contiguous observed anchor, creates the canonical full diff, enforces complete-diff
scope, and restores the pre-image on rejection. Do not substitute fuzzy matching,
unobserved source, new paths, or model-selected mutation evidence IDs.
Retired requirement/case annotations remain for exact legacy recovery, not fresh requests.

A repair invalidates checks for the prior diff. Submission requires a nonempty tracked
diff and every registered required check passing on that exact diff. Optional probes
do not supply required-check credit. Passing checks establish their observed results,
not complete semantic coverage. Preserve pre-state, submitted-candidate, and incremental
patch identities separately; replayed results retain action-time identities.

The scheduler reserves the minimum completion path and bounded recovery opportunities.
A failed check does not require another read when current edit evidence exists.
Preserve the distinction between minimum and protected completion, and do not add
hard tool restrictions from advisory progress signals or task-specific failure patterns.

## Context and recovery

Project only public task/source/diff/action/check information. Keep current evidence
distinct from historical or unverified notes; do not equate delivery with model use.
Latest tool observations must reach the next request. Retained source is bounded,
uses only observed complete lines, and never fills unseen gaps. Optional run-local
working notes do not enable cross-run memory.

External state uses append-only, hash-chained `dev-run-v1` JSONL and immutable run
envelopes. Mutations/checks preserve `action_id + input_hash`: replay completed results,
reject conflicting reuse, reconcile admitted mutations after crashes instead of
applying them twice. Do not rewrite journals, old envelopes, or prior native outputs.
Resume requires repeat=1, exact envelope-bound settings/identities, and the run lock.
Pre-envelope runs cannot resume. Preserve settled usage, counters, and active deadlines.

OpenAI uses `store=false` and encrypted continuation with exact call/output ordering;
never log plaintext reasoning or reasoning summaries. Missing/corrupt continuation
fails closed. An unmatched provider dispatch or uncertain usage must not trigger retry.
Durable evaluator completion can finalize from verified artifacts without re-execution;
a crash before that receipt does not establish exactly-once evaluator execution.

One deadline covers preparation, counting, generation, tools, Git, and evaluation.
After expiry permit only bounded metadata/reconciliation work. Unknown process or
container cleanup stops execution/repetitions; preserve the original failure and typed
cleanup evidence. Interrupted probes may rerun only on their bound snapshot after
confirmed owned-container cleanup; this is not an exactly-once process guarantee.

## Live, cost, and evaluation boundary

Live work requires the authorized exact checked-in `dev-train` task, model,
credential file, repeat count, and positive invocation-wide cap. Runtime/lock inputs
and the selected task package must be tracked and HEAD-clean. Keep credentials out
of repository/evaluator subprocess environments. Inspect existing local images;
never start Docker Desktop or pull/build images automatically.

Count actual input immediately before dispatch and reserve conservative input/output
cost using reviewed prices. Cost admission may reduce the desired output ceiling.
Use zero SDK retries; count, transport, billing, or cleanup uncertainty stops all
remaining repetitions. Reservations are not billed usage; unknown usage is not zero.

Probes use isolated public snapshots and the approved clean image/profile: no network,
read-only source/root, bounded resources, and no private files, credentials, Git data,
symlinks, or reparse points. Their sandbox receipts are separate from task correctness.
Finish stores the exact submitted diff and content-bound manifest before isolated
evaluation. Do not feed evaluator output back into the coding agent. Report acceptance
and safety separately; `EVALUATOR_PASS` means task acceptance, mock Docker safety is
`NOT_RUN`, and `claim_eligible=false`. Development results are not general quality claims.

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
  [setup](probe-setup.md), [dependencies](prepared-probe-dependencies.md), [threads](probe-threads.md).
- Discovery diagnostics: [counterexamples](counterexample-discovery.md),
  [task-first discovery](task-first-discovery.md), [construction links](construction-links.md),
  [frozen expectations](frozen-probe-expectation.md), [profile scope](profile-scope-diagnostic.md).
- Completion advice: [status-only diagnostic](completion-status-diagnostic.md), an
  opt-in seeded-loop projection that keeps completion gates and tool admission intact.
  [Mutation advice checkpoint](mutation-advice-checkpoint.md) prepares an offline
  post-probe input pair; [offline continuation](checkpoint-continuation.md) restores
  that state for scripted registered-action and evaluation tests. The separate
  [live collector](checkpoint-comparison.md) binds fresh accounting and admission.
  The [caller-state probe](caller-state-probe.md) is a separate provider-free observation.
  [Caller information](caller-information.md) tests its first-input delivery with advice fixed.
- Candidate comparison: [independent candidate](independent-candidate.md), an
  opt-in public alternative in the ordinary seeded repair loop.
- Search context: [declaration context](declaration-context.md), opt-in bounded
  declaration/documentation expansion in the first tool batch; the separate
  [checkpoint sampler](declaration-checkpoint.md) retains a saved first decision prefix.

## Validation checklist

Run focused tests appropriate to the changed contract, Ruff, the fast suite, and mock
smoke as relevant. Documentation-only changes need the documentation layout/link tests.
Keep focused validation under two minutes; report longer or unrun groups honestly.
Freeze runtime source during provenance checks. Use unique external basetemps under
`C:\pt\tmp\<unique-name>`; parallel processes need separate roots. Durable run/evidence
stores are not scratch. Never sweep a parent directory or relocate recorded state.

```powershell
uv run pytest tests/test_documentation_layout.py -p no:cacheprovider
uv run ruff check patchloop tests
uv run pytest tests -p no:cacheprovider --basetemp C:\pt\tmp\<unique-name>
uv run patchloop dev --provider mock --task tasks/smoke/csv-quoted-newline/public.yaml --model mock-dev --repeat 1
```

Set `PATCHLOOP_STATE_ROOT` to an external directory for mock smoke. Real-Docker tests
are opt-in and require existing images; mock/local evidence does not prove live behavior.
Before handoff check public/private boundaries, current links, external state, exact
recovery identities, unrelated edits, and unchanged historical artifacts. Report what
was implemented, locally tested, live-executed, and left `NOT_RUN` separately.
