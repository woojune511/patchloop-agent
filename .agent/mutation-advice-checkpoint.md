# Current mutation advice checkpoint diagnostic

## Question and implemented scope

N1's first AnyIO repair relied on caller cancellation that its preceding probe had
not measured. The current input also recommended `replace_text`. Their coexistence
does not establish causation. Test the immediate contribution of that recommendation
before adding another generic instruction or mandatory probe.

`diagnostics.mutation_advice_checkpoint` implements **offline preparation and
validation only**. It selects the next input after the first successful probe batch,
before any mutation, from a content-bound OpenAI segmented `dev-train` run. It checks
the journal chain, public projection, encrypted continuation, source identities and
historical count/dispatch binding. It executes no searches, probes, checks, model
requests, counts, credential reads or evaluator. There is no `collect` command or
full-rollout continuation engine in this module.

## One-factor input contract

A is the exact saved request object, including its final current-state message.
B changes only these fields in that message:

- `completion_guidance.next_action`: `{"tool":"replace_text"}` becomes `null`.
- `completion_guidance.message`: remove the instruction to use `replace_text`;
  retain the repair status, anchor-evidence caveat and submission requirements.

All other request values are identical: system/public task, tool schema/admission,
probe result, source spans, plans/notes, horizon, budget, model/effort/output ceiling,
and native history including opaque encrypted continuation. Earlier rendered current
states are not reinserted. Prior exposure through continuation is not erased, and
other mutation cues remain. This tests current-message advice, not all prior advice
or all action pressure. A different next action alone is not improvement evidence.

The A hash must equal its historical counted/dispatched request hash. B receives
its own hash; the historical token count is not reused for B. Preserved source
segment metadata describes the original context, not a new B execution receipt.
Hashes bind canonical JSON request objects, not captured HTTP transport bytes.
Future edits, later failed probes and evaluator results are never inserted into
either input. Changing historical records to make B look original is prohibited.

## Proposed later execution contract — not authorized or implemented here

Use `anyio-interrupt-runner-cleanup-v3` and `gpt-5.4-2026-03-05`, xhigh, desired
25,000 output tokens, with the same public source/dependency identities and runtime
policies. Proposed order is A1, B1, B2, A2: two independent continuations per arm,
not paired deterministic seeds or an estimate of general reliability.

Restore the checkpoint's gateway evidence/anchors, plans/notes, tool results,
conversation, segment state and counters in fresh external roots. Do not replay
the historical probe or charge its prior work as new execution. The captured
remaining allowance is 37 model calls, 92 tool actions, four accepted mutations,
1,655 active seconds and $0.967463 per continuation; original settled prefix cost
is $0.232537. Proposed new invocation cap is **$3.869852 for all four continuations**.
Historical $1.20 caps and closed allocations confer no new spending authority.

Apply B only to the first dispatched checkpoint request. Later messages use the
unchanged runtime. Execute selected actions through registered tools, including
`action_id + input_hash` recovery, required checks and isolated evaluation on finish.
The restored source-dependent state and first dispatched A/B identities need a
provider-free end-to-end test before live work. A fresh solve, seeded-patch loop or
next-response-only sampler does not satisfy this continuation contract.

Before any live run, freeze the runtime/implementation, exact credential file,
prepared-source/dependency/image hashes, prices, four-run order and positive total
cap in a separately authorized manifest. Count each actual request immediately
before dispatch, keep zero SDK retries, and stop remaining repetitions on count,
transport, billing or cleanup uncertainty. Do not start Docker or pull images.
Restore the historical budget display coherently with fresh invocation accounting;
old usage is baseline bookkeeping, not new billed cost. Do not silently grant a
fresh 40-call/1,800-second horizon. Record environment readiness separately.

Primary outcomes: submitted task acceptance and safety separately, public check
regressions, new billed cost and active time. Secondary trace review: whether the
first edit's premise was measured, whether a new probe discriminates competing
causes, and whether cancellation ordering preserves cleanup. Non-submission leaves
acceptance/safety `NOT_RUN`; more reads/probes alone do not count as success.
Keep `official=false`; no default adoption or efficacy claim follows preparation.

## Commands and artifacts

Prepare from a JSON `Source` record containing root/run ID and exact journal,
envelope and public-task file hashes:

```powershell
python -m diagnostics.mutation_advice_checkpoint prepare --source C:\pt\source.json --output C:\pt\fresh-packet
python -m diagnostics.mutation_advice_checkpoint validate --packet C:\pt\fresh-packet\packet.json --packet-hash <sha256>
```

Output must be fresh, external and disjoint from the source. The packet contains
content-addressed A/B requests, inherited artifact identities, a bounded checkpoint
receipt and a separate hash-chained `dev-run-v1` preparation journal. Its state is
`PREPARED_NOT_EXECUTABLE`. Preserve it; changes require a new packet. Tests cover
synthetic native history, exact field isolation, evidence/budget/schema tampering,
unknown guidance, source identity, CAS integrity and overwrite rejection. They do
not establish provider acceptance, environment readiness or task-solving efficacy.
