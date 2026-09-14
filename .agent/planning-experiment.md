# Brief planning: opt-in contract and comparison

## Hypothesis, not a conclusion

A short public plan may help the small model reuse its overall goal, remaining
work and verification intentions after observing results. Prior supplied-case
and advice experiments are closed and preserved. They did not establish that
missing internal planning caused the behavior; this is a new intervention.

## Runtime contract

`--planning-policy none|brief-v1` defaults OFF. Brief planning is append-v1 only.
Only ON adds nullable `plan_update` to existing `turn_decision` schemas and adds
brief instructions. There is no planning tool, separate response, API call or
planner model. OFF keeps the old system prompt, tool schema/order and absent
decision-field serialization. The planning contract binds its instruction hash
to model/envelope/tool identity and the evaluator manifest. No historical migration.

A nonempty plan up to 3,000 characters replaces the whole plan. It should state
the public task goal, remaining work/current hypotheses, verification and untested
assumptions, not raw reasoning. Content guidance now asks for concrete unfinished
work and the observation/check that could settle an assumption, not a generic
inspect/edit/check outline. After a review signal, describe what the observed result
confirmed, contradicted or left unresolved and the resulting remaining work and
verification. Do not keep a completed-action log or invent changes to raise revision
counts. This is task-independent guidance, not a required section schema or semantic
validator. Null keeps the existing plan when there is no useful revision. Identical text is
recorded as unchanged, not counted as a new substantive review. The first non-null
annotation in a parallel batch owns the update; further annotations or an invalid
first value receive a short diagnostic. The prior plan and valid tool action
survive invalid types, blanks and oversize text. No annotation error adds a
protocol correction or provider call.

`working_plan` projects text, revision, authoring turn/diff hash and review reasons.
Changed diff marks the plan historical without deleting or rewriting it. The
first valid decision after a mutation success/rejection, visible check/probe or
first transition to ready-to-submit receives a review request. Ordinary reads do
not demand rewriting; if no plan exists, the initial-plan request persists.
Null is allowed even when review is requested and is not proof of reconsideration.
Only a valid decision consumes an event-based request, never `turn_started` alone.
`working_plan_updated` records one idempotent receipt per valid turn before tools,
including null/unchanged/rejected outcomes. Recovery uses those durable records.

Native calls/results and encrypted reasoning remain in their existing order.
The native owner result carries the bounded annotation receipt; the latest plan
and review signal remain in the actual next model input. Planning stays separate
from working notes and verification concerns. The harness validates formatting,
not the truth of a model-authored interpretation. Planning never changes evidence,
source admission, check PASS, tool masks, costs, counters or finish eligibility.
Only public inputs are available; hidden/private/reference data never enters plans.

## Predeclared comparison

Every trial starts fresh from the same public task base, without prior-run notes,
encrypted state, patches, hints or supplied reproduction code. Model is
`gpt-5.4-mini-2026-03-17`, medium, output ceiling 25,000 with existing cost admission,
root `.env`, repeat=1, $1.20/run, 40 model/100 tool/4 accepted mutation/1800 seconds.
Both arms use append-v1, probes and repair-recheck. A is OFF; B is brief-v1.

| Stage | Fresh trials | Order |
| --- | --- | --- |
| Initial pyfakefs parent-traversal v2 | A4/B4 | A1/B1/B2/A2/B3/A3/A4/B4 |
| At most two justified planning revisions | A4/B4 each | Same eight-label order |
| Qualified loguru invalid-format v3 | A2/B2 | A1/B1/B2/A2 |
| Qualified hf-hub xet-endpoint v1 | A2/B2 | A1/B1/B2/A2 |

The authorized cycle cap is $40, maximum 32 trials with cap sum $38.40. No extra
approval is needed inside this exact scope, and no extra run exists to spend the
remainder. Each group freezes code/prompt/configuration. Subsequent planning
changes need public trace evidence and change only instructions, review timing,
or delivery/storage, one axis at a time. No stronger masks, forced probes, model
upgrade, context reorganization or planner call is part of this cycle.

A pyfakefs version qualifies for extension only if B has at least 2/4 acceptance
PASS, strictly exceeds A, and has no integrity defect. Freeze that runtime for
extension. Otherwise choose one evidence-supported revision or stop; never infer
improvement from a tie or exhaust remaining versions without a hypothesis.

## Evidence and cost

