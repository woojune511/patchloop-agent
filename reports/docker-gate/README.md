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

`research-moto-query-scanned-count.json` records the seventh research admission and first
development-validation task. It pins SWE-rebench V2 instance `getmoto__moto-7208`, base commit
`624de34d...` and image `sha256:dfdf957a...`. On clean harness commit `b4cc0ec8...`, the
production-only reference passed three official evaluations, while the base passed 182 selected
regressions and failed the nine-check private oracle. Six semantic partial fixes and one forbidden
test edit were rejected. The benchmark's 173 logical P2P nodes expand to 179 concrete passing cases;
nine explicitly deselected endpoint tests are outside that P2P declaration. All containers ran
without network, and the gate made zero model/API calls.

`research-babel-strict-grouped-decimal-trailing-zeroes.json` records the eighth research admission
and completes the two-task development-validation lane. It pins SWE-rebench V2 instance
`python-babel__babel-1042`, base commit `aca76637...` and image `sha256:864e84fc...`. On clean harness
commit `313af714...`, the exact production reference passed three official evaluations, while the base
passed all 132 upstream number tests and failed nine of the 16 private checks. Seven semantic partial
fixes and one forbidden test edit were rejected. The registered checks import submitted source from
`/workspace` while using only the pinned image's generated CLDR data; a source-binding check enforces
that boundary. All containers ran without network, and the gate made zero model/API calls.

`research-sqlglot-duckdb-ignore-nulls-modifier-order.json` records the ninth research admission and
first core-cross-repo held-out task. It pins SWE-rebench leaderboard instance
`tobymao__sqlglot-7187`, base commit `0e8d0824...` and image `sha256:43c43d77...`. On clean harness
commit `89f47025...`, the exact production reference passed three official evaluations, while the base
passed all 39 upstream DuckDB tests and failed the 21-check private oracle. Seven semantic partial
implementations were rejected at hidden acceptance, including a BigQuery `HAVING MAX` negative-transfer
mutant; a forbidden test edit additionally failed scope and test-tampering checks. All containers ran
without network, and the gate made zero model/API calls.

`research-pdm-target-project-options-loading.json` records the tenth research admission and first
core-same-repo held-out task. It pins SWE-rebench leaderboard instance `pdm-project__pdm-3759`, base
commit `e96d535b...` and image `sha256:7a012a5b...`. On clean harness commit `ad25a8a9...`, the
hardened maintainer-follow-up reference passed three official evaluations, while the base passed 63
network-independent regressions and failed the 11-check private oracle. The exact benchmark production
patch and eight other semantic partials failed hidden acceptance; one forbidden test edit additionally
failed scope and test-tampering checks. One declared P2P node that attempts an external install is
explicitly deselected. All 14 containers ran without network, and the gate made zero model/API calls.

`research-anyio-extensionless-entrypoint-worker-main.json` records the eleventh research admission
and second core-same-repo held-out task. It pins SWE-rebench leaderboard instance
`agronholm__anyio-1134`, base commit `01b8d023...` and image `sha256:d7997027...`. On clean harness
commit `9dfc60dd...`, the exact one-file production reference passed three official evaluations, while
the base passed all 36 upstream process regressions and failed the 11-check private oracle. Nine
semantic partial implementations failed hidden acceptance; one forbidden test edit additionally
failed scope and test-tampering checks. All 14 containers ran without network and with read-only root
and submitted filesystems, and the gate made zero model/API calls. The upstream image has no configured
user, so Docker used its default root user; this is disclosed in the report and limitations rather than
being conflated with the native PatchLoop image's non-root smoke.

`research-param-shared-rx-fanout-cache.json` records the twelfth research admission and second
core-cross-repo held-out task. It pins SWE-rebench leaderboard instance `holoviz__param-1117`, base
commit `833c8f05...` and image `sha256:c10bc0ad...`. On clean harness commit `4d73605a...`, the exact
production reference passed three official evaluations, while the base passed 94 upstream reactive
regressions and failed the ten-check private oracle. Eight semantic partials and one forbidden test edit
were rejected. All 13 containers ran without network and with read-only submitted filesystems, and the
gate made zero model/API calls.

`research-hf-hub-custom-tqdm-class-contract.json` records the thirteenth research admission and third
core-same-repo held-out task. It pins SWE-rebench leaderboard instance
`huggingface__huggingface_hub-4056`, base commit `6983a4d3...` and image `sha256:cbfae263...`. On clean
harness commit `962668e8...`, the exact two-file production reference passed three official evaluations.
The base passed all 17 tests present in the frozen upstream file and failed nine of 15 private cases.
Nine semantic partials and one forbidden test edit were rejected. An adversarial pre-gate review found
an escaping combined partial in the original oracle; the strengthened oracle rejects that union and the
evidence retains it explicitly. All 14 containers ran without network and with read-only submitted
filesystems, and the gate made zero model/API calls. The image has no configured user, so Docker used
its default root user.

