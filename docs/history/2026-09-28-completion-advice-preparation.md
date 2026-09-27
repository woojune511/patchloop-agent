# Offline completion-advice input pair

Date: 2026-09-28. `official=false`; model experiment NOT_RUN.
Follows the [closure audit](2026-09-28-completion-closure-audit.md).

The audit found unsupported closure of changed-behavior questions after old regression
PASS. Completion advice is a possible contributor, not an established cause. This
preparation removes its action recommendation while retaining factual eligibility.
It does not add another warning or force a probe.

## Prepared intervention

The source is the same first accepted post-edit boundary of
`run_dev_33068b6e257f423a`, before regression and question narrowing. Control uses the
previous proposed $3 fresh allowance; treatment has the identical allowance. These
are offline input values, not reopened funds or a new paid allocation.

Only latest-state `completion_guidance.next_action` and `message` differ. Before
regression, the check identifier and exact-diff PASS requirement remain, without
the instruction to run that check. At readiness, the eligibility/untested-behavior
warning remains, without the conditional probe/finish recommendation or the statement
that no extra experiment is required. Tools, gates, system prompt, patch, plan,
notes, history and remaining resources are preserved. This tests the local advice
bundle; it would not separately identify the effect of its JSON field versus prose.
Other completion language is deliberately unchanged.

## Evidence and limits

- Packet: `C:/pt/analyses/completion-advice-checkpoint-20260928-v1/packet.json`.
- SHA-256: `24a21170d5b40200ebd539c2eb84592df095cc5155ba1a93f3bb501b54b7c424`.
- Preparation journal: `runs/run_dev_advicepreparation.jsonl` under that root.
- Offline fixture receipt: `rehearsal.json`, bound by
  `runs/run_dev_advicerehearsal.jsonl` and content-addressed artifacts.
- Source identities and both input artifacts are bound in the packet. Validation
  reconstructs them from immutable source. Control exactly matches the historical
  unhinted first dispatch. Reversing the two changed guidance fields reproduces
  the complete baseline request at both saved check and ready boundaries.

The ready boundary is a saved control fixture, not an observed treatment trajectory.
No new provider call, public check or evaluator execution was used for preparation.
The module has no live collector integration, and ordinary runtime is unchanged.
This is input-pair readiness, not end-to-end continuation readiness or solving evidence.

Focused tests cover unchanged evidence/tools/budgets/eligibility and rejection of
changed wording and unsupported stages. Advice, post-edit continuation and document
tests passed together within two minutes; Ruff passed for runtime, tests and the new
diagnostic. A test initially expected ValueError instead of the repository's
ContractError; the expectation was corrected. The whole repository suite was not run.
Ordinary mock smoke `run_dev_6a0632d06833453d` reached EVALUATOR_PASS, safety NOT_RUN,
cost zero under `C:/pt/runs/completion-advice-mock-20260928-v1`. This smoke does not
exercise an advice-removal continuation hook, which is not implemented.

## Next decision

Implement and rehearse a scoped continuation hook before proposing live execution:
apply advice removal from the first boundary, bind canonical state and input before
counting, and define what happens after additional edits or unsupported stages.
Keep factual tool eligibility unchanged. Then freeze a fresh manifest with exact
task/model/repeats/credential path and invocation-wide cap for a separately authorized
run. No default adoption, automatic dispatch, or carryover of closed allocations.

Implementation contract: [offline advice pair](../../.agent/completion-advice-checkpoint.md).
