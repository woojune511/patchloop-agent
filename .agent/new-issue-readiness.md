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
Earlier failed preparations are preserved. No Docker image was acquired or built.

Live readiness remains NOT_READY: no checked-in dev-train package or registered
check/isolated evaluation environment is admitted. A working optional probe does
not establish evaluator readiness. No model or paid call has run.

An offline image recipe is ready under
`C:\pt\preparations\jsonschema-1538-20261001-v2\evaluator-image-context`.
It pins the already-local Python image and copies only verified site-packages;
the context excludes credentials, source and journal files. Proposed command:
`docker build --pull=false --network=none -t patchloop-jsonschema-1538:py312-v1 C:\pt\preparations\jsonschema-1538-20261001-v2\evaluator-image-context`.
Build NOT_RUN pending explicit authorization under AGENTS.md hard gate 7.

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

## Next preparation work

Source and optional-probe preparation are complete. Admit a registered-check
and isolated evaluation environment using the verified dependencies; do not
assume optional probe mounts are present during evaluation. Image acquisition
still requires explicit authorization. Preserve the reproducible original failure.

Then define the exact dev-train package, meaningful completion checks, mutation
scope and evaluation boundaries. Do not label public-only checks as hidden or
independent quality evidence. Only after readiness should a one-run proposal name
the model, credential file, repeat and positive cost cap. No cost estimate from
the earlier PDM run is evidence for this task's actual cost.

During an eventual autonomous run, supply only the frozen public task and normal
tools. No operator hint, manual repair or mid-run rescue. Preserve failures and
analyze them after termination; operational approval is separate from solving.
