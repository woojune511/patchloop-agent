# Public-check focus: offline localization and live response comparison

## Result

Completed the [frozen design](2026-09-28-public-check-focus-design.md) under the
user's delegated design/execution authorization. official=false. No default change.
Twelve independent responses were collected, with no uncertainty, retries or tools.

| Frozen checkpoint | A: finish / 2 | B: finish / 2 | Relevant discriminator A / B |
| --- | ---: | ---: | ---: |
| Pydantic PA1 (failure-selected) | 2 | 2 | 0 / 0 |
| HF Hub HA1 (failure-selected) | 2 | 2 | 0 / 0 |
| Fromager FA1 (successful control) | 2 | 2 | 0 / 0 |

A preserved the saved input; B additionally repeated its registered public check
definitions at the end. Both had a fresh common 25K output ceiling. The rubric did
not reward more tools or a refusal by itself. No P response raised provider opt-in
versus generic field mode; no H response raised explicit client endpoint versus
constructor-resolved default. F introduced no unnecessary inspection or alleged defect.
All twelve outputs were completed and protocol-valid. This is a negative local
presentation result, not proof of equivalence or a general task-solving result.

Cost $0.367024, 12 counts, 12 generations, 132.791 seconds. Unused $7.632976 closed.
Model gpt-5.4-2026-03-05 xhigh. No Docker, tools, edits to candidates, probes or
benchmark evaluations executed. Acceptance/safety remain NOT_RUN in this diagnostic.

## Offline temporal localization

All six inspected pre-edit/post-check inputs verified against native public state
and the saved actual dispatch. Registered public definitions were already present,
including inline Python checker bodies. A separate upstream pytest selector does
not include the selected test bodies: this experiment did not supply those missing
bodies, and must not be called full checker-source delivery.

- Pydantic's first mutation (call 5), before any check ran, already used field mode
  rather than provider-carried applicability. Later check PASS did not originate
  that scope error. Final explanations often limit their claims to exercised cases,
  but do not recover the provider distinction. A late completion signal is therefore
  not a sufficient explanation of how this particular edit scope first arose.
- HF's first mutation (call 5) explicitly preserves callers without an explicit
  endpoint. Its later source edits forward self.endpoint; final submission says
  remaining uncertainty was resolved by regression PASS. This supports investigating
  loss of the explicit/default distinction during implementation/verification, not
  an assertion that the original requirement was absent. The public provenance
  concern is not established as the hidden evaluator's failing assertion.
- Fromager's first mutation (call 2) explicitly preserves children with surviving
  parents. The final decision keeps the same scoped rationale and public-check limit.
  Mere submission after PASS is not intrinsically wrong or evidence of overconfidence.

These observations separate an early applicability error from later closure without
turning three selected checkpoints into a general failure-frequency estimate.

## Interpretation and limits

The tested seam is presentation of already available public-check definitions.
Repetition, position and input length change together; no additional requirement,
coverage verdict, failure hint, expected solution or private material enters B.
The late duplicate neither corrected the missing distinctions in these two cases
nor induced extra work in the successful control. Do not adopt this duplicate block.

A few completion explanations acknowledge unverified broader behavior, but none
selects a discriminating investigation. One P treatment response explicitly leaves
broader behavior unverified; another broadly claims plain OpenAI behavior is unchanged.
This variation is not consistent semantic improvement. Public wording was graded
before sample arm/order/cost mapping; the same investigator performed review, and
content can indirectly reveal treatment. Aggregate result/cost was visible.

This result weakens the practical hypothesis that merely resurfacing available
checker definitions at submission fixes the observed decisions. It does not prove
that comprehension is impossible, that the model alone is responsible, or that
memory, all result formats, and all completion guidance are harmless. Existing plans,
earlier cues and tool availability stayed shared. The available upstream test bodies
were not added. Two repetitions per checkpoint and historical runtime cohorts limit
any causal/generalization claim; these are not fresh solves on the latest runtime.

The remaining useful seam is requirement-to-edit applicability: determine whether
the deciding condition is justified before it is encoded in the patch, then whether
the chosen verification distinguishes that condition from nearby preservation cases.
No additional intervention, mandatory gate, paid continuation or new allocation follows
automatically. Current production baseline remains unchanged.

## Evidence and verification

- Prepared implementation commit 703169b.
- Plan: C:/pt/analyses/check-focus-plan-20260928-v1/packet.json.
- Offline six-input audit: pre-edit-audit.json plus packet delivery receipts in that root.
- Live: C:/pt/checkfocus0928a, run_dev_sample_a1d7f16afe8e4fe6.
- Report: C:/pt/analyses/check-focus-results-20260928-v1/report.json.
- pre-mapping-grades.json and run_dev_checkfocusreview preserve assessment before mapping.
- All 12 dispatched request artifacts match frozen cells byte-for-byte; source journal
  hashes revalidated after collection; cost sum, model, response status, deadline and
  zero tool executions checked. Plan creation and authorization are journal-bound.
- Shared collector/projection tests passed; 12 fake dispatches preserve exact inputs
  without tools. Ruff passed. Documentation layout and whitespace checks run at closure.
- Official prices reviewed on execution UTC date:
  https://developers.openai.com/api/docs/models/gpt-5.4.

The newer Basic/Current six-task panel was inspected when locating current authority;
its results remain intact and are not pooled as arms or outcomes of this experiment.
No runtime source, historical artifact or previously closed record was rewritten.
