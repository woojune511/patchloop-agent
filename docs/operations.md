# Run and validate

Current operating instructions for `dev-head`. Read [current status](current-status.md)
for the selected baseline and open question. Read only the relevant
[internal guide](../.agent/guide.md) section for implementation contracts.
Past commands, approvals, results and diagnostic narratives are searchable through
[the history index](history/README.md); they are not current run authorization.

## State and temporary workspaces

All generated state belongs outside the repository. Use short Windows paths:

- `C:\pt\tmp\<unique-name>`: disposable test workspaces, one per process.
- `C:\pt\validation\<unique-name>.xml`: retained reports outside test scratch.
- `C:\patchloop-state`: durable runs, artifacts and managed workspaces.

After a test process and its children exit, retain its report and recycle only its
exact temporary directory. Keep failed-test scratch while diagnosis needs it.
Do not sweep a parent directory, empty the Recycle Bin automatically, or infer
disposability from names such as `test` or `tmp`. Preserve existing run, preparation,
analysis and experiment paths and bytes.

## Local verification

Run focused tests, Ruff, the fast suite and mock smoke as relevant. Keep focused
validation below two minutes. This test path needs no provider or Docker call.

```powershell
$testId = 'pytest-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$testRoot = Join-Path 'C:\pt\tmp' $testId
$testReport = Join-Path 'C:\pt\validation' ($testId + '.xml')
New-Item -ItemType Directory -Force -Path 'C:\pt\tmp', 'C:\pt\validation' | Out-Null
uv sync --extra dev --locked
uv run ruff check patchloop tests
uv run pytest tests -p no:cacheprovider --basetemp $testRoot --junitxml $testReport
# After pytest and its children exit, recycle only $testRoot.
```

Replace `tests` with relevant files for focused validation. Keep runtime bytes
unchanged while tests run. Parallel processes need fresh, separate basetemps and
disjoint file selections. Record commands, results, reports and unexecuted checks;
old suite totals do not verify a current change.

## Mock end-to-end

```powershell
$env:PATCHLOOP_STATE_ROOT = 'C:\patchloop-state'
uv run patchloop dev `
  --provider mock `
  --task tasks/smoke/csv-quoted-newline/public.yaml `
  --model mock-dev `
  --repeat 1
```

Mock mode forbids credential and cost options. The smoke path covers public
inspection, mutation, visible checking, submission and isolated evaluation.
It remains `official=false` and is not live provider or Docker evidence.

## Explicitly approved live development

A live invocation needs the exact checked-in `dev-train` task, model, credential
file, repeat count and positive invocation-wide cap authorized by the user.
A documentation example, local PASS or remaining budget grants no additional run,
retry or resume. Choose a bounded comparison only for a concrete causal question.

Read-only prerequisite checks:

```powershell
$env:PATCHLOOP_STATE_ROOT = 'C:\patchloop-state'
uv run patchloop doctor
uv run patchloop task validate tasks/dev-train/<task>
```

`doctor` inspects prerequisites without starting Docker or acquiring images.
Task validation is an operator check; private task material and evaluator details
must never enter coding-agent context.

For the selected GPT-5.4 xhigh baseline, fill in the exact approved task, credential
file and cap before execution:

```powershell
uv run patchloop dev `
  --provider openai `
  --task tasks/dev-train/<task>/public.yaml `
  --model gpt-5.4-2026-03-05 `
  --reasoning-effort xhigh `
  --max-output-tokens 25000 `
  --context-policy segmented-v1 `
  --segment-boundary-policy result-or-size-v1 `
  --planning-policy brief-v1 `
  --enable-probes `
  --probe-policy none `
  --repair-recheck `
  --repair-inspection-policy protected-v1 `
  --completion-cost-policy per-call-v1 `
  --env-file <credential-file> `
  --max-cost-usd <positive-decimal> `
  --repeat 1
```

The selected baseline is a working configuration, not a change to CLI defaults:

| Setting | CLI default |
| --- | --- |
| Provider, task, model | Required explicit values |
| Reasoning / desired output | `medium` / 25,000 tokens |
| Context / segment boundary | `append-v1` / `result-or-size-v1` |
| Planning | `none` |
| Probes / probe policy | Disabled / `none` |
| Repair recheck / inspection | Disabled / `protected-v1` |
| Completion cost | `per-call-v1` |
| Repeat | 1, maximum 6 |
| Automatic compaction | Disabled |

Per-run defaults: 40 model calls, 100 tool actions, four accepted mutations and
1,800 active seconds. Output includes reasoning (128..128,000 desired tokens);
cost admission can lower it. Full GPT-5.4 requires `segmented-v1`.
See [CLI options](../patchloop/cli.py) and [request contracts](../patchloop/dev/contracts.py).

Before dispatch:

- Active runtime/lock inputs and the selected task package must be tracked and
  HEAD-clean. Unrelated edits outside these pathspecs do not block preflight.
- The credential file contains only one `OPENAI_API_KEY=...` assignment and must
  remain untracked. The SDK receives it directly; task subprocesses do not.
