# Offline completion-advice ablation

`diagnostics.completion_advice_checkpoint` prepares and validates an offline input
pair from the first post-edit checkpoint. It has no provider collector or runtime
hook. A packet is not runnable authorization and must not be passed to the normal
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

A future live experiment would need a scoped hook from this first boundary through
subsequent decisions, canonical context/input rebinding before counts, count-driven
segmentation tests and an exact independently authorized invocation. None is supplied
by this offline packet. A saved historical ready request tests projection only; it
is not the treatment's future trajectory. New mutations/unsupported stages need an
explicit continuation design before dispatch, not an improvised mid-run policy.

Judge behavior by evidence for changed requirements, whether assumptions are tested,
patch correctness/regressions and reliable submission. Probe counts alone are not
improvement. Keep original benchmark outcomes and public operator checks separate;
non-execution is NOT_RUN, with no causal or efficacy claim.
