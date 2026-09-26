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

The retrospective Pydantic comparison now contrasts a successful fresh GPT-5.4 xhigh
run with the recent failed fresh generation. Twenty actual inputs were reverified.
Model and selected controls match; the initial inputs match after removing measured
preparation time and its derived segment identity. This is a selected historical
pair, not a controlled causal comparison or a new success-rate sample.

The successful first plan was also incomplete. At call 2, before receiving fuller
profile source, its public read question explicitly considered reusing existing
configuration versus adding an optional profile setting. It then read the declaration,
format documentation and provider construction, and implemented a separate applicability
condition. The failed run retained provider-preservation words but sought only format
settings and the shared serializer; its edit used field mode alone. Both passed the
same checks without a discriminating probe. Success therefore demonstrates the observed
implementation distinction, not better verification selection or a benefit from more reading.

Prior factorized case design, frozen expectations and source supplementation did not
establish improvement. Earlier failures sometimes already had the field-format docs.
Do not add a planning template, mandatory review or broader search output on this evidence.
Keep the independent-candidate diagnostic optional: its closed A 0/2 versus B 0/2
comparison also did not improve acceptance, and neither generated alternative passed.

The optional declaration-context diagnostic is implemented for fresh dev runs. In the
first tool batch, it expands an already matched Python module/class data declaration
through its adjacent literal documentation, subject to existing search output limits
and a 40-line span bound. The original search hits, public boundary, evidence accounting,
prompt, schemas and finish gates remain intact. Omission uses the existing runner.

An offline replay of PG's four initial searches matches the historical source outputs.
Only the profile declaration query changes: it gains 12 source lines, including the
format documentation, without removing previous lines. This is source delivery evidence;
it does not show a better question, edit or acceptance result. The saved-search preview
is not a hydrated historical checkpoint. A separate checkpoint sampler now reconstructs
the saved post-search request and retains its first plan, native continuation and budgets.
A must match the original; B recomputes only source-derived context after the generic
expansion. It reuses the bounded one-response collector for A1/B1/B2/A2. Selected tools
are not executed, so a later edit and task acceptance remain outside this diagnostic.
No paid comparison or new live allocation exists. The next decision is whether immediate
public questions change under this fixed input intervention. This belongs to the earlier
information supplement family; local/mock validation does not justify default adoption.

H's missing-import capability gap is resolved for this prepared environment: an
opt-in adapter statically reads literal setup.py runtime requirements and reuses the
existing public wheel resolver/offline installer. An exact-base, network-free Docker
canary imports requests and the actual Xet module. The original source and existing
image remain intact. No model probe occurred in this comparison, so improved import
availability is not itself an observed task-solving improvement.

## Implemented and measured

The declaration diagnostic's focused validation includes A/B mocks in both append-v1
and segmented-v1, reaching edit/check/submit/isolated evaluation and checking actual input
delivery. The scope, replay/cache and mutation-evidence contracts are covered. The old
runtime hash remains unchanged because the adapter is optional diagnostic code.

The frozen checkpoint collector has separate local evidence for exact input restoration,
unchanged first plan/continuation, source-dependent projection and shared collection stops.
Its scripted responses test the collector, not autonomous question selection or acceptance.

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

- Current implementation: [declaration context](../.agent/declaration-context.md).
- Frozen decision contract: [checkpoint sampler](../.agent/declaration-checkpoint.md).
- Checkpoint implementation: [frozen declaration decision](history/2026-09-26-declaration-checkpoint-sampler.md).
- Prepared comparison: `C:\pt\analyses\declaration-checkpoint-20260926-v1\result.md`.
- Implementation record: [declaration-context diagnostic](history/2026-09-26-declaration-context-diagnostic.md).
- Source preview: `C:\pt\analyses\declaration-context-preview-20260926-v1\result.md`.
- Local validation: `C:\pt\validation\declaration-context-20260926-v1\result.md`.
- Current audit: [first interpretation and source questions](history/2026-09-26-first-interpretation-audit.md).
- Detailed audit: `C:\pt\analyses\pydantic-first-interpretation-audit-20260926-v1\result.md`.
- Latest live result: [independent candidate comparison](history/2026-09-26-independent-candidate-comparison.md).
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
