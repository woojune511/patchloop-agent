# Ordinary probe action replay: no verification use in the selected pair

Date: 2026-10-07. CLOSED; official=false, claim_eligible=false.
Execution commit: `eba08ff913de7c883300dda200f3ee13e75a00cd`.
Preparation: `C:/pt/parpairprep02`; execution: `C:/pt/parpairlive01`;
assessment and closeout: `C:/pt/parpairassessment01`.

## Question and decision

The [readiness audit](2026-10-07-probe-action-readiness.md) found a usable public
reproducer ID in the actual pre-submission context of the failed SQLFluff B2
continuation. Ordinary action replay removed the need to have saved or rewritten
that program. The question was whether this reduced effort would lead the agent
to verify the current patch, reject the wrong repair and correct it.

It did not change the observed decision in this pair. A and B both immediately
submitted the inherited patch, using the existing regression PASS as their reason
to finish. Neither performed a public verification or edit. Both isolated task
evaluations failed. The replay mechanism is NOT_EXERCISED and incremental repair
benefit is NOT_ESTABLISHED. The criterion for expanding to fresh tasks was not met.

Close the allocation and retain the selected 24k baseline. No further paid
comparison, prompt change or compulsory probe gate follows from this result.

## Executed controls

The user approved A/B once each, USD 1.20 per row and USD 2.40 total with
"진행해줘" after reviewing the concrete plan. The approved manifest hash was
`sha256:24dc6c3e891373fb8e2e64ac01a330ee1acb6410915dbff99c3368a26dff8c7d`.

- Task: `tasks/dev-train/current-dev20/18/public.yaml`, SQLFluff 1733, dev-train.
- Source: `C:/pt/sretcl01/2`, run `run_dev_984d4340fa4e43d3`, before prepared
  boundary 526. Future source decisions and evaluation were excluded.
- Model: gpt-5.4-mini-2026-03-17, xhigh, 25,000 desired output tokens;
  repository `.env`, inherited segmented-v1/brief-v1 and 48k source retention.
- A: ordinary inline probes. B: ordinary probes plus action-ID replay.
  Preserve all observations, notes, plans, candidate code and encrypted continuation.
- Inherited allowance: five model calls, 50 actions, three edits, 162 solver seconds
  and 330 evaluation seconds. Actual first inputs showed 160 seconds for A and 161
  for B after preparation overhead. Both received the same fresh USD 1.20 allowance.
- Execute A then B, with new input counts immediately before dispatch, zero SDK
  retries, no automatic continuation, and group stop on execution/billing uncertainty.

The two actual first requests matched their approved hashes. After normalizing
elapsed-time fields, changing only B's run_probe schema into A's reproduces A's
request exactly. Both explicitly offered run_probe and finish_task. Source,
dependency and existing-image preflight passed for both rows.

## Results

| Arm | New model calls | New probes / edits / public checks | Submission | Acceptance / safety | New USD |
| --- | ---: | --- | --- | --- | ---: |
| A, inline probes | 1 | 0 / 0 / 0 | Unchanged patch | FAIL / PASS | 0.02574825 |
| B, action replay available | 1 | 0 / 0 / 0 | Unchanged patch | FAIL / PASS | 0.02352495 |

Both submissions retained candidate hash
`sha256:339ced45df8758edfb39c66f63731a9b70537642ab8e7ef219e4efb1ee00cce8`.
The cumulative accepted mutation count remained one; there were zero new edits.
The prior regression PASS was inherited on that exact diff, not rerun here.

Two input counts and two provider calls settled without uncertainty. Total new
cost was USD 0.04927320; USD 2.35072680 is closed, not transferred. Group journal
wall time was 153.745434 seconds, including setup and isolated evaluation.
No resource-limit terminal or evaluator infrastructure error occurred. No Docker
containers remained at read-only closeout inspection.

## Decision trace and interpretation

Both first inputs retained unresolved concern v1: verify the current WITH repair's
eight-space indentation while preserving plain SELECT. Both retained the eligible
public probe `call_YcnJuf5oV8ffOwrmGNBweCbB` in the observation catalog. B offered
the replay selector and its instruction. Availability and identifier loss do not
explain its non-use at this selected boundary.

The new action at sequence 541 was finish_task in each branch. A's public basis
said the current-diff regression passed and further public uncertainty would not
change submission. B's basis likewise cited regression PASS and said another
public experiment was unnecessary. Neither resolved v1 with new execution evidence.
Four model calls remained after each finish decision; neither exhausted cost or time.

Thus this pair shows the same premature completion decision despite accessible
verification. It does not establish that replay is generally ineffective. Only
one exposed checkpoint was sampled once per arm; model variability, execution
order, completion advice and model capability remain unseparated. In particular,
the shared finish suggestion was not independently manipulated, so no causal
claim about that guidance follows.

The unresolved issue is how the agent decides whether the changed public behavior
has actually been verified. More interface capability alone did not alter that
decision here. Another experiment requires new evidence, not the unused cap.

## Evidence boundaries

The prepared manifest, live group/branch journals, actual request artifacts,
submitted diffs and isolated results remain unchanged. `summary.json` and the
hash-chained assessment journal bind their identities, costs and trace findings.
The source journal, envelope, public task and parent fork metadata were rehashed
and confirmed unchanged. No evaluator details or later operator diagnosis entered
either model request. The original failed preparation remains at `C:/pt/parpairprep01`.

New operator public probes, independent native evaluation, fresh task solves and
the 20-task rerun were NOT_RUN. The registered isolated acceptance/safety results
above are the new evaluation evidence. No repair-success or generalization claim
is supported by this pair.
