# Current evidence

## Implemented and locally executed

On 2026-09-01, after the reset implementation:

- `uv run ruff check patchloop tests` passed.
- `uv run pytest tests --basetemp <short-external-path> -p no:cacheprovider`
  passed 23 tests in 10.03 seconds in the final locked verification.
- The mock end-to-end test completed parallel read/search, one admitted mutation,
  a visible check, automatic diff projection, finish, separate private evaluation,
  and `EVALUATOR_PASS`.
- Task-loader identity checks retained the pre-reset hashes for a smoke v1 task, a
  dev-train v1 task, and a held-out private-v2 task.

These are current local observations, not historical or provider results. A final
verification run may report a slightly different wall time while the pass/fail
claim remains the same.

## Preserved checkpoint

Checkpoint commit `b71ddeee` records the secret-scanned pre-reset non-scratch tree.
Historical executable code can be recovered there. The current reset must leave
Git-tracked bytes under `reports/`, `experiments/`, and `docs/archive/` unchanged
relative to that checkpoint.

## Not executed

- no OpenAI/provider request
- no provider input-count request
- no Docker command, image inspection, pull, build, or container run
- no remote repository fetch
- no live `dev-train` row
- no claim, qualification, activation, adoption, or held-out evaluation

Therefore the two-minute focused-validation target is locally supported, while the
30-minute live operational target is still pending. No quality, generalization,
causal, or memory-benefit conclusion is authorized.
