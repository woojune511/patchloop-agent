# Current status

Updated: 2026-09-27. This is a replaceable snapshot of current decisions, not an
append-only log. Source code owns runtime behavior; this page owns current priorities.
Read [history](history/README.md) only for a specific evidence question.

## Direction

Build an agent that understands public tasks, makes correct repairs, checks changed
and preserved behavior, and submits reliably within bounded cost and time. Start
with observed failures, diagnose causes, and select the smallest useful improvement.
Research questions can arise during diagnosis; reusable method claims follow evidence.
There is no commitment to demonstrate a memory effect or another preselected method.

Comparisons answer concrete causal questions when needed. Successful plumbing,
note/probe use, or submission alone does not establish better task solving.
Simplifying an ineffective mechanism is a valid next step.

## Active runtime and working baseline

- `dev-head` is the sole active mutable runtime; every run is `official=false`.
- The chosen performance baseline is `gpt-5.4-2026-03-05`, xhigh, 25,000 output tokens.
  The last live comparison used runtime checkpoint `93ec0af`.
  These selected settings are not a statement of CLI defaults.
- Baseline options: segmented-v1, result-or-size-v1 boundaries, brief-v1, probes
  enabled / probe-policy none, repair-recheck, protected-v1 inspection, and
  per-call-v1 completion-cost admission.
- Limits: 40 model calls, 100 tool actions, 4 accepted mutations, 1,800 seconds;
  paid work also needs an exact separately authorized invocation-wide cost cap.
- Cross-run memory, held-out tuning, and claim execution are disabled. Bounded
  run-local notes and public state remain available.
- Historical Rapid executables are absent. Existing history and evidence are immutable.

Keep the chosen baseline fixed while diagnosing a failure. Any proposed change
should identify the mechanism it tests; task-specific repair hints are excluded.
See [operations](operations.md) for commands and actual CLI defaults, and the
[implementation guide](../.agent/guide.md) for the relevant source and contracts.

## Current problem and next decision

The planning ON/OFF regression comparison is closed. On AnyIO v3, Fromager v1 and
pgmpy v1, `brief-v1` achieved acceptance 2/3 planned plus one NOT_RUN; `none` achieved
3/3. All six started, five submitted and passed acceptance and safety, and no uncertainty
stopped the group. These tasks were selected from prior successes; each arm/task has
only one new run. Older outcomes were not controls or pooled into this group.

AnyIO ON made ten source calls before editing, failed the public explicit-cancellation
preservation case, and used a probe that timed out without observations. Its last
response hit a cost-reduced output ceiling, then COST_CAP_REACHED prevented submission.
OFF grouped eleven source actions into four calls and edited on call six after its own
probe timed out. Its pending-future/runner-loop condition passed the public checks and
acceptance. Code, batching and available recovery budget differed; this does not isolate
planning's effect on judgment. Both Fromager arms succeeded with the same call count.
Both pgmpy arms succeeded, but OFF inspected more source and had higher cache-neutral cost.

OFF preserved all three selected prior successes and lost no A success. This supports
none as a simpler option for subsequent development. Defaults and the selected working
baseline were not automatically changed. Close this planning comparison branch here;
the evidence does not call for another planning template or establish general efficacy.
The earlier Pydantic/HF ON/OFF and first-plan timing comparisons remain separate evidence.

The probe readiness correction now also has an exact replay on the ON failure candidate.
Its original question/program and candidate reproduced the old bundle's empty timeout.
With the corrected pytest bundle, the same program observed ordinary cancellation ending
the shared runner task, then `ClosedResourceError` during fixture teardown. Both new
executions kept the full 30-second probe limit, identical source and sandbox controls;
only dependencies and derived profile identity differed. The earlier base-source replay
remains separate evidence. These observations were not delivered to the original models,
and neither closed solve result changes.

Preparation supports `--select-dependency` within public declared groups/extras. Use the
new AnyIO bundle for subsequent diagnostics; top-level import success alone is not
entry-point readiness. No new prompt, planning policy or default change is indicated.

The next comparison is prepared: identical saved ON candidate, fresh independent runs,
with timeout evidence in A and completed lifecycle evidence in B. Both arms use the
corrected dependencies for any new probes and retain the chosen baseline. This tests
use of supplied observations, not spontaneous case selection or native continuation.
The fixed proposal is A1/B1/B2/A2, two per arm, $1.20 each / $4.80 total. It has input
delivery checks and existing seeded-run mock validation; collection is NOT_RUN and
requires this new group's cap to be authorized. Old plans/check verdicts are not imported.

The group spent $3.183588 of $7.20; unused funds are closed. All 47 actual inputs, 49
count requests, seven journal chains and frozen files verified. One response was
incomplete; the other 46 completed. Probe timeout, resource exhaustion, acceptance and
safety remain separate. No paid allocation or continuation is active.

## Implemented and measured

The latest investigation changed no product runtime files. Two provider-free Docker
replays exposed the selected candidate's ordinary-cancellation failure. Paired input
previews verified observation delivery with equal remaining controls. Existing seeded
repair mocks reached isolated evaluation. These establish execution and delivery,
not improved model repair or acceptance. No new paid model run occurred.

The opt-in first-plan timing, declaration expansion and independent-candidate diagnostics
remain implemented, with no default adoption established by their closed comparisons.
The planning OFF comparison removes the explicit planning feature as a whole; bounded
working notes, internal reasoning and registered tools remain available.

Evidence for targeted lookup:

- Latest diagnostic: [AnyIO failure observation](history/2026-09-27-anyio-failure-observation.md).
- Reproduction and prepared comparison: `C:\pt\analyses\anyio-observation-repair-20260927-v1`.
- Preparation correction: [AnyIO probe readiness](history/2026-09-27-anyio-probe-readiness.md).
- New bundle and public reproduction: `C:\pt\analyses\anyio-probe-readiness-20260927-v1`;
  descriptor: `selected-pytest\prepared-probe-dependencies.json` within that packet.
- Latest model result: [planning OFF regression](history/2026-09-27-planning-off-regression.md).
- Protocol, metrics, public review, environment inventory and closure:
  `C:\pt\analyses\planning-off-regression-20260927-v1`.
- Separate prior result: [planning ON/OFF comparison](history/2026-09-26-planning-off-comparison.md).
- Separate timing result: [first-plan timing comparison](history/2026-09-27-after-source-planning-comparison.md).
- Current implementation: [first plan after source](history/2026-09-26-after-source-planning.md).
- Existing contract: [brief planning](../.agent/planning-experiment.md).
- Prior next-question result: [declaration checkpoint comparison](history/2026-09-26-declaration-checkpoint-comparison.md).
- Prior interpretation audit: [first interpretation and source questions](history/2026-09-26-first-interpretation-audit.md).
- Prior candidate result: [independent candidate comparison](history/2026-09-26-independent-candidate-comparison.md).
- Earlier decisions and immutable records: [documentation history](history/README.md).

## Reading and updating this page

At task start, read this page and the relevant implementation/operation section.
Search history only when a named failure, decision, or evidence gap needs it; read
the matching passage rather than whole snapshots. Historical "current", "latest",
"next", commands, and approvals describe their original checkpoint only.

Replace stale status here. Record a significant completed investigation once in
`docs/history/`, then keep only its current implication and evidence link here.
Do not append run-by-run results, validation totals, or superseded plans to this page.
Documentation size limits are checked by `tests/test_documentation_layout.py`.
