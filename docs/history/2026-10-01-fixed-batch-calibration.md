# Fixed three-task benchmark calibration

## Question and scope

Can the three preselected original benchmark environments reproduce their stated
failures and accept their reference patches? This gate separates environment or
oracle failures from future agent repair failures. Selection was frozen before
private test/reference inspection, without replacements or image-based filtering.
See the [protocol](../../.agent/fixed-batch-proposal.md) for dataset, source and
image identities, selection rule and unchanged proposed agent baseline.

The user explicitly approved the three pinned image downloads and offline
calibration. All three pulls succeeded, and local image inspection confirmed the
approved RepoDigests. No image build, Docker Desktop startup or model call occurred.
Manifest unique compressed layers total 1,839,136,655 bytes; this is not measured
network transfer or host disk growth because shared/cached layers may be reused.

## Method

Used the existing `diagnostics.anyio_benchmark_calibrate.PROGRAM`, environment
inspection from `diagnostics.original_pilot_calibrate.ENV`, and cached extracted
upstream scoring functions from SWE-rebench harness commit
`e4907b7a90eafaa1f0a6428fd04fe31cdd8b4284`. Bound their content hashes and the
driver before tests. Preserved original test patches, F2P/P2P membership and
reference patches; no evaluator rewrite or agent guidance change.

Each environment/base/reference operation ran in a separate disposable container:
network none, no host mounts or credentials, all capabilities dropped,
no-new-privileges, 2 CPUs, 4 GiB memory and 256 PIDs. Test limit was 90 seconds,
outer container limit 115 seconds. All nine containers were removed with confirmed
cleanup. Each environment reported the exact source base and clean tracked files,
with Python 3.13.13. Writable container source was required for applying patches;
this is operator calibration, not a probe sandbox safety result.

Expected baseline: every F2P case fails and every P2P case passes. Expected reference:
every required case passes. Missing cases, setup errors and timeouts would leave
calibration incomplete rather than count as evidence of repair failure.

## Results

| Task | Base F2P passing | Reference F2P passing | P2P passing in each state |
| --- | ---: | ---: | ---: |
| OpenSandbox 816 | 0/1 | 1/1 | 108/108 |
| pyinfra 1679 interface | 0/3 | 3/3 | 10/10 |
| isort 2491 | 0/1 | 1/1 | 73/73 |

All six test executions had complete required-case accounting, no timeout, and
the expected result: baseline exit 1, reference exit 0. All five F2P cases were
explicitly FAILED on baseline, not skipped or missing. The 191 P2P cases passed
in both states. This supports using these image/oracle pairs for further package
preparation. It does not establish agent correctness, broad hidden-test coverage,
or equivalence of future public/probe environments.

## Evidence and next decision

External root: `C:\pt\preparations\fixed-batch-20261001-v1`.
`calibration-v1/summary.json` contains compact results.
`calibration-v1/runs/run_dev_fixedbatchcalibration.jsonl` is append-only and hash-chained;
`calibration-v1/evaluator-artifacts` contains private inputs, logs, scoring code,
image receipts and cleanup receipts. Driver:
`C:\pt\fixed_batch_calibrate_20261001.py`. Runtime checkout at launch: `792b2e86`.
Original selection and preflight records remain unchanged.

Keep the frozen task selection and agent baseline. Next prepare runtime task
packages, exact source admission, public regression checks, isolated end-to-end
evaluation and clean probe dependencies/canaries. Those steps remain unexecuted;
the three-source preflight checkouts alone are not runtime admission. No paid run
is authorized, and the proposed USD 9 allocation has not been opened.
