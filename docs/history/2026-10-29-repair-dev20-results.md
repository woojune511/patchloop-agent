# Current configuration on historical dev20: 10 of 20 accepted

Date: 2026-10-29. Live allocation CLOSED; all 20 planned attempts executed once.
official=false, claim-ineligible. No runtime change or additional model run.

## Question and result

The user requested a measurement on the complete historical 20-task roster
instead of another small diagnostic selection. The frozen current configuration
accepted **10/20 (50%)**, with **9 completed acceptance failures and 1 unsubmitted
attempt**. Required public checks passed on all 19 submitted candidates; all 19
received safety PASS. These are separate outcomes, not alternative denominators.

Provider usage cost was **USD11.7967235** within the approved USD90 invocation
cap and USD4.50/task caps. All 223 provider calls reconcile with input counts and
usage records. The batch closed without an accounting or execution uncertainty,
retry, replacement attempt, or condition change between tasks.

The [preparation record](2026-10-29-repair-dev20-plan.md) remains immutable.
The earlier five-task 4/5 result and seeded/saved-candidate experiments are not
pooled into this score. This is one fresh attempt per development-exposed task;
it measures this configuration on this panel, not held-out generalization.

## Frozen execution and provenance

- User approved `& 'C:/pt/repair-dev20-plan-v2/run.ps1'` for each index 1-20 once,
  with USD90 total and no per-task cap transfer.
- Manifest: `sha256:307a67811c6954608f224fb38ffbf72e3688dc4bec6b8e3791b636377a0e0e2a`.
  Exact approval is retained in `C:/pt/repair-dev20-plan-v2/approval.json` and the
  preparation journal.
- Execution HEAD: `2b44add1ea091cedbdf8003196d3fe3a4c25d668`; runtime implementation
  unchanged since `98a0f5b6d2ef9a0792c914ad1c1309c5af9de66e`.
  Runtime hash: `sha256:08b32133d33201efb3b55cd44db917ff76ffc8752676e00f5cdc366280b16b1e`.
- gpt-5.4-2026-03-05, xhigh; primary repository `.env`; sequential fresh original
  source, no previous patch, checkpoint, operator diagnosis or private feedback.
- public-checks-v1, thin, segmented-v1, completion-recovery-v1, protected-v1,
  repair-recheck, ordinary optional probes; no automatic replay.
- Per task: 20 responses including at most one correction, 40 actions, 3 accepted
  edits; input60K, output40K/correction25K; 2,400 active seconds including 390
  reserved for isolated evaluation. Zero SDK retries and stop-all uncertainty
  rules remained active.

The registered `original-oracle` applies the original SWE-bench test patch and
upstream grading in the isolated evaluation workspace. All 19 evaluations were
complete with zero missing expected cases, no infrastructure failure, and
confirmed cleanup. Their resolved flags agree with the reported 10 PASS/9 FAIL.
No duplicate native grading was run. Private receipt contents stayed outside
solver feedback.

## Per-task outcomes

Previous means the latest complete
[PatchLoop mini panel](2026-10-16-patchloop-mini-dev20-results.md), not a later
supplement or the best historical result. Calls are model responses/tool actions;
edits are accepted mutations. All evaluated rows had current-diff public PASS.

