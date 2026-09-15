# Brief planning: opt-in contract and comparison

## Hypothesis, not a conclusion

A short public plan may help the small model reuse its overall goal, remaining
work and verification intentions after observing results. Prior supplied-case
and advice experiments are closed and preserved. They did not establish that
missing internal planning caused the behavior; this is a new intervention.

## Runtime contract

`--planning-policy none|brief-v1|brief-evidence-v1|brief-assumption-v1` defaults OFF. All brief variants
support append-v1 and segmented-v1, not native-window-v1.
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

## Edit-assumption content contrast (2026-09-15)

`brief-assumption-v1` adds one short instruction block to the unchanged
`brief-evidence-v1` text. At the existing post-mutation review, connect one behavior
newly assumed, reimplemented or bypassed by the edit to a concrete public input/setup
and distinguishing observable outcome. State what already observed evidence exercises
that pair; otherwise retain it as untested. Connect it to the next useful allowed
action and reconsider it after results. A rejected proposal is not the current
rollback baseline. Do not invent a concern when none is material; null remains valid.

This changes plan content guidance only: no new fields, review event, extra call,
mandatory probe, concern quota, semantic judge, stronger mask or finish requirement.
The conditional guidance is present from the first system prompt; no additional
per-turn review message or timing intervention is introduced.
All old prompts, ordered tool schemas and planning identities stay exact. The new
instruction text binds through the existing v39 planning wrapper, model/envelope and
manifest identity. Both append and segmented paths use the existing storage/replay.
Old runs and closed experiment packets are never migrated or reused as new samples.

Reason for this contrast: the A1/A3 public audit found verification narrowing at
or shortly after the first edit despite preserved goals, plans, sources and available
tools. Their plans already had broad evidence-aware guidance. The new hypothesis is
that explicitly linking a change-specific assumption to a concrete observation is
more actionable than repeating an overall goal or check list. No historical
counterexample, task-specific input or repair is injected. This is not a diagnosed
transport fix, model-ability verdict or established performance improvement.
[Official guidance](https://developers.openai.com/api/docs/guides/optimizing-llm-accuracy#optimization)
supports clear instructions and systematic testing, not the effectiveness of this
particular intervention. Keep the prompt variant opt-in pending measured comparison.

The next comparison should use fresh runs, A=`brief-evidence-v1` and
B=`brief-assumption-v1`, otherwise identical task/model/context/probe options. Do not
change probe reuse, context, submission guidance or tool masks in that comparison.
Judge actual edits, useful distinguishing observations, repairs/rechecks and task
acceptance, not simply plan revisions or mentions of an assumption. This implementation
does not create a paid packet or reopen a closed budget. Freeze a new exact group and
its cost boundary before any dispatch, using the existing runner and zero-retry rules.

Provider-free validation records: `C:\pt\validation\assumption-planning-20260915`.
Tests use authored fixture plans to verify delivery and failure boundaries; they
cannot show that a real model chooses a useful assumption or tests it correctly.
Focused55 PASS/101.86s; full2306 PASS/8 skips in921.915s across109 files, fixed
runtime/test hashes, Ruff/diff PASS. OFF/baseline/new local smoke each reaches one
accepted edit, visible checks, finish and isolated smoke acceptance PASS/safety NOT_RUN
with4 turns/5 tools/2 segments; ON revision2 plans reach the final actual input.
The new instruction adds912 UTF-8 bytes. No API count/token/cost or real-model behavior
measurement; no provider/compact/Docker execution. Old planning identities and
199 recent/9658 historical protected file hashes match. Full-suite two-minute target
was not met. See result.md and verification.json in the receipt directory.

## Opt-in content contrast (2026-09-15)

`brief-evidence-v1` preserves all brief-v1 instructions and appends one format request:

- `Behavior`: observable behavior required by the public task, not a workflow list.
- `Evidence / open assumptions`: observed evidence versus untested assumptions;
  carry unresolved requirements forward when replacing the plan.
- `Next discriminating action`: the next useful allowed action and the observation
  that would change the edit/submission decision. No mandatory probe.

These are headings inside the existing string, not fields or a parsed section schema.
Missing sections remain valid text; no content validator, extra call or stronger mask.
Maximum length, review timing, null/parallel/replay behavior, native identity, notes,
gates and budgets are unchanged. The entire selected instruction text is hash-bound
in the planning contract. Existing none/brief-v1 tool hashes and schemas stay exact;
the new policy gets a distinct v39 wrapper, model/envelope and manifest identity.

Public B diagnosis found plans narrowing to visible checks despite delivered goals,
remaining tools and budget. Existing instructions already request evidence-aware
plans: this contrast tests salience/format, not a missing transport feature or a
proven causal repair. It contains no task-specific diagnostic case or code fix.
The [official prompt/evaluation guidance](https://developers.openai.com/api/docs/guides/model-optimization#write-effective-prompts)
supports explicit output goals and measured comparison, not an efficacy claim here.

This implementation is provider-free only. Tests verify preservation of authored
open statements, update/null/invalid/parallel behavior, actual next-input delivery,
segmented handoff, exact replay and unchanged action/evaluator boundaries. They do
not show that a real model authors useful plans, keeps all assumptions, or solves
more tasks. Frozen old comparators and results below are unchanged; they are not
executors or authorization for this new policy. A later fresh old/new-format
comparison must fix the same model/context and a new exact packet before dispatch.

Local receipts: `C:\pt\validation\evidence-planning-20260915\verification.json`.
Focused33 PASS/53.18s; full2228 PASS/8 skips/731.984s, Ruff/diff PASS. Local OFF/old/new
smoke each uses4 model/5 tool decisions, one accepted edit and two segments through
isolated smoke acceptance PASS/safety NOT_RUN; both ON revision2 plans are present
in the final actual input. No provider/count/compact/Docker dispatch. The new planning
instructions add904 UTF-8 bytes; no real token/efficacy measurement. Initial crash
fixture failures were corrected to match random-ID mutation events; no runtime
repair was needed for them. Full verification ran with fixed runtime/test hashes.

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
