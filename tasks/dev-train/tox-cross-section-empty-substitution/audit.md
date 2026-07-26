# Task audit: tox-cross-section-empty-substitution

- Dataset role: admitted `memory-development`
- Source: SWE-rebench leaderboard instance `tox-dev__tox-3810`, split `2026_02`
- Benchmark revision: `ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b`
- Benchmark row: 2
- Upstream issue: <https://github.com/tox-dev/tox/issues/3809>
- Upstream resolution: <https://github.com/tox-dev/tox/pull/3810>
- Base commit: `02e9ed73da6a0f97f9167e957e1168d6116942ce`
- Resolution commit: `9adb72702cbad18351fbcb80183bd55bddc9b40b`
- License: MIT
- Retrieved: `2026-07-26T17:14:20Z`
- Benchmark gold patch SHA-256:
  `sha256:336a9d33b9c256a3c184501d68d9706596cc8a877ff8790370a0132bc441ea61`
- Benchmark test patch SHA-256:
  `sha256:4f42234fbd651c151d6dec52f4f0ec86faae6195c8307a0236ec7901d4bc6a7e`
- Evaluator image:
  `swerebench/sweb.eval.x86_64.tox-dev_1776_tox-3810@sha256:ffd1129e4be4692becf5011c874858918864d586267002a2917195726542de57`
- Workflow: real-repository issue fix
- Failure pattern: a valid empty result is misclassified as source absence
- Expected source change: `src/tox/config/loader/ini/replace.py`
- Public regression: all 29 benchmark P2P nodes in
  `tests/session/cmd/test_show_config.py`
- Private acceptance: unmatched and matched factor behavior, missing-key defaults,
  multiple independent references, caller-environment context, and preservation of
  same-section computed fallback
- Leakage control: the benchmark gold patch, test patch, reference patch, and hidden
  assertions remain evaluator-only and are excluded from agent context and memory source text
- Contamination risk: high. The task and resolution are public, and the upstream PR
  explicitly records Claude Code assistance.

The bug was introduced by the earlier tox PR #3751. That change intentionally made an
existing same-section value that filters to empty raise `KeyError`, allowing a computed
default such as `base_python` to take over. The same signal then crossed a `SectionProxy`
boundary where an existing-but-empty value must instead resolve to an empty string.
The evaluator therefore rejects broad fixes that remove the earlier fallback behavior.

Later tox PR #3951 also changes the same helper for override propagation. That independent
post-base feature is deliberately outside this task's hidden acceptance.

Difficulty audit:

| Dimension | Score | Reason |
| --- | ---: | --- |
| Localization | 1 | The issue identifies substitution but not the `SectionProxy` exception boundary. |
| Reasoning depth | 2 | The fix must distinguish absence from valid emptiness without undoing an earlier fallback contract. |
| Implementation breadth | 1 | The production fix is localized but needs a reusable resolution path. |
| Verification breadth | 2 | Matched, unmatched, missing, default, caller-context, and same-section cases differ. |
| Total | 6 | Hard under `dataset-manifest-v1`. |

Admission requires an official network-disabled Docker gate showing:

1. the unmodified base passes the 29 public P2P tests and fails private acceptance;
2. the reviewed reference passes hidden, regression, scope, and safety verdicts three times;
3. every declared known-bad patch applies cleanly and fails at its intended boundary;
4. the source commit, evaluator image, specs, patch, manifest, result, and provenance are
   content-addressed in the admission evidence.

The hidden tests are independently authored from the issue behavior. They do not copy the
benchmark F2P test or inspect implementation helper names.
