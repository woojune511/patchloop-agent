# Evidence/context assessment collection

This diagnostic consumes a validated evidence-context preparation. Both arms are
fresh reviewers with the same QUESTION and public evidence; only A has the prepared
surrounding_context. Original tools/instructions are quoted data. The sole callable
schema, record_assessment, carries a public assessment string and is never executed.
It supplies no answer categories, task hints or scoring criteria. No tool gateway,
patch, test, Docker, evaluator, new source, response chaining or plaintext reasoning.

## Fixed execution and admission

- Four dev-train checkpoints: C1/C2 hf-hub-xet-endpoint-propagation v5;
  C3 anyio-interrupt-runner-cleanup v3; C4 tox-cross-section-empty-substitution v1.
  Exact root/turn/evidence identities come from the prepared packet.
- A/B twice each: 16 responses in paired AB/BA blocks, reversing each pair in repeat 2.
- gpt-5.4-2026-03-05, xhigh, 25,000 output ceiling; input ceiling 60,000.
- Exact PatchLoop/.env; total proposed USD 9, maximum full reservation USD 8.40
  (16 times USD 0.525 at input 2.50/output 15 per million). Cached input USD 0.25/M.
- Thirty minutes total; count the exact request immediately before each dispatch.
  Zero SDK retries/corrections/resume; stop on count, transport or billing uncertainty.
  Reserve a complete pair before its first call. Record partial pairs; do not replace.
- Collection requires a separate exact approved scope and matching approval JSON;
  plan preparation/validation never loads credentials. Recheck prices on execution UTC day.
  CLI: python -m diagnostics.evidence_context_sampler {prepare,validate,collect} --help.
- Hash-bound preparation, requests, implementation, rubric, sources and pricing;
  fresh external result root, immutable artifacts, append-only dev-run-v1 journal.

The shared collector records report functions directly without converting them to
coding actions. Invalid/incomplete reports are NOT_ASSESSABLE, retained without retry.
Encrypted continuation is audited separately and never reused. VALID means schema
validity only, not correct judgment. Task acceptance and safety stay NOT_RUN.

## Frozen manual rubric (never included in model requests)

Mask arm, order, usage and latency before grading; save grades and cited response
excerpts before revealing labels. Grade each dimension supported / unsupported /
not_assessable, with short evidence justification. Schema-invalid/incomplete responses
are not_assessable on all dimensions, remain in the planned denominator, and are
reported separately from semantic mistakes. Use exact observed code/IDs, not keywords.

Dimensions: (1) observation and current-versus-historical candidate identity;
(2) relevant discrepancy/setup validity and disposition;
(3) cited-check scope and uncertainty limits. Primary supported assessment requires
all three supported. An equally evidence-grounded alternative interpretation can pass;
record its basis without changing the rubric. No desired next action or patch score.

- C1: Current HF operator observation concerns an ambient endpoint with no explicit
  HfApi constructor endpoint. Registered client checks use explicit endpoints and
  do not negate that boundary. Recognize the unresolved discrepancy, or give an
  evidence-grounded applicability critique; public PASS alone is not rejection.
- C2: The same observation is historical after the explicit/ambient handling edit.
  No delivered exact current rerun settles it. A code-supported provisional resolution
  with its limit is acceptable; neither current failure nor exact empirical resolution
  follows solely from the old observation or other PASS. No forced investigation.
- C3: wrapped_name setup failure call_2JGcBMcg2C5fCncp3neASL4Q did not reach its
  intended behavior. Historical exit-zero call_VK4F44C7vfoXSJQpCj7VFrtl did execute
  and expose resumed-test behavior. Separate these from the lifecycle check that
  later passed; its PASS does not answer the original probe question.
- C4: Import failure call_zpxMz31ZAieaMrHoxlJIvr8a is setup-invalid. Later current
  call_CndFh03WtWoKdz1ra3Bdy9EP passed setup comparisons and reached changed lines:
  factor-filtered and missing-default results were both empty, with the latter
  contradicting fallback. This supports a current reduced-execution discrepancy,
  not full CLI verification. Other showconfig PASS does not discharge it. Later
  repair/CLI confirmation is excluded from inputs and cannot justify the assessment.

Report per-case A/B counts and paired wins/ties, supported dimensions, invalid and
uncollected responses, cost/time. Two repeats are descriptive, not inferential power.
Cases differ in stage and evidence, so no pooled solverate. A B advantage supports
bundled context dependence here, not length/framing/history separately. Both fail
leaves evidence/question limitations open; both pass does not establish repair skill.
No runtime adoption or generalization claim from this diagnostic.

API basis: https://developers.openai.com/api/docs/guides/function-calling and
https://developers.openai.com/api/docs/pricing (Standard short-context pricing).
