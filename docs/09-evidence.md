# Implementation evidence — through 2026-07-27

This is a local implementation checkpoint, not the planned core experiment result.

## Executed gates

| Gate | Command | Outcome |
| --- | --- | --- |
| Lock consistency | `uv --cache-dir .patchloop/uv-cache lock --check` | pass, 78 packages resolved |
| Static analysis | `.venv/Scripts/ruff check .` | pass |
| Tests | `.venv/Scripts/python -m pytest -q -p no:cacheprovider` | 105 pass, 2 skipped; all six research admissions and dataset-role gates included |
| Package build | `uv build` | sdist and wheel built |
| Task contract | `patchloop task validate tasks/<split>/<task>` | five calibration plus six research packages pass |
| Dataset audit | `patchloop dataset audit` | expected incomplete: calibration 5/5, research 6/20, no contract errors |
| Docker build | pinned base, `--network=none --provenance=false`, repeated twice | stable image ID in 2/2 builds |
| Docker isolation | network, UID, read-only workspace, host secret | all pass |
| Research admission | Loguru, AnyIO, tox, Hugging Face Hub, PDM and pyfakefs references ×3 plus declared negatives | references pass; all negative cases rejected; all `official=true` |
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

## Recovery evidence

Both automated E2E and a CLI-derived run were exercised. The run was suspended immediately after the
durable patch checkpoint, resumed, reached the hidden evaluator and retained exactly one `PatchApplied`
event. Checkpoint/worktree hash corruption is separately rejected by test.

## Open gates

`patchloop doctor` now passes with authenticated `gh`, WSL2, Docker Desktop and the pinned evaluator image;
`official_evaluation_ready=true`. `patchloop dataset audit` still intentionally exits non-zero:
calibration is 5/5, admitted research is 6/20, and the stress sentinels are 0/3. The registry has no
contract or content-hash errors; it remains `draft` because the remaining 14 research tasks are not
admitted. No live OpenAI request or paid campaign was made.
