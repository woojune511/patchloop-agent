# SWE-bench Lite remaining dev tasks: metadata inventory

## Question and decision

The three-task mini pilot completed original evaluation at low model cost, but
cannot characterize the current agent across the dev split. The user authorized
PR/CI delivery and a provider-free investigation of the remaining 20 tasks before
deciding on more image downloads or paid execution. The question is whether that
fixed larger roster can use trustworthy public checks and original evaluation.

All 20 have accessible Linux/amd64 image manifests and pinned public source trees.
None of those exact image digests is present locally. This is metadata readiness,
not execution readiness: public checks, original base/reference calibration and
task admission remain NOT_RUN for all 20. No model call, image pull/build or
container execution occurred during this inventory. The credential file was not loaded.

Keep all remaining dev instances in the roster, with no outcome-based replacements.
The next step is image acquisition and provider-free integration/calibration, subject
to explicit approval. A paid run is a separate later decision. Do not retune the
agent on the previous two failures or infer that a new prompt is needed from them.

## Frozen inputs and evidence

The dataset and harness revisions are unchanged from the
[pilot protocol](../../.agent/swebench-lite-pilot.md): dataset
b0dde1093fe417d83b7184254edf8199c1f0dff5, harness
02e7a74ffd0b707aab73d203fe87bdc7c76afc8e. The locally retained parquet was verified
against SHA-256 b90bcbfaca1b5f65155500124a977876c264a4003ab384aca4dfc39a54bef89f.
Subtract the three completed instance IDs from the 23 dev rows, then sort by ID.
This fixes 20 tasks across six repositories without consulting their answers.
No test-split row was selected.

Evidence root: C:/pt/analyses/lite-dev20-inventory-20261002-v1.
The hash-chained runs/run_dev_litedev20inventory.jsonl binds the roster, data,
per-task registry/source observations, review and integrity audit. summary.json is
a readable projection; image-acquisition-manifest.json lists the exact 20 image
digests proposed for download. The audit checked 202 unique artifact references.
Read-only drivers audit.py and finalize.py are hash-bound. The inventory inspected
execution HEAD aec32bf42002305196927df8b727eb0440e683b7.

Source metadata came from each repository's GitHub tree at its exact base commit,
then configuration files from raw.githubusercontent.com at that same commit.
Image metadata came from registry-1.docker.io/v2/<repository>/manifests/latest;
the response bytes and config digests were verified and retained. Only manifests
and small configuration blobs were fetched, never image filesystem layers.
Private original evaluation material stays in operator evidence; it is not a
source for selecting agent-visible checks or adding task hints.

## Roster and compressed image sizes

| Repository | Remaining issue IDs | Images | Sum GiB |
| --- | --- | ---: | ---: |
| marshmallow-code/marshmallow | 1343 | 1 | 0.917 |
| pvlib/pvlib-python | 1072, 1154, 1606, 1707, 1854 | 5 | 7.898 |
| pydicom/pydicom | 901, 1139, 1413, 1694 | 4 | 4.640 |
| pylint-dev/astroid | 1196, 1268, 1333, 1866 | 4 | 3.643 |
| pyvista/pyvista | 4315 | 1 | 1.831 |
| sqlfluff/sqlfluff | 1517, 1625, 1733, 1763, 2419 | 5 | 4.744 |

The naive manifest layer/config sum is 25,418,509,532 bytes (23.673 GiB).
Deduplicating layer digests across these 20 images gives 105 layers totaling
9,266,684,090 bytes (8.630 GiB), plus small configuration blobs. Existing daemon
cache overlap was not deducted. Actual download traffic and unpacked disk growth
are unmeasured. C: had 62,662,639,616 bytes (58.36 GiB) free at inventory time;
this does not establish sufficient unpacked capacity. No existing image was removed.

## Integration and public-check readiness

All 20 original evaluation scripts have one plain pytest command and valid
nonempty, nonoverlapping test membership. All six requested parser names exist in
the pinned upstream parser module. These static facts do not prove evaluator
equivalence. The current private adapter extracts pytest while the original script
also performs setup/editable installation, so native/adapter base and reference
controls are still required at each exact image and source revision.

Current operator tools intentionally bind the first pilot: the native runner
requires three rows, and package preparation assumes its control paths and three
repository layouts. pvlib, pyvista and sqlfluff also need explicit repository
admission. Those seams need bounded generalization before admitting a 20-task batch;
none was changed by this investigation.

| Repository | Public-source observation | What remains to verify |
| --- | --- | --- |
| marshmallow | src/marshmallow and tests; version 2.20 | Previous 3.0 calibration cannot establish this version's public check. |
| astroid | astroid and tests; four version-specific pytest configurations | Collect/run at each base; do not assume prior warning filters are necessary or sufficient. |
| pydicom | pydicom/tests; four different API issues and configuration versions | Select checks from each public issue/source. The previous JSON/Sequence selection does not cover all four. |
| pvlib | pvlib/tests; optional scientific dependencies and remote-data plugin | Offline collection, dependency availability and bounded public regression coverage. |
| pyvista | VTK; OFF_SCREEN fixture setting; upstream skips needs_download by default | Native libraries, rendering requirements and offline collection. A graphics failure has not been observed here. |
| sqlfluff | src/sqlfluff and test/; dbt/plugin configuration | Correct discovery pattern and plugin scope. The public issue for 1763 mentions dbt, so a blanket not-dbt selection is unjustified. |

All public checks are NOT_FROZEN and NOT_RUN. The investigation found integration
gaps and compatibility questions, not 20 proven environment failures. Preserve
original private tests/scoring. Record any later setup/calibration failure against
the full roster instead of silently dropping or replacing that task.

## Proposed next scope, not approval

The reviewable acquisition scope is only the 20 exact digests in the external
manifest, followed by provider-free source preparation, public checks and isolated
original base/reference calibration. No image builds, image/branch deletions or
provider dispatch is included. Recheck free space and stop on insufficient space
or an integrity/cleanup failure; do not remove historical evidence to make room.

A potential later paid batch keeps the mini pilot model and policy: exact model
gpt-5.4-mini-2026-03-17, xhigh, 25,000 output ceiling, once per admitted task,
credential file C:/Users/geonj/Documents/PatchLoop/.env, USD 1.20 per task and
USD 24.00 invocation-wide maximum for all 20. This is a proposed ceiling, not a
spend forecast or authorization. No calls follow automatically from downloading
images or passing calibration. Freeze packages, checks, configuration and stop
rules before requesting the separate live approval. Keep baseline policies fixed
through the batch, no retry or budget transfer, and separate infrastructure,
submission, original resolution, scope/safety, cost and time outcomes.

## Delivery validation

[PR #20](https://github.com/woojune511/patchloop-agent/pull/20) contains the pilot
integration/results and this preparation record. Before adding this documentation,
25 focused/local documentation tests and Ruff passed. A fresh mock smoke reached
isolated evaluation with acceptance PASS and safety NOT_RUN. The remote merge-tree
check was clean. Ubuntu and Windows CI were started at aec32bf4; exact final-head
CI status belongs to the live PR, not this historical inventory record.

No agent runtime, prompt, task package or paid allocation changed during this
inventory. Every result remains official=false and claim-ineligible. The two
original pilot failures and all historical evidence are preserved.
