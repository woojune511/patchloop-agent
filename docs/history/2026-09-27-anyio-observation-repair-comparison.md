# AnyIO observation and repair comparison

Date: 2026-09-27. All results are `official=false`, `claim_eligible=false`.

## Problem and hypothesis

The prior planning ON run left an incorrect AnyIO candidate, a public
explicit-cancellation failure and a relevant probe question. The probe returned
an empty timeout; a later cost-limited response ended without submission.
[Provider-free reproduction](2026-09-27-anyio-failure-observation.md) showed that
the same program with corrected pytest dependencies observes the shared runner
task ending on cancellation and `ClosedResourceError` during fixture teardown.

The comparison asked whether supplying that completed observation improves repair
of the same saved candidate. A received the same historical question/program with
the timeout receipt; B received the completed observation. Both had corrected
dependencies available for new probes. No operator repair proposal was supplied.

## Execution

The separately approved $4.80 group ran exactly NA1 -> NB1 -> NB2 -> NA2, $1.20
per run, repeat=1. Task: `anyio-interrupt-runner-cleanup-v3`, dev-train. Model:
`gpt-5.4-2026-03-05`, xhigh, desired output 25,000. Existing `run_dev` and the
existing seeded-repair diagnostic retained segmented-v1, result-or-size-v1,
brief-v1, probes enabled / probe-policy none, repair-recheck, protected-v1 and
per-call-v1 admission. Each independent clone started from the identical saved
candidate with three remaining mutation slots and a fresh budget.

Previous plans, notes, registered-check state, acceptance and encrypted reasoning
were not imported. The common historical question mentioned the prior failure,
but its registered-check receipt was not imported. Execution HEAD was `5d74710`;
the runtime content hash stayed
`sha256:e3b533ac585ea2b48d159a6f8449d3996cd991b3da73fa268dbda71f8d5230c3`.

## Results

| Run | Acceptance / safety | Recorded USD | No-cache equivalent USD | Model calls | First edit call |
| --- | --- | ---: | ---: | ---: | ---: |
| NA1 | PASS / PASS | 0.4468195 | 0.4931875 | 5 | 3 |
| NB1 | PASS / PASS | 0.4656565 | 0.6275125 | 6 | 4 |
| NB2 | PASS / PASS | 0.5150110 | 0.7822750 | 8 | 6 |
| NA2 | PASS / PASS | 0.4607050 | 0.6810250 | 7 | 5 |

Primary metric: **A 2/2 planned, B 2/2 planned**. Each arm started and submitted
two runs. Acceptance FAIL, NOT_RUN, infrastructure stops and safety failures were
zero. The group used **$1.888192 / $4.80**; no-cache equivalence was **$2.584**.
No-cache equivalence reprices the recorded input without cache discounts; it is
not another bill. No retry, replacement, resume or additional sample occurred.

All 26 responses completed with the full 25,000 output ceiling. Largest counted
input was 44,789 tokens. Every run had three segments: initial, then twice
major_result_reviewed. No resource stop contributed to the outcomes. There is
no basis for a general cost or quality claim from two selected attempts per arm.

## Public behavior

All four began with the same fresh public lifecycle check: 6/7 passed, with
explicit cancellation producing fixture teardown failure and task/context mismatch.
The next call read the owning TestRunner source. Each then made one new edit to
the CancelledError handler so a cancelled call could report its result without
ending the shared task needed for later fixture teardown.

NA1 used that owning read alone. NB1 additionally searched other runner methods
and interrupt handling, and also added a separate run_test CancelledError branch.
NB2 read pytest-plugin runner lease management before editing. NA2 read plugin
and trio caller behavior and also changed the call future to store the exception.
These are distinct edits; passing checks do not isolate every added line's effect.

Configured repair-recheck automatically ran the lifecycle check after each edit:
7/7 passed. Each then selected the upstream regression check: 32 passed, three
deselected. All submitted their verified current diff. No run requested a new
probe or had a rejected/repeated rejected edit. A's fresh failed check and source
were sufficient in both attempts without receiving the completed probe result.
NB1's public rationale explicitly cited the supplied diagnostic; delivery alone
does not establish equivalent uptake in NB2.

## Interpretation and next question

Supplying the completed observation showed no acceptance advantage here. This
does not establish that observations are generally unnecessary, that the policies
are equivalent, or that case selection improved. Completion guidance and automatic
recheck remained fixed; both arms received the historical probe question/program.

These are fresh seeded repairs, not full solves or native continuations. The prior
ON result remains NOT_RUN, and earlier results/costs are not pooled. Resetting the
candidate context and budget means this result cannot identify probe timeout,
planning, model ability or budget alone as the original cause. Neither this group
nor the prior replay establishes that unmodified base source passed explicit_cancel.
Cause analysis used public traces only, not private evaluator explanations.

Keep the corrected AnyIO dependencies; no new default prompt, planning rule or
runtime change follows. The unresolved question is whether a fresh full solve
with that environment can reach repair and submission within its original cap.
That question is NOT_RUN here. This group and its unused funds are closed.

## Validation and evidence

The collector verified 26 actual inputs and selected count requests, equal initial
controls/tools after the declared observation differences, exact observation
delivery and recorded continuations. After each edit the original observation was
marked historical while task/diff/check state reflected the current candidate.
Five journal chains, 92 frozen files, 90 earlier protected files, source/dependency
identities and accounting verified. Execution/probe container inventories were empty.
No Docker startup or image pull/build occurred.

Preparation's mock/control validation remains in its prior record; no product
runtime code changed here. The live runs reached mutation, public checks,
submission and isolated evaluation. Product-wide regression was not rerun for
this execution and documentation-only follow-up.
Documentation checks passed all five tests; Ruff passed for product, diagnostics,
tests and the two new analysis scripts. The first documentation check exceeded the
history index's byte limit; shortening only the new index entry resolved it.

- Frozen preparation, authorization and public timelines:
  `C:\pt\analyses\anyio-observation-repair-20260927-v1`.
- Paid journal, per-run audits and group `result.json`: `C:\pt\obsrepair0927a`.
- Report, metrics, public decision cards and `closure-verified.json`:
  `C:\pt\analyses\anyio-observation-repair-results-20260927-v1`.

The frozen preparation status remains a historical snapshot. Later authorization
and execution are separate records. An offline closure-report serialization error
left a retained empty file; correcting the descriptor-hash field and repeating
read-only verification produced `closure-verified.json`, without rerunning any model,
task or evaluator. The paid group's completion and billing records were unaffected.
