# Revision pilot follow-up: budget pressure and avoidable work

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: validate
- Origin Date: 2026-10-26
- Verification Status: ANALYZED; saved public evidence; no reproducibility rerun
- Version Label: repair-revision-budget-behavior-v1

## Question and scope

The user asked whether the [closed revision pilot](2026-10-26-repair-revision-live.md)
needs a larger limit or more efficient behavior. The distinction matters because
the cap was nearly exhausted, while original-call repair and submission both failed.
This follow-up analyzes the existing public receipts and dispatched input metadata.
It adds no provider calls, target executions, runtime changes or new paid allocation.

The observed terminal pressure is real: total cost was $1.199996700 against $1.20,
and the last outputs reached their admitted 4,677/4,157-token ceilings without a
tool call. The hard model/action/edit/time limits were not reached: 37/40 model
calls, 39/100 actions, 2/4 edits and roughly 668/1,800 seconds. Neither path trace
hit a collection limit. Increasing those unused limits does not address the
observed terminal condition.

## Where the money went

All amounts below are settled costs of model responses, including their inputs
and outputs. They are not target CPU charges. The phase ranges partition all 37
model calls; the supplemental totals below overlap and must not be summed.

| Calls | Activity | Settled USD |
| --- | --- | ---: |
| 1 | Construct original reproduction | 0.137976000 |
| 2-12 | Inspection before path observation | 0.127871400 |
| 13 | Original-call path observation request | 0.024855000 |
| 14-29 | Inspection after complete observation | 0.420026100 |
| 30-31 | First source edit and diagnosis request | 0.042777750 |
| 32-33 | Incomplete response and correction | 0.138755250 |
| 34 | Second source edit | 0.170306250 |
| 35 | Public regression request | 0.041460000 |
| 36-37 | Incomplete finalization responses | 0.095968950 |
| Total | | 1.199996700 |

- First edit arrived on call 30, after **$0.710728500 / 59.2%** of the final spend.
- The 27 inspection responses cost **$0.547897500 / 45.7%**, with 936,678 input
  tokens including 419,840 cached tokens. Their requested tools comprised 19
  searches and 11 reads; some responses batched multiple actions.
- Calls 32, 36 and 37 emitted no tools and cost **$0.202655700 / 16.9%**. Their
  26,631 output tokens were all reasoning-token usage according to provider
  metadata. No private reasoning text was inspected.
- Calls 27-29 cost **$0.072110700 / 6.0%** and each added zero new covered source
  lines. Call 27 reread manager.py:101-127, already included in calls 6 and 15.
  Call 28 searched that file again for ast_from_file, and call 29 searched
  astroid/**/*.py for source=True and found no matches.

Zero new source coverage is an efficiency signal, not proof of zero semantic
information: rereads and negative searches can answer useful questions. The
explicit last-search question concerned the upstream source=True caller. Its
failure to find that caller should lead to a revised search scope or diagnostic
question, not an assumption that every inspection was unnecessary. A fixed ban
after two reads would not follow from this evidence.

The first probe and second source revision also consumed substantial reasoning
output (27,452 and 32,307 tokens respectively), but each produced a useful action.
They must not be grouped with the three responses that produced no tool call.
Lowering reasoning effort or output ceilings is an untested intervention and may
reduce useful repair work as well as cost.

## Context and completion admission

The last two input contexts contained 39,131 and 37,206 tokens even after the
visible regression passed. The final correction offered only finish_task/stop_task,
yet still carried seven source files, reproduction review, recent probes and notes.
Audit serialization sizes of three public state fields were approximately 28.4 KB
for current_sources, 19.9 KB for reproduction_review and 13.4 KB for recent_probes.
These field bytes are not model token counts or exact request wire sizes.

The current completion-recovery contract reserves 60,000 uncached input tokens
and only 128 output tokens for each ordinary successor, plus one separately
protected 25K correction. Thus it protects dispatch feasibility, not enough output
for a useful completion response. The protected correction was consumed at call
33, which returned the invalid directory-level test selection. The final correction
did not renew it. This explains why nominal 40K/25K ceilings did not mean that
40K/25K output remained available at the end.

Increasing the configured output ceiling while holding $1.20 fixed cannot remove
that monetary restriction. Increasing the monetary cap could buy additional
output or calls, but this run provides no counterfactual evidence that they would
repair the task. Saving the last three inspections is likewise not a measured
gain: a changed trajectory would have different contexts, actions and costs.

## Correctness remains a separate bottleneck

The second source edit used the prior refutation and entered its new branch, but
the original caller then raised FileNotFoundError. The host correctly refused
to treat empty F0010 output as a verified repair. However, the final public inputs
projected UNKNOWN and current_public_failure=null without the captured exception.
That concrete feedback omission survives any cap increase.

The model then requested the public regression, which passed 1,231 tests. It had
not been told the actual new target exception. More available output would not
by itself restore this missing fact or turn regression PASS into original-case
success. This is why the next change should preserve the captured outcome as
actionable current failure evidence, while keeping absent observation distinct.

## Recommended next decision

1. Preserve unexpected target exceptions in the compact current-failure view:
   call identity, exception type/message, capture completeness and current diff.
   Distinguish observed target failure from a call that was never observed. Offer
   a bounded repair/diagnostic response; do not relabel it as successful original
   verification or repeatedly rerun the same failed request without a new question.
2. Give finalization a smaller evidence-focused context and usable output funding.
   Keep current patch summary, check verdicts, original outcome and unresolved
   obligations; retrieve source detail only if needed for another repair. Minimize
   repeated representations instead of enlarging the context ceiling. Determine
   the concrete completion allowance against this compact request, rather than
   claiming the current 128-token admission floor is adequate.
3. Reuse observed source and connect further inspection to an unresolved decision.
   Treat the no-new-coverage signal as a prompt to reassess information value,
   with a finite targeted question when necessary. Expose valid test-file/node
   selections for paired tests so a directory-level request cannot consume the
   comparison opportunity without running a child.
4. Validate these mechanisms locally, then evaluate the real model under the
   same cap to distinguish efficiency from additional funding. A separate capped
   budget comparison becomes informative if correct failure feedback and compact
   completion are present and the remaining stop is still insufficient funding.
   No implementation or new experiment is authorized by this analysis alone.

These are priorities from observed failures, not an adoption or general-quality
claim. The single exposed-task run and changed historical caller conditions cannot
separate a stochastic trajectory effect from the intervention's causal benefit.

## Validation and evidence

All 11 statistical-fallacy categories were checked for applicability in the external
analysis. No population, significance, accuracy or causal effect estimate is made.
All 37 calls and all failed outcomes remain included. Post-hoc phase grouping,
selected-task scope, regression-to-mean risk in historical comparisons and untested
budget counterfactuals are explicit. No reproducibility rerun was performed.

- Source: C:/pt/repair-revision-live-v1/public-analysis.json,
  SHA-256 77146597ebcf147bd1f7ce339f01e59f109189edc434af87a2226c939430d4fd.
- Follow-up: C:/pt/repair-revision-live-v1/budget-behavior-analysis.json,
  SHA-256 aaeec822218b6b1ae9a0d57d73e8239033278cbd2365a82818c9f57a7dc3bdd5.
- The derived audit and its script are content-addressed and linked by an appended
  event in run_dev_repairrevisionliveoperator. Previous records were not rewritten.
