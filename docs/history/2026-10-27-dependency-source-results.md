# Registered caller source trial: diagnosis reached, first edit still absent

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: approved execution, monitoring and public-evidence audit
- Origin Date: 2026-10-27
- Verification Status: LIVE EXECUTED; original failure observed; repair NOT_ACHIEVED;
  final public/isolated checks NOT_RUN; last provider usage UNKNOWN
- Implementation: `a4c1c61a`; execution commit: `42a0f515`
- [Sealed plan](2026-10-27-dependency-source-plan.md), user approved R1 once / $1.20

## Question and reason

The preceding trial could not switch from repository search to available caller
dependency source. This single trial tested whether explicit dependency scopes in
ordinary read/search would lead to source acquisition, execution diagnosis and a
first repair. The same development-exposed saved candidate, initial public
feedback, complete Astroid source, model and resource limits were retained.
The interface intervention is opt-in; no operator repair hint or private evaluator
material entered the model request.

## Execution and integrity

The user explicitly approved manifest
`sha256:4ee44611c691ea5e7701546c7c1005da3905f5a84f8fd6a2111af4d202a61c84`.
The manifest was revalidated, the result root was absent, and approval was recorded
in `C:/pt/dependency-source-plan-v1/approval.json` plus a hash-chained journal.
The exact `run.ps1` executed once. Its collector exited zero after recording a
controlled uncertain terminal; shell exit zero is not experiment success.

Task: Astroid-1333 `dev-train/current-dev20/13`, official=false; R1 once;
`gpt-5.4-mini-2026-03-17` xhigh; repository `.env`; $1.20 cap. Input 60K,
output 40K/25K, normal 16/correction 1, tools 24, helpers 2, original selection 1,
additional edits 3, shared model/intermediate-check 600s. Final public and isolated
verification retain their separate 390s limits. No retries, image pull/build or
additional trial was performed. User-owned `AGENTS.md` edits were preserved.

## Observed sequence

| Response | Observed action or result |
| --- | --- |
| 5 | Two `dependency:pylint` searches returned registered caller source. |
| 6 | Read all 139 lines of `pylint/lint/expand_modules.py`, untruncated, with pinned file/version provenance. |
| 10 | Selected `recheck_original`; host ran unchanged base and saved candidate. F0010 remained with matching call conditions and unchanged control output. |
| 14 | Executed a helper comparing search roots. Absolute cwd produced `['src', 'project']`; `'.'` produced `ImportError`. The helper passed with exit 0 and untruncated output. |
| 15 | With `replace_text` and `stop_task` offered, used 40,000 output tokens in 269.381s, produced no tool call, and returned `incomplete_response`. |
| Correction | Input was compacted/recounted to 56,323; a 25K-ceiling call started but had no completion or usage receipt. Terminal: `PROVIDER_UNCERTAIN`. |

The helper result concerns its reduced entry point and setup. It is diagnostic
evidence, not proof that a repair fixes the original caller. There was no new edit,
so the final diff remains the saved seed
`sha256:93b024b3f11ef89311d9cbf5a06a56328b14f7b7d7687746e6d24a8b9fb8e3e5`.
There is no failed-feedback revision to assess after a new mutation.

## Counts, costs and context

- Input-count requests: 20 started / 20 completed. Provider calls: 16 started /
  15 settled. The unsettled call is the single correction.
- Model actions: 20 completed, comprising 5 reads, 13 searches, 1 original selection
  and 1 helper; no failed tool action and 0 edits. Two host source-preload reads are
  additional, for 22 action receipts in the model journal. Dependency use itself
  was 3 searches and 1 read. Host original executions: 2; helper executions: 1.
- Four context boundaries recovered from 60,823/62,222/68,487/96,137 counted input
  tokens to 57,103/56,247/56,308/56,323. No budget or deadline reset occurred.
  Previously read dependency source remained separately present in the handoffs.
- Settled output total: 66,324 tokens; the final normal response alone used 40,000.
- **Confirmed cost: $0.49747575 for 15 settled calls.** This is not the final total
  charged amount: correction usage and billing remain unknown. The authorized
  allocation is closed and its remaining nominal balance cannot fund a repeat.
- Model/intermediate-check phase: 535.162s. Final public controls/regression and
  isolated acceptance: `NOT_RUN`, because no new candidate was produced and the
  uncertain terminal stopped further work.

## What caused the final stop, and what remains uncertain

The observed normal failure is output exhaustion while constructing the first
mutation/stop request. Caller source acquisition and diagnostic execution had
already succeeded. It is not supported to blame an inability to access Pylint or
an unrecoverable input overflow for that final failure. The financial cap was not
the recorded terminal condition either.

The correction had a nominal 25K output allowance but little executable time.
`model_timeout` reserves 60s for a new-diff original recheck plus 5s whenever an edit
is offered. With the baseline already available, that is 65s. Correction dispatch
occurred 528.975s after stage readiness, leaving roughly 71s total and 6s for the
provider after that reserve. Termination occurred 6.187s later, at approximately
600-65s from stage readiness. This strongly fits a timeout at the reserved-time
boundary. However, the collector catches an untyped provider exception without
recording its class, so the precise exception cannot be established from evidence.
Do not claim that the correction consumed 25K tokens: no receipt says so.

The outcome changes the next investigation from caller-source access to converting
obtained diagnostic evidence into a bounded edit and giving correction a usable
time allowance. Reading and execution are now demonstrated in this case; repair
is not. The trace does not reveal why the model spent 40K tokens without a tool call.
Request construction, task uncertainty and model behavior remain alternatives.
Investigate the public edit request/context and time admission before prescribing
more output tokens or automatically rerunning. No such follow-up was executed.

This is one assisted saved-candidate trial, not a concurrent A/B control, fresh
solve or general quality estimate. The historical contrast supports capability
uptake but cannot isolate which interface element caused the changed behavior.

## Evidence and checks

- Result: `C:/pt/dependency-source-run-v1/result.json`
- Public model journal: `C:/pt/dependency-source-run-v1/R1/runs/run_dev_feedbacksourcemodel.jsonl`
- Separate public audit: `C:/pt/dependency-source-analysis-v1/public-analysis.json`
- Audit script: `C:/pt/dependency-source-audit-v1.py`; no provider or target calls
- Result hash: `sha256:540984b9548df38bd9d6427e304b1266f8e7e125109382acc030b55c0ec4c361`
- Model journal hash: `sha256:097cb3c208b9a8f39ad011fbeccf823dc9752bc30bae2ced04e4f4503664acf4`

The audit verified journal chains, request artifact identities, action/settlement
counts and cost sums. A separate read-only agent reached the same public findings;
it is a corroborating audit, not an independent experimental sample. Opaque model
reasoning and private evaluation material were not inspected. Runtime code stayed
unchanged during execution and analysis. Documentation validation: 5 PASS/0.19s;
whitespace check PASS. No unchanged runtime suite was repeated.
