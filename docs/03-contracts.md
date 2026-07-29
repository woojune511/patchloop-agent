# Data and Tool Contracts

상태: **Normative draft**

이 문서는 구현 언어와 storage backend보다 우선하는 논리 계약을 정의한다. 예시는 설명용이며 Phase 1에서 Pydantic/JSON Schema로 구체화한다.

## 1. Cross-cutting rules

- 모든 ID는 type prefix를 가진 opaque string이다: `task_`, `run_`, `evt_`, `art_`, `mem_`.
- Timestamp는 UTC RFC 3339 형식이다.
- Content identity는 `sha256:<hex>` 형식이다.
- Schema는 explicit `schema_version`을 가진다.
- Unknown field 처리 정책은 schema별로 명시하고, 보안·평가 관련 입력은 기본적으로 reject한다.
- Public document는 private locator의 opaque ID를 가질 수 있지만 private content를 포함하지 않는다.
- Result는 summary뿐 아니라 원시 artifact locator와 provenance를 가진다.

## 2. Task package

권장 layout:

```text
tasks/{split}/{task_id}/
├── public.yaml
├── private.yaml          # agent에 mount하지 않음
├── environment.yaml      # optional digest-pinned evaluator image
├── hidden/               # agent에 mount하지 않음
├── reference.patch       # agent와 memory builder에 노출하지 않음
└── audit.md              # evaluator/editor 전용
```

### Public task spec

```yaml
schema_version: task-public-v1
task_id: parser-quoted-newline-001
task_version: 1

repository:
  url: local://sample-parser
  base_commit: a13f8d2
  language: python

issue:
  title: CSV parser fails on quoted multiline fields
  description: |
    Quoted fields containing newline characters are parsed as separate records.

constraints:
  allowed_paths: ["src/**", "tests/**"]
  forbidden_paths: ["pyproject.toml", ".github/**"]
  max_changed_files: 4
  max_diff_lines: 120
  dependency_changes_allowed: false
  public_api_changes_allowed: false

visible_checks:
  - id: existing_unit_tests
  - id: lint
  - id: typecheck
```

### Private evaluator spec

```yaml
schema_version: task-private-v2
task_id: parser-quoted-newline-001
task_version: 1

hidden_checks:
  - id: hidden_multiline_csv_tests
  - id: regression_suite

hidden_artifacts:
  - path: hidden/test_multiline_csv.py
    sha256: "sha256:..."

reference_patch:
  path: reference.patch
  sha256: "sha256:..."

audit:
  expected_files: ["src/parser.py"]
  prohibited_behaviors:
    - modifying existing assertions
    - bypassing quote handling
    - special-casing hidden test values
```

새 research task는 `task-private-v2`를 사용한다. V2는 `hidden/` 아래의 모든 evaluator
artifact를 `hidden_artifacts`에 빠짐없이 선언하고 SHA-256을 고정한다. Loader는 선언된
inventory와 실제 파일 집합이 정확히 같은지, 각 content hash가 일치하는지 검사한다.
따라서 run manifest의 `private_spec_hash`는 hidden assertion 본문을 노출하지 않으면서도
그 content identity를 간접적으로 고정한다. 기존 admitted evidence 재해석을 피하기 위해
`task-private-v1`은 읽기 호환만 유지하며, 새 admission에는 사용하지 않는다.

`task_id + task_version + base_commit`은 평가 도중 immutable하다. Public/private의 ID와 version이 일치하지 않으면 실행을 거부한다.

Benchmark dependency environment가 필요한 package는 별도 `task-environment-v1` 파일로
`repository@sha256:<digest>` evaluator image와 observed image digest를 함께 고정한다. Mutable tag는
source provenance로만 남기고 실행에는 사용하지 않는다. Environment file은 solution이나 hidden
assertion을 포함하지 않으며, 실제 run manifest의 `evaluator_image_digest`가 선언 digest와 다르면
실행을 거부한다. Environment file이 없는 calibration fixture만 기본 PatchLoop image를 사용한다.

Allowlist에 등록된 remote repository의 `base_commit`은 소문자 40자리 hexadecimal SHA여야 한다.
Evaluator는 전체 repository 이력을 clone하지 않고 그 exact SHA만 `--depth 1`로 fetch한 뒤
`FETCH_HEAD`를 detached checkout한다. Windows에서도 audited monorepo의 긴 경로를 보존하도록
checkout repository에 `core.longpaths=true`를 설정한다. 최종 `HEAD`가 선언 SHA와 정확히
일치하지 않거나 exact-SHA fetch가 실패하면 task 실행을 거부한다.

### Dataset registry and eligibility

Task package가 evaluator를 통과했다는 사실만으로 memory 또는 core experiment에 사용할 수 있는 것은
아니다. `data/dataset-manifest.yaml`이 task의 연구 역할, source provenance, difficulty, solution
lineage와 admission evidence를 별도로 등록한다. Directory 이름이 아니라 manifest의 `role`이
eligibility를 결정한다.

초기 manifest의 역할과 목표는 다음과 같다.

| Role | Target | Eligibility |
| --- | ---: | --- |
| `calibration` | 5 | Harness와 evaluator 확인 전용; memory/core/headline에서 제외 |
| `memory-development` | 6 | Reviewed failure만 memory source로 사용 가능 |
| `development-validation` | 2 | Rendering, no-match, leak 검증 전용; memory source에서 제외 |
| `core-same-repo` | 6 | Frozen core experiment 전용 |
| `core-cross-repo` | 6 | Frozen core experiment 전용 |
| `external-acceptance` | 별도 | 호환성 evidence 전용; core aggregate에서 제외 |

따라서 research target은 calibration을 제외한 20개다. 현재 존재하는 세 smoke task와 역사적으로
`dev-train` 경로에 작성된 두 쉬운 task는 모두 `calibration` fixture다. 이 다섯 package의
reference/bad-patch evidence는 유효하지만 admitted research task 수에는 포함하지 않는다.

Research entry는 최소한 다음을 만족해야 한다.

- `benchmark-instance` 또는 `upstream-incident` source와 immutable upstream commit
- Benchmark revision/instance ID 또는 issue/PR URL, retrieval timestamp와 SPDX license
- Contamination risk, workflow type, environment image provenance
- Medium 이상으로 사전 판정된 difficulty와 고유 `solution_lineage_id`
- Base visible pass/private hidden fail, 동일 reference의 official Docker 3회 통과와 세 개 이상의
  representative bad-patch rejection을 가리키는 content-hashed admission evidence

Non-synthetic source의 repository, base commit, license와 benchmark identity는 빈 문자열을
허용하지 않는다. Dataset audit는 research entry의 `source.upstream_repository`를 public task의 canonical GitHub
`repository.url`과, `source.upstream_base_commit`을 public task의 `repository.base_commit`과
각각 결속한다. Manifest provenance만 바꿔 same-repo pairing이나 source identity를 가장하는
entry는 role count에 포함하지 않고 구조화된 audit error로 남긴다.

