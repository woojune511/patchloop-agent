# Prior-decision response collection and frozen scoring

Uses [prepared views](prior-decision-design.md). New A retains prior attempt-card
decisions; new B removes only those decisions. Both use fresh Responses calls,
the unchanged neutral QUESTION and the same record_assessment schema as the prior
context experiment. Quoted code/tools are data. No returned function is executed.
Prior responses are neither fed to reviewers nor reused as new samples.

## Frozen execution

Four dev-train checkpoints: C1/C2 hf-hub-xet-endpoint-propagation v5,
C3 anyio-interrupt-runner-cleanup v3, C4 tox-cross-section-empty-substitution v1.
Exact turns and source identities are preparation-bound. A/B twice per checkpoint,
16 responses; paired AB/BA order reverses in repeat 2. Same model throughout:
gpt-5.4-2026-03-05, xhigh, maximum 60,000 input / 25,000 output tokens per call.
Standard price input USD 2.50/M, cached USD 0.25/M, output USD 15/M; maximum full
reservation USD 0.525/call, USD 8.40 total. Proposed invocation cap USD 9, 30 minutes.
Exact credential file C:/Users/geonj/Documents/PatchLoop/.env. Separate approval
required; preparation/validation never loads credentials or calls token counting.

Reuse the existing collector's pre-dispatch exact count and complete-pair reservation,
zero retries/corrections/resume, and stop-all on counting/transport/billing uncertainty.
Invalid/incomplete reports are retained, not replaced. Bound source, question, schema,
implementation, rubric and price hashes; require fresh external output. No patches,
tools, Docker, task evaluation or paid judge. official=false, acceptance/safety NOT_RUN.
Preserve encrypted continuation for audit only; never inspect private reasoning or
chain reports. Reconfirm pricing on execution UTC date. No runtime adoption is implied.

## Scoring locked before collection

Use the three dimensions and case-specific evidence criteria in
[the previous frozen rubric](evidence-context-sampler.md#frozen-manual-rubric):
candidate identity, discrepancy/setup disposition, and check scope/uncertainty.
That file is hash-bound as a dependency. Do not use its old arm descriptions.
Primary requires all three supported; keep unsupported and not_assessable separate.
Grade shuffled public reports with arm/order/cost masked, save cited excerpts and
grades before revealing labels. This is informed masked review, not independent blindness.

Resolve previously encountered scoring ambiguities in advance:
- C1 explicitly retaining a relevant current discrepancy while declining conclusive
  whole-task failure can pass. Merely repeating the mismatch and suspending applicability
  because it is unregistered/model-authored does not pass without a grounded critique.
  Pre-mark borderline cases during masked grading; report a strict sensitivity treating
  any such applicability-uncertain pass as unsupported. Never claim superiority depending
  only on a borderline pass.
- C2 code-supported resolution with appropriate check limits can pass without an exact
  rerun. Claiming a rerun or empirical resolution from non-overlapping PASS cannot.
- C3 omitted wrapped_name setup disposition is not_assessable, not an incorrect belief.
  Report setup-target coverage separately. Keep the broad question unchanged even if
  all responses omit it again; absence limits this control's usefulness.
- C4 requires the current reduced-execution default discrepancy and limited PASS scope;
  no requirement to quote a particular phrase or propose a repair.

Report per-case support counts, dimensions, invalid/missing/omitted responses and paired
wins/ties with both primary and strict C1 results. No pooled task solve rate, significance
claim or repair claim from two repeats. If B improves C1 but weakens C4, discuss the
tradeoff rather than a universal benefit. Both-fail leaves source/wording/other framing
open. This removes a field family and some tokens, not all guidance or pure length.

CLI: python -m diagnostics.prior_decision_sampler {prepare,validate,collect} --help.
API basis: https://developers.openai.com/api/docs/guides/function-calling and
https://developers.openai.com/api/docs/pricing.
