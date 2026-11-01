# Task8 after completion-reserve clarification

Date: 2026-11-01. One authorized fresh development solve. CLOSED; official=false,
claim-ineligible. No retry, resume, extra evaluation or operator repair hint.

## Question and frozen scope

The [prior task8 run](2026-11-01-failed8-rerun-results.md) submitted while citing a
one-call completion stage, although its final input had 32 calls left and offered
probes and edits. The [display correction](2026-11-01-completion-reserve-clarity.md)
groups completion requirements under `completion_reserve`, separate from remaining
resources. The user selected only that problem for a fresh attempt and explicitly
approved a new USD4 cap. Prior allocations were not reused.

Question: does the agent distinguish these quantities and continue useful public
verification when warranted, and does its eventual repair pass independent evaluation?
The pre-run manifest recorded the baseline, intervention, selection, limits, criteria,
alternatives and stop conditions before provider dispatch.

- Code: `a1833855e075e8a280c9473af55fa5839895404b`.
- Runtime: `sha256:c455b38f9be2d1845b7cae4609536190a665b4ab5c8d0e0f6156b9b72b52773c`.
- Exact task: `tasks/dev-train/current-dev20/8/public.yaml`, pydicom1413.
- Model: `gpt-5.4-2026-03-05`, xhigh, 25,000 output tokens.
- Credential file: `C:/Users/geonj/Documents/PatchLoop/.env`; no credential values
  enter artifacts, task workspaces or container environments.
- One attempt, one worker, USD4 total; 40 model calls, 100 actions, 12 accepted
  edits, 1,800 seconds including 330 seconds reserved for evaluation.
- Same policies and prepared source/dependency descriptors as the previous task8.
  Request fields differ only in fresh `state_root`; the previous batch had two workers.
- Fresh public task only: no previous patch, response, helper, notes, counterexample
  or private expectation. Zero SDK retries; uncertainty stops further admissions.

