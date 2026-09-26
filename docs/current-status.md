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

The first-input completion-advice comparison completed four seeded runs with
GPT-5.4 xhigh: acceptance A 0/2, B 0/2. A kept ordinary guidance; B removed its
check/submit recommendations from the first input. Every run passed both required
public checks and submitted its seed unchanged. No resource or infrastructure
stop contributed to the result. This intervention did not improve acceptance.

P-B added two source reads before checking. It accurately described the candidate's
field-mode predicate and DeepSeek's settings, then treated that as sufficient scope
for the change. The public task separately preserves ordinary profiles unless they
carry the provider-supplied requirement. No contrasting profile probe or new repair
followed. The finding remained present through submission; this is not observed
loss of the read result or note. H showed the same check/check/submit sequence in
both arms, without new inspection of the endpoint-preservation distinction.

The remaining target is evidence selection: distinguish the public requirement's
applicability from the existing candidate's predicate, then choose a check that can
separate them and use its result to revise the repair. Extra reading, reminders or
note retention alone are not the target. Keep the baseline fixed; the two advice
fields were insufficient in these samples, but other completion cues, seeded
framing and sampling variation remain unresolved. No new mechanism or paid group
is selected by this result.

## Implemented and measured

The seeded diagnostic now accepts optional `completion_guidance_policy="status-only-v1"`.
It changes only the recommendation and message for check-needed/submission-ready
stages. Failure/repair guidance, prompt, tool admission, check gates and budgets
remain intact. Other supplemental review/feedback interventions cannot be combined
with it. Omission preserves the existing path; common runtime remains `4d2fc8ba`.

Local mock/regression validation established delivery and compatibility. The live
comparison now verified all 13 actual inputs; B's projection reached all seven B
inputs. Source reads/searches/probes remained available throughout. The extra P-B
reading is an observed behavior difference, not a demonstrated accuracy gain or a
reliable causal effect from one sample per task/arm.

Recorded cost was $0.599650 of $4.80; cache-neutral equivalent was $0.881890.
Unused allocation is closed. There were no retries, extra samples, post-submission
candidate executions or hidden-detail audits. The optional diagnostic remains
available; it is not adopted as the performance baseline or a CLI default.

Evidence locations for targeted lookup:

- Current result: [completion advice comparison](history/2026-09-26-completion-status-comparison.md).
- Detailed packet: `C:\pt\analyses\completion-status-compare-20260926-v1\result.md`.
- Implementation: [completion advice record](history/2026-09-26-completion-status-diagnostic.md)
  and [contract](../.agent/completion-status-diagnostic.md).
- Local validation: `C:\pt\validation\completion-status-20260926-v1\result.md`.
- Earlier comparison: [paired-reference record](history/2026-09-26-paired-reference-comparison.md).
- Follow-up analysis: [verification scope audit](history/2026-09-26-verification-scope-audit.md).
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
