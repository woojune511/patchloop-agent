# Reviewer time-budget diagnosis

## Question and selection

The [third pilot](2026-10-02-review-pilot-v2-result.md) reached valid reviewer actions
but timed out before B returned a report. This prevented the repair-quality
comparison. Diagnose whether input size, the reviewer horizon, or variable response
latency explains the failure before changing limits or funding another run.
This is a provider-free examination of saved public requests, event timestamps,
usage settlements and current admission code at 4f1037ca, not a new experiment.

Evidence: C:/pt/analyses/review-timing-audit-20261002-v1/summary.json and its
hash-chained journal. Driver: C:/pt/review_timing_audit_20261002.py. Only the three
closed pilot reviewer journals were inspected. Encrypted reasoning contents were
not examined or projected. No provider calls, probes, credentials or invoice
queries were used; original evidence was not rewritten.

## Exact timed-out request

| Property | Saved value |
| --- | --- |
| B call | Third of at most four |
| Input tokens | 9,768 |
| Model / reasoning | gpt-5.4-2026-03-05 / xhigh |
| Maximum output tokens | 25,000 |
| Remaining time shown before counting | 147.1558848 seconds |
| Remaining calls including this request | 2 |
| Remaining actions | 8 |
| Remaining shared cost | USD 1.958134 |
| Tool choice | required; finish_review not forced |
| Wait until timeout | 146.838377 seconds |
| Returned output / usage | Absent; actual output tokens unknown |

The first two B generations took 14.089355 and 16.205312 seconds, returning 734 and
759 output tokens. Their four read/search actions completed. The third response
did not arrive within the remaining time. The output ceiling is a maximum, not
evidence that the provider generated 25,000 tokens. Cost and call slots remained;
the time deadline was the binding observed limit.

## Bounded comparison with existing responses

| Pilot / arm | Completed response durations, seconds | Returned output tokens |
| --- | --- | --- |
| 20261001-v1 / A | 13.15, 34.34, 3.30, 15.49 | 669, 1,935, 115, 839 |
| 20261002-v1 / A | 119.02 | 8,493 |
| 20261002-v2 / A | 66.68 | 3,822 |
| 20261002-v2 / B | 14.09, 16.21 | 734, 759 |

Eight completed responses span 3.30-119.02 seconds, median 15.85 seconds. The
timed-out response is censored and is excluded from that completed-latency summary.
These are different instructions, contexts and response contents across revisions;
they are not a controlled latency study or enough data to estimate a reliable tail.
Earlier larger inputs of 19,730-28,652 tokens completed. Therefore input growth to
9,768 alone does not establish a context-size bottleneck. Variable output/reasoning
work and provider/transport delay remain plausible; saved data cannot separate them.

## Mechanism in source

review_context_rehearsal._review sets a single deadline at budget.started + 180.
report_required is based only on remaining calls == 1 or exhausted action allowance.
Each generation receives deadline.check() as its timeout; no report-time reserve
is subtracted. The adapter passes that timeout into the provider request.
SharedBudget rejects later work once the review deadline has elapsed.

Consequently, reserving the fourth call does not reserve enough wall time to reach
it. Any earlier generation can consume the remaining deadline. Time is disclosed
to the model but not used to force an earlier report. This is an identifiable
completion-design limitation, not evidence that the SDK ignored a timeout.

A simple "force report below 60 seconds" threshold would not change the observed
third request, which began with 147 seconds left. Cutting that request short to
reserve 60 seconds would cause a transport/billing-uncertain stop; the approved
contract forbids continuing to a fourth request afterward. Thus an early timeout
is not a usable report reservation under the current stop rule.

For scale only, the observed 119-second generation plus A's 67-second report would
already exceed 180 seconds before other work. This is arithmetic on different
responses, not a prediction or a recommended new timeout. Forcing a report on the
third call also has an unknown latency and changes available investigation; it
cannot be claimed to fix this run counterfactually.

## Decision and limits

The 180-second allowance is not proven universally inadequate, but it does not
guarantee the intended investigate-then-report procedure with observed variable
latency. There is no evidence-based replacement deadline, output ceiling or
reasoning setting from these eight completed responses. Increasing time could
allow completion, but has not been shown to improve repair quality or resolve
the underlying unbounded response-latency problem.

Keep the coding-agent baseline and diagnostic implementation unchanged; no paid
rerun or adjacent prompt tuning is queued. The audit changes the interpretation
from "four calls reserve completion" to "call reservation leaves a time-dependent
censoring risk." Any future redesign must address the procedure before dispatch,
preserve honest partial evidence and uncertainty stops, and measure correctness
alongside completion, latency and cost. It needs a separate justification, not
the unused allocation from this closed pilot.

The comparison remains INCONCLUSIVE. The latest confirmed cost remains a lower
bound of USD 0.2585735; the timed-out request's billing was not reconciled here.
Documentation validation and diff hygiene are checked for this follow-up; runtime
tests are not rerun because runtime and diagnostic behavior were not changed.
