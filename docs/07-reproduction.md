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

This is a cooperative fault-injection demonstration after a durable patch checkpoint, not an
operating-system process kill. Start with any completed mock run ID:

```powershell
uv run patchloop inject-fault --run <baseline-run-id> --fault worker-kill-after-patch
uv run patchloop resume --run-id <fault-run-id>
```

Inspect the derived run in the viewer. It must have one `PatchApplied`, one `FaultInjected`, durable
checkpoint evidence and a final evaluator result.

## Live API gate

CI never performs live calls. The checked-in live files are contracts, not proof of a paid run:

- `experiments/dev-validation-pilot.template.yaml`: terminal Terra r3 contract; historical
  inspection only, never rerun
- `experiments/dev-validation-gpt54mini-pilot.yaml`: terminal mini r1 contract;
  historical inspection only, never rerun
- `experiments/dev-no-memory.template.yaml`: six memory-development tasks,
  `no_memory` × 2 = 12 runs, $20 cap

As of 2026-07-28 the official
[OpenAI API pricing](https://developers.openai.com/api/docs/pricing) for the mini pilot is $0.75/M
uncached input, $0.075/M cached input and $4.50/M output, with no separate published cache-write
rate. The suite pins `gpt-5.4-mini-2026-03-17`. Recheck the price within 72 hours of every live
invocation and record the installed SDK version, clean Git commit and execution timestamp.

Configure `OPENAI_API_KEY` in the host process without printing it. Leave `OPENAI_BASE_URL` and
`OPENAI_API_BASE` unset. Then run the no-call preflight first:

```powershell
git status --short
uv run patchloop evaluate `
  --suite experiments/dev-validation-gpt54mini-pilot.yaml `
  --preflight-only
```

The checked-in mini suite now refers to terminal experiment
`dev-validation-gpt54mini-pilot-20260729-r1`. Its immutable run
`run_d4fea5e7198b4abc` passed prompt-token trace qualification but failed before evaluation, so the
command above is inspection-only and should report the existing journal/terminal state. Do not add
approval flags or execute this suite again.

A corrective live retry requires the harness change to be committed, a new experiment ID and suite
snapshot, a clean no-call preflight, review of its new execution hash and a separate user cost
approval. This guide intentionally does not provide a ready-to-copy paid retry command before that
new contract exists. Editing approval fields in YAML, deleting the old journal or changing only an
experiment ID does not authorize spending.

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

A terminal pilot is immutable whether it passes or fails acceptance. A corrective retry is a new
experiment only after the original result, qualification, journal and root-cause evidence are
preserved, the harness fix is committed, and the retry receives a new preflight hash and separate
user approval. The Terra pilot template names the terminal
`dev-validation-live-pilot-20260728-r3` experiment and must not be rerun; it is not the suite used
by the commands above. r1
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
This remains historical v1 evidence. The development suite intentionally leaves `pilot_run_id`
empty because a v1 runtime cannot authorize the corrected v2 tool/context/lifecycle contract.

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

Four paid pilot runs exist when this guide was updated: two immutable Terra failures, one accepted
Terra r3 success and one immutable mini model-candidate failure. Their cumulative measured
list-price cost is `$0.906317625`. Docker availability, exact images,
credential presence, clean-worktree state and price age may still appear as preflight blockers for
the separate 12-run development campaign.

After committing the v2 correction and returning to a clean worktree, create a new Terra
development-validation pilot config and run its no-call preflight. It requires a new experiment
ID, exact execution hash and separate approval capped at $2. Do not reuse the terminal r1-r3 or
mini experiment IDs.

```powershell
git status --short
uv run patchloop evaluate `
  --suite <new-v2-terra-pilot.yaml> `
  --preflight-only
```

Only after that run reaches the evaluator and produces a qualified
`trace-qualification-v2` may its run ID be inserted into
`experiments/dev-no-memory.template.yaml`. Development preflight then verifies the same model,
budget, harness commit, tool/context versions and exact runtime-contract hash before producing a
separate 12-row execution hash. That campaign still requires a distinct approval capped at $20.

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
