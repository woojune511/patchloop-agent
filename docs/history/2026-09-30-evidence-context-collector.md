# Evidence/context reviewer: executable preparation, no live collection

## Problem and hypothesis

The preceding disposition instruction did not improve supported evidence judgment.
The [prepared comparison](2026-09-30-evidence-context-preparation.md) asks whether
surrounding plans, prior explanations and completion guidance influence judgment
given identical public evidence. It compares two fresh reviewers, not original
agent history versus a fresh reviewer. Runtime behavior remains unchanged.

## Change

Added `diagnostics/evidence_context_sampler.py` and a separate frozen
[collector/rubric contract](../../.agent/evidence-context-sampler.md). The eight
prepared views become 16 independent responses: A/B twice per checkpoint, paired
and counterbalanced. A single non-executing record_assessment function returns
public prose. The existing neutral question is unchanged; the report schema gives
no task-specific hint or scoring categories. Original coding tools remain quoted data.

The shared sampler now has an optional report parser, bypassing coding-action
conversion for this response-only use. Its existing cost, count, deadline and
uncertainty handling remain shared. The default coding-decision collection path
is unchanged. Invalid/incomplete reports are retained without corrective calls;
encrypted continuation is audited, never sent to later reviewers.

Rubric is frozen separately from requests: candidate identity, discrepancy/setup
interpretation, check scope/uncertainty. Grade masked responses with evidence excerpts
before revealing arms. Report all planned cells, missing/invalid responses and
per-case paired results; do not aggregate a task solve rate.

## Frozen evidence

- Preparation v3: `C:/pt/analyses/evidence-context-preparation-20260930-v3/packet.json`.
  SHA `sha256:f0d76812521444fb21724e4e7773258d455572ed8271d2ad70daeed9576e8f7e`.
- Previous v2 remains immutable. V3 only rebinds the changed shared implementation:
  all eight view content hashes, all case receipts and source bindings match v2.
- Collection plan: `C:/pt/analyses/evidence-context-collection-plan-20260930-v1/packet.json`.
  SHA `sha256:0de2e01b698dfe565d5919be83dab0bd611d12cf288b2703ac7dd3bc02ecc727`.
- Sampler content set SHA
  `sha256:146b1334acc6ffd0e15bc597499b90c84060a280001e2e2395afc22bffa468a5`.
- Mock: `C:/pt/analyses/evidence-context-collection-mock-20260930-v1`,
  `run_dev_sample_46618ac82f8647cc`, 16/16 responses, eight completed pairs.
  Mock call/cost counters are simulated, not provider usage or spending.
- Plan journal records offline validation. Source journals/envelopes are unchanged.

## Validation and boundaries

68 focused tests passed: new collector 11, preparation 5, shared sampler 39,
prior disposition wrapper 8, documentation 5. Ruff passed. An additional actual-input
mock verified all 16 outgoing request hashes; credentials, real provider creation
and tool execution were patched to fail if reached. No credential was read.
Failure coverage includes input counting, transport, uncertain billing, missing
encrypted continuation, malformed/incomplete reports and artifact tampering.

No model call, token-count API call, tool, Docker or evaluator was executed.
No task-runtime behavior changed, so task/evaluator smoke was not run; the applicable
smoke is response collection. Correctness and safety remain NOT_RUN, official=false.
No scoring outcome or causal advantage is established by the mock.

## Next decision

Await a separate paid approval: dev-train HF endpoint v5 (two checkpoints), AnyIO
cleanup v3 and tox substitution v1; gpt-5.4-2026-03-05 xhigh, exact
`C:/Users/geonj/Documents/PatchLoop/.env`, A/B twice each, 16 responses total,
30 minutes, USD 9 invocation-wide cap. Per-call input ceiling 60,000 and output
ceiling 25,000 imply USD 0.525/call and USD 8.40 maximum at reviewed Standard prices.
No retry/resume or tool execution. Proposed fresh result root `C:/pt/context0930a`.

Official pricing reviewed on 2026-09-29 UTC: input USD 2.50/M, cached USD 0.25/M,
output USD 15/M. Recheck if execution UTC date changes. Sources:
[pricing](https://developers.openai.com/api/docs/pricing) and
[function calling](https://developers.openai.com/api/docs/guides/function-calling).
Approval is NOT_GRANTED; no approval file was created. Prior budgets remain closed.
