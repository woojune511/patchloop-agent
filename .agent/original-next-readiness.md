# Next original benchmark task

## Frozen selection

Conan `conan-io__conan-19735_interface`, base
`4a65d65f53d2ab37f4ce0e52dc3f25cd832b2934`.
The original public issue concerns Emscripten informational output before its
version line causing compiler detection to return None.

Dataset `nebius/SWE-rebench-leaderboard`, revision
`ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b`, split `2026_03`.
Parquet SHA-256 `18e198ac18b3c25b307c0aa5d9b6e20d338886e186bf7c12addb759ad4165a61`.
Reuse the existing `patchloop-original-input-pilot-v1` hash ranking, taking one
repository after excluding the current candidate ledger and all public packages.
83 of 110 rows satisfy the existing public issue/image/pytest-parser filter and
repository exclusion. No tests, reference patch, hints or outcomes were decoded
before selection; image availability did not affect selection.
This is absence from current inventories, not proof of no historical exposure or
model-training contamination. Do not replace the selected task for convenience.

## Original evaluator materials

After freezing selection, saved the original test patch, reference patch, F2P/P2P
lists and install configuration in external operator artifacts. One FAIL_TO_PASS
and 21 PASS_TO_PASS cases are declared. Original command:
`pytest --no-header -rA --tb=line --color=no -p no:cacheprovider test/unittests/util/detect_test.py`.
Declared Python 3.13; parser parse_log_pytest. Preserve these original semantics;
do not substitute locally invented hidden tests. Pinned parser/grading/test-spec
sources from SWE-rebench/SWE-bench-fork revision
`e4907b7a90eafaa1f0a6428fd04fe31cdd8b4284` are bound as artifacts. This is an
explicit harness pin, not proof of the dataset producer's historical harness.

External root: `C:\pt\preparations\original-next-20261001-v1`.
Hash-chained journal: `runs/run_dev_originalnextselection.jsonl`.
Public selection and private evaluator artifacts remain separated from future
coding-agent input. Raw reference/test bodies were stored as data, not printed.

## Approved image and completed calibration

The user approved the pinned linux/amd64 image pull, which completed:
`swerebench/sweb.eval.x86_64.conan-io_1776_conan-19735_interface@sha256:564734fbebe544567e2e47bac7362ae68a749ffdaa7401dd273903d3552277fa`.
Only the final layer was newly downloaded according to pull output; 1.28 GB was
total compressed layer size, not measured traffic or disk growth. No build or
Docker startup occurred.

[Original calibration](../docs/history/2026-10-01-conan-original-calibration.md)
confirmed exact base/clean source, Python 3.13.13 and pytest 7.4.4. Baseline:
F2P 0/1, P2P 21/21, RESOLVED_NO. Reference: F2P 1/1, P2P 21/21, RESOLVED_FULL.
All required cases were accounted for; no timeout, setup error or extra failure.
Separate containers ran without network or host mounts and were cleaned up.
Journal: `runs/run_dev_conanoriginalcalibration.jsonl` under the external root.

## Package integration and probe preparation complete

[Package admission](../docs/history/2026-10-01-conan-package-admission.md) added
`tasks/dev-train/original-conan-19735`, version 1. Original issue and oracle inputs
are preserved. Full isolated evaluation rejects a behavior-preserving baseline
control and accepts the reference; public tests pass 28/28 on both. Scope and
safety pass. This is operator calibration, not an autonomous solve.

Task hash:
`sha256:7853e01fc73daf9d0c50fd14c252d65468de2283afa43b2a557877f1f1e5b67a`.
Prepared source: `source/prepared-source.json` under the external root.
Journal: `runs/run_dev_conanpackage.jsonl`. Focused tests 43 PASS, Ruff PASS;
mock `run_dev_17ecdace4a5840bb` reaches EVALUATOR_PASS, safety NOT_RUN.

