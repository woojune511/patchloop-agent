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
The latest tool batch's observations are guaranteed in the next stateless request. Prior
inspection intent stays in the exact native call arguments, not repeated as a tool finding:
result/ledger/history copies use action-bound references. Source and actual check results
remain exact; explicit notes and questions are unchanged. Older current
source uses a deterministic 24,000-character retained working set: pin the current edit
or failed anchor, retain source-backed notes, then fill with recent observations.
Overlapping observed ranges are merged; unobserved gaps are never filled. The current view
presents the gate, remaining horizon, mutation readiness, complete-diff scope budget and
search aggregates. Detailed covered ranges and recent inspection accounting stay in the
canonical audit context and native observations. Omitted observed source has short
range metadata without body text, bounded to 12 ranges plus its full range count.
The audit context's bounded `observed_source_index` locates lexical function/class headers
in delivered current source, with at most 16 entries and 4,000 characters; the model view
groups them into `current_sources` without changing selection. It helps find
observed code again without reading unseen source or claiming complete function extents.
`ready_to_attempt` means non-empty, current editable evidence is delivered
in this input. It does not establish that a proposed replacement's complete anchor is
covered or that the semantic solution is sufficient; admission validates the exact
replacement separately. The current diff's
complete visible-check status and exact remaining check IDs are projected separately
from the bounded recent output. `ready_to_submit` additionally requires a non-empty
diff and no non-ignored untracked files.
A failed public check creates a bounded `current_public_failure` focus for its
checked diff. After an edit, the model view instead shows `pending_recheck`: the
current candidate is unchecked, with a reference to the earlier failure's exact
native result (or bounded historical details if no matching result was delivered).
The original error and comparison history remain in that result and the audit;
they are not repeated as an active failure of the edited candidate.
Recheck guidance names only an offered check; zero remaining mutations
prevents more edits, not affordable checks and submission after they pass. Current
failure feedback instead names offered repair/inspection tools. This is advisory
presentation, not a new tool restriction or a reason to reject voluntary stop. For a
registered inline Python command, the gateway maps an unhandled `<string>` traceback
line back to the exact public command statement without reading another file. It keeps
the raw-output failure signature for provenance and derives a separate semantic site
fingerprint for comparisons across diffs. The focus survives intervening inspection
and restart, distinguishes the same mapped site from a changed traceback location,
and becomes pending through repair until a recheck passes or supplies a new current
failure. By default, rechecking a repair is advice, not a gate: an independent source-supported
edit remains possible. A hypothesis or unread helper's header is not a verified
defect. Source-line
order does not establish execution history through loops or branches; whether later
lines ran remains unknown. A failure guides investigation without restricting it to
the reported file or forcing a claim that a prior hypothesis was falsified.

The optional `--repair-recheck` experiment couples an accepted repair with one
rerun of the latest still-failing public check on its baseline. The harness supplies
that current verdict before the next inference, charging the normal tool/time budget.
It does not fabricate a model call, add tool masks, require notes/plans, or run private
evaluation early. Other checks and all semantic repair choices remain the agent's.
This option is off by default; its effect on agent quality has not been live-tested.
Check output limits preserve complete lines and explicitly report clipping. A small
literal failure summary preserves public test IDs/comparison text even when a long log
pushes them out of the delivered tail. Exception labels come from recognized terminal
formats, not arbitrary log words; ambiguous or unrecognized types remain unknown.
These are public observations, not a model-authored diagnosis or another submission gate.
A successful exact replacement maps already observed unchanged complete lines to their
new positions using verified pre/post bytes and the exact edit offset. Changing one line
does not discard the observation's unchanged prefix/suffix. It adds a bounded replacement
post-image span, all bound to current file and diff hashes. This preserves known source
without treating changed
text as current evidence. It lets a failed public check lead directly to an overlapping
same-file repair, while edits outside current spans still require read/search evidence.
The model supplies the exact replacement but no evidence IDs. The gateway binds the
contiguous union of actually observed current source ranges covering that replacement,
and records their IDs only as append-only action provenance. Complete-line output bounds,
empty EOF reads, and consistent CRLF normalization keep that coverage accurate. The public mutation
summary reports whether post-image repair evidence is available; uncovered anchors
still fail closed.

