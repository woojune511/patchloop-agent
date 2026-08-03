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
docker image inspect patchloop-sandbox:py312 --format "{{.Id}}"
uv run pytest -q -p no:cacheprovider `
  tests/test_sandbox.py::test_docker_sandbox_has_no_network `
  tests/test_sandbox.py::test_docker_sandbox_is_non_root_read_only_and_does_not_forward_host_secret `
  tests/test_sandbox.py::test_docker_probe_is_non_root_networkless_and_workspace_read_only `
  tests/test_sandbox.py::test_docker_probe_runtime_and_kernel_process_boundaries `
  tests/test_agent_runtime.py::test_offline_v3_profile_agent_executes_real_probe_and_review
docker ps -aq --filter label=io.patchloop.managed=probe
uv run patchloop eval-task tasks/smoke/csv-quoted-newline `
  --patch tasks/smoke/csv-quoted-newline/reference.patch --backend docker
```

The Dockerfile pins the base digest used by the 2026-07-23 evaluator gate. Before a frozen experiment,
re-audit the base digest deliberately and record the built image digest in the experiment manifest; do not
silently float the tag. A Docker result is official only when the daemon is available and the evaluator
actually runs with the Docker backend. The five-test command must pass after the image build, and the final
managed-probe query must print no container IDs. It covers the profile-bearing probe/review lifecycle and
the D-061 immutable-image, read-only/networkless and kernel process-boundary contracts that the earlier
general pytest command may skip when Docker is unavailable.

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
- `experiments/dev-validation-gpt54mini-investigation-v4-pilot-r1.yaml`: consumed
  `phase-evidence-v4` development-validation pilot; inspect only, never rerun
- `experiments/dev-no-memory-v4.template.yaml`: consumed second six-task `no_memory` × 2
  campaign; terminal inspection only, never rerun
- `experiments/dev-validation-gpt54mini-completion-v6-pilot-r1.yaml`: consumed D-054/D-055
  Babel+Moto completion panel; 2/2 scope-compliant success and qualification, inspection only,
  never rerun
- `experiments/dev-no-memory-budget-pilot-20260731-r1.yaml`: consumed D-060
  HF Hub/PDM/pyfakefs no-memory diagnostic; inspect only, never rerun
- `experiments/dev-no-memory-corrective-pilot-20260731-r1.yaml`: consumed D-062
  corrective campaign; HF row only, original gate false, remaining rows not-started, inspect only,
  never rerun or continue

Superseded and pending D-052 contracts remain checked in for provenance:

- `experiments/dev-validation-gpt54mini-token-tail-v5-pilot-r1.yaml`:
  unexecuted `dev-validation-gpt54mini-token-tail-v5-20260730-r1`, now
  `superseded-unexecuted`
- `experiments/dev-no-memory-v5.template.yaml`: `dev-no-memory-v5-20260730-r1`;
  `pilot_run_id: null` and the unfrozen budget keep it non-executable
- `experiments/core.template.yaml`: future 96-run v5 matrix; the embedding revision remains a
  freeze marker, so this is not executable core authorization

The four experiment identities consumed under the 21-call/200,000-token contract
`dev-validation-gpt54mini-campaign-20260730-r2`, `dev-no-memory-20260728`,
`dev-validation-gpt54mini-investigation-v4-20260730-r1` and
`dev-no-memory-v4-20260730-r1` are immutable historical evidence. Do not edit, rebind or rerun
them under the D-052 budget. The D-055 experiment
`dev-validation-gpt54mini-completion-v6-20260731-r1` is likewise immutable after consuming its
exact approval hash once.

As of 2026-07-30 the official
[OpenAI API pricing](https://developers.openai.com/api/docs/pricing) for the primary mini contract is $0.75/M
uncached input, $0.075/M cached input and $4.50/M output, with no separate published cache-write
rate. The suite pins `gpt-5.4-mini-2026-03-17`. Recheck the price within 72 hours of every live
invocation and record the installed SDK version, clean Git commit and execution timestamp.

At those frozen repository rates, D-054 reserved `$5.625` under a `$6` suite cap. The completed
panel used a calculated `$0.15682575`, bringing the D-055 point-in-time usage-derived list-price total to
`$5.138372625`. D-052's `$14.85` development and `$118.80` core numbers remain unfrozen draft
reserves rather than current authorizations. Reserves are not measured spend or invoice
predictions. The project-wide `$150` cap is not machine-enforced; only each suite's
`cost_limit_usd` is enforced.

Inspect the consumed D-055 contract without approval flags and without a provider call:

```powershell
git status --short
uv run patchloop evaluate `
  --suite experiments/dev-validation-gpt54mini-completion-v6-pilot-r1.yaml `
  --preflight-only
```

It must report `HISTORICAL_SUITE_IMMUTABLE`. Do not add `--approve-live-cost` or
`--approved-execution-hash`, delete its journal/result or reuse the consumed hash. The portable
aggregate is
[`dev-validation-gpt54mini-completion-v6-20260731-r1.json`](../reports/live-pilot/dev-validation-gpt54mini-completion-v6-20260731-r1.json).

Inspect the current D-060 calibration and obtain its no-call preflight evidence with:

```powershell
git status --short
uv run patchloop evaluate `
  --suite experiments/dev-no-memory-budget-pilot-20260731-r1.yaml `
  --preflight-only
```

`--preflight-only` never constructs the agent or calls the provider. On an otherwise ready host,
the unapproved inspection must remain blocked by `LIVE_COST_NOT_APPROVED` and
`APPROVAL_HASH_MISMATCH` while reporting the candidate execution hash. A hash is approval-ready
only after the worktree is clean and the preflight binds the real Docker image identities,
installed OpenAI SDK and pricing verified within 72 hours. Do not add the approval flags or start
the suite until the user separately approves that exact hash. Do not run the pending v5
development template or core template.

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
investigation continuity. Its approved pilot execution hash
`sha256:cc2117dc698cdc991ccbcad45bbcfa4302f1ac265bdfdcc0753b60b2fda6eba2`
was consumed exactly once by `run_d7207fbb06184dd3`. The run passed official task evaluation and
trace qualification 25/25 with 10/10 exact input counts, one natural rejected-patch retry,
81,719 input + 5,952 output tokens and `$0.08807325`. Semantic replay and tail admission block
were not exercised in that trace. Never invoke the pilot suite/hash again.

Its run ID was bound to the v4 campaign. The campaign used the exact pilot commit
`5045e398646ec73d615785aeb95f02e877c34c90` in a clean detached worktree and shared the
host's external `.patchloop` runtime root through a junction. That root includes mutable SQLite and
workspaces; append-only applies to its event/artifact evidence histories. This preserved exact
pilot/current commit equality rather than relaxing the preflight. Execution hash
`sha256:9befd0bf8b2eb7dbc25999786713581b4b6c95f2ad45df56e2f098a9252e5bac`
was consumed exactly once. The current template is inspection-only:

```powershell
git status --short
uv run patchloop evaluate `
  --suite experiments/dev-no-memory-v4.template.yaml `
  --preflight-only
