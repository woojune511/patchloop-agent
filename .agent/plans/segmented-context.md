# Segmented public working state (v39)

Implemented experimental `--context-policy segmented-v1`. Default is still
`append-v1`, planning `none`. This change authorizes provider-free verification,
not a new paid run, B4 resume, or reopening the closed planning comparison.

## Ownership and projection

The gateway, not a model summary, supplies the exact public task, full current
diff/files, current-diff check table, current failure or pending recheck, submission
conditions, actual tools, and global execution/cost budgets. Retain existing bounded
successful/rejected mutation evidence. A visible PASS is not full task acceptance.

Latest source-validated notes/question and optional <=3,000-character plan replace
older values; six-finding retention/expiry and verification concerns are unchanged.
Model-authored statements remain unverified. Empty notes/plans stay empty. A handoff
invites reconsideration on the next ordinary tool decision; no mandatory annotation,
new schema, planning-only turn, or extra model call. Null preserves existing values.

Current source uses the existing 24,000-character prioritized retained projection.
Latest parallel batch results retain their existing per-tool bounds. At handoff,
quote their real public calls/results in `harness_historical_public_evidence_v1`,
not top-level `function_call_output`. New-segment source references resolve against
that quoted record or inline current observations. No unseen source is read, no old
native reference is left pointing to absent history. Gateway admission still accepts
all actually observed current evidence, not just the latest prompt's working set.

Keep recent three inspection/attempt outcomes and search aggregates. Superseded
snapshots/plans, unselected old source/candidate bodies, and older native exchanges
leave the next segment's input, not the immutable journal/CAS. External archives
are not an agent-accessible memory tool. Registered read/search re-observes current
public source when necessary.

## Segment boundaries

Inside a segment, preserve native encrypted reasoning and actual call/result order.
The seed has an immutable public task and a single same-task user message; the
mutable current-state record is replaced. Between segments explicitly begin a new
request with public working state, no earlier reasoning/native continuation.
This is an intentional information-loss experiment, not equivalent reasoning state.
The [official reasoning guidance](https://developers.openai.com/api/docs/guides/reasoning#keeping-reasoning-items-in-context)
motivates preserving complete native order inside the interval, not treating opaque
reasoning as durable cross-segment public memory.

Mutation success/rejection or public check/probe completion schedules review. Switch
only after the next normal decision and its completed batch. A normal decision's
own major result remains pending until a later decision; the watermark is the
reviewing turn's start, not its batch finish. This proves delivery and subsequent
action, not understanding, a causal pivot, or a substantive plan update.

Size can override the wait at a completed execution boundary:

| Resource | Experimental ceiling | Measurement |
| --- | ---: | --- |
| Input tokens | 60,000 | Successful exact request count |
| Request JSON | 1,048,576 bytes | Complete final HTTPX/SDK UTF-8 JSON serialization |
| Single encrypted field | 262,144 bytes | UTF-8 field value, not tokens or JSON characters |

Check bytes before count; on excess compose a fresh seed. If a normal count exceeds
60,000, compose/recount the changed request. A fresh seed still over any ceiling
terminates `LIMIT_REACHED` once, without silently clipping task/diff/failure evidence.
These are PatchLoop management thresholds, not verified API limits or optimum values.
No standalone compact call; simultaneous native-compaction options are rejected.

Known completed reasoning-only incomplete output can be excluded for size while
preserving its original correction and protocol allowance. Unknown count/provider
dispatch, billing uncertainty, missing or corrupt continuation/inputs are terminal;
resegmentation cannot repair them. Generating huge reasoning remains a model risk.

## Durable identity and recovery

`segments.py` binds thresholds/instructions/boundary semantics into model hash,
envelope segment contract and v39 tool-surface identity. Tool names/input formats
are unchanged; planning OFF adds no plan fields. Segmented planning supports `none`,
`brief-v1` and opt-in `brief-evidence-v1`; the latter changes only plan-format
instructions, not segment timing or handoff semantics. The selected planning
contract is bound separately. Existing native-window restrictions remain unchanged.

Under the run execution lock, write the handoff CAS before `context_segment_started`.
The event binds previous/current segment ID, reason, seed/state/contract hashes,
parent input, last decision/batch, cursor and review watermark. Per-turn metadata
binds the active handoff and previous in-segment input. Restore/validate this chain,
finish pending decision/actions/reconciliation first, then consider a new request.
Never replay an unknown provider dispatch or count. A completed count is reused on
resume; reseeding intentionally requires a new exact count but no extra model turn.

No cost, time, protocol, accepted-mutation, tool-action or completion-horizon reset.
Public terminal `context_management` reports segment count/reasons and bounded
context-limit details. Terminal resume remains read-only/idempotent. Old runs are
not migrated; nonterminal exact-runtime/config mismatches fail before provider work.

## Evidence and limitations

Verification: `tests/test_dev_segments.py`, existing planning/window/continuation/
source/gateway tests, Ruff, full external-root pytest, and true local mock smoke.
Injected fake-provider tests intentionally fail isolated manifest validation because
their synthetic Docker identity differs from the smoke task; separate provider=mock
runs verify real isolated acceptance PASS / safety NOT_RUN without weakening it.

Read-only B4 comparison is in `C:\pt\validation\segmented-context-20260914`.
Use `b4-comparison-verified.json` (including inline source inventory), not the first
draft's native-only source count. Both shapes are measured with the same current
schemas/settings: 2,175,132 -> 99,185 UTF-8 bytes; 85 -> 5 items. All 261 selected
current-source lines survive, with 815 total quoted/inline observed lines and no new
unobserved source. The 21 old reasoning items and older exchanges/state are absent.
Historical plan revision 1 and empty findings remain, explicitly unverified.
No real token count, generation, compact, Docker or hidden evaluator was invoked.
This is not proof the model will update a plan, remember all relevant semantics,
avoid repeat exploration, or solve the task. A separately frozen future packet is
needed for behavioral testing; do not revive the consumed planning/compact grants.

Final verification receipt: `verification.json`. Focus44 PASS/81.734s, shared139
PASS/104.212s, full2155 cases/762.928s with one stale expected v38 hash corrected
and targeted rerun: combined2147 PASS/8 skips. No production change after full-suite
dispatch. Final local smoke OFF/ON each4 model/5 tools/1 edit/2 segments through
real isolated smoke acceptance PASS, safety NOT_RUN; ON revision2 is actually in
the saved next input. These are provider-free functional results, not pyfakefs live
performance. All9658 protected files/eight old journals/closed result match baseline.
