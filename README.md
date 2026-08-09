# PatchLoop

PatchLoop is a recoverable single coding agent and evaluation harness for scope-compliant software repair.
Agent, hidden evaluator, recovery state and cross-run memory evidence remain separate.

## Current direction

The 96-run A/B/C/D campaign is deferred. The checked-in readiness panel is:

- A: no cross-run memory
- C: the exact three-entry structured bundle
- Moto and Babel, one A/C pair each
- identical model, prompt, tools, context policy and 3M/3600 resource ceiling

The suite, delivery and R2 cost/completion source are offline-qualified. The earlier D-132 activation remains
consumed at its official-pricing action-started boundary and is never retried. D-135 now seals that incident
with a local procedural terminal. D-136 offline-qualifies a distinct fixed pricing helper and future evidence
topology; it does not activate or perform pricing capture.

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
- D-135 procedural terminal commit `98f4560e718145bc7465732c1a3d2f5a4ea8d786` preserves the consumed
  incident without inventing canonical response evidence.
- D-136 gate `d136_aef9768fcc24b48df09034d14aefcd02b1812531fe77bf56ca1601ac4e5e00fd`
  binds source `96916ac481ac8beced2db0be9022607e0705e018`. The new helper closes every returned
  `Response` in `try/finally`; focused tests passed 29/29 and the selected relevant set passed 102/102 with
  focused included. No D-136 receipt, attempt, marker, pricing evidence or terminal exists; external actions
  are 0.

Machine-readable evidence is indexed in `docs/09-evidence.md`.

## Offline quickstart

```powershell
uv sync --extra dev
uv run pytest -q tests/test_d136_d135_fixed_pricing_successor_offline.py
uv run python scripts/build_d136_d135_fixed_pricing_successor_offline.py --validate-gate-postcommit
uv run pytest -q tests/test_documentation_structure.py
git diff --check
```

These paths validate sealed local evidence only. There is intentionally no supported live A/C command.

## CLI surface

Use `uv run patchloop --help` to discover the CLI.

CLI availability does not imply authority. A fresh exact D-136 activation must quote the gate tuple, source
commit/tree and gate+docs evidence-commit tuple. It may use only the qualified
receipt/attempt/marker/capture sequence; Docker and SDK preflight remain separate, and hash/candidate, cost
and A/C authority remain closed.

## Documentation

Use `docs/00-index.md` for active authority/navigation. Historical narratives live under `docs/archive/`.
