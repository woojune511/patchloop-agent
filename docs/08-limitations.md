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
- Tenth research task admitted: PDM #3759 as the first core-same-repo held-out task, with three
  hardened-reference passes, 63 network-independent upstream regressions, 11 independent hidden checks
  and one base hidden failure. The exact benchmark production patch and eight other semantic partials
  were rejected, as was one scope/test-tampering edit. One declared P2P node that attempts an external
  install is explicitly deselected. This is deterministic evaluator admission evidence, not a
  live-model core result.
- Eleventh research task admitted: AnyIO #1134 as the second core-same-repo held-out task, with
  three exact-production-reference passes, all 36 upstream process regressions, 11 independent
  hidden checks and one base hidden failure. Nine semantic partial implementations were rejected,
  as was one scope/test-tampering edit. Its worker bootstrap lineage is distinct from the AnyIO
  #1121 development task. This is deterministic evaluator admission evidence, not a live-model
  core result.
- Twelfth research task admitted: Param #1117 as the second core-cross-repo held-out task, with
  three exact-production-reference passes, all 94 upstream reactive regressions, ten independent
  hidden checks and one base hidden failure. Eight semantic partial implementations and one
  scope/test-tampering edit were rejected. Its digest-pinned evaluator image is
  `sha256:c10bc0ad51b00c59ed8fa4366ee722c38e83dfaa620a7cc229f78489ccbaf010`.
  This is deterministic evaluator admission evidence, not a live-model core result.
- Thirteenth research task admitted: Hugging Face Hub #4056 as the third core-same-repo held-out
  task, with three exact-production-reference passes, 17 base-resident upstream regressions,
  15 independent hidden cases and one base hidden failure. Nine semantic partial implementations
  and one scope/test-tampering edit were rejected. Two of the benchmark's 19 declared P2P nodes
  exist only in the excluded benchmark test patch, so the executed and declared counts are
  reported separately. An adversarial pre-gate review found and closed a combined-partial oracle
  escape before admission. This is deterministic evaluator evidence, not a live-model core result.
- Fourteenth research task admitted: MTPLX #21 as the third core-cross-repo held-out task, with
  three hardened-reference passes, 55 base-resident OpenAI bridge regressions, 21 independent
  hidden cases and one base hidden failure. Nine semantic implementations, including the exact
  upstream accepted source patch, were rejected, as was one scope/test-tampering edit. The hardened
  oracle requires an exact `<tool_call>` delimiter, preserves lookalike tags as content and rejects
  non-whitespace residue beside or between streamed calls. This is deterministic evaluator admission
  evidence, not a live-model core result.
- Fifteenth research task admitted: FuseSoC #776 as the fourth core-cross-repo held-out task, with
  three exact-production-reference passes, 12 selected base-resident regressions, ten independent
  hidden cases and one base/no-op hidden failure. Eight semantic partial implementations were
  rejected by hidden acceptance, and one forbidden test edit was rejected by hidden, scope and
  test-tampering checks. The visible suite collects 14 tests but explicitly deselects one
  network-dependent export test and one lockfile test incompatible with the read-only submitted
  filesystem. This is deterministic evaluator admission evidence, not a live-model core result.
- Sixteenth research task admitted: tox #3846 with follow-up #3851 as the fourth core-same-repo
  held-out task, with three hardened-reference passes, 101 selected visible regressions and
  17 independent hidden cases across eight test functions. Base/no-op and ten semantic partials,
  including each accepted PR in isolation, were rejected; one forbidden test edit was rejected by
  hidden, scope and test-tampering checks. The visible surface is 99 passing cases plus two explicitly
  re-included healthy siblings out of 110 declared P2P nodes. This is deterministic evaluator
  admission evidence, not a live-model core result.
