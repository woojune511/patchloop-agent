# PatchLoop Agent Guide

이 파일은 repository 전체에 적용된다. 과거 milestone 상세는 `docs/archive/snapshots/d121/`에
보존되어 있으며 현재 작업의 지침이 아니다.

## Mission

재현 가능한 평가 기반에서 single coding agent를 실행하고 trace-driven failure memory와 recovery
정책의 효과를 공정하게 비교한다. Agent가 제품이며 evaluator, recovery, memory pipeline은 검증과
개선을 위한 지원 계층이다.

## Current state

- D-129부터 D-141까지는 immutable consumed predecessor다. D-136의 public pricing GET과 D-137-D-141의
  bounded BLOCKED transitions를 포함한 exact tuple은 `docs/09-evidence.md`가 소유하며 retry/repair하지 않는다.
- D-142는 source-qualified/unactivated/deferred다. Mocked test는 runtime evidence가 아니며 현재 경로는
  receipt, attempt, marker 또는 terminal을 만들지 않는다.
- 현재 evaluator-v1 runtime은 safety verdict를 literal PASS로 둔다. Evaluator-v2는 separately supplied
  authority가 있을 때만 standard runner가 선택하며 durable-prefix/CAS 재검증, append-only receipt,
  completed-result persistence, qualification과 completion adapter까지 구현됐다. Raw v2 result는 계속
  `official=false`; R3 Moto A의 live receipt-qualified completion은 한 행의 실제 v2 evidence다.
- Evaluator-v2 boundary는 `04ee027171d9d4891c4f481d2ccfb277e7a4a9e6`다. V1/v2는 immutable predecessor다.
  Qualified executable v3 source `ce0628880107db2319816272cfa49adc7ea99667`와 state
  `ncpstate_105d0becd0a33fe453e6be83044b239263eb855c165da6f275d9e4591e54f317`는 exact approval 뒤 1회
  `BLOCKED(docker_not_ready)` terminal로 consumed됐다. Read-only Docker CLI는 8회였고 daemon start/pull/load/
  mutation, `.env` read, SDK child, network/provider/evaluator/agent는 0이었다. Retry/resume하지 않는다.
- Manual-start v4 source `5b592e4f4f86a62d90951e49494ed3f8cf2ae315`와 state
  `ncpstate_9f8c92448974e89bd7c244feff4df63c94a4a82e6f6e526c262f3cb43b9effef`는 사용자 수동 시작 보고만
  결속한다. Daemon/image/container는 미검증이고 runtime/approval/external observation/mutation은 0이다.
- Selective retrieval과 held-out/B/D authority는 닫혀 있다. Fixed C injection은 R3 Moto C에서 live로
  실행됐지만 제출 전 exact-request token-budget guard로 evaluator에 도달하지 않았다.
- R3-R6 are sealed `inconclusive` predecessors whose successive budget/plan/qualification/runtime-binding failures
  are indexed in `docs/09-evidence.md`; no row, approval or configuration may retry, resume or transfer authority.
- R7/R9 and candidate `sha256:8b962b80...bf6c` are superseded unexecuted after offline contract audits. R10
  qualified the exact R8 execution source. Candidate `sha256:60c67908...cff9e` consumed one exact `$15.30`/`$18`
  approval; all four rows resolved, evaluator-v2 receipt-qualified and settled at `$0.3664215`. The immutable raw
  result has a stale v1/v2 completion projection; the append-only R8 R4 index records the corrected complete matrix.
- Exact R10/R9/R8/R6/R5/R4/R3 evidence tuples are owned by `docs/09-evidence.md`. R8 is descriptive development
  readiness only; no causal, held-out, retrieval or general memory-benefit claim follows.
- Held-out A/C is preregistered for 48 rows. R2/R5 qualify offline contracts and adapter source; materialization R1
  stores 12 opaque run-secret-independent templates and refreshed prices. Execution-contract R1 and no-call-preflight
  R2 source-qualify candidate/manifest/secret expansion and readiness code. One clean no-call at commit `391c4e2` saw
  SDK/key presence but `DOCKER_UNAVAILABLE`; candidate, runtime contract, call, approval, spend and execution stayed 0.
- 현재 상태의 단일 prose authority는 `docs/current-status.md`다.

- V1-V25 artifacts are immutable historical evidence. V23 reached Docker and both frames before
  `ERROR(child_checker_error/diagnostic_result_invalid)`; V24/V25 are source correction/wrapper evidence, not live
  readiness. Exact tuples remain in `docs/09-evidence.md`.
- The active fast track preserves completed attempt records but reuses unchanged source/configuration. A new version
  is required only for schema, evaluator, security-boundary or treatment changes—not for another attempt.
- Local no-call preflight may make at most three pre-provider attempts without state/approval/exact-prose ceremony.
  Paid/provider execution still requires one approval binding the exact four-row hash and hard cost cap.
- R3 through R8 executions are sealed and cannot resume or overwrite; all approvals are consumed. A future paid run
  requires a new suite/source qualification, exact candidate and separate approval. No provider execution is
  currently authorized.

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
