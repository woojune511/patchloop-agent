# Separating intent from history ranking text

2026-10-19 experiment; 2026-10-20 closeout. Provider-free follow-up to the
[raw semantic comparison](2026-10-19-semantic-history-search.md).

## Problem and fixed intervention

The user requested a separation of plans/hypotheses from observed evidence in search
text, followed by a fixed-query BM25/dense/hybrid comparison and displacement audit.
The prior comparison found public tool results echoing model-authored intent; related
plans could outrank original caller conditions. That overlap did not establish its
causal effect. This experiment changes the indexed fields while holding the questions,
model, scoring algorithms and returned records fixed.

`diagnostics/semantic_history_index.py` separates a public record into an observed
projection and an annotation map indexed by original JSON pointer. It uses schema
ownership, not task keywords or natural-language deletion:

- For registered public tools, move call-level `turn_decision` and `memory_update`.
- For reads/searches, move output-level `inspection_intent` and `inspection_intent_ref`.
- For replacements, move `hypothesis`, `expected_behavior`, `causal_revision` and legacy
  `requirement_ref`/`behavior_cases` in call arguments and the output mutation receipt.
- For probes, move the explanatory `question` from call arguments and output.

Actual programs, replacements/diffs, path/line/query arguments, stdout/stderr, failure
states, source spans, setup checks and supplied observations stay exact. The projector
does not recursively delete similarly named keys in captured values, parse source or
output strings, infer truth, or rewrite queries. Other harness metadata stays present.
Removing a model-authored question from an indexed record is separate from changing
the current search query; all 123 current queries are checked against the saved originals.

The pre-score structure audit covered 152 distinct public records. 137 changed:
16 inspection-intent objects, 90 intent references, 17 mutation-argument groups,
12 mutation-receipt groups and 14 probe-question pairs (overlapping record groups).
Reattaching annotations reconstructed every original body hash exactly. No named
structured plan/hypothesis/question fields remained in the observed projection of
this corpus. This does not mean source/output prose is free of hypotheses or that
every supplied observation is verified. The target caller packet is unchanged.

The exact same projection feeds BM25 and dense inputs; fusion stays equal-weight RRF,
k=60. Original record IDs, bodies, provenance, exact-ID pages, lexical excerpt selection
and whole-body-first rendering are unchanged. Original annotations can therefore still
appear in returned bodies/excerpts. This isolates ranking text, not response rewriting
or the agent's interpretation after delivery.

Use the prior 123 dispatched inputs from all 12 Astroid branches after sequence 341,
with their question/plan/issue queries, first 800 characters. B acquired the known
caller packet and lacks it at 28 of 53 saved inputs; A never acquired it. This is one
known packet at correlated decisions, not independent retrieval trials. The packet
is an analysis label only, and not all current questions necessarily need it.

Keep the same local BGE-base-en-v1.5 ONNX revision, query prefix, float32 CLS/L2,
512-token windows, 64-token overlap, all overflow windows, maximum cosine per record,
CPU threads=4 and batch=8. No second model, post-outcome field/weight tuning, downloads
or paid calls. The generic paraphrase controls are unchanged.

Keep result-or-size-v1, two handoff references, eight candidates/48k response, 24k
retained source, 60k input tokens, 1MiB requests, 262144-byte opaque items, 40 calls,
100 actions, four edits, 1800 seconds and original monetary admission. The same
119/123 action/call-headroom opportunities apply; the other four A projections are
not admitted searches. Independent packing excludes unknown new reasoning and uses
the original +/-128-token sensitivity. No adaptive continuation or repair grade is inferred.

Baseline source: commit `e2de3cd09741f5e13db405c49e97ba87c0fdb940`.
Protocol: `C:/pt/semantic21/protocol.md`, frozen before scores. Raw BM25 reproduces
exactly at every request. Compare each separated arm with its same-method raw arm,
and separately with raw BM25. Record all whole-record gains/losses, post-packing
absence, native source/output displacement and actual sizes; inspect their relevance.

## Recovery results

All values are raw index -> separated index with the same method. A complete packet
means the exact original body, including the actual caller, environment, program and
outputs; a selected ID or short excerpt does not count as restoration.

| Measure | BM25 | Dense | Hybrid |
| --- | ---: | ---: | ---: |
| Packet among eight candidates, 28 missing inputs | 25 -> 25 | 14 -> 18 | 21 -> 28 |
| Complete packet returned, 28 missing inputs | 11 -> 25 | 2 -> 2 | 6 -> 20 |
| Packet available after packing, all 53 B inputs | 32 -> 46 | 19 -> 19 | 25 -> 41 |
| Paired post-packing gains / losses | 15 / 1 | 0 / 0 | 17 / 1 |
| Size handoffs, all 123 inputs | 17 -> 19 | 18 -> 18 | 18 -> 19 |
| Median estimated input tokens | 45,955 -> 46,064 | 45,052 -> 45,308 | 45,189 -> 45,941 |

