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

The CLI demonstration remains a cooperative fault injection after a durable patch checkpoint.
Start with any completed mock run ID:

```powershell
uv run patchloop inject-fault --run <baseline-run-id> --fault worker-kill-after-patch
uv run patchloop resume --run-id <fault-run-id>
```

Inspect the derived run in the viewer. It must have one `PatchApplied`, one `FaultInjected`, durable
checkpoint evidence and a final evaluator result.

The actual operating-system kill/fresh-interpreter gate is executable without Docker, network or
an API key:

```powershell
.venv\Scripts\python.exe -m pytest -q tests/test_process_recovery.py
```

The test uses a single-file smoke patch and holds the first process after its only atomic postimage
replacement but before outcome persistence. It verifies that a concurrent resume returns
`RUN_OWNERSHIP_CONFLICT` without changing run state, terminates that process, then uses another
Python process to reclaim stale `RUNNING`. The final evidence requires the same run ID, one patch
call, one `PatchPrepared`, one `PatchApplied`, one `RunCompleted`, no `RunFailed`, two distinct
worker claims and a successful evaluator result. Multi-file mixed/partial reconciliation is covered
by unit tests rather than this process-kill E2E.

## Live API gate

CI never performs live calls. The checked-in suite files are contracts; measured paid-run evidence
is preserved separately under `reports/live-pilot/`:

- `experiments/dev-validation-pilot.template.yaml`: terminal Terra r3 contract; historical
  inspection only, never rerun
- `experiments/dev-validation-gpt54mini-campaign-pilot-r1.yaml`: terminal fault-free primary
  campaign-pilot r1 contract; consumed once, inspection only, never rerun
- `experiments/dev-validation-gpt54mini-campaign-pilot-r2.yaml`: D-047 corrective primary
  contract; consumed once by accepted `run_afd5080a77a34995`, inspection only, never rerun
- `experiments/dev-validation-gpt54mini-pilot.yaml`: terminal mini r1 contract;
  historical inspection only, never rerun
- `experiments/dev-validation-gpt54mini-pilot-r2.yaml`: v2 corrective mini diagnostic;
  terminal r2 contract, historical inspection only, never rerun
- `experiments/dev-validation-gpt54mini-d037-r3.yaml`: terminal D-037 exercise diagnostic;
  historical inspection only, never rerun
- `experiments/dev-validation-gpt54mini-d037-r4.yaml`: terminal corrective D-037 diagnostic;
  consumed 25,000 per-call / 120,000 total token contract, inspection only, never rerun
- `experiments/dev-validation-gpt54mini-d037-r5.yaml`: D-041 profile-v3 diagnostic contract;
  consumed strict 25,000 per-call / 200,000 total contract; terminal inspection only, never rerun
- `experiments/dev-validation-gpt54mini-d037-r6.yaml`: D-043 profile-v4 controlled diagnostic;
  consumed exact hash once; terminal inspection only, never rerun
- `experiments/dev-no-memory.template.yaml`: consumed first six-task
  `no_memory` × 2 campaign; 12/12 terminal but evaluator 0/12, inspection only, never rerun
- `experiments/dev-validation-gpt54mini-investigation-v4-pilot-r1.yaml`: next
  `phase-evidence-v4` development-validation pilot, $2 cap
- `experiments/dev-no-memory-v4.template.yaml`: next six-task `no_memory` × 2 campaign,
  blocked until the v4 pilot passes, $20 cap

