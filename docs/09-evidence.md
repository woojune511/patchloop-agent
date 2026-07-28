# Implementation evidence — through 2026-07-28

This is a local implementation checkpoint, not the planned core experiment result.

## Executed gates

| Gate | Command | Outcome |
| --- | --- | --- |
| Lock consistency | `uv --cache-dir .patchloop/uv-cache lock --check` | pass, 78 packages resolved |
| Static analysis | `.venv/Scripts/ruff check . --no-cache` | pass |
| Tests | `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q -p no:cacheprovider` | 224 passed, 2 skipped |
| Package build | `uv build` | sdist and wheel built |
| Task contract | `patchloop task validate tasks/<split>/<task>` | five calibration plus twenty research packages pass |
| Dataset audit | `patchloop dataset audit` | pass: frozen 25-task manifest, research 20/20, stress 3/3, 30 derived runs, no blockers |
| Docker build | pinned base, `--network=none --provenance=false`, repeated twice | stable image ID in 2/2 builds |
| Docker isolation (native image) | network, UID, read-only workspace, host secret | all pass; external benchmark-image user remains separately disclosed |
| Research admission | Loguru #1451/#1297, AnyIO #1121/#1134, tox #3810/#3846+#3851, Hugging Face Hub #3180/#4056, PDM #2781/#3759, pyfakefs #991/#1269, Moto #7208, Babel #1042, SQLGlot #7187, Param #1117, MTPLX #21, FuseSoC #776, Dagster #33605 and Kubeflow Pipelines #13112 references ×3 plus declared negatives | research role target 20/20; references pass; all negative cases rejected; all `official=true` |
| Offline agent smoke | three tasks × mock/replay on Docker | 6/6 SCRR pass, complete trace, all `official=true` |
| Offline campaign | `patchloop evaluate --suite experiments/smoke.yaml` | 1/1 completed, 0 infra errors |
| Report regeneration | `patchloop report --experiment offline-smoke ...` | JSON/CSV/HTML and portable evidence bundle |
| Viewer routes | six ASGI route requests | all HTTP 200 |
| Portable bundle scan | username, absolute workspace, private/reference path scan | pass |

Latest bundled offline run: `run_671aa408ac4241ca`.

- SCRR: pass
- hidden: pass
- regression: pass
- scope: pass
- official: false
- model calls: 5 mock calls
- tool calls: 4
- measured active wall time: 1,144 ms

The one-task bootstrap interval `[1.0, 1.0]` is mechanically correct but not inferentially useful. It must
not be presented as benchmark evidence.

## Official offline agent smoke evidence

Commit `1ea257cbbcc2ce131b5c09508f6df8c62ed23ed8` was run against the pinned Docker evaluator.
Each of the three smoke tasks completed once with the task-aware mock and once with its checked-in,
content-hashed replay.

| Task | Mock run | Replay run | Observed |
| --- | --- | --- | --- |
| `csv-quoted-newline` | `run_5cd7103a1c6f4d7a` | `run_c468655d03ed4d08` | 2/2 SCRR pass, `official=true` |
| `config-falsy-override` | `run_1492e28b07dd4feb` | `run_403b92ac32264725` | 2/2 SCRR pass, `official=true` |
| `path-prefix-boundary` | `run_27339c856bee4242` | `run_bd06edd18bc9434f` | 2/2 SCRR pass, `official=true` |

Every accepted run records five model calls, four tool calls, five rebuilt contexts, one `PatchApplied`,
one `RunCompleted` and a final `DONE` checkpoint. Persisted `result.json` usage equals SQLite state.
The context scan found no hidden check ID or reference-patch locator; the first context also excludes the
private reference hash. Replay manifests bind the repository-relative JSONL path to its SHA-256.

The machine-readable [offline agent smoke summary](../reports/offline-agent-smoke/summary.json) records
run IDs plus manifest, result, provenance, submitted-patch, event-stream and checkpoint hashes. It also
keeps an exclusion ledger for one non-official Docker-daemon diagnostic run and six pre-fix runs whose
persisted result artifact omitted agent usage. Those runs were not counted in the 6/6 gate.

These are deterministic scripted runs with zero API calls and zero model cost. They establish harness,
trace and evaluator behavior; they are not evidence of live-model quality or memory effectiveness.

## Official Docker evaluator evidence

The pinned base image is
`python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de`.
Two network-disabled builds with BuildKit provenance disabled produced the same evaluator image ID:
`sha256:5d430c8dbf2e1222148909ed4c79c3cbf212aa25a94c8c2d0cbd0a97adfccf1f`.

| Fixture | Final run | Expected boundary | Observed |
| --- | --- | --- | --- |
| reference | `run_251d172b049e49c3` | full success | success |
| no-op | `run_8da6d410add948e4` | hidden fail | rejected |
| regression | `run_9b86d529fd57493b` | regression fail | rejected |
| forbidden path | `run_9328887b3bfc4d12` | scope fail | rejected |
| dependency | `run_e68390d517824e4b` | dependency/scope fail | rejected |
| test tampering | `run_2f57822c729348c1` | tampering/scope fail | rejected |
| public API | `run_a7771fc59af24470` | public-API/scope fail | rejected |

The machine-readable [Docker gate summary](../reports/docker-gate/summary.json) records the immutable
manifest, result and provenance hashes for these runs. This evidence covers one smoke task, not the planned
held-out dataset or model campaign.

Every final Docker gate manifest records baseline commit
`cf38649bbbf458316f38e64a579fd0196c782237`; no run in the machine-readable summary uses an uncommitted
harness identifier.

## Smoke task expansion evidence

Two additional independently content-addressed snapshots were frozen in commit
`024a3a375dc9514be6d127199d10f7115659eecf`.

| Task | Reference run | Known-bad corpus | Observed |
| --- | --- | --- | --- |
| `config-falsy-override` | `run_57c437c24e154317` | no-op, partial falsey fix, regression, forbidden path | reference passed; 4/4 rejected |
| `path-prefix-boundary` | `run_395efa14bc7c4e59` | no-op, boundary-only fix, regression, forbidden path | reference passed; 4/4 rejected |

All ten expansion runs record the task commit and the same pinned evaluator image as the CSV gate. The
[smoke expansion summary](../reports/docker-gate/smoke-expansion.json) records task/spec hashes, run IDs
and manifest/result/provenance hashes. Together, the three smoke tasks cover parser state, merge semantics
and path normalization without sharing a solution.

## First additional calibration fixture

`duration-minute-boundary` is the first `dev-train` package. Its immutable snapshot keeps exact-minute
and sub-minute visible behavior working while deliberately rounding incomplete minute buckets upward.
The private acceptance checks values inside and near the end of those buckets.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| reference | `run_4c333240f3ae4a26` | full success | success, `official=true` |
| no-op | `run_02cdf575981042d5` | hidden fail | rejected |
| near-miss | `run_18b131fb74a84d1a` | hidden fail | rejected |
| regression | `run_51bc997fa1394e20` | visible regression fail | rejected |
| forbidden path | `run_a5b492be61d2433d` | hidden and scope fail | rejected |

All five manifests record clean harness commit `6152e9b207ee615f5c1dd0ec8dbefc09f075f951`
and the pinned evaluator image. The machine-readable
[dev-train task gate](../reports/docker-gate/dev-train-duration-minute-boundary.json) records task/spec,
patch, manifest, result and provenance hashes. This is calibration evidence, not a model run; it
made zero API calls and does not create a memory entry. A clean clone reproduced the declared snapshot
hash `sha256:a3508607ed05735c39f766580002fa29801440ee66301fbc85b1525114f079fe`.

## Second additional calibration fixture

`csv-final-record-flush` uses a separate chunked-parser API and source file from the multiline-CSV smoke
task. Its base snapshot handles newline-terminated records, chunk boundaries and quoted commas, but does
not finalize the remaining valid record when input reaches EOF.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| reference | `run_b01dedac6de84caa` | full success | success, `official=true` |
| no-op | `run_aad5c6d582d24e40` | hidden fail | rejected |
| near-miss | `run_6992b1281550416c` | hidden fail | rejected |
| regression | `run_4db275cfe376444f` | visible regression fail | rejected |
| forbidden path | `run_32865f2f94754584` | hidden and scope fail | rejected |

All five manifests record clean harness commit `76471df95e26857f42662b7514fa31896a5496a2`
and the pinned evaluator image. The machine-readable
[CSV final-record gate](../reports/docker-gate/dev-train-csv-final-record-flush.json) records task/spec,
patch, manifest, result and provenance hashes. This fixture gate made zero API calls and creates no memory
entry. A clean clone reproduced snapshot hash
`sha256:afa42fe0bcb75bc7f0f7969e394433d5c8e9c8ce34232ebbf5bb5416c2bcd680`.

## First research task admission

