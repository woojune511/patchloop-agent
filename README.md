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
offline-qualified. D-129 is the current offline successor gate and still requires exact approval. It preserves
D-128 as terminal-blocked history while recording the user's later manual endpoint check as self-attestation,
not as agent-observed or fresh future readiness.

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
- D-129 made zero Docker/network/SDK/provider/evaluator/agent calls. It records two user-reported manual checks:
  first unavailable/rc 1, then client/server 29.6.2 on linux/amd64/rc 0, with no pre-existing container
  auto-start reported. The agent did not independently observe these facts and a future phase must reobserve.
- D-129 focused tests passed 12/12; the selected union passed 115/115 and includes the focused tests.

Machine-readable evidence is indexed in `docs/09-evidence.md`.

## Offline quickstart

```powershell
uv sync --extra dev
uv run pytest -q tests/test_d129_d128_terminal_successor_offline.py
uv run python scripts/build_d129_d128_terminal_successor_offline.py --validate
uv run pytest -q tests/test_documentation_structure.py
git diff --check
```

These paths validate sealed local evidence only. There is intentionally no supported live A/C command.

## CLI surface

Use `uv run patchloop --help` to discover the CLI.

CLI availability does not imply authority. D-129 has no approval receipt, external attempt, pricing/preflight,
execution hash/candidate, reservation, cost or A/C result. A future no-call phase requires approval quoting the
exact D-129 gate tuple and the local evidence commit that tracks it. The agent still must not start Desktop or
the daemon; hash/candidate and live execution remain later gates.

## Documentation

Use `docs/00-index.md` for active authority/navigation. Historical narratives live under `docs/archive/`.
