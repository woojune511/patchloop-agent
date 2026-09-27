# Toqito unsubmitted patch: public validation and process diagnosis

2026-09-28, `official=false`. No model/count request or hidden evaluation. Original
run `run_dev_33068b6e257f423a` remains unsubmitted and correctness NOT_RUN.

## Direction correction

The user clarified that more budget is acceptable when the task needs it. $1.20 was
an experiment allocation, not a product requirement. The earlier cost audits remain
valid arithmetic evidence but do not establish excessive investigation or a need to
change scheduling. Budget-policy work is deferred. This diagnostic asks whether the
stored implementation and its public evidence are technically sound.

## Candidate and isolation

The exact unsubmitted diff is
`sha256:fdd4fa640b555cc3ef43317ec9b4b3fa2a694902f11d571f43fb48dd2a318745`.
A separate checkout of the prepared public base received that patch. Both its diff
and the original run checkout's diff matched this identity before/after validation.
No production patch, benchmark test, original evidence or agent policy was edited.

Existing pinned evaluator image was used only to execute public checks in its
Python 3.13 environment, with network disabled, read-only root/workspace and bounded
resources. The custom math cases are operator-authored diagnostics, not additions to
the benchmark or tests authored by the solving agent. No image was pulled or built.

The first auxiliary checkout attempt used host CRLF conversion and could not apply
the patch; it executed no tests. That v1 directory is preserved. V2 specified
core.autocrlf=false before clone and verified the resulting diff byte identity.

## Results

- Existing registered public regression: **14 passed, 1 deselected**, exit 0.
  The deselection is the already-frozen obsolete test asserting uparrow unsupported.
- New issue-based cases: **11 passed, 1 failed**, exit 1. Passing cases cover product
  and Bell states at alpha=0.5/1/2, nonmaximally entangled pure alpha=0.5, alpha=1
  agreement, invalid variant/order and the agent's commuting CQ example.
- Independent follow-up: two strictly positive definite witness states reproduce
  the failed inequality. Exit 0 confirms this counterexample, not candidate correctness.
- No timeout or cleanup failure; no owned PatchLoop containers remained.

### A concrete mathematical counterexample

For A classical and B quantum, use

`rho_AB = 1/2 |0><0|_A tensor |0><0|_B + 1/2 |1><1|_A tensor |+><+|_B`,
where `|+>=(|0>+|1>)/sqrt(2)`, with alpha=1/2.

The candidate returns **0.5849625007211562**. Choose the valid B density operator
`|v><v|`, where `v=(|0>+|+>)/norm(|0>+|+>)`. Direct evaluation of the sandwiched
objective at this single feasible choice gives **0.771553303163612**. An optimized
supremum cannot be below a feasible objective. The gap is about **0.18659 bits**.
No numerical optimizer or assumption of a globally optimal witness is required.

For strict positivity, replace sigma by `(1-epsilon)*|v><v| + epsilon*I/2`.
At epsilon=1e-4 and 1e-6 the feasible objectives are 0.7714935435407103 and
0.7715527055796358, still above the candidate by more than 0.18. The second check
uses the independent rank-one block fidelity expression and confirms import from
`/workspace/toqito/state_props/sandwiched_renyi_conditional_entropy.py`.

The issue's cited primary source distinguishes the optimized sandwiched definition
from the Petz closed form: [Tomamichel, Definition 15 and Lemma 9](https://arxiv.org/html/1504.00233).
The candidate CQ helper computes the latter expression and treats it as an exact
sandwiched result for arbitrary CQ blocks. Our counterexample uses noncommuting B
blocks, for which this substitution fails. Taking max with the downarrow result
still returns 0.58496 and does not fix it. The special branch bypasses the optimizer.

## Information to action: what went wrong

The first agent probe exposed BFGS instability on the pure-state alpha=1/2 example.
Its follow-up Powell probe recovered that pure-state value. This was useful public
investigation; successful process exits alone did not establish all assertions.

The follow-up's commuting CQ state is the diagonal joint table
`[[0.35, 0], [0.39, 0.26]]`. Its optimizer output **0.7981900091260226** agrees with
`H(A|B)` calculated directly from the classical column sums of square roots:
`log2(sum_b (sum_a sqrt(p_ab))**2) = 0.7981900091260214`.
But its expected value **0.7109373971934037** uses the row sums, giving **H(B|A)**.
Thus the reported 0.087 difference does not demonstrate optimizer failure.
The final candidate actually returns the correct 0.79819 on this commuting example.

After seeing that difference, the saved public plan/action rationale at events 108
and 127 explicitly says the optimizer misses the CQ closed form and chooses exact
special cases plus a fallback. The process failure is accepting an incorrect expected
value as authoritative, blaming the solver without checking conditioning direction,
and applying a different closed form beyond its valid regime. The stored rationale
also anticipates what hidden tests might exercise; that is agent speculation, not
hidden-test information exposure or evidence of their contents.

The final patch was never checked in the original run. We cannot infer whether the
agent would have caught this with more time/budget. What is now established is that
finishing the existing public regression alone would not detect this semantic error.

## Implication and next step

Do not treat a larger allowance as sufficient by itself, and do not treat the $1.20
failure as proof that investigation was wasteful. The concrete issue is validation of
the expected value and applicability of a special-case formula. Keep the saved patch
unchanged as diagnostic evidence. A useful next agent experiment would test whether
it can validate its own expected values and catch this error during verification with
adequate resources. Any provided counterexample must be labeled operator feedback;
a fresh no-hint solve and a supplied-feedback repair are different experiments.
No paid allocation or new experiment is authorized by this record.

## Evidence

Root: `C:/pt/analyses/toqito-public-validation-20260928-v2`.
Hash-chained journal: `runs/run_dev_toqitopublicaudit.jsonl`.
Results: `public-tests.json`, `public-math-cases.json`, `witness-confirmation.json`,
`summary.json`; result and code artifacts are journal-bound.

Operator programs: `C:/pt/toqito_public_validation_0928_v2.py`,
`C:/pt/toqito_public_cases_0928.py`, `C:/pt/run_toqito_math_cases_0928.py`,
`C:/pt/toqito_witness_confirm_0928.py`, `C:/pt/run_toqito_witness_confirm_0928.py`.
All three container checks took under 15 seconds combined (excluding checkout/setup).
This does not establish coverage of every branch or arbitrary-state accuracy.

Documentation layout: 5 passed after shortening current summaries. Runtime and task
packages were unchanged; no new mock/full-suite or provider run was performed.