- The evaluator image must already be local at the required digest. Enabled probes
  also require the separate clean Python image and trusted wrapper. Never start
  Docker Desktop or pull/build an image automatically; no evaluator-image fallback.
- Confirm current applicable pricing before a paid comparison. Unknown model
  pricing fails closed. Exact input counting happens immediately before dispatch;
  one ledger covers every repetition under the invocation-wide cap.
- SDK transport retries stay zero. Count, transport, billing, process-cleanup or
  container-cleanup uncertainty stops remaining execution/repetitions. Do not
  reinterpret an uncertain dispatch as an unused sample or retry it.

The deadline covers preparation through evaluation. Interrupted Git descendant
cleanup remains uncertain after the direct process exits. After expiry, only
bounded metadata recovery and exact pending-mutation reconciliation may proceed.

## Optional preparation and policies

Prepare only what the selected task and diagnostic require; these interfaces do
not reopen historical experiment approvals.

`patchloop task prepare-source <task-dir> --output <new-external-directory>`
fetches the exact source once, verifies its tree/public bytes and publishes
`prepared-source.json`. Preparation uses a 120-second deadline with no provider
or Docker call. Pass `--prepared-source <descriptor>` to dev for independent
execution/evaluation workspaces. Missing, changed or mismatched preparation fails
without a remote fallback. Descriptors and source workspaces are durable evidence.

When probes need project dependencies, use:

```powershell
uv run patchloop task prepare-probe-dependencies <task-dir> `
  --prepared-source <prepared-source.json> `
  --wheel-lock <selection.json> `
  --output <new-external-directory>
```

With no source lock, `--resolve` can resolve supported static public dependencies
for Python 3.12/Linux. Preparation can download public wheels; execution uses only
verified local copies without network/install. Add `--enable-probes
--prepared-probe-dependencies <descriptor>` to the approved request. Read the
[dependency contract](../.agent/prepared-probe-dependencies.md) before preparation.

For other context, planning, cost or repair policies, read the relevant internal
contract and CLI compatibility checks first. Reusable probe cases have a separate
[case contract](../.agent/probe-cases.md). Compaction needs a compatible mini
configuration and conditional model-limit reservation acknowledgement; it is not
part of the selected baseline. Repeat every selected option on resume. Interface
availability and local tests alone do not demonstrate an acceptance improvement.

## Submission, evidence and interpretation

The coding agent receives registered public tools, never unrestricted shell access.
`finish_task` requires a non-empty current diff, every registered visible check
passing on that exact diff and no non-ignored untracked files. Historical PASS,
probe execution and notes do not provide current check credit. A diagnostic probe
does not replace a registered check. `stop_task` ends without submission/evaluation.

The content-addressed patch and manifest bind separate evaluation. Never return
private specs, hidden checks, reference patches or evaluator details to the agent.
`EVALUATOR_PASS` means task acceptance; safety is separate and
`claim_eligible=false`. Unexecuted evidence remains `NOT_RUN`.

Each run records an external append-only, hash-chained `dev-run-v1` JSONL stream
and content-addressed artifacts. Preserve its directory and original bytes.
Report implemented, locally tested, live-executed and claim-producing evidence
separately. Record completed results in history; update current status with only
the current decision, supporting evidence pointers and unresolved question.

## Resume an interrupted run

Resume requires an existing `dev-run-envelope-v1` and authorization covering that
recovery. Reissue the original command against the same state root, retain every
option and add `--resume-run-id run_dev_<id>` with `--repeat 1`.
Do not reconstruct it from a newer baseline example.

Provider, exact task/content, runtime bytes, model/reasoning/output target,
resolved credential-file identity, cap, limits, context/planning/cost/repair/probe
options, prepared-source/dependency bindings and sandbox identities must match the
stored envelope. A mismatch yields `RESUME_CONTRACT_MISMATCH` before a provider call
and leaves the journal unchanged. Pre-envelope runs cannot resume; no migration.

Recovery holds a run-lifetime lock and restores settled cost, counters and active
time; process downtime counts only toward run age. Durable actions replay by
`action_id + input_hash`, conflicting ID reuse fails, and pending mutations
reconcile instead of applying twice. Recorded decisions retain exact tool-policy
and call linkage. Missing, damaged or mismatched encrypted continuation ends at
`PROVIDER_CONTINUATION_ERROR`, with no stateless fallback. An unmatched dispatch is
never retried and becomes `PROVIDER_TIMEOUT_OR_UNKNOWN`.

A terminal resume returns its existing public result read-only. If evaluation
completion is already durable but the terminal is missing, receipt/patch/manifest
validation permits metadata-only completion, without loading credentials,
recreating workspaces, preflighting Docker or rerunning evaluation. Exact-envelope
and provider-uncertainty checks still apply.

A completed probe uses ordinary replay. An interrupted probe without a durable
result may rerun only after confirming cleanup of its exact owned container on
the same bound snapshot; that is isolated recovery, not an exactly-once guarantee.
Cleanup uncertainty stops execution.