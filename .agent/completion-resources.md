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

## Ordinary recovery cost and time admission

`completion-recovery-v1` constructs ordinary completion paths from shared steps.
Each step states its model response, real tool action, output allowance and
execution time. Admission derives all resource dimensions from these paths.
A required repair retains
the full ordinary output ceiling; preparation/check/finish retain min(8,192,
ordinary ceiling). Correction retains its independent nonrenewable allowance.
The 128-output monetary unit is only an initial slot-count upper bound, not the
final reserve or a promised useful response. Other cost policies remain unchanged.

Required completion retains current diagnosis and unused diagnostic request
correction, a still-missing mutation anchor, repair, original replays, required
checks and finish. Reading a caller or related test does not establish an anchor.
Automatic replay/check steps retain actions and time while consuming no model
response. A rejected diagnostic request retains a response/action without target
execution time. The protocol correction remains a separate run-wide reserve.

When capacity permits, alternative paths protect one later original or public-check
failure and revision. Original failure may require another path diagnosis and its
request correction; public-check failure does not acquire those unrelated steps.
These alternatives are not concatenated as if all failures necessarily occur.
An original-only failure cannot borrow automatic registered-check savings.
Known-original-failure exploration, as well as required preparation/repair/check,
may release speculative future recovery when it does not fit, while preserving
current completion. Per-action `completion_routes`, `released_reason` and
`failure_recovery_reserved` report the selected guarantee. Releasing protection
does not grant another revision if a later failure exceeds remaining capacity.
The older multiple-failure physical forecast is advisory for these ordinary paths.
No caps, retries or correctness credit are added.

Acquisition, first observation, general probes that can add a case, observation/helper
correction and paired-test/test addition retain a labeled conservative adapter. They are not claimed
to use the ordinary step model. Other cost policies remain unchanged.

Before counting or generation, reserve registered check timeouts plus five seconds
per execution, probe timeout/cleanup, and 30 seconds per successor response.
Selected comparisons reserve both executions. Test addition also retains its
comparison and both mutations' original replays. Count and generation share one
earlier deadline, so counting cannot renew generation time. A protocol correction
requires 30 seconds after these reservations. Time/cost rejection happens before
dispatch; uncertain dispatched work still stops rather than being retried.
These are nominal execution allowances, not a worst-case promise about every Git,
filesystem or container setup delay. The separately reserved isolated-evaluation
deadline remains independent.

## Host-bound revision opportunity

The internal `requested_revision_diff_hash` policy argument lets an operator
diagnostic reserve a revision opportunity for its measured current candidate.
It defaults to absent and activates only in `completion-recovery-v1` with a cost
ledger, `ready_to_submit`, remaining edit capacity and an equal current diff hash.
Model notes cannot activate it. Ordinary runs have no new default reserve.
The current public-counterexample diagnostic instead registers its confirmed
failure as a [required check](required-public-checks.md), so the ordinary failed-check
repair path owns completion and its resource reservation. The internal opportunity
adapter remains available for nonmandatory operator requests.

Optional source/history reads, helper probes and selected tests must then leave
one successful revision path: a still-missing source anchor, edit, all original
replays, fresh public checks and finish. The same steps determine response/action
counts, role-based output costs and nominal execution time. Existing adapter
floors remain per-dimension maxima, not added duplicate paths; all monetary
alternatives remain funded. The unused protocol correction reserve is unchanged.

This is budget admission, not a new failure or completion gate. Direct edit,
finish and stop retain their ordinary rules. Changed diffs deactivate this
measured-candidate reserve; rejected/no-op edits retain it. Restoring the same
hash restores the same binding, so this is not a new run-wide consumable credit.
No counters, limits or verification receipts are changed. The guarantee covers
one successful path, not malformed actions, another failed repair or model uptake.

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

`request-annotation-pair-v1` uses that same opportunity policy in two isolated arms,
each at USD 1.20 (invocation cap USD 2.40). Both receive identical full public
evidence and source. A uses current tool annotations; B reuses only the existing
thin wire schema/parser/validator/gateway. The main instructions, operational tool
parameters, mutation intent and host verification stay identical. This is not the
full thin policy or its note lifecycle. Preparation validates the sole schema delta;
the manifest binds the per-arm policies and exact total cap. Wrong-shaped calls
retain their received annotation fields in the bounded correction transcript.

`model-setting-pair-v1` fixes that thin wire representation in both arms and varies
only the model snapshot: A is gpt-5.4-mini-2026-03-17, B is gpt-5.4-2026-03-05, both
xhigh. Initial requests must differ only in `model`. Eight normal responses and one
correction retain 60K input and 40K/25K output, twelve actions, one probe attempt
and one accepted edit. Each arm has the same USD 6.60 ceiling; the invocation cap
is USD 8.60. Uncached maximum-token costs are USD 1.9575 and 6.525, respectively.
The total also preserves the full USD 6.60 initial remaining display for B after
A's maximum cost. Thus price cannot shrink the specified token/action opportunity
within these bounds. Time, invalid requests and repair failure can still stop it.

The diagnostic collector is sequential. On entry to each model phase the shared
ledger switches pricing for future admission and settlement only; accumulated USD
nanos remain unchanged. The manifest binds both snapshot IDs, registered prices,
thin policies and exact caps. This adds no production-model default, new repair
hint, ordinary-runner policy or task-acceptance claim.

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
