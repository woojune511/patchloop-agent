# Diagnosis failure analysis: late repair and unresolved action-selection burden

Date: 2026-10-26. Read-only follow-up to the
[closed live pilot](2026-10-26-diagnosis-mode-live.md).

## Material Passport and scope

- Origin: academic-research-suite / experiment-agent, validate mode.
- Version: `diagnosis-mode-analysis-v1`; verification status: ANALYZED.
- One saved exposed dev-train run, `run_dev_d5a051b1ed8f4536`.
- Zero additional provider calls, target executions or runtime changes.
- Public requests, action receipts and source only. Provider reasoning contents
  and private evaluator material were not inspected. No reproducibility rerun.

The selected question is why the narrowed diagnosis contract still produced no
diagnostic action. Repeated pre-execution failures prevent measurement of useful
call-path diagnosis and repair; another increase in limits alone would not identify
which part of this failure needs intervention.

## Established observations

1. The model performed 28 read/search actions before its first accepted mutation
   at model call 32. Call 30 proposed identical old/new text and was rejected.
   Call 32 used 31,472 output tokens; settled spend then reached $0.762499800,
   about 64% of the invocation cap. Diagnosis began after this late repair.
2. The accepted `_spec_from_modpath` missing-init branch did not remove the original
   F0010. The automatic replay reported changed lines 631-633 unobserved. The model
   had described the source as localizing the failure, but this was an unverified
   interpretation. The evidence refutes its predicted original-call effect without
   proving that the entire function was never entered.
3. The shortened 805-character description was delivered, together with the correct
   null-only fields and required symbolic call_path. The complete delivered
   run_probe tool definition still occupies 7,158 characters in compact JSON.
   Its shared turn_decision schema is 5,502 characters in default JSON formatting;
   fields include mode, basis, evidence_goal, memory_update, plan_update and
   plan_update_reason. These are character counts with the stated serialization,
   not token counts. Optional annotations permit null, so size alone does not prove
   that a valid short answer is difficult.
4. The model still chooses an enclosing caller focus, one to four watched functions,
   paths/origins and up to six scalar fields per watch. The host fills identities
   and lines after selection. This removes coordinate bookkeeping while leaving
   the substantive diagnostic selection with the model. The system instructions
   retain 13,332 characters covering all workflow stages. Call 33's actual input
   was 31,981 tokens, despite the shorter tool description.
5. The correction was delivered in recent_attempt_result_next_question. It was
   not lost during context projection. Its message says to return a valid tool
   shape and offers a useful read/search, small public probe, or stop. It does not
   turn the failure into a minimal caller/watch selection task. Both actual
   requests already had tool_choice=required and reasoning effort xhigh.
6. Call 34 kept one opaque reasoning item from the incomplete response; its input
   was 48,323 tokens. No reasoning contents were decoded. The preparation choices
   and diagnosis tool schema remained the same. Calls 33 and 34 returned no tool
   action after 16,380 and 25,000 output tokens, all counted as reasoning by provider
   usage. No diagnosis request reached host admission or execution.

The source projection reported zero omitted observed ranges and zero omitted
pinned ranges. This does not establish that all necessary caller source had been
discovered, but there is no recorded loss of those projected ranges to explain
the outcome. Provider status identifies output exhaustion, not a context-window
error. Schema rejection, helper NameError and inconsistent failure judgment were
not the immediate failures in these diagnosis turns.

## Interpretation and alternatives

The observed chain is late first repair, unchanged original failure, mandatory
diagnosis, and two incomplete model responses before action dispatch. The terminal
stop follows the consecutive incomplete-response policy. The run retained
$0.200825400 of the $1.20 cap and six unused model slots; monetary or call-cap
exhaustion was not the terminal cause.

The leading structural hypothesis is that the request became valid in shape while
the diagnosis turn still required too much action selection and general workflow
bookkeeping. Its correction reused essentially the same selection problem with
more output allowance. This hypothesis is grounded in the delivered contract and
state, but no controlled comparison shows that their complexity caused the model's
token use. Stochastic behavior, xhigh effort, missing caller knowledge and output
allocation remain plausible contributors. Reasoning-token counts cannot reveal
what the model was thinking or prove an internal loop.

The 40,000 configured normal ceiling was not a guaranteed grant: future completion
and correction reserves reduced call 33 to 16,380. Call 34 received its full 25,000
allowance and still returned no action. This establishes neither that a larger
cap would work nor that the reservation is optimal. The contract correction can
remain useful even though live diagnosis admission was not exercised here.

## Next design priority

Reduce the pending diagnosis to a small decision before adding rules or budget.
Keep the frozen failing call, current changed region and failure evidence; derive
the known changed-function watch on the host where unambiguous, and ask the model
only for the missing diagnostic selection. Remove unrelated optional annotation
and all-stage instructions from that decision where their omission is safe.
The incomplete-response correction should target that same bounded decision.

This is a proposed intervention, not implemented or measured improvement. An
earlier bounded path observation could also prevent a late speculative repair;
its additional cost and opportunity cost need a separate comparison. Preserve
original-case verification and bounded cleanup/accounting regardless of which
intervention is chosen. No paid continuation is authorized by this analysis.

## Methodological limits and evidence

All 11 ARS fallacy categories were checked for applicability in the analysis
artifact. No p-values, population estimates or causal effect sizes were computed.
Selected-task bias, exploratory choices and historical comparison prevent a
general improvement claim. All failed and incomplete turns remain included.

Artifact: `C:/pt/diagnosis-mode-analysis-v1/analysis.json`.
Hash: `sha256:8c209616294751e5cbfe8f755d793289d8b849546e61d218ff2304635a7260a4`.
The artifact binds the two actual prepared request hashes, correction delivery,
token counters, source projection, shared metadata schema, and the prior closeout.
It is recorded in the external hash-chained dev-run-v1 analysis journal.

Documentation checks and the commit binding are recorded separately at closeout.
The closed live report and execution artifacts are unchanged.
