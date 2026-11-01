# Original-case verification at submission

Date: 2026-10-22. User requested implementation and experiments after the recorded
caller/helper diagnosis. All work is official=false and claim-ineligible.

## Question and intervention

Repeated Astroid repairs replaced the original caller conditions with helper cases
and submitted after regression PASS. Exact observations and separate verification
reports did not reliably prevent this. Test whether making the already acquired
public reproduction part of submission prevents that evidence substitution.

Baseline: commit 188f7267, current-diff required checks plus model assessment;
reproduction review is advisory. Intervention: retain all mechanically replayable
original-requirement cases, replay stale ones before finish, reject a current
comparable mismatch/conflict, and explicitly label absent/incomplete cases unverified.
Use the existing public sandbox, action replay, journal and total limits. The host
does not certify the model's requirement mapping or the correctness of an oracle.
Matched baseline controls remain replayable. Plans, notes and helper successes cannot
close cases. Changed inputs/expectations create other cases, not repair evidence.

Alternative explanations remain model capability, initial wrong interpretation,
failure to acquire an original case, and verification opportunity cost. This change
cannot demonstrate autonomous acquisition by replaying an operator-provided case.

## First experiment: local execution, no provider

Use the public csv-quoted-newline smoke fixture and actual local subprocess programs
under its trusted test backend, with a scripted decision sequence. Compare the old
finish prerequisite against the new gateway and complete runner path. Include:

- Wrong candidate with passing helper/regression but original-case mismatch.
- Matching repair and ordinary-input control.
- Different input/environment/expectation that passes without resolving the old case.
- Another edit after PASS, repeated finish, child and parent crash recovery.
- Missing case, setup failure, truncated observation, and exhausted action allowance.

Preserve external append-only dev-run-v1 journals, exact programs/diffs and results.
No LLM model, credentials, provider requests, paid judges or downloaded images are
needed. A run has at most 40 scripted decisions, 100 actions and four edits; each
local probe has a 10-second timeout. Stop on unexpected execution or recovery
uncertainty; repair implementation defects before a separately labelled rerun.

Adoption criterion for the implementation: every negative control preserves its
original unresolved evidence, correct control reaches isolated mock evaluation,
and recovery/limits do not duplicate or exceed actions. This is engineering
validation, not evidence that an LLM repairs more tasks. A reduction in submissions
alone is not a repair improvement.

## Paid comparison boundary

Existing paid allocations are closed. This request has not specified the exact
new model/credential/repetitions/invocation cap required by AGENTS.md and
docs/operations.md. Prepare a concrete comparison after local validation; no live
OpenAI dispatch is authorized by this plan. Preserve the current agent checkpoint,
all denominators, independent acceptance and normal controls if a later approved
comparison uses Astroid. Do not reuse unused historical allocations.
