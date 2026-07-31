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
| Development validation | Rendering/no-match/leak와 live runtime/completion validation | 2 | 제한적; memory entry와 core headline 생성 금지 |
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

Historical D-045/D-047 절차는 Babel #1042 development-validation task 한 개를
`no_memory`로 실행한 뒤, trace qualification과 `evaluation_reached=true`를 통과한 pilot에
결속해 memory-development 여섯 task를 task당 2회 실행하는 순서였다. 당시 pilot의
cost limit은 $2, 12-run campaign은 $20이었다. 그 두 historical 12-run campaign은 각각
evaluator 도달 0/12와 3/12로 budget-confounded였으므로 usable no-memory baseline이 아니다.

완료된 D-054 순서는 다음과 같다.

1. Babel #1042와 Moto #7208 development-validation task를 `no_memory`로 각각 1회 실행한다.
2. 두 run 모두 `trace-qualification-v2`, exact prompt telemetry, leakage 검사,
   terminal persistence와 `evaluation_reached=true`를 만족하는지 검사한다.
3. Infrastructure/qualification/diagnostic error와 token/model/tool/wall budget terminal이
   하나라도 있으면 completion gate를 닫는다. Hidden/SCRR 결과는 별도로 보고하되 runtime
   completion gate의 필수조건으로 사용하지 않는다.
4. 20% headroom gate를 함께 계산해 후속 fair-budget 검토 입력으로 쓸 수 있는지 판정한다.
5. 이 gate를 통과하고 별도의 no-memory baseline budget을 동결하기 전에는
   memory-development live campaign과 memory index build를 진행하지 않는다.

D-054 panel의 cost limit은 총 $6이었다. 두 run은 모두 official evaluator의
hidden/regression/scope/safety를 통과했고 panel SCRR 2/2, qualification 25/25,
completion/headroom gate를 기록했다. 실제 계산 비용은 `$0.15682575`였다.
Development-validation trace는 memory source나
core SCRR 분모가 아니다. 이후 no-memory baseline이 확보되면 qualification된 unresolved
failure만 append-only human review 대상으로 삼으며, resolved run은 trace evidence로만 남긴다.

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

Exact input + full output reservation 차단은 `model-generation-block-v1`이다. Input count
전에 이미 model/tool/wall counter가 다음 generation을 허용하지 않으면
`model-generation-block-v2`로 종료한다. V2 qualifier는 strict duration/counter 재계산,
`model → tool → wall` reason 우선순위, budget-guard actor, request CAS와 terminal/result
결속을 검사한다. Valid block은 trace-qualified `agent_failure`이며 evaluator나 task
success로 집계하지 않는다.

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

D-056 opt-in V3/V6에서는 `get_diff`와 `finish_task` 사이에 `review_task`를 추가한다.
Agent는 공개 issue requirement, current-diff registered check 및 선택적 probe, residual
risk를 구조화해 남긴다. 매 run에 probe나 새 test file을 강제하지 않는다. 이 review는
hidden test를 대신하는 judge가 아니라 같은 diff에서 무엇을 확인했는지 감사 가능한
self-attestation이며, evaluator의 hidden outcome은 review나 같은-run agent context로
돌아오지 않는다.

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

새 `context_policy_version=phase-evidence-v4` trace는 v3 rejected-patch 계약을
상속하면서, 각 `ContextBuilt` request의 `investigation_ledger`를 그 request보다 앞선
event/checkpoint와 verified read/search input·result CAS에서 다시 계산한다. Qualifier는
ledger content hash, source-through sequence, no-progress streak, tail admission과 실제
rendered request가 재계산 결과와 정확히 같은지 검사한다. 동일 mutation epoch의 exact
search와 fully-covered read는 model action과 `ToolCalled` 1회를 그대로 세되 filesystem
dispatch 없이 `LoopDetected(investigation-loop-v1)`와
`ToolReplayed(tool-replayed-v2)`로 닫힌다. Corrective-tail threshold에서 read/search가
거부되면 `ToolAdmissionBlocked(tool-admission-blocked-v1)`만 기록하고 `ToolCalled`
budget은 소모하지 않는다. Apply/check/diff/finish는 이 admission 정책으로 차단하지 않는다.
CAS 누락·변조, 다른 worktree diff나 mutation epoch의 observation 재사용, request/ledger
불일치는 `investigation_evidence` qualification failure다. 이 within-run policy는 네
cross-run memory 조건에 동일하게 적용한다.