As of 2026-07-29 the official
[OpenAI API pricing](https://developers.openai.com/api/docs/pricing) for the primary mini contract is $0.75/M
uncached input, $0.075/M cached input and $4.50/M output, with no separate published cache-write
rate. The suite pins `gpt-5.4-mini-2026-03-17`. Recheck the price within 72 hours of every live
invocation and record the installed SDK version, clean Git commit and execution timestamp.

Configure `OPENAI_API_KEY` in the host process without printing it. Leave `OPENAI_BASE_URL` and
`OPENAI_API_BASE` unset. The historical r1 inspection-only preflight is:

```powershell
git status --short
uv run patchloop evaluate `
  --suite experiments/dev-validation-gpt54mini-campaign-pilot-r1.yaml `
  --preflight-only
```

This is now inspection-only. It should report existing journal/result blockers for terminal
experiment `dev-validation-gpt54mini-campaign-20260730-r1`; do not add approval flags, delete
artifacts or reuse its consumed execution hash. Run `run_6993722014bf4e3b` exhausted the 20-call
model budget after applying a patch, passing the registered check, reading the final diff and
entering `REVIEW`, but before `finish_task`. All 20 provider responses completed and all input
pre-counts matched usage. The evaluator was not run and qualification remained 21/22 because the
call-budget terminal block is not a versioned valid ending.
See the
[primary r1 evidence record](../reports/live-pilot/dev-validation-gpt54mini-campaign-20260730-r1.json)
for the source/postmortem separation and hash-bound public patch.

The D-047 offline contract uses 21 total model calls for every future primary/development/core
condition and `model-generation-block-v2` for deterministic next-generation model/tool/wall
counter exhaustion. It does not reserve a privileged `finish_task` call. Its corrective r2
execution hash
`sha256:eb13280308f3f2642504da8493982543bb466d9bafaa5031b727dd4503003411`
was consumed exactly once by `run_afd5080a77a34995`. The run used 7 model and 8 tool calls,
39,171 input + 4,523 output tokens and `$0.04973175`; official hidden/regression/scope/safety and
qualification 23/23 passed. Inspect its portable record and never invoke the suite/hash again:

```powershell
Get-Content reports/live-pilot/dev-validation-gpt54mini-campaign-20260730-r2.json
```

The first `dev-no-memory-20260728` campaign then completed all 12 rows, but all 12 were qualified
agent failures and none reached the evaluator. It is immutable loop diagnostic evidence, not a
no-memory performance baseline or automatic memory-index source. D-048 adds condition-neutral
investigation continuity. Its fresh no-call pilot preflight is:

```powershell
git status --short
uv run patchloop evaluate `
  --suite experiments/dev-validation-gpt54mini-investigation-v4-pilot-r1.yaml `
  --preflight-only
```

This command does not call the provider. Review the clean execution hash and blockers first; a
paid invocation still requires a separate approval capped at $2.

The original checked-in mini suite refers to terminal experiment
`dev-validation-gpt54mini-pilot-20260729-r1`. Its immutable run
`run_d4fea5e7198b4abc` passed prompt-token trace qualification but failed before evaluation.
Inspect it only with:

```powershell
uv run patchloop evaluate `
  --suite experiments/dev-validation-gpt54mini-pilot.yaml `
  --preflight-only
```

Do not add approval flags or execute this historical suite again.

The corrective r2 contract is also terminal. This inspection-only command should now report the
existing result/journal blockers:

```powershell
uv run patchloop evaluate `
  --suite experiments/dev-validation-gpt54mini-pilot-r2.yaml `
  --preflight-only
```

Do not add approval flags, delete the journal or execute this suite again. Its separately approved
hash `sha256:fc2649790241f9623ea259a05957a38d1063472a9f17998e9e489b5b3fad21ca`
was consumed exactly once by `run_4a9737ec91964dca`. The run reached the official evaluator and
passed v2 trace qualification, but hidden acceptance failed. It also showed that the stateless
retry after a rejected patch retained the candidate hash and error without restoring the candidate
body. The checked-in
[mini r2 evidence record](../reports/live-pilot/dev-validation-gpt54mini-pilot-20260729-r2.json)
preserves aggregate verdicts and portable patch hashes without private evaluator details.

The D-037 r3 contract is terminal as well. Approved execution hash
`sha256:c33a50abe48b554c37d95de4833d1d17ede816f4d128b9adc22e88c010e138e6`
was consumed exactly once by `run_e90f7c52aa134182`. The run made eight model calls and twelve
search/read tool calls, using 54,851 input and 6,079 output tokens for a calculated list-price
cost of `$0.06849375`. All eight input pre-counts matched provider usage. The final response used
the full 4,096-token per-call output allowance, including 3,989 reasoning tokens, and returned
`incomplete/max_output_tokens` without a complete tool call. The run therefore ended before any
patch, rejection, submission or evaluator execution. Qualification failed only
`prompt_token_integrity`; the D-037 feature had zero episodes and the diagnostic failed
`qualification_not_passed`. This is not evidence of input prompt truncation, total 90,000-token
budget exhaustion, or D-037 success/failure. The
[mini D-037 r3 evidence record](../reports/live-pilot/dev-validation-gpt54mini-d037-20260729-r3.json)
binds the aggregate result and local artifact identities.

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

The historical Terra r3 harness recounts only hunk line totals in the agent-visible gateway. It preserves the exact
raw patch for hashing, validates body/context/path and all policy checks, and uses the same raw
patch with reverse recount on rejection. It then verifies the pre-call diff hash and zero-untracked
workspace invariant. Rollback failure or state mismatch is a recovery error, not a recoverable tool
message. Hidden evaluator patch application remains strict.

The resulting historical Terra r3 `run_3cb86f8d70094a11` created a `trace-qualification-v1` artifact with
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
For a new v2 patch, this inventory also rehashes the `PatchPrepared` intent and every nested raw
patch, preimage and postimage CAS object.
Completed v2 evaluation evidence additionally rehashes the receipt, manifest, result, provenance
and every verifier evidence CAS object. A valid receipt lets a fresh process finish the same run
without rerunning the evaluator after a crash between evaluation and terminal commit.

Direct `patchloop run --model openai`, direct resume of an OpenAI run and direct fault injection
from an OpenAI baseline are blocked; all paid calls go through an approved suite. A failed started
attempt still persists its run ID, events, usage including cached/cache-write tokens, calculated
cost and terminal outcome. The suite halts after the first infrastructure, qualification or required
trace-exercise error and records remaining rows as not started.

Eleven paid pilot runs exist when this guide was updated. The additional corrective primary r2 is
an accepted official run; the eleven-pilot cumulative calculated list-price cost is
`$1.652716875`. The separate first 12-run development campaign makes 23 paid provider attempts and
raises the calculated total to `$3.045909375`. Actual invoice or free daily usage treatment was
not verified. Docker
availability, exact images,
credential presence, clean-worktree state and price age may still appear as preflight blockers for
the fresh v4 pilot and later v4 development campaign.

The D-037 offline gate and its single controlled live exercise are complete. The next request after a
rejected mutating-tool call receives the exact budget-bounded candidate bytes, content hash and
structured rejection reason. Historical v3 manifests activated this as
`context_policy_version=phase-evidence-v3`; current non-replay manifests use
`phase-evidence-v4`, which inherits that contract and adds a durable read/search investigation
ledger, semantic replay and corrective-tail admission. Qualification rehashes the candidate/result
CAS, actual request and v4 ledger evidence; the token guard records a no-generation event when the
full request plus response allowance cannot fit. Mini r2, r3 and r4 remain immutable traces. The corrective r4
contract fixed `max_output_tokens=25,000` and `max_total_tokens=120,000` together under diagnostic
profile `d037-rejected-patch-retry-v2`; changing only one member is rejected. R4 consumed execution
hash `sha256:bbb6dbdcab1c7561c868ae4cc40478d6e3401c5900feb59b8ea09ef38d9156a1`
exactly once as `run_826c1c7fb3d242c2`. Its 13 provider generations completed without
truncation, but the next REVIEW request was blocked locally because 8,583 exact input + 25,000
allowance exceeded the 28,563 remaining total-token budget. Do not use a naive runner `continue`
after an incomplete response: without an
explicit original-request/logical-turn contract it can move the D-037 latest-model boundary past
the rejected candidate.

D-041 fixes the next r5 contract without changing that strict admission rule. Its 200,000-token
diagnostic budget is derived as
`91,437 + 3 × (10,031 + 25,000) = 196,530`, rounded up. The conservative reserve is
`(200,000 + 25,000) × $4.50/M = $1.0125`, below the unchanged $2 cap. Newly emitted exact-request
no-generation payloads use `model-generation-block-v1`; a correctly bound generic block can preserve
trace qualification without being counted as a rejected-patch retry. Historical unversioned r4
remains 21/22. R5 injects no synthetic rejection and has no automatic retry.

R5 consumed execution hash
`sha256:97249f05deda8e59118fdac0dd6f62f44c18b086ecb16bface2cc4d0f41a3a12`
exactly once as `run_0ad8676d42614fbf`. All 18 provider generations completed, and all 18 exact
input pre-counts matched provider usage with truncation disabled. The run used 121,366 input and
9,913 output tokens for a calculated list-price cost of `$0.135633`. Its submitted one-file,
one-line replacement passed official hidden, regression, scope and safety evaluation, and
`trace-qualification-v2` passed 23/23. No mutation was rejected, so the retry feature has zero
episodes and the diagnostic is terminal
`inconclusive/retry_episode_not_observed`. Preserve the run and do not rerun it. The checked-in
[mini D-037 r5 evidence record](../reports/live-pilot/dev-validation-gpt54mini-d037-20260730-r5.json)
binds the aggregate result and portable public-source patch.

```powershell
git status --short
.venv\Scripts\python.exe -m pytest tests/test_context.py tests/test_agent_runtime.py tests/test_trace_qualification.py
.venv\Scripts\python.exe -m pytest tests/test_live_pilot_evidence.py
.venv\Scripts\python.exe -m pytest
```

The r3, r4 and r5 diagnostics are now terminal. These commands are inspection-only and must never be
given approval flags:

```powershell
uv run patchloop evaluate `
  --suite experiments/dev-validation-gpt54mini-d037-r3.yaml `
  --preflight-only

uv run patchloop evaluate `
  --suite experiments/dev-validation-gpt54mini-d037-r4.yaml `
  --preflight-only

uv run patchloop evaluate `
  --suite experiments/dev-validation-gpt54mini-d037-r5.yaml `
  --preflight-only
```

It should report the existing journal/result blocker. Do not delete those artifacts or rerun the
suite. Each `experiment-diagnostic-v1` requirement was part of its consumed execution hash. The
mini diagnostic remains outside the current primary campaign gate.

R4 was required to exercise a rejected mutating-tool retry to validate D-037; ordinary progress
alone was insufficient. It stopped before submission, so the machine predicate remains unmet:

```text
evaluation_reached == true
AND retry_episode_count >= 1
AND verified_retry_count == retry_episode_count
AND failed_source_failure_sequences == []
```

A zero-episode run that reached the evaluator is `TraceExerciseInconclusive`, not a task or generic
qualification failure. Evaluator non-arrival is `TraceExerciseFailed`. R3 is the latter because
generic qualification failed before evaluation; r4 is also failed because its generic REVIEW
budget block is unversioned and evaluation was not reached. Neither zero episode is an
inconclusive result. R5 is exactly that case: generic qualification and task evaluation passed, but
zero retry episodes make the diagnostic inconclusive. Never reuse any consumed hash. Do not create
another paid diagnostic merely to wait for an accidental rejection.

D-043 resolves that disposition with a new controlled r6 suite. Before any paid approval, run its
offline gateway/recovery/qualification tests and inspect the unapproved preflight:

```powershell
.venv\Scripts\python.exe -m pytest `
  tests/test_tool_gateway.py `
  tests/test_agent_runtime.py `
  tests/test_experiments.py `
  tests/test_trace_qualification.py

uv run patchloop evaluate `
  --suite experiments/dev-validation-gpt54mini-d037-r6.yaml `
  --preflight-only
```

The preflight must remain blocked on live approval/hash until the repository is clean and the exact
execution hash is reviewed. Do not pass approval flags without a new explicit approval for that
hash and the $2 cap. R6 may run at most once. It must show exactly one controlled rejection, zero
`PatchApplied` for that rejected action, exact next-request rehydration and evaluator arrival.
Official task success remains a separate result.

The approved hash
`sha256:d6a756dc69a7cf6e024d541b64a458a940ec41bdfeb3c403a3f01c539660e67b`
was consumed exactly once by `run_73f5aaf7328a4ea5`. The run passed the controlled diagnostic,
official task evaluation and trace qualification; its aggregate is preserved in
[the r6 evidence record](../reports/live-pilot/dev-validation-gpt54mini-d037-20260730-r6.json).
Inspect the existing result and never invoke that suite/hash again.

After that diagnostic gate, the separately approved fault-free primary r1 ran once and became the
terminal call-budget failure described above. Its exact final patch passed a separate no-model
Docker postmortem, but that does not change the missing submission/evaluator evidence. D-047
completed the offline 21-call policy and versioned deterministic model/tool/wall next-generation
terminal-block qualification. Corrective primary r2 then passed the official evaluator and trace
qualification, and the first 12-run campaign completed with evaluator arrival at 0/12. The campaign
also showed repeated/covered inspections and no durable within-run investigation
continuity. This co-occurrence diagnoses the v4 harness gap; it does not establish that the gap
caused every failure. Those consumed suites remain immutable.

D-048 closes that harness boundary offline. Only a fresh
`experiments/dev-validation-gpt54mini-investigation-v4-pilot-r1.yaml` run with a distinct clean
execution hash and $2 approval that reaches the evaluator and passes
`trace-qualification-v2` including `investigation_evidence` and
`investigation_lifecycle` may have its run ID inserted into
`experiments/dev-no-memory-v4.template.yaml`. Development preflight then verifies the same model,
budget, harness commit, tool/context versions and exact runtime-contract hash before producing a
separate 12-row execution hash. That new campaign still requires a distinct approval capped at $20.

If a campaign halts or a row fails qualification/required trace exercise, `patchloop report` may
still export row-level CSV and available-case diagnostics for investigation. Qualification failure,
diagnostic inconclusive and diagnostic failure have separate exclusion reasons. Confirm
`analysis_ready=true` before using any aggregate as a result. With an incomplete or excluded matrix the report sets
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
