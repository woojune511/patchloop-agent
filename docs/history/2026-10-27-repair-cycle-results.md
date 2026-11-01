# Live repair-cycle pilot: neither row reached its first edit

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: authorized execution, public-journal accounting and result collection
- Origin Date: 2026-10-27
- Verification Status: LIVE-EXECUTED; post-edit recovery NOT_OBSERVED; acceptance NOT_RUN
- Version Label: feedback-source-pair-v2, runtime commit `4f440498`

## Question, intervention and authorization

The user asked whether the real model would consume the first failed edit's
original-call feedback, revise again, and resolve F0010. The
[implemented cycle](2026-10-27-original-repair-cycle.md) removed the preceding
one-edit cutoff and reserved further diagnosis, repair and final verification.
That control-flow change passed local tests; model uptake remained unmeasured.

The user explicitly approved the prepared R0/R1 pair once each: Astroid-1333,
`dev-train/current-dev20/13`, `gpt-5.4-mini-2026-03-17` with xhigh, repository `.env`,
$1.20 per row and $2.40 invocation-wide maximum. Each row had 16 normal responses,
one global correction, 24 model actions, two helper probe requests and three new
accepted edits; output 40K/25K, input 60K. Model work and intermediate rechecks
shared 600 seconds; final public checks and isolated evaluation had separate
390-second budgets. Zero SDK retries and stop-all on uncertainty remained active.

R0 received nine source lines; R1 received the same file's full 676 lines. Both
started from the same saved A candidate and public feedback. Prepared source/image
checks and exact anchor registration passed before approval, with no target/model
execution or credential read. The actual source packets remained present and
unchanged in every dispatched request. No operator solution or private evaluation
content entered the model. Runtime and conditions stayed frozen during execution.

Prepared plan and exact command: `C:/pt/feedback-source-cycle-plan-v1/PLAN.md` and
`run.ps1`. Approved manifest hash:
`sha256:a351ef768e4e059b85bba74237d6294ba35e9f9a0290a06b42d72294f07deed6`.
The direct user approval is preserved in `authorization.json` and the preparation
journal. This was a new allocation; earlier approvals were not reused.

## Observed result

| Outcome | R0: partial source | R1: complete source |
| --- | --- | --- |
| Terminal | AGENT_STOPPED | INPUT_LIMIT |
| Settled normal responses / dispatched corrections | 15 / 0 | 9 / 0 |
| Executed model tool actions | 19 | 21 |
| Probe requests / actual target executions | 0 / 0 | 1 / 0 |
| Accepted new edits | 0 | 0 |
| Original-call rechecks | 0 | 0 |
| Maximum dispatched input tokens | 48,418 | 57,480 |
| Maximum counted input tokens | 48,418 | 68,124 |
| Maximum output tokens | 1,715 | 10,577 |
| Settled cost | $0.16598325 | $0.162135 |
| Final public checks / isolated acceptance | NOT_RUN / NOT_RUN | NOT_RUN / NOT_RUN |

The process exited 0 and closed the allocation after both rows. Total settled
cost was **$0.32811825**, below $2.40. All 24 generation calls have settled usage;
25 input-count requests completed. No billing uncertainty or automatic retry
occurred. This does not resolve older allocations' unrelated unsettled usage.

Both candidates retained the identical seed diff
`sha256:93b024b3f11ef89311d9cbf5a06a56328b14f7b7d7687746e6d24a8b9fb8e3e5`.
There was no new target execution, original-call result or acceptance verdict.
The seed's recorded F0010 remains historical evidence; do not describe this run as
a fresh failing replay. Failure-feedback delivery, its use and subsequent revision
are all **NOT_OBSERVED_NO_EDIT**, rather than a failed test of post-edit recovery.

## Where the trajectories stopped

R0 performed ten reads and eight searches, then called `stop_task` with
`insufficient_public_evidence`. It said it needed another source inspection to
confirm module-path derivation. In four successive responses, reads intended to
locate `_get_relative_base_path` requested 220-265, 180-220, 140-180 and 200-260,
all missing its definition at line 276. An earlier 240-290 read already included
the header. The model eventually searched the name and read 274-320 in responses
13 and 14. The tool returned the requested ranges; wrong location selection and
repeated acquisition are observable, while the model's internal reason is unknown.

The last R0 request had two normal responses, six model actions, three edits and
two probe requests left in its counters. The opportunity policy had closed further
inspection/probes to leave an edit and a following response, but still offered
`replace_text`. Its output ceiling was 40K, with over $1.07 remaining. It elected
to stop. There was no cost/time narrowing, correction or context-limit event.

R1 spent its first seven responses on six reads and fourteen searches. Response
eight requested `run_probe` with **`python_source=null`**, `call_path=null` and no
replay action. Its declared purpose/conditions did not supply an executable
program. The gateway rejected it before target execution. The generic error said
the source must contain 1-8,000 characters; this was **missing code, not oversized
code**. That distinction corrects the initial progress-message interpretation.

R1 response nine then requested a search and a read together. With three tool
slots left, the offered opportunity allowed only one parallel inspection to
preserve an edit and a following response. The two-call batch was rejected before
either action ran, and a protocol correction was constructed. The preceding
dispatched input was 57,480 tokens, its output 10,577, and the correction's counted
input was **68,124 > 60,000**. The correction was never dispatched; its 25K output
allowance was not spent. Available money alone could not admit that input.

The final request grew by 148,829 serialized characters. The new opaque reasoning
continuation item accounted for 148,033 characters; rejected tool calls and their
rejection outputs added 417 and 334 respectively. Existing source/history was
preserved and there were no new file results in this step. The initial source
body remained 23,436 characters. These are size/type measurements only, not a token
attribution, decryption or interpretation of reasoning. Accumulated exploration
occupied earlier context; the immediate final growth came from the continuation.

## Decision and limitations

The run did not answer whether a model can repair after receiving its first edit's
failure. The earlier first-edit boundary was removed, but neither trajectory
reached that boundary. No successful repair or post-edit mechanism uptake can be
claimed. The next unresolved bottleneck is pre-edit behavior: locating useful
source without redundant reads, forming an executable probe, and fitting a valid
correction after a rejected action batch. Increasing context could admit this
specific correction but does not by itself repair its request or source selection.

Do not spend the unused allocation on retries. A follow-up needs a new question
and exact scope. Public action/request replay can first distinguish acquisition
and schema issues from input-retention pressure without another model charge.
The expanded horizon differs from the closed v1 pair, and the one pair is not a
feedback-only causal estimate, model ranking, general success rate or production
adoption result. The diagnostic implementation and its local checks remain valid
within their tested scope; live post-edit behavior remains unexercised.

## Evidence and verification

- Results and append-only hash-chained journals:
  `C:/pt/feedback-source-cycle-run-v1/result.json`, each row's
  `runs/run_dev_feedbacksourcemodel.jsonl`, and the comparison journal.
- Public accounting/source-delivery receipt: `public-analysis.json`; sum of row
  usage equals the invocation's 328,118,250 nanos. Request artifact hashes and
  source equality were checked; actual journal chains were loaded and validated.
- Request-size receipt: `request-growth.json`, linked to the before/after request
  artifact hashes. Analysis receipts are in `runs/run_dev_cycleanalysis.jsonl`.
- Repository code was unchanged after approval. Only this follow-up record,
  history index and current-status summary change; historical bytes and user-owned
  `AGENTS.md`/pytest artifacts are preserved. Documentation validation: **5 PASS
  in 0.23 seconds**; `git diff --check` passed. Receipt: `docs-validation.xml` in
  the result root. No full test suite or target rerun was performed for this
  documentation-only change.
