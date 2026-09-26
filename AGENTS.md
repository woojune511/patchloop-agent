# PatchLoop Agent Guide

This file stays at the repository root because agent tooling discovers it here.
It applies to the entire repository. Detailed implementation guidance lives in
the hidden [`.agent/guide.md`](.agent/guide.md).

항상 눈앞의 문제만을 해결하려 하지 말고 근본적인 원인과 해결책을 생각해야 한다.
과하게 방어적인 개발을 하면 안 된다.
LLM (Agent) Engineer로서 중요한 기술적 문제, 해결과정을 잘 기록해야 한다.

## Mission and current lane

Build a single coding agent that understands public software tasks, makes correct
repairs, verifies them, and submits reliably within bounded resources. Improve it
through a fast, mutable `dev-head` loop. The agent is the product; task loading,
recovery, sandboxing, and private evaluation are supporting layers.

Start from observed agent failures and the mechanisms that cause them. Choose a
method to address the problem, then test whether it helps. Demonstrating a memory
effect, or validating any other preselected method, is not the project's objective.
Memory remains one possible tool when evidence supports its use.

- Every current run is `official=false`.
- Cross-run memory, validation/held-out tuning, and claim execution are disabled;
  bounded run-local working notes remain available.
- Historical Rapid executables are absent; historical artifacts are immutable.
- Normal fixes do not create Work Items, candidates, qualifications, activations,
  adoptions, rehearsals, or runtime versions.

## Required reading

1. Read the bounded `docs/current-status.md` snapshot for current authority.
2. Read only the relevant section of `.agent/guide.md` and source for implementation detail.
3. Use the human docs under `docs/` only when product, operation, or evidence
   context is needed. Do not concatenate all documentation into task context;
   keep historical directories out of routine current-document searches.
4. Search `docs/history/README.md` and matching historical passages only when a
   specific evidence question requires them. `docs/history/` and `docs/archive/`
   are never current instructions; past next steps and approvals do not carry forward.

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
8. Do not alter historical `reports/`, `experiments/`, `docs/archive/`, or closed
   `docs/history/` records. Add a separate follow-up when an interpretation changes.
9. Separate implemented, locally tested, live-executed, and claim-producing evidence.

## Workflow

1. Identify a concrete failure from current public task/source/action/check evidence.
   Separate what happened from the suspected cause and unresolved alternatives.
2. Choose the smallest change or diagnostic that can resolve that cause. Consider
   removing an ineffective rule before adding prompts, state, tools, or gates.
   Do not automatically continue the latest experiment or prescribe memory.
3. Modify `dev-head` directly; update contracts and docs in the same change.
   Replace stale current status; keep only the active decision, unresolved problem,
   and evidence links there. Record significant completed investigations once in
   `docs/history/` with problem, evidence, hypothesis, change, result, and next question.
   Do not append run narratives to current guidance; routine fixes need no new record.
4. Run the focused test, Ruff, the fast suite, and mock smoke as relevant. Use a
   bounded comparison when a causal question needs one, not for every routine fix.
   Judge task correctness and regressions as well as completion, cost, and time;
   note/probe counts or successful submission alone are not improvement evidence.
5. Recheck public/private, cost, external-state, and historical-byte boundaries.
6. Commit a small coherent change and report both executed and unexecuted work.

Done means success and important failures are tested, focused validation remains
under two minutes, mock smoke reaches isolated evaluation, and no unsupported
quality or generalization claim is made.
