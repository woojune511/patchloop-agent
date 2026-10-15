# isort I3: preserve executed observations across contexts

Date: 2026-10-15. Design only, official=false, paid_authorized=false.
No provider, input-count, metadata, credential, Docker, target diagnostic,
registered-check, evaluator or mock-continuation execution. Runtime and the
I1/I2 executors remain unchanged. This separately requested design follows the
[I2 input audit](2026-10-15-isort-table-input-audit.md); the
[I2 result](2026-10-15-isort-table-result.md) and its grades remain closed.

## Limits and criteria fixed first

Run **I3 once**, only after later implementation, free rehearsal and exact-manifest
approval. Compare with the existing I2; do not rerun I2 or add a control. Restore
the original pre-339 checkpoint used by I2, not I2's revised second-turn plan.
The numerical limits and operation-specific cap rules are copied unchanged.

| Resource | Frozen new-invocation maximum |
| --- | --- |
| Task / row / repetitions | `original-isort-2491`, `dev-train` / I3 / 1 |
| Model | `gpt-5.4-2026-03-05`, xhigh, default tier |
| Provider allowance | **USD 3.50 total**, separate from closed I2 spending |
| Generation / input-count requests | **6 / 6**, including discarded counts |
| Tokens per request | At most 60,000 input; fixed 25,000 output including reasoning |
| Solver actions / accepted source edits | **18 / 2**; same mutation scope |
| Parallel inspections | At most 4 reads/searches per response; each counts |
| Solver time | **281 s**, including preparation and bounded by inherited time |
| Terminal public oracle | Unchanged four-case program, once, at most 30 s |
| Isolated evaluation | Existing registered evaluator, once, at most 330 s |
| Entire invocation | **720 s**, including preparation, public review and assessments |
| Exact-model metadata reads | At most 1 |
| Retries / correction calls / paid compactions / paid judges | 0 / 0 / 0 / 0 |
| Seed diagnostic reexecution / additional samples | 0 / 0 |
| Credential file | Existing repository `.env`; not read during design |

Using the unchanged registered planning rates, reserve at most USD 0.525 per
60,000-input/25,000-output request and USD 3.150 for six. This is neither fresh
official pricing verification nor an expected bill. Fresh official prices and
exact model access must be checked before any separately approved dispatch.
Each generation needs a fresh successful single-use count of its exact final
request, including retained data, and the full fixed-output reservation.

Count six may fund generation six. Settle already dispatched usage; returned
actions still require time/action admission. Edit two forbids edit three, not
remaining affordable checks or finish. Automatic repair recheck costs one action
and no generation. Unused calls or money do not extend the solver deadline.

| Axis | Predeclared criterion |
| --- | --- |
| D: initial delivery | Same complete I2 packet reaches the first dispatched request on the bound seed, with first-input parity. |
| C: continuity exposure | Before the first new accepted edit, an actually dispatched input after a new segment boundary contains the exact packet and observed diff on the unchanged seed. Every later request follows the current/historical rule below. |
| R: recheck reduction plus action | **Zero** pre-edit same-case ownership probe actions, versus I2's one, **and at least one new accepted allowed non-noop source edit** relative to the seed within the same limits. |
| U: uptake | Unchanged semantic rubric: public evidence before/in an accepted edit connects a specific observation to rejection or material qualification of keyword-only placement, and that edit implements the distinction. |
| P: public final repair | Actual submission has a new source change, fresh unchanged regression PASS on its exact final diff, and all four frozen position/text/count/AST controls pass, including exact original issue output. |
| I: isolated acceptance | One existing isolated assessment of that submitted artifact returns `EVALUATOR_PASS`. |
| Safety / integrity | Safety PASS; source, input, cost and public/private boundaries remain intact. |

The local experimental target requires **D/C/R/U/P/I and safety PASS**. U remains
the original rubric: conditional qualification counts; no specific phrase,
file, parser category, note field or simple reversion is required. Recognition
or a revised plan without an accepted edit is insufficient. A correct patch
without observable evidence-to-revision-to-action linkage is U NOT_OBSERVABLE.
Explicit retention of the contradicted premise or submission of the unchanged
seed as sufficient is U FAIL. Silence, reads or cutoff alone are not U FAIL.

If editing or termination occurs before a qualifying later handoff exposure,
C is **NOT_EXERCISED**, even if the final repair succeeds. Missing dispatch
evidence is NOT_ASSESSABLE; wrong/missing/stale-as-current data stops dispatch as
an integrity failure. No new handoff is forced to make C observable.

**Seal U, C and R with public event citations before both terminal assessments**,
inside the existing 720 s. They are operator assessment fields, not new solver
gates or instructions. Preserve the existing uncertainty stop: do not manufacture
a retrospective seal after transport/billing uncertainty. Record raw actions and
NOT_RUN as applicable. Only actual submission permits the terminal public oracle
and then isolated evaluation. Normal public behavior failure may still receive
that one isolated assessment; infrastructure uncertainty stops it. Results never
return to the solver.

