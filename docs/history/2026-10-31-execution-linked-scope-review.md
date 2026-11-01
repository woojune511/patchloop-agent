# Execution-linked scope review and saved task 8 diagnostic

2026-10-31. Implementation and local validation are separate from the pending
paid diagnostic. No fresh solve, patch repair or independent acceptance is included.

## Problem, hypothesis and decision

The [latest task 8 audit](2026-10-31-affected-family-task8-results.md) showed a
verification-selection gap: public family source, the exact probe program and
post-edit instructions were delivered, yet the agent submitted after a narrow
helper repair, public regression PASS and replay. Its final assessment disclosed
an unresolved mapping to the reporter's input/caller. Available resources and
retained information do not explain the absence of new cases in that attempt.
The latest private failure's exact assertion was not inspected.

This matters because a changed rule can affect more inputs than the asserted
examples cover. Previous prose already requested a contract/case/evidence mapping;
another reminder alone would not change the mechanism. The user selected an
execution-linked review within the existing decision and a small saved-state
diagnostic. The hypothesis is that explicit source/execution references and
unexecuted dispositions will make a material gap harder to collapse into suite
PASS. Alternatives include incorrect source interpretation, an underspecified
public setup, an irrelevant perceived gap, or failure to construct a useful case.
A populated annotation alone is not evidence that this intervention helps.

## Implementation

Enabled brief planning now exposes nullable `scope_review` beside its existing plan
annotations. The review contains an affected scope statement, up to four public
read/search result IDs and one to four grouped cases. Each case records its public
input/caller construction, expected observable, `executed` / `source_inferred` /
`untested` disposition, optional execution ID and interpretation. Text fields and
identifiers are bounded. The existing prose mapping instruction is replaced by this
contract; the post-edit guidance directs the model to use it.

The host resolves an executed row to an already returned public check, selected
test or probe on the current patch, and binds its action/input/diff identity and
reported outcome. Failure, timeout and partial-output facts stay visible. An executed
row does not certify the named assertion, complete scope or correct interpretation.
Source inference needs an observed public source reference and gets no execution
credit; prior source diff identity remains visible. Forged, pending, wrong-tool or
stale execution references reject only the annotation, without an extra model call.

The existing working plan/event stores the latest review. Null and prose-plan
replacement preserve it; subsequent edits mark earlier evidence historical.
Completion and finish retain it alongside the assessment. There is no new tool,
independent reviewer, persistent concern store, mandatory probe or submission gate.
The model can still submit with unverified gaps, so actual uptake must be measured.
Planning-OFF schemas/identities and old absent-field serialization remain unchanged;
enabled planning contracts bind the new schema and guidance. Old artifacts are not
migrated or rewritten.

Preparation exposed a necessary integration issue: inline source retained after a
segment reset can omit the original read/search ID. Requiring an undiscoverable ID
would encourage redundant reads or rejected citations. A derived
`working_plan.source_receipts` index now supplies IDs for already selected repository
`source_spans` (not the separate dependency-source pool). It uses source
scope/path/file-hash/range intersections only, without source text or new authority.
It is capped at eight receipts and eight ranges each, with omission counts, and is
recomputed after stage projection. The normal runtime and saved-packet diagnostic
use the same function; the latter does not receive a stronger operator-only index.

An internal `evidence_events` seam lets a diagnostic resolve IDs against a validated
public checkpoint prefix plus its own new results. It does not replay old actions
as new executions, replace the diagnostic's plan lifecycle or change counters and
idempotency. Normal runs resolve against their own journal.

## Diagnostic question and bounded scope

Question: at the saved task 8 pre-submission decision, does the changed review lead
the same model to construct and execute a useful unverified public case?

The baseline is the original decision from run `run_dev_3be40073fc4640bd` at public
input sequence **171**, before finish. The candidate is fixed at
`sha256:be082f2721c12b34c2e8032d185297fb2e09379e45a46f5ce7fff1bd642862b9`.
The public packet already includes the required-check PASS and changed-diff helper
replay. Using this point distinguishes a new case from merely repeating needed
post-edit verification. No subsequent finish judgment, private evaluator body,
reference patch or operator counterexample is supplied.

Only the current review instructions/schema and declared diagnostic tool/budget
overlays change. Original public task, patch, source, executed programs/results and
unresolved purposes are retained. This is a fixed-candidate diagnostic with a new
continuation, not exact normal-run resumption or an unseeded repair comparison.

