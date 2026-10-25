# Run and validate

See [status](current-status.md) for baseline/questions, [guide](../.agent/guide.md)
for contracts and [history](history/README.md) for past evidence. Historical approvals
do not authorize current runs.

## State and temporary workspaces

All generated state belongs outside the repository. Use short Windows paths:

- `C:\pt\tmp\<short-id>`: disposable test workspaces, one per process.
- `C:\pt\validation\<unique-name>.xml`: retained reports outside test scratch.
- `C:\patchloop-state`: durable runs, artifacts and managed workspaces.

After tests and children exit, retain reports and recycle only that exact temporary
directory. Preserve failed-test scratch until diagnosis ends. Never sweep parents,
empty the Recycle Bin automatically or infer disposability from names. Preserve all
existing run, preparation, analysis and experiment bytes.

## Local verification

Run focused tests, Ruff, the fast suite and mock smoke as relevant. Keep focused
validation below two minutes. This test path needs no provider or Docker call.

```powershell
$testId = 't' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$testRoot = Join-Path 'C:\pt\tmp' $testId
$testReport = Join-Path 'C:\pt\validation' ($testId + '.xml')
New-Item -ItemType Directory -Force -Path 'C:\pt\tmp', 'C:\pt\validation' | Out-Null
uv sync --extra dev --locked
uv run ruff check patchloop tests
uv run --locked pytest tests -n 4 --dist loadfile --max-worker-restart 0 --durations=20 --basetemp $testRoot --junitxml $testReport
# After pytest and its children exit, recycle only $testRoot.
```

For focused checks select relevant files and omit `-n 4`. Freeze runtime while testing.
Full-suite workers keep files together, use separate basetemps and cannot restart.
Independent invocations need separate roots. Record commands, results and unexecuted
checks; old suite totals do not verify current changes.

CI: PRs/`main`, Windows/Linux Python 3.12, four file-grouped workers, task validation,
mock smoke and Ruff. Logs retain 20 slowest phases; JUnit persists 14 days even on failure.
`--locked` rejects lock drift. Parallelism preserves selection and Docker opt-in.

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

`--agent-policy thin --planning-policy none` selects the experimental
[thin interface](../.agent/thin-policy-reference.md). The default is `current`.
Policy choice binds the envelope, manifest and resume; it changes presentation,
not tool availability, source retention, verification gates or resource limits.
Local parity does not establish repair quality or authorize a paid comparison.

## Public-only repair

`patchloop repair --request request.json` accepts a separate public task, local Git
source and exact base commit, allowed paths, registered checks, explicit sandbox,
model and invocation-wide cost cap. See the [small example](../examples/repair/README.md).
OpenAI needs an existing digest-pinned image; mock uses trusted local checks.
The shared loop preserves costs, edit limits, tool restrictions and recovery.
`PATCH_READY` returns a patch plus public receipts, with acceptance `NOT_RUN`.
The public repair path currently has no probes, so its explicit delivery state is
`unverified_delivery`; this is not a verified repair claim.
It neither changes the original checkout nor applies/opens a PR for its patch.
No hidden/reference material is needed; `dev` admission remains unchanged.
Paid repair requires approval of this exact public request, credential, repeats and
cap. No provider call was used to implement or locally validate this path.

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
| History search | `none` |
| Repeat | 1, maximum 6 |
| Automatic compaction | Disabled |

Per-run defaults: 40 model calls, 100 tool actions, four accepted mutations and
1,800 active seconds. Output includes reasoning (128..128,000 desired tokens);
cost admission can lower it. Full GPT-5.4 requires `segmented-v1`.
See [CLI options](../patchloop/cli.py) and [request contracts](../patchloop/dev/contracts.py).

