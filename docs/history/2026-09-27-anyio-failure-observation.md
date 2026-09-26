# AnyIO failure observation and prepared repair comparison

Date: 2026-09-27. Follow-up to [probe readiness](2026-09-27-anyio-probe-readiness.md)
and [planning regression](2026-09-27-planning-off-regression.md).
All results are `official=false`; no paid model call or new AnyIO acceptance occurred.

## Problem and evidence boundary

The previous diagnostic replayed the unmodified OFF source. It had not established
what the ON candidate's post-failure probe would observe. NA1's public trace already
contained a failed ordinary-cancellation case, a relevant probe question, an empty
timeout and a later cost stop. A missing observation and an incorrect interpretation
are different problems; the latter had not been tested at this checkpoint.

Source: `planning-off-regression-20260927-v1/NA1-public-timeline.json`, model calls
11 (candidate), 12 (public lifecycle check), 13 (probe). The source run is
`run_dev_444f104bb27645d3`. Only public action/check evidence was inspected.

New packet: `C:\pt\analyses\anyio-observation-repair-20260927-v1`.
Runtime remained `sha256:e3b533ac585ea2b48d159a6f8449d3996cd991b3da73fa268dbda71f8d5230c3`.
No product source, public task, model prompt or tool schema changed.

## Exact public reproduction

The original generated mutation was applied to a fresh local prepared-source clone,
then its canonical Git diff was verified. The generated mutation text and canonical
diff have different byte identities; the observed workspace diff is authoritative.
Independent original/corrected clones received that same canonical candidate.

- Candidate: `sha256:5301a0333fbc718bbb0cf822d63796116a67896e8fa71a607a1f2363cdd2b8b8`.
- Probe: `sha256:ac9690149fcc5a3c8694a3db21859479a19ba610434f67551b80502c653d5cc8`.
- Snapshot: `sha256:1b086966cc9263d4150958c4f700382f388bd73333c41d937be99485489816db`.

The program, question, candidate, pinned image, changed-line collector and sandbox
controls were the same. A 120-second operator deadline allowed dependency copying
while retaining the full 30-second execution timeout in both cases. Only the
dependency inventory and its derived profile hash differed in execution policy.
The existing daemon/image was used; no Docker start, pull or build occurred.

| Dependency bundle | Process outcome | Public observation |
| --- | --- | --- |
| Original runtime-only | Timeout, 33.840 seconds overall | Empty stdout/stderr |
| Corrected pytest bundle | Exit 0, 21.768 seconds overall | Runner task cancelled/done; teardown raises `ClosedResourceError` |

The corrected program reports three stages: fixture setup with the shared task
alive; ordinary cancellation with that task done/cancelled and pending uncancellations
zero; then failed fixture advancement. No fixture cleanup event appears before the
last print. The print precedes the runner context's exit, so this probe does not
observe any later generator-shutdown cleanup.

The existing public check had independently reported 6/7 cases passing, with
`explicit_cancel: setup_and_teardown_passed` failing and cleanup task/context
mismatches. The new observation explains a concrete failure path in this candidate:
ordinary cancellation ends the shared runner before normal fixture advancement.
This is not a claim that the unmodified base passed that case, or a hidden-evaluator
cause. NA1's original empty timeout was not separately instrumented for its internal
exception; the earlier OFF replay supplied the missing `_pytest` exception evidence.

Exit zero means the diagnostic completed after catching and printing exceptions,
not that the candidate passed the task. The original model did not receive the
corrected observations. Its final cost-limited response remains unaltered.

## Prepared next comparison

The packet's `compare.py` reuses `candidate_review_repair.run_seeded`, the ordinary
`run_dev`, the existing bounded provider collector, settled-usage audit and public
input reconstruction. It does not add a product policy or task-specific repair hint.

Both arms begin with the same saved candidate, consume one of four mutation slots,
and get equal fresh budgets. A receives the old-bundle timeout receipt; B receives
the completed observation. Both receive the same probe program/question and literal
public requirement. Their future probes use the corrected bundle. No old native
reasoning, plan, notes, registered-check receipt/state or acceptance is inherited.
The original question mentions the earlier explicit-cancellation failure in both
arms; that model-authored claim is not a fresh registered-check verdict.

This tests whether supplied execution evidence changes fresh candidate repair.
It does not measure probe selection, original-run continuation, or general success.
The source run's failed check selects the seed but is not imported as live check state.
New runs must perform their own registered checks and isolated submission evaluation.

Fixed proposal: `gpt-5.4-2026-03-05`, xhigh, desired 25,000 output tokens;
segmented-v1/result-or-size-v1, brief-v1, probes/none, repair-recheck, protected-v1,
per-call-v1. Order NA1, NB1, NB2, NA2, repeat one each, $1.20 each / $4.80 total.
Keep the ordinary 40 model/100 tool/4 mutation/1,800-second limits. Counts, provider,
billing, continuation, cleanup or integrity uncertainty stop the group. No retries,
replacement samples, automatic resume, budget transfer or extra runs are allowed.

Primary metric is acceptance PASS / planned two per arm, retaining NOT_RUN, submission,
safety and infrastructure categories. Review public interpretation, edit scope,
changed/preserved lifecycle checks and subsequent action. Costs and resource stops
remain separate. Full protocol and frozen requests are in the external packet.
The group is prepared, not authorized or collected; previous unused funds are closed.

## Local validation and limits

Both actual public candidate/feedback inputs were delivered to a scripted stopping
adapter. After removing the declared observation and measured/derived run identities,
their native initial states and tool schemas matched. These previews used a local
mock envelope with the evaluator environment omitted in memory. They executed no
check or evaluator and make no model-quality claim. The initial incompatible mock
envelope attempt stopped before execution and is retained in its separate directory.

Existing candidate-repair and documentation tests passed: 24 in 194.27 seconds,
including eight fixture smoke paths reaching mutation/check/submission/isolated
evaluation. This broad selection exceeded the two-minute focused target. Separate
packet control tests verify input equality, tamper detection, budget binding and
runner-hook restoration. Ruff, final documentation checks and integrity results
are recorded in `validation.json`; product-wide regression was not rerun for this
external diagnostic and documentation-only change.

Historical files and both dependency bundles remain unchanged. Prepared source,
candidate identity, source/snapshot hashes, journal chains and owned-container
absence are checked again in the packet. No new acceptance result or default
adoption is established. The remaining question is how the model uses this available
observation, not whether the selected probe can expose the failure.