Current local tests, runtime and source hashes were verified before dispatch.
Existing Docker images, prepared dependencies, import/operation canaries and a
selected public test passed. No Docker startup, image pull or build was performed.
Cost accounting uses the previously selected model's verified
[standard pricing](https://developers.openai.com/api/docs/pricing).

## Result

| Measure | Previous task8 | This task8 |
| --- | --- | --- |
| Independent acceptance | FAIL | FAIL |
| Safety | PASS | PASS |
| Model calls | 9 | 16 |
| Tool actions | 14 | 23 |
| Accepted edits | 1 | 2 |
| Probe executions | 1 | 3 |
| Recorded generation cost | USD0.556946 | USD1.797247 |
| Row elapsed time | 288.593s | 786.524s |

Current run: `run_dev_abbcd884047f44be`, terminal `EVALUATOR_FAIL`.
All 16 generations and 16 input counts are matched and settled. The USD4 allocation
and unused USD2.202753 are CLOSED. Model dispatch occupied 671.501 seconds; the
additional actions did not produce an acceptance or efficiency gain.
Invoice and input-count endpoint billing were not independently verified.

## Actual public decisions

Every dispatched input contains the new grouped reserve and omits the four flat
completion-forecast fields. A reconstruction verifies each exact delivered public
state against the frozen projection and canonical authority.

The baseline already performed one probe with reserve one, at call8. The important
difference is what followed that evidence, not the mere existence of another probe.
Baseline call9 submitted with 32 calls remaining and invoked the one-call-stage limit.

| Current call | Calls remaining | Completion minimum | Selected action |
| --- | --- | --- | --- |
| 11 | 30 | 1 | Probe OL array input, OL bytes and OB array controls |
| 12 | 29 | 1 | Read two source/test ranges |
| 13 | 28 | 1 | Add an OL writer regression method |
| 14 | 27 | 2 | Run the required public check on the new diff |
| 15 | 26 | 1 | Replay the helper on the final diff |
| 16 | 25 | 1 | Submit with the original-case evidence gap stated |

The final basis says further helpers/tests are unlikely to change the repair
decision and cannot substitute for missing original-case evidence. It does not
invoke a one-call cap. This supports that the erroneous explanation did not recur
and work continued beyond the first successful helper. It does not reveal the
model's internal understanding or establish a causal effect from one attempt.

## Repair evidence and remaining gap

Before editing, call3's public approximation already stored OL bytes as bytes and
wrote successfully, as did its OB control (action sequence54). The reported sample
converts an H-array using `tostring()` before `add_new`; the full reporter setup
was not reproduced. The agent then selected a buffer-input hypothesis: normalize
OB/OD/OF/OL/OV/OW/UN values using `memoryview(val).tobytes()` before list detection.

The combined source/test edit was rejected for changing an existing test body or
decorator and rolled back (sequence131). The agent recovered with a production-only
edit (144), then added `test_write_OL_buffer_values_match_bytes` in the existing
writer test class (209), preserving prior tests.

The public check explicitly selects `test_dataelem.py` and `test_filewriter.py`:
212 PASS after the source edit (159), then 213 PASS after the added test (225).
The final helper replay (243) observes successful OL array, OL bytes and OB array
writing. The new test compares bytearray/array inputs to bytes under implicit and
explicit little-endian writers. This is current-candidate evidence for those cases,
not an observed original failure-to-success transition or coverage of all seven VRs.

Public stdout is truncated and `collection_status=not_reported`. Explicit file
selection and the 212-to-213 count increase support the added test's inclusion, but
there is no direct retained node-level collection record. Changed-line tracing is
UNKNOWN (`unsupported_python_options`), not evidence of unexecuted lines. The first
operator recorder incorrectly expected the new node name in stdout; its assertion
failed, was retained, and the follow-up records this narrower evidence. No test or
evaluation was rerun to fill that telemetry gap.

The final assessment acknowledges that the issue's bytes example is already
byte-valued under current source/tests and that exact original reproduction is
missing. `unverified_delivery` remains a separate evidence label. The private
assertions were not inspected, so this public mismatch is not attribution of the
exact independent FAIL.

## Decision and limits

Keep the resource display clarification. This run does not justify higher limits
or a mandatory-probe/finish gate. The unresolved question is why a passing base
bytes approximation leads to a repair centered on different buffer inputs, and
why further work to distinguish the original cause is judged unhelpful.

One selected, development-exposed task and one stochastic fresh attempt cannot
establish repair gain, repeatability, generalization or field causality. A different
trajectory and one-versus-two-worker execution also limit timing comparisons.
The result separates corrected stopping language, more verification, and unchanged
independent failure. No further paid run is scheduled or funded by unused money.

## Evidence

Preparation and operator records: `C:/pt/reserve-task8-20261101-v1/`.
Execution records: `C:/pt/reserve-task8-run-20261101-v1/`.

- `manifest.json`: `sha256:cef66ca6b3748880f2ffb31e4c8ad95efcaea6758b129f77643890dfb1213cee`.
- `closure.json`: `sha256:3d77a7b25eb75808d7a1e8402882807d2b541df402bfbafaf0e9506979aa0274`.
- `findings.json`: `sha256:86b22879c882d8a0cb1b6dc5f2599741e79f27d7b850b99b90a705d3749814e6`.
- Submitted patch: `sha256:52f7cc595dc7547f70b4d81a736812243cdb3fb329fc71afc25943c5101294da`.
- Final journal: `sha256:d6033aec267c5991de266ae101db3354af2f180ac0b1e558621a2ab96ab9e3e1`.

The append-only preparation journal binds approval, observers, settlement and
interpretation; public audit files retain exact request refs, actions and patches.
Post-run analysis executes no model, target or evaluator and exports no reasoning
payloads or private evaluator bodies. Documentation validation and the final commit
are bound separately in `result-validation.json` and `result-commit.json`.
