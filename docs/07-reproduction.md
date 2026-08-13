# Current reproduction and execution path

Historical D/V commands are preserved in Git and `docs/archive/`; they are not the current runbook.

## Install and validate offline

```powershell
uv sync --offline --frozen --extra dev
& .\.venv\Scripts\python.exe -E -s -B -m pytest -q -p no:cacheprovider `
  tests/test_fast_preflight.py `
  tests/test_evaluator_v2_source_qualification.py `
  tests/test_evaluator_v2_contracts.py `
  tests/test_ac_fixed_bundle_cost_completion.py `
  tests/test_documentation_structure.py
& .\.venv\Scripts\python.exe -E -s -B `
  scripts/build_evaluator_v2_ac_source_qualification.py
```

These commands validate source, contracts and synthetic evidence only. They make no Docker, SDK transport,
provider, evaluator or agent call and grant no paid authority.

## Build the execution candidate

The repository-root `.env` must contain exactly one assignment, `OPENAI_API_KEY`. The command temporarily injects
that value and never prints it. It performs local Git/SDK checks and read-only Docker/image inspection; it makes no
container, network, provider, evaluator or agent call.

```powershell
& .\.venv\Scripts\patchloop.exe preflight `
  --suite experiments/dev-validation-ac-fixed-bundle-readiness-20260813-fast-r1.yaml `
  --env-file .env `
  --max-attempts 3
```

Only transient Docker/process readiness failures retry, within this command. Schema, source, credential, pricing and
policy failures stop immediately. Success means `execution_candidate_ready=true`; `ready` remains false until paid
approval and the exact execution hash are supplied.

## Run the four-row A/C campaign

After reviewing the candidate, one explicit approval must bind its exact `execution_hash` and the suite's `$55.00`
hard cap. Only then run:

```powershell
& .\.venv\Scripts\patchloop.exe evaluate `
  --suite experiments/dev-validation-ac-fixed-bundle-readiness-20260813-fast-r1.yaml `
  --env-file .env `
  --approve-live-cost `
  --approved-execution-hash sha256:<exact-candidate-hash>
```

This is the provider/agent/evaluator boundary. SDK transport retry and outcome-bearing row replacement remain zero.
The four rows must all be terminal, trace-qualified, cost-settled and evaluator-v2 receipt-qualified; otherwise the
panel is inconclusive. This approval does not authorize held-out A/C or B/D.

## Static checks

```powershell
& .\.venv\Scripts\ruff.exe check patchloop tests
& .\.venv\Scripts\ruff.exe format --check patchloop tests
& .\.venv\Scripts\python.exe -E -s -B -m compileall -q patchloop tests
git diff --check
```

Historical attempts stay immutable. Their old one-use configuration policy does not govern this reusable preflight.