공개 benchmark의 instruction, solution과 verifier를 그대로 복사하는 것은 admission이 아니다.
Terminal-Bench 계열은 PatchLoop의 registered-check-only, patch-producing Python workflow와
분리 evaluator 경계로 변환해 독립적으로 재감사한다. 원본 benchmark 실행은
`external-acceptance` evidence로만 취급한다. 단순히 pattern만 재구성한
`benchmark-inspired` fixture는 출처를 기록할 수 있지만 그 사실만으로 research eligibility를
얻지 못한다.

Dataset manifest는 freeze 시 role별 목표를 정확히 채워야 하며 manifest content hash를 experiment
manifest에 기록한다. Calibration entry, research entry와 external acceptance 결과를 같은 headline
분모에 합치지 않는다.

`core-same-repo` lane이 목표 수를 채운 시점에는 memory-development repository 집합과 정확히
일치해야 하며, 두 lane 모두 repository당 한 task만 가져야 한다. 단순 부분집합 검사는 같은
repository의 held-out task를 중복해 다른 development repository를 누락하는 구성을 막지 못하므로
freeze 전 machine audit가 1:1 pairing을 별도로 검증한다.

### Stress lane

Stress는 새로운 core split이 아니라 admitted research task 중 사전 고정한 세 sentinel에 fault를
덧씌우는 overlay다. 초기 lane은 Terminal-Bench 2.1의 long-horizon/container failure pattern을
참고하되 다음 세 deterministic scenario만 사용한다.

```text
context-reset
worker-kill-after-patch
test-timeout
```

Frozen dataset은 정확히 하나의 stress lane을 가져야 한다. 그 lane은 admitted held-out task
세 개, 위 세 scenario, `selection_policy: public-contract-structure-v1`, task별 공개
selection rationale와 `stress-schedule-v1` schedule을 모두 가져야 한다.

```yaml
stress_lanes:
  - lane_id: terminal-recovery-v1
    benchmark_inspiration: terminal-bench-2.1
    sentinel_count: 3
    task_ids:
      - fusesoc-retained-parse-error-diagnostics
      - anyio-extensionless-entrypoint-worker-main
      - pyfakefs-file-wrapper-io-capabilities
    scenarios:
      - context-reset
      - worker-kill-after-patch
      - test-timeout
    selection_policy: public-contract-structure-v1
    selection_rationale:
      fusesoc-retained-parse-error-diagnostics: Public constraints allow the widest three-file production change surface; the task ID is the deterministic tie-break.
      anyio-extensionless-entrypoint-worker-main: Public constraints provide the narrowest remaining mutation surface at one file and forty diff lines.
      pyfakefs-file-wrapper-io-capabilities: Its 240-second registered visible check is the longest among the remaining held-out tasks.
    schedule:
      schema_version: stress-schedule-v1
      schedule_id: terminal-recovery-v1
      seed: 20260723
      memory_condition: no_memory
      task_scope: all-sentinels
      baseline_source: core-no-memory
      expected_derived_runs: 30
      cases:
        - fault: context-reset
          trigger: after-model-call-10
          persistent_state_modes: ["on", "off"]
          repetitions: 2
          arm_once: true
        - fault: worker-kill-after-patch
          trigger: after-first-durable-patch-checkpoint
          persistent_state_modes: ["on", "off"]
          repetitions: 2
          arm_once: true
        - fault: test-timeout
          trigger: first-registered-visible-check
          persistent_state_modes: ["on"]
          repetitions: 2
          arm_once: true
    include_in_core_metrics: false
```

`public-contract-structure-v1`은 private spec, hidden test, reference patch와 model outcome을 읽지
않는다. Held-out 12개 public contract에서 순서대로 다음 archetype을 고르고, 이미 선택한 task는
다음 단계에서 제외한다.

1. `max_changed_files`가 가장 큰 task. 동률이면 task ID 오름차순.
2. `max_changed_files`, `max_diff_lines`, task ID 순으로 가장 작은 task.
3. Registered visible check의 최대 timeout이 가장 긴 task. 동률이면 task ID 오름차순.

Schedule의 세 case는 모든 sentinel에 적용한다. Derived run 수는 sentinel별로
`(2 state mode × 2 repetition) + (2 × 2) + (1 × 2) = 10`, 전체 30개다. Fault-free baseline은
동일 task의 core `no_memory` run을 참조하며, stress 30개는 core 96개에 더하거나 core metric에
포함하지 않는다. Schedule hash는 schedule object의 canonical JSON SHA-256이고, dataset manifest
hash와 함께 audit output에 기록한다.

Stress lane은 `sentinel_count: 3`과 `include_in_core_metrics: false`를 고정한다. Fault-derived run은
원본 task identity와 manifest를 보존하면서 새 run ID를 사용하고, core memory 결과와 별도로
보고한다. Dataset `frozen`은 selection과 schedule 계약이 동결됐다는 뜻이다. Fault runtime,
persistent-state-off arm 또는 30개 stress run의 실행 완료를 뜻하지 않는다.

### Registered check

```yaml
id: unit_test_parser
command: ["python", "-m", "pytest", "tests/test_parser.py", "-q"]
timeout_seconds: 60
working_directory: "."
environment: {}
expected_exit_codes: [0]
output_limit_bytes: 200000
```

Command는 task editor가 등록한다. Agent가 executable, argument, environment를 덮어쓸 수 없다.

## 3. Experiment suite와 live preflight

`experiment-v2`는 모든 suite에 `purpose`를 명시한다. 기존 offline smoke와 core template의
`experiment-v1`은 읽기 호환만 유지하며 새 live 실행에는 사용하지 않는다.

| Purpose | Exact contract |
| --- | --- |
| `offline-smoke` | `model=mock`; API 호출 없음 |
| `development-validation-live-pilot` | Babel #1042 한 task, `no_memory`, repetition 1, $2 상한 |
| `development-validation-model-candidate-pilot` | Babel #1042 한 task, `no_memory`, repetition 1, dated candidate model, $2 상한; Terra 선행 gate와 분리 |
| `memory-development-no-memory` | frozen memory-development 여섯 task, `no_memory`, repetition 2, 총 12 run, $20 상한 |
| `core` | frozen held-out 12 task, memory 네 조건, repetition 2, 총 96 run |

Terra comparison purpose는 다음 값을 고정한다.

```yaml
model: openai
model_id: gpt-5.6-terra
reasoning_effort: medium
reasoning_mode: standard
service_tier: default
max_output_tokens: 4096
budget:
  max_model_calls: 20
  max_tool_calls: 50
  max_total_tokens: 80000
  wall_clock_timeout_seconds: 900
seed: 20260723
```

Pilot task는
`tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes/public.yaml`로 exact match한다.
Development campaign은 frozen registry의 memory-development 여섯 task가 정확히 한 번씩
suite에 선언돼야 한다. 다른 role, 일부 집합, 중복 task 또는 다른 repetition은 schema 또는
preflight에서 거부한다. Development campaign은 먼저 성공 여부와 무관하게 trace
qualification과 `evaluation_reached=true`를 함께 만족한 accepted pilot의 run ID와
qualification hash를 요구한다.

