# SWE-bench Lite mini pilot

## Question and scope

Measure whether PatchLoop can complete original SWE-bench Lite development tasks
with GPT-5.4 mini, and measure actual per-task cost before considering the 300-task
test split. This is a three-task integration/cost pilot, not a model comparison,
agent improvement claim or benchmark score. All runs remain official=false.

On 2026-10-02 the user approved the three image downloads, integration/calibration,
and the conditional USD 3.60 live pilot below. It never covers the 300 test tasks.
Registered public/private calibration passes. The three calibrated packages are
admitted under tasks/dev-train; the frozen live invocation uses the allocation below.
This exact conditional approval is retained; no larger or replacement allocation follows.

## Frozen inputs

- Dataset: SWE-bench/SWE-bench_Lite, dev split only, 23 rows.
- Revision: b0dde1093fe417d83b7184254edf8199c1f0dff5.
- File: data/dev-00000-of-00001.parquet.
- SHA-256: b90bcbfaca1b5f65155500124a977876c264a4003ab384aca4dfc39a54bef89f.
- Official SWE-bench harness revision: 02e7a74ffd0b707aab73d203fe87bdc7c76afc8e.
- Selection: sort SHA-256 of seed + newline + instance ID, then take the first
  three distinct repositories. Seed: patchloop-swebench-lite-dev-20261002-v1.
  Selection uses neither issue/answer content nor evaluation outcomes or image availability.

| Instance | Base commit | Checked-in package under tasks/dev-train |
| --- | --- | --- |
| pylint-dev__astroid-1978 | 0c9ab0fe56703fa83c73e514a1020d398d23fa7f | swebench-lite-dev-pylint-dev-astroid-1978 |
| pydicom__pydicom-1256 | 49a3da4a3d9c24d7e8427a25048a1c7d5c4f7724 | swebench-lite-dev-pydicom-pydicom-1256 |
| marshmallow-code__marshmallow-1359 | b40a0f4e33823e6d0f341f7e8684e359a99060d1 | swebench-lite-dev-marshmallow-code-marshmallow-1359 |

Operator evidence: C:/pt/analyses/swebench-lite-dev-preparation-20261002-v1.
The plan.json file is a human-readable projection; the hash-chained
runs/run_dev_swebenchliteprepare.jsonl and referenced artifacts bind provenance.
Never mount evaluator-artifacts into a coding-agent workspace. Public input is
limited to instance ID, repository, base commit and original problem statement.
Hints, reference/test patches, scoring lists and evaluator scripts remain excluded.
Raw benchmark test patches are publicly downloadable; their exclusion from the
agent context does not establish absence from model training data.

## Images and environment

The three exact image identities are:

- swebench/sweb.eval.x86_64.pylint-dev_1776_astroid-1978@sha256:c8c32dfa1bb2ac5bf5b52e2c96fbd18b0a3a8a864b30e757b03f5a79a6e6a685
- swebench/sweb.eval.x86_64.pydicom_1776_pydicom-1256@sha256:6443432fb247833fa2a2158e751ef62817e36d0a0219aa89ada44bfe7129a3fd
- swebench/sweb.eval.x86_64.marshmallow-code_1776_marshmallow-1359@sha256:440807ded8d239ea71daaf31d3158013e58b9cdfad8a56d4f82e646426d3f4e6

Registry metadata reports 3,107,458,297 compressed bytes in total (2.894 GiB),
before shared-layer reuse. All three approved digests were downloaded. Host free
space was about 61 GiB afterward; image-only expanded usage was not isolated.
This is not a readiness claim for the complete benchmark.
Do not delete existing images, branches, worktrees or evidence to make room.
After approval, acquire only these digests, sequentially; no image builds or
automatic alternative images. Check actual free space before every acquisition
and stop if it falls below 25 GiB. Registry metadata and preparation make no pulls.

## Integration and calibration before live execution

Existing original-input packages use a SWE-rebench-specific pytest oracle.
Do not reuse it as though it were the official SWE-bench Lite evaluator.
The selected upstream harness/data schema includes the original eval_script,
repository-specific log parser and grading. Preserve these unchanged, and export
submitted diffs in official prediction format. Native control execution is implemented
in diagnostics/swebench_lite_native.py. Its transport restores exact canonical LF
bytes after Windows text writes. Its Docker client denies pulls, disables network
and removes extra capabilities; original test and grading code are unchanged.

