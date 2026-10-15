# isort I4: remove the current ready-state finish recommendation

Date: 2026-10-15. Design only, official=false, paid_authorized=false.
No provider, input-count, metadata, credential, Docker, target diagnostic,
registered-check, evaluator or mock-continuation execution. No connector or
default runtime change. The [I2/I3 audit](2026-10-15-isort-first-response-audit.md)
and [I3 result](2026-10-15-isort-retention-result.md) remain closed and unchanged.

## Limits and criteria fixed first

Run **I4 once**, only after implementation, free rehearsal and later approval of
an exact executable manifest. Use the existing I3 as the primary historical
comparison; I2 is a reference for first-response variation, not another control
to execute. Restore the original pre-339 checkpoint through event 338, as in I3.
Do not continue from I3's submitted result or splice in I2's revised plan.

| Resource | Frozen new-invocation maximum |
| --- | --- |
| Task / row / repetitions | `original-isort-2491`, `dev-train` / I4 / 1 |
| Model | `gpt-5.4-2026-03-05`, xhigh, default tier |
| Provider allowance | **USD 3.50 total**; no transfer from closed runs |
| Generation / input-count requests | **6 / 6**, including discarded counts |
| Tokens per request | At most 60,000 input; fixed 25,000 output including reasoning |
| Solver actions / accepted source edits | **18 / 2**, unchanged mutation scope |
| Parallel inspections | At most 4 reads/searches per response; each counts |
| Solver time | **281 s**, including preparation, bounded by inherited remaining time |
| Terminal public oracle | Same four-case program, once, at most 30 s |
| Isolated evaluation | Existing registered evaluator, once, at most 330 s |
| Entire invocation | **720 s**, including preparation, public review and assessments |
| Exact-model metadata reads | At most 1 |
| SDK retries / protocol corrections / paid compactions / paid judges | 0 / 0 / 0 / 0 |
| Seed diagnostic reexecution / additional samples / new control rows | 0 / 0 / 0 |
| Credential file | Existing repository `.env`; not read during design |

These numerical and operation-specific limits are copied from the frozen
[I3 design](2026-10-15-isort-retention-design.md). At the unchanged registered
planning rates of USD 2.50/0.25/15 per million input/cached-input/output tokens,
the uncached maximum reservation is USD 0.525 per request and USD 3.150 for six.
These are planning rates, not a fresh official price check or a predicted bill.
Verify official prices and exact model access before any later approved dispatch;
an incompatible price/environment stops readiness rather than changing the design.

Count six may fund its matching generation. Settle already dispatched usage;
returned actions still need time/action admission. Edit two prohibits edit three,
not remaining affordable checks or finish. An automatic required-check recheck
costs one action and no generation. Spare money/calls do not extend time.

| Axis | Predeclared criterion |
| --- | --- |
| A: advice-removal exposure | First actual dispatch contains exactly the specified two-field removal; every later latest state obeys the same stage-specific policy. Count/dispatch hashes and non-treatment parity must agree. |
| D: diagnostic delivery | The complete unchanged packet and seed reach the first dispatched input. Only the advice fields and the existing displayed-time normalization differ from I3. |
| First response | Classify immediate unchanged submission, continued public action, stop without submission, or unobservable/censored action. Record the public decision and executed tool batch. This is a process measure, not repair success. |
| U: uptake | Same semantic rubric: public evidence before/in a new accepted edit links a specific observation to rejecting or materially qualifying keyword-only placement; the edit implements that distinction. |
| P: public final repair | Actual submission has a new allowed source change, fresh unchanged regression PASS on its exact final diff, and all four frozen position/text/count/AST controls pass, including exact original issue output. |
| I: isolated acceptance | The one existing isolated assessment of the submitted artifact returns `EVALUATOR_PASS`. |
| Safety / integrity | Safety PASS, intact source/input/cost/public-private boundaries. |

**Primary local success requires A/D/U/P/I and safety PASS.** Delaying finish,
reading, revising a plan or choosing a probe is insufficient. Conditional
qualification counts for U; simple reversion and any specific wording/file are
not required. A correct patch without observable evidence-to-revision-to-action
linkage is U NOT_OBSERVABLE. Explicitly retaining the contradicted premise or
submitting the unchanged seed as sufficient is U FAIL. Silence or cutoff alone
is not U FAIL. No check or acceptance criterion is weakened.

