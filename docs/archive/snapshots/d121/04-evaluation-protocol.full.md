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
measured list-price `$4.981546875`에 더한 D-055 시점 누적 합은 `$5.138372625`였다. D-052의 12-run
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

이 authorization은 이후 execution hash
`sha256:464a6eca2597698ca35caa4d7c97173f1af792daec042c36d81b5b8189ae4031`에 대해 정확히 한
번 소비됐다. Experiment `dev-no-memory-corrective-pilot-20260731-r1`은 첫 HF Hub row
`run_0ccfc8fd359a4785`만 실행한 뒤 original trace qualification failure로 fail-closed했다.
PDM과 pyfakefs row는 not-started이고, original `no-memory-corrective-pilot-gate-v1` verdict는
false로 유지한다. Original result, journal과 qualification artifact를 수정하거나 이
experiment/hash를 재실행해서 denominator를 채우지 않는다.

HF run은 33개 completed response에서 875,908 token과 `$0.8408853`의 list-price cost를
기록했다. Exact-request budget block 전까지 `PatchPrepared`/`PatchApplied`와 evaluator
receipt는 없었다. Trace에는 saturation 이후 dispatch되지 않은 read/search 30건과 preview에서
거부된 patch candidate 7건이 있다. 특히 saturation admission과 model-visible phase contract가
불일치했으므로 이 run은 model capability, SCRR 또는 no-memory 성능 baseline이 아니다.

Original qualification failure와 별개로 qualifier의 v5-vs-v6/v7 reserve-version drift가
관찰됐다. Append-only correction `qcor_8b6ff812...4870b6`는 corrected trace qualification을
통과했지만 original result, qualification, campaign gate와 task outcome은 변경하지 않는다.
다음 gate는 v7을 소급 변경하지 않는 새 `phase-evidence-v8` saturation-context
계약의 offline evidence다. 그 뒤에도 D-062 continuation이 아니라 새 execution identity와
별도 비용 승인을 가진 single live pilot만 허용한다.

### D-064 V8 single live pilot protocol

새 suite `dev-no-memory-saturation-v8-pilot-20260801-r1`은 HF Hub 한 task를 `no_memory`로
한 번만 실행한다. Model/runtime/budget은 `gpt-5.4-mini-2026-03-17`, medium/standard/default,
tool v4/context v8/runtime contract v2, 40 model/100 tool/900,000 total token/1,800초,
output 25,000으로 고정한다. Worst-case reserve는 `$4.1625`, suite cap은 `$5`다.

`trace-qualification-v2`는 trace 구조와 public/private boundary를 판정한다. 별도
`v8-saturation-context-v1` diagnostic은 다음을 요구한다.

```text
saturated_context_count >= 1
AND saturated context에서 read_file/search_files가 allowed_next_actions에 없음
AND post-saturation successful PatchApplied 뒤 첫 context가 존재
AND 그 context의 semantic_replay_count == 0
AND mutation_epoch_sequence == PatchApplied.sequence
AND failed_reset_context_sequences == []
```

Trace가 유효하지만 saturation이나 reset opportunity가 나타나지 않으면 inconclusive다. 이는
자동 재실행 권한이 아니며 그 1회 결과를 그대로 보존한다. Gate는 terminal·qualified·official
evaluator arrival, diagnostic pass와 infrastructure/qualification/diagnostic/budget error 0을
요구하지만 SCRR는 요구하지 않는다. 이 결과는 tuning/policy evidence이며 comparison
denominator, failure-memory admission과 core headline을 열지 않는다. Checked-in suite와
no-call preflight는 비용 승인이나 provider 호출 권한이 아니다.

### D-066 V9 offline review-evidence protocol

D-064의 total-token ceiling에는 240,627 token이 남았고 binding dimension은 40 model calls였다.
그러나 먼저 증액만 하면 14회 review rejection 원인을 섞으므로, D-066은 provider 없이 다음
논리곱을 검증하는 versioned correction이다.
이 offline path는 `review_evidence_validation=True` + mock provider + experiment 부재만 허용하며,
live V9은 exact D-067 purpose + OpenAI provider selector로 분리한다.

```text
phase-evidence-v9 request in REVIEW
AND current-diff required passing checks pinned outside recent-event eviction
AND final current-diff get_diff pinned outside recent-event eviction
AND exact citable sequence list visible to model and tool gateway
AND stale/forged/wrong-diff citation rejected with review-citation-error-v1
AND qualifier independently rebuilds the same anchors and artifact CAS
AND three review failures in one mutation epoch terminate before another generation
AND successful PatchApplied resets the rejection epoch
AND historical V8 rendering and qualification remain unchanged
```

이 gate는 task success, live model improvement 또는 memory 효과를 측정하지 않는다. 집중
회귀는 504 collected, 502 passed/2 skipped였고 full regression은 879 collected,
872 passed/7 environment-dependent skipped로 통과했다. 이는 offline integrity evidence다.

### D-067 historical V9 completion-pilot protocol and consumed outcome

Offline gate 이후 별도 승인으로 실행한 suite
`dev-no-memory-review-evidence-v9-pilot-20260801-r1`은 HF Hub 한 task, `no_memory` 1회,
tool v4/context v9/runtime v3, 60 model/100 tool/1,200,000 token/1,800초와 output 25,000으로
고정한다. Dated standard rate의 conservative authorization reserve는 `$5.5125`, cap은 `$6`다.
40→60 model call과 900k→1.2M token 증액은 D-064 tail을 그대로 재생한다는 예측이 아니라
review correction 뒤 남는 우발적 headroom이다.

승인 execution hash는 정확히 한 번 소비됐고 `run_4c77b1102e224785`는 terminal과 official
evaluator에 도달했다. Budget terminal과 infrastructure error는 0이었지만 original
qualification이 32/33이라 `qualified_runs=0`, `qualification_errors=1`이고 campaign gate는
false다. Hidden acceptance도 실패했으므로 outcome은 `task_failure`, SCRR=false다. 이 original
gate는 append-only correction 뒤에도 재계산하지 않는다. Checked-in YAML의 false/null 값은
새 실행을 허용하지 않는 source boundary이며 실행 hash를 재사용하지 않는다.

### D-068 append-only V9 qualification-correction protocol

V9-aware qualifier는 pinned final diff를 recent-events의 대체 증거로 인정하되 request CAS와
source descriptor/path/size/hash/bytes, exact integer sequence, current diff identity, untruncated
body와 nested/top-level exact-one presentation을 모두 검증한다. Historical V1-V8은 recent-event
source를 계속 요구한다. Float/bool sequence alias, duplicate source, missing citable source와
independent sidecar tamper corpus는 모두 fail closed해야 한다.

Correction writer는 original qualification hash
`sha256:8840382b824dc27015e82d2949d39ada06c8169efe0fdcda3b219c3a1dece59e`와 source evidence hash
`sha256:2096b9a6114dc767aabd5e2d35d89077c91993a8cad6c42eeae99e223539f572`를 확인하고 clean
correction harness에서 `persist=false`로 재계산한다. Original bytes가 전후 동일할 때만 새
content-addressed correction을 exclusive-create하며 동일 호출은 idempotent해야 한다. Corrected
qualification pass는 trace integrity만 뜻한다. Original campaign gate, hidden verdict,
`task_failure`, SCRR=false와 baseline/memory/core exclusion은 불변이다.

### D-069 V10 offline public-coverage protocol

D-069는 D-067 hidden failure를 다시 실행하거나 채점하는 experiment가 아니다. 공개 issue의
quantified requirement가 단일 requirement status와 한 visible check만으로 완료되는 것을 막기 위한
offline lifecycle gate다. Maintainer는 `public-review-contract-v2`에서 각 requirement를 explicit
coverage target으로 분해한다. Runtime은 `all`/`every`/`each` keyword만 보고 target을 자동 생성하지
않으며, target set의 완전성은 별도 authoring review 책임이다.

Factory admission과 그 결과 manifest selector는 다음 exact conjunction이다.

```text
build_manifest coverage_review_validation == true
AND emitted tool_schema_version == v5
AND context_policy_version == phase-evidence-v10
AND public_review_contract.schema_version == public-review-contract-v2
AND provider == mock
AND experiment context is absent
```

Replay, OpenAI 또는 arbitrary provider, experiment-bearing manifest, mixed validation mode는
qualification 대상이 아니라 manifest/start 단계에서 fail closed해야 한다. Factory boolean은
RunManifest field로 영속되지 않으므로 qualifier는 이를 사후 추측하지 않고, 결과 manifest의 exact
v5/v10/contract-v2/mock/no-experiment selector와 runtime source를 검증한다. V10 source는
`corrective-runtime-contract-v4`, `context-build-evidence-v10`, `review-evidence-v2`,
`task-review-v3`, `public-review-coverage-v1`, `public-review-base-provenance-v1`과
`trace-source-evidence-v10`을 사용한다. V1-V9 source schema와 historical qualification은 기존
version과 bytes로 유지한다.

Offline acceptance는 최소 다음 논리곱을 검증한다.

```text
V2 contract가 exact public task/hash에 결속되고 private/reference marker가 없음
AND 모든 requirement가 하나 이상의 canonical, unique coverage target을 가짐
AND 모든 inspection anchor가 model call 전 Git public base bytes에 존재하고 provenance CAS와 일치
AND current_diff_inspection citation이 latest mutation 뒤 same-diff read/path/anchor CAS와 일치
AND passing_validation citation이 same-diff passing visible check와 target check_id에 일치
AND check/read event metadata가 result artifact의 pass/path/content/diff/timeout/truncation과 exact match
AND review-evidence-v2 target mapping과 citable order를 qualifier가 event/CAS에서 독립 재구성
AND review_task가 every requirement/target을 exact once 평가
AND parent requirement status/evidence가 child target의 canonical roll-up과 일치
AND targeted_validation/residual-risk 및 optional probe lifecycle이 public contract/CAS와 일치
AND incomplete review가 durable evidence로 보존된 뒤 REVIEW에서 IMPLEMENT로 전이
AND incomplete coverage 상태의 finish_task가 SubmissionAccepted를 만들지 않음
AND complete same-diff target review 뒤에만 submission lifecycle이 진행됨
AND complete review + accepted submission + evaluation이 실제로 관찰되어 공집합 terminal이 아님
AND crash/resume이 partial decision을 complete로 합성하거나 stale target evidence를 재사용하지 않음
AND missing/duplicate/wrong-kind/wrong-diff/descriptor/hash/bytes/sequence tamper가 fail closed
AND historical V1-V9 contract, rendering과 qualification evidence가 변하지 않음
```

Partial review는 qualification corruption이 아니다. Target row shape와 인용이 유효하면
`coverage_complete=false`인 `task-review-v3`를 보존하고 corrective lifecycle을 검증한다. 반대로
partial review를 곧바로 submission-ready로 처리하거나, unresolved target 없이 complete라고
기록하거나, 다른 target에 광고된 citation으로 target을 verified 처리하면 qualification failure다.

Checked-in HF Hub V2 sidecar는 four code-path inspection targets와 four visible-validation targets를
가진 공개 fixture다. 이는 D-067 original suite/manifest의 replacement, frozen dataset change,
reference patch 또는 hidden oracle가 아니며 paid execution capability를 발급하지 않는다.

D-069 offline acceptance는 complete다. V10 집중 통합 회귀와 repository-wide 971 collected,
964 passed/7 environment-dependent skipped, Ruff 및 `git diff --check`가 통과했고 provider call은
없었다. 증명 범위는 여전히 declared public process coverage와 trace integrity뿐이다. Hidden
acceptance, task correctness, SCRR, live model 성능, no-memory baseline 또는 cross-run memory
benefit은 별도 deterministic evaluator/live campaign evidence 없이는 주장하지 않는다.
D-067/D-068 outcome과 artifact는 immutable하다.

### D-070 exact V10 live-pilot protocol

D-070은 D-069의 generic mock selector를 넓히지 않고 exact
`memory-development-no-memory-coverage-review-pilot` purpose만 OpenAI 예외로 허용한다. Suite는
HF Hub 한 task, `no_memory` 한 번, `gpt-5.4-mini-2026-03-17`
medium/standard/default, 60 model call, 100 tool call, 1,200,000 total token, 1,800초와
25,000 per-call output으로 고정한다. Dated standard output rate로 모든 1,225,000 token을
보수적으로 계산한 reserve는 `$5.5125`, suite cap은 `$6`다.

Preflight와 start/resume/qualification은 exact experiment ID, frozen dataset row와 image,
`public-review-contract-v2` bytes, v5/v10/runtime-v4 prompt/tool hashes, SDK, clean harness commit,
pricing freshness와 randomized schedule을 같은 execution hash로 다시 계산한다. Checked-in YAML과
`--preflight-only`는 capability가 아니다. Clean execution hash에 대한 사용자의 별도 비용 승인 전
provider call을 금지한다.

Post-run `v10-coverage-review-live-pilot-gate-v1`은 한 row의 terminal trace qualification,
official evaluator 도달, budget/infrastructure/qualification error 부재와 다음 다섯 check의
non-vacuous evidence를 요구한다.

```text
public_coverage_contract
AND coverage_decision_integrity
AND coverage_submission_lifecycle
AND coverage_recovery_contract
AND coverage_terminal_contract
```

Task success는 gate predicate가 아니라 별도 관찰값이다. 따라서 hidden failure도 process gate는
통과할 수 있지만 SCRR은 false로 남는다. 이 pilot은 comparison denominator, failure-memory
admission과 core에서 제외한다. D-060과 D-067 experiment ID는 hard-immutable이며 재실행하지 않는다.
D-070 offline contract 회귀는 988 collected, 981 passed/7 environment-dependent skipped, Ruff와
`git diff --check`를 통과했다. Host no-call preflight는 Docker/pinned image, SDK, key presence,
clean Git과 pricing freshness를 통과했고 approval/hash 두 blocker만 남겼다. Provider call은
이 preflight snapshot 시점에는 없었다. 이후 한 번 소비된 live outcome은 아래
D-071 context에 별도로 보존한다.

### D-071 V11 structured rejection and exact-anchor recovery protocol

D-070은 이후 별도 승인 hash로 정확히 한 번 실행됐다. Original
`run_6cc69fc1170c4a44`는 valid partial review 7/8 뒤 missing anchor를 읽지 않은 채
unrelated evidence sequence를 반복 인용해 evaluator 전 submission-protocol failure로 끝났다.
Original gate/qualification/outcome은 immutable하며 D-071은 이 run을 재실행하지 않는다.

D-071은 provider 없이 exact v6/v11 mock path에서 다음 논리곱을 검증한다.

```text
wrong target citation is rejected as coverage-citation-error-v1
AND error names target/requirement, submitted/allowed/invalid sequences
AND error gives only required public path+anchor or registered check IDs
AND source ToolCalled/ToolFailed and input/result CAS are exact
AND every source/recovery/clearing call resolves to one actual model request and declared response tool call
AND worker exits immediately after the durable rejection
AND only state-store checkpoint bookkeeping occurs before the fresh runner's first request
AND model-request CAS and ContextBuilt mirror the exact active worker claim
AND a fresh runner's first request rehydrates coverage-rejection-feedback-v1
AND the active source failure is not duplicated in recent_events
AND exact-anchor current-diff evidence is obtained after resume
AND a later stale retry may be rejected again and then recover on the same reclaimed worker
AND the latest unresolved rejection, not an older rejection, is present in each recovery request
AND every fresh cited validation result is bound, including batched calls from one model response
AND refreshed get_diff precedes one complete task-review-v3
AND the source rejection is fully rebuilt before any clearing decision
AND only a complete review whose arguments and citations rebuild against public evidence clears it
AND any mutation clear has ToolCalled -> PatchPrepared intent -> success -> PatchApplied provenance
AND source, resumed, and cleared requests bind the latest active worker claim
AND submission reaches the separate evaluator
AND PatchPrepared/PatchApplied remain exactly one
AND qualifier independently rebuilds every binding
```

Tamper corpus은 error detail의 allowed sequence, rejection result descriptor/CAS, prior request
identity, restart worker claim/request/mirror, source/recovery tool-call lifecycle, 최초/갱신
diff result CAS, malformed source target mapping, forged clearing feedback/build/review mirror,
missing prepared-patch intent, cleared-request worker claim, orphan review/mutation과 duplicate mutation을
각각 fail closed해야 한다. Stale target sequence만 반복 제출한 retry도 fresh public
evidence 전에는 다시 structured rejection되어야 한다. Focused
`tests/test_coverage_rejection_v11.py`는 durable rejection 직후 `SystemExit`, fresh-runner
resume, 두 rejection 뒤 same-worker recovery, exact-anchor read, multiple/batched validation checks,
complete review, submission과 separate local evaluator, V10 다섯 coverage check 및 새
`coverage_rejection_recovery_contract`의 pass를 검증했다.
Mock/non-campaign run의 overall qualification은 live campaign provenance와 별개이다.

이 protocol은 public recovery feedback의 delivery/integrity를 검증할 뿐, target set의 의미적
충분성, hidden acceptance, live model recovery rate, SCRR, no-memory baseline 또는 memory
효과를 증명하지 않는다. D-071 implementation은 OpenAI/provider call을 실행하지
않았고 추가 model cost는 0이다. 별도 live suite/hash/비용 승인은 없다. Final repository
regression은 999 collected, 992 passed/7 environment-dependent skipped이며 Ruff, compileall과
`git diff --check`도 통과했다.

### D-072 V11 live-readiness protocol

D-072는 먼저 D-071의 context/qualification helper를 전용 모듈로 분리한다. 이 refactor는
tool/context/schema, canonical artifact와 qualifier check 의미를 바꾸지 않고 historical V10/V11
evidence를 재해석하지 않는다. 이후 generic V11 mock selector와 분리된 exact
`memory-development-no-memory-coverage-rejection-pilot` purpose를 추가한다.

Checked-in `dev-no-memory-coverage-rejection-v11-pilot-20260802-r1`은 HF Hub 한 task를
`no_memory`로 한 번만 실행하는 tuning-only row다. Model은
`gpt-5.4-mini-2026-03-17` medium/standard/default, runtime은 v6/v11/runtime-v5이고 budget은
60 model/100 tool/1,200,000 token/1,800초, output 25,000이다. Worst-case reserve는 `$5.5125`,
suite cap은 `$6`다. Generic V11은 계속 mock/no-experiment 전용이고 exact purpose+OpenAI pair만
exact live exception이다.

