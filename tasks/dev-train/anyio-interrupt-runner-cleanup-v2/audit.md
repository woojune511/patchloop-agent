# AnyIO interrupt runner cleanup - task version 2

## Scope and provenance

This version adds the public `interrupt-lifecycle-contract` check and preserves
the existing upstream pytest-plugin regression. The task identity, issue, source
commit, constraints and evaluator image are unchanged. Version 1 remains intact
at `../anyio-interrupt-runner-cleanup`; its task content hash is
`sha256:fd4296c47cbc9ef4ad0035cde643c534772238086784744f044500fcb9a1203e`.

The new public code comes from the operator-authored reproducer at
`C:\pt\analyses\anyio-public-interrupt-20260916-v1\public_cases.py`, SHA-256
`a7c1b7d4222751000ed700a7243efdc3e30f99d8056a8c83ea979ff298d19fba`.
It was developed from the public issue and executed on base and a submitted patch.
It is not derived from hidden tests or the reference patch. The reproduction and
assessment functions are preserved; the command now converts their semantic
assertions into process success/failure and prints bounded, concrete diagnostics.

## Public contract

- Function and module async-generator fixtures: propagate callback KeyboardInterrupt,
  never execute the interrupted test's post-interrupt marker, clean up exactly once.
- Explicit cancellation: preserve cancellation behavior and clean up once.
- Shared module fixture with a task group: preserve pass, intentional failure, skip
  and expected failure, with one fixture setup/cleanup.

Expected child pytest exits are 2 for interruption and 1 for the other controls.
The parent check exits 0 only when every required observation passes; collection
errors, incomplete execution, timeout, wrong outcomes or resumed tests return 1.
The check imports the workspace's AnyIO source and uses the existing offline
sandbox; it does not install packages or alter tracked source.

A current-diff FAIL uses the existing run_check state and submission gate. After
mutation, the agent can rerun the same registered check. Historical diff receipts
do not become current PASS evidence. No context, planning, probe or segment policy
was changed.

## Private package boundary

Private metadata differs only by task_version=2. Hidden files, reference patch,
bad-patch fixtures and image configuration are copied byte-for-byte. Their contents
were not used to author the new public reproducer. No new private evaluation or
model-based repair result is claimed. The added public information means future
version-2 runs must not be pooled with version-1 results as an unchanged task.

## Validation

Provider-free evidence is recorded at
`C:\pt\analyses\anyio-public-check-v2-20260916-v1`. It separates local semantic and
workflow fixtures from actual checks on known source revisions. All results are
`official=false`. This package change establishes a usable public validation route,
not a successful AnyIO repair.
