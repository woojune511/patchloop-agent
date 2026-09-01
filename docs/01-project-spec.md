# Project Spec

상태: **Normative draft**

## 1. Problem statement

Visible test만 통과한 coding agent는 테스트 약화, scope/API 변경, dependency 추가나 regression으로도 성공처럼
보일 수 있다. Context reset과 worker crash는 작업을 중복시키고, 과거 trace의 무차별 주입은 비용과 오판을
늘린다.

PatchLoop의 주 질문은 동일 모델·예산에서 structured failure memory가 held-out scope-compliant success를
높이고 비용과 negative transfer를 줄이는지다. Persistent checkpoint의 recovery 효과는 별도 reliability
질문이며 두 결과를 하나의 인과 주장으로 합치지 않는다.

## 2. Product goals

- Python snapshot과 issue를 받는 phase 기반 single agent, constrained tools와 external recovery state
- agent와 분리된 hidden acceptance/regression/scope/dependency/API/safety evaluator
- evidence 기반 failure taxonomy와 solution-leakage 없는 structured memory
- No Memory → fixed Structured readiness → 향후 Raw/Selective의 단계적 공정 비교
- 결과·비용·trace·verifier report와 최소 viewer/Draft PR demo

## 3. Explicit non-goals for v1

- 멀티에이전트/self-deploy loop, 다중 언어, unrestricted shell 또는 분산 운영 플랫폼
- LLM-only grading, benchmark 전체 실행, SaaS dashboard나 결과 전 UI/GitHub 확장

## 4. Users and outputs

| 사용자 | 필요한 결과 |
| --- | --- |
| Agent/LLM platform engineer | 재현 가능한 state/tool/budget trace |
| Evals engineer | audited task, manifest, deterministic verifier, paired result |
| Maintainer/demo reviewer | issue, patch, 검증 근거, timeline, Draft PR |

각 run은 manifest, events/checkpoint, patch, verdict/failure와 resource accounting을 남긴다.

## 5. Research hypotheses

| ID | Hypothesis | Primary evidence |
| --- | --- | --- |
| H1 | Structured failure memory가 no-memory보다 held-out SCRR을 높이는지 단계적으로 검증한다. | frozen-panel A/C와 별도 fresh successor |
| H2 | Raw trace는 token을 더 쓰고 무관한 task에서 negative transfer를 만들 수 있다. | overhead, failure flip, reviewed trace |
| H3 | Persistent checkpoint는 정상 성공보다 fault recovery에 더 큰 영향을 준다. | reset/restart ablation |
| H4 | Deterministic verifier는 visible pass보다 scope violation과 regression을 더 잘 차단한다. | verifier ablation |

H1·H2가 핵심 실험이고 H3·H4는 독립 stress/ablation으로 보고한다.

## 6. Primary user flows

1. **Standard:** audited task/base → 격리 agent → 별도 private evaluator → immutable outcome.
2. **Memory-conditioned:** fixed-budget A-null/C-bundle 외 조건을 고정해 task 단위로 비교한다.
3. **Recovery:** fault 뒤 checkpoint와 action identity를 대조해 첫 미완료 action부터 재개한다.

## 7. Scope-compliant success

```python
scope_compliant_success = (
    hidden_tests_passed
    and regression_tests_passed
    and scope_policy_passed
    and safety_policy_passed
)
```

Visible check는 agent feedback일 뿐이고 LLM review는 qualitative evidence라서 primary success bit를 바꾸지
않는다.

## 8. MVP boundary

- audited Python smoke/development/held-out와 사전등록 반복
- reset/restart/timeout fault, machine-readable report와 최소 UI
- 모든 task에 base, public/private spec, hidden/regression check, reference와 audit note

Task 수보다 audit 품질을 우선한다.

## 9. Product acceptance

1. Evaluator가 reference, known-bad, safety-negative를 구분하고 safety evidence 부재를 fail-close한다.
2. Single-agent run이 완전한 manifest, trace와 artifact를 남긴다.
3. Worker kill 뒤 중복 patch 없이 동일 run을 재개한다.
4. Development A/C delivery 뒤 별도 승인된 frozen held-out 비교를 실행한다.
5. 사전등록 held-out에서 SCRR, 비용, negative transfer와 제한된 uncertainty를 생성한다.
6. 최소 viewer에서 대표 run의 provenance를 확인한다.

개선이 없거나 음수여도 실험이 재현 가능하고 failure analysis가 정직하면 유효한 결과다.
