# Implementation Plan

상태: **Implementation baseline active**  
현재 milestone: **Dataset expansion and external acceptance gates**

2026-07-24 구현 스냅샷:

| 영역 | 상태 | 현재 evidence |
| --- | --- | --- |
| Phase 1 evaluator | done (local + Docker) | Reference 통과, 6종 bad patch 거부, `official=true` |
| Phase 2 agent | done (offline + Docker evaluator) | 3 task × mock/replay 6개 공식 run, 전체 trace와 valid patch 생성 |
| Phase 3 state machine | done | Transition guard와 turn별 context 재구성 |
| Phase 4 recovery | done (offline) | Kill-after-patch resume, duplicate mutation 0 |
| Phase 5 memory | implemented, data gate pending | Admitted memory-development task 3/6 |
| Phase 6 evaluation | implemented, core campaign pending | Seeded smoke와 task bootstrap report 실행 |
| Phase 7 viewer/GitHub | viewer implemented, external GitHub gate pending | Route test 통과, 실제 Draft PR 미실행 |

Calibration fixture gate는 5/5로 완료됐다. 세 smoke task와
`duration-minute-boundary`, `csv-final-record-flush`는 evaluator, sandbox와 authoring workflow를
검증하는 fixture다. 뒤의 두 package가 물리적으로 `dev-train` 아래에 있어도 memory source나
research task로 보지 않는다. 현재 admitted research task는 3/20이다.

`done`은 해당 코드 경로와 executable evidence를 뜻한다. Docker evaluator와 offline agent
smoke와 세 research admission은 2026-07-27까지 통과했다. Live OpenAI, 완성된 20개 research dataset, 세 sentinel stress
overlay와 96-run core campaign은 아직 완료가 아니며 `docs/08-limitations.md`에서 별도로
추적한다.

## 1. Sequencing rule

다음 phase는 현재 phase의 exit gate가 executable evidence로 통과한 뒤 시작한다. UI와 GitHub 연동은 Phase 6의 core experiment가 재현된 뒤에만 시작한다.

```text
Evaluation foundation
  → Minimal agent
  → Structured state machine
  → Persistence and recovery
  → Failure memory
  → Core evaluation
  → Viewer and GitHub demo
```

## Current dataset gate

목표: Calibration과 research evidence를 분리하고, benchmark/upstream provenance가 있는 20개
research task를 admission한다.

### Ordered work items

1. Dataset manifest에 5개 calibration fixture를 등록하고 headline exclusion을 검증한다.
2. SWE 계열 benchmark instance와 실제 upstream issue/PR에서 Python coding 후보를 수집한다.
3. 각 후보를 constrained tool, registered check, submitted patch와 separate hidden evaluator
   계약으로 변환한다.
4. Base/no-op로 visible pass와 hidden fail을 확인하고, reference를 pinned Docker image에서 3회
   실행하며 세 개 이상의 representative bad patch를 거부한 evidence hash를 등록한다.
5. Memory-development 6, development-validation 2, same-repo core 6, cross-repo core 6을 채운다.
6. Admitted research task 중 Terminal-Bench 2.1 pattern을 적용할 sentinel 세 개를 동결한다.
7. 원본 benchmark 호환성 run은 external acceptance lane에 남기고 core aggregate와 분리한다.

### Exit gate

- Calibration은 정확히 5개이며 memory/core/headline에서 거부된다.
- Research role은 정확히 20개이고 easy task가 없으며 현재보다 낮은 품질 기준으로 수를 채우지
  않는다.
- 모든 research task가 immutable source provenance, base visible pass/private hidden fail,
  official reference 3회 pass와 세 개 이상 bad-patch rejection evidence를 가진다.
- Same-repo repository coverage와 cross-repo disjointness, solution-lineage uniqueness가
  machine audit를 통과한다.
- 세 sentinel과 fault schedule이 freeze되고 `include_in_core_metrics=false`다.

## Phase 1. Evaluation Foundation

목표: Agent 없이도 submitted patch를 공정하게 판정하는 evaluator를 만든다.

