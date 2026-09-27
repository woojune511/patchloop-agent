# Offline completion-advice ablation

`diagnostics.completion_advice_checkpoint` prepares and validates an offline input
pair from the first post-edit checkpoint. It has no live provider collector.
A packet is not runnable authorization and must not be passed to the normal
resume or existing post-edit collector.

Control and treatment receive identical proposed fresh budgets. Treatment changes
only the latest state's `completion_guidance.next_action` to null and replaces its
message with factual check/eligibility information. It retains the warning that
eligibility does not prove untested behavior. Check identifiers, patch, tool schemas,
system instructions, history, notes, plans and resource counters stay fixed.

Only the observed needs-visible-checks and ready-to-submit wording is supported;
unknown stages or changed wording fail rather than silently broaden the ablation.
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
check invalidation. Unsupported stages (including needs-mutation after failed checks)
or changed wording stop before counting, without baseline fallback. This is a bounded
diagnostic limitation, not a solver failure or a new submission gate. Live integration
and an exact independently authorized invocation are still absent. A saved ready
fixture is not a treatment trajectory; scripted actions establish plumbing only.

Judge behavior by evidence for changed requirements, whether assumptions are tested,
patch correctness/regressions and reliable submission. Probe counts alone are not
improvement. Keep original benchmark outcomes and public operator checks separate;
non-execution is NOT_RUN, with no causal or efficacy claim.
