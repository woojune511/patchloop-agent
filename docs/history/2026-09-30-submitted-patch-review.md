# Public review of the four submitted patches

Status: COMPLETE / provider-free operator review / official=false.
This is a follow-up to the [closed four-row comparison](2026-09-30-probe-replay-comparison.md),
not a new agent run or a replacement for its recorded evaluator verdicts.

## Scope and controls

Reviewed all four content-hash-verified submitted patches against the original
public issues and public source. Each patch changes one relevant file without
task-specific output constants, dependency changes or unrelated edits. The two
Darts implementations share the same approach; the two MontePy implementations
differ in optimization-flag reset behavior.

Concrete source-level concerns determined the checks before execution: Darts
derives encoded columns from raw categories minus one dropped category and builds
inverse mappings only from surviving columns; MontePy clears the same public
assignment via different internal paths. Fresh external copies of the original
public prepared sources received the exact submitted patches. Original sources
were tested as controls. Existing digest-pinned evaluator images supplied the
dependencies, with network disabled and read-only source mounts. No private spec,
hidden test, reference patch, model call or new task package was used. Historical
artifacts and submitted patches were not changed.

## Findings: both Darts patches are incomplete

### P1: inverse transform silently loses a zero-width input column

Input categorical data: `constant=['k','k','k','k']`,
`variable=['a','b','c','d']`, with `OneHotEncoder(drop='first')`.
The fitted encoder emits zero columns for constant and three for variable.
Both submitted patches now transform successfully, with columns variable_b,
variable_c and variable_d. However, inverse_transform returns only variable,
filled with `['k','k','k','k']`: it loses constant and misassigns its decoded values
to variable. The required original two-column round trip is not preserved.

Mechanism: deleting the sole category leaves an empty forward mapping. No inverse
mapping entry retains that original column. `_add_back_static_covs` then walks
only surviving encoded columns and consumes the first decoded column under the
wrong surviving name. This is information loss in the mapping, not a reason to
change the reference observation or reinterpret successful execution as correctness.

The original source failed during forward transformation on this input. Thus this
is a remaining correctness gap on a newly reachable inverse path, not evidence
that a previously successful original round trip regressed.

### P2: grouping categories still makes output-width metadata incorrect

Input: `cat=['a','a','b','b','c','d']`, with
`OneHotEncoder(min_frequency=2, drop='first')`. An independently fitted encoder
produces two output columns, while both patches derive three from categories_
after deleting the drop index. StaticCovariatesTransformer raises
`IndexError: index 2 is out of bounds for axis 1 with size 2`.

The grouped-without-drop control also fails in the original and both patched
sources (three actual outputs versus four raw categories). Category grouping is
a pre-existing unsupported boundary that the drop-only patch does not address;
it is not a new regression caused by either A or B. The public issue's expectation
of respecting the underlying transformer's output width remains only partly met.

| Selected public case | Original | Darts A / row 1 | Darts B / row 2 |
| --- | --- | --- | --- |
| Three categories, drop first, round trip | Forward FAIL | PASS | PASS |
| Binary drop if_binary, round trip | PASS | PASS | PASS |
| Grouping plus drop first | Forward FAIL | Forward FAIL | Forward FAIL |
| Grouping without drop (pre-existing control) | Forward FAIL | Forward FAIL | Forward FAIL |
| Zero-width original column, round trip | Forward FAIL | Forward PASS / inverse FAIL | Forward PASS / inverse FAIL |

These are deliberately selected operator cases, not an agent success-rate sample.
The public regression source uses OneHotEncoder without drop/min_frequency and
does not exercise the two failing cases. The existing eight-test PASS established
preservation of that suite, not coverage of these new behavioral boundaries.
A separate replay of the unchanged registered base-regression on the original
unpatched Darts source also passed all eight tests (0.70 seconds). Thus the
suite's PASS alone does not discriminate the original defect from either repair.

## MontePy: no confirmed requirement defect in the selected checks

Both patches passed six selected combinations: set None/delete, each detached,
attached with no default universe, and attached with an existing universe 0.
Checks include repeated clearing, retaining the existing default object's identity,
avoiding duplicate defaults and preserving rejection of an invalid integer value.
The original source fails the new clearing operations, as described by the issue.

One additional public behavior differs: after setting not_truncated=True, clearing,
then assigning a new positive universe, B returns False and A returns True for
not_truncated. B explicitly resets the flag; A retains it. The public issue does
not settle whether clearing must reset this independent optimization flag. This
is recorded as an unresolved semantic difference, not an asserted defect or a
quality advantage for B. No broad MontePy correctness claim follows from six checks.

## Implication and next question

Keep all original isolated acceptance/safety PASS verdicts unchanged. This review
adds narrower public counterexamples; it does not change hidden evaluation, retry
the panel or manufacture a B advantage. Both Darts arms have the same confirmed
gaps, and neither used a probe in the live run.

The observed failure is incomplete verification of encoded feature ownership and
inverse schema preservation. The patch mechanism accounts for drop indices but
not all output-width changes or restoration of zero-width original columns.
Runtime enforcement, model test selection and issue interpretation are competing
explanations for why the agent submitted without detecting this; this review does
not establish which intervention would improve the agent.

The smallest public reproductions are now fixed outside the repository. Preserve
them as operator evidence, not model hints or new task-private oracle cases. No
prompt reminder, mandatory probe gate, new runtime method, operator correction or
additional paid allocation is introduced. Selected baseline remains probe-policy
none. PR #11 was merged at d10b78b3 after its exact-head CI passed on both OSes.

## Evidence

Root: `C:\pt\reviews\probe-patches-20260930-v1`.
Review journal: `runs/run_dev_b66c161f8ed941cb.jsonl`.
Final event hash: `sha256:9e2818849b6c4ffa1816ae9caedc83f86ec1e0e45b08fa3ea4303b02f30d8f80`.
Programs: `darts_cases.py`, `montepy_cases.py`; orchestration: `run_review.py`.
Darts program hash: `sha256:2d85d35a71120fc9f8eaf65f03656e9ff75e2c52c76d885c6a8a8676d9b9a522`.
MontePy program hash: `sha256:2fba4d4e6c86bcd42ff34384aae8b46ecf73e8286bdf793030e7ff84ce47e951`.
Each receipt binds source/patch identity and the sandbox execution result. Six
container executions completed with confirmed cleanup; case FAIL is distinct
from execution failure. Individual submitted-patch hashes remain in the original
comparison record and the new review journal. All generated evidence is external
append-only dev-run-v1 state; no agent/provider execution was performed.

The separate original-source public regression receipt is in
`runs/run_dev_6dab5c1843fe4386.jsonl`: eight tests passed, execution passed and
cleanup succeeded. This was one additional container execution, with no provider
call or change to the registered check.
