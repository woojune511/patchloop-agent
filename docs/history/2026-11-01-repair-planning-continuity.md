# Compact repair: retain existing plans, notes and review requests

Date: 2026-11-01. Implemented and locally tested. No live provider call
or benchmark rerun. All prior paid allocations remain closed.

## Problem and decision

The [preceding actual-input audit](2026-11-01-diagnostic-continuity-delivery-audit.md)
found a delivery defect in 174/274 requests from the frozen dev20 run. Compact
repair dropped the stored plan and review request, suppressed the handoff review
flag and omitted normal planning instructions while offering optional annotations.
Task18 reopened diagnostic questions after supporting probe outputs left its
bounded context; no pre-edit finding was stored. A statement in action basis did
not become a working note. Later authored notes were stored and delivered correctly.

This matters because the existing continuity mechanism could not consistently
reach the decisions it was meant to inform. Fix delivery before adding memory
infrastructure or increasing limits. The audit does not establish that omission
caused repetition: failure to author useful notes, uncertain interpretation or
failure to act on delivered evidence remain plausible model-level explanations.

## Change

- Compact repair preserves canonical `working_plan` and `working_notes`, including
  note IDs, update receipts, findings and remaining questions. The separate
  `repair_intent` projection is removed from new inputs; old artifacts are untouched.
- Its enabled prompt reuses existing planning instructions. Shared guidance asks
  for a scoped finding/question with prior public evidence when a result changes
  the next decision, on the next useful action offering annotations. It distinguishes
  action basis from durable notes without requiring a note or separate response.
- Segmented repair reprojects the plan after handoff creation and retains the
  enabled review signal. Public source receipt identities match retained source.
- Mock fixtures respect the existing annotation-free mutation contract. They no
  longer write or dereference a mutation's absent `turn_decision`. Previously
  uncovered fixture regressions and actual-input continuity enter the quick suite.
- The operator input auditor follows the current projection and checks both its
  public state and saved native input bindings. Historical audits require their
  matching runtime; no old input is rewritten or resumed under changed identities.

The planning contract binds the delivery revision and instruction hash. There is
no new state machine, model/tool call, tool schema field, submission gate or budget.
Null annotations, bounded records, source expiry and current/historical evidence
meaning are unchanged. Mutation, original-observation and stop remain annotation-free.
Restored fields and shared instructions add bounded input bytes; admission still
counts the actual payload. No cost or latency reduction is claimed.

## Validation

Base HEAD: `54a7713e35d469d5b1f7346341e38bb1c3b76be0`. Runtime content hash:
`sha256:cfa5c287a3eb54ac3da3b2c42e9e153dd50d9f5a403912651076bc5b938acb95`.
Evidence root: `C:/pt/repair-continuity-local-20261101-v1/`.

Final focused validation: **12 PASS in 64.46 seconds**, under the two-minute bound.
The broader owner selection initially had 168 PASS/8 FAIL in 184.32 seconds.
Failures exposed stale append/segmented prompt wording (2), the previously added
edit_files tool missing from a fixture's expected tool set (3), and a fixture still
expecting the plan to be omitted in compact repair (3). Rechecks corrected these
expectations while retaining submission, counts, evidence and recovery assertions;
the final focused run passed every previously failing case. Earlier failed reports
remain in the evidence root. All 176 owner cases pass across the corrected attempts.

The original quick selection completed with 1,471 PASS/3 FAIL/one host skip in
875.22 seconds. Its three failures were expectations changed by this implementation:
the plan's former omission after diagnosis returns to repair, the old prompt length
cap, and the old planning-contract fingerprint. The shared guidance adds 355
characters; the current prompt cap increases by that amount, while frozen-arm caps,
60K input tokens, request-byte limits, model/tool slots and wall limits remain fixed.
The changed guidance/delivery contract intentionally changes the enabled fingerprint.
Targeted rechecks passed all five selected cases in 46.14 seconds, including all
three failures and two related diagnosis-correction variants. The original selection
therefore resolves to **1,474 PASS/one host skip**, without rerunning passed cases.
The newly added source-note selector below passes separately: the updated quick
manifest totals **1,475 PASS/one host skip across these executions**.

Ruff, diff checking, documentation bounds and local links pass. Four isolated mock
planning modes assert EVALUATOR_PASS; their replay and exact call counts pass too.
An initially oversized guide was shortened without changing runtime authority.
The runtime hash remained fixed throughout validation. Final source/document/test
bindings are stored in `validation.json` and immutable CAS objects, referenced by
`runs/run_dev_repaircontinuitylocal.jsonl`; the commit gets a separate receipt.

A separate source-note fixture had the same absent-mutation-annotation assumption
and outdated source line references. It now records both notes on an allowed
pre-edit read, citing the actual import and physical-line loop. The corrected test
passed in 9.71 seconds: two notes before editing, only the unchanged-source note
afterward, and the question retained at the next segment. Its one additional read
belongs to that deterministic test script, not a new runtime recording requirement.
This regression also joins the quick selectors.

The deterministic provider fixture receives the actual assembled inputs; it does
not call a model. It authors a note/question referring to a completed public probe,
then performs three later probes and a follow-up read across result boundaries.
After the first probe leaves the recent-three tail and native history, its scoped
finding, remaining question, evidence reference and update receipt still reach the
next input. With planning ON, plan text/revision and handoff review also remain.
With planning OFF, notes remain without introducing planning instructions/state.
Null updates preserve the plan. Counts are the scripted 10 model turns and 11 tool
actions; completed-run replay performs no new actions. The synthetic provider's
Docker identity intentionally cannot pass isolated evaluation for the local smoke
task; real mock smoke supplies the separate acceptance check.

## Interpretation and next question

The implementation addresses a demonstrated transport gap using the existing
mechanism. Local delivery does not show that a live model will save a useful
finding, interpret it correctly or choose the right repair. Required checks,
source staleness, independent acceptance and replay boundaries remain separate.

A future authorized frozen run should inspect whether task18 records a scoped
conclusion and remaining question before the old probe is evicted, receives them
at a later decision and avoids an equivalent repeated investigation. Task8's
original public-input correspondence and independent correctness remain safeguards
against optimizing note/probe counts alone. No such run or causal quality claim is
included here.
