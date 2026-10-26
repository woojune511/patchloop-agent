# Preserve captured target failures after helper failure

Date: 2026-10-26. Implemented and locally validated; official=false, claim-ineligible.
ARS experiment-agent, validate mode. No new paid execution allocation.

## Problem and decision

The [propagation audit](2026-10-26-target-exception-propagation-analysis.md) found
that the last Astroid pilot captured a current `FileNotFoundError` under the same
selected-call inputs and environment, then its helper raised `RuntimeError`.
`target_outcome.bound_failure` required outer passed/zero, so it discarded the
positive target-failure evidence. The existing repair/diagnosis/finish-blocking
path therefore did not activate. This was selected because it let a known current
failure reach submission after unrelated public regression PASS.

The new real regression reproduced target_failure_count=0 on the unchanged runtime.
This supports correcting the classifier, without adding a new tool, gate, reserve
or context ceiling. Whether the model would act on the corrected classification
and repair the original task is a separate unanswered question.

## Change and boundaries

- Accept settled outer passed/zero or failed/nonzero receipts with integer exit
  codes for selected negative evidence. The action must still have succeeded.
- Keep qualified unchanged-base acquisition, frozen binding/program, current diff,
  unique call identity, complete capture and matching inputs/environment checks.
  Failed setup, timeout, truncation, deadline/cleanup uncertainty, expected exceptions
  and SystemExit remain excluded.
- Preserve actual outer failure, helper stderr, global incomplete and whole-case
  UNKNOWN. No equality, verification or task-correctness credit is granted.
- Reuse existing `current_public_failure`, per-candidate diagnosis allowance,
  `needs_mutation` and runner/gateway finish blockers. Observer bytes, `_healthy()`,
  replay identities, prompts, schemas, budgets and context policy are unchanged.

Runtime change is confined to `patchloop/dev/target_outcome.py`. The same frozen
test helper succeeds on the baseline and, after an edit, captures a target
`FileNotFoundError` then raises its own `RuntimeError`. A real local subprocess
supplies the nonzero exit; the test does not manufacture a successful receipt.
Separate controls fail before the target or after a normal target return.

## Local evidence

Evidence root: `C:/pt/target-exception-fix-v1`.
Append-only `dev-run-v1` ledger: `runs/run_dev_targetexceptionfix.jsonl`.
Baseline commit: `0fb8ac39`.
Before runtime: `sha256:9632249097a22a6e8d8e63adf5df3d5000510f9e7da778360341afc9353799bd`.
After runtime: `sha256:61887a3ccfabb9db830b1ae63548babb53e411a7bcf5e351a202e0c5511c7f64`.
The ledger records exact commands, source hashes, timing and content-addressed outputs.

- Red: the new nonzero-helper regression failed at expected failure count 1 versus
  actual 0 on the unchanged runtime (5.86 seconds).
- Green: all 21 target-outcome tests passed (28.67 seconds), including real helper
  success/failure, helper-only controls, uncertain/changed receipt exclusions,
  compact-context visibility, finish rejection with public-check eligibility true,
  and restart reuse without duplicate replay.
- Quick: 451 passed in 61.16 seconds (62.83 seconds command wall time), including
  isolated mock evaluation. No separate duplicate smoke was run.
- Ruff and five documentation checks passed. Independent read-only code review
  found no blocking issue.

Read-only projection of the unchanged saved public receipt from
`run_dev_b4614e40c1714e81`, action event 266, now yields one target failure,
diagnosis available, no pending replay and whole-case `unverified` / `UNKNOWN`.
Its outer status remains failed/1. The old journal hash was verified unchanged.
Projection artifact: `sha256:f69c5fa59a5c0cc6e619a77ed7ca2737e3ee3dbb816954c29108bfd1ebe687fb`.
This projection executed neither the saved target nor the model or evaluator.

## Interpretation and next question

Local evidence establishes that a complete bound target failure survives a later
helper failure and drives the existing completion controls. It does not establish
F0010 repair, successful live-model use, an acceptance gain, or generalization.
The prior live outcome and its immutable artifacts remain unchanged. No provider
or Docker work ran in this change; fresh live behavior is NOT_RUN.

The next unresolved measurement is whether a fresh authorized solve uses this
failure signal to diagnose the actual remaining source-stream path and repair it.
Context continuity remains separate; this fix supplies no evidence for increasing
the input ceiling. No further execution is authorized by this record.
