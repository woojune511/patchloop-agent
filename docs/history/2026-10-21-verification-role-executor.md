# Shared-budget verification executor

Implemented on 2026-10-21 from specification commit
89bc0fb2fdf912a6498a9bfadfdd76c08d5b79a8. This is local implementation evidence,
not a new paid allocation, accepted-repair result, or architecture adoption.

The [probe comparison](2026-10-21-probe-purpose-results.md) exposed unsupported
completion despite available public checks. The next question is whether a
separate verification context helps beyond requiring a verification phase in the
same context. Missing caller evidence, wrong interpretation, ignored feedback
and insufficient repair resources remain alternative explanations. The
[comparison specification](../../.agent/plans/verification-role-comparison.md)
keeps those stages and independent repair acceptance separate.

The implementation uses one existing runner, ledger, deadline, workspace and
action namespace. Initial repair, read-only verification and final repair use
the specified 28/6/6 model-call and USD 0.48/0.20/0.20 envelopes; unused earlier
resources flow only to final repair. The 40-call, 100-action, four-edit totals,
1,800-second clock, existing result/size boundaries, two references and context
limits are unchanged. No task-specific caller or solution is added to the agent.

A continues its native stream; B uses a separate journal read view during
verification, then returns to the paused repair stream. Both use the same public
packet mask, report schema and read-only tools. Archived notes are not concatenated
on return. The report is an ordinary durable action, explicitly unverified and
bound to its reviewed patch. A later edit makes its verdict historical. History
searches in verification also mask repair annotations on exact-ID pages, avoiding
a second route for injecting the repairer's conclusions into B.
An end-to-end sentinel test also caught verifier decision text carried back in a
generic attempt card. Plans and attempt cards now use the current phase's events;
the bounded report and observed receipts remain available without that extra
interpretation channel. Opaque verifier continuation never enters B's repair input.

The grader binds reports, completion claims and report application to actual
request/action/receipt/diff identities. It distinguishes the last final-phase
completion judgment (J_final), any earlier wrong completion (J_any), verifier
false support/rejection (V_wrong), and native plus both original caller grades
(R). Later nonclaims cannot erase a final error. Merely delivering a report,
using an unreviewed interpretation, or treating a stale report as current cannot
receive supported-use credit. Semantic judgments still require a public-evidence
reviewer before fresh private acceptance grades are opened.

Focused tests cover both arms through isolated mock acceptance, fake-provider
counting/dispatch with opaque native items, shared limits and carry, unsettled
batch stops, report idempotency, read-only enforcement, stale reports, interrupted
delivery, scoped schemas, observation-only search and grading controls. The fake
provider deliberately retains the existing evaluator identity mismatch; real
mock runs separately reach EVALUATOR_PASS. No assertion or skip policy was relaxed.
Validation artifacts are outside the repository under
`C:/pt/verification-role49-validation`; the final full-suite receipt is recorded
there after committing the implementation. No provider/counting API, paid judge,
real evaluator, Docker startup, image pull or build is part of these checks.

One locally observed limitation matters for the experiment: the normal
result-followup boundary can reset A exactly when verification begins. The smoke
trajectory does this. The code preserves that rule and records native streams and
phase dispatches; it does not force extra history retention to create a contrast.
Task-specific same-snapshot capture and historical A1/B1/B2 packet replay must
therefore measure the actual contrast and displaced evidence before freezing.
Resource feasibility, those receipts, a frozen six-row manifest and new human
spending approval remain pending. Local tests establish executor mechanics, not
model uptake, verifier accuracy or repair improvement.
