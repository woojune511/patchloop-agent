# PatchLoop

> Trace-Driven Coding Agent Reliability Harness

PatchLoop는 Python coding agent의 model/tool call, patch, checkpoint와 hidden evaluator 결과를
재현 가능한 artifact로 보존하고, 실패 memory 표현이 held-out 성능과 비용에 미치는 영향을
비교하는 실험 harness다.

현재 저장소에는 evaluator-first MVP와 offline end-to-end 경로가 구현되어 있다. 2026-07-29 현재
세 smoke task를 mock과 content-hashed replay로 각각 실행한 6개 agent run이 고정된 Linux Docker
evaluator에서 모두 공식 통과했다. 쉬운 자체 task 다섯 개는 calibration fixture로만 남기고,
SWE-rebench 계열의 실제 Loguru, AnyIO, tox, Hugging Face Hub, PDM #2781과 pyfakefs #991
사례 여섯 개를 memory-development task로, Moto #7208과 Babel #1042를
development-validation task로, SQLGlot #7187, Param #1117, MTPLX #21, FuseSoC #776,
Dagster #33605와 Kubeflow Pipelines #13112를
core-cross-repo task로,
Loguru #1297, PDM #3759, AnyIO #1134, Hugging Face Hub #4056, tox #3846/#3851과
pyfakefs #1269를 core-same-repo task로 admission했다. Research role 20/20은 채웠지만
FuseSoC #776, AnyIO #1134와 pyfakefs #1269를 stress sentinel로 선정하고 30-run fault
schedule을 machine audit한 뒤 dataset manifest를 동결했다. 이 동결은 실행 전 계약
고정이며, stress run과 실제 OpenAI 96-run campaign은 아직 완료하지 않았다. 미실행 gate는
[Current limitations](docs/08-limitations.md)에 분리했다.

현재 live 경로에는 `experiment-v2` purpose, 비용 승인 preflight, durable execution plan,
hash-chained campaign journal과 legacy `trace-qualification-v1`/신규
`trace-qualification-v2`가 구현돼 있다. Babel #1042의
paid development-validation pilot 세 회를 2026-07-28 실행했다. r1과 r2는 각각 tool
grammar와 hunk line-count 상호운용성 문제로 evaluator 전에 실패했고, r3
`run_3cb86f8d70094a11`은 제출 patch와 official hidden/regression/scope/safety verdict,
당시 v1 trace qualification을 모두 통과했다. 이후 tool/context/lifecycle 계약이 v2로
바뀌었으므로 이 historical pilot은 새 campaign을 열지 않는다. 여섯 memory-development
task의 12-run no-memory campaign도 아직 실행하지 않았다.

2026-07-29의 별도 model-candidate pilot `run_d4fea5e7198b4abc`는
`gpt-5.4-mini-2026-03-17`로 exact prompt-token telemetry를 확인했지만, agent가
`VERIFY`에서 legacy `DONE`을 반환해 evaluator 전에 종료됐다. 이 immutable run은
16 model call, 25 tool call, 66,287 input + 6,164 output token과 `$0.07745325`를
기록했으며 성공이나 accepted pilot가 아니다. 원인 뒤에는 새 run용
`tool_schema_version=v2`/`phase-evidence-v2`를 구현했다. 현재-diff check,
완전한 final `get_diff` 제시와 구조화 `finish_task`를 제출 조건으로 묶고, 잘못된
제출은 두 번까지 model-visible rejection으로 돌려준다.

별도 승인된 r2 `run_4a9737ec91964dca`는 이 v2 경로를 실제 provider에서 실행했다.
10 model call, 13 tool call, 58,695 input + 7,543 output token과 계산상 `$0.07796475`를
사용했다. Final check → complete diff → review → `finish_task` → official evaluator →
receipt 순서와 `trace-qualification-v2`는 통과했지만 hidden acceptance가 실패해
`scope_compliant_success=false`인 task failure다. Prompt token은 10/10 정확히 일치했고
provider truncation도 없었다. 다만 첫 rejected patch 뒤 stateless context가 patch hash와
오류는 보존하면서 body는 복원하지 않은 continuity gap이 확인됐다. 따라서 이 run은
accepted pilot가 아니며 Terra 또는 development campaign gate를 열지 않는다. Aggregate
verdict와 hash-bound artifact는
[mini r2 evidence record](reports/live-pilot/dev-validation-gpt54mini-pilot-20260729-r2.json)에
보존했다.

