# C2 public-regression feedback: two autonomous continuations

Date: 2026-10-04. Allocation closed; official=false, claim-ineligible.
Both candidates now satisfy the issue output and 506 public regressions after one
autonomous additional edit. One submitted and passed original acceptance/safety;
the other exhausted its cost allowance before submission, so acceptance is NOT_RUN.
Keep the selected four-edit baseline. No additional run or policy adoption follows.

## Problem, hypothesis and intervention

The [previous choice diagnostic](2026-10-04-c2-choice-results.md) ended 0/2: both
fourth edits produced the expected eight-space output but broke the same public
regressions. Neither had a remaining edit after that feedback. Repeating that
diagnostic would not answer whether the model could use the newly observed failure.
Mismatch recognition and operator localization were already closed questions.

The user approved two continuations after [provider-free preparation](2026-10-04-c2-feedback-preparation.md).
Each starts after its actual failed registered check, with the source, public
observations, native history and spent resources preserved. The existing maximum
accepted-mutations setting changes from four to five in a new diagnostic fork.
No new prompt, conditional extension policy, gate or reviewer was implemented.
No operator correction, post-run observation or hidden result enters model input.

This tests autonomous correction with failure feedback and one additional edit.
Continued regression or loss of the issue output would weaken that repair hypothesis.
Successful repair still need not imply successful bounded submission, as live1 shows.
It does not isolate feedback from added edit capacity or improve pre-feedback
fourth-edit selection. The old allocations stay closed and historical spending is
not billed again. Full scope is retained in the external approved-scope.md snapshot.

## Execution identity and bounds

- Execution commit: 89c1ff4ccb06ca30b2436fcbd8f48018b6a46528.
- Runtime hash: sha256:ca68a11874470d7887733422b5c715afb67a11e9b8d22d2a1c1de3e5b3b2b027.
- Manifest hash: sha256:eba2c6c17e4aec20f0159cbcf38ba3b9181316dfb9b0bbf62971f414c5b9b779.
- Registered dev-train task: swebench-lite-dev-sqlfluff-sqlfluff-1733.
- Model: gpt-5.4-2026-03-05, xhigh, desired output ceiling 25,000 tokens.
- Credential file: C:/Users/geonj/Documents/PatchLoop/.env.
- Source order: C:/pt/c2cp01/live1 then live2, one continuation each.
- New caps: USD 0.5849210 and 0.8077385; invocation total USD 1.3926595.
- Remaining calls/actions at failure: 21/65 and 22/64; one edit each.
- Remaining active time upper bounds: 544.085 and 611.741 seconds, without reset.

SDK retries remained zero. No resume, replacement, transfer, sixth edit or time
extension occurred. All usage settled; no count/transport/billing/cleanup/identity
uncertainty triggered stop-all. Existing images were used. The independent post-run
public pair had a separate 120-second operator deadline and was never fed back.

## Results

Each row's issue-output program and regression suite ran on the same final diff.

| Row | Issue output | Public regressions | Terminal | Acceptance | Safety | New USD |
| --- | --- | --- | --- | --- | --- | ---: |
| live1 | PASS | 506 PASS | COST_CAP_REACHED | NOT_RUN | NOT_RUN | 0.5849120 |
| live2 | PASS | 506 PASS | EVALUATOR_PASS | PASS | PASS | 0.3234745 |

Total new cost: USD 0.9083865. There were eight dispatched model calls, nine input
counts, thirteen actions and two accepted edits. Historical usage remains separate.

| Row | New calls/counts/actions/edits | Solver active seconds since failure | Process seconds | Post-run operator seconds |
| --- | --- | ---: | ---: | ---: |
| live1 | 5 / 6 / 8 / 1 | 327.585 | 327.293 | 39.713 |
| live2 | 3 / 3 / 5 / 1 | 208.792 | 208.407 | 40.624 |

Active elapsed includes preserved preparation timing; process duration is measured
separately. Neither candidate had timeout, truncated public output or cleanup failure.

### Autonomous changes and completion

live1 searched public fixtures and source, then restricted L036's whitespace copy
to an existing whitespace index and `segment.pos_marker.working_line_pos > 1`.
This uses the SELECT's column to distinguish the indented issue from the observed
top-level regressions. It differs from the operator's first-target correction.
The accepted fifth edit is at journal sequence 385; automatic regression completion
390 reports 506 passing, and saved-probe completion 394 preserves the full expected
output and nearby control. These checks precede the final model request.

That final request had 51,273 input tokens. Cost admission reduced output capacity
to 224 tokens; all 224 were consumed by reasoning output, yielding a known-billed
`incomplete_response` with `max_output_tokens`, without a finish tool call.
The normal protocol-correction input was counted once, but no further dispatch
fit the remaining USD 0.000009. Sequence 409 closes COST_CAP_REACHED. This is a
completion-resource failure after public repair, not evidence that the patch
failed or that the model rejected successful verification. Acceptance was not
forced after the terminal state.

live2 independently restricted whitespace copying to the first target, with a
second target after the first existing newline and a usable whitespace position
before the last target. Mixed lists keep the plain-newline behavior. Its fifth
edit is accepted at sequence 343, required regression completes at 348, and saved
probe at 352 passes both the issue and preservation case. The model calls
finish_task at 366; isolated evaluation then reports acceptance PASS and safety
PASS. This was an actual model-selected patch, not the synthetic preparation fixture.

Both candidates retain earlier L003 changes. Removing those changes was not a
success condition; their necessity and broader input coverage are not reassessed.

Final cumulative patch hashes:

- live1: sha256:6dc38dc8bdc19526ae2f52be39e206096a4f056657a26d0d34872e7bb3633868.
- live2: sha256:2374e8b1a0c85e5658ce7c5bb5a30113484d852cb5d455c4209fdb6b6b9dbba6.

## Audit, evidence and decision

External preparation/authorization: C:/pt/analyses/c2-feedback-prep-20261004-v1.
Closed result, audit, approved scope, final diffs and independent public receipts:
C:/pt/c2fb01/allocation. Funded journals/workspaces: C:/pt/c2fb01/live1-funded and
live2-funded, each run_dev_8ae27bd1b3464578. Hash-chained allocation and closeout
journals bind the immutable artifacts; the repository contains no generated run state.

The provider-free auditor verifies original files and seed prefixes unchanged,
exact frozen first requests, settled new-only billing, unique complete actions,
and identical candidate identity across mutation, final workspace and public pair.
Each dispatch matches its selected counted input; only the admitted output ceiling
may shrink. All eight dispatches and nine counts have completed records. The extra
live1 count is the denied correction request, not an unaccounted generation.
The user AGENTS.md change and closed historical records were preserved.

Repository closeout changes are documentation only. Documentation layout/link
tests, Ruff and diff checks passed. Runtime, full fast suite and mock smoke were
not rerun; preparation already exercised the unchanged runner and collector paths.
The two live executions and real checks are separate from those synthetic tests.

The prior open question now has positive evidence: these two agents could use
actual regression feedback to narrow a change while retaining the issue behavior,
given one extra edit. One also completed original acceptance within its budget.
The local decision changes from autonomous correction NOT_RUN to observed 2/2
public repair, with 1 PASS and 1 NOT_RUN acceptance. It does not establish general
five-edit performance, a causal feedback-only effect, improved fourth-edit judgment,
or sufficient grounds to adopt conditional budget extensions. Baseline stays at
four and this allocation closes. Completion under a nearly exhausted cost cap is
a separate observed limitation; no additional evaluation is automatically queued.
