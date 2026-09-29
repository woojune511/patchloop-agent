# Public execution observations linked to verification concerns

Date: 2026-09-29. Implemented in mutable dev-head; local validation, no new provider
calls, task solve comparison or demonstrated quality gain. Follows the
[lifecycle audit](2026-09-29-verification-concern-lifecycle-audit.md).

## Problem and scope

Some public verification questions were never registered as concerns. The first
increment retains observed unsuccessful executions independently of the model's
choice to register an interpretation, and allows an explicit link to existing
concerns. It does not require the model to classify every event or add a new call,
required check, hard submission gate, automatic repair or runtime version.

## Implementation

working_notes.verification.observations derives from completed action_finished
records for run_check/run_probe. Existing append-only action journals are the durable
record: no second mutable store, new recovery event or duplicate execution is needed.
The model view keeps the latest six unique action IDs and an omitted count; older
records remain in the journal. Linked concerns retain their own original observation.
Current/historical/unknown currency uses the action-completion workspace diff, never
the current workspace retroactively. Unrelated PASS does not erase a failed record.

The compact projection preserves action ID, input hash, origin, tool, candidate hash,
action status/error code, execution flags and bounded question/check identifier.
It does not duplicate stdout/stderr, infer applicability from exception strings,
or declare candidate bugs. behavior_verdict=not_assessed separates unsuccessful
execution from a correct behavioral interpretation. Syntax, setup and assertion
failures can all require different explanations; this increment does not invent
an automatic semantic classifier. Public registered checks own their success verdict,
including allowed nonzero success exit codes. Unhealthy/truncated observations
remain visible without converting them into task-acceptance failures.

Upsert's existing evidence_action_id can now refer to a previously completed
unsuccessful check/probe. Null still creates a hypothesis-only concern. The gateway
validates the reference and attaches original provenance separately from the
model-authored statement. A reference to a missing, pending, healthy or unrelated
tool action is rejected as an observation link. Upsert with a different observation
cannot overwrite an existing link; use a distinct concern. A newly attached link
reopens the concern; exact repeated original/progress plus the same link is a no-op.
Resolution evidence remains separate from the original observation.

No tool schema fields were added. An evidence ID formerly ignored on upsert now
has this checked linking meaning; dismissal still ignores the unused evidence ID.
The system prompt is unchanged: observation interpretation travels with the compact
catalog and linking is described on the evidence field. Existing prompt/memory-schema
size caps and wire-shape hashes stay unchanged; description-inclusive snapshots were
updated for the new field guidance.
Old journal snapshots without observation fields remain valid, and replay restores
stored decisions rather than reinterpreting old actions. First-non-null update
ownership, action_id/input_hash idempotency, original statement immutability and
nonblocking annotation errors remain intact. Submitted/check gates are unchanged.

Operator-supplied public feedback stays in its existing separately labelled channel;
it is not silently imported as a registered agent observation. This first increment
covers durable registered tool outcomes only. It does not solve the HF external
feedback omission by claiming that receipt was an agent-executed check.

## Validation and evidence

Focused concern/identity/gateway-flow validation passed 68 tests, followed by four
final observation tests after adding the nonzero-success-code case (69 distinct
focused tests across the final set). Includes bounded/deduplicated observations,
no bug verdict from a syntax-error fixture, missing-link rejection, immutable origin,
retention through unrelated PASS/focus/edit, restart and the existing unresolved
concern finish behavior. Ruff and documentation checks passed.

The full suite ran as four isolated pytest processes: 3,641 collected, 3,610 passed,
15 failed and 16 skipped. Failures exposed the existing prompt/schema size caps and
description snapshots; editing descriptions during that run also triggered runtime
identity checks in recovery tests. Removed redundant system-prompt additions,
shortened the field description within the unchanged caps, and refreshed only the
description-inclusive snapshots. All 15 failed cases plus the four observation tests
then passed on frozen final code (19 tests, 49.061 seconds). This is a full-suite run
plus targeted corrections, not an uninterrupted final-code all-green suite.
Logs, JUnit files and cross-checked closure: C:/pt/tmp/observation-link-shards-0929.

Mock CLI smoke reached EVALUATOR_PASS, four model steps/five tools, cost zero:
C:/pt/observation-link-smoke-0929, run_dev_03a08fd7a01b4cbf.
Final-code repeat also reached EVALUATOR_PASS with the same call counts and zero
cost: C:/pt/observation-link-final-smoke-0929, run_dev_ab97ea39d9074431.
Mock safety remains NOT_RUN and claim_eligible=false; this is not live quality proof.

Provider-free projection of 17 prior unsuccessful public actions:
C:/pt/analyses/verification-observation-replay-20260929-v1/final-projection.json,
with source and implementation hashes in the append-only audit journal. The initial
report remains preserved separately. These are saved-output projections, not task
or probe re-executions. Historical experiments and results remain unchanged.

Next measure whether actual models link and correctly interpret the recorded
observations, and whether verification/repair improves without unnecessary work.
No paid comparison is authorized by this implementation request; do not infer
quality from catalog size or linking frequency.
