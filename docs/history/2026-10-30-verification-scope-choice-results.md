# Scope-choice guidance: one fresh SQLFluff development run

Date: 2026-10-30 KST. Allocation CLOSED. One exposed dev-train attempt,
official=false and claim-ineligible. Independent acceptance FAIL, safety PASS.

## Question and fixed scope

Following the [selection diagnosis](2026-10-30-verification-selection-diagnosis.md),
the [implementation](2026-10-30-verification-scope-choice.md) replaced existing
instructions to distinguish required behavior from repair choices and select a
material falsification or a justified narrower edit. The recurring SQLFluff failure
was selected because its previous patch changed general matching behavior while
verification stayed on the reported example. New cases or shorter patches alone
are not the success criterion; inspect public action evidence and task acceptance.

Executed commit `5f0eb78436b57b7af05e130019a9d1643ec45366`, runtime
`sha256:ed9b23780500ed4d4f72fa7751156de34314d18be3a2a05a8fcd3830dca6f4b9`.
User approved the exact prepared scope in
`["request_user_input_async","call_e83a4c868aff487c8d77c5e04da152cf",0]`:
dev-train current-dev20 task16/SQLFluff1517, gpt-5.4-2026-03-05/xhigh,
`C:/Users/geonj/Documents/PatchLoop/.env`, one fresh repeat, one worker,
USD4 row and invocation cap, 40 calls, 100 actions, 12 edits, 1,800 seconds with
330 seconds evaluation reserve. Output limit25,000 and selected policies match
the preceding run. Same pristine source/dependencies; no prior patch, plan,
operator counterexample or other-agent output entered solver context.

Preparation: `C:/pt/scope16-20261030-v1`.
Result: `C:/pt/scope16-run-20261030-v1`.
Run: `run_dev_55d4f4526e154a53`.
Existing bounded scheduler, pre-dispatch token count, zero retries and shared
uncertainty stop were preserved. The existing isolated evaluator ran once after
submission. No extra native evaluation, image pull/build or Docker Desktop startup.

## Result

| Measure | Previous task16 | This attempt |
| --- | --- | --- |
| Independent acceptance / safety | FAIL / PASS | FAIL / PASS |
| Required public check | PASS | 167 PASS / 1 deselected |
| Delivery | unverified_delivery | unverified_delivery |
| Accepted edits / model calls / actions | 1 / 13 / 25 | 1 / 10 / 21 |
| Cost | USD1.0609665 | USD0.8053575 |
| Task wall time | 566.561 s | 500.831 s |

Previous execution: `556cbbbdcdc2b0b41be20404c5d82f683e8360d4`,
`C:/pt/contractobs3916-run-20261030-v1/16`. Current cost decreased24.09% and task
time11.60% descriptively. The previous task ran in a two-worker/three-task batch;
this is one worker/one task, with uncontrolled host load. No stable efficiency or
causal improvement follows. Provider dispatch occupied373.717 seconds, 74.62%
of task time. Batch wall time including host overhead:503.513 seconds.

## What changed in public behavior

The agent chose a probe before editing: normal `select id from tbl;`, adjacent
`select id from tbl;;` and whitespace-separated `select id from tbl; ;`.
On the unchanged base, the control returned and both variants raised the observed
`Dropped elements in sequence matching` RuntimeError. After the single edit and
public PASS, it reran the same program: both variants returned SQLParseError rather
than RuntimeError. Question and observed exception/return behavior align. These
were unbound helper diagnostics, so runtime delivery remains unverified_delivery;
manual before/after observations do not manufacture a bound original-case receipt.

The submitted patch changes two returns in
`src/sqlfluff/core/parser/grammar/delimited.py` and adds a Linter regression in
`test/core/linter_test.py`. The new regression checks that both variants produce
SQLParseError and calls the normal control. The patch is +16/-2 lines versus the
previous +59/-11, but no narrowing/undo action occurred: this was the first and
only chosen edit, not an observed removal of an unnecessary assumption.

