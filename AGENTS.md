# PatchLoop Agent Guide

이 파일은 repository 전체에 적용된다. 과거 milestone의 상세 서술은
`docs/archive/snapshots/d121/`에 보존되어 있으며 현재 작업의 지침이 아니다.

## Mission

재현 가능한 평가 기반에서 single coding agent를 실행하고, trace-driven failure memory와
recovery 정책의 효과를 공정하게 비교한다. Agent가 제품이며 evaluator, recovery, memory
pipeline은 이를 검증하고 개선하기 위한 지원 계층이다.

## Current state

- 최신 봉인 checkpoint는 D-125 offline runtime-finalization source qualification이다. Gate ID는
  `d125_ed9c892a598ce4543591bf3b9135a1cbe3752589fdc447b05867d59e07d45539`, semantic body SHA는
  `sha256:ed9c892a598ce4543591bf3b9135a1cbe3752589fdc447b05867d59e07d45539`, file SHA는
  `sha256:9bc5f6e618f31312dc5026a807eabf478e47c05893cca72c71328378b593856e`이며 13,820 bytes다.
- Moto와 Babel development-validation task의 A(`no_memory`)와 C(`structured`) exact four-row
  suite, fixed D-110 bundle delivery, condition-aware manifest/trace qualification을 구현했다. 현재
  R2 exact full-schedule cost reservation/settlement와 four-row completion gate source를 구현했다.
- D-124는 sealed-historical predecessor다. D-125는 repository-local at-most-once row consumption과 mocked
  process-fault finalization recovery source만 qualified했다. Cross-store/global/cross-clone exclusion,
  noncooperative path swap, actual kill과 torn-write/power-loss durability는 검증하지 않았다.
- D-125 status는 `D125_AC_RUNTIME_FINALIZATION_SOURCE_QUALIFIED_EXECUTION_CANDIDATE_BLOCKED`다. Gate는
  23/23, D-124+D-125는 37/37을 통과했다. Row attestation 147과 finalization union 136은 겹치므로 합산하지
  않는다. 실제 reservation, result, candidate와 execution hash는 없다.
- Provider/evaluator/agent/Docker/retrieval call은 모두 0이다. Runtime memory injection, paid execution,
  held-out/core campaign은 별도의 exact approval 전까지 금지한다.
- D-121 no-start successor는 historical/deferred다. D-119를 retry, resume 또는 repair하지 않는다.
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
7. **Deterministic primary grading.** Hidden acceptance, regression, scope와 safety는 코드 기반
   evaluator가 판정한다.
8. **Fair comparison.** Memory 외 model, prompt, tool, task, commit, image, budget, retry와 evaluator를
   고정한다.
9. **No held-out tuning.** Held-out 결과를 본 뒤 task, memory, threshold, prompt 또는 policy를 바꾸지 않는다.
10. **No solution leakage.** Memory에 정답 코드, hidden assertion 또는 reference patch를 넣지 않는다.
11. **No invented results.** Plan, implemented path, measured result와 authorized execution을 분리해 쓴다.
12. **No authority inference.** Checked-in config, test pass, candidate hash 또는 일반적인 “진행해줘”를
    provider call이나 gated execution 승인으로 해석하지 않는다.

## Implementation workflow

1. `docs/05-implementation-plan.md`의 현재 work item을 선택한다.
2. 입력, 출력, failure mode, authority boundary와 acceptance test를 먼저 적는다.
3. Machine-visible schema나 실험 비교가 바뀌면 같은 change에서 계약과 protocol을 갱신한다.
4. 최소 단위 test부터 관련 regression까지 실행한다.
5. Private data 노출, task repository 내부 state, held-out tuning과 scope 확장을 점검한다.
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
