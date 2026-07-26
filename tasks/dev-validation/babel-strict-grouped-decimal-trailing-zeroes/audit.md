# Task audit: babel-strict-grouped-decimal-trailing-zeroes

- Dataset role: proposed `development-validation`
- Source: SWE-rebench V2 instance `python-babel__babel-1042`, split `train`
- Benchmark revision: `475dd5e8703bb5fb22dd3c60b5d038b019eba1e0`
- Benchmark row: 25179
- Upstream issue: <https://github.com/python-babel/babel/issues/928>
- Upstream resolution: <https://github.com/python-babel/babel/pull/1042>
- Base commit: `aca7663728e08e9d60b192b11fa6626a60974929`
- Base tree: `65feb399220abaca78c4634a29d50d57ac27fc3b`
- PR head: `e89a6c9c2f56c2e1a87330f45d801f8ca1f11cec`
- Squash-merge commit: `946efcdddb73d4470f2dc4e689aef0477a0ca02f`
- Resolution tree: `8659f9795b17d299eb63e7ffa9cc12d7a228fc40`
- License: BSD-3-Clause
- Retrieved: `2026-07-27T00:00:00Z`
- Benchmark gold patch SHA-256:
  `sha256:ff2ca11b6df2bd0567a8ad6a4687b8373ede412f649ad892a351055a584e449a`
- Benchmark test patch SHA-256:
  `sha256:de5e5c18eb65287a221260e56dd39c6008982eb96a47e0cc66ad92cc83af5349`
- Evaluator image:
  `docker.io/swerebenchv2/python-babel-babel@sha256:864e84fc4bdf09252f7fda4f85665cc05155a7b1d75847d61c67325abce7ef5a`
- Workflow: real-repository issue fix
- Failure pattern: fractional canonicalization assumes an all-zero tail
- Expected source change: `babel/numbers.py`
- Benchmark declaration: one F2P and 131 P2P tests
- Contamination risk: high. The issue, PR, benchmark row, and accepted patch
  are public.

The benchmark metadata's 36 modified lines counts additions to the production
patch, not total changed lines. The production diff is +36/-1; the complete
upstream PR also changes tests by +11/-1. PatchLoop keeps only the exact
production hunk and excludes the benchmark test patch.

The Git checkout intentionally lacks generated CLDR data. Both registered
checks import submitted code from `/workspace` and point only Babel's data
lookup globals at `/babel/babel/global.dat` and `/babel/babel/locale-data` in
the pinned evaluator image. The source-binding check ensures that this runtime
bootstrap cannot silently evaluate the image's baked production module.

The 16-check independent private oracle does not copy the issue value or
upstream test assertions. It covers dot-, comma-, and Arabic-decimal symbols,
Indian and narrow-space grouping, negative values, significant internal
zeroes, one- through three-zero suffixes, all-zero fractions, ungrouped and
non-strict compatibility, malformed grouping, duplicate and wrong-locale
separators, scale preservation, and submitted-source binding.

Difficulty audit:

| Dimension | Score | Reason |
| --- | ---: | --- |
| Localization | 1 | The defect is localized to strict validation in `parse_decimal`. |
| Reasoning depth | 1 | The fix must compare localized canonical form after removing only insignificant fractional padding. |
| Implementation breadth | 1 | One production module changes without a public API change. |
| Verification breadth | 2 | Locale separators, grouping systems, signs, significant zeroes, malformed inputs, and Decimal scale interact. |
| Total | 5 | Medium under `dataset-manifest-v1`. |

The package is staged, not admitted. Admission requires the clean base to pass
the public regression and fail the hidden oracle, the production reference to
pass three official Docker evaluations, every semantic and scope known-bad to
be rejected, and all resulting artifacts to be content-addressed.
