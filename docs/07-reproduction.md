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

## Validate the current D-136 fixed-pricing successor gate

```powershell
uv run pytest -q tests/test_d136_d135_fixed_pricing_successor_offline.py
uv run python scripts/build_d136_d135_fixed_pricing_successor_offline.py `
  --validate-gate-postcommit
```

The validator rebinds the exact D-135 terminal bytes/commit, predecessor gate topology, four-path D-136 source
commit and loaded modules. It checks append-only/new-only, collision/orphan/idempotence and exact Git topology.
The fixed helper preserves the exact URL, unauthenticated request, redirect, decoded-size and replay bounds,
but replaces response context-manager use with explicit `try/finally` close semantics.

The corrected boundary records one application-level unauthenticated `client.send` returning one `Response`.
Underlying HTTP request count/completion and response status, headers, body and redirects remain
unknown/unretained; completed/replayable
canonical pricing evidence count is 0, no canonical artifact exists and retained replay bytes are 0.
Validation must
not reconstruct a response or infer a GET count.

Focused mocked tests passed 29/29. The selected relevant set passed 102/102 with focused tests included, so
these counts are not additive. The mocks cover a `Response` without `__enter__`, close-on-success, redirects
and errors; they are not official pricing evidence. D-136 source preparation and gate construction made zero
official-docs/network/pricing, Docker, SDK/credential, provider/evaluator/agent, memory/retrieval,
hash/candidate, cost or A/C calls.

Do not call `--create-activation-receipt`, `--create-pricing-attempt` or `--capture-pricing` without a fresh
exact D-136 activation quoting the gate tuple, source commit/tree and evidence-commit tuple. The output of
`--render-activation-template` is not approval. Never invoke a D-132/D-134 creation or external mode to repair
or resume the consumed phase.

## Historical validators

D-123 through D-135 commands remain in their owning scripts, tests and Git history. Use only explicit
sealed/read-only modes when auditing them. D-127 through D-129 are terminal or consumed; D-132 pricing is
consumed; D-134's ambiguous gate is preserved and invalid; D-135's terminal is immutable incident evidence.

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

1. Preserve the D-132 consumed attempt/marker, invalid D-134 gate and D-135 procedural terminal without repair.
2. Preserve the D-136 gate in its exact gate-add/10-active-doc evidence commit.
3. Obtain a fresh exact D-136 activation quoting the gate tuple, source commit/tree and evidence-commit tuple.
4. Create and commit only the activation receipt, then only the pricing attempt.
5. Immediately before helper dispatch, write/fsync the action-started marker. Success commits marker plus
   replayable pricing terminal; failure preserves marker only and consumes the activation with no retry.
6. Qualify Docker/SDK no-call preflight as a later separate offline successor.
7. Only after a ready successor gate may separate hash/candidate, cost and live A/C approvals be considered.

Do not repurpose a historical receipt, attempt, marker, gate, template or generic CLI flag to bypass this
sequence.
