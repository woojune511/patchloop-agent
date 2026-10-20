# SQLFluff 1625: public setup fixed; full-suite compatibility veto

## Problem and public basis

The [first scope comparison](2026-10-03-sqlfluff-public-scope.md) stopped on four
baseline failures. The wider selection was motivated by the existing public CLI
behavior difference between saved A1 and B1, which the required `test/rules` check
did not exercise. A wider check is useful only if its environment runs correctly
and it does not reject a valid repair for stale expectations.

Public `tox.ini` installs `plugins/sqlfluff-plugin-example` and runs pytest with
`-vv`, defaulting to `-m "not dbt"` across `test`. The previous runner omitted
that plugin and used quiet assertion output. Three failures concerned plugin
registration, rules and configuration; the fourth expected text removed from an
abbreviated assertion message. The public source, configuration and failing public
tests motivated the setup change before new execution. No private test membership
or reference implementation selected the public scope or implementation.

## Bounded intervention

The candidate required check selects all of `test` with the upstream non-dbt marker
policy. Its existing temporary public checkout now installs the checked-out example
plugin into a sibling temporary directory using the image's existing pip/build
tools. `--no-index`, `--no-deps` and `--no-build-isolation` prevent fetching or
resolving dependencies; caches and bytecode installation are disabled. The sandbox
also has no network and mounts the original checkout read-only. A small local wheel
is built from public source inside the temporary sandbox; no Docker image is built
or pulled and no host/image packages are installed.

Current source precedes the temporary plugin directory on `PYTHONPATH`. Pytest uses
`-q -o verbosity_assertions=2`, retaining detailed assertions without listing every
passing node. Plugin setup failure exits with code 2 before pytest. The optional
selected-test suite shares this exact runner. Existing 300-second timeout, output,
CPU and memory limits, model prompt, tool surface and private evaluator are unchanged.
The final registration restores the original required `test/rules` selection;
the wider candidate selection was not adopted after the compatibility veto below.

## Frozen controls and results

The external plan was frozen at head
`a3bfb614526f301b4f56eccfe7087fb329ceee8c`, runtime
`sha256:c5db9ef2e78b2f56944bbc8910d57c978346111fbba6cf03c409c61177917792`.
All controls use the exact base `14e1a23a3166b9a645a16de96f694c77a5d4abb7`
and existing image digest
`sha256:b61e33ddbf217f64b2ce29abc39aa9e577e0eacdbcd1b885d78e4ecdfaff9069`.
Base, saved A1 and saved B1 retained their verified heads and patch hashes. The plan
stops on baseline failure or execution uncertainty; there are no automatic retries.

| Public control | Result | Counts | Docker elapsed |
| --- | --- | --- | --- |
| Base | PASS | 2,157 passed, 24 deselected | 84.714 s |
| A1 | FAIL | 2,156 passed, one failed, 24 deselected | 87.973 s |
| B1 | PASS | 2,157 passed, 24 deselected | 88.463 s |

The four setup failures disappeared. A1 fails only the existing
`test/cli/commands_test.py::test__cli__command_directed`: its output omits L031
from the no-join alias fixture. The issue explicitly describes TSQL, while that
CLI test uses the default ANSI configuration; the public L031 documentation also
describes avoiding aliases in FROM clauses. B1 preserves that existing CLI output.
This is evidence of a public behavior difference, not by itself proof of which
complete repair is correct. Neither saved candidate is a known-correct oracle.

Before registration, a separate isolated existing-reference control was added as
a compatibility veto. It runs the already frozen public check without new private
tests or provider calls. Reference source and raw output remain operator-only;
failure would veto mandatory expansion rather than authorize tuning public tests
from the reference output. This additional check strengthens the original
base/A1/B1 adoption criterion; it does not supply a new repair example to an agent.

That reference control failed (exit 1) in 87.788 seconds with an unchanged workspace
and no execution uncertainty. Its source and raw output were not inspected to
choose exceptions or change expectations. A wider gate that passes the base and
B1 but rejects the existing reference cannot be admitted as a required regression
check. Base/A1/B1 alone would have led to an unjustified adoption.

