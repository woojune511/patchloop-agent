# Current-candidate counterexample: closed results

Date: 2026-10-07. Two live seeded repair episodes on one exposed SQLFluff-1733
candidate, official=false and claim-ineligible. Neither repaired the candidate.
The [preparation](2026-10-07-counterexample-prep.md),
[design](../../.agent/current-counterexample.md) and
[earlier replay result](2026-10-07-probe-action-results.md) remain unchanged.

## Question and execution

Can supplying the actual failure of the original public reproduction lead the
model to revise the same wrong candidate with an equal fresh repair allowance?
A receives the program with execution output withheld; B receives the same program
and its current-candidate output. Both receive the same saved B2 patch, mini xhigh,
40 calls, 100 actions, three new edits and 1,800 seconds including 330 for evaluation.
This is a supplied-program diagnostic, not unassisted discovery or a fresh solve.

The user approved A then B once each, gpt-5.4-mini-2026-03-17, repository `.env`,
USD 1.20 per arm and USD 2.40 total. No row, count or provider dispatch occurred
in the initial failed admission described below. Its corrected preparation retained
identical normalized first model requests and unchanged task/model/credential,
repeat, tool, time and cost settings. The first authorized model episodes then ran
once each. No model retry, response correction, resume or replacement row occurred.

Execution commit: `d8fb98fdd336f60642f270f09b77fcb76529f5d7` in the managed
`counterexample-delivery` worktree. Final manifest: `C:/pt/cceprep03/manifest.json`,
`sha256:9eee15341b7dd6b51eeb29e514a5b07e02cd7bb84754f0e61ee95e077b2a475c`.
Live root: `C:/pt/ccelive02`. Assessment: `C:/pt/cceassessment01/summary.json`,
hash-bound in `runs/run_dev_currentcounterexampleassessment.jsonl`.

## Outcomes

| Outcome | A: output withheld | B: current failure delivered |
| --- | ---: | ---: |
| Model calls / input counts | 2 / 2 | 2 / 2 |
| Agent reads / probes / new edits | 0 / 0 / 0 | 0 / 0 / 0 |
| Actions | base-regression, finish | base-regression, finish |
| Registered public regression | 506 PASS | 506 PASS |
| Frozen public reproduction after submission | FAIL | FAIL |
| Isolated task acceptance | FAIL | FAIL |
| Sandbox safety | PASS | PASS |
| Settled USD | 0.02749725 | 0.01270185 |

Both submitted the unchanged candidate
`sha256:339ced45df8758edfb39c66f63731a9b70537642ab8e7ef219e4efb1ee00cce8`.
Both external audits reproduced the WITH assertion failure with setup passing,
no timeout/truncation and confirmed cleanup. The plain SELECT assertion was
NOT_REACHED after the first failure; printed output does not grant it PASS.
The audits happened outside the solver, without feedback or continuation.

Four counts and four provider calls settled with known usage. Token arithmetic
reconciles USD 0.04019910 total; unused USD 2.35980090 is closed. Group wall time
including setup, isolated evaluation and external public audits was 249.7026 seconds.
There was no model-resource exhaustion, billing uncertainty or evaluator error.

## Public decision evidence

A: `run_dev_9336c3ece6de4afa`; B: `run_dev_1ff9e31309d748a9`.
Both journals have prepared inputs at sequences 9 and 22, public decisions at
15 and 29, and tool actions at 18 and 32. Actual submitted artifacts and terminal
results are recorded later in each journal. No private reasoning text was inspected.

A's first decision already treated base-regression as confirmation of the WITH
and ordinary SELECT behavior. After PASS it explicitly claimed the WITH fix was
confirmed and submitted. The reproduction code was present, but output was
withheld in both inputs. Thus A failed to choose the supplied verification; it
must not be described as ignoring an already-delivered failing output.

B's two actual inputs contained the complete original program and exact calibration
stdout/stderr/exit/setup result. The feedback was labelled current_candidate and
bound to the unchanged current diff; no output was dropped or truncated. Prepared,
counted and dispatched request identities matched. Nevertheless, B's first plan
was to submit if the regression passed. Its final public basis called submission
the only remaining action for a verified candidate. Neither public decision cited
or refuted the delivered counterexample, and no investigation or repair followed.

