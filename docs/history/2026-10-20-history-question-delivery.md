# Optional history retrieval and context selection

Date: 2026-10-20. Implemented and provider-free replayed; official=false.
No provider/counting API/evaluator calls or new spend. Model selection of queries,
use of retrieved evidence and actual repair success remain NOT_RUN.

## Problem and decision

The user challenged treating any displacement of old context as a reason to reject
optional history search. The [previous comparison](2026-10-20-history-evidence-bundles.md)
showed a real tradeoff: its all-native preservation guard rejected a rank-one caller
packet at B1/502. Its short lexical excerpt also omitted a relevant function branch.
Preserving all existing evidence is not the same as preserving what the question needs.
These recurring caller-condition losses matter because a changed calling convention
can make an apparently successful repair irrelevant to the original failure.

The working hypothesis is that execution-oriented ranking and coherent evidence units
can make an optional recovery tool useful without requiring zero context displacement.
Alternatives remain: the right record can be absent from the candidates, the selected
source function can be wrong, and the model may misuse correct evidence. Better delivery
alone cannot rule out any of these. The investigation tests delivery and capacity,
not whether an LLM will choose the tool or repair a task successfully.

Keep the new implementation on the existing opt-in `public-v1` path; default remains
off. Mixed coverage is recorded rather than made an automatic implementation veto.
This changes the optional tool and question-citation contract; search is still absent
unless enabled. It does not renew any paid-run authorization.
Do not increase the runtime context limit yet: the capacity result below supports a
bounded follow-up design, not an unmeasured adaptive policy or increased money cap.

## Implementation and fixed limits

- `history_evidence.py` ranks original execution data using the existing BM25 math.
  Owned plans, hypotheses, probe questions and note/plan receipts do not supply ranking
  support. Supplied observations and domain/source text are not recursively stripped.
  Record IDs continue to hash original bodies. The raw `PublicHistory` class remains
  available for historical diagnostics; the gateway uses `EvidenceHistory`.
- Eight candidate cards precede ranked evidence units. Probe/check programs, arguments,
  captured setup/environment/results and truncation/error flags remain together.
  Source delivery chooses an entire observed Python function, with explicit query
  identifiers ahead of incidental body matches; otherwise a whole observed span.
  An observed function requires a parseable fragment and an observed end boundary.
  These units remain fragments of the original record, with exact pointers/offsets.
  No arbitrary 1,200-character cut or spare-space expansion fills the response.
- A unit that cannot fit is metadata-only, explicitly incomplete; the model can request
  its original ID using the existing exact JSON paging. Every extra page spends an
  ordinary action and model opportunity. There is no output-only probe fallback.
- The current question may cite a prior `search_history` action as primary or
  countercheck through the existing tool-result reference. Its original call/result
  can then survive the next normal handoff, within the existing two references.
  A search citation is labelled historical even when the retrieval occurred at the
  current diff. Its role remains the model's interpretation, not verified relevance.
  No new reference kind or automatic semantic correctness gate was introduced.
- The all-native preservation veto was not promoted from the diagnostic. Runtime
  native continuation integrity remains unchanged: previously dispatched native items
  are not rewritten or selectively deleted within a segment. Ordinary handoff selection
  retains the current question's declared references; old search results do not acquire
  edit-anchor or current-verification credit.

Result-or-size-v1, two references, eight candidates/48,000 result characters, 24,000
retained source characters, 60,000 input tokens, 1MiB request and 262,144-byte opaque
item limits remain. So do 40 model calls, 100 actions, four edits, 1,800 seconds and
original monetary admission. Optional search does not bypass completion headroom.

## Local comparison

Baseline commit: `6e99a930428f84d2262073cc96fd5b8839320c6f`.
Final runtime hash:
`sha256:367c62d1a0da81793dbfabbd4aa6c46c9c236baabcc363b9cf6b444cc0980bce`.

Frozen protocol and append-only evidence: `C:/pt/question23/`. The final comparison is
`verified-replay/result.json`; earlier replay directories remain preliminary. Final
schema/contract descriptions and repository LF bytes were verified before this run.
No selector, rank weights or limits changed after the first results.

Use the same 123 saved dispatched Astroid-1333 inputs, saved questions and original
public corpus from the 12 A/B continuations after sequence 341. A never acquired the
target caller packet; B contains 53 inputs, 25 originally visible and 28 missing.
Only 119 inputs have ordinary search headroom. The other four remain packing-only
counterfactuals, not admitted extra actions. Each input is independent; this is not
a reconstructed 12-run augmented trajectory.

The whole-first control is the separated-index BM25 arm from
[index separation](2026-10-19-history-index-separation.md), not the former raw runtime
BM25. The guard control is the subsequent bundle experiment. Their saved input
artifacts are hash-validated. Fixed-rank delivery reuses the first control's candidates;
runtime delivery also removes note/plan receipts from ranking, changing candidate
order/set at 119/123 opportunities. Thus the runtime result is not a renderer-only
effect. No new semantic embedding was computed.

| Measure, repeated saved input exposures | Whole-first | Prior guard | Fixed rank/new units | Runtime/new units |
| --- | ---: | ---: | ---: | ---: |
| Exact caller packet returned at 28 missing inputs | 25 | 24 | 25 | 25 |
| Exact caller packet available after packing, B/53 | 46 | 49 | 47 | 48 |
| Size handoffs | 19 | 0 | 15 | 14 |
| Required result handoffs | 41 | 41 | 41 | 41 |
| Summed known input-token estimates | 5,821,910 | 6,070,840 | 5,633,769 | 5,642,774 |
| Summed result characters | 5,813,915 | 5,378,424 | 4,995,591 | 4,956,916 |

