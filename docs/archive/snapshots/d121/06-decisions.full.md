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
| D-040 | Terminal D-037 r4 `run_826c1c7fb3d242c2`와 그 승인 hash는 immutable evidence로 보존하고 재실행하지 않는다. R4는 13개 completed generation으로 r3의 per-call output-ceiling confounder를 제거했지만, REVIEW turn의 exact input 8,583 + full output allowance 25,000이 남은 28,563-token total budget에 들어가지 않아 provider call 전에 종료됐다. 이 generic terminal budget block은 retry candidate가 없으므로 현재 v3 retry 전용 validator에서 valid로 인정되지 않는다. 후속 paid diagnostic 전에 total budget과 response reservation의 관계, rejected retry가 아닌 terminal budget block의 qualification 의미를 새 offline contract와 experiment ID로 고정한다. | 정합한 token telemetry를 mismatch로 오해하거나 단순히 total budget만 올려 동일 suite를 재실행하지 않게 한다. 비용 상한, diagnostic exercise 가능성, generic trace qualification을 함께 설계하고 이미 소비된 approval을 재사용하지 않는다. |
| D-041 | Terminal r4와 unversioned qualification 21/22는 immutable하게 유지한다. 후속 r5는 새 experiment ID와 `d037-rejected-patch-retry-v3` profile로 per-call output 25,000, strict exact-input + full-response reservation과 diagnostic-only total budget 200,000을 함께 고정한다. 200,000은 r4 prefix 91,437에 r4 최대 exact input 10,031 + allowance 25,000의 tail reservation 세 개를 더한 196,530을 올림한 값이다. 새 exact-request no-generation payload는 `model-generation-block-v1`이며, request/budget/terminal binding이 맞는 versioned generic block은 retry와 독립된 valid trace evidence다. 그러나 retry episode나 D-037 gate로 세지 않는다. Historical unversioned retry block은 읽기 호환하고 unversioned generic r4는 소급 통과시키지 않는다. Synthetic rejection, reservation runtime 의미 변경과 automatic retry는 추가하지 않는다. Evaluator에 도달한 zero-episode r5는 inconclusive이고 자동 재실행하지 않는다. | Strict runtime 규칙을 완화하거나 관찰될 때까지 rejection을 인위적으로 만들지 않으면서, r4에서 실제 관찰한 prefix와 세 tail turn으로 diagnostic budget을 사전 산출한다. `(200,000 + 25,000) × $4.50/M = $1.0125` conservative reserve는 $2 cap 아래다. Generic budget exhaustion의 trace integrity와 D-037 exercise 성공을 분리하고, 소비된 r4 승인과 evidence를 재해석하지 않는다. |
| D-042 | Terminal r5 `run_0ad8676d42614fbf`와 승인 hash는 immutable evidence로 보존하고 재실행하지 않는다. 이 run은 18/18 exact input telemetry와 completed response, official hidden/regression/scope/safety pass, `trace-qualification-v2` 23/23을 남겼지만 rejected candidate와 retry episode가 0이므로 `retry_episode_not_observed` inconclusive다. Task 성공과 D-037 provider 검증을 분리하며 Terra gate를 열지 않는다. 다음 작업은 paid retry가 아니라 기존 opportunistic-rejection gate를 유지할지, 별도 version의 controlled diagnostic으로 대체할지 offline에서 결정하고 계약·failure mode·acceptance test를 먼저 고정하는 것이다. | D-041이 사전 선언한 zero-episode terminal 의미와 no-auto-rerun 규칙을 지키고, 성공 task를 diagnostic 성공으로 과장하거나 rejection이 우연히 나올 때까지 비용을 쓰는 selection bias를 막는다. Controlled rejection은 현재 계약에 없는 material change이므로 새 version과 별도 evidence 없이 암묵적으로 도입하지 않는다. |
| D-043 | D-037 provider branch coverage는 별도 `d037-rejected-patch-retry-v4` controlled diagnostic으로 전환한다. V4만 `FaultSpec(type=controlled-reject-first-prepared-patch, trigger_after=1)`을 manifest와 approved execution plan에 결속한다. 첫 preflight-valid `PatchPrepared` 뒤 실제 mutation 전에 `CONTROLLED_DIAGNOSTIC_REJECTION`을 정확히 한 번 durable `ToolFailed`로 기록한다. Invalid candidate는 trigger를 소비하지 않고 crash/resume도 prepared patch를 적용하지 않는다. V4 gate는 controlled rejection 1회, 해당 action `PatchApplied` 0회, exact next-request retry 전체 검증과 evaluator 도달을 요구한다. Direct `inject-fault`, stress/core와 natural-recovery claim에는 사용하지 않는다. | R3-r5처럼 우연한 rejection을 기다리는 반복 paid run과 selection bias를 피하면서 real provider request에서 D-037 harness branch를 결정적으로 검증한다. Prepared preflight가 증명하지 않는 post-mutation full policy pass까지 `valid`라고 과장하지 않고, task 성공과 model의 자연 오류 회복률을 이 controlled result와 분리한다. |
| D-044 | 승인된 r6 execution hash `sha256:d6a756dc69a7cf6e024d541b64a458a940ec41bdfeb3c403a3f01c539660e67b`와 `run_73f5aaf7328a4ea5`를 terminal immutable evidence로 보존하고 재실행하지 않는다. Run은 controlled rejection/verified retry 1/1, rejected action `PatchApplied` 0, evaluator 도달, official hidden/regression/scope/safety와 trace qualification 23/23을 통과했다. 19/19 exact input telemetry와 completed response, 138,262 input + 13,800 output token, 계산상 `$0.1657965`를 기록했다. 이 결과는 D-037 harness branch를 live provider request에서 검증하지만 natural model-error recovery rate, memory benefit 또는 Terra campaign quality를 증명하지 않는다. 결정 당시 후속 paid gate는 별도 clean hash와 승인을 요구하는 tool-v2/context-v3 Terra development-validation pilot이었다. | Controlled intervention의 인과 범위를 넘는 성능 주장을 막고, 소비된 승인/hash를 재사용하지 않으며, mini diagnostic과 Terra/memory campaign의 비교 계약을 분리한다. |
| D-045 | D-034와 D-044의 미래 Terra campaign requirement 및 D-032/D-039/D-041의 “mini는 diagnostic-only” 경계를 supersede한다. 앞으로 development-validation pilot, memory-development와 core 비교는 dated snapshot `gpt-5.4-mini-2026-03-17`, reasoning `medium`, mode `standard`, service tier `default`, `max_output_tokens=25,000`, run total `200,000`을 동일하게 사용한다. Historical Terra와 mini r1-r6 suite/run의 당시 purpose, qualification과 claim boundary는 변경하지 않는다. 새 primary pilot은 fault 없는 `development-validation-live-pilot` purpose와 별도 clean execution hash/$2 승인을 요구하며, historical model-candidate/controlled diagnostic은 이를 대신하지 않는다. 공식 standard list price는 input `$0.75/M`, cached input `$0.075/M`, output `$4.50/M`, 별도 cache-write rate 없음으로 2026-07-29T22:39:42Z에 재확인했다. 보수적 authorization reserve는 run당 `(200,000 + 25,000) × $4.50/M = $1.0125`, 12-run `$12.15`, 96-run `$97.20`이며 기존 $2/$20/$150 cap 안이다. Account의 complimentary/data-sharing 적용은 list-price preflight나 measured cost를 대체하지 않는다. | 사용자가 향후 전체 실험을 더 저렴한 dated mini snapshot으로 실행하려는 의도를 명확히 했고, r5/r6가 4,096/90,000의 output 및 tail-budget confounder 없이 25,000/200,000 경로를 실제 provider에서 완주했다. 실험 중간에 model/budget을 섞지 않고 본 campaign 전에 한 번만 계약을 바꾸며, 비용을 낮추면서 네 memory 조건의 공정 비교를 유지한다. |
| D-046 | 승인된 primary execution hash `sha256:969477ca029570ea61f9fca74fd3aa558f6e16ff9b5be1c7ffa8927ed1139047`과 `run_6993722014bf4e3b`를 terminal immutable evidence로 보존하고 재실행하지 않는다. Run은 20/20 input pre-count 일치와 completed response, patch 적용, visible regression pass, complete final diff와 `REVIEW` 진입을 남겼지만 20 model-call 상한을 모두 사용해 `finish_task`용 다음 generation 전에 `model_call_budget_exhausted`로 끝났다. Evaluator는 실행되지 않았고 primary gate를 열지 않는다. Exact final diff `sha256:9ca2431c14ce0cd5fd49b19710498a7a55a33568c748d3e44fbe794a825e083d`는 별도 no-model Docker postmortem에서 hidden/regression/scope/safety를 모두 통과했지만 이를 원 run의 제출·official success로 소급하지 않는다. Qualification 21/22의 유일한 실패는 token mismatch가 아니라 call-budget terminal block이 versioned valid ending이 아닌 계약 gap이다. 다음 paid retry 전에 offline에서 submission tail-call reserve 또는 공정한 model-call budget을 고정하고, model/tool/wall-call deterministic pre-generation block의 schema·qualification·failure mode를 versioning하며 broad regression을 통과해야 한다. Corrective provider run은 새 experiment ID, clean execution hash와 별도 $2 승인을 요구한다. | Prompt truncation, total-token exhaustion, patch correctness와 call-budget lifecycle을 분리한다. 성공 가능했던 patch라는 postmortem 결과로 미제출 live run을 성공 처리하지 않고, 우연히 한 turn을 더 주는 사후 재실행 대신 네 memory 조건 모두에 적용할 budget/submission 정책을 본 campaign 전에 고정한다. |
| D-047 | Exact-token reservation의 `model-generation-block-v1`은 유지하고, next-generation admission 전에 model/tool/wall counter가 소진된 경우 `model-generation-block-v2`를 사용한다. Qualifier는 exact field set과 strict nonnegative integer, durable call/token/duration 재계산, model/tool 상한, `model → tool → wall` reason 우선순위, `budget-guard` actor, request/retry/terminal/result usage 결속을 검증한다. Unversioned generic primary r1은 소급 통과시키지 않는다. Future primary, memory-development와 core는 모두 총 `max_model_calls=21`을 사용하며 이는 `finish_task` 전용 reserve가 아니다. Historical primary r1과 diagnostic suite는 기존 20-call 계약을 유지하고 모두 preflight-immutable하다. 결정 당시 corrective r2는 새 experiment ID와 clean execution hash, 별도 $2 승인을 요구하는 pending gate였다. | Primary r1이 실제로 20번째 call 뒤 submission-ready 상태에 도달했다는 bounded evidence에 따라 한 call만 공정하게 늘리되, 특정 condition이나 action에 특권을 주지 않는다. V1과 historical trace 의미를 보존하고, next-generation 차단을 deterministic qualified agent-failure로 만들면서 task/evaluator success와 분리한다. |
| D-048 | Consumed corrective r2 `run_afd5080a77a34995`와 12-run `dev-no-memory-20260728`은 immutable evidence로 보존한다. R2는 official evaluator와 qualification 23/23을 통과했지만, 12-run은 evaluator 도달 0/12이고 search 405, read 157, apply 1에 머물러 no-memory 성능 baseline으로 쓰지 않는다. 새 non-replay manifest는 `phase-evidence-v4`를 사용한다. V4는 active `PatchApplied` mutation epoch 이후의 successful read/search input·result CAS에서 `investigation-ledger-v1`을 매 turn 결정적으로 재계산하고 checkpoint schema를 복제하지 않는다. 동일 epoch의 exact search와 fully-covered read는 새 model action/`ToolCalled`/tool budget 1회를 유지하되 filesystem dispatch 없이 verified result CAS를 `ToolReplayed(tool-replayed-v2)`로 semantic replay한다. 두 번째 연속 no-progress부터 `strategy_change_required=true`를 표시한다. Nominal tail은 `4 + 2 × registered_check_count` tool call과 3 model call(+feedback 1)을 제시하며, threshold 이후 read/search는 `ToolAdmissionBlocked`로 admission 전에 닫아 `ToolCalled` budget을 소모하지 않는다. Apply/check/diff/finish는 차단하지 않는다. V4 qualifier는 각 request ledger와 rendered context를 preceding event/checkpoint/CAS에서 재계산한다. V1-v3 rendering, hashes와 qualification은 소급 변경하지 않는다. 새 v4 pilot과 후속 campaign은 각각 새 experiment ID, clean hash와 별도 승인을 요구한다. | 12개 run 모두 충분한 token/wall budget을 남긴 채 model/tool call cap에서 종료했고, 562개 inspection 중 216개 exact 비연속 중복과 추가 60개 fully-covered read가 관찰됐다. 단순 budget 증가나 cross-run memory는 이 condition-neutral within-run 상태 손실을 고치지 못한다. Repository observation만 보존하고 model-authored hypothesis나 solution memory를 추가하지 않아 네 memory 조건의 공정 비교를 유지한다. |
| D-049 | 승인된 v4 execution hash `sha256:cc2117dc698cdc991ccbcad45bbcfa4302f1ac265bdfdcc0753b60b2fda6eba2`와 `run_d7207fbb06184dd3`를 terminal immutable evidence로 보존하고 재실행하지 않는다. Run은 10/10 exact input telemetry, completed responses, 자연 rejected-patch retry 1/1, official hidden/regression/scope/safety와 `trace-qualification-v2` 25/25를 통과했다. 81,719 input + 5,952 output token, 계산상 `$0.08807325`를 기록했다. `investigation_evidence`와 `investigation_lifecycle`은 v4 ledger 10/10과 mutation-epoch 전환을 검증했지만 semantic replay와 tail admission block은 각각 0회였다. 이 run ID는 새 12-run v4 no-memory suite의 pilot gate로만 사용하며 memory 효과, baseline 성능이나 core 결과로 해석하지 않는다. 후속 campaign은 새 clean no-call preflight hash와 별도 최대 $20 승인을 요구한다. | V4 context/ledger를 실제 provider·evaluator 경로에서 검증한 범위와, 이번 trace가 exercise하지 않은 semantic replay/tail-admission branch의 offline evidence 범위를 분리한다. 성공한 한 task를 campaign 성능으로 과장하지 않고 소비된 hash의 재사용과 자동 paid 실행을 막는다. |
| D-050 | Pilot/current harness commit의 exact equality는 완화하지 않는다. Branch가 pilot 뒤로 진행된 상태에서 campaign은 clean detached worktree를 exact pilot commit `5045e398646ec73d615785aeb95f02e877c34c90`에 만들고, ignored `.patchloop` junction으로 host의 external runtime root를 공유하는 `exact-pilot-commit-detached-worktree-v1` bridge를 사용한다. 이 root에는 mutable SQLite와 workspaces도 포함되고 append-only는 event/artifact evidence history의 계약이다. 실행 suite는 frozen template에서 `pilot_run_id: run_d7207fbb06184dd3` binding만 다르며, source import와 모든 RunManifest는 detached commit을 기록한다. 이 bridge도 새 no-call preflight hash와 별도 승인을 요구하고 descendant compatibility나 dirty-tree 허용으로 해석하지 않는다. | Pilot qualification이 증명한 exact runtime code를 유지하면서 이미 진행된 문서/evidence branch를 되돌리거나 equality gate를 느슨하게 만들지 않는다. External runtime-root 공유는 evidence continuity를 위한 host boundary이고 source, private oracle 또는 credential을 agent container에 전달하지 않는다. |
| D-051 | `dev-no-memory-v4-20260730-r1` execution hash `sha256:9befd0bf8b2eb7dbc25999786713581b4b6c95f2ad45df56e2f098a9252e5bac`는 D-050 bridge에서 정확히 한 번 소비됐고 재실행하지 않는다. 12/12 terminal, infrastructure/qualification/diagnostic error 0, trace qualification/leakage pass 12/12지만 SCRR은 0/12다. 아홉 run은 exact next input과 full 25,000-token response allowance가 남은 200,000-token budget에 함께 들어가지 않아 evaluator 전에 agent failure가 됐고, 세 run은 regression/scope/safety를 통과한 submitted patch가 hidden acceptance에 실패한 task failure다. Executed 144 request의 input count와 provider usage는 144/144 일치하고 incomplete/truncation은 0이다. Semantic replay 26회와 rejected retry 11/11은 관찰됐지만 `ToolAdmissionBlocked`는 0회다. Campaign 계산 비용은 `$1.84756425`, 전체 누적 list-price는 `$4.981546875`다. 이 결과는 completed failure-trace collection이지만 usable no-memory performance baseline이 아니다. 아홉 budget-confounded trace는 memory에서 제외하고 세 task failure만 hidden detail 없이 두 semantic group으로 provisional review한다. Index freeze와 core는 token-aware corrective-tail offline gate, structured self-review/deduplication, 새 runtime pilot과 새 12-run hash 뒤까지 보류한다. | Strict exact accounting을 prompt truncation이나 infrastructure failure로 오해하지 않고, 0/12를 task difficulty 또는 memory 효과의 baseline으로 과장하지 않는다. Machine eligibility와 human-reviewed index admission을 분리하고, 동일 승인/hash 재사용이나 사후 budget 변경 없이 runtime confound를 먼저 닫는다. |
| D-052 | D-045의 future total-token/cost 부분, D-048의 current-runtime designation과 D-051의 pending token-tail gate만 supersede한다. Future development-validation, memory-development와 core는 `gpt-5.4-mini-2026-03-17`, medium/standard/default, `phase-evidence-v5`, `21 model call / 50 tool call / 250,000 total token / 900초`, `max_output_tokens=25,000`을 모든 memory 조건에 동일하게 사용한다. Projection은 durable `ModelCalled`의 `requested_input_tokens`를 우선하고 값이 `None`일 때만 actual `input_tokens`로 fallback하며 invalid 값은 fail closed한다. `projected_next_input = max(observed input) + max(0, maximum positive consecutive growth)`, generation 전/후 `projected_turns=5/4`, `reserved_tokens = max_output_tokens + projected_next_input × projected_turns`로 계산하고 `remaining_tokens <= reserved_tokens`이면 equality를 포함해 read/search만 `token_tail_reserved`로 `ToolCalled`와 dispatch 전에 차단한다. Apply/check/diff/finish와 strict exact-request + full 25,000 response guard는 유지한다. 이 cutoff는 nominal policy이며 completion guarantee가 아니다. 새 schema는 `investigation-policy-v2`, `investigation-ledger-v2`, `investigation-tail-policy-v2`, `context-build-evidence-v5`, `tool-admission-blocked-v2`, `trace-source-evidence-v5`이고 qualification envelope은 `trace-qualification-v2`를 유지한다. 21/200,000 계약으로 소비된 `dev-validation-gpt54mini-campaign-20260730-r2`, `dev-no-memory-20260728`, `dev-validation-gpt54mini-investigation-v4-20260730-r1`, `dev-no-memory-v4-20260730-r1`은 immutable하다. Future template은 `experiments/dev-validation-gpt54mini-token-tail-v5-pilot-r1.yaml` (`dev-validation-gpt54mini-token-tail-v5-20260730-r1`), `experiments/dev-no-memory-v5.template.yaml` (`dev-no-memory-v5-20260730-r1`)와 `experiments/core.template.yaml`이며 provider call은 실행하지 않았다. Frozen repository rate의 authorization reserve는 run당 `$1.2375`, 12-run `$14.85`, 96-run `$118.80`; measured `$4.981546875`와 세 future reserve의 수동 합은 `$139.869046875`다. Reserve는 spend/invoice prediction이 아니며 project-wide `$150` cap은 machine-enforced가 아니고 suite별 `cost_limit_usd`만 강제된다. | D-051의 9/12 exact-budget terminal failure를 prompt truncation이나 task 난이도로 오해하지 않으면서, exploration을 condition-neutral하게 줄이고 patch/check/review tail에 더 많은 nominal 여유를 둔다. 기존 200,000-token evidence를 사후 예산 변경으로 재해석하지 않고, 새 runtime·budget을 별도 v5 pilot과 새 execution hash로 검증하기 전까지 성능 baseline이나 memory 효과를 주장하지 않는다. |
| D-053 | `memory-review-proposal-v1`은 human approval 전 read-only, hash-bound review artifact다. Campaign candidate/exclusion exact coverage, current failure/qualification/source/public-spec/submitted-patch/event provenance와 semantic-group membership을 검증한다. Producer는 `maintainer-assisted`와 exact model/response artifact가 결속된 `model-self-review`를 구분한다. Public evidence로 causal claim을 뒷받침하는 group만 candidate이며 불확실한 group은 hold한다. Proposal validation은 `failure-review` history나 index를 쓰지 않으며, append-only approval과 group-aware builder가 구현되기 전에는 memory gate를 통과하지 않는다. | D-051의 세 task failure를 목표 개수에 맞춰 억지로 rule로 만들거나 maintainer 분석을 agent self-review로 과장하지 않는다. Tox 두 repetition은 하나의 candidate로 deduplicate하고, 공개 evidence로 원인을 특정할 수 없는 Loguru source는 hold하면서 raw/private solution 누출과 자동 self-approval을 함께 막는다. |
| D-054 | Cross-run memory human admission과 index build를 보류하고 no-memory runtime completion을 먼저 calibration한다. D-052의 실행되지 않은 250k single pilot은 `superseded-unexecuted`로 보존하고 preflight에서 차단한다. 새 `development-validation-live-pilot`은 Babel control과 Moto harder completion probe를 각각 1회, `no_memory`, `gpt-5.4-mini-2026-03-17`, medium/standard/default, `40 model call / 100 tool call / 600,000 total token / 1,800초`, per-call output 25,000으로 실행한다. 2026-07-30T22:25:47Z에 재확인한 standard rate input `$0.75/M`, cached input `$0.075/M`, output `$4.50/M`에서 conservative reserve는 run당 `$2.8125`, 두 run `$5.625`, suite cap `$6`다. `no-memory-completion-gate-v1`은 2/2 terminal·qualified·official evaluator arrival, infrastructure/qualification/budget terminal 0을 요구하지만 SCRR 성공은 요구하지 않는다. 480k token/32 model/80 tool/1,440초의 20% panel headroom은 후속 fair-budget 검토의 필요조건일 뿐 충분조건이 아니다. Memory-development/core의 250k template은 calibration 결과 전까지 pending draft로 남으며 어떤 memory 조건도 실행하지 않는다. | V4의 0/12는 아홉 exact-request budget failure가 섞인 diagnostic이라 memory 효과 baseline이 아니다. 먼저 작은 development-validation 표본에서 agent가 evaluator까지 끝까지 갈 수 있는지를 task correctness와 분리해 확인해야 한다. 높은 ceiling은 진단용이며 core 예산으로 자동 승격되지 않고, 결과를 본 뒤 모든 memory 조건에 동일한 최종 예산과 비용을 다시 동결한다. |
| D-055 | D-054 suite를 commit `59621ec`, Docker image digest, SDK 2.47.0과 execution hash `sha256:444cd7f2d00b3925a1227d1e9fc0436c68ba9700005b8416572c5fd654de1f78`에 결속해 정확히 한 번 실행했다. Babel `run_685c492e34f84fef`와 Moto `run_0814be408332479e`는 모두 official hidden/regression/scope/safety, qualification 25/25와 completion/headroom gate를 통과했다. Budget/infrastructure/qualification error는 0이고 총 사용량은 172,249 input + 6,142 output token, 계산 비용은 `$0.15682575`다. 19/19 exact input count가 provider usage와 일치했고 모든 response는 completed/truncation-disabled였다. Result hash는 `sha256:a540ff52f271cd22c58ca561e559d9608ac50b99889a523f8a9a3d80cf8822ba`다. Suite/approval/run은 immutable로 닫고 재실행하지 않는다. 이 n=2 결과는 runtime ceiling evidence일 뿐 6-task baseline이나 memory/core budget evidence가 아니다. 다음 provisional calibration 후보는 480k token을 쓰되 40 model/100 tool/1,800초 counter ceiling은 유지한 resource-stratified memory-development 3-task no-memory panel이다. Exact task는 immutable V4 budget-terminal run에서 total-token과 wall-clock 최대를 모두 기록한 pyfakefs, model-call 최대 PDM, tool-call 최대 HF Hub로 고정하고 tie는 task ID 오름차순으로 푼다. 별도 config/hash/비용 승인이 필요하다. | 600k ceiling이 budget termination 없이 끝까지 실행할 수 있음을 확인하면서도, 한 번에 token·call·tool·wall 축을 모두 줄이거나 두 development-validation 성공을 전체 dataset과 memory 조건에 일반화하지 않는다. 480k는 calibration 후보일 뿐 96-run core에 적용하면 보수적 reserve가 `$218.16`이므로 현재 `$150` 계획과 양립하지 않는다. Final comparison/core budget은 새 development evidence와 전체 비용계획을 함께 다시 freeze한다. |
| D-056 | Visible check 통과만으로 곧바로 제출하는 경로를 보완하기 위해 `tool_schema_version=v3`/`context_policy_version=phase-evidence-v6` self-validation을 explicit opt-in으로 추가한다. `run_probe`는 repository 밖 source를 official Docker sandbox에서만, target checkout read-only·network/secrets/private mount 없음으로 실행하는 optional 비권위 진단이다. Probe나 새 test file을 매 run에 강제하지 않고 registered check를 대체하지 않는다. `review_task`는 current-diff final `get_diff`와 exact request에서 실제로 본 public check/optional probe evidence를 인용하고 requirement·residual risk를 구조화하는 inspectable self-attestation이다. Review는 deterministic grader나 hidden predictor가 아니며, 제출 뒤 separate evaluator의 hidden/regression/scope/safety conjunction만 primary verdict다. V3/V6은 probe/review CAS, request/diff/submission binding, recovery, leak scan과 v1-v5 byte stability offline gate가 닫히기 전 live/pilot/campaign에서 금지한다. 기존 manifest, trace와 qualification을 소급 해석하지 않으며 future live 사용도 별도 suite/hash/비용 승인 없이는 금지한다. | SWE-style agent가 visible tests 외에 issue-derived edge case를 능동 점검할 수 있게 하되 unrestricted shell, repository test pollution, 자기채점과 same-run hidden feedback을 도입하지 않는다. 새 lifecycle을 versioning해 historical evidence와 frozen comparison을 보존하고, 구현 중인 기능을 live 성능 개선으로 과장하지 않는다. |
| D-057 | D-056의 probe sandbox/image/profile 세부를 supersede한다. `run_probe`는 `task-public-v2`의 bounded registered profile이 있을 때만 사용할 수 있고 input은 `probe_id + source`다. 기존 v1 task는 빈 `probe_profiles` field조차 거부하며 canonical dump/hash가 바뀌지 않는다. Probe는 task evaluator/SWE-bench image가 아니라 repository-free `patchloop-sandbox:py312`에서만 실행하고 strict image ID를 manifest에 결속한다. Read-only checkout/root, masked real `.git`, network none, cleared proxy variables, non-root, cap-drop, no-new-privileges, container-side timeout, bounded output과 stale-container cleanup의 canonical policy를 result/event/qualification에 동일하게 결속한다. Interrupted probe는 자동 재실행하지 않고 fatal recovery evidence로 닫는다. V6은 mandatory review를 위해 V5보다 nominal model/tool tail을 각 1개 추가 예약하며 V5 evidence는 유지한다. `review_task` result는 canonical review 본문을 다음 finish request에 재제시하고, 이후 같은 diff의 probe/check/diff는 review를 무효화한다. OpenAI start/resume은 별도 future decision 전 코드에서 거부한다. | Evaluator image 내부 `/testbed`나 Git history, Docker proxy credential과 worker-death container가 agent-visible side channel이 되지 않게 한다. Task가 등록하지 않은 executable diagnostic을 금지해 constrained-execution invariant를 유지하고, receipt만 재제시하는 형식적 review가 아니라 실제 stateless self-review 본문과 최신 validation 순서를 검증한다. |
| D-058 | 2026-07-31 현재 source로 `patchloop-sandbox:py312`를 다시 빌드하고 image ID `sha256:268495717da1396e3413ce6695063c9516202b4e38cb8042f2f181420b64e9c1`을 확인했다. Docker Desktop 4.83.0 / Engine 29.6.2에서 network 차단, non-root/read-only/secret 차단과 probe 전용 Git/evaluator-path/proxy 차단의 실제 container E2E 3/3이 통과했고 잔존 labeled container는 0이다. 전체 회귀는 704 collected, 702 passed/2 Windows symlink-capability skipped다. 비용 없는 v1-task mock smoke `run_36f90bda91b94d42`는 review-only v3/v6 lifecycle, official hidden/regression/scope/safety와 `self_validation_lifecycle`을 통과했으며 model cost는 `$0`이다. 이 evidence는 Docker isolation과 offline lifecycle gate만 닫고 profile-bearing task의 full agent probe 선택, OpenAI provider 또는 memory/core 효과를 증명하지 않는다. | Sandbox 내부 CLI/WSL 조회의 false negative로 실제 host 상태를 오판하지 않고, mock command construction만으로 security boundary를 닫지 않는다. 동시에 review-only smoke와 real probe E2E의 증명 범위를 분리하고 별도 live suite/hash/비용 승인 전 OpenAI start/resume fail-closed를 유지한다. |
| D-059 | 동결 dataset 밖에 infrastructure-only `task-public-v2` fixture `csv-quoted-newline@2`를 두고 registered `quoted-newline-case` profile의 full agent lifecycle을 검증한다. Public/private spec hash는 각각 `sha256:e72110791ac062f719a26c5b3d68d32152a5d82ede75a9971f667138f9bde926`와 `sha256:c1727483c0a496cde1765a55204b922ca7874973b937a2d9658121b5c938099c`다. 비용 없는 final mock CLI run `run_7e3c5af2ce8d498a`는 clean image `sha256:268495717da1396e3413ce6695063c9516202b4e38cb8042f2f181420b64e9c1`에서 probe event 33 `probe-ok`를 만들고, 같은 diff review가 그 event를 인용한 뒤 official hidden/regression/scope/safety와 `self_validation_lifecycle`을 통과했다. 전체 회귀는 708 collected, 706 passed/2 Windows symlink-capability skipped다. Frozen manifest는 25 task/candidate 0으로 그대로다. Mock/non-campaign 전체 qualification은 의도대로 19/26 false이며 live provider 또는 leak-safe campaign qualification으로 세지 않는다. | Profile 등록과 Docker isolation을 각각 따로 검증하는 데서 멈추지 않고 실제 agent 선택→probe result→review citation→submission/evaluator chain을 닫는다. 동시에 쉬운 infrastructure fixture를 research dataset에 섞거나 mock success를 live 성능·memory 효과로 과장하지 않는다. |
| D-060 | 다음 no-memory calibration은 별도 `memory-development-no-memory-budget-pilot` purpose로 표현한다. Exact task는 immutable V4 budget-terminal 모집단의 resource maxima에서 HF Hub/PDM/pyfakefs로 고정하고 `no_memory` 각 1회, tool v2/context v5, `40 model / 100 tool / 480,000 token / 1,800초`, output 25,000을 사용한다. 선행 pilot requirement는 적용하지 않고 qualification은 세 task 전체 plan/schedule을 다시 계산한다. `no-memory-budget-pilot-gate-v1`은 3/3 terminal·qualified·official evaluator arrival와 budget/infrastructure/qualification/diagnostic error 0을 요구하되 SCRR는 요구하지 않는다. 이 purpose는 memory candidate와 comparison denominator에서 제외되고 성공도 memory admission을 자동으로 열지 않는다. Frozen rate reserve는 run당 `$2.2725`, 총 `$6.8175`, suite cap `$7`다. Checked-in suite는 paid 권한이 아니며 clean commit, 실제 Docker identity, SDK, 72시간 내 가격을 결속한 새 execution hash와 별도 승인이 필요하다. | 기존 6-task×2 baseline purpose를 약화하거나 provisional failure를 memory source로 오염시키지 않고, D-055의 작은 development-validation 표본을 resource-heavy memory-development 표본에서 먼저 검증한다. Dirty source bytes를 결속하지 않는 hash를 승인하지 않으며, calibration completion과 task correctness·memory 효과를 계속 분리한다. |
| D-061 | Commit 전 security audit에서 D-057 probe가 manifest image ID를 기록하면서 실제 `docker run`은 mutable tag로 시작하는 inspect/run race와, agent source가 container 내부 process primitive를 직접 호출할 수 있는 계약 gap을 발견했다. Probe는 tag identity를 manifest ID와 precheck한 뒤 exact `sha256:...` ID로 container를 create하고 실제 container `.Image` equality를 확인해야만 start한다. AST/audit hook은 common direct call의 defense-in-depth일 뿐 reflection과 subinterpreter에 대한 security boundary로 주장하지 않는다. Repository-free trusted PID 1이 source를 compile한 뒤 untrusted child를 정확히 한 번 fork하고, child에 `no_new_privs`와 `seccomp-bpf-v1`을 설치해 fork/clone/exec, parent signal과 process trace syscall을 kernel에서 `EPERM`으로 거부한다. PID cgroup은 parent+child 두 개로 제한한다. 이 hardening은 opt-in tool v3/context v6에만 적용하며 D-060의 frozen tool v2/context v5 suite나 historical trace를 소급 변경하지 않는다. | Manifest-bound identity가 단순 사후 receipt가 아니라 실행 전 authorization boundary가 되게 하고, Python-level hook 우회를 솔직히 인정하면서 bounded diagnostic이 unrestricted container shell로 변하는 것은 kernel policy와 test로 차단한다. |
| D-062 | D-060은 immutable하게 보존한다. Read-only 재집계에서 HF Hub는 438,483/480,000 token 뒤 exact next request에 5,171 token이 부족했고 v5 동일-prefix exploration 유지 최소는 658,739였다. PDM과 pyfakefs는 각각 153,702와 252,066 token에서 끝나 budget dimension이 bind하지 않았다. 후속 corrective lane만 `tool_schema_version=v4`/`phase-evidence-v7`로 올린다. V7은 공개 issue excerpt만 허용하는 hash-bound checklist와 `task-review-v2`, 숫자 hunk 진단, rejected candidate source snapshot 및 다음 apply outcome까지의 persistence, 첫 apply 뒤 같은 model response의 나머지 call을 durable barrier로 닫는 정책과 resume reconciliation, active mutation epoch당 semantic replay 6회 saturation을 추가한다. 새 `memory-development-no-memory-corrective-pilot`은 같은 HF Hub/PDM/pyfakefs를 no-memory 1회씩, `40 model / 100 tool / 900,000 token / 1,800초`, output 25,000으로 고정한다. Frozen rate의 worst-case reserve는 run당 `$4.1625`, 총 `$12.4875`, suite cap `$13`다. 이 panel은 tuning evidence이며 comparison baseline, memory admission과 core budget을 열지 않는다. 승인 execution hash `sha256:464a6eca2597698ca35caa4d7c97173f1af792daec042c36d81b5b8189ae4031`는 정확히 한 번 소비됐다. HF `run_0ccfc8fd359a4785`만 terminal에 도달한 뒤 original qualification failure가 campaign을 fail-closed했고 PDM/pyfakefs는 not-started다. HF는 33개 completed call, 875,908 token, `$0.8408853` 뒤 exact-budget block으로 끝났고 patch prepared/applied와 evaluator 도달은 0이다. Original result/journal/qualification과 false gate는 immutable하며 suite/hash를 재실행하지 않는다. Qualifier v5-vs-v6/v7 reserve drift는 append-only correction `qcor_8b6ff812...4870b6`로 corrected trace qualification을 통과했지만 original gate와 task outcome은 변경하지 않는다. 다음 gate는 historical v7을 바꾸지 않는 `phase-evidence-v8` saturation-context offline evidence와 새로 승인된 single live pilot이다. | 700k는 v7 projection의 동일-prefix 최소 697,790보다 2,210 token만 커 새 prompt/checklist overhead에 취약하다. 실제 900k run에서는 saturation이 context allowed action에 반영되지 않아 read/search 30회가 차단되면서도 15 model turn을 소비했고, 이후 raw diff 일곱 개가 preview에서 거부됐다. 따라서 이 결과는 budget 증액만의 평가도, SCRR/no-memory baseline도 아니다. 확인된 context-policy gap을 단일 변경으로 검증한 뒤에만 patch interface나 cross-run memory를 별도 결정한다. |
| D-063 | D-062/v7 artifact는 byte-stable historical evidence로 보존하고 별도 `tool v4/context phase-evidence-v8` offline opt-in을 만든다. V8은 active mutation epoch 뒤 semantic replay 6회를 `phase-contract-v3.read_search_policy`에 반영해 다음 context의 read/search action을 제거한다. Saturation-only에서는 registered probe를 유지하고 tail closure에서는 probe까지 제거한다. Runtime/context/source evidence는 각각 `corrective-runtime-contract-v2`, `context-build-evidence-v8`, `trace-source-evidence-v8`로 versioning하며 qualifier는 runtime builder와 독립적으로 epoch/count/reason/action을 재계산한다. V8 manifest는 우선 mock/no-experiment만 허용하고 live purpose, suite, hash와 비용 승인은 offline regression 뒤 별도 change로 둔다. | Gateway가 거부하는 action을 model context가 계속 권장하는 불일치를 직접 제거하면서 prompt, tool schema, patch interface와 cross-run memory를 바꾸지 않아 인과를 좁힌다. Historical v7을 고치거나 기존 corrective purpose를 완화하지 않고 provider 권한이 우연히 열리는 것도 막는다. |
| D-064 | 새 `memory-development-no-memory-saturation-pilot`만 exact OpenAI V8 exception으로 허용한다. Suite는 HF Hub `hf-hub-xet-endpoint-propagation` 한 task, `no_memory` 1회, `gpt-5.4-mini-2026-03-17` medium/standard/default, 40 model/100 tool/900,000 token/1,800초와 output 25,000으로 고정한다. Runtime v2, public review contract, frozen task/evaluator/image/SDK/commit/가격과 schedule을 새 execution hash에 결속한다. Trace qualification은 V8 구조 무결성을 판정하고 별도 `v8-saturation-context-v1` diagnostic은 saturated context의 read/search 제거와 이후 successful patch의 mutation-epoch reset이 자연 관찰됐는지를 pass/inconclusive/fail로 분리한다. Run이 inconclusive여도 자동 재실행하지 않는다. Worst-case reserve는 `$4.1625`, suite cap은 `$5`이며 checked-in YAML과 no-call preflight는 paid 권한이 아니다. 이 purpose는 SCRR headline, comparison denominator와 failure-memory admission에서 제외한다. | D-062를 계속하거나 목적을 완화하지 않고 관찰된 HF 경로 하나에서 D-063의 live behavior만 좁게 검증한다. Stochastic branch 미관찰을 trace corruption으로 오판하지 않으며, task success와 policy-exercise 성공도 분리한다. 새 clean execution hash와 사용자의 별도 비용 승인이 있기 전에는 provider 호출을 계속 차단한다. |
| D-065 | D-064 execution hash `sha256:dcade27f9f89efd6c349db58cbe732c0c81f1bbaf3bbb05e6c14b4ca62f2b85c`는 정확히 한 번 소비됐고 experiment ID를 historical immutable set에 추가한다. `run_45e3edc434d749f7`은 qualification 30/30과 saturation seq 101, post-saturation patch seq 106, reset context seq 110으로 V8 diagnostic을 통과했다. 그러나 14회 `review_task` rejection 뒤 model calls 40/40에서 generation 41 전에 종료되어 제출과 evaluator 도달은 0이고 completion gate는 false다. 618,370 input + 41,003 output, 총 659,373 token, 64 tool call, `$0.6140766`을 기록했다. Raw artifact는 local hash로 결속하고 sanitized report만 check in한다. D-064를 재실행하거나 hash를 재사용하지 않으며, 다음 변경은 current-diff passing check와 diff evidence를 REVIEW context에 유지하고 반복 rejection을 구조적으로 차단하는 offline correction으로 제한한다. | Live 결과는 V8 policy exercise를 검증했지만 task completion 실패 원인은 token ceiling이 아니라 review-evidence presentation loop와 model-call ceiling의 결합이었다. Model-call 상한 증액이나 cross-run memory를 먼저 적용하면 원인을 섞으므로, review evidence lifecycle을 먼저 고친 뒤 새 purpose/hash/cost 승인을 별도로 판단한다. |

