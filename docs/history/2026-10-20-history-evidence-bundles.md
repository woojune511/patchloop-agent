# Exact execution bundles in history responses

2026-10-20. Provider-free follow-up to the
[intent separation comparison](2026-10-19-history-index-separation.md).

## Problem and intervention

The previous fixed-query comparison improved caller-packet restoration with an
intent-separated BM25 index, but lost conditional probe results, a failed setup
check and some current-question source. Whole-body-first rendering could spend
the response on bookkeeping and then return only a historical question for a
probe. An additional size handoff also dropped an already-visible caller packet.
The user requested implementation and a local test of preserving execution
conditions and observations together. These failures affect the ability to tell
an invalid experiment or conditional control from evidence for the actual repair.

The renderer in `diagnostics/history_evidence_bundles.py` preserves candidate IDs,
scores and order. It allocates each candidate's minimum evidence before expanding
source, instead of completing whole records before considering other candidates.

- Registered tool records quote exact values at their original JSON pointers.
  Programs, actual arguments, execution policy/environment, setup comparisons,
  errors, status, stdout/stderr, timeout/truncation/cleanup flags and execution
  observations remain together. A probe that does not fit stays metadata-only;
  its output is never separated from its program and available setup conditions.
- Model intent, annotation receipts and read/search accounting counters are omitted
  from the displayed bundle. Omission paths are explicit. Captured strings and
  supplied observation bodies are not recursively rewritten or truth-certified.
- A source minimum retains actual call/result metadata and one query-matching
  source window using the existing 1,200-character bound and complete lines.
  Empty searches remain exact. A mutation retains its replacement and post-image
  evidence; broad revalidated source can be expanded later. Expansions use residual
  response space in the same candidate order, without adding discarded annotations.
- Supplied observations remain an indivisible original body. Original record
  identities, provenance and exact-ID pages are unchanged. A field bundle is
  explicitly a partial record, not full original-record recovery or current proof.

The optional local packing callback admits a minimum or expansion only if it
fits without losing additional native source, tool output or supplied observations
beyond a metadata-only response with the same candidates. It checks all three
original token-estimation scenarios. This floor is determined by the existing
context rules; no target identity, task name or answer label enters the renderer
or guard. Rejecting an addition can lose useful retrieved evidence and is measured.
It does not change boundaries or prevent a required result handoff.

Question framing and ranking can still exclude the needed record before rendering.
Large atomic execution units can still crowd out other evidence. This comparison
tests the combined allocation and local packing intervention; it does not isolate
which component causes an observed difference.

## Frozen comparison and measurement

Source commit: `2985299398ab42ccc39d614c45ac7c4c2cb8fdaa`.
Frozen protocol: `C:/pt/bundles22/protocol.md`, written before comparison.
Use all 123 saved dispatched inputs after sequence 341 from the same 12 Astroid
continuations. Every question and the eight selected candidates of each separated
BM25/dense/hybrid arm are reused from `C:/pt/semantic21/replay/result.json`.
No reranking, model download, new embedding computation, question rewriting,
future/cross-run evidence, record-ID follow-up or model continuation is simulated.
The same-method old response is the control, with its packed input hash reproduced.

Keep result-or-size-v1, two handoff references, eight candidates/48,000 response
characters, 24,000 retained source characters, 60,000 input tokens, 1MiB request,
262,144-byte opaque item, 40 calls, 100 actions, four edits, 1,800 seconds and
original cost admission. There are 119 admitted search opportunities; four A inputs
have no call/action headroom and are only diagnostic. B has 53 inputs, including
28 where the previously acquired original caller packet is absent. A never acquired
that packet. These correlated decisions are not independent repair trials.

The original caller packet counts only when its exact whole body survives delivery
and packing. Program/setup/output coverage uses the exact probe arguments and actual
result fields, excluding the explanatory question and annotation receipts. Same
execution content in native context can substitute for the corresponding retrieved
record. Source coverage compares exact path, file hash, line and text in native
context, complete quoted spans and full lines within source excerpts. Quoted source
does not become a current mutation anchor. Original metadata or fields not in the
bundle are not inferred from a record ID.

Validate every quoted pointer/value and source offset against its original record.
Report restored and displaced source/probe evidence, caller-packet availability,
native losses, response sizes and packing modes. Inspect the previous 16 missing
probe exposures and the B6 caller loss, plus any new regressions. Stop on provenance,
scope, field, packing or budget failure. No post-outcome tuning or repeat panel.