The first [preparation attempt](../docs/history/2026-10-01-conan-probe-preparation.md)
failed because patch-ng>=1.18.0,<1.19 has no usable public wheel; its receipts remain
unchanged. The [follow-up](../docs/history/2026-10-01-conan-probe-ready.md) built the
reviewed public patch-ng 1.18.1 sdist offline in the existing clean Python image,
then reused explicit generated-wheel admission. Conan setup.py was not executed.
Descriptor: probe-dependencies-v2/prepared-probe-dependencies.json under the external
root. Real DockerProbeSandbox imports patch_ng and the Conan detection module;
exit 0, no timeout, cleanup confirmed. Journal: runs/run_dev_conanprobecanary.jsonl.
This verifies import readiness in Python 3.12, not complete dependency behavior or
repair success. Public/hidden checks remain in the calibrated original Python 3.13
image. No probe disabling, dependency-version relaxation or runtime policy change.
The approved single run is now complete; see the
[result](../docs/history/2026-10-01-conan-live-result.md). Allocation closed.

## Approved single live invocation (completed; no reuse)

The user approved the exact proposal below. Execution run_dev_ffee311ba7aa4a11
finished EVALUATOR_PASS at USD 0.544468 of USD 3. This command is a record of the
closed invocation, not permission to run it again. No retry/resume is authorized.

Question: can the unchanged working agent baseline repair this original public
issue and pass the calibrated original oracle in one fresh attempt? This is a
development observation, not an intervention comparison or general success-rate
estimate. No reference patch, added hidden tests, evaluator feedback or operator
repair hints enter agent context. Start from the frozen clean base and empty state.

Exact scope: task original-conan-19735 version 1 and hash above; model
gpt-5.4-2026-03-05, xhigh, desired output ceiling 25,000 tokens; repository credential
file C:\Users\geonj\Documents\PatchLoop\.env; repeat 1; proposed invocation-wide
cap USD 3. Credential existence was checked without loading or printing its value.
This is a new proposed allocation, not reuse of any earlier balance.

Keep selected segmented-v1/result-or-size-v1/brief-v1/probes-none/repair-recheck/
protected-v1/per-call-v1 policies, 40 model calls, 100 actions, four accepted edits,
1,800 seconds, four changed production files and 1,000 diff lines. No test,
dependency or public API edits. No automatic retry, resume, operator rescue,
budget replenishment or second run. Count before dispatch, zero SDK retries;
stop on count/transport/billing uncertainty or any exhausted limit.

After approval, run from HEAD-clean tracked runtime/task inputs; record the exact
commit/runtime and prepared descriptor identities through the normal run envelope.
Reverify task, source, dependencies and existing images before dispatch. An input
identity change requires review, not silent substitution. Proposed state root must
be unused; preserve it after execution. No image pull/build or Docker startup.

```powershell
$env:PATCHLOOP_STATE_ROOT = 'C:\pt\runs\conan-original-live-20261001-v1'
.venv\Scripts\patchloop.exe dev `
  --provider openai `
  --task tasks/dev-train/original-conan-19735/public.yaml `
  --model gpt-5.4-2026-03-05 --reasoning-effort xhigh `
  --max-output-tokens 25000 --repeat 1 --max-cost-usd 3 `
  --env-file C:\Users\geonj\Documents\PatchLoop\.env `
  --context-policy segmented-v1 --segment-boundary-policy result-or-size-v1 `
  --planning-policy brief-v1 --enable-probes --probe-policy none `
  --repair-recheck --repair-inspection-policy protected-v1 `
  --completion-cost-policy per-call-v1 `
  --prepared-source C:\pt\preparations\original-next-20261001-v1\source\prepared-source.json `
  --prepared-probe-dependencies C:\pt\preparations\original-next-20261001-v1\probe-dependencies-v2\prepared-probe-dependencies.json
```

Report execution completion, exact submitted patch, public checks, original F2P/P2P
hidden evaluation, acceptance, safety, time and settled cost separately. Success
requires original task acceptance and passing scope/safety; public PASS or import
readiness alone is insufficient. Preserve an unsuccessful result and diagnose it
before proposing another run. This draft grants no paid dispatch authorization.
