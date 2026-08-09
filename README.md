# PatchLoop

PatchLoop is a recoverable single coding agent and evaluation harness for scope-compliant software repair.
Agent, hidden evaluator, recovery state and cross-run memory evidence remain separate.

## Current direction

The 96-run A/B/C/D campaign is deferred. The checked-in readiness panel is:

- A: no cross-run memory
- C: the exact three-entry structured bundle
- Moto and Babel, one A/C pair each
- identical model, prompt, tools, context policy and 3M/3600 resource ceiling

The suite, delivery and R2 cost/completion source are offline-qualified. The earlier D-132 activation is now
consumed at its official-pricing action-started boundary and is not retried. D-135 offline-qualifies only a
corrected procedural-terminal writer; an exact local-only terminalization approval is still required.

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
- D-121 is deferred; D-124/D-131 are historical and D-129 is terminal blocked.
- D-132 activation/pricing attempt are consumed at the D-133-preserved action-started marker; no retry or
  backfill is allowed. Application-level `client.send` returned a `Response` once, while underlying HTTP and
  response fields remain unknown/unretained. Completed/replayable canonical pricing evidence count is 0, its
  artifact is absent and replay bytes are 0.
- D-134's ambiguous gate is preserved exactly but has no qualification or terminalization authority.
- Corrected D-135 gate `d135_7e67561d187cfb44440790052a95fc8b95a4006fe886e0f7c3dce9bae437e8c6`
  binds source `ca50402aa8d3965ea384563262c713c6090d2ecf`. Focused tests passed 15/15 and the selected
  set passed 85/85 with focused included. The procedural terminal is absent; current-turn external actions are 0.

Machine-readable evidence is indexed in `docs/09-evidence.md`.

## Offline quickstart

```powershell
uv sync --extra dev
uv run pytest -q tests/test_d135_d134_ambiguous_gate_correction_offline.py
uv run python scripts/build_d135_d134_ambiguous_gate_correction_offline.py --validate-offline-gate-post-commit
uv run pytest -q tests/test_documentation_structure.py
git diff --check
```

These paths validate sealed local evidence only. There is intentionally no supported live A/C command.

## CLI surface

Use `uv run patchloop --help` to discover the CLI.

CLI availability does not imply authority. A new exact D-135 gate/evidence approval may create only one local
procedural terminal and terminal-only commit. It is not pricing evidence and grants no external, successor,
hash/candidate, cost or A/C authority.

## Documentation

Use `docs/00-index.md` for active authority/navigation. Historical narratives live under `docs/archive/`.
