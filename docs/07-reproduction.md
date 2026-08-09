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

## Validate historical D-126 through D-129 evidence

```powershell
uv run python scripts/build_d126_clean_source_pricing_no_call_preflight.py --validate-post-commit
uv run python scripts/build_d128_d127_terminal_successor_offline.py --validate
uv run python scripts/build_d129_external_sequence_block.py --validate-post-commit
```

These are read-only sealed-history validators. Never invoke their preflight, external, receipt or terminal
creation flags: D-127 through D-129 are consumed/terminal, and validation must not repeat Docker or network
work. Focused historical test commands remain discoverable in Git history and their owning test files.

## Validate the D-130 offline predecessor gate

```powershell
uv run pytest -q tests/test_d130_d129_sequence_block_successor_offline.py
uv run python scripts/build_d130_d129_sequence_block_successor_offline.py --validate
```

This is read-only offline validation of the exact D-129 chain, D-130 source identity and two-stage contract.
It must report status
`D130_D129_EXTERNAL_SEQUENCE_BLOCK_SUCCESSOR_OFFLINE_SOURCE_QUALIFIED_ADMISSION_APPROVAL_REQUIRED`,
13/13 focused tests, and zero receipt/intent/activation/external authority. Its later Stage 1 approval was not
exercised and is non-reusable after D-131 changed the topology. Do not run a D-130 admission or external action
from these predecessor commands.

## Validate the current D-131 local-admission implementation gate

```powershell
uv run pytest -q tests/test_d131_d130_local_admission_offline.py
uv run python scripts/build_d131_d130_local_admission_offline.py --validate-gate
```

This read-only offline path verifies the exact D-130 gate/evidence predecessor, D-131 source and loaded-module
bindings, append-only/new-only writer contracts, orphan/collision/idempotence failures, exact receipt-only and
intent-only Git topology, and activation challenge tuple rendering. It must report status
`D131_D130_LOCAL_ADMISSION_IMPLEMENTATION_OFFLINE_SOURCE_QUALIFIED_APPROVAL_REQUIRED`, 15/15 focused tests,
zero future-writer/challenge invocation during gate creation and no receipt or intent. The selected
D-127–D-131/docs bundle passed 107/107; overlapping selections are not additive.

Do not call `--create-receipt`, `--create-armed-intent` or any activation/external operation without the next
fresh exact approval. Validation must not read credentials, Docker or SDK state and must make no external call.

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

1. preserve the consumed D-128 and D-129 receipts/terminals without retry;
2. preserve the materialized D-130 predecessor and the unexercised, non-reusable D-130 approval;
3. preserve the D-131 offline gate binding the local-admission implementation source;
4. obtain fresh exact D-131-qualified local-admission approval for receipt-only plus durable
   `ARMED_WAITING_EXACT_ACTIVATION` intent-only commits and challenge rendering, with external counts zero;
5. obtain separate exact activation quoting the D-131 gate, receipt, intent and both commit tuples before
   daemon/images/pricing/SDK observation;
6. after a ready successor, obtain separate hash/candidate and exact live approvals.

Do not repurpose `experiments/core.template.yaml`, the D-121 candidate, or a generic CLI flag to bypass that
sequence.
