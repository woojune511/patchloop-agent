# Fresh normal task 8: provider interruption before repair

Date: 2026-11-01. Status: CLOSED. Execution commit:
`c855b0de317b3ba8c9f98585fc081247e853a392`.
Runtime: `sha256:763e4efd4f14a7939d9ca1e01db91d770be3445da6b3642404da3ddb12e96298`.
Development-only, official=false, claim-ineligible.

## Question and authorized conditions

The [fixed-patch diagnostic](2026-11-01-public-input-comparison-results.md)
used the new input comparison but did not resolve original-condition uncertainty.
That report-only setting could also influence its stopping decision. The current
question was whether the accumulated review changes support relevant observations,
repair and acceptance in a normal fresh solve. The earlier normal task8 at
60029805 failed independent acceptance; it used an older runtime. This is not a
first-ever normal-flow test or an isolated causal comparison of one field.

The user approved one pristine dev-train 8/pydicom1413 execution on c855b0de,
gpt-5.4-2026-03-05/xhigh, credential file
`C:/Users/geonj/Documents/PatchLoop/.env`, new total cap USD4, 12 accepted edits,
40 model calls, 100 actions and 1,800 seconds. The 330-second evaluation reserve
is inside the total, leaving at most 1,470 seconds for the solver. No retry or
extra evaluation was authorized. Cost, transport or recovery uncertainty stops
new work. Exact counting precedes generation; SDK retries remain zero.

The normal request uses the original public task and prepared base source, with
no saved candidate, checkpoint, helper, later diagnostic answer or operator
counterexample. Public checks and run_dev's single isolated evaluation were
authorized if the solver submitted. Private evaluator bodies/reference patches
were not supplied. This development-exposed task does not establish generalization.

The preparation records the question, baseline, frozen runtime, limits, judgment
criteria and stop conditions. Its wrapper reuses the earlier normal runner; the
normalized request changes only the state root. No runtime prompt/tool/gate was
changed for this execution. Fresh public capability canaries passed (import,
generic roundtrip, one selected existing test); they were not injected as solver
evidence. Same-runtime local validation remains 1,453 passed/one platform skip,
including isolated mock evaluation. That evidence is not live task acceptance.

## Observed sequence and failure

Run: `run_dev_43b9b0f439014efb`, 58 validated hash-chained events.

- Two valid response batches executed five searches and two reads, all on the
  unchanged source. No mutation was accepted.
- Sequence 51 proposed three searches and one run_probe in the same response.
  Sequence 52 rejected the whole batch as INVALID_TOOL_BATCH: up to four reads/
  searches may run together, while another action must be alone. The authored
  probe was never dispatched and contributes no observed correctness evidence.
  Its public question compared bytes against direct array input through save_as,
  but used I-array values and a flat Dataset rather than the known H-array/bytes
  and lineSeq setup. It printed outcomes, without assertions. This was a proposed
  helper comparison, not an exact original reproduction or a discovered failure.
- Sequence 57 started the fourth generation request, asking the model to correct
  the batch. This is a new protocol-correction request, not a transport retry.
- Sequence 58 terminated PROVIDER_TIMEOUT_OR_UNKNOWN with
  `provider dispatch failed: InternalServerError`. The fourth started call has no
  finished response/usage receipt. The available record does not contain HTTP
  status, request ID or response-body diagnostics for that exception.

Elapsed row time was 55.951 seconds. The last dispatch allowed 1,419.583 seconds;
its terminal followed about 5.45 seconds later. Therefore the observed cause is
the recorded provider exception, not exhaustion of the model or wall-time limits.
The broad terminal name alone does not identify a timeout. Upstream root cause
and whether the failed call incurred usage are unresolved.

Counts: four count calls completed, four generation calls started, three
generation responses settled, seven tools executed. Edits, probes, public checks,
submission, independent acceptance and independent safety are all NOT_RUN/zero.
No hidden evaluator was started. No provider retry, resume, further task run or
extra evaluation was performed. The batch stop latch closed the allocation.

## Cost and interpretation

Settled generation subtotal is USD0.1686595 for the first three responses.
The fourth call reserved USD0.45691 under the cap but has unknown actual usage;
reservation is not a charge. Total generation billing remains UNKNOWN. Count
endpoint billing and invoice are also unverified. Do not describe the difference
between USD4 and the subtotal as known unused funds. The entire allocation is
closed and none of its remainder authorizes another request.

The source-inspection and attempted-probe trajectory is observable. It did not
reach post-mutation review, executed counterexample evidence, repair or finish.
The fresh scope.input object schema was delivered, but scope_review remained null
in all three decisions. The normal repair-stage system prompt did not include the
diagnostic's full working-plan instruction paragraph; do not claim equivalent
delivery of every diagnostic instruction merely from a shared runtime hash.
Thus this run neither supports nor refutes improved verification or repair. It
also cannot explain an agent voluntarily stopping after helper success: that did
not happen here. The malformed batch is a separate protocol event, not evidence
that a proposed probe found a defect or that the new schema caused the exception.

Decision: retain the unchanged runtime and the unresolved normal-run question.
Do not infer a need to increase limits, force probes, or change semantic review
from this provider interruption. A later invocation requires its own authorized
allocation; this record authorizes no retry. The record preserves failure and
billing uncertainty rather than converting an interrupted run into a task FAIL.

## Evidence and validation

- Preparation: `C:/pt/condition-normal8-20261101-v1/`.
  Manifest `sha256:a14798989e49db5a5951177ccfcd58faae9392f350a1bd095000cc854dd20791`;
  preflight `sha256:6c026d6558811fa44ac22b5ab03cf813f5e2c1b8511598cc3c98a2607a612688`.
  Exact user approval is in approval.json; execution-console.log retains result.
- Execution: `C:/pt/condition-normal8-run-20261101-v1/result.json`;
  task journal under `8/runs/run_dev_43b9b0f439014efb.jsonl`.
- Public metadata audit and closure:
  `C:/pt/condition-normal8-closure-20261101-v1/`.
  Public action/usage facts and exact source bindings are retained in
  content-addressed artifacts and append-only dev-run-v1. No private evaluator
  bodies or raw/encrypted provider reasoning were inspected for this audit.

Only documentation changes follow this run. Documentation layout/link/history
checks pass (six tests); runtime quick/mock evidence belongs to the unchanged
runtime's prior local validation, not another execution in this closure.
