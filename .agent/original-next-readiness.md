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

## Environment blocker and concrete next action

Docker image is absent locally. Registry manifest inspection succeeded without
pulling layers. Immutable linux/amd64 image:
`swerebench/sweb.eval.x86_64.conan-io_1776_conan-19735_interface@sha256:564734fbebe544567e2e47bac7362ae68a749ffdaa7401dd273903d3552277fa`.
Compressed layers total 1,281,108,852 bytes (about 1.28 GB); shared-layer reuse and
uncompressed disk usage are not yet known. Host C: had about 96 GB free at inspection.

Approval is needed under AGENTS.md hard gate 7 before this exact pull:

```powershell
docker pull swerebench/sweb.eval.x86_64.conan-io_1776_conan-19735_interface@sha256:564734fbebe544567e2e47bac7362ae68a749ffdaa7401dd273903d3552277fa
```

After approval, verify local identity and original base/environment, then run the
original tests against baseline and reference in separate network-disabled
workspaces with bounded time/resources. Freeze the check protocol before execution;
require complete case accounting and distinguish collection/setup errors from
wrong answers. Validate the public/private task package through full isolated
evaluation before proposing a paid run. Do not expose private material to the agent.

Current status: selection and evaluator-material capture complete; environment
calibration NOT_RUN; no task package admitted, no source allowlist change, no
image pull/build or Docker startup, no provider call. The analysis-only pyarrow
dependency ran through uv's temporary environment; project dependencies unchanged.
No live model/cost allocation is authorized.
