# Expectation reconciliation: live results

## Outcome

Completed the preregistered conditional probe-construction diagnostic after the
user's new $4 approval. official=false. A generated 0/2 supported expectations;
B generated 1/2. The generic reconciliation cue did not reliably prevent reuse of
the contradicted CQ formula. No default adoption or general improvement claim.

| Sample | Expectation | Unchanged operator execution | New model cost |
| --- | --- | --- | --- |
| A1 | Contradicted, two noncommuting CQ cases | Reached API; failed invalid expected-value assertions | $0.280405 |
| A2 | Contradicted, noncommuting CQ | Setup equality stopped before API: NOT_RUN behavior | $0.104677 |
| B1 | Supported, diagonal non-product classical case | PASS | $0.238911 |
| B2 | Contradicted, noncommuting CQ | Setup equality stopped before API: NOT_RUN behavior | $0.247767 |

Four generation calls and four input counts; 535.423 seconds; known total
$0.871760. Unused $3.128240 is closed. No retry, model feedback or continuation.
Each generated program was syntactically valid and executed once unchanged on the
same isolated frozen patch. All cleanups confirmed; no timeout/output truncation.
The ordinary 30-second child timeout was retained; observed host execution times
include snapshot/setup/cleanup overhead. Benchmark acceptance and safety NOT_RUN.

## Process evidence and interpretation

Both arms forced the registered run_probe function. B alone received the generic
instruction to reconcile expectations with contrary observations. Four dispatch
request hashes match the frozen cells; both arms retain the prior counterexample
with cq_shortcut=0.4081546342464168. The intervention changes conditional probe
construction, not spontaneous verification selection. Source patch hash remained
051bc0ad8f0cc4aeca528cc0ad8a681d81b79abe2fa357e391fea5b4613de34d
before/after execution, as did the original workspace diff.

All responses frame the remaining question as a current-diff CQ/classical check.
Three reassert a general CQ closed form without addressing the contrary observation.
B1 selects a valid commuting restriction but does not explicitly reconcile the
prior noncommuting evidence. This supports one sound restricted probe, not proof
that the model understood or resolved the contradiction. The small 0/2 versus 1/2
comparison is insufficient to establish a treatment effect or dependable policy.

A2 and B2 compare a computed trace 0.9999999999999999 exactly with 1.0 in
check_setup. Their API assertions are unreached, independently of their invalid
oracles. This repeats the generic numerical setup issue in both arms.
A1 reaches the API: actual up values 0.2811691164 and 0.3886472179 exceed both
downarrow values, but fail the asserted CQ expectations 0.2185794239 and
0.3078844352. These failures do not establish candidate defects.
B1's diagonal table [[0.5,0],[0.25,0.25]] has expected up 0.6115161727387654;
observed 0.6115161727387678 (error 2.44e-15), down 0.5849625007211555.
It exercises the mixed-state optimizer on a valid non-product case, not all CQ inputs.

## Independent oracle review

For alpha=2 and rank-one CQ blocks, any positive trace-one sigma gives a feasible
conditional entropy -log2(sum_i p_i^2 * <v_i|sigma^(-1/2)|v_i>^2). The optimized
entropy is at least this feasible value. Simple explicit 2x2 witnesses contradict
all three noncommuting probes without candidate execution or numerical optimization:

| Probe case | Claimed optimum | Feasible entropy | Gap | Probe tolerance |
| --- | --- | --- | --- | --- |
| B2 p=.4, theta=pi/4 | .218579424 | .253178759 | .034599335 | .001 |
| A2 p=.35, theta=pi/4 | .206339486 | .264113968 | .057774483 | .005 |
| A1 p=.6, theta=pi/4 | .218579424 | .256782051 | .038202627 | .005 |
| A1 p=.63, theta=pi/5 | .307884435 | .375469239 | .067584804 | .005 |

The first two use sigma=[[.6,.3],[.3,.4]]; the latter two use
sigma=[[.8,.15],[.15,.2]]. Both are positive definite and trace one.
The latter witness was chosen from seven simple feasible matrices before execution;
this operator analysis never entered model context. For B1, the commuting objective
minimization gives (sum_b sqrt(sum_a p_ab^2))^2 by Cauchy-Schwarz, justifying its oracle.

Anonymous response content was graded and journaled before executions and arm/cost
mapping. No per-sample timestamp/order metadata was displayed. Aggregate terminal
cost/timestamp were visible. The same investigator performed the assessment; this
is arm-masked review, not independent blind judging.

## Evidence and next decision

Design: [frozen protocol](2026-09-28-expectation-reconciliation-design.md).
Live: C:/pt/reconcile0928a, run_dev_sample_b29446eff5ec4b3c.
Report: C:/pt/analyses/expectation-reconcile-results-20260928-v1/report.json;
pre-mapping-grades.json and operator-executions.json retain separate stages.
Journal run_dev_reconcilereview binds report and scripts; source journal integrity,
dispatch identities, cost sums, common snapshots and cleanup were checked.
Official pricing rechecked on execution UTC date (2026-09-28):
https://developers.openai.com/api/docs/models/gpt-5.4.

Do not add this cue to the default harness on this evidence. The smallest next
engineering change is a generic computed-float example for check_setup using an
explicit tolerance predicate, with a real mismatch control. This addresses the
observed early-stop mechanism only. Expectation validity remains a separate
unsolved problem; neither more probes nor setup PASS establishes semantic coverage.
No runtime change, paid successor, repaired replay or benchmark rerun in this turn.
