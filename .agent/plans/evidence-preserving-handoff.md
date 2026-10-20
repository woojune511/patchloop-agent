# Evidence-preserving handoff and unverified interpretations

Date: 2026-10-17. Status: diff-scoped refs and observed call support; live quality untested.
Design baseline: `e9966142e1a24f5c3a78d2261013cbf8542723d2`; design commit: `ffe11a0`.
See [implementation and offline evidence](../../docs/history/2026-10-17-evidence-handoff-implementation.md).
The [displacement audit](../../docs/history/2026-10-17-handoff-counterevidence.md)
motivates the current reference-scope refinement below.
See its [implementation and displacement results](../../docs/history/2026-10-17-question-evidence-priority.md).
The [call-support refinement](question-call-support.md) adds optional observed syntax
support; its [follow-up](../../docs/history/2026-10-17-question-call-support.md) records displacement.
Only provider-free validation is authorized; no paid comparison is scheduled.

## Problem and intended change

The [segment audit](../../docs/history/2026-10-16-segment-boundary-audit.md)
established two separate problems: useful source disappears at handoff, and an
unsupported interpretation can survive in public plans/notes after reasoning resets.
It did not isolate a repair-quality effect of changing boundary timing.

Use the existing segment trigger, but replace its implicit promise of review with
an explicit delivery contract. Preserve a small, declared set of already-observed
evidence; display its actual contents and limitations next to model interpretations.
The runtime can guarantee identity, currency and delivery. It cannot establish that
a free-text claim follows from the evidence or that a test covers the task.

Current code already labels plans/notes `model_authored_unverified`, retains plan
predecessors/reasons and reopens concern decisions after a diff change. Adding those
features again is not an intervention. The [C/D comparison](../../docs/history/2026-10-16-plan-grounds.md)
exposed traceability yet obtained 0/8 in both arms. The substantive new behavior here
is declared evidence selection and adjacent delivery of evidence and interpretation.

## 1. Boundary timing remains mechanical

Keep the current completed-batch rule and all hard limits: 60,000 counted input
tokens, 1,048,576 request bytes and 262,144 bytes per encrypted item. Keep 24,000
retained source characters and existing run-wide resource/cost limits.

Fresh contracts describe `major_result_reviewed` as
`major_result_followup_completed`: the result was followed by a normal response
and its completed tool batch. This is a naming clarification, not a new timing rule
or proof of understanding. Preserve old events and their meanings on old runs.

At each existing boundary:

1. Complete/reconcile the current batch using existing recovery rules.
2. Resolve declared evidence against public observations; compute currentness.
3. Select evidence within the existing source budget and compose an immutable
   candidate input. Record its exact payload and any count receipt before dispatch.
4. Apply byte/count admission and the bounded optional-body fallback below. After
   any recomposition, resolve every delivery reference against the final input,
   including quoted results and inline source; recompute owner-level omissions.
5. Only then commit the admitted seed, selection/omission manifest and contract
   identity as the segment binding. Never edit an already committed segment seed.

Do not wait for the model to declare its thinking complete. An oversized or stale
optional evidence range does not postpone handoff, force a read, or block an otherwise
valid action. If the fresh required state itself exceeds existing limits, retain
the current limit-stop behavior. Do not silently truncate task/diff/failure authority.

The first candidate deliberately keeps timing fixed. A later timing experiment
would need a distinct question; changing timing and content together would obscure
which mechanism helped. A soft boundary does not certify a phase or hypothesis.

## 2. One active question owns explicit evidence references

Evolve the existing `memory_update.open_question` into one nullable object. It works
with planning disabled and does not create a separate claim/task registry:

```json
{
  "open_question": {
    "text": "Which observed branch opens the missing __init__.py?",
    "evidence": [
      {"kind": "source", "role": "primary", "path": "astroid/builder.py",
       "start_line": 115, "end_line": 128},
      {"kind": "source", "role": "countercheck", "path": "astroid/manager.py",
       "start_line": 199, "end_line": 211}
    ]
  }
}
```

