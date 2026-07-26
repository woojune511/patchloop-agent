# Task audit: pyfakefs-makedirs-parent-traversal

- Dataset role: proposed `memory-development`
- Source: SWE-rebench V2 instance `pytest-dev__pyfakefs-991`, split `train`
- Benchmark revision: `475dd5e8703bb5fb22dd3c60b5d038b019eba1e0`
- Benchmark row: 308
- Upstream issue: <https://github.com/pytest-dev/pyfakefs/issues/987>
- Upstream resolution: <https://github.com/pytest-dev/pyfakefs/pull/991>
- Base commit: `7285b671883b8a06fc26466582a8a45baf508bf7`
- PR head: `a3abfcc52e7a5b8b31b9e5005de61fe37250cf5a`
- Merge commit: `080529189ac09d1fea2202cae4396aa964a3ad1f`
- License: Apache-2.0
- Retrieved: `2026-07-26T19:50:26Z`
- Benchmark gold patch SHA-256:
  `sha256:5a41a1a02dda3f1804c94456bb1610d7aabca6b277a7e705bdc996c5e51219fa`
  (46 serialized lines, two files, `+22/-1`; production hunk `+21/-1`)
- Benchmark test patch SHA-256:
  `sha256:030b095bd9b551a315e81ae423f3467aeda52b3e844cba94472f63ecda31565b`
  (20 serialized lines, one file, `+8/-0`)
- Evaluator image:
  `docker.io/swerebenchv2/pytest-dev-pyfakefs@sha256:6de3b39018eec22728567f44dfbdc3cbd31322c384f6ee3d7f328ef38165d57c`
- Workflow: real-repository issue fix
- Failure pattern: whole-path normalization erases traversal side effects
- Expected source change: `pyfakefs/fake_os.py`
- Benchmark F2P declaration: one test
- Benchmark P2P declaration: 517 tests from `pyfakefs/tests/fake_os_test.py`
- Private acceptance: submitted-source binding, component-order side effects,
  nested and bytes paths, trailing separators, existing-leaf policy,
  non-directory parent errors, and mode separation
- Leakage control: benchmark interface, issue and PR text, gold patch, test patch,
  reference patch, and hidden assertions remain evaluator-only and are excluded
  from agent context and memory source text
- Contamination risk: high. The issue, merged patch, tests, and benchmark row
  have been public since 2024.

The benchmark gold also changes `CHANGES.md`. PatchLoop uses the exact upstream
production hunk in `pyfakefs/fake_os.py` as a normalized reference and excludes
the changelog and upstream test patch. The private oracle is independently authored
and does not copy the benchmark F2P test.

Difficulty audit:

| Dimension | Score | Reason |
| --- | ---: | --- |
| Localization | 1 | The public method is identifiable, but the defect sits below a seemingly valid final result. |
| Reasoning depth | 1 | Correctness depends on ordered component traversal, not normalized path equivalence. |
| Implementation breadth | 1 | One production module changes without a public API change. |
| Verification breadth | 2 | Nested, bytes, existing, error, separator and mode cases diverge independently. |
| Total | 5 | Medium under `dataset-manifest-v1`, matching the benchmark metadata. |

Admission remains pending until the clean committed harness passes the official
Docker base/no-op, three-reference, upstream-regression, and known-bad gates.