This remains a local diagnostic. Live token accounting, the latency of a runtime
integration, new reasoning and model use of bundles are not tested. Provider,
counting API and evaluator calls, downloads and new spending are zero. All runs
are official=false; query choice, evidence uptake and repair success are NOT_RUN.

## Results and decision

Each arrow compares the same separated ranking arm's original whole-first renderer
with the new bundle renderer and packing guard. Candidate inclusion is unchanged.

| Measure | BM25 | Dense | Hybrid |
| --- | ---: | ---: | ---: |
| Exact packet returned at the 28 originally missing inputs | 25 -> 24 | 2 -> 16 | 20 -> 24 |
| Exact packet available after packing at all 53 B inputs | 46 -> 49 | 19 -> 41 | 41 -> 49 |
| Paired packet availability gains / losses | 4 / 1 | 22 / 0 | 10 / 2 |
| Recorded probe execution units gained / lost | 24 / 2 | 16 / 6 | 26 / 10 |
| Exact source-line exposures gained / lost | 6,629 / 5,472 | 4,891 / 4,384 | 5,634 / 5,628 |
| Size handoffs | 19 -> 0 | 18 -> 0 | 19 -> 0 |
| Additional native source / output / observation losses | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |

The 41 required major-result handoffs remain; the other 82 opportunities stay in the
same segment in all three token-estimation scenarios. This does not disable size
handoffs: additions that would require them are rejected. Minimums/expansions rejected
for context preservation total 87/79/92, with another 262/186/253 rejected by the
response cap. These counts include multiple proposed additions within one search.

Maximum response sizes are 47,952/47,997/47,998 characters, and maximum central input
estimates are 59,860/59,854/59,866 tokens. All final inputs fit in all three scenarios.
The guard preserves 5,593/5,408/5,593 native source-line exposures, 123/119/123 outputs
and 5/4/5 supplied observations relative to the old same-method responses. These
native quantities overlap the overall source/probe changes and must not be added.
Zero added native loss is a checked property of the guard, not evidence that every
retained native fact matters more than a rejected result.

The dense arm's exact packet delivery rises from 2 to 16 while its ranking is fixed.
The earlier weak dense result therefore included a delivery bottleneck, not only
poor ranking. It still trails the other arms on this packet, and this comparison
does not establish a broadly superior search method. The packet is a single known
development-exposed target; not every question independently needs it.

All source/probe counts are repeated exposures across saved decisions. Source
counts include blank lines and historical file versions, and do not assign equal
importance to every line. A complete execution unit means all recorded arguments
and captured result fields, including original truncation flags; it does not restore
output that the original execution never captured. Whole-record delivery and these
execution-field units remain separate metrics.

## Recovery and new losses in the current questions

The BM25 audit revisits all 16 earlier probe exposures that lacked equivalent complete
program/output evidence. Nine are recovered. This includes the conditional namespace
control at B3/377, /393 and /409; the failed `cwd_is_workspace` setup check at four of
five A5 inputs; and the missing-initializer/context-file failure at B5/466. The actual
program, setup report and captured output now travel together. The failed A5 setup
still means execution stopped before the intended calls, not a behavioral result.

Seven remain missing: A3/366's probe is outside the frozen eight candidates; the
minimum units at B1/456, B2/394, B2/410, A5/452, B5/405 and B5/466 do not fit the
context/response allocation. In particular, B5/466 recovers the missing-initializer
failure but still loses the directory-versus-real-file control. Restoring one branch
does not establish that the competing branch is preserved. Of the prior 1,953 missing
source-line exposures, 534 return; the rest are still absent under the exact-line
criterion. Selection outside the candidate set cannot be fixed by rendering alone.

At B6/380, the original caller packet was already visible but the old separated
response forced an extra size handoff. The new 40,904-character response fits in
the same segment at an estimated 57,638 tokens, retains the packet and has no
rejected additions. BM25 also retains previously lost packets at B4/407, B6/393
and B6/406. This is recovery of existing context, distinct from retrieval of a
previously missing packet.

The new regressions prevent an unconditional adoption:

- **B1/502, original caller packet:** the question asks how `ast_from_file` and
  `file_build` distinguish a missing initializer from a directory. The packet is
  rank one but the context guard rejects its minimum, even though the old renderer
  delivered it after a size handoff. The new same-segment input is 59,488 tokens.
  Protecting all existing native evidence ahead of this new packet is not a
  demonstrated current-question priority. Hybrid also loses it at B1/489.
