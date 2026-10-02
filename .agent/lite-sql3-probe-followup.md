# Lite SQLFluff three-task probe follow-up

Prepared 2026-10-02. Status: **public readiness checked; paid approval pending**.
Operator plan only, never coding-agent context. This is a new allocation; the
[closed dev20 batch](swebench-lite-dev20-batch.md) stays closed with its original results.

## Question and comparison

Does making public dependencies and plugin metadata available let the agent obtain
useful reproduction evidence, correct its own probe/API errors, and produce better
repairs? The three tasks were selected because their requested probes failed before
behavior execution, not because a new repair is known to pass. The historical
baseline submitted all three but resolved zero under original hidden evaluation.

Use fresh workspaces and no prior patches, notes, trajectories, operator diagnostic
programs or evaluator results. Keep the original task packages and prepared public
source byte-identical. Attach only each task's prepared public dependency descriptor.
Model, prompt policies, completion gates and budgets stay unchanged. The resulting
generic tool/environment description and profile identity necessarily differ.

This is a historical before/after development diagnostic, not a randomized paired
estimate. One new sample per task cannot isolate stochastic model variation or
establish general accuracy. Operator exposure is disclosed; no hidden-derived repair
advice enters the solver. Do not reinterpret this as another three successes/failures
to append to the original 20-task denominator.

Fixed order and dependencies (under `C:/pt/analyses/lite-probe-support-20261002-v1`):

| Order | Registered dev-train instance | Dependency descriptor |
| --- | --- | --- |
| 1 | sqlfluff__sqlfluff-1517 | dependencies-16/prepared-probe-dependencies.json |
| 2 | sqlfluff__sqlfluff-1625 | dependencies-17/prepared-probe-dependencies.json |
| 3 | sqlfluff__sqlfluff-1733 | dependencies-18/prepared-probe-dependencies.json |

These are clean Python 3.12 public wheel bundles with `src` snapshots, literal
plugin metadata and explicit operator `setuptools==80.9.0` compatibility support.
They do not reproduce the Python 3.9 evaluator environment exactly. Existing
registered checks and original hidden grading remain unchanged.

Provider-free readiness: all three isolated public import/plugin/basic-parse
canaries passed. Fourteen driver controls and five documentation checks passed;
the installed original harness is version 5.0.2 with its source identity recorded.
Controls cover request differences, approval/CI gates, one-shot execution and
uncertainty/cap stops. Evidence is `canaries.json` and `controls-pass.xml` below.
These checks establish readiness, not improved repairs. The final committed-head
receipt is generated separately before any execution approval is requested.

## Proposed paid scope

- Model `gpt-5.4-mini-2026-03-17`, `xhigh`, 25,000 desired output tokens.
- Credential `C:/Users/geonj/Documents/PatchLoop/.env`; exact key read locally and
  never printed, hashed into evidence, or supplied to evaluator subprocesses.
- One fresh sequential solve each; no resume, retry, replacement or extra samples.
- USD 1.20 per task, USD 3.60 invocation-wide ceiling; no budget transfer.
- Per task: 40 model calls, 100 actions, four accepted edits, 1,800 seconds.
- Same `segmented-v1`, `result-or-size-v1`, `brief-v1`, probes enabled/policy `none`,
  repair recheck, `protected-v1`, `per-call-v1` admission. Exact input counting and
  zero SDK retries remain mandatory. The cap is a ceiling, not a price forecast.
- No source/image/dependency downloads, builds, benchmark test-split runs or merges
  are included. Reuse prepared sources, local images and frozen dependency bundles.

## Gates and stop rules

Evidence/drivers: `C:/pt/analyses/lite-sql3-registration-20261002-v1`.
`manifest.json` binds the three task/source/native-row/dependency identities.
`preflight.json` is written at the committed execution head, binding runtime,
requests, driver hashes, installed original-harness identity and local probe/image
preflight. Only the intentional dependency binding and new state roots differ from
the historical requests. `batch.py` without arguments performs no provider calls.

After explicit approval, an operator records the actual human message in
`authorization.json`, bound to the frozen manifest, head, repeat count and cap.
Only then may `batch.py --execute` proceed, after live exact-head Ubuntu and Windows
`fast-dev-head` SUCCESS and no failed current check. It rechecks the remote branch,
local HEAD and frozen receipt. Never create an approval file from this plan alone.

Fresh live roots: `C:/pt/lp3live01/1` through `/3`; native evaluation output:
`C:/pt/lp3native01`. No invocation may restart once its durable start is recorded,
even if it produced no settled result. Keep the process/log reference when launched.
A settled agent failure or cap exhaustion is a result, not permission to repeat.
Stop further dispatch on counting/transport/billing uncertainty, head/source/image/
dependency drift, evaluator infrastructure errors or uncertain cleanup. Preserve
unstarted tasks as NOT_RUN and settled cost; unknown cost is never zero.

After a settled batch with submissions, operator-only `evaluate.py` may run once
against the installed pinned SWE-bench 5.0.2 harness and existing original images.
Compare every submitted original-native verdict with registered evaluation. Missing
evaluation or disagreement stops follow-up; never feed hidden output to the solver.

## Measurements and interpretation

Record per task: attempted/completed/submitted/original-resolved, public regression,
safety, missing work, model calls, cost and wall time. From public action traces,
record whether probes execute real task behavior, whether the agent repairs invalid
API calls, and whether it repeats the reported case after the final edit. Process
exit zero, probe count and successful submission alone are not repair success.

More original-resolved tasks without new public/safety regressions is a promising
local signal only. If correct repairs coincide with useful pre/post-edit evidence,
the mechanism has descriptive support. If probes run but repairs remain incorrect,
investigate interpretation or repair ownership rather than expanding dependencies.
If the agent does not use probes, or uses incorrect programs, the causal question
remains unresolved; do not automatically add mandatory probes or increase budget.
Regardless of result, close this allocation and add a separate outcome record.
No additional paid work is authorized by success, failure or unused budget.
