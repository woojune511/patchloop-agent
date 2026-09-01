# PatchLoop Agent Guide

이 파일은 repository 전체에 적용된다. 과거 milestone 상세는 `docs/archive/snapshots/d121/`에
보존되어 있으며 현재 작업의 지침이 아니다.

## Mission

재현 가능한 평가 기반에서 single coding agent를 실행하고 trace-driven failure memory와 recovery
정책의 효과를 공정하게 비교한다. Agent가 제품이며 evaluator, recovery, memory pipeline은 검증과
개선을 위한 지원 계층이다.

## Current state

- D-129-D-141, historical V1-V25, development R3-R8, held-out R7/R11/R14-R16 and Rapid R1-R24 are immutable; never
  retry, repair, relabel or resume them. D-142 is source-qualified/unactivated/deferred.
- Evaluator-v1 still assigns literal safety PASS. V2 uses typed controls and receipts; raw results remain
  `official=false`. Selective retrieval and B/D authority are closed.
- Exact consumed metrics/hashes and limits are owned by `docs/current-status.md` and `docs/09-evidence.md`; none proves
  a causal/general benefit. PDM is retired and AnyIO is retained.
- R20 settled 6/6 for `$1.62950550`; V22 and V24 both reached/submitted/succeeded 0/3/0. Two V24 rows exposed an
  internal initial-plan/feedback compatibility confound, so V24 is not promoted and lower cost is censored.
- R21 consumed candidate-v29 once and settled 3/3 for `$1.42525890`. V25 reached/submitted/succeeded 1/3/0; two rows
  recorded a valid initial plan and first mutation, but the preregistered evaluator-reach floor was 2/3. V25 is not
  promoted and R21 cannot retry; no quality, efficiency or generalization claim follows.
- R22 candidate-v30's approved entry was stopped before batch start: its complete path would inspect the image 13 times
  against approval for one. All six rows are unstarted, provider/evaluator/model cost are zero; outer Docker preflight
  count is unknown. The plan and prestart-stop audit are preserved. Do not retry.
- R23 candidate-v32 inspected its image once, then halted after 2 settled rows for `$0.16285425`; 4 rows never started.
  V25 submitted but failed hidden evaluation; V26 hit a provider strict-schema rejection before generation. Zero model
  events do not mean zero API requests. R23 is consumed, cannot retry/resume and supports no V25/V26 comparison.
- R24 candidate-v33 inspected its image once, then halted after 3 settled rows for `$0.927549`; 3 rows never started.
  No row reached the evaluator or submitted. V25 exhausted exploration; V27 hit three cross-field lifecycle-plan
  rejections across two rows, and the latter recovery timed out. R24 is consumed, cannot retry/resume and supports no
  V25/V27 comparison or promotion.
- Paid authority is closed. Harbor has 0/12 local images; pull authority is closed. Work Item 86 selected Lean V28 only
  as a future `official=false` Rapid treatment; Work Item 87 has no candidate or execution authority yet.
  `docs/current-status.md` owns current prose and `docs/09-evidence.md` owns exact tuples.

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
