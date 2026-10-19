# Whole history originals under actual input admission

## Problem and decision

The [previous optional search renderer](2026-10-20-history-question-delivery.md)
chose one question-matching function from
each source record before checking available space. This could remove a helper's
exception/dispatch conditions even when the request could carry them. The user
requested original delivery when space permits and a review of transitions and
the two-reference limit. This is an observed projection defect, not evidence of a
model reasoning limit or proof that more history improves repair quality.

The first whole-first implementation still used a fixed 48k response cap. Its
provider-free replay restored source but lost five probe units on 28 exposures.
Every eight-record original set exceeded 48k (50,898–100,711 characters). That did
not implement available-input-space delivery, so it remains a preliminary result,
not the final behavior. No ranking or query tuning followed those results.

Final behavior, still opt-in `--history-search public-v1`:

- Execution-only BM25 and eight candidates are unchanged. Complete original
  records, including exact calls/source/program/setup/results, get first priority.
  Original authored annotations are labelled by JSON pointer and remain excluded
  from ranking. Historical records grant no current source/check credit.
- Keyword originals no longer share an unconditional 48k response cap. Their
  necessary outer character bound equals the existing 1 MiB request-byte ceiling;
  actual serialized request bytes and provider input-token count decide admission.
- Existing result/size handoffs run first. If a fresh seed still exceeds its limit,
  retain the existing optional-reference omission fallback, then reduce the new
  search response to 48k only if it still cannot fit. Try complete records, whole
  execution fields, whole observed spans, then multiple complete observed functions.
  This last fallback is coarse, not a maximum-density token allocation algorithm.
- Only a fresh uncommitted seed receives that reduced view. Its manifest binds
  `history_result_reduced`; recovery reuses it. Canonical action results and previously
  dispatched native outputs remain unchanged. Exact-ID pages remain 48k. Count
  uncertainty stops execution; repacking does not get a free model/tool action.

The 60k input-token, 1 MiB request, 262,144-byte encrypted-item, 24k retained-source,
two-reference, 40-call/100-action/four-edit/1,800-second limits are unchanged.
The runner's counted-input cost admission and future reservation are unchanged.

## Provider-free comparison

Evidence: `C:/pt/fullhistory24/actual-replay/result.json`,
`actual-input-protocol.md`, `actual-review.json`; preliminary `replay/` is preserved.
Compare saved outputs from commit `8c28bfb` against the final renderer with identical
queries, acquired records, rank order and a common current prompt/schema. The
123 saved Astroid-1333 inputs are independent packing counterfactuals; 119 permit
an extra search within the ordinary action budget. No new trajectory, query choice,
reasoning, use of evidence or repair outcome was simulated. Source hashes verified.

| Metric, repeated input exposures | One function | Full originals | Full + size-only sensitivity |
| --- | ---: | ---: | ---: |
| Exact caller available, B's 53 inputs | 48 | 50 | 50 |
| Caller returned when missing, 28 inputs | 25 | 25 | 25 |
| Complete retrieved records, out of 984 | 36 | 954 | 954 |
| Size handoffs, including overflow fallback | 14 | 40 | 58 |
| Result handoffs, including fallbacks | 41 | 41 | 0 |
| Known input token estimates, sum | 5,654,436 | 6,474,290 | 6,531,606 |

Full originals survive without response reduction in 117/123 requests. Six B1
requests exceed 60k even after a fresh seed and optional-body omission, so their
new search results are reduced. All final lower/central/upper packing scenarios
fit existing limits; the largest central request is 59,934 tokens. Upper-bound
estimates trigger two additional size handoffs (B3/364 and A4/380). These are local
calibrated estimates; unknown future search-decision reasoning is excluded. Runtime
admission uses the actual provider count, which was exercised only with a fake provider.

