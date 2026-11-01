# Implementation guide

See [AGENTS.md](../AGENTS.md) and [status](../docs/current-status.md).
Source/tests own behavior; read relevant sections.

## Choosing the next improvement

Integrate fixes; isolate unresolved design decisions. Keep evidence in history,
active decisions in current status.

## Source map

| Concern | Current source |
| --- | --- |
| CLI/defaults | `patchloop/cli.py`, `patchloop/dev/contracts.py` |
| Loop/admission/termination | `patchloop/dev/runner.py` |
| Pure resource forecasts | `patchloop/dev/completion_budget.py` |
| Prompt/adapter | `patchloop/dev/model.py`, `patchloop/agent/model.py` |
| Tools/observed anchors | `patchloop/dev/tools.py` |
| Audit context and compact public view | `patchloop/dev/context.py`, `patchloop/dev/model_state.py` |
| Native delivery and context policies | `patchloop/dev/conversation.py`, `patchloop/dev/native_sources.py`, `patchloop/dev/segments.py` |
| Notes, concerns, and source currency | `patchloop/dev/working_notes.py`, `patchloop/dev/verification_concerns.py`, `patchloop/dev/source_rebinding.py` |
| Journal/recovery and evaluator completion | `patchloop/dev/state.py`, `patchloop/dev/evaluation_completion.py` |
| Prices and pre-dispatch cost admission | `patchloop/dev/cost.py` |
| Workspaces, prepared inputs, deadlines | `patchloop/repository.py`, `patchloop/prepared_source.py`, `patchloop/git_execution.py`, `patchloop/deadline.py` |
| Registered checks and public probes | `patchloop/sandbox/`, `patchloop/dev/probe_replay.py`, `patchloop/dev/probe_cases.py` |
| Patch/test comparison | `patchloop/repair_verification.py` |
| Task/manifest contracts and isolated evaluation | `patchloop/contracts.py`, `patchloop/task_loader.py`, `patchloop/verifier/` |

Never expose private task/evaluator material through context, diagnostics or hints.

Forecasts are pure; runner admits tools, `dev/cost.py` admits provider work.
Preserve exact-envelope runtime identity.

## Loop and mutation contract

Only mutable `dev-head` runs, always `official=false`.
Gates: `needs_mutation`, `needs_visible_checks`, `ready_to_submit`, and, under
`reproduction-gated-v1`, opt-in `needs_original_reproduction`.
Gates and resource horizons expose registered tools, never unrestricted shell.

`TextReplacementIntent` preserves explicit/absent fields, legacy annotations,
cross-field validation and exact anchor/scope admission.

Batch 1–4 reads/searches; other tools run singly. See [request continuity](request-continuity.md)
for stage-valid schemas, parallel generation and unexecuted correction drafts.
Opt-in history search: eight candidates, execution-only ranking, whole originals
within actual input limits. Only fresh-seed overflow uses 48k units; ID pages are
48k too. Authored fields labelled, no source/PASS credit.
A question may retain search results within its existing two handoff references.
Fresh edit/observation/stop omit decision/plan/memory annotations;
see [small contracts](repair-path.md). Other calls use `turn_decision`, or nullable
root `memory_update` with `--agent-policy thin --planning-policy none`;
see [contract](thin-policy-reference.md). Execution gates stay shared.
Notes/plans are unverified; never reasoning transcripts.
One consecutive protocol/incomplete correction; reset on valid batches.

Reads: null bounds and explicit ranges use 24k-character complete-line pages;
follow next_start_line for omitted content. Fresh ranges have no separate line cap.
Search: literal queries, rooted component-aware globs; one tracked-path scan/uncached call.
After 20-hit/24k-character selection, merge same-source overlap, preserving lines,
gaps, read-only provenance and truncation. Freed space admits no additional hits.
Edits require delivered current public source. `replace_text` accepts an exact occurrence
in a tracked, allowed file, a hypothesis and expected behavior (each 1-1,500 characters
in both schemas). Bind each contiguous observed anchor, enforce canonical full-diff scope,
and restore the pre-image on rejection. No fuzzy matching, unseen source
or model-selected mutation evidence IDs. Exact reads/previews use literal Git pathspecs;
decode quoted/NUL-delimited Git paths without changing diff bytes.
`occurrence="all"` changes all exact matches in one file as one accepted edit;
every match needs current observed source, and rollback/recovery use admitted offsets.
Fresh dev/repair defaults allow 12 edits; explicit task/invocation limits still apply.
Retired requirement/case annotations remain for exact legacy recovery, not fresh requests.

`edit_files` supports creation, multi-file edits and receipt undo. Each accepted
batch/undo spends one edit; uncertain rollback remains pending.
See [file transactions](file-transactions.md) for fields and recovery.

