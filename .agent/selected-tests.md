# Selected public tests

`run_tests` selects existing public pytest files or node IDs. A task declares
`test_suites` in its public spec; no new CLI flag is needed. The tool is offered
only for declared suites and when its action leaves the protected completion
budget intact. An absent or empty list retains legacy public serialization.

## Registration and selection

`PublicTestSuite` extends `RegisteredCheck` with `runner: pytest` and 1–8
repository-relative public `test_roots`. The trusted registration supplies the
command prefix, environment, working directory, timeout and output limits.
The prefix must forward appended `--` selectors and preserve pytest exit codes.
Only exit zero is registered as success. A wrapper may copy the public workspace
before invoking pytest, as the existing SQLFluff runner does.

```yaml
test_suites:
  - id: public-pytest
    runner: pytest
    test_roots: [tests]
    command: [python, -m, pytest, -q]
```

The model supplies only `suite_id` and 1–8 `targets` (each at most 500 characters),
plus the ordinary action identity and verify-mode `turn_decision`:

```json
{"suite_id":"public-pytest","targets":["tests/test_api.py::TestAPI::test_output"]}
```

Each target must name a tracked public `.py` file below a declared root and the
suite working directory. Directories, flags, hidden paths, traversal, control
characters, duplicate targets, symlinks and Windows reparse points are rejected
before execution. Node suffixes remain literal argv, never shell text. The
registered prefix receives `--` followed by the selected targets translated to
its working directory. The model cannot supply commands or environment values.

The existing task sandbox and resource limits execute the derived check. Selection
does not choose dependencies or acquire images. Local mock execution is test
evidence, not Docker isolation evidence. SQLFluff 1625 shares its required public
check's wrapper: it installs the checked-out example plugin into a temporary path
offline, without resolving dependencies, and preserves assertion detail. Both use
the upstream `not dbt` policy; the required check retains `test/rules`, while this
optional suite accepts selections below `test`. The full tree is not a calibrated
mandatory gate: an existing-reference compatibility control failed it. It carries
no specific CLI node or evaluator hint. Setup failure exits before pytest with code 2.

## Additive test cases

An additive-test task can extend a single existing inline parametrization with
literal cases or direct `pytest.param(...)` calls containing literal positional
values and an optional literal string `id`. New cases cannot use `marks`, other
keywords, unpacking, aliases or computed values. Existing cases, including their
marks and IDs, must remain structurally unchanged and in their original order.
Existing test bodies, imports, fixtures and decorators stay protected. New imports
needed by a new test belong inside that test.

Pre-existing duplicate definitions may remain unchanged in their original order.
An unrelated, uniquely named test or method can still be added. Changing either
duplicate (including its parameter cases), adding another duplicate, or removing
or reordering original definitions remains unsupported.

Case selection uses collected parameter indices, so a descriptive `id` does not
change which addition is compared. The repair comparison runs added cases against
base and candidate source; original-test restoration for isolated evaluation still
applies. Accepting an addition does not establish that its expectation is correct.

## Evidence and recovery

Results preserve suite, targets, action/input identity, current diff, exit code,
output and execution flags. `test_status` is PASS for exit zero, FAIL for exit one,
and ERROR for other exits, timeout, deadline exhaustion or cleanup failure. These
are execution categories: the output still needs interpretation, and exit one
alone does not prove an assertion failure or its cause. Truncation is retained.

Interpret expectations with their public requirement, dialect and invocation
settings. Default CLI behavior and a test that explicitly selects a rule can
exercise different contracts; passing one does not establish the other. An old
output snapshot touching the requested behavior needs compatibility review.
Keep supplied examples distinct from derived boundary cases and unresolved policy
choices; none becomes a mandatory assertion merely because it separates two patches.

Selected tests are optional. They never populate required-check credit, erase a
required check result, or add a submission gate. A subsequent edit makes previous
test results historical. The agent explicitly reruns a selection when needed;
the required-check automatic recheck policy does not schedule optional tests.

The latest three completed selections survive context changes in `recent_tests`,
with bounded stdout/stderr and explicit diff currency. Native result references
avoid duplicate output where that result is already delivered. Failed selections
can become verification observations; a current successful selection can support
an explicitly linked concern resolution. Neither mechanism proves full coverage.

Durable action results replay without test execution for the same
`action_id + input_hash`. A pending action may rerun only against its admitted
diff, using the same execution identity and the existing owned-process/container
cleanup protocol. This is not an exactly-once process guarantee. Normal runtime
and task identity checks still reject incompatible run resumes.

Source: `patchloop/dev/test_selection.py`, `patchloop/dev/tools.py`, and
`patchloop/dev/runner.py`. Provider-free validation and claim boundaries are in
the [implementation record](../docs/history/2026-10-03-selected-public-tests.md).
