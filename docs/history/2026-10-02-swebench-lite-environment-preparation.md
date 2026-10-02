# SWE-bench Lite environment correction preparation

Date: 2026-10-02. Provider-free operator work at `dff8ef95`; official=false.
Follow-up to [dev20 calibration](2026-10-02-swebench-lite-dev20-calibration.md).
Original calibration failures and packages remain unchanged.

## Problem and decision

Eight of the fixed twenty development tasks could not complete calibration in
their original images. These failures prevent interpreting future solver results:
five pvlib images import code using `np.Inf` with NumPy 2.0.2, two pydicom images
run nose-style setup methods under pytest 8.3.5, and PyVista cannot load VTK's
system libraries. The user requested environment correction, without paid runs.

The smallest intervention is to correct installed dependencies while preserving
task source, public test membership, original hidden tests, reference patches and
grading rules. An alternative was that dependency correction would reveal task
failures or missing data; unchanged public tests distinguished these possibilities.
No solver prompt, tool, resource budget or acceptance rule was changed.

## Observed results

Existing images were inspected without pulling or building. Candidate packages
were installed only into disposable containers. Public sources were mounted
read-only; the unchanged registered public command copied them into temporary
checkouts. Execution had no network, two CPUs, 2 GiB memory and a 300-second check
timeout. PyVista's temporary package installation needed package-manager
capabilities; this diagnostic is not a production sandbox safety calibration.

| Task | Candidate environment change | Public result |
| --- | --- | --- |
| pvlib-1072 | NumPy 2.0.2 -> 1.26.4 | 17 passed |
| pvlib-1154 | Same | 98 passed |
| pvlib-1606 | Same | 257 passed |
| pvlib-1707 | Same | 30 passed |
| pvlib-1854 | Same | 281 passed |
| pydicom-1139 | pytest 8.3.5 -> 7.4.4 | 38 passed |
| pydicom-1413 | pytest 7.4.4 plus upstream pydicom-data 1.0.0 | 212 passed |
| pyvista-4315 | libgl1, libxrender1 and their Ubuntu dependency closure | 115 passed, 1 skipped |

Total: eight public checks passed, 1,048 tests passed and one upstream skip.
Tests and selection arguments were not modified or removed. These are base-source
compatibility diagnostics, not eight repaired tasks or hidden-test successes.

For pydicom-1413, the pytest-only attempt had 207 passes and five failures,
preserved separately. All five came from missing public fixtures: `color-pl.dcm`,
`SC_rgb.dcm` and `explicit_VR-UN.dcm`. The official pydicom-data wheel supplies
them through the source's existing external-data entry point. Each file's SHA-256
matches `pydicom/data/hashes.json` at the task's original base commit. Installing
that package produced 212 passes without test edits, a shim or network access.

The dependency choices agree with the upstream
[NumPy 1.26.4 Python support](https://numpy.org/doc/2.1/release/1.26.4-notes.html)
and [pytest nose lifecycle documentation](https://pytest.org/en/8.0.x/how-to/nose.html).
Actual compatibility above was established by local execution, not documentation
alone. No additional pandas, SciPy, NumPy-for-pydicom or VTK version change was
needed for these selected public checks.

## Frozen build proposal and remaining gate

Eight offline derivative-image contexts are ready. Each starts from its existing
exact original image digest, verifies dependency SHA-256 values, and installs
only the listed packages. Three wheels and 32 Ubuntu debs total 99,119,276 bytes
of unique downloaded dependencies. Apt simulation selected 32 new packages,
zero upgrades and zero removals; the debs were verified against the signed
repository metadata obtained by apt. Wheel hashes match PyPI metadata.

Proposed builds use `--pull=false --network=none --provenance=false`, new local
tags and one build at a time, stopping below 12 GiB free disk or on any build,
identity or cleanup uncertainty. No registry push, parent-image modification or
task admission is included. No image was built: AGENTS.md's explicit no-automatic
image-build gate remains applicable, and the earlier acquisition scope excluded
builds. The concrete frozen proposal awaits explicit build authorization.

After a permitted build, bind its locally verified immutable RepoDigest in new
draft packages and native rows. Require original/native and registered base
unresolved/reference resolved controls with complete required-test accounting,
then actual EvaluationEngine reference acceptance. Preserve test/reference/grader
and original eval-script bytes. New failures remain failures; this preparation
does not establish that every native script or private check will pass.

The fully calibrated count remains **12/20**. Corrected-image native, private and
EvaluationEngine controls are **NOT_RUN**. Agent executions and provider calls
were zero; cost was USD 0.00. Existing paid allocations remain closed.

## Evidence and validation

External root: `C:/pt/analyses/lite-dev20-environment-20261002-v1`.

- `diagnosis.json`, `apt-metadata.json`: installed packages, VTK dependencies and
  exact Ubuntu installation simulation.
- `wheels.json`, `debs.json`, `data-wheel.json`: URLs, versions and verified hashes.
- `public-compatibility.json`, `pyvista-public.json`, `public-data-followup.json`:
  unchanged public executions and the retained pytest-only failure.
- `build-plan.json`, `build-contexts/`: exact eight parent identities, commands,
  package lists, Dockerfiles and content-addressed recipe records.
- `drivers/`, `runs/`, `artifacts/`, `summary.json`: reproducible operator scripts,
  append-only hash-chained journals and immutable output artifacts.

The final audit verified 100 artifact references across ten journals, all twenty
original package hashes, the eight source checkouts and parent image identities,
and absence of owned containers. The prior full suite and Windows/Linux CI passed
at `dff8ef95`; this follow-up changes documentation only. Its documentation tests
and whitespace validation passed. No new mock or full-suite execution was needed.

Decision: prepare these environment corrections for original/private calibration;
retain the agent baseline and cohort. Whether the corrected immutable images pass
all evaluation layers remains the next unresolved question.
