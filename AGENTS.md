# PatchLoop Agent Guide

이 파일은 repository 전체에 적용된다. PatchLoop에서 작업하는 coding agent는 구현 전에 이 문서와 현재 milestone 문서를 읽어야 한다.

## Mission

재현 가능한 평가 기반 위에서 single coding agent를 실행하고, trace-driven failure memory와 recovery 정책의 효과를 공정하게 비교한다.

Repo Maintainer와 Draft PR은 데모다. 평가 harness와 실제 실험 결과가 제품의 핵심이다.

## Current state

- Evaluator, constrained offline agent, state/recovery, memory, experiment/report와 viewer의
  implementation baseline이 존재한다.
- 현재 milestone은 `D-037 controlled diagnostic offline gate`다.
  Rejected-patch retry context와 execution-hash-bound `experiment-diagnostic-v1` consumer는
  offline evidence를 통과했다. 승인된 mini D-037 r3는 provider에서 실행됐지만 rejected mutation이
  생기기 전에 per-call output allowance를 소진해 실제 retry는 아직 검증하지 못했다.
  Terminal r3 evidence와 원인은 보존됐다. r4는 official reasoning guidance에 맞춘
  25,000 per-call / 120,000 total token pair를 hash-bound profile v2로 분리해 full
  offline 검증 뒤 provider에서 정확히 한 번 실행했다. 모든 13개 generation은 completed였지만
  `REVIEW` turn 직전 남은 28,563 token으로 exact input 8,583 + response allowance 25,000을
  보장할 수 없어 local guard가 provider call 전에 종료했다. 제출·evaluator·retry episode는
  0개이고 D-037은 여전히 검증 또는 반증되지 않았다. 이 r4를 immutable evidence로 보존한다.
  D-041은 새 r5 profile v3에 strict exact-input + full 25,000 response reservation을 그대로
  유지하고 diagnostic-only total token budget을 200,000으로 고정한다. 이는 r4의 91,437-token
  prefix에 당시 최대 exact input 10,031과 25,000 allowance의 tail reservation 세 개를 더한
  196,530을 올림한 값이다. 새 `model-generation-block-v1` exact-request payload가 결속된
  generic terminal budget block은 retry 유무와 무관하게 valid trace evidence가 될 수 있지만 D-037 episode로
  세거나 gate를 열지는 않는다. Unversioned r4 qualification 21/22는 그대로 유지한다.
  Synthetic rejection, runtime reservation 의미 변경과 automatic retry는 도입하지 않는다.
  R5가 evaluator에 도달해도 rejection이 없으면 inconclusive로 보존하고 자동 재실행하지 않는다.
  이 계약은 2026-07-30 targeted 191-test, full 504-pass/2-skip와 Ruff evidence로 닫혔다.
  별도 승인된 r5 `run_0ad8676d42614fbf`는 18/18 exact input telemetry와 completed
  response, official hidden/regression/scope/safety pass, `trace-qualification-v2` 23/23을
  남겼다. 그러나 rejected candidate와 retry episode가 모두 0이어서 D-037 diagnostic은
  `retry_episode_not_observed`로 terminal inconclusive다. 계약대로 자동 재실행하지 않는다.
  D-043은 별도 r6/profile v4에서 첫 preflight-valid `PatchPrepared` candidate를 실제
  mutation 전에 정확히 한 번 거절하고 next-request exact rehydration을 검증하는 controlled
  diagnostic을 구현했다. 이 경로는 offline gateway, crash recovery, agent-loop와 qualification
  evidence 및 529 passed/2 skipped broad regression을 통과했지만 provider call은 아직 없다.
  Clean execution hash와 별도 승인 전에는 r6를, r6 gate 통과 전에는
  tool-v2/context-v3 Terra pilot을, Terra pilot이 통과하기 전에는 memory-development
  campaign을 실행하지 않는다.
