# PatchLoop Agent Guide

이 파일은 repository 전체에 적용된다. 과거 milestone 상세는 `docs/archive/snapshots/d121/`에
보존되어 있으며 현재 작업의 지침이 아니다.

## Mission

재현 가능한 평가 기반에서 single coding agent를 실행하고 trace-driven failure memory와 recovery
정책의 효과를 공정하게 비교한다. Agent가 제품이며 evaluator, recovery, memory pipeline은 검증과
개선을 위한 지원 계층이다.

## Current state

- D-129는 procedural sequence-blocked historical evidence이며 retry/resume/repair하지 않는다. D-130
  offline predecessor와 D-131 local-admission source gate도 historical predecessor로 보존한다.
- D-131-qualified local admission은 완료됐다. D-130 approval receipt
  `d130approval_03c8c824f0d74122b8233df9810897b898c29b3bf907dd1a5cfd364f5026e010`와 durable
  `ARMED_WAITING_EXACT_ACTIVATION` intent
  `d130intent_4cd20c7a8bbd20751b2f6a7b4a0d13de16d7aa5a41b6bf20648dedb414b6a153`는 각각 exact
  receipt-only/intent-only commit으로 보존된다. 이것들은 external activation이 아니다.
- D-132는 D-130 external-activation implementation source를 offline-qualified했다. Gate ID는
  `d132_ae224ab320e74bf871b74b0c9df23f88c5de170dfd26e7724aa234f29b2b0ba7`, source commit은
  `ccf898d869342a9d5da42a1fef2c00e593fe91b4`, status는
  `D132_D130_EXTERNAL_ACTIVATION_IMPLEMENTATION_OFFLINE_SOURCE_QUALIFIED_FRESH_ACTIVATION_REQUIRED`다.
- D-132 source는 activation receipt-only commit, phase별 committed attempt, action-started marker,
  terminal transition commit과 final gate를 fail-closed로 검증한다. Started-without-terminal 또는
  orphan/blocked phase는 consumed이며 retry하지 않는다.
- D-132 이전 activation request/challenge는 수신됐지만 그 메시지가 스스로 activation이 아님을
  명시했다. 실행되지 않았고 D-132 topology 변경 뒤 재사용할 수 없다.
- 현재 D-132 activation receipt, phase attempt/started/terminal/final gate와 external action은 모두 없다.
  Official-docs/network/pricing, Docker/SDK/credential, provider/evaluator/agent, retrieval/injection,
  hash/candidate, cost와 A/C authority도 없다.
- Moto/Babel의 A(`no_memory`)/C(`structured`) exact four-row suite와 D-110 bundle delivery, R2
  cost/completion source는 구현됐지만 live result나 memory benefit 근거는 없다.
- 현재 상태의 단일 prose authority는 `docs/current-status.md`다.

## Required reading

모든 작업은 아래 순서로 필요한 문서만 읽는다.

1. `docs/00-index.md`
2. `docs/current-status.md`
3. 구현 대상에 해당하는 문서 한두 개

| 작업 | 추가 문서 |
| --- | --- |
| agent/state/tool | `docs/02-architecture.md`, `docs/03-contracts.md` |
| task/evaluator/schema | `docs/03-contracts.md`, `docs/04-evaluation-protocol.md` |
| memory/experiment | `docs/04-evaluation-protocol.md`, `docs/05-implementation-plan.md` |
| decision change | `docs/06-decisions.md` |
| validation/runbook | `docs/07-reproduction.md` |
| claims/review | `docs/08-limitations.md`, `docs/09-evidence.md` |

Archive 문서는 historical audit가 필요한 경우에만 읽는다.

## Non-negotiable invariants

1. **Evaluator first.** Task schema, hidden evaluator와 Docker boundary를 agent prompt보다 먼저 고정한다.
2. **Public/private separation.** Private spec, hidden tests, reference patch와 oracle 결과를 agent,
   memory, task selection 또는 retrieval input에 노출하지 않는다.
3. **External run state.** Event, checkpoint, evaluator data와 generated state를 task repository 안에
   기록하지 않는다.
4. **Constrained execution.** Agent에는 등록된 tool/check만 제공하고 unrestricted shell을 주지 않는다.
5. **Append-only evidence.** 이미 관찰된 run과 gate를 수정하거나 결과를 덮어쓰지 않는다.
6. **Idempotent recovery.** Action identity와 input hash로 중복 실행을 감지한다.
7. **Deterministic primary grading.** Hidden acceptance, regression, scope와 safety는 코드 evaluator가 판정한다.
8. **Fair comparison.** Memory 외 model, prompt, tool, task, commit, image, budget, retry와 evaluator를 고정한다.
9. **No held-out tuning.** Held-out 결과를 본 뒤 task, memory, threshold, prompt 또는 policy를 바꾸지 않는다.
10. **No solution leakage.** Memory에 정답 코드, hidden assertion 또는 reference patch를 넣지 않는다.
11. **No invented results.** Plan, implemented path, measured result와 authorized execution을 분리한다.
12. **No authority inference.** Config, test pass, candidate hash 또는 일반 “진행해줘”를 gated execution
    승인으로 해석하지 않는다.

## Implementation workflow

1. `docs/05-implementation-plan.md`의 현재 work item을 선택한다.
2. 입력, 출력, failure mode, authority boundary와 acceptance test를 먼저 적는다.
3. Machine-visible schema나 실험 비교가 바뀌면 같은 change에서 contract/protocol을 갱신한다.
4. 최소 test부터 관련 regression까지 실행한다.
5. Private data, task-repository state, held-out tuning과 scope 확장을 점검한다.
6. 실제 실행한 명령과 실행하지 않은 항목을 구분해 handoff한다.

## Definition of done

- Success와 주요 failure path가 test로 검증됐다.
- Public/private와 append-only boundary가 유지됐다.
- 실제 artifact는 stable ID/hash/provenance를 갖는다.
- Paid/network/Docker 실행은 해당 승인 범위를 넘지 않는다.
- Active 문서는 현재 동작만 설명하고 historical narrative는 archive에 남긴다.
- 결과가 없으면 개선이나 memory benefit을 주장하지 않는다.

## Repository boundaries

```text
patchloop/agent/       orchestration and phase policy
patchloop/tools/       constrained tool implementations
patchloop/sandbox/     process/container isolation
patchloop/state/       events, checkpoints and recovery
patchloop/verifier/    deterministic graders
patchloop/failures/    taxonomy and classification
patchloop/memory/      memory schema and delivery
patchloop/evals/       experiment runner and metrics
tasks/                 audited public/private fixtures
experiments/           immutable suites and offline plans
reports/               machine-readable evidence
docs/                  current documentation and historical snapshots
```
