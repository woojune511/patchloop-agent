# Expected-value provenance and same-input requirements

Date: 2026-09-28. Provider-free public evidence audit; `official=false`.
Follows [advice-removal results](2026-09-28-completion-advice-results.md).

## Question

Why did more probing produce a patch that satisfies the probes but violates a
public requirement? Trace the origins of expected values, actual returned source,
assertion inputs and the mutation rationale. This is evidence about public model
statements and programs, not access to private reasoning or proof of frequency.

## What was authoritative, and what was assumed

The public issue explicitly requires uparrow to be at least downarrow on small
bipartite states. It also asks for a standard CQ closed form from a cited definition,
but does not supply the executable block-power expression used in the probes.
This audit does not read or make new claims about the cited papers. The expression's
authority in the observed continuation must therefore be distinguished from the
task's explicit inequality requirement.

| Evidence | Actual content | What it does not establish |
| --- | --- | --- |
| First probe | Agent-authored block-power expectation; separately implemented PSD powers | Independent validity of that formula for the CQ case |
| CQ search, result 177 | One hit: the candidate's own newly written exact-branch documentation | Independent confirmation that the branch is exact |
| Reshape search, result 178 | The candidate's own CQ helper | Independent subsystem convention |
| Sandwiched search, result 176 | Mostly candidate source plus imports; truncated results | Exhaustive absence of other formulas in the repository |
| Public test read, result 195 | Lines 28–61: Bell, dimension, obsolete unsupported-uparrow and invalid-input tests | The requested CQ expected-value construction |
| Second probe | Block-power and normalized-block formulas on revealing, product and non-orthogonal states | Proof that rejecting one alternative validates the retained formula generally |

The second probe explicitly calls the candidate module's `psd_matrix_power` and
reconstructs the candidate's block-power expression. The first has a separate
matrix-power implementation but shares the same mathematical assumption. Code
separation alone is not independent validation. These observations do not imply
all shared helpers are inappropriate; they limit what agreement can prove here.

## The decisive inference and missed relation

Decision 206 asks whether the earlier discrepancy is a code bug or a wrong
expectation. The second probe rejects the normalized-block alternative on revealing
and product limits. At decision 221, the mutation's `causal_revision` says the
formula/subsystem hypothesis was falsified and attributes the discrepancy to the
`max(downarrow, classical_value)` guard. It removes that guard from exact branches.

This inference exceeds the evidence: those edge cases reject the particular
alternative; they do not independently validate the retained formula on the
non-orthogonal CQ input. The candidate's own description of its branch as exact
also cannot supply that missing evidence.

The first probe checks the inequality only on `mixed_state` at alpha 2, while its
CQ equality uses `cq_state` at alpha 0.5. It never calculates CQ downarrow alongside
that equality. The second probe similarly omits a same-input downarrow comparison.
Thus the equality and the independent requirement are evaluated on different inputs.

The prior journal-bound operator check applied both to that same CQ input after
repair: uparrow 0.5626401326, downarrow 0.5698489418, gap -0.0072088092. Both original
probe programs now pass, yet this explicit public inequality fails. The existing
feasible-state counterexample also remains; its evidence is linked in prior results.
No specific hidden evaluator failure is inferred.

The first probe's CQ assertion also aborts before its final error-message and
inequality assertions. Values were printed, but later claims that all those checks
passed overstate which assertions actually executed. Finally, the promised targeted
post-repair probe was dropped: only base-regression and finish followed the edit.
Those selected tests do not exercise the changed uparrow branch.

## Mechanism and next diagnostic

The observable failure is a combination of an unsupported expected value, weak
discrimination between competing formulas, and failure to apply an independent
requirement to the same changed case. Missing tools or missing delivery are not
supported explanations for this trace: seven actual input projections verify, the
public requirement was supplied, and the agent itself used it on another input.
This does not establish which prompt or model mechanism caused the inference.

Do not turn this into a toqito-specific harness formula or an obligatory probe quota.
The next bounded diagnostic should start before the guard-removal decision and
test a generic review of two questions: where the disputed expectation comes from,
and which independent public requirement can challenge it on the same failing input.
Prepare that comparison offline first, retain a matched unmodified control, and
exclude the operator's formula, witness and numerical answer. Measure whether the
agent actually tests and revises its expectation, preserves the independent property,
and verifies its final change. A longer explanation or more probes is insufficient.
This is a proposed intervention, not authorization for paid execution or adoption.

## Evidence and validation

- Audit: `C:/pt/analyses/oracle-provenance-20260928-v1/audit.json`.
- Hash-chained receipt: `runs/run_dev_oracleprovenance.jsonl` under that root;
  artifacts bind the report, extracted probe programs/assertions and script.
- Script: `C:/pt/audit_oracle_provenance_0928.py`.
- Source: `C:/pt/adviceofflive0928a`, branch A1, run `run_dev_33068b6e257f423a`.
- Reused operator receipts: `C:/pt/analyses/advice-public-checks-20260928-v1`.

Assertions checked all seven delivered projections, public requirement text, actual
search/read provenance, probe-source construction, the guard-removal mutation,
post-edit action sequence and the journal-bound same-input failure. No new provider,
Docker or check execution. Runtime and closed historical records are unchanged;
documentation layout checks are the relevant repository validation for this audit.