`loguru-invalid-format-feedback` comes from SWE-rebench leaderboard instance
`delgan__loguru-1451`, upstream issue #1450 and PR #1451. It is registered as
`memory-development`, not held-out. The source is pinned to Loguru commit
`2abeb0fa6d7be4b0455c6e0b580b1e9dab19005e`; the upstream resolution is
`b782e56fcf07fecf9545ff6ee2350baacb0968ce`.

The evaluator uses the official task environment at immutable digest
`sha256:181bd51aa34ebe84d749819dfbe9a2d3d215ff8f6406d897d790f876bc5f36db`.
Every run is network-disabled and uses harness commit
`d7cdd6fa1055311275ff4c8751051f47bb118ed5`.

| Patch | Runs | Expected boundary | Observed |
| --- | --- | --- | --- |
| reference | `run_da8b68a7ed544b20`, `run_528b24d9038e47d5`, `run_63e461ef353b4756` | full success ×3 | 3/3 success, `official=true` |
| no-op | `run_0766fe431389477d` | base visible pass, hidden fail | rejected |
| generic diagnostic | `run_70725e940deb4260` | hidden diagnostic-content fail | rejected |
| catch-true only | `run_6ca5cfe1e4d84d88` | hidden catch-false fail | rejected |
| hardcoded reproduction | `run_51a443c8c3484b7b` | hidden alternate-key fail | rejected |
| swallowed catch-false | `run_67209fa6a07844cc` | hidden propagation fail | rejected |
| forbidden README edit | `run_f2cb40457ecb494d` | hidden and scope fail | rejected |

The upstream `tests/test_add_option_format.py` file reported 20 passes on each reference run. PatchLoop's
independently authored hidden oracle additionally checks both catch modes, actionable diagnostic content
and patcher-injected keys. The machine-readable
[research admission report](../reports/docker-gate/research-loguru-invalid-format-feedback.json) records
all manifest, result, patch and provenance hashes. It made zero API calls and is evaluator evidence, not
live-model performance.

## Second research task admission

`anyio-interrupt-runner-cleanup` comes from SWE-rebench instance
`agronholm__anyio-1121`, AnyIO issue #1060 and PR #1121. It is a hard
`memory-development` task pinned to base commit
`cb245dba9883516f2ed4c23899de157183a1cb50` and evaluator image
`sha256:063bb968109c70a3fe617d9d30287a3a43d549eb1091b27a030a9af2a74c2320`.

The original upstream fix stopped an interrupted async test from resuming during fixture teardown.
Follow-up issue #1179 and PR #1180 later showed that the same handler incorrectly reset the runner for
normal pytest `OutcomeException` signals. PatchLoop therefore uses a hardened reference that preserves
both behaviors, and treats a source-equivalent normalization of the original fix as a known-bad patch.

| Patch | Runs | Expected boundary | Observed |
| --- | --- | --- | --- |
| hardened reference | `run_4b93be1d3b664ee4`, `run_127a2daf82c14f3b`, `run_863bf64317894ade` | full success ×3 | 3/3 success, `official=true` |
| no-op | `run_bcf39b1790d94d8f` | P2P pass, hidden no-resume fail | rejected |
| cancel without drain | `run_0e57530dd1f9485b` | hidden lifecycle fail | rejected |
| drop runner reference only | `run_48d940b39f694567` | hidden stale-task fail | rejected |
| swallow interrupt | `run_f572a38ce28446d6` | hidden propagation fail | rejected |
| normalized upstream fix | `run_3fc2bd62bc9d4a9e` | hidden expected-outcome lifecycle fail | rejected |
| forbidden test edit | `run_a888124ac80a47f7` | hidden, scope and tampering fail | rejected |

The 32 benchmark P2P tests passed on base and reference. Three unrelated upstream tests that need the
optional `hypothesis` package were explicitly deselected because that dependency is absent from the
pinned official image. The private signal/lifecycle oracle passed 20/20 supplemental repetitions with
the hardened reference. The
[AnyIO research admission report](../reports/docker-gate/research-anyio-interrupt-runner-cleanup.json)
records task, image, patch, manifest, result and provenance hashes. It made zero model/API calls.

## Third research task admission

`tox-cross-section-empty-substitution` comes from SWE-rebench leaderboard instance
`tox-dev__tox-3810`, tox issue #3809 and PR #3810. It is a hard `memory-development` task pinned to
base commit `02e9ed73da6a0f97f9167e957e1168d6116942ce` and evaluator image
`sha256:ffd1129e4be4692becf5011c874858918864d586267002a2917195726542de57`.

The regression followed an earlier same-section fallback change: a same-section value filtered to empty
must still signal the computed fallback, while an existing value reached through a `SectionProxy` must
resolve to an empty string rather than be treated as absent. The independent hidden oracle checks both
sides of that boundary and excludes the later, unrelated override-propagation behavior from tox PR #3951.

| Patch | Runs | Expected boundary | Observed |
| --- | --- | --- | --- |
| reference | `run_69c2902bef904d70`, `run_4fc68a56c574420e`, `run_a50049ba72f04850` | full success ×3 | 3/3 success, `official=true` |
| no-op | `run_26381b0f1ede4362` | P2P pass, hidden fail | rejected |
| section `KeyError` on empty | `run_32cfdaf52afe4e2f` | hidden semantic fail | rejected |
| global factor empty | `run_7497de1bbeef42fe` | hidden and regression fail | rejected |
| hardcoded upstream section | `run_c03e7fdeedfc41e3` | hidden alternate-section fail | rejected |
| drop all cross-section values | `run_cd00d175dee740b5` | hidden and regression fail | rejected |
| forbidden test edit | `run_db7e448418114cea` | hidden, scope and tampering fail | rejected |

The base and reference passed all 29 benchmark P2P tests. The reference passed six independently authored
hidden checks on each of three official network-disabled Docker evaluations. The admission work also
fixed two harness defects before the final evidence set was frozen: Git patch evidence is decoded as
UTF-8 on Windows, and src-layout checks explicitly bind to the submitted source tree while preserving
the image-generated `tox/version.py` module. The
[tox research admission report](../reports/docker-gate/research-tox-cross-section-empty-substitution.json)
records task, image, patch, manifest, result and provenance hashes. It made zero model/API calls.

## Fourth research task admission

`hf-hub-xet-endpoint-propagation` comes from SWE-rebench V2 instance
`huggingface__huggingface_hub-3180`, Hugging Face Hub issue #3168 and PR #3180. It is a hard
`memory-development` task pinned to base commit
`6f9b87ecda5025259c69a1eb0ae6f8ee80d05d33` and evaluator image
`sha256:c698facf4c9a9e636b8dc114aa9bda6a17ee5f89fe3efd43f39a6543540e891f`.

| Patch | Runs | Expected boundary | Observed |
| --- | --- | --- | --- |
| reference | `run_d5419f78c5584ab3`, `run_a35997231ad7495a`, `run_4d4da461a8b74ea4` | full success ×3 | 3/3 success, `official=true` |
| no-op | `run_e6276ffd6a974845` | P2P pass, hidden fail | rejected |
| parser only | `run_61cc4dc3fff94994` | hidden propagation fail | rejected |
| missing `HfApi` forwarding | `run_6e39f1dbc4034225` | hidden wrapper-path fail | rejected |
| missing download forwarding | `run_092c0061dce545f6` | hidden internal-path fail | rejected |
| unguarded substring replace | `run_7088ef71a036459b` | hidden foreign-route fail | rejected |
| hardcoded default endpoint | `run_e9281b5a7e6f46ab` | hidden endpoint-context fail | rejected |
| forbidden test edit | `run_5c1be518ea764f8f` | hidden, scope and tampering fail | rejected |

The base and every semantic partial fix passed all 15 benchmark P2P tests. The independently authored
eight-check oracle covers header and link parsing, relative and foreign-origin route preservation,
default and explicit endpoints, the low-level parser, internal download path and `HfApi` wrapper. It
also binds imports to `/workspace/src` and fingerprints the exact allowed public-signature delta, so the
broad task-level API permission does not widen acceptance. The
[Hugging Face Hub research admission report](../reports/docker-gate/research-hf-hub-xet-endpoint-propagation.json)
records all patch, manifest, result and provenance hashes from clean harness commit `ebf05dd5...`.
It made zero model/API calls.

## Fifth research task admission

`pdm-ignore-active-venv-resolution` comes from SWE-rebench V2 instance
`pdm-project__pdm-2781`, PDM issue #2779 and PR #2781. It is a hard `memory-development` task pinned to
base commit `881cd4e38d31663ae67bdae227ec1ccdfd5e2c77` and evaluator image
`sha256:a822ad3888e56650c18e9506f8d7882c145ed83d47d518e541e3e44406a929a0`.
PatchLoop normalizes the upstream gold to its production `src/pdm/project/core.py` hunk, excluding the
news fragment and benchmark test patch.

