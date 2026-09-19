# Case design before candidate disclosure

`diagnostics.counterexample_discovery prepare --case-design task-first-v1` adds an
opt-in information-order experiment to the fixed-candidate diagnostic. It composes
with the existing `--review-guidance` choices; omission preserves their requests.
It changes neither dev repair defaults nor the existing planning/probe policies.
`--case-design task-first-factors-v1` uses the same flow with an additional initial
case-selection instruction; see [factorized case selection](#factorized-case-selection).

## Motivation and claim boundary

The motivating closed observation checked actual setup and reported two serializer
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

## Closed live observation: 2026-09-19 KST

User continuation authorized one new original-task/P10/GPT-5.4 medium observation,
applicability-contrast-v1 plus task-first-v1, repeat=1 and a new $1.20 cap. Committed
runtime/diagnostic source is `8c84874b`; the core content hash is unchanged. Current-day
official pricing, prepared source/dependencies and existing Docker/image passed admission.
No prior cases or findings were injected. Executable plan hash:
`sha256:4c95f0860d22286bdaea7b2201308218fa5da129e5d19be98d35a8bc2ad34e1f`.

The live provider accepts the new case schema. Turn1 records four cases before seeing
the candidate: tool-only empty field, existing thinking/text, deferred tool-search
history, and a broad non-applicable boundary group. It names supplied-profile origin
and ordinary-provider preservation, but does not construct an ordinary field-mode
case independent of the supplied profile. Reuse/copy with a renamed field is omitted.
Thus candidate exposure is not necessary for this sample's missing concrete contrast;
the observation does not establish the causal effect of information order.

Turn2 performs one read and two searches. Turn3 executes a single program against current
workspace code. Setup checks match the package path, actual DeepSeek mode and field.
Five direct complete comparisons match: tool-only, thinking/text preservation, default
plain provider, disabled sending and empty response. Two deferred capabilities load in
one offline conversation; the final request has six assistant tool-call messages with
string-valued fields. The replay expected count/tool names are copied from actual data,
and only the field types are independently asserted. Exact synthetic empty values,
full payload/return preservation and a second Agent.run with saved history are unverified.

The selected preservation case adds ThinkingPart and disables the candidate's no-thinking
condition. Default plain/disabled cases also do not exercise same-trigger preservation.
The complete output, three setup rows and same-trigger warning reach turn4. The model
reports no counterexample, explicitly acknowledging same-trigger and renamed/reused-profile
gaps. Public review records **NO_REPRODUCTION, supported discoveries0/1**. This narrow
no-mismatch conclusion is supported; candidate correctness remains NOT_ASSESSED. There
is no setup mismatch to measure correction. Only one proposed excerpt matches literally;
the others and the final excerpt join clauses. Manual review uses the full public task.

All four request deliveries, frozen-plan identity, native continuation and fixed candidate
pass audit. Four model/count calls, six actions, first probe turn3; cost $0.1824,
cache-neutral $0.2256, max input20,465, active161.774s/wall266.227s. Proposal overhead
is one response/action and $0.025995 within the shared cap. No infrastructure/resource
stop; complete output and cleanup confirmed. All four added lines have launch-thread
events, not per-case semantic coverage. Invoice/count-endpoint billing is unverified.

One planned/started/reported sample and unused $1.0176 are closed. All 1,583 earlier
evidence entries are preserved. The sealed 160-test diagnostic validation and unchanged
core regression evidence are reused; only documentation checks are newly run. No retry,
resume, replacement, paid judge, extra candidate/baseline program or hidden evaluation.
Fewer calls and broader examples than the preceding sample are observations, not causal
improvement. Do not adopt into repair defaults on this evidence. Further diagnosis should
separate concrete input construction and independent expectation quality from planning
activity; another paid prompt variant is not implied.

Evidence: `C:\pt\analyses\counterexample-discovery-task-first-20260919-v1`.
Raw: `C:\pt\pl-discovery-case-live-0919a`.

## Factorized case selection

The later direct-links observation groups ordinary profiles, disabled mode and empty
field names into one initial boundary case before seeing the candidate. Both executed
probe annotations then declare that their preservation input disables the trigger.
This is a selection gap already present in the proposal; its cause is not established.
The read-only diagnosis is recorded in
`C:\pt\analyses\task-first-factors-20260919-v1\selection-diagnosis.json`.

The optional `task-first-factors-v1` mode asks the model to distinguish public scope
(which inputs or objects a requirement covers) from activation (when the behavior
occurs within that scope). Using the existing applicability/setup/expected fields,
it prioritizes concrete cases that vary one supported factor while holding the others
fixed: in scope with activation present, out of scope with the same activation, and
in scope with activation absent. Expectations must follow literal public clauses.
Unsupported or dependent combinations belong in limitations; the four-case bound,
empty proposals and later corrections remain available. No case or probe is mandatory.

Only a 1,209-character initial system prefix changes. It remains in the append-only
review history after disclosure. The review-request template, record_case_plan schema,
tools, phase transitions, public task, model settings and shared limits are unchanged.
There is no new response, metadata field, check gate, supplied case, source hint or
semantic verdict. The selected mode and module hash use the existing packet identity.
The CLI, freeze/reveal path, native continuation, interruptions and action recovery
are exercised for both task-first modes.

Provider-free verification preserves all32 legacy request/protocol combinations;
all16 new combinations differ only by that prefix. Focused59 PASS/88.58s includes
both context policies through mutation, public checks, submission and isolated mock
evaluation, with actual task/diff/check/setup delivery. Offline prepared-source
rehearsal and closed historical inspection pass. Related regression, Ruff and docs
pass: regression251/206.52s with durations, docs3 and Ruff, for313 distinct tests.
Core runtime is unchanged; its broader regression receipt is reused, not rerun.
All1,838 earlier evidence entries
and user edits are preserved. Provider/count/credential/Docker operations and new
candidate executions are zero, with model cost $0. Previous paid samples remain closed.
Whether this instruction improves model selection or discovery is NOT_ESTABLISHED;
no new live observation, hidden evaluation or repair-default change is included.