| # | Task | Previous | Current acceptance | Calls | Edits | USD |
|---|---|---|---|---:|---:|---:|
| 1 | marshmallow-1343 | PASS | PASS | 11/19 | 2 | 0.5504700 |
| 2 | pvlib-1072 | PASS | PASS | 8/8 | 2 | 0.3403205 |
| 3 | pvlib-1154 | PASS | PASS | 9/16 | 1 | 0.4200290 |
| 4 | pvlib-1606 | PASS | PASS | 9/14 | 2 | 0.5254200 |
| 5 | pvlib-1707 | FAIL | FAIL | 8/8 | 1 | 0.4142345 |
| 6 | pvlib-1854 | PASS | PASS | 5/7 | 1 | 0.2384140 |
| 7 | pydicom-1139 | FAIL | FAIL | 8/14 | 1 | 0.2837345 |
| 8 | pydicom-1413 | FAIL | FAIL | 11/25 | 1 | 0.7541715 |
| 9 | pydicom-1694 | PASS | NOT_RUN | 13/21 | 3 | 0.7256500 |
| 10 | pydicom-901 | FAIL | FAIL | 15/15 | 1 | 0.4772140 |
| 11 | astroid-1196 | FAIL | PASS | 14/23 | 2 | 0.7586770 |
| 12 | astroid-1268 | FAIL | FAIL | 9/19 | 2 | 0.3810035 |
| 13 | astroid-1333 | FAIL | FAIL | 16/33 | 1 | 0.8357505 |
| 14 | astroid-1866 | FAIL | PASS | 7/7 | 1 | 0.2002940 |
| 15 | pyvista-4315 | PASS | PASS | 10/13 | 2 | 0.5544405 |
| 16 | SQLFluff-1517 | FAIL | FAIL | 15/25 | 2 | 0.9944225 |
| 17 | SQLFluff-1625 | NOT_RUN | FAIL | 15/28 | 2 | 0.8755990 |
| 18 | SQLFluff-1733 | NOT_RUN | PASS | 17/35 | 2 | 1.2536585 |
| 19 | SQLFluff-1763 | FAIL | FAIL | 15/37 | 1 | 0.9071245 |
| 20 | SQLFluff-2419 | PASS | PASS | 8/16 | 1 | 0.3060955 |

Index 9 ended `LIMIT_REACHED`, with the terminal message
`completion horizon exhausted before provider dispatch`. Three accepted edits
had been used and the latest required public regression still failed. It did not
submit and never entered acceptance evaluation. Its USD0.72565 spend was below
the USD4.50 cap; NOT_RUN is not a completed hidden-test failure. This records an
unresolved public failure under the edit/completion limits, without establishing
whether a fourth edit would have repaired it.

For index 18, the public milestones show FAIL on the earlier candidate and PASS
on the final candidate after the second accepted edit, followed by acceptance
PASS. This is a useful within-run repair sequence; it does not isolate the effect
of a particular guidance card. The other failed candidates have not received new
source-level diagnosis or repair in this measurement.

## Accounting, time and evidence audit

| Measure | Recorded result |
|---|---|
| Planned / attempted / submitted / evaluated | 20 / 20 / 19 / 19 |
| Acceptance PASS / FAIL / ERROR / NOT_RUN | 10 / 9 / 0 / 1 |
| Latest required public checks | 19 PASS / 1 FAIL |
| Safety | 19 PASS / 1 NOT_RUN |
| Model calls / input-count calls / tool actions | 223 / 223 / 383 |
| Accepted mutations / executed probes / protocol corrections | 31 / 13 / 1 |
| Input tokens, including cached | 5,100,797 |
| Cached input tokens | 2,421,504 |
| Output tokens, including reasoning | 299,541 |
| Reasoning output tokens | 260,734 |
| Maximum counted request / observed response | 50,628 / 10,516 tokens |
| Provider usage cost | USD11.7967235 |
| Sum of per-task active elapsed time | 6,117.366 seconds (1h41m57s) |
| Batch wall time | 7,158.385690 seconds (1h59m18s) |

Batch wall time runs from approved dispatch at 2026-10-29 04:10:37.907453 UTC
to closure at 06:09:56.293143 UTC. It includes between-task identity/preflight
work; it is not model reasoning time. The per-task active total is a different
measurement. Cost is derived from provider-reported usage and reconciled with
the host ledger, not a separate invoice reconciliation.

The read-only post-run audit rechecked the frozen manifest, runtime, task sources,
local images and dependencies, all 20 journal chains and settlement receipts,
and 108 referenced content-addressed artifacts. It verified patch identity in
each isolated evaluation and original-oracle completeness. Four captured private
log streams retain a bounded suffix with omitted-prefix byte counts; their
complete test-result reports remain available. Retained stream lengths and
hashes were checked, with full-stream hashes recomputed only where no prefix
was omitted. No audit made a provider call or executed a target again.

