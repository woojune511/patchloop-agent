# Unhinted post-edit budget continuation

This opt-in diagnostic tests autonomous verification/correction after the first
accepted edit. It selects the next prepared model turn, before generation and any
subsequent check. It supports one completed historical mutation and segmented-v1
with per-call-v1 cost admission. This is a continuation, not a fresh solve or A/B.

`post_edit_budget_checkpoint.prepare` freezes the public source, candidate, prefix,
native input and proposed fresh allowance. `checkpoint_continuation.restore` copies
that completed prefix into a separate external store and restores the exact edit.
It retains an already prepared segment and completed size-triggering count when
needed; it excludes the selected count/dispatch and all later solving outcomes.
No historical tool is re-executed. No operator observation or repair hint is added.

Only current-state cost `invocation_cap` and `remaining` change in the first input.
Historical settled usage remains intact. Effective cumulative cap is historical
settled cost plus the new allowance; the old unused allowance is not reopened.
The fork journal records that override explicitly; its unchanged source envelope
describes inherited provenance, not ordinary resume authorization. Do not resume
this diagnostic with the normal CLI. Calls, tools, mutation limits, native history,
working notes, candidate, public checks and active time retain checkpoint state.
The ordinary first-state reconstruction must equal the selected request except
elapsed time. The frozen first input is counted again immediately before dispatch.

`post_edit_budget_continuation.prepare` freezes one proposed invocation and performs
read-only environment admission. It never loads credential contents or calls the
provider. `collect` needs the separately authorized manifest hash and exact positive
new cap. It claims a fresh result directory once, runs one branch with zero SDK
retries and separately accounts new usage. Count/transport/billing/cleanup
uncertainty stops execution. No automatic retry, resume, image pull or Docker start.

Measure the actual process: whether the agent checks its expectation, discovers
a defect, revises its patch, and submits; distinguish those from merely running
checks. Existing registered checks retain their original scope. A submitted patch
may undergo isolated benchmark evaluation, whose internals/feedback never enter
the solver. Operator public mathematical checks are separate post-run evidence.
Non-submission leaves benchmark correctness NOT_RUN. One result cannot establish
general improvement. A later generic-guidance comparison requires separate design
and allocation; it is not part of this single unhinted branch.

Validate exact restoration, cost-only input changes, unchanged source bytes,
subsequent budget persistence, new-cost accounting, and uncertainty stops without
provider calls. Scripted rehearsal tests plumbing, not autonomous discovery.