| Patch | Runs | Expected boundary | Observed |
| --- | --- | --- | --- |
| normalized production reference | `run_0d4fa49d3001445b`, `run_d442b8a0f0c84c5d`, `run_ff83740fc8254969` | full success ×3 | 3/3 success, `official=true` |
| no-op | `run_072ec52983844c14` | base regression pass, hidden fail | rejected |
| outer guard removed only | `run_fc56d899d7c3408e` | hidden active-environment fail | rejected |
| direct lookup filtered only | `run_d7cfeeb5a7bf41eb` | hidden associated-environment fail | rejected |
| raw environment truthiness | `run_fc9ff1e3a4f04a53` | hidden false-like-value fail | rejected |
| skip associated environments | `run_886dd7ac5d9549b4` | hidden fallback fail | rejected |
| `VIRTUAL_ENV` only | `run_7eb8ce0b05ec4809` | hidden `CONDA_PREFIX` fail | rejected |
| string-prefix containment | `run_a4f6bdb83c444973` | hidden path-component fail | rejected |
| forbidden test edit | `run_8613c82a35eb49e8` | hidden, scope and test-tampering fail | rejected; aggregate safety remained `pass` |

The base checkout and all six semantic partial fixes passed 36 upstream regression tests. The benchmark
declares 37 P2P nodes because one passing false-flag parameter exists only after its test patch; the
independently authored ten-check hidden oracle covers that behavior without importing the benchmark
test. It also checks submitted-source binding, truthy and false-like settings, `VIRTUAL_ENV`,
`CONDA_PREFIX`, associated-environment and create fallbacks, path-component boundaries and saved
interpreter precedence. The forbidden edit was rejected by the scope and `test_tampering` verifier;
the current aggregate safety verdict remained `pass`, so it is not reported as a safety failure. The
[PDM research admission report](../reports/docker-gate/research-pdm-ignore-active-venv-resolution.json)
records all patch, manifest, result and provenance hashes from clean harness commit `035d7c7f...`.
This gate made zero model/API calls.

## Sixth research task admission

`pyfakefs-makedirs-parent-traversal` comes from SWE-rebench V2 instance
`pytest-dev__pyfakefs-991`, pyfakefs issue #987 and PR #991. It is a medium
`memory-development` task pinned to base commit
`7285b671883b8a06fc26466582a8a45baf508bf7` and evaluator image
`sha256:6de3b39018eec22728567f44dfbdc3cbd31322c384f6ee3d7f328ef38165d57c`.
PatchLoop normalizes the upstream gold to the exact production hunk in
`pyfakefs/fake_os.py`, excluding `CHANGES.md` and the benchmark test patch.

| Patch | Runs | Expected boundary | Observed |
| --- | --- | --- | --- |
| normalized production reference | `run_009825262b514a68`, `run_7af592bb11bd4e1c`, `run_12873e02117e455b` | full success ×3 | 3/3 success, `official=true` |
| no-op | `run_0f7e30047ecf4639` | P2P pass, hidden fail | rejected |
| normalize before creation | `run_f3cae9f4ed4c4442` | regression and hidden traversal fail | rejected |
| one string parent only | `run_4faf97a4757940cf` | hidden bytes/mode fail | rejected |
| propagate leaf mode to parents | `run_e3a8ccad251245fd` | hidden intermediate-mode fail | rejected |
| ignore `exist_ok` | `run_dae4dc5afe1e43bd` | regression and hidden existing-leaf fail | rejected |
| stop after parent creation | `run_28df8167bca54794` | regression and hidden destination fail | rejected |
| swallow non-directory errors | `run_71fa030f5eb04a96` | regression and hidden error-policy fail | rejected |
| leave parent `FileExistsError` uncaught | `run_4007c8257dc443dd` | regression and hidden traversal fail | rejected |
| forbidden test edit | `run_17f66c01ff914266` | hidden, scope and test-tampering fail | rejected |

The base checkout passed all 517 benchmark-declared P2P tests and failed the private
acceptance suite; the same network-disabled command reported 570 platform skips. The
independently authored 12-check oracle binds `FakeOsModule.makedirs` to `/workspace` and covers
ordered POSIX and Windows traversal, nested and bytes paths, trailing separators, pre-existing
destinations, `exist_ok`, non-directory parents and leaf-only mode application. The reference
passed all 12 checks. The
[pyfakefs research admission report](../reports/docker-gate/research-pyfakefs-makedirs-parent-traversal.json)
records all patch, manifest, result and provenance hashes from clean harness commit `64b2f467...`.
This gate made zero model/API calls.

## Seventh research task admission

`moto-query-scanned-count` comes from SWE-rebench V2 instance
`getmoto__moto-7208`, Moto issue #7206 and PR #7208. It is a hard
`development-validation` task pinned to base commit
`624de34d82a1b2c521727b14a2173380e196f1d8` and evaluator image
`sha256:dfdf957ab30b8829e8b6bbfd693b00fab88b7979d3c856362fd5d66c489a1fee`.
PatchLoop normalizes the accepted PR to its production module and excludes the
benchmark test patch.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| normalized production reference | `run_cee764017ee14f6f`, `run_e3c92f006f094766`, `run_ebb46abb00ea4da9` | full success ×3 | 3/3 success, `official=true` |
| no-op | `run_7e5dad51ff294ca7` | regression pass, hidden fail | rejected |
| partition total only | `run_f3838733470e4876` | range, page and index count fail | rejected |
| key results before page | `run_a45ede4752554f08` | per-page count fail | rejected |
| limit without cursor | `run_659b65fc2bde4447` | final-page count fail | rejected |
| post-filter result count | `run_e752404041714902` | pre-filter count fail | rejected |
| index uses table count | `run_bc92fd9ff295438c` | GSI and page count fail | rejected |
| cursor subtraction without limit | `run_06f7c30a08ed4b85` | first and middle-page count fail | rejected |
| forbidden test edit | `run_6fa7ed308ac6435a` | hidden, scope and test-tampering fail | rejected |

The base and all six semantic partial fixes passed 182 selected upstream
regressions. The benchmark declares 173 logical P2P nodes; two truncated
parameterized identifiers expand the set to 179 concrete passing cases. Nine
endpoint tests outside the P2P declaration are explicitly deselected because
they attempt real AWS hosts under a network-disabled evaluator. The independent
nine-check oracle binds `Table.query` to `/workspace` and covers partition and
empty-query scoping, pre-filter accounting, range and GSI conditions, three-page
pagination, filtered limits, projection and reverse ordering. The
[Moto research admission report](../reports/docker-gate/research-moto-query-scanned-count.json)
records every patch, manifest, result and provenance hash from clean harness
commit `b4cc0ec8...`. This gate made zero model/API calls.

## Eighth research task admission

`babel-strict-grouped-decimal-trailing-zeroes` comes from SWE-rebench V2
instance `python-babel__babel-1042`, Babel issue #928 and PR #1042. It is a
medium `development-validation` task pinned to base commit
`aca7663728e08e9d60b192b11fa6626a60974929` and evaluator image
`sha256:864e84fc4bdf09252f7fda4f85665cc05155a7b1d75847d61c67325abce7ef5a`.
PatchLoop keeps the exact accepted production diff and excludes the benchmark
test patch.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| exact production reference | `run_76d98886b57a46ff`, `run_d0b4c5c529d042b1`, `run_bf33a6f3a4ef42f9` | full success ×3 | 3/3 success, `official=true` |
| no-op | `run_a8f6829db59a4693` | regression pass, hidden fail | rejected |
| dot-decimal only | `run_cad3072044ae4125` | comma and Arabic symbol fail | rejected |
| positive only | `run_6377516927944677` | signed value fail | rejected |
| single-zero trim | `run_3d6585338f7648c3` | longer padding fail | rejected |
| normalize returned Decimal | `run_2e67c5483f094e52` | scale preservation fail | rejected |
| remove all fractional zeroes | `run_ee43f7dbdcbc487f` | significant internal zero fail | rejected |
| suffix-zero bypass | `run_299c0b5d1d174afa` | malformed grouping acceptance | rejected |
| Western grouping only | `run_a3f1007f58cf4c70` | Indian and locale grouping fail | rejected |
| forbidden test edit | `run_e6d6853299034b7f` | hidden, scope and test-tampering fail | rejected |

The base and all seven semantic partial fixes passed all 132 upstream number
tests. The independent 16-check oracle uses values not copied from the issue or
benchmark test patch and covers dot, comma and Arabic decimal symbols, Western,
Indian and narrow-space grouping, signs, significant internal zeroes,
one- through three-zero suffixes, malformed inputs, non-strict compatibility
and Decimal scale. The immutable Git checkout omits generated CLDR data, so the
registered checks use `/babel/babel` data from the pinned image while a
source-binding assertion proves that `parse_decimal` comes from `/workspace`.
The
[Babel research admission report](../reports/docker-gate/research-babel-strict-grouped-decimal-trailing-zeroes.json)
records every patch, manifest, result and provenance hash from clean harness
commit `313af714...`. This gate made zero model/API calls.

## Ninth research task admission

