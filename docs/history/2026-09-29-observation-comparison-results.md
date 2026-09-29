# Observation comparison: partial execution and collector boundary failures

Date: 2026-09-29. Every run is official=false. Allocation closed; no automatic retry,
resume, replacement rows or unspent-budget carryover.

## Problem, frozen design and authorization

Does retaining unsuccessful public observations lead to supported interpretation
and discriminating action? The [preparation](2026-09-29-observation-comparison-preparation.md)
fixed three checkpoints, A/B exposure, the first-three-batch public rubric and a
separate terminal acceptance/safety assessment. A hides only the structured
observation catalog; B preserves it. Both retain the original public outcomes.

The user's continuation instruction accepted the proposed six-condition execution:
N1A, N1B, P1B, P1A, P2A, P2B; GPT-5.4-2026-03-05, xhigh, desired 25,000 output
tokens, repository `.env`, USD 3 per condition and USD 18 invocation-wide. Original
remaining action/edit/time limits stayed spent. Parent P1/P2 model settings differ
from the executing baseline, as disclosed in preparation.

Executing HEAD: `81ce9bf`. Frozen manifest:
`C:/pt/analyses/observation-comparison-preparation-20260929-v1/plan-v2/manifest.json`,
hash `sha256:a34406b480fa600b165989146b53bcf0909491fc37114aa4e9c9909d0be544b1`.
Run root: `C:/pt/observation-comparison-20260929-v1`.
Review/audit root: `C:/pt/analyses/observation-comparison-results-20260929-v1`.
Source journals, rubric, runtime and diagnostic identities were rechecked unchanged.

## Executed results

| Condition | New responses | New accepted edits | New active seconds | Recorded new USD | Terminal |
| --- | ---: | ---: | ---: | ---: | --- |
| N1A | 6 | 1 | 365.999 | 0.6148955 | EVALUATOR_ERROR |
| N1B | 6 | 2 | 521.928 | 0.7294345 | EVALUATOR_ERROR |
| P1B | 4 | 1 | 516.485 | 0.7409325 | PROVIDER_TIMEOUT_OR_UNKNOWN |
| P1A / P2A / P2B | 0 | 0 | — | — | NOT_RUN |

N1A and N1B both submitted patches with both required public checks passing on
their respective final diff. N1B additionally had an intermediate scope rejection
and a failed lifecycle check before a later repair. Neither final patch received
an acceptance or safety verdict: evaluator receipt validation failed before patch
application or evaluator checks. ERROR is not task FAIL.

P1B made a repair and passed the automatic upstream regression recheck. Execution
stopped before its next model response or submission; this does not establish
that all required checks passed on that current diff. Three remaining rows were
not executed, and the original six-condition comparison is incomplete.

## Primary public review, frozen before unmasking and evaluator inspection

`extract_review.py` produced shuffled public-only sheets, excluding provider
reasoning and evaluator results. `primary-scores-masked.json` and the review JSONL
froze judgments before `arm-key.json` and terminal results were opened. Blinding is
imperfect: the operator knows the cases and execution order, particularly for the
single executed side of P1. Event hashes/action IDs remain in the sheets.

| Condition | Retention | Interpretation | Action | Primary endpoint |
| --- | ---: | --- | ---: | --- |
| N1A | 0 | absent | 0 | not met |
| N1B | 0 | absent | 0 | not met |
| P1B | 2 | supported | 1 | not met |
| Other three | — | NOT_RUN | — | not scored |

The fixed N1 target is the probe's `wrapped_name` setup mismatch, not the separate
genuine lifecycle-check failure. N1A inspected the repair path (sequences 114/128/144);
N1B inspected and attempted repairs (114/129/143). Neither interpreted the target
probe mismatch in the first three batches. These scores do not mean the agent did
no useful task work or that its repair was unjustified. Primary closure remains
unasserted; unnecessary change is unknown, not inferred from editing alone.

P1B explicitly said the probe used the wrong API and left helper behavior unresolved
(416). The precise public traceback and script identify `fs.symlink` as the failed
setup operation. It retained the question and read resolver source (435/440/449/454),
but did not verify a corrected probe or establish the requested broken/looping-link
behavior in that window. Its source-backed `absnormpath` observation narrowed a
possible method while leaving `lresolve` behavior unresolved; it is investigation,
not the frozen discriminating-action endpoint. No new probe executed in any row.

Only one A/B pair is complete: wins/losses/ties 0/0/1 on the primary endpoint.
The unpaired P1B observation cannot establish an exposure effect. No adoption,
quality improvement, negative generalization or task-success rate is justified.

## Two execution-system failures, not demonstrated model failures

### Cumulative count balance rejects legitimate recounting

In P1B, input count reached 60,389 tokens (477), triggering the existing segment
transition (478). The replacement input counted 27,705 tokens (481). The collector
had six count attempts and four dispatches at this point, but required
`len(counted) == len(dispatched) + 1`. A legitimate discarded oversized count made
that assertion false before the next SDK dispatch. The runtime had already written
`provider_call_started` (484), so it conservatively recorded UNKNOWN (485).

`reproduce_count_guard.py` replayed the saved request/count/dispatch shape through
the unchanged collector with inert base adapter methods and networking forbidden.
It reproduced `ContractError: dispatch lacks immediate count`, six inert counts,
four inert sends, and no fifth base-adapter send. This was a local pre-SDK rejection,
not evidence of an HTTP timeout, unavailable model, or incompatible continuation.

The raw result keeps `billing_known=false` and `new_cost_nanos=null`. The separate
`results-audit.json` reconciles all 16 actual generation-dispatch markers with 16
recorded responses and usage entries, totaling USD 2.0852625. The unmatched attempt
never reached the SDK boundary. This is a log/code accounting audit, not an external
invoice check; original UNKNOWN and stop records remain immutable. No provider call
was made during review, reproduction or reconciliation.

### Historical receipts are incorrectly bound to the current probe profile

Both N1 submissions included two inherited probe receipts with historical profile
`sha256:df3a7c7097f2c964d74f53c7d0b2c2b1a6d5c6e0d40f77c3d1ed678e650e01`.
Their current manifests used
`sha256:fb4b96c930e23c2b9430939783022cfb60d07b332f6d83131eef2fb137fa98d8`.
The image digest matched. Each evaluator provenance reports both receipts as
`image, profile or action diff disagrees`, zero completed checks and no applied patch.
The current-runtime fork preserved history correctly for context, but submission
packaging treated historical executions as current-profile execution evidence.
Read-only environment admission and synthetic same-profile fixtures missed this
cross-profile provenance boundary. The evaluator correctly refused the mismatch.

## Next correction and validation boundary

Fix the collector to bind a dispatch to its latest successful, unconsumed count,
allowing discarded counts during context transitions while retaining payload equality
and zero retry rules. Distinguish local pre-dispatch rejection from uncertain remote
execution in accounting evidence.

Give inherited execution receipts explicit historical lineage when constructing a
new-runtime submission. Keep them available for context/audit, but do not present
them as executions under the new profile. Do not rewrite old receipts or weaken
the evaluator's equality checks. Until that boundary is supported, detect incompatible
lineage before paid execution.

These corrections are not implemented in this execution record. Validate the two
failure paths provider-free, including mixed-profile submission validation, before
preparing any replacement paid manifest. The original allocation remains closed.

Validation in this follow-up: provider-free count-guard reproduction passed with
networking forbidden; all five documentation layout/link checks passed. No production
or collector code was changed, and no acceptance evaluation was rerun.
