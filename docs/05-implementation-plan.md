# Implementation Plan

상태: **Implementation baseline active**  
현재 milestone: **Memory-development no-memory campaign preflight and collection**

2026-07-28 구현 스냅샷:

| 영역 | 상태 | 현재 evidence |
| --- | --- | --- |
| Phase 1 evaluator | done (local + Docker) | Reference 통과, 6종 bad patch 거부, `official=true` |
| Phase 2 agent | done (offline + Docker evaluator) | 3 task × mock/replay 6개 공식 run, 전체 trace와 valid patch 생성 |
| Phase 3 state machine | done | Transition guard와 turn별 context 재구성 |
| Phase 4 recovery | done (offline) | Kill-after-patch resume, duplicate mutation 0 |
| Phase 5 memory | qualification/review path implemented, live trace/index pending | Memory-development 6/6, development-validation 2/2 |
| Phase 6 evaluation | accepted pilot complete, development campaign pending | r3가 official SCRR와 trace qualification을 통과; 세 pilot 누적 비용 $0.828864375 |
| Phase 7 viewer/GitHub | viewer implemented, external GitHub gate pending | Route test 통과, 실제 Draft PR 미실행 |

Calibration fixture gate는 5/5로 완료됐다. 세 smoke task와
`duration-minute-boundary`, `csv-final-record-flush`는 evaluator, sandbox와 authoring workflow를
검증하는 fixture다. 뒤의 두 package가 물리적으로 `dev-train` 아래에 있어도 memory source나
research task로 보지 않는다. 현재 admitted research task는 20/20이며 memory-development
task admission은 6/6, development-validation은 2/2, core-same-repo와 core-cross-repo는
각각 6/6과 6/6이다. Dataset manifest에는 calibration 5개와 admitted research 20개,
총 25개 package가 등록돼 있다. FuseSoC #776, AnyIO #1134와 pyfakefs #1269가 public
contract 구조만으로 stress sentinel에 선정됐고 30-run schedule과 함께 machine audit를
통과했다. Dataset은 `frozen`이며 `research_ready=true`, `stress_ready=true`,
`complete=true`다.

`done`은 해당 코드 경로와 executable evidence를 뜻한다. Docker evaluator와 offline agent
smoke, 스무 research admission과 dataset freeze는 2026-07-28까지 통과했다. 동결된
stress schedule은 아직 실행되지 않았고, Live OpenAI와 96-run core campaign도 완료가
아니며 `docs/08-limitations.md`에서 별도로 추적한다.

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

## Current dataset gate — completed

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

2026-07-28 현재 1~6번은 executable admission과 machine-audit evidence로 완료됐다.
7번 external acceptance lane은 frozen core dataset과 분리된 후속 작업이다. 다음 단계는
Babel development-validation live pilot preflight를 acceptance한 뒤 여섯 memory-development
task의 no-memory development trace를 qualification하는 것이다.

동결 evidence:

- Manifest:
  `sha256:cf608ca1a35cb270f2e4cadcf0b34912256ef1c9cd3c0757a89692f8a5fdf786`
- Stress schedule:
  `sha256:d5a3d90f8429f24b6940d4a5cb1b78a35fa34d3fe3df9937ad6c57daba23f468`
- Sentinel: `fusesoc-retained-parse-error-diagnostics`,
  `anyio-extensionless-entrypoint-worker-main`,
  `pyfakefs-file-wrapper-io-capabilities`
- Schedule: 세 task 모두 context reset과 worker restart를 persistent state on/off로 2회씩,
  synthetic test timeout을 persistent state on으로 2회씩 실행하는 총 30개 derived run.
  Fault-free baseline은 core no-memory run이며 stress 결과는 core aggregate에 포함하지 않는다.

### Exit gate — passed

- Calibration은 정확히 5개이며 memory/core/headline에서 거부된다.
- Research role은 정확히 20개이고 easy task가 없으며 현재보다 낮은 품질 기준으로 수를 채우지
  않는다.
- 모든 research task가 immutable source provenance, base visible pass/private hidden fail,
  official reference 3회 pass와 세 개 이상 bad-patch rejection evidence를 가진다.
- Same-repo repository coverage와 cross-repo disjointness, solution-lineage uniqueness가
  machine audit를 통과한다.
- 세 sentinel과 fault schedule이 freeze되고 `include_in_core_metrics=false`다.

