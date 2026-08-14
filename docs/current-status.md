# Current status — 2026-08-14

## Current checkpoint

The reusable fast track and evaluator-v2 paid boundary are implemented. R10 qualified the exact R8 source at commit
`a4f00f8565c840588b120d91e730427bb51166b5`. R8 candidate `sha256:60c67908...cff9e` received one approval binding
Moto A/C + Babel C/A, `$15.30` reserve and `$18` cap. All four Moto A/C + Babel C/A rows resolved, passed
hidden/regression/scope/safety, carried authenticated evaluator-v2 receipts, trace-qualified and cost-settled. Actual
model cost was `$0.3664215`; the four-run A/C readiness matrix is complete and R8 is consumed.

The immutable result incorrectly stored `inconclusive`: its completion adapter accepted
`trace-qualification-v1`, while every live producer row correctly emitted `trace-qualification-v2`. The original
result and journal remain unchanged. Append-only index
`reports/live-pilot/dev-validation-ac-fixed-bundle-readiness-20260814-r8-evidence-r4.json` binds them and records the
offline corrected projection: 4 official receipt-qualified v2 runs, 4 successes, 0 failures and 0 unclassified.
Correction activity was zero provider/evaluator/Docker/agent calls and `$0` added cost.

R3 through R6 remain sealed `inconclusive` predecessors: R3 stopped after Moto C exhausted its aggregate token
budget; R4 failed split-budget paid-plan binding before provider dispatch; R5 and R6 each resolved/evaluated Moto A
but failed successive terminal-qualification contracts. R7/R9 is superseded unexecuted. None may retry, resume or
transfer approval. Exact tuples are in `docs/09-evidence.md`.

D-142 remains **source-qualified only, unactivated**; its planning disposition is now **deferred**. D-142 and the V25 one-use
lifecycle are historical, not current gates.

## Evaluator correctness gap

Evaluator-v1 still assigns literal safety PASS. V2 binds typed evidence, fail-closed verdicts, durable receipts and
qualification while each raw v2 result remains `official=false`. R8 is the first complete receipt-qualified four-row
development-readiness matrix. This validates the exact path, not production security, held-out generalization or a
memory effect.

## R8 result boundary

All R8 rows shared `cumulative-split-v1`: 3M input, 350k output, 3.35M aggregate, 25k/response, 180 model calls, 300
tool calls and 3,600 seconds. The reserve was `$3.825`/row and `$15.30`/panel under an `$18` cap; these R3-informed
limits are not held-out-safe or completion guarantees.

Both A and C resolved twice, so observed success delta is zero. Structured used 37,997 fewer total tokens and
`$0.03862275` less on Moto, and 36,041 fewer tokens and `$0.04254075` less on Babel. These are descriptive results
from two development tasks and one repetition, with no causal or inferential memory-benefit authority.

## Evidence, retry and authority

Completed evidence is append-only; R3 through R8 are never overwritten. Reusable no-call preflight allows at most
three transient pre-provider attempts without state artifacts or per-attempt approval prose, but R8 is now in the
historical consumed set. Its candidate, plan and approval cannot run again. R10 binds the executed bytes, not the
completion-corrected current source. No paid, held-out or B/D execution is currently authorized.

## Next gate

Work item 6 freezes a 48-row scheduled-row complete-panel design; execution and unblinding remain closed. Next: offline
qualification, refreshed pricing, an exact candidate and separate approval.
