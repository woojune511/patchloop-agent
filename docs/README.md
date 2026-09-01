# PatchLoop documentation

This directory is intentionally human-facing. There are four current documents:

1. [Current status](current-status.md) — the shortest authoritative snapshot
2. [Product and architecture](product.md) — product boundary and runtime composition
3. [Run and validate](operations.md) — commands and execution boundaries
4. [Evidence and limitations](evidence.md) — observations, gaps, and prohibited claims

If you read only one document, read [Current status](current-status.md). Source
code owns runtime behavior; that status page owns the current operational summary.

## Historical material

`docs/archive/` is preserved audit history. It is not current guidance. Exact
historical IDs and hashes live with artifacts under `reports/` and
`experiments/`. Task- and fixture-specific `audit.md` or `README.md` files stay
beside the data they describe. Archived links may refer to the historical tree;
use their recorded commit when an old active path no longer exists.

Contributor automation instructions remain in the required root `AGENTS.md`.
Agent-only implementation detail is intentionally kept outside this visible docs
set.