`sqlglot-duckdb-ignore-nulls-modifier-order` comes from SWE-rebench leaderboard
instance `tobymao__sqlglot-7187`, SQLGlot issue #7179 and PR #7187. It is the
first hard `core-cross-repo` held-out task, pinned to base commit
`0e8d0824c40ac46c5e7275180cf2eaae6810f805` and evaluator image
`sha256:43c43d77e3bed15361140767e3f3fd84811e0bad5b58f6afcba83f79b8e58303`.
PatchLoop keeps the exact accepted three-file production diff and excludes the
benchmark test patch. The public localization therefore matches the accepted
patch and is disclosed as high contamination risk.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| exact production reference | `run_f6a17eb337ac486b`, `run_e3395c116cb747ae`, `run_f8633ed259ec4c3c` | full success ×3 | 3/3 success, `official=true` |
| no-op | `run_7724db84e8d44a66` | regression pass, hidden fail | rejected |
| parser only | `run_1a90d9dfea954ad5` | generator/order policy fail | rejected |
| generator only | `run_8aecaee9e8dc4742` | trailing parse fail | rejected |
| global order change | `run_5b43cf766610458e` | dialect isolation fail | rejected |
| IGNORE only | `run_3b4dd9eb77954b7c` | symmetric RESPECT behavior fail | rejected |
| missing DuckDB policy | `run_effcc359b41947fc` | dialect suffix generation fail | rejected |
| missing shared generator policy | `run_d2125ae9d3ef40f7` | generator integration fail | rejected |
| missing `HAVING MAX` policy | `run_93483d6a5b6f4a7d` | BigQuery modifier-chain guard fail | rejected |
| forbidden test edit | `run_7dce9a09b23f47ab` | hidden, scope and test-tampering fail | rejected |

The base and all seven semantic partial implementations passed all 39 upstream
DuckDB tests. The independently authored 21-check oracle binds submitted modules
to `/workspace`; checks `IGNORE NULLS` and `RESPECT NULLS` across FIRST_VALUE,
LAST_VALUE, NTH_VALUE, LAG and LEAD; preserves offsets, defaults, named windows,
frames and AST placement; and guards BigQuery `HAVING MAX` / `ORDER BY` / `LIMIT`
ordering. The hardened extension uses different identifiers, clauses and values
from the benchmark test patch and is a targeted guard, not an exhaustive claim
over every SQLGlot dialect. The
[SQLGlot research admission report](../reports/docker-gate/research-sqlglot-duckdb-ignore-nulls-modifier-order.json)
records every patch, manifest, result and provenance hash from clean harness
commit `89f47025...`. This gate made zero model/API calls.

## Tenth research task admission

`pdm-target-project-options-loading` comes from SWE-rebench leaderboard instance
`pdm-project__pdm-3759`, PDM issue #3756 and PR #3759. It is the first hard
`core-same-repo` held-out task, pinned to base commit
`e96d535bb1bd64ac21575cf3490d64f737c6a668` and evaluator image
`sha256:7a012a5bfd460d638b74d3de84426cd1fa2141aec3914c4f9171071491f5ac93`.
The development PDM #2781 task changes interpreter candidate selection in
`src/pdm/project/core.py`; this task changes CLI bootstrap ordering in
`src/pdm/core.py`, so their solution lineages are distinct.

The benchmark PR test mocked `parse_args` and put `-p` before the subcommand,
an order rejected by PDM's real subcommand parser. Its production patch also
scanned raw arguments before parsing. PatchLoop therefore uses the PDM
maintainer's immediate follow-up, normalized onto the benchmark base, as the
hardened one-file reference. The exact benchmark production hunk remains a
known-bad patch.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| hardened maintainer-follow-up reference | `run_dc888b1a81b94a6a`, `run_5de9431b97a24932`, `run_a2436ff595514516` | full success ×3 | 3/3 success, `official=true` |
| no-op | `run_c208dfd11cdc41ad` | regression pass, hidden fail | rejected |
| exact benchmark PR extractor | `run_9f8eb00272e8407f` | attached/repeated/environment precedence fail | rejected |
| caller fallback when target has no option | `run_852bbd813c5b4c5c` | target isolation fail | rejected |
| caller options injected after selection | `run_081e6a8b166d4535` | regression and target isolation fail | rejected |
| environment-only selection | `run_46fcaf6a87324578` | CLI selection forms fail | rejected |
| ignore explicit object | `run_eab9fa34934d457d` | regression and object precedence fail | rejected |
| inject without reparse | `run_1d1c3454dd604b62` | configured options have no parsed effect | rejected |
| install command only | `run_473206223a554407` | cross-command behavior fail | rejected |
| project selection without injection | `run_f03af3d7aee34e6c` | regression and configured-option behavior fail | rejected |
| separated short form only | `run_26aada063fef4f5d` | long/attached/repeated forms fail | rejected |
| forbidden test edit | `run_386caf37ef904569` | hidden, scope and test-tampering fail | rejected |

The registered public file reports 63 passing regressions after explicitly
deselecting one node that attempts an external package install under the
mandatory network-disabled evaluator. The benchmark metadata separately
declares one F2P and 63 P2P nodes. The independent 11-check oracle binds imports
to `/workspace/src`; exercises separated and attached short/long forms,
repeat-last-wins, `PDM_PROJECT`, explicit-object precedence, global isolation,
multiple commands and no caller fallback; and preserves normal caller-project
behavior. The
[PDM target-project research admission report](../reports/docker-gate/research-pdm-target-project-options-loading.json)
records every patch, manifest, result and provenance hash from clean harness
commit `ad25a8a...`. This gate made zero model/API calls.

## Eleventh research task admission

`anyio-extensionless-entrypoint-worker-main` comes from SWE-rebench leaderboard
instance `agronholm__anyio-1134`, AnyIO issue #1027 and PR #1134. It is the
second hard `core-same-repo` held-out task, pinned to base commit
`01b8d02381ba95ba11241c1ec361e908fe05b8be` and evaluator image
`sha256:d7997027864d2bfb32d649e7e544381f5d1b161df8f1682c719d222d66489dc0`.
The development AnyIO #1121 task changes interrupted pytest runner cleanup in
`src/anyio/_backends/_asyncio.py`; this task changes process-worker reconstruction
of an extensionless entrypoint in `src/anyio/to_process.py`. Their trigger,
failure mechanism and solution lineage are distinct.

The benchmark gold also changes a changelog and an unrelated documentation
dependency marker, while its test patch changes `tests/test_to_process.py`.
PatchLoop keeps the exact accepted production hunk only. No semantic hardening
or later follow-up was substituted.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| exact production reference | `run_195b5bb706d8474c`, `run_cc99d8a8a0714a45`, `run_61da03d9899b4bad` | full success ×3 | 3/3 success, `official=true` |
| no-op | `run_c3ef90631f9549b4` | regression pass, hidden fail | rejected |
| only `__main__` alias | `run_0068d719bf2c412c` | multiprocessing alias missing | rejected |
| metadata dropped | `run_84374942f4c44310` | module name/file contract fail | rejected |
| entrypoint executed twice | `run_9f849b88babc4de1` | exactly-once contract fail | rejected |
| empty main module | `run_1b74ccf7e065445d` | entrypoint globals missing | rejected |
| dictionary used as module alias | `run_d88cdcf779fa44d8` | module identity/type fail | rejected |
| run-path result not copied | `run_7062a43e83664327` | callable/global lookup fail | rejected |
| extensionless-only fallback | `run_ee7d3cff08a64b60` | unknown-suffix compatibility fail | rejected |
| unnamed run path | `run_dffecd32ca814d8d` | multiprocessing module name fail | rejected |
| `run_name="__main__"` | `run_cc5a0510264e407e` | main-guard recursion; regression and hidden fail | rejected |
| forbidden test edit | `run_61eae9117ae04a94` | hidden, scope and test-tampering fail | rejected |

The unmodified base and eight non-recursive semantic partials passed all 36
upstream process-pool tests while failing the independent 11-check oracle. The
oracle launches real extensionless entrypoints through AnyIO's worker path,
binds imports to `/workspace/src`, covers asyncio and trio, an unknown suffix,
path spaces, `__main__` / `__mp_main__` identity, module metadata, exactly-once
loading, worker reuse, ordinary `.py` compatibility and initialization-error
propagation. It observes behavior rather than requiring `runpy` or `ModuleType`.
The
[AnyIO process-worker research admission report](../reports/docker-gate/research-anyio-extensionless-entrypoint-worker-main.json)
records every patch, manifest, result and provenance hash from clean harness
commit `9dfc60dd...`. This gate made zero model/API calls. All runs used a
network-disabled, read-only Docker boundary. The external evaluator image has no
configured user and therefore ran as Docker's default root user; the limitation
is disclosed rather than attributed to the native image's non-root smoke.

## Twelfth research task admission

