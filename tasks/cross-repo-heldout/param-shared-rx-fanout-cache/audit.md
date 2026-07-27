# Task audit: param-shared-rx-fanout-cache

- Dataset role: proposed `core-cross-repo`
- Source: SWE-rebench leaderboard instance `holoviz__param-1117`, split `2026_03`
- Frozen benchmark revision: `ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b`
- Benchmark row: `51`
- Upstream issue: <https://github.com/holoviz/param/issues/1116>
- Upstream resolution: <https://github.com/holoviz/param/pull/1117>
- Base commit: `833c8f05f7a47fa1476620307ef7fd447c45e6fb`
- Base tree: `4ff1217f89eacb433531421269e0d64ff38b8383`
- PR head: `248ade93c6e587f5fe892e5000642be76d33c5f2`
- PR head tree: `68e204d0424d7350765dbd29c993d6f35580b101`
- Squash merge: `d93e585339068de7dadc0bb26b1dc9ee096780b4`
- Merge tree: `9e9809209a9be9f76bd1463eedac6ed68c0e4e05`
- Created: `2026-03-25T14:50:38Z`
- Merged: `2026-03-30T14:27:31Z`
- License: BSD-3-Clause
- Base license blob: `6e7f0c13f45eaa43299d72040698ba863f069745`
- Retrieved: `2026-07-27T04:15:00Z`
- Benchmark production patch SHA-256:
  `sha256:531f7143c3eb04494e3eae258685018c70654f4c3c403aefe10f8a5a2f700d23`
- Benchmark test patch SHA-256:
  `sha256:5cb30a1a08a7a49144b8d2b8a68712194a9419bf6c51470474f9ca7511c2911a`
- Evaluator image:
  `swerebench/sweb.eval.x86_64.holoviz_1776_param-1117@sha256:c10bc0ad51b00c59ed8fa4366ee722c38e83dfaa620a7cc229f78489ccbaf010`
- Workflow: real-repository issue fix
- Failure pattern: one shared reactive source is recomputed independently by each downstream branch
- Expected source change: `param/reactive.py`
- Benchmark declaration: two F2P and 94 P2P tests
- Contamination risk: high. The issue, PR, benchmark row, accepted patch, and
  the one-file localization exposed by `allowed_paths` are public.

The production-only reference is byte-for-byte identical to the accepted
upstream change in `param/reactive.py`; the two upstream regression tests are
not included. The fix is still present on the current main branch, both
regression tests remain, and Param documented the fix for v2.3.3. Later
overlapping changes added lazy evaluation, typing, and weak invalidation
watchers without reverting the shared-evaluation contract. Current main was
inspected for persistence but was not executed as part of this pinned-base
admission.

The public registered check uses the pinned testbed interpreter and runs
`tests/testreactive.py`. Under PatchLoop's network-disabled, read-only Docker
boundary the base collected 101 tests and completed with 94 passed, seven
skipped, and no failures or errors in 2.19 seconds. The default image Python at
`/opt/conda/bin/python` does not contain pytest, so both contracts deliberately
pin `/opt/conda/envs/testbed/bin/python`.

The independent private oracle is intentionally distinct from the two
upstream tests. It uses different parameter models, fan-out shapes, values,
consumer ordering, and invalidation sequences while checking submitted-source
binding, synchronous and asynchronous reuse, generator-backed reuse,
multi-level fan-out, independent graph isolation, repeated reads, updates,
accessor divergence, and error propagation and recovery. These additions
strengthen acceptance; they do not reduce the recorded contamination risk or
make the held-out task eligible for prompt, tool, threshold, or memory tuning.

Difficulty audit:

| Dimension | Score | Reason |
| --- | ---: | --- |
| Localization | 1 | The issue points to reactive fan-out, but the relevant clone, invalidation, resolution, and async paths are separated inside a large module. |
| Reasoning depth | 2 | A valid fix must distinguish shared source state from branch-local operations across synchronous and asynchronous resolution. |
| Implementation breadth | 1 | One production module changes, but several interacting methods participate. |
| Verification breadth | 2 | Cache lifetime, invalidation, independent graphs, coroutines, generators, accessors, and errors interact. |
| Total | 6 | Hard under `dataset-manifest-v1`. |

Admission remains provisional until the reference, base/no-op, semantic
known-bad, and scope/tampering cases pass from a clean harness commit. The
official evidence report and immutable run IDs will be appended only after
those executable gates complete.
