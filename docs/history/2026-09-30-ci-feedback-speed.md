# CI feedback latency: local diagnosis and bounded scheduling change

Date: 2026-09-30. Completed local investigation; hosted validation is a separate
receipt. This is engineering feedback evidence, not agent repair-quality evidence.

## Problem and competing explanations

The integration PR at `b7de8ccbf79fdc61503fdb0fb2ed339d101061a4` ran both PR and
branch-push workflows. Each repeated the complete suite on Linux and Windows.
PR run `36619883797` passed 3,688 tests with 25 skips on each OS; pytest took
519.48 seconds on Linux and 2,564.75 seconds on Windows. Duplicate push run
`36619870701` also passed, taking 647.34 and 2,339.76 seconds respectively.
Those different timings already show host/run variability.

Candidates included expensive fixture setup, repeated runtime hashing, durable
journal synchronization and serial Git subprocess waits. Existing local JUnit
shards identified slow files, but their summed case durations were not serial
wall-clock measurements. A fresh cProfile of
`test_model_state_review.py::test_blind_freeze_then_unblind_preserves_originals_and_cache`
passed in 32.05 seconds (29.34 call, 1.20 setup). Its 656 `run_git` calls consumed
27.20 cumulative seconds; 335 fsync calls consumed 0.14 seconds. This supports
Git subprocess overhead/waiting as the dominant cost for this case, not a finding
about every slow test. The diagnostic did not establish redundant runtime work
that could safely be removed.

## Change

Retain the actual Git integration coverage and schedule independent files with
four pytest-xdist workers. `--dist loadfile` keeps a file together and pytest gives
workers separate temporary directories. `--max-worker-restart 0` makes a worker
crash fail the run without automatically replacing it. Small focused checks remain
serial. See the official [distribution options](https://pytest-xdist.readthedocs.io/en/stable/distribution.html)
and [worker fixture behavior](https://pytest-xdist.readthedocs.io/en/stable/how-to.html).

Only PR events and pushes to main trigger CI, eliminating duplicate branch-push
runs for open PRs while retaining post-merge validation. Both operating systems
still run all tests, task validation and mock smoke. Logs include the 20 slowest
test phases; JUnit artifacts are retained for 14 days, including failed test runs.
The only dependency additions are development-only pytest-xdist and execnet.
Production source, fixtures, assertions and test selections are unchanged.

## Local result and limits

Collection before and after the change produced the same 3,713 unique node IDs
in the same order. One sequential before/after timing comparison used these four
unchanged tests, fresh separate temporary roots, the same installed dependencies
and no concurrent local test invocation:

- `test_model_state_review.py::test_blind_freeze_then_unblind_preserves_originals_and_cache`
- `test_planning_cycle.py::test_mock_ab_full_fresh_runs_and_completed_reuse`
- `test_public_case_rollout.py::test_four_arm_mock_repair_check_optional_case_finish_and_separate_audit`
- `test_model_state_episode_collector.py::test_mock_multi_turn_public_check_finish_smoke`

All four passed in both modes. Total subprocess wall time was 138.231 seconds
serially and 62.034 seconds with four workers, a 55.1% reduction in this sample.
Individual cases became slower under contention; the gain is overlapping work,
not cheaper individual tests. The serial timing comparison exceeded the two-minute
focused-validation target. This single fixed-order Windows/Python 3.14 comparison
does not establish a stable speedup or hosted Python 3.12 performance. Full hosted
Windows/Linux coverage and timing are pending and must be checked on the PR head.

## Evidence and next question

Append-only evidence root: `C:\pt\analyses\ci-feedback-speed-20260930-v1`.
`run_dev_cifeedback` is the hash-chained dev-run-v1 journal. `baseline.prof`,
`baseline.xml`, `baseline-nodeids.json`, `serial.xml`, `parallel.xml` and
`timing-comparison.json` retain the observations. The baseline profile artifact is
`sha256:69f4a87d791002cabf814608d089d6089b97ca15f550f5977f7b7bac95004acf`.
Original integration logs remain in the separate
`C:\pt\analyses\dev-head-integration-20260930-v1` evidence root.

The remaining question is whether the same complete suite passes under four-worker
scheduling on both hosted operating systems and reduces their feedback latency.
No live provider, Docker execution, task-quality experiment or paid allocation was
started. All development results remain official=false and claim-ineligible.