The registered-check adapter executes the original test patch/pytest arguments with
the task interpreter and unchanged official Python parser/grader. It imports copied
public source from temporary storage instead of installing an editable package into
a read-only image. Import namespaces avoid loading unrelated Docker/cloud modules.
This is an adapter, not the full upstream CLI. Final submitted patches must also
receive native upstream evaluation; any disagreement must be reported.

Construct public checks only from base-repository documentation/source, not
private test targets or reference-patch locations. Keep the current restricted
agent tools and public/private boundary. Inspect the evaluator images for original
source and dependencies; ensure solver workspaces contain neither evaluator tests
nor answers. Bind digests and package hashes and commit packages before live calls.

Run base and original reference controls evaluator-side on each selected task.
Require expected unresolved/resolved results and complete F2P/P2P accounting, with
no collection/setup errors or missing tests. Run focused boundary tests and mock
smoke. Stop paid admission on any failed control or integration defect; preserve
evidence instead of rewriting the original test oracle or choosing replacement tasks.
Deterministic host transport/import fixes may receive separately identified
provider-free checks; this does not authorize retries of completed solver attempts.

## Approved conditional invocation

- Exact model: gpt-5.4-mini-2026-03-17; reasoning xhigh, desired output 25,000.
- Credential file: C:/Users/geonj/Documents/PatchLoop/.env; never put its contents
  in logs, task/evaluator inputs or subprocess environments.
- Repeat: one fresh solve per selected task, in the table's order, sequentially.
- Positive invocation cap: USD 3.60; maximum USD 1.20 per task, no budget transfers.
- Existing selected policies: segmented-v1, result-or-size-v1, brief-v1, probes
  enabled/policy none, repair-recheck, protected-v1, per-call-v1 admission.
- Existing per-task limits: 40 calls, 100 actions, four accepted edits, 1,800 seconds.
- Count actual input before dispatch; zero SDK retries. Stop the whole invocation
  on count, transport, billing, integrity or container-cleanup uncertainty.
- A settled resource limit or wrong patch is a recorded outcome; no retry,
  replacement task, funded continuation or test correction is permitted.
- Submit one patch per task to unchanged official evaluation. Never return private
  evaluation feedback to a solver. Report resolved, unresolved, resource-limited
  and infrastructure outcomes separately, including PatchLoop safety evidence.

Report task count, submissions, resolved count, total cost, total cost divided by
resolved count (undefined at zero), calls and elapsed time. Use observed usage to
project a range for a future 300-task allocation, not a promise of equal cost or
success. Do not tune against the test split. Any later full run needs a separate
frozen scope, integration check and budget.

## Preparation status

Implemented and executed: pinned dev-data/selection, separate public/private
artifacts, approved image pulls, native controls (6/6 expected), and registered
public/private controls (6/6 expected). The latter are preserved under
C:/pt/analyses/swebench-lite-registered-controls-20261002-v4.

Pydicom's public required check is the complete existing test_json.py and
test_sequence.py modules: 31 tests, chosen from the public issue's JSON/SQ scope.
It is not the full repository suite. That suite requires legacy pytest behavior
and external DICOM fixtures absent from this pinned, offline image. A diagnostic
restoring class setup/teardown exposed these additional failures; its shim was not
adopted. No test assertions, expected outcomes or private target lists determine
the public check. Original hidden evaluation and the other tasks' public full
suites are unchanged. Each public check receives a temporary writable HOME.

The public astroid suite has two narrow filters for newer setuptools' pkg_resources
deprecation warnings; assertions and original evaluation are unchanged. This
environmental adjustment belongs only to public regression, not the oracle.
The three calibrated packages are copied byte-for-byte into tasks/dev-train.
Raw-byte Git attributes preserve their original evaluator artifact hashes.
See the [initial findings](../docs/history/2026-10-02-swebench-lite-preflight.md)
and [public-check follow-up](../docs/history/2026-10-02-swebench-lite-public-checks.md).

Model calls, submitted agent patches, native agent evaluation and all 300 test tasks
remain NOT_RUN. Model cost is USD 0.00; the credential file was not loaded.

Reproduction of preparation only (optional pyarrow stays outside runtime deps):

```powershell
uv run --no-sync --with pyarrow python -m diagnostics.swebench_lite_prepare --output C:/pt/analyses/<new-directory>
```

Official references: [dataset](https://huggingface.co/datasets/SWE-bench/SWE-bench_Lite),
[evaluation](https://www.swebench.com/SWE-bench/guides/evaluation/),
[mini pricing](https://developers.openai.com/api/docs/models/gpt-5.4-mini).
