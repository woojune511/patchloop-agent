# Diagnostic continuity: stored plans versus actual repair inputs

Date: 2026-11-01 KST. Status: CLOSED operator audit; runtime change proposed, not applied.
No new live provider call, benchmark execution or independent evaluation.

## Question and changed decision

The user asked whether the existing plan and notes actually carry established
conclusions and remaining questions into the next decision. The
[full20 result](2026-11-01-pre-edit-dev20-results.md) selected this question because
task18 reopened previously answered diagnostic questions and consumed all 40 calls.
Possible explanations were absent model updates, failed note storage, lossy delivery,
or deliberate repetition despite sufficient delivered evidence.

**There is a structural delivery gap before the first repair.** The compact repair
view removes working_plan and its review_request, changes the handoff review flag
to false, and replaces the ordinary planning prompt with the compact repair prompt.
Read/search/probe schemas still offer nullable plan and memory updates. Thus the
write mechanism exists while the corresponding plan/read-and-review context is absent.

This refines the previous audit's wording: its context_artifact has the generic
revision1 plan, but that artifact precedes projection. The model's actual current
state did not retain that plan during compact repair. Stored review requests cannot
be described as signals the model received and ignored. The earlier closed record
is preserved; this follow-up records the more precise delivery boundary.

The next intervention should first align the existing compact repair view, planning
state and advisory update instructions. A new memory subsystem, larger budgets,
mandatory notes, extra review calls or compulsory probes are not indicated. This
audit establishes a delivery mechanism and observed discontinuity, not that restoring
the plan will by itself improve model reasoning, task acceptance or latency.

## Scope and method

- Audit HEAD `13e06587786d5f77df5fc98f5cb3c7fb802263bc`; unchanged runtime
  `sha256:a1c2a5948d4cb0992f1cdecbe49e1af4a5566dae69145eab2d131f8d20213b20`.
- Read all 274 dispatched model inputs from the closed latest full20. Unsent
  preparation/count candidates are excluded. Verify their artifact hashes and
  each task journal's final chain hash against the closed summary.
- Compare stored context_artifact with the last actual developer record whose
  kind is harness_current_state, and inspect the actual system prompt/tool schemas.
- Exclude every provider reasoning item before inspecting public input. No
  continuation artifacts, private evaluator bodies, hidden tests or reference patches.
- Trace task18's completed public probe stdout, action IDs, public decision bases,
  note/plan receipts and segment boundaries. Inspect the current source path and
  reproduce its projection locally without running the benchmark or a model.

Across 274 actual requests, **174 used the compact repair view and all omitted
working_plan**. In 146 of those, a plan already existed in the stored context.
Fifty stored contexts had review_request.requested=true without an actual delivered
working_plan. These counts concern the observed batch and pre-projection state;
they are not all possible review signals or proof of model uptake.
These counts mean absence from the authoritative current-state slot, not absence
of every historical plan string. Task18's initial plan text still appears in earlier
native arguments at calls2/8, but is absent after the call9 handoff and at the
repeated decisions in calls31/32. Historical presence is not durable plan delivery.

## Task18 timeline

| Phase | Stored state | Actual next input |
| --- | --- | --- |
| Calls1-34, through the first edit | Revision1 from call1 onward; no findings or open_question | Compact repair; working_plan absent, handoff review false; empty repair_intent |
| Call35 after first edit | Revision1 plus mutation review | Ordinary planning state and full planning instructions return |
| Call36 after public regression failure | Revision2 plus failed-check review | Model writes revision3, note n1 and an evidence-linked remaining question |
| Call37, input seq558 | Accepted n1 and revision3 | Both the finding text and remaining question are present, with source/result references |
| Calls38-40 after source repair | n1 source dependency changed; revision3 remains | Note expiry is explicit; open question remains; plan is historical, not certified current proof |

The 34 compact inputs include the first call without an existing plan and 33 inputs
with the stored plan omitted. Ten pre-projection contexts requested a review. No
pre-edit memory_update was rejected, evicted or lost: none was submitted. The sole
working_notes_updated event is seq549 after the public regression failure; it was
accepted without diagnostics. Native presentation renames statement to
model_interpretation and adds evidence-delivery metadata, preserving the actual text.

The later note's expiry is not accidental loss. The source repair changed the cited
L036 lines, producing last_source_lifecycle.expired_notes with reason source_changed.
The open question survives with currency metadata. This is distinct from a note
disappearing on a context handoff or from a tool-result-only note's lifetime.

### Observed results become unavailable before repeated questions

| Original observation | Actual inputs carrying its full stdout | First absent input | Later repeat |
| --- | --- | --- | --- |
| Probe1: L036-only CTE first target has 0 spaces | Calls8-19 | Call20 / seq290 | Probe8 at call31 / input seq461 |
| Probe2: L036 then L003 gives CTE8/plain4 | Calls14-20 | Call21 / seq306 | Probe9 at call32 / input seq476 |
| Probe4: L003+L036 path gives CTE8/plain4 | Calls20-27 | Call28 / seq418 | Same default-versus-isolated-rule question reopened at calls31-32 |