Proposed live scope: `dev-train/current-dev20/8`, model `gpt-5.4-2026-03-05`, xhigh,
25,000 maximum output tokens, credential file
`C:/Users/geonj/Documents/PatchLoop/.env`, **one attempt, USD2 invocation-wide cap**.
Limits: four model calls, 12 actions including report, two probes, 40,000 counted
input tokens per call and 600 seconds total. Provider waiting is bounded by the
remaining overall deadline. Allowed actions are registered public reads/searches,
probes and a diagnostic report; the candidate is immutable. No patch mutation or
independent evaluator is admitted. All counting, billing, transport or continuation
uncertainty stops new calls, with zero retries or automatic extra samples.
The [official standard pricing page](https://developers.openai.com/api/docs/pricing)
was fetched on 2026-10-31: this short-context GPT-5.4 scope retains USD2.50 input,
USD0.25 cached input and USD15 output per million tokens. Actual settlement, not
reservation or the cap, determines reported cost.

Success requires public grounding, a materially different unverified input/path/
outcome, an executed program that observes that outcome, and an interpretation that
matches its result. A new name, a table, probe count, helper PASS or honest report of
unknowns alone is insufficient. A discovered violation would establish diagnostic
discovery, not successful repair; this fixed-patch scope cannot establish acceptance
or repair gain. If only the format changes, there is no behavioral adoption evidence.
One saved development-exposed decision cannot establish a general capability ceiling
or a causal quality gain. Replacing tools/budgets and using a fresh continuation are
explicit differences from the original run.

## Local evidence and readiness

Local receipts are external at
[execution-scope-local-20261031-v1](C:/pt/execution-scope-local-20261031-v1/).
The first focused selection included the full planning/recovery owner suite and hit
its 115-second deadline before a complete result. That failed attempt is preserved;
the final focused selection is restricted to the changed contract, binding and
delivery paths. No provider or benchmark task was run by local validation.

The next focused attempt found a test-loader mistake: the new segmented integration
test used the loader's append-policy default. Supplying its actual context policy
fixed the test; 78 tests then passed. The first quick run passed 1,404 tests with
one host-symlink skip but failed the unchanged system-prompt ceiling
(10,964 > 10,809 characters). Removing redundant scope guidance reduced the prompt
to **10,778**, rather than raising the ceiling. These failed receipts remain intact.

With source-ID delivery included, final focused checks are **92 PASS in 46.16 seconds**
(48.035-second command wall), including real append/segmented mock flows reaching
isolated evaluation with unchanged call/action counts. Ruff passes. Enabled brief-v1
tool identity is
`sha256:fb118efd9c53f599800877d2ff25adb836ca56354b76c5ea03c8bf8605a8bf94`;
planning OFF remains
`sha256:312ac6385ef2fb65495fbb76da1f682f1135292252a6bd4ab64f3548862c0313`.
Runtime is
`sha256:0963cb074795d1809310160f02dd3c2bc42efe892af302846c3a6454bf598e75`.

The external driver passed **19 mocked diagnostic tests in 60.23 seconds** and Ruff:
[exact command/output receipt](C:/pt/evidence8-review-20261031-v1/validation-local.json).
It covers terminal-only review without an extra read/probe, null review, annotation
feedback, public-prefix separation, bounded execution and uncertainty stops. There
is no native JUnit for that invocation; no substitute test record was generated.
An exploratory recursive lint also selected the reconstructed upstream repository;
those upstream style findings were outside the driver scope and no upstream file
was edited.

[Preparation](C:/pt/evidence8-review-20261031-v1/preparation-result.json) verifies the
fixed candidate, prepared source/dependencies and existing image without a target
program, provider or evaluator call. The credential file was separately shape-checked
without recording its contents. The saved checkpoint contains four public messages
and 44 allowlisted public records before sequence171; it excludes later outcomes
and raw/encrypted provider reasoning. Its source receipt index has eight entries and
includes the already-delivered family-source reads, with no omitted action.
Checkpoint file hash:
`sha256:480451e2ec29916d447d996d63a323f2562a7de15d834c5c38b33f62f51b8efd`.
Prepared request canonical hash:
`sha256:92ef4053806e959df61ccb5cbe53db1ffc35cfa2e0a2c3e9a85f2171c9e1ccec`.

Final validation totals and the diagnostic's exact frozen preparation are recorded
in the external evidence directory. The final quick suite passed **1,418 tests /
1 host-symlink SKIP in 402.42 seconds** (404.157-second command wall), four workers
with no restart, including isolated mock evaluation. Local tests do not establish
actual model uptake or repair gain. The diagnostic allocation is not open until
its exact scope and new cap are authorized; prior allocations remain closed.
