# Checkpoint source delivery and effective public-state handoff

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: authorized implementation and focused local validation
- Origin Date: 2026-10-27
- Verification Status: IMPLEMENTED / LOCALLY TESTED; new live run NOT_RUN
- Baseline: `d346abd6`; [observed defect](2026-10-27-first-edit-checkpoint-results.md)

## Problem and change

The accepted A repair could not receive its original-call verification in a second
model response: post-edit input reached 65,982 tokens. Revalidated source was sent
again alongside the same frozen source. The checkpoint builder then ignored the
generic handoff state and reconstructed the identical over-limit request.

Fix that delivery contract in the checkpoint diagnostic. Keep the initial A/B
requests unchanged and preserve durable receipts, source admission, budgets and
original-call checks. No model setting, input/output ceiling or repair opportunity
is added. The production agent and other diagnostic request builders are unchanged.

`checkpoint_delivery` replaces only a successful mutation's revalidated source
content with an explicit reference when the entire text exactly matches contiguous
lines already visible in the same request's frozen evidence. The reference names
the source scope, path, file hash, inclusive range and content hash. Its containing
span still carries the current file hash/range and revalidation metadata; an old
source reference does not assert that the old file is current. Adjacent observed
ranges can be joined, but unobserved gaps cannot be filled. Missing, mismatching or
unhelpfully small references retain the inline body. Changed mutation evidence,
patches, failure messages and current original-call feedback remain present.
There are no fabricated read calls or references to unseen tool results.

At a counted context boundary the builder now consumes the actual
`diagnostic_repair_cycle_handoff_v1` record. It combines frozen observations, fresh
public state and completed public exchanges, then applies the existing lossless
representation to that combined document. This boundary policy is common to A/B;
it is not applied to the initial A request. New diff, observed current sources,
latest mutation, verification, correction and counters are retained. Opaque model
state remains outside the request. The runner recounts and admits the changed
request before committing the handoff and dispatching; counters never restart.
If the rebuilt request still exceeds the limit, the existing one-rebuild rule stops.

The shared fallback changes the continuation contract, so its policy and the new
module are included in future manifest scope/bindings. Old allocations stay closed;
old request artifacts and historical reports are not rewritten.

## Local evidence

Offline reconstruction of the actual saved A/B public follow-ups verified:

| Check | A | B |
|---|---:|---:|
| Previous request JSON characters | 234,677 | 164,921 |
| New request JSON characters | 208,204 | 138,381 |
| Referenced revalidated source spans | 2 | 2 |
| Exact decoded tool-result round trip | PASS | PASS |
| Exact current original-call feedback | supported | failed |
| Initial request hash unchanged | PASS | PASS |

Receipt: `C:/pt/checkpoint-delivery-local-v1/summary.json`, with a hash-chained
local journal. No provider, API input counting or target execution was used.
Character counts do not establish the new provider-token count or 60K admission.

Focused tests cover exact source-reference expansion, metadata and negative-result
preservation, missing/mismatched-source fallback, and unchanged durable inputs.
Scripted model tests use an actual large-source fixture and a deterministic size
boundary rather than always returning 100 input tokens. They verify successful and
failed original-call results in the actual next create request, count/send input
agreement, and unchanged response/action/edit allowances. A forced boundary checks
that the new request includes the real handoff state and differs from its parent;
a still-over-limit case stops after one rebuild without another model dispatch.

Focused validation: **81 PASS in 77.15 seconds**, including the delivery tests and
existing repair-cycle, correction-time, context and preparation contracts.
Receipt: `C:/pt/tmp/checkpointdelivery-focus27.xml`.
Quick suite: **472 PASS in 108.05 seconds**, including isolated mock evaluation;
receipt: `C:/pt/tmp/checkpointdelivery-quick27.xml`. Ruff and whitespace checks PASS.
Both selections remain under two minutes; mock smoke was not repeated separately.
Read-only review found no blocking correctness issue and confirmed the distinction
between simulated counting and actual provider admission.

## Decision and limitation

The previous no-op handoff and duplicate retransmission have specific local
regressions. This establishes request construction and scripted feedback delivery,
not real-model comprehension, real API admission or additional repair quality.
The preceding A accepted repair remains evidence for the earlier saved-evidence
trial only. No paid experiment was requested or run for this implementation.