Successful mutation feedback separates the complete pre-edit diff
(`output.baseline_diff_hash`) from the completed candidate (`workspace_diff_hash`,
also `output.worktree_diff_hash`). The incremental replacement's `output.patch_hash`
is not the complete candidate hash. A replay returns those original action-time
identities, not the later workspace. A rolled-back proposal retains the restored
baseline identity. None of these hashes establishes a check verdict: an edited
candidate still needs its own checks.

Public searches use repository-rooted, case-sensitive globs: ordinary wildcards stay
within one path component and `**` includes zero or more directories. This includes
root files in the default `**/*` search. Queries are literal text; a searched-file
count distinguishes an empty eligible file selection from a text search with no match.

For OpenAI runs, the complete active native episode follows one stable user task:
encrypted reasoning, canonical function calls, and matching public results in order.
A fixed initial harness state precedes that user boundary. Later complete, compact
current-state views append after tool results without rewriting the prefix. Read the
latest view directly; only the public task is inherited from the initial message.
It starts with the current workflow gate, a short `completion_guidance`, current check
verdicts and remaining checks. The harness derives this guidance from actual state and
available actions; it does not execute the suggested action. Historical PASS is labeled
as not counting toward current completion. Submission uses `finish_task`; `stop_task`
is unsuccessful abandonment, even when no further code edit is needed.
Older mutable fields are not inherited. The detailed audit context stays separate:
rolling inspection accounting is not a model-facing edit log. Saved input artifacts
preserve every previous item, and metadata binds history and current view.
Current source bodies already in native results are linked by exact path/hash/line and
action identity, not copied again into state. Missing or ambiguous delivery keeps the
inline source; mutation admission is unchanged. New mutation results also reference
unchanged source in prior native outputs when the admitted edit position, raw-file hashes
and exact delivered lines prove the mapping. Backward references retain the new source
identity and a body hash; changed code and post-images stay explicit. They never silently
re-read source or rewrite old messages. The obsolete alternative-requirement flag stays
out of the model view. Stopping uses a reason and summary, not model-supplied source IDs;
this simplifies the interface without preventing voluntary abandonment.
`current_sources` groups path/hash,
native action/field/ranges and observed headers without filling unseen gaps. Each file's
`edit_permission=allowed|read_only` uses the existing mutation path rules, including
forbidden-path precedence. It does not grant anchor evidence or change offered tools. Scope
rejection explicitly names the rejected path and actual public path rules; a helper
can be inspectable but not editable. Earlier observations
are historical, not current source or check PASS. Effective reasoning mode is recorded
only when the provider reports it; delivery is not proof of effective model reuse.
Full history is subject to existing exact cost admission and can cost more; it is not
silently truncated or compacted by another model. Plaintext reasoning,
reasoning summaries, private task material, and evaluator details are never retained
or projected. Missing or damaged continuation evidence stops the run before another
provider or tool call.

Each action carries a bounded public decision, with an evidence question for inspection.
An optional `memory_update` on that same action records at most two concise findings
citing already observed source ranges or prior public tool results and one open question.
The first non-null update in a parallel batch is used; additional updates are diagnosed
and ignored. Each finding has a stable run-local ID such as `n3`, independent of its
citations. `note_id=null` creates a finding; an existing ID updates it even when the
cited range changes. The model can consolidate duplicates by updating one ID and
listing the others in `remove_note_ids`. The run retains at most six model-authored
findings, rebinds unchanged source or expires stale source notes, marks old tool-result
references historical, and journals IDs and updates for resume. A note's observed source
body is retained independently of temporary source spans; mutation-linked lifecycle
records make continuation and resume agree on which notes survive. Invalid notes receive
a separate storage receipt with the affected note and a correction hint, without rejecting
the main action. That receipt describes the update before its tool batch, not which IDs
survive a following edit. The native owner output separately reports note IDs and expiries
after the completed batch. A mutation that expires notes reports that lifecycle even when
it requests no note update; unrelated later actions do not repeat the expiry.
`working_notes.available_note_ids` is the current authority. Once the exact storage receipt
is delivered, later current views reference it rather than repeating its historical success
or rejection body. Missing or mismatched delivery keeps the bounded inline receipt.
Before observing an answer, the agent can keep an open question; afterward
it can create a note and use its ID for revisions while it remains in the current list.
This run-local working memory has no
retrieval from prior runs and stores no reasoning transcript.