| D-066 | D-064의 immutable V8 trace를 소급 변경하지 않고 exact `tool v4 / phase-evidence-v9` correction을 추가한다. `SYSTEM_PROMPT_V6`는 REVIEW citation authority를 top-level `review_evidence`로 제한한다. `review-evidence-v1`은 latest mutation의 required current-diff passing checks와 final `get_diff`를 recent-event 12개 창 밖에 pin하고, full untruncated tool result와 artifact CAS를 request/execution context에 결속한다. Gateway는 stale/forged/wrong-diff citation을 `review-citation-error-v1`의 exact citable sequence로 거절한다. 같은 active mutation epoch의 세 번째 failed `review_task` 뒤에는 추가 generation 전에 terminal로 닫고 successful patch가 새 epoch를 시작하면 count를 reset한다. Runtime/context/source schema는 `corrective-runtime-contract-v3`, `context-build-evidence-v9`, `trace-source-evidence-v9`이고 qualifier의 `review_evidence_context_contract`는 anchor와 CAS를 independently rebuild한다. Historical V1-V8은 재렌더링하지 않는다. 집중 회귀는 504 collected, 502 passed/2 skipped, full regression은 879 collected, 872 passed/7 environment-dependent skipped로 통과했으며 provider call은 없다. | D-064는 total-token ceiling이 아니라 recent-event eviction과 stale citation 반복이 40-call ceiling을 소모한 사례다. Current-diff evidence 전달을 versioned contract로 고쳐 원인을 분리하고, 구조화된 retry information과 finite loop guard를 두되 review를 hidden grader나 task-success 보증으로 만들지 않는다. |
| D-067 | D-067 결정 당시 D-066 offline gate 뒤에만 고려할 별도 `memory-development-no-memory-review-evidence-pilot` purpose와 checked-in suite를 만든다. Exact HF Hub task 한 개, `no_memory`, `gpt-5.4-mini-2026-03-17` medium/standard/default, v4/v9/runtime-v3, 60 model/100 tool/1,200,000 total token/1,800초, output 25,000으로 고정한다. Dated standard output rate를 사용한 conservative reserve는 `$5.5125`, suite cap은 `$6`다. 당시 source YAML은 `live_cost_approved=false`, execution hash와 pilot run ID null이며 clean no-call preflight도 pending으로 고정했다. `v9-review-evidence-live-pilot-gate-v1`은 terminal·qualified·official evaluator arrival를 요구하지만 task success는 요구하지 않고 comparison denominator와 memory admission을 항상 false로 둔다. 별도 clean execution hash와 사용자의 명시적 비용 승인 전 provider call을 금지한다. | D-064의 40-call ceiling은 실제 binding dimension이었으므로 당시 future one-row completion diagnostic에 여유를 주되, 증액을 V9 correction의 효과나 core budget으로 미리 해석하지 않는다. YAML·preflight·hash·승인을 분리해 사용자가 요청한 상한 확대가 기존 hash 재사용이나 자동 paid execution으로 이어지지 않게 한다. |
| D-068 | D-067 승인 hash `sha256:f1b7d78243af8c87e3ec83f9373312f171073e0713a23fbc51c909fac0be6982`는 정확히 한 번 소비됐다. `run_4c77b1102e224785`는 official evaluator에 도달했지만 hidden acceptance가 실패해 `task_failure`, SCRR=false다. Original qualification 32/33과 false campaign gate는 immutable하다. V9 common submission qualifier가 pinned final diff를 recent-events 밖에서 인정하되 request/source CAS, exact integer sequence와 exact-one nested/top-level presentation을 검증하도록 고친다. Append-only correction `qcor_51b72504161eddf250e872cc533dbfc5a315c377971e8a6f19a74a380fe3c032`은 corrected trace qualification 33/33을 기록하지만 original artifact, task outcome, SCRR, comparison eligibility, memory admission과 campaign gate를 바꾸지 않는다. D-067과 hash는 재실행·재사용하지 않는다. | D-067은 344,754/1,200,000 token과 21/60 model call에서 종료되어 budget이 binding 원인이 아니었다. 따라서 추가 budget이나 cross-run memory보다 qualification 해석을 append-only로 바로잡고 hidden-acceptance task failure의 원인과 requirement coverage를 public evidence만으로 분석하는 것이 원인 분리에 맞다. |
| D-069 | D-067의 broad quantified public requirement를 runtime keyword 추측으로 판정하지 않고 maintainer-authored `public-review-contract-v2`의 explicit `coverage_targets`로 분해한다. 각 target은 latest patch/current diff에 결속된 exact path+anchor `current_diff_inspection` 또는 advertised passing visible `run_check`만 evidence로 허용한다. Inspection anchor는 model context 전에 Git public base에 존재해야 하며 `public-review-base-provenance-v1` CAS로 start/resume/qualification/source hash에 결속한다. Exact `tool v5 / phase-evidence-v10`은 `SYSTEM_PROMPT_V7`, `review-evidence-v2`, `task-review-v3`, `public-review-coverage-v1`, `phase-contract-v4`, `context-build-evidence-v10`, `corrective-runtime-contract-v4`와 `trace-source-evidence-v10`을 사용한다. 모든 requirement/target을 정확히 한 번 평가하고 parent status/evidence를 child target에서 canonical roll-up한다. Valid partial review는 append-only evidence로 보존한 뒤 `REVIEW → IMPLEMENT`로 전이하며, same-diff authoritative target이 모두 verified되기 전에는 `finish_task`를 거부한다. Check/read event metadata와 CAS result semantics, finish recovery provenance, optional probe lifecycle과 non-vacuous complete-review/submission/evaluation을 독립 검증한다. V10은 `coverage_review_validation=True`의 mock/no-experiment 전용이고 live/provider/replay/experiment를 fail closed한다. V1-V9 serialization과 artifact를 소급 변경하지 않고 D-067 run/hash를 재사용·재실행하지 않는다. Checked-in HF Hub V2 sidecar도 live suite, frozen dataset 변경 또는 correctness label이 아니다. Offline gate는 971 collected, 964 passed/7 environment-dependent skipped, Ruff와 `git diff --check`로 완료했고 provider call은 없었다. | V9는 check와 final diff가 model에 전달됐음을 증명했지만 “every metadata access path” 같은 문장을 단일 requirement row와 한 passing check만으로 verified 처리할 수 있었다. 선언된 경로와 behavior clause를 target 단위로 드러내면 빠진 public review evidence를 구조적으로 교정할 수 있다. 다만 target 목록의 완전성과 anchor/visible-check의 의미적 충분성은 maintainer 책임이며, coverage completion은 hidden acceptance, task correctness, SCRR 또는 memory 효과를 보증하지 않는다. |

D-066 selector boundary는 offline에서 `review_evidence_validation=True` + mock provider +
experiment 부재만 허용하고 replay, arbitrary provider, experiment 및 mixed validation mode를
fail closed한다. Live V9은 exact D-067 purpose + OpenAI provider 조합만 허용하며 별도 approved
execution plan 없이는 start/resume할 수 없다.

D-069 selector는 이 live V9 exception을 확장하지 않는다. V10은 exact
`coverage_review_validation=True` + mock provider + experiment 부재만 허용한다. V2 sidecar를
작성하거나 V10 offline qualification을 통과해도 paid execution capability, D-067 재실행 권한,
comparison eligibility 또는 memory admission이 생기지 않는다.

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

Q-005는 D-021/D-022와 이를 supersede한 D-045/D-052에서 당시 값이 정해졌지만, D-074가
future baseline tuple/budget 부분을 다시 supersede한다. D-075는
`40 model / 100 tool / 850,000 token / 1,800초`를 exact four-task readiness 후보 ceiling으로
선택했지만 live gate가 budget confound 2개로 실패해 comparison budget으로 동결하지 않았다.
기존 21/50/250,000/900 template과 소비된 D-075 suite는 실행하지 않는다. 새 condition-neutral tuple의
readiness pass와 별도 freeze decision 전에는 no-memory baseline을 시작하지 않는다.

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

## D-070 accepted decision

- Status: accepted
- Supersedes: D-069의 "V10 live selector 없음" 경계만 future live lane에 대해 supersede하며,
  D-069 offline evidence와 D-067/D-068 artifact는 변경하지 않는다.
- Context: D-069 V10 public-coverage lifecycle은 offline에서 통과했지만 provider에서 exact V10
  path를 관찰한 evidence는 없다.
- Decision: 별도 `memory-development-no-memory-coverage-review-pilot` purpose와 exact
  `dev-no-memory-coverage-review-v10-pilot-20260802-r1` ID만 OpenAI v5/v10/runtime-v4 exception으로
  허용한다. HF Hub/no-memory ×1, 60 model/100 tool/1.2M token/1,800초/output 25k, reserve
  `$5.5125`, cap `$6`를 고정한다. V2 sidecar와 runtime/pricing/task/image/schedule/commit을 execution
  hash에 묶고 non-vacuous coverage lifecycle과 official evaluator 도달을 post-run gate로 사용한다.
- Consequences: checked-in suite와 no-call preflight는 실행 승인이 아니다. Task success는 gate에
  요구하지 않으며 comparison, memory admission과 core에서 제외한다. D-060/D-067은 hard-immutable다.
- Date: 2026-08-02
- Evidence/issue: D-069 offline V10 gate와 D-070 988 collected, 981 passed/7 skipped contract
  regression, host no-call preflight environment pass; live evidence는 아직 없음.

## D-071 accepted decision

- Status: accepted
- Supersedes: D-070의 "live evidence는 아직 없음" 상태만 supersede하며 D-069 offline 계약과
  D-070 원 artifact를 변경하지 않는다.
- Context: 승인 execution hash
  `sha256:cc361c4fa569085b0268a419ec86a7a91ec87719206d604227d2cb45a9c46914`로 exact D-070
  one-row suite가 한 번 실행됐다.
- Decision: `run_6cc69fc1170c4a44`와 original false gate/qualification을 immutable evidence로
  보존하고 experiment ID를 source-level hard-immutable set에 추가한다. Run은 667,553 token,
  28 model/50 tool, 계산상 `$0.671307`을 사용했고 budget은 bind하지 않았다. Valid partial review가
  7/8 target을 판정한 뒤 agent가 missing anchor를 보완하지 않고 unrelated evidence를 세 번
  인용해 evaluator 전 `SubmissionProtocolError`로 종료됐다. 별도 zero-model evaluator
  `run_c07bb2e439a74380`은 exact unsubmitted diff의 hidden fail을 append-only로 기록하되 live
  outcome, SCRR와 gate를 바꾸지 않는다.
