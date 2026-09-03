# Run and validate

All generated state must live outside the repository. The examples use short
Windows paths to avoid temporary-directory permission and path-length failures.

## Fast local verification

```powershell
$testRoot = 'C:\patchloop-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
uv sync --extra dev --locked
uv run ruff check patchloop tests
uv run pytest tests --basetemp $testRoot
```

This path uses no provider or Docker call.

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
`uv.lock`, and selected task-package input must be tracked and match HEAD;
unrelated scratch or untracked paths outside those pathspecs are ignored. The
credential file may contain only one `OPENAI_API_KEY=...` assignment. It may be the
ignored repository-root `.env` or an exact external path, but it must never be tracked
or committed.

The required evaluator image must already exist locally at the declared digest.
PatchLoop never starts Docker Desktop or pulls/builds an image. Unknown model
pricing fails before dispatch. The adapter counts the actual request immediately
before generation, reserves a conservative output allowance, uses zero SDK
transport retries, and stops all remaining repetitions when count, transport, or
billing state is uncertain. Generation and input counting use the same
`tool_choice=required` contract, so the provider request and the runner's non-empty
tool-batch requirement agree. From the second turn onward, the request reconstructs
the immediately preceding public function calls and their matching outputs as native
Responses input items. Raw reasoning and non-tool response content are not replayed.
The application still enforces its smaller grammar: up to four reads/searches, or
exactly one mutation, check, finish, or stop.

Current GPT-5.4 mini pricing and supported reasoning effort are reviewed against
the official [API pricing](https://developers.openai.com/api/docs/pricing) and
[model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini). Input
counting follows the official
[token-counting guide](https://developers.openai.com/api/docs/guides/token-counting).
Required tool choice follows the official
[Responses create contract](https://developers.openai.com/api/reference/resources/responses/methods/create).

## Submission and evaluation

The mutation tool is `apply_git_diff`. Its `git_diff` value must start exactly with
`diff --git a/<path> b/<path>` and contain a raw Git unified diff. Codex-style
`*** Begin Patch` / `*** Update File` wrappers are rejected rather than converted.
Declared hunk line totals are recounted deterministically from the raw hunk body for
check, apply, rollback, and crash reconciliation. Invalid hunk syntax or source
context still fails closed, as do stale anchors, non-tracked paths, and scope
violations. The requested patch hash remains evidence, while visible checks and
submission bind the canonical diff produced by the resulting worktree.
If a valid mutation call fails, its bounded public diff and intent remain in
`last_failed_mutation` across later reads and resume. The agent may read/search when
needed for repair, but a successful mutation is required to clear that repair target.
Tool execution failures are not counted or presented as model protocol violations.
Every tool call must include one bounded public `turn_decision` containing `mode`,
`basis`, and an `evidence_goal` only for inspection. Its mode must match the actual
tool family. Parallel reads all use `inspect` mode, while their `basis` and
`evidence_goal` may describe different concrete queries or ranges. Each decision
records its action after the preceding public result; it is not a promise about an
unseen result or stored raw reasoning. Action identity binds each decision, while the
operational read cache remains keyed only by the executable request and current diff.

Tool availability is derived from the workflow gate, current evidence, unexecuted
visible checks, remaining model/tool budget, and an inspection lease. The default
lease allows 24 inspection turns per unchanged diff and three repair-specific inspection
turns after a failed mutation. Reads disappear before they would consume calls needed
for mutation, checks, and finish. This is a resource horizon, not repeated-evidence
classification; cached or repeated evidence remains diagnostic-only, and `stop_task`
is always available. Repetition counts are per evidence fingerprint at the unchanged
diff and are not globally reset by an unrelated new span or check.
One consecutive invalid or incomplete model response receives a correction that
names the current workflow gate and remaining public checks. A valid tool batch
resets that correction allowance. Provider journals retain only output item counts,
types, and a shape hash for diagnosis; response text and model reasoning are not
stored. If no public read, check, or safe scoped mutation can make progress, the
agent may call `stop_task` with a bounded reason. This produces `AGENT_STOPPED`
without submission or evaluation.

`finish_task` becomes available only after every visible check passes on the
current non-empty diff and no non-ignored untracked file remains. The context lists
every current-diff check as PASS, FAIL, or NOT_RUN and separately names remaining
IDs; the `run_check` schema exposes only public checks not yet executed on that exact
diff. A failed check therefore requires a mutation or stop rather than a same-diff
rerun. The full
submitted patch is stored by content hash. A separate
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
match the stored envelope exactly. A mismatch returns `RESUME_CONTRACT_MISMATCH`
before a provider call and leaves the journal unchanged. Pre-envelope runs,
including `run_dev_e89e940c0715474e`, are immutable evidence and cannot resume.

Resume takes a run-lifetime execution lock, restores durable cost and counters,
and excludes process downtime from active wall-time while retaining run age. A
recorded model decision continues with the same tool calls; completed actions use
`action_id + input_hash` replay, and pending mutations use reconciliation. An
unmatched provider dispatch is never retried and becomes one
`PROVIDER_TIMEOUT_OR_UNKNOWN` terminal. Resuming a terminal run is a read-only,
idempotent return of its existing public result. The restored protocol counter is
the consecutive corrections since the latest completed valid tool batch, not a
lifetime total.
