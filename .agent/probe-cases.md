# Public probe replay and experimental cases-v1

## Ordinary action-ID replay

Whenever probes are enabled, `run_probe` exposes nullable `replay_action_id` under
`none`, `cases-v1`, and `reference-cases-v1`. Ordinary executions provide question
and Python source with `replay_action_id=null`. To execute an earlier completed
same-run probe again, use its action ID with question/source null. Leave case and
reference IDs null and `save_program=false` where those fields are offered.
The separate counterexample-discovery and paired initial-observation diagnostics
retain inline-only probe schemas because their annotations bind supplied programs.

The new action executes the exact recorded question and program on the current
diff. No earlier save or saved-case registration is required; the action neither
activates a case nor performs reference comparison. A completed assertion/import
failure is eligible, including non-JSON output. A recorded timeout or output limit
also permits explicit reuse after confirmed cleanup; new admission still applies
the current resource limits. Pending or outer-failed actions and unconfirmed cleanup
are ineligible. Prior action/input/diff/program identities must match the receipt.

Admission stores the resolved program and original action/input/diff/source hashes
in `action_started.probe_replay_request`; the new result retains `replayed_from`
provenance and its own execution identities. Pending recovery rejects changed
bindings or an admitted workspace diff that has drifted. Reusing the same
`action_id + input_hash` still returns its completed receipt without execution.
Explicit replay uses normal probe admission and resources; it triggers no automatic
execution, grants no required-check credit, and changes no submission gate.

This removes the prior-save prerequisite for a program already in the public action
journal. It does not select a useful reproducer or establish correct expectations.
Local validation includes unchanged-source failure-to-pass replay, interruption and
identity checks, case compatibility, and a segmented mock solve through isolated
evaluation. Evidence is under `C:/pt/parvalidation01`; repair-success benefit is unmeasured.

## Purpose and boundary

The plan-format diagnosis found delivered reference observations that were not
checked against the edited implementation. This option connects a concrete public
observation to a reusable model-authored candidate program. It does not certify
that either program implements the task's intended behavior. Do not inject the
diagnostic pyfakefs cases or private evaluation details into a fresh agent run.

`--enable-probes --probe-policy cases-v1` opts into saved cases. Default
`probe_policy=none` exposes ordinary probes and action-ID replay, without saved-case
fields or a catalog. The case policy extends run_probe's input and saved case view;
no new tool, planner call, tool mask, required test, scope allowance or budget.
All context policies support the view. Plans and notes remain independent.

For the [incremental capability comparison](probe-replay-comparison.md),
`--probe-policy reference-cases-v1` selects control A in the same runtime.
It retains ordinary probes and reference-based registration/comparison/replay,
but omits `save_program` from its schema. Supplying that field (even false), or
replaying a reference-free definition by case ID, fails before dispatch.
`cases-v1` remains B with its existing contract. The effective policy/contract
binds model/tool hashes, envelope, manifest and exact resume identity. This
experimental control does not change the selected baseline or enable probes itself.

## Four uses of the same run_probe action

