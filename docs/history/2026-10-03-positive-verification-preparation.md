# Positive-verification preparation and public predicate replay

Date: 2026-10-03 KST. User requested execution of the domain-knowledge plan.
This record covers completed provider-free assessment and the prepared repair
comparison. It does not authorize provider dispatch.

## Problem, evidence and decision

The final SQLFluff audit found a probe checking disappearance of nine-space
indentation, although the public example requires eight spaces. A five-space
output therefore escaped that check. The later standalone authoring response
contained an apparently correct expected-output predicate, but failed its verbatim
quote contract; no generated predicate was executed in that closed allocation.

The selected question was whether that unchanged saved predicate actually
distinguishes the public expected output from the observed symptom and other
wrong outputs. This is needed before interpreting the earlier NOT_ASSESSABLE
report as inability to understand or test the requirement. Alternatives were a
semantic predicate failure, an execution failure, or metadata-only rejection.

The unchanged saved predicate now passes all four controls in a new operator
sandbox replay. Its original quote remains invalid. The old report and its
NOT_RUN assessment are preserved. This establishes useful elicited predicate
authorship for this single exposed example; it does not establish autonomous
check selection, formatter invocation, repair success or a prompt benefit.

The remaining causal question is whether positive-result guidance is used during
an actual repair and changes its correctness. A fresh A/B implementation is
prepared in diagnostics/positive_verification_panel.py with the exact proposed
scope in [the experiment note](../../.agent/positive-verification-experiment.md).
Runtime defaults remain baseline. No provider calls were made in this preparation.

## Public-only controls and outcome

Controls are derived from the public expected SQL, before reading new outputs.
They comprise the full expected example, original nine-space indentation, a
different five-space indentation, and missing one_more content.

| Predicate origin | Correct classifications | Interpretation |
| --- | --- | --- |
| Operator exact positive-output comparison | 4/4 | Calibration succeeds |
| Operator symptom-only comparison | 2/4 | Accepts different wrong output and missing content |
| Operator constant true | 1/4 | Rejects no incorrect output |
| Operator erroring predicate | Unassessed | Errors are INVALID_OUTPUT, not successful rejection |
| Unchanged saved model predicate | 4/4 | One elicited public-example predicate discriminates controls |

The saved function compares actual.splitlines() against its literal expected
lines. Manual review agrees with the bounded single-example result: content,
indentation and blank-line layout are checked; line separators and an optional
terminal line separator are normalized. Other SQL inputs and valid formatting
variants were not assessed. No generated Python ran on the host.

The report's quote-validity axis remains false. Code execution and control
classification are recorded independently. The original authoring artifact was
hash-verified and neither source nor quotation was corrected.

Separate public API checks were frozen for the actual repair comparison. On the
unchanged prepared base, 1733 produces nine spaces and fails the complete expected
output comparison. In 1625 the no-alias example has no L031 violation, while the
alias example produces L031 at line 3, position 16. Both public defects are thus
reproduced in the same prepared environment intended for both arms. After the
paid batch, the frozen programs will assess only hash-verified submitted patches.
Public examples and original isolated acceptance remain separate result axes.

## Implementation and execution

The B arm replaces the generic closing paragraph of existing brief-v1 planning
instructions with positive-result guidance. Existing planning identity hashes
bind the actual text; A/B use the same system prompt, tools, state, completion
rules, prepared public dependencies and resource limits. Each fresh run restores
the ordinary instructions afterwards. No new required annotation or tool exists.

First scope is only positive expected behavior. Execution-path tracing and
neighboring preservation remain conditional follow-ups requiring new evidence.
Proposed live scope is two development-exposed SQLFluff tasks, two repetitions
per arm, eight runs of the selected full GPT-5.4 model, USD 3 per row / USD 24 total.
This is not yet a live-executed comparison or a default adoption.

The first calibration process completed all five sandbox programs, then failed
while writing its summary through a CAS-rooted store to the parent directory.
All completed receipts were durable. Fixed the output store root and finalized
the summary from five hash-verified artifacts without rerunning a predicate.
Added a local regression test for whole-summary creation with an invalid quote.
This operational failure did not change any classification.

## Evidence and validation

- New evidence: C:/pt/analyses/positive-verification-20261003-v1/calibration.
  calibration.json and run_dev_positivecontrols JSONL retain five sandbox receipts;
  finalize_calibration.py records artifact-only summary finalization.
- Saved public source artifact: C:/pt/loa1live01/objects/sha256/e8/
  d91dfd86934d360bde0ca3878ec001b0a776fb3ae043d8c5ab8c9cf52bdf8b.
- Saved response artifact SHA-256:
  e8d91dfd86934d360bde0ca3878ec001b0a776fb3ae043d8c5ab8c9cf52bdf8b.
- Final focused tests: 27 passed in 16.86 seconds, including the summary-output
  regression and five documentation checks. Report:
  C:/pt/validation/positive-focused-20261003-c.xml.
- Full fast suite: 4,013 passed, 16 skipped in 1,391.60 seconds. Report:
  C:/pt/validation/positive-full-20261003-a.xml. It was collected before the last
  summary-output regression was added; the final focused run covers that addition.
- Ruff passed on patchloop, tests and both new diagnostics. Mock smoke
  run_dev_9039b3515517491f reached EVALUATOR_PASS; safety remains NOT_RUN.
- Two new public import/plugin/parse canaries passed. Together with five predicate
  programs and two public base reproductions, nine isolated programs completed.
  canaries.json, public-programs.json, public-base.json and their operator scripts
  live under the new evidence root and are bound before paid execution.
- Provider calls: 0. Paid repair comparisons, their patch acceptance/regressions,
  cost/time comparison, and autonomous selection: NOT_RUN.

Prepared comparison does not feed these controls, the saved predicate, operator
diagnoses, prior patches or evaluator details into either coding-agent arm.
Original Lite and SQL3 results and all historical bytes remain unchanged.
