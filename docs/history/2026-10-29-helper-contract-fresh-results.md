# Helper API clean-start result: verified delivery and acceptance PASS

## Material Passport

- Date: 2026-10-29 KST. ARS experiment-agent; one approved code experiment.
- Astroid-1333, dev-train current-dev20/13; official=false, claim_eligible=false.
- Implementation `14a1aa70da1e9e4d083cb3119afcde8e1bb6a8f6`; execution checkout
  `af30c773` (preparation documentation only after that implementation).
- Result: **EVALUATOR_PASS**, `cases_verified_delivery`; original obligation verified,
  public regression PASS, isolated acceptance PASS and safety PASS.
- Accounting SETTLED: **USD 2.0153455 / 4.50**, 609.474 active seconds.
- Allocation CLOSED. Unused USD 2.4846545 is not authorization for another run.

## Question and execution

The [plan](2026-10-29-helper-contract-fresh-plan.md) tested whether the shared API
contract permits a valid first original call, then useful observation and repair.
The [previous run](2026-10-29-observation-opportunity-fresh-results.md) failed before
original reproduction after missing setup arguments and an undisclosed root-count
limit. The [change](2026-10-29-helper-api-contract.md) aligned guidance, static
preflight and runtime feedback without increasing limits.

The user approved `& 'C:/pt/helper-contract-fresh-plan-v1/run.ps1'`, one run with
a new USD 4.50 invocation cap and manifest
`sha256:8512c820b8defdd515ff92996f28742e295af2144147ed2d0080b418c93e9b39`.
The exact command ran once: gpt-5.4-2026-03-05(xhigh), repository `.env`, responses
20 including correction 1, actions 40, edits 3, context 60K, output 40K/25K,
2400 seconds including 390 reserved for isolated evaluation.

It began from the clean prepared original with the same public dependencies and
read-only pylint caller source. No patch, checkpoint, previous observations,
operator counterexamples, reference patch or private evaluator content was seeded.
The serialized request differed from the closed baseline only in the result root;
runtime and probe profile were the intended intervention.

First actual input was 9389 tokens. Prepared/count/dispatch identities matched;
differences from the offline request were only remaining time and segment ID.
The actual input contained the shared setup and observer descriptions. This checks
what was sent, not whether the model used each sentence causally.

## Public trajectory and repair

Run: `run_dev_8b2d82c60a4c455c`.

- After four searches, the model's second response requested the original probe.
  It supplied all arguments for six setup comparisons, used one input root with
  generated output kept separate, and invoked the actual zero-argument CLI signature.
  Both declared calls entered the target and had complete captures. The directory
  call emitted F0010 without W0611; the file control emitted W0611 without F0010.
  Host comparison matched the declared original failure on unchanged source.
  Acquisition used one actual attempt and zero request-error slots.
- The next request exposed `observe_original`; the model selected it. Sequence 55
  replayed the real call but tracing hit 200001 call events against a 200000 limit.
  Selected events were zero; focus/watch status stayed UNKNOWN and the observation
  was insufficient. This does not confirm or refute the proposed internal path.
- The model continued public source/test/caller exploration and one general helper.
  That helper completed, but a result-format lookup caught an AttributeError for
  `ModuleSpec.module_type`. Its output was not a complete module-spec comparison.
  Successful action/execution status must not be read as faultless diagnosis.
- Sequence 247, the first edit in response 16, changed
  `astroid/modutils.py::modpath_from_file_with_callback`: caller-supplied `path`
  entries now have normalized variants tried before their original forms, matching
  the treatment already given to `sys.path`. The raw-path fallback is retained.
  The patch adds four lines and removes one. Its link to the original observation
  honestly retains `observation_status=insufficient`; no trace confirmation is minted.
- Sequence 254 revalidated the original case on that candidate. Both directory and
  file-control calls had `F0010=false`, `W0611=true`, with comparability `same`.
  This is selected public error-absence and processing-marker evidence on the
  unchanged invocation conditions, not exhaustive semantic coverage.
- Sequence 268, current-diff base-regression: **1231 passed, 69 skipped, 15 xfailed**,
  exit 0, no timeout/truncation/cleanup failure. The structured check result
  (`passed`, `exit_code`, `diff_hash`) and original replay reached the final actual
  model request. The raw pytest summary was not itself included in that request.
- Sequence 283, normal `finish_task` returned `cases_verified_delivery`; sequence
  287 recorded the exact patch. Isolated acceptance and safety both passed, ending
  with EVALUATOR_PASS. Mutation, original replay, public check and submission share
  diff hash `sha256:b26a44bbe7746c3d11876a4dca1a1e2afb7a483c1fa66df7ac786bff7987a5bc`.

The host's original obligation is verified and submission status is cases_verified.
Its separate generic `repair_success` field remains `not_assessed`; the task-level
success statement rests on the explicit isolated acceptance result, not promotion
of that generic field or on the model's own assessment.

## Interpretation and limits

The first-call bottleneck did not recur: a valid original reproduction was acquired
and the same-budget autonomous run delivered a patch accepted by the task evaluator.
This supports retaining the shared API fix and shows that this execution reached
and completed repair. It does not isolate which part of the bundled intervention
caused the difference, or establish a success rate on other tasks or repeated runs.

Helper API correction, failed-repair revision and regression-failure revision are
**NOT_EXERCISED**: the API call was valid initially, and the first patch passed the
selected original/public checks. Their local tests remain separate evidence.
The model selected observation, but the capped trace did not test its internal
path hypothesis. General diagnostic code was also imperfect. Do not explain the
successful repair as a fully observed causal chain or claim all helper errors solved.

Exploration consumed 15 responses before the first edit, so response economy remains
a limitation even in this success. There is no basis here for automatically raising
limits or spending unused funds. The next unresolved questions are repeatability
and useful bounded trace collection, each requiring its own justified scope.

## Accounting and durable evidence

- Responses 18/20, input counts 19, actions 32/40, edits 1/3. All responses completed.
- Actions: search 18, read 7, original observation 1, run_probe 3 (including automatic
  candidate replay), edit 1, public check 1 and finish 1.
- Input 686851 including 107392 cached; output 35990. Maximum input 56878 and
  output 8995. Cost USD 2.0153455; active time 609.474 seconds.
- All count/provider/action starts and finishes pair; usage and cost sums agree.
  No protocol correction, automatic retry or additional post-run target execution.
- All 14 bound files and the runtime hash remained unchanged. Existing pinned images
  were used. No private evaluator content was read or returned to the model.

Result root: `C:/pt/helper-contract-fresh-run-v1`.
The collection, summary, 290-event chained journal, accounting audit, first
reproduction audit, public outcome audit and submitted patch retain the evidence.

- Journal: `sha256:42a5eeca71fba0d4f64b097678246f626873f6dd1f1ef5fae254b7562a2c246f`.
- Public outcome audit: `sha256:2af5db7d9ddfcb92d4ffbef03c9a795557f75d34fceb06a90c95f27833e0a2bd`.
- Submitted patch: `submitted-candidate.patch`, hash equal to the candidate diff above.
- Plan root: `C:/pt/helper-contract-fresh-plan-v1`, including exact approval,
  first-live-request audit and append-only preparation/execution/collection receipts.

Two shared-context workers checked the public first request and trajectory; the
parent verified accounting, bound bytes and patch contents. This is not blinded or
cross-model review. Post-run work was read-only analysis and documentation, with no
new model, count or target calls. Runtime tests were not repeated unchanged.
Five documentation checks passed after updating the result and current status.
