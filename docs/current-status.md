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

The AnyIO observation/repair comparison is closed: A received the historical probe
program/question with a timeout receipt; B received the same program/question with
the completed lifecycle observation. Both started from the same saved incorrect
candidate with fresh budgets and the corrected environment for any new probes.
Acceptance was A 2/2 and B 2/2 planned; all four submitted and passed safety. There
were no NOT_RUN results, infrastructure stops or incomplete responses.

All four first reran the public lifecycle check, read the owning source, made one
new edit, passed the automatic lifecycle recheck and upstream regression, then
submitted. No new probe was requested. A recovered from the fresh check and source
without the completed operator observation. This small selected comparison shows
no acceptance advantage from supplying that observation and supports no new prompt
or planning rule. It does not establish general equivalence or spontaneous case
selection; completion guidance and repair-recheck were fixed controls.

A source/action audit links all 26 inputs, 34 public actions and 31 delivered source
spans. Reads informed the four repairs, but B1's helper explanation overreached:
the seed entered that helper and returned before its additional cancellation.
Its runner-loop repair addressed the observed failure; the extra exception branch's
necessity remains untested. Completed B observations, probe access and a warning
about untested behavior were present. These records do not support missing delivery,
probe access or warnings as explanations. Advice/action alignment does not prove causation.

The public explicit-cancel case uses a plain fixture and bypasses its same-task
assertion. A separate operator replay now closes that observation gap: the exact
existing probe reproduced the old seed's failed teardown, while all four saved
final candidates kept the runner alive and completed cleanup once in the original
task. All five executions used the same corrected dependency/profile identities,
completed without timeout and confirmed owned-container cleanup; model calls were
zero. This is one single-cancellation plain-fixture observation, not autonomous
verification, all-state equivalence or proof that extra patch branches are needed.

The smallest next counterfactual is deletion of B1's extra exception branch under
the same public probe/check environment. That tests patch necessity, not harness
ablation. A recommendation-removal comparison would need matched feedback conditions:
the existing status-only diagnostic rejects supplemental feedback. Neither experiment
is active, and no prompt or runtime change is supported by the current audit.

The original cost-limited ON run remains NOT_RUN. It had asked a relevant probe
question after its failed check, but obtained no observation. These new seeded
runs reset both context and budget, so they cannot isolate the original failure's
cause or show that recovery would fit its remaining budget. A separate question
remains whether a fresh full solve, including initial investigation and candidate
generation, recovers within its original cap using the corrected probe environment.
That full-solve comparison has not been run here.

Use the selected pytest dependency bundle for subsequent AnyIO diagnostics;
top-level import success alone is not entry-point readiness. The earlier planning
OFF comparisons remain closed and separate: none is a simpler development option,
with no automatic adoption or change to this comparison's chosen baseline.
The current group spent $1.888192 of $4.80. Unused funds are closed; no paid
allocation, additional sample or continuation is active.

## Implemented and measured

The closed comparison used existing runtime and seeded-repair code for four live
model runs. All 26 actual inputs/count requests, continuation records, five journal
chains and frozen source/dependency identities verified; owned containers are absent.
Recovery is observed for this supplied candidate, with same-task ordinary-cancellation
cleanup separately observed on all four saved final patches. End-to-end task-solving
improvement and default adoption remain unestablished.

The opt-in first-plan timing, declaration expansion and independent-candidate diagnostics
remain implemented, with no default adoption established by their closed comparisons.
The planning OFF comparison removes the explicit planning feature as a whole; bounded
working notes, internal reasoning and registered tools remain available.

Evidence for targeted lookup:

- Latest audit: [AnyIO evidence/action links](history/2026-09-27-anyio-evidence-action-link.md);
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
