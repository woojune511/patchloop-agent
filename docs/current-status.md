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

Public evidence now isolates a concrete Pydantic scope error. With the field-mode
trigger fixed, the failed seed inserts an empty field for ordinary profiles as well
as profiles carrying the provider requirement. A new four-case public contrast on
three independent workspaces found: base preserves ordinary profiles but misses
required insertion (2/4); seed supplies insertion but breaks preservation (2/4);
the earlier fresh-solve GPT-5.4 patch satisfies both (4/4). These are operator-chosen
public probes, not new acceptance results or a model-improvement experiment.

P-B's two source reads and source-linked note reached its actual inputs through
submission. Its checks passed on the unchanged seed, but their inputs did not cover
ordinary field-mode tool-only messages. Edit/probe tools and substantial budget
remained. Missing note delivery, missing probe dependencies and exhausted tool
budgets were not observed in P-B. Delivery still does not establish effective use.

H has a separate capability gap: its recorded probe environment lacks prepared
dependencies. A new exact-base import attempt fails on missing requests. Neither H
run in the completion-advice comparison attempted a probe, so this is not a proven
cause of those choices. Standard-library probes remain available; P's prepared
dependencies verify and its public serializer executes successfully.

Prioritize deriving applicability and expected preserved behavior from the public
requirement independently of the candidate's predicate, then selecting a check that
distinguishes them. Keep the baseline fixed. The same full model produced a correct
fresh repair and accepted an incorrect seeded repair, but seed state, framing,
guidance and sampling differ; anchoring is a hypothesis, not an established cause.
No new method, default or paid comparison is selected by this audit.

## Implemented and measured

The seeded diagnostic now accepts optional `completion_guidance_policy="status-only-v1"`.
It changes only the recommendation and message for check-needed/submission-ready
stages. Failure/repair guidance, prompt, tool admission, check gates and budgets
remain intact. Other supplemental review/feedback interventions cannot be combined
with it. Omission preserves the existing path; common runtime remains `4d2fc8ba`.

The closed completion-advice comparison remains A 0/2, B 0/2: all seeds submitted
unchanged after required checks passed. Its 13 actual inputs, tool schemas and
environment identities were reverified. This intervention did not improve acceptance;
the optional diagnostic is not a baseline or CLI default.

The separate follow-up used four new public probes and zero provider/count calls or
private evaluations. Fresh-solve historical evidence favors the full model over mini
on two tasks (2/2 versus 0/2), but conditional rescue examples and the seeded failures
do not support either "only model upgrades help" or a general method efficacy claim.

Current guidance is bounded and old snapshots remain byte-exact. Reduced document
size is measured; actual input-token, latency, contamination and quality effects are
not measured. Historical reports and unused paid allocations remain closed.

Evidence locations for targeted lookup:

- Current verification: [diagnostic claims](history/2026-09-26-diagnostic-claims-verification.md).
- Verification packet: `C:\pt\analyses\claims-verification-20260926-v1\result.md`.
- Prior result: [completion advice comparison](history/2026-09-26-completion-status-comparison.md).
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
