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
- The chosen performance baseline is `gpt-5.4-2026-03-05`, xhigh, 25,000 output tokens.
  The last live comparison used runtime checkpoint `4d2fc8ba` / tool surface v45.
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

The eight fresh planning ON/OFF solves are closed. Explicit planning (`brief-v1`)
produced acceptance 0/4; `none` produced 2/4. The difference is confined to Pydantic
(ON 0/2, OFF 2/2); HF Hub remained 0/2 in each arm. All eight submitted, passed safety
and completed evaluation, with no NOT_RUN or infrastructure stop. These are two selected
development tasks, not a general success-rate claim.

Both Pydantic ON runs used field format as the repair's applicability condition, even
while their plans mentioned preserving existing profile/provider behavior. Both OFF runs introduced an
optional profile requirement, enabled it in the provider-supplied profile, and used it
in serialization. All passed the same registered checks; none independently tested the
ordinary-profile preservation case. The observed improvement is repair scope, not proven
improvement in verification selection.

HF Hub public failures prompted caller-forwarding repairs in both arms. All four then
passed the public contract and regression checks but failed acceptance. A public-source
follow-up identifies an unexecuted concern about stored endpoint values losing whether
the caller explicitly supplied them; hidden failure causes were not inspected or inferred.

Keep planning OFF as a comparison candidate, with CLI defaults and the chosen working
baseline unchanged. The comparison toggled instructions, annotation schema, plan state
and review signals together. It does not isolate first-plan anchoring. The new opt-in
`brief-after-source-v1` delays the first plan request until source text is observed,
retaining later planning. It addresses both the instruction and actual review signal;
empty/failed reads and initial handoffs do not trigger planning. A voluntary early plan
remains valid. This timing condition does not establish sufficient understanding.

The next performance question is `brief-v1` versus `brief-after-source-v1` with the
same model, tasks and runtime. This timing option has no live efficacy result or new
paid allocation. Do not add another planning template, mandatory reviewer or task hint.

The group spent $5.988843 of $9.60; unused funds are closed. All actual inputs, usage,
journal chains and frozen files verified. OFF cost more and used more calls. Some HF
output ceilings shrank and one oversized candidate caused a segment transition; every
response completed and every run submitted. Resource differences remain separate from
claims about planning or continuity. No retry, replacement, resume or extension is active.

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
in this planning comparison. Working notes and xhigh reasoning stayed enabled in OFF.

Evidence for targeted lookup:

- Current implementation: [first plan after source](history/2026-09-26-after-source-planning.md).
- Latest result: [planning ON/OFF comparison](history/2026-09-26-planning-off-comparison.md).
- Detailed protocol, metrics and closure: `C:\pt\analyses\planning-off-compare-20260926-v1`.
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
