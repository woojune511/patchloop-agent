# Product and architecture

## Product

PatchLoop is one coding agent that repairs a public software task. It inspects
source, applies a bounded mutation, verifies the current diff with registered
checks, submits it, and receives a public-safe summary from a separate private
evaluator.

The evaluator, state journal, workspace manager, sandbox, and model adapter are
supporting layers. The product is the agent and its ability to reach a durable
submission reliably.

## Development objective

Use short `official=false` loops to improve completion and submission reliability.
Optimize for an answerable next question and a durable terminal. Historical
runtime comparability and claim-producing evaluation are separate concerns.

## Runtime shape

```text
public task ──> dev-head ──> constrained model/tool loop
                    │                   │
                    └──> external JSONL journal
                                        │
                                        v
                               submitted patch artifact
                                        │
                                        v
                            separate private evaluator
                                        │
                                        v
                     task acceptance + separate safety state
```

`dev-head` derives its next gate from public execution facts: `needs_mutation`,
`needs_visible_checks`, or `ready_to_submit`. There is no separate planning phase,
runtime-version switch, memory retrieval path, or candidate/qualification workflow.
The exact latest tool batch is guaranteed in the next stateless request; older
current source spans form a small recency-ordered working set. Before the larger task
text, the prompt presents the current gate, remaining horizon, mutation readiness,
complete-diff mutation scope budget, and a bounded ledger of covered ranges and recent
searches. `ready_to_attempt` says only that a current exact anchor exists; it is not a
semantic-solution judgment. The current diff's
complete visible-check status and exact remaining check IDs are projected separately
from the bounded recent output. `ready_to_submit` additionally requires a non-empty
diff and no non-ignored untracked files.
A successful mutation revalidates unchanged, uniquely occurring pre-image spans in an
edited file and adds a bounded replacement post-image span, all bound to the current
file and diff hashes. This preserves nearby imports or symbols without treating changed
text as current evidence. It lets a failed public check lead directly to an overlapping
same-file repair, while edits outside current spans still require read/search evidence.
The model supplies the exact replacement but no evidence IDs. The gateway binds the
most recent observed span whose current file hash and line range cover that replacement,
and records the selected ID only as append-only action provenance. The public mutation
summary reports whether post-image repair evidence is available; uncovered anchors
still fail closed.

For OpenAI runs, stateless continuity also carries the provider-encrypted reasoning
items returned by the immediately preceding response. Their ciphertext and output
order live in the external content-addressed store; the journal carries only the
artifact hash, item counts, and order hash. The next request replays those items with
the matching function calls and public results before the new public context. Plaintext reasoning,
reasoning summaries, private task material, and evaluator details are never retained
or projected. Missing or damaged continuation evidence stops the run before another
provider or tool call.

Every read/search decision carries a bounded public working state: the current causal
hypothesis, one evidence gap addressed by that operation, and the decision to take
after its result. The state is returned with the result in the next stateless request
and retained in its attempt card. This public state remains independently inspectable;
it does not expose the separately replayed encrypted reasoning or create a planning
phase or execution gate.

Every model response must call at least one constrained tool. Besides inspection,
mutation, checking, and finish, `stop_task` provides an explicit unsuccessful exit
when the public evidence cannot support safe progress. It records a bounded public
conclusion and does not create a submission or run the evaluator.

Inspection availability is based on completion slack rather than a fixed number of
earlier reads. When only one optional inspection turn remains, the context warns that
`read_file` and `search_files` will close next. At zero slack they close so mutation,
remaining visible checks, submission, or an explicit stop retain the required calls.
Each decision uses one fresh public workspace snapshot for both its action policy and
model context. This keeps the prompt and action mask coherent without caching state
across mutations, checks, or recovery boundaries.
The horizon holds two independent bounded allowances: two calls for one rejected-
mutation recovery and at least three calls for one failed-visible-check recovery. The
latter preserves one targeted read before replacement and recheck, plus reruns of checks
that passed earlier on the invalidated diff. Consuming one allowance
does not erase the other. Best-path and protected-path feasibility both reflect actual
remaining model and tool budgets, not merely the presence of another mutation slot.
After two consecutive successful inspection batches add no non-overlapping coverage in
any tracked public source while a current mutation anchor exists, the context adds a
soft `commitment_signal` recommending mutation or explicit stop. A new query, shifted
span, or contained range can be novel telemetry without being new evidence. Editable
and supporting coverage remain separate. Once activated, the signal stays active for
the current diff even when a later inspection adds coverage; mutation or a check/
completion transition resets it. The signal does not remove read/search.
Every such change is journaled and projected once; corrections name only tools that are
actually present in that turn's action space.

Mutation uses one exact `old_text` to `new_text` replacement in an existing tracked,
allowed file. The gateway validates the current anchor and constructs the Git diff, so
the model does not spend turns serializing hunk headers or line counts. After a failed
visible check, one `read_file` turn is restricted to the changed or currently evidenced
paths before mutation is offered again.
Scope rejection returns the restored baseline and rejected complete candidate arithmetic
instead of only a generic message. Scope and replacement-contract failures stay in
mutation-or-stop mode; stale anchor/evidence failures get one targeted reread of their
path, never broad search. If the minimum remaining mutation/check/finish path becomes
mathematically impossible, the runtime records `LIMIT_REACHED` before another provider
dispatch rather than offering actions that cannot reach submission.

Visible checks are executable public examples, not the private acceptance oracle.
They should exercise the central behavior already promised by the issue while
remaining black-box: assert observable inputs and outputs, not an implementation
shape, reference patch, hidden input, or exact sentence unless the public contract
requires it. Hidden evaluation remains separate and tests unexposed variations.
When a development task's public contract changes materially, preserve the old
package and create a new task version/content identity.

## Main components

- `patchloop/dev/runner.py` composes the mutable loop.
- `patchloop/dev/tools.py` provides registered read, search, mutation, check, finish,
  and unsuccessful-stop tools.
- `patchloop/dev/state.py` stores append-only, hash-chained run events.
- `patchloop/dev/cost.py` performs provider cost admission immediately before dispatch.
- `patchloop/agent/model.py` owns stateless model requests with zero SDK retries.
- `patchloop/repository.py` creates isolated workspaces and full diffs.
- `patchloop/sandbox/runner.py` runs registered checks locally or in a pinned image.
- `patchloop/verifier/core.py` evaluates the submitted artifact in a separate workspace.

The run envelope and manifest have different lifetimes. The immutable envelope is
written when a run starts and makes interruption recovery exact. The manifest is
written only after submission and makes evaluator inputs exact. Both bind hashes,
not private task paths or contents, into public run provenance.

## Scope

Current development includes public source inspection, constrained edits, visible
checks, exact-envelope run resume, action recovery, cost enforcement, external run
state, content-bound manifests, typed safety evidence, and isolated private
evaluation. Resume derives the current workflow gate
from the workspace and durable check evidence; it does not restore a decorative
workflow state. It excludes memory experiments, held-out tuning, claim runs,
automatic provider retries, Docker startup, image pull/build, and compatibility
with deleted historical runners or pre-envelope journals.
