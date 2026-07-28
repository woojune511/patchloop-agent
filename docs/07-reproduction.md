# Clean-machine reproduction

## Supported environment

- Windows 11 + WSL2 + Docker Desktop for official evaluator results
- Python 3.12 and `uv`
- Git; `gh` is optional and only required for the GitHub demo

## Offline validation

```powershell
git clone <repository-url> PatchLoop
Set-Location PatchLoop
uv sync --extra dev
uv run ruff check patchloop tests
uv run pytest -q
uv run patchloop task validate tasks/smoke/csv-quoted-newline
uv run patchloop run --task tasks/smoke/csv-quoted-newline/public.yaml --model mock
uv run patchloop run --task tasks/smoke/csv-quoted-newline/public.yaml `
  --model replay:replays/smoke/csv-quoted-newline.jsonl
uv run patchloop evaluate --suite experiments/smoke.yaml
uv run patchloop report --experiment offline-smoke --output reports/offline-smoke
```

The mock run does not need an API key. It creates `.patchloop/state.sqlite3`, immutable run manifests,
ordered events, checkpoints, submitted patches and content-addressed evidence. Local backend results have
`official=false` by design.

The replay file must be inside the repository and is identified by both its repository-relative path and
SHA-256 in the immutable run manifest. Resume rejects a missing, moved or changed replay. The checked-in
smoke replays are deterministic test fixtures, not captured live-model responses.

## Official Docker boundary

```powershell
uv run patchloop doctor
docker pull python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de
docker build --network=none --provenance=false -f docker/Dockerfile.sandbox -t patchloop-sandbox:py312 docker
uv run patchloop eval-task tasks/smoke/csv-quoted-newline `
  --patch tasks/smoke/csv-quoted-newline/reference.patch --backend docker
```

The Dockerfile pins the base digest used by the 2026-07-23 evaluator gate. Before a frozen experiment,
re-audit the base digest deliberately and record the built image digest in the experiment manifest; do not
silently float the tag. A Docker result is official only when the daemon is available and the evaluator
actually runs with the Docker backend.

If Docker Desktop is installed per-user outside `PATH`, `patchloop doctor` checks its standard Windows
location. Set `PATCHLOOP_DOCKER_CLI` to an existing CLI path for a non-standard install.

## Recovery demonstration

Start with any completed mock run ID:

```powershell
uv run patchloop inject-fault --run <baseline-run-id> --fault worker-kill-after-patch
uv run patchloop resume --run-id <fault-run-id>
```

Inspect the derived run in the viewer. It must have one `PatchApplied`, one `FaultInjected`, durable
checkpoint evidence and a final evaluator result.

## Live API gate

CI never performs live calls. The checked-in live files are contracts, not proof of a paid run:

- `experiments/dev-validation-pilot.template.yaml`: Babel #1042, `no_memory` × 1, $2 cap
- `experiments/dev-no-memory.template.yaml`: six memory-development tasks,
  `no_memory` × 2 = 12 runs, $20 cap

