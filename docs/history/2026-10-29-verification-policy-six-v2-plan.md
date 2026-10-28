# Public-check submission comparison after observation correction

Status: preparation only; no live invocation authorized or executed. official=false,
claim-ineligible. This follow-up replaces the stale v1 preparation, not its files.

## Question and reason

The three-task development panel had one isolated acceptance PASS, one FAIL and
one NOT_RUN. A malformed original observation blocked pvlib despite passing public
checks. This motivates separating benchmark repair acceptance from the completeness
of diagnostic evidence. See the [result](2026-10-29-helper-transfer-three-results.md),
[submission policy](2026-10-29-public-check-submission.md) and
[observation correction](2026-10-29-observation-shape-correction.md).

Does optional reproduction with public-check-based submission improve isolated task
acceptance versus mandatory reproduction gates within the same resource ceilings?
The alternative is that bypassing diagnosis mainly increases submissions of wrong
patches. Compare acceptance and regressions, not submission counts alone. Mixed
results or no use of the changed behavior leave the benefit unresolved.

Both arms contain the new bounded observation correction. Consequently this is a
submission-policy comparison, not an estimate of the correction feature's isolated
effect. Correction opportunity, explicit attempt and verified supersession are
secondary process measurements. An absent opportunity is NOT_EXERCISED, not success.
No malformed probe is injected to force this branch.

## Frozen design

| Order | dev-train current-dev20 task | A | B |
| --- | --- | --- | --- |
| 1, 2 | 5: pvlib/pvlib-python-1707 | reproduction-gated-v1 | public-checks-v1 |
| 3, 4 | 9: pydicom/pydicom-1694 | reproduction-gated-v1 | public-checks-v1 |
| 5, 6 | 18: sqlfluff/sqlfluff-1733 | reproduction-gated-v1 | public-checks-v1 |

Each row is one fresh solve from the prepared original source. Within a task pair,
only verification_policy and the fresh state directory differ. The preselected
exposed development tasks, fixed A-first order and one draw per cell cannot support
statistical superiority, repeatability or held-out generalization claims. The
pydicom public report includes a repair suggestion; it remains in both arms.

- Model: gpt-5.4-2026-03-05, xhigh. Credential path:
  C:/Users/geonj/Documents/PatchLoop/.env; preparation checks existence, not contents.
- Proposed allocation: USD4.50 per row, USD27.00 invocation-wide, no transfers.
  These are unapproved ceilings, not spending or guaranteed usable capacity.
- Per row: 20 responses including at most one protocol correction, 40 tool actions,
  three accepted edits, 60K input, 40K ordinary output and 25K correction output.
- 2,400 seconds per row, including 390 seconds reserved for isolated evaluation.
- Thin agent, segmented-v1 context, result-or-size-v1 boundaries, probes enabled,
  bounded-v1 acquisition, repair recheck, protected-v1 inspection and
  completion-recovery-v1 admission. No cross-run history or caller-source override.
- Same registered public checks and isolated evaluator in both arms. No prior patch,
  checkpoint, observations, operator counterexamples or private material in solver
  input. Existing pinned sources, wheels and images are reused without download,
  image pull/build or task-specific changes between rows.

Primary outcome is registered isolated task acceptance, with PASS, FAIL and NOT_RUN
separate. Safety, public checks, submission, delivery labels, original evidence,
cost/time/calls and correction outcomes remain separate. More submissions alone
do not justify changing the default. No default policy changes in this preparation.

The runner counts immediately before dispatch, has zero SDK retries and stops the
whole batch on count, transport, billing, execution, cleanup or bound-input
uncertainty. Settled ordinary failures may proceed to the next predeclared row;
no failed or interrupted row is retried and unused money is not reassigned.

## Reproducibility and validation

Runtime implementation: 0e7d1c20627e647d42f07e4e6944a07f5ed75248,
sha256:db3e1e79a63f9091d1de51ebee32a5bc68df8a62409f5b1aa7247294bf414950.
No runtime change is part of this preparation. Existing validation receipts are
reused at that unchanged content hash: 26 focused cases, 49 legacy controls and
quick-suite evidence (877 PASS plus six intentional description-hash failures,
then all six fixed expectations PASS). Quick includes isolated mock evaluation;
none of this is a live-model or benchmark result.

Fresh preparation, audit receipts, manifest bindings and command live under
C:/pt/verification-policy-six-plan-v2. The reserved live output directory is
C:/pt/verification-policy-six-run-v2. local-validation.json distinguishes the
reused runtime checks from newly executed first-request audits, batch-safety and
correction-metric controls. Offline first-request counts are synthetic and cannot
certify actual provider token fit. The sealed manifest and append-only preparation
journal carry exact hashes and final preflight results.

Fresh checks: six actual first-request construction audits PASS, 19 batch-safety
controls PASS (0.097 seconds), 12 correction-metric controls PASS (0.003469 seconds)
and five documentation checks PASS (0.15 seconds). Ruff and whitespace checks PASS.
The audits block network, credentials and target execution and compare the counted
and dispatched payloads exactly. Metric controls preserve receipts and distinguish
successful supersession from an action merely executing. Feedback exposure remains
unverified until the actual public request is inspected; tool availability alone
does not count as delivery. The four pinned local images are present; full preflight
rechecks their identity after sealing. No new full runtime suite was needed because
the already validated runtime content hash did not change.

No approval receipt or live state is created by preparation. The old v1 manifest
and pending approval do not authorize this changed runtime. A later execution
requires the new manifest's exact task/model/credential/repeat scope and USD27 cap.
