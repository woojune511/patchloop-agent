# Current status — 2026-08-14

## Current checkpoint

The reusable fast track and corrected evaluator-v2 paid boundary are implemented. The successor A/C offline qualification
R10/v11/R8 rejects duplicate YAML keys, scalar coercion, incomplete paid-source closure and evidence drift. R7/R9 is
immutable but superseded unexecuted; its candidate and approval prose do not transfer.

The approved R4 campaign is sealed `inconclusive` at execution hash `sha256:be4ea2e4...8d7124`. Paid-plan
revalidation selected the legacy aggregate-only budget instead of R4's split budget, so Moto A terminated with
`ContractError` before provider dispatch, cost `$0`, and the other three rows were not started. R4 and its R6 source
qualification cannot retry or resume.

The approved R5 campaign is also sealed `inconclusive` at execution hash `sha256:b8d156c6...a1627`. Moto
A/no-memory resolved and all evaluator-v2 verdicts passed, but terminal qualification still required the legacy
null-call/aggregate-only profile. The row therefore ended `TraceQualificationFailed` after evaluation; Moto C and
both Babel rows were not started. Actual settled model cost was `$0.19303425`; R5 cannot retry or resume.

The approved R6 campaign is sealed `inconclusive` at execution hash `sha256:c800f36b...e5d61`. Moto
A/no-memory resolved and all evaluator-v2 verdicts passed, but its runtime evidence serialized the legacy
`model-tool-observability-only-v1` policy while terminal qualification required
`model-tool-bounded-enforcement-v1`. The row ended `TraceQualificationFailed`; Moto C and both Babel rows were not
started. It used 144,240 input plus 13,648 output tokens, 14 model calls, 15 tool calls and `$0.169596`. The checked-in
evidence index is owned by `docs/09-evidence.md`; R6 cannot retry or resume.

One approved R3 **four-run A/C readiness** campaign is sealed `inconclusive` at execution hash
`sha256:c6506a33...374a2a` and indexed by
`reports/live-pilot/dev-validation-ac-fixed-bundle-readiness-20260813-r3-evidence.json`. Two Moto rows became
terminal; the fail-closed halt left both Babel rows not started. No retry, held-out A/C or B/D run occurred.

D-142 remains **source-qualified only, unactivated**; its planning disposition is now **deferred**.
D-142 and the V25 one-use lifecycle are historical, not current gates.

## Evaluator correctness gap

Evaluator-v1 still assigns literal safety PASS. V2's offline successor-only integration path binds typed evidence,
fail-closed verdicts, durable receipts and qualification while keeping raw results `official=false`. R3 contains one receipt-qualified Moto A success; its Moto
C hit the 3M ceiling before submission and Babel did not start. R5 and R6 each add one resolved evaluator-v2 Moto A
row that failed post-evaluator trace qualification. None is a complete panel, security claim or memory-effect result;
`docs/09-evidence.md` owns the exact row, token, cost and hash tuples.

## R8 successor budget boundary

R8 preserves R7's identical A/C limits: `cumulative-split-v1`, 3,000,000 input, 350,000 output, 3,350,000 aggregate,
25,000 output per response, 180 model calls, 300 tool calls and 3,600 seconds. Reasoning counts as output; every
dimension fails closed.

The full-input-price reserve is `$3.825` per row and `$15.30` per panel, with `$18` cap and `$2.70` slack. This
diagnostic tuple is informed by one R3 development row; it is neither held-out-safe, an invoice/completion guarantee,
nor evidence that extra budget benefits memory.

## Evidence and retry rule

Completed evidence is append-only; R3 through R6 are never resumed or overwritten. Reusable no-call preflight is bounded to
three transient pre-provider attempts without state artifacts or per-attempt approval prose. Semantic or budget
changes require the corresponding new version, identity, qualification, cost binding and approval.

## Closed authority

R3 through R6 approvals are consumed. R7/R9 is superseded unexecuted. Its old candidate
`sha256:8b962b80...bf6c` is invalid for the contract-hardened source. R10 is offline-only and currently authorizes no
preflight candidate, Docker/credential observation, provider, evaluator or agent call. Paid, held-out and B/D
execution remain closed.

## Next gate

Commit an execution-clean R8 source, then run bounded no-call preflight. Only a newly emitted exact R8 candidate
may be presented for a separate Moto A/C + Babel C/A
four-row approval binding `$15.30` full-schedule reserve and `$18` hard cap.
