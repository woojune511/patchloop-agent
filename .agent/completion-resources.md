# Completion resources and bounded original-failure diagnosis

`completion_budget.py` is a pure forecast; `runner.py` admits real model/tool work
and cost. `completion_reproduction.py` projects public invocation evidence and
durable diagnostic consumption. Runtime hashes bind these changes on resume.

## Early execution and receipt reuse

The projection marks `early_replay_reusable` only when every case is a healthy
replayable original failure acquired on the unchanged base, every current result
is settled and comparable, and none is pending, unverified, unestablished or
conflicting. Eligibility uses all cases before display truncation. The runner
also requires the probe backend to be available.

For that state, the failed-original recovery branch excludes one failed finish
model call and its tool action. An early mismatch reaches repair before finish;
finish reuses the same case/diff action rather than discovering a new failure.
Actual read, mutation, rejection recovery, registered check and replay actions
remain reserved. Minimum completion is unchanged. Deferred, mixed, unacquired
or unknown cases keep the conservative finish fallback. An eligible automatic
registered recheck saves a model call, never its real tool action.

## Independent correction output

`max_output_tokens` remains the desired ceiling for normal generations. Optional
`max_correction_output_tokens` is a strict integer from 128 to 128000, allowed only
with `completion-recovery-v1` (which requires segmented context). It can be lower
or higher than the ordinary ceiling. The CLI flag is
`--max-correction-output-tokens`.

Omission preserves request field serialization and the coupled correction ceiling.
The current cost contract also binds the finalization floor described in
[completion feedback](completion-feedback.md). An explicit value binds model identity and
envelope; changing or removing it on resume is rejected. New defaults do not
silently allocate 25K when a different ordinary ceiling was requested.

One run-wide correction reserves a model slot plus 60K uncached input and the
correction output allowance, with no tool slot. The first durable protocol
correction spends this credit. Its prepared/count request and dispatch use the
independent ceiling as both desired and minimum output. If the full correction
plus the offered successful successor cannot fit, admission stops. Normal calls
retain exact-count output reduction. A valid action or restart never renews the
credit; tool failure and unknown billing do not earn funded retries. Count,
transport and billing uncertainty retain the existing stop-all behavior.

## One diagnostic opportunity for a refuted candidate

A nonempty candidate with a comparable current refutation of an acquired original
case can spend one preparation read/search and one model diagnostic probe
using the minimum successful completion reserve. Baseline acquisition, a helper,
old-diff failure or missing/incomparable observation does not grant this credit.
A qualified complete selected-call exception is separate positive failure evidence
and uses the same finite opportunity, while whole-case UNKNOWN stays unverified.
The actual minimum repair, fresh checks, original replays and finish must still
fit the remaining model calls, tool actions and selected cost-admission policy.
No cap or mutation capacity is increased. A diagnostic probe reserves one possible additional case
replay: a new binding can add work after the next edit.

Only these bounded exceptional actions use the minimum path; normal protected
admission remains available when it already fits. An exceptional inspection has
parallelism one and a last-opportunity warning. Spending speculative recovery
means subsequent rejection/check/reproduction failure recovery is not guaranteed.
The full protected forecast and its feasibility remain visible separately.

Preparation and probe consumption are derived separately from the first model
`tool_batch_started` after a qualifying failure on that diff. A read never consumes
the probe slot. Probe batches include rejected/cached requests and interrupted
execution. Harness replay has no model batch and does not spend this credit.
Repeated replay, new action IDs and restart cannot renew it. A new candidate
requires its own comparable failure. Current failure
continues to block finish; offering diagnosis never grants verification credit.

The public action horizon reports the candidate/failure IDs, spent action, offered
diagnostic tools and whether minimum reserves are used. This is an opportunity,
not a command to probe or evidence that useful diagnosis/repair will occur.

The narrower [call-path diagnosis](repair-path.md) activates when a current
implementation branch was measured as unobserved while the same original failure
persists. It reserves the diagnostic in minimum completion, then separately
protects preparation and one malformed-request correction. Here only a durable
execution start consumes the single actual attempt. Optional selected-test
comparisons reserve two physical child executions plus completion capacity.

A diagnosed implementation may instead revise source with a small prediction or
add a selected test. Test addition cannot use the source-edit successor discount:
it reserves the edit, its automatic original replay/recheck, one paired-test model
call and two child executions, then the still-needed source edit, original replay,
required checks and finish. It is offered only with at least two accepted-edit
slots left. All normal edit, call, action, monetary and output caps remain fixed.
The pending comparison contributes one model call and two tool actions, plus any
not-yet-run original replay; a still-pending diagnosis remains in the forecast.
Only this one diagnosed comparison may use minimum reserves. A successful fresh
original observation remains authoritative; a test-only PASS never supplies it.
The unused protocol correction reserve is not released by this change.

## Seeded diagnostic operator

The separate `diagnostics/exception_frame_repair.py` operator has an opt-in
`source-ready-opportunity-v1` profile. Its ordinary source-ready and information-pair
profiles retain their existing requests. This diagnostic is not the ordinary runner.

With a probe unused, optional inspections must leave two model responses and two
tool actions for probe then edit/stop; after the probe they must leave one. Direct
edit or stop remains available. A correction contributes its current response
without spending another normal slot. The request's allowed tools, maximum read
batch and response validator share the same immutable opportunity calculation.

Cost admission reserves each offered successful normal successor at 60K uncached
input plus 40K output, in addition to the unused 25K protocol correction. A correction
releases only its own reservation and retains successor funding. If an inspection
cannot fit, the operator removes reads and recounts the new request; if necessary
it then removes the optional probe and recounts the edit/stop request. At most two
such reductions occur per decision, without generation, renewed credit or retries
after uncertain counting. Current normal output retains exact-count admission;
correction output must fit in full. Count/dispatch identities record each reduction.
The prepared first-request hash binds the initial counted request; a cost-narrowed
first generation has its own recorded request hash and artifact.

No quota, source evidence, host verification or provider setting is increased.
Time limits, input limits, invalid responses, tool failure and repair correctness
remain outside this successful-path opportunity guarantee. Fresh process restart
cannot continue a collection: the operator requires a new result root and exact
authorization; its diagnostic collection is not resumable.

## Focused local verification

[Helper program correction](helper-correction.md) reserves one model/probe action
for the same question after a confirmed pre-dispatch source error before the first
mutation. Only that corrected helper or stop is offered. It uses minimum successor
funding without increasing caps or borrowing the protocol correction allowance.
Returned diagnostics do not establish original-call or task correctness.

[Observation correction](observation-judgment.md) adds one model/probe action before
repair and one future corrected-case replay. It uses minimum successor funding,
separate from the protocol correction allowance; unresolved or unfunded conflicts
return verification incomplete instead of releasing into source exploration.

Run `uv run --locked pytest @tests/recovery-budget.txt --basetemp C:/pt/<unique>`.
The selection uses pure path enumeration, exact boundary checks, local invocation
fixtures and stubbed provider dispatch/recovery. It performs no paid generation
or real container execution. Run quick separately for integration and isolated
mock evaluation; do not repeat the mock smoke outside quick.
