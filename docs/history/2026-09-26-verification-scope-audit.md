# Verification scope audit: 2026-09-26

Follow-up interpretation of the closed paired-reference comparison; it does not
rewrite that record. Current priorities are in [current status](../current-status.md).
All evidence is `official=false`. New provider calls, candidate executions, checks,
and evaluations: zero. No runtime, prompt, task, or default changed.

## Question and method

Did completion guidance prematurely end investigation, or had verification already
narrowed? Compare the four runs' public requirements, seeded patches, exact-base
source, first plans, check definitions, observed results, and subsequent decisions.
Verify actual dispatched inputs rather than treating absent annotations as lost memory.
Read only registered upstream check sources at the task's exact base commit; do not
execute them or consult hidden evaluator details. Revisit the earlier final-guidance
ablation before proposing the same intervention again.

## Findings

| Evidence | Observation |
| --- | --- |
| H first plans | No-explicit-endpoint preservation was recognized, but direct calls and a client's omitted endpoint/default substitution were not distinguished. |
| H registered contract | 292 PASS; both HfApi construction sites explicitly supply endpoint. Direct metadata is the no-endpoint branch. The upstream 15-test file contains no HfApi or metadata-access call. |
| H after first PASS | The remaining public question became only whether upstream Xet regressions pass; no new evidence resolved the client-construction distinction. |
| P first plans | The stated insertion condition mirrors the candidate's field-mode/nonempty-field predicate, blurring the public provider-profile requirement. PB explicitly narrows preservation to profiles not using field mode. |
| P registered checks | Contract: 8 PASS including basic preservation cases. Upstream: 18 PASS. Its seven selected message tests have no tool calls and test existing thinking replay, not the new empty tool-call insertion branch. |
| P after first PASS | The model expected those regressions to cover custom-field reuse and profile copies, then submitted after PASS without inspecting their bodies. |

These are public coverage gaps, not identified hidden failing assertions. Static
source analysis exposes distinctions worth checking; no new counterexample result
was produced. The first required check was a useful action. The unsupported step
was treating its result and named regressions as sufficient for broader conditions.

The public task, seed, and supplied reference source survived in all 12 dispatched
inputs; previous plans survived verbatim in all eight subsequent inputs. Reads,
searches, and probes were offered throughout, with no read-path enum restriction.
Registered test bodies were readable but never read. Actual check-navigation metadata
marked coverage `not_assessed` and showed no observed upstream source ranges.

All 12 decisions match guidance and PB call 1 cites it, but initial guidance was
already present when the first plan formed. Narrowing before the final submit cue
therefore does not rule out influence from earlier cues. Model judgment, candidate
anchoring, and verification-scope reasoning remain alternatives.

## Prior evidence and decision

The closed 2026-09-15 submission-guidance diagnostic used mini medium at two pyfakefs
submission checkpoints. Removing only the latest action recommendation left finish
selection at A 4/4 and B 4/4; no selected tools or evaluations ran. Existing plans
and earlier cues remained. This weakens the case for repeating a final-cue-only
intervention, without establishing equivalence for the current model or full loop.

Prioritize the mapping from public applicability conditions to actual verification
inputs. Any next intervention needs a mechanism addressing that judgment; declaration,
probe, or note counts alone are insufficient. Isolate initial guidance only if that
causal uncertainty warrants a comparison; do not automatically launch one or adopt
recommendation removal. This audit establishes no new quality result.

## Evidence and validation

`C:\pt\analyses\verification-narrowing-audit-20260926-v1\result.md` contains the full
analysis. The packet records 25 verified source artifacts, 12 inputs, 12 decisions,
8 existing check results, registered upstream sources, and static scope checks.
Audit scripts passed Ruff. Documentation tests and final preservation hashes are
recorded in its closure manifest. Runtime tests/mock smoke were not rerun because
this change contains documentation and external read-only analysis only.
