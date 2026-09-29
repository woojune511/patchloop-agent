# Observation versus completion: B1/B2 decision audit

Date: 2026-09-29. Provider-free analysis of the closed
[repair comparison](2026-09-29-observation-repair-panel-results.md).
No additional model calls, task executions, private evaluator inspection or runtime
changes. This follow-up leaves the closed experiment and its records unchanged.

## Observed divergence

Reconstructed all 17 dispatched B1/B2 inputs and their public decisions. Both
received identical B feedback fields. B1's first five inputs describe the initial
candidate; its nine later inputs correctly mark that observation historical.
All three B2 inputs retain it as current. There was no missing-feedback explanation.
Public decisions are action justifications, not access to private reasoning.

Both first plans proposed the same broad route: contract check, remaining regression
check if PASS, then submission. Their actions diverged on turn two after contract
PASS. B1 explicitly cited the ambient-client counterexample and searched constructor
and wrapper ownership; B2 proceeded to the regression check. B2's next plan treated
the contract PASS as support for the candidate and retained only the regression
question. Its verification concern list remained empty. A plan review was requested
after each check and on first submission eligibility, so absent review requests or
lost plan storage do not explain this episode. B1 broke its initial plan when it
reconciled the contrary observation; plan presence alone did not distinguish success.

## Budget and availability: hard constraint ruled out for B2

At B2's final input, before its third model dispatch:

- 38 model calls, 98 tool actions, three accepted edits and 846 seconds remained.
- USD 1.935501 remained from its USD 2 cap.
- read_file, search_files and run_probe were callable alongside finish_task/stop_task.
- exploration_state was open, with 37 model turns available for exploration.
- minimum_completion_calls and completion_budget_calls were both one.

The last number describes the remaining submission path, not one remaining total
call. Its public decision nevertheless referred to the final completion call.
That is compatible with a misleading interpretation of the horizon, but does not
prove it caused submission. There was no hard forced-finish condition.

Both B runs initially had mutation_completion_horizon.minimum_possible=false and
no replace_text tool because fresh episodes had no current editable-source anchors.
They also had mutation_readiness=needs_anchor_evidence and callable reads/searches.
The source predicate requires current anchor evidence; B1 acquired it and edited.
This flag does not establish that budget prohibited B2 from eventually repairing.
The existing system prompt already explains this distinction.

## Evidence representation and check scope

The external counterexample lives in operator_public_feedback, with receipt/diff
identity and clear limits on interpreting model-authored expectations. It does not
populate the gateway's active failed registered check. In B2, current_public_failure
was therefore null throughout. This is a scope distinction, not evidence that the
whole candidate had no public counterexample.

The gateway's ready_to_submit predicate tests a nonempty tracked diff and all
required visible checks passing. Its completion guidance therefore recommended
checks and then finish_task even while external contrary evidence remained. It
explicitly said eligibility was not proof of untested behavior and offered a probe
for concrete uncertainty. There was no blanket instruction to ignore counterexamples.
The mechanism does, however, give required-check completion a computed next action,
while noticing and retaining the external contradiction depends on model judgment.
The model-authored verification list was never populated in either B episode;
it cannot preserve a concern that the model never records.

Check coverage was marked not_assessed in the actual inputs. Inspection of the
public check program confirms environmental cases use endpoint=REQUEST for client
construction; direct-no-endpoint is a standalone helper call. The supplied probe
instead exercises HfApi(token=False) under an ambient HF_ENDPOINT. Thus PASS and
that counterexample can coexist without contradiction in test execution. Neither
B episode read an additional check definition through tools; the definition was
already present in public_task. No hidden checks were read for this audit.

Relevant source:

- diagnostics/candidate_review_repair.py: feedback_overlay and state overlay.
- patchloop/dev/tools.py: current_public_failure and ready_to_submit.
- patchloop/dev/runner.py: _completion_budget, mutation_allowed predicate,
  _completion_guidance and public state projection.
- patchloop/dev/model.py: DEV_SYSTEM_PROMPT already limits coverage claims and
  distinguishes current mutation eligibility from availability after a read.

## Interpretation and smallest next diagnostic

The supported failure is failure to carry delivered contrary evidence into the
next action and submission assessment. Delivery, hard budget exhaustion, tool
closure and absent plan-review requests are excluded for B2. The first observable
loss occurs after the initial contract PASS, before final submit guidance.

Competing explanations remain: model variation/salience, overgeneralized check
coverage, preference for the suggested completion path, and treatment of external
observations as lower-authority advice. The artifact distinguishes these signals
but cannot assign causal weights. B1 succeeded with the same representation;
no deterministic harness failure or reliable treatment effect follows.

A minimal next comparison would hold the fixed post-contract-PASS B2 input and all
evidence/budgets/tools constant and remove only completion_guidance.next_action
and its imperative action recommendation, retaining eligibility, limits and the
coverage disclaimer. Measure acknowledgment of the existing contrary evidence and
an appropriate next inspection/probe, not mere plan length or additional tool use.
This isolates steering toward the completion path; it does not establish successful
repair. A separate horizon-label change would require a separate comparison. Do
not simultaneously add a concern gate or task-specific repair hint. No paid
comparison is authorized or run by this analysis.

If later testing favors persistent discrepancy tracking, reuse existing concerns
with provenance and explicit support/dismissal reasons; do not automatically turn
every failed model-authored assertion into a trusted bug or hard submission block.
The unresolved B1 benchmark failure is a separate correctness question.

## Evidence and validation

Immutable comparison: C:/pt/analyses/observation-decision-audit-20260929-v1/comparison.json.
Its dev-run-v1 journal binds the artifact hash. Contains 17 exact-input hashes,
feedback hashes/currency, budgets, offered tools, completion guidance, plans,
notes, check metadata and public decisions; no plaintext private reasoning.
Source experiment: C:/pt/analyses/observation-repair-panel-20260929-v1.
All B feedback fields were asserted equal to its frozen packet. No prior artifacts
were rewritten. Documentation-layout tests and diff checks validate this docs-only
follow-up; no new production implementation or performance claim is made.