- Consequences: D-070/hash는 재실행·재사용하지 않는다. Baseline, memory admission과 core는 계속
  닫힌다. 다음 변경은 budget 증액이나 live retry가 아니라 public structured rejection feedback과
  exact-anchor recovery의 offline E2E다.
- Date: 2026-08-02
- Evidence/issue: sanitized seal
  `reports/live-pilot/dev-no-memory-coverage-review-v10-pilot-20260802-r1.json`; qualification 30/34,
  evaluator reached 0, no-model exact-diff hidden fail.

### D-071 implementation completion addendum

- Status: accepted and offline-verified
- Context: D-070의 v5/v10 validator는 unrelated citation을 정확히 거부했지만 public error
  details가 비어 있어 agent가 offending target의 exact anchor를 회복할 수 없었다.
- Decision: Historical V10을 바꾸지 않고 offline-only `tool v6 / phase-evidence-v11`,
  `SYSTEM_PROMPT_V8`, `corrective-runtime-contract-v5`를 추가한다. Gateway는
  target/requirement, submitted/allowed/invalid sequence, required public path+anchor 또는 visible
  check ID, mutation/diff/source-diff identity를 `coverage-citation-error-v1`로 반환한다.
  Context builder는 source call/failure와 input/result CAS를 재검증해 active rejection을
  `coverage-rejection-feedback-v1`로 restart 뒤에도 exact rehydrate한다. Source rejection을
  먼저 완전 재검증하고 exact feedback/build evidence를 받은 complete review가 call arguments와
  authoritative public evidence에 일치하거나 새 mutation이 `ToolCalled`/`PatchPrepared` intent
  CAS/success/`PatchApplied` 전체 lifecycle에 결속될 때만 clear한다. Rejected call은 실제 prior
  request CAS와 실제 `ModelCalled` response tool call에 결속하고 V11 request/`ContextBuilt`는 active 및 clear request의
  `worker-claim-evidence-v1`를 mirror한다. Stale target evidence만
  반복 제출하면 fresh evidence 전까지 다시 거부한다. Qualifier는
  `coverage_rejection_recovery_contract`로 first-rejection restart claim, same-worker 후속 rejection,
  latest-feedback supersession, batched multi-check recovery evidence, complete review/submission과 single
  mutation을 독립 재구성하고 first rejection 뒤 resume 전 old-worker activity를 거부한다.
- Consequences: Generic V11은 `coverage_rejection_validation=True` + mock + no experiment에서만
  선택한다. Dedicated E2E는 durable rejection 직후 worker exit, fresh resume,
  exact-anchor read, refreshed diff, complete review, separate local evaluator와 target/result/context/restart/recovery,
  orphan/forged-clearing 및 duplicate-mutation tamper rejection을 통과했다. 이 결정은 provider 권한, live 비용
  승인, SCRR, no-memory baseline, memory admission 또는 core gate를 열지 않는다.
- Date: 2026-08-02
- Evidence/issue: `tests/test_coverage_rejection_v11.py` 7/7, focused bundle 43/43, repository-wide
  999 collected and 992 passed/7 environment-dependent skipped; Ruff, compileall and `git diff --check`
  pass. D-070 experiment/hash/run/original qualification and no-model postmortem remain immutable.

### D-072 accepted decision

- Status: implemented offline; exact live invocation later consumed once and sealed by D-073
- Context: D-071은 exact-anchor restart recovery를 닫았지만 V11-specific reconstruction이 큰
  context/qualification module에 남아 있었고, generic mock contract를 넓히지 않으면서 자연 live
  rejection의 관찰 여부와 trace integrity를 분리할 one-row readiness contract가 필요했다.
- Decision: D-071 helper를 의미 보존 방식으로 `patchloop.agent.coverage_rejection`과
  `patchloop.evals.coverage_rejection`에 분리하고 기존 import surface, schema/version, canonical
  artifact와 check ID를 유지한다. 새 exact purpose
  `memory-development-no-memory-coverage-rejection-pilot`, ID
  `dev-no-memory-coverage-rejection-v11-pilot-20260802-r1`은 HF Hub 한 task, `no_memory` 1회,
  v6/v11/runtime-v5, 60 model/100 tool/1,200,000 token/1,800초, output 25,000,
  reserve `$5.5125`/cap `$6`로 고정한다. Generic V11은 mock/no-experiment 전용이고 이 exact
  purpose+OpenAI pair만 exact live exception이다.
- Diagnostic decision: 자연 rejection이 0이면 recovery exercise는
  `inconclusive/rejection_not_observed`지만 다른 integrity 조건이 참이면 qualification/readiness가
  통과할 수 있다. Rejection이 하나 이상이면 모든 structured public source와 recovery/clearing CAS를
  검증하고 하나라도 실패하면 gate를 닫는다. Live hard restart는 exact row의 필수조건이 아니라 별도
  후속 fault exercise다.
- Consequences: Checked-in source suite는 `live_cost_approved=false`, `approved_execution_hash=null`,
  `pilot_run_id=null`이다. 이 변경은 clean-host preflight, 실제 runtime에 persist한 execution
  plan/hash, 사용자 비용 승인, provider call 또는 cost evidence가 아니다. Offline test의 temporary
  synthetic hash/approval branch는 usable capability를 만들지 않는다. D-070 run/hash/gate는 immutable하며
  task success를 요구하지 않는 tuning-only readiness row는 comparison denominator, memory admission과
  core를 열지 않는다.
- Date: 2026-08-02
- Evidence/issue: exact suite와 offline selector/qualification/report contract; focused 322 collected,
  321 passed/1 environment-dependent skipped, repository 전체 1,022 collected, 1,015 passed/7
  environment-dependent skipped. Ruff, Python compileall과 `git diff --check` 통과. API/network/provider
  call과 model cost는 0이고, 이 offline decision 시점에는 clean-host/persisted execution hash와 사용자
  approval이 없었다.

### D-073 accepted decision — D-072 live-result evidence seal

- Status: accepted; append-only seal complete, no additional provider call
- Supersedes: D-072의 `live invocation unapproved` 상태만 supersede한다. D-072 contract와 offline
  verification, D-070 artifact, raw D-072 result/journal/qualification/gate는 변경하지 않는다.
- Context: Clean-host no-call preflight 뒤 사용자가 execution hash
  `sha256:12fb0fb8a02ffe464555bd23125fae18deb6e52e6b6448a482243c036cce080d`로 exact HF Hub
  one-row invocation을 최대 `$6` 아래 명시 승인했다. Hash는 정확히 한 번 소비됐다.
- Decision: `run_e2132144a8774b05`와 experiment ID/hash를 immutable evidence로 보존하고 source-level
  consumed-ID hard seal 및 sanitized portable evidence
  `reports/live-pilot/dev-no-memory-coverage-rejection-v11-pilot-20260802-r1.json`을 추가한다. Original
  raw artifact를 수정하거나 qualification/outcome/campaign gate를 다시 쓰지 않는다.
- Result: Run은 official evaluator, trace qualification 36/36과 readiness gate를 통과했다.
  Structured coverage rejection은 0이라 recovery exercise는
  `inconclusive/rejection_not_observed`다. Regression/scope/safety는 pass, hidden acceptance는 fail이며
  outcome은 `task_failure`, SCRR=false다. Usage는 797,862 input + 64,465 output = 862,327 token,
  35 model call, 57 tool call, 369,385ms, 계산 비용 `$0.841833`이고 budget binding은 없다.
- Diagnostic boundary: Rejected-patch candidate/retry 17/17, saturated context 17개와 post-saturation
  `PatchApplied` 1회가 trace qualification에서 검증됐다. 이는 mutation-preview retry 및 investigation
  policy evidence이지 structured coverage-citation rejection recovery나 live hard-restart evidence가
  아니다.
- Consequences: Suite/hash/run을 재실행하지 않는다. Readiness pass를 task success 또는 recovery pass로
  표현하지 않으며 comparison denominator, memory admission, no-memory baseline과 core에서 제외한다.
  Live hard restart는 별도 fault suite/hash/승인이 필요한 후속 경계다. D-073 seal 자체의 provider call과
  추가 model cost는 0이다. Seal verification은 focused 375 collected, 374 passed/1
  environment-dependent skipped와 repository 전체 1,025 collected, 1,018 passed/7
  environment-dependent skipped를 기록했고 Ruff, Python compileall과 `git diff --check`도 통과했다.
- Date: 2026-08-02
- Evidence/issue: immutable local experiment result and qualification for `run_e2132144a8774b05`;
  portable evidence `reports/live-pilot/dev-no-memory-coverage-rejection-v11-pilot-20260802-r1.json`.

### D-074 accepted decision — semantic rollback to generic baseline preparation

- Status: accepted; policy rollback recorded, exact baseline tuple/readiness panel pending
- Supersedes: D-052의 future 21 model/50 tool/250,000 token/900초 tuple과 D-069~D-072를
  baseline-readiness prerequisite로 취급하던 sequencing만 supersede한다. D-069~D-073의 code,
  raw/portable evidence, schema/qualifier decoder, consumed experiment ID와 immutable guard는
  삭제하거나 소급 변경하지 않는다.
- Context: D-055는 두 development-validation task에서 budget/infrastructure/qualification
  confound 없이 evaluator completion을 보였고, D-060은 HF Hub의 budget bind와 PDM/pyfakefs의
  non-budget hidden task failure를 분리했다. 그 뒤 D-067은 budget bind 없이 evaluator에
  도달했지만 hidden acceptance에 실패했다. D-069~D-072는 같은 HF Hub diagnostic에서 public
  coverage/recovery contract를 계속 정교화했고 모든 row를 baseline, memory admission과 core에서
  제외했다. 이 sequence는 harness branch evidence로는 보존 가치가 있지만 generic no-memory
  baseline을 시작하기 위한 추가 선행조건으로 삼으면 task-specific adaptive tuning 위험이 있다.
- Decision: D-069~D-072의 V10/V11과 exact HF Hub V2 review sidecar lane을
  `retired diagnostic-only`로 분류한다. Generic development/core runtime은
  `tool_schema_version=v2`와 `context_policy_version=phase-evidence-v5`를 유지한다. HF Hub
  sidecar를 generic path나 다른 task로 복사·확장하지 않고, retired V10/V11 live pilot의 gate나
  qualification을 generic campaign prerequisite로 사용하지 않는다.
- Budget/freeze decision: 현재 checked-in 21/50/250,000/900초 template은 stale/unvalidated
  draft이며 그대로 실행하지 않는다. 다음 live approval 전에 exact model snapshot/reasoning,
  system prompt, V2/V5 tool/context, retry, sandbox image, evaluator와 budget을 하나의 새 tuple로
  결정한다. 그 tuple은 서로 다른 repository와 failure pattern의 작은 predeclared development
  readiness panel에서 검증한다. 각 row는 terminal·qualified이고 official evaluator에 도달해야
  하며 infrastructure, qualification 또는 budget confound가 없어야 한다. Task success,
  hidden acceptance와 SCRR pass는 이 readiness gate의 필수조건이 아니다.
- Tuning boundary: Baseline freeze 전 hidden task failure는 immutable outcome으로만 기록하고
  prompt, tool schema, context policy, checklist, sidecar 또는 task-specific validation 변경의 trigger로
  사용하지 않는다. Condition-neutral runtime defect는 public trace/contract로 독립 입증하고 새
  decision에서 수정한 뒤 readiness panel 전체를 다시 검증해야 한다.
- Reliability boundary: Live hard restart는 별도 reliability suite/hash/approval에서 측정한다.
  그 evidence가 없다는 사실은 limitation으로 남지만 generic no-memory baseline의 blocker가 아니다.
- Consequences: Historical V10/V11 decoder와 offline diagnostic tests는 evidence 해석을 위해 남는다.
  Memory admission과 four-condition/core campaign은 exact tuple, diverse readiness panel과 usable
  no-memory baseline이 순서대로 닫힐 때까지 보류한다. D-074 자체는 provider/API call, execution
  hash 또는 비용 evidence를 만들지 않는다.
- Date: 2026-08-02
- Evidence/issue: Retrospective comparison of immutable D-055, D-060, D-067, D-070 and D-072
  outcomes; generic V2/V5 runtime selector and historical consumed-ID guards remain source-enforced.

### D-075 accepted decision — exact generic V2/V5 readiness contract

- Status: accepted and offline-verified; live invocation not approved
- Supersedes: D-074의 `exact baseline tuple/readiness panel pending` 상태 중 readiness 후보 tuple과
  source contract만 supersede한다. D-074의 semantic rollback, historical evidence boundary와
  comparison budget 미동결 상태는 유지한다.
- Context: Generic no-memory path가 task-specific V10/V11 corrective lane과 분리됐지만 기존
  21/50/250,000/900 template은 budget-confounded historical evidence를 반영하지 못했다. Final
  comparison budget을 즉시 동결하기 전에 서로 다른 repository/pattern의 작은 V2/V5 panel이 exact
  runtime tuple로 evaluator까지 안정적으로 완료되는지 검증해야 한다.
- Decision: Exact purpose/ID를 `generic-baseline-readiness` /
  `generic-baseline-readiness-v2v5-20260802-r1`로 정하고 Babel, Moto, pyfakefs와 HF Hub를 ordered
  `no_memory` single rows로 고정한다. Model은 `gpt-5.4-mini-2026-03-17`
  medium/standard/default, prompt/tool/context는 `SYSTEM_PROMPT_V3`/v2/`phase-evidence-v5`,
  per-call output은 25,000이다. Budget은 40 model/100 tool/850,000 total token/1,800초다.
- Retry decision: 새 suite는 `transport_max_retries=0`을 필수로 하고
  `generic-baseline-runtime-contract-v1`에 retry, prompt/tool hash와 clean harness commit을 결속한다.
  이는 OpenAI SDK의 opaque transport retry만 끄며 PatchLoop의 durable logical retry/recovery는
  유지한다. Historical config의 `None`은 field를 serialize하지 않고 기존 `OpenAI()` behavior와
  suite/manifest hash를 보존한다.
- Gate decision: `generic-baseline-readiness-gate-v1`은 exact 4 task, 4 terminal, 4 qualified,
  4 evaluator reached, 4 official completed evaluator와 infrastructure/qualification/diagnostic/budget
  error 0을 요구한다. Task success와 SCRR는 요구하지 않는다. Purpose는 calibration-only이며
  `comparison_denominator_eligible=false`, `memory_admission_unlocked=false`다.
- Cost/approval: Dated source pricing의 conservative reserve는 run당 `$3.9375`, four-row `$15.75`,
  cap `$16`이다. Source YAML은 approval false와 null execution hash/run ID를 유지한다. Offline contract,
  source suite와 no-call preflight는 provider capability가 아니며 clean exact execution hash에 대한 별도
  사용자 승인이 필요하다. Pricing age가 start 기준 72시간을 넘으면 다시 확인한다.
- Consequences: 850k는 readiness 후보 ceiling이지 fair comparison budget이 아니다. Live panel이
  gate를 통과한 뒤 hidden outcome에 맞춘 task-specific tuning 없이 별도 decision으로 comparison tuple을
  freeze한다. Final budget/runtime/harness commit이 D-075와 다르면 same-tuple readiness를 주장하지 않고
  second exact readiness panel을 요구한다. 기존 21/50/250,000/900 template, memory admission,
  no-memory baseline과 core는 계속 보류한다. Live hard restart는 별도 reliability lane이다.
- Date: 2026-08-02
- Evidence/issue: Exact suite/schema, mixed-role preflight, runtime/plan/manifest/start/resume/qualification
  drift rejection, task-success-independent gate, report exclusion and historical suite-hash regression;
  no provider/API call or measured live result in this decision.

### D-076 accepted decision — seal failed D-075 live readiness outcome

- Status: accepted; one approved invocation consumed and append-only result seal recorded; readiness gate failed
- Preserves: D-074 semantic rollback과 D-075 source/runtime/gate definition을 소급 변경하지 않는다.
  Original result, journal, plan, run artifacts, qualifications와 false gate는 immutable하다.
- Invocation: 사용자가 execution hash
  `sha256:1709a9e9911f980aafe28cdd9fe9ed486367c134e2dc9e465c88e01f9462bd66`와 최대 `$16`을
  승인했고 exact suite를 한 번 실행했다. 이 experiment ID와 hash는 소비됐으며 재실행하지 않는다.
- Observed gate: 4/4 terminal, 4/4 qualified, 2/4 evaluator reached/official completed,
  infrastructure/qualification/diagnostic error 0과 budget-terminal 2다. Babel과 Moto는 official
  evaluator/SCRR를 통과했다. HF Hub는 809,867 token에서 exact-request total-token admission이,
  pyfakefs는 40 model call에서 call admission이 bind했다. 따라서
  `generic-baseline-readiness-gate-v1.passed=false`다.
- Usage: 1,580,179 input + 128,645 output = 1,708,824 token, 95 model call, 142 tool call,
  calculated model cost `$1.76403675`. Source reserve/cap과 measured spend를 혼동하지 않는다.
- Reporting boundary: Panel은 calibration-only다. 2/4 SCRR는 diagnostic description이며 no-memory
  baseline, memory 효과 또는 headline metric이 아니다. Comparison denominator, memory admission과
  core는 false/closed를 유지한다.
- Next tuple boundary: Public budget evidence는 50 model/100 tool/1,200,000 total token/1,800초를
  condition-neutral candidate로 지지하지만 completion을 보장하지 않는다. D-076은 이 값을 freeze하거나
  실행 승인하지 않는다. 채택한다면 prompt/tool/context/model/retry는 유지한 새 suite, clean harness
  commit/execution hash와 별도 cost approval로 네 row 전체를 다시 검증해야 한다. Hidden outcome은
  task-specific prompt/tool/sidecar tuning trigger로 사용하지 않는다.
- Date: 2026-08-02
- Evidence/issue: Hash-bound raw local result/journal/plan/run/qualification artifacts, portable sanitized
  record `reports/live-pilot/generic-baseline-readiness-v2v5-20260802-r1.json`, diagnostic-only report and
  consumed-ID guard. Result raw file SHA-256 is
  `sha256:ba2670e8f1bb79e0af9cf56d02841014cc3e66d58db85b114459776af277d30d`.

### D-077 accepted decision — adopt a budget-only generic V2/V5 readiness successor

- Status: accepted and offline-verified source-contract decision; clean no-call preflight pending; no
  provider call, execution hash, live approval, run, measured cost or gate outcome.
- Preserves: D-075 r1 suite/hash/run/result/false gate와 D-076 append-only seal을 수정·재개·합산하지 않는다.
  Historical consumed-ID guard와 calibration-only reporting boundary도 유지한다.
- Exact successor: 새 experiment ID는 `generic-baseline-readiness-v2v5-20260802-r2`, purpose는
  `generic-baseline-readiness`다. Ordered Babel/Moto/pyfakefs/HF Hub task와 원 dataset role,
  `no_memory` repetition 1을 그대로 사용한다.
- Controlled change: `gpt-5.4-mini-2026-03-17` medium/standard/default, `SYSTEM_PROMPT_V3`, tool
  v2/context V5, SDK retry 0, output 25,000, tool 100, wall 1,800초, sidecar absent와 fault none은
  바꾸지 않는다. Model call만 40→50, total token만 850,000→1,200,000으로 올린다. 다른 drift가
  생기면 budget-only evidence가 아니라 새 tuple로 versioning한다.
- Gate/report boundary: `generic-baseline-readiness-gate-v1`은 계속 exact 4/4 terminal·qualified·official
  evaluator completion과 infrastructure/qualification/diagnostic/budget-terminal 0을 요구한다. Hidden
  acceptance와 SCRR는 요구하지 않는다. 모든 row는 calibration-only이고 comparison denominator,
  failure-memory admission과 core에서 제외한다. Pass도 comparison/no-memory budget을 자동 freeze하지 않는다.
- Authorization boundary: 공식 rate는 2026-08-02T13:11:37Z에 다시 확인했다. Conservative reserve는
  `$5.5125`/run, `$22.05`/four rows, cap `$23`이며 completion guarantee, 예상 비용 또는 invoice가 아니다.
  Tracked source와 offline tests를 clean commit으로 만든 뒤 no-call preflight가 새 exact hash를 계산해야
  하고, 사용자가 그 hash와 최대 `$23`을 명시적으로 승인해야 한 번 실행할 수 있다.
- Rationale: D-075 public trace가 HF Hub total-token과 pyfakefs model-call budget만 readiness confound로
  식별했다. 두 limit에 모든 row가 공유하는 headroom을 주면 hidden outcome에 맞춘 task-specific tuning
  없이 runtime completion을 다시 판정할 수 있다. 50/1.2M은 observed headroom에 기반한 heuristic이지
  completion 보장이 아니다.
- Date: 2026-08-02
- Evidence/issue: D-076 immutable public budget facts와 dated official pricing verification. D-077 source
  및 offline gate는 1,095 collected/1,088 passed/7 environment-dependent skipped, Ruff, compileall과
  `git diff --check`를 통과했다. Provider/result evidence가 없고 readiness, SCRR, baseline 또는
  memory-effect claim을 만들지 않는다.

### D-078 accepted decision — seal failed D-077 budget-only readiness outcome

- Status: accepted append-only result seal. 승인 execution hash
  `sha256:de73e622fcaa4cec85191cceb01efdb0d27cc6a5a6b8f05c7cd4844df50763f5`는 source harness
  commit `4a2596e43398af094f1f17bcb0cb1a7945cb7058`에서 정확히 한 번 소비됐다.
- Preserves: D-077 suite, raw result, hash-chained journal, plan, run artifact, qualification과 original
  false gate를 수정·재개·합산하지 않는다. R2 experiment ID를 consumed hard-immutable set에 추가하고
  재실행하지 않는다.
- Result: 4/4 terminal·qualified, 3/4 official evaluator, infrastructure/qualification/diagnostic error 0,
  budget-terminal 1이다. HF Hub와 Babel은 hidden acceptance 실패, Moto는 SCRR, pyfakefs는 evaluator
  전에 `model_call_budget_exhausted`로 끝났다. Hidden outcome은 readiness pass requirement가 아니다.
- Remaining confound: pyfakefs는 50 model call을 모두 사용했지만 387,160 token, 16 tool call과
  1,100,745ms가 남았다. D-077의 HF row는 D-075의 total-token terminal을 재현하지 않고 evaluator에
  도달했으며, D-077에서 관찰된 유일한 binding dimension은 model-call admission이다.
- Usage/cost: 1,816,830 input + 181,254 output = 1,998,084 token, 125 model call, 219 tool call,
  usage-derived cost `$2.1782655`다. 이는 `$23` authorization cap이나 실제 invoice가 아니다.
- Claims boundary: Report의 1/4 SCRR는 calibration-only diagnostic이고 ordinary metrics는 비어 있다.
  Readiness gate, comparison denominator, no-memory baseline, memory admission과 core는 모두 닫혀 있다.
  D-078은 자동 재실행, 추가 budget 증가 또는 hidden-failure 기반 prompt/tool/context tuning을 승인하지
  않는다.
- Date: 2026-08-03
- Evidence/issue: Sanitized record
  `reports/live-pilot/generic-baseline-readiness-v2v5-20260802-r2.json`, result SHA-256
  `sha256:22385cf6efd9b54de960cfe5b55c812ba74d3275ac9496f7db16fd0cb727e5fe`, journal final event
  `sha256:0a65f0bd0e20caa4f1cedd41433a63f53c6aa2a965ee256531a0d71777ba4b62`와 네 qualification.
  Seal verification은 focused 11 passed, repository-wide 1,099 collected/1,092 passed/7 skipped,
  Ruff, compileall, JSON parse와 `git diff --check`를 통과했고 provider call/model cost는 0이다.

### D-079 accepted decision — isolate call-count censorship with one bounded pyfakefs completion probe

- Status: accepted source/offline contract decision; executable offline verification complete, clean no-call
  preflight와 separate live approval pending. Provider call, execution hash, user approval, run/result, measured
  usage/cost와 gate outcome은 아직 없다.
- Preserves: D-077 r2 suite/hash/four runs/false gate와 D-078 append-only seal을 수정·재개·합산하지 않는다.
  Hidden outcomes도 prompt/tool/context tuning input으로 사용하지 않는다.
- Exact identity: purpose `workflow-completion-probe`, experiment ID
  `pyfakefs-workflow-completion-probe-v2v5-20260803-r1`, frozen pyfakefs task, `no_memory`, repetition 1이다.
- Fixed runtime: `gpt-5.4-mini-2026-03-17` medium/standard/default, `SYSTEM_PROMPT_V3`, tool v2/context
  `phase-evidence-v5`, SDK retry 0, output 25,000, sidecar absent와 fault none을 유지한다.
- Controlled policy: `model-tool-observability-only-v1` 아래 model/tool call limit은 `null`이고 counters는
  기록·reconcile한다. 3,000,000 total token, 7,200초 wall, exact-request, cost, loop, constrained-tool,
  Docker/network/evaluator guard는 계속 강제한다. Runtime schema는
  `workflow-completion-runtime-contract-v1`이다.
