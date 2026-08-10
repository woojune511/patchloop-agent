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
consumed. D-137 completed bounded Docker READY and SDK missing-key BLOCKED no-call phases; D-138 through D-140
each ended missing-key BLOCKED and are consumed. D-141 now qualifies only a fresh SDK successor source and
future one-use topology.

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
- D-121 is deferred; D-124/D-131 are historical, D-129 is terminal blocked, and D-132 through D-135 preserve
  one consumed incident without reconstruction. D-136 later preserved one successful public GET and is consumed.
- D-137 through D-139 preserve consumed Docker/SDK no-call transitions. Exact tuples and zero-activity limits are
  indexed in `docs/09-evidence.md`; none is reusable authority.
- D-140 committed receipt, attempt and ACTION_STARTED+BLOCKED transition
  `4b8eaf4d815f2ad5e2205bace0e8d9a97ad043f2`. The three presence bits were false/false/false after exactly
  three membership checks; value/`.env`, child, SDK import/probe, transport/network and provider activity were 0.
  D-140 is consumed and cannot be retried.
- D-141 source commit `0ffe586760659542d7ecf7c94698a2f1e109e6b0`, tree
  `41d14e4d9778e52834e4e6636f1bcd35ce148876`, is the exact four-add sole child of D-140. Gate
  `d141_51e825a474cc957f6fa20dea9ec5332c9b0defd7569dfe6f063f57f195636aab` is source-qualified only;
  fully injected/mocked focused tests passed 170/170 and are non-additive. D-141 preparation performed zero
  membership/value/`.env`/SDK/child/network/Docker observation or action.

Machine-readable evidence is indexed in `docs/09-evidence.md`.

## Offline quickstart

```powershell
uv sync --offline --frozen --extra dev
$d141Basetemp = Join-Path 'C:\Users\geonj\AppData\Local\Temp' ('patchloop-d141-' + [guid]::NewGuid())
& .\.venv\Scripts\python.exe -E -s -B -m pytest -q `
  -p no:cacheprovider --basetemp $d141Basetemp tests/test_d141_d140_sdk_blocked_successor_offline.py
& .\.venv\Scripts\python.exe -E -s -B scripts/build_d141_d140_sdk_blocked_successor_offline.py `
  --validate-gate-postcommit
$docsBasetemp = Join-Path 'C:\Users\geonj\AppData\Local\Temp' ('patchloop-docs-' + [guid]::NewGuid())
& .\.venv\Scripts\python.exe -E -s -B -m pytest -q -p no:cacheprovider `
  --basetemp $docsBasetemp tests/test_documentation_structure.py
git diff --check
```

These paths validate sealed local evidence only. There is intentionally no supported live A/C command.

## CLI surface

Use `uv run --offline --frozen patchloop --help` to discover the CLI.

CLI availability does not imply authority. A fresh exact D-141 activation must quote gate, source and evidence
commit tuples. Its parent launch uses repository-venv Python `-E -s -B`, inherits the environment unchanged and,
after the fsynced marker, observes only approved membership bits. Eligible SDK work runs in a bounded `env={}`
child with a fixed nonsecret placeholder, zero ambient credential forwarding and zero transport dispatch. The
child audit hook starts only after CPython/site startup, so pre-bootstrap network absence is not claimed.
Credential provisioning is a separate action authorized by neither source preparation nor activation; no
credential value belongs in an approval message or chat. No outcome grants hash/candidate, cost or A/C authority.

## Documentation

Use `docs/00-index.md` for active authority/navigation. Historical narratives live under `docs/archive/`.