## 구현된 핵심 경로

```text
public.yaml → stateless context builder → model adapter
            → constrained tool gateway → append-only events/checkpoints
            → submitted patch → separate hidden evaluator
            → deterministic SCRR verdict → experiment/report/viewer
```

- Pydantic v2 public/private task, run, event, checkpoint, tool, verifier, failure, memory 계약
- Local smoke와 Docker 공식 backend (`--network none`, resource limits, read-only root)
- Reference/no-op/regression/forbidden/dependency/tampering/public-API patch evaluator
- Mock/replay/OpenAI Responses adapters; OpenAI adapter는 `store=false`, current-turn context를 사용
- 새 live turn은 exact logical request와 context-policy omission evidence를 CAS에 저장하고,
  Responses input-token pre-count와 실제 usage를 대조하며 `truncation=disabled`를 강제
- Registered `search_files`, `read_file`, `apply_patch`, `run_check`, `get_diff`와
  orchestrator control `finish_task`만 허용
- SQLite WAL event/checkpoint/action store와 SHA-256 content-addressed artifact store
- `action_id + input_hash` idempotency, OS-held per-run ownership과 stale `RUNNING` reclaim,
  context reset 및 offline local mock의 fresh-process hard-kill recovery
- v2 patch의 raw input, pre/post file image와 expected diff를 CAS에 준비한 뒤 mutation하고,
  중간 종료 시 pre/post/partial/unknown 상태를 판별해 duplicate apply 없이 복구
- Dataset role이 `memory-development`인 reviewed failure 전용 structured/raw memory index
- Seeded experiment runner, task-level bootstrap CI, JSON/CSV/HTML report. 불완전하거나
  qualification-failed인 matrix는 diagnostic으로만 남기고 headline/paired 결과를 억제
- 목적을 명시하는 `experiment-v2`, durable approved execution plan에서만 발급되는
  execution-hash-bound live capability와 source-evidence-bound trace qualification
- 최초 `CampaignStarted`를 exclusive create하고 API call 전에 각 `RunStarted`를 fsync하는 append-only,
  hash-chained campaign journal
- Content-addressed frozen dataset manifest와 3-sentinel, 30-run stress schedule audit
- FastAPI/Jinja/HTMX trace viewer와 host-only `gh` Issue/Draft PR adapter
- Memory/core/headline에서 제외되는 content-addressed calibration fixture 5개
- SWE-rebench revision, upstream issue/PR/commit, upstream license evidence와 Docker digest를
  고정한 Loguru, AnyIO, tox, Hugging Face Hub, PDM #2781, pyfakefs #991, Moto #7208과
  Babel #1042, SQLGlot #7187, Param #1117, PDM #3759, AnyIO #1134와
  Hugging Face Hub #4056, MTPLX #21, FuseSoC #776, Dagster #33605와
  Kubeflow Pipelines #13112, tox #3846/#3851, Loguru #1297과 pyfakefs #1269
  research task
- Task별 base hidden failure, reference 3회와 최소 5종의 known-bad를 기록한 admission evidence
- 후속 upstream 회귀까지 판별해 원래 AnyIO benchmark fix를 거부하는 hardened reference/oracle
- 실제 CLI grammar와 project precedence를 어긴 PDM #3759 benchmark fix를 거부하고
  maintainer follow-up을 채택한 hardened reference/oracle
- 확장자 없는 entrypoint를 process worker에서 복원하는 AnyIO #1134 exact-production
  reference와 module identity·metadata·exactly-once를 판별하는 독립 oracle
- 공유 reactive source의 branch fan-out 재계산을 판별하는 Param #1117 exact-production
  reference와 sync·coroutine·generator cache lifetime을 검증하는 독립 oracle
- file/snapshot download의 caller-owned progress 정책과 Hub-owned subclass 정책을 분리하는
  Hugging Face Hub #4056 exact-production reference와 adversarial combined-partial oracle
- mixed content 뒤의 streamed tool call을 chunk 경계와 marker case에 무관하게 복원하고,
  lookalike tag와 non-whitespace residue를 거부하는 MTPLX #21 hardened reference/oracle
- 여러 core-file parse failure를 discovery 중 보존하고 manager·public wrapper·missing-core
  diagnostic까지 전달하는 FuseSoC #776 exact-production reference와 독립 oracle
- compound dotted Python factor 인식과 `ignore_base_python_conflict`의 default/validation
  경계를 함께 보존하는 tox #3846 + accepted follow-up #3851 hardened reference와 독립 oracle
