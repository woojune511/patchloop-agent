# Unhinted post-edit continuation preparation

Date: 2026-09-28. Provider-free preparation, official=false. No paid allocation.

## Problem and hypothesis

The toqito public audit found a semantic defect in an unsubmitted candidate. The
delivery audit found the relevant observations were available before its mistaken
interpretation. The original run then exhausted its cost allowance before checking
the edit. Whether it would autonomously discover/correct the defect with resources
remains unknown. Do not supply the discovered witness or a task-specific repair hint.

## Boundary and intervention

Source: `run_dev_33068b6e257f423a`, external root
`C:/pt/runs/original-pilot-original-toqito-1538-proposed-v1`.
Restore the first accepted mutation (event 133), its batch (135), and the prepared
size-triggered segment (139). Select turn
`turn_bad6fd9e41ad4abba2a6f31600223829`, excluding its old count/dispatch and all
later outcomes. The completed count before segment 139 remains historical only.

Candidate: `sha256:fdd4fa640b555cc3ef43317ec9b4b3fa2a694902f11d571f43fb48dd2a318745`.
Historical settled cost: $1.091299. Proposed new allowance: $3.00; effective
cumulative cap: $4.091299. The prior unused allowance stays closed. Remaining
32 model calls, 85 tools, three accepted edits, and approximately 1,212 active
seconds are preserved. The prepared first input changes only current cost cap
and remaining cost. Native input, notes, plan, candidate and public check scope
remain inherited. No supplied operator observations or generic new guidance.

## Implementation and evidence

The optional checkpoint backend freezes/restores this boundary. A single-use
collector separately accounts fresh usage, binds exact authorization, counts
before dispatch, and stops on uncertainty with no automatic retry/resume.
Ordinary runtime policy and ordinary resume semantics are unchanged.

Packet: `C:/pt/analyses/postedit-budget-checkpoint-20260928-v1`.
Actual-task rehearsal: `C:/pt/analyses/postedit-budget-rehearsal-20260928-v1`.
Rehearsal restored the exact candidate and naturally rebuilt input, then used a
synthetic stop: one simulated count/call, zero provider calls/billed cost. This
establishes restoration, not provider acceptance or autonomous repair. The source
history remains immutable. New focused tests cover cost-only projection, later
budget persistence, first-state restoration, accounting, uncertainty, authorization
mismatch and single-use collection; existing continuation tests cover action replay.

Validation: the 11 new tests, 22 related continuation/collector tests and five
documentation checks passed across focused runs (the initial credential-path
fixture mismatch and documentation size failures were fixed and rechecked).
Ruff passed. Mock `run_dev_d987d73aa28d403f` reached isolated EVALUATOR_PASS with
zero cost and safety NOT_RUN. The optional full repository suite was interrupted
before completion; no full-suite pass is claimed. Read-only local environment
admission returned READY with zero model calls, counts or container launches.
The live manifest is prepared separately at
`C:/pt/analyses/postedit-budget-live-20260928-v1/manifest.json`; its result root is
`C:/pt/posteditlive0928a`. Neither preparation nor READY authorizes paid work.

## Next question

After exact funding authorization, collect one unhinted continuation using
`gpt-5.4-2026-03-05`, xhigh, 25,000 desired output tokens, the original repository
`.env`, and `tasks/dev-train/original-toqito-1538/public.yaml`. Observe whether the
agent revisits its comparator, corrects the patch and submits. Benchmark evaluation
is isolated after submission; public operator checks are separate post-run evidence.
Non-submission remains NOT_RUN for benchmark correctness. This selected continuation
cannot establish fresh-solve performance, a causal A/B effect or general improvement.
