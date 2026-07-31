# PatchLoop

> Trace-Driven Coding Agent Reliability Harness

PatchLoop는 Python coding agent의 model/tool call, patch, checkpoint와 hidden evaluator 결과를
재현 가능한 artifact로 보존하고, 실패 memory 표현이 held-out 성능과 비용에 미치는 영향을
비교하는 실험 harness다.

현재 저장소에는 evaluator-first MVP와 offline end-to-end 경로가 구현되어 있다. 2026-07-30 현재
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
바뀌었으므로 이 historical pilot은 새 campaign을 열지 않는다. 이후 current mini
primary r2와 12-run no-memory campaign의 실행·판정은 아래 D-048 상태와 portable
evidence record에서 별도로 추적한다.

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
accepted pilot가 아니며 현재 primary development campaign gate를 열지 않는다. Aggregate
verdict와 hash-bound artifact는
[mini r2 evidence record](reports/live-pilot/dev-validation-gpt54mini-pilot-20260729-r2.json)에
보존했다.

이후 D-037 offline gate에서 새 non-replay manifest의 context policy를
`phase-evidence-v3`로 올렸다. 최신 model turn에서 거부된 `apply_patch`는 candidate/result
CAS와 canonical input hash를 다시 검증한 뒤 exact patch bytes·content hash·structured
reason을 바로 다음 request 한 번에만 복원한다. Full request와 output allowance가 남은
token budget을 넘으면 input count까지만 수행하고 `ModelGenerationBlocked`와 구조화
terminal error를 남긴 채 generation을 호출하지 않는다. Qualification은 candidate/result
CAS와 실제 request body, 첫 consumer와 stale-block 부재를 다시 대조한다. 이 경로는 전체
offline suite에서 통과했다. Terminal mini D-037 r3 suite에는 retry episode를 실제 관찰해야
하는 별도 hash-bound diagnostic consumer도 구현했다. 승인된 mini D-037 r3
`run_e90f7c52aa134182`는 실제
provider에서 실행됐지만 mutation 전에 여덟 번째 응답이 per-call 4,096-token ceiling에
도달해 incomplete로 끝났다. 8회 input pre-count는 모두 provider usage와 일치했고 input
prompt cut은 관찰되지 않았지만 evaluator와 rejected retry episode에는 도달하지 못했다.
따라서 이 terminal run은 D-037을 검증하거나 반증하지 않으며 primary development gate를
열지 않는다.

별도 승인 hash
`sha256:bbb6dbdcab1c7561c868ae4cc40478d6e3401c5900feb59b8ea09ef38d9156a1`의 r4
`run_826c1c7fb3d242c2`는 25,000 per-call / 120,000 total 계약을 실제 provider에서
정확히 한 번 실행했다. 13개 generation은 모두 completed였고 exact input count도 13/13
일치해 r3의 output-ceiling confounder는 제거됐다. Agent는 patch 1회, visible check pass,
final diff와 `REVIEW` 진입까지 진행했지만, 14번째 request의 exact input 8,583과 full
response allowance 25,000이 남은 28,563-token run budget에 들어가지 않아 local guard가
provider generation 전에 차단했다. 제출·evaluator·rejected retry episode는 모두 0이므로
r4 역시 D-037을 검증하거나 반증하지 않고 gate를 열지 않는다.

D-041은 다음 diagnostic을 새 r5/profile v3로 분리한다. Per-call allowance 25,000과
`exact input + full allowance`가 남은 budget 안에 들어가야 한다는 strict runtime 의미는
바꾸지 않고, diagnostic-only total token budget만 200,000으로 고정한다. 이 값은 r4가
사용한 91,437-token prefix에 당시 가장 큰 exact input 10,031과 25,000 allowance로 된
tail reservation 세 개를 더한 196,530을 올림한 것이다. 새로 생성되는
`exact_request_budget_exceeded` terminal event만 `model-generation-block-v1` payload를
사용한다. 이 versioned generic block은 retry
candidate가 없어도 trace integrity evidence로 인정할 수 있지만 D-037 retry episode나 gate
통과로 세지 않는다. Historical unversioned r4는 21/22 qualification 그대로다. Synthetic
rejection이나 automatic retry는 추가하지 않으므로 r5가 evaluator에 도달하고도 rejection이
없으면 diagnostic은 inconclusive이며 자동 재실행하지 않는다. 이 offline 계약은 targeted
191 test, full 504 passed/2 skipped와 Ruff를 통과했다.