This changes the interpretation of the A1 CLI failure: it is an observed difference
from an old public expectation, not sufficient evidence of an unacceptable repair.
The broader suite's compatibility failure does not establish that A1 is correct,
or identify which reference behavior conflicts with it. Prior private acceptance
failures remain valid historical outcomes. No public test expectations or
case-specific exclusions were introduced from reference feedback.

The final change retains the public environment correction and the original required
scope. Optional selections can now run public plugin/introspection tests that lacked
their prerequisites. A separate base/reference comparison calibrates that exact
final registration; the wider candidate's checks cannot certify a different command.

Both final controls passed: base in 30.777 seconds and reference in 30.061 seconds,
with unchanged workspaces and no timeout, truncation, deadline or cleanup uncertainty.
The checked-in required command exactly matches this last frozen comparison.

## Evidence

Public comparison root:
`C:/pt/analyses/sqlfluff-public-scope-20261003-v2`.
It preserves `public_runner.py`, `run.py`, `plan.json`, `result.json`, raw receipts
and the append-only hash-chained `run_dev_sqlfluffpublicsetup` journal. Result hash:
`sha256:dcd15d5693c5c9d01cfdb82dfcb5b7af58345bf299a64dcecbccf5a4ef6c7a1b`.
The existing failed v1 evidence remains unchanged.

Reference compatibility root:
`C:/pt/analyses/sqlfluff-scope-reference-20261003-v1`, with a separate frozen plan,
driver, operator-only receipt and `run_dev_sqlfluffscopereference` journal.
Its workspace is separate from every solver workspace.

Final registration control root:
`C:/pt/analyses/sqlfluff-registered-setup-20261003-v1`, with its frozen command,
separate `run_dev_sqlfluffregisteredsetup` journal and blinded summaries. It reuses
the separate base/reference workspaces without projecting reference content.
Final control summary hash:
`sha256:97e9ab449929a51998ae9f889e4f60fa6fded39759dc9001fa998f17bc0313c5`.
Final public spec hash:
`sha256:1c6d4d6cd298fc9514f4c08962a6fb28f91cdb8b8c08c14ef68ea15094bcc934`.

All three public comparison workspaces were unchanged after execution; no timeout,
output truncation, deadline exhaustion or cleanup failure occurred. No agent was
run on the changed task. Paid provider calls and cost were zero. No SQLFluff private
acceptance or safety evaluation was rerun; prior acceptance failures are unchanged.

## Local validation

Focused public-runner, selected-test and package checks: 41 passed, one real-Docker
opt-in skipped in 34.38 seconds. New local checks exercise temporary dependency
visibility, current-source precedence, hidden-directory exclusion, workspace
preservation, pytest failure propagation and stopping/cleanup after installer failure.
They use a local installer double; the real installation evidence is the Docker
comparison above. Related diagnostic, continuation and Lite adapter checks:
52 passed in 14.79 seconds. Reports are `focused.xml` and `integration.xml`.

Ruff, task validation and diff whitespace checks passed. Mock smoke
`run_dev_e9333bd9c8ad412c` reached isolated acceptance PASS with safety NOT_RUN;
its four local mock model calls are not provider requests. The full repository
suite was not repeated for a task-local launcher/registration change with no runtime
code changes. Final documentation layout/link and suite-registration checks:
six passed in 0.74 seconds (`docs.xml`).

## Decision and remaining question

Adopt the isolated public environment correction: the original required scope
passes both final controls. Do not expand the mandatory scope, hardcode the
observed CLI node, change the agent prompt, or launch another paid comparison.
This work separates two problems: missing test prerequisites were correctable;
turning broader old public expectations into mandatory repair constraints was not
justified. There is no demonstrated improvement in agent repair success.

The next unresolved question is which public behavior must remain stable under
the issue's intended change. Resolve that from public requirements and source
before proposing a revised regression contract. Do not use the failed reference's
raw output to design test exclusions or infer a repair implementation.