This is an operator-authored illustration, not a field present in the original run.
Keep the 500-character question and two-reference bounds. Each reference declares
`role=primary` (the smallest observed unit answering the current question) or
`role=countercheck` (a competing branch or precondition that could challenge its
explanation), at most one of each. Zero allows an unanswered question; a second
reference is optional and must not be invented. Roles and minimality are model
judgments, not semantic facts certified by the runtime. No arbitrary line cap or
task-specific branch heuristic determines what counts as minimal.

Reuse source-note admission: an entire source range must already have been observed
and be current or validly rebound; a tool result must have completed before this
response. Fresh tool references accept verification results only; source-bearing
reads/searches/mutations require an explicit source range instead of promoting the
entire result. Pending actions and the current batch cannot serve as observed evidence.
The runtime binds file/body hash, action/input/diff identity and origin receipt;
the model supplies none of those hashes. A tool reference retains its actual scope
and may be historical, explicitly labelled as such.

This direct-reference shape avoids extra focus lists, same-response note-ID aliases,
and copies of focus in the plan. Do not copy a whole note/function when a smaller
observed unit addresses the question. There is no arbitrary surrounding-line or
whole-function promotion. Optional call support below adds no declared references.
Overlapping references share one delivered body.

Update semantics:

- `memory_update=null` preserves notes, question and concerns.
- `open_question=null` clears the active question and its priority references;
  it does not resolve any verification concern or delete notes.
- A valid object replaces the previous question and references atomically.
- The runtime binds `declared_diff_hash` at the before-tool-batch update; the model
  cannot supply it. A changed diff leaves the question visible with
  `priority_status=needs_refresh`, even when source bytes remain current. A normal
  later response may refresh the declaration if it is still relevant. Null does
  not refresh it, and a generic PASS does not refresh it automatically.
- `eligible` means the declaration is scoped to this diff, not that its role,
  minimality, or delivery is validated. Unscoped legacy objects stay readable with
  `priority_status=unscoped` but receive no extra source/result priority. Legacy
  strings stay strings; no old note is automatically promoted to an active focus.
- An invalid reference rejects that question update and preserves the prior question;
  report bounded feedback. Independently valid note/concern updates and the main
  action continue under their existing contracts.
- Later source expiry leaves the question visible with an unavailable reference.
  Never reconnect an old range by coordinates alone or invent missing source.

All notes remain bounded at six, updates at two findings, and unresolved concerns
at three. An inactive note is not promoted merely because it exists or is repeated.

## 3. Selection preserves declared evidence, not every old interpretation

Current `tools._source_projection_priorities` gives note citations rank 3, while
editable source has default rank 2. The selector takes the minimum; therefore a
note citation does not improve priority inside an editable file. Ranks 0/1 retain
mutation precedence; question ranges use the subsequent optional atomic tier.
This is one selector and one source budget, not a second source store.

Within the same retained-source budget, use this order:

1. Existing mutation anchors/postimages and their current priorities.
2. The active question's eligible countercheck source range, then primary range.
3. One atomic bundle of observed Python call support for admitted source citations.
4. Existing ordinary source selection with its current priorities and recency.

The support tier uses complete parseable observed function fragments, local
parameter/assignment/import dependencies, branch and exception conditions, effect
calls before the focus, and immediate observed caller/cited-target candidates.
It uses no task names, question-prose ranking or unbounded call traversal. Non-Python
or unparseable source, ambiguous names and incomplete scopes add no inferred support.
The bundle must fit after both citations; otherwise ordinary selection still runs.
It cannot displace mutation protection or an admitted countercheck. Existing delivery
and omission accounting describes actual source bodies; support is not a third
reference, resolved dispatch, a sufficient-context certificate or semantic evidence.

