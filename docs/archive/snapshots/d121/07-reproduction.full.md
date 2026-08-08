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

## D-110 frozen-index read-only validation

D-109 candidate에 결속된 exact freeze는 D-110에서 이미 한 번 실행됐고 one-use execution journal도 소비됐다.
따라서 `scripts/run_d110_index_freeze.py --execute`는 **재실행하지 않는다**. Retrieval, runtime memory injection과
core campaign도 아직 승인되지 않았다.

Clean clone에서는 checked-in portable frozen index, marker, receipt와 completion gate를 다음처럼 read-only로
검증한다. `--validate`는 provider, evaluator, embedding model이나 retrieval을 호출하지 않는다.

```powershell
.venv\Scripts\python.exe scripts\run_d110_index_freeze.py --validate --verify-current-implementation
```

Freeze를 실행한 원 workspace에 `.patchloop` runtime state가 그대로 남아 있을 때만 다음 live 대조를 추가한다.
Clean clone에는 ignored runtime directory가 없으므로 이 두 번째 명령의 성공을 기대하지 않는다.

```powershell
.venv\Scripts\python.exe scripts\run_d110_index_freeze.py --validate `
  --verify-live-runtime --verify-current-implementation
```

성공한 live validator는 runtime과 portable D-110 `index.json`이 모두 55,687 bytes/file SHA
`sha256:c0d2ec424e6cc10d64cdebd5ae493e0546fdfa08d09eb5f3269557b46025c6d0`이고, 두 `FROZEN`
marker가 모두 72 bytes/file SHA
`sha256:cdfe40b734135a30f66e34ff24469940063a7231a1fe0783420ee2ff816d9561`임을 확인한다. Marker의
정확한 bytes는 post-freeze content hash
`sha256:3a99e6c190672d1676bc4d13604de989899de9ddac85d282cc90c4d56f426c56` 뒤에 LF 한 바이트를
붙인 값이다. D-106 portable unfrozen index는 별도 historical pre-state로 남으며 55,644 bytes/file SHA
`sha256:c9b292f67fcb3c4bf524065801681e76c5df22142bbbb8b2db36d3c932df358a`에서 바뀌지 않았다.

Frozen file이 존재해도 retrieval authority는 열리지 않았다. 다음 검사는 portable D-110 index를 직접 전달하고,
query embedding을 만들기 전에 exact authorization error로 거부되는지 확인한다.

```powershell
@'
from pathlib import Path

from patchloop.contracts import MemoryCondition, Phase
from patchloop.errors import ContractError
from patchloop.memory.retrieval import retrieve_memory

index_path = Path(
    "reports/memory-development/artifacts/d110/"
    "idxgrp_563976c4443a725e287225cef1e718daf134fbb96574921cb9e020049ea52064/"
    "index.json"
)
expected = "D-106 group-aware index retrieval requires a later explicit authorization gate"
try:
    retrieve_memory(
        run_id="d110-read-only-retrieval-denial",
        query="read-only authorization check",
        phase=Phase.REVIEW,
        condition=MemoryCondition.STRUCTURED,
        index_path=index_path,
    )
except ContractError as exc:
    assert str(exc) == expected, str(exc)
    print(expected)
else:
    raise AssertionError("retrieval unexpectedly succeeded")
'@ | .venv\Scripts\python.exe -
```

실제 mutation 전에 D-110 focused test 16개와 legacy-freeze denial test 1개가 17/17 통과했다. Freeze 뒤 같은
focused set도 17/17을 256.5초에 통과했다. Pre-mutation과 post-freeze 수치는 서로 구분해 보존한다. Live validation과
direct retrieval-denial probe도 성공했고, 이 과정과 freeze 자체의 provider/evaluator call과 added model cost는
0/0/`$0`다. 다음 단계는 별도 retrieval-readiness authorization candidate를 준비하는 것뿐이며 retrieval 실행
권한이 아니다.

## D-111 retrieval-readiness authorization candidate validation

D-111은 frozen index를 읽어 현재 retrieval 경로의 준비 상태와 차단 요인을 오프라인으로 기록하고, 별도 승인이
필요한 one-use read-only scoring diagnostic의 범위만 고정했다. 다음 명령은 preflight, authorization candidate와
source gate를 deterministic하게 다시 만들고 검증한다.

```powershell
uv run python scripts/build_d111_retrieval_readiness_authorization_candidate.py
uv run pytest -q tests/test_d111_retrieval_readiness_authorization.py
```

Focused test는 8/8, 별도 related regression set은 7/7 통과했다. 생성된 exact candidate는 다음 세 값으로 식별한다.

- Candidate ID:
  `d111retrievalcandidate_bfde5cfe1c75cd90e8d78a0960b6d5ac7986420016d805e75b9725abdb20fe7a`
- Semantic body SHA:
  `sha256:bfde5cfe1c75cd90e8d78a0960b6d5ac7986420016d805e75b9725abdb20fe7a`
- 6,465-byte candidate file SHA:
  `sha256:f91aa284cc7a2add2516f44b4397b29e3aee5caa4cf0f83ec7913e6e5d7899d6`

Source gate ID/body SHA는
`d111_348e6dd21ad0816a3c4dc1889f2d7a421c7e41194c48b2fe5c7120513f6b3524`/
`sha256:348e6dd21ad0816a3c4dc1889f2d7a421c7e41194c48b2fe5c7120513f6b3524`이고, 3,308-byte gate file
SHA는 `sha256:d550cb048e417965e482c64682df4a1b91b90067f66b36e370912f5a8d759c16`이다.

이 단계에서는 retrieval function, query embedding, runtime memory injection, provider와 evaluator를 호출하지
않았고 frozen index와 marker도 바꾸지 않았다. Candidate는 실행 권한이 아니다. 다음 gate는 사용자가 위 exact
candidate ID, semantic body SHA와 file SHA를 별도 메시지에서 다시 제시하는 승인뿐이며, 그 전에는 proposed
one-use diagnostic, retrieval, runtime injection 또는 core campaign을 실행하지 않는다.

## Historical D-109 freeze-candidate verification

다음 명령은 checked-in D-109 pre-freeze artifact를 검증하며 index를 쓰지 않는다.

```powershell
uv run python -c "from patchloop.memory.d109_index_freeze_authorization import validate_d109_source_gate; print(validate_d109_source_gate(repository='.'))"
uv run pytest -q tests/test_d109_index_freeze_authorization.py
```

D-109의 `verify_live_runtime=True`는 freeze 직전 unfrozen pre-state만을 위한 historical 검사였으므로 현재 frozen
runtime에는 사용하지 않는다. Candidate 생성 script는 pre-freeze artifact만 재구성하며 D-110 completion을
재현하지 않는다. Actual freeze의 현재 증거는 위 D-110 portable validator로 확인한다.

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

## Inspect the D-088 measured campaign seal without provider access

Portable report는 다음 경로에 있다.

```text
reports/live-pilot/dev-no-memory-condition-neutral-accrued-cap-20260804-r1.json
```

Expected byte SHA는
`sha256:2e24bfb0d98c2a7b2b0d8b5bf80c238ae048d782ce43c1cf08a2c10a6c6b5269`다. 다음 검증은 provider를
호출하지 않는다.

```powershell
Get-FileHash -Algorithm SHA256 reports/live-pilot/dev-no-memory-condition-neutral-accrued-cap-20260804-r1.json
.\.venv\Scripts\python.exe -m pytest -q -o addopts='' tests/test_d088_condition_neutral_campaign_seal.py tests/test_d088_runtime_hardening.py
```

`.patchloop` raw evidence가 있는 원 execution host에서는 test가 result/journal/plan, 12 qualification, trace,
fixed-rate cost와 SQLite consumption까지 재검증한다. Raw evidence가 없는 clean machine에서는 portable hash,
claims boundary, leak-safe schema와 hard-consumed preflight guard를 검증하고 raw-only test는 명시적으로 skip한다.
D-087 suite를 다시 evaluate하지 않는다. 새 provider 실행은 이 reproduction 범위 밖이며 새 experiment와 별도
승인이 필요하다.

## Inspect the historical D-089 AnyIO source gate

D-089 source와 predecessor seal은 다음처럼 provider 없이 검사한다.

```powershell
Get-FileHash -Algorithm SHA256 experiments/dev-no-memory-condition-neutral-accrued-cap-20260804-r1.yaml
Get-FileHash -Algorithm SHA256 reports/live-pilot/dev-no-memory-condition-neutral-accrued-cap-20260804-r1.json
Get-FileHash -Algorithm SHA256 reports/live-pilot/artifacts/d087-condition-neutral-comparison-accrued-spend-cap-source-gate.json
Get-Content reports/live-pilot/artifacts/d089-anyio-budget-only-readiness-probe-source-gate.json -Raw | ConvertFrom-Json | Out-Null
.\.venv\Scripts\python.exe -m pytest -q -o addopts='' tests/test_d089_anyio_budget_only_probe.py tests/test_d089_source_gate_artifact.py
```

Expected immutable SHA는 D-087 suite
`sha256:44de6899656c96830d3a0aa3326777848c5d632ef903eccc166839fa1caeaf79`, D-088 portable seal
`sha256:2e24bfb0d98c2a7b2b0d8b5bf80c238ae048d782ce43c1cf08a2c10a6c6b5269`, D-087 source artifact
`sha256:5f038999b65930a0f155d5eb00a530ac06b6e359de0bdac12fff22398aaa7efe`다. D-089 source는
AnyIO 한 task, no-memory 한 번, mini medium/standard/default, retry 0, output 25,000과
`null/null/2,000,000/1,800`을 가져야 한다. `$9.1125`는 worst-rate reserve이고 `$10`은 approval cap이다.

Source gate 당시에는 clean commit에서 다음 no-call preflight가 `ready=false`, 정확히
`LIVE_COST_NOT_APPROVED`, `APPROVAL_HASH_MISMATCH` 두 blocker와 candidate execution hash를 출력했다. D-090
seal 뒤에는 다시 출력된 hash를 새로운 승인 capability로 취급하거나 승인 입력으로 사용하지 않는다.

```powershell
uv run --env-file .env patchloop evaluate `
  --suite experiments/anyio-workflow-completion-budget-only-v2v5-20260804-r1.yaml `
  --preflight-only
