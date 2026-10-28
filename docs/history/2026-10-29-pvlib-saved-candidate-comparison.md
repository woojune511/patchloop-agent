# pvlib saved candidates: reported call repaired, acceptance failure unexplained

## Material Passport

- Workflow: academic-research-suite experiment-agent, local run and validation.
- Status: LOCAL_EXECUTED; public measurements verified, acceptance cause unresolved.
- Task: dev-train current-dev20/5, pvlib-1707; official=false, claim-ineligible.
- Scope: three saved code variants, public source and 14 declared case groups.
- New provider calls: zero. Private evaluation: NOT_RUN. Runtime changes: none.

## Question and selection

The [six-run comparison](2026-10-29-verification-policy-six-v2-results.md)
recorded public checks PASS for both pvlib candidates but independent acceptance
PASS for A and FAIL for B. Its public-source analysis identified a possible
difference between an absolute-angle guard and a clipped-cosine guard, without
testing whether this difference violates the public contract.

This concrete unresolved question was selected before spending on another live
run. The user authorized comparing the original and saved A/B on public inputs,
then connecting differences to the recorded observations and edits. The comparison
must allow the suspected explanation to weaken: different outputs alone do not
identify an error when the public expected behavior is unspecified.

## Design and execution

Evidence root: `C:/pt/pvlib-saved-comparison-v1/`. `plan.json`, `public-cases.json`
and the generated helper were sealed before target execution. Each variant used
the same public base `40e9e978c170bdde4eeee1547729417665dbc34c`, prepared dependencies
and Docker probe profile. No provider or evaluator was invoked; no image was
pulled/built. The original and candidates were recreated in separate external
workspaces, not in the historical runs.

The 120-second controller budget admitted three target executions, each bounded
by the existing 30-second probe limit. Recorded execution durations were 23.149,
18.073 and 17.566 seconds. These are execution receipts, not a performance study.
All three returned exit 0 with confirmed cleanup and no timeout or truncation.
Source, full diff, helper and profile hashes were verified before/after execution.
The new `dev-run-v1` journal records matched action IDs/input hashes and receipts.

Only the exact public task, `pvlib/iam.py` and `pvlib/tests/test_iam.py` supplied
expectations. Six groups reflect explicit public issue/doc/test expectations;
other groups are labeled extensions, parameter-boundary hypotheses or exploration.
The suite checks arrays and Series, custom index preservation, coating behavior,
the geometric endpoints and NaN. It is not 42 independent trials or a solve rate.

## Results and mechanism

| Public or exploratory input | Original | Saved A | Saved B | Interpretation |
| --- | --- | --- | --- | --- |
| Scalar 100 degrees, n=1, default K/L | NaN | 0 | 0 | Both repair the explicit report |
| n=1 array/Series including -100, -90, 0, 90, 100, 180, NaN | Back-facing NaNs | Expected values | Expected values | Both satisfy selected extensions; Series/index retained |
| Existing public default/coating/scalar expectations | Match | Match | Match | Within existing numerical tolerances |
| 90 degrees, n=1, K=0 or L=0 | NaN | 0 | NaN | Different degenerate boundary behavior; zero is inferred |
| 300 degrees, n=1 | 0.9920319148370607 | 0 | 0.9920319148370607 | Outside geometric AOI domain; no required zero established |

At the degenerate boundary, B tests whether the clipped incidence cosine is
exactly zero. Floating-point cosine at 90 degrees is slightly positive, so this
guard does not select it. The refraction square root nevertheless rounds to zero;
zero absorption then leaves an invalid division in the exponential argument.
A's direct absolute-angle guard replaces the final result with zero.

This source-backed explanation is consistent with the observed arrays
`[1, 1, 0, 0]` for A and `[1, 1, NaN, 0]` for B on `[0, 45, 90, 100]`.
K=0 and L=0 expose the same K*L=0 mechanism, not two independent repair failures.
The public parameter docs and existing tests do not settle this exact boundary:
zero absorption before a grazing limit differs from a grazing limit with positive
absorption. We therefore do not convert the hypothesized zero into a benchmark
oracle or assert that this caused the historical acceptance FAIL.