별도 승인 hash
`sha256:97249f05deda8e59118fdac0dd6f62f44c18b086ecb16bface2cc4d0f41a3a12`의 r5
`run_0ad8676d42614fbf`는 2026-07-30 provider에서 정확히 한 번 실행됐다. 18개 generation은
모두 completed였고 input pre-count와 provider usage가 18/18 일치했다. Agent는
`babel/numbers.py` 한 줄을 바꿔 official hidden/regression/scope/safety verdict와
`trace-qualification-v2` 23/23을 통과했다. 사용량은 121,366 input + 9,913 output token,
계산상 `$0.135633`이다. 그러나 rejected candidate와 retry episode가 모두 0이므로 D-037
diagnostic은 `retry_episode_not_observed`로 terminal inconclusive다. 이 run은 task 성공
evidence이지만 D-037을 검증하거나 반증하지 않고 primary development gate를 열지 않으며,
계약대로 자동 재실행하지 않는다. Aggregate evidence는
[mini D-037 r5 evidence record](reports/live-pilot/dev-validation-gpt54mini-d037-20260730-r5.json)에
보존했다.

D-043은 rejection이 우연히 발생할 때까지 paid run을 반복하는 대신
`experiments/dev-validation-gpt54mini-d037-r6.yaml`의 별도
`d037-rejected-patch-retry-v4` profile을 도입한다. 이 profile만 immutable
`FaultSpec(type=controlled-reject-first-prepared-patch, trigger_after=1)`을 사용한다.
첫 `apply_patch`가 raw-diff, tracked-target, current-context applicability와 non-empty
preflight를 통과해 `PatchPrepared`가 된 직후, 실제 worktree write 전에
`CONTROLLED_DIAGNOSTIC_REJECTION`으로 정확히 한 번 닫는다. 다음 request는 기존 D-037
contract로 candidate bytes·hash·structured reason을 exact rehydrate한다. Qualifier는
controlled rejection 1회, 그 action의 `PatchApplied` 0회, 전체 retry 검증과 evaluator
도달을 함께 요구한다. Invalid patch는 injection을 소모하지 않고, crash 뒤 resume도
prepared patch를 적용하지 않는다. 이 경로는 현재 offline evidence만 있으며 r6 provider
call 전에는 live claim을 만들지 않았다. 이후 승인된 r6 `run_73f5aaf7328a4ea5`가 controlled
rejection 1회, verified retry 1회, rejected action `PatchApplied` 0회와 evaluator 도달을
모두 충족했다. Official hidden/regression/scope/safety와 trace qualification 23/23도
통과했으며, 138,262 input + 13,800 output token과 계산상 `$0.1657965`를 기록했다. 이
결과는 D-037 harness branch의 live validation이지 자연 model-error recovery rate나 memory
효과가 아니다. Aggregate evidence는
[mini D-037 r6 evidence record](reports/live-pilot/dev-validation-gpt54mini-d037-20260730-r6.json)에
보존하며 같은 hash/run을 재실행하지 않는다.

D-045는 사용자의 당시 비용·snapshot 고정 선택을 반영해 이후 primary pilot,
memory-development와 core 비교 모델을 `gpt-5.4-mini-2026-03-17`로 통일했다. Reasoning은
medium, mode는 standard, service tier는 default이며, r5/r6에서 output/tail-budget
confounder 없이 완주한 25,000 per-call output과 200,000 run-total budget을 모든 조건에
같게 적용했다. 이 200,000-token 계약은 consumed suite의 historical evidence로 유지되고,
future suite에 대해서만 D-052가 supersede한다. Historical Terra와 mini r1-r6의 당시
purpose와 판정은 바꾸지 않는다. 다음
paid gate였던 fault-free primary r1은 승인 hash
`sha256:969477ca029570ea61f9fca74fd3aa558f6e16ff9b5be1c7ffa8927ed1139047`로 정확히 한 번
실행됐다. `run_6993722014bf4e3b`는 20/20 input-token pre-count 일치와 completed response,
patch 적용, visible regression pass, final diff와 `REVIEW` 진입을 남겼지만 model-call
20회를 모두 사용해 `finish_task` 전 local budget guard에서 끝났다. 사용량은 131,266 input +
12,038 output token, 계산상 `$0.1526205`다. Evaluator는 실행되지 않았고 qualification은
call-budget terminal block 계약 때문에 21/22다. Exact final diff는 별도 no-model Docker
postmortem에서 hidden/regression/scope/safety를 모두 통과했지만 이를 live run의 제출이나
official success로 소급하지 않는다. 이 suite/hash/run은 재실행하지 않는다.
Portable claims boundary와 artifact hash는
[primary mini r1 evidence record](reports/live-pilot/dev-validation-gpt54mini-campaign-20260730-r1.json)에
보존한다.

