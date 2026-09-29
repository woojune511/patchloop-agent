# Current-runtime observation fork rehearsal

Date: 2026-09-29. Status: provider-free diagnostic; official=false.

## Problem and competing explanation

The previous request-parity audit established a first-input difference only.
Historical envelopes cannot resume under changed runtime identity, and a one-time
projection could leak observation catalogs again after a tool result. These were
execution/delivery gaps, not evidence that retention improves repair decisions.

## Change

Added `diagnostics/observation_exposure.py` and its
[contract](../../.agent/observation-exposure.md). A fresh external diagnostic branch
retains the exact prefix, verified CAS references, candidate, action counters,
settled usage and active time. It writes a new current-runtime envelope and explicit
parent/cut/implementation provenance. No historical files or ordinary resume guard
are changed; old unused funds remain closed. Seeded tox checkpoints are excluded.

Scoped A/B projections now cover every context and assembled request, including
serialized tool-output views. A removes the structured observation catalog; B keeps
it. Raw public outcomes remain visible in both. Finite synthetic SDK responses and
declared synthetic probes exercise the ordinary runner without credentials/network
or probe-code execution. The entry point rejects real-task repair/check execution
and submission, and cannot be retried after starting.

## Executed evidence

Packet: `C:/pt/analyses/observation-fork-rehearsal-20260929-v3`.
`run.py`, `report.json`, six branch journals/envelopes/fork records, and 18 frozen
input payloads preserve the replay. N1 AnyIO and P1/P2 pyfakefs each ran A/B through
search, synthetic failed probe and stop: 6/6 AGENT_STOPPED, all 18 inputs met exposure
rules, parent journals unchanged, real provider calls and billed cost zero.

First-request comparison removes the catalog and normalizes only naturally elapsed
active-wall time. This is a plumbing parity check, not strict timing-controlled live
sampling. `validation.json` binds all 18
input hashes and verifies pair parity after normalizing only active-wall seconds.
Later synthetic probe failures
remained in B and were omitted in A without removing the original outcome.

Focused tests cover per-turn projection, frozen source/cap/implementation identity,
seeded/terminal rejection, count/transport/usage hard stops, pre-dispatch cost stop,
and reloaded gateway replay of mutation/check/probe receipts with conflicting-ID
rejection. Ordinary envelope mismatch still fails. No evaluation is performed by
this diagnostic; a separate mock smoke checks isolated evaluation.

Focused validation: 24 passed in 44.93 seconds; Ruff passed. The full fast suite
covered all 193 test files in four disjoint shards: 3,638 passed, 16 skipped,
no failures (slowest shard 43m09s). `verification.json` binds code identities,
test-log hashes and input/rehearsal receipts. Mock smoke
`C:/pt/observation-fork-mock-20260929-v1`, run `run_dev_92976185ab6d4fa1`, reached
EVALUATOR_PASS with safety NOT_RUN. Earlier packets and interrupted broad-test attempts
remain preserved. Review identified overly broad parsing of JSON source content;
the final filter restricts parsing to native message/tool-output wrappers, includes
the actual developer-state role and tests source preservation. The v2 audit caught
the missing developer role before final parity admission.

## Boundary and next question

Implemented and locally exercised does not mean live-executed or claim-producing.
Fresh agent behavior, task acceptance, Docker safety, recovery of uncertain provider
calls and general improvement remain NOT_RUN. Next decide whether a separately
bounded live diagnostic can distinguish retention failure from faulty interpretation;
these already examined tasks cannot demonstrate generalization.