Live readiness는 자연 rejection을 강제로 만들지 않고 다음과 같이 판정한다.

```text
evaluator_reached
AND trace_qualified
AND public_coverage_lifecycle_observed
AND coverage_rejection_exercise.status in {passed, inconclusive}
AND infrastructure/qualification/budget error absent
```

- Rejection이 0이면 `inconclusive/rejection_not_observed`다. 이는 recovery가 검증됐다는 뜻이
  아니지만 다른 trace-integrity check가 모두 참이면 row qualification과 readiness gate는 통과할 수
  있다.
- Rejection이 하나 이상이면 모든 `coverage-citation-error-v1`, source model request/response와
  tool input/result CAS, fresh public recovery evidence, refreshed diff, clearing review/mutation을 전부
  재구성해야 한다. 누락·위조·실패 sequence가 하나라도 있으면 `failed`이며 gate도 false다.
- Task success와 hidden acceptance는 readiness gate의 필수조건이 아니다. Outcome과 SCRR은 별도로
  보고하며 이 row는 comparison denominator와 memory admission에서 제외한다.
- Offline D-071은 실제 fresh-runner restart를 필수로 검증했지만 D-072 live row는 자연 rejection
  recovery만 판정한다. Provider hard kill과 stale-run reclaim을 live로 시험하는 fault exercise는 별도
  후속 suite·execution hash·비용 승인이 필요하다.

Checked-in source suite의 `live_cost_approved=false`, `approved_execution_hash=null`,
`pilot_run_id=null`은 source config만으로는 no-call이라는 뜻이다. D-072 contract 구현 단계에서는
clean-host preflight, persisted execution plan/hash, 사용자 invocation approval, provider request와 cost
evidence를 생성하지 않았다. Offline test도 fake environment와 temporary root에서 synthetic hash 및
approval branch만 검증했다. 이후의 exact approved invocation과 source suite를 혼동하지 않는다.
D-070 run/hash/gate는 immutable하고 이 contract는 memory admission이나 core campaign을 열지 않는다.

### D-073 D-072 live-result evaluation record

별도 clean-host preflight와 사용자 승인 뒤 execution hash
`sha256:12fb0fb8a02ffe464555bd23125fae18deb6e52e6b6448a482243c036cce080d`를 정확히 한 번 소비했다.
`run_e2132144a8774b05`는 다음과 같이 판정됐다.

```text
terminal = true
official evaluator reached = true
trace qualification = 36/36
readiness campaign gate = true
coverage_rejection_exercise = inconclusive/rejection_not_observed
hidden/regression/scope/safety = fail/pass/pass/pass
outcome/SCRR = task_failure/false
budget_terminal = false
```

따라서 이 run은 D-072의 live request/trace/evaluator readiness를 검증했지만 structured coverage
rejection이 실제로 발생하지 않아 rejection 후 recovery는 검증하거나 반증하지 않았다. 17개의
rejected patch candidate와 verified retry 17회는 별도 `rejected_patch_retry_context` check이고,
`coverage-citation-error-v1` count 0을 바꾸지 않는다. Saturated context 17개 뒤 `PatchApplied` 1회가
발생한 사실도 investigation policy evidence이지 coverage recovery evidence가 아니다.

Usage는 797,862 input + 64,465 output = 862,327 token, 35 model call, 57 tool call, 369,385ms,
계산 비용 `$0.841833`이며 budget dimension은 bind하지 않았다. Task success는 gate 조건이 아니므로
gate pass와 hidden failure가 동시에 유효하다. D-073은 original result/journal/qualification/gate를
수정하지 않고 consumed ID를 source-level immutable set에 추가하며 승인 hash와 portable evidence를
함께 seal한다. 이 row는 재실행하지 않으며
comparison denominator, memory admission, SCRR baseline과 core에서 제외한다. D-073 seal 과정의 provider
call과 추가 model cost는 0이고 live hard-restart는 여전히 별도 fault exercise다.

### D-074 retrospective stop rule and next baseline gate

D-069~D-072는 exact HF Hub task에서 V10/V11 public-review/recovery path를 관찰한 diagnostic lane으로
종료한다. 이 lane은 generic no-memory agent를 대체하거나 generic baseline의 선행조건이 아니다.
Generic development/core comparison은 task-specific coverage sidecar 없이 V2/V5 pair를 사용한다.

현재 template의 `21 model / 50 tool / 250,000 total token / 900초`는 D-052 당시의 pending draft이고,
D-055/D-060 및 후속 diagnostic usage를 반영해 freeze된 comparison budget이 아니다. 따라서 이를
그대로 실행하지 않는다. 다음 paid gate 전에는 exact generic model/prompt/tool/context/budget tuple을
먼저 결정하고, 그 tuple과 current harness commit을 사용한 작은 diverse development readiness panel을
별도 manifest로 고정한다.

Readiness panel은 모든 row의 terminal persistence, trace qualification, official evaluator arrival와
infrastructure/qualification/diagnostic/budget confound 0을 요구한다. Hidden/SCRR success는 요구하지
않는다. 이 panel이 통과하면 tuple을 동결하고 no-memory baseline을 수집한다. 이후 valid hidden failure,
scope-compliant task failure와 predeclared budget 안의 agent failure는 결과로 보존하며, 한 task의 hidden
failure를 통과시키기 위한 prompt/tool/coverage contract 변경이나 같은 task corrective live loop를
진행하지 않는다.

Baseline freeze 전 code change를 다시 허용하는 사유는 public/private boundary, infrastructure,
qualification corruption, deterministic tool/runtime contract 또는 systemic budget confound처럼 결과의
신뢰성을 깨는 문제로 제한한다. 모델이 충분한 public evidence와 frozen budget 안에서 잘못된 patch를
제출한 것은 baseline 성능이지 harness blocker가 아니다. Live hard restart는 별도 reliability protocol로
측정하고 fault-free no-memory baseline을 막지 않는다.

### D-075 exact generic readiness protocol

Checked-in `generic-baseline-readiness-v2v5-20260802-r1`은 D-074의 작은 diverse panel을 다음 네
development row로 구체화한다.

| Order | Dataset role | Task | Public failure surface |
| ---: | --- | --- | --- |
| 1 | Development validation | Babel strict grouped-decimal trailing zeroes | numeric parsing/format boundary |
| 2 | Development validation | Moto query scanned count | query-state accounting |
| 3 | Memory development | pyfakefs makedirs parent traversal | path/parent semantics |
| 4 | Memory development | Hugging Face Hub xet endpoint propagation | endpoint/config propagation |

모든 row는 `no_memory` 한 번이며 `gpt-5.4-mini-2026-03-17`, medium/standard/default,
`SYSTEM_PROMPT_V3`, tool v2/context v5, SDK transport retry 0, output 25,000을 공유한다. Run budget은
40 model call, 100 tool call, 850,000 total token, 1,800초다. SDK transport retry 0은 provider
request의 숨은 재전송을 제거해 model call/usage evidence와 실제 request 횟수를 맞추기 위한 controlled
variable이다. PatchLoop의 event-visible tool retry와 worker recovery는 변경하지 않는다. Historical
suite는 retry field를 생략한 채 기존 adapter behavior와 hash를 유지한다.

Gate `generic-baseline-readiness-gate-v1`은 4/4 exact task identity, terminal result, trace
qualification, evaluator arrival와 official completed evaluation, 그리고 infrastructure,
qualification, diagnostic 및 token/model/tool/wall budget terminal 0을 요구한다. Hidden pass,
scope-compliant success와 SCRR는 별도 task outcome이며 gate에 넣지 않는다. 따라서 four-row hidden
failure도 다른 predicate가 모두 참이면 process readiness pass가 될 수 있다.

Purpose는 calibration-only다. Readiness row는 report의 baseline/headline/paired comparison에서 제외하고
CSV에는 `calibration_only=1`, `analysis_included=0`, `exclusion_reason=calibration_only`로 남긴다.
이 출력 경계 변경은 `analysis-report-v2`로 versioning한다. JSON의 일반 `metrics`는 비우고 관찰용
집계만 `diagnostic_metrics`에 두며 HTML에도 diagnostic calibration table로 표시한다. Failure-memory candidate나
index admission을 만들지 않는다. Gate pass도 850k를 comparison budget으로
자동 동결하지 않는다. 이후 public trace에서 condition-neutral systemic confound가 없는지 확인하고,
hidden outcome에 맞춘 task-specific 수정 없이 별도 decision으로 no-memory/comparison tuple을 동결한다.
그 decision이 D-075 budget 또는 harness commit을 바꾸면 final tuple에 대한 second readiness panel이
필요하며 D-075 gate를 소급 승격하지 않는다.

Dated standard pricing block의 conservative reserve는 run당 `$3.9375`, four-row `$15.75`, suite
cap `$16`이다. Checked-in YAML의 false/null approval fields와 no-call preflight는 provider 권한이
아니다. Clean harness commit, task/private package, dataset role, image/evaluator, SDK, pricing freshness,
prompt/tool/retry와 randomized schedule을 결속한 exact execution hash에 사용자가 별도 승인해야 live
campaign을 한 번 시작할 수 있다. 이 offline contract 단계는 provider request, measured cost, readiness
outcome, SCRR 또는 baseline evidence를 생성하지 않는다.

### D-077 budget-only generic readiness successor protocol

D-077은 D-075 r1을 재실행하거나 false gate를 수정하지 않는다. 새 exact ID
`generic-baseline-readiness-v2v5-20260802-r2`로 같은 Babel, Moto, pyfakefs, HF Hub ordered row를
`no_memory` 한 번씩 실행하는 successor다. Model snapshot, reasoning/service tier, `SYSTEM_PROMPT_V3`,
tool v2/context V5, SDK retry 0, output 25,000, tool 100, wall 1,800초, task package, image/evaluator와
fault-free policy는 고정하고 model-call ceiling만 40→50, total-token ceiling만
850,000→1,200,000으로 바꾼다. 다른 model-facing 또는 evaluator 변수가 바뀌면 budget-only panel이
아니므로 새 tuple로 versioning한다.

`generic-baseline-readiness-gate-v1`의 의미는 바꾸지 않는다. 네 row 모두 terminal·qualified이고 official
evaluator를 완료해야 하며 infrastructure, qualification, diagnostic, token/model/tool/wall budget-terminal은
0이어야 한다. Hidden acceptance와 SCRR는 별도 task outcome이므로 gate pass를 요구하지 않는다. 한 row라도
budget에 막히면 panel gate는 false이며 해당 row만 추가 실행하거나 D-075/D-077 결과를 합쳐 gate를 만들지
않는다. Hidden result를 보고 prompt/tool/context, task sidecar나 budget을 task별로 조정하지 않는다.

이 panel도 report에서 calibration-only이며 ordinary metric, comparison denominator, failure-memory admission과
core에서 제외한다. Gate pass 뒤에도 같은 exact tuple을 comparison budget으로 채택할지는 별도 freeze
decision으로 결정한다. Live hard restart/reclaim은 별도 reliability protocol이고 이 fault-free readiness
panel에 합치지 않는다.

2026-08-02T13:11:37Z에 재확인한 공식 rate 기준 reserve는 `$5.5125`/run, `$22.05`/four rows,
cap `$23`이다. Source contract와 offline verification은 paid authority가 아니다. 현재 provider call,
execution hash, 사용자 승인, run, measured cost와 gate outcome은 없다. Clean no-call preflight가 만든 exact
hash와 최대 `$23`에 대한 별도 명시적 승인이 있어야 campaign을 한 번 시작할 수 있다.
Offline protocol validation은 1,095 collected, 1,088 passed/7 environment-dependent skipped와 Ruff,
compileall, `git diff --check`로 닫혔다. Provider call과 추가 model cost는 0이며 clean-host preflight와
live gate는 아직 실행되지 않았다.

### D-079 bounded workflow-completion probe protocol

D-079는 D-078에서 확인한 pyfakefs model-call admission confound만 다루는 one-row calibration이다.
Four-row readiness를 반복하거나 hidden acceptance를 개선하는 실험이 아니다. Exact task는
`pyfakefs-makedirs-parent-traversal`, condition은 `no_memory`, repetition은 1이다. Generic V2/V5
model/prompt/tool/context, SDK retry 0과 output 25,000을 유지한다.

Model/tool call limits는 `null`이며 `model-tool-observability-only-v1` 아래 count와 usage만 추적한다.
3,000,000 total token, 7,200초 wall, exact-request response reservation, cost authorization, loop controls,
constrained tools, Docker/network isolation과 evaluator safety는 계속 강제한다. 따라서 이 probe는
call-count censorship을 제거하지만 무제한 실행은 아니다.

`workflow-completion-probe-gate-v1`은 exact 1/1 terminal·qualified·official evaluator completion,
infrastructure/qualification/diagnostic error 0, disabled-call-guard contract와 retained-guard integrity를
요구한다. Hidden pass와 SCRR는 요구하지 않는다. 의미는 다음처럼 분리한다.

```text
gate pass:
  call-count admission에 잘리지 않고 retained guard 안에서 evaluator까지 workflow 완료

gate fail:
  evaluator 전 non-completion, invalid qualification/guard evidence 또는 infrastructure/diagnostic error

task outcome:
  official hidden acceptance/SCRR는 별도 관찰값이며 gate predicate가 아님
```

`LoopDetected` 같은 semantic-replay event가 한 번 존재하는 것 자체는 gate failure가 아니다. Loop policy의
event/CAS가 유효하고 이후 terminal lifecycle을 완료하면 integrity를 통과할 수 있다. 반대로 loop control,
total-token 또는 wall guard에서 evaluator 전에 종료되면 probe gate는 false다.

Pass/fail 어느 쪽도 자동 재실행, hidden-driven tuning, comparison budget freeze, no-memory baseline,
failure-memory admission 또는 core campaign을 승인하지 않는다. Source/offline stage에는 provider call,
execution hash, cost approval, run/result, measured cost와 gate outcome이 없다. Fresh-pricing no-call preflight의
exact hash와 최대 `$14` 승인을 별도로 받은 뒤에만 한 번 실행하고, 결과는 별도 D-080 seal로 닫는다.

### D-080 D-079 result interpretation and append-only gate correction

D-080 평가는 같은 run에서 서로 다른 세 predicate를 합치지 않는다.

```text
workflow/process observation:
  terminal + qualified + official evaluator reached
  AND no infrastructure/qualification/diagnostic/budget/terminal-loop confound
  => completed

task correctness:
  regression + scope + safety pass
  AND hidden acceptance fail
  => task_failure / SCRR false

historical campaign gate artifact:
  original call_guard_contract_passed false due to omitted summary projection
  => original gate remains immutable false

derived correction:
  full qualification disabled_call_guard_contract exact 1/1 pass
  AND all other original process predicates true
  => derived process gate true, original not replaced
```

이 correction의 input projection은 `qualification-gate-check-projection-v1`이다. Consumer는 outer key set을
`disabled_call_guard_contract` 하나로, inner key set을 `schema_version/check_id/check_count/passed` 네 개로
정확히 제한한 뒤 schema/ID 일치, strict integer count 1과 boolean true를 검사한다. Boolean/float/string
count를 포함한 missing, duplicate, extra 또는 malformed field는 모두 fail closed한다. Correction
`gcor_6552d8277d70fba7f296b0aee837a8f497be8384cce7fea4521cb39de1e19861`의 semantic body hash는
`sha256:6552d8277d70fba7f296b0aee837a8f497be8384cce7fea4521cb39de1e19861`이고 correction harness commit은
`7e40e27446bcf011f700c219a96983e5670422f4`다. ID는 source, correction harness, cause, exact original/
corrected `workflow-completion-probe-gate-v1` payload와 claims boundary를 함께 결속한다.

Run은 84 model/119 tool call, 1,790,707 token과 856,559ms를 사용했다. Token 1,209,293과 wall
6,343,441ms가 남았고 call counters는 limit이 아니며 blocked tool, exact-request block과 budget terminal은
0이다. 따라서 D-078에서 관찰된 50-model-call admission이 이 별도 trajectory의 completion을 censor했을
조건이라는 public process evidence는 얻었다. 다만 한 stochastic row가 일반 completion probability나
frozen comparison budget을 정하지는 않는다.

Public trace efficiency는 별도 diagnostic이다. 84 model call 중 73개와 119 tool call 중 104개가
REPRODUCE에서 발생했고 semantic replay가 repeated read/search 41회를 감지했다. Rejected candidate 3개는
모두 mutation 전에 거부됐고 retry context 3/3이 검증됐다. 이 관찰은 workflow가 구현되지 않았다는
근거가 아니라 exploration-control 효율 개선 후보이며 hidden outcome을 이용한 tuning 권한이 아니다.

D-080 correction은 stored result와 full qualification hash만 읽으며 provider request를 보내지 않는다.
Portable manifest는 `reports/live-pilot/artifacts/d080-workflow-completion-gate-summary-correction.json`이다.
Original result/gate, hidden task outcome과 SCRR를 수정하지 않는다. Corrected process gate true도
calibration-only exclusion, `analysis_ready=false`, no-memory baseline, memory admission과 core closure를
변경하지 않는다. Final offline verification은 focused 331 passed, repository-wide 1,162 collected 중 1,155
passed/7 environment-dependent skipped였고 Ruff, Python compileall, JSON parse와 `git diff --check`를 통과했다.
Provider call은 0이며 추가 model cost는 `$0`이다.

### D-081 condition-neutral four-row protocol and D-082 measured result

D-081은 새 exact ID `generic-baseline-readiness-v2v5-20260803-r3`로 D-075/D-077의 Babel,
Moto, pyfakefs, HF Hub order와 generic V2/V5 tuple을 보존한다. 네 row는 모두 `no_memory` 한 번이며
model/prompt/tool/context/retry/output, task role/package, sidecar absent와 fault-free policy를 바꾸지 않는다.
검증 질문은 “call-count admission이 없는 동일한 condition-neutral ceiling에서 네 workflow가 모두
official evaluator까지 완료되는가”이고 hidden correctness는 별도 outcome이다.

