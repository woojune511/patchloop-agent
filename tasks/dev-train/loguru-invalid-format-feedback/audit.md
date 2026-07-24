# Task audit: loguru-invalid-format-feedback

- Dataset role: proposed `memory-development`
- Source: SWE-rebench leaderboard instance `delgan__loguru-1451`
- Upstream issue: <https://github.com/Delgan/loguru/issues/1450>
- Upstream resolution: <https://github.com/Delgan/loguru/pull/1451>
- Base commit: `2abeb0fa6d7be4b0455c6e0b580b1e9dab19005e`
- Resolution commit: `b782e56fcf07fecf9545ff6ee2350baacb0968ce`
- License: MIT
- Workflow: real-repository issue fix
- Failure pattern: an internal catch boundary removes diagnostic context
- Expected source change: `loguru/_handler.py`
- Public regression: ordinary static formats and patcher-injected top-level fields
- Private acceptance: actionable feedback in both catch modes, complete record-key context,
  and dynamic patcher-key compatibility
- Leakage control: the benchmark gold patch, upstream test patch, and hidden assertions remain
  evaluator-only and are excluded from the agent context and future memory source text

Difficulty audit:

| Dimension | Score | Reason |
| --- | ---: | --- |
| Localization | 1 | The issue points at formatting but not the handler catch boundary. |
| Reasoning depth | 1 | The fix must preserve two exception modes and exception chaining. |
| Implementation breadth | 1 | A reusable diagnostic path is needed within one production module. |
| Verification breadth | 2 | Catching, propagation, message contents, record keys, and patcher fields interact. |
| Total | 5 | Medium under `dataset-manifest-v1`. |

Admission requires an official network-disabled Docker run showing:

1. the unmodified base passes public checks and fails private acceptance;
2. the upstream reference patch passes hidden, regression, scope, and safety verdicts;
3. every declared known-bad patch is rejected at its intended boundary;
4. the checkout and evaluator image are content-addressed in the evidence artifact.

The hidden tests were authored for PatchLoop from the upstream behavioral contract rather than copied
from the upstream test patch.
