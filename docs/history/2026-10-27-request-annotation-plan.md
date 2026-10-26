# Required action annotations: controlled seeded comparison

## Material Passport

Date: 2026-10-27. ARS experiment preparation; official=false, claim-ineligible.
Status: PREPARED_AWAITING_EXACT_EXECUTION_APPROVAL. No provider execution, credential read or new target
execution. The user asked to proceed with request structure and model settings
examined separately; this preparation fixes the model and changes one interface
factor. Exact paid execution approval remains separate.

## Question and alternatives

Does requiring a public action explanation on read/search/probe calls change the
agent's ability to reach a justified repair from the same observed failed candidate?
The [previous source-ready run](2026-10-27-source-ready-repair-live.md) delivered
useful failure evidence and valid source anchors, yet all twelve actions inspected
source/tests. These were valid requests; the six settled responses did not exhaust
their output ceilings. Request-construction failure is therefore not an established
explanation. Required explanations may shape continued exploration, or may help
avoid premature edits. Model action selection or other missing facts may dominate.

This small comparison tests that annotation requirement, not all request structure,
not a context-size increase and not the full historical thin-policy bundle. A null
result would weaken this narrow interface hypothesis under the tested conditions;
it would not justify adding another mandatory diagnosis stage.

## Fixed conditions and intervention

| Condition | A | B |
| --- | --- | --- |
| Read/search/probe annotations | Required `turn_decision` with mode/basis/evidence_goal and nullable memory update | Nullable root `memory_update`; no required action commentary |
| Full exception/source messages | Identical | Identical |
| Main instructions and operational tool descriptions/arguments | Identical | Identical |
| Edit/stop schemas and repair intent | Identical | Identical |
| Opportunity policy and cost admission | Identical | Identical |

Both arms use `request-annotation-pair-v1`: Astroid-1333,
`tasks/dev-train/current-dev20/13/public.yaml`, the same first failed saved candidate,
the same source packet (148 public lines), and gpt-5.4-mini-2026-03-17 at xhigh.
Each uses a fresh isolated workspace and conversation, eight normal responses,
one correction, twelve model actions, one diagnostic probe, one accepted new edit,
40K normal/25K correction output, 60K input, 600 seconds preparation/model time,
and the existing separate 390-second host verification deadline.

Credential path: `C:/Users/geonj/Documents/PatchLoop/.env`. One run per arm, fixed
order A then B. Each arm keeps the previous USD 1.20 cap, so the new invocation cap
is USD 2.40. This is a proposed cap, not authorization inherited from prior runs.
Splitting USD 1.20 between arms would alter the previous per-arm opportunity and
trigger more conservative cost-based tool narrowing.

The [opportunity policy](2026-10-27-repair-opportunity.md) is fixed in both arms.
Its effect is not identified by this comparison. The existing thin schema/parser
and gateway are reused; thin system prompts, state projection, planning changes
and a new note lifecycle are not introduced. Optional note payloads remain native
transcript data in this diagnostic, as before. Operational notes processing in
the ordinary runner is outside this comparison.

## Procedure and stop conditions

Preparation checks runtime, calibration, source/dependency identity, public task
and frozen candidate; registers neither new target execution nor provider work.
For both first requests, all messages/provider settings are equal. Normalizing
only the specified annotation locations must make the tool schemas equal too.
At collection each arm rechecks existing images and fresh registered source anchors
before credential loading. No image pull/build/start is implicit.

Run the model until one accepted edit or an existing bounded terminal condition.
After an edit, replay the unchanged original/control program and run the registered
public regression suite. No finish/submission or private acceptance is performed.
Count immediately before dispatch, keep SDK retries at zero, and stop both arms
on count/transport/billing uncertainty or unsafe external-execution state. Preserve
the failed or unknown result; no automatic replacement run or continuation.

## Outcomes and interpretation

The primary conditional outcome is whether the frozen original failure is resolved,
the control is unchanged and public regression passes on the candidate. Record each
component separately. A patch, helper PASS, or submission eligibility alone is not
repair success or independent task acceptance. Record no edit, invalid probe,
unresolved/new exception, failed regression and unknown execution distinctly.

Secondary measures are valid targeted probe, first edit, action sequence, annotation
and protocol errors, normal/correction responses, input/output tokens, settled cost,
and time. Compare public behavior without inventing missing B action rationales.
Required-commentary removal also removes a source of self-reported rationale, so
that rationale is not a symmetric outcome measure.

One seeded development case and one stochastic run per arm are exploratory. A
difference can motivate a replication or a model-setting comparison, not automatic
policy adoption or a general accuracy claim. Fixed order, caching and shared service
conditions limit timing/cost interpretation. More information may still be needed;
delivery of supplied evidence is not proof of information sufficiency.

## Prepared artifacts and local validation

The manifest, first requests, comparison audit and execution command are saved under
`C:/pt/request-annotation-plan-v1/`. The command is `run.ps1`; planned results are
isolated under `C:/pt/request-annotation-live-v1/`. Exact manifest hash:
`sha256:936f0da9d58c0c04c7924b50d71fc733e2394cb55373462fa566eaad0b2e4bb4`.
Comparison audit hash:
`sha256:21c068d82595cec71baba59c3a0780bf8cc587cbc5e162c46cf6bf6535c76287`.

Focused validation: 61 PASS in 40.59 seconds of process time; quick: 472 PASS in
113.20 seconds, including isolated mock evaluation. Ruff and diff checks passed.
JUnit reports are in `C:/pt/request-annotation-local-v1/`. Existing probe and public
regression image IDs matched the saved identities; no container was executed.

Local tests cover exact initial-input/schema separation, identical registered
read/search/stub-probe/edit behavior, native thin transcript preservation, one
bounded correction, gateway policy mismatch before dispatch, manifest binding,
exact caps, and per-arm source validation before credentials. They identified an
operator correction bug for wrong-shaped thin annotations; the operator now uses
the shared rejected-call serializer to retain those fields. The older opportunity
test's probe request used null purpose and exercised a rejected attempt; this
follow-up changes the fixture to helper purpose and asserts successful stub-probe
execution. The earlier reservation accounting evidence remains distinct from
this stronger tool-execution check.

Initial request UTF-8 sizes are 61,233 bytes (A) and 59,674 bytes (B), not token
counts. All initial messages are equal; only three tools' annotation schemas differ.
Subsequent histories may diverge as a consequence of different annotations/actions.
No model-setting change is made in this phase; a later model
comparison needs a fixed request representation and its own exact scope, including
any price-dependent output-admission differences.
