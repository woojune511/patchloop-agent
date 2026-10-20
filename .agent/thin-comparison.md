# Bounded current/thin comparison

Closed 2026-10-07: [results](../docs/history/2026-10-07-thin-comparison-results.md).
All sixteen attempts ran; current remains selected. The USD 64 allocation is
closed at USD 9.71364450. This record grants no restart, replacement or follow-up.

The operator driver is `diagnostics/thin_comparison.py`. This comparison asks
whether the thin interface preserves two known successes and improves two recent
repair failures. It does not change the current default. The frozen design is
`C:/pt/thplan01/plan-v4.json`; public rubrics are `C:/pt/thrub01/packet.json`.
These are operator inputs and never enter a fresh solver's context.

## Scope

Four current-dev20 tasks: SQLFluff-1733 (18), SQLFluff-2419 (20), pvlib-1072 (2),
and pydicom-1694 (9). Each has two fresh solves per arm, sixteen total.
A is current/brief-v1; B is thin/none. Both use gpt-5.4-2026-03-05, xhigh,
25,000 desired output tokens, the repository `.env`, 24k retained source,
segmented/result-or-size context, probes enabled with policy none, repair recheck,
protected inspection and per-call cost admission. Automatic probe replay is off.

Each row has USD 4, 40 model calls, 100 actions, four accepted edits and 1,800
active seconds including 330 evaluation reserve. Native grading has its existing
separate 600-second operational timeout. USD 64 is the exact invocation cap;
unused allocations cannot transfer. This document grants no paid authorization.

The frozen four-wave queue has four distinct tasks per wave and at most two
workers. Each wave must settle before the next begins. A permanent uncertainty
stop prevents subsequent waves and new admissions; admitted calls settle. Known,
settled row limits remain distinct from billing/cleanup/evaluation uncertainty.
No restart, resume, replacement, retry or automatic next panel is allowed.

## Preparation and execution

Preparation uses existing images only and validates task/source/dependency/image,
model/tool and implementation identities. It runs import, public operation,
selected-test and frozen public-base canaries without any provider call or
credential read. The base must expose the scoped bug; saved positive controls
calibrate the rubric separately. Preparation evidence is immutable and external.

Freeze only after code checks and evidence documentation are committed. The final
manifest binds current HEAD and the preparation/validation receipts. Execution
revalidates these inputs, requires exact manifest/cap/model/credential/repetition
authorization, holds a one-shot execution lock, and requires fresh row roots.

Each submitted patch first receives the existing registered/native assessment,
including additive-test projection and request-bound model metadata. Public
grading runs only after settlement with confirmed infrastructure, on the same
unchanged patch and frozen program/profile. Unsubmitted or uncertain rows retain
NOT_RUN public status. Grading output is not returned to the solver. Each row has
its own assessment directory; repeated task identities cannot collide.

## Interpretation

Report registered/native acceptance, public behavior, submission, safety, billing,
time and infrastructure separately. Missing/resource-censored verdicts are
inconclusive. Thin becomes a candidate for further validation only if all four
thin control attempts pass, no paired current-PASS/thin-FAIL regression occurs,
and at least one failure task improves current-FAIL to thin-PASS in both repeats
with matching public behavior and no safety/integrity regression. Savings alone
are insufficient. This exposed development panel does not establish general gain.
Preserve current if both policies repeat the same repair failures.