D-047은 이 failure에서 드러난 경계를 offline에서 닫는다. Exact-token reservation 차단은
기존 `model-generation-block-v1`을 유지하고, model/tool/wall counter exhaustion은
`model-generation-block-v2`로 분리한다. 새 qualifier는 durable event에서 counter를 다시
계산하고 `model → tool → wall` reason 우선순위, strict payload/type, exact request CAS와
terminal error 결속을 검증한다. Valid v2 block은 재현 가능한 `agent_failure`이지 task
success나 evaluator 도달이 아니다. D-047 이후 D-052 전까지의 primary,
memory-development와 core suite는 모든 memory 조건에 같은 총
`21 model call / 50 tool call / 200,000 token / 900초` 상한을 사용했다. 21번째 call은
`finish_task` 전용 reserve가 아니며 정상 model call이다. Historical
primary r1과 diagnostic suite의 20-call 의미와 qualification은 바꾸지 않는다. Corrective
primary r2 `run_afd5080a77a34995`는 official evaluator와 qualification 23/23을 통과했다.
이어 실행한 `dev-no-memory-20260728` 12-run은 12/12 qualified agent failure,
evaluator 도달 0/12였다. Search 405, read 157, apply 1에 머문 이 결과는 no-memory
성능 baseline이 아니라 within-run investigation continuity failure evidence다.

D-048은 새 non-replay runtime을 `phase-evidence-v4`로 올린다. V4는 마지막
`PatchApplied` 뒤의 successful read/search CAS를 bounded `investigation-ledger-v1`로
매 turn 다시 만들고, exact search와 fully-covered read를 filesystem 재실행 없이 exact
result semantic replay로 제공한다. 두 번째 연속 no-progress부터 strategy change를
요구하며, nominal corrective tail에서는 read/search만 admission 전에 차단한다. 이
within-run repository evidence는 네 cross-run memory 조건 모두에 동일하고, hypothesis나
solution memory를 추가하지 않는다. V1-v3 trace는 소급 재해석하지 않는다.

D-052는 future non-replay runtime을 `phase-evidence-v5`로 올리고 budget을 모든 memory
조건에서 `21 model call / 50 tool call / 250,000 total token / 900초`, per-call output
25,000으로 고정한다. Durable `ModelCalled` telemetry의 `requested_input_tokens`를 우선하고
그 값이 `None`일 때만 actual `input_tokens`로 fallback하며, invalid 값은 fail closed한다.
관찰된 input 최댓값에 positive consecutive growth 최댓값을 더해 next input을 예측하고,
generation 전에는 5 turn, generation 후에는 4 turn을 예약한다.
`reserved_tokens = max_output_tokens + projected_next_input × projected_turns`이며
`remaining_tokens <= reserved_tokens`일 때 read/search만 `token_tail_reserved`로
`ToolCalled`와 dispatch 전에 차단한다. Apply/check/diff/finish는 계속 허용한다. 이 cutoff는
nominal corrective-tail 전환점이지 완료 보장이 아니며, strict exact-request + full 25,000
response admission guard는 그대로다. V5 offline contract는 검증됐지만 provider call은
없었다.

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
- `phase-evidence-v3`는 rejected patch 원문과 structured error를 CAS에서 다음 request로
  exact rehydrate하고, 요청+응답 allowance가 budget을 넘으면 provider generation 전에 차단
- `phase-evidence-v4`는 successful read/search CAS에서 durable investigation ledger를
  재구성하고, exact search와 fully-covered read를 semantic replay하며 corrective tail에
  들어가면 semantic replay 대상까지 포함한 모든 valid read/search를 admission 전에 차단
