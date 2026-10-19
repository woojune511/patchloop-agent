# Local semantic history retrieval comparison

2026-10-19. Closed, provider-free diagnostic. Production BM25 remains unchanged.

## Question and fixed conditions

The user asked to check actual semantic search before moving on. The previous
[passage/character comparison](2026-10-19-history-search-followup.md) was lexical,
not pretrained semantic retrieval. Its negative result could not answer this question.
Losing the original caller conditions is a recurring obstacle in the exposed Astroid
logs; retrieving more records alone does not demonstrate better repair.

Compare current BM25, dense cosine, and equal-weight BM25+dense reciprocal rank
fusion (k=60). The hypothesis was that semantic similarity could recover related
evidence despite vocabulary differences. Alternatives: existing questions may already
encode the wrong investigation direction; public JSON metadata may dominate similarity;
or correct candidates may still lose their bodies at the delivery limit.

Reuse all 123 dispatched post-checkpoint inputs from the closed 12-branch panel,
source manifest `C:/pt/ce19ready/packet/manifest.json`, after sequence 341. Query is
unchanged: current question, else plan, else issue, first 800 characters. A never
acquired the supplied caller packet. B acquired it: visible in 25 of 53 saved inputs,
missing in 28. This is one known packet at correlated decisions, not 28 independent
trials or a general relevance benchmark. Not every question independently needs it.

