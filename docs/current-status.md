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

The cost-matched independent-candidate comparison is complete: direct reconsideration
A 0/2, independent generation plus comparison B 0/2. All four final runs submitted
their saved seeds unchanged after the required checks; no read/search tool call,
probe or new edit occurred in those final runs. Both intermediate fresh generations
also submitted and failed acceptance. All 32 actual inputs and count/dispatch records
were audited; the exact alternatives reached every B request.

Pydantic's fresh generation already reduced the provider-specific applicability
requirement to field-mode configuration in its first plan. Subsequent source work
correctly found the shared serializer/replay owner, but its edit omitted a separate
provider-requirement discriminator. Checks passed, and their ordinary default-mode
provider example was treated as confirming preservation more broadly. The same scope
error therefore appears without an imported candidate and before any context summary.
This weakens an explanation based only on seed anchoring or lost memory; it does not
prove the cause of every acceptance failure.

Keep the independent-candidate diagnostic optional. No improvement was observed in
this sample, and neither generated alternative passed, so the receiver's ability to
use a correct alternative remains unresolved. Prioritize the first translation of
public applicability requirements into executable conditions, separately from format
settings. Use this public sequence and earlier condition/case-design evidence before
adding another generic planning instruction, comparison gate or paid experiment.

H's missing-import capability gap is resolved for this prepared environment: an
opt-in adapter statically reads literal setup.py runtime requirements and reuses the
existing public wheel resolver/offline installer. An exact-base, network-free Docker
canary imports requests and the actual Xet module. The original source and existing
image remain intact. No model probe occurred in this comparison, so improved import
availability is not itself an observed task-solving improvement.

## Implemented and measured

The optional `alternative` argument on the seeded diagnostic admits only exact public
patch/hash/base data from a separately verified producer. It supplies generic comparison
guidance, not an applied patch, editable-source evidence, previous notes/actions or
evaluator results. The imported seed still consumes one mutation slot. Omission keeps
the previous path; system/planning prompts, registered tools, finish/check gates,
continuation and isolated evaluation remain unchanged. Core runtime stays `4d2fc8ba`.

Focused checks, related regression, Ruff and two isolated evaluation mocks passed.
Both context policies delivered public task/diff/check state and the alternative.
The full core suite was not rerun because core files did not change; local mock and
real Docker import results remain distinct from live task acceptance.

The live group used $1.9097295 of its $9.60 cap; billing was settled and there was no
infrastructure stop or limit-based terminal. HG used all four mutation slots and had
two late output ceilings reduced by remaining cost. B had separate generation and
comparison phases, so equal total caps did not equal aggregate call/time opportunities.
Unused funds are closed; no retry, replacement, resume, extension or default adoption.

Evidence locations for targeted lookup:

- Current result: [independent candidate comparison](history/2026-09-26-independent-candidate-comparison.md).
- Detailed packet: `C:\pt\analyses\independent-candidate-compare-20260926-v1\result.md`.
- Contract: [independent candidate](../.agent/independent-candidate.md).
- Local validation: `C:\pt\validation\independent-candidate-20260926-v1\result.md`.
- Preceding public contrast: [diagnostic claims verification](history/2026-09-26-diagnostic-claims-verification.md).
- Earlier recommendation removal: [completion advice comparison](history/2026-09-26-completion-status-comparison.md).
- Earlier decisions and closed evidence: [documentation history](history/README.md).

## Reading and updating this page

At task start, read this page and the relevant implementation/operation section.
Search history only when a named failure, decision, or evidence gap needs it; read
the matching passage rather than whole snapshots. Historical "current", "latest",
"next", commands, and approvals describe their original checkpoint only.

Replace stale status here. Record a significant completed investigation once in
`docs/history/`, then keep only its current implication and evidence link here.
Do not append run-by-run results, validation totals, or superseded plans to this page.
Documentation size limits are checked by `tests/test_documentation_layout.py`.
