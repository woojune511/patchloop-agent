# Scripted review-to-repair integration

## Result and scope

Connected the offline review inputs to the ordinary native repair loop in
diagnostics/review_context_rehearsal.py. This is finite scripted SDK execution,
not a model experiment or live collector. No credentials, provider network calls,
paid cost, Docker startup or new evaluator image were used.

All C/A/B fixture branches reached EVALUATOR_PASS through the ordinary isolated
local evaluator. A further B fixture performed a new accepted edit, a current-diff
registered check and successful submission. Nine real-source branches (three arms
each for OpenSandbox, isort and pyinfra) preserved the native trajectory and ended
at the scripted AGENT_STOPPED boundary. Those real-task acceptance/safety results
are NOT_RUN; do not confuse fixture evaluation with real-task correctness.

Conan remains excluded from native rehearsal because its source runtime differs.
The earlier exact-hash materialization mapping was not extended to ordinary resume.

## Implemented boundaries

The reviewer has a finite script and registered read/search dispatch. A structured
finish_review response produces bounded untrusted advice tied to the candidate.
Reviewer tools execute against a separate journal, so their source observations
do not silently authorize repair mutations. Probe requests stop explicitly as
unsupported in this local rehearsal; real admitted Docker probes still need wiring.

The repair context is restored from the original prefix in every arm. Before first
repair dispatch, native history before the current state must equal the original
request. A/B add the report to the newly bound first state/context artifact; C does
not. Later turns do not reinject the report as fresh evidence. It can remain in
native history as old advice, and grants no check credit. No check/finish gate changes.

Each branch receives sixteen new model calls and forty-eight registered actions,
less actual reviewer consumption; the report call counts as a model call, not a
registered workspace action. Both phases share the USD 2 simulated cap. Reviewer
cost is included on every repair-ledger restoration, separate from historical
usage. Two new accepted edits are enforced by the native gateway rather than the
earlier conservative attempt counter. Reviewer elapsed time reduces the new
900-second allowance; integer deadline conversion has subsecond rounding precision.

A file-locked panel journal claims each output once, rejects unfinished prior
episodes and stops later episodes after count/transport/usage uncertainty. It allows
at most twelve episodes with fixed USD 2 caps, bounding simulated panel admission
by USD 24. It is not a resumable live accounting implementation. An interrupted
episode remains blocked rather than silently restarting or skipping its costs.

## Validation

Twenty-three focused tests passed: twelve offline contract tests and eleven new
integration tests. Coverage includes C/A/B fixture evaluation; actual new edit/check/
submit; candidate-bound report delivery without continued reinjection; equal added
call/action limits with review deductions; reviewer and repair count/transport/usage
faults; and durable refusal after an unfinished episode. Ruff, documentation layout
and diff whitespace checks passed. Existing baseline runtime files are unchanged.

Initial test failures were in fixture requests: a read omitted evidence_goal, and
a later edit reused a historical action_id with different arguments. Both were
rejected by existing contracts. Corrected the scripted requests, preserving those
guards; final tests use distinct action IDs. Failed local test directories remain.

The complete repository suite and separate mock CLI smoke were not repeated for
this opt-in diagnostic change; focused integration already reaches local isolated
evaluation. No claim of cross-platform CI or live-model correctness is made.

## Evidence and remaining admission

Real-source rehearsal root: C:/pt/analyses/review-native-rehearsal-20261001-v1.
Each arm stores inherited prefix, copied artifacts, reviewer journal where relevant,
resource-allocation event and diagnostic receipt. panel/runs/run_dev_reviewpanel.jsonl
records nine starts and nine completions. Driver:
C:/pt/review_native_rehearsal_20261001.py. Tests use the separate external
C:/pt/tmp/reviewloop04 root; earlier failing roots remain untouched.

Before paid approval: resolve Conan compatibility without hiding a runtime change;
admit existing images/dependencies; wire actual reviewer probes and the live
provider/report contract; freeze evaluation/scoring artifacts and the twelve-row
manifest; validate the live collector's durable accounting without paid dispatch.
The proposed pilot remains NOT EXECUTABLE for live work and no paid run is queued.
