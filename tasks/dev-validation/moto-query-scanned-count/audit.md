# Task audit: moto-query-scanned-count

- Dataset role: admitted `development-validation`
- Source: SWE-rebench V2 instance `getmoto__moto-7208`, split `train`
- Benchmark revision: `475dd5e8703bb5fb22dd3c60b5d038b019eba1e0`
- Benchmark row: 9878
- Upstream issue: <https://github.com/getmoto/moto/issues/7206>
- Upstream resolution: <https://github.com/getmoto/moto/pull/7208>
- Base commit: `624de34d82a1b2c521727b14a2173380e196f1d8`
- Base tree: `bf80fd425702651642b9ba655322b6daf8a4a424`
- PR head: `a64b7bcb4246760047d2cc1565d033fd0261693d`
- Squash-merge commit: `455fbd5eaa0270e03eac85a532e47ec75c7acd21`
- Resolution tree: `0e71074206f143c2c4fd175cc866c21e14a3f878`
- License: Apache-2.0
- Retrieved: `2026-07-26T20:31:52Z`
- Benchmark gold patch SHA-256:
  `sha256:1c068070effeafae13d0d261c7d7d7cbde115c6ac3e8b9fef17a61742e4c95cd`
- Benchmark test patch SHA-256:
  `sha256:13508ec3ce19a9b59a440eb12820f007410b0fa0fd09ad5fd37041220fd3df96`
- Normalized production reference SHA-256:
  `sha256:943e20a2eb696c6501d1d68b9988c2fb03bac79496dec4324d160b7abb922fe0`
- Evaluator image:
  `docker.io/swerebenchv2/getmoto-moto@sha256:dfdf957ab30b8829e8b6bbfd693b00fab88b7979d3c856362fd5d66c489a1fee`
- Workflow: real-repository issue fix
- Failure pattern: aggregate query accounting ignores partition, filter, and page boundaries
- Expected source change: `moto/dynamodb/models/table.py`
- Benchmark declaration: three F2P and 173 logical P2P nodes
- Contamination risk: high. The task, issue, PR, benchmark row, and accepted
  patch have been public since 2024.

The benchmark P2P list contains two truncated parameterized node names. Expanding
those two function groups produces 179 concrete P2P test cases, all of which pass
in the pinned image with Docker networking disabled. The visible check runs the
two containing upstream files and explicitly deselects nine tests that attempt
real AWS endpoints. Those nine tests are not members of the benchmark P2P list;
the resulting base command executes 182 tests, including every declared P2P
case and the pre-patch forms of the three F2P tests.

PatchLoop uses the exact production hunk from the accepted PR and excludes the
benchmark test patch. Applying the normalized reference reproduces the PR-head
blob `c675a7becacf8314fca2bd7a4dfb29483795fcdf` for the production module. The
independently authored private oracle does not copy
the issue's example or benchmark assertions. It covers partition scoping,
pre-filter accounting, range conditions, three-page traversal, filtered limits,
projections, reverse ordering, global secondary indexes, empty results, and
submitted-source binding.

Difficulty audit:

| Dimension | Score | Reason |
| --- | ---: | --- |
| Localization | 1 | The defect is localized to `Table.query`, but accounting is spread across selection, filtering, sorting, and trimming stages. |
| Reasoning depth | 2 | Correctness requires distinguishing key conditions, post-query filters, limits, prior pages, size boundaries, and index keys. |
| Implementation breadth | 1 | One production module changes without a public API change. |
| Verification breadth | 2 | Partition, range, filter, pagination, projection, ordering, index, and empty-result semantics interact. |
| Total | 6 | Hard under `dataset-manifest-v1`. |

Authoring probes on the pinned image show the normalized reference passes all
9 independent checks, while the clean base fails 7 checks. Six semantic partial
fixes each fail at least one distinct private boundary. These probes are not
admission evidence.

Admission evidence from clean harness commit
`b4cc0ec8d2dffad907f31ed8ffac220ed0353c38` shows:

1. the normalized production reference passes regression, hidden, scope, and
   safety verdicts in runs `run_cee764017ee14f6f`,
   `run_e3c92f006f094766`, and `run_ebb46abb00ea4da9`;
2. the clean base passes all 182 selected regressions and fails the private
   acceptance boundary in `run_7e5dad51ff294ca7`;
3. all six semantic partial fixes pass the public regression and fail private
   acceptance;
4. the forbidden test edit fails hidden acceptance, scope, and test-tampering
   policy;
5. all runs are `official=true`, execute without container networking, and make
   zero model or API calls.

The content-addressed case ledger is
`reports/docker-gate/research-moto-query-scanned-count.json`. The task may be
used only for rendering, no-match, and leak validation. Its runs are prohibited
from memory-entry generation and the held-out core denominator.
