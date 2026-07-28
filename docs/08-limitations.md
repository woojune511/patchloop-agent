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
- Nineteenth research task admitted: Loguru #1297 as the fifth core-same-repo held-out task, with
  three exact-production-reference passes, all 43 base-resident visible tests and 11 independently
  authored hidden cases across five test functions. An implementation-independent
  `utcfromtimestamp()` solution also passed. Base/no-op and all nine semantic partials were rejected;
  one forbidden test edit was rejected by hidden, scope and test-tampering checks. Three
  deterministic, internally consistent fallback profiles cover positive, negative and
  date-rollover-derived offsets so a fixed derived-looking offset or zone cannot satisfy the oracle.
  All 15 official cases ran from clean staging commit
  `8c5084eee3a44a44e207345950a9ffb45b23e4b1` and made zero model/API calls. This is
  deterministic evaluator admission evidence, not live-model agent performance or a core campaign
  result.
- Twentieth research task admitted: pyfakefs #1269 as the sixth core-same-repo held-out task, with
  three exact-production-reference passes over 431 visible passes, 161 skips and 29 independently
  authored hidden cases per run. An implementation-independent dynamic capability interface also
  passed. Base/no-op, all nine semantic partials and one forbidden test edit were rejected; the
  forbidden edit also failed scope and test-tampering checks. All 15 official cases ran from clean
  staging commit `b50b4314aa7fd209737db46f15b38aee056bbd80` and made zero model/API
  calls. This completes the 20-task research role target but is deterministic evaluator evidence,
  not live-model agent performance or a core campaign result.
- Worker-kill recovery with duplicate-mutation assertion
- One-run offline experiment and raw-derived report
- Unit/integration/recovery/viewer route tests
- Frozen 25-package dataset manifest with 5/5 calibration, 20/20 research roles, three selected
  stress sentinels and a deterministically expanded 30-run schedule. `patchloop dataset audit`
  reports `complete=true` with no freeze blockers.

## Implemented but not yet accepted as an external gate

- OpenAI Responses adapter is contract-tested with a fake client; no paid live model call was made.
- `experiment-v2` now distinguishes offline smoke, Babel development-validation live pilot,
  memory-development no-memory campaign and core purpose. The live templates fix the pilot to
  `no_memory` × 1 with a $2 cap and the six development tasks to `no_memory` × 2 = 12 runs with a
  $20 cap. This is an execution contract, not a completed experiment.
- A no-call preflight checks frozen dataset identity/role, canonical task package path,
  public/private spec hash, digest-pinned environment and observed Docker identity, clean Git
  commit, OpenAI SDK and API-key presence without the value, absence of a custom base URL,
  Terra medium/standard/default settings, 72-hour official pricing and budget reserve. Paid
  authorization is invocation-only and bound to its execution hash. A live capability is issued
  only after the approved plan is durably persisted. Current-machine readiness has not yet been
  accepted; one or more environment blockers may remain.
- The campaign journal is append-only and hash-chained. It fsyncs `CampaignStarted` and each
  stable-ID `RunStarted` before the corresponding model-call scope, so a hard crash leaves a guard
  that blocks automatic schedule replay. Automatic resume from an interrupted journal is not
  implemented, and this path has no paid-run evidence yet.
- `trace-qualification-v1` checks approved-plan binding, required content-addressed artifact
  references, event/checkpoint/result integrity, usage reconciliation, public/private leakage and
  pilot tool-loop evidence. Its `source_evidence_hash` binds plan, manifest, events, checkpoints,
  result and agent-visible artifact inventory and is recalculated at review/index admission. Only
  qualified memory-development failures are eligible for append-only human review; classifier
  output omits hidden check IDs. No live qualification artifact exists yet.
- Cache usage enforces `cached + cache-write <= input`, and a malformed billed function-call
  response preserves usage/cost before terminating as agent failure. These are contract-tested
  paths, not paid-provider evidence.
- Reports mark incomplete or qualification-failed matrices `analysis_ready=false`, keep
  available-case rows only as diagnostics and suppress headline, paired comparison/CI and flip
  results. No live matrix has yet exercised this reporting boundary.
- Failed started attempts are designed to retain run ID, usage including cached/cache-write tokens,
  calculated cost and terminal outcome. This persistence path has no paid-run evidence yet.
- Memory build/retrieval/freeze contracts exist; a real reviewed index still requires admitted
  memory-development traces and an exact embedding revision. Calibration traces are not eligible.
