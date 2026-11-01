# SQLFluff observation follow-up: acceptance PASS, optional replay not selected

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: authorized single experiment and public-receipt verification
- Origin Date: 2026-10-29
- Verification Status: LIVE_EXECUTED; acceptance/safety PASS; causal gain unestablished
- Version Label: probe_followup_single_results_v1

## Question and prior evidence

The [previous run](2026-10-29-edit-prerequisite-single-results.md) submitted after
506 public checks passed, but independent acceptance failed. Its pre-edit helper
had observed the public indentation problem. A separate
[saved-candidate replay](2026-10-29-sqlfluff-public-candidate-replay.md) confirmed
unchanged behavior, and [branch tracing](2026-10-29-sqlfluff-branch-diagnosis.md)
found that the old edit executed but produced an equivalent intermediate result.

The [runtime change](2026-10-29-probe-followup-guidance.md) retains a bounded link
between a pre-edit helper and the current candidate, and clarifies optional replay
of an existing example. This matters because public regression success alone did
not cover that earlier observed failure. The hypothesis was that a visible link
could help the model revisit a relevant question. Alternatives included receiving
the evidence without replaying it, or replaying without repairing correctly.

This was one fresh development follow-up against a historical run, not a concurrent
A/B comparison. Both the card and general probe wording changed together. No causal
effect, independent component effect or general repair-rate estimate is available.

## Sealed scope and execution

- Task: `dev-train current-dev20/18`, `swebench-lite-dev-sqlfluff-sqlfluff-1733`.
- Model: `gpt-5.4-2026-03-05`, `xhigh`; credential file: repository `.env`.
- One fresh run, USD4.50 invocation cap; no prior patch, observations, checkpoint,
  operator diagnosis, counterexample or answer hint supplied to the solver.
- Unchanged `public-checks-v1`, thin, segmented context and completion-recovery
  policy. Request differed from the prior run only in its state root.
- Limits: 20 responses including at most one protocol correction, 40 actions,
  three accepted edits, 60K input, 40K ordinary / 25K correction output,
  2,400 seconds including 390 seconds reserved for isolated evaluation.
- Runtime commit: `59f3f074ddab38ae6a8dcabb33d42adb6d7c6f1f`.
- Runtime hash: `sha256:08b32133d33201efb3b55cd44db917ff76ffc8752676e00f5cdc366280b16b1e`.
- Approved manifest: `sha256:d7823699a8fef6f902629c4f95bf63445db80120ab792c2d1a9b88755820b22f`.
- Command: `& 'C:/pt/probe-followup-single-plan-v1/run.ps1'`.
- Run: `run_dev_c076da84daa147d4`.
- Local time: 2026-10-29 06:35:40.602 to 06:46:33.942 KST, 653.34 seconds.

Offline preparation checked the first real request-construction path with a
synthetic response, unchanged schemas apart from the intended probe description,
19 stop/accounting controls, seven existing metric controls and six observation
metric controls. Local image, dependency and source identities passed preflight.
The unchanged runtime's 923-test quick-suite receipt was reused; no repeated suite
or extra target execution was required to prepare this run. Actual input counting
occurred immediately before all 17 provider dispatches. There was no automatic
retry, image pull/build or unapproved continuation.

## Observed sequence

1. The model read and searched public source/tests. Its first helper reproduced
   nine spaces before `my_id` and an L003 repeated-fix warning on the original.
2. Its second helper compared L036-only formatting with full formatting. L036
   alone moved the first target to an unindented line; full formatting still left
   nine spaces and a remaining L003 violation. Both helpers were unbound public
   probes, not registered original-call verification.
3. In response 12, the model edited `src/sqlfluff/rules/L036.py` to reuse existing
   target indentation when moving targets onto new lines. The first public check
   returned **2 failed, 504 passed**, exposing changed behavior in top-level
   multiline SELECT cases.
4. The model received that failure, made two further searches, and in response 16
   narrowed indentation reuse to SELECT clauses whose SELECT token is itself
   indented. The host's automatic current-diff recheck returned **506 passed**.
5. In response 17, the model submitted. Its final assessment explicitly disclosed
   that the original CTE example had not been replayed on the final candidate.
6. Independent task acceptance and safety both returned **PASS**. No evaluator
   detail was fed back to the solver.

The accepted patch changes only L036. This demonstrates an accepted upstream
repair in this run; the prior downstream trace did not establish L003
normalization as the only viable repair location.

## Outcomes kept separate

| Outcome | Observed result |
| --- | --- |
| Independent task acceptance / safety | PASS / PASS |
| Public checks | First candidate 2 FAIL + 504 PASS; final candidate 506 PASS |
| Submission | Successful `finish_task` |
| Accepted source edits | 2 |
| Actual counted/dispatched requests | 17/17 matched |
| Eligible follow-up card requests | 5/5 delivered; no missing-card gap |
| Replay offered | 4 requests; unavailable in one small repair request |
| Post-edit helper/replay selection | 0 |
| Helpers on the original | 2; no registered original calls |
| Model calls / tool actions | 17 / 25; actions include one automatic host recheck |
| Protocol corrections | 0 |
| Cost / cap | USD1.18095550 / USD4.50; settled |
| Delivery diagnostic | `unverified_delivery`, original verification still unverified |

The five card-bearing responses selected check, search, search, edit and finish.
All baseline receipt identities and current diff hashes matched the delivered
requests. The card correctly continued to report candidate `not_run`.
The final completion request offered replay, but the model chose submission with
the remaining gap disclosed. Limits were not exhausted; unused funds are closed,
not permission to run again.

The successful acceptance verdict is the primary repair outcome. Missing optional
replay does not turn it into a failed benchmark attempt. Conversely, successful
acceptance does not establish that the card caused the repair or induced replay:
the latter behavior was not observed. The model used regression feedback to narrow
its first change, and this candidate passed independent acceptance. Direct
same-SQL before/after verification on this candidate remains unmeasured by helpers.

## Decision and evidence

Keep the submission policy and budgets unchanged. This run validates live delivery
and records one successful repair; it supplies no reason to add a mandatory replay
gate. Preserve optional replay and honest diagnostic labels. Whether this change
improves action selection or repair reliability across runs remains unresolved.
Any controlled follow-up needs a specific new question, comparison and approval.

Evidence is outside the repository:

- `C:/pt/probe-followup-single-plan-v1/`: design, exact request, manifest, approval,
  offline audits, preflight and hash-chained preparation/execution ledger.
- `C:/pt/probe-followup-single-run-v1/18-B/`: completed public journal and artifacts.
- `batch-collection.json`: closed allocation and settled accounting.
- `summary.json`: public checks, delivery, acceptance and safety kept separate.
- `observation-audit.json`: actual wire identities, eligibility, cards and choices.
- `result-facts.json`: asserted receipt summary, elapsed time and bound evidence hashes.

Submitted patch: `sha256:a7f85769bb06ac55aa190fb94c4d676a713674e280810abfe41d6a1effe0eb1e`.
No post-run target replay, hidden-test inspection or reference-patch access was
performed. Historical artifacts were not changed. This exposed development run
remains `official=false`, `claim_eligible=false`; repeatability and held-out
generalization remain unverified. The allocation is CLOSED and no further paid
invocation is authorized.
