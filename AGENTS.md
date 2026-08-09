# PatchLoop Agent Guide

이 파일은 repository 전체에 적용된다. 과거 milestone 상세는 `docs/archive/snapshots/d121/`에
보존되어 있으며 현재 작업의 지침이 아니다.

## Mission

재현 가능한 평가 기반에서 single coding agent를 실행하고 trace-driven failure memory와 recovery
정책의 효과를 공정하게 비교한다. Agent가 제품이며 evaluator, recovery, memory pipeline은 검증과
개선을 위한 지원 계층이다.

## Current state

- D-129 offline gate는 historical이다. 승인 뒤 공식 문서 tool open 1회가 machine receipt와 durable
  attempt보다 먼저 발생해 external phase는 `D129_EXTERNAL_NO_CALL_SEQUENCE_OBSERVED_BLOCKED`로
  terminal 봉인됐다.
- Receipt ID는 `d129approval_0d505214f607b0f2a2536e1b754750131bc4b6dab2995d24a12554d63090fb42`,
  terminal ID는 `d129sequenceblock_b5fc90e29ed2ca7febda54a2e63e4f5a0606703e0e93a997fab719d33797f5c8`다.
  Receipt는 non-retroactive이며 consumed다. D-129를 retry, resume, repair하지 않는다.
- Canonical pricing capture, Docker, image pull, SDK, provider/evaluator/agent, retrieval/injection,
  hash/candidate, cost와 A/C 실행은 모두 0이다. Underlying docs HTTP/redirect 수는 unknown이다.
- D-130 offline successor gate와 evidence commit `d6079e55fd1c4745b05c2e345228b1a66d0a3df4`는
  historical predecessor다. 그 뒤 받은 D-130 Stage 1 승인은 committed writer가 없어 실행되지 않았고,
  D-131 topology 변경 뒤 재사용할 수 없다.
- D-131 offline gate는 D-130 chain과 local-admission implementation source commit
  `9cd736c0221bba17375c3b7ddce02e5214fc21fe`를 봉인했다. Gate ID는
  `d131_849502e63d33aa3c8ceea8dc03faf0ff86e8ec51db9321fa13544df15a4af057`이고 status는
  `D131_D130_LOCAL_ADMISSION_IMPLEMENTATION_OFFLINE_SOURCE_QUALIFIED_APPROVAL_REQUIRED`다.
- 다음 작업은 fresh exact D-131-qualified D-130 local-admission approval이다. 승인되더라도 receipt-only
  commit, durable `ARMED_WAITING_EXACT_ACTIVATION` intent-only commit과 activation challenge만 만들 수
  있고 external action은 0이어야 한다. Stage 2는 그 tuple들을 인용하는 별도 exact activation이 필요하다.
- 실제 D-130 receipt/intent는 없고 D-131-qualified admission, activation, external phase, credential,
  Docker/SDK, hash/candidate, cost와 A/C authority도 아직 없다.
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
