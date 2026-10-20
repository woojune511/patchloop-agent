# Run-local public history search

2026-10-19. Local implementation and offline experiment; official=false. No paid
execution, provider token counting, native evaluation or credential reading.
Closed caller and size-only experiments remain immutable.

The final packing audit corrects v3/v4, which omitted an already due major-result
follow-up boundary. Their retrieval counts remain valid; their packing and
displacement interpretation is superseded by v5. The correction changes neither
queries nor ranking. It uses `segments.boundary_reason` directly to separate
required result handoffs from additional size-triggered handoffs.

## Question and pre-experiment protocol

[Size-only replay](2026-10-19-size-only-replay.md) retained the original caller packet at 7-8 additional
request opportunities and increased input cost. Can a small registered search
recover already delivered public evidence after its segment expires, without
changing boundaries, source selection or resource limits? Retrieval cannot fix
evidence never obtained, and successful retrieval does not demonstrate correct
judgment or repair. The earlier B runs include condition changes before evidence
loss, so loss is not the only plausible cause.

- Baseline: saved `result-or-size-v1` inputs from all 12 closed caller-evidence
  continuations, all 123 post-checkpoint dispatched requests. No grade-based
  selection. Intervention: opt-in `--history-search public-v1`, one registered
  `search_history` action, at most two exact evidence bundles. Default is none.
