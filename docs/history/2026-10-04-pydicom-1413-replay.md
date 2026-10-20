# pydicom-1413: reproducible saved-candidate replay

2026-10-04. No paid calls, hidden evaluation or runtime/default changes. C2 stays closed.

The [earlier diagnosis](2026-10-02-lite-dev20-failure-diagnosis.md) proposed rerunning
the original probe's failing list case. The new [test](../../tests/test_pydicom_1413_replay.py)
separates that observation from public-issue reproduction. Original program and
submitted patch bytes are pinned in [fixtures](../../tests/fixtures/pydicom_1413/README.md).

| Unchanged program | Base | Saved submission | Meaning |
| --- | --- | --- | --- |
| Original agent: direct write_data_element, list and ordinary bytes | List TypeError; bytes succeed | Same | No failing issue byte case or Dataset.save_as coverage |
| Existing operator: OL bytes with 0x5c through save_as/dcmread | TypeError | Same | Submitted patch does not repair this public byte/save case |
| Same operator: ordinary OL and OB preservation | Pass | Pass | Nearby behavior already worked |

The issue converts data to bytes before saving. Its snippet has undefined indexData
and lacks exact failing bytes. The operator's byte ranges are constructed examples,
not literal issue input or model-authored expectations. They are unchanged from
diagnostics/probe_recheck_public.py; the original probe was not edited. Integer-list
failure is not promoted to a product defect. The earlier ineffective-repair finding
stands via the byte/save reproduction, but the original probe alone is insufficient.

The existing saved-program-v1 path already reruns a saved program once after a
changed mutation. This unsuitable original ad-hoc probe supplies no reason to add
another connection or selection policy. No runtime PR is justified; the deliverable
is a reproducible test, with operator evidence explicitly separate. No claim is made
that automatic replay would have led the model to a correct patch.

Real replay: 2 tests passed in 37.81 seconds using the existing pinned probe image,
with four executions across exported base/submitted source. The first test attempt
stopped before Docker because its new opt-in name was not the existing test guard's
flag; the test now reuses PATCHLOOP_TEST_REAL_PROBES. No image was acquired.
Receipts: C:/pt/tmp/p1413r02/test_same_programs_on_base_and0/evidence.
JUnit: C:/pt/validation/p1413-replay-20261004-v2.xml. The separate focused group
passed 31 tests with one Docker skip in 108.81 seconds, including mock paths to
isolated evaluation. Documentation checks (5), Ruff and diff checks passed. Full
suite was not rerun for test-only changes. External closeout:
C:/pt/analyses/pydicom-1413-replay-20261004-v1.
