# PatchLoop Agent Guide

This file stays at the repository root because agent tooling discovers it here.
It applies to the entire repository. Detailed implementation guidance lives in
the hidden [`.agent/guide.md`](.agent/guide.md).

## Mission and current lane

Build a reliable single coding agent through a fast, mutable `dev-head` loop. The
agent is the product; task loading, recovery, sandboxing, and private evaluation
are supporting layers.

- Every current run is `official=false`.
- Memory, validation/held-out tuning, and claim execution are disabled.
- Historical Rapid executables are absent; historical artifacts are immutable.
- Normal fixes do not create Work Items, candidates, qualifications, activations,
  adoptions, rehearsals, or runtime versions.

## Required reading

1. Read `docs/current-status.md` for current authority.
2. Read only the relevant section of `.agent/guide.md` for implementation detail.
3. Use the human docs under `docs/` only when product, operation, or evidence
   context is needed. `docs/archive/` is never current guidance.

## Hard gates

1. Never project private specs, hidden tests, reference patches, or evaluator
   details into agent context.
2. Expose only registered reads, searches, mutations, visible checks, and finish;
   never provide unrestricted shell access to the coding agent.
3. Keep generated state outside the repository in append-only, hash-chained
   `dev-run-v1` JSONL.
4. Preserve `action_id + input_hash` idempotency for mutation and check recovery.
5. Live OpenAI work requires an exact `dev-train` task, model, credential file,
   repeat count, and positive invocation-wide cap.
6. Count cost immediately before dispatch, use zero SDK retries, and stop all
   repetitions on count, transport, or billing uncertainty.
7. Never start Docker Desktop or pull/build an evaluator image automatically.
8. Do not alter historical `reports/`, `experiments/`, or `docs/archive/` bytes.
9. Separate implemented, locally tested, live-executed, and claim-producing evidence.

## Workflow

1. Define the smallest behavior change and failure boundary.
2. Modify `dev-head` directly; update contracts and docs in the same change.
3. Run the focused test, Ruff, the fast suite, and mock smoke as relevant.
4. Recheck public/private, cost, external-state, and historical-byte boundaries.
5. Commit a small coherent change and report both executed and unexecuted work.

Done means success and important failures are tested, focused validation remains
under two minutes, mock smoke reaches isolated evaluation, and no unsupported
quality or generalization claim is made.
