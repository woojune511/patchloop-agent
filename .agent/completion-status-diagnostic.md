# Completion advice diagnostic

## Question and scope

Does recommending the next registered check and then submission help narrow the
agent's verification plan before it has examined requirement scope and test inputs?
The public traces show matching actions, not a causal result. This diagnostic tests
one part of that explanation; it does not assess semantic coverage automatically.

`diagnostics.candidate_review_repair.run_seeded` accepts an optional
`completion_guidance_policy="status-only-v1"`. Omission or `"none"` preserves the
existing seeded path. This is a process-local diagnostic, not a CLI/default change.
Run branches sequentially in dedicated processes, as for the existing seeded seam.

## Projection contract

Starting with the first input, `diagnostics/completion_status.py` changes only
`completion_guidance.next_action` and `completion_guidance.message` in these stages:

| Stage | Projected guidance |
| --- | --- |
| `needs_visible_checks` | `next_action=null`; required checks have not all passed on the current diff, so submission is not eligible. A PASS on another diff does not count. |
| `ready_to_submit` | `next_action=null`; required checks pass on the current diff and submission is eligible, without proving untested behavior. |

Diff identity, stage and submission readiness remain exact. Failed-check repair,
missing-source and blocked explanations remain exact. Tool admission, schemas,
system/planning instructions, action horizons, check gates, notes and budgets remain
owned by the common runtime. The seeded-candidate notice remains unchanged. The
diagnostic neither requires another investigation nor permits premature submission.
It removes these two recommendations, not every completion cue in the context.

Projection happens in the existing context overlay before native input assembly,
counting and dispatch. Subsequent append/segment inputs inherit the projected state
normally. No old request, plan, check result or continuation item is rewritten.
The journal records `diagnostic_completion_guidance_policy` before the first turn,
binding the policy, message hash, changed fields and external experiment hash.
The policy name and experiment metadata are not added to model state.

## Isolation and evidence

The option rejects external review, supplemental change-review policy, paired
observation and operator feedback in the same branch. Existing fresh-root,
repeat=1, no-resume and exact-seed/base requirements still apply. The imported
candidate consumes one mutation slot; evaluation uses a separate clean workspace.

`tests/test_completion_status.py` checks the two-field boundary, unchanged failure
guidance, option isolation, default behavior, hook restoration and actual native
input delivery in append/segmented smoke runs. The script exercises a failed check,
read, repair, successful recheck and isolated evaluation with network prohibited.
Mock decisions establish transport and runtime compatibility, not agent efficacy.

A later live comparison must freeze its exact tasks, seeds, model, settings, prices,
source hashes, sample order and total cap separately. Compare requirement scope,
actual selected check inputs, resulting edits and acceptance; neither extra reads
nor a different first action is sufficient improvement evidence. Existing closed
allocations do not authorize additional runs. Keep `official=false`.
