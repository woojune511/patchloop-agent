# Review pilot runtime fork and accounting

## Decision and implemented boundary

Conan's old runtime identity prevented native continuation even though the preceding
public probe admission passed. The diagnostic now creates a new current-runtime
envelope for an explicitly requested fork. The original envelope is retained in CAS,
the exact parent prefix is copied, and a new event binds parent/target runtime,
parent source hashes, historical settled usage and the new allocation. Historical
funds are not reopened. Ordinary load/resume still rejects Conan's old runtime.

All C/A/B arms use the same fork option. Only the reviewed exact Conan runtime pair
can cross a runtime mismatch; other mismatches remain rejected. The script-only
entry still requires a finite ScriptedClient, so this does not enable paid work.

Reviewer counting, dispatch reservation, request artifact and settled token/cost
records are now journaled separately. Count/transport/usage uncertainty leaves the
boundary visible and stops later episodes. Tests compare durable reviewer settlement
with the cost deducted from repair, and verify that failed dispatches are not settled.
This is simulated accounting evidence, not live provider billing validation.

## Validation

Twelve actual saved-source branches reached scripted AGENT_STOPPED with their native
history preserved, in the specified interleaved order. All target envelopes bind
the current runtime. Original journals/envelopes were hash-checked unchanged.
Root: C:/pt/analyses/review-runtime-fork-20261001-v1.
Driver: C:/pt/review_runtime_fork_20261001.py. No task correctness evaluation occurred.

Thirty-six focused tests passed, including fixture submission/evaluation in both
old-envelope and explicit-fork modes, accounting failure stops, and public scoring
controls. Ruff passed. A nested fixture initially selected an older fork's CAS map;
selecting the newest marker fixed the reproduced continuation failure. Two subsequent
test assumptions were corrected: the source fixture injects its evaluator environment,
and prefix counters differ from full-source counters. Failed directories remain.

## Operator-only scoring preparation

diagnostics/review_pilot_manifest.py binds exact source/request/candidate identities,
evaluation packages, visible regressions, diagnostic programs and scoring code for
twelve rows. Pyinfra evaluation uses v2 while preserving the original public input
and v1 verdict separately. The two public matrices classify missing observations as
contract errors; isort requires original comment ownership plus idempotence. Hidden
checks remain required and private. None of these scoring inputs enter model context.

The provider-free preparation driver is C:/pt/review_pilot_prepare_20261001.py.
It freezes identities, rescores saved controls, and checks existing source/probe/
evaluation environments without credential reads, model dispatch or image acquisition.
Its result must not be treated as live-collector readiness. Actual response continuation,
full shared live accounting, repair-stage probe execution and final evaluator integration
still require provider-free collector rehearsals before a paid approval request.