Use [BAAI/bge-base-en-v1.5](https://huggingface.co/BAAI/bge-base-en-v1.5), official
ONNX revision `a5beb1e3e68b9ab74eb54cfd186867f64f240e1a`, CPU float32, CLS pooling,
L2 normalization, and the published retrieval query prefix. Canonical public record
bodies are split into 512-token windows including special tokens, with 64-token
overlap; every overflow window is embedded. Each record takes its maximum window
cosine. This English general retriever is not an exhaustive or code-specific model
comparison. Maximum aggregation can favor long records. No model/weight/query tuning
or second model was run after outcomes.

All arms use the existing renderer: eight candidates, 48,000 canonical JSON
characters, complete bodies before previews, unchanged lexical excerpts and ID pages.
Thus this compares ranking, not semantic excerpt selection. Retrieval scope is only
the same logical run's previously dispatched public records. Reusing identical
vector computations across the diagnostic does not expand any query's candidate set.

Keep result-or-size-v1, two handoff references, 24k retained source, 60k input tokens,
1MiB requests, 262144-byte opaque items, 40 calls, 100 actions, four edits, 1800 seconds
and existing monetary admission. Independent packing excludes unknown new reasoning
and uses the prior +/-128-token sensitivity. It is not an executable continuation.
119 of 123 opportunities had original action/call headroom; four A opportunities did
not. Input-fit projections are not financial or completion-reserve admission.

Freeze protocol, code, dependencies and public model hashes before scoring. Two
generic paraphrase controls passed before the log comparison. Model setup downloaded
public weights only; embedding and replay blocked socket connections. No run data
was uploaded. Provider, provider-counting and evaluator calls: zero; spend: USD 0.

## Results

| Metric | BM25 | Dense | Hybrid |
| --- | ---: | ---: | ---: |
| Missing-packet opportunities | 28 | 28 | 28 |
| Packet among first 8 | 25 | 14 | 21 |
| Packet delivered complete | 11 | 2 | 6 |
| Candidate selected but body incomplete | 14 | 12 | 15 |
| Packet available after packing, all B inputs | 32/53 | 19/53 | 25/53 |
| Packet availability gains/losses vs BM25 | — | 0/13 | 0/7 |
| Complete record exposures, all 123 inputs | 706 | 801 | 721 |
| Newly complete / displaced complete exposures vs BM25 | — | 363/268 | 176/161 |
| Displaced BM25 complete records also absent after packing | — | 252 | 151 |
| Additional size handoffs | 17 | 18 | 18 |
| Final input tokens, median | 45,955 | 45,052 | 45,189 |

There were 41 already-due major-result handoffs in every arm. Lower/central/upper
packing modes agreed; all known-content projections fit existing size limits.
Maximum input tokens were 59,872 / 59,761 / 59,500; response lengths stayed at or
below 48k. Smaller median input and more complete records did not preserve this
caller packet better. Model uptake, decisions, repair correctness and live latency
remain NOT_RUN; none can be inferred from this table.

Dense lost packet availability relative to BM25 at B1/440; B3/377,393,409,423;
B4/421,437; and B5/377,390,405,421,435,451. Hybrid lost B1/440; B3/377,393,423;
and B5/390,405,421. Neither gained availability at another input.

The additional packing loss occurs at A2/420: both alternatives induce one more
size handoff, losing 286 additional source-line exposures and six tool outputs.
No additional supplied observation is lost through packing itself. Ranking and
delivery still remove supplied caller packets that BM25 would have returned.

The 252 dense / 151 hybrid unavailable complete-record exposures cover 32 / 24
distinct records. They include import-resolution source, not just redundant metadata:
`modutils.py:430-500` (50 / 47 exposures), `builder.py:1-220` (14 / 13),
`manager.py:240-280` (13 / 12), and prior probes (64 / 22). These are potential
dependencies and counterexamples; not every exposure is independently necessary.
The alternative gains are mostly other source reads and searches. Full displaced
bodies, gained bodies, questions, ranks and packed inputs are retained for review.

## What the matching windows revealed

The intended exclusion of standalone model notes/plans is not sufficient to make
the current public corpus observation-only. Tool result bodies can echo a model's
`result.output.inspection_intent`, including its basis, plan and evidence goal.
Top-level call annotations were removed by the existing search implementation;
these nested echoed fields were not. The fixed comparison preserved these same
public bodies for every arm. It therefore tests raw public JSON, not an index
restricted to execution evidence. No private material or encrypted reasoning was
indexed, and no post-result filtering experiment was silently substituted.

Of 152 distinct public records across these branches, 16 contain echoed inspection
intent. Among the highest-ranked records, the best dense window overlaps intent in
77/123 dense selections and 73/123 hybrid selections. For comparison, the best dense
window of BM25's selected first record overlaps intent in 64/123. That last count
does not describe BM25's scoring mechanism. Overlap is a diagnostic, not an ablation
proving how much of the aggregate regression those fields caused.

At B1/440, the question says the source fix is in place and asks for a focused probe
and regression test. Dense ranks an earlier search first whose echoed plan repeats
that direction, and another search with no returned source spans second. The original
caller packet moves from BM25 rank 3 (complete) to dense rank 11 (not selected);
hybrid rank 7 is selected but metadata-only. Its matched window is mostly setup-check
metadata/warnings rather than the decisive call. All 21 windows of that packet were
embedded, so this is not silent truncation of its tail.

There is also a legitimate question-target mismatch: B5/405 explicitly asks which
test module covers the fallback behavior. Prioritizing test source can be relevant
to that narrow question even when the original caller packet drops. Consequently,
these results do not establish that every semantic ranking change was wrong or that
semantic search generally fails. They show that this fixed raw-JSON implementation
does not improve retention of the original caller conditions.

## Decision and evidence

Keep BM25 and the existing opt-in/default-off behavior. Do not promote either tested
alternative or begin a paid continuation. The new evidence changes the next useful
question: distinguish model-authored intent from observed execution/source content
in the ranking representation, while preserving the full original record for delivery.
A separate fixed-query ablation would test whether removing echoed intent changes
the result; this run does not establish that intervention's effect. Query framing
and body-packing limits remain separate unresolved factors.

Implementation is diagnostic-only:
`diagnostics/semantic_history_search.py`, `diagnostics/semantic_history_replay.py`.
Production runtime remains
`sha256:77afaab85c6f847956a6856e4706749ffee93e93c0ea69401566075c076098b3`,
matching baseline commit `43c54308a6201ca6f42efffae040b20d7f2a81f7`.

Evidence root: `C:/pt/semantic20/`. Frozen protocol is `protocol.md`; public model
download manifest is `model/download.json`; comparison is `replay/result.json`;
paired loss audit is `analysis.json`; echoed-intent audit is `intent-audit.json`.
The append-only hash-chained journal is `replay/runs/run_dev_semantichistory.jsonl`.
1,017 bound source/model/helper/prior-packing files rehashed unchanged; original
baseline retrieval reproduced exactly for all 123 requests. Public model file size
is 435,811,539 bytes. The replay took 294.49 seconds, including 241.12 seconds of
CPU embedding work for 1,011 unique windows; vector scoring took 0.16 seconds.
Downloads, full online indexing and an actual agent's search latency are not included.
Download/setup duration was not separately instrumented. Dependency versions were
frozen, but wheel bytes were not separately hashed; model and diagnostic source bytes were.
External dependencies: onnxruntime 1.31.0, tokenizers 0.23.3, numpy 2.5.4; repo runtime
dependencies and lockfile were not changed.

Hashes:

- Protocol: `sha256:1dfa044731257a50dee7acffe3696f4db90e9ad7318841434fc20fa5eb7b4a07`.
- Comparison: `sha256:f53cb705c33a66403dac74f08e36719e3a9ca27e6536d97d293e5728ea7799ea`.
- Paired audit: `sha256:4dc268e2f09176ad5ad22fbae0f8f9ee4f1bc84260daea12b25692e166faa8d7`.
- Intent audit: `sha256:9b0604f834f5d7db6ca0431451e8299b979048853f39c3614ad9a1645dc1781a`.

Three focused tests cover run-local candidate selection, overflow/tail rejection,
and bounded complete-body delivery without requiring model packages. The concise
quick suite passed 78 tests in 38.59 seconds (`C:/pt/semantic20/quick.xml` and
`quick.log`), including search round-trip mock smoke reaching isolated evaluation.
Ruff and documentation checks passed. No full-suite run; earlier full-suite failures
are not cleared by this selection. The pre-existing user edit to AGENTS.md is preserved.
