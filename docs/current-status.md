# Current status — 2026-08-15

## Current checkpoint

R10-qualified R8 candidate `sha256:60c67908...cff9e` consumed its Moto A/C + Babel C/A `$15.30`/`$18` approval.
All four Moto A/C + Babel C/A rows resolved with four PASS verdicts, authenticated v2 receipts and settlement for
`$0.3664215`; the four-run A/C readiness matrix is complete. Its stale v1/v2 projection is corrected append-only.
R3-R6 remain sealed inconclusive and R7/R9 remains superseded.

Held-out R11 candidate `sha256:f48a0de...a6b0` consumed one exact 48-row `$252`/`$275` approval. It sealed
`inconclusive` after 3 starts: 2 settled, 1 observed-unsettled and 45 not started. Settled model cost was
`$0.15699525`; the unsettled row had durable `$0.261021` usage, so total observed started cost was `$0.41801625`.
No complete matrix, official held-out analysis or memory claim follows.

## R11 failure attribution

- Loguru/structured resolved with four PASS verdicts at `$0.0972915`.
- Loguru/no-memory settled as hidden/safety FAIL at `$0.05970375`. Its 14 redactions were evaluator-private while
  agent-visible event/patch matches were zero; correcting that false safety signal does not change the hidden failure.
- Dagster/no-memory completed agent submission but did not run the evaluator. Historical runtime recorded
  `CONTRACT_ERROR`; deterministic successor attribution is `EVALUATOR_CONTROL_CONTRACT_COLLISION`, caused by raw
  registered-check control text colliding with fixed redaction placeholders. Agent-visible marker matches were zero.

The immutable runtime artifacts remain unchanged. Correction index
`reports/heldout-ac/artifacts/heldout-ac-r11-campaign-inconclusive-r1.json` binds the observed rows, durable usage,
historical error code and post-runtime attribution; it made zero provider/evaluator/Docker/SDK/agent calls and added
`$0` cost.

## Evaluator correctness gap

Evaluator-v1 still assigns literal safety PASS. V2 binds typed evidence, fail-closed verdicts, durable receipts and
qualification while raw v2 results remain `official=false`. R8 is the first complete receipt-qualified four-row
development-readiness matrix; this validates the exact path, not production security, held-out generalization or a
memory effect.

The successor uses opaque controls, agent-visible leakage evidence, durable pre-qualification cost, typed failures,
pre-journal plan validation and timestamp-independent paid identity. Persisted DTOs remain unofficial; only
runtime-authenticated non-serialized provenance can reach the 48-row analysis gate.

Development-only evidence lowers equal A/C to 1M/100k/1.1M tokens, `$1.20`/row and `$57.60`/`$60`; held-out outcomes
and task content were excluded, and results cannot pool directly with R11. Contract R8 → binding R9 → materialization
R5 → execution R6 → preflight R14 remains zero-authority.

## Evidence, retry and authority

Completed evidence is append-only. R3-R8 development campaigns and held-out R7/R11 cannot retry, resume, overwrite or
transfer approval. Reusable no-call preflight allows at most three transient pre-provider attempts without state
artifacts or per-attempt approval prose; paid campaign identity is separately one-use across readiness timestamps.

D-142 remains **source-qualified only, unactivated**; its planning disposition is now **deferred**. D-142 and the V25 one-use
lifecycle are historical, not current gates. No paid, held-out or B/D execution is currently authorized.

## Next gate

Commit the source-qualified successor, then run one fresh read-only no-call preflight with a new append-only output on
execution-clean source. A READY result would create a secret-free candidate only. Provider execution remains closed
until a separate approval binds that exact new hash, all 48 rows, the `$57.60` reserve and `$60` hard cap.