At the final decision, A still had 39 calls, 99 actions, three edits, 1,408 solver
seconds and USD 1.18616325. B had the same call/action/edit allowance, 1,424 seconds
and USD 1.19498685. Reads, searches, selected tests and probes were available.
The mutation tool required first reading current source, which was possible;
there was no mutation attempt or rejection. Resource or tool blocking does not
explain either observed early submission.

Delivery is not proof of attention or comprehension. In both B inputs, the external
failure was in `operator_public_feedback`; the native verification catalog remained
empty and `current_public_failure` remained null. That field tracks failed registered
checks under the existing contract, so this is not a newly discovered projection bug.
After the check, completion guidance recommended finish while distinguishing
eligibility from correctness and explicitly allowing a useful probe. The phrase
"only remaining action" was model-authored, not a restriction imposed by the runtime.
Feedback integration, guidance effects and model interpretation are still unseparated.

## Decision and relevant prior evidence

Current failure delivery alone did not elicit repair in this pair. A verification
selection problem exists, but selecting a verification example is not a sufficient
explanation for B: it already received the result. No evidence supports raising
the budget or retained context for these early submissions. Neither episode tried
to repair, so this does not prove the model could not implement a correct repair.

The same broader behavior occurred in the earlier full-model
[HF observation panel](2026-09-29-observation-repair-panel-results.md): one B episode
used the counterexample and changed its patch, another submitted unchanged, and all
four failed full acceptance. The later
[recommendation-removal diagnostic](2026-09-29-completion-recommendation-ablation-results.md)
tied at 1/3 versus 1/3 on its response-only primary outcome. Those are different tasks
and conditions, not pooled accuracy data, but they argue against repeating an
adjacent wording experiment or attributing this exclusively to the mini model.

Close this comparison and preserve the baseline. Do not add a universal probe gate,
reinterpret arbitrary assertions as trusted task failures, remove completion advice,
or start another paid panel on the strength of this result. The earlier
[mini/full comparison](2026-10-04-mini-full-results.md) did not include SQLFluff-1733.
A full-model repair of this exact B candidate would answer a still-open case-level
feasibility question, if separately chosen; it is not queued or authorized here,
and one successful episode would not establish model superiority or a default change.

## Admission correction and validation

Initial collection at `C:/pt/ccelive01` stopped before its first row: the coordinator
created its result folder, then called a controls helper that required that same
folder not to exist. Its immutable result remains rows=[], known cost USD 0 and
PREFLIGHT_FAILED. This was an implementation bug in the new diagnostic, not a task
failure or an uncertain provider response. It explains why preparation passed but
collection initially could not start.

`d8fb98fd` separates permanent non-overlap checks from fresh-entry checks. Repeated
environment validation permits the collector-owned folder; prepare/collect still
reject reusing an existing result root. The regression keeps real controls,
validation, collection and environment transitions. It fails with the old helper,
passes A/B admission with the fix, rejects a second collection without changing
journal bytes, and covers protected-path overlap and preparation before preview.

Six new lifecycle tests passed; fixed-worktree coordinator, 20 clean-checkout task
packages and documentation tests passed 55/55 in 33.62 seconds
(`C:/pt/cce-isolated03.xml`). Ruff and diff checks passed. Earlier focused mock arms
reached isolated EVALUATOR_PASS with mock safety NOT_RUN. The task-byte checkout
fix and its independent evidence are retained in the preparation record.

Source journal, envelope, public task and calibration hashes were rechecked unchanged.
Group and branch journal chains, four delivered inputs, submitted hashes, both public
audit artifacts and token costs were validated in the external assessment. Existing
failed preparation and replay records were not rewritten. No private evaluator
details or operator root-cause hints entered model context.
Closure documentation tests passed 5/5 in 0.14 seconds
(`C:/pt/cce-results-docs01.xml`); no Docker containers remained at closeout inspection.

The full repository suite, native benchmark rerun, fresh solves, twenty-task panel,
new model comparison and publication remain NOT_RUN. No repair benefit or general
accuracy improvement is established.
