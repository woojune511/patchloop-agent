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

Held-out R14 candidate `sha256:67475f578338026bc0c66ff3904ef1adfaaae8a33e2cba824d0f88a5d57307fd`
consumed one exact 48-row `$57.60`/`$60` approval. It sealed `inconclusive`: 0 settled, 1 observed-unsettled and 47
not started, with `$0.126342` observed-started model cost. It cannot retry, resume, reauthenticate, reclassify or
transfer approval; no official held-out analysis or memory claim follows.

Held-out R15 candidate `sha256:e11ece5552e2f574ee334ec98a93a9929732df7592096bcd0478717dfd64f8bc`
consumed a separate 48-row `$57.60`/`$60` approval. It sealed `inconclusive` after 3 starts: 2 settled,
1 observed-unsettled and 45 not started. Settled cost was `$0.2002335`; total observed-started cost was `$1.112112`.
It cannot retry, resume, reauthenticate, reclassify or transfer approval.

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

## R14 failure attribution

The immutable runtime reason remains `DURABLE_EVIDENCE_AUTHENTICATION_FAILED` in phase `authentication`.
Append-only deterministic diagnosis attributes the contract stop to
`TRACE_QUALIFICATION_RUNTIME_BUDGET_AUTHORITY_MISMATCH`: trace-qualification-v2 correctly recorded the approved
candidate budget (1M input, 100k output, 1.1M total), while the completion path compared it with the immutable suite
budget (4M/500k/4.5M). This does not relabel the historical reason, reauthenticate the row or change its underlying
hidden FAIL. The R14 evidence index added zero calls and `$0` cost.

## R15 failure attribution

Rows 1 and 2 settled. Row 3 hit the approved model-generation budget before submission; its persisted v2 result
correctly used the sanitized terminal error `{code: AGENT_SUBMISSION_FAILED, phase: agent}` and its blocked/RunFailed
events carried `MODEL_GENERATION_BUDGET_EXCEEDED`. The old trace qualifier incorrectly required the richer v1 terminal
shape for v2, so authentication stopped with historical `DURABLE_EVIDENCE_AUTHENTICATION_FAILED`.

The version-aware repair preserves exact v1 behavior and binds v2's sanitized result to the exact blocked and
RunFailed events. `TRACE_QUALIFICATION_V2_TERMINAL_RESULT_SCHEMA_MISMATCH` is a post-runtime attribution only; the
historical row was not reauthenticated or reclassified. The append-only R15 index made zero runtime calls and added
`$0` cost.

## Evaluator correctness gap

Evaluator-v1 still assigns literal safety PASS. V2 binds typed evidence, fail-closed verdicts, durable receipts and
qualification while raw v2 results remain `official=false`. R8 is the first complete receipt-qualified four-row
development-readiness matrix; this validates the exact path, not production security, held-out generalization or a
memory effect.

The successor uses candidate-v3. Its `realized_schedule_hash` binds every ordered row and task/evaluator identity;
runtime tuple and cost controls bind the candidate rather than the immutable suite. A current next row requires a
persisted-v5 wrapper and persisted-row-v2, then revalidates runtime/cost hashes, semantic usage/result bindings and all
budgets. Known R7/R11/R14/R15 replay is accepted only for each exact final-file/content/journal SHA triple. Persisted DTOs
remain unofficial; only runtime-authenticated non-serialized provenance can reach analysis.

Development-only evidence lowered equal A/C to 1M/100k/1.1M tokens, `$1.20`/row and `$57.60`/`$60`; held-out outcomes
and task content were excluded, and results cannot pool with R11, R14 or R15. Current Contract R11 → binding R11 →
materialization R7 → execution R8 → preflight R16 is source-qualified but zero-authority.

## Evidence, retry and authority

Completed evidence is append-only. R3-R8 development and held-out R7/R11/R14/R15 cannot retry, resume, overwrite or
transfer approval. Reusable no-call preflight allows at most three transient pre-provider attempts without state
artifacts or per-attempt approval prose; paid campaign identity is separately one-use across readiness timestamps.

D-142 remains **source-qualified only, unactivated**; its planning disposition is now **deferred**.
D-142 and the V25 one-use lifecycle are historical, not current gates.
No paid, held-out or B/D execution is currently authorized.

## Next gate

Commit the R11/R11/R7/R8/R16 source-qualified successor, then run one fresh read-only no-call preflight with a new
append-only output on execution-clean source. A READY result would create a secret-free candidate only. No candidate
or approval exists now; provider execution remains closed until separate approval binds that exact new hash, all 48
rows, the `$57.60` reserve and `$60` hard cap.
