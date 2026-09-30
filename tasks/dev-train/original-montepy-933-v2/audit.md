# MontePy development task version 2

Version 1 remains byte-for-byte unchanged. This is a development revision, not an
unchanged original benchmark input or a held-out task.

The public check copies the unchanged source into its existing disposable checkout.
Only there, it preserves arbitrary-precision integer arithmetic with object arrays
in TestFill.test_fill_index_setter and adds five explicit boundary examples. Both
unbounded Hypothesis strategies, all original assertions and both test modules
remain enabled. No production source, submitted patch or prepared source is changed.
Missing/ambiguous public source anchors exit 2 as infrastructure failure.
Pytest reporting changes from -rA to -ra to avoid observed truncation from passing
tests' captured output; test selection and assertions are unchanged.

The issue, base commit, scope limits, image and private/reference bytes are inherited
unchanged; private.yaml changes only task_version to 2. Private evaluation receives
no public-test override. One provider-free calibration ran the inherited private
check on base (FAIL) and production reference (PASS); both public checks passed
all 44 tests. This validates the development package, not an agent solve, sandbox
safety verdict or stability across every Hypothesis seed.

See the separate follow-up in docs/history/2026-09-30-montepy-public-check-v2.md
for execution evidence. Prior version-1 records remain immutable.
