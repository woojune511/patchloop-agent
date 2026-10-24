# Stable invocation and original feedback before submission

Status: local implementation and mechanism validation, official=false.
This follow-up preserves the closed [cap-only pilot](2026-10-25-budget-live.md).
No paid solve, Docker execution, image acquisition or live quality claim is included.

## Problem and decision

The pilot passed public regression and submitted, but its original failing call
still emitted F0010. Automatic replay occurred inside the final finish request;
there was no subsequent model turn to use it. The original and candidate had the
same selected input content and normalized caller arguments, but host tracing
argv and random HOME/PYLINTHOME hashes prevented comparable completion evidence.
This matters because submission and public PASS can otherwise end the repair loop
without testing the model's hypothesis on the original caller.

The implemented intervention changes execution conditions and feedback timing.
It does not relax identity equality or introduce another independent completion
gate. The existing current-case failure gate remains authoritative. More budget
alone, a matching helper, and deleting environment identity from comparison do
not address the two observed mechanisms. Local controls can establish delivery
and identity behavior; they cannot establish that a live model will use it well.

## Implementation

- Fresh invocation v4 initializes target-visible argv before authored setup, so
  host timeout/tracing arguments do not enter the callable. Explicit authored CLI
  argv is preserved. `reproduction_workspace()` exclusively creates a stable path
  under the fresh sandbox cwd; fixtures and selected HOME/cache variables can be
  set there explicitly. Occupied paths are neither reused nor deleted. Selected
  actual environment hashes and input contents remain equality conditions.
- After an accepted edit, the runner replays acquired baseline-failure cases
  before the next model input. Selection uses the complete original-case set,
  independent of the latest helper, saved program or bounded display. It shares
  the existing case/root/diff action identity and executor with finish.
- Current observation and execution status are retained separately from
  comparability and bounded condition-difference paths. Same-condition failure
  remains REFUTED; changed/incomplete conditions remain UNKNOWN. Host child
  results are projected from the journal, without invented native tool outputs.
- New early work uses the minimum completion reservation; it is not charged as
  an optional model probe. Unfunded work stays pending for finish fallback.
  Already started children reconcile regardless of new-work admission. Protected
  tool forecasts account for original replay after each future accepted repair.
  Host replay adds no model call; monetary minimum admission still guarantees
  only the successful successor path, not recovery from a wrong repair.
- Tool contract v54 records the change. Frozen invocation v1/v2/v3 observer and
  program bytes remain unchanged. The v4 observer is 7,617 characters; a maximum
  entrypoint wrapper is 7,962, within the existing 8,000 host-character allowance.
  No Docker runner or image change is required.

## Local design and observations

Pre-registration: `C:/pt/preedit25-local-v1`, journal `run_dev_preedit25local`.
Plan hash: `sha256:ddd0e5c0e2c6f963bd3953206bc49ac2241b4ee0c3d4e7747b0b6ff9c40e393f`.
Base commit: `d797158db3704f451f53ff7844b6a7c8efa741b3`.
The frozen toy failure, wrong comment-only candidate and normal control are shared.
The provider is scripted mock and the probe backend executes trusted local Python;
no network/provider request is permitted. Identity OFF uses the actual v3 observer;
ON uses v4. Host launch arguments change after the baseline. Feedback OFF disables
only the new hook; ON exercises the real pre-model scheduler and journal projection.

| Stable identity | Early feedback | First model input after the wrong edit |
|---|---|---|
| OFF | OFF | Pending; no current original observation |
| ON | OFF | Pending; no current original observation |
| OFF | ON | Original bug observed, changed argv, unverified |
| ON | ON | Original bug observed, same conditions, refuted |

Each early-ON cell executes the exact frozen original program once, including the
normal control. Its replay completion precedes the next dispatched mock turn.
The matrix stops at that input so timing is measured before checks or finish;
registered checks are NOT_RUN in these four cells. This narrows the planned
fixed-visible-check control: a separate integration control executes a wrong edit,
helper PASS and registered-check PASS, then confirms early original refutation and
no second replay at finish. The two evidence scopes are not pooled as repair rates.

Separate controls execute actual line tracing ON/OFF with the stable workspace,
HOME/cache hashes and explicit CLI argv. Changed input, selected environment,
cache path and authored CLI argv remain incomparable. Occupied workspace paths
are preserved. Positive repair reaches isolated mock evaluation; mutation-result,
child-admission, child-result, child-completion and finish-result crash boundaries
recover without duplicate durable probe execution. Exhausted admission launches
no new replay and grants no verification. One remaining final model slot can still
use the already reserved replay and finish without an optional-probe allowance.

## Validation and limits

Initial integration: 32 passing feedback/finish/resource checks. Identity owner:
49 passing workspace, argv, observation and source-size controls. Focused local
controls: 31 passed in 22.389 seconds, below the two-minute owner limit. Ruff passed.
The first quick run passed 280 checks, including isolated mock evaluation, with
two maintenance failures: an intentionally changed guidance hash and the guide's
byte limit. Both were corrected. The final focused/maintenance group passed all
37 checks in 22.341 seconds, including both failed quick nodes. The other 280
quick nodes were not rerun after these test-snapshot/documentation-only fixes.
The quick run took 46.744 seconds; Ruff passed again after the corrections.

Final runtime hash: `sha256:2d1a7111c4fb45675cbb415df884c96460fbc138eca2bec06c6a06f747fa5dce`.
Result artifact: `sha256:6bf959033d4de2039a539c8823224531c75209d228dae8d130ad64440d0c8473`.
Readable local result: `C:/pt/preedit25-local-v1/results.json`; final test XML:
`C:/pt/preedit25-local-v1/final.xml`. The quick XML preserves its initial failures.
Runtime identities for individual cells and the implementation commit receipt
are recorded separately; earlier development checks are not relabeled as final runs.

Runtime hashes, exact local journals, selected next-model public inputs, test XML
and final validation receipts are retained in the external append-only journal
and content-addressed artifact store. Historical pilot artifacts were not changed.

The evidence supports stable host-controlled conditions and pre-submission
feedback delivery in these local cases. It does not establish task-level repair
success, broader generalization, or live-model adoption. The model must actually
use the fresh workspace for selected random environment paths; arbitrary random
HOME/cache setup correctly remains incomparable. Bounded line collection is not
full branch coverage. A future authorized fresh solve must test whether the
model revises its original-call repair hypothesis from the delivered observation.
