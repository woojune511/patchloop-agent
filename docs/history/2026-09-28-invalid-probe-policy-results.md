# Post-invalid-probe policy comparison results

2026-09-28 KST, `official=false`. Follows the
[preregistered design](2026-09-28-invalid-probe-experiment-design.md).
The user approved the proposed fresh $4 cap. All four responses were collected in
A1/B1/B2/A2 order with gpt-5.4-2026-03-05 xhigh, 25,000 output ceiling and the exact
PatchLoop `.env`. No retries, automatic continuation or extra model calls occurred.

## Results

| Condition | Repeat 1 | Repeat 2 | Valid targeted behavioral recheck |
| --- | --- | --- | --- |
| A: unchanged input | finish_task | run_probe | 0 |
| B: two system sentences removed | finish_task | finish_task | 0 |

The removal did not increase rechecking in these two responses per arm. This small
exploratory sample does not establish a negative causal effect, significance or
general policy efficacy. All other request fields were frozen; source identity,
native delivery and intervention isolation were validated by the collector.

Known cost **$0.404483**, four counts/four provider calls, 131.029 seconds. Per-cell
costs: A1 $0.103480, B1 $0.0862365, B2 $0.0210195, A2 $0.193747.
Unused **$3.595517 is closed**. No submitted candidate, benchmark evaluation or
interactive continuation was produced by this response-only experiment; acceptance
and safety remain NOT_RUN. The earlier patch's PASS is separate evidence.

The three finish decisions explicitly acknowledged that the syntax-invalid probe
left behavior untested, then cited required-check PASS/submission eligibility.
A2 instead said a valid probe could change submit versus stop even without edits.
It selected a different noncommuting CQ example, not the original diagonal case.
Thus neither arm produced an exact repair/rerun of the original classical probe.

## Exact operator execution and expectation audit

The sole returned probe was syntactically valid and ran once, unchanged, in the
existing prepared Docker environment against an isolated copy of the fixed patch
`sha256:051bc0ad8f0cc4aeca528cc0ad8a681d81b79abe2fa357e391fea5b4613de34d`.
It stopped in `check_setup('rho_trace', ..., 1.0)` because the calculated trace was
0.9999999999999999. Exit 1, no timeout, cleanup confirmed. The API calls follow
this check and were not reached. This is setup failure / behavior NOT_RUN, not a
candidate correctness failure. Per design, no manual fix or second run occurred.

Its expected value has a separate mathematical error: at alpha=2, p=0.35 with
conditional pure states |0> and |+>, it treats the Petz-type CQ expression as the
exact optimized sandwiched entropy, yielding 0.20633948555758125. A positive-definite
feasible reference sigma=[[0.6,0.3],[0.3,0.4]] has determinant 0.15 and eigenvalues
0.18377223398316206 and 0.816227766016838. For these rank-one blocks the sandwiched
trace is sum_i p_i^2 * (<v_i|sigma^(-1/2)|v_i>)^2 = 0.8327099867655438.
The corresponding feasible entropy is 0.2641139684516675. A supremum cannot be
smaller than this feasible value: the gap 0.05777448 exceeds the probe's 0.005
tolerance. This scalar calculation uses no optimizer or candidate result and
independently refutes the claimed exact expectation. It is not a repaired probe run.

## Interpretation and evidence

Grades were recorded in shuffled order before arm/cost mapping. However, the review
artifact metadata exposed timestamps before the sanitized response display, so this
is not a strictly blinded or independent review. Action labels and setup outcome
are directly auditable; the subjective rationale review has that limitation.

Do not adopt the two-sentence removal based on these results. More probes alone are
not evidence of better verification. The recurring issue now spans both choosing
to close a known uncertainty and constructing a sound experiment/expected value.
The next useful investigation is the public expectation-construction process and
the exact-equality setup contract, without feeding the model this task's answer or
adding blanket mandatory retries. No additional paid work is authorized here.

- Live: `C:/pt/invalidprobepolicy0928a/result.json`, journal
  `run_dev_sample_28c0c5132b744969`.
- Frozen plan: `C:/pt/analyses/invalid-probe-policy-plan-20260928-v1/packet.json`, hash
  `sha256:8b9c366419ef8e5722eba1f4652f34d8cecc19d8ae93cb61e5741fdac5f0b01c`.
- Grades, one exact operator execution, scalar witness and budget closure:
  `C:/pt/analyses/invalid-probe-policy-results-20260928-v1/report.json`.
- Scripts: `C:/pt/review_invalid_probe_policy_0928.py` and
  `C:/pt/finalize_invalid_probe_policy_0928.py`.

Source journals, prior plans/results and submitted patch bytes were preserved.
No default runtime or task implementation changed during this experiment.
