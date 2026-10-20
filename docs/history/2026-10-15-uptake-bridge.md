# Frozen uptake continuation connector

Date: 2026-10-15. Implemented and provider-free tested; no paid execution authorized.
Every artifact remains official=false and claim-ineligible.

## Question and scope

The [frozen design](2026-10-15-uptake-design.md) asks whether the model revises its
L036 preservation premise after its own diagnostic disconfirms it, then submits a
correct repair. Selection of a useful diagnostic alone does not answer that question.
This work implements the connection needed to test it, without sampling responses,
executing either SQLFluff probe, or running a SQLFluff evaluator.

Keep the original B1/B2 samples, prompt, programs, row order, budgets and grading.
The corrected [B1 grading](2026-10-15-pre-edit-grade.md) remains authoritative:
a later ancillary assertion is not a veto on a usable CTE observation.
No runtime/default adoption or quality improvement follows from these mocks.

## Implementation and compatibility findings

- [Checkpoint import](../../diagnostics/uptake_checkpoint.py) verifies the frozen
  plan, 74 prior bindings, runtime, sample, exact arguments and ordered encrypted
  continuation. It copies the settled parent prefix before event 364 and restores
  the third-edit candidate. The imported decision consumes one historical model
  slot and its recorded time; it makes no count/dispatch and adds no new charge.
- The generic restoration helper omitted the parent's `thin` policy. This connector
  supplies it explicitly before writing the new envelope. It tightens the inherited
  counters instead of resetting edits, actions or time. Existing helpers and runtime
  source were left unchanged.
- The managed-history grammar accepts JSON state records, whereas frozen B adds a
  trailing developer instruction. The connector hashes the complete wire input and
  that exact instruction, validates the remaining history with the normal validator,
  and restores the instruction verbatim on every request. It does not insert it into
  quoted state or duplicate it across handoffs.
- A normal result boundary would archive the imported response before its first
  continuation. The frozen first-delivery requirement therefore needs an explicit
  import seam: deliver the saved native prefix, ordered response and matching receipt
  before allowing a result handoff. Once a new decision consumes that exchange, the
  existing result-or-size policy resumes. An oversized first exchange stops the row;
  it is not silently substituted with a different input. This seam is confined to
  the experiment, not a new runtime context policy.
- [Execution](../../diagnostics/uptake_execution.py) dispatches the unchanged saved
  probe through the registered gateway, retains its raw receipt, and gates new counts
  on usable disconfirmation. It checks the printed target, complete B2 CTE output,
  or the exact B1 CTE assertion frame as applicable. Missing necessary output,
  invalid setup and no contradiction stop the row. A later YAML assertion does not
  invalidate an earlier CTE counterexample. Operator gate prose never enters context.
- Actual submitted patches alone reach the frozen public oracle and existing isolated
  evaluator. Both use the submitted diff. A public review packet is sealed before
  private evaluation, with no private verdict or encrypted reasoning contents in it.
  Stop/resource outcomes retain a separate final diff without inventing a submission.
  Terminal evidence cannot trigger another model turn or edit.
- [Collection](../../diagnostics/uptake_collection.py) binds the committed executor,
  frozen scope, rehearsal and fresh output location. Its CLI only prepares a manifest.
  The separate paid entry point requires the exact manifest hash, USD 7 cap and fresh
  official price review; it checks existing images/dependencies and performs at most
  one model metadata read. It cannot start Docker, pull/build images, retry a row,
  resume an interrupted call or substitute a sample/model. Private verdicts are
  withheld from its automatic summary pending public trace grading.

## Preserved bounds and stop behavior

