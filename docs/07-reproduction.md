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

## Validate the current D-135 correction gate

```powershell
uv run pytest -q tests/test_d135_d134_ambiguous_gate_correction_offline.py
uv run python scripts/build_d135_d134_ambiguous_gate_correction_offline.py `
  --validate-offline-gate-post-commit
```

The validator rebinds the exact D-132 pricing attempt and marker, D-134 source, preserved ambiguous D-134 gate,
its preservation-only commit and the D-135 source/loaded modules. It requires the D-134 recorded status and
next-gate text to remain invalid and non-authoritative, and it validates the corrected future terminal contract
under a distinct D-135 path.

The corrected boundary records one application-level unauthenticated `client.send` returning one `Response`.
Underlying HTTP request count/completion and response status, headers, body and redirects remain
unknown/unretained; completed/replayable
canonical pricing evidence count is 0, no canonical artifact exists and retained replay bytes are 0.
Validation must
not reconstruct a response or infer a GET count.

Focused tests passed 15/15. The selected regression passed 85/85 with focused tests included, so these counts
are not additive. D-135 source preparation and gate construction made zero official-docs/network, Docker,
SDK/credential, provider/evaluator/agent, memory/retrieval, hash/candidate, cost or A/C calls.

Do not call `--create-procedural-terminal` without a fresh exact D-135-qualified terminalization approval that
quotes the gate and evidence-commit tuple. The template printed by `--print-terminalization-template` is not
approval. Never invoke a D-132 or D-134 creation/external mode to repair or resume the consumed phase.

## Historical validators

D-123 through D-134 commands remain in their owning scripts, tests and Git history. Use only explicit
sealed/read-only modes when auditing them. D-127 through D-129 are terminal or consumed; D-132 pricing is
consumed; D-134's ambiguous gate is preserved but cannot authorize its procedural terminal.

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

1. Preserve the D-132 consumed attempt/marker and the invalid, non-authoritative D-134 gate without repair.
2. Preserve the D-135 gate in its exact gate-add/10-active-doc evidence commit.
3. Obtain a fresh exact D-135-qualified local-only terminalization approval.
4. Create and commit only the D-135 procedural terminal; this performs no external action and is not canonical
   pricing evidence.
5. Qualify and approve any fixed pricing/preflight successor separately before another external action.
6. Only after a ready successor gate may separate hash/candidate, cost and exact live approvals be considered.

Do not repurpose a historical receipt, attempt, marker, gate, template or generic CLI flag to bypass this
sequence.
