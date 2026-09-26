# Independent candidate diagnostic

The opt-in `alternative` argument on `diagnostics.candidate_review_repair.run_seeded`
adds an independently generated public patch to the existing saved-candidate repair
loop. Omission preserves the original behavior. This is an experimental operator
seam, not a CLI option, default policy or separate reviewer tool.

`diagnostics.independent_candidate.Candidate` permits only a bounded patch, its
exact SHA-256 and the public base identity. The base must match the seeded run.
Extra fields, empty payloads, hash mismatches and combinations with other review,
feedback, paired-observation or completion-advice interventions fail before runner
entry. The operator must verify the producing run's public task/base and bind the
patch to its exact public submission; the seam does not establish independence.

The model receives the alternative as unverified, base-relative data. It is not
applied, does not authorize an edit, and does not carry previous actions, notes,
plans or evaluator outcomes. The normal seeded-candidate notice stays in both arms.
The new instruction asks for a substantive behavioral difference, a public expected
outcome, and a distinguishing observation connected to the next edit or submission.
Coincident candidates may proceed normally. Current-source reads and ordinary
edits/checks/probes remain available; probes execute only the current workspace.

The exact alternative is stored in public CAS and journaled before the first turn.
Its context field records whether its patch matches the current diff. The imported
seed consumes one mutation slot; showing an alternative consumes none. System and
planning prompts, registered tools, check/finish gates, cost admission, continuation,
source isolation and private evaluation remain unchanged. Run scoped hooks only in
a dedicated sequential process.

An experiment may allocate the same total dollars to direct reconsideration and
independent generation plus comparison. Account for both B stages, fix their caps
before dispatch, and do not transfer unused generation allocation. Without a
submitted generation patch, mark the B final outcome NOT_RUN. Never select or reject
the alternative using its hidden evaluation result. Generation and final acceptance
are separate outcomes; additional phases also mean different aggregate call/time
opportunities. Delivery, comparison language and probe counts alone are not efficacy.

Tests: `tests/test_independent_candidate.py` and the alternative cases in
`tests/test_candidate_review_repair.py` cover fail-before-model validation and both
context policies through read/edit/check/submit/isolated mock evaluation.