- Seventeenth research task admitted: Dagster #33605 as the fifth core-cross-repo held-out task,
  with three exact-production-reference passes, all 28 base-resident visible regressions and nine
  independently authored hidden tests. Base/no-op and all eight semantic partials were rejected;
  one forbidden test edit was rejected by hidden, scope and test-tampering checks. The
  `task-private-v2` content hash binds the hidden oracle, and both visible tests and the hidden
  oracle remain on read-only mounts while submitted production source is copied to a fresh
  writable import root. All 13 official cases made zero model/API calls. This is deterministic
  evaluator admission evidence, not live-model agent performance or a core campaign result.
- Eighteenth research task admitted: Kubeflow Pipelines #13112 as the sixth core-cross-repo
  held-out task, with three exact-production-reference passes, all 277 base-resident visible tests,
  15 subtests and 11 independently authored hidden tests. Base/no-op and all eight semantic partials
  were rejected; one forbidden test edit was rejected by hidden, scope and test-tampering checks.
  The frozen benchmark declares 278 P2P nodes because its test patch adds one preservation P2P case;
  the base-resident declared P2P surface is therefore exactly 277. The `task-private-v2` content
  hash binds the hidden oracle, and both visible tests and the hidden oracle remain on read-only
  mounts while submitted production source is copied to a fresh writable import root. All 13
  official cases ran from clean staging commit
  `5e7b019e60b4d76f67e48bafe6fd1a3b309fe313` and made zero model/API calls. This is deterministic
  evaluator admission evidence, not live-model agent performance or a core campaign result.
- Worker-kill recovery with duplicate-mutation assertion
- One-run offline experiment and raw-derived report
- Unit/integration/recovery/viewer route tests

## Implemented but not yet accepted as an external gate

- OpenAI Responses adapter is contract-tested with a fake client; no paid live model call was made.
- Memory build/retrieval/freeze contracts exist; a real reviewed index still requires admitted
  memory-development traces and an exact embedding revision. Calibration traces are not eligible.
- GitHub adapters exist; no Issue was imported and no Draft PR was created in this session.
- HTMX is pinned from a CDN; fully offline viewer packaging would require vendoring the BSD asset.
- Digest-pinned external SWE-rebench evaluator images currently inherit the image's configured user.
  The AnyIO #1134, Param #1117, Hugging Face Hub #4056, MTPLX #21, FuseSoC #776, tox #3846,
  Dagster #33605 and Kubeflow Pipelines #13112 images have no configured `User` and therefore ran
  as Docker's default root user.
  Network denial, a read-only root filesystem and a read-only submitted workspace were enforced,
  but uniform non-root execution for arbitrary external images is not yet implemented. The native
  PatchLoop image's non-root isolation smoke does not prove this property for external images.
- Evaluator `result.json` records an opaque `submitted_patch_artifact_id`, but the current
  `ArtifactStore` does not persist a standalone ID-to-content-hash catalog for that field. Admission
  evidence remains byte-resolvable through the persisted `provenance.diff_hash` and corresponding CAS
  object, but direct lookup by the opaque artifact ID alone is not yet implemented.

## Dataset and campaign not yet produced

- The calibration fixture set is complete at 5/5, but it is excluded from memory, core metrics and
  portfolio performance headlines.
- The dataset manifest contains 23 packages: five calibration fixtures and 18 admitted research tasks.
  Research admission is 18/20: memory-development 6/6, development-validation 2/2,
  same-repo core 4/6 and cross-repo core 6/6. The remaining two research tasks are not admitted.
- No three-sentinel Terminal-Bench-inspired stress overlay has been selected or frozen.
- The six `python-tabulate` rows remain candidate inventory in `data/oss-candidate-ledger.csv`; none is
  an admitted research task.
- No Terminal-Bench original or constrained coding adaptation has passed PatchLoop admission. Any future
  original benchmark run is external acceptance evidence, not a core result.
- No 96-run OpenAI campaign, cost measurement, negative-transfer review or live-model cross-repo
  result exists.
- The six scripted offline runs validate harness plumbing, not model capability or memory effectiveness.
  No portfolio performance claim about a live model should be made from them.

These are deliberate hard gates. The repository rejects an incomplete core experiment manifest instead of
silently lowering the design or fabricating missing results.
