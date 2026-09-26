# Current status

Updated: 2026-09-26. This is a replaceable snapshot of current decisions, not an
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
- The chosen performance baseline is `gpt-5.4-2026-03-05`, xhigh, 25,000 output tokens,
  common runtime checkpoint `4d2fc8ba` / tool surface v45. This is a selected
  configuration, not a statement of CLI defaults.
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

Recent seeded repair runs submitted unchanged candidates that passed registered
public checks while isolated acceptance failed. In the last paired-observation
group, acceptance was A 0/2 and B 0/2; both B declarations were rejected before
their comparison executed. Comparison execution was NOT_RUN 2, separate from the
four executed acceptance failures. This does not establish a memory bottleneck.

Use saved public task/source/action/check evidence to locate the failure, including
possible gaps in requirement interpretation, case selection, or repair decisions.
Distinguish an interface rejection from the semantic usefulness of a proposed case.
Choose the next diagnostic, correction, or simplification for the uncertainty it
resolves. Do not automatically continue paired-observation experiments.

## Implemented and measured

The optional paired-observation diagnostic now uses code-owned public evidence IDs
and allows correction of a rejected declaration within its original phase/resource
limits. This is an opt-in diagnostic; common runtime defaults remain unchanged.
Valid IDs do not certify case execution, expectation validity, or requirement coverage.

Its recorded local validation is 40 focused tests, 138 related regression tests,
and nine isolated evaluation mocks passing. The focused group took 87.803 seconds;
the related regression took 651.897 seconds. These are retained checkpoint results,
not fresh tests of all current repository behavior. Live performance of the updated
interface is NOT_RUN. No unused budget or local PASS authorizes another run.

Evidence locations for targeted lookup:

- Public-reference implementation: `C:\pt\validation\paired-reference-20260926-v1\result.md`.
- Closed comparison: `C:\pt\analyses\paired-observation-compare-20260926-v1\result.md`.
- Full prior narrative and earlier decisions: [documentation history](history/README.md).

## Reading and updating this page

At task start, read this page and the relevant implementation/operation section.
Search history only when a named failure, decision, or evidence gap needs it; read
the matching passage rather than whole snapshots. Historical "current", "latest",
"next", commands, and approvals describe their original checkpoint only.

Replace stale status here. Record a significant completed investigation once in
`docs/history/`, then keep only its current implication and evidence link here.
Do not append run-by-run results, validation totals, or superseded plans to this page.
Documentation size limits are checked by `tests/test_documentation_layout.py`.