```

This command does not call the provider. On the original host with its ignored runtime root it
should report the existing terminal journal/result blockers. A clean checkout does not bundle that
raw `.patchloop` root and therefore cannot reproduce those blockers; their absence is not permission
to run. Do not add approval flags, delete artifacts, copy the experiment under a new ID or reuse the
consumed hash. Inspect the portable
[campaign evidence record](../reports/memory-development/dev-no-memory-v4-20260730-r1.json)
instead.

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

Before D-055, twelve paid one-run pilots existed. The v4 pilot
`run_d7207fbb06184dd3` is an accepted official run; the twelve-pilot cumulative calculated
list-price cost is `$1.740790125`. The first 12-run development campaign raises the total to
`$3.133982625`; the v4 12-run campaign adds `$1.84756425`, making 36 paid run attempts and
`$4.981546875` in calculated list-price cost. D-055 adds two completed attempts and
`$0.15682575`, making 38 paid run attempts and a D-055 point-in-time usage-derived total of `$5.138372625`. Actual
invoice or free daily usage treatment was not verified. D-052's development/core reserves remain
unfrozen drafts, not current paid authorizations. The `$150` project cap is not a global runtime
guard. No consumed suite/hash may be rerun.

The D-037 offline gate and its single controlled live exercise are complete. The next request after a
rejected mutating-tool call receives the exact budget-bounded candidate bytes, content hash and
structured rejection reason. Historical v3 manifests activated this as
`context_policy_version=phase-evidence-v3`; current non-replay manifests use
`phase-evidence-v5`. Historical V4 inherited that contract and added a durable read/search
investigation ledger, semantic replay and call-count corrective-tail admission. V5 adds a durable
token projection with `requested_input_tokens` priority, actual-token fallback only for `None`,
maximum observed input plus maximum positive consecutive growth, and pre/post-generation 5/4-turn
reservation. `remaining_tokens <= reserved_tokens` blocks only read/search before `ToolCalled`
with `token_tail_reserved`; apply/check/diff/finish remain available. The cutoff is nominal, not a
completion guarantee. Qualification rehashes the candidate/result CAS, actual request and v5
ledger/tail evidence; the strict token guard records a no-generation event when the
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

D-048 closes that harness boundary offline. The separately approved
`run_d7207fbb06184dd3` reached the evaluator and passed `trace-qualification-v2`, including
`investigation_evidence` and `investigation_lifecycle`; its run ID was inserted into
`experiments/dev-no-memory-v4.template.yaml`. D-050's exact-commit detached bridge retained the
same model, budget, harness commit, tool/context versions and runtime-contract hash. D-051 then
consumed the 12-row execution hash once: 12/12 rows terminated and qualified with no infrastructure
or diagnostic errors, but SCRR was 0/12. Nine rows stopped before evaluation on strict
exact-request budget reservation and three submitted patches failed hidden acceptance. Preserve the
campaign as diagnostic evidence; do not treat it as a valid performance baseline.

D-052 closes the token-aware corrective-tail implementation gate offline with
`phase-evidence-v5`, future `21/50/250,000/900` budgets and 25,000 per-call output. It versions
`investigation-policy-v2`, `investigation-ledger-v2`, `investigation-tail-policy-v2`,
`context-build-evidence-v5`, `tool-admission-blocked-v2` and `trace-source-evidence-v5` while
retaining `trace-qualification-v2`. No provider call was made for D-052. The next gates are the
leak-safe structured review/deduplication of the three task failures and, only after that, a new
single v5 pilot with a separate execution hash and explicit approval.

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

## D-060 budget pressure and consumed D-062 evidence

Historical D-060 evidence can be diagnosed without changing it:

```powershell
uv run patchloop budget `
  --experiment dev-no-memory-budget-pilot-20260731-r1
```

The historical D-062 preflight can still be recomputed read-only:

```powershell
uv run patchloop evaluate `
  --suite experiments/dev-no-memory-corrective-pilot-20260731-r1.yaml `
  --preflight-only
```

The suite reports three memory-development tasks, no-memory repetition 1, embedded public review
contract hashes, `40/100/900000/1800`, output 25,000, run reserve `$4.1625`, total reserve
`$12.4875` and cap `$13`. Its corrective-only runtime contract binds v4/v7, the exact
prompt/tool-schema hashes and harness commit.

That authorization was consumed exactly once under execution hash
`sha256:464a6eca2597698ca35caa4d7c97173f1af792daec042c36d81b5b8189ae4031`. Inspect the persisted
experiment JSON and journal rather than invoking `evaluate` again:

```powershell
Get-Content .patchloop/experiments/dev-no-memory-corrective-pilot-20260731-r1.json
Get-Content .patchloop/experiments/journals/dev-no-memory-corrective-pilot-20260731-r1.jsonl
uv run patchloop budget `
  --experiment dev-no-memory-corrective-pilot-20260731-r1
