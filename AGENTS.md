# PatchLoop Agent Guide

이 파일은 repository 전체에 적용된다. 과거 milestone 상세는 `docs/archive/snapshots/d121/`에
보존되어 있으며 현재 작업의 지침이 아니다.

## Mission

재현 가능한 평가 기반에서 single coding agent를 실행하고 trace-driven failure memory와 recovery
정책의 효과를 공정하게 비교한다. Agent가 제품이며 evaluator, recovery, memory pipeline은 검증과
개선을 위한 지원 계층이다.

## Current state

- D-129-D-141, V1-V25 and their exact transitions are immutable consumed evidence in `docs/09-evidence.md`; never
  retry, repair or relabel them. D-142 remains source-qualified/unactivated/deferred and mocked tests are not runtime
  evidence.
- Evaluator-v1 still assigns literal safety PASS. V2 uses typed controls, receipts, persistence and qualification;
  raw v2 results remain `official=false`. Selective retrieval and B/D authority remain closed.
- Development R3-R6 are sealed inconclusive; R7/R9 is superseded. R10-qualified R8 consumed candidate
  `sha256:60c67908...cff9e`, completed four receipt-qualified rows for `$0.3664215`, and has an append-only correction
  for its stale v1/v2 projection. It supports descriptive development readiness only.
- Held-out R7 sealed 0 settled/1 unsettled/47 not-started. R11 candidate `sha256:f48a0de...a6b0` consumed a fresh
  `$252`/`$275` approval and sealed 2 settled/1 observed-unsettled/45 not-started; costs were `$0.15699525` settled and
  `$0.41801625` total observed-started. Successor attribution is `EVALUATOR_CONTROL_CONTRACT_COLLISION`, with zero
  agent-visible marker matches. No complete analysis or memory claim follows.
- Development-only evidence lowers equal A/C to 1M/100k/1.1M tokens and `$57.60`/`$60`; R11 outcomes and held-out
  task content were excluded. Contract R8 → binding R9 → materialization R5 → execution R6 → preflight R14 remains
  zero-authority: no candidate, observation, approval or spend.
- Local no-call preflight permits at most three transient pre-provider attempts. Paid campaign identity ignores
  readiness timestamps and is one-use by semantic source/suite/schedule; a future run needs committed qualified source,
  fresh clean candidate and separate exact approval. No provider execution is currently authorized.
- `docs/current-status.md` is the single current prose authority; `docs/09-evidence.md` owns exact tuples.

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
5. **Append-only evidence.** 이미 관찰된 attempt를 수정하거나 결과를 덮어쓰지 않는다. 동일 source/config의
   새 attempt는 새 ID로 허용한다.
6. **Idempotent recovery.** Action identity와 input hash로 중복 실행을 감지한다.
7. **Deterministic primary grading.** 새 success는 hidden acceptance, regression, scope와 safety 각각의 실제
   code-evaluator evidence가 있을 때만 인정한다. 현재 v1 literal safety PASS는 새 A/C를 막는 gap이다.
8. **Fair comparison.** Memory 외 model, prompt, tool, task, commit, image, budget, retry와 evaluator를 고정한다.
9. **No held-out tuning.** Held-out 결과를 본 뒤 task, memory, threshold, prompt 또는 policy를 바꾸지 않는다.
10. **No solution leakage.** Memory에 정답 코드, hidden assertion 또는 reference patch를 넣지 않는다.
11. **No invented results.** Plan, implemented path, measured result와 authorized execution을 분리한다.
12. **Bounded authority.** Repository policy authorizes only the documented no-call preflight. Provider/paid
    execution requires one explicit campaign approval binding the exact execution hash and cap.

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
