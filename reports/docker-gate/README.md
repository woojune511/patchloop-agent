# Docker evaluator gate

This directory records the 2026-07-23 official Docker smoke checkpoint. The evaluator accepted the
audited reference patch and rejected all six known-bad patches using one pinned Linux image. The
machine-readable summary includes the local run IDs and hashes of their immutable manifest, result and
provenance files.

The source artifacts remain under `.patchloop/artifacts/runs/<run-id>` on the machine that executed the
gate and are intentionally ignored as mutable runtime state. This summary is evidence for the single
smoke task only; it is not the planned 23-task dataset or 96-run model campaign. The repository had no
initial commit when this checkpoint ran, so its manifests record `harness_git_commit=uncommitted`. Create
the baseline commit and rerun this gate before treating the evidence as a frozen portfolio artifact.
