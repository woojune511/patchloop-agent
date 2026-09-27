# Offline completion-advice ablation

`diagnostics.completion_advice_checkpoint` prepares and validates an offline input
pair from the first post-edit checkpoint. That offline packet is not runnable
authorization and must not be passed to normal resume. The opt-in
`completion_advice_collector` prepares a separately bound live manifest from an
unhinted post-edit budget packet and requires its approved hash and exact new cap.

Control and treatment receive identical proposed fresh budgets. Treatment changes
only the latest state's `completion_guidance.next_action` to null and replaces its
message with factual check/eligibility information. It retains the warning that
eligibility does not prove untested behavior. Check identifiers, patch, tool schemas,
system instructions, history, notes, plans and resource counters stay fixed.

Check, ready (with or without probes), repair, source-needed and blocked wording
are supported; unknown stages or changed wording stop before counting.
This is removal of local completion advice, not all completion language: system
instructions, stage names and historical state remain. Scope cues cannot be combined.

`prepare(source, output, new_cap_nanos=...)` freezes both requests and source/runtime
identities externally with a hash-chained preparation receipt. `validate(path, hash)`
reconstructs the pair and checks stored bytes. The source loader verifies public task,
candidate and delivered state; neither source history nor closed artifacts are edited.

`completion_advice_continuation.rehearse` wraps an unhinted budget fork with a finite
scripted SDK and no network. Its scoped preparation hook transforms the authoritative
frozen first request and each later prepared request before counting. It rebinds
canonical context, native input, sizes and hashes, appending replacement preparation
records and baseline/selected receipts. Already transformed boundaries are reused;
count-driven segments receive the same intervention. Old records remain unchanged.

Accepted edits that return to needs-visible-checks retain advice removal and normal
check invalidation. Failed checks retain factual repair and source prerequisites;
blocked state is already factual and remains unchanged. Unknown wording stops without
baseline fallback. A saved ready fixture is not a treatment trajectory; scripted
actions establish plumbing only.

The live collector wraps the existing single-use post-edit collector, preserving
immediate counting, zero SDK retries, separate new-cost accounting and stop-on-
uncertainty controls. Its manifest binds the ablation implementation, first treatment
request hash, exact dev-train task/model/credential path, repeat=1 and positive cap.
Preparation reads environment identities without provider calls or credential contents.
Collection needs separate explicit authorization; closed allocations never reopen.
The hook remains diagnostic-only, with no ordinary runtime/default change.

Judge behavior by evidence for changed requirements, whether assumptions are tested,
patch correctness/regressions and reliable submission. Probe counts alone are not
improvement. Keep original benchmark outcomes and public operator checks separate;
non-execution is NOT_RUN, with no causal or efficacy claim.
