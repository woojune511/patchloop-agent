# Observed-source retention comparison

Authorized 2026-10-06 by the user's "실험 진행해줘" for the exact scope below.
This is a fresh-solve comparison design, not a continuation of a closed
allocation. Both arms use the same implementation including the resource accounting
correction from e55393ed. General runtime defaults remain unchanged.

## Question and smallest intervention

Does retaining more already observed source across context handoffs improve actual
repairs within unchanged call, action, token, cost and time limits?

The [source audit](../docs/history/2026-10-06-resource-budget-context-review.md)
found a lost arithmetic branch before SQLFluff-1733's wrong edit. A 48k-character
pool recovered it in saved-input projections; 32k did not. Source was available
again at submission, so retention alone does not explain omitted verification.
Alternatives remain: the agent ignores available source, selects a wrong causal
hypothesis, fails to test it, or loses useful turns to increased input cost and
earlier size handoffs. A correctness tie despite greater source availability would
weaken the proposed quality benefit.

A uses `retained_source_chars=24000`; B uses `48000`. Only that setting differs
apart from necessary fresh state paths and identities. Selection priorities,
segment boundary policy, prompts, tools and caps are identical. Active-function
pinning, new guidance, mandatory probes and automatic probe replay are excluded.

## Exact authorized scope

- SQLFluff-1733: `tasks/dev-train/current-dev20/18/public.yaml`, source-loss case.
- pvlib-1072: `tasks/dev-train/current-dev20/2/public.yaml`, regression control
  with PASS in both the previous full and corrected dev20 observations. This is
  an existing-success control, not evidence of the same source-loss mechanism.
- These task packages include selected/additive test capabilities. Do not replace
  them with the older similarly named Lite packages. Both are exposed dev-train
  tasks; no held-out inference or overall SWE-bench score is justified.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh, 25,000 output-token ceiling. Mini matches
  the motivating traces; this does not change the general full-model baseline.
- Credential file: `C:/Users/geonj/Documents/PatchLoop/.env`; never copy its content
  into a packet, journal or model input.
- Two fresh repetitions per task per arm: eight requests, each `repeat=1`.
- Each row: USD 1.20, 40 model calls, 100 tool actions, four accepted edits,
  1,800 total seconds including 330 seconds reserved for registered evaluation.
  Total invocation cap: USD 9.60; no transfers or increases.
- Shared policies: segmented-v1, result-or-size-v1, brief-v1, ordinary probes
  enabled, probe_policy none, probe_recheck none, repair_recheck true,
  protected-v1 inspection and per-call-v1 cost admission. Cross-run memory stays off.
- Source output remains 24,000 characters/read and 400 lines; segment admission
  remains 60,000 counted input tokens, 1,048,576 request bytes and 262,144 bytes
  for the largest encrypted item. A larger source pool grants no exemption.

Use four waves with two distinct tasks in parallel, isolated process/checkouts,
clients, state and cost ledgers. Row numbers are execution order, not dev20 indices.

| Wave | SQLFluff-1733 | pvlib-1072 |
| --- | --- | --- |
| 1 | A1 (row 1) | B1 (row 2) |
| 2 | B1 (row 3) | A1 (row 4) |
| 3 | B2 (row 5) | A2 (row 6) |
| 4 | A2 (row 7) | B2 (row 8) |

The existing `diagnostics/parallel_dev_batch.py` accepts distinct tasks per call,
so call it once per wave under one outer allocation; never submit all eight rows
to its distinct-task interface. Carry a global stop decision across waves. Fresh
requests and separate row roots are prepared externally. The execution driver is
`diagnostics/source_retention_comparison.py`; it maps each wave's local indices to
the correct task and unique native-assessment directory, and carries a stop across
all later waves. It rejects restart/resume and preserves all eight allocated rows.

## Assessment and decision

Primary outcomes are isolated registered acceptance and agreeing native assessment,
public regressions, safety, submitted patch, settled cost and elapsed time. Keep
non-submission, evaluation errors and NOT_RUN separate from graded behavioral FAIL.
The two-task denominator and every unsuccessful allocated row remain visible.

Before paid dispatch, freeze operator-only public examples and calibrate them in
the existing environments: SQLFluff must produce the complete expected SQL from
the issue; pvlib must handle timezone-aware and naive time series while preserving
the ordinary output. After the whole batch, assess submitted candidates with those
same programs. No historical patch, target line hint, operator program, hidden test
or evaluator detail enters the fresh solver input. Public PASS covers its examples
only; it does not replace isolated acceptance.

Audit actual pre-edit requests to distinguish source delivery, model use, an executed
counterexample and a changed repair decision. More retained characters, probes,
reads or successful submissions alone do not establish an improvement. Record
actual counted tokens, size-triggered handoffs and resource-limited outcomes; do
not estimate tokens from character counts or reset a budget at handoff.

A positive pilot requires at least two more accepted repairs out of four B rows
than A, no per-task success-count regression, and trace evidence that newly retained
observed source informed a correct repair. A cost/time increase above 25% requires
an explicit tradeoff decision. Even a positive pilot only supports a provisional
decision on this exposed scope. Ties, mixed correctness, non-exercised mechanism or
unresolved infrastructure censoring preserve the 24k default. No adjacent context
variant, repeated panel or full dev20 remeasurement starts automatically.

## Dispatch boundary and prepared artifacts

Stop all new admission on count, transport, billing, cleanup or identity uncertainty,
or unexplained registered/native disagreement. Already admitted calls settle and
retain their usage. Settled row-local cost exhaustion remains unsuccessful and
local. No retries, resumes, replacement tasks or automatic image acquisition.

Preparation root: `C:/pt/analyses/source-retention-option-20261006-v1`.
`comparison-proposal-v2.json` records typed requests and current task/source/dependency
identities, with `live_execution_authorized=false`. Source and dependency descriptors
are checked without model calls or Docker execution. This is not an execution-ready
environment certificate. Before dispatch, bind the final clean code/driver commit,
runtime, task and dependency hashes, local images, public calibration and validation
receipts in the actual execution packet. The current explicit user authorization
covers this exact scope; record it against that packet. Historical preparation
files remain unchanged. Execution evidence: `C:/pt/sretp02`; fresh states:
`C:/pt/sretlive01/1` through `8`. Calibration uses original sources and saved agent
submissions only in the operator process, never in the fresh solver input.
