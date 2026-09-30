# MontePy v2 fresh repair result

Completed 2026-09-30 on merged head `3f29be10218f4d454aed06c0fbcd6618b70748e0`.
One user-authorized paid invocation; allocation closed. official=false,
claim_eligible=false. No retry, continuation, second sample or runtime change.

## Scope and result

Task `original-montepy-933`, version 2, dev-train; upstream base
`fbc03d10eb552cf82acc788ef70d120adec8130c`. The user approved the exact
[prepared scope](../../.agent/next-montepy-repair.md): gpt-5.4-2026-03-05, xhigh,
25,000 desired output tokens, one invocation, USD 3.00 cap, 40 model calls,
100 tools, four edits and 1,800 seconds. Selected baseline policies were unchanged.
Credentials came from the authorized repository-local ignored `.env` file.

| Measure | Observed result |
| --- | --- |
| Terminal | EVALUATOR_PASS |
| Isolated task acceptance | PASS |
| Evaluator safety state | PASS |
| Public regression | 44 passed; complete output; cleanup confirmed |
| Model / input-count calls | 12 / 12 |
| Tool actions / accepted edits | 18 / 1 |
| Submitted scope | montepy/cell.py only; 16 added lines, zero deleted |
| Active elapsed time | 251.479 seconds |
| Usage-accounted cost | USD 0.594456 of the USD 3.00 cap |
| Optional run_probe calls | 0 |

The agent inspected the public implementation, added a None-handling branch to
the Cell.universe setter and a deleter delegating to that path, ran the registered
public regression and submitted. The branch clears a standalone assignment or
selects/creates problem universe zero and resets the truncation flag. This describes
the submitted patch, not a new operator-authored repair or an exhaustive API proof.

## Verification and evidence boundaries

The runtime/task inputs were clean at dispatch. Exact prepared public source and
dependency descriptor hashes and existing image identities were revalidated.
No Docker start, image pull/build or prior solution/private context was provided.
The prepared source still verifies unchanged after execution.

All 12 dispatches have matching completed responses and input counts, no reported
usage/count/transport uncertainty, and costs summing exactly to the terminal value.
This is provider-usage accounting under runtime prices, not invoice reconciliation.
The journal chain (193 events), all six terminal artifact hashes, and all 12 actual
model inputs passed read-only verification. The preparation-delivery audit confirms
prepared-source metadata and host preparation paths are absent from those inputs.

Public regression passing is separate from isolated task acceptance and safety.
The public changed-line report was `unknown / report_unavailable`, so it does not
prove execution of the newly added branches. No optional probe was used. Private
evaluation verdict/provenance were retained outside the model loop; no hidden
test content or reference solution was supplied to the coding agent.

Run: `run_dev_6d1fff8c7e6d4823` under
`C:\pt\runs\montepy-next-repair-20260930-v1`.
Operator scope/review: `C:\pt\analyses\montepy-v2-fresh-repair-20260930-v1`,
append-only journal `run_dev_montepyv2audit`, with content-addressed review and patch.
Submitted patch hash:
`sha256:a9fc3e62d322a9eb106ac186a4889258623f4f4668865d7a0f473c53f4ed91dc`.
Run journal tail:
`sha256:df5cfc1a6aaf1a9724f09b4e9f4bfda93237c2a2976d0ab3f8d7ce8419b81d3c`.

## Decision

This previously exposed development task demonstrates one successful fresh
repair/check/submission path. It is not a held-out result, a causal comparison,
evidence of memory benefit or proof of general repair-quality improvement.
The invocation found no new runtime failure warranting a feature or prompt change.
Retain the baseline and close this allocation; any next task or experiment requires
its own concrete scope. Runtime regression and mock smoke were not rerun for this
result-only documentation change; the preceding merged runtime's CI remains separate.