Preserve **C and R definitions** from I3, and report the old
`D/C/R/U/P/I/safety` conjunction separately. C measures qualifying post-first-input
handoff exposure before a new edit; no such exposure is NOT_EXERCISED. R requires
zero pre-edit same-case ownership probe actions plus a new accepted edit; zero
probes without an edit is NOT_OBSERVABLE. Configuration changes do not exempt a
same-case action; strict identical replay remains a separate count. I2 had one
same-case action and zero strict replays; I3 had zero probes and zero new edits.

C/R are secondary to this new advice question, not extra primary gates. An
immediate correct edit can meet the new primary target without exercising C.
No handoff or probe is forced to obtain a grade. This prospective distinction
does not change I3's frozen target or retroactively upgrade its result.

**Seal A, D, first-response classification and U/C/R with public event citations
before both terminal assessments**, within 720 s, with no paid judge. Preserve
NOT_RUN and raw evidence under transport/billing uncertainty; do not manufacture
a retrospective seal. Only actual submission permits the terminal public oracle
and then isolated evaluation. An ordinary public behavior FAIL may still receive
the one isolated assessment; infrastructure uncertainty stops it. Results never
return to the solver.

## Why this question, and the single treatment

I3 immediately submitted the inherited keyword-based patch, citing the two
confirming cases without addressing the crossed item-type regression. I2 rejected
that hypothesis under the same first input except two displayed seconds. Shared
plan/advice influence is plausible, but this pair does not isolate it. The current
user request authorizes one subtractive design tied to actual final repair; it
does not establish a runtime defect or authorize another paid run.

Remove the finish recommendation **only inside `completion_guidance` in the
newest `harness_current_state`, whenever `stage=ready_to_submit`**, before the
exact request is counted/dispatched. Apply this on the first and subsequent
eligible inputs. The machine suggestion and its prose are one treatment:

1. Change `next_action: {"tool":"finish_task"}` to `next_action: null`.
2. Delete only the conditional finish clause from its message, closing the
   preceding sentence with a period.

Exact first-input message before:

```text
All required visible checks pass on the current diff; submission is eligible, not proof of untested behavior. Use run_probe if a concrete remaining public uncertainty could change the edit; otherwise use finish_task to submit. No extra experiment is required.
```

Exact first-input message after:

```text
All required visible checks pass on the current diff; submission is eligible, not proof of untested behavior. Use run_probe if a concrete remaining public uncertainty could change the edit. No extra experiment is required.
```

If a later ready state has the existing no-probe message, replace only
`Use finish_task to submit; keep any remaining uncertainty explicit.` with
`Keep any remaining uncertainty explicit.` The same `next_action: null` applies.
Keep existing suffixes byte-for-byte, including time-reserve information naming
`finish_task`; this is not a global word deletion. Require the original next
action and one exact supported message prefix. Unknown forms stop before count
or dispatch, without a heuristic rewrite.

Keep `stage`, `submission_ready=true`, `diff_hash`, workflow eligibility and all
tools, including `finish_task`. All non-ready stages and their repair/check/source
advice remain identical. Preserve the initial plan and ordinary later plan
updates, system-level completion language, user task, native/opaque/call/output
items and historical states. Do not insert a replacement next-action suggestion,
review paragraph, mandatory probe/edit, extra turn or new finish gate. Initial
mutation scope remains four changed files / 1,000 full-diff lines, with the same
observed-anchor rules; no source location or repair hint is added.

Keep the **entire existing diagnostic and I3 retention**: same seed means the
current operator field with complete raw input, setup, results and table; after
an edit it becomes the historical field with the complete observed seed patch,
while ordinary `current_diff` stays current. Returning to the exact seed restores
the current form. No new diagnostic, pruning, summary or segmentation policy.
The retained packet stays separate from registered failures and finish eligibility.
The bound I3 retention policy is reused; only its old advice-unchanged/first-input
equality clauses are superseded by this explicitly scoped treatment.

## Comparison and interpretation

For the first input, undoing the two fields and normalizing only displayed
`active_wall_time_seconds` must recover the complete I3 first preview. Preserve
real clocks and report their actual values; no artificial 267-second display.
Later inputs compare with their own ordinary I3-retention assembly before this
treatment. Undoing the two fields must recover that assembly exactly. Later
model-authored plans/actions may differ; do not splice historical responses to
make trajectories match. Bind exact assembled, counted and dispatched hashes.

