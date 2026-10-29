# Finish choice and edit allowance: public local audit

Date: 2026-10-29. Parent runtime change: `bb042dd6`. Local read-only audit and
focused tests; no model calls, Docker execution, private evaluator inspection or
quality claim. Original runs, grades, journals and requests are unchanged.

## Question and selection

The user requested the next work after contract/budget normalization: understand
why a known public failure can still end in submission, and check whether the
action forecast and larger edit allowance address the actual obstruction. This
matters because increasing an unrelated budget cannot fix a wrong decision, and
a new finish gate could obscure rather than explain the problem.

Selected three decision boundaries from the closed
[completion-guidance pair](2026-10-29-completion-guidance-results.md), plus the
public terminal record of the only edit-quota-exhausted dev20 row. These isolate
two different mechanisms without a new repair run. This selection is diagnostic,
not a representative task sample.

Inputs are the public prepared request, counted/dispatched request identities,
public actions and their actually delivered observations. The audit does not load
private specs, hidden tests, reference patches or evaluator artifacts. Journal
hash validation traverses the chain but exports only selected public fields.
It exports hashes/lengths and delivery facts, never source/probe bodies, model
reasoning or evaluator payloads. Execution success is not classified as success
of the behavior being investigated.

## Observed facts and exclusions

All turn numbers below are `turn_started` journal sequences; decision sequences
are listed separately. This avoids confusing count/dispatch/action events.

| Boundary | Actual choice | Remaining calls / correction / actions / edits | Observation |
|---|---|---|---|
| A turn 247, decision 250 | `finish_task` | 5 / 1 / 13 / 2 | Caller probe 239's exact stdout delivered in current state; edit offered. |
| B turn 261, decision 265 | `run_probe` | 4 / 1 / 12 / 2 | Exact 2,681-character source span from action 255 present in native input; edit offered. |
| B turn 277, decision 281 | `stop_task` | 3 / 1 / 11 / 2 | Probe 271's exact stdout and the same source span delivered; edit absent. |
| Dev20 row 9 terminal 195 | host `LIMIT_REACHED` | 7 / 1 / 19 / 0 | Three accepted edits used; `accepted_mutations` is the recorded blocker after a public check failed. |

A's public assessment acknowledges that the original F0010 remains, while the
required public check passes on the current candidate. Four ordinary responses
remain against the three-response successful edit/check/finish route. The input
offers `replace_text`, reads/searches and probes. Missing delivery, exhausted
edit allowance, missing edit tools and immediate response exhaustion are therefore
contradicted as explanations for this decision. Its internal cause is unknown.
There is still no demonstrated correct alternative patch at that exact decision;
available resources do not prove such a patch was within reach.

B is different: before its probe, four total responses minus one correction
reservation leave three ordinary responses. The probe spends one, leaving two.
The next edit/check/finish route needs three. Increasing accepted edits cannot
recover that spent response. The public stop assessment accurately identifies
the absent edit action; its stronger claim about which file pylint processed is
not established by this resource/delivery audit.

The host behavior is intentional under `public-checks-v1`: scoped nonempty diff
plus required same-diff public checks permits candidate submission. Diagnostic
original-failure observations remain advisory; `unverified_delivery` and a candid
assessment do not certify task repair. Current `completion_context.SYSTEM_PROMPT`
already states that required-check PASS is not original repair and that unknown
or known failure cannot become verification through submission. The A decision
is a behavioral repair/abandonment question, not a newly established bypass of
the execution contract. No blanket reproduction gate or prompt is added here.

## Executed local comparison

The new `diagnostics/finish_choice_audit.py` verifies prepared-input bytes and
count/dispatch identity, then checks exact evidence delivery across current state
and native/public archive channels. It compares accepted-edit caps **3, 4, 12**
while holding remaining model calls, correction reservation and tool actions fixed.
The route is explicitly current-source anchor + successful edit + one required
check + finish, with no automatic recheck or original replay. It must match the
recorded mutation minimum; incompatible route assumptions are rejected.

| State | Cap 3 | Cap 4 | Cap 12 |
|---|---|---|---|
| A before finish | immediate minimum fits | fits | fits |
| B before probe | immediate minimum fits; after probe calls short | same | same |
| B after probe | calls short | calls short | calls short |
| Row 9 after failed check | edit quota short | minimum slots fit | minimum slots fit |

Consequences: the new forecast can expose B's loss **before** the probe, whereas
its saved request lacked `action_budget`. Merely displaying that consequence is
not proof that a model chooses differently. Row 9 supports removing the three-edit
bottleneck; **four edits already remove that particular minimum-slot obstruction**.
This record gives no evidence that twelve is optimal or better than four.
No row demonstrates improved task correctness, regression behavior, cost or total
time. Slot fit also does not promise scope/source admission or future cost/time
availability, and failure recovery can need additional work.

Evidence is in `C:/pt/finish-choice-local-audit-v2/runs/run_dev_finishchoiceaudit.jsonl`
with four append-only, hash-chained audit events and content-addressed reports.
Sources: `C:/pt/completion-guidance-run-v1/{A,B}/runs/run_dev_aecd56b8decc47ff.jsonl`
and `C:/pt/repair-dev20-run-v2/9/runs/run_dev_52aadb8135574bec.jsonl`.
An earlier v1 audit omitted source-span body checks; v2 adds those checks without
rewriting v1 or the source runs.

Example read-only reproduction:

```powershell
.venv/Scripts/python.exe -m diagnostics.finish_choice_audit `
  C:/pt/completion-guidance-run-v1/B run_dev_aecd56b8decc47ff 277 `
  --evidence-action-id call_A4HPLLkPhuIuty9GpLv6LXkG `
  --evidence-action-id call_dRkHflUkWsXTMb7Pf4A6mxFP
```

Focused tests: **7 passed in 1.02 seconds**, Ruff passed. Tests distinguish an
earlier receipt from delivered bodies, reject artifact tampering and a mismatched
minimum-route assumption, protect the public-only output boundary, and exercise
both call exhaustion and accepted-edit exhaustion. No production decision rule
was modified.

## Decision and next experiment boundary

Keep the exact action forecast and larger configurable edit allowance as engineering
capabilities. Do not explain every unchanged submission as quota/cost exhaustion;
do not adopt another global completion gate from this pair. A's next useful question
is whether public source can support a concrete repair alternative and what
discriminating check would accept or refute it. If that cannot be established,
another guidance A/B on the same checkpoint lacks a clear intervention target.

The local comparison is ready and executed. A later model-behavior comparison
should separate two questions rather than change both dimensions together:

1. Forecast effect: freeze a new current-runtime public checkpoint and all tool,
   source, budget, prompt and observation conditions; vary only delivery of the
   action-specific forecast. Select a decision with one optional action capable of
   spending the final repair route. Measure chosen action, actual repair, required
   regressions, isolated acceptance, time and cost. A different choice or successful
   submission alone is insufficient.
2. Quota effect: select public development tasks that actually exhaust accepted
   edits; compare 4 versus 12 under the same model, response/action/time/cost limits
   and tool capabilities. Keep the original 3-edit run as historical evidence,
   not an interchangeable baseline. Stop if no selected task binds on edit quota;
   that would make more quota an untested explanation rather than an intervention.

Neither experiment has a new paid allocation. Exact current commit/configuration,
task, model, credential file, repeats, positive invocation cap and stop conditions
must be specified before dispatch; previous unused budget does not carry forward.
