# Reproduction

Status: offline validation and immutable audits. R21 candidate-v29 is consumed; R24 is also consumed. Neither may be
rehearsed or executed again.
R22 is prestart-stopped; R23 and R24 are halted. None can retry or resume.

## 1. Validation environment

Use `uv run --offline --frozen` and a unique workspace-local `--basetemp` on Windows. Never reset/clean the dirty tree.
Run state remains outside task repositories. Selected mock runner tests use local synthetic check processes, not
Docker, providers or the real task/evaluator. Historical artifact builders report zero provider,
Docker, evaluator, visible-check, network and cost activity; those claims describe the recorded builds.

```powershell
uv run --offline --frozen ruff check patchloop tests scripts
git diff --check
```

Formatting is checked on the changed files only. The global formatting check currently flags 158 pre-existing files;
do not rewrite frozen runtime/evidence solely to satisfy it. Historical builds are audited by their exact stored bytes,
not regenerated over consumed paths after source integration.

## Lean V27 qualification and activation review - Work Items 80/81

Work Items 80/81 are frozen. Their original builders/tests bind pre-integration source and must not be regenerated
after R24 integration. Recorded commands/results are in `docs/archive/work-item-81-pre-integration-20260901.md`.
Current source preservation is checked by `rapid_v27_package_binding`, without rewriting predecessor bytes.

## R24 preparation and consumed audit - Work Items 82/83

Work Item 82's frozen preparation commands and limits are in
`docs/archive/work-item-82-validation-20260901.md`; do not rerun them. Candidate-v33 was consumed once, so never invoke
it in rehearsal or execute mode, retry its image receipt or resume rows 4-6. Its no-call rehearsal stopped before count
and proved no later bytes/count/budget/provider acceptance. The stored preparation added no external call or task result.

After the writer closes, only `build_rapid_r24_halted_audit.py` and `tests/test_rapid_r24_halted_audit.py` may verify
the stored public audit. They read closed public inputs and add no calls/cost; exact commands/results are archived in
`docs/archive/work-item-83-r24-execution-and-halted-audit-20260901.md`.

## Lean V28 lifecycle binding - Work Item 84

The synthetic/public focused suite passed 14/14. Two qualification-builder calls must preserve content
`sha256:2139df760fdc779ba2bef52dba3d2d7c4b22c389df29ee6e6757978ce44d68c5` and the same 6,498-byte file
`sha256:7ab720ed2eee560ef0d827488a4fb0e361bef44e17676234bade941bb5471b4e`. Related V19-V27/runtime/provider-schema
regressions passed 139/139. The artifact is zero-call/noncreating and neither activates V28 nor measures quality.

## Lean V28 activation review - Work Item 85

The review suite passed 17/17. `build_lean_harness_lifecycle_binding_activation_review.py --check-only` must preserve
the 8,517-byte file
`sha256:12b5e11c2aecd453cfdcf6a909f30b7fdc6cd41a3b4bb20fb87371d34dfc16ed` and content
`sha256:119a40b5c8e80c13e2e2fc2bf5b2f73e2bddfd2c0f452b1d8a3d9a56646980c3`. The review is append-only,
`eligible-not-adopted`, zero-call/cost and noncreating. `--check-only` may verify stored bytes; it grants no adoption.

## Lean V28 treatment adoption - Work Item 86

```powershell
uv run --offline --frozen pytest -o 'addopts=' -q -p no:cacheprovider `
  tests/test_workflow_lifecycle_binding_adoption_decision.py --basetemp .p86decision
uv run --offline --frozen python scripts/build_lean_harness_lifecycle_binding_adoption_decision.py --check-only
```

The suite passes 18/18. The 4,950-byte decision is file/content
`sha256:32979189a7ee8323127950e1f2e48f16d8e85cf363da4c42964a0039ce49dca3`/
`sha256:3c715c15ee46dc87ff1970f079c1cfda891b2df4d131b110dcaa06b9ccb97d75`. It selects V28 only for later
Rapid preparation and creates no candidate, rehearsal, call, cost, default-runtime change or execution authority.

## 2. Consumed R23 audit

R23 candidate-v32 is consumed and halted. Do not invoke its builder, rehearsal or execute mode, retry its image receipt
or resume four unstarted rows. Historical detail is archived.

```powershell
uv run --offline --frozen pytest -o addopts= -q `
  tests/test_rapid_r23_halted_audit.py tests/test_rapid_r22_prestart_stop.py `
  tests/test_documentation_structure.py --basetemp .p23audit1
```

This query-only audit closes its connections and adds no calls or state mutation; exact identity is in `docs/09-evidence.md`.

## 3. Closed R22 prestart attempt

Do not invoke candidate-v30 in rehearsal or execute mode again. Section 2 audits its preserved prestart stop, not an
agent result. Historical commands are in `docs/archive/work-item-79-status-runbook-limits-20260831.md`.

## 4. Immutable prior evidence

R20 candidate-v28 and R21 candidate-v29 are consumed. Never invoke either rehearsal or execute mode. Audit stored bytes
through `docs/09-evidence.md`; V25/V26 reviews stay frozen and runner-continuity remains unexecuted.

After the SQLite writer closes, public diagnosis can be checked read-only without response/reasoning or hidden content:

```powershell
uv run --offline --frozen python scripts/build_rapid_workflow_diagnosis.py `
  --bundle reports/rapid-development/rapid-public-dev-anyio-v5-v25-mechanical-activation-20260830-r21-590bbd602a34.jsonl `
  --state .patchloop/state.sqlite3 `
  --public-task fixtures/task-packages/anyio-interrupt-runner-cleanup-v5/public.yaml `
  --output reports/rapid-development/rapid-workflow-diagnosis-r21-590bbd602a34.json
```

The output must match the stored bytes. A mismatch halts the audit; it cannot retry, repair or reclassify the run.

## 5. Trace viewer

Only after the active writer closes:

```powershell
uv run --offline --frozen patchloop serve --host 127.0.0.1 --port 8000
```

The page shows the public task and attempt timeline; `/raw` renders JSON trees, source ranges, diffs and check output.
LLM/tool/token/cost views are separate. Private evaluator data, checkpoint internals and reasoning text remain hidden.
Reads close. Pre-existing sidecars require a closed writer; never mutate an active trace.