Model/tool limits는 `null`이고 `model-tool-observability-only-v1` 아래 counter와 usage는 계속
trace-qualified telemetry다. Total token 2,400,000, wall 1,800초, exact-request, cost, loop,
constrained-tool, Docker/network/evaluator guard는 유지한다. Candidate는 evaluator-complete public process
rows만 사용해 다음처럼 정했다.

```text
(1,790,707 max observed token
 + 84 model calls * 2,000 memory-token allowance
 + 25,000 next-response allowance)
 * 1.2 headroom
= 2,380,448.4 -> round up to 2,400,000

856.559 seconds * 2 = 1,713.118 -> round up to 1,800 seconds
```

`generic-baseline-readiness-gate-v2`는 4/4 exact identity, terminal, trace-qualified, official evaluator
completion, zero infrastructure/qualification/diagnostic/budget-terminal과 terminal-loop failure를 요구한다.
또한 네 row 각각에서 `qualification-gate-check-projection-v1`의 exact-one
`disabled_call_guard_contract`와 aggregate `call_guard_contract_passed=true`를 요구한다. Task success와
SCRR는 gate 조건이 아니다. 한 row라도 빠지거나 projection이 malformed/duplicate/missing이면 gate는
false이며 D-075/D-077/D-079 row를 합쳐 보충하거나 실패 row만 재실행하지 않는다.

Runtime plan/trace schema는 각각 `generic-baseline-runtime-contract-v2`와
`generic-baseline-runtime-evidence-v2`다. 이는 historical v1 의미를 소급 변경하지 않고 exact r3
nullable-count policy를 분리한다. Report는 계속 calibration-only이며 ordinary metrics, paired comparison,
failure-memory admission과 core에서 제외한다.

2026-08-03T01:08:49Z standard pricing으로 계산한 conservative authorization reserve는
`(2,400,000 + 25,000) * $4.50/M = $10.9125`/run, `$43.65`/four rows, cap `$44`였다.
별도 clean preflight와 승인으로 commit `b4c79242bb0a94eed50530116205323e78c7d21a`, execution hash
`sha256:446b60568795c585856468064fa1aa11a9d85a8e8806e6c71b3b19ab1aa12579`가 결속됐고 D-081은
정확히 한 번 실행됐다. Predeclared predicate를 그대로 적용한 결과 4/4 terminal·qualified·official evaluator,
각 row exact-one disabled-call projection, infrastructure/qualification/diagnostic/budget-terminal 및
terminal-loop confound 0으로 gate v2가 pass했다. Task success는 predicate 밖이며 실제 outcome은 Babel
1/4 success, HF Hub/Moto/pyfakefs hidden failure다. Regression/scope/safety는 4/4 pass다.

사용량은 111 model/175 tool call, 1,929,316 token, 고정 rate 계산 비용 `$1.79426325`다.
111/111 request가 completed·exact-input-matched이고 truncation disabled, `store=false`였다. Natural
rejected-patch retry 3/3이 verified됐고 loop observation은 50회(pyfakefs 39회)지만 terminal loop failure는
없다. 이 비용은 billed invoice/free-tier charge가 아니다. Raw result hash
`sha256:f8a2cd25916290ae02e46b484519cc01dedbe50097326085524a88bb9b324f83`, journal file hash
`sha256:52626ba6d7e61bc293ce327f4bf190e3b4118b20a2efe4d9de09d8186ce6afdd`, final event hash
`sha256:f5537479c3c1e8c150f9cbfec5238d99c882eff537006773af8d9ddf9f78c254`와 portable report
`reports/live-pilot/generic-baseline-readiness-v2v5-20260803-r3.json`/
`sha256:2a8f650e73e01aed9d629290627999232ec6aebd1769d2179bc22f084ddbede2`가 measured boundary다.
D-082 seal 자체는 provider call/model cost 0/$0이다.

Gate pass는 exact workflow readiness calibration일 뿐 comparison budget freeze, no-memory baseline, memory
admission 또는 core를 열지 않는다. Theoretical 96-run reserve `$1,047.60`과 `$150` cap의 충돌은 별도
사전 decision이 필요하다. D-075/D-077/D-079/D-080 evidence는 immutable하다. D-082 final
documentation-seal verification은 repository-wide 1,214 collected 중 1,207 passed/7
environment-dependent skipped와 focused D-082 8/8을 통과했다.

### D-083 offline condition-neutral comparison-budget freeze protocol

D-083은 D-081 r3의 public process evidence만 읽어 per-run policy를 model/tool call `null`/`null`,
total token 1,600,000, wall 1,800초, output 25,000, SDK transport retry 0으로 동결한다. Pyfakefs
observed-prefix minimum 1,303,223에 20%를 더한 1,563,867.6을 100,000 단위로 올림한 값이다.
Hidden acceptance와 task success는 derivation에서 사용하지 않는다. D-080 historical minimum
1,815,619는 이 exact D-081 r3 scope 밖이며 frozen ceiling은 completion을 보장하지 않는다.

이 protocol은 네 future memory condition에 동일한 per-run resource policy를 적용하기 위한 decision일 뿐
실행 protocol은 아니다. D-081/D-082 row는 calibration-only로 denominator에서 계속 제외한다. Runtime,
manifest와 qualification support가 다음 gate에서 구현·검증되기 전에는 template, preflight와 report가
live authority를 만들 수 없다. `analysis_ready`, live execution, no-memory baseline, memory admission과 core는
모두 false/closed다.

Worst-rate reserve는 `$7.3125`/run, `$87.75`/12 run, `$131.625`/18 run과 `$702`/96 run이다.
기존 `$20` 12-run cap과 `$150` project cap을 유지하므로 campaign scale과 비용 승인은 unresolved다.
Append-only evidence path는
`reports/live-pilot/artifacts/d083-condition-neutral-comparison-budget-freeze.json`, SHA는
`sha256:e01c5f0107592e1c29c1ec8264f32bf05c979a718c353c37acb0d87fafd2cb88`다. D-083 protocol
implementation은 provider call 0, model cost `$0`이고 historical D-081/D-082 artifact를 변경하지 않는다.
Final verification은 1,238 collected 중 1,231 passed/7 environment-dependent skipped다.

### D-084 offline comparison runtime qualification protocol

D-084의 검증 질문은 “동결된 동일 budget이 source YAML에만 적혀 있는가?”가 아니라 “그 exact tuple이
plan, manifest, durable start evidence와 qualifier가 보는 동일한 identity인가?”다. Provider call 없이 다음
순서로 검증한다.

1. Exact dev no-memory와 four-condition core suite에서
   `condition-neutral-comparison-runtime-contract-v1`을 만들고 execution hash에 포함한다.
2. Start 직전 `RunManifest`에서 contract를 다시 구성해 approved plan과 비교한다. Purpose, condition order,
   model/mode/retry/output, budget, memory allowance, prompt/tool hash, V2/V5, D-083 SHA 또는 harness commit
   drift를 거부한다.
3. Runner는 `condition-neutral-comparison-runtime-evidence-v1` bytes를 content-addressed artifact로 저장하고
   `RunStarted` full descriptor를 남긴다. Fresh start와 resume 모두 descriptor·bytes·expected document를
   검증한다.
4. Budget diagnostic은 exact registered profile에서만 nullable call counts를 받아들이고 partial null이나
   arbitrary null profile을 거부한다.
5. No-memory trace qualification은 `approved_execution_plan`, `comparison_runtime_contract`,
   `disabled_call_guard_contract`, `pricing_start_freshness`와 `no_memory_boundary`를 요구한다. Runtime CAS,
   budget, call-guard policy 또는 plan tamper는 qualification을 닫아야 한다.

Core의 네 memory condition은 동일 plan/manifest/runtime tuple을 구성할 수 있는지만 offline에서 확인한다.
Raw trace, structured와 selective structured condition은 frozen memory index, leakage scan과 condition별
terminal evidence가 필요하다. Index identity가 plan/hash와 per-run evidence에 결속되기 전까지 preflight는
`CORE_MEMORY_RUNTIME_BINDING_PENDING`이고 paid-call boundary도 core를 거부하므로 D-084에서 전체
trace-qualified 또는 campaign-ready로 판정하지 않는다.

이 protocol의 artifact는
`reports/live-pilot/artifacts/d084-condition-neutral-comparison-runtime-gate.json`이다. Gate가 통과해도
provider execution, no-memory baseline, denominator, memory admission과 core는 열리지 않는다. 별도 clean
preflight가 만든 exact execution hash, fresh pricing, cost-cap 해결과 명시적 사용자 승인이 필요하다.
Final verification은 focused D-084 68/68과 repository-wide 1,304 collected 중 1,297 passed/7
environment-dependent skipped다. Artifact SHA는
`sha256:e7fb7b7e7e9dad3e6b31fb781f09151b940bf226bdd5876e5e75e472ff24b701`이다.

### D-085 exact comparison-pilot source and preflight protocol

D-085는 exact suite `dev-validation-condition-neutral-v2v5-pilot-20260803-r1`로 frozen memory index보다
먼저 no-memory collection path의 pilot을 닫는다. 다음 순서를 고정한다.

1. Frozen Babel development-validation task 한 개와 D-083/D-084 exact tuple을 source suite로 고정한다.
2. Suite, manifest, runtime CAS, fresh-start/resume, paid-boundary와 qualifier selector의 near-match drift를
   offline test로 거부한다.
3. Process readiness는 1/1 terminal·trace-qualified·official evaluator, exact disabled-call-guard pass와
   infrastructure/qualification/diagnostic/budget-terminal/terminal-loop 0으로 판정하고 hidden success/SCRR는
   사용하지 않는다.
4. Source gate를 commit한 뒤 clean host에서 Docker image digest, SDK, Git commit과 72시간 이내 official
   pricing을 포함한 no-call preflight를 수행한다.
5. Preflight hash는 사용자 승인 전까지 candidate일 뿐이다. Exact hash와 최대 `$8`의 별도 승인이 있을 때만
   한 번 실행한다.

