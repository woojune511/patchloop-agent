# Revision opportunity preserved; unchanged candidate submitted

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run
- Origin Date: 2026-10-28
- Verification Status: live execution completed; task repair FAILED
- Version Label: probe-revision-repair-results-v1

Official=false, claim-ineligible. One authorized run completed; allocation CLOSED.
This is an assisted checkpoint continuation, not a fresh solve or a generalization
claim. No retry or additional paid run was performed.

## Question, fixed conditions and intervention

The [prepared trial](2026-10-28-probe-revision-repair-plan.md) tested whether keeping
latest helper observations and reserving an affordable revision path would let the
model repair the supplied public regressions. The prior continuation had lost a
helper output and exhausted the response window for editing.

The user approved the exact manifest and a fresh USD3.38078870 invocation cap.
We ran `C:/pt/probe-revision-repair-plan-v1/run.ps1` once with
`gpt-5.4-2026-03-05`, xhigh, repository `.env`, dev-train Astroid-1333/current-dev20/13.
The same saved candidate, cut 212, public packet and caller dependency scope were
restored. Historical spend/counters, eight remaining responses including one
correction, thirteen ordinary actions, two possible additional edits, 60K context,
40K/25K output, solver/evaluation/final-matrix deadlines were preserved.

Runtime implementation was `fed389aaf949c3f46a9f79a4750e25ee5ea16415`; the
preparation record commit was `05f5e90`. Both fixes were active together. The
single stochastic follow-up cannot isolate their individual effects.

## Observed result

| Outcome | Observation |
| --- | --- |
| New model responses | 5; all settled |
| New ordinary actions | Four source reads and one successful finish |
| New accepted edits | 0; result's total of one is inherited |
| New helper executions | 0 |
| Submitted diff | Same candidate as the starting checkpoint |
| Original caller and public regression | Unchanged-diff receipts reused, no new check |
| Final public preservation | 8 of 11 required cases passed |
| Candidate regressions | All three still failed |
| Isolated task acceptance | FAIL; terminal EVALUATOR_FAIL |
| Safety | PASS |
| New settled cost | USD0.34631750 |

The unresolved cases are `namespace_leaf_explicit`, `split_leaf_forward` and
`split_leaf_reverse`. `namespace_root_empty` still fails but predates this candidate
and remains separately nonmandatory. No private evaluator artifacts or logs were
inspected; independent acceptance failure is not attributed to these public cases.

Candidate identity:
`sha256:141dc0f8e373a23b7379661de8c08b3b0f07c6fa010f2d7bbb8b18b0ed74967f`.
The earlier original-call/processing and 1,231-test public PASS still apply only
to this unchanged diff. They do not establish success on the public counterexamples
or an independent task repair.

The four reads covered `astroid/modutils.py` lines 220-440 and 597-670, and
`astroid/interpreter/_import/spec.py` lines 96-233 and 234-369. Each successful
read's exact source body reached the next request once. All five actual inputs
retained the frozen public counterexamples and the current-diff revision binding.
Fresh input counts and dispatched requests matched for all five calls.

Maximum actual input was 28,781 tokens and output was 2,853 tokens, below the
60K/40K settings. Every response completed; no protocol correction, incomplete
response, output-limit or context-limit termination occurred. Recorded token
totals were 127,877 input (33,280 cached) and 6,767 output. Independent cost
recalculation agrees with the settled USD0.34631750.

## Mechanism evidence and interpretation

At the final prepared request, sequence 268, the model had four raw responses left:
one protected protocol correction and three ordinary responses. Nine tool actions
and two edit slots remained, with USD3.142093700 and approximately 1281 solver
seconds available. The required mutation path was three responses/four actions,
and `mutation_completion_possible` was true.

The actual offered tools were `replace_text`, `finish_task` and `stop_task`. The
current-diff revision binding was active. Optional exploration had closed while
the revision path remained affordable. This is the boundary the previous run had
crossed until editing was no longer available.

The model instead chose finish. Its public assessment explicitly acknowledged
the three supplied current-candidate counterexamples were unresolved and had not
been rerun: "Those regressions were not repaired or rechecked in this segment".
This supports a narrower conclusion than successful repair: the host
preserved an edit opportunity, but the model did not use it. The public counterexample
packet remained informational; ordinary finish eligibility still relied on the
already-passing original/public-check obligations. There was no gate requiring a
new successful counterexample result.

No helper executed, so the new helper-output retention path's live uptake is
NOT_EXERCISED. Its saved-data/local evidence remains valid but cannot be promoted
to a live repair effect. The same applies to post-edit verification and historical
packet transition: no new edit occurred. Normal finish alone does not support the
repair hypothesis.

This result weakens the claim that insufficient money or the absence of an editing
window alone explains the failure. It does not establish the model's private reason
for finishing or rule out benefit from different information or resource settings.
Do not raise the limit solely because money remained. Keep the delivery fix and
corrected reservation mechanism, without claiming repair improvement. The next
unresolved design question is how confirmed public failures should enter verification
and completion decisions, rather than remain acknowledged but nonbinding feedback.
No new implementation or experiment is authorized by that question.

## Accounting, artifacts and boundaries

Ordinary branch active time increased by 132.036 seconds; the final public matrix
took 6.7824986 seconds. Combined tool actions were 32, including 26 inherited,
five new ordinary actions and one final host execution. The unchanged program and
environment were used on the settled submitted diff. Final matrix feedback was
not returned to the model.

Billing is settled. The remaining USD3.03447120 is CLOSED, not available for an
automatic follow-up. Historical spending plus this run totals USD1.46552880 in
the fork's cumulative ledger. No provider retry, image pull/build or automatic
restart occurred.

- Approved manifest:
  `sha256:16f9df355f2e4412925b4ba48fd30094bc8096fc38326714a3e6896247cf8676`.
- Result: `C:/pt/probe-revision-repair-run-v1/result.json`,
  `sha256:eae24fe740830a1c506d77b7eb1ff8e6743f758f614daf12bb0f286b0bf0eae8`.
- Branch journal: `repair/runs/run_dev_3e21775752a54cae.jsonl` under that result root,
  `sha256:5eb4f08db4ec1bc8da0e104b10ccaea7ad50d5fb141b63187e3b91507c41ac6c`.
- Public outcome audit: `public-outcome-audit.json` under that result root,
  `sha256:caaca51b81a44910ef0be24e28cf1c0c1b56b43ed07a7acc0392ce718f7f473c`.
  The audit is linked in collector journal sequence 27, event
  `sha256:3731f9ff5801eb052517bf94a8378fa8f56c11bc69566bb16e74921272d189c1`.

The post-run read-only audit passed without additional provider, target or evaluator
execution. Documentation checks passed five tests; `git diff --check` passed.
Runtime code stayed frozen throughout collection and outcome analysis.

The source prefix, prior plans and historical run records remain unchanged. Private
evaluation details, reference patches, operator repairs and opaque reasoning were
not used for the analysis. Public delivery, public compatibility, submission,
isolated acceptance and safety remain distinct observations.