`param-shared-rx-fanout-cache` comes from SWE-rebench leaderboard instance
`holoviz__param-1117`, Param issue #1116 and PR #1117. It is the second hard
`core-cross-repo` held-out task, pinned to base commit
`833c8f05f7a47fa1476620307ef7fd447c45e6fb` and evaluator image
`sha256:c10bc0ad51b00c59ed8fa4366ee722c38e83dfaa620a7cc229f78489ccbaf010`.
PatchLoop keeps the exact accepted production hunk in `param/reactive.py` and
excludes the benchmark test patch. The public issue, accepted patch and one-file
localization are all available upstream, so contamination risk remains high.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| exact production reference | `run_abd2492639524050`, `run_6371e12b93324023`, `run_314c93a4a1f24577` | full success ×3 | 3/3 success, `official=true` |
| no-op | `run_16f15bd5874c4c75` | regression pass, hidden fail | rejected |
| missing shared clone link | `run_972670209bdf4d59` | hidden shared-source fail | rejected |
| synchronous sharing only | `run_552269843cd84065` | hidden async/generator fail | rejected |
| async result not awaited | `run_9bffaeffa42345bb` | hidden coroutine fan-out fail | rejected |
| generator detection omitted | `run_13241124090d4297` | regression and hidden generator fail | rejected |
| wrong shared pointer | `run_cb2d851f8f9e4b31` | regression and hidden isolation fail | rejected |
| self-method guard omitted | `run_be453108ce604ba8` | hidden accessor-divergence fail | rejected |
| shared-method guard omitted | `run_d653e11cc58f4928` | regression and hidden accessor-divergence fail | rejected |
| stale shared current value | `run_ba0d5de8cd66404e` | regression and hidden invalidation fail | rejected |
| forbidden test edit | `run_21905bc5bce74b3e` | hidden, scope and test-tampering fail | rejected |

The base checkout passed all 94 upstream reactive regressions, with seven
skips, while failing the private ten-check oracle. Four
semantic partials also preserved the visible suite but failed hidden
acceptance; the other four failed both regression and hidden checks. The
independent oracle binds submitted imports to `/workspace` and covers
synchronous, coroutine and generator fan-out, nested sharing, independent
graphs, repeated invalidation, property and method accessors, consumer
isolation, and source error recovery. The
[Param reactive fan-out research admission report](../reports/docker-gate/research-param-shared-rx-fanout-cache.json)
records every patch, manifest, result and provenance hash from clean harness
commit `4d73605a...`. This gate made zero model/API calls. All runs enforced
network denial and a read-only submitted workspace; the image has no configured
user and therefore ran as Docker's default root user.

## Thirteenth research task admission

`hf-hub-custom-tqdm-class-contract` comes from SWE-rebench leaderboard instance
`huggingface__huggingface_hub-4056`, Hugging Face Hub issue #4050 and PR #4056.
It is the third hard `core-same-repo` held-out task, pinned to base
`6983a4d3d2bdcbd09c6ea08acae64cdf83ccb2e4` and evaluator image
`sha256:cbfae263dff792cc7c763057905869c548bf37733352ff999b3d7d4278c87677`.
PatchLoop keeps the exact two-file accepted production patch and excludes the
benchmark test patch. Contamination risk remains high because the public issue,
patch and localization are available upstream.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| exact production reference | `run_91a8053743aa45ce`, `run_8b0127ad2395461b`, `run_006387b2578e4ae6` | full success ×3 | 3/3 success, `official=true` |
| no-op | `run_ec70609f8e1248e6` | regression pass, hidden fail | rejected |
| combined foreign-only policy | `run_16d062dbc74f4a01` | hidden snapshot-HF-policy fail | rejected |
| file context only | `run_53188d82a1014206` | hidden snapshot path fail | rejected |
| exact HF class only | `run_479fb08d999645f3` | hidden HF-subclass fail | rejected |
| force custom `disable=False` | `run_4816ec4e8aa04ef4` | hidden constructor-ownership fail | rejected |
| drop all HF policy | `run_6e2a878491334888` | hidden HF group/log fail | rejected |
| snapshot path only | `run_d14dd4bad8e9406f` | hidden file path fail | rejected |
| strip only `name` | `run_5068ed072e8744ca` | hidden `disable` ownership fail | rejected |
| unguarded `issubclass` | `run_79d02f9f0ad84027` | hidden callable/partial fail | rejected |
| treat every upstream subclass as HF | `run_8d432cc577e34d66` | hidden foreign-subclass fail | rejected |
| forbidden test edit | `run_10f9c5a6702c4be2` | hidden, scope and test-tampering fail | rejected |

The base passed all 17 tests present in the frozen upstream file and failed nine
of 15 hidden cases. The benchmark declares 19 P2P nodes because its excluded
test patch introduces two extra nodes that already pass on the base; the
executed and declared counts are not conflated. The oracle binds imports to
`/workspace` and exercises strict custom classes, a foreign upstream-tqdm
subclass, function and partial factories, existing bars, fully mocked file and
snapshot downloads, aggregation, and HF subclass group/log/TQDM_POSITION policy.

Adversarial review before the clean commit combined two individually rejected
partials and demonstrated an actual false positive in the original 11-case
oracle: the shared file context was correct, but snapshot construction discarded
HF-owned policy. PatchLoop added snapshot callable and HF-policy observations,
retained the escaping union as a known-bad patch, and reran the full matrix from
clean commit `962668e8...`. The
[Hugging Face progress-policy admission report](../reports/docker-gate/research-hf-hub-custom-tqdm-class-contract.json)
binds all 14 run manifests, results, provenance records and patch hashes. The
gate made zero model/API calls and used a network-disabled, read-only submitted
workspace. The image has no configured user and ran as Docker's default root
user.

## Fourteenth research task admission

`mtplx-mixed-content-tool-call-stream` comes from SWE-rebench leaderboard
instance `youssofal__mtplx-21`, MTPLX issue #20 and PR #21. It is the third hard
`core-cross-repo` held-out task, pinned to base commit
`c06cc13286e86d9ff3d2e3b991eba327549c534b` and evaluator image
`sha256:32510a901064f5d405f3d4313a4556d924c94e72b2b0993296a43f04de83370e`.
The accepted source patch fixes mixed preamble handling but also matches
lookalike marker stems and can silently discard non-whitespace residue. PatchLoop
therefore retains it as a known-bad and uses a one-file hardened reference with
an exact `<tool_call>` delimiter and stream-local residue enforcement.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| hardened reference | `run_236767f9815b41e9`, `run_1e751bd099b44d82`, `run_647176898cdb411e` | full success ×3 | 3/3 success, `official=true` |
| no-op | `run_9a04e61629c74a27` | regression pass, hidden fail | rejected |
| content lock removed only | `run_7e3a2597aa464ab3` | mixed-stream state fail | rejected |
| chunk-start marker only | `run_c8402fc708b043ec` | arbitrary chunk-boundary fail | rejected |
| current-chunk search only | `run_58f5c4143d9b43e4` | cross-chunk marker fail | rejected |
| initial-buffer search, preamble dropped | `run_4b088912a14741a1` | preamble preservation fail | rejected |
| case-sensitive scan | `run_54eb40b2aa2b4ad1` | mixed-case marker fail | rejected |
| no partial-tail retention | `run_75d42a5562464f21` | marker split fail | rejected |
| one-character tail only | `run_8977994330c94642` | longer marker prefix fail | rejected |
| trailing policy relaxed | `run_b564f13cb67146e2` | residue rejection fail | rejected |
| exact accepted upstream source patch | `run_7a98e3bcbf5c4e17` | delimiter and residue hardening fail | rejected |
| forbidden test edit | `run_89f4d3e5fd28425a` | hidden, scope and test-tampering fail | rejected |

The base/no-op run passed all 55 registered CPU/mock regressions and failed the
21-case independent oracle. Three collected session tests are explicitly
deselected because the benchmark image lacks the MLX runtime. All official runs
used a network-disabled, read-only submitted workspace and made zero model/API
calls. The image has no configured user and ran as Docker's default root user.

The first clean-gate attempt exposed that a normal clone did not advertise the
frozen base tree. PatchLoop now validates a lowercase 40-hex revision and, only
after checkout failure, fetches that exact SHA into `FETCH_HEAD`, rechecks a
detached `HEAD`, and rejects unavailable or mismatched revisions. Success,
invalid-SHA and fetch-failure tests cover this path. The official matrix was then
run from clean harness commit `82a0c23b...`. The
[MTPLX streaming admission report](../reports/docker-gate/research-mtplx-mixed-content-tool-call-stream.json)
binds all 14 patch, manifest, result and provenance hashes.

## Fifteenth research task admission

