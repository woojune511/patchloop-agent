# PatchLoop dataset card

## Purpose

The dataset evaluates whether failure-memory representations change coding-agent reliability under fixed
model, prompt, tools and budgets. The evaluator outcome is deterministic; `bad_patch` is never a model
prediction.

## Current contents

Five independently content-addressed `mini-data-utils` tasks are audited and executable as calibration
fixtures. They validate task authoring, sandboxing and deterministic evaluation; they are not members of
the research dataset.

Original smoke fixtures:

- `csv-quoted-newline`: parser state across quoted LF/CRLF fields
- `config-falsy-override`: explicit falsey values in merge semantics
- `path-prefix-boundary`: segment boundaries and parent-segment normalization

Additional calibration fixtures stored under the historical `dev-train` path:

- `duration-minute-boundary`: completed-unit semantics around elapsed-minute boundaries
- `csv-final-record-flush`: parser-state finalization when chunked input reaches EOF

Each package contains public issue/check metadata, evaluator-only hidden acceptance, a reviewed reference
patch and known-bad patches. All five are excluded from failure-memory generation, the core SCRR
denominator and performance headlines. A physical directory such as `dev-train` does not override the
dataset-manifest role.

The fourteen admitted research tasks are:

- `loguru-invalid-format-feedback`, derived from SWE-rebench `delgan__loguru-1451` and upstream
  Loguru issue #1450 / PR #1451. Its admission evidence contains three reference passes, one base hidden
  failure, 20 upstream regression tests and five independently authored known-bad patch rejections.
- `anyio-interrupt-runner-cleanup`, derived from `agronholm__anyio-1121` and upstream AnyIO issue
  #1060 / PR #1121. A later upstream incident showed that the original fix regressed normal pytest
  outcome handling, so PatchLoop uses a hardened reference and rejects a source-equivalent normalization
  of the original fix. It records three official passes, 20/20 hidden-oracle stability runs, 32 P2P
  regressions, one base hidden failure and five known-bad rejections.
- `tox-cross-section-empty-substitution`, derived from `tox-dev__tox-3810` and upstream tox issue
  #3809 / PR #3810. Its oracle distinguishes a factor-filtered empty value from a missing cross-section
  key while preserving an earlier same-section fallback contract. It records three official passes,
  29 P2P regressions, six independent hidden checks, one base hidden failure and five known-bad
  rejections.
- `hf-hub-xet-endpoint-propagation`, derived from SWE-rebench V2
  `huggingface__huggingface_hub-3180` and upstream Hugging Face Hub issue #3168 / PR #3180.
  Its oracle checks endpoint context across parser, internal download and `HfApi` boundaries while
  preserving relative and foreign-origin routes. It records three official passes, 15 P2P regressions,
  eight independent hidden checks, one base hidden failure and six known-bad rejections.
- `pdm-ignore-active-venv-resolution`, derived from SWE-rebench V2 `pdm-project__pdm-2781` and
  upstream PDM issue #2779 / PR #2781. Its oracle distinguishes excluding the active environment from
  disabling interpreter search, including false-like settings, `VIRTUAL_ENV`, `CONDA_PREFIX`,
  associated-environment and create fallbacks, and path-component boundaries. It records three official
  passes, 36 base-checkout regressions, ten independent hidden checks, one base hidden failure, six
  semantic known-bad rejections and one scope/test-tampering rejection. The benchmark declares 37 P2P
  nodes because one passing parameter exists only in its test patch.
- `pyfakefs-makedirs-parent-traversal`, derived from SWE-rebench V2
  `pytest-dev__pyfakefs-991` and upstream pyfakefs issue #987 / PR #991. Its oracle compares ordered
  path-component effects across POSIX and Windows modes while preserving nested and bytes paths,
  `exist_ok`, invalid-parent errors and leaf-only mode application. It records three official passes,
  all 517 declared P2P regressions, 12 independent hidden checks, one base hidden failure, seven
  semantic known-bad rejections and one scope/test-tampering rejection.
- `moto-query-scanned-count`, derived from SWE-rebench V2 `getmoto__moto-7208` and upstream
  Moto issue #7206 / PR #7208. Its oracle locates query cardinality at the boundary between key
  selection and non-key filtering across partitions, ranges, pagination, global secondary indexes,
  projections and empty results. It records three official passes, 182 selected upstream regressions,
  nine independent hidden checks, one base hidden failure, six semantic known-bad rejections and one
  scope/test-tampering rejection. The nine deselected endpoint tests are outside the benchmark P2P
  declaration; every one of the 173 logical P2P nodes is represented by 179 passing concrete cases.
