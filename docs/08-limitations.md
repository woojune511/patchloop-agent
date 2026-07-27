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
- Second research task admitted: AnyIO #1121, with three hardened-reference passes, 20/20 hidden
  stability runs, 32 P2P regressions, one base hidden failure and five known-bad rejections. Its
  independent oracle rejects a source-equivalent normalization of the original benchmark fix because a
  later upstream incident exposed an expected-outcome lifecycle regression.
- Third research task admitted: tox #3810, with three reference passes, 29 P2P regressions, six
  independent hidden checks, one base hidden failure and five known-bad rejections. Its oracle preserves
  both cross-section empty-substitution and earlier same-section fallback semantics.
- Fourth research task admitted: Hugging Face Hub #3180, with three reference passes, 15 P2P
  regressions, eight independent hidden checks, one base hidden failure and six known-bad rejections.
  Its oracle binds imports to submitted source and limits the allowed public API change to the exact
  endpoint-aware signature delta.
- Fifth research task admitted: PDM #2781, with three normalized production-reference passes,
  36 base-checkout regressions, ten independent hidden checks, one base hidden failure, six semantic
  known-bad rejections and one scope/test-tampering rejection. The benchmark declares 37 P2P nodes
  because one passing parameter exists only in its test patch.
- Sixth research task admitted: pyfakefs #991, with three normalized production-reference passes,
  all 517 declared P2P regressions, 12 independent hidden checks and one base hidden failure. Seven
  semantic partial fixes and one scope/test-tampering patch were rejected. The task is medium, not
  hard; its strength is a clean network-disabled evaluator boundary and broad regression surface.
- Seventh research task admitted: Moto #7208 as development-validation only, with three normalized
  production-reference passes, 182 selected regressions, nine independent hidden checks and one base
  hidden failure. Six semantic partial fixes and one scope/test-tampering patch were rejected. Nine
  endpoint tests outside the benchmark P2P declaration are explicitly deselected; all 173 logical
  P2P nodes expand to 179 network-independent passing cases.
- Eighth research task admitted: Babel #1042 as development-validation only, with three exact
  production-reference passes, all 132 upstream number tests, 16 independent hidden checks and one
  base hidden failure. Seven semantic partial fixes and one scope/test-tampering patch were rejected.
  The task is medium, not hard. Its pinned-image CLDR overlay is explicit and submitted-source binding
  prevents evaluation against the image's baked production module.
- Ninth research task admitted: SQLGlot #7187 as the first core-cross-repo held-out task, with three
  exact production-reference passes, all 39 upstream DuckDB tests, 21 independent hidden checks and
  one base hidden failure. Seven semantic partial implementations and one scope/test-tampering patch
  were rejected. Its hardened oracle covers both NULL modifiers across five value-window functions
  and a representative BigQuery modifier-chain negative-transfer guard. This is deterministic
  evaluator admission evidence, not a live-model core result.
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
- Admitted research tasks are 9/20: memory-development 6/6, development-validation 2/2,
  same-repo core 0/6 and cross-repo core 1/6.
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