- Docker 공식 evaluator smoke와 calibration 5/5, SWE-style research admission 20/20을 완료했다.
  Memory-development lane은 6/6, development-validation lane은 2/2, core-same-repo lane은
  6/6, core-cross-repo lane은 6/6이다. 세 stress sentinel과 30-run fault schedule을
  machine audit한 뒤 dataset manifest를 동결했다. 앞선 두 Live OpenAI pilot은 terminal
  agent failure로 보존돼 있다. 세 번째 pilot `run_3cb86f8d70094a11`은 당시 v1 계약에서
  official hidden/regression/scope/safety verdict와 trace qualification을 통과한 historical
  accepted pilot이다. 이후 tool/context/submission lifecycle이 v2로 바뀌었으므로 이 run은
  현재 campaign gate를 열지 않는다. 별도 mini model-candidate r1
  `run_d4fea5e7198b4abc`는 evaluator 전에 실패했다. 새 v2 mini r2
  `run_4a9737ec91964dca`는 telemetry, submission lifecycle, evaluator receipt와
  `trace-qualification-v2`를 통과했지만 hidden acceptance가 실패한 immutable task
  failure다. 이 trace는 stateless retry context가 직전 rejected patch의 hash와 오류만
  보존하고 patch body는 복원하지 않는 gap도 드러냈다. 새 `phase-evidence-v3`는 exact
  candidate/reason next-request rehydration, CAS/request qualification과 structured
  no-generation budget event를 offline test로 검증했다. D-037 r3
  `run_e90f7c52aa134182`는 input pre-count 8/8 일치와 leakage pass를 보존했지만, event 55의
  응답이 `max_output_tokens=4096`에서 incomplete가 되어 evaluator 전에 terminal
  agent/qualification/diagnostic failure로 끝났다. Mutation과 rejected retry episode는
  0개이므로 이 run은 D-037을 검증하거나 반증하지 않으며 재실행하지 않는다. R4
  `run_826c1c7fb3d242c2`는 patch 1회와 visible check pass, final diff 뒤 `REVIEW`까지
  진행했고 13/13 exact token telemetry와 completed response를 남겼다. 그러나 14번째
  generation은 `MODEL_GENERATION_BUDGET_EXCEEDED`로 시작 전에 차단됐고 evaluator와
  rejected retry에는 도달하지 못했다. Qualification 21/22의 유일한 실패는 token mismatch가
  아니라 retry candidate가 없는 generic budget-block을 현재 v3 qualifier가 terminal-valid로
  보지 않는 계약 경계다. 이 run도 재실행하지 않는다.
  후속 r5는 25,000 per-call / 200,000 total의 profile v3와
  `model-generation-block-v1`만 새로 허용했다. 승인 hash
  `sha256:97249f05deda8e59118fdac0dd6f62f44c18b086ecb16bface2cc4d0f41a3a12`로
  provider에서 정확히 한 번 실행한 `run_0ad8676d42614fbf`는 official task success와
  qualified trace를 남겼지만 rejection이 없어 D-037에는 inconclusive다. 사용량은
  121,366 input + 9,913 output token, 계산상 `$0.135633`이며 재실행하지 않는다.
  실제 subprocess hard-kill 뒤 stale
  `RUNNING` reclaim은 offline test만 통과했으며, tool-v2/context-v3 Terra pilot, stress schedule,
  12-run development campaign과 96-run core campaign은 완료되지 않았다.
- `docs/08-limitations.md`에 미완료라고 표시된 결과를 구현 또는 측정된 사실처럼 표현하지 않는다.
- 다음 dataset/campaign gate는 이전 gate의 executable evidence를 확인한 뒤 통과시킨다.

## Required reading

작업 유형에 따라 다음 문서를 읽는다.

| 작업 | 반드시 읽을 문서 |
| --- | --- |
| 모든 구현 | `README.md`, `docs/05-implementation-plan.md`, `docs/06-decisions.md` |
| task/evaluator/schema | `docs/03-contracts.md`, `docs/04-evaluation-protocol.md` |
| agent/tool/state | `docs/02-architecture.md`, `docs/03-contracts.md` |
| memory/retrieval | `docs/03-contracts.md`, `docs/04-evaluation-protocol.md` |
| report/UI | `docs/04-evaluation-protocol.md` |

## Non-negotiable invariants

