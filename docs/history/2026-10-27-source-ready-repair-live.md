# Source-ready repair: inspection saturation and uncertain usage

Date: 2026-10-27. Status: CLOSED; official=false. No repair or acceptance claim.
Execution implementation: `a7bf2e0e`, diagnostic hash `ab09c725...`; runtime remains
`5753dbef...`. See the [exact approved preparation](2026-10-27-source-ready-repair-plan.md).

## Material Passport and execution scope

ARS single seeded feasibility run, public evidence only. The user approved the
manifest `49f8be0b...`: same first failed Astroid-1333 candidate, mini/xhigh, one run,
USD 1.20, eight ordinary responses plus one correction, twelve model tool actions,
one probe and one new accepted edit. Source availability, presentation and response
horizon differ from the preceding A/B; this is not an isolated effect comparison.

Root: `C:/pt/source-ready-repair-live-v1`. Result hash:
`sha256:5c07810335f45faa177d3ec362dcf44379a16e0a9280df2ceb83c443268dfe61`.
B journal hash:
`sha256:474ab6a53249fda01c2b13bf792301841533476c842b078e108bc69b9eece217`.

## Result

No new mutation or diagnostic probe occurred. Six settled model responses used all
twelve model actions for reading/searching. A seventh response was dispatched with
zero remaining tool actions and ended in BILLING_UNCERTAIN. Generation stopped;
there was no retry or continuation. Original/control replay, public regression,
submission and independent acceptance were NOT_RUN because no candidate was produced.

| Measure | Observed |
| --- | --- |
| Host source reads | 6, separate from model actions |
| Source packet | 8 excerpts, 148 lines, 5,140 source characters |
| Provider dispatches / settled responses | 7 / 6 |
| Model read/search actions | 12 |
| Diagnostic probes / new edits | 0 / 0 |
| Settled response output tokens | 11,985 total; largest 4,925 |
| Seventh requested input count | 35,401, below the 60K input ceiling |
| Output ceiling on each dispatch | 40,000 |
| Settled cost for first six responses | USD 0.084176850 |
| Total cost including seventh response | UNKNOWN |

The JSON field `new_cost_nanos=84176850` is settled cost only; `billing_known=false`
must accompany it. It is not the invocation's final bill. Known first-six outputs
did not exhaust their ceiling. The seventh response's usage, output size and detailed
status were not retained, so its termination cannot be diagnosed more precisely.

## What the model received and did

All seven actual requests retained the identical current failure and full source
packet with truncation disabled. Each of the six workspace excerpts exactly matched
the registered read's path, range, file hash and content. Mutation anchors were
available. The model could edit the delivered source without an additional read.

The first actions searched for the already-delivered `file_build` and namespace
handling. A subsequent builder read overlapped 50 supplied lines and added six lines.
The model also searched `pylint/**/*.py` in the Astroid repository (zero files), and
searched Astroid sources for `tokenize_module` (zero matches). The dependency function
was already present as a read-only excerpt; a diagnostic probe remained available.

By the fifth response the public action rationale connected a namespace object
without file/bytes to later tokenization or stream-dependent operations. This is
evidence of recognizing the relevant mechanism, so it would be inaccurate to say
the new information was entirely unused. However, the next actions did not test
that mechanism. The final two available tools searched direct API tests for
`file_build` and `ast_from_file`. No repair or hypothesis-targeted execution followed.

The last dispatched request reported two ordinary responses, one probe and one
mutation still available, but zero tool actions. Those per-category allowances did
not create an executable action. The operator nevertheless made a provider request.

Audit: `C:/pt/source-ready-repair-analysis-v1/analysis.json`, hash
`sha256:50a579545256c5970e2faf925b554d3ae3b16e83e0f9d0f6b080798882067da1`.
It verifies journals, actual request artifacts, retained packets, registered source
anchors, all action arguments and the six settled usage records. No reasoning text
or private task/evaluator data was read.

## Confirmed operator defects and bounded follow-up

1. `run_model` checked tool allowance only after generating a response. Once twelve
   reads consumed it, even a stop/edit tool could not execute. The local fix checks
   the existing action limit before constructing/counting/dispatching another request
   and returns TOOL_LIMIT. It does not reserve new capacity or force a repair.
2. The uncertain-usage event stored only `input_token_count_mismatch`. In the shared
   adapter this is a compatibility umbrella for missing/null/invalid usage as well
   as an actual input-count mismatch. The event omitted the already-sanitized
   `usage_evidence`, so the seventh response's precise failure kind cannot be recovered.
   The local follow-up preserves that evidence and call identity without raw response
   bodies or reasoning. Billing and stop-all rules remain unchanged.

These fixes prevent wasted dispatch and preserve future diagnosis. They do not
change this historical result, recover the seventh bill, or establish model repair
improvement. No new paid run is authorized by the fixes or unused allocation.
Local follow-up: 29 operator tests passed in 12.43 seconds, including stopping before
count/dispatch after twelve reads and still allowing an edit as action twelve.
Documentation5, Ruff and diff checks passed. The pre-run readiness quick472 remains
recorded separately; the product runtime was unchanged throughout this diagnostic.

## Decision and limits

The source packet reached the model and the mechanism appeared in its public action
rationale. The unresolved bottleneck is converting that understanding into a targeted
test or edit within available actions. Additional context/output capacity is not
supported by the known first-six behavior. The seventh usage error is a separate
uncertainty, not an explanation for why the first twelve actions contained no edit.

Do not add another mandatory failure-specific stage based on this result. Further
work should discriminate action selection/model settings from the repair opportunity
design while retaining a small stable surface. No new model comparison or additional
funding is implied. One development case and this bundled intervention cannot
establish model incapability, source-packet efficacy or general repair quality.

ARS methodological scan: 11/11 checked. No inferential test is warranted; the failed
and uncertain outcomes are retained. Conditional repair, whole-task acceptance and
fresh-solve generalization remain distinct and unestablished.
