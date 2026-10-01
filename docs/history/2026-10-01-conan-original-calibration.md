# Conan original benchmark environment calibration

## Question and fixed inputs

Does the selected original SWE-rebench task reproduce its original failing case
and accept its reference patch without altering the evaluator or test membership?
This checks environment/evaluator readiness before a fresh agent attempt.

Instance `conan-io__conan-19735_interface`, base
`4a65d65f53d2ab37f4ce0e52dc3f25cd832b2934`. Selection and dataset identities are
recorded in [readiness](../../.agent/original-next-readiness.md). Selection was
frozen before decoding original tests/reference data; no image-based substitution.
Original benchmark tests and case lists were used, not newly authored hidden tests.

## Approved acquisition and environment

The user approved the exact image pull. Retrieved:
`swerebench/sweb.eval.x86_64.conan-io_1776_conan-19735_interface@sha256:564734fbebe544567e2e47bac7362ae68a749ffdaa7401dd273903d3552277fa`.
Local image inspection confirms the digest. Pull output shows only the final
layer was newly downloaded; the other layers were reusable. The 1.28 GB figure
was total compressed layer size, not measured transferred bytes or host disk growth.
No build or Docker Desktop startup was performed.

The image reports Python 3.13.13, pytest 7.4.4, the exact base commit and clean
tracked source. Calibration reused the existing original-benchmark container
program and extracted parser/grading functions from pinned upstream harness
revision `e4907b7a90eafaa1f0a6428fd04fe31cdd8b4284`.
Protocol/program/scoring identities were journaled before test execution.

Each environment/baseline/reference check used a separate disposable container,
network none, no host mounts or credentials, dropped capabilities,
no-new-privileges, 2 CPUs, 4 GB memory and 256 PIDs. Tests had a 90-second limit,
outer container execution 115 seconds. Source/test changes were confined to
the container writable layer. Every owned container was removed successfully.

## Results

| Original evaluation | Baseline | Reference patch |
| --- | --- | --- |
| FAIL_TO_PASS | 0/1 pass | 1/1 pass |
| PASS_TO_PASS | 21/21 pass | 21/21 pass |
| Missing required cases | 0 | 0 |
| Test exit code | 1 | 0 |
| Original resolution | RESOLVED_NO | RESOLVED_FULL |

No timeout, setup/collection error or additional nonpassing case was observed.
These results support the frozen environment and original oracle functioning for
this task. They are not an agent solve or a general accuracy result. No provider
calls, token counting, paid allocation or agent-context exposure occurred.

## Evidence and remaining work

External root: `C:\pt\preparations\original-next-20261001-v1`.
Selection journal: `runs/run_dev_originalnextselection.jsonl`.
Acquisition journal: `runs/run_dev_originalnextacquisition.jsonl`.
Calibration journal: `runs/run_dev_conanoriginalcalibration.jsonl`.
All detailed test logs, private inputs, image metadata and scoring artifacts are
content-addressed outside the repository. Historical evidence is unchanged.

Environment calibration is complete. The task still needs a checked-in public/
private package, prepared source and applicable probe dependencies, public check
selection from unmodified upstream source, and a full isolated package evaluation.
Preserve original issue and oracle behavior during that integration; do not feed
reference/test patch material to the coding agent. No live run is authorized.
Only documentation changed in this step; documentation tests and diff checks pass.