- `phase-evidence-v5`는 durable token projection으로 nominal corrective tail을 더 일찍
  감지하고 read/search만 `tool-admission-blocked-v2` evidence와 함께 차단한다.
  `investigation-policy-v2`, `investigation-ledger-v2`, `investigation-tail-policy-v2`,
  `context-build-evidence-v5`, `trace-source-evidence-v5`를 사용하며 qualification contract는
  계속 `trace-qualification-v2`다.
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
patchloop memory validate-review <proposal.json>
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
전달하지 않는다. 현재 live sequence는 primary config와 historical diagnostic lane으로
분리한다.

| Purpose | Task/condition/repetition | 상한 |
| --- | --- | ---: |
| `development-validation-live-pilot` | Current: Babel #1042 + Moto #7208, mini dated snapshot, `no_memory`, 각 1회 | $6 |
| `development-validation-model-candidate-pilot` | Historical mini diagnostics only; 재실행 금지 | $2 |
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

Historical Terra r3 evidence는 `run_3cb86f8d70094a11`이다. 별도 승인된 execution hash
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
않았음이 확인됐다. D-037의 hash-bound next-turn rehydration과 qualification은 이후
offline 구현/test를 통과했다. 새
`experiments/dev-validation-gpt54mini-d037-r3.yaml`은 execution hash에
`experiment-diagnostic-v1` 요구를 결속하고, evaluator 도달·retry episode 1개 이상·모든
episode 검증·failed source sequence 0을 별도로 검사한다. Evaluator에 도달했지만 episode가
없으면 task/qualification failure가 아니라 diagnostic inconclusive이고, evaluator 미도달은
diagnostic failure다. 승인 hash
`sha256:c33a50abe48b554c37d95de4833d1d17ede816f4d128b9adc22e88c010e138e6`
는 r3 `run_e90f7c52aa134182`에서 정확히 한 번 사용됐다. Run은 8 model call과 12개
search/read tool call, input 54,851 + output 6,079 token, 계산상 `$0.06849375`를 사용했다.
Event 55의 요청/실제 input 6,943은 일치했지만 output 4,096 중 reasoning이 3,989를 사용한
상태에서 `incomplete/max_output_tokens`가 발생했다. Patch·rejection·submission·evaluator는
모두 0이고 qualification 21/22 중 `prompt_token_integrity`만 실패했으므로 diagnostic은
`failed/qualification_not_passed`다. 이는 90,000-token 전체 budget 고갈이나 prompt
truncation이 아니다. 이 suite/run은 재실행하지 않으며 aggregate와 artifact identity는
[mini D-037 r3 evidence record](reports/live-pilot/dev-validation-gpt54mini-d037-20260729-r3.json)에
보존한다.

