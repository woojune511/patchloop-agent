# Saved first-patch cleanup diagnostic

`diagnostics/anyio_cleanup_probe.py` uses verified closed public journals to restore
the exact B1/B2 first accepted patches in fresh external prepared-source workspaces.
Verify preimage, postimage and complete-diff hashes; never inspect or modify the
old live workspaces. The closed comparison manifest/audit and hash-chained source
journals bind the candidates. No credentials, provider, evaluator or image acquisition.

The public program directly drives TestRunner with a ContextVar async-generator
fixture and callback KeyboardInterrupt. It preserves the existing waiting caller
and shared runner tasks; it adds no task wrapper, awaits or monkeypatched methods.
Each patch runs once without source tracing and once with synchronous filtered
line tracing. Snapshots observe done/cancelled/cancelling, future state, cancel sites
and waiting stacks. Tracing overhead remains a possible perturbation; compare
discrete lifecycle outcomes with the untraced execution before interpreting it.

A two-second loop timer records stalled state and exits the isolated process with
`diagnostic_watchdog_exit`. That intentional diagnostic stop is not completed
fixture cleanup or task success, even though the sandbox process exits zero.
It avoids adding cancellation requests during failure cleanup. The ordinary sandbox
deadline remains a separate backstop. Stop on external timeout, truncation, missing
identity or uncertain cleanup; retain all receipts, with no automatic retry.

The optional `--remove-caller-cancel` phase runs B1 only, twice with the same program.
Use it after source-line observations support the repeated-cancel hypothesis. It
removes exactly the caller handler's runner.cancel line, retaining the outer
run_test cancellation, future logic and all other code. Bind the changed diff as a
synthetic one-line ablation, not an agent repair or default adoption. This phase
does not run registered checks or isolated acceptance. An observed local rescue
does not establish safety for other caller-cancellation paths.

Original phase is four probes; ablation is two. All generated state is external
CAS and append-only dev-run-v1 JSONL. Confirm candidate bytes stay unchanged during
each probe and exact owned containers are absent after collection. Record the
measured mechanism separately from hypotheses, broader task correctness and model
improvement. Keep historical packets and records immutable.
