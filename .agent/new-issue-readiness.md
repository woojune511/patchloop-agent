# New public issue intake

Status: NOT_READY. Provider calls: zero. No paid run or cost allocation authorized.

## Selected candidate

[jsonschema #1538](https://github.com/python-jsonschema/jsonschema/issues/1538)
reports that a deeply nested regex escapes validation as RecursionError instead
of a validation error. The public issue supplies a small reproducer using
Draft202012Validator and FormatChecker, and identifies Python 3.13/jsonschema
4.26.0. Observed open on 2026-10-01 KST. Upstream main was resolved to
`51cd75e399c760e5aa3adce600dcce1385756ab0`; no repair/reference patch was retrieved.

No jsonschema repository match was found in existing task public manifests. This
does not establish model-training novelty. The issue's own explanation remains
public issue content, not an operator-created repair hint.

## Prepared source and probe environment

The [preparation record](../docs/history/2026-10-01-jsonschema-environment-preparation.md)
records the exact source and wheel identities. The selected repository is now
allowlisted. Source preparation and the corrected package-root probe environment
succeeded. The public issue reproduces as RecursionError on Python 3.12.13; valid
and ordinary-invalid controls behave as expected. Upstream test_format: 8 PASS.

External root: `C:\pt\preparations\jsonschema-1538-20261001-v2`.
Source: `source\prepared-source.json`.
Dependencies: `dependencies-package-root\prepared-probe-dependencies.json`.
Journal: `audit\runs\run_dev_ac3fbd909d62437a.jsonl`.
Earlier failed preparations are preserved. The subsequently approved local image
build and its checks are recorded below.

Task/environment preparation is complete after checked-in task/check admission.
No live model or paid call has run; execution authorization remains absent.
Calibration establishes the public checks only, not agent repair quality.

## Built evaluator image

[Build and validation](../docs/history/2026-10-01-jsonschema-image-validation.md)
completed with the existing base layer and verified dependencies. Image:
`patchloop-jsonschema-1538@sha256:901f8eebd991b12da7dfb43a74c4c6ee51d7fcd9d37cead1f8af7dc292017ccd`.
The public bug reproduced and eight upstream format tests passed through the
registered-check execution path, with network disabled and cleanup confirmed.

BuildKit contacted the registry for authentication/metadata despite --pull=false
and --network=none. No package installation or image-layer download occurred;
do not describe the build as fully offline. No image was pushed.
Context: `C:\pt\preparations\jsonschema-1538-20261001-v2\evaluator-image-context`.
Journal: `image-build\runs\run_dev_aca56d9ead3d40a0.jsonl` under that preparation root.

## PatchLoop validation

Prepared-source tests: 29 PASS. Ruff and documentation checks (5) pass.
Full suite: 3,775 PASS, 16 SKIP, one FileNotFoundError while opening a 266-character
temporary artifact path. With the shorter basetemp `C:\pt\j1538`, all 46 tests in
the affected test_dev_check_feedback_v32.py file pass. This is a full-suite attempt
plus focused successful revalidation, not a clean full-suite rerun. No runtime
workaround was added. Preserve both reports under `C:\pt\validation`:
`jsonschema-intake-fast-20261001.xml` and `jsonschema-feedback-rerun-20261001.xml`.
Mock run `run_dev_d454da980f474c40` reached EVALUATOR_PASS with safety NOT_RUN.

## Candidate disposition

- SQLGlot #8443 has a short MySQL comment reproducer and an existing local image.
  Rejected after public-manifest inventory found an existing cross-repo-heldout
  task in the same repository. Its new public source was prepared but never
  executed; no held-out private material was read. Preserve repository separation.
- SQLGlot #8390 has the same repository overlap.
- Click #3840 is intermittent and Windows GUI dependent, making it unsuitable
  for the current Linux sandbox. Click #3802 is already closed.
- jsonschema #1511 additionally depends on duration-format support. Prefer the
  smaller regex reproducer for initial intake; no comparative execution occurred.

SQLGlot rejected-source journal:
`C:\pt\preparations\sqlglot-8443-20261001-v1\audit\runs\run_dev_87a95e82a2de4955.jsonl`.

## Admitted task and next boundary

[Task admission](../docs/history/2026-10-01-jsonschema-task-admission.md) records
`tasks/dev-train/jsonschema-regex-recursion-1538`, version 1, and its public-only
completion checks. The baseline fails the reported case; a private calibration
patch passes. Accept-all and reject-all mutants fail the public contract even
though all eight upstream tests pass. Missing imports are setup errors.

Package content hash:
`sha256:44d8ab5d22e9f02b8030717659bef9ca64fe966d0ae0efa1fbfde50f19793414`.
Admission journal: `task-admission/runs/run_dev_943dd2d377e64349.jsonl` under the
preparation root. Package CLI validation, 17 focused tests and Ruff pass. Fresh
mock smoke `run_dev_185794715c6643f5` reaches EVALUATOR_PASS, safety NOT_RUN.

Preparation is complete. No autonomous jsonschema solve or submitted-candidate
evaluation has run. Isolated evaluation uses the same public checks, with no
independent hidden oracle. The private reference is operator calibration material,
never agent context or evidence of agent success.

Before a live invocation, freeze the exact task, model, credential file, repeat
and positive cost cap. Prior paid allocations remain closed. Do not infer this
task's cost from PDM. Supply only the public task and normal tools; no operator
hint, manual repair or mid-run rescue. Preserve failures for post-run analysis.