```

`--approve-live-cost`나 `--approved-execution-hash`를 붙이지 않으며 이 명령은 agent/provider를 호출하지 않는다.
현재 source에서 실행하면 `HISTORICAL_SUITE_IMMUTABLE`가 반드시 포함되어야 하고, local raw artifact 유무에 따라
result/journal blocker가 추가될 수 있다. D-089이나 D-087의 experiment ID, result 또는 run ID를 resume/reuse하지
않는다.

## Inspect the sealed D-090 result without rerunning D-089

```powershell
Get-Content reports/live-pilot/anyio-workflow-completion-budget-only-v2v5-20260804-r1.json -Raw |
  ConvertFrom-Json | Out-Null
.\.venv\Scripts\python.exe -m pytest -q -o addopts='' tests/test_d090_anyio_budget_probe_seal.py
```

Local raw evidence가 있는 원 실행 host에서는 같은 test가 result bytes/hash, journal chain, durable event count,
qualification read-only recomputation, token 합계와 model cost까지 비교한다. Raw runtime이 없는 clean machine에서는
portable contract와 static consumed guard를 검사하고 raw-only test만 skip한다.

`patchloop evaluate`로 D-089을 다시 실행하지 않는다. Seal 뒤 preflight는 local result/journal 유무와 무관하게
`HISTORICAL_SUITE_IMMUTABLE`를 반환해야 한다. Next-call minimum 2,014,913을 새 실행 budget으로 해석하지 않는다.

## Inspect the D-091 public-trajectory audit

```powershell
Get-Content reports/live-pilot/artifacts/d091-anyio-public-trajectory-audit.json -Raw |
  ConvertFrom-Json | Out-Null
.\.venv\Scripts\python.exe -m pytest -q -o addopts='' tests/test_d091_public_trajectory_audit.py
```

Execution host에서는 test가 D-087/D-089 durable public event metadata로 phase, token, tool, context, patch/check와
tail을 재집계한다. Raw state가 없는 clean machine에서는 D-088/D-090 portable SHA, arithmetic, strict boundary와
authority false를 검증하고 raw-only test만 skip한다. 이 절차는 experiment YAML, execution hash, cost approval과
provider capability를 만들지 않으며 D-087/D-089을 resume/evaluate하지 않는다.

## Inspect the D-092 public stall-policy replay

Portable contract와 pure simulator는 raw state 없이 검증할 수 있다.

```powershell
.\.venv\Scripts\python.exe -m pytest -q -o addopts='' tests/test_policy_replay.py tests/test_d092_policy_decision.py
Get-Content reports/live-pilot/artifacts/d092-public-policy-replay-decision.json -Raw | ConvertFrom-Json | Out-Null
```

Execution host에서만 immutable SQLite의 18개 durable public event projection을 재계산한다.

```powershell
.\.venv\Scripts\python.exe -m pytest -q -o addopts='' tests/test_d092_policy_replay_raw.py
.\.venv\Scripts\python.exe scripts/build_d092_policy_decision.py `
  --state .patchloop/state.sqlite3 `
  --recorded-at 2026-08-04T10:30:30Z `
  --compact
```

Builder는 stdout만 출력하고 SQLite를 `mode=ro&immutable=1`·`query_only`로 연다. Raw state가 없는 clean
machine에서는 raw-only test가 skip되어야 하며 frozen source bytes/SHA, semantic hash, strict projection, grid
arithmetic와 authority boundary는 계속 검증된다. 이 절차는 provider/evaluator를 호출하거나 run을 resume하지 않는다.

## Inspect the D-093 readiness-stage correction

Portable correction과 exact D-092 source binding은 raw runtime state 없이 검증할 수 있다.

```powershell
.\.venv\Scripts\python.exe -m pytest -q -o addopts='' `
  tests/test_d093_readiness_budget_correction.py `
  tests/test_d092_policy_decision.py `
  tests/test_d092_policy_replay_raw.py
Get-Content reports/live-pilot/artifacts/d093-readiness-budget-outcome-correction.json -Raw |
  ConvertFrom-Json | Out-Null
.\.venv\Scripts\python.exe scripts/build_d093_readiness_budget_correction.py --compact
```

Builder output을 checked-in artifact와 canonical JSON으로 비교하면 exact rebuild가 되어야 한다. Builder는 D-092
source가 한 바이트라도 달라지면 실패하며 provider SDK, runtime runner, SQLite 또는 evaluator를 import하지 않는다.
이 절차는 D-092 결과를 수정하거나 successor experiment config/hash/approval을 만들지 않는다.

## Inspect the historical D-094 high-headroom readiness source gate

다음 검사는 provider나 evaluator를 호출하지 않고 exact source/config/runtime binding만 재현한다.

```powershell
Get-Content experiments/generic-high-headroom-readiness-v2v5-20260804-r1.yaml -Raw |
  Out-Null
Get-Content reports/live-pilot/artifacts/d094-high-headroom-readiness-source-gate.json -Raw |
  ConvertFrom-Json | Out-Null
.\.venv\Scripts\python.exe -m pytest -q -o addopts='' `
  tests/test_d094_high_headroom_readiness.py `
  tests/test_d094_source_gate_artifact.py