별도 `investigation_lifecycle` check는 기록된 context를 신뢰하지 않고 semantic replay의
`ToolCalled → LoopDetected → ToolReplayed` correlation/order/actor, source sequence와
result CAS, normalized/worktree/mutation identity, no-progress streak를 독립 재계산한다.
Investigation loop와 semantic replay는 일대일이어야 하므로 schema와 semantic marker를
동시에 제거한 orphan lifecycle도 실패한다. Truncated search result는 replay source가
아니며 같은 exact query도 다시 dispatch한다. Admission block은 당시 durable counter와
nominal reserve에서 reason을 다시 만들고 같은 correlation의 `ToolCalled`가 없음을
요구한다. Gateway는 dispatch와 admission에 같은 strict type, safe-path, symlink
containment와 existing-file validation을 적용한다. Admission 당시 resolved path와 target
bytes는 `inspection-admission-preflight-v1` CAS에 동결하며 qualifier는 terminal
workspace 대신 그 CAS를 검사한다. Context tail 계산은 imminent generation 1회를 먼저
차감한 projected model-call count를 사용해야 하며 gateway의 실제 counter와 동일한 허용
경계를 가져야 한다. V4의 replay/admission input·preflight·target·result artifact bytes는
leak scan과 `trace-source-evidence-v4`에 결속하고, v1-v3 source evidence와 qualification
hash는 그대로 유지한다.

`context_policy_version=phase-evidence-v5` qualification은 V4 checks를 상속하고 durable
token projection을 독립 재계산한다. Observed input은 각 선행
`ModelCalled.requested_input_tokens`를 우선하며 값이 `None`일 때만 actual
`input_tokens`를 사용한다. Invalid 값은 fail closed한다. Qualifier는
`projected_next_input = max(observed input) + max(0, maximum positive consecutive
growth)`와 generation 전 5 turn, generation 후 4 turn을 적용해
`reserved_tokens = max_output_tokens + projected_next_input × projected_turns`를
재구성한다. `remaining_tokens <= reserved_tokens`이면 equality를 포함해 read/search만
`ToolAdmissionBlocked(tool-admission-blocked-v2, reason=token_tail_reserved)`로
`ToolCalled`와 dispatch 전에 닫혀야 한다. Apply/check/diff/finish는 이 정책으로 차단되면
안 된다.

V5 qualification은 `investigation-policy-v2`, `investigation-ledger-v2`,
`investigation-tail-policy-v2`, `context-build-evidence-v5`,
`tool-admission-blocked-v2`, `trace-source-evidence-v5`의 version과 source binding을
검사한다. 전체 qualification envelope은 계속 `trace-qualification-v2`다. 이 cutoff는
nominal policy이며 completion guarantee가 아니다. Strict exact-request + full 25,000
response allowance guard는 별도로 유지되어, 이를 넘으면 provider generation 없이
terminal evidence가 남아야 한다. V1-V4 qualification hash와 판정을 소급 변경하지 않는다.

### D-056 opt-in self-validation qualification

`tool_schema_version=v3`와 `context_policy_version=phase-evidence-v6`은 pair로만
qualification한다. 이 경로는 V5 checks를 상속하며 다음을 추가로 검사한다.