- **B1/489, recorded source-flag counterexample:** BM25 now loses the full probe
  showing both default and `source=True` missing-initializer calls raising
  `AstroidImportError`. Context preservation rejects the unit. It is related to
  the current fallback question, while its differing caller/environment and diff
  still limit transfer to the exact public failure.
- **A2/448, conditional namespace control:** BM25 loses the complete namespace
  success probe while the question asks about tightening `get_source_file` and
  directory compatibility. This is a useful alternative path, but not a direct
  test of `include_no_ext=True`. Its necessity is weaker than that of the exact
  B1 caller conditions; neither loss should be hidden by the net gain of 22 probes.
- **B1/364, source behavior:** the short builder excerpt retains class setup and
  `module_build`, while `file_build` lines 115--151 disappear, including
  `open_source_file(path)`, the `OSError` branch and module-name derivation. These
  lines help explain the question's source/fallback failure. Exact full-line
  quoting prevents fabrication but does not make lexical window selection sufficient.
- Many other source losses are less decisive. At B3/409, much of the lost builder
  text is imports or neighboring methods; the actual `file_build` file-opening
  branch survives across the excerpt and native context. The 5,472 lost BM25 line
  exposures therefore must not be described as 5,472 necessary counterevidence lines.

The dense arm loses six exposures of the same conditional namespace-control content
(A4/419 through /473 and B5/377); hybrid loses ten, including B1/515, /530 and
B6/393, /406. They constrain alternative namespace paths but are not the exact
public caller. Complete bodies, questions, diffs, source-line losses and rejection
reasons remain in the saved audit for every arm.

## Decision and evidence

Keep this implemented renderer and local packing guard diagnostic-only. Do not
replace the production BM25 renderer, change its default-off behavior or launch a
paid continuation. The comparison supports quoting execution conditions and captured
results together and shows that response construction materially affects semantic
retrieval's measured delivery. It also falsifies the stronger expectation that this
allocation would preserve the current question's necessary branches without new loss.

The unresolved priority is now explicit: preserving every native fact can block an
important new caller packet, and a short lexical source window can omit the relevant
function branch. More packet availability or more execution units is not sufficient
to accept that tradeoff. Any next change needs to distinguish the current question's
minimum source/caller evidence from other retained content within the same limits;
this run does not demonstrate that selection or an actual repair improvement.
No fields, thresholds or rankings were retuned after these outcomes.

All 369 same-method baseline packed inputs reproduced their saved hashes. The run
checked 63,026 exact field/excerpt values and rehashed 947 bound files unchanged.
Runtime hash remains
`sha256:77afaab85c6f847956a6856e4706749ffee93e93c0ea69401566075c076098b3`.
Replay elapsed time was 532.02 seconds; this repeated offline packing prototype
does not measure an agent's live search latency.

Evidence root: `C:/pt/bundles22/`. `replay/result.json` binds the responses, packed
inputs, source/probe changes and addition decisions. `loss-review.json` revisits the
previous losses and inventories every new loss; `review.py` reproduces that audit.
The append-only journal is `replay/runs/run_dev_evidencebundles.jsonl`. Baseline files
under `C:/pt/semantic21/` and earlier closed reports were not modified.

- Protocol: `sha256:fe58d4d6885adfe40fb2ff7fa4441cb7007e079db4664989e5d083293bf67283`.
- Comparison: `sha256:4841fc39647cdd0d99c0cb1d0788fc9a97f2b7b866522da6e813b1023bc255e0`.
- Loss review: `sha256:33f3d8693bdbac791190bce85a4a605c533aac4c61640ad81768460608cbbe19`.

The external closeout binds the final commit, validation and source hashes. Model
evidence uptake and actual repair success remain NOT_RUN; new spending is zero.

## Validation

Five focused cases cover atomic failed-setup/truncated probe delivery, minimum-unit
allocation before source expansion, exact full-line source offsets and empty
searches, local budget rejection/unchanged ID paging, and execution coverage without
claiming full-record restoration. The concise quick suite passed 86 tests in 39.33
seconds (`C:/pt/bundles22/quick.xml` and `quick.log`), including isolated mock search
smoke. Ruff passed on `patchloop`, `tests` and the three new diagnostic modules.
No full-suite run; prior unrelated full-suite failures remain unresolved. Tests ran
concurrently with part of the local replay, so replay time is not an isolated latency
benchmark. Production runtime and the pre-existing user AGENTS.md edit are unchanged.