.\.venv\Scripts\python.exe scripts/build_d094_high_headroom_readiness_source_gate.py --compact
```

Builder output은 checked-in artifact와 canonical JSON으로 exact 일치해야 한다. Artifact semantic body SHA는
`sha256:ab7be9ad2448d1016b88d451e271330844fc11d8fd4b890f08142618446ff929`, file SHA는
`sha256:6887936ec141496e35e3a9d3bd6c34cf04cf02d1849bf80208677151a692c6ed`다. 검사는 ordered three-task schedule,
mini/runtime tuple, 3M/3,600s ceiling, 2026-08-04T14:47:00Z standard pricing, `$40.8375` reserve와 `$41`
source cap을 확인해야 한다. 이 command는 no-call preflight나 execution hash를 만들지 않는다. 실제 provider 실행은
그 뒤 clean commit의 별도 preflight가 만든 one-use candidate hash와 max-`$41` 사용자 승인으로 정확히 한 번
수행됐으며, 그 invocation과 결과는 아래 D-095 seal에만 속한다.

## Inspect the sealed D-095 result without rerunning D-094

Portable report와 focused seal contract는 provider 없이 검사한다.

```powershell
Get-Content reports/live-pilot/generic-high-headroom-readiness-v2v5-20260804-r1.json -Raw |
  ConvertFrom-Json | Out-Null
.\.venv\Scripts\python.exe -m pytest -q -o addopts='' `
  tests/test_d095_high_headroom_readiness_seal.py `
  tests/test_d095_runtime_hardening.py
```

Original execution host에서는 같은 test가 raw result SHA, 8-event journal chain, execution plan, 세 run의
manifest/result/evaluator receipt, qualification 84/84와 read-only recomputation, 63 response token telemetry와
fixed-rate cost를 재검증한다. Raw runtime이 없는 clean machine에서는 portable wrapper/hash, leak-safe claims와
static consumed guard를 검증하고 raw-only 검사는 명시적으로 skip한다. Execution host에서 artifact를 다시 만들 때만
다음을 사용하며 출력은 checked-in portable JSON과 canonical-exact해야 한다.

```powershell
.\.venv\Scripts\python.exe scripts/build_d095_high_headroom_readiness_seal.py --compact
```

`patchloop evaluate`로 D-094를 다시 실행하거나 세 run ID를 resume하지 않는다. Seal 뒤의 no-call preflight는 local
result/journal 유무와 무관하게 `HISTORICAL_SUITE_IMMUTABLE`를 포함해야 한다. 3M ceiling과 관측된 0/3 SCRR을
각각 일반적인 충분 budget이나 no-memory performance estimate로 해석하지 않는다.

## Inspect the D-096 resource-policy and baseline-admission decision

D-096은 offline source decision이다. 다음 명령은 provider/evaluator를 호출하거나 experiment suite, execution hash,
approval capability를 만들지 않는다.

```powershell
Get-Content reports/live-pilot/artifacts/d096-condition-neutral-resource-policy-baseline-admission.json -Raw |
  ConvertFrom-Json | Out-Null
Get-FileHash reports/live-pilot/artifacts/d096-condition-neutral-resource-policy-baseline-admission.json `
  -Algorithm SHA256
.\.venv\Scripts\python.exe scripts/build_d096_resource_policy_baseline_admission.py --compact
.\.venv\Scripts\python.exe -m pytest -q -o addopts='' `
  tests/test_d096_resource_policy_baseline_admission.py
```

Builder stdout의 compact JSON을 parse한 payload는 checked-in artifact와 exact semantic equality여야 한다. Focused test는 D-095와 D-083/D-084,
D-094 pricing source, dataset manifest, 여섯 `public.yaml`과 historical schedule carrier의 source bytes/SHA를
검증하고, 한 source라도 바뀌면 fail closed해야 한다. 각 task file SHA는 manifest `public_spec_hash`와 일치해야
한다. 또한 다음을 확인한다.

- Future tuple이 mini medium/standard/default, retry 0, prompt V3, tool v2, context v5, output 25k,
  memory allowance 2k와 `null/null/3M/3,600s`인지
- Frozen memory-development task 6개 × repetition 2, seed `20260723`, expected row 12와 ordered schedule hash가
  exact한지
- Task success와 hidden acceptance가 campaign admission predicate가 아니며, official-evaluator task failure만
  leak-safe review 후보가 되는지
- Official branch와 canonical pre-call token/wall budget branch가 disjoint·exhaustive exact-one인지, budget branch의
  actor/CAS/no-provider-after와 submission/evaluator 부재가 강제되는지, issued response가 모두 `completed`인지
- D-083/D-084 v1이 historical로 보존되고 runtime v2와 새 12-row suite가 아직 미구현인지
- D-094 pricing block에서 `$13.6125`/run을 직접 재도출하는지, 12-run reserve `$163.35`와 current project cap `$150`의 conflict가
  `NO_MEMORY_AUTHORIZATION_CAP_PENDING`으로 닫혀 있는지
- Provider/evaluator call과 added model cost가 0/0/`$0`이고 live/result/memory/core/analysis authority가 false인지

이 검사를 통과해도 live run을 시작하지 않는다. 다음에는 별도 change에서 runtime v2와 exact successor suite,
non-censoring campaign cost policy를 구현한 뒤 clean no-call preflight, fresh pricing, 새 experiment ID/hash와
사용자 비용 승인을 받아야 한다.

## Inspect the D-097 exact no-memory source gate without provider access

D-097 source와 portable evidence는 provider/evaluator 없이 재현할 수 있다.

```powershell
Get-Content experiments/dev-no-memory-condition-neutral-3000k-20260805-r1.yaml -Raw | Out-Null
Get-Content reports/live-pilot/artifacts/d097-condition-neutral-baseline-source-gate.json -Raw |
  ConvertFrom-Json | Out-Null
Get-FileHash reports/live-pilot/artifacts/d097-condition-neutral-baseline-source-gate.json `
  -Algorithm SHA256
.\.venv\Scripts\python.exe scripts/build_d097_condition_neutral_baseline_source_gate.py --compact
.\.venv\Scripts\python.exe -m pytest -q -o addopts='' `
  tests/test_d097_condition_neutral_baseline_source_gate.py `
  tests/test_d097_runtime_v2.py `
  tests/test_d097_runtime_independent_review.py