```

Expected immutable observations are one terminal HF row `run_0ccfc8fd359a4785`, two not-started
rows, original gate false, 33 completed model calls, 875,908 tokens, `$0.8408853`, and a terminal
exact-request budget block before any `PatchPrepared`, `PatchApplied` or evaluator receipt. The
trace also contains 30 non-dispatched read/search admission blocks and seven patch-preview failures.
Original result, journal and qualification artifacts must not be edited or regenerated in place.
The independently identified qualifier reserve-version drift is recorded separately at:

```powershell
Get-Content .patchloop/qualification-corrections/v1/run_0ccfc8fd359a4785/qcor_8b6ff81250263bf37ebf8f0239de12719760db012a62ca81e4f124f2624870b6.json
```

It binds correction hash `sha256:a240256fe26eed6277b6668a985e2a20df6a94125cf7e7e813f25c3d4975961c`,
corrected qualification hash `sha256:803460fb5703c5d6423bd125f0b32b4e6d690114712367b5884ccdfad96e2b12`
and harness commit `b35bb91caf8a28313f305bd5507d0a4fba9079e8`.
The corrected failed-check list is empty and exact repeated creation preserved the correction file
SHA-256 `sha256:fc6c469a989a7109d0d6b0ac8f609171aba87cdf8c3df543dd25bc75916d49c9`.
This validates corrected trace integrity only; the canonical
qualification, original false campaign gate and failed task outcome remain unchanged.

Do not rerun or continue D-062. D-063 supplied the offline `phase-evidence-v8` gate and D-064 now
supplies a new one-row experiment identity and contract; neither changes the historical D-062 result.

## D-064 exact V8 live-pilot inspection only

D-064 was consumed exactly once. Do not add `--approve-live-cost`, reuse execution hash
`sha256:dcade27f9f89efd6c349db58cbe732c0c81f1bbaf3bbb05e6c14b4ca62f2b85c`, delete local evidence to
make the suite appear new, or rerun/resume this experiment. A no-call inspection is still safe:

```powershell
$env:UV_CACHE_DIR = ".uv-cache"
uv run patchloop evaluate `
  --suite experiments/dev-no-memory-saturation-v8-pilot-20260801-r1.yaml `
  --preflight-only
uv run pytest -q `
  tests/test_experiments.py `
  tests/test_live_pilot_evidence.py -k "d064 or saturation"
```

Preflight must remain `ready=false` with `HISTORICAL_SUITE_IMMUTABLE`; a checkout that retains raw local
evidence can additionally report existing-result/journal blockers. The portable sanitized record is
[`reports/live-pilot/dev-no-memory-saturation-v8-pilot-20260801-r1.json`](../reports/live-pilot/dev-no-memory-saturation-v8-pilot-20260801-r1.json).
When the original local artifacts are available, verify their byte identities without modifying them:

```powershell
Get-FileHash -Algorithm SHA256 `
  .patchloop/experiments/dev-no-memory-saturation-v8-pilot-20260801-r1.json,
  .patchloop/experiments/journals/dev-no-memory-saturation-v8-pilot-20260801-r1.jsonl,
  .patchloop/experiments/plans/dcade27f9f89efd6c349db58cbe732c0c81f1bbaf3bbb05e6c14b4ca62f2b85c.json,
  .patchloop/qualifications/run_45e3edc434d749f7.json
```

Expected raw file hashes are respectively `7f956827...849ac`, `f4b245b4...efc24`,
`e8c8c6a4...da51b` and `51797106...e807`. The separate canonical execution-plan hash is
`sha256:297261447db53b3c7a19fdc18a0bbda8326f04b4b6ab01d52c2c969ed66400c3`; it is not the plan file's
byte hash. The run established the V8 saturation/reset policy branch only. It did not submit or reach
the evaluator and therefore is not task-success, SCRR, baseline or memory-effect evidence.

## D-066-D-068 V9 offline gate, consumed pilot and correction inspection

D-066's focused, credential-free validation set is:

```powershell
$env:UV_CACHE_DIR = ".uv-cache"
uv run pytest -q `
  tests/test_context.py `
  tests/test_tool_gateway.py `
  tests/test_agent_runtime.py `
  tests/test_trace_qualification.py `
  tests/test_experiments.py
uv run ruff check .
git diff --check
```

The focused run collected 504 tests: 502 passed and two existing capability-dependent tests skipped.
The separate repository-wide run collected 879 tests: 872 passed and seven environment-dependent tests
skipped. Ruff and `git diff --check` passed. These are D-066 offline results, not reused D-064 evidence.

The checked-in source suite can still be inspected without authorizing a provider call:

```powershell
$env:UV_CACHE_DIR = ".uv-cache"
uv run patchloop evaluate `
  --suite experiments/dev-no-memory-review-evidence-v9-pilot-20260801-r1.yaml `
  --preflight-only
```

Do not add `--approve-live-cost` or `--approved-execution-hash`. The checked-in state intentionally
remains `live_cost_approved=false`, `approved_execution_hash=null`, `pilot_run_id=null`; it is a source
contract, not authority for a second paid run. Historical execution hash
`sha256:f1b7d78243af8c87e3ec83f9373312f171073e0713a23fbc51c909fac0be6982` was consumed exactly once
and must not be reused.

Inspect the immutable local result and append-only correction without calling the provider:

```powershell
$runId = "run_4c77b1102e224785"
$correctionId = "qcor_51b72504161eddf250e872cc533dbfc5a315c377971e8a6f19a74a380fe3c032"
Get-Content -Raw -Encoding utf8 ".patchloop/experiments/dev-no-memory-review-evidence-v9-pilot-20260801-r1.json"
Get-Content -Raw -Encoding utf8 ".patchloop/qualifications/$runId.json"
Get-Content -Raw -Encoding utf8 ".patchloop/qualification-corrections/v1/$runId/$correctionId.json"
Get-Content -Raw -Encoding utf8 "reports/live-pilot/dev-no-memory-review-evidence-v9-pilot-20260801-r1.json"
```

The canonical qualification must remain false with file SHA-256
`1e3558eeee6ab505fe313a3f75ab4ae958e85876010321b74500c8c7a3464d2c`; the correction file must be
separate with SHA-256 `2a78f098a0d5ff9782fd5e4385a1b56b2b23623475554f0f2c295cc2b99fba71`.
The correction records corrected qualification 33/33, but the experiment result must still show the
original false gate, hidden failure, `task_failure`, SCRR=false, comparison exclusion and memory
admission false. These commands are read-only; no provider credential is needed.

Inspect the consumed, immutable D-070 V10 contract without issuing a provider call:

```powershell
$env:UV_CACHE_DIR = ".uv-cache"
uv run --env-file .env patchloop evaluate `
  --suite experiments/dev-no-memory-coverage-review-v10-pilot-20260802-r1.yaml `
  --preflight-only
```

Do not add `--approve-live-cost` or reuse the consumed execution hash. The preflight may read API-key
presence from the host `.env`, but it must fail closed on the historical immutable suite before any
provider request.

Reproduce the D-071 V11 offline correction without loading `.env` or issuing a provider call:

```powershell
.venv\Scripts\python.exe -m pytest -q `
  tests/test_coverage_rejection_v11.py `
  tests/test_coverage_review_v10.py `
  tests/test_trace_qualification_v10.py `
  tests/test_web.py