- `run_probe`가 관찰되면 `task-public-v2` registered profile인지, manifest의 dedicated
  clean-image digest와 exact execution policy가 일치하는지, read-only checkout,
  networkless/no-secret/no-proxy invocation인지, source/result CAS와 active diff hash가
  일치하는지 검사한다. Task evaluator image에서 실행된 probe는 허용하지 않는다.
- Probe는 optional이다. 호출 수 0은 failure가 아니고, probe pass를 registered check나
  official verifier pass로 환산하지 않는다.
- `review_task`는 latest mutation의 required visible checks와 final `get_diff` 뒤에 있고,
  그 exact request가 인용한 public check/probe/diff result를 완전하게 포함해야 한다.
- `finish_task` request에는 같은 diff의 complete `task-review-v1` canonical 본문과 receipt가
  들어 있어야 하며 submission lifecycle이 source review artifact를 참조해야 한다. Review
  뒤 같은 diff에서 새 probe/check/diff 결과가 생기면 이전 review는 무효다.
- Probe/review source evidence, request binding과 output을 leak scan한다. Private spec,
  hidden assertion, reference patch와 evaluator artifact가 agent-visible evidence에
  나타나면 fail closed한다.

이 check는 tool/lifecycle provenance를 검증할 뿐 review 서술의 의미를 primary grade로
사용하지 않는다. 공식 결과는 변함없이 separate hidden evaluator의 deterministic
hidden/regression/scope/safety conjunction이다. 같은 run에는 hidden 결과를 feedback으로
돌려 재수정하는 loop가 없으며 evaluator 도달 뒤 patch는 immutable하다.

D-059 offline E2E는 dataset 밖 `csv-quoted-newline@2` fixture에서 이 sequence를 실제로
실행한다. Agent가 registered `quoted-newline-case`를 선택하고 clean Docker image에서
성공한 probe event를 만든 뒤, exact request에 제시된 그 event sequence를
`review_task.targeted_validation`과 requirement evidence에 인용해야 한다. Probe stdout,
profile ID, source/result CAS, image identity와 non-authoritative flag를 함께 검사한다.
성공한 probe가 없으면 review가 probe evidence를 꾸며 내도록 요구하지 않으며, nominal
token tail이 `run_probe`를 admission에서 제거한 경우 mandatory review/finish 경로로
진행한다. 이 fixture 검사는 offline lifecycle evidence이지 provider 또는 task 성능
평가가 아니다.

V3/V6은 targeted unit/integration, Docker isolation, recovery, source-evidence/policy tamper,
qualification과 historical byte-stability gate가 모두 통과하기 전에는 live pilot,
memory-development, core experiment에 허용하지 않는다. Gate가 닫혀도 별도 suite/config,
execution hash, 비용 검토와 승인이 필요하다. 기존 V1-V5 run과 qualification artifact에는
새 check를 적용하거나 event를 합성하지 않는다.

D-037 diagnostic suite의 machine consumer는 generic qualification과 별도로 다음 세 상태를
낸다.

| Diagnostic status | 조건 | 해석 |
| --- | --- | --- |
| `passed` | qualification 통과, `evaluation_reached=true`, retry episode 1개 이상, 모든 episode 검증, failed source sequence 없음 | 요청한 retry exercise와 evaluator 경로가 관찰·검증됨 |
| `inconclusive` | qualification과 evaluator 도달은 통과했지만 retry episode가 0 | Agent/task/qualification 실패가 아니라 exercise 미관찰 |
| `failed` | evaluator 미도달, check 부재·중복·malformed 또는 일부 episode 검증 실패 | D-037 diagnostic 계약 실패 |

Requirement는 suite와 execution hash에 포함되고, 관찰 결과는 qualification hash에 결속된
sanitized count/sequence만 저장한다. Patch body와 rejection error body는 diagnostic result에
복사하지 않는다. 한 row짜리 diagnostic은 `passed`일 때만 gate를 연다. `inconclusive`나
`failed`여도 evaluator의 task outcome과 generic trace qualification 원본은 그대로 보존한다.

