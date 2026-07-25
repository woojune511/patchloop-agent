# Docker evaluator gate

This directory records the 2026-07-23 official Docker smoke checkpoints. `summary.json` covers the
original CSV task: the evaluator accepted its reference patch and rejected all six known-bad patches.
`smoke-expansion.json` covers the config and path tasks: both references passed and eight known-bad
patches were rejected. Every run used the same pinned Linux image. The summaries include local run IDs
and hashes of their immutable manifest, result and provenance files.

The source artifacts remain under `.patchloop/artifacts/runs/<run-id>` on the machine that executed the
gate and are intentionally ignored as mutable runtime state. The calibration summaries cover the original
three-task smoke split; they are not the planned 20-task research dataset or 96-run model campaign. CSV manifests are pinned
to baseline commit `cf38649bbbf458316f38e64a579fd0196c782237`; config/path manifests are pinned to task
commit `024a3a375dc9514be6d127199d10f7115659eecf`.

`research-loguru-invalid-format-feedback.json` is the first research admission summary. It pins
SWE-rebench instance `delgan__loguru-1451`, upstream base/resolution commits and evaluator image
`sha256:181bd51...`. On harness commit `d7cdd6fa...`, the reference passed three times, the no-op failed
hidden acceptance, five known-bad patches were rejected, and the upstream format regression file reported
20 passes. This is deterministic evaluator evidence with zero model/API calls, not agent performance.

`research-anyio-interrupt-runner-cleanup.json` records the second research admission. It pins
`agronholm__anyio-1121`, base commit `cb245dba...` and image `sha256:063bb968...`. On clean harness
commit `45949f20...`, a hardened reference passed three official evaluations and 20/20 supplemental hidden
stability repetitions. The base failed private no-resume acceptance, 32 P2P tests passed, and five
known-bad patches were rejected. One negative is a source-equivalent normalization of the upstream fix:
PatchLoop rejects it because the later AnyIO #1179/#1180 incident exposed a pytest outcome regression.
