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
offline-qualified. D-129 is terminal-blocked after one approved official-docs tool open preceded its machine
receipt and durable attempt. D-130 now exact-binds that incident offline and requires local-admission approval;
it grants no external authority.

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
- D-126 sealed observations, not readiness; D-127 and D-128 are terminal-blocked historical predecessors.
- D-128 made three read-only calls, all return code 1; every mutation and later phase remained zero.
- D-129 made one agent-visible official-docs open before receipt; underlying HTTP count is unknown. Canonical
  pricing capture, Docker, SDK, provider/evaluator/agent and all execution/cost paths stayed zero.
- D-130 gate `d130_443b0bc935ba6affd4a009dee780ae85ec1ecdc1e3ce62edcd566e12307c74db`
  qualifies only the offline two-stage admission contract. Focused tests passed 13/13 and the selected
  D-127–D-130/docs regression bundle passed 92/92; overlapping selections are not additive.

Machine-readable evidence is indexed in `docs/09-evidence.md`.

## Offline quickstart

```powershell
uv sync --extra dev
uv run pytest -q tests/test_d129_d128_terminal_successor_offline.py
uv run pytest -q tests/test_d129_external_sequence_block.py
uv run python scripts/build_d129_external_sequence_block.py --validate-terminal
uv run pytest -q tests/test_d130_d129_sequence_block_successor_offline.py
uv run python scripts/build_d130_d129_sequence_block_successor_offline.py --validate
uv run pytest -q tests/test_documentation_structure.py
git diff --check
```

These paths validate sealed local evidence only. There is intentionally no supported live A/C command.

## CLI surface

Use `uv run patchloop --help` to discover the CLI.

CLI availability does not imply authority. D-129 has a consumed receipt and procedural terminal but no external
attempt or canonical pricing/preflight. D-130 is offline-source-qualified only: stage 1 may create and commit
the exact receipt and durable `ARMED_WAITING_EXACT_ACTIVATION` intent, then render a challenge, while all
external actions stay zero. A separate exact stage-2 activation is required; hash/candidate, cost and A/C remain
closed.

## Documentation

Use `docs/00-index.md` for active authority/navigation. Historical narratives live under `docs/archive/`.
