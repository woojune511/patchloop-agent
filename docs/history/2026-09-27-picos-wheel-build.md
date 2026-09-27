# PICOS public-source wheel feasibility

## Question and source

Toqito's public metadata requires picos>=2.6.2. The binary-only dependency
preparer rejected PICOS because the pinned 2.6.2 release has only an sdist.
Inspecting and building that exact public release tests whether a compiler or
system-package dependency is an additional blocker.

Public metadata: https://pypi.org/pypi/picos/2.6.2/json . Upstream installation
context: https://picos-api.gitlab.io/picos/introduction.html . The downloaded
sdist size is 541,158 bytes and SHA-256 is
`f3af4f9e98f0c449eb4b602d7e4e02cc0927e7a9094aa53f5d79a7487659e433`.
The JSON size/hash matched the downloaded bytes. Its setup.py uses setuptools,
find_packages and a packaged version file; it declares cvxopt and numpy as runtime
dependencies, with no native extension build. No pyproject.toml was present.
No setup code was executed on the host during inspection.

## Executed build and canary

Evidence root: `C:/pt/analyses/picos-build-inspection-20260927-v1`.
Journal: `run_dev_picosbuildinspection`; public downloads, scripts, commands,
results, cleanup and installed-file inventory are retained there.

A fresh container used the already-local clean Python image
`python@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de`,
network none, read-only root, nonroot UID, no capabilities, one CPU, 512 MiB memory,
32 PIDs and 128 MiB temporary storage. Only public build inputs were mounted read-only,
plus a fresh wheel output directory writable by the builder. No task repository,
private evaluator material or credentials were mounted. No image was built or pulled.

Public build wheels were pinned and verified:

- setuptools 80.9.0: `062d34222ad13e0cc312a4c02d73f059e86a4acbfbdea8f8f76b28c99f306922`.
- wheel 0.45.1: `708e7481cc80179af0e556bbf0cc00b8444c7321e2700b8d8580231d13017248`.

The offline build used setuptools.build_meta and SOURCE_DATE_EPOCH=1760313600.
It produced `wheel-output/picos-2.6.2-py3-none-any.whl`, 511,618 bytes,
SHA-256 `5bb8e1e8ca5f0194cd9f3b6b5c6510cbe39dac0279b40de9f9c2aefc3ead19a8`.
The wheel reports Root-Is-Purelib=true, PICOS 2.6.2 and requirements cvxopt/numpy.
No compiler/system-package installation was needed. One successful build does not
establish byte-for-byte reproducibility across tool versions or environments.

NumPy 2.4.1 and CVXOPT 1.3.3 public CPython 3.12 Linux wheels were also downloaded
with verified PyPI hashes. Offline installation of these and the generated wheel
succeeded. The first canary installed into tmpfs and failed loading NumPy's shared
object with 'failed to map segment'; its receipt is retained. This is consistent
with an executable-mapping restriction, not evidence of a bad PICOS wheel.

The corrected canary follows the normal dependency placement: host-prepared files
mounted read-only, with noexec scratch. It used the same clean Python image,
network none, eight PIDs, one CPU, 512 MiB memory and OPENBLAS_NUM_THREADS=1.
All three imports passed. Minimizing scalar x subject to x>=1 via CVXOPT produced
1.0000000000000002, within 1e-6 of the expected value. Exit 0; owned containers
were confirmed absent. The container canary was operator-side, not the actual
DockerProbeSandbox wrapper with its additional process restrictions.

## Result and next boundary

Public-source wheel preparation is feasible for this pinned dependency. The normal
preparer still accepts only public-index wheels; this diagnostic did not bypass or
change that contract. No usable toqito dependency descriptor was published.

Next add an explicit generated-wheel admission path binding sdist, build tools,
script/image and output hashes. Keep it separate from model-authored actions and
normal wheel downloads. Then resolve/install the complete public toqito dependency
set and run its public import/entry point through the actual probe sandbox.
Do not label the original-input pilot ready from this package-level canary.
Darts' installed-size blocker is unchanged. No provider/count calls or paid run.

Documentation layout checks validate this documentation-only change. Runtime and
checked-in task packages are unchanged; no full suite or mock smoke was repeated.
