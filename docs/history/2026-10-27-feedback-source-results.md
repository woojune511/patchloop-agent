# Full current-file delivery did not repair the saved failure in this pair

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run and validate
- Origin Date: 2026-10-27
- Verification Status: IMPLEMENTED, LOCALLY TESTED, LIVE EXECUTED; no quality gain established
- Version Label: feedback-source-results-v1

## Question, intervention and result

The [design](2026-10-27-feedback-source-plan.md) asked whether complete current
source helps the next repair when a saved failed candidate, public failure feedback
and further opportunities are identical. This matters because the earlier search
excerpt omitted the incremental construction just above the edited lines. The
[implementation](2026-10-27-feedback-source-implementation.md) also makes selected
small files readable in one call, with explicit consecutive pages for larger files.
The live comparison kept the old range-only tool interface in both rows; it tests
host source preloading, not uptake of that new API.

Both assigned model runs completed once. R0 retracted the whole seed patch and
returned to the failing base. R1 added a namespace-discovery fallback but retained
F0010 and failed separate isolated acceptance. Both public regression runs passed.
Complete source delivery alone did not produce a correct repair in this pair.
This is a narrow negative result, not evidence that full-file reads are useless.

| Outcome | R0: current lines 265-273 | R1: current lines 1-676 |
| --- | --- | --- |
| Final change relative to clean base | Empty diff after reverting seed | Namespace fallback in check_modpath_has_init |
| Normal / correction responses | 7 / 0 | 8 / 0 |
| Model actions, excluding host reads | 10: 3 reads, 6 searches, 1 edit | 8: 2 reads, 4 searches, 1 probe, 1 edit |
| Host preload reads | 1 | 2 |
| Additional accepted edits | 1 | 1 |
| Original call-1 F0010 resolved | No | No |
| Namespace empty/import/invalid-child fixtures | All fail; child not selected or parsed | All fail; child not selected or parsed |
| Direct-file / ordinary-package controls | PASS / PASS | PASS / PASS |
| Public regression | 1,231 PASS, 69 skipped, 15 xfailed | 1,231 PASS, 69 skipped, 15 xfailed |
| Isolated acceptance | NOT_RUN, no candidate diff | FAIL, one completed evaluation |
| Isolated regression / scope / safety | NOT_RUN | PASS / PASS / PASS |
| First / maximum input tokens | 25,177 / 34,604 | 31,570 / 43,045 |
| Maximum response output tokens | 3,644 | 18,527 |
| Model stage elapsed | 71.997 seconds | 191.177 seconds |
| Settled cost | $0.10363125 | $0.23100870 |

Total settled cost is **$0.33463995** against the unchanged $2.40 cap. The
allocation is closed. There was no failed-run replacement, extra model repetition
or evaluator retry. All results are official=false and claim-ineligible.

## What the observed actions establish

R0 obtained the enclosing function and recognized that the seed's value-based
`modpath.index(part)` slicing was unsound. Its last declared hypothesis correctly
identified that the accumulated prefix was already available, but its only new
edit simply restored that original code. The host then ended the one-edit row.
Retracting a bad patch is useful progress but does not repair the original task.

R1 received the complete file in every actual request. Its first model read
re-read lines 258-276, already present in the preload. It searched for namespace
handling and for `expand_modules` in the Astroid workspace; the two caller
searches returned no spans. Its only helper constructed a public directory fixture
and ran Pylint, successfully observing F0010 again. Setup, execution and cleanup
succeeded. It did not compare competing causes or request call-path observation;
`call_path` was null and it received helper/unbound diagnostic credit only.

R1 then changed `check_modpath_has_init` to retain a base path and accept either
`util.is_namespace` or a `spec.find_spec(...).type == PY_NAMESPACE` result. No
new-candidate model probe occurred: the accepted edit ends this diagnostic row.
Host replay subsequently preserved the failure. In its launch-thread line
observation across the two original calls, added line 264 (`base_path = path`)
was observed, but the new fallback lines 269-272 and 274-275 were not. Line 273
had no line event. This is bounded, aggregated line-entry evidence, not proof of
which call entered the function, full branch coverage or behavior in other threads.
It does not support claiming that the new fallback affected the failing call.

The original calls met the recorded identity comparisons in both rows; control
output was unchanged and no unexpected exception was reported. The five public
fixtures likewise retained their conditions. The namespace fixtures still emitted
F0010 instead of selecting and parsing the actual child. Public regression PASS
therefore cannot be promoted to repair success.

## Delivery, resource and stopping audit

All 7 R0 and 8 R1 dispatched requests retained their assigned source packet and
identical common public feedback. Initial request bytes and hashes matched the
sealed preparation. Only `current_source` differs between the initial structures.
Both host preload ranges for R1 returned the expected current file hash without
truncation. The model did not receive private evaluation material or operator
repair advice, and no acceptance result was fed back into either model conversation.