`research-mtplx-mixed-content-tool-call-stream.json` records the fourteenth research admission and
third core-cross-repo held-out task. It pins SWE-rebench leaderboard instance
`youssofal__mtplx-21`, base commit `c06cc132...` and image `sha256:32510a90...`. On clean harness
commit `82a0c23b...`, the hardened one-file reference passed three official evaluations, while
base/no-op passed all 55 registered CPU/mock regressions and failed the 21-case private oracle. The
exact accepted upstream source patch was retained among nine rejected semantic patches because it
matches lookalike marker stems and can discard non-whitespace stream residue; one forbidden test edit
additionally failed scope and test-tampering checks. The benchmark's four F2P and five P2P nodes all
come from its excluded test patch, and three MLX-runtime environment failures are explicitly
deselected from the independent base-resident regression surface. All 14 containers ran without
network and with read-only submitted filesystems, and the gate made zero model/API calls. The image
has no configured user, so Docker used its default root user.

`research-fusesoc-retained-parse-error-diagnostics.json` records the fifteenth research admission
and fourth core-cross-repo held-out task. It pins SWE-rebench leaderboard instance
`olofk__fusesoc-776_interface`, base commit `d2e6e720...` and image `sha256:1e971791...`. On clean
harness commit `da3105d3...`, the exact three-file production reference passed three official
evaluations. Base/no-op passed the 12 selected visible regressions and failed the ten-case independent
oracle; eight semantic partial implementations were rejected at hidden acceptance, and one forbidden
test edit additionally failed scope and test-tampering checks. The visible suite collects 14
base-resident tests but explicitly deselects the network-dependent export case and the lockfile case
that writes beneath the read-only submitted workspace. All 13 containers ran without network and
with read-only root and submitted filesystems. This is deterministic evaluator admission evidence,
not agent performance. The image has no configured user, so Docker used its default root user. The
report SHA-256 is `cef87dda16402d874b28264fcbed5bba2acf07736800c5fd297d812112081918`.

`research-tox-dotted-version-factor-base-python.json` records the sixteenth research admission and
fourth core-same-repo held-out task. It pins SWE-rebench leaderboard instance
`tox-dev__tox-3846`, base commit `ae05f2a3...` and image `sha256:269a3255...`. Because accepted PR
#3846 immediately regressed real multiple-factor names, the hardened one-file reference combines its
factor grammar with accepted follow-up PR #3851's conflict-policy handling. On clean harness commit
`678d30a5...`, that reference passed three official evaluations. Base/no-op and all ten semantic
partials failed the 17-case independent oracle; four semantic partials also failed visible regression,
and one forbidden test edit additionally failed scope and test-tampering checks. The visible check
covers 101 of 110 declared P2P nodes through a 99-case primary invocation plus two explicitly
re-included healthy siblings. All 15 runs were `official=true` and made zero model/API calls. This is
deterministic evaluator admission evidence, not agent performance or a live-model core result. The
image has no configured `User`, so Docker used its default root user. The report SHA-256 is
`216ccfd1f9017ca499c9902ac857a2e6d4ebc0dca1aeb1aff04e9af396485fe6`.

`research-dagster-subset-partition-definition-selection.json` records the seventeenth research
admission and fifth core-cross-repo held-out task. It pins Dagster PR #33605 through SWE-rebench
leaderboard instance `dagster-io__dagster-33605`. On clean harness commit
`26f28cf11d53f3b0e17b2a4663d0ce68afe63b27`, the exact two-file production reference passed all
three repetitions. Base/no-op passed all 28 visible regressions and failed all nine cases in the
independent hidden oracle; eight semantic partial implementations were rejected, and one forbidden
test edit failed hidden acceptance, scope and test-tampering checks. All 13 runs were
`official=true`. Visible tests and the hidden oracle executed read-only, with the private-v2 hidden
artifact bound to
`sha256:dbfd76a912a27d498092fda20e37db4d99c69fc359d8a5e1c048751e5be24c86`.
The gate made zero model/API calls and incurred zero model cost. This is deterministic evaluator
admission evidence, not agent performance or a live-model core result. The report SHA-256 is
`2d95aa36990b8cd475476a0992b0db7a8d9259d5c7a21d35c99ea3a6c551d012`.

`research-kubeflow-exit-handler-after-dependencies.json` records the eighteenth research admission
and completes the six-task core-cross-repo lane. It pins Kubeflow Pipelines issue #10722 and PR
#13112 through SWE-rebench leaderboard instance `kubeflow__pipelines-13112`. On clean harness commit
`5e7b019e60b4d76f67e48bafe6fd1a3b309fe313`, the exact two-file production reference passed all
three repetitions. Base/no-op passed all 277 base-resident visible tests plus 15 subtests and failed
the 11-test independent oracle; eight semantic partial implementations were rejected, and one
forbidden test edit failed hidden acceptance, scope and test-tampering checks. The benchmark's 278
P2P declaration includes one preservation test added by its excluded test patch, leaving exactly
277 base-resident P2P tests. All 13 runs were `official=true`, used network-disabled read-only
evaluator boundaries and made zero model/API calls. The external image has no configured `User`, so
Docker used its default root user. This is deterministic evaluator admission evidence, not agent
performance or a live-model core result. The report SHA-256 is
`c7998d064949dd5a67f05c15ff7d426ef1051f74fea7bb03e37f91c7d1d5084c`.