- Search only inputs actually dispatched earlier in the same run (including the
  current decision's input). Include paired public calls/results and supplied
  public observations; exclude encrypted reasoning, private/evaluator records,
  model notes/plans as evidence, future inputs and other runs. Quoted old evidence
  never becomes a current PASS, mutation anchor or verified interpretation.
- Query rule, frozen before retrieval: use the current open question when
  nonempty; otherwise current working-plan text; otherwise public task statement.
  Take the first 800 characters. No answer-derived keywords, later decisions,
  evaluation results or per-case query changes. Report empty queries separately.
- Run the same query independently at each saved request; do not pretend the
  saved trajectory already includes these searches. Compare top-two retrieval
  with the exact original operator observation identity and historical executed
  probes. Separate already visible, missing but retrievable, missing/unmatched,
  oversized, and never acquired. A rows are acquisition controls.
- Preserve complete supplied bundles within 24,000 result characters. Oversized
  records return explicit metadata only, never a clipped program/result presented
  as complete. Preserve original identity, delivery provenance and diff currency.
  Exact record IDs can be fetched singly with another counted search action. The
  frozen one-query replay does not assume that a model chooses this extra action.
- Keep result/size boundaries, two current-question references, 24,000 selected
  source characters, 60,000 input tokens, 1,048,576 request bytes, 262,144 maximum
  encrypted-item bytes, 40 calls, 100 actions, four edits and original money/time
  limits. Search consumes an ordinary action and a subsequent model opportunity;
  no reserve for a required source inspection is spent on history retrieval.
- Locally estimate input expansion using the saved tokenizer/count anchors. Apply
  the existing result-follow-up boundary, then check size and the normal fresh
  handoff. Inventory displaced source,
  public observations and tool outputs. Separate hard byte checks from approximate
  token counts, and report unavailable budget explicitly. No provider count calls.
- Success for this diagnostic: exact historical evidence is retrievable with the
  frozen query, complete conditions survive delivery, limits and provenance hold.
  Report failures rather than tune exposed queries/ranking. Default adoption,
  model-chosen queries, evidence uptake and repair success remain NOT_RUN.
- Stop on source hash/chain mismatch, private/future leakage, changed invariant or
  ambiguous source provenance. Keep source artifacts byte-identical. Validate
  registered-tool integration, recovery, budget closure and a local mock smoke.

## Implementation and decision

`patchloop/dev/history_search.py` derives an index from hash-verified model inputs
whose dispatch is recorded in this run. It does not search arbitrary journal
payloads, raw artifact files, reasoning, grades, plans or notes. Paired public
tool arguments/results and supplied public observations remain quoted data with
their original identity, first delivery and diff currency. Source references
within an old result remain historical references, not fresh edit permission.

`search_history(query)` is an opt-in singleton inspect action. Unicode identifier
BM25 ranks records; no Astroid name, error, path or target hash is in the runtime.
The exact record-ID lookup addresses a result whose body could not fit beside
another result. It uses another normal action, not an automatic/free fetch.
The two-result aggregate bound is checked before admitting complete bodies;
metadata-only is explicit. There is no clipped program/result presented as a
complete observation. A record too large on its own stays metadata-only.

The gateway uses the original `action_started` cutoff after interruption and
replays a durable receipt with `action_id + input_hash`. The corpus is not cached
by workspace diff, since new observations can arrive on the same diff. Retrieval
never creates a current source anchor, check PASS, verification-concern resolution
or repair-read credit. The runner offers it only when an ordinary optional action
leaves the protected completion path affordable in calls/actions. Existing cost
admission still applies separately. Envelope, model/tool identities and the
isolated verifier bind the option; defaults and old option-off wire hashes remain.

**Keep the selected baseline and leave search off by default.** First-query
recovery of this packet is limited on these historical questions. Retrieval does
not guarantee that useful counterevidence survives the existing handoff. Known
content caused no additional size handoffs in the corrected replay. This does not
establish that every search strategy is ineffective. Model-chosen search terms,
ID fetch choices, condition alignment and repair success remain untested. Do not start another paid panel
merely because the tool exists or an earlier allocation had unused funds.

## Retrieval results

All 123 original inputs reconstructed exactly before retrieval. Queries came from
105 open questions and 18 existing plans; no query was changed after seeing hits.
The original packet is intentionally absent from A: zero target acquisitions in
its 70 requests. B supplied the packet earlier in all six continuations.

| B's 53 request opportunities | Count |
| --- | ---: |
| Exact packet already visible | 25 |
| Packet missing from current input, present in prior dispatched input | 28 |
| Missing packet returned completely by the first search | 1 |
| Missing packet identified in top two, but body cannot fit beside the first hit | 4 |
| Missing packet outside top two | 23 |

The one newly complete result is B3/request409. B1/request364 also returns the
packet, but it was already visible. The packet is 19,227 canonical characters:
ranking it second often leaves insufficient room under the 24,000 total result
bound. Across all requests, 218 of 246 returned record slots contain complete
bodies; 28 are metadata-only. Exact-ID lookup is tested separately, not counted
as an extra recovered packet in this one-query comparison.

A separate identity audit found 59/246 hits already exactly visible in the current
input, including 15/46 hits at the 23 missing-packet opportunities where the packet
ranked outside the top two. This establishes some redundancy, not that all other
hits are irrelevant or that duplicate filtering would recover the target. The
audit did not alter queries, ranking or the runtime.

This separates three mechanisms: acquisition history exists for all 28 missing
cases; ranking misses the packet in 23; packing with another record prevents full
delivery in four. The first mechanism is addressed by a searchable corpus, but
that alone is insufficient to fix the other two. A question already framed around
a substituted caller condition can keep selecting evidence about that condition.
The experiment does not identify a causal effect on subsequent model judgment.
Packet presence is not a general search-relevance score: other returned records
can answer the immediate question, and these 28 opportunities were not independently
labeled as all requiring the full packet. We establish no improvement in repair.

## Input, budget and displaced evidence

Each opportunity is independent. We add a **quoted hypothetical** tool result to
that saved input and apply the existing result boundary and size projection. This
is a packing diagnostic, not a resumable trajectory or an invented model response.
The search decision's new opaque reasoning, output usage and latency are unknown.
Source selection and current-question references are held fixed; retrieved source
text is not promoted to current mutation evidence. All selected source projections
remain at or below 24,000 characters, with at most two question references.

- 119/123 opportunities have optional model/action headroom under the existing
  protected-completion forecast. A3/485, A3/520, A4/473 and A4/492 do not. This is
  not a claim that all 119 are financially fundable; actual input count, output,
  cache settlement and later admission would still govern any real execution.
- Central known-content estimate: adding search instructions, schema and result
  increases the unrolled input by 3,191–8,344 tokens, median 5,466. The local
  estimator reuses saved counts and reasoning attribution, never tokenizes opaque
  ciphertext, and uses the prior empirical +/-128 sensitivity, not a guaranteed
  provider-count confidence bound. Tool-schema deltas are locally estimated too.
- In all three sensitivity scenarios, 82 opportunities stay in the same segment
  and 41 complete an already pending major-result follow-up. **Zero additional
  size-triggered handoffs** are needed for known content. All candidates fit after
  the applicable ordinary handoff; unknown new search reasoning could require
  additional space. Central final inputs are 26,687–59,532 tokens, median 37,760;
  maximum serialized request is 390,351 bytes and retained opaque item 99,000
  bytes. No size cap is raised.
- A search round costs a call/action as well as the new result's tokens. At the
  source experiment's frozen uncached input price, the **whole extra input** alone
  is about USD 0.0200–0.0446, median USD 0.0283; output/reasoning cost is additional
  and cache behavior is unknown. These are independent estimates, not an invoice,
  budget approval or the cost of a new 12-run experiment. Actual new spend is zero.

At the 41 required result handoffs, native inventory loses 5,731 source
line/version/request exposures, 92 tool outputs and five supplied observations.
Counting retrieved quotations as already visible data leaves **3,782 source
exposures, 63 tool records and five supplied observations absent from these explicit
inventories.** These are exposure counts, not distinct necessary lines. Current
source selection is unchanged. Some older-version text is replaced by current
text. These losses occur when applying the unchanged handoff to a hypothetical
search; they do not establish that search caused extra size loss or a net causal
benefit. Old quoted records receive no source-read or current-check authority.

| Independent opportunity | Data displaced after counting retrieved quotations | Relevance |
| --- | --- | --- |
| A1/430 | 164 source exposures; six read/search results | `modutils.py` resolution and `_import/spec.py` namespace branches remain potentially relevant to the regression being planned. The retrieved mutation/probe concerns `src.project`, not proof of the original `project` caller. |
| A3/396 | 324 source exposures; four read/search results and one probe | The probe fails in `modpath_from_file` before reaching the later planned calls. Losing the raw exception can obscure that the deeper failure path was never tested. |
| B1/515 | 404 source exposures; five read/search results and probe508 | Probe508 directly contrasts a directory argument with the missing initializer and observes different failures. It is a useful countercheck for the current question and is not among the two retrieved records. |
| B2/394 | 191 old-version manager source exposures; four read/search results; exact caller packet | The current-version manager body remains in the retrieved mutation result. The supplied packet expires at the required result handoff in all three sensitivity scenarios. |

B1's lost probe `call_C0AnbL5Vmenbrf1meHIAcb8N` observed `AstroidBuildingError`
with an is-a-directory error for `ast_from_file(project_dir)`, versus
`AstroidImportError` for the missing `__init__.py` path. The retrieved probe uses
the missing path with `source=True` and does not replace that directory comparison.
Both are historical evidence on the same saved diff; neither establishes a repair.

The exact packet expires at B1/378, B2/394, B3/377, B4/421 and B5/390 under the
existing result-follow-up rule. Comparing post-search packet presence against
pre-search presence mixes decision times: another ordinary follow-up action can
also complete that same boundary. The earlier claim that an additional size
handoff canceled B3's recovery is withdrawn. No live trajectory, net search effect
or A/B repair score against size-only's fixed-output trajectory is established.

## Validation and reproducibility

- Final feature/replay/documentation tests: 25 PASS in 114.98s, including a real
  mock smoke reaching isolated EVALUATOR_PASS. A fake-provider transport test
  preserves the expected evaluator provenance rejection and verifies one extra
  counted call/action without changing ordinary result-driven boundaries.
- Tests cover dispatch/future/private/opaque/notes separation, exact bundles,
  aggregate result bounds, ID lookup, current-source/check credit, optional-budget
  closure, same-diff corpus growth, interrupted and durable idempotent recovery,
  exact resume identity and token-size fallback.
- Initial integration caught an omitted verifier tool-contract binding; fixed
  the owning verifier path. Replay caught a derived-state/card shape mismatch and
  the separate 500-character decision-goal limit for an 800-character query. Those
  were corrected without changing queries, BM25 ranking, limits or expectations.
  First-attempt logs remain in the external evidence root. Record-ID lookup was
  added for identified bodies crowded out by another hit; it does not alter the
  frozen question-based ranking or count as a free follow-up in the results.
- Review also reproduced a missing successor reservation when history search is
  combined with `completion-reserve-v1` before a required source read. Include
  history in the optional-action successor calculation and test that five future
  calls remain funded. The first full suite was deliberately stopped before this
  fix; its log and temporary files remain. The selected `per-call-v1` is unchanged.
- Packing review found that the diagnostic omitted the major-result follow-up
  boundary. The correction uses the runtime boundary function and reconstructs
  its public handoff review signals. A regression exercises a mandatory handoff
  with ample context space. All four diagnostic tests pass in 38.36s; v5 verifies
  that all 123 queries, retrieval results and acquisition classifications remain
  identical to v4. Runtime code did not change for this diagnostic correction.
- Full suite: **5,405 PASS, 4 FAIL, 20 SKIP in 7,836.77s** with four workers.
  All four failed runs had history search disabled. They stopped on the existing
  five-second reconciliation reads, with only 13.6-23.5 seconds of the unchanged
  1,800-second total consumed. Two interrupted-run tests therefore did not reach
  submission; one collector dispatched six instead of seven new calls; one of the
  twelve-branch collector's rows stopped before its first new delivery. No cost
  discrepancy or complete-delivery success is inferred from those aborted rows.
- The four exact cases pass individually, **4 PASS in 109.18s**, without changing
  source, timeouts, budgets or assertions. AST comparison verifies the relevant
  recovery/deadline functions match pre-change commit `29488277945c0551c7c39119cdb98ca1c462e1b3`.
  The saved events establish reconciliation expiry. Parallel load is a plausible
  timing cause; test-order effects were not independently excluded. **The full
  suite is not a clean PASS.** Isolated success does not erase its four failures.
- The full suite began on the final runtime before the diagnostic boundary fix;
  the final 25-test focused run covers that diagnostic correction. Skips comprise
  two unavailable symlink cases, four inapplicable brief-planning combinations,
  thirteen explicit real-execution opt-ins and one absent dependency descriptor.
  `C:/pt/history19/full-failure-details.json`, `recovery-path-comparison.json`,
  full-suite/failure-isolation logs and XML preserve the distinction. Final commit
  validation is bound separately in the external closeout. No OpenAI inference/count,
  native grade or Docker run was performed.

Implementation: `patchloop/dev/history_search.py`, contracts/runner/gateway/CLI,
`patchloop/verifier/core.py`; diagnostic: `diagnostics/history_search_replay.py`.
Source: `C:/pt/ce19ready/packet/manifest.json`, rows under `C:/pt/ce19live/`, inherited
public input artifacts only. All **891** source files read were rehashed unchanged.

Final evidence root: `C:/pt/history19/replay-v5/`. `manifest.json` and the hash-chained
`runs/run_dev_historysearchreplay.jsonl` freeze the protocol before retrieval.
`result.json` contains every query, response, packing attempt and displacement;
`analysis.json` distinguishes lost native identities from still-visible quoted
data. `visible-hit-audit.json` records current-input duplicate identities. Frozen
protocol bytes are preserved in CAS. Earlier v1 (interrupted by the goal-field
limit), v2, v3 and v4 remain separate and immutable.

- Result: `sha256:be33c392856467896bd80ab87d078fdf9cd2eb4d2af887a432720ff1ec648a69`.
- Runtime: `sha256:cff1d42f1677bcd59b2e22c99af878eb0593cd1215d24b4bc4501d9884a1fa6b`.
- Source runtime: `sha256:90f3b4f2467cb802e89bd27997e69bc8233e041db18105c7f0a557b5586693f7`.

V4 verified the completion-reservation fix without changing retrieval. V5 fixes
the diagnostic boundary omission; its `verification-comparison.json` confirms
identical queries, retrieval and source files to v4 while explicitly superseding
the earlier packing interpretation. These are corrections and verification of
the same comparison, not additional experimental samples or query tuning.

The diagnostic deliberately reads a prior runtime without resuming it; it first
reconstructs its actual inputs exactly. Ordinary live/recovery runtime matching
remains strict. Local retrieval capability is implemented and tested; model uptake
and actual repair improvement remain NOT_RUN.