| Bound | Enforcement |
| --- | --- |
| B1 then B2, once each | Fresh output root; immutable imports; single-use row marker |
| Six new counts and six generations per row; twelve each overall | Count admission before opening another count; discarded counts consume the cap |
| 60,000 input; fixed 25,000 output | Exact count-to-dispatch binding; no ceiling shrink to fit money |
| USD 3.50 per row; USD 7 overall | Full uncached reservation against both ledgers; no transfer or historical rebilling |
| Eighteen actions per row including the seed and automatic checks | Tightened normal runner/gateway counters; inherited action IDs and recovery unchanged |
| One remaining accepted edit | Inherited mutation count retained; no reset |
| 600s solver, 330s evaluator, 30s final public oracle, 2,100s invocation | Inherited solver limit intersected with the new limit; phase deadlines and invocation bound |
| Zero retries, correction calls, paid compactions/judges | Existing zero-retry adapter, zero recovery allowance, fixed segmented policy |

A response already dispatched is settled at the call/time boundary. Returned tool
actions still obey action/time limits. Usage outside the admitted token/cost bounds
stops all remaining work, even if cached-input savings would hide an output overrun.
Ordinary settled failure, malformed response or lack of exposure stops only that row.
Count, transport, billing, continuation, identity, evaluator infrastructure or cleanup
uncertainty stops the invocation and preserves B2 as NOT_RUN when applicable.

## Evidence and limits

Final fixed-sample rehearsal: `C:/pt/hypbridge04/result.json`, with append-only
`runs/run_dev_uptakebridge.jsonl` and independent B1/B2 fork journals.
Both imported samples reach their synthetic diagnostic receipt, a synthetic read and
stop. Each uses two simulated counts/generations and three actions, including the seed.
Both preserve the candidate hash
`sha256:59679012118d519810c25430eb177c6fe0fb5480b986b452b6c2e8bd676d2987`.
Historical plus simulated cumulative counters are not new API usage.

Actual provider/count/metadata calls, credential reads and billed cost are all zero.
The simulated cost arithmetic is USD 0.0011 per row, USD 0.0022 total, clearly separated
from billing. Synthetic stdout is labeled; it is not an observed SQLFluff result.

Development rehearsal `C:/pt/hypbridge01` stopped before any SDK request because the
first native prefix was lost; B2 stayed NOT_RUN. `C:/pt/hypbridge02` and
`C:/pt/hypbridge03` verified subsequent connector revisions. All earlier evidence is
retained; these were free connector debugging runs, not additional model samples.
The original design, grading and paid-run artifacts remain byte-identical.

[Execution tests](../../tests/test_uptake_execution.py) cover the input/receipt link,
persistent instruction, inherited budgets, token/cost/call limits, settlement at the
boundary, source/continuation corruption, exposure cases and row/global stops.
A separate local CSV fixture makes one source edit, runs unchanged public checks,
submits, and reaches the ordinary isolated evaluator. Its oracle receipt is synthetic;
its acceptance does not establish SQLFluff correctness. [Collection tests](../../tests/test_uptake_collection.py)
use inert key, metadata and executor doubles to test exact approval, one metadata
attempt, no retry and private-verdict withholding. No test contacts the provider.

Validation: 34 focused tests passed in 26.89s; full suite 4,715 passed / 19 skipped
in 977.64s with four workers. Ruff and staged diff checks passed; documentation
layout checks passed (5). The standalone CSV mock smoke reached EVALUATOR_PASS,
with safety NOT_RUN and zero provider cost, under `C:/pt/uptake-smoke01`.
The final external root records validation and the unchanged evidence hashes.

## Decision and next boundary

Keep the runtime baseline and the frozen experimental design. The connector's
provider-free path is tested; actual diagnostic exposure, model uptake, final SQLFluff
repair and acceptance remain NOT_RUN. The small local fixture does not settle whether
one remaining edit is enough for the real task.

Preparation writes `C:/pt/hypbridgeready01/manifest.json` after the implementation
commit. It is a reviewable execution identity, not authorization. Before any later
paid collection, obtain its exact approval and recheck official prices, exact model
availability and the existing pinned environment. No subsequent experiment, prompt
revision, extra sample or budget transfer is authorized by this record.
