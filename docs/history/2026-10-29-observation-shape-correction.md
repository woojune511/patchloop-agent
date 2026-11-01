# Bounded correction of malformed JSON observations

Status: IMPLEMENTED and LOCALLY_VALIDATED; no live model or benchmark execution.
All evidence is development-only, official=false, claim-ineligible.

## Selected defect and decision

In the [three-task result](2026-10-29-helper-transfer-three-results.md), pvlib's
first original probe declared a two-field object but recorded nine fields. The
comparison became a permanent REFUTED case even after later valid observations.
The existing one-attempt correction handled captured diagnostic conflicts only,
so the model could not link a repair of this observation to the old invalid case.

The [submission-policy change](2026-10-29-public-check-submission.md) made these
diagnostics advisory under explicit public-checks-v1. It did not repair the
observation contract. The user requested that additional correction now. The
goal is to make a chosen diagnostic repairable without turning diagnosis back
into a compulsory stage or redefining benchmark acceptance.

## Change and boundaries

- For v11/null-rules probes, expected and reported-failure JSON must have the same
  root object keys before a different observed key set can be called an observation
  format error. Both comparisons become not_compared, with the raw values/captures
  and bounded missing/extra-field feedback preserved. There is no code-refutation
  credit or automatic replay of this invalid case. Views recompute the narrow
  classification for stored v11 rows; raw receipts are not rewritten.
- Root scalar changes, value changes, array cardinality, nested values and differing
  desired/failure key sets are not classified by this rule. They may be the real
  bug. This is a narrow observation contract, not general JSON-schema inference.
- The existing run-wide single correction allowance covers either this error or a
  legacy captured-judgment conflict. The changed observation program explicitly
  names corrects_action_id and preserves the entire frozen purpose, failure/desired
  JSON and observed call conditions. Complete unchanged-base execution must match
  the declared failure before the old invalid case is superseded. The corrected
  program then supports ordinary candidate replay. Historical action/case links
  remain, and notes based on the old observation require revalidation.
- Rejected requests also consume the one attempt. Altered expectations/inputs,
  incomplete execution or failure to reproduce do not supersede. Exact action
  recovery reuses the receipt; uncertainty still stops physical re-execution.
- Correction is limited to before source edits. Running a corrected program on
  the current candidate cannot certify an original failure. A separate original
  snapshot execution path was not added; later correction remains unavailable.
  A candidate/replay shape error does not create a new baseline-correction gate;
  it stays unknown diagnostic evidence so ordinary repair can continue. Review
  found and corrected this distinction before final validation.
- public-checks-v1 offers correction information in the next model view without
  new mandatory reservations. Unrelated helper/probe work remains possible; an
  explicit correction still undergoes all checks. Strict policy reuses its
  existing correction/repair/check/finish forecast. Total budgets are unchanged.
- General probe descriptions now respect the selected submission policy as well
  as the system prompt. Expected tool-schema hashes changed only for the updated
  ordinary probe description; argument shapes and first-original schemas stayed fixed.

The host does not prove semantic truth of a model-written extractor or issue-to-call
mapping. A field mismatch does not establish that the project code is correct.
Independent task acceptance and required public checks remain unchanged.

## Local validation

New correction controls plus public-check submission controls: **25 PASS in
57.06 seconds**, including ten new cases. Artifact:
`C:/pt/tmp/shape-correction29.xml`. They exercise a real local two-field/nine-field
probe, corrected baseline, candidate edit/replay, finish, same-action recovery,
raw-receipt retention, actual input/expectation preservation, unsuccessful and
second attempts, after-edit rejection, optional-policy guidance, and isolated mock
PASS/FAIL independently of original-verification labels.
One added candidate/replay negative control passed in **2.48 seconds**
(`C:/pt/tmp/shape-candidate29.xml`), bringing the focused set to 26 cases and the
new file to 11 cases. It confirms that candidate shape errors do not force an
unavailable original correction. Compact repair/diagnosis/completion views retain
the observation error as well as its not_compared result.

Legacy correction, resource and description controls: **49 PASS in 1.11 seconds**,
artifact `C:/pt/tmp/shape29core.xml`. Two expected description hashes were updated
after confirming the intentional wording change; no failing behavior was waived.
Quick: **877 PASS, six description-hash failures in 108.33 seconds**
(`C:/pt/tmp/shape29quick.xml`). The six cases' expected hashes were refreshed for
the same intentional probe-description addition, preserving historical-arm values,
and all **six PASS in 0.89 seconds** (`C:/pt/tmp/shape29gold2.xml`). No runtime change
followed quick; a second full run was unnecessary. These 883 cases include isolated
mock smoke. Ruff over `patchloop tests` and whitespace checks passed. No provider,
credential, target benchmark, image build/pull or paid experiment was used.

## Next evidence boundary

The prior `C:/pt/verification-policy-six-plan-v1` comparison binds runtime
`sha256:5f4510bebad0ecd800aba62fb8b4bbcab6f009519c711b5686236e7b659cbbf6` at
`dcede75e`. Its USD27 approval was pending and no live run started. This new runtime
invalidates that preparation; sealed files remain unchanged. Any later live
comparison must be prepared against current code, then authorized for its exact
scope. This turn does not repeat or fund an experiment.

These deterministic controls support mechanism correctness within the stated
shape/base/identity boundaries. Whether a live model recognizes the feedback,
chooses the correction and improves accepted repairs is untested.