- GitHub adapters exist; no Issue was imported and no Draft PR was created in this session.
- HTMX is pinned from a CDN; fully offline viewer packaging would require vendoring the BSD asset.
- Digest-pinned external SWE-rebench evaluator images currently inherit the image's configured user.
  The AnyIO #1134, Param #1117, Hugging Face Hub #4056, MTPLX #21, FuseSoC #776, tox #3846,
  Dagster #33605, Kubeflow Pipelines #13112, Loguru #1297 and pyfakefs #1269 images have no
  configured `User` and
  therefore ran
  as Docker's default root user.
  Network denial, a read-only root filesystem and a read-only submitted workspace were enforced,
  but uniform non-root execution for arbitrary external images is not yet implemented. The native
  PatchLoop image's non-root isolation smoke does not prove this property for external images.
- Evaluator `result.json` records an opaque `submitted_patch_artifact_id`, but the current
  `ArtifactStore` does not persist a standalone ID-to-content-hash catalog for that field. Admission
  evidence remains byte-resolvable through the persisted `provenance.diff_hash` and corresponding CAS
  object, but direct lookup by the opaque artifact ID alone is not yet implemented.
- Tracked admission reports bind each raw `manifest.json`, `result.json` and `provenance.json` by
  SHA-256, but those per-run files currently remain under the ignored local `.patchloop/artifacts`
  store. A clean checkout can validate the report and rerun the deterministic gate, but cannot rehash
  the original raw run files until a portable evidence bundle is exported. This limitation applies
  to the existing admission-report family and must be closed before claiming clean-checkout raw
  evidence inspection.
- `RunManifest.harness_git_commit` records the harness `HEAD` but not a full dirty-tree hash.
  The new live-suite preflight rejects a dirty worktree before execution; older admission gates used
  manually verified clean staging commits and are not retroactively covered by that enforcement.

## Dataset freeze completed; campaign not yet completed

- The calibration fixture set is complete at 5/5, but it is excluded from memory, core metrics and
  portfolio performance headlines.
- The dataset manifest contains 25 packages: five calibration fixtures and 20 admitted research tasks.
  All research role targets are filled: memory-development 6/6, development-validation 2/2,
  same-repo core 6/6 and cross-repo core 6/6. It is frozen at
  `sha256:cf608ca1a35cb270f2e4cadcf0b34912256ef1c9cd3c0757a89692f8a5fdf786`;
  the machine audit reports `research_ready=true`, `stress_ready=true` and `complete=true`.
- The Terminal-Bench-inspired stress contract selects FuseSoC #776, AnyIO #1134 and pyfakefs #1269
  from public task structure only. Its 30-run schedule is frozen at
  `sha256:d5a3d90f8429f24b6940d4a5cb1b78a35fa34d3fe3df9937ad6c57daba23f468`
  and remains excluded from core metrics. None of those 30 runs has been executed.
- The frozen schedule is a preregistered contract, not proof that the stress runtime is complete.
  The after-model-call-10 context-reset trigger, the `persistent_state=off` arm and a stress
  matrix runner/report are not implemented.
- The existing worker-kill path cooperatively suspends a run after the first durable patch
  checkpoint; it does not terminate an external operating-system worker process.
- The existing timeout injector synthesizes one timeout on the first registered visible check.
  It does not yet reproduce a real environment hang or specifically target a full-suite check.
- The six `python-tabulate` rows remain candidate inventory in `data/oss-candidate-ledger.csv`; none is
  an admitted research task.
- No Terminal-Bench original or constrained coding adaptation has passed PatchLoop admission. Any future
  original benchmark run is external acceptance evidence, not a core result.
- No 96-run OpenAI campaign, cost measurement, negative-transfer review or live-model cross-repo
  result exists.
- No $2 Babel live pilot or $20/12-run no-memory development campaign has been executed. The
  2026-07-28 configured official rates—$2.50/M input, $0.25/M cached input, $3.125/M cache-write
  input and $15/M output—must be refreshed if older than 72 hours at invocation. Only the
  `gpt-5.6-terra` alias, not a dated Terra snapshot, is currently recorded.
- The six scripted offline runs validate harness plumbing, not model capability or memory effectiveness.
  No portfolio performance claim about a live model should be made from them.

These are deliberate hard gates. The repository rejects an incomplete core experiment manifest instead of
silently lowering the design or fabricating missing results.