Standard `gpt-5.4-mini` rate는 [OpenAI API pricing](https://developers.openai.com/api/docs/pricing), current
snapshot은 [GPT-5.4 mini model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini)에서 확인한다.
Worst-rate authorization reserve는 `(1,600,000 + 25,000) * $4.50/M = $7.3125`이고 source cap은 `$8`이다.
이는 invoice prediction이나 free-tier 적용 주장이 아니다.

Artifact `reports/live-pilot/artifacts/d085-condition-neutral-comparison-pilot-source-gate.json`은 source/offline
gate만 기록한다. Clean preflight와 live result는 source commit 뒤 별도 evidence이며, pilot이 qualified되기
전에는 12-run no-memory cap decision, review/index freeze와 core binding을 진행하지 않는다.

Pilot source와 future campaign source는 별도 clean commit으로 봉인한다. Exact
`dev-no-memory-v5-20260730-r1` consumer는 raw commit equality가 아니라 D-083/D-084 exact semantic tuple,
qualification/source/approved plan CAS와 네 필수 qualification check를 재검증하며 task success는 사용하지
않는다. Persisted qualification은 durable state에서 read-only 재계산한 값과 exact 일치해야 한다.
`condition-neutral-comparison-pilot-admission-v1` canonical hash는 future campaign execution
plan/hash에 결속되고 start/resume/post-run에서 재검증된다. 이 offline consumer가 있어도 qualified pilot,
`$88` cap decision, 새 clean preflight/hash와 별도 승인이 없으면 12-run paid execution은 fail closed한다.
Final offline verification은 focused 153/153, repository-wide 1,392 collected 중 1,385 passed/7 skipped다.
Artifact SHA는 `sha256:8b60cb2e62a6259db29527a600712e95b36390a1c07da9fb66e6f1d7d16f51d2`이다.

### D-086 measured-result sealing protocol

1. Exact D-085 raw result, four-event journal, plan, manifest, receipt, qualification, state trace와 submitted diff의
   byte/hash identity를 read-only로 대조한다.
2. Persisted qualification을 durable state에서 `persist=false`로 재계산해 canonical exact equality와 28/28,
   네 필수 process check를 확인한다.
3. Original readiness gate pass와 hidden/regression/scope/safety pass를 그대로 기록한다. Task success는
   readiness predicate에 사후 추가하지 않는다.
4. Original `budget_pressure` error는 수정하지 않는다. Exact D-085 ID/purpose/runtime에만 열린 selector로
   diagnostic을 재산출하고 token/wall headroom 1,526,799/1,749,231ms, binding `none`을 append-only correction에
   기록한다.
5. Provider/private/evaluator payload를 제외한 portable seal과 raw-local artifact hash index를 만들고 leak scan,
   journal chain, result/qualification binding과 correction identity를 검증한다.
6. Experiment ID를 hard-consumed로 고정해 raw local evidence가 없어도 재실행을 provider 전에 거부한다.

Measured usage는 69,701 input + 3,500 output = 73,201 token, 8 model/9 tool calls, 50,769ms와 공식 고정
rate 계산 `$0.06802575`다. 이는 invoice/free-tier 적용액이 아니다. Raw result/journal/final-event/qualification
hash는 각각 `sha256:e0c3c4c67adc8c157a5030c9a93e3fd106d6b7a12f596253ddf10582fe74b80a`,
`sha256:4c114059fad069526d95786c392b7ea36724443b7231b4426bb097ee0c2199c8`,
`sha256:93853c6367459bcae004789a9a2710c6be518078b21041ece0b160d9843e5a8b`와
`sha256:11bda7b2f31bae453f21c4718fdcb4563a74e173e621fd8035f1ab8aa64f1293`다.

Portable/correction paths는
`reports/live-pilot/dev-validation-condition-neutral-v2v5-pilot-20260803-r1.json`
(`sha256:520ae8408c4e090a2c66a0ed3b2c5c29738762eec1b4f7d87b9452e551635464`)와
`reports/live-pilot/artifacts/d086-condition-neutral-comparison-pilot-budget-pressure-correction.json`
(`sha256:bd42c50b7da2400eea8e340358e92ff2605a9fde8d866d3fdff1c9695b95aeb4`)이고 final verification은 `focused 64/64; repository-wide 1,416 collected, 1,409 passed/7 skipped; Ruff/compileall/JSON/git-diff checks passed; seal provider calls/model cost 0/$0`이다. Passed pilot은
12-run 실행 승인이 아니다. D-086 시점의 다음 protocol 후보는 `$20 → $88` cap decision이었지만,
D-087의 `$25` accrued-spend protocol이 이 forward choice를 supersede한다.

### D-087 no-memory campaign cost protocol

새 12-run no-memory source는 performance 결과가 아니라 collection authority의 비용 경계다. Per-run resource는
모든 future memory condition과 비교 가능한 D-083/D-084 tuple을 유지한다. Campaign cap `$25`는 D-081 r3의
public process usage에서 사전 선택했고 hidden task outcome을 사용하지 않았다.

다음 run admission은 `accrued_list_price_cost + full_next_run_reserve <= hard_cap`이다. Terminal outcome이
task failure나 agent failure여도 발생한 usage는 누적한다. Usage가 없거나 invalid하면 reserve를 held 상태로
남기고 fail closed한다. Cost stop으로 시작하지 못한 row가 하나라도 있으면 12-run completion/readiness gate는
false이며 headline baseline, paired comparison과 memory admission 입력으로 사용할 수 없다.

각 admitted row는 journal의 `RunCostReserved`가 fsync된 뒤 exact one-use paid-boundary capability를 발급받고,
StateStore에서 atomic consume된 뒤에만 provider를 호출한다. 다음 row admission 전에 이전 row의 persisted
qualification, source evidence와 result bytes/hash를 다시 읽고 provider token counters를 fixed nano-USD 가격으로
재산출해 journal settlement와 exact 비교한다. 이 replay가 실패하거나 SQLite consumed set과 journal이 다르면
campaign을 fail closed한다. Live resume은 request-level billing ambiguity 때문에 지원하지 않는다.

Source gate 뒤의 live sequence는 반드시 clean commit -> fresh no-call preflight -> candidate execution hash ->
exact hash와 max `$25` 별도 승인 -> one campaign invocation -> immutable result seal 순서다. Source artifact와
preflight는 SCRR, success rate 또는 memory effect evidence가 아니다.

### D-088 D-087 measured-result protocol

승인된 D-087 invocation은 exact hash로 한 번만 실행하고 즉시 immutable evidence로 닫는다. Post-run 절차는
provider를 다시 호출하지 않고 다음을 수행한다.

1. Raw result, plan과 50-event journal의 byte/canonical hash를 검증한다.
2. 12개 qualification을 durable state에서 `persist=False`로 재계산해 persisted payload와 exact 비교한다.
3. 340개 `ModelCalled`의 completed status, exact input/total token telemetry, truncation disabled,
   `store=false`와 previous-response dependency 0을 검증한다. 차단된 generation의 local input pre-count 한 건을
   포함해 input-token count call은 341회다.
4. Token usage를 fixed nano-USD rate로 재가격하고 journal 12 reserve/12 settle 및 SQLite 12 one-use
   consumption과 대조한다.
5. Private/hidden/reference/submitted-patch/request-response payload를 제외한 portable report를 content-address한다.
6. Experiment ID를 hard-consumed로 만들고 original gate를 그대로 보존한다.

Readiness predicate에는 task success가 없지만 12/12 official evaluator completion과 budget-terminal 0이 있다.
실측은 12/12 terminal·qualified, 11/12 evaluator와 budget-terminal 1이므로 false다. 1 resolved, 10 hidden task
failure와 1 agent budget failure는 진단으로 보존하되 hidden failure로 prompt/tool/task를 튜닝하지 않는다.
새 실행은 새 budget-only condition-neutral source, clean preflight, execution hash와 별도 사용자 승인 없이는
허용되지 않는다.

### D-089 AnyIO budget-only readiness protocol

1. D-088 portable seal에서 evaluator 미도달 budget-terminal row가 정확히 AnyIO repetition 2 하나인지 확인한다.
2. D-087 suite/result/source artifact SHA를 다시 검증하고 수정하지 않는다.
3. 새 exact one-row source에서 per-run runtime tuple 중 total-token ceiling만 1.6M -> 2.0M인지 검증한다.
4. Clean commit에서 no-call preflight를 실행해 fresh pricing, Docker, SDK, task/package와 execution hash를 확인한다.
5. Candidate hash와 최대 `$10`에 대한 별도 승인 전에는 provider를 호출하지 않는다.
6. 실행 후 terminal·qualified·official evaluator와 budget/infrastructure/qualification/diagnostic/loop confound를
   판정한다. Hidden success는 결과로 보존하지만 readiness predicate에는 넣지 않는다.
7. 결과를 새 immutable seal로 닫기 전에는 baseline, memory admission/index 또는 core를 열지 않는다.

2M은 same-prefix minimum보다 382,712 token 높지만 stochastic completion guarantee가 아니다. Probe가 다시
budget에 걸리면 그대로 failed calibration으로 봉인하고 자동 budget escalation이나 재실행을 하지 않는다.

### D-090 D-089 measured-result interpretation

D-089은 1회만 실행하고 original gate를 그대로 판정한다. Gate false의 직접 원인은 qualified trace나 identity
실패가 아니라 evaluator 전 `exact_request_budget_exceeded`다. Observed prefix에서 next call 최소치는
2,014,913 token이지만 이는 한 generation admission counterfactual이지 completion budget 추천값이 아니다.
Token-tail projection이 관측한 exploration-open 최대치는 2,179,715지만 이것도 stochastic completion guarantee가
아니다. 따라서 이 결과로 budget을 자동 증액하거나 재실행하지 않는다.

Task success, hidden acceptance와 verifier outcome은 관측되지 않았으므로 agent correctness나 task 난이도에 대한
값으로 코딩하지 않는다. Reported facts는 readiness false, total-token process failure, exact usage/cost,
qualification 27/27과 no-evaluator boundary다. No-memory baseline과 memory comparison denominator는 계속 닫힌다.

### D-091 non-convergence classification rule

Budget terminal을 곧바로 budget root cause로 분류하지 않는다. Public trace가 qualified이고 retry-source failure가
없더라도 다음 조건을 별도로 본다: visible check pass, last `PatchApplied` event 이후 model/tool/token tail, rejected
patch, loop/replay, finalization tool과 evaluator arrival. D-089은 마지막 `PatchApplied` event 뒤 68 model/96 tool
call과 1,772,530 token 동안 추가 `PatchApplied` event가 0이었고 visible check 0/6, finish/evaluator 0이다. 따라서
deterministic terminal trigger는 budget guard지만 bounded process classification은
`qualified-process-nonconvergence-ending-in-budget-terminal`이다.

D-087 r2와 D-089은 budget 외에 fresh repetition, schedule, execution identity와 harness commit이 달라 causal
paired comparison이 아니다. 같은 task D-087 r1이 534,853 token에서 evaluator에 도달한 사실은 process variance
control로만 사용하며 task/hidden outcome은 사용하지 않는다. 2.4M/3M counterfactual은 관측된 prefix에서 다음
request를 admit한다는 산술일 뿐, seq 546의 exploration block 이후 path나 completion을 식별하지 못한다.

### D-092 policy admission and denominator outcome rule

Candidate trigger 뒤 public progress marker가 하나라도 있으면 task correctness와 무관하게 `false_stop=true`다.
`false_stop=false`는 해당 observed trace에서 later progress를 보지 못했다는 뜻일 뿐 future safety proof가 아니다.
Trigger 이후 model token/call, tool call과 wall time은 observed suffix이며 실제 guard를 실행해 얻은 causal saving이
아니다.

D-092의 generic candidate는 네 gate를 모두 통과하지 못했으므로 runtime을 바꾸지 않는다. Terminal이며
trace-qualified인 budget stop은 향후 condition-neutral denominator에서 원래 task/repetition identity를 유지한
`agent_failure` row로 남기고, 삭제·재실행·대체하지 않는 outcome rule을 선택했다. 다만 D-092는 이 rule을 four
memory condition consumer에 아직 결속하지 않았으므로 baseline denominator admission은 계속 닫혀 있다.

### D-093 readiness-stage correction

D-092의 마지막 outcome rule은 comparison 분석을 readiness calibration에 너무 일찍 적용했다. 현재 단계의 질문은
“이 workflow가 generous finite safety ceiling 아래 submission과 official evaluator까지 끝까지 도달하는가”다.
따라서 evaluator 전에 budget ceiling으로 끝난 qualified run은 task failure나 usable performance row가 아니라
`readiness_inconclusive` / `budget_confounded`다. Raw runtime outcome은 감사 가능성을 위해 그대로 보존한다.

Readiness pass는 각 row가 started/terminal/trace-qualified이고 accepted submission과 official evaluator receipt를
남기며 exact-input telemetry, completed response와 truncation-disabled evidence를 갖는 경우에만 성립한다. 동시에
infrastructure, qualification, diagnostic, budget terminal, terminal loop와 model/tool call block이 0이어야 한다.
Hidden acceptance와 SCRR은 관측·보고하지만 readiness predicate에는 넣지 않는다. 이 구분은 agent가 hidden case를
완벽히 해결할 때까지 readiness를 반복 튜닝하는 것을 막는다.

Historical exact run을 재실행하지 않는다. 별도 successor panel은 새 experiment ID와 frozen source/preflight/hash/
cost approval을 가져야 하며, 그 결과도 workflow readiness만 판정한다. Comparison row를 failure로 셀지는 네 condition
모두에 동일한 resource policy를 명시적으로 freeze할 때 별도로 결정한다.

### D-094 high-headroom readiness source and later execution protocol

Source gate에서는 exact YAML, frozen dataset/task identity, D-093/D-084 predecessor bytes, runtime schema와 fresh
official pricing만 검증한다. Ordered panel은 AnyIO, pyfakefs, HF Hub 각 1회이며 model/prompt/tool/context와
memory condition은 동일하고 resource ceiling만 exact `null/null/3M/3,600s`, output 25k로 고정한다. Standard
rate timestamp는 2026-08-04T14:47:00Z이고 conservative authorization reserve는 `$13.6125`/run,
`$40.8375`/suite, cap은 `$41`이다.

Source commit이 clean해진 다음 별도 no-call preflight가 Docker, evaluator, dataset, SDK, pricing과 commit을 묶어
one-use candidate execution hash를 만든다. 사용자가 그 exact hash에 max-`$41`을 별도로 승인하기 전에는 provider를
호출하지 않는다. D-094 source 단계 자체는 preflight, hash, 승인, provider/evaluator call 또는 run/result를
만들지 않는다.

실행 이후 readiness는 세 row 모두 terminal·qualified·accepted submission·official evaluator에 도달하고 durable
qualification이 read-only recomputation과 정확히 같을 때만 pass다. Exact-input telemetry completeness, completed
responses, truncation disabled와 모든 명시된 process confound 0도 요구한다. Hidden acceptance, task success와
SCRR은 결과로 보고하되 readiness 판정에는 넣지 않는다. Gate 성공도 no-memory baseline이나 memory/core
collection을 자동 승인하지 않는다.

### D-095 D-094 measured-result interpretation

Approved D-094 invocation은 exact hash로 한 번만 실행하고 original result와
`generic-high-headroom-readiness-gate-v1`을 그대로 판정한다. 세 row 모두 terminal·qualified·accepted
submission·official evaluator에 도달했고 persisted qualification 재계산, 63/63 completed response와 exact
input/total-token match, truncation disabled, `store=false`, previous-response dependency 0을 확인했다. Budget과
다른 process confound가 없어 workflow-readiness disposition은 `passed`다.

Correctness는 별도 축이다. AnyIO, pyfakefs, HF Hub 모두 hidden acceptance가 실패했으므로 outcome은 세 건의
`task_failure`, SCRR은 0/3이다. Regression/scope/safety는 3/3 통과했다. 이 0/3을 숨기지 않되 readiness를
hidden perfection으로 재정의하거나 task-specific prompt/tool tuning과 자동 rerun의 근거로 사용하지 않는다.

사용량 기반 `$0.9374115`는 frozen standard rate로 계산한 reproducible list-price accounting이며 invoice나
free-tier 적용액이 아니다. Post-run seal은 provider/evaluator를 다시 호출하지 않는다. 이 small selected panel은
calibration-only이므로 no-memory 성능 baseline, success-rate estimate, comparison denominator/resource freeze,
memory review/admission/index와 core는 별도 condition-neutral admission decision 전까지 닫힌다.

### D-096 prospective comparison and no-memory admission protocol

Policy selection에는 D-093의 public resource derivation과 D-095의 readiness/process-confound 결과만 사용한다.
D-095의 0/3 hidden acceptance나 task success는 선택 입력이 아니다. 3M/3,600초 policy는 budget을 비교 변수로
삼지 않기 위한 동일한 finite allocation이며 일반적인 task completion 보장이 아니다. 네 memory condition은 향후
같은 model, prompt, tool, context, retry, output, memory allowance와 resource ceiling을 사용해야 한다. Pricing은
D-094 source artifact의 exact-bound pricing block에서 직접 읽고 rate와 worst-reserve formula를 재계산한다.

No-memory baseline source는 frozen memory-development 여섯 task를 각 2회, seed `20260723`으로 구성한 exact
12-row successor여야 한다. D-087 historical result나 D-095 calibration row를 가져와 채우거나 교체하지 않는다.
각 task `public.yaml` bytes/file SHA를 frozen manifest row의 `public_spec_hash`와 먼저 대조하고 하나라도 drift하면
source admission을 중단한다. Task success/hidden pass는 source admission 요건이 아니지만 campaign completion은
exact 12 terminal·qualified·cost-settled row, process error와 cost censoring 0 및 durable qualification/telemetry/
runtime-policy reconciliation을 요구한다. Issued response status는 전부 `completed`여야 한다.

각 terminal row는 다음 branch 중 exact-one이어야 한다.

1. Official evaluator branch: accepted submission, completed official receipt, `resolved|task_failure`, budget terminal 0.
2. Budget branch: canonical pre-call `ModelGenerationBlocked` with `total_tokens|wall_clock`, runtime actor와 expected
   CAS, provider-after-terminal 0, `agent_failure`, accepted submission/evaluator receipt 0.

따라서 frozen-policy budget terminal은 denominator에 `agent_failure`로 남고 자동 재실행하지 않으며 memory
candidate가 될 수 없다. Memory candidate는 official-evaluator `task_failure`, qualified trace와 leakage pass 뒤에도
자동 admission하지 않고 별도 maintainer/agent review를 거친다.

D-096은 source-authoring permission만 연다. Historical D-083/D-084 v1을 수정하지 않고 새 runtime v2 binding과
3M suite를 별도 구현해야 한다. 또한 12-run worst-case `$163.35`가 project cap `$150`을 넘으므로
`NO_MEMORY_AUTHORIZATION_CAP_PENDING`을 해소하는 non-censoring cost policy가 필요하다. 이 두 조건과 fresh
pricing, clean no-call preflight, 새 execution hash 및 별도 user approval 전에는 provider/evaluator를 호출하지
않는다. No-memory result, denominator, memory review/index와 core analysis는 계속 닫힌다.

### D-097 exact no-memory runtime-v2 source and future execution protocol

D-097은 source gate, clean preflight, paid invocation을 하나의 단계로 합치지 않는다.

1. **Offline source gate:** Exact suite
   `dev-no-memory-condition-neutral-3000k-20260805-r1`, D-096 policy/admission CAS, six public/environment
   identities, runtime contract/evidence v2와 full-schedule cost policy를 고정한다. Suite file identity는
   2,741 bytes, `sha256:7b3c217388e86a2760694e98031b7ac974c8c450075e3433ee977e35b344abb0`다. Provider/evaluator call,
   candidate execution hash와 run/result는 0이다.
2. **Future clean no-call preflight:** Source change를 clean commit으로 만든 뒤 exact dataset/task/environment,
   Docker/evaluator digest, SDK, official pricing freshness와 harness commit을 재검증한다. 이 단계가 execution
   payload와 candidate hash를 만들지만 provider/evaluator는 호출하지 않는다. D-096 source-identity hash
   `sha256:e399114a6ea516821a30104a612f7222c0caf3f88def7b5d7472d15f7cc4c27b`와 runner-expanded
   schedule hash `sha256:dff4f38db99bcbc878e917a6c76e10a6c244701d2a8eb5ea4b43daf427a305ba`는 별도
   field로 검증한다.
3. **Separate approval and one invocation:** 사용자가 candidate hash, maximum `$164`와 historical project cap
   `$150`에 대한 campaign-scoped exception을 명시적으로 승인한 invocation만 plan을 persist하고 paid boundary를
   넘을 수 있다. Approval flag/hash는 source YAML이나 source artifact에 미리 넣지 않는다.

Source suite는 Loguru, AnyIO, tox, HF Hub, PDM, pyfakefs를 exact input order로 `no_memory` 각 2회 사용한다.
Seed `20260723` shuffle 뒤 row order는 pyfakefs r1/r2, AnyIO r1, HF Hub r1, PDM r1, HF Hub r2,
AnyIO r2, Loguru r1/r2, tox r2/r1, PDM r2다. Preflight는 12개 unique row ID와 task/repetition/order/dataset
role을 execution hash에 포함한다. Missing, duplicate, replacement와 reordered source는 fail closed한다.

Runtime verification은 plan/manifest tuple 일치에서 끝나지 않는다. Runner는 provider boundary 전에 D-096
artifact와 cost-control hash를 다시 읽고, `RunStarted`에 runtime-evidence-v2 CAS를 단 한 번 기록한다. Resume는
같은 bytes를 재구성하지 못하면 model call 전에 실패한다. Terminal qualification은 persisted qualification을
다시 load하고 `persist=false` read-only recomputation과 hash까지 exact 비교한다. Model/tool call count `null`은
0이 아니라 observability-only이며 token, wall, exact-request, cost, loop, constrained-tool, Docker/network와
evaluator guard는 유지한다.

Exact runtime schema 이름은 `condition-neutral-comparison-runtime-contract-v2`와
`condition-neutral-comparison-runtime-evidence-v2`다. Historical runtime-v1 schema로 fallback하거나 두 schema를
서로 대신하지 않는다.

Campaign cost는 첫 provider call 전에 하나의 fsync된 `FullScheduleCostReserved` event로 exact 12-row schedule,
row별 `$13.6125` allocation과 `$163.35` full reserve를 한 번에 결속해야 한다. Hard cap은 `$164`다. Initial
reservation이 실패하면 paid row를 하나도 시작하지 않는다. Runner는 같은 plan/CAS/journal을 각 row 전에 다시
검증하고 terminal row마다 durable usage의 deterministic settlement를 기록한다. 앞 row의 낮은 settlement가 뒤
row allocation을 바꾸지 못하고 unknown request outcome은 해당 row의 full reserve를 유지한다. 이는 per-row
atomic SQLite capability가 아니다. Live resume은 disabled다. D-097 cost journal은 duplicate paid-call prevention을
주장하지 않으며, 기존 one-use execution hash가 authorization을 단일 sequential campaign invocation으로 제한할
뿐이다. 이 boundary는 task completion guarantee나 expected
invoice/free-tier 계산이 아니다.

12개 settlement 뒤 `CampaignCompleted`가 기록되면 post-run qualifier는 final result bytes/hash, execution/plan/
cost-control binding과 embedded cost qualification을 다시 읽는다. Foreign binding이나 duplicate terminal event는
hash chain을 다시 만든 경우에도 fail closed한다. 이 검사는 sealed result integrity이고 paid call idempotency를
소급 만들어 내지 않는다.

Post-run admission output schema는 `condition-neutral-no-memory-baseline-admission-gate-v2`이며 task success를
요구하지 않는다. 각 row는 다음 중 exact-one이어야 한다.

1. Official branch: terminal·qualified, accepted submission, completed official evaluator receipt, outcome
   `resolved|task_failure`, persisted/recomputed qualification match.
2. Budget branch: terminal·qualified, canonical pre-provider total-token 또는 wall-clock block, `agent_failure`,
   no provider-after, no accepted submission, no evaluator receipt.

전체 12 row는 cost-settled이고 issued response는 모두 `completed`, exact token telemetry, truncation disabled와
`store=false`여야 한다. Infrastructure/qualification/diagnostic error, cost `not_started`, model/tool-call block,
unknown/mixed terminal은 admission을 닫는다. Qualified budget terminal은 denominator `agent_failure`지만 rerun이나
memory candidate가 아니다. Future 12-row denominator gate가 통과하면 campaign-level
`memory_review_eligible=true`가 된다. Review candidate pool은 official task failure로만 제한된다. 이 값은
automatic rule admission이 아니고, 별도 review/dedup/leak gate가 통과하기 전
`memory_admission_unlocked=false`다.

Source-focused suite는 builder/identity/cost/authority contract만 검증한다. Artifact semantic body SHA는
`sha256:05d952065136a45914e2fb3c44edcbb553732c9f33484c5412b9135062c6481b`, 21,029-byte file SHA는
`sha256:21ed073ad1fbe1985e7a46cabebbfdc836baa303c4434e0777152c1d2d88a777`다. Runtime executable test와
qualification/final-seal test를 포함한 D-097 focused 65/65와 D-084~D-097 관련 354/354가 통과했다. Full repository
run은 1,728 collected, 1,720 passed/7 skipped/1 order-dependent D-092 WAL/SHM failure였으며 exact isolated retest는
1/1 pass다. 이를 monolithic 1,721/7로 보고하지 않는다. Clean no-call preflight,
hash와 사용자 승인이 끝나기 전 no-memory result, denominator, memory review/admission/index, core와 analysis는
모두 닫혀 있다. Canonical blocker는 `NO_MEMORY_CLEAN_PREFLIGHT_AND_164_USD_APPROVAL_PENDING`이다.

### D-098 measured no-memory baseline result and review-eligibility protocol

승인된 execution hash `sha256:1a5aaccc4f95f71d285e0e0a9c8ccb27f82e235fbff465ef30f095401fde25f4`의
exact campaign은 12/12 terminal·qualified·cost-settled로 끝났고 final
`condition-neutral-no-memory-baseline-admission-gate-v2`가 통과했다. 11개 row는 accepted submission과 completed
official evaluator receipt를 가진다. AnyIO repetition 1 한 row는 2,964,853 token 뒤 다음 exact request에
26,231 token이 부족해 provider call 전에 차단된 canonical budget terminal이다. Issued 613 response는 모두
completed이고 truncation disabled, `store=false`, previous-response dependency 0이다.

Primary no-memory denominator outcome은 resolved 2, official task failure 9, agent budget failure 1이며 exact
development SCRR는 2/12다. Evaluated 11개 중 hidden acceptance는 2/11이고 regression/scope/safety는 11/11
통과했다. 이 값은 development baseline의 기술 통계이며 held-out 성능, memory 효과 또는 일반 agent 성능으로
해석하지 않는다. Task-first 결과도 PDM 2/2, 다른 다섯 task 0/2로 별도 기록한다.

Memory review queue는 9개 official task failure만 포함한다. Generic hidden failure label은 oracle outcome으로만
사용하고 rule causal claim은 public task, agent-visible events/artifact CAS, visible checks와 submitted diff로만
작성한다. Success 2개와 budget terminal은 source가 아니다. Review queue open은 admission이 아니며
review·semantic dedup·leak scan, group-level decision과 proposal-consuming builder 전에는 index를 build/freeze하지
않는다. Core나 다른 memory condition 실행도 계속 닫혀 있다.

D-098 portable seal은 raw result/journal/qualification을 수정하지 않고 exact experiment ID를 hard-consumed한다.
Seal 작성 과정은 provider/evaluator를 호출하지 않았고 추가 model cost는 `$0`이다. Usage-derived standard
list-price `$11.838408`은 invoice/free-tier treatment 주장이 아니다.

### D-099 public-evidence review and deduplication protocol

D-099 reviewer가 해석할 수 있는 근거는 public task, agent-visible search/read result, submitted task-failure patch,
registered visible-check summary, diff/review/submission lifecycle metadata와 generic official task-failure outcome뿐이다.
Qualification hash, source-evidence hash와 failure-record file hash는 source eligibility를 결속하는 opaque identity이며
원인 분석 내용으로 열지 않는다. Private spec, acceptance check ID/assertion/output, evaluator evidence body, reference
patch, provider request/response body와 credential은 금지한다.

Semantic grouping은 submitted code의 public failure pattern에 대한 causal hypothesis다. Generic task-failure label만으로
exact acceptance 원인을 확정하지 않는다. 또한 target agent architecture defect, harness defect 또는 memory 효과를
뜻하지 않는다. Candidate는 human review 대상으로 제안할 만큼 일반화 가능한 pattern이라는 뜻이고 admission이 아니다.
Hold는 public patch risk가 없다는 뜻이 아니라, reusable rule의 precondition와 do-not-apply boundary가 아직 충분히
확정되지 않았다는 뜻이다.

Admission 전에 다음 exact gate를 만족해야 한다.

- D-098 candidate 9개와 resolved/budget exclusion 3개의 12-row partition
- 9 source를 정확히 한 group에만 배치하는 5-group partition
- candidate proposed-rule / hold unresolved-reason payload XOR
- portable patch SHA/bytes와 selected event type/event hash/CAS binding
- proposal text와 patch artifact의 분리된 leakage scan
- human admission pending, admitted rule 0, review history/index/core authority false

D-099은 이 gate를 검증하되 human decision을 기록하지 않는다. 다음 단계는 group-level append-only decision과
group-aware proposal consumer다. Existing per-failure builder는 dedup group을 모르므로 D-099 source를 개별 승인해
우회하지 않는다.

### D-100 group-decision and template-preview protocol

D-100 mechanism test는 actual reviewer choice를 만들지 않고 synthetic journal만 사용한다. Production decision은
사용자가 exact proposal/group/fingerprint와 candidate rule hash를 확인한 뒤 `approve|reject|continue_hold` 중
하나를 명시해야 한다. Generic implementation authorization, agent recommendation 또는 candidate disposition을 human
approval로 변환하지 않는다.

Decision protocol은 다음을 요구한다.

- caller-provided unique action ID와 action input hash에 포함되는 explicit expected journal tail
- exact D-099 proposal descriptor, group fingerprint와 approval rule hash
- candidate만 approve; hold approve 거부
- global contiguous chain과 same-group latest-decision supersedes
- duplicate retry idempotency와 conflicting reuse/stale tail rejection
- canonical JSONL append, writer lock, flush/fsync, full reread와 single-snapshot descriptor
- noncanonical/blank/partial-tail/reordered/hash-inconsistent/unknown-field/leaking row fail closed
- optional external expected head/count match; whole-row suffix deletion과 fully rehashed rewrite는 future seal anchor가 담당

Projection protocol은 five-group effective decision coverage가 complete일 때만 실행한다. Approve는 group당 하나의
template, reject와 continue-hold는 zero template다. 두 source가 있는 group도 하나의 entry 후보이며 run/failure
provenance를 중복 없이 보존한다. Template에는 actual `index_version`, embedding 또는 frozen state가 없고 source run
count를 validation count로 사용하지 않는다. 따라서 preview pass는 admission/index/core 또는 memory 개선을 뜻하지
않는다.

Reviewer kind는 `human|maintainer_assisted|synthetic` self-attestation이다. Future admission seal은 explicit user
approval receipt, effective head/count와 journal file SHA를 함께 결속해야 하며 standalone journal validator만으로
사람의 identity나 complete-history immutability를 주장하지 않는다.

### D-101 explicit group review and admission protocol

검토자는 checked-in D-101 한글 Markdown을 읽되 그 파일에 선택을 직접 기록하지 않는다. 답변에는 내부 이름,
긴 식별값, hash나 영문 상태명을 옮겨 적지 않고 1번부터 5번까지 각 번호의 한글 선택과 이유만 적는다. 1·2·5번의
선택지는 `기억에 추가`, `사용하지 않음`, `나중에 결정`이고, 아직 일반화 근거가 부족한 3·4번은
`사용하지 않음`, `나중에 결정`만 허용한다. 시스템 기록 단계가 이 답변을 exact 기계 항목에 대응시키며, 원본
machine JSON bytes와 D-099/D-100 의미는 바꾸지 않는다.

다섯 번호의 명시적 답변이 모두 있어야 선택 기록을 준비할 수 있다. 일반적인 `진행해줘`나 문서 구현 요청은
어느 번호의 선택도 아니며, D-101 packet 생성 시점의 사용자 선택과 production decision은 모두 0이었다. 다섯 항목에 답했더라도
`나중에 결정`이 남아 있으면 전체 검토가 끝난 것은 아니다.

Candidate 준비 시점에는 journal head, record count와 file SHA를 외부 승인 문맥에서 함께 고정한다. Candidate
내용 검증만으로 외부 anchor가 진짜 사용자에게서 왔음을 증명하지 않으므로, 다음 receipt 단계에서 candidate
ID/body SHA/file SHA를 다시 명시해 exact snapshot을 승인한다. Seal은 receipt와 live journal bytes까지 검증한다.
이 절차가 통과해도 승인 rule의 효과, negative transfer, held-out SCRR 또는 index readiness는 증명되지 않는다.
Index build/freeze와 core comparison은 별도 gate를 통과해야 한다.

현재 한글 Markdown identity는 12,872 bytes와
`sha256:9fc8e51dc867d66672b7c5334402bafdc27759914df88df09d506a5832d479c5`다. Source gate는 3,807 bytes,
file SHA `sha256:987cded0f469370f3f9c5542c8353f7153429d7b3743df9af003f2f594b3a275`, semantic body SHA
`sha256:26838ab1e8097e47f53e712ce11d0d8a603cd4dd3dff408792f77f7d164fe4f9`다.

### D-102 recorded-decision and candidate approval protocol

사용자는 1·2·5번을 `기억에 추가`, 3·4번을 `나중에 결정`으로 명시적으로 확인했다. 시스템은 이를 proposal
순서대로 `approve, approve, continue_hold, continue_hold, approve`에 대응시켰다. 기술적 이유를 시스템이 기존
public evidence에서 연결했으므로 reviewer kind는 모두 `maintainer_assisted`다. 이 선택을 `human` rationale로
재표현하거나 reviewer identity 인증으로 해석하지 않는다.

기록 단계는 각 append 전에 직전 tail을 CAS로 확인하고, 마지막에는 record count 5, correction count 0, head
`sha256:4192b503768093e2134b7651da4922fcd9d5c2a064e0150a7f523adc952ac469`와 journal file SHA
`sha256:5c46e6b6a49e436794c1b118f96a9d05caa48a4cd4199e9791ec2ec4499327e3`를 검증한다. Candidate
builder에는 이 head, count와 file SHA를 별도 입력으로 다시 제공한다.

생성된 candidate는 approved 3/rejected 0/continued hold 2와 projection-only preview 3개를 담는다. Candidate
ID는 `d101candidate_97c0d2499e2ffab97df6050b84af7c1d455e4af631a3e0fb58d50a084a62ac9d`, body SHA는
`sha256:97c0d2499e2ffab97df6050b84af7c1d455e4af631a3e0fb58d50a084a62ac9d`, file SHA는
`sha256:9620e99961010bc4c942728f1948cb50b3f067025b8d5a02ba579dd3a1b4e457`다. Candidate를
만든 행위는 exact candidate 승인과 다르다.

다음 protocol action은 위 candidate ID/body SHA/file SHA를 사용자에게 함께 제시하고 별도 메시지로 exact
승인을 받는 것이다. 승인 전에는 receipt와 seal을 만들지 않는다. 두 hold가 있으므로 이후 seal이 생기더라도
full group review는 finalized가 아니다. 현 단계에서는 admitted memory/source authoring/index/core/analysis가
모두 닫혀 있고 provider/evaluator 호출이나 model cost도 없다.

### D-103 exact approval and admission-seal protocol

사용자가 candidate ID, body SHA와 file SHA를 별도 메시지에서 정확히 다시 입력하면 그 세 값과 고정 확인 문구를
하나의 approval receipt에 기록한다. Receipt validator는 candidate 전체를 다시 만들고 exact bytes와 hash를
비교한다. 이 기록은 사용자의 입력을 보존하는 self-attestation이며 identity authentication이나 digital
signature 검증으로 보고하지 않는다.

Seal 단계에서는 receipt 검증만으로 끝내지 않는다. D-102 journal의 현재 bytes, record count, head와 file SHA,
candidate와 receipt를 모두 다시 확인한다. 하나라도 달라지면 seal을 만들거나 통과시키지 않는다. 현재 seal은
approved group 세 개의 template와 provenance를 보존하고 hold 두 개를 제외한다.

Seal 통과 후 허용되는 작업은 세 template를 exact memory source로 작성하고 leak scan·schema·provenance를
검증하는 것뿐이다. 다음 항목은 계속 금지한다.

- 보류된 두 그룹을 승인된 것으로 간주
- 검색 index build 또는 freeze
- held-out/core campaign 실행
- memory 성능 개선이나 negative transfer 결론 보고

D-103 portable gate는 receipt/seal과 이전 D-102 gate를 exact hash로 결속하고 위 권한 값을 다시 검사한다.
Focused 7/7, 관련 회귀 497/497, repository-wide 1,823 collected 중 1,816 passed/7 environment-dependent skipped,
failure 0이 현재 executable evidence다.

### D-104 unindexed source materialization protocol

Producer는 D-103 seal의 admitted projected entry 세 개만 읽어 source record 세 개를 만든다. Trace, public patch
또는 failure record를 새로 해석해 rule 문구를 바꾸지 않는다. Template과 provenance의 모든 field 및 template
hash가 seal과 같아야 한다. Hold group은 source로 만들 수 없다.

Portable validator는 다음 순서로 검사한다.

1. D-103 gate와 seal을 exact rebuild해 D-099~D-103 chain을 재검증한다.
2. Admitted order가 pyfakefs, HF Hub, tox 세 그룹이고 hold가 AnyIO, Loguru 두 그룹인지 확인한다.
3. Source directory의 direct file set이 exact 세 개인지 확인하고 link/junction, missing/extra file을 거부한다.
4. 각 strict source schema와 canonical UTF-8 JSON, content-derived source ID/body SHA/file SHA를 확인한다.
5. Template와 provenance를 seal 값과 exact 비교하고 source run/failure의 전역 중복이 없는지 확인한다.
6. Free-text leak scan을 수행하되 검출 본문은 error에 출력하지 않는다.
7. Gate authority가 D-104-created actual MemoryEntry/render/embedding/index와 core authority를 계속 0/false로
   두는지 확인한다.

Inherited D-099 portable validator는 tracked submitted public patch copy를 읽어 integrity/leak scan을 다시 확인한다.
따라서 “patch body를 전혀 읽지 않았다”고 주장하지 않는다. 정확한 경계는 public patch text를 D-104 source에
복사하지 않았고 새 rule 의미를 patch body에서 작성하지 않았다는 것이다. Portable mode에서 raw SQLite/event/
search-read artifact body, private task, hidden test/assertion, reference solution patch, evaluator payload와 provider
request/response body는 읽지 않는다.

D-104 완료만으로 model-facing render, 2,000-token fit, embedding revision, retrieval no-match, index build/freeze나
core를 승인하지 않는다. Focused 30/30과 related 530/530이 통과했다. Repository-wide는 1,853 collected 중
1,845 passed/7 environment-dependent skipped/1 failed이며, 유일한 기존 order-dependent D-093 SQLite WAL/SHM
invariant는 fresh isolated process에서 1/1 통과했다. 이를 D-104 failure나 fix로 합산하지 않는다.

### D-105 renderer and prospective index-authorization protocol

D-105 validator는 provider/evaluator/embedding model을 호출하지 않고 legacy memory store/retrieval API도 호출하지
않는 offline source gate다. 다만 `patchloop.memory` package initialization은 legacy retrieval/store module을 간접
import한다. Exact predecessor validation도 inherited D-099 path에서 public submitted patch bytes를 integrity/leak
scan용으로 읽는다. Module import와 API call을 분리하고, patch bytes를 render에 복사하거나 새 rule 의미 작성에
사용하지 않았는지 별도로 검사한다. 다음 순서로 검사한다.

1. Exact D-104 gate와 source collection/order/hash를 다시 검증한다.
2. Source 세 개에서 whole-entry render를 다시 만들고 checked-in direct file set과 byte-for-byte 비교한다.
3. ASCII 범위, 이미 NFKC인 입력, LF, trailing LF, fixed field/list order와 fixed separator를 확인한다.
4. Model-visible allowlist 밖 provenance/local-path field와 private/hidden/reference/credential/leak-shaped text가 없는지
   확인한다.
5. Render file 세 개의 size/SHA, ordered render-set hash와 canonical joined-bundle size/SHA를 다시 계산한다.
6. Provider token policy가 same-full-request delta, maximum 2,000, no `chars/4` estimate로 고정됐는지 확인한다.
7. Embedding candidate가 exact model ID와 full 40-hex revision, normalization과 no-remote-code 설정에 결속됐는지
   확인한다.
8. Group-aware plan이 D-104 source 세 개만 받고 hold group과 legacy failure별 builder를 거부하는지 확인한다.
9. Authority가 candidate 단계 이상으로 올라가지 않았는지 확인한다. 특히 provider validation, snapshot
   verification, actual authorization, MemoryEntry/embedding/index, retrieval와 core는 0/false여야 한다.

현재 checked-in render 세 개는 1,191/1,164/1,161 bytes이고 render-set SHA는
`sha256:7b72fc94642d996fad5a0b199719c56bfecc8a8fc1bbe42b2060aa18e21d2667`이다. Canonical
joined bundle은 3,528 bytes/SHA
`sha256:572667d431aa75e4fe74bfc030a99f64245b77d9afa1c88e5d531129f708accf`다. Missing, extra,
tampered source/render, nonimmutable embedding revision, changed authority, conflicting retry와 repository 밖 write는
fail closed한다. Focused executable verification은 47/47, related는 550/550다. Repository-wide는 1,900
collected 중 1,892 passed/7 environment-dependent skipped/1 failed다. 유일한 기존 order-dependent D-092 raw
replay SQLite WAL/SHM invariant는 fresh isolated process에서 1/1 통과했으며 D-105 failure나 fix로 합산하지
않는다.

2,000-token policy의 통과 판정은 future provider receipt가 있을 때만 가능하다. Baseline canonical context의
`/selected_memory`는 JSON `null`이고 with-memory context의 같은 위치만 exact whole-entry bundle이어야 한다.
Canonical context deep diff는 그 pointer 하나뿐이어야 하며 context slot을 정규화한 full request 두 개도 같아야
한다. 각 context/request hash와 `responses.input_tokens.count`를 함께 기록하고 `with_memory - baseline`이 0 이상
2,000 이하인지 검사한다. Header, separator와 envelope overhead도 포함한다. D-105 gate의
`provider_exact_budget_validated=false`와 null count를 local estimate로 채우지 않는다.

Embedding revision observation은 upstream commit을 가리키는 외부 관찰이며 서명이나 local snapshot proof가
아니다. Next preflight는 locked dependency install, exact revision snapshot download, snapshot file inventory/hash,
offline reload, expected 384-dimension float32 normalized vector를 executable하게 검증해야 한다. 그 결과와 exact
D-105 gate를 사용자가 별도로 승인하고 group-aware builder가 구현되기 전에는
`memory_index_build_authorized=false`를 유지한다.

D-105는 structured source 세 개의 model-facing rendering만 다룬다. Raw Trace 조건의 trace selection,
redaction/truncation/token receipt와 renderer를 검증하지 않았으므로 네 memory 조건 전체의 실행 준비가 끝났다고
판정하지 않는다. Provider/evaluator call은 0/0, added model cost는 `$0`이며 memory effect, negative transfer와
held-out/core 결과를 보고하지 않는다.

## D-106 index-build qualification boundary

D-106 qualification은 agent 성능이 아니라 index construction integrity만 판정한다. Exact D-105 approval binding,
snapshot file identity, local-only reload, no-truncation, vector shape/dtype/finiteness/norm, admitted group exactness,
deterministic index identity, out-of-band provenance와 unfrozen state가 모두 통과해야 한다. Task success, hidden
acceptance, SCRR, retrieval score와 memory improvement는 gate 조건이 아니다.

Provider token delta는 아직 측정하지 않았고 retrieval도 실행하지 않는다. 따라서 D-106 index는 future validation
input일 뿐 comparison condition에 배정할 수 없다. 다음 gate에서 provider exact memory delta와 portable index를
다시 검증하고 별도 freeze authorization을 받은 뒤에만 retrieval/no-match test로 진행한다.

## D-107 portable validation and token-count source-gate protocol

D-107은 D-106 index의 성능을 평가하는 단계가 아니다. Portable copy가 runtime `.patchloop`와 embedding
weight 없이도 exact source, render, vector와 authority로 다시 검증되는지 보고, provider에 보낼
token-count request 두 개의 bytes를 미리 고정하는 offline gate다.

Portable index qualification은 다음을 모두 요구한다.

1. D-106 gate의 exact ID, body SHA, file bytes/SHA가 외부 anchor와 같다.
2. D-106 implementation file binding과 portable directory의 exact-one index file set이 같다.
3. Index JSON이 canonical이고 content-derived ID가 같다.
4. Stored vector로 전체 index를 다시 만든 bytes가 checked-in portable bytes와 같다.
5. Admitted group은 pyfakefs, HF Hub, tox 순서이고 AnyIO/Loguru hold가 index에 없다.
6. `frozen=false`, `FROZEN` marker 부재, retrieval/core authority false다.
7. Runtime index, embedding model, provider, retrieval, freeze, private/evaluator body를 읽거나 호출하지 않는다.

Token-count pair는 frozen manifest의 첫 development-validation task `moto-query-scanned-count` version 1 public
context에서 만든다. Model/prompt/tool/context tuple은
`gpt-5.4-mini-2026-03-17` medium/standard/default, `SYSTEM_PROMPT_V3`, tool schema `v2`,
`phase-evidence-v5`이다. Baseline의 `/selected_memory`는 `null`, with-memory의 같은 slot은 exact
D-105 whole-entry bundle이다. Canonical context deep diff는 그 pointer 하나뿐이고, slot normalization 후
full request와 count request pair도 각각 같아야 한다. Context, full request, count request의 baseline/
with-memory artifact 6개 전체가 file SHA와 semantic hash로 결속된다.

현재 gate의 provider 호출 수는 0이다. `baseline_input_tokens`, `with_memory_input_tokens`,
`memory_delta_tokens`는 모두 `null`이고 receipt는 없다. 따라서 `provider_exact_budget_validated=false`다.
이를 local tokenizer count나 문자 수 추정으로 채우지 않는다.

후속 실행은 D-107 source gate ID/body/file SHA에 대한 별도 exact 승인을 받은 경우에만
다음 순서로 진행한다.

1. Baseline `responses.input_tokens.count` 1회
2. With-memory `responses.input_tokens.count` 1회
3. 두 결과가 모두 있을 때만 `with_memory - baseline` 계산
4. `0 <= delta <= 2000`이면 exact budget pass receipt 후보 생성

SDK transport retry와 automatic retry는 금지한다. 두 count call 중 하나가 실패하면 부분 결과로
delta나 receipt를 만들지 않는다. `responses.create` generation call은 0회이어야 한다. Count
receipt가 생기더라도 index freeze는 자동으로 허용되지 않으며 별도 승인이 필요하다.

D-107 portable report, plan, source gate는 각각
`d107portable_8fb06997dfd9aa7e07c116db8095b5397382356bcd1cfd71ab3ce6c8b4ad1785`,
`d107plan_7ace0e204f367fc857bfbc1ddaa1bbdc58dd9ff3c9272f9d9c7e2b7241160ee6`,
`d107_4bc473796fd4564bb4d4cc9bf975ea9e41addb4fda620135e6ae4d6a21e645d4`다. Source gate file SHA는
`sha256:b3e24975062e379ec94c77187570b392026bacdcc855adedb00943467aaf09f2`다. 이 gate는 provider
count/generation, freeze, retrieval, runtime injection, core, analysis와 memory-effect 결론을 열지 않는다.

## D-108 exact two-count execution qualification

D-107은 D-108이 exact predecessor로 소비한 historical no-call gate다. D-108 qualification은 memory가
task 성공을 높였는지를 평가하지 않는다. 같은 full-request pair의 `/selected_memory` 차이가 provider
input token으로 얼마인지 exact 두 count-only call로 측정하고, 그 실행이 승인 범위와 journal
계약을 지켰는지만 판정한다.

Qualification은 다음 조건을 모두 요구한다.

1. Approval이 exact D-107 gate/plan에 대한 baseline, with-memory count call 2회만 허용한다.
2. Journal이 exclusive create된 one-use file이며 exact 6-event 순서와 hash chain을 만족한다.
3. Issued request hash가 D-107의 baseline/with-memory count request와 같다.
4. Completed response 두 개가 HTTP 200, `response.input_tokens`, nonnegative integer다.
5. 두 raw response의 `retries_taken=0`이고 SDK transport/automatic retry를 사용하지 않았다.
6. Provider receipt와 committed journal row의 count/delta/hash가 서로 같다.
7. Generation, freeze, retrieval, runtime injection, evaluator, core와 analysis action이 없다.

성공 journal sequence는 claim, baseline issued/completed, with-memory issued/completed, receipt committed의 6개다.
기존 journal이 있으면 같은 execution을 다시 시작하지 않는다. 첫 번째나 두 번째 call이
실패하면 failure event 후 종료하고 retry하지 않으며, partial count로 delta, provider receipt 또는 success
completion gate를 만들지 않는다.

실제 관찰값은 다음과 같다.

```text
baseline input tokens    = 2,193
with-memory input tokens = 2,895
memory delta             =   702
maximum allowed delta    = 2,000
```

따라서 provider exact token-budget check는 통과했다. 이는 선택 memory bundle이 고정된 request pair에서
2,000-token allowance 안에 든다는 뜻이지 retrieval quality, task success, SCRR, memory effect나 negative
transfer의 결과가 아니다.

D-108 gate에서 `index_freeze_authorization_candidate_ready=true`가 되었지만
`index_freeze_authorized=false`, `memory_index_frozen=false`다. 따라서 retrieval/no-match test, runtime memory
injection, core campaign과 comparative analysis는 실행하지 않는다. 다음 gate는 exact D-108
completion gate에 대한 사용자의 별도 index-freeze 승인이다.

Executable evidence identity는 approval
`d108approval_dbe0873a16902f36a5094e963360f77d414973e29dec5fca5bab7a17c1ff3af3`, journal head
`sha256:84905f7a334ec349a2c979e6cfb68c9c67a23dda9219f1fc8036f9d2e78f5eaf`, provider receipt
`d107countreceipt_80447f354d982620b1c849a32abcd276c40428721c8948f6aef5671a11176946`, completion gate
`d108_c663c745d43fc31bdee5309825059827899872c13368d7e3709e8730ee0a0f86`다. Gate file SHA는
`sha256:5f57e29caa3a3c940c280a69fbed3abe3d8daba4b4542e039355443df931d7bc`다. Count-only endpoint의
실제 billing 또는 free-tier 적용을 확인할 invoice evidence는 없으므로
`billing_or_free_tier_claim=null`이다.

## D-109 index-freeze authorization candidate qualification

D-109 qualification은 memory 효과가 아니라 freeze 대상과 권한 경계의 정확성을 판정한다. 다음을 모두 요구한다.

1. Exact D-108 gate가 delta 702/maximum 2,000과 candidate readiness true를 유지한다.
2. Portable D-106 index가 55,644 bytes와 고정 SHA/content hash로 다시 검증된다.
3. Runtime directory에는 같은 `index.json` 하나만 있고 `FROZEN` marker가 없다.
4. 세 admitted group과 두 hold group, memory/vector 순서와 embedding revision이 바뀌지 않았다.
5. Future mutation whitelist 이외의 JSON field 변경, retry, provider/evaluator/retrieval/core 권한이 없다.
6. Current source gate가 candidate만 준비하고 approval receipt와 actual freeze를 만들지 않는다.

Actual freeze 직전에는 `verify_live_runtime=true`로 pre-state를 다시 확인해야 한다. D-109 checked-in portable
validation은 future freeze 뒤에도 historical artifact를 검증할 수 있도록 runtime recheck를 기본값으로 강제하지
않는다. Candidate ID/body/file SHA에 대한 사용자의 별도 exact 승인 전에는 freeze executor를 실행하지 않는다.

## D-110 exact one-use freeze qualification

D-110 qualification은 retrieval quality나 agent 성능을 평가하지 않는다. 사용자가 exact D-109 candidate triple에
승인한 한 번의 index freeze가 승인 범위, mutation whitelist, 순서와 증거 계약을 지켰는지만 판정한다.

Qualification은 다음을 모두 요구한다.

1. Approval receipt가 exact D-109 source gate와 candidate ID/body/file SHA를 결속하고 one-use freeze만 허용한다.
2. 실행 직전 `verify_live_runtime=true` 재검증이 55,644-byte unfrozen runtime index와 marker 부재를 확인한다.
3. One-use journal이 exact 8-event 순서, monotonic sequence와 hash chain을 만족한다.
4. Pre/post JSON deep diff가 `/frozen`, `/frozen_at`, 두 freeze authority pointer, `/content_hash`의 exact 다섯
   pointer뿐이다.
5. Post-freeze `content_hash`와 canonical file SHA가 재계산 결과와 일치한다.
6. Index commit이 marker보다 먼저이며 marker 내용이 post-freeze content hash와 LF다.
7. Runtime index/marker와 portable D-110 evidence가 byte-for-byte 같고 D-106 portable pre-index는 바뀌지 않았다.
8. Execution lock과 staged file이 남지 않고 partial 또는 ambiguous state가 없다.
9. Retrieval, runtime injection, core, analysis, provider와 evaluator action이 없다.

실제 execution start는 `2026-08-06T13:54:43.725943Z`다. Frozen runtime index는 55,687 bytes/file SHA
`sha256:c0d2ec424e6cc10d64cdebd5ae493e0546fdfa08d09eb5f3269557b46025c6d0`, content hash
`sha256:3a99e6c190672d1676bc4d13604de989899de9ddac85d282cc90c4d56f426c56`다. `FROZEN` marker는 72 bytes/file SHA
`sha256:cdfe40b734135a30f66e34ff24469940063a7231a1fe0783420ee2ff816d9561`다. Historical D-106 portable index는
55,644 bytes/file SHA `sha256:c9b292f67fcb3c4bf524065801681e76c5df22142bbbb8b2db36d3c932df358a`로 그대로다.

Commit은 ordered per-file protocol이다. Index staged-file fsync와 `os.replace` 후 marker를 exclusive-create/fsync한다.
두 파일을 합친 atomic transaction, arbitrary external writer exclusion 또는 crash 때의 automatic retry/rollback은
주장하지 않는다. Index-only 또는 다른 모호한 중간 상태는 성공으로 판정하지 않고 fail closed한다.

Executable evidence identity는 다음과 같다.

- Approval: `d110approval_cb0ab444a4c453fbf496e509891013163825c8b5c362204c43d37c7452d49e7b`, body SHA
  `sha256:cb0ab444a4c453fbf496e509891013163825c8b5c362204c43d37c7452d49e7b`, file SHA
  `sha256:f409c6296b1f87d8cb151fcc1866d263f3e74aa9341c46ab49ea3b4fef66a97c`
- Journal: 8 records, head
  `sha256:03d8bcbf57230aa9bfd5ce4e81fa2890bb36c2f5f9e4e51c9e64b3a8c09313e1`, file SHA
  `sha256:f06cfa9037f09720675d3c0edd7e19516144bd46375aaa86679c5b1f6923b1e2`
- Freeze receipt: `d110freezereceipt_b8ca4f167c330011118edb33d8ad3f18a47a20e795f28e752d6cc87e84daa839`, body SHA
  `sha256:b8ca4f167c330011118edb33d8ad3f18a47a20e795f28e752d6cc87e84daa839`, file SHA
  `sha256:a2aeaa0985cb1bf9ced5bdfd43c5bc473a73e5ac93bf7660ca717e3eb9285702`
- Completion gate: `d110_bc1cae7a2ebc5d6531d203ef4d7101762d7366c9e77814c3a4c772d353f0a736`, body SHA
  `sha256:bc1cae7a2ebc5d6531d203ef4d7101762d7366c9e77814c3a4c772d353f0a736`, file SHA
  `sha256:79578db09955dab2a22b015ba5210baec28e7d30b9cac818b1f2c6d6eac782cd`

Freeze receipt는 `2026-08-06T13:54:43.782123Z`, completion gate는
`2026-08-06T13:54:43.793637Z`에 기록됐다.

D-110 focused 검사는 mutation 전 17/17, freeze 이후 재검증 17/17이 통과했고 post-freeze run은
256.5초에 완료됐다. D-110 관련 전체 회귀나 repository-wide suite 결과로 확대해 보고하지 않는다.

Completion gate가 확인한 것은 index freeze 완료뿐이다. `retrieval_ready=false`,
`retrieval_experiment_authorized=false`, runtime memory injection count 0, `core_campaign_unlocked=false`,
`analysis_ready=false`이므로 retrieval/no-match test, agent context injection, core campaign과 comparative analysis는
아직 실행하지 않는다. Provider/evaluator call은 0/0이고 added model cost는 `$0`다. 다음 단계는 별도의
retrieval-readiness authorization candidate이며 이 완료가 retrieval 실행을 자동 승인하지 않는다.

## D-111 retrieval-readiness candidate qualification

D-111 qualification은 retrieval 품질이나 memory 효과를 측정하지 않는다. Exact D-110 frozen evidence를 바꾸지
않고 향후 local read-only probe의 입력과 권한 경계를 재현 가능하게 고정했는지만 판정한다.

Qualification은 다음을 요구한다.

1. Exact D-110 completion gate, frozen index/marker와 unchanged D-106 index가 다시 검증된다.
2. Probe는 public specification만 사용하는 Moto `IMPLEMENT`, Babel `IMPLEMENT`, Moto `REPRODUCE` 세 개이며
   이 순서를 고정한다.
3. 현재 scorer에서 자연스러운 public query의 최대 가능 점수 0.65가 threshold 0.72보다 낮음을 기록한다.
4. 이 점수 한계와 renderer, snapshot-locality, token-accounting gap 때문에 legacy retriever를 ready로 판정하지
   않는다.
5. Candidate는 가설과 control만 정의한다. 예상 ranking이나 pass/fail 결과를 미리 확정하지 않는다.
6. Approval receipt, query embedding, retrieval, runtime injection, provider/evaluator call, agent run, core와 analysis가
   모두 absent 또는 false여야 한다.

Preflight는
`d111preflight_ee48af2da2ab34bb252f11842fe34c734229ad193776fc97bdd34dc3849003f9`/
`sha256:ee48af2da2ab34bb252f11842fe34c734229ad193776fc97bdd34dc3849003f9`/13,085 bytes/
`sha256:fed699e068c52e2dd929b654a65369aee3499d6d69c5a38c14dcee808ff57387`다. Candidate는
`d111retrievalcandidate_bfde5cfe1c75cd90e8d78a0960b6d5ac7986420016d805e75b9725abdb20fe7a`/
`sha256:bfde5cfe1c75cd90e8d78a0960b6d5ac7986420016d805e75b9725abdb20fe7a`/6,465 bytes/
`sha256:f91aa284cc7a2add2516f44b4397b29e3aee5caa4cf0f83ec7913e6e5d7899d6`다. Source gate는
`d111_348e6dd21ad0816a3c4dc1889f2d7a421c7e41194c48b2fe5c7120513f6b3524`/
`sha256:348e6dd21ad0816a3c4dc1889f2d7a421c7e41194c48b2fe5c7120513f6b3524`/3,308 bytes/
`sha256:d550cb048e417965e482c64682df4a1b91b90067f66b36e370912f5a8d759c16`다.

Executable evidence는 focused 8/8과 related 7/7뿐이며 broader regression이나 repository-wide 통과로 확대해
보고하지 않는다. 다음 단계는 위 candidate triple을 외부에서 정확히 다시 제시하는 별도 sidecar approval이다.
그 전에는 retrieval, embedding, runtime memory injection과 core campaign을 실행하지 않는다.

## D-112 local scoring diagnostic qualification

D-112 qualification은 memory가 agent 성능을 개선하는지 평가하지 않는다. Exact D-111 approval 범위 안에서 local
query encoder와 고정 scorer를 한 번 실행하고 그 산출물을 model-free로 다시 검증할 수 있는지만 판정한다.

실행 acceptance는 다음 구조 조건의 논리곱이다.

1. Exact D-111 candidate/source gate, D-110 frozen index/marker, unchanged D-106 index, 두 public task와 10-file
   snapshot이 model load 전에 검증된다.
2. One-use receipt를 exclusive create/fsync한 뒤 model load 1회와 ordered batch encode 1회만 수행한다.
3. Moto/IMPLEMENT, Babel/IMPLEMENT, Moto/REPRODUCE 순서와 `(3, 384)` float32 finite normalized vector를 지킨다.
4. 모든 query-entry 조합의 semantic/class/phase/language/validation component, weighted contribution, final score,
   rank와 threshold 판정을 기록한다.
5. 저장된 full query vector로 9개 점수와 rank를 모델 없이 재계산한 결과가 gate와 같다.
6. Moto의 동일 query vector SHA가 같고 IMPLEMENT와 REPRODUCE의 entry별 score 차이가 `0.15`다.
7. Pre/post immutable input fingerprint가 같다.
8. Memory text 반환·선택·주입, legacy retrieval, agent/provider/evaluator call과 policy/index mutation이 없다.

Observed top group이나 hypothesized group 일치는 acceptance criterion이 아니다. 실제 결과는 다음과 같다.

| Probe | top group | top score | threshold pass |
| --- | --- | ---: | --- |
| Moto / IMPLEMENT | `exception-origin-state-conflation` | 0.3541890713468577 | false |
| Babel / IMPLEMENT | `exception-origin-state-conflation` | 0.39188659397843584 | false |
| Moto / REPRODUCE | `exception-origin-state-conflation` | 0.20418907134685768 | false |

세 probe 모두 diagnostic no-match다. Moto positive hypothesis의 hypothesized group은
`platform-emulation-matrix-gap`이지만 observed top과 달랐다. 이는 D-111에서 예측한 selective degeneracy와 semantic
ranking 한계를 관찰한 것이며, execution failure, memory benefit, negative transfer 또는 agent defect로 분류하지 않는다.

Executable evidence는 D-112 focused 11/11과 D-111/공용 memory 관련 회귀 13/13이다. Repository-wide full suite와
D-106~D-110 전체 관련 suite는 이번 checkpoint에서 실행하지 않았으므로 통과했다고 보고하지 않는다.

사후 source audit에서 actual score algebra와 9개 row는 stored-data-only 재계산과 일치했지만, generic validator
qualification에는 두 gap이 남았다. Skip-current-input flag도 local snapshot/dependency를 읽고, receipt fully-rehashed
unknown field strictness가 완전하지 않다. 따라서 D-112 통과는 **exact current artifact와 current checkout에 대한
qualification**이지 arbitrary rehashed artifact나 clean-machine portable validator의 완전한 보장이 아니다.

## D-113 validator-correction candidate qualification

D-113 qualification은 D-112 점수나 memory 효과를 다시 평가하지 않는다. 다음 조건의 논리곱으로, 별도
validator 보정 후보가 기존 실행 증거를 변경하지 않고 만들어졌는지만 판정한다.

1. D-112 receipt/gate와 실행-bound module/script/test의 exact bytes·ID·hash가 일치한다.
2. D-112에 기록된 portable frozen index/marker와 D-106 unfrozen index가 build 전후 동일하다.
3. 실제 세 timestamp 순서는 올바르지만 기존 validator가 그 순서를 강제하지 않는다는 차이를 기록한다.
4. 다섯 validator gap은 exact D-112 source SHA와 AST 구조 근거에 결속된다.
5. Future D-114 path는 기존 D-112 및 index path와 겹치지 않고 새 파일 생성만 허용한다.
6. Fully rehashed candidate의 권한 확대와 preflight binding/finding 변조는 expected payload equality에서 거부된다.
7. D-112 validator/replay, snapshot/model read, load/encode, retrieval/injection, agent/provider/evaluator/network
   call은 artifact 생성 과정에서 모두 0이다.
8. Approval receipt가 없고 correction, policy, retrieval, core와 analysis authority가 모두 false다.

Focused 검사는 18/18 통과했다. 별도의 D-111~D-113 연속 회귀는 기존 snapshot 검증 비용으로 5분 제한에서
시간 초과됐으므로 통과로 합산하지 않는다. D-113 completion은 correction 구현 완료가 아니라 exact candidate
triple에 대한 별도 사용자 승인 gate가 준비됐다는 뜻이다.

## D-114 append-only validator-correction qualification

D-114 qualification은 D-112 결과를 다시 실행하거나 점수를 바꾸는 검사가 아니다. Exact D-113 candidate 승인을
결속한 새 successor validator가 기존 D-112 증거를 수정하지 않고 알려진 validator gap을 fail closed하는지만 판정한다.

Qualification은 다음 조건의 논리곱이다.

1. Approval receipt가 exact D-113 candidate/source gate/action hash와 사용자 승인을 결속하고 repository-local
   exclusive-create claim을 한 번만 소비한다.
2. D-112 receipt/gate의 exact root/body/claim key set과 full expected payload equality를 검사한다.
3. Rehashed unknown field, unchecked claim flip과 paired receipt+gate rehash를 거부한다.
4. `approval <= claim <= completion` chronology와 receipt/gate pair binding을 강제한다.
5. `sealed-historical`과 `current-input` mode가 분리되고 correction evidence는 sealed mode만 실행한다.
6. Sealed mode가 checked-in frozen index, stored query vector와 exact public specification으로 D-112 score 9개를
   model/snapshot/dependency 없이 정확히 재계산한다.
7. D-112 실행-bound 파일과 receipt/gate/index/marker의 pre/post bytes가 같다.
8. Score/threshold/rank, retrieval/injection, agent/provider/evaluator/core authority가 열리지 않는다.

Approval receipt는
`d114approval_20d5025c5d72b156e8470812a0062da2d4d639aa2fa9848ef38da96a71112fd7`/
`sha256:20d5025c5d72b156e8470812a0062da2d4d639aa2fa9848ef38da96a71112fd7`/10,493 bytes/
`sha256:1f494579e70d9e8a7f0d28439578afc3b3aa77c7735ac8bc4e81627cab70793b`다. Completion gate는
`d114_8f378245c6965d59cd5e589a67cea203e502553e19fa9391b11a667db09271fb`/
`sha256:8f378245c6965d59cd5e589a67cea203e502553e19fa9391b11a667db09271fb`/15,686 bytes/
`sha256:c336004f12f187ab0bfb7946204f877c088703d25e809a8e79e9ec84d374be11`다. 승인, claim, completion 시각은
각각 `2026-08-07T03:04:28.745556Z`, `2026-08-07T03:42:18.669461Z`,
`2026-08-07T03:42:18.693491Z`이며 순서가 유효하다.

Sealed validation은 9개 row exact replay와 세 probe 모두 historical no-match임을 확인했다. 이는 query embedding
semantic fidelity의 재검증이나 memory 효과 측정이 아니다. Current-input mode는 구현됐지만 correction evidence에서
실행하지 않았으므로 current snapshot/dependency 일치까지 확인했다고 주장하지 않는다.

One-use는 repository-local cooperative claim이고 global/cross-clone exclusion이 아니다. Network call 0은
source-path/self-attested evidence이며 OS socket block은 검증하지 않았다. Materialization 중 별도의 negative tamper
probe를 실행하지 않았으므로 gate의 성공과 tamper unit test evidence를 혼동하지 않는다. Focused D-114 검사는 35/35가
통과했지만 repository-wide suite 통과로 확대하지 않는다. D-114 자체 model load/encode, retrieval, runtime injection,
agent/provider/evaluator call은 모두 0이고 added model cost는 `$0`다.

## D-115 offline score-policy decision candidate qualification

D-115 qualification은 corrected scorer나 runtime classifier를 구현하는 단계가 아니다. Exact D-114 successor evidence와
D-112의 9개 stored public-probe score row를 읽어 현행 정책의 구조적 한계와 허용 가능한 다음 조사 범위를 offline으로
봉인했는지만 판정한다.

Qualification은 다음을 요구한다.

1. Exact D-114 receipt/gate와 D-112 gate를 고정 ID/body/file SHA로 다시 검증한다.
2. D-112 9개 observed component와 current final score를 정확히 재계산한다.
3. Observed failure-class/validation 0, within-probe phase/language equality와 current upper bound `0.65 < 0.72`를
   확인한다.
4. 하나의 global threshold만 바꿔 Moto selection과 Babel no-match를 동시에 만족할 수 없음을 exact row로 증명한다.
5. Nonnegative current feature weight만 바꿔 Moto hypothesized group의 rank를 1위로 만들 수 없음을 증명한다.
6. D-112 hypothesis를 사용한 계산은 synthetic counterfactual로 표시하고 observed component, runtime classifier output,
   acceptance ground truth와 분리한다.
7. Corrected policy를 선택하지 않고 추가 public relevance evidence가 필요하다고 판정한다.
8. Protected D-112/D-114/index bytes와 score policy, runtime authority가 변하지 않는다.

Observed 결과와 synthetic counterfactual은 다음처럼 구분한다.

| 구분 | 입력 | Moto / IMPLEMENT | Babel / IMPLEMENT | Moto / REPRODUCE | 의미 |
| --- | --- | ---: | ---: | ---: | --- |
| Observed current | D-112 stored component | top `0.3541890713468577`, hypothesized group `0.30430094253875567` | top `0.39188659397843584` | top `0.20418907134685768` | 실제 D-112 diagnostic row |
| Synthetic conditional | hypothesis-derived class assumption + `0.25/0.40/0.15/0.10/0.10`, threshold `0.60` | hypothesized `0.6530721018133969` | top `0.3156332814131685` | hypothesized `0.503072101813397` | non-runtime, non-authoritative what-if |

Synthetic row는 Moto/IMPLEMENT non-acceptance hypothesis에 class signal 1.0을 넣고 이를 Moto/REPRODUCE에 복사하며
Babel은 모두 abstain한다는 수동 가정을 쓴다. 실제 classifier output이나 true relevance를 관찰하지 않았으며 이 결과로
policy를 선택하지 않는다.

Artifact identity는 다음과 같다.

- Preflight:
  `d115preflight_c9af86f3dd2f5e68316cd36290fcadb1ca8b2cfbe5627d6c6a531246183ba12b`/
  `sha256:c9af86f3dd2f5e68316cd36290fcadb1ca8b2cfbe5627d6c6a531246183ba12b`/59,725 bytes/
  `sha256:91908b43eb581b09249f8285e5f1d09389092c5b40c1c794b9ab139667c86bad`
- Candidate:
  `d115scoredecisioncandidate_91e3ef5af000fe830483012b5deee4eeb47f5a117fa5904d93d713b03f2308ec`/
  `sha256:91e3ef5af000fe830483012b5deee4eeb47f5a117fa5904d93d713b03f2308ec`/6,839 bytes/
  `sha256:1fd424eab88c60a9d8480e756642b2c70b03afd03dd777e27bf36a3ea428df7a`
- Source gate:
  `d115_ab5e8f0e9f57c5fb37f05137da5b6cf8ca6421856ade33616448023d39c4a805`/
  `sha256:ab5e8f0e9f57c5fb37f05137da5b6cf8ca6421856ade33616448023d39c4a805`/13,730 bytes/
  `sha256:67f62c23e9f5e14fe9cd1d075b2c6f679764c18644837914b0031348c4a21b72`

Focused D-115 검사는 19/19 통과했다. Repository-wide suite는 이 qualification에서 실행하지 않았으므로 통과로
보고하지 않는다. Source path 기준 model load/encode, retrieval, runtime injection, agent/provider/evaluator와
network-capable call path invocation은 모두 0이며 OS-level socket block/instrumentation은 검증하지 않았다.

Candidate의 exact triple 승인은 이후 D-116에서 public development input만 사용하는 deterministic abstaining
failure-class signal contract와 calibration candidate 준비에 한 번 결속됐다. D-115 자체는 classifier나 calibration을
실행하지 않았으며 `corrected_policy_selected=false`, score policy correction/implementation false, class signal
unchanged, `retrieval_ready=false`, retrieval experiment authorization false, runtime injection 0, agent run 0,
core/analysis false 경계는 D-116에서도 유지됐다.

## D-116 public applicability-signal contract qualification

D-116 qualification은 classifier 정확도나 memory 효과를 측정하지 않는다. Exact D-115 승인에 결속된 public-only
input/result/abstention grammar와 prospective calibration protocol이 exact artifact와 명시적 권한 경계로 봉인됐는지만
판정한다.

Qualification은 다음을 요구한다.

1. Approval receipt가 exact D-115 candidate ID/body/file SHA와 authorized action hash에 결속되고, 허용 범위가 새
   contract module/script/test와 네 append-only artifact로 제한된다.
2. Public inventory는 `dev-train` 8개와 `dev-validation` 2개의 `public.yaml` 정확히 10개이고, classifier projection은
   issue title·description·language만 포함한다. Task ID, path, tags, repository identity, phase, trace/patch/test/evaluator
   결과와 private/hidden/reference/known-bad/held-out evidence는 제외한다.
3. Input은 exact canonical key set과 SHA를 요구한다. Invalid/noncanonical projection은 ABSTAIN이 아니라
   `CONTRACT_ERROR`다.
4. `SELECT`는 exactly one fully supported group에만 허용한다. No full group, multiple full groups, partial evidence,
   contradiction 또는 unsupported language는 deterministic ABSTAIN이며 fallback semantic-top 선택은 금지한다.
5. Evidence span은 canonical field의 zero-based Unicode-code-point half-open 좌표를 사용하고, result collection의
   order·uniqueness·null 규칙을 고정한다.
6. Formal matcher grammar와 regex compile 검사는 완성되지만 matcher evaluator/classifier를 구현하거나 실행하지
   않는다. Task-level signal result와 calibration result도 생성하지 않는다.
7. Inventory 10개 중 prospective eligible은 8개이고 bootstrap exclusion은 2개다. Grammar 작성에 사용한 Pyfakefs와
   HF Hub 두 source anchor는 independent positive로 세지 않으며, tox는 public prose에 third-group required S3
   shared-error-boundary가 없어 strict expectation이 ABSTAIN이다.
8. 현재 panel은 contract authoring에 사용된 non-blind panel이고 independent positive count는 0이다. 12개 synthetic
   conformance case는 실행되지 않은 계획이며 calibration 또는 independent evidence로 세지 않는다.
9. Protected D-115/D-105/public task bytes와 D-116 implementation fingerprint는 materialization 전후 동일하다.
10. Score/threshold/weight, runtime class signal, memory entry/index/marker와 ranking이 바뀌지 않고 retrieval,
    injection, agent/provider/evaluator/core authority가 계속 닫혀 있다.

Artifact identity는 다음과 같다.

- Approval receipt:
  `d116approval_016c99bd81a756f640cf10132eda196057cb3a50a59cf593d64e215dc4d47bcb`/
  `sha256:016c99bd81a756f640cf10132eda196057cb3a50a59cf593d64e215dc4d47bcb`/12,014 bytes/
  `sha256:86c4e279df6c3d4b6ea02719375f76370d76fb795d642f2d10211e878662ba77`
- Preflight:
  `d116preflight_e9005e90895ea4554ea04b21b025ff1afc42076d4e08a7adef2b6476cbf06a3f`/
  `sha256:e9005e90895ea4554ea04b21b025ff1afc42076d4e08a7adef2b6476cbf06a3f`/76,157 bytes/
  `sha256:fc2602a385242204ab9ae274ea6c73a83bd00a00eace88c7f310a57b5d4655f5`
- Calibration candidate:
  `d116classsignalcandidate_0b1b700af4ce2274cb9cb032ecf23c741ec9c41b0e86abbc06e96e18f91c74d4`/
  `sha256:0b1b700af4ce2274cb9cb032ecf23c741ec9c41b0e86abbc06e96e18f91c74d4`/8,017 bytes/
  `sha256:8299f3d400bd9412a8b7100305a0eb57f1d5b4ea78a39d8e5edad6cd5a2b15ca`
- Source gate:
  `d116_e93b1d39428c3778dd1f55dd0ae1a6c7f4b2091f9b4a92c347f6b7b3c6a66c37`/
  `sha256:e93b1d39428c3778dd1f55dd0ae1a6c7f4b2091f9b4a92c347f6b7b3c6a66c37`/19,859 bytes/
  `sha256:f03bc7806d8401b9ac9f3d9e47df7b0ef19b16a04380bed1c9cb1d105e52320d`

Focused D-116 검사는 21/21 통과했다. Repository-wide suite는 이 qualification에서 통과로 보고하지 않는다. Formal
contract와 synthetic plan만 materialize됐고 matcher evaluator/classifier/calibration execution, task-level result,
model/embedding load, retrieval, runtime injection, agent/provider/evaluator/network-capable call은 모두 0이며 added model
cost는 `$0`다. Network evidence는 source-path/self-attested이고 OS-level socket block/instrumentation은 검증하지 않았다.
따라서 `three_class_calibrated=false`, `independent_generalization_validated=false`, `true_relevance_established=false`,
`corrected_policy_selected=false`, `retrieval_ready=false`, core/analysis false다.

다음 gate는 exact D-116 candidate ID/body/file SHA의 별도 사용자 승인을 받아 D-117의 **grammar-blind preexisting
byte-frozen public pool acquisition protocol candidate**만 준비하는 것이다. Pool assembler와 selector/adjudicator는
matcher grammar·hash·output으로부터 분리하고 selector/adjudicator에는 D-105 applicability rubric만 제공해야 한다.
Source pool membership 또는 exhaustive inclusion rule과 bytes/provenance는 D-116 이전 상태에 결속돼야 한다. 격리를
증명하지 못하면 control은 `post-hoc`, `independent=false`로 기록한다. 그 승인도 grammar 변경,
matcher/classifier/calibration 실행, score policy 수정, retrieval/runtime injection, agent/provider/evaluator call 또는
core/analysis campaign을 허용하지 않는다.

## Historical D-117 grammar-blind public-control acquisition protocol qualification

D-117 qualification은 independent control이나 matcher 정확도를 측정하지 않는다. Exact D-116 승인에 결속된
public-development-only acquisition protocol이 preexistence, role isolation, chain of custody와 fail-closed fallback을
명시하면서도 실제 pool acquisition과 review 권한을 열지 않았는지만 판정한다.

Qualification은 다음을 요구한다.

1. Approval receipt가 exact D-116 candidate ID/body/file SHA, source gate, frozen grammar hash, cutoff와 authorized action
   hash에 결속되고 새 module/script/test와 네 append-only artifact만 허용한다.
2. Future source pool은 public-development control만 허용하며 held-out task issue/result와
   private/hidden/reference/patch/trace/evaluator evidence를 membership과 read에서 제외한다.
3. Exact source bytes와 exact membership manifest 또는 grammar-independent exhaustive rule은 D-116 cutoff 전 trusted
   anchor에 결속돼야 한다. Current fetch, 새 hash, mtime, Git timestamp 또는 self-attested time만으로는 부족하다.
4. Provenance verifier, pool assembler, blinding broker, selector A/B, adjudicator, independence auditor와 future matcher
   evaluator의 visibility가 capability로 분리된다. 현재 process/agent, D-116 grammar observer, 같은 checkout
   subagent와 prompt-only blinding은 blind role이 아니다.
5. Selector A/B와 adjudicator는 opaque public projection과 exact D-105 rubric만 받고, 서로의 결과를 보기 전에
   independent first-pass를 봉인한다. D-116 grammar/hash/output, source identity와 task expectation은 금지한다.
6. Independence logic의 모든 항이 통과해야 positive로 인정한다. Missing/unknown/contaminated evidence는 record를
   삭제하지 않고 `post_hoc=true`, `independent=false`, independent calibration ineligible로 append-only 보존한다.
7. Zero eligible control은 유효한 결과이며 이를 이유로 ontology나 grammar를 약화하거나 label을 본 뒤 pool을
   확장할 수 없다. Group당 positive 1개도 matcher-evaluation 최소 coverage일 뿐 calibration 증명이 아니다.
8. D-117에서 신규 pool name/content를 식별·열람하지 않는다. Pool manifest/member, role/isolation session, blind
   packet, selector/adjudication result와 independent positive count는 모두 0이어야 한다.
9. Matcher evaluator/classifier/calibration 구현·실행, score/index/ranking 변경, model/embedding load, retrieval,
   injection, agent/provider/evaluator/network-capable call과 core campaign은 모두 0/false여야 한다.
10. Protected D-116/D-105 bytes와 D-117 implementation fingerprint는 materialization 전후 동일해야 한다.

Artifact identity는 다음과 같다.

- Approval receipt:
  `d117approval_f70a2ff210ae2df203591b9650177161ca71084da256e994539af09a48deeae9`/
  `sha256:f70a2ff210ae2df203591b9650177161ca71084da256e994539af09a48deeae9`/10,096 bytes/
  `sha256:40ea64548634353a12b48f8bcabce941df47e16f9b27d892722d55fcda1e5e13`
- Preflight:
  `d117preflight_34645da3c09db9d3ba288425b44e0e27f631e8b034a231abd7e113dbdeea5464`/
  `sha256:34645da3c09db9d3ba288425b44e0e27f631e8b034a231abd7e113dbdeea5464`/29,919 bytes/
  `sha256:6682f4f2870cdb34e6ee766333c95ac58a406a7d4e4086d6086752650869c305`
- Authorization candidate:
  `d117blindprotocolcandidate_27622afdd9d46e43cb9e23675a334b5a4e91fc768298374cae61ab440c850dae`/
  `sha256:27622afdd9d46e43cb9e23675a334b5a4e91fc768298374cae61ab440c850dae`/7,999 bytes/
  `sha256:d10bbe5b3b65050868a1202cd1af9f130c89bbe43ceccf9359af145cac96cda7`
- Source gate:
  `d117_750cd5a0a8946984aafe75b0939417bf026120cdb3dbc54d09180fd795202589`/
  `sha256:750cd5a0a8946984aafe75b0939417bf026120cdb3dbc54d09180fd795202589`/16,813 bytes/
  `sha256:a439fc936b5b594c043b4ea90cd57bb676e79004cf4de8794b83f3af15fb13e3`

D-116+D-117 focused 검사는 46/46 통과했다. Repository-wide suite는 이번 qualification에서 실행하지 않았으므로
통과로 보고하지 않는다. Source pool read, held-out read, pool/member/role/isolation/blind-review artifact,
matcher/classifier/calibration implementation·execution, model/embedding load, retrieval/runtime injection,
agent/provider/evaluator/network-capable call은 모두 0이며 added model cost는 `$0`다. Isolation profile은 아직
실행되지 않았고 OS-level socket block/instrumentation도 검증하지 않았다. 따라서 independent positive count는 0,
`three_class_calibrated=false`, `independent_generalization_validated=false`, `retrieval_ready=false`, core/analysis false다.

당시 next gate는 exact D-117 candidate triple과 exact external pre-D-116 source snapshot, pre-D-116 membership manifest 또는
exhaustive rule, trusted cutoff anchor, isolation profile triple을 별도 승인해 D-118의 **one isolated public-development
pool acquisition execution-authorization candidate만** 준비하는 것이다. 그 승인도 actual acquisition/review,
unapproved issue content read, matcher/classifier/calibration 실행, score policy 변경, retrieval/runtime injection,
agent/provider/evaluator/network call 또는 core/analysis campaign을 허용하지 않는다. Exact next-gate code는
`exact-d117-candidate-triple-plus-external-source-membership-cutoff-and-isolation-triples-d118-execution-authorization-candidate-approval`이다.

## Historical D-118 external source evidence qualification

D-118 qualification은 task 적합성, matcher 정확도나 memory 효과를 측정하지 않는다. Exact D-117 승인 범위 안에서
revision-pinned public-development source 파일을 opaque하게 결속하고, preexistence와 isolation evidence가 부족하면
실행 권한을 열지 않는지만 판정한다.

Qualification은 다음을 요구한다.

1. Receipt, preflight, evidence pack, source gate의 exact root/body key set, canonical bytes, ID/body/file SHA와 chronology가
   재현돼야 한다.
2. SWE-bench `f5351ee8c6663736817027db3ad03fe662cb5bb8` dev와 SWE-Gym
   `26a6eae79ae9cb6d4307c3cc99c126fbf23cb3f0` train의 `.gitattributes`, `README.md`, opaque parquet 6개만
   source binding에 포함하며 총 크기는 45,036,395 bytes여야 한다.
3. Opaque payload는 각각 1,382,594 bytes/
   `sha256:d758d54540aa4140d0274ed0cc93b8288aa6f323c3c603e2557e7666a47fc41b`와 43,644,473 bytes/
   `sha256:60569cea74bb281f7a5579467436a2bc1932c6e0c5f2f7fa0d084392abd9ad97`여야 한다.
4. Record container parse, task/issue record와 prose·label·hint·patch·test·oracle field read는 0이어야 한다. Raw record
   value나 snapshot bytes를 report/document에 복제하지 않는다.
5. Provider revision·split/member count·tree binding·GPG badge 관찰은 self-attested source-level research로만 표시한다.
   Bound input에서 provider tree/signature proof를 재구축하지 않았다면 trusted timestamp나 portable proof로 승격하지
   않는다.
6. Trusted pre-D-116 anchor가 exact snapshot과 membership rule을 함께 묶지 못하거나 isolation session이 실행되지
   않았다면 `BLOCKED_INSUFFICIENT_PREEXISTENCE`로 fail closed한다.
7. 이때 `trusted_cutoff_anchor_verified`, `technical_isolation_verified`, `independent`,
   `eligible_for_independent_calibration`, `execution_authorization_candidate_ready`는 모두 false여야 한다.
8. Issue labeling/review, matcher/classifier/calibration, score/index/ranking mutation, retrieval/runtime injection,
   agent/provider/evaluator call과 core/analysis campaign은 모두 0/false여야 한다.
9. 기본 `sealed-historical` mode는 raw object 없이 봉인된 pack을 replay하고, opt-in `current-object` mode만 ignored local
   object를 read-only rehash한다. Current-object 일치도 historical preexistence나 independence를 증명하지 않는다.

Artifact identity는 다음과 같다.

- Approval receipt:
  `d118approval_2a7461b834374e4a34db8c02850501d0ad9e8416e7a4bf7f73613abef08713a2`/
  `sha256:2a7461b834374e4a34db8c02850501d0ad9e8416e7a4bf7f73613abef08713a2`/4,199 bytes/
  `sha256:0adb87887b42a19aa8d1b9be3ca5268801666bbecb2cf94b4664e3df1dba8344`
- Preflight:
  `d118preflight_1f11c66f174e5e475ef9d94df7810c568857f02a8164edf30287778276dab4b0`/
  `sha256:1f11c66f174e5e475ef9d94df7810c568857f02a8164edf30287778276dab4b0`/17,476 bytes/
  `sha256:4f4bff33cbf55e841f86da0a30fc67885f9302fa2f149dde040a3d85a2c4c0b3`
- Evidence pack:
  `d118evidencepack_e40dad5ceac6dcfbb29d47bec3a548c44bdcbeba964e4e7a43818b76e8c62f10`/
  `sha256:e40dad5ceac6dcfbb29d47bec3a548c44bdcbeba964e4e7a43818b76e8c62f10`/25,451 bytes/
  `sha256:318d4f58276283e6e6ae6c45c4afe50af5bca6b6937ffa841b8b791a0357c6b1`
- Source gate:
  `d118_cdd55277ad1dc1215a45aa3588e7862df3535b91b7274681fe0a8488abd3e707`/
  `sha256:cdd55277ad1dc1215a45aa3588e7862df3535b91b7274681fe0a8488abd3e707`/17,748 bytes/
  `sha256:0f01a2b315f9c32c34b8c2400af6f22a1c4f2538b2538f8597f2ab0b8d57c343`

Actual result는 `BLOCKED_INSUFFICIENT_PREEXISTENCE`다. Record read/label/review와 matcher/retrieval/agent/core count는
0이고 trusted cutoff, technical isolation, independence와 execution readiness는 false다. D-117+D-118 focused 검사는
48/48 통과했다. Repository-wide suite는 이 qualification 결과로 통과했다고 보고하지 않는다. 당시 다음 qualification은
trusted pre-D-116 external anchor와 실행된 immutable isolation evidence가 별도 승인·결속된 뒤에만 정의할 수 있었다.
이후 D-119는 실행을 시작했지만 trusted cutoff나 independence를 확립하지 못했다.

## Historical D-119 cutoff/isolation partial-execution qualification

D-119 qualification은 exact one-use 실행이 어디까지 durable하게 기록됐는지를 journal로 판정한다. 결과는
`PARTIAL_CONSUMED_FAILED`이고 probe outcome은 `UNSEALED_UNKNOWN`이다.

Qualification 해석은 다음 경계를 지킨다.

1. Receipt와 preflight의 exact ID/body/file SHA, authorized action hash와 automatic-retry 금지를 검증한다.
2. Journal hash chain은 `ExecutionClaimed`, `ImageIdentityVerified`, 첫 `IsolationSessionStarted`, `ExecutionFailed` 네
   record까지만 인정한다.
3. Probe result, cleanup detail, `IsolationSessionCompleted`, 두 번째 session start와 completion gate가 없으므로 first
   probe 성공·실패를 추론하지 않는다.
4. Approval claim은 소비됐고 같은 D-119의 retry/resume/repair를 허용하지 않는다.
5. Cleanup validator failure를 source hash, task, container removal 또는 Docker isolation failure로 재분류하지 않는다.
6. D-119 external-anchor evidence, isolation evidence와 source gate는 absent 상태로 유지한다.

Artifact identity는 다음과 같다.

- Approval receipt:
  `d119approval_671af8d6e7cbd44ef0793c1bf1bf53f3f5f8e3fcbfd26e04906cb4abdea50cce`/
  `sha256:671af8d6e7cbd44ef0793c1bf1bf53f3f5f8e3fcbfd26e04906cb4abdea50cce`/5,299 bytes/
  `sha256:625cd6487fffe50b2429e011c67da222ec0da020dbf62d65a911fa83da3f550c`
- Preflight:
  `d119preflight_85dcbc49bec53797904f080d0e6922b521a9f6f232902e122895090e5f886dd1`/
  `sha256:85dcbc49bec53797904f080d0e6922b521a9f6f232902e122895090e5f886dd1`/11,229 bytes/
  `sha256:57f59fc29054276947851abdfe3dbf0040fe10cef5624946e66dc84a698fb18a`
- Four-record journal: head
  `sha256:4bd08521b13431251449d79cb2847a93fc947cf2ce6e6b319e71f728cc74bd46`/2,075 bytes/file SHA
  `sha256:fadda3b86b2ad954a1d233b0dbf11d67b8a9a86f3db6704eab555eec5f2a4950`

D-120이 기록한 source-consistent/self-attested diagnosis는 removed-object `inspect`의 nonzero return code와 별개로
stdout exact-empty를 요구한 cleanup output-representation assumption이다. Current CLI의 synthetic missing-object
observation은 `[]` plus LF지만 original D-119 raw transcript/stdout이 없으므로 portable root-cause proof가 아니다.
Cleanup exception이 earlier primary outcome을 가렸을 가능성도 배제하지 않는다.

관련 public web 조사에는 incidental example parser overreturn 1이 있었고 dataset record read는 0이다. 이 둘을 함께
공개하며 prohibited content exposure가 0이었다고 주장하지 않는다.

## Historical D-120 D-119 failure-seal and D-121 authorization-candidate qualification

D-120 qualification은 cleanup fix나 successor run을 수행하지 않는다. D-119 partial state와 진단 한계를 exact bytes로
봉인하고, 별도 승인 후 만들 수 있는 D-121 implementation/test/no-start readiness/execution-candidate 범위만 준비한다.

Qualification은 다음을 요구한다.

1. D-119 receipt/preflight/journal, absent output set, implementation와 exact execution tuple을 다시 결속한다.
2. D-119 status를 `PARTIAL_CONSUMED_FAILED`, first probe를 `UNSEALED_UNKNOWN`, durable completed session과 sealed
   outcome을 0으로 유지한다.
3. Cleanup diagnosis는 source-consistent/self-attested, portable proof false로 표시하고 source/task/isolation failure를
   새로 주장하지 않는다.
4. D-119 mutation/retry/resume/repair authority를 false로 유지한다.
5. D-121 preparation과 prospective run output path를 분리하고 normalization alias, ADS, symlink/junction/reparse와
   existing inode alias를 fail closed한다.
6. D-120 candidate materialization 중 Docker/container/network call, opaque source open/read, record parse/read를 0으로
   유지한다. 이 zero-call claim은 source-path static audit와 focused guard이며 subprocess/socket instrumentation 증명이
   아니다.
7. Exact D-120 candidate 승인 범위와 later D-121 run 승인을 별도 gate로 분리한다.
8. Trusted cutoff, record-projection isolation, independence, matcher/retrieval/agent/core authority를 false/closed로
   유지한다.

Artifact identity는 다음과 같다.

- Preflight:
  `d120preflight_cc3496328cf64c924c762d47a7f4926d23322991c29064e68ae6d376a8339310`/
  `sha256:cc3496328cf64c924c762d47a7f4926d23322991c29064e68ae6d376a8339310`/21,101 bytes/
  `sha256:6ec5ff207fdf24cb8baab733b9db096ece3d1fe1ba0ba5c6c644ac6c20ccd5ea`
- Authorization candidate:
  `d120cleanupcandidate_86d95b4b3cf0b49a20724b136075bfa9da281fce4dc6b20b6063a07bfcdd9b82`/
  `sha256:86d95b4b3cf0b49a20724b136075bfa9da281fce4dc6b20b6063a07bfcdd9b82`/10,464 bytes/
  `sha256:f4f985e6574ead218ffea4813d234c1b5c35cdf60e109de5bbe0849dd25127d8`
- Source gate:
  `d120_8172bae0e2446e647edb8d03272cf5499a9faa8f92a1f26b8cd08b5a9dc6abbd`/
  `sha256:8172bae0e2446e647edb8d03272cf5499a9faa8f92a1f26b8cd08b5a9dc6abbd`/12,140 bytes/
  `sha256:cd4fe9024bfb1b44e9e762412e442f3c2958085629b15e19f7a9423aefa3581b`

D-118~D-120 regression은 당시 76/76 통과했지만 repository-wide suite 통과로 확대하지 않는다. Exact D-120
candidate 승인은 이후 D-121 preparation에 한 번 소비됐다. D-121 materialization 뒤 D-120 focused의 historical
successor-path absent-state assertion 7개가 실패하는 것은 예상된 post-successor 결과이며 D-120 fix나 product
regression이 아니다.

## Current D-121 no-start readiness and execution-candidate qualification

D-121 qualification은 actual hash-only isolation success가 아니라 Docker **configuration realization only**를 판정한다.
Exact artifact identity는 다음과 같다.

- Preparation receipt:
  `d121preparationapproval_0f0627d6cdc6e63cd5d73eff66646406b7bbd1c64affb43fc35e0fa701b6fc79`/
  `sha256:0f0627d6cdc6e63cd5d73eff66646406b7bbd1c64affb43fc35e0fa701b6fc79`/14,662 bytes/
  `sha256:5a5592c2fff7deae63c50482d109c0d8e79ff4016fb96aaa8cb5a7b442d83606`
- Readiness:
  `d121readiness_8d1bbf95e3bb8fbe9717a0f3620cdd9985091d0695aff69622d92d046ad6be12`/
  `sha256:8d1bbf95e3bb8fbe9717a0f3620cdd9985091d0695aff69622d92d046ad6be12`/32,423 bytes/
  `sha256:3423bf9af71d9b69579115d65a2b67d2bdb39363748e40a9cb78bdd461ad94e6`
- Execution candidate:
  `d121executioncandidate_b37bde7b9f49f92118ca277e521cd409b1e51b6f97c1ad8c2e9ff5090a1c38ef`/
  `sha256:b37bde7b9f49f92118ca277e521cd409b1e51b6f97c1ad8c2e9ff5090a1c38ef`/11,046 bytes/
  `sha256:0e8ea35d4fda06ecfba180150062b873ada5b11dd98df7bd0416c557777db1c5`
- Source gate:
  `d121_711b9c8e738128d3d03b42c3287bf57418e02348b12a2c10707e9ce5ba1fe592`/
  `sha256:711b9c8e738128d3d03b42c3287bf57418e02348b12a2c10707e9ce5ba1fe592`/15,514 bytes/
  `sha256:e9c05396e10770c4290b2e57235f32da6fe3997afcd3fdb109c3697cea773b50`

No-start qualification은 다음 exact counters를 요구한다.

1. Docker daemon command 8, create 1, start/run/exec 0
2. Probe execution과 stdin bytes 0
3. Opaque source filesystem path reference/mount/access/read bytes 0
4. Record parse/field read 0
5. Exact-ID와 successor-label residual container 0

Created container는 synthetic nonopaque sentinel 한 개만 read-only bind하고 start 전에 inspect한 뒤 제거했다. Image,
user, command, network none, read-only root, capabilities, pids/resources, tmpfs와 mount configuration은 실현됐지만 probe는
실행되지 않았다. 그러므로 `no_start_readiness_passed=true`, `docker_configuration_realization_verified=true`여도
`hash_only_isolation_profile_verified=false`, actual successor run authorization/count 0,
`trusted_cutoff_anchor_verified=false`, `record_projection_isolation_verified=false`, `independent=false`다.

D-121 focused 47/47과 D-119+D-121 82/82가 통과했다. 다음 gate는 exact D-121 execution candidate triple의 별도
승인으로 action hash `sha256:abcb95eb01311419dfd5907a25e91fd1bb09fac5b035e60585ce2b8f5057e47b`에
결속된 fresh two-session successor run 정확히 1회만 허용한다. D-119 retry/resume/repair나 automatic retry가 아니며,
성공하더라도 trusted cutoff/projection/independence는 false로 남는다. Matcher/classifier/calibration, score/index mutation,
retrieval/runtime injection, agent/provider/evaluator와 core/analysis는 계속 닫혀 있다.
