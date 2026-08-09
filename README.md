# PatchLoop

PatchLoop is a recoverable single coding agent and evaluation harness for scope-compliant software repair.
Agent, hidden evaluator, recovery state and cross-run memory evidence remain separate.

## Current direction

The 96-run A/B/C/D campaign is deferred. The checked-in readiness panel is:

- A: no cross-run memory
- C: the exact three-entry structured bundle
- Moto and Babel, one A/C pair each
- identical model, prompt, tools, context policy and 3M/3600 resource ceiling

The suite, delivery and R2 cost/completion source are offline-qualified. D-136 completed one bounded official
public pricing capture and is consumed. D-137 now offline-qualifies only the source and future topology for
separate Docker and SDK no-call preflights; neither phase has been activated.

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
- D-136 gate→receipt→attempt→ACTION_STARTED+terminal completed in exact Git order. The terminal preserves one
  unauthenticated public GET, HTTP 200, zero redirects and 3,735 replay bytes; provider/evaluator/agent calls
  and cost were 0. The phase is consumed and cannot be reused.
- D-137 source commit `adcdeadbbb561f82548044d8c9a18d976b584132`, tree
  `a1f649cd45007d032ae97d76f97b8a0df9180432`, is the exact four-add sole child of the D-136 success commit.
  Gate `d137_7aee6dbd665e667f5fe8697b47b9046dfcf188b1a8529880215e15a676261acc` is source-qualified only;
  its exact gate+10-doc evidence commit is the direct child reported by the post-commit validator. Focused tests
  passed 62/62 and the selected current-compatible set passed 112/112 with focused included, so counts are not
  additive.
- No D-137 receipt, attempt, marker or terminal exists. D-137 preparation observed no real Docker, SDK,
  credential/environment value, endpoint or network state and grants no current readiness or execution authority.

Machine-readable evidence is indexed in `docs/09-evidence.md`.

## Offline quickstart

```powershell
uv sync --extra dev
uv run pytest -q tests/test_d137_d136_no_call_preflight_successor_offline.py
uv run python scripts/build_d137_d136_no_call_preflight_successor_offline.py --validate-gate-postcommit
uv run pytest -q tests/test_documentation_structure.py
git diff --check
```

These paths validate sealed local evidence only. There is intentionally no supported live A/C command.

## CLI surface

Use `uv run patchloop --help` to discover the CLI.

CLI availability does not imply authority. A fresh exact D-137 activation must quote the gate tuple, source
commit/tree and exact gate+docs evidence-commit tuple. Docker must complete through a committed READY
terminal before a separate SDK attempt can be created. Both phases are one-use and marker-first; hash/candidate,
cost and A/C authority remain closed.

## Documentation

Use `docs/00-index.md` for active authority/navigation. Historical narratives live under `docs/archive/`.
