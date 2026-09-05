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
runtime-version switch, cross-run memory retrieval, or candidate/qualification workflow.
The exact latest tool batch is guaranteed in the next stateless request. Older current
source uses a deterministic 24,000-character retained working set: pin the current edit
or failed anchor, retain source-backed notes, then fill with recent observations.
Overlapping observed ranges are merged; unobserved gaps are never filled. Before the larger task
text, the prompt presents the current gate, remaining horizon, mutation readiness,
complete-diff mutation scope budget, and a bounded ledger of covered ranges and recent
inspection outcomes, including reads and searches. Omitted observed source has short
range metadata without body text, bounded to 12 ranges plus its full range count.
`ready_to_attempt` means non-empty, current editable evidence is delivered
in this input. It does not establish that a proposed replacement's complete anchor is
covered or that the semantic solution is sufficient; admission validates the exact
replacement separately. The current diff's
complete visible-check status and exact remaining check IDs are projected separately
from the bounded recent output. `ready_to_submit` additionally requires a non-empty
diff and no non-ignored untracked files.
A failed public check also creates a bounded `current_public_failure` focus. For a
registered inline Python command, the gateway maps an unhandled `<string>` traceback
line back to the exact public command statement without reading another file. It keeps
the raw-output failure signature for provenance and derives a separate semantic site
fingerprint for comparisons across diffs. The focus survives intervening inspection
and restart, distinguishes the same mapped site from a changed traceback location,
and remains active through repair until a recheck passes or replaces it. Source-line
order does not establish execution history through loops or branches; whether later
lines ran remains unknown. A failure guides investigation without restricting it to
the reported file or forcing a claim that a prior hypothesis was falsified.
A successful mutation revalidates unchanged, uniquely occurring pre-image spans in an
edited file and adds a bounded replacement post-image span, all bound to the current
file and diff hashes. This preserves nearby imports or symbols without treating changed
text as current evidence. It lets a failed public check lead directly to an overlapping
same-file repair, while edits outside current spans still require read/search evidence.
The model supplies the exact replacement but no evidence IDs. The gateway binds the
contiguous union of actually observed current source ranges covering that replacement,
and records their IDs only as append-only action provenance. Complete-line output bounds,
empty EOF reads, and consistent CRLF normalization keep that coverage accurate. The public mutation
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

Each action carries a bounded public decision, with an evidence question for inspection.
An optional `memory_update` on that same action records at most two concise findings
citing already observed source ranges or prior public tool results and one open question.
The first non-null update in a parallel batch is used; additional updates are diagnosed
and ignored. Revised statements replace the same evidence-keyed finding. The run retains at most six
model-authored findings, rebinds unchanged source or expires stale source notes, marks
old tool-result references historical, and journals updates for
resume. Invalid notes receive a diagnostic without rejecting the main action. This
run-local working memory has no retrieval from prior runs and stores no reasoning transcript.

Every model response must call at least one constrained tool. Besides inspection,
mutation, checking, and finish, `stop_task` provides an explicit unsuccessful exit
when the public evidence cannot support safe progress. It records a bounded public
conclusion and does not create a submission or run the evaluator.

Inspection availability is based on completion slack rather than a fixed number of
earlier reads. When only one optional inspection turn remains, the context warns that
`read_file` and `search_files` will close next. At zero slack they close so mutation,
remaining visible checks, submission, or an explicit stop retain the required calls.
Each decision selects its actually delivered source before computing readiness and the
tool policy. The latest native tool results and retained source jointly establish the
available evidence; larger gateway memory is not misrepresented as visible context.
Native results are not copied again into source, mutation, or recent-check cards.
One completion model accounts for mutation, all invalidated checks, finish, and bounded
failure-recovery allowances under the remaining model/tool/mutation budgets. It does not
assume the model will run checks in their declared order. A rejected optional edit leaves
its rollback baseline usable, including any checks already passed on that baseline.
Read/search remain available after mutation or check failure while the completion budget
allows. Missing exact edit evidence may require a source read, but known evidence never
requires a ceremonial reread. Coverage and commitment are advisory, including after a
plateau; already observed source or a negative search can resolve an important question.
Editable and supporting coverage remain distinct observations, not semantic progress scores.
Every such change is journaled and projected once; corrections name only tools that are
actually present in that turn's action space.

Mutation uses one exact `old_text` to `new_text` replacement in an existing tracked,
allowed file. The gateway validates the current anchor and constructs the Git diff, so
the model does not spend turns serializing hunk headers or line counts. Mutation admission
binds the complete candidate diff before the source replacement. Recovery checks that
same identity rather than accepting any changed workspace. `causal_revision` is optional
explanatory metadata even when a failure site repeats.
Scope rejection returns the restored baseline and rejected complete candidate arithmetic
instead of only a generic message. The agent can revise the proposal, investigate its
error, or abandon it while continuing from the restored baseline. If the minimum
remaining mutation/check/finish path becomes
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
workflow state. Tool-surface `v13` adds run-local working notes, accurate source projection,
advisory exploration signals, shared deadline/recovery accounting, and exact agreement
between provider action schemas and internal decision validation. Bounded conversion
diagnostics retain hashes and field codes, never raw rejected arguments. It excludes cross-run
memory experiments, held-out tuning, claim runs,
automatic provider retries, Docker startup, image pull/build, and compatibility
with deleted historical runners or pre-envelope journals.
