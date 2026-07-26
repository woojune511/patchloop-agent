# Task audit: pdm-ignore-active-venv-resolution

- Dataset role: proposed `memory-development`
- Source: SWE-rebench V2 instance `pdm-project__pdm-2781`, split `train`
- Benchmark revision: `475dd5e8703bb5fb22dd3c60b5d038b019eba1e0`
- Benchmark row: 19118
- Upstream issue: <https://github.com/pdm-project/pdm/issues/2779>
- Upstream resolution: <https://github.com/pdm-project/pdm/pull/2781>
- Base commit: `881cd4e38d31663ae67bdae227ec1ccdfd5e2c77`
- PR head: `455dd5b36ce86c7c7e729d13892655aa81d2adf1`
- Squash-merge commit: `b99b17224879695780adf00ebe8cd0d09574498e`
- Resolution tree: `cfdb34943e3233101166a0f2d482728608172c5d`
- License: MIT
- Retrieved: `2026-07-26T18:49:04Z`
- Benchmark gold patch SHA-256:
  `sha256:6017923b36942ed8f2f59638383f1bb3613e1259c6b14c2142bdd31d76dcc4ec`
- Benchmark test patch SHA-256:
  `sha256:6ac90001c762af5af11f670f5a2b1aecff84d946b716e7ccb74ac09a3f772d95`
- Evaluator image:
  `docker.io/swerebenchv2/pdm-project-pdm@sha256:a822ad3888e56650c18e9506f8d7882c145ed83d47d518e541e3e44406a929a0`
- Workflow: real-repository issue fix
- Failure pattern: an exclusion flag short-circuits the containing interpreter search
- Expected source change: `src/pdm/project/core.py`
- Public regression: 36 tests collected from the base `tests/test_project.py`
- Benchmark P2P declaration: 37 nodes; one false-flag parameter exists only after the
  benchmark test patch and is covered independently by the private oracle
- Private acceptance: source binding, truthy and false-like flag semantics,
  VIRTUAL_ENV and CONDA_PREFIX, associated-environment fallback, create fallback,
  path-component boundaries, no-active-prefix behavior, and saved-interpreter precedence
- Leakage control: benchmark interface, PR description, gold patch, test patch,
  reference patch, and hidden assertions remain evaluator-only and are excluded
  from agent context and memory source text
- Contamination risk: high. The task, benchmark training row, issue, PR, and code
  review have been public since 2024.

The benchmark gold patch also adds a news fragment. PatchLoop uses the exact upstream
production hunk as a normalized reference and excludes both the news fragment and upstream
test patch. The PR head and squash-merge commit have different commit IDs but the same
resolution tree.

The image working directory is `/pdm`, while PatchLoop mounts the submitted checkout at
`/workspace`. Every check pins `PYTHONPATH=/workspace/src` and writable cache/home roots
under `/tmp`. The private oracle additionally verifies that `pdm.project.core` was imported
from the submitted checkout.

Difficulty audit:

| Dimension | Score | Reason |
| --- | ---: | --- |
| Localization | 1 | The failure is in interpreter resolution, but the flag affects multiple candidate sources. |
| Reasoning depth | 2 | The fix must distinguish exclusion from branch disabling and interpret false-like values. |
| Implementation breadth | 1 | One production module changes without a public API change. |
| Verification breadth | 2 | Active, managed, created, Conda, false-like and path-boundary cases differ. |
| Total | 6 | Hard under `dataset-manifest-v1`. |

Admission requires an official network-disabled Docker gate showing:

1. the unmodified base passes 36 public regressions and fails private acceptance;
2. the normalized production reference passes hidden, regression, scope, and safety
   verdicts three times;
3. every declared known-bad patch applies cleanly and fails at its intended boundary;
4. source commit, image, specs, patch, manifest, result, and provenance are content-addressed.

The hidden tests are independently authored from the reported behavior. They do not copy the
benchmark F2P test, create a real virtual environment, or inspect implementation helper names.
