# Task audit: loguru-post-2038-local-timezone-fallback

- Admission state: candidate; official Docker matrix pending
- Proposed dataset role: `core-same-repo`
- Source: SWE-rebench leaderboard aggregate `test` row 209, corresponding to
  the 2025-02 bucket, instance `Delgan__loguru-1297`
- Frozen benchmark revision:
  `ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b`
- Local frozen dataset artifact:
  `.patchloop/candidate-data/test-ab4805d.parquet`
- Local dataset artifact SHA-256:
  `sha256:1497b218db0a8259d22471812f0de12b779c699daf741b930d68bc717636f0bf`
- Upstream issue: <https://github.com/Delgan/loguru/issues/1291>
- Upstream resolution: <https://github.com/Delgan/loguru/pull/1297>
- Base commit: `e310e2029102b5d63a679a2b64501c045aa86336`
- Resolution commit: `258326b747761a5c2430161b9f52b04bd7644014`
- License at the base commit: MIT
- Frozen source image:
  `swerebench/sweb.eval.x86_64.delgan_1776_loguru-1297:latest`
- Registry manifest digest:
  `sha256:8d899d1147cf88bc088afe57fc5299fdcf2fafe6a1e30ef26825577e8953362f`
- Benchmark patch files: `CHANGELOG.rst`, `loguru/_datetime.py`
- Benchmark test-patch files: `tests/conftest.py`, `tests/test_datetime.py`
- Benchmark patch size: 67 serialized diff lines; 39 changed lines, of
  which 38 are in the production module
- Benchmark test-patch size: 124 serialized diff lines; 58 changed lines
- Benchmark F2P/P2P: 4/34
- Expected submitted source change: `loguru/_datetime.py`
- Workflow: real-repository platform-boundary bug fix
- Failure pattern: platform local-time metadata cannot construct a valid timezone
- Solution lineage: `delgan-loguru-pr-1297`

The source of `reference.patch` is the `loguru/_datetime.py` production hunk
in the frozen benchmark row's `patch` field. It matches the accepted upstream
PR #1297 production change; the row's `CHANGELOG.rst` hunk and its separate
`test_patch` field are deliberately omitted. The upstream issue is labeled
`bug`, not `easy` or `good first issue`, and the accepted behavior remains
present on Loguru's current `master` branch as of the provenance review.

This lineage is independent of the memory-development task
`loguru-invalid-format-feedback` from PR #1451. That task changes
`loguru/_handler.py` to preserve diagnostic context across a formatting catch
boundary. This task changes `loguru/_datetime.py` to preserve timezone
construction across platform conversion failures.

Difficulty audit:

| Dimension | Score | Reason |
| --- | ---: | --- |
| Localization | 1 | The traceback points to timezone construction, but the safe fallback belongs around multiple platform-data boundaries. |
| Reasoning depth | 2 | The fix must distinguish invalid offsets, platform range errors, absent struct fields, and the valid fast path. |
| Implementation breadth | 1 | One internal production module changes, with reusable fallback and selection helpers. |
| Verification breadth | 2 | Deterministic validation must simulate Windows-only failures while preserving offset, zone name, wall time, and microseconds on Linux. |
| Total | 6 | Hard under `dataset-manifest-v1`. |

The private oracle is independently authored. It has five pytest test
functions collecting 11 independent parameter cases. Every case runs the
submitted source in a fresh subprocess and replaces all host-sensitive clock
and timezone inputs with deterministic values. Three independent fallback
profiles exercise positive, negative, and date-rollover-derived offsets with
different zone names, so a fixed offset or name cannot satisfy the oracle. The
cases check:

1. valid negative, zero, and positive platform offsets and names remain
   authoritative (three cases);
2. invalid positive and negative offsets use the datetime-derived fallback;
3. `OSError` and `OverflowError` from local-time conversion use the fallback;
4. missing both fields, a missing zone, and a missing offset independently use
   the fallback;
5. fallback offset and zone name are derived rather than hard-coded;
6. local wall-clock fields and microseconds are preserved; and
7. an unsupported `RuntimeError` is propagated rather than hidden by a broad
   exception handler.

The known-bad corpus contains one no-op, nine semantic partials, and one
forbidden test edit. The semantic partials cover fixed UTC fallback, clamped
offsets, a fixed derived-looking offset and name, wrong supported range
exceptions, a wrong timezone-construction exception, reversed offset
derivation, discarded fallback zone names, bypass of valid platform metadata,
and an overly broad local-time exception catch.

The candidate is not admitted until a clean pinned-image evaluation proves
base visible-pass/private-fail, the same reference passes three official
network-disabled runs, and every declared semantic and scope bad patch is
rejected. No result in this package claims those pending observations.
