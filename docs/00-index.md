# Documentation index

## Authority order

1. Checked-in source code, task manifests and machine-readable artifacts
2. `docs/current-status.md`
3. Topic-specific active documents in this directory
4. Historical snapshots under `docs/archive/`

Archive prose explains how a decision was reached. It does not reopen an old gate or override current
code/artifacts.

## Active documents

| File | Owns |
| --- | --- |
| `current-status.md` | Current checkpoint, priority, next gates and closed authority |
| `01-project-spec.md` | Product question and durable scope |
| `02-architecture.md` | Effective runtime architecture |
| `03-contracts.md` | Current contract map and invariants |
| `04-evaluation-protocol.md` | Dataset roles, A/C readiness design and analysis rules |
| `05-implementation-plan.md` | Ordered remaining work |
| `06-decisions.md` | Effective decisions and open questions |
| `07-reproduction.md` | Supported offline validation commands |
| `08-limitations.md` | Claims that remain unsupported |
| `09-evidence.md` | Index into canonical machine artifacts |

## Documentation rules

- Exact IDs and hashes live in `reports/`; active prose links to them instead of copying them everywhere.
- Current checkpoint and next authority appear only in `current-status.md`.
- Milestone narratives do not accumulate in active topic documents.
- A superseded detail remains discoverable through the archive and Git history.
- New active documents should normally stay below 300 lines.

## Historical snapshot

The pre-reorganization D-121 documentation snapshot is under
`archive/snapshots/d121/`. Its manifest records original paths, sizes and SHA-256 values.