Paid approval은 checked-in YAML 상태가 아니다. `live_cost_approved`와
`approved_execution_hash`는 이전 schema를 읽기 위한 deprecated field이며 값을 바꿔도 실행
권한을 주지 않는다. 실행자는 먼저 `--preflight-only`가 반환한 exact `execution_hash`를
검토하고, 실제 paid invocation에 다음 두 값을 함께 제공해야 한다.

```text
--approve-live-cost
--approved-execution-hash sha256:<exact execution hash>
```

Execution hash는 approval field를 제외한 normalized suite, frozen dataset identity, task의
canonical package path/public spec/private spec/base commit, seeded schedule hash, clean Git
commit, digest-pinned environment와 observed Docker image identity, OpenAI SDK version과
선행 pilot qualification hash를 결속한다. Suite가 manifest의 canonical package가 아닌
복제 경로를 가리키거나 현재 private evaluator hash가 registry와 다르거나 digest-pinned
environment가 없으면 paid execution 전에 거부한다. Preflight는 매 invocation마다 다음도
다시 확인한다.

- Frozen dataset status와 manifest hash, task role/split
- Clean Git worktree와 commit identity
- 모든 evaluator image의 digest identity와 Docker server availability
- `OPENAI_API_KEY` 존재 여부만 확인하고 credential value는 출력·저장하지 않음
- `OPENAI_BASE_URL`, `OPENAI_API_BASE`가 설정되지 않았음
- Terra alias, medium reasoning, standard mode, default service tier와 SDK provenance
- 72시간 이내의 공식 price source/rate와 positive estimate
- 한 run의 frozen token/output budget을 모두 예약해도 campaign cost limit을 넘지 않음
- 동일 experiment result가 아직 존재하지 않음