Relative to one-function delivery: source-line exposures +15,765/-3,294 and complete
probe-unit exposures +20/-6. Restricting to the 119 eligible opportunities gives
+15,243/-3,294 source lines and the same +20/-6 probes. These are repeated exposures,
not unique facts, significance estimates or quality scores. B1/364 now carries
`builder.file_build` lines 115–151, including `open_source_file`, OSError translation,
and module-name fallback previously omitted from its retrieved source.

Costs: +819,854 known input tokens across all 123 requests; +776,537 across eligible
119. At the frozen panel's uncached $0.75/million input price, those are $0.61489050
and $0.58240275 input-only scenarios. They exclude caching, outputs, extra counts,
later actions and trajectory changes; they are not an authorized run cost estimate.
New provider calls and spend: **0**. Uptake and repair success: **NOT_RUN**.

## Newly displaced information

Twenty-six additional central size handoffs drop older native context. Loss is
not uniformly unimportant: B1/474 loses previously present `file_build`/OSError
source when its fresh input still overflows; A3/382 loses resolver alternatives
including `get_source_file`; other cases lose surrounding tests/import helpers.
The full line-by-line deltas remain in `actual-replay/result.json`.

The six lost probe exposures are two original units:

- Record `652f4137…`, B1/474,489,502,515,530: default versus `source=True` calls for
  a missing initializer both raise AstroidImportError. It is rank 3 but falls to
  metadata in the 48k fallback. This is relevant contrary evidence against blaming
  the source flag alone; it lacks the exact public caller's explicit module-name
  and import-path setup, so it is not a reproduction of that public call.
- Record `494c34ff…`, B1/544: module-path, file and module-name calls fail under the
  probe's search path. This older cited optional result is omitted for space and
  is outside the eight search candidates. It helps distinguish environment from
  caller behavior, but does not certify the repaired public path.

The caller packet gains occur at B6/393 and B6/406; three remaining B failures to
retain it are B3/455,469,483, where it is outside the eight candidates. No old caller
exposure is lost. Full delivery improves this coverage axis but is not lossless.

## Transition and reference decision

Keep `result-or-size-v1` and two references for now; neither was assumed immutable.
At the same 60k cap, the existing size-only policy avoids 23 next-step handoffs,
adds 57,316 known input tokens, restores 48 source-line exposures, and restores no
additional caller/probe unit or any of the six lost probes. This tests the next
boundary at each saved input, not accumulating a complete size-only trajectory;
its model reasoning effect remains unknown. The observed residual loss is mainly
size pressure, not an early-result boundary.

Reference occupancy is 0/1/2 in 18/17/88 inputs. Among 41 result handoffs it is
0/1/2 in 16/7/18. Existing declarations retain zero or one optional tool body,
never two; source citations share the same slots. Thus the cap is frequently full,
but the logs do not identify a third citation the model would have chosen. Raising
it alone cannot recover an unselected record or resolve an oversized fresh seed.
Its adequacy remains unproven; do not infer that two is optimal.

The next unresolved packing question is whether reducing only the actual excess,
while retaining necessary caller and counterexample units, can avoid the coarse
48k fallback losses. A default policy change or repair-quality claim needs separate
evidence. This optional change satisfies full-before-overflow delivery; it does
not establish better repairs or authorize another paid experiment.

## Validation and boundaries

Focused tests cover whole originals above 48k with spare capacity, exact byte/token
overflow, atomic probe paging, multiple functions, labelled authored fields, native
prefix integrity, canonical action immutability and recovery after a prepared reduced
seed. Quick tests include mock submission through isolated evaluation. Fake-live
fixtures preserve the intentional evaluator-provenance rejection rather than
weakening it. Full-suite historical failures are not reclassified by this validation.
Final test/lint/commit identities are bound in `C:/pt/fullhistory24/closeout.json`.
No hidden evaluation, paid API, network retrieval, model embedding or old evidence
mutation occurred. The user's existing `AGENTS.md` edit is outside this change.
