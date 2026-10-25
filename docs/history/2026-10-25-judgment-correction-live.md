# Judgment pilot: consistent original failure, ineffective repairs

Date: 2026-10-25. Status: completed; allocation closed. `official=false`,
`claim_eligible=false`. Material passport: academic-research-suite /
experiment-agent / run; verification ANALYZED from saved public evidence, not an
independent rerun; version `judgment-live-v1`.

## Question and frozen conditions

The [previous pilot](2026-10-25-completion-resources-live.md) captured F0010 but
classified it as absent by checking stderr alone. The model inherited that false
premise and never edited source. The [local follow-up](2026-10-25-judgment-correction.md)
added host diagnostic calculation, one baseline correction, judgment/note linkage
and completion-resource accounting. This pilot asked whether that intervention
established a usable original baseline and enabled repair under the unchanged cap.

The current user requested an experiment after implementation. One fresh invocation
used the current thread's previous task/model/credential/repeat/cap conditions;
the exact scope was restated and sealed before dispatch. Earlier allocations were
not reopened. This is a bundled intervention on one exposed dev-train task, compared
descriptively with one historical trajectory; no causal effect or generalization
is identified.

- Task: `tasks/dev-train/current-dev20/13/public.yaml`, Astroid-1333.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh; credential file
  `C:/Users/geonj/Documents/PatchLoop/.env`, contents not printed.
- Normal output ceiling 40,000; independent protocol correction ceiling 25,000.
  One repetition, USD1.20 invocation-wide cap, 40 model calls, 100 tool actions,
  four accepted mutations, 1,800 active seconds and 1,920-second supervision.
- Same run_probe recommendation, segmented-v1 / result-or-size-v1 / brief-v1,
  bounded-v1 acquisition, probes with policy none, repair-recheck, protected-v1,
  completion-recovery-v1, prepared source/dependencies and existing images.
- Runtime commit `94c7238800bdc886b5d82f11cbecc41e377aacd5`; runtime hash
  `sha256:d4c94133e80b3bd6bc8df8a0bcbd6aecb2d2f57f4d9bc62f5f8f3e3fcf290bc7`.
  Every request setting except the new state root matched the previous pilot.
- Existing frozen post-submission public checks retained a shared 120-second
  bound and were conditional on an eligible settled submission. Count, transport,
  billing, cleanup uncertainty or input drift stops work; no automatic repeat,
  resume, image acquisition or limit increase.

