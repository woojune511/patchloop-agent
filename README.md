# PatchLoop

PatchLoop is a recoverable single coding agent and evaluation harness for scope-compliant software repair.
Agent, hidden evaluator, recovery state and cross-run memory evidence remain separate.

## Current direction

The 96-run A/B/C/D campaign is deferred. The checked-in readiness panel is:

- A: no cross-run memory
- C: the exact three-entry structured bundle
- Moto and Babel, one A/C pair each
- identical model, prompt, tools, context policy and 3M/3600 resource ceiling

The suite, delivery and R2 cost/completion source are offline-qualified. D-136 pricing succeeded and is
consumed. D-137 then completed bounded Docker READY and SDK missing-key BLOCKED no-call phases; it is consumed.
D-138 now qualifies only a fresh SDK successor source and future one-use topology.

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
- D-132 through D-135 preserve one consumed pricing incident without retry, response reconstruction or canonical
  pricing evidence. D-136 later preserved one successful public GET and is also consumed.
- D-137 completed exact receipt, Docker attempt/READY transition, SDK attempt/BLOCKED transition Git order.
  Docker used eight bounded read-only commands with zero mutation. SDK checked three membership bits, found
  `OPENAI_API_KEY` absent, and performed zero value reads, `.env` reads, SDK import/probe, dispatch or network call.
- D-138 source commit `f1f821cd57feb8e1405929ff949e82892e3de6f9`, tree
  `b493d9c36a8cdcee646e5773ffe81353bf1d5c8a`, is the exact four-add sole child of D-137 transition commit
  `8aa0ebf09b51b5ca6fc6cee90a7136cfb95a8a01`. Gate
  `d138_fb8eb1890fc6b9723e9c1e7651eaccc6881a94ab277e94b16a8f6ef2fae41e1f` is source-qualified only;
  injected-mock focused tests passed 168/168. No D-138 runtime artifact or environment/SDK/network/Docker
  observation exists.

Machine-readable evidence is indexed in `docs/09-evidence.md`.

## Offline quickstart

```powershell
uv sync --offline --frozen --extra dev
$d138Basetemp = Join-Path 'C:\Users\geonj\AppData\Local\Temp' ('patchloop-d138-' + [guid]::NewGuid())
& .\.venv\Scripts\python.exe -E -s -B -m pytest -q `
  -p no:cacheprovider --basetemp $d138Basetemp tests/test_d138_d137_sdk_blocked_successor_offline.py
& .\.venv\Scripts\python.exe -E -s -B scripts/build_d138_d137_sdk_blocked_successor_offline.py `
  --validate-gate-postcommit
$docsBasetemp = Join-Path 'C:\Users\geonj\AppData\Local\Temp' ('patchloop-docs-' + [guid]::NewGuid())
& .\.venv\Scripts\python.exe -E -s -B -m pytest -q -p no:cacheprovider `
  --basetemp $docsBasetemp tests/test_documentation_structure.py
git diff --check
```

These paths validate sealed local evidence only. There is intentionally no supported live A/C command.

## CLI surface

Use `uv run --offline --frozen patchloop --help` to discover the CLI.

CLI availability does not imply authority. A fresh exact D-138 activation must quote gate, source and evidence
commit tuples. Its parent launch uses repository-venv Python `-E -s -B`, inherits the environment unchanged and,
after the fsynced marker, observes only approved membership bits. Eligible SDK work runs in a bounded `env={}`
child with zero ambient credential forwarding and transport dispatch. No outcome grants hash/candidate, cost or
A/C authority.

## Documentation

Use `docs/00-index.md` for active authority/navigation. Historical narratives live under `docs/archive/`.