These are completed stdout observations on the unchanged base, not failed setup
retries. Unique output markers disappear with the full outputs; the earlier probes
also leave recent_probes. Later probes add presentation detail but revisit the
already tested central distinction.

Public action basis seq295 explicitly says the minimal L003+L036 path stays correct
and another default rule/fix-loop interaction is likely. It requests a useful next
observation. However, plan_update and memory_update are null. By seq466/481 the
bases again treat the L036-only/L003-follow-up distinction as unresolved. Another
earlier basis, seq226, had over-attributed the cause to L003 after L036 despite
incomplete discrimination. Retaining every interpretation as fact would therefore
be unsafe; conclusions need their observations, scope and unresolved alternatives.

## Implementation path

1. [runner.py](../../patchloop/dev/runner.py), around2690, builds working_plan in the
   operator context. [working_plan.py](../../patchloop/dev/working_plan.py) retains
   revisions/reasons and derives advisory review requests from public events.
2. The segmented builder in runner.py, around3335-3363, selects compact repair
   whenever repair_context.pending is true. It uses repair_context.system_prompt
   instead of the ordinary prompt that appends working_plan.instructions.
3. [repair_context.py](../../patchloop/dev/repair_context.py), project at97, omits
   working_plan. Existing note findings, question and verification data survive
   under repair_intent. The compact prompt permits null updates; it contains no
   normal plan-review instructions. It does not forbid every optional note update.
4. runner.py around3471 explicitly sets segment_handoff.review_requested=false
   during repair. The stored review request is therefore not a delivered request.
5. [segments.py](../../patchloop/dev/segments.py), boundary_reason at160, starts a
   new segment after a major result has had one subsequent valid action response.
   It does not verify that the response retained the result's conclusion. Old native
   exchanges do not automatically survive the new segment.
6. runner.py retains only the most recent three probes and three attempt cards.
   Optional evidence_focus exchanges are skipped in compact stages. The journal
   preserves full history, but this does not make that history part of the next request.
7. [tools.py](../../patchloop/dev/tools.py), record_working_notes_update at2089,
   records only an actual non-null update, before the next tool batch. It does not
   infer a finding from stdout or automatically copy an action basis into memory.
   [working_notes.py](../../patchloop/dev/working_notes.py) already supports prior
   tool-result evidence; a new storage type is not required for these observations.

The existing planning delivery test explicitly expects compact repair to omit the
plan. This is current design behavior, not an intermittent serialization or recovery
failure. The proposed change revises that design choice, while preserving compact
mutation schemas and the distinction between advisory interpretation and evidence.

## Smallest proposed change and checks

Keep the existing bounded working_plan and review_request available during compact
repair, and align the compact prompt with those advisory signals. On an ordinary
read/search/probe response that already offers annotations, the agent can retain a
short evidence-backed conclusion and remaining question before the next handoff.
Do not add annotations to core mutation/observation schemas solely for this purpose,
add another model call, require a note, or promote a model conclusion to verified fact.

Validate actual assembled input across a result boundary, not merely the stored
context artifact: plan/review delivered, existing finding/question preserved, null
updates allowed, source edits marking stale evidence, and ordinary mutation/check/
submission still possible. The five stale mock tests below need adaptation to their
current annotation-free mutation contract. A later live result must separately
measure repetition, original-task correspondence and repair correctness; the audit
does not authorize or establish that outcome.

## Local validation and remaining test work

The deterministic public audit passed all 274 input comparisons and hash checks.
Selected existing tests produced **23 PASS, 5 FAIL in 33.83 seconds**. Four failures
are the parameterized original-purpose mock test in test_plan_revision_evidence.py;
one is the note-recovery mock test in test_dev_notes_feedback_v15.py. All terminate
before mutation with mock model failed: AttributeError.

Their custom adapters unconditionally dereference turn_decision. Current
MockDevAdapter deliberately omits it for an annotation-free replace_text schema.
Pure mock generation on saved failed contexts with the same frozen runtime's
mutation schema reproduces turn_decision=None. These are stale test-adapter
assumptions, separate from the delivery omission; they were not silently skipped
or changed to produce a green result. They are outside the existing quick selectors
used by the previous full20 preflight. Their normalization remains implementation
work, alongside the proposed delivery change.

This turn changes documentation only. Documentation tests: **6 PASS in 0.14 seconds**;
no full quick/Ruff rerun is claimed. Existing local fixture failures do not invalidate
the read-only comparison of saved live requests, but the selected test suite is not green.

External evidence: `C:/pt/diagnosis-continuity-audit-20261101-v1/` contains audit.py,
audit.json (all input references and task18 timelines), fixture-diagnosis.json,
focused-tests.xml, documentation-tests.xml, validation/commit receipts and
`runs/run_dev_diagnosticcontinuityaudit.jsonl`. New records are hash-bound and
append-only; prior experiment roots and closed history are unchanged.
