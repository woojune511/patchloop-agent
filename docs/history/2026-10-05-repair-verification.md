# Public returned-patch verification

## Requirement and implementation

The dotenv public repair supplied an unchanged model-authored regression test
that could be checked against both implementations. Its external comparison was
manual; the existing runtime already provided checkout isolation, prepared
sandboxes, deadlines, content-addressed artifacts and a hash-chained journal.
The requested user feature reuses those components rather than adding another
solver, tool or submission policy.

`patchloop repair-verify --request request.json --patch returned.patch` runs the
original registered public checks on three separate checkouts: base, base with
submitted tests, and the full patch. The submitted test bytes are identical in
the latter two. Python/pytest additions in existing test files are structurally
identified; ambiguous edits, existing test/fixture/configuration changes and
unsupported file operations are reported without rewriting the patch.

The JSON preserves all public check outcomes and separately compares added
tests. Collection errors/skips, fixture errors, call failures, skips, xfail/xpass,
missing tests and incomplete execution remain distinct. A fail-before/pass-after
observation does not establish issue coverage or acceptance. No model calls,
automatic corrections, new gates, defaults or publishing were added.

## Validation

- Focused command tests: 32 passed in 104.41 seconds. Coverage includes unchanged
  source/test bytes, additive parameters, failed assertions, fixture/collection
  errors, skip/xfail, missing cases, non-pytest public failures, unsafe edits,
  original scope, unavailable environment and incomplete execution.
- Existing repair plus new-command and documentation tests: 46 passed in 118.92
  seconds before the final unsupported-file classification adjustment. The final
  command tests cover that adjustment; the full suite covers both paths.
- Ruff and five documentation layout/link tests passed.
- Existing dev mock smoke: `EVALUATOR_PASS`, isolated acceptance `PASS`, safety
  `NOT_RUN`; no external provider dispatch or paid calls.
- Final Windows full suite: 4,161 passed, zero failed, 18 skipped in 2,305.77
  seconds (38 minutes 25 seconds), four workers with `--dist loadfile` and no
  worker restarts. The skipped tests are not counted as executed successes.

The saved dotenv request and returned patch were replayed using the existing
prepared image, without a model. Original base: 218 passed. Base plus identical
model tests: 1 failed, 218 passed. Full returned patch: 219 passed. Both model test
files had hash `sha256:d4734f8554d3a276a68305fd747c5e44b16be0a7776ba1e3e23829f76b232fb5`.
This checks the new command, not a new autonomous repair or policy effect.

Evidence remains outside the repository:

- `C:/pt/repair-verify-dotenv-final-result.json`: final command result and CAS link.
- `C:/pt/repair-verify-dotenv-final/`: request, patch, public task, check receipts,
  phase workspaces, runtime hash and append-only journal.
- `C:/pt/repair-verify-mock-smoke-result.json`: existing dev mock evaluation.
- `C:/pt/repair-verify-full-suite-final.txt`: final full-suite log.

An earlier full-suite run was stopped to correct unsupported file-operation
classification; it is not counted as a completed verification. Its log remains
at `C:/pt/repair-verify-full-suite.txt`. Runtime source is frozen for the final run.

## Decision and limits

Keep the verification command separate from solver submission. Human review of
failure cause, test relevance and implementation quality remains necessary;
`requirement_fit=NOT_ASSESSED`, `acceptance=NOT_RUN`. Unsupported separations do
not trigger repair or follow-up diagnostics. Existing C2, pydicom, Click, dotenv
and model-comparison allocations remain closed. No new paid execution occurred.
Linux CI, other project environments and unsupported test-edit forms were not
validated by this run. The prepared dotenv container is the real-project check.
Usage and exact supported scope: [example](../../examples/repair/README.md).
