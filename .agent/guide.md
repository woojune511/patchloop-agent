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
- exactly one `apply_git_diff`, `run_check`, `finish_task`, or `stop_task` call.

The provider request uses required tool choice, and the application validates the
smaller batch grammar above. Mixed, empty, duplicate-action, and oversized batches
receive one short correction. A second consecutive protocol/incomplete violation
terminates the row; any valid completed tool batch resets the correction allowance.
`run_check` is available on the first turn and its schema enumerates only the public
registered IDs. `finish_task` is exposed only for a non-empty diff with no untracked
files after all visible checks pass on that exact diff. `stop_task` is an explicit
unsuccessful terminal when no public action can support safe progress; it never
submits or evaluates.

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
tool batch, a recency-ordered current-source working set, recent visible-check
output, the complete current-diff check status, exact remaining check IDs, bounded
`last_successful_mutation`, bounded `last_failed_mutation`, remaining budget, and
the latest three attempt-result-next-question cards. A successful check card names
the next remaining check instead of treating PASS as a failure. A failed mutation
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
repetitions. Provider completion records structural output evidence only: item
count, non-tool count, item types, and a shape hash. Never persist response text or
raw reasoning for protocol diagnosis.

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
- one consecutive protocol/incomplete recovery
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
all existing mutation and submission checks. The next seam is a versioned successor
task package whose private oracle accepts the semantic behavior exposed by the public
contract, followed by provider-free base/candidate/evaluator validation. Any seventh
live row remains separately authorized and must name the exact task version/content
identity. Confirmatory design review waits for three distinct harness/contract-clean
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
