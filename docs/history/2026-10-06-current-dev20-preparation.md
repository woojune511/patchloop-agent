# Current dev20 capability and parallel-run preparation

## Problem and decision

The last dev20 run resolved 9/20 versus the historical 10/20. The
[saved-evidence review](2026-10-06-dev20-decline-review.md) found that it preserved
historical task restrictions and did not measure all current verification
capabilities. The user requested ordinary probes with dependencies, selected tests,
test additions, no automatic probe replay, and concurrent execution of distinct
tasks. When three task environments were incompatible, the user explicitly chose
environment support before measurement instead of relying only on selected tests.

This work removes demonstrated capability blockers. It does not claim that enabling
these features will improve repair correctness, and does not attribute the previous
9/20 result to the restrictions alone.

## Implementation

- Separate `tasks/dev-train/current-dev20/1..20` packages preserve the original
  issues, repository commits, private checks, reference bytes and evaluator images.
  Existing pytest roots become selectable. Tests may gain new top-level test
  functions or literal parameter cases; existing tests, fixtures and helpers stay
  structurally unchanged. Additions still consume the four-edit task allowance.
  SQLFluff-1625 uses its already corrected current public launcher, including local
  example-plugin setup; the preceding portfolio run used the historical frozen
  launcher. This is an explicit configuration difference in the current measurement.
- Public checks see the complete submission. Isolated hidden grading restores the
  original test files temporarily; native grading uses a separately hashed
  source-only patch. Both retain the original full submitted artifact.
- Public setup.py/setup.cfg metadata is read statically without running builds.
  Interpreter requirements and wheel markers/ABI are bound to the selected clean
  public probe image. No evaluator files or image contents supply dependencies.
- The batch driver runs two independent task processes with separate workspaces,
  journals, clients and budgets. Twenty nontransferable USD 1.20 allocations stay
  within a USD 24 invocation allocation. A shared admission stop prevents later
  count/generation calls after uncertainty; already admitted calls settle.
  No retries, resumed rows or automatic follow-ups are introduced.

## Observed environment failures and repairs

The initial Python 3.12 preparation exposed real compatibility failures:
Marshmallow imported removed `distutils`; two Astroid snapshots required
`wrapt<1.14`, which has no matching CPython 3.12 wheel; PyVista could not load
`libX11.so.6`. Failed artifacts remain in `C:/pt/cd20p06` and
`C:/pt/cd20p06b/dependencies`.

Marshmallow and those Astroid snapshots now use the pre-existing pinned public
Python 3.10 image. PyVista uses a new clean Python 3.12 image with X11/OpenGL
libraries, built under the user's explicit environment-expansion request. The
image's receipt and base-layer verification are in `C:/pt/cd20graphics06`.
No task source, hidden test, reference patch or evaluator image was included.
Runtime/preflight still never acquires images automatically.

Public canaries demonstrated Marshmallow integer deserialization, Astroid parsing,
and PyVista sphere creation. The complete capability check then passed **20/20
imports and 20/20 selected public test executions**. This establishes availability
for those checks, not exhaustive dependency compatibility or task success.

## Validation and evidence

- Final focused validation: 38 passed in 42.054 seconds. The initial full run
  recorded 4,175 passed, 18 skipped, one failure and 29 setup errors. All 30
  unsuccessful cases referenced the removed fixed image export in two diagnostic
  drivers. Both now resolve the selected profile; their complete file reruns
  passed 23 and 11 tests. The new summary test also passed. Latest outcomes are
  **4,206 passed, 18 skipped, no unresolved failures**, combining the original
  full run with these explicit reruns, not claiming a fresh all-green full run.
  `full-pass.xml` retains the original failed report; `full-reconciled.xml` and
  `validation-reconciliation.json` bind each contributing report and the recipe.
- Ruff and source/doc whitespace checks passed; copied reference patches retain
  their original whitespace and exact bytes. Mock smoke reached `EVALUATOR_PASS`.
  Mock Docker safety remains `NOT_RUN`.
- Real spawned-process tests exercised overlapping tasks, aggregate allocation
  rejection, peer failure, prevention of the next call, and retained settled cost.
- Evaluator tests verify that added test bytes reach public checks, original tests
  reach hidden grading, and the full submitted patch remains intact.
- `C:/pt/cd20p06b/capabilities.json` binds all twenty capability receipts to runtime,
  task, source and dependency identities. External journals remain append-only
  `dev-run-v1`. Historical runs and closed reports are unchanged.

## Measurement boundary

Provider calls for this preparation: **0**. New solve outcomes: **NOT_RUN**.
The [current panel contract](../../.agent/current-dev20.md) specifies mini xhigh,
one fresh solve per original dev20 task, two workers, the unchanged task budgets,
and automatic probe replay off. Exact live authorization remains separate from
provider-free preparation. Compare original acceptance, regressions, settled cost
and wall time with the closed 9/20 and 10/20 panels. One development-exposed panel
does not isolate individual feature effects or support general accuracy claims.
