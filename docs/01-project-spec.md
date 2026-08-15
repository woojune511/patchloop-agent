# Project Spec

상태: **Normative draft**  
대상: 제품·아키텍처·평가 작업을 수행하는 agent와 기여자

## 1. Problem statement

Visible test 통과만으로 coding agent가 이슈를 올바르게 해결했다고 볼 수 없다. Agent는 테스트를 약화하거나, 무관한 파일과 public API를 바꾸거나, dependency를 추가하거나, 기존 동작을 깨뜨리면서도 표면적으로 성공할 수 있다. Context reset과 worker crash는 이미 수행한 탐색·patch·검증을 반복하게 만들며, 과거 trace를 무차별로 넣으면 비용과 오판을 늘릴 수 있다.

PatchLoop가 답할 주 질문은 다음과 같다.

> 동일한 모델과 실행 예산에서, 실패 경험을 어떤 구조로 저장하고 선택적으로 검색해야 held-out task의 scope-compliant 성공률을 높이면서 비용과 negative transfer를 줄일 수 있는가?

별도의 reliability 질문은 다음과 같다.

> Persistent state와 checkpoint가 context reset 및 worker restart 이후의 recovery rate를 얼마나 높이는가?

두 질문의 결과를 하나의 인과 주장으로 섞지 않는다.

## 2. Product goals

PatchLoop v1은 다음을 제공해야 한다.

- Python repository snapshot과 issue를 입력으로 받는 single coding agent
- 명시적 phase와 제한된 tool을 가진 실행 loop
- model/tool/state transition의 추적 가능한 event와 artifact
- agent와 격리된 hidden evaluator
- hidden acceptance, regression, scope, dependency, API, safety verifier
- crash 후 재개 가능한 external checkpoint와 idempotent action
- evidence 기반 failure taxonomy와 structured memory
- 단계적 memory 비교: 먼저 No Memory 대 fixed Structured readiness, 이후 Raw Trace와 Selective Structured를 포함한 공정한 비교
- task-level 결과, 비용, trace, verifier evidence를 담은 재현 가능한 report
- 핵심 trace를 확인할 수 있는 최소 viewer와 마지막 단계의 Issue import/Draft PR 데모

## 3. Explicit non-goals for v1

- planner/coder/reviewer 멀티에이전트
- agent가 harness 자체를 수정·배포하는 self-improvement loop
- 여러 프로그래밍 언어 동시 지원
- Kubernetes, distributed worker, Temporal 수준의 운영 플랫폼
- unrestricted shell access
- 모든 실패를 LLM만으로 분류하거나 평가하는 방식
- 대규모 benchmark 전체 실행
- SaaS 수준 dashboard 또는 조직 권한 관리
- 평가 결과를 보기 전에 UI/GitHub 통합을 핵심 범위로 확장하는 일

## 4. Users and outputs

| 사용자 | 필요한 결과 |
| --- | --- |
| Agent/LLM platform engineer | 재현 가능한 trace, 상태 전이, tool·budget 데이터 |
| Evals engineer | audited task, run manifest, deterministic verifier, paired result |
| Repository maintainer/demo reviewer | issue, patch, 검증 근거, timeline, Draft PR |

한 run의 최소 출력은 다음과 같다.

- Git patch
- immutable run manifest
- ordered event stream
- phase artifact와 checkpoint
- visible/hidden verifier result
- failure record(실패 시)
- token, cost, duration, tool-call accounting
- final report

## 5. Research hypotheses

| ID | Hypothesis | Primary evidence |
| --- | --- | --- |
| H1 | Structured failure memory가 no-memory보다 held-out SCRR을 높이는지 단계적으로 검증한다. | 완료된 frozen-panel A/C와 별도 fresh-panel 후속 |
| H2 | Raw trace는 token을 더 사용하고 무관한 task에서 negative transfer를 만들 수 있다. | Token overhead, failure flip, reviewed trace |
| H3 | Persistent checkpoint는 정상 성공률보다 fault recovery에 더 큰 영향을 준다. | Context-reset/worker-restart ablation |
| H4 | Deterministic verifier는 단순 visible pass보다 scope violation과 regression을 더 잘 차단한다. | Verifier ablation |

H1·H2가 핵심 실험이다. H3·H4는 독립된 stress/ablation 결과로 보고한다.

## 6. Primary user flows

### Standard run

1. 사용자가 audited task와 repository base commit을 선택한다.
2. 시스템이 격리된 agent workspace를 만든다.
3. Agent가 issue를 intake하고 bug를 재현한다.
4. Agent가 계획을 세우고 constrained tool로 patch를 만든다.
5. Agent가 visible check를 실행하고 diff를 검토한다.
6. Agent 종료 후 별도 evaluator가 private check와 policy verifier를 실행한다.
7. 시스템이 run trace, artifact, outcome을 저장한다.

### Memory-conditioned run

1. Task metadata와 signal을 추출한다.
2. 선택한 memory policy를 fixed token budget 안에서 실행한다.
3. Fixed C는 승인된 exact bundle을 항상 제공하고, threshold/no-match는 향후 selective D에만 적용한다.
4. 동일한 agent/harness 조건으로 run을 수행한다.
5. No-memory paired run과 task 단위로 비교한다.

### Recovery run

1. Configuration에 지정한 deterministic fault를 주입한다.
2. 새 worker가 동일 run ID와 마지막 durable checkpoint를 읽는다.
3. Repository state와 patch/action identity를 대조한다.
4. 완료된 action은 건너뛰고 첫 미완료 action부터 재개한다.
5. 중복 action과 recovery outcome을 별도 metric으로 기록한다.

## 7. Scope-compliant success

메인 성공 판정은 다음과 같다.

```python
scope_compliant_success = (
    hidden_tests_passed
    and regression_tests_passed
    and scope_policy_passed
    and safety_policy_passed
)
```

Visible check는 agent feedback이며 단독 성공 조건이 아니다. LLM reviewer 결과는 qualitative evidence로만 사용하고 primary success bit를 바꾸지 않는다.

## 8. MVP boundary

- 2개 Python repository
- smoke 3~5 task, development 8~10 task, held-out 12~15 task
- 초기 runtime readiness는 task/condition당 1회, confirmatory held-out 비교는 조건당 최소 2회 반복
- context reset, worker restart, test timeout의 3개 fault
- CLI와 machine-readable JSON/CSV report
- UI는 run list, trace timeline, diff, verifier result, condition comparison만 제공

Task 수보다 audit 품질을 우선한다. 모든 evaluation task에는 base commit, public/private spec, hidden acceptance, regression check, reference patch, audit note가 있어야 한다.

## 9. Product acceptance

포트폴리오용 v1은 다음을 증거와 함께 보여야 완료다.

1. Reference, known-bad, safety-negative fixture를 evaluator가 구분하고 required safety evidence 부재를
   fail-closed로 처리한다.
2. Single agent run이 완전한 manifest·trace·artifact를 남긴다.
3. Worker kill 이후 중복 patch 없이 동일 run을 재개한다.
4. Development-validation에서 A/C fixed-bundle delivery를 검증한 뒤, 별도 승인된 frozen held-out 비교를 실행한다.
5. 사전등록된 held-out 단계에서 SCRR, 비용, negative-transfer와 명시적으로 제한된 uncertainty summary를 생성한다.
6. 최소 trace viewer에서 대표 성공·실패 run의 provenance를 확인할 수 있다.

개선이 없거나 음수여도 실험이 재현 가능하고 failure analysis가 정직하면 유효한 결과다.
