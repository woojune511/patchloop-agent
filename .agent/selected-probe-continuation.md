# Selected-response probe boundary

`diagnostics/selected_probe_continuation.py` prepares the specific closure B2
continuation with no new provider call. It is a diagnostic Python entry point,
not a production resume command or a live collector.

`prepare(plan_path, plan_hash, live_root, output)` requires the validated closure
plan and settled B2 sample. It restores the original pre-decision checkpoint using
the existing time-extension restorer, preserves the exact public call, usage and
encrypted continuation, and replays that already-paid response once through the
ordinary runner. Historical count/dispatch/usage replay is explicitly labeled in
the new journal; it is not another network request or billed charge.

The selected probe executes through the ordinary gateway in the already-local
prepared Docker environment. Network calls and credential loading in the Python
process are replaced with explicit no-provider hooks. No Docker startup/pull/build
is permitted. Only the selected probe may run; preparation stops before counting
the next model request. Unexpected extra counts/dispatches fail closed.

The sampler's two-sentence system-message deletion does not match the original
segment seed. A scoped verifier normalizes only that exact selected input back to
its original system message before checking the inherited binding. All other
inputs use the normal validator. Original seed artifacts and segment IDs are never
rewritten. Following inputs use ordinary runtime instructions, as prescribed by
the current-input-only ablation. Source continuation ordering and ciphertext are
validated, not replaced with synthetic reasoning. Ordinary segment rotation may
drop encrypted reasoning from the next input while retaining public results/notes.

The captured boundary must have no unresolved count/provider call and no terminal.
Its displayed old cost allowance is bookkeeping, not paid authority. A separate
live continuation collector must bind a fresh cap, exact credentials, model/task,
remaining counters/deadline and the new first request before any paid approval.
Neither replay nor boundary preparation establishes an agent repair or acceptance.