### Ordered work items

| ID | Status | Work item | Depends on | Acceptance evidence |
| --- | --- | --- | --- | --- |
| P1.1 | done | Python package/CLI/test scaffold | 없음 | Offline unit test와 lint command 실행 |
| P1.2 | done | Public/private task Pydantic schema와 loader | P1.1 | Valid fixture load, path traversal reject |
| P1.3 | done | Audited sample Python repository와 patch fixtures | P1.2 | Reference와 6종 bad patch 보유 |
| P1.4 | done | Immutable checkout/workspace manager | P1.2 | Snapshot에서 매 run clean Git workspace 생성 |
| P1.5 | done | Docker sandbox policy와 registered check runner | P1.3, P1.4 | network 차단, non-root, read-only mount, host secret 비전달 검사 통과 |
| P1.6 | done | Hidden/visible test runner 분리 | P1.5 | Hidden asset는 evaluator workspace에 제출 후 복사 |
| P1.7 | done | Scope/dependency/tampering verifier | P1.3 | Known-bad patch별 expected boundary 거부 |
| P1.8 | done | Run manifest, verifier result, artifact writer | P1.2 | Schema-valid JSON과 SHA-256 object 저장 |
| P1.9 | done (local + Docker) | `patchloop eval-task` end-to-end | P1.6~P1.8 | Reference 성공, bad fixture 전체 실패, Docker 결과 `official=true` |

### Exit gate

```bash
patchloop eval-task tasks/dev/task_001
```

- Reference patch는 SCRR 구성 verdict가 모두 pass다.
- No-op, regression, forbidden path, dependency, tampering fixture는 의도한 verifier에서 fail한다.
- 두 번 실행해 verdict가 동일하고, manifest가 허용된 변동(timestamp/run ID)을 제외하면 재현 가능하다.
- Hidden content가 agent-visible workspace와 output에 없다.

## Phase 2. Minimal Coding Agent

목표: 제한된 tool로 간단한 task를 제출하고 완전한 trace를 남긴다.

### Work items

- Provider-neutral model adapter와 deterministic mock/replay adapter
- `list_tree`, `search_repo`, `read_file`, `apply_patch`, `run_check`, `inspect_diff`
- Tool schema/policy gateway와 action identity
- Basic ReAct loop와 stop/budget policy
- Model/tool event logging과 usage accounting
- Agent submission을 Phase 1 evaluator로 전달하는 end-to-end path

### Exit gate

- Mock/replay agent로 offline smoke run이 가능하다.
- 간단한 task에서 valid patch를 제출한다.
- 모든 model/tool call과 failure가 ordered event로 저장된다.
- Budget 초과와 invalid tool argument가 구조화된 failure로 종료된다.

## Phase 3. Structured State Machine

목표: 실행을 evidence-gated phase로 만든다.

### Work items

- `INTAKE → REPRODUCE → PLAN → IMPLEMENT → VERIFY → REVIEW → DONE`
- 허용된 backward transition과 invalid transition guard
- Phase별 required artifact schema
- Context builder와 remaining-budget section
- `write_checkpoint`, `finish_task` orchestrator action

### Exit gate

- Evidence 없이 phase를 건너뛸 수 없다.
- `VERIFY` 실패 후 `IMPLEMENT`로 돌아갈 수 있다.
- `DONE`과 evaluator outcome이 명확히 분리된다.
- 모든 phase artifact가 contract를 만족한다.

## Phase 4. Persistence and Recovery

목표: Context 또는 worker가 사라져도 중복 mutation 없이 작업을 재개한다.

### Work items

- Append-only event store와 monotonic sequence
- Durable checkpoint와 artifact store
- Stable action ID/input hash, patch idempotency
- Recovery reconciliation과 worker resume
- Context-reset, worker-restart fault injector
- Duplicate/repeated-work metrics

### Exit gate

- `PatchApplied` 직후 worker를 종료해도 동일 run ID로 재개한다.
- Patch와 완료 action을 중복 적용하지 않는다.
- Corrupt checkpoint/hash mismatch는 안전하게 fail한다.
- 정상/장애 run 모두 evaluator 결과까지 연결된다.