- 선택되지 않은 sibling entity의 partition definition이 선택 결과에 섞이지 않게 하는
  Dagster #33605 exact two-file reference와 private-v2 hash-bound read-only oracle. 공식
  reference 3/3, visible 28개, hidden 9개가 통과했고 semantic partial 8종과
  forbidden scope/test-tampering patch를 거부했다.
- `.after()`의 public dependency API와 compiler name resolver를 함께 확장해 일반 task와
  `ExitHandler` group dependency를 구분하는 Kubeflow Pipelines #13112 exact two-file
  reference와 private-v2 hash-bound read-only oracle. 공식 reference 3/3, base-resident
  visible 277개와 15개 subtest, independent hidden 11개가 통과했고 no-op, semantic partial
  8종과 forbidden scope/test-tampering patch를 거부했다.
- file wrapper의 `readable()`/`writable()` capability query를 실제 read/write guard와
  분리하는 pyfakefs #1269 exact-production reference와 private-v2 29-case oracle. 공식
  reference 3/3과 독립 dynamic-interface equivalent 1/1이 통과했고 no-op, semantic
  partial 9종과 forbidden scope/test-tampering patch를 거부했다.

새 run에서 agent 제출은 `DONE` 문자열이 아니라 current-diff evidence gate를 통과한
`finish_task`다. `SubmissionAccepted`도 정답 판정이 아니라 evaluator에 넘길 수 있다는
뜻이며, 성공은 다음 evaluator 결과의 논리곱이다.

```text
hidden acceptance
AND regression
AND scope policy
AND safety policy
```

## 5분 offline quickstart

Python 3.12와 `uv`가 설치된 PowerShell에서 실행한다.

```powershell
uv sync --extra dev
uv run patchloop task validate tasks/smoke/csv-quoted-newline
uv run patchloop eval-task tasks/smoke/csv-quoted-newline `
  --patch tasks/smoke/csv-quoted-newline/reference.patch --backend local
uv run patchloop run --task tasks/smoke/csv-quoted-newline/public.yaml `
  --model mock --memory no_memory
uv run patchloop run --task tasks/smoke/csv-quoted-newline/public.yaml `
  --model replay:replays/smoke/csv-quoted-newline.jsonl --memory no_memory
