# Host watches and a compact original-call diagnosis stage

Date: 2026-10-26. Follow-up to the [request analysis](2026-10-26-diagnosis-mode-analysis.md).
Status: local implementation and validation; official=false, claim-ineligible.
Baseline commit: `e0681222863357f014e5e499cd1fbd555d2828e8`.
External record: `C:/pt/diagnosis-stage-local-v1`, dev-run-v1 append-only journal.

## Problem and decision

The preceding live run exhausted 16,380 normal and 25,000 correction tokens without
returning its first diagnostic action. The model still chose watches/fields and
supplied general decision metadata; the probe schema had 7,158 compact characters.
The correction carried general guidance and an opaque continuation. This blocked
the intended diagnosis before its relevance to repair could be evaluated.

The selected intervention reduces that decision to an enclosing caller. It does
not increase output or monetary limits, infer a repair from coverage, or change the
original failure oracle. Schema/context burden is a plausible cause, not a proven
explanation of internal generation. A real model may still select an uninformative
focus or fail to form a correct repair despite successful diagnostic execution.

## Implementation

1. `diagnosis_request.watch_plan` reads tracked current public bytes through the
   gateway, checks the observed file hash and uses AST ownership to derive changed
   functions and their parameter names. Unique function/frame, four-watch and
   six-field limits apply. Existing static line construction and hash binding remain.
2. Pending run_probe accepts only `focus {origin,path,function}`. The shared
   selection validator, batch validator, parser, execution adapter, attempt cards
   and recovery support absent annotations. Other offered diagnosis tools also
   omit annotations. Raw action/input identity and host canonical admission remain
   separate; saved older admissions still replay without recomputation.
3. The diagnosis model view contains public task/call/candidate evidence, host
   watches, relevant current source, latest results, corrections and existing budgets.
   General notes and plans remain in the audit/journal. Segmented-v1 uses explicit
   entry/return boundaries and a diagnosis prompt without generic plan-review work.
4. No-action/incomplete response correction starts a fresh diagnostic segment after
   validating old continuations. Invalid request fields use field correction;
   source-binding rejection corrects focus. Unknown actual diagnosis retains the
   original verification gap. All existing counters and cost admission remain global.

Append/window policies retain native history and receive the small current view;
only segmented-v1 can discard the old continuation through its existing handoff
contract. Ordinary prompt instructions explicitly pause annotations in diagnosis.
Module-level or ambiguous changed frames cannot be guessed into a watch. Such a
request remains unverified within the existing bounds.

## Local evidence

Validation uses tiny authored public fixtures, a fake provider, and existing local
isolated mock evaluation. It does not execute a live model or the F0010 task.
Results and durations are recorded in `closeout.json` and XML/log artifacts under
the external record above. Final quick: **369 PASS in 81.14 seconds**. Ruff: PASS.
Focused selection: 108 PASS plus one test-output assertion failure in 103.23 seconds;
the assertion was corrected and its test passed in 5.28 seconds. The later contract,
plan-restoration and field-rejection delta was **20 PASS in 30.29 seconds**.
Continuation/thin-policy/document owners: **8 PASS in 8.90 seconds**. The focused
selection now has 112 cases; these results are per-phase evidence, not a claim that
a single final 112-case suite was rerun. No known failing assertion remains.

- Host watches retain the original root, failing call, candidate and source hashes;
  raw focus-only requests survive replay and crashes at admission/dispatch/result.
- Invalid focus correction is linked to the same case/candidate. Rejected requests
  do not execute. Unknown traces cannot release another repair.
- Real runner controls cover diagnosis entry, incomplete/no-tool/field correction,
  focus-only execution, normal repair return and saved plan restoration.
- Correction and segment-commit crashes recover once; returned diagnostic execution
  recovers without another dispatch. Repeated no-action output cannot refill its allowance.
- Corrections decrease remaining model calls, retain tool counts before dispatch,
  consume the existing correction allowance and increase settled fake-provider usage.
- Nine ordinary current/thin/planning/probe schema combinations match the baseline.
  Pending probe serialization is 871 characters. This is a byte/character comparison,
  not a provider token count or a performance result.
- General guidance stays within the existing bound at 7,964 characters (10,773 with
  brief planning); the new exception did not justify raising that limit. Quick tests
  caught the initial overflow and pinned current prose was updated after shortening it.
- Scripted repair reaches independent isolated mock acceptance with safety NOT_RUN.
  Fake-provider controls retain their expected synthetic-environment evaluation error;
  this is not presented as acceptance or real-model repair success.

Initial tests caught an execution-adapter field leak (`focus` in the canonical replay
arguments), a residual ordinary annotation requirement in batch execution, and a
request-kind mismatch in correction receipts. These were fixed without mutating raw
requests or relaxing the original replay identity. Read-only review also identified
the attempt-card annotation requirement, which the stage-aware card now handles.
The quick suite was rerun after its seven prompt-bound/current-prose failures were
fixed. The focus-only preflight now rejects legacy extra fields before suggesting
null values that would themselves conflict with the new schema.

## Scope and next question

The local evidence supports keeping this smaller stage as the next implementation.
It does not establish that it reduces model reasoning use or repairs F0010. Existing
original-case, check and acceptance gates remain independent. A future exact-scope
live authorization is needed to test focus quality, actual diagnosis dispatch,
use of its evidence in repair, original-case repair and total cost.