All 19 submitted collections retain `unverified_delivery`: their formal bound
original-call obligations were not discharged. That diagnostic label neither
changes the SWE-bench 10/20 score nor proves the absence of useful unbound public
observations. No benchmark pass is relabelled a failure for missing diagnostics.

## Historical comparison and decision

| Fresh full-roster panel | Model | PASS / FAIL / NOT_RUN | Recorded USD |
|---|---|---|---:|
| Previous PatchLoop | gpt-5.4-mini-2026-03-17, xhigh | 8 / 10 / 2 | 7.01172285 |
| Previous mini-SWE-agent | gpt-5.4-mini-2026-03-17, xhigh | 10 / 5 / 5 | 3.2146974 |
| Current PatchLoop | gpt-5.4-2026-03-05, xhigh | 10 / 9 / 1 | 11.7967235 |

Against the latest PatchLoop panel, seven previous passes remain passes;
astroid-1196 and astroid-1866 change FAIL to PASS; SQLFluff-1733 changes NOT_RUN
to PASS. Pydicom-1694 changes PASS to NOT_RUN, while SQLFluff-1625 changes NOT_RUN
to a completed FAIL. Eight previous failures remain failures. Net acceptance is
8/20 to 10/20, or +10 percentage points, with an explicit lost pass.

Public issue text, task IDs, repository bases and evaluation images match the
historical roster. Model, tool/prompt/runtime policies, response/edit/time limits,
concurrency and cost caps differ: the previous PatchLoop panel used USD0.88/task,
40 responses/100 actions/4 edits, output25K and two workers; the current run used
USD4.50/task, 20/40/3, output40K and one worker. The previous mini-SWE-agent panel
used a different tool interface and USD1.19987985/task. These are descriptive
comparisons, not a matched-budget agent ranking or a causal architecture gain.
The original [mini-SWE-agent report](2026-10-16-mini-swe-dev20-results.md) and its
later completion runs retain their separate denominators.

Keep the measured runtime and budgets unchanged. The next useful investigation
is the gap between public-check success and acceptance failure, separated from
index 9's public-failure/completion-limit case. Nine failures already reached
normal submission and complete evaluation, and none exhausted its dollar cap;
this does not support a blanket cost/context increase or another submission
gate. A failure classification can use retained operator logs for measurement,
but any future solver intervention needs public-source/check evidence and must
not expose private test expectations. No such diagnosis, new rule, or additional
live experiment has been executed here. Repeated-run reliability and held-out
performance remain unresolved.

## Validation and evidence locations

This change adds a result record and updates current status; it does not modify
runtime behavior. Reuse the unchanged runtime's recorded 33 focused and 923
quick PASS results, including isolated mock smoke. Preparation had 19 batch
safety, 4 summary and 3 comparison checks PASS, plus five documentation tests.
The read-only post-run auditor passed Ruff. The result documentation receives
the five documentation tests and `git diff --check`, recorded in the closeout
receipt; these are not new runtime or model-quality tests.

- [Manifest](C:/pt/repair-dev20-plan-v2/manifest.json) and
  [approval](C:/pt/repair-dev20-plan-v2/approval.json).
- [Closed batch](C:/pt/repair-dev20-run-v2/batch-collection.json).
- [Per-task summary](C:/pt/repair-dev20-plan-v2/results-summary.json) binds run IDs,
  collection/journal hashes, submitted patches and public milestones.
- [Historical outcome comparison](C:/pt/repair-dev20-plan-v2/historical-outcome-comparison.json).
- [Accounting and integrity audit](C:/pt/repair-dev20-plan-v2/postrun-audit.json).
- [Operator-only oracle audit](C:/pt/repair-dev20-plan-v2/operator-evaluation-audit.json)
  retains receipt identities, completeness and stream metadata without solver
  reinjection.
- Per-task states: `C:/pt/repair-dev20-run-v2/<index>/`.
  Master hash-chained journal:
  `C:/pt/repair-dev20-plan-v2/runs/run_dev_repairdev20preparation.jsonl`.

The USD90 allocation is closed. Unused funds authorize no continuation or rerun.
