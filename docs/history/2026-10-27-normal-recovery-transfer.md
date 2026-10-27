# Transfer of feedback and resource contracts to the ordinary runner

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: implementation, focused local validation and execution preparation
- Origin Date: 2026-10-27
- Verification Status: IMPLEMENTED / LOCALLY_TESTED; fresh live trial NOT_RUN
- Baseline: `0f0cd23a`; all earlier paid allocations remain closed

The [saved-evidence trial](2026-10-27-public-regression-cycle-results.md) demonstrated
regression failure uptake and a successful revision, but used a separate diagnostic
loop, prepared observations and synthetic submission. The next product question is
whether normal acquisition, repair, verification and `finish_task` can achieve the
same outcome from clean source. Copying the whole diagnostic would add another
workflow without establishing that the existing runner lacks its capabilities.

## Findings and intervention

The ordinary runner already retains public check failures, automatically replays
acquired originals after edits, rechecks a known failing registered check, and
requires every current-diff registered check to pass before `finish_task`.
Two actual-request integration tests confirmed that ordinary result handoff and
a forced 60,001-token overflow preserve latest failure details, action/diff links,
current-file source and counters. The overflow path used one additional count,
not another generation or renewed budget. No source/context rewrite was needed.

The actual resource gap was monetary and temporal: the selected `per-call-v1`
profile does not reserve successors, while the existing recovery policy priced
nonfinal successors at only 128 output tokens and provider calls could use the
entire solver deadline. Physical call/tool forecasts alone do not protect useful
repair output or time for mandatory checks and completion.

The existing opt-in `completion-recovery-v1` now prices successor roles. Required
repair uses the configured ordinary ceiling; preparation, checks, continuation
and finish use min(8,192, ordinary ceiling). The independent correction allowance
and its one-credit recovery identity remain. An already eligible action can protect
one future public-failure revision when physical capacity exists. Required immediate
completion may release speculative recovery, and the per-action record says so.
No new policy name, CLI option, model tool, forced inspection or unrestricted shell
was added. `per-call-v1`, reserve/minimum policies and the selected general baseline
remain unchanged; the planned transfer trial explicitly selects recovery.

Review exposed a reservation collision: with only a 128-token current floor,
optional exploration could reserve a future full repair while starving the current
repair response. The current required repair now protects its full output first;
optional actions close when they cannot leave that and their successors funded.
Future check allowances also match their actual 8,192-token current floor, avoiding
an envelope that becomes unaffordable on the very next response.

Count and generation share a deadline ending before reserved check/probe time and
30 seconds per successor. Nominal check timeouts include five seconds per execution.
Original-only failure cannot receive the registered-recheck call discount. Paired
tests reserve both executions, and a test-addition route retains its paired test,
first host replay/recheck and later source repair. These allowances do not guarantee
all filesystem/setup overhead or a useful answer. Existing evaluation reservation,
idempotency and uncertainty handling remain.

Ordinary regression scheduling remains model-selected, with automatic replay for
an already known failed registered check. This does not copy the diagnostic rule
that unconditionally runs every regression immediately after every edit. Existing
finish checks enforce current-diff PASS; the fresh trial must establish whether the
model selects and uses that verification path.

## Local evidence

- New successor cost tests and existing recovery/finalization owner tests:
  42 PASS / 21.16s.
- New ordinary feedback and resource tests: 11 PASS; actual count/request capture,
  forced overflow, failure/source currency, full repair funding, insufficient time,
  original-only recovery and paired-test reservations.
- Quick: 500 PASS / 61.887s with four workers, including isolated mock evaluation.
- Ruff and diff checks PASS. The first quick pass exposed four stale literal
  contract expectations; those were updated to v3, their 14-test owner file passed,
  then the complete quick selection passed. No implementation regression was hidden.

The local trials use scripted providers/local fixtures. No new real model input
count, provider generation, credential read or Astroid execution occurred. Tests
establish implementation behavior, not fresh-solve success or general quality.
Receipt: `C:/pt/tmp/normalquick29final.xml`. New test files are
`test_recovery_successor_cost.py`, `test_normal_recovery_resources.py` and
`test_normal_feedback_continuation.py`.

## Next trial and limits

Prepare one clean-base Astroid-1333 dev-train run through ordinary `run_dev`, with
mini/xhigh, 60K input, 40K ordinary/25K correction, 20 total model calls, 40 tools,
three accepted edits, and 2,400s including a 390s evaluation reservation. The proposed
new invocation cap is $4.50. At pinned mini rates, 20 ordinary maximum requests cost
$4.50; 19 ordinary plus one correction cost $4.4325. This covers the configured token
envelope, not useful output, wall-time sufficiency or success. No retry is included.

Supply only the public task, clean repository and prepared public dependencies.
Do not supply prior patches, source excerpts, helper results or later observations.
The normal helper can inspect the pinned public caller; it does not currently offer
the diagnostic's `dependency:pylint` read/search scope. That source-access difference
is explicit, not silently treated as an identical experimental condition.

Acceptance criteria distinguish original reproduction/acquisition, first repair,
public verification delivery, any revision, actual `finish_task`, and isolated
acceptance/scope/safety. A first-pass repair leaves revision NOT_EXERCISED. This is
a within-task transfer pilot, not a causal comparison or held-out generalization.
The exact request and command require new plan-bound approval after sealing.
