# PatchLoop documentation

Current guidance and historical evidence have different reading paths.

| Need | Read |
| --- | --- |
| Current priority, baseline, unresolved problem | [Current status](current-status.md) |
| Product goals and architecture | [Product](product.md) |
| Run, validate, prepare, or resume | [Operations](operations.md) |
| Interpret results and claim limits | [Evidence](evidence.md) |
| Change an implementation contract | [Internal guide](../.agent/guide.md), then relevant source/tests |
| Explain a particular past decision or failure | [History index](history/README.md), then a matching passage |

Start with current status. Read other material only for the task at hand; do not
concatenate this directory, the internal guide, and history into every task.
Source code owns behavior. Current status owns current priorities. History records
what was observed or decided at a prior checkpoint, including superseded proposals.

## Maintenance

Current documents are edited in place. Replace stale statements and keep only
decision-relevant facts with evidence links. Significant completed investigations
go once into a dated entry under `docs/history/`; old run narratives do not grow
inside the current status, product, operations, or internal guide.

The documentation tests bound current document sizes and verify active links and
the preserved migration snapshots. Move detail to the right existing location
instead of routinely raising a limit or creating mandatory process paperwork.

Existing `docs/archive/`, `reports/`, and `experiments/` remain immutable. Task-local
audit files stay beside their data. Generated run state remains outside the repository.
The root [AGENTS.md](../AGENTS.md) contains contributor instructions.
