# Evaluation Protocol

상태: **Normative draft**

## 1. Evaluation questions

### Core experiment

Harness를 고정하고 memory representation/retrieval만 바꿨을 때 held-out Scope-Compliant Resolve Rate와 비용이 어떻게 변하는가?

### Separate reliability experiments

- Persistent state가 context reset과 worker restart recovery에 미치는 영향
- Deterministic verifier가 scope violation과 regression detection에 미치는 영향

Core memory effect와 reliability component effect를 같은 비교표에서 하나의 원인처럼 해석하지 않는다.

## 2. Dataset roles

물리적 task directory와 연구 eligibility를 분리한다. `data/dataset-manifest.yaml`의 role만
memory와 experiment 사용 가능 여부를 결정한다.

| Role | Purpose | Target | May tune on it? |
| --- | --- | ---: | --- |
| Calibration | Pipeline, schema, evaluator boundary 확인 | 5 | Harness 확인만; 성능·memory 보고 금지 |
| Memory development | Prompt, taxonomy, retrieval, threshold 개발 | 6 | 예 |
| Development validation | Rendering, no-match, leak validation | 2 | 제한적; memory entry 생성 금지 |
| Core same-repo | Repository-specific memory 효과 | 6 | 아니요 |
| Core cross-repo | Remediation rule의 repository 간 일반화 | 6 | 아니요 |
| External acceptance | 원본 benchmark/외부 workflow 호환성 | 별도 | 아니요; core 집계 금지 |

Research dataset target은 calibration을 제외한 20개다. Core campaign은 그중 held-out 12개만
사용한다. 세 smoke task와 기존의 쉬운 dev-train task 두 개는 calibration fixture로 유지하고,
memory generation, core SCRR와 portfolio headline에서 제외한다. 현재 admitted research task는
20/20이다. Memory-development entry는 SWE-rebench 계열의 Loguru #1451, AnyIO #1121,
tox #3810, Hugging Face Hub #3180, PDM #2781과 pyfakefs #991이며, Moto #7208과
Babel #1042는 development-validation 전용이다. SQLGlot #7187, Param #1117, MTPLX #21과
FuseSoC #776, Dagster #33605와 Kubeflow Pipelines #13112는 core-cross-repo held-out
entry이고 Loguru #1297, PDM #3759, AnyIO #1134, Hugging Face Hub #4056,
tox #3846/#3851과 pyfakefs #1269는 core-same-repo held-out entry다. 이들
held-out task는 prompt, tool, retrieval, threshold와 memory tuning에 사용할 수 없다.

Stress는 별도 task count가 아니다. Admitted held-out task에서 세 sentinel을 미리 선택해
deterministic fault를 적용하는 overlay이며 core aggregate에 포함하지 않는다. Frozen
`public-contract-structure-v1` panel은 FuseSoC #776, AnyIO #1134와 pyfakefs #1269다.

### Minimum MVP size

| Data | Target |
| --- | ---: |
| Calibration fixture | 5 |
| Research task | 20 |
| Core held-out task | 12 |
| Research repository | 2 이상 |
| Core repetition | condition당 2회 |
| Stress sentinel | 3 |
| Fault scenario | 3 |

작은 수의 audited research task가 많은 저품질 task보다 우선한다. Calibration evidence가 완전해도
research readiness를 의미하지 않는다.

## 3. Task admission and audit

각 task에는 다음이 필요하다.

- Task ID/version, repository URL, immutable base commit
- Issue와 명시적 acceptance criteria
- Agent-visible checks와 private hidden acceptance
- Regression check
- Allowed/forbidden path, dependency, API, diff-size policy
- Human-reviewed reference patch
- Source benchmark/issue/PR, revision, license, retrieval timestamp와 contamination risk
- 4차원 difficulty audit와 role assignment
- Failure pattern ID와 split 간 중복되지 않는 solution lineage ID
- Base visible pass/private hidden fail, official reference 3회 통과, 세 개 이상 known-bad rejection을
  포함한 content-hashed admission evidence