[Official pricing](https://developers.openai.com/api/docs/pricing) was checked
before dispatch: USD0.75 input, USD0.075 cached input and USD4.50 output per million
tokens. The [model snapshot and xhigh support](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
were also checked. The request, sources and verification are frozen outside the
repository in `C:/pt/judgment-live-ready-v1`.

Preregistered alternatives included null diagnostic rules, an already-consistent
first observation, an unsuccessful or incomparable correction, a wrong repair
hypothesis after acquisition, setup-failed cases preventing reuse, output/cost
limits and stochastic trajectory variation. No conflict would mean correction
NOT_TRIGGERED, not correction success. Repair required comparable candidate
success, required checks, submission, frozen public checks and isolated acceptance.

## Observed result

Run `run_dev_ba8ee369693d4c84` ended `LIMIT_REACHED`, blocked by
`accepted_mutations`, after 1,085.378 seconds (18m05s). It settled USD1.031992500,
leaving USD0.168007500 unused. Counting and billing are known. There were 23 model
calls, 24 input counts and 26 tool actions. No patch was submitted; independent
acceptance, safety and both post-submission public checks were NOT_RUN.

| Observation | Previous resource pilot | Judgment pilot |
| --- | --- | --- |
| Original failure acquired | No | Yes, first authored original probe |
| Diagnostic host calculation | Not available | Five consistent probe judgments |
| Captured/authored conflict | False authored value in historical audit | None observed |
| Baseline judgment correction | Not available | NOT_TRIGGERED |
| Accepted mutations | 0 | 4: three source changes and one test addition |
| Candidate original replays | 0 | 4, all comparable and still F0010 |
| Final submission / acceptance | NOT_RUN | NOT_RUN |
| Terminal | INCOMPLETE_RESPONSE | LIMIT_REACHED: accepted mutations |

Tool counts: eight searches, seven reads, five probes, four mutations, one registered
check and one selected test. These are resource measures, not repair-quality scores.

## Public evidence sequence

1. Calls 1-2 searched/read source. Call 3 selected two literal diagnostic rules for
   `F0010: error while code parsing`, bound to the failing directory invocation and
   a normal file invocation of `pylint.lint.Run`. The first call's complete stdout
   contained F0010 for absent `src/project/__init__.py`; the control lacked F0010.
   Authored and host JSON both were `{"bug_has_error":true,"control_has_error":false}`.
   The unchanged-base failure was acquired. Exact capture and judgment reached
   dispatched model input 4.
2. Mutation 1 (model call 7) classified a package directory lacking an init file
   as PY_NAMESPACE in `astroid/modutils.py`. Automatic original replay still failed.
3. Mutation 2 (call 11) added a namespace-spec/submodule-resolution test in
   `tests/unittest_modutils.py`; it was a test addition, not another implementation
   fix. Original replay still failed. At this intermediate diff, the registered
   suite passed 1,232 tests (69 skipped, 15 xfailed), and the selected added test
   passed once. Neither check exercised away the original caller failure.
4. Mutation 3 (call 19) made `check_modpath_has_init` consult namespace specs.
   Original replay still failed. All three candidate failures appeared in the next
   dispatched states (calls 8, 12 and 20), tied to their current diff/action IDs.
   Automatic results travel in completion state rather than native model-call
   outputs; a missing native-output match is not missing feedback.
5. Call 22 received an 8,979-token normal ceiling after cost reservation and
   exhausted it without a tool call. The separate protocol correction at call 23
   had a 25,000 ceiling, used 13,265 output tokens and produced mutation 4: removing
   terminal `__init__` from an accepted module path. Its original replay still
   failed. The fourth accepted mutation exhausted the edit limit, so no further
   model call, final-diff regression check or finish occurred.

All five probes (baseline plus four candidates, two target calls each) had complete
captures and consistent host/authored values. Their normalized actual-condition
hash was identical:
`sha256:d50e9bc224f44825513a583b5d7af6ca8a18feeaff8cb15cc3fcbdd01cb883e6`.
The final original obligation remains refuted. The intermediate regression PASS
must not be attributed to the final two untested implementation changes.

## Interpretation and next question

Host diagnostic calculation was selected and exercised; the initial extraction
was already correct. The baseline and every candidate retained the original
failure. This supports the live consistency/feedback mechanism for these selected
literal rules, not a causal claim that the new host code prevented a mistake.

No conflict occurred, so bounded baseline correction, supersession, stale-note
handling and their extra reserve remain locally tested only. The previously
implemented protocol correction was exercised successfully as response recovery,
but its valid mutation did not repair the task. Reusable early replay was eligible;
finish receipt reuse was not exercised because finish never occurred. No exceptional
diagnostic using only the minimum reserve was offered in the dispatched states.

This result preserves the original-failure completion gate and the host judgment
implementation without claiming repair gain. It does not justify increasing limits
just because money remains. The selected repair hypotheses changed helper-level
namespace/path behavior while the actual caller still attempted the missing init
file. The next unresolved question is where the original caller constructs/uses
that path and whether the changed functions participate in that execution. A
bounded public call-path diagnostic could distinguish an unexercised branch from
a changed result ignored downstream; neither explanation is established here.

## Integrity and evidence

Result root: `C:/pt/judgment-live-v1`. The collector verified all 113 sealed
repository inputs, hash-chained journals, 127 content-addressed objects at collection,
matching settled provider dispatches and action_id/input_hash pairs. No timeout or
cleanup failure was recorded. Private evaluator and continuation artifacts were
only hashed; private reasoning/evaluator contents were not used.

- Request: `sha256:fea074dd5e77dcb205247dbfec74c695e411f5efba7dc9088cbd824f43b46cfa`.
- Collection: `sha256:2d2ebd6bd93a9c9d087a629eb22703e1fa44cf5a7a35169854a06a65d235dc12`.
- Public analysis: `sha256:5c49cdb8b4a9247f996acfefdd1f568ffd09de47aeb5b25407002c5f537aa226`.
- Judgment analysis: `sha256:bf7dc4f0482c3e01cf3530e5200a9990ad5d5f0ad0e4b2b3fcf2db247d6c37c1`.
- Delivery audit: `sha256:8a7209cae2bb3aefab58f8d68e938af2833f1141997d506e9f44302350307973`.

Token metadata: 855,190 input (321,280 cached), 134,992 output including 123,491
reasoning tokens. Reasoning is not added again to output. An initial offline audit
failed because automatic replay requests have nullable purpose; that script and
failure were retained. Its follow-up normalized that field and completed without
another model/probe/evaluator execution. Documentation validation and final docs
commit are bound in the external closeout receipt. The one paid allocation is
closed; unused funds do not authorize a continuation. Runtime source was unchanged.
