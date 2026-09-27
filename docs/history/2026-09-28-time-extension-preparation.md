# Post-check time extension preparation

Date: 2026-09-28. official=false; new paid execution NOT_RUN.
Follows [matched result](2026-09-28-expectation-review-results.md).

The user requested continuation with the harness timeout relaxed. Normal resume
rejects changed envelopes, and the last source call has unknown billing. The new
[diagnostic contract](../../.agent/post-check-extension.md) instead freezes the
completed public prefix before that call, preserving the entire source journal
and its unresolved billing. This is a separate invocation, not reconciliation of
the old request or a replacement A/B outcome. A fresh call may incur an additional
charge even if the old unknown request was billed.

The selected boundary is after the final passed regression, before count sequence
452 and unresolved dispatch 456. The prefix includes sequence 451. Three accepted
mutations are restored in order with exact file/diff hashes; prior actions/checks
are not replayed. The actual final patch remains
`sha256:003d549bab52d602d4efb2c0c80b7002c4ab587da5c3fb086ea1a2977351bb50`.
The current state keeps 13 model calls, 61 tool actions and one accepted mutation
remaining. Active limit changes from 1,800 to 5,400 seconds; the frozen first state
has 3,608 seconds remaining. This is a generous finite limit, not infinite timeout.
Only current remaining time and fresh cost allowance change; other state/history,
model and registered tools persist. No operator counterexample output or new cue is
injected. Both inherited advice removal and unknown-source metadata are preserved
in their appropriate solver/operator boundaries.

The proposed live invocation is original-toqito-1538 dev-train,
gpt-5.4-2026-03-05 xhigh, max output 25,000, existing PatchLoop/.env, one continuation,
fresh cap $3. It requires separate cost authorization. New uncertainty stops work;
zero SDK retries and single-use roots remain. Runtime defaults are unchanged.

## Executed offline evidence

- Packet: `C:/pt/analyses/time-extension-checkpoint-20260928-v1/packet.json`;
  hash `sha256:0d1388dfad6da0cd60a24074b6cdbb1c02cbcd5dd1cad04acb88262ef8edb880`.
- Actual-source rehearsal: `C:/pt/analyses/time-extension-rehearsal-20260928-v2/receipt.json`;
  synthetic one count/response, AGENT_STOPPED, exact first-state restoration, three
  inherited mutations, no repeated historical probes and zero live cost.
- Earlier v1 rehearsal used a malformed scripted stop argument, triggering a protocol
  correction and exhausting its finite fake SDK. Retained as synthetic failure only;
  no real provider call or charge occurred. v2 corrected the script, not the runtime.
- Focused extension tests: 3 passed (normal/count/transport, separate accounting,
  fresh allowance, unknown source retained, single use); review continuation and
  documentation regression group: 9 passed. Ruff passed. Full suite not run.
- Ordinary mock `run_dev_54df22ff49c74970` at
  `C:/pt/runs/time-extension-mock-20260928-v1`: isolated EVALUATOR_PASS,
  safety NOT_RUN, zero cost. Offline restoration is not a solving result.

Next freeze the implementation-bound live manifest and check existing environments,
then obtain the exact fresh cap authorization before any provider count/generation.
The original comparison remains closed with unknown final total and B NOT_RUN.