Submit a nonempty tracked diff only after all required checks pass on it.
Host-registered counterexamples use the same registry; see
[required public checks](required-public-checks.md). Speculative notes stay advisory.
`finish_task.assessment` and `plan_review` bind judgment and plan to the submitted diff.
Plan replacements need `plan_update_reason`; invalid reasons preserve the prior plan.
Plan review and advisory contract/case mapping: [planning](planning-experiment.md).
Check PASS alone certifies no requirement coverage. Label source inference.
See [evidence recovery](evidence-recovery.md) for opt-in source restoration and
fixed probe comparisons.
`--verification-policy public-checks-v1` makes diagnostics advisory; public checks
still gate submission. See [policy and evidence](completion-feedback.md).
The following diagnostic gates apply to the default `reproduction-gated-v1`:
replay acquired originals after edits; reuse receipts at finish.
Known failure blocks; missing/incomplete evidence stays unverified. See linked
contract for v4 identity and budget bounds.
`original_obligation.py` separates the public-task obligation from acquired cases.
Optional bounded acquisition allows two original dispatches, two rejected requests
and six preparations within shared budgets. Rejections create no evidence; releases
preserve unmet verification. Public failure/desired comparisons remain distinct.
See [acquisition](first-reproduction-comparison.md), [helper correction](helper-correction.md)
and [host judgment](observation-judgment.md). Identity and uncertainty survive recovery.
Only an unchanged-base failure plus comparable current support permits
`cases_verified_delivery`; otherwise finish returns `unverified_delivery`.
Delivery, selected-case verification and independent acceptance stay separate.
After edits, required checks need fresh PASS; probes give no check credit.
Preserve pre-state, candidate and incremental patch identities on replay.
Visible-check IDs must be unique at task admission.
Advisory line feedback decodes those paths and binds script filenames at launch,
preserving arguments and tracking across chdir.

Reserve minimum completion and bounded recovery; count model calls and real tool
actions separately. Diagnostic reservations below apply to `reproduction-gated-v1`.
`action_horizon.action_budget` explains the call/tool slots left after offered
exploration, including read batches and paired tests, against an edit/check/finish
route. These conditional forecasts grant no tools and do not predict outcomes.
See [resources](completion-resources.md) for replay reuse and bounded preparation,
and [completion feedback](completion-feedback.md) for failures and finalization.
Measured unobserved changed lines require [call-path diagnosis](repair-path.md)
before another repair. Optional first-edit `observe_original` tests path premises
on the frozen original without granting repair credit.

## Context and recovery

Project only explicit public fields; separate current evidence, history and notes.
The six retained unsuccessful executions keep identities, flags and omission count.
PASS cannot erase them; edits make them historical. Null concern ID creates; an ID
updates. Bound evidence requires an unsuccessful observation; null means hypothesis.
Operator feedback is never an observation; delivery does not imply use.
Model positions describe discussion. `reproduction_review` computes case evidence;
requirement mapping stays unverified.
Plans/concerns cannot close it or gate finish. See [scope](evidence-recovery.md).
Completion retains all obligations beyond its bounded display.

Deliver latest observations. `--retained-source-chars`: 24,000 (default) or 48,000;
retain complete observed lines, no unseen gaps. Binds model/envelope/resume.
Keep native history and the 60,000-token segmented limit; handoffs can drop older
history. Notes are run-local. Native outputs carry primary results; state carries
note/plan receipts. Annotation failures cannot change actions. Preserve replay bytes.
Compact repair retains bounded plans/notes and enabled reviews; delivery is not use.

External state is append-only, hash-chained `dev-run-v1` JSONL with immutable envelopes.
Journal reads reuse decoded events only for a byte-identical validated prefix;
all bytes are still read, changed prefixes are revalidated, and callers receive copies.
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

Count actual input immediately before dispatch; reserve conservative reviewed cost.
Admission may reduce output. Opt-in `completion-minimum-v1` requires segmented-v1:
retain model/tool slot rules, close unaffordable actions, reserve the largest offered
successful successor at 60K uncached input + 128 output per call. Ready finish uses
exact counting without successor reserve. Rechecks/replays retain real tool slots.
Opt-in `completion-recovery-v1` reserves one model slot and one correction at 60K
input + `max_correction_output_tokens` (ordinary ceiling when omitted). Its first
durable protocol correction consumes the full allowance; restart/valid actions
never renew it. The independent ceiling and capped 8,192-output finalization floor
are contract-bound. Tool failures/unknown billing are excluded; funding never proves repair.
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

CLI defaults are defined by `DevRunRequest` and differ from the selected baseline
in current status. The reviewed full GPT-5.4 snapshot requires segmented-v1 and its
counted input bound. Reading diagnostics never authorizes live work or changes defaults.

Optional details: [native context](plans/native-context-window.md),
[planning](planning-experiment.md), [probe cases](probe-cases.md),
[recheck](probe-recheck.md), [dependencies](prepared-probe-dependencies.md),
[selected tests](selected-tests.md), and [current panel](current-dev20.md).
Closed investigations remain in [history](../docs/history/README.md).

Public [repair and repair-verify](../examples/repair/README.md) return public evidence,
acceptance `NOT_RUN`. Verification compares unchanged submitted tests without a model.
Live repair requires exact public-request/cost approval; live dev requires dev-train.

## Validation checklist

Use quick plus changed-owner tests; broad integrations require full regression.
Quick includes isolated mock smoke; do not repeat it. Slow A/B matrices stay in
owner/full suites. Docs-only: `test_documentation_layout.py`.
Keep focused validation under two minutes; freeze runtime for provenance checks.
Use short unique external basetemps; never sweep durable evidence or a parent directory.

```powershell
uv run ruff check patchloop tests
uv run --locked pytest @tests/quick.txt --basetemp C:\pt\tmp\<short-id>
# Changed owner: request construction/correction (short local selection)
uv run --locked pytest @tests/request-correction.txt --basetemp C:\pt\tmp\<other-id>
# Full regression when warranted:
uv run --locked pytest tests -n 4 --dist loadfile --max-worker-restart 0 --basetemp C:\pt\tmp\<short-id>
```

Worker crashes fail validation. Docker tests require
opt-in and existing images. Before handoff verify boundaries, links, recovery identities,
unrelated edits and historical bytes. Separate local evidence from live and `NOT_RUN`.
