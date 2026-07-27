# Task audit: kubeflow-exit-handler-after-dependencies

- Dataset role: proposed `core-cross-repo`
- Source: SWE-rebench leaderboard instance `kubeflow__pipelines-13112`,
  split `2026_03`
- Frozen benchmark revision:
  `ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b`
- Frozen benchmark row: `92`
- Upstream issue: <https://github.com/kubeflow/pipelines/issues/10722>
- Upstream resolution: <https://github.com/kubeflow/pipelines/pull/13112>
- Base and environment commit:
  `98f5b7a300ee52d6c530b429558b718ade9fdb7a`
- Base tree: `24f4a3556de13ddc11b574c748b7090b9a908869`
- PR head: `67ac7a290bc2a07477821e1463a0b85b16e53f58`
- PR head tree: `f9421bba99e98ac49898c31add91369b07215f39`
- Merge commit: `0e775d5c7b1d3d5ba4870992bb544edf9850198e`
- Merge tree: `f74032f91e7b1c086a93d667bb915e5ae7731a9e`
- Created: `2026-03-23T23:40:27Z`
- Merged: `2026-03-27T14:44:55Z`
- License: Apache-2.0; base `LICENSE` blob
  `261eeb9e9f8b2b4b0d119366dda99c6fd7d35c64`
- Retrieved: `2026-07-28`
- Frozen production patch SHA-256:
  `sha256:ea57612615fc67d2707284b740ee5be170fa2684ad1d98e72046bf18d5d940a1`
  (159 serialized lines)
- Frozen test patch SHA-256:
  `sha256:fb94e7491c0121e4343d3aa246ee10e808aabfc3a88570966aad2cb99c376729`
  (189 serialized lines)
- Evaluator image:
  `swerebench/sweb.eval.x86_64.kubeflow_1776_pipelines-13112@sha256:842b24c98e1b2c1145b8826b90a95e0634a3520cd523b3d3ae6940201ec2e79a`
- Workflow: real-repository issue fix
- Failure pattern: an explicit dependency name is assumed to identify only a
  task even when `.after()` recorded an `ExitHandler` group
- Expected source changes: `sdk/python/kfp/compiler/compiler_utils.py` and
  `sdk/python/kfp/dsl/pipeline_task.py`
- Benchmark declaration: seven F2P and 278 P2P nodes
- Contamination risk: high. The issue, pull request, benchmark row, accepted
  patch, and benchmark tests are public.

The reference is the exact two-production-file patch frozen in the benchmark
row. It adds public validation and typing to `PipelineTask.after`, then resolves
recorded dependency names against both pipeline tasks and supported task
groups. The 189-line benchmark test patch is excluded from the task package.
Applying it produces accepted blobs
`e2f16b2bce413efe92b66f630dd917f6ff2df18b` for `compiler_utils.py` and
`c77529bad6e3720f328e2c0b3c0c920182db6415` for `pipeline_task.py`.

## Visible regression selection

The registered check copies only the submitted `sdk/python/kfp` package from
the read-only `/workspace` mount to a fresh `/tmp` source root. It runs the
base-resident `compiler_test.py` and `pipeline_task_test.py` modules from their
original read-only paths while importing the copied production package. The
authoring probe observed 277 passing base-resident cases. The benchmark test
patch adds seven F2P tests and one preservation P2P test, so its 278 declared
P2P nodes decompose into exactly 277 base-resident tests plus that one
evaluator-only addition. The complete two-module visible surface therefore
matches the base-resident P2P declaration.

The check uses the testbed interpreter, redirects Python cache and home state
to `/tmp`, and does not copy either visible tests or the private oracle to a
writable location.

## Independent acceptance design

The private oracle is independently authored and does not copy the benchmark
test patch. It checks submitted-source binding plus ten semantic boundaries:

- public `.after()` acceptance and name recording for an `ExitHandler`;
- compiled dependency placement on the group rather than its exit task;
- preservation of mixed ordinary-task and group dependencies;
- ordering through two chained exit-handler groups;
- early, mutation-free rejection of a non-exit task group;
- early, mutation-free rejection of an arbitrary object;
- clear rejection of a manually recorded missing dependency;
- clear rejection of an ambiguous task/group name;
- continued rejection of direct cross-group dependence on an inner task; and
- task-final-status attribution to the depended-on exit-handler group.

The package uses `task-private-v2`; the private spec binds the exact hidden
oracle SHA-256 so undeclared files or oracle mutation are rejected before
evaluation.

The bad-patch corpus models eight distinct partial fixes: public validation
without compiler resolution, compiler resolution without public validation,
fallback to any task group, resolving a group as its exit task, silently
preferring a task on name collision, leaking a raw key error for unknown
names, recording only the first dependency, and accepting every task-group
type in the public API. A no-op and forbidden test edit cover base rejection
and policy enforcement.

Difficulty audit:

| Dimension | Score | Reason |
| --- | ---: | --- |
| Localization | 1 | The public failure appears in compiler topology construction, while dependency names are recorded earlier by the DSL task API. |
| Reasoning depth | 2 | Task, supported group, unsupported group, missing, ambiguous, nested-context and final-status semantics must remain distinct. |
| Implementation breadth | 2 | The accepted change spans the public task API and compiler dependency resolver. |
| Verification breadth | 2 | Single, mixed, chained, invalid, ambiguous and final-status cases diverge independently. |
| Total | 7 | Hard under `dataset-manifest-v1`. |

## Admission status

Admitted as the sixth `core-cross-repo` task on 2026-07-28. The 13-case
official matrix ran from clean staging commit
`5e7b019e60b4d76f67e48bafe6fd1a3b309fe313` with the exact public/private
spec hashes and pinned image:

- the exact two-file reference passed three of three independent runs;
- base/no-op passed all 277 visible tests plus 15 subtests and failed the
  11-test independent hidden acceptance;
- all eight semantic partials were rejected, with two also failing visible
  regression coverage; and
- the forbidden test edit failed hidden acceptance, scope and the generalized
  test-tampering verifier.

All 13 runs were `official=true`, used `--network none`, read-only root and
submitted filesystems, and made zero model/API calls. The machine-readable
report is
`reports/docker-gate/research-kubeflow-exit-handler-after-dependencies.json`
with SHA-256
`c7998d064949dd5a67f05c15ff7d426ef1051f74fea7bb03e37f91c7d1d5084c`.
This is deterministic evaluator admission evidence, not agent-performance or
memory-improvement evidence.