.venv\Scripts\ruff.exe check .
.venv\Scripts\python.exe -m compileall -q patchloop
git diff --check
```

The focused test must exercise a durable structured rejection, fresh-runner reclaim, exact-anchor
recovery, two-rejection same-worker continuation, batched multi-check recovery, refreshed diff, complete
review, evaluator arrival and one mutation. Its tamper matrix must
reject missing/retagged source and recovery calls, forged source/refreshed diff bytes, forged clearing
feedback/build/review mirrors, malformed source coverage rows, missing prepared-patch intent,
cleared-request worker-claim drift, missing model-response tool declarations, orphan review/mutation,
old-worker activity across the designated restart boundary, duplicate outcomes and duplicate mutation. V10
compatibility remains a separate assertion; this command creates no live execution authority or cost.

Inspect the D-072 V11 live-readiness contract without loading `.env` or contacting a provider:

```powershell
Get-Content -Raw -Encoding utf8 `
  experiments/dev-no-memory-coverage-rejection-v11-pilot-20260802-r1.yaml
.venv\Scripts\python.exe -m pytest -q `
  tests/test_coverage_rejection_live_v11.py `
  tests/test_experiments.py
.venv\Scripts\ruff.exe check `
  patchloop/agent/coverage_rejection.py `
  patchloop/evals/coverage_rejection.py `
  patchloop/evals/runner.py `
  tests/test_coverage_rejection_live_v11.py `
  tests/test_experiments.py
git diff --check
```

The YAML must name exact purpose `memory-development-no-memory-coverage-rejection-pilot`, exact ID
`dev-no-memory-coverage-rejection-v11-pilot-20260802-r1`, one HF Hub/no-memory row,
60/100/1,200,000/1,800 and output 25,000, with reserve `$5.5125`, cap `$6`,
`live_cost_approved=false`, `approved_execution_hash=null` and `pilot_run_id=null`. Offline assertions
must keep generic V11 mock/no-experiment only and permit only this exact purpose+OpenAI pair as a future
exception. They must classify zero rejection as integrity-pass-capable but recovery-inconclusive, and fail
an observed rejection unless every structured public source/recovery/clearing CAS verifies.

These commands reproduce the historical offline contract only; they are not a clean-machine preflight and
do not create a new execution capability. The unit tests calculate a synthetic hash and exercise the
approval branch only inside a fake environment and temporary root. Do not add `--approve-live-cost`, load
`.env` or invoke `patchloop evaluate` for this suite as part of offline reproduction. The exact D-072 live
invocation has already consumed its approved hash and must not be repeated. Provider hard-kill/reclaim is
also a separate follow-up fault exercise rather than a requirement of this one-row contract.

The 2026-08-02 reference execution collected 322 focused tests with 321 passed/1
environment-dependent skipped and 1,022 repository tests with 1,015 passed/7 environment-dependent
skipped. Ruff, Python compileall and `git diff --check` also passed. These are offline results from
in-memory Responses doubles; they are not provider or cost evidence.

Inspect the D-073 portable seal for the one consumed D-072 invocation:

```powershell
Get-Content -Raw -Encoding utf8 `
  reports/live-pilot/dev-no-memory-coverage-rejection-v11-pilot-20260802-r1.json
```

The sealed record must identify exact execution hash
`sha256:12fb0fb8a02ffe464555bd23125fae18deb6e52e6b6448a482243c036cce080d`, run
`run_e2132144a8774b05`, completion gate `passed=true`, qualification 36/36, official evaluator arrival and
recovery status `inconclusive/rejection_not_observed`. It must report hidden fail with
regression/scope/safety pass, `task_failure`, SCRR=false, no budget binding, and usage 797,862 input +
64,465 output = 862,327 token, 35 model call, 57 tool call, 369,385ms and `$0.841833`.

The 17 rejected candidates/17 verified retries refer to rejected-patch mutation-preview recovery, while
the structured coverage rejection count is 0. Likewise saturated context count 17 and one post-saturation
`PatchApplied` do not make the coverage recovery diagnostic pass. A reproduction or report consumer must
not collapse these counters into one rejection type.

On the source host, the portable record can be traced back to the append-only experiment result, campaign
journal and `.patchloop/qualifications/run_e2132144a8774b05.json`; a clean checkout intentionally does not
vendor those large/private raw artifacts. Do not mutate them or invoke the suite again to “reproduce” the
result. Verify the portable seal and consumed-ID guard instead. D-073 performs no provider call and adds no
model cost; live hard restart remains unmeasured.

The sealed source was verified with 375 focused tests (374 passed and one environment-dependent skip) and
1,025 repository-wide tests (1,018 passed and seven environment-dependent skips). Ruff, Python compileall
and `git diff --check` also passed. These checks belong to the D-073 source seal; they are not a second live
invocation.

## D-074 no-call baseline-readiness audit

D-069~D-073 is an immutable diagnostic/evidence-seal history. Do not reproduce it by rerunning the HF Hub
V10/V11 suites, and do not copy their task-specific review sidecar into a generic development or core
manifest. The generic no-memory lane remains tool V2/context V5.

The following files are inspection inputs only:

```powershell
Get-Content -Raw -Encoding utf8 experiments/dev-no-memory-v5.template.yaml
Get-Content -Raw -Encoding utf8 experiments/core.template.yaml
Get-Content -Raw -Encoding utf8 `
  reports/live-pilot/dev-validation-gpt54mini-completion-v6-20260731-r1.json
Get-Content -Raw -Encoding utf8 `
  .patchloop/experiments/dev-no-memory-budget-pilot-20260731-r1.json
```

At the D-074 decision point, the `21/50/250,000/900` values in the two templates were stale, unvalidated
drafts. D-083 later replaced their future budget-policy fields, but the current templates remain non-runnable
until execution-plan runtime evidence, RunManifest and qualification support pass. Do not add
`--approve-live-cost`, compute an approval hash for them or run them as-is. The next reproducible live
artifact must instead come from a newly checked-in, small diverse development readiness panel whose exact
generic V2/V5 model/prompt/tool/context/budget tuple matches the intended no-memory baseline. Its process
gate requires terminal qualified official-evaluator rows with no infrastructure, qualification, diagnostic
or budget confound; hidden task success is reported separately and is not required.

After that panel passes, freeze the exact tuple and collect the no-memory baseline without tuning against
individual hidden failures. Provider hard-kill/reclaim reproduction remains part of the separate reliability
suite and is not a prerequisite for this fault-free baseline gate.

## D-075 generic readiness source audit

At the D-075 source-contract point, the exact suite was checked in and the following were read-only/no-call
inspection steps. The later approved hash has now been consumed; these commands remain useful for source audit,
not for producing or reusing live authority.

