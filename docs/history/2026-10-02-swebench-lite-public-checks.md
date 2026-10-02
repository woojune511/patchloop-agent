# SWE-bench Lite public-check compatibility follow-up

## Problem and decision

The three-task mini pilot was blocked before any model call because its newly
registered full pydicom suite failed on untouched source. The public check would
have required repairs unrelated to the user's task. This follows the immutable
[initial preflight](2026-10-02-swebench-lite-preflight.md).

Restore useful public verification by removing the unnecessary whole-repository
requirement for pydicom. Its required public check now runs both complete existing
test_json.py and test_sequence.py modules, selected from the public issue's JSON
conversion and SQ-element scope. This narrows public regression coverage; it does
not make the whole repository suite compatible. It changes no assertion, outcome,
private test patch, F2P/P2P list or original grading rule. No individual failing
case is skipped or reclassified. Astroid and marshmallow retain their full public
suites. Public checks use a writable temporary HOME inside the existing sandbox.

## Diagnosis and alternatives

The leading explanation was pytest 8 no longer invoking old class setup/teardown.
Public source contains 60 such classes. A provider-free diagnostic restored those
hooks in memory and reran all public tests. It produced 1,607 passes, 326 skips,
144 failures and 27 errors. Failures included unavailable external DICOM fixtures,
read-only /root/.pydicom and seven uses of the removed pytest.warns(None) behavior.
Pytest's [removal notes](https://docs.pytest.org/en/8.1.x/deprecations.html)
explain the legacy lifecycle and warning API incompatibilities.

This weakened the hypothesis that a small lifecycle bridge alone could restore
the whole suite. A complete environment restoration would need compatible test
dependencies and public fixture provisioning. Neither belongs in an agent's issue
repair. The temporary shim was therefore not adopted; no new image was built or
pulled and no dependency was installed into the approved images.

The alternative chosen is a task-scoped public regression check, grounded in the
original public issue: it names from_json, BulkDataURI, SQ elements and jsonrep.py.
The base repository supplies JSON conversion and Sequence unit modules. No hidden
target names or reference-patch locations were used to select these modules.
Passing them is public regression evidence, not proof that the issue is fixed.

## Calibration

The registered adapter was executed on separate base/reference workspaces for
all three frozen tasks. All six public checks passed. The original private adapter
reported unresolved for each base and resolved for each reference with all
required cases present, agreeing with the earlier native upstream controls.

| Task | Public result on each control | Private base / reference |
| --- | --- | --- |
| astroid-1978 | 1,425 passed, 84 skipped, 14 xfailed | unresolved / resolved |
| pydicom-1256 | 31 passed | unresolved / resolved |
| marshmallow-1359 | 911 passed | unresolved / resolved |

These are known-answer calibration controls, not agent solves. The final submitted
agent patches still require native evaluation as specified in the
[pilot protocol](../../.agent/swebench-lite-pilot.md).

A separate public negative control changed Sequence.validate_dataset to return
None instead of the supplied Dataset. The 31-test public check rejected it with
9 failures and 22 passes. This confirms regression detection for that corruption;
it does not establish complete coverage. The original source remained unchanged.

Evidence is outside the repository in append-only journals and referenced artifacts:

- C:/pt/analyses/swebench-lite-public-compatibility-20261002-v1: lifecycle diagnostic,
  preserved temporary shim source in the recorded command, complete failure output.
- C:/pt/analyses/swebench-lite-registered-controls-20261002-v4: six registered controls,
  three external draft packages, workspace and package hashes.

## Validation and remaining execution

A subprocess regression runs multiple public test paths, verifies current source
imports, excludes private files, permits temporary HOME writes and leaves the source
unchanged. An intentionally broken public module still fails the check. Focused
selection, transport, private error classification and launcher tests passed (14).
Ruff and documentation checks passed. Mock run run_dev_62eca89fc6544d30 reached
EVALUATOR_PASS with safety NOT_RUN under
C:/pt/swebench-lite-public-smoke-20261002-v1.

The four-worker full suite completed in 862.78 seconds: 3,968 passed, 16 skipped,
one failed while creating a 263-character temporary artifact path on Windows.
The parent existed; no public-check assertion caused the failure. The same failure
was reproduced with a long basetemp. Rerunning the complete affected file,
test_dev_check_feedback_v32.py, under C:/pt/lpc-1002 passed all 46 tests. The initial
full-suite failure remains recorded rather than being relabeled as a clean pass.
XML outputs are in the compatibility evidence root. This change does not repair
general Windows long-path support. Remote CI was not run.

Task admission and paid execution have not occurred. The existing exact three-task
USD 3.60 conditional authorization is retained; usage is USD 0. No 300-task run is
authorized. The public-check blocker is cleared; full-suite compatibility and
benchmark performance are not claimed.
