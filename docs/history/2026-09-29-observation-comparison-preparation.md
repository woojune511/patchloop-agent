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
N1's parent used GPT-5.4/xhigh; P1/P2 used GPT-5.4-mini/medium. Both arms use the
selected GPT-5.4/xhigh baseline, with parent settings recorded separately. These are
current-baseline forks, not same-model resumes. Provider compatibility with inherited
cross-model continuation remains NOT_RUN; failure stops all remaining rows.
The first preparation stopped before provider work: an overly strict parent-model
check rejected P1/P2. After separating provenance from the executing baseline, the
`plan/` packet passed input parity but rejected every environment because admission
compared the current probe profile to the historical profile. Image digests matched;
profile hashes differed. The corrected collector binds parent and executing probe
identities separately and checks the latter, as the new runtime envelope does.
The earlier packet remains preserved and is not the execution manifest.
At the runtime's 60K input bound, a full 25K-output call reserves at most USD 0.525
at reviewed standard rates; USD 3 covers the primary three-call token allowance,
but cannot guarantee completed investigations, useful outputs or successful repairs.

Actual input counting, provider dispatch and remote-task tool execution remain
NOT_RUN. Preparation and synthetic collection do not authorize the proposed allocation.

## Preparation result and local validation

The final `plan-v2/manifest.json` is bound by
`sha256:a34406b480fa600b165989146b53bcf0909491fc37114aa4e9c9909d0be544b1`.
All six synthetic first requests passed pair parity; all six read-only preflights
returned READY. `identity-recheck.json` confirmed unchanged source/control hashes.
These are preparation results, not provider compatibility or task-solving evidence.
The earlier `plan/` packet remains a failed-preflight record, not a live allocation.

Matched remaining allowances before new execution overhead (each A/B pair):

| Checkpoint | Model calls | Tool actions | Accepted edits | Active seconds |
| --- | ---: | ---: | ---: | ---: |
| N1 | 34 | 89 | 3 | 1484.839 |
| P1 | 12 | 62 | 1 | 1511.744 |
| P2 | 29 | 89 | 4 | 1690.161 |

Every parent has a 1800-second total active limit; elapsed time stays spent.
The first-input hash normalizes displayed remaining seconds to zero for parity;
zero in the saved normalized request does not mean the run's allowance is zero.

Focused validation initially passed 26 tests in 66.35s. After real-source admission
corrections, the collector's nine tests passed in 121.80s while the full suite was
running concurrently; this contention run exceeded the two-minute target. The final
collector recheck passed all nine in 85.14s after concurrency decreased, meeting the
two-minute target. Ruff passed. Mock run `run_dev_d576c828c49540a7` under
`C:/pt/observation-comparison-mock-20260929-v1` reached EVALUATOR_PASS with
task acceptance PASS and safety NOT_RUN, cost zero.

The full suite covered 194 files across eight disjoint shards: 3,646 passed,
16 skipped, no failures; longest shard 2222.28s (37m02s). It started before the
real-source admission corrections; the final nine-test collector recheck above
covers those changes, including the new executing-profile test. Documentation
layout/link checks also passed (five tests). Full-suite logs, `pytest-results.json`
and `pytest-summary.json` are stored beside the preparation packet.

Actual model input counts and dispatches: zero. Live interpretation/action effects:
NOT_RUN. Next executable proposal is exactly the final six-row manifest at USD 18;
it still requires new paid authorization and a fresh per-row preflight.