`fusesoc-retained-parse-error-diagnostics` comes from SWE-rebench leaderboard
instance `olofk__fusesoc-776_interface`, FuseSoC issue #761 and PR #776. It is
the fourth hard `core-cross-repo` held-out task, pinned to base commit
`d2e6e720222f57cb66d6c303a326d336c582aade` and evaluator image
`sha256:1e971791d4ce192eae296747d46dff477cb2ce2c47e08b2ed9d0108ee5a85ad9`.
The exact three-file production reference retains every parse failure while
continuing valid-core discovery, forwards the current list through `Fusesoc`
and appends every path and parser message to the existing missing-core
diagnostic.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| exact production reference | `run_1930d4d388214a39`, `run_ecc6b25d878941dd`, `run_41a5e6e0c3a9460f` | full success ×3 | 3/3 success, `official=true` |
| base/no-op | `run_27a35b3567fc4b75` | visible pass, hidden fail | rejected |
| manager-only retention | `run_fd337d9d5db34b19` | wrapper/CLI fail | rejected |
| wrapper-only exposure | `run_058153b57a3f4135` | manager retention fail | rejected |
| missing CLI propagation | `run_7e8f97cfc9e44546` | final diagnostic fail | rejected |
| last error only | `run_1b70b4fca4ad411c` | accumulation fail | rejected |
| class-shared errors | `run_a55d1e200c5e4163` | instance isolation fail | rejected |
| hard stop on parse error | `run_6df53dc5f3fe4326` | valid-core continuation fail | rejected |
| import errors misclassified | `run_b5bf8f2a76794047` | non-parse handling fail | rejected |
| CLI first error only | `run_e150bdb76e554d24` | complete diagnostic fail | rejected |
| forbidden test edit | `run_03d995290fee481d` | hidden, scope and test-tampering fail | rejected |

The visible file collects 14 base tests. The network-dependent `test_export`
and the lockfile-writing `test_lockfile_no_file_create` are explicitly
deselected under the network-none, read-only boundary; the remaining 12 pass
with the image's testbed environment on `PATH`. The independent ten-case
oracle binds all three production imports to `/workspace` and checks
multi-error accumulation, valid-core continuation, instance isolation, live
wrapper forwarding, complete CLI diagnostics and unchanged `ImportError`
handling. Base/no-op and all eight semantic partials failed hidden acceptance
only; the forbidden edit additionally failed scope and tampering.

All 13 official cases ran from clean harness staging commit
`da3105d30f0c7eb6fec65650200aedac7eb12b13` with Docker networking disabled
and read-only root and submitted filesystems. The image has no configured
`User` and ran as Docker's default root user. The public task hash is
`sha256:2dd38ab34abc7ab53c0487c2d5b19dbda5b303fe2d04bf04474cc5bafef6ba31`
and the private task hash is
`sha256:e5db4a13d05518abd3a2be50c99ed8aa9536168896c27f52a4947c6773e7b66d`.
The [FuseSoC diagnostic admission report](../reports/docker-gate/research-fusesoc-retained-parse-error-diagnostics.json)
binds the run manifests, results, provenance records and patch hashes. Its
SHA-256 is
`cef87dda16402d874b28264fcbed5bba2acf07736800c5fd297d812112081918`.

## Sixteenth research task admission

`tox-dotted-version-factor-base-python` comes from SWE-rebench leaderboard
instance `tox-dev__tox-3846`, tox issue #3845 and PR #3846, plus follow-up
regression issue #3850 and PR #3851. It is the fourth hard
`core-same-repo` held-out task, pinned to base commit
`ae05f2a33ccfe52ff22ac578ec6c8eb9f750ce4a` and evaluator image
`sha256:269a32558d3aeac5f9e9b6fc451302667b83a85f260f0b915babe1838b50b3bc`.
The benchmark patch recognizes bare `2.N` and `3.N` factors inside compound
environment names. Its accepted release immediately regressed names containing
multiple Python-like factors because extraction raised before
`ignore_base_python_conflict` could apply. PatchLoop therefore combines the
accepted #3846 grammar and #3851 conflict-policy production changes as its
hardened reference and retains each PR in isolation as a known-bad partial.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| hardened #3846 + #3851 reference | `run_41553bac68ee4214`, `run_6917e86f2f2a4a20`, `run_0fd0206fb8144eb9` | full success ×3 | 3/3 success, `official=true` |
| base/no-op | `run_4bd98e35f36c4fe7` | visible pass, hidden fail | rejected |
| exact #3846 only | `run_a64d4e9fd59c4f6f` | follow-up conflict policy fail | rejected |
| exact #3851 only | `run_a4d76dfa461c420e` | dotted-factor grammar fail | rejected |
| major restriction only | `run_cf5d23ef8f1047e4` | compound factor fail | rejected |
| explicit factors only | `run_2ffd9b9ee3ad4931` | classic-factor regression | regression and hidden fail |
| first match wins | `run_0274332691db4949` | ambiguity detection fail | regression and hidden fail |
| ignore all validation conflicts | `run_b17cf94c4e404256` | older single-factor contract fail | regression and hidden fail |
| default-only ignore handling | `run_8b68477a7bc542dc` | validation path fail | rejected |
| validation-only ignore handling | `run_0499c984ec814e1c` | default path fail | rejected |
| threaded suffix stripped | `run_60fb1826103d45bf` | free-threaded factor fail | rejected |
| dotted major range too broad | `run_7d153b8ec0e44c95` | non-Python major guard fail | regression and hidden fail |
| forbidden test edit | `run_4efaa4b1bbe549f6` | hidden, scope and test-tampering fail | rejected |

The private oracle collects 17 cases from eight functions and binds the Python
API to submitted source. It covers compound factor positions, free-threaded
suffixes, classic factors, whole-name CPython/PyPy normalization, rejection of
major versions 4 and above, ambiguity diagnostics, both ignore-policy entry
points and the older single-factor override contract. It deliberately does not
require compound `qa-pypy-3.10`, which the accepted grammar splits into two
recognized factors.

The registered visible check covers 101 of 110 declared P2P nodes. Nine
deterministic environment-incompatible nodes are deselected; because one pytest
node prefix also removes two healthy siblings, those exact cases run in a
second invocation. The observed total is therefore 99 + 2 passing cases.

All 15 official runs came from clean harness commit
`678d30a50ae27cb48623c1fbe5bc04bb65d34bad`. The
[tox dotted-factor admission report](../reports/docker-gate/research-tox-dotted-version-factor-base-python.json)
binds patch, manifest, result and provenance hashes and has SHA-256
`sha256:216ccfd1f9017ca499c9902ac857a2e6d4ebc0dca1aeb1aff04e9af396485fe6`.
The gate made zero model/API calls and is deterministic
evaluator evidence, not live-model agent performance or a core campaign result.
The external image has no configured `User` and ran as Docker's default root
user under the network-disabled, read-only evaluator boundary.

## Seventeenth research task admission

`dagster-subset-partition-definition-selection` comes from SWE-rebench
leaderboard instance `dagster-io__dagster-33605`, Dagster issue #33584 and
PR #33605. It is the fifth hard `core-cross-repo` held-out task, pinned to
base commit `f8430dc7bf76bfab4f026165e5c5f821104298df` and evaluator image
`sha256:98a0b69301022cba2ac7520a8ab1891c2a490cf4ec4ba889d6ce36a29f40831b`.
The exact two-file production reference makes the `AssetsDefinition`
partition result depend on selected asset and asset-check keys, then delegates
the execution context to that selection-aware property.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| exact production reference | `run_1927909d6cd241e7`, `run_bd7f5b11e51d4202`, `run_c66f90c1fc4242cc` | full success ×3 | 3/3 success, `official=true` |
| base/no-op | `run_2a20d874bedf450b` | 28 visible pass, hidden fail | rejected |
| always unpartitioned | `run_d8c2b3eb40814ba8` | selected partition and visible regression fail | regression and hidden fail |
| assets definition only | `run_7ea661da98c748f2` | execution-context delegation fail | rejected |
| check asset-key filter | `run_fb0bd8300f514af9` | selected check-key semantics fail | rejected |
| execution context only | `run_2682f33ade874bd9` | selection-aware definition fail | rejected |
| first selected definition | `run_2204c73911354106` | incompatible-definition conflict fail | rejected |
| selected assets only | `run_91a3c33dfdbc4958` | selected check partition fail | rejected |
| selected checks only | `run_55ba57333f1740ec` | selected asset partition fail | rejected |
| unfiltered check specs | `run_2a7f765456c44ab0` | unselected check isolation fail | rejected |
| forbidden test edit | `run_2b6c0ba491ee4d86` | hidden, scope and test-tampering fail | rejected |

The complete base-resident visible module passed all 28 declared P2P nodes on
each reference run. The independently authored private oracle contains nine
tests covering selected and unselected assets and checks, compatible
deduplication, real conflicts and execution-context delegation. The
`task-private-v2` spec binds the hidden artifact by content hash. Visible tests
and the hidden oracle remain on read-only mounts; each check copies only the
submitted Dagster production package into a fresh writable `/tmp` import root
and asserts submitted-source binding. Base/no-op and all eight semantic
partials were rejected, and the forbidden edit additionally failed scope and
test-tampering enforcement.

