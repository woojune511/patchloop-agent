# Expectation-review offline pair

Date: 2026-09-28. `official=false`; model execution NOT_RUN.
Follows [expected-value audit](2026-09-28-expected-value-provenance.md).

## Frozen boundary

The selected turn is `turn_a35a06fed94a4e8ab61834c422973c69` in
`C:/pt/adviceofflive0928a/A1`, run `run_dev_33068b6e257f423a`. It follows the second
agent probe and precedes the guard-removal decision. The source prefix ends at event
215, before count 216 and generation 219. The later mutation, benchmark result and
operator counterexamples are excluded from model input.

Control exactly equals the fifth actual dispatch from that run. The current patch
is still `fdd4fa640b555cc3ef43317ec9b4b3fa2a694902f11d571f43fb48dd2a318745`.
Both arms retain local completion-advice removal and all other state. Treatment
adds only one current-state field, `expectation_review`, with this fixed text:

> Before changing code to match a disputed expected value, distinguish an independent
> public specification or derivation from assumptions shared with the implementation.
> Rejecting one alternative does not validate the remaining expectation. Check whether
> an independent public requirement challenges that expectation on the same failing
> input. Use the available evidence to decide whether to revise the expectation,
> the implementation, or neither; keep unresolved conflicts explicit.

The cue contains no task name, formula, inequality, witness or numerical answer.
It is one review intervention with several related clauses, not an experiment that
separately estimates each clause's contribution. The development comparison retains
the failing task's existing public requirements; it does not import private evidence.

## Artifact and verification

- Packet: `C:/pt/analyses/expectation-review-checkpoint-20260928-v1/packet.json`.
- SHA-256: `caef960bb51daa26038a94bcdd04aa16a7117e61399f2c07507c88ea41fde6eb`.
- Control request: `7ba8d6c96f4824129752643d493fe1560bcbe7f0e10f07caa7109cc2579cf7a6`.
- Treatment request: `cc74da6a688ad3f18e848d7a57f1a5c376c6d84b595ce9c65dcbfe2f7f440c48`.
- `receipt.json` in that root confirms exact historical-control equality and that
  deleting the single added field reconstructs the complete control request.
- Hash-chained journals: `run_dev_expectationpreparation` and
  `run_dev_expectationpairaudit`; artifacts bind the pair and verification receipt.

The loader verifies journal/envelope/task identity, runtime, the post-probe boundary,
candidate context and recorded delivery. Validation reconstructs both inputs from
source. Unit checks protect unchanged state/tools and reject duplicate review or a
noncurrent record. Ruff and focused/document tests accompany this change.

Projection plus document checks passed (7 tests), as did Ruff. Ordinary mock smoke
`run_dev_10bd98fab22843a0` reached isolated EVALUATOR_PASS, safety NOT_RUN and zero
cost under `C:/pt/runs/expectation-review-mock-20260928-v1`. It does not exercise a
review continuation hook. No full repository suite was run for this offline module.

No model counts, provider calls, new task checks or Docker execution were needed
to prepare the pair. Its historical remaining budget ($2.3368545, 28 calls, 79 actions,
3 edits, 918 active seconds) is frozen context, not a reopened allocation. All prior
paid allocations stay closed. Runtime/defaults are unchanged.

## Next step and limitations

Implement a bounded offline continuation for this later checkpoint, verifying the
complete inherited source/probe/plan state and canonical treatment delivery before
counting. Keep a matched control and distinguish scripted plumbing from autonomous
behavior. This pair itself has no collector integration or paid authorization.
Future outcomes should examine expectation revision, independent properties on the
same input, final correctness and revalidation, not just probe counts or submission.
No general effect or default adoption follows from this preparation.

Contract: [expectation-review checkpoint](../../.agent/expectation-review-checkpoint.md).
