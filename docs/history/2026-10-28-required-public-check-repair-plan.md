# Required public check repair follow-up

## Material Passport

- Date: 2026-10-28. Code experiment preparation, official=false.
- Status: PREPARED_AWAITING_NEW_COST_APPROVAL; provider/target executions zero.
- Runtime change: `aaf598c1`; preparation corrections: `f73ba6c9`, `0eb1c972`.
- Scope: one assisted checkpoint continuation, not a fresh solve or causal estimate.

## Question and decision

The [preceding continuation](2026-10-28-probe-revision-repair-results.md) acknowledged
three public regressions and resubmitted the unchanged patch despite an affordable
repair path. The [implementation](2026-10-28-required-public-checks.md) now registers
those public counterexamples as required checks rather than advisory feedback and
a post-submission replay.

Test whether the same model makes a new repair, receives current verification,
preserves the already-passing original call and passes all 11 required public path
cases before normal finish. Failure to fix them must remain a failed/incomplete
result. Finish blocking alone is mechanism evidence, not successful repair.

The original F0010 call already passes at this checkpoint; this trial does not
measure newly discovering or solving that original failure. The model may stop,
produce an incorrect patch or fail its response. This would leave repair uptake
unestablished even if the host correctly prevents premature finish. Public success
with isolated acceptance failure remains incomplete task repair.

## Fixed conditions and bounded changes

- Astroid-1333, dev-train `current-dev20/13/public.yaml`.
- Source `C:/pt/caller-completion-repair-run-v1/repair`,
  `run_dev_3e21775752a54cae`, cut 212 excluding the prepared request.
- Candidate `sha256:141dc0f8e373a23b7379661de8c08b3b0f07c6fa010f2d7bbb8b18b0ed74967f`.
- `gpt-5.4-2026-03-05`, xhigh, one invocation; credential file
  `C:/Users/geonj/Documents/PatchLoop/.env`.
- Proposed fresh invocation cap **USD3.38078870**. Historical USD1.11921130 is
  inherited accounting only, preserving the original USD4.50 cumulative ceiling.
  All earlier allocations are closed; their unspent funds are not reopened.
- Eight remaining responses including at most one correction, fourteen remaining
  ordinary tool actions, at most two additional accepted edits.
- Context 60K, normal output 40K, protocol correction output 25K.
- Global limits remain 20 responses, 40 actions, three edits and 2400 seconds.
  Remaining solver 1388.349 seconds; isolated evaluation reserve 390 seconds.

The former 13 ordinary actions plus one final replay become 14 ordinary actions;
1353.349 solver seconds plus 35 final-check seconds become 1388.349 solver seconds.
There is no separate post-finish public target execution. Each registered matrix
execution reserves its 35-second timeout plus the standard five-second overhead
in the ordinary completion route. Overall caps and original verification are unchanged.

The same public packet, caller registration, prepared dependencies and original
case identity are retained. No hidden evaluation material, reference/operator patch,
future trajectory or new repair hint is supplied. The 12th preexisting discrepancy
is excluded from the required 11 and reported separately.

The actual first request offers only `replace_text` and `stop_task`. The required
path fits three responses/five actions, but the protected exploration forecast
requires nine responses/twelve actions; only eight responses remain. Existing
current source is available. This changes the action space as a consequence of
registering the failure: do not interpret a missing exploration action as the
model freely declining exploration, or claim to isolate a prompt-only effect.
The active forecast is in the actual first request, not the inherited cost snapshot
in `manifest.remaining_budget`. This single run supports no general repair-gain claim.

## Preparation and controls

The first preparation stopped because its audit required optional read/search
tools. The audit now requires repair/stop, verifies actual current source, and only
rehearses a later read if offered. Runtime admission and budgets were not loosened.
Fourteen driver tests and Ruff passed. The saved first input contains 21 current
editable source spans, 23,997 characters, exactly matching the canonical context.
The public check program occurs once; its overlay references that definition.

Preparation v1 remains as failed evidence. v2 is superseded because a diagnostic
refactor changed its implementation fingerprint after offline fork creation.
Final v3 was prepared with frozen source; both offline forks match the manifest's
runtime and diagnostic fingerprints. All versions used finite scripted clients,
zero real provider counts/calls and zero target executions. v3 passes first-request
parity, a fresh scripted dispatch/stop and independent read-only review. The optional
later-read path is NOT_EXERCISED because that tool is closed. Prior local tests cover
automatic check feedback after edits; actual model uptake remains the trial question.

Read-only task/source/image/dependency preflight is READY. No Docker startup,
pull/build or credential-content read was performed.

## Outcomes and stopping

Record new edits, current-diff original-call/processing evidence, ordinary public
regression, required 11-case assessment, delivery to the next model input, normal
finish/submission, isolated acceptance, safety, settled cost and time separately.
Old PASS reuse on an unchanged patch is not a new repair. New public repair support
requires a new candidate and all current required evidence. Missing checks,
unresolved failures, stop and limit exhaustion cannot count as successful repair.

Monitor the process and only this new result directory. Count immediately before
dispatch, retain zero SDK retries, and stop on count, transport, billing, execution
or cleanup uncertainty. No automatic repeat/resume. A settled failure is a result,
not permission for another attempt.

## Execution package

- Plan: `C:/pt/required-public-check-repair-plan-v3/manifest.json`.
- Manifest: `sha256:0e64d7e62d5648e4904fd9640f026105236eb492002cf31b099e966a78e2eca1`.
- Script: `C:/pt/required-public-check-repair-plan-v3/run.ps1`.
- Result root: `C:/pt/required-public-check-repair-run-v1` (not created).
- First request: `sha256:0e2222d8e1affee90912be8db98d323f135463c5e7fbcbdba76ab834d42228dd`.
- Required check binding:
  `sha256:053763e9a6bf4de62215fc2b0fa2ed38365a35f90352f05b968a920bf8ba2cda`.
- Runtime: `sha256:5f53471aec9fac1305fdb7c79b673a525aec6cd9ed8600da57b486fa80a85634`.
- Diagnostic: `sha256:c4387d8fc071d02b41260247b5a11423031633161e0d8525b941362bb8601b34`.
- Preparation commit: `0eb1c9727dba318c70cc530c3a78f14b3e12ca73`.
- Preparation evidence: `feedback-audit.json`, `preflight.json`,
  `independent-audit.json`, `first-request.json` and the append-only preparation journal.

Execution is pending the new positive invocation-wide cost approval required by
AGENTS.md Hard gate 5. This package does not authorize spending.