As of 2026-07-28 the official
[OpenAI API pricing](https://developers.openai.com/api/docs/pricing) for Terra is $2.50/M uncached
input, $0.25/M cached input, $3.125/M cache-write input and $15/M output. The model catalog exposes
the `gpt-5.6-terra` alias but no dated Terra snapshot. Recheck the price within 72 hours of every
live invocation and record the installed SDK version, clean Git commit and execution timestamp.

Configure `OPENAI_API_KEY` in the host process without printing it. Leave `OPENAI_BASE_URL` and
`OPENAI_API_BASE` unset. Then run the no-call preflight first:

```powershell
git status --short
uv run patchloop evaluate `
  --suite experiments/dev-validation-pilot.template.yaml `
  --preflight-only
```

The unapproved command intentionally exits with code 2 after printing JSON. Copy its
`execution_hash` and inspect every blocker. It checks the frozen dataset/role/hash, the manifest's
canonical task package path, public/private spec hash and base commit, the digest-pinned task
environment and observed Docker image identity, clean commit, SDK, API-key presence without its
value, absence of custom base URLs, `gpt-5.6-terra`/medium/standard/default settings, price
age/rates and full-run budget reserve.

After the user separately approves at most $2, validate the same execution identity:

```powershell
uv run patchloop evaluate `
  --suite experiments/dev-validation-pilot.template.yaml `
  --preflight-only `
  --approve-live-cost `
  --approved-execution-hash <sha256:...>
```

Only if this returns `ready=true`, execute with the same two approval flags:

```powershell
uv run patchloop evaluate `
  --suite experiments/dev-validation-pilot.template.yaml `
  --approve-live-cost `
  --approved-execution-hash <same-sha256:...>
```

Approval is invocation-only. Editing `live_cost_approved` or `approved_execution_hash` in YAML does
not authorize spending. A Git change, image/SDK change, suite change or pilot qualification change
produces a different execution hash.

The paid command first persists
`.patchloop/experiments/plans/<execution-hash>.json` as an approved
`experiment-execution-plan-v1`. It exclusive-creates the journal with `CampaignStarted`, fsyncs it,
then issues the live capability from that durable plan. A concurrent invocation that loses this
atomic claim stops before authorization. Each row's stable-ID `RunStarted` is also appended and fsynced to
`.patchloop/experiments/journals/<experiment-id>.jsonl` before any model call for that scope. Each
journal row links `previous_event_hash` to its own content hash. If the process hard-crashes, a
later preflight reports `EXPERIMENT_JOURNAL_EXISTS` instead of automatically starting the paid
schedule again. Automatic journal resume is not implemented: preserve and inspect the journal;
do not delete it or change the experiment ID merely to bypass this guard.

Execution does not reload the suite path after preflight. It validates and uses the normalized
suite snapshot in the approved plan, then rechecks each task package and generated run manifest
against the plan before writing `RunStarted`. A replaced suite/task therefore stops before a model
call instead of borrowing an older approval hash.

A terminal pilot is immutable whether it passes or fails acceptance. A corrective retry is a new experiment only after
the original result, qualification, journal and root-cause evidence are preserved, the harness fix
is committed, and the retry receives a new preflight hash and separate user approval. The checked-in
pilot template names the terminal `dev-validation-live-pilot-20260728-r3` experiment and must not be
rerun. r1
`run_c6f13dd9a1a1472d` and r2 `run_de8f2a2846044c01` remain immutable; neither unlocks the
development campaign. r2's trace artifact passed integrity/leakage qualification, but
`evaluation_reached=false` makes the pilot acceptance consumer reject it.

The r3 harness recounts only hunk line totals in the agent-visible gateway. It preserves the exact
raw patch for hashing, validates body/context/path and all policy checks, and uses the same raw
patch with reverse recount on rejection. It then verifies the pre-call diff hash and zero-untracked
workspace invariant. Rollback failure or state mismatch is a recovery error, not a recoverable tool
message. Hidden evaluator patch application remains strict.

The resulting r3 `run_3cb86f8d70094a11` created a `trace-qualification-v1` artifact with
`qualified=true`, `trace_integrity_passed=true`, `leakage_scan_passed=true` and
`evaluation_reached=true`, and its official hidden/regression/scope/safety verdicts all passed.
The development suite records that run ID. Return the worktree to a committed clean state, run the
no-call development preflight, inspect its exact execution hash and separately approve at most $20
before the 12-run campaign. The r3 pilot approval does not authorize the development campaign.

Qualification also records a `source_evidence_hash` over the approved plan, manifest, ordered
events, checkpoints, state/persisted result and agent-visible CAS artifact inventory. Required
`RunStarted`, `ContextBuilt` and `ModelCalled` events need both artifact ID and path, and the bytes
must match their content-addressed identity. Development-campaign preflight, review and
memory-index admission recalculate the current source hash; copying a previously qualified JSON
beside changed or missing evidence is not enough. Usage validation rejects cached plus cache-write
input above total input, while malformed
function-call arguments still retain the already billed response usage and calculated cost.

Direct `patchloop run --model openai`, direct resume of an OpenAI run and direct fault injection
from an OpenAI baseline are blocked; all paid calls go through an approved suite. A failed started
attempt still persists its run ID, events, usage including cached/cache-write tokens, calculated
cost and terminal outcome. The suite halts after the first infrastructure or qualification error
and records remaining rows as not started.

Three paid pilot calls exist when this guide was updated: two immutable failures and one accepted r3
success. Their cumulative measured cost is `$0.828864375`. Docker availability, exact images,
credential presence, clean-worktree state and price age may still appear as preflight blockers for
the separate 12-run development campaign.

After checking in the r3 evidence and returning to a clean commit, generate the next gate without
calling the model:

```powershell
git status --short
uv run patchloop evaluate `
  --suite experiments/dev-no-memory.template.yaml `
  --preflight-only
```

The suite contains `pilot_run_id: run_3cb86f8d70094a11`. Preflight reloads its immutable
qualification, recomputes `source_evidence_hash`, and binds both identities into the new execution
hash. The unapproved no-call command is expected to report approval blockers. Do not run the
12-row suite until that exact hash, the cost reserve and every blocker have been reviewed and the
user separately approves at most $20.

If a campaign halts or a row fails qualification, `patchloop report` may still export row-level
CSV and available-case diagnostics for investigation. Confirm `analysis_ready=true` before using
any aggregate as a result. With an incomplete or qualification-failed matrix the report sets
`analysis_ready=false`, labels the basis `available-case-diagnostic-not-for-headlines`, and
suppresses headline metrics, paired differences/intervals and success/failure flips.

## Memory freeze gate

```powershell
uv sync --extra dev --extra memory
uv run patchloop memory build --split dev-train --embedding-revision <hugging-face-commit>
uv run patchloop memory freeze --index <index-id> --embedding-revision <same-commit>
```

A non-empty index is freezeable only when its vectors were created by
`sentence-transformers/all-MiniLM-L6-v2` at the recorded commit. Empty or lexical placeholder indexes
are rejected before any memory-condition campaign.
