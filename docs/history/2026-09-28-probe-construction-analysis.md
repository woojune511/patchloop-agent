# Probe construction: exact setup misuse and reuse of a contradicted expectation

2026-09-28. Provider-free follow-up to the
[policy comparison](2026-09-28-invalid-probe-policy-results.md). No new model call,
container run, candidate edit or runtime change. Existing actual input was verified
against its native/canonical public delivery; conclusions concern public evidence,
not encrypted reasoning.

## Setup failure

The sampled probe compares a computed trace, 0.9999999999999999, with 1.0 using
`check_setup`. The implementation performs type-strict scalar equality and raises
on mismatch. This matches its contract; it is not an environment or candidate bug.
The model-visible tool description asks for setup checks, accepts finite floats,
and specifies type-strict scalar comparisons, but offers only a categorical-mode
example and no numerical-tolerance example. That is a plausible usability gap,
not evidence that the helper silently violated its documented semantics.

Five local helper characterizations: the rounded trace fails; literal 2.0 passes;
an explicit `math.isclose(..., rel_tol=0, abs_tol=1e-12)` boolean passes; .99 under
the same predicate fails; int 1 versus float 1.0 fails. These tests execute only the
stdlib helper, not the generated probe or candidate. Numerical tolerance must be
chosen explicitly for the invariant; a global tolerance would weaken intentional
categorical comparisons and is not justified by this example.

This failure had already occurred in the inherited run: sequence 260 has the same
0.9999999999999999-versus-1.0 mismatch. At 269 the model changed the setup checks and
continued successfully. One boolean check there tested a literal projector rather
than the eventual candidate input, so it is not evidence of a generally sound
setup procedure. That earlier recovery did not prevent recurrence in the sample.

## Expectation construction and delivered counterevidence

The model previously rejected the CQ shortcut using a non-orthogonal example:
sequence 396 reported shortcut 0.4081546342464168, grid 0.46973610922837294 and
direct optimization 0.490645387475638. At 423 it explicitly acknowledged the
contradiction and removed the shortcut's call path. It did not remove the helper
definition, which still describes itself as a CQ closed form.

Crucially, **the counterevidence was still in the sampled input**:
`input[4].content.state.recent_probes[0]` after decoding contains the non-orthogonal
question and those exact numbers. The discarded hypothesis was not absent due to
compaction. An initial absence hypothesis was rejected by a full nested-input scan.
No retained finding summarizes the invalid formula/applicability restriction, but
absence from the notes alone is not loss from the actual request.

The same input exposes the dormant helper in the current diff and source. AST
inspection finds its definition once and no direct call to it in that file.
The new probe reconstructs the same mathematical expression and labels it an
independent expected value, now on a different noncommuting CQ state. This bypasses
the independence that matters: using separate code does not independently justify
the same previously contradicted assumption. Actual copying versus recall cannot
be identified from public evidence.

The public task also asks for a standard CQ closed form while explicitly excluding
Petz entropy, without supplying this particular formula or establishing its scope.
That is a competing cue, not a validation of the generated expectation. Current
source, task wording, historical probe facts and model-authored mathematical claims
must retain different authority. The separate feasible-state counterexample in the
prior result refutes the sampled formula; its setup failure prevented the generated
assertion from reaching the API, not from being semantically wrong.

## Implication and next action

The immediate causes differ: an inappropriate exact comparison blocks execution;
an unsupported mathematical expectation would make execution misleading anyway.
Fixing syntax/setup alone is therefore insufficient. More context storage is not
supported as the first remedy: the decisive contrary observation was delivered.

The smallest engineering candidate is a generic numerical setup example using an
explicit boolean tolerance, retaining exact helper semantics. Its benefit still
needs a bounded test. The higher-value causal diagnostic is whether requiring an
expectation to be reconciled with existing contrary public observations prevents
reusing a rejected assumption. Keep this separate from adding task-specific math,
mandatory retry gates or claiming better task correctness from more probe calls.
Neither change nor paid experiment is executed by this analysis.

Evidence: `C:/pt/analyses/probe-construction-analysis-20260928-v1/report.json`,
hash-chained journal `run_dev_probeconstruction`, and
`C:/pt/analyze_probe_construction_0928.py`. Runtime contract:
[setup helper](../../.agent/probe-setup.md). Source journals and artifacts unchanged.
