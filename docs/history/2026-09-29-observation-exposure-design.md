# Observation exposure comparison preparation

Date: 2026-09-29. Provider-free design; no model/tool/Docker/evaluator execution.
Follows [observation linking](2026-09-29-verification-observation-linking.md).

## Problem and diagnostic

Retention/linking is implemented and locally tested; better agent interpretation or
repair is unproven. Freeze a single exposure axis: A hides the automatic observation
catalog, B shows it, while both retain the same linking schema, raw public outcomes,
tools, budgets, completion gates and system prompt. Future continuations must apply
the policy to all verification renderings, including working_notes_after_batch.

## Evidence and result

Inspected the existing 45-run cross-task inventory. Seventeen unsuccessful actions
across nine runs/four tasks have hash-verified next-input artifacts and matching
candidate/action diff hashes. Generated 34 public-context fixtures; A/B differ only
at working_notes.verification.observations. Projection uses only actions before the
next model-input cut. Native/encrypted reasoning and private evaluation are not copied.
These are context fixtures, not restored runnable checkpoints or provider requests.

Eleven failures across HF, pyfakefs and AnyIO are registered checks already required
by submission gates. They are secondary controls, not evidence for retaining optional
questions. All six optional probe failures come from one toqito run. Setup/syntax
failures must be separated from candidate runtime failures with unproven applicability.
The final SyntaxError cut has zero edits remaining and cannot measure repair success.
Operator-provided HF feedback is outside the new feature's registered-tool scope.

Frozen candidates: C01 HF, C05 pyfakefs and C08 AnyIO as gated controls; C15 toqito
as invalid-setup diagnostic; C16 toqito as applicability-pending optional repair;
C17 only for verification, excluded from repair. Repeated failures are not independent
tasks. No candidate is selected by private acceptance or treatment output.

## Decision and validation boundaries

NO_GO for a multi-task nonblocking-effect trial from this inventory. Require eligible
natural agent-run optional failures from at least two additional tasks before that
panel; this minimum diversity is not a generalization/statistical-power claim.
Do not substitute the already-gated controls or manufacture counterexamples.
The complete protocol fixes success/false-bug/irrelevant-PASS/extra-work measures,
public applicability review, single-axis invariants and future execution admission.
Correct linking alone is not a primary outcome; relevant executed verification and
repair matter. Keep environment, interpretation, behavior and acceptance separate.

Packet: C:/pt/analyses/observation-exposure-design-20260929-v1.
inventory.json contains immutable source/cut/artifact references, hashes, budgets,
tools and paired fixture hashes. protocol.md contains eligibility and judging rules;
prepare.py records the reproducible provider-free extraction. Preparation events use
an external append-only dev-run-v1 hash chain. Historical journals were read only.
Source/fixture hashes and pair equality passed for all 17 cases. Workspace restoration,
all-provider-request parity, environment readiness and live effect remain NOT_RUN.
All 45 original journal hashes remained unchanged. Five documentation layout/link
tests passed after shortening the current-status summary within its existing cap;
git diff --check passed. Runtime code is unchanged, so no full suite or mock rerun.
No paid allocation is opened. Next inspect a separately identified independent saved
inventory for natural optional failures, or explicitly choose a narrower diagnostic.
