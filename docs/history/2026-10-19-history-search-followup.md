# History retrieval follow-up and smaller routine validation

2026-10-19. Local-only follow-up to the immutable [first search experiment](2026-10-19-run-history-search.md).

## Problem and frozen comparison

The user requested simpler testing and questioned the two-hit bound, result size
and BM25-only ranking. In the previous replay, the known caller packet was absent
from 28 B inputs: one complete recovery, four selected but omitted bodies, and 23
outside the first two. Already visible records occupied 59/246 result slots. These
are recurring retrieval/delivery obstacles, not proof that all questions need that
packet or that acquiring it repairs the task.

The proposed change separates search candidates from the two handoff references. Search
offers eight candidates within 48,000 canonical JSON characters. Matching string
fields are searched in overlapping 1,200-character passages. Two ranks are fused:
IDF-weighted query coverage and character-trigram cosine similarity. Character
similarity requires lexical support. A .5 score multiplier lowers the priority of
records already present in the latest input. No embedding, model reranker, synonym
table, task name or answer-derived keyword is used. Semantic paraphrases and
incorrectly framed queries remain limitations.

Complete bodies stay exact. When a body cannot fit, a labelled exact excerpt gives
its JSON pointer and character range. ID lookup obtains the record separately;
oversized records expose ordered canonical JSON pages and explicit next offsets.
An excerpt/page is never a complete observation or current verification. Each page
costs an ordinary action and model opportunity. Default search remains off.

Before seeing new retrieval results, fix these variants over the same 123 saved
post-checkpoint requests from all 12 closed A/B branches:

1. Reproduce the original two-hit/24k BM25 results from commit d224e1e.
2. Change only that implementation's bounds to eight hits/48k (no previews).
3. Use the new passage ranking/previews with current-input demotion disabled.
4. Use the final implementation with current-input demotion.

Reuse the original question-else-plan-else-issue query, first 800 characters. No
per-case query changes, result-dependent tuning or hidden evaluation material.
The known packet identity is diagnostic-only. Report acquisition, candidate
presence, complete first-response delivery and potential ID-fetch separately.
Potential ID-fetch is an oracle-guided capability bound, not a model choice.
Report lost complete records as well as gains; target recall is not general
relevance. Variants 2 and 3 also differ in preview packaging, so they do not isolate
ranking from its rendering cost.

Keep result-or-size-v1, two handoff references, 24k selected sources, 60k input
tokens, 1MiB requests, 262144-byte opaque items, 40 calls, 100 actions, four edits,
1800 seconds and original monetary admission limits. The user-requested search
response expansion is separate from these limits. Project known-content packing,
displaced evidence and input cost using the saved local tokenizer and +/-128-token
sensitivity. Do not assume new model reasoning, query choices or continuations.
Original sources must rehash unchanged; stop on mismatch or boundary failure.

No paid calls, provider counting, new native evaluation, model uptake or repair
measurement. Keep search opt-in unless future evidence supports adoption. This is
an exposed development comparison, not an independent quality test. Preserve
negative results without tuning the same replay again.

## Validation policy

`tests/quick.txt` explicitly selects the routine core checks, including isolated
mock smoke. Add tests for other changed owners. Keep the full suite intact and
available for broad integration or explicit full-regression work. This reduces
routine execution, not assertions, deadlines or the meaning of full-suite PASS.
No all-suite run is planned for this change. The previous four full-suite timing
failures remain historical failures.

## Results

The frozen comparison completed. Among the 28 missing-packet opportunities,
baseline recovered one full packet, bounds-only 14, passage ranking four, and
passage ranking with current-input demotion five. The new ranker was rejected;
it is preserved at `C:/pt/history20/passage-prototype.py` and in the external
append-only evidence store. No query/weight tuning follows this negative result.

Select the original BM25 ranking with eight candidates, 48k output, exact excerpts
and paged ID reads. BM25's semantic limitations remain; these results do not justify
replacing it with the tested lexical alternative. Final verification reruns only
this selected implementation with the same fixed queries, checking the rendering
cost of previews and recording newly displaced input evidence. It does not rerun
the rejected alternatives or add model execution.

The first comparison stopped on a visibility invariant before producing results:
the same action ID can reappear as a reduced handoff view. Only an exact body match
may label its full original record currently visible. The corrected regression
preserves the full original and labels the reduced view accurately. The interrupted
record remains at `C:/pt/history20/replay/`; completed comparison is `replay-v2/`.

The first selected replay (`selected/`) returned 25 target candidates but only
eight complete bodies. Reserving previews ahead of complete bodies accounted for
the decrease from the bounds-only 14. Correct this packaging priority: reserve
candidate metadata, admit complete bodies in rank order, then add exact previews
only in remaining space. A synthetic regression with two fitting high-ranked
bodies and six oversized candidates requires both complete bodies to survive.
Ranks, queries and numeric limits stay unchanged. Retain the first selected replay
and verify the corrected renderer separately; this is not rank/weight tuning.

