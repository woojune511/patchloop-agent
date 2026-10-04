# Public-only repair entry point

The requested product boundary was missing: the current `dev` entry point loaded
a `TaskPackage` with private evaluation material before running the solver. An
ordinary public issue/source request could not use that entry point independently.
This was an explicit capability requirement, not a new C2/pydicom investigation
or a continuation of the closed mini/full comparison.

Implemented `repair --request` with a separate public task/request/envelope. It
clones an existing local Git source at an exact commit into managed state, uses an
explicit prepared sandbox and the existing solver, budgets, tools and journal,
then returns the patch and public verification receipt. Only final delivery is
separated from independent evaluation; no model loop was copied. `dev` still
requires its private/reference material and registered live development task.

Public checks gate the existing finish action, not acceptance: repair completion
is `PATCH_READY` with independent acceptance `NOT_RUN`. Receipt recovery verifies
the patch, checked diff, action/finish evidence and envelope without re-execution,
including when the original source is unavailable after committed delivery.
No original-source patch application, PR, source fetch, dependency installation,
image pull/build, new tool, policy default or edit-limit change was added.

## Offline evidence

- Initial focused validation: 17 passed in 60.81 seconds.
- Full suite: 4,126 passed, 3 failed, 18 skipped in 2,549.29 seconds. All three
  failures were the same completion-card compatibility error: older lightweight
  test tasks omit `split`. The repair branch now checks the explicit `RepairTask`
  type. This keeps ordinary development completion behavior unchanged.
- After that correction, all 76 tests in the new repair, existing completion,
  probe-observation, mutation-identity, request/CLI-contract and documentation
  groups passed in 87.91 seconds. The full suite was not rerun after this one-line
  discriminator correction; the initial failures are retained as recorded.
- Ruff passed. Actual CLI mock repair returned `PATCH_READY`; actual CLI mock dev
  reached isolated `EVALUATOR_PASS`. Each used four scripted model turns, five
  gateway actions, and zero provider cost. These are plumbing/recovery tests, not
  autonomous model-quality evidence.
- Tests cover pinned-source isolation (including dirty/untracked source files),
  current-diff public receipts, failed checks, scope/edit constraints, unchanged
  private-task rejection, image preflight, immutable resume identity, corrupted
  artifacts and five interruption boundaries without duplicate actions.

Final runtime content hash:
`sha256:232455c1be0abcb4c85b54c8ca838a5225fd7bca8851be5963384e337293258d`.
Retained local evidence is outside the repository under `C:/pt/validation/`:
`repair-focused-20261005.xml`, `repair-full-final-20261005.{log,xml}`,
`repair-regression-final-20261005.{log,xml}`, and
`repair-{cli,dev-smoke}-complete-20261005.json`. The earlier interrupted full run
and pre-correction smoke artifacts remain separate and are not passing evidence.

Decision: ship the public-only path and keep existing runtime defaults. Live
OpenAI/Docker repair and independent acceptance of real repair candidates remain
unexecuted; no paid calls were made. Usage and limitations are in the
[small executable example](../../examples/repair/README.md). No follow-up experiment
is automatically authorized.
