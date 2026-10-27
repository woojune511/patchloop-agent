# A known empty candidate must not become an uncertain evaluation

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: implementation, local verification and live incident diagnosis
- Origin Date: 2026-10-27
- Verification Status: R0 EXECUTED; continuation fix LOCALLY TESTED; R1 pending
- Version Label: feedback-source-empty-diff-v1

The authorized [feedback/source comparison](2026-10-27-feedback-source-plan.md)
started at commit `95d9a0ce`, manifest
`sha256:844256532293cfdeaf8ecdc3f1a3924dd8eb1bdcf9381d1df967fbc7e58b228e`.
R0 made seven settled responses and ten model tool actions, then used its one
additional edit to undo the entire saved patch. This is a known no-repair outcome,
not a successful repair. Public checks confirmed F0010 remained; regression passed.

The reused saved-candidate evaluator requires a nonempty diff. Its precheck
therefore returned PRECHECK_FAILED with zero evaluator dispatches, and the wrapper
interrupted collection before R1. The original journals and safe summary under
`C:/pt/feedback-source-live-v1` are preserved byte-for-byte. No model or evaluator
call is repeated. R0 spent $0.10363125; independent token-rate recalculation agrees.
All seven input counts/provider calls, six candidate public probes, six baseline
probes and one regression check are complete. The 13 public external executions
confirmed cleanup; all 13 public receipt hashes and sizes match.

`feedback_source.acceptance` now returns NOT_RUN_NO_DIFF without dispatch for a
known empty diff. Nonempty candidates still use the opaque evaluator; uncertainty
still stops the comparison. A focused test covers an empty R0 continuing to R1,
and another ensures an uncertain nonempty evaluation prevents R1.

The incident-specific `diagnostics/feedback_source_remaining.py` permits only the
unstarted R1. It freezes original manifest/model/summary bytes, verifies seven
settled calls and no pending input count, checks the original workspace still has
an empty diff, and rejects an existing R1. It requires identical model requests,
source bundle, scope, credential path and runtime. The only changed existing code
binding is the post-model no-diff operator handling. It restores R0 settled usage
to the original $2.40 invocation ledger, retains R1's $1.20 row cap, creates a fresh
single-use result directory and never restarts the interrupted directory. This
incident's remaining result directory is fixed in code, so selecting another path
cannot reopen R1 or omit its expenditure from the restored ledger.
The current user authorization covers this remaining arm; no new repeat or budget
is introduced. The original PRECHECK_FAILED stays in evidence, accompanied by a
NO_CANDIDATE_DIFF interpretation instead of being rewritten as acceptance FAIL.

Local operator and remaining-condition validation: 25 PASS in under five seconds;
Ruff and whitespace checks passed. One pytest cache-write warning did not affect
the result. The previous implementation's 472-test quick suite already passed;
this correction changes only post-model diagnostic orchestration. The broader
21-failure selection described in the implementation report remains unresolved;
its baseline status is not established.

This incident changes handling of a deterministic no-repair outcome. It does not
justify relaxing identity, uncertainty or billing stops, nor increasing model
context, output or edit limits. The completed comparison is recorded separately.