- Gate/report boundary: `workflow-completion-probe-gate-v1`은 1/1 terminal·qualified·official evaluator,
  zero infrastructure/qualification/diagnostic error와 call-policy/retained-guard integrity를 요구하되 hidden
  pass나 SCRR는 요구하지 않는다. Calibration-only이며 comparison denominator, baseline, memory admission과
  core는 닫혀 있다.
- Authorization boundary: Conservative reserve `$13.6125`와 cap `$14`는 source authorization bounds다.
  Fresh official pricing을 포함한 clean no-call preflight의 exact hash와 최대 `$14`에 대한 별도 명시적
  승인 전에는 provider를 호출하지 않는다. Pass/fail 뒤 자동 재실행도 없다.
- Rationale: D-078 pyfakefs row는 token/tool/wall headroom이 남은 채 model-call 50에서만 종료됐다.
  한 task의 call-count guard만 orthogonal하게 제거하면 agent를 hidden behavior에 맞추지 않고 workflow
  completion distribution의 오른쪽 꼬리를 관찰할 수 있다. 단일 row이므로 일반 completion rate나 fair
  comparison budget을 추정하지 않는다.
- Date: 2026-08-03
- Evidence/issue: Source/runtime/gate contracts와 repository-wide 1,182 collected, 1,175 passed/7
  environment-dependent skipped, Ruff, compileall, `git diff --check`. Official standard pricing은
  2026-08-02T16:35:25Z에 `$0.75/M` input, `$0.075/M` cached input, `$4.50/M` output으로 재확인했다.
  Provider call/model cost는 0이다. Live 결과가 승인·생성되면 별도 D-080 seal에서 immutable evidence와
  measured usage/cost를 기록한다.

### D-080 accepted decision — seal D-079 result and correct only the gate-summary projection

- Status: accepted append-only result/correction seal with final offline verification complete. Focused tests are
  331 passed; repository-wide regression is 1,162 collected, 1,155 passed and 7 environment-dependent skipped.
  Ruff, Python compileall, JSON parse and `git diff --check` passed. D-080 itself makes zero provider call and adds
  `$0` model cost.
- Preserves: D-079 suite, execution hash, run, raw result, journal, qualification, submitted diff, original
  `workflow-completion-probe-gate-v1` false와 hidden task failure를 수정·재실행·합산하지 않는다.
- Live result: `run_606349c2c56342d4`는 84 model/119 tool, 1,790,707 token, 856,559ms와
  `$1.81747785`를 사용해 terminal·qualified·official evaluator에 도달했다. Token 1,209,293과 wall
  6,343,441ms가 남았고 binding dimension은 none이다.
- Outcome boundary: Regression/scope/safety는 pass, hidden acceptance는 fail이므로 task outcome은
  `task_failure`, SCRR false다. Process completion과 correctness를 합치지 않는다.
- Defect: Full qualification의 `disabled_call_guard_contract`는 exact 1/1 pass였지만 historical terminal
  summary가 raw checks를 생략했고 gate consumer가 그 collection을 검색했다. Original false는
  `qualification-summary-projection-mismatch`이며 runtime/trace violation이 아니다.
- Correction: `gcor_6552d8277d70fba7f296b0aee837a8f497be8384cce7fea4521cb39de1e19861`의 suffix는
  semantic body hash `sha256:6552d8277d70fba7f296b0aee837a8f497be8384cce7fea4521cb39de1e19861`와 같다.
  Body는 source identity와 raw result/qualification/source-evidence hashes, correction harness commit
  `7e40e27446bcf011f700c219a96983e5670422f4`, projection contract, exact cause, original gate의 전체
  payload, corrected gate의 전체 payload와 claims boundary를 함께 결속한다.
- Gate semantics: Original과 corrected payload는 모두 `workflow-completion-probe-gate-v1`이다. Corrected
  payload의 process pass는 append-only correction 안에만 있고, `claims_boundary.original_gate_replaced=false`와
  `original_artifacts_modified=false`가 원 gate와 artifacts가 그대로임을 명시한다.
- Forward contract: Summary producer는 full checks 대신 `qualification-gate-check-projection-v1` sanitized
  projection을 만든다. Consumer는 exact outer key set과 exact
  `schema_version/check_id/check_count/passed` inner key set, schema/ID, strict integer count 1과 boolean true를
  모두 요구하고 absence, duplicate, extra key, bool/float/string count, type drift와 tamper를 fail closed한다.
- Claims boundary: D-079/D-080은 calibration-only다. Derived gate pass는 agent workflow completion만
  보여주며 task quality, general completion rate, memory effect 또는 fair comparison budget을 증명하지
  않는다. Baseline, comparison denominator, memory admission과 core는 닫혀 있고 자동 재실행·hidden-driven
  tuning은 금지한다.
- Date: 2026-08-03
- Evidence/issue: Portable sanitized record
  `reports/live-pilot/pyfakefs-workflow-completion-probe-v2v5-20260803-r1.json`과 portable correction manifest
  `reports/live-pilot/artifacts/d080-workflow-completion-gate-summary-correction.json`; raw local artifacts는
  hash로만 참조하고 provider bodies, private evaluator assertions와 reference patch를 포함하지 않는다.

### D-081 accepted decision — condition-neutral generic V2/V5 four-row readiness source contract

- Status: historical accepted source/offline contract decision. D-082 later executed and sealed this exact r3
  identity; the source decision itself made provider call 0 and cost `$0`.
- Preserves: D-075/D-077/D-079/D-080 suite, consumed execution identities, raw/portable artifacts, original false
  gates와 append-only correction을 수정·재개·결합하지 않는다. Historical runtime/gate v1 의미도 바꾸지 않는다.
- Exact identity: purpose `generic-baseline-readiness`, experiment ID
  `generic-baseline-readiness-v2v5-20260803-r3`. Ordered Babel, Moto, pyfakefs, HF Hub task와 원 dataset role,
  `no_memory` repetition 1, seed `20260723`을 D-075/D-077과 동일하게 유지한다.
- Fixed tuple: `gpt-5.4-mini-2026-03-17` medium/standard/default, `SYSTEM_PROMPT_V3`, tool v2/context
  `phase-evidence-v5`, SDK transport retry 0, output 25,000, sidecar absent와 fault none을 고정한다.
- Count-policy decision: model/tool call limit은 exact pair `null`이고
  `model-tool-observability-only-v1` 아래 durable counter와 usage reconciliation만 유지한다. Total token
  2,400,000, wall 1,800초, exact-request, cost, loop, state/idempotency, constrained-tool,
  Docker/network/evaluator guard는 계속 admission boundary다.
- Public derivation: evaluator-complete process usage만 사용한다.
  `((1,790,707 + 84 * 2,000 + 25,000) * 1.2) = 2,380,448.4`를 100,000 단위로 올림해
  2,400,000을 선택한다. Wall은 `856.559s * 2 = 1,713.118s`를 300초 단위로 올림해
  1,800초를 선택한다. Private evaluator outcome과 task success는 산식에 쓰지 않는다.
- Version decision: plan/trace/gate는 각각 `generic-baseline-runtime-contract-v2`,
  `generic-baseline-runtime-evidence-v2`, `generic-baseline-readiness-gate-v2`다. 네 row 모두 exact-one
  `qualification-gate-check-projection-v1`/`disabled_call_guard_contract`와
  `call_guard_contract_passed=true`를 요구한다. Task success/SCRR는 gate 조건이 아니다.
- Cost/approval: 2026-08-03T01:08:49Z official standard pricing에서 conservative reserve는
  `(2,400,000 + 25,000) * $4.50/M = $10.9125`/run, `$43.65`/four rows, cap `$44`다. Source
  YAML과 source/preflight artifact는 authority가 아니며 clean preflight가 만든 exact hash와 최대 `$44`의
  별도 명시적 승인 전 provider call을 금지한다.
- Claims boundary: D-081은 calibration-only다. Source contract나 향후 gate pass는 comparison budget을
  자동 freeze하거나 no-memory baseline, memory admission, core를 열지 않는다. 동일 ceiling의 theoretical
  96-run reserve `$1,047.60`은 original `$150` project cap과 충돌하므로 readiness 뒤 별도 budget/scale
  decision이 필요하다. Hidden outcome에 따른 task-specific tuning이나 automatic rerun을 승인하지 않는다.
- Date: 2026-08-03
- Evidence/issue: Public derivation artifact
  `reports/live-pilot/artifacts/d081-condition-neutral-budget-candidate.json`과 exact source config. Repository-wide
  1,204 collected 중 1,197 passed/7 environment-dependent skipped, Ruff, Python compileall과
  `git diff --check`가 historical source-stage executable offline evidence다. 이후 live evidence는 아래
  D-082 decision에만 속한다.

### D-082 accepted decision — immutable D-081 measured-result seal

- Status: accepted measured calibration result. Exact source commit
  `b4c79242bb0a94eed50530116205323e78c7d21a`와 승인 execution hash
  `sha256:446b60568795c585856468064fa1aa11a9d85a8e8806e6c71b3b19ab1aa12579`로 D-081을 정확히 한 번
  실행했고 재실행하지 않는다.
- Process outcome: 4/4 terminal·trace-qualified·official evaluator, exact-one disabled-call projection과
  `generic-baseline-readiness-gate-v2` pass. Infrastructure/qualification/diagnostic/budget-terminal과
  terminal-loop confound는 0이다.
- Task outcome: Babel만 task success/SCRR이고 HF Hub, Moto, pyfakefs는 hidden acceptance failure다.
  Regression/scope/safety는 4/4 pass다. Hidden perfection은 gate predicate가 아니며 이 1/4를 baseline이나
  population estimate로 사용하지 않는다.
- Measured usage: 111 model/175 tool call, 1,929,316 token, fixed standard-rate calculated cost
  `$1.79426325`. 111/111 request는 completed, exact input telemetry 일치, truncation disabled,
  `store=false`다. Rejected-patch recovery 3/3이 verified됐고 loop observation 50회 중 pyfakefs가 39회지만
  terminal loop failure는 0이다. 계산 비용은 billed invoice/free-tier charge 주장이 아니다.
- Evidence identity: pre-run derivation artifact SHA
  `sha256:6f871c13aee71043c20c54c72a93667600462e8369483e9354507a94d0063193`; raw result SHA
  `sha256:f8a2cd25916290ae02e46b484519cc01dedbe50097326085524a88bb9b324f83`; journal file SHA
  `sha256:52626ba6d7e61bc293ce327f4bf190e3b4118b20a2efe4d9de09d8186ce6afdd`; final event hash
  `sha256:f5537479c3c1e8c150f9cbfec5238d99c882eff537006773af8d9ddf9f78c254`. Portable report
  `reports/live-pilot/generic-baseline-readiness-v2v5-20260803-r3.json`의 content hash는
  `sha256:2a8f650e73e01aed9d629290627999232ec6aebd1769d2179bc22f084ddbede2`다.
- Claims boundary: D-081/D-082는 calibration-only다. Comparison denominator, no-memory baseline, memory
  admission, core 또는 comparison budget freeze를 열지 않는다. `$1,047.60` theoretical 96-run reserve와
  `$150` cap 충돌은 별도 사전 decision으로 해결한다. Hidden failure에 따른 automatic rerun과
  task-specific tuning은 승인하지 않는다.
- Seal cost: provider call 0, model cost `$0`. Final documentation-seal verification은 repository-wide
  1,214 collected 중 1,207 passed/7 environment-dependent skipped와 focused D-082 8/8을 통과했다.
- Date: 2026-08-03

### D-083 accepted decision — offline condition-neutral comparison-budget policy freeze

- Status: accepted offline policy freeze; runtime support and every live/admission gate remain closed.
- Supersedes: D-081/D-082의 `comparison budget not frozen` 상태만 supersede한다. 두 decision의 source,
  result, calibration-only status, task outcome, consumed execution identity와 claims boundary는 immutable하다.
- Evidence scope: exact D-081 r3 public process evidence만 사용한다. Pyfakefs observed-prefix minimum
  1,303,223에 20% headroom을 적용한 `1,563,867.6`을 100,000 단위로 올림해 1,600,000을 선택한다.
  Hidden acceptance와 task success는 derivation에 사용하지 않는다. D-080 historical minimum 1,815,619는
  이 scope 밖이며 completion guarantee가 아니다.
- Frozen policy: model/tool call limit `null`/`null`, total token 1,600,000, wall 1,800초,
  max output 25,000과 SDK transport retry 0. Null count는 admission 제거이지 counter/usage observability,
  exact-request, cost, loop, constrained-tool, Docker/network/evaluator guard 제거가 아니다.
- Cost boundary: worst-rate reserve는 `$7.3125`/run, `$87.75`/12 run, `$131.625`/18 run과
  `$702`/96 run이다. 기존 `$20` 12-run cap과 `$150` project cap을 변경하지 않으므로 source template,
  suite scale과 paid execution은 승인되지 않는다.
- Implementation boundary: `comparison_budget_policy_frozen=true`만 기록한다. Runtime/manifest/qualification
  support는 다음 offline gate까지 pending이고, 그전까지 source template은 fail closed다.
  `live_execution_authorized=false`, `comparison_denominator_eligible=false`,
  `no_memory_baseline_unlocked=false`, `memory_admission_unlocked=false`,
  `core_campaign_unlocked=false`, `analysis_ready=false`를 유지한다.
- Evidence identity: append-only artifact path는
  `reports/live-pilot/artifacts/d083-condition-neutral-comparison-budget-freeze.json`, SHA는
  `sha256:e01c5f0107592e1c29c1ec8264f32bf05c979a718c353c37acb0d87fafd2cb88`다.
- Verification: repository-wide 1,238 collected 중 1,231 passed/7 environment-dependent skipped, focused
  artifact 9/9와 experiment contract 245/245.
- Cost: provider call 0, model cost `$0`.
- Date: 2026-08-03

### D-084 accepted decision — offline condition-neutral comparison runtime binding

- Status: accepted offline runtime gate. D-083 policy bytes는 수정하지 않고 exact tuple을 execution identity에
  결속한다.
- Runtime contract: `condition-neutral-comparison-runtime-contract-v1`은 purpose, ordered memory conditions,
  `gpt-5.4-mini-2026-03-17` medium/standard/default, retry 0, output 25,000,
  `null/null/1,600,000/1,800`, memory allowance 2,000, `SYSTEM_PROMPT_V3`, tool v2/context
  `phase-evidence-v5`, prompt/tool hash, `model-tool-observability-only-v1`, D-083 path/SHA와 harness commit을
  execution plan과 hash에 포함한다.
- Manifest/start decision: Start 전에 exact `RunManifest`에서 runtime contract를 재구성한다. Partial null이나
  purpose/condition/model/retry/output/budget/V2/V5/fault/sidecar drift는 fail closed한다. Start는
  `condition-neutral-comparison-runtime-evidence-v1`을 content-addressed artifact로 저장하고
  `RunStarted`에 full descriptor를 남기며 resume도 descriptor·bytes·expected document를 다시 검증한다.
- Qualification decision: Budget diagnostic은 exact registered profile만 허용한다. No-memory qualifier는
  approved execution plan, `comparison_runtime_contract`, `disabled_call_guard_contract`, pricing freshness와
  no-memory boundary를 요구한다. D-081 nullable-count와 historical 250k/200k semantics는 소급 변경하지 않는다.
- Core boundary: Four-condition core는 동일 tuple의 plan/manifest/offline start-resume structure만 구현한다.
  Frozen-index identity가 execution hash와 per-run evidence에 결속되지 않았고 condition별 leak-safe terminal
  qualification도 pending이다. 따라서 `CORE_MEMORY_RUNTIME_BINDING_PENDING` preflight blocker와 paid-call
  거부를 유지하며 core campaign과 aggregate gate는 닫혀 있다.
- Authority/claims: Provider call 0, model cost `$0`; 승인 execution hash, live execution, no-memory baseline,
  comparison denominator, memory admission, core 또는 `analysis_ready`를 만들지 않는다. 기존 `$20`/`$150`
  cap도 바꾸지 않는다.
- Evidence: `reports/live-pilot/artifacts/d084-condition-neutral-comparison-runtime-gate.json`.
- Verification: focused D-084 68/68; repository-wide 1,304 collected, 1,297 passed/7 environment-dependent
  skipped. Artifact SHA
  `sha256:e7fb7b7e7e9dad3e6b31fb781f09151b940bf226bdd5876e5e75e472ff24b701`.
- Date: 2026-08-03

### Historical D-085 accepted source decision — exact one-row comparison live-readiness pilot

- Status: historical source/offline gate; clean preflight와 exact single invocation은 이후 D-086 evidence로
  별도 봉인됐고 이 source decision 자체는 immutable하다.
- Identity: Exact ID `dev-validation-condition-neutral-v2v5-pilot-20260803-r1`, purpose
  `development-validation-live-pilot`, frozen Babel task, `no_memory`, one repetition만 허용한다.
- Runtime: D-083/D-084의 mini medium/standard/default, retry 0, `SYSTEM_PROMPT_V3`, tool v2/context V5,
  output 25,000, memory allowance 2,000과 `null/null/1,600,000/1,800`을 변경 없이 사용한다.
- Cost: Current official standard rate는 input `$0.75/M`, cached `$0.075/M`, output `$4.50/M`이다.
  Worst-rate reserve `$7.3125`, source cap `$8`이며 별도 exact-hash 승인이 필요하다. 이는 invoice/free-tier
  prediction이 아니다.
- Readiness: 1/1 terminal·trace-qualified·official evaluator, exact disabled-call-guard pass와
  infrastructure/qualification/diagnostic/budget-terminal/terminal-loop 0을 요구한다. Task success와 SCRR는
  요구하지 않는다.
- Future campaign admission: Pilot과 campaign은 별도 clean source commit을 사용한다. Exact
  `dev-no-memory-v5-20260730-r1` consumer가 qualification/source/approved plan CAS, 네 필수 check와 D-083/D-084
  semantic exact tuple을 검증하며 persisted qualification을 durable state에서 read-only 재계산한 값과 exact
  비교하고 task success는 제외한다. 결과의
  `condition-neutral-comparison-pilot-admission-v1` canonical hash는 future campaign plan/hash와
  start/resume/post-run qualification에 결속된다. Consumer와 qualified pilot evidence가 있어도 cap 변경,
  새 campaign hash/승인과 paid authority는 pending이다.
- Sequencing: Qualified pilot 뒤에만 12-run dev cap을 `$20 → $88`로 바꾸는 별도 decision을 검토한다.
  New no-memory collection 전에는 historical failure를 memory로 승격하거나 index를 freeze하지 않는다.
- Authority: Source artifact와 suite는 candidate/approved execution hash, provider capability, baseline,
  denominator, memory admission, core 또는 `analysis_ready`를 만들지 않는다.
- Evidence: `reports/live-pilot/artifacts/d085-condition-neutral-comparison-pilot-source-gate.json`, SHA
  `sha256:8b60cb2e62a6259db29527a600712e95b36390a1c07da9fb66e6f1d7d16f51d2`.
- Verification: focused 153/153; repository-wide 1,392 collected, 1,385 passed/7 skipped.
- Date: 2026-08-03

### D-086 accepted result decision — seal D-085 readiness and correct budget-pressure projection append-only

- Status: accepted measured-result/correction seal; future campaign authority remains closed.
- Identity: Source commit `629b9fdd9f69d1522cf565a06ae9679abe3f60a7`, execution hash
  `sha256:7163f6c44aa5b7790d35546be37781248d6575eac60986b2610f2e21c35348a0`, run
  `run_c355405d826641b9`를 immutable consumed evidence로 고정한다.
- Outcome: Original `condition-neutral-comparison-pilot-readiness-gate-v1` passed; terminal/qualified/official
  evaluator 1/1이고 hidden/regression/scope/safety도 모두 pass다. Qualification은 28/28이다.
- Usage: 69,701 input + 3,500 output = 73,201 token, 8 model/9 tool call, 50,769ms와 official fixed-rate
  calculated `$0.06802575`다. Invoice/free-tier charge는 주장하지 않는다.
- Immutable hashes: Result
  `sha256:e0c3c4c67adc8c157a5030c9a93e3fd106d6b7a12f596253ddf10582fe74b80a`, journal file
  `sha256:4c114059fad069526d95786c392b7ea36724443b7231b4426bb097ee0c2199c8`, final event
  `sha256:93853c6367459bcae004789a9a2710c6be518078b21041ece0b160d9843e5a8b`, qualification
  `sha256:11bda7b2f31bae453f21c4718fdcb4563a74e173e621fd8035f1ab8aa64f1293`다.
- Correction: Original result의 `budget-pressure-error-v1`은 exact D-085 purpose가 diagnostic selector에서
  누락된 projection gap이다. Original result/gate를 바꾸지 않고 exact ID/runtime만 허용한 derived correction이
  token/wall headroom 1,526,799/1,749,231ms와 binding `none`을 기록한다.
- Immutability: D-085 experiment ID는 local result/journal 유무와 무관하게 hard-consumed다. Source artifact와
  D-085 decision도 소급 수정하지 않는다.
- Claims: Single-row readiness와 observed Babel task success만 established다. No-memory baseline,
  comparison denominator, memory admission/index, core와 analysis는 false/closed다.
- Evidence: Portable
  `reports/live-pilot/dev-validation-condition-neutral-v2v5-pilot-20260803-r1.json`
  (`sha256:520ae8408c4e090a2c66a0ed3b2c5c29738762eec1b4f7d87b9452e551635464`), correction
  `reports/live-pilot/artifacts/d086-condition-neutral-comparison-pilot-budget-pressure-correction.json`
  (`sha256:bd42c50b7da2400eea8e340358e92ff2605a9fde8d866d3fdff1c9695b95aeb4`), verification `focused 64/64; repository-wide 1,416 collected, 1,409 passed/7 skipped; Ruff/compileall/JSON/git-diff checks passed; seal provider calls/model cost 0/$0`.
- Next decision: 12-run cost cap `$20 → $88` 채택 여부를 별도로 결정한다. 채택해도 새 campaign source commit,
  `pilot_run_id`, fresh pricing/preflight/hash와 별도 사용자 비용 승인이 필요하다.
- Date: 2026-08-03

### D-087 accepted source decision — campaign-local accrued list-price cap

- Status: source/offline gate only. Clean preflight, candidate/approved execution hash와 provider execution은 없다.
- Identity: 새 exact ID는 `dev-no-memory-condition-neutral-accrued-cap-20260804-r1`이다. Historical
  `dev-no-memory-v5-20260730-r1` `$20` source와 D-083~D-086 artifact는 수정하지 않고
  `superseded-unexecuted` predecessor로 보존한다.
- Runtime: D-083/D-084의 mini medium/standard/default, retry 0, generic `SYSTEM_PROMPT_V3` + tool V2/context
  V5, output 25,000, memory allowance 2,000, `null/null/1,600,000/1,800` tuple을 유지한다.
- Cap derivation: D-081 r3 public process cost `$1.79426325 / 4 * 12 = $5.38278975`, max observed
  `$1.19727 * 12 = $14.36724`, 여기에 full-run reserve `$7.3125`를 더한 `$21.67974`를 `$5` 단위로
  올려 `$25`를 선택한다. Hidden outcome과 task success는 산식에 쓰지 않는다.
- Admission: `accrued + full_next_run_reserve <= $25`일 때만 다음 row를 시작하고 equality는 허용한다.
  Integer nano-USD로 비교하며 reserve/settlement는 append-only fsync journal과 token-derived cost로 검증한다.
  Reserve가 부족하면 나머지는 `not_started`이고 readiness gate는 false다.
- Bounds: `$87.75`는 12-run worst-rate theoretical upper bound로 계속 공개한다. `$25`는 campaign-local fixed
  list-price accounting cap이며 invoice/free-tier/project-wide cap이나 12/12 completion guarantee가 아니다.
- Binding: Cost policy/hash는 suite, execution plan/hash, `ExperimentRunContext`, manifest reconstruction,
  start paid boundary와 post-run `campaign_spend_cap_contract`에 결속한다. Exact one-use capability는 SQLite
  `BEGIN IMMEDIATE`로 row를 소비하고, next-row admission은 prior qualification/source/result를 reload해 fixed
  nano-USD로 다시 계산한다. Preserved SQLite anchor 아래 marker 삭제, journal reset, alternate root와 lowered
  settlement rehash는 거부한다. Campaign live resume은 external/request-level billing reservation ledger가
  생길 때까지 fail closed다.
- Authority: Baseline, comparison denominator, memory admission/review/index, core와 `analysis_ready`는 닫혀 있다.
  다음 gate는 clean source commit의 fresh no-call preflight와 새 candidate hash이며, provider 실행에는 그 hash와
  최대 `$25`에 대한 별도 사용자 승인이 필요하다.
- Evidence:
  `reports/live-pilot/artifacts/d087-condition-neutral-comparison-accrued-spend-cap-source-gate.json`,
  `sha256:5f038999b65930a0f155d5eb00a530ac06b6e359de0bdac12fff22398aaa7efe`, focused 68/68,
  repository-wide 1,472 collected 중 1,465 passed/7 skipped.
- Provider calls/model cost for this decision: `0/$0`.
- Date: 2026-08-04

## Deferred ideas

다음 항목은 아이디어로만 유지하며 v1 work item으로 만들지 않는다.

- Multi-agent 역할 분리
- Kubernetes/distributed queue
- Full GitHub App/organization permissions
- Multi-language evaluator
- Autonomous harness self-modification
- LLM-only grading/classification
- Enterprise dashboard and access control

