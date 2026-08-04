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

`task-public-v1`은 historical/frozen task 계약이며 `probe_profiles` field를 빈 배열로도
허용하지 않는다. Agent-authored diagnostic을 명시적으로 허용하는 새 task만
`task-public-v2`를 사용한다.

```yaml
schema_version: task-public-v2
# v1의 repository/issue/constraints/visible_checks는 동일하게 유지
probe_profiles:
  - id: python-edge-cases
    runtime: ephemeral-python-v1
    timeout_seconds: 30       # 1..60
    output_limit_bytes: 64000 # 최대 64 KB
    source_limit_bytes: 12000 # UTF-8 bytes 기준 최대 12 KB
```

Profile은 실행 command나 image를 task가 선택하게 하지 않는다. Harness가 고정한
repository-free image와 trusted wrapper만 사용하며, profile은 public opt-in ID와 더 낮출
수만 있는 timeout/output/source bound를 등록한다. V2는 profile을 최소 하나 요구하고 ID
중복을 거부한다. Probe profile은 visible check가 아니며 authoritative acceptance를 만들지
않는다.

D-059의 checked-in contract fixture는
`fixtures/task-packages/self-validation-csv-quoted-newline`의
`csv-quoted-newline@2`다. 이 package는 같은 작은 calibration issue를 이용해 profile
lifecycle을 결정적으로 검사할 뿐 새로운 research task가 아니다. 따라서 `tasks/` 밖에
두고 `data/dataset-manifest.yaml`에 등록하지 않으며 calibration, memory-development,
held-out, core 또는 headline task로 셀 수 없다. Loader와 agent resume은 exact
`task_id + task_version + public_spec_hash`로 이 fixture를 식별한다.

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
| `development-validation` | 2 | Rendering/no-match/leak와 live runtime/completion 검증 전용; memory source와 core headline에서 제외 |
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

`experiment-v2`는 모든 suite에 `purpose`를 명시한다. 기존 `experiment-v1` suite는
historical/offline evidence를 위한 읽기 호환만 유지하며 새 live 실행에는 사용하지 않는다.

| Purpose | Exact contract |
| --- | --- |
| `offline-smoke` | `model=mock`; API 호출 없음 |
| `development-validation-live-pilot` | Consumed D-054: Babel #1042 + Moto #7208, `no_memory`, task별 repetition 1, 총 2 run, $6 상한. Historical IDs는 당시 task/budget 계약으로만 읽고 재실행 금지 |
| `development-validation-model-candidate-pilot` | Babel #1042 한 task, `no_memory`, repetition 1, dated candidate model, $2 상한; primary campaign gate와 분리된 historical diagnostic lane |
| `memory-development-no-memory` | frozen memory-development 여섯 task, `no_memory`, repetition 2, 총 12 run, $20 상한 |
| `memory-development-no-memory-budget-pilot` | V4 budget-terminal resource maxima로 고정한 HF Hub/PDM/pyfakefs, `no_memory`, repetition 1, 총 3 run, $7 상한; memory source와 comparison denominator에서 제외 |
| `memory-development-no-memory-corrective-pilot` | Consumed D-062 HF Hub/PDM/pyfakefs corrective panel, v4/v7, 900k, $13 상한; immutable하고 재실행 금지 |
| `memory-development-no-memory-saturation-pilot` | D-064 HF Hub 한 task, `no_memory`, repetition 1, v4/v8/runtime-v2, 900k, $5 상한; 자연 saturation/reset diagnostic이며 memory source와 comparison denominator에서 제외 |
| `memory-development-no-memory-review-evidence-pilot` | Consumed D-067 HF Hub 한 task, `no_memory`, repetition 1, v4/v9/runtime-v3, 60/100/1.2M/1,800초, output 25k, $6 상한; immutable hidden task failure이며 재실행·comparison·memory admission 금지 |
| `memory-development-no-memory-coverage-review-pilot` | D-070 exact HF Hub 한 task, `no_memory`, repetition 1, v5/v10/runtime-v4, 60/100/1.2M/1,800초, output 25k, $6 상한; tuning-only이며 comparison·memory admission 제외, 별도 hash/비용 승인 전 live 실행 금지 |
| `memory-development-no-memory-coverage-rejection-pilot` | Consumed D-072 exact HF Hub 한 task, `no_memory`, repetition 1, v6/v11/runtime-v5, 60/100/1.2M/1,800초, output 25k, reserve $5.5125/$6 상한; readiness gate pass/recovery inconclusive/hidden task failure인 immutable row이며 재실행·comparison·memory admission 금지 |
| `generic-baseline-readiness` | D-075 r1과 D-077 r2는 consumed/immutable false gate다. D-081 r3는 같은 ordered four-row generic V2/V5 tuple에서 model/tool count를 observability-only `null`, total token 2.4M, wall 1,800초로 고정했고 D-082에서 exact hash로 한 번 실행되어 4/4 workflow completion과 gate v2 pass를 기록했다. 1/4 task success지만 calibration-only이며 baseline/memory/core 제외 |
| `comparison-budget-freeze` | D-083은 D-081 r3 public process evidence만으로 null/null/1.6M token/1,800초/output 25k/retry 0 per-run policy를 offline 동결한다. Runtime/manifest/qualification support와 live/baseline/memory/core authority는 없음 |
| `workflow-completion-probe` | D-079 exact pyfakefs 한 row, `no_memory` repetition 1, generic V2/V5, model/tool call `null`·observability-only, 3M token/7,200초/output 25k, reserve $13.6125/$14 cap; calibration-only이며 clean hash와 별도 승인 전 live 실행 금지 |
| `core` | frozen held-out 12 task, memory 네 조건, repetition 2, 총 96 run |

Primary comparison purpose는 다음 값을 고정한다.

```yaml
model: openai
model_id: gpt-5.4-mini-2026-03-17
reasoning_effort: medium
reasoning_mode: standard
service_tier: default
max_output_tokens: 25000
budget:
  max_model_calls: 21
  max_tool_calls: 50
  max_total_tokens: 250000
  wall_clock_timeout_seconds: 900
seed: 20260723
```

위 21/50/250k 값은 아직 실행하지 않은 memory-development/core comparison draft다.
D-054 completion calibration은 이를 공정 비교 budget으로 자동 채택하지 않고 다음 별도
진단 계약을 사용한다.

```yaml
purpose: development-validation-live-pilot
tasks:
  - tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes/public.yaml
  - tasks/dev-validation/moto-query-scanned-count/public.yaml
conditions: [no_memory]
repetitions: 1
model_id: gpt-5.4-mini-2026-03-17
reasoning_effort: medium
reasoning_mode: standard
service_tier: default
max_output_tokens: 25000
budget:
  max_model_calls: 40
  max_tool_calls: 100
  max_total_tokens: 600000
  wall_clock_timeout_seconds: 1800
cost_limit_usd: 6
```

이 21은 모든 future memory 조건에 동일한 총 model-call 상한이며 `finish_task` 전용
reserve가 아니다. D-052 이전에 소비된 primary/development suite의 21/200,000 계약과
historical diagnostic suite의 20-call 의미는 변경하지 않는다.

Consumed completion panel task set은 Babel과 Moto의 위 두 canonical path로 exact match한다.
과거 single-task pilot ID와 실행되지 않았지만 superseded된 D-052 v5 ID는 Babel path와
당시 budget을 그대로 읽어 evidence identity를 보존한다.
Current 600k completion qualification은 approved execution plan의 task row가 suite task와
정확히 1:1인지 검사하고, `_make_schedule`과 같은 deterministic rule로 전체 schedule을
재계산해 row, hash와 expected run count를 exact match한다. 현재 run 하나와 일치하는
부분 plan만으로 qualification을 통과할 수 없다.
Development campaign은 frozen registry의 memory-development 여섯 task가 정확히 한 번씩
suite에 선언돼야 한다. 다른 role, 일부 집합, 중복 task 또는 다른 repetition은 schema 또는
preflight에서 거부한다. Development campaign은 먼저 성공 여부와 무관하게 trace
qualification과 `evaluation_reached=true`를 함께 만족한 accepted pilot의 run ID와
qualification hash를 요구한다.

Completion panel result는 `no-memory-completion-gate-v1`을 포함한다. `passed=true`는
두 row가 모두 terminal·trace-qualified이고 official evaluator에 도달했으며
infrastructure error, qualification error, diagnostic error와 budget terminal이 0이라는 뜻이다.
`task_successes`는 별도 관찰값이며 hidden/SCRR success는 completion 필수조건이 아니다.
`panel_headroom`은 각 run이 480,000 total token, 32 model call, 80 tool call,
1,440,000ms 안에 끝났는지를 기록한다. Completion은 통과했지만 headroom이 실패하면 해당
trace는 끝까지 실행된 evidence로 보존하되 후속 fair comparison budget은 동결하지 않는다.
Headroom pass도 후속 budget freeze의 필요조건일 뿐 충분조건이 아니다. 두
development-validation task의 관찰값을 memory-development 표본에 그대로 일반화하지 않고,
별도의 동일조건 no-memory baseline pilot과 비용 검토를 거쳐 비교 budget을 동결한다.

새 resource-stratified budget pilot은
[`dev-no-memory-budget-pilot-20260731-r1.yaml`](../experiments/dev-no-memory-budget-pilot-20260731-r1.yaml)에
세 canonical task와 `40 model / 100 tool / 480,000 total token / 1,800초`,
per-call output 25,000을 고정한다. 이 별도 purpose는 선행 qualified pilot을 요구하지 않아
자기 자신을 승인해야 하는 순환 gate를 만들지 않으며, 실패해도
`memory_candidate_eligible`이 되지 않는다. Approved plan qualification은 세 task row와
seeded schedule 전체를 다시 계산한다.

Result의 `no-memory-budget-pilot-gate-v1`은 expected run 3, terminal·qualified·official
evaluator arrival 3/3과 infrastructure/qualification/diagnostic/budget-terminal error 0을
요구한다. `task_successes`는 별도 관찰값이며 gate 필수조건이 아니다.
`comparison_denominator_eligible=false`와 `memory_admission_unlocked=false`는 이 진단
결과가 final baseline이나 memory admission을 자동으로 열지 않음을 명시한다.

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
- dated mini snapshot, medium reasoning, standard mode, default service tier와 SDK provenance
- 72시간 이내의 공식 price source/rate와 positive estimate
- 한 run의 frozen token/output budget을 모두 예약해도 campaign cost limit을 넘지 않음
- 동일 experiment result가 아직 존재하지 않음

