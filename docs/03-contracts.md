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

Stress lane은 `sentinel_count: 3`과 `include_in_core_metrics: false`를 고정한다. Fault-derived run은
원본 task identity와 manifest를 보존하면서 새 run ID를 사용하고, core memory 결과와 별도로
보고한다.

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

## 3. Run manifest

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

## 4. Event envelope

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
ToolSucceeded     ToolFailed         PatchApplied
CheckStarted      CheckFinished      CheckpointSaved
FailureTagged     RunCompleted       RunFailed
```

Event payload schema는 type별 version을 가져야 한다. Secret, full hidden assertion, raw credential을 payload에 저장하지 않는다.

## 5. Checkpoint

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

## 6. Tool call contract

모든 mutating 또는 비용이 큰 tool call은 다음 공통 envelope를 사용한다.

```json
{
  "tool": "apply_patch",
  "tool_schema_version": "v1",
  "action_id": "act_0071",
  "run_id": "run_0041",
  "input": {},
  "input_hash": "sha256:..."
}
```

### `search_repo`

```json
{
  "query": "parse_csv",
  "path": "src",
  "file_glob": "*.py",
  "max_results": 20
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
  "patch": "...unified diff...",
  "expected_file_hashes": {
    "src/parser.py": "sha256:..."
  }
}
```

Expected hash mismatch는 stale write이며 patch를 부분 적용하지 않는다. 동일 `action_id + input_hash`가 성공했다면 기존 result를 반환한다. 같은 action ID에 다른 input hash가 오면 conflict로 거부한다.

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

## 7. Verifier result and final outcome

```json
{
  "schema_version": "verifier-result-v1",
  "verifier_result_id": "vr_0011",
  "run_id": "run_0041",
  "check_type": "hidden_acceptance",
  "check_id": "hidden_multiline_csv_tests",
  "passed": true,
  "duration_ms": 412,
  "evidence_artifact_ids": ["art_0200"],
  "details": {
    "tests_passed": 4,
    "tests_failed": 0
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
  "verdicts": {
    "hidden_tests_passed": true,
    "regression_tests_passed": true,
    "scope_policy_passed": true,
    "safety_policy_passed": true
  },
  "usage": {
    "input_tokens": 0,
    "output_tokens": 0,
    "model_cost_usd": 0,
    "model_calls": 0,
    "tool_calls": 0,
    "wall_clock_ms": 0
  },
  "submitted_patch_artifact_id": "art_0180"
}
```

Skipped, infrastructure error, policy rejection을 `false`와 혼합하지 않는다. 각 verdict는 내부적으로 `pass | fail | error | not_run` 상태를 보존하고, SCRR 성공은 네 항목이 모두 `pass`일 때만 true다.

`scope_policy_passed`는 단일 검사 결과가 아니라 allowed/forbidden path, diff size, dependency, test tampering, public API 정책의 deterministic aggregation이다. 구성 검사 하나라도 `fail | error | not_run`이면 scope policy를 pass로 만들 수 없다. 개별 구성 결과는 별도 `VerifierResult`로 보존한다.

## 8. Failure record

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

## 9. Failure memory entry

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

## 10. Retrieval decision

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
