# HF versus tox: argument and retained-framing audit

Provider-free follow-up to the [closed context experiment](2026-09-30-evidence-context-results.md).
No previous grades, results, inputs or history files were revised. All budgets remain
closed. This audit reads only delivered public evidence and saved public responses.

## Finding

The useful localization is the connection from a public requirement and an observed
result to applicability/resolution, not delivery or candidate identity. However, the
experiment does not isolate a model reasoning deficit or a source-trust mechanism.
Its B arm retains prior model explanations and task-specific repair hypotheses inside
the shared evidence object. The literal label "evidence only" is therefore too strong:
read B as **reduced surrounding context with retained framing**. The prior result still
holds for the actual removed fields; it is not a clean test of all explanatory context.

## Delivered argument chains

| Element | C1 HF current counterexample | C4 tox current regression |
| --- | --- | --- |
| Public preservation requirement | Preserve callers without an explicit endpoint | Preserve explicit replacement defaults |
| Constructed input | HF_ENDPOINT is set; HfApi(token=False) omits constructor endpoint | Existing source section, missing key, reference with fallback |
| Executed observation | Ambient client rebases the default-origin route; direct call preserves it | Missing-key reference returns empty, not fallback |
| Setup evidence | Three selected comparisons passed, including ambient.endpoint | Six selected comparisons passed; direct-module execution reaches changed code |
| Same-candidate binding | Operator observed_on_diff_hash equals current diff | Probe action/diff hash equals current diff |
| Local mechanism delivered | Diff forwards self.endpoint and rebases non-None endpoint; no materialized source groups | Diff plus 47 source lines show broad KeyError catch and later default fallback |
| Registered PASS | Client paths explicitly construct HfApi(endpoint=endpoint); ambient constructor omission is absent | showconfig suite passed; this does not establish the reduced missing-default case |
| Prior explanations retained in both arms | Two check decisions describe propagation/rebasing PASS and completion | Two probe decisions already identify default swallowing and propose narrowing the handler |
| Response pattern | All identify the observation; applicability remains uncertain with provenance caveats | All identify the current default regression and limit unrelated PASS |

HF's additional inferential step is to interpret "explicit endpoint" at the public
caller boundary rather than equating a populated client.endpoint attribute with an
explicit constructor argument. The probe shows those are different: ambient and
explicit clients have the same attribute but only one received the constructor
argument. The issue, exact program, setup comparisons, stdout and diff are present.
Thus zero materialized source groups does not mean the HF evidence is absent. It
does mean the larger constructor/source context available for a code-level explanation
differs from tox. This audit does not fetch unseen source to retrofit the reviewer input.

Tox's source closes a much shorter argument: a missing src[key] raises KeyError;
the new inner handler returns empty before the outer fallback can use settings["default"].
The retained plan states this mechanism and the possible repair before the reviewer
is asked. Successful tox reports cannot establish independent derivation from execution
evidence alone. They also do not prove copying or reliance on the retained explanation.

Both experiments have diagnostic limits and model-authored expectations. A passing
setup comparison does not establish applicability; a failing assertion alone does not
certify a bug. Conversely, being unregistered does not rebut a requirement-based
counterexample. Keep these provenance limits rather than relabeling expectations as truth.

## What survived the context removal

`diagnostics/evidence_context_design.py:project` excludes seven top-level context
fields and moves turn_decision from archived function arguments. All other current
state fields remain intact to avoid dropping mutation/result facts. Consequently,
recent_attempt_result_next_question retains both turn_decision and next_question.
Nested turn_decision includes basis and plan_update, sometimes a specific repair.

The exact surviving decision paths in B are:

- C1: evidence.recent_attempt_result_next_question[0..1].turn_decision.
- C2: evidence.recent_attempt_result_next_question[0..2].turn_decision.
- C3: evidence.recent_attempt_result_next_question[0..2].turn_decision.
- C4: evidence.recent_attempt_result_next_question[1..2].turn_decision.

C4's first retained decision says the handler catches KeyError around src[key] and
process_raw, and instructs narrowing it if the default is swallowed. C1's last retained
check card describes PASS and the next regression check; its next_question permits
submission but explicitly warns that PASS does not resolve unrelated concerns.
These are interpretations/advice, not observed result facts. A and B contain identical
copies, so removing working_plan/working_notes did not remove all prior plans.

Both cases also have workflow_gate=ready_to_submit, current_public_failure=null and
no remaining visible checks, despite the targeted observations. Therefore different
gate values or a populated registered-failure slot cannot explain this pair's different
reports. Their latest evidence, provenance, source support and narrative still differ.

This is a finding about these frozen replay inputs, not a claim that every current
runtime request retains such cards. The current compact_model_state filters most cards
depending on the projection path. The actual delivered request remains the authority.

## Competing explanations and practical implication

| Hypothesis | Evidence here | What remains unresolved |
| --- | --- | --- |
| Observation was lost or mistaken for another candidate | Both arms retain it; reports identify it correctly | Not supported for these cases |
| A different submit gate caused the contrast | Both gates/registered-failure slots match | Gate alone is insufficient; interaction remains possible |
| Too much of the removed surrounding context caused failure | Substantial reduction did not improve C1 | Retained framing means broader context effects remain open |
| Prior explanations steer the conclusion | tox carries a matching mechanism; HF carries PASS descriptions | No intervention on those nested explanations |
| External versus native diagnostic status changes weighting | HF responses cite external/unregistered status; tox is a native probe | Provenance is confounded with content, code and case |
| HF requirement mapping needs more semantic/source work | Explicit caller argument differs from resolved attribute | No source-matched or interpretation-matched comparison |

The engineering issue that can be stated with confidence is **an incomplete separation
of observations from interpretations in the diagnostic projection**. It limits what
the experiment identifies. It is not yet evidence for a new runtime memory mechanism,
hard submission gate, or deleting provenance warnings. The agent-level observed
failure remains unsupported applicability/closure in the HF episode; its cause is open.

The smallest useful next preparation is a single-axis, provider-free comparison that
moves only the retained recent_attempt_result_next_question[*].turn_decision objects
out of one arm. Hold source bodies, public issue, program/assertions, setup/output,
candidate/action IDs, provenance and other advice fixed. Recursively audit the prepared
request for duplicate copies before declaring that axis isolated. Do not recursively
delete all question/expectation text: probe programs and expectations are part of the
evidence needed to assess an assertion. Byte/hash checks should prove their preservation.
Only after that preparation should a new paid comparison be proposed. This audit
does not prepare, authorize or execute that comparison, or change the runtime.

## Verification and record

Audit root: C:/pt/analyses/evidence-argument-audit-20260930-v1.
`audit.py` reconstructs and validates all four prepared pairs, checks their identical
evidence, inventories structured interpretation paths, verifies HF constructor/check
coverage and current probe binding, and preserves excerpts with exact JSON paths.
`audit.json` and its hash-chained run_dev_argumentaudit receipt bind preparation,
eight view artifacts, source journals/envelopes and prior review files. All stayed
byte-identical. This is deterministic inspection, not a model run or causal test.

Provider calls, API token counts, task actions, Docker and evaluation: zero. Existing
runtime and frozen grading remain unchanged. Documentation checks cover the new
follow-up and bounded current snapshot; no new software behavior requires task smoke.