```

Builder의 compact JSON은 checked-in artifact와 canonical semantic equality여야 한다. Expected semantic body SHA는
`sha256:05d952065136a45914e2fb3c44edcbb553732c9f33484c5412b9135062c6481b`, 21,029-byte file SHA는
`sha256:21ed073ad1fbe1985e7a46cabebbfdc836baa303c4434e0777152c1d2d88a777`다. Suite file identity는
2,741 bytes, `sha256:7b3c217388e86a2760694e98031b7ac974c8c450075e3433ee977e35b344abb0`다. Final focused/runtime/
repository test count는 전체 회귀가 끝날 때까지 pending이다. 이 검사는 runtime implementation을 artifact만으로
self-attest하지 않는다.

다음 identity를 서로 구분해 확인한다.

- D-096 pre-shuffle source identity:
  `sha256:e399114a6ea516821a30104a612f7222c0caf3f88def7b5d7472d15f7cc4c27b`
- Seed `20260723` expanded schedule identity:
  `sha256:dff4f38db99bcbc878e917a6c76e10a6c244701d2a8eb5ea4b43daf427a305ba`
- Expanded order: pyfakefs r1/r2, AnyIO r1, HF Hub r1, PDM r1, HF Hub r2, AnyIO r2,
  Loguru r1/r2, tox r2/r1, PDM r2
- Runtime schemas: `condition-neutral-comparison-runtime-contract-v2` and
  `condition-neutral-comparison-runtime-evidence-v2`

Artifact의 `live_cost_approved`, clean-preflight/hash/provider/evaluator/result/memory/core authority는 false이고
blocker는 `NO_MEMORY_CLEAN_PREFLIGHT_AND_164_USD_APPROVAL_PENDING`여야 한다.
`$164`는 prospective source cap이지 실행 승인이 아니다. 현재 checkout에서 `patchloop evaluate`를 호출하거나
approval flag/hash를 추가하지 않는다. 다음 단계는 이 source를 clean commit으로 만든 뒤 수행하는 별도 no-call
preflight다. 그 preflight가 Docker/evaluator, frozen dataset/task/environment, SDK, fresh official pricing과 commit을
묶어 one-use candidate hash를 만든 후에도, 사용자가 exact hash와 최대 `$164`, historical `$150` cap에 대한
campaign-scoped exception을 별도로 승인하기 전에는 paid invocation을 시작하지 않는다.

Future live inspection에서 기대할 cost boundary는 row별 SQLite consumption이 아니다. 첫 provider call 전 단 하나의
fsync된 `FullScheduleCostReserved`가 exact 12-row schedule 전체를 결속하고, runner가 동일 plan/CAS/journal을 각
row 전에 다시 검증하며, terminal row마다 deterministic settlement를 기록해야 한다. Live resume은 disabled다.
D-097 cost journal이 duplicate paid-call prevention을 구현했다고 기록하지 않는다. 기존 one-use execution hash가
authorization을 한 번의 sequential campaign invocation으로 제한하는 범위만 재현한다.

Final seal이 존재하는 future result에서는 `CampaignCompleted`의 execution/plan/cost-control/qualification/result
binding과 persisted result file hash를 다시 대조한다. Rehashed foreign binding이나 duplicate terminal event가
거부되는지는 evidence-integrity 검사이고, 이미 발생한 provider call의 중복 과금을 막았다는 증거로 쓰지 않는다.

Future result의 `condition-neutral-no-memory-baseline-admission-gate-v2`를 검사할 때는 12-row denominator
completion gate가 먼저 pass했는지 확인한다. Pass했을 때
campaign-level `memory_review_eligible=true`여야 하고, 실제 review candidate pool은 official-evaluator task failure
row로만 제한되어야 한다. Budget/infrastructure row는 후보가 아니며, 별도 review/dedup/leak gate 전에는 결과가
있더라도 `memory_admission_unlocked=false`여야 한다.

## D-098 portable baseline seal verification

D-098 seal은 API key, Docker execution이나 evaluator call 없이 기존 local D-097 evidence를 read-only로 검증한다.

```powershell
.\.venv\Scripts\python.exe scripts\build_d098_condition_neutral_baseline_seal.py `
  --output .patchloop\reproduction\d098-rebuilt.json

$expected = Get-Content -Raw -Encoding UTF8 `
  reports\live-pilot\dev-no-memory-condition-neutral-3000k-20260805-r1.json
$actual = Get-Content -Raw -Encoding UTF8 .patchloop\reproduction\d098-rebuilt.json
if ($expected -ne $actual) { throw "D-098 portable seal mismatch" }

.\.venv\Scripts\python.exe -m pytest -q -o addopts='' `
  tests\test_d098_condition_neutral_baseline_seal.py `
  tests\test_d098_runtime_hardening.py
```

Raw local evidence가 없는 clean machine에서는 tracked portable report의 outer key, semantic body hash, source
artifact binding, claims boundary와 leak-safe projection test만 검증하고 raw reconciliation test는 skip될 수 있다.
Raw evidence가 있는 source machine에서는 result/journal/plan/12 qualification과 SQLite trace projection을 다시
읽어 byte-for-byte 같은 report를 생성해야 한다. Builder는 원본 SQLite/WAL/SHM fingerprint를 고정하고 copied
database/WAL snapshot에서 qualification을 `persist=False`로 재계산한 뒤 원본 fingerprint의 exact 불변을 확인한다.
Original result, journal, run artifact와 qualification을 수정하지 않는다. Non-canonical `sealed_at`, durable state와
다른 manifest/result artifact 또는 budget provenance drift는 fail closed한다.

확인할 핵심 값은 12/12 denominator completion, 2 resolved/9 task failure/1 budget agent failure,
11,374,709 token, 613 completed provider calls, 1 pre-provider generation block, `$11.838408` list-price 계산과
9 review candidate다. 이 명령은 memory rule을 승인하거나 index를 만들지 않는다. Exact experiment ID는
hard-consumed되어 preflight가 `HISTORICAL_SUITE_IMMUTABLE`로 provider 전에 차단해야 한다.

## D-099 portable public-review proposal verification

API key, Docker, evaluator와 raw `.patchloop` state 없이 checked-in proposal을 검증한다.

```powershell
uv run patchloop memory validate-d099-review `
  reports/memory-development/d099-public-evidence-review-dedup-proposal.json
```

기대 결과는 review source 9, semantic group 5, candidate 3 group/6 source, hold 2 group/3 source,
selected public-event reference 74, portable patch 9와 두 leak scan pass다. `raw_evidence_validation=not_requested`,
human admission pending, admitted rule 0, review history/index/admission/core false여야 한다. 이 명령은 `.patchloop`를
만들지 않으며 historical v1 review validator나 memory store를 호출하지 않는다.

Raw evidence가 있는 source machine에서만 explicit deep audit를 실행한다.

```powershell
uv run patchloop memory validate-d099-review `
  reports/memory-development/d099-public-evidence-review-dedup-proposal.json `
  --require-raw-evidence

uv run python scripts/build_d099_public_review_proposal.py `
  --output .patchloop/reproduction/d099-rebuilt.json

$expected = Get-Content -Raw -Encoding UTF8 `
  reports/memory-development/d099-public-evidence-review-dedup-proposal.json
$actual = Get-Content -Raw -Encoding UTF8 .patchloop/reproduction/d099-rebuilt.json
if ($expected -ne $actual) { throw "D-099 proposal mismatch" }
```

Explicit raw mode는 copied SQLite/WAL의 allowlisted selected event와 CAS를 다시 읽고 exact proposal을 rebuild한다.
원본 SQLite/WAL/SHM byte·mtime·SHA fingerprint가 전후 같아야 한다. Raw state가 없으면 이 mode는 fail closed하며
portable validation으로 자동 downgrade하지 않는다. Rebuild 과정은 tracked patch copy를 같은 bytes로 교체할 수
있지만 failure review history, memory index, raw result, qualification과 original state는 수정하지 않는다.

Exact proposal semantic body SHA는
`sha256:63c74999242f6217f2a81c9c2dc22d618d2be137948580f93401341c4ea49574`, 77,942-byte
file SHA는 `sha256:24e34b02a66fc132d333bb51614a10786d38bc188b5550432a5f21f435f21493`다.

## D-100 mechanism-only source gate verification

다음 명령은 actual human decision journal이나 index를 만들지 않는다.

```powershell
uv run patchloop memory d100-status `
  reports/memory-development/d099-public-evidence-review-dedup-proposal.json

uv run patchloop memory validate-d100-source-gate `
  reports/memory-development/d100-group-review-projector-source-gate.json

uv run python scripts/build_d100_group_admission_source_gate.py `
  --output .patchloop/reproduction/d100-rebuilt.json

$expected = Get-Content -Raw -Encoding UTF8 `
  reports/memory-development/d100-group-review-projector-source-gate.json
$actual = Get-Content -Raw -Encoding UTF8 .patchloop/reproduction/d100-rebuilt.json
if ($expected -ne $actual) { throw "D-100 source gate mismatch" }
```

기대 상태는 mechanism implemented true, production human decision 0, admitted rule/preview entry 0/0,
admission/index/core false다. Source artifact는 5,048 bytes, semantic body SHA
`sha256:5ac180b32fef27d5937c1447e39f01bafda65ce6b5a3eef1992a7da45cab9b2b`, file SHA
`sha256:866bad69dad24dd908339330f27a24a388e64b453e6dc403363836292ea24e47`다. Validator는 semantic equality만이
아니라 이 deterministic pretty-JSON bytes와의 exact match도 요구한다.

Decision CLI는 실제 review 시에만 사용한다. 첫 append의 `--expected-tail`은 `none`, 이후에는 직전 명령의
`decision_hash`다. 아래는 형식 예시일 뿐 현재 production journal에 실행하지 않는다.

