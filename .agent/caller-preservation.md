# Waiting caller cancellation diagnostic

`diagnostics/anyio_caller_preservation.py` runs ten isolated provider-free probes:
base and four saved final candidates, each with normal Event release and direct
cancellation of the existing waiting caller. Restore both accepted mutations from
the closed journal into fresh prepared-source workspaces, verifying pre/post file
and complete-diff hashes. Never modify the saved live workspaces or old artifacts.

The coroutine blocks on an unset Event before the callback runs. The normal case
sets it; the cancellation case calls caller.cancel() without releasing it. This
avoids mistaking a test that already finished for cancellation propagation. No task
wrapper or TestRunner monkeypatch is added. Observe test finally, caller and runner
states, and one same-task async fixture cleanup including ContextVar reset.

A two-second loop watchdog records stalled tasks and exits without additional
cancellation. Its zero process exit is diagnostic completion, not successful
teardown. Sandbox timeout/truncation or uncertain cleanup stops collection without
retry. Both programs differ only in the CANCEL flag. Existing pinned dependencies
and images are required; never start Docker or acquire images automatically.

Keep generated state in external CAS and hash-chained dev-run-v1 journals. Verify
unchanged source snapshots and absence of all owned containers. Record base versus
candidate behavior separately: a failure shared with base is a coverage limitation,
not evidence that the new repair introduced a regression. No provider, new isolated
evaluation, default policy change or generalized task-quality claim is involved.
