# isort continuation: implementation and provider-free verification

Date: 2026-10-15. Follows the immutable [design](2026-10-15-isort-uptake-design.md)
and [public position control](2026-10-15-isort-control.md). No paid model, count,
metadata or credential access; no Docker start/pull/build, isort diagnostic,
registered target check or target evaluator execution. All runs are official=false.

## Question and fixed decision

The design asks whether one continuation uses a supplied public observation to
qualify keyword-only placement and preserve original comment ownership. This
preparation establishes execution integrity only. It does not measure model
uptake or isort repair success. The original packet, expectations, rubric,
checkpoint and runtime defaults remain unchanged.

The existing SQLFluff bridge imports a saved model-authored probe decision and
executes it. This isort continuation instead delivers already executed operator
observations, permits two further accepted edits, and retains only 281 seconds
of solver time. Reusing the SQLFluff seed import or its 330-second solver reserve
would violate this design. Reuse the prefix restorer, registered runtime loop,
single-use cost admission, probe lineage handling and inert transport guards;
keep the differences in three new diagnostic modules.

## Implemented seam

- `diagnostics/isort_uptake_checkpoint.py` validates the frozen packet and all
  21 bound inputs, restores through event 338 before prepared request 339, and
  preserves source, policy, opaque native history, counters and settled billing.
  The new totals are 26 generations, 56 actions and four accepted edits. New
  funds are USD 3.50; historical unused funds are not reopened. Restoration and
  preflight consume applicable deadlines. Old probe lineage remains historical;
  the current profile must match both supplied operator receipts.
- `diagnostics/isort_uptake_execution.py` adds the exact observation packet to
  the first public state, validates its source currency and unchanged native
  item ordering, and counts that exact request. There is no fabricated model
  tool call, seed rerun, extra repair instruction or repeated reminder. After
  the first decision, ordinary segmentation, source retention and notes apply.
  The 60,000-token fit remains unmeasured until a separately authorized fresh
  count; synthetic counts do not establish live fit. Oversize first input stops
  after one count without pruning/replacement.
- `diagnostics/isort_uptake_collection.py` prepares a manifest binding committed
  code, frozen inputs, runtime, current environment identity and mock evidence.
  Its CLI cannot collect. The separate funded function requires the exact
  manifest hash, USD 3.50 approval, fresh official price review, read-only
  environment readiness and one exact-model metadata read, with zero retries.

Six counts can fund six matching generations with the full 25,000-output-token
reservation. The sixth dispatched response still settles; returned actions
require their own time and action admission. Two accepted edits forbid a third
edit but permit remaining reads, checks and finish under the unchanged runtime
policy. Each parallel read and automatic check consumes one action. Optional
reads can close earlier under the ordinary completion budget; the experiment
does not widen those gates. Automatic recheck applies after repairing a current
failed registered check, not after every edit.

Solver time is bounded by inherited active time and 281 seconds from invocation
start. Whole invocation time is 720 seconds, including preparation and review.
Only actual submission permits a single 30-second public oracle followed by one
330-second existing isolated evaluation. The terminal phases cannot start a new
model turn. A normal oracle behavior FAIL still permits isolated evaluation;
setup, identity, timeout, truncation or cleanup uncertainty stops assessment.
Oracle exit zero alone is not P PASS: the four explicit behavior records must
pass, a new allowed source change must remain, and unchanged registered checks
must have fresh PASS receipts on that exact submitted diff.

## U review order

Before either terminal assessment, the connector seals a public-only packet
containing the task, supplied observation, public actions/notes and final patch.
A semantic reviewer supplies U and public citations; no paid judge or keyword
classifier is added. A conditional repair can be PASS. Correct code without
observable linkage stays NOT_OBSERVABLE. Resource exhaustion alone is not FAIL.
The code checks evidence linkage, not the semantic truth of the reviewer's prose.
The inert reviewer used by rehearsal does not supply model-quality evidence.

For a future authorized collection the default reviewer writes
`public-review-ready.json` in the new invocation root and waits for one
`public-grade.json` within the same 720-second deadline. Inspect only the bound
public packet and frozen grading rubric. Publish the completed JSON atomically:

```json
{
  "review_hash": "sha256:<public packet content hash>",
  "U": "NOT_OBSERVABLE",
  "reason": "Concrete public evidence and semantic explanation.",
  "public_event_sequences": [],
  "observation_case_ids": []
}
```

PASS requires specific observation case IDs and public explanation plus new
accepted-edit event citations. FAIL requires affirmative public evidence.
NOT_OBSERVABLE does not require invented citations. This is the predeclared
grading step, not a new approval, extra inference, retry or resume. A missing,
invalid or late grade stops terminal assessment. The grade is journalled before
the oracle and isolated evaluator; later verdicts do not revise U automatically.

## Verification and evidence

The focused tests use finite synthetic SDK responses, network denial and an
inert local CSV repository. They exercise exact first-input delivery, current
read/edit evidence, unchanged opaque history, ordinary subsequent segmentation,
two edits and third-edit rejection, failed-check automatic recheck, fresh final
regression and real local fixture submission/evaluation. Other cases cover
sixth-call completion, discarded counts, exact request/count binding, full-cost
reservation, late usage settlement, parallel-read accounting, deadlines,
malformed responses, count/transport/billing uncertainty, U citation ordering,
terminal behavior failure versus infrastructure uncertainty, and funded-entry
scope/readiness rejection using inert doubles.

The real checkpoint rehearsal uses only restored-source read and stop actions:
two synthetic counts/generations, one read and one stop, zero new accepted
edits and AGENT_STOPPED. Operator receipts are delivered, not rerun. Local CSV
EVALUATOR_PASS is connector evidence; it is not isort acceptance or safety proof.

Focused validation: **48 passed in 91.65 seconds**. Full provider-free suite:
**4,763 passed, 19 skipped in 1,061.99 seconds** with four workers. Ruff and the
five documentation-layout tests passed. Standalone mock smoke reached
EVALUATOR_PASS with safety NOT_RUN and zero provider cost. Real execution/probe
test opt-ins were unset. All production runtime bytes and the 21 frozen input
files were rechecked unchanged.

Final evidence is outside the repository:

- `C:/pt/isortbridge01/result.json` and `runs/run_dev_isortbridge.jsonl`:
  final fixed-checkpoint read/stop rehearsal and hash-chained provenance.
- `C:/pt/isortbridgechecks01/validation.json`: focused tests, Ruff, suite and
  standalone mock-smoke results, with source/evidence hashes.
- `C:/pt/isortbridgeready01/manifest.json`: exact committed execution identity
  and unchanged caps. `paid_authorized=false`; proposed live output
  `C:/pt/isortuptakelive01` remains unused.

During implementation, an initial inert script omitted the inherited public
turn-decision object and stopped with PROTOCOL_VIOLATION; a later rehearsal
completed read/stop. Early fixture tests assumed unrestricted follow-up reads
and recheck after every edit; those scripts were corrected to match existing
runtime policy. A terminal connector Path conversion error was corrected before
fixture evaluation passed. These were provider-free integration failures, not
model outcomes. Debug roots `C:/pt/isortbridgedebug01` and `02` are preserved;
the final manifest binds only the final verified implementation and rehearsal.

The runtime and all frozen evidence remain unchanged. Model uptake, isort P/I,
live environment readiness and general performance gain remain NOT_RUN. This
work makes the previously fixed experiment executable and reviewable; it does
not justify adopting a prompt, tool, memory, pruning or workflow change.
