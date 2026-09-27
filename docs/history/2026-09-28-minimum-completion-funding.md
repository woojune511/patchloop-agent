# Minimum completion funding: independent saved-state diagnostic

2026-09-28. `official=false`; provider/count/evaluator calls zero; policy unchanged.

## Question and definition

The [prior audit](2026-09-28-completion-budget-audit.md) found that the existing cost
policy closes investigation to protect speculative recovery. Separate that recovery
budget from the minimum successful successor path while retaining the baseline
model/tool-count scheduler and offered tools, including parallel-read capacity.

For each saved state, calculate successful successor calls for every offered action:
read/search removes a required missing-anchor read if applicable; probe preserves the
current path; an edit leaves all checks and finish; a successful required check removes
one check; a diagnostic base check leaves the repair path; finish/stop need no successor.
This calculation covers the observed states with no failed mutation or failed check.
It assumes successful actions and is not a failure-recovery contract.

Before generation the selected action is unknown. The main projection therefore
reserves the largest minimum successor across all currently offered tools. Separate
per-action columns are hindsight sensitivity, not a dispatch algorithm. The difference
between protected and minimum horizons is reported as advisory cost, not charged or
reserved. No new tool restriction was introduced.

Future input stays at the frozen 60,000-token bound with uncached pricing. Sensitivity
grid for future output: 128, 1,024, 4,096, 25,000 tokens. These are hypothetical future
allowances, not useful-output guarantees or recommended thresholds. Current output
retains the existing 128-token admission floor and 25,000 desired ceiling. No price
lookup or provider request was made; the calculations use the run's frozen rates.

## Results

All 24 saved current-request ceilings reproduce the baseline ledger calculation.
At each independently observed state, read/search availability and parallel-read
capacity remain unchanged. For every admitted sensitivity row, current reservation
plus future reserve remains within the remaining cap.

| Assumed future output | Toqito: first recorded response too long or no admission | MontePy | Darts |
| --- | --- | --- | --- |
| 128 | call 8 | all recorded responses fit | all recorded responses fit |
| 1,024 | call 7 | all recorded responses fit | all recorded responses fit |
| 4,096 | call 6 | all recorded responses fit | all recorded responses fit |
| 25,000 | call 1 | call 1 | call 1 |

"Fits" only compares recorded output length with an arithmetic ceiling. It does not
mean the alternative model would produce that response or solve the task. Even where
the recorded response fits, a changed output ceiling may change behavior. At 128 future
output, the first ceiling change is toqito call 5 and MontePy call 8; darts retains the
same ceiling at all five observed states. At 4,096, all first-request ceilings change.
Do not chain later observed-state results into a hypothetical alternate execution.

### Toqito's edit boundary

Before call 8: $0.4642405 remains; the saved input is 30,731 tokens; the observed output
is 19,560 tokens. Read/search/probe/diagnostic check each need three successful future
calls, while immediate edit needs two (check and finish).

At the 128 future-output assumption, preserving every offered action reserves
$0.45576, leaving too little even for the current input. The request cannot dispatch.
If the next action were already known to be edit, reserving $0.30384 for check/finish
would leave only 5,571 output tokens. The future-output assumptions 1,024 and 4,096
reduce that edit-only ceiling to 3,779 and no admission respectively.

Thus late reservation alone cannot retain the recorded large edit and fund its
completion under this cap. The actual edit call cost $0.3555395; adding the conservative
minimum two-call reserve would require $0.6593795, above the $0.4642405 then remaining.
This is a comparison to a bounded reservation, not a measured cost for unexecuted future
checks/submission. Actual future inputs, caching, output and correctness are unknown.

## Decision

Separating speculative recovery removes the early investigation restriction in this
projection and preserves arithmetic room for both successful control traces at the
three smaller assumptions. It is a useful candidate mechanism, not a validated fix.
A uniform 25,000-token allowance for each possible future call cannot fit this $1.20
setup. Picking 1,024 or 4,096 merely because the two successes fit would overfit them.

Do not adopt a new reservation policy or claim a recovered toqito solve. The next
concrete design question is earlier cost control: how to leave room for edit production
and completion before optional investigation consumes it. Review what budget and
completion information the agent actually saw around toqito calls 5-8, alongside the
successful controls, before adding a prompt, output cap or tool gate. No further
paid experiment, budget increase, or private evaluation of the unsubmitted patch is
part of this diagnostic.

## Evidence and validation

Root: `C:/pt/analyses/minimum-completion-funding-20260928-v1`.
Report: `report.json`; hash-chained journal: `runs/run_dev_minimumfundingaudit.jsonl`.
Script: `C:/pt/minimum_completion_funding_0928.py`, hash bound in diagnostic_started.
Source is the prior audit plus hash-verified saved public contexts and run journals.
Four structural checks cover missing-anchor read, edit, required check and ready-finish
successors. Twenty-four baseline ceiling assertions and all admitted budget inequalities
passed. No runtime, task, old report or closed historical record was modified.

Documentation layout: 5 passed; diff whitespace check passed. Runtime was unchanged,
so no new full-suite or mock run was performed. Additional provider cost: $0.