- `babel-strict-grouped-decimal-trailing-zeroes`, derived from SWE-rebench V2
  `python-babel__babel-1042` and upstream Babel issue #928 / PR #1042. Its public-API oracle distinguishes
  insignificant fractional padding from significant internal zeroes across dot, comma and Arabic decimal
  symbols, Western and Indian grouping, signs, malformed inputs and Decimal scale. It records three
  official passes, all 132 upstream number tests, 16 independent hidden checks, one base hidden failure,
  seven semantic known-bad rejections and one scope/test-tampering rejection. The pinned image supplies
  generated CLDR data while a source-binding check proves that submitted code is imported from
  `/workspace`.
- `sqlglot-duckdb-ignore-nulls-modifier-order`, derived from SWE-rebench leaderboard instance
  `tobymao__sqlglot-7187` and upstream SQLGlot issue #7179 / PR #7187. Its hardened oracle checks
  symmetric `IGNORE NULLS` / `RESPECT NULLS` handling across five value-window functions, DuckDB
  prefix-to-suffix canonicalization, argument/window AST separation, and a representative BigQuery
  `HAVING MAX` / `ORDER BY` / `LIMIT` negative-transfer guard. It records three official reference
  passes, all 39 upstream DuckDB tests, 21 independent hidden checks, one base hidden failure, seven
  semantic partial rejections and one scope/test-tampering rejection.
- `param-shared-rx-fanout-cache`, derived from SWE-rebench leaderboard instance
  `holoviz__param-1117` and upstream Param issue #1116 / PR #1117. Its exact production reference
  links cloned reactive branches to one shared source evaluation while preserving invalidation and
  branch-local accessor semantics. It records three official reference passes, all 94 upstream
  reactive regressions, ten independent hidden checks, one base hidden failure, eight semantic
  partial rejections and one scope/test-tampering rejection. The evaluator image is pinned by digest,
  and the public issue, patch and one-file localization make the disclosed contamination risk high.
- `pdm-target-project-options-loading`, derived from SWE-rebench leaderboard instance
  `pdm-project__pdm-3759` and upstream PDM issue #3756 / PR #3759. The original benchmark patch scanned
  raw arguments before the real parser and its test mocked the parser while using an invalid option
  order. PatchLoop therefore normalizes the maintainer's immediate follow-up onto the benchmark base and
  rejects the exact benchmark production patch. The oracle covers attached and repeated project flags,
  environment and explicit-object precedence, global isolation, multiple commands and caller-option
  fallback. It records three official reference passes, 63 network-independent upstream regressions,
  11 hidden checks, one base hidden failure, nine semantic rejections and one scope/test-tampering
  rejection. One declared P2P node that attempts an external install is explicitly deselected.
- `anyio-extensionless-entrypoint-worker-main`, derived from SWE-rebench leaderboard instance
  `agronholm__anyio-1134` and upstream AnyIO issue #1027 / PR #1134. Its exact one-file production
  reference reconstructs extensionless entrypoints in process workers. The independent oracle checks
  submitted-source binding, asyncio and trio, unknown suffixes, path spaces, `__main__` /
  `__mp_main__` identity, module metadata, exactly-once loading, worker reuse, ordinary `.py`
  compatibility and initialization-error propagation. It records three official reference passes,
  all 36 upstream process regressions, 11 hidden checks, one base hidden failure, nine semantic
  rejections and one scope/test-tampering rejection.
- `hf-hub-custom-tqdm-class-contract`, derived from SWE-rebench leaderboard instance
  `huggingface__huggingface_hub-4056` and upstream Hugging Face Hub issue #4050 / PR #4056.
  Its exact production reference separates caller-owned progress constructors from Hub-owned
  subclass policy in both file and snapshot downloads. The 15-case independent oracle covers strict
  custom classes, foreign upstream-tqdm subclasses, function and partial factories, existing bars,
  offline file and snapshot flows, and Hub group/log/TTY/TQDM_POSITION behavior. It records three
  official passes, one base hidden failure, nine semantic rejections and one scope/test-tampering
  rejection. The public base contains 17 regressions; two additional P2P nodes exist only in the
  excluded benchmark test patch, producing the separately disclosed benchmark count of 19.
