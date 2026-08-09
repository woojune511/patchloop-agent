# Current reproduction and validation

Historical per-milestone commands are archived at
`docs/archive/snapshots/d121/07-reproduction.full.md`. Commands below are the supported current paths.

## Environment

- Windows/PowerShell
- Python 3.12+
- `uv` with the repository lockfile
- Docker Desktop only for a separately approved Docker step

```powershell
uv sync --extra dev
```

## Validate the A/C sources and fixed-bundle delivery

```powershell
uv run pytest -q tests/test_ac_structured_pilot_plan.py tests/test_ac_fixed_bundle_readiness.py
uv run pytest -q tests/test_ac_fixed_bundle_cost_completion.py
uv run pytest -q tests/test_fixed_bundle_delivery.py tests/test_d122_ac_fixed_bundle_qualification.py
uv run python scripts/build_d122_ac_fixed_bundle_qualification.py --validate-sealed-historical
```

These are offline checks for the four-row source, A-null/C-exact bundle contract, trace qualification and
historical D-122 bytes. They grant no live, retrieval, provider, Docker, hash/candidate or cost authority.

## Validate the current D-137 no-call-preflight successor gate

```powershell
uv run pytest -q tests/test_d137_d136_no_call_preflight_successor_offline.py
uv run python scripts/build_d137_d136_no_call_preflight_successor_offline.py `
  --validate-gate-postcommit
```

The validator rebinds the complete D-136 gate/receipt/attempt/STARTED/terminal topology, exact four-add D-137
source commit, loaded modules and gate+10-doc evidence commit. It checks append-only/new-only,
collision/orphan/idempotence, TOCTOU and exact Git topology. Focused mocked tests passed 62/62; the selected
current-compatible set passed 112/112 with focused included, so counts are not additive.

D-136's replayable terminal records one official public GET, HTTP 200, zero redirects and 3,735 bytes;
provider/evaluator/agent calls and cost are 0. D-137 validation does not repeat that request. Its mocked Docker
and SDK helpers use injected dependencies only and make no real Docker, SDK, credential/environment-value,
endpoint or network observation.

Do not call `--create-activation-receipt`, `--create-docker-attempt`, `--run-docker-preflight`,
`--create-sdk-attempt` or `--run-sdk-preflight` without a fresh exact D-137 activation quoting the gate tuple,
source commit/tree and evidence-commit tuple. The rendered activation template is not approval. Never invoke a
historical creation/external mode to repair, resume or retry a consumed phase.

## Historical validators

D-123 through D-136 commands remain in their owning scripts, tests and Git history. Use only explicit
sealed/read-only modes when auditing them. D-132 is a consumed incident; D-134's gate is preserved and invalid;
D-135 is procedural incident evidence; D-136 pricing succeeded and is consumed.

## Static and documentation checks

```powershell
uv run ruff check patchloop tests
uv run ruff format --check patchloop tests
uv run python -m compileall -q patchloop tests
uv run pytest -q tests/test_documentation_structure.py
git diff --check
```

Large repository-wide suites may include historical tests that intentionally assert a superseded absent state.
Prefer the current focused bundles and explain any historical-state mismatch instead of rewriting sealed
evidence.

## Live execution

There is no supported live A/C command. The current sequence is:

1. Preserve the consumed D-132 and D-136 chains and the D-134/D-135 incident evidence without repair.
2. Validate the exact D-137 gate+10-active-doc evidence commit.
3. Obtain a fresh exact D-137 activation quoting gate, source and evidence-commit tuples.
4. Create and commit only the activation receipt, then the Docker attempt.
5. Write/fsync Docker ACTION_STARTED immediately before read-only observation. Commit READY/BLOCKED terminal,
   or preserve marker only after failure; never retry.
6. Only after committed Docker READY, create the separate SDK attempt and use the same marker-first one-use
   pattern for the no-call SDK observation.
7. Only after both committed READY terminals may separate hash/candidate, cost and live A/C approvals be considered.

Do not repurpose a historical receipt, attempt, marker, gate, template or generic CLI flag to bypass this
sequence.
