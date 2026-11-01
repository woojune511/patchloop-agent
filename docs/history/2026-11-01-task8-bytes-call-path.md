# Task8 bytes through add_new and save_as: the submitted patch still fails

Date: 2026-11-01. CLOSED, provider-free public diagnostic; official=false,
claim-ineligible. Operator-selected cases, no model or private evaluation.

## Question and selection

The [unchanged regression comparison](2026-11-01-task8-public-test-comparison.md)
showed a buffer-input assertion FAIL-to-PASS, but left its connection to the
reported bytes failure unverified. The user requested a diagnostic preserving the
original bytes representation and `add_new -> save_as` API path. This distinguishes
a relevant repair from success on a different input representation.

Public `dataelem.py:434` provides a discriminating condition: the value setter
splits bytes on backslash unless the VR is excluded. OB and OF are excluded; OL
is not. The submitted `memoryview(...).tobytes()` patch starts later, in
`_convert_value`. The leading hypothesis was that bytes containing `0x5c` become
a list before that patch can handle them, leaving the reported write error intact.
Candidate-only success on this input would contradict that prediction; failure of
the controls or setup would weaken attribution to this OL branch.

The cases, predicted mechanism, alternative outcomes, source and program hashes,
image and execution bounds were frozen before dispatch. No reference patch,
private assertion or prior successful agent patch was used as the test oracle.
This is an operator diagnosis on a development-exposed task, not blind autonomous
discovery or a held-out improvement result.

## Controlled execution

Same H-array-to-bytes representation, tag `(0066,0040)`, nested sequence item and
parent file writer on both original and submitted code:

```python
data = array.array('H', indexData).tobytes()
lineSeq.add_new(0x00660040, vr, data)
ds.save_as(filename)
```

The ordinary values are `[1, 2, 3, 4, 5, 6, 7, 8, 9]`; the trigger changes only
the fifth element from 5 to 92. Both serialize to 18 bytes on the pinned little-endian
environment. Exactly one byte differs, offset 8: `0x05 -> 0x5c`.

- Ordinary: `010002000300040005000600070008000900`.
- Trigger: `01000200030004005c000600070008000900`.

Each input runs as OL and as the issue's OB/OF controls. A minimal `FileDataset`
contains `SurfaceSequence -> SurfaceMeshPrimitivesSequence -> lineSeq`, with
implicit little-endian transfer syntax and fixed metadata. Successful writes are
read back through `dcmread`; both stored and readback bytes must equal the input.
No `bytearray` or array object is passed to `add_new`, and no test expectation is
changed between phases.

Two isolated public check executions run six cases each. The original and submitted
workspaces come from the same base; the submitted workspace receives the exact
saved patch. The existing public temporary-copy launcher preserves source priority
and excludes Git/private directories. The same program runs under the same existing
pinned image, with no network and read-only source/root. Bounds are 60 seconds per
execution and 300 seconds total. No Docker startup, image pull/build or credential
loading occurs.

## Observed result

| Input and VR | Original code | Submitted patch |
| --- | --- | --- |
| Ordinary bytes, OL | PASS, exact roundtrip | PASS, exact roundtrip |
| Bytes containing `0x5c`, OL | FAIL at `save_as` | FAIL at `save_as` |
| Both bytes inputs, OB and OF | Four PASS, exact roundtrip | Four PASS, exact roundtrip |

For the failing case, `add_new` returns but the element already contains
`pydicom.multival.MultiValue` instead of the original bytes. It holds two byte
chunks separated at the backslash. `ds.save_as` then raises:

```text
TypeError: a bytes-like object is required, not 'MultiValue'
```

This occurs on both original and submitted code. Retained traceback evidence
includes `Dataset.save_as -> dcmwrite` and the nested writer's
`write_OWvalue` at `filewriter.py:284`, where `fp.write(elem.value)` receives the
wrong type. OL and OF share this writer, but only OL's value is split earlier.
The completed observations are five PASS and one FAIL per phase; the diagnostic
process's exit zero means all observations were collected, not that all cases passed.

Both raw reports are complete, untruncated and free of timeout or cleanup errors.
Execution durations: original 11.649s, submitted 5.121s; whole comparison 20.475s.
There were zero provider calls, zero new API cost, zero independent evaluations
and no retry. Saved source, submitted diff and both prior journals remain unchanged.

