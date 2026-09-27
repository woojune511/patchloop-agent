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
  The last live comparison used execution checkpoint `5d74710`.
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

Two fresh AnyIO v3 full solves with the corrected probe environment are closed.
Both used the fixed baseline, no historical hints/candidates and $1.20 per run.
N1 made two unsuccessful repairs and ended COST_CAP_REACHED without submission:
acceptance and safety are NOT_RUN. N2's first repair passed both public checks,
submitted and passed isolated acceptance/safety. Total cost was $1.854949 of $2.40;
unused funds are closed. No paid allocation, extra sample or continuation is active.

Both independently selected probes and reproduced interrupted-test resumption.
N1's first repair nevertheless claimed a caller-cancellation condition that its
probe had not measured. Its attempted discriminator then stopped on a model-authored
function-name setup assertion. A second repair still resumed the test and broke
cleanup; a final useful probe preceded a reasoning-only incomplete response at a
reduced 4,081-token ceiling. Failed repair, diagnostic error and resource exhaustion
are distinct observations, not a proven single-cause account of the terminal result.

N2 directly handled an incomplete call on the interrupt path and retained the
shared runner for cleanup. It passed lifecycle 7/7 and upstream 32 tests (three
deselected), then submitted. It did not rerun its original probe after editing.
The visible plain-fixture explicit-cancel same-task assertion gap remains a public
coverage limit; prior operator replays of other candidates do not close it here.

All 19 actual inputs/count bindings and continuation records verified. No probe
timed out, no infrastructure uncertainty stopped the group, and all eight owned
check/probe containers are absent. The corrected environment enabled observations,
but one accepted result and one resource-limited non-submission do not establish
general reliability, an environment-effect estimate or a new harness mechanism.

The next causal question is how unsupported premises enter a repair decision and
how cancellation ordering defeats recovery. Use N1's public trace to isolate a
concrete distinction before selecting a harness ablation. More generic warnings,
mandatory probes and larger budgets are not established fixes. Step 3 is unrun.

Earlier supplied-candidate A/B repairs remain a separate 2/2 acceptance per arm,
with no observed advantage from supplied completed output. Their operator probes
and B1 branch deletion establish only those saved candidates' measured behaviors.
They are not fresh-solve controls; earlier NOT_RUN outcomes remain unchanged.
Use the selected pytest dependency bundle for further AnyIO diagnostics. The
planning OFF comparisons remain closed without automatic adoption or baseline change.

## Implemented and measured

The latest two fresh solves used unmodified run_dev and the existing bounded
collector with corrected dependencies. One complete solve within the original cap
is observed; reliable recovery, general task-solving improvement and default adoption
remain unestablished. The earlier four seeded repairs and their operator observations
remain separate evidence.

The opt-in first-plan timing, declaration expansion and independent-candidate diagnostics
remain implemented, with no default adoption established by their closed comparisons.
The planning OFF comparison removes the explicit planning feature as a whole; bounded
working notes, internal reasoning and registered tools remain available.

Evidence for targeted lookup:

- Latest result: [AnyIO fresh solves](history/2026-09-27-anyio-fresh-solve.md);
  packet: `C:\pt\analyses\anyio-fresh-solve-20260927-v1`; live: `C:\pt\anyiofresh0927a`.
- Patch diagnostic: [AnyIO B1 branch deletion](history/2026-09-27-anyio-b1-branch-deletion.md);
  packet: `C:\pt\analyses\anyio-b1-branch-deletion-20260927-v1`.
- Audit: [AnyIO evidence/action links](history/2026-09-27-anyio-evidence-action-link.md);
  packet: `C:\pt\analyses\anyio-evidence-action-link-20260927-v2`.
- Replay: [AnyIO final probe scope](history/2026-09-27-anyio-final-probe-scope.md);
  packet: `C:\pt\analyses\anyio-final-probe-scope-20260927-v2`.
- Process analysis: [AnyIO process audit](history/2026-09-27-anyio-observation-process-audit.md);
  packet: `C:\pt\analyses\anyio-observation-process-audit-20260927-v1`.
- Closed result: [AnyIO observation repair comparison](history/2026-09-27-anyio-observation-repair-comparison.md).
- Results, public decision review and closure:
  `C:\pt\analyses\anyio-observation-repair-results-20260927-v1`; live state: `C:\pt\obsrepair0927a`.
- Prior preparation: [AnyIO failure observation](history/2026-09-27-anyio-failure-observation.md).
- Frozen reproduction/comparison: `C:\pt\analyses\anyio-observation-repair-20260927-v1`.
- Preparation correction: [AnyIO probe readiness](history/2026-09-27-anyio-probe-readiness.md).
- New bundle and public reproduction: `C:\pt\analyses\anyio-probe-readiness-20260927-v1`;
  descriptor: `selected-pytest\prepared-probe-dependencies.json` within that packet.
- Separate prior model result: [planning OFF regression](history/2026-09-27-planning-off-regression.md).
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
