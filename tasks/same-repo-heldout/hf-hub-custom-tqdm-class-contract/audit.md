# Task audit: hf-hub-custom-tqdm-class-contract

- Dataset role: proposed `core-same-repo`
- Source: SWE-rebench leaderboard instance
  `huggingface__huggingface_hub-4056`, split `2026_03`
- Frozen benchmark revision:
  `ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b`
- Benchmark row: `64`
- Upstream issue: <https://github.com/huggingface/huggingface_hub/issues/4050>
- Upstream resolution: <https://github.com/huggingface/huggingface_hub/pull/4056>
- Base commit: `6983a4d3d2bdcbd09c6ea08acae64cdf83ccb2e4`
- Base tree: `fb454d52b8dd48b5c43e5a96d0b31dc498cbd7ef`
- PR head: `d5d3eba80b862b84f16f3118bec3a25ba49852dd`
- PR head tree: `0d7a02c09279a25f4380bd8ba790c5e1cb59d68f`
- Squash merge: `0fa8edcb1c1c19a5280ca4e412a0ef8d8303d6e3`
- Merge tree: `bee369a83df2794e7f0f13c624fa83079091cf8f`
- Created: `2026-04-06`
- Merged: `2026-04-07`
- License: Apache-2.0
- Base license blob: `261eeb9e9f8b2b4b0d119366dda99c6fd7d35c64`
- Retrieved: `2026-07-27T03:44:13Z`
- Benchmark production patch SHA-256:
  `sha256:4ed0bca7b7370147472f34b56aa7d67aa2938cf9dd03bfa45a1786df495b04bd`
- Benchmark test patch SHA-256:
  `sha256:265988b2a6734a001f8b4577a9686be5c72c564c7cea97adb2d4f345049599b8`
- Evaluator image:
  `swerebench/sweb.eval.x86_64.huggingface_1776_huggingface_hub-4056@sha256:cbfae263dff792cc7c763057905869c548bf37733352ff999b3d7d4278c87677`
- Workflow: real-repository issue fix
- Failure pattern: Hub-owned visibility and naming policy is imposed on a
  caller-owned progress implementation
- Expected source changes:
  `src/huggingface_hub/_snapshot_download.py` and
  `src/huggingface_hub/utils/tqdm.py`
- Benchmark declaration: two F2P and 19 P2P tests
- Contamination risk: high. The issue, PR, benchmark row, accepted patch, and
  two-file localization exposed by `allowed_paths` are public.

The production-only reference is byte-for-byte identical to the accepted
upstream changes in the two allowed source files; the separate upstream test
patch is not included. The accepted behavior is still present on current main.
PR #4065 later fixed a separate stderr-lock failure, and open PR #4059 describes
its proposal as orthogonal to this custom-class contract. No revert was found.

The benchmark declares 19 P2P nodes although the frozen base file contains 17
tests. Its excluded test patch adds four nodes: two F2P nodes and two nodes
classified P2P because they already pass on the base. The public check therefore
runs all 17 base-resident upstream regressions. The independent oracle separately
checks the added group-policy boundary and strengthens the weak base-passing
`no_name_kwarg` case with a strict foreign class that cannot silently discard the
invalid argument. Admission evidence must report 17 executed upstream regressions
and 19 benchmark-declared P2P nodes as different quantities.

This task is distinct from development task
`hf-hub-xet-endpoint-propagation`. The development task carries request-specific
endpoint context through `file_download.py`, `hf_api.py`, and `utils/_xet.py`.
This task separates library-owned and caller-owned progress construction policy
inside `_snapshot_download.py` and `utils/tqdm.py`. They share a repository but
not a module set, trigger, failure mechanism, or solution lineage.

The public acceptance deliberately names both single-file and snapshot download
paths. The private oracle adds different classes, callable forms, state
transitions, and an offline-mocked snapshot path without copying the two
benchmark tests or requiring a private helper name.

Difficulty audit:

| Dimension | Score | Reason |
| --- | ---: | --- |
| Localization | 1 | The issue identifies custom progress construction, but two construction paths and the existing Hub policy must be traced. |
| Reasoning depth | 2 | Ownership depends on class lineage, callable shape, non-TTY/logging state, and the Hub subclass's own group policy. |
| Implementation breadth | 1 | Two closely related source modules change without a public API or dependency change. |
| Verification breadth | 2 | Foreign classes, callable factories, Hub subclasses, file and snapshot paths, and several disable signals require separate observations. |
| Total | 6 | Hard under `dataset-manifest-v1`. |

## Admission evidence

Pending the clean-commit official Docker matrix. The task remains proposed and
must not enter the dataset manifest until the unmodified base, three reference
runs, semantic partials, and scope/tampering corpus produce immutable evidence.
