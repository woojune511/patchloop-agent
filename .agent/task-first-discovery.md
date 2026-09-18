# Case design before candidate disclosure

`diagnostics.counterexample_discovery prepare --case-design task-first-v1` adds an
opt-in information-order experiment to the fixed-candidate diagnostic. It composes
with the existing `--review-guidance` choices; omission preserves their requests.
It changes neither dev repair defaults nor the existing planning/probe policies.

## Motivation and claim boundary

The latest closed observation checked actual setup and reported two serializer
matches, but chose a preservation input that disabled the candidate condition.
Generic guidance and the same-trigger warning were delivered. The model's report
treated the implementation condition as the complete public applicability boundary.
Candidate anchoring is one hypothesis, not an established explanation of that trace.

This diagnostic tests a different information order: propose cases from the full
public requirement first, then inspect the candidate. It does not supply a known
counterexample, operator-selected case, expected answer or semantic judge. Public
check examples remain part of the task. Model prior knowledge, those examples, the
extra response and different context can still affect selection. No efficacy claim
follows from implementing the flow or from its scripted mock.

## Two stages, one invocation

1. The first request contains the original complete public task and review limits.
   It contains no candidate patch/hash, prepared paths, dependency environment or
   prior-run material. Only `record_case_plan` is available; source reads/searches,
   probes, reports and mutations cannot run in this stage. The prepared workspace
   already contains the fixed candidate, but no source tool exposes it to the model.
2. One valid case proposal is stored in CAS and a hash-chained
   `discovery_case_plan_frozen` event before candidate-containing input is built.
   The native function result then reveals the fixed patch and public probe
   environment. The next request offers exactly the existing read/search/probe/report
   schemas for the selected review guidance. The initial system/task input and the
   model's native proposal remain in append-only history with opaque continuation.

The proposal holds zero to four cases: bounded `case_id`, `purpose` (change,
preserve or boundary), literal `requirement_excerpt`, `applicability`, concrete
`setup`, and observable `expected`; `limitations` carries unknowns. Empty cases are
allowed. Public snippets are requested, not private reasoning. Strict shape/bounds
are validated, but excerpt mismatch and duplicate IDs are advisory. A matching
excerpt proves only textual presence; all cases remain `model_authored_unverified`,
with `coverage_status=not_assessed`.

The model may revise a mistaken proposal during later source inspection/probing,
using the existing question and report fields to explain changes. It cannot overwrite
the original proposal or invoke the recording tool again. No case is mandatory to
execute, and no positive discovery claim or probe is required to finish. An empty
proposal followed by a blocked/no-discovery report is a valid limited result.

## Cost, identity and interruption

The proposal consumes one model response and one tool action within the original
40-call/100-action/1,800-second/$1.20 invocation limits. Count-before-dispatch,
full 25,000-output reservation, 60,000-input bound and zero retries are unchanged.
Neither ledger, counters nor deadline restart at disclosure. Current-day pricing,
exact task/model/credential/repeat/cap and clean source admission still apply to live work.

The design binds both `request.json` and the later `review-request.json` template,
the case-design selection and its implementation hash. An interrupted design has
no published packet. The executable packet binds this selection and current
diagnostic implementation. It never resumes a consumed output directory.

The recorded proposal includes `action_id`, the raw tool/argument `input_hash`,
`plan_hash`, CAS reference, public-task identity and advisory excerpt diagnostics.
The standard inspector verifies the CAS reference and journal chain. An interruption
after freezing preserves that proposal but does not imply the candidate reached
another model call. Only the recorded next request/dispatch establishes delivery.
Read-only inspection never reveals additional input to the model or resumes work.
Older closed journal summaries retain their original shape when there is no proposal.

## Evidence and next measurement

Provider-free implementation evidence is in
`C:\pt\analyses\counterexample-task-first-20260919-v1`.
It includes an isolated scripted proposal/read/probe/report flow, stage-escape and
interruption checks, shared limits, old-mode input equality and the core mock solve
through public checking/submission/isolated evaluation. Real-task preparation is not
an executable paid packet; no credentials, provider/count call or real candidate
program are used by this implementation validation.

Focused: 36 PASS/42.77s, including both context policies' actual task/diff/check/setup
delivery and isolated evaluation. Diagnostic regression: 121 PASS/145.02s with durations;
the feature-focused set meets the two-minute target. Two formatting-adjusted test paths
also pass their targeted recheck. Ruff, documentation checks, prepared-source offline
rehearsal and old closed-journal inspection pass. Core runtime bytes are unchanged;
the prior resolved 2,884-test/16-skip full-regression evidence is reused, not rerun.
All 1,470 earlier evidence entries and unrelated user edits are preserved.

A separately bounded live observation can ask whether initial cases distinguish
public applicability before seeing the candidate, whether later construction matches
the proposal, what changes after disclosure, and whether any executed mismatch is
publicly justified. Count proposal overhead and untested cases as well as discoveries.
Keep the previous samples/budgets closed and review public traces only. Better case
selection, candidate correctness and causal improvement remain unassessed here.