Final selected replay is `C:/pt/history20/selected-v2/result.json`. All 123 original
inputs reconstruct exactly, all selected top-eight IDs match bounds-only BM25,
and 891 source files rehash unchanged. Counts below are repeated decision
opportunities in six B trajectories, not independent tasks or repair trials.

| Variant | Missing target in candidates / 28 | Complete first-response target / 28 | Extra size handoffs / 123 |
| --- | ---: | ---: | ---: |
| Original two hits / 24k | 5 | 1 | 0 |
| Bounds only, eight hits / 48k, no previews | 25 | 14 | 16 |
| Rejected passage rank and previews | 17 | 4 | 18 |
| Rejected passage rank with visible demotion | 18 | 5 | 19 |
| Selected BM25, eight hits / 48k, body-first previews and ID pages | 25 | 11 | 17 |

The selected result has 706 complete bodies, 171 excerpts and 107 metadata-only
candidates across 984 slots. All 218 originally returned complete bodies remain
complete; 488 additional complete record exposures appear. Extra candidate metadata
and rendering still cost space: three targets that fit the bare bounds-only output
do not fit the selected first response. ID fetch/page access remains available;
choosing it is an untested model action, not counted as recovery here.

## Packing tradeoff and decision

The larger response is not free retention. Relative to original search packing,
17 opportunities additionally cross the unchanged size boundary; all three local
token-sensitivity scenarios agree. Forty-one already-due result handoffs remain.
The additional omissions are 5,122 source-line exposures (2,851 unique within each
branch), 113 tool-output exposures (47 reads, 66 searches), and four caller-packet
observation exposures. These are structural omissions, not 5,122 independently
judged necessary lines. One of those four caller packets returns inside a complete
search result. The other three are newly unavailable at B4/407, B6/393 and B6/406.

Counting both original input and delivered search results, exact caller packet
availability after packing rises from 21 to 32 of B's 53 opportunities: 14 gains
and three losses. Four previously visible packets are unavailable after selected
packing in total; B2/394 was already unavailable after baseline search packing.
The three new losses are material counterevidence to treating larger output as
uniformly better. The known packet is only one evidence target; relevance of all
other gained/lost records has not been independently labelled.

Final input estimates are 35,705–59,872 tokens (median 45,955), versus the previous
median 37,760. The unrolled search addition has median 15,928 tokens. At the same
historical uncached input rate of USD 0.75/million, the whole extra input's median
is about USD 0.0345, excluding new output/reasoning/cache effects. Maximum request
is 340,395 bytes and maximum opaque item 78,668 bytes. All 123 known-content inputs
fit under unchanged caps; unknown new model reasoning is not projected. No provider
token counting or paid model calls were made, and normal monetary admission remains.

Keep the original ranker and leave the richer search opt-in. The experiment supports
wider candidate access and exact paged retrieval as implemented capabilities. It
does not establish better relevance, model use, repair success or a reason to raise
the agent's context/run budgets. A genuinely semantic retriever remains untested;
the tested lexical replacement does not justify replacing BM25.

## Verification and reproducibility

`tests/quick.txt` is an explicit 75-case routine selection. Existing full regression
tests were not deleted or weakened. Changed-boundary tests cover exact previews,
body-first packing, Unicode JSON page reassembly, invalid offsets, eight candidates
versus two handoff references, public-only provenance, recovery/idempotency and
isolated mock evaluation. Final command/results are sealed in
`C:/pt/history20/head-validation-verified.xml` and the external hash-chained work journal.
Ruff covers runtime/tests and both replay diagnostics. Full suite, paid generation,
model-chosen retrieval, evidence uptake and repair grading are NOT_RUN.

Comparison: `diagnostics.history_search_followup` with original manifest,
`C:/pt/history20/baseline.py`, `C:/pt/history20/passage-prototype.py` as
`--candidate-source`, and the immutable original replay. The rejected prototype is
also saved as a content-addressed artifact. The selected replay uses
`diagnostics.history_search_replay` and `--protocol
C:/pt/history20/selected-v2-protocol.md`, the original manifest/target identity,
`--after-sequence 341`, and the existing local tokenizer/cache. Network connections
are blocked during both diagnostics. Their manifests bind source, protocol and
runtime hashes. `analysis.json`, `analysis-supplement.json` and
`paired-availability.json` record exact displacements and paired availability;
`C:/pt/history20/analyze.py` preserves the audit logic.

- Final selected result: `sha256:e873750ceb88e1e7e98be2ebf6e43b1bd34a7483229369850c9bd1e24849d429`.
- Four-way comparison: `sha256:330207606878751dbdd1d1a0791f8f23c9001486950735a43d3530eee1a86c81`.
