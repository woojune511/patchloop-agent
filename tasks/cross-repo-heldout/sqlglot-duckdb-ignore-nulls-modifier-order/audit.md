# Task audit: sqlglot-duckdb-ignore-nulls-modifier-order

- Dataset role: proposed `core-cross-repo`
- Source: SWE-rebench leaderboard instance `tobymao__sqlglot-7187`, split `2026_03`
- Benchmark revision: `ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b`
- Benchmark row: 40
- Upstream issue: <https://github.com/tobymao/sqlglot/issues/7179>
- Upstream resolution: <https://github.com/tobymao/sqlglot/pull/7187>
- Base commit: `0e8d0824c40ac46c5e7275180cf2eaae6810f805`
- Base tree: `c18f45f4f5928bd76f85bf85cdf3fe1eb5bc0675`
- PR head: `1fbc1c120a1f5e8a786765d8d2c503ca27d01454`
- Merge commit: `baa9974b8042eaef7897537772b1002c30e503b8`
- License: MIT
- Retrieved: `2026-07-26T23:43:49Z`
- Benchmark production patch SHA-256:
  `sha256:3f2d45f2116df6bb68432756ae243b27826d42b2a36d856caf55f22085018f7b`
- Benchmark test patch SHA-256:
  `sha256:06b0e421d8b686defbc6f6f5a2caf751296cb19dd9f2af1f5744722252f46661`
- Evaluator image:
  `swerebench/sweb.eval.x86_64.tobymao_1776_sqlglot-7187@sha256:43c43d77e3bed15361140767e3f3fd84811e0bad5b58f6afcba83f79b8e58303`
- Workflow: real-repository issue fix
- Failure pattern: parser and generator disagree about the position of a dialect-specific NULL modifier
- Expected source changes: `sqlglot/parser.py`, `sqlglot/generator.py`, and
  `sqlglot/dialects/duckdb.py`
- Benchmark declaration: one F2P and 38 P2P tests
- Contamination risk: high. The issue, PR, benchmark row, accepted patch, and
  the exact three production-file localizations exposed by `allowed_paths` are
  public.

The benchmark production patch changes three modules. PatchLoop exposes those
paths as a constrained localization boundary, excludes the upstream test hunk
in `tests/dialects/test_duckdb.py`, and evaluates the production-only
resolution against an independently authored hardened oracle. This adaptation
extends the single upstream F2P case with symmetric IGNORE/RESPECT behavior,
the five affected value-window functions, canonical prefix handling,
argument/window separation, and a representative BigQuery negative-transfer
guard. The oracle uses different identifiers, clauses, and values from the
upstream reproduction and test patch. These additions strengthen acceptance;
they do not reduce the recorded high contamination risk or make the task
eligible for prompt, tool, threshold, or memory tuning after the core split is
frozen.

The 21-check private oracle checks submitted-module binding, symmetric trailing
IGNORE and RESPECT forms across FIRST_VALUE, LAST_VALUE, NTH_VALUE, LAG, and
LEAD, prefix-form canonicalization, offsets and defaults, named windows,
multiple ordered arguments, outer frames, AST placement, round trips, existing
DuckDB forms, and representative BigQuery modifier ordering including its
HAVING MAX / ORDER BY / LIMIT chain. This is a targeted cross-dialect guard, not
an exhaustive proof over every SQLGlot dialect. The public registered check
runs all 39 methods in the pinned image's DuckDB dialect test module: the 38
declared P2P methods plus the original F2P method before the benchmark test
patch is applied. The pinned image does not install the DuckDB runtime package,
so the oracle deliberately validates parser, AST, and generator behavior
without adding a new dependency.

The bad-patch corpus contains a no-op baseline, seven distinct implementation
omissions, and one forbidden test edit. Some omissions are nested component
ablations and are not claimed as statistically independent failure modes.

Difficulty audit:

| Dimension | Score | Reason |
| --- | ---: | --- |
| Localization | 1 | The issue identifies DuckDB parsing, but the fix spans parser, shared generator, and dialect policy. |
| Reasoning depth | 2 | Parser acceptance and dialect-specific generation order must agree without changing other dialects. |
| Implementation breadth | 2 | Three production modules participate in the accepted resolution. |
| Verification breadth | 2 | IGNORE/RESPECT, prefix/trailing forms, AST placement, round trips, and cross-dialect behavior interact. |
| Total | 7 | Hard under `dataset-manifest-v1`. |

Admission requires a clean committed harness and official network-disabled
Docker evidence showing:

1. the base passes all 39 upstream DuckDB methods and fails private acceptance;
2. the production-only reference passes hidden, regression, scope, and safety
   verdicts three times;
3. every semantic partial fix and the forbidden test edit is rejected at its
   intended boundary;
4. source commit, image digest, specs, patch, manifests, results, and provenance
   are content-addressed.

Admission evidence is pending.