All 13 official cases ran from clean harness staging commit
`26f28cf11d53f3b0e17b2a4663d0ce68afe63b27` with Docker networking disabled
and read-only root and submitted filesystems. The external image has no
configured `User` and ran as Docker's default root user. The
[Dagster partition-selection admission report](../reports/docker-gate/research-dagster-subset-partition-definition-selection.json)
binds every patch, manifest, result and provenance hash and has SHA-256
`sha256:2d95aa36990b8cd475476a0992b0db7a8d9259d5c7a21d35c99ea3a6c551d012`.
The gate made zero model/API calls and is deterministic evaluator admission
evidence, not live-model agent performance, memory improvement or a core
campaign result.

## Eighteenth research task admission

`kubeflow-exit-handler-after-dependencies` comes from SWE-rebench leaderboard
instance `kubeflow__pipelines-13112`, Kubeflow Pipelines issue #10722 and
PR #13112. It is the sixth hard `core-cross-repo` held-out task, pinned to
base commit `98f5b7a300ee52d6c530b429558b718ade9fdb7a` and evaluator image
`sha256:842b24c98e1b2c1145b8826b90a95e0634a3520cd523b3d3ae6940201ec2e79a`.
The exact two-file production reference broadens the public
`PipelineTask.after` contract to supported `ExitHandler` groups and makes the
compiler distinguish task, group, missing and ambiguous dependency names.
The benchmark test patch remains evaluator-only.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| exact production reference | `run_7876f396980a4c55`, `run_e2930e730d104a3c`, `run_f4c2707cc64e4a63` | full success ×3 | 3/3 success, `official=true` |
| base/no-op | `run_28d458248adb4cca` | 277 visible pass, hidden fail | rejected |
| compiler resolution only | `run_9c0ab4f5a208424a` | public validation fail | rejected |
| accept any task group | `run_fb281c4593234662` | non-exit group rejection fail | rejected |
| retain only first dependency | `run_f4445927f042437d` | mixed dependency preservation fail | regression and hidden fail |
| group-only resolution | `run_61a35efc95b34a2a` | ordinary task dependency fail | regression and hidden fail |
| public validation only | `run_030d1c1ffa3c4e0b` | compiler group resolution fail | rejected |
| resolve group as exit task | `run_a3d0b17e1e624efe` | group boundary and final-status fail | rejected |
| prefer task on collision | `run_9b25341374b54dfe` | ambiguous-name rejection fail | rejected |
| leak unknown-name key error | `run_d48f210c19244f82` | clear missing dependency error fail | rejected |
| forbidden test edit | `run_2da8391ec73948e4` | hidden, scope and test-tampering fail | rejected |

The complete base-resident `compiler_test.py` and `pipeline_task_test.py`
surface passed 277 tests plus 15 subtests on each reference run. The frozen
benchmark declares 278 P2P nodes because its test patch adds one preservation
P2P test; after excluding that evaluator-only addition, the base-resident P2P
declaration is exactly 277. The same patch adds all seven F2P tests.

The independently authored private oracle contains 11 tests covering
submitted-source binding and ten semantic boundaries: single, mixed and
chained group dependencies; unsupported and arbitrary inputs; missing and
ambiguous names; nested-context rejection; and final-status attribution. The
`task-private-v2` spec binds the oracle by content hash. Visible tests and the
hidden oracle remain on read-only mounts while each check copies only the
submitted KFP production package into a fresh writable `/tmp` import root.

All 13 official cases ran from clean harness staging commit
`5e7b019e60b4d76f67e48bafe6fd1a3b309fe313` with Docker networking disabled
and read-only root and submitted filesystems. The external image has no
configured `User` and ran as Docker's default root user. The
[Kubeflow ExitHandler admission report](../reports/docker-gate/research-kubeflow-exit-handler-after-dependencies.json)
binds every patch, manifest, result and provenance hash and has SHA-256
`sha256:c7998d064949dd5a67f05c15ff7d426ef1051f74fea7bb03e37f91c7d1d5084c`.
The gate made zero model/API calls and is deterministic evaluator admission
evidence, not live-model agent performance, memory improvement or a core
campaign result.

## Nineteenth research task admission

`loguru-post-2038-local-timezone-fallback` comes from the frozen SWE-rebench
leaderboard aggregate `test` row 209, instance `Delgan__loguru-1297`, Loguru
issue #1291 and PR #1297. It is the fifth hard `core-same-repo` held-out task,
pinned to base commit `e310e2029102b5d63a679a2b64501c045aa86336` and
evaluator image
`sha256:8d899d1147cf88bc088afe57fc5299fdcf2fafe6a1e30ef26825577e8953362f`.
The reference is the exact accepted `loguru/_datetime.py` production hunk;
the benchmark changelog hunk and test patch remain evaluator-only.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| exact production reference | `run_76b8e870024a49ec`, `run_44fcae6e680445ed`, `run_f3de06b5c7d24af7` | full success ×3 | 3/3 success, `official=true` |
| equivalent `utcfromtimestamp` solution | `run_9c5e228c646442a3` | implementation-independent full success | accepted |
| base/no-op | `run_5643e3746f804cb7` | 43 visible pass, hidden fail | rejected |
| always use fallback | `run_cc840d2e13634aa3` | valid platform metadata preservation fail | regression and hidden fail |
| catch all local-time exceptions | `run_cb02eb1400664bb8` | unsupported exception propagation fail | rejected |
| clamp invalid offset | `run_1d2ab550b6824215` | derived offset fail | rejected |
| fixed derived-looking fallback | `run_c6e7472411484011` | multi-profile derivation fail | rejected |
| reverse fallback offset | `run_197650ce0f014d54` | offset direction fail | rejected |
| discard fallback zone | `run_40744cf912f047ce` | zone-name preservation fail | rejected |
| use UTC on invalid offset | `run_2b1157c21b434842` | local offset derivation fail | rejected |
| catch wrong local-time errors | `run_18d9696bbefb454f` | supported range-error recovery fail | rejected |
| catch wrong timezone error | `run_9ca3c4bc27184551` | invalid offset recovery fail | rejected |
| forbidden test edit | `run_c3e433e0ac98456f` | hidden, scope and test-tampering fail | rejected |

Every reference run passed all 43 base-resident `test_datetime.py` cases and
all 11 independently authored hidden cases. The frozen benchmark separately
declares 34 P2P and four F2P nodes; the executed full base test module and
declared benchmark subsets are reported without conflating their counts.

The hidden oracle collects 11 subprocess cases across five test functions.
It preserves valid negative, zero and positive platform offsets; exercises
invalid offsets, supported range errors and each missing-field boundary; and
propagates an unsupported `RuntimeError`. Positive, negative and date-rollover
fallback profiles use different offsets and zone names while keeping wall
time, UTC conversion and timestamp internally consistent. The clock double
supports valid `now(tz=...)`, `utcfromtimestamp()`, `astimezone()` and
`combine()` paths; the positive equivalent run proves the oracle is not tied
to the accepted reference's exact conversion call. The `task-private-v2` spec
binds the oracle by content hash, and both visible and hidden tests remain on
read-only mounts while submitted production source is copied to a fresh
writable import root.

All 15 official cases ran from clean harness staging commit
`8c5084eee3a44a44e207345950a9ffb45b23e4b1` with Docker networking disabled
and read-only root and submitted filesystems. The external image has no
configured `User` and ran as Docker's default root user. The
[Loguru timezone-fallback admission report](../reports/docker-gate/research-loguru-post-2038-local-timezone-fallback.json)
binds every patch, manifest, result and provenance hash and has SHA-256
`sha256:044655debc7255549e8ba49cdfc339c6a0d04f2fdab3b983017efcbc7c38ffbc`.
The gate made zero model/API calls and is deterministic evaluator admission
evidence, not live-model agent performance, memory improvement or a core
campaign result.

## Twentieth research task admission

`pyfakefs-file-wrapper-io-capabilities` comes from the frozen SWE-rebench
leaderboard aggregate `test` row 653, instance `pytest-dev__pyfakefs-1269`,
pyfakefs issue #1265 and PR #1269. It is the sixth, medium
`core-same-repo` held-out task, paired one-to-one with the pyfakefs
memory-development task while using a distinct base, production file, failure
pattern and solution lineage.

| Patch group | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| exact production reference ×3 | `run_b9902d125f9a4a9e`, `run_41bba6a0e480483c`, `run_d0a0277614f04b49` | full success | 3/3 success, `official=true` |
| dynamic-interface equivalent | `run_1bf5034e9a2a48fb` | implementation-independent full success | accepted |
| base/no-op | `run_6b26a5042d6048dc` | visible pass, hidden fail | rejected |
| nine semantic partials | nine content-addressed runs in the report | capability and guard boundaries | all rejected |
| forbidden test edit | `run_722a1d4381a74127` | hidden, scope and tampering fail | rejected by all three |