```powershell
uv run patchloop memory record-d100-decision `
  reports/memory-development/d099-public-evidence-review-dedup-proposal.json `
  --journal <explicit-journal-path> `
  --group <semantic-group-id> `
  --decision <approve|reject|continue_hold> `
  --reviewer-kind <human|maintainer_assisted|synthetic> `
  --reviewer <human-reviewer-label> `
  --rationale <public-evidence-only-rationale> `
  --action-id <caller-generated-id> `
  --expected-tail <none|sha256:...>
```

Reviewer kind/label은 인증된 전자서명이 아니라 self-attested provenance다. Complete five-group chain만
`validate-d100-decisions`와 `preview-d100-entries`를 통과한다. 두 명령은 `--expected-head <sha256:...>`와
`--expected-record-count <n>`을 함께 주면 external anchor도 검증한다. 이 preview도 index를 생성하지 않으며 future
admission seal은 explicit approval receipt, exact head/count와 journal file SHA를 반드시 결속해야 한다.
`d100-status`와 `validate-d100-source-gate`의 result schema는 각각
`memory-group-review-mechanism-status-d100-v1`과
`memory-group-review-source-gate-validation-result-d100-v1`이며 source-gate document schema와 구분한다.

## D-101 한글 검토 문서와 승인 절차 검증

다음 명령은 한글 검토 문서, 변경되지 않은 machine JSON과 source gate를 검증할 뿐 production journal, candidate,
receipt 또는 seal을 만들지 않는다.

```powershell
$env:UV_CACHE_DIR=(Resolve-Path .).Path + '\.uv-cache'
uv run python scripts/d101_group_admission.py validate-packet
uv run python scripts/d101_group_admission.py validate-source
uv run pytest -q tests/test_d101_group_admission.py
```

Exact checked-in identities는 다음과 같다.

- Packet JSON: 17,494 bytes, file SHA
  `sha256:e7d4acf48dbcac1e366964fc2ed8ceb924d9907f2cb2ddeed94a23ef816c93ef`, semantic body SHA
  `sha256:bd78712747b1718ed8c9c4f67324bd8f11f564c76c041d3108843b2da0224947`
- 사용자용 한글 Markdown: 12,872 bytes, file SHA
  `sha256:9fc8e51dc867d66672b7c5334402bafdc27759914df88df09d506a5832d479c5`
- Source gate: 3,807 bytes, file SHA
  `sha256:987cded0f469370f3f9c5542c8353f7153429d7b3743df9af003f2f594b3a275`, semantic body SHA
  `sha256:26838ab1e8097e47f53e712ce11d0d8a603cd4dd3dff408792f77f7d164fe4f9`

Machine JSON의 bytes/hash와 5개 문제 유형 순서는 바뀌지 않는다. 한글 Markdown은 내부 ID/hash와 영문 상태명을
사용자 본문에 표시하지 않고 1~5번 문제 유형별 `기억에 추가|사용하지 않음|나중에 결정` 선택과 이유만 요청한다.
Focused D-101 검증은 26/26, 관련 회귀는 399/399를 통과했다. Repository-wide는 1,810 tests를 수집해
1,803 passed/7 environment-dependent skipped/failure 0으로 끝났다.

`prepare-candidate`, `record-exact-approval`, `seal` subcommand는 D-101 source snapshot 당시 future mutating review 단계였다. 먼저 1~5번
문제 유형 각각에 대한 명시적 선택과 이유가 필요하다. 특히 `record-exact-approval`은 exact candidate ID/body/file SHA와
`EXPLICITLY_APPROVE_EXACT_D101_CANDIDATE` confirmation을 모두 요구한다. D-101 source reproduction에서는 이 세
subcommand를 실행하지 않았다.

## D-102 선택 기록과 candidate 검증

다음 명령은 checked-in journal, candidate와 portable gate를 read-only로 검증한다. Approval receipt나 seal을
생성하지 않고 memory index도 만들지 않는다.

```powershell
$env:UV_CACHE_DIR=(Resolve-Path .).Path + '\.uv-cache'

uv run patchloop memory validate-d100-decisions `
  reports/memory-development/d099-public-evidence-review-dedup-proposal.json `
  --journal reports/memory-development/d102-maintainer-assisted-group-decisions.jsonl `
  --expected-head sha256:4192b503768093e2134b7651da4922fcd9d5c2a064e0150a7f523adc952ac469 `
  --expected-record-count 5

uv run python scripts/build_d102_maintainer_assisted_decision_gate.py validate
uv run pytest -q tests/test_d102_maintainer_assisted_decisions.py
```

Exact expected identities는 다음과 같다.

- Journal: 5 records/correction 0, 7,829 bytes, head
  `sha256:4192b503768093e2134b7651da4922fcd9d5c2a064e0150a7f523adc952ac469`, file SHA
  `sha256:5c46e6b6a49e436794c1b118f96a9d05caa48a4cd4199e9791ec2ec4499327e3`
- Candidate: 31,148 bytes, ID
  `d101candidate_97c0d2499e2ffab97df6050b84af7c1d455e4af631a3e0fb58d50a084a62ac9d`, body SHA
  `sha256:97c0d2499e2ffab97df6050b84af7c1d455e4af631a3e0fb58d50a084a62ac9d`, file SHA
  `sha256:9620e99961010bc4c942728f1948cb50b3f067025b8d5a02ba579dd3a1b4e457`
- D-102 gate: 5,453 bytes, body SHA
  `sha256:27e6b50c156e2c590e4225302534c5fedca67596eae2c831d03d3a4810c11732`, file SHA
  `sha256:e8ff1cdecdb7b107593f43f0b68b564abab34668558a0bb367296e16fbcca373`

기대 decision 순서는 `approve, approve, continue_hold, continue_hold, approve`이고 reviewer kind는 모두
`maintainer_assisted`다. Candidate의 approved/rejected/continued-hold count는 3/0/2, preview entry count는 3이다.
Focused D-102 test는 6/6, D-097~D-102/memory/contracts/CLI/qualification related test는 405/405가 통과했다.
Repository-wide는 1,816 tests를 수집해 1,809 passed/7 environment-dependent skipped/failure 0으로 끝났다.

다음 단계에서 사용자는 candidate ID/body SHA/file SHA를 별도 메시지에서 정확히 다시 승인해야 한다. 그 승인
전에는 `record-exact-approval`과 `seal`을 실행하지 않는다. 현재 group 선택 메시지는 그 뒤에 생성된 candidate
snapshot의 승인으로 재사용할 수 없다.

## D-103 exact candidate 승인과 seal 검증

현재 checked-in receipt, seal과 portable gate는 다음 명령으로 read-only 검증한다. Provider/evaluator는 호출하지
않고 index도 만들지 않는다.

```powershell
$env:UV_CACHE_DIR=(Resolve-Path .).Path + '\.uv-cache'

uv run python scripts/d101_group_admission.py validate-seal `
  --seal reports/memory-development/d103-maintainer-assisted-admission-seal.json `
  --candidate reports/memory-development/d102-maintainer-assisted-admission-candidate.json `
  --receipt reports/memory-development/d103-exact-candidate-approval-receipt.json `
  --journal reports/memory-development/d102-maintainer-assisted-group-decisions.jsonl `
  --expected-file-sha256 sha256:af1e6ea8811445f26d542f34500d1a7b3919392bef00c98b71f4c26ded236e8e

uv run python scripts/build_d103_exact_candidate_admission_gate.py validate
uv run pytest -q tests/test_d103_exact_candidate_admission.py
```

Expected identities는 다음과 같다.

- Receipt: 6,245 bytes, ID
  `d101receipt_23c8ff9b5f8b91820d03a25242abaa02f1ec2af0357bd9b26c227882cf8f5f7a`, body SHA
  `sha256:23c8ff9b5f8b91820d03a25242abaa02f1ec2af0357bd9b26c227882cf8f5f7a`, file SHA
  `sha256:dad12cf181fee8e113d9da703795eb8ccb4a16be6014218ea923a919d0695031`
