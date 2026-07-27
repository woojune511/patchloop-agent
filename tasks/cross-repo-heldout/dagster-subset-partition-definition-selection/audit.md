# Task audit: dagster-subset-partition-definition-selection

- Dataset role: proposed `core-cross-repo`
- Source: SWE-rebench leaderboard instance `dagster-io__dagster-33605`,
  split `2026_03`
- Frozen benchmark revision:
  `ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b`
- Frozen benchmark row: `35`
- Upstream issue: <https://github.com/dagster-io/dagster/issues/33584>
- Upstream resolution: <https://github.com/dagster-io/dagster/pull/33605>
- Base and environment commit:
  `f8430dc7bf76bfab4f026165e5c5f821104298df`
- Base tree: `db9b18f7592d800c8ad056e6a3f4520cfae7977e`
- PR head: `f1d8ab55d59431bfedb02b99b58d42911e8ce9a4`
- PR head tree: `5edfd9d7d57f67f4631136e37a7dd48bd6fcdc72`
- Merge commit: `2c0b00d9b6149c5e493cbeb636a47a12db95ba6d`
- Merge tree: `14568e8433b2f4a2d700ac6dbb876ed1512d89ac`
- Created: `2026-03-15T15:42:33Z`
- Merged: `2026-03-16T15:42:20Z`
- License: Apache-2.0; base `LICENSE` blob
  `82b6b68d6ad4d65757310c2e7dab12ccae01de36`
- Retrieved: `2026-07-27T16:50:08Z`
- Benchmark production patch SHA-256:
  `sha256:1f0ec526d126ef8893fb40d032cc5a26b52bb1eb1b2eba56757541088ae0308e`
  (42 serialized lines)
- Benchmark test patch SHA-256:
  `sha256:c8eb674dc7d4082c7e4ef006a65ec229c229f78405b94790cddd1d06a2ebf06a`
  (52 serialized lines)
- Evaluator image:
  `swerebench/sweb.eval.x86_64.dagster-io_1776_dagster-33605@sha256:98a0b69301022cba2ac7520a8ab1891c2a490cf4ec4ba889d6ce36a29f40831b`
- Workflow: real-repository issue fix
- Failure pattern: unselected entity partition state leaks into a selected
  multi-asset subset
- Expected source changes:
  `python_modules/dagster/dagster/_core/definitions/assets/definition/assets_definition.py`
  and `python_modules/dagster/dagster/_core/execution/context/system.py`
- Benchmark declaration: one F2P and 28 P2P tests
- Contamination risk: high. The issue, pull request, benchmark row, accepted
  patch and test patch are public.

The task reference is the exact two-production-file patch frozen in the
benchmark row. It adds 12 lines, removes seven lines and excludes the
benchmark's evaluator-only regression test. The resulting blobs are
`641d5c12f673f6f06330e796641e009bc4db43dc` for
`assets_definition.py` and
`941d5ce1aa6c2306c5934725ea77b909a290cbef` for `system.py`, matching both
the PR head and merge result. Targeted history review through 2026-07-28
found no revert or semantic correction; the selection-aware property and
execution-context delegation remain upstream.

## Visible regression selection

All 28 base-resident P2P nodes are in
`python_modules/dagster/dagster_tests/asset_defs_tests/test_partitioned_assets.py`.
They pass in 2.96 seconds inside the image's `/testbed`. A direct Windows
read-only bind is much slower because importing the Dagster monorepo performs
many small filesystem reads: the full file took about 161 seconds and cannot
fit the normal task timeout.

The registered check therefore copies only the submitted production package,
`python_modules/dagster/dagster`, from the read-only `/workspace` mount to a
fresh `/tmp` import root. It executes the complete 28-node visible module from
its original read-only `/workspace` path with `PYTHONPATH` bound to the copied
production source. The hidden oracle likewise remains on the read-only mount
while importing the copied submitted source, and it asserts that
`dagster.__file__` resolves below that temporary source root. Networking
remains disabled and neither the visible tests nor hidden oracle are copied to
a writable location. A reference authoring probe completed the copy-backed
boundary within the 90-second registered timeout.

The task uses `task-private-v2`; the private spec binds the exact hidden oracle
SHA-256 and the loader rejects either undeclared hidden files or content
mutation before evaluation.

## Independent acceptance design

The private oracle does not copy the benchmark materialization test. It
constructs subsettable definitions directly and checks:

- a selected non-partitioned asset ignores an unselected partitioned sibling;
- a selected partitioned asset retains its exact definition;
- only selected incompatible definitions trigger the existing conflict;
- check-only selection contributes an asset-check partition definition;
- unselected asset checks do not poison an asset-only subset;
- compatible selected asset and check definitions deduplicate; and
- `StepExecutionContext` delegates to the selection-aware property rather
  than scanning specs again.

The draft known-bad corpus contains eight semantic partials: updating only
the `AssetsDefinition`, updating only the execution context, filtering only
asset specs, filtering only check specs, including every check regardless of
selection, comparing a check's asset key instead of its check key, silently
returning the first conflicting definition, and treating every subset as
unpartitioned. A no-op and a forbidden test edit cover base rejection and
scope/tampering enforcement.

Difficulty audit:

| Dimension | Score | Reason |
| --- | ---: | --- |
| Localization | 1 | The failure appears at `partition_key`, while duplicated derivation lives in a definition property and execution context. |
| Reasoning depth | 2 | Asset keys, check keys, selected subsets, compatible definitions and real conflicts have distinct semantics. |
| Implementation breadth | 2 | The correction spans the public `AssetsDefinition` property and execution-context policy in separate modules. |
| Verification breadth | 2 | Asset-only, check-only, selected, unselected, compatible, conflicting and delegation cases diverge independently. |
| Total | 7 | Hard under `dataset-manifest-v1`. |

Admission remains pending. It requires a clean staging commit and an official
network-disabled, read-only Docker matrix proving base visible pass/private
fail, three exact-reference passes, rejection of all semantic partials, and
scope/tampering rejection. No model-performance result is claimed here.
