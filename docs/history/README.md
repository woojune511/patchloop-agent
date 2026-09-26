# Documentation history

History is retained evidence, not current instructions or a queue of next actions.
Start at [current status](../current-status.md). Consult history for a named problem,
decision, or evidence gap, and read only the matching passage. Old "current",
"latest", "next", example commands, and approvals apply to their original checkpoint.

## Pre-split snapshots: 2026-09-26

Migration decision, measurements, and validation:
[separating current guidance from history](2026-09-26-documentation-separation.md).

These five files preserve the exact bytes of the active documents immediately before
current guidance and accumulated history were separated. The
[manifest](2026-09-26-context-split/manifest.json) records original paths, sizes, line
counts, and SHA-256 digests. They include obsolete statements alongside observations;
no historical claim becomes current through this migration.

| Snapshot | Useful lookup topics |
| --- | --- |
| [Current status](2026-09-26-context-split/current-status.md) | Paired observation, public evidence IDs, value-origin review, model baseline, prior run decisions |
| [Internal guide](2026-09-26-context-split/agent-guide.md) | Earlier implementation decisions, contract evolution, per-version validation |
| [Evidence](2026-09-26-context-split/evidence.md) | Early development observations, failures, local checks, original claim boundaries |
| [Operations](2026-09-26-context-split/operations.md) | Closed pilots, old invocation examples, prior preparation procedures |
| [Product](2026-09-26-context-split/product.md) | Earlier feature descriptions and architecture narrative |

Search first, then read a bounded range around a matching heading. For example:

```powershell
rg -n '^## .*paired|^## .*value-origin' docs/history/2026-09-26-context-split/current-status.md
Get-Content docs/history/2026-09-26-context-split/current-status.md | Select-Object -Skip <line-before-match> -First 60
```

Relative links inside byte-exact snapshots retain their original spelling and
original base directory from the manifest. They are not maintained as current
navigation; use the active docs, original path, or recorded Git revision when needed.

## New records

- [2026-09-26: first interpretation and source questions](2026-09-26-first-interpretation-audit.md):
  equal fresh inputs, different pre-edit questions, and limits of source-context explanations.
- [2026-09-26: independent candidate comparison](2026-09-26-independent-candidate-comparison.md):
  offline HF imports, cost-matched generation/comparison, and repeated first-plan scope reduction.
- [2026-09-26: diagnostic claims verification](2026-09-26-diagnostic-claims-verification.md):
  actual input audits, four public probes, profile-scope regression, and causal claim limits.
- [2026-09-26: completion advice comparison](2026-09-26-completion-status-comparison.md):
  four completed runs, additional P-B reading, and unchanged acceptance after recommendation removal.
- [2026-09-26: first-input completion advice diagnostic](2026-09-26-completion-status-diagnostic.md):
  opt-in recommendation removal, unchanged runtime gates, and local delivery validation.
- [2026-09-26: verification scope audit](2026-09-26-verification-scope-audit.md):
  first-plan narrowing, actual public check inputs, and limits of the guidance hypothesis.
- [2026-09-26: paired-reference comparison](2026-09-26-paired-reference-comparison.md):
  admitted declarations, unchanged seeded candidates, and the completion-guidance question.

Add one short dated Markdown entry for a significant completed investigation, with
problem, evidence, hypothesis, change, result/limits, and the unresolved question.
Link detailed external run artifacts rather than copying them. Routine edits need
no new record. Never rewrite a closed record to reflect a later interpretation;
add a separate correction or follow-up and update the current implication instead.

Keep current status replaceable and bounded. This index is for locating records,
not for copying every result into another growing narrative. Existing legacy
`docs/archive/`, `reports/`, and `experiments/` remain unchanged and are also historical.
