# PatchLoop Agent Guide

This file applies to the entire repository. Historical milestone material under
`docs/archive/` is audit evidence, not current implementation guidance.

## Mission

Build a reliable single coding agent with a fast public development loop. The
agent is the product. Task loading, constrained tools, recovery state, sandboxing,
and private evaluation are supporting layers.

## Active state

- `dev-head` is the only coding-agent runtime and is intentionally mutable.
- Work Item 87 candidate preparation is abandoned. Do not create a new Work Item,
  candidate, qualification, activation, adoption, or rehearsal artifact for a
  normal development change.
- Legacy Rapid and provider-backed claim commands are removed. Historical runs
  and archived bytes are immutable and must not be edited or relabeled.
- Memory is disabled. `dev-validation` and held-out splits are not development
  tuning inputs.
- Every new run is `official=false`. No current result supports a quality,
  generalization, or memory-benefit claim.

## Required reading

Read only what the change needs, in this order:

1. `docs/00-index.md`
2. `docs/current-status.md`
3. One or two relevant documents:

| Change | Documents |
| --- | --- |
| agent, state, tools | `docs/02-architecture.md`, `docs/03-contracts.md` |
| task, evaluator, schema | `docs/03-contracts.md`, `docs/04-evaluation-protocol.md` |
| next implementation | `docs/05-implementation-plan.md` |
| decision or boundary | `docs/06-decisions.md` |
| validation or operation | `docs/07-reproduction.md` |
| review or claim language | `docs/08-limitations.md`, `docs/09-evidence.md` |

## Hard gates for the development lane

1. Keep public task material separate from private specs, hidden tests, reference
   patches, and evaluator details. Never project private material into agent context.
2. Expose only registered reads, searches, mutations, visible checks, and finish;
   never give the agent an unrestricted shell.
3. Store generated state outside the PatchLoop repository in append-only,
   hash-chained `dev-run-v1` JSONL.
4. Require `action_id + input_hash` for idempotent mutation and check recovery.
5. Live OpenAI runs require an explicit `dev-train` task, model, credential file,
   positive invocation-wide cost cap, and repetition count. The exact invocation
   is its development authority; do not broaden it.
6. Check cost immediately before provider dispatch using actual counted input and
   a conservative output reservation. Use zero SDK retries and stop repetitions
   on count, transport, or billing uncertainty.
7. Inspect a required local evaluator image once before live work. Never pull,
   build, start Docker Desktop, or install prerequisites automatically.
8. Preserve historical `experiments/`, `reports/`, and `docs/archive/` bytes.
9. Distinguish implemented, locally tested, live-executed, and claim-producing
   evidence. Never invent or promote a result.

Exact candidate/hash/rehearsal rules belong only to a future confirmatory lane.
They are not development-lane gates and must not be reintroduced incidentally.

## Workflow

1. State the smallest behavior change and its failure boundary.
2. Implement directly on `dev-head` with a small feature commit.
3. Run the focused test, then Ruff, the fast suite, and mock smoke as relevant.
4. Verify no private projection, in-repository run state, live call, Docker action,
   or historical artifact mutation occurred.
5. Report commands actually run and work deliberately not run.

## Definition of done

- Success and important failure paths are covered by the fast suite.
- Focused validation remains under two minutes.
- Public/private, allowed-path, cost-cap, and append-only boundaries remain enforced.
- Mock smoke completes read, mutation, visible check, automatic diff, finish, and
  isolated private evaluation.
- Live operational acceptance is claimed only after an explicitly authorized
  one-row run leaves a durable terminal and evaluator summary within 30 minutes.
- No quality or generalization claim is made from development results.

## Active source boundaries

```text
patchloop/dev/         mutable orchestration, tools, context, cost, and journal
patchloop/agent/       provider adapter only
patchloop/sandbox/     registered local/Docker checks
patchloop/verifier/    isolated private evaluator and static policy
patchloop/state/       active journal export
tasks/                 audited public/private task packages
fixtures/              audited local repository snapshots
experiments/ reports/  immutable historical artifacts
docs/archive/          immutable historical documentation
```
