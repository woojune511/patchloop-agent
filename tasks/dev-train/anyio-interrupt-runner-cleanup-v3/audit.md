# AnyIO interrupt runner cleanup - task version 3

## Public contract correction

Version 3 keeps the issue, source, edit constraints, upstream regression and image
from v2. It replaces only the public lifecycle command and increases its outer
timeout from 90 to 120 seconds for seven child cases (15 seconds each).

The v2 public review reproduced fixture context loss on the submitted patch and a
false PASS: its completion marker preceded task-group exit, and the final test's
xfail marker hid a teardown error. Public evidence is recorded at
`C:\pt\analyses\anyio-v2-fixture-review-20260916-v1\result.md`.
This successor is derived from that public diagnostic and the pinned public AnyIO
fixture contract, not hidden tests, evaluator failure details or a reference patch.

The registered check now requires:

- One setup and completed cleanup, with task identity preserved through ordinary
  pytest outcomes and callback interruption.
- ContextVar value propagation, successful token reset and restoration after
  ordinary execution, skip and callback KeyboardInterrupt.
- Task-group completion after the entire context manager exits, including after
  interruption and the ordinary pass/fail/skip/xfail sequence.
- Expected call outcomes per test, with setup/teardown independently successful.
  Even xfailed or skipped teardown is a failure; the intentional xfail accepts only
  AssertionError. Non-interrupted tests must all produce teardown reports.
- Propagated KeyboardInterrupt, no interrupted-test resumption, once-only test
  finalization, and the existing explicit cancellation control.

The native cancellation control retains v2's plain fixture and outcome/once-only
cleanup requirements; it does not add a context/task preservation requirement to
that separate path. Baseline execution established that cancellation terminates
the persistent worker. Expanding this control would change the repair scope.

Child collection, wrong process exits, timeout and missing cases cannot become
parent success. Concrete public observations name task/context/cleanup failures.
Failure output includes only compact mismatches and phase outcomes so all seven
case verdicts survive the existing gateway's feedback bound.
All cases run with workspace source in the existing offline sandbox. No packages
are installed and no tracked source is modified by the check.

## Version and private boundary

Version 2 is immutable; its task content hash remains
`sha256:eddc56cdb046406027cad1ed30f7788f50327de98e6a40ac387fbfe25b73478d`.
Private metadata changes only task_version from 2 to 3. Hidden files, reference
patch, bad fixtures and environment are copied byte-for-byte without using their
contents to author public checks. Future v3 results must be reported separately
from v2. Runtime, model, tools, planning, probes and context policies are unchanged.

## Validation

Evidence is retained at `C:\pt\analyses\anyio-public-check-v3-20260916-v1`.
It separates synthetic assessor/workflow tests, generated fixture execution,
real offline checks on BASE and the exact prior submitted patch, and the unrelated
mock smoke through isolated fixture evaluation. This change does not implement
an AnyIO repair or claim task acceptance. All results are `official=false`.