```powershell
Get-Content -Raw -Encoding utf8 `
  experiments/generic-baseline-readiness-v2v5-20260802-r1.yaml

uv run --cache-dir .uv-cache pytest `
  tests/test_model_adapter.py `
  tests/test_experiments.py `
  tests/test_report.py -q

uv run --cache-dir .uv-cache patchloop evaluate `
  --suite experiments/generic-baseline-readiness-v2v5-20260802-r1.yaml `
  --preflight-only
```

The preflight must report exactly four ordered rows across development-validation and memory-development,
tool v2/context V5, no public-review sidecar, `transport_max_retries=0`, a per-run reserve of `$3.9375`
and total reserve `$15.75`. Before approval its blocker set must include live-cost approval and execution-hash
mismatch; the API key value must never be printed. A dirty checkout, missing/pinned-image mismatch, package
drift, SDK drift or pricing older than 72 hours adds a fail-closed blocker and must be fixed before asking for
approval.

The suite hash can be inspected as source identity, but it is not an invocation approval hash. The live
execution hash also includes the clean Git commit, package/image/evaluator identities, randomized schedule and
fresh environment state. Running preflight on a different commit is expected to produce a different execution
hash. Do not write that hash into the source YAML or commit an approval toggle.

The predeclared live gate semantics for the separately approved one-time run were 4/4 terminal, qualified,
evaluator-reached and official-completed rows with zero infrastructure/qualification/diagnostic/budget
confounds. The number of hidden successes may be zero without invalidating readiness. Readiness rows remain
excluded from comparison and memory admission, and 850k remains unfrozen until a separate post-panel decision.
If that decision changes the budget/runtime/harness commit, run a new final-tuple readiness panel instead of
reusing the D-075 gate.

## D-076 D-075 live result inspection — do not rerun

The separately approved D-075 execution hash
`sha256:1709a9e9911f980aafe28cdd9fe9ed486367c134e2dc9e465c88e01f9462bd66` was consumed exactly
once. Do not invoke `patchloop evaluate` with live flags for this experiment ID or hash again. Inspect the
sanitized portable record and the diagnostic report instead:

```powershell
Get-Content -Raw -Encoding utf8 `
  reports/live-pilot/generic-baseline-readiness-v2v5-20260802-r1.json

Get-Content -Raw -Encoding utf8 `
  .patchloop/analysis/generic-baseline-readiness-v2v5-20260802-r1/report.json

Get-FileHash -Algorithm SHA256 `
  .patchloop/experiments/generic-baseline-readiness-v2v5-20260802-r1.json
```

The raw local result hash must be
`ba2670e8f1bb79e0af9cf56d02841014cc3e66d58db85b114459776af277d30d`. The observed gate is
4/4 terminal, 4/4 qualified, 2/4 official evaluator completion, zero infrastructure/qualification/diagnostic
errors and two budget-terminal rows, so it is false. `report.json` must retain `analysis_ready=false`, empty
ordinary metrics and the descriptive 2/4 SCRR only under diagnostic metrics. Local `.patchloop` artifacts are
hash-bound evidence and may be absent on a clean clone; the checked-in portable record is sanitized and excludes
provider bodies, secrets, private task specs, hidden assertions and reference patches.

The next 50/100/1,200,000/1,800 candidate is not a reproduction command or approved run. It requires a new
checked-in suite, clean execution hash and explicit cost approval.

## D-077 budget-only successor source audit and no-call preflight

D-077 assigns the new exact ID `generic-baseline-readiness-v2v5-20260802-r2`. Inspect its source and run only
offline tests before creating live authority:

```powershell
Get-Content -Raw -Encoding utf8 `
  experiments/generic-baseline-readiness-v2v5-20260802-r2.yaml

uv run --cache-dir .uv-cache pytest `
  tests/test_model_adapter.py `
  tests/test_experiments.py `
  tests/test_report.py `
  tests/test_trace_qualification.py -q
```

The exact contract must retain the four D-075 tasks and order, model/reasoning/tier, prompt V3, tool V2/context
V5, SDK retry 0, output 25,000, tool 100, wall 1,800 seconds, absent sidecar and fault-free policy. Only model
calls 40→50 and total tokens 850,000→1,200,000 may differ. The D-075 r1 source, consumed hash, run artifacts and
false gate must remain unchanged.

After all tracked source and documentation is committed and `git status --short` is empty, run the new suite's
preflight. This command may inspect API-key presence but must not send a provider request:

```powershell
uv run --cache-dir .uv-cache --env-file .env patchloop evaluate `
  --suite experiments/generic-baseline-readiness-v2v5-20260802-r2.yaml `
  --preflight-only
```

Do not add `--approve-live-cost` or an approved hash at this stage. On an otherwise ready host the output must
show the exact four-row schedule, 50/100/1,200,000/1,800 budget, 25,000 output, `$5.5125` per-run reserve,
`$22.05` total reserve and `$23` cap. It must bind the clean commit, task/private package, Docker image/evaluator,
SDK, randomized schedule, prompt/tool/retry and the official rate rechecked at 2026-08-02T13:11:37Z. Expected
authorization blockers remain live-cost approval and approved-execution-hash mismatch. Any dirty source,
package/image/SDK drift or stale pricing is an additional blocker and must be resolved before requesting approval.

The preflight-produced execution hash is ephemeral authority for that exact clean state. Do not write it into the
source YAML or change tracked files afterward. Present the hash and maximum `$23` to the user for explicit
approval. Until that separate approval, provider call, run ID, measured cost and readiness outcome remain absent.

## D-078 D-077 live result inspection — do not rerun

The separately approved D-077 execution hash
`sha256:de73e622fcaa4cec85191cceb01efdb0d27cc6a5a6b8f05c7cd4844df50763f5` was consumed exactly
once. Do not invoke `patchloop evaluate` with live flags for this experiment ID or hash again. Inspect the
sanitized record and diagnostic report instead:

```powershell
Get-Content -Raw -Encoding utf8 `
  reports/live-pilot/generic-baseline-readiness-v2v5-20260802-r2.json

Get-Content -Raw -Encoding utf8 `
  .patchloop/analysis/generic-baseline-readiness-v2v5-20260802-r2/report.json

Get-FileHash -Algorithm SHA256 `
  .patchloop/experiments/generic-baseline-readiness-v2v5-20260802-r2.json