### D-088 accepted result decision — seal failed readiness without hidden-driven tuning

- D-087의 `$25` campaign cap은 충분했다. Actual list-price accrual `$5.36842875`와 maximum committed
  `$12.31149825`는 cap 아래였고 12개 row 모두 reserve/settle됐다.
- Original readiness gate는 false로 유지한다. AnyIO repetition 2가 per-run 1.6M token ceiling에 걸려
  evaluator가 11/12였기 때문이다.
- 관찰된 1 resolved, 10 hidden task failure, 1 agent budget failure를 no-memory 성능 baseline이나 memory
  admission 근거로 사용하지 않는다. Hidden outcome을 근거로 prompt/tool/task를 수정하지 않는다.
- D-087 ID/hash/result/journal은 immutable하고 재실행하지 않는다. 후속 후보는 condition-neutral budget-only
  새 experiment로만 다루며 자동 생성·실행하지 않는다.
- D-088 seal 작업은 provider call 0, added model cost `$0`이다.

### D-089 accepted source decision — rerun only the budget-confounded AnyIO row

- D-087 전체 12-run이나 immutable run을 재실행·resume하지 않는다. 새 exact experiment
  `anyio-workflow-completion-budget-only-v2v5-20260804-r1`에서 AnyIO task를 no-memory로 한 번 실행하는
  source만 준비한다.
- “Budget-only”의 비교 범위는 per-run agent/model/runtime knob다. Model, reasoning/mode/tier, transport retry,
  prompt V3, tool V2/context V5, output 25,000, memory allowance 2,000, null model/tool call limit과 wall 1,800초는
  유지하고 total-token ceiling만 1.6M에서 2.0M으로 바꾼다. Experiment ID, purpose, schedule, repetitions,
  estimate/cap과 campaign-policy fields는 새 suite identity다.
- D-087 AnyIO repetition 2는 1,578,208 token을 쓴 뒤 remaining 21,792로 exact input 14,080과 full output
  allowance 25,000을 함께 예약하지 못했다. Same-prefix minimum 1,617,288 대비 새 ceiling headroom은
  382,712 token이다. 이는 completion guarantee가 아니다.
- 공식 standard rate `$0.75/M` input, `$0.075/M` cached input, `$4.50/M` output을 2026-08-04T05:10:38Z에
  재확인했다. Worst-rate authorization reserve는 `$9.1125`, source cap은 `$10`이다. 관찰 prefix 기반
  `$1.866201`은 illustrative projection일 뿐 예상 invoice가 아니다.
- Readiness는 terminal, trace qualification, official evaluator, exact disabled-call-guard와
  infrastructure/qualification/diagnostic/budget/terminal-loop confound 0을 요구한다. Hidden acceptance,
  task success와 SCRR는 요구하지 않는다. 결과와 무관하게 이 single-row probe는 calibration-only다.
- D-083 budget freeze, D-087 source/result/journal과 D-088 portable seal은 byte-immutable하다. Source 결정
  당시 D-087은 hard-consumed였고 D-089는 결과 전이므로 consumed set에 넣지 않았다.
- Source 결정 당시 authority는 source/offline뿐이었다. Clean commit의 no-call preflight에서 exact candidate
  hash를 만든 뒤 최대 `$10`에 대한 별도 사용자 승인 전에는 provider를 호출하지 않았다. 이후 exact invocation과
  static consumption은 아래 D-090 결정에만 속한다. Baseline, comparison denominator, memory review/admission/index와
  core는 계속 닫혀 있다.
- Evidence: `reports/live-pilot/artifacts/d089-anyio-budget-only-readiness-probe-source-gate.json`, SHA
  `sha256:19eca850799e9549eef1d8b383d0c3461aa2b9a2e5471d67fe599cb373ea4555`.
- Final offline verification: focused `228/228`; repository-wide `1,529` collected, `1,522` passed and `7` skipped;
  Ruff, compileall, JSON parse and `git diff --check` passed.
- Provider calls/model cost for this decision: `0/$0`.
- Date: 2026-08-04

### D-090 accepted result decision — seal the failed D-089 readiness probe without rerun

- Exact execution hash `sha256:dafb1182bc77a80a19384406a528997d608dc935201df63e7fdc1ef5aad471c3`는
  source commit `7f3e6debb2a67f4b108c4422fa4cf51ebfea994f`에서 한 번 소비됐다.
- `run_e444de1bb20a4325`는 terminal·qualified 27/27이지만 evaluator 전에 total-token guard로 끝났다.
  1,956,109 token 뒤 remaining 43,891, next required 58,804, deficit 14,913이다. Wall headroom은 171,305ms다.
- Gate는 false다: terminal/qualified 1/1, evaluator/official 0/1, budget-terminal 1, 다른 process confound 0이다.
  Hidden outcome과 task correctness는 관측되지 않았다.
- 79 provider response와 121 tool call을 기록했고 fixed-rate cost는 `$2.28858675`다. Seal 작업 자체는 provider
  call 0과 model cost `$0`이다.
- Raw result SHA는 `sha256:60dccc5e58e53accba3c2c68d241fc0d79bf1752f0fea8866c30de1594065b55`다.
  Portable evidence는 `reports/live-pilot/anyio-workflow-completion-budget-only-v2v5-20260804-r1.json`, SHA
  `sha256:06006c95454618b7adcea305465fa63611d2043c70aaa3e1df2de9a3f5a192f1`다.
- D-089 ID를 static consumed set에 추가한다. 자동 rerun, 새 budget/prompt/tool/context, baseline, memory
  admission/index와 core authority는 열지 않는다.
- Final verification은 focused 232/232, repository-wide sharded 1,533 collected 중 1,526 passed/7 skipped이며
  final D-090 report/plan/manifest retest 4/4, Ruff, compileall, JSON parse와 `git diff --check`를 통과했다.
- Date: 2026-08-04

### D-091 accepted analysis decision — classify the AnyIO tail without another live run

- D-087 AnyIO r2와 D-089의 public manifest, qualification, event/checkpoint metadata를 read-only 재집계한다.
  Private assertion, hidden/reference/candidate patch와 request/response/tool artifact body는 분석하지 않는다.
- D-089은 seq 103 `PatchApplied` event 뒤 1,772,530 token, 68 model/96 tool call 동안 추가 `PatchApplied` event가 0이고 14 patch가
  rejected됐다. Visible check는 6회 모두 false이며 마지막 check 뒤에도 863,211 token을 사용했다.
- D-087 r2도 check 0/8이고 budget terminal이지만 여섯 mutation이 있었다. 동일 task r1은 534,853 token에서
  evaluator에 도달했으므로 D-089을 D-087의 deterministic continuation이나 budget causal effect로 보지 않는다.
- Qualification과 retry rehydration은 두 run 모두 통과했으므로 confirmed harness defect는 아니다. 동시에
  harness defect를 ruled out하지 않으며 classification은 `qualified-process-nonconvergence-ending-in-budget-terminal`다.
- 2.4M과 3M은 관측 prefix의 token threshold만 넘기고 171,305ms wall headroom을 바꾸지 않는다. Completion,
  evaluator arrival, sufficient budget과 agent correctness는 추정하지 않는다.
- Artifact는 `reports/live-pilot/artifacts/d091-anyio-public-trajectory-audit.json`, SHA
  `sha256:74b6b229520d3358e7fbd33faad3b0be532405bbe5711a35c4d064114ba8e9a7`이다. Provider/evaluator call과
  added model cost는 0/0/$0이다.
- Final verification은 focused 238/238, repository-wide sharded 1,539 collected 중 1,532 passed/7
  environment-dependent skipped이며 Ruff, compileall, JSON/hash와 `git diff --check`가 통과했다.
- 자동 rerun, budget/prompt/tool/context 변경, baseline, comparison denominator, memory admission/index와 core를
  열지 않는다. 다음 decision은 public cross-task offline evidence만으로 retain/fail-fast/context-ceiling 중 선택한다.
- Date: 2026-08-04

### D-092 accepted policy decision — retain current policy and count qualified budget terminals as agent failure

- D-081 r3 4개, D-085/D-086 pilot 1개, D-087 12개와 D-089 1개, 총 18-run·8-task·4,079-event panel을
  public manifest/event metadata만으로 offline replay한다. Harness commit과 total-token ceiling이 다르므로
  performance comparison이나 denominator로 재해석하지 않는다.
- Repeated-rejection `N=3..10`은 각각 4/3/3/2/2/2/2/2 run을 trigger했고 false stop은
  3/2/2/1/1/1/1/1개다. D-089을 잡는 모든 tested threshold가 later public progress가 있는 AnyIO run도 자른다.
- Relative-context `{2,4,8} × {8,16,32 calls}` 9개 candidate도 모두 false stop이 있고 safe generic
  3-task/leave-one-task-out coverage를 만들지 못한다.
- Absolute 90k character sensitivity는 D-089 하나에서 false stop 0과 824,161 observed suffix token을 보이지만
  post-hoc single-task evidence이고 admission scope 밖이다.
- 따라서 exact selection은 `retain-current-policy-and-count-qualified-budget-terminal-as-agent-failure`다.
  이는 현재 정책의 최적성이나 future guard 불필요성을 증명하지 않는다.
- Qualified budget terminal outcome을 `agent_failure`로 선택했지만 exact four-condition denominator consumer
  binding은 다음 offline gate다. Live execution, baseline denominator, memory admission/index와 core는 열지 않는다.
- Artifact는 `reports/live-pilot/artifacts/d092-public-policy-replay-decision.json`, semantic body SHA는
  `sha256:6fde1253a7ba92a2cb60b09f05bc070849c1f868e96cc00870cf03eff62782ec`, file SHA는
  `sha256:541b890e2b123a5431060e23dcf4544fce3f7b810cb8cb1a560fbcc245b3fe22`다.
- D-092 provider/evaluator call은 0/0이고 추가 model cost는 `$0`이다.
- Final verification은 focused 20/20, repository-wide sharded 1,559 collected 중 1,552 passed/7
  environment-dependent skipped이며 Ruff, compileall, JSON/hash와 `git diff --check`를 통과했다.
- Date: 2026-08-04

### D-093 accepted correction — budget-confounded readiness is inconclusive

- D-092가 tested stall-policy candidate를 기각하고 current runtime을 유지한 계산과 결론은 보존한다.
- D-092 artifact, journal, qualification과 두 AnyIO raw `RunResult.outcome_kind=agent_failure`는 수정하지 않는다.
- Readiness 단계에서는 evaluator 전 budget terminal을 `readiness_inconclusive` / `budget_confounded`로 해석한다.
  Comparison failure disposition은 explicit content-addressed resource-policy freeze 전까지 pending이다.
- Historical exact run의 자동 재실행은 허용하지 않는다. Small diverse high-headroom successor는 별도 source gate,
  clean no-call preflight, new execution hash와 사용자 비용 승인을 거쳐야 한다.
- Candidate panel은 AnyIO, pyfakefs, HF Hub 각 1회와 3M token/3,600초/model-tool call `null`이지만 아직 freeze나
  실행 권한이 아니다. Task success, hidden acceptance와 SCRR은 readiness pass 요건이 아니다.
- Artifact는 `reports/live-pilot/artifacts/d093-readiness-budget-outcome-correction.json`, semantic body SHA는
  `sha256:3a5790e57252132387b803681339e00032c62f7026a81d9acbd9f4598fc64ccd`, file SHA는
  `sha256:df8a35d7818dba3055ee4bb34519bd39abdc97d4d6add178d3d41b0521273941`다. D-088/D-090
  portable seal이 raw outcome, evaluator boundary와 resource maximum을 exact hash로 뒷받침한다.
- D-093 provider/evaluator call은 0/0이고 추가 model cost는 `$0`이다. Baseline, denominator, memory
  review/admission/index와 core authority는 계속 닫혀 있다.
- Final verification은 focused 32/32, repository-wide sharded 1,571 collected 중 1,564 passed/7
  environment-dependent skipped이며 Ruff, compileall, exact rebuild, JSON/hash와 `git diff --check`를 통과했다.
- Date: 2026-08-04

### D-094 accepted source decision — freeze a diverse high-headroom readiness panel

- Exact suite는 `generic-high-headroom-readiness-v2v5-20260804-r1`이고 AnyIO, pyfakefs, HF Hub를 순서대로
  각 1회 `no_memory`로 실행하도록 source만 고정한다.
- Runtime은 `gpt-5.4-mini-2026-03-17` medium/standard/default, SDK retry 0, prompt V3, tool v2,
  context v5, output 25,000과 `null/null/3,000,000/3,600`이다. 새로운 high-headroom runtime/evidence/gate
  schema와 exact experiment ID를 함께 결속한다.
- 2026-08-04T14:47:00Z standard rate `$0.75/M` input, `$0.075/M` cached input, `$4.50/M` output을
  기록한다. Worst-rate reserve는 `$13.6125`/run과 `$40.8375`/suite이고 source cap은 `$41`이다.
- Readiness는 3/3 terminal·qualified·accepted submission·official evaluator와 exact telemetry, persisted
  qualification recomputation, process-confound 0을 요구한다. Task success, hidden acceptance와 SCRR은 요구하지
  않는다.
- Artifact 경로는 `reports/live-pilot/artifacts/d094-high-headroom-readiness-source-gate.json`, semantic body SHA는
  `sha256:ab7be9ad2448d1016b88d451e271330844fc11d8fd4b890f08142618446ff929`, file SHA는
  `sha256:6887936ec141496e35e3a9d3bd6c34cf04cf02d1849bf80208677151a692c6ed`다. Source 단계는
  provider/evaluator를 호출하지 않고 execution hash, approval 또는 paid capability를 만들지 않는다.
- Historical runs와 결과는 immutable하다. Baseline, comparison denominator, memory review/admission/index와 core는
  닫혀 있으며, 다음 단계는 clean no-call preflight 뒤 exact hash에 대한 max-`$41` 사용자 승인이다.
- Final verification은 focused 56/56, repository-wide two-shard 1,627 collected 중 1,620 passed/7
  environment-dependent skipped이며 Ruff, compileall, exact rebuild, JSON/hash와 `git diff --check`를 통과했다.
- Date: 2026-08-04

### D-095 accepted result decision — seal passed workflow readiness without promoting performance

- Clean D-094 source commit `82fbb33f20cabb57a151db871782345c6cafa3f0`에서 approved execution hash
  `sha256:ae54b9cc14e3bcb80cbead61a003012cec4dbd0e8a205917b3cefdeaf0c11d75`를 한 번 소비했다.
- AnyIO `run_9fd10f7feeee4df5`, pyfakefs `run_7449597e84b94446`, HF Hub
  `run_9566c0367bd24f52`는 모두 terminal·qualified 28/28·accepted submission·official evaluator에 도달했다.
  Persisted qualification과 read-only recomputation도 3/3 일치했다.
- Original readiness gate는 passed다. Infrastructure/qualification/diagnostic/budget-terminal/terminal-loop와
  model-or-tool-call budget confound는 모두 0이고 63/63 response의 exact token telemetry, completed status,
  truncation disabled와 `store=false`가 확인됐다.
- Correctness outcome은 별도 보존한다. 세 run 모두 hidden fail, regression/scope/safety pass인 `task_failure`이며
  task success와 SCRR은 0/3이다. 이를 readiness gate를 뒤집거나 hidden-driven tuning의 권한으로 사용하지 않는다.
- Aggregate usage는 957,052 input + 48,805 output = 1,005,857 token, 63 model/119 tool call,
  fixed-manifest list-price `$0.9374115`다. 이는 invoice나 free-tier 적용액 주장이 아니다.
- Raw result SHA는 `sha256:1b0c7d7452b70d6221c40b284646e50286f8f12b1d125d54bf66c1d89a0cf2b2`,
  journal file/final-event SHA는 `sha256:d5164b3d34bf0ec392d879b62aa0624f001499b0cb89f10c24145ef0aa26905b` /
  `sha256:fbaa048e3ed89e33de868a7794aa8c7d30b1af915c486e51b174f9630a1083a3`다. Portable evidence는
  `reports/live-pilot/generic-high-headroom-readiness-v2v5-20260804-r1.json`에 둔다.
- Exact experiment는 hard-consumed이며 자동 rerun하지 않는다. D-095 sealing 자체 provider/evaluator call과 added
  model cost는 0/0/`$0`이다.
- 이 three-task one-repetition 결과는 calibration-only다. No-memory baseline, success-rate estimate, comparison
  denominator/resource-policy freeze, memory review/admission/index, core와 analysis는 계속 닫혀 있다.
- Final verification은 focused/relevant 303/303, repository-wide split 1,637 collected 중 1,630 passed/7
  environment-dependent skipped를 통과했다. File shard의 D-092 WAL/SHM order-sensitive invariant는 isolated
  process에서 통과했다. Ruff, compileall, exact rebuild, JSON/hash와 `git diff --check`도 통과했다.
- Date: 2026-08-05

### D-121 accepted preparation decision — seal no-start readiness and keep actual execution separately gated

- Exact D-120 candidate approval은 D-121 new-only implementation, offline tests, no-start readiness와 execution candidate
  준비에 한 번 소비됐다. D-119와 D-120은 historical이며 어느 파일도 retry, repair 또는 rewrite하지 않는다.
- 네 preparation artifact의 ID/body/file SHA와 크기는 receipt
  `d121preparationapproval_0f0627d6cdc6e63cd5d73eff66646406b7bbd1c64affb43fc35e0fa701b6fc79` /
  `sha256:0f0627d6cdc6e63cd5d73eff66646406b7bbd1c64affb43fc35e0fa701b6fc79` /
  `sha256:5a5592c2fff7deae63c50482d109c0d8e79ff4016fb96aaa8cb5a7b442d83606`, 14,662 bytes; readiness
  `d121readiness_8d1bbf95e3bb8fbe9717a0f3620cdd9985091d0695aff69622d92d046ad6be12` /
  `sha256:8d1bbf95e3bb8fbe9717a0f3620cdd9985091d0695aff69622d92d046ad6be12` /
  `sha256:3423bf9af71d9b69579115d65a2b67d2bdb39363748e40a9cb78bdd461ad94e6`, 32,423 bytes; candidate
  `d121executioncandidate_b37bde7b9f49f92118ca277e521cd409b1e51b6f97c1ad8c2e9ff5090a1c38ef` /
  `sha256:b37bde7b9f49f92118ca277e521cd409b1e51b6f97c1ad8c2e9ff5090a1c38ef` /
  `sha256:0e8ea35d4fda06ecfba180150062b873ada5b11dd98df7bd0416c557777db1c5`, 11,046 bytes; gate
  `d121_711b9c8e738128d3d03b42c3287bf57418e02348b12a2c10707e9ce5ba1fe592` /
  `sha256:711b9c8e738128d3d03b42c3287bf57418e02348b12a2c10707e9ce5ba1fe592` /
  `sha256:e9c05396e10770c4290b2e57235f32da6fe3997afcd3fdb109c3697cea773b50`, 15,514 bytes다.
- Readiness는 8 Docker commands, create 1, start/run/exec/probe 0, opaque access/read 0, residual 0이다. 오직 Docker
  configuration realization만 verified이며 runtime hash-only isolation, cutoff, projection isolation과 independence는 false다.
- Actual successor run은 unauthorized/count 0이고 retrieval/agent/core는 closed다. D-121 47/47와 D-119+D-121 82/82가
  통과했다. D-120 7 failures는 D-121 path 부재를 요구하던 historical assertion의 예상 실패이며 D-120 수정이나 D-121
  product regression이 아니다.
- 다음 승인은 exact D-121 candidate triple에 결속된 fresh two-session run 정확히 1회만 허용한다. D-119 retry/repair,
  retrieval, agent 또는 core로 확대하지 않는다.
- Date: 2026-08-08

### Historical D-120 accepted candidate decision — seal the consumed D-119 failure and require a separate D-121 execution approval

- D-119의 exact partial state를 rewrite하지 않고 append-only D-120 preflight/candidate/source gate로 봉인한다. D-119는
  `PARTIAL_CONSUMED_FAILED`, probe 결과는 `UNSEALED_UNKNOWN`이며 같은 실행을 retry, resume 또는 repair하지 않는다.
  Durable completed session과 sealed probe outcome은 모두 0이다.
- Cleanup failure는 current D-119 source와 운영자 관찰에 일치하는
  `HARNESS_CLEANUP_EVIDENCE_VALIDATOR_ERROR`로 기록하되, raw command transcript와 probe result가 journal에 없으므로
  `source-consistent-self-attested-diagnosis-not-portable-proof`로 제한한다. Probe 성공, source hash failure,
  container removal failure 또는 Docker isolation failure를 소급 주장하지 않는다.
- D-120 materialization은 D-119 receipt/preflight/journal과 implementation bytes 및 세 미생성 output을 exact하게
  재검증했지만 D-119를 실행하거나 수정하지 않았다. Docker/network call과 opaque source read는 0이며 이 zero-call
  주장은 source-path static audit와 focused forbidden-boundary test에 근거한 self-attested 경계이지 OS socket
  instrumentation 증거가 아니다.
- Preflight/candidate/source gate의 ID/body/file SHA와 크기는 각각
  `d120preflight_cc3496328cf64c924c762d47a7f4926d23322991c29064e68ae6d376a8339310`/
  `sha256:cc3496328cf64c924c762d47a7f4926d23322991c29064e68ae6d376a8339310`/
  `sha256:6ec5ff207fdf24cb8baab733b9db096ece3d1fe1ba0ba5c6c644ac6c20ccd5ea`, 21,101 bytes,
  `d120cleanupcandidate_86d95b4b3cf0b49a20724b136075bfa9da281fce4dc6b20b6063a07bfcdd9b82`/
  `sha256:86d95b4b3cf0b49a20724b136075bfa9da281fce4dc6b20b6063a07bfcdd9b82`/
  `sha256:f4f985e6574ead218ffea4813d234c1b5c35cdf60e109de5bbe0849dd25127d8`, 10,464 bytes,
  `d120_8172bae0e2446e647edb8d03272cf5499a9faa8f92a1f26b8cd08b5a9dc6abbd`/
  `sha256:8172bae0e2446e647edb8d03272cf5499a9faa8f92a1f26b8cd08b5a9dc6abbd`/
  `sha256:cd4fe9024bfb1b44e9e762412e442f3c2958085629b15e19f7a9423aefa3581b`, 12,140 bytes다.
- Exact D-120 candidate 승인은 D-121의 new-only implementation, offline tests, container를 시작하지 않는 exact
  Docker readiness preflight와 execution-authorization candidate 준비만 연다. Docker container start, opaque source
  read와 actual D-121 run은 열지 않는다. 실제 D-121 실행은 이후 생성될 exact D-121 candidate triple에 대한 별도
  사용자 승인이 필요하다.
- D-119+D-120 focused 검사는 76/76 통과했다. Repository-wide suite 통과로 확대하지 않는다. Trusted cutoff anchor,
  record projection isolation과 independence는 false이고 matcher/classifier/calibration, retrieval/runtime injection,
  agent/provider/evaluator와 core/analysis는 0/closed다.
- Date: 2026-08-07

### Historical D-119 execution decision — consume once, stop on cleanup failure, and preserve an unknown probe outcome

- D-119 approval receipt와 preflight의 ID/body/file SHA 및 크기는 각각
  `d119approval_671af8d6e7cbd44ef0793c1bf1bf53f3f5f8e3fcbfd26e04906cb4abdea50cce`/
  `sha256:671af8d6e7cbd44ef0793c1bf1bf53f3f5f8e3fcbfd26e04906cb4abdea50cce`/
  `sha256:625cd6487fffe50b2429e011c67da222ec0da020dbf62d65a911fa83da3f550c`, 5,299 bytes와
  `d119preflight_85dcbc49bec53797904f080d0e6922b521a9f6f232902e122895090e5f886dd1`/
  `sha256:85dcbc49bec53797904f080d0e6922b521a9f6f232902e122895090e5f886dd1`/
  `sha256:57f59fc29054276947851abdfe3dbf0040fe10cef5624946e66dc84a698fb18a`, 11,229 bytes다.
- One-use action hash `sha256:be673eec0b6cf5cde23db0f19c050d82867a1a4a497a28124f61ca47e24278c2`를
  소비한 journal은 2,075 bytes/file SHA
  `sha256:fadda3b86b2ad954a1d233b0dbf11d67b8a9a86f3db6704eab555eec5f2a4950`, 4 records, head
  `sha256:4bd08521b13431251449d79cb2847a93fc947cf2ce6e6b319e71f728cc74bd46`다. Event는
  `ExecutionClaimed → ImageIdentityVerified → IsolationSessionStarted → ExecutionFailed`에서 끝난다.
- External-anchor evidence, isolation evidence와 completion source gate는 생성되지 않았다. 따라서 first probe의
  성공/실패를 판정하지 않고 `UNSEALED_UNKNOWN`으로 유지하며, D-119 승인을 재사용하거나 partial run을 자동
  재시도하지 않는다.
- D-118의 `BLOCKED_INSUFFICIENT_PREEXISTENCE`, `trusted_cutoff_anchor_verified=false`와
  `independent=false`는 바뀌지 않았다.
- Date: 2026-08-07

### Historical D-118 accepted evidence decision — bind opaque public-development sources but fail closed on preexistence and isolation

