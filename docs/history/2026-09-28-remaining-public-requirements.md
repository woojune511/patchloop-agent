# Remaining public requirements after time-extended submission

Date: 2026-09-28. official=false; provider-free operator analysis.
Follows [time-extension result](2026-09-28-time-extension-results.md).

## Question and scope

Why is the submitted patch still inadequate against independently checkable public
requirements, even though the two earlier public counterexamples now pass? No private
evaluator tests, logs, reference patches or current upstream solution were inspected.
The public issue, frozen candidate and recorded actions/checks are the evidence.
No paid model calls, candidate edits, runtime changes or evaluator reruns occurred.

The exact submitted patch is
`sha256:003d549bab52d602d4efb2c0c80b7002c4ab587da5c3fb086ea1a2977351bb50`.
It documents finite alpha >= 1/2, exact pure/product branches and numerical mixed-state
optimization. Its final CQ-branch removal routes mixed CQ inputs through that optimizer.

## Independent expectations

Muller-Lennert et al., [On quantum Renyi entropies](https://arxiv.org/html/1306.3142v4),
Proposition 9 gives conditioning on classical information; Theorem 10 gives duality.
We specialize those statements to diagonal joint distributions and bipartite pure
states (empty third subsystem), respectively. These expectations do not call the
candidate's CQ helper or objective implementation.

For joint probabilities p[a,b], the classical expectation is
`alpha/(1-alpha) * log2(sum_b (sum_a p[a,b]**alpha)**(1/alpha))`.
For pure Schmidt probabilities p and beta=alpha/(2*alpha-1), it is `-H_beta(p)`;
compute powers in log space using logsumexp. At alpha=1/2 use log2(max(p)).
These restricted families avoid assuming a closed form for general noncommuting CQ
states or confusing which subsystem is classical.

A fixed diagnostic set contains 15 cases: pure Schmidt weights (0.8,0.2) at orders
0.5, 0.50001, 0.5001, 0.75, 2; and joint distributions [[0.4,0.1],[0.2,0.3]] and
diag(0.3,0.7), each at 0.5, 0.75, 1.5, 2, 3. Absolute tolerance is 1e-6.
Eight pass and seven fail. This is a purposive diagnostic, not an accuracy estimate.

## Confirmed defects

1. Pure-state boundary underflow. At alpha=0.50001, beta is about 25,000.5. The
   existing `renyi_entropy` utility directly raises eigenvalues to this power, so
   both 0.8**beta and 0.2**beta become zero. The pure helper yields -infinity, then
   `max(downarrow, pure)` silently substitutes -0.556398021 rather than the correct
   -0.321940972 (error -0.234457049 bits). The helper emits a divide-by-zero warning.
   In an operator-only process, substituting stable log-space entropy calculation
   alone restores -0.321940972. The candidate files remain unchanged. This is an
   exact-branch/dependency numerical failure masked by a one-sided invariant guard,
   not merely inexact generic optimization. Neighboring selected orders pass.
2. Mixed-state objective crash. Both simple diagonal distributions raise TypeError
   at alpha 1.5, 2 and 3. The traceback ends at line 174 in the candidate objective:
   `float(np.real_if_close(trace_term))`. At alpha=2 the failing intermediate trace
   is approximately 1.136771311e9 + 7.450580597e-9j. A negligible relative imaginary
   residual survives real_if_close's scalar tolerance and cannot be cast to float.
   The previous decoder repair changed a different trace conversion at line 283;
   it did not cover this objective conversion. This is a reproducible unhandled
   exception on valid public inputs, not an expected optimizer accuracy limitation.

Both outcomes reproduce with identical numeric observations in the existing solver
probe environment (Python 3.12, prepared dependencies) and evaluation-image public
command environment (Python 3.13). Thus these reproductions are not explained by
missing wheels, package readiness, or an evaluator-only environment mismatch.

## Verification coverage and process

| Public obligation | Available evidence | Remaining implication |
| --- | --- | --- |
| uparrow finite alpha >= 1/2 | Boundary pure case wrong; valid mixed orders crash | Claimed support is too broad for implementation |
| Optimize over B on small states | Prior noncommuting witnesses now pass | Local improvement does not cover commuting families/orders |
| Classical/quantum special cases | Commuting subset has exact independent expectation | Even this simple subset has exceptions |
| uparrow >= downarrow | Enforced by max; earlier example passes | Cannot establish objective correctness; masks pure underflow |
| Preserve original API behavior | Final registered regression: 14 pass | Selected assertions use default downarrow; not uparrow coverage |
| Clear limitations and unsupported inputs | Solver tolerances and finite range documented | Documentation does not excuse errors inside advertised range |

All four new B probes fixed alpha=2 and pursued the non-orthogonal CQ dispute. They
were not devoid of independent evidence: two produced decisive optimizer/grid
counterexamples. But after the final CQ shortcut removal, only the base regression
was rerun. The subsequent extended-time decision submitted immediately, describing
broader numerical adequacy as a limitation. There was no final changed-path check
across input families or near the supported range boundary. The first observed
complex-to-float crash was repaired locally in density decoding; an analogous
conversion in the objective remained untested. These are trace-supported coverage
and repair-generalization gaps, not evidence that more budget alone would fix them.

## Durable evidence and limits

- Matrix + cloned frozen candidate + bound program/results + audit:
  `C:/pt/analyses/remaining-public-requirements-20260928-v1`;
  journal `run_dev_remainingpublic`, final `audit.json`.
- Cause tracing and in-process pure-helper counterfactual:
  `C:/pt/analyses/remaining-public-causes-20260928-v1/results.json`;
  journal `run_dev_publiccauses`.
- Same program through the actual prepared DockerProbeSandbox:
  `C:/pt/analyses/remaining-public-probe-environment-20260928-v1/result.json`;
  journal `run_dev_publicprobeenv`.
- All Docker processes completed and cleaned up; existing images only, no pull/build.
  The diagnostic scripts collect failures and exit zero intentionally. Probe status
  passed means execution completed; row-level semantic results are 8 pass / 7 fail.
- The submitted source diff hash was rechecked unchanged. Prior records were preserved.
  None of these operator observations were sent to the coding agent.

The benchmark's private failure cause remains NOT_ESTABLISHED. We have proved two
public defects, not identified the hidden assertions or established exhaustive
correctness after a proposed fix. No candidate repair or harness policy was adopted.

## Next decision

The next general-agent question is whether verification follows newly activated
execution paths and advertised input ranges after a repair, and whether fixing a
conversion failure prompts checking analogous operations. Audit the existing
current-diff coverage/working-note mechanism before adding another prompt or gate.
A future bounded intervention should expose public coverage obligations, not these
specific formulas or counterexample values. Keep success measured by correctness
and submission, rather than probe count or detection alone.
