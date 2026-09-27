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
  The latest information comparison used collector checkpoint `0cf07b81`.
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

The cleanup-information comparison is closed. Four continuations of B1 immediately
after its first failed lifecycle check ran A1/B1/B2/A2. A retained the saved input;
B added later raw operator cancellation-order/state observations of that exact
candidate once. Other candidates, rescue patches and interpreted causal verdicts
were excluded. Both arms retained previous caller-information exposure.

Both arms achieved 2/2 acceptance with seven new model calls per arm. A cost
$0.956988 and B $0.9576855. Both repaired the failure; this selected checkpoint
does not demonstrate an information benefit or general equivalence.

Delivery and billing audits passed; owned containers are absent. New spend was
$1.9146735 of $2.786950; unused funds are closed. No paid allocation, retry or
continuation is active. Detailed traces and receipts remain in
[results](history/2026-09-27-cleanup-information-results.md).

The provider-free waiting-caller follow-up is also complete. Ten probes compared
base and all four accepted candidates with normal Event release versus direct
cancellation of the existing waiting caller. All five normal cases completed with
exactly one same-task fixture cleanup; all five cancellation cases stalled. The
caller was cancelled, but the runner retained cancelling() == 0 and the active
test's finally and teardown had not begun at the two-second watchdog. All ten
containers were removed; source snapshots and old journals remained unchanged.

Because base also stalls, this is not evidence of a newly introduced regression.
It is a distinct internal-task cancellation path, not the task's KeyboardInterrupt
case or public check's test-coroutine cancellation. A bounded review of the pinned
public docs, plugin, runner API and source found no supported entry point for
directly cancelling that waiting caller. Close this diagnostic without expanding
the required checks or invalidating prior acceptance. This is absence of support
evidence in the inspected version, not proof that no external integration can do it.
See [caller support scope](history/2026-09-27-caller-support-scope.md).

The pinned benchmark comparison confirms the same base, but rewritten issue input,
added public checks and a different final oracle. Recent acceptance is for adapted
development tasks, not original SWE-rebench scores. Original configuration specifies
Python 3.13; a fresh inspection confirms the local evaluator is 3.13.13 with the
correct clean base. Recent probes use a separate 3.12 bundle. Original inputs and
upstream scoring sources are pinned evaluator-side. Original-oracle calibration now
distinguishes BASE (F2P 0/1, P2P 32/32) from REFERENCE (1/1, 32/32). Both full commands
exit 1 due to three extra Hypothesis-dependent tests; none of the required cases
are missing. Selected upstream parser/grading functions ran, not the full upstream CLI.
Next: freeze original-input baseline protocol and sample before fresh solves.
See [calibration](history/2026-09-27-original-benchmark-calibration.md).
AnyIO remains development/calibration data, not untouched held-out evidence.
See [benchmark differences](history/2026-09-27-anyio-benchmark-differences.md).
No new paid run is authorized.

Caller-state observations concern the pinned callback-interrupt path, not every
SIGINT/cancellation path. Earlier fresh N1/N2 solves and advice-removal comparison
remain separate closed evidence with unchanged budgets and outcomes.

Earlier supplied-candidate A/B repairs remain separate 2/2 acceptance per arm,
with no observed information advantage. They are not fresh-solve controls;
earlier NOT_RUN outcomes remain unchanged.
Use the selected pytest dependency bundle for further AnyIO diagnostics. The
planning OFF comparisons remain closed without automatic adoption or baseline change.

## Implemented and measured

The checkpoint collector has live provider acceptance, exact delivery and separate
cost-accounting evidence for the closed interventions. Accepted continuations are
not fresh solves. The earlier N1/N2 fresh solves used unmodified run_dev with corrected
dependencies. Reliable recovery, general improvement and default adoption remain
unestablished; earlier supplied-candidate repairs remain separate evidence.

The opt-in first-plan timing, declaration expansion and independent-candidate diagnostics
remain implemented, with no default adoption established by their closed comparisons.
The planning OFF comparison removes the explicit planning feature as a whole; bounded
working notes, internal reasoning and registered tools remain available.

Evidence for targeted lookup:

- Cleanup information: [results](history/2026-09-27-cleanup-information-results.md);
  packet: `C:\pt\analyses\cleanup-information-results-20260927-v1`.

- Cleanup mechanism: [trace and one-line removal](history/2026-09-27-anyio-cleanup-cancellation.md);
  packet: `C:\pt\analyses\anyio-cleanup-analysis-20260927-v1`.
- Information comparison results: [outcomes and public audit](history/2026-09-27-caller-information-results.md);
  packet: `C:\pt\analyses\caller-information-results-20260927-v1`; live: `C:\pt\callerinfo0927a`.
- Information comparison preparation: [scope and validation](history/2026-09-27-caller-information.md);
  [contract](../.agent/caller-information.md);
  packet: `C:\pt\analyses\caller-information-comparison-20260927-v1`.
- Caller-state measurement: [observation and control](history/2026-09-27-anyio-caller-state.md);
  packet: `C:\pt\analyses\anyio-caller-state-20260927-v1`.
- Closed comparison: [checkpoint results](history/2026-09-27-checkpoint-live-results.md);
  packet: `C:\pt\analyses\checkpoint-live-results-20260927-v1`; live: `C:\pt\mutationlive0927a`.
- Live collector: [preparation and environment block](history/2026-09-27-checkpoint-live-preparation.md);
  [contract](../.agent/checkpoint-comparison.md);
  packet: `C:\pt\analyses\checkpoint-live-comparison-20260927-v1`.
- Offline continuation: [restoration and execution](history/2026-09-27-checkpoint-continuation.md);
  [contract](../.agent/checkpoint-continuation.md);
  packet: `C:\pt\analyses\checkpoint-continuation-20260927-v1`.
- Original input pair: [mutation advice checkpoint](history/2026-09-27-mutation-advice-checkpoint.md);
  [contract](../.agent/mutation-advice-checkpoint.md);
  packet: `C:\pt\analyses\mutation-advice-checkpoint-20260927-v1`.
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
