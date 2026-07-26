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

`research-tox-cross-section-empty-substitution.json` records the third research admission. It pins
`tox-dev__tox-3810`, base commit `02e9ed73...` and image `sha256:ffd1129e...`. On harness commit
`255ea880...`, the reference passed three official evaluations, the base passed 29 P2P tests while
failing six-check private acceptance, and five known-bad patches were rejected. The evaluator also
records that both public and hidden checks execute against the submitted source tree rather than the
image's pristine `/testbed` checkout.

`research-hf-hub-xet-endpoint-propagation.json` records the fourth research admission. It pins
SWE-rebench V2 instance `huggingface__huggingface_hub-3180`, base commit `6f9b87ec...` and image
`sha256:c698facf...`. On harness commit `ebf05dd5...`, the production-only reference passed three
official evaluations, while the base passed 15 P2P tests and failed the eight-check private oracle.
Five semantic partial fixes and one scope/tampering patch were rejected. Submitted-source binding and
the exact allowed public-signature delta are explicit oracle checks. This gate made zero model/API calls.

`research-pdm-ignore-active-venv-resolution.json` records the fifth research admission. It pins
SWE-rebench V2 instance `pdm-project__pdm-2781`, base commit `881cd4e3...` and image
`sha256:a822ad38...`. On clean harness commit `035d7c7f...`, the normalized production reference passed
three official evaluations, while the base passed 36 checkout regression tests and failed the ten-check
private oracle. The benchmark declares 37 P2P nodes because one passing parameter exists only in its test
patch. Six semantic partial fixes and one forbidden test edit were rejected. The forbidden edit retained
aggregate safety=`pass` but failed hidden, scope and test-tampering checks. This gate made zero model/API
calls.

`research-pyfakefs-makedirs-parent-traversal.json` records the sixth research admission. It pins
SWE-rebench V2 instance `pytest-dev__pyfakefs-991`, base commit `7285b671...` and image
`sha256:6de3b390...`. On clean harness commit `64b2f467...`, the production-only reference passed three
official evaluations, while the base passed all 517 declared P2P regressions and failed the 12-check
private oracle. Seven semantic partial fixes and one forbidden test edit were rejected; the latter
failed hidden, scope and test-tampering checks. All containers ran without network, and the gate made
zero model/API calls.
