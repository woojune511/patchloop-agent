# Public regression feedback before diagnostic completion

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: implementation and focused local validation
- Origin Date: 2026-10-27
- Verification Status: implemented and locally tested; new live execution NOT_RUN
- Baseline: `5951b45f`; all prior paid allocations remain closed

## Problem and decision

The [last live trial](2026-10-27-checkpoint-feedback-single-results.md) delivered
the original-call success to the model, which stopped accurately. A subsequent
public regression then exposed a broken symlink path. Because that check ran
after the last model response, its failure could not inform diagnosis or repair.
This is a completion-order defect, independent of the earlier context overflow.
Increasing context alone cannot deliver a result that does not yet exist.

Move registered public regression checks into the existing checkpoint repair
cycle, after every accepted edit and original-call recheck. Allow one additional
edit when either the original call still fails or a registered check fails. Do not
change hidden evaluation, send private evaluation details to the model, or add
unrestricted execution. This is the saved-checkpoint diagnostic path, not a change
to every production agent profile or proof of improved benchmark accuracy.

## Implemented contract

`PublicRegressionRecheck` executes all `public.visible_checks` through the existing
gateway on the current diff. Feedback includes the check IDs, exit code and verdict,
public failure location/summary, bounded stdout/stderr tails and receipt references.
Output clipping is explicitly marked. A settled exit remains usable even if its
output is clipped; timeout, unconfirmed cleanup, infrastructure failure or a pending
execution remains incomplete and aborts further model continuation.

Each execution is bound to the public task/check definitions, execution environment,
candidate diff and `action_id + input_hash`. The controller permits checks on at most
two distinct candidate diffs. Reconstruction reuses completed receipts, executes
only never-started checks in a partial pass, and never retries an unfinished start.
The original durable gateway receipt is retained even when its model-visible view
is shortened. It is not a claim that an already-clipped gateway log is complete.

After an accepted edit, the runner clears old feedback, completes original and
registered regression verification, and then builds the next request. The current
regression is also carried through protocol correction and public context handoff.
Old-diff success cannot mark the new diff verified. If checks pass together, only
`stop_task` is offered. If either fails, the remaining allowance can fund one
diagnostic response with up to two reads/searches, one extra edit and a final
response. Exhausting the allowance preserves `registered_verification=unverified`.
This field covers the original call and registered regression, not hidden acceptance.

Final host verification reuses the exact current-diff registered receipts, including
failed receipts; it does not rerun them simply because the model stopped. Five
additional public control cases and isolated evaluation remain after the model
phase and are reported separately. This change does not make those later control
results model-visible or turn diagnostic `stop_task` into production `finish_task`.

## Bounded resources

| Resource | Prior checkpoint trial | Updated local profile |
|---|---:|---:|
| Ordinary responses | 2 | 4 |
| Protocol corrections | 1 | 1 |
| Model tool actions | 2 | 5 |
| Accepted edits | 1 | 2, second only after public failure |
| Helper / optional original selections | 0 / 0 | 0 / 0 |
| Host original actions | 2 | 3, shared fresh baseline plus two candidates |
| Registered regression | After model stop | After each edit, at most two candidate passes |
| Model plus intermediate verification | 600s | 1,200s |
| Final public / isolated limits | 390s / 390s | 390s / 390s |
| Input / ordinary output / correction output | 60K / 40K / 25K | unchanged |
| Row cap / single-A invocation cap | $1.20 / $1.20 | unchanged |

Time admission reserves both still-offered edits' mandatory checks, not only the
immediate one. For the current task these are up to three original actions at 60s
and two registered regressions at 300s, plus overhead and usable follow-up time.
Inspection leaves time for the repair response; every edit leaves its checks and
a final response. Correction retains the existing minimum 30 usable seconds after
verification reservation. Missing time closes mutation opportunities or stops before
the first dispatch rather than producing an unchecked candidate.

Future model funding reserves 8,192 diagnostic, 40,000 repair and 8,192 final output
tokens, separately from the 25K correction. At the repository's pinned mini prices,
four 40K ordinary responses plus one 25K correction, each with 60K uncached input,
cost at most $1.0575. This is a configured token-cost envelope, not a promise about
elapsed time, useful output or live repair success. The $1.20 cap still requires
fresh exact authorization for any new live invocation; old manifests no longer bind
the changed source and scope. No new live manifest or provider call was created.

## Local evidence and remaining question

The focused suite passed 108 tests in 109.69s. Review then found that gateway log
clipping had initially been treated as uncertain execution; this was corrected.
The updated controller passed 21 tests in 30.19s, followed by 9 integration/legacy
cycle tests in 69.68s. These bounded runs cover failure-feedback delivery, a real
fixture edit/read/re-edit/stop sequence, success-only closure, a second failure,
correction and handoff retention, exact receipt reuse and stale receipt rejection,
multi-check recovery, and insufficient time/cost. Models and sandbox outcomes are
scripted; no real provider or Astroid target execution occurred.

The quick suite passed 472 tests in 119.15s, including isolated mock smoke; no
separate mock was repeated. Ruff, documentation layout and diff checks passed.
Focused and final integration receipts are `C:/pt/tmp/regressionfocus28b.xml` and
`C:/pt/tmp/regressionfinal28.xml`; quick receipt is `C:/pt/tmp/regressionquick28.xml`.

Actual frozen public inputs were loaded offline, and A/B evidence expansion remained
equal. The new first request offers only edit/stop. Its hashes changed intentionally
because the prompt and resource scope changed. An independent source review checked
public/private separation, old-feedback invalidation and verification reservation.

The next live question is whether the model uses the newly available public failure
to repair within the one-revision allowance while preserving original-call success.
Local tests establish the mechanism, not that behavioral gain. The previous symlink
candidate and its failure remain immutable; this change does not patch Astroid for
the model or incorporate hidden-test hints.
