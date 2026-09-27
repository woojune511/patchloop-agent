# Closure-policy collector implementation and local validation

Date: 2026-09-28. `official=false`; no live model calls or policy adoption.
Follows the [pair design](2026-09-28-closure-policy-pair-design.md).
Contract: [response sampler](../../.agent/closure-policy-sampler.md).

## Change

The new diagnostic validates the frozen pair against its original dispatch and
source journals, rechecks native delivery, and admits only the exact two-sentence
deletion. It reuses the existing response-only engine. There is no production
prompt change, workspace restoration or execution of returned actions.

Collection reloads disk evidence before credential access; binds implementation,
runtime, public task and prices; requires the exact credential path and positive
grant; and claims a fresh external result root. Four independent responses use
A1/B1/B2/A2 order. Count occurs immediately before each dispatch. Uncertain counting,
transport or usage stops all remaining calls. No retry, correction or resume.

The proposed cap is $4 total / $1 per response. At the stored prices, the inherited
60K input bound plus 25K output reserves at most $0.525 per response. This arithmetic
check is not a fresh price review or paid authorization. Execution-date price review
and user approval remain required. Historical agent-displayed allowance is unchanged;
the collector itself has a separate 1,800-second invocation deadline.

## Evidence and limits

- New focused tests: 13 passed, covering exact-input isolation, rehashed unrelated
  changes, source drift, invalid grants, count/transport/billing stops, input/cost
  bounds, four independent responses, no tool execution and no root reuse.
- Shared response-engine regression tests: 39 passed. Documentation checks: 5 passed.
  Ruff passed for the new diagnostic, production package and tests.
- Full 3,605-test suite was started but stopped during its slow early portion.
  It is incomplete, not a full-suite pass. Focused tests finished under two minutes.
- Mock smoke reached EVALUATOR_PASS (`run_dev_607982192c2b4fc8`) in
  `C:/pt/mock/closure-policy-0928a`; it does not establish this diagnostic's efficacy.
- Actual frozen request validation and four synthetic responses passed in
  `C:/pt/analyses/closure-policy-mock-20260928-v1`. Its recorded provider counters
  and cost are simulated ledger data: actual provider calls and spending were zero.

Current prepared plan: `C:/pt/analyses/closure-policy-collector-20260928-v2/packet.json`.
Packet hash: `sha256:d55e9100ae3a615238a0058bd123fa01bf1c172f1e2c6f4a05e555e4ac1cf5dd`.
Sampler hash: `sha256:fada4b8c9448cc2bdc14ad795f278151c574115376cea1518c517b8e1bc6fd12`.
The v1 preparation predates final implementation binding and is superseded without
modification. Production runtime hash remains
`sha256:850942479181d7ce55199c21f08aa0221edd9bbaaa71098ca13ce6521b51b1de`.

Next is a separately approved response-only collection after current price review.
Chosen actions alone cannot establish successful verification, repair or acceptance.