## Cause and decision

The public source and observed stored value agree on this mechanism:

1. `DataElement.value`, lines 439-448, splits OL bytes on `0x5c` into a list.
2. The current patch runs at lines 509-515, after that split. `memoryview(list)`
   raises `TypeError`, which the patch catches, so execution continues.
3. Lines 517-523 wrap the list as `MultiValue`. The raw bytes writer cannot write it.

**The submitted patch does not repair this original-representation, original-API
counterexample.** The prior buffer-test success remains valid for that test, but
does not cover this earlier transformation. A repair must preserve binary bytes
before the setter applies text-style multi-value splitting. Simply adding more
buffer conversions or repeating successful buffer tests does not address it.

No corrective patch was made in this diagnostic. The next implementation question
is how the agent chooses and checks the first incorrect transformation while
preserving the public input and caller, rather than accepting a later helper's
success as sufficient evidence. Existing bounded execution tools were sufficient
for the operator; this does not establish autonomous use or justify a new finish
gate or higher limits.

## Limits and identities

The reporter did not provide actual `indexData` or the full original dataset.
The sequence setup is a compatible minimal reconstruction, not that unavailable
file. The image runs Python 3.9.21 and benchmark source `2.2.0.dev0`, whereas the
issue mentions version `2.0.0.0`. The removed `array.tostring` alias is represented
by `tobytes`; bytes representation and the two public API calls are preserved.
This reproduces the public error and VR distinction on the benchmark base and
candidate. It does not identify the exact private failing assertion, establish
complete DICOM conformance, or evaluate an unimplemented corrected patch.

- Execution HEAD: `dc89a7370ed2efa18e6a70c81dacd9f825b95f8b`.
- Runtime unchanged: `sha256:c455b38f9be2d1845b7cae4609536190a665b4ab5c8d0e0f6156b9b72b52773c`.
- Task: `tasks/dev-train/current-dev20/8/public.yaml`, pydicom1413.
- Base: `f909c76e31f759246cec3708dadd173c5d6e84b1`.
- Source run: `run_dev_abbcd884047f44be`.
- Submitted patch: `sha256:52f7cc595dc7547f70b4d81a736812243cdb3fb329fc71afc25943c5101294da`.
- Existing image digest: `sha256:ce1687a82b9b9eaa4d93763ac8405105c1eb8c5123f295f0aa15d3252c10e39d`.

## Evidence and validation

External evidence root: `C:/pt/task8-bytes-path-20261101-v1/`. The append-only
`run_dev_task8bytespath` journal binds exact program/check identities before both
dispatches and retains raw reports. `audit.json` checks identical inputs, one-byte
difference, public call path, exact exception/type, positive controls and source
preservation; it also retains hashed public source excerpts.

- `public_bytes_case.py`: `sha256:55ee50194f7f60bd294d33e71f4e699992d24eb7a74a4c58aa324cd319683942`.
- `manifest.json`: `sha256:a63aad93b68ad954e661aa37740f09a3cadf7c199c40ce4c6128d0753ffd4ab6`.
- `result.json`: `sha256:0fc043b690155a6387669c078700f97d55fb609f7c6f24a843b1809a8447ef1a`.
- `audit.json`: `sha256:c0ee249a5e34ecc8a4dc37d3b41ea25fbd8ccfff7fb3e64c0870b4eab755e4b4`.
- Original raw receipt: `sha256:e8c5abf94f2ca24b07c744217757cba178df433dddf5afe99363891f2e1a0167`.
- Submitted raw receipt: `sha256:9c4bfa9b96e46cee757eebe5ce1f2ef85da7a7cfaddeebdf4e569e906717e238`.
- Audited journal head: `sha256:bde7c34c9a531c300b0b7c3afab599da79aba313054bbf7f3c7a9c0b2d21024b`.

Repository changes are documentation only. Documentation checks, Ruff, link/source
integrity checks and the final commit are bound in separate `result-validation.json`
and `result-commit.json` receipts. The fast runtime suite and isolated mock were not
rerun; no runtime change or new independent acceptance is claimed.
