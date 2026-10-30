# Applied-change review on the next useful decision

## Problem and decision

The [latest normal SQLFluff run](2026-10-30-retained-source-sqlfluff-results.md)
received relevant current source and public option tests, but its new test checked
input preservation in only the chosen permissive configuration. The
[public before/after comparison](2026-10-30-retained-source-public-counterexamples.md)
then found two changes from required rejection to success. This is a correctness
problem: preserving data did not justify changing success eligibility. It is not
evidence that source was still missing or that the private failing assertion is known.

The working hypothesis is that the next-decision review should make the applied
semantic change its subject before accepting the mutation hypothesis or new test
expectations as the requirement. Competing explanations remain: the model may
misunderstand the contract or fail to construct a useful counterexample even with
that focus. Earlier diagnostic identification of risk did not demonstrate execution
of a refuting case. Another generic warning, mandatory probe quota or reviewer
call would add cost without resolving this uncertainty.

The user requested implementation and local testing. This change uses the existing
review turn rather than introducing another stage or paid comparison.

## Implementation

- `working_plan.project()` adds an optional `review_request.behavior_change` from
  an admitted successful mutation that still matches the current diff. It contains
  the existing action/input identity, before/current diff hashes and host guidance.
  The instruction hash binds the existing planning contract. No authored semantic
  interpretation or new event/state store is introduced.
- The next useful decision connects public requirements, callers and pre-existing
  tests to changed success/failure meaning, a refuting input and an observable
  assertion. Mutation intent, plan conclusions and added test expectations remain
  claims to review. Original code is a comparison, not an automatic oracle.
- Existing reads, probes, tests, edits and receipt undo support the next action.
  An observed violation should lead to an executed regression, repair and fresh
  checks. No extra model call, mandatory probe, tool or semantic finish gate exists.
- Existing plan text, unresolved purposes and evidence remain intact. Failed,
  no-op, stale and replay-only mutations do not create this focus. A successful
  undo is a mutation. Existing valid-decision receipts consume it, including null
  or rejected plan annotations; turn start, protocol correction and segment
  rollover alone do not. Historical receipt copies are not new review requests.
- Guidance lives only in this optional projection. The shared system instructions
  and planning-OFF/thin presentation remain unchanged; redundant mutation wording
  in brief planning is replaced with the pointer. Compact completion retains the
  projected request through its existing working-plan field.

This is task-independent guidance. No operator SQLFluff counterexample, private
evaluator, hidden test, reference patch or raw reasoning is used in agent context.

## Local evidence

Runtime is frozen for validation at
`sha256:47057ca997eaa2ba5c3c566aa76df16ae9c4e2bdb41b47f08d68da05b0ff2fd9`.
Evidence root:
`C:/pt/postedit-review-20261030-v1`, journal `run_dev_posteditvalidation`.
Commands and results are recorded in append-only `dev-run-v1` JSONL; outputs are
content-addressed artifacts outside the repository.

An initial owner run exposed a stale test fixture: it attempted to write a plan
annotation on mutation tools, which no longer carry `turn_decision`. That failed
inside the mock before mutation. The fixture now injects invalid annotations only
where supported and expects the mutation's existing `not_requested` receipt.
Runtime behavior was not loosened to make the fixture pass.

The owner selection passed 61 cases in 78.117 seconds; its two failures were
expected current planning-contract fingerprints after this identity change.
Current fingerprints were updated; historical frozen-arm values were untouched.
The focused selection then passed all three identity cases and 15 of the new
behavior cases. Eight request-delivery cases initially expected internal concern
fields verbatim rather than the existing model-facing unverified projection.
Correcting those expectations passed all eight in 3.408 seconds. This verifies
preserved concern IDs/questions and `behavior_coverage=not_assessed`, not an
implementation change to concern semantics.

All 23 new cases therefore have passing evidence: both mutation tools, append and
segmented contexts, compact completion, failure/currentness/identity boundaries,
valid-decision consumption, historical receipt copies and reconstructed recovery.
The three actual mock paths (current/brief, current/none and thin/none) each retain
4 model responses, 5 tool actions, zero paid cost and isolated acceptance PASS.
Mock safety remains NOT_RUN. These are scripted delivery tests, not autonomous
counterexample discovery. The focused 26-case selection took 19.408 seconds,
followed only by the eight failed expectations above; neither exceeded two minutes.

Logs: initial owner `sha256:81028404accffea1d628791bea7f0ddd6c2161e062e6914a5fa4cf6b00e94cfb`;
focused `sha256:a0c52704fddf87a871c07cd2f00e6528bc7706d30234f746f2d111e7f782ea59`;
delivery correction `sha256:06955fb47f16312e5d13266c774a2aa4648c46e423cbe6564a92e25b68e39131`.
The delivery correction has its separate journal/artifacts under
`C:/pt/postedit-review-delivery-20261030-v1`, summary
`sha256:a446322795edc7db926d0a49d3380ee274c7b3f04a9df565e36f8437f0e77b5b`.
The shared system prompt stays byte-identical at 7,979 characters; only an active
mutation review receives the attached instructions. Repository Ruff passes.
Quick regression passes 1,285 cases with one host-symlink skip in 377.916 seconds
(pytest reports 376.16 seconds), four workers and unchanged runtime. It includes
the existing isolated mock smoke; no separate smoke was repeated. Log:
`sha256:932117145ccbc0415942af530b19e6a7710da17bc53b0e6699bbaaf03dfcb411`.
The new quick selectors add the 20 projection/consumption cases; the three mock
comparisons remain changed-owner tests. Current-document tests pass; final checks
verify local HTML links, unique IDs, unchanged scripts and historical record bytes.
Final checks artifact:
`sha256:f2eee2d236b2c853b25de0fa8c6a418c3c12a26a56e3aab86083eb1f20cf33bf`.
All 80 HTML links and 51 unique IDs pass; current status is 11,871 bytes.

## Interpretation and remaining question

Local tests can establish delivery, identity, consumption, preserved authority and
the scripted mock repair path. They cannot show that a model notices a violated
contract, selects a refuting input or repairs more tasks. This turn authorizes no
paid run; all earlier allocations remain closed. Full-suite/Linux validation and
live repair improvement remain unverified.

The next development run should inspect whether a newly changed success condition
becomes an actually executed discriminating case and, if it fails, a repair with
regression evidence. Judge task correctness and regressions alongside cost and
time, not mentions of concerns or the presence of this review field. If the model
already reasons from the changed contract but still constructs inadequate tests,
that would weaken the review-focus explanation and redirect the next investigation.
