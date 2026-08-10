# PatchLoop Agent Guide

이 파일은 repository 전체에 적용된다. 과거 milestone 상세는 `docs/archive/snapshots/d121/`에
보존되어 있으며 현재 작업의 지침이 아니다.

## Mission

재현 가능한 평가 기반에서 single coding agent를 실행하고 trace-driven failure memory와 recovery
정책의 효과를 공정하게 비교한다. Agent가 제품이며 evaluator, recovery, memory pipeline은 검증과
개선을 위한 지원 계층이다.

## Current state

- D-129부터 D-138까지는 immutable historical predecessor다. Consumed gate, attempt 또는 marker를
  retry/resume/repair/backfill하지 않는다.
- D-136은 공식 public GET 1회, HTTP 200, redirect 0, replay 3,735 bytes를 보존하고 consumed됐다.
  Provider/evaluator/agent와 비용은 0이다.
- D-137은 receipt 뒤 Docker attempt→ACTION_STARTED+READY, SDK attempt→ACTION_STARTED+BLOCKED 순서로
  종료되고 consumed됐다. Docker는 bounded read-only 관찰에서 READY였고, SDK blocker는
  `OPENAI_API_KEY` presence false였다. Credential/environment value, `.env`, SDK import/probe, transport와
  network 관찰은 모두 0이었다.
- D-138은 receipt와 attempt 뒤 ACTION_STARTED+BLOCKED terminal commit
  `9f31d330190aa83768077b17c3cde47eb86c639d`로 종료되고 consumed됐다. `OPENAI_API_KEY` presence는
  false였고 membership check는 3회였다. Credential/environment value, `.env`, child launch, SDK
  import/probe, transport dispatch와 network는 모두 0이며 D-138을 재시도하지 않는다.
- 현재 D-139 gate는 `d139_09f2e9dfe0ee333a2683c058b772b92f025708c4bcc6b7f1eb89c007ed8df7f8`다.
  Source commit `f5625be6cf98b5f8824a0d6a5068f1cf03e94d98`, tree
  `073f821ce8f800a9bbd4cf56c228f00804a8c55a`는 D-138 terminal commit의 exact four-path sole child다.
- D-139는 source-qualified only다. Fully injected/mocked focused test는 168/168이며 이 count는 다른
  검증과 합산하지 않는다. Future artifact와 source-prep membership/value/SDK/child/network/Docker 관찰은
  0이다. Fresh exact activation 뒤 `-E -s -B` parent가 inherited environment에서 세 membership bit만
  확인하고, eligible SDK 검증은 ambient forwarding이 없는 `env={}` child에서 고정 placeholder와
  zero-dispatch로 수행한다.
- Provider/evaluator/agent, retrieval/injection, execution hash/candidate, cost와 A/C authority는 닫혀 있다.
- Moto/Babel A/C source는 구현됐지만 live result나 memory benefit 근거는 없다.
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