- Seal: 19,357 bytes, ID
  `d101seal_3dc67e77a0c8c2d9a94f6bea9138d179eb6d6ac1cda0d8b490a1eab3bfbe705e`, body SHA
  `sha256:3dc67e77a0c8c2d9a94f6bea9138d179eb6d6ac1cda0d8b490a1eab3bfbe705e`, file SHA
  `sha256:af1e6ea8811445f26d542f34500d1a7b3919392bef00c98b71f4c26ded236e8e`
- D-103 gate: 5,315 bytes, body SHA
  `sha256:4a542cd571ffc0b94b6f95e106fd2371425dd66f82cfa6091cc602905036fb1f`, file SHA
  `sha256:4602a579d7c11dd300e2f9bede38e8a6d7bf21c78a8fbfc255550b7d86f3d354`

Expected authority는 admitted rule template 3, open hold 2, memory source authoring true, actual source count 0,
index build/freeze false, core false다. Focused verification은 7/7, related verification은 497/497,
repository-wide는 1,823 collected 중 1,816 passed/7 environment-dependent skipped/failure 0이다.

## D-104 unindexed memory source 검증

다음 명령은 exact source 3개와 portable gate를 read-only로 다시 검증한다. Build 명령은 파일이 없을 때만 만들고,
같은 bytes의 retry만 허용하며 다른 기존 bytes를 덮어쓰지 않는다.

```powershell
$env:UV_CACHE_DIR=(Resolve-Path .).Path + '\.uv-cache'

uv run python scripts/build_d104_unindexed_sources.py validate
uv run pytest -q tests/test_d104_unindexed_sources.py
```

새 checkout에서 materialization을 재현할 때만 다음을 사용한다.

```powershell
uv run python scripts/build_d104_unindexed_sources.py build
```

Expected identities:

- Source collection ID:
  `d104collection_4017131c10c127f47b8ea68ff2d8c3c3265c2f6cb11c1b175dd52c23882bd399`
- Ordered source-set hash:
  `sha256:1168c8c9cfcaa3671f42391436bfff713c90f01baec468e5ef2509ddb95dbad2`
- Pyfakefs source: 5,188 bytes,
  `sha256:8a139248e3e53e3a563366c6a2f9ad213a6a164831bd3cef2a3e5b6cb37008e8`
- HF Hub source: 5,333 bytes,
  `sha256:87b1b751634d8c34ef125042e472807828a7820064f25e413a51d0755b5b51da`
- tox source: 5,416 bytes,
  `sha256:d5b22f7c2ca75a271cf60cd52eb9089f2fd54bec99f5c9a75d09c311e0311505`
- D-104 gate: ID `d104_61e44eb5609c05c97b84602bbaa4eb7bff84dd33af227cef18592aa2b6a32c11`,
  12,705 bytes, body SHA
  `sha256:61e44eb5609c05c97b84602bbaa4eb7bff84dd33af227cef18592aa2b6a32c11`, file SHA
  `sha256:8eeb26d6f5e0ff22658501afe54bd8cebe35896dc18b60f8f73355ec53190dd0`

Source record에는 `index_version`, embedding 또는 frozen state가 없어야 한다. Expected authority는 sources 3,
held sources 0, D-104-created actual MemoryEntry/render/embedding/index 0, build/freeze/retrieval/core false다.
Historical index state는 inspect/modify하지 않는다. Focused 30/30과 related 530/530이 통과했다.
Repository-wide는 1,853 collected 중 1,845 passed/7 environment-dependent skipped/1 failed다. 유일한 기존
order-dependent D-093 SQLite WAL/SHM invariant는 fresh isolated process에서 1/1 통과했으며 D-104 failure나
fix로 합산하지 않는다.

## D-105 deterministic render와 index 후보 gate 검증

Checked-in D-105 gate와 render의 exact validation은 provider, evaluator와 embedding model을 호출하지 않는다.

```powershell
$env:UV_CACHE_DIR=(Resolve-Path .).Path + '\.uv-cache'

uv run pytest -q tests/test_d105_renderer_authorization.py
```

새 checkout에서 missing render/gate를 materialize하거나 현재 exact bytes의 idempotent retry를 확인할 때는 다음
명령을 사용한다. 다른 기존 bytes가 있으면 덮어쓰지 않고 실패한다.

```powershell
uv run python scripts/build_d105_renderer_authorization_gate.py
```

Expected identities:

- Render 1: 1,191 bytes,
  `sha256:f1cd44ed10d527ff7f5c44dd0be4e6957810530cd055d3329da0d7962d3cec7c`
- Render 2: 1,164 bytes,
  `sha256:ab0273b575f76efd4ca9facda9540d87f2ea85e69a333cf87e4d7ac781287c2a`
- Render 3: 1,161 bytes,
  `sha256:00ceca8ed912a48f36ab26fb50b1d7eb428fe261a83b2bd84e231f0c6e786bf7`
- Ordered render-set SHA:
  `sha256:7b72fc94642d996fad5a0b199719c56bfecc8a8fc1bbe42b2060aa18e21d2667`
- Canonical joined bundle: 3,528 bytes,
  `sha256:572667d431aa75e4fe74bfc030a99f64245b77d9afa1c88e5d531129f708accf`
- Gate: ID/body SHA
  `d105_0f99c7d1cd1c371191073ead8d60636be9ea6040947d9c7f3522aba25bc3df70`/
  `sha256:0f99c7d1cd1c371191073ead8d60636be9ea6040947d9c7f3522aba25bc3df70`, 12,368 bytes, file SHA
  `sha256:db6303f3de834b3c36493f2863dcc5be3ca697490d18df15c86a18e7ee7b17eb`

Expected policy는 ASCII-subset UTF-8, NFKC-required input, LF/trailing LF, fixed whole-entry rendering과 maximum
2,000 provider input-token delta다. Future receipt는 canonical context의 `/selected_memory`만 JSON `null`에서 exact
bundle로 바뀌는 deep diff와 context-slot normalization 뒤 request equality를 증명해야 한다. `chars/4` estimate,
partial truncation과 model-text provenance는 없어야 한다.
Current gate의 provider exact count/receipt와 snapshot verification은 absent/false다. Focused 47/47와 related
550/550가 통과했다. Repository-wide는 1,900 collected 중 1,892 passed/7 environment-dependent skipped/1
pre-existing order-dependent D-092 raw replay SQLite WAL/SHM failure다. 그 exact test는 fresh isolated process에서
1/1 통과했다.

Gate evidence에는 inherited validator의 public submitted patch integrity read와 package initialization의 legacy
retrieval/store transitive import가 true여야 한다. Public patch text의 render 복사, patch 기반 새 rule authoring,
legacy API call과 historical index inspection/modification은 false여야 한다.

Embedding candidate는 다음 exact tuple이다.

```text
model: sentence-transformers/all-MiniLM-L6-v2
revision: 1110a243fdf4706b3f48f1d95db1a4f5529b4d41
normalize_embeddings: true
trust_remote_code: false
```

Gate가 결속한 dependency input은 다음과 같다.

- Install command: `uv sync --locked --extra memory`
- `pyproject.toml`: 1,032 bytes,
  `sha256:2e8395b0d26e0f4e686daa3481c18301e025417666db828da0e0425cfd5b3986`
- `uv.lock`: 240,131 bytes,
  `sha256:7cc04e0ad0fa5e94619612b322ce1e1f9113e5da405f62b8c9bc256ba0952d8c`
- Locked packages: `huggingface-hub==1.24.0`, `sentence-transformers==5.6.0`,
  `tokenizers==0.22.2`, `torch==2.13.0`, `transformers==5.14.1`

