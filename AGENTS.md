# PatchLoop Agent Guide

이 파일은 repository 전체에 적용된다. PatchLoop에서 작업하는 coding agent는 구현 전에 이 문서와 현재 milestone 문서를 읽어야 한다.

## Mission

재현 가능한 평가 기반 위에서 single coding agent를 실행하고, trace-driven failure memory와 recovery 정책의 효과를 공정하게 비교한다.

Repo Maintainer와 Draft PR은 데모다. 평가 harness와 실제 실험 결과가 제품의 핵심이다.

## Current state

- Evaluator, constrained offline agent, state/recovery, memory, experiment/report와 viewer의
  implementation baseline이 존재한다.
- 현재 milestone은 `D-037 r4 clean commit and preflight`이다.
  Rejected-patch retry context와 execution-hash-bound `experiment-diagnostic-v1` consumer는
  offline evidence를 통과했다. 승인된 mini D-037 r3는 provider에서 실행됐지만 rejected mutation이
  생기기 전에 per-call output allowance를 소진해 실제 retry는 아직 검증하지 못했다.
  Terminal r3 evidence와 원인은 보존됐다. 새 r4는 official reasoning guidance에 맞춘
  25,000 per-call / 120,000 total token pair를 hash-bound profile v2로 분리했고 full
  offline 검증을 통과했다. Clean execution hash와 별도 비용 승인을 받기 전에는 후속 mini diagnostic,
  tool-v2/context-v3 Terra pilot 또는 memory-development campaign을 실행하지 않는다.
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
  0개이므로 이 run은 D-037을 검증하거나 반증하지 않으며 재실행하지 않는다.
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