BM25's 25 returned packets are complete; its other three are below rank eight.
Dense selects the packet 18 times, but 11 deliveries contain only metadata and five
only an excerpt. Hybrid selects it 28 times, with seven excerpts and one metadata-only
delivery. Removing intent improves BM25 and hybrid packet delivery, but does not solve
dense ranking plus body packing. It does not demonstrate better agent judgment.

Relative to raw BM25, separated hybrid gains 12 post-packing packet exposures and
loses three, ending at 41 versus 32. Separated dense gains none and loses 13, ending
at 19. Separated BM25 is the strongest packet-restoration arm in this fixed comparison.
The original caller packet never appears in A's corpus; acquisition was not simulated.

All 123 known-content inputs fit in each lower/central/upper scenario, with identical
packing modes across those scenarios. Maximum central input estimates are 59,669 /
59,577 / 59,846 tokens for BM25/dense/hybrid. Every response remains within 48,000
characters. The 41 already-due major-result handoffs stay the same. Four A searches
lack action/call headroom and are diagnostic-only; all B packet measures and the two
extra BM25 handoffs concern admitted opportunities. Unknown new model reasoning,
chosen queries and subsequent trajectory effects remain unmeasured.

## What the gains displace

Counts below are repeated record exposures, not distinct facts or independent trials.
The comparison is always separated versus the same-method raw arm.

| Measure | BM25 | Dense | Hybrid |
| --- | ---: | ---: | ---: |
| Newly complete records | 137 | 332 | 266 |
| Previously complete records no longer complete in response | 221 | 347 | 339 |
| Those records also absent in full after packing | 193 | 323 | 316 |
| Distinct IDs in that last group | 27 | 29 | 40 |
| Source-bearing exposures with all source lines available elsewhere | 142 | 208 | 215 |
| Source-bearing exposures with some/all exact source lines missing | 33 | 47 | 39 |
| Probe exposures lacking the same complete program and output elsewhere | 16 | 49 | 50 |
| Additional native source line exposures lost to packing | 471 | 0 | 185 |
| Additional native outputs / supplied observations lost | 10 / 1 | 0 / 0 | 4 / 1 |

The content audit checks exact path, file hash, line and text against native context,
complete retrieved source spans and complete lines inside source excerpts. No semantic
paraphrase or model claim substitutes for source. There are no unresolved source
references among the displaced records. Quoted history remains historical evidence;
this audit does not turn it into a current mutation anchor.

For BM25, 193 unavailable whole-record exposures comprise 131 searches, 25 reads,
20 mutations and 17 probes. Of the 175 source-bearing exposures, 142 have their source
fully covered elsewhere; 22 are partially covered and 11 entirely uncovered. Their
1,953 missing exact source-line exposures include older file versions and repeated
lines across decisions, and must not be added to the separate 471 native-loss count.
The one remaining non-probe record is an empty search. Of 17 displaced probe bodies,
one retains an equivalent complete program/output in native context; 16 do not.

Inspecting the current question changes the interpretation of these losses:

- A1/490 and /506 ask for an exact test insertion anchor. 39 of 40 lines of the
  relevant `tests/unittest_modutils.py` read are unavailable at each input. Promoting
  broad caller evidence is not sufficient for this local edit question.
- B1/456 asks whether `source=True` still forces the failing build. The corresponding
  probe's actual `AstroidImportError` is reduced to its explanatory question. A similar
  default-call probe survives elsewhere, so count only the source-flag result as lost.
  These probes also lack the original caller's `modname`/environment conditions;
  they are conditional counterevidence, not proof about the exact Pylint call.
- B3/377, /393 and /409 lose a successful `ast_from_module_name('project')` control
  under an explicitly added `root/src` search path. B5/466 loses both a missing
  initializer/context-file failure and the directory-versus-real-file control. These
  branches constrain conclusions about the current question even though their caller
  conditions differ from the supplied original trace.
- A5/424 through /483 lose the probe's failed `cwd_is_workspace` setup check. The
  program stopped before its two target calls; empty stdout is not a behavioral
  result. Early deliveries retain only the question and later ones only metadata.
  Losing this failure weakens the ability to reject an invalid experiment.
