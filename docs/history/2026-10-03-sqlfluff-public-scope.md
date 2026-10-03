# SQLFluff 1625: broader public scope blocked by baseline setup

## Problem and decision

The [seeded selected-test diagnostic](2026-10-03-selected-tests-results.md)
left A1's public CLI regression unrepaired: both agents ran the mandatory
`test/rules` check and finished without using the optional
[selected-test tool](2026-10-03-selected-public-tests.md). A required check that
omits an existing caller regression is a concrete coverage gap. This investigation
asked whether the upstream non-dbt public suite could replace that narrow scope
within the existing environment and 300-second limit.

Do not adopt the scope expansion yet. The unmodified base completed within the
limit but failed four public tests. A1 and B1 were not executed after this baseline
failure, as required by the frozen stop condition. No task, runner, prompt, model,
image or dependency was changed. The current narrow check remains incomplete;
this result explains why simply replacing its directory argument is insufficient.

## Why the original scope was narrow

The immutable preparation plan at
`C:/pt/analyses/lite-dev20-calibration-20261002-v1/public-plan.json` selected
`test/rules` because the issue concerns L031 and table aliases. It does not cite
a failed full-suite run or a time limit as the reason for that selection.
The [original calibration](2026-10-02-swebench-lite-dev20-calibration.md) subsequently
added the public upstream `not dbt` marker condition after an optional dbt failure;
the resulting narrow suite passed 500 tests and deselected one on its controls.

At the exact public base, `tox.ini` runs pytest with `-vv -rs` and defaults to
`-m "not dbt"`; its configured test path is `test`. Its test environment also
installs `plugins/sqlfluff-plugin-example`. The public CI Python jobs run these
tox environments. These public files supplied the broader scope independently
of private evaluation membership. This comparison preserved the existing runner
and installed image; it did not reproduce the complete upstream tox environment.

## Frozen comparison and observed result

Execution head: `51f4d85a7f9bdd9db6860e2d28d71b5217630530`.
Public base: `14e1a23a3166b9a645a16de96f694c77a5d4abb7`.
Existing image digest:
`sha256:b61e33ddbf217f64b2ce29abc39aa9e577e0eacdbcd1b885d78e4ecdfaff9069`.

The plan changed only the required check's `test/rules` argument to `test`, keeping
`-m "not dbt"`, the temporary public checkout wrapper, image, resource limits and
300-second check timeout. Base, saved A1 and saved B1 were selected before execution.
Their checkout heads and exact patch hashes were verified. B1 was a public
preservation control, not a correct reference patch. Adoption required base PASS,
A1 regression detection, B1 preservation and no timeout, truncation or cleanup
uncertainty. Baseline failure stopped the comparison without retries.

| Control | Result | Counts | Elapsed |
| --- | --- | --- | --- |
| Base | FAIL | 2,153 passed, 4 failed, 24 deselected | 87.119 s including Docker; pytest 69.18 s |
| A1 | NOT_RUN | Baseline stop | n/a |
| B1 | NOT_RUN | Baseline stop | n/a |

Three failures are in `test/core/plugin_test.py`: the example plugin, its rule and
its default configuration are absent from the loaded plugin registry. Public
`plugins/sqlfluff-plugin-example/setup.py` supplies the setuptools entry point,
and `src/sqlfluff/core/plugin/host.py` loads those entry points. The observation
supports a missing public test-environment prerequisite, not an L031 repair defect.

The fourth failure is
`test/test_testing.py::test_rules__test_helper_has_variable_introspection`.
It expects `select` in an intentional assertion failure, but pytest's abbreviated
message removes the common SQL prefix and retains only the changed lines.
The registered wrapper uses `-q`, unlike upstream's `-vv`. Restoring upstream
verbosity is a concrete candidate correction, but was not executed or proven here.

No output was truncated; no timeout, deadline exhaustion or cleanup failure occurred.
The base workspace remained unchanged. No tests were excluded to manufacture a
passing baseline. Private acceptance was not rerun; the earlier A1/B1 acceptance
failures remain historical results, not verdicts from this comparison.

## Evidence and validation

Evidence root: `C:/pt/analyses/sqlfluff-public-scope-20261003-v1`.
`run.py`, `plan.json`, `result.json`, content-addressed raw check output and
`runs/run_dev_sqlfluffpublicscope.jsonl` preserve the driver, frozen conditions,
source hashes, runtime hash and result in append-only hash-chained evidence.
Result hash:
`sha256:1462572a8514a58592b18a81f78370423b32aae6dace86ff3c3df4701a36e17b`.

Focused selected-test, public-runner, package and documentation checks:
44 passed, one Docker opt-in skipped in 27.18 seconds (`focused.xml`). Ruff and
task validation passed. Mock smoke `run_dev_3dbdabeeb52f444b` reached isolated
acceptance PASS with safety NOT_RUN. Documentation close-out verifies layout,
links and diff whitespace. The full repository suite was not repeated for this
documentation-only change. Paid provider calls and cost were zero; the four mock
model calls are local mock execution, not provider requests. The comparison made
no new private evaluation; smoke exercised its separate fixture evaluator.

## Remaining question

Can the public test environment supply the upstream example-plugin prerequisite
and compatible assertion verbosity without changing task source or private
evaluation? Establish that on the base before repeating the broader base/A1/B1
comparison. No dependency installation, image build, compatibility correction or
new paid allocation was executed here. This is evidence about public-check setup
and coverage; it establishes no improvement in agent repair correctness.
