# Completion-advice continuation rehearsal

Date: 2026-09-28. `official=false`; live agent efficacy NOT_RUN.
Follows [offline pair preparation](2026-09-28-completion-advice-preparation.md).

## Change

Added an offline-only scoped hook around input preparation. The ordinary first-state
restoration still checks the unmodified baseline. The hook then transforms the saved
authoritative input and each subsequent boundary before input-token counting. Context,
input artifacts, native-history metadata, sizes and request hashes are rebound together.
Both baseline and selected identities are recorded in the external hash-chained journal.
Previously transformed boundaries are reused; old preparation events are not edited.

The same two completion-guidance fields change as in the offline pair. All tool
eligibility, public evidence and resource rules remain ordinary runtime behavior.
This hook is accessible only through a finite scripted rehearsal, not the live
collector or normal resume. Runtime source/defaults are unchanged.

## Validation scope

Integration scenarios exercise check-to-ready, another inspection while ready,
count failure before dispatch, count-triggered segmentation and an additional
accepted edit returning to unchecked status. Each counted input retains advice
removal; receipts precede counts; dispatched inputs match canonical public context.
Input-count API payloads omit generation-only fields by design; tests compare that
projection and separately verify dispatched canonical inputs. An initial fixture
reused a historical mutation action ID and correctly hit ActionConflict; its second
mutation now has a distinct ID. Recovery/idempotency rules were not weakened.

The actual toqito post-edit checkpoint also restored and dispatched one scripted
stop through the hook, with its exact original candidate hash. This used no new
check, probe, evaluator or live provider call. It verifies first-boundary delivery,
not autonomous behavior or multi-step toqito correctness.

- Durable rehearsal: `C:/pt/analyses/advice-continuation-rehearsal-20260928-v1/receipt.json`.
- Receipt journal: `runs/run_dev_advicerehearsalreceipt.jsonl` under that root.
- Restored branch: `fork`; original run `run_dev_33068b6e257f423a`.
- Synthetic integration fixtures: `C:/pt/tmp/advice-loop-0928-v3`; these are local
  test data, not durable evaluation results.

The focused integration/projection/document group passed 12 tests within two minutes;
Ruff passed for runtime, tests and both advice diagnostic modules. Ordinary mock smoke
`run_dev_ec69c7bedf2044fc` reached isolated EVALUATOR_PASS, safety NOT_RUN, cost zero
under `C:/pt/runs/advice-hook-mock-20260928-v1`. The full repository suite was not run.

## Limits and next step

Unsupported guidance stages or changed prose stop before counting. In particular,
a failed visible check that requires repair is outside this initial ablation; the
hook does not silently reinstate baseline recommendations. Such interruption would
make the experiment incomplete, not prove the agent cannot repair. A successful
additional edit is supported because it returns to the known check-required state.

Before live use, decide whether to keep that bounded stop or explicitly extend the
factual projection to repair/source-needed states, then integrate a manifest-bound
collector and rerun uncertainty controls. No live manifest or paid allocation was
created. Do not infer efficacy from synthetic actions or adopt the policy by default.