Terminal r3 `run_e90f7c52aa134182`는 8회 input pre-count가 모두 provider usage와
일치했지만 event 55에서 4,096 output token 중 3,989를 reasoning에 사용하고
`incomplete/max_output_tokens`로 끝났다. 전체 run은 60,930/90,000 token이어서 input
prompt truncation이나 total-budget exhaustion이 아니다. Mutation/rejection/evaluator가
없었으므로 generic qualification과 diagnostic은 실패했고, D-037 exercise는 미관찰이다.

Corrective r4 profile은 official
[reasoning guide](https://developers.openai.com/api/docs/guides/reasoning#allocating-space-for-reasoning)의
초기 권고에 맞춰
`max_output_tokens=25,000`, total run budget `120,000`을 함께 고정한다. Historical mini
r1~r3는 4,096/90,000으로 그대로 qualification한다. V2 profile은 자동 provider retry를
추가하지 않으며, 각 generation 전에 exact input + 25,000 full allowance가 남은 120,000
budget 안에 들어가는지 같은 방식으로 검사한다. Post-run qualifier는 approved plan의
canonical suite hash와 diagnostic/model/output/budget 계약을 manifest에 다시 결속하고,
schedule 및 Git/Docker/SDK/pilot-qualification 입력으로 execution hash를 재계산한다.

R4는 승인 execution hash
`sha256:bbb6dbdcab1c7561c868ae4cc40478d6e3401c5900feb59b8ea09ef38d9156a1`로
정확히 한 번 실행됐다. `run_826c1c7fb3d242c2`의 13개 generation은 모두
`completed`, `truncation=disabled`였고 exact input count와 provider usage가 전부
일치했다. 누적 사용은 84,082 input + 7,355 output = 91,437/120,000 token이었다.
14번째 logical request는 input 8,583을 exact-count했지만 남은 28,563 token보다
input + full allowance 33,583이 커 generation 전에 차단됐다.

이 trace의 `prompt_token_integrity=false`는 provider count mismatch나 incomplete response를
뜻하지 않는다. `failed_event_sequences=[]`이며, retry candidate가 없는 generic
`ModelGenerationBlocked`를 현재 v3 retry-specific terminal validator가 valid로 보지 않아
`terminal_generation_block_valid=false`가 된 것이다. Patch와 visible check, final diff,
REVIEW phase까지는 도달했지만 submission·evaluator·rejected retry는 0개다. 따라서
diagnostic은 `failed/qualification_not_passed`이고 D-037은 검증 또는 반증되지 않았다.

D-041 r5 profile v3는 per-call 25,000-token allowance와 strict reservation rule을 유지하고
diagnostic-only total budget을 200,000으로 올린다. 산출 근거는 r4의 terminal prefix
91,437과 세 tail generation의 보수적 reservation이다.

```text
largest observed exact input = 10,031
one tail reservation = 10,031 + 25,000 = 35,031
r4 prefix + three tails = 91,437 + 3 × 35,031 = 196,530
frozen diagnostic total budget = 200,000
```

각 generation은 계속 exact input과 full 25,000 allowance가 남은 total budget 안에 함께
들어갈 때만 시작한다. 새 exact-request terminal block payload는
`model-generation-block-v1`이다.
Qualification은 이 versioned payload의 request identity, recomputed remaining budget,
no-generation 상태와 terminal result binding을 retry context 유무와 독립적으로 검사한다.
따라서 valid generic budget block은 trace integrity를 실패시키지 않지만 retry episode 또는
D-037 pass로 세지 않는다. Historical unversioned generic r4 block과 21/22 qualification은
그대로 유지한다.

R5에는 synthetic rejection이나 automatic provider retry를 넣지 않는다. Agent가 자연스럽게
rejected mutation을 만들지 않고 evaluator까지 도달하면 generic qualification과 task outcome을
보존한 채 `inconclusive/retry_episode_not_observed`다. 이 결과는 자동 재실행 사유가 아니다.
Evaluator 미도달은 기존대로 diagnostic failure다. R5는 새 experiment ID, clean execution
hash와 별도 비용 승인으로 최대 한 번 실행한다.

D-043 controlled diagnostic은 r3-r5의 natural-rejection 결과를 재해석하지 않는다. 새
r6/profile v4에서만 첫 preflight-valid `PatchPrepared` candidate를 mutation 전에 한 번
거절한다. Primary task grading은 여전히 deterministic evaluator가 수행하며 controlled
rejection 자체는 model-quality success/failure가 아니다. 이 lane의 목적은 real provider
request가 PatchLoop의 exact rejected-patch rehydration 경로를 통과해 evaluator까지
이어지는지를 branch-cover하는 것이다. Verified controlled rejection은 correlated
`PatchPrepared` 바로 다음 sequence의 `ToolFailed`여야 하며, intervening event가 있는
trace는 worktree mutation 여부와 관계없이 fail-closed한다.

V4 pass는 다음 논리곱이다.

```text
qualification == true
AND evaluation_reached == true
AND controlled_rejection_count == 1
AND verified_controlled_rejection_count == 1
AND controlled_patch_applied_sequences == []
AND retry_episode_count >= 1
AND verified_retry_count == retry_episode_count
AND failed_source_failure_sequences == []
AND failed_controlled_source_failure_sequences == []
```

Controlled rejection 뒤 수정 patch가 task를 해결했는지는 별도 official verdict로 보고한다.
따라서 이 run은 D-037 harness property evidence가 될 수 있지만 자연 발생 오류에서의 model
recovery rate나 memory 효과를 측정하지 않는다. Core headline, paired comparison과 stress
schedule에는 포함하지 않는다.

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

소비된 D-054 development-validation completion block은
`gpt-5.4-mini-2026-03-17`, reasoning `medium`, mode `standard`, service tier `default`,
max output 25,000 token과 run budget
`40 model call / 100 tool call / 600,000 total token / 1,800초`를 고정했다.
이는 두 task의 runtime completion을 진단하기 위한 높은 ceiling이며 memory-development나
core의 비교 budget을 자동으로 정하지 않는다. D-052의
`21 model call / 50 tool call / 250,000 total token / 900초` memory-development/core
template은 실행되지 않은 pending draft다. 후속 공정 비교 budget은 D-054의 실제 사용량과
20% headroom gate를 본 뒤 모든 memory 조건에 동일하게 별도 동결한다. OpenAI SDK version,
clean harness Git commit과 execution window도 provenance로 사용한다. D-031 provider
telemetry를 검증했던 별도
development-validation model-candidate pilot의 historical r1~r3는
`gpt-5.4-mini-2026-03-17`, medium, default tier, per-call output 4,096과 run 전체
input+output 90,000 token을 고정한다. 새 D-037 corrective r4만 hash-bound diagnostic
profile v2에서 25,000/120,000 pair를 허용하고, 후속 r5 profile v3와 controlled r6
profile v4만 25,000/200,000 pair와 `model-generation-block-v1`을 허용한다. 모든 suite는 별도
experiment ID로 보존하며, 이 diagnostic lane은 core headline 비교나 primary 선행 gate에
포함하지 않는다.

Primary r1은 historical 20-call 계약에서 patch, visible check와 final diff 뒤 `REVIEW`에
도달했지만 `finish_task`용 다음 generation 전에 call budget을 소진했다. Exact patch의
별도 evaluator pass는 원 run을 success로 바꾸지 않는다. D-047 offline gate는 future
campaign의 공정한 21-call 상한과 reason-specific v2 next-generation terminal evidence를
검증했다. Historical r1 qualification 21/22를 소급 수정하거나 소비된 hash를 재사용하지
않는다. Corrective primary r2 `run_afd5080a77a34995`는 official evaluator와
qualification 23/23을 통과했다. 이어진 첫 `dev-no-memory-20260728` campaign은 12/12
qualified terminal trace를 만들었지만 evaluator 도달 0/12라 no-memory 성능 baseline으로
사용하지 않는다. D-048 v4 investigation gate를 통과한 새 pilot 뒤 D-051 12-run도
12/12 qualified terminal trace를 만들었지만 evaluator 3/12, SCRR 0/12이며 아홉
exact-request budget failure가 있다. 이 결과도 baseline이 아니며 token-aware tail
runtime을 offline에서 다시 고정하기 전에는 새 baseline 후보를 실행하지 않는다. D-052는
그 future-only runtime을 `phase-evidence-v5`와 250,000 total-token 계약으로 offline
검증했다. Provider call은 없었다. D-054는 cross-run memory admission을 보류하고,
실행되지 않은 250k single pilot을 supersede한 뒤 Babel과 Moto 두 development-validation
task에 600,000-token no-memory completion ceiling을 적용했다. Exact hash로 한 번 실행된
panel은 official evaluator 기준 scope-compliant success 2/2와
qualification·completion/headroom을 통과했고 immutable로
닫혔다. 이 결과만으로 comparison budget을 동결하지 않으며 작은 memory-development
no-memory pilot 전에는 memory condition을 실행하지 않는다. 21/200,000 계약으로 이미 소비된
`dev-validation-gpt54mini-campaign-20260730-r2`, `dev-no-memory-20260728`,
`dev-validation-gpt54mini-investigation-v4-20260730-r1`,
`dev-no-memory-v4-20260730-r1`은 immutable historical evidence다.

D-054 completion panel은 correctness gate가 아니라 runtime gate다.

- Babel은 과거 evaluator/SCRR 완료 이력이 있는 control이고 Moto는 더 넓은 query-state
  추론을 요구하는 harder completion probe다.
- 두 run 모두 terminal, `trace-qualification-v2`, leakage, exact prompt telemetry와
  official evaluator arrival를 통과해야 한다.
- Infrastructure/qualification/diagnostic error와 token/model/tool/wall budget terminal은
  0이어야 한다.
- Hidden/SCRR success는 별도 보고하지만 `no-memory-completion-gate-v1`의 필수조건이
  아니다. Hidden failure라도 evaluator까지 도달했다면 runtime completion evidence다.
- 20% headroom인 480k token, 32 model call, 80 tool call, 1,440초를 둘 다 만족해야만
  관찰 결과를 후속 fair-budget 검토의 입력으로 사용한다. 이 pass는 budget freeze의
  필요조건일 뿐 충분조건이 아니며, memory-development 표본의 별도 no-memory pilot과
  비용 검토 없이 비교 budget을 동결하지 않는다.
- Panel 실패는 자동 재실행이나 즉시 추가 증액으로 이어지지 않는다. Terminal evidence를
  먼저 분석하고 새 suite/hash/승인을 별도로 만든다.

D-060은 다음 calibration을 기존 campaign과 분리된
`memory-development-no-memory-budget-pilot` purpose로 고정한다.

- Task는 immutable V4 budget-terminal run에서 resource maximum을 기록한 HF Hub
  `hf-hub-xet-endpoint-propagation`, PDM `pdm-ignore-active-venv-resolution`, pyfakefs
  `pyfakefs-makedirs-parent-traversal` 세 개다. pyfakefs가 total-token과 wall-clock 두 축을
  차지하므로 task ID로 deduplicate한다.
- 조건은 `no_memory`, task별 1회, tool v2/context v5이며 budget은
  `40 model / 100 tool / 480,000 total token / 1,800초`, output 25,000이다.
- `no-memory-budget-pilot-gate-v1`은 3/3 terminal·qualified·official evaluator arrival와
  budget/infrastructure/qualification/diagnostic error 0을 요구한다. SCRR는 별도 보고한다.
- 이 purpose는 prior pilot gate를 요구하지 않고 memory candidate를 만들지 않으며, 성공해도
  final comparison denominator, fair budget 또는 memory admission을 자동으로 열지 않는다.
- Frozen rate의 보수적 authorization reserve는
  `(480,000 + 25,000) × $4.50/M = $2.2725`/run, 총 `$6.8175`, suite cap `$7`다.

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

2026-07-30T22:25:47Z에 다시 확인한
[OpenAI API pricing](https://developers.openai.com/api/docs/pricing)의 `gpt-5.4-mini`
standard rate는 input $0.75/M, cached input $0.075/M, output $4.50/M이며 별도
cache-write rate는 없다. Preflight는 verification age가 72시간을 넘거나 rate가 다르면
실행하지 않는다. D-054 completion panel의 600,000 total과 25,000 response allowance를
frozen repository의 최고 rate로 예약한 authorization reserve는 run당 `$2.8125`, 두 run
`$5.625`이고 suite cap은 `$6`였다. 실제 계산 비용은 `$0.15682575`였고, 이를 이전
measured list-price `$4.981546875`에 더한 누적 합은 `$5.138372625`다. D-052의 12-run
`$14.85`와 core `$118.80` reserve는 calibration 뒤 변경될 수 있는 draft라 현재 승인
합계에 넣지 않는다. Reserve는 예측
지출이나 invoice·무료 사용 증거가 아니다. Project-wide `$150` 상한은 machine-enforced가
아니며 runner가 강제하는 것은 각 suite의 `cost_limit_usd`다.

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
   journal에 fsync한 뒤 Babel+Moto D-054 completion panel을 실행하고 trace를 qualification한다.
7. Immutable V4 resource evidence로 고정한 pyfakefs, PDM, Hugging Face Hub 세 task를
   provisional `480k token / 40 model / 100 tool / 1,800초` no-memory suite에서 각각
   한 번 실행한다. 새 suite, execution hash, 비용 검토와 별도 승인이 필요하다.
8. 세 run 모두 terminal·qualified·official evaluator arrival, budget/infrastructure/
   qualification error 0인지 확인한다. SCRR는 completion과 분리해 보고한다.
9. 통과하면 전체 여섯 memory-development task를 포함하는 별도 no-memory calibration으로
   task coverage를 확보한다. Provisional budget에서 나온 run은 최종 comparison denominator로
   소급 편입하지 않는다.
10. 세-task 및 여섯-task 관찰값과 전체 비용 계획을 검토한 뒤 모든 memory 조건에 동일한
    fair budget을 동결하고, 새 승인 아래 no-memory baseline을 수집한다.
11. Eligible failure의 append-only human review를 거쳐 memory index와 retrieval config를
   freeze한다.
12. Condition/task/repetition 실행 순서를 seed 기반으로 섞는다.
13. 각 run의 manifest, raw event, checkpoint, result, artifact와 verifier result를
    immutable하게 저장하고 `source_evidence_hash`로 결속한다.
14. 사전 정의된 aggregation script로 paired result를 계산한다.
15. Task-level matrix, aggregate, confidence interval, failure trace를 함께 공개한다.

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
`not_started`, missing terminal result, trace qualification failure 또는 required trace
exercise의 inconclusive/failure가 하나라도 있으면
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
- Machine `memory_candidate_eligible`은 review queue eligibility일 뿐 자동 index admission이
  아니다. Exact-request budget exhaustion처럼 runtime confound가 있는 trace는 별도
  procedural analysis로 격리하고, hidden acceptance에 실패한 task trace만 public evidence로
  self-review한 뒤 사람이 leak scan과 semantic deduplication을 승인한다.
- Structured review는 먼저 `memory-review-proposal-v1`으로 고정한다. Validator는
  campaign의 task-failure candidate와 budget-confounded exclusion exact coverage,
  current failure/qualification/source-evidence/public-spec/submitted-patch hash, event
  sequence와 semantic group membership을 read-only로 재검증한다.
- Proposal producer가 `maintainer-assisted`이면 자동 agent self-review evidence로
  해석하지 않는다. `model-self-review`는 exact model ID와 sanitized response artifact
  hash를 요구하고 별도의 usage/cost gate를 따른다.
- Proposal group은 `candidate`와 `hold`를 구분한다. Public evidence로 stage-specific
  causal claim을 뒷받침할 수 있는 group만 candidate가 될 수 있다. 원인을 특정할 수 없는
  반복은 일반적인 조언을 억지로 admission하지 않고 hold로 남긴다.
- Proposal validation은 human approval이 아니다. Append-only review가 proposal/rule/group
  provenance를 결속하고 builder가 group-level dedup entry를 소비하는 후속 계약이
  완료되기 전에는 실제 index를 build/freeze하지 않는다.
- D-054 순서에서는 위 human approval과 index build 자체도 high-budget completion panel과
  새 no-memory baseline 뒤까지 보류한다. V4 proposal은 historical candidate/hold
  evidence로 남기며 새 baseline의 failure와 합치거나 성능 개선 근거로 사용하지 않는다.
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

## 15. D-060 budget diagnosis and D-062 corrective pilot

`patchloop budget --experiment <id-or-path>`는 persisted result와 append-only state를 읽어
run별 model/tool/token/wall headroom, exact-request deficit, token-tail 차단과 동일-prefix
counterfactual minimum을 계산한다. 원본 event, checkpoint, result JSON은 변경하지 않는다.

D-060 재집계 결과는 다음처럼 분리한다.

| Task | Used tokens | Binding dimension | Interpretation |
| --- | ---: | --- | --- |
| HF Hub | 438,483 / 480,000 | total tokens | exact next request deficit 5,171; v5 same-prefix exploration minimum 658,739 |
| PDM | 153,702 / 480,000 | none | hidden task failure; budget 증거가 아님 |
| pyfakefs | 252,066 / 480,000 | none | hidden task failure; budget 증거가 아님 |

후속 `memory-development-no-memory-corrective-pilot`은 위 세 task를 no-memory 1회씩만
실행한다. Budget은 `40 model / 100 tool / 900,000 token / 1,800초`, output 25,000이다.
V7 projection으로 계산한 historical HF 동일-prefix minimum 697,790에 약 202k 여유를 주며,
historical 평균 token/call에서는 40-call counter가 먼저 오도록 설계했다. 이는 새 prompt와
정책이 있는 미래 run의 completion guarantee가 아니다.

Corrective preflight는 configured rate, 공식 source, run당 reserve와 schedule upper bound를
하나의 pricing block으로 결정적으로 파생한다. Qualification은 plan의 선언을 신뢰하지 않고
suite/model/budget/schedule로 이 block 전체를 다시 계산한다. 가격 확인 freshness는 qualification
실행 시각이 아니라 append-only trace의 unique runner `RunStarted` 시각을 경계로 삼는다.
Verification time이 미래이거나 72시간을 초과하면 실패하며 정확히 72시간은 허용한다.

Gate `no-memory-corrective-pilot-gate-v1`은 세 row가 terminal, qualified, official evaluator
arrival이고 infrastructure/qualification/diagnostic/budget terminal error가 0인지 본다.
SCRR는 별도 task outcome으로 보고 gate 조건에 넣지 않는다. 이 purpose는 report baseline,
memory candidate/admission, core aggregate와 모든 memory-effect headline에서 제외한다. Frozen
rate reserve는 run당 `$4.1625`, 3-run `$12.4875`, suite cap `$13`이며 execution에는 clean
hash와 별도 비용 승인이 필요하다.
