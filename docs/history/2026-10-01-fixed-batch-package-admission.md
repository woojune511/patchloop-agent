# Fixed batch package admission

## Requirement and changes

Connect the three [calibrated tasks](2026-10-01-fixed-batch-calibration.md) to normal
PatchLoop execution without changing their original issues or private benchmark
oracles. Added three dev-train v1 packages and their exact GitHub repository URLs
to source admission. Scope permits production code under server, src or isort,
respectively; tests and dependencies are forbidden, with four files/1,000 diff lines.
Public API edits are allowed, including the requested pyinfra interface extension.
These are bounded harness constraints, not unrestricted benchmark execution.

Public issues are identical to the frozen rows. Hidden test patches, F2P/P2P lists,
commands and scoring code are retained. Package-local test runners put server/src
ahead of installed dependencies so candidate code, not the image's editable base,
is tested. Private artifacts and reference patches are hash-bound and Git preserves
their exact bytes. Original selection and calibration evidence remain unchanged.

## Public-check conflict and correction

Initial pyinfra reference evaluation passed the original hidden oracle but failed
the public upstream `test_load_ssh_config_proxyjump`. Its mock requires the gateway
call to omit the timeout argument that the public issue requests. This is an old
call-shape assertion, not a supported invariant for the new interface. Retained
that initial result and original public specification externally; deselected this
one public test and kept the other ten unchanged. No private case was removed or
changed. The corrected package was evaluated again on both controls.

## Package integration results

Each control used a fresh prepared-source clone, submitted manifest, DockerSandbox
and EvaluationEngine. Baseline submission adds an inert comment because submission
requires a nonempty patch; the earlier calibration exercised unmodified baselines.

| Final package | Baseline hidden / acceptance | Reference hidden / acceptance | Public, scope, safety |
| --- | --- | --- | --- |
| original-opensandbox-816 | FAIL / false | PASS / true | PASS in both |
| original-pyinfra-1679 | FAIL / false | PASS / true | PASS in both |
| original-isort-2491 | FAIL / false | PASS / true | PASS in both |

No missing case, setup error or cleanup uncertainty occurred in final evaluations.
These are operator controls, not agent solves. Manifest runtime hashes identify
the working source at each evaluation; no quality or causal improvement is claimed.

## Probe preparation and narrow defect fix

Prepared clean Python 3.12 Linux dependencies from public metadata: pyinfra and
isort use root PEP 621 requirements; OpenSandbox uses its existing server/uv.lock
exported frozen/offline without development dependencies. Exact compatible wheels
are checked against that public lock, downloaded with hash/size verification, and
installed offline without source builds. No extra image acquisition was needed.

The nested lock revealed a preparation defect: editable `.` was interpreted from
the repository root rather than the lock directory. Metadata now resolves relative
to the lock's directory, binds server/pyproject.toml, and rejects parent traversal.
Root locks and ordinary resolver behavior remain unchanged. Regression tests cover
the nested descriptor through publication/reload and reject escaping paths.

Real DockerProbeSandbox canaries passed with read-only source/dependencies, no
network, non-root user and existing resource bounds. They confirmed /workspace
module origins and exercised isort sorting, pyinfra gateway with a mock transport,
and OpenSandbox valid/invalid path validation. All cleanup was confirmed. This
checks those entry points; it does not establish equivalence of every dependency
between Python 3.12 probes and Python 3.13 benchmark checks.

## Evidence, validation and remaining decision

Root: `C:\pt\preparations\fixed-batch-20261001-v1\packages-v1`.
Each task has `source/prepared-source.json` and
`probe-v1/prepared-probe-dependencies.json`. `evaluation-v1` retains all initial
results; `evaluation-pyinfra-v2` retains the corrected controls. `canaries-v1` and
`canary-opensandbox-v2` retain public probe receipts. Top-level preparation,
public-check selection and wheel-selection journals bind the changes. External
drivers are `C:\pt\fixed_batch_{packages,evaluate,probe_prepare,canary}_20261001.py`,
plus `fixed_batch_evaluate_pyinfra_20261001.py` and `fixed_batch_canary2_20261001.py`.

98 focused package/private-boundary, prepared-source, dependency and documentation
tests passed; Ruff passed. Mock `run_dev_83e5074272a440df` reached EVALUATOR_PASS,
safety NOT_RUN. Full cross-platform suite is a separate CI gate, not a claimed
local result. No paid call occurred. The agent baseline remains unchanged; the
[proposal](../../.agent/fixed-batch-proposal.md) records exact task identities and
execution scope. Paid approval remains required after review/CI; no next run starts
automatically.
