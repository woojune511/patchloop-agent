# Docker evaluator gate

This directory records the 2026-07-23 official Docker smoke checkpoints. `summary.json` covers the
original CSV task: the evaluator accepted its reference patch and rejected all six known-bad patches.
`smoke-expansion.json` covers the config and path tasks: both references passed and eight known-bad
patches were rejected. Every run used the same pinned Linux image. The summaries include local run IDs
and hashes of their immutable manifest, result and provenance files.

The source artifacts remain under `.patchloop/artifacts/runs/<run-id>` on the machine that executed the
gate and are intentionally ignored as mutable runtime state. These summaries cover the complete three-task
smoke split; they are not the planned 23-task dataset or 96-run model campaign. CSV manifests are pinned
to baseline commit `cf38649bbbf458316f38e64a579fd0196c782237`; config/path manifests are pinned to task
commit `024a3a375dc9514be6d127199d10f7115659eecf`.
