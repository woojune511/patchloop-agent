# Thin policy adapter and local execution parity

Date: 2026-10-07. Source baseline: `a447dc6f`. User-authorized implementation of
the [prepared interface](2026-10-07-policy-candidate-prep.md), official=false.
No provider calls, task probe replays, image operations or paid allocation.
Legacy sweep runtime hash:
`sha256:7ec7e6f896a0868f5935b58197ff491526cc8423bb7fa6f63db17deb307cadef`.
Final runtime hash after preserving the current parser's error path:
`sha256:3381660b5484eb474efe897157c711b32a8c26f54cbba05ab90ac1c9ec226522`.

## Problem and decision

The [system review](2026-10-07-system-review.md) left a concrete interface question:
the agent still submitted inadequate candidates despite retained public failures,
available diagnostic tools and earlier prompt/context interventions. Decision and
plan narration may be ineffective or counterproductive, but the observations do
not establish that cause. Candidate quality or use of evidence can remain the
limiting factor even with simpler presentation.

Testing that question needs an executable alternative, not fabricated decision
fields under a shorter prompt. This change implements the prepared policy bundle
and tests operational parity. It does not measure model behavior or adopt a new
default. Keep `current`; any live comparison still needs a frozen task/model/cost
scope and success criteria. The missing SQLFluff-1733 A2 public replay and the
incomplete 1517 oracle remain separate evidence gaps.

## Change

`--agent-policy thin --planning-policy none` selects the bounded prompt and explicit
projection in [thin_policy.py](../../patchloop/dev/thin_policy.py). Schemas retain
tool names, descriptions and operational arguments, while replacing `turn_decision`
with required nullable root `memory_update`. Notes and concerns still use their
existing independent, nonblocking validation. B has no model-authored plan state,
decision rationale or invented inspection intent.

Only named derived advice fields are removed. Source selection, actual source and
result payloads, current/historical checks, mutation expectations and resource
forecasts stay shared. Segments keep the same boundary algorithm and limits with
the specified narration removed; shorter requests may still change size boundaries.
Native calls use B's actual annotations, including null. The existing whole-turn
`turn_decision_recorded` lifecycle remains without manufacturing per-call decisions.

Malformed B annotations also retain their actual presence and values across
durable recovery; unexpected decisions are rejected without A's normalization.
Internal presence metadata is absent from default A records and provider arguments.
The current parser still extracts only `turn_decision`: an unexpected root
`memory_update` remains an operational argument and reaches the same tool-input
rejection as before, rather than consuming a protocol correction.

Policy selection binds model/tool identities, the immutable envelope, segment
bindings and the evaluation manifest. Resume rejects policy changes. Default A
serialization and golden schema/tool-surface hashes remain unchanged. Mutations,
source anchors, required checks, optional tests/probes, budget admission and
idempotent recovery reuse existing execution code.

## Local validation

- Fast malformed-wire regression before the final current-parser correction:
  **7 passed in 9.48s**, `C:/pt/validation/thmal10.log`.
- The current-parser compatibility regression failed before the correction
  (**1 failed in 0.90s**, `C:/pt/validation/tharegr01.log`). After correction,
  all **11** selected current/thin wire and bounded-correction cases passed:
  `C:/pt/validation/thwire12.log`, basetemp `C:/pt/tmp/thwire12`.
- Earlier expanded adapter comparison: **62 passed in 189.54s** alongside the
  disjoint legacy suite, `C:/pt/validation/thfocus11.log` and `.xml`.
  Optional diagnostic additions: **8 passed in 62.56s**,
  `C:/pt/validation/thop01.log`. These broader integration groups are separate
  from the fast regression gate.
- Final complete adapter selection: **71 passed in 163.79s**, four workers,
  `C:/pt/validation/thfinal12.log` and `.xml`, basetemp `C:/pt/tmp/thfinal12`.
  This complete integration selection exceeds the two-minute focused target;
  the 11-case wire regression is the separate fast gate.
- Ruff: `uv run ruff check patchloop tests` passed.
- Documentation layout, size and links: **5 passed in 0.08s**,
  `C:/pt/validation/thdocs12.log`.
- Legacy full suite: **4513 passed, 19 skipped, 1 failed in 3786.01s**,
  `C:/pt/validation/thall11.log` and `.xml`, basetemp `C:/pt/tmp/thall11`.
  It excludes only the three new adapter files. The failure was
  `test_real_local_timeout_retains_partial_output_and_leaves_no_readers`: the
  child had no first output within its 0.3-second timeout under parallel load.
  All **28** cases in `tests/test_sandbox_capture.py` then passed in isolation
  against the same unchanged runtime (`C:/pt/validation/thcap12.log`). This is
  consistent with a startup-sensitive test; the sweep is not a clean full-suite
  PASS. No sandbox code or timeout assertion was changed. The broad sweep was
  not repeated after the separate current-parser correction.
- Final CLI mock smoke on the final runtime: current/brief-v1
  `run_dev_20f26adb92c54c10` and thin/none `run_dev_8ce6b653c50746d4` both
  **EVALUATOR_PASS**, each four model calls, five tool actions and one accepted
  edit. State roots: `C:/pt/validation/thsmoke-current12` and
  `C:/pt/validation/thsmoke-thin12`; CLI result files append `.json` to those roots.
  Public checks and isolated task acceptance PASS; safety NOT_RUN, provider cost zero.

The focused cases cover exact default wire, strict annotation selection, read-batch
limits, invalid/stale/forbidden anchors, rollback, current-diff check invalidation,
annotation errors, completed replay, interrupted post-write recovery, cross-policy
resume rejection, unchanged resource/tool decisions, real B continuation/handoff,
incomplete/malformed-response recovery and program replay with actual annotation
hashes. Extra cases cover selected-test PASS/FAIL/setup ERROR and trusted local
probe PASS/assertion/import-setup outcomes without completion credit,
zero-model/one-action automatic repair rechecks, real source citation expiry and
failure-linked concerns independent of submission eligibility.
Mock execution reaches isolated task acceptance in append, native-window and
segmented contexts; safety remains NOT_RUN. Fake-provider transport tests count
requests locally and do not contact OpenAI.

Initial tests exposed a missing manifest-to-evaluator policy binding, a rejected
thin-call null-presence loss and current-parser error-path drift; all were fixed
and regression-tested. An earlier
current-policy sweep overlapped edits and had two evaluation ContractErrors; it is
superseded by frozen-source validation. An initial full run was stopped to fix the
wire issue before restarting the disjoint suites. Test-fixture mistakes were also
corrected before the final 62-case pass. None measures model repair behavior.

## Interpretation and next question

The implementation makes the policy alternative concrete and preserves the tested
execution contracts. It does not show improved repair success, lower live cost or
better use of public counterexamples. No baseline change, automatic retry, mandatory
probe, candidate selector or paid follow-up is justified by mock success. A future
bounded comparison can test the bundle only after its public evidence and admission
conditions are fixed; component-level attribution would require separate evidence.
