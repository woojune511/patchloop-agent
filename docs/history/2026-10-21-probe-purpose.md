# Attach verification purpose to the selected probe

Implemented and locally tested; model uptake and repair improvement are untested.
No paid provider work, input counting, real Docker run or benchmark evaluation was
performed. This follow-up starts at `cbc779d2` and preserves the
[closed declaration diagnosis](2026-10-21-reproduction-nonuse.md) and its six runs.

## Problem and decision

The earlier feature was disclosed in all 132 requests, but all five probes used
null reproduction metadata. Some were helper experiments; A3 also attempted the
original public failure without binding it. Four outputs contained progress or
multiple records; the last failed its assertion before emitting a comparable
result. A nullable declaration and a single-JSON stdout protocol required an
additional choice and conflicted with the instruction to print progress.

This change addresses those two interface obstacles. It does not assume that
every helper should become a reproduction, or that attachment alone corrects
mistaken caller selection and premature completion. Those remain competing
explanations for unsuccessful repairs.

## Change and boundaries

- Each newly advertised `run_probe` selects `purpose.kind=helper` or
  `original_requirement`. Selecting the latter requires the public requirement
  quote, Python entrypoint, input/environment conditions and frozen `expected_json`
  in that same object. Invalid metadata fails before execution. There is no
  additional declaration action or automatically inferred requirement mapping.
- Original-requirement probes call the injected `record_observation(value)` once.
  Stdout/stderr remain progress logs. The host compares the recorded JSON value,
  so printing several progress messages cannot corrupt the predicate input.
  An observed bug should be recorded as a mismatching value rather than asserted
  away before an observation is produced.
- Missing, duplicate, invalid or oversized values cannot compare. A recorded
  value remains visible after a subsequent crash, without comparison credit.
  Timeout, output truncation, setup-check failure, uncertain cleanup and missing
  caller observations still prevent comparison.
- The binding includes the observation channel. Existing action replay preserves
  the exact program, purpose and expectation across edits/restart; same-action
  retries return the stored receipt. Unadvertised legacy declarations retain
  their original wrapper bytes, comparator and recovery identities.
- Authored purpose/input/expectation fields are annotations, excluded from
  observed-evidence ranking. Case evidence can become `SUPPORTED` or `REFUTED`,
  but requirement mapping remains unverified and `repair_success=not_assessed`.
  No new submission gate or mandatory probe was added.

No runtime branch names a benchmark task or symptom. Tests use the existing
generic CSV mock task. Guidance to print/assert the expected observation now
applies specifically to helpers; original-requirement probes use the separate
recording channel.

## Existing-log replay

Evidence: `C:/pt/probe-purpose45/replay-final`, produced by
`diagnostics/probe_purpose_replay.py`. Its executed source is snapshotted there,
and the append-only `run_dev_probepurposereplay` journal binds each output to
verified public-artifact hashes.

- All **132** saved verification-state views rebuild exactly, using the original
  OFF/ON state projection. The five historical probes remain unbound. Original
  input bodies and historical judgments are not rewritten or regraded.
- Projecting only the new probe input and guidance adds **689 canonical public
  wire bytes** in the **129** requests offering probes; the other three change by
  zero bytes. This is a schema-only projection, not a new model trajectory or a
  measurement of token count, cost or future handoffs.
- **10 local transport fixtures** combine the five saved progress-log bodies with
  a fixed stdlib observation, once matched and once mismatched. All distinguish
  the expected comparison and preserve stdout. These execute synthetic stdlib
  fixtures, **not the historical solver programs or original callers**; they
  establish channel separation, not historical repair success.

## Limits and local validation

`C:/pt/probe-purpose45/invariants.json` records unchanged owners for transition,
conversation, two-reference notes, cost/completion budgets, model state, runner
and sandbox. The system prompt remains 8,000 characters and the memory schema
4,000 bytes. Model/tool/edit/time budgets and transition rules are unchanged.
The legacy wrapper is byte-identical, and only `run_probe` changes its schema.

The recording wrapper adds **749 characters** inside the existing 8,000-character
combined source cap. The observation still fits 2,048 UTF-8 bytes, the observer
report 6,000 characters and total output 12,000 bytes. This consumes existing
capacity; it does not expand it. A large program or verbose log can still exceed
the cap and remain unverified.

The final quick run passed **149 tests**, including nine new focused cases and
isolated mock evaluation, in **59.8 seconds**. Focused cases cover invalid public
mapping, log/observation separation, duplicate/invalid/missing values, crash
retention, execution limits, annotation separation, restart/replay/idempotency,
handoff state and the distinction between case support and task acceptance.
The affected compatibility suite passed **183 tests**; documentation checks
passed **5 tests**. These selections overlap the quick suite and are not an
additive distinct-test count. Ruff passed for runtime, tests and diagnostics.
The full repository suite was not rerun. Results and source identities are bound
in the closeout under `C:/pt/probe-purpose45`.

The initial local failures were one missing-observation reason classification
(fixed without granting comparison credit) and stale schema/description snapshot
expectations. Existing strictness, regex validation, resource limits and frozen
historical-arm expectations were retained.

## Remaining question

Does a model now bind a probe when it chooses to verify the original requirement,
and does that evidence change its completion judgment? Local execution cannot
answer that. Helper selection, a mistaken public caller, an incorrect expected
value and substituting suite PASS for caller verification remain possible. A
future authorized comparison must distinguish selection, binding, comparison
use, completion judgment and independent repair acceptance.
