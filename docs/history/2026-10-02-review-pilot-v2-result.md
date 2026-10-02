# Review pilot v2: partial execution and timeout stop

The user approved the exact [readmitted proposal](2026-10-02-review-pilot-v2-readmission.md)
and USD 24 cap. Execution used source HEAD 94ae45e5 with the audited reviewer
implementation from 8d583e64. The unrelated local AGENTS.md edit was preserved.
All four environments and the complete manifest passed admission before dispatch.

## Frozen scope and artifacts

- Manifest: C:/pt/analyses/review-pilot-ready-20261002-v2/manifest.json
- Hash: sha256:2b10fc24828b4c8c2d3d7873728172faea53e298a74e68654a744acd96742707
- Result: C:/pt/runs/review-context-pilot-20261002-v2/result.json
- Result hash: sha256:29b4c9d53ebc1f810c3c5358a4fb4993a24aeead6bf7ef33056ed137706d958c
- Read-only audit: C:/pt/analyses/review-pilot-v2-result-audit-20261002-v1/summary.json
- Audit driver: C:/pt/review_pilot_v2_result_audit_20261002.py

The original four-task, three-arm order, model, budgets, source checkpoints and
public/private scoring contracts were retained. Two rows completed, one was
partial, nine never started. No retries, resume, replacements or extra calls were
made after the stop; this allocation is closed.

## Observed results

| OpenSandbox arm | Completion | Patch/evaluation | Settled new cost USD |
| --- | --- | --- | ---: |
| C: ordinary continuation | Submitted and scored | Original patch unchanged; public matrix 5/8; hidden acceptance FAIL; safety PASS | 0.0646275 |
| A: review retaining trajectory | Report, submission and scoring | Same unchanged patch and same verdicts as C | 0.1520800 |
| B: fresh factual review | PARTIAL, no report or repair | No new submission; acceptance NOT_RUN | 0.0418660 lower bound |

Both completed patch hashes equal the frozen source candidate. Their inherited
accepted-mutation counters are not evidence of a new edit. A returned its report
in one model call with no reviewer tool execution; its reviewer portion cost
USD 0.106655. A's extra review did not improve the final patch in this instance.

B completed two reviewer generations and executed search/search followed by
read/search, four registered actions total. Its third generation timed out with
APITimeoutError. No reviewer probe executed, no report was returned, and the
fourth/final-call report rule was not reached. The previous mixed-batch rejection
did not recur in the observed completed responses.

The third dispatch waited 146.838377 seconds; the interval from initial review
admission event to stop was 179.410217 seconds. This is consistent with exhausting
the 180-second review deadline while waiting for a response. It does not identify
why the provider response did not arrive within the remaining time. No returned
response or usage settlement exists for that third dispatch.

## Cost and uncertainty

Confirmed settlements total USD 0.2585735. This is a lower bound, not final spend.
The collector correctly records billing_known=false and new_cost_nanos=null,
retaining the confirmed amount as recorded_new_cost_nanos. Billing for the timed-out
generation is unresolved; no provider invoice reconciliation was performed. The
USD 24 cap is the authorized maximum, not observed expenditure.

## Audit and decision

The audit validated the hash-chained panel and reviewer journals, manifest/result
hashes, row statuses, completed candidate hashes, evaluation/matrix verdicts and
partial settlement arithmetic. It made zero provider calls and zero probe executions
and preserved original result bytes. Runtime code was not changed after observations.

The contract repair has limited live evidence: A returned a valid report and B's
completed read batches executed. The reserved-final-call behavior remains unexercised.
The repair-quality comparison is INCONCLUSIVE because B did not reach report or
repair and the other three tasks never started. Neither a fresh-context benefit
nor general ineffectiveness is established; no baseline change is justified.

Preserve the baseline and close the allocation. Remaining questions are whether
provider-side usage can be reconciled and whether the frozen review time allowance
can support the intended procedure. Any investigation starts with saved public
timing/action evidence; this outcome does not authorize longer limits or another
paid comparison. Historical records and hidden-evaluation boundaries remain intact.