```

The raw result SHA-256 must be
`22385cf6efd9b54de960cfe5b55c812ba74d3275ac9496f7db16fd0cb727e5fe`. The journal must contain ten
contiguous hash-bound events ending at
`sha256:0a65f0bd0e20caa4f1cedd41433a63f53c6aa2a965ee256531a0d71777ba4b62`. The observed gate is 4/4
terminal·qualified, 3/4 official evaluator, zero infrastructure/qualification/diagnostic errors and one
model-call budget terminal, so it is false. `report.json` must keep `analysis_ready=false`, ordinary metrics
empty and 1/4 SCRR only under diagnostic metrics. Local `.patchloop` evidence may be absent on a clean clone;
the checked-in record contains sanitized metadata and hashes, not provider bodies, secrets, hidden assertions or
private task specifications. D-078 authorizes neither a rerun nor another budget increase.

## D-079 workflow-completion probe source audit and no-call preflight

D-079 source를 먼저 읽고 exact one-row identity와 bounded observability-only policy를 확인한다.

```powershell
Get-Content -Raw -Encoding utf8 `
  experiments/pyfakefs-workflow-completion-probe-v2v5-20260803-r1.yaml

uv run --cache-dir .uv-cache pytest `
  tests/test_workflow_completion_probe.py `
  tests/test_experiments.py `
  tests/test_trace_qualification.py `
  tests/test_report.py -q
```

Source에는 exact pyfakefs task 한 개, `no_memory` repetition 1, dated mini medium/standard/default,
prompt V3, tool V2/context V5, SDK retry 0, output 25,000이 있어야 한다. Model/tool limits는 YAML `null`,
total token은 3,000,000, wall은 7,200초여야 한다. `null`은 call event와 usage 계측을 없애는 값이 아니라
`model-tool-observability-only-v1` 아래 call-count admission만 끄는 값이다. Exact-request, token, wall,
loop, cost, sandbox와 evaluator guard는 유지돼야 한다.

Offline verification과 tracked documentation이 끝난 clean commit에서만 다음 no-call preflight를 실행한다.
이 명령은 API-key presence를 검사할 수 있지만 provider request를 보내면 안 된다.

```powershell
uv run --cache-dir .uv-cache --env-file .env patchloop evaluate `
  --suite experiments/pyfakefs-workflow-completion-probe-v2v5-20260803-r1.yaml `
  --preflight-only
```

`--approve-live-cost`나 approved hash를 이 단계에 추가하지 않는다. Preflight는 exact task/package,
Docker image/evaluator, SDK, clean harness commit, prompt/tool/runtime, schedule과 fresh official pricing을
결속해야 한다. Expected source reserve는 `$13.6125`, cap은 `$14`이지만 preflight 시점의 공식 가격 freshness를
다시 검사한다. Dirty source, package/image/SDK drift, stale pricing, runtime/policy mismatch는 blocker다.

Preflight가 만든 exact execution hash와 최대 `$14`를 사용자에게 별도로 제시한다. 명시적 승인 전에는
live command를 실행하지 않는다. 당시 source/offline 단계에는 provider call, hash authority, user approval,
run ID/result, measured usage/cost, SCRR 또는 gate outcome이 없었다. 이후 approved exact experiment는 한
번만 실행됐고 아래 D-080 sanitized seal에 기록됐다. 결과를 재현할 때는 raw artifacts와 seal을 읽고 같은
ID를 재실행하지 않는다.

## D-080 D-079 live result and gate correction inspection — do not rerun

D-079 execution hash와 experiment ID는 이미 정확히 한 번 소비됐다. Live command를 다시 실행하지 말고
portable seal을 읽는다.

```powershell
Get-Content -Raw -Encoding utf8 `
  reports/live-pilot/pyfakefs-workflow-completion-probe-v2v5-20260803-r1.json

Get-Content -Raw -Encoding utf8 `
  reports/live-pilot/artifacts/d080-workflow-completion-gate-summary-correction.json

Get-FileHash -Algorithm SHA256 `
  reports/live-pilot/artifacts/d080-workflow-completion-gate-summary-correction.json

Get-FileHash -Algorithm SHA256 `
  .patchloop/experiments/pyfakefs-workflow-completion-probe-v2v5-20260803-r1.json

Get-FileHash -Algorithm SHA256 `
  .patchloop/qualifications/run_606349c2c56342d4.json
```

Local raw files가 남아 있다면 hashes는 각각 experiment result
`c9f85ac52b0b3933625966c2bd6af1f6b57bdc974f2c141aa74bd21a2700ee28`, qualification file
`4d7a15f9984394b6ab798f78e391c6b0d5632bc0e6d4d4c9c4876eb5028c8168`이어야 한다. Local
`.patchloop` files는 clean clone에 없을 수 있으며 portable record는 private/provider content가 아니라
sanitized metadata와 hashes만 가진다.

Correction manifest의 portable file hash는
`sha256:45a73a5000befa4f4d0ccbde739c686778f25a77cafe245a1529c35671bda3dd`이고 bytes는 4,591이어야
한다. Main portable record의 compact pointer와 manifest body를 함께 검사한다.

```text
original_completion_gate.passed = false
original_completion_gate.call_guard_contract_passed = false
original_completion_gate.immutable = true

gate_summary_correction.correction_id =
  gcor_6552d8277d70fba7f296b0aee837a8f497be8384cce7fea4521cb39de1e19861
gate_summary_correction.semantic_body_hash =
  sha256:6552d8277d70fba7f296b0aee837a8f497be8384cce7fea4521cb39de1e19861
gate_summary_correction.correction_harness_commit =
  7e40e27446bcf011f700c219a96983e5670422f4
gate_summary_correction.original_gate_passed = false
gate_summary_correction.corrected_gate_passed = true
gate_summary_correction.replaces_original_gate = false

manifest.semantic_body.correction_harness.projection_schema_version =
  qualification-gate-check-projection-v1
manifest.semantic_body.projection_contract.outer_keys =
  [disabled_call_guard_contract]
manifest.semantic_body.projection_contract.inner_keys =
  [check_count, check_id, passed, schema_version]
manifest.semantic_body.original_completion_gate.schema_version =
  workflow-completion-probe-gate-v1
manifest.semantic_body.original_completion_gate.passed = false
manifest.semantic_body.corrected_completion_gate.schema_version =
  workflow-completion-probe-gate-v1
