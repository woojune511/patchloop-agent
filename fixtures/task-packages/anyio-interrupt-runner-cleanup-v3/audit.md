# AnyIO public behavior-check successor

This package preserves the version-1 repository commit, environment, reference patch and hidden evaluator bytes. It is
an append-only successor to the consumed version-2 qualification package; only the public task version/check surface
and matching private metadata version are changed.

It lives under `fixtures/task-packages/` as an opt-in offline successor. It is not registered in the frozen dataset
manifest and therefore cannot silently replace or reinterpret the consumed version-1 task.

The new first visible check is derived from the public issue text. A supervisor creates a temporary public pytest case
under `/tmp` and runs it in a child process, so SIGINT exercises the actual plugin, async-generator fixture teardown and
pytest process boundary without terminating the registered-check supervisor. It checks non-resumption, exactly-once
cleanup and nonzero interrupt propagation. A separate shared-fixture scenario preserves pass, skip and xfail outcomes
across multiple tests. The existing upstream pytest-plugin regression remains second.

No hidden assertion or reference patch was inspected to author the check. The package is locally schema/syntax
qualified only; its check has not run in Docker and it grants no task, evaluator, provider or paid authority.