`diagnostics.planning_cycle` is a wrapper around the existing runner, not a new
engine. External cycle/group manifests fix task/runtime/config/source identities,
orders, hypotheses and prices. A run-lifetime OS lock prevents duplicate execution;
each independent sample has its own journal/workspace. Completed receipts are
checked and reused; pending runs use exact native recovery. A group starts only
with all invocation caps reserved; spend is restored from durable provider usage.
Normal task failure continues to the next fresh sample. Count/provider/cost,
execution integrity or cleanup uncertainty stops the entire cycle, with no
unknown dispatch retry or replacement sample. Already-prepared Docker/images only.

Report acceptance PASS/all trials, submission rate and cost, with non-submitted
evaluator results marked NOT_RUN. Isolated evaluation follows each submission;
hidden details are never sent back or used to author planning improvements.
Also report first accepted-edit call count, repeat/zero-coverage inspection,
uncertainty-targeted probes, post-failure edits/rechecks, plan creation/update
rates and verified actual delivery. Null/identical text do not establish review.
Token totals include planning overhead. Report actual model-rate and uncached
equivalent cost separately; cache differences alone are not efficiency gains.
No paid judge. Small dev-train observations are not generalization or official claims.

## Validation boundary

Focused tests cover OFF parity, nonblocking annotation variants, native delivery,
event requests, past-diff currency, terminal/gate independence and crash recovery.
Continuation/privacy regressions remain active. The wrapper covers group cap,
source drift, duplicate invocation, unknown outcomes and completed result reuse.
Mock A/B reaches edit, public check, plan refresh, finish and isolated evaluation.
Then run Ruff, the entire provider-free suite with external short temporary roots,
and mock smoke. Record actual timing rather than claiming the two-minute target
was met without measurement. Preserve credentials, user changes, task/history and
all existing external evidence. Every result remains `official=false`.

## First cycle outcome (2026-09-14)

The first eight attempted trials at `5bdb524a` produced OFF acceptance 1/4 vs ON
0/4, with 2/4 submitted in each arm and $4.064418300 durable model-rate cost.
All ON drafts were created/delivered, but only one of 30 post-initial valid review
decisions replaced its plan. This is not evidence of efficacy or of a causal
relationship between plan staleness and task failure.

B4's reasoning-only 25,000-token incomplete response returned a single encrypted
item of 1,717,452 characters. The next input count received HTTP 400
`string_above_max_length`; the native `COUNT_TIMEOUT_OR_UNKNOWN` terminal and
cycle stop were recorded. No retry, second version or extension ran. Preserve the
stop: leftover budget is not permission to reset continuation or bypass admission.
The cycle result and public-only review are at
`C:\pt\analyses\planning-cycle-20260914\result.md` and its `reviews` directory.

## Post-cycle content-guidance change (2026-09-14)

The read-only memory/plan audit verified all 191 actual dispatched request hashes.
B4's 20 normal tool decisions contained no memory update; its six post-result valid
review decisions made no plan replacement. Across all eight trials, the only note
creation was in A2's final finish response, too late for another model request.
No submitted annotation loss or missing review signal was found. B4 still made
public-error-driven repairs, so empty notes do not imply no evidence use, and stale
plans are not established as the cause of task failure. Audit/62-test receipts:
`C:\pt\analyses\planning-memory-audit-20260914`.

Only `working_plan.INSTRUCTIONS` changes in the runtime. Timing, null consumption,
storage, projection, schema/order, notes, tools and gates stay unchanged. The existing
instructions hash changes ON model/tool identity; no new policy name or historical
migration is introduced. OFF remains the default. This change is provider-free only,
not a second live comparison group or evidence of better planning/task performance.
The closed cycle and continuation-size stop remain in force.

The instruction-only choice follows [OpenAI's function guidance](https://developers.openai.com/api/docs/guides/function-calling#best-practices-for-defining-functions)
to state purpose and use conditions clearly. It does not import a task-specific
solution, add a planner call or establish that this prompt will improve mini's behavior.

Current validation: focused 54 passed/37.01s; full 2069 passed/8 skipped/708.903s;
Ruff and both OFF/ON mock smoke pass through isolated evaluation, provider cost zero.
The full-suite two-minute target was not met. Runtime AST/parity/identity and test
receipts are at `C:\pt\validation\planning-content-20260914`. No paid comparison ran.
