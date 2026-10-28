# Frozen-runtime transfer check on three development tasks

Status: PREPARED_NOT_EXECUTED, official=false, claim-ineligible. New exact paid
execution approval is pending. Prior allocations remain CLOSED.

## Question and selection

The [clean-start Astroid result](2026-10-29-helper-contract-fresh-results.md)
established one successful original reproduction, repair, public verification,
normal delivery and isolated acceptance. It did not establish that the shared
helper contract works beyond that task; helper correction and failed-repair
revision were not exercised. Before adding more mechanisms, freeze the runtime
and inspect other public failure types under the same model and per-task limits.

Select current-dev20 rows **5, 9, 18**, in that order. Selection used public issue
descriptions, not previous outcomes or private evaluator details. Exclude Astroid,
use one task per repository, require an explicit failure and expected result, and
cover three different output contracts. Do not replace a task after observing its
outcome. These tasks belong to a previously exposed development pool, not held-out
data or a statistically representative sample.

| Row | Exact task ID | Public failure contract |
| --- | --- | --- |
| 5 | `swebench-lite-dev-pvlib-pvlib-python-1707` | Numeric boundary: `iam.physical(aoi=100, n=1)` should return zero, not NaN. |
| 9 | `swebench-lite-dev-pydicom-pydicom-1694` | `to_json_dict(suppress_invalid_tags=True)` should suppress invalid-tag conversion errors. |
| 18 | `swebench-lite-dev-sqlfluff-sqlfluff-1733` | SQL fixing should produce the public expected CTE indentation without an extra space. |

The pydicom public report already suggests moving a statement inside a try block.
Keep the original report intact, but do not interpret success as independent cause
discovery. No additional solution, trajectory, prior patch, checkpoint or operator
counterexample is supplied to any solver.

## Frozen conditions and limits

Runtime implementation `14a1aa70da1e9e4d083cb3119afcde8e1bb6a8f6`; preparation
repository head `aca2cf6488ddd4979ffa7ba84dea906d13ae6543`. Runtime hash:
`sha256:12637b2377a327f5e2c1ccd176ccc2669c98d6a5efdf76d509d6f39c24cd5a27`.
No runtime or public-task content changed for this plan.

- Model `gpt-5.4-2026-03-05`, xhigh, provider OpenAI; credential file
  `C:/Users/geonj/Documents/PatchLoop/.env` (existence checked, contents not read).
- One fresh normal `run_dev` per task, sequential, no resume or automatic retry.
  Proposed nontransferable cap USD4.50 per task, **USD13.50 invocation-wide**.
- Per task: 20 responses including at most one protocol correction; 40 tool actions;
  three accepted edits; context 60K; normal/correction output ceilings 40K/25K.
- Per task: 2400 seconds total, including 390 seconds reserved for isolated
  evaluation. Maximum response/output counts are ceilings, not guarantees within
  the monetary cap. Existing count-before-dispatch completion admission remains.
- Thin, segmented-v1, result-or-size-v1, probes enabled/policy none,
  repair-recheck, protected-v1 inspection, completion-recovery-v1 and bounded-v1
  reproduction acquisition match the successful Astroid request.
- Task/source/dependency/state paths change. External caller roots are empty:
  these public tasks use their repository APIs/CLI rather than Astroid's pylint
  caller. There is no private context, cross-run memory or inter-task observation
  sharing. Runtime and settings stay fixed across all three tasks.

Prepared original sources are `C:/pt/ld20p01/s/{5,9,18}/prepared-source.json`.
The old public dependency locks/wheels under `C:/pt/cd20p06c/dependencies/` were
verified and reused offline, preserving selected versions and historical files.
New descriptors are under the new plan's `dependencies/{5,9,18}/` directories and
bind the current Python 3.12 image. Astroid used Python 3.9, and public issue
environments differ too; this is not a causal A/B across tasks. Minimal static
project metadata and source-snapshot versions remain environment limitations.
All required images already exist locally; nothing was pulled or built.

## Execution, measurement and decision

Root: `C:/pt/helper-transfer-three-plan-v1`; result root:
`C:/pt/helper-transfer-three-run-v1`. Requests, prepared identities, source/task
hashes, image digests, scripts and local evidence are bound by `manifest.json`:

`sha256:cf5de320a946525da9caafd83ef0e6bcd1301b3db5792b8cd2d8336e9f819bb9`

Exact proposed command: `& 'C:/pt/helper-transfer-three-plan-v1/run.ps1'`.
An exact new approval is required before this command can dispatch a provider.
Preparation events use the hash-chained `run_dev_helpertransferpreparation` journal
outside the repository. Source and execution identities are checked before each
row. Caps cannot transfer; SDK retries stay zero.

Count, transport, billing, execution or cleanup uncertainty stops all remaining
tasks. Bound-input/runtime drift and unknown terminal states also stop the batch.
A settled failure or task-local resource cap may end just that row after receipts
are checked. The external stop rule distinguishes known accounting from permission
to continue, checks count-to-dispatch links without rejecting an ordinary output
ceiling adjustment, and retains pending probe/action uncertainty. A partial call
trace is insufficient observation, not automatically uncertain process execution.

For each task, report original acquisition and comparable candidate verification,
actual target processing, current-diff public checks, normal `finish_task`, patch
delivery, isolated task acceptance and safety separately. Also record request
validity, offered/selected inspection and observation, responses/cost before the
first edit, natural correction/revision, and settled cost/time. Feedback delivery
and use require public trajectory review; a raw error event alone is not proof.
If no natural helper or repair failure occurs, record the corresponding mechanism
as NOT_EXERCISED. Environment smoke results are never injected into solver context.

Success requires the complete original-to-submission chain and separate isolated
acceptance/safety PASS. Three successes would support operation on these three
selected tasks, not generalization or a causal improvement over another agent.
If the same harness stage repeatedly fails, investigate that reusable mechanism
before adding task-specific instructions. If requests and evidence are valid but
a patch fails, inspect its repair hypothesis. Budget exhaustion alone does not
justify larger limits. Do not tune or rerun within this allocation.

## Local evidence and limits

- All three new dependency descriptors and installed inventories verified. Existing
  source/lock/wheel bytes were preserved; no network downloads or provider calls.
- Three ordinary public library operations and three registered selected-test
  invocations passed in **71.881 seconds**. This checks capability, not the reported
  bug, full public regression coverage or repair acceptance. The bounded check
  script initially stopped on a missing loader argument before target execution;
  the argument was corrected before these six executions.
- Three actual normal-run first requests passed an offline synthetic count/stop
  audit: empty diff, only NOT_RUN public regression, no prior observations/source
  spans, shared v11 helper guidance and identical counted/dispatched input/tools.
  Network, credentials, actual provider/count, target and evaluator were blocked.
  Live token fit remains NOT_MEASURED.
- External batch receipt checks: **17 PASS in 0.095 seconds**, including normal
  task failures/caps, incomplete provider/probe receipts, malformed usage, count
  mismatch, cleanup uncertainty and allowed output-only adjustment. A local cap
  type mismatch was caught and corrected before final validation.
- Ruff and sealed-command preflight PASS. Runtime remains unchanged; earlier
  161 focused/855 quick PASS (including isolated mock evaluation) are not new tests
  of these tasks. No paid solve or isolated repair evaluation has run for this plan.

Evidence: `environment-checks.json`, `audits/*-first-request.json`,
`batch-safety-tests-final.json`, `local-validation.json`, dependency
`preparation-result.json`, and the preparation journal under the external plan root.

The plan preserves the runtime instead of adding a new rule. Whether the selected
tasks reach the full verified completion path remains the next unresolved question.
