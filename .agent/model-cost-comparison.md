# Mini/full completion-cost comparison

Preparation only. No paid execution is authorized by this document.
Driver: `python -m diagnostics.model_cost_panel` (freeze, preflight, run).
Reuse the existing fresh-row driver and normal runner; no policy or prompt patch.

## Frozen design

Six registered dev-train tasks, ordered as below. Prior outcomes select three
successes and three failures across four repositories; they are not control results.
No C2/SQLFluff-1733 or pydicom-1413 continuation or diagnosis is reopened.

| Case | Task suffix after swebench-lite-dev- | Prior selection stratum |
| --- | --- | --- |
| marshmallow1343 | marshmallow-code-marshmallow-1343 | success |
| pydicom1694 | pydicom-pydicom-1694 | success |
| astroid1196 | pylint-dev-astroid-1196 | success |
| pydicom1139 | pydicom-pydicom-1139 | failure |
| astroid1268 | pylint-dev-astroid-1268 | failure |
| sqlfluff1517 | sqlfluff-sqlfluff-1517 | failure |

mini = gpt-5.4-mini-2026-03-17; full = gpt-5.4-2026-03-05.
Both: xhigh, desired 25,000 output tokens; 40 model calls, 100 actions,
4 accepted edits, 1,800 active seconds. Fresh base, native state and cost ledger
for every row; two repetitions per task/model, 24 rows total. Credential file:
C:/Users/geonj/Documents/PatchLoop/.env. It is not read during offline input capture.

Per-row cap USD 3 for either model; per-task four-row cap USD 12; per-model
twelve-row cap USD 36; invocation cap USD 72. Unused amounts are not transferred.
These are equal dollar limits, not equal token allowances: prices and actual token
use affect admission under the same per-call-v1 rule. Costs are provider-reported
usage at frozen registry rates, not admission reservations or historical spending.
Input/cached/output USD per million: mini 0.75/0.075/4.50, full 2.50/0.25/15.00.
Official model pages reviewed 2026-10-04:
[mini](https://developers.openai.com/api/docs/models/gpt-5.4-mini),
[full](https://developers.openai.com/api/docs/models/gpt-5.4).

Order: all six tasks in repetition 1, then all six in repetition 2. First repetition
uses mini/full for positions 1,3,5 and full/mini for 2,4,6. Second reverses each pair.
Both models use segmented-v1, result-or-size-v1, brief-v1, probes enabled with
policy none, repair-recheck, protected-v1 and per-call-v1. Saved-program recheck
stays off. Prepared source and available SQLFluff probe dependencies are identical
within each pair. Historical patches, operator programs and solutions never enter
solver input. Missing existing environments stop preparation; no pull/build.

## Validation and execution

Freeze records every request, task/public hash, model/runtime identity, prepared
descriptors, environment identities, implementation commit, pricing and validation.
Validate configuration parity, fresh roots, original first-input assembly, and
aggregation offline; synthetic results are not model-performance evidence. Freeze
only after tests and mock isolated evaluation pass on the final implementation.
The offline receipt binds its evidence files. The live root must not exist.

`freeze --root <external-root> --live-root <fresh-live-root> --validation <receipt>`
writes manifest.json and result-format.json. `preflight --root <root> --packet-hash
<hash>` verifies existing environments. A separately recorded authorization.json
must have approved=true, the exact packet_hash and the user's human_message before
`run --root <root> --packet-hash <hash>` is allowed. Never synthesize that approval.

Zero SDK retries. No resume, replacement, budget/time expansion or instructions
changed after outcomes. Count/transport/billing/cleanup/identity uncertainty stops
the allocation. No automatic per-failure diagnosis or follow-up run is created.

## Results and operating decision

Preserve each row's final original acceptance (PASS/FAIL/ERROR/NOT_RUN), submission
flag, safety, terminal, settled cost and end-to-end elapsed process time, including
evaluation. Distinguish unsubmitted attempted runs from rows never started. Summaries
include counts per model/repetition, total cost/time and total cost per acceptance
(null for zero successes or uncertain billing). Planned denominator is 12 per model.
Incomplete or uncertain batches cannot support model selection. Both repetitions
remain a small, development-exposed panel, not a general quality estimate.

Choose mini for this panel only if both repetitions have at least as many accepted
tasks as full, with at least one mini success overall, no more unsubmitted runs,
lower total cost, elapsed total <=125% of full, and PASS safety for all submissions.
Otherwise keep full and review the aggregate quality/cost/time tradeoff. Acceptance
is primary; a lower cost per acceptance alone cannot hide lost completions. The
outcome does not automatically change CLI defaults or initiate task diagnoses.