2026-07-30T22:25:47Z에 재확인한 공식
[API pricing](https://developers.openai.com/api/docs/pricing)은 1M token당 input $0.75,
cached input $0.075, output $4.50이며 별도 cache-write rate는 없다. Primary model은
dated snapshot `gpt-5.4-mini-2026-03-17`이고, model ID와 SDK version, Git commit,
실행 시점을 함께 남긴다. Price verification이 72시간을 넘으면 live 실행을 거부하고
다시 확인한다.

D-054 completion ceiling의 authorization reserve는 run당
`(600,000 + 25,000) × $4.50/M = $2.8125`, 두 run `$5.625`이며 suite cap은 `$6`다.
이는 실제 spend나 invoice prediction이 아니다. D-052 comparison draft의 12-run
`$14.85`와 96-run `$118.80`은 calibration 뒤 변경될 수 있으므로 현재 paid authorization
합계로 보지 않는다. Completion panel의 실제 계산 비용은 `$0.15682575`이고, D-055 시점까지
측정된 list-price 합은 `$5.138372625`였다. Project-wide `$150` 상한은 machine-enforced
field가 아니며,
runner는 각 suite의 `cost_limit_usd`만 강제한다.

과거 Terra r1-r3 experiment ID와 r3 계약
`experiments/dev-validation-pilot.template.yaml`은 당시 identity를 그대로 보존한다.
Loader는 historical evidence 해석을 위해 이를 읽을 수 있지만 preflight는 항상
`HISTORICAL_SUITE_IMMUTABLE`로 차단한다. Terminal primary r1
`experiments/dev-validation-gpt54mini-campaign-pilot-r1.yaml`도 20-call historical
evidence로만 읽고 preflight에서 차단한다. Corrective primary r2
`experiments/dev-validation-gpt54mini-campaign-pilot-r2.yaml`와 첫
`experiments/dev-no-memory.template.yaml` campaign도 한 번 소비된 뒤 immutable
inspection 전용이다. V4 pilot
`experiments/dev-validation-gpt54mini-investigation-v4-pilot-r1.yaml`과 후속
`experiments/dev-no-memory-v4.template.yaml`도 각각 한 번 소비돼 inspection 전용이다.
정확히 21 model call/200,000 total-token 계약으로 소비된
`dev-validation-gpt54mini-campaign-20260730-r2`, `dev-no-memory-20260728`,
`dev-validation-gpt54mini-investigation-v4-20260730-r1`,
`dev-no-memory-v4-20260730-r1`은 immutable historical evidence이며 D-052로
소급 재해석하거나 재실행하지 않는다.

D-052의 실행되지 않은 single-pilot template
`experiments/dev-validation-gpt54mini-token-tail-v5-pilot-r1.yaml`
(`dev-validation-gpt54mini-token-tail-v5-20260730-r1`)은 D-054가
`superseded-unexecuted`로 보존하며 preflight에서 `SUPERSEDED_SUITE`로 차단한다.
`experiments/dev-validation-gpt54mini-completion-v6-pilot-r1.yaml`도 exact hash로 한 번
실행된 뒤 `HISTORICAL_SUITE_IMMUTABLE`로 닫혔다. 같은 experiment ID와 approval hash를
다시 제공해도 실행할 수 없다.
`experiments/dev-no-memory-v5.template.yaml` (`dev-no-memory-v5-20260730-r1`)와
`experiments/core.template.yaml`의 250k 값은 calibration 결과 전 pending draft다.
Development template의 `pilot_run_id`는 `null`이라 accepted v5 pilot 전에는 실행할 수
없고, core template의 embedding revision도 freeze 전 marker를 유지하므로 core 실행을
허용하지 않는다. 다음 paid candidate는 아직 만들지 않았다. 다음 gate는
memory-development의 작은 no-memory budget pilot을 별도 suite/hash로 설계하는 것이다.
Memory human admission과 index build도 새 baseline 뒤까지 보류한다. 이미 소비된
mini model-candidate r1/r2와 D-037 r3-r6 diagnostic suite도
`HISTORICAL_SUITE_IMMUTABLE`이며 approval/hash를 다시 제공해도 실행할 수 없다.

D-031 telemetry를 실제 provider에서 검증한 terminal r1은
`experiments/dev-validation-gpt54mini-pilot.yaml`에 보존한다. v2 corrective retry는
`experiments/dev-validation-gpt54mini-pilot-r2.yaml`에 별도 고정한다. D-037 r3는
`experiments/dev-validation-gpt54mini-d037-r3.yaml`에 보존한다. 세 suite는
`development-validation-model-candidate-pilot` purpose를 사용하며 기존
`development-validation-live-pilot` 선행 gate를 충족하지 않는다.
`gpt-5.4-mini-2026-03-17`, medium effort, default tier, `max_output_tokens: 4096`,
`max_total_tokens: 90000`을 허용한다. 공식 standard rate는 input $0.75/M, cached input
$0.075/M, output $4.50/M이고 cache-write rate는 `null`이다. 90,000은 run 전체
input+output 누적 상한이다. 이 historical diagnostic purpose와 4,096/90,000 계약은
같은 model snapshot을 쓰더라도 current primary mini purpose의 25,000/250,000 계약을 충족하지 않는다.
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

이 block은 `experiment-v2`의 명시적으로 versioned diagnostic purpose에서만 허용된다.
D-037 계열 `development-validation-model-candidate-pilot`은
`rejected_patch_retry_context`, D-064의 exact
`memory-development-no-memory-saturation-pilot`은 `saturation_context`를 정확히 한 번
선언해야 한다. Normalized suite, execution hash와 durable approved plan이 이 block을
포함하므로 승인 뒤 제거·변경하면 hash가 달라지고 실행 전에 거부된다. Block이 없는
historical r1/r2 suite는 기존 normalized identity를 유지한다.

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

R4 `run_826c1c7fb3d242c2`는 위 contract와 승인 execution hash를 정확히 한 번
사용했다. 13개 generation은 completed였지만 REVIEW의 다음 exact input 8,583과
25,000-token allowance가 남은 28,563-token total budget을 초과해 generation 전에
차단됐다. Retry candidate가 없는 이 generic terminal budget block은 현재 retry-specific
validator에서 valid terminal block으로 인정되지 않아 qualification은 21/22다. Suite와
run은 terminal evidence로 보존하며 같은 experiment ID나 승인 hash를 재사용하지 않는다.
Historical unversioned generic block과 qualification 21/22도 소급 변경하지 않는다.

D-041의 후속 r5는 새 experiment ID와
`d037-rejected-patch-retry-v3` profile을 사용한다.

```yaml
max_output_tokens: 25000
budget:
  max_model_calls: 20
  max_tool_calls: 50
  max_total_tokens: 200000
  wall_clock_timeout_seconds: 900
diagnostic:
  schema_version: experiment-diagnostic-v1
  profile: d037-rejected-patch-retry-v3
  required_trace_features:
    - rejected_patch_retry_context
```

V3는 runtime reservation 의미를 바꾸지 않는다. 매 generation 전에 exact input과 full
25,000-token response allowance가 남은 200,000-token total budget에 함께 들어가야 한다.
200,000은 r4가 이미 소비한 91,437-token prefix에 r4에서 관찰한 가장 큰 exact input
10,031과 25,000 allowance로 된 tail reservation 세 개를 더한
`91,437 + 3 × (10,031 + 25,000) = 196,530`을 올림한 diagnostic-only 값이다. 이는
Terra/core와 historical mini budget을 바꾸지 않는다. 같은 보수적 preflight 공식의
authorization reserve는 `(200,000 + 25,000) × $4.50/M = $1.0125`로 $2 cap 아래다.

V3는 새로 생성되는 `exact_request_budget_exceeded` terminal event에
`schema_version: model-generation-block-v1`을 요구한다. 이 payload가 request artifact,
recomputed remaining budget와 terminal error에 정확히 결속되면 retry candidate가 없는
generic block도 valid trace evidence가 될 수 있다. 그러나 generic block은
`rejected_candidate_count`, `retry_episode_count` 또는 D-037 gate를 증가시키지 않는다.
Historical unversioned retry block은 읽기 호환을 유지하지만 r4의 unversioned generic block은
당시 판정 그대로 invalid다. R5는 synthetic rejection이나 incomplete-response automatic
retry를 추가하지 않는다. Evaluator에 도달한 zero-episode r5는 inconclusive로 보존하며
자동으로 다시 실행하지 않는다.

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

R5가 terminal inconclusive로 끝난 뒤 D-043은 별도 r6/profile v4 controlled diagnostic을
고정한다.

```yaml
diagnostic:
  schema_version: experiment-diagnostic-v1
  profile: d037-rejected-patch-retry-v4
  required_trace_features:
    - rejected_patch_retry_context
```

V4만 run manifest에 다음 fault를 결속한다.

```yaml
fault:
  type: controlled-reject-first-prepared-patch
  trigger_after: 1
```

Trigger의 정확한 의미는 “첫 완전한 policy-pass patch”가 아니라
`first-preflight-valid-apply-patch`다. Raw Git diff 형식, tracked regular target,
현재 worktree context에서의 적용 가능성과 non-empty expected diff를 검증하고
`patch-mutation-intent-v1`을 CAS에 준비한 뒤, 실제 postimage write 전에 한 번 거절한다.
Invalid/비적용 patch는 trigger를 소비하지 않는다. Rejection은
`CONTROLLED_DIAGNOSTIC_REJECTION`과 `controlled-rejection-v1` details를 가진 durable
`ToolFailed`/result CAS로 기록하며 별도 `FaultInjected` event를 만들지 않는다. Resume은
interrupted prepared intent가 정확한 pre-state일 때 동일 rejection으로 닫고 post/mixed/
unknown state는 fail-closed한다. `PatchPrepared`와 controlled `ToolFailed`는 monotonic
sequence에서 정확히 인접해야 하며, 사이에 다른 event가 있거나 durable declaration이
malformed·duplicate이면 fault를 재주입하지 않고 recovery error로 닫는다.

V4 diagnostic은 일반 retry predicate에 더해 controlled rejection 정확히 1회, verified
controlled rejection 1회, 해당 action의 `PatchApplied` 0회와 controlled failure sequence
0개를 요구한다. Missing/duplicate/interleaved/mutated controlled evidence는 `failed`이며
`inconclusive`가 아니다. Direct `inject-fault` allowlist에는 이 fault를 노출하지 않는다.
R6는 r5의 25,000/200,000 budget pair와 $2 cap을 유지하지만 새 suite/profile/fault가
execution hash를 바꾸므로 별도 승인 없이는 provider call을 할 수 없다.

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
  max_output_tokens: 25000

budget:
  max_model_calls: 21
  max_tool_calls: 50
  max_total_tokens: 250000
  wall_clock_timeout_seconds: 900

environment:
  agent_image_digest: "sha256:..."
  evaluator_image_digest: "sha256:..."
  probe_image_digest: "sha256:..." # v3/v6 + registered probe profile일 때만
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

D-056 self-validation은 explicit opt-in pair인 `tool_schema_version=v3`와
`context_policy_version=phase-evidence-v6`을 함께 요구한다. 한쪽만 선택한 manifest는
reject한다. Current frozen experiment와 historical V1-V5 manifest는 기존 version/hash로
그대로 해석하며 v3/v6 field나 event를 합성하지 않는다. Probe를 실제 실행하는 manifest는
dedicated clean image의 strict SHA-256 image ID를 `probe_image_digest`에 고정한다. Offline
gate가 닫히기 전에는 OpenAI provider, paid preflight와 experiment campaign이 이 pair를
허용하지 않으며 start와 resume 모두 코드에서 거부한다.

D-059 offline fixture run은 public spec
`sha256:e72110791ac062f719a26c5b3d68d32152a5d82ede75a9971f667138f9bde926`,
private spec
`sha256:c1727483c0a496cde1765a55204b922ca7874973b937a2d9658121b5c938099c`와
clean image
`sha256:268495717da1396e3413ce6695063c9516202b4e38cb8042f2f181420b64e9c1`을
결속했다. 이 offline evidence는 위 live-provider 금지를 해제하지 않는다.

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
ToolAdmissionBlocked
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

`phase-evidence-v4`는 v3의 phase/retry 계약을 상속하고 top-level
`investigation_ledger`를 추가한다. Ledger는 checkpoint에 복사하지 않고, 마지막
`PatchApplied` 뒤 active mutation epoch의 correlated `ToolCalled`와 successful
read/search result CAS에서 매 turn 재계산한다. 최소 identity는 source sequence,
normalized call hash, worktree diff hash, query/glob, file content hash, 실제 반환 line
range, coverage union과 result content hash다. Context-build evidence와
`ContextBuilt`는 ledger hash, source-through sequence, no-progress streak와 exploration
admission을 기록하며 qualifier가 request마다 preceding durable prefix에서 다시 계산한다.
`source_through_sequence`는 해당 `ContextBuilt` 바로 전 sequence여야 한다. Tail의
model-call admission은 현재 context를 소비할 imminent generation 1회를 먼저 차감한
projected remaining count로 계산하므로 prompt의 `allowed_next_actions`와 같은 turn의
gateway admission이 일치한다.
V1-v3 context rendering과 qualification은 이 필드를 갖지 않는다.

`phase-evidence-v5`는 V4의 repository-evidence reconstruction을 상속하고 token-aware
projection을 `investigation-policy-v2`, `investigation-ledger-v2`,
`investigation-tail-policy-v2`와 `context-build-evidence-v5`로 versioning한다.
Projection의 observed input은 durable `ModelCalled.requested_input_tokens`를 우선하고,
그 값이 `None`일 때만 같은 event의 actual `input_tokens`로 fallback한다. Boolean,
negative 또는 그 밖의 invalid 값은 projection에서 조용히 제외하지 않고 fail closed한다.
유효한 관찰값에서 다음 input은 다음과 같이 계산한다.

```text
projected_next_input =
  max(observed_input_tokens)
  + max(0, maximum_positive_consecutive_growth)

projected_turns =
  5  before the current generation is durably recorded
  4  after the current generation is durably recorded

reserved_tokens =
  max_output_tokens + projected_next_input × projected_turns
```

`remaining_tokens <= reserved_tokens`이면 context의 read/search action은 nominal
corrective tail로 닫힌다. Equality도 차단 경계에 포함한다. 이 계산은 completion
guarantee가 아니며, generation admission의 strict exact request + full 25,000 response
allowance 검사는 독립적으로 그대로 수행한다.

`phase-evidence-v6`는 V5의 investigation/token-tail 의미를 바꾸지 않고 v3
self-validation lifecycle만 추가한다. V6은 mandatory `review_task` generation/tool을 위해
V5보다 nominal corrective tail에 model turn 1개와 tool call 1개를 추가로 예약한다. V5
projection과 historical evidence는 바꾸지 않는다. Machine-readable required sequence는
다음과 같다.

```text
PatchApplied
→ every registered visible check passes on the current diff
→ get_diff succeeds on that diff and is presented untruncated
→ review_task records same-request public evidence on that diff
→ the review_task result is presented untruncated
→ finish_task
```

`run_probe`는 위 sequence의 필수 단계가 아니다. 실행된 probe는 active mutation epoch와
`worktree_diff_hash`에 결속되며 `review_task.targeted_validation`이 인용할 수 있지만,
registered check를 대신하거나 hidden acceptance를 추정하는 authoritative verdict가 아니다.
V6 context/build/source evidence는 probe source/result와 review input/result의 CAS identity,
source event sequence, request artifact와 diff hash를 기록한다. Private spec, hidden
assertion, reference patch나 evaluator result를 context 또는 review에 넣으면 qualification을
fail closed한다.

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

`query`는 1~500자다. `path_glob`은 최대 500자·100 path segment의 repository-relative
pattern이며 `**`는 segment 전체로만 사용할 수 있다. Empty/current-directory, parent,
absolute와 Windows drive-relative pattern은 거부한다. 이 runtime validation은 invalid
glob이 corrective-tail admission으로 오분류되거나 `Path.glob` recursion/error를 일으키지
않게 한다. Historical request hash를 보존하기 위해 tool schema v2 JSON 자체는 바꾸지
않으며 gateway와 qualifier가 같은 validator를 적용한다.

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

### `run_probe` (tool schema v3, optional)

```json
{
  "probe_id": "python-edge-cases",
  "source": "from package import api\nassert api.public_behavior() == expected"
}
```

Probe source는 repository file이 아니라 normalized tool input/CAS artifact다. `probe_id`는
같은 public task의 registered `probe_profiles`에 있어야 하며 model이 timeout, command나
image를 선택하지 않는다. Gateway는 Local backend에서 이를 실행하지 않고 dedicated
repository-free `patchloop-sandbox:py312`에서만 허용한다. Task evaluator/SWE-bench image는
사용하지 않는다. Gateway는 source AST에서 `subprocess`/`os`/`pty`/`ctypes` 계열의 직접
import, process-spawn attribute와 `eval`/`exec`/`compile`/dynamic import의 직접 call을
거부한다. Bootstrap audit hook도 흔한 alias와 indirect import를 조기에 거부하지만,
reflection·subinterpreter가 가능한 Python-level hook을 hard security boundary로 간주하지
않는다. Trusted runner가 source를 compile한 뒤 untrusted child를 한 번 fork하고, 그
child에 `no_new_privs`와 `seccomp-bpf-v1`을 설치해 fork/clone/exec, parent signal과
process trace syscall을 kernel에서 `EPERM`으로 막는 것이 executable process boundary다.

Container는 target checkout을 read-only로 mount하고 network, proxy credential, host
credential과 evaluator/private mount를 받지 않으며 read-only root와 bounded `/tmp`를
사용한다. Non-root/cap-drop/no-new-privileges, PID limit 2와 trusted-parent timeout을
적용하고 stale container를 회수한다. Mutable tag identity가 manifest-bound ID와 같은지
precheck하고, 그 exact `sha256:...` ID로 container를 create한 뒤 실제 `.Image`가
일치해야만 start한다.
`ephemeral-python-probe-v2` 호출의 `ephemeral-python-probe-result-v2` result는 exit status,
timeout, truncation, bounded stdout/stderr, exact `probe-execution-policy-v2` artifact,
`source_hash`와 invocation 시점 `worktree_diff_hash`를 가진다. Probe가 target source를
수정하거나 새 tracked/untracked file을 제출 patch에 남길 수 없어야 한다.

Probe 성공은 public hypothesis에 대한 보조 evidence일 뿐 `RegisteredCheck`,
`VerifierResult`, hidden acceptance나 SCRR bit가 아니다. `run_probe`를 호출하지 않은
run도 valid할 수 있으며 매 run에 새 test file을 작성할 의무도 없다.
Probe container는 real non-symlink `.git` checkout만 받고 `/workspace/.git`을 empty
tmpfs로 가려 repository history를 validation evidence나 solution source로 사용할 수 없다.
Clean image에 task-specific dependency가 없으므로 일부 import probe는 의도적으로 실패할
수 있다. Dependency를 추가하려면 evaluator image 재사용이 아니라 새 audited image 계약이
필요하다.

### `review_task` (tool schema v3)

```json
{
  "requirements": [
    {
      "requirement": "Public behavior named in the issue remains supported",
      "status": "verified",
      "evidence_event_sequences": [42, 47],
      "notes": "The public check and final diff cover the required behavior."
    }
  ],
  "targeted_validation": [
    {
      "kind": "registered_check",
      "event_sequence": 42,
      "outcome": "passed",
      "notes": "The current-diff visible check passed."
    }
  ],
  "residual_risks": [
    "Unobserved inputs remain for the separate evaluator"
  ]
}
```

`review_task`는 REVIEW phase에서만 성공한다. Latest mutation 뒤 current-diff registered
check가 모두 pass하고, 그 뒤의 complete `get_diff` result가 이 exact model request에
포함돼야 한다. Requirement와 validation reference는 같은 request가 실제로 볼 수 있었던
public event/result sequence만 가리키며, 최소 하나의 targeted validation은 current-diff
registered check 또는 optional probe를 인용한다. Hidden/private/evaluator artifact identity는
입력·출력에 허용하지 않는다.

성공 result는 canonical `task-review-v1` 본문, current `worktree_diff_hash`, latest mutation
sequence, source `get_diff` sequence, request artifact identity와 review content hash를
보존한다. Review input은 8,000 UTF-8 bytes, context에 제시될 전체 result는 12,000 bytes를
넘지 못한다. 따라서 다음 stateless `finish_task` request는 단순 receipt가 아니라 실제
requirement·validation·residual-risk 본문을 완전하게 다시 본다. 이것은 model 자기점검을
inspectable하게 만드는 self-attestation이며 truth verdict나 deterministic grade가 아니다.
Qualifier는 citation, 본문 재제시와 lifecycle binding을 검증하지만 review 문장의 의미적
정답 여부를 LLM으로 채점하지 않는다.

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

Tool schema v3/context v6에서는 위 조건에 다음을 더한다.

```text
AND review_task succeeded after the final get_diff on the same mutation epoch/diff
AND that review_task result was available and untruncated in this finish_task request
```

V3/V6의 `ReviewRecorded`는 source `review_task` sequence/artifact와 canonical review
content hash를 참조한다. 기존 v1/v2 lifecycle의 procedural `ReviewRecorded` 의미와
artifact hash는 바꾸지 않는다.

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

`phase-evidence-v4`의 read/search call과 successful result는 current
`worktree_diff_hash`와 full input/result CAS descriptor를 함께 기록한다. 같은 mutation
epoch에서 exact search가 다시 요청되거나 requested read range가 verified coverage union에
완전히 포함되면 underlying filesystem dispatch를 반복하지 않는다. 대신 새 action을
정상 `ToolCalled`로 세고 tool budget 1회를 소비한 뒤 다음 lifecycle을 한 transaction으로
닫는다.

```text
ToolCalled
  → LoopDetected(schema=investigation-loop-v1,
                 reason=duplicate_search|fully_covered_read,
                 enforcement=semantic-cache-replay)
  → ToolReplayed(schema=tool-replayed-v2)
```

`ToolReplayed` result는 source CAS에서 exact body를 다시 제공하며
`semantic_replay=true`를 사용한다. 동일 `action_id` idempotency만 기존
`replayed=true`와 zero-new-`ToolCalled` 의미를 유지한다. 새로운 query, uncovered/partially
overlapping range, truncated search나 첫 zero-match query는 dispatch를 허용한다.
No-progress streak 2부터 `strategy_change_required=true`지만 hard terminal threshold는
두지 않는다.

Qualifier는 context 재렌더링만 비교하지 않는다. 각 semantic replay의 correlated
`ToolCalled → LoopDetected → ToolReplayed` 순서·actor·source sequence·normalized hash·
worktree/mutation epoch·result CAS와 no-progress streak를 durable prefix에서 독립
재계산한다. Investigation loop와 semantic-cache replay는 정확히 일대일이어야 하며,
schema/semantic marker를 함께 제거해도 구조적 correlation에서 빠질 수 없다. Admission
block도 당시 model/tool counter, reserve, reason priority와 같은 correlation의
`ToolCalled` 부재를 다시 검사한다. Read admission 전에는 normal dispatch와 같은
safe-path, symlink containment, existing-file 검사를 한다. No-dispatch admission은 그
시점의 resolved in-root path와 target bytes를 `inspection-admission-preflight-v1` CAS로
동결한다. Qualifier는 이후 patch로 바뀔 수 있는 terminal workspace를 보지 않고 이
preflight CAS와 event-time worktree identity를 검사한다. Admission의 nested input,
preflight, target CAS와 replay/admission result CAS는 leak scan과
`trace-source-evidence-v4`에 실제 bytes로 결속하며, v1-v3 source-evidence schema와
hash는 바꾸지 않는다.

Nominal corrective tail은 `4 + 2 × registered_check_count` tool call과 3 model call,
한 feedback model call이다. Threshold 이후 read/search request는
`ToolAdmissionBlocked(tool-admission-blocked-v1)`로 gateway dispatch와 `ToolCalled`
전에 닫고, result/action identity는 durable하게 보존한다. 이 admission은
apply/check/diff/finish를 차단하거나 성공을 보장하지 않는다. Model이 계속 blocked
exploration을 선택하면 model-call budget으로 deterministic agent failure가 될 수 있다.
Context builder는 imminent generation 1회를 반영한 projected model-call count를
사용하고, gateway는 그 generation이 durable `ModelCalled`가 된 뒤의 실제 counter로
같은 경계를 집행한다.

V5에서는 read/search admission이 `investigation-tail-policy-v2`의 token projection을
함께 사용한다. Context builder는 generation 전 5-turn projection을
`context-build-evidence-v5`에 결속하고, gateway는 generation 뒤 durable telemetry로
4-turn projection을 다시 계산한다. Gateway cutoff가 닿으면 valid read/search를
`ToolAdmissionBlocked(schema=tool-admission-blocked-v2,
reason=token_tail_reserved)`로 `ToolCalled`와 dispatch 전에 닫는다. Apply, registered
check, diff와 finish는 이 정책의 차단 대상이 아니다. Admission payload는 observed input
source, maximum observed input, maximum positive consecutive growth,
`projected_next_input_tokens`, `projected_turns`, `reserved_tokens`,
`remaining_tokens`와 cutoff reason을 포함하고 `trace-source-evidence-v5`로 source CAS에
결속한다. Qualifier는 이 값을 preceding durable events에서 독립 재계산하고 equality
cutoff, blocked correlation의 `ToolCalled` 부재, unchanged mutation/check/diff/finish
admission과 private-token scan을 검증한다.

이 token cutoff는 nominal tail 전환일 뿐 성공이나 finish 가능 횟수를 예약하지 않는다.
Tail 전환 뒤에도 next generation의 exact input과 full 25,000 output allowance가 남은
250,000 total-token budget에 맞지 않으면 기존 `model-generation-block-v1`으로 provider
call 없이 종료한다. Trace envelope은 계속 `trace-qualification-v2`이며 V4와 earlier
source-evidence hash를 소급 변경하지 않는다.

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
    "schema_version": "model-generation-block-v1",
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

`model-generation-block-v1`은 retry-specific evidence와 terminal budget evidence를
분리한다. Retry context가 있으면 candidate hash까지 기존 D-037 조건으로 검증하고, 없으면
request와 budget/terminal binding만 검증한다. 후자의 성공은 prompt telemetry와 trace
integrity를 보존할 뿐 retry episode를 합성하지 않는다. Version 도입 전의 retry-bound block은
historical read compatibility를 유지하고, version이 없는 generic block은 새 의미로
재qualification하지 않는다.

Next-generation admission 전에 model/tool/wall counter가 이미 소진된 경우는 별도
`model-generation-block-v2`를 사용한다.

```json
{
  "type": "ModelGenerationBlocked",
  "actor": "budget-guard",
  "payload": {
    "schema_version": "model-generation-block-v2",
    "reason_code": "model_call_budget_exhausted",
    "error_code": "MODEL_GENERATION_BUDGET_EXCEEDED",
    "generation_started": false,
    "request_artifact_id": "art_...",
    "request_artifact_path": "...",
    "request_body_hash": "sha256:...",
    "requested_input_tokens": null,
    "remaining_tokens": null,
    "max_output_tokens": 25000,
    "input_token_count_calls": 0,
    "retry_context_present": false,
    "retry_candidate_content_hash": null,
    "model_calls_used": 21,
    "max_model_calls": 21,
    "tool_calls_used": 30,
    "max_tool_calls": 50,
    "wall_clock_ms": 12345,
    "wall_clock_timeout_ms": 900000,
    "total_tokens_used": 143304,
    "max_total_tokens": 250000
  }
}
```

허용 reason은 `model_call_budget_exhausted`, `tool_call_budget_exhausted`,
`wall_clock_budget_exhausted` 세 개다. Payload는 위 exact field set을 사용하고 모든
counter/limit은 bool을 허용하지 않는 nonnegative integer다. Qualifier는 block 이전의
`ModelCalled`, `ToolCalled`, `ToolSucceeded`와 `ToolFailed`에서 call, token과
`duration_ms`를 다시 계산한다. Model/tool counter는 각각 manifest 상한을 넘을 수 없고,
reason은 `model → tool → wall` 순서로 결정한다. 따라서 여러 상한이 동시에 닿아도 더 낮은
우선순위 reason으로 바꿀 수 없다. 같은 wall-clock 재계산값은 `RunResult.usage`에도
결속한다.

V2는 `actor=budget-guard`, exact `ContextBuilt` request CAS/body hash,
`generation_started=false`, input-token count 미실행, retry-context shape와 block 뒤
`FailureTagged`/`RunFailed` terminal suffix를 검사한다. Payload 전체는
`RunFailed.error_details`와 `RunResult.terminal_error.details`에 동일해야 한다. Valid
v2 block은 self-consistent qualified `agent_failure`이며 evaluator 도달, task success 또는
pilot acceptance가 아니다.

Primary mini r1 `run_6993722014bf4e3b`는 token-total guard가 아니라 20번째
`ModelCalled` 뒤의 unversioned `model_call_budget_exhausted` guard에서 멈췄다. 이
historical qualification 21/22 artifact는 v2로 소급 변경하지 않는다. D-047은 future
primary, memory-development와 core의 총 상한을 21회로 고정하고, offline에서 21번째
generation 허용과 22번째 generation 전 v2 차단을 검증했다. Corrective primary r2
`run_afd5080a77a34995`는 한 번 실행돼 official evaluator와 qualification 23/23을
통과했다. 뒤의 첫 12-run campaign은 evaluator 도달 0/12라 baseline으로 채택하지 않고,
D-048 v4 gate 뒤 새 experiment ID로 다시 측정했다. 그 D-051 campaign도 12/12 terminal과
qualification을 남겼지만 evaluator 3/12, SCRR 0/12이며 아홉 exact-request budget
failure가 있어 baseline으로 채택하지 않는다.

D-052는 future non-replay contract만 `phase-evidence-v5`, 21/50/250,000/900,
25,000 per-call output으로 바꾼다. 위 네 consumed 21/200,000 experiment identity와
각 manifest, plan, result, qualification은 immutable하다. V5 offline contract는
검증됐지만 provider execution, accepted v5 pilot, usable no-memory baseline과 core
measurement는 아직 없다.

별도 model-candidate mini r2 `run_4a9737ec91964dca` evidence는 이 version 도입 전
`phase-evidence-v2` trace로 그대로 보존한다.

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
- primary mini snapshot/medium/standard/default, fault-free와 exact Docker provenance가 일치함
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
- `model-generation-block-v2`를 선언한 trace는 strict counter/duration 재계산,
  reason 우선순위와 budget-guard actor, request/retry/terminal/result usage 결속을 만족함
- Pilot은 적어도 한 tool call을 포함해 실제 function-tool loop를 통과함

`qualified=true`는 trace artifact가 자기 outcome과 provenance를 일관되게 보존했다는 뜻이다.
Development-validation pilot acceptance는 여기에 `evaluation_reached=true`를 추가로 요구한다.
따라서 evaluator 이전 agent failure도 trace qualification은 통과할 수 있지만 development
campaign을 열지는 못한다.

r1~r3처럼 D-031 이전에 생성된 immutable Terra `development-validation-live-pilot`에는
`prompt_telemetry_version`이 없다. Qualification은 이 legacy absence 자체를 실패로
소급하지 않는다. 반면 새 primary mini development-validation pilot,
model-candidate pilot, memory-development와 core purpose는
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
Pilot과 campaign의 `harness_git_commit` equality는 exact match다. Branch가 pilot commit
뒤로 진행됐다고 descendant compatibility로 완화하지 않는다. D-050 campaign처럼 exact
pilot commit의 clean detached worktree에서 source를 import하고 host의 external
`.patchloop` runtime root를 공유할 수 있다. 이 root에는 mutable SQLite와 workspaces가
포함되므로 append-only라는 표현은 event/artifact evidence history에만 적용한다. Bridge
자체도 execution plan에 기록되고 새 execution hash와 승인을 받아야 한다. Dirty tree,
source overlay 또는 manifest commit 재기록은 허용하지 않는다.

Human review는 원래 `FailureRecord`를 수정하지 않는다.
`failure-review-v1` JSONL에 decision, failure/qualification/dataset hash와 이전 review hash를
연결해 append-only chain으로 쌓는다. Review 시작과 memory index build는 각각 현재
`source_evidence_hash`를 다시 계산한다. Memory builder는 가장 최근 decision이 `reviewed`이고
현재 source hash가 qualification과 review provenance에 모두 일치할 때만 entry를 만든다.
`memory_candidate_eligible=true`는 이 review를 시작할 수 있다는 machine label이지 index
admission이 아니다. Budget/runtime confound가 있는 candidate는 qualification을 통과해도
review disposition에서 제외할 수 있고, 같은 semantic failure의 repetition은 hidden detail을
복사하지 않은 하나의 reviewed rule로 deduplicate한다.

사람의 승인 전에는 `memory-review-proposal-v1`이 structured self-review와 deduplication
제안을 별도 artifact로 보존한다. Proposal은 campaign report/execution/suite/dataset hash,
각 source의 failure/qualification/source-evidence/public-spec/submitted-patch hash,
agent-visible event sequence, semantic group membership과 candidate/hold disposition을
결속한다. Campaign의 task-failure candidate와 budget-confounded exclusion을 정확히 모두
포함해야 하며, 한 source를 둘 이상의 group에 넣을 수 없다. Rule text에는 raw diff, 코드
본문, private/hidden/reference marker를 넣지 않는다.

```yaml
schema_version: memory-review-proposal-v1
proposal_id: proposal_dev_no_memory_v4_20260730_r1
producer:
  kind: maintainer-assisted
  method: codex-public-trace-review-v1
campaign:
  report_path: reports/memory-development/dev-no-memory-v4-20260730-r1.json
  report_sha256: sha256:...
  experiment_id: dev-no-memory-v4-20260730-r1
  execution_hash: sha256:...
  suite_hash: sha256:...
  dataset_manifest_hash: sha256:...
sources:
  - failure_id: fail_...
    run_id: run_...
    semantic_group_id: exception-origin-state-conflation
    disposition: candidate
groups:
  - semantic_group_id: exception-origin-state-conflation
    relation: semantic-duplicate
    disposition: candidate
    rule: ...
excluded_runs:
  - run_id: run_...
    reason: exact_request_budget_exceeded
human_review_status: pending
content_hash: sha256:...
```

`patchloop memory validate-review <proposal.json>`는 위 binding과 current source hash를
재계산하고 leak/code-shaped marker를 fail-closed로 검사한다. 발견 문자열은 오류에
재출력하지 않는다. 이 명령은 read-only이며 `failure-review-v1` history를 쓰거나 index를
build하지 않는다. Proposal의 `candidate`는 검토할 가치가 있다는 뜻이고 `hold`는 공개
증거만으로 causal rule을 승인하기 어렵다는 뜻이다. 둘 다 human `reviewed` decision이나
index admission이 아니다.

Producer는 `maintainer-assisted`와 `model-self-review`를 구분한다. 후자는 exact model ID와
sanitized response artifact hash가 모두 있어야 하며, 전자는 model response provenance를
주장할 수 없다. 따라서 maintainer가 공개 trace를 검토해 만든 proposal은 PatchLoop agent가
post-run self-review를 실행했다는 evidence가 아니다.

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

## 12. D-062 public review and corrective evidence

Corrective manifest는 `PublicReviewContract`를 반드시 포함한다. 각 requirement는
`req-<12 hex>` stable ID, `source=issue.description`, 최대 1,000자의 normalized exact public
excerpt를 가진다. Loader, manifest builder, context builder와 qualifier가 모두 public source
provenance와 private-marker leak scan을 재검증한다. Private spec, hidden check, reference patch나
credential marker는 올바른 self-hash를 가져도 거부된다.

Corrective execution plan의 `runtime_contract`는 schema `corrective-runtime-contract-v1`, exact
`tool_schema_version=v4`, `context_policy_version=phase-evidence-v7`, system-prompt/tool-schema
content hash와 `harness_git_commit`을 가진다. 이 block은 corrective execution hash에 포함된다.
`RunManifest`는 corrective purpose와 v4/v7/public-review 세 요소를 함께 강제한다. AgentRunner는
start와 resume 모두 plan block을 exact 비교하고, qualifier는 runner가 남긴 단 하나의
`RunStarted`에서 task ID, artifact role, top-level descriptor binding, JSON media type, CAS path,
content hash와 bytes를 검증한 뒤 exact runtime document를 재구성한다.

`review_task` v4 input은 contract requirement ID를 정확히 한 번씩 평가해야 한다. Unknown,
duplicate, missing ID는 거부하고 `partially_verified`/`unverified` 항목은 같은 requirement ID를
가리키는 residual risk를 요구한다. 결과는 `task-review-v2`와 contract content hash를 CAS에
저장하며 deterministic correctness claim은 항상 false다.

V7 rejected-patch evidence는 `rejected-mutation-retry-v2`와
`patch-source-snapshot-v1`을 사용한다. 다음 apply outcome 전까지 pending이고, 성공/거부 뒤
다음 request에서 null이어야 한다. 첫 apply 뒤 같은 response의 call은
`tool-admission-blocked-v3`/`turn-mutation-barrier-v1`로 기록하며 `ToolCalled`가 없어야 한다.
V7 source evidence version은 `trace-source-evidence-v7`이고 qualification envelope은 계속
`trace-qualification-v2`다.

### Consumed D-062 execution boundary

`dev-no-memory-corrective-pilot-20260731-r1`의 execution hash
`sha256:464a6eca2597698ca35caa4d7c97173f1af792daec042c36d81b5b8189ae4031`는 정확히 한 번
소비됐다. Schedule의 첫 row인 HF Hub `run_0ccfc8fd359a4785`만 terminal이며, original
qualification failure 뒤 `QualificationFailureHalt`가 나머지 PDM과 pyfakefs row를
not-started로 닫았다. 이 suite, hash와 experiment ID는 재실행하거나 continuation하지 않는다.

HF run의 provider response 33개는 모두 completed였고 usage는 총 875,908 token, 계산 비용
`$0.8408853`이다. 마지막 exact request는 남은 token으로 input과 25,000-token response
allowance를 함께 예약할 수 없어 provider 호출 전에 차단됐다. Candidate 일곱 개는
`git apply` preview에서 모두 거부됐으므로 `PatchPrepared=0`, `PatchApplied=0`, evaluator
arrival=0이다. Read/search 30개도 `evidence_saturated`로 dispatch 전에 차단됐다.

Original experiment result, campaign journal과 original qualification artifact는 append-only
source evidence로 보존하며 덮어쓰지 않는다. 후속 분석에서 드러난 qualifier의
v5-vs-v6/v7 nominal-reserve drift는 original gate를 true로 바꾸지 않는다.

`trace-qualification-correction-v1` writer는 승인된 original qualification hash와 source
evidence hash를 요구하고, source를 재계산 전후 검증하며 canonical qualification bytes가
변하지 않았음을 다시 확인한다. Corrected 전체 semantics/hash, original failed check IDs,
clean harness commit, package version, reason과 timestamp를 content-derived `qcor_<sha256>`에
결속해 `qualification-corrections/v1/<run-id>/` 아래 exclusive-create한다. 동일 semantics는
exact-idempotent이고 기존 path의 다른 bytes는 덮어쓰지 않고 거부한다.

D-062 correction `qcor_8b6ff812...4870b6`는 original failed checks
`investigation_evidence`와 `investigation_lifecycle`를 corrected failed check 0개로
재계산했고 corrected trace qualification은 통과했다. 그러나 original campaign gate와 HF
task outcome은 그대로이므로 이 run을 SCRR 또는 no-memory baseline으로 세지 않는다.

## 13. Phase-evidence-v8 saturation context

V8 manifest는 exact `tool_schema_version=v4` / `context_policy_version=phase-evidence-v8`
pair와 `PublicReviewContract`를 요구한다. 이 pair는 historical corrective purpose의 v4/v7
pair를 대체하거나 완화하지 않는다. Generic V8은 mock provider와 experiment context 부재만
허용한다. 유일한 live exception은 exact
`memory-development-no-memory-saturation-pilot` purpose이며 OpenAI provider, frozen HF Hub
task, approved execution plan과 `corrective-runtime-contract-v2`가 모두 필요하다.

V8 request의 `phase_contract`는 `phase-contract-v3`이고 다음 exact object를 포함한다.

```json
{
  "read_search_policy": {
    "schema_version": "read-search-policy-v1",
    "policy_version": "evidence-saturation-v1",
    "admitted": false,
    "reason_codes": ["evidence_saturated"],
    "semantic_replay_count": 6,
    "semantic_replay_threshold": 6,
    "mutation_epoch_sequence": null
  }
}
```

`reason_codes`는 `investigation-tail-policy-v2.block_reasons`의 기존 순서를 보존하고, active
epoch의 semantic replay가 6개 이상이면 마지막에 `evidence_saturated`를 한 번 추가한다.
`admitted`는 reason이 없을 때만 true다. Saturation-only request는 read/search action만
제거하고 `run_probe`를 유지한다. Tail reason이 하나라도 있으면 read/search/probe를 모두
제거한다.

`context-build-evidence-v8`은 `read_search_policy`를 byte-for-byte mirror하고,
`ContextBuilt`는 다음 scalar/list mirror를 기록한다.

- `investigation_read_search_admitted`
- `investigation_read_search_reason_codes`
- `investigation_semantic_replay_count`
- `investigation_semantic_replay_threshold`
- `investigation_saturation_mutation_epoch_sequence`

Qualifier의 V8-only `saturation_context_contract`는 runtime context builder를 호출하지 않고
event prefix에서 mutation epoch, semantic replay count, threshold, tail reason과 그 결과의 action
filtering을 독립 재계산한다. 일반적인 tool-result presentation availability는 기존
`investigation_evidence`의 exact context rebuild와 CAS 검사에 결속하며 별도의 두 번째 renderer로
주장하지 않는다. Rendered request, context evidence와 `ContextBuilt` mirror가 모두 일치해야
통과한다. `corrective-runtime-contract-v2`의 prompt/tool/context bytes와 CAS,
`trace-source-evidence-v8`도 별도로 결속한다. V7은 계속 `phase-contract-v2`,
`context-build-evidence-v7`, `corrective-runtime-contract-v1`과 기존 source hash를 사용한다.

D-064의 `v8-saturation-context-v1` diagnostic은 qualification과 별도다. Qualification은
모든 V8 context가 독립 재계산과 CAS 검사를 통과했는지를 판정한다. Diagnostic은 최소 한
saturated context에서 read/search가 제거됐고, 그 뒤 successful `PatchApplied`와 첫 후속
context가 존재할 때 `semantic_replay_count=0`, 새 `mutation_epoch_sequence`,
`evidence_saturated` 제거가 확인돼야 pass다. Saturation 또는 reset opportunity가 자연 발생하지
않으면 inconclusive이고 자동 재실행하지 않는다. 이 purpose의
`memory_candidate_eligible`는 항상 false다.

## 14. Phase-evidence-v9 review evidence

V9 manifest는 exact `tool_schema_version=v4` / `context_policy_version=phase-evidence-v9`,
`PublicReviewContract`, `SYSTEM_PROMPT_V6`와 `corrective-runtime-contract-v3`를 요구한다.
Offline V9은 `review_evidence_validation=True`, mock provider, experiment 부재의 exact 조합만
허용한다. Replay, arbitrary provider, experiment context와 다른 validation mode 결합은
fail closed하며 RunManifest도 v4/v9를 mock/no-experiment 또는 아래 exact live exception으로만
허용한다. 유일한 live selector는 exact
`memory-development-no-memory-review-evidence-pilot` purpose와 OpenAI provider 조합이다. Suite
파일만으로 실행 capability가 생기지 않으며 approved execution plan이 없으면 start/resume가
fail closed한다.

REVIEW readiness가 충족된 request에는 top-level `review_evidence`가 반드시 존재한다.

```text
schema_version == review-evidence-v1
pinning_active == true
worktree_diff_hash == checkpoint/current workspace diff hash
mutation_event_sequence == latest successful PatchApplied
passing_check_event_sequences == required current-diff passing checks
source_get_diff_sequence == latest eligible current-diff final get_diff
citable_event_sequences == passing_check_event_sequences + [source_get_diff_sequence]
incomplete_event_sequences == []
```

`pinned_results`는 위 citable sequence의 full, untruncated current-diff `ToolSucceeded` result를
담는다. 같은 sequence가 recent event에도 있으면 한 번만 execution context에 제시한다. Missing
event, unavailable artifact, truncation, wrong diff, wrong order 또는 forged citation list는
recovery/qualification failure다.

V9 `review_task`의 requirement evidence와 targeted validation은 오직
`citable_event_sequences`를 인용할 수 있다. Targeted validation은
`passing_check_event_sequences` 중 하나를, source diff는 exact
`source_get_diff_sequence`를 사용해야 한다. 위반은 `review-citation-error-v1` details와 함께
rejected result로 남는다. Details는 private/hidden assertion을 포함하지 않고 다음 public
field만 사용한다.

```text
schema_version, stage, reason, invalid_event_sequence,
citable_event_sequences, passing_validation_event_sequences,
source_get_diff_sequence
```

같은 active mutation epoch에서 failed `review_task` 세 건은 recoverable limit을 넘는다. Runner는
네 번째 generation을 시작하지 않고 structured terminal failure를 남긴다. 새 successful patch
뒤에는 이전 review failure를 세지 않는다. `review_evidence_context_contract`는 V9 request,
`context-build-evidence-v9`, `ContextBuilt` mirror, artifact CAS와 independently rebuilt anchor를
모두 비교한다. Source evidence schema는 `trace-source-evidence-v9`이며 V1-V8 artifact는
소급 변경하지 않는다.

D-067 suite 계약은 exact HF Hub task 한 개, no-memory 한 번,
`gpt-5.4-mini-2026-03-17` medium/standard/default, 60 model call, 100 tool call,
1,200,000 total token, 1,800초, per-call output 25,000이다. Dated standard pricing에서
authorization reserve는 `(1,200,000 + 25,000) × $4.50/M = $5.5125`, suite cap은 `$6`다.
Checked-in source YAML의 `live_cost_approved=false`, `approved_execution_hash=null`,
`pilot_run_id=null`은 재실행 capability가 없는 source boundary로 유지한다. 별도 승인 plan의
execution hash는 한 번 소비됐으며, 이 tuning-only run의 comparison denominator와 memory
admission은 항상 false다.

D-068 correction은 V9 `submission_lifecycle.complete_source_in_context`를 판정할 때 request
artifact CAS를 먼저 검증하고, durable `ToolSucceeded` event의 `result_artifact` descriptor와
bytes에서 final `get_diff` anchor를 독립 재구성한다. V9에서는 source sequence가 recent events에
없고 `review_evidence.pinned_results`, nested `pinned_tool_results`와 top-level `tool_results`에
각각 정확히 한 번 존재해야 한다. 모든 sequence는 JSON integer여야 하며 float/bool alias,
중복, truncation, wrong diff, descriptor/hash/size/path tamper는 fail closed한다. V1-V8은 기존
recent-event-only semantics를 유지한다.

과거 qualification 해석을 고칠 때 canonical qualification이나 campaign result를 덮어쓰지
않는다. `trace-qualification-correction-v1`은 original qualification hash, source evidence hash,
source/correction harness commit과 corrected semantics를 결속해
`qualification-corrections/v1/<run-id>/<qcor-id>.json`에 content-addressed append-only artifact로
기록한다. 동일 semantic body의 반복 호출은 같은 correction ID와 최초 timestamp를 반환해야
한다. Corrected trace integrity는 original campaign gate, task outcome, SCRR, comparison
eligibility 또는 memory admission을 소급 변경하지 않는다.

## 15. Phase-evidence-v10 public coverage review

D-069는 D-067의 공개 issue를 사후 정답으로 바꾸지 않고, 넓은 범위의 공개 requirement를
검토 가능한 단위로 분해하는 별도 offline 계약이다. `all`, `every`, `each` 같은 단어를
runtime NLP로 추측하지 않는다. Task maintainer가 `public-review-contract-v2`에 각
requirement의 `coverage_targets`를 명시하며, schema는 모든 requirement에 target이 하나 이상
있고 전체 target 수가 20개 이하이며 `coverage_target_id`가 전역에서 유일한지 검사한다.
V1 contract에 target field를 추가하는 것은 허용하지 않으므로 기존 V1 serialization과 hash는
그대로 유지된다.

```yaml
schema_version: public-review-contract-v2
requirements:
  - requirement_id: req-...
    source: issue.description
    source_excerpt: Ensure context is preserved through every metadata access path.
    coverage_targets:
      - coverage_target_id: cov-...
        description: Inspect one declared metadata access path after the patch.
        evidence_kind: current_diff_inspection
        path: src/package/api.py
        anchor: "def get_metadata("
      - coverage_target_id: cov-...
        description: Validate the declared endpoint behavior.
        evidence_kind: passing_validation
        check_ids: [upstream-regression]
```

Target ID는 parent requirement ID와 normalized description, evidence kind, path/anchor 또는
정렬된 check ID를 canonical JSON으로 hash해 `cov-<12 hex>`로 만든다. 두 evidence kind의
shape는 섞을 수 없다.

- `current_diff_inspection`: public task의 allowed path와 한 줄 exact anchor가 필요하다. Latest
  successful patch 뒤, current worktree diff hash에 결속된 complete `read_file` result가 exact
  path와 anchor를 실제로 포함해야 한다. 또한 anchor는 model context 생성 전에 Git public base
  revision의 해당 path에 이미 존재해야 한다. Ordered target/path/anchor와 base file hash는
  `public-review-base-provenance-v1` CAS에 기록되며 start, resume, qualification과
  `trace-source-evidence-v10`이 같은 bytes를 검증한다.
- `passing_validation`: non-empty, sorted, unique check ID가 필요하며 모두 public task의 visible
  check여야 한다. Current diff에 결속된 advertised passing `run_check` event만 인용할 수 있다.

V10 manifest는 exact `tool_schema_version=v5` / `context_policy_version=phase-evidence-v10`와
`public-review-contract-v2`를 함께 요구한다. Generic selector는
`coverage_review_validation=True`, mock provider, experiment context 부재의 조합만 허용한다.
유일한 live exception은 `coverage_review_live_pilot=True`, exact
`memory-development-no-memory-coverage-review-pilot` purpose와 OpenAI provider의 논리곱이다.
Replay, arbitrary experiment와 mixed validation mode는 fail closed한다. Runtime은
`SYSTEM_PROMPT_V7`, `TOOL_SCHEMAS_V5`,
`corrective-runtime-contract-v4`, `context-build-evidence-v10`과
`phase-contract-v4`를 사용한다. Checked-in D-070 suite와 no-call preflight만으로는 live
capability가 생기지 않는다. Clean execution hash에 대한 별도 invocation approval이 필요하다.

REVIEW request의 `review-evidence-v2`는 contract 순서 그대로
`coverage_target_event_sequences`를 제공한다. Target evidence를 먼저 순서대로 deduplicate한 뒤
current-diff passing checks와 final `get_diff`를 더해 `citable_event_sequences`를 만든다. 모든
pinned result는 complete/untruncated여야 하고 event payload, result artifact descriptor와 실제
CAS bytes가 같은 diff/path/check를 가리켜야 한다. `run_check`의 pass/check/timeout/truncation과
`read_file`의 path/content/diff identity도 exact 비교하므로 event metadata 재표시로 실패 또는 stale
결과를 승격할 수 없다. JSON object key 순서는 의미로 사용하지 않고 exact target key membership을
검증한 뒤 target/review rows와 citation은 contract 순서로 canonicalize한다.

Tool v5 `review_task`는 모든 requirement와 coverage target을 정확히 한 번씩 제출한다. Target
status는 `verified`, `partially_verified`, `unverified` 중 하나이며 target에 광고된 exact evidence
sequence만 인용한다. Gateway는 evidence kind를 독립 검증하고 parent requirement의 status와
evidence를 child target의 ordered roll-up과 정확히 맞춘다. 결과는 `task-review-v3`,
`task-review-result-v3`와 다음 `public-review-coverage-v1` 결정을 CAS에 보존한다.

```json
{
  "schema_version": "public-review-coverage-v1",
  "authoritative_coverage_target_ids": ["cov-..."],
  "verified_coverage_target_ids": [],
  "unresolved_coverage_target_ids": ["cov-..."],
  "coverage_complete": false,
  "ready_for_submission": false,
  "deterministic_correctness_claimed": false
}
```

Valid partial review는 실패로 버리지 않고 `ReviewRecorded`/tool result와 artifact로 남긴다. 다만
runner는 즉시 `REVIEW → IMPLEMENT`로 전이하고 phase contract에
`public_review_coverage_incomplete`와 unresolved target ID를 제시한다. 이후 agent는 필요한
public inspection/validation을 수행하고 current final diff evidence를 본 뒤 review를 다시 제출해야 한다.
`finish_task`는 current mutation/diff에 결속된 `task-review-v3`에서 authoritative target 순서,
verified target 순서, empty unresolved list와 `coverage_complete=true`가 모두 정확히 일치할 때만
accept한다. Crash/resume 뒤에도 incomplete review를 complete로 합성하거나 target evidence를
다른 mutation epoch에서 재사용하지 않는다.

Qualifier의 V10-only coverage checks는 request/context/CAS에서 target mapping을 독립 재구성하고,
partial-review corrective transition과 submission ordering, terminal/recovery source를 검증한다.
`targeted_validation`과 residual-risk row도 request-bound CAS와 public contract에 맞는지 재검증하고,
tool v5 probe 사용 시 기존 self-validation lifecycle을 동일하게 요구한다. Complete coverage review,
accepted submission과 evaluation이 없는 generic terminal trace는 gate를 닫지 못한다. Source schema는
`trace-source-evidence-v10`이다. 이 검증은 evidence와 lifecycle integrity에 대한 것이며 target
문구의 의미적 충분성이나 code correctness를 LLM으로 채점하지 않는다.

Checked-in 예시는
`experiments/review-contracts-v2/hf-hub-xet-endpoint-propagation.yaml`이다. D-067에서 사용한
공개 issue clause를 네 code-path inspection target과 네 visible-validation target으로 표현하지만,
새 live suite나 D-067 재실행 권한이 아니다. 이 V2 sidecar는 original D-067 manifest, run,
qualification/correction, hidden failure, SCRR와 frozen dataset을 변경하지 않는다.

## 16. Phase-evidence-v11 structured coverage rejection

V11 manifest는 exact `tool_schema_version=v6` / `context_policy_version=phase-evidence-v11`,
`public-review-contract-v2`, `SYSTEM_PROMPT_V8`와 `corrective-runtime-contract-v5`를 함께
사용한다. Factory의 `coverage_rejection_validation=True`는 mock/no-experiment에서만
선택 가능하며 replay, OpenAI, experiment context와 mixed validation mode를 거부한다.
V10 v5/v10 pair와 D-070 live exception은 기존 contract/hash로 계속 해석한다.

Tool v6의 target-specific citation rejection result는 다음 exact public shape를 사용한다.

```json
{
  "error_code": "COVERAGE_CITATION_REJECTED",
  "error_details": {
    "schema_version": "coverage-citation-error-v1",
    "stage": "review",
    "reason": "target_evidence_not_allowed",
    "coverage_target_id": "cov-...",
    "requirement_id": "req-...",
    "submitted_event_sequences": [169],
    "allowed_event_sequences": [],
    "invalid_event_sequences": [169],
    "evidence_kind": "current_diff_inspection",
    "required_evidence": {
      "tool": "read_file",
      "path": "src/package/api.py",
      "anchor": "def get_metadata("
    },
    "mutation_event_sequence": 120,
    "worktree_diff_hash": "sha256:...",
    "source_get_diff_sequence": 165,
    "guidance": "public bounded remediation guidance"
  }
}
```

`reason`은 `target_evidence_not_allowed`, `verified_target_evidence_mismatch` 또는
active feedback 뒤 stale sequence만 다시 제출한 `fresh_target_evidence_required`다. `passing_validation` target의
`required_evidence`는 `{"tool":"run_check","check_ids":[...]}`다. Sequence는 positive
JSON integer의 unique list이며 submitted/allowed에서 invalid list를 결정적으로 재계산한다.
Error event와 result CAS, request input CAS의 arguments/execution context, target-specific
`review-evidence-v2` mapping, mutation/diff/source-diff identity와 public contract가 exact
match해야 한다. JSON object key order는 target identity가 아니며 exact target-key membership을
확인한 뒤 contract order로 canonicalize한다.

유효한 active rejection은 다음 request의 top-level에
`coverage-rejection-feedback-v1`로 복원된다.

```text
source_call_sequence, source_failure_sequence, action_id, error_code
reason, coverage_target_id, requirement_id
submitted_event_sequences, allowed_event_sequences, invalid_event_sequences
evidence_kind, required_evidence
mutation_event_sequence, worktree_diff_hash, source_get_diff_sequence, guidance
```

`context-build-evidence-v11`은 feedback inclusion, canonical content hash, input/result CAS
descriptor와 source-through sequence를 보존한다. 별도 `worker-claim-evidence-v1`은 V11
model-request CAS top-level과 `ContextBuilt` payload에 exact mirror되며 claim ID, owner ID,
PID, hostname, claimed time, prior status와 reclaimed flag를 포함한다.
Active source `ToolFailed`는 bounded `recent_events`에서 제거하여 top-level feedback만
authoritative하게 한다. Feedback은 같은 mutation에서 corrective read/check/diff를 수행해도
유지된다. Source와 recovery/clearing tool call은 request CAS뿐 아니라 `ModelCalled` response CAS의
exact `{name, action_id, arguments}` 선언에도 결속된다. Source rejection의
call/input/request/result를 먼저 완전 재검증한 뒤, 그 exact
visible feedback과 build evidence를 실제 request CAS에서 받은 complete `review_task` 또는
correlated `ToolCalled → PatchPrepared(patch-mutation-intent-v1 CAS) → ToolSucceeded →
PatchApplied`를 가진 새 mutation만 제거할 수 있다. Complete review는 call arguments의 모든
requirement/target row, canonical target mapping, 실제 anchor/check result CAS와 roll-up을 다시
계산해야 한다. Valid partial review와 orphan/self-consistent-forged clearing event는 feedback을
제거하지 않는다. Feedback이 inactive인 후속 `ContextBuilt`도 request CAS의 active worker claim과
exact mirror되어야 한다.

연속 rejection에서는 각 source request가 직전 durable prefix의 active feedback과 일치해야 한다.
후속 recovery/read/check/diff request는 과거 rejection이 아니라 최신 unresolved rejection을 rehydrate한다.
첫 rejection 뒤 fresh runner reclaim은 필수지만, 그 runner가 stale retry로 다시 거절된 경우 새 worker를
한 번 더 만들지 않고 같은 durable claim으로 복구를 계속할 수 있다. 첫 rejection과 fresh request 사이의
run event는 `state-store`의 `CheckpointSaved`만 허용하며 old-worker model/tool activity는 fail closed한다.
`passing_validation` target이 여러
fresh check sequence를 광고하면 complete review는 그 전체를 제출하고 runtime/qualifier는 batched
single-generation call을 포함한 각 call/result provenance를 독립 검증한다.

V11 qualifier는 V10 public-coverage checks에
`coverage_rejection_recovery_contract`를 추가한다. 적어도 하나의 non-vacuous
structured rejection, source call/result CAS, 첫 rejection에 결속된 restart worker claim 이후의 exact feedback,
target에 맞는 후속 current-diff evidence, 그 뒤의 content-valid refreshed `get_diff`, complete review,
feedback clearing, submission/evaluation와
single-mutation lifecycle을 independently rebuild한다. Target/sequence/required evidence,
result descriptor/bytes, resumed context, source/recovery tool call, 최초/갱신 diff bytes,
clearing request feedback/build mirror, orphan success/mutation 또는 duplicate mutation tamper는
fail closed해야 한다. Source evidence는 `trace-source-evidence-v11`이고 qualification
envelope은 `trace-qualification-v2`를 유지한다. Mock/non-campaign run의 overall
qualification은 campaign provenance 부재로 false일 수 있으며, 그 경우에도 전용 check
pass와 separate local evaluator result를 별도로 보고한다.

## 17. D-072 exact V11 live-readiness contract

D-072의 `patchloop.agent.coverage_rejection`과 `patchloop.evals.coverage_rejection` 모듈 분리는
D-071 함수의 canonical input/output, exception, schema version, artifact bytes와 qualification check
ID를 바꾸지 않는 의미 보존 refactor다. `patchloop.agent.context`와
`patchloop.evals.qualification`은 기존 import surface를 유지한다. Historical V10/V11 run은 원 source
version으로 해석하며 이 이동을 이유로 재qualification하지 않는다.

Exact live-readiness suite는 다음 tuple 전체를 요구한다.

```yaml
schema_version: experiment-v2
experiment_id: dev-no-memory-coverage-rejection-v11-pilot-20260802-r1
purpose: memory-development-no-memory-coverage-rejection-pilot
tasks:
  - tasks/dev-train/hf-hub-xet-endpoint-propagation/public.yaml
conditions: [no_memory]
repetitions: 1
model: openai
model_id: gpt-5.4-mini-2026-03-17
reasoning_effort: medium
reasoning_mode: standard
service_tier: default
max_output_tokens: 25000
budget:
  max_model_calls: 60
  max_tool_calls: 100
  max_total_tokens: 1200000
  wall_clock_timeout_seconds: 1800
seed: 20260723
live_cost_approved: false
approved_execution_hash: null
pilot_run_id: null
estimated_cost_usd: 5.5125
cost_limit_usd: 6
```

Purpose와 experiment ID, exact one-row task/schedule/model/budget/pricing, dataset/image/review sidecar,
v6/v11/runtime-v5와 clean harness identity 중 하나라도 다르면 start/resume와 qualification은 fail
closed한다. Generic V11은 `coverage_rejection_validation=True` + mock + no experiment에서만 허용되고,
위 exact purpose의 OpenAI pair만 exact live exception이다. Checked-in suite,
`live_cost_approved=false`, null hash/run ID는 live capability 또는 비용 승인이 아니다.

`coverage_rejection_recovery_contract`의 live-pilot 판정은 rejection occurrence와 trace integrity를
분리한다.

```text
rejection_count == 0
  => check may pass, exercise_status=inconclusive,
     exercise_reason=rejection_not_observed

rejection_count > 0
  => every observed structured public rejection and every source/recovery/
     refreshed-diff/clearing request-response-tool-result CAS must verify
  => any failed sequence makes check and live gate fail
```

따라서 `v11-coverage-rejection-live-pilot-gate-v1`은 exact row의 evaluator arrival, trace
qualification, public coverage lifecycle과 `exercise_status in {passed, inconclusive}`를 요구하지만
task success를 요구하거나 comparison denominator/memory admission을 열지 않는다. `failed`는 항상
gate failure다. Live-pilot branch는 rejection이 생겨도 worker restart를 필수로 만들지 않는다.
Provider process hard kill, stale `RUNNING` reclaim과 fresh-worker request를 live로 검증하는 fault
exercise는 별도 suite/hash/비용 승인 아래 후속으로 수행한다.

## 18. D-073 consumed D-072 result contract

Approved execution hash
`sha256:12fb0fb8a02ffe464555bd23125fae18deb6e52e6b6448a482243c036cce080d`는 exact D-072 tuple로
정확히 한 번 소비됐다. Experiment ID는 source-level hard-immutable set에 들어가고 승인 hash는 그
consumed ID의 portable evidence에 결속된다. Start/resume/preflight는 같은 ID의 재사용을 거부하며,
동일한 execution payload는 experiment ID를 포함하므로 같은 hash로도 다시 승인될 수 없다. Original result, campaign journal,
qualification과 completion gate는 append-only이고 D-073 portable evidence는 이 raw evidence를
교체하거나 outcome을 다시 계산하지 않는다.

`run_e2132144a8774b05`의 immutable contract realization은 다음과 같다.

```text
completion gate = passed
trace qualification = 36 / 36
official evaluator reached = true
coverage rejection count = 0
coverage rejection exercise = inconclusive / rejection_not_observed
outcome = task_failure
SCRR = false
verdicts = hidden fail, regression/scope/safety pass
usage = 797,862 input + 64,465 output = 862,327 token
        35 model call, 57 tool call, 369,385 ms, $0.841833
budget binding = none
rejected-patch retry = 17 candidates / 17 verified retries
saturated contexts = 17
PatchApplied = 1
```

`rejected-patch retry`는 mutation preview rejection의 candidate-context 복구 계약이고
`coverage rejection`은 `review_task`의 `coverage-citation-error-v1` 계약이다. 전자는 17회
관찰됐지만 후자는 0회이므로 `coverage_rejection_recovery_contract`는 integrity-pass이면서 exercise는
inconclusive다. Saturation과 patch count도 coverage recovery 또는 fresh-worker restart를 대체하지
않는다. Task success는 readiness gate 조건이 아니므로 gate pass와 hidden failure가 동시에 존재할 수
있다. 이 row는 comparison denominator와 memory admission에서 제외되고 core run으로 승격되지 않는다.

D-073 seal artifact는
`reports/live-pilot/dev-no-memory-coverage-rejection-v11-pilot-20260802-r1.json`이다. Seal 생성은 raw
artifact를 변경하지 않고 provider를 추가 호출하지 않으며 추가 model cost는 0이다.

## 19. D-074 generic no-memory readiness contract

이 절은 D-069~D-073 artifact나 판정을 다시 해석하지 않고, 다음 generic no-memory 실행의 경계를
명시한다. 현재 baseline/core의 generic runtime pair는 다음과 같다.

```text
tool_schema_version = v2
context_policy_version = phase-evidence-v5
task-specific public-review-contract-v2 sidecar = absent
coverage_review_validation = false
coverage_rejection_validation = false
```

`memory-development-no-memory-review-evidence-pilot`,
`memory-development-no-memory-coverage-review-pilot`과
`memory-development-no-memory-coverage-rejection-pilot`은 consumed diagnostic purpose다. Generic
`memory-development-no-memory`와 `core` loader는 이 purpose의 V9/V10/V11 runtime이나 HF Hub
sidecar를 선택해서는 안 된다. 이 diagnostic lane의 pass, fail 또는 inconclusive 판정은 generic
baseline preflight의 prerequisite가 아니다.

현재 `experiments/dev-no-memory-v5.template.yaml`과 `experiments/core.template.yaml`의
`21/50/250,000/900` budget은 `stale-unvalidated`다. Exact generic tuple과 fair budget이 새로
결정되고 같은 tuple을 사용한 development readiness evidence에 결속되기 전에는 이 값을 live
execution plan으로 승인하지 않는다. 새 readiness panel의 exact task list와 budget은 별도 checked-in
contract에서 고정하며, 그 gate는 다음 논리곱을 사용한다.

```text
expected diverse development rows are complete
AND every row is terminal and trace-qualified
AND every row reaches the official evaluator
AND infrastructure_error_count == 0
AND qualification_error_count == 0
AND diagnostic_error_count == 0
AND budget_terminal_count == 0
```

`task_successes`와 SCRR는 별도 관찰값이며 위 gate의 항이 아니다. Hidden failure는 readiness failure가
아니고, baseline freeze 전 task-specific prompt/tool/review correction의 입력으로 사용하지 않는다.
Gate가 통과하면 model/prompt/tool/context/budget/container/evaluator tuple을 동결한 뒤 별도 승인으로
no-memory baseline을 수집한다. Provider hard kill, stale `RUNNING` reclaim과 fresh-worker recovery는
이 gate에 합치지 않고 별도 reliability suite에서 판정한다.

## 20. D-075 exact generic V2/V5 readiness contract

새 purpose는 `generic-baseline-readiness`이고 exact experiment ID는
`generic-baseline-readiness-v2v5-20260802-r1`이다. Loader는 다음 ordered task list, single
`no_memory` condition과 repetition 1을 요구한다.

```text
tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes/public.yaml
tasks/dev-validation/moto-query-scanned-count/public.yaml
tasks/dev-train/pyfakefs-makedirs-parent-traversal/public.yaml
tasks/dev-train/hf-hub-xet-endpoint-propagation/public.yaml
```

첫 두 row의 dataset role은 `development-validation`, 뒤 두 row는 `memory-development`다. Purpose의
allowed-role contract는 이 두 role의 exact set이며 task order나 identity, role, package hash가
달라지면 preflight/start/qualification이 fail closed한다. 이 혼합 panel은 dataset split을 바꾸지
않고 report에서 calibration-only로 제외한다.

Exact model/runtime tuple은 다음과 같다.

```text
model/provider = gpt-5.4-mini-2026-03-17 / openai
reasoning = medium / standard
service tier = default
system prompt = SYSTEM_PROMPT_V3
tool/context = v2 / phase-evidence-v5
transport_max_retries = 0
public review sidecar = absent
fault = none
condition = no_memory
max output = 25,000
run budget = 40 model / 100 tool / 850,000 total token / 1,800 seconds
```

`ModelConfig.transport_max_retries`는 exact JSON integer 0 또는 historical `None`만 허용한다.
Readiness manifest는 0을 필수로 요구하고 model adapter는 `OpenAI(max_retries=0)`을 사용한다. 이는
SDK transport retry만 끄며 constrained tool gateway, rejected-patch retry, idempotent action recovery와
worker resume 계약은 그대로 유지한다. Historical `None`은 `OpenAI()`와 기존 SDK default를 유지하고
serialization에서 field를 생략한다. 따라서 이 field 추가만으로 historical suite/manifest hash를
바꾸지 않는다.

Execution plan의 `runtime_contract`는 다음 canonical document다.

```json
{
  "schema_version": "generic-baseline-runtime-contract-v1",
  "tool_schema_version": "v2",
  "context_policy_version": "phase-evidence-v5",
  "system_prompt_hash": "sha256:<SYSTEM_PROMPT_V3 bytes>",
  "tool_schema_hash": "sha256:<canonical TOOL_SCHEMAS_V2 bytes>",
  "transport_max_retries": 0,
  "harness_git_commit": "<clean commit>"
}
```

Preflight, manifest factory, paid start/resume comparator와 qualifier는 suite를 신뢰하지 않고 위 document와
task/schedule/model/budget/environment identity를 다시 구성한다. V10/V11 runtime이나
`public-review-contract-v2`가 나타나거나 retry field가 누락·변조되면 provider call 전에 거부한다.
Runner는 같은 schema name을 raw trace object에 재사용하지 않는다. Unique `RunStarted`의
`generic-baseline-runtime-evidence-v1` artifact는 exact `SYSTEM_PROMPT_V3` bytes,
`TOOL_SCHEMAS_V2` canonical value, v2/V5와 retry 0을 full CAS descriptor로 보존한다. Qualifier는
top-level/nested descriptor, CAS path/hash/size/bytes와 모든 model-request body의 system/tools를 plan
contract와 독립 대조한다. Resume 시 runner도 checkpoint 유무와 관계없이 이 unique `RunStarted`
descriptor와 CAS bytes, semantic document를 model adapter 생성 전에 다시 검증하며 손상되면 추가 provider
request 없이 `RecoveryError`로 종료한다.

`generic-baseline-readiness-gate-v1`은 다음 논리곱을 사용한다.

```text
exact four task identities are present once each
AND the row schedule IDs and order/task/split/role/condition/repetition fields
    exactly match the frozen preflight schedule
AND every row run_id is unique and equals both result.run_id and qualification.run_id
AND every qualification task_id and schedule_row_id equal its exact frozen row
AND every qualification execution_hash equals the approved preflight execution_hash
AND terminal_runs == 4
AND qualified_runs == 4
AND evaluator_reached_runs == 4
AND official_evaluator_runs == 4
AND infrastructure_errors == 0
AND qualification_errors == 0
AND diagnostic_errors == 0
AND budget_terminal_run_ids == []
```

`task_successes`는 관찰값이며 gate predicate가 아니다. Gate payload는
`task_success_required=false`, `comparison_denominator_eligible=false`,
`memory_admission_unlocked=false`를 명시한다. Hidden failure와 SCRR false는 runtime readiness와 함께
존재할 수 있고 task-specific correction trigger가 아니다.

Pricing source block의 dated standard rate로 보수적으로 모든 token을 최고 configured rate에 놓으면
run당 reserve는 `(850,000 + 25,000) × $4.50/M = $3.9375`, four-row upper bound는 `$15.75`,
suite cap은 `$16`이다. 이는 authorization reserve이지 예상 invoice가 아니다. Checked-in source는
`live_cost_approved=false`, null execution hash와 null pilot ID를 유지한다. Source suite, offline tests와
no-call preflight는 live capability가 아니며 clean commit에서 다시 계산한 exact execution hash와 별도
사용자 승인이 있어야 한 번 실행할 수 있다. Pricing verification이 start 시각 기준 72시간을 넘으면
fresh official verification 없이는 fail closed한다.

850,000-token ceiling과 readiness pass는 final comparison budget freeze가 아니다. Panel 실행 결과를
숨은 정답에 맞춰 tuning하지 않고 검토한 뒤, 별도 decision/config에서 모든 memory condition에 동일한
comparison tuple을 동결해야 한다. Final budget 또는 harness commit이 D-075와 다르면 이 panel을 same-tuple
evidence로 재사용하지 않고 새 exact suite/hash/approval의 readiness panel을 먼저 통과한다. 기존
21/50/250,000/900 template은 계속 stale/unvalidated다.

## 21. D-077 budget-only generic readiness successor contract

새 exact experiment ID는 `generic-baseline-readiness-v2v5-20260802-r2`이고 purpose는 기존과 같은
`generic-baseline-readiness`다. D-075 r1을 수정하거나 재개하지 않으며 다음 ordered task와 dataset
role을 그대로 사용한다.

```text
tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes/public.yaml
tasks/dev-validation/moto-query-scanned-count/public.yaml
tasks/dev-train/pyfakefs-makedirs-parent-traversal/public.yaml
tasks/dev-train/hf-hub-xet-endpoint-propagation/public.yaml
```

모든 row는 `no_memory`, repetition 1이다. Budget-confound 외 변수를 고정하기 위해 다음 항목은
D-075와 동일해야 한다.

```text
model/provider = gpt-5.4-mini-2026-03-17 / openai
reasoning = medium / standard
service tier = default
system prompt = SYSTEM_PROMPT_V3
tool/context = v2 / phase-evidence-v5
transport_max_retries = 0
public review sidecar = absent
fault = none
condition = no_memory
max output = 25,000
max tool calls = 100
wall clock = 1,800 seconds
```

의도적으로 바뀌는 두 값만 다음과 같다.

```text
max model calls = 50   # D-075: 40
max total tokens = 1,200,000   # D-075: 850,000
```

Task/order/role/package, prompt와 tool bytes, model selector, retry, output, tool/wall limit, image/evaluator와
fault policy drift는 preflight, execution plan, generated manifest, runner start/resume와 qualification에서
fail closed한다. 새 clean harness commit은 새 execution identity의 일부지만 model-facing runtime 의미를
변경하지 않는다. 이 invariant가 깨지면 D-077을 budget-only evidence로 부르지 않고 별도 tuple과 readiness
panel로 versioning한다. D-075 experiment ID, execution hash, run, result와 false gate는 immutable하며
D-077 authority 또는 outcome으로 재사용하지 않는다.

Gate와 report 경계는 D-075의 `generic-baseline-readiness-gate-v1` 및 `analysis-report-v2`를 그대로
사용한다. Exact 4/4 task identity, terminal, qualified, evaluator-reached와 official-completed,
infrastructure/qualification/diagnostic/budget-terminal 0을 모두 요구한다. Hidden acceptance, task success와
SCRR는 gate predicate가 아니다. 모든 row는 `calibration_only=1`, `analysis_included=0`이고
`comparison_denominator_eligible=false`, `memory_admission_unlocked=false`다. Gate가 통과해도 comparison
budget이나 no-memory baseline은 별도 freeze decision 전까지 열리지 않는다.

공식 rate는 2026-08-02T13:11:37Z에 다시 확인했다. 보수적 authorization reserve는
`(1,200,000 + 25,000) × $4.50/M = $5.5125`/run, four-row `$22.05`, suite cap `$23`이다.
이는 completion guarantee, 예상 비용 또는 invoice가 아니다. Source suite와 offline test에는 provider call,
execution hash, 비용 승인, run ID, measured usage/cost 또는 gate outcome이 없다. Clean checkout에서 Docker,
pinned task/image/evaluator, SDK, pricing freshness, randomized schedule과 exact source를 다시 결속한 no-call
preflight hash를 만든 뒤 사용자가 그 hash와 최대 `$23`을 명시적으로 승인해야 정확히 한 번 실행할 수 있다.
Source/runtime/qualification/report 계약은 repository-wide 1,095-test 회귀와 Ruff, compileall,
`git diff --check`를 통과했다. 이 offline closure는 provider capability, execution hash나 live outcome이 아니다.

## 22. D-079 exact workflow-completion probe contract

D-079는 D-077의 false four-row gate를 수정하거나 재실행하지 않는 별도 calibration identity다.

```yaml
purpose: workflow-completion-probe
experiment_id: pyfakefs-workflow-completion-probe-v2v5-20260803-r1
tasks:
  - tasks/dev-train/pyfakefs-makedirs-parent-traversal/public.yaml
conditions: [no_memory]
repetitions: 1
model: openai
model_id: gpt-5.4-mini-2026-03-17
reasoning_effort: medium
reasoning_mode: standard
service_tier: default
system_prompt: SYSTEM_PROMPT_V3
tool_schema_version: v2
context_policy_version: phase-evidence-v5
transport_max_retries: 0
max_output_tokens: 25000
budget:
  max_model_calls: null
  max_tool_calls: null
  max_total_tokens: 3000000
  wall_clock_timeout_seconds: 7200
```

`max_model_calls: null`과 `max_tool_calls: null`은 `model-tool-observability-only-v1`에서 call-count
admission을 비활성화하지만 counters, event sequence와 usage reconciliation을 비활성화하지 않는다.
Runtime document는 schema `workflow-completion-runtime-contract-v1`, trace mirror는
`workflow-completion-runtime-evidence-v1`을 사용한다. Plan, generated manifest, runner start/resume와
qualification은 exact prompt/tool bytes, versions, task/package/image/evaluator, SDK retry, call policy,
budget, pricing과 clean harness commit을 독립 비교한다.

Call policy 변경으로 완화할 수 없는 retained guard는 exact-request input + full response reservation,
3,000,000 total token, 7,200초 wall, cost authorization, loop controls, state-machine/idempotency,
constrained tools, Docker/network isolation 및 official evaluator separation이다. 이 중 하나라도 manifest나
trace에서 누락·완화되면 qualification은 fail closed한다.

Gate schema `workflow-completion-probe-gate-v1`은 다음 논리곱이다.

```text
exact pyfakefs row 1/1
AND terminal 1/1
AND trace-qualified 1/1
AND official evaluator reached/completed 1/1
AND infrastructure/qualification/diagnostic error = 0
AND disabled call-guard contract valid
AND retained token/wall/loop/sandbox/cost guard integrity valid
```

Hidden acceptance, task success와 SCRR는 gate 조건이 아니다. 모든 row는 calibration-only이고
`analysis_included=0`, `comparison_denominator_eligible=false`,
`memory_admission_unlocked=false`를 유지한다. Pass는 uncensored call-count workflow completion만
보이며 comparison fairness, memory effect 또는 task correctness를 증명하지 않는다.

Checked-in conservative reserve는 `$13.6125`, suite cap은 `$14`이다. Source/config/offline test는
live authority가 아니다. 이 단계에는 provider call, execution hash, 사용자 비용 승인, run ID/result,
measured token/cost, gate outcome 또는 SCRR가 없다. Clean no-call preflight에서 fresh official pricing과
exact environment를 결속한 hash를 만든 뒤 사용자가 그 hash와 최대 `$14`를 명시적으로 승인해야 정확히
한 번 실행할 수 있다. 승인된 live result가 생기면 D-079 source contract를 바꾸지 않고 별도 D-080
append-only seal에서 보존한다.

## 23. D-080 gate-summary projection and correction contract

D-080은 D-079 source/runtime contract의 새 invocation이 아니다. Exact execution
`sha256:70bc29196115cc6b201a30587d6974d3a05607345d447cb3a9144b0920c09791`과 run
`run_606349c2c56342d4`의 immutable result를 입력으로 하는 evidence seal이다.

Terminal qualification summary는 workflow-completion purpose에서 다음 exact projection을 가진다.

```yaml
gate_checks:
  disabled_call_guard_contract:
    schema_version: qualification-gate-check-projection-v1
    check_id: disabled_call_guard_contract
    check_count: 1
    passed: true
```

Projection producer는 full `trace-qualification-v2.checks`에서 exact ID match를 세고 boolean pass만
전달한다. Consumer acceptance는 다음 논리곱이다.

```text
gate_checks is an object
AND set(gate_checks.keys) == {disabled_call_guard_contract}
AND set(projection.keys) == {schema_version, check_id, check_count, passed}
AND schema_version == qualification-gate-check-projection-v1
AND embedded check_id equals the key
AND type(check_count) is strict integer AND check_count == 1
AND passed is exactly true
```

Raw full-check list를 terminal summary에 넣지 않는다. Missing/duplicate/extra outer 또는 inner key, wrong
schema/ID, count 0 또는 2 이상, boolean/float/string count, truthiness와 malformed object는 모두 false다. Historical
summary에 projection이 없다는 이유로 original result를 새 schema로 재해석하지 않는다.

Portable append-only manifest는
`reports/live-pilot/artifacts/d080-workflow-completion-gate-summary-correction.json`이고 schema는
`workflow-completion-gate-summary-correction-manifest-v1`이다. Correction identity
`gcor_6552d8277d70fba7f296b0aee837a8f497be8384cce7fea4521cb39de1e19861`의 digest는 semantic body의
canonical SHA-256인 `sha256:6552d8277d70fba7f296b0aee837a8f497be8384cce7fea4521cb39de1e19861`와 같아야 한다.
`workflow-completion-gate-summary-correction-v2` body는 다음 immutable source에 결속된다.

```text
experiment result SHA-256 = sha256:c9f85ac52b0b3933625966c2bd6af1f6b57bdc974f2c141aa74bd21a2700ee28
qualification file SHA-256 = sha256:4d7a15f9984394b6ab798f78e391c6b0d5632bc0e6d4d4c9c4876eb5028c8168
qualification hash = sha256:0368ef128ac6bb22ec4b15bac0ad6f77d73869c1f4d82c8537defd67aaa99d82
source evidence hash = sha256:5efce76a94abfe48bcce9f63283cd0459fd9606c4a05d4c008430d52437b5928
```

Body는 source identity와 위 hashes뿐 아니라 correction harness commit
`7e40e27446bcf011f700c219a96983e5670422f4`, package identity, projection schema/outer-inner exact-key
contract, `qualification-summary-projection-mismatch` cause, original gate의 exact full payload, corrected gate의
exact full payload와 claims boundary를 모두 포함한다. 이 중 하나가 달라지면 semantic body hash와 correction
ID도 달라진다.

Original과 corrected gate의 schema는 모두 `workflow-completion-probe-gate-v1`이다. Corrected payload는
`call_guard_contract_passed=true`와 그에 따른 `passed=true`를 기록하지만 task success 0,
`task_success_required=false`, comparison denominator false와 memory admission false를 그대로 유지한다.
Correction-specific claims는 gate object에 넣지 않고 `claims_boundary`에 둔다. 이 boundary는
`original_artifacts_modified=false`, `original_gate_replaced=false`, `task_outcome_changed=false`, task success/SCRR
false, calibration-only true, comparison/memory/core false를 정확히 결속한다. D-080 seal/verification은 provider
call 0과 추가 model cost `$0`로 수행됐다. Contract verification은 focused 331 passed, repository-wide 1,162
collected 중 1,155 passed/7 environment-dependent skipped였고 Ruff, Python compileall, JSON parse와
`git diff --check`를 통과했다.

## 24. D-081 source contract and D-082 measured-result seal

Exact experiment ID는 `generic-baseline-readiness-v2v5-20260803-r3`, purpose는 기존과 같은
`generic-baseline-readiness`다. D-075/D-077/D-079/D-080을 수정·재개·결합하지 않고 다음 ordered
task와 원 dataset role을 그대로 사용한다.

```text
tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes/public.yaml
tasks/dev-validation/moto-query-scanned-count/public.yaml
tasks/dev-train/pyfakefs-makedirs-parent-traversal/public.yaml
tasks/dev-train/hf-hub-xet-endpoint-propagation/public.yaml
```

모든 row는 `no_memory`, repetition 1이다. Exact runtime/config 계약은 다음과 같다.

```yaml
model: openai
model_id: gpt-5.4-mini-2026-03-17
reasoning_effort: medium
reasoning_mode: standard
service_tier: default
system_prompt: SYSTEM_PROMPT_V3
tool_schema_version: v2
context_policy_version: phase-evidence-v5
transport_max_retries: 0
max_output_tokens: 25000
budget:
  max_model_calls: null
  max_tool_calls: null
  max_total_tokens: 2400000
  wall_clock_timeout_seconds: 1800
```

두 null은 exact pair로만 허용한다. 하나만 null이거나 다른 generic experiment ID, task/order,
model/prompt/tool/context/retry/output/token/wall 조합에 붙으면 loader, plan, manifest, start/resume와
qualification이 provider request 전에 fail closed한다. `model-tool-observability-only-v1`은 model/tool call
counter와 usage evidence를 계속 기록·reconcile하지만 두 count를 admission reason으로 사용하지 않는다.
Exact-request, total-token, wall, cost, loop, phase/idempotency, constrained tool, Docker/network와 evaluator
guard는 계속 필수다.

Public process-only derivation은 다음 canonical arithmetic을 사용한다.

```text
token subtotal = 1,790,707 + (84 * 2,000) + 25,000 = 1,983,707
unrounded token ceiling = 1,983,707 * 1.2 = 2,380,448.4
token ceiling = round_up(2,380,448.4, 100,000) = 2,400,000

unrounded wall ceiling = 856.559 * 2 = 1,713.118 seconds
wall ceiling = round_up(1,713.118, 300) = 1,800 seconds
```

여기서 1,790,707 token, 84 model call과 856.559초는 evaluator까지 완료한 D-079 public process
usage이고, call당 2,000은 향후 memory condition과의 condition-neutral allowance다. Private evaluator
outcome이나 task success는 selection 또는 산식에 쓰지 않는다. Derivation artifact는
`reports/live-pilot/artifacts/d081-condition-neutral-budget-candidate.json`이다.

D-081은 historical v1 schema를 확장하지 않고 다음 exact version을 사용한다.

```text
runtime plan schema = generic-baseline-runtime-contract-v2
RunStarted runtime evidence = generic-baseline-runtime-evidence-v2
aggregate gate = generic-baseline-readiness-gate-v2
call policy = model-tool-observability-only-v1
qualification projection = qualification-gate-check-projection-v1
projection check ID = disabled_call_guard_contract
```

`generic-baseline-readiness-gate-v2`는 v1의 exact four task/schedule/run/execution binding, 4/4 terminal,
qualified, evaluator-reached/official-completed와 zero infrastructure/qualification/diagnostic/budget-terminal
predicate를 유지한다. 여기에 네 row 모두의 `disabled_call_guard_contract` projection exact-one과
`call_guard_contract_passed=true`, terminal-loop failure 0을 추가한다. Projection은 outer/inner exact-key,
exact schema/ID, bool이 아닌 strict integer `check_count=1`, `passed is true`를 요구한다. Hidden acceptance,
task success와 SCRR는 여전히 gate 조건이 아니다.

2026-08-03T01:08:49Z 공식 standard rates `$0.75/M` input, `$0.075/M` cached input,
`$4.50/M` output에서 최고 configured rate를 사용한다.

```text
per-run reserve = (2,400,000 + 25,000) * $4.50/M = $10.9125
four-row reserve = $10.9125 * 4 = $43.65
suite cap = $44
```

Source YAML의 `live_cost_approved=false`, `approved_execution_hash=null`, `pilot_run_id=null`은 invocation
authority가 아니며 그대로 유지한다. 실제 D-081 invocation은 별도 clean preflight와 사용자 승인으로
commit `b4c79242bb0a94eed50530116205323e78c7d21a`, execution hash
`sha256:446b60568795c585856468064fa1aa11a9d85a8e8806e6c71b3b19ab1aa12579`를 결속해 정확히 한 번
소비됐다. 네 row 모두 terminal·trace-qualified·official evaluator completion, exact-one
`disabled_call_guard_contract`와 aggregate gate v2 pass를 기록했다. Infrastructure/qualification/
diagnostic/budget-terminal/terminal-loop confound는 모두 0이다. Task success는 Babel 1/4이고 HF Hub,
Moto, pyfakefs는 hidden failure지만 regression/scope/safety는 4/4 pass다.

측정 사용량은 111 model/175 tool call과 1,929,316 token, 고정 standard rate 계산 비용
`$1.79426325`다. 111/111 model request는 completed, exact telemetry 일치, truncation disabled,
`store=false`였고 rejected-patch recovery 3/3이 verified됐다. Loop observation 50회 중 pyfakefs가
39회였으며 terminal loop failure는 0이다. 계산 비용을 billed invoice/free-tier charge로 해석하지 않는다.
Raw result hash는 `sha256:f8a2cd25916290ae02e46b484519cc01dedbe50097326085524a88bb9b324f83`,
journal file/final event hash는
`sha256:52626ba6d7e61bc293ce327f4bf190e3b4118b20a2efe4d9de09d8186ce6afdd`와
`sha256:f5537479c3c1e8c150f9cbfec5238d99c882eff537006773af8d9ddf9f78c254`다. Portable report
`reports/live-pilot/generic-baseline-readiness-v2v5-20260803-r3.json`의 content hash는
`sha256:2a8f650e73e01aed9d629290627999232ec6aebd1769d2179bc22f084ddbede2`다. D-082 seal 작업은
provider call 0, model cost `$0`이다.

D-081/D-082는 calibration-only이며 `comparison_denominator_eligible=false`,
`no_memory_baseline_unlocked=false`, `memory_admission_unlocked=false`, `core_campaign_unlocked=false`다.
같은 per-run ceiling을 96 run에 적용한 theoretical reserve `$1,047.60`은 원래 `$150` cap을 넘으므로
별도 freeze/cost decision 없이 comparison/core로 승격하지 않는다. Historical D-075/D-077/D-079/D-080
suite, execution identity, raw/portable artifact, original gate와 append-only correction은 immutable하다.
D-082 final documentation-seal verification은 repository-wide 1,214 collected 중 1,207 passed/7
environment-dependent skipped와 focused D-082 8/8을 통과했다.

## 25. D-083 condition-neutral comparison-budget freeze contract

D-083은 다음 per-run budget policy만 동결한다.

```yaml
schema_version: condition-neutral-comparison-budget-freeze-v1
source_experiment_id: generic-baseline-readiness-v2v5-20260803-r3
budget:
  max_model_calls: null
  max_tool_calls: null
  max_total_tokens: 1600000
  wall_clock_timeout_seconds: 1800
max_output_tokens: 25000
transport_max_retries: 0
claims_boundary:
  comparison_budget_policy_frozen: true
  runtime_support_implemented: false
  manifest_support_implemented: false
  qualification_support_implemented: false
  live_execution_authorized: false
  comparison_denominator_eligible: false
  no_memory_baseline_unlocked: false
  memory_admission_unlocked: false
  core_campaign_unlocked: false
```

Canonical derivation은 D-081 r3 pyfakefs observed-prefix minimum 1,303,223만 사용한다.
`1,303,223 * 1.2 = 1,563,867.6`을 100,000 단위로 올림해 1,600,000을 얻는다. Hidden outcome과
task success는 입력이 아니며 D-080 historical minimum 1,815,619는 exact-source scope 밖이다.
따라서 frozen ceiling은 completion을 보장하지 않는다.

Worst-rate reserve는 `$7.3125`/run, `$87.75`/12 run, `$131.625`/18 run과 `$702`/96 run이다.
기존 `$20` 12-run cap과 `$150` project cap은 supersede하지 않는다. Artifact, source template이나
no-call preflight는 paid authority가 아니며 runtime/manifest/qualification support가 구현·검증되기 전
모든 source template은 fail closed해야 한다.

Append-only artifact는
`reports/live-pilot/artifacts/d083-condition-neutral-comparison-budget-freeze.json`, SHA는
`sha256:e01c5f0107592e1c29c1ec8264f32bf05c979a718c353c37acb0d87fafd2cb88`다. D-083은
provider call 0, model cost `$0`인 offline contract다.
D-081/D-082 result, calibration-only status, task outcome과 evidence identity는 수정하지 않는다.
Final verification은 1,238 collected 중 1,231 passed/7 environment-dependent skipped다.

## 26. D-084 condition-neutral comparison runtime contract

`condition-neutral-comparison-runtime-contract-v1`은 D-083 profile을 execution identity로 승격하되
execution authority는 부여하지 않는다. Exact selector는 다음 둘 중 하나의 purpose만 허용한다.

- `memory-development-no-memory`: condition은 정확히 `no_memory` 하나다.
- `core`: ordered condition은 `no_memory`, `raw_trace`, `structured`, `selective_structured`다.

두 purpose 모두 model `gpt-5.4-mini-2026-03-17`, medium/standard/default, SDK retry 0,
`SYSTEM_PROMPT_V3`, tool v2/context `phase-evidence-v5`, output 25,000, memory context 2,000과 아래 exact
budget을 요구한다.

```yaml
max_model_calls: null
max_tool_calls: null
max_total_tokens: 1600000
wall_clock_timeout_seconds: 1800
call_guard_policy: model-tool-observability-only-v1
```

Plan contract의 canonical field set은 purpose, ordered `memory_conditions`, provider/model/mode, retry,
output, budget, memory allowance, tool/context version, exact system-prompt/tool-schema hash, call-guard policy,
harness commit과 다음 D-083 descriptor다.

```yaml
comparison_budget_policy:
  schema_version: condition-neutral-comparison-budget-freeze-v1
  profile_id: gpt54mini-v2v5-condition-neutral-1600k-v1
  path: reports/live-pilot/artifacts/d083-condition-neutral-comparison-budget-freeze.json
  content_hash: sha256:e01c5f0107592e1c29c1ec8264f32bf05c979a718c353c37acb0d87fafd2cb88
```

이 document는 execution hash에 포함된다. Start 직전에는 `RunManifest`에서 같은 document를 재구성해
approved preflight와 exact 비교한다. Partial null count, 목적·조건·model·retry·output·budget·V2/V5·fault
또는 public-review sidecar drift는 거부한다. Historical finite-count 200k/250k profile, D-081 2.4M과 D-079
3M nullable-count profile은 각자의 exact selector로만 유지되며 새 contract로 재해석하지 않는다.

`condition-neutral-comparison-runtime-evidence-v1`은 `RunStarted.runtime_contract_artifact`가 가리키는
content-addressed JSON이다. 이 trace document는 purpose와 현재 memory condition, model tuple, budget,
memory allowance, system prompt bytes, tool-schema bytes, V2/V5, call-guard policy와 D-083 descriptor를 가진다.
Descriptor CAS와 bytes를 모두 검증하고 start/resume에서 expected document와 exact 비교한다.

No-memory qualification은 `comparison_runtime_contract`와 `disabled_call_guard_contract`를 trace check로
추가한다. 후자는 null count가 counter observability일 뿐 model/tool admission block으로 사용되지 않았는지
검사한다. Core 네 condition의 plan/manifest/runtime document contract는 구현됐지만 memory index와 각
condition의 frozen-index identity와 leak-safe terminal qualification contract는 pending이다. Core preflight는
`CORE_MEMORY_RUNTIME_BINDING_PENDING`을 유지하고 paid-call boundary도 core manifest를 거부한다. 따라서
structural support를 core campaign qualification 또는 comparison evidence로 표현하지 않는다.

Append-only offline gate artifact는
`reports/live-pilot/artifacts/d084-condition-neutral-comparison-runtime-gate.json`이다. Provider call/model
cost는 0/$0이며 승인 execution hash와 live 권한은 없다.
Final verification은 focused D-084 68/68과 repository-wide 1,304 collected 중 1,297 passed/7
environment-dependent skipped다. Artifact SHA는
`sha256:e7fb7b7e7e9dad3e6b31fb781f09151b940bf226bdd5876e5e75e472ff24b701`이다.

## 27. D-085 condition-neutral comparison pilot source contract

Exact pilot selector는 다음 값을 모두 요구한다.

```yaml
schema_version: experiment-v2
experiment_id: dev-validation-condition-neutral-v2v5-pilot-20260803-r1
purpose: development-validation-live-pilot
tasks:
  - tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes/public.yaml
conditions: [no_memory]
repetitions: 1
model: openai
model_id: gpt-5.4-mini-2026-03-17
reasoning_effort: medium
reasoning_mode: standard
service_tier: default
transport_max_retries: 0
max_output_tokens: 25000
budget:
  max_model_calls: null
  max_tool_calls: null
  max_total_tokens: 1600000
  wall_clock_timeout_seconds: 1800
memory_token_budget: 2000
estimated_cost_usd: 7.3125
cost_limit_usd: 8
```

Approval compatibility fields는 false/null이고 pilot ID, task, condition, repetition, model tuple, budget,
prompt/tool/context, retry, output, memory allowance, pricing 또는 sidecar drift를 거부한다. Arbitrary
`development-validation-live-pilot`가 nullable count를 사용할 수 없으며 historical pilot은 각자의 기존
contract로만 해석한다.

Execution plan과 `RunManifest`는 D-084의 `condition-neutral-comparison-runtime-contract-v1`을 사용하고
`RunStarted`는 `condition-neutral-comparison-runtime-evidence-v1` full CAS를 남긴다. Start/resume, paid-call
boundary와 qualifier가 동일 document와 D-083 policy SHA를 독립 재구성한다. Terminal qualification은
`comparison_runtime_contract`, `disabled_call_guard_contract`, `pricing_start_freshness`와 no-memory boundary를
요구한다.

`condition-neutral-comparison-pilot-readiness-gate-v1`은 terminal/qualified/official evaluator 1개,
`call_guard_contract_passed_required=true`와 `terminal_loop_failure_runs_allowed=0`을 포함한 모든 process
confound 0을 요구하고 `task_success_required=false`다. Source artifact는
`reports/live-pilot/artifacts/d085-condition-neutral-comparison-pilot-source-gate.json`이며 provider call,
execution hash, live approval, baseline, denominator, memory admission 또는 core authority를 만들지 않는다.

Future campaign admission은 exact consumer `dev-no-memory-v5-20260730-r1`의
`condition-neutral-comparison-pilot-admission-v1`을 따른다. Pilot과 campaign은 서로 다른 clean source commit을
사용하므로 raw commit equality는 요구하지 않는다. 대신 D-083 policy, model/provider/reasoning/mode/tier,
retry, prompt/tool hash, tool/context version, output, budget, memory conditions/allowance와 call-guard policy의
exact semantic tuple을 검증한다. Qualification/source/approved pilot plan CAS와 네 필수 check도 다시 확인한다.
Persisted qualification은 `qualify_run(..., persist=false)`의 durable recomputation과 canonical exact
일치해야 하며 task success는 admission 입력이 아니다. Canonical descriptor hash는 future campaign execution plan/hash에
포함되고 start/resume/post-run matcher가 재검증한다. Consumer는 offline 구현됐지만 qualified pilot과 별도
cap·preflight·hash·승인이 없으므로 future campaign 실행 권한은 계속 닫혀 있다.
Final offline verification은 focused 153/153, repository-wide 1,392 collected 중 1,385 passed/7 skipped다.
Artifact SHA는 `sha256:8b60cb2e62a6259db29527a600712e95b36390a1c07da9fb66e6f1d7d16f51d2`이다.

## 28. D-086 measured-result and append-only correction contract

D-086 source identity는 다음 exact values다.

```yaml
experiment_id: dev-validation-condition-neutral-v2v5-pilot-20260803-r1
execution_hash: sha256:7163f6c44aa5b7790d35546be37781248d6575eac60986b2610f2e21c35348a0
source_harness_commit: 629b9fdd9f69d1522cf565a06ae9679abe3f60a7
run_id: run_c355405d826641b9
result_hash: sha256:e0c3c4c67adc8c157a5030c9a93e3fd106d6b7a12f596253ddf10582fe74b80a
journal_file_hash: sha256:4c114059fad069526d95786c392b7ea36724443b7231b4426bb097ee0c2199c8
final_journal_event_hash: sha256:93853c6367459bcae004789a9a2710c6be518078b21041ece0b160d9843e5a8b
qualification_hash: sha256:11bda7b2f31bae453f21c4718fdcb4563a74e173e621fd8035f1ab8aa64f1293
source_evidence_hash: sha256:41d9b862fe5042b4838c53cd80c3318dc55dc5f0bd892962fecc20caba0b2105
```

Original `condition-neutral-comparison-pilot-readiness-gate-v1` payload는 passed이며 immutable하다. Run usage는
69,701 input, 3,500 output, 73,201 total token, 8 model call, 9 tool call, 50,769ms와 calculated
`$0.06802575`다. Official evaluator verdict는 hidden/regression/scope/safety 모두 pass다. Qualification은
28/28이고 persisted payload가 durable `qualify_run(..., persist=false)` recomputation과 canonical exact
일치해야 한다.

Original result의 `budget-pressure-error-v1`은 runtime failure가 아니라 exact pilot purpose를 허용 목록에서
빠뜨린 read-only diagnostic selector defect다. `condition-neutral-comparison-pilot-budget-pressure-correction-v1`
은 exact experiment ID, purpose, run/runtime/source/result hash를 요구하고 token headroom 1,526,799,
wall headroom 1,749,231ms, model/tool limit `null`, binding `none`을 결속한다. Original result/gate replacement와
retroactive gate recomputation은 모두 false다. Near-match pilot과 arbitrary development-validation purpose는
계속 거부한다.

Portable schema `condition-neutral-comparison-pilot-d086-evidence-v1`은 sanitized metadata, original gate,
run/usage/verdict, qualification projection, safe trace telemetry, correction reference, journal seal과 raw-local
artifact hashes만 포함한다. Provider body, API key, private spec/hash, hidden assertion, verifier detail, patch body와
reference patch는 금지한다. Path/SHA는
`reports/live-pilot/dev-validation-condition-neutral-v2v5-pilot-20260803-r1.json` /
`sha256:520ae8408c4e090a2c66a0ed3b2c5c29738762eec1b4f7d87b9452e551635464`와
`reports/live-pilot/artifacts/d086-condition-neutral-comparison-pilot-budget-pressure-correction.json` /
`sha256:bd42c50b7da2400eea8e340358e92ff2605a9fde8d866d3fdff1c9695b95aeb4`다. Final verification은 `focused 64/64; repository-wide 1,416 collected, 1,409 passed/7 skipped; Ruff/compileall/JSON/git-diff checks passed; seal provider calls/model cost 0/$0`이다.

D-085 ID는 hard-consumed라 local result/journal 존재 여부와 무관하게 재실행할 수 없다. Seal은 readiness와
한 task success를 기록할 뿐 baseline/denominator/memory/core/analysis authority가 아니다. Future campaign의
canonical pilot-admission hash는 별도 campaign commit을 포함하므로 이 seal이 미리 authoritative hash를 만들지
않는다. D-086 시점의 다음 contract 후보는 `$88` cap을 고정하는 separate source decision이었지만,
D-087의 `$25` accrued-spend contract가 이 forward choice를 supersede한다.

## 29. D-087 campaign cost-control contract

Exact successor `dev-no-memory-condition-neutral-accrued-cap-20260804-r1`만
`campaign-list-price-accrual-cap-v1`을 가질 수 있다. Canonical policy는 campaign-local list-price accounting,
`$25` hard cap, `$7.3125` full-next-run reserve, `$87.75` schedule upper bound, equality admission,
`not_started` stop action과 disabled live resume을 결속한다. 다른 ID에 policy가 있거나 exact ID에서 field가
빠지거나 달라지면 `ExperimentSuite` validation이 거부한다.

Preflight의 `campaign-cost-control-evidence-v1`은 descriptor와 canonical content hash를 가진다. 그 hash는
execution hash와 `ExperimentRunContext.campaign_cost_control_hash`에 들어간다. Exact D-087 context에서는 hash가
필수이고 다른 experiment에서는 금지된다. Post-run qualifier는 plan을 재파싱하고 suite, pricing, descriptor와
manifest hash를 독립 재계산해 `campaign_spend_cap_contract`로 검증한다.

Campaign journal의 비용 event는 다음 순서를 따른다.

```text
RunCostReserved -> RunStarted -> RunTerminal -> RunCostSettled
```

각 event는 policy hash, schedule row, cap, reserve와 accrued/held nano-USD를 포함한다. Reserve 부족 시
`CostReserveUnavailable` 뒤 row가 `RunNotStarted`가 된다. `campaign-cost-qualification-v1`은 hash chain,
reservation/settlement cardinality, row identity와 모든 시점의 `accrued + held <= cap`을 재집계한다.

Provider 경계를 넘기 위한 `CampaignCostReservationAuthorization`은 exact execution hash, schedule row,
run ID, journal/root, policy hash와 latest reservation event hash를 묶는 one-use capability다. AgentRunner는
canonical path/root equality를 다시 확인하고 StateStore의 D-087 consumption table에 `BEGIN IMMEDIATE`로
원자적 insert한 뒤에만 model adapter를 호출할 수 있다. 같은 execution/row 또는 reservation event의 재사용은
항상 거부한다. 다음 capability 발급 시 SQLite의 consumed set이 journal에 exact subset으로 남아 있는지 확인하고,
모든 prior settlement의 durable qualification/source/result hash를 다시 로드해 token counter와 fixed
nano-USD 가격을 독립 재계산한다. 표시용 `model_cost_usd`는 이 계산에 사용하지 않는다.

이 contract는 preserved SQLite anchor 아래의 marker 삭제, journal reset, alternate root와 settlement 축소·rehash를
차단한다. 외부/request-level billing ledger는 아직 구현하지 않았으므로 exact D-087 live resume은 fail closed다.

## 30. D-088 immutable D-087 result contract

Portable schema `condition-neutral-no-memory-campaign-d088-evidence-v1`은 outer
`schema_version/report_id/semantic_body_hash/semantic_body` exact wrapper를 사용한다. `report_id`는 canonical
semantic body SHA에서 파생한다. Exact identities는 source commit
`7eee5fa1837d30e6177c46119885035f2b1d976f`, execution hash
`sha256:0dd8ca1d0632398fed25ca28fbce89b97b0bf2137be163ed19a09fbf2d7f470d`, plan semantic hash
`sha256:66246391a30be5743c9c0de890249f2b4216dfd9ad61aa3e79b459cc9a82de07`, plan byte SHA
`sha256:45aabeac18fd6648904a8d18a7c311da5277a4cc4bb5a057d74bd3222d624aaa`, suite semantic/source SHA와
cost-control hash를 서로 다른 field로 보존한다.

Original result gate는 수정하거나 재산출하지 않는다. Contract는 12 terminal, 12 qualified, 11 official
evaluator, budget-terminal run `run_4613c65b2a254349`, task success 1과 gate `false`를 그대로 요구한다.
Cost qualification은 12 reservation/settlement, accrued 5,368,428,750 nano-USD, maximum committed
12,311,498,250 nano-USD, held 0과 cap 25,000,000,000 nano-USD를 exact 비교한다. SQLite one-use consumption
12개는 journal reservation set과 exact match해야 한다.

`CONSUMED_CONDITION_NEUTRAL_ACCRUED_CAP_EXPERIMENT_IDS`는 exact D-087 ID 하나만 포함하고
`HISTORICAL_IMMUTABLE_LIVE_EXPERIMENT_IDS`에만 합쳐진다. Multi-run identity를 single-task set이나 historical
200k-budget selector set에 넣지 않는다. Portable claims는 no-memory baseline, success-rate estimate,
comparison denominator, memory admission/index, core, analysis와 automatic rerun을 모두 false로 고정한다.

## 31. D-089 AnyIO budget-only readiness contract

Exact experiment ID는 `anyio-workflow-completion-budget-only-v2v5-20260804-r1`이고 purpose는
`workflow-completion-probe`다. Registered tuple은 AnyIO memory-development task 한 개, no-memory 1회,
mini medium/standard/default, retry 0, output 25,000, memory allowance 2,000과
`null/null/2,000,000/1,800`이다. Source estimate/reserve는 `$9.1125`, hard approval cap은 `$10`이다.

“Budget-only”는 D-087 failed row와 비교 가능한 per-run agent/model/runtime fields에만 적용한다. Source artifact는
새 suite identity fields를 별도로 열거하고 runtime changed fields를 정확히 `budget.max_total_tokens` 하나로
제한한다. D-087 suite/result/source artifact의 byte SHA와 failed run/schedule row/deficit evidence를 결속한다.

Gate schema는 `workflow-completion-probe-gate-v1`, gate ID는 `d089-anyio-budget-only-readiness`다. Required
predicate는 terminal, qualified, evaluator reached, official completed, disabled-call guard와 process confound 0이다.
`task_success_required=false`, hidden/SCRR required=false, comparison/memory authority=false다.

## 32. D-090 AnyIO budget-only result-seal contract

Portable report schema는 `anyio-budget-only-readiness-d090-evidence-v1`이다. Top-level exact keys는
`schema_version`, `report_id`, `semantic_body_hash`, `semantic_body`이며 report ID는 canonical semantic body
hash에서 결정된다. Body는 source commit/YAML/source-gate SHA, exact execution/suite/schedule/row/run identity,
raw result/journal/plan/qualification artifact hash, original gate, terminal usage/budget pressure, public trace
aggregate, evidence validation과 claims boundary를 결속한다.

Required measured facts는 terminal/qualified `1/1`, evaluator/official `0/1`, budget-terminal `1`, qualification
27/27, usage `1,737,041 + 219,068 = 1,956,109`, cost `$2.28858675`, exact-request deficit `14,913`이다. Stored
qualification은 `persist=False` 재계산과 canonical-exact해야 하고 source-evidence hash도 재계산한다. Journal은
`CampaignStarted -> RunStarted -> RunTerminal -> CampaignCompleted` 네 event와 result hash를 검증한다.

Seal은 D-089 source artifact나 raw result를 수정하지 않는다. Exact experiment ID는 result seal과 함께
workflow-completion consumed set에 들어가며 provider call 0/$0인 seal 작업은 새 live authority를 만들지 않는다.
