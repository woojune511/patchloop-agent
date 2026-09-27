# Delivered verification questions and closure decisions

Date: 2026-09-28. Status: completed public-input audit; `official=false`.
No provider calls, candidate edits, runtime changes or new evaluation occurred.

## Problem and evidence

The [time extension](2026-09-28-time-extension-results.md) submitted the unchanged
toqito patch immediately. The [public requirements audit](2026-09-28-remaining-public-requirements.md)
then found numerical boundary and mixed-state failures. This investigation asks
whether verification questions disappeared, survived but were dismissed, or were
never constructed. Private evaluator details and hidden failures are excluded.

Artifacts: `C:/pt/analyses/verification-closure-process-20260928-v1/audit.json`
and `policy-review.json`; append-only journal `run_dev_closureprocess` binds them
and `C:/pt/audit_verification_closure_0928.py`. Source journals are
`C:/pt/reviewlive0928a` / `run_dev_reviewcomparison` and
`C:/pt/timeextension0928a` / `run_dev_timeextension`; branch run is
`run_dev_33068b6e257f423a`. All 17 dispatched input bindings were verified with
the segmented-input verifier. Five final frames received detailed inspection.

## Observed sequence

| Input sequence | Delivered state and next public decision |
| --- | --- |
| 403 | Plan revision 21 still requires resolving CQ shortcut versus direct optimizer behavior. |
| 420 | Revision 22 treats submission as unsafe until that semantic question is resolved. The removal edit produces revision 23: regression and a focused CQ probe before submission. |
| 438 | Revision 23 and the CQ question are delivered. Before receiving the requested regression result, the model changes revision 24 to reassess whether a focused probe would materially change submission. |
| 454 | Revision 24 and the optional-probe question survive in the input to the call that times out without a returned decision. |
| 460 | The extension delivers the same question and plan, with fresh time/cost allowance. The next decision is `finish_task`, explicitly clearing the question and describing broader optimizer quality as a documented numerical limitation. |

The final input had 3,608 seconds, $3 and 13 model calls remaining, and exposed
`run_probe` as well as submission. Completion guidance had no recommended next
action. It explicitly said passing required checks permits submission but does
not prove untested behavior. The working plan requested review after context
handoff/check results. The latest current-diff check passed, but evidence coverage
was `not_assessed`, selection was `unresolved`, and declared targets were empty.
All three recent probes were marked historical; none checked the final diff.

The model's returned submission rationale relies on the same-patch regression
and its preceding CQ repair, and classifies remaining optimizer adequacy as
nonblocking. This is an observed public decision, not an inference about private
reasoning. The progression from required probe to optional probe to closure was
model-authored and visible in successive decisions.

## Existing mechanisms and limitations

All 17 inputs had an empty structured verification list; no associated decision
added a nonempty `verification_updates` entry. The tool schema exposed that field.
The existing optional concern mechanism preserves original concerns separately
from focus, requires current-diff successful evidence and a reason for resolution,
and permits reasoned dismissal. It does not establish semantic coverage or gate
submission. This trace shows non-use, not eviction or failed concern recovery.

The root policy also says to use an affordable experiment if it could change the
decision, otherwise submit, and that no extra review or experiment is required.
That instruction remains despite removal of local completion recommendations.
Its causal contribution is untested; other instructions explicitly warn against
treating a passing check as proof of every requirement.

This is not evidence that all source information survived. Final test-file inline
spans contain only blank lines 26, 33 and 39; full assertions were not re-delivered
there. The source projection omits 529 observed lines across 74 ranges. Earlier
reads, search cards and check output are separate evidence. Some helper paths
present after the edit are absent from the final source projection.

Nevertheless, the specific CQ question and its plan demonstrably survived.
The later-discovered near-0.5 pure-state and classical diagonal cases were never
constructed in these probe decisions. They are case-selection gaps, not known
failure observations shown to have been forgotten. Rechecking the same CQ case
alone would not necessarily detect either remaining defect.

## Result and next question

For the CQ question, information disappearance is contradicted by actual inputs;
plan weakening and explicit closure are observed. Separately, public input-range
and behavior coverage was incomplete. Neither result identifies the private
benchmark's failure cause or proves a general improvement mechanism.

The next intervention should target verification scope or closure judgment on one
causal axis, with a frozen input and predefined public outcome measures. The
remaining conditional-submit wording is a testable hypothesis, not an established
cause. Do not add memory/state or mandatory gates merely because existing concern
tracking was unused. No paid continuation or default change is authorized here.
