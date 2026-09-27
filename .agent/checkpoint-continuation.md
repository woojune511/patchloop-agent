# Offline checkpoint continuation

`diagnostics/checkpoint_continuation.py` extends the separately frozen
[input-pair preparation](mutation-advice-checkpoint.md) without changing that
module, contract or packet. It restores a branch and runs finite scripted SDK
responses through the existing adapter, action gateway, loop and evaluator.
This module has no credential argument or automatic paid dispatch. The separate
[live collector](checkpoint-comparison.md) shares restoration and first-input
verification, with its own admission and new-cost accounting.

## Restoration boundary

`restore(packet_path, packet_hash, output, arm)` requires a verified packet and a
fresh external directory disjoint from repository, packet and source. It copies
the completed journal prefix through the first probe batch. It excludes the old
checkpoint count, dispatch and all future decisions. Original events and embedded
artifact references remain exact; a new fork event binds their provenance.
Referenced CAS bytes are verified and copied recursively. A scoped resolver maps
only exact inherited references to those copied bytes; it does not relax ordinary
artifact checks. The original journal, envelope and CAS are never written.

A fresh base workspace comes from the envelope-bound prepared source or a local
snapshot fixture. No historical search/probe is executed. The existing gateway
rehydrates source observations and anchors, working notes, check state and mutation
state. The loop restores plans, native encrypted history, counters and deadlines.
Restored call/action/cost allowances must equal the checkpoint. Historical cost
remains baseline bookkeeping; offline receipts separate it from simulated new cost
and actual new billed cost (zero). Unknown simulated billing remains null.

The selected frozen A/B input is stored as a new prepared boundary. On first loop
entry, the naturally rebuilt A request must equal the original except for elapsed
wall time. The actual first dispatched request is the exact selected frozen input,
including its historical displayed remaining time. The active deadline continues
to spend time during local preflight and execution; it is not reset to 1,800 seconds.
Fresh source/CAS materialization precedes that continuation deadline and is setup,
not a task-solving or live-readiness measurement.

Both arms perform a new count through the adapter; the old checkpoint count is not
imported or reused. After the first decision, context construction and guidance are
ordinary runtime behavior. The proposal removes only current-message advice, not
prior exposure or all mutation cues.

The optional `supplemental_observation` argument instead selects the separately
validated [caller-information intervention](caller-information.md). Both arms retain
original guidance; only B adds the observation to its first current-state record
and matching canonical context. The fork binds the supplement hash and intervention.
Later turns use the same ordinary construction, without reinjecting the observation.

## Rehearsal and evidence limits

`rehearse(branch, ScriptedClient(steps))` is a single-use offline entry point. Each
step contains function name, action ID and arguments; responses are finite and
synthetic. The real adapter parses them and the ordinary runner executes admitted
registered actions. The journal marks the fork and rehearsal before execution.
Scoped hooks are restored even on failure; do not run branches concurrently in
one process. Historical run IDs remain source-bound, with distinct external roots.

SDK counts, usage and encrypted continuation placeholders are synthetic. Credential
loading and Docker preflight are replaced with explicit offline stubs; Python socket
connections are forbidden. The shared loop is entered after restoration rather
than through live admission. This does not test live admission, provider acceptance,
real token counts, prices, network availability or Docker isolation. Live execution
uses the separate collector and still needs a frozen manifest and authorization.

Registered visible checks and isolated evaluation use `LocalSandbox`. The submitted
manifest records a local sandbox and diagnostic identity. The inherited OpenAI
provider/envelope describes the source and wire grammar; it is not evidence of a
new live call. Historical probe receipts may remain as inherited evidence; new
probe execution is rejected, and no Docker environment is claimed ready.

Tests must cover exact first A/B delivery, restored counters/evidence, first-input
only intervention, mutation/check/finish, action idempotency, failure outcomes and
count/transport/usage uncertainty stopping before any new tool. Scripted fixture
acceptance measures plumbing and the fixture patch, not autonomous repair quality.
Actual-task restoration followed by a scripted stop leaves its acceptance and
safety `NOT_RUN`. Preserve that distinction in receipts and summaries.
