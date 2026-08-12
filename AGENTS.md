# PatchLoop Agent Guide

이 파일은 repository 전체에 적용된다. 과거 milestone 상세는 `docs/archive/snapshots/d121/`에
보존되어 있으며 현재 작업의 지침이 아니다.

## Mission

재현 가능한 평가 기반에서 single coding agent를 실행하고 trace-driven failure memory와 recovery
정책의 효과를 공정하게 비교한다. Agent가 제품이며 evaluator, recovery, memory pipeline은 검증과
개선을 위한 지원 계층이다.

## Current state

- D-129부터 D-141까지는 immutable historical predecessor다. Consumed gate, attempt 또는 marker를
  retry/resume/repair/backfill하지 않는다.
- D-136은 공식 public GET 1회(HTTP 200, redirect 0, replay 3,735 bytes)를 보존했고, D-137은 bounded
  Docker READY 뒤 SDK missing-key BLOCKED로 종료됐다. D-138부터 D-140도 missing-key BLOCKED다. 모두 consumed며
  external mutation/value/`.env`/SDK dispatch는 0이었다. Exact tuple은 `docs/09-evidence.md`가 소유한다.
- D-141은 gate→receipt→attempt→ACTION_STARTED+BLOCKED transition
  `6405be40eb52d71fc9376065b553a04164543a4b`로 종료되고 consumed됐다. `OPENAI_API_KEY`, `PYTHONHOME`,
  `PYTHONPATH` presence는 false/false/false였고 membership check는 3회였다. Credential/environment value,
  `.env`, child launch, SDK import/probe, transport/network와 provider/evaluator/agent는 모두 0이었다.
- 현재 D-142 gate는 `d142_9515aeb4c7289fa26987ec605917c395e54b27d076cd226c266acd2a3cb82914`다.
  Source commit `1370cf43c08cefb550b158a5d4172a60ac172470`, tree
  `7f7e7e25c79899eee6180ae45767492435003096`는 D-141 terminal commit의 exact four-path sole child다.
- D-142의 evidence state는 source-qualified/unactivated이며 planning disposition은 deferred다. Fully
  injected/mocked focused test 170/170은 별도 local evidence이고 runtime artifact나 external observation은
  없다. 원래 one-use contract는 `reports/`에 보존하지만 현재 경로에서 receipt/attempt/marker/terminal을
  만들지 않는다.
- 현재 evaluator-v1 runtime은 safety verdict를 literal PASS로 둔다. Evaluator-v2는 separately supplied
  authority가 있을 때만 standard runner가 선택하며 durable-prefix/CAS 재검증, append-only receipt,
  completed-result persistence, qualification과 completion adapter까지 local/mock으로 검증됐다. Raw v2
  result는 계속 `official=false`이고 새 A/C 전에 새 source/suite/source-qualification identity가 필요하다.
- Evaluator-v2 boundary는 `04ee027171d9d4891c4f481d2ccfb277e7a4a9e6`다. V1/v2는 immutable predecessor다.
  Qualified executable v3 source `ce0628880107db2319816272cfa49adc7ea99667`와 state
  `ncpstate_105d0becd0a33fe453e6be83044b239263eb855c165da6f275d9e4591e54f317`는 exact approval 뒤 1회
  `BLOCKED(docker_not_ready)` terminal로 consumed됐다. Read-only Docker CLI는 8회였고 daemon start/pull/load/
  mutation, `.env` read, SDK child, network/provider/evaluator/agent는 0이었다. Retry/resume하지 않는다.
- Manual-start v4 source `5b592e4f4f86a62d90951e49494ed3f8cf2ae315`와 state
  `ncpstate_9f8c92448974e89bd7c244feff4df63c94a4a82e6f6e526c262f3cb43b9effef`는 사용자 수동 시작 보고만
  결속한다. Daemon/image/container는 미검증이고 runtime/approval/external observation/mutation은 0이다.
- Retrieval/injection, new `.env`/SDK/Docker observation, execution candidate, cost와 A/C authority는 닫혀 있다.
- Moto/Babel A/C source는 구현됐지만 live result나 memory benefit 근거는 없다.
- 현재 상태의 단일 prose authority는 `docs/current-status.md`다.

- V5/v7/v12 are immutable consumed failures. V7 stopped at fixed `diagnostic_runtime_import_error`; v12 ended
  `ERROR(child_checker_error/child_output_invalid)` after Docker passed. Both had forbidden activity 0 and cannot
  retry. V8-v11 are immutable offline/source/state/approval predecessors and cannot be reused; exact tuples are in
  `docs/09-evidence.md`.
- Framed v13 is consumed `BLOCKED(docker_not_ready)` at `d9fb103b7be464f3ff1aaf73ef31097eb9815239`;
  eight Docker reads ran and `.env`/SDK/network/mutation stayed 0. Retry/resume is false.
- Manual-restart v14 consumed `ERROR(child_checker_error/framed_output_invalid)` at `e63f418`: Docker passed eight
  reads and one child returned without an envelope. Recorded forbidden counts are 0, but accounting is incomplete,
  unknown activity is true and retry/resume is false.
- V15 is the source predecessor. V16 consumed one exact-approved attempt at `30c254d`: Docker passed 8 reads, one
  child returned no envelope, and terminal `ERROR(child_checker_error/framed_output_invalid)` has incomplete
  accounting, unknown activity true and retry/resume false.
- V18 `e4c76af` preserves v17's supervisor/worker pipe. Exact state/approval led to one consumed attempt at
  `490f1ed`: Docker passed 8 reads, one supervisor child returned no envelope, and terminal is
  `ERROR(child_checker_error/supervised_output_invalid)`. Forbidden counts are 0, accounting incomplete/unknown and
  retry false; exact IDs remain in `docs/09-evidence.md`.
- V19 source `91300324d0fd9ac83356204f03325cded4137f12` changes only the outer result transport. V20 activation
  wrapper source `304da8e9e4fe0d730c184944006e4c76970c12f0`, contract
  `ncpcontract_2c5d22d26c1ae017e8b78d0e99fe99d33b5916b8282a1c186f25fbd818f68102` and qualification
  `sha256:6e6a58dcaa1f034ad6146e955bdcd9a289b4031ec261ed22d71fc5264f8fe90b` are offline-only. Self-attested state
  `ncpstate_7931e548e99c34ba36b334bab032d7359701929cbb6866d8b713bc2c94b9d17b` records observation 0 and no
  execution authority. Approval `ncpapproval_4dc5670957a304fcbf4178479059a61217a528d008a5f4d70603269e11c0c49f`
  is bound with no attempt; the next gate is a separate exact immediate-run statement.

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
7. **Deterministic primary grading.** 새 success는 hidden acceptance, regression, scope와 safety 각각의 실제
   code-evaluator evidence가 있을 때만 인정한다. 현재 v1 literal safety PASS는 새 A/C를 막는 gap이다.
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
