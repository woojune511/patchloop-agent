# Processing-evidence pilot: request construction stopped before reproduction

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: approved one-run execution and public receipt audit
- Origin Date: 2026-10-28 KST
- Verification Status: LIVE_EXECUTED / INCOMPLETE_RESPONSE
- Runtime commit: `4b9b9b20`; preparation commit: `c07cfa69`
- official=false; claim-ineligible; allocation CLOSED

## Question, authorization and scope

The user approved the [sealed plan](2026-10-28-processing-evidence-fresh-plan.md),
manifest `sha256:1020afc8af054ea026dfda97107ba8bc88007514cf443a6ec794e5fff77512ee`,
for one clean-start Astroid-1333 run (`dev-train/current-dev20/13`),
`gpt-5.4-mini-2026-03-17` xhigh, repository `.env`, total USD 4.50.
Total responses 20 including one correction, tools 40, edits 3, input 60K,
output 40K/25K and 2,400 seconds including 390 for evaluation stayed fixed.
All six provider responses reported the requested model snapshot.

The question was whether the model would select joint failure/processing evidence,
repair F0010 and complete normal public and isolated verification under v7. No
prior patch, observations, target-specific witness or answer hint was injected.
The [previous v6 run](2026-10-28-canonical-diagnostic-fresh-results.md) is operator
comparison context only. This one trajectory cannot isolate the three bundled
runtime interventions or establish repair-rate improvement.

## Observed outcome

| Component | Result |
|---|---|
| Terminal | INCOMPLETE_RESPONSE: max_output_tokens |
| Preparation | Three search_files and three read_file actions, all succeeded |
| Original target calls / helpers | 0 / 0 |
| Accepted edits / public checks / finish | 0 / 0 / 0 |
| Isolated acceptance / scope / safety | NOT_RUN / NOT_RUN / NOT_RUN |
| Cost | USD 0.40966830 / 4.50, all usage settled |
| Active duration | 552.214 seconds (9m12s) |
| Model / exact-count / tool calls | 6 / 6 / 6 |
| Protocol correction | One, consumed after the first incomplete response |
| Retry / operator repair / synthetic submission | None |

The first four responses inspected file-loading and module-resolution source.
After six preparation actions, acquisition became request-only: the fifth request
offered an original-requirement `run_probe` or `stop_task`. No target execution had
yet occurred.

| Response | Input | Output | Reported reasoning output | Observed shape |
|---|---:|---:|---:|---|
| First original-request attempt | 29,270 | 40,000 | 39,753 | reasoning + partial function_call; no accepted tool call |
| Sole correction | 15,948 | 25,000 | 25,000 | reasoning only; no accepted tool call |

Both responses ended `incomplete/max_output_tokens`. The smaller second input
followed the existing encrypted-item-size context transition. It did not produce
an executable request. Reasoning **counts** and public request metadata were read;
encrypted continuation and private reasoning contents were not read or interpreted.

Neither input reached the 60K context ceiling. The invocation-wide money, total
time and model/tool limits remained available. The immediate termination mechanism
was consecutive per-response output exhaustion and a spent correction allowance.
It was not target/probe execution failure, transport uncertainty or hidden-test failure.

## What this supports and leaves unresolved

This run identifies request construction before first reproduction as the current
operational bottleneck. The request required public caller/fixture/environment,
bounded Python code, distinct failure/desired observations and same-call role
declarations in one tool call. Additional request-construction burden and the
model/reasoning configuration are plausible explanations; this single run cannot
establish that the role fields caused the exhaustion or that a larger cap would help.

The processing conjunction, no-op rejection and subsequent revision,
fixture/output comparability and pre-target obligation distinction are all
NOT_EXERCISED. No F0010 repair occurred, and there is no task-acceptance result.
Local mechanism tests remain valid evidence at their own scope; this live failure
does not test their runtime correctness or demonstrate model uptake.

The decision is to close this allocation and retain the implementation without
claiming a live repair gain. Diagnose the smallest first-request construction
burden versus model-setting question before proposing another paid run. Increasing
the global cost/context limits is not supported by the observed failure. Do not
manufacture a candidate failure, inject a fix, or retry using unused money.

## Evidence and closeout

- Plan root: `C:/pt/processing-evidence-fresh-plan-v1`, including exact approval,
  preflight, hash-chained preparation journal and unchanged one-shot entry.
- Run: `run_dev_3e21775752a54cae`, root `C:/pt/processing-evidence-fresh-run-v1`.
- `collection.json`: ordinary runner result; `analysis.json`: public outcome and
  accounting audit; `request-audit.json`: separate read-only request analysis.
- Runtime hash: `sha256:1efe175d82fa407d1d91c144dfb9082f82e9052e3199bf0c224f563eaaeafca5`.

All provider, input-count and action starts have matching completions. Summed
provider cost equals both terminal and collection cost; every exact input count
matches reported usage. Totals: input 114,132 (cached 23,424), output 75,529,
reported reasoning output 73,753. Both journal chains validate. No evaluator data
was read, no runtime source changed during execution, no image was pulled/built,
and no invocation was retried. The launch returned normally with the negative
terminal and closed the authorized once-only allocation.
