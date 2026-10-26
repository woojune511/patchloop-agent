# Trace-budget live pilot: proposed fresh solve

Status: PREDECLARED; paid execution not authorized. Current local readiness is
recorded in the external request and preparation receipts.
All earlier paid allocations remain closed. official=false; claim-ineligible.

## Question and reason

The [last live pilot](2026-10-26-first-repair-live.md) acquired F0010 and made one
edit, but both path observations were truncated and the edit did not fix the
original call. The [collector correction](2026-10-26-trace-budget.md) returned
complete observations on two saved calls with identical captured output. Local
replays establish collection behavior, not model uptake or repair effectiveness.

Does the real model use complete original-call observations to choose or revise
its repair hypothesis, remove F0010 and preserve the clean control? This is one
fresh solve on an exposed dev-train task, not a causal A/B estimate or general
quality measurement. No saved patch, operator diagnosis or fixed original program
is seeded into the solver.
The model chooses its new probe and functions; fixed request settings do not
imply byte-identical caller programs across these two fresh runs.

## Exact proposed scope

- Task: `tasks/dev-train/current-dev20/13/public.yaml`, Astroid-1333.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh. Credential file:
  `C:/Users/geonj/Documents/PatchLoop/.env`; preparation checks its path only.
- Repeat 1; positive invocation-wide maximum **USD 1.20**. Normal output ceiling
  40,000; existing one correction allowance capped at 25,000. Exact cost admission
  may reduce an output ceiling; these are maxima, not guaranteed output capacity.
- 40 model calls, 100 actions, four accepted edits, 1,800 active seconds;
  1,920-second operator supervision. Input/context settings unchanged.
- Segmented-v1, result-or-size-v1, brief-v1, probes enabled/policy none,
  repair-recheck, protected-v1 inspection, bounded-v1 reproduction acquisition,
  completion-recovery-v1. The run_probe recommendation stays enabled.
- Same prepared source/dependencies and local image digests as the previous
  pilot. Same two frozen public post-submission checks share 120 seconds; skip
  them without a submitted patch. Registered isolated evaluation remains separate.
- Implementation commit `2c54996951b69e6d493e0522895a70c8404e2358`;
  runtime `sha256:207d9b9e81ec10b3e013e7028520366d3103c2dea59a289307fba700b5125dda`.
  The final request binds the preparation commit and current source inventory.
- Only the trace-budget/whole-call-diagnosis implementation and fresh state change
  from the previous live request. The changed probe profile binds the new wrapper;
  images, resources, tool limits and public post-submission check programs stay fixed.

Preparation root: `C:/pt/trace-budget-live-ready-v1`.
Proposed execution root: `C:/pt/trace-budget-live-v1`.
Immutable request/command/script hashes and the preparation journal define the
reviewable scope. New authorization must bind that request before dispatch.

```powershell
uv run --locked --offline python C:/pt/trace-budget-live-ready-v1/supervisor.py
uv run --locked --offline python C:/pt/trace-budget-live-ready-v1/assess_submission.py
```

## Measurements and decision

1. Acquire the unchanged-base failure with a distinct clean control and consistent
   host judgment. Record frozen arguments, cwd, environment, fixture and output.
   Same-call identity is separate from equivalence to the issue's `cd root_dir;
   pylint src/project` steps. Review that mapping from public evidence; do not
   silently rewrite an acquired call or count absent equivalence as established.
2. Separate observation offered, selected, constructed, rejected, dispatched,
   returned and delivered. For every trace, retain scope, coverage status,
   call/selected-event counts, coalesced/omitted detail and exhausted counters.
   Complete coverage with sampled values is distinct from incomplete coverage.
3. Review selected-function entry/line/return/exception counts and premise verdicts.
   Return/exception trace events do not imply normal return or escaped exception.
   Unknown is insufficient, never no-hit. Missing detail is not missing execution.
4. Link the first and later accepted edits to their current observation receipt.
   Inspect explicit hypotheses, public source changes and next delivered state for
   semantic uptake; an ID link alone is not evidence that the model used the result.
   If a failed edit triggers diagnosis, measure fresh whole-call scope and whether
   the subsequent hypothesis addresses the observed path. Do not force a trigger.
5. Assess current-diff original F0010 removal and control preservation separately
   from visible checks, submission, frozen public checks, task acceptance and safety.
   Complete collection alone is a mechanism result, never successful repair.
6. Record actual tokens, model/tool/edit counts, cost, elapsed time, correction
   reasons and the first unmet stage. Distinguish NOT_OFFERED, NOT_SELECTED,
   INCOMPLETE, COMPLETE_UNUSED, REPAIR_FAILED and verified outcomes from receipts.

No observation tests no collection effect. Complete useful evidence followed by
another ineffective repair weakens the explanation that collection was the main
remaining obstacle. A failure after useful uptake points to a different mechanism;
it does not authorize another run. A success remains one development example.

## Readiness and boundaries

Reuse completed local validation: short owner 111 PASS/8.39 s, quick 374 PASS/34.58 s,
Ruff PASS and two frozen-call collector replays. Run only read-only prerequisites
and small collection-script controls for this proposal; no redundant runtime suite.
Check tracked runtime/task bytes, prepared source/dependencies, existing local
images, credential path and frozen public-check hashes. Stub the runner to verify
the CLI/request match. Provider access remains untested until authorized dispatch.

Count actual input immediately before dispatch, zero SDK retries, stop all work on
count/transport/billing/cleanup/source uncertainty. No automatic retry, resume,
replacement, limit increase, Docker Desktop launch or image pull/build. Public
solver inputs cannot include private checks, reference patches or evaluator output.
State remains external and hash-chained; preserve historical and user-owned bytes.
An exact new task/model/credential/repeat/cap approval is still required.
