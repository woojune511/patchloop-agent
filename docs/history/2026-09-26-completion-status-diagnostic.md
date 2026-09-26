# First-input completion advice diagnostic

## Problem and evidence

The [scope audit](2026-09-26-verification-scope-audit.md) found that verification
already narrowed in initial plans, with no observed task/plan delivery loss.
All 12 actions in the preceding four-run comparison matched completion guidance.
That association does not establish that the guidance caused the narrowing.
Earlier final-state-only sampling still chose finish in both arms; it did not vary
the initial check recommendation or run the full reconsideration loop.

Task-first case planning, factor distinctions, change review and value-origin
instructions have already been investigated. Another case declaration is not the
selected next step. The bounded question is whether existing check/submit advice
influences the earlier selection of verification evidence.

## Change

The opt-in seeded diagnostic accepts `completion_guidance_policy="status-only-v1"`.
From the first input onward, `needs_visible_checks` and `ready_to_submit` keep their
status facts, set `next_action=null` and omit imperative check/submit recommendations.
The other guidance stages, common prompt, schemas, real admission rules, resource
accounting and evaluator path are unchanged. The journal binds the policy and
message hash to the external experiment. Supplemental reviews, paired observation
and operator feedback are excluded from the same branch.

The omission/default path remains unchanged. Common runtime content stays at
`4d2fc8ba` / surface v45; the new diagnostic source must be frozen separately for
any later comparison. See the [contract](../../.agent/completion-status-diagnostic.md).

## Local result and limits

- Focused tests: 16 passed in 44.69 seconds, including two scripted smoke runs.
- Append and segmented smoke paths both reached `EVALUATOR_PASS` after a public
  check failure, current-source read, repair and automatic recheck. Eight actual
  native inputs were inspected; plan content/identity survived normal delivery
  references and segment handoff metadata. Each run used four mock decisions,
  five tool actions and one new mutation. This is fixture acceptance, not model efficacy.
- Related regression: 98 passed in 650.46 seconds with per-test durations recorded.
  Documentation: 5 passed in 0.58 seconds. Ruff passed. Initial test failures remain
  recorded in the validation packet below.
- Prior packet/analysis bytes remained exact across 221 recorded files. No common
  runtime, private test, historical record or live run was changed.
- New provider/count calls and recorded cost: zero. Real Docker safety and live
  behavioral/acceptance effects: `NOT_RUN`.

Initial test failures exposed test assumptions: the ordinary CSV smoke checks do
not catch its original multiline defect, so the failure-path fixture now drops a
row that those checks cover. Input assertions also distinguish unchanged plan
content from existing native receipt references and handoff metadata. Those
corrections did not require changes to the common runner or diagnostic mechanism.

Detailed evidence: `C:\pt\validation\completion-status-20260926-v1\result.md`.

## Next question

A separately frozen comparison can now vary this advice from the first decision
while keeping tasks, candidates, model and ordinary settings fixed. Inspect whether
the agent selects inputs that distinguish required changes from preserved cases,
uses the observations to change its edit, and improves acceptance. More inspection
alone is insufficient. Other completion cues remain, so this does not isolate all
workflow framing. No paid group or default adoption is included in this result.
