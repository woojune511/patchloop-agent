# Completion guidance with identical public observations: preparation

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent.
- Origin Mode: bounded code-experiment preparation.
- Origin Date: 2026-10-29.
- Verification Status: preparation in progress; live repair benefit NOT_RUN.
- Version Label: completion_guidance_v1; official=false, claim-ineligible.

## Question and reason

In the [replay-feedback comparison](2026-10-29-astroid-replay-feedback-results.md),
B received its model-authored helper's current-candidate output, acknowledged the
unchanged behavior and submitted without further investigation. Tools and budget
remained. This rules against lost feedback or immediate resource exhaustion as
explanations for that choice, but does not establish its internal cause.

Test whether generic guidance separating submission eligibility from the need for
further diagnosis changes the next action and eventual repair on this checkpoint.
An alternative is that the raw helper evidence is insufficient or that repair
reasoning still fails even after useful investigation. No additional state machine,
tool restriction, automatic replay, private hint or finish gate is proposed.

## Paired conditions

Restore the original pilot at cut 214, through sequence 213, before the next model
response. Both new arms receive the identical sealed helper receipt previously used
in B; both are charged its one action and 11.198 seconds. Do not reuse the previous
B response as the control and do not rerun the helper during preparation.

- A: existing completion guidance.
- B: insert this paragraph before the existing finish-task paragraph:

> Submission eligibility alone does not settle whether further repair is warranted.
> When current public observations conflict with requested behavior, prefer a small
> check of the relevant caller, input, or setup before finishing. Missing changed-line
> coverage limits what that measurement establishes; examine how the conflicting
> behavior arises before deciding whether the candidate is adequate.

The paragraph does not identify Astroid, the absent initializer, a faulty function,
or a reference repair. It does not declare the helper equivalent to the original
CLI reproduction. Normal context, source/tool availability, acceptance grading and
public-check submission eligibility stay fixed. Both arms start with six responses
(at most one correction), 14 actions and two edits remaining, about 1,648 solver
seconds plus the 390-second isolated-evaluation reserve, input60K/output40K/25K,
gpt-5.4-2026-03-05/xhigh, public-checks-v1/thin/segmented-v1 and the same caller scope.

The proposed fresh cap is USD3.397541 per arm, USD6.795082 total, one run each,
without transfer. Credential path is `C:/Users/geonj/Documents/PatchLoop/.env`.
The previous allocation is closed; this record does not authorize new paid calls.

## Implementation and verification boundary

The intervention lives in diagnostics; the ordinary runtime/default prompt remains
unchanged pending evidence. The inherited first completion segment is already
prepared. Replacing a module constant alone would leave its saved system prompt
unchanged; rewriting the finished request would break native seed validation.
Instead append a replacement of the uncommitted pending segment before attaching
the host observation, preserving public state and native history. Use the same
prompt variant on subsequent completion-stage entries within that branch.

Local checks must establish actual first-input prompt delivery, unchanged tools,
public state, receipts and allowances, valid native seed binding, and continued
count-to-dispatch equality. A's normalized request must equal the previous sealed
replay condition; A and B must differ only in the selected system text, excluding
elapsed time and derived segment identity. Reuse the existing cost/admission,
hash-chained journals, action identities and no-retry collector.

## Outcomes and limits

Primary repair outcome: original SWE-bench acceptance, with public behavior,
regressions, delivery, cost and time reported separately. Mechanism support requires
a relevant discriminating check or repair and a subsequent evidence-based decision;
more actions alone do not establish improvement. B-only PASS would support this
checkpoint, not default adoption or generalization. Useful investigation followed
by FAIL is a behavior effect without demonstrated repair gain. Unchanged submission,
irrelevant work, new regressions or exhaustion without resolution are negative
outcomes. Both improving gives no differential advantage.

The checkpoint was selected after failures, the task is exposed, and each arm has
one stochastic response trajectory. The helper does not itself execute the original
CLI/F0010 reproduction. Prompt length and resulting token cost necessarily differ.
Stop all remaining rows on count, transport, billing, execution or cleanup uncertainty;
zero SDK retries, no automatic resume, no evaluator feedback to the repair model.

No new provider call, target execution or private evaluation is part of preparation.
Sealed commands and local receipts will be recorded when validation completes.