The new atomic reference identity includes path, file hash, complete line range,
and owner/question revision. Deduplicate costs by actual `(path, file_hash, line)`.
Already delivered native/quoted source can satisfy a reference without a duplicate
body. The manifest records that delivery, not merely that CAS contains the text.

For each declared range, admit its missing lines as a complete group if they fit.
Otherwise give that range no priority admission and continue to the next range.
Its lines may still participate in ordinary selection at their original priorities;
a bad oversized focus must not suppress useful baseline source. Atomicity governs
priority admission, not a prohibition on partial ordinary context. After selection,
mark completeness from the actual delivered union and list exact missing lines.
A large primary reference must not consume a declared countercheck's priority space.
An oversized countercheck still permits a smaller primary to fit; neither blocks
ordinary selection. No additional source quota or reservation is introduced.
Existing mutation-anchor omission rules are unchanged.

Do not pin all six notes or automatically treat the model's favored hypothesis as
true. Focus references control attention only. Report newly displaced ordinary
source as well as newly preserved references; preserving one body can evict another.

Tool evidence uses the existing bounded public action projection: retain input or
target/question, returned result fields, execution flags and source/action/diff
identity. This must show actual available detail, not only a PASS/result ID. Use
existing per-tool public bounds; deduplicate repeated actions. Do not import raw
unbounded logs or reinterpret stdout. If an original output was truncated, it stays
truncated. Numeric values/false assertions printed by a healthy probe remain exact
observations; execution success is not a behavior verdict.

An additional old read/search result cannot bypass the source budget by putting
its source in a quoted tool body or expanding all its spans into fresh focus.
Explicit ranges use the same retained-source selection. Keep latest-batch/native
delivery bounds unchanged; 24k is the retained-source budget, not a claim that all
source in the full request totals 24k. Source and result references must deduplicate
against all actual delivery routes.

Selected additional tool projections share the existing final request limits;
they are not a new unlimited evidence budget. If the fresh candidate exceeds a
limit and contains optional added result bodies, remove those added bodies in one
deterministic fallback, retaining compact identities/flags and explicit omissions.
Rebuild delivery references and recount only the changed exact request. This permits
at most two fresh candidate counts and no summary/review call. Each count is admitted
under existing invocation-wide caps; no extra budget is authorized by this design.
If the final candidate still does not fit, the ordinary stop applies.

Candidates/count receipts are immutable prepared records, separate from committed
segment state. Recovery reuses a known completed count only for its identical payload
and finalizes the same chosen candidate once. An unknown count/transport/billing
outcome stops immediately; it never authorizes the fallback or a retry. This requires
runner preparation through `segments.start(prepare=True)` and finalization through
`segments.commit`, never mutation of a committed binding. After fallback, a source reference
formerly satisfied by a removed tool
body must resolve to budgeted inline/other delivered source or become incomplete.

## 4. Evidence, model interpretation and proposed work stay separate

The model-facing state should distinguish these existing owners:

| Owner | Content and authority |
| --- | --- |
| Public observations | Runtime-projected source text and actual execution input/target/result, with identities and flags. Facts about that observation only. |
| Notes | `model_interpretation` plus cited observations. Never a runtime-certified fact, even when evidence is current. |
| Open question | The next uncertainty and up to two declared references that should survive a handoff. |
| Verification concerns | Existing stable ID, immutable original purpose, progress and the model's disposition/reason. |
| Plan | Proposed remaining work and ordering, referring to notes/concerns. Not another store of observed results or verified conclusions. |
| Mutation intent | The existing hypothesis/expected behavior remains an expectation; retain its actual patch/result separately. |

For each interpretation, expose `evidence_currency` separately from
`evidence_delivery`. `current` means current source/diff evidence, not a true
statement. A current citation whose body is absent is explicitly incomplete.
Show exact reference-level states and compact omissions; do not infer availability
from the journal, a historical catalog, or a delivery marker that no longer resolves.
Original result truncation is separate from whether all available public text was
delivered. No field may imply complete original output when only an excerpt exists.

