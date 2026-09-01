# PDM public behavior-check successor

This package preserves the version-1 repository commit, environment, reference patch and hidden evaluator bytes. It is
an append-only successor to the consumed version-3 qualification package; only the public task version/check surface
and matching private metadata version are changed.

It lives under `fixtures/task-packages/` as an opt-in offline successor. It is not registered in the frozen dataset
manifest and therefore cannot silently replace or reinterpret the consumed version-1 task.

The first visible check is derived from the public issue text. It exercises unset/false-like flag values, both active-
environment variables, exact active-environment exclusion, a component-boundary sibling and the creation fallback.
The ambiguous descendant-selection assertion from consumed v3 is removed. Each expected behavior mismatch emits an
allowlisted `PUBLIC_CASE:pdm:*` identifier; unrelated setup/import failures remain unclassified. The existing upstream
project regression remains second.

No hidden assertion or reference patch was inspected to author the check. The package is locally schema/syntax
qualified only; its check has not run in Docker and it grants no task, evaluator, provider or paid authority.
