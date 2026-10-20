# B2 uptake grading correction

Date: 2026-10-15. Existing-evidence review; no model, count, probe, task or
evaluator execution. The user requested comparison of B2's original response
with the predeclared criterion, without another run.

## Decision

Correct **B2 U from NOT_OBSERVABLE to PASS**. The initial
[result record](2026-10-15-uptake-results.md) applied the frozen criterion too
narrowly. B2's public hypothesis and expected behavior connect the observed
flat/CTE distinction to conditional preservation of L036 behavior, and its accepted
edit implements that distinction. The correction uses those pre-submission
public fields, not the successful patch's later public or private test results.

| Row | D | U | P | I | Safety |
| --- | --- | --- | --- | --- | --- |
| B1, unchanged | PASS | FAIL | FAIL | FAIL | PASS |
| B2, corrected U | PASS | PASS | PASS | PASS | PASS |

The complete observable chain is **1/2, mixed evidence**, replacing the original
0/2 interpretation. Public repair and isolated acceptance remain **1/2**.
Original cost remains USD 1.21861750, with eight generations and eight counts.
Regrading used zero provider calls and zero task executions. Keep the runtime
baseline; no adoption, causal gain, general quality claim or new run follows.

## Frozen criterion and the actual evidence

The [design](2026-10-15-uptake-design.md) permits the existing hypothesis,
causal-revision, notes **or tool arguments** to connect an observation to
rejection **or material qualification** of the simple-revert premise, with a
consistent next action. It explicitly requires no announcement or explanation
format. Correct behavior without a public linkage would still be insufficient.

`C:/pt/hypfollow01/grading.json` remains unchanged at
`sha256:40899f2b28d39d28913e0d561f57d4239a6557ce86d823546f0303a8ee7bdc8a`.
Relevant source events are in
`C:/pt/hypfollowlive01/B2/runs/run_dev_c6cdf266d5a34ded.jsonl`:

| Requirement | Existing public evidence | Assessment |
| --- | --- | --- |
| Identify a relevant observation | Seed receipt 374 shows five-space CTE output under reversion. Follow-up question 384 asks whether L036 alone or L003/L036 interaction explains flat/CTE behavior; receipt 387 contrasts their outputs. Edit hypothesis 416 describes the observed wrongly indented flat first target. | The explanation refers to the concrete rule-specific behavior investigated in the probes. |
| Reject or materially qualify simple reversion | At 416, the hypothesis restricts whitespace copying to the first target being alone on its original line; expected behavior says CTE cases should still inherit the existing target indentation. | The explanation preserves the L036 behavior needed for CTE and removes it for the flat case, materially qualifying blanket reversion. |
| Act consistently | Decision 416 and accepted edit 419 compare the first and second targets' original `working_line_no` and copy indentation only when they differ. | The accepted action implements the stated distinction. |

The accepted hypothesis says:

> In flat SELECTs with multiple targets on the original SELECT line, that borrowed indentation belongs to later lines and incorrectly indents `a,`. Restricting the copied whitespace to cases where the first target is the only target on its original line should preserve the CTE behavior while restoring the L036 regression case.

The same call's expected behavior says:

> CTE-style cases where only the first target moves off the SELECT line should still inherit the existing target indentation so the combined fix keeps `my_id` aligned with the following targets.

These are pre-edit public explanations of the mechanism and required distinction,
not an inference from P or I. A conditional edit alone, with no such explanation,
would not establish U. Here the observed behavior, stated qualification and
matching edit jointly satisfy the original criterion.

## Why the original NOT_OBSERVABLE grade was too strict

The initial grade acknowledged that B2 materially changed its repair strategy
and distinguished flat L036-only behavior from CTE preservation. It nevertheless
required the explanation to explicitly restate the **first seed counterfactual**
or name the **simple-revert premise** in
`causal_revision.falsified_prior_hypothesis`. That field instead named the
always-copy-whitespace premise, and `memory_update` was null.

Those facts do not veto the combined hypothesis and expected-behavior evidence.
The criterion allows multiple public fields and material qualification; it does
not require a particular field, a restatement of the seed result, or a note
update. The original adjudication effectively narrowed the permitted evidence
and explanation form. The explicit-linkage requirement is retained: the linkage
is expressed semantically by the public flat/CTE distinction and conditional
preservation argument already present in the response.

This correction does not assert that the first diagnosis caused the repair or
reveal the model's internal reasoning. It recognizes observable uptake under
the predeclared rule. No fresh A or result-withheld control exists. This is a
retrospective review after private outcomes were already known, not a new blind
assessment; the U justification uses only the recorded public observations,
arguments and action before submission.

## Preservation and evidence

The original execution, grades, result document and frozen design are preserved
byte-for-byte. This separate follow-up supersedes only the B2 U interpretation
and complete-chain aggregate. Ten consumed historical files were hash-bound and
verified unchanged; the B2 journal chain was also validated. The user's existing
AGENTS.md change remains separate.

New external evidence: `C:/pt/hypuptakeregrade01/result.json`;
artifact `sha256:9c3b25547e36eddbb239ca55a94f9d8c69bb1d0662fc6e78ae7cdef4aa9825f5`.
Its append-only `run_dev_uptakeregrade` journal records the old grade, unchanged
criterion, criterion-to-evidence mapping, correction and zero new executions.
Only current status/navigation and this follow-up are changed in the repository.
Five documentation layout/link tests, the follow-up's local links and the scoped
Git diff check passed. No agent workflow, mock smoke or task evaluation was run.
