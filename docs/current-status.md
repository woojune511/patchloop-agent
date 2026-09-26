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

The fresh first-plan timing comparison is closed: `brief-v1` acceptance 0/4 versus
`brief-after-source-v1` 1/4. Pydantic was 0/2 versus 1/2; HF Hub was 0/2 in both arms.
All eight submitted, passed safety and completed evaluation, with no NOT_RUN or
infrastructure stop. The one-result difference leaves direction uncertain under the
frozen decision rule. These selected development tasks do not establish general quality.

The timing intervention happened in every run: A planned before its first source
result, while B first planned in the next model response after source delivery.
Later planning, tool schemas and other settings matched. Delaying that first request
did not reliably correct applicability: successful Pydantic PB1 explicitly asked whether
a generic field-mode change would be too broad, then added a provider-carried opt-in.
PB2 read the full profile and provider before planning but still used field mode alone,
as both A runs did. All four passed the same registered checks; none independently
tested the ordinary-profile preservation case.

All four HF runs ultimately forwarded `self.endpoint` and passed the public contract
and regression checks but failed acceptance. Both arms contain a public-failure repair
trajectory and a first-check-pass trajectory. The unresolved public question is whether
the value being forwarded distinguishes an explicit argument from a resolved default;
this group supplied no independent probe of that distinction. Hidden failure causes
remain unknown.

Keep defaults and the selected working baseline unchanged. First-plan timing alone is
not established as an improvement. The next design question is how an agent checks
repair applicability and preserved behavior before choosing an implementation condition.
PB1's pre-edit question is a useful observed
example; it is not a task hint or a new mandatory planning/probe template.
Planning OFF remains a simplification candidate from the separate prior comparison;
its results must not be treated as a third arm of this group.

The group spent $5.299640 of $9.60; unused funds are closed. All 76 actual inputs and
settled responses, nine journal chains and frozen files verified. Both arms used 38
model calls and 18 segments; B cost more. Some HF output ceilings shrank, but every
response completed and every run submitted. These resource differences remain separate
from claims about planning or continuity. No paid allocation or continuation is active.

## Implemented and measured

The runtime now includes the opt-in first-plan timing change. Existing planning
identities and tool schemas remain unchanged; the new policy has a distinct timing
contract in model/tool identity, envelope and evaluator manifest. Source observations
come from public journal results; no new tool, planning phase or submission gate is added.
The broad local sweep recorded timing/Git execution failures; unchanged-code rechecks
passed. Exact validation results and local/live limits are in the implementation record.

Declaration expansion and independent-candidate diagnostics remain optional; their
closed comparisons did not establish better acceptance or justify default adoption.
H's prepared probe dependencies support offline imports, but no model probe occurred
in this timing comparison. The agent runtime was frozen throughout collection.

Evidence for targeted lookup:

- Current implementation: [first plan after source](history/2026-09-26-after-source-planning.md).
- Latest result: [first-plan timing comparison](history/2026-09-27-after-source-planning-comparison.md).
- Detailed protocol, metrics and closure: `C:\pt\analyses\planning-after-source-compare-20260927-v1`.
- Separate prior result: [planning ON/OFF comparison](history/2026-09-26-planning-off-comparison.md).
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