In the public projection, show the observation first and then the model interpretation.
Keep shared bodies once and use resolvable references beside each claim. Inactive
notes may have no body in the current request; show that limitation rather than
duplicating every historical source or deleting the uncertainty.

Project existing concern `resolved` as `closed_by_model`, and `dismissed` as
`dismissed_by_model`, together with the original question, reason and cited result.
Preserve the existing current-diff eligibility rule for resolve. An actual PASS
remains an execution result with `behavior_coverage=not_assessed`; it does not create
`verified=true` for the concern. Model-written `fact`, `confirmed` or `verified`
states are not part of this contract. This is a display/authority distinction,
not semantic validation of the model's reason.

Keep the brief plan bound and predecessor/reason history. Ask it to express remaining
work, with substantive unresolved verification purposes in existing concerns so a
whole-plan replacement cannot erase an already-recorded concern. Do not create
concerns by parsing prose, require one for every thought, or add a task/claim graph.
A purpose never registered as a concern is not mechanically protected by this
design; plan prose alone cannot provide that guarantee. Concern-capacity feedback
must not be treated as successful registration. Original purposes remain immutable
in the journal, but the current bounded concern store can evict closed/dismissed
items when admitting a new concern. Their perpetual presence in later model inputs
is not guaranteed: a weak model closure can still indirectly cause that loss.
Keep this as a declared limitation rather than pinning every closed concern.
Source-inference completion remains allowed and is labelled as model judgment
without executed behavioral proof.

### Lifecycle rules

| Event | Required behavior |
| --- | --- |
| Null update or unchanged plan | Retain prior interpretation without promoting certainty. |
| Generic suite PASS | Preserve the actual receipt; do not turn an unrelated concern into verified behavior or erase older failure observations. |
| Diff changes | Old execution results/decisions become historical; existing concern decisions reopen. An old failure does not automatically refute the new patch. |
| Source changes | Apply existing exact rebind/expiry; no stale body presented as current. Evidence currency cannot revalidate a semantic claim. |
| Focus moves or note expires | Preserve independent concerns and their original purposes. Clear priority only, not evidence history or concern status. |
| Model rejects a hypothesis | Keep the bounded decision/reason and cited observation as model judgment; do not infer contradiction from arbitrary stdout automatically. |
| Size forces handoff | Carry these states and omissions without claiming review completion. No requirement to write a new plan first. |

For the SQLFluff pattern, a fresh input would distinguish: a pre-edit L003-only
probe printed `equals_expected=False`; the helper was then edited; the model
believes that edit fixes the full path; no cited post-edit target execution supports
that belief. It must not summarize those four statements as "the fix is verified."
Conversely, the pre-edit failure must not be labelled a refutation of the new patch.

## 5. What the design can and cannot establish

Guaranteed and testable: declared-reference admission, identity, bounded selection,
explicit omissions, current/historical labels, and no automatic promotion of an
interpretation into an execution/coverage fact. Use semantic labels only where
the underlying contract actually establishes them.

Not guaranteed: good focus selection, sufficient context, correct hypothesis
revision, or a correct repair. The model can still overstate a conclusion in prose.
There is no reliable syntax rule that decides whether arbitrary source or a passing
test supports an arbitrary claim. A stronger guarantee would require a separately
defined behavioral predicate and its coverage assumptions; that is not introduced
as a universal gate here.

Astroid makes this limit concrete: preserving old builder 110-170 displaced eight
route-discriminating manager lines, while 37 newly retained neighboring lines had
lower direct relevance. A narrower paired declaration fits but also loses useful
name-derivation ordering. The historical model never selected either new declaration;
do not assign it that knowledge or claim it would have avoided a reread or bad repair.

## 6. Implementation seams and bounded validation

