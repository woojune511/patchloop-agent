# Current limitations

This file separates implemented behavior from the remaining 12-week campaign work.

## Implemented and measured locally

- Three audited `mini-data-utils` smoke tasks with independent snapshot hashes
- Reviewed reference and known-bad evaluator paths for every smoke task
- Official Linux Docker evaluator smoke: reference accepted, six bad patches rejected
- Docker network denial, non-root UID, read-only workspace and host-secret non-forwarding checks
- Offline mock-agent end-to-end run
- Worker-kill recovery with duplicate-mutation assertion
- One-run offline experiment and raw-derived report
- Unit/integration/recovery/viewer route tests

## Implemented but not yet accepted as an external gate

- OpenAI Responses adapter is contract-tested with a fake client; no paid live model call was made.
- Memory build/retrieval/freeze contracts exist; a real reviewed dev-train index still requires dev traces
  and an exact embedding revision.
- GitHub adapters exist; no Issue was imported and no Draft PR was created in this session.
- HTMX is pinned from a CDN; fully offline viewer packaging would require vendoring the BSD asset.

## Dataset and campaign not yet produced

- The planned 3 smoke, 6 dev-train, 2 dev-validation and 6 same-repo held-out packages are incomplete.
- The six `python-tabulate` tasks remain `pending-audit` in `data/oss-candidate-ledger.csv`.
- No 96-run OpenAI campaign, cost measurement, negative-transfer review or cross-repo result exists.
- Consequently, no portfolio performance claim beyond the single offline smoke should be made.

These are deliberate hard gates. The repository rejects an incomplete core experiment manifest instead of
silently lowering the design or fabricating missing results.
