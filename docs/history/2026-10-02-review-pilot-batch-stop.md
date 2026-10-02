# Revised review pilot stopped on a mixed tool batch

Date: 2026-10-02. Follow-up to the
[frozen proposal](2026-10-02-review-pilot-ready.md).

## Approved execution and outcome

The user instructed execution after the exact twelve-episode, USD 24 proposal.
Manifest SHA:
`sha256:8822888faab6122852f00c6eefc9566a89968ca7936c6c00a58fb67778cb6d59`.
Executing commit: `4be2dca6`; model, credential path, repetitions and limits remained
as frozen. Exact-manifest and all four environment admissions passed.
Run root: C:/pt/runs/review-context-pilot-20261002-v1.

One episode completed, one partially executed, and ten never started. The panel
stopped according to its protocol and was not resumed or retried. Allocation closed.

| Episode | Observed result | New usage cost |
| --- | --- | ---: |
| OpenSandbox C | Unchanged candidate submitted; acceptance FAIL, safety PASS; public matrix 5/8 | USD 0.0299565 |
| OpenSandbox A | First reviewer response rejected before any tool execution | USD 0.1339760 |
| Remaining ten | NOT_RUN | No dispatch |

Total new usage cost: USD 0.1639325. The result records billing_known=true and
includes the partial review settlement; no independent provider invoice was checked.
Unlike the preceding allocation, A is correctly labeled PARTIAL with its settled
usage preserved. Original result, journals and manifests remain immutable.

## Diagnosis

The first A response contained read_file and run_probe together. The local review
executor permits a single call, or up to four calls consisting only of reads and
searches. It rejected this mixed batch with `invalid review batch` before either
tool ran. The proposed probe therefore supplies no observed behavior or correctness
evidence. There was one completed reviewer generation with settled usage, no report,
and no repair continuation.

The saved request has parallel_tool_calls=true, but its review system instruction
does not state the batch restriction. The run_probe description also omits the
single-call restriction. The custom reviewer projection replaces the original
system instruction, while the executor still enforces its grouping rule. This
establishes a reviewer-interface mismatch; it does not establish that explicit
instructions alone would guarantee compliance.

The new remaining-budget message was present. Partial accounting worked in this
live stop. The final-call reporting rule was not reached and cannot be credited
with a live success. This failure differs from the previous call-limit exhaustion.

## Provider-free audit and decision

Driver: C:/pt/review_pilot_batch_stop_audit_20261002.py.
Evidence: C:/pt/analyses/review-pilot-batch-stop-audit-20261002-v1/summary.json.
The audit validates saved journals/artifacts, reproduces the batch predicate,
checks zero reviewer actions, matches settlement to the partial row and total,
revalidates all original source hashes, and confirms the unchanged C candidate.
No model or probe was dispatched during audit. No evaluator, prompt or runtime
change was made during this allocation.
Five documentation layout/link tests and git diff --check passed.

The comparison is INCONCLUSIVE: B and the other three tasks never ran. Preserve
the baseline. Before proposing another paid comparison, audit reviewer-facing tool
grouping, budgets and completion against the executor as one contract and exercise
valid/invalid batches offline. Avoid another cycle of a single observed contract
patch followed immediately by paid execution. No additional paid run is queued.
