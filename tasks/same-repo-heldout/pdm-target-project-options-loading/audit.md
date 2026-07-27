# Task audit: pdm-target-project-options-loading

- Dataset role: admitted `core-same-repo`
- Source: SWE-rebench leaderboard instance `pdm-project__pdm-3759`, split `2026_03`
- Benchmark revision: `ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b`
- Benchmark row: 29
- Upstream issue: <https://github.com/pdm-project/pdm/issues/3756>
- Upstream resolution PR: <https://github.com/pdm-project/pdm/pull/3759>
- Benchmark base: `e96d535bb1bd64ac21575cf3490d64f737c6a668`
- Base tree: `472c1574aef690fc68be530c66a22a367657b8d8`
- PR head: `3c486795439627902dfa38a244e5f40e718aa948`
- Squash merge: `40034ac0af6acf6715ab961beaf14e6ef333c6d8`
- Maintainer follow-up: `0765ad9c1c8a7cf9444d16225f0f25e123f3085e`
- Follow-up tree: `124115768b9ce752a43b345db48da10be1d7a5f2`
- License: MIT
- Retrieved: `2026-07-27T00:27:00Z`
- Benchmark gold patch SHA-256:
  `sha256:1387d91c027a87bc4b36d602b70ac568e9ddd0d6f733816020cede93cee24294`
- Benchmark test patch SHA-256:
  `sha256:9f699b771294fdea007f96477159f39aeb50456c328cb378dfe4f0e41c6d666f`
- Exact benchmark production-only patch SHA-256:
  `sha256:8b542ad78f25ae5335106c231802fad1eb12873032ef657b6826e275b87bc88b`
- Hardened reference SHA-256:
  `sha256:9845af31ba7180d8ef73e17866d01abcd4b34c38726802c440b69f84c803aebb`
- Evaluator image:
  `swerebench/sweb.eval.x86_64.pdm-project_1776_pdm-3759@sha256:7a012a5bfd460d638b74d3de84426cd1fa2141aec3914c4f9171071491f5ac93`
- Workflow: real-repository issue fix
- Failure pattern: command defaults are read before the CLI-selected project is known
- Expected source change: `src/pdm/core.py`
- Benchmark declaration: one F2P and 63 P2P nodes
- Public regression: 63 base tests, after explicitly deselecting one declared P2P
  that attempts an external package install and fails under the mandatory
  network-disabled evaluator
- Private acceptance: submitted-source binding, short and long separated forms,
  attached short and long forms, repeated-option last-wins behavior,
  `PDM_PROJECT`, explicit object precedence, global-project isolation,
  cross-command behavior, missing-command-option isolation, and unchanged
  caller-project behavior
- Contamination risk: high. The issue, PR, benchmark row, original accepted patch,
  and maintainer follow-up are public.

The benchmark production patch is not PatchLoop's accepted reference. Its new
test mocks `parse_args` and invokes `-p` before the subcommand, even though the
real option belongs to each subcommand parser. The patch also scans raw arguments
before parsing, so it misses attached short forms, uses the first repeated option,
cannot honor parser-derived environment/global selection, and may disagree with
the explicitly supplied project object.

The PDM maintainer replaced that approach 58 minutes after the squash merge. The
follow-up parses the real CLI first, resolves the effective project through the
existing precedence policy, injects options from that project, and reparses only
when configured options were added. PatchLoop normalizes the follow-up's
`src/pdm/core.py` behavior onto the benchmark base as a one-file hardened
reference. The exact benchmark production hunk remains in the known-bad corpus
as `upstream-pr-extractor.patch`.

This task is distinct from development task
`pdm-ignore-active-venv-resolution`. The development task changes interpreter
candidate selection in `src/pdm/project/core.py`; this task changes CLI bootstrap
ordering and configuration source selection in `src/pdm/core.py`. They share a
repository but not a source module, trigger, failure mechanism, or solution
lineage.

Difficulty audit:

| Dimension | Score | Reason |
| --- | ---: | --- |
| Localization | 1 | The issue points to project selection, but the defect spans parse, project resolution, option injection, and reparse ordering. |
| Reasoning depth | 2 | Raw argument scanning must be rejected in favor of the parser's actual precedence and grammar. |
| Implementation breadth | 1 | One production module changes without a public API change. |
| Verification breadth | 2 | CLI spellings, repeats, environment, object/global precedence, multiple commands, and caller isolation differ. |
| Total | 6 | Hard under `dataset-manifest-v1`. |

Official admission used the pinned image with network disabled on clean harness
commit `ad25a8a95806d7e15597b03325af9de9108940b2`:

1. the unmodified base passed 63 public regressions and failed the independent
   hidden oracle;
2. the hardened reference passed all 11 hidden tests and 63 public regressions
   in three independent official runs;
3. the exact benchmark production patch and eight other semantic partial fixes
   failed hidden acceptance;
4. the forbidden test edit failed hidden acceptance, scope and test-tampering
   policy;
5. all 14 run records report `official=true` and made zero model/API calls.

The content-addressed
[admission report](../../../reports/docker-gate/research-pdm-target-project-options-loading.json)
records every run ID and patch, manifest, result and provenance hash. Its
SHA-256 is
`sha256:b39397b673438d3a98d125a3c34ddc1c1d58ab63527a552d08a13829ea6e5848`.
