# Reviewer completion and partial accounting

Date: 2026-10-01. Provider-free follow-up to the
[stopped live pilot](2026-10-01-review-pilot-live-stop.md).

## Observed defect and bounded change

The first reviewer used four calls on inspection without a report. The harness
never supplied its four-call horizon and then made an unnecessary fifth input
count before rejecting generation. The outer collector labeled this partial run
NOT_RUN and omitted its settled review usage from the aggregate. These are
completion/accounting defects; the evidence did not compare A and B repair quality.

Every reviewer request now receives its remaining call/action/time/cost allowance.
The final call is reserved for finish_review through the existing forced-function
tool choice mechanism. This also applies after the action allowance is exhausted.
A response that ignores the constraint stops before tool execution; it receives no
extra call. Reports may state uncertainty or no established defect. No limit is
increased and A/B share the same rule. Call admission is checked before counting.

Reviewer stop records retain a specific reason, settled usage and billing certainty
separately. Completed settlements survive an expected protocol stop or a later
unknown count/dispatch. The collector marks unfinished attempted rows PARTIAL,
keeps untouched rows NOT_RUN, includes partial settlements in its recorded total,
and leaves the total null when uncertainty remains. All later episodes still stop.

## Validation and limits

Adversarial finite responses exercise three exploratory calls followed by a valid
report, another read, or count/transport/usage failure. Assertions cover decreasing
budget visibility, forced final report, rejection before a fourth read, no fifth
count or generation, and preservation of earlier settlements. Collector tests
cover both known partial totals and uncertain totals with a recorded lower bound.
Existing continuation-order tests retain encrypted reasoning and call/result order
around the added budget message.

The 62 focused tests passed in 100.88 seconds. Ruff, five documentation tests and
whitespace checks passed. The first test run exposed test assumptions about the
last input item and a string-versus-Path fixture argument; those fixtures were
updated for the budget message and the rerun passed. Mock smoke
`run_dev_efee4ff49b86420a` reached EVALUATOR_PASS with safety NOT_RUN and zero
provider cost at C:/pt/runs/review-horizon-mock-20261001-v1.

The stopped result and reviewer-journal hashes match the separate audit record.
The previous manifest is rejected because its bound implementation changed.
On 2026-10-02 the full local Windows suite passed: 3,904 passed and 16 skipped in
3,288.53 seconds (54 minutes 48 seconds), with four workers, loadfile distribution
and no worker restart. JUnit evidence:
C:/pt/tmp/reviewhorizonfull01-results.xml. Implementation commit: `a1ecfa6b`.
This is local validation, not remote cross-platform CI. No paid calls, evaluator
changes or edits to the closed manifest/journals/results are part of this follow-up.
The earlier reported USD 0.216319 remains historical usage, not a new allocation.

## Decision

Keep the baseline and the closed pilot result. The change makes the finite horizon
explicit and enforces completion at the boundary; it does not prove reviewers will
produce useful reports or repairs under four calls. A new comparison requires a
fresh exact manifest and explicit paid approval. Do not reuse the prior approval.
