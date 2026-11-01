# Completion reserve and remaining run allowance

Date: 2026-11-01. Local presentation change, not a fresh model experiment.
Base checkout: `88d9d7756528b761dfdb03f150d905b397f9d630`.

## Observed problem and decision

In the [failed-eight rerun](2026-11-01-failed8-rerun-results.md), task8's final
public explanation treated completion as a one-call stage. Its actual ninth
request still showed 32 model calls, 87 tool actions, 31 exploration calls,
1,209 solver seconds and USD3.504356, with reads, probes and edits offered.
`minimum_completion_calls=completion_budget_calls=1` was the capacity needed to
submit the current candidate, not a remaining-call cap. This is a concrete mismatch
between the stopping explanation and the supplied resources.

This issue matters because a mistaken scarcity judgment can terminate useful
diagnosis with ample resources. The observation does not prove that the field caused
the decision or the independent FAIL: the agent may have judged additional work
low-value and supplied an inaccurate explanation afterward. More limits or a new
finish gate would not distinguish these explanations. The user selected a bounded
wording/representation correction with local validation.

## Implemented change

`compact_model_state` replaces four flat completion-forecast fields in the model
view with `action_horizon.completion_reserve`:

- `minimum.model_calls/tool_actions`: capacity needed for the successful required path.
- `with_bounded_recovery.model_calls/tool_actions`: capacity including the existing
  bounded recovery forecast.
- `interpretation`: a reserve of one is not a one-call cap; use `remaining_budget`
  for remaining totals and the exploration state/offered tools for further work.

Unknown dimensions remain absent and zero is retained. Reapplying the projection
preserves the grouped view. Actual current/thin, append/segmented requests receive
the same explanation. The operator-only probe-first diagnostic accepts current and
legacy saved requests without rewriting their inputs.

No limit, admission calculation, forecast, tool schema, system prompt, finish gate,
canonical journal field or recovery identity changes. No mandatory extra inspection,
new planner or model call is introduced. Historical dispatched inputs are immutable.

## Local evidence

Evidence root: `C:/pt/completion-reserve-20261101-v1/`. Validation and the saved
public budget projection are recorded in an append-only `dev-run-v1` journal under
`runs/run_dev_completionreserveclarity.jsonl`; associated files have content hashes.

The focused controls cover actual outgoing inputs with 32 calls versus one call,
current/thin policies, append/segmented contexts, zero/missing dimensions, unchanged
ordinary/correction/action forecasts and legacy diagnostic compatibility. The roomy
case retains 31 exploration calls and probe/edit tools; the one-call case retains
only finish/stop. These verify representation and preserved enforcement, not model
understanding.

- Focused: **152 PASS**, command wall time **6.48s**, under the two-minute bound.
- Fast suite: **1,504 PASS, one host symlink-permission skip**, **905.06s** as
  reported by pytest. It includes both diagnosis/repair and segmented-reproduction
  controls reaching isolated mock evaluation; no separate mock run was needed.
- Ruff and final documentation checks: PASS. The system HTML has 99 resolving local
  links. The six final documentation controls run after the evidence text is updated.
- Saved task8 ninth request: its artifact hash is
  `sha256:4c054260134b119de65d69e8c93ae80d91ae6e555d56f8fd481ecbdef35d9c4d`.
  A read-only projection verifies reserve **1**, remaining calls **32**, exploration
  calls **31**, and identical tools, other forecasts and budget values. This projects
  the budget portion only; the synthetic tests above cover actual request construction.
  The receipt hash is
  `sha256:92e9f153c1f372a492675579f39ca7d6a887d619a4dac52d2c1e18dd02a639ee`.
- Validated runtime:
  `sha256:c455b38f9be2d1845b7cae4609536190a665b4ab5c8d0e0f6156b9b72b52773c`.
  `validation.json` binds source/log hashes and test counts; `commit.json` binds the
  final commit after validation.

Initial validation found a malformed synthetic source span in the new fixture and
four older owner-test cases whose expected tool sets omitted the already-supported
`edit_files`. The fixture and expected sets were corrected; runtime admission was
not changed to fit the tests. The original failure log is retained.

## Evidence boundary and next question

There is no new provider dispatch, benchmark solve, target-patch execution or private
evaluation. The local fast suite's isolated mock evaluation is a synthetic control.
No hidden assertion, reference patch or operator hint is added to agent context.
Existing paid allocations remain closed.

The result preserves the decision to clarify resources before increasing limits.
Whether this prevents premature stopping remains untested with the live model. If
the agent recognizes the remaining resources yet still declines useful work, the
remaining question concerns its evidence/value judgment, not a hidden one-call cap.