| Seam | Responsibility |
| --- | --- |
| `working_notes.py`, `tools.py` | Question-reference schema/admission, persistence/rebind, atomic priority tier and bounded feedback. |
| `context.py`, `question_support.py` | Atomic selection, optional observed call support and exact omission accounting. |
| `evidence_focus.py`, `model_state.py`, existing native/public-history resolvers | Bound references, evidence-versus-interpretation projection and actual inline/native/quoted delivery. |
| `evidence_focus.py`, `working_plan.py`, existing concern lifecycle | Model-disposition wording, original purpose continuity and plan role; no new correctness gate. |
| `runner.py`, `segments.py`, `contracts.py` | Compose/bind handoff manifest, hard admission, recovery and fresh contract identity. |

Do not reinterpret legacy open-question strings or serialized statuses while
resuming an old contract. Keep old recovery behavior; a fresh implementation must
bind the new wire/projection semantics in existing model/envelope/contract hashes
and reject mixed-contract resume. No historical run is migrated or rewritten.

Build the change in separable slices: first admission/selection/delivery, then
evidence-versus-interpretation projection. Keep timing fixed throughout. Introduce
no extra review model, summary call, automatic tool action, mandatory probe, or new
finish gate. Do not create another family of planning variants for this design.

Provider-free acceptance cases:

- Complete declared ranges retained when they fit after mutation anchors; equality
  and one-character overflow, overlapping references, a large first range and small
  second range, duplicate native delivery, unseen gaps and stale versions.
- Countercheck-before-primary ordering, duplicate/mixed-role rejection, no fabricated
  roles for legacy objects, and unchanged question/source bytes losing only priority
  after a diff change. Explicit refresh and crash/recovery retain exact scope.
- An old source-bearing result reference cannot bypass retained-source selection;
  existing latest-batch delivery retains its original bounded semantics.
- Invalid question updates preserve the previous question; null update/clear have
  different meanings; new notes and a direct question reference work in one response.
- Current-but-undelivered source is not represented as delivered. Healthy probe,
  printed false value, timeout, truncated result and unexecuted test stay distinct.
- A false model sentence with a valid current citation remains an interpretation;
  a generic PASS cannot produce behavior verification. Pre-edit failure does not
  refute a later patch. Plan replacement/focus change does not delete a concern.
- After optional-body fallback, shared source/result references resolve against the
  final input or are incomplete; failed counts never trigger fallback/retry.
- Actual composed request references resolve; no hidden/evaluator/unobserved bytes,
  no reasoning replay across segments, no budget reset or duplicate mutation/check.
- Crash/resume between candidate preparation, successful count and segment commit
  produces the same admitted question, evidence identities, omission manifest and
  seed; incomplete batches remain governed by existing reconciliation.

Use the 75 saved handoff snapshots to characterize displacement, source characters,
referenced-range coverage and public-result delivery. They contain no new focus
declarations: an operator-specified or deterministic surrogate selection is a
selector test only, explicitly labelled, not observed model uptake. Freeze that
selection before comparing; never infer it from future actions, later probes or
private evaluator outcomes. Track astroid citation versus full-context coverage
separately. SQLFluff-2419 is a no-loss control. Historical L003 line 706 is not a
required retained reference unless the admissible pre-boundary declaration covers it.

Offline replay cannot establish fewer rereads or higher repair success by reusing
the saved next action. Measure those only in a separately scoped, approved live
comparison, if a new evidence-based reason justifies one. No such run is scheduled.
Stop this candidate if it silently loses declared evidence, displaces mandatory
mutation state, changes admission/finish behavior, or cannot stay within budgets.
Even successful delivery tests do not justify baseline adoption on quality grounds.

Validation includes focused success/failure/recovery cases, Ruff, the fast suite
and isolated mock smoke; results and limitations live in the implementation record.
Keep focused groups under two minutes. Runtime delivery is locally testable;
model uptake, reread reduction and repair-quality effects remain untested.
