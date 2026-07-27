# Task audit: fusesoc-retained-parse-error-diagnostics

- Dataset role: `core-cross-repo`; admitted as the fourth task in this lane
- Source: SWE-rebench leaderboard instance
  `olofk__fusesoc-776_interface`, split `2026_03`
- Frozen benchmark revision:
  `ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b`
- Frozen benchmark row: `69`
- Upstream issue: <https://github.com/olofk/fusesoc/issues/761>
- Upstream resolution: <https://github.com/olofk/fusesoc/pull/776>
- Base and environment commit:
  `d2e6e720222f57cb66d6c303a326d336c582aade`
- PR head: `d219148c396a24f8cbc5ccab98eaee50e8ec0bac`
- Squash merge commit:
  `49eb72f296e1ccfb29ede2feab6cacdac06d3d54`
- Created: `2026-05-07T12:05:49Z`
- Merged: `2026-05-10T21:15:52Z`
- License: BSD-2-Clause
- Retrieved: `2026-07-27`
- Task reference patch SHA-256:
  `sha256:c25ac0f174a7b0b9d9d5d9b5d0a179856103351652a64e4da8483e8f5ed83658`
- Evaluator image:
  `swerebench/sweb.eval.x86_64.olofk_1776_fusesoc-776_interface@sha256:1e971791d4ce192eae296747d46dff477cb2ce2c47e08b2ed9d0108ee5a85ad9`
- Workflow: real-repository issue fix
- Failure pattern: parse diagnostics are discarded after warning
- Expected source changes: `fusesoc/coremanager.py`,
  `fusesoc/fusesoc.py`, and `fusesoc/main.py`
- Benchmark declaration: one F2P and fourteen P2P tests
- Contamination risk: high. The issue, pull request, benchmark row, accepted
  patch, and interface declaration are public.

The task reference is the exact three-production-file patch frozen in the
benchmark row. It adds 29 lines, removes one line, changes three files, and has
74 serialized unified-patch lines. Applying it to the frozen base produces the
same three source blobs as the upstream squash merge. The benchmark test patch
adds one 40-line regression test and is not included in the task reference.
The fix persists in FuseSoC 2.4.6 and current upstream main, and no revert was
found during screening.

## Visible regression selection

The benchmark declares fifteen nodes for `tests/test_coremanager.py`: one F2P
node from its test patch and fourteen base-resident P2P nodes. The F2P test
patch is evaluator-only and is not copied into the submitted workspace.

The official PatchLoop boundary is both network-disabled and source-read-only.
Within that boundary, `tests/test_coremanager.py::test_export` attempts to
download a GitHub tarball and
`tests/test_coremanager.py::test_lockfile_no_file_create` writes a generated
lockfile below `/workspace/tests`. Both are therefore explicitly deselected.
`test_deptree` also launches a `python3` child process, so the registered check
pins `PATH` to the image's testbed environment instead of allowing the
image-level `/opt/conda/bin/python3` to omit PyYAML. With those environment
constraints, the complete remaining base-resident selection passes 12 nodes
on the exact production patch in the official network-none, read-only Docker
boundary.

## Independent acceptance design

The private oracle does not copy the upstream test or require a new internal
helper. It binds all three imported modules to `/workspace`, then exercises:

- multiple malformed files with different validation failures;
- discovery continuing to a valid core after malformed files;
- accumulation across scans and independence between manager instances;
- exact tuple shape and string payloads;
- live forwarding through the `Fusesoc` property;
- missing-core CLI output preserving the original diagnostic and including
  every retained file path and parser message;
- unchanged missing-core output when no parse failures exist; and
- unchanged handling for non-parse `ImportError` failures.

The known-bad corpus contains eight semantic partial fixes: manager-only
retention, wrapper-only exposure, missing CLI propagation, retaining only the
last error, class-shared state, stopping after a parse failure, classifying
provider import failures as parse failures, and rendering only the first error
at the CLI boundary. A no-op and a forbidden test edit cover base rejection
and policy enforcement.

Difficulty audit:

| Dimension | Score | Reason |
| --- | ---: | --- |
| Localization | 1 | The issue identifies discovery, but the diagnostic must cross manager, wrapper, and CLI boundaries. |
| Reasoning depth | 2 | The fix must preserve best-effort discovery while retaining typed failure state and later composing it with dependency errors. |
| Implementation breadth | 2 | State collection, public forwarding, and terminal reporting span three production modules. |
| Verification breadth | 2 | Multiple failures, valid continuation, instance isolation, non-parse behavior, and CLI formatting interact. |
| Total | 7 | Hard under `dataset-manifest-v1`. |

## Admission evidence

The official matrix ran from clean harness staging commit
`da3105d30f0c7eb6fec65650200aedac7eb12b13`. All 13 cases used the exact
digest-addressed evaluator image with Docker networking disabled and read-only
root and submitted filesystems. The image supplied Python 3.13.13 and
pytest 9.0.3, and its unconfigured `User` meant Docker used the image-default
root user.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| exact production reference | `run_1930d4d388214a39`, `run_ecc6b25d878941dd`, `run_41a5e6e0c3a9460f` | full success ×3 | 3/3 success, `official=true` |
| base/no-op | `run_27a35b3567fc4b75` | visible pass, hidden fail | rejected at hidden acceptance |
| manager-only retention | `run_fd337d9d5db34b19` | wrapper/CLI propagation fail | rejected at hidden acceptance |
| wrapper-only exposure | `run_058153b57a3f4135` | manager retention fail | rejected at hidden acceptance |
| missing CLI propagation | `run_7e8f97cfc9e44546` | missing-core diagnostic fail | rejected at hidden acceptance |
| last error only | `run_1b70b4fca4ad411c` | multi-error accumulation fail | rejected at hidden acceptance |
| class-shared errors | `run_a55d1e200c5e4163` | manager isolation fail | rejected at hidden acceptance |
| hard stop on parse error | `run_6df53dc5f3fe4326` | valid-core continuation fail | rejected at hidden acceptance |
| import errors misclassified | `run_b5bf8f2a76794047` | non-parse failure handling fail | rejected at hidden acceptance |
| CLI first error only | `run_e150bdb76e554d24` | complete diagnostic fail | rejected at hidden acceptance |
| forbidden test edit | `run_03d995290fee481d` | hidden, scope and tampering fail | rejected at all three boundaries |

The three reference runs each collected 14 visible base tests, deselected
`test_export` and `test_lockfile_no_file_create` for the documented environment
constraints, and passed the remaining 12. The independent hidden oracle
collected and passed all ten cases on the reference. Base/no-op and all eight
semantic partials remained otherwise policy-compliant, so their hidden-only
rejections isolate acceptance behavior from scope policy.

The admission binds public task hash
`sha256:2dd38ab34abc7ab53c0487c2d5b19dbda5b303fe2d04bf04474cc5bafef6ba31`,
private task hash
`sha256:e5db4a13d05518abd3a2be50c99ed8aa9536168896c27f52a4947c6773e7b66d`,
the reference hash recorded above and every run's manifest, result and
provenance artifact. The immutable run index is
[the FuseSoC Docker admission report](../../../reports/docker-gate/research-fusesoc-retained-parse-error-diagnostics.json),
with SHA-256
`cef87dda16402d874b28264fcbed5bba2acf07736800c5fd297d812112081918`.
