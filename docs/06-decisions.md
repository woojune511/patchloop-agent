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
| Q-005 | Live model provider와 fixed model identifier를 무엇으로 할지 | 실제 실험 비용과 reproducibility | Phase 2 종료 전 |
| Q-006 | Raw trace retrieval candidate pool을 same-repo dev run으로 제한할지 | Fairness와 leakage | Phase 5 시작 전 |
| Q-007 | Similarity embedding을 local model로 고정할지 | Offline reproducibility와 품질 | Phase 5 시작 전 |
| Q-008 | Small-sample bootstrap의 resampling unit을 task로만 둘지, repetition hierarchy를 반영할지 | Confidence interval 해석 | Phase 6 시작 전 |

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