1. **Evaluator first.** Agent prompt보다 task schema, hidden evaluator, Docker boundary를 먼저 구현한다.
2. **Public/private separation.** Private spec, hidden test, reference patch는 agent workspace·prompt·tool output에 노출하지 않는다.
3. **External run state.** Event, checkpoint, evaluator data를 대상 repository 안에 기록하거나 최종 patch에 포함하지 않는다.
4. **Constrained execution.** Agent는 task에 등록된 check만 실행한다. unrestricted shell을 agent tool로 제공하지 않는다.
5. **Append-only evidence.** 관찰된 과거 event를 수정하지 않는다. 정정은 새 event 또는 파생 artifact로 남긴다.
6. **Idempotent recovery.** Patch와 재개 가능한 tool action은 stable identity/hash를 가져야 하며, 복구 시 중복 실행을 감지한다.
7. **Deterministic primary grading.** 테스트·diff·dependency·API·safety처럼 코드로 판정 가능한 항목은 LLM 점수로 대체하지 않는다.
8. **Fair comparison.** Memory 실험에서는 model snapshot, prompt, tools, task, commit, image, budget, retry와 evaluator를 고정한다.
9. **No held-out tuning.** Held-out 실행 전에 split, threshold, scoring weight, memory index를 동결한다.
10. **No solution leakage.** Failure memory에 reference patch, 정답 코드 조각, hidden assertion을 저장하지 않는다.
11. **No invented results.** 실행 artifact가 없는 수치나 개선 주장을 README·리포트·이력서 문구에 쓰지 않는다.
12. **CLI-first scope.** Phase 6의 실험 결과가 나오기 전에는 dashboard나 전체 GitHub App을 우선하지 않는다.

## Implementation workflow

1. `docs/05-implementation-plan.md`에서 현재 phase의 가장 앞선 미완료 work item 하나를 선택한다.
2. 해당 item의 입력, 출력, failure mode, acceptance test를 확인한다.
3. 외부에 보이는 schema나 의미를 바꾸면 같은 change에서 계약 문서를 갱신한다.
4. 최소 단위 test부터 실행하고, 관련 통합 test를 실행한다.
5. diff에서 private data 노출, 대상 repo 내부 state, scope 확장을 확인한다.
6. 실제로 통과한 명령과 남은 검증을 handoff에 기록한다.

요구사항이 불명확할 때는 범위를 넓히지 않는다. [열린 질문](docs/06-decisions.md#open-questions)에서 이미 정한 임시 기본값이 있으면 그것을 사용하고, 의미 있는 계약 변경이 필요하면 결정을 기록한다.

## Definition of done

변경은 다음을 모두 만족해야 완료다.

- 지정된 work item의 acceptance criteria를 충족한다.
- 성공 경로와 대표 failure path가 test로 검증된다.
- public/private boundary를 깨지 않는다.
- 실행 결과가 stable ID, timestamp, hash 등 필요한 provenance를 남긴다.
- 실패를 삼키지 않고 구조화된 오류 또는 event로 남긴다.
- 관련 문서와 예제가 실제 동작과 일치한다.
- 재현에 필요한 명령과 환경 가정이 기록된다.

## Planned engineering defaults

확정 전까지 다음 기본값을 따른다.

- Python 3.12+, Typer, Pydantic v2, pytest, Ruff
- 명시적 domain model과 작은 adapter; 복잡한 agent framework는 사용하지 않음
- SQLite와 local filesystem으로 시작하고 저장소 인터페이스 뒤에 둠
- UTC timestamp, SHA-256 content hash, monotonic per-run sequence
- JSON/JSONL은 machine artifact, YAML은 사람이 작성하는 task/config에 사용
- 테스트는 network와 live model credential 없이 실행 가능해야 함

정확한 dependency와 명령은 `pyproject.toml`과 자동화가 생기면 그 파일을 기준으로 갱신한다.

## Expected repository boundaries

```text
patchloop/agent/       orchestration and phase policy
patchloop/tools/       constrained tool implementations
patchloop/sandbox/     process/container isolation
patchloop/state/       events, checkpoints, recovery
patchloop/verifier/    deterministic graders
patchloop/failures/    taxonomy and classification
patchloop/memory/      memory schema and retrieval
patchloop/evals/       experiment runner and metrics
tasks/                 audited public/private task fixtures
experiments/           immutable configs and generated results
docs/                  normative design documents
```

Generated run state와 evaluation artifact는 source tree의 tracked files와 섞지 않는다.
