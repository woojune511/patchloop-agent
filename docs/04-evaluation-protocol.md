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
7/20이다. Memory-development entry는 SWE-rebench 계열의 Loguru #1451, AnyIO #1121,
tox #3810, Hugging Face Hub #3180, PDM #2781과 pyfakefs #991이며, Moto #7208은
development-validation 전용이다.

Stress는 별도 task count가 아니다. Admitted research task에서 세 sentinel을 미리 선택해
deterministic fault를 적용하는 overlay이며 core aggregate에 포함하지 않는다.

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

## 5. Controlled variables

한 experiment block 안에서 다음을 고정한다.

- Model ID 또는 immutable snapshot과 sampling parameters
- System prompt와 output schema
- Tool schema와 retry/loop policy
- Repository base commit과 task version
- Agent/evaluator container digest
- Max model calls, tool calls, total tokens, wall clock
- Visible check와 private evaluator version
- Memory token budget
- Fault schedule(정상 실험은 `none`)

Run manifest hash가 다르면 같은 controlled block으로 집계하지 않는다. Provider가 immutable model snapshot을 제공하지 않으면 실행 시점과 provider revision을 기록하고 limitation으로 보고한다.

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
5. Development run으로 pipeline을 검증한다.
6. Memory index와 retrieval config를 freeze한다.
7. Condition/task/repetition 실행 순서를 seed 기반으로 섞는다.
8. 각 run의 manifest, raw event, artifact, verifier result를 immutable하게 저장한다.
9. 사전 정의된 aggregation script로 paired result를 계산한다.
10. Task-level matrix, aggregate, confidence interval, failure trace를 함께 공개한다.

실패한 run을 동일 ID로 다시 실행해 결과를 덮어쓰지 않는다. Retry는 새 attempt ID로 연결한다.

## 10. Fault protocol

MVP fault는 admitted research task 중 사전에 고정한 세 sentinel에 deterministic config로
주입한다. Sentinel 선택, trigger와 schedule은 normal/core 결과를 보기 전에 manifest hash로
freeze한다.

| Fault | Trigger | Expected behavior |
| --- | --- | --- |
| Context reset | 10번째 model call 후 history 제거 | Checkpoint로 context 재구성, 완료 탐색 반복 억제 |
| Worker restart | `PatchApplied` 직후 process 종료 | 동일 run 재개, patch 중복 없이 `VERIFY`부터 진행 |
| Test timeout | 첫 full-suite check를 강제 timeout | 무한 반복 없이 targeted strategy 또는 environment failure |

후속 stress candidate는 output truncation, forbidden modification, repeated-action loop다. Random flaky behavior 대신 fixed seed와 schedule을 쓴다.

Terminal-Bench 2.1에서 참고하는 것은 async cancellation, long-horizon scheduling, persisted-state
recovery와 deployment failure의 task pattern이다. Binary forensics, unrestricted Git mutation,
runtime package download 또는 background service 조작이 필요한 원본 task는 현재 constrained tool
계약에 직접 넣지 않는다.

Stress run은 core 96-run campaign의 일부가 아니며 normal/core SCRR와 별도 표로 보고한다.

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
- Success flip과 failure flip task 목록
- Memory가 도움/방해된 대표 trace
- Infrastructure error와 exclusion ledger
- Harness/model/task/memory version provenance

Task 수가 작으면 p-value를 headline으로 삼지 않는다. Effect size, interval, task evidence를 함께 제시한다. Negative result도 그대로 보고한다.

## 13. Leakage controls

- Held-out task를 development prompt/taxonomy tuning에 사용하지 않는다.
- Calibration fixture와 external acceptance trace를 memory source로 사용하지 않는다.
- Held-out evaluation 동안 memory index를 변경하지 않는다.
- Memory builder가 private spec, hidden test, reference patch를 읽지 못하게 한다.
- Raw trace condition도 held-out solution trace를 검색 대상으로 사용하지 않는다.
- Report/viewer가 hidden assertion body를 model-visible trace에 역으로 노출하지 않게 한다.
- Split, config, index, task package의 hash를 run manifest에 기록한다.

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
