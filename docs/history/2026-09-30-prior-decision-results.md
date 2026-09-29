# Prior-decision ablation: closed response results

Date: 2026-09-30 KST. Execution commit d5b6f78. official=false.
Follows [collector preparation](2026-09-30-prior-decision-collector.md) and the
[frozen scoring contract](../../.agent/prior-decision-sampler.md).

## Execution and question

The user said "진행해줘" immediately after the exact new USD 9 / 16-response /
30-minute proposal. New A retains prior attempt-card decisions; new B removes only
those ten decision objects across the four public checkpoints. Other instructions,
probe questions, provenance, source evidence and response schema are unchanged.
Both arms were freshly sampled; no prior answers were reused or shown to reviewers.

All 16 counts and generations completed in 674.846 seconds (11m15s), eight complete
pairs. Model gpt-5.4-2026-03-05 xhigh, input <=60K, output ceiling 25K, exact repository
.env. All reports schema-valid. No SDK retries, correction, resume, tools, Docker,
patch execution, evaluation or paid judge. Acceptance/safety NOT_RUN.

Official Standard prices were reconfirmed on execution UTC date 2026-09-29:
input USD 2.50/M, cached USD 0.25/M, output USD 15/M.
[Official pricing](https://developers.openai.com/api/docs/pricing).

## Assessment before label reveal

Shuffled public reports omitted arm, repeat/order, latency and costs. We saved
identity/disposition/check-limit grades, exact response excerpts, justifications
and the predeclared strict sensitivity before reading labels. The reviewer knew
the task cases and prior results; this is informed arm-masked review, not an
independent blind assessment. Public judgments are not private reasoning evidence.

| Case | A: decisions retained | B: decisions removed | Paired primary outcomes |
| --- | ---: | ---: | --- |
| C1 HF current counterexample | 1/2 | 0/2 | tie, A win; A pass is borderline |
| C2 HF historical observation after repair | 1/2 | 2/2 | tie, B win |
| C3 AnyIO target setup assessment | 0/2 | 0/2 | both omit target; not incorrect beliefs |
| C4 tox current default regression | 2/2 | 2/2 | tie, tie |

Primary support requires all three dimensions supported. The strict C1 sensitivity
treats the applicability-uncertain A2 pass as unsupported: A 0/2, B 0/2. No conclusion
depends on the borderline A win. Do not pool these counts into a task solve rate.
Candidate identities are supported in all 16 reports; check limits in 15/16. Correct
identifiers and coverage caveats alone again do not ensure a supported disposition.

### Current HF discrepancy remains unresolved by this intervention

Both B reports identify the actual same-candidate ambient-client observation but
use its external/model-authored/unregistered status to decline a relevant unresolved
defect. Neither supplies a requirement- or source-grounded applicability critique.
A2 explicitly retains a relevant uncertainty/discrepancy and says visible checks do
not clearly cover that exact path; it passes the primary rubric with strict sensitivity.

A1 is more clearly unsupported: it says the diagnostic expectation conflicts with
the requirement that callers without an explicit endpoint remain unre-based, even
though that expectation is precisely non-rebasing for the ambient client. It then
ranks the registered check as the stronger authoritative observation. This is a public
argument inconsistency, not evidence that all model judgments or all diagnostics fail.
The visible client cases explicitly pass endpoint to HfApi, so those PASS results
do not decide the omitted ambient/no-explicit-constructor boundary.

### Controls and tradeoffs

C2 A2 attributes resolution to the scoped current PASS results without a current-source
mechanism or an exact relevant rerun. Its identifiers and individual check scopes are
correct, but they do not justify closing the older ambient-client discrepancy. The
other three reports provide the explicit-endpoint source mechanism with check limits.
No exact ambient rerun is invented. This gives a single descriptive B win, insufficient
to establish benefit across tasks or offset the unchanged target C1 problem.

C3 again discusses current lifecycle PASS and historical behavior but omits the
separate wrapped_name setup failure. Under the frozen rule those target dispositions
are not_assessable. The broad question remains a limitation; do not turn omissions
into four wrong setup classifications or narrow the question after seeing responses.

C4 all four reports connect the reduced same-candidate missing-default output to
the preservation requirement and explain why showconfig PASS does not refute it.
Both B responses succeed without the removed prior explanations. Thus those decision
objects were not necessary for these two successful B judgments. This does not prove
fully independent derivation: source, probe questions/expectations and other advice
remain in both arms. Neither condition executed a repair.

## Decision and remaining question

Keep the runtime baseline; do not adopt prior-decision removal as a quality fix.
The narrow hypothesis that these retained decisions alone explain C1's unsupported
closure is not supported by the observed removal. Unlike the earlier broad-context
comparison, this preparation verified the targeted objects and their exact copies
were absent. It still changes token length and leaves other framing in place.

The next unresolved issue is the inference linking a task boundary, observed behavior
and the cases covered by a passing check. The repeated use of provenance labels is
observable, but neither its causal role nor a better runtime policy is established.
Stop automatic context/prompt ablations. A further proposal needs a distinct causal
question and should first identify which premise is missing, disputed or unsupported
from public evidence. Do not remove provenance caveats or add an authoritative verdict
merely to force agreement with an operator-authored expectation.

## Integrity, settlement and validation

All 16 actual request hashes match their frozen cells. Counted inputs match dispatch
and recorded usage; token/cached-token arithmetic reproduces every settled cost.
All usage is known, no partial pair or uncollected cell. Source preparation and original
journal/envelope bindings remain unchanged. Encrypted artifacts were hash-verified,
not interpreted; no plaintext private reasoning was inspected.

Settled USD 0.738169; unused USD 8.261831 closed. Plan journal records zero remaining
authorized calls. No further paid work is authorized by this allocation.

- Plan/approval: C:/pt/analyses/prior-decision-collection-plan-20260930-v1.
- Live: C:/pt/priordecisions0930a/result.json; run_dev_sample_aac66ea3d2594610.
- Review: C:/pt/analyses/prior-decision-results-20260930-v1, verify.py, integrity.json,
  masked-public.json, masked-grading.json, settle.py, summary.json, sensitivity.json;
  receipts in hash-chained run_dev_priordecisionreview.
- Frozen grading SHA: sha256:283eb790044eae99c2218230aede18254efa89a35ef5d5257d239de8ce811106.
- Collector preparation had 31 focused tests, Ruff and an actual-input 16-response
  mock passing. This result-only change verifies documentation and saved execution;
  it changes no runtime code and produces no generalization or repair-success claim.