- Exact D-117 candidate triple에 대한 사용자 승인은 공개 development benchmark metadata 조사, revision-pinned opaque
  snapshot 다운로드와 membership/cutoff/isolation hash preflight에만 사용했다. D-117이 제안한 후속
  execution-authorization-candidate action은 승인하거나 소비하지 않았다.
- SWE-bench dev `f5351ee8c6663736817027db3ad03fe662cb5bb8`과 SWE-Gym train
  `26a6eae79ae9cb6d4307c3cc99c126fbf23cb3f0`의 `.gitattributes`, `README.md`, 단일 Parquet shard를
  각각 binary hash-only로 결속했다. 최종 집합은 6개 파일, 45,036,395 bytes다. Parquet metadata/schema/row와
  issue prose, label, patch, test 또는 oracle field는 읽지 않았다.
- `swe-bench-dev-f5351`은 작은 official development surface 때문에 provisional priority 1로 기록했을 뿐이다.
  Source pool selection/acquisition/freeze나 independent control admission은 없으며 두 후보 모두 `post_hoc=true`,
  `independent=false`, independent calibration 부적격이다.
- Provider의 revision/tree/membership/GPG badge 관찰은 self-attested source research로 명시적으로 낮췄다. Bound
  input에서 provider tree·membership proof를 재구성하지 못했고 exact snapshot과 membership rule을 함께 묶는 trusted
  pre-D-116 anchor도 없다. Isolation profile은 immutable image digest와 실행된 negative probe가 없는 계획이므로
  technical isolation evidence가 아니다. 따라서 disposition은 `BLOCKED_INSUFFICIENT_PREEXISTENCE`이고
  execution-authorization candidate는 준비되지 않았다.
- Receipt/preflight/evidence pack/source gate의 ID/body/file SHA와 크기는 각각
  `d118approval_2a7461b834374e4a34db8c02850501d0ad9e8416e7a4bf7f73613abef08713a2`/
  `sha256:2a7461b834374e4a34db8c02850501d0ad9e8416e7a4bf7f73613abef08713a2`/
  `sha256:0adb87887b42a19aa8d1b9be3ca5268801666bbecb2cf94b4664e3df1dba8344`, 4,199 bytes,
  `d118preflight_1f11c66f174e5e475ef9d94df7810c568857f02a8164edf30287778276dab4b0`/
  `sha256:1f11c66f174e5e475ef9d94df7810c568857f02a8164edf30287778276dab4b0`/
  `sha256:4f4bff33cbf55e841f86da0a30fc67885f9302fa2f149dde040a3d85a2c4c0b3`, 17,476 bytes,
  `d118evidencepack_e40dad5ceac6dcfbb29d47bec3a548c44bdcbeba964e4e7a43818b76e8c62f10`/
  `sha256:e40dad5ceac6dcfbb29d47bec3a548c44bdcbeba964e4e7a43818b76e8c62f10`/
  `sha256:318d4f58276283e6e6ae6c45c4afe50af5bca6b6937ffa841b8b791a0357c6b1`, 25,451 bytes,
  `d118_cdd55277ad1dc1215a45aa3588e7862df3535b91b7274681fe0a8488abd3e707`/
  `sha256:cdd55277ad1dc1215a45aa3588e7862df3535b91b7274681fe0a8488abd3e707`/
  `sha256:0f01a2b315f9c32c34b8c2400af6f22a1c4f2538b2538f8597f2ab0b8d57c343`, 17,748 bytes다.
- Focused D-117+D-118 검사는 48/48 통과했다. Repository-wide suite 통과로 확대하지 않는다. Issue/task record
  read, labeling/review, matcher/classifier/calibration, retrieval/injection, agent/provider/evaluator call은 모두 0이고
  core/analysis는 closed, added model cost는 `$0`다.
- 다음 gate는 exact snapshot과 membership rule을 함께 결속하는 trusted pre-D-116 anchor와 immutable image에서
  실제 실행된 isolation negative-probe evidence다. 그 전에는 admission, execution-authorization candidate,
  matcher/calibration, retrieval, agent 또는 core를 열지 않는다.
- Date: 2026-08-07

### Historical D-117 accepted implementation decision — seal a grammar-blind public-development control-acquisition protocol without acquiring a pool

- Exact D-116 candidate triple과 next-action hash
  `sha256:e368dcb794875064f605a341902b4c27be20fcb3ff9b86d65ca5fb66dbf35e55`의 별도 사용자 승인은 D-117 새
  module/script/test와 receipt/preflight/candidate/source gate를 만드는 데만 소비했다. Actual pool discovery/acquisition,
  public issue read, role session, review/label, matcher/classifier/calibration, score/retrieval/agent/API/core는 승인하지 않았다.
- Future pool scope는 public-development control 전용이고 held-out task·issue·result와
  private/hidden/reference/patch/trace/evaluator lineage를 fail closed로 제외한다. Exact source bytes와 membership
  manifest 또는 exhaustive inclusion rule은 D-116 cutoff `2026-08-07T06:22:51.021003Z`보다 먼저 신뢰 가능한 외부
  anchor에 결속돼야 한다. Issue `created_at`, filesystem mtime, Git timestamp, self-attestation 또는 현재 fetch/hash만으로는
  preexistence가 아니다.
- Protocol author/current conversation actor, D-116 grammar observer와 same-checkout subagent는 blind role에 부적합하다.
  Future assembler는 D-105/D-116을 보지 않고, selector A/B와 adjudicator에는 opaque control ID, canonical public
  title/description/language와 exact D-105 applicability rubric만 제공한다. First-pass 결과는 cross-reveal 전에 각각
  봉인한다. 이 contract는 process input isolation을 요구하지만 인간의 사전 지식 부재를 cryptographically 증명하지 않는다.
- Preexistence, development-only split, lineage, role isolation, first-pass seal, evidence span 또는 chain-of-custody가
  불완전하면 record를 보존하면서 `post_hoc=true`, `independent=false`로 낮춘다. Zero-control 결과도 유효하며 ontology나
  grammar를 약화하거나 observed label에 맞춰 pool을 확장하지 않는다.
- Receipt/preflight/candidate/source gate의 ID/body/file SHA와 크기는 각각
  `d117approval_f70a2ff210ae2df203591b9650177161ca71084da256e994539af09a48deeae9`/
  `sha256:f70a2ff210ae2df203591b9650177161ca71084da256e994539af09a48deeae9`/
  `sha256:40ea64548634353a12b48f8bcabce941df47e16f9b27d892722d55fcda1e5e13`, 10,096 bytes,
  `d117preflight_34645da3c09db9d3ba288425b44e0e27f631e8b034a231abd7e113dbdeea5464`/
  `sha256:34645da3c09db9d3ba288425b44e0e27f631e8b034a231abd7e113dbdeea5464`/
  `sha256:6682f4f2870cdb34e6ee766333c95ac58a406a7d4e4086d6086752650869c305`, 29,919 bytes,
  `d117blindprotocolcandidate_27622afdd9d46e43cb9e23675a334b5a4e91fc768298374cae61ab440c850dae`/
  `sha256:27622afdd9d46e43cb9e23675a334b5a4e91fc768298374cae61ab440c850dae`/
  `sha256:d10bbe5b3b65050868a1202cd1af9f130c89bbe43ceccf9359af145cac96cda7`, 7,999 bytes,
  `d117_750cd5a0a8946984aafe75b0939417bf026120cdb3dbc54d09180fd795202589`/
  `sha256:750cd5a0a8946984aafe75b0939417bf026120cdb3dbc54d09180fd795202589`/
  `sha256:a439fc936b5b594c043b4ea90cd57bb676e79004cf4de8794b83f3af15fb13e3`, 16,813 bytes다.
- D-117은 source pool/issue를 이름 붙이거나 읽지 않았다. Pool manifest/member, trusted cutoff verification, role/isolation
  session, blind packet, selector/adjudication result, independent control/positive는 모두 0/false다. Matcher/classifier/
  calibration implementation·execution, model/embedding load, retrieval/injection, agent/provider/evaluator/network-capable call도
  모두 0이고 added model cost는 `$0`다. Network evidence는 source-path/self-attested이며 OS socket block/instrumentation은
  검증하지 않았다.
- D-117 focused 25/25와 D-116+D-117 연속 46/46이 통과했다. 이는 repository-wide suite 통과가 아니다. Candidate
  status는 `protocol-sealed-no-pool-inspected-acquisition-and-independent-positives-still-blocked`, next-action hash는
  `sha256:362cf3f74c9d57ecc4238f4b7c024b470c8ad65038ee6a599581a1df82fc6c06`다.
- 다음 gate는 exact D-117 candidate triple과 external public-development source snapshot, pre-D-116 membership,
  trusted cutoff anchor, isolation profile의 exact triples를 함께 요구하는 D-118 **execution-authorization candidate
  준비만**이다. 그 gate도 actual acquisition/review, matcher/classifier/calibration, score/retrieval/agent/core authority가 아니다.
- Date: 2026-08-07

### Historical D-116 accepted implementation decision — seal the formal public-applicability contract without executing it

- Exact D-115 candidate/action 승인은 D-116 새 module/script/test와 receipt/preflight/candidate/source gate를 만드는
  범위로만 소비했다. Public development inputs만 허용하고 private/hidden/reference/known-bad/held-out, task ID·path,
  phase, trace/patch/test 결과와 D-112 hypothesized group은 classifier input에서 제외한다.
- 입력 projection은 `issue_title`, `issue_description`, `language` exact key set이다. NFKC, LF, casefold와 whitespace
  collapse를 고정하고 language는 Python만 지원한다. Invalid/noncanonical projection은 `CONTRACT_ERROR`, unsupported
  language는 text matching 없이 `ABSTAIN/UNSUPPORTED_LANGUAGE`다.
- CPython 3.12 stdlib `re` grammar에 token/sentence/clause segmentation, token offset, negation, all-atom tuple 및
  minimum-distinct-atom 선택, cross-predicate span reuse, contradiction 우선순위, evidence/result collection ordering을
  결정적으로 명시했다. Taxonomy/input/result/abstention/predicate hash는 각각
  `sha256:910b02269b16d8277a48dfd0353724e06c5aea988874b9dcb89e062cd1508b45`,
  `sha256:24a0d5102b5066dd19b8cc9b68cf8d84bbb70b4f364e604ea804fab120a260b2`,
  `sha256:ae1536068aa28142e289feb97045bd289ca1dbf0df70a8d25777a9885df220d9`,
  `sha256:1ad0614589c555c285befb51f7e28e80f7b3e5c0f155116e05e08295bc09063c`,
  `sha256:c9e88df2d48ea1d089da11ec394fd41daa2d3e377b3058899e9f530b51548bf1`다.
- Public inventory 10개 중 eligible 8개와 bootstrap exclusion 2개를 고정했다. Pyfakefs/HF Hub 두 source anchor는
  contract authoring에 사용된 in-sample/non-independent conformance evidence다. Tox association은 S3 shared error
  boundary가 public prose에 없어 label이 아니며 Moto D-112 hypothesis도 label이 아니다. Blind independent positive는
  0개다. Plan hash는 `sha256:a53c25ad05eb3cbedadde5c22f0ad226db17e6713fc33f3d8fb6ea7c7a613c8a`이고
  `three_class_calibration_ready=false`, `calibration_execution_ready=false`다.
- Receipt/preflight/candidate/source gate의 ID/body/file SHA와 크기는 각각
  `d116approval_016c99bd81a756f640cf10132eda196057cb3a50a59cf593d64e215dc4d47bcb`/
  `sha256:016c99bd81a756f640cf10132eda196057cb3a50a59cf593d64e215dc4d47bcb`/
  `sha256:86c4e279df6c3d4b6ea02719375f76370d76fb795d642f2d10211e878662ba77`, 12,014 bytes,
  `d116preflight_e9005e90895ea4554ea04b21b025ff1afc42076d4e08a7adef2b6476cbf06a3f`/
  `sha256:e9005e90895ea4554ea04b21b025ff1afc42076d4e08a7adef2b6476cbf06a3f`/
  `sha256:fc2602a385242204ab9ae274ea6c73a83bd00a00eace88c7f310a57b5d4655f5`, 76,157 bytes,
  `d116classsignalcandidate_0b1b700af4ce2274cb9cb032ecf23c741ec9c41b0e86abbc06e96e18f91c74d4`/
  `sha256:0b1b700af4ce2274cb9cb032ecf23c741ec9c41b0e86abbc06e96e18f91c74d4`/
  `sha256:8299f3d400bd9412a8b7100305a0eb57f1d5b4ea78a39d8e5edad6cd5a2b15ca`, 8,017 bytes,
  `d116_e93b1d39428c3778dd1f55dd0ae1a6c7f4b2091f9b4a92c347f6b7b3c6a66c37`/
  `sha256:e93b1d39428c3778dd1f55dd0ae1a6c7f4b2091f9b4a92c347f6b7b3c6a66c37`/
  `sha256:f03bc7806d8401b9ac9f3d9e47df7b0ef19b16a04380bed1c9cb1d105e52320d`, 19,859 bytes다.
- Formal grammar와 plan은 봉인했지만 matcher evaluator/classifier와 calibration executor를 구현하지 않았고
  matcher/classifier/calibration도 실행하지 않았다. Focused 21/21이 통과했다. Model/embedding load, retrieval,
  runtime injection, agent/provider/evaluator와
  network-capable call path는 모두 0, added model cost는 `$0`다. Network evidence는 source-path/self-attested이고
  OS-level socket block/instrumentation은 검증하지 않았다. True relevance와 corrected policy는 확립되지 않았다.
- Candidate status는
  `formal-matcher-contract-sealed-calibration-blocked-on-grammar-blind-preexisting-control-protocol-and-public-applicability-positives`다.
  Next-action hash `sha256:e368dcb794875064f605a341902b4c27be20fcb3ff9b86d65ca5fb66dbf35e55`는
  D-117 `prepare-grammar-blind-preexisting-public-applicability-control-acquisition-protocol-candidate`만 제안했다.
  Source pool·exact membership·bytes·provenance는 D-116 이전 상태로 고정돼야 한다. Pool assembler와
  selector/adjudicator는 grammar/hash/output에서 격리되고, selector/adjudicator는 D-105 applicability rubric만 받는다.
  현재 process/agent는 blind selector가 될 수 없으며 blinding을 증명하지 못하면 post-hoc/independent=false로
  처리한다. 이 exact gate는 이후 D-117 protocol candidate에 한해 소비됐고 classifier/calibration 실행, score/index
  변경, retrieval/injection, agent/API/network, core/analysis 권한으로 확대되지 않았다.
- Date: 2026-08-07

### Historical D-115 accepted implementation decision — defer policy mutation and seal a public class-signal contract candidate

- D-114 strict successor가 검증한 exact D-112 public score row 9개만 offline 입력으로 사용한다. Private/hidden,
  reference/known-bad, raw trace/patch와 held-out 결과는 읽지 않는다.
- D-112 Moto group hypothesis는 acceptance ground truth가 아니다. Observed matrix 계산에는 저장된 component만
  사용하고, hypothesis는 명시적으로 non-runtime/non-acceptance인 counterfactual class signal을 구성하는 데만 쓴다.
- Current failure-class/validation은 모두 0이고 probe 내 phase/language는 entry별로 같다. Moto hypothesized group은
  rank 3/score `0.30430094253875567`이며 Moto observed top non-hypothesized group score는
  `0.3541890713468577`, Babel lowest/top은
  `0.3514907443341587`/`0.39188659397843584`다. Threshold-only로 Moto를 선택하면서 Babel을 no-match로
  유지할 구간은 없고, nonnegative current-feature weight만으로도 hypothesized group을 top으로 만들 수 없다.
- 따라서 corrected policy를 선택하거나 구현하지 않는다. Conditional tuple
  `{semantic: 0.25, failure_class: 0.40, phase: 0.15, language: 0.10, validation: 0.10}`, threshold `0.60`은
  독립적인 deterministic abstaining public classifier가 있다고 가정한 비권위적 counterfactual이다. 그 가정에서
  Moto IMPLEMENT hypothesized score `0.6530721018133969`, Babel top `0.3156332814131685`, Moto REPRODUCE
  hypothesized score `0.503072101813397`, phase delta `0.1499999999999999`가 나오지만 runtime classifier와 true
  relevance는 관찰되지 않았다.
- Preflight ID/body/file SHA와 크기는
  `d115preflight_c9af86f3dd2f5e68316cd36290fcadb1ca8b2cfbe5627d6c6a531246183ba12b`/
  `sha256:c9af86f3dd2f5e68316cd36290fcadb1ca8b2cfbe5627d6c6a531246183ba12b`/
  `sha256:91908b43eb581b09249f8285e5f1d09389092c5b40c1c794b9ab139667c86bad`, 59,725 bytes다. Candidate는
  `d115scoredecisioncandidate_91e3ef5af000fe830483012b5deee4eeb47f5a117fa5904d93d713b03f2308ec`/
  `sha256:91e3ef5af000fe830483012b5deee4eeb47f5a117fa5904d93d713b03f2308ec`/
  `sha256:1fd424eab88c60a9d8480e756642b2c70b03afd03dd777e27bf36a3ea428df7a`, 6,839 bytes다. Source gate는
  `d115_ab5e8f0e9f57c5fb37f05137da5b6cf8ca6421856ade33616448023d39c4a805`/
  `sha256:ab5e8f0e9f57c5fb37f05137da5b6cf8ca6421856ade33616448023d39c4a805`/
  `sha256:67f62c23e9f5e14fe9cd1d075b2c6f679764c18644837914b0031348c4a21b72`, 13,730 bytes다.
- Focused 19/19이 통과했고 protected input fingerprint는 build 전후 같다. Model load/encode, retrieval,
  injection, agent/provider/evaluator call은 0이고 added cost는 `$0`다. Network 0은 source-path/self-attested이며
  OS-level socket block/instrumentation 증거가 아니다. `score_policy_correction_authorized=false`,
  `retrieval_ready=false`, `core_campaign_unlocked=false`다.
- Exact D-115 candidate triple 승인은 이후 D-116 contract/plan materialization 범위로만 한 번 소비됐고, policy
  mutation, retrieval/injection, agent/API/network, core와 analysis 권한으로 확대되지 않았다.
- Date: 2026-08-07

### D-114 accepted execution decision — complete one append-only D-112 validator correction

- 사용자가 exact D-113 candidate triple을 별도 메시지에서 다시 제시하고 D-114 새 module/script/test와
  append-only receipt/gate 생성 1회만 승인했다. D-112 실행-bound 파일과 artifact, index/marker는 수정하지 않는다.
- Successor validator는 D-112 receipt/gate의 exact root/body/claim key set과 full expected payload equality,
  approval → execution → completion chronology와 paired rehash rejection을 강제한다.
- `sealed-historical` validation은 local snapshot이나 exact installed embedding dependency 없이 checked-in frozen
  index, D-112 gate vectors와 public specs로 9개 score row를 재계산한다. `current-input` validation은 별도 opt-in이다.
- Receipt ID/body/file SHA와 크기는
  `d114approval_20d5025c5d72b156e8470812a0062da2d4d639aa2fa9848ef38da96a71112fd7`/
  `sha256:20d5025c5d72b156e8470812a0062da2d4d639aa2fa9848ef38da96a71112fd7`/
  `sha256:1f494579e70d9e8a7f0d28439578afc3b3aa77c7735ac8bc4e81627cab70793b`, 10,493 bytes다. Gate는
  `d114_8f378245c6965d59cd5e589a67cea203e502553e19fa9391b11a667db09271fb`/
  `sha256:8f378245c6965d59cd5e589a67cea203e502553e19fa9391b11a667db09271fb`/
  `sha256:c336004f12f187ab0bfb7946204f877c088703d25e809a8e79e9ec84d374be11`, 15,686 bytes다.
- Focused 35/35가 통과했고 protected D-112/index bytes는 전후 같다. Correction evidence materialization은 정확히
  1회다. Original D-112 guarantee나 결과를 소급 변경하지 않는다.
- Model load/encode, retrieval, runtime injection, agent/provider/evaluator call은 0이고 added cost는 `$0`다.
  Network claim은 source-path/self-attested이며 OS socket block은 검증하지 않았다. Score policy, retrieval,
  runtime injection, core와 analysis는 계속 닫는다.
- Date: 2026-08-07

### D-113 accepted implementation decision — seal a validator-correction candidate only

- 사용자의 일반적인 진행 요청은 D-112의 알려진 검증 한계를 고치는 실행 승인으로 확대하지 않는다. 먼저 exact
  D-112 artifact/source에 결속된 offline authorization candidate만 만든다.
- D-112 module/script/test, receipt/gate와 frozen/unfrozen index는 수정하거나 재실행하지 않는다. D-113은 exact
  bytes를 읽고 AST 구조를 감사한 새 preflight/candidate/source gate만 생성한다.
- Stable finding은 `skip-current-not-portable`, `receipt-validator-not-exact`,
  `timestamp-chronology-not-enforced`, `one-use-repository-local-only`,
  `network-zero-not-socket-instrumented` 다섯 개다. 실제 D-112 timestamp 순서는 정상이다.
- Future D-114는 새 module/script/test와 append-only receipt/gate만 만들 수 있다. Full payload/key equality,
  paired rehash 거부, chronology, current/sealed mode 분리와 snapshot/model 없는 portable replay를 acceptance로
  결속한다. 기존 D-112 또는 index mutation, policy/threshold/rank 변경, retrieval/injection/agent/API/core는 금지한다.
- Candidate ID/body/file SHA는
  `d113validatorcandidate_373257ce1e2c904482a2aeb4649495baf737a11b3c958ef8420b66640a7f3732`/
  `sha256:373257ce1e2c904482a2aeb4649495baf737a11b3c958ef8420b66640a7f3732`/
  `sha256:4b576b6b7edbb7ebf9813e8c4ac35fae7af88992dc4dac3a28a181f79aa6e8a9`다.
- Focused 18/18이 통과했다. D-111~D-113 연속 회귀는 5분 제한에서 시간 초과되어 통과로 합산하지 않는다.
  Model/retrieval/agent/provider/evaluator call과 added model cost는 모두 0/`$0`다.
- Exact candidate triple의 별도 사용자 승인 전에는 `validator_correction_authorized=false`이고 D-114 구현도
  시작하지 않는다. Score policy, retrieval, runtime injection, core와 analysis도 계속 닫는다.
- Date: 2026-08-07

### D-112 accepted execution decision — consume the exact D-111 local scoring diagnostic once

- 사용자가 D-111 candidate ID
  `d111retrievalcandidate_bfde5cfe1c75cd90e8d78a0960b6d5ac7986420016d805e75b9725abdb20fe7a`, semantic body
  SHA `sha256:bfde5cfe1c75cd90e8d78a0960b6d5ac7986420016d805e75b9725abdb20fe7a`, file SHA
  `sha256:f91aa284cc7a2add2516f44b4397b29e3aee5caa4cf0f83ec7913e6e5d7899d6`를 별도 메시지에서 다시
  제시하고 D-112 구현과 local read-only scoring diagnostic 1회만 승인한 것을 실행 권한으로 받아들인다.
- D-111 `future_output_paths`에 없는 journal이나 approval file을 추가하지 않는다. 지정된 probe receipt 자체를
  self-attested approval sidecar와 exclusive one-use claim으로 사용한다. Receipt 생성 뒤 실패나 hard kill은
  consumed/incomplete이며 자동 retry나 rollback을 하지 않는다.
- Pinned snapshot을 CPU/local-files-only/library-offline로 정확히 한 번 load하고 public query 세 개를 한 batch에서
  정확히 한 번 encode한다. Query vector full values와 float32 SHA를 보존해 이후 validation은 model-free다.
- Current score policy와 threshold를 바꾸지 않는다. 실제 9개 score row에서 세 probe 모두 no-match였고 Moto
  positive hypothesis의 hypothesized group이 top rank가 아니었다. 이 관찰을 execution failure나 memory effect로
  재분류하지 않는다.
- Receipt ID/body/file SHA는
  `d112probereceipt_ad73368b4b0f47174f53762c917f9f39f17e22ac3bd077d795b0b9e1ac8c9257`/
  `sha256:ad73368b4b0f47174f53762c917f9f39f17e22ac3bd077d795b0b9e1ac8c9257`/
  `sha256:74fcd761cac65a9cab26529076b7cde60eaa14a1faf40475e680f526e00ba1d1`다. Gate ID/body/file SHA는
  `d112_3242bed73c9a322ff1d346eba61cfec2f9eae3b57e4cc7e4d7b0e9a5456367b6`/
  `sha256:3242bed73c9a322ff1d346eba61cfec2f9eae3b57e4cc7e4d7b0e9a5456367b6`/
  `sha256:a7e691ae43c60405cbb10cd27caf3055eabaa96bb7fa6f2a02142d97aa903951`다.
- Focused 11/11과 D-111/공용 memory 회귀 13/13이 통과했다. Repository-wide와 D-106~D-110 전체 회귀는
  실행하지 않았다. Provider/evaluator/agent/retrieval call 0/0/0/0, runtime injection 0, added cost `$0`다.
- `retrieval_ready`, retrieval experiment, score correction, core와 analysis는 계속 false/closed다. 다음 단계는
  별도의 offline score-policy decision candidate를 준비할지 결정하는 것이며 자동 correction이 아니다.
