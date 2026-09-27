# Public caller-state discriminator

`diagnostics/anyio_caller_probe.py` is a provider-free operator diagnostic. It is
not an agent policy, tool-surface change or repair. It uses the frozen public N1
source identity, existing prepared source/dependencies and pinned probe sandbox.
No key loading, token count, model call, private evaluation, network source fetch,
Docker start or image acquisition is provided.

The public program `diagnostics/probes/anyio_caller_state.py` has two modes differing
only in a driver-supplied constant. The original callback raises KeyboardInterrupt;
the positive control requests cancellation on the existing waiting caller. Each
mode runs once in its own isolated probe process on the unchanged base workspace.

Capture exactly one existing `TestRunner._call_in_runner_task` Task while the test
is running in the shared task. Ambiguity is a setup failure. Do not create a wrapper
Task, monkeypatch methods, insert awaits, inspect private evaluator information or
change the interrupt path. At the trigger and subsequent boundaries, synchronously
read done/cancelled/cancelling for both captured caller and shared runner. Ordinary
fixture setup, test yield, teardown and runner close remain in the reproduction.

Only the explicit-cancel control calls cancel. Its accepted request and transition
from pending/requested to cancelled/completed must validate before interpreting
zero counts in the callback case. A completed uncancelled caller is inconclusive,
not proof of cancellation. Later normal runner shutdown cancellation is a separate
stage from the interrupted test boundary.

The callback case's four original observation stages must match saved event order,
task ownership and runner completion state after ignoring process-local IDs. This
supports preservation of those discrete observations, not universal timing parity.
The fresh source workspace must remain unchanged. Store exact programs, receipts,
source/runtime identities and interpretation in external CAS plus an append-only
dev-run-v1 journal. A fresh output directory is mandatory; no automatic resume.
Stop on execution/setup/cleanup uncertainty and preserve receipts without turning
them into a behavior verdict. Confirm exact owned containers are absent afterward.

Successful observation does not establish acceptance, safety or improved agent
reasoning. Do not rewrite old tool outputs or continuation history with these later
operator observations. A future information-effect comparison needs its own honest
projection, input-integrity checks and exact paid authorization; keep recommendation
policy and other controls fixed if observation content is the tested variable.