With cases-v1, `question`, `python_source`, `replay_action_id`, `reference_action_id`,
and `case_id` are required nullable fields. Keep `replay_action_id=null` for the four
uses below. `save_program` is a required boolean, false except
for reference-free registration. All calls still carry the normal turn_decision.
This follows the [OpenAI strict function-calling contract](https://developers.openai.com/api/docs/guides/function-calling#strict-mode):
required keys with nullable values, no extra object properties. Case policy `none`
has nullable question/source/replay fields without the extra case fields.

1. Ordinary/reference observation: provide question and Python source; save_program=false, both IDs
   are null. Ad-hoc probes keep their old behavior. A potential reference should
   print exactly one JSON value, including at most 2,048 UTF-8 bytes of stdout.
2. New candidate case: provide question and new Python source, reference_action_id
   of an already completed public probe, and case_id=null. The candidate program
   must explicitly call current public project code and print the same observation
   shape. The host uses the reference's actual recorded JSON, not an expected value
   invented by a summary or supplied through a new assertion field.
3. Rerun: provide a retained case_id; question/source/reference_action_id are null.
   Execute the exact saved candidate source on this diff. Do not rerun the reference
   or manufacture native call/output history. The explicit action has its own
   action_id/input_hash and costs one model call and one tool action as before.
4. Reference-free program: set save_program=true, provide question and Python source,
   and leave both IDs null. A completed execution saves the program even when an
   assertion/exception fails or stdout is not JSON. Rerun using case_id and
   save_program=false; the source is unchanged. Do not combine registration with
   a reference or an existing case ID. This mode has no reference equality check.

Reference eligibility requires successful action completion, healthy exit zero,
complete/nontruncated JSON output, and consistent action/input/diff/source identity.
Unknown, pending, failed, private or registered-check references are not admitted.
Malformed JSON, duplicate object keys, nonfinite numbers, surrogate encoding errors
and oversized observations cannot become expectations. Compare canonical JSON:
object order/whitespace are irrelevant; arrays, values and number/bool types are not.
The 2,048-byte threshold is an experiment bound, not an API limit.

Candidate source retains the existing 8,000-character/32,000-byte bounds and clean
Docker snapshot, timeout, output, deadline and owned-container cleanup contract.
A candidate's failed process, malformed JSON or large output produces not_compared,
not a task FAIL. Preserve the original output and keep the program for later reuse.
A bad reference or replay request is a tool contract error before sandbox execution;
it neither changes the workspace nor removes the ordinary probe capability.

## Result, memory and interpretation

`case_comparison.status` is matched, mismatched, or not_compared. It binds case and
definition hashes, candidate source hash, original reference action, expected JSON
and observed JSON/reason. A match means equality to the model-selected observation.
It does not establish a correct reference, execution of intended code, coverage of
the whole goal, or task acceptance. Normal probe observation remains
`behavior_verdict=not_assessed`. Source-line entry is not a semantic attestation.

Reference-free cases keep reference=null and not_compared/reason=no_reference.
Their last result includes the program hash and execution status, exit code,
timeout/cleanup/output flags and available environment/snapshot/policy hashes;
the existing action result binds the candidate diff and retains bounded output.
Neither nonzero exit nor exit zero is a task verdict. Timeout or uncertain cleanup
does not trigger retry; normal runner stop/recovery rules still apply. Source
changes create a new identity. Both modes share the existing three-case bound.

`probe_cases.items` retains the three most recently executed cases; IDs are stable
content-derived references, never reassigned. Rerunning refreshes a case's position;
a fourth distinct execution drops the least recent from active memory, not the
journal. Unknown/expired IDs are not substituted. Change a program by registering
a new case, not silently rewriting its saved source.

Context contains question, bound reference observation and last candidate result.
It excludes candidate source bodies: the explicit case-ID tool operation reuses
them without requiring the model to read an external archive. Expected values are
not duplicated within the catalog; matched observations reference that value.
Program relevance is `model_authored_unverified`. Result currency comes from the
executed/current diff hashes; a mutation leaves a historical result, not a current
PASS. Current catalog state replaces old views across window/segment boundaries.
No old case is resurrected from historical context. No model memory annotation is
needed for storage and no plan/concern is auto-resolved by a comparison.

Mismatch or untested historical cases never withhold finish, grant visible-check
credit, consume accepted mutation capacity, grant anchor evidence, or trigger
automatic reruns. Existing budget policy decides when run_probe is available.

## Durability and exact recovery

Resolve reference/case identity before execution and bind the resolved question,
source and definition in action_started.probe_case_request. Resume checks this
same binding and the admitted workspace diff before the existing sandbox action.
Bind definition and result atomically in action_finished.probe_case. Rebuild the
bounded catalog from completed action events; no separate mutable allocator or
annotation event can be half committed. Conflicting identity is a recovery error.

Completed `action_id + input_hash` replays its result without execution. A probe
interrupted before a durable receipt retains the existing exact-container cleanup
then isolated rerun contract; it is not an exactly-once process guarantee. Provider,
mutation and completed probe calls are not duplicated after a durable decision/result.
Uncertain cleanup, provider usage, deadline or state is never bypassed by case reuse.

Policy/limits/description/retention semantics have their own identity composed over
the current base tool-surface hash, including any planning policy. Model hash,
envelope, manifest and evaluator tool identity bind the option. Resume must repeat
it; old runs are not migrated. Probe image/profile identity does not change because
the sandbox execution surface is unchanged.

## Required validation / remaining hypothesis

Test ordinary action-ID replay across all policies; completed failure eligibility;
invalid identities and pending recovery drift; valid/malformed/oversized reference
observations; current versus historical comparisons; exact source rerun; bounded
eviction; bad references;
source/definition/workspace drift; interrupted admission/result/batch boundaries;
native continuation/call/result identity; window/segment replacement; no gate/budget
changes; and mock submission through isolated evaluation. No real network/Docker
operation is required for these tests.

The feature makes a selected experiment reusable and its observation comparison
explicit. It does not prove that a small model will select useful references,
write a real candidate experiment, interpret a mismatch, or repair the defect.
Keep it opt-in until a separately frozen behavioral comparison supports adoption.

## First live comparison (2026-09-15)

Four fresh OFF/four ON pyfakefs-v2 trials at a1156982, with the same mini/medium,
segmented-v1 and brief-evidence-v1, achieved acceptance 1/4 each. All 161 requests
offered run_probe and all 90 ON inputs included this contract/catalog, but no run
invoked a probe. The new execution path therefore remains mock-verified, not
live-exercised by this group. Total cost $2.103549150; no retry or extra sample.
Do not treat tied small samples as proof of equivalence, or B1's success as evidence
of case reuse. Default remains OFF. Investigate verification selection before
adding storage features or requiring probes. Preserve the closed group's records:
`C:\pt\analyses\probe-cases-compare-20260915\result.md`.
