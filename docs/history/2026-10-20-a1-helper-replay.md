# A1's added helper test passes before and after the edit

Date: 2026-10-20. Two local operator experiments, official=false and
claim-ineligible. Follow-up to the [A1/B1 diagnosis](2026-10-20-a1b1-diagnosis.md)
after the user started Docker and authorized the prepared local comparison.
The prior NOT_RUN record and the closed paid comparison remain unchanged.

## Question and controlled difference

A1 asserted that its added test exercised the repair. The preceding source audit
instead predicted that the test already passed through the existing namespace
resolver. Checking this matters because a test that passes independently of an
edit cannot demonstrate that the reported regression was repaired.

The two programs frozen under `C:/pt/a1b1-diagnosis30/` were executed unchanged.
They run the exact extracted AST of A1's `test_namespace_package_without_init`
method, with its assertions and temporary directory setup, in separate isolated
Python 3.9.25 processes. One binds the baseline `_spec_from_modpath` function;
the other binds the submitted function. All other source, dependencies, sandbox
profile and test AST are identical. Each program records resolver calls, returned
spec types and whether the changed `PKG_DIRECTORY` body is entered.

This is an isolated method comparison, not a rerun of the complete unittest class,
its shared fixtures, the public suite, or the original Pylint caller. The extracted
functions are compiled into the module namespace without editing stored sources.
There are no model requests, evaluator executions or network-enabled containers.

## Measured result

| Condition | Added test body | Resolver calls | Observed type | Entered changed package body | Duration |
| --- | --- | --- | --- | --- | --- |
| Baseline function | PASS | 2 | `PY_NAMESPACE` | No | 6.560s |
| Submitted function | PASS | 2 | `PY_NAMESPACE` | No | 5.709s |

Both processes exited 0, output was complete, and owned-container cleanup was
confirmed. The source snapshots have the same hash:
`sha256:59656634654e84a4e08b43db1a73c3ea4413c5669067c205ecc8f113d47f193a`.
The baseline/submitted function hashes differ while the test AST hashes match.
The image and dependency profile match the original prepared Python 3.9 sandbox.

The prior static prediction is now observed in this environment: the helper test
does not distinguish the edit and does not enter its changed branch. Its PASS
cannot establish a repair effect. The separately saved original-caller assessment
already failed on A1's submitted source; that result was not rerun or replaced.
This does not show that the patch has no effect on every other possible input.

## Decision and limits

The evidence strengthens the A1 diagnosis: the model selected a different route,
then interpreted a passing, non-discriminating helper test as confirmation of the
reported repair. This is not adequately explained by source loss alone; the prior
audit found the relevant branch guard in the actual input before the source edit.

Keep the current runtime and budgets. The remaining question is whether the already
implemented B reproduction mechanism makes the model execute the original caller
under its actual input/setup and compare fixed observations before and after an
edit. B1 never took a tool action, so this experiment does not measure that uptake
or justify another prompt, gate, or paid allocation. B1 billing remains UNKNOWN.

Evidence: `C:/pt/a1-helper31/scope.json`, both `*-receipt.json` files, `result.json`
and the hash-chained `run_dev_a1helper31` journal. Result SHA-256:
`4d9941b6b39fc748f58283ef18e4391eaf11de31cd45990664f7f62a3f3ef2ba`.
Twenty-three protected prior evidence files retained their hashes. No historical
grade, previous diagnosis record, submitted patch or source workspace was changed.

Executed: two bounded local helper experiments. Not executed: paid calls, fresh
agent solves, caller/native reevaluation or full-suite reruns. Transition rules,
two references, context/execution/cost limits and the uncertainty stop remain intact.
Documentation checks: 5 passed. Ruff and `git diff --check` passed. Runtime code
was unchanged; the prior isolated mock validation remains separate from these
real Docker helper executions.
