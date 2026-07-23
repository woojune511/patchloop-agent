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
schema_version: task-private-v1
task_id: parser-quoted-newline-001
task_version: 1

hidden_checks:
  - id: hidden_multiline_csv_tests
  - id: regression_suite

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

`task_id + task_version + base_commit`은 평가 도중 immutable하다. Public/private의 ID와 version이 일치하지 않으면 실행을 거부한다.

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
