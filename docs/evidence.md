# Evidence and limitations

## Current local evidence

On 2026-09-01, after the Rapid Dev Reset:

- `uv run ruff check patchloop tests` passed.
- The locked fast suite passed 26 tests in 10.46 seconds after documentation consolidation.
- Mock end-to-end reached `EVALUATOR_PASS` after parallel inspection, one mutation,
  a visible check, automatic diff projection, finish, and isolated evaluation.
- Task-loader identity hashes remained stable for representative smoke,
  `dev-train`, and held-out task packages.
- Active legacy Rapid/import references were absent.
- The visible-doc allowlist, hidden agent guide, and current local Markdown links
  are enforced by the fast suite.
- The reset changed no tracked bytes under `reports/`, `experiments/`, or
  `docs/archive/` relative to checkpoint `b71ddeee`.

These are local observations, not provider or claim results.

## Not executed

- no OpenAI generation or provider input-count request
- no Docker command, image inspection, pull, build, or container run
- no remote repository fetch
- no live `dev-train` row
- no claim, qualification, activation, adoption, or held-out evaluation

The under-two-minute validation target is locally supported. The 30-minute live
target remains unverified.

## Known limitations

- The price registry accepts only reviewed model IDs; unknown models fail closed.
- Input counting and generation are separate provider operations. Timeout after
  either boundary can make billing uncertain, so the invocation stops.
- Digest and requested sandbox policy are recorded, but they are not host-level attestation.
- Mock fixtures do not prove remote checkout, provider schema acceptance, model
  behavior, or production billing.
- The evaluator currently records literal safety PASS after constrained execution
  and static policies, so development results are not official claim evidence.
- Long-horizon memory is disabled; only bounded current-run public evidence is projected.
- Deleted historical executables require Git history to replay.

A development PASS does not establish comparative quality, generalization,
causality, or memory benefit. A future confirmatory lane needs separate frozen
contracts and authority.

## Historical audit

Checkpoint `b71ddeee` preserves the secret-scanned pre-reset tree. Historical
results remain under `reports/` and `experiments/`; historical narrative remains
under `docs/archive/`. Verify their tracked bytes with:

```powershell
git diff --name-only b71ddeee -- reports experiments docs/archive
```

Expected output is empty.