Notes may retain the observed mechanism, the chosen implementation approach, and
behavior still unverified. The prompt encourages reuse of existing functions' behavior
and asks whether another inspection could change the edit or next check. These are
short public observations and decisions; no extra model call, planning tool, or
mandatory three-part plan is added. Reusable facts remain distinct from current error
status, which the automatic failure card already provides. Updating an existing note
refines the same fact; a distinct fact needs a new ID. Citation validation does not prove an interpretation.
An executed check citation carries its actual check name, PASS/FAIL boolean, and bounded
exception type beside the model's prose. Its current/historical diff label is recomputed
after edits without changing that verdict; absent diff identity is unknown. This can
expose an interpretation contradicting its own cited result without judging or blocking it.
Projected notes explicitly remain `model_authored_unverified`; `status=current` means
their cited evidence is current, not that a behavior claim was checked after an edit.
Guidance favors causal mechanisms, closing answered questions, and reconsidering claims
against changed behavior rather than merely preserving repeated function locations.

A separate working set retains up to three public verification concerns,
independent of the focused question and expiring source observations. The same optional
memory update creates an immutable original `statement` with a null concern ID. An
existing `vN` ID stores the supplied statement as its latest `progress_note`, without
replacing the original question. Distinct questions need new IDs. Repeating the original
or currently retained progress is reported as `unchanged`; it does not reopen decisions
or change state. New progress reopens the concern. The agent can resolve a concern with
a completed successful current-diff check or experiment and a brief reason, or explicitly
dismiss it. Earlier-diff evidence
is historical, and later edits reopen retained resolved/dismissed concerns. These remain
model judgments: the harness verifies evidence identity, not whether a test establishes
the claimed behavior. The final visible-check PASS invites reviewing remaining concerns
or submitting; it neither orders immediate submission nor introduces a mandatory review
call, experiment, or finish blocker. Nothing is carried into another run.

Every model response must call at least one constrained tool. Besides inspection,
mutation, checking, and finish, `stop_task` provides an explicit unsuccessful exit
when the public evidence cannot support safe progress. It records a bounded public
conclusion and does not create a submission or run the evaluator.

Inspection availability is based on completion slack rather than a fixed number of
earlier reads. The context previews which tools would close after one more read/search
with unchanged evidence. `tools_closing_after_this_turn` uses the actual next policy,
including `run_probe` or `run_check` when affected, not just the inspection tools.
This conditional notice does not predict new evidence or reserve a different budget.
At zero inspection slack, reads and searches close so mutation,
remaining visible checks, submission, or an explicit stop retain the required calls.
Each decision selects its actually delivered source before computing readiness and the
tool policy. The latest native tool results and retained source jointly establish the
available evidence; larger gateway memory is not misrepresented as visible context.
Native results are not copied again into source, mutation, or recent-check cards.
Every retained check summary keeps its action ID, check name, and diff hash together.
Concern resolution records the actual cited check, not an automatic interpretation of
its coverage. Invalid source-note citations distinguish missing observations from missing
current bindings and report bounded usable/missing ranges without requiring another read.
One completion model accounts for mutation, all invalidated checks, finish, and bounded
failure-recovery allowances under the remaining model/tool/mutation budgets. It does not
assume the model will run checks in their declared order. A rejected optional edit leaves
its rollback baseline usable, including any checks already passed on that baseline.
An optional edit remains executable when its minimum successful edit/check/finish path
fits, even if full additional-failure recovery does not. The context reports conditional
post-edit minimum/protected costs separately and warns when recovery is not fully covered.
This lets an affordable diagnostic-driven revision follow already-passing checks without
treating every failed experiment as a mandatory repair. Inspection/probes retain their
existing protected-budget floor.
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