Compare I4 with I3's immediate `finish_task`, zero new edits and U/P/I FAIL.
I3 C remains NOT_EXERCISED and R NOT_OBSERVABLE. I2 is an additional reference for
recognition followed by exploration/recheck, not a matched later-trajectory
control; its uncertainty-censored formal U remains NOT_RUN. Neither old run is
resumed, retried, regraded or assigned unused new allowance.

Record evidence selected in the first public decision, first executed batch,
first accepted edit and final diff. Separate count, provider wait, preparation
and tool intervals; do not label these internal reasoning time. Report all
pre-edit probe inputs/configurations/reasons, new-call costs and censoring,
registered checks, submission, terminal public cases, acceptance and safety.

Plausible alternatives remain: the old plan/native hypothesis or task reading
may dominate; unchanged system/eligibility cues may make this advice redundant;
response/backend variation or timing may change selection; or the model may
reopen the repair but still fail to implement it within the budget.

- Another immediate unchanged submission shows this deletion was insufficient
  in this sample; it does not prove zero influence in all runs.
- Recognition or exploration without accepted final repair does not justify
  adoption. It may locate a later bottleneck, without authorizing another run.
- A complete chain shows one successful repair under this variant. With one
  new sample and a historical comparator, it cannot establish a causal effect,
  reliability rate or general gain. Machine recommendation and prose effects
  are also not separately identified.
- Missing exposure/integrity or censored execution is reported separately from
  behavioral failure. Do not replace that row with another sample.

Keep the default baseline and close the one row regardless of result. No prompt
tuning, additional sample or automatic follow-up/adoption follows success either.

## Stops and readiness still required

Stop before dispatch on source/receipt/currency/diagnostic/parity uncertainty,
unknown advice form, unavailable exact model/environment, or failed exact count
and full fixed-output reservation. Input overflow above 60,000 stops without
trimming, a new handoff or shrinking output. Preserve operation-specific ceilings
and inherited time. Finish, stop or deadline closes solver work; malformed or
incomplete responses get zero correction calls. Count, transport, usage/billing,
continuation, private-boundary, infrastructure or cleanup uncertainty stops the
invocation with no retrieval/retry/resume. No automatic Docker start, image pull
or build. Do not change wording, cases, expectations, plan, model, seed, limits
or criteria after seeing an outcome.

Implementation and free rehearsal remain **NOT_RUN**. A later narrow I4 adapter
must preserve I3/default implementations and verify first/later two-field parity,
non-ready identity, suffix/native/plan/tool preservation, observation currency,
edit/recheck/finish, unchanged-finish grading, count binding and every existing
cap/uncertainty stop. Check pre-assessment A/D/first-response/U/C/R sealing and
private isolation. Then bind the exact committed implementation, this design,
mock evidence, task/model/credential/repeat/caps to a fresh executable manifest.
This design packet is not executable and grants no paid authorization.

## Frozen evidence and local validation

Design head: `e8dff93887e4b179fda9c5e3c46651f4677315af`.
Runtime remains
`sha256:b3c8e80c0656fb4954eebcb5d30de411d4b0fa687a150ef3308883487bb08208`.
The original seed diff remains
`sha256:6edb32a68f8fea1002de9fa6836b1e583de021a53c176b94653dc894567e2940`.

External root: `C:/pt/isortfinishplan01`. Its append-only hash-chained
`runs/run_dev_isortfinishplan.jsonl` records limits/criteria first, before
treatment-preview construction. `limits-and-criteria.json` hash:
`sha256:9231ee74723275ae8b2ec4c601fbf482d46b6703f94ea510e453e3aa5c00c82a`.
`design-packet.json` hash:
`sha256:9bab428334bcbec950e1013f754950f5ea1b01f92c3aa174d1660e42175f8250`.

Saved-data construction validates the I2/I3 row chains, original nested bindings,
unchanged limits and exact two-field first-input difference. Undo recovers the
full original request, including native/system/tool/plan/diagnostic bytes. Four
static message fixtures cover both ready branches, suffix preservation and a
non-ready identity case. This is a request preview, not an input count, actual
exposure, mock continuation or model-performance result. The user's existing
AGENTS.md change is preserved. Five documentation layout/link tests passed in
0.13 s; the new record's three relative links and `git diff --check` passed.
Eighteen direct immutable file bindings plus nested I3 bindings were verified.
Runtime tests, mock smoke, free continuation and all live work remain NOT_RUN.