manifest.semantic_body.corrected_completion_gate.passed = true
manifest.semantic_body.claims_boundary.original_gate_replaced = false
manifest.semantic_body.claims_boundary.task_success = false
manifest.semantic_body.claims_boundary.scrr = false
```

Correction ID의 digest와 `semantic_body_hash`가 같아야 한다. 이 semantic body가 source identity,
correction harness, projection contract, exact cause, original/corrected gate의 전체 payload와 claims boundary를
모두 결속하므로 일부 field만 떼어 새 correction이라고 주장할 수 없다. Forward consumer는 outer/inner key
set을 정확히 검사하며 `check_count`는 Python `bool`을 포함한 truthy 값이 아니라 strict integer `1`이어야
한다. 따라서 `true`, `1.0`, `"1"`은 모두 거부한다.

Forward projection과 seal validation은 provider를 호출하지 않는 offline command로만 수행한다.

```powershell
uv run --cache-dir .uv-cache pytest `
  tests/test_workflow_completion_probe.py `
  tests/test_live_pilot_evidence.py -q
```

Final verification evidence는 focused 331 passed, repository-wide 1,162 collected 중 1,155 passed/7
environment-dependent skipped다. Ruff, Python compileall, JSON parse와 `git diff --check`도 통과했다. D-080
verification의 provider call은 0이고 추가 model cost는 `$0`이다. Hidden assertion,
private evaluator output 또는 reference patch를 reproduction 절차에서 열거나 portable record에 넣지 않는다.

## D-081 r3 source audit and D-082 immutable measured-result inspection

D-081 exact source identity와 public derivation, D-082 portable measured report만 inspect한다.
Consumed D-075/D-077/D-079/D-080/D-081 live command를 재실행하지 않는다.

```powershell
Get-Content -Raw -Encoding utf8 `
  experiments/generic-baseline-readiness-v2v5-20260803-r3.yaml

Get-Content -Raw -Encoding utf8 `
  reports/live-pilot/artifacts/d081-condition-neutral-budget-candidate.json
```

Source에는 D-075/D-077과 같은 ordered Babel, Moto, pyfakefs, HF Hub task, `no_memory` repetition 1,
dated mini medium/standard/default, prompt V3, tool V2/context V5, SDK retry 0과 output 25,000이 있어야 한다.
Model/tool limit은 둘 다 YAML `null`, total token은 2,400,000, wall은 1,800초여야 한다. Null counter는
`model-tool-observability-only-v1` telemetry이며 exact-request, token, wall, cost, loop, sandbox,
constrained-tool와 evaluator guard를 제거하지 않는다.

Derivation artifact의 arithmetic은 다음 값과 일치해야 한다.

```text
token subtotal = 1,790,707 + 84 * 2,000 + 25,000 = 1,983,707
unrounded = 1,983,707 * 1.2 = 2,380,448.4
rounded token budget = 2,400,000

unrounded wall = 856.559 * 2 = 1,713.118 seconds
rounded wall budget = 1,800 seconds

per-run reserve = (2,400,000 + 25,000) * $4.50/M = $10.9125
four-row reserve = $43.65
suite cap = $44
```

Runtime/evidence/gate schema는 각각 `generic-baseline-runtime-contract-v2`,
`generic-baseline-runtime-evidence-v2`, `generic-baseline-readiness-gate-v2`여야 한다. Gate는 네 row
각각의 `qualification-gate-check-projection-v1` exact-one `disabled_call_guard_contract`를 요구한다.
Historical generic v1이나 workflow probe v1을 r3 의미로 재해석하지 않는다.

Historical D-081 source-stage offline validation은 다음 결과로 완료됐다.

```text
pytest: 1,204 collected; 1,197 passed; 7 environment-dependent skipped
ruff: passed
python compileall: passed
git diff --check: passed
provider calls: 0
model cost: $0
```

Consumed D-081 suite를 다시 preflight하거나 실행하지 않는다. D-082 portable report와 source derivation을
읽고 hash를 검증한다.

```powershell
$derivation = `
  "reports/live-pilot/artifacts/d081-condition-neutral-budget-candidate.json"
$report = `
  "reports/live-pilot/generic-baseline-readiness-v2v5-20260803-r3.json"

Get-FileHash -Algorithm SHA256 -LiteralPath $derivation
Get-FileHash -Algorithm SHA256 -LiteralPath $report
Get-Content -Raw -Encoding utf8 $report | ConvertFrom-Json | Out-Null
```

Expected derivation SHA는
`sha256:6f871c13aee71043c20c54c72a93667600462e8369483e9354507a94d0063193`, portable report SHA는
`sha256:2a8f650e73e01aed9d629290627999232ec6aebd1769d2179bc22f084ddbede2`다. Report는 source commit
`b4c79242bb0a94eed50530116205323e78c7d21a`, execution hash
`sha256:446b60568795c585856468064fa1aa11a9d85a8e8806e6c71b3b19ab1aa12579`, raw result SHA
`sha256:f8a2cd25916290ae02e46b484519cc01dedbe50097326085524a88bb9b324f83`, journal file SHA
`sha256:52626ba6d7e61bc293ce327f4bf190e3b4118b20a2efe4d9de09d8186ce6afdd`와 final event hash
`sha256:f5537479c3c1e8c150f9cbfec5238d99c882eff537006773af8d9ddf9f78c254`를 포함해야 한다.

Measured predicate는 4/4 terminal·qualified·official evaluator, confound 0과 gate v2 pass다. Task outcome은
Babel 1/4 success와 세 hidden failure이며 regression/scope/safety 4/4 pass다. Usage는 111 model/175 tool,
1,929,316 token, 고정 rate 계산 비용 `$1.79426325`이고 billed invoice/free-tier charge가 아니다.
111/111 request completed/exact, truncation disabled, `store=false`, recovery 3/3, loop observation
50(pyfakefs 39)도 함께 확인한다. D-082 seal은 provider call 0/$0이며 final documentation-seal verification은
repository-wide 1,214 collected 중 1,207 passed/7 environment-dependent skipped와 focused D-082 8/8을
통과했다. D-081/D-082는 calibration-only이고 comparison/no-memory/memory/core를 열지 않는다.
96-run theoretical reserve `$1,047.60`과 `$150` cap 충돌은 별도 decision 전까지 unresolved다.

## D-083 offline comparison-budget freeze inspection — do not execute

D-083은 provider나 source template을 실행하는 절차가 아니다. Final artifact가 생성된 뒤 다음 path의
bytes와 SHA만 확인한다.

```powershell
$freeze = `
  "reports/live-pilot/artifacts/d083-condition-neutral-comparison-budget-freeze.json"

Get-FileHash -Algorithm SHA256 -LiteralPath $freeze
Get-Content -Raw -Encoding utf8 $freeze | ConvertFrom-Json | Out-Null
```

