# Internal implementation guide

This is the agent-only companion to the required root `AGENTS.md`. It summarizes
active contracts for navigation; checked-in source remains the behavioral authority.

## Source map

```text
patchloop/dev/runner.py   loop composition, gates, context, terminal handling
patchloop/dev/tools.py    tool grammar, spans, mutations, checks, finish
patchloop/dev/state.py    append-only JSONL, action/provider recovery
patchloop/dev/cost.py     reviewed prices and pre-dispatch admission
patchloop/agent/model.py  stateless Responses adapter, zero retries
patchloop/repository.py   audited checkout, workspace, full diff
patchloop/sandbox/        registered local/Docker checks
patchloop/verifier/       separate private evaluation and static policy
patchloop/contracts.py    task, manifest, result, and evaluator models
tasks/                    public/private packages and declared checks
```

## Loop and tool contract

The only runtime is mutable `dev-head`. Its public workflow gates are
`needs_mutation`, `needs_visible_checks`, and `ready_to_submit`; there is no plan
state or plan tool.

One model response may request either:

- 1–4 parallel `search_files` and/or `read_file` calls, or
- exactly one `apply_git_diff`, `run_check`, or `finish_task` call.

Mixed, empty, duplicate-action, and oversized batches receive one short correction.
A second protocol/incomplete violation terminates the row. `run_check` is available
on the first turn. `finish_task` is exposed only after all visible checks pass on
the exact current diff; the next context already contains the complete diff.

## Mutation and causal pivot

Every `apply_git_diff` requires `git_diff` to begin exactly with
`diff --git a/<path> b/<path>`. Patch wrappers such as `*** Begin Patch` and
`*** Update File` are rejected. Git recounts each hunk's declared line totals from
the raw body before check, apply, rollback, and crash reconciliation. Recount does
not relax hunk syntax, source context, tracked-path, anchor, or scope validation;
the resulting canonical worktree diff remains the submission authority. The
mutation also requires:

- `hypothesis`
- `expected_behavior`
- current `evidence_span_ids`
- exact `edit_anchor.path`, `old_text`, and occurrence

Anchors and spans must still match current source. Resulting paths, file count,
line count, dependencies, tests, and public API remain constrained by the public
task. If one public failure signature repeats across two distinct diffs, the next
mutation additionally requires `falsified_prior_hypothesis` and
`alternative_mechanism`; this never creates a separate planning turn.

## Context boundary

Model context contains only the public task, current full diff, the exact latest
tool batch, a recency-ordered current-source working set, recent visible checks,
bounded `last_successful_mutation`, bounded `last_failed_mutation`, remaining
budget, and the latest three attempt-result-next-question cards. A failed mutation
retains its public diff excerpt, full diff hash, intent, anchor, evidence IDs, error,
and parsed error location across later reads and process resume. A later failed
mutation replaces it; a successful mutation clears it. Identical evidence may be
cached and signaled but is not hard-blocked. Never add raw reasoning, private task
material, hidden tests, reference patches, or evaluator details.

## State and recovery

Each run owns an external `dev-run-v1` JSONL stream with sequence, prior hash, and
event hash. Mutations and checks use `action_id + input_hash`; identical input
replays the durable result, conflicting reuse fails closed, and an admitted
mutation is reconciled after a crash instead of applied twice. A provider start
without durable usage is uncertain and must not be retried automatically.

New runs also own one immutable `dev-run-envelope-v1`. `--resume-run-id` requires
`repeat=1` and an exact match for provider, task, runtime, model, reasoning,
credential path hash, cost cap, limits, and sandbox identity. Pre-envelope runs
cannot resume. A run-lifetime OS lock rejects concurrent execution. Generic turn
and tool-batch events recover a durable model decision without another provider
call; counters, settled cost, latest batch, and active execution time are rebuilt
from unique journal events. Process downtime contributes only to run age.

## Live and evaluation boundary

Live mode accepts only checked-in `dev-train` tasks and requires an explicit model,
credential file, positive total cap, and repeat count. The credential is injected
directly into the SDK and is never placed in the process environment inherited by
repository or evaluator subprocesses. Active runtime/lock files and the selected
task package must be tracked and HEAD-clean; unrelated pathspecs do not block live
preflight. The local evaluator image and digest are checked before provider
dispatch; no pull/build/start occurs.

Actual request input is counted immediately before generation. The ledger reserves
uncached input plus a conservative output ceiling, lowers that ceiling when needed,
and emits `COST_CAP_REACHED` without generation when the minimum request cannot fit.
Transport retry is zero. Count, provider, or billing uncertainty stops remaining
repetitions.

After finish, the canonical submitted diff is content-addressed and an immutable
manifest is recorded before evaluator execution. It binds task bytes, full runtime
bytes, model/tool/sandbox identities, the visible-check diff, changed files, and
the submitted artifact. The evaluator validates those inputs before workspace or
check execution, then a clean workspace receives the exact artifact and private
files. Agent context is never resumed with evaluator output.

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
- one protocol/incomplete recovery
- four parallel reads
- one repetition by default, six maximum

## Development decisions and next seam

- Edit `dev-head` directly in small commits; do not version ordinary fixes.
- Keep memory disabled until completion and submission reliability are established.
- Keep mutation intent embedded in the mutation turn.
- Treat the exact live invocation as bounded development authority.
- Recover historical executables only from checkpoint `b71ddeee`; do not restore
  their active import graph.
- Keep confirmatory work in a future, separately frozen lane.

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

Keep repeated-evidence detection diagnostic-only. The bounded continuation evidence
does not support a hard workflow gate or a replacement mutation DSL. The smaller
current correction uses Git's deterministic recount for hunk totals while preserving
all existing mutation and submission checks. Any fifth live row remains separately
authorized. Confirmatory design review waits for three distinct harness/contract-clean
submissions with at least two private passes; that threshold itself proves no quality
or generalization benefit.

## Validation checklist

Run only what the change needs, then broaden to:

```powershell
uv run ruff check patchloop tests
uv run pytest tests --basetemp <short-external-path>
uv run patchloop dev --provider mock --task tasks/smoke/csv-quoted-newline/public.yaml --model mock-dev --repeat 1
```

Before handoff, confirm no private projection, repository-local run state, live
call, Docker mutation, historical artifact edit, stale active-doc link, or invented
result was introduced.
