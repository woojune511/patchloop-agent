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
- After the first-live diagnosis, the context-projection checkpoint passed Ruff,
  29 tests in 16.45 seconds, and mock `EVALUATOR_PASS`. This is local evidence only.
- The reset changed no tracked bytes under `reports/`, `experiments/`, or
  `docs/archive/` relative to checkpoint `b71ddeee`.

These are local observations, not provider or claim results.

## First live development observation

On 2026-09-02, one separately approved row used:

- task `loguru-invalid-format-feedback` from the checked-in `dev-train` split
- model `gpt-5.4-mini-2026-03-17` with medium reasoning
- one repetition under a $1.20 invocation-wide cap
- external state root `C:\patchloop-live-20260902-loguru-r1`

Run `run_dev_e89e940c0715474e` wrote a valid 455-event hash chain ending at
`sha256:36a3e266f769197203f04870d49e92411a62bbcf7cc7daf43bc97af250167f9a`.
It reached `LIMIT_REACHED` (`tool-action limit reached`) in 141.147 seconds.
All 39 provider calls completed with the requested model and no unmatched call
start. Recorded usage was 91,907 input tokens, including 17,408 cached tokens,
and 4,866 output tokens, including 1,384 reasoning tokens. Recorded cost was
$0.07907685.

The agent made 76 searches and 23 reads, all successful, but used only 26 distinct
action input hashes. One successful `KeyError` search repeated 33 times and one
successful `format(` search repeated 18 times. No plan, edit, check, mutation,
submission, artifact, or evaluator result was produced. This is live development
evidence of a context-projection failure expressed as duplicate inspection, not
task correctness or quality evidence.

## Not executed

- no second repetition, transport retry, or follow-up paid run
- no image pull, image build, or automatic Docker Desktop start
- no mutation, visible check, submission, private evaluator, or evaluator container
- no claim, qualification, activation, adoption, or held-out evaluation

The under-two-minute validation target is locally supported. A durable live terminal
was observed within 30 minutes, but the full operational target remains unverified
because no evaluator summary was reached.

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
