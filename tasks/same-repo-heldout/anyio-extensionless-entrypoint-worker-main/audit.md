# Task audit: anyio-extensionless-entrypoint-worker-main

- Dataset role: admitted `core-same-repo`
- Source: SWE-rebench leaderboard instance `agronholm__anyio-1134`, split `2026_03`
- Frozen benchmark revision: `ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b`
- Benchmark row: 14
- Upstream issue: <https://github.com/agronholm/anyio/issues/1027>
- Upstream resolution PR: <https://github.com/agronholm/anyio/pull/1134>
- Benchmark base: `01b8d02381ba95ba11241c1ec361e908fe05b8be`
- PR head: `021201c701465c946458822ea25ae61dedf2552d`
- Merge commit: `bcb2db67c8a3d96c1c514954fe1bbce58efd2d8a`
- License: MIT
- Retrieved: `2026-07-27T02:35:00Z`
- Evaluator image:
  `swerebench/sweb.eval.x86_64.agronholm_1776_anyio-1134@sha256:d7997027864d2bfb32d649e7e544381f5d1b161df8f1682c719d222d66489dc0`
- Workflow: real-repository issue fix
- Failure pattern: a loader assumes the executable path has a Python source suffix
- Expected source change: `src/anyio/to_process.py`
- Benchmark declaration: four F2P and 36 P2P nodes
- Public regression: all 36 parameterized process-pool tests across asyncio,
  asyncio+uvloop, asyncio+eager and trio
- Private acceptance: submitted-source binding, extensionless and unknown-suffix
  entrypoints, asyncio and trio, path spaces, `__main__`/`__mp_main__` identity,
  module and file metadata, exactly-once loading, worker reuse, ordinary `.py`
  compatibility and initialization-error propagation
- Contamination risk: high. The issue, PR, benchmark row and accepted patch are public.

The benchmark gold plus its separate test patch touch four files, but only
`src/anyio/to_process.py` is production behavior for issue #1027. PatchLoop
excludes the changelog, unrelated documentation dependency marker and benchmark
test patch. The reference is the exact accepted production hunk.

This task is distinct from development task `anyio-interrupt-runner-cleanup`.
The development task changes async pytest runner cancellation in
`src/anyio/_backends/_asyncio.py`; this task changes process-worker reconstruction
of an executable's main module in `src/anyio/to_process.py`. They share a
repository but not a module, lifecycle, trigger, failure mechanism or solution
lineage.

Difficulty audit:

| Dimension | Score | Reason |
| --- | ---: | --- |
| Localization | 1 | The issue identifies process-worker main loading, but the parent/worker protocol and import state must still be traced. |
| Reasoning depth | 2 | Module execution, pickling, two module names, recursion guards and exception transport interact across a process boundary. |
| Implementation breadth | 1 | One production module changes without a public API or dependency change. |
| Verification breadth | 2 | Backends, path forms, module identity/metadata, execution count, worker reuse and error propagation require separate observations. |
| Total | 6 | Hard under `dataset-manifest-v1`. |

The official network-disabled Docker matrix showed:

1. the unmodified base passed all 36 public regressions and failed the independent
   hidden oracle;
2. the exact production reference passed public and private checks three times;
3. representative loader, alias, metadata, execution-count and scope/tampering
   partials were rejected;
4. evaluator image, task specs, patches, run artifacts and the clean harness
   commit are content-addressed.

The 14-run gate is recorded in
[`reports/docker-gate/research-anyio-extensionless-entrypoint-worker-main.json`](../../../reports/docker-gate/research-anyio-extensionless-entrypoint-worker-main.json)
and is bound to clean harness commit
`9dfc60dd4b469f17732bb3bf4eeca0e61e10bdac`.

The hidden oracle observes actual child-process behavior. It does not import
private helpers, require `runpy` or `ModuleType` by name, or copy the benchmark
test values.