2026-07-28의 공식 [API pricing](https://developers.openai.com/api/docs/pricing)은 1M token당
input $2.50, cached input $0.25, cache write $3.125, output $15다. 현재 model catalog에는
dated Terra snapshot 없이 `gpt-5.6-terra` alias만 있으므로 model ID와 SDK version, Git
commit, 실행 시점을 함께 남긴다. Price verification이 72시간을 넘으면 live 실행을
거부하고 다시 확인한다.

D-031 telemetry를 실제 provider에서 검증한 terminal r1은
`experiments/dev-validation-gpt54mini-pilot.yaml`에 보존한다. v2 corrective retry는
`experiments/dev-validation-gpt54mini-pilot-r2.yaml`에 별도 고정한다. D-037 r3는
`experiments/dev-validation-gpt54mini-d037-r3.yaml`에 보존한다. 세 suite는
`development-validation-model-candidate-pilot` purpose를 사용하며 기존
`development-validation-live-pilot` 선행 gate를 충족하지 않는다.
`gpt-5.4-mini-2026-03-17`, medium effort, default tier, `max_output_tokens: 4096`,
`max_total_tokens: 90000`을 허용한다. 공식 standard rate는 input $0.75/M, cached input
$0.075/M, output $4.50/M이고 cache-write rate는 `null`이다. 90,000은 run 전체
input+output 누적 상한이며 memory-development/core의 Terra 계약을 바꾸지 않는다.
Generation 전에 exact input count와 manifest의 full per-call output allowance가 남은
budget에 함께 들어가는지 검사하므로 마지막 response가 이 상한을 넘도록 시작하지 않는다.

새 D-037 provider diagnostic은
`experiments/dev-validation-gpt54mini-d037-r3.yaml`에 다음 execution-hash-bound 요구를
선언한다.

```yaml
diagnostic:
  schema_version: experiment-diagnostic-v1
  profile: d037-rejected-patch-retry-v1
  required_trace_features:
    - rejected_patch_retry_context
```

이 block은 `experiment-v2`의 `development-validation-model-candidate-pilot`에서만 허용되며
feature는 정확히 한 번 선언해야 한다. Normalized suite, execution hash와 durable approved
plan이 이 block을 포함하므로 승인 뒤 제거·변경하면 hash가 달라지고 실행 전에 거부된다.
Block이 없는 historical r1/r2 suite는 기존 normalized identity를 유지한다.

R3 `run_e90f7c52aa134182`는 rejected mutation 전에 per-call 4,096-token allowance를
reasoning에서 소진해 `incomplete/max_output_tokens`로 끝났다. 이 terminal suite/run은
재실행하지 않는다. Corrective r4는
`experiments/dev-validation-gpt54mini-d037-r4.yaml`과 다음 profile로 별도 versioning한다.

```yaml
max_output_tokens: 25000
budget:
  max_model_calls: 20
  max_tool_calls: 50
  max_total_tokens: 120000
  wall_clock_timeout_seconds: 900
diagnostic:
  schema_version: experiment-diagnostic-v1
  profile: d037-rejected-patch-retry-v2
  required_trace_features:
    - rejected_patch_retry_context
```

V2 profile은 위 output/total-budget pair를 모두 요구한다. 일부만 바꾸거나 v1 profile에
새 budget을 붙이면 suite validation에서 거부한다. Post-run qualification도 approved
plan의 complete canonical suite를 다시 parse/hash하고 profile, model, reasoning mode,
service tier, output allowance, budget과 pricing을 run manifest에 대조한다. 또한 raw
schedule hash를 다시 계산하고 suite/dataset/tasks/Git commit/Docker images/SDK/pilot
qualification hash로 execution hash를 재구성해 plan·approval·manifest의 값과 대조한다. 공식
[reasoning guide](https://developers.openai.com/api/docs/guides/reasoning#allocating-space-for-reasoning)의
초기 25,000-token reasoning/output 권고와
[현재 mini snapshot](https://developers.openai.com/api/docs/models/gpt-5.4-mini)의
128,000-token max output 안에 있다. 2026-07-29 suite rate와 conservative
preflight authorization reserve로 계산한 `$0.6525`는 기존 $2 approval cap 아래다.
이것은 predicted/measured spend나 tight billing upper bound가 아니며, historical mini
r1~r3와 Terra/core 계약을 바꾸지 않고 incomplete response 자동 retry도 추가하지 않는다.

일반 trace qualification은 rejection이 없으면 조건부 retry 계약을 통과할 수 있다. Diagnostic
consumer는 qualification의 patch/error body를 복사하지 않고 count와 failure sequence만 읽어
다음 predicate를 별도로 판정한다.

```text
evaluation_reached == true
AND retry_episode_count >= 1
AND verified_retry_count == retry_episode_count
AND failed_source_failure_sequences == []
```

`rejected_candidate_count`는 여러 rejection이 한 retry episode의 latest candidate로 수렴할 수
있어 gate의 분모로 사용하지 않는다. Evaluator에 도달했지만 episode가 0이면 generic
qualification이나 task outcome을 실패로 바꾸지 않고 `TraceExerciseInconclusive`로 기록한다.
Evaluator에 도달하지 못했거나 episode가 관찰됐지만 완전히 검증되지 않았거나 check evidence가
없거나 중복·malformed이면 `TraceExerciseFailed`다.
Run row는 `qualification`/`qualification_error`와 `diagnostic`/`diagnostic_error`를 분리해
보존한다.

`patchloop run --model openai`, OpenAI run의 direct `resume`, direct `inject-fault`는 승인된
suite 경로를 우회할 수 없도록 거부한다.

실행 단계는 suite 경로를 다시 읽지 않고 approved plan의 normalized suite snapshot을
재검증해 사용한다. 각 row에서는 task package identity를 plan의 canonical path/spec/base/image와
다시 대조하고, 생성한 `RunManifest`의 task/model/budget/sandbox/memory/experiment identity가
plan과 정확히 일치한 뒤에만 `RunStarted`를 기록한다.

Ready preflight는 paid runner를 만들기 전에
`.patchloop/experiments/plans/<execution-hash>.json`에
`experiment-execution-plan-v1`을 저장한다. Live execution capability는 이 plan이
`ready=true`, blocker 없음, invocation approval과 exact execution hash 일치를 다시
증명할 때만 발급된다. In-memory flag나 임의로 만든 manifest만으로 capability를 만들 수 없다.

Campaign은 별도의 `experiment-journal-event-v1` JSONL을 사용한다. 최초
`CampaignStarted`는 exclusive create로 journal ownership을 원자적으로 선점하고, 각 event는 monotonic
sequence, `previous_event_hash`와 자신의 content hash를 가지며 append 뒤 flush와 fsync한다.
`CampaignStarted`는 capability 발급과 첫 model call 전에, 각 `RunStarted`는 stable run ID와
함께 해당 row의 model call 전에 기록한다. `RunTerminal`, `RunNotStarted`,
`CampaignCompleted`도 같은 chain에 추가한다. 결과 JSON이 생성되기 전에 process가 종료돼도
기존 journal이나 동시 선점 경쟁의 패자가 새 schedule 시작을 차단한다. 이 계약은 중복 paid
call 방지 경계이며, 중단된 campaign의 자동 resume 계약은 아직 제공하지 않는다.
`CampaignCompleted.payload.result_hash`는 persisted experiment result의 정확한 UTF-8
bytes를 SHA-256한 값이다. 플랫폼 newline 변환으로 journal hash와 실제 파일 bytes가
달라지지 않도록 runner는 hash한 bytes를 그대로 기록한다.

## 4. Run manifest

```yaml
schema_version: run-manifest-v1
run_id: run_0041

task:
  id: parser-quoted-newline-001
  version: 1
  base_commit: a13f8d2
  public_spec_hash: "sha256:..."
  private_spec_hash: "sha256:..."

harness:
  git_commit: b214aa9
  system_prompt_hash: "sha256:..."
  tool_schema_version: v1
  context_policy_version: v1
  memory_policy_version: selective-v1

model:
  provider: configured-provider
  model_id: fixed-model-id
  replay_hash: null
  temperature: 0
  max_output_tokens: 4096

budget:
  max_model_calls: 20
  max_tool_calls: 50
  max_total_tokens: 80000
  wall_clock_timeout_seconds: 900

environment:
  agent_image_digest: "sha256:..."
  evaluator_image_digest: "sha256:..."
  network_enabled: false
  cpu_limit: 2
  memory_limit: 2g

fault:
  type: none
  schedule: null

memory:
  condition: selective_structured
  index_version: memory-dev-v3
  index_hash: "sha256:..."
  max_context_tokens: 2000

created_at: "2026-07-23T10:00:00Z"
```

Manifest는 run 시작 전에 finalize하며 이후 수정하지 않는다. 계산된 실제 usage/outcome은 result에 기록한다.
`provider: replay`인 경우 `model_id`는 `replay:<repository-relative-jsonl-path>` 형식이고
`replay_hash`는 해당 JSONL bytes의 SHA-256이다. Resume은 둘을 다시 검증해 source가 이동하거나
변조된 경우 실행을 거부한다. 다른 provider에서는 `replay_hash`를 허용하지 않는다.

Approved suite가 만든 run은 optional `experiment` context를 반드시 채운다.

```yaml
experiment:
  experiment_id: dev-validation-live-pilot-20260728
  purpose: development-validation-live-pilot
  suite_hash: "sha256:..."
  execution_hash: "sha256:..."
  dataset_manifest_hash: "sha256:..."
  dataset_role: development-validation
  schedule_seed: 20260723
  schedule_order: 1
  schedule_row_id: "sha256:..."
  repetition: 1
```

OpenAI model block은 provider SDK version, reasoning effort/mode, service tier와 input,
cached-input, cache-write-input, output rate를 보존한다. 이 값으로 terminal usage의 model cost를
재계산할 수 있어야 한다.

## 5. Event envelope

```json
{
  "schema_version": "run-event-v1",
  "event_id": "evt_0193",
  "run_id": "run_0041",
  "sequence": 37,
  "type": "PatchApplied",
  "timestamp": "2026-07-23T10:14:30Z",
  "actor": "tool-gateway",
  "correlation_id": "act_0071",
  "payload": {
    "patch_hash": "sha256:...",
    "changed_files": ["src/parser.py"]
  }
}
```

최소 event type:

```text
RunStarted        PhaseChanged       ContextBuilt
MemoryRetrieved   ModelCalled        ToolCalled
PatchPrepared     ToolSucceeded      ToolFailed
ToolReplayed      PatchApplied
CheckStarted      CheckFinished      LoopDetected
ReviewRecorded    SubmissionAttempted
SubmissionRejected SubmissionAccepted CheckpointSaved
FailureTagged     RunCompleted       RunFailed
```

Event payload schema는 type별 version을 가져야 한다. Secret, full hidden assertion, raw credential을 payload에 저장하지 않는다.

Submission lifecycle payload는 patch body나 model text를 복사하지 않는다. Public
`worktree_diff_hash`, attempt number, reason code, source event/request artifact identity와
accepted patch의 CAS artifact metadata만 남긴다. `SubmissionAccepted`는 deterministic evaluator에 넘길 orchestration 조건을
충족했다는 뜻이며 hidden/regression/scope/safety 성공을 주장하지 않는다.

새 live turn의 `ContextBuilt` artifact는 `model-request-evidence-v1`이다. API key와 HTTP
authorization header를 제외한 exact logical Responses request body, request body hash와
버전된 context-build evidence를 함께 보존한다. `phase-evidence-v2`와 이를 상속하는
`phase-evidence-v3`는 raw event window를 먼저 자른 뒤 filtering하지 않고 agent-visible
event를 먼저 filtering한 뒤 최근 12개를 선택한다. Oversized tool result는 원본 JSON을 먼저
parse하고 string field를 semantic하게
줄여 가능한 경우 valid JSON과 scalar metadata를 보존한다. 그래도 character cap을 넘는
large list/object는 bounded top-level key와 summary fallback으로 대체한다. Context evidence는 전체 eligible event 수,
최근-event policy로 포함·생략한 sequence, tool-result character cap 적용 여부, memory와
component별 character 수, 최종 UTF-8 byte 수를 기록한다. 따라서 PatchLoop가 policy에 따라
context를 줄인 경우와 provider가 input을 줄인 경우를 분리할 수 있다.

v2 context의 `phase_contract`는 current phase/diff hash, current-diff completed/pending
checks, missing evidence, allowed next actions와
`apply_patch → run_check → get_diff → finish_task` 순서를 machine-readable하게 제공한다.
`execution_signals.repeated_calls`는 `LoopDetected`를 요약한다. 기존 manifest의
`context_policy_version=v1`은 과거 replay와 immutable trace 해석을 위해 기존 rendering을
유지한다.

새 live `ModelCalled` event는 `prompt_telemetry_version: prompt-token-integrity-v1`과 함께
다음을 기록한다.

```text
requested_input_tokens        Responses input-token-count endpoint의 exact count
input_tokens                  생성 응답 usage의 실제 input count
input_token_count_match       위 두 값의 일치 여부
cached/cache-write input      provider usage breakdown
output/reasoning output       전체 output과 그 안의 reasoning token
total_tokens                  input + output reconciliation
response_status               completed | incomplete | failed
response_truncation           요청과 응답의 truncation policy
response_incomplete_reason    max_output_tokens 등의 provider reason
response_model                요청한 dated snapshot과 실제 provider model의 일치
request artifact identity     같은 turn의 ContextBuilt request와 결속
```

Responses request는 `truncation: disabled`를 명시한다. Context window를 넘으면 앞부분을
조용히 제거하지 않고 provider error로 종료해야 한다. Input-token count mismatch나 incomplete
response에서는 tool call을 실행하지 않고 이미 반환된 usage를 먼저 보존한다.

## 6. Checkpoint

```json
{
  "schema_version": "checkpoint-v1",
  "run_id": "run_0041",
  "checkpoint_id": "ckpt_0012",
  "through_sequence": 37,
  "phase": "VERIFY",
  "task_summary": "...",
  "reproduction_status": "confirmed",
  "current_plan": [
    "Update quoted field state handling",
    "Run targeted parser tests",
    "Run full regression suite"
  ],
  "modified_files": ["src/parser.py"],
  "completed_action_ids": ["act_0068", "act_0071"],
  "completed_checks": ["unit_test_parser"],
  "pending_checks": ["regression_suite"],
  "important_decisions": [
    {
      "decision": "Do not modify public parser interface",
      "evidence_event_ids": ["evt_0151"]
    }
  ],
  "repository_head": "a13f8d2",
  "worktree_diff_hash": "sha256:...",
  "last_patch_hash": "sha256:...",
  "remaining_budget": {
    "model_calls": 8,
    "tool_calls": 21,
    "tokens": 26000
  },
  "created_at": "2026-07-23T10:14:31Z"
}
```

Checkpoint가 참조한 event sequence나 hash를 검증할 수 없으면 자동 재개하지 않고 recovery error를 기록한다.
v2에서 `completed_checks`는 전체 history의 한 번이라도 성공한 check가 아니라
`worktree_diff_hash`에 대한 최신 check 결과만 뜻한다. `pending_checks`는 그 diff에서
아직 pass하지 않은 required public check이고, `last_patch_hash`는 이후 read/check/diff와
무관하게 마지막 성공 mutation identity를 유지한다. 이 강화는 checkpoint schema에
default field를 추가하지 않으므로 기존 checkpoint serialization을 바꾸지 않는다.
v2 checkpoint의 `current_plan`은 비워 두고, 다음 turn에서 실제 포함된 tool-result
evidence까지 다시 계산한 `phase_contract.allowed_next_actions`만 authoritative하게 사용한다.
마지막 `PatchApplied` 이전 check/review는 현재 diff hash가 우연히 과거 값으로 돌아와도
새 mutation epoch에서 재사용하지 않는다.
Submission readiness는 현재 non-empty diff와 같은 hash를 기록한 최신 `PatchApplied`도
요구한다. 따라서 base repository의 visible check와 empty diff만으로 `finish_task`를
accept하지 않는다.

## 7. Tool call contract

모든 mutating 또는 비용이 큰 tool call은 다음 공통 envelope를 사용한다.

```json
{
  "tool": "apply_patch",
  "tool_schema_version": "v2",
  "action_id": "act_0071",
  "run_id": "run_0041",
  "input": {},
  "input_hash": "sha256:..."
}
```

### `search_files`

```json
{
  "query": "parse_csv",
  "path_glob": "src/**/*.py"
}
```

### `read_file`

```json
{
  "path": "src/parser.py",
  "start_line": 1,
  "end_line": 160
}
```

### `apply_patch`

```json
{
  "patch": "diff --git a/src/parser.py b/src/parser.py\n--- a/src/parser.py\n+++ b/src/parser.py\n@@ ..."
}
```

`patch`는 `diff --git`으로 시작하는 raw Git unified diff다. OpenAI built-in
apply-patch envelope인 `*** Begin Patch` / `*** End Patch` 형식은 이 constrained tool의
입력이 아니며 구조화된 `CONTRACT_ERROR`로 거부한다.

현재 patch tool은 기존 tracked text file의 동일 경로 수정 또는 삭제만 지원한다. 새 파일,
rename/copy, binary와 metadata-only patch는 agent workspace의 untracked state가 scope
요약을 우회하지 않도록 거부한다. Agent-visible gateway는 hunk header에 선언된 old/new
line total만 `git apply --recount`로 body에서 다시 계산한다. Hunk body 문법, context,
파일 경로와 Git 적용 가능성은 완화하지 않는다. Hidden evaluator와
`WorkspaceManager.apply_patch`는 `--recount` 없이 strict patch를 요구한다.

Mutation 뒤에는 scope, dependency, test tampering, public API와 zero-untracked 불변식을
모두 검사한다. v2의 거부 또는 post-mutation 검사 예외는 intent의 검증된 preimage로
복원하고 pre-call worktree diff hash와 zero-untracked 상태를 재확인한다. Legacy v1만 같은
raw patch를 `--reverse --recount`로 적용한다. Rollback 실패나 정확한 복원 실패는 일반 tool
rejection으로 삼키지 않고 `RECOVERY_ERROR`로 run을 fail-closed한다. Checkpoint와 resume도
agent workspace에 untracked file이 있으면 거부한다. Raw 입력은 다시 쓰지 않으므로
`input_hash`, `patch_hash`와 CAS evidence는 model이 보낸 원문에 결속한다. Function parameter JSON
Patch parameter schema 자체는 유지하지만, current-diff evidence와 structured submission을
함께 고정하기 위해 새 run의 전체 tool surface는 v2다. 기존 v1 replay는 그대로 유지한다.

v2의 mutating lifecycle은 다음 순서다.

```text
ToolCalled(raw patch CAS)
→ PatchPrepared(patch-mutation-intent-v1 CAS)
→ all-target preflight
→ atomic postimage replace/delete
→ action_results + ToolSucceeded/ToolFailed + optional PatchApplied atomic commit
→ phase transition + checkpoint
```

Intent는 baseline/expected worktree diff hash와 각 touched tracked regular file의 path, mode,
Git mode, preimage CAS, postimage CAS 또는 deletion marker를 가진다. v2는 target 전체를
검증한 뒤 각 postimage를 atomic replace/delete한다. Policy 또는 post-validation 오류가
나면 검증된 preimage로 모든 target을 복원하고 baseline을 다시 확인한다. Direct
`git apply --recount`와 `--reverse --recount` rollback은 legacy v1에만 남는다. 새 owner는
최신 checkpoint 뒤의 미완료 patch를 다음처럼 판정한다.

```text
all pre    apply once
all post   finalize without another forward apply
mixed      restore every verified preimage, verify baseline, then apply once
unknown    RECOVERY_ERROR without overwriting the unknown state
```

Raw patch, intent와 nested pre/post CAS는 v2 source evidence와 leak scan에 포함된다.
동일 action/result의 재기록은 canonical result JSON까지 같아야 하며, 같은 input hash라도
다른 result를 허용하지 않는다.

동일 `action_id + input_hash`가 성공했다면 기존 result를 반환한다. 같은 action ID에 다른
input hash가 오면 stale/conflicting action으로 거부하고 patch를 적용하지 않는다.

v2 non-mutating tool은 normalized input CAS를 `ToolCalled`에 보존한다. Durable outcome 없이
중단된 `read_file`, `search_files`, `run_check`, `get_diff`는 workspace가 마지막 checkpoint와
같을 때만 같은 action identity로 재실행하고 원래 call을 `ToolSucceeded`/`ToolFailed`로
닫는다. 이미 durable result가 있는 v2 action을 다시 호출한 idempotency cache hit만
`ToolReplayed`를 남긴다. v1은 기존 event 순서와 source hash 호환성을 위해 cached outcome을
legacy `ToolSucceeded`/`ToolFailed`로 다시 나타낸다.

Patch format/context/policy rejection artifact는 `error_details.stage`,
`error_details.reason`, retry guidance와 파악 가능한 경우 corrupt line을 포함한다. Gateway가
patch를 대신 수정하거나 느슨하게 적용하지는 않는다.

### `run_check`

```json
{
  "check_id": "unit_test_parser"
}
```

Result 공통 필드:

```json
{
  "action_id": "act_0080",
  "status": "succeeded",
  "started_at": "2026-07-23T10:15:00Z",
  "finished_at": "2026-07-23T10:15:04Z",
  "exit_code": 0,
  "timed_out": false,
  "truncated": false,
  "stdout_artifact_id": "art_0102",
  "stderr_artifact_id": "art_0103"
}
```

`run_check`와 `get_diff` result 및 대응 `ToolSucceeded`에는
`worktree_diff_hash`가 반드시 들어간다. Registered check가 tracked worktree를 바꾸면
그 결과를 acceptance evidence로 사용하지 않고 recovery error로 fail-closed한다.

### `finish_task`

```json
{}
```

`finish_task`는 empty object만 받는 orchestrator action이다. 다음 조건의 논리곱을
만족해야 한다.

```text
latest successful PatchApplied matches a non-empty current worktree_diff_hash
AND latest required visible checks pass on that current worktree_diff_hash
AND get_diff succeeded after those latest check events on the same diff
AND that get_diff tool result was available and untruncated in this model request
AND current phase is REVIEW
```

성공 시 exact patch bytes를 CAS에 먼저 동결하고 `ReviewRecorded → SubmissionAttempted
→ ToolSucceeded → SubmissionAccepted → REVIEW→DONE → CheckpointSaved` lifecycle을
남긴 뒤 그 CAS artifact만 evaluator에 전달한다. 현재 offline fault test에서는 각
lifecycle boundary의 injected suspension 뒤 같은 runner가 resume할 때 `action_id`별
durable prefix를 검증하고 누락 suffix만 보충하며 중복 event나 transition을 만들지 않는다.
별도 subprocess E2E는 single-file smoke patch의 유일한 atomic postimage replacement 뒤,
outcome persistence 전에 실제 worker를 종료한다. 새 interpreter가 stale `RUNNING`을
reclaim해 같은 run ID로 evaluator까지 완료하며 duplicate `ToolCalled`/`PatchApplied`가
없음을 검증한다. Multi-file mixed/partial reconciliation은 별도 unit test evidence다. 실패 시
`SubmissionAttempted → SubmissionRejected`와
rejected tool result를 남기고 phase를 유지한다. 세 번째 거부만
`SubmissionProtocolError` terminal failure가 된다. Legacy v1 replay의 text `DONE`은
과거 artifact 재현을 위해 별도 호환 경로로만 읽는다.

성공과 거부를 포함한 모든 tool result는 content-addressed artifact로 저장한다. 거부 event는
`error_code`, public `error_message`와 artifact identity를 남기며 다음 turn의 stateless
context builder가 이 결과를 다시 제공한다. Private evaluator는 agent tool gateway를
통과하지 않으므로 hidden assertion이나 reference material은 이 feedback에 포함되지 않는다.

새 `context_policy_version=phase-evidence-v3`로 D-037을 선언한 run은
model-originated mutating-tool call이 거부된 경우 바로 다음 request가
result만이 아니라 latest rejected input의 exact agent-visible bytes와 content hash도
함께 제공해야 한다. Context builder는 event의 CAS descriptor를 모델에게 보여주는 것으로
충족했다고 보지 않고 실제 bytes를 CAS에서 읽어 request에 넣는다. Exact candidate와
structured rejection reason이 full per-call budget 안에 함께 들어가지 않으면 generation을
시작하지 않고 structured budget failure를 남긴다. 이 retry block은 public/model-originated
content만 허용하며 private evaluator artifact는 참조하지 않는다.

```json
{
  "rejected_mutation_retry": {
    "schema_version": "rejected-mutation-retry-v1",
    "tool": "apply_patch",
    "action_id": "act_0071",
    "source_call_sequence": 27,
    "source_failure_sequence": 29,
    "candidate": {
      "patch": "diff --git ...",
      "content_hash": "sha256:...",
      "size_bytes": 1326,
      "input_hash": "sha256:..."
    },
    "rejection": {
      "status": "rejected",
      "error_code": "CONTRACT_ERROR",
      "error_message": "public structured reason",
      "error_details": {"stage": "syntax", "reason": "git_apply_failed"}
    }
  }
}
```

Candidate와 rejection result의 nested artifact descriptor는 각각 top-level
`ToolCalled`/`ToolFailed` artifact identity와 일치해야 하며, builder는 두 CAS object의
path·size·SHA-256과 UTF-8을 다시 확인한다. Candidate는 일반 tool-result character cap으로
자르지 않는다. 최신 `ModelCalled` 뒤 여러 rejected patch가 있으면 마지막 것만 선택하고,
새 `ModelCalled` 뒤에는 block을 제거한다. Exact input과 full output allowance가 남은
token budget을 넘으면 request artifact와 다음 event를 남기고 response generation은 호출하지
않는다.

```json
{
  "type": "ModelGenerationBlocked",
  "payload": {
    "reason_code": "exact_request_budget_exceeded",
    "error_code": "MODEL_GENERATION_BUDGET_EXCEEDED",
    "generation_started": false,
    "requested_input_tokens": 1000,
    "remaining_tokens": 4899,
    "max_output_tokens": 4096,
    "input_token_count_calls": 1,
    "retry_context_present": true,
    "retry_candidate_content_hash": "sha256:..."
  }
}
```

Qualification은 `remaining_tokens`를 block 이전 `ModelCalled`의 input/output usage와
manifest의 `max_total_tokens`로 다시 계산한다. 또한 위 payload 전체가 terminal
`RunFailed.error_details`와 `RunResult.terminal_error.details`에 동일하게 결속되고,
terminal error type/code가 `ModelGenerationBudgetError` /
`MODEL_GENERATION_BUDGET_EXCEEDED`인지 확인한다.

현재 mini r2 evidence는 이 version 도입 전 `phase-evidence-v2` trace로 그대로 보존한다.

## 8. Verifier result and final outcome

```json
{
  "schema_version": "verifier-result-v1",
  "verifier_result_id": "vr_0011",
  "run_id": "run_0041",
  "check_type": "hidden_acceptance",
  "check_id": "hidden_multiline_csv_tests",
  "state": "pass",
  "duration_ms": 412,
  "evidence_artifact_ids": ["art_0200"],
  "details": {
    "tests_passed": 4,
    "tests_failed": 0,
    "evidence_artifacts": [{
      "artifact_id": "art_0200",
      "content_hash": "sha256:...",
      "media_type": "text/plain",
      "size_bytes": 120,
      "path": "objects/sha256/...",
      "created_at": "2026-07-29T00:00:00Z"
    }]
  }
}
```

```json
{
  "schema_version": "run-result-v1",
  "run_id": "run_0041",
  "agent_submission_status": "completed",
  "evaluation_status": "completed",
  "scope_compliant_success": true,
  "official": true,
  "verdicts": {
    "hidden_tests": "pass",
    "regression_tests": "pass",
    "scope_policy": "pass",
    "safety_policy": "pass"
  },
  "usage": {
    "input_tokens": 0,
    "cached_input_tokens": 0,
    "cache_write_input_tokens": 0,
    "output_tokens": 0,
    "reasoning_output_tokens": 0,
    "model_cost_usd": 0,
    "model_calls": 0,
    "input_token_count_calls": 0,
    "tool_calls": 0,
    "wall_clock_ms": 0
  },
  "submitted_patch_artifact_id": "art_0180"
}
```

새 evaluator bundle의 각 executed verifier는 opaque ID뿐 아니라
`details.evidence_artifacts`에 full Artifact descriptor를 남긴다. Provenance는
`verifier-evidence-v1`과 같은 descriptor 목록을 보존한다. Runner는
`evaluation-receipt-v1`의 manifest/result/provenance hash, run/diff/result-artifact
identity, duration과 모든 verifier CAS bytes를 검증한 경우에만 완료된 evaluation을
재사용한다. v2 accepted submission이 있으면 그 submitted-patch descriptor와 bytes도
동일해야 한다. Terminal result/status/event와 optional `FailureTagged`는 한 SQLite
transaction으로 확정한다.

Skipped, infrastructure error, policy rejection을 `false`와 혼합하지 않는다. 각 verdict는 내부적으로 `pass | fail | error | not_run` 상태를 보존하고, SCRR 성공은 네 항목이 모두 `pass`일 때만 true다.

`scope_policy_passed`는 단일 검사 결과가 아니라 allowed/forbidden path, diff size, dependency, test tampering, public API 정책의 deterministic aggregation이다. 구성 검사 하나라도 `fail | error | not_run`이면 scope policy를 pass로 만들 수 없다. 개별 구성 결과는 별도 `VerifierResult`로 보존한다.

Live suite의 각 시작된 attempt는 성공 여부와 관계없이 stable run ID를 가진다. Terminal
failure도 `RunFailed` event와 `RunResult`를 저장하며 usage에는 input, cached input,
cache-write input, output token과 계산된 model cost가 포함된다. Experiment row는 terminal
outcome, infrastructure error와 qualification 결과를 연결한다. 첫 infrastructure 또는
qualification error 뒤의 schedule row는 새 API call 없이 `not_started`로 보존한다.

`cached_input_tokens + cache_write_input_tokens <= input_tokens`는 schema 불변식이다. 이미
응답을 받은 뒤 function-call argument JSON이 malformed인 경우에도 adapter는 응답 usage를
먼저 구조화하고 `ModelCalled`와 terminal failure에 보존한 뒤 agent failure로 종료한다. 이미
과금된 response usage를 parsing exception 때문에 버리거나 cache token 초과분을 조용히
clamp한 값으로 qualification해서는 안 된다.

`reasoning_output_tokens <= output_tokens`도 불변식이다. `output_tokens`는 화면에 보이는
text만이 아니라 reasoning, tool/message framing 등 provider가 생성한 모든 output token을
포함하므로 예산과 비용은 전체 `output_tokens`로 계산한다. `input_token_count_calls`는 생성
model call과 구분한 observability count이며 model-call budget이나 model token cost에 더하지
않는다.

`model_cost_usd`는 manifest에 동결한 공식 list-price profile로 재계산한 direct token-cost
estimate다. Account invoice나 data-sharing incentive 적용 증거가 아니며, PatchLoop의
function-tool run은 무료라고 가정하지 않는다.

## 9. Failure record

```yaml
schema_version: failure-v1
failure_id: fail_0042
run_id: run_0041
primary_cause: CONTEXT_MISSING
observed_symptoms:
  - WRONG_FILE_SELECTED
  - REPEATED_ACTION
phase: IMPLEMENT
recoverability: recoverable
evidence:
  - event_id: evt_0171
    description: Agent edited adapter.py without reading parser.py
confidence: 0.87
classification_method: deterministic_plus_review
review_status: reviewed
```

초기 taxonomy:

```text
SPEC_AMBIGUITY          CONTEXT_MISSING
WRONG_FILE_SELECTED     TOOL_MISUSE
REPEATED_ACTION         TEST_OVERFITTING
SCOPE_VIOLATION         VERIFICATION_FAILURE
ENVIRONMENT_FAILURE     PREMATURE_STOP
STATE_RECOVERY_FAILURE  MEMORY_MISAPPLICATION
UNKNOWN
```

Cause와 symptom을 구분하고, label만 단독 저장하지 않는다.

### Trace qualification과 review eligibility

Legacy v1 run은 immutable `trace-qualification-v1`을 유지하고, 새 v2 run은
`trace-qualification-v2` artifact를 content hash와 함께 별도로 남긴다.
Qualification은 최소한 다음 경계를 검사한다.

- Task/public/private hash와 frozen dataset role, experiment purpose가 일치함
- Event sequence가 1부터 연속이고 terminal event가 정확히 하나이며 마지막 event임
- `RunStarted`, `ContextBuilt`, `ModelCalled`, durable checkpoint evidence가 존재함
- 위 세 필수 event가 `artifact_id`와 content-addressed `artifact_path`를 모두 가지며,
  path가 가리키는 bytes의 SHA-256이 CAS identity와 일치함
- `no_memory` manifest에 retrieval event나 index identity가 없음
- OpenAI/Terra/medium/standard/default, fault-free와 exact Docker provenance가 일치함
- Durable approved execution plan의 suite/dataset/task/private evaluator/schedule row가
  run manifest와 일치함
- Agent-visible event/artifact에 공개 contract에 없는 private 구조 marker/hidden check ID가
  없고, 공개 여부와 무관하게 hidden artifact path/hash, reference hash 또는 현재 API key가 없음
- Event usage, persisted result, terminal outcome과 evaluator verdict가 서로 일치함
- v2 submission은 actual `get_diff` event, 그 결과를 포함한 다음 request,
  `finish_task` success, same-diff accepted patch CAS artifact, `REVIEW→DONE`과 final
  checkpoint가 하나의 lifecycle로 결속됨
- `prompt-token-integrity-v1`을 선언한 새 trace는 모든 turn에서 exact request artifact가
  `ContextBuilt`와 결속되고, input-token pre-count와 response usage가 일치하며,
  `truncation=disabled`, `status=completed`, incomplete reason 없음과 total/reasoning token
  불변식을 만족함
- Pilot은 적어도 한 tool call을 포함해 실제 function-tool loop를 통과함

`qualified=true`는 trace artifact가 자기 outcome과 provenance를 일관되게 보존했다는 뜻이다.
Development-validation pilot acceptance는 여기에 `evaluation_reached=true`를 추가로 요구한다.
따라서 evaluator 이전 agent failure도 trace qualification은 통과할 수 있지만 development
campaign을 열지는 못한다.

r1~r3처럼 D-031 이전에 생성된 immutable `development-validation-live-pilot`에는
`prompt_telemetry_version`이 없다. Qualification은 이 legacy absence 자체를 실패로
소급하지 않는다. 반면 model-candidate pilot, memory-development와 core purpose는
telemetry 자체가 없으면 fail-closed하며, 한 event라도 새 telemetry version을 선언한
trace는 모든 model event에서 새 prompt-token integrity 계약을 만족해야 한다.

Leak scan은 private token의 값이나 일치 문자열을 artifact에 다시 기록하지 않고 match count만
남긴다. Canonical public spec에 이미 있는 generic structure marker와 hidden check ID만
disclosure-tolerant로 취급하며, reference/hidden artifact identity와 API key는 항상 private다.
Deterministic failure record도 hidden `check_id`를 복사하지 않는다. 공개
`check_type:state`, opaque verifier result ID와 artifact ID만 저장한다.

Qualification된 모든 run이 memory source가 되는 것은 아니다.
`memory_candidate_eligible=true`는 `memory-development` role,
`memory-development-no-memory` purpose, `no_memory`, fault-free, qualification 통과와
`task_failure | agent_failure` outcome을 모두 만족할 때만 가능하다. Resolved run,
development-validation pilot, infrastructure error, calibration/held-out run은 후보가 아니다.

Qualification은 자기 JSON의 `qualification_hash` 외에 `source_evidence_hash`를 가진다. 이
hash는 approved execution plan bytes, manifest, ordered events, checkpoints, state result,
persisted result artifact hash와 agent-visible CAS artifact identity/content hash를 하나의
canonical snapshot으로 결속한다. v2 source snapshot은 `SubmissionAccepted`에 nested된
submitted-patch CAS object의 실제 bytes와 size도 다시 읽어 결속한다. Modern evaluator
receipt가 있는 fresh v1/v2 run은 receipt, manifest/result/provenance 실제 hash와 verifier
evidence CAS도 다시 읽어 결속한다. Receipt가 없는 historical v1 artifact는 기존 source
hash 경로를 유지한다. Qualification file을 다시 읽는 것만으로 source가 그대로라고
간주하지 않는다.

Development campaign preflight도 pilot qualification을 소비할 때 현재
`source_evidence_hash`를 다시 계산해 불일치나 원본 부재를 차단한다.

Human review는 원래 `FailureRecord`를 수정하지 않는다.
`failure-review-v1` JSONL에 decision, failure/qualification/dataset hash와 이전 review hash를
연결해 append-only chain으로 쌓는다. Review 시작과 memory index build는 각각 현재
`source_evidence_hash`를 다시 계산한다. Memory builder는 가장 최근 decision이 `reviewed`이고
현재 source hash가 qualification과 review provenance에 모두 일치할 때만 entry를 만든다.

## 10. Failure memory entry

```yaml
schema_version: memory-entry-v1
memory_id: mem_0042
index_version: memory-dev-v3

failure_pattern:
  class: REPEATED_ACTION
  phase: VERIFY
  description: Agent repeatedly runs the full suite after a localized failure.

preconditions:
  - Full suite execution exceeds 5 minutes
  - Failing test has a directly identifiable test module

diagnostic_evidence:
  - Three consecutive identical full-suite commands
  - No source change between commands

recommended_actions:
  - Run the nearest failing unit test first
  - Inspect the first actionable traceback
  - Run the full suite only after the targeted test passes

do_not_apply_when:
  - Failure occurs only in an integration environment
  - Test-order dependency is suspected

applicable_languages: [python]
source_run_ids: [run_0182, run_0214]
validation_count: 4
confidence: 0.83
```

Memory에는 raw solution, reference patch, hidden test text를 넣지 않는다. `do_not_apply_when`은 required field다.

## 11. Retrieval decision

```json
{
  "schema_version": "memory-retrieval-v1",
  "run_id": "run_0041",
  "index_version": "memory-dev-v3",
  "query_hash": "sha256:...",
  "threshold": 0.72,
  "token_budget": 2000,
  "candidates": [
    {
      "memory_id": "mem_0042",
      "score": 0.81,
      "selected": true,
      "rendered_tokens": 241
    }
  ],
  "selected_memory_ids": ["mem_0042"],
  "no_match": false
}
```

No candidate가 threshold를 넘지 않으면 `selected_memory_ids`는 빈 배열이고 `no_match`는 true다. 빈 결과는 failure가 아니다.
