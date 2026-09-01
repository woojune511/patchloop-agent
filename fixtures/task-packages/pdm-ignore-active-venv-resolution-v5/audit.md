# PDM public behavior-check successor v5

This package preserves the version-1 repository commit, environment, reference patch and hidden evaluator bytes. It is
an append-only successor to the consumed version-4 qualification package; only the public task version/check surface
and matching private metadata version are changed.

It lives under `fixtures/task-packages/` as an opt-in offline successor. It is not registered in the frozen dataset
manifest and therefore cannot silently replace or reinterpret the consumed version-1 task.

The first visible check is derived from the public issue text and the exact base-commit implementation of
`pdm.project.config.ensure_boolean()`. That public helper treats empty, `false`, `no` and `0` as false but treats `off`
as true. Consumed qualification-v5 showed that public case `false-off` over-constrained the task, so this successor
removes exactly that case and changes no other behavior. It still covers both active-environment variables, exact
active-environment exclusion, a component-boundary sibling and the creation fallback. Expected mismatches retain the
allowlisted `PUBLIC_CASE:pdm:*` identifiers; the existing upstream project regression remains second.

The public-only decision and exact one-case delta were fixed before a later PowerShell inspection mistake emitted the
private metadata file. No field from that output changed this successor, and no hidden assertion or reference patch
body was used. The package is locally schema/syntax qualified only; it grants no Docker, task, evaluator, provider or
paid authority.
