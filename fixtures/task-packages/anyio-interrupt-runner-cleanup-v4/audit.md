# AnyIO public behavior-check successor

This package preserves the version-1 repository commit, environment, reference patch and hidden evaluator bytes. It is
an append-only successor to the consumed version-3 qualification package; only the public task version/check surface
and matching private metadata version are changed.

It lives under `fixtures/task-packages/` as an opt-in offline successor. It is not registered in the frozen dataset
manifest and therefore cannot silently replace or reinterpret the consumed version-1 task.

The first visible check is derived from the public issue text. A supervisor waits until a temporary child pytest test
records that it is suspended, then sends SIGINT externally. This replaces v3's in-test `raise_signal()`, which both base
and reference passed. It checks non-resumption, exactly-once cleanup and nonzero interrupt propagation; a separate
shared-fixture scenario preserves pass, skip and xfail. Expected mismatches emit allowlisted `PUBLIC_CASE:anyio:*`
identifiers. The existing upstream pytest-plugin regression remains second.

No hidden assertion or reference patch was inspected to author the check. The package is locally schema/syntax
qualified only; its check has not run in Docker and it grants no task, evaluator, provider or paid authority.