## Current live trace gate — pilot passed, development campaign pending

목표: 첫 paid call 전에 실행 계약과 비용 경계를 machine-check하고, 단일 pilot의 완전한
trace를 증명한 뒤에만 12-run development campaign을 연다.

### Frozen sequence

| Order | Status | Work item | Acceptance evidence |
| ---: | --- | --- | --- |
| 1 | implemented, live contract exercised | `experiment-v2` explicit purpose와 exact suite shape | Wrong task/role/repetition/model/budget contract reject |
| 2 | implemented, r3 host accepted; clean-machine reproduction pending | Canonical task/private hash/digest environment preflight, durable approved plan과 live capability | Unapproved/hash mismatch/dirty Git/wrong package/private/image/stale price reject |
| 3 | implemented, interrupted-run recovery pending | Paid call 전 fsync하는 hash-chained campaign journal | Existing journal이 hard-crash 뒤 새 schedule 시작을 차단; 자동 resume은 미구현 |
| 4 | implemented, three live artifacts observed | Source-evidence-bound `trace-qualification-v1`과 sanitized failure linkage | r2의 trace qualification과 r3의 accepted qualification이 원시 evidence에 결속됨 |
| 5 | passed on r3 | Babel #1042 `no_memory` 1회 pilot, $2 cap | `run_3cb86f8d70094a11`, `evaluation_reached=true`, official SCRR pass |
| 6 | pending new preflight and approval | Memory-development 6 task × 2회, `no_memory`, $20 cap | 12 terminal rows 또는 structured halt/not-started ledger |
| 7 | pending eligible failures | Append-only failure review와 memory build | Reviewed qualified failure만 index source로 수용 |

Live suite는 `gpt-5.6-terra`, reasoning `medium`, mode `standard`, service tier `default`,
4,096 max output token과 기본 run budget을 고정한다. Dataset hash는
`sha256:cf608ca1a35cb270f2e4cadcf0b34912256ef1c9cd3c0757a89692f8a5fdf786`다.

Preflight는 frozen dataset role/hash, manifest의 canonical task path, public/private hash와
base commit, task별 digest-pinned environment/observed Docker image, clean Git commit, SDK와
API key 존재 여부, custom base URL 부재, 72시간 price age, official rate와 budget reserve를
검사한다. Checked-in config는 승인 권한을 갖지 않는다. `--approve-live-cost`와 preflight가
출력한 exact `--approved-execution-hash`를 실제 실행 invocation에 다시 제공해야 한다.
Paid runner는 승인된 execution plan을 durable하게 저장한 뒤에만 capability를 받는다.
Campaign과 row start journal event는 model call 전에 append, flush, fsync되므로 hard crash 뒤
같은 experiment를 자동으로 다시 시작하지 않는다. 중단된 journal의 자동 resume은 후속
work item이다.

Qualification은 필수 event의 content-addressed artifact reference와 usage/cache 불변식을
검사하고, plan/manifest/events/checkpoints/result/artifact inventory를
`source_evidence_hash`로 결속한다. Development campaign preflight, human review와 index
build는 현재 source hash를 다시 검증한다.

2026-07-28 공식 rate는 1M token당 input $2.50, cached input $0.25, cache write $3.125,
output $15다. 현재 dated Terra snapshot은 제공되지 않아 alias와 SDK/Git/time provenance를
남긴다.

### Pilot gate — passed; development gate — not run

- 관련 unit/integration test와 Ruff가 통과한다.
- Approval 없는 `--preflight-only`가 API call 없이 execution hash와 blocker를 출력한다.
- 실제 환경에서 approval을 포함한 preflight가 `ready=true`다.
- 사용자가 $2 pilot을 별도로 승인한 뒤 한 run이 `trace-qualification-v1`과
  `evaluation_reached=true` pilot acceptance를 함께 통과한다.
- Accepted pilot run ID `run_3cb86f8d70094a11`을 development suite에 고정했다. Preflight는
  qualification hash와 현재 `source_evidence_hash`를 artifact에서 다시 읽어 새 execution
  hash에 결속한다.
- 12-run campaign은 새 clean commit의 no-call preflight, exact execution hash 검토와 별도
  $20 승인 전에는 시작하지 않는다.
- Hard-crash journal을 안전하게 inspect/resume하는 절차는 아직 exit gate를 통과하지 않았다.

