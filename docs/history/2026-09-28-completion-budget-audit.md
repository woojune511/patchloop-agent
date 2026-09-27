# Completion-budget audit of the original pilot

2026-09-28. Provider-free, `official=false`; no runtime/default changes.

## Question and method

The [pilot](2026-09-28-original-pilot-results.md) left toqito unsubmitted after a
244-token post-edit response. Would the existing opt-in completion-reserve policy
address that failure without cutting off useful public investigation?

Read saved public context/request artifacts and settled usage from all three runs.
Reconstruct each of the 24 dispatched-call states, then call the actual `_tool_policy`
and `DevCostLedger.admit` with baseline and reserve policies. Baseline tool sets,
minimum/protected horizons and output ceilings match every saved state. Artifact
hashes and source journals are verified. No source checkout, model, token-count
service, evaluator, private tests or reference patch is executed or projected.

Every row starts from the observed baseline state and spend. These are independent
policy projections, not a simulated alternate solve. Alternative schemas/context
would change input tokens: ceilings below reuse observed counts as a sensitivity
calculation, not exact token counts for a newly assembled alternative request.
Later rows cannot be chained after an earlier policy divergence.

## Findings

1. `per-call-v1` protects the current request's maximum cost but reserves no future
   calls. Model/tool-count completion checks do not prevent monetary starvation.
2. `completion-reserve-v1` prices each future call as 60,000 uncached input tokens
   plus **128 output tokens**, or **$0.15192** at the frozen model rates. It intersects
   affordable call slots with the existing completion/recovery scheduler. It is an
   admission floor, not evidence that an xhigh response can emit a useful action.
3. At $1.20, only seven such slots fit. The initial state requires four calls on the
   success path and nine with protected recovery. Its special missing-anchor exception
   allows one read/search. After that evidence, the ordinary protected horizon is eight;
   another inspection must preserve that horizon. With only seven funded slots,
   **all three observed second-call states offer only replace_text and stop_task**.
   The rule treats delivered editable evidence as an anchor, not semantic sufficiency.
4. Therefore successful baseline investigations would change too. MontePy's first
   response already contains two parallel searches, exceeding the alternate initial
   max_parallel_reads=1. Toqito and darts first actions fit, but their second source
   reads/searches do not. Tool schemas differ from the first request for every task,
   even where the observed action remains admissible.

| Toqito observed state | Remaining USD | Minimum / protected calls | Reserve projection |
| --- | --- | --- | --- |
| First request | 1.2000000 | 4 / 9 | one read/search; reserve 3 calls ($0.45576) |
| Second request | 1.1663025 | 3 / 8 | edit/stop only; reserve 2 calls ($0.30384) |
| Before eighth, edit-producing call | 0.4642405 | 3 / 8 | edit/stop; reserve $0.30384 |
| After accepted edit, ninth call | 0.1087010 | 2 / 7 | completion infeasible; no dispatch |

At the eighth state, reserving two calls and reusing 30,731 observed input tokens
would leave **5,571 output tokens**, versus the actual edit response's **19,560**
(including 14,349 reasoning tokens). This demonstrates the budget tradeoff, not that
the same edit would be produced under the smaller allowance. At the ninth state the
reserve policy would stop before the observed $0.094002 incomplete call. It cannot
recover already-spent money or establish a successful earlier alternative.

The successful baseline check/finish responses were 629/696 output tokens for MontePy
and 1,343/712 for darts. These observations exceed 128 but are not a reliable universal
minimum. Raising the future-output floor alone would reduce affordable slots further;
it does not resolve the early exploration restriction.

## Decision and next diagnostic

Do not adopt completion-reserve-v1 as the fix. It couples financial reservation to a
protected recovery horizon that closes source investigation early at this allowance,
while still promising only minimal output admission. The audit proves neither that
this would fail every solve nor that an alternative would improve correctness.

Next isolate two decisions in a provider-free diagnostic: reserve a minimal successful
check/submit path separately from speculative recovery, and examine current-response
output headroom separately from future-call input cost. Retain the existing action-count
scheduler; avoid adding task-specific hints or a new hard tool gate from this one failure.
Use the two successful traces as controls and stop counterfactual claims at first divergence.
Do not increase budgets, select an output floor from one success, or start a paid rerun.

## Evidence and validation

Runtime remains `sha256:850942479181d7ce55199c21f08aa0221edd9bbaaa71098ca13ce6521b51b1de`.
Audit root: `C:/pt/analyses/completion-budget-audit-20260928-v2`.
Journal: `runs/run_dev_completionbudgetaudit.jsonl`; report: `audit.json`.
Driver: `C:/pt/completion_budget_audit_0928_v2.py`, hash bound in audit_started.
V1 is retained; v2 additionally checks parallel-read batch admission and separates
completion infeasibility from arithmetic current-call affordability. No historical
pilot record, task, runtime policy or source evidence was modified.

Validation: existing `tests/test_dev_completion_cost.py` passed, including its offline
admission/recovery controls; documentation layout 5 passed after shortening current
summaries. Ruff passed. No new mock invocation or full-suite run was required for
this documentation-only record; no runtime behavior changed. Additional provider cost: $0.
