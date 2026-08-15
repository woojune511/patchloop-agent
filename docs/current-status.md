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

Held-out R16 candidate `sha256:24044c1ed525458446f1c97d94f52331082d74051f5c6d680da995ea9aa48813`
consumed a new exact 48-row `$57.60`/`$60` approval and completed the preregistered matrix: 48 settled, 0
observed-unsettled, 0 not started and 0 confounded. Cost accounting is complete at `$27.24465825`, with no retry,
replacement or resume. The result contains 15 resolved, 14 task-failure and 19 typed agent-failure rows.

Its authenticated persisted completion unlocked official analysis for this frozen panel. No-memory succeeded on 8/24
rows and structured on 7/24; structured minus no-memory is `-1/24` (-4.17 percentage points). The deterministic
task-cluster stability interval is `[-1/4, 1/6]`, and the sign-flip sensitivity reference is `p=1`. These are
descriptive frozen-panel quantities, not a population confidence interval, causal effect or general memory-benefit
claim. Same-repo effect is 0; cross-repo effect is `-1/12`; benefit/negative-transfer flips are 3/24 and 4/24.

## Preserved predecessor diagnoses

- R11 keeps historical `CONTRACT_ERROR`; append-only attribution is `EVALUATOR_CONTROL_CONTRACT_COLLISION` with zero
  agent-visible marker matches. Correcting evaluator-private redaction does not change its hidden failure.
- R14 keeps `DURABLE_EVIDENCE_AUTHENTICATION_FAILED`; append-only
  `TRACE_QUALIFICATION_RUNTIME_BUDGET_AUTHORITY_MISMATCH` records candidate 1M/100k/1.1M versus suite
  4M/500k/4.5M.
- R15 keeps the same historical campaign reason; append-only
  `TRACE_QUALIFICATION_V2_TERMINAL_RESULT_SCHEMA_MISMATCH` binds its sanitized v2 budget terminal to exact typed
  failure events. None of these indices reauthenticates, reclassifies, settles or reruns a row; all added zero calls
  and `$0` cost.

## Evaluator correctness gap

Evaluator-v1 still assigns literal safety PASS. V2 binds typed evidence, fail-closed verdicts, durable receipts and
qualification while raw v2 results remain `official=false`. R8 is the first complete receipt-qualified four-row
development-readiness matrix; this validates the exact path, not production security, held-out generalization or a
memory effect.

The successor uses candidate-v3. Its `realized_schedule_hash` binds every ordered row and task/evaluator identity;
runtime tuple and cost controls bind the candidate rather than the immutable suite. A current next row requires a
persisted-v5 wrapper and persisted-row-v2, then revalidates runtime/cost hashes, semantic usage/result bindings and all
budgets. Known legacy R7/R11/R14/R15 replay is accepted only for each exact final-file/content/journal SHA triple.
Persisted DTOs
remain unofficial; only runtime-authenticated non-serialized provenance can reach analysis.

Development-only evidence lowered equal A/C to 1M/100k/1.1M tokens, `$1.20`/row and `$57.60`/`$60`; held-out outcomes
and task content were excluded when that amendment was made. Contract R11 → binding R11 → materialization R7 →
execution R8 → preflight R16 is the consumed source chain for the completed R16 campaign. Its qualification artifacts
were zero-authority; the later candidate and approval were separate and are now consumed.

## Evidence, retry and authority

Completed evidence is append-only. R3-R8 development and held-out R7/R11/R14/R15/R16 cannot retry, resume, overwrite
or transfer approval. The R16 index binds exact source/runtime files and official analysis while adding no calls or
cost. Reusable no-call preflight allows at most three transient pre-provider attempts without state artifacts or
per-attempt approval prose; paid campaign identity is separately one-use across readiness timestamps.

D-142 remains **source-qualified only, unactivated**; its planning disposition is now **deferred**.
D-142 and the V25 one-use lifecycle are historical, not current gates.
No paid, held-out or B/D execution is currently authorized.

## Next gate

Preserve the completed R16 matrix and its append-only index; do not rerun, resume or tune against this unblinded panel.
The next experiment, if any, must first define a separate preregistered design and fresh held-out panel, then qualify
its exact source before any no-call candidate or approval. B/D remain deferred. No current candidate, approval or
provider execution is authorized.