uv run pytest -q
```

`replays/smoke/*.jsonl`은 public task 정보만으로 만든 deterministic offline fixture다. Replay run은
repository-relative source 경로와 content hash를 immutable manifest에 기록하며, live model 결과나
memory experiment evidence로 간주하지 않는다.

Offline experiment와 report도 API key 없이 재현된다.

```powershell
uv run patchloop evaluate --suite experiments/smoke.yaml
uv run patchloop report --experiment offline-smoke --output reports/offline-smoke
uv run patchloop serve
```

Viewer는 `http://127.0.0.1:8000`에서 run manifest, outcome·usage·prompt-integrity 요약,
critical path, 접이식 model turn/raw trace, patch와 verifier 결과를 보여준다. 원시 event
payload는 삭제하지 않고 기본 화면에서만 접어 둔다.

## CLI

```text
patchloop doctor
patchloop task validate <task-dir>
patchloop dataset audit
patchloop eval-task <task-dir> --patch <patch> [--backend local|docker]
patchloop run --task <public.yaml> --model <mock|openai|replay:path> --memory <condition>
patchloop resume --run-id <run-id>
patchloop memory build --split dev-train
patchloop memory freeze --index <index-id>
patchloop evaluate --suite <experiment.yaml> [--preflight-only]
  [--approve-live-cost --approved-execution-hash <sha256:...>]
patchloop inject-fault --run <baseline-run-id> --fault <type>
patchloop memory review --failure-id <id> --approve|--reject
patchloop report --experiment <id> --output <directory>
patchloop github import-issue <url> --output <public.yaml>
patchloop github draft-pr --run-id <id> --repo <checkout>
patchloop serve
```

## Live/OpenAI와 공식 campaign gate

Responses API adapter는 host process에서만 API key를 읽고 container, checkpoint, event payload에
전달하지 않는다. 현재 live sequence는 다음 두 config로 고정한다.

| Purpose | Task/condition/repetition | 상한 |
| --- | --- | ---: |
| `development-validation-live-pilot` | Babel #1042, `no_memory`, 1회 | $2 |
| `development-validation-model-candidate-pilot` | Babel #1042, mini dated snapshot, `no_memory`, 1회 | $2 |
| `memory-development-no-memory` | frozen memory-development 6개, `no_memory`, 각 2회(12 run) | $20 |

첫 pilot evidence는 `run_c6f13dd9a1a1472d`다. 실제 비용은 `$0.34025875`, model/tool call은
20/22, input/cache-write/output token은 73,730/73,670/7,326이었다. Agent는 Git unified
diff 대신 `*** Begin Patch` envelope를 반복해 모든 mutation이 거부됐고 80,000-token
budget을 넘긴 마지막 응답 뒤 terminal agent failure가 기록됐다. Submitted patch와
evaluator verdict는 없으며 이 run은 성능 성공이나 qualified pilot가 아니다. 당시
leakage scan의 41 match는 공개 task contract에 이미 있던 marker의 오진이었고 API key
match는 0이었다. 원본 qualification은 immutable하게 실패 상태로 보존한다. 첫 model
candidate의 코드 내용은 바꾸지 않고 envelope만 Git diff로 변환한 사후 진단 patch
`sha256:4c49b6edd0603f2e56c04c18e83fdecb3a6a5868ab40bffca198504951b01606`는 별도
Docker evaluator에서 모든 verdict를 통과했다. 이는 tool-contract 원인 evidence이지
원래 agent run의 성공으로 집계하지 않는다.

r2 evidence는 `run_de8f2a2846044c01`이다. 비용은 `$0.328036875`, model/tool call은
19/22, input/cache-write/output token은 74,868/74,811/6,274였다. 수정된 gateway
feedback과 leakage scan은 동작했고 `trace-qualification-v1` artifact는 `qualified=true`를
기록했다. 그러나 아홉 model output의 patch candidate(고유 7개)가 모두 hunk header에
old/new 7줄을 선언하면서 실제 body는 6줄만 포함했다. 실행된 여덟 `apply_patch`가 strict
`git apply`에서 모두 거부돼 evaluator에는 도달하지 못했다. Pilot acceptance는
`evaluation_reached=false` 때문에 실패하며, 이 run은 trace-qualified이지만 agent
success나 accepted pilot가 아니다. r1+r2 누적 비용은 `$0.668295625`다.

Agent-visible gateway는 이 evidence를 근거로 raw patch의 hunk 줄 수만 `--recount`로
재계산한다. Body 문법, context, path와 모든 deterministic policy는 그대로 검사한다.
Legacy v1 policy rollback은 같은 raw patch를 reverse recount하고, v2는 durable intent의
검증된 preimage를 복원한다. Rollback 실패나 pre-call 상태 불복원은 `RecoveryError`로
fail-closed하며, agent workspace의 untracked file은 checkpoint와 recovery를 포함해
허용하지 않는다. Hidden evaluator의 patch 적용은 계속 strict하다. 새 파일, rename/copy,
binary와 metadata-only patch도 계속 거부한다.

새 v2 run은 raw patch를 `ToolCalled` CAS에 보존하고, target별 pre/post image와
baseline/expected diff를 `PatchPrepared` intent CAS에 기록한 뒤에만 실제 mutation을 시작한다.
모든 target을 먼저 검증하고 postimage를 atomic replace/delete한다. Single-file smoke
patch의 유일한 postimage replacement 뒤 outcome 기록 전에 worker를 종료하는 local
subprocess E2E에서 새 process가 같은 run lock을 획득해 재적용하지 않고 완료한다.
Multi-file partial state의 preimage 복원은 별도 unit test로 검증한다. CAS 변조, untracked
file 또는 제3의 파일 상태는 `RecoveryError`로 fail-closed한다.

Evaluator도 manifest/result/provenance와 verifier stdout artifact를 원자적으로 기록한 뒤
hash-bound evaluation receipt를 만든다. Receipt bundle과 참조된 verifier CAS, 그리고 새
v2의 accepted submitted-patch CAS가 검증될 때만 resume이 evaluator를 재실행하지 않으며,
terminal result/status/event는 한 SQLite transaction으로 확정한다.

r3 evidence는 `run_3cb86f8d70094a11`이다. 별도 승인된 execution hash
`sha256:03c57fb3dd0182e63645e346311ee2a46c1284d9770857240b2011b666b8bde6`로
정확히 한 번 실행했고 `$0.16056875`를 사용했다. 11 model call과 13 tool call 뒤
`babel/numbers.py` 한 줄을 수정한 patch를 제출했다. Official evaluator는 hidden,
regression, scope와 safety를 모두 통과시켜 `scope_compliant_success=true`를 기록했다.
72개 monotonic event와 15개 checkpoint의 qualification도 integrity, leakage,
usage reconciliation과 `evaluation_reached=true`를 모두 통과했다. 세 pilot의 누적 비용은
`$0.828864375`다. 이 결과는 historical v1 accepted-pilot evidence이며, 현재 v2
development campaign의 선행 gate나 memory 효과 증거는 아니다.

Mini r2 model-candidate diagnostic은 execution hash
`sha256:fc2649790241f9623ea259a05957a38d1063472a9f17998e9e489b5b3fad21ca`로
정확히 한 번 실행돼 terminal evidence로 고정됐다. 실행/telemetry/lifecycle은 완주했지만
task acceptance는 실패했고, post-run audit에서 새 D-037 retry-context target이 충족되지
않았음이 확인됐다. 다음 gate는
새 paid call이 아니라 rejected mutating-tool argument를 hash-bound·크기 제한된 형태로
다음 turn에 복원하고 이를 qualification에서 검사하는 offline 구현과 test다. 그 뒤 새
experiment ID, clean execution hash와 별도 승인으로 rejected mutation retry를 실제로
exercise하는 mini diagnostic을 다시 실행한다. 새 Terra development-validation pilot이
evaluator에 도달하고 `trace-qualification-v2`를 통과해 `pilot_run_id`에 고정된 뒤에만
아래 12-run development campaign preflight를 실행한다. Pilot의 task outcome은 이
harness gate와 별도로 보고한다.

```powershell
uv run patchloop evaluate `
  --suite experiments/dev-no-memory.template.yaml `
  --preflight-only
```

출력의 `execution_hash`와 blocker를 검토한다. Preflight는 frozen dataset/role/hash,
manifest가 지정한 canonical task package path와 public/private spec hash, base commit,
digest-pinned evaluator environment와 observed Docker image identity, clean Git commit,
OpenAI SDK, `OPENAI_API_KEY`의 존재 여부만, custom base URL 부재,
`gpt-5.6-terra` + medium reasoning + standard mode + default service tier, 72시간 이내 공식
가격과 12개 run의 전체 budget reserve를 확인한다. Credential 값은 출력하거나 hash에 넣지
않는다. 환경 blocker와 비용을 확인한 뒤 사용자가 별도로 최대 $20를 승인한 경우에만 같은
hash를 invocation-only 승인으로 전달한다.

```powershell
uv run patchloop evaluate `
  --suite experiments/dev-no-memory.template.yaml `
  --preflight-only `
  --approve-live-cost `
  --approved-execution-hash <sha256:...>

# 위 preflight가 ready=true일 때만 별도로 실행한다.
uv run patchloop evaluate `
  --suite experiments/dev-no-memory.template.yaml `
  --approve-live-cost `
  --approved-execution-hash <same-sha256:...>
```

Checked-in `live_cost_approved`와 `approved_execution_hash` 값은 승인 권한이 아니며 compatibility
필드일 뿐이다. 승인 두 flag는 해당 invocation과 exact execution hash에만 유효하다. Direct
`patchloop run --model openai`, live `resume`, live `inject-fault`는 이 gate를 우회하지 못하게
차단된다.

`ready=true`인 paid invocation은 승인 내용과 preflight evidence를
`experiment-execution-plan-v1`으로 먼저 durable하게 저장한다. `CampaignStarted`로 journal을
원자적으로 exclusive create하고 flush와 fsync한 뒤 그 plan에서 live capability를 발급한다. 각 row의
stable run ID를 가진 `RunStarted`도 fsync한 다음 model call을 허용한다. Process가
hard-crash해도 journal이
남아 같은 experiment를 새 schedule로 자동 재실행하지 못하지만, **중단된 journal의 자동
resume은 아직 구현되지 않았다.**

실행기는 suite 파일을 승인 뒤 다시 읽지 않고 plan의 normalized suite snapshot을 사용한다.
각 task package와 생성 manifest의 task/model/budget/environment identity도 plan과 대조한
뒤에만 `RunStarted`와 model call로 넘어간다.

2026-07-28에 확인한 공식 Terra API rate는 1M token당 input $2.50, cached input $0.25,
cache write $3.125, output $15다. 가격 source는
[OpenAI API pricing](https://developers.openai.com/api/docs/pricing)이며 preflight 시점 기준
72시간을 넘으면 다시 확인해야 한다. 현재 model page에는 dated snapshot 없이
`gpt-5.6-terra` alias만 제공되므로 SDK version, Git commit과 72시간 execution window를
provenance로 남긴다.

새 v2 Terra pilot이 model, budget, harness commit, runtime-contract hash와
`trace-qualification-v2`를 모두 통과한 뒤에만 그 run ID를 no-memory development
suite에 넣고 새 execution hash를 preflight한다. 실패한 live attempt도 삭제하지 않고 run ID,
input/cached/cache-write/output usage, 계산 비용, terminal outcome과 qualification을 보존한다.
Qualification의 `source_evidence_hash`는 approved plan, manifest, events, checkpoints,
persisted result와 agent-visible content-addressed artifact inventory를 결속한다. v2는
`SubmissionAccepted` 안의 nested submitted-patch CAS bytes도 직접 다시 hash한다. 필수
`RunStarted`/`ContextBuilt`/`ModelCalled` artifact reference, cache usage 불변식과 malformed
function-call response의 이미 과금된 usage도 검사·보존하며, development campaign
preflight와 memory review/index admission은 현재 source evidence hash를 다시 계산한다.
새 D-031 live trace는 여기에 exact request artifact, context builder가 최근-event/tool-result
cap으로 생략한 양, input-token count endpoint의 예상치와 생성 응답의 실제
`usage.input_tokens`, reasoning-output breakdown, response status·truncation·incomplete reason을
turn별로 추가한다. 요청은 `truncation=disabled`이므로 provider의 silent input truncation은
허용하지 않는다. r1~r3는 이 필드가 도입되기 전 immutable legacy evidence로 유지한다.
이 경로의 terminal r1 provider suite는
`experiments/dev-validation-gpt54mini-pilot.yaml`이고, v2 corrective retry는
`experiments/dev-validation-gpt54mini-pilot-r2.yaml`이며
`gpt-5.4-mini-2026-03-17` + medium, run total 90,000 token, per-call output 4,096,
$2 cap으로 고정한다. 별도 `development-validation-model-candidate-pilot` purpose이므로
기존 Terra memory/core 계약의 선행 gate나 결과로 집계하지 않는다. 매 turn의 exact input
count와 4,096-token response allowance가 남은 90,000 안에 함께 들어가지 않으면 generation
call을 시작하지 않는다.
세 Terra pilot과 mini r1/r2는 usage/source-evidence 보존 경로를 실제 provider에서
확인했다. Terra r2 trace artifact는 qualified지만
evaluator 미도달 때문에 pilot acceptance를 통과하지 못했고, r3가 별도 clean execution
hash에서 v1 accepted pilot를 만들었다. Mini r2는 v2 evaluator 경로에 도달했지만 hidden
acceptance는 실패했고 post-run audit에서 D-037 target이 충족되지 않았음이 확인됐다.
다음 immediate gate는 이를 고치는 offline implementation/test이며, 별도 v2 Terra
pilot이 통과하기 전에는 12-run development campaign을 승인하지 않는다.

OpenAI integration은 공식 [Responses API migration guide](https://developers.openai.com/api/docs/guides/migrate-to-responses),
[function calling guide](https://developers.openai.com/api/docs/guides/function-calling),
[GPT-5.6 Terra model page](https://developers.openai.com/api/docs/models/gpt-5.6-terra)와
[GPT-5.4 mini model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini)의 계약을 따른다.

## 문서

1. [Agent instructions](AGENTS.md)
2. [Project spec](docs/01-project-spec.md)
3. [Architecture](docs/02-architecture.md)
4. [Contracts](docs/03-contracts.md)
5. [Evaluation protocol](docs/04-evaluation-protocol.md)
6. [Implementation plan](docs/05-implementation-plan.md)
7. [Decisions](docs/06-decisions.md)
8. [Reproduction guide](docs/07-reproduction.md)
9. [Current limitations](docs/08-limitations.md)
10. [Dataset card](data/DATASET_CARD.md)
11. [Latest implementation evidence](docs/09-evidence.md)

## 한 문장 설명

PatchLoop는 coding agent의 trace를 실패 memory와 deterministic regression evidence로 변환하여,
harness 변경이 성공률·비용·안전성·복구 능력에 미치는 영향을 고정 조건에서 측정한다.
