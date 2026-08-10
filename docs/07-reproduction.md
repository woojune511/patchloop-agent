# Current reproduction and validation

Historical per-milestone commands are archived at
`docs/archive/snapshots/d121/07-reproduction.full.md`. Commands below are the supported current paths.

## Environment

- Windows/PowerShell
- Python 3.12+
- `uv` with the repository lockfile
- Docker Desktop only for a separately approved Docker step

```powershell
uv sync --offline --frozen --extra dev
```

## Validate the A/C sources and fixed-bundle delivery

```powershell
uv run --offline --frozen pytest -q tests/test_ac_structured_pilot_plan.py tests/test_ac_fixed_bundle_readiness.py
uv run --offline --frozen pytest -q tests/test_ac_fixed_bundle_cost_completion.py
uv run --offline --frozen pytest -q tests/test_fixed_bundle_delivery.py tests/test_d122_ac_fixed_bundle_qualification.py
uv run --offline --frozen python scripts/build_d122_ac_fixed_bundle_qualification.py --validate-sealed-historical
```

These are offline checks for the four-row source, A-null/C-exact bundle contract, trace qualification and
historical D-122 bytes. They grant no live, retrieval, provider, Docker, hash/candidate or cost authority.

## Validate the current D-142 SDK successor gate

```powershell
$d142Basetemp = Join-Path 'C:\Users\geonj\AppData\Local\Temp' ('patchloop-d142-' + [guid]::NewGuid())
& .\.venv\Scripts\python.exe -E -s -B -m pytest -q -p no:cacheprovider `
  --basetemp $d142Basetemp tests/test_d142_d141_sdk_blocked_successor_offline.py
& .\.venv\Scripts\python.exe -E -s -B scripts/build_d142_d141_sdk_blocked_successor_offline.py `
  --validate-gate-postcommit
```

The validator rebinds the complete D-141 gate/receipt/attempt/ACTION_STARTED+BLOCKED topology, exact four-add D-142
source commit, loaded modules and gate+10-doc evidence commit. It checks append-only/new-only,
collision/orphan/idempotence, TOCTOU and exact Git topology. Fully injected/mocked focused tests passed 170/170.
This count is separate from documentation and static checks.

D-141 became BLOCKED with false/false/false presence bits after three membership checks; value/`.env`, child,
import/probe/transport/network/provider counts were 0. D-142 validation does not repeat it and performs no environment
membership/value, credential provisioning, SDK, child, endpoint, network or Docker observation.

Do not call `--create-activation-receipt`, `--create-sdk-attempt` or `--run-sdk-preflight` without a fresh exact
D-142 activation quoting gate, source and evidence-commit tuples. The rendered template is not approval. Never
invoke a historical creation/external mode to repair, resume or retry a consumed phase.

## Historical validators

D-123 through D-141 commands remain in their owning scripts, tests and Git history. Use only explicit
sealed/read-only modes when auditing them. D-132 is a consumed incident; D-134's gate is preserved and invalid;
D-135 is procedural incident evidence; D-136 pricing, D-137 no-call phases and D-138 through D-141 SDK are consumed.

## Static and documentation checks

```powershell
& .\.venv\Scripts\ruff.exe check patchloop tests
& .\.venv\Scripts\ruff.exe format --check patchloop tests
& .\.venv\Scripts\python.exe -E -s -B -m compileall -q patchloop tests
$docsBasetemp = Join-Path 'C:\Users\geonj\AppData\Local\Temp' ('patchloop-docs-' + [guid]::NewGuid())
& .\.venv\Scripts\python.exe -E -s -B -m pytest -q -p no:cacheprovider `
  --basetemp $docsBasetemp tests/test_documentation_structure.py
git diff --check
```

Large repository-wide suites may include historical tests that intentionally assert a superseded absent state.
Prefer the current focused bundles and explain any historical-state mismatch instead of rewriting sealed
evidence.

## Live execution

There is no supported live A/C command. The current sequence is:

1. Preserve D-132, D-136, D-137 and D-138 through D-141 consumed chains without repair.
2. Validate the exact D-142 gate+10-active-doc evidence commit.
3. Obtain a fresh exact D-142 activation quoting gate, source and evidence-commit tuples.
4. Commit only the activation receipt, then the SDK attempt.
5. Launch the inherited-environment repository-venv Python with `-E -s -B`; write/fsync ACTION_STARTED immediately
   before membership-only checks. Never read values or `.env`.
6. If eligible, run SDK provenance and zero-dispatch synthetic validation only in the bounded `env={}` child
   with a fixed nonsecret placeholder and no ambient forwarding. Do not claim pre-bootstrap network absence.
   Credential provisioning is a separate action authorized by neither preparation nor activation; no credential
   value belongs in approval/chat.
7. Commit READY/BLOCKED terminal, or marker only after failure; never retry. Request a D-143 offline successor.

Do not repurpose a historical receipt, attempt, marker, gate, template or generic CLI flag to bypass this
sequence.
