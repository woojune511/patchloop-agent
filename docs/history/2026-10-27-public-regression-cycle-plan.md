# Sealed live public-regression revision trial

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: execution preparation and read-only preflight
- Origin Date: 2026-10-27
- Verification Status: PREPARED / PREFLIGHTED; live NOT_RUN
- Implementation: `ca96a4cb`; [contracts and local evidence](2026-10-27-public-regression-repair-cycle.md)

The [previous live candidate](2026-10-27-checkpoint-feedback-single-results.md)
resolved the original F0010 but broke a public symlink regression. Its model had
already stopped when that failure arrived. This trial asks whether moving public
regression before the next response and reserving one revision lets a real model
use failed-check evidence and pass both original and registered regression checks.

Run A once from the same saved public post-helper/pre-first-edit checkpoint and
seed diff. The first edit is newly model-authored; no prior failed or successful
patch is forced into the run. This exercises the newly implemented end-to-end path
without a new restoration mechanism. It may not produce a first regression failure.
A post-failure-only experiment could isolate revision further but is not this trial.

The public task, saved observations, source coverage and mini model stay the same.
The first request differs from historical A because the prompt, response/action
allowances and verification policy changed. Historical A is not a concurrent
control; no causal repair-gain, general quality or fresh-solve claim follows.
Prior operator repairs, later model patches, private evaluator details and opaque
reasoning are excluded from the prepared public request.

## Exact execution scope

- Astroid-1333, `dev-train/current-dev20/13`, official=false.
- `gpt-5.4-mini-2026-03-17`, xhigh; credential file
  `C:/Users/geonj/Documents/PatchLoop/.env`.
- A only, once; $1.20 row and invocation cap, no automatic repeat.
- Four ordinary responses, one protocol correction, five model tools, at most
  two accepted edits; zero helpers and zero optional original-call selections.
- The first request offers edit/stop. A public failure permits bounded read/search
  and one additional edit; an inspection response allows at most two reads.
- Every accepted edit is followed by original and registered public regression
  verification. The task has one registered `base-regression` check (300s).
- Up to three original host actions and two candidate regression passes.
- Input 60K; ordinary/correction output 40K/25K. Future diagnostic/repair/final
  reserves 8,192/40,000/8,192, with correction reserved separately.
- Model plus intermediate verification 1,200s; final public controls and isolated
  evaluation each 390s. A correction needs at least 30 usable seconds after reserves.
- Count immediately before dispatch, zero SDK retries. Count, transport, billing
  or execution uncertainty stops the invocation. No retry of a started condition.

Final host checks reuse exact current-diff registered regression receipts. Additional
public control cases and private evaluation remain separate later outcomes. The
configured uncached maximum token envelope is $1.0575 under the $1.20 cap; it does
not promise a usable response or a completed repair within the wall-time bound.

## Outcome criteria

The primary positive observation requires all of the following, tied to exact
public journal and request artifacts:

1. The first accepted edit has a completed registered regression FAIL.
2. Its current-diff failure, including useful public diagnostics, is present in an
   actually dispatched model request before the next edit. A counted-only request
   does not count as delivery.
3. A second accepted edit addresses that failure. Public action hypotheses, source
   changes and subsequent checks support the uptake assessment; opaque reasoning
   is not inspected. Reading before the edit is optional, not a success requirement.
4. Both the original call and registered regression pass on the second diff, and
   the model accurately acknowledges the result and stops.

Report feedback delivery, revision, final task checks, termination, cost and time
separately. Original-call identity limitations remain explicit. Hidden acceptance
is a separate host verdict and is never model-visible repair feedback.

If no edit occurs or the first edit already passes both checks, regression-driven
revision is NOT_EXERCISED. If only the original call fails, original-feedback repair
may be exercised but the regression-revision question remains unexercised. These
outcomes do not authorize another run. A second failing edit, missing feedback,
resource exhaustion or unacknowledged result is recorded as observed, without
operator repair or spending the unused cap on another attempt.

## Sealed artifacts and preflight

- Manifest: `C:/pt/public-regression-cycle-plan-v1/manifest.json`
- Manifest SHA-256: `3f470e864a1b2b2f578dcf6f727918a781b916a88795857d75ac93b22f375b19`
- Exact command: `& 'C:/pt/public-regression-cycle-plan-v1/run.ps1'`
- Script SHA-256: `ed36bc2f04df41e12e10eb0989ba9c3069863ba0b2a1279bfa8dcfed7bb680ca`
- Result root: `C:/pt/public-regression-cycle-run-v1` (absent before execution).
- Preflight: `C:/pt/public-regression-cycle-plan-v1/preflight.json`.
- Restore receipt: `C:/pt/public-regression-cycle-restore-v1/summary.json`.
- First A request SHA-256: `2319e5f25afd5eca83ee6cd2bb30c3d61bc1d2fac0b8c150a6bd1cf5e9376005`.
- Seed diff SHA-256: `93b024b3f11ef89311d9cbf5a06a56328b14f7b7d7687746e6d24a8b9fb8e3e5`.

Preflight validated the manifest and all code/task/source bindings, tracked clean
runtime inputs, restoration of the exact seed, 14 source reads/13 coalesced context
spans, new action/model/edit/time limits, both pinned local images and script syntax.
The public regression controller was constructed without executing a check; its
new-diff time requirement is 305s. Credential existence was checked without reading
its contents. No Docker startup, image pull/build, target execution, API input count
or generation occurred. Existing local tests were not rerun unchanged for preparation.

All previous allocations remain closed. Exact paid approval for this new manifest
is pending; preparation itself does not authorize execution.