- `mtplx-mixed-content-tool-call-stream`, derived from SWE-rebench leaderboard instance
  `youssofal__mtplx-21` and upstream MTPLX issue #20 / PR #21. Its hardened reference recognizes
  exact, case-insensitive `<tool_call>` delimiters across arbitrary chunks, preserves mixed preamble
  and lookalike tags as content, reconstructs ordered call deltas and rejects non-whitespace residue
  beside or between complete calls without changing the non-streaming parser. It records three
  official reference passes, 55 base-resident OpenAI bridge regressions, 21 independent hidden
  cases, one base hidden failure, nine semantic rejections and one scope/test-tampering rejection.
  The exact upstream accepted source patch is one of the rejected semantic patches. The digest-pinned
  external image has no configured `User` and therefore ran as Docker's default root user; network
  denial and read-only root and submitted filesystems were still enforced.

All fourteen tasks pin an exact upstream base commit, upstream license evidence and a digest-addressed
SWE-rebench evaluator image. Seven are MIT licensed, including both PDM tasks, both AnyIO tasks and
SQLGlot; both Hugging Face Hub tasks, pyfakefs, Moto and MTPLX are Apache-2.0; Babel and Param are
BSD-3-Clause. Together with the five calibration fixtures, the curated manifest currently contains
19 task entries.

## Research dataset target

The research target is 20 newly admitted tasks, separate from the five calibration fixtures.

| Manifest role | Target | Memory source | Currently admitted |
| --- | ---: | --- | ---: |
| Memory development | 6 | reviewed failures only | 6 |
| Development validation | 2 | no | 2 |
| Core same-repo | 6 | prohibited | 3 |
| Core cross-repo | 6 | prohibited | 3 |
| **Research total** | **20** |  | **14** |

Repeated runs of one task must stay in the same role. Development and held-out tasks may share a failure
pattern, but not a solution lineage. Private checks and reference patches are excluded from context,
agent-visible traces and memory source text.

Research admission requires immutable benchmark/upstream provenance, an independently reviewed
medium-or-harder difficulty audit, a base visible-pass/private hidden-fail result, three official Docker
reference passes and at least three representative bad-patch rejections. An executable calibration
fixture or a row in a candidate ledger is not an admitted research task.

## OSS audit

`astanin/python-tabulate` rows in `oss-candidate-ledger.csv` are candidate inventory only. They must pass
source, license, environment, issue/test alignment, dependency, base-test, hidden-acceptance, difficulty
and solution-lineage audits before registration. No `python-tabulate` task is currently admitted.

`benchmark-candidate-ledger.csv` records the pinned SWE-style shortlist and
`terminal-bench-pattern-ledger.csv` records direct-import/adaptation decisions. Candidate rows are not
admissions.

The same-repository tox #3904 candidate is explicitly excluded under the current contract. Its accepted
solution adds `python-discovery` as a direct dependency; omitting that metadata relies on an undeclared
transitive package, while the dependency-free architecture taxonomy was rejected in upstream review and
later shown incomplete. PatchLoop's current binary dependency policy cannot allow only that audited
package and metadata file, so the task can be reconsidered only after a dependency allowlist contract is
implemented.

SWE-style benchmark instances and upstream issue/PRs are the primary research candidate sources.
Terminal-Bench 2.1 is used to shape a three-sentinel reliability overlay and external acceptance lane.
Terminal tasks that depend on unrestricted shell, runtime network, binary forensics or background service
administration are not imported into the core suite. Code-writing candidates must first be adapted to the
PatchLoop constrained tool, registered check, submitted patch and separate hidden evaluator contract.

The three stress sentinels are selected from admitted research tasks and receive deterministic
`context-reset`, `worker-kill-after-patch` and `test-timeout` overlays. They do not add to the 20-task
research target and their results are not aggregated into the 96-run core campaign.

## Intended metrics

SCRR, hidden pass, regression-free, scope violations, recovery, cost per success, token overhead and
success/failure flips are reported. Two repetitions are first averaged per task; paired task bootstrap uses
10,000 samples, seed 20260723 and a 95% percentile interval.

Calibration, stress and external acceptance results are always shown separately from research/core
headlines.
