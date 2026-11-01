# Causal-link task8: helper repair still replaces original-path diagnosis

Date: 2026-11-01. CLOSED. Fresh live execution and public audit; official=false,
claim-ineligible. No retry, resume or additional evaluation.

## Question, selection and frozen conditions

The [guidance change](2026-11-01-causal-link-repair-guidance.md) asked the existing
hypothesis to connect public input/caller, cause precondition and wrong result,
inspect an unexplained producing step, and derive a discriminating case while
preserving representation and caller. The question was whether that concrete
contrast changes repair selection after the [latest task8 failure](2026-11-01-completion-reserve-task8-results.md).
That failure mattered because a helper repair passed tests without explaining the
reported bytes input; a separate [public reconstruction](2026-11-01-task8-bytes-call-path.md)
found a residual original-path defect. No reconstruction hint entered this solve.

- Execution commit: `9b2e2a7388d87d3a969c03be3d0ea96ff954c6f1`.
- Runtime: `sha256:22642fb00502a44dafb64072fe5ce97bc2061f3594a033a2a361873572b4f976`.
- Fresh dev-train current-dev20 task8, pydicom1413; one worker, one attempt.
- Model: gpt-5.4-2026-03-05/xhigh, output cap 25,000;
  credential file `C:/Users/geonj/Documents/PatchLoop/.env`.
- New invocation cap USD4; 40 model calls, 100 actions, 12 edits, 1,800 seconds
  including the 330-second evaluation reserve. Same policies and prepared
  source/dependencies as the baseline; request differs only in fresh state_root.
- Public source only; no prior patch, helper, notes, diagnostic output or private
  expectations supplied. Count/transport/billing/recovery uncertainty stops new work;
  zero SDK retries, no extra evaluation or budget increase.

Preflight, exact authorization, request and runtime hashes are bound in
`C:/pt/causal-task8-20261101-v1`. Live state is under
`C:/pt/causal-task8-run-20261101-v1/8`.

## Result

| Measure | Previous task8 | New causal-link run |
| --- | --- | --- |
| Independent acceptance | FAIL | **FAIL** |
| Safety | PASS | PASS |
| Public check summary | 213 PASS | 213 PASS |
| Model calls / actions / edits | 16 / 23 / 2 | 11 / 16 / 1 |
| Recorded generation cost | USD1.797247 | **USD0.8620045** |
| Task wall time | 786.524s | **393.872s** |

New run: `run_dev_5dc6e479ff2649eb`; batch wall 395.896s. Submitted patch:
`sha256:1a07568ea115221393ef705093185aa49cbfb4bb066afb065191cefafaf0532e`.
There were 11 settled generation calls and 11 input counts. The new USD4 allocation
and unused USD3.1379955 are CLOSED. No accounting or transport uncertainty occurred.
Lower cost/time on this unsuccessful trajectory is not repair-quality or efficiency
gain. Invoice and count-endpoint billing have not been independently verified.

## What the public trace establishes

1. The new causal contrast, producer-search and condition-selection instructions
   were present in actual dispatched calls 1-8, before the first edit. Both mutation
   tools carried the exact new field descriptions in calls 2-11. This is not just a
   mock delivery result. Calls 9-11 used the existing post-edit/completion prompts.
2. Source inspection covered `dataelem.py` 480-535 and 535-635, the writer, nearby
   tests, and search snippets around MultiValue, OL and `_is_bytes`. None of the
   delivered read/search spans covered the value setter at 433-449. No read/search
   followed the first edit. The upstream producing step remained unexamined.
3. The first probe (call6, result seq94) used H-array `[1,2,3,4]` serialized to
   bytes as a passing control. Direct array/bytearray inputs became MultiValue and
   failed for **both OL and OB**. It called `add_new -> write_dataset`, not the
   report's sequence-item `add_new -> parent save_as`. Its successful process status
   means the diagnostic ran; the caught TypeErrors are the observed base failures.
4. The public plan already generalized serialized bytes to bytes-like inputs in
   call1. After the helper, call7 explicitly changed the repair target to buffer
   containers and described the failure as not OL-only. That does not explain the
   report's specific OL-fails/OB-and-OF-pass distinction. The helper's successful
   normal bytes case was treated as a control, not a reason to investigate which
   original-content condition was missing.
5. Call8 edited `_convert_value`: buffer-protocol values for binary VRs return
   unchanged before appendable-list conversion. The added test checks OB/OL bytes,
   bytearray and array with identical writer output. The required visible selection
   then reported **213 passed**. The summary alone lacks exact per-node telemetry.
6. Call10 replayed the exact base helper on the changed diff; array/bytearray now
   wrote successfully, while ordinary bytes still passed. This is a useful patch
   effect for those cases, not a redundant same-diff repeat or original-path proof.
7. Call11's finish basis said the helper directly addressed the reported failure
   and no remaining offered action was needed. The assessment still acknowledged
   missing bound original-case verification. It thus treated the mismatch as a
   formal evidence gap while accepting the helper as semantically sufficient.
   Its input still offered reads/searches/probes/edits and showed 30 remaining
   calls, 11 edits, 85 actions, 1,104 solver seconds and USD3.211710. Resource
   exhaustion did not force this decision.

The final public source still has the earlier OL bytes-splitting setter, followed
by the modified conversion. Source inspection therefore predicts the previously
identified bytes-to-list path remains too early for the new guard. This is an
inference from the new patch and public source: the operator did not execute another
counterexample or read the new private failing assertions. Independent FAIL and
this public targeting failure are separate observations, not exact hidden-test
attribution.

## Decision and remaining question

The expected autonomous original-path discovery did **not** occur in this run.
Instructions and tools were delivered, and the agent had resources, but it still
promoted an adjacent helper into the task's success criterion. The observed plan
generalization and finish basis narrow the next question: how to preserve the
reported input and differentiating conditions when revising a repair target, and
make a contradiction with those conditions affect the next action rather than only
the final limitation statement.

Do not add another reminder, finish gate, memory layer or resource increase on the
basis of this single result. The wording change is implemented and locally compatible;
it has no demonstrated quality benefit here. This negative local result does not
prove an inherent reasoning ceiling or universal ineffectiveness. A further change
needs evidence about target-selection/requirement rewriting, not unused budget.
No additional paid run is scheduled.

## Evidence

`C:/pt/causal-task8-20261101-v1/{manifest,preflight,approval,closure,task8,audit,guidance-audit,findings}.json`
bind the frozen configuration, public inputs, tool actions, final patch and usage.
`C:/pt/causal-task8-run-20261101-v1/{result,summary}.json` and
`analysis/public-flow.json` retain aggregate outcomes and public action timing.
All generated evidence stays external in content-addressed artifacts and hash-chained
dev-run-v1 journals. Prior records were not rewritten. No provider reasoning or
private evaluator body was exported into the public analysis or solver context.
