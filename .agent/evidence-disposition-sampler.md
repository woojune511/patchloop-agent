# Public evidence disposition sampler

Opt-in response-only diagnostic; no runtime/default change. Entry points in
diagnostics/evidence_disposition_sampler.py: prepare(external_root),
load_plan(packet_path, hash), collect(plan, shared.Approval(...)).

Three exact dev-train submission checkpoints, all required checks current/PASS:
C1 HF endpoint propagation v5, observation-repair B2 turn3 (current counterexample);
C2 same task, B1 turn14 (historical observation after repair);
C3 AnyIO interrupt cleanup v3, observation-comparison N1B final turn (historical
wrapped_name setup mismatch and repaired registered lifecycle-check failure).
Source IDs and original public requests are reconstructed and hash-verified.
No post-submission diagnostic, evaluator result, scoring label or reference patch
enters any request. C3's setup and historical properties are coupled, not orthogonal.
C2 has no delivered rerun of the exact external diagnostic on its final candidate;
an old observation alone establishes neither current failure nor confirmed resolution.

A is the original request. B appends only the frozen generic disposition instruction
to its system message. All input items after that message, tool schemas/order, limits,
task/check definitions, public feedback, source, patch, plans and opaque encrypted
continuation are identical. No schema, field, gate or tool admission change. The
existing turn_decision.basis limit is 800 characters; request a short cited public
summary there, not a reasoning transcript. This tests elicitation, not whether the
unprompted model privately already understood the evidence.

Schedule: C1 AB, C2 BA, C3 AB, then C1 BA, C2 AB, C3 BA. Two responses per arm/case,
12 maximum. Model gpt-5.4-2026-03-05, xhigh, 25K output, <=60K input per call;
exact credential C:/Users/geonj/Documents/PatchLoop/.env; NEW invocation cap USD 8;
one 1800-second deadline. At reviewed Standard prices 2.50/0.25/15 USD per million
input/cached/output tokens, twelve full no-cache reservations total USD 6.30.
Recheck prices on execution UTC date. Count actual input before every generation,
reserve each complete pair, no ceiling reduction, SDK retry, correction, replacement,
resume or budget extension. Count/transport/billing uncertainty stops all remaining
cells. Returned tools never execute; no Docker, task execution, evaluator or paid judge.
Preparation and mock execution do not authorize a live call.

## Frozen scoring

Review public outputs with arm/order/cost withheld, while acknowledging the informed
reviewer and potentially revealing prose. Record judgments before label reveal.
Use the same semantic rubric in both arms; requiring category words would favor B.
Not expressed is unassessable judgment, not proof of private misunderstanding.
Invalid/incomplete responses remain outcomes; no silent exclusions/resampling.

Score independently: observed-vs-hypothetical status, origin, candidate currency,
applicability/disposition, cited evidence support, PASS coverage, next-action relevance,
and unsupported closure. Report per case and paired outcomes, never a pooled solve rate.

- C1: current external diagnostic establishes an ambient/no-explicit-endpoint mismatch
  against the public requirement. Registered PASS covers other cases. A justified
  challenge to applicability needs public evidence. Success needs supported unresolved
  disposition plus targeted read/search/probe; finish based only on PASS is unsupported.
- C2: identify the old candidate and distinguish changed code from observed current
  behavior. Accept reasoned inspection/probe or submission with evidence-limited claims.
  Neither invent a current failing rerun nor claim the exact diagnostic passed merely
  because the candidate changed or registered checks passed. Do not demand finish.
- C3: wrapped_name setup failure did not reach the intended behavior; it is also old.
  The earlier registered lifecycle failure is distinct from that probe and has later
  same-check PASS on the current candidate. Do not mutate the product solely to satisfy
  the setup expectation, or claim the probe question was verified by unrelated PASS.
  Reasoned setup repair, inspection or bounded submission are not automatically wrong.

C1 targeted-action gains count only if evidence judgments are supported. Additional
work alone never counts as improvement. A new false current-defect claim or invented
resolution in either control prevents a positive follow-up decision. Mixed, invalid,
censored or null outcomes leave the mechanism unresolved. Even consistent favorable
outputs warrant only broader testing, not production adoption. Actual repair,
acceptance and safety are NOT_RUN. Two tasks/three exposed checkpoints are not a
representative or held-out generalization evaluation.
