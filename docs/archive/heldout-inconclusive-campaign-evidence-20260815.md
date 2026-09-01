# Held-out inconclusive campaign evidence — archived

These exact predecessor tuples are immutable audit evidence, not current authority. Machine artifacts under
`reports/heldout-ac/artifacts/` remain authoritative.

- R7 candidate `sha256:2f51935b...b2afa` consumed `$252`/`$275` and sealed 0 settled/1 unsettled/47 not-started
  after CRLF/LF qualification-byte drift. Its index content/file is
  `sha256:0a421d5baf26abd6fa1092dd6c2c6a5f064950be53ba9a2a3f5fd93b7e639157`/
  `sha256:dd50a53a1c19e1214a575c3b37b82400b8961bf9a38e72f39a2aa87b3390b906` (7,854 bytes).
- R11 candidate `sha256:f48a0de...a6b0` consumed `$252`/`$275` and sealed 2 settled/1 observed-unsettled/
  45 not-started: `$0.15699525` settled, `$0.41801625` observed-started. Historical `CONTRACT_ERROR` is preserved;
  successor diagnosis is `EVALUATOR_CONTROL_CONTRACT_COLLISION`, with zero agent-visible marker matches. Its index
  content/file is `sha256:ff66718e1fa403baf0978de1b0e43625aac0a046117e85c5f42fb0cc4312db9b`/
  `sha256:1badf8a78ba142f9868a3b9e836fa83df7beb0248f9c5e745fd205fd0185f48c` (18,525 bytes).
- R14 candidate `sha256:67475f57...307fd` consumed `$57.60`/`$60` and sealed 0 settled/1 observed-unsettled/
  47 not-started at `$0.126342`. Historical `DURABLE_EVIDENCE_AUTHENTICATION_FAILED` is preserved; successor
  diagnosis is `TRACE_QUALIFICATION_RUNTIME_BUDGET_AUTHORITY_MISMATCH`. Exact final/content/journal hashes are
  `sha256:77a8a129...ed34`/`sha256:1860badb...6619`/`sha256:8f436552...30a6`; index file/content is
  `sha256:21cda8f9...cd7b`/`sha256:1b602c19...5341` (12,856 bytes).

All three are append-only attribution only: zero added runtime calls/cost, no retry/resume, no official analysis and
no memory claim.

R15 candidate `sha256:e11ece5552e2f574ee334ec98a93a9929732df7592096bcd0478717dfd64f8bc` at commit/tree
`2571a7a31bb0071bf1d984ea5e6ff852c1713b13`/`e6d3f6ded652c33eb105c2ee3a24e1dbcdc5a635` consumed one exact
48-row `$57.60`/`$60` approval and sealed 2 settled/1 observed-unsettled/45 not-started. Cost was `$0.2002335`
settled and `$1.112112` observed-started. Historical `DURABLE_EVIDENCE_AUTHENTICATION_FAILED` remains; successor
attribution is `TRACE_QUALIFICATION_V2_TERMINAL_RESULT_SCHEMA_MISMATCH`. Exact final-file/content/journal is
`sha256:6cd811c27ec8533a034f95a40893780a2e90a0b5f1d35ad0a2db950691414269`/
`sha256:d6e78bd93e74aad332e93b24a7d5cacfab397978a52bfea82d59da251eeb05a8`/
`sha256:5459d339d2afc3d309e5c747edcaf0823df0e65fa3618e95c61b3776893be4bb`.
Append-only index `reports/heldout-ac/artifacts/heldout-ac-r15-campaign-inconclusive-r1.json` is 12,209 bytes;
file/content are `sha256:7aaca2be0797ea36f12e125dc85dd582bdc5f63ad5afd7449cc2d2cf77d46c54`/
`sha256:85b211c637eeff05805c8bef1ba3790a6beab8cef98a8680c48fa74f496a56eb`; it added no calls/cost/authority.

None of these candidates or approvals is reusable or transferable.
