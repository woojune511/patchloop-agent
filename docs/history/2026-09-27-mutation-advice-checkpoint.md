# Current mutation advice: N1 checkpoint preparation

Date: 2026-09-27. Offline diagnostic preparation, `official=false`.
This record does not authorize a live comparison or change runtime defaults.

## Problem and hypothesis

In the [fresh AnyIO solves](2026-09-27-anyio-fresh-solve.md), N1's first repair
depended on caller cancellation that its first probe had not measured. Its current
message recommended `replace_text`. A possible mechanism is that this recommendation
encouraged an edit before resolving that premise. Competing explanations include
the agent's causal model, continuation history, other mutation cues and randomness.
Observed action alignment does not distinguish these explanations.

The bounded diagnostic removes just that current recommendation at the saved
post-probe boundary. It does not add a task hint, mandatory observation, extra tool,
memory or budget. The existing `status-only-v1` check/submit projection does not
cover mutation advice and remains unchanged.

## Prepared change and source

Implementation: `diagnostics/mutation_advice_checkpoint.py`; execution proposal:
[contract](../../.agent/mutation-advice-checkpoint.md).

Source run: `run_dev_49efb33fc65a49a2`, turn
`turn_7477f829d6b4455681d779cbbd1802b0`, after first probe
`call_VK4F44C7vfoXSJQpCj7VFrtl` and before any edit. The source had spent $0.232537;
the displayed remainder was $0.967463, 37 model calls, 92 tool actions, four mutations
and 1,655 active seconds. These are historical allowances, not new authorization.

A is the exact captured request object. B changes only the final developer
current-state message's `completion_guidance.next_action` to null and removes
the `Use replace_text` instruction from `completion_guidance.message`. Repair
status, evidence caveat and submission conditions remain. The 22 earlier native
input items, including three opaque encrypted reasoning items, remain exact.
The earlier rendered current messages are not reinserted; prior exposure survives
through native continuation. This is not removal of all advice or all mutation cues.

Original request hash:
`sha256:480ce9c1d4fe3e30142bdb3ddc4881dd3a29cde6f64478159d5cc23cd173ca7a`.
Projected request hash:
`sha256:02c3dbabf765b46f8bc84e11dece96c98e5ef28bb0809e048fffd3b56440ce7e`.
The original count was 36,637 input tokens; no new count was performed for either
arm. These hashes bind request objects, not HTTP bytes. Historical state IDs are
retained as source metadata; B has no fabricated original dispatch/count receipt.

## Result and evidence boundary

Packet: `C:\pt\analyses\mutation-advice-checkpoint-20260927-v1`.
`packet.json` binds source identities, implementation/contract hashes, checkpoint
receipt, preserved fields and two content-addressed requests. Packet identity:
`sha256:ad2f787c814d8e1c7195d137693f4e098a4bfd5e51ece7545964542f08f5c9d1`.
`offline-validation.json` records validation and 589 unchanged protected files from
the previous fresh-solve packet and live state. Eight inherited CAS artifacts,
source journal chain, native continuation, projected public state and historical
count/dispatch binding verified. A separate one-event `dev-run-v1` preparation
journal binds the packet. Future decisions and evaluator outputs are not in A/B.

The actual preparation and validation ran with network, credential loading,
provider construction, Docker construction and registered tool execution trapped.
Model calls, new counts and tool executions were all zero. No historical search or
probe was replayed. Acceptance, safety, environment readiness for a new run and
agent efficacy remain `NOT_RUN`. Status is `PREPARED_NOT_EXECUTABLE`.

Focused validation passed 25 tests in 44.62 seconds, including synthetic native
history, packet validation, additional-field tamper rejection, unknown advice,
source/hash/CAS integrity, public-projection audit and documentation checks. The
projection audit includes a mock solve reaching isolated `EVALUATOR_PASS`; Docker
safety is not established by that mock. Ruff passed for runtime, tests and the new
diagnostic. No production runtime code or historical evidence was changed.
The full `pytest tests` suite was started, then stopped during existing seeded-run
tests because of its broader runtime; it is incomplete, not a full-suite PASS.
The completed focused group above includes the new loader/projection and mock smoke.

## Next question

Implement and test provider-free restoration and continuation before requesting
live execution. The saved pair alone cannot execute the selected action or measure
task correctness. The proposed A1/B1/B2/A2 order and $3.869852 new invocation cap
remain a design, not a paid allocation. Do not substitute a next-response-only
sampler or grant a fresh budget. Measure task acceptance/safety, regressions, cost
and time; classify unsubmitted arms as `NOT_RUN`, and inspect whether any new probe
actually tests the edit's premise. Neither additional investigation nor a changed
first action suffices to claim better problem solving.
