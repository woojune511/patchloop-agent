# Current reproduction and validation

Historical per-milestone commands are archived at
`docs/archive/snapshots/d121/07-reproduction.full.md`. Commands below are the supported current paths.

## Environment

- Windows/PowerShell
- Python 3.12+
- `uv` with the repository lockfile
- Docker Desktop only for explicitly authorized Docker steps

```powershell
uv sync --extra dev
```

## Validate the A/C sources

```powershell
uv run pytest -q tests/test_ac_structured_pilot_plan.py tests/test_ac_fixed_bundle_readiness.py
uv run pytest -q tests/test_ac_fixed_bundle_cost_completion.py
```

This checks the non-executable design plan, exact experiment-v2 suite, purpose/profile/schedule/source hashes,
A-no-index/C-D110 manifests and mocked runtime admission. Git, Docker and SDK observations are mocked; the
tests perform no provider, evaluator, embedding, network or live Docker call.

## Validate fixed-bundle delivery

```powershell
uv run pytest -q tests/test_fixed_bundle_delivery.py tests/test_d122_ac_fixed_bundle_qualification.py
uv run python scripts/build_d122_ac_fixed_bundle_qualification.py --validate-sealed-historical
```

These checks cover A-null/C-exact delivery, all-request evidence, request artifact/CAS/context/consumer replay,
condition-aware trace qualification, tamper rejection and guards against retrieval, embedding and network
use. Validation of the sealed gate is read-only and must report candidate readiness false and all live-call
counts zero.

`--validate-sealed-historical` validates the exact D-122 predecessor bytes without replaying changed current
implementation as historical evidence.

## Validate D-123 through D-125 historical sources

```powershell
uv run python scripts/build_d123_ac_cost_completion_qualification.py --validate-sealed-historical
uv run python scripts/build_d124_ac_settlement_reconciliation_correction.py --validate-sealed-historical
uv run python scripts/build_d125_ac_runtime_finalization_qualification.py --validate-sealed-historical
```

These validate exact historical bytes without promoting them to current source evidence. D-124 corrects
D-123 prospectively; D-125 remains local/mock only.

## Validate current D-126 blocked preflight

```powershell
uv run pytest -q tests/test_d126_clean_source_pricing_no_call_preflight.py
uv run python scripts/build_d126_clean_source_pricing_no_call_preflight.py --validate-post-commit
```

The tests use mocked Git/pricing/Docker/SDK observations. `--validate-post-commit` validates the sealed
evidence-commit topology; it does not repeat the public pricing GET or Docker commands. Do not invoke
`--run-preflight` to refresh observations without separate exact authority.

## Validate D-127 source and blocked-phase contracts

```powershell
uv run pytest -q tests/test_d127_docker_remediation.py tests/test_d127_pricing_capture.py tests/test_d127_d126_successor_no_call_preflight.py
```

This mocked path creates no downstream evidence or external call. In the recorded production path, an
exact-key ephemeral `.env` loader passed static without exposing the value, then Docker remediation recorded
six bounded read-only CLI calls and terminally blocked before Desktop start or mutation. Do not use
`--run-external-preflight`: the existing receipt is terminal/idempotent blocked, and renewed work requires a
separate exact successor approval.

## Validate current memory contracts

```powershell
uv run pytest -q tests/test_memory.py tests/test_d110_index_freeze_execution.py
uv run pytest -q tests/test_d112_retrieval_readiness_probe.py tests/test_d114_d112_validator_correction.py
```

The D-112 test may require only sealed-historical replay depending on the selected test. Do not invoke a model
or current-input path merely to validate the checked-in score evidence.

## Historical D-121 validation

```powershell
uv run python scripts/run_d121_hash_only_isolation_successor.py --validate-preparation
uv run pytest -q tests/test_d121_hash_only_isolation_successor.py
```

Run this only when auditing the historical/deferred lane. `--validate-preparation` is read-only and must not
start the successor. Do not call private execution helpers or reconstruct authority from readable artifacts.

## Static checks

```powershell
uv run ruff check patchloop tests
uv run ruff format --check patchloop tests
uv run python -m compileall -q patchloop tests
git diff --check
```

Large repository-wide suites may include historical tests that intentionally assert a pre-successor absent
state. Prefer the current focused bundles and explain any expected historical-state failure rather than
rewriting sealed history.

## Documentation checks

```powershell
uv run pytest -q tests/test_documentation_structure.py
git diff --check
```

The D-121 snapshot is historical evidence and is not mandatory reading. The test verifies active-file size,
historical snapshot hashes, the single D-121 prose owner and the closed four-run authority boundary.

## Live execution

There is no supported live A/C command. Although the exact suite is an `ExperimentSuite` source, a future live
command must appear only after:

1. preserve the current D-127 terminal blocked remediation evidence;
2. manually establish safe Docker Desktop state or explicitly expand incidental-start authority, then obtain
   a separate exact successor approval and complete its bounded remediation/pricing/no-call scope;
3. after a ready successor, obtain separate exact-gate approval for execution-hash and candidate creation;
4. obtain separate approval of the exact candidate triple, execution hash and $55 cap.

Do not repurpose `experiments/core.template.yaml`, the D-121 candidate, or a generic CLI flag to bypass that
sequence.
