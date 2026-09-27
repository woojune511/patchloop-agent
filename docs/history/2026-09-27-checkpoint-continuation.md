# Checkpoint continuation: provider-free execution validation

Date: 2026-09-27. All evidence is `official=false`; no new live allocation.

## Problem and implemented change

The [mutation-advice input pair](2026-09-27-mutation-advice-checkpoint.md) established
two-field isolation, but did not execute actions selected at that boundary. A
next-response-only comparison could not answer whether the repair or verification
improved. A continuation must preserve earlier evidence and remaining resources.

`diagnostics/checkpoint_continuation.py` now restores that checkpoint into a fresh
external root and exercises the ordinary adapter, registered gateway, loop and
isolated evaluator using finite synthetic SDK responses. Its
[contract](../../.agent/checkpoint-continuation.md) separates restoration, simulated
provider usage, actual local check execution and untested live behavior. Production
runtime, prior preparation module/contract and frozen packet are unchanged.

Completed prefix events and referenced CAS bytes are preserved. New fork/preparation
events identify the branch; an exact-reference resolver reads copied historical
artifacts without rewriting old references or journals. The ordinary gateway
restores observed source/anchors and notes, while the loop restores plans, native
continuation, counters and deadline. It never replays the historical probe.

The first rebuilt A input must equal the captured input except for elapsed time.
The actual first A/B request remains the exact frozen selection and receives a
new synthetic count. Later inputs use normal guidance. Local checks and evaluation
are labeled local in the submitted manifest; the OpenAI adapter identity describes
the wire grammar and source, not a remote call. Historical baseline cost and
simulated new usage are separate, with unknown simulated usage left null.

## Actual N1 restoration evidence

Packet: `C:\pt\analyses\checkpoint-continuation-20260927-v1`.
Two fresh roots, `A` and `B`, each preserve 58 completed prefix events and 15
referenced artifacts. The resulting journals each contain 77 events. Their first
count/dispatch identities match the original frozen hashes:

- A: `sha256:480ce9c1d4fe3e30142bdb3ddc4881dd3a29cde6f64478159d5cc23cd173ca7a`.
- B: `sha256:02c3dbabf765b46f8bc84e11dece96c98e5ef28bb0809e048fffd3b56440ce7e`.

Both restore 37 model calls, 92 tool actions, four mutation slots, 1,655 displayed
active seconds and $0.967463 remaining from the original $1.20 bookkeeping cap.
Historical settled usage is $0.232537. The active deadline spends local preflight
and continuation time; preliminary workspace/CAS materialization is separate setup.

Each N1 branch uses one synthetic response that deliberately selects `stop_task`.
Each records `AGENT_STOPPED`, no mutation, no new probe and no evaluator execution.
N1 acceptance and safety remain `NOT_RUN`. The synthetic count of 36,637 is fixture
input, not a new tokenizer measurement or B's real token count. Simulated usage is
not billed cost. Actual model calls and new billed cost are zero.

`A-receipt.json`, `B-receipt.json` and `restoration-audit.json` bind these observations;
the separate audit journal binds the implementation/contract and audit hashes.
All 598 files in the original live state, fresh-solve analysis and frozen input-pair
packet retain their prior bytes. No Docker startup/pull or credential file read ran.

## Validation and limits

Synthetic fixture continuations use the same restoration code and real registered
replacement, public checks, submission and isolated local evaluator. Both A and B
reach fixture acceptance PASS. This is hand-scripted plumbing/fixture evidence,
not autonomous model success or a mutation-advice efficacy result. Docker safety
remains `NOT_RUN`; no public or private evaluator result is fed into later input.

The final focused group passed six tests in 111.09 seconds. It covers exact first
A/B requests and restored state, ordinary guidance after the first input,
repair/check/submission/evaluation, completed mutation/check replay and conflicting
action-ID reuse, visible-check failure without submission, and count/transport/usage
uncertainty stopping before any new tool. Twenty input-pair/public-projection
regressions passed in 45.66 seconds, including a mock isolated-evaluation smoke;
five documentation checks passed. Ruff passed for runtime, tests and the new
diagnostic. The whole repository suite was not rerun; its earlier interrupted run
remains incomplete. Focused scripted acceptance is not a replacement for live checks.

The implementation forbids replaying a rehearsal and has no live collector. Its
offline probe stub preserves schema identity but rejects new probe execution.
Live admission, real provider continuation acceptance, real counts/prices, Docker
environment readiness and invocation-wide new-spend enforcement need separate
implementation and verification before the proposed paid comparison. Existing
caps/credential settings and historical approvals do not authorize that work's
paid execution. Do not describe this as an executed A/B efficacy comparison.