Each reference and equivalent run passed 431 visible tests with 161 skips
(592 collected) and all 29 independently authored hidden cases. Base/no-op
preserved the same visible result but failed 12 hidden boundary cases. The
semantic corpus covers constant, mirrored, inverted, primary-mode-only and
backing-buffer capability answers; missing callable methods; and methods that
do not control internal guards.

All 15 official cases ran from clean harness staging commit
`b50b4314aa7fd209737db46f15b38aee056bbd80` with Docker networking disabled
and read-only root and submitted filesystems. The external image has no
configured `User` and ran as Docker's default root user. The
[pyfakefs capability admission report](../reports/docker-gate/research-pyfakefs-file-wrapper-io-capabilities.json)
binds every patch, manifest, result and provenance hash and has SHA-256
`sha256:49f92f1ceab905d086d23820f0af581706ffaa8bd3e923d4cc972cac914e252e`.
The gate made zero model/API calls and is deterministic evaluator admission
evidence, not live-model agent performance, memory improvement or a core
campaign result.

## Recovery evidence

Both automated E2E and a CLI-derived run were exercised. The run was suspended immediately after the
durable patch checkpoint, resumed, reached the hidden evaluator and retained exactly one `PatchApplied`
event. Checkpoint/worktree hash corruption is separately rejected by test.

## Dataset freeze evidence

`patchloop dataset audit` completed successfully with `complete=true`, `research_ready=true`,
`stress_ready=true`, `freeze_eligible=true`, no errors and no freeze blockers. The frozen manifest
contains five calibration fixtures and 20 admitted research tasks and has SHA-256
`sha256:cf608ca1a35cb270f2e4cadcf0b34912256ef1c9cd3c0757a89692f8a5fdf786`.

The `public-contract-structure-v1` selector used no private oracle, reference patch or model result.
It selected:

| Archetype | Task |
| --- | --- |
| widest allowed change surface | `fusesoc-retained-parse-error-diagnostics` |
| narrowest remaining mutation surface | `anyio-extensionless-entrypoint-worker-main` |
| longest remaining registered visible check | `pyfakefs-file-wrapper-io-capabilities` |

The frozen schedule has SHA-256
`sha256:d5a3d90f8429f24b6940d4a5cb1b78a35fa34d3fe3df9937ad6c57daba23f468`.
It deterministically expands to 30 derived stress rows: context reset and worker restart each use
persistent-state on/off arms with two repetitions per task, and synthetic test timeout uses the
on arm with two repetitions per task. The baseline source is the core no-memory lane, and all stress
rows are excluded from core metrics. This is schedule-registration evidence only; no stress row or
live-model request was executed by this gate.

## First paid live-pilot evidence

On 2026-07-28, the approved Babel #1042 development-validation execution hash
`sha256:e078a32eff4ab1b0a7c02a7aca6c97115e968bb57bb9e618b42d69fa943f6513`
reached `ready=true` on clean harness commit
`636d0cf973203f2e0521fe41ec4675562c34ccbd` and ran exactly one schedule row.
Run `run_c6f13dd9a1a1472d` persisted 113 monotonic events, 23 checkpoints, the approved plan,
hash-chained campaign journal, terminal result and immutable qualification artifact.

The attempt cost `$0.34025875`: 73,730 input tokens, 73,670 cache-write input tokens and 7,326
output tokens across 20 model and 22 tool calls. All eight failed mutations used an OpenAI-style
`*** Begin Patch` envelope while the constrained gateway accepted only raw Git unified diff.
The next-turn context exposed only `CONTRACT_ERROR`, not the actionable `git apply` error, so the
agent repeated the rejected mutation until the total-token budget was exceeded. No submitted patch
or evaluator verdict exists.

The immutable qualification artifact is `qualified=false`. Its only failed deterministic check was
the original public/private scan: all 41 matches were false positives already disclosed in the
public contract—20 `.patchloop-hidden` forbidden-path markers and 21 occurrences of the hidden-check
name embedded in the public task ID. A separate forensic count found zero API-key, reference-hash,
`private.yaml` or `reference.patch` matches. The historical trace and qualification are retained
unchanged; corrected tool feedback and scanner logic require a fresh commit, execution hash,
preflight and explicit paid approval.

For diagnosis only, the first rejected model candidate was converted from its marker envelope to a
raw Git diff without changing the proposed one-line code edit. The resulting patch has SHA-256
`sha256:4c49b6edd0603f2e56c04c18e83fdecb3a6a5868ab40bffca198504951b01606`
and diff hash
`sha256:5992cb41eb18d9924dcea456fead9bc414489500b88b9371114bdfcf1f8ef743`.
Official Docker evaluator run `run_4299e6b326de4c1c` passed hidden acceptance, all registered
number regressions, scope, dependency, test-tampering and public-API policy in 4,078 ms with zero
model calls. This format-only counterfactual isolates the gateway grammar as the immediate failure
cause; it is not an agent submission or a pilot success. The checked-in
[live-pilot evidence record](../reports/live-pilot/dev-validation-live-pilot-20260728.json)
binds the local raw files, immutable qualification and diagnostic evaluator result by SHA-256.

## Second paid live-pilot and recount evidence

After the r1 tool feedback, leakage filtering, execution ownership and source-evidence fixes were
committed, execution hash
`sha256:c7fe89287ed3310885f548954917c810b699a54ea420b3a7551d9863ebd839a3`
was separately approved for exactly one r2 row with a $2 cap. The run used clean harness commit
`34673def916401efb97bb4bd02dec9dd927db36e` and produced
`run_de8f2a2846044c01`. It cost `$0.328036875`: 74,868 input tokens, 74,811
cache-write input tokens and 6,274 output tokens across 19 model and 22 tool calls. Cumulative
r1+r2 spend is `$0.668295625`.

The r2 run preserved 111 monotonic events and 23 checkpoints with zero infrastructure or
qualification errors. Its immutable `trace-qualification-v1` artifact is `qualified=true`:
trace integrity and leakage passed, private match count was zero, usage reconciled and the
source-evidence hash is
`sha256:84079a25b6b3cdc84df440e8e5a943aaa462eafb161b1fc487f221cc97f0b451`.
This does **not** mean the pilot passed its acceptance gate. No submitted patch or evaluator verdict
exists and `evaluation_reached=false`; the development-campaign consumer therefore rejects this
run and the 12-run campaign remains locked.

The model emitted nine `apply_patch` candidates, seven of them byte-distinct. Eight reached the
gateway and all eight failed with `corrupt patch`; the ninth was produced in the response that
crossed the token budget before tool execution. Every candidate declared seven old and seven new
lines in its hunk header while its body contained six old and six new lines. The candidates changed
line offsets and code variants in response to visible errors, but never repaired this manual count.
Model event 51 proposed the same tuple-membership code edit as the r1 official-passing
counterfactual. Its exact raw patch has SHA-256
`sha256:f041469f1d938452c6e25c54aa1e6b816247be0525920184a77be493f7111695`.
Strict `git apply --check` rejects that file; `git apply --check --recount` accepts it and leaves the
workspace unchanged. This is parser/interoperability evidence, not an agent submission, evaluator
result, pilot success or repetition.

The corrective contract applies `--recount` only to the agent-visible forward apply and the reverse
rollback of the same raw patch. The raw input/hash, hunk body, context, path and deterministic
policies remain unchanged, and hidden evaluator application stays strict. Policy rejection must
restore the exact pre-call diff hash. Reverse failure, restoration mismatch or untracked agent
workspace state is a recovery error; new-file, rename/copy, binary and metadata-only patches remain
rejected. Regression tests cover the r2-style 7/7-versus-6/6 patch, non-empty baseline rollback,
same-action replay without duplicate `PatchApplied`, untracked/recovery guards and fail-closed
rollback. The checked-in
[r2 evidence record](../reports/live-pilot/dev-validation-live-pilot-20260728-r2.json)
and [portable candidate](../reports/live-pilot/artifacts/run_de8f2a2846044c01-recount-candidate.patch)
preserve this claims boundary. No r3 paid call is part of this evidence.

The corrective worktree collected 306 tests: 304 passed in the restricted test environment and the
two Docker-only sandbox tests were skipped because that environment could not see the daemon.
Running `tests/test_sandbox.py` on the host with a repository-local ignored pytest temp directory
passed all nine tests, including the two Docker isolation checks. Full Ruff and `git diff --check`
also passed. These are harness regression results, not live-model task evidence.

## Open gates

`patchloop doctor` now passes with authenticated `gh`, WSL2, Docker Desktop and the pinned evaluator image;
`official_evaluation_ready=true`. The dataset freeze gate is complete, but the stress campaign is not:
the context-reset trigger, persistent-state-off arm and stress matrix runner/report remain
unimplemented. The current worker path is cooperative suspension rather than external process
termination, and the timeout path is a synthetic timeout on the first registered visible check.
No stress schedule row, accepted live pilot, 12-run development campaign or 96-run core campaign
has been executed.
