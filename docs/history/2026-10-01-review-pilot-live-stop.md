# Review pilot stopped at the reviewer call limit

Date: 2026-10-01. Follow-up to the immutable
[readiness record](2026-10-01-review-pilot-ready.md).

## Authorization and execution

The user approved the exact twelve-episode proposal: four dev-train tasks, C/A/B
once each, gpt-5.4-2026-03-05 / xhigh / 25,000 output tokens, project .env,
USD 2 per row and USD 24 invocation cap. Manifest SHA:
`sha256:cd2ca5a1258c588d004c8b64c4ce55e0b102bfbd7b959bad75c2c1ca86eb9ee5`.
Executing commit: `7ac7f9e6`. All four environments passed admission.

Root: C:/pt/runs/review-context-pilot-20261001-v1.
The collector stopped on the second episode and did not retry or resume.
One episode completed, one partially executed, and ten never started. This
allocation is closed; unused capacity does not authorize another attempt.

## Observations

OpenSandbox C made one new model call and submitted its unchanged checkpoint
candidate. Isolated task acceptance FAIL, safety PASS, and the frozen public matrix
passed 5/8 observations. It left the same three known gaps. New cost: USD 0.0658275.
The receipt's ten model calls and one accepted mutation include inherited history;
they are not ten new calls or a new edit in this episode.

OpenSandbox A made four completed, usage-settled reviewer calls: three read_file
actions and one search_files. It produced no report or probe and never entered
repair. A fifth input count completed, then admission rejected a fifth generation
with `call budget exhausted`. The reviewer journal spans 79.726 seconds, below the
180-second review limit. Review usage cost: USD 0.1504915.

The original collector result records only the completed row's cost, labels the
partial row NOT_RUN, and marks total billing unknown. Preserve that result. Its
exception path loses partial-episode classification and settled-review aggregation;
the label does not mean no provider calls occurred.

## Separate provider-free audit

Driver: C:/pt/review_pilot_stop_audit_20261001.py.
Evidence: C:/pt/analyses/review-pilot-stop-audit-20261001-v1/summary.json.
The audit validates the review journal, matches four dispatches to four responses
and settlements, and reproduces rejection of call five using the same budget code
without a provider. There is no pending generation dispatch in that review journal.
It also revalidates all original source hashes and the unchanged C candidate.

Usage-record-reconciled new total: USD 0.216319 (five new model generations).
This is a separate reconciliation, not a modification of the original unknown
billing flag or independent verification of the provider invoice. No new calls
occurred during audit. Original manifests, journals and scoring outputs are intact.

## Interpretation and next question

The call cap worked, but the run did not reach a comparison of review procedures.
The reviewer receives no explicit four-call horizon or updated remaining budget,
and no call is reserved for its required final report. Finite rehearsals explicitly
supplied a report early and therefore did not test an exploratory reviewer reaching
the boundary. This is an observed harness usability gap, not evidence against fresh
context. The evidence does not establish that exposing the horizon alone would
produce a useful report, or that four calls suffice for this task.

Preserve the baseline. A provider-free follow-up should first distinguish expected
review exhaustion from billing uncertainty and retain partial settlements, then
test report completion at the existing call boundary with adversarial scripted
sequences. Do not expand budgets or tune against private scoring. Any changed
protocol requires a fresh manifest and explicit new paid approval. Improvement is
INCONCLUSIVE; B and all other tasks were never executed.