Current offline validation에는 `sentence-transformers` install이나 model download가 필요하지 않으며 이를
실행해서도 snapshot preflight 통과로 간주하지 않는다. Future locked preflight에서만
`uv sync --locked --extra memory`로 exact lock을 설치하고, revision snapshot file inventory/hash, offline reload와
384-dimension float32 normalized vector를 별도 artifact로 검증한다. Network가 필요한 이 단계와 실제 index build는
exact D-105 gate 승인 전에는 수행하지 않는다.

Expected authority는 render/token policy frozen, embedding revision candidate pinned와
`index_build_authorization_candidate=true`까지다. User approval receipt, provider exact validation, snapshot verified,
actual build authorization, MemoryEntry/embedding/index count, build/freeze/retrieval/runtime injection/core/analysis는
absent, 0 또는 false여야 한다. D-105는 provider/evaluator call 0/0, added model cost `$0`다.

## Historical D-106 locked snapshot과 unfrozen group index 재현

Memory dependency는 exact lock으로 설치한다. Windows sandbox에서 기본 uv cache가 충돌하면 repository 내부
cache를 사용한다.

```powershell
$env:UV_CACHE_DIR=(Resolve-Path .).Path + '\.uv-cache'
uv sync --locked --extra dev --extra memory
```

Checked-in portable evidence만 검증하는 focused test는 model download나 provider call이 필요하지 않는다.

```powershell
.venv\Scripts\python.exe -m pytest -q `
  tests\test_d106_locked_group_index.py `
  tests\test_memory.py
```

아래 build 명령은 D-106 unfrozen pre-state를 연구하는 별도 clean/isolated checkout에서만 사용한다. D-110 freeze가
완료된 현재 workspace에서는 실행하지 않고, checked-in D-106 portable file을 read-only로 검증한다. 이 명령은
Hugging Face에서 exact revision file 10개를 내려받을 수 있지만 OpenAI/evaluator는 호출하지 않는다. Existing
output이 다른 bytes이면 덮어쓰지 않고 실패하며 exact retry만 허용한다.

```powershell
$env:HF_HOME=(Resolve-Path .).Path + '\.patchloop\hf-home'
$env:HF_HUB_CACHE=$env:HF_HOME + '\hub'
.venv\Scripts\python.exe scripts\build_d106_locked_group_index.py
```

이미 exact snapshot이 있으면 network 없이 다음처럼 다시 검사한다.

```powershell
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
.venv\Scripts\python.exe scripts\build_d106_locked_group_index.py --no-download
```

Historical D-106 expected index ID는
`idxgrp_563976c4443a725e287225cef1e718daf134fbb96574921cb9e020049ea52064`다. Portable index file SHA는
`sha256:c9b292f67fcb3c4bf524065801681e76c5df22142bbbb8b2db36d3c932df358a`, snapshot manifest SHA는
`sha256:e497d8dad53f09ddc8b9fcc9b81e3ff778e002e120ab4254c72993d8611959cb`다. Token count는
218/220/207이고 max sequence length는 256이어야 한다. Runtime index directory에는 `index.json`만 있어야 하며
`FROZEN` marker가 있으면 D-106 pre-state 재현으로서는 실패다. 이는 current D-110 runtime에 marker가 없어야 한다는
뜻이 아니다. Current state는 문서 앞부분의 D-110 validator로 확인한다. 이 historical 절차는 index freeze,
retrieval 실험, provider token-count call 또는 core campaign을 승인하거나 실행하지 않는다.

## Historical D-108 provider token-count 완료 evidence 재검증

D-108의 one-use live capability는 이미 baseline과 with-memory count call 두 번으로 소비됐다. Live script나 같은
provider call을 다시 실행하지 않는다. Checked-in approval, journal, receipt와 completion gate는 다음 read-only
명령으로만 재검증한다.

```powershell
.venv\Scripts\python.exe -c "from patchloop.memory.d108_provider_token_count_execution import validate_d108_completion_gate; print(validate_d108_completion_gate())"
```

Expected 결과는 다음과 같다.

- Approval receipt ID:
  `d108approval_dbe0873a16902f36a5094e963360f77d414973e29dec5fca5bab7a17c1ff3af3`
- Provider receipt ID:
  `d107countreceipt_80447f354d982620b1c849a32abcd276c40428721c8948f6aef5671a11176946`
- Completion gate ID/body SHA:
  `d108_c663c745d43fc31bdee5309825059827899872c13368d7e3709e8730ee0a0f86` /
  `sha256:c663c745d43fc31bdee5309825059827899872c13368d7e3709e8730ee0a0f86`
- Completion gate file: 4,794 bytes,
  `sha256:5f57e29caa3a3c940c280a69fbed3abe3d8daba4b4542e039355443df931d7bc`
- Baseline/with-memory/delta: 2,193 / 2,895 / 702 input token
- Provider input-token count call 2, generation call 0, SDK retry 0, automatic retry 없음
- API key value가 portable artifact에 없고 `billing_or_free_tier_claim=null`
- D-108 checkpoint 기준 `index_freeze_authorization_candidate_ready=true`, `index_freeze_authorized=false`
- D-108 checkpoint 기준 `memory_index_frozen=false`, `retrieval_ready=false`, `core_campaign_unlocked=false`

Focused D-108 verification은 10/10 통과했다. 이 결과를 재현한다는 이유로
`scripts\run_d108_provider_token_counts.py`를 실행하면 안 된다. Freeze 여부 결정은 이후 D-109/D-110에서 별도
승인과 실행 evidence로 완료됐다. D-108 자체는 retrieval 또는 core를 승인하지 않았고, D-110 이후에도 그 두 권한은
계속 닫혀 있다.

## Historical D-107 portable index 검증과 token-count 실행 계획 재현

D-107은 network, provider client, API key와 ignored `.patchloop` runtime index 없이 checked-in evidence만 사용한다.
먼저 offline builder를 exact retry로 실행한다. Existing output bytes가 다르면 덮어쓰지 않고 실패한다.

```powershell
.venv\Scripts\python.exe scripts\build_d107_portable_index_freeze_readiness.py
```

이미 생성된 artifact와 source gate를 쓰지 않고 다시 계산해 검증하려면 다음 read-only validator를 실행한다.

```powershell
.venv\Scripts\python.exe -c "from patchloop.memory.d107_portable_index_freeze_readiness import validate_d107_source_gate; print(validate_d107_source_gate())"
```

Focused test는 다음과 같다.

```powershell
.venv\Scripts\python.exe -m pytest -q `
  tests\test_d107_portable_index_freeze_readiness.py
```

Expected 결과는 다음과 같다.

- Portable validation ID:
  `d107portable_8fb06997dfd9aa7e07c116db8095b5397382356bcd1cfd71ab3ce6c8b4ad1785`
- Token-count plan ID:
  `d107plan_7ace0e204f367fc857bfbc1ddaa1bbdc58dd9ff3c9272f9d9c7e2b7241160ee6`
- Source gate ID/body SHA:
  `d107_4bc473796fd4564bb4d4cc9bf975ea9e41addb4fda620135e6ae4d6a21e645d4` /
  `sha256:4bc473796fd4564bb4d4cc9bf975ea9e41addb4fda620135e6ae4d6a21e645d4`
- Source gate file: 4,175 bytes,
  `sha256:b3e24975062e379ec94c77187570b392026bacdcc855adedb00943467aaf09f2`
- Prepared request artifact: baseline/with-memory context, full request와 count request를 합해 6개
- Provider input-token count: `null` / `null`; observed delta: `null`
- Provider input-token count call 0, generation call 0, evaluator call 0
- `memory_index_frozen=false`, `retrieval_ready=false`, `core_campaign_unlocked=false`

향후 승인 대상은 고정된 baseline과 with-memory request를 사용하는 Responses input-token count call 정확히 두
번뿐이다. Generation과 automatic retry는 포함하지 않는다. 이 문서에는 그 API 실행 명령을 제공하지 않는다. Exact
D-107 gate에 대한 별도 승인을 받고 실행 receipt 계약을 다시 검증하기 전에는 count call, freeze, retrieval 또는 core를
실행하지 않는다.

## D-112 completed local scoring diagnostic validation

D-112 one-use execution은 이미 소비됐으므로 `--execute`를 다시 실행하지 않는다. 다음 명령은 저장된 full query
vector와 frozen entry vector로 9개 score row를 재계산하며 model을 load/encode하지 않는다.

```powershell
.\.venv\Scripts\python.exe scripts/run_d112_retrieval_readiness_probe.py `
  --validate `
  --verify-current-implementation
