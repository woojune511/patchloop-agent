# PatchLoop

PatchLoop is a recoverable single coding agent and evaluation harness for scope-compliant software repair.
Agent, hidden evaluator, recovery state and cross-run memory evidence remain separate.

## Current direction

The 96-run A/B/C/D campaign is deferred. The checked-in readiness panel is:

- A: no cross-run memory
- C: the exact three-entry structured bundle
- Moto and Babel, one A/C pair each
- identical model, prompt, tools, context policy and 3M/3600 resource ceiling

The suite, delivery and R2 cost/completion source are offline-qualified. D-129 is terminal sequence-blocked.
D-131-qualified local admission later created exact D-130 receipt and durable armed-intent commits, but no
external action. D-132 now qualifies the external-activation implementation source only; fresh activation is
still required.

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
- D-129 has one pre-receipt docs open with unknown transport count; later external/runtime/cost paths stayed zero.
- D-131 gate `d131_849502e63d33aa3c8ceea8dc03faf0ff86e8ec51db9321fa13544df15a4af057`
  precedes the exact D-130 receipt/intent chain.
- D-132 gate `d132_ae224ab320e74bf871b74b0c9df23f88c5de170dfd26e7724aa234f29b2b0ba7`
  binds source commit `ccf898d869342a9d5da42a1fef2c00e593fe91b4` and qualifies only activation receipt,
  committed-attempt/action-started/terminal transitions and final-gate validation. Focused tests passed 15/15;
  the selected regression passed 170/170 with the focused set included, so counts are not additive.
- The pre-D-132 activation request/challenge was received but explicitly was not activation. It is unexercised
  and non-reusable; no D-132 activation receipt, phase artifact, final gate or external action exists.

Machine-readable evidence is indexed in `docs/09-evidence.md`.

## Offline quickstart

```powershell
uv sync --extra dev
uv run pytest -q tests/test_d129_d128_terminal_successor_offline.py
uv run pytest -q tests/test_d129_external_sequence_block.py
uv run python scripts/build_d129_external_sequence_block.py --validate-terminal
uv run pytest -q tests/test_d130_d129_sequence_block_successor_offline.py
uv run python scripts/build_d130_d129_sequence_block_successor_offline.py --validate
uv run pytest -q tests/test_d131_d130_local_admission_offline.py
uv run python scripts/build_d131_d130_local_admission_offline.py --validate-gate
uv run pytest -q tests/test_d132_d130_external_activation_offline.py
uv run python scripts/build_d132_d130_external_activation_offline.py --validate-offline-gate-post-commit
uv run pytest -q tests/test_documentation_structure.py
git diff --check
```

These paths validate sealed local evidence only. There is intentionally no supported live A/C command.

## CLI surface

Use `uv run patchloop --help` to discover the CLI.

CLI availability does not imply authority. The D-130 local receipt and durable
`ARMED_WAITING_EXACT_ACTIVATION` intent exist, but do not authorize external work. Only a fresh exact
D-132-qualified activation quoting the gate/evidence tuple and the D-131 gate, receipt, intent and commit tuples
may create the activation receipt and begin the attempt-first sequence. Until then credential/Docker/SDK,
official pricing, hash/candidate, cost and A/C remain closed.

## Documentation

Use `docs/00-index.md` for active authority/navigation. Historical narratives live under `docs/archive/`.
