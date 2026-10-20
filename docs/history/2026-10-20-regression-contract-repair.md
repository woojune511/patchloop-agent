# Regression contract repair

Follow-up to [verification state separation](2026-10-20-verification-state-separation.md).
Base: `3bdb832bbda0d799fb7f18f669885a19340a9fc6`. Provider-free maintenance;
no new experiment, runtime version, paid allocation or repair-quality claim.

The earlier full regression exposed 80 failures that also reproduced before the
state-separation change. Leaving them inherited did not make the repository clean.
They included broken diagnostic execution, not merely old test snapshots. The
request was to repair them without relaxing verification or resource contracts.

## Causes and corrections

| Failed cases | Cause | Correction |
| --- | --- | --- |
| 37 | Two diagnostic `_run_probe` overrides did not accept the host's new reproduction binding; downstream reports stopped or lacked results. | Explicitly accept and forward the same binding. Keep declaration validation, execution failures and action recovery distinct. |
| 17 | Inline/OFF schemas removed replay inputs but retained replay instructions inside reproduction guidance. | Name that sentence separately and remove it only in inline/OFF projections. Retain all other reproduction guidance and inputs. |
| 13 | Full prompt exceeded existing 8,000/8,007-character assertions and frozen caller invariants. | Compress inspection prose from 8,553 to 8,000 characters; planning still totals 10,809. Preserve scope, uncertainty and verification instructions. |
| 13 | Exact schema/description identities and a field inventory predated reproduction support. | Pin the reviewed current shape and prose, retaining strict equality, ordering, nullability and historical-arm expectations. |

The first focused run passed 98/99. Fixing the full-prompt assertion exposed another
assertion in the same test: the memory schema was 4,003 bytes against a 4,000-byte
ceiling. Replacing “in an ordinary response” with “in a normal response” restores
4,000 bytes; its ordered validation structure is identical. No ceiling was raised.
A second run passed 99/100; the remaining explicit prompt hash in probe-policy
coverage was refreshed for the compressed prompt, retaining frozen-arm hashes.

Only two new execution cases were added, one per diagnostic adapter. Actual local
Python execution checks bound mismatch evidence, replay identity, same-action
idempotency, invalid-declaration rejection before execution and UNKNOWN requirement
coverage. Existing OFF tests additionally check that reproduction inputs and scope
warnings survive projection. Five cheap existing contract checks join the quick
selection; adapter coverage is already in its evidence-recovery file.

## Validation and boundaries

Durable packet: `C:/pt/regression-contract40/`. The append-only, hash-chained
`runs/run_dev_regressioncontract40.jsonl` records source, contract and result hashes.
Earlier failed checks remain in `focused1.xml` and `focused2.xml`. The initial quick
selection passed 116 tests in 61.94 seconds. Final focused checks passed 100 tests in
51.17 seconds; expanded quick selection plus isolated mock evaluation passed 121
tests in 64.82 seconds. Ruff passed for runtime, tests and diagnostics.
The first committed full run (`698d4368`) passed 5,462 cases, failed one and skipped
the existing 20 in 1,464.63 seconds; all original 80 failures passed. Its sole failure
was another literal protocol-guidance assertion that expected pre-compression
sentences. The correction retains the assertion, checks the new complete batching
and mode clauses, preserves historical-arm phrases and joins the quick selection.
No runtime source changed after that first full run. Its reports remain preserved.
After the literal correction, quick checks plus isolated mock evaluation passed
122 tests in 58.45 seconds; the targeted contract and documentation checks passed
six tests in 0.28 seconds. Ruff passed again before the final commit.

`validation.json` binds final results to the tested commit and tree.
`full-final2.xml` / `full-final2.txt` are the final-commit full-suite evidence; their
result is authoritative rather than a prediction embedded in this source commit.
The full command retains four workers, file grouping and zero worker restarts.

Segment transitions, two question references, source/input limits, action/edit/time
budgets, cost admission, recovery identities and private evaluation boundaries are
unchanged. The only working-notes source change is the three-byte description edit.
Historical evidence and the user's pre-existing `AGENTS.md` edit are preserved.
No test is removed, skipped, marked expected-failure or given a longer timeout to
clear these failures. Live provider execution and real evaluator runs are NOT_RUN.

This repairs local compatibility and restores existing size contracts. It does not
establish better requirement-to-test mapping or improved actual repair success.