At runtime selection versus whole-first: execution-unit exposures **+20/-0**,
exact source-line exposures **+2,547/-8,743**. Restricted to the 119 admitted search
opportunities, the figures are +20/-0 and +2,519/-8,476. Versus the guard: execution
units **+6/-8**, source lines **+2,350/-9,703**. Counts include repeated exposures,
historical file versions and blank lines; a source-line count is not an importance
score. The input totals are independent hypothetical next requests, not billed usage.

Final lower/central/upper estimates fit normal limits; the maximum central admitted
input is 59,638 tokens. A2/434 is sensitive to the +/-128-token local estimation
interval, so central size-boundary counts must not be treated as exact API counts.

## Recovered and displaced evidence

- B1/502 now delivers the rank-one original caller packet rather than rejecting it
  to protect all native context. B4/407 and B6/380 retain their packet gains over
  whole-first. B6/393 and B6/406 lose an originally visible packet relative to the
  guard: it is candidate eight, its 19,227-character body does not fit the search
  result, and the added result causes a size handoff. These are genuine condition
  losses, not just missing receipt metadata.
- B3/455, /469 and /483 do not retrieve the packet because it is outside the eight
  candidates. More context cannot restore something that was neither retained nor
  retrieved. An ID read or a different model-chosen query is possible, but unexecuted.
- The guard-relative eight lost probe exposures form four groups. B3/409 loses a
  namespace success under root plus root/src on sys.path (response cap). This is a
  useful environment-dependent alternative, not the exact public caller. A5/424
  loses a failed setup check with empty stdout (response cap); this is evidence that
  the intended experiment did not run, not evidence for the expected behavior.
- A5/499, /516 and /544 lose the namespace-control success at `src.project` because
  receipt-free ranking moves it outside the candidates. Their current question is
  where to insert a regression test and whether imports suffice; this control is
  secondary to that immediate question but could matter again later.
- B5/435, /451 and /466 lose the original context-file import failure (response cap).
  It constrains a proposed module-name fallback, although its environment differs
  from the exact public failure and does not directly test current directory/source
  behavior. These are meaningful limitations, not harmless losses to hide in a net gain.
- Whole functions fix arbitrary within-function chopping, not function selection.
  At B1/364, `ast_from_file` survives, but builder retrieval still chooses `module_build`
  and omits `file_build` lines 115--151, including its file-open exception branch.
  This is an unresolved relevant source loss. The original remains available by ID;
  whether the model notices and follows that route is NOT_RUN.

The audit preserves each lost/gained source line and original probe body. No task
name, Astroid symbol, target hash, evaluation result or known failure label appears
in runtime selection logic. The known target hash is used only for measurement.

## Context-capacity sensitivity

For the same runtime responses, independently raise only the diagnostic token bound
to 70,000 and 80,000 when central packing required a size handoff at 60,000. Mandatory
result handoffs and result/byte/reference limits remain. This changes no runtime
constant, paid cap, model setting or automatic admission policy.

- 14 size cases avoid that handoff at 70k; 12 of these have ordinary search headroom.
  The highest known-content estimate is 67,371 central / 67,499 upper tokens.
- Exact caller availability becomes **50/53**, restoring B6/393 and B6/406. The three
  candidate misses remain. Source exposures increase by 3,580, with no new source or
  execution-unit losses relative to the same response at 60k. 80k adds no further gain.
- Keeping those histories increases summed input by 306,161 tokens across the 14
  cases, or 253,571 across the 12 eligible ones. At the panel's frozen 2026-10-19
  uncached input price of USD 0.75/million, that is input-only USD 0.22962075 or
  **USD 0.19017825** respectively. These are scenario estimates, not a current price
  quote, billed usage, full-run cost or a renewed spending authorization. Output,
  cache behavior, unknown new reasoning and future decisions are unmeasured.

This supports investigating a 60k ordinary threshold with a separately bounded 70k
allowance when normal projection would lose explicitly requested evidence. It does
not establish the necessity detector: the 14-case sensitivity retained all available
native context, not only evidence a model correctly identified as necessary. A real
policy must bind its upper bound into the run envelope/recovery identity and future
cost reservations, count the actual request, reserve output space, and keep the same
invocation money/action/time limits. Raising input capacity may leave fewer affordable
future calls. None of that policy is enabled by this local sensitivity calculation.

## Validation and remaining question

The final replay verifies 45,575 exact field/excerpt values and 1,062 bound source
files unchanged. No private evaluator data or opaque reasoning is searched or exposed.
New concise tests cover intent/evidence separation, full function branches and partial
span labels, oversize atomic probes plus exact paging, and two-reference search handoff
with historical currency. Existing focus, source-support and recovery tests remain.
Ruff passed; the quick/focused selection passed 128 tests in 35.381 seconds, including
isolated mock EVALUATOR_PASS. Documentation checks passed separately (5 tests).
Final hashes and commit are bound in `C:/pt/question23/closeout.json`. The earlier unrelated four
full-suite failures are not cleared; a full suite and live repair comparison are NOT_RUN.

The next empirical question is whether the model actually searches when needed,
recognizes incomplete results, uses exact-ID expansion within its ordinary budget,
and changes its repair judgment correctly. This implementation makes that question
testable; it does not answer it from offline retrieval metrics.
