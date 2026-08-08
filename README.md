# PatchLoop

PatchLoop is a recoverable single coding agent and evaluation harness for scope-compliant software repair.
Agent, hidden evaluator, recovery state and cross-run memory evidence remain separate.

## Current direction

The 96-run A/B/C/D campaign is deferred. The checked-in readiness panel is:

- A: no cross-run memory
- C: the exact three-entry structured bundle
- Moto and Babel, one A/C pair each
- identical model, prompt, tools, context policy and 3M/3600 resource ceiling

The exact suite and plan live under `experiments/`. Delivery, qualification and R2 cost/completion source are
offline-qualified. D-126 is the latest sealed gate. D-127 static passed without key exposure, then Docker
remediation terminally blocked after six read-only CLI calls and before Desktop start, mutation or later phases.

See `docs/current-status.md` for the current checkpoint and closed authority.

## Implemented product path

- Agent phases: INTAKE → REPRODUCE → PLAN → IMPLEMENT → VERIFY → REVIEW → DONE
- Constrained search/read/patch/check/diff/submission tools; no unrestricted agent shell
- Stateless provider turns plus append-only events, checkpoints, CAS and workspace reconciliation
- Rejected-patch recovery and token/cost accounting
- Separate hidden evaluator for acceptance, regression, scope and safety
- Audited dataset roles and a frozen, human-reviewed three-entry memory index
- Exact A-null/C-D110 delivery with replay and condition-aware trace qualification

## Evidence boundary

- D-098 is a development baseline (12 terminal, 11 evaluated, 2 scope-compliant), not held-out evidence.
- D-110 froze three entries; D-112/D-115 left selective scoring unready.
- D-124/D-125 are historical local/mock predecessors; D-121 is deferred.
- D-126 sealed observations, not readiness; no reservation, result, candidate, hash or A/C outcome exists.
- D-127 recorded a terminal blocked Docker-remediation observation: six bounded read-only Docker CLI calls,
  no Desktop start, pull/image-store mutation or container/workload, and no pricing/preflight/gate or live call.

Machine-readable evidence is indexed in `docs/09-evidence.md`.

## Offline quickstart

```powershell
uv sync --extra dev
uv run pytest -q tests/test_d126_clean_source_pricing_no_call_preflight.py
uv run python scripts/build_d126_clean_source_pricing_no_call_preflight.py --validate-post-commit
uv run pytest -q tests/test_documentation_structure.py
git diff --check
```

These paths validate sealed local evidence only. There is intentionally no supported live A/C command.

## CLI surface

Use `uv run patchloop --help` to discover the CLI.

CLI availability does not imply readiness. The approved D-127 scope stops at blocker remediation, official
pricing capture and a repeated no-call preflight. The current receipt is terminal/idempotent blocked after
read-only Docker observation, so it cannot be retried after Desktop state changes. A user must first start
Docker Desktop while safely accounting for existing restart-policy containers, or explicitly expand the
incidental-start authority; either route then needs a separate successor approval. A later ready successor
still needs separate exact-gate approval before hash/candidate preparation and live approval.

## Documentation

Use `docs/00-index.md` for active authority/navigation. Historical narratives live under `docs/archive/`.
