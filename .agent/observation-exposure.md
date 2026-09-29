# Offline observation-exposure fork

`diagnostics/observation_exposure.py` is a synthetic runner diagnostic, not a live
continuation entry point. Production defaults and ordinary resume guards are unchanged.
The separately authorized [live comparison](observation-comparison.md) reuses its
restoration primitive with an explicitly funded envelope; the synthetic entry point
continues to forbid real dispatch and submission.

`fork(Source, cut_sequence, output, arm, synthetic_cap_usd=Decimal(...))` accepts
hash-bound dev-train OpenAI segmented checkpoints without compaction. The cut is a
prepared request following a settled tool batch. Seeded/terminal prefixes and
uncertain count/provider calls are rejected. Output must be fresh and external.

It copies the exact parent prefix and verifies/copies inherited CAS objects, rebuilds
the local prepared source or snapshot, reapplies accepted mutations with pre/post
identities, and checks candidate/call/action/edit allowances. A new envelope binds
the current runtime; a fork event binds parent hashes, cut, diagnostic implementation
hash, arm and inherited active time. The retained run ID identifies the parent
lineage; the new state root identifies the diagnostic branch. Copied events are not
new executions. Historical settled usage is retained; unused historical funds are
closed. The positive new allowance funds synthetic accounting only.

`rehearse(branch, ScriptedClient(steps), probe_outcomes={action_id: status})` uses
the ordinary loop, adapter grammar, count/cost admission and tool gateway with an
inert provider and explicit synthetic probe receipts. No probe Python executes.
Network connects and credential loading are replaced; remote-task mutations/checks
and all submissions are rejected. Snapshot-fixture edits/checks run locally for
idempotency tests. Each branch is single-use, including after uncertain billing or
transport. Completed effect receipts can be reloaded by the ordinary gateway;
this does not authorize retrying an interrupted provider call.

Exposure is applied to canonical context and every final assembled model input:
A removes only `working_notes.verification.observations`, including JSON-serialized
tool-output views; B preserves it. Original check/probe results, concerns, other
JSON fields and opaque reasoning continuations remain unchanged. Hooks are scoped
and restored on exit; branches run serially or in separate processes.

Synthetic completion, delivery and recovery are plumbing evidence. They cannot
establish model behavior, task acceptance, Docker safety or a quality improvement.
Live execution still requires a separate exact invocation and execution path.
