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

## Historical validators

D-123 through D-131 commands remain in their owning scripts, tests and Git history. Use only explicit
sealed/read-only validation modes when auditing them. D-127 through D-129 are consumed/terminal; D-130/D-131
artifacts are immutable predecessors. Never invoke an old creation, preflight or external mode to reconstruct
current authority.

## Validate the current D-132 external-activation implementation gate

```powershell
uv run pytest -q tests/test_d132_d130_external_activation_offline.py
uv run python scripts/build_d132_d130_external_activation_offline.py --validate-offline-gate-post-commit
```

This path checks the exact D-131 gate/D-130 receipt/intent topology, source and loaded modules, future-artifact
absence at source preparation, activation receipt-only topology, and the ordered committed-attempt /
action-started / terminal-transition state machine. It also covers exact no-start Docker pull scope, bounded
replayable pricing, credential-presence/official-endpoint SDK no-call behavior, collision/orphan/idempotence and
READY/BLOCKED final gates under mocks.

The focused set passed 15/15 and the selected regression passed 170/170 including those tests; do not add the
counts. Post-commit validation must report
`D132_D130_EXTERNAL_ACTIVATION_IMPLEMENTATION_OFFLINE_SOURCE_QUALIFIED_FRESH_ACTIVATION_REQUIRED` and zero
future writer/helper invocations. Do not call `--create-activation-receipt`, `--run-external-preflight` or any
future-artifact mode without a fresh exact D-132-qualified activation. Offline validation must not read
credentials, Docker or SDK state and must make no external call.

Memory and D-121 historical checks remain discoverable in their owning tests/scripts. Run only offline or
sealed-historical modes; never infer current execution authority from a readable artifact.

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
2. preserve the D-130/D-131 predecessor and exact receipt-only plus durable
   `ARMED_WAITING_EXACT_ACTIVATION` intent-only commits;
3. preserve the D-132 source gate and its exact gate-add/active-docs evidence commit;
4. obtain fresh exact D-132-qualified activation quoting the D-132 gate/evidence plus D-131 gate, receipt,
   intent and both commit tuples, then create the activation receipt-only commit;
5. commit each ordered phase attempt before its action and commit each action-started+terminal transition before
   the next phase; do not retry an uncertain, orphaned or blocked phase;
6. after a ready final successor gate, obtain separate hash/candidate and exact live approvals.

Do not repurpose `experiments/core.template.yaml`, the D-121 candidate, or a generic CLI flag to bypass that
sequence.
