# Task audit: pyfakefs-file-wrapper-io-capabilities

- Admission state: screened candidate awaiting the clean official Docker matrix
- Proposed dataset role: `core-same-repo`
- Source: SWE-rebench leaderboard aggregate `test` row 653, instance
  `pytest-dev__pyfakefs-1269`
- Frozen benchmark revision:
  `ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b`
- Local frozen dataset artifact:
  `.patchloop/candidate-data/test-ab4805d.parquet`
- Local dataset artifact SHA-256:
  `sha256:1497b218db0a8259d22471812f0de12b779c699daf741b930d68bc717636f0bf`
- Upstream issue: <https://github.com/pytest-dev/pyfakefs/issues/1265>
- Upstream resolution: <https://github.com/pytest-dev/pyfakefs/pull/1269>
- Base commit: `a3685da29db2f185d4793f185ca07dfe36f3d9a9`
- Base tree: `26d02d6f220a83e54f41cd1d08a16ba9c469c68f`
- Resolution merge commit: `9f6d8bcd873002dd0d315b195e2675261e96d39b`
- License at the base commit: Apache-2.0
- Retrieved: `2026-07-27T21:23:39Z`
- Frozen source image:
  `swerebench/sweb.eval.x86_64.pytest-dev_1776_pyfakefs-1269:latest`
- Registry manifest digest:
  `sha256:02c69afcbf763a1ede2637197e0979327f7b29392f2fedeead6e2a17e8746a91`
- Benchmark gold patch SHA-256:
  `sha256:477352e8cb5b51653d1ac2afbde24dadf329cbc46afb98ce8a983cd2b457d9e6`
- Benchmark production patch SHA-256:
  `sha256:21f7350ac6a344e0a076a91491e41f0a08f223c32be5f4354c4db1ccc460fa7d`
- Benchmark test-patch SHA-256:
  `sha256:39edf7cfec5497ae55af6ccb0b6ba3f6c0d606cc00543bfd9a074f352594e47a`
- Base production blob: `2cc3f1eda46008fafa8fafbaa19af716b50f6ff6`
- Accepted production blob: `293b39340acd8e75ccc1902e2bf86b5c84f64336`
- Benchmark patch files: `CHANGES.md`, `pyfakefs/fake_file.py`
- Benchmark test-patch file: `pyfakefs/tests/fake_open_test.py`
- Benchmark patch size: 58 serialized lines; production hunk 43 lines,
  `+11/-3`
- Benchmark test-patch size: 34 serialized lines, `+23/-0`
- Benchmark F2P/P2P: 1/431
- Expected submitted source change: `pyfakefs/fake_file.py`
- Workflow: real-repository file-like protocol bug fix
- Failure pattern: capability query is routed through an operation guard
- Solution lineage: `pytest-dev-pyfakefs-pr-1269`

The source of `reference.patch` is the exact `pyfakefs/fake_file.py`
production hunk in the frozen benchmark row. It matches accepted upstream PR
#1269. The changelog hunk and benchmark test patch are deliberately excluded.

The private-v2 oracle is independently authored and hash-bound. It contains
ten pytest functions collecting 29 cases. It checks the complete `r/w/a/x/+`
capability matrix for text and binary handles, `io.TextIOWrapper`
construction and binary-backed writes, disallowed operation errors, update
mode behavior, readable iteration, submitted-source binding, and whether
dynamic read and iterator guards honor the capability method rather than
duplicating stale mode checks.

`equivalent/dynamic-capability-interface.patch` is an
implementation-independent positive control. It exposes the same callable
protocol dynamically through `__getattr__` and does not add the accepted
reference methods to the class body. The oracle must accept both this design
and the exact upstream reference.

The known-bad corpus contains one no-op, nine semantic partials, and one
forbidden test edit. The semantic partials cover methods that do not control
the internal guards, constant capability answers, mirrored and inverted
capabilities, backing-buffer leakage, loss of `+` semantics, boolean
properties in place of methods, and omission of the writable protocol.

This task intentionally permits a public API change because the accepted fix
adds the standard file-like `readable()` and `writable()` methods. Scope
remains limited to one production module, while hidden behavior and the
known-bad corpus bound the intended API extension.

This lineage is independent of the memory-development task
`pyfakefs-makedirs-parent-traversal` from PR #991. That task changes
`pyfakefs/fake_os.py` to preserve path-component traversal side effects. This
candidate changes `pyfakefs/fake_file.py` to separate capability
introspection from actual file operations.

Difficulty audit:

| Dimension | Score | Reason |
| --- | ---: | --- |
| Localization | 1 | The traceback identifies the file wrapper, though the capability query reaches it through dynamic dispatch. |
| Reasoning depth | 1 | The fix must distinguish an introspection call from an attempted operation and preserve mode semantics. |
| Implementation breadth | 1 | One production module changes with a narrow standard file-like API extension. |
| Verification breadth | 2 | Text/binary and read/write/append/exclusive/update modes, wrapper integration, operation errors and iterator guards diverge independently. |
| Total | 5 | Medium under `dataset-manifest-v1`; it is not inflated to hard despite the 431-test regression surface. |

The candidate is not admitted by this document. Admission still requires a
clean harness commit, base visible pass/private hidden fail, three official
reference passes, an official equivalent-solution pass, rejection of all
declared bad patches, and content-addressed run evidence.