Research task는 medium 이상이어야 하며 `benchmark-instance` 또는 `upstream-incident` provenance를
가져야 한다. 공개 benchmark의 파일을 그대로 복사하거나 task author의 difficulty label을
신뢰하는 것으로는 충분하지 않다.

Terminal-Bench 2.1은 세 sentinel stress overlay의 failure pattern과 external acceptance에
사용한다. Code-writing 후보는 unrestricted terminal task를 그대로 import하지 않고
PatchLoop의 Python repository, constrained tool, registered check, submitted patch와 separate hidden
evaluator 계약으로 변환한 뒤 재감사한다. 원본 Harbor run과 adaptation 결과는 core SCRR에
합치지 않는다.

다음 task는 결과를 보기 전에 제외한다.

- 외부 credential 또는 nondeterministic network가 필요함
- Base commit에서 required check가 이미 실패함
- 고정 예산에서 실행 시간이 과도함
- Issue만으로 acceptance criteria를 정의할 수 없음
- 의미 있는 hidden acceptance를 작성할 수 없음

결과를 본 뒤 어려운 task를 제거하지 않는다. 사후 제외가 불가피하면 원래 결과와 exclusion reason을 함께 공개한다.

## 4. Memory conditions

| ID | Condition | Context content |
| --- | --- | --- |
| A | `no_memory` | 과거 실패 정보 없음 |
| B | `raw_trace` | 유사 run의 raw trace를 같은 token budget으로 절단 |
| C | `structured` | 구조화된 remediation rule 제공 |
| D | `selective_structured` | Metadata, similarity, rerank, threshold를 통과한 rule만 제공 |

첫 핵심 결과표는 A~D만 사용한다. Human feedback은 별도 확장 실험이다.

### No-memory development trace acquisition

Memory entry를 만들기 전에 live harness 자체를 development-validation task 하나로 검증한다.
Frozen sequence는 다음과 같다.

1. Babel #1042 development-validation task를 `no_memory`로 1회 실행한다.
2. 그 run의 `trace-qualification-v2`가 trace integrity, leakage, function-tool-loop와
   v2 submission lifecycle을 통과했는지 확인하고, 별도 pilot acceptance에서
   `evaluation_reached=true`인지 검사한다.
   성공 patch일 필요는 없지만 infrastructure error나 evaluator 미도달은 accepted pilot가
   아니다.
3. Trace-qualified이면서 acceptance를 통과하고 development suite와 동일한 model,
   budget, harness commit, tool/context runtime-contract hash를 가진 pilot run ID와
   qualification hash를 다음 suite에 고정한다. Historical v1 pilot은 이 gate를 열지 않는다.
4. Frozen memory-development 여섯 task를 `no_memory`로 task당 2회, 총 12회 실행한다.
5. Qualification된 failure만 human review queue에 넣는다. Resolved run도 trace evidence로
   남지만 memory candidate는 아니다.

Pilot의 cost limit은 $2, 12-run development campaign은 $20다. 이 두 실행은 core SCRR
분모에 포함하지 않는다. Development-validation trace도 memory source가 아니다.

각 started attempt는 resolved/task failure뿐 아니라 agent/infrastructure failure도 stable run
ID, event, checkpoint, usage와 terminal outcome을 남긴다. Usage는 uncached input, cached
input, cache-write input, output token과 reasoning-output breakdown을 분리하며 2026-07-28
공식 rate로 비용을 계산한다.
Cached input과 cache-write input의 합은 total input을 넘을 수 없다. Provider가 이미 과금한
응답의 function-call argument가 malformed여도 그 response usage와 비용을 먼저 남긴 뒤
agent failure로 종료한다.
Infrastructure 또는 qualification error가 발생하면 campaign을 중단하고 나머지 schedule row는
`not_started` reason과 함께 남긴다. 실패를 같은 run ID로 재실행하거나 결과를 덮어쓰지 않는다.

