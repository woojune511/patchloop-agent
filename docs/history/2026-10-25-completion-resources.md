# Reuse-aware completion forecasts and bounded failure diagnosis

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run / local mechanism validation
- Origin Date: 2026-10-25
- Verification Status: IMPLEMENTED and LOCALLY_VALIDATED; live experiment NOT_RUN
- Version Label: completion-resources-v1
- official=false; claim_eligible=false

## Problem and decision

The [closed diagnosis](2026-10-25-output40-diagnosis.md) identified two resource
effects in a failed repair trajectory: the protected physical-call horizon closed
diagnostics despite repeated original-case feedback, and the ordinary 40K output
setting also reserved a 40K protocol correction. The forecast still counted a
failed finish even where early replay would deliver that failure and finish would
reuse its receipt. This matters because the model selected three ineffective
edits without another discriminating observation, before the final cost stop.

The user authorized the proposed implementation and short local verification.
This follow-up changes scheduling/contracts; it does not change the task patch,
inject caller-specific repair hints, run another model solve, resume a closed run,
increase a cap or perform a real container/evaluator experiment. Prior run and
diagnosis artifacts remain immutable. Baseline commit:
`3df9270c5d1370b4de6c55fe5a963de87d2a992e`.

## Changes and rationale

1. The pure completion forecast removes one failed finish call and action only
   when all cases are acquired originals with healthy comparable settled current
   evidence and early execution is available. It preserves all real replay,
   check, read and mutation/rejection work. Pending/deferred, mixed, unknown and
   conflicting cases retain fallback. The diagnosed pure state changes protected
   model calls 11 to 10 and tool actions 15 to 14; minimum 3 calls/4 actions stays.
2. Optional `max_correction_output_tokens` / `--max-correction-output-tokens`
   separates the correction allowance from ordinary `max_output_tokens` under
   `completion-recovery-v1`. Omission preserves historical serialization and the
   coupled contract. Explicit values, including values above the normal ceiling,
   bind model identity, envelope, prepared request, dispatch and resume. Only the
   first protocol correction receives the reserved full allowance.
3. A comparable current refutation of an acquired original case on a nonempty
   candidate provides one diagnostic opportunity using minimum completion
   reserves. Source read/search or probe may spend speculative recovery, while
   repair/check/replay/finish must remain fundable. The ordinary cost cap and
   correction reservation still apply. A possible new probe binding requires an
   additional future replay action. The model batch consumes the credit even on
   rejection, cached replay or interruption; automatic replay does not. Restart
   and repeated same-diff failure cannot renew it. A new candidate needs new
   comparable failure evidence. Finish remains blocked while failure persists.

The [resource contract](../../.agent/completion-resources.md) contains exact
eligibility, tradeoffs and public projection behavior. Native bounded reviews
checked the forecast and independent allowance; they are shared-context engineering
reviews, not blinded independent acceptance evidence. Review found and corrected
the possible additional probe-case replay slot and prepared-request ceiling binding.

## Local verification

The focused selection is `tests/recovery-budget.txt`: pure bounded outcome
traversal, resource boundaries, real local observer fixtures and stubbed provider
dispatch/recovery. Network and real Docker use are blocked in these tests.
The existing quick suite supplies isolated mock evaluation. These tests establish
mechanics, not an LLM's ability to choose a useful diagnosis or repair this task.

| Selection | Result | Elapsed |
| --- | --- | --- |
| Initial focused owner selection | 56 PASS | 45.130s |
| Final diagnostic boundaries after batch-consumption refinement | 12 PASS | 14.943s |
| Quick, two workers, no worker restart | 305 PASS | 30.657s |
| Ruff / whitespace | PASS | under 1s |

The selections overlap; counts are not a combined independent sample. Each
focused invocation stays below two minutes. The final diagnostic selection adds
cached replay and interruption before action start. Quick includes the existing
segmented reproduction smoke through isolated mock acceptance; mock safety stays
NOT_RUN. Stubbed provider dispatch demonstrates general40K/correction25K and
general8K/correction25K behavior, exact request counting and one correction after
resume. Synthetic provider/evaluator identity mismatch remains EVALUATOR_ERROR in
those dispatch fixtures; their submissions are not counted as acceptance.

External evidence root: `C:/pt/od-validation1`. JUnit XML, source hashes and the
local result receipt are stored outside the repository; the receipt is copied
into CAS and referenced from hash-chained dev-run-v1 journal
`runs/run_dev_completion_resources_local_v1.jsonl`. The initial 56-test run preceded
the final diagnostic consumption refinement; the final 12-test/quick results
validate that change. Runtime identity and the implementation commit are bound
by the external receipt/follow-up journal entry. No historical record is rewritten.

## Unresolved scope

Spending speculative recovery can leave no recovery path after another failed
mutation/check. The minimum monetary path still reserves only 128 output tokens
per ordinary future call; it does not promise useful generation. The correction
allowance remains reserved until consumed/terminal, so diagnosis can still be
unaffordable near the cap. The new opportunity is not mandatory and does not prove
that the model will inspect the relevant caller or abandon an incorrect hypothesis.

Live repair, paid rerun, target-container execution, Linux CI and generalization
are NOT_RUN. All earlier allocations remain closed. A later comparison would
need a fresh exact authorized scope and should measure diagnostic selection,
observed intermediate values, current-original resolution, regression results,
submission, independent acceptance and actual cost separately.
