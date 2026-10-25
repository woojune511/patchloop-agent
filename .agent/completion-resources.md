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

Omission preserves old request/envelope serialization and the exact coupled cost
contract. An explicit value is bound into the cost contract, model identity and
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
case can spend one model diagnostic (`read_file`, `search_files` or `run_probe`)
using the minimum successful completion reserve. Baseline acquisition, a helper,
old-diff failure or unknown/incomparable observation does not grant this credit.
The actual minimum repair, fresh checks, original replays and finish must still
fit the remaining model calls, tool actions and selected cost-admission policy.
No cap or mutation capacity is increased. A diagnostic probe reserves one possible additional case
replay: a new binding can add work after the next edit.

Only the one exceptional diagnostic uses the minimum path; normal protected
admission remains available when it already fits. An exceptional inspection has
parallelism one and a last-opportunity warning. Spending speculative recovery
means subsequent rejection/check/reproduction failure recovery is not guaranteed.
The full protected forecast and its feasibility remain visible separately.

Consumption is derived from the first model `tool_batch_started` containing a
diagnostic after a qualifying failure on that diff. This includes rejected or
cached requests and a crash before execution. Harness replay has no model batch
and does not spend the credit. Repeated replay, new action IDs and restart cannot
renew it. A new candidate requires its own comparable failure. Current failure
continues to block finish; offering diagnosis never grants verification credit.

The public action horizon reports the candidate/failure IDs, spent action, offered
diagnostic tools and whether minimum reserves are used. This is an opportunity,
not a command to probe or evidence that useful diagnosis/repair will occur.

## Focused local verification

Run `uv run --locked pytest @tests/recovery-budget.txt --basetemp C:/pt/<unique>`.
The selection uses pure path enumeration, exact boundary checks, local invocation
fixtures and stubbed provider dispatch/recovery. It performs no paid generation
or real container execution. Run quick separately for integration and isolated
mock evaluation; do not repeat the mock smoke outside quick.
