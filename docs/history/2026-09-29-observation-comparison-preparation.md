# Observation comparison: scoring and live execution preparation

Date: 2026-09-29. Every run is official=false; no paid execution is authorized here.

## Problem and hypothesis

The offline fork established restoration and repeated delivery, not whether a model
uses an unsuccessful observation correctly. Keeping a failure visible may improve
retention while leaving interpretation wrong or encouraging an unnecessary edit.
The next diagnostic must distinguish these outcomes before inspecting new responses.

## Frozen design and implementation

The [rubric and contract](../../.agent/observation-comparison.md) fixes the first
three new tool batches as the primary window and records retention, interpretation,
discriminating action, closure and unsupported edits separately. Directly inspected
public source can justify rejecting an invalid probe; blind patching cannot count
as success. Every row binds the target failed-probe action ID. Reviewer judgments
must cite public event/action/input/diff evidence; hidden evaluation and opaque
reasoning cannot determine the public interpretation score.

Fixed panel/order: N1A, N1B, P1B, P1A, P2A, P2B. These are three checkpoints on
two already examined tasks, all with probe setup/API/introspection failures. They
do not estimate confirmed-product-defect repair, fresh-solve rate or generalization.

`diagnostics/observation_comparison.py` adds separate prepare/collect commands.
Preparation constructs six synthetic first inputs, checks pair parity with only
catalog exposure and elapsed seconds differing, freezes content-bound controls and
performs read-only environment admission. Collection uses the existing new-usage
group ledger and ordinary registered-tool/evaluator loop. Each first count must
match the approved normalized request, and each dispatch must match its immediately
counted input with only an admitted output-ceiling reduction allowed.

Original event prefixes remain unchanged. A new executing Git identity supplies
submission provenance instead of silently reusing the parent's historical commit.
Ordinary resume, task admission, deadlines, idempotency, zero SDK retries and global
uncertainty stops are preserved. A claimed result root cannot be reused.

## Proposed invocation and evidence packet

Preparation packet root: `C:/pt/analyses/observation-comparison-preparation-20260929-v1`.
`cases.json` fixes sources/cuts/target IDs; `review-template.json` has unscored rows.
The proposed allocation is USD 3 per row, USD 18 invocation-wide, with the existing
`gpt-5.4-2026-03-05`, xhigh, 25,000 desired output tokens and repository `.env` path.
Inherited time/model/action/edit limits remain unchanged. Old funds stay closed.
At the runtime's 60K input bound, a full 25K-output call reserves at most USD 0.525
at reviewed standard rates; USD 3 covers the primary three-call token allowance,
but cannot guarantee completed investigations, useful outputs or successful repairs.

Actual input counting, provider dispatch and remote-task tool execution remain
NOT_RUN. Preparation and synthetic collection do not authorize the proposed allocation.