- Post-execution audit는 actual artifact와 score를 확인했지만 validator strictness gap도 찾았다. Skip-input flag가
  current snapshot/dependency를 여전히 요구하고, receipt의 fully-rehashed unknown/unchecked field와 timestamp chronology를
  모두 차단하지 못한다. One-use는 global authorization이 아니라 repository-local cooperative file claim이다.
  D-112 implementation binding이나 gate를 사후 rewrite하지 않고 separately authorized append-only correction으로 남긴다.
  따라서 score-policy decision보다 validator-correction candidate를 우선 검토한다.
- Date: 2026-08-07

### D-111 accepted decision — seal a retrieval-readiness candidate without executing retrieval

- Exact D-110 frozen index/marker를 다시 검증하고 public dev-validation 세 probe만 결속한다:
  `moto-query-scanned-count`/`IMPLEMENT`, `babel-strict-grouped-decimal-trailing-zeroes`/`IMPLEMENT`,
  `moto-query-scanned-count`/`REPRODUCE`. Private/hidden/reference/known-bad patch는 읽지 않는다.
- Preflight ID/body SHA는
  `d111preflight_ee48af2da2ab34bb252f11842fe34c734229ad193776fc97bdd34dc3849003f9`/
  `sha256:ee48af2da2ab34bb252f11842fe34c734229ad193776fc97bdd34dc3849003f9`, 13,085-byte file SHA는
  `sha256:fed699e068c52e2dd929b654a65369aee3499d6d69c5a38c14dcee808ff57387`다.
- Candidate ID/body SHA는
  `d111retrievalcandidate_bfde5cfe1c75cd90e8d78a0960b6d5ac7986420016d805e75b9725abdb20fe7a`/
  `sha256:bfde5cfe1c75cd90e8d78a0960b6d5ac7986420016d805e75b9725abdb20fe7a`, 6,465-byte file SHA는
  `sha256:f91aa284cc7a2add2516f44b4397b29e3aee5caa4cf0f83ec7913e6e5d7899d6`다. Gate ID/body SHA는
  `d111_348e6dd21ad0816a3c4dc1889f2d7a421c7e41194c48b2fe5c7120513f6b3524`/
  `sha256:348e6dd21ad0816a3c4dc1889f2d7a421c7e41194c48b2fe5c7120513f6b3524`, 3,308-byte file SHA는
  `sha256:d550cb048e417965e482c64682df4a1b91b90067f66b36e370912f5a8d759c16`다.
- Natural public query는 current class/validation component에서 점수를 얻지 못해 완전한 semantic match와
  IMPLEMENT/Python을 가정해도 selective score 상한이 `0.65`다. Threshold `0.72`를 넘을 수 없으므로 positive
  hypothesis를 acceptance criterion으로 쓰거나 threshold를 조용히 낮추지 않는다.
- Legacy structured renderer는 D-105 exact model-facing text와 세 entry 모두 byte mismatch이고, query encoder는
  pinned snapshot의 local-only load를 강제하지 않는다. D-111은 이 gap을 기록할 뿐 retriever를 수정하거나 실행하지 않는다.
- Focused 8/8과 related 7/7이 통과했다. Retrieval/query embedding/runtime injection/provider/evaluator/core는
  모두 0/false다. 정확한 candidate ID/body/file SHA를 사용자가 별도 메시지에서 승인해야만 one-use local read-only
  scoring diagnostic을 허용할 수 있다. 그 승인도 runtime retrieval, injection, provider/evaluator 또는 core 권한이 아니다.

### Historical D-110 accepted execution decision — consume the exact one-use freeze approval

- 사용자가 exact D-109 candidate ID
  `d109freezecandidate_480d2aa8657fd143397fcfc71f252b8a8e3c0988d3950b5671089cf6dc8b8d46`, semantic body
  SHA `sha256:480d2aa8657fd143397fcfc71f252b8a8e3c0988d3950b5671089cf6dc8b8d46`, file SHA
  `sha256:ae8a8c6e58b058720943bae9088da2cf242168a70f654006557dd84c84d4e580`를 같은 메시지에서 다시
  제시하고 exact index freeze 1회만 승인한 것을 실행 권한으로 받아들인다. Retrieval, runtime memory injection과
  core campaign은 이 승인에 포함하지 않는다.
- Approval receipt는 `reports/memory-development/d110-exact-index-freeze-approval-receipt.json`, ID/body/file SHA
  `d110approval_cb0ab444a4c453fbf496e509891013163825c8b5c362204c43d37c7452d49e7b`/
  `sha256:cb0ab444a4c453fbf496e509891013163825c8b5c362204c43d37c7452d49e7b`/
  `sha256:f409c6296b1f87d8cb151fcc1866d263f3e74aa9341c46ab49ea3b4fef66a97c`, 3,495 bytes다.
  `recorded_at=2026-08-06T12:42:48Z`이고 self-attested approval일 뿐 reviewer identity 인증이나 cryptographic
  signature 증명이 아니다.
- One-use execution은 `2026-08-06T13:54:43.725943Z`에 시작했다. Exact pre-state를 다시 확인한 뒤 기존 index의
  `/frozen`, `/frozen_at`, `/authority/index_freeze_authorized`, `/authority/memory_index_frozen`,
  `/content_hash` 다섯 pointer만 변경한다. Automatic retry와 rollback은 하지 않으며 one-use capability는 소비한다.
- Post-freeze index는 55,687 bytes/file SHA
  `sha256:c0d2ec424e6cc10d64cdebd5ae493e0546fdfa08d09eb5f3269557b46025c6d0`, content hash
  `sha256:3a99e6c190672d1676bc4d13604de989899de9ddac85d282cc90c4d56f426c56`,
  `frozen_at=2026-08-06T13:54:43.725943Z`다. Runtime과 portable D-110 `FROZEN` marker는 72 bytes/file SHA
  `sha256:cdfe40b734135a30f66e34ff24469940063a7231a1fe0783420ee2ff816d9561`이고 frozen index bytes도 일치한다.
  D-106 portable unfrozen index는 55,644 bytes/file SHA
  `sha256:c9b292f67fcb3c4bf524065801681e76c5df22142bbbb8b2db36d3c932df358a`로 unchanged다.
- Append-only journal은 `reports/memory-development/d110-index-freeze-execution.jsonl`, 8 records, head
  `sha256:03d8bcbf57230aa9bfd5ce4e81fa2890bb36c2f5f9e4e51c9e64b3a8c09313e1`, 9,481-byte file SHA
  `sha256:f06cfa9037f09720675d3c0edd7e19516144bd46375aaa86679c5b1f6923b1e2`다.
- Freeze receipt는 `reports/memory-development/d110-index-freeze-receipt.json`, ID/body/file SHA
  `d110freezereceipt_b8ca4f167c330011118edb33d8ad3f18a47a20e795f28e752d6cc87e84daa839`/
  `sha256:b8ca4f167c330011118edb33d8ad3f18a47a20e795f28e752d6cc87e84daa839`/
  `sha256:a2aeaa0985cb1bf9ced5bdfd43c5bc473a73e5ac93bf7660ca717e3eb9285702`, 5,986 bytes이며
  `recorded_at=2026-08-06T13:54:43.782123Z`다.
  Completion gate는 `reports/memory-development/d110-index-freeze-completion-gate.json`, gate/body/file SHA
  `d110_bc1cae7a2ebc5d6531d203ef4d7101762d7366c9e77814c3a4c772d353f0a736`/
  `sha256:bc1cae7a2ebc5d6531d203ef4d7101762d7366c9e77814c3a4c772d353f0a736`/
  `sha256:79578db09955dab2a22b015ba5210baec28e7d30b9cac818b1f2c6d6eac782cd`, 7,754 bytes이며
  `recorded_at=2026-08-06T13:54:43.793637Z`다.
- Transaction 의미는 staged index fsync + same-filesystem `os.replace`, 이후 marker exclusive binary create +
  fsync의 ordered per-file commit이다. Cooperative lock은 D-110 executor끼리만 조정한다. Global two-file atomic
  transaction이나 arbitrary external writer exclusion은 주장하지 않고 partial/ambiguous state를 fail closed한다.
- Pre-mutation focused 17/17과 post-freeze focused 17/17(256.5초)이 각각 통과했다. D-110 related와
  repository-wide full-suite 결과는 아직 없으므로 주장하지 않는다. D-110 자체 provider/evaluator call은 0/0,
  added model cost는 `$0`다.
- `memory_index_frozen=true`만 새로 열린다. `retrieval_ready=false`, retrieval experiment authorization false,
  runtime memory injection count 0, core/analysis false를 유지한다. 다음 gate는 **별도 retrieval-readiness
  authorization candidate**를 준비하는 것이며 retrieval 실행, runtime injection 또는 core 권한이 아니다.
- Date: 2026-08-06

### Historical D-109 accepted offline source decision — prepare an exact freeze authorization candidate

- 일반적인 `진행해줘`를 실제 freeze 승인으로 해석하지 않는다. D-109는 사용자가 승인할 exact candidate를
  만드는 offline 단계이며 runtime index와 `FROZEN` marker를 수정하지 않는다.
- Exact D-108 completion gate, D-107 portable validation, D-106 portable index와 current runtime copy를
  재검증한다. Runtime copy는 portable bytes와 같고 directory에는 `index.json` 하나만 있어야 한다.
- Candidate는 exact pre-state와 허용 mutation 다섯 개, marker content rule, one-use/no-retry 계약만 결속한다.
  Retrieval, runtime injection, provider/evaluator call, core와 analysis는 허용하지 않는다.
- Candidate ID/body/file SHA는
  `d109freezecandidate_480d2aa8657fd143397fcfc71f252b8a8e3c0988d3950b5671089cf6dc8b8d46`/
  `sha256:480d2aa8657fd143397fcfc71f252b8a8e3c0988d3950b5671089cf6dc8b8d46`/
  `sha256:ae8a8c6e58b058720943bae9088da2cf242168a70f654006557dd84c84d4e580`다.
- Source gate ID/body/file SHA는
  `d109_e37e716aceb0a322820eada8b83d8a309e06052f6060c986f6025c61b7d999ef`/
  `sha256:e37e716aceb0a322820eada8b83d8a309e06052f6060c986f6025c61b7d999ef`/
  `sha256:0953687473bd25f48ad52bdc78c577d6a4daa4947b019fcd65809e7548c4f949`다.
- D-109 당시 `exact_candidate_user_approval_received`, freeze execution/authorization, actual frozen state,
  retrieval/core는 false였다. 당시 다음 단계는 exact candidate triple에 대한 별도 사용자 승인이었다.
- Date: 2026-08-06

### D-108 accepted result decision — seal the exact two-call provider token count

- 사용자는 exact D-107 gate ID/body/file SHA를 참조해 baseline과 with-memory Responses input-token count call 두
  번만 명시적으로 승인했다. Approval receipt는 self-attested이며 reviewer identity 인증이나 cryptographic signature가
  아니다. Generation, automatic retry, freeze, retrieval/runtime injection과 core는 승인 범위가 아니다.
- One-use 실행은 baseline, with-memory 순서로 완료됐다. Baseline은 2,193 input token, with-memory는 2,895 input
  token이고 exact D-105 bundle의 증가분은 702 token이다. 이는 사전 고정한 0~2,000 token 범위 안이므로 이 exact
  pair에 대해서만 `provider_exact_budget_validated=true`다.
- Provider input-token count call은 정확히 2회, generation call은 0회다. 두 응답은 HTTP 200,
  `object=response.input_tokens`, SDK retry 0이며 automatic retry를 사용하지 않았다. 실행 capability는 이미 소비됐고
  같은 live command를 재실행하지 않는다.
- Approval receipt ID/body/file SHA는
  `d108approval_dbe0873a16902f36a5094e963360f77d414973e29dec5fca5bab7a17c1ff3af3`/
  `sha256:dbe0873a16902f36a5094e963360f77d414973e29dec5fca5bab7a17c1ff3af3`/
  `sha256:20442ff99a50fe6b79b7f155559816e98b3cf79523fb55e17627480de95f7b31`다.
- Provider receipt ID/body/file SHA는
  `d107countreceipt_80447f354d982620b1c849a32abcd276c40428721c8948f6aef5671a11176946`/
  `sha256:80447f354d982620b1c849a32abcd276c40428721c8948f6aef5671a11176946`/
  `sha256:43ce5dc5260a9f67e05f695a68a7dbf840ef3743f7ba7858583e9e74fb07d474`다.
- Append-only execution journal은 6 records, head
  `sha256:84905f7a334ec349a2c979e6cfb68c9c67a23dda9219f1fc8036f9d2e78f5eaf`, 6,124-byte file SHA
  `sha256:01f96bc62f4a1f1d692328e2e7e71e8456a2976b772a70cf0bd66ab1b07227cd`다.
- Completion gate ID/body SHA는
  `d108_c663c745d43fc31bdee5309825059827899872c13368d7e3709e8730ee0a0f86`/
  `sha256:c663c745d43fc31bdee5309825059827899872c13368d7e3709e8730ee0a0f86`, 4,794-byte file SHA는
  `sha256:5f57e29caa3a3c940c280a69fbed3abe3d8daba4b4542e039355443df931d7bc`다.
- API key 값은 receipt, journal과 gate에 저장하지 않았고 checked-in D-108 artifact의 secret scan이 통과했다.
  Custom base URL과 organization/project override도 사용하지 않았다. Billing 또는 free-tier 적용액은 확인하지 않았으므로
  `billing_or_free_tier_claim=null`이다.
- Token budget 선행 조건이 통과해 exact index의 freeze authorization candidate를 검토할 준비만 됐다. 이는 freeze
  승인이나 실행이 아니다. Index는 계속 unfrozen이고 retrieval/runtime injection, retrieval 실험, core와 analysis도
  닫혀 있다. Focused verification은 10/10 통과했다.
- Date: 2026-08-06

### D-107 accepted offline decision — validate the portable index and prepare the exact token-count pair

- D-106 completion gate와 portable index를 repository 안의 checked-in bytes만으로 다시 검증한다. Ignored
  `.patchloop` runtime index와 embedding snapshot/model은 읽지 않는다. Stored vector로 전체 index를 다시 만들었을
  때 canonical bytes가 portable index와 같아야 하고, hold group과 `FROZEN` marker는 없어야 한다.
- Token budget 검증용 carrier는 frozen dataset manifest에서 첫 번째로 admitted된 development-validation task인
  `moto-query-scanned-count`다. Public spec만 읽고 events는 빈 배열, checkpoint는 `null`로 고정한다. Private spec과
  evaluator body는 읽지 않는다.
- Baseline과 with-memory context는 `/selected_memory`만 JSON `null`에서 exact 3,528-byte D-105 bundle로 바뀐다.
  이 slot을 다시 `null`로 정규화하면 context, full Responses request와 input-token-count request가 각각 같아야 한다.
  Normal runtime retrieval은 `MemoryRetrieved` event를 추가하므로 이 좁은 token-count pair를 만들 때 호출하지 않는다.
- Future 실행은 `POST /v1/responses/input_tokens`를 baseline, with-memory 순서로 정확히 두 번 호출하는 것만 계획한다.
  SDK transport retry는 0이고 automatic retry와 `responses.create` generation call은 허용하지 않는다. 두 count call 중
  하나라도 실패하면 delta와 receipt를 만들지 않는다.
- D-107에서는 provider client/API key를 읽거나 provider를 호출하지 않았다. Baseline/with-memory count는 모두
  `null`이고 receipt도 없다. 따라서 `provider_exact_budget_validated=false`이며 두 count call에는 exact D-107 gate를
  기준으로 한 별도 사용자 승인이 필요하다.
- Portable validation ID/body/file SHA는
  `d107portable_8fb06997dfd9aa7e07c116db8095b5397382356bcd1cfd71ab3ce6c8b4ad1785`/
  `sha256:8fb06997dfd9aa7e07c116db8095b5397382356bcd1cfd71ab3ce6c8b4ad1785`/
  `sha256:a6e71de1eea4a311d790e14a25dc9e507e1a2107176a7d0967ac074f9e50f259`다. Token-count plan
  ID/body/file SHA는 `d107plan_7ace0e204f367fc857bfbc1ddaa1bbdc58dd9ff3c9272f9d9c7e2b7241160ee6`/
  `sha256:7ace0e204f367fc857bfbc1ddaa1bbdc58dd9ff3c9272f9d9c7e2b7241160ee6`/
  `sha256:2a3d817d14d500863d56d5446010866a6feb2361eb684c3575400020bc31a085`다.
- Source gate ID/body SHA는
  `d107_4bc473796fd4564bb4d4cc9bf975ea9e41addb4fda620135e6ae4d6a21e645d4`/
  `sha256:4bc473796fd4564bb4d4cc9bf975ea9e41addb4fda620135e6ae4d6a21e645d4`, 4,175-byte file SHA는
  `sha256:b3e24975062e379ec94c77187570b392026bacdcc855adedb00943467aaf09f2`다.
- Freeze authorization precondition의 형태만 정의했다. Provider receipt와 0~2,000 token delta가 없으므로 freeze
  candidate도 아직 ready가 아니다. Index freeze, retrieval/runtime injection, retrieval 실험, core와 analysis는
  모두 false다. Provider/evaluator call과 added model cost는 0/0/`$0`다.
- Date: 2026-08-06

### D-106 accepted decision — build one exact unfrozen group-aware index

- Exact D-105 gate를 참조한 사용자의 승인은 pinned snapshot preflight, 새 group-aware builder와 admitted group
  3개의 unfrozen index 하나에만 적용한다. Freeze, retrieval와 core는 승인하지 않는다.
- `all-MiniLM-L6-v2`의 exact revision에서 safetensors runtime file 10개만 사용한다. Local file set, Git/LFS hash,
  dependency version, no-truncation tokenization, shape/dtype/finiteness/normalization과 current-host fresh-load
  determinism이 모두 통과해야 한다.
- Legacy failure별 builder와 legacy `entry_embedding_text()`는 사용하지 않는다. Exact D-105 render bytes를
  embedding하고 semantic group 하나당 `MemoryEntry` 하나를 만든다.
- Index identity는 gate/receipt/source/render/snapshot/vector/dataset canonical identity에서 도출하며 timestamp와
  UUID를 사용하지 않는다. Provenance는 model-facing text 밖에 보존한다.
- 결과 index는 `idxgrp_563976c4443a725e287225cef1e718daf134fbb96574921cb9e020049ea52064`, `frozen=false`다.
  `FROZEN` marker는 만들지 않으며 later explicit gate 전에는 freeze와 retrieval이 fail closed해야 한다.
- Provider/evaluator call과 added model API cost는 0/0/`$0`다. Index build 성공을 memory effect나 core result로
  해석하지 않는다.
- Date: 2026-08-06

### D-105 accepted production decision — freeze deterministic render and prepare a non-authoritative index candidate

- D-104의 exact ordered source 세 개만 model-facing rendering의 의미 원천으로 사용한다. Source rule text를
  수정하거나 raw trace, submitted patch, private/evaluator/provider body에서 새 의미를 작성하지 않는다.
- Exact predecessor rebuild 중 inherited D-099 validator가 public submitted patch bytes를 integrity/leak scan용으로
  읽는 사실을 기록한다. Patch를 render에 복사하지 않는다. Package initialization이 legacy retrieval/store module을
  간접 import하는 사실도 기록하되 해당 API call과 historical index inspection/modification은 0/false로 분리한다.
- Renderer는 `model-facing-memory-render-d105-v1`로 고정한다. 이미 NFKC인 ASCII-subset UTF-8, LF,
  trailing newline, fixed field/list order와 whole-entry-only를 요구한다. Partial truncation을 금지하고 provenance,
  ID/hash/seal/confidence/local path를 model text에서 제외하되 gate에는 out-of-band로 보존한다.
- Exact render는 `reports/memory-development/rendered/d105/`의 세 파일이다. Size는 1,191/1,164/1,161 bytes,
  ordered render-set SHA는 `sha256:7b72fc94642d996fad5a0b199719c56bfecc8a8fc1bbe42b2060aa18e21d2667`,
  fixed separator로 만든 canonical joined bundle은 3,528 bytes/SHA
  `sha256:572667d431aa75e4fe74bfc030a99f64245b77d9afa1c88e5d531129f708accf`로 고정한다.
- Memory budget은 maximum 2,000 provider input token delta로 유지한다. `chars/4`를 사용하지 않고 canonical
  context의 `/selected_memory`만 JSON `null`에서 exact whole-entry bundle로 바뀌는 두 full request의
  `responses.input_tokens.count` 차이로만 exact validation한다. Context deep diff, normalized request equality, 두
  context/request hash와 header/separator 포함 count가 있는 future receipt가 필요하다. D-105에는 provider receipt가 없으므로
  `provider_exact_budget_validated=false`다.
