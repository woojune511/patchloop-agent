# Planning OFF regression on three prior successful tasks

## Problem and hypothesis

Earlier selected-task comparisons gave a Pydantic-only OFF signal and an uncertain
first-plan timing result. Repeating the broad diagnosis about change/preservation
judgment did not identify a new useful mechanism. The next bounded question was
whether the existing `planning_policy=none` could preserve prior successful behavior
on other development tasks, supporting simplification of explicit planning.

## Fixed intervention and execution

No production code changed. A used brief-v1; B used none. This removes the explicit
planning instructions, annotation, state and review requests together. Internal
reasoning, bounded notes and registered tools remain available.

Fresh order: NA1, NB1, FB1, FA1, GA1, GB1. N is AnyIO v3, F is Fromager v1 and G is
pgmpy v1, each once per arm. Prior successes selected these tasks; old rows were not
controls and were not pooled with the new results. All runs are official=false.

The user authorized GPT-5.4-2026-03-05 xhigh, repeat=1 for each slot, $1.20 each and
$7.20 total. Segmented context, result-or-size boundaries, probes/probe-policy none,
repair-recheck, protected inspection, per-call cost admission and 40/100/4/1,800-second
limits stayed fixed. Prepared sources, dependencies and existing images were reused.
Each solve started from an independent clean workspace with no earlier candidate or notes.

The wrapper reused run_dev, actual-request recording, public-input verification,
settled-usage auditing and group accounting. No retries, replacement samples,
automatic resume or remaining-budget extension were permitted. The frozen HEAD was
45959c7f and runtime hash was `9320c697313e8340762a3fe48eb8717ef547e95a3696354d7fdad9d90d9935c6`.

## Results

| Task | ON acceptance / calls / cost | OFF acceptance / calls / cost |
| --- | --- | --- |
| AnyIO v3 | NOT_RUN / 14 / $1.1760960 | PASS / 9 / $0.7345315 |
| Fromager v1 | PASS / 5 / $0.3182045 | PASS / 5 / $0.2818270 |
| pgmpy v1 | PASS / 6 / $0.3415430 | PASS / 8 / $0.3313860 |

ON acceptance was 2/3 planned, OFF 3/3. All six started; five submitted and passed
acceptance and safety. AnyIO ON never submitted, so acceptance and safety are NOT_RUN,
not FAIL. No uncertainty stopped the group. Both recorded probe timeouts had confirmed
cleanup and remain separate from infrastructure-stop counts.

Recorded cost was $3.183588; the unused $4.016412 is closed. Cache-neutral conversion
was $4.212900. A/B recorded costs were $1.8358435/$1.3477445 and cache-neutral values
$2.4328675/$1.7800325. These are usage-based standard-rate records, not invoice or
credit claims. Collection took 1,801.159 seconds, excluding preparation and analysis.

## Public behavior evidence

AnyIO ON performed ten source actions in ten model responses, editing on call 11.
Its injected-cancellation counter condition passed the interrupt cases but failed
the public explicit_cancel fixture task/context preservation case. A post-failure
probe timed out without observations. The last response exhausted a reduced 2,758
output ceiling and was followed by COST_CAP_REACHED, before repair or submission.

OFF performed eleven source actions in four responses and edited on call 6, after
its own pre-edit probe also timed out. It used the observed pending-future/runner-loop
relationship to keep the shared runner reusable after aborting a call. The first
candidate passed lifecycle 7 and upstream 32 checks, then acceptance. Reading volume,
batching, code and recovery budget differed; this does not isolate planning's effect
on applicability judgment. Neither probe supplied behavioral confirmation.

Both Fromager arms read the relevant file once and edited on call 2. Their local
worklists removed descendants only after losing the last parent, preserving surviving
parent/ROOT references. Both passed public 5 and upstream 12 checks and submitted on
call 5. No separate case discovery or behavior improvement was demonstrated.

Both pgmpy arms used a graph snapshot inside each stable conditioning round, preserving
refresh between rounds. OFF additionally inspected round progression and the separator
helper, editing on call 5 versus ON's call 3. Both passed public 12 and upstream 7 checks.
OFF used more calls and had a higher cache-neutral cost on this task. It is not uniformly
faster or cheaper. All six applied one edit; rejected duplicate edits were zero.

## Probe environment limitation

The public AnyIO source delivered to both models lazily imports `_pytest.outcomes`
inside the shared runner coroutine. Both probe programs called fixture setup before
their first stdout observation. Their setup reports were unknown, so the timeout
location is not established by the trace.

After collection, a separate module-discovery check used the existing probe image
and prepared dependencies with no candidate source mounted. It confirmed pytest and
_pytest absent while idna and typing_extensions were present. There was no dependency
installation, candidate replay or model call. The owned container was removed.

This establishes an environment/entry-point mismatch. A failed lazy import leaving
the waiting future unsettled is a static causal hypothesis, not a replay-confirmed
explanation of either timeout. The inventory is operator evidence, not an observation
the agent obtained or an extra performance sample.

## Validation and limits

Focused wrapper checks: 11 PASS in 63.759 seconds, including both mock arms through
mutation, public check, submission and isolated evaluation. Related input/usage/
transport checks: 68 PASS in 141.172 seconds. Ruff passed. No production source changed;
the existing identical-runtime broad validation was reused. Its original 3,435 cases
were 3,412 PASS / 7 FAIL / 16 SKIP; all seven failures passed unchanged-code rechecks.
The original failure record remains intact. Post-documentation checks are in the closure.

All 47 actual model inputs, 49 count requests, seven journal chains and 87 frozen
files verified. Responses were completed 46/incomplete 1. Both arms used ten segments;
ON had one input-size boundary. A pre-dispatch count reached 71,220; after handoff the
largest dispatched input was 49,763. The 60,000 limit applies to selected dispatches,
not every exploratory count. No hidden evaluator details were read for this review.

## Decision and next question

OFF preserved all three selected prior successes and did not lose an A success.
This supports using none as a simpler option for subsequent development. One sample
per task and the AnyIO resource-limited outcome do not establish general superiority
or better independent condition discovery. Defaults and the selected working baseline
were not automatically changed. Earlier Pydantic/HF and timing groups remain separate.

Close planning comparisons here. The concrete next diagnostic is whether public probe
entry points have their prerequisite dependencies and expose failures before waiting
indefinitely. The missing pytest finding narrows that question without authorizing a
candidate replay, new dependency preparation or another paid group.

## Evidence

- Protocol, metrics, public behavior, environment inventory and closure:
  `C:\pt\analyses\planning-off-regression-20260927-v1`.
- Raw group: `C:\pt\planreg0927a`, `run_dev_planreg0927a`.
- Preceding [planning ON/OFF result](2026-09-26-planning-off-comparison.md).
- Separate [first-plan timing result](2026-09-27-after-source-planning-comparison.md).