## What counts as a repeated check

Count one model-authored probe action when, **before the first accepted new
edit and on the seed diff**, it runs at least one byte-identical frozen case
input through the unchanged candidate and inspects/asserts its comment position
or exact output. Count an action once even if it contains multiple cases or mixes
old and new cases. Configuration changes and stated intent do not exempt it from
this descriptive metric; tag their new coverage and rationale separately.

I2 has **one** such action. It has **zero strict identical replays**, because
its new probe changed configuration. Report that stricter count separately;
do not call I2's probe an identical replay or claim a reduction from zero.
A reasonable new-configuration check can therefore fail this narrow R target
without being declared an engineering error. This is not a tool restriction.

Exclude post-edit verification, registered regression/automatic recheck, terminal
assessment, source reads, setup-only checks and probes of different inputs or
helper behavior. No exception is invented after seeing an outcome. One or more
counted actions means R FAIL. Zero without an accepted edit, or insufficient
public evidence to classify the action, is R NOT_OBSERVABLE. A timeout or immediate
finish cannot earn improvement merely by doing fewer checks. Keep raw counts,
configuration differences, probe intent and censoring visible.

Also record the first edit's generation ordinal, elapsed solver time and elapsed
time after retained handoff exposure; preceding reads/searches/probes; and provider
wait, count, preparation and action intervals separately. I2 had no edit, so there
is no observed I2 time-to-edit to subtract. Its roughly 88 s search-to-probe window
is not a guaranteed saving. Provider waits are not isolated internal reasoning time.

## Question and alternatives

At I2 event 352 the model rejected the text-only rule. After the handoff, input
363 retained that revised plan but lost the diagnostic inputs, settings, table,
raw results and provenance. Response 369 reopened item placement as untested;
the next response returned to the earlier helper investigation. No edit occurred
before the fixed deadline. This concrete evidence-delivery gap motivates I3.

The hypothesis is that preserving the executed observation can prevent that
return to an answered behavior question, leaving enough opportunity for an
evidence-linked repair. The revised plan already carried the contradiction, so
data loss may not be decisive. New configuration coverage, source understanding,
implementation difficulty and provider latency remain plausible explanations.
Faithful retained exposure followed by another such probe weakens the proposed
mechanism. No probe but no edit shows that removal of this step was insufficient.
An accepted revision with a bad final patch separates continuity from correctness.

## Exact data-only intervention

Preserve the existing **25,211-byte I2 packet in full**, including its four-case
table, exact case inputs, `Config(profile="black")` program and setup checks,
both complete base/seed receipts, stdout/stderr, parser/position/text/AST results,
expectation provenance, execution flags and snapshot/diff hashes. Do not create
a summary or infer new facts. Derived controls remain derived public controls.

The existing packet already says observations apply only to their recorded
diff. Freeze the full public seed `current_diff`, including its patch bytes, from
the saved first input. Its patch hashes to the same seed identity as the receipt.
The delivery rule is:

1. **First request:** exactly I2's packet and ordinary state, without new wrapping
   or wording. Only the existing displayed-time parity normalization is allowed.
2. **Later request, same seed diff:** insert that exact packet under the existing
   `state.operator_public_observation`. The ordinary `state.current_diff` already
   contains the full observed patch; require its hash and bytes to match. Repeat
   this data delivery after handoffs and within a segment, without a new turn.
3. **Later request, different diff:** omit the current operator field. Insert
   `state.historical_operator_public_observation` containing exactly
   `{observed_candidate_diff: <frozen seed current_diff>, observation: <original packet>}`.
   Keep the ordinary current diff unchanged. The nested packet's `current` and
   `submitted` labels refer to the original recording; each receipt applies only
   to its own hash and cannot verify the new repair. An exact return to the seed
   restores the same-diff form, with package/configuration bindings still checked.

There is one bounded operator packet in the latest current-state view, not a
growing observations list. Existing handling of older native/historical items
remains unchanged; do not rewrite encrypted reasoning, calls or returned outputs.
The data is separately labelled operator evidence, not model-authored memory,
a registered observation, failed regression, concern or mandatory completion gate.
Do not add a repair hint, source location, no-retest instruction, forced edit,
plan rewrite, extra context request, paid summary or cross-run memory.

## Unchanged conditions and parity

Restore `C:/pt/runs/fixed-batch-20261001-v1/original-isort-2491`,
`run_dev_49397fa9568d4b80`, through event **338**, before request **339**.
Seed diff: `sha256:6edb32a68f8fea1002de9fa6836b1e583de021a53c176b94653dc894567e2940`.
Keep the original 20 model calls, 38 actions, two accepted edits and 1,518.331 s
already spent. Total ceilings stay 26 model calls, 56 actions and four accepted
edits; the originally remaining 281.669 s is still rounded down to 281 s.
I2's new responses, revised plans, probes, billing uncertainty and final results
are operator-only comparison evidence; none becomes inherited solver context.

