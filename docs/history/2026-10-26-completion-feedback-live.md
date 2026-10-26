# Completion-feedback pilot: no first edit, correction exhausted

Date: 2026-10-26. Status: CLOSED after one authorized fresh solve.
official=false; claim-ineligible. No retry, resume or transfer of remaining funds.

## Problem, question and frozen conditions

The [plan](2026-10-26-completion-feedback-live-plan.md) tested whether the
[completion-feedback change](2026-10-26-completion-feedback.md) would carry a
captured target exception into repair, support useful finalization within the
same cap, and help the model reuse delivered inspection evidence. The prior
pilot's missing exception feedback, repeated inspection and small final outputs
made these correctness and completion problems worth investigating.

The user authorized the frozen request with "실행해줘". This was one fresh
Astroid-1333 dev-train solve using gpt-5.4-mini-2026-03-17 xhigh, normal/correction
ceilings 40,000/25,000, the repository `.env`, 40 model calls, 100 actions, four
edits, 1,800 active seconds and USD 1.20 invocation cap. Operator supervision was
1,920 seconds. Existing prepared source, dependencies, images and frozen public
post-submission checks were unchanged. No prior patch, caller or operator
diagnosis was seeded into the solver.

- Execution commit: `ae06ff720e1cae4761f9d2161d751490db2feb6f`.
- Implementation commit: `a885f8ea79f3511b62fb0bf219a66b62e6fd04b7`.
- Runtime: `sha256:3a7fd37953ffeee6074c53f93ebc315ebe4a77673c9dc40b1645480c9082a1f0`.
- Request: `sha256:9f1ab5f3c57e07a98f54b61b71b6e86b566ee9013e01e07c1437a95229d03349`.
- Run: `run_dev_e6e47ca89df54317`.
- Preparation: `C:/pt/completion-feedback-live-ready-v1`.
- Execution: `C:/pt/completion-feedback-live-v1`.

## Observed result

| Measure | Result |
|---|---|
| Logical terminal | INCOMPLETE_RESPONSE |
| Process | Exit 0; no hard timeout; stderr empty |
| Operator wall time | 679.51 seconds, about 11 minutes 20 seconds |
| Model / input counts / registered actions | 34 / 35 / 34 |
| Actions | 22 search_files, 11 read_file, one rejected run_probe |
| Applied edits / target executions | 0 / 0 |
| Billed cost / unused cap | USD 0.843607950 / USD 0.356392050 |
| Input / cached input tokens | 1,122,395 / 724,736 |
| Output / reasoning output tokens | 109,113 / 98,010 |
| Original obligation | unverified; no original execution result |
| Public regression / submission / independent evaluation | NOT_RUN / none / NOT_RUN |
| Frozen public checks / safety | NOT_RUN / NOT_RUN |

Cached input is part of input, and reasoning output is part of output; do not add
either category again. Process exit 0 means the runner returned its terminal
record, not that the task succeeded. The final patch is empty. F0010 was never
executed or checked in this run, so there is no observed repair or persistence
verdict for its behavior.

## Public action sequence and failure

1. Calls 1-6 remained in needs_original_reproduction but selected only source
   reads/searches. The bounded six-action acquisition stage then released into
   needs_mutation, retaining the unverified original obligation.
2. Call 23 issued the first run_probe request. It used original_requirement
   purpose with symbolic call_path, no authored helper source and no established
   original-call diagnosis. The host rejected it with CONTRACT_ERROR:
   `symbolic call_path requires a pending original-call diagnosis`.
   This was preflight_rejected, not a helper exception or a target execution.
   The model returned to inspection instead of repairing that request.
3. Through call 32, the model had completed 33 reads/searches and that one rejected
   probe, spending USD 0.557793300. Six inspection actions added zero covered
   lines; that metric alone does not prove they had no semantic value. Call 33
   was offered only replace_text/stop_task because the completion horizon closed
   exploration with eight model calls remaining.
4. Call 33 returned two replace_text requests, for astroid/builder.py and
   tests/unittest_builder.py. It used 30,833 of the admitted 40,000 output tokens,
   including 29,289 reasoning tokens, and cost USD 0.163911750. The host rejected
   the batch with INVALID_TOOL_BATCH before either edit was applied. Reads may
   be batched; a mutating response must contain exactly one action. The rejected
   edits have no behavioral evidence and are not submitted repair artifacts.
5. Call 34 received the explicit batch correction in a new context segment, with
   14,150 input tokens and the full protected 25,000 correction-output allowance.
   It used all 25,000 output tokens as reasoning output and returned no tool call.
   It cost USD 0.121902900 and ended with max_output_tokens/incomplete_response.
   The single protocol correction allowance was consumed, so the run stopped.

This terminal was not caused by reaching the USD 1.20 cap, 40-call maximum or
time limit. The first repair response was not truncated: it returned a disallowed
two-action batch. The subsequent correction exhausted its separate output ceiling.
This distinguishes request construction and useful-action production from the
availability of total money or an admitted output allowance.

## Mechanism findings and decision

| Mechanism | What this run establishes |
|---|---|
| Selected-call target-exception feedback | NOT_EXERCISED: no target invocation |
| Observation/source reuse advisory | NOT_EXERCISED: no complete first observation |
| Compact finalization and completion correction | NOT_EXERCISED: ready_to_submit never reached |
| Finalization funding | 8,192-token floor was present in admission records; useful finalization remains untested |
| Separate first protocol correction | Full 25K allowance delivered; no usable action returned |
| Honest completion boundary | No patch, verification or submission was credited |

The downstream feedback and finalization hypotheses remain unresolved. Their
absence here is not evidence that they failed after being delivered. The new
advisory begins after a complete observation, so it cannot address this run's
earlier inspection loop by itself.

The next diagnostic priority is the transition from initial exploration into an
executable original request and from a rejected edit batch into one corrected
action. Inspect which evidence and request fields were available at those two
points before changing total spend. A higher correction ceiling might change
this particular response, but this run does not establish that it would produce
a useful action. Unused budget does not justify a second run. No additional
runtime change or paid experiment was performed during closeout.

This is one exposed-task fresh solve, with stochastic model decisions and multiple
runtime changes relative to the historical baseline. It is neither a causal
comparison nor a general solve-rate result. No private evaluator contents,
reference patch or model reasoning text was inspected for this analysis; token
usage metadata and public requests/receipts supplied the observations.

## Evidence integrity and closeout

Current source/task identity, prepared source/dependencies, existing image
identities and frozen check bytes passed preflight. Runtime and the 127-file
inventory remained unchanged. All 34 provider starts had settled returns; all
34 registered action identity pairs matched. Counting and billing are known.
No target container ran, no image was acquired and no credential contents were
printed by the operator. The solver alone loaded its authorized credential file.

The collection verified 161 content-addressed objects plus preparation/execution
journal chains. Later analysis is separately stored and hash-linked. The
post-submission assessor recorded NOT_RUN/no_submission without executing its
two programs. Existing user changes and historical evidence bytes were preserved.

- Collection: `sha256:6b2ff30f4e994a4388bb906cf3a29343d3e2b9aec52c3d16292933d0f93fbc34`.
- Public analysis: `sha256:b955cf6140a524ef810200bd1ee608e29e97ba3187debcfa993ea627f90a0c2e`.
- Process result, public-assessment.json, collection.json and public-analysis.json
  are retained under the execution root; scripts and exact authorization are under
  the preparation root. The source/runtime tests from implementation remain local
  mechanism evidence; this paid run adds no repaired-task acceptance evidence.