`--history-search public-v1` requires `segmented-v1` and the current agent policy.
It offers a singleton search of already delivered public evidence from this run,
including earlier segments. BM25 ranks execution data, excluding owned plans and
hypotheses. Eight candidates return whole originals within actual input limits.
If a fresh seed still exceeds those limits, reduce the new result to 48,000 chars;
never rewrite dispatched outputs. Authored fields and omissions are labelled;
no one-function limit. Fetch any returned ID
for its complete original; oversized records offer canonical JSON pages through
`offset`. Every fetch/page spends another ordinary action. A question can retain
a search result within its existing two references; it remains historical data.
It uses optional budget and grants no current source/check credit. Boundaries and
run/input limits stay unchanged. [Offline evidence](history/2026-10-20-history-question-delivery.md)
does not establish model uptake or better repairs; the selected baseline keeps it off.

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
contract and CLI compatibility checks first. Opt-in `--completion-cost-policy
completion-minimum-v1` requires segmented-v1: retain recovery slots and reserve
successful minimum check/finish successors before dispatch. `completion-recovery-v1`
reserves one model slot and one correction at 60K input + output allowance. Set
`--max-correction-output-tokens 25000` independently of `--max-output-tokens 40000`;
omitting it preserves the coupled ceiling. The first correction consumes it;
restart cannot renew it. No repair guarantee; see the [contract](../.agent/completion-resources.md).
Reusable probe cases have a separate
[case contract](../.agent/probe-cases.md). Optional `--probe-recheck saved-program-v1`
requires enabled probes and `cases-v1`; it reruns the last saved program after edits
within existing budgets and never gates submission. Defaults remain off; see the
[recheck contract](../.agent/probe-recheck.md). Compaction needs a compatible mini
configuration and conditional model-limit reservation acknowledgement; it is not
part of the selected baseline. Repeat every selected option on resume. Interface
availability and local tests alone do not demonstrate an acceptance improvement.

## Submission, evidence and interpretation

Public task `test_suites` can expose `run_tests` for 1–8 tracked public Python test
files or pytest node IDs. The registration owns the command, environment and
sandbox limits; the model cannot supply command flags. See the
[selection contract](../.agent/selected-tests.md). Results bind the executed diff
and remain optional: they supply no required-check credit. Missing nodes,
collection errors and incomplete execution do not establish behavior correctness.

Registered tools never expose unrestricted shell. `finish_task` needs a non-empty
tracked diff, no untracked files, all required checks passing on that diff, and an
assessment (1–1,500 characters) connecting evidence to requirements and remaining
gaps. Resolve material gaps when feasible; edits require fresh checks. Regression
PASS, notes and probes do not establish task coverage or replace required checks.
Finish replays stale original cases and controls with deterministic action IDs,
within the solver budget and without another model call. Current mismatch/conflict
rejects finish. `stop_task` abandons without submission/evaluation.

`--enable-probes --reproduction-acquisition bounded-v1` permits two original dispatches,
two rejected requests and six total investigations before edits; requests are not
executions. Completion budgets can release it earlier (default `none`). Release or
helper/normal PASS cannot discharge the obligation. Caller receipts bind sys.argv,
arguments, cwd and selected
input/environment identities. See the [contract](../.agent/evidence-recovery.md).
Fresh original purposes bind distinct failure/desired JSON values. Acquisition needs
a healthy unchanged-base failure match and desired mismatch. Third values stay
unverified; mapping remains model-authored. Rejected requests create no case; accepted
uncertain executions remain unverified.

Finish, repair receipts and dev results expose `delivery_state`, `original_verification`
and `submission_verification`. An unchanged-base failure plus current case support
permits `cases_verified_delivery`; missing/incomplete evidence returns
`unverified_delivery`. These judge selected cases, not semantic requirement coverage.
Independent acceptance remains separate, even if PASS follows an unverified delivery.

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

A completed probe uses ordinary replay. A fresh durable backend return resumes
postprocessing without another execution. A dispatch without that receipt stops
with execution uncertainty; it is never automatically repeated.
