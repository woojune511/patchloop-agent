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

The existing task sandbox and resource limits execute the derived check. This
adds no dependency installation or image acquisition. Local mock execution is
test evidence, not Docker isolation evidence. SQLFluff 1625 registers its existing
public pytest wrapper and environment with the generic `test` root; it carries no
specific CLI node or evaluator hint.

## Evidence and recovery

Results preserve suite, targets, action/input identity, current diff, exit code,
output and execution flags. `test_status` is PASS for exit zero, FAIL for exit one,
and ERROR for other exits, timeout, deadline exhaustion or cleanup failure. These
are execution categories: the output still needs interpretation, and exit one
alone does not prove an assertion failure or its cause. Truncation is retained.

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