2026-07-28 첫 paid pilot `run_c6f13dd9a1a1472d`는 ready preflight 뒤 `$0.34025875`를
사용했다. 20 model call과 22 tool call 동안 agent가 `*** Begin Patch` envelope를 반복해
mutation 8회가 거부됐고, input 73,730 + output 7,326 token으로 80,000-token budget을
넘겨 submission 전에 종료됐다. Evaluator는 실행되지 않았고 qualification은 false다.
Agent failure와 별개로 qualification의 유일한 failed check는 leak scanner였다. 41 match는
API key가 아니라 공개 contract의 `.patchloop-hidden` marker
20건과 public task ID에 포함된 hidden-check 문자열 21건이었다. 기존 trace와 qualification은
수정하지 않으며, failed-tool feedback과 patch-format 안내 및 공개 marker filtering을
고친 새 commit/hash에서 별도 승인된 pilot로 exit gate를 다시 평가한다. 첫 model
candidate를 내용 변경 없이 raw Git diff로 변환한 사후 진단 patch
`sha256:4c49b6edd0603f2e56c04c18e83fdecb3a6a5868ab40bffca198504951b01606`는
official evaluator run `run_4299e6b326de4c1c`에서 모든 verdict를 통과했다. 이 run은
format-only counterfactual evidence이며 agent success나 pilot repetition으로 집계하지
않는다. 12-run development result는 아직 없다.

두 번째 paid pilot `run_de8f2a2846044c01`은 별도 승인 hash
`sha256:c7fe89287ed3310885f548954917c810b699a54ea420b3a7551d9863ebd839a3`로
정확히 한 번 실행됐고 `$0.328036875`를 사용했다. 19 model call과 22 tool call,
111 event와 23 checkpoint가 보존됐으며 leakage match는 0이다. Trace qualification
artifact 자체는 `qualified=true`지만 `evaluation_reached=false`이므로 pilot acceptance는
실패한다. Agent가 낸 아홉 patch candidate(고유 7개)는 모두 hunk header에 old/new 7줄을
선언하고 실제 body는 6줄만 포함했다. 실행된 여덟 mutation은 `corrupt patch`로 거부됐고
evaluator는 실행되지 않았다. 선택한 원문 patch
`sha256:f041469f1d938452c6e25c54aa1e6b816247be0525920184a77be493f7111695`는
strict `git apply --check`에서 실패하고 `--recount` check에서 workspace 변경 없이
통과한다. 이 parser diagnostic도 agent success나 repetition으로 집계하지 않는다.

r3 corrective gate는 agent-visible forward와 policy rollback에만 hunk recount를
적용했다. Raw input hash는 유지하고 body/context/path/policy는 strict하게 검사한다.
Policy reject 뒤 pre-call diff hash 복원, duplicate `PatchApplied` 방지와 zero-untracked
checkpoint/recovery를 executable test로 고정했다. Hidden evaluator는 strict하게 유지했다.

세 번째 paid pilot은 clean harness commit
`eeeeba6aa68e9d58677e2d8218381f79285f5545`와 별도 승인 execution hash
`sha256:03c57fb3dd0182e63645e346311ee2a46c1284d9770857240b2011b666b8bde6`로
정확히 한 번 실행됐다. `run_3cb86f8d70094a11`은 11 model call, 13 tool call,
43,963 input token과 1,547 output token에 `$0.16056875`를 사용했다. Recount gateway로
한 번의 `PatchApplied`를 만든 뒤 `babel/numbers.py` 한 줄만 바꾼 submitted patch를
제출했다. Official evaluator의 hidden, regression, scope와 safety가 모두 pass했고
`scope_compliant_success=true`, `outcome_kind=resolved`다. Qualification은 72개 연속 event,
15개 checkpoint, leakage 0, reconciled usage와 `evaluation_reached=true`를 검증했으며
qualification hash는
`sha256:5bc11b4087061921a415d94caeb0ac8370e39013f1d94a531130256fd3101811`,
현재 source evidence hash는
`sha256:f4726a1d6c2abfdf859c92135ae345dffb2075aaa9d5a7f0fc4fb7b1b0259322`다.
이 evidence로 pilot gate는 통과했지만 12-run development campaign은 아직 실행하지 않았다.

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
- Matrix가 불완전하거나 qualification-failed이면 `analysis_ready=false` diagnostic만 만들고
  headline, paired CI와 flip 결과를 억제한다.
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
