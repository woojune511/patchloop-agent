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
| D-023 | Live no-memory attempt는 `trace-qualification-v1`을 거쳐야 하며 memory candidate는 qualified memory-development failure로 제한한다. Qualification의 `source_evidence_hash`는 approved plan, manifest, events, checkpoints, result와 agent-visible artifact inventory를 결속하고 review/index admission 때 다시 계산한다. Failure는 hidden check ID를 제거하고 append-only hash-chained human review를 통과해야 memory build에 들어간다. | 실패 trace에서 배우되 solution/private oracle 누출, stale qualification과 자동 self-approval을 막고 원시 판정과 사람의 review history를 덮어쓰지 않는다. |
| D-024 | Paid campaign은 `CampaignStarted`와 각 `RunStarted`를 model call 전에 append-only hash chain에 flush와 fsync한다. 기존 journal은 hard-crash 뒤 같은 experiment의 새 schedule 시작을 차단한다. 중단된 campaign의 자동 resume은 구현될 때까지 제공한다고 주장하지 않는다. | Process 종료와 최종 result JSON 사이의 창에서도 이미 시작한 paid row를 잊고 중복 호출하는 것을 막으며, 구현되지 않은 recovery 의미론을 분리한다. |
| D-025 | Predeclared matrix가 불완전하거나 qualification-failed이면 report는 `analysis_ready=false` available-case diagnostic만 제공하고 headline metrics, paired difference/CI와 success/failure flip을 억제한다. | Infrastructure halt나 누락 repetition의 불균형 분모를 정상적인 memory 효과 비교로 오해하지 않게 한다. |

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