An explicitly enabled `run_probe` lets the model test a concrete public uncertainty
with a small Python program. It runs against a separate read-only export of current
tracked public source in a pinned clean Python image. The tool description makes explicit
that accepted edits are importable from read-only `/workspace`, with writable `/tmp`
scratch. Only base Python and public project code are supplied; dependencies cannot be
installed and network access is absent. The host selects the image,
mounts, command, execution limits, and trusted wrapper. The program and its output
are diagnostic evidence: a successful probe grants no visible-check or submission
credit, and a failure may be a defect in the experiment itself. Experiments are not
included in the submitted patch. Each costs one model turn and one tool action and
is available only when the remaining protected completion budget still fits afterward.
The capability is off by default and requires explicit `--enable-probes` configuration.

The model-facing probe observation distinguishes `execution_status=completed` from
`behavior_verdict=not_assessed`: normal exit is not an answer to the experiment's question.
Bounded observed/not-observed changed-line excerpts accompany the actual output; unknown
collection does not imply unexecuted code. The agent is guided to vary a public input
that could falsify a new assumption and state its expected observation, using the existing
probe fields. This adds no required experiment or note. Submission eligibility after
required checks still permits finish, without claiming that untested behavior is correct.

## Main components

- `patchloop/dev/runner.py` composes the mutable loop.
- `patchloop/dev/tools.py` provides registered read, search, mutation, check, optional
  probe, finish, and unsuccessful-stop tools.
- `patchloop/dev/state.py` stores append-only, hash-chained run events.
- `patchloop/dev/cost.py` performs provider cost admission immediately before dispatch.
- `patchloop/agent/model.py` owns stateless model requests with zero SDK retries.
- `patchloop/repository.py` creates isolated workspaces and full diffs.
- `patchloop/sandbox/runner.py` runs registered checks locally or in a pinned image.
- `patchloop/sandbox/probes.py` runs bounded experiments in a separate public snapshot.
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
workflow state. Tool-surface `v27` retains public changed-line execution feedback without new
tools or submission gates. A check can pass while newly added error-handling lines remain
unobserved. Results distinguish those lines from positions with no Python line event and
from unknown collection. This is launch-thread line-entry evidence, not branch coverage,
assertion coverage or correctness. It is separate from read/search coverage, and current
summaries never inherit old-diff execution evidence. Existing optional notes/probes can
use this information; private evaluation remains outside the model loop.
It preserves one append-only native episode with complete
compact state views and exact source delivery references. Its read description states the
unchanged inclusive 400-line bound. It retains v21's separation of recorded inspection intent from observed
feedback without changing actions or budgets. It places actual check outcomes beside note citations and
describes existing candidate-probe capability explicitly. It preserves unchanged observed
line fragments across edits,
separates unobserved/stale range feedback, and retains check citation identity. It preserves
original verification questions, distinguishes
update-time and after-batch note state, indexes observed headers, and previews actual
conditional tool closures without changing action masks or budget rules. It retains
component-aware search, minimum-path edit admission with separate recovery warnings,
explicit unverified note interpretations, durable
note-source lifecycles, distinct annotation feedback, stable note IDs,
implementation-oriented guidance, opt-in public
experiments, and the existing source projection,
advisory exploration, shared deadline/recovery accounting, and exact agreement
between provider action schemas and internal decision validation. Bounded conversion
diagnostics retain hashes and field codes, never raw rejected arguments. It excludes cross-run
memory experiments, held-out tuning, claim runs,
automatic provider retries, Docker startup, image pull/build, and compatibility
with deleted historical runners or pre-envelope journals.
