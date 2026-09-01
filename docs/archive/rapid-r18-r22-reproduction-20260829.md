# Archived R18-R22 reproduction procedures

These offline procedures were current while the R18 driver, V20 diagnosis and V21/V22 successors were being
qualified. Their artifacts and consumed executions remain immutable. This archive grants no candidate, rehearsal,
Docker, provider, evaluator, visible-check or paid authority.

## Row-local infrastructure isolation

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_rapid_row_continuation.py tests/test_rapid_row_continuation_qualification.py tests/test_rapid_public_development_v19.py --basetemp .pytest-row-continuation
.\.venv\Scripts\python.exe scripts/build_rapid_row_continuation_qualification.py --repository .
```

The byte-stable 9,969-byte file/content hashes were `sha256:61c07553...11cbd`/
`sha256:0a8096cd...47de1`. It bound consumed R16 with zero external/check calls, workspace mutation or cost.

## Rapid driver and terminal parity

Driver V1 is consumed at 4,510-byte file/content `sha256:72b35511...1cc5c`/
`sha256:e2825a3c...2cb6a`; byte-audit only.

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_rapid_batch_driver.py tests/test_rapid_batch_driver_qualification.py tests/test_rapid_terminal_state_parity_qualification.py --basetemp .pytest-terminal-parity
.\.venv\Scripts\python.exe scripts/build_rapid_terminal_state_parity_qualification.py --repository .
```

Terminal-parity V2 was 3,920 bytes at file/content `sha256:d992159b...de0d6`/
`sha256:c316e23c...c53bd`, with zero external/check calls or cost.

## Policy-label repair and R18 diagnosis

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_rapid_batch_driver.py tests/test_rapid_driver_policy_label_qualification.py --basetemp .pytest-policy-label
.\.venv\Scripts\python.exe scripts/build_rapid_driver_policy_label_qualification.py --repository .
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_rapid_r18_exploration_diagnosis.py --basetemp .pytest-r18-exploration
.\.venv\Scripts\python.exe scripts/build_rapid_r18_exploration_diagnosis.py --repository .
```

Policy-label repair was 4,774 bytes at file/content `sha256:a88ad9e1...c0535`/
`sha256:71ffa142...dff16`. The public R18 diagnosis was 31,828 bytes at file/content
`sha256:15a3b155...4ced3`/`sha256:1e83ccc2...c560f`. Close active trace writers first; the diagnosis reads only a
closed SQLite snapshot and public projections. Both paths add zero external/check calls, state mutation or cost.

## Lean V21 plan-gate liveness

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_workflow_plan_gate_liveness_successor.py tests/test_workflow_plan_gate_liveness_successor_qualification.py tests/test_workflow_successor_v2_runner.py --basetemp .pytest-plan-gate-liveness
.\.venv\Scripts\python.exe scripts/build_lean_harness_plan_gate_liveness_qualification.py --repository .
uv run --offline pytest -q -p no:cacheprovider --basetemp .pytest-v21-review tests/test_workflow_plan_gate_liveness_activation_review.py
uv run --offline python scripts/build_lean_harness_plan_gate_liveness_activation_review.py --repository .
```

Qualification was 5,617 bytes at file/content `sha256:e45a36b5...467bb`/
`sha256:dc1c5be7...71867`. Activation review was 5,559 bytes at file/content `sha256:aabe212a...a69d`/
`sha256:86a58009...18f9`; it measured mock JSON bytes, not provider tokens, and remained
`candidate-preparation-blocked`.

## Lean V22 bounded feedback and activation review

```powershell
uv run --offline pytest -q -p no:cacheprovider --basetemp .pytest-v22-feedback tests/test_workflow_plan_admission_feedback_successor.py tests/test_workflow_plan_admission_feedback_runner.py tests/test_workflow_plan_admission_feedback_successor_qualification.py
uv run --offline python scripts/build_lean_harness_plan_admission_feedback_qualification.py --repository .
uv run --offline pytest -q -p no:cacheprovider --basetemp .pytest-v22-review tests/test_workflow_plan_admission_feedback_activation_review.py tests/test_workflow_plan_admission_feedback_runner.py
uv run --offline python scripts/build_lean_harness_plan_admission_feedback_activation_review.py --repository .
```

Qualification was 5,281 bytes at file/content `sha256:abeed728...cf0dc`/
`sha256:57f3b3e5...0d30e`; activation review was 6,574 bytes at file/content `sha256:897204b8...270d2`/
`sha256:d1194a9c...1a18d`. Both were byte-stable, public-mock, zero-call evidence. The review permitted only the now
consumed exact no-call R19 candidate preparation.

## Consumed identities

Candidate-v21/R14 and candidate-v23-R19 are immutable `official=false` evidence. Never execute, rehearse, rebuild or
refresh them. Historical source mismatch must fail closed; it cannot transfer an old approval. Exact candidate,
rehearsal, result, diagnosis and cost tuples remain in `docs/09-evidence.md`.
