# Development direction after the fixed batch

## Decision and purpose

The user asked what repeated task diagnosis contributes to the agent's ultimate
goal. Close the automatic sequence of task-specific investigations. Put the
suggested isort ownership repair control on hold. Keep the agent baseline; no
new prompt, memory, mandatory probe, review stage or paid run is selected.

The product goal is autonomous correct repair of unfamiliar public software tasks
within bounded resources. Manually repaired benchmark cases, operator-authored
tests and revised evaluators are supporting evidence, not product improvement.
The relevant development outcome is a reusable change that improves actual patches
without unacceptable regression, resource or reliability costs.

This review synthesizes existing results; it introduces no new execution or
aggregate success estimate. Historical results retain their original definitions.

## What the evidence selects, and what it does not

| Evidence | Supported conclusion | Unsupported extension |
| --- | --- | --- |
| [OpenSandbox](2026-10-01-opensandbox-public-diagnosis.md): helper-only probe, incomplete backend validation | Verification did not cover the relevant execution boundaries | More probes or a reminder necessarily repairs that gap |
| [Isort](2026-10-01-isort-public-diagnosis.md): two probes, broad repair fails regressions, text-specific narrowing passes but loses ownership | Useful diagnostics and regression feedback can coexist with a semantically incomplete final repair | Evidence was unavailable, forgotten, or a mandatory probe would solve it |
| [Pyinfra](2026-10-01-pyinfra-v2-behavior-evaluation.md): calibrated v2 saved-patch PASS | Original assertion failures did not establish the claimed behavioral failures | Original batch becomes 1/3 autonomous successes or agent capability improved |
| [Darts guidance comparison](2026-10-01-verification-selection-comparison.md): B used probes; both patches retained the same frozen failures | Probe activity alone did not improve those repairs | One pair proves verification guidance never helps |
| [Earlier development review](2026-09-30-development-review.md): public coverage gaps, successful failure recovery and heterogeneous probe failures | There is no established universal evidence-handling defect | Every failure shares one cause or needs the same architecture |

The repeated symptom is insufficient semantic coverage of the delivered repair.
That is an outcome category, not a proven implementation mechanism. OpenSandbox
misses a boundary; isort changes the wrong abstraction after identifying ambiguity;
pyinfra concerns evaluator validity. They must not be pooled into a single model
deficiency or used to justify a general intervention by frequency alone.

Current dev/model.py already instructs the agent to identify behavior owners,
name untested assumptions, connect observations to actions, reconsider claims after
edits, and keep conclusions within check coverage. Therefore another version of
those words has no demonstrated missing instruction to supply. The existence of
instructions does not prove the agent followed them or that compliance suffices.

The closest useful hypothesis is that some final decisions use regression success
as sufficient support for a repair whose wider semantic assumptions remain untested.
Trace statements and post-run cases support investigating that hypothesis, but
do not identify whether reasoning capability, test selection, available time,
context handling or another mechanism would be improved by a particular feature.
No current missing-output, inaccessible-tool or recovery defect was established.

## Why the workflow drifted

The earlier development review already closed adjacent prompt/context ablations.
The fresh batch added useful evidence and evaluator corrections, but each local
diagnosis generated another local next step. A correct isort control would show
how that task can be repaired; without a specified agent design decision it would
not resolve whether or how PatchLoop should change. Selecting it automatically
would continue the same loop. The selection error belongs to the development
workflow and is not evidence of a runtime bug.

Stop conditions need to govern investigation selection: if the result cannot
change an identified engineering or adoption decision, do not run it merely to
finish another benchmark case. This is a development decision, not a new solver
approval gate or required per-turn annotation.

## Criteria for useful future work

Routine work can resume for a reproducible current product defect or explicit
product requirement. Fix and test that concrete contract without a model A/B.

For quality work, first name a mechanism, the behavior a concrete change should
alter, and an observation that would make it unnecessary. A new quality proposal
must differ materially from the closed guidance/probe comparisons. No candidate
currently meets that threshold in this review; there is no experiment to fund yet.

If a candidate is justified later, freeze baseline and intervention, public task
inputs, evaluator version, task selection, model, cost/time limits and stopping
rules before execution. Evaluate executed final patches, regressions, completion,
cost and time, and whether the predicted mechanism occurred. More tool calls,
better explanations and operator fixes are secondary observations, not success.
Use the exposed cases only as development/regression evidence. Any later evaluation
on tasks outside this diagnostic set needs separate scope and must honor the
project's disabled held-out/claim lanes; this review authorizes none.

Adopt only on credible improvement under the specified conditions. Otherwise
preserve the baseline and close the candidate, without automatically proposing an
adjacent wording variant. Keep original and revised evaluator outcomes separate.

## Validation and scope

Reviewed current status, current prompt, the linked fixed-batch diagnoses and
earlier comparison/closeout records. No historical record was rewritten, private
test contents projected, provider call made or task repair implemented. Only this
new synthesis and replaceable current status changed. Documentation layout/link
checks and whitespace checks validate the documentation change; no runtime tests
or smoke run are needed for this review.
