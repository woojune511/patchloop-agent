# Current limitations

This file separates implemented behavior from the remaining 12-week campaign work.

## Implemented and measured locally

- Five audited `mini-data-utils` calibration fixtures with independent snapshot hashes
- Reviewed reference and known-bad evaluator paths for every calibration fixture
- Official Linux Docker evaluator smoke: three references accepted, 14 known-bad patches rejected
- Docker network denial, non-root UID, read-only workspace and host-secret non-forwarding checks
- Official Docker-evaluated offline agent smoke: three tasks under both mock and content-hashed replay,
  six of six runs accepted with complete persisted usage and trace evidence
- Duration-minute boundary and CSV EOF-finalization fixture references accepted, with four known-bad
  patches rejected per task by the pinned Docker evaluator
- First SWE-rebench-derived research task admitted: Loguru #1451, with an immutable official image,
  three reference passes, 20 upstream regressions, one base hidden failure and five known-bad rejections
- Worker-kill recovery with duplicate-mutation assertion
- One-run offline experiment and raw-derived report
- Unit/integration/recovery/viewer route tests

## Implemented but not yet accepted as an external gate

- OpenAI Responses adapter is contract-tested with a fake client; no paid live model call was made.
- Memory build/retrieval/freeze contracts exist; a real reviewed index still requires admitted
  memory-development traces and an exact embedding revision. Calibration traces are not eligible.
- GitHub adapters exist; no Issue was imported and no Draft PR was created in this session.
- HTMX is pinned from a CDN; fully offline viewer packaging would require vendoring the BSD asset.

## Dataset and campaign not yet produced

- The calibration fixture set is complete at 5/5, but it is excluded from memory, core metrics and
  portfolio performance headlines.
- Admitted research tasks are 1/20: memory-development 1/6, development-validation 0/2,
  same-repo core 0/6 and cross-repo core 0/6.
- No three-sentinel Terminal-Bench-inspired stress overlay has been selected or frozen.
- The six `python-tabulate` rows remain candidate inventory in `data/oss-candidate-ledger.csv`; none is
  an admitted research task.
- No Terminal-Bench original or constrained coding adaptation has passed PatchLoop admission. Any future
  original benchmark run is external acceptance evidence, not a core result.
- No 96-run OpenAI campaign, cost measurement, negative-transfer review or cross-repo result exists.
- The six scripted offline runs validate harness plumbing, not model capability or memory effectiveness.
  No portfolio performance claim about a live model should be made from them.

These are deliberate hard gates. The repository rejects an incomplete core experiment manifest instead of
silently lowering the design or fabricating missing results.
