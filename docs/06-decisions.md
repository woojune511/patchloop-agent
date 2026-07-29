# Decisions and Open Questions

상태: **Living decision log**

이 문서는 agent가 이미 정한 사항을 반복해서 재논의하거나 임의로 범위를 확장하지 않게 한다.

## Accepted decisions

| ID | Decision | Rationale |
| --- | --- | --- |
| D-001 | v1은 Python repository만 지원한다. | Dataset, sandbox, verifier 범위를 통제한다. |
| D-002 | Single-agent state machine을 사용한다. | Memory policy 효과와 역할/prompt 변화를 분리한다. |
| D-003 | Evaluator를 agent보다 먼저 구현한다. | 이후 harness 변화가 실제 개선인지 판정할 기준이 먼저 필요하다. |
| D-004 | Agent와 hidden evaluator는 별도 sandbox다. | Hidden test 검색·수정·누출을 막는다. |
| D-005 | Run state는 대상 repository 밖에 둔다. | Source patch와 orchestration state를 분리하고 agent 변조를 막는다. |
| D-006 | Agent는 registered check만 실행한다. | 안전성과 재현성을 높인다. |
| D-007 | Primary verdict는 deterministic verifier로 계산한다. | 재현 가능하고 비용이 낮으며 기준이 명시적이다. |
| D-008 | Memory core comparison은 A~D 네 조건이다. | 표현 효과를 같은 harness에서 분리한다. |
| D-009 | Held-out 전에 memory index와 retrieval config를 freeze한다. | Data leakage와 사후 tuning을 막는다. |
| D-010 | Failure memory는 remediation rule이며 solution code를 저장하지 않는다. | 일반화 가능성을 평가하고 정답 누출을 막는다. |
| D-011 | UI와 GitHub는 core evaluation 뒤에 구현한다. | Portfolio의 핵심을 trace와 실험 결과에 둔다. |
| D-012 | Negative result를 유효한 산출물로 취급한다. | 과장된 개선 주장보다 재현 가능한 failure analysis가 중요하다. |
| D-013 | `DONE`은 agent submission 완료이며 evaluator 성공이 아니다. | Agent 자기평가와 최종 판정을 분리한다. |
| D-014 | v1 공식 evaluator 경로는 Windows 11 + WSL2의 Linux Docker container다. | Agent/evaluator 격리와 실행 환경을 고정하며 local backend는 smoke 전용 `official=false`로 유지한다. |
| D-015 | Replay source는 repository-relative JSONL 경로와 SHA-256을 run manifest에 함께 고정한다. | Offline run과 resume이 같은 recorded response bytes를 사용했음을 검증하고 외부 경로 의존을 막는다. |
| D-016 | 기존 `mini-data-utils` 다섯 task는 calibration fixture이며 memory, core와 headline에서 제외한다. Research target은 별도의 20개다. | 쉬운 authoring/evaluator 확인 문제를 agent capability나 memory effectiveness evidence로 오해하지 않게 한다. |
| D-017 | Research admission은 immutable provenance가 있는 benchmark instance 또는 upstream incident, medium 이상 difficulty, base failure, official reference 3회와 세 개 이상 bad-patch rejection evidence를 요구한다. | 유명 benchmark 포함 여부나 directory 이름 대신 재현 가능한 독립 audit로 데이터 품질을 결정한다. |
| D-018 | Terminal-Bench 2.1은 세 sentinel stress overlay와 external acceptance의 참고 원천으로 사용하고 core aggregate와 분리한다. 원본 terminal task보다 constrained coding adaptation을 우선한다. | Unrestricted shell, network와 shared verifier를 PatchLoop의 고정 tool/evaluator 계약에 섞지 않으면서 실제 deployment failure pattern을 보존한다. |
| D-019 | Stress sentinel은 held-out 12개의 public contract structure만으로 결과를 보기 전에 선택한다. `public-contract-structure-v1`은 widest change surface로 FuseSoC #776, 남은 task 중 narrowest mutation surface로 AnyIO #1134, 남은 task 중 longest visible check로 pyfakefs #1269를 고정한다. | Private oracle, reference solution과 model outcome을 선택에 사용하지 않으면서 change breadth, 좁은 mutation, 긴 check의 서로 다른 stress profile을 재현 가능하게 포함한다. |
| D-020 | 세 sentinel 모두에 context reset, worker restart와 test timeout을 적용한다. Memory는 `no_memory`, context/worker는 persistent state on/off 각 2회, timeout은 on 2회로 총 30개 derived run이며 core 96개와 분리한다. Trigger는 각각 model call 10 직후, 첫 durable patch checkpoint 직후, 첫 registered visible check다. | Fault와 task를 임의 배정하지 않고 persistence ablation과 timeout behavior를 같은 고정 panel에서 비교하며, stress 결과가 memory core headline을 오염시키지 않게 한다. |
| D-021 | 새 suite는 `experiment-v2`의 explicit purpose를 사용한다. 첫 live gate는 Babel #1042 development-validation `no_memory` 1회($2 cap), 다음 gate는 frozen memory-development 6 task의 `no_memory` 각 2회, 총 12 run($20 cap)이다. | 한 번의 작은 tool-loop/trace 검증 없이 12개 paid run을 시작하지 않고, validation trace가 memory source로 섞이지 않게 한다. |
| D-022 | Paid approval은 checked-in config가 아니라 invocation의 `--approve-live-cost`와 exact preflight `--approved-execution-hash` 조합이다. Preflight는 dataset/role/hash와 canonical package path, public/private spec hash, digest-pinned environment/observed Docker identity, clean commit, API key 존재만, custom base URL 부재, SDK/model config, 72시간 공식 가격과 budget reserve를 검사한다. Live capability는 이 승인을 포함한 durable execution plan에서만 발급하며 direct live run/resume/fault를 차단한다. | 승인 후 task/private oracle/config/환경이 달라진 실행과 우회 경로를 막고 secret을 artifact에 넣지 않으면서 비용 권한을 한 exact execution으로 제한한다. |
| D-023 | Legacy run은 immutable `trace-qualification-v1`을 유지하고 새 live no-memory attempt는 `trace-qualification-v2`를 거쳐야 하며 memory candidate는 qualified memory-development failure로 제한한다. Qualification의 `source_evidence_hash`는 approved plan, manifest, events, checkpoints, result와 agent-visible artifact inventory를 결속하고 development campaign preflight와 review/index admission 때 다시 계산한다. Failure는 hidden check ID를 제거하고 append-only hash-chained human review를 통과해야 memory build에 들어간다. | 실패 trace에서 배우되 solution/private oracle 누출, stale qualification과 자동 self-approval을 막고 원시 판정과 사람의 review history를 덮어쓰지 않는다. |
| D-024 | Paid campaign은 최초 `CampaignStarted`를 exclusive create로 원자적으로 선점하고, 각 `RunStarted`를 model call 전에 append-only hash chain에 flush와 fsync한다. 기존 journal 또는 동시 선점 경쟁의 패자는 새 schedule 시작을 차단한다. 중단된 campaign의 자동 resume은 구현될 때까지 제공한다고 주장하지 않는다. | Process 종료와 최종 result JSON 사이의 창 및 동시 invocation에서도 이미 시작한 paid row를 잊거나 중복 호출하는 것을 막으며, 구현되지 않은 recovery 의미론을 분리한다. |
| D-025 | Predeclared matrix가 불완전하거나 qualification-failed이면 report는 `analysis_ready=false` available-case diagnostic만 제공하고 headline metrics, paired difference/CI와 success/failure flip을 억제한다. | Infrastructure halt나 누락 repetition의 불균형 분모를 정상적인 memory 효과 비교로 오해하지 않게 한다. |
| D-026 | Constrained `apply_patch` 입력은 `diff --git`으로 시작하는 raw Git unified diff로 고정하고 marker envelope를 거부한다. 성공·거부 tool result 모두 CAS artifact와 다음-turn feedback을 남긴다. Leakage scan은 canonical public spec에 이미 공개된 generic structure marker와 hidden check ID만 예외 처리하고, reference/hidden artifact identity와 API key는 항상 비밀로 검사한다. | 첫 paid pilot이 유효한 코드 후보를 만들고도 문법 feedback 부재로 mutation을 8회 반복했고, 공개 marker 41건을 private leak로 오인했다. 실제 tool failure와 secret leak를 구분하면서 같은 오류의 비용 반복을 막는다. |
| D-027 | Terminal 상태로 끝난 unqualified paid pilot는 기존 result, qualification과 journal을 그대로 보존한다. 원인과 수정 evidence를 check-in한 뒤에만 새 experiment ID, clean execution hash, preflight와 별도 비용 승인으로 retry한다. | Completed journal 삭제나 experiment ID 변경만으로 중복 실행 guard를 우회하지 않으면서 development gate의 명시적인 corrective retry를 허용한다. |
| D-028 | Paid execution은 preflight 뒤 suite path를 다시 읽지 않고 approved plan의 normalized suite snapshot을 사용한다. 각 row의 task package와 생성 manifest는 plan의 task/model/budget/sandbox/memory/experiment identity에 다시 대조하고 일치할 때만 `RunStarted`와 model call을 허용한다. | 승인 hash 계산과 실제 실행 사이에 suite/task 파일이 교체되는 TOCTOU가 승인 범위 밖의 호출로 이어지지 않게 한다. |
| D-029 | Agent-visible gateway는 raw Git patch의 hunk old/new line total만 `--recount`한다. Raw input/hash, hunk body/context/path와 verifier는 그대로 유지하고 hidden evaluator는 strict하다. Legacy v1 policy rollback은 같은 raw patch를 reverse recount한다. 새 파일·rename/copy는 거부하며 agent workspace는 gateway 전후, checkpoint와 recovery에서 zero-untracked를 강제한다. Policy reject 뒤 pre-call diff hash를 복원하지 못하거나 rollback이 실패하면 `RecoveryError`로 fail-closed한다. v2 rollback/mutation은 D-035가 이 부분을 supersede한다. | r2의 아홉 patch candidate가 모두 실제 6줄 body를 7줄로 선언해 coherent edit가 evaluator 전에 거부됐다. Recount check는 원문을 적용 가능하게 만들었지만, untracked와 rollback 실패를 일반 rejection으로 처리하면 scope 우회 또는 더러운 workspace에서 실행을 계속할 수 있으므로 호환성과 복구 경계를 함께 고정한다. |
| D-030 | `CampaignCompleted.result_hash`는 persisted experiment result의 정확한 UTF-8 bytes를 가리킨다. Runner는 hash 계산에 사용한 bytes를 `write_bytes`로 그대로 저장하고 플랫폼 newline 변환을 허용하지 않는다. 기존 r3의 CRLF file hash와 LF journal hash 불일치는 원시 evidence에 그대로 남기고 별도 correction evidence로 공개한다. | Windows `Path.write_text`가 LF를 CRLF로 변환해 journal의 logical serialization hash와 실제 파일 hash가 달라졌다. Qualification의 별도 source-evidence 결속은 유효하지만 campaign result를 clean checkout에서 byte-for-byte 검증하려면 두 identity가 같아야 한다. |
| D-031 | 새 live model call은 exact logical Responses request와 context-build omission/truncation evidence를 CAS에 먼저 저장하고, `truncation=disabled`를 명시한다. 같은 input/tool/reasoning payload를 input-token-count endpoint로 세어 응답의 `usage.input_tokens`와 turn별로 대조하며, response status·incomplete reason·reasoning token breakdown도 보존한다. 이 telemetry를 선언한 trace는 count mismatch, provider truncation 또는 incomplete response가 있으면 qualification을 통과하지 못한다. 기존 r1~r3 evidence는 새 필드가 없는 legacy trace로 immutable하게 유지한다. | API의 silent input truncation과 PatchLoop context builder가 의도적으로 생략한 evidence를 구분하고, tool schema와 message framing을 포함한 실제 token 사용량을 로컬 문자 수 추정 없이 검증한다. 과거 pilot을 새 계약으로 소급 재해석하지 않으면서 이후 campaign의 prompt integrity를 강화한다. |
| D-032 | D-031 telemetry의 첫 provider 검증은 기존 core 계약을 바꾸지 않는 별도 `development-validation-model-candidate-pilot` purpose로 실행한다. Model은 `gpt-5.4-mini-2026-03-17`, reasoning effort `medium`, default service tier, per-call output 4,096, run total token 90,000과 $2 cap으로 고정한다. GPT-5.4 request에는 GPT-5.6 전용 `reasoning.mode/context`를 보내지 않고 `store=false`, `previous_response_id` 미사용과 durable context rebuild로 stateless boundary를 유지한다. Exact input count와 full response allowance가 남은 run budget에 들어가지 않으면 generation을 시작하지 않는다. 이 purpose의 run은 Terra memory-development campaign의 선행 pilot gate를 충족하지 않는다. | 저가 dated snapshot에서 token-integrity 경로를 먼저 검증하면서 기존 Terra r1~r3와 향후 memory/core 비교 계약을 소급 변경하지 않는다. 90,000은 run 전체 input+output 예산이며 90,000-token 단일 응답을 뜻하지 않는다. |
| D-033 | 새 agent run은 `tool_schema_version=v2`와 `context_policy_version=phase-evidence-v2`를 사용한다. Visible check의 최신 결과와 final `get_diff`는 exact current worktree diff hash에 묶고, complete/untruncated diff result가 바로 다음 model request에 포함된 뒤 `finish_task`를 호출해야 evaluator 제출을 승인한다. `SubmissionAccepted`는 evaluator 진입 승인이지 SCRR 성공이 아니다. 미충족 제출은 두 번까지 structured rejection으로 복구시키고 세 번째에는 `premature-stop`으로 종료한다. Tool 실패 전에는 phase를 전이하지 않으며, mutation은 이전 check/review evidence를 무효화한다. 기존 v1 manifest, replay와 trace는 소급 변경하지 않는다. | `run_d4fea5e7198b4abc`가 patch/check evidence를 만들고도 final review 순서를 놓친 채 `VERIFY → DONE` 전이 오류로 evaluator 전에 끝났다. Prompt 권고만으로 순서를 기대하지 않고 현재 code state와 실제 model-visible evidence를 실행 gate로 만들되, 단일 실수를 즉시 terminal failure로 만들지 않는다. |
| D-034 | v2 `finish_task`는 accepted patch bytes를 CAS에 동결하고 lifecycle, evaluator input과 result artifact ID를 그 artifact에 결속한다. Partial crash는 correlation별 durable prefix와 recoverable action result를 검증해 누락 suffix, DONE transition과 checkpoint event만 보충한다. 현재 v2 campaign preflight는 같은 model/budget/harness commit 및 exact runtime-contract hash의 `trace-qualification-v2` Terra pilot만 허용하며 historical v1 r3는 통과시키지 않는다. | 제출 승인과 evaluator 사이의 mutable-workspace 창, lifecycle 반쪽 기록, 중복 acceptance/transition 및 구 runtime pilot이 새 계약을 승인하는 문제를 함께 닫는다. |
| D-035 | Offline run ownership은 TTL/PID 추정이 아니라 run lifetime 동안 유지되는 Windows/Linux OS advisory lock과 SQLite atomic claim으로 구현한다. v2 patch는 raw input, baseline/expected diff와 touched-file pre/post image를 CAS에 준비한 뒤 all-target preflight와 atomic postimage replace/delete로 mutate하고 action result/outcome/PatchApplied를 한 DB transaction으로 닫는다. Fresh owner는 pre/post/mixed를 결정적으로 reconcile하고 unknown/CAS 손상은 fail-closed한다. Direct OpenAI resume과 paid campaign journal resume은 계속 별도 차단 범위다. | 긴 model/check call을 stale lease로 오인하지 않고 실제 process death에는 커널 lock 해제로 즉시 대응한다. 첫 postimage write와 durable result 사이의 창에서도 duplicate mutation이나 임의 overwrite 없이 같은 run을 복구하며, offline recovery 권한이 paid-call 재개 권한으로 확대되지 않게 한다. |
| D-036 | Evaluator는 unique staging workspace에서 manifest/result/provenance와 verifier evidence CAS를 atomic write한 뒤 hash-bound `evaluation-receipt-v1`을 만든다. Resume은 receipt bundle과 참조된 verifier CAS를 검증하고, v2에서는 accepted submitted-patch CAS까지 검증한 경우에만 evaluator 결과를 재사용한다. Optional `FailureTagged`, terminal event, result와 status는 단일 SQLite transaction으로 확정한다. | Evaluator 성공 뒤 worker가 종료된 경우 expensive/private evaluation을 중복 실행하거나 반쪽 artifact를 신뢰하지 않으면서, terminal state와 verdict의 불일치를 방지한다. Host가 DB와 모든 artifact를 함께 다시 쓰는 공격은 local host trust boundary 밖이며 qualification은 관찰된 source evidence를 tamper-evident하게 묶는다. |
| D-037 | 새 manifest는 `context_policy_version=phase-evidence-v3`로 retry-continuity contract를 활성화한다. Stateless run에서 model이 생성한 mutating-tool argument가 거부되면 바로 다음 model request는 latest rejected candidate의 exact agent-visible bytes, content hash와 structured rejection reason을 함께 포함해야 한다. Candidate가 request budget에 완전하게 들어가지 않으면 generation을 시작하지 않고 structured budget failure로 끝낸다. Qualification은 version을 확인한 뒤 CAS source와 request body를 다시 대조하며 기존 provider state나 agent에게 없는 CAS-read 기능에 의존하지 않는다. 기존 `phase-evidence-v2` trace는 소급 재평가하지 않는다. | Mini r2 `run_4a9737ec91964dca`는 token count, final review, evaluator와 trace qualification을 통과했지만 첫 rejected patch 뒤 request에 hash/error만 남고 patch body가 사라져 stateless continuity가 보장되지 않았다. 이후 제출된 별도 candidate에는 공개 grouping/separator 요구를 훼손하는 결함이 있었지만, trace는 body 누락이 그 결함이나 hidden failure를 일으켰다거나 첫 candidate가 통과했을 것이라는 반사실을 증명하지 않는다. Provider truncation과 PatchLoop context omission을 분리하고 retry continuity를 기계적으로 보장한다. |
| D-038 | D-037 provider diagnostic은 generic trace qualification을 강화하지 않고, `experiment-v2` model-candidate suite의 hash-bound `experiment-diagnostic-v1` block으로 선언한다. Consumer는 `evaluation_reached=true`와 sanitized `rejected_patch_retry_context` evidence의 `retry_episode_count >= 1`, `verified_retry_count == retry_episode_count`, failed source sequence 없음의 논리곱을 검사한다. Evaluator에 도달한 zero-episode run은 `TraceExerciseInconclusive`, evaluator 미도달이나 malformed/partial evidence는 `TraceExerciseFailed`로 분리하고 task outcome 및 generic qualification을 덮어쓰지 않는다. | Rejection이 없는 정상 v3 trace를 qualification failure로 만들지 않으면서도, 비용 승인 대상 run이 실제로 D-037 경로와 evaluator lifecycle을 exercise했는지 기계적으로 확인한다. Requirement를 execution hash에 결속해 승인 뒤 제거할 수 없게 하고 patch/error body 없이 count/sequence만 보고한다. |
| D-039 | Terminal D-037 r3는 immutable evidence로 보존하고 재실행하지 않는다. Corrective r4는 `d037-rejected-patch-retry-v2` profile로 `gpt-5.4-mini-2026-03-17`, medium/default, `max_output_tokens=25,000`, total run budget `120,000`, $2 cap을 함께 고정한다. Historical mini r1~r3의 4,096/90,000과 Terra/core 계약은 그대로 허용한다. Incomplete response 자동 retry는 이번 change에 넣지 않으며, 후속에 도입하려면 original request identity, logical-turn/attempt correlation, crash ambiguity와 qualification pairing을 별도 version으로 고정한다. | R3 `run_e90f7c52aa134182`는 8회 input delivery가 모두 일치했지만 마지막 response가 4,096-token cap 중 3,989를 reasoning에 쓰고 visible tool call 없이 incomplete가 됐다. 공식 [reasoning guide](https://developers.openai.com/api/docs/guides/reasoning#allocating-space-for-reasoning)는 초기 실험에 reasoning+output 최소 25,000 token 예약을 권고하고 [mini model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini)는 max output 128,000을 명시한다. 2026-07-29 suite rate로 계산한 120,000 total + 25,000 allowance의 conservative authorization reserve `$0.6525`는 $2 cap 아래이며, 단순 `continue`가 D-037 latest-model boundary를 넘기는 문제를 피한다. |

D-037은 D-033의 새 non-replay manifest context version만 supersede한다. Tool schema v2,
submission lifecycle과 기존 phase-evidence-v2 artifact의 해석은 그대로 유지한다.

## Provisional defaults

구현을 막지 않기 위해 아래 값을 기본으로 사용한다. 변경은 가능하지만 contract나 실험 비교에 영향을 주면 이 로그에 기록한다.

| Area | Default | Revisit by |
| --- | --- | --- |
| Runtime | Python 3.12+ | P1.1 |
| CLI | Typer | P1.1 |
| Validation | Pydantic v2 + generated JSON Schema | P1.2 |
| Tests/lint | pytest + Ruff | P1.1 |
| MVP metadata DB | SQLite behind repository interface | Persistence implementation |
| Artifact/event MVP | Local filesystem, JSONL/JSON | P1.8/P4 |
| Sandbox | Docker Engine + Python adapter | P1.5 |
| Repository operations | Git CLI adapter | P1.4 |
| Code search | ripgrep | Phase 2 |
| Model integration | Small internal adapter; live provider optional | Phase 2 |
| Retrieval MVP | Metadata filter + simple cosine search | Phase 5 |
| Reporting | JSON/CSV first, HTML later | Phase 6 |
| Frontend | Not selected until Phase 7 | Phase 7 |

## Open questions

열린 질문은 해당 decision deadline 전까지 구현을 막지 않는다. 임시 기본값을 사용한다.

| ID | Question | Why it matters | Decision deadline |
| --- | --- | --- | --- |
| Q-001 | 첫 audited fixture repository를 자체 제작할지 외부 OSS snapshot을 사용할지 | License, realism, reproducibility | P1.3 시작 전 |
| Q-003 | Scope verifier의 diff-line 계산 규칙을 add/delete 합계로 할지 | `max_diff_lines` 재현성 | P1.7 시작 전 |
| Q-004 | Test tampering의 초기 deterministic 범위를 어디까지 볼지 | False positive와 task authoring burden | P1.7 시작 전 |
| Q-006 | Raw trace retrieval candidate pool을 same-repo dev run으로 제한할지 | Fairness와 leakage | Phase 5 시작 전 |
| Q-007 | Similarity embedding을 local model로 고정할지 | Offline reproducibility와 품질 | Phase 5 시작 전 |
| Q-008 | Small-sample bootstrap의 resampling unit을 task로만 둘지, repetition hierarchy를 반영할지 | Confidence interval 해석 | Phase 6 시작 전 |

Q-005는 D-021/D-022로 해결했다. 현재는 `gpt-5.6-terra` alias,
medium/standard/default와 SDK/Git/time provenance를 고정하며, dated snapshot이 공개되면
core freeze 전에 새 decision으로 재검토한다.

## Decision change template

확정 결정을 바꿀 때 기존 행을 지우지 않는다. 새 decision을 추가하고 대체 관계를 적는다.

```text
ID:
Status: accepted | superseded
Supersedes:
Context:
Decision:
Consequences:
Date:
Evidence/issue:
```

## Deferred ideas

다음 항목은 아이디어로만 유지하며 v1 work item으로 만들지 않는다.

- Multi-agent 역할 분리
- Kubernetes/distributed queue
- Full GitHub App/organization permissions
- Multi-language evaluator
- Autonomous harness self-modification
- LLM-only grading/classification
- Enterprise dashboard and access control