- Embedding authorization candidate는 `sentence-transformers/all-MiniLM-L6-v2` revision
  `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, normalized embedding,
  `trust_remote_code=false`로 고정한다. 이 commit observation은 signature나 verified local snapshot이 아니다.
  Snapshot download/file hash, expected 384-dimension float32 vector와 locked offline reload를 후속 preflight로 남긴다.
- Group-aware index plan은 exact D-104 source 세 개를 ordered input으로 사용하고 admitted group당 entry 하나,
  hold-group rejection, deterministic index identity와 out-of-band provenance를 요구한다. Existing failure별 legacy
  builder는 사용하지 않는다.
- `index_build_authorization_candidate=true`는 승인 가능한 설정 후보가 정해졌다는 뜻일 뿐 actual authorization이
  아니다. Exact D-105 gate에 대한 별도 사용자 approval receipt, verified snapshot과 implemented builder 전까지
  `memory_index_build_authorized=false`다.
- Portable gate는
  `reports/memory-development/d105-renderer-embedding-index-authorization-gate.json`, gate/body ID
  `d105_0f99c7d1cd1c371191073ead8d60636be9ea6040947d9c7f3522aba25bc3df70`/
  `sha256:0f99c7d1cd1c371191073ead8d60636be9ea6040947d9c7f3522aba25bc3df70`, 12,368-byte file SHA
  `sha256:db6303f3de834b3c36493f2863dcc5be3ca697490d18df15c86a18e7ee7b17eb`다.
- Current executable evidence는 focused 47/47, related 550/550다. Repository-wide는 1,900 collected 중 1,892
  passed/7 environment-dependent skipped/1 failed다. 유일한 기존 order-dependent D-092 raw replay SQLite
  WAL/SHM invariant는 fresh isolated process에서 1/1 통과했으며 D-105 failure나 fix로 합산하지 않는다.
  D-105 provider/evaluator call 0/0, added model cost `$0`다.
  Actual MemoryEntry/embedding/D-105-created index count는 0이고 build/freeze, retrieval/runtime injection, core,
  analysis, memory-effect와 negative-transfer claim은 false다. Raw Trace renderer와 네 condition 전체 readiness도
  D-105 결정 범위 밖이다.
- 다음 gate는 exact D-105 gate approval, locked embedding snapshot preflight와 group-aware builder다. 이 결정을
  자동 index build나 core authority로 사용하지 않는다.
- Date: 2026-08-06

### D-104 accepted production decision — materialize exact unindexed rule sources

- D-103 seal의 admitted `D100ProjectedEntry` 세 개만 source 의미 원천으로 사용한다. Raw trace, failure record나
  submitted patch를 다시 요약해 rule을 수정하지 않는다.
- Current `MemoryEntry.index_version`은 actual enclosing index identity이므로 index 전 단계에 `pending`, `none`,
  source collection ID를 넣지 않는다. Shared `MemoryEntry` contract를 바꾸지 않고 local strict
  `unindexed-memory-entry-source-d104-v1` wrapper를 사용한다.
- Exact source는 `reports/memory-development/sources/d104/`의 세 파일이며 pyfakefs/HF Hub/tox admitted group에
  각각 하나다. AnyIO/Loguru hold source는 0이다. Source collection ID는
  `d104collection_4017131c10c127f47b8ea68ff2d8c3c3265c2f6cb11c1b175dd52c23882bd399`, ordered source-set
  hash는 `sha256:1168c8c9cfcaa3671f42391436bfff713c90f01baec468e5ef2509ddb95dbad2`다.
- Source file size/SHA는 5,188 bytes/
  `sha256:8a139248e3e53e3a563366c6a2f9ad213a6a164831bd3cef2a3e5b6cb37008e8`, 5,333 bytes/
  `sha256:87b1b751634d8c34ef125042e472807828a7820064f25e413a51d0755b5b51da`, 5,416 bytes/
  `sha256:d5b22f7c2ca75a271cf60cd52eb9089f2fd54bec99f5c9a75d09c311e0311505`다.
- Gate는 `reports/memory-development/d104-three-rule-source-materialization-gate.json`, semantic body SHA
  `sha256:61e44eb5609c05c97b84602bbaa4eb7bff84dd33af227cef18592aa2b6a32c11`, 12,705-byte file SHA
  `sha256:8eeb26d6f5e0ff22658501afe54bd8cebe35896dc18b60f8f73355ec53190dd0`다. Schema/provenance/leak scan과
  exclusive-create/exact-retry contract를 결속한다.
- Inherited D-099 validator가 tracked public patch copy의 integrity는 재검증하지만 patch text를 D-104 source에
  복사하거나 새 rule 의미를 작성하지 않는다. Portable path는 raw SQLite/event/search-read artifact, private/
  hidden/reference/evaluator/provider body를 읽지 않는다.
- D-104-created actual MemoryEntry/rendered memory/embedding/index count는 모두 0이다. Legacy per-failure builder를
  연결하지 않고 historical index를 inspect/modify하지 않는다. Index build/freeze, retrieval, core, analysis와
  memory-effect claim은 false다.
- Focused 30/30과 related 530/530이 통과했다. Repository-wide는 1,853 collected 중 1,845 passed/7
  environment-dependent skipped/1 failed다. 유일한 기존 order-dependent D-093 SQLite WAL/SHM invariant는 fresh
  isolated process에서 1/1 통과했으며 D-104 failure나 fix로 합산하지 않는다. Provider/evaluator call 0/0,
  added model cost `$0`다.
- 다음 gate는 deterministic model-facing renderer/2,000-token policy와 pinned embedding/group-aware index-build
  authorization이다. D-104 완료를 자동 index build나 core authority로 사용하지 않는다.
- Date: 2026-08-06

### D-103 accepted production decision — approve the exact candidate and seal narrow admission

- 사용자가 D-102 candidate ID
  `d101candidate_97c0d2499e2ffab97df6050b84af7c1d455e4af631a3e0fb58d50a084a62ac9d`, semantic body SHA
  `sha256:97c0d2499e2ffab97df6050b84af7c1d455e4af631a3e0fb58d50a084a62ac9d`, file SHA
  `sha256:9620e99961010bc4c942728f1948cb50b3f067025b8d5a02ba579dd3a1b4e457`를 별도 메시지에서 정확히
  다시 입력한 것을 exact candidate 승인으로 받아들인다.
- Receipt는 `reports/memory-development/d103-exact-candidate-approval-receipt.json`, ID
  `d101receipt_23c8ff9b5f8b91820d03a25242abaa02f1ec2af0357bd9b26c227882cf8f5f7a`, semantic body SHA
  `sha256:23c8ff9b5f8b91820d03a25242abaa02f1ec2af0357bd9b26c227882cf8f5f7a`, 6,245-byte file SHA
  `sha256:dad12cf181fee8e113d9da703795eb8ccb4a16be6014218ea923a919d0695031`로 고정한다.
- Receipt의 `approver_kind=human`은 자기확인 provenance다. Reviewer identity 인증이나 cryptographic signature를
  주장하지 않는다.
- Seal은 receipt뿐 아니라 exact candidate와 현재 D-102 journal bytes/head/count/file SHA를 모두 재검증한다.
  경로는 `reports/memory-development/d103-maintainer-assisted-admission-seal.json`, ID
  `d101seal_3dc67e77a0c8c2d9a94f6bea9138d179eb6d6ac1cda0d8b490a1eab3bfbe705e`, semantic body SHA
  `sha256:3dc67e77a0c8c2d9a94f6bea9138d179eb6d6ac1cda0d8b490a1eab3bfbe705e`, 19,357-byte file SHA
  `sha256:af1e6ea8811445f26d542f34500d1a7b3919392bef00c98b71f4c26ded236e8e`다.
- 1·2·5번의 template 3개만 source authoring 대상으로 admit하고 3·4번 hold 2개는 유지한다. Full review는
  finalized가 아니며 D-103 checkpoint의 unindexed source record count는 0이다. Source authoring만 열고 index build/freeze,
  core와 analysis는 false로 유지한다.
- Portable gate는 `reports/memory-development/d103-exact-candidate-admission-gate.json`, semantic body SHA
  `sha256:4a542cd571ffc0b94b6f95e106fd2371425dd66f82cfa6091cc602905036fb1f`, 5,315-byte file SHA
  `sha256:4602a579d7c11dd300e2f9bede38e8a6d7bf21c78a8fbfc255550b7d86f3d354`다. Focused 7/7,
  related 497/497, repository-wide 1,823 collected 중 1,816 passed/7 environment-dependent skipped/failure 0이다.
- D-103 provider/evaluator call은 0/0이고 added model cost는 `$0`다. 다음 결정 대상은 exact 세 rule source
  materialization과 leak/schema/provenance validation이며 index build/freeze와 core는 별도 결정으로 남긴다.
- Date: 2026-08-06

### D-102 accepted production decision — record five choices and prepare an unapproved candidate

- 사용자가 D-101 한글 검토 문서를 읽은 뒤 1·2·5번은 `기억에 추가`, 3·4번은 `나중에 결정`으로
  명시적으로 확정한 답변을 production decision으로 기록한다.
- 기술적 이유는 시스템이 D-099 public-evidence proposal과 D-101 한글 설명에서 연결했고 사용자는 권장 선택을
  확인했다. 따라서 reviewer provenance는 5개 모두 `maintainer_assisted`이며 사용자가 rationale를 직접
  작성했거나 reviewer identity가 인증됐다고 주장하지 않는다.
- Exact effective decisions는 proposal 순서대로 `approve, approve, continue_hold, continue_hold, approve`다.
  Journal은 `reports/memory-development/d102-maintainer-assisted-group-decisions.jsonl`, 5 records/correction 0,
  head `sha256:4192b503768093e2134b7651da4922fcd9d5c2a064e0150a7f523adc952ac469`, 7,829-byte file SHA
  `sha256:5c46e6b6a49e436794c1b118f96a9d05caa48a4cd4199e9791ec2ec4499327e3`다.
- Journal head/count/file SHA를 caller input으로 다시 고정해 candidate를 생성한다. Candidate 경로는
  `reports/memory-development/d102-maintainer-assisted-admission-candidate.json`, ID는
  `d101candidate_97c0d2499e2ffab97df6050b84af7c1d455e4af631a3e0fb58d50a084a62ac9d`, semantic body SHA는
  `sha256:97c0d2499e2ffab97df6050b84af7c1d455e4af631a3e0fb58d50a084a62ac9d`, 31,148-byte file SHA는
  `sha256:9620e99961010bc4c942728f1948cb50b3f067025b8d5a02ba579dd3a1b4e457`다.
- Candidate observed counts는 approve 3/reject 0/continue-hold 2와 preview entry 3이다. Candidate와 preview는
  admission이 아니고 admitted memory rule count는 0이다. 두 hold 때문에 full group review도 finalized가 아니다.
- Portable gate는 `reports/memory-development/d102-maintainer-assisted-decision-candidate-gate.json`, semantic
  body SHA `sha256:27e6b50c156e2c590e4225302534c5fedca67596eae2c831d03d3a4810c11732`, 5,453-byte file SHA
  `sha256:e8ff1cdecdb7b107593f43f0b68b564abab34668558a0bb367296e16fbcca373`다. Focused verification은
  6/6, D-097~D-102/memory/contracts/CLI/qualification related verification은 405/405 pass이고 D-099~D-101
  artifact/hash는 변경하지 않았다. Repository-wide는 1,816 collected 중 1,809 passed/7 environment-dependent
  skipped/failure 0이다.
- 현재 사용자 답변은 group decision 승인이지, 그 뒤에 생성된 exact candidate snapshot 승인이 아니다.
  Approval receipt와 seal은 만들지 않으며 memory source authoring, index build/freeze, core와 analysis를 열지 않는다.
  다음 gate는 사용자가 candidate ID/body SHA/file SHA를 별도 메시지에서 정확히 다시 승인하는 것이다.
- D-102는 provider/evaluator call 0/0, added model cost `$0`이다. 이 decision은 memory improvement, negative
  transfer, hidden cause, agent architecture defect 또는 held-out performance evidence가 아니다.
- Date: 2026-08-06

### D-101 확정 결정 — 한글 검토 문서와 명시적 승인 절차

- D-099 proposal과 D-100 source gate에 exact 결속된 machine JSON은 변경하지 않고, 사람이 확인하는 Markdown만
  쉬운 한국어 검토 문서로 제공한다.
- 한글 검토 문서에서는 내부 ID와 hash, `candidate`/`hold` 같은 영문 상태명을 본문에서 숨긴다. 사용자는 문제 유형
  1~5번을 읽고 `기억에 추가|사용하지 않음|나중에 결정` 중 허용된 선택과 이유만 별도로 제공한다. 어떤 선택도 미리
  고르거나 권고하지 않는다.
- 일반적인 구현 진행 요청은 문제 유형의 결정이나 exact candidate 승인으로 해석하지 않는다. Checked-in 검토 문서에는
  선택을 직접 기록하지 않는다.
- Future candidate는 complete non-synthetic journal과 외부에서 제공된 head/count/file SHA를 모두 요구한다.
- Future receipt는 exact candidate ID/body/file SHA를 명시적으로 다시 입력해야 하며 self-attested provenance로만
  취급한다. Identity authentication과 signature verification은 주장하지 않는다.
- Future seal은 candidate/receipt와 live journal bytes가 계속 일치해야 한다. Seal이 생겨도 index build/freeze와
  core는 별도 gate 전까지 닫힌다.
- 한글 Markdown은 12,872 bytes/file SHA
  `sha256:9fc8e51dc867d66672b7c5334402bafdc27759914df88df09d506a5832d479c5`다. 갱신된 source gate는
  3,807 bytes/file SHA `sha256:987cded0f469370f3f9c5542c8353f7153429d7b3743df9af003f2f594b3a275`, semantic
  body SHA `sha256:26838ab1e8097e47f53e712ce11d0d8a603cd4dd3dff408792f77f7d164fe4f9`다.
- 이 결정은 한글 검토 화면과 mechanism/source gate만 승인한다. Production human decision은 0이며 candidate,
  receipt, seal 또는 memory rule admission을 승인하지 않는다.
- Final verification은 focused 26/26, related 399/399, repository-wide 1,810 collected 중 1,803 passed/7
  environment-dependent skipped/failure 0이다. Related run에서 시간이 지나며 경계를 넘은 D-081 historical
  pricing freshness test는 suite pricing timestamp로 test clock만 고정했다. Production qualifier, suite와
  historical artifact는 변경하지 않았고 이를 D-101 product/runtime fix로 주장하지 않는다.
- Date: 2026-08-06

### D-096 accepted offline decision — freeze the future resource policy and admit exact no-memory source authoring

- D-095가 workflow-readiness 3/3을 process-confound 없이 통과했으므로, public process evidence만 사용해
  future comparison의 condition-neutral resource policy를 고정한다. D-095의 hidden 0/3이나 task success는 이
  policy 선택 근거로 사용하지 않는다.
- 선택한 prospective tuple은 `gpt-5.4-mini-2026-03-17` medium/standard/default, SDK transport retry 0,
  `SYSTEM_PROMPT_V3`, tool schema v2, context `phase-evidence-v5`, max output 25,000, memory allowance 2,000과
  model/tool call `null`, total token 3,000,000, wall 3,600초다. 네 memory condition은 이 tuple을 공유한다.
- D-083 `condition-neutral-comparison-resource-policy-v1`과 D-084 runtime contract/evidence v1은 historical로
  그대로 보존한다. Future consumer는 runtime contract/evidence v2를 사용해야 하지만 D-096 시점에는 아직
  구현되지 않았고, historical manifest/result/qualification을 다시 쓰지 않는다.
- Exact admission은 frozen memory-development의
  `loguru-invalid-format-feedback`, `anyio-interrupt-runner-cleanup`,
  `tox-cross-section-empty-substitution`, `hf-hub-xet-endpoint-propagation`,
  `pdm-ignore-active-venv-resolution`, `pyfakefs-makedirs-parent-traversal`을 이 순서로 `no_memory` 각 2회,
  seed `20260723`에 실행하는 12-row contract다. Historical 1.6M template은 task/order carrier일 뿐 새 campaign
  runtime source가 아니다. 여섯 `public.yaml` 각각의 exact bytes/file SHA는 frozen dataset manifest row의
  `public_spec_hash`와 일치해야 한다.
- Admission은 12/12 terminal·qualified·cost-settled와 exact persisted/recomputed qualification, runtime/no-memory
  binding과 complete telemetry를 요구한다. Not-started, infrastructure, qualification, diagnostic,
  duplicate/replacement, unknown-terminal, model/tool-call-budget-block count는 0이고 issued response는 모두
  `completed`여야 한다. Official branch는 accepted submission,
  completed official receipt와 `resolved|task_failure`; budget branch는 actor/CAS/pre-call/no-provider-after evidence를
  가진 canonical total-token/wall `ModelGenerationBlocked`, `agent_failure`, submission/evaluator 부재를 요구한다.
  두 branch는 disjoint·exhaustive exact-one이다. Task success와 hidden acceptance는 admission predicate가 아니다.
  Qualified budget terminal은 `agent_failure`로 포함하되 자동 rerun하거나 memory candidate로 삼지 않는다.
- Memory candidate는 official evaluator가 완료된 task failure이면서 qualification과 leakage scan을 통과해야 한다.
  Candidate는 자동 rule admission이 아니며 collection 뒤 agent 또는 maintainer review와 deduplication을 거친다.
- Worst-rate reserve는 `$13.6125`/run, `$163.35`/12 run이다. 현재 project cap `$150`를 `$13.35` 초과하므로
  campaign cost policy와 authorization은 `NO_MEMORY_AUTHORIZATION_CAP_PENDING`으로 닫는다. 최소 정수
  non-censoring cap은 `$164`지만 이 산식 자체가 cap 변경이나 비용 승인은 아니다. Pricing은 exact-bound D-094
  source artifact의 pricing block에서 직접 읽고 standard-rate formula로 재도출한다.
- 이 decision이 여는 것은 resource-policy freeze, exact baseline-admission contract와 future no-memory source
  authoring뿐이다. New suite/runtime v2, preflight, execution hash, live run, baseline result, denominator, memory
  review/admission/index, core와 analysis는 계속 닫혀 있다. D-087/D-095도 소급 baseline이 아니다.
- Portable artifact는 `reports/live-pilot/artifacts/d096-condition-neutral-resource-policy-baseline-admission.json`이다.
  Semantic body SHA는 `sha256:2e9360d92db5224d181fe8f18254da3850f324b33b24f3833633589085e3b75d`,
  19,031-byte file SHA는 `sha256:5c032cff1045a39d1d8d9757205a920b1cd1cfd948c7c4e3e5b526ae6744661d`다.
  D-096 자체 provider/evaluator call과 added model cost는 0/0/`$0`이며 focused 26/26, 관련 계약 178/178,
  repository-wide 1,656 pass/7 environment-dependent skip이 확인됐다. Shard 순서에 민감한 D-092 WAL/SHM
  invariant 1건은 독립 프로세스에서 통과했다. Parsed exact rebuild와 `git diff --check`도 통과했다.
- Date: 2026-08-05

### D-097 accepted source decision — bind the exact no-memory successor without authorizing execution

- D-096의 future source-authoring permission을 exact suite
  `dev-no-memory-condition-neutral-3000k-20260805-r1`로 구현한다. Source order는 Loguru, AnyIO, tox,
  HF Hub, PDM, pyfakefs이고 `no_memory` 각 2회, seed `20260723`이다. Suite file은 2,741 bytes,
  `sha256:7b3c217388e86a2760694e98031b7ac974c8c450075e3433ee977e35b344abb0`다.
- D-096 source identity
  `sha256:e399114a6ea516821a30104a612f7222c0caf3f88def7b5d7472d15f7cc4c27b`와 seed shuffle 뒤
  expanded schedule hash `sha256:dff4f38db99bcbc878e917a6c76e10a6c244701d2a8eb5ea4b43daf427a305ba`를
  별도 identity로 보존한다. Source identity, expanded schedule과 future preflight execution schedule hash는
  서로 대체하지 않는다.
- Exact D-096 model/prompt/tool/context/resource tuple을
  `condition-neutral-comparison-runtime-contract-v2`와
  `condition-neutral-comparison-runtime-evidence-v2`에 결속한다. Exact successor ID만 v2 selector에 들어가며
  D-083/D-084의 1.6M runtime-v1과 historical manifest/result/qualification은 수정하거나 재해석하지 않는다.
- `campaign-list-price-full-schedule-reserve-v1`을 선택한다. 첫 provider call 전에 하나의 fsync된
  `FullScheduleCostReserved` event가 exact 12-row schedule, row별 `$13.6125`와 full reserve `$163.35`를 함께
  결속한다. 같은 plan/CAS/journal은 각 row 전에 재검증되고 terminal row마다 deterministic settlement가
  기록된다. Prospective campaign-scoped source cap은 `$164`다. D-097에는 per-row atomic SQLite consumption이
  없고 live resume은 disabled다. Cost journal은 duplicate paid-call prevention을 주장하지 않으며 기존 one-use
  execution hash가 authorization을 단일 sequential invocation으로 제한할 뿐이다. 이는 historical project cap
  `$150` 변경, campaign exception 승인,
  expected invoice/free-tier claim 또는 completion guarantee가 아니다.
- Post-run journal reconciliation은 `CampaignCompleted`와 persisted result hash를 exact 재검증하고 foreign binding
  또는 duplicate terminal event를 rehash한 경우에도 거부한다. 이 사후 evidence-integrity 검증을 provider-side
  idempotency나 duplicate paid-call prevention으로 확대하지 않는다.
- Source completion은 official evaluator가 완료된 `resolved|task_failure` 또는 canonical pre-call token/wall
  budget `agent_failure` 중 exact-one terminal branch를 요구한다. Runtime output schema는
  `condition-neutral-no-memory-baseline-admission-gate-v2`다. Task success, hidden acceptance와 SCRR는 gate가
  아니다. Budget/infrastructure failure는 memory candidate가 아니며 automatic rerun하지 않는다. Future 12-row
  denominator gate가 통과하면 campaign-level `memory_review_eligible=true`가 되고 review candidate pool은
  official task failure로만 제한된다. 별도 review/dedup/leak gate 전에는 `memory_admission_unlocked=false`이고
  candidate를 rule로 자동 승격하지 않는다.
- Portable artifact는 `reports/live-pilot/artifacts/d097-condition-neutral-baseline-source-gate.json`이다.
  Semantic body SHA는 `sha256:05d952065136a45914e2fb3c44edcbb553732c9f33484c5412b9135062c6481b`,
  21,029-byte file SHA는 `sha256:21ed073ad1fbe1985e7a46cabebbfdc836baa303c4434e0777152c1d2d88a777`다.
  Source artifact는 runtime implementation을 스스로 검증하지 않으며 final focused/runtime/repository count는
  전체 회귀가 끝날 때까지 pending이다.
- D-097 source 단계는 provider/evaluator call 0/0, added model cost `$0`이다. Clean committed source에서 Docker,
  evaluator, dataset/task/environment, SDK와 fresh pricing을 다시 묶는 no-call preflight가 candidate hash를 만든 뒤,
  사용자가 그 exact hash와 max-`$164`, `$150` campaign exception을 별도로 승인하기 전에는 실행하지 않는다.
  Live result, baseline denominator, memory review/admission/index, core와 analysis는 계속 닫혀 있고 blocker는
  `NO_MEMORY_CLEAN_PREFLIGHT_AND_164_USD_APPROVAL_PENDING`이다.
- Date: 2026-08-05

### D-098 accepted result decision — seal the exact development baseline and open review only

- D-097 source commit `67fa85e47c5cf39c0ee03ad69d9d31f9fdd11ac3`과 approved execution hash
  `sha256:1a5aaccc4f95f71d285e0e0a9c8ccb27f82e235fbff465ef30f095401fde25f4`로 생성된 result를
  exact development no-memory baseline으로 봉인한다. ID/hash/run/result는 immutable하며 재실행하지 않는다.
- 12/12 terminal·qualified·cost-settled와 final gate pass가 denominator completion을 결정한다. Task success는
  predicate가 아니고 observed outcome 2 resolved, 9 task failure, 1 canonical budget agent failure를 그대로 남긴다.
- SCRR 2/12와 task-first 1/6은 development baseline 기술 통계다. Held-out 성능, memory improvement, CI 또는
  일반적인 agent 능력을 주장하지 않는다.
- Memory review source는 official evaluator `task_failure`이면서 qualification의
  `memory_candidate_eligible=true`인 9개 row뿐이다. PDM success 2개와 AnyIO budget terminal은 제외한다.
- Review queue를 여는 것과 rule/index admission을 분리한다. Public-evidence review, semantic dedup, leak scan,
  group-level approval과 proposal-consuming builder 전에는 `memory_admission_unlocked=false`다.
- Portable artifact는 `reports/live-pilot/dev-no-memory-condition-neutral-3000k-20260805-r1.json`이다. Semantic
  body SHA는 `sha256:e35cab52597c3ec6e884f074f9acf346dec65301e22d11edc2de56db7be9eacf`, 117,209-byte
  file SHA는 `sha256:ad87fa8c540552da62d964a430c29b032097b5cabbe78f0102c23cf36330b2dc`다.
- Usage-derived standard list-price는 `$11.838408`이며 actual invoice/free-tier treatment 주장이 아니다. D-098
  seal 과정의 provider/evaluator call과 added model cost는 0/0/`$0`이다.
- Date: 2026-08-05

### D-099 accepted review decision — seal a non-admitting five-group proposal

- D-098 official task-failure candidate 9개를 public evidence로만 검토하고 pyfakefs/HF Hub/AnyIO/Loguru/tox의
  5개 semantic group으로 exact partition한다.
- Pyfakefs/HF Hub/tox 3 group·6 source를 candidate proposal로, AnyIO/Loguru 2 group·3 source를 hold로 둔다.
  Loguru의 secondary diagnostic defect는 public code에서 구체적이지만 broader formatter rule은 미확정이며,
  AnyIO는 eligible run이 하나뿐이라 reusable lifecycle rule의 일반화를 보류한다.
- Candidate proposal은 admitted rule이 아니다. 모든 group approval은 `not_made`, human admission은 pending이고
  review history/index/admission/core/analysis를 열지 않는다.
- Historical v1 validator와 failure별 index builder를 소급 변경하거나 D-099 input에 연결하지 않는다. 다음 gate에서
  group-level append-only decision과 group-aware consumer를 별도로 만든다.
- Portable validation은 `.patchloop` 없이 수행하고 explicit raw audit만 copied SQLite/WAL을 사용한다. Raw 부재 시
  silent downgrade하지 않는다.
- Exact artifact는 `reports/memory-development/d099-public-evidence-review-dedup-proposal.json`, semantic body SHA
  `sha256:63c74999242f6217f2a81c9c2dc22d618d2be137948580f93401341c4ea49574`, 77,942-byte file
  SHA `sha256:24e34b02a66fc132d333bb51614a10786d38bc188b5550432a5f21f435f21493`다.
- D-099 자체 provider/evaluator call과 added model cost는 0/0/`$0`이다.
- Final verification은 focused 13/13, related 126/126, repository-wide 1,756 collected 중
  1,749 passed/7 environment-dependent skipped/failure 0이다. Ruff, compileall, exact rebuild와
  `git diff --check`도 통과했다. Historical D-092 full-order issue가 이번에는 재발하지 않았지만 이를 D-099
  수정으로 분류하지 않는다.
- Date: 2026-08-05

### D-100 accepted mechanism decision — implement group journal and non-indexing preview without human admission

- D-099 exact proposal/group/rule을 소비하는 `memory-group-review-decision-d100-v1`과
  `memory-entry-preview-d100-v1`을 별도 code path로 구현한다.
- Journal은 action idempotency, expected-tail CAS, global hash chain, group correction supersedes, writer lock와
  flush/fsync를 요구한다. Hold approve, stale tail, conflicting action reuse와 noncanonical/malformed/hash-inconsistent/
  leaking chain을 거부하고 descriptor는 parsed decision과 동일 byte snapshot에서 만든다.
- Approved group 하나를 template 하나로 projection하되 actual `MemoryEntry`를 만들지 않는다. Rule field와 ordered
  source provenance를 보존하고 `validation_count=0`이며 index version/embedding/freeze state는 없다.
- Existing per-failure review/build/freeze path를 연결하거나 historical artifact를 수정하지 않는다. Legacy operator
  bypass를 globally disabled했다고 주장하지 않는다.
- 일반적인 implementation 요청은 group별 human decision이 아니다. Production decision record, admission seal,
  admitted rule과 preview entry는 0이고 memory admission/index/core/analysis는 닫혀 있다.
- Source artifact는 `reports/memory-development/d100-group-review-projector-source-gate.json`, semantic body SHA
  `sha256:5ac180b32fef27d5937c1447e39f01bafda65ce6b5a3eef1992a7da45cab9b2b`, 5,048-byte file SHA
  `sha256:866bad69dad24dd908339330f27a24a388e64b453e6dc403363836292ea24e47`다.
- D-100 implementation 자체 provider/evaluator call과 added model cost는 0/0/`$0`이다.
- Standalone chain은 valid whole-row suffix deletion이나 fully rehashed rewrite를 감지할 external root가 없다.
  Optional expected head/count 검증을 구현하고 future admission seal이 exact approval receipt, head/count와 file SHA를
  결속하도록 남긴다. Reviewer kind도 self-attested provenance이지 인증 evidence가 아니다.
- Final verification은 focused 28/28, related 154/154, repository-wide 1,784 collected 중 1,776 passed/7
  environment-dependent skipped/1 failed다. 유일한 historical D-092 WAL/SHM order-dependent invariant는 fresh
  isolated process에서 1/1 통과했으며 D-100 pass/fix로 합산하지 않는다. Ruff, compileall, exact rebuild와
  `git diff --check`도 통과했다. D-077 pricing-freshness test의 clock-only 안정화도 D-100 runtime fix나 historical
  result 변경으로 분류하지 않는다.
- Date: 2026-08-05
