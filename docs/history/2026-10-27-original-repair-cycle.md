# Original-call feedback between saved-candidate repairs

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: implementation and focused local validation
- Origin Date: 2026-10-27
- Verification Status: IMPLEMENTED / LOCALLY TESTED; live NOT_RUN
- Version Label: feedback-source-pair-v2 / original-call-feedback-v1

The user requested a post-edit original-call recheck, delivery of its failure to
the next model response, and resources for further diagnosis, repair and final
verification. This is implementation/local-test authorization. No new paid run,
credential read, target Docker execution or task acceptance was performed.
The preceding allocation is closed; the changed scope requires fresh preparation
before any separately authorized live execution.

## Problem, evidence and decision

The [preceding R0/R1 pair](2026-10-27-feedback-source-results.md) retained F0010 in
both rows. The complete source was delivered, input/output/cost ceilings were not
reached, and the first accepted edit ended each model row. Public failures were
collected afterward and could not influence another response. This diagnosed a
known control-flow limitation, not evidence that larger context would repair it.
It matters because a wrong first premise could never be revised in that experiment.

Keep the existing shared loop and add an explicit original-call cycle to the saved
candidate diagnostic. Legacy profiles still stop after one accepted edit. This
repairs the demonstrated experiment boundary without adding another hypothesis
declaration or changing production defaults. Bad diagnosis, ineffective edits and
insufficient useful reasoning remain plausible causes of future task failure;
making feedback available cannot establish that a model will use it correctly.

## Implemented behavior

`diagnostics/feedback_source.py` supplies an `OriginalCallRecheck` controller to
`exception_frame_repair.run_model`. Each accepted replacement now replays the
original public request before the next model response. A fresh clean baseline is
executed once; candidate receipts are bound to the original arguments, public task,
prepared source, dependencies, image/profile and current diff. Completed identical
actions reuse their durable receipts. Unfinished actions are never retried.

The next request receives the current diff, host comparison, captured output,
public exceptions and scoped changed-line observation under
`current_original_recheck`. It can read current code and revise again. The preload
is labeled `initial_source` with its seed diff so it cannot masquerade as current
source after mutation. Returning to an empty diff is a known failed candidate that
can be revised again. Incomplete execution/capture stops before another model
dispatch and stops remaining rows; it is not treated as an ordinary task failure.

The controller uses the existing public original-call judgment, including its
call-identity/control-output distinctions. Original support does not mean task
acceptance. After the model phase, every known edited candidate still receives
public controls and regression. Final checks reuse only the matching original
receipts; missing or changed-input evidence cannot silently dispatch unbudgeted
replays. Isolated acceptance stays outside the model conversation, under its
existing eligibility rule. Empty diff records `NOT_RUN_NO_DIFF`. Verification
completion and acceptance PASS/FAIL are separate fields.

## Resource contract

The v2 preparation defaults are identical between R0 and R1, but differ from the
closed v1 pair. They are not authorization or a controlled estimate of feedback's
isolated effect.

| Resource | v2 diagnostic ceiling/reservation |
| --- | --- |
| Normal responses / protocol correction | 16 / 1 global correction |
| Model tool actions / helper probe requests | 24 / 2 |
| Additional accepted edits | 3; imported seed is not an edit |
| Ordinary / correction output; counted input | 40K / 25K; 60K, unchanged |
| Future output funding | 8,192 diagnosis + 8,192 repair + 128 final-response tokens when another cycle fits |
| Host original-call actions | At most 4: one baseline plus up to three candidates |
| Model and inter-edit recheck deadline | Shared 600 seconds |
| Final public checks | 11 actions: five base/candidate controls plus regression; separate 390 seconds |
| Isolated evaluation | Existing separate 390-second worker budget |
| Future row / invocation monetary cap | $1.20 / $2.40, unchanged; not spent in this change |

An offered edit leaves at least one response and action to consume its recheck.
Inspection/probes leave an edit and that final response. When another cycle fits,
cost admission reserves its diagnosis and edit separately from the current output
ceiling. It can release optional continuation/exploration funding when necessary,
freshly counting each changed request. It skips identical narrowing steps instead
of declaring a premature cost stop. The one protocol correction and all global
counters are never replenished after an edit.

Before dispatch, the model timeout leaves 60 seconds per required original action
(120 before the uncached baseline) and five seconds for the following response.
Insufficient time before the first request gives `RECHECK_TIME_UNAVAILABLE` without
changing the sealed request or calling the provider. Subsequent time exhaustion
can restrict the request to stopping. These are bounded opportunities, not a
guarantee of useful model output or successful verification. Final public and
isolated checks have independent host phases and do not consume model API funds.

## Local evidence

- Focused owner/legacy selection: **82 PASS in 27.91 seconds**. It covers public
  failed-edit feedback followed by a current read and second edit, empty-diff
  retraction, incomplete recheck stopping, fixed global budgets, cost narrowing,
  insufficient initial time, durable receipt reuse, stale-diff/input rejection,
  final-check reuse, and preservation of the legacy one-edit path.
- The integration sequence uses a scripted SDK, small public fixture and recorded
  public observations. It proves host/request wiring, not real F0010 repair by a
  model. Local provider calls and credential reads: zero.
- Fast suite: **472 PASS in 105.36 seconds**, including isolated mock evaluation.
  This is not a full-suite result; previously recorded broader-suite failures are
  outside this change and remain unresolved.
- Ruff passed for `patchloop`, `tests` and `diagnostics`; `git diff --check` passed.
  Final documentation checks: **5 PASS in 0.13 seconds**.
- Machine-readable focused and quick receipts are outside the repository:
  `C:/pt/tmp/cyclefinal27b.xml`, `C:/pt/tmp/cyclequick27.xml` and
  `C:/pt/tmp/cycledoc27.xml`. Tests use short
  external workspaces; no generated execution state is added to the checkout.

The result permits a later bounded test of feedback use. It does not establish a
successful new model repair, an independent acceptance gain, generalization or a
need for a larger context window. Any live comparison must disclose the changed
response/action/edit horizon and separate delivery, model action, public behavior
and isolated acceptance outcomes.
