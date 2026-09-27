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
Its displayed old cost allowance is bookkeeping, not paid authority.
Neither replay nor boundary preparation establishes an agent repair or acceptance.

`diagnostics/probe_boundary_collector.py` supplies a separate funded fork through
Python `prepare(source_root, env_file, result_root, output, new_cap_usd)` and
`collect(manifest_path, approved_hash, approved_cap_usd)`. Preparation binds the
source journal/envelope/receipt, runtime, implementation, dev-train task, model,
credentials path, one repetition and exact first funded request. It performs
read-only environment checks. Execution requires a fresh explicit paid approval.

The fork copies runtime CAS recursively and preserves journal bytes, then replays
only accepted mutation anchors in a fresh prepared-source workspace. Historical
sampler provenance links remain external references; probes/checks are not replayed.
Settled usage stays historical; the fresh group ledger counts only new calls.
Only cost changes in the first input. Work counters and the already extended active
deadline remain unchanged; old unused funds never reopen. The existing ledger and
adapter enforce count-before-dispatch, zero SDK retries and uncertainty stops.
The result root is single-use even after preflight failure; no automatic resume.

The ordinary runner revisits B2's parent input before constructing the next input.
A scoped exact-input verifier therefore retains the original two-sentence overlay
normalization for that inherited input alone. New inputs use normal seed validation.
Local completion-advice removal continues as in the source run. Runtime defaults
are unchanged. Scripted rehearsal checks restoration and failures, not agent quality.