Both changed returns replace `MatchResult.from_unmatched(mutated_segments)` with
`MatchResult(matched_segments.matched_segments, mutated_segments)`. Public source
defines unmatched results with an empty matched tuple and truthiness by presence
of matched content. Therefore retaining a nonempty prefix also changes failure
into a truthy partial match. Smaller line count does not make that semantic choice
narrow. The two new returns have no trailing/minimum guard, while the probes and
regression use only default Linter configuration. No observation establishes that
the new success meaning respects those options. This is an unverified public
contract concern, not an identified hidden failing test.

Compared with the preceding run, one whitespace sibling case was added, but direct
whole-input/tree-preservation assertions disappeared; the new checks focus on
exception types. Verification breadth improved along one input dimension while
losing an observed property. Neither total probe count nor submission can summarize
that tradeoff as a repair gain.

The revised shared instructions reached the first system message at turns114,
129,144 and162, before and after the edit. Nevertheless, plan134 still chooses to
revise if the visible suite fails and submit if it passes; the new success meaning
does not become a separate assumption to test. Assessment168 explicitly mentions
only the unverified exact CLI reproduction.

Early plan replacements at seq34,51,70 and87 lacked required revision reasons;
the host preserved the prior plan and returned the annotation diagnostics. A
post-edit replacement at134 succeeded, so the final plan did not remain revision1.
These are authored annotation failures, not evidence of lost review signals or a
new execution defect. Their contribution to acceptance failure is unestablished.

## Decision and limits

This attempt partly followed the sibling-case guidance, but did not demonstrate
correct contract selection, material-assumption validation or successful repair.
Keep the small generic instruction revision without claiming quality benefit.
Do not add another warning/quota or automatically rerun this same condition.
The next useful diagnosis should distinguish whether the solver can connect the
changed truthy return to its success conditions and construct a discriminating
public case, versus choosing an unnecessarily broad repair in the first place.
One exposed attempt cannot separate stopping preference from construction ability
or establish a model capability ceiling. Exact private failure remains unknown.

No hidden tests, reference patches, evaluator contents or provider reasoning were
opened. Only public source/actions/plans/patches, accounting metadata and evaluator
verdict summaries were reviewed. Operator counterexamples were not rerun or injected.

## Evidence and closure

Manifest:
`sha256:79326e546cd7ec3110774f5083a37336d1c18427cb83031c469a21aff2aa8275`.
Approval:
`sha256:0402b56c11c9d6e7cad2b6a8cf6bcda5ddcb8545f5df89af81be3a913a57fac3`.
Result:
`sha256:e48471edc63ceda66a70505a8222499cf6c920f69db3883c8b27390ef7c63db8`.
Summary:
`sha256:e9c2607c6b5367aef509bd2946d628595909c57d249e6a264dbfcf3f44dafa5a`.
Submitted patch:
`sha256:57aadee74f816fb44c764ef444ba797078194cbac2230174c1c3036c9a7821cf`.

Independent public accounting audit:
`C:/pt/scope16-20261030-v1/analysis/accounting-audit/audit.json`.
Independent public behavior review:
`C:/pt/scope16-run-20261030-v1/analysis/contract-choice-review-v1/runs/run_dev_scope16publicreview.jsonl`;
last event `sha256:28ebed783e42c597087dfa088aa751451c9ee2c71b0bfbeaa80444cb187591e0`.
Public sequence anchors:108 unchanged-base probe,121 accepted mutation,136 visible
check,154 after-edit probe,168 final assessment. MatchResult truthiness and unmatched
construction were delivered at read91, source lines47-52 and103-105.
All10 generation/count pairs,21 action pairs and one accepted edit agree with the
hash-chained journal and settled usage. Input318,447, cached172,800, output26,536
tokens reprice exactly to USD0.8053575. Identity/bound-input checks pass. No pending
action, retry, timeout/cleanup uncertainty or unsettled cost remains. USD4 allocation
is CLOSED; unused funds do not authorize another call. Local implementation tests
are recorded separately in the implementation record; no live quality claim is made.

Result-document validation:6 PASS in0.18 seconds, diff check PASS; HTML51 unique
IDs/74 static links resolve, with scripts unchanged. Visual rendering was not rerun.
Validation report:
`sha256:b5035373c1ddca2997c83ed4fd946d07cfde007e5069f0d14a3a0d8aba981e25`.
The runtime remained unchanged while reviewing results and writing this follow-up.
