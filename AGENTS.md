# PatchLoop Agent Guide

이 파일은 repository 전체에 적용된다. 과거 milestone의 상세 서술은
`docs/archive/snapshots/d121/`에 보존되어 있으며 현재 작업의 지침이 아니다.

## Mission

재현 가능한 평가 기반에서 single coding agent를 실행하고, trace-driven failure memory와
recovery 정책의 효과를 공정하게 비교한다. Agent가 제품이며 evaluator, recovery, memory
pipeline은 이를 검증하고 개선하기 위한 지원 계층이다.

## Current state

- 최신 offline successor checkpoint는 D-129 approval-required gate다. Gate ID는
  `d129_fa5412dd269ba6d4f502220fe1655d6f84b746eff6fa95633691464d6e29243c`, semantic body SHA는
  `sha256:fa5412dd269ba6d4f502220fe1655d6f84b746eff6fa95633691464d6e29243c`, file SHA는
  `sha256:fd57c187d1f260952b581e60f7d0ff98243f3b4ef172c9a6d6669b3e84968512`이며 18,678 bytes다.
  Clean source commit은 `1fef6716cddca571777c8b7f9f1dc4501f988d1c`다.
- Moto와 Babel development-validation task의 A(`no_memory`)와 C(`structured`) exact four-row
  suite, fixed D-110 bundle delivery, condition-aware manifest/trace qualification을 구현했다. 현재
  R2 exact full-schedule cost reservation/settlement와 four-row completion gate source를 구현했다.
- D-126은 historical blocked이고 D-127/D-128은 terminal-blocked predecessor다. D-128은 read-only Docker
  CLI call 3개가 모두 rc 1인 뒤 receipt를 소비했으며 retry, resume 또는 repair하지 않는다.
- D-129는 사용자가 같은 Linux endpoint를 총 두 번 수동 확인했다고 기록한다. 첫 확인은 daemon
  unavailable/rc 1, 이후 확인은 client/server 29.6.2, linux/amd64, rc 0이며 기존 container auto-start가
  없었다는 보고다. 이는 self-attested이고 agent가 독립 관찰하지 않았으며 future receipt 뒤 다시
  관찰해야 한다.
- D-129 focused 12/12는 selected union 115/115에 포함된다. D-129 Docker/network/SDK/provider/evaluator/
  agent/retrieval/injection/cost/A-C는 0이고 historical D-128 Docker call은 3개다.
- D-129 receipt/external/pricing/preflight/hash/candidate/result는 없다. 다음 gate는 exact D-129 tuple과
  evidence commit을 인용한 별도 승인이 필요하다. Desktop/daemon start와 live/memory/cost는 금지한다.
- D-124/D-125의 repository-local/mock 한계는 그대로고 실제 reservation/result는 없다.
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
