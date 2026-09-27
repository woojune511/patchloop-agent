# First failed-check information comparison preparation

## Problem and hypothesis

B1's first patch in the closed caller-information comparison stalled during
fixture cleanup. A later operator probe measured cancellation order and task/future
states on that exact candidate. The new question is whether supplying those raw
observations helps the agent repair the failure with its remaining resources.
The prior one-line rescue and B2 success are operator findings, not treatment input.

## Intervention and fixed controls

Source: `C:\pt\callerinfo0927a\B1`, run `run_dev_49efb33fc65a49a2`, next turn
`turn_6a305cdb662f49bfb79efd3ac5004724` after the first lifecycle check failed.
Candidate diff: `sha256:98f2a7addca143126102a85752908891b2e33fbd0330851dca55bb80c4feb243`.
A retains the exact saved request. B adds traced/untraced program and stdout/stderr
from B1 only in `operator_caller_observation`. No later patch, ablation, interpreted
causal verdict or evaluator information enters the supplement. Both arms retain
original guidance and prior exposure; subsequent turns do not reinject the field.

The new four-row order is A1/B1/B2/A2. Exact public dev-train task:
`tasks/dev-train/anyio-interrupt-runner-cleanup-v3/public.yaml`;
model `gpt-5.4-2026-03-05`, xhigh, 25,000 output tokens; credential path
`C:\Users\geonj\Documents\PatchLoop\.env`. Each row inherits $0.5032625 spent,
leaving $0.6967375, 35 model calls, 90 tool actions, 3 accepted mutations and 1,507
shown active seconds. Proposed invocation-wide new cap: **$2.786950**.
Old allocations remain closed. New paid execution requires exact fresh approval.

## Restoration changes and validation

The new packet loader selects and verifies the failed candidate and saved input.
The continuation restores the completed mutation without executing old actions.
Recreating a native segment initially changed its artifact-bound ID and failed the
first-input identity check. Retaining the existing segment before the target count
fixed this while keeping the old target count/dispatch excluded. Nested synthetic
forks also exposed distinct artifact metadata for identical CAS bytes; reference
mapping now keys full metadata instead of conflating references by path.

Focused validation: 33 tests passed in 67.223 seconds, including both nested-fork
arms, first-input-only injection, corrupt reference/preimage rejection, observation
exclusion, existing collector uncertainty handling, ordinary repair/check/finish
and documentation bounds. Ruff passed. Report:
`C:\pt\validation\cleanup-info-final-0927c.xml`.
Mock smoke: `C:\pt\cleanup-information-smoke-0927a`,
`run_dev_cb9725e752a547e3`, EVALUATOR_PASS; safety NOT_RUN.

Real-task scripted A/B restoration each retained 90 historical events and dispatched
one exact frozen request to the fake SDK before scripted stop. This is restoration
and delivery evidence, not autonomous repair. Source journal bytes remained unchanged.
Read-only environment admission returned READY with existing images and dependencies.
No Docker start/pull/build, new probe, input count API or paid model call occurred.

## Frozen evidence and next decision

Packet and rehearsals: `C:\pt\analyses\cleanup-information-checkpoint-20260927-v1`.
Packet hash: `sha256:7dd9ad90ea7c47990b8184a00aafa911a7e514f5576720ca0ec25ac66a2a57d1`.
The separate collector manifest will bind the committed implementation and a fresh
`C:\pt\cleanupinfo0927a` output. Paid comparison, new task acceptance and safety
remain NOT_RUN. The next decision is authorization of this exact four-row allocation.
No default prompt policy or runtime/task change is adopted.
