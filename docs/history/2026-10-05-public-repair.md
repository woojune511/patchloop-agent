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

## Final full regression closeout (2026-10-05)

The preceding section preserves the initial delivery record. Its outstanding
full-suite recheck is now closed. No same-commit CI run was available, so commit
`a47feb37a4a75a5ba86ae80e4d2a4cebe915a66c` was tested locally on Windows 11,
Python 3.14.5, with the unchanged complete `tests` scope, four workers,
`--dist loadfile --max-worker-restart 0`. Runtime hash remained the value above.

**4,129 passed, zero failures/errors, 18 skipped; 2,572.86 seconds (42:52).**
All three previously failing cases passed in this full run:

- `tests/test_dev_completion_v27.py::test_guidance_tracks_recheck_then_submission_without_rewriting_history`
- `tests/test_dev_probe_observation_v28.py::test_actual_native_projection_restart_and_historical_probe_keep_evidence`
- `tests/test_dev_mutation_identity_v31.py::test_final_unchecked_edit_keeps_consistent_identity_and_available_check_or_stop`

These retain coverage of recheck/submission guidance, native history/restart and
historical probe evidence, and final-diff mutation/check identity. The original
missing-`split` error and explicit `RepairTask` discriminator fix are described above;
no additional runtime or test change was needed in this closeout.

| Skip reason | Count |
| --- | ---: |
| Symlink creation unavailable | 1 |
| Brief planning is append-only (excluded parameter combinations) | 4 |
| Real Docker probes require explicit opt-in | 10 |
| SDK compatibility needs an existing public dependency descriptor | 1 |
| Local-source/real-probe explicit opt-in absent | 1 |
| Real check/probe explicit opt-in absent | 1 |

Fresh evidence is under `C:/pt/validation/` with prefix
`repair-closeout-a47feb37-20261005`: `.log`, `.xml`, `-start.json` and `-result.json`.
The result binds artifact hashes, all skip reasons, the three regression outcomes,
and the unchanged runtime and user `AGENTS.md` hashes. Earlier evidence was retained.
Linux/Python 3.12 CI, opt-in real environments, paid model calls and actual public
repair usage were not run. Independent acceptance remains `NOT_RUN` for `repair`.

Decision: implementation and final local full regression verification are complete.
Existing dev contracts, public/private boundaries, limits and defaults are unchanged.
No new feature, policy, paid execution or follow-up diagnostic was added or queued.
