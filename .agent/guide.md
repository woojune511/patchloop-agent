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
- exactly one `apply_patch`, `run_check`, or `finish_task` call.

Mixed, empty, duplicate-action, and oversized batches receive one short correction.
A second protocol/incomplete violation terminates the row. `run_check` is available
on the first turn. `finish_task` is exposed only after all visible checks pass on
the exact current diff; the next context already contains the complete diff.

## Mutation and causal pivot

Every `apply_patch` requires a raw Git diff plus:

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
bounded `last_successful_mutation`, remaining budget, and the latest three
attempt-result-next-question cards. Identical evidence may be cached and signaled
but is not hard-blocked. Never add raw reasoning, private task material, hidden
tests, reference patches, or evaluator details.

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
repository or evaluator subprocesses. The local evaluator image and digest are
checked before provider dispatch; no pull/build/start occurs.

Actual request input is counted immediately before generation. The ledger reserves
uncached input plus a conservative output ceiling, lowers that ceiling when needed,
and emits `COST_CAP_REACHED` without generation when the minimum request cannot fit.
Transport retry is zero. Count, provider, or billing uncertainty stops remaining
repetitions.

After finish, a clean workspace receives the exact submitted artifact and private
files. Agent context is never resumed with evaluator output. Public results expose
only PASS/FAIL and a safe failure class. Every result remains `official=false`.

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

The next local seam is stronger content provenance and typed task-acceptance versus
safety evidence. A second live row remains separately authorized. Confirmatory
design review waits for three distinct harness/contract-clean submissions with at
least two private passes; that threshold itself proves no quality or generalization
benefit.

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
