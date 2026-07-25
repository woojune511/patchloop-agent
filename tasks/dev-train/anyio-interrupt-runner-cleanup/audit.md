# Task audit: anyio-interrupt-runner-cleanup

- Dataset role: proposed `memory-development`
- Source: SWE-rebench leaderboard instance `agronholm__anyio-1121`, split `2026_03`
- Frozen benchmark revision: `ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b`
- Upstream issue: <https://github.com/agronholm/anyio/issues/1060>
- Upstream resolution: <https://github.com/agronholm/anyio/pull/1121>
- Base commit: `cb245dba9883516f2ed4c23899de157183a1cb50`
- Resolution commit: `f821c3712a7eb208b17d04f2df9f0168366ead3b`
- Follow-up regression: <https://github.com/agronholm/anyio/issues/1179>
- Follow-up hardening: <https://github.com/agronholm/anyio/pull/1180>
- Hardening commit: `1dbc3b62256e5877bcf610aca98ba6e450d14c20`
- License: MIT
- Evaluator image:
  `swerebench/sweb.eval.x86_64.agronholm_1776_anyio-1121@sha256:063bb968109c70a3fe617d9d30287a3a43d549eb1091b27a030a9af2a74c2320`
- Workflow: real-repository issue fix with a hardened regression oracle
- Failure pattern: interrupted background work survives an owner lifecycle transition
- Public regression: the benchmark's 32 dependency-complete P2P tests from
  `tests/test_pytest_plugin.py`
- Private acceptance: interrupt propagation, no post-interrupt execution, exactly-once async fixture
  cleanup, and preservation of expected pytest outcomes across a shared fixture
- Leakage control: benchmark gold/test patches and private assertion bodies remain evaluator-only

The benchmark gold patch fixes issue #1060, but follow-up issue #1179 showed that catching every
non-`Exception` outcome as an interrupt tears down the runner for pytest `skip` and `xfail`
signals. PatchLoop therefore uses a human-reviewed hardened reference that combines the interrupt
cleanup with the later `OutcomeException` distinction. The original benchmark gold is retained as
`bad/upstream-gold-outcome-regression.patch` and must be rejected. This makes the PatchLoop
evaluator stricter than the original benchmark F2P/P2P oracle while preserving the original issue.

The pinned evaluator image does not contain the optional `hypothesis` dependency. Three unrelated
upstream tests that require it are explicitly deselected; the registered check runs the benchmark's
32 P2P tests rather than treating a missing optional package as a product regression.

Difficulty audit:

| Dimension | Score | Reason |
| --- | ---: | --- |
| Localization | 2 | The report points at the pytest plugin, while the stale task is owned by the asyncio backend runner. |
| Reasoning depth | 2 | Interrupt propagation, task cancellation/draining, stream state, and pytest BaseException classes interact. |
| Implementation breadth | 1 | The production fix is localized but must reconcile several runner fields atomically. |
| Verification breadth | 2 | Signal timing, no-resume behavior, cleanup, expected outcomes, and shared fixtures require separate checks. |
| Total | 7 | Hard under `dataset-manifest-v1`. |

Admission requires an official network-disabled Docker run showing:

1. the unmodified base passes the upstream public suite and fails private no-resume acceptance;
2. the hardened reference passes private, regression, scope, and safety verdicts repeatedly;
3. the original benchmark gold and every other declared known-bad patch are rejected;
4. the evaluator image, task specs, run artifacts, and clean harness commit are content-addressed.

The hidden tests use subprocess-level observable behavior. They do not inspect internal variable
names or require the upstream implementation shape.