Expected SHA는 `sha256:e01c5f0107592e1c29c1ec8264f32bf05c979a718c353c37acb0d87fafd2cb88`이다.
Payload는 exact D-081 r3 source, pyfakefs observed-prefix minimum 1,303,223과 다음 arithmetic을 포함해야 한다.

```text
1,303,223 * 1.2 = 1,563,867.6
round_up(1,563,867.6, 100,000) = 1,600,000

budget = null model / null tool / 1,600,000 token / 1,800 seconds
output = 25,000
transport retry = 0
reserve = $7.3125/run, $87.75/12, $131.625/18, $702/96
```

Hidden outcome은 source arithmetic에 없어야 하고 D-080 historical minimum 1,815,619는
`outside_scope`여야 한다. `comparison_budget_policy_frozen=true` 외에 live execution, comparison
denominator, no-memory baseline, memory admission, core와 `analysis_ready`는 모두 false여야 한다. 기존
`$20`/`$150` cap과 historical D-081/D-082 artifact도 바뀌지 않아야 한다. Runtime/manifest/qualification
support가 pending인 동안 template preflight나 evaluate를 실행하지 않는다. 이 inspection의 provider call은
0이고 model cost는 `$0`이다. Sealed source의 final verification은 1,238 collected 중 1,231 passed와
7 environment-dependent skipped다.

## Inspect the D-086 measured pilot seal without provider access

Do not rerun the consumed D-085 experiment. Inspect the checked-in sanitized records and local raw evidence only.

```powershell
$portable = "reports/live-pilot/dev-validation-condition-neutral-v2v5-pilot-20260803-r1.json"
$correction = "reports/live-pilot/artifacts/d086-condition-neutral-comparison-pilot-budget-pressure-correction.json"

Get-FileHash -Algorithm SHA256 $portable
Get-FileHash -Algorithm SHA256 $correction
Get-Content -Raw -Encoding UTF8 $portable | ConvertFrom-Json | Out-Null
Get-Content -Raw -Encoding UTF8 $correction | ConvertFrom-Json | Out-Null

uv run pytest -o addopts='' -q tests/test_d086_condition_neutral_pilot_seal.py
uv run ruff check .
git diff --check
```

Expected portable and correction hashes are `sha256:520ae8408c4e090a2c66a0ed3b2c5c29738762eec1b4f7d87b9452e551635464` and
`sha256:bd42c50b7da2400eea8e340358e92ff2605a9fde8d866d3fdff1c9695b95aeb4`; final test evidence is `focused 64/64; repository-wide 1,416 collected, 1,409 passed/7 skipped; Ruff/compileall/JSON/git-diff checks passed; seal provider calls/model cost 0/$0`. When raw local evidence is
present, reconciliation must verify result
`sha256:e0c3c4c67adc8c157a5030c9a93e3fd106d6b7a12f596253ddf10582fe74b80a`, journal
`sha256:4c114059fad069526d95786c392b7ea36724443b7231b4426bb097ee0c2199c8`, final event
`sha256:93853c6367459bcae004789a9a2710c6be518078b21041ece0b160d9843e5a8b`, qualification
`sha256:11bda7b2f31bae453f21c4718fdcb4563a74e173e621fd8035f1ab8aa64f1293` and durable source evidence
`sha256:41d9b862fe5042b4838c53cd80c3318dc55dc5f0bd892962fecc20caba0b2105`.

The original result's budget-pressure error remains immutable. The correction must derive 1,526,799 token and
1,749,231ms wall headroom with binding `none` from the exact D-085 identity; it must reject near matches. The
portable record must contain no provider body, private task/hash, hidden assertion, patch body or reference patch.
Preflight/evaluate for the consumed D-085 ID must fail before runner construction even when local result/journal is
absent. These commands make zero provider calls and do not authorize the separate `$88` 12-run decision.

## Inspect the D-087 accrued-spend source gate without provider access

이 단계는 source/contract만 검증하며 OpenAI provider를 호출하지 않는다.

```powershell
$env:UV_CACHE_DIR = ".uv-cache"
$suite = "experiments/dev-no-memory-condition-neutral-accrued-cap-20260804-r1.yaml"
$artifact = "reports/live-pilot/artifacts/d087-condition-neutral-comparison-accrued-spend-cap-source-gate.json"
$legacy = "experiments/dev-no-memory-v5.template.yaml"

Get-FileHash -Algorithm SHA256 $legacy
Get-FileHash -Algorithm SHA256 $suite
Get-Content -Raw -Encoding UTF8 $artifact | ConvertFrom-Json | Out-Null

uv run pytest -o addopts='' -q `
  tests/test_d087_campaign_cost_policy.py `
  tests/test_d087_cost_journal.py `
  tests/test_d087_cost_runner.py `
  tests/test_d087_execution_binding.py `
  tests/test_d087_source_gate_artifact.py `
  tests/test_state_store.py
uv run ruff check .
uv run python -m compileall -q patchloop
git diff --check
```

Historical source hash는
`sha256:ef7f901a65764832f294e6e5d5706beb9f953523d669b292234d78bd7aa6a1a3`, 새 source hash는
`sha256:44de6899656c96830d3a0aa3326777848c5d632ef903eccc166839fa1caeaf79`여야 한다. Artifact는
`$5.38278975` mean projection, `$14.36724` empirical envelope, `$7.3125` full-next-run reserve,
`$21.67974` cap basis, `$25` campaign cap과 `$87.75` theoretical schedule bound를 함께 기록해야 한다.
Focused source/runtime/SQLite 검증은 68/68이어야 한다. 이 검증은 one-use reservation consumption,
canonical journal/root binding, marker 삭제와 journal reset 거부, prior durable settlement reload/repricing을
포함한다.
Artifact SHA는 `sha256:5f038999b65930a0f155d5eb00a530ac06b6e359de0bdac12fff22398aaa7efe`이고,
repository-wide 결과는 1,472 collected 중 1,465 passed/7 skipped다.

이 inspection은 candidate execution hash나 비용 승인을 만들지 않는다. 다음 단계에서는 먼저 이 변경을 clean
commit으로 봉인한 다음, 공식 가격·Docker·SDK·D-086 pilot admission을 다시 확인하는 no-call preflight만
실행한다. Provider 호출은 그 candidate hash와 최대 `$25`에 대한 별도 사용자 승인이 있을 때만 허용된다.