Input stayed below 60K, every ordinary output ceiling stayed at 40K, and actual
output, cost and 600-second model deadlines were not exhausted. This does not mean
opportunities were unrestricted. R0's seventh response had two normal responses
and three model actions left, but the reservation policy had removed reads/searches;
probe remained available and was not used. R1 used its probe on response seven;
response eight offered only edit/stop despite five model actions remaining.
The first accepted edit stopped both rows. The results therefore leave the effect
of a longer diagnosis/revision horizon unresolved.

Every input count and provider dispatch has a matching settled completion.
Token-rate recalculation agrees with every usage receipt and the invocation total.
Both public verification sequences completed: six candidate probes, six clean-base
probes and one regression check per row, with confirmed cleanup. R1's additional
model helper also completed. Public receipt hashes/sizes were checked independently.
Only the safe summary of the isolated evaluation was inspected.

## Empty-diff incident and exact remaining-arm execution

The original collector's evaluator precheck rejected R0's empty diff and interrupted
the pair before R1. The original safe summary remains PRECHECK_FAILED with zero
evaluator dispatches; it is not rewritten as an acceptance FAIL. The separate
[incident record](2026-10-27-feedback-source-empty-diff.md) documents the correction:
known empty candidates now return NOT_RUN_NO_DIFF without private dispatch.

R1 ran once from a new, fixed, single-use remaining-arm directory. Its original
request, source bundle, scope, model/runtime identity and credential path remained
unchanged. Only post-model no-diff handling changed in the existing bound operator.
The new invocation ledger restored all seven settled R0 usage records before R1.
The interrupted original directory was not resumed or altered. Final result data
preserves R0's original PRECHECK_FAILED alongside NO_CANDIDATE_DIFF interpretation.

Implementation commit: `95d9a0ce`. Empty-diff/remaining-arm commit: `715a0b51`.
Core read/schema checks and the quick suite passed: 472 tests in 104.09 seconds,
including isolated mock evaluation. After the diagnostic correction, 25 focused
tests passed in 4.85 seconds and Ruff passed. A separate broader selection had
21 unresolved failures; baseline status was not established. These local results
do not claim a full-suite pass or general repair improvement.

## Decision and next unresolved question

Keep the small-file read simplification as an implemented acquisition convenience;
there is no live quality evidence for adopting mandatory whole-file reads, raising
context, or changing the production defaults from this pair. Full current source
was present within budget, yet the observed diagnosis still centered on the old
edited function and did not test whether the proposed branch explained the failure.

The next useful distinction is between inadequate diagnosis and the diagnostic's
own first-edit stopping rule. In particular, R0's legitimate retraction consumed
the entire mutation horizon. A subsequent design should consider using the existing
production repair/recheck cycle with a bounded opportunity to continue after a
retraction, and compare this under fixed evidence/model resources. Do not infer
that another mandatory declaration, prompt, larger context or automatic repetition
is needed. No such follow-up is implemented or funded by this completed pair.

This is an assisted continuation from one saved, development-exposed state with
one sample per condition. It does not isolate the effect of feedback, measure a
fresh solve, establish held-out generalization or compare unrestricted shell
agents. Source information, acquisition burden and available edit anchors changed
together; the interruption handling and opportunity limits are explicit caveats.

## Evidence locations

- Original plan/command: `C:/pt/feedback-source-plan-v1/{manifest.json,run.ps1}`;
  manifest `sha256:844256532293cfdeaf8ecdc3f1a3924dd8eb1bdcf9381d1df967fbc7e58b228e`.
- Original R0: `C:/pt/feedback-source-live-v1/R0`; model journal
  `sha256:8f2700cd3ebd9cd2bc9b8378dfc4e24d4bf4e1fd559489628506be75f98ba873`;
  public journal `sha256:45ab6d3e69bfbb831f0dc3a13cafb0441e9a1a6c1fb43bb8f1b1e76a1968e1f3`.
- Remaining plan/command: `C:/pt/feedback-source-remaining-plan-v1/{remaining.json,run.ps1}`;
  remaining manifest `sha256:1877bfd18efeae8c4919b7886aa4df4ac2c69166fa7bcd1d0b5fa4b9fa8e243a`;
  underlying manifest `sha256:eaf2985e20497aaa5f44ace7ffd2470a14a1e34ee05dcd06a14567e8070a37ba`.
- R1 and combined result: `C:/pt/feedback-source-remaining-live-v1/{R1,result.json}`;
  R1 model journal `sha256:8f059219687d7cefb0b650a65cdfa9e5275778e8a5ef4825f00d5bd17f583d8f`;
  public journal `sha256:6fe7b8380ff5e644ee94138ce80c181913ba4cf6add3e5df7c30b891c25318a0`.
- Public-only usage/request audit: `C:/pt/feedback-source-audit-v1/runs/run_dev_feedbacksourceaudit.jsonl`.
- Seed diff `sha256:93b024b3f11ef89311d9cbf5a06a56328b14f7b7d7687746e6d24a8b9fb8e3e5`;
  R0 final `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`;
  R1 final `sha256:3ce9de6d3a2a5bd31c343e2a1763123bea14d738ca0998453a77d4df83128929`.
