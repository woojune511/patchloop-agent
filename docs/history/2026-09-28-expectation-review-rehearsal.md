# Expectation-review matched continuation rehearsal

Date: 2026-09-28. `official=false`; autonomous efficacy NOT_RUN.
Follows [offline pair](2026-09-28-expectation-review-preparation.md).

The existing restoration helper now recognizes review packets, restricts them to
offline-scripted mode, and restores their explicit later prefix rather than selecting
the first post-edit turn. This boundary still has one completed mutation; multiple
historical mutations are rejected. Nested artifact references are copied and checked
without rewriting source events. Historical probes are retained as evidence and never
re-executed. The frozen cumulative budget is simulated, not reopened spending.

Both arms preserve completion-advice removal. The naturally rebuilt first state must
match the baseline except elapsed time; the frozen request then supplies exact first
delivery. B's canonical context and input include the review field. A scoped hook
retains it across pre-dispatch count-driven rebuilding, then stops reinjecting it.
Subsequent history or agent notes can naturally retain its content. No extra tool,
submission gate, private information or answer hint is introduced.

## Executed evidence

The actual toqito checkpoint was restored into two isolated branches with identical
scripted read/stop actions. Both reached AGENT_STOPPED, each with two simulated counts
and two simulated generations, no live provider calls and no new checks/evaluation.
All four dispatched public-state projections verified. First requests exactly match
the frozen A/B pair; field presence was A `[false,false]`, B `[true,false]`.
Both second states retain recommendation removal. Original probe evidence and the
pre-guard-removal patch are preserved, not replayed or replaced by the final patch.

- Durable receipt: `C:/pt/analyses/review-continuation-20260928-v1/receipt.json`.
- Hash-chained journal: `run_dev_reviewcontinuationaudit`; separate A/B fork journals
  and artifacts under the same root. The receipt binds implementation hashes.
- Earlier single-control canary: `C:/pt/analyses/review-fork-A-20260928-v1`.
- Frozen packet remains `C:/pt/analyses/expectation-review-checkpoint-20260928-v1/packet.json`;
  source records and previously closed evidence were not edited.

Synthetic tests cover both arms, count failure with zero dispatch, first-delivery
identity, canonical input bindings, no repeated historical probe execution and no
later review reinjection. An oversized count on this already-fresh segment correctly
stops at LIMIT_REACHED with zero dispatch; it cannot demonstrate a successful new
segment transition before first dispatch. That fallback remains unverified here.
Existing post-edit continuation tests protect the shared restoration
helper. This is infrastructure evidence, not a model decision or solving comparison.

Final review-continuation/projection/document group: 11 passed. The separate shared
post-edit/projection/document regression group: 19 passed. Ruff passed. Ordinary mock
`run_dev_9582a6938502432c` reached isolated EVALUATOR_PASS, safety NOT_RUN and zero cost
under `C:/pt/runs/review-continuation-mock-20260928-v1`. Each focused group remained
under two minutes; the full repository suite was not run.

## Remaining work

No live collector/manifest exists for this later checkpoint. Before a paid comparison,
bind a fresh invocation-wide cap across the matched arms, preserve separate inherited
and newly billed usage, and test uncertainty stops. Historical unused funds stay closed.
Then obtain exact task/model/repeats/credential/cap authorization and collect once.
Score expectation revision, same-input independent properties and final correctness;
scripted read/stop success and probe counts do not establish improvement.