새 live turn은 생성 call 전에 같은 model/input/tools/reasoning payload를
[Responses input-token count endpoint](https://developers.openai.com/api/docs/guides/token-counting)로
계산한다. Exact logical request와 context-builder omission/truncation manifest를 CAS에 남기고,
생성 응답의 `usage.input_tokens`와 count를 turn별로 대조한다. 생성 요청은
`truncation=disabled`를 명시하므로 provider가 오래된 input item을 조용히 버릴 수 없다.
Context 초과는 400/provider failure로, count mismatch와 incomplete response는
qualification failure로 가시화한다. Input-token count call 수는 별도로 기록하며 생성
model-call budget이나 model token cost에 합치지 않는다.

Count 뒤에는 현재 누적 input+output, 새 exact input과 manifest의 full
`max_output_tokens`를 합쳐 run budget과 비교한다. 합계가 상한을 넘으면 generation을
호출하지 않고 structured agent failure로 종료한다.

이 비교는 PatchLoop 자체 context policy를 대체하지 않는다. Context artifact는 최근 event
limit로 생략된 event 수와 12,000-character tool-result cap 적용을 별도 필드로 기록한다.
따라서 `request count == response usage`여도 context builder가 의도적으로 제외한 evidence가
있을 수 있고, 이를 “전체 과거 trace가 모델에 전달됐다”는 뜻으로 해석하지 않는다.

새 `phase-evidence-v2` block은 eligible event를 먼저 고른 뒤 최근 12개를 선택하고,
oversized tool artifact를 JSON parse 뒤 semantic field truncation한다. Final review
acceptance에는 `get_diff` result가 available하고 `truncated=false`였다는 exact
`ContextBuilt` evidence가 필요하다. 단순히 과거 어느 시점에 `get_diff`를 호출했거나
passing check가 한 번 있었다는 사실은 제출 조건이 아니다.

Agent submission protocol은 다음 순서를 고정한다.

```text
successful non-empty mutation
→ every registered visible check passes on current diff hash
→ get_diff succeeds after those checks on the same hash
→ complete get_diff result is included in the next model request
→ finish_task
→ accepted patch bytes are frozen in CAS
→ deterministic evaluator
```

뒤의 mutation은 앞선 check/review를 무효화하며, diff hash가 과거 값으로 되돌아와도
이전 mutation epoch의 evidence를 재사용하지 않는다. Tool/patch 실패는 phase를 전이시키지
않는다. 조기 `finish_task`는 즉시 run을 버리지 않고 structured reason을 다음 turn에
돌려주며 두 번까지 복구를 허용한다. 세 번째 rejection은 `premature-stop`으로 분류한다.
`SubmissionAccepted`는 evaluator 진입 승인이고 SCRR 성공은 evaluator의 별도 verdict다.
Legacy v1 trace에는 새 lifecycle event를 합성하지 않는다.

`context_policy_version=phase-evidence-v3`로 D-037 target을 선언한 trace는 latest
rejected mutating-tool input의 exact CAS
bytes, content hash와 rejection reason이 바로 다음 model request에 함께 있었는지
qualification에서 다시 검사한다. Hash descriptor나 error만 포함한 경우, candidate가
context cap에서 잘린 경우, 또는 model이 읽을 수 없는 CAS locator만 제공한 경우는
`rejected_patch_retry_context` failure다. Candidate와 full response allowance가 budget에
들어가지 않아 generation을 시작하지 않은 structured budget failure는 trace integrity와
구분해 보고한다. Qualification은 correlated `ToolCalled`와 `ToolFailed`의 nested CAS
descriptor 및 top-level identity를 다시 확인하고, 첫 후속 `ContextBuilt` request의
`rejected_mutation_retry`를 byte-for-byte 대조한다. 그 request는 첫 후속
`ModelCalled`에 결속되거나 exact-token count 뒤 `ModelGenerationBlocked`로 닫혀야 한다.
Qualification은 기록된 `remaining_tokens`를 신뢰하지 않고 선행 model usage에서
재계산하며, block payload를 terminal `RunFailed`와 `RunResult.terminal_error`에
동일하게 결속한다.
같은 source failure를 가리키는 retry block이 다음 model turn 뒤에도 남아 있으면
next-turn-only 계약 위반이다. Check detail에는 sequence, count와 content hash만 남기고
patch/error body는 복사하지 않는다. Rejection이 없는 v3 trace는 이 조건을 vacuously
통과하지만, D-037 mini diagnostic은 별도로 적어도 한 retry episode를 실제 실행해야 한다.
Mini r2 `run_4a9737ec91964dca`는
`context_policy_version=phase-evidence-v2`인 immutable diagnostic이며 새 gate의 통과
evidence로 소급 해석하지 않는다.

## 5. Controlled variables

한 experiment block 안에서 다음을 고정한다.

- Model ID 또는 immutable snapshot과 sampling parameters
- System prompt와 output schema
- Tool schema와 retry/loop policy
- Context policy와 submission lifecycle version
- Repository base commit과 task version
- Agent/evaluator container digest
- Max model calls, tool calls, total tokens, wall clock
- Visible check와 private evaluator version
- Memory token budget
- Fault schedule(정상 실험은 `none`)

Run manifest hash가 다르면 같은 controlled block으로 집계하지 않는다. Provider가 immutable model snapshot을 제공하지 않으면 실행 시점과 provider revision을 기록하고 limitation으로 보고한다.

현재 memory-development와 core live block은 `gpt-5.6-terra`, reasoning `medium`, mode
`standard`, service tier `default`, max output 4,096 token과 run budget
`20 model call / 50 tool call / 80,000 total token / 900초`를 고정한다. 현재 공식 catalog에는
dated Terra snapshot이 없으므로 alias, OpenAI SDK version, clean harness Git commit과
execution window를 provenance로 사용한다. D-031 provider telemetry를 검증하는 별도
development-validation model-candidate pilot은 `gpt-5.4-mini-2026-03-17`, medium,
default tier, per-call output 4,096과 run 전체 input+output 90,000 token을 고정한다.
Terminal r1과 v2 corrective r2는 별도 experiment ID로 보존하며, 이 diagnostic lane은
core headline 비교나 Terra 선행 gate에 포함하지 않는다.

Paid execution은 config의 boolean으로 승인하지 않는다. Secret-free preflight가 출력한 exact
execution hash를 사람이 검토한 뒤, 해당 invocation에만 `--approve-live-cost`와
`--approved-execution-hash`를 함께 전달한다. Hash는 suite, frozen dataset/task/schedule,
Git commit, canonical dataset package path, public/private spec hash, digest-pinned environment와
observed Docker identity, SDK와 선행 pilot qualification을 결속한다. Preflight는 API key의
값이 아니라 존재 여부만 보고, custom OpenAI base URL을 거부한다.

Ready preflight는 durable `experiment-execution-plan-v1`을 먼저 저장한다.
`CampaignStarted`로 journal을 원자적으로 exclusive create하고 flush와 fsync한 뒤 그
plan에서만 live capability를 발급한다. 동시 invocation의 선점 패자는 authorization 전에
중단하며, 각 `RunStarted`도 해당 paid call 전에 fsync한다. Hard crash 뒤 남은 journal은
같은 experiment의 자동 재실행을 차단한다. 중단된 campaign을 자동 resume하는
기능은 아직 없으므로 journal을
삭제하거나 새 experiment ID로 우회하지 않고 별도 recovery 절차가 마련될 때까지 보존한다.

승인 후 suite 경로는 다시 읽지 않으며 plan의 normalized suite snapshot만 실행 입력으로 쓴다.
각 task package와 생성 manifest도 plan의 task/model/budget/environment identity와 다시
대조하고, 불일치하면 `RunStarted`와 model call 전에 중단한다.

2026-07-28 공식 [OpenAI API pricing](https://developers.openai.com/api/docs/pricing)은 1M
token당 input $2.50, cached input $0.25, cache write $3.125, output $15다. Preflight는
verification age가 72시간을 넘거나 rate가 다르면 실행하지 않으며, 남은 cost limit에서 한
run의 frozen budget reserve를 확보할 수 없는 경우 다음 run을 시작하지 않는다.

2026-07-29 UTC에 다시 확인한 `gpt-5.4-mini` standard rate는 input $0.75/M, cached input $0.075/M,
output $4.50/M이며 별도 cache-write rate는 없다. Mini pilot preflight는 model ID와 이
price profile을 함께 검증하며 $2 cap 안에 보수적 $0.423432 run reserve를 요구한다.

## 6. Selective retrieval policy

초기 retrieval pipeline:

1. Language, current phase, failure signal을 추출한다.
2. Metadata filter를 적용한다.
3. Semantic similarity로 candidate를 찾는다.
4. Candidate를 fixed scoring rule로 rerank한다.
5. Relevance threshold를 적용한다.
6. Memory token budget 안에서 선택한다.
7. 기준 미달이면 아무 memory도 제공하지 않는다.

초기 scoring proposal:

```text
score =
    0.35 * semantic_similarity
  + 0.25 * failure_class_match
  + 0.15 * phase_match
  + 0.15 * language_match
  + 0.10 * historical_validation_score
```

Weight, embedding, reranker, threshold는 development set에서 결정하고 held-out 전에 config와 hash로 동결한다.

## 7. Primary metric

Scope-Compliant Resolve Rate(SCRR):

```text
SCRR = Σ I(hidden_pass AND regression_pass AND scope_pass AND safety_pass) / N
```

Infrastructure error와 not-run은 성공으로 세지 않는다. 분모 처리 정책은 사전에 config에 고정하고 error count를 별도 보고한다.

여기서 `scope_pass`는 path, diff size, dependency, test tampering, public API policy가 모두 pass인 집계값이다. Safety는 command, network, secret, sandbox policy 위반을 별도로 집계한다.

## 8. Secondary metrics

| Category | Metrics |
| --- | --- |
| Correctness | Resolve@1, hidden pass rate, regression-free rate |
| Policy | scope violation rate, unsafe-action attempt rate |
| Recovery | recovery rate, duplicate-action rate, repeated-work count |
| Efficiency | input/output token, cost/attempt, cost/resolved task, median time, tool calls/resolution |
| Stability | repetition consistency, infrastructure error rate |
| Memory | retrieval precision, no-match accuracy, utilization, token overhead, success/failure flip, negative transfer, utility/1K tokens |

Memory utilization과 negative-transfer 원인은 자동 metric만으로 단정하지 않고 blinded trace review를 연결한다.

## 9. Execution protocol

1. Task split과 exclusion list를 freeze한다.
2. Task public/private package를 audit하고 reference patch가 성공하는지 확인한다.
3. Known-bad/no-op/out-of-scope patch가 적절히 실패하는지 확인한다.
4. Harness, model, budget, container, evaluator config를 hash한다.
5. `--preflight-only`로 canonical task/private evaluator, live environment, price, budget
   reserve와 execution hash를 검토한다.
6. Explicit invocation approval을 durable execution plan으로 저장하고 campaign/run start를
   journal에 fsync한 뒤 Babel development-validation pilot을 실행하고 trace를 qualification한다.
7. Trace qualification과 `evaluation_reached=true` acceptance를 함께 통과한 pilot hash에
   결속된 여섯 task × 2 no-memory development campaign을 실행한다.
8. Eligible failure의 append-only human review를 거쳐 memory index와 retrieval config를
   freeze한다.
9. Condition/task/repetition 실행 순서를 seed 기반으로 섞는다.
10. 각 run의 manifest, raw event, checkpoint, result, artifact와 verifier result를
    immutable하게 저장하고 `source_evidence_hash`로 결속한다.
11. 사전 정의된 aggregation script로 paired result를 계산한다.
12. Task-level matrix, aggregate, confidence interval, failure trace를 함께 공개한다.

실패한 run을 동일 ID로 다시 실행해 결과를 덮어쓰지 않는다. Retry는 새 attempt ID로 연결한다.

## 10. Fault protocol

MVP fault는 admitted research task 중 사전에 고정한 세 sentinel에 deterministic config로
주입한다. Sentinel 선택, trigger와 schedule은 normal/core 결과를 보기 전에 manifest hash로
freeze한다.

### Sentinel selection

선택은 held-out 12개의 public contract structure만 사용한다. Private spec, hidden test,
reference patch, agent trace와 model 성공/실패는 입력이 아니다. 선택 순서는 다음과 같으며,
앞 단계에서 고른 task는 다음 단계의 candidate에서 제외한다.

| Archetype | Deterministic rule | Selected task | Public signal |
| --- | --- | --- | --- |
| Wide change surface | `max_changed_files` 내림차순, task ID 오름차순 | `fusesoc-retained-parse-error-diagnostics` | 3 files; 동률을 task ID로 결정 |
| Narrow mutation surface | `max_changed_files`, `max_diff_lines`, task ID 오름차순 | `anyio-extensionless-entrypoint-worker-main` | 1 file, 40 diff lines |
| Long visible check | remaining task의 최대 registered-check timeout 내림차순, task ID 오름차순 | `pyfakefs-file-wrapper-io-capabilities` | 240 seconds |

세 archetype은 panel 다양성을 위한 선택 기준일 뿐 fault-task 전용 배정이 아니다. 선택된 세
task 모두가 세 fault를 받는다.

### Frozen schedule

| Fault | Trigger | Expected behavior |
| --- | --- | --- |
| Context reset | 10번째 model call 직후, run당 한 번 | Checkpoint로 context 재구성, 완료 탐색 반복 억제 |
| Worker restart | 첫 durable patch checkpoint 직후, run당 한 번 | 동일 run 재개, patch 중복 없이 `VERIFY`부터 진행 |
| Test timeout | 첫 registered visible check, run당 한 번 | 무한 반복 없이 targeted strategy 또는 structured environment failure |

Memory condition은 `no_memory`로 고정하고 fault-free 비교점은 core campaign의 같은 sentinel
`no_memory` run이다. Context reset과 worker restart는 persistent state `on`/`off`를 각각
task당 2회 실행한다. Test timeout은 `on`만 task당 2회 실행한다.

```text
context reset: 3 tasks × 2 state modes × 2 repetitions = 12
worker restart: 3 tasks × 2 state modes × 2 repetitions = 12
test timeout: 3 tasks × 1 state mode × 2 repetitions = 6
stress derived total = 30
```

Schedule seed는 `20260723`이다. Frozen dataset manifest hash는
`sha256:cf608ca1a35cb270f2e4cadcf0b34912256ef1c9cd3c0757a89692f8a5fdf786`,
schedule hash는
`sha256:d5a3d90f8429f24b6940d4a5cb1b78a35fa34d3fe3df9937ad6c57daba23f468`다.

후속 stress candidate는 output truncation, forbidden modification, repeated-action loop다. Random flaky behavior 대신 fixed seed와 schedule을 쓴다.

Terminal-Bench 2.1에서 참고하는 것은 async cancellation, long-horizon scheduling, persisted-state
recovery와 deployment failure의 task pattern이다. Binary forensics, unrestricted Git mutation,
runtime package download 또는 background service 조작이 필요한 원본 task는 현재 constrained tool
계약에 직접 넣지 않는다.

Stress run은 core 96-run campaign의 일부가 아니며 normal/core SCRR와 별도 표로 보고한다.

이 freeze는 sentinel selection과 machine-readable schedule의 사전 등록을 증명한다.
Local mock E2E에서는 single-file smoke patch의 유일한 atomic postimage replacement 뒤,
outcome persistence 전에 실제 worker process를 종료했다. 새 interpreter는 stale
`RUNNING`을 reclaim해 같은 run ID로 evaluator까지 완료했고, 동시에 resume한 contender는
event/status를 바꾸지 않았으며 `ToolCalled(apply_patch)=1`, `PatchApplied=1`이었다.
Multi-file mixed/partial recovery는 unit test evidence다. 다만 fault runtime의 schedule
소비, 완전한 context-reset 의미론, persistent-state-off arm과 30개 stress run은 아직 완료
증거가 아니다. 이 실행 gate가 통과하기 전에는 campaign recovery 수치나 stress 성공을
보고하지 않는다.

### Recovery success

Recovery rate의 성공은 단순 process 재시작이 아니다. Fault가 없을 때와 동일한 acceptance 조건을 만족하고, budget 안에서 완료하며, corrupt/duplicate mutation이 없어야 한다.

## 11. Ablations

우선순위 ablation:

| Ablation | Primary readout |
| --- | --- |
| Full - Persistent State | Context-reset/worker-restart recovery |
| Full - Selective Retrieval | SCRR, token overhead, failure flip |
| Full - Deterministic Verifier | Scope violation, regression-free rate |

Human approval는 autonomous agent 비교를 바꾸므로 main ablation에 넣지 않는다.

## 12. Analysis and reporting

조건 간 비교는 task-level paired analysis를 사용한다. 보고서는 최소한 다음을 포함한다.

- Task × condition × repetition pass/fail matrix
- SCRR와 각 verifier rate
- Absolute/relative difference와 bootstrap confidence interval
- Same-repo와 cross-repo 분리
- Normal과 stress 결과 분리
- Calibration, external acceptance와 research/core 분모 분리
- Token, cost, duration, tool call
- Turn별 request input-token count 대 response usage, provider truncation/incomplete status,
  context-policy omission과 tool-result truncation
- Success flip과 failure flip task 목록
- Memory가 도움/방해된 대표 trace
- Infrastructure error와 exclusion ledger
- Harness/model/task/memory version provenance

Task 수가 작으면 p-value를 headline으로 삼지 않는다. Effect size, interval, task evidence를 함께 제시한다. Negative result도 그대로 보고한다.

Predeclared task × condition × repetition matrix가 완전하지 않거나 infrastructure,
`not_started`, missing terminal result 또는 trace qualification failure가 하나라도 있으면
report는 `analysis_ready=false`와 exclusion reason을 기록한다. 이때 available-case 수치와
CSV는 복구·진단용으로만 표시하고 `headline_metrics`, paired difference/CI와
success/failure flip은 생성하지 않는다. 누락 row를 제외한 교집합을 정식 비교처럼 보고해서는
안 된다.

## 13. Leakage controls

- Held-out task를 development prompt/taxonomy tuning에 사용하지 않는다.
- Calibration fixture와 external acceptance trace를 memory source로 사용하지 않는다.
- Held-out evaluation 동안 memory index를 변경하지 않는다.
- Memory builder가 private spec, hidden test, reference patch를 읽지 못하게 한다.
- Failure classifier는 hidden check ID를 저장하지 않고 공개 check type/state와 opaque evidence
  locator만 저장한다.
- `trace-qualification-v1`/`v2` leakage scan은 private token의 본문을 결과에 복사하지 않고 match
  count만 남긴다. 공개 contract에 이미 있는 generic structure marker/hidden check ID만
  예외로 하고 reference/hidden artifact identity와 API key는 항상 private로 검사한다.
- Qualification의 `source_evidence_hash`는 approved plan, manifest, events, checkpoints,
  result, agent-visible artifact inventory와 v2 accepted-patch CAS bytes를 결속하며
  development campaign preflight와 review/index admission 때 다시 계산한다. v2 final-review
  검사는 sidecar뿐 아니라 hashed request body의 user context를 parse해 exact `get_diff`
  event와 complete patch payload가 실제 포함됐는지도 확인한다.
- Review는 원본 failure record를 수정하지 않고 이전 review hash를 잇는 append-only
  `failure-review-v1` history로 기록한다.
- Raw trace condition도 held-out solution trace를 검색 대상으로 사용하지 않는다.
- Report/viewer가 hidden assertion body를 model-visible trace에 역으로 노출하지 않게 한다.
- Split, config, index, task package의 hash를 run manifest에 기록한다.
- 새 research task의 hidden evaluator 파일은 `task-private-v2.hidden_artifacts`의 content
  hash로 private spec identity에 결합하며, 선언되지 않았거나 hash가 달라진 oracle은
  실행 전에 거부한다.

## 14. Phase 1 evaluator acceptance

`patchloop eval-task <task-dir>` 목표 명령은 다음 fixture를 결정적으로 구분해야 한다.

| Fixture | Expected |
| --- | --- |
| Audited reference patch | success |
| No-op patch | hidden acceptance fail |
| Regression patch | regression fail |
| Forbidden-path patch | scope fail |
| Dependency-changing patch | dependency/scope fail |
| Test-tampering patch | tampering/scope fail |

각 결과는 structured verifier output과 evidence artifact를 남겨야 한다.