Corrective contract는
`experiments/dev-validation-gpt54mini-d037-r4.yaml`로 분리했다. 공식
[reasoning guide](https://developers.openai.com/api/docs/guides/reasoning#allocating-space-for-reasoning)의
초기 권고에 맞춰 per-call 25,000 token과 total 120,000 token을 profile v2에 함께 고정하고,
historical mini r1~r3와 당시 Terra/core 계약은 바꾸지 않는다. 자동 incomplete-response retry도
추가하지 않았다. Full offline 검증 뒤 승인된 execution hash로 r4를 정확히 한 번 실행했으며,
13개 응답은 모두 completed였지만 `REVIEW`의 다음 호출이 total-budget reservation에 의해
provider 전에 차단됐다. Qualification 21/22의 유일한 실패는 실제 token mismatch가 아니라
retry candidate가 없는 generic terminal budget block을 현재 v3 qualifier가 valid로 인정하지
않는 계약 경계다. Aggregate와 artifact identity는
[mini D-037 r4 evidence record](reports/live-pilot/dev-validation-gpt54mini-d037-20260729-r4.json)에
보존한다. 이 suite/run은 terminal inspection 전용이며 재실행하지 않는다. 후속 paid
diagnostic은 D-041의 새 r5/profile v3에서만 허용됐다. R5는 strict 25,000-token response
reservation과 200,000 total budget, 새 `model-generation-block-v1` generic terminal
block을 고정한 뒤 별도 hash로 정확히 한 번 실행됐다. `run_0ad8676d42614fbf`는 official
task와 trace qualification은 통과했지만 rejected candidate가 없어 diagnostic은
inconclusive다. R4와 r5의 승인이나 hash는 재사용하지 않는다. D-043의 별도 r6/profile v4는
controlled rejection을 도입한 뒤 새 hash로 한 번 실행됐고, exact retry와 evaluator gate를
통과했다. R6도 immutable하며 재실행하지 않는다. Historical primary r1, consumed
primary r2와 첫 12-run campaign은 terminal inspection 전용이다. 별도 승인된 v4
fault-free development-validation pilot `run_d7207fbb06184dd3`은 evaluator와
`trace-qualification-v2`의 `investigation_evidence`·`investigation_lifecycle`을 포함한
25/25 checks를 통과했다. 10/10 exact input telemetry, 자연 rejected-patch retry 1/1,
81,719 input + 5,952 output token과 계산상 `$0.08807325`를 기록했다. 이 pilot의 task
outcome은 후속 12-run baseline이나 memory 효과와 별도로 보고한다.

기존 mini D-037 r3, r4, r5와 r6 suite는 terminal inspection 전용이다. Journal이나 result를
삭제하거나 approval flag를 다시 전달하지 않는다.

Pilot suite와 승인 hash는 소비됐으며 재실행하지 않는다. 그 pilot에 결속된
`dev-no-memory-v4-20260730-r1` campaign도 별도 승인 hash로 정확히 한 번 실행되어 이제
terminal inspection 전용이다.

과거 Terra r3의 `experiments/dev-validation-pilot.template.yaml`은 evidence 해석을 위해
원래 계약 그대로 남아 있으며 preflight가 `HISTORICAL_SUITE_IMMUTABLE`로 재실행을 차단한다.
Primary r1 suite도 이제 terminal inspection 전용이다. Journal/result blocker를 유지하고
approval flag나 소비된 hash를 다시 전달하지 않는다.

D-048 offline gate는 durable investigation ledger, semantic replay, tail admission과
request-by-request qualification 재계산을 추가한다. 별도 승인된 v4 pilot
`run_d7207fbb06184dd3`은 official evaluator와 qualification 25/25를 통과했고 자연
rejected-patch retry 1/1을 남겼다. 이 run에서 semantic replay와 tail admission block은
각각 0회였으므로 해당 branch는 offline evidence로만 주장한다. Campaign preflight의 exact
pilot/current commit equality는 완화하지 않았다. 대신 clean detached worktree를 pilot commit
`5045e398646ec73d615785aeb95f02e877c34c90`에 두고, host의 external `.patchloop`
runtime root를 junction으로 공유하는 exact-commit bridge로 실행했다. 이 root에는 mutable
SQLite와 workspaces도 포함되며 event/artifact evidence의 append-only 계약은 그대로
유지했다. 실행 suite는 template에서
`pilot_run_id: run_d7207fbb06184dd3`만 달랐고 실제 run manifest도 그 exact commit을
기록한다.
공개 가능한 경계는
[v4 pilot evidence record](reports/live-pilot/dev-validation-gpt54mini-investigation-v4-20260730-r1.json)과
[v4 12-run campaign evidence record](reports/memory-development/dev-no-memory-v4-20260730-r1.json)에
고정했다. Campaign execution hash
`sha256:9befd0bf8b2eb7dbc25999786713581b4b6c95f2ad45df56e2f098a9252e5bac`는
이미 소비됐으므로 template, ignored bound suite, journal 또는 result를 삭제해 재실행하지
않는다.

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

2026-07-30T22:25:47Z에 다시 확인한 공식 mini standard rate는 1M token당 input $0.75,
cached input $0.075, output $4.50이며 별도 cache-write rate는 게시되지 않았다. 가격 source는
[OpenAI API pricing](https://developers.openai.com/api/docs/pricing)이고 model page는
`gpt-5.4-mini-2026-03-17`을 current snapshot, 400,000 context, 272,000 max input,
128,000 max output으로 게시한다. Preflight 시점 기준 72시간을 넘으면 가격을 다시 확인하며
SDK version, Git commit과 execution window를 provenance로 남긴다.

D-054 completion panel은 600,000 run-total token과 25,000 output allowance를 모두 최고
output rate로 잡아 run당 `$2.8125`, 두 run `$5.625`, suite cap `$6`를 사용했다. 실제
계산 비용은 `$0.15682575`였고 현재까지 측정된 list-price 합은 `$5.138372625`다.
D-052의 12-run `$14.85`와 96-run `$118.80`은
calibration 뒤 바뀔 수 있는 comparison draft라 현재 승인 합계에 넣지 않는다. Project-wide
`$150` 상한은 machine-enforced guard가 아니며, 실행기는 각 suite의 `cost_limit_usd`만
강제한다.

Consumed tool-v2/context-v3 corrective primary r2
`run_afd5080a77a34995`는 model, budget, harness commit, runtime-contract hash,
official evaluator와 `trace-qualification-v2` 23/23을 통과했다. 이어진 historical
`dev-no-memory-20260728` campaign도 12/12 terminal trace를 보존했지만 evaluator 도달
0/12라 성능 baseline으로 사용하지 않는다. 새 tool-v2/context-v4 pilot
`run_d7207fbb06184dd3`은 `investigation_evidence`와 `investigation_lifecycle`을 포함한
qualification 25/25와 evaluator 도달을 통과했다. 이어진 v4 campaign은 12/12 terminal,
qualification 12/12와 evaluator 도달 3/12를 남겼지만 SCRR은 0/12다. 아홉 run은 strict
exact-request budget reservation 때문에 evaluator 전에 종료됐고, 세 submitted patch는
regression/scope/safety를 통과했지만 hidden acceptance에 실패했다. 따라서 이 결과도 usable
no-memory performance baseline으로 쓰지 않는다. 실패한 live attempt는 삭제하지 않고 run ID,
input/cached/cache-write/output usage, 계산 비용, terminal outcome과 qualification을 보존한다.
Qualification의 `source_evidence_hash`는 approved plan, manifest, events, checkpoints,
persisted result와 agent-visible content-addressed artifact inventory를 결속한다. v2는
`SubmissionAccepted` 안의 nested submitted-patch CAS bytes도 직접 다시 hash한다. 필수
`RunStarted`/`ContextBuilt`/`ModelCalled` artifact reference, cache usage 불변식과 malformed
function-call response의 이미 과금된 usage도 검사·보존하며, development campaign
preflight와 memory review/index admission은 현재 source evidence hash를 다시 계산한다.
`memory validate-review`는 campaign report, failure/qualification/source evidence, 제출 patch와
semantic-group membership을 다시 검증하는 read-only 단계다. 이 명령이 통과해도 사람의
append-only review가 기록되거나 memory index가 생성되지는 않는다.
새 D-031 live trace는 여기에 exact request artifact, context builder가 최근-event/tool-result
cap으로 생략한 양, input-token count endpoint의 예상치와 생성 응답의 실제
`usage.input_tokens`, reasoning-output breakdown, response status·truncation·incomplete reason을
turn별로 추가한다. 요청은 `truncation=disabled`이므로 provider의 silent input truncation은
허용하지 않는다. Historical Terra r1~r3는 이 필드가 도입되기 전 immutable legacy
evidence로 유지한다.
이 경로의 terminal r1 provider suite는
`experiments/dev-validation-gpt54mini-pilot.yaml`이고, v2 corrective retry는
`experiments/dev-validation-gpt54mini-pilot-r2.yaml`이다. Terminal D-037 exercise suite는
`experiments/dev-validation-gpt54mini-d037-r3.yaml`이며 세 suite 모두 당시
`gpt-5.4-mini-2026-03-17` + medium, run total 90,000 token, per-call output 4,096,
$2 cap으로 고정한다. 별도 `development-validation-model-candidate-pilot` purpose이므로
새 primary campaign pilot이나 결과로 집계하지 않는다. 매 turn의 exact input
count와 4,096-token response allowance가 남은 90,000 안에 함께 들어가지 않으면 generation
call을 시작하지 않는다.
새 r4 corrective suite만 diagnostic profile v2로 per-call 25,000과 total 120,000을
허용한다. 이 pair는 suite schema와 post-run approved-plan qualification에서 함께
검증되며 일부만 바꾼 suite는 거부된다. Qualifier는 schedule hash, Git/Docker/SDK 상태와
pilot qualification을 포함한 execution hash도 preflight 공식으로 다시 계산한다.
2026-07-29 configured rates로 계산한
conservative authorization reserve는 `$0.6525`로 $2 cap 아래지만, checked-in suite는
승인 권한이 아니다. 별도 clean execution hash와 invocation-only 승인으로 r4를 한 번
실행한 뒤 terminal evidence로 동결했다. 25,000은
[GPT-5.4 mini model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini)의
published 128,000 max output 안이다.
후속 r5 profile v3는 historical pair를 바꾸지 않고 diagnostic-only 25,000/200,000 pair를
별도 experiment ID로 사용한다. `91,437 + 3 × (10,031 + 25,000) = 196,530`을 올림한
200,000이며, 같은 보수적 preflight 공식의 reserve는
`(200,000 + 25,000) × $4.50/M = $1.0125`로 $2 cap 아래다. Runtime은 계속 exact input과
full 25,000 allowance가 남은 total budget에 함께 들어갈 때만 generation을 시작한다.
Exact-token terminal block은 `model-generation-block-v1`, model/tool/wall counter
terminal block은 `model-generation-block-v2`일 때만 retry와 독립된 valid trace evidence가
되며, retry episode나 diagnostic pass를 만들지 않는다.
세 Terra pilot과 historical mini r1/r2/r3/r4/r5/r6는 usage/source-evidence 보존 경로를 실제 provider에서
확인했다. Terra r2 trace artifact는 qualified지만
evaluator 미도달 때문에 pilot acceptance를 통과하지 못했고, historical Terra r3가 별도 clean execution
hash에서 v1 accepted pilot를 만들었다. Mini r2는 v2 evaluator 경로에 도달했지만 hidden
acceptance는 실패했고 post-run audit에서 D-037 target이 충족되지 않았음이 확인됐다.
Mini r4는 모든 generated response가 completed였지만 REVIEW 전 total-budget guard로
끝나 evaluator와 D-037 retry에는 도달하지 못했다.
Mini r3는 evaluator와 rejected mutation 전에 incomplete response로 끝나 D-037 target을
exercise하지 못했다. Mini r5는 official task와 qualification을 통과했지만 rejection이
없어 D-037 diagnostic은 inconclusive다. Mini r6는 deliberate controlled rejection으로
harness retry branch와 evaluator 도달을 검증했지만 natural recovery rate는 측정하지 않는다.
Historical 일곱 mini run의 누적 계산 비용은 `$0.77412075`였다. Primary r2와 v4 pilot
`run_d7207fbb06184dd3`까지 포함한 열두 paid pilot의 계산상 총액은 `$1.740790125`이고,
첫 12-run development campaign의 계산 비용 `$1.3931925`를 더한 전체 list-price 합계는
`$3.133982625`였다. V4 12-run campaign은 `$1.84756425`를 추가해 D-051 시점 합계가
`$4.981546875`였다. D-055 completion panel의 `$0.15682575`를 더한 현재 사용량 기반
list-price 합계는 `$5.138372625`다. 실제 invoice/free daily usage 적용 여부는 확인하지
않았다. R5, r6, primary r1/r2, v4 pilot, 두 12-run campaign과 모든 소비된 hash는 자동
재실행하지 않는다. 특히 21-call/200,000-token 계약으로 소비된
`dev-validation-gpt54mini-campaign-20260730-r2`, `dev-no-memory-20260728`,
`dev-validation-gpt54mini-investigation-v4-20260730-r1`,
`dev-no-memory-v4-20260730-r1`은 immutable historical evidence다. 실행되지 않은 250k
single-pilot config
`experiments/dev-validation-gpt54mini-token-tail-v5-pilot-r1.yaml`은
`superseded-unexecuted`로 보존되어 preflight에서 차단된다. D-054 completion config
`experiments/dev-validation-gpt54mini-completion-v6-pilot-r1.yaml`은 exact hash 승인 아래
한 번 실행된 뒤 immutable로 닫혔다. Babel `run_685c492e34f84fef`와 Moto
`run_0814be408332479e`는 모두 official hidden/regression/scope/safety와 trace qualification
25/25를 통과했다. Completion/headroom gate는 2/2, budget·infrastructure·qualification
error는 0이었다. 총 사용량은 172,249 input + 6,142 output token, 계산 비용은
`$0.15682575`다. 이는 두 development-validation task의 runtime completion evidence이며
memory 효과나 usable 12-task no-memory baseline은 아니다. Memory human admission과 index
build는 작은 memory-development no-memory budget pilot 뒤까지 보류한다.

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