The earlier periodicity suspicion also needs narrowing. `physical` defines AOI
as the angle between two vectors but does not promise absolute clipping of values
outside that geometric range. Other IAM functions' clipping policies do not
automatically define this function's contract. At 300 degrees A changes original
behavior and B preserves it; neither fact establishes intended correctness.

Scalar result types differ as well: original float64, A zero-dimensional ndarray,
B int at 100 degrees. Public scalar tests assert numerical equivalence, so this
is a compatibility observation, not a demonstrated violation. Numerical warnings
remain in both patches; neither eliminates all invalid intermediate calculations.

## Connection to the model trajectory

`trajectory-audit.json` verifies all 11 A and 10 B counted/dispatched inputs and
the public CAS hashes. B's helper result at sequence 61, from action
`call_svbQFqmpodhhm9oGvX2eH8ZE`, contains n=1/default arrays at
`[90, 100, -100, NaN]`. It reaches the following input (67) and the edit inputs
(81, 95, 109). Final input 138 retains current-diff public-check PASS. These
transitions contradict missing feedback as the explanation.

Both candidates add scalar, array and Series tests; the type dimension was not
simply ignored. A saw the adjacent `ashrae` direct-angle guard in its first-edit
source context; B did not. This is an available-source difference, not proof of
its causal influence. Neither tested the newly investigated K*L=0 boundary.

B's three accepted edits declare the mask, apply it, then add tests. They are
one hypothesis split into three mutations, not three failed repair hypotheses.
Before finish, 11 model responses, 29 tool actions, approximately USD4.019664 and
1,731 solver seconds remained, but no edit slots remained. This reduces later
repair capacity. It did not block a known failing public check here: no such
failure remained. Money/context/output exhaustion and absent scalar/type tests
are unsupported explanations for this particular outcome.

## Decision and limits

Both saved candidates repair the exact report. Mandatory replay of that call
alone would not distinguish them. Do not add a generic gate, increase the budget
or claim a policy improvement based on this comparison. The historical isolated
acceptance difference remains recorded, with its cause UNESTABLISHED.

This result changes the earlier suspected explanation from an assumed broader
angle error to a measured boundary difference with unresolved contract semantics.
Keep runtime behavior unchanged. A fixed-runtime development panel can examine
repeatability and remaining failures; it requires a separate concrete live plan
and authorization. It would not establish held-out generalization or card causality.

All 11 ARS interpretation fallacies were considered in `analysis.json`. No
p-values, independent-case success rate or population inference are used. Operator
diagnostics do not retroactively become solver observations or checks.

## Boundary incident and reproducibility

One delegated source reviewer accidentally retrieved `hidden/oracle.json` during
an overbroad path search. It reported the incident without returning the contents
and stopped. Its judgments were excluded. A fresh reviewer with no inherited
context read only the three exact public files and later the public measurements.
No private content was supplied to the parent, comparison helper or solver.
This incident is retained rather than claiming that every worker avoided private
reads. The local comparison is public-evidence-only and not a blinded quality claim.

Reproducible artifacts include `run_compare.py`, `helper.py`, `execution-helper.py`,
three patches/requests/receipts/measurements, `summary.json`, `audit_trajectory.py`,
`trajectory-audit.json`, `analyze.py` and `analysis.json`. The execution script
rejects reuse of its journal. Recomputing the public trajectory with `--stdout`
does not overwrite prior receipts. Original run journals remained hash-identical.

The saved patch hashes are A
`sha256:7041413d0eda413ca2f9072c8ea7cdecd23009b920963c50ca9856724fa34686`
and B `sha256:6033ce71c14461d85acf565e6dc8ba090b5c4846a62ebe7bcf8a2b4b92d720ad`.
No paid allocation was reopened; no new task repair or private evaluation occurred.

Validation: execution helper/runner Ruff and syntax checks PASS; documentation
layout/link checks 5 PASS in 0.109 seconds; `git diff --check` PASS. The runtime hash
remained `sha256:08b32133d33201efb3b55cd44db917ff76ffc8752676e00f5cdc366280b16b1e`.
No runtime tests or mock evaluation were repeated for this documentation-only change.