```

이 명령도 model을 재실행하지는 않지만 local pinned snapshot 약 91MB와 D-106~D-111 predecessor, exact installed
dependency를 다시 읽는다. 현재 `--skip-current-input-verification` flag도 이 read를 생략하지 못하므로 clean checkout
portable validation 용도로 사용하지 않는다. 그 flag의 help text는 executed implementation에 결속된 historical
limitation이며 별도 correction 전에는 신뢰하지 않는다.

Expected identity:

- Probe receipt: 13,835 bytes,
  `sha256:74fcd761cac65a9cab26529076b7cde60eaa14a1faf40475e680f526e00ba1d1`
- Completion gate: 77,591 bytes,
  `sha256:a7e691ae43c60405cbb10cd27caf3055eabaa96bb7fa6f2a02142d97aa903951`
- Input fingerprint:
  `sha256:d54454b2693e231c0ef50c94b20d75d58f00a885dfae98d3b6b190665f9d2e17`
- Score rows 9, diagnostic no-match 3/3
- Retrieval/provider/evaluator/agent call 0/0/0/0, runtime injection 0

`--preflight` 또는 두 번째 `--execute`가 `one-use execution is already consumed`로 거부되는 것은 의도된
post-state다. Receipt가 있지만 gate가 없으면 이전 실행이 incomplete/failed-consumed인 것이며 재실행하지 않는다.
현재 checkout에는 valid completion gate가 있으므로 `--validate`가 성공해야 한다.

## D-113 validator-correction candidate validation

D-113은 D-112 one-use 실행을 재현하지 않는다. 다음 명령은 exact D-112 receipt/gate/source와 작은 portable
index artifact만 읽어 preflight, candidate와 source gate를 동일 바이트로 다시 만들고 검증한다. Local embedding
snapshot, model load/encode, retrieval 또는 API call은 없다.

```powershell
uv run python scripts/build_d113_validator_correction_authorization_candidate.py
uv run pytest -q tests/test_d113_validator_correction_authorization.py
```

Expected candidate identity:

- Candidate ID:
  `d113validatorcandidate_373257ce1e2c904482a2aeb4649495baf737a11b3c958ef8420b66640a7f3732`
- Semantic body SHA:
  `sha256:373257ce1e2c904482a2aeb4649495baf737a11b3c958ef8420b66640a7f3732`
- 5,963-byte candidate file SHA:
  `sha256:4b576b6b7edbb7ebf9813e8c4ac35fae7af88992dc4dac3a28a181f79aa6e8a9`

Focused test expected result는 18/18이다. 이 명령은 D-114 correction을 구현하거나 승인하지 않는다. 위 세 값을
사용자가 별도 메시지에서 정확히 다시 제시하기 전에는 D-114 파일, retrieval, runtime injection과 core campaign을
만들거나 실행하지 않는다.

## D-121 completed preparation validation

다음 명령은 sealed preparation 네 artifact를 현재 implementation과 exact payload/hash/chronology로 다시 검증한다.
Docker runner를 새로 만들거나 container를 시작하지 않고, opaque source를 열지 않으며 execution output이 없는지도 확인한다.

```powershell
uv run python scripts/run_d121_hash_only_isolation_successor.py --validate-preparation
```

Expected status는 `D121_EXECUTION_CANDIDATE_READY_PENDING_EXACT_APPROVAL`이다. Artifact는 다음 네 개다.

- `d121-isolation-successor-preparation-approval-receipt.json`: ID/body/file SHA
  `d121preparationapproval_0f0627d6cdc6e63cd5d73eff66646406b7bbd1c64affb43fc35e0fa701b6fc79` /
  `sha256:0f0627d6cdc6e63cd5d73eff66646406b7bbd1c64affb43fc35e0fa701b6fc79` /
  `sha256:5a5592c2fff7deae63c50482d109c0d8e79ff4016fb96aaa8cb5a7b442d83606`, 14,662 bytes
- `d121-isolation-successor-readiness-preflight.json`: ID/body/file SHA
  `d121readiness_8d1bbf95e3bb8fbe9717a0f3620cdd9985091d0695aff69622d92d046ad6be12` /
  `sha256:8d1bbf95e3bb8fbe9717a0f3620cdd9985091d0695aff69622d92d046ad6be12` /
  `sha256:3423bf9af71d9b69579115d65a2b67d2bdb39363748e40a9cb78bdd461ad94e6`, 32,423 bytes
- `d121-isolation-successor-execution-authorization-candidate.json`: ID/body/file SHA
  `d121executioncandidate_b37bde7b9f49f92118ca277e521cd409b1e51b6f97c1ad8c2e9ff5090a1c38ef` /
  `sha256:b37bde7b9f49f92118ca277e521cd409b1e51b6f97c1ad8c2e9ff5090a1c38ef` /
  `sha256:0e8ea35d4fda06ecfba180150062b873ada5b11dd98df7bd0416c557777db1c5`, 11,046 bytes
- `d121-isolation-successor-authorization-source-gate.json`: ID/body/file SHA
  `d121_711b9c8e738128d3d03b42c3287bf57418e02348b12a2c10707e9ce5ba1fe592` /
  `sha256:711b9c8e738128d3d03b42c3287bf57418e02348b12a2c10707e9ce5ba1fe592` /
  `sha256:e9c05396e10770c4290b2e57235f32da6fe3997afcd3fdb109c3697cea773b50`, 15,514 bytes

Recorded readiness는 Docker 8 commands/create 1/start·run·exec·probe 0, opaque access/read 0, residual 0이다.
Actual successor run은 unauthorized/count 0이다. 다음 단계는 위 candidate triple을 별도로 승인한 정확히 한 번의 fresh
two-session hash-only run이며 D-119 retry/repair, retrieval/agent/core를 포함하지 않는다.

검사 결과는 D-121 47/47, D-119+D-121 82/82다. D-120 suite의 7 failures는 historical test가 D-121 future output path의
부재를 요구하기 때문에 preparation 완료 뒤 예상되는 실패다. D-120 test나 artifact를 수정하지 않으며 D-121 product
regression으로 해석하지 않는다.

## Historical: D-119 partial failure와 D-120 candidate offline validation

D-119는 approval receipt, preflight와 4-event journal을 남긴 채 소비된 실패로 끝났다. Completion gate가 없으므로
D-119 실행을 다시 호출하거나 journal을 삭제·수정해 복구하지 않는다. 다음 명령은 이미 생성된 D-120 preflight,
authorization candidate와 source gate를 exact D-119 partial bytes 및 현재 D-120 구현에서 다시 계산해 비교한다.

```powershell
uv run python scripts/build_d120_d119_cleanup_correction_authorization.py --validate
uv run pytest -q tests/test_d120_d119_cleanup_correction_authorization.py
```

Historical validator의 expected status는 `D119_PARTIAL_FAILURE_SEALED_D120_CANDIDATE_PENDING_APPROVAL`이다. 이 경로는 Docker와
network를 호출하지 않고 두 opaque benchmark source를 열거나 record를 parse하지 않는다. 첫 번째 후속 승인은 이미
D-121의 new-only 구현, offline test, no-start readiness와 실행-승인 후보 준비에 소비됐다. 실제 two-session D-121
run은 그 후보의 ID, semantic body SHA와 file SHA를 다시 제시하는 두 번째 승인이 있어야 한다. D-120 validation이나
두 승인 중 어느 것도 retrieval, agent run, core campaign을 열거나 trusted cutoff와 independence를 입증하지 않는다.