Keep initial plan, review request, notes, completion advice, system/user/task
text, tool definitions, source/read ownership, mutation scope, workflow gates,
repair recheck, source retention, segment boundaries, output settings, U/P/I
rubric and terminal programs unchanged. The model can subsequently update its
own plan, notes and source. Ordinary handoff still regenerates the current system
text as it did in I2; do not silently harmonize the historical first prompt.

Future first-wire reconstruction must match the existing I2 preview, normalizing
only `remaining_budget.active_wall_time_seconds`. Report the real time difference
and enforce the real deadlines. For every later request, capture ordinary
assembly and final assembly: removing the single added current/historical field
must recover that turn's ordinary input exactly. Later I3 plans may differ from
I2 because the model acts freely; they must not be replaced with saved I2 plans.
Record final counted/dispatched request hashes, segment/candidate identity,
packet hash, placement and timestamps. A prepared preview alone is not exposure.

The retained data increases input bytes, salience and redundancy. Normal existing
segmentation remains; there is no new pruning or policy change to compensate.
If the fully assembled request exceeds 60,000 tokens, stop without trimming,
summarizing, shrinking output or creating a replacement handoff to make it fit.
Token counts remain NOT_RUN; old counts are never reused.

## Stops and decision rule

Stop before dispatch on binding, data, currency, first-input or non-treatment
parity uncertainty. Stop on count, transport, billing, continuation, private-data,
infrastructure or cleanup uncertainty. Apply the fixed phase, cost and
operation-specific caps. No retry, resume, model substitution, correction call,
automatic Docker start, or image pull/build.

Close this one I3 row regardless of full success, failure, non-exposure or cutoff.
No outcome-dependent wording, data, grading, threshold or seed change, extra
sample, replacement row or automatic follow-up. I2's USD 0.509389 known subtotal
and unknown fourth-call usage stay closed and separate; no allowance transfers.

This is a single historical-control comparison, not randomized or replicated.
The first new response may differ before retention takes effect. Even complete
success supports only local feasibility under this data delivery; it does not
isolate continuity from salience/redundancy, estimate an effect size, demonstrate
spontaneous diagnostic selection or establish general memory/repair gains.
Keep the baseline unchanged. No automatic adoption follows a PASS, and a negative
or unobservable result does not authorize adjacent wording experiments.

## Design artifacts and remaining work

External root: `C:/pt/isortretainplan01`. Limits/criteria were the first event in
append-only, hash-chained `runs/run_dev_isortretaindesign.jsonl`, before treatment
or preview construction. The frozen design packet is `design-packet.json`,
`sha256:d43f3e998691a1b73c288217ee3480262dfa3a7f36eb409f91a774f6f11e5ee4`.
It binds `plan.json`, `limits-and-criteria.json`, `retention-policy.json`, the
unchanged I2 feedback/grading/oracle/cap rules, `observed-candidate-diff.json`,
the historical data envelope, `static-parity.json` and source bindings.
Design head: `974789520ace6909e9a624db934e530141821f92`; runtime remains
`sha256:b3c8e80c0656fb4954eebcb5d30de411d4b0fa687a150ef3308883487bb08208`.

Saved-data transforms of actual inputs 344/363/377/394 passed: the first is
unchanged; the later three add only the operator field, and removing it recovers
each complete original request, including plans/advice/diff/tools/native items.
Each later serialized request grows by 27,862 bytes due to JSON escaping; this
is not a token count. The historical envelope preserves the complete packet and
seed patch. These later-input fixtures are operator-only examples, not an I3
trajectory and not an authorization to splice in I2 responses.

The initial static builder stopped on a serialization-binding mismatch: the
audit's published hash identifies its indented CAS artifact, while `analysis.json`
is a compact view. A separate builder binds the journal-referenced CAS bytes and
verifies equal parsed content. The original script, failure explanation and
already frozen limits are preserved; no source evidence or criterion changed.

Next, if requested, implement a separate narrow connector and use provider-free
mocks to verify real first-wire reconstruction, same-segment/handoff delivery,
post-edit historical placement and exact return, token/count/cost/tool/edit/time
boundaries, uncertainty stops, edit/recheck/submit, C non-exposure, R no-action
censoring, U/C/R sealing order and private-result isolation. Bind that committed
implementation and validation in a fresh executable manifest before paid approval.
No execution manifest, connector readiness or mock continuation is claimed here.

Five documentation-layout/link tests passed. Static validation verified 59 bound
files, the design journal chain, new record links and unchanged runtime/AGENTS.md;
`git diff --check` passed. Runtime/Ruff/full-suite/mock-smoke runs were not needed
for this design-only documentation change. No live or target behavior was tested.