## Phase 5. Failure Taxonomy and Memory

목표: Development trace를 solution이 아닌 일반화 가능한 remediation rule로 변환한다.

### Work items

- Cause/symptom/evidence 기반 failure schema
- Timeout, forbidden path, repeated action 등의 deterministic classifier
- Human review queue와 audit state
- Versioned structured memory store
- Raw trace renderer와 structured renderer
- Metadata filter, semantic retrieval, rerank, threshold, token budget
- Memory index build/freeze command

### Exit gate

- Admitted `memory-development` task의 failure에서 reviewed memory entry를 생성한다.
- Calibration과 external acceptance trace는 memory source에서 거부한다.
- Reference patch·hidden test·정답 code가 memory에 포함되지 않는다.
- 관련 memory가 없을 때 empty retrieval을 반환한다.
- Frozen index의 content hash가 held-out run manifest에 기록된다.

## Phase 6. Core Evaluation

목표: 네 memory 조건을 고정된 harness와 예산에서 비교한다.

### Work items

- Experiment config와 condition matrix runner
- Seeded execution order와 repetition
- Same-repo/cross-repo split audit
- Calibration/external/stress headline exclusion audit
- SCRR, 비용, recovery, memory metric
- Paired comparison과 bootstrap confidence interval
- Task-level JSON/CSV와 analysis report
- Success/failure flip trace selection

### Exit gate

- No Memory, Raw Trace, Structured, Selective Structured를 같은 task/budget으로 실행한다.
- 12개 core held-out task를 condition당 두 번 실행해 96개 core run을 만든다.
- 세 sentinel stress 결과를 core aggregate와 분리한다.
- Raw result에서 report를 다시 생성할 수 있다.
- Task-level matrix와 confidence interval이 생성된다.
- 모든 headline 수치가 raw row와 run artifact로 추적된다.
- Negative 또는 inconclusive 결과도 변경 없이 보고한다.

## Phase 7. Viewer and GitHub Demo

목표: 핵심 evidence를 빠르게 검토할 수 있게 하고 portfolio demo를 완성한다.

### Minimal viewer

- Run list와 task/condition/status/cost
- Run timeline과 model/tool detail
- Patch diff와 checkpoint history
- Verifier result와 failure classification
- Retrieved memory와 no-match decision
- Condition comparison과 task heatmap

### GitHub demo

- Issue import
- Audited result를 바탕으로 Draft PR 생성
- PR body에 patch, verifier summary, run/report provenance 연결

### Exit gate

- 대표 성공과 실패 run을 source event까지 추적할 수 있다.
- Viewer가 private test content와 secret을 노출하지 않는다.
- README의 demo 명령이 clean setup에서 재현된다.

## 2. Cross-phase definition of done

각 work item은 다음을 포함한다.

- Domain contract와 validation error
- Happy path unit test
- 대표 policy/error path test
- 필요한 integration test 또는 fixture
- Offline/mock 실행 경로
- Provenance/event/artifact evidence
- 관련 docs와 CLI help 갱신

테스트 통과만으로 완료하지 않는다. Boundary, reproducibility, failure observability도 acceptance에 포함한다.

## 3. Planned repository shape

필요해질 때만 디렉터리를 만든다. 빈 scaffolding을 한 번에 생성하지 않는다.

```text
patchloop/
├── agent/
├── models/
├── tools/
├── sandbox/
├── state/
├── verifier/
├── failures/
├── memory/
├── evals/
└── api/                  # Phase 7
tasks/
├── smoke/
├── dev/
├── heldout/
└── stress/
tests/
├── unit/
├── integration/
└── recovery/
experiments/
├── configs/
└── results/              # generated, retention policy 필요
ui/                       # Phase 7
```

## 4. Handoff template

Agent가 work item을 넘길 때 다음을 기록한다.

```text
Work item:
Implemented:
Contracts changed:
Commands run and results:
Artifacts/evidence:
Known limitations:
Next unblocked item:
```
