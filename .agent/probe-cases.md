# Reusable public probe cases: experimental cases-v1

## Purpose and boundary

The plan-format diagnosis found delivered reference observations that were not
checked against the edited implementation. This option connects a concrete public
observation to a reusable model-authored candidate program. It does not certify
that either program implements the task's intended behavior. Do not inject the
diagnostic pyfakefs cases or private evaluation details into a fresh agent run.

`--enable-probes --probe-policy cases-v1` opts in. Default `probe_policy=none`
preserves the existing system prompt, tools, schema order and tool-surface hash.
The new policy changes only run_probe's input extension and its saved case view;
no new tool, planner call, tool mask, required test, scope allowance or budget.
All context policies support the view. Plans and notes remain independent.

## Three uses of the same run_probe action

With cases-v1, `question`, `python_source`, `reference_action_id`, and `case_id`
are required nullable fields. All calls still carry the normal turn_decision.
This follows the [OpenAI strict function-calling contract](https://developers.openai.com/api/docs/guides/function-calling#strict-mode):
required keys with nullable values, no extra object properties. OFF retains the
old two non-null source/question fields without the extra case fields.

1. Ordinary/reference observation: provide question and Python source; both IDs
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
the existing v39 tool-surface hash, including any planning policy. Model hash,
envelope, manifest and evaluator tool identity bind the option. Resume must repeat
it; old runs are not migrated. Probe image/profile identity does not change because
the sandbox execution surface is unchanged.

## Required validation / remaining hypothesis

Test OFF byte/hash parity; valid/malformed/oversized reference observations; current
versus historical comparisons; exact source rerun; bounded eviction; bad references;
source/definition/workspace drift; interrupted admission/result/batch boundaries;
native continuation/call/result identity; window/segment replacement; no gate/budget
changes; and mock submission through isolated evaluation. No real network/Docker
operation is required for these tests.

The feature makes a selected experiment reusable and its observation comparison
explicit. It does not prove that a small model will select useful references,
write a real candidate experiment, interpret a mismatch, or repair the defect.
Keep it opt-in until a separately frozen behavioral comparison supports adoption.
