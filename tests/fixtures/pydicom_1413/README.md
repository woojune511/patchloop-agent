# pydicom-1413 public replay fixtures

`original_probe.py` is byte-for-byte the original model's action
call_d0bcaphoLo7QAwEOgNYJUbQu, sequence 111 in run_dev_24ac4f435fd04df4.
Source journal: C:/pt/ld20live01/8/runs/run_dev_24ac4f435fd04df4.jsonl,
SHA-256 528a7ab67a2ec29843a35359ddc8e9ee085db918aa358ce9d6d597b985afa93e.
It uses the existing sandbox check_setup helper. No assertion or input was added.

`submitted.patch` is that run's actual submitted candidate, not a reference patch.
Its base is f909c76e31f759246cec3708dadd173c5d6e84b1. Hashes are pinned in the test.

The separate operator program is the unchanged PYDICOM_WRITE in
diagnostics/probe_recheck_public.py, originally prepared on 2026-10-03. It uses
bytes containing 0x5c and Dataset.save_as/dcmread. It is NOT the original agent
program, a model-authored expected result, or a newly discovered model capability.
The public issue converts integers into bytes before assigning OL and saving;
it contains an undefined indexData variable and does not supply exact failing
bytes. The operator's ranges are an explicit constructed public-domain example,
not a literal replay of that incomplete snippet. List failure alone is not a
product defect. The ordinary-byte and OB cases check nearby preservation.

Run from the repository with existing local source and the pinned probe image:

```powershell
$env:PATCHLOOP_TEST_REAL_PROBES = '1'
$env:PYDICOM_1413_SOURCE = 'C:/path/to/existing/pydicom-checkout'
uv run pytest tests/test_pydicom_1413_replay.py --basetemp C:/pt/tmp/pydicom1413-new
```

The test exports the pinned public source into scratch, applies the saved patch,
and executes both unchanged programs on base and candidate. No dependency install,
image acquisition, provider invocation or hidden evaluation occurs. Missing local
prerequisites fail when opted in; otherwise the Docker replay is skipped. Receipts
are stored under the external basetemp in a hash-chained dev-run-v1 journal.
