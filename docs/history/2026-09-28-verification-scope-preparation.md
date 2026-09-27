# Verification-scope cue: preparation only

2026-09-28, official=false. Provider-free preparation; no new paid allocation.
This follows the [unhinted result](2026-09-28-post-edit-budget-results.md), where
the agent described downarrow-only regression PASS as evidence for new uparrow
behavior, then submitted the unchanged defective patch with ample resources left.

## Question and single intervention

Does one generic verification-scope cue lead the agent to inspect selected test
assertions and discover an unverified changed behavior, rather than stopping at PASS?
Use the same first-post-edit checkpoint and proposed fresh $3 allowance. Add only
the exact `verification_scope_cue` field to its first current-state input and matching
canonical context. The source module and packet bind the English text:

> Before treating a passing check as evidence that a changed behavior is correct,
> inspect what its selected assertions actually exercise. Distinguish preserved
> behavior from new or changed behavior. If a material part of the change is
> unverified, use a targeted public check or probe before deciding to submit;
> do not infer coverage from a passing summary alone.

There are no task names, mathematical hints, supplied failing cases, or private
evaluator feedback in this cue. Original completion guidance is unchanged. No
new action, required test, memory field or default policy is introduced. Later
turns use ordinary context construction without reinjecting the cue; native history
and agent-authored notes can still carry its influence.

The existing unhinted run is the sequential comparison reference, not a new control
or randomized/replicated experiment. This cue was selected after observing its
failure; a favorable result would be a development diagnostic, not held-out efficacy.

## Verified boundary and readiness

Source: `run_dev_33068b6e257f423a` in the original pilot store, prefix through 139.
The candidate, 32 remaining calls, 85 tools, three edits and approximately 1,212
active seconds remain fixed. Model: `gpt-5.4-2026-03-05`, xhigh, desired output 25,000.
Task: `tasks/dev-train/original-toqito-1538/public.yaml`; credential: repository `.env`.
Proposed execution: one continuation, new cap $3.00, zero SDK retries, no auto-resume.
The original unused allocations remain closed.

The actual old first-dispatch request was read from its immutable artifact and
compared with the new frozen input. Removing only the cue yields exact equality:

- Unhinted request: `sha256:230f5887d14ca79c6d3b6d54b84ac1e4e782e4261de41706a13ee38e4e1a8d56`.
- Cued request: `sha256:c4109ac4f0dd3979a298553a25d4b25351aa7a930070728422bb4edf9aabf883`.

Actual-task offline restoration rebuilt the baseline exactly and delivered the
frozen cued request to a finite synthetic stop. Paid calls/cost: zero; autonomous
discovery, provider acceptance and task correctness remain NOT_RUN.
Focused tests additionally exercise the collector with a synthetic provider,
verify one-field equality and later absence from current state, and reject arbitrary
cue text. Existing uncertainty/accounting and other continuation tests apply.
Mock `run_dev_d7215c9cfbde4eae` reached isolated EVALUATOR_PASS, safety NOT_RUN.
The focused regression group passed 39 tests in 71.46 seconds; Ruff passed.
Documentation size/link checks were rechecked after recording this preparation.
The full repository suite was not rerun for this opt-in diagnostic change.

## Evidence and decision rule

- Packet: `C:/pt/analyses/verification-scope-checkpoint-20260928-v1/packet.json`.
- Offline/pair receipt: `C:/pt/analyses/verification-scope-rehearsal-20260928-v1/receipt.json`.
- Live manifest location: `C:/pt/analyses/verification-scope-live-20260928-v1/manifest.json`.
- Proposed live root: `C:/pt/scopecuelive0928a`.

Before any generation, require the exact separately authorized manifest and cost cap.
Measure whether source assertions are inspected, new-behavior checks are actually
performed, the defect is discovered/corrected, and the patch passes evaluation.
More inspection/probe calls alone are not improvement. Report public correctness
evidence separately from isolated benchmark acceptance; a non-submission is NOT_RUN.
Do not use private evaluation details for the next solver attempt. No default
adoption or generalized effect is established by preparation or a single follow-up.
