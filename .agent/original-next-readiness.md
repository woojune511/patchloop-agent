# Next original benchmark task

## Frozen selection

Conan `conan-io__conan-19735_interface`, base
`4a65d65f53d2ab37f4ce0e52dc3f25cd832b2934`.
The original public issue concerns Emscripten informational output before its
version line causing compiler detection to return None.

Dataset `nebius/SWE-rebench-leaderboard`, revision
`ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b`, split `2026_03`.
Parquet SHA-256 `18e198ac18b3c25b307c0aa5d9b6e20d338886e186bf7c12addb759ad4165a61`.
Reuse the existing `patchloop-original-input-pilot-v1` hash ranking, taking one
repository after excluding the current candidate ledger and all public packages.
83 of 110 rows satisfy the existing public issue/image/pytest-parser filter and
repository exclusion. No tests, reference patch, hints or outcomes were decoded
before selection; image availability did not affect selection.
This is absence from current inventories, not proof of no historical exposure or
model-training contamination. Do not replace the selected task for convenience.

## Original evaluator materials

After freezing selection, saved the original test patch, reference patch, F2P/P2P
lists and install configuration in external operator artifacts. One FAIL_TO_PASS
and 21 PASS_TO_PASS cases are declared. Original command:
`pytest --no-header -rA --tb=line --color=no -p no:cacheprovider test/unittests/util/detect_test.py`.
Declared Python 3.13; parser parse_log_pytest. Preserve these original semantics;
do not substitute locally invented hidden tests. Pinned parser/grading/test-spec
sources from SWE-rebench/SWE-bench-fork revision
`e4907b7a90eafaa1f0a6428fd04fe31cdd8b4284` are bound as artifacts. This is an
explicit harness pin, not proof of the dataset producer's historical harness.

External root: `C:\pt\preparations\original-next-20261001-v1`.
Hash-chained journal: `runs/run_dev_originalnextselection.jsonl`.
Public selection and private evaluator artifacts remain separated from future
coding-agent input. Raw reference/test bodies were stored as data, not printed.

## Approved image and completed calibration

The user approved the pinned linux/amd64 image pull, which completed:
`swerebench/sweb.eval.x86_64.conan-io_1776_conan-19735_interface@sha256:564734fbebe544567e2e47bac7362ae68a749ffdaa7401dd273903d3552277fa`.
Only the final layer was newly downloaded according to pull output; 1.28 GB was
total compressed layer size, not measured traffic or disk growth. No build or
Docker startup occurred.

[Original calibration](../docs/history/2026-10-01-conan-original-calibration.md)
confirmed exact base/clean source, Python 3.13.13 and pytest 7.4.4. Baseline:
F2P 0/1, P2P 21/21, RESOLVED_NO. Reference: F2P 1/1, P2P 21/21, RESOLVED_FULL.
All required cases were accounted for; no timeout, setup error or extra failure.
Separate containers ran without network or host mounts and were cleaned up.
Journal: `runs/run_dev_conanoriginalcalibration.jsonl` under the external root.

## Package integration complete; optional probes unresolved

[Package admission](../docs/history/2026-10-01-conan-package-admission.md) added
`tasks/dev-train/original-conan-19735`, version 1. Original issue and oracle inputs
are preserved. Full isolated evaluation rejects a behavior-preserving baseline
control and accepts the reference; public tests pass 28/28 on both. Scope and
safety pass. This is operator calibration, not an autonomous solve.

Task hash:
`sha256:7853e01fc73daf9d0c50fd14c252d65468de2283afa43b2a557877f1f1e5b67a`.
Prepared source: `source/prepared-source.json` under the external root.
Journal: `runs/run_dev_conanpackage.jsonl`. Focused tests 43 PASS, Ruff PASS;
mock `run_dev_17ecdace4a5840bb` reaches EVALUATOR_PASS, safety NOT_RUN.

Conan declares dependencies through setup.py and conans/requirements.txt, whereas
the current optional-probe resolver reads PEP 621/735 project metadata. Probe
preparation/execution remains NOT_RUN. Registered public/hidden checks work in the
original Python 3.13 image. Before a live invocation, explicitly choose a scoped
probe preparation solution or disclose probes disabled as a baseline difference.
Do not silently enable unprepared probes or claim complete baseline readiness.
No model/cost allocation is authorized; no paid call occurred.
