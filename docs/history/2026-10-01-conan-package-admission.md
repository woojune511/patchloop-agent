# Conan original task package admission

## Requirement and implementation

Connect the calibrated original benchmark to PatchLoop's normal task and isolated
evaluation contracts without replacing its hidden tests or original issue.
Added `tasks/dev-train/original-conan-19735` version 1 and the exact Conan GitHub
repository URL to source admission. No model, prompt, tool or acceptance rule changed.

Task content hash:
`sha256:7853e01fc73daf9d0c50fd14c252d65468de2283afa43b2a557877f1f1e5b67a`.
Base `4a65d65f53d2ab37f4ce0e52dc3f25cd832b2934` and image digest remain those of
the [original calibration](2026-10-01-conan-original-calibration.md).

The public issue is byte-for-byte the selected problem statement. Visible checks
run the existing upstream detect_test.py in a disposable copy without private
assets. Both baseline and reference pass its 28 tests. Mutation scope permits
production conan/conans code, four files and 1,000 diff lines; test, dependency and
public API edits remain forbidden. These are harness restrictions, not unrestricted
benchmark execution. The reference patch satisfies those constraints.

Hidden evaluation uses the original test patch, original F2P/P2P lists and command,
plus the previously pinned upstream scoring functions. These inputs were verified
equal to the selected dataset row. The existing private oracle runner applies the
test patch in temporary storage and separates setup/incomplete execution (exit 2)
from a completed wrong answer (exit 1). The original reference's production patch
is private; test changes belong only to the oracle. Raw artifact bytes are preserved
by Git attributes and private artifact/reference hashes.

## Complete isolated validation

Two fresh manifests ran through the existing EvaluationEngine using prepared
source and the approved image. An unchanged program with an inert comment served
as the baseline submission: the submission contract requires a nonempty diff, so
an empty patch is not a valid integration control. Original unmodified baseline
behavior was already checked in the preceding image calibration.

| Package evaluation | Baseline control | Reference |
| --- | --- | --- |
| Public tests | 28 PASS | 28 PASS |
| Original hidden oracle | FAIL | PASS |
| Scope/policy | PASS | PASS |
| Safety | PASS | PASS |
| Acceptance | false | true |

No setup error, missing required case or container cleanup uncertainty occurred.
This is operator calibration, not an agent solve. Manifests label the model as
operator-calibration-no-model; no model/count call or paid allocation occurred.

## Optional probe limitation

Conan's pyproject.toml contains build-system metadata only; setup.py reads public
conans/requirements.txt. The existing dependency preparation resolver supports
PEP 621/735 project metadata and cannot directly prepare this task's optional
clean Python 3.12 probes. No setup.py execution, invented lock, resolver expansion,
dependency installation or probe execution was performed. Registered public and
hidden checks use the original Python 3.13 image and are validated.

A future invocation must explicitly resolve this probe limitation or propose
probes disabled as a documented departure from the selected baseline. Do not claim
the existing probes-enabled baseline is fully prepared. No live run is authorized.

## Evidence and validation

Root: `C:\pt\preparations\original-next-20261001-v1`.
Source: `source/prepared-source.json`, reverified unchanged after calibration.
Journal: `runs/run_dev_conanpackage.jsonl`.
Isolated results/manifests:
`package-evaluation/runs/run_dev_conanpackagebaselinecontrol/` and
`package-evaluation/runs/run_dev_conanpackagereference/`.

43 focused package/source/classification tests PASS; Ruff and documentation checks
PASS. Tests reject private input tampering and verify that private material stays
out of both supported context projections. Mock `run_dev_17ecdace4a5840bb` reaches
EVALUATOR_PASS with safety NOT_RUN. The recent full suite (3,788 PASS, 16 SKIP)
was not repeated for this package and one-URL admission change; it is prior evidence,
not a full-suite result for this commit. Detailed calibration and focused checks
cover the changed paths. Historical records and prior submitted artifacts remain
unchanged.