- Some source losses are less material to the question: B3/483 asks where to append a
  builder test, while seven displaced `modutils.py` lines concern an older inspection.
  Conversely, manager source and mutation post-images at B2/B5/B6 are related to
  fallback/source handling. Full per-input lines and version hashes are retained in
  the audit rather than treating every displaced record as equally necessary.

The most direct regression is B6/380. Its question asks which consumer of
`file_info_from_modpath` can turn a namespace/directory into a missing initializer.
The original caller packet is already visible. Raw BM25's same-segment input is
59,872 tokens; the separated response raises that candidate input to 60,186
(60,058--60,314 under sensitivity), so the unchanged size rule must hand off.
The packet is ranked 11, outside eight candidates, and is not restored. The final
42,395-token input loses it, 185 native source lines and four outputs. A2/420 accounts
for the other 286 native lines/six outputs lost in an extra BM25 handoff. These are
real preservation regressions within the reconstruction, not merely record-ID changes.

The unchanged excerpt selector still picks `/call/arguments/question`, `hypothesis`
or `expected_behavior` from several records when full bodies do not fit. Excluding
these fields from ranking has not excluded them from delivery. No excerpt retuning
or extra record-ID reads were added after seeing this result.

## Decision, limits and evidence

The separation is implemented as a reproducible diagnostic option, `--index-mode
observed --raw-replay ...`. Keep the production BM25 implementation and its opt-in,
default-off behavior unchanged. The comparison supports separating intent for
ranking, but does not justify promoting this complete selector: current-question
anchors, counterbranches and a previously visible caller packet can still be lost.
There is no reason from this panel to adopt dense or hybrid over separated BM25.
This is not a general rejection of semantic retrieval; only one embedding model,
one exposed task and fixed queries were tested.

The next design question is response construction within the same cap: preserve
program/setup/output together when selecting a probe excerpt, and account for the
current question's minimum evidence plus the existing context that a response would
displace. This result does not establish that such a change works. Do not enlarge
budgets, tune this panel or start a paid continuation on the strength of recovery alone.
Model query choice, actual evidence uptake and repair success are all NOT_RUN;
provider/count/evaluator calls and new spending are zero.

The production runtime hash remains
`sha256:77afaab85c6f847956a6856e4706749ffee93e93c0ea69401566075c076098b3`.
All 123 raw BM25 responses reproduced exactly and all 906 bound source/model/helper
files rehashed unchanged. The two generic paraphrase controls passed. The local run
took 384.75 seconds, including 318.16 seconds of CPU embeddings for 979 unique
windows and 0.15 seconds of vector scoring. The previous raw run took 294.49 seconds
for 1,011 windows; these separate timings do not isolate a speed effect. Downloads
and online indexing are excluded; the cached model/dependencies were reused offline.

Evidence root: `C:/pt/semantic21/`. `protocol.md` was frozen before scores;
`projection-audit.json` checks reversible separation; `replay/result.json` binds all
retrievals, input projections and index texts; `paired-analysis.json` records both
same-method and raw-BM25 comparisons; `content-coverage-v2.json` records exact source
coverage and probe equivalence. Reproducers are `audit_projection.py`, `analyze.py`
and `content_audit.py`. The hash-chained journal is
`replay/runs/run_dev_semantichistory.jsonl`. The first content-audit serialization
failed on a supplied-record label; only the label serialization was corrected, and
the empty first artifact was preserved. No rankings or embeddings were rerun.

- Protocol: `sha256:d7f14bdcf8f33cb4dc475b5da7d13709d111e9d6b6cfe9203660fb1f6662faef`.
- Projection audit: `sha256:123fba4f575c75a1f0821cdac984336ffe88157009b006b3f05f68547019494c`.
- Comparison: `sha256:b3a45288cbdb91270fd52f0c2864c62962f6e30c6599f9aab5a1589863f93f4a`.
- Paired audit: `sha256:a751ec97d87d1afecfee63ab551f3438d3ca40b3054dbf6501e541ec09c3c793`.
- Content coverage: `sha256:4103eb6e35bf05cc431f3d404d32e5af91b1216bc3ba30611ae7946c9a0b6543`.

Three added tests cover reversible schema-owned separation, same-named captured data
preservation and observation-only ranking with exact original return bytes. No model
packages or paid calls are needed for tests. The quick suite passed 81 tests in
41.93 seconds (`C:/pt/semantic21/quick.xml` and `quick.log`), including the search
round-trip mock smoke reaching isolated EVALUATOR_PASS. Ruff and documentation checks
passed. No full-suite run; earlier full-suite failures are outside this concise
selection. Final commit, source hashes and validation artifacts are bound in the
external closeout. The pre-existing AGENTS.md edit is preserved.
