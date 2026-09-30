# jsonschema public task admission

## Problem and decision

The selected public issue [jsonschema #1538](https://github.com/python-jsonschema/jsonschema/issues/1538)
reproduces on pinned source, but the earlier reproduction wrapper exits successfully
after printing the exception. That is environment evidence, not a completion gate.
Admit a bounded dev-train package with checks that reject the observed defect and
obvious semantic regressions. No agent policy or prompt intervention is justified
by this preparation work.

Task: `tasks/dev-train/jsonschema-regex-recursion-1538`, version 1.
Source: `51cd75e399c760e5aa3adce600dcce1385756ab0`.
Image and dependency provenance remain in the separate
[image record](2026-10-01-jsonschema-image-validation.md).
Task content hash:
`sha256:44d8ab5d22e9f02b8030717659bef9ca64fe966d0ae0efa1fbfde50f19793414`.

## Checks and boundaries

The original public issue text is retained. Registered public checks require the
reported nested pattern to produce one format validation error, valid patterns
and non-string instances to remain valid, and ordinary invalid patterns to fail.
The second check runs the pinned upstream test_format module: exactly eight tests,
no skips. Semantic failures exit 1; import/setup failures exit 2. Source mutation
is limited to jsonschema package code, excluding its tests, with no dependency or
public API changes.

The existing package contract requires a reference patch. A private, hash-bound
operator calibration patch was constructed from the public issue; it is not an
agent repair or an upstream reference patch. It is never projected to the coding
agent. There are no hidden checks. Isolated evaluation reruns public checks;
its PASS cannot establish independent hidden acceptance or general correctness.

## Executed calibration

Checks ran through DockerSandbox with the approved image, network disabled,
read-only source and confirmed container cleanup. Original prepared source and
dependency identities were reverified unchanged. Mutants and reference application
were confined to separate external copies.

| Source | Public regex contract | Upstream format tests |
| --- | --- | --- |
| Original | FAIL: escaped RecursionError | 8 PASS |
| Private calibration patch | PASS | 8 PASS |
| Reject every string pattern | FAIL: valid control | 8 PASS |
| Accept every string pattern | FAIL: invalid controls | 8 PASS |
| Missing package source | Setup ERROR (exit 2) | Setup ERROR (exit 2) |

The first calibration script incorrectly expected the upstream module to reject
the reject-all mutant and stopped after saving that receipt. The follow-up records
the corrected interpretation without changing either public check. Upstream tests
alone do not cover these regex semantics; the explicit public contract is necessary.
An admission test also caught a missing Git diff header in the calibration patch;
the header and reference hash were corrected, with the same hunk and successful
git apply --check. All earlier receipts remain intact.

External hash-chained journal under
`C:\pt\preparations\jsonschema-1538-20261001-v2\task-admission`:
`run_dev_943dd2d377e64349`. It records ten check receipts and the corrections.

## Validation and limits

Package CLI validation, 17 focused package/classification/documentation tests,
Ruff and diff checks pass. New tests cover source/image admission, reference
tampering and public projection under both conversation policies. Mock smoke
`run_dev_185794715c6643f5` reaches EVALUATOR_PASS (safety NOT_RUN, USD 0) under
`C:\pt\validation\jsonschema-admission-mock-20261001`.

No runtime code changed in this admission. The preceding full-suite attempt and
short-path revalidation remain recorded in the
[environment preparation](2026-10-01-jsonschema-environment-preparation.md);
the full suite was not repeated for this package-only change.

Task/environment preparation is complete. No fresh autonomous solve, paid call,
jsonschema submission evaluation, independent hidden evaluation or quality claim
was executed. A live invocation still needs an exact model, credential file,
repeat count and positive cap. This small, cause-described public issue can test
end-to-end operation; its result alone cannot demonstrate diagnosis ability or a
general repair improvement. No manual hint or rescue is authorized during a run.
